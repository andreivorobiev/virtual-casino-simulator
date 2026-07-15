"""Immutable Chuck-a-Luck dice and number-wager rules."""

# Import a read-only mapping wrapper so runtime callers cannot alter the payout profile.
from types import MappingProxyType

# Use one stable game identifier for state documents, catalog metadata, and ledger events.
GAME_ID = "chuck_a_luck"
# Require exactly three dice for every settled Chuck-a-Luck round.
DICE_COUNT = 3
# Use standard six-sided dice for every authoritative server roll.
DIE_SIDES = 6
# Preserve the canonical public wager order from face one through face six.
WAGER_TARGETS = ("one", "two", "three", "four", "five", "six")
# Map stable wager identifiers to their matching die faces through an immutable profile.
FACE_BY_TARGET = MappingProxyType({target: index + 1 for index, target in enumerate(WAGER_TARGETS)})
# Pay net winnings equal to the count of matching dice through an immutable profile.
NET_PAYOUT_BY_MATCH_COUNT = MappingProxyType({1: 1, 2: 2, 3: 3})


# Return fresh JSON-compatible rule metadata for API and browser consumers.
def bet_catalog() -> list[dict]:
    # Build the shared match-count paytable once for this response.
    payouts = [
        # Describe one matching-dice row without including the returned stake.
        {"matches": matches, "net_multiplier": multiplier}
        # Preserve ascending match counts for stable rendering and evidence.
        for matches, multiplier in NET_PAYOUT_BY_MATCH_COUNT.items()
    ]
    # Return one independently mutable catalog row for every legal face wager.
    return [
        # Copy nested payout rows so callers cannot mutate another target's metadata.
        {"id": target, "face": FACE_BY_TARGET[target], "payouts": [dict(row) for row in payouts]}
        # Preserve canonical one-through-six ordering in every payload.
        for target in WAGER_TARGETS
    ]
