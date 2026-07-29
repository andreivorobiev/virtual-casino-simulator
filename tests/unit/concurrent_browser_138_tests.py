"""Listener-free TEST-142 proofs for the issue #225 exact-138 browser qualification."""

import asyncio  # Exercise the asynchronous synchronized barrier without launching a browser.
import ast  # Parse production route decorators without importing optional application dependencies.
from collections import Counter  # Match the grouped production diagnostic counter schema.
from concurrent.futures import ThreadPoolExecutor  # Drive deterministic concurrent autoplay registry transactions.
import copy  # Return independent fake registry snapshots like JSON deserialization.
import json  # Persist one external exact-source pool preflight fixture.
import os  # Patch only the explicit disposable marker for boundary tests.
from pathlib import Path  # Resolve the tracked application source independently from the runner working directory.
import re  # Match concrete browser paths against production route patterns.
import tempfile  # Own and clean external listener-free evidence files.
import time  # Widen fake registry read/write races for deterministic concurrency evidence.
import tomllib  # Parse optional dependency groups for listener-free workflow policy proof.
import unittest  # Integrate focused proofs with the repository test runner.
from types import SimpleNamespace  # Build small aggregate-only barrier fixtures.
from unittest import mock  # Isolate current-catalog and environment scenarios.

from casino.core import autoplay  # Exercise the synchronized server-side autoplay registry.
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
            "game_id": assignment["game_id"],  # Preserve the public assigned game.
            "barrier_ready": True,  # Model exact synchronized readiness.
            "login_ok": True,  # Model successful rendered authentication.
            "gameplay_ok": True,  # Model one complete visible action.
            "ledger_expectation": "wager_required",  # Require one assigned-game player-scoped row.
            "context_closed": True,  # Model terminal browser cleanup.
            "login_seconds": 0.1,  # Preserve one bounded successful login sample.
            "play_seconds": 0.2,  # Preserve one bounded successful gameplay sample.
            "completed_phases": list(concurrent_browser_138.FORMAL_PHASES),  # Model complete fixed-phase evidence.
            "completed_action_states": list(concurrent_browser_138.FORMAL_ACTION_STATES),  # Model complete fixed action-state evidence.
            "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}},  # Model clean grouped browser diagnostics.
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

    # Prove the formal operation deadline is task-local, absolute, and absent from ordinary profiles.
    def test_formal_operation_deadline_preserves_ordinary_timeouts(self):
        # Freeze monotonic time so the remaining formal window is deterministic.
        with mock.patch.object(concurrent_browser_138.ui_50000.time, "perf_counter", return_value=100.0):
            # Install one task-local ninety-second absolute deadline.
            token = concurrent_browser_138.ui_50000.FORMAL_OPERATION_DEADLINE.set(190.0)
            # Start protected context restoration.
            try:
                # Require the ordinary fifteen-second input to expand only to the remaining formal absolute window.
                self.assertEqual(concurrent_browser_138.ui_50000.operation_timeout_ms(15_000), 90_000)
            # Always restore the ordinary browser context.
            finally:
                # Remove only the test-owned deadline.
                concurrent_browser_138.ui_50000.FORMAL_OPERATION_DEADLINE.reset(token)
        # Require ordinary profiles to retain the exact caller-owned timeout after restoration.
        self.assertEqual(concurrent_browser_138.ui_50000.operation_timeout_ms(15_000), 15_000)

    # Prove the formal gameplay deadline is derived from hosted success evidence, rounded, and capped.
    def test_formal_gameplay_deadline_uses_documented_hosted_latency_policy(self):
        # Require the third-run p95/max plus fixed margins to round upward to two minutes.
        self.assertEqual(concurrent_browser_138.FORMAL_GAMEPLAY_DEADLINE_MS, 120_000)
        # Require p95-plus-thirty-seconds to own the current evidence bound.
        self.assertGreater(
            concurrent_browser_138.OBSERVED_GAMEPLAY_SUCCESS_P95_MS + concurrent_browser_138.FORMAL_GAMEPLAY_P95_MARGIN_MS,  # Compare the p95 evidence bound.
            concurrent_browser_138.OBSERVED_GAMEPLAY_SUCCESS_MAX_MS + concurrent_browser_138.FORMAL_GAMEPLAY_MAX_MARGIN_MS,  # Compare the maximum-tail bound.
        )
        # Require a future extreme observation to remain beneath the documented hard cap.
        self.assertEqual(
            concurrent_browser_138.derive_formal_gameplay_deadline_ms(p95_ms=200_000, maximum_ms=210_000),  # Derive from deliberately extreme observations.
            concurrent_browser_138.FORMAL_GAMEPLAY_DEADLINE_HARD_CAP_MS,  # Require the documented fixed ceiling.
        )
        # Refuse malformed policy inputs rather than silently shrinking the formal window.
        with self.assertRaisesRegex(ValueError, "nonnegative latency"):
            # Supply one invalid observed p95.
            concurrent_browser_138.derive_formal_gameplay_deadline_ms(p95_ms=-1)

    # Prove formal gameplay emits fixed navigation phases and returns one action-aware ledger expectation.
    def test_formal_gameplay_uses_one_deadline_and_fixed_navigation_phases(self):
        # Exercise the production orchestration without a listener or browser.
        async def scenario():
            # Preserve every fixed phase transition in caller order.
            events = []

            # Record only the fixed public phase and status.
            def observe_phase(name, status):
                # Append one deterministic phase transition.
                events.append((name, status))

            # Model the shared navigation helper and its fixed subphase callbacks.
            async def navigate(_page, _game_id, _activated_counts, _ordinal, phase_observer=None):
                # Require the governed caller to supply the fixed observer.
                self.assertIs(phase_observer, observe_phase)
                # Emit each public subphase exactly once.
                for phase in ("navigation_return_lobby", "navigation_lobby_ready", "navigation_route_open", "navigation_game_ready"):
                    # Record one subphase start.
                    phase_observer(phase, "started")
                    # Record one subphase completion.
                    phase_observer(phase, "completed")

            # Return one deterministic wagering action classification.
            async def play(_page, _game_id, _ordinal, _seen_counts, _activated_counts):
                # Require an active formal remaining-time override inside the driver.
                self.assertGreater(concurrent_browser_138.ui_50000.operation_timeout_ms(15_000), 15_000)
                # Model a rendered action that commits a wager.
                return "wager_required"

            # Replace only browser primitives while retaining the production deadline and phase controller.
            with (
                mock.patch.object(concurrent_browser_138.ui_50000, "navigate_to_game", new=navigate),
                mock.patch.object(concurrent_browser_138, "play_catalog_gap_ui", new=mock.AsyncMock(return_value=False)),
                mock.patch.object(concurrent_browser_138.ui_50000, "play_game_ui", new=play),
            ):
                # Run one non-gap assignment beneath the formal wrapper.
                expectation = await concurrent_browser_138.run_formal_gameplay(
                    object(),  # Use one inert browser-free page seam.
                    {"game_id": "craps", "user_index": 0},  # Select one unaffected inherited wagering driver.
                    Counter(),  # Collect no persistent rendered-control state.
                    Counter(),  # Collect no persistent activation state.
                    observe_phase,  # Record only fixed phase transitions.
                    lambda _name, _status: None,  # Accept only fixed action-state transitions.
                )
            # Require the action-aware evidence to remain fail-closed for a wager.
            self.assertEqual(expectation, "wager_required")
            # Require top-level navigation/action phases plus all four fixed navigation subphases.
            self.assertEqual(
                events,
                [
                    ("gameplay_navigation", "started"),  # Start aggregate navigation.
                    ("navigation_return_lobby", "started"),  # Start persistent Lobby activation.
                    ("navigation_return_lobby", "completed"),  # Complete persistent Lobby activation.
                    ("navigation_lobby_ready", "started"),  # Start Lobby render observation.
                    ("navigation_lobby_ready", "completed"),  # Complete Lobby render observation.
                    ("navigation_route_open", "started"),  # Start assigned route activation.
                    ("navigation_route_open", "completed"),  # Complete assigned route activation.
                    ("navigation_game_ready", "started"),  # Start module-ready observation.
                    ("navigation_game_ready", "completed"),  # Complete module-ready observation.
                    ("gameplay_navigation", "completed"),  # Complete aggregate navigation.
                    ("gameplay_action", "started"),  # Start the assigned visible action.
                    ("gameplay_action", "completed"),  # Complete the assigned visible action.
                ],
            )
            # Require task-local deadline cleanup after the formal operation returns.
            self.assertIsNone(concurrent_browser_138.ui_50000.FORMAL_OPERATION_DEADLINE.get())

        # Run the browser-free formal orchestration proof.
        asyncio.run(scenario())

    # Prove one exhausted formal gameplay window fails with a stable public diagnostic.
    def test_formal_gameplay_deadline_fails_closed(self):
        # Exercise the outer absolute bound without launching Chromium.
        async def scenario():
            # Model navigation that cannot complete inside the patched absolute window.
            async def stalled_navigation(*_args, **_kwargs):
                # Sleep beyond the test-owned one-millisecond deadline.
                await asyncio.sleep(0.02)

            # Patch only the bounded policy and stalled navigation primitive.
            with (
                mock.patch.object(concurrent_browser_138, "FORMAL_GAMEPLAY_DEADLINE_MS", 1),
                mock.patch.object(concurrent_browser_138.ui_50000, "navigate_to_game", new=stalled_navigation),
            ):
                # Require one fixed fail-closed diagnostic instead of a framework timeout.
                with self.assertRaisesRegex(AssertionError, "formal gameplay absolute deadline exceeded"):
                    # Run one browser-free assignment through the production deadline wrapper.
                    await concurrent_browser_138.run_formal_gameplay(
                        object(),  # Use one inert browser-free page seam.
                        {"game_id": "baccarat", "user_index": 0},  # Select one inherited driver.
                        Counter(),  # Collect no rendered-control state.
                        Counter(),  # Collect no pointer-activation state.
                        lambda _name, _status: None,  # Accept only fixed phase callbacks.
                        lambda _name, _status: None,  # Accept only fixed action-state callbacks.
                    )
            # Require task-local deadline cleanup after cancellation.
            self.assertIsNone(concurrent_browser_138.ui_50000.FORMAL_OPERATION_DEADLINE.get())

        # Run the bounded cancellation proof.
        asyncio.run(scenario())

    # Prove every diagnosed game uses a bounded ready/action/settlement driver without long-suite coverage work.
    def test_formal_bounded_drivers_cover_all_eleven_diagnosed_games(self):
        # Exercise every production branch with listener-free awaitable browser seams.
        async def scenario():
            # Preserve the exact public game set diagnosed from the terminal third-run artifact.
            expected_games = {
                "baccarat",  # Preserve one diagnosed coup driver.
                "big_six_wheel",  # Preserve one diagnosed input-and-spin driver.
                "bingo",  # Preserve one diagnosed card-purchase driver.
                "blackjack",  # Preserve one diagnosed decision driver.
                "double_bonus_video_poker",  # Preserve one diagnosed draw-poker driver.
                "jacks_or_better_video_poker",  # Preserve one diagnosed draw-poker driver.
                "keno",  # Preserve one diagnosed ticket driver.
                "multi_hand_video_poker",  # Preserve one diagnosed draw-poker driver.
                "roulette",  # Preserve one diagnosed wager-and-spin driver.
                "scratch_cards",  # Preserve one diagnosed card-settlement driver.
                "slots",  # Preserve one diagnosed spin driver.
            }
            # Require the production ownership set to stay exact.
            self.assertEqual(concurrent_browser_138.FORMAL_BOUNDED_GAME_IDS, expected_games)
            # Return the caller's first public selector as immediately actionable.
            async def wait_any_enabled(_page, selectors, *_args):
                # Preserve caller priority for deterministic decision tests.
                return selectors[0]

            # Return one inert rendered locator for every selector.
            async def enabled_locators(_page, _selector):
                # Preserve a nonempty actionable control surface.
                return [object()]

            # Exercise each diagnosed driver independently.
            for ordinal, game_id in enumerate(sorted(expected_games)):
                # Preserve only fixed action-state transitions for this public game.
                events = []

                # Record one fixed low-cardinality transition.
                def observe_state(name, status):
                    # Append only the governed action state and status.
                    events.append((name, status))

                # Build a minimal page seam for the three helpers that resolve locators directly.
                page = SimpleNamespace(
                    get_by_test_id=lambda _test_id: object(),  # Return one inert Keno reset locator.
                    locator=lambda _selector: object(),  # Return one inert direct-selector locator.
                    wait_for_function=mock.AsyncMock(),  # Model Roulette's resolving-state observation.
                    wait_for_timeout=mock.AsyncMock(),  # Model request-owned busy-state rerender allowance.
                )
                # Replace only browser primitives while retaining every production branch and state boundary.
                with (
                    mock.patch.object(concurrent_browser_138.ui_50000, "inventory_controls", new=mock.AsyncMock()),  # Avoid DOM inventory.
                    mock.patch.object(concurrent_browser_138.ui_50000, "wait_any_enabled", new=wait_any_enabled),  # Model immediate readiness.
                    mock.patch.object(concurrent_browser_138.ui_50000, "enabled_locators", new=enabled_locators),  # Model one enabled control.
                    mock.patch.object(concurrent_browser_138.ui_50000, "locator_ready", new=mock.AsyncMock(return_value=False)),  # Keep Keno in fresh-ticket state.
                    mock.patch.object(concurrent_browser_138.ui_50000, "click_control", new=mock.AsyncMock()),  # Record no real pointer work.
                    mock.patch.object(concurrent_browser_138.ui_50000, "click_locator", new=mock.AsyncMock()),  # Record no real pointer work.
                    mock.patch.object(concurrent_browser_138.ui_50000, "fill_control", new=mock.AsyncMock()),  # Record no keyboard work.
                    mock.patch.object(concurrent_browser_138.ui_50000, "roulette_add_bet", new=mock.AsyncMock()),  # Model committed drawer readiness.
                ):
                    # Complete one bounded public action for this diagnosed game.
                    handled = await concurrent_browser_138.play_formal_bounded_ui(
                        page,  # Reuse the inert task-owned page seam.
                        game_id,  # Select the diagnosed public game.
                        ordinal,  # Preserve deterministic visible selection.
                        Counter(),  # Collect no persistent control inventory.
                        Counter(),  # Collect no persistent pointer history.
                        observe_state,  # Record fixed state transitions.
                    )
                # Require explicit formal-only ownership.
                self.assertTrue(handled, game_id)
                # Require every started fixed state to reach a matching completion.
                self.assertEqual(Counter(name for name, status in events if status == "started"), Counter(name for name, status in events if status == "completed"), game_id)
                # Require genuine initial readiness before action commitment.
                self.assertIn(("initial_ready", "completed"), events, game_id)
                self.assertIn(("action_commit", "completed"), events, game_id)

        # Run the listener-free all-driver proof.
        asyncio.run(scenario())

    # Prove the formal controller selects the bounded driver instead of the inherited long-suite strategy.
    def test_formal_controller_routes_diagnosed_game_to_bounded_driver(self):
        # Exercise the orchestration without opening a listener or browser.
        async def scenario():
            # Model navigation as one immediate rendered route transition.
            navigation = mock.AsyncMock()
            # Model the bounded Baccarat driver as successfully handled.
            bounded = mock.AsyncMock(return_value=True)
            # Keep the long-suite driver red if the controller reaches it.
            inherited = mock.AsyncMock(return_value="wager_required")
            # Replace only browser operations while retaining production ownership selection.
            with (
                mock.patch.object(concurrent_browser_138.ui_50000, "navigate_to_game", new=navigation),  # Replace visible route work.
                mock.patch.object(concurrent_browser_138, "play_formal_bounded_ui", new=bounded),  # Observe bounded ownership.
                mock.patch.object(concurrent_browser_138.ui_50000, "play_game_ui", new=inherited),  # Detect forbidden long-suite delegation.
            ):
                # Run one diagnosed assignment through the formal controller.
                expectation = await concurrent_browser_138.run_formal_gameplay(
                    object(),  # Use one inert browser-free page seam.
                    {"game_id": "baccarat", "user_index": 0},  # Select one diagnosed game.
                    Counter(),  # Collect no persistent rendered controls.
                    Counter(),  # Collect no persistent pointer actions.
                    lambda _name, _status: None,  # Accept fixed phase transitions.
                    lambda _name, _status: None,  # Accept fixed action-state transitions.
                )
            # Preserve fail-closed wager evidence for the bounded visible action.
            self.assertEqual(expectation, "wager_required")
            # Require one exact bounded-driver invocation.
            bounded.assert_awaited_once()
            # Refuse the unrelated 50,000-cycle strategy in the formal profile.
            inherited.assert_not_awaited()

        # Run the listener-free routing proof.
        asyncio.run(scenario())

    # Prove concurrent autoplay starts and lifecycle calls preserve every issued session id.
    def test_autoplay_registry_serializes_concurrent_lifecycle_transactions(self):
        # Start one fake JSON-deserialized registry owned only by this listener-free test.
        registry = autoplay.default_state()

        # Return an independent delayed snapshot so unlocked read-modify-write calls would overwrite siblings.
        def fake_load_state():
            # Widen the read window enough for the worker pool to expose lost-update behavior.
            time.sleep(0.001)
            # Match real JSON deserialization by returning a detached object graph.
            return copy.deepcopy(registry)

        # Replace the fake persisted registry with one independent delayed snapshot.
        def fake_save_state(state):
            # Rebind the test-owned registry after the simulated storage delay.
            nonlocal registry
            # Widen the write window enough for concurrent callers to overlap without the production lock.
            time.sleep(0.001)
            # Match atomic JSON replacement with a detached committed object graph.
            registry = copy.deepcopy(state)

        # Patch only storage I/O while retaining production ids, timestamps, validation, and locking.
        with (
            mock.patch.object(autoplay, "load_state", side_effect=fake_load_state),  # Replace only registry reads.
            mock.patch.object(autoplay, "save_state", side_effect=fake_save_state),  # Replace only registry writes.
        ):
            # Start more concurrent sessions than the hosted artifact's five missing registrations.
            with ThreadPoolExecutor(max_workers=12) as executor:
                # Create twenty-four independent server registrations.
                sessions = list(executor.map(lambda index: autoplay.start("slots", f"player-{index:02d}", "medium", 2), range(24)))
            # Preserve every unique server-issued id after concurrent start transactions.
            autoplay_ids = [session["autoplay_id"] for session in sessions]
            # Require no generated identity collision.
            self.assertEqual(len(set(autoplay_ids)), 24)
            # Require every issued id to remain immediately readable.
            self.assertEqual({autoplay.get_session(autoplay_id)["autoplay_id"] for autoplay_id in autoplay_ids}, set(autoplay_ids))
            # Tick every retained session concurrently through the same transaction boundary.
            with ThreadPoolExecutor(max_workers=12) as executor:
                # Require every tick to complete without a lost-session 404 boundary.
                ticked = list(executor.map(autoplay.tick, autoplay_ids))
            # Require one committed round per independent session.
            self.assertEqual({row["rounds_completed"] for row in ticked}, {1})
            # Request every stop concurrently.
            with ThreadPoolExecutor(max_workers=12) as executor:
                # Preserve every retained id through the stop transition.
                stopped = list(executor.map(autoplay.stop, autoplay_ids))
            # Require every stop request to remain associated with its issued id.
            self.assertEqual({row["autoplay_id"] for row in stopped}, set(autoplay_ids))
            # Complete every stop concurrently like the shared browser controller.
            with ThreadPoolExecutor(max_workers=12) as executor:
                # Preserve every retained id through finish-stop.
                terminal = list(executor.map(autoplay.finish_stop, autoplay_ids))
        # Require all twenty-four sessions to remain present and terminal.
        self.assertEqual(len(registry["sessions"]), 24)
        self.assertEqual({row["status"] for row in terminal}, {"stopped"})

    # Prove the browser controller's exact autoplay paths resolve in the real router.
    def test_autoplay_browser_paths_match_registered_server_routes(self):
        # Read the tracked production router source without importing optional Pillow or provider dependencies.
        app_source = (Path(__file__).resolve().parents[2] / "casino" / "app.py").read_text(encoding="utf-8")
        # Parse decorators structurally so formatting changes cannot create a false route match.
        app_tree = ast.parse(app_source)
        # Collect only literal GET and POST patterns registered inside production source.
        registrations = {
            (decorator.func.attr.upper(), decorator.args[0].value)
            for node in ast.walk(app_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr in {"get", "post"}
            and decorator.args
            and isinstance(decorator.args[0], ast.Constant)
            and isinstance(decorator.args[0].value, str)
        }
        # Enumerate every path observed as 404 in the preserved governed artifact.
        requests = (
            ("GET", "/api/v1/autoplay/sessions/auto-regression"),  # Preserve the session-read path.
            ("POST", "/api/v1/autoplay/tick"),  # Preserve the round-tick path.
            ("POST", "/api/v1/autoplay/stop"),  # Preserve the stop-request path.
            ("POST", "/api/v1/autoplay/finish-stop"),  # Preserve the terminal-stop path.
        )
        # Require each browser-owned public request to match one real server registration.
        for method, path in requests:
            # Reject path drift independently from runtime storage behavior.
            self.assertTrue(
                any(registered_method == method and re.fullmatch(pattern, path) for registered_method, pattern in registrations),
                f"{method} {path}",
            )

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
        # Build one successful wagering result for each deterministic formal assignment.
        results = [self.passing_result(assignment) for assignment in concurrent_browser_138.build_assignment_plan()]
        # Map each synthetic player to its assigned public game for exact evidence attribution.
        game_by_player = {user["player_id"]: result["game_id"] for user, result in zip(users, results)}

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
                                "game": game_by_player[player_id],  # Preserve the exact assigned public game identity.
                                "details": {"ledger_action_key": f"action-{player_id}"},  # Preserve one unique action identity.
                            }
                        ]
                    }
                # Refuse any unexpected or global evidence route.
                raise AssertionError(f"unexpected evidence path: {path}")

        # Collect the production aggregate through the browser-free fake client.
        client = FakeClient()
        evidence = concurrent_browser_138.collect_isolation_evidence(client, users, results)
        # Require one gameplay-ledger row for every synthetic player beyond the global hundred-row cap.
        self.assertEqual(evidence["users_with_gameplay_ledger"], 138)
        # Require no duplicate player, ledger, or action identities.
        self.assertEqual(evidence["duplicate_player_id_count"], 0)
        self.assertEqual(evidence["duplicate_ledger_id_count"], 0)
        self.assertEqual(evidence["duplicate_action_key_count"], 0)
        # Require exact assigned-game evidence for every wagering action.
        self.assertEqual(evidence["wager_evidence_required"], 138)
        self.assertEqual(evidence["wager_evidence_satisfied"], 138)
        # Require no action to be silently treated as non-wagering.
        self.assertEqual(evidence["non_wager_actions"], 0)
        # Reject the global Admin ledger route that filtered only after its hundred-row cap.
        self.assertFalse(any(path.startswith("/api/v1/admin/ledger") for path in client.paths))
        # Require exactly one player-scoped bounded ledger request per synthetic account.
        self.assertEqual(sum(path.startswith("/api/v1/players/") and path.endswith("/ledger?limit=100") for path in client.paths), 138)

    # Prove action-aware evidence accepts legitimate no-wager completions while requiring an assigned-game wager row.
    def test_isolation_distinguishes_non_wager_actions_from_committed_wagers(self):
        # Build three synthetic users representing Play, Pass, and automatic terminal action paths.
        users = [{"user_id": f"user-{index}", "player_id": f"player-{index}"} for index in range(3)]
        # Model one wagering Play and two legitimate no-wager completions.
        results = [
            {"game_id": "acey_deucey", "gameplay_ok": True, "ledger_expectation": "wager_required"},  # Model rendered Play.
            {"game_id": "acey_deucey", "gameplay_ok": True, "ledger_expectation": "non_wager"},  # Model rendered Pass.
            {"game_id": "acey_deucey", "gameplay_ok": True, "ledger_expectation": "non_wager"},  # Model automatic free-boundary terminal state.
        ]

        # Return one exact player-scoped assigned-game ledger row only for the wagering action.
        class FakeClient:
            # Resolve the two evidence routes without opening storage or a listener.
            def call(self, path):
                # Return one matching nonnegative player state.
                if path.startswith("/api/v2/admin/users/"):
                    # Derive the synthetic ordinal from the public user segment.
                    ordinal = int(path.rsplit("/", 2)[1].rsplit("-", 1)[1])
                    # Preserve exact user-to-player binding.
                    return {"player_id": f"player-{ordinal}", "token_balance": 100}
                # Resolve the exact player-scoped ledger route.
                if path.startswith("/api/v1/players/"):
                    # Derive the synthetic ordinal from the public player segment.
                    ordinal = int(path.split("/", 5)[4].rsplit("-", 1)[1])
                    # Return one assigned-game wager row only for the rendered Play path.
                    rows = [
                        {
                            "ledger_id": "ledger-player-0",  # Preserve one immutable player-scoped row identity.
                            "transaction_type": "BET",  # Mark the committed wager movement.
                            "game": "acey_deucey",  # Bind the row to the assigned public game.
                            "details": {"ledger_action_key": "acey-play-0"},  # Preserve one unique action identity.
                        }
                    ] if ordinal == 0 else []
                    # Return the standard bounded ledger collection.
                    return {"ledger": rows}
                # Refuse any global or unexpected evidence route.
                raise AssertionError(f"unexpected evidence path: {path}")

        # Collect the production action-aware aggregate.
        evidence = concurrent_browser_138.collect_isolation_evidence(FakeClient(), users, results)
        # Require the committed wager to have one exact assigned-game player-scoped row.
        self.assertEqual((evidence["wager_evidence_required"], evidence["wager_evidence_satisfied"]), (1, 1))
        # Require both legitimate no-wager actions to remain accepted without fabricated ledger movement.
        self.assertEqual((evidence["non_wager_actions"], evidence["non_wager_actions_with_ledger"]), (2, 0))
        # Require every successful action to have exactly one recognized expectation.
        self.assertEqual(evidence["classified_gameplay_actions"], 3)

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
            # Classify two successful Acey-Deucey assignments as rendered no-wager Pass or automatic outcomes.
            for row in [result for result in results if result["game_id"] == "acey_deucey"][:2]:
                # Preserve successful gameplay while changing only its actual ledger expectation.
                row["ledger_expectation"] = "non_wager"
            # Model the exact synchronized barrier terminal state.
            barrier = SimpleNamespace(ready=138, peak_ready=138)
            # Provide complete aggregate-only isolation evidence.
            isolation = {
                "unique_player_count": 138,  # Preserve one unique player per account.
                "duplicate_player_id_count": 0,  # Model no duplicate player binding.
                "matching_player_count": 138,  # Preserve exact account-to-player binding.
                "nonnegative_balance_count": 138,  # Keep every synthetic wallet solvent.
                "users_with_gameplay_ledger": 136,  # Exclude the two legitimate no-wager completions.
                "wager_evidence_required": 136,  # Require evidence only for actions that committed wagers.
                "wager_evidence_satisfied": 136,  # Satisfy every committed wager.
                "non_wager_actions": 2,  # Model Pass and automatic free-boundary completion.
                "non_wager_actions_with_ledger": 0,  # Model no unexpected movement.
                "classified_gameplay_actions": 138,  # Classify the complete formal population.
                "duplicate_ledger_id_count": 0,  # Preserve unique ledger row identities.
                "duplicate_action_key_count": 0,  # Preserve exactly-once action identities.
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
                "wager_evidence_required": 138,  # Require all modeled actions to produce evidence.
                "wager_evidence_satisfied": 138,  # Satisfy every modeled wager.
                "non_wager_actions": 0,  # Model no token-free paths.
                "non_wager_actions_with_ledger": 0,  # Model no unexpected movement.
                "classified_gameplay_actions": 138,  # Classify the complete formal population.
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

    # Prove identical enabled-Deal failures remain precisely attributable to public game and fixed phase.
    def test_deal_state_failures_are_attributed_by_game_and_phase(self):
        # Build the exact complete current-catalog assignment.
        assignments = concurrent_browser_138.build_assignment_plan()
        # Start from one sanitized successful result per user.
        results = [self.passing_result(assignment) for assignment in assignments]
        # Select three distinct public games that use the same rendered Deal selector.
        failed_games = ("dragon_tiger", "red_dog", "hi_lo")
        # Inject one identical Deal readiness failure into each public game.
        for game_id in failed_games:
            # Resolve the first deterministic result for this game.
            row = next(result for result in results if result["game_id"] == game_id)
            # Mark the visible action incomplete.
            row["gameplay_ok"] = False
            # Remove the successful latency sample.
            row.pop("play_seconds")
            # Preserve the identical bounded public selector diagnostic.
            row["error"] = "enabled control timeout: ['[data-action=\"deal\"]']"
            # Attribute the failure to the fixed game-action phase.
            row["failure_phase"] = "gameplay_action"
            # Attribute the identical selector failure to the fixed initial-readiness state.
            row["failure_action_state"] = "initial_ready"
            # Remove the terminal action completion from phase evidence.
            row["completed_phases"] = [phase for phase in row["completed_phases"] if phase != "gameplay_action"]
        # Model exact barrier and cleanup completion.
        barrier = SimpleNamespace(ready=138, peak_ready=138)
        # Model action-aware isolation for the remaining 135 successful wagering actions.
        isolation = {
            "unique_player_count": 138,  # Preserve one unique player per account.
            "duplicate_player_id_count": 0,  # Model no duplicate player bindings.
            "matching_player_count": 138,  # Preserve exact account-to-player bindings.
            "nonnegative_balance_count": 138,  # Keep every synthetic wallet solvent.
            "users_with_gameplay_ledger": 135,  # Model rows for the successful actions only.
            "wager_evidence_required": 135,  # Require evidence for each successful wager.
            "wager_evidence_satisfied": 135,  # Satisfy each successful wager.
            "non_wager_actions": 0,  # Model no token-free action in this failure scenario.
            "non_wager_actions_with_ledger": 0,  # Model no unexpected no-wager movement.
            "classified_gameplay_actions": 135,  # Classify all successful actions.
            "duplicate_ledger_id_count": 0,  # Preserve unique immutable ledger rows.
            "duplicate_action_key_count": 0,  # Preserve exactly-once action identities.
        }
        # Build one clean fixed-cardinality exact-source MySQL preflight.
        pool_preflight = {
            "source_commit": "e" * 40,  # Bind the fixture to one exact synthetic source.
            "measurements": [
                {"concurrency": concurrency, "p50_ms": 1.0, "p95_ms": 2.0, "throughput_rps": 10.0, "errors": 0}  # Preserve one clean aggregate row.
                for concurrency in (1, 2, 4, 8)  # Cover every governed preflight level.
            ],
            "pool": {
                "capacity": 2,  # Preserve the configured pool capacity.
                "in_use": 0,  # Require terminal lease cleanup.
                "idle": 2,  # Return both physical sessions.
                "waiting": 0,  # Require terminal waiter cleanup.
                "physical_created": 2,  # Keep physical creation within capacity.
                "reused": 50,  # Prove bounded connection reuse.
                "discarded": 0,  # Model no unhealthy-session discard.
                "wait_count": 2,  # Preserve fixed aggregate wait evidence.
                "timeout_count": 0,  # Refuse checkout exhaustion.
                "rollback_cleanup": 0,  # Model no residual rollback cleanup.
                "connector_error": 0,  # Refuse connector failures.
                "wait_buckets_ms": {"1": 1, "5": 1, "25": 0, "100": 0, "500": 0, ">500": 0},  # Preserve fixed wait buckets.
            },
        }
        # Aggregate without retaining user-level failure rows.
        report = concurrent_browser_138.aggregate_results(
            assignments,  # Preserve the exact complete assignment.
            results,  # Aggregate the three deterministic Deal failures.
            barrier,  # Preserve exact synchronized readiness.
            {"active_setup": 0, "peak_setup": 12, "active_gameplay": 0, "peak_gameplay": 138},  # Preserve bounded concurrency.
            isolation,  # Supply action-aware aggregate evidence.
            {"provider": "json", "available": False},  # Avoid inventing runtime MySQL counters.
            pool_preflight,  # Supply exact-source Package B evidence.
            "e" * 40,  # Bind the report to one synthetic source.
            90,  # Preserve one bounded synthetic elapsed time.
        )
        # Require the complete qualification to remain fail-closed.
        self.assertEqual(report["status"], "FAIL")
        # Require one exact aggregate row for each affected public game.
        self.assertEqual(
            report["failure_attribution"],
            [
                {"game_id": "dragon_tiger", "phase": "gameplay_action", "action_state": "initial_ready", "error": "enabled control timeout: ['[data-action=\"deal\"]']", "count": 1},  # Attribute Dragon Tiger.
                {"game_id": "hi_lo", "phase": "gameplay_action", "action_state": "initial_ready", "error": "enabled control timeout: ['[data-action=\"deal\"]']", "count": 1},  # Attribute Hi-Lo.
                {"game_id": "red_dog", "phase": "gameplay_action", "action_state": "initial_ready", "error": "enabled control timeout: ['[data-action=\"deal\"]']", "count": 1},  # Attribute Red Dog.
            ],
        )
        # Require the fixed action-state failure counter to preserve all three readiness defects.
        self.assertEqual(report["action_state_counts"]["failed"]["initial_ready"], 3)

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
