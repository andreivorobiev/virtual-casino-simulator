"""Isolated Four Card Poker module for GitHub issue #141."""

# Re-export the stable game identity so importers avoid reaching into the engine.
from casino.games.four_card_poker.engine import GAME_ID

# Publish only the stable identity from the package root.
__all__ = ["GAME_ID"]
