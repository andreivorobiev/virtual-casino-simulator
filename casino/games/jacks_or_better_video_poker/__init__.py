# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Isolated Jacks or Better Video Poker package for GitHub issue #91."""

# Re-export the stable game identifier for game-local adapters and focused tests.
from casino.games.jacks_or_better_video_poker.engine import GAME_ID

# Publish only the stable identifier from this package boundary.
__all__ = ["GAME_ID"]
