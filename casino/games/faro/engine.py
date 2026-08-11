# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Faro rules for the shared settlement core: entropy, bet validation, and resolution. (#146)

Every function is pure and deterministic given its inputs, so the shared core can settle a round,
replay a retry, and recover from committed ledger proof without ever re-dealing the cards.
"""

# Import the immutable ranks, deck size, and multipliers.
from casino.games.faro import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Deal two distinct authoritative cards from the injected random function.
def entropy(randbelow) -> dict:
    # Draw the banker card as a card index across the whole fifty-two-card deck.
    banker = randbelow(rules.DECK)
    # Draw the player card from the remaining fifty-one cards, then skip over the banker card.
    player = randbelow(rules.DECK - 1)
    # Shift the player index up by one whenever it would collide with the already-drawn banker card.
    if player >= banker:
        # Advance past the banker card so the two dealt cards are always distinct.
        player += 1
    # Return the committed card indices and their ranks so the resolver never re-deals.
    return {"banker": banker, "player": player, "banker_rank": banker // rules.SUITS, "player_rank": player // rules.SUITS}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the chosen rank as a bounded one-to-thirteen integer.
    rank = (request or {}).get("rank")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Reject a non-integer or out-of-range rank before any wallet movement.
    if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= len(rules.RANKS):
        # Fail closed on an invalid rank choice.
        raise ValidationError("rank must be an integer from one to thirteen")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"rank": rank, "stake": stake}, float(stake), f"rank:{rank}:{stake}"


# Resolve the deterministic settlement from the committed wager and committed cards.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # Convert the one-based chosen rank into the zero-based rank index the cards carry.
    chosen = wager["rank"] - 1
    # Read whether each dealt card matches the chosen rank.
    player_match = entropy_value["player_rank"] == chosen
    banker_match = entropy_value["banker_rank"] == chosen
    # A split takes half the stake when both cards share the chosen rank.
    if player_match and banker_match:
        # Settle the historical split as a half-stake loss.
        outcome, multiplier = "split", rules.SPLIT_MULTIPLIER
    # A matching player card wins even money.
    elif player_match:
        # Settle the even-money win.
        outcome, multiplier = "win", rules.WIN_MULTIPLIER
    # A matching banker card loses the whole stake.
    elif banker_match:
        # Settle the banker win as a total loss.
        outcome, multiplier = "lose", 0
    # Neither card matching returns the whole stake as a push.
    else:
        # Settle the push by returning the stake.
        outcome, multiplier = "push", rules.PUSH_MULTIPLIER
    # Return the settlement with both dealt cards and the total return.
    return {"outcome": outcome, "total_return": wager["stake"] * multiplier, "detail": {"banker": rules.RANKS[entropy_value["banker_rank"]], "player": rules.RANKS[entropy_value["player_rank"]]}}
