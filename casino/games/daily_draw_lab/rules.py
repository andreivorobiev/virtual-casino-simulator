# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable Daily Draw Lab rules: the number pool, the draw size, and per-pick paytables. (#144)

Daily Draw Lab draws five distinct numbers from one to thirty. The player marks one to five numbers, and
the payout depends on how many marks the draw hits, on a separate keno-style paytable for each pick count.
The paytables reward larger pick counts with bigger jackpots, up to ten thousand times the stake for
hitting all five marks. Every pick count's expected return is below one, between 0.91 and 0.95, so all
five bets are house-positive. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "daily_draw_lab"
# Draw numbers from an inclusive pool of one through thirty.
POOL = 30
# Draw exactly five distinct numbers each round.
DRAW = 5
# Allow the player to mark between one and five numbers.
MIN_PICKS = 1
MAX_PICKS = 5
# Map each pick count to a hits-to-multiplier paytable; unlisted hit counts pay nothing.
PAYTABLES = {
    1: {1: 5.5},
    2: {2: 15.0, 1: 2.0},
    3: {3: 100.0, 2: 8.0, 1: 0.5},
    4: {4: 600.0, 3: 40.0, 2: 4.0},
    5: {5: 10000.0, 4: 200.0, 3: 18.0, 2: 2.0},
}
# Bound one wager so a single draw can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report the pool, draw size, pick bounds, and every per-pick paytable so the client can render honestly.
    return {"pool": POOL, "draw": DRAW, "min_picks": MIN_PICKS, "max_picks": MAX_PICKS, "paytables": {str(picks): {str(hits): PAYTABLES[picks][hits] for hits in sorted(PAYTABLES[picks], reverse=True)} for picks in sorted(PAYTABLES)}}
