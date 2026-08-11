# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Isolated Chuck-a-Luck game package for GitHub issue #89."""

# Re-export the stable game identifier for game-local adapters and focused tests.
from casino.games.chuck_a_luck.rules import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
