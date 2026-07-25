"""Immutable Pattern Draw rules: the nine-cell grid, its patterns, and payout multipliers. (#155)

Pattern Draw lights each of a three-by-three grid's nine cells independently with even odds, then settles
one chosen pattern bet. A line bet wins on any fully lit row, column, or diagonal; a cross bet wins on the
fully lit plus shape of the centre and its four edge cells; and a full bet wins only when all nine cells
light, paying a large jackpot. Over the 512 equally likely grids the line bet wins 282 times, the cross 16
times, and the full grid once, and every payout is set below its fair multiple, so all three bets are
house-positive. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "pattern_draw"
# Light a three-by-three grid of nine cells indexed zero through eight.
CELLS = 9
# Enumerate the eight winning lines: three rows, three columns, and two diagonals, by cell index.
LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
# Define the cross as the plus shape of the centre cell and its four orthogonal neighbours.
CROSS_CELLS = (1, 3, 4, 5, 7)
# Map each pattern bet to its total-return multiplier, each set below its fair multiple for a house edge.
PAYOUTS = {"line": 1.75, "cross": 30.0, "full": 480.0}
# Bound one wager so a single draw can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report each pattern bet and its multiplier so the client can render honest odds.
    return {"cells": CELLS, "bets": [{"bet": name, "multiplier": PAYOUTS[name]} for name in ("line", "cross", "full")]}
