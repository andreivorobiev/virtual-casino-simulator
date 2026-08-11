# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Pachinko rules for the shared settlement core: entropy, bet validation, and resolution. (#142)

Every function is pure and deterministic given its inputs, so the shared core can settle a drop, replay
a retry, and recover from committed ledger proof without ever re-dropping the ball.
"""

# Import the immutable pin-row count and pocket multipliers.
from casino.games.pachinko import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Drop the ball through the pin field using the injected random function.
def entropy(randbelow) -> dict:
    # Bounce left or right at each of the twelve rows.
    path = ["R" if randbelow(2) else "L" for _ in range(rules.ROWS)]
    # The landing pocket is the number of right bounces, from zero through twelve.
    pocket = sum(1 for step in path if step == "R")
    # Return the committed path and pocket so the resolver never re-drops the ball.
    return {"path": path, "pocket": pocket}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the stake as a bounded positive integer; Pachinko stakes the whole drop.
    stake = (request or {}).get("stake")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"stake": stake}, float(stake), f"stake:{stake}"


# Resolve the deterministic settlement from the committed wager and committed drop.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read the committed landing pocket.
    pocket = entropy_value["pocket"]
    # Read the multiplier for the landing pocket.
    multiplier = rules.POCKETS[pocket]
    # A pocket paying more than the stake wins, exactly the stake pushes, and less loses.
    outcome = "win" if multiplier > 1 else "push" if multiplier == 1 else "lose"
    # Return the settlement with the committed path, pocket, and total return.
    return {"outcome": outcome, "total_return": round(wager["stake"] * multiplier, 2), "detail": {"pocket": pocket, "path": list(entropy_value["path"]), "multiplier": multiplier}}
