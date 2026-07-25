"""Pure Daily Draw Lab rules for the shared settlement core: entropy, validation, resolution. (#144)

Every function is pure and deterministic given its inputs, so the shared core can settle a draw, replay
a retry, and recover from committed ledger proof without ever re-drawing the numbers.
"""

# Import the immutable pool, draw size, pick bounds, and paytables.
from casino.games.daily_draw_lab import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Draw the five distinct authoritative numbers from the injected random function.
def entropy(randbelow) -> dict:
    # Start with every number in the pool eligible to be drawn.
    pool = list(range(1, rules.POOL + 1))
    # Draw distinct numbers by repeatedly removing one remaining number.
    drawn = [pool.pop(randbelow(len(pool))) for _ in range(rules.DRAW)]
    # Return the committed draw in sorted order so the resolver never re-draws.
    return {"drawn": sorted(drawn)}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the player's marked numbers without trusting their shape.
    picks = (request or {}).get("picks")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Require a list of one to five distinct in-range integer picks.
    if not isinstance(picks, list) or not rules.MIN_PICKS <= len(picks) <= rules.MAX_PICKS or any(not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= rules.POOL for number in picks) or len(set(picks)) != len(picks):
        # Fail closed on any malformed, duplicate, or out-of-range pick set.
        raise ValidationError("picks must be one to five distinct numbers from one to thirty")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"picks": sorted(picks), "stake": stake}, float(stake), f"picks:{sorted(picks)}:{stake}"


# Resolve the deterministic settlement from the committed wager and committed draw.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read the committed drawn numbers.
    drawn = entropy_value["drawn"]
    # Find which of the player's marks the draw hit.
    hit = sorted(set(wager["picks"]) & set(drawn))
    # Select the paytable for this pick count and read the multiplier for the hit count.
    multiplier = rules.PAYTABLES[len(wager["picks"])].get(len(hit), 0)
    # Return the settlement with the committed draw, hits, and total return.
    return {"outcome": "win" if multiplier > 0 else "lose", "total_return": round(wager["stake"] * multiplier, 2) if multiplier > 0 else 0, "detail": {"drawn": list(drawn), "picks": list(wager["picks"]), "hit": hit, "hit_count": len(hit)}}
