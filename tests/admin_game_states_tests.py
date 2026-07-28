# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
"""Regression test: the admin Game States view must surface nested per-player state files. (issue #457)"""

# Import JSON so state fixtures can be written in the on-disk format.
import json
# Import os so the data directory is isolated before any casino import binds config.
import os
# Import tempfile so all fixture state lives in a disposable directory.
import tempfile
# Import unittest for the dependency-free runner.
import unittest
# Import Path for platform-safe fixture paths.
from pathlib import Path

# Create one module-scoped disposable data root before casino.config resolves GAME_DATA_DIR.
_TMP = tempfile.TemporaryDirectory(prefix="admin_game_states_")
# Route persistent state into the disposable root so the test never touches checked-in data.
os.environ["CASINO_DATA_DIR"] = str(Path(_TMP.name) / "data")
# Route logs into the disposable root for the same isolation guarantee.
os.environ["CASINO_LOG_DIR"] = str(Path(_TMP.name) / "logs")
# Force the JSON provider so no operator MySQL environment can receive test traffic.
os.environ["CASINO_STORAGE_PROVIDER"] = "json"

# Import the resolved game-data root after the environment override binds config.
from casino.config import GAME_DATA_DIR
# Import the admin module under test after isolation.
from casino import admin


# Group the issue #457 game-states regression.
class AdminGameStatesTests(unittest.TestCase):
    # Prove nested per-player state files and legacy flat files both appear in game_states.
    def test_nested_and_flat_state_files_are_surfaced(self):
        # Write a per-player nested state file exactly where live games persist it.
        nested = GAME_DATA_DIR / "bingo" / "human.json"
        # Create the per-game subdirectory before writing.
        nested.parent.mkdir(parents=True, exist_ok=True)
        # Persist a recognizable nested state fixture.
        nested.write_text(json.dumps({"active_session": {"pattern": "line"}}), encoding="utf-8")
        # Write a legacy top-level state file to prove both layouts are covered.
        flat = GAME_DATA_DIR / "roulette.json"
        # Ensure the game-data root exists for the flat fixture.
        flat.parent.mkdir(parents=True, exist_ok=True)
        # Persist a recognizable flat state fixture.
        flat.write_text(json.dumps({"open_bets": []}), encoding="utf-8")
        # Read the admin game-states aggregation under test.
        states = admin.game_states()
        # The nested per-player file must appear under a composite game/player key. (issue #457)
        self.assertIn("bingo/human", states)
        # The nested file's parsed contents must be returned intact.
        self.assertEqual({"pattern": "line"}, states["bingo/human"]["state"]["active_session"])
        # The legacy flat file must still appear under its stem key.
        self.assertIn("roulette", states)
        # A non-recursive glob would have surfaced only the flat file, so seeing both proves the fix.
        self.assertGreaterEqual(len(states), 2)


# Run this focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
