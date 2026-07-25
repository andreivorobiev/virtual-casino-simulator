"""Pure Poker Dice rules for the shared settlement core: entropy, bet validation, and resolution. (#151)

Every function is pure and deterministic given its inputs, so the shared core can settle a round, replay
a retry, and recover from committed ledger proof without ever re-rolling the dice.
"""

# Import Counter for face-frequency hand evaluation.
from collections import Counter

# Import the immutable faces, paytable, straights, and bounds.
from casino.games.poker_dice import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Draw the authoritative five-die roll from the injected random function.
def entropy(randbelow) -> dict:
    # Roll five independent dice as face indices zero through five.
    dice = [randbelow(len(rules.FACES)) for _ in range(rules.DICE)]
    # Return the committed dice so the resolver never re-rolls randomness.
    return {"dice": dice}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the stake as a bounded positive integer; Poker Dice stakes the whole roll.
    stake = (request or {}).get("stake")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"stake": stake}, float(stake), f"stake:{stake}"


# Classify one five-die roll into its highest paying poker category.
def category(dice) -> str:
    # Count how many dice share each face.
    counts = sorted(Counter(dice).values(), reverse=True)
    # Five identical faces is five of a kind.
    if counts[0] == 5:
        # Return the top category.
        return "five_of_a_kind"
    # Four identical faces is four of a kind.
    if counts[0] == 4:
        # Return four of a kind.
        return "four_of_a_kind"
    # A triple plus a pair is a full house.
    if counts == [3, 2]:
        # Return full house.
        return "full_house"
    # Five distinct faces forming one of the two straights beats three of a kind.
    if frozenset(dice) in rules.STRAIGHTS:
        # Return straight.
        return "straight"
    # A bare triple is three of a kind.
    if counts[0] == 3:
        # Return three of a kind.
        return "three_of_a_kind"
    # Two pair, one pair, and high card do not pay.
    return "bust"


# Resolve the deterministic settlement from the committed wager and committed dice.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Evaluate the committed roll's best category.
    hand = category(entropy_value["dice"])
    # Read the multiplier for a paying hand, or zero for a non-paying category.
    multiplier = rules.PAYOUTS.get(hand, 0)
    # A paying category wins its multiplier; anything else loses.
    outcome = "win" if multiplier > 0 else "lose"
    # Return the settlement with the committed dice, category, and total return.
    return {"outcome": outcome, "total_return": wager["stake"] * multiplier, "detail": {"dice": list(entropy_value["dice"]), "faces": [rules.FACES[index] for index in entropy_value["dice"]], "hand": hand}}
