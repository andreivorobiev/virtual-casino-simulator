"""Isolated Hi-Lo game package for GitHub issue #85."""

# Re-export the stable game identifier for game-local adapters and tests.
from casino.games.hi_lo.engine import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
