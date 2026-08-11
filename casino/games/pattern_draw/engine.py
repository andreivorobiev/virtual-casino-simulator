# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Pattern Draw rules for the shared settlement core: entropy, bet validation, and resolution. (#155)

Every function is pure and deterministic given its inputs, so the shared core can settle a draw, replay
a retry, and recover from committed ledger proof without ever re-lighting the grid.
"""

# Import the immutable grid, patterns, and multipliers.
from casino.games.pattern_draw import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Light each of the nine grid cells independently with even odds from the injected random function.
def entropy(randbelow) -> dict:
    # Draw one on-or-off bit per cell for a uniformly random grid.
    grid = [randbelow(2) for _ in range(rules.CELLS)]
    # Return the committed grid so the resolver never re-lights the cells.
    return {"grid": grid}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the requested pattern bet without trusting its value.
    bet = (request or {}).get("bet")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Reject any bet outside the three supported patterns.
    if bet not in rules.PAYOUTS:
        # Fail closed on an unknown pattern bet.
        raise ValidationError("bet must be line, cross, or full")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"bet": bet, "stake": stake}, float(stake), f"{bet}:{stake}"


# Report which winning lines are fully lit in a grid.
def lit_lines(grid) -> list:
    # Collect every line whose three cells are all lit.
    return [list(line) for line in rules.LINES if all(grid[cell] for cell in line)]


# Decide whether a chosen pattern is present in the drawn grid.
def pattern_present(bet: str, grid) -> bool:
    # A line bet wins when any winning line is fully lit.
    if bet == "line":
        # Report whether at least one line is complete.
        return any(all(grid[cell] for cell in line) for line in rules.LINES)
    # A cross bet wins when the plus shape is fully lit.
    if bet == "cross":
        # Report whether every cross cell is lit.
        return all(grid[cell] for cell in rules.CROSS_CELLS)
    # A full bet wins only when every cell is lit.
    return all(grid)


# Resolve the deterministic settlement from the committed wager and committed grid.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read the committed grid.
    grid = entropy_value["grid"]
    # Decide whether the chosen pattern is present.
    won = pattern_present(wager["bet"], grid)
    # Read the pattern multiplier for a win.
    multiplier = rules.PAYOUTS[wager["bet"]]
    # Return the settlement with the committed grid, lit lines, and total return.
    return {"outcome": "win" if won else "lose", "total_return": round(wager["stake"] * multiplier, 2) if won else 0, "detail": {"grid": list(grid), "lit_lines": lit_lines(grid), "bet": wager["bet"]}}
