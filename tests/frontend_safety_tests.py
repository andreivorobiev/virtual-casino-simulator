# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free frontend safety regression for SEC-013, UX-021, CORE-028, and TEST-136."""

# Import portable paths for tracked-source and runtime-output assertions.
import pathlib
# Import executable discovery for local and hosted Node runtimes.
import shutil
# Import subprocess execution for the exact JavaScript contract.
import subprocess
# Import unittest assertions and skips.
import unittest

# Resolve the exact checkout root.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Verify security, feedback, motion, and runtime-state hygiene without a browser.
class FrontendSafetyTests(unittest.TestCase):
    # Execute the real JavaScript helpers and tracked source contracts.
    def test_frontend_safety_contract(self):
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
        result = subprocess.run([node, "tests/frontend_safety.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        # Require every JavaScript assertion to pass.
        self.assertEqual(result.returncode, 0, msg=(result.stderr or result.stdout)[-2000:])

    # Keep generated runtime state out of the tracked source inventory.
    def test_runtime_state_is_ignored_and_untracked(self):
        # Read the repository ignore rules exactly as committed.
        ignore_rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        # Require the complete runtime root to be ignored by one exact rule.
        self.assertIn("data/", ignore_rules)
        # Enumerate runtime artifacts that were previously committed with mutable account or game state.
        tracked_runtime_paths = [
            # Cover player identity, wallet, and password state.
            "data/players.json",
            # Cover durable ledger output.
            "data/ledger.jsonl",
            # Cover exported round history.
            "data/history.csv",
            # Cover Baccarat route state.
            "data/games/baccarat.json",
            # Cover Bingo route state.
            "data/games/bingo.json",
            # Cover Keno route state.
            "data/games/keno.json",
        ]
        # Read Git's exact tracked data inventory while allowing prior API cases to create disposable files.
        result = subprocess.run(["git", "ls-files", "--", "data"], cwd=ROOT, capture_output=True, text=True, timeout=20)
        # Branch when a normal checkout exposes exact Git inventory metadata.
        if result.returncode == 0:
            # Normalize every tracked data path to repository-style separators.
            tracked_data = {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}
            # Require every mutable artifact to remain absent from the tracked inventory.
            for relative_path in tracked_runtime_paths:
                # Fail if repository material reintroduces a mutable runtime snapshot.
                self.assertNotIn(relative_path, tracked_data)
        # Otherwise validate the canonical package boundary used by exported release-source copies.
        else:
            # Import the exact packaging policy available inside the isolated candidate source.
            from scripts import package_app
            # Require the complete runtime root to remain forbidden from every archive.
            self.assertIn("data", package_app.FORBIDDEN_PARTS)
            # Require no allowed package prefix to admit the generated runtime root.
            self.assertFalse(any(prefix == "data/" or prefix.startswith("data/") for prefix in package_app.ALLOWED_PREFIXES))
            # Require no explicit top-level package file to admit a runtime snapshot.
            self.assertFalse(any(relative_path in package_app.ALLOWED_FILES for relative_path in tracked_runtime_paths))


# Run this focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
