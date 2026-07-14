"""Isolated Multi-Hand Video Poker game package for GitHub issue #94."""

# Re-export the stable game identifier for game-local adapters and tests.
from casino.games.multi_hand_video_poker.engine import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
