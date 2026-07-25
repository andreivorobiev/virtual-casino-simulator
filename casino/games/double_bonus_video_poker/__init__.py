"""Isolated Double Bonus Video Poker module for GitHub issue #131."""

# Re-export the stable game identity so importers avoid reaching into the engine.
from casino.games.double_bonus_video_poker.engine import GAME_ID

# Publish only the stable identity from the package root.
__all__ = ["GAME_ID"]
