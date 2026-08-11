# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Safety tests for the issue-scoped real-backend browser harness."""

# Import portable filesystem paths for exact boundary assertions.
from pathlib import Path
# Import disposable operating-system directories for allowed-path tests.
import tempfile
# Import standard unit-test support.
import unittest

# Import the harness functions without starting a listener.
from tests.games.dragon_tiger import live_server


# Verify the harness cannot touch repository data or the protected live port.
class DragonTigerLiveServerSafetyTests(unittest.TestCase):
    # Confirm repository paths fail before any directory or server mutation.
    def test_repository_data_path_is_rejected(self):
        # Address the exact protected data location in this worktree.
        protected_data = live_server.REPOSITORY_ROOT / "data"
        # Require fail-closed path validation.
        with self.assertRaises(ValueError):
            # Exercise the same guard called by the launcher.
            live_server.require_temporary_path(protected_data, "data directory")

    # Confirm disposable operating-system paths remain usable for evidence runs.
    def test_operating_system_temp_path_is_allowed(self):
        # Allocate one caller-owned temporary root.
        with tempfile.TemporaryDirectory(prefix="dragon-tiger-harness-test-") as directory:
            # Exercise the accepted resolved data child.
            live_server.require_temporary_path(Path(directory) / "data", "data directory")

    # Confirm the protected live port is rejected before configuration or bind.
    def test_port_8765_is_rejected_before_listener_start(self):
        # Allocate safe data and readiness arguments for the early port guard.
        with tempfile.TemporaryDirectory(prefix="dragon-tiger-harness-test-") as directory:
            # Resolve the disposable root once for both arguments.
            root = Path(directory)
            # Require the launcher to stop before a socket is opened.
            with self.assertRaises(ValueError):
                # Invoke the exact command boundary with the protected port.
                live_server.main(["--data-dir", str(root / "data"), "--ready-file", str(root / "ready.json"), "--port", "8765"])


# Run this focused suite directly when requested.
if __name__ == "__main__":
    # Exit through standard unittest result handling.
    unittest.main()
