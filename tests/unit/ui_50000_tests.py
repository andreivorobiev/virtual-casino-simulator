# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused TEST-092 proofs for the exact-source 50,000-cycle UI harness."""

import argparse  # Build narrow command namespaces without invoking the CLI parser.
import asyncio  # Exercise the browser-free aggregate controller end to end.
import json  # Persist synthetic shard reports for resume-policy tests.
import math  # Verify each integer replica stays within its profiled UI target.
import tempfile  # Own disposable report directories for every test.
import unittest  # Integrate the focused proofs with the repository API runner.
from collections import Counter  # Aggregate deterministic per-game allocation totals.
from pathlib import Path  # Address temporary shard reports with platform-neutral paths.
from unittest import mock  # Inject immutable provenance when release tests intentionally omit Git metadata.

from tests import baccarat_sustained, formal_ui_profile, ui_50000  # Exercise both public qualification profiles without starting Playwright.


# Prove TEST-092 allocation, control classification, and exact-source resume invariants.
class UI50000HarnessTests(unittest.TestCase):
    # Prove an expired pre-soak Admin session is replaced before the first privileged evidence read. (TEST-092)
    def test_post_soak_admin_evidence_reauthenticates_before_read(self):
        events = []  # Record only public authentication and evidence-read boundaries.

        class ExpiredAdminClient:  # Model the Admin client after a soak longer than its governed idle window.
            def __init__(self):
                self.session_token = "expired"  # Start with the unusable pre-soak bearer reproduced by run 32459496338.

            def login_default_user(self):
                events.append(("POST", "/api/v2/auth/login"))  # Record the required public reauthentication boundary.
                self.session_token = "fresh"  # Model the new bearer returned by a successful login.
                return self.session_token  # Preserve the production client method contract.

            def call(self, path):
                events.append(("GET", path, self.session_token))  # Record which bearer owns the privileged read.
                if self.session_token != "fresh":  # Reproduce rejection of the expired session without weakening policy.
                    raise AssertionError("Session is invalid or expired")  # Fail if the helper skips reauthentication.
                return {"player_id": "player_test"}  # Return one minimal Admin evidence payload.

        result = ui_50000.call_post_soak_admin_evidence(ExpiredAdminClient(), "/api/v2/admin/users/user_test/state")  # Exercise the exact post-soak seam without a browser.
        self.assertEqual(result, {"player_id": "player_test"})  # Preserve the privileged endpoint payload unchanged.
        self.assertEqual(events, [("POST", "/api/v2/auth/login"), ("GET", "/api/v2/admin/users/user_test/state", "fresh")])  # Require login before the first evidence read.

    # Prove rejected reauthentication prevents every post-soak privileged read. (TEST-092)
    def test_post_soak_admin_evidence_fails_closed_when_login_fails(self):
        events = []  # Record whether the protected evidence endpoint was reached.

        class RejectedAdminClient:  # Model invalid bootstrap credentials or another public login failure.
            def login_default_user(self):
                events.append("login")  # Record the sole allowed attempt before failure.
                raise AssertionError("login rejected")  # Preserve fail-closed public authentication behavior.

            def call(self, _path):
                events.append("read")  # Expose any forbidden privileged read after failed login.
                raise AssertionError("protected read must not run")  # Prevent a false-positive test result.

        with self.assertRaisesRegex(AssertionError, "login rejected"):  # Require the login failure to remain terminal.
            ui_50000.call_post_soak_admin_evidence(RejectedAdminClient(), "/api/v2/admin/operations")  # Exercise the terminal readiness evidence seam.
        self.assertEqual(events, ["login"])  # Prove no privileged request followed the rejected reauthentication.

    # Build one complete focused Baccarat aggregate for listener-free profile tests.
    def passing_baccarat_sustained_report(self):
        deal_signature = 'baccarat::button[data-testid="baccarat-deal"]'  # Match the production control namespace and public test identity.
        shard = {"status": "PASS", "control_activated_counts": {deal_signature: baccarat_sustained.EXPECTED_ROUNDS}}  # Model one uninterrupted accepted browser shard.
        return {"status": "PASS", "source_commit": "a" * 40, "requested_cycles": baccarat_sustained.EXPECTED_ROUNDS, "selected_games": ["baccarat"], "worker_count": 1, "attempted_cycles": baccarat_sustained.EXPECTED_ROUNDS, "completed_cycles": baccarat_sustained.EXPECTED_ROUNDS, "failed_cycles": 0, "failed_attempts": 0, "assignment": {"no_gaps_or_duplicates": True}, "game_counts": {"baccarat": {"quota": baccarat_sustained.EXPECTED_ROUNDS, "completed": baccarat_sustained.EXPECTED_ROUNDS, "failed": 0, "failed_attempts": 0, "status": "PASS"}}, "failure_counts": {}, "visual_failures": [], "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}}, "shards_pass": True, "isolation_ok": True, "listener_cleanup_ok": True, "visuals_complete": True, "shards": [shard]}  # Return every focused acceptance field.

    # Prove the issue #265 profile cannot be shortened, sharded, resumed, or retried.
    def test_baccarat_sustained_arguments_are_exact_and_retry_free(self):
        with tempfile.TemporaryDirectory() as temporary_directory:  # Own and clean the test-only output root.
            arguments = baccarat_sustained.build_arguments(temporary_directory, progress_every=125, headed=True)  # Build the production profile without browser work.
        self.assertEqual(arguments.total_cycles, 2_000)  # Require the exact issue-owned round count.
        self.assertEqual(arguments.only_games, "baccarat")  # Prevent unrelated catalog work from diluting the gate.
        self.assertEqual(arguments.parallel, 1)  # Require one uninterrupted browser session.
        self.assertEqual(arguments.game_replicas, 1)  # Prevent aggregate fragments from satisfying the consecutive sequence.
        self.assertEqual(arguments.max_attempts_per_cycle, 1)  # Reject a recovered Deal disappearance or timeout.
        self.assertFalse(arguments.resume_shards)  # Refuse prior-head and interrupted evidence.
        self.assertFalse(arguments.keep_deployments)  # Require deterministic runtime cleanup.
        self.assertEqual(arguments.progress_every, 125)  # Preserve the only requested monitoring override.
        self.assertTrue(arguments.headed)  # Preserve the explicit local-debug browser choice.

    # Prove a clean 2,000-round aggregate receives the permanent focused identity.
    def test_baccarat_sustained_accepts_only_complete_clean_report(self):
        report = self.passing_baccarat_sustained_report()  # Build one complete listener-free aggregate.
        errors = baccarat_sustained.stamp_report(report)  # Apply the production focused gate.
        self.assertEqual(errors, [])  # Require every acceptance invariant to pass.
        self.assertEqual(report["qualification"]["test_id"], "BR-BAC-SUSTAINED-001")  # Publish the stable browser-test identity.
        self.assertEqual(report["qualification"]["requirements"], ["BAC-026", "TEST-099"])  # Bind the new permanent requirements exactly.
        self.assertEqual(report["qualification"]["visible_deal_activations"], 2_000)  # Require one public Deal action per coup.
        self.assertEqual(report["status"], "PASS")  # Keep the top-level aggregate aligned with the focused result.

    # Prove one recovered failure or missing Deal activation makes the focused report red.
    def test_baccarat_sustained_rejects_interrupted_sequence(self):
        report = self.passing_baccarat_sustained_report()  # Start from the complete accepted aggregate.
        report["failed_attempts"] = 1  # Model one Deal disappearance that the general harness might otherwise retry.
        report["shards"][0]["control_activated_counts"] = {}  # Model a hidden shortcut around the rendered Deal control.
        errors = baccarat_sustained.stamp_report(report)  # Apply the production focused gate.
        self.assertIn("one or more Baccarat attempts failed", errors)  # Reject the interrupted sequence.
        self.assertIn("visible Baccarat Deal activation count is not 2000", errors)  # Reject missing public-control proof.
        self.assertEqual(report["qualification"]["status"], "FAIL")  # Keep focused evidence red.
        self.assertEqual(report["status"], "FAIL")  # Keep the aggregate result red as well.

    # Prove the hosted sustained qualification remains one explicit job isolated from the formal 50,000-cycle matrix.
    def test_baccarat_sustained_workflow_is_single_opt_in_job(self):
        workflow_path = ui_50000.ROOT / ".github" / "workflows" / "browser-tests.yml"  # Resolve the repository-owned hosted browser workflow.
        workflow = workflow_path.read_text(encoding="utf-8")  # Read its declarative dispatch contract without launching a browser.
        self.assertEqual(workflow.count("baccarat_sustained_2000:"), 2)  # Require exactly one input plus one job with the stable identity.
        self.assertEqual(workflow.count("python -m tests.baccarat_sustained"), 1)  # Require the repository-safe module invocation exactly once.
        self.assertNotIn("python tests/baccarat_sustained.py", workflow)  # Reject the Linux import-path failure reproduced by the first hosted attempt.
        ordinary_job = workflow.split("  browser_tests:", 1)[1].split("  # Run the focused issue #265", 1)[0]  # Isolate the ordinary browser job from the sustained profile.
        self.assertIn("github.event_name == 'pull_request' || github.event_name == 'push' || inputs.formal_ui_50000 == true", ordinary_job)  # Run ordinary coverage for pull requests, protected main, and formal dispatch while skipping sustained-only dispatches.
        self.assertNotIn("baccarat_sustained_2000", ordinary_job)  # Keep the focused run from starting a second browser suite.
        sustained_job = workflow.split("  baccarat_sustained_2000:", 2)[2].split("  # Derive the formal TEST-092 matrix", 1)[0]  # Isolate only the focused hosted job before formal planning begins.
        self.assertIn("inputs.baccarat_sustained_2000 == true", sustained_job)  # Keep the expensive profile behind explicit authorization.
        self.assertIn("baccarat-sustained-${{ github.sha }}", sustained_job)  # Bind the terminal artifact name to the exact source head.
        self.assertNotIn("ui_50000.py", sustained_job)  # Prevent the focused dispatch from starting the unrelated 50,000-cycle controller.

    # Prove rotating paint is required without treating its intentionally clipped square bounds as stable stage geometry.
    def test_big_six_stage_contract_separates_paint_from_containment(self):
        contract = ui_50000.ESSENTIAL_STAGE_CONTRACTS["big_six_wheel"]  # Read the public harness contract used by every formal viewport.
        self.assertEqual(contract["stage"], ".big-six-wheel__stage")  # Keep the route-owned stage as the containment boundary.
        self.assertIn(".big-six-wheel__wheel-shell", contract["contained_items"])  # Require the stable circular shell to remain fully inside the stage.
        self.assertNotIn(".big-six-wheel__wheel", contract["contained_items"])  # Avoid interpreting a rotated square bounding box as visible circular overflow.
        self.assertEqual(contract["paint_items"][".big-six-wheel__wheel"], ".big-six-wheel__wheel-shell")  # Require the wheel to paint across its clipping owner.
        self.assertEqual(contract["paint_min_ratio"], 0.8)  # Reject a missing or materially undersized wheel without requiring its intentional 90% inset to fill the shell.

    # Prove Crown and Anchor cannot pass when any non-control die or hit-result panel escapes the governed stage.
    def test_crown_and_anchor_stage_contract_tracks_complete_theater(self):
        contract = ui_50000.ESSENTIAL_STAGE_CONTRACTS["crown_and_anchor"]  # Read the route-specific contract applied after every formal viewport capture.
        self.assertEqual(contract["stage"], ".crown-anchor__stage")  # Keep the game-owned panel as the completeness boundary.
        dice = tuple(selector for selector in contract["contained_items"] if selector.startswith("[data-die="))  # Isolate the three stable die identities.
        symbols = tuple(selector for selector in contract["contained_items"] if selector.startswith("[data-symbol="))  # Isolate the six stable result-panel identities.
        self.assertEqual(dice, ('[data-die="0"]', '[data-die="1"]', '[data-die="2"]'))  # Require every die slot exactly once.
        self.assertEqual(symbols, tuple(f'[data-symbol="{symbol}"]' for symbol in ("crown", "anchor", "heart", "diamond", "club", "spade")))  # Require every authoritative symbol panel exactly once.
        self.assertEqual(contract["paint_items"], {})  # Keep all Crown nodes on the strict painted-and-contained path.

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
        allocations = ui_50000.formal_allocations()  # Build the profiled formal deterministic assignment.
        per_game = Counter()  # Aggregate replica quotas back to canonical games.
        assigned_ids = []  # Reconstruct every global cycle ID for uniqueness evidence.
        expected_offset = 0  # Pin deterministic contiguous worker boundaries in canonical plan order.
        for game_id, _game_index, _replica_index, quota, cycle_start in allocations:  # Inspect every bounded worker assignment.
            self.assertEqual(cycle_start, expected_offset)  # Reject gaps, overlaps, or reordered subranges before expanding case IDs.
            per_game[game_id] += quota  # Preserve the complete game quota across replicas.
            assigned_ids.extend(range(cycle_start, cycle_start + quota))  # Rebuild the worker's contiguous global range.
            expected_offset += quota  # Advance to the next exact immutable boundary.
        self.assertEqual(sum(per_game.values()), 50_000)  # Require the exact formal total.
        self.assertEqual(len(per_game), len(ui_50000.GAME_IDS))  # Require every registered game exactly once in the aggregate.
        expected_floor = 50_000 // len(ui_50000.GAME_IDS)  # Derive the honest catalog-wide floor from the current registered game count.
        self.assertGreaterEqual(min(per_game.values()), expected_floor)  # Require every game to receive at least its exact balanced share.
        self.assertEqual(sorted(assigned_ids), list(range(50_000)))  # Require exact case-inventory equality from zero through 49,999.
        self.assertEqual(len(assigned_ids), len(set(assigned_ids)))  # Reject overlapping replica ranges.
        self.assertEqual(allocations, ui_50000.formal_allocations())  # Require the checked-in profile to reproduce byte-equivalent plan inputs.
        self.assertEqual(len(allocations), 140)  # Pin the exact checked-in profile result under GitHub's 256-entry matrix ceiling.

    # Prove profiled ranges retain duration headroom plus the special Roulette and draw-poker aggregate affinities. (TEST-092, issue #1053)
    def test_formal_duration_profile_preserves_replica_affinities(self):
        allocations = ui_50000.formal_allocations()  # Resolve the same canonical plan consumed by workflow workers and the aggregate.
        entries = {entry["id"]: entry for entry in formal_ui_profile.FORMAL_DURATION_PROFILE["games"]}  # Index the immutable timing evidence by canonical game.
        self.assertEqual(list(entries), list(ui_50000.GAME_IDS))  # Require exact catalog/profile case equality before measuring any range.
        self.assertEqual(formal_ui_profile.FORMAL_EXECUTION_BUDGET_SECONDS, 17 * 60)  # Leave three minutes for cleanup and terminal artifact upload.
        self.assertEqual(formal_ui_profile.FORMAL_UI_STEP_TARGET_SECONDS, 18 * 60)  # Preserve the normal UI-step target below the hard job limit.
        self.assertEqual(formal_ui_profile.FORMAL_WORKER_TIMEOUT_MINUTES, 20)  # Pin the job-start-through-upload contract.
        for game_id, _game_index, replica_index, quota, _cycle_start in allocations:  # Verify every integer range independently.
            entry = entries[game_id]  # Read this allocation's measured cycles and conservative planning duration.
            predicted_seconds = math.ceil(entry["planning_ui_seconds"] * quota / entry["measured_cycles"])  # Scale the source run without hiding range remainders.
            self.assertLessEqual(predicted_seconds, formal_ui_profile.FORMAL_UI_STEP_TARGET_SECONDS, (game_id, replica_index, quota))  # Keep every range below the 18-minute UI target.
            if not (game_id == "roulette" and replica_index == 0):  # Permit only the explicit primary Rebet affinity range to use reserved target headroom.
                self.assertLessEqual(predicted_seconds, formal_ui_profile.FORMAL_PLANNING_TARGET_SECONDS, (game_id, replica_index, quota))  # Keep ordinary ranges at or below fifteen minutes.
        roulette = [allocation for allocation in allocations if allocation[0] == "roulette"]  # Isolate the continuous table schedule.
        self.assertEqual((len(roulette), roulette[0][2], roulette[0][3]), (12, 0, 101))  # Reserve one history seed plus one hundred real primary-shard Rebet activations.
        draw_games = [game_id for game_id, family in ui_50000.UI_STRATEGY_FAMILIES.items() if family == "draw_poker"]  # Derive every five-position hold-balancing family member.
        for game_id in draw_games:  # Prove replica-local deficit selection still exceeds the aggregate floor at every hold position.
            quotas = [allocation[3] for allocation in allocations if allocation[0] == game_id]  # Collect every deterministic independent range.
            self.assertGreaterEqual(sum(quota // 5 for quota in quotas), ui_50000.CONTROL_ACTIVATION_FLOOR, game_id)  # Require at least one hundred complete five-position schedules in the aggregate.

    # Prove every registered catalog game names one implemented strategy and future growth fails closed. (TEST-092, issue #1050)
    def test_catalog_games_have_explicit_implemented_ui_strategy_families(self):
        self.assertEqual(set(ui_50000.UI_STRATEGY_FAMILIES), set(ui_50000.GAME_IDS))  # Require exact catalog coverage without stale or missing strategy registrations.
        self.assertEqual(set(ui_50000.UI_STRATEGY_FAMILIES.values()), set(ui_50000.IMPLEMENTED_UI_STRATEGY_FAMILIES))  # Require every registered family to reach executable dispatch and every dispatch family to remain used.
        simple_games = {game_id for game_id, family in ui_50000.UI_STRATEGY_FAMILIES.items() if family == "simple_terminal"}  # Derive the configured settled-action family from the canonical registry.
        self.assertEqual(simple_games, set(ui_50000.SIMPLE_TERMINAL_UI_STRATEGIES))  # Require complete selectors for every simple-family member without extra configs.
        with self.assertRaisesRegex(AssertionError, "no UI cycle strategy for catalog game fixture_catalog_growth"):  # Model a future registered game before its strategy is implemented.
            ui_50000.strategy_family_for("fixture_catalog_growth")  # Require the production resolver to stop instead of silently skipping the new game.
        with mock.patch.dict(ui_50000.UI_STRATEGY_FAMILIES, {"fixture_bad_family": "missing_dispatch"}):  # Model a typo that superficially registers a future game.
            with self.assertRaisesRegex(AssertionError, "no UI cycle strategy implementation for family missing_dispatch"):  # Require an executable family rather than a registry-only waiver.
                ui_50000.strategy_family_for("fixture_bad_family")  # Exercise the exact invalid-family guard.

    # Prove newly covered board and staged controls retain stable semantic identities in both discovery paths.
    def test_new_strategy_controls_use_stable_semantic_signatures(self):
        source = (ui_50000.ROOT / "tests" / "ui_50000.py").read_text(encoding="utf-8")  # Read the inert harness source without starting a browser.
        semantic_attributes = ("data-number", "data-cell", "data-color", "data-rank", "data-marble", "data-card-index", "data-ante", "data-aces", "data-fold", "data-deal", "data-draw", "data-hold", "data-repeat")  # Enumerate the strategy-owned identities that cannot fall back to translated text.
        for attribute in semantic_attributes:  # Inspect pointer signatures and rendered inventory together.
            self.assertEqual(source.count(f"'{attribute}'"), 2, attribute)  # Require the attribute once in each aligned expression augmentation.

    # Prove manual Pai Gow setting keeps the low hand on the weakest two distinct visible ranks.
    def test_pai_gow_manual_low_hand_uses_legal_visible_rank_order(self):
        self.assertEqual(ui_50000.pai_gow_low_hand_positions(("K", "2", "A", "5", "2", "J", "JOKER")), (1, 3))  # Avoid a low-hand pair and keep the Joker in the five-card high hand.
        self.assertEqual(ui_50000.pai_gow_low_hand_positions(("10", "4", "Q", "7", "A", "3", "K")), (5, 1))  # Order ordinary visible ranks numerically rather than lexicographically.
        with self.assertRaisesRegex(AssertionError, "Pai Gow setting exposed 1 card ranks"):  # Reject an incomplete rendered setting surface.
            ui_50000.pai_gow_low_hand_positions(("A",))  # Exercise the fail-closed public-count gate.

    # Prove the simple-family runner completes either one repeat or one configured fresh play, never both.
    def test_simple_terminal_strategy_keeps_one_settlement_per_cycle(self):
        events = []  # Record only the public helper boundaries exercised by the dispatcher.

        async def fake_repeat(_page, ordinal, repeat_selector, ready_selector, _activated):
            events.append(("repeat", ordinal, repeat_selector, ready_selector))  # Preserve the replay contract chosen for this game.
            return ordinal == 1  # Model one reachable repeat cycle and one ordinary cycle.

        async def fake_rotate(_page, selector, ordinal, clicks, _activated):
            events.append(("rotate", selector, ordinal, clicks))  # Record each configured real-control group in order.

        async def fake_terminal(_page, selector, _activated):
            events.append(("terminal", selector))  # Record the sole fresh terminal action.

        with mock.patch.object(ui_50000, "maybe_repeat_terminal", side_effect=fake_repeat), mock.patch.object(ui_50000, "rotate_control_group", side_effect=fake_rotate), mock.patch.object(ui_50000, "terminal_action", side_effect=fake_terminal):  # Isolate deterministic dispatch without Playwright.
            asyncio.run(ui_50000.play_simple_terminal_game(object(), "color_wheel", 1, Counter()))  # Exercise the bounded repeat path.
            asyncio.run(ui_50000.play_simple_terminal_game(object(), "color_wheel", 101, Counter()))  # Exercise the ordinary configured play path.
        self.assertEqual(events, [("repeat", 1, '[data-testid="color-wheel-repeat"]', '[data-testid="color-wheel-spin"]'), ("repeat", 101, '[data-testid="color-wheel-repeat"]', '[data-testid="color-wheel-spin"]'), ("rotate", "[data-color]", 101, 1), ("rotate", "[data-chip]", 101, 1), ("terminal", '[data-testid="color-wheel-spin"]')])  # Reject a second settlement on repeat cycles or skipped fresh choices.

    # Prove the hosted matrix derives every exact profiled allocation and rejects stale catalog growth. (TEST-092)
    def test_formal_workflow_matrix_comes_from_canonical_allocator(self):
        current_indices = ui_50000.formal_allocation_indices()  # Derive the exact current hosted-worker plan.
        self.assertEqual(current_indices, list(range(140)))  # Require the complete duration-sized matrix with contiguous stable identities.
        with mock.patch.object(ui_50000, "GAME_IDS", ui_50000.GAME_IDS + ("fixture_catalog_growth",)):  # Model one future catalog addition without editing workflow YAML.
            with self.assertRaisesRegex(RuntimeError, "profile is stale for the catalog"):  # Require measured policy before scheduling an unprofiled strategy.
                ui_50000.formal_allocation_indices()  # Refuse a partial matrix instead of guessing the new game's throughput.
        workflow = (ui_50000.ROOT / ".github" / "workflows" / "browser-tests.yml").read_text(encoding="utf-8")  # Read the inert exact-source workflow contract.
        planner_job = workflow.split("  formal_ui_plan:", 1)[1].split("  formal_ui_workers:", 1)[0]  # Isolate canonical planning from worker execution.
        worker_job = workflow.split("  formal_ui_workers:", 1)[1].split("  formal_ui_aggregate:", 1)[0]  # Isolate only the dynamic matrix consumer.
        aggregate_job = workflow.split("  formal_ui_aggregate:", 1)[1].split("  # Run issue #225", 1)[0]  # Isolate the fail-closed terminal aggregate.
        self.assertIn("python tests/ui_50000.py --print-formal-allocation-indices", planner_job)  # Bind planning to the public canonical helper.
        self.assertIn("allocation_index: ${{ fromJSON(needs.formal_ui_plan.outputs.allocation_indices) }}", worker_job)  # Consume the complete exact-source JSON matrix.
        self.assertNotIn("allocation_index:\n          - 0", worker_job)  # Reject a reintroduced enumerated prefix that can drift after catalog growth.
        self.assertIn("    name: Formal UI worker ${{ matrix.allocation_index }}", worker_job)  # Preserve the required branch-protection context family.
        self.assertIn("    timeout-minutes: 20", worker_job)  # Enforce the hard job-start-through-terminal-upload ceiling.
        self.assertNotIn("timeout-minutes: 350", worker_job)  # Reject the former multi-hour stale-profile window.
        self.assertIn("      max-parallel: 20", worker_job)  # Preserve the repository's bounded runner-capacity policy.
        self.assertIn("--max-attempts-per-cycle 1", worker_job)  # Keep formal evidence retry-free on workflow attempt one.
        self.assertIn("      - formal_ui_plan\n      - formal_ui_workers", aggregate_job)  # Require the aggregate to depend on both planning and every worker.
        self.assertIn("    name: Formal UI exact aggregate", aggregate_job)  # Preserve the exact required terminal context name.

    # Prove a stale worker is cancelled inside the cleanup margin and returns an aggregate-safe red handback.
    def test_formal_worker_execution_budget_fails_closed(self):
        allocation = ui_50000.formal_allocations()[0]  # Use one real deterministic identity and range.

        async def stalled_shard(*_args):
            await asyncio.sleep(1)  # Model a worker that cannot finish inside its checked-in profile.

        args = argparse.Namespace(allocation_index=0)  # Select the immutable hosted-worker deadline path.
        with mock.patch.object(ui_50000, "FORMAL_EXECUTION_BUDGET_SECONDS", 0.001), mock.patch.object(ui_50000, "run_game_shard", side_effect=stalled_shard):  # Compress only the browser-free unit deadline.
            result = asyncio.run(ui_50000.run_bounded_shard(None, asyncio.Semaphore(1), args, allocation, "run", "a" * 40))  # Exercise cancellation without starting Playwright.
        self.assertEqual(result["status"], "FAIL")  # Keep the timed-out allocation terminally red.
        self.assertEqual(result["failed"], allocation[3])  # Account every assigned unique cycle as incomplete.
        self.assertFalse(result["listener_cleanup"]["closed"])  # Forbid an unproven cleanup claim after the synthetic stall.
        self.assertEqual(result["controller_error"], "TimeoutError")  # Preserve the fixed bounded profile-staleness diagnostic.

    # Prove the formal deadline traverses the production shard cleanup and persists terminal artifact evidence.
    def test_formal_worker_timeout_cleans_real_shard_and_writes_report(self):
        events = []  # Capture cleanup order without starting a server or browser.

        class Client:
            base_url = "http://127.0.0.1:1/"

            def call(self, path, method="GET", payload=None):
                return {"ready": True} if path == "/api/v2/admin/operations" else {}

            def login_default_user(self):
                return None

        class Context:
            async def new_page(self):
                return object()

            async def close(self):
                events.append("context")

        class Browser:
            async def new_context(self, **_kwargs):
                return Context()

            async def close(self):
                events.append("browser")

        class Chromium:
            async def launch(self, **_kwargs):
                return Browser()

        class Playwright:
            chromium = Chromium()

        async def stall_login(*_args):
            await asyncio.Event().wait()  # Hold inside the real shard after every tracked resource exists.

        def stop_tracked_server(_proc, _client):
            events.append("server")
            return {"closed": True}

        allocation = ui_50000.formal_allocations()[0]
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            deployment = root / "deployment"
            deployment.mkdir()
            args = argparse.Namespace(allocation_index=0, evidence_root=str(root / "visual"), shard_report_root=str(root / "shards"), keep_deployments=False, headed=False)
            patches = (
                mock.patch.object(ui_50000, "FORMAL_EXECUTION_BUDGET_SECONDS", 0.001),
                mock.patch.object(ui_50000, "prepare_deployment", return_value=deployment),
                mock.patch.object(ui_50000, "start_ui_server", return_value=(object(), Client())),
                mock.patch.object(ui_50000, "create_synthetic_user", return_value={"email": "fixture", "password": "fixture"}),
                mock.patch.object(ui_50000, "attach_page_diagnostics"),
                mock.patch.object(ui_50000, "login_through_ui", side_effect=stall_login),
                mock.patch.object(ui_50000, "stop_server", side_effect=stop_tracked_server),
                mock.patch("builtins.print"),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
                result = asyncio.run(ui_50000.run_bounded_shard(Playwright(), asyncio.Semaphore(1), args, allocation, "run", "a" * 40))
            report = json.loads((root / "shards" / "00-roulette-r0.json").read_text(encoding="utf-8"))
            self.assertFalse(deployment.exists())  # Remove only the isolated runtime after its listener closes.
        self.assertEqual(events, ["context", "browser", "server"])  # Preserve complete resource teardown order.
        self.assertEqual((result["status"], result["failed"], result["listener_cleanup"]), ("FAIL", allocation[3], {"closed": True}))  # Return truthful cleanup while failing every unfinished case.
        self.assertEqual((report["status"], report["failed"], report["fatal_error"]["message"]), ("FAIL", allocation[3], "CancelledError"))  # Persist fail-closed terminal artifact evidence.
        self.assertIn("ui_process_seconds", report)  # Keep cancellation timing available for hosted profile review.

    # Prove formal liveness is time-based and sanitized instead of waiting for one hundred completed cycles.
    def test_formal_worker_heartbeat_identifies_immutable_range(self):
        allocation = ui_50000.formal_allocations()[0]  # Use one canonical hosted range with no browser work.
        cadences = []  # Capture the requested interval independently of any cycle counter.

        async def stop_after_cadence(seconds):
            cadences.append(seconds)  # Observe the requested wall-clock interval without actually waiting.
            raise asyncio.CancelledError  # End the perpetual production loop after its first emission.

        with mock.patch("builtins.print") as emit, mock.patch.object(formal_ui_profile.asyncio, "sleep", side_effect=stop_after_cadence):
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(ui_50000.formal_worker_heartbeat(0, allocation, interval_seconds=60))  # Exercise only the browser-free monitoring seam.
        line = emit.call_args.args[0]  # Inspect the single sanitized heartbeat string.
        self.assertIn("UI50K HEARTBEAT allocation=0 game=roulette replica=0 range=0-100", line)  # Bind liveness to immutable allocation identity.
        self.assertIn("budget_seconds=1020", line)  # Expose the checked-in cleanup-margin deadline in live Actions output.
        self.assertNotIn("completed=", line)  # Never let liveness imply browser progress while an action may be stalled.
        self.assertEqual(cadences, [60])  # Pin a time-based cadence independent of the one-hundred-cycle progress setting.

    # Prove namespacing prevents identical generic selectors from merging across games.
    def test_control_signatures_keep_module_ownership(self):
        roulette = ui_50000.qualify_control_signature("button[data-action=deal]", "roulette")  # Qualify one generic selector for Roulette.
        baccarat = ui_50000.qualify_control_signature("button[data-action=deal]", "baccarat")  # Qualify the same selector for Baccarat.
        self.assertNotEqual(roulette, baccarat)  # Require independent coverage identities.

    # Prove every observed control receives exactly one honest acceptance classification.
    def test_control_coverage_classifies_floor_conditional_failure_and_exclusion(self):
        seen = Counter({"roulette::button[data-testid=spin]": 120, "blackjack::button[data-action=insurance]": 12, "baccarat::button[data-action=deal]": 200, "auth::input[data-testid=login-email]": 1, "casino_war::button[data-action=surrender]": 124, "casino_war::button[data-action=war]": 124})  # Model ordinary, rare, skipped, lifecycle, and shared rare-state controls.
        activated = Counter({"roulette::button[data-testid=spin]": 120, "blackjack::button[data-action=insurance]": 6, "auth::input[data-testid=login-email]": 1, "casino_war::button[data-action=surrender]": 60, "casino_war::button[data-action=war]": 64})  # Exercise passing and finite mutually exclusive controls through real sampled opportunities.
        result = ui_50000.classify_control_coverage(seen, activated)  # Apply the durable policy.
        self.assertIn("roulette::button[data-testid=spin]", result["exercised"])  # Accept the literal 100-activation floor.
        self.assertIn("blackjack::button[data-action=insurance]", result["intentionally_unavailable"])  # Accept a rare control only with real activation evidence.
        self.assertIn("baccarat::button[data-action=deal]", result["failed"])  # Fail an ordinarily reachable skipped control.
        self.assertIn("auth::input[data-testid=login-email]", result["excluded"])  # Keep one-time authentication outside gameplay counts.
        self.assertIn("casino_war::button[data-action=surrender]", result["intentionally_unavailable"])  # Accept only an exercised alternative whose fair share of rare tie states is below the floor.
        self.assertIn("casino_war::button[data-action=war]", result["intentionally_unavailable"])  # Preserve the paired alternative under the same explicit finite-state rule.
        self.assertEqual(result["intentionally_unavailable"]["casino_war::button[data-action=war]"]["opportunities"], 64)  # Never report fewer opportunities than the control's actual activations.
        self.assertEqual(result["classified_count"], 6)  # Require complete mutually exclusive accounting.

    # Prove focused profiles exempt only registered navigation for deliberately unselected games.
    def test_control_coverage_scopes_only_unselected_registered_game_navigation(self):
        baccarat_nav = "shell::button[data-testid=nav-baccarat]"  # Name selected navigation that must remain subject to the literal floor.
        roulette_nav = "shell::button[data-testid=nav-roulette]"  # Name registered navigation deliberately omitted from the focused profile.
        roulette_open = "shell::button[data-testid=open-roulette]"  # Cover the second governed catalog routing identity.
        unknown_nav = "shell::button[data-testid=nav-not_registered]"  # Model a malformed or future identity that cannot receive an implicit waiver.
        deal = "baccarat::button[data-testid=baccarat-deal]"  # Keep the selected game-owned action above its floor.
        seen = Counter({baccarat_nav: 120, roulette_nav: 1, roulette_open: 1, unknown_nav: 1, deal: 2_000})  # Reproduce focused discovery of the complete shell beside repeated Baccarat actions.
        activated = Counter({baccarat_nav: 120, deal: 2_000})  # Exercise only the selected route and game-owned action.
        default_result = ui_50000.classify_control_coverage(seen, activated)  # Preserve strict behavior when no focused selection is declared.
        focused_result = ui_50000.classify_control_coverage(seen, activated, selected_games={"baccarat"})  # Apply the explicit Baccarat-only scope.
        full_catalog_result = ui_50000.classify_control_coverage(seen, activated, selected_games=set(ui_50000.GAME_IDS))  # Model the formal catalog scope.
        self.assertIn(roulette_nav, default_result["failed"])  # Keep direct/default TEST-092 classification fail closed.
        self.assertIn(roulette_nav, full_catalog_result["failed"])  # Keep formal full-catalog navigation under the activation floor.
        self.assertIn(roulette_nav, focused_result["excluded"])  # Exclude only the omitted registered route from focused acceptance.
        self.assertIn(roulette_open, focused_result["excluded"])  # Apply the same exact rule to lobby open controls.
        self.assertEqual(focused_result["excluded"][roulette_nav]["reason"], "unselected registered-game navigation outside focused profile")  # Publish a durable non-waiver explanation.
        self.assertIn(unknown_nav, focused_result["excluded"])  # Keep unregistered or utility-like shell identities outside the gameplay floor.
        self.assertEqual(focused_result["excluded"][unknown_nav]["reason"], "non-gameplay shell control")  # Prevent a nav-shaped utility from becoming eligible by prefix alone.
        self.assertIn(baccarat_nav, focused_result["exercised"])  # Keep selected navigation on the literal floor.
        self.assertIn(deal, focused_result["exercised"])  # Keep selected game-owned actions fully governed.

    # Prove every exact formal game continues one deterministic schedule across worker boundaries.
    def test_coverage_ordinal_continues_every_formal_replica(self):
        self.assertEqual(ui_50000.coverage_ordinal("roulette", 0, 417), 417)  # Continue Roulette after the prior replica's exact range.
        self.assertEqual(ui_50000.coverage_ordinal("blackjack", 0, 6667), 0)  # Preserve the local first-one-hundred budgets for ordinary games.
        keno_allocations = [allocation for allocation in ui_50000.formal_allocations() if allocation[0] == "keno"]  # Read the exact six-worker Keno plan.
        first, second = keno_allocations[:2]  # Resolve one real replica boundary from the governed profile.
        self.assertEqual(ui_50000.coverage_ordinal("keno", 0, second[4], True), first[3])  # Continue immediately after the preceding worker's quota.

    # Prove locale synchronization observes old-node detachment before replacement-form readiness.
    def test_login_locale_synchronization_orders_detachment_before_new_form(self):
        events = []  # Record the exact browser-owned transition sequence without launching Chromium.

        class FakeGateHandle:  # Model the captured old DOM owner independently from later locator resolution.
            async def wait_for_element_state(self, state, timeout):
                events.append(("old_gate", state, timeout))  # Record the detachment/hide oracle before replacement lookup.

        class FakeLocator:  # Provide only the current gate and locale-control surfaces used by the helper.
            def __init__(self, test_id):
                self.test_id = test_id  # Preserve the stable public identity for assertions.

            async def element_handle(self):
                events.append(("element_handle", self.test_id))  # Capture the exact pre-change node first.
                return FakeGateHandle()  # Return one immutable old-node handle.

            async def select_option(self, locale, timeout):
                events.append(("select", self.test_id, locale, timeout))  # Record visible selection before detachment.

        class FakePage:  # Model locator replacement and the final attached-form predicate.
            def get_by_test_id(self, test_id):
                return FakeLocator(test_id)  # Resolve current semantic locators by public identity.

            async def wait_for_function(self, expression, arg, timeout):
                events.append(("replacement", arg, timeout, "login-submit" in expression))  # Require committed locale and complete replacement fields.

        counts = Counter()  # Capture the successful locale activation identity.
        with mock.patch.object(ui_50000, "control_signature", new=mock.AsyncMock(return_value="auth::select[data-testid=auth-locale-select]")):  # Isolate signature extraction from DOM evaluation.
            asyncio.run(ui_50000.synchronize_login_locale(FakePage(), "ru-RU", counts, lambda: 3210))  # Exercise the ordered helper with one unchanged caller deadline.
        self.assertEqual(events, [("element_handle", "login-gate"), ("select", "auth-locale-select", "ru-RU", 3210), ("old_gate", "hidden", 3210), ("replacement", "ru-RU", 3210, True)])  # Reject credential readiness before old-node detachment.
        self.assertEqual(counts, Counter({"auth::select[data-testid=auth-locale-select]": 1}))  # Count only a complete replacement transition.

    # Prove Rebet closes a real activation deficit beyond the first hundred cycles without duplicating work across Roulette shards.
    def test_roulette_rebet_retries_only_primary_shard_until_floor(self):
        signature = ui_50000.qualify_control_signature("button#rebet", "roulette")  # Resolve the exact aggregate signature used by the formal report.
        under_floor = Counter({signature: 80})  # Reproduce the frozen aggregate's twenty-activation deficit.
        at_floor = Counter({signature: ui_50000.CONTROL_ACTIVATION_FLOOR})  # Model the completed literal acceptance floor.
        self.assertTrue(ui_50000.should_exercise_roulette_rebet(0, under_floor))  # Continue real rendered attempts on the first Roulette shard after cycle one hundred.
        self.assertFalse(ui_50000.should_exercise_roulette_rebet(1, under_floor))  # Prevent every later replica from restarting the same control budget.
        self.assertFalse(ui_50000.should_exercise_roulette_rebet(0, at_floor))  # Stop immediately after one hundred successful pointer activations.
        exact_primary = Counter()  # Simulate the frozen 101-cycle primary shard with cycle zero reserved for its seed spin.
        rebet_ranks = []  # Record only cycles that can see and activate the real restored template.
        for game_ordinal in range(101):  # Reproduce every exact primary rank once.
            if game_ordinal > 0 and ui_50000.should_exercise_roulette_rebet(0, exact_primary):  # Model disabled Rebet before rank-zero settlement and ready Rebet thereafter.
                exact_primary[signature] += 1  # Count the successful real pointer activation.
                rebet_ranks.append(game_ordinal)  # Preserve exact affinity evidence.
        self.assertEqual((rebet_ranks, exact_primary[signature]), (list(range(1, 101)), 100))  # Require exactly ranks1..100 and no overrun.
        play_source = (ui_50000.ROOT / "tests" / "ui_50000.py").read_text(encoding="utf-8")  # Read the exact dispatch owner for ordering governance.
        rebet_position = play_source.index("if should_exercise_roulette_rebet(replica_index, activated_counts)")  # Locate the real ready-template attempt.
        configuration_position = play_source.index("await exercise_configuration_controls(page, ordinal, activated_counts)", rebet_position)  # Locate the next generic mutation boundary.
        self.assertLess(rebet_position, configuration_position)  # Preserve Rebet before configuration and autoplay can invalidate its template.
        scheduled_settings_position = play_source.index("await exercise_roulette_settings_controls(page, game_ordinal, activated_counts)", configuration_position)  # Locate the deterministic serialized settings schedule.
        exact_mode_position = play_source.index("await ensure_roulette_mode(page, mode, activated_counts)", scheduled_settings_position)  # Locate scheduled-mode enforcement after any opposite-mode probe.
        self.assertLess(configuration_position, scheduled_settings_position)  # Keep client-only generic configuration before server-owned settings work.
        self.assertLess(scheduled_settings_position, exact_mode_position)  # Require every probe to complete before exact mode restoration.

    # Prove each Roulette settings selection finishes its exact response and replacement generation before another selection can begin.
    def test_roulette_setting_selection_serializes_response_and_generation(self):
        events = []  # Record only public locator, response, selection, detachment, and replacement-readiness boundaries.
        values = {"roulette-mode": "double", "roulette-zero": "normal"}  # Model the accepted rendered settings generation.
        generation = {"value": 0}  # Distinguish every response-owned DOM replacement.

        class FakeHandle:  # Preserve the selected pre-response node identity.
            def __init__(self, test_id, owned_generation):
                self.test_id = test_id  # Retain only the public setting identity.
                self.generation = owned_generation  # Retain the exact old generation for detachment evidence.

        class FakeLocator:  # Model one current server-owned Roulette select.
            def __init__(self, test_id):
                self.test_id = test_id  # Preserve the public data-testid.

            async def wait_for(self, state, timeout):
                events.append(("visible", self.test_id, state, timeout, generation["value"]))  # Require actionability on the current generation.

            async def element_handle(self):
                events.append(("handle", self.test_id, generation["value"]))  # Capture the exact pre-request generation.
                return FakeHandle(self.test_id, generation["value"])  # Return one immutable old node.

            async def input_value(self):
                events.append(("value", self.test_id, generation["value"]))  # Read the accepted current value before request dispatch.
                return values[self.test_id]  # Return only the rendered value.

        class FakeResponse:  # Model one exact public settings response.
            def __init__(self, ok=True):
                self.ok = ok  # Expose server acceptance without a body.

        class FakeResponseInfo:  # Model Playwright's async response observation.
            def __init__(self, page):
                self.page = page  # Retain the owning page's configured response result.

            async def __aenter__(self):
                events.append(("response-armed", generation["value"]))  # Require observation before the real selection.
                return self  # Return the awaitable response facade.

            async def __aexit__(self, *_args):
                events.append(("response-captured", generation["value"]))  # Record terminal response capture after selection.

            @property
            def value(self):
                async def resolve():
                    events.append(("response-value", generation["value"]))  # Resolve the exact response before DOM acceptance.
                    return FakeResponse(self.page.response_ok)  # Return the configured public status.
                return resolve()  # Match Playwright's awaitable property.

        class FakePage:  # Provide the exact public browser seams owned by the helper.
            response_ok = True  # Start with accepted settings responses.

            def get_by_test_id(self, test_id):
                events.append(("locator", test_id, generation["value"]))  # Record each current-generation locator lookup.
                return FakeLocator(test_id)  # Resolve against the latest generation.

            def expect_response(self, predicate, timeout):
                candidate = type("Response", (), {"url": "http://test/api/v1/games/roulette/settings", "request": type("Request", (), {"method": "POST"})()})()  # Build one exact public response identity.
                events.append(("expect", predicate(candidate), timeout, generation["value"]))  # Prove endpoint/method filtering and unchanged deadline.
                return FakeResponseInfo(self)  # Arm one response observation.

            async def wait_for_function(self, expression, arg, timeout):
                if isinstance(arg, FakeHandle):  # Distinguish old-generation detachment from fresh-render acceptance.
                    events.append(("detached", arg.test_id, arg.generation, generation["value"], "isConnected" in expression, timeout))  # Require exact old identity after response.
                    return  # Complete only the detachment boundary.
                events.append(("fresh", arg["test_id"], arg["value"], generation["value"], timeout))  # Require the accepted fresh setting and catalog generation.

        page = FakePage()  # Create one isolated fake rendered Roulette surface.

        async def fake_select_control(locator, value, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(("select", locator.test_id, str(value), generation["value"], timeout_ms))  # Record one real rendered select activation.
            values[locator.test_id] = str(value)  # Publish the accepted setting value.
            generation["value"] += 1  # Model the response-owned full rerender.

        with mock.patch.object(ui_50000, "select_control", side_effect=fake_select_control):  # Isolate selection bookkeeping from DOM signature evaluation.
            asyncio.run(ui_50000.select_roulette_setting(page, "roulette-zero", "la_partage", Counter()))  # Commit one zero-rule transition.
            first_selection_end = len(events)  # Capture the exact boundary before another settings request starts.
            asyncio.run(ui_50000.select_roulette_setting(page, "roulette-mode", "single", Counter()))  # Commit one later mode transition.
        first_detach = next(index for index, event in enumerate(events[:first_selection_end]) if event[0] == "detached")  # Locate old-node invalidation for the first request.
        first_fresh = next(index for index, event in enumerate(events[:first_selection_end]) if event[0] == "fresh")  # Locate replacement acceptance for the first request.
        second_arm = next(index for index, event in enumerate(events[first_selection_end:], start=first_selection_end) if event[0] == "response-armed")  # Locate the second request boundary.
        self.assertLess(first_detach, first_fresh)  # Require old-node detachment before fresh-generation readiness.
        self.assertLess(first_fresh, second_arm)  # Forbid overlapping settings requests across sequential helper calls.
        self.assertEqual(sum(event[0] == "select" for event in events), 2)  # Dispatch exactly one real selection per exact response.
        self.assertEqual(sum(event[0] == "response-armed" for event in events), 2)  # Arm exactly one public settings response per selection.
        page.response_ok = False  # Model a server-rejected settings transition without retry authority.
        with mock.patch.object(ui_50000, "select_control", side_effect=fake_select_control):  # Reuse the exact real-selection seam.
            with self.assertRaisesRegex(AssertionError, "settings request failed"):
                asyncio.run(ui_50000.select_roulette_setting(page, "roulette-zero", "normal", Counter()))  # Fail closed on the single rejected response.

    # Prove Roulette cannot mistake its pre-click enabled node for post-settlement readiness.
    def test_roulette_terminal_action_observes_resolving_before_ready(self):
        events = []  # Record the browser-free synchronization order.

        class FakePage:  # Provide only the page method owned by the transition helper.
            async def wait_for_function(self, expression, timeout):
                events.append("resolving")  # Record the explicit busy-state observation between click and readiness.
                self.expression = expression  # Preserve the browser predicate for semantic assertions.
                self.timeout = timeout  # Preserve the governed action bound for semantic assertions.

        async def fake_click_control(_page, selector, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            self.assertEqual(selector, '[data-testid="roulette-spin"]')  # Require the public Roulette control identity.
            self.assertEqual(timeout_ms, ui_50000.ACTION_TIMEOUT_MS)  # Preserve the default bounded pointer action.
            events.append("click")  # Record the real-action boundary before the busy-state wait.

        async def fake_wait_any_enabled(_page, selectors, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            self.assertEqual(selectors, ['[data-testid="roulette-spin"]'])  # Require the same control to define fresh-round readiness.
            self.assertEqual(timeout_ms, ui_50000.ACTION_TIMEOUT_MS)  # Preserve the default bounded settlement wait.
            events.append("ready")  # Record terminal readiness only after the resolving observation.
            return selectors[0]  # Model one genuinely enabled post-settlement control.

        page = FakePage()  # Create one browser-free transition recorder.
        with mock.patch.object(ui_50000, "click_control", side_effect=fake_click_control), mock.patch.object(ui_50000, "wait_any_enabled", side_effect=fake_wait_any_enabled):  # Isolate synchronization order from Playwright.
            asyncio.run(ui_50000.roulette_terminal_action(page, Counter()))  # Exercise the helper without launching a browser.
        self.assertEqual(events, ["click", "resolving", "ready"])  # Reject any return to readiness before the disabled resolving state.
        self.assertIn("roulette-result-region", page.expression)  # Bind the predicate to the visible phase contract.
        self.assertIn("spin?.disabled", page.expression)  # Require the public button to be non-actionable during resolution.
        self.assertEqual(page.timeout, ui_50000.ACTION_TIMEOUT_MS)  # Keep transition observation inside the governed action timeout.

    # Prove Roulette serializes refund and wager rerenders before the strict spinning-state transition.
    def test_roulette_reset_seed_and_spin_orders_every_drawer_boundary(self):
        events = []  # Record only public UI mutation and committed-state boundaries.

        class FakeLocator:  # Model one rendered removal or replacement control.
            def __init__(self, name):
                self.name = name  # Preserve a stable semantic name for the event trace.

        class FakePage:  # Supply the page only as an identity passed through patched helpers.
            pass  # No private browser behavior is needed for this browser-free ordering proof.

        remove = [FakeLocator("remove-0"), FakeLocator("remove-1")]  # Model two committed open wagers before the contextual refund.
        replacement = [FakeLocator("number-0")]  # Model one playable straight-up target after clear-all.

        async def fake_enabled_locators(_page, selector):
            events.append(f"discover:{selector}")  # Record each DOM re-resolution boundary.
            return remove if selector == "[data-clear]" else replacement  # Return the state-owned control collection.

        async def fake_click_locator(locator, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"click:{locator.name}")  # Record the contextual refund pointer action.

        async def fake_wait_drawer(_page, expected_rows, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"drawer:{expected_rows}")  # Record the exact committed drawer size before continuing.

        async def fake_click_control(_page, selector, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"click:{selector}")  # Record clear-all through its public selector.

        async def fake_add_bet(_page, locator, _activated_counts):
            events.append(f"add:{locator.name}")  # Record the replacement wager plus its internal populated-drawer wait.

        async def fake_terminal(_page, _activated_counts):
            events.append("spin")  # Record the strict spinning-state helper only after every drawer boundary.

        with mock.patch.object(ui_50000, "enabled_locators", side_effect=fake_enabled_locators), mock.patch.object(ui_50000, "click_locator", side_effect=fake_click_locator), mock.patch.object(ui_50000, "wait_roulette_bet_drawer", side_effect=fake_wait_drawer), mock.patch.object(ui_50000, "click_control", side_effect=fake_click_control), mock.patch.object(ui_50000, "roulette_add_bet", side_effect=fake_add_bet), mock.patch.object(ui_50000, "roulette_terminal_action", side_effect=fake_terminal):  # Isolate the exact mutation order from Playwright and network timing.
            asyncio.run(ui_50000.roulette_reset_seed_and_spin(FakePage(), 1, Counter()))  # Select the second contextual row and execute the complete ordered seam.
        self.assertEqual(events, ["discover:[data-clear]", "click:remove-1", "drawer:1", "click:#clear", "drawer:0", 'discover:[data-testid^="roulette-num-"]', "add:number-0", "spin"])  # Require every refund/wager rerender before the terminal click.

    # Prove each single or multi-component Roulette wager waits for a populated response-owned drawer rerender.
    def test_roulette_add_bet_waits_for_committed_row_growth(self):
        events = []  # Record the committed row count, pointer action, and minimum populated boundary.

        class FakeRows:  # Model the current committed removable-wager collection.
            async def count(self):
                events.append("count:7")  # Record the pre-action drawer inventory.
                return 7  # Model seven existing rows before a single or call-bet request.

        class FakePage:  # Provide the one public selector lookup owned by the helper.
            def locator(self, selector):
                self.selector = selector  # Preserve the requested removable-row selector.
                return FakeRows()  # Return the current committed drawer collection.

        async def fake_click_locator(locator, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"click:{locator}")  # Record the pointer dispatch after the baseline count.

        async def fake_wait_minimum(_page, minimum_rows, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"minimum:{minimum_rows}")  # Record the required post-response lower bound.

        page = FakePage()  # Create one isolated page seam for the asynchronous wager helper.
        with mock.patch.object(ui_50000, "click_locator", side_effect=fake_click_locator), mock.patch.object(ui_50000, "wait_roulette_bet_drawer_minimum", side_effect=fake_wait_minimum):  # Isolate ordering from Playwright and API timing.
            asyncio.run(ui_50000.roulette_add_bet(page, "roulette-target", Counter()))  # Exercise one rendered wager mutation.
        self.assertEqual(page.selector, "[data-clear]")  # Count only public removable wager rows.
        self.assertEqual(events, ["count:7", "click:roulette-target", "minimum:8"])  # Require response-owned row growth before the helper returns.

    # Prove draw poker waits for all five positions, balances the activation deficit, and observes the persisted held rerender before Draw.
    def test_draw_poker_hold_waits_balances_and_commits(self):
        events = []  # Record each public decision-state and pointer boundary without launching a browser.

        class FakeHold:  # Model one response-owned hold control with a stable semantic position.
            def __init__(self, position):
                self.position = str(position)  # Preserve the same string-valued dataset identity exposed by the DOM.

            async def get_attribute(self, name):
                self.requested_attribute = name  # Retain the requested public attribute for debugging this test seam.
                return self.position  # Return the rendered hold position used by aggregate signatures.

        class FakePage:  # Provide only the committed-state predicate boundary owned by the helper.
            async def wait_for_function(self, expression, arg, timeout):
                events.append(f"committed:{arg}")  # Record the selected hold's persisted rerender after the click.
                self.expression = expression  # Preserve the public DOM predicate for semantic assertions.
                self.timeout = timeout  # Preserve the governed action bound.

        holds = [FakeHold(position) for position in range(5)]  # Model the complete five-card decision state.

        async def fake_wait_any_enabled(_page, selectors, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"wait:{selectors[0]}")  # Record the async Deal-to-Hold boundary.
            return selectors[0]  # Model a genuinely enabled unheld source card.

        async def fake_inventory_controls(_page, _seen_counts):
            events.append("inventory")  # Record discovery only after the decision state is committed.

        async def fake_enabled_locators(_page, selector):
            events.append(f"discover:{selector}")  # Record response-owned locator resolution.
            return holds  # Expose every authoritative source-card position.

        async def fake_control_signature(locator):
            events.append(f"score:{locator.position}")  # Record that every authoritative position participates in the real deficit selector.
            return f"jacks_or_better_video_poker::button[data-hold-position={locator.position}]"  # Return the aggregate identity scored by production code.

        async def fake_click_locator(locator, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"click:{locator.position}")  # Record the real pointer boundary before committed-state observation.

        page = FakePage()  # Create one browser-free public state-machine seam.
        activated = Counter({f"jacks_or_better_video_poker::button[data-hold-position={position}]": 100 + position for position in range(5)})  # Give every position a passing but distinct activation count.
        activated["jacks_or_better_video_poker::button[data-hold-position=3]"] = 12  # Reproduce one material aggregate deficit that must win selection.
        with mock.patch.object(ui_50000, "wait_any_enabled", side_effect=fake_wait_any_enabled), mock.patch.object(ui_50000, "inventory_controls", side_effect=fake_inventory_controls), mock.patch.object(ui_50000, "enabled_locators", side_effect=fake_enabled_locators), mock.patch.object(ui_50000, "control_signature", side_effect=fake_control_signature), mock.patch.object(ui_50000, "click_locator", side_effect=fake_click_locator):  # Isolate the exact wait, discovery, real deficit selection, click, and commit order.
            asyncio.run(ui_50000.draw_poker_select_balanced_hold(page, Counter(), activated))  # Exercise the complete draw-poker synchronization helper.
        selector = '[data-hold-position][aria-pressed="false"]'  # Reuse the expected public unheld-card identity.
        self.assertEqual(events, [f"wait:{selector}", "inventory", f"discover:{selector}", "score:0", "score:1", "score:2", "score:3", "score:4", "click:3", "committed:3"])  # Reject early discovery, unbalanced selection, or Draw-before-commit ordering.
        self.assertIn("aria-pressed", page.expression)  # Bind the response boundary to the visible selected state.
        self.assertIn("!node.disabled", page.expression)  # Require the public hold response to leave the hand actionable.
        self.assertEqual(page.timeout, ui_50000.ACTION_TIMEOUT_MS)  # Keep the network-backed hold transition bounded.

    # Prove Double Bonus completes the shared Deal, five-position hold, committed-hold, and Draw sequence through its rendered attribute dialect.
    def test_double_bonus_draw_poker_uses_rendered_controls_without_changing_family_defaults(self):
        events = []  # Record the complete browser-free rendered-control order.

        class FakeHold:  # Model one of the five Double Bonus source-card buttons.
            def __init__(self, position):
                self.position = str(position)  # Preserve the public data-hold identity.

            async def get_attribute(self, name):
                self.requested_attribute = name  # Retain the exact semantic attribute used by the harness.
                return self.position  # Return the stable zero-based card position.

        class FakePage:  # Provide only the committed held-card predicate boundary.
            async def wait_for_function(self, expression, arg, timeout):
                events.append(f"committed:{arg}")  # Require the hold rerender before Draw.
                self.expression = expression  # Preserve the rendered-state predicate for assertions.
                self.timeout = timeout  # Preserve the unchanged action timeout.

        holds = [FakeHold(position) for position in range(5)]  # Expose the complete five-position decision state.

        async def fake_inventory_controls(_page, _seen_counts):
            events.append("inventory")  # Record both ready-state and post-deal inventory boundaries.

        async def fake_configuration(_page, _ordinal, _activated_counts):
            events.append("configuration")  # Preserve the existing pre-deal configuration stage.

        async def fake_autoplay(_page, _ordinal, _activated_counts):
            events.append("autoplay")  # Preserve the existing shared control-plane stage.

        async def fake_enabled_locators(_page, selector):
            events.append(f"discover:{selector}")  # Record mode discovery and five-card discovery distinctly.
            return holds if selector == '[data-hold][aria-pressed="false"]' else []  # Expose holds only after the rendered Deal state.

        async def fake_click_control(_page, selector, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"control:{selector}")  # Record real Deal and Draw selector dispatch boundaries.
            return selector  # Preserve the click helper's stable signature-shaped return seam.

        async def fake_wait_any_enabled(_page, selectors, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"wait:{selectors[0]}")  # Record both deal-to-hold and terminal-to-next-deal waits.
            return selectors[0]  # Model a visible enabled rendered control.

        async def fake_control_signature(locator):
            events.append(f"score:{locator.position}")  # Require every position to participate in deficit balancing.
            return f"double_bonus_video_poker::button[data-hold={locator.position}]"  # Use the stable aggregate identity added for Double Bonus.

        async def fake_click_locator(locator, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
            events.append(f"hold:{locator.position}")  # Record the one balanced real pointer hold activation.

        activated = Counter({f"double_bonus_video_poker::button[data-hold={position}]": 100 + position for position in range(5)})  # Start with distinct passing counts.
        activated["double_bonus_video_poker::button[data-hold=2]"] = 3  # Make position two the unique aggregate deficit.
        page = FakePage()  # Create one isolated deterministic browser seam.
        with mock.patch.object(ui_50000, "inventory_controls", side_effect=fake_inventory_controls), mock.patch.object(ui_50000, "exercise_configuration_controls", side_effect=fake_configuration), mock.patch.object(ui_50000, "exercise_autoplay_controls", side_effect=fake_autoplay), mock.patch.object(ui_50000, "enabled_locators", side_effect=fake_enabled_locators), mock.patch.object(ui_50000, "click_control", side_effect=fake_click_control), mock.patch.object(ui_50000, "wait_any_enabled", side_effect=fake_wait_any_enabled), mock.patch.object(ui_50000, "control_signature", side_effect=fake_control_signature), mock.patch.object(ui_50000, "click_locator", side_effect=fake_click_locator):  # Isolate exact selector and ordering behavior without Playwright or Chromium.
            asyncio.run(ui_50000.play_game_ui(page, "double_bonus_video_poker", 7, Counter(), activated))  # Execute one complete Double Bonus formal strategy cycle.
        self.assertEqual(events, ["inventory", "configuration", "autoplay", "discover:[data-hand-count],[data-coin-count]", "control:[data-deal]", 'wait:[data-hold][aria-pressed="false"]', "inventory", 'discover:[data-hold][aria-pressed="false"]', "score:0", "score:1", "score:2", "score:3", "score:4", "hold:2", "committed:2", "control:[data-draw]", "wait:[data-deal]", "inventory"])  # Require the full rendered Deal-to-Draw state machine and terminal inventory without timeout-only selectors.
        self.assertTrue(all(hold.requested_attribute == "data-hold" for hold in holds))  # Require all five controls to share the registered semantic position attribute.
        self.assertIn("[data-hold]", page.expression)  # Bind committed-state observation to Double Bonus markup.
        self.assertIn("aria-pressed", page.expression)  # Preserve the visible selected-state contract.
        self.assertEqual(page.timeout, ui_50000.ACTION_TIMEOUT_MS)  # Preserve the established hold-response wait budget.
        self.assertEqual(ui_50000.DRAW_POKER_UI_CONTROLS["default"], {"deal": '[data-action="deal"]', "hold_attribute": "data-hold-position", "draw": '[data-action="draw"]'})  # Prove every previously qualified draw-poker family retains its exact selectors.
        other_draw_games = {game_id for game_id, family in ui_50000.UI_STRATEGY_FAMILIES.items() if family == "draw_poker"}.difference({"double_bonus_video_poker"})  # Derive every already-qualified shared family member independently of catalog order.
        self.assertTrue(all(ui_50000.DRAW_POKER_UI_CONTROLS.get(game_id, ui_50000.DRAW_POKER_UI_CONTROLS["default"]) is ui_50000.DRAW_POKER_UI_CONTROLS["default"] for game_id in other_draw_games))  # Reject an accidental selector override for any predecessor draw-poker route.

    # Prove Acey-Deucey deals before editing its phase-owned wager and skips that edit for Pass or automatic settlement.
    def test_acey_deucey_orders_wager_after_deal_only_for_play(self):
        # Execute one browser-free decision scenario and return its exact public interaction order.
        async def run_scenario(decision_action):
            events = []  # Record only semantic harness boundaries, never private runtime data.

            class FakeDecision:  # Model one already-actionability-filtered decision locator.
                def __init__(self, action):
                    self.action = action  # Preserve the public data-action value used by the helper.

                async def get_attribute(self, name):
                    self.assert_name = name  # Retain the requested attribute for the enclosing assertion seam.
                    return self.action  # Return the stable Play or Pass identity.

            class FakeCollection:  # Model Playwright's locator collection wrapper for the wager field.
                first = "wager-locator"  # Expose the same first-locator property used by production code.

            class FakePage:  # Provide only the selector lookup owned by the wager edit path.
                def locator(self, selector):
                    self.selector = selector  # Preserve the exact public wager selector for assertion.
                    return FakeCollection()  # Return the synthetic rendered input collection.

            page = FakePage()  # Create one isolated page seam for this state-machine scenario.
            waits = [decision_action if decision_action == '[data-action="deal"]' else f'[data-action="{decision_action}"]']  # Return automatic terminal state or the requested decision first.
            if decision_action != '[data-action="deal"]':  # Add the post-decision fresh-deal boundary for interactive scenarios.
                waits.append('[data-action="deal"]')  # Model successful settlement returning to ready.

            async def fake_click_control(_page, selector, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
                events.append(f"click:{selector}")  # Record the initial free boundary deal.

            async def fake_wait_any_enabled(_page, selectors, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
                events.append(f"wait:{'|'.join(selectors)}")  # Record each real state boundary before returning it.
                return waits.pop(0)  # Resolve the deterministic next public state.

            async def fake_inventory_controls(_page, _seen_counts):
                events.append("inventory")  # Record terminal or decision-state coverage discovery.

            async def fake_enabled_locators(_page, selector):
                self.assertEqual(selector, '[data-action="play"],[data-action="pass"]')  # Require the bounded decision selector.
                return [FakeDecision("play"), FakeDecision("pass")]  # Preserve rendered Play-before-Pass order.

            async def fake_fill_control(locator, value, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
                self.assertEqual(locator, "wager-locator")  # Require the public wager input seam.
                self.assertEqual(value, "1")  # Keep the synthetic play-token wager bounded.
                events.append("fill:wager")  # Record that editing occurs only after Deal exposes Play.

            async def fake_click_locator(locator, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
                events.append(f"click:{locator.action}")  # Record the selected rendered decision.

            patches = (  # Group the browser-free replacements around one helper invocation.
                mock.patch.object(ui_50000, "click_control", side_effect=fake_click_control),
                mock.patch.object(ui_50000, "wait_any_enabled", side_effect=fake_wait_any_enabled),
                mock.patch.object(ui_50000, "inventory_controls", side_effect=fake_inventory_controls),
                mock.patch.object(ui_50000, "enabled_locators", side_effect=fake_enabled_locators),
                mock.patch.object(ui_50000, "fill_control", side_effect=fake_fill_control),
                mock.patch.object(ui_50000, "click_locator", side_effect=fake_click_locator),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:  # Apply every interaction seam for this isolated scenario.
                ordinal = 0 if decision_action in {"play", '[data-action="deal"]'} else 1  # Select Play first, Pass second, or ignore decisions for automatic settlement.
                action_evidence = await ui_50000.acey_deucey_terminal_action(page, ordinal, Counter(), Counter())  # Exercise the production state ordering and capture the actual ledger expectation.
            self.assertFalse(waits)  # Require the helper to consume every modeled public state boundary.
            return events, action_evidence  # Return semantic order plus the actual action-aware ledger classification.

        decision_wait = 'wait:[data-action="play"]|[data-action="pass"]|[data-action="deal"]'  # Reuse the exact decision boundary in all scenarios.
        ready_wait = 'wait:[data-action="deal"]'  # Reuse the exact post-settlement boundary.
        play_events, play_evidence = asyncio.run(run_scenario("play"))  # Exercise the wager-consuming decision.
        self.assertEqual(play_events, ['click:[data-action="deal"]', decision_wait, "inventory", "fill:wager", "click:play", ready_wait])  # Require Deal before wager before Play.
        self.assertEqual(play_evidence, "wager_required")  # Require exact player-scoped ledger evidence for the committed Play wager.
        pass_events, pass_evidence = asyncio.run(run_scenario("pass"))  # Exercise the token-free decision.
        self.assertEqual(pass_events, ['click:[data-action="deal"]', decision_wait, "inventory", "click:pass", ready_wait])  # Forbid an unnecessary wager edit on Pass.
        self.assertEqual(pass_evidence, "non_wager")  # Accept Pass without fabricating a wager ledger row.
        automatic_events, automatic_evidence = asyncio.run(run_scenario('[data-action="deal"]'))  # Exercise an automatically terminal boundary pair.
        self.assertEqual(automatic_events, ['click:[data-action="deal"]', decision_wait, "inventory"])  # Return safely without fabricating a wager or decision.
        self.assertEqual(automatic_evidence, "non_wager")  # Accept the free-boundary automatic terminal state without a ledger mutation.

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
        allocations = ui_50000.formal_allocations()  # Build the immutable profiled formal assignment.
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
        allocations = ui_50000.formal_allocations()  # Build the immutable profiled formal assignment.
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
        allocations = ui_50000.formal_allocations()  # Build the immutable profiled formal assignment.
        source_commit = "f" * 40  # Use one valid immutable identity independent of optional release-copy Git metadata.
        with tempfile.TemporaryDirectory() as temporary_directory:  # Own and clean the complete downloaded-artifact simulation.
            root = Path(temporary_directory)  # Resolve the disposable aggregate root.
            shard_root = root / "shards"  # Separate terminal JSON from screenshots.
            evidence_root = root / "visual"  # Separate screenshots from aggregate reports.
            shard_root.mkdir(parents=True, exist_ok=True)  # Create the test-owned shard directory.
            self.write_distributed_corpus(shard_root, allocations, source_commit, evidence_root)  # Persist the complete current-catalog worker corpus.
            report_path = root / "aggregate.json"  # Resolve the test-owned terminal aggregate.
            args = argparse.Namespace(aggregate_only=True, allocation_index=None, source_commit=source_commit, only_games="", replicate_games="", total_cycles=50_000, roulette_replicas=4, game_replicas=4, shard_report_root=str(shard_root), evidence_root=str(evidence_root), report=str(report_path), parallel=4)  # Provide every aggregate-owned immutable option.
            with mock.patch.object(ui_50000, "resolve_distributed_source_commit", return_value=source_commit):  # Isolate aggregate accounting from the release builder's intentional metadata-free source copy.
                exit_code = asyncio.run(ui_50000.run_all(args))  # Execute aggregate accounting without importing or launching Playwright.
            report = json.loads(report_path.read_text(encoding="utf-8"))  # Read the generated terminal evidence.
            self.assertEqual(exit_code, 0)  # Require the aggregate controller to accept the complete corpus.
            self.assertEqual(report["status"], "PASS")  # Require every universal gate to resolve green.
            self.assertEqual(report["attempted_cycles"], 50_000)  # Require exact unique attempted-cycle accounting.
            self.assertEqual(report["completed_cycles"], 50_000)  # Require exact terminal completion accounting.
            self.assertTrue(report["assignment"]["no_gaps_or_duplicates"])  # Require the immutable global range proof.
            self.assertTrue(report["visuals_complete"])  # Require all 132 unique governed screenshots.
            first_allocation = allocations[0]  # Select one deterministic test-owned shard for a visual completeness regression.
            first_path = shard_root / f"{first_allocation[1]:02d}-{first_allocation[0]}-r{first_allocation[2]}.json"  # Resolve its exact distributed filename.
            incomplete = json.loads(first_path.read_text(encoding="utf-8"))  # Read the synthetic passing shard before introducing one bounded defect.
            incomplete["visuals"][0]["geometry"]["essential_stage_failures"] = [{"selector": ".stage", "reason": "essential node clipped by hidden ancestor"}]  # Model the human-found Big Six class that enabled-control geometry missed.
            first_path.write_text(json.dumps(incomplete), encoding="utf-8")  # Persist only the disposable incomplete-stage evidence.
            with mock.patch.object(ui_50000, "resolve_distributed_source_commit", return_value=source_commit):  # Keep the second aggregate browser-free and provenance-stable.
                rejected_exit_code = asyncio.run(ui_50000.run_all(args))  # Re-evaluate the complete corpus with one explicit essential-stage failure.
            rejected = json.loads(report_path.read_text(encoding="utf-8"))  # Read the fail-closed aggregate evidence.
            self.assertEqual(rejected_exit_code, 1)  # Reject an otherwise perfect 50,000-cycle corpus with clipped essential theater.
            self.assertEqual(rejected["status"], "FAIL")  # Keep the terminal qualification red for human-visible stage loss.
            self.assertEqual(len(rejected["visual_failures"]), 1)  # Preserve the exact single governed viewport failure.


# Run the focused module directly for local diagnosis.
if __name__ == "__main__":
    unittest.main()  # Return unittest's standard terminal status.
