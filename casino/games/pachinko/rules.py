# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable Pachinko rules: the twelve-row pin field and its thirteen payout pockets. (#142)

A ball drops through twelve rows of pins, bouncing left or right at each row, and settles in one of
thirteen pockets numbered by how many times it went right. The landing pocket is binomially distributed,
so the centre pockets are common and pay little while the outer pockets are rare and pay large, up to a
hundred-times jackpot in the two extreme pockets. Across all 4096 equally likely twelve-bounce paths the
expected return is 0.9832, a house edge of about 1.68 percent. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "pachinko"
# Drop the ball through twelve rows of pins, giving thirteen landing pockets.
ROWS = 12
# Pay each of the thirteen pockets its total-return multiplier, symmetric with rare high-paying edges.
POCKETS = (100.0, 15.0, 4.0, 2.0, 1.0, 0.5, 0.3, 0.5, 1.0, 2.0, 4.0, 15.0, 100.0)
# Bound one wager so a single drop can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing payout catalog in pocket order.
def bet_catalog() -> dict:
    # Report the row count and every pocket multiplier so the client can render the board honestly.
    return {"rows": ROWS, "pockets": list(POCKETS)}
