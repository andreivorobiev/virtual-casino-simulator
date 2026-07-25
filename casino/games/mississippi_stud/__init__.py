"""Isolated Mississippi Stud module for GitHub issue #143."""

# Re-export the stable game identity so importers avoid reaching into the engine.
from casino.games.mississippi_stud.engine import GAME_ID

# Publish only the stable identity from the package root.
__all__ = ["GAME_ID"]
