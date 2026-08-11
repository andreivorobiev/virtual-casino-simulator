# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable Poker Dice rules: dice faces, hand categories, and payout multipliers. (#151)

Poker Dice rolls five dice whose six faces are the poker ranks nine, ten, jack, queen, king, and ace.
The best five-die poker category decides the payout. Payouts are total returns that already include the
returned stake, and only three of a kind and above pay, which keeps the expected return below one: over
all 7776 equally likely rolls the return is 0.9761, a house edge of about 2.39 percent. All amounts are
play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "poker_dice"
# Present the six faces in ascending poker-rank order for display and straights.
FACES = ("9", "10", "J", "Q", "K", "A")
# Number of dice rolled each round.
DICE = 5
# Map each paying hand category to its total-return multiplier; unpaid categories are omitted.
PAYOUTS = {"five_of_a_kind": 80, "four_of_a_kind": 15, "full_house": 5, "straight": 4, "three_of_a_kind": 2}
# Enumerate the two straights over six ranks by their face-index sets.
STRAIGHTS = (frozenset({0, 1, 2, 3, 4}), frozenset({1, 2, 3, 4, 5}))
# Bound one wager so a single roll can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing paytable in descending hand order.
def bet_catalog() -> dict:
    # Report each paying hand and its multiplier so the client can render the paytable honestly.
    return {"dice": DICE, "faces": list(FACES), "paytable": [{"hand": hand, "multiplier": PAYOUTS[hand]} for hand in ("five_of_a_kind", "four_of_a_kind", "full_house", "straight", "three_of_a_kind")]}
