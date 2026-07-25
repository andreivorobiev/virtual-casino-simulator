"""Isolated Teen Patti Practice module for GitHub issue #150."""

# Re-export the stable game identity so importers avoid reaching into the engine.
from casino.games.teen_patti.engine import GAME_ID

# Publish only the stable identity from the package root.
__all__ = ["GAME_ID"]
