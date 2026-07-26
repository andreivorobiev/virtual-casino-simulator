"""Immutable Faro rules: the thirteen ranks, the fifty-two-card deck, and payout multipliers. (#146)

Faro deals two cards from a standard fifty-two-card deck: the banker card first, then the player card.
The player stakes on a chosen rank. If the player card matches the chosen rank the bet wins even money;
if the banker card matches it loses; if neither matches the stake is returned as a push; and if both cards
share the chosen rank the historical split takes half the stake. Because win and lose are symmetric, the
split half-loss is the entire house edge, about 0.23 percent. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "faro"
# Present the thirteen ranks in ascending faro order.
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
# Give each rank four suits so a fifty-two-card deck can turn a same-rank split.
SUITS = 4
# Derive the full deck size so the entropy draws two distinct real cards.
DECK = len(RANKS) * SUITS
# Pay a matching player card even money as a total return of twice the stake.
WIN_MULTIPLIER = 2
# Return the whole stake on a push where neither card matches the chosen rank.
PUSH_MULTIPLIER = 1
# Return half the stake on a split where both cards share the chosen rank.
SPLIT_MULTIPLIER = 0.5
# Bound one wager so a single deal can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report the selectable ranks and every settlement multiplier so the client can render honest odds.
    return {"ranks": list(RANKS), "win_multiplier": WIN_MULTIPLIER, "push_multiplier": PUSH_MULTIPLIER, "split_multiplier": SPLIT_MULTIPLIER}
