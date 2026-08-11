# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Lucky Grid rules for the shared settlement core: entropy, bet validation, and resolution. (#153)

Every function is pure and deterministic given its inputs, so the shared core can settle a grid, replay
a retry, and recover from committed ledger proof without ever re-placing the prizes.
"""

# Import the immutable board size, pick count, and multipliers.
from casino.games.lucky_grid import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Hide the three prizes on random distinct cells drawn from the injected random function.
def entropy(randbelow) -> dict:
    # Start with every cell eligible to hide a prize.
    pool = list(range(rules.CELLS))
    # Draw distinct prize cells by repeatedly removing one remaining cell.
    prizes = [pool.pop(randbelow(len(pool))) for _ in range(rules.PICKS)]
    # Return the committed prize cells in sorted order so the resolver never re-places them.
    return {"prizes": sorted(prizes)}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the player's picks without trusting their shape.
    picks = (request or {}).get("picks")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Require exactly three distinct in-range integer picks.
    if not isinstance(picks, list) or len(picks) != rules.PICKS or any(not isinstance(cell, int) or isinstance(cell, bool) or not 0 <= cell < rules.CELLS for cell in picks) or len(set(picks)) != rules.PICKS:
        # Fail closed on any malformed or duplicate pick set.
        raise ValidationError("picks must be three distinct cell indices from zero to eight")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"picks": sorted(picks), "stake": stake}, float(stake), f"picks:{sorted(picks)}:{stake}"


# Resolve the deterministic settlement from the committed wager and committed prize placement.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read the committed prize cells.
    prizes = entropy_value["prizes"]
    # Count how many of the player's picks landed on a prize.
    matched = sorted(set(wager["picks"]) & set(prizes))
    # Read the multiplier for the match count, or zero for one or no matches.
    multiplier = rules.PAYOUTS.get(len(matched), 0)
    # Return the settlement with the committed prizes, matched cells, and total return.
    return {"outcome": "win" if multiplier > 0 else "lose", "total_return": round(wager["stake"] * multiplier, 2) if multiplier > 0 else 0, "detail": {"prizes": list(prizes), "picks": list(wager["picks"]), "matched": matched, "match_count": len(matched)}}
