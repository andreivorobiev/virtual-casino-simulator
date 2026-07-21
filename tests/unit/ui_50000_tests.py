"""Focused TEST-092 proofs for the exact-source 50,000-cycle UI harness."""

import argparse  # Build narrow command namespaces without invoking the CLI parser.
import asyncio  # Exercise the browser-free aggregate controller end to end.
import json  # Persist synthetic shard reports for resume-policy tests.
import tempfile  # Own disposable report directories for every test.
import unittest  # Integrate the focused proofs with the repository API runner.
from collections import Counter  # Aggregate deterministic per-game allocation totals.
from pathlib import Path  # Address temporary shard reports with platform-neutral paths.
from unittest import mock  # Inject immutable provenance when release tests intentionally omit Git metadata.

from tests import ui_50000  # Exercise the public harness helpers without starting Playwright.


# Prove TEST-092 allocation, control classification, and exact-source resume invariants.
class UI50000HarnessTests(unittest.TestCase):
    # Prove rotating paint is required without treating its intentionally clipped square bounds as stable stage geometry.
    def test_big_six_stage_contract_separates_paint_from_containment(self):
        contract = ui_50000.ESSENTIAL_STAGE_CONTRACTS["big_six_wheel"]  # Read the public harness contract used by every formal viewport.
        self.assertEqual(contract["stage"], ".big-six-wheel__stage")  # Keep the route-owned stage as the containment boundary.
        self.assertIn(".big-six-wheel__wheel-shell", contract["contained_items"])  # Require the stable circular shell to remain fully inside the stage.
        self.assertNotIn(".big-six-wheel__wheel", contract["contained_items"])  # Avoid interpreting a rotated square bounding box as visible circular overflow.
        self.assertEqual(contract["paint_items"][".big-six-wheel__wheel"], ".big-six-wheel__wheel-shell")  # Require the wheel to paint across its clipping owner.

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

    # Prove only replicated Roulette continues its deterministic target schedule across worker boundaries.
    def test_coverage_ordinal_continues_roulette_replicas_only(self):
        self.assertEqual(ui_50000.coverage_ordinal("roulette", 0, 417), 417)  # Continue Roulette after the prior replica's exact range.
        self.assertEqual(ui_50000.coverage_ordinal("blackjack", 0, 6667), 0)  # Preserve the local first-one-hundred budgets for ordinary games.

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
                await ui_50000.acey_deucey_terminal_action(page, ordinal, Counter(), Counter())  # Exercise the production state ordering without Playwright.
            self.assertFalse(waits)  # Require the helper to consume every modeled public state boundary.
            return events  # Return the semantic order for precise assertions.

        decision_wait = 'wait:[data-action="play"]|[data-action="pass"]|[data-action="deal"]'  # Reuse the exact decision boundary in all scenarios.
        ready_wait = 'wait:[data-action="deal"]'  # Reuse the exact post-settlement boundary.
        play_events = asyncio.run(run_scenario("play"))  # Exercise the wager-consuming decision.
        self.assertEqual(play_events, ['click:[data-action="deal"]', decision_wait, "inventory", "fill:wager", "click:play", ready_wait])  # Require Deal before wager before Play.
        pass_events = asyncio.run(run_scenario("pass"))  # Exercise the token-free decision.
        self.assertEqual(pass_events, ['click:[data-action="deal"]', decision_wait, "inventory", "click:pass", ready_wait])  # Forbid an unnecessary wager edit on Pass.
        automatic_events = asyncio.run(run_scenario('[data-action="deal"]'))  # Exercise an automatically terminal boundary pair.
        self.assertEqual(automatic_events, ['click:[data-action="deal"]', decision_wait, "inventory"])  # Return safely without fabricating a wager or decision.

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
            self.write_distributed_corpus(shard_root, allocations, source_commit, evidence_root)  # Persist a complete passing 33-worker corpus.
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
