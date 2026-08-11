# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Isolated Texas Hold'em Practice Table package for GitHub issue #95."""

# Export the stable game identifier from the package boundary.
from casino.games.texas_holdem_practice_table.engine import GAME_ID

# Restrict wildcard imports to the documented package identifier.
__all__ = ["GAME_ID"]
