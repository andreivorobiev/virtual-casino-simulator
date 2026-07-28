"""Listener-free TEST-142 proofs for the issue #225 exact-100 browser qualification."""

import asyncio  # Exercise the asynchronous synchronized barrier without launching a browser.
import json  # Persist one external exact-source pool preflight fixture.
import os  # Patch only the explicit disposable marker for boundary tests.
import tempfile  # Own and clean external listener-free evidence files.
import unittest  # Integrate focused proofs with the repository test runner.
from types import SimpleNamespace  # Build small aggregate-only barrier fixtures.
from unittest import mock  # Isolate current-catalog and environment scenarios.

from tests import concurrent_browser_100  # Exercise the public qualification planner and aggregator.


# Prove the exact-user planner, barrier, aggregation, privacy, and workflow contracts.
class ConcurrentBrowser100Tests(unittest.TestCase):
    # Build the issue-era thirty-game catalog used by the literal three-user floor.
    def thirty_games(self):
        # Return stable public test identifiers without depending on game implementation.
        return tuple(f"game_{index:02d}" for index in range(30))

    # Build one complete passing terminal result for a public game assignment.
    def passing_result(self, assignment):
        # Return no user, credential, token, cookie, path, process, or listener identity.
        return {
            "game_id": assignment["game_id"],
            "barrier_ready": True,
            "login_ok": True,
            "gameplay_ok": True,
            "context_closed": True,
            "login_seconds": 0.1,
            "play_seconds": 0.2,
            "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}},
        }

    # Prove exactly 100 users give every issue-era game at least three deterministic assignments.
    def test_exact_thirty_game_plan_is_balanced(self):
        # Build the literal issue-owned plan.
        plan = concurrent_browser_100.build_assignment_plan(self.thirty_games())
        # Count assignments by current public game id.
        counts = {}
        # Visit every deterministic assignment.
        for row in plan:
            # Increment the public game count.
            counts[row["game_id"]] = counts.get(row["game_id"], 0) + 1
        # Require exactly one row per synthetic user.
        self.assertEqual(len(plan), 100)
        # Require contiguous unique ordinals without account data.
        self.assertEqual([row["user_index"] for row in plan], list(range(100)))
        # Require the ten-game canonical prefix to receive four users.
        self.assertEqual(list(counts.values()).count(4), 10)
        # Require every remaining issue-era game to receive the literal floor of three.
        self.assertEqual(list(counts.values()).count(3), 20)

    # Prove current protected main fails before resource creation instead of weakening the issue floor.
    def test_current_catalog_exposes_exact_acceptance_arithmetic_blocker(self):
        # Pin the current registered catalog size so future additions require an explicit test update.
        self.assertEqual(len(concurrent_browser_100.GAME_IDS), 46)
        # Require a bounded aggregate-count diagnostic for the impossible exact-100 plan.
        with self.assertRaisesRegex(ValueError, r"requires 138 users \(46 games x 3\).*exactly 100"):
            # Attempt the unmodified formal current-catalog profile.
            concurrent_browser_100.build_assignment_plan()

    # Prove every asynchronous participant waits until the controller releases the exact barrier.
    def test_start_barrier_releases_only_after_all_parties_arrive(self):
        # Exercise the production barrier on one isolated event loop.
        async def scenario():
            # Build a four-party listener-free barrier.
            barrier = concurrent_browser_100.StartBarrier(4)
            # Track task completion after release.
            completed = []

            # Arrive once and record only after release.
            async def worker(index):
                # Wait at the production barrier.
                await barrier.wait()
                # Record post-release completion order.
                completed.append(index)

            # Start every independent synthetic task.
            tasks = [asyncio.create_task(worker(index)) for index in range(4)]
            # Wait until the exact population has arrived.
            await asyncio.wait_for(barrier.all_ready.wait(), timeout=1)
            # Require no task to pass before controller release.
            self.assertEqual(completed, [])
            # Require exact ready and peak accounting.
            self.assertEqual((barrier.ready, barrier.peak_ready), (4, 4))
            # Release every waiting task once.
            barrier.release.set()
            # Wait for exact terminal completion.
            await asyncio.gather(*tasks)
            # Require every task to complete once.
            self.assertEqual(sorted(completed), [0, 1, 2, 3])

        # Run the listener-free asynchronous scenario.
        asyncio.run(scenario())

    # Prove a complete thirty-game result passes without retaining user-level evidence.
    def test_aggregate_accepts_complete_sanitized_result(self):
        # Build the mathematically compatible exact-100 plan.
        games = self.thirty_games()
        # Patch only the catalog used by aggregate acceptance.
        with mock.patch.object(concurrent_browser_100, "GAME_IDS", games):
            # Build exact deterministic assignments.
            assignments = concurrent_browser_100.build_assignment_plan(games)
            # Build one sanitized passing row per assignment.
            results = [self.passing_result(row) for row in assignments]
            # Model the exact synchronized barrier terminal state.
            barrier = SimpleNamespace(ready=100, peak_ready=100)
            # Provide complete aggregate-only isolation evidence.
            isolation = {
                "unique_player_count": 100,
                "duplicate_player_id_count": 0,
                "matching_player_count": 100,
                "nonnegative_balance_count": 100,
                "users_with_gameplay_ledger": 100,
                "duplicate_ledger_id_count": 0,
                "duplicate_action_key_count": 0,
            }
            # Provide a clean fixed-cardinality MySQL snapshot.
            pool = {
                "provider": "mysql",
                "available": True,
                "capacity": 2,
                "in_use": 0,
                "idle": 2,
                "waiting": 0,
                "physical_created": 2,
                "reused": 198,
                "discarded": 0,
                "wait_count": 98,
                "timeout_count": 0,
                "rollback_cleanup": 0,
                "connector_error": 0,
                "wait_buckets_ms": {"1": 10, "5": 80, "25": 8, "100": 0, "500": 0, ">500": 0},
            }
            # Reuse the same fixed pool evidence with the exact four governed measurement rows.
            pool_preflight = {
                "source_commit": "a" * 40,
                "measurements": [
                    {"concurrency": concurrency, "p50_ms": 1.0, "p95_ms": 2.0, "throughput_rps": 10.0, "errors": 0}
                    for concurrency in (1, 2, 4, 8)
                ],
                "pool": {key: value for key, value in pool.items() if key not in {"provider", "available"}},
            }
            # Aggregate the exact-source terminal evidence.
            report = concurrent_browser_100.aggregate_results(
                assignments,
                results,
                barrier,
                {"active_gameplay": 0, "peak_gameplay": 73},
                isolation,
                pool,
                pool_preflight,
                "a" * 40,
                12.5,
            )
        # Require every pre-cleanup acceptance gate to pass.
        self.assertEqual(report["status"], "PASS")
        # Require the permanent browser identity and exact source.
        self.assertEqual(report["qualification"]["test_id"], "BR-CONCURRENT-100-001")
        # Require exact aggregate peak concurrency.
        self.assertEqual(report["counts"]["peak_gameplay"], 73)
        # Reject accidental user-level result persistence.
        self.assertNotIn("results", report)
        # Reject credential-shaped fields anywhere in the public schema.
        self.assertNotIn("password", str(report).lower())
        # Reject token-shaped fields anywhere in the public schema.
        self.assertNotIn("token", str(report).lower())

    # Prove one browser error and one duplicate settlement identity fail the aggregate.
    def test_aggregate_rejects_browser_and_isolation_failures(self):
        # Build one compatible exact assignment.
        games = self.thirty_games()
        # Patch only the aggregate catalog.
        with mock.patch.object(concurrent_browser_100, "GAME_IDS", games):
            # Build exact deterministic assignments.
            assignments = concurrent_browser_100.build_assignment_plan(games)
            # Build passing task rows.
            results = [self.passing_result(row) for row in assignments]
            # Inject one bounded browser diagnostic.
            results[0]["browser_diagnostics"]["page_errors"] = {"synthetic failure": 1}
            # Model exact barrier completion.
            barrier = SimpleNamespace(ready=100, peak_ready=100)
            # Inject one duplicated ledger identity.
            isolation = {
                "unique_player_count": 100,
                "duplicate_player_id_count": 0,
                "matching_player_count": 100,
                "nonnegative_balance_count": 100,
                "users_with_gameplay_ledger": 100,
                "duplicate_ledger_id_count": 1,
                "duplicate_action_key_count": 0,
            }
            # Aggregate against disposable JSON storage.
            pool_preflight = {
                "source_commit": "b" * 40,
                "measurements": [
                    {"concurrency": concurrency, "p50_ms": 1.0, "p95_ms": 2.0, "throughput_rps": 10.0, "errors": 0}
                    for concurrency in (1, 2, 4, 8)
                ],
                "pool": {
                    "capacity": 2,
                    "in_use": 0,
                    "idle": 2,
                    "waiting": 0,
                    "physical_created": 2,
                    "reused": 50,
                    "discarded": 0,
                    "wait_count": 2,
                    "timeout_count": 0,
                    "rollback_cleanup": 0,
                    "connector_error": 0,
                    "wait_buckets_ms": {"1": 1, "5": 1, "25": 0, "100": 0, "500": 0, ">500": 0},
                },
            }
            report = concurrent_browser_100.aggregate_results(
                assignments,
                results,
                barrier,
                {"active_gameplay": 0, "peak_gameplay": 100},
                isolation,
                {"provider": "json", "available": False},
                pool_preflight,
                "b" * 40,
                10,
            )
        # Require the overall qualification to fail.
        self.assertEqual(report["status"], "FAIL")
        # Require browser diagnostics to remain an independent red gate.
        self.assertFalse(report["gates"]["browser_diagnostics"])
        # Require duplicate settlement evidence to keep isolation red.
        self.assertFalse(report["gates"]["isolation"])

    # Prove exact-source fixed-cardinality pool evidence is accepted and foreign evidence is rejected.
    def test_pool_preflight_requires_exact_source_and_fixed_schema(self):
        # Build one complete passing Package B evidence packet.
        evidence = {
            "source_commit": "c" * 40,
            "measurements": [
                {"concurrency": concurrency, "p50_ms": 1.0, "p95_ms": 2.0, "throughput_rps": 10.0, "errors": 0}
                for concurrency in (1, 2, 4, 8)
            ],
            "pool": {
                "capacity": 2,
                "in_use": 0,
                "idle": 2,
                "waiting": 0,
                "physical_created": 2,
                "reused": 50,
                "discarded": 0,
                "wait_count": 2,
                "timeout_count": 0,
                "rollback_cleanup": 0,
                "connector_error": 0,
                "wait_buckets_ms": {"1": 1, "5": 1, "25": 0, "100": 0, "500": 0, ">500": 0},
            },
        }
        # Own one external evidence directory that cannot overlap source control.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the disposable evidence file.
            path = os.path.join(temporary_directory, "pool.json")
            # Persist stable exact-source JSON.
            with open(path, "w", encoding="utf-8") as handle:
                # Write only the test-owned fixture.
                json.dump(evidence, handle)
            # Require exact-source acceptance.
            self.assertEqual(concurrent_browser_100.load_pool_preflight(path, "c" * 40), evidence)
            # Require foreign-head evidence refusal.
            with self.assertRaisesRegex(ValueError, "source does not match"):
                # Attempt to reuse the packet for another commit.
                concurrent_browser_100.load_pool_preflight(path, "d" * 40)

    # Prove the formal runner requires an explicit external disposable data root.
    def test_runtime_boundary_rejects_source_owned_data(self):
        # Patch the selected data root to the repository's normal data directory.
        with mock.patch.dict(os.environ, {"CASINO_225_DISPOSABLE": "1", "CASINO_DATA_DIR": "data"}, clear=False):
            # Patch the already-imported configuration value to the forbidden source child.
            with mock.patch("casino.config.DATA_DIR", concurrent_browser_100.ui_50000.ROOT / "data"):
                # Require refusal before any state mutation.
                with self.assertRaisesRegex(RuntimeError, "outside the source checkout"):
                    # Validate only the safety boundary.
                    concurrent_browser_100.validate_runtime_boundary()

    # Prove the hosted profile is opt-in, exact, sequential, and artifact-retaining.
    def test_workflow_keeps_formal_profile_explicit_and_exact(self):
        # Resolve the repository-owned browser workflow.
        workflow_path = concurrent_browser_100.ui_50000.ROOT / ".github" / "workflows" / "concurrent-browser-100.yml"
        # Read declarative workflow text without contacting GitHub.
        workflow = workflow_path.read_text(encoding="utf-8")
        # Require exactly one dispatch input plus one job identity.
        self.assertEqual(workflow.count("concurrent_browser_100:"), 2)
        # Require one exact module invocation.
        self.assertEqual(workflow.count("python -m tests.concurrent_browser_100"), 1)
        # Require an explicit disposable marker in the formal job.
        self.assertIn("CASINO_225_DISPOSABLE: 1", workflow)
        # Require an external runner-owned data root.
        self.assertIn("CASINO_DATA_DIR: ${{ runner.temp }}/casino-browser-100-data", workflow)
        # Require the Package B MySQL gate before the browser invocation.
        self.assertLess(
            workflow.index("python tests/run_tests.py --storage --mysql-migrations-live"),
            workflow.index("python -m tests.concurrent_browser_100"),
        )
        # Require terminal aggregate artifact upload on failure or success.
        self.assertIn("concurrent-browser-100-${{ github.sha }}", workflow)
        # Keep the expensive qualification outside ordinary pull-request execution.
        job = workflow.split("\n  concurrent_browser_100:\n", 1)[1]
        # Require explicit workflow-dispatch authorization.
        self.assertIn("inputs.concurrent_browser_100 == true", job)


# Run the focused listener-free suite directly.
if __name__ == "__main__":
    # Execute standard unittest discovery semantics.
    unittest.main()
