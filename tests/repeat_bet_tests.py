# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free catalog-wide repeat-bet regression for UX-022 and TEST-137."""

# Import portable paths for the exact JavaScript contract.
import pathlib
# Import executable discovery for local and hosted Node runtimes.
import shutil
# Import subprocess execution without a browser or listener.
import subprocess
# Import unittest assertions and skips.
import unittest

# Resolve the exact checkout root.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Verify every governed game exposes safe, localized one-click repeat behavior.
class RepeatBetTests(unittest.TestCase):
    # Execute the real catalog-wide JavaScript source contract.
    def test_catalog_repeat_bet_contract(self):
        # Discover Node from PATH before considering the bundled Windows runtime.
        node = shutil.which("node")
        # Resolve the bundled runtime used by the desktop workspace when PATH is minimal.
        bundled = pathlib.Path("C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
        # Select the bundled executable only when ordinary discovery failed and it exists.
        if not node and bundled.is_file():
            # Use the exact absolute bundled executable path.
            node = str(bundled)
        # Skip only when the platform has no JavaScript runtime at all.
        if not node:
            # Preserve hosted CI as the required execution gate.
            self.skipTest("Node is unavailable")
        # Execute the focused exact-source contract without a listener.
        result = subprocess.run([node, "tests/repeat_bet.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        # Require every game, locale, delegation, guard, and timer assertion to pass.
        self.assertEqual(result.returncode, 0, msg=(result.stderr or result.stdout)[-3000:])


# Run this focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
