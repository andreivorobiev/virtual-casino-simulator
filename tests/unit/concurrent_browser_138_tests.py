"""Listener-free TEST-142 proofs for the issue #225 exact-138 browser qualification."""

import asyncio  # Exercise the asynchronous synchronized barrier without launching a browser.
from collections import Counter  # Match the grouped production diagnostic counter schema.
import json  # Persist one external exact-source pool preflight fixture.
import os  # Patch only the explicit disposable marker for boundary tests.
import tempfile  # Own and clean external listener-free evidence files.
import tomllib  # Parse optional dependency groups for listener-free workflow policy proof.
import unittest  # Integrate focused proofs with the repository test runner.
from types import SimpleNamespace  # Build small aggregate-only barrier fixtures.
from unittest import mock  # Isolate current-catalog and environment scenarios.

from tests import concurrent_browser_138  # Exercise the public qualification planner and aggregator.


# Prove the exact-user planner, barrier, aggregation, privacy, and workflow contracts.
class ConcurrentBrowser138Tests(unittest.TestCase):
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
            "completed_phases": list(concurrent_browser_138.FORMAL_PHASES),  # Model complete fixed-phase evidence.
            "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}},
        }

    # Prove exactly 138 users give every current registered game three deterministic assignments.
    def test_exact_current_catalog_plan_is_balanced(self):
        # Build the owner-authorized current-catalog plan.
        plan = concurrent_browser_138.build_assignment_plan()
        # Count assignments by current public game id.
        counts = {}
        # Visit every deterministic assignment.
        for row in plan:
            # Increment the public game count.
            counts[row["game_id"]] = counts.get(row["game_id"], 0) + 1
        # Require exactly one row per synthetic user.
        self.assertEqual(len(plan), 138)
        # Require contiguous unique ordinals without account data.
        self.assertEqual([row["user_index"] for row in plan], list(range(138)))
        # Require every registered game to receive exactly the owner-selected floor.
        self.assertEqual(set(counts.values()), {3})

    # Prove the exact population remains coupled to the complete current catalog and three-user floor.
    def test_current_catalog_rejects_any_shortened_population(self):
        # Pin the current registered catalog size so future additions require an explicit test update.
        self.assertEqual(len(concurrent_browser_138.GAME_IDS), 46)
        # Require the formal profile to reject even a one-user reduction before resource creation.
        with self.assertRaisesRegex(ValueError, r"requires exactly 138 users"):
            # Attempt to weaken the owner-authorized population.
            concurrent_browser_138.build_assignment_plan(user_count=137)

    # Prove every asynchronous participant waits until the controller releases the exact barrier.
    def test_start_barrier_releases_only_after_all_parties_arrive(self):
        # Exercise the production barrier on one isolated event loop.
        async def scenario():
            # Build a four-party listener-free barrier.
            barrier = concurrent_browser_138.StartBarrier(4)
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

    # Prove pre-barrier browser setup obeys the explicit admission bound.
    def test_setup_admission_bounds_pre_barrier_work(self):
        # Exercise the production helper with a deliberately small browser-free cap.
        async def scenario():
            # Use three slots so queuing is observable without heavy resources.
            admission = asyncio.Semaphore(3)
            # Mirror the aggregate-only production setup counters.
            counters = {"active_setup": 0, "peak_setup": 0}
            # Serialize the production counter mutations.
            counter_lock = asyncio.Lock()
            # Hold the first admitted cohort until bounded state is inspected.
            release = asyncio.Event()
            # Signal when the configured cap has been reached.
            cap_reached = asyncio.Event()

            # Model one admitted browser setup without opening Chromium.
            async def operation():
                # Observe the third active setup after the production helper accounts for it.
                if counters["active_setup"] == 3:
                    # Wake the test controller at the exact cap.
                    cap_reached.set()
                # Hold admitted work so queued operations cannot enter early.
                await release.wait()

            # Start more operations than the declared admission bound.
            tasks = [
                asyncio.create_task(
                    concurrent_browser_138.run_admitted_setup(
                        admission,
                        counters,
                        counter_lock,
                        operation,
                    )
                )
                for _ in range(12)
            ]
            # Wait until the first admitted cohort is fully active.
            await asyncio.wait_for(cap_reached.wait(), timeout=1)
            # Refuse any fourth concurrent pre-barrier setup.
            self.assertEqual(counters["active_setup"], 3)
            self.assertEqual(counters["peak_setup"], 3)
            # Release the cohort and allow every queued operation to complete.
            release.set()
            await asyncio.gather(*tasks)
            # Require complete active-accounting cleanup.
            self.assertEqual(counters["active_setup"], 0)
            self.assertEqual(counters["peak_setup"], 3)

        # Run the listener-free admission scenario.
        asyncio.run(scenario())

    # Prove the formal profile reuses the rendered gate and applies one bounded absolute deadline.
    def test_formal_login_reuses_rendered_gate_with_bounded_deadline(self):
        # Exercise only the wrapper contract without opening Chromium.
        async def scenario():
            # Build one fixed aggregate observer spy.
            observer = mock.Mock()
            # Replace the shared rendered-login helper with one awaitable spy.
            with mock.patch.object(concurrent_browser_138.ui_50000, "login_through_ui", new=mock.AsyncMock()) as login:  # Replace the browser helper with one awaitable spy.
                # Submit one already-rendered form through the formal wrapper.
                await concurrent_browser_138.login_from_rendered_gate("page", "http://127.0.0.1", {"email": "synthetic@example.test", "password": "not-persisted"}, "en-US", Counter(), observer)
                # Refuse the failed-run redundant navigation and preserve the fixed 90-second ceiling.
                login.assert_awaited_once_with(
                    "page",  # Preserve the already-rendered page.
                    "http://127.0.0.1",  # Preserve the inert public base URL argument.
                    {"email": "synthetic@example.test", "password": "not-persisted"},  # Preserve one in-memory synthetic user.
                    "en-US",  # Preserve the fixed locale argument.
                    mock.ANY,  # Accept the task-local aggregate activation counter.
                    navigate=False,  # Refuse the synchronized second navigation.
                    deadline_ms=90_000,  # Require the bounded formal absolute deadline.
                    phase_observer=observer,  # Forward the fixed aggregate phase observer.
                )

        # Run the listener-free wrapper proof.
        asyncio.run(scenario())

    # Prove Pai Gow waits for deterministic initial-deal readiness before pointer activation.
    def test_pai_gow_driver_waits_for_deal_readiness(self):
        # Exercise the production driver with browser-free awaitable spies.
        async def scenario():
            # Preserve the exact order of readiness and pointer operations.
            events = []

            # Record one fixed readiness selector.
            async def wait_any_enabled(_page, selectors):
                # Append only the public selector under test.
                events.append(("wait", selectors[0]))

            # Record one fixed pointer selector.
            async def click_control(_page, selector, _activated_counts):
                # Append only the public selector under test.
                events.append(("click", selector))

            # Replace browser primitives while retaining the production branch.
            with (
                mock.patch.object(concurrent_browser_138.ui_50000, "wait_any_enabled", new=wait_any_enabled),  # Observe fixed readiness checks.
                mock.patch.object(concurrent_browser_138.ui_50000, "click_control", new=click_control),  # Observe fixed pointer actions.
                mock.patch.object(concurrent_browser_138.ui_50000, "inventory_controls", new=mock.AsyncMock()),  # Avoid browser inventory work.
            ):
                # Complete exactly one Pai Gow visible action.
                handled = await concurrent_browser_138.play_catalog_gap_ui(
                    object(),
                    "pai_gow_poker",
                    0,
                    Counter(),
                    Counter(),
                )
            # Require the production branch to own this catalog game.
            self.assertTrue(handled)
            # Require readiness before deal, house-way readiness before settlement, and terminal deal readiness.
            self.assertEqual(
                events,  # Compare the complete recorded readiness/action sequence.
                [
                    ("wait", '[data-action="deal"]'),  # Require initial readiness.
                    ("click", '[data-action="deal"]'),  # Commit the ready initial deal.
                    ("wait", '[data-action="house-way"]'),  # Require the rendered legal arrangement.
                    ("click", '[data-action="house-way"]'),  # Settle through the ready arrangement.
                    ("wait", '[data-action="deal"]'),  # Require terminal next-deal readiness.
                ],
            )

        # Run the browser-free deterministic readiness proof.
        asyncio.run(scenario())

    # Prove ledger evidence filters by player before the bounded row limit.
    def test_isolation_uses_player_scoped_ledger_routes(self):
        # Build the exact formal synthetic population without real account identifiers.
        users = [{"user_id": f"user-{index:03d}", "player_id": f"player-{index:03d}"} for index in range(concurrent_browser_138.USER_COUNT)]  # Build one deterministic public identity pair per formal user.

        # Model only the two bounded evidence routes used after browser cleanup.
        class FakeClient:
            # Initialize one call inventory for route-scope assertions.
            def __init__(self):
                # Retain only public request paths.
                self.paths = []

            # Return deterministic player state and ledger rows.
            def call(self, path):
                # Preserve the public path for filter-before-limit proof.
                self.paths.append(path)
                # Resolve the Admin state route.
                if path.startswith("/api/v2/admin/users/"):
                    # Resolve the public synthetic user segment before its state suffix.
                    user_id = path.rsplit("/", 2)[1]
                    # Derive the synthetic ordinal from the public test id.
                    ordinal = int(user_id.rsplit("-", 1)[1])
                    # Return the matching player and one nonnegative fake-money balance.
                    return {"player_id": f"player-{ordinal:03d}", "token_balance": 100}
                # Resolve the player-scoped bounded ledger route.
                if path.startswith("/api/v1/players/"):
                    # Derive the synthetic player id from the path.
                    player_id = path.split("/", 5)[4]
                    # Return one unique gameplay row for this player.
                    return {
                        "ledger": [  # Return the standard bounded ledger collection.
                            {
                                "ledger_id": f"ledger-{player_id}",  # Preserve one unique immutable row identity.
                                "transaction_type": "BET",  # Mark the row as gameplay rather than setup grant.
                                "game": "baccarat",  # Preserve one public game identity.
                                "details": {"ledger_action_key": f"action-{player_id}"},  # Preserve one unique action identity.
                            }
                        ]
                    }
                # Refuse any unexpected or global evidence route.
                raise AssertionError(f"unexpected evidence path: {path}")

        # Collect the production aggregate through the browser-free fake client.
        client = FakeClient()
        evidence = concurrent_browser_138.collect_isolation_evidence(client, users)
        # Require one gameplay-ledger row for every synthetic player beyond the global hundred-row cap.
        self.assertEqual(evidence["users_with_gameplay_ledger"], 138)
        # Require no duplicate player, ledger, or action identities.
        self.assertEqual(evidence["duplicate_player_id_count"], 0)
        self.assertEqual(evidence["duplicate_ledger_id_count"], 0)
        self.assertEqual(evidence["duplicate_action_key_count"], 0)
        # Reject the global Admin ledger route that filtered only after its hundred-row cap.
        self.assertFalse(any(path.startswith("/api/v1/admin/ledger") for path in client.paths))
        # Require exactly one player-scoped bounded ledger request per synthetic account.
        self.assertEqual(sum(path.startswith("/api/v1/players/") and path.endswith("/ledger?limit=100") for path in client.paths), 138)

    # Prove every accepted governed-run catalog gap has a bounded visible driver.
    def test_catalog_gap_drivers_cover_all_fifteen_games(self):
        # Pin the exact missing-game set from the accepted failed evidence.
        expected_games = {
            "boule",
            "coin_pusher",
            "color_wheel",
            "daily_draw_lab",
            "faro",
            "four_card_poker",
            "lucky_grid",
            "marble_race",
            "mississippi_stud",
            "pachinko",
            "pai_gow_poker",
            "pattern_draw",
            "poker_dice",
            "teen_patti",
            "trente_et_quarante",
        }
        # Require the fail-closed registry to cover exactly those fifteen games.
        self.assertEqual(set(concurrent_browser_138.CATALOG_GAP_GAME_IDS), expected_games)

        # Exercise every branch with awaitable browser-free UI spies.
        async def scenario():
            # Replace only browser primitives while retaining production branch selection.
            with (
                mock.patch.object(
                    concurrent_browser_138,
                    "select_visible_controls",
                    new=mock.AsyncMock(),
                ),
                mock.patch.object(
                    concurrent_browser_138.ui_50000,
                    "click_control",
                    new=mock.AsyncMock(),
                ),
                mock.patch.object(
                    concurrent_browser_138.ui_50000,
                    "wait_any_enabled",
                    new=mock.AsyncMock(),
                ),
                mock.patch.object(
                    concurrent_browser_138.ui_50000,
                    "terminal_action",
                    new=mock.AsyncMock(),
                ),
                mock.patch.object(
                    concurrent_browser_138.ui_50000,
                    "inventory_controls",
                    new=mock.AsyncMock(),
                ) as inventory,
            ):
                # Select every former gap driver once.
                for game_id in sorted(expected_games):
                    # Require a concrete production branch and terminal control inventory.
                    handled = await concurrent_browser_138.play_catalog_gap_ui(
                        object(),
                        game_id,
                        0,
                        Counter(),
                        Counter(),
                    )
                    self.assertTrue(handled, game_id)
                # Every bounded driver must finish with one rendered-control inventory.
                self.assertEqual(inventory.await_count, len(expected_games))

        # Run the branch-completeness probe without Chromium.
        asyncio.run(scenario())

    # Prove expected anonymous current-user probes are ignored only before login.
    def test_pre_auth_diagnostics_ignore_only_expected_me_probes(self):
        # Store browser callbacks without creating a browser page.
        class FakePage:
            # Initialize one event-name-to-callback map.
            def __init__(self):
                # Preserve only the listener functions under test.
                self.callbacks = {}

            # Match Playwright's event-registration surface.
            def on(self, event_name, callback):
                # Retain the callback for deterministic direct invocation.
                self.callbacks[event_name] = callback

        # Model the exact browser console error emitted for a rejected resource request.
        class FakeMessage:
            # Mark the message as a browser error.
            type = "error"
            # Match Playwright's stable 401 console text.
            text = "Failed to load resource: the server responded with a status of 401 (Unauthorized)"

        # Model the request method used by the anonymous current-user probe.
        class FakeRequest:
            # Current-user hydration is read-only.
            method = "GET"

        # Model the protected current-user response read by the listener.
        class FakeResponse:
            # Keep the origin synthetic and query-free.
            url = "https://casino.test/api/v2/me"
            # Represent the expected anonymous result.
            status = 401
            # Expose the request object through Playwright's response surface.
            request = FakeRequest()

        # Track whether authoritative rendered login has completed.
        authentication_state = {"authenticated": False}
        # Match the grouped diagnostic mapping used by the real runner.
        diagnostics = {
            "console_errors": Counter(),
            "page_errors": Counter(),
            "http_failures": Counter(),
        }
        # Register the real diagnostic listeners against a browser-free page double.
        page = FakePage()
        concurrent_browser_138.ui_50000.attach_page_diagnostics(
            page,
            diagnostics,
            anonymous_probe_active=lambda: not authentication_state["authenticated"],
        )
        # Repeated anonymous probes before login must not create false failures.
        page.callbacks["console"](FakeMessage())
        page.callbacks["response"](FakeResponse())
        page.callbacks["console"](FakeMessage())
        page.callbacks["response"](FakeResponse())
        self.assertEqual(diagnostics["console_errors"], Counter())
        self.assertEqual(diagnostics["http_failures"], Counter())
        # The same failures after authentication must remain visible and fail closed.
        authentication_state["authenticated"] = True
        page.callbacks["console"](FakeMessage())
        page.callbacks["response"](FakeResponse())
        self.assertEqual(sum(diagnostics["console_errors"].values()), 1)
        self.assertEqual(diagnostics["http_failures"]["401 GET /api/v2/me"], 1)

    # Prove a complete current-catalog result passes without retaining user-level evidence.
    def test_aggregate_accepts_complete_sanitized_result(self):
        # Build the owner-authorized exact-138 plan.
        games = concurrent_browser_138.GAME_IDS
        # Patch only the catalog used by aggregate acceptance.
        with mock.patch.object(concurrent_browser_138, "GAME_IDS", games):
            # Build exact deterministic assignments.
            assignments = concurrent_browser_138.build_assignment_plan(games)
            # Build one sanitized passing row per assignment.
            results = [self.passing_result(row) for row in assignments]
            # Model the exact synchronized barrier terminal state.
            barrier = SimpleNamespace(ready=138, peak_ready=138)
            # Provide complete aggregate-only isolation evidence.
            isolation = {
                "unique_player_count": 138,
                "duplicate_player_id_count": 0,
                "matching_player_count": 138,
                "nonnegative_balance_count": 138,
                "users_with_gameplay_ledger": 138,
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
            report = concurrent_browser_138.aggregate_results(
                assignments,
                results,
                barrier,
                {"active_setup": 0, "peak_setup": 12, "active_gameplay": 0, "peak_gameplay": 73},
                isolation,
                pool,
                pool_preflight,
                "a" * 40,
                12.5,
            )
        # Require every pre-cleanup acceptance gate to pass.
        self.assertEqual(report["status"], "PASS")
        # Require the permanent browser identity and exact source.
        self.assertEqual(report["qualification"]["test_id"], "BR-CONCURRENT-138-001")
        # Require exact aggregate peak concurrency.
        self.assertEqual(report["counts"]["peak_gameplay"], 73)
        # Require every fixed phase to report exact aggregate completion.
        self.assertEqual(set(report["phase_counts"]["completed"].values()), {138})
        # Require the passing aggregate to retain zero failures in every fixed phase bucket.
        self.assertEqual(set(report["phase_counts"]["failed"].values()), {0})
        # Reject accidental user-level result persistence.
        self.assertNotIn("results", report)
        # Reject credential-shaped fields anywhere in the public schema.
        self.assertNotIn("password", str(report).lower())
        # Reject token-shaped fields anywhere in the public schema.
        self.assertNotIn("token", str(report).lower())

    # Prove one browser error and one duplicate settlement identity fail the aggregate.
    def test_aggregate_rejects_browser_and_isolation_failures(self):
        # Build one compatible exact assignment.
        games = concurrent_browser_138.GAME_IDS
        # Patch only the aggregate catalog.
        with mock.patch.object(concurrent_browser_138, "GAME_IDS", games):
            # Build exact deterministic assignments.
            assignments = concurrent_browser_138.build_assignment_plan(games)
            # Build passing task rows.
            results = [self.passing_result(row) for row in assignments]
            # Inject one bounded browser diagnostic.
            results[0]["browser_diagnostics"]["page_errors"] = {"synthetic failure": 1}
            # Model exact barrier completion.
            barrier = SimpleNamespace(ready=138, peak_ready=138)
            # Inject one duplicated ledger identity.
            isolation = {
                "unique_player_count": 138,
                "duplicate_player_id_count": 0,
                "matching_player_count": 138,
                "nonnegative_balance_count": 138,
                "users_with_gameplay_ledger": 138,
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
            report = concurrent_browser_138.aggregate_results(
                assignments,
                results,
                barrier,
                {"active_setup": 0, "peak_setup": 12, "active_gameplay": 0, "peak_gameplay": 138},
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
            self.assertEqual(concurrent_browser_138.load_pool_preflight(path, "c" * 40), evidence)
            # Require foreign-head evidence refusal.
            with self.assertRaisesRegex(ValueError, "source does not match"):
                # Attempt to reuse the packet for another commit.
                concurrent_browser_138.load_pool_preflight(path, "d" * 40)

    # Prove the formal runner requires an explicit external disposable data root.
    def test_runtime_boundary_rejects_source_owned_data(self):
        # Patch the selected data root to the repository's normal data directory.
        with mock.patch.dict(os.environ, {"CASINO_225_DISPOSABLE": "1", "CASINO_DATA_DIR": "data"}, clear=False):
            # Patch the already-imported configuration value to the forbidden source child.
            with mock.patch("casino.config.DATA_DIR", concurrent_browser_138.ui_50000.ROOT / "data"):
                # Require refusal before any state mutation.
                with self.assertRaisesRegex(RuntimeError, "outside the source checkout"):
                    # Validate only the safety boundary.
                    concurrent_browser_138.validate_runtime_boundary()

    # Prove the hosted profile is opt-in, exact, sequential, and artifact-retaining.
    def test_workflow_keeps_formal_profile_explicit_and_exact(self):
        # Resolve the repository-owned browser workflow.
        workflow_path = concurrent_browser_138.ui_50000.ROOT / ".github" / "workflows" / "browser-tests.yml"
        # Read declarative workflow text without contacting GitHub.
        workflow = workflow_path.read_text(encoding="utf-8")
        # Require exactly one dispatch input plus one job identity.
        self.assertEqual(workflow.count("concurrent_browser_138:"), 2)
        # Require one exact module invocation.
        self.assertEqual(workflow.count("python -m tests.concurrent_browser_138"), 1)
        # Require an explicit disposable marker in the formal job.
        self.assertIn("CASINO_225_DISPOSABLE: 1", workflow)
        # Require an external runner-owned data root.
        self.assertIn("CASINO_DATA_DIR: ${{ runner.temp }}/casino-browser-138-data", workflow)
        # Require the Package B MySQL gate before the browser invocation.
        self.assertLess(
            workflow.index("python tests/run_tests.py --storage --mysql-migrations-live"),
            workflow.index("python -m tests.concurrent_browser_138"),
        )
        # Require terminal aggregate artifact upload on failure or success.
        self.assertIn("concurrent-browser-138-${{ github.sha }}", workflow)
        # Keep the expensive qualification outside ordinary pull-request execution.
        job = workflow.split("\n  concurrent_browser_138:\n", 1)[1]
        # Require explicit workflow-dispatch authorization.
        self.assertIn("inputs.concurrent_browser_138 == true", job)
        # Require the disposable MySQL preflight to install both connector and recovery groups.
        self.assertEqual(job.count('python -m pip install -e ".[mysql,recovery]"'), 1)
        # Reject the incomplete environment that reached TEST-141 without recovery crypto.
        self.assertNotIn('python -m pip install -e ".[mysql]"', job)
        # Resolve the canonical optional-dependency metadata without installing or opening a listener.
        pyproject_path = concurrent_browser_138.ui_50000.ROOT / "pyproject.toml"
        # Parse the exact checkout's dependency groups as inert TOML.
        project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        # Prove the installed recovery extra supplies the encryption backend required by TEST-141.
        self.assertIn("cryptography>=46,<50", project["project"]["optional-dependencies"]["recovery"])


# Run the focused listener-free suite directly.
if __name__ == "__main__":
    # Execute standard unittest discovery semantics.
    unittest.main()
