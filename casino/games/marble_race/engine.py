"""Pure Marble Race rules for the shared settlement core: entropy, bet validation, and resolution. (#157)

Every function is pure and deterministic given its inputs, so the shared core can settle a race, replay
a retry, and recover from committed ledger proof without ever re-running the race.
"""

# Import the immutable marbles, podium size, and multipliers.
from casino.games.marble_race import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Run the race by drawing a uniformly random finishing order from the injected random function.
def entropy(randbelow) -> dict:
    # Start with every marble still waiting to be placed.
    pool = list(range(len(rules.MARBLES)))
    # Build the finishing order by repeatedly drawing one remaining marble.
    order = []
    # Draw each finishing position from the marbles not yet placed for a uniform permutation.
    while pool:
        # Pick a uniformly random remaining marble for the next finishing place.
        order.append(pool.pop(randbelow(len(pool))))
    # Return the committed finishing order so the resolver never re-runs the race.
    return {"order": order}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the requested bet type without trusting its value.
    bet = (request or {}).get("bet")
    # Read the chosen marble index without trusting its type.
    marble = (request or {}).get("marble")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Reject any bet outside the two supported markets.
    if bet not in ("win", "podium"):
        # Fail closed on an unknown bet.
        raise ValidationError("bet must be win or podium")
    # Reject a non-integer or out-of-range marble selection.
    if not isinstance(marble, int) or isinstance(marble, bool) or not 0 <= marble < len(rules.MARBLES):
        # Fail closed on an invalid marble choice.
        raise ValidationError("marble must be an integer marble index")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"bet": bet, "marble": marble, "stake": stake}, float(stake), f"{bet}:{marble}:{stake}"


# Resolve the deterministic settlement from the committed wager and committed finishing order.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read the committed finishing order.
    order = entropy_value["order"]
    # A win bet wins when the chosen marble finished first.
    if wager["bet"] == "win":
        # Settle the win market against the first-place marble.
        won, multiplier = order[0] == wager["marble"], rules.WIN_MULTIPLIER
    else:
        # Settle the podium market against the first three finishers.
        won, multiplier = wager["marble"] in order[:rules.PODIUM_SIZE], rules.PODIUM_MULTIPLIER
    # Return the settlement with the committed order, winner, and podium.
    return {"outcome": "win" if won else "lose", "total_return": round(wager["stake"] * multiplier, 2) if won else 0, "detail": {"order": list(order), "winner": order[0], "podium": order[:rules.PODIUM_SIZE]}}
