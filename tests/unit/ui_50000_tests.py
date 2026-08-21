# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused TEST-092 proofs for the exact-source 50,000-cycle UI harness."""

import argparse  # Build narrow command namespaces without invoking the CLI parser.
import asyncio  # Exercise the browser-free aggregate controller end to end.
import json  # Persist synthetic shard reports for resume-policy tests.
import tempfile  # Own disposable report directories for every test.
import unittest  # Integrate the focused proofs with the repository API runner.
from collections import Counter  # Aggregate deterministic per-game allocation totals.
from pathlib import Path  # Address temporary shard reports with platform-neutral paths.
from unittest import mock  # Inject immutable provenance when release tests intentionally omit Git metadata.

from tests import baccarat_sustained, ui_50000  # Exercise both public qualification profiles without starting Playwright.


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
        sustained_job = workflow.split("  baccarat_sustained_2000:", 2)[2].split("  # Derive the formal issue #227", 1)[0]  # Isolate only the focused hosted job before formal planning begins.
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
        allocations = ui_50000.allocate_cycles(list(ui_50000.GAME_IDS), 50_000, 4, set(), 4)  # Build the formal deterministic assignment.
        per_game = Counter()  # Aggregate replica quotas back to canonical games.
        assigned_ids = []  # Reconstruct every global cycle ID for uniqueness evidence.
        for game_id, _game_index, _replica_index, quota, cycle_start in allocations:  # Inspect every bounded worker assignment.
            per_game[game_id] += quota  # Preserve the complete game quota across replicas.
            assigned_ids.extend(range(cycle_start, cycle_start + quota))  # Rebuild the worker's contiguous global range.
        self.assertEqual(sum(per_game.values()), 50_000)  # Require the exact formal total.
        self.assertEqual(len(per_game), len(ui_50000.GAME_IDS))  # Require every registered game exactly once in the aggregate.
        expected_floor = 50_000 // len(ui_50000.GAME_IDS)  # Derive the honest catalog-wide floor from the current registered game count.
        self.assertGreaterEqual(min(per_game.values()), expected_floor)  # Require every game to receive at least its exact balanced share.
        self.assertEqual(set(assigned_ids), set(range(50_000)))  # Require no missing or duplicate global identities.
        self.assertEqual(len(assigned_ids), len(set(assigned_ids)))  # Reject overlapping replica ranges.
        self.assertEqual(len(allocations), len(ui_50000.GAME_IDS) + 3)  # Pin one shard per game plus three additional Roulette replicas.

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
        semantic_attributes = ("data-number", "data-cell", "data-color", "data-rank", "data-marble", "data-card-index", "data-ante", "data-aces", "data-fold", "data-deal", "data-repeat")  # Enumerate the new strategy-owned identities that cannot fall back to translated text.
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

    # Prove the hosted matrix derives every exact allocation and grows with the catalog instead of a YAML list. (TEST-092)
    def test_formal_workflow_matrix_comes_from_canonical_allocator(self):
        current_indices = ui_50000.formal_allocation_indices()  # Derive the exact current hosted-worker plan.
        self.assertEqual(current_indices, list(range(len(ui_50000.GAME_IDS) + 3)))  # Require one index per game plus three extra Roulette replicas.
        with mock.patch.object(ui_50000, "GAME_IDS", ui_50000.GAME_IDS + ("fixture_catalog_growth",)):  # Model one future catalog addition without editing workflow YAML.
            expanded_indices = ui_50000.formal_allocation_indices()  # Recompute the plan through the production allocator.
        self.assertEqual(expanded_indices, list(range(len(current_indices) + 1)))  # Require the hosted matrix to add the new game's worker automatically.
        workflow = (ui_50000.ROOT / ".github" / "workflows" / "browser-tests.yml").read_text(encoding="utf-8")  # Read the inert exact-source workflow contract.
        planner_job = workflow.split("  formal_ui_plan:", 1)[1].split("  formal_ui_workers:", 1)[0]  # Isolate canonical planning from worker execution.
        worker_job = workflow.split("  formal_ui_workers:", 1)[1].split("  formal_ui_aggregate:", 1)[0]  # Isolate only the dynamic matrix consumer.
        aggregate_job = workflow.split("  formal_ui_aggregate:", 1)[1].split("  # Run issue #225", 1)[0]  # Isolate the fail-closed terminal aggregate.
        self.assertIn("python tests/ui_50000.py --print-formal-allocation-indices", planner_job)  # Bind planning to the public canonical helper.
        self.assertIn("allocation_index: ${{ fromJSON(needs.formal_ui_plan.outputs.allocation_indices) }}", worker_job)  # Consume the complete exact-source JSON matrix.
        self.assertNotIn("allocation_index:\n          - 0", worker_job)  # Reject a reintroduced enumerated prefix that can drift after catalog growth.
        self.assertIn("      - formal_ui_plan\n      - formal_ui_workers", aggregate_job)  # Require the aggregate to depend on both planning and every worker.

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
        self.assertIn(unknown_nav, focused_result["failed"])  # Refuse to exempt unregistered or malformed catalog identities.
        self.assertIn(baccarat_nav, focused_result["exercised"])  # Keep selected navigation on the literal floor.
        self.assertIn(deal, focused_result["exercised"])  # Keep selected game-owned actions fully governed.

    # Prove only replicated Roulette continues its deterministic target schedule across worker boundaries.
    def test_coverage_ordinal_continues_roulette_replicas_only(self):
        self.assertEqual(ui_50000.coverage_ordinal("roulette", 0, 417), 417)  # Continue Roulette after the prior replica's exact range.
        self.assertEqual(ui_50000.coverage_ordinal("blackjack", 0, 6667), 0)  # Preserve the local first-one-hundred budgets for ordinary games.

    # Prove Rebet closes a real activation deficit beyond the first hundred cycles without duplicating work across Roulette shards.
    def test_roulette_rebet_retries_only_primary_shard_until_floor(self):
        signature = ui_50000.qualify_control_signature("button#rebet", "roulette")  # Resolve the exact aggregate signature used by the formal report.
        under_floor = Counter({signature: 80})  # Reproduce the frozen aggregate's twenty-activation deficit.
        at_floor = Counter({signature: ui_50000.CONTROL_ACTIVATION_FLOOR})  # Model the completed literal acceptance floor.
        self.assertTrue(ui_50000.should_exercise_roulette_rebet(0, under_floor))  # Continue real rendered attempts on the first Roulette shard after cycle one hundred.
        self.assertFalse(ui_50000.should_exercise_roulette_rebet(1, under_floor))  # Prevent every later replica from restarting the same control budget.
        self.assertFalse(ui_50000.should_exercise_roulette_rebet(0, at_floor))  # Stop immediately after one hundred successful pointer activations.

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
