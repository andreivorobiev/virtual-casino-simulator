"""Immutable Marble Race rules: the six marbles, the two bets, and their track-takeout payouts. (#157)

Six equally fast marbles race and finish in a fully random order. A win bet backs one marble to finish
first; a podium bet backs one marble to finish in the top three. The true odds are five to one for a win
and even money for the podium, and each payout applies a five percent track takeout to those fair odds:
the win pays five point seven times the stake and the podium pays one point nine times, so both bets
return 0.95 on average for a house edge of five percent. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "marble_race"
# Race six equally likely marbles identified by index zero through five.
MARBLES = ("red", "blue", "green", "yellow", "purple", "orange")
# Fill the podium with the first three finishers.
PODIUM_SIZE = 3
# Pay a winning first-place bet five point seven times the stake, a five percent takeout on fair five-to-one odds.
WIN_MULTIPLIER = 5.7
# Pay a winning podium bet one point nine times the stake, a five percent takeout on fair even-money odds.
PODIUM_MULTIPLIER = 1.9
# Bound one wager so a single race can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report the marbles, podium size, and both multipliers so the client can render honest odds.
    return {"marbles": list(MARBLES), "podium_size": PODIUM_SIZE, "win_multiplier": WIN_MULTIPLIER, "podium_multiplier": PODIUM_MULTIPLIER}
