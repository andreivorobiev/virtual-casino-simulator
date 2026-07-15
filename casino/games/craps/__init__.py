"""Isolated Craps game package for GitHub issue #90."""

# Re-export the stable game identifier for game-local adapters and tests.
from casino.games.craps.engine import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
