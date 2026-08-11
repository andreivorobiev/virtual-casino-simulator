# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable Boule rules: the nine-number French wheel, its house number, and payouts. (#148)

Boule draws one number from one to nine. Five is the house number: it belongs to no even-money
group, so every even-money bet loses whenever five is drawn, which is the sole source of the house
edge. Each even-money group covers four of the nine numbers and pays two times the stake, and a
single-number bet covers one number and pays eight times the stake. Both bet families therefore
return eight ninths of the stake on average, a house edge of about 11.1 percent. All amounts are play
tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "boule"
# Present the nine drawable numbers in ascending order.
NUMBERS = tuple(range(1, 10))
# Name the house number that belongs to no even-money group and drives the entire edge.
HOUSE_NUMBER = 5
# Map each even-money group to the four numbers it covers; five is deliberately excluded from all.
EVEN_MONEY = {"low": frozenset({1, 2, 3, 4}), "high": frozenset({6, 7, 8, 9}), "odd": frozenset({1, 3, 7, 9}), "even": frozenset({2, 4, 6, 8})}
# Pay every even-money group two times the stake on a covered number.
EVEN_MONEY_MULTIPLIER = 2
# Pay a straight single-number bet eight times the stake on an exact match.
NUMBER_MULTIPLIER = 8
# Bound one wager so a single spin can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report the drawable numbers, the house number, and every payable bet with honest coverage and multiplier.
    return {"numbers": list(NUMBERS), "house_number": HOUSE_NUMBER, "even_money": [{"bet": name, "covers": sorted(EVEN_MONEY[name]), "multiplier": EVEN_MONEY_MULTIPLIER} for name in ("low", "high", "odd", "even")], "number_multiplier": NUMBER_MULTIPLIER}
