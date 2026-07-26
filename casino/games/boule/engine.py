"""Pure Boule rules for the shared settlement core: entropy, bet validation, and resolution. (#148)

Every function is pure and deterministic given its inputs, so the shared core can settle a round,
replay a retry, and recover from committed ledger proof without ever re-drawing the number.
"""

# Import the immutable numbers, groups, and multipliers.
from casino.games.boule import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Draw the authoritative one-to-nine number from the injected random function.
def entropy(randbelow) -> dict:
    # Draw a zero-based index and shift it into the inclusive one-to-nine range.
    number = randbelow(len(rules.NUMBERS)) + 1
    # Return the committed number so the resolver never re-draws randomness.
    return {"number": number}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the requested bet family without trusting its type.
    bet = (request or {}).get("bet")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Accept a straight single-number bet with an explicit in-range number.
    if bet == "number":
        # Read the chosen number without trusting its type.
        number = (request or {}).get("number")
        # Reject a non-integer or out-of-range single-number selection.
        if not isinstance(number, int) or isinstance(number, bool) or number not in rules.NUMBERS:
            # Fail closed on an invalid number choice.
            raise ValidationError("number must be an integer from one to nine")
        # Return the authoritative straight wager, its total, and a stable fingerprint.
        return {"bet": "number", "number": number, "stake": stake}, float(stake), f"number:{number}:{stake}"
    # Accept a named even-money bet only when it is one of the four groups.
    if bet in rules.EVEN_MONEY:
        # Return the authoritative even-money wager, its total, and a stable fingerprint.
        return {"bet": bet, "stake": stake}, float(stake), f"{bet}:{stake}"
    # Reject any unknown bet family.
    raise ValidationError("bet must be one of low, high, odd, even, or number")


# Resolve the deterministic settlement from the committed wager and committed number.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read the committed drawn number.
    number = entropy_value["number"]
    # Settle a straight single-number bet on an exact match.
    if wager["bet"] == "number":
        # Win the straight multiplier when the drawn number matches the chosen number.
        won = number == wager["number"]
        # Read the straight multiplier for a win.
        multiplier = rules.NUMBER_MULTIPLIER if won else 0
    else:
        # Win the even-money multiplier when the drawn number is covered by the chosen group.
        won = number in rules.EVEN_MONEY[wager["bet"]]
        # Read the even-money multiplier for a win; a drawn house number covers no group and loses.
        multiplier = rules.EVEN_MONEY_MULTIPLIER if won else 0
    # Return the settlement with the committed number and total return.
    return {"outcome": "win" if won else "lose", "total_return": wager["stake"] * multiplier, "detail": {"number": number, "house_number": number == rules.HOUSE_NUMBER}}
