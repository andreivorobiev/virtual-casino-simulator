"""Focused TEST-092 proofs for the exact-source 50,000-cycle UI harness."""

import argparse  # Build narrow command namespaces without invoking the CLI parser.
import json  # Persist synthetic shard reports for resume-policy tests.
import tempfile  # Own disposable report directories for every test.
import unittest  # Integrate the focused proofs with the repository API runner.
from collections import Counter  # Aggregate deterministic per-game allocation totals.
from pathlib import Path  # Address temporary shard reports with platform-neutral paths.

from tests import ui_50000  # Exercise the public harness helpers without starting Playwright.


# Prove TEST-092 allocation, control classification, and exact-source resume invariants.
class UI50000HarnessTests(unittest.TestCase):
    # Prove the formal catalog allocation assigns exactly 50,000 unique IDs and the required game floor.
    def test_formal_allocation_is_exact_and_balanced(self):
        allocations = ui_50000.allocate_cycles(list(ui_50000.GAME_IDS), 50_000, 4, set(), 4)  # Build the formal deterministic assignment.
        per_game = Counter()  # Aggregate replica quotas back to canonical games.
        assigned_ids = []  # Reconstruct every global cycle ID for uniqueness evidence.
        for game_id, _game_index, _replica_index, quota, cycle_start in allocations:  # Inspect every bounded worker assignment.
            per_game[game_id] += quota  # Preserve the complete game quota across replicas.
            assigned_ids.extend(range(cycle_start, cycle_start + quota))  # Rebuild the worker's contiguous global range.
        self.assertEqual(sum(per_game.values()), 50_000)  # Require the exact formal total.
        self.assertEqual(len(per_game), len(ui_50000.GAME_IDS))  # Require every registered game exactly once in the aggregate.
        self.assertGreaterEqual(min(per_game.values()), 1_666)  # Require the issue-owned per-game floor.
        self.assertEqual(set(assigned_ids), set(range(50_000)))  # Require no missing or duplicate global identities.
        self.assertEqual(len(assigned_ids), len(set(assigned_ids)))  # Reject overlapping replica ranges.

    # Prove namespacing prevents identical generic selectors from merging across games.
    def test_control_signatures_keep_module_ownership(self):
        roulette = ui_50000.qualify_control_signature("button[data-action=deal]", "roulette")  # Qualify one generic selector for Roulette.
        baccarat = ui_50000.qualify_control_signature("button[data-action=deal]", "baccarat")  # Qualify the same selector for Baccarat.
        self.assertNotEqual(roulette, baccarat)  # Require independent coverage identities.

    # Prove every observed control receives exactly one honest acceptance classification.
    def test_control_coverage_classifies_floor_conditional_failure_and_exclusion(self):
        seen = Counter({"roulette::button[data-testid=spin]": 120, "blackjack::button[data-action=insurance]": 12, "baccarat::button[data-action=deal]": 200, "auth::input[data-testid=login-email]": 1})  # Model ordinary, rare, skipped, and lifecycle controls.
        activated = Counter({"roulette::button[data-testid=spin]": 120, "blackjack::button[data-action=insurance]": 6, "auth::input[data-testid=login-email]": 1})  # Exercise the passing control and sample the mutually exclusive rare action.
        result = ui_50000.classify_control_coverage(seen, activated)  # Apply the durable policy.
        self.assertIn("roulette::button[data-testid=spin]", result["exercised"])  # Accept the literal 100-activation floor.
        self.assertIn("blackjack::button[data-action=insurance]", result["intentionally_unavailable"])  # Accept a rare control only with real activation evidence.
        self.assertIn("baccarat::button[data-action=deal]", result["failed"])  # Fail an ordinarily reachable skipped control.
        self.assertIn("auth::input[data-testid=login-email]", result["excluded"])  # Keep one-time authentication outside gameplay counts.
        self.assertEqual(result["classified_count"], 4)  # Require complete mutually exclusive accounting.

    # Prove a terminal shard from another source commit is rerun instead of silently resumed.
    def test_resume_requires_exact_source_commit(self):
        allocation = ("roulette", ui_50000.GAME_IDS.index("roulette"), 0, 5, 0)  # Build one deterministic shard identity.
        with tempfile.TemporaryDirectory() as temporary_directory:  # Own and clean one synthetic report root.
            root = Path(temporary_directory)  # Resolve the disposable root.
            report_path = root / f"{allocation[1]:02d}-roulette-r0.json"  # Match the harness's shard filename.
            report = {"source_commit": "a" * 40, "game": "roulette", "game_index": allocation[1], "replica_index": 0, "quota": 5, "global_cycle_start": 0, "global_cycle_end": 4, "attempted": 5, "listener_cleanup": {"closed": True}, "isolation": {"player_match": True, "nonnegative_balance": True}}  # Build an otherwise terminal foreign-source handback.
            report_path.write_text(json.dumps(report), encoding="utf-8")  # Persist the candidate evidence.
            args = argparse.Namespace(resume_shards=True, shard_report_root=str(root))  # Enable safe-boundary resumption.
            resumed, pending = ui_50000.partition_resume_allocations(args, [allocation], "b" * 40)  # Ask for a different immutable source.
            self.assertEqual(resumed, [])  # Reject the stale handback.
            self.assertEqual(pending, [allocation])  # Schedule the exact range from scratch.
            report["source_commit"] = "b" * 40  # Bind the handback to the requested source.
            report_path.write_text(json.dumps(report), encoding="utf-8")  # Replace only the test-owned candidate.
            resumed, pending = ui_50000.partition_resume_allocations(args, [allocation], "b" * 40)  # Re-evaluate exact-source compatibility.
            self.assertEqual(len(resumed), 1)  # Accept the complete matching safe boundary.
            self.assertEqual(pending, [])  # Avoid rerunning already terminal matching work.


# Run the focused module directly for local diagnosis.
if __name__ == "__main__":
    unittest.main()  # Return unittest's standard terminal status.
