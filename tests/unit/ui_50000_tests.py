"""Focused TEST-092 proofs for the exact-source 50,000-cycle UI harness."""

import argparse  # Build narrow command namespaces without invoking the CLI parser.
import asyncio  # Exercise the browser-free aggregate controller end to end.
import json  # Persist synthetic shard reports for resume-policy tests.
import subprocess  # Resolve the exact test checkout commit for provenance validation.
import tempfile  # Own disposable report directories for every test.
import unittest  # Integrate the focused proofs with the repository API runner.
from collections import Counter  # Aggregate deterministic per-game allocation totals.
from pathlib import Path  # Address temporary shard reports with platform-neutral paths.

from tests import ui_50000  # Exercise the public harness helpers without starting Playwright.


# Prove TEST-092 allocation, control classification, and exact-source resume invariants.
class UI50000HarnessTests(unittest.TestCase):
    # Persist one complete synthetic distributed corpus bound to an exact source identity.
    def write_distributed_corpus(self, root, allocations, source_commit, evidence_root=None):
        for game_id, game_index, replica_index, quota, cycle_start in allocations:  # Materialize every deterministic formal worker handback.
            report = {"source_commit": source_commit, "game": game_id, "game_index": game_index, "replica_index": replica_index, "quota": quota, "global_cycle_start": cycle_start, "global_cycle_end": cycle_start + quota - 1, "requirements": list(ui_50000.REQUIREMENT_IDS)}  # Bind the synthetic evidence to its exact immutable identity.
            if evidence_root is not None:  # Add complete passing fields only for end-to-end aggregate proofs.
                control = f"{game_id}::button[data-testid=primary-action]"  # Give every game one eligible control above the activation floor.
                visuals = []  # Build one unique artifact for each governed viewport.
                for viewport in ui_50000.VIEWPORTS:  # Cover the complete authoritative viewport inventory.
                    artifact = f"representative/{game_index:02d}-{game_id}-r{replica_index}-{viewport['id']}.png"  # Derive a stable unique public artifact name.
                    screenshot = evidence_root / Path(artifact)  # Resolve the disposable screenshot path.
                    screenshot.parent.mkdir(parents=True, exist_ok=True)  # Create only the test-owned evidence directory.
                    screenshot.write_bytes(b"synthetic-png")  # Persist a nonempty placeholder because unit tests validate inventory, not pixels.
                    geometry = {"document_overflow_x_px": 0, "brand_truncated": False, "clipped_enabled_control_count": 0, "occluded_enabled_control_count": 0}  # Model clean automated geometry.
                    visuals.append({"viewport": viewport, "geometry": geometry, "artifact": artifact, "evidence_class": "after_pass"})  # Record one passing governed row.
                report.update({"attempted": quota, "attempted_actions": quota, "completed": quota, "failed": 0, "failed_attempts": 0, "status": "PASS", "listener_cleanup": {"closed": True}, "isolation": {"player_match": True, "nonnegative_balance": True}, "control_seen_counts": {control: quota}, "control_activated_counts": {control: quota}, "failure_counts": {}, "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}}, "visuals": visuals, "latency": {"count": quota}})  # Complete every aggregate-owned passing gate.
            path = root / f"{game_index:02d}-{game_id}-r{replica_index}.json"  # Match the production shard filename.
            path.write_text(json.dumps(report), encoding="utf-8")  # Persist the test-owned public evidence.

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
        self.assertEqual(len(allocations), 33)  # Pin the current 30-game catalog plus three additional Roulette replicas for the workflow matrix.

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

    # Prove a complete distributed corpus loads once in canonical allocation order.
    def test_distributed_shards_require_complete_exact_inventory(self):
        allocations = ui_50000.allocate_cycles(list(ui_50000.GAME_IDS), 50_000, 4, set(), 4)  # Build the immutable formal assignment.
        source_commit = "c" * 40  # Use one valid synthetic full commit identity.
        with tempfile.TemporaryDirectory() as temporary_directory:  # Own and clean the downloaded-artifact simulation.
            root = Path(temporary_directory)  # Resolve the test-owned shard root.
            self.write_distributed_corpus(root, allocations, source_commit)  # Persist every exact worker handback.
            args = argparse.Namespace(shard_report_root=str(root), evidence_root=str(root / "visual"))  # Provide only the loader-owned options.
            loaded = ui_50000.load_distributed_shards(args, allocations, source_commit)  # Validate the complete synthetic artifact set.
            self.assertEqual(len(loaded), len(allocations))  # Require every formal worker exactly once.
            missing_path = root / f"{allocations[-1][1]:02d}-{allocations[-1][0]}-r{allocations[-1][2]}.json"  # Select one test-owned terminal artifact.
            missing_path.unlink()  # Model an interrupted or failed artifact upload inside the disposable directory.
            with self.assertRaisesRegex(RuntimeError, "inventory mismatch"):  # Require a bounded fail-closed diagnostic.
                ui_50000.load_distributed_shards(args, allocations, source_commit)  # Reject the incomplete corpus without repair work.

    # Prove an exact filename cannot smuggle a foreign source or altered range into the aggregate.
    def test_distributed_shards_reject_foreign_identity(self):
        allocations = ui_50000.allocate_cycles(list(ui_50000.GAME_IDS), 50_000, 4, set(), 4)  # Build the immutable formal assignment.
        source_commit = "d" * 40  # Use one valid expected full commit identity.
        with tempfile.TemporaryDirectory() as temporary_directory:  # Own and clean the downloaded-artifact simulation.
            root = Path(temporary_directory)  # Resolve the test-owned shard root.
            self.write_distributed_corpus(root, allocations, source_commit)  # Persist the exact inventory first.
            game_id, game_index, replica_index, quota, cycle_start = allocations[0]  # Select one deterministic worker identity.
            path = root / f"{game_index:02d}-{game_id}-r{replica_index}.json"  # Resolve that worker's expected filename.
            foreign = {"source_commit": "e" * 40, "game": game_id, "game_index": game_index, "replica_index": replica_index, "quota": quota, "global_cycle_start": cycle_start, "global_cycle_end": cycle_start + quota - 1, "requirements": list(ui_50000.REQUIREMENT_IDS)}  # Preserve every field except the immutable source.
            path.write_text(json.dumps(foreign), encoding="utf-8")  # Replace only the disposable candidate with foreign evidence.
            args = argparse.Namespace(shard_report_root=str(root), evidence_root=str(root / "visual"))  # Provide only the loader-owned options.
            with self.assertRaisesRegex(RuntimeError, "identity mismatch"):  # Require a precise fail-closed diagnostic.
                ui_50000.load_distributed_shards(args, allocations, source_commit)  # Reject foreign-source evidence without browser work.

    # Prove the browser-free controller accepts exactly 50,000 completed cycles only when every formal gate is present.
    def test_distributed_aggregate_accounts_for_exact_terminal_corpus(self):
        allocations = ui_50000.allocate_cycles(list(ui_50000.GAME_IDS), 50_000, 4, set(), 4)  # Build the immutable formal assignment.
        completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ui_50000.ROOT, capture_output=True, text=True, check=True)  # Resolve the test checkout's full public commit identity.
        source_commit = completed.stdout.strip().lower()  # Normalize exact provenance for the aggregate guard.
        with tempfile.TemporaryDirectory() as temporary_directory:  # Own and clean the complete downloaded-artifact simulation.
            root = Path(temporary_directory)  # Resolve the disposable aggregate root.
            shard_root = root / "shards"  # Separate terminal JSON from screenshots.
            evidence_root = root / "visual"  # Separate screenshots from aggregate reports.
            shard_root.mkdir(parents=True, exist_ok=True)  # Create the test-owned shard directory.
            self.write_distributed_corpus(shard_root, allocations, source_commit, evidence_root)  # Persist a complete passing 33-worker corpus.
            report_path = root / "aggregate.json"  # Resolve the test-owned terminal aggregate.
            args = argparse.Namespace(aggregate_only=True, allocation_index=None, source_commit=source_commit, only_games="", replicate_games="", total_cycles=50_000, roulette_replicas=4, game_replicas=4, shard_report_root=str(shard_root), evidence_root=str(evidence_root), report=str(report_path), parallel=4)  # Provide every aggregate-owned immutable option.
            exit_code = asyncio.run(ui_50000.run_all(args))  # Execute aggregate accounting without importing or launching Playwright.
            report = json.loads(report_path.read_text(encoding="utf-8"))  # Read the generated terminal evidence.
            self.assertEqual(exit_code, 0)  # Require the aggregate controller to accept the complete corpus.
            self.assertEqual(report["status"], "PASS")  # Require every universal gate to resolve green.
            self.assertEqual(report["attempted_cycles"], 50_000)  # Require exact unique attempted-cycle accounting.
            self.assertEqual(report["completed_cycles"], 50_000)  # Require exact terminal completion accounting.
            self.assertTrue(report["assignment"]["no_gaps_or_duplicates"])  # Require the immutable global range proof.
            self.assertTrue(report["visuals_complete"])  # Require all 132 unique governed screenshots.


# Run the focused module directly for local diagnosis.
if __name__ == "__main__":
    unittest.main()  # Return unittest's standard terminal status.
