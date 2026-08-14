# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Govern dedicated Browser acceptance ownership for the five newest games. (TEST-185)"""

# Parse the browser runner's literal acceptance map without starting a server.
import ast
# Load the reviewed duration profile and economics registry.
import json
# Resolve repository-owned files independently of the caller's working directory.
from pathlib import Path
# Use focused assertions without network or browser dependencies.
import unittest

# Import the pure affected-game classifier for exact path ownership checks.
from scripts import affected_browser_games


# Resolve the repository root once for every source-bound assertion.
ROOT = Path(__file__).resolve().parents[1]
# Bind each newly adopted catalog game to its permanent dedicated Browser case.
EXPECTED_CASES = {
    "daily_draw_lab": "BR-DAILY-DRAW-LAB-001",
    "faro": "BR-FARO-001",
    "four_card_poker": "BR-FOUR-CARD-POKER-001",
    "pachinko": "BR-PACHINKO-001",
    "trente_et_quarante": "BR-TEQ-001",
}


# Prove dedicated case inventory, per-game ownership, and affected-game routing together.
class NewestGameBrowserCoverageTests(unittest.TestCase):
    # Load one literal assignment from the browser runner without importing Playwright.
    def runner_assignment(self, name):
        # Parse the complete runner so missing or computed declarations fail closed.
        tree = ast.parse((ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8"))
        # Search deterministic top-level assignments for the requested owner.
        for node in tree.body:
            # Ignore statements that cannot bind the requested literal.
            if not isinstance(node, ast.Assign) or not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                continue
            # Return only JSON-like literals; executable expressions are rejected by literal_eval.
            return ast.literal_eval(node.value)
        # Fail with the exact missing declaration name.
        self.fail(f"missing runner assignment {name}")

    # Require all five dedicated Browser cases and reviewed duration entries.
    def test_acceptance_map_and_duration_profile_are_complete(self):
        # Read the canonical game-to-case selection map.
        acceptance_map = self.runner_assignment("BROWSER_GAME_ACCEPTANCE_CASES")
        # Require every adopted game to own exactly the approved case id.
        self.assertEqual({game_id: acceptance_map.get(game_id) for game_id in EXPECTED_CASES}, EXPECTED_CASES)
        # Read literal Browser declarations to reject missing or duplicate cases.
        source = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Require each dedicated case to appear exactly once as a run_case declaration.
        for case_id in EXPECTED_CASES.values():
            # Count only the declaration prefix so map and duration strings do not affect the assertion.
            self.assertEqual(source.count(f"run_case('{case_id}'"), 1, case_id)
        # Load the deterministic shard-packing duration profile.
        durations = json.loads((ROOT / "tests" / "browser_case_durations.json").read_text(encoding="utf-8"))
        # Require a positive bounded duration for every newly dedicated case.
        self.assertTrue(all(isinstance(durations.get(case_id), int) and 1 <= durations[case_id] <= 10 for case_id in EXPECTED_CASES.values()))

    # Require per-game suite packages and removal of the former top-level test owners.
    def test_game_test_ownership_is_per_game(self):
        # Check every moved suite through its canonical game-owned package.
        for game_id in EXPECTED_CASES:
            # Require an importable package marker and the existing API/engine suite bytes.
            self.assertTrue((ROOT / "tests" / "games" / game_id / "__init__.py").is_file(), game_id)
            self.assertTrue((ROOT / "tests" / "games" / game_id / "test_api.py").is_file(), game_id)
            # Reject the former conflict-prone top-level ownership path.
            self.assertFalse((ROOT / "tests" / f"{game_id}_tests.py").exists(), game_id)
        # Bind the economics registry to the moved importable suite modules.
        economics = json.loads((ROOT / "tests" / "game_economics_registry.json").read_text(encoding="utf-8"))["entries"]
        # Index the registry once by canonical game id.
        indexed = {row["game_id"]: row for row in economics}
        # Require each proof selector to point beneath its game-owned test package.
        for game_id in EXPECTED_CASES:
            # Reject stale top-level dotted references after the physical move.
            self.assertTrue(all(selector.startswith(f"tests.games.{game_id}.test_api:") for selector in indexed[game_id]["proof_tests"]), game_id)

    # Require single-game changes to select only the matching dedicated Browser case family.
    def test_affected_game_detector_routes_each_owned_path(self):
        # Exercise both a per-game suite path and a frontend path for every adopted game.
        for game_id in EXPECTED_CASES:
            # Require one moved suite file to resolve to its sole owning game.
            self.assertEqual(affected_browser_games.resolve([f"tests/games/{game_id}/test_api.py"]), game_id)
            # Require the corresponding frontend source to select the same dedicated game.
            self.assertEqual(affected_browser_games.resolve([f"web/games/{game_id}.js"]), game_id)


# Run focused evidence directly without starting a listener or browser.
if __name__ == "__main__":
    # Propagate unittest's deterministic process status.
    unittest.main()
