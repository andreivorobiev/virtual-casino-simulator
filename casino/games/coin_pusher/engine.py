"""Pure Coin Pusher rules for the shared settlement core: entropy, bet validation, and resolution. (#156)

Every function is pure and deterministic given its inputs, so the shared core can settle a drop, replay
a retry, and recover from committed ledger proof without ever re-simulating the shelf.
"""

# Import the immutable shelf, push, threshold, and cascade multipliers.
from casino.games.coin_pusher import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Draw the authoritative shelf fill and push from the injected random function.
def entropy(randbelow) -> dict:
    # Draw how many earlier coins already sit on the shelf before the drop.
    shelf_start = randbelow(rules.SHELF_SLOTS)
    # Draw how many push units the dropped coin advances the pile.
    push = randbelow(rules.PUSH_SLOTS)
    # Return the committed shelf fill and push so the resolver never re-simulates.
    return {"shelf_start": shelf_start, "push": push}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the stake as a bounded positive integer; Coin Pusher stakes the whole drop.
    stake = (request or {}).get("stake")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"stake": stake}, float(stake), f"stake:{stake}"


# Compute how many coins cascade off the edge for a committed shelf fill and push.
def cascade(shelf_start: int, push: int) -> int:
    # The dropped coin adds itself plus its push to the earlier pile.
    filled = shelf_start + push + 1
    # Coins cascade only once the pile reaches the tipping threshold.
    return filled - rules.THRESHOLD + 1 if filled >= rules.THRESHOLD else 0


# Resolve the deterministic settlement from the committed wager and committed shelf.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Compute how many coins cascade off the front edge.
    coins = cascade(entropy_value["shelf_start"], entropy_value["push"])
    # Read the multiplier for the cascaded coin count, or zero when nothing tips.
    multiplier = rules.CASCADE_PAYOUTS.get(coins, 0)
    # A cascade wins its multiplier; a pile that stays below the threshold loses.
    outcome = "win" if multiplier > 0 else "lose"
    # Return the settlement with the committed shelf detail and total return.
    return {"outcome": outcome, "total_return": round(wager["stake"] * multiplier, 2), "detail": {"shelf_start": entropy_value["shelf_start"], "push": entropy_value["push"], "filled": entropy_value["shelf_start"] + entropy_value["push"] + 1, "coins": coins, "multiplier": multiplier}}
