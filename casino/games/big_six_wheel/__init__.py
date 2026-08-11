# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Isolated Big Six Wheel game package for GitHub issue #86."""

# Re-export the stable game identifier for catalog and focused-test consumers.
from casino.games.big_six_wheel.rules import GAME_ID

# Limit wildcard imports to the package's public identity.
__all__ = ["GAME_ID"]
