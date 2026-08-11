# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable Lucky Grid rules: the nine-cell board, the pick count, and match payouts. (#153)

Lucky Grid hides three prizes on random distinct cells of a nine-cell board. The player picks three
cells, and the payout depends on how many picks land on a prize: matching all three pays a jackpot, two
pays a smaller multiple, and one or none pays nothing. Over the eighty-four equally likely prize
placements a fixed set of picks matches all three once, two eighteen times, one forty-five times, and none
twenty times, so the paytable returns 0.9405 on average for a house edge of about six percent. All amounts
are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "lucky_grid"
# Lay out a three-by-three board of nine cells indexed zero through eight.
CELLS = 9
# Hide three prizes and require the player to pick three cells.
PICKS = 3
# Map each match count to its total-return multiplier; one and zero matches pay nothing.
PAYOUTS = {3: 25.0, 2: 3.0}
# Bound one wager so a single grid can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report the board size, pick count, and match multipliers so the client can render honest odds.
    return {"cells": CELLS, "picks": PICKS, "payouts": [{"matches": matches, "multiplier": PAYOUTS[matches]} for matches in (3, 2)]}
