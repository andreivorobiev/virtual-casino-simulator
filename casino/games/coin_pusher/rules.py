# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable Coin Pusher rules: the shelf threshold, push range, and cascade payouts. (#156)

A dropped coin lands on a shelf that already holds a random pile of earlier coins, and the coin advances
the pile by a random push. When the pile crosses the tipping threshold the overflowing coins cascade off
the front edge and pay out; the more coins that fall, the larger the multiplier, up to a sixteen-times
jackpot. When the pile stays below the threshold nothing falls and the coin simply feeds the shelf.
Across all forty-eight equally likely shelf-and-push combinations the expected return is 0.9583, a house
edge of about 4.17 percent. This shelf is simulated fresh each drop rather than persisted across rounds,
so every drop settles purely from its own committed randomness. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "coin_pusher"
# Model the shelf as already holding between zero and eleven earlier coins before the drop.
SHELF_SLOTS = 12
# Advance the pile by zero to three push units when the coin lands.
PUSH_SLOTS = 4
# Tip the pile once it reaches this filled height, cascading the overflow off the edge.
THRESHOLD = 12
# Pay each count of cascaded coins its total-return multiplier, rising to a jackpot on a full cascade.
CASCADE_PAYOUTS = {1: 1.5, 2: 4.0, 3: 6.0, 4: 16.0}
# Bound one wager so a single drop can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing payout catalog in cascade order.
def bet_catalog() -> dict:
    # Report the threshold and every cascade multiplier so the client can render honest odds.
    return {"threshold": THRESHOLD, "cascades": [{"coins": coins, "multiplier": CASCADE_PAYOUTS[coins]} for coins in (1, 2, 3, 4)]}
