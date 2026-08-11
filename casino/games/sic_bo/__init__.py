# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Isolated Sic Bo game package for GitHub issue #88."""

# Re-export the stable identifier used by game-local adapters and tests.
from casino.games.sic_bo.rules import GAME_ID

# Publish only the stable package identifier from this boundary.
__all__ = ["GAME_ID"]
