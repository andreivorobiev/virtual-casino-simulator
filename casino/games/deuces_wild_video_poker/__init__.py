"""Isolated Deuces Wild Video Poker package for GitHub issue #92."""

# Re-export the stable game identifier for game-local adapters and focused tests.
from casino.games.deuces_wild_video_poker.engine import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
