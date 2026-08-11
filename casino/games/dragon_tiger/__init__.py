# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Isolated Dragon Tiger game package for GitHub issue #83."""

# Re-export the stable game identifier for game-local adapters and tests.
from casino.games.dragon_tiger.engine import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
