# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-integrated Let It Ride module for GitHub issue #134."""

# Re-export the stable game identifier for focused tests and integration metadata.
from casino.games.let_it_ride.engine import GAME_ID

# Publish only the stable identifier from the package boundary.
__all__ = ["GAME_ID"]
