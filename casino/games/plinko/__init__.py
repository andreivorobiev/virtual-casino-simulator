"""Catalog-integrated Plinko game module accepted for GitHub issue #136."""

# Import the stable game identifier from the game-owned engine.
from casino.games.plinko.engine import GAME_ID

# Expose only the game identifier at package level.
__all__ = ["GAME_ID"]
