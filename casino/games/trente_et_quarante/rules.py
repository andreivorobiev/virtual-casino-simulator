"""Immutable Trente et Quarante rules: card values, the two rows, and payout multipliers. (#147)

Trente et Quarante ("thirty and forty") deals two rows of cards, Noir first then Rouge, each until its
running pip total passes thirty, so every row settles between thirty-one and forty. The row closer to
thirty-one wins. Players bet Rouge or Noir on which row wins, or Couleur or Inverse on whether the very
first card's colour matches the winning row's colour. All four bets pay even money. When both rows tie
the stake is returned as a push, except the refait at thirty-one, where the bank bars half the stake:
this refait is the entire house edge. All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "trente_et_quarante"
# Present the thirteen ranks for card display.
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
# Model a standard fifty-two-card shoe so ranks and colours keep authentic proportions.
DECK = 52
# Deal each row until its running total passes this threshold, so totals land between thirty-one and forty.
ROW_THRESHOLD = 30
# Name the refait total where a tie bars half the stake and creates the entire house edge.
REFAIT_TOTAL = 31
# Enumerate the four even-money bets in stable order.
BETS = ("rouge", "noir", "couleur", "inverse")
# Pay a winning even-money bet a total return of twice the stake.
WIN_MULTIPLIER = 2
# Return the whole stake on a non-refait tie push.
PUSH_MULTIPLIER = 1
# Return half the stake on a refait at thirty-one.
REFAIT_MULTIPLIER = 0.5
# Bound one wager so a single coup can never stake an absurd amount.
MAX_STAKE = 100_000


# Compute the pip value of a shoe card index, where ace is one and every ten-or-face card is ten.
def card_value(card: int) -> int:
    # Return the capped pip value for the card's rank.
    return min(card % len(RANKS) + 1, 10)


# Compute the colour of a shoe card index, where the first two suits are red and the last two are black.
def card_color(card: int) -> str:
    # Return red for the heart and diamond suits and black for the club and spade suits.
    return "red" if card // len(RANKS) < 2 else "black"


# Publish the player-facing bet catalog in stable order.
def bet_catalog() -> dict:
    # Report the four bets and every settlement multiplier so the client can render honest odds.
    return {"bets": list(BETS), "win_multiplier": WIN_MULTIPLIER, "push_multiplier": PUSH_MULTIPLIER, "refait_multiplier": REFAIT_MULTIPLIER, "refait_total": REFAIT_TOTAL}
