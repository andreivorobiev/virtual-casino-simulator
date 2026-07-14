"""Isolated Plinko game module proposed by GitHub issue #136."""

# Import the stable game identifier from the isolated engine.
from casino.games.plinko.engine import GAME_ID

# Expose only the game identifier at package level.
__all__ = ["GAME_ID"]
