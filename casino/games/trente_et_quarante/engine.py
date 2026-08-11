# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Trente et Quarante rules for the shared settlement core: entropy, validation, resolution. (#147)

Every function is pure and deterministic given its inputs, so the shared core can settle a coup, replay
a retry, and recover from committed ledger proof without ever re-dealing the cards.
"""

# Import the immutable card values, thresholds, bets, and multipliers.
from casino.games.trente_et_quarante import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Deal one row from the injected random function until its running pip total passes the threshold.
def _deal_row(randbelow) -> tuple:
    # Accumulate dealt cards and their running pip total.
    cards, total = [], 0
    # Keep drawing until the row total passes thirty, so it always lands between thirty-one and forty.
    while total <= rules.ROW_THRESHOLD:
        # Draw the next shoe card index.
        card = randbelow(rules.DECK)
        # Record the card's rank and colour for display and colour bets.
        cards.append({"rank": rules.RANKS[card % len(rules.RANKS)], "color": rules.card_color(card)})
        # Add the card's pip value to the row total.
        total += rules.card_value(card)
    # Return the dealt row and its final total.
    return cards, total


# Deal both rows and record the totals and the first card's colour.
def entropy(randbelow) -> dict:
    # Deal the Noir row first, exactly as at a real table.
    noir, noir_total = _deal_row(randbelow)
    # Deal the Rouge row second.
    rouge, rouge_total = _deal_row(randbelow)
    # Return the committed rows, totals, and the first dealt card's colour so the resolver never re-deals.
    return {"noir": noir, "rouge": rouge, "noir_total": noir_total, "rouge_total": rouge_total, "first_color": noir[0]["color"]}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the requested bet without trusting its type.
    bet = (request or {}).get("bet")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Reject any bet outside the four even-money options.
    if bet not in rules.BETS:
        # Fail closed on an unknown bet.
        raise ValidationError("bet must be one of rouge, noir, couleur, or inverse")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"bet": bet, "stake": stake}, float(stake), f"{bet}:{stake}"


# Resolve the deterministic settlement from the committed wager and committed deal.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Read both committed row totals.
    noir_total, rouge_total = entropy_value["noir_total"], entropy_value["rouge_total"]
    # The row with the lower total is closer to thirty-one and wins; equal totals tie.
    winner = "noir" if noir_total < rouge_total else "rouge" if rouge_total < noir_total else None
    # A tie at thirty-one is the refait that bars half the stake.
    if winner is None and noir_total == rules.REFAIT_TOTAL:
        # Settle every bet as a refait half-loss.
        outcome, multiplier = "refait", rules.REFAIT_MULTIPLIER
    # Any other tie returns the whole stake as a push.
    elif winner is None:
        # Settle the push by returning the stake.
        outcome, multiplier = "push", rules.PUSH_MULTIPLIER
    else:
        # Map the winning row to its colour so the colour bets can settle.
        winning_color = "black" if winner == "noir" else "red"
        # A rouge or noir bet wins when it names the winning row.
        row_win = wager["bet"] == winner
        # A couleur bet wins when the first card's colour matches the winning colour; inverse is the opposite.
        colour_win = (wager["bet"] == "couleur" and entropy_value["first_color"] == winning_color) or (wager["bet"] == "inverse" and entropy_value["first_color"] != winning_color)
        # Settle the even-money win when either the row bet or the colour bet is satisfied.
        won = row_win or colour_win
        # Read the win multiplier or a total loss.
        outcome, multiplier = ("win", rules.WIN_MULTIPLIER) if won else ("lose", 0)
    # Return the settlement with both totals, the winning row, and the first card's colour.
    return {"outcome": outcome, "total_return": wager["stake"] * multiplier, "detail": {"noir_total": noir_total, "rouge_total": rouge_total, "winner": winner, "first_color": entropy_value["first_color"], "noir": entropy_value["noir"], "rouge": entropy_value["rouge"]}}
