"""Isolated Three Card Poker package for GitHub issue #93."""

# Re-export the stable game identifier for adapters and focused tests.
from casino.games.three_card_poker.engine import GAME_ID

# Publish only the stable package identifier.
__all__ = ["GAME_ID"]
