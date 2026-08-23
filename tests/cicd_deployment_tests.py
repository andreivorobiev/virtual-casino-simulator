# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free CI/CD workflow policy tests for TOOL-002/008/015 and TEST-036/133/180."""

# Import Python syntax inspection for listener-free browser ownership policy tests.
import ast
# Import modules from exact file paths for isolated generator hostile tests.
import importlib.util
# Import JSON encoding for synthetic fail-closed shard evidence.
import json
# Import path helpers so assertions read the checked-in workflow from any cwd.
from pathlib import Path
# Import regular expressions for deterministic literal browser case discovery.
import re
# Import subprocess execution for the listener-free aggregate CLI regression.
import subprocess
# Import the active Python executable for isolated aggregate verification.
import sys
# Import disposable directories for synthetic shard evidence.
import tempfile
# Import module objects for dependency-free explicit-live registration capture.
import types
# Import unittest for dependency-free workflow policy checks.
import unittest
# Import restoring patches for a synthetic PostgreSQL live module with no driver import.
from unittest import mock

# Resolve the repository root from this focused test file.
ROOT = Path(__file__).resolve().parents[1]
# Point at the protected-main production deployment workflow.
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-production.yml"
# Point at every ordinary workflow that may cancel only superseded runs for one pull request.
PR_QUALIFICATION_WORKFLOWS = (
    ROOT / ".github" / "workflows" / "browser-tests.yml",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / ".github" / "workflows" / "comment-density.yml",
    ROOT / ".github" / "workflows" / "contract-tests.yml",
    ROOT / ".github" / "workflows" / "docs.yml",
    ROOT / ".github" / "workflows" / "long-suite-100.yml",
    ROOT / ".github" / "workflows" / "module-boundaries.yml",
)
# Point at the sharded mandatory long-suite workflow.
LONG_SUITE_WORKFLOW = ROOT / ".github" / "workflows" / "long-suite-100.yml"
# Point at the manual 300/500 soak workflow that must never inherit PR cancellation.
LONG_SOAK_WORKFLOW = ROOT / ".github" / "workflows" / "long-suite-soak.yml"
# Point at the immutable publication workflow whose in-flight work must never be cancelled.
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
# Point at the long-suite runner so artifact and listener cleanup invariants can be inspected inertly.
LONG_SUITE_RUNNER = ROOT / "tests" / "long_suites.py"
# Point at the stable compatibility entrypoint retained by workflows and operators.
TEST_ENTRYPOINT = ROOT / "tests" / "run_tests.py"
# Point at the extracted runner implementation whose inline state must remain governed.
BROWSER_RUNNER = ROOT / "tests" / "runner.py"
# Point at the extracted pure Browser shard policy module. (TEST-242)
BROWSER_SHARDING = ROOT / "tests" / "browser_sharding.py"
# Point at the reviewed pre-slice count and sorted case-id inventory. (TEST-242)
BROWSER_CASE_INVENTORY = ROOT / "tests" / "browser_case_inventory.json"
# Point at every extracted API-area module owned by the compatibility runner. (TEST-242)
API_CASES_ROOT = ROOT / "tests" / "cases" / "api"
# Point at the reviewed non-Browser count and sorted case-id inventory. (TEST-242)
API_CASE_INVENTORY = ROOT / "tests" / "api_case_inventory.json"
# Point at the ordinary, formal, and sustained browser workflow.
BROWSER_WORKFLOW = ROOT / ".github" / "workflows" / "browser-tests.yml"
# Point at the scheduled and manually dispatchable Browser duration-profile workflow. (TOOL-017)
BROWSER_DURATION_WORKFLOW = ROOT / ".github" / "workflows" / "browser-duration-profile.yml"
# Point at the pull-request affected-game detector.
AFFECTED_BROWSER_GAMES = ROOT / "scripts" / "affected_browser_games.py"
# Declare the sole ordinary Browser shard-count oracle used by synthetic CI evidence. (TEST-242)
BROWSER_SHARD_COUNT = 6


# Validate the production deployment workflow without invoking GitHub or SSH.
class CicdDeploymentWorkflowTests(unittest.TestCase):
    # Read the workflow once per assertion to keep each test independent.
    def workflow_text(self) -> str:
        # Return the checked-in workflow text using the repository encoding.
        return WORKFLOW.read_text(encoding="utf-8")

    # Prove protected-main pushes are the only automatic deployment trigger.
    def test_workflow_triggers_on_main_push_only(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require the workflow to exist under the expected production name.
        self.assertIn("name: Production Deploy", text)
        # Require the automatic protected-main push trigger.
        self.assertIn("push:", text)
        # Require the exact main branch allowlist.
        self.assertIn("- main", text)
        # Reject a manual dispatch path that would bypass merge-to-main semantics.
        self.assertNotIn("workflow_dispatch:", text)
        # Reject pull-request deployment so drafts can never cut production over.
        self.assertNotIn("pull_request:", text)

    # Prove immutable package-version reuse fails instead of deploying stale assets.
    def test_workflow_refuses_tag_reuse_at_another_commit(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require tag identity to be resolved from canonical module metadata.
        self.assertIn("modules/module-manifest.json", text)
        # Require remote tag lookup before publication.
        self.assertIn('git ls-remote --tags origin "refs/tags/${RELEASE_TAG}"', text)
        # Require mismatched tag targets to fail clearly.
        self.assertIn("already points to another commit", text)
        # Require release candidates to be built with a predecessor manifest for rollback eligibility.
        self.assertIn('python scripts/make_release.py --release-tag "${RELEASE_TAG}" --previous-manifest previous/release-manifest.json', text)

    # Prove rollback selection follows repository compatibility policy instead of release ordering.
    def test_workflow_uses_compatibility_declared_predecessor(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require the current packaged version to enter the resolver.
        self.assertIn("APP_VERSION: ${{ steps.release_identity.outputs.app_version }}", text)
        # Require exact predecessor selection from the tracked compatibility record.
        self.assertIn('previous_tag="$(python scripts/resolve_release_predecessor.py --app-version "${APP_VERSION}")"', text)
        # Require the downloaded manifest to be verified against the same declaration.
        self.assertIn('--verify-manifest previous/release-manifest.json', text)
        # Reject the defective latest-other-release heuristic that produced v0.9.5.6 provenance.
        self.assertNotIn('releases?per_page=100', text)
        # Reject any release-list API ordering as a rollback policy input.
        self.assertNotIn('gh api "repos/${GITHUB_REPOSITORY}/releases', text)

    # Prove publication verifies hosted Release assets rather than trusting local build outputs.
    def test_workflow_verifies_hosted_release_assets(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require post-publication download of the three canonical assets.
        self.assertIn('gh release download "${RELEASE_TAG}" --pattern virtual_casino_simulator_package.zip --pattern release-manifest.json --pattern checksums.txt --dir published --clobber', text)
        # Require hosted assets to be verified against exact commit, tag, and rollback provenance.
        self.assertIn('python scripts/package_app.py --verify-only --archive published/virtual_casino_simulator_package.zip --manifest published/release-manifest.json --expected-commit "${GITHUB_SHA}" --expected-tag "${RELEASE_TAG}" --require-rollback', text)
        # Preserve the existing bounded Actions artifact as publication evidence.
        self.assertIn("name: production-release-assets", text)
        # Reject any consumer job because the host downloads the immutable public Release directly.
        self.assertNotIn("uses: actions/download-artifact", text)
        # Reject deployment from either the runner's local dist directory or its hosted download directory.
        self.assertNotIn("scp -P", text)

    # Prove the workflow publishes only and cannot contact or mutate production.
    def test_workflow_retires_the_dead_ssh_deployment_leg(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require one publication job and no second production deployment job.
        self.assertIn("publish-release:", text)
        # Reject the dead ordinary deployment job entirely.
        self.assertNotIn("deploy-production:", text)
        # Reject every runner-to-host transport and credential seam.
        for forbidden in ("CASINO_DEPLOY_SSH_HOST", "CASINO_DEPLOY_SSH_PORT", "CASINO_DEPLOY_SSH_USER", "CASINO_DEPLOY_SSH_KEY", "CASINO_DEPLOY_KNOWN_HOSTS", "ssh -p", "scp -P", "known_hosts"):
            # Require the retired boundary to stay absent.
            self.assertNotIn(forbidden, text)
        # Preserve the release publication name used by protected-main accounting.
        self.assertIn("name: Publish exact-main release", text)


# Validate ordinary qualification acceleration without starting a browser, listener, or workflow.
class CiQualificationWorkflowTests(unittest.TestCase):
    # Read one tracked workflow using the repository encoding.
    def workflow_text(self, path: Path) -> str:
        # Return inert workflow source for exact policy assertions.
        return path.read_text(encoding="utf-8")

    # Prove cancellation is scoped to one workflow and one pull request only.
    def test_concurrency_cancels_only_superseded_runs_for_the_same_pr(self):
        # Preserve the exact expression whose fallback makes non-PR runs unique.
        expected_group = "group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.run_id }}"
        # Inspect every ordinary workflow changed by the acceleration slice.
        for workflow in PR_QUALIFICATION_WORKFLOWS:
            # Read the workflow as data without invoking GitHub Actions.
            text = self.workflow_text(workflow)
            # Require the workflow name plus PR-number group with a unique run fallback.
            self.assertIn(expected_group, text, workflow.name)
            # Permit cancellation only inside that exact event-scoped group.
            self.assertIn("cancel-in-progress: true", text, workflow.name)
        # Read Browser Tests separately because it also owns governed manual qualifications.
        browser_text = self.workflow_text(PR_QUALIFICATION_WORKFLOWS[0])
        # Require manual dispatch to remain available for formal and Baccarat evidence.
        self.assertIn("workflow_dispatch:", browser_text)
        # Require the formal 50,000-cycle input to remain governed by the unique-run fallback.
        self.assertIn("formal_ui_50000:", browser_text)
        # Require the Baccarat sustained input to remain governed by the unique-run fallback.
        self.assertIn("baccarat_sustained_2000:", browser_text)
        # Require Browser Tests to execute when its own workflow policy changes.
        self.assertIn("- '.github/workflows/browser-tests.yml'", browser_text)
        # Read protected publication and deployment workflows independently.
        release_text = self.workflow_text(RELEASE_WORKFLOW)
        # Keep release candidates and recovery dispatches non-cancellable.
        self.assertIn("cancel-in-progress: false", release_text)
        # Reject inheritance of the pull-request cancellation expression.
        self.assertNotIn(expected_group, release_text)
        # Read the protected-main deployment workflow independently.
        deploy_text = self.workflow_text(WORKFLOW)
        # Keep production cutover work non-cancellable.
        self.assertIn("cancel-in-progress: false", deploy_text)
        # Reject inheritance of the pull-request cancellation expression.
        self.assertNotIn(expected_group, deploy_text)
        # Read the manually selected 300/500 soak workflow independently.
        soak_text = self.workflow_text(LONG_SOAK_WORKFLOW)
        # Keep the formal soak workflow manual.
        self.assertIn("workflow_dispatch:", soak_text)
        # Reject PR-scoped cancellation for manually authorized soak evidence.
        self.assertNotIn("cancel-in-progress: true", soak_text)

    # Prove four deterministic workers exhaust Suite 100 without duplicate scenarios.
    def test_long_suite_shards_are_exhaustive_and_nonduplicating(self):
        # Import the runner only after inert workflow checks have been defined.
        from tests import long_suites
        # Compute the exact scenario ownership of every governed shard.
        shard_sets = [set(long_suites.shard_indices(100, 4, index)) for index in range(4)]
        # Require the balanced 25-scenario allocation expected for 100 modulo four.
        self.assertEqual([len(shard) for shard in shard_sets], [25, 25, 25, 25])
        # Require the union to cover every logical scenario exactly.
        self.assertEqual(set().union(*shard_sets), set(range(100)))
        # Compare every distinct pair so no scenario can execute twice.
        for left_index in range(4):
            # Compare only later shards to avoid redundant pairs.
            for right_index in range(left_index + 1, 4):
                # Require disjoint ownership for the selected shard pair.
                self.assertTrue(shard_sets[left_index].isdisjoint(shard_sets[right_index]))

    # Prove shard audio ownership, artifacts, cleanup, and the required aggregate fail closed.
    def test_long_suite_workflow_preserves_audio_artifacts_cleanup_and_gate(self):
        # Read the mandatory workflow as inert text.
        workflow_text = self.workflow_text(LONG_SUITE_WORKFLOW)
        # Require exactly four shard identities.
        self.assertIn("shard: [0, 1, 2, 3]", workflow_text)
        # Preserve every shard result even when another shard fails.
        self.assertIn("fail-fast: false", workflow_text)
        # Isolate the shell branch that owns the audio policy.
        shard_script = workflow_text.split("run: |", 1)[1].split("- name: Upload long-suite shard artifacts", 1)[0]
        # Separate shard zero from the deliberate non-audio shards.
        audio_branch, non_audio_branch = shard_script.split("else", 1)
        # Require shard zero to retain LONG-AUDIO-001 execution.
        self.assertNotIn("--skip-browser-audio", audio_branch)
        # Require only the remaining branch to skip the duplicated audio probe.
        self.assertIn("--skip-browser-audio", non_audio_branch)
        # Require isolated disposable deployments for all parallel workers.
        self.assertEqual(shard_script.count("--copy-deployment"), 2)
        # Require a unique artifact identity for each matrix worker.
        self.assertIn("name: long-suite-100-shard-${{ matrix.shard }}-artifacts", workflow_text)
        # Invoke the Slots proof as a package module so repository imports resolve on hosted Linux.
        self.assertIn("run: python -m tests.slots_economics_long", workflow_text)
        # Reject direct-file execution because it omits the repository root from Python's import path.
        self.assertNotIn("run: python tests/slots_economics_long.py", workflow_text)
        # Invoke the exact Keno proof as a package module so repository imports resolve on hosted Linux.
        self.assertIn("run: python -m tests.keno_economics_long", workflow_text)
        # Run the governed Keno module exactly once rather than multiplying proof across shards.
        self.assertEqual(workflow_text.count("python -m tests.keno_economics_long"), 1)
        # Keep both exact proof and artifact-identity steps on the single shard-one owner.
        keno_steps = workflow_text.split("- name: Prove Keno exact economics", 1)[1].split("- name: Prove complete game economics registry", 1)[0]
        # Require both governed steps to declare shard one explicitly.
        self.assertEqual(keno_steps.count("if: matrix.shard == 1"), 2)
        # Require fail-closed semantic verification of the exact evidence identity before upload.
        self.assertIn("python scripts/verify_keno_economics_artifact.py logs/test-runs/keno-economics-exact.json", keno_steps)
        # Isolate the complete catalog proof so its shard and artifact contract cannot weaken the Keno checks.
        economics_step = workflow_text.split("- name: Prove complete game economics registry", 1)[1].split("- name: Upload long-suite shard artifacts", 1)[0]
        # Run the complete registry once on the shard that already owns its deep Slots and Keno prerequisites.
        self.assertEqual(economics_step.count("if: matrix.shard == 1"), 1)
        # Require the executable registry to write the aggregate artifact uploaded by the workflow.
        self.assertIn("python -m tests.game_economics_registry_tests --execute --artifact logs/test-runs/game-economics-registry.json", economics_step)
        # Reject direct-file Keno execution for the same import-path reason.
        self.assertNotIn("run: python tests/keno_economics_long.py", workflow_text)
        # Upload terminal evidence even when one shard command fails.
        self.assertIn("if: always()", workflow_text)
        # Require the exact branch-protection aggregate job identifier once.
        self.assertEqual(workflow_text.splitlines().count("  long_suite_100:"), 1)
        # Require the aggregate to depend on both the scope decision and complete matrix result.
        self.assertIn("- long_suite_scope", workflow_text)
        self.assertIn("- long_suite_100_shard", workflow_text)
        # Ensure the aggregate accepts only a successful matrix or an explicitly verified skipped matrix.
        self.assertIn('test "${{ needs.long_suite_100_shard.result }}" = "success"', workflow_text)
        self.assertIn('test "${{ needs.long_suite_100_shard.result }}" = "skipped"', workflow_text)
        # Read runner cleanup behavior without opening its loopback server.
        runner_text = self.workflow_text(LONG_SUITE_RUNNER)
        # Preserve JSON evidence outside disposable copies before their removal.
        self.assertIn("report_root = ROOT if args.copy_deployment else repo_root", runner_text)
        # Require tracked listener cleanup before the report is finalized.
        cleanup_index = runner_text.index("listener_cleanup = progress.cleanup()")
        # Locate the terminal report write that captures closure evidence.
        report_index = runner_text.index("report_path.write_text")
        # Locate disposable deployment cleanup after artifact preservation.
        deployment_cleanup_index = runner_text.index("shutil.rmtree(cleanup_target")
        # Prove listener cleanup is captured before the report write.
        self.assertLess(cleanup_index, report_index)
        # Prove the preserved report is written before the copied tree is removed.
        self.assertLess(report_index, deployment_cleanup_index)

    # Read and parse the browser runner without importing Playwright or opening a listener.
    def browser_runner_syntax(self):
        # Read exact checked-in source once for syntax and literal policy assertions.
        source = self.workflow_text(BROWSER_RUNNER)
        # Parse the source as data so ownership checks cannot execute browser code.
        return source, ast.parse(source)

    # Prove the historical command path is now a narrow compatibility shim. (TEST-242)
    def test_run_tests_entrypoint_is_thin_compatibility_shim(self):
        # Read the public entrypoint without importing the extracted runner.
        source = self.workflow_text(TEST_ENTRYPOINT)
        # Parse the shim as inert syntax so this structural check opens no listener or Browser.
        tree = ast.parse(source)
        # Enforce the parent issue's final under-three-hundred-line ceiling.
        self.assertLess(len(source.splitlines()), 300)
        # Reject function or class implementations that would rebuild a second runner monolith.
        self.assertFalse(any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in tree.body))
        # Locate the single explicit compatibility import from the implementation owner.
        runner_imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == "tests.runner"]
        # Require exactly one reviewed export boundary rather than scattered implementation imports.
        self.assertEqual(len(runner_imports), 1)
        # Bind every compatibility helper used by focused callers plus the one CLI delegate.
        self.assertEqual(
            {alias.name for alias in runner_imports[0].names},
            {"DEFAULT_AUTH_EMAIL", "DEFAULT_AUTH_PASSWORD", "api", "login_default_user", "main", "roulette_i18n_failure_diagnostic", "start_server", "stop_server"},
        )
        # Require exactly one process-status delegation through the extracted main function.
        self.assertEqual(source.count("raise SystemExit(main())"), 1)
        # Reject case registrations and every lifecycle implementation from the compatibility surface.
        for forbidden in ("run_case(", "def start_server", "def stop_server", "def run_api_tests", "def run_browser_tests", "sync_playwright", "subprocess.Popen"):
            # Name the first regressed responsibility without executing it.
            self.assertNotIn(forbidden, source)
        # Require the moved implementation to retain the unchanged CLI dispatcher and suite owners.
        implementation = self.workflow_text(BROWSER_RUNNER)
        # Keep the one accepted main dispatcher in the implementation owner.
        self.assertIn("def main():", implementation)
        # Keep both API and Browser lifecycle functions out of the public shim.
        self.assertIn("def run_api_tests():", implementation)
        # Keep the Browser owner in the implementation module beside shared lifecycle state.
        self.assertIn("def run_browser_tests(", implementation)

    # Read and parse the extracted shard policy without importing the compatibility runner.
    def browser_sharding_syntax(self):
        # Read exact checked-in shard-policy source once for literal ownership assertions.
        source = self.workflow_text(BROWSER_SHARDING)
        # Parse the source as data so focused CI tests never execute Browser code.
        return source, ast.parse(source)

    # Prove every #727 slice preserves the exact pre-slice count and sorted Browser identity list.
    def test_browser_case_inventory_matches_runner_exactly(self):
        # Parse the compatibility runner without importing Playwright or opening a listener.
        source, _tree = self.browser_runner_syntax()
        # Import the listener-free discovery seam from the extracted implementation without starting Playwright or a listener.
        from tests import runner as browser_runner_module
        # Expand inline and reviewed area-owned registrations in exact source order.
        case_ids = browser_runner_module.browser_case_ids()
        # Load the checked-in count and sorted-ID baseline as inert JSON.
        inventory = json.loads(BROWSER_CASE_INVENTORY.read_text(encoding="utf-8"))
        # Require the baseline to expose only the two acceptance dimensions.
        self.assertEqual(set(inventory), {"count", "case_ids"})
        # Prove exact before/after case-count equality for this extraction slice. (TEST-242)
        self.assertEqual(inventory["count"], len(case_ids))
        # Prove exact before/after sorted identity equality, not merely set inclusion. (TEST-242)
        self.assertEqual(inventory["case_ids"], sorted(case_ids))
        # Require the compatibility runner to invoke the strict baseline before returning discovery.
        self.assertIn("validate_browser_case_inventory(case_ids,BROWSER_CASE_INVENTORY_PATH)", source)

    # Prove missing, added, duplicated, or malformed baseline evidence fails closed.
    def test_browser_case_inventory_validator_rejects_drift(self):
        # Import only the listener-free pure policy module.
        from tests import browser_sharding
        # Use a tiny synthetic current inventory so every mismatch is easy to isolate.
        current = ["BR-A-001", "BR-B-001"]
        # Create one disposable baseline path without changing tracked governance data.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Resolve the exact task-local baseline path.
            inventory_path = Path(temp_dir) / "browser_case_inventory.json"
            # Define hostile packets covering count drift, sorted-ID drift, duplication, and shape drift.
            hostile_packets = (
                {"count": 1, "case_ids": ["BR-A-001", "BR-B-001"]},
                {"count": 2, "case_ids": ["BR-A-001", "BR-C-001"]},
                {"count": 2, "case_ids": ["BR-A-001", "BR-A-001"]},
                {"count": 2, "case_ids": ["BR-A-001", "BR-B-001"], "optional": True},
            )
            # Exercise each hostile packet independently through the production validator.
            for packet in hostile_packets:
                # Persist only this bounded synthetic packet.
                inventory_path.write_text(json.dumps(packet), encoding="utf-8")
                # Require the one fixed value-free mismatch diagnostic.
                with self.assertRaisesRegex(AssertionError, "^browser case inventory does not match the reviewed baseline$"):
                    # Validate exact current source identities against hostile evidence.
                    browser_sharding.validate_browser_case_inventory(current, inventory_path)
            # Persist one exact packet to prove the strict validator accepts the intended path.
            inventory_path.write_text(json.dumps({"count": 2, "case_ids": current}), encoding="utf-8")
            # Preserve source order on successful validation.
            self.assertEqual(browser_sharding.validate_browser_case_inventory(current, inventory_path), current)

    # Prove Craps Browser evidence waits on durable committed progress rather than a transient animation.
    def test_craps_browser_roll_wait_is_durable(self):
        # Parse the compatibility runner without importing Playwright or opening a listener.
        source, tree = self.browser_runner_syntax()
        # Select the Browser owner so assertions remain bounded to executable acceptance code.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Select the nested Craps acceptance function from the reviewed Browser owner.
        craps_case = next(node for node in ast.walk(runner) if isinstance(node, ast.FunctionDef) and node.name == "craps_acceptance")
        # Read only the exact Craps acceptance source for durable-wait assertions.
        craps_source = ast.get_source_segment(source, craps_case)
        # Reject the flaky requirement to observe the short-lived decorative CSS class.
        self.assertNotIn("locator('.craps-die.is-rolling').first.wait_for", craps_source)
        # Require both come-out and point-play loops to use the shared durable completion helper.
        self.assertEqual(len(re.findall(r"(?m)^\s+roll_and_wait_for_commit\(\)$", craps_source)), 2)
        # Bind completion to a strictly advanced committed roll count after the public click.
        self.assertIn("prior => Number(document.querySelectorAll('.craps-metrics .craps-metric strong')[3]?.textContent.replace(/[^0-9.-]/g, '')) > prior", craps_source)
        # Preserve the post-commit wait for decorative presentation to settle before state inspection.
        self.assertIn("() => !document.querySelector('.craps-die.is-rolling')", craps_source)

    # Prove every #727 API slice preserves the exact reviewed non-Browser count and sorted identities.
    def test_api_case_inventory_matches_extracted_sources_exactly(self):
        # Import only the source-reading inventory helper with no runner or case execution.
        from tests import api_case_inventory
        # Resolve the compatibility entrypoint plus every extracted API-area source deterministically.
        source_paths = api_case_inventory.api_case_source_paths(BROWSER_RUNNER, API_CASES_ROOT)
        # Discover literal non-Browser registrations without importing the runner or opening a listener.
        case_ids = api_case_inventory.discover_api_case_ids(source_paths)
        # Load the checked-in count and sorted-ID baseline as inert JSON.
        inventory = json.loads(API_CASE_INVENTORY.read_text(encoding="utf-8"))
        # Require the baseline to expose only the two acceptance dimensions.
        self.assertEqual(set(inventory), {"count", "case_ids"})
        # Prove exact before/after case-count equality for the current extraction slice. (TEST-242)
        self.assertEqual(inventory["count"], len(case_ids))
        # Prove exact before/after sorted identity equality, including every storage and API-lane gate.
        self.assertEqual(inventory["case_ids"], list(case_ids))
        # Require the compatibility runner to invoke strict source validation before API execution.
        self.assertIn("validate_api_case_inventory(current_api_case_ids,API_CASE_INVENTORY_PATH)", BROWSER_RUNNER.read_text(encoding="utf-8"))

    # Prove missing, added, duplicated, unsorted, or malformed API baseline evidence fails closed.
    def test_api_case_inventory_validator_rejects_drift(self):
        # Import only the source-neutral exact inventory validator.
        from tests import api_case_inventory
        # Use a tiny synthetic sorted current inventory so every mismatch is easy to isolate.
        current = ("API-A-001", "GOV-B-001")
        # Create one disposable baseline path without changing tracked governance data.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Resolve the exact task-local baseline path.
            inventory_path = Path(temp_dir) / "api_case_inventory.json"
            # Define hostile packets covering count, ID, duplicate, ordering, type, and shape drift.
            hostile_packets = (
                {"count": 1, "case_ids": ["API-A-001", "GOV-B-001"]},
                {"count": 2, "case_ids": ["API-A-001", "GOV-C-001"]},
                {"count": 2, "case_ids": ["API-A-001", "API-A-001"]},
                {"count": 2, "case_ids": ["GOV-B-001", "API-A-001"]},
                {"count": True, "case_ids": ["API-A-001", "GOV-B-001"]},
                {"count": 2, "case_ids": ["API-A-001", "GOV-B-001"], "optional": True},
            )
            # Exercise each hostile packet independently through the production validator.
            for packet in hostile_packets:
                # Persist only this bounded synthetic packet.
                inventory_path.write_text(json.dumps(packet), encoding="utf-8")
                # Require the one fixed value-free mismatch diagnostic.
                with self.assertRaisesRegex(AssertionError, "^API case inventory does not match the reviewed baseline$"):
                    # Validate exact current source identities against hostile evidence.
                    api_case_inventory.validate_api_case_inventory(current, inventory_path)
            # Persist one exact packet to prove the strict validator accepts the intended path.
            inventory_path.write_text(json.dumps({"count": 2, "case_ids": list(current)}), encoding="utf-8")
            # Preserve sorted immutable identities on successful validation.
            self.assertEqual(api_case_inventory.validate_api_case_inventory(current, inventory_path), current)

    # Prove harness-foundation registrations moved as one exact listener-free area.
    def test_api_harness_foundation_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("REQUEST-LATENCY-UNIT-001", ["TEST-148"]),
            ("BROWSER-138-HARNESS-001", ["AUTH-001", "AUTH-002", "SESSION-001", "SESSION-005", "TEST-039", "TEST-042", "TEST-142", "CORE-021"]),
            ("UI-50000-HARNESS-001", ["TEST-042", "TEST-047", "TEST-092"]),
            ("MONEY-NONFINITE-UNIT-001", ["CORE-025", "LEDGER-027", "MHVP-006", "TEST-055"]),
            ("API-GUEST-TEARDOWN-LEDGER-001", ["LEDGER-035", "AUTH-020", "LEDGER-037", "TEST-188", "TEST-194"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "harness_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be inspected without execution.
        spec = importlib.util.spec_from_file_location("harness_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registration identity without running any focused suite.
        captured = []
        def capture(case_id, requirements, callback):
            # Preserve all ownership dimensions for one fail-closed equality proof.
            captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture)
        # Bind permanent IDs, requirement mappings, order, and focused callback ownership.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "_run_request_latency_unit_tests", "_run_concurrent_browser_138_harness_tests",
            "_run_ui_50000_harness_tests", "_run_nonfinite_money_unit_tests",
            "_run_guest_teardown_ledger_tests",
        ))
        # Reject duplicate registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation after inventory validation and before runner process helpers.
        delegation = "api_harness_foundation.run_cases(run_case)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("validate_api_case_inventory(current_api_case_ids,API_CASE_INVENTORY_PATH)"), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("def run_unit_module"))
        # Keep process, listener, and server lifecycle out of the extracted owner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)
        self.assertNotIn("start_server", area_source)

    # Prove live infrastructure cases moved without transferring listener or reset ownership.
    def test_api_live_infrastructure_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("API-MONEY-NONFINITE-001", ["CORE-025", "LEDGER-027", "MHVP-006", "TEST-055"]),
            ("API-OPS-001", ["OPS-001", "OPS-002", "OPS-003", "OPS-004", "OPS-005", "MYSQL-011", "TEST-044"]),
            ("API-OAUTH-001", ["OAUTH-001", "OAUTH-002", "OAUTH-006", "OAUTH-007", "AUTH-007", "TEST-045", "TEST-093"]),
            ("API-OAUTH-002", ["OAUTH-007", "OAUTH-008", "OAUTH-009", "OAUTH-010", "OAUTH-012", "OAUTH-013", "AUTH-007", "AUTH-017", "TEST-093", "TEST-167", "TEST-168"]),
            ("API-MAIL-002", ["MAIL-001", "MAIL-002", "MAIL-003", "TEST-090"]),
            ("API-INVITE-002", ["INVITE-001", "INVITE-002", "INVITE-003", "INVITE-004", "TEST-091"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "live_infrastructure.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the area owner so its registrations can be inspected without a server.
        spec = importlib.util.spec_from_file_location("live_infrastructure_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture registration identity while leaving every live callback unexecuted.
        captured = []
        def capture(case_id, requirements, callback):
            # Preserve permanent ID, mapping, order, and callback ownership dimensions.
            captured.append((case_id, requirements, callback.__name__))
        # Register the one pre-reset case with inert dependency sentinels.
        module.run_money_boundary_case(capture, object(), object(), object(), object())
        # Register the five post-reset cases with inert dependency sentinels.
        module.run_service_cases(capture, object(), object(), object())
        # Bind exact reviewed IDs, requirement mappings, and historical order.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Bind the six moved callback bodies to the new owner.
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "nonfinite_money_api", "operations_api", "oauth_api",
            "oauth_runtime_api", "mail_api", "invitation_api",
        ))
        # Reject duplicate literal registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require the exact two delegations around the runner-owned reset and login boundary.
        money_delegation = "api_live_infrastructure.run_money_boundary_case(run_case,base,api,raw_api,ROOT)"
        service_delegation = "api_live_infrastructure.run_service_cases(run_case,base,api,ROOT)"
        reset_call = "api(base,'/api/v1/casino/reset','POST',{})"
        login_call = "login_default_user(base)"
        self.assertEqual(runner_source.count(money_delegation), 1)
        self.assertEqual(runner_source.count(service_delegation), 1)
        self.assertLess(runner_source.index("api_admin_guest.run_cases(run_case,base,validate_guest_admin_api)"), runner_source.index(money_delegation))
        self.assertLess(runner_source.index(money_delegation), runner_source.index(reset_call, runner_source.index(money_delegation)))
        self.assertLess(runner_source.index(reset_call, runner_source.index(money_delegation)), runner_source.index(login_call, runner_source.index(reset_call, runner_source.index(money_delegation))))
        self.assertLess(runner_source.index(login_call, runner_source.index(reset_call, runner_source.index(money_delegation))), runner_source.index(service_delegation))
        self.assertLess(runner_source.index(service_delegation), runner_source.index("def auth_backend"))
        # Keep listener, process, reset, and login lifecycle out of the extracted owner.
        self.assertNotIn("start_server", area_source)
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("/api/v1/casino/reset", area_source)
        self.assertNotIn("login_default_user", area_source)

    # Prove storage and MySQL registrations moved without weakening explicit live selectors.
    def test_api_storage_foundation_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("MYSQL-MIGRATION-001", ["MYSQL-005", "MYSQL-007", "MYSQL-008", "MYSQL-009", "STORAGE-007", "TEST-048", "TEST-174"]),
            ("STORAGE-SESSIONS-001", ["SESSION-014", "STORAGE-019", "MYSQL-010", "TEST-250"]),
            ("RECOVERY-POLICY-001", ["MYSQL-006", "MYSQL-008", "MYSQL-009", "TOOL-004", "TEST-049", "TEST-174"]),
            ("POSTGRES-CONFIG-001", ["STORAGE-001", "STORAGE-003", "STORAGE-004", "STORAGE-020", "TEST-252"]),
            ("POSTGRES-POOL-001", ["STORAGE-010", "STORAGE-021", "TEST-253"]),
            ("POSTGRES-MIGRATION-001", ["STORAGE-022", "TEST-254"]),
            ("POSTGRES-STORAGE-001", ["STORAGE-023", "TEST-255"]),
            ("POSTGRES-GAME-ACTION-001", ["STORAGE-024", "TEST-256"]),
            ("STORAGE-JSON-001", ["CORE-017", "LEDGER-001", "LEDGER-007", "AUDIO-010", "STORAGE-016", "TEST-030", "TEST-243"]),
            ("STORAGE-PROVIDER-SETTLEMENT-PARITY-001", ["CORE-031", "STORAGE-013", "STORAGE-016", "TEST-243"]),
            ("STORAGE-WALLET-CORRUPTION-001", ["STORAGE-014", "TEST-177"]),
            ("STORAGE-WALLET-CENTS-001", ["STORAGE-015", "LEDGER-036", "TOOL-019", "TEST-190"]),
            ("STORAGE-JSON-IDEMPOTENCY-001", ["LEDGER-026", "LEDGER-033", "LEDGER-034", "STORAGE-005", "STORAGE-006", "TEST-043", "TEST-164", "TEST-169"]),
            ("STORAGE-GAME-ACTION-ONCE-001", ["STORAGE-011"]),
            ("STORAGE-GAME-ACTION-LIFECYCLE-001", ["CORE-031", "STORAGE-013", "TEST-174"]),
            ("MYSQL-GAME-ACTION-LIFECYCLE-001", ["MYSQL-009", "STORAGE-013", "TEST-174"]),
            ("STORAGE-PLAYER-STATE-ATOMIC-001", ["CORE-030", "STORAGE-001", "STORAGE-002", "STORAGE-018", "TEST-247"]),
            ("STORAGE-PRACTICE-OPPONENT-001", ["BOT-009", "BOT-010", "BOT-011", "ADMIN-023", "LEDGER-026", "STORAGE-005", "STORAGE-006"]),
            ("API-ENROLLMENT-POLICY-001", ["AUTH-013", "AUTH-014", "AUTH-015", "OAUTH-011", "TEST-158"]),
            ("STORAGE-LEDGER-GUARD-001", ["STORAGE-008", "STORAGE-012", "LEDGER-001", "CORE-017", "TEST-162"]),
            ("API-GAME-RULES-001", ["SEC-002", "SEC-004", "SEC-014", "TEST-163"]),
            ("STORAGE-TABLE-RULES-001", ["LEDGER-029", "TOKEN-006"]),
            ("STORAGE-MYSQL-001", ["CORE-017", "LEDGER-001", "LEDGER-007", "LEDGER-009", "LEDGER-033", "TEST-164"]),
            ("MYSQL-POOL-001", ["STORAGE-010", "MYSQL-011", "TEST-141", "TEST-220"]),
            ("STORAGE-MYSQL-LIVE-001", ["STORAGE-001", "STORAGE-002", "STORAGE-003", "STORAGE-004", "STORAGE-005", "STORAGE-006", "STORAGE-010", "MYSQL-001", "MYSQL-002", "MYSQL-003", "MYSQL-004", "OTT-001", "OTT-002", "MAIL-002", "MAIL-004", "INVITE-003", "TEST-038", "TEST-043", "TEST-089", "TEST-090", "TEST-091", "TEST-141", "TEST-171", "TEST-220"]),
            ("MYSQL-MIGRATION-LIVE-001", ["MYSQL-005", "MYSQL-007", "MYSQL-008", "MYSQL-009", "STORAGE-007", "STORAGE-010", "STORAGE-018", "GAMECORE-009", "OTT-001", "OTT-002", "MAIL-002", "MAIL-004", "TEST-048", "TEST-089", "TEST-090", "TEST-141", "TEST-174", "TEST-220", "TEST-246", "TEST-247", "TEST-251"]),
            ("POSTGRES-MIGRATION-LIVE-001", ["STORAGE-022", "TEST-254"]),
            ("POSTGRES-STORAGE-LIVE-001", ["STORAGE-023", "TEST-255"]),
            ("POSTGRES-GAME-ACTION-LIVE-001", ["STORAGE-024", "TEST-256"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "storage_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be captured without execution.
        spec = importlib.util.spec_from_file_location("storage_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture the default selection without running any provider or focused suite.
        default_captured = []
        def capture_default(case_id, requirements, callback):
            # Preserve permanent ID, mapping, order, and callback identity.
            default_captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture_default)
        # Require both live registrations to remain absent without explicit selectors.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in default_captured), expected_cases[:24])
        # Capture the explicitly selected live registrations without invoking their callbacks.
        live_captured = []
        def capture_live(case_id, requirements, callback):
            # Preserve the complete explicit-live registration packet.
            live_captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture_live, include_live=True, include_migration_live=True, request_latency_callback=object())
        # Bind all twenty-five default and MySQL-live IDs, mappings, and historical order.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in live_captured), expected_cases[:26])
        # Bind the two explicit selector cases to the final two historical positions.
        self.assertEqual(tuple(case_id for case_id, _, _ in live_captured[-2:]), ("STORAGE-MYSQL-LIVE-001", "MYSQL-MIGRATION-LIVE-001"))
        # Capture the PostgreSQL live registration independently from both MySQL selectors.
        postgres_live_captured = []
        def capture_postgres_live(case_id, requirements, callback):
            # Preserve the default inventory plus the disposable PostgreSQL callback identity.
            postgres_live_captured.append((case_id, requirements, callback.__name__))
        # Create a driver-free module so this governance test cannot require psycopg or a listener.
        postgres_live_module = types.ModuleType("tests.postgres_migration_live")
        def main():
            # Refuse execution if registration capture ever starts the disposable live lifecycle.
            raise AssertionError("PostgreSQL live callback must not execute during registration capture")
        # Publish the exact named callback consumed by the storage registration owner.
        postgres_live_module.main = main
        # Replace only the service-dependent import for the duration of inert registration capture.
        with mock.patch.dict(sys.modules, {"tests.postgres_migration_live": postgres_live_module}):
            # Select only the PostgreSQL live path while keeping both MySQL selectors false.
            module.run_cases(capture_postgres_live, include_postgres_migration_live=True)
        # Require the separate selector to append only the exact PostgreSQL live registration.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in postgres_live_captured), expected_cases[:24] + expected_cases[26:27])
        # Bind the imported live entrypoint without executing the disposable service lifecycle.
        self.assertEqual(postgres_live_captured[-1], ("POSTGRES-MIGRATION-LIVE-001", ["STORAGE-022", "TEST-254"], "main"))
        # Capture the complete-provider live registration separately from migration authority.
        postgres_storage_live_captured = []
        def capture_postgres_storage_live(case_id, requirements, callback):
            # Preserve the default inventory plus the complete-provider callback identity.
            postgres_storage_live_captured.append((case_id, requirements, callback.__name__))
        # Create a second driver-free module so provider-live capture cannot open a target.
        postgres_storage_live_module = types.ModuleType("tests.postgres_provider_live")
        # Reuse the never-executed named callback because only registration identity is governed.
        postgres_storage_live_module.main = main
        # Replace only the service-dependent provider-live import during inert capture.
        with mock.patch.dict(sys.modules, {"tests.postgres_provider_live": postgres_storage_live_module}):
            # Select only complete-provider live evidence, not migration or MySQL lifecycles.
            module.run_cases(capture_postgres_storage_live, include_postgres_storage_live=True)
        # Require the new selector to append only the exact complete-provider live case.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in postgres_storage_live_captured), expected_cases[:24] + expected_cases[27:28])
        # Bind the provider-live entrypoint without executing any connector or listener lifecycle.
        self.assertEqual(postgres_storage_live_captured[-1], ("POSTGRES-STORAGE-LIVE-001", ["STORAGE-023", "TEST-255"], "run_postgres_storage_live_tests"))
        # Capture game-action live registration independently from all other live selectors.
        postgres_game_action_live_captured = []
        def capture_postgres_game_action_live(case_id, requirements, callback):
            # Preserve the default inventory plus the game-action callback identity.
            postgres_game_action_live_captured.append((case_id, requirements, callback.__name__))
        # Create a driver-free module so registration capture cannot open PostgreSQL.
        postgres_game_action_live_module = types.ModuleType("tests.postgres_game_action_live")
        # Reuse the never-executed named callback because only registration identity is governed.
        postgres_game_action_live_module.main = main
        # Replace only the service-dependent game-action live import during capture.
        with mock.patch.dict(sys.modules, {"tests.postgres_game_action_live": postgres_game_action_live_module}):
            # Select only exact PostgreSQL game-action live evidence.
            module.run_cases(capture_postgres_game_action_live, include_postgres_game_action_live=True)
        # Require one explicit live append after the complete default inventory.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in postgres_game_action_live_captured), expected_cases[:24] + expected_cases[28:])
        # Bind the imported game-action entrypoint without executing a listener lifecycle.
        self.assertEqual(postgres_game_action_live_captured[-1], ("POSTGRES-GAME-ACTION-LIVE-001", ["STORAGE-024", "TEST-256"], "main"))
        # Reject duplicate literal registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one exact delegation that forwards both selectors and the callback.
        delegation = "api_storage_foundation.run_cases(run_case,include_live=args.mysql_live,include_migration_live=args.mysql_migrations_live,include_postgres_migration_live=args.postgres_migrations_live,include_postgres_storage_live=args.postgres_storage_live,include_postgres_game_action_live=args.postgres_game_actions_live,request_latency_callback=request_latency_callback,gunicorn_json_load_callback=gunicorn_json_load_callback,gunicorn_load_callback=gunicorn_load_callback)"
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the existing dispatch guard so default API runs never open a provider.
        self.assertIn("if args.storage or args.mysql_live or args.mysql_migrations_live or args.postgres_migrations_live or args.postgres_storage_live or args.postgres_game_actions_live: " + delegation, runner_source)
        # Keep listener, server, and raw subprocess lifecycle out of the extracted owner.
        self.assertNotIn("start_server", area_source)
        self.assertNotIn("ServerThread", area_source)
        self.assertNotIn("subprocess.run", area_source)

    # Prove the shared session/wallet-integrity registrations moved as one exact ordered area.
    def test_api_session_integrity_area_registration_ownership_is_exact(self):
        # Define every permanent ID and requirement mapping in historical execution order.
        expected_cases = (
            ("API-PRIVATE-SESSION-001", ["SESSION-003", "USER-001", "USER-003", "USER-005", "TOKEN-004", "TEST-039"]),
            ("API-MHVP-001", ["MHVP-001", "MHVP-002", "MHVP-003"]),
            ("API-CW-001", ["CW-001", "CW-002", "CW-003"]),
            ("API-BIG-SIX-001", ["BIG-SIX-001", "BIG-SIX-002", "BIG-SIX-003", "BIG-SIX-008"]),
            ("API-RD-001", ["RD-001", "RD-002", "RD-003"]),
            ("API-DT-001", ["DT-001", "DT-002", "DT-003", "DT-007"]),
            ("API-HILO-001", ["HILO-001", "HILO-002", "HILO-003"]),
            ("API-TCP-001", ["TCP-001", "TCP-002", "TCP-003"]),
            ("API-JOBVP-001", ["JOBVP-001", "JOBVP-002", "JOBVP-003"]),
            ("API-DWVP-001", ["DWVP-001", "DWVP-002", "DWVP-003"]),
            ("API-SCRATCH-001", ["SCRATCH-001", "SCRATCH-002", "SCRATCH-003"]),
            ("API-SIC-BO-001", ["SIC-BO-001", "SIC-BO-002", "SIC-BO-003", "SIC-BO-007"]),
            ("API-CHUCK-001", ["CHUCK-001", "CHUCK-002", "CHUCK-003", "CHUCK-007"]),
            ("API-CRAPS-001", ["CRAPS-001", "CRAPS-002", "CRAPS-003"]),
            ("API-CAA-001", ["CAA-001", "CAA-002", "CAA-003", "CAA-007"]),
            ("API-OU7-001", ["OU7-001", "OU7-002", "OU7-003", "OU7-008"]),
            ("API-PLINKO-001", ["PLINKO-001", "PLINKO-002", "PLINKO-003"]),
            ("API-FAN-TAN-001", ["FAN-TAN-001", "FAN-TAN-002", "FAN-TAN-003", "FAN-TAN-007"]),
            ("API-AB-001", ["AB-001", "AB-002", "AB-003"]),
            ("API-AD-001", ["AD-001", "AD-002", "AD-003"]),
            ("API-CS-001", ["CS-001", "CS-002", "CS-003"]),
            ("API-LIR-001", ["LIR-001", "LIR-002", "LIR-003"]),
            ("API-CH-001", ["CH-001", "CH-002", "CH-003"]),
            ("API-PGP-001", ["PGP-001", "PGP-002", "PGP-003"]),
            ("API-JP-001", ["JP-001", "JP-002", "JP-003"]),
            ("API-THPT-001", ["THPT-001", "THPT-002", "THPT-003", "THPT-005", "BOT-009", "BOT-010", "BOT-011", "LEDGER-026", "SEC-001", "SEC-002", "SEC-003", "SEC-004", "SEC-005", "SEC-006", "SEC-008", "SEC-009"]),
            ("API-TOKEN-001", ["TOKEN-003", "TOKEN-004"]),
            ("API-ADMIN-USERS-001", ["AUTH-005", "AUTH-008", "USER-002", "USER-004", "TEST-060"]),
            ("API-CONTRACT-V2-001", ["API-001", "API-002", "TOKEN-002"]),
            ("API-TERMS-001", ["TERMS-001", "TERMS-002", "TERMS-003"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "session_integrity.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the listener-free registration owner for callback capture.
        spec = importlib.util.spec_from_file_location("session_integrity_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registrations without invoking live HTTP or backend lifecycle.
        captured = []
        def capture(case_id, requirements, callback):
            # Retain identity, mapping, order, and callback for semantic checks.
            captured.append((case_id, requirements, callback))
        # Build two authenticated identities for every extracted per-game predicate.
        users = [{"player_id": "player-a"}, {"player_id": "player-b"}]
        # Define the complete state keys consumed by the extracted per-game callbacks.
        game_keys = (
            "three_card_poker_rounds", "jacks_or_better_rounds", "deuces_wild_rounds", "scratch_cards", "sic_bo_rounds", "chuck_a_luck_rounds", "craps_rounds", "crown_and_anchor_rounds", "over_under_7_rounds", "plinko_drops", "fan_tan_rounds", "andar_bahar_rounds", "acey_deucey_rounds", "caribbean_stud_rounds", "let_it_ride_rounds", "casino_holdem_rounds", "pai_gow_poker_rounds", "joker_poker_rounds", "texas_holdem_practice_hands",
        )
        # Seed a valid callback packet without using any production player or game state.
        state = {key: {"player-a": f"{key}-a", "player-b": f"{key}-b"} for key in game_keys}
        # Add the direct predicates consumed before and after the per-game block.
        state.update({"users": users, "mhvp_verified": True, "casino_war_verified": True, "big_six_verified": True, "red_dog_verified": True, "dragon_tiger_verified": True, "hi_lo_verified": True, "token_credit_count": 1, "contract_player": {"player_id": "player-a", "token_balance": 250, "token_label": "Play Tokens"}, "admin_blocked": 21, "email": "wallet-a@example.local"})
        # Preserve the historical private-session callback identity with an inert focused seam.
        wallet_calls = []
        def wallet_auth_integrity():
            # Record the callback invocation without contacting a listener.
            wallet_calls.append("called")
        # Fail the focused test if any extracted assertion predicate is false.
        def assert_condition(value, message):
            # Preserve the runner helper's boolean assertion semantics.
            if not value:
                raise AssertionError(message)
        # Register every callback through the exact explicit dependency boundary.
        module.run_cases(capture, wallet_auth_integrity, state, assert_condition)
        # Bind every permanent ID, requirement mapping, and historical position.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Execute each captured callback once against the valid synthetic state.
        for _, _, callback in captured:
            # Prove extracted closure semantics without network or process ownership.
            callback()
        # Require the private-session callback to execute exactly once in the focused model.
        self.assertEqual(wallet_calls, ["called"])
        # Reject duplicate literal registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one exact dependency-forwarding delegation at the historical boundary.
        delegation = "api_session_integrity.run_cases(run_case,wallet_auth_integrity,integrity_state,assert_condition)"
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the process-restart boundary immediately after the complete area.
        self.assertLess(runner_source.index(delegation), runner_source.index("# Stop and verify the live backend before persistence is tested across a process boundary."))
        # Keep server, transport, process, and persistence-reset ownership out of the area.
        for forbidden in ("start_server", "stop_server", "ServerThread", "subprocess.run", "reset_data"):
            self.assertNotIn(forbidden, area_source)

    # Prove the post-restart platform registrations moved as one exact ordered area.
    def test_api_post_restart_foundation_area_registration_ownership_is_exact(self):
        # Define every permanent ID and requirement mapping in historical execution order.
        expected_cases = (
            ("API-WALLET-RESTART-001", ["SESSION-003", "USER-001", "TOKEN-003", "TOKEN-004", "TEST-039", "MHVP-002", "CW-002", "BIG-SIX-002", "RD-002", "DT-002", "HILO-002", "SCRATCH-002", "SIC-BO-002", "CHUCK-002", "CRAPS-002", "CAA-002", "OU7-002", "PLINKO-002", "FAN-TAN-002", "AB-002", "AD-002", "CS-002", "LIR-002", "CH-002", "PGP-002", "JP-002", "THPT-002"]),
            ("API-CORE-001", ["CORE-001", "CORE-016", "TEST-003"]),
            ("API-CATALOG-001", ["CORE-021", "SESSION-005", "TEST-042"]),
            ("ECONOMICS-REGISTRY-001", ["TEST-175"]),
            ("API-I18N-001", ["I18N-001", "I18N-003"]),
            ("API-I18N-FOUNDATION-001", ["I18N-006", "I18N-007", "TEST-101"]),
            ("API-CONTROL-001", ["BOT-001", "BOT-003", "BOT-009", "BOT-010", "BOT-011", "ADMIN-023", "AUDIO-001", "AUDIO-002", "AUDIO-010", "AUTO-001", "AUTO-003"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "post_restart_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the listener-free registration owner for callback capture.
        spec = importlib.util.spec_from_file_location("post_restart_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registrations without invoking the live listener callbacks.
        captured = []
        def capture(case_id, requirements, callback):
            # Retain identity, mapping, order, and callback for semantic checks.
            captured.append((case_id, requirements, callback))
        # Record callback execution in the same order expected from the extracted area.
        callback_calls = []
        def callback(name):
            # Return a distinct inert callback that records its semantic owner.
            return lambda: callback_calls.append(name)
        # Preserve the shared i18n callback identity across its two registrations.
        i18n_callback = callback("i18n")
        # Register every callback through the exact explicit dependency boundary.
        module.run_cases(capture, callback("wallet_restart"), callback("core"), callback("catalog"), callback("economics"), i18n_callback, callback("control"))
        # Bind every permanent ID, requirement mapping, and historical position.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Require the shared i18n callback to remain identical at both historical positions.
        self.assertIs(captured[4][2], captured[5][2])
        # Execute each callback once to prove direct forwarding semantics.
        for _, _, registered_callback in captured:
            # Invoke only the inert focused seam, never live HTTP or process lifecycle.
            registered_callback()
        # Require exact callback execution order, including both i18n registrations.
        self.assertEqual(callback_calls, ["wallet_restart", "core", "catalog", "economics", "i18n", "i18n", "control"])
        # Reject duplicate literal registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one exact dependency-forwarding delegation at the historical boundary.
        delegation = "api_post_restart_foundation.run_cases(run_case,wallet_restart_persistence,core,catalog_foundation,lambda: game_economics_registry_tests.validate_registry(game_economics_registry_tests.read_json(game_economics_registry_tests.REGISTRY_PATH)),validate_i18n_resources,bots_audio_autoplay)"
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the next historical live-game owner after the complete area.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_core_live_games.run_cases("))
        # Keep server, transport, process, and persistence-reset ownership out of the area.
        for forbidden in ("start_server", "stop_server", "ServerThread", "subprocess.run", "reset_data"):
            self.assertNotIn(forbidden, area_source)

    # Prove the core live-game and Admin registrations moved as one exact ordered area.
    def test_api_core_live_games_area_registration_ownership_is_exact(self):
        # Define every permanent ID and requirement mapping in historical execution order.
        expected_cases = (
            ("API-ROU-001", ["ROU-010", "ROU-011", "ROU-030", "ROU-032", "LEDGER-001"]),
            ("API-SLOT-001", ["SLOT-001", "SLOT-002", "SLOT-003"]),
            ("API-BJ-001", ["BJ-010", "BJ-011", "BJ-020", "BJ-034"]),
            ("API-BJ-003", ["BJ-020", "LEDGER-015", "TEST-056"]),
            ("API-BJ-002", ["BJ-002", "BJ-003", "BJ-004", "BJ-005", "BJ-006", "BJ-007", "BJ-012", "BJ-015", "BJ-016", "BJ-017", "BJ-018", "BJ-019", "BJ-026", "BJ-031", "TEST-054"]),
            ("API-BAC-001", ["BAC-001", "BAC-010", "BAC-030"]),
            ("API-KENO-001", ["KENO-001", "KENO-002", "KENO-010"]),
            ("API-BINGO-001", ["BINGO-001", "BINGO-010", "BINGO-020"]),
            ("API-GAME-STATE-ISOLATION-001", ["ROU-010", "SLOT-019", "BJ-020", "BAC-010", "KENO-008", "BINGO-020", "LEDGER-001", "AUTO-001"]),
            ("API-ADMIN-001", ["ADMIN-001", "ADMIN-003", "ADMIN-004", "ADMIN-014", "DOC-001", "LOG-001", "ADMIN-USER-PENDING-035", "TERMS-PENDING-035", "TOKEN-PENDING-035", "I18N-003", "TEST-003"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "core_live_games.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so the focused model cannot open a listener.
        spec = importlib.util.spec_from_file_location("core_live_games_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registrations without invoking the live HTTP callbacks.
        captured = []
        def capture(case_id, requirements, callback):
            # Retain identity, mapping, order, and callback for semantic checks.
            captured.append((case_id, requirements, callback))
        # Build distinct inert callbacks in the same semantic order as the live runner.
        callback_calls = []
        def callback(name):
            # Return one inert callback that records direct forwarding.
            return lambda: callback_calls.append(name)
        # Register every callback through the explicit area boundary.
        callbacks = tuple(callback(name) for name in ("roulette", "slots", "blackjack", "blackjack_insurance", "blackjack_rules", "baccarat", "keno", "bingo", "private_sessions", "admin"))
        module.run_cases(capture, *callbacks)
        # Bind every permanent ID, requirement mapping, and historical position.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Execute each inert callback once to prove direct forwarding semantics.
        for _, _, registered_callback in captured:
            # Invoke only the inert seam, never live HTTP or process lifecycle.
            registered_callback()
        # Require callbacks to execute once in exact registration order.
        self.assertEqual(callback_calls, ["roulette", "slots", "blackjack", "blackjack_insurance", "blackjack_rules", "baccarat", "keno", "bingo", "private_sessions", "admin"])
        # Reject duplicate literal registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one exact dependency-forwarding delegation before runner-owned teardown.
        delegation = "api_core_live_games.run_cases(run_case,roulette,slots,blackjack,blackjack_insurance_phase_guard,blackjack_rule_edges,baccarat,keno,bingo,private_sessions,admin)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("api_post_restart_foundation.run_cases("), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("# Stop the tracked API child and prove its loopback listener is closed."))
        # Keep server, transport, process, and persistence-reset ownership out of the area.
        for forbidden in ("start_server", "stop_server", "ServerThread", "subprocess.run", "reset_data", "api("):
            self.assertNotIn(forbidden, area_source)

    # Prove the final live authentication registration has one exact area owner.
    def test_api_live_authentication_area_registration_ownership_is_exact(self):
        # Bind the permanent ID and its exact historical requirement mapping.
        expected_case = ("API-AUTH-001", ["AUTH-001", "SESSION-001", "SESSION-007", "SESSION-012", "USER-001", "TERMS-001"])
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "live_authentication.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only registration metadata so the focused test cannot open a listener.
        spec = importlib.util.spec_from_file_location("live_authentication_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture the registration and callback identity without live HTTP execution.
        captured = []
        def capture(case_id, requirements, callback):
            # Retain the immutable packet for exact comparison.
            captured.append((case_id, requirements, callback))
        # Record one inert callback execution through the area boundary.
        callback_calls = []
        def auth_callback():
            # Prove direct callback forwarding without session mutation.
            callback_calls.append("auth")
        # Register the one final API-lane case.
        module.run_cases(capture, auth_callback)
        # Require the exact permanent ID, mapping, and callback object.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), (expected_case,))
        self.assertIs(captured[0][2], auth_callback)
        # Execute the captured callback once and prove no wrapper substitution.
        captured[0][2]()
        self.assertEqual(callback_calls, ["auth"])
        # Reject duplicate literal registration ownership in the compatibility runner.
        self.assertNotRegex(runner_source, r"\brun_case\(\s*['\"]API-AUTH-001['\"]")
        # Require exact delegation after auth callback definition and before session-integrity state.
        delegation = "api_live_authentication.run_cases(run_case,auth_backend)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("def auth_backend():"), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("# Store wallet integrity evidence for the later server-restart persistence check."))
        # Keep HTTP, server, process, session, and storage implementation out of the owner.
        for forbidden in ("api(", "start_server", "stop_server", "ServerThread", "subprocess.run", "auth_core", "login_default_user"):
            self.assertNotIn(forbidden, area_source)

    # Prove the first API area moved as one exact registration group without duplication in the shim.
    def test_api_governance_area_registration_ownership_is_exact(self):
        # Define the exact reviewed registrations moved by this slice in historical execution order.
        expected_ids = (
            "FILE-HEADER-POLICY-001", "GOV-FILE-LENGTH-001", "PERF-PAYLOAD-BUDGET-001", "PERF-PAYLOAD-PROJECTION-001", "PERF-TARGET-GATE-001",
            "PERF-MULTIPROCESS-SAFETY-001",
            "GOV-GAME-SUITE-DISCOVERY-001", "GOV-GAME-SUITES-001", "GOV-REQUIREMENT-SHARDS-001", "GOV-DEAD-ARTIFACTS-001", "UI-ROULETTE-I18N-DIAGNOSTICS-001",
            "UI-I18N-SINGLE-SOURCE-001", "UI-BROWSER-WAIT-001", "CI-COMPUTE-001", "GOV-MODULE-VERSIONS-001", "GOV-NEWEST-GAME-BROWSER-COVERAGE-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit governance area module.
        governance_source = (API_CASES_ROOT / "governance.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", governance_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute a gate twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation at the historical registration point.
        self.assertEqual(runner_source.count("api_governance.run_cases(run_case,run_unit_module,ROOT)"), 1)

    # Prove the atomic game-state registrations moved as one exact ordered area.
    def test_api_game_atomic_area_registration_ownership_is_exact(self):
        # Define the complete reviewed atomic case order from Casino War through Pai Gow Poker.
        expected_ids = (
            "API-CW-ATOMIC-001", "API-KENO-ATOMIC-001", "API-BAC-ATOMIC-001", "API-BJ-ATOMIC-001",
            "API-MHVP-ATOMIC-001", "API-ROU-ATOMIC-001", "API-BINGO-ATOMIC-001", "API-CS-ATOMIC-001",
            "API-FOUR-CARD-POKER-ATOMIC-001", "API-TCP-ATOMIC-001", "API-CH-ATOMIC-001", "API-PGP-ATOMIC-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit atomic game-state area module.
        area_source = (API_CASES_ROOT / "game_atomic.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", area_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute an atomic game suite twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the established fresh-process helper.
        delegation = "api_game_atomic.run_cases(run_case,run_unit_module)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after governance and before the money-integrity area.
        self.assertLess(runner_source.index("api_governance.run_cases("), runner_source.index(delegation))
        # Keep the next extracted area after the complete atomic area.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_money_integrity.run_cases("))
        # Keep process construction and execution in the compatibility runner rather than the area owner.
        self.assertNotIn("subprocess.run", area_source)

    # Prove the storage and legacy-settlement registrations moved as one exact ordered area.
    def test_api_money_integrity_area_registration_ownership_is_exact(self):
        # Define the reviewed order from ledger-cache safety through bounded Bingo economics.
        expected_ids = (
            "STORAGE-LEDGER-CACHE-001", "API-LEGACY-SETTLE-001",
            "API-LEGACY-SETTLE-002", "API-BINGO-ECONOMICS-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit money-integrity area module.
        area_source = (API_CASES_ROOT / "money_integrity.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", area_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute money evidence twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the established fresh-process helper.
        delegation = "api_money_integrity.run_cases(run_case,run_unit_module)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after atomic game-state and before the Admin policy area.
        self.assertLess(runner_source.index("api_game_atomic.run_cases("), runner_source.index(delegation))
        # Keep the next extracted area after the complete money-integrity area.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_admin_policy.run_cases("))
        # Keep process construction and execution in the compatibility runner rather than the area owner.
        self.assertNotIn("subprocess.run", area_source)

    # Prove the Admin diagnostics and policy registrations moved as one exact ordered area.
    def test_api_admin_policy_area_registration_ownership_is_exact(self):
        # Define the reviewed order from state diagnostics through Guest admission policy.
        expected_ids = (
            "API-ADMIN-GAME-STATES-001", "API-ADMIN-ECONOMICS-001", "API-ADMIN-SESSION-POLICY-001",
            "API-ADMIN-RATE-LIMITS-001", "API-GUEST-ADMISSION-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit Admin policy area module.
        area_source = (API_CASES_ROOT / "admin_policy.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", area_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute a policy gate twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the established fresh-process helper.
        delegation = "api_admin_policy.run_cases(run_case,run_unit_module)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after money integrity and before game lifecycle evidence.
        self.assertLess(runner_source.index("api_money_integrity.run_cases("), runner_source.index(delegation))
        # Keep the next extracted game lifecycle area after the complete Admin policy area.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_game_lifecycle.run_cases("))
        # Keep process construction and execution in the compatibility runner rather than the area owner.
        self.assertNotIn("subprocess.run", area_source)

    # Prove the game lifecycle registrations moved as one exact ordered area.
    def test_api_game_lifecycle_area_registration_ownership_is_exact(self):
        # Define the complete reviewed order from practice-table escrow through Teen Patti state publication.
        expected_ids = (
            "API-THPT-ESCROW-001", "API-THPT-ATOMIC-001", "API-CRAPS-ATOMIC-001", "API-AB-ATOMIC-001",
            "API-OU7-ATOMIC-001", "API-BIG-SIX-ATOMIC-001", "API-CAA-ATOMIC-001", "API-FAN-TAN-ATOMIC-001",
            "API-AD-ATOMIC-001", "API-CHUCK-ATOMIC-001", "API-DWVP-ATOMIC-001", "API-DBVP-ATOMIC-001",
            "API-DT-ATOMIC-001", "API-JP-ATOMIC-001", "API-HILO-ATOMIC-001", "API-JOBVP-ATOMIC-001",
            "API-LIR-ATOMIC-001", "API-MSTUD-ATOMIC-001", "API-PLINKO-ATOMIC-001", "API-RD-ATOMIC-001",
            "API-SCRATCH-ATOMIC-001", "API-SIC-BO-ATOMIC-001", "API-SLOT-ATOMIC-001", "API-TEEN-PATTI-ATOMIC-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit game lifecycle area module.
        area_source = (API_CASES_ROOT / "game_lifecycle.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", area_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute a lifecycle suite twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the established fresh-process helper.
        delegation = "api_game_lifecycle.run_cases(run_case,run_unit_module)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after Admin policy and before delivery infrastructure.
        self.assertLess(runner_source.index("api_admin_policy.run_cases("), runner_source.index(delegation))
        # Keep the next extracted delivery-infrastructure area after the complete lifecycle area.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_delivery_infrastructure.run_cases("))
        # Keep process construction, execution, and listener ownership in the compatibility runner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove the listener-free delivery-infrastructure registrations moved as one ordered area.
    def test_api_delivery_infrastructure_area_registration_ownership_is_exact(self):
        # Define the reviewed order from edge preparation through CI qualification.
        expected_ids = (
            "EDGE-PREPARATION-001", "DEPLOY-PROVENANCE-001", "RELEASE-PREDECESSOR-001",
            "MONITOR-CONFIG-001", "DEPLOY-CICD-001", "DEPLOY-PULL-001", "CI-QUALIFICATION-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit delivery-infrastructure area module.
        area_source = (API_CASES_ROOT / "delivery_infrastructure.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", area_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute a delivery-policy gate twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the compatibility runner's run_case helper.
        delegation = "api_delivery_infrastructure.run_cases(run_case)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after game lifecycle and before frontend presentation.
        self.assertLess(runner_source.index("api_game_lifecycle.run_cases("), runner_source.index(delegation))
        # Keep the next extracted frontend-presentation area after delivery infrastructure.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_frontend_presentation.run_cases("))
        # Keep subprocess construction and every listener owner outside the extracted area.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove frontend-presentation registrations moved without process ownership.
    def test_api_frontend_presentation_area_registration_ownership_is_exact(self):
        # Define the reviewed registration and requirement order from Roulette motion through wallet timing.
        expected_cases = (
            ("UI-ROU-MOTION-001", ["ROU-063", "ROU-064", "ROU-065", "ROU-066", "ROU-067", "ROU-068", "ROU-069", "ROU-070", "TEST-102"]),
            ("UI-ROU-PRESENTATION-001", ["ROU-063", "ROU-064", "ROU-065", "ROU-066", "ROU-067", "ROU-068", "ROU-072"]),
            ("UI-SLOT-PRESENTATION-001", ["SLOT-030", "SLOT-031", "SLOT-032", "SLOT-033", "SLOT-034", "SLOT-035", "SLOT-037"]),
            ("UI-WALLET-TIMING-001", ["LEDGER-031", "TEST-151"]),
            ("UI-GAME-LIFECYCLE-001", ["CORE-034", "TEST-248"]),
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit frontend-presentation area module.
        area_path = API_CASES_ROOT / "frontend_presentation.py"
        # Read source once for duplicate and process-boundary assertions.
        area_source = area_path.read_text(encoding="utf-8")
        # Load the listener-free registration module without importing the compatibility runner.
        spec = importlib.util.spec_from_file_location("frontend_presentation_area", area_path)
        # Require a valid loader for the checked-in Python module.
        self.assertIsNotNone(spec.loader)
        # Construct the isolated module object from its exact file specification.
        module = importlib.util.module_from_spec(spec)
        # Execute only definitions and imports from the registration-only area.
        spec.loader.exec_module(module)
        # Capture every registration without executing any mapped test callback.
        captured = []
        # Record the exact registration tuple supplied by the area owner.
        def capture(case_id, requirements, callback):
            # Preserve each callback so its runner-owned binding can be inspected separately.
            captured.append((case_id, requirements, callback))
        # Use a stable sentinel for the runner-owned in-process Roulette callback.
        roulette_motion_callback = object()
        # Capture every runner-owned Node callback invocation without launching a subprocess.
        node_calls = []
        # Record the exact relative path and failure message delegated by a presentation callback.
        def capture_node(relative_path, failure_message):
            # Preserve inputs for equality assertions after the lazy callback runs.
            node_calls.append((relative_path, failure_message))
        # Register the area through the same callback boundary used by the compatibility runner.
        module.run_cases(capture, roulette_motion_callback, capture_node)
        # Prove exact IDs, requirement lists, and historical registration order.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Prove the Roulette motion case retains the runner-owned unittest callback verbatim.
        self.assertIs(captured[0][2], roulette_motion_callback)
        # Execute only the four inert lazy adapters against the capture callback.
        for _, _, callback in captured[1:]:
            # Resolve one lazy mapping without launching Node.
            callback()
        # Prove exact test paths and diagnostic messages survived the extraction.
        self.assertEqual(node_calls, [
            (Path("tests/games/roulette/test_frontend.mjs"), "Roulette presentation suite failed"),
            (Path("tests/games/slots/test_frontend.mjs"), "Slots presentation suite failed"),
            (Path("tests/wallet_timing.mjs"), "wallet timing suite failed"),
            (Path("tests/game_frontend_lifecycle.mjs"), "game frontend lifecycle suite failed"),
        ])
        # Require every moved registration to be absent from the compatibility runner.
        for case_id, _ in expected_cases:
            # Reject duplicated ownership that could execute a presentation gate twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit delegation through both runner-owned execution callbacks.
        delegation = "api_frontend_presentation.run_cases(run_case,run_roulette_motion_tests,run_game_frontend_node_test)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after delivery infrastructure and before self-service foundation.
        self.assertLess(runner_source.index("api_delivery_infrastructure.run_cases("), runner_source.index(delegation))
        # Keep the following self-service foundation area after the complete presentation area.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_self_service_foundation.run_cases("))
        # Keep process construction and every listener owner outside the extracted area.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove documentation, personal settings, and receipts moved as one listener-free area.
    def test_api_self_service_foundation_area_registration_ownership_is_exact(self):
        # Define exact case and requirement order from documentation through receipts.
        expected_cases = (
            ("API-DOCS-001", ["API-003", "TEST-152"]),
            ("API-SETTINGS-001", ["USER-006", "USER-007", "USER-008", "USER-009", "TEST-103", "TEST-158"]),
            ("API-RECEIPT-001", ["RECEIPT-001", "RECEIPT-002", "TEST-104"]),
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit self-service foundation area module.
        area_path = API_CASES_ROOT / "self_service_foundation.py"
        # Read source once for duplicate and process-boundary assertions.
        area_source = area_path.read_text(encoding="utf-8")
        # Load the listener-free registration module without importing the compatibility runner.
        spec = importlib.util.spec_from_file_location("self_service_foundation_area", area_path)
        # Require a valid loader for the checked-in Python module.
        self.assertIsNotNone(spec.loader)
        # Construct the isolated module object from its exact file specification.
        module = importlib.util.module_from_spec(spec)
        # Execute only definitions and imports from the registration-only area.
        spec.loader.exec_module(module)
        # Capture every registration without executing any mapped test callback.
        captured = []
        # Record exact case identity, requirement mapping, and callback ownership.
        def capture(case_id, requirements, callback):
            # Preserve all three registration dimensions for one equality assertion.
            captured.append((case_id, requirements, callback.__name__))
        # Register the area through the same callback boundary used by the compatibility runner.
        module.run_cases(capture)
        # Prove exact IDs, requirement lists, and historical registration order.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Prove each focused adapter remains owned by the extracted area.
        self.assertEqual(tuple(callback for _, _, callback in captured), ("_run_api_docs_tests", "_run_user_settings_tests", "_run_receipt_tests"))
        # Require every moved registration to be absent from the compatibility runner.
        for case_id, _ in expected_cases:
            # Reject duplicated ownership that could execute one self-service proof twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the runner-owned case recorder.
        delegation = "api_self_service_foundation.run_cases(run_case)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after frontend presentation.
        self.assertLess(runner_source.index("api_frontend_presentation.run_cases("), runner_source.index(delegation))
        # Keep the next specialized-game acceptance area after the self-service foundation.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_specialized_game_acceptance.run_cases("))
        # Keep subprocess construction and every listener owner outside the extracted area.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove specialized-game and cross-game-polish registrations moved as one listener-free area.
    def test_api_specialized_game_acceptance_area_registration_ownership_is_exact(self):
        # Define exact case and requirement order from Double Bonus through Slots economics.
        expected_cases = (
            ("API-DOUBLE-BONUS-VIDEO-POKER-001", ["DBVP-001", "DBVP-002", "TEST-114"]),
            ("API-MISSISSIPPI-STUD-001", ["MSTUD-001", "MSTUD-002", "TEST-115"]),
            ("API-TEEN-PATTI-001", ["TEENP-001", "TEENP-002", "TEST-116"]),
            ("UI-GAME-POLISH-001", ["I18N-010", "UX-020", "TEST-117"]),
            ("API-SLOT-ECONOMICS-001", ["SLOT-036"]),
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit specialized-game acceptance area module.
        area_path = API_CASES_ROOT / "specialized_game_acceptance.py"
        # Read source once for duplicate and process-boundary assertions.
        area_source = area_path.read_text(encoding="utf-8")
        # Load the listener-free registration module without importing the compatibility runner.
        spec = importlib.util.spec_from_file_location("specialized_game_acceptance_area", area_path)
        # Require a valid loader for the checked-in Python module.
        self.assertIsNotNone(spec.loader)
        # Construct the isolated module object from its exact file specification.
        module = importlib.util.module_from_spec(spec)
        # Execute only definitions and imports from the registration-only area.
        spec.loader.exec_module(module)
        # Capture every registration without executing any mapped test callback.
        captured = []
        # Record exact case identity, requirement mapping, and callback ownership.
        def capture(case_id, requirements, callback):
            # Preserve all three dimensions for one fail-closed equality assertion.
            captured.append((case_id, requirements, callback.__name__))
        # Register the area through the same callback boundary used by the compatibility runner.
        module.run_cases(capture)
        # Prove exact IDs, requirement lists, and historical registration order.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        # Prove each focused adapter remains owned by the extracted area.
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "_run_double_bonus_video_poker_tests", "_run_mississippi_stud_tests", "_run_teen_patti_tests",
            "_run_game_polish_tests", "_run_slots_economics_tests",
        ))
        # Require every moved registration to be absent from the compatibility runner.
        for case_id, _ in expected_cases:
            # Reject duplicated ownership that could execute one game acceptance proof twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation through the runner-owned case recorder.
        delegation = "api_specialized_game_acceptance.run_cases(run_case)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the historical boundary after self-service foundation.
        self.assertLess(runner_source.index("api_self_service_foundation.run_cases("), runner_source.index(delegation))
        # Keep the following player-foundation area after specialized-game acceptance.
        self.assertLess(runner_source.index(delegation), runner_source.index("api_player_foundation.run_cases("))
        # Keep subprocess construction and every listener owner outside the extracted area.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove player-experience and account-foundation registrations moved as one listener-free area.
    def test_api_player_foundation_area_registration_ownership_is_exact(self):
        # Define exact case and requirement order from wellness through static marketing.
        expected_cases = (
            ("API-WELLNESS-001", ["WELL-001", "WELL-002", "TEST-105"]),
            ("API-TOUR-001", ["TOUR-001", "TOUR-002", "TEST-106"]),
            ("API-SELF-SERVICE-BATCH-001", ["REPLAY-001", "REPLAY-002", "PROFILE-001", "PROFILE-002", "COMPARE-001", "TEST-108", "TEST-109", "TEST-110"]),
            ("API-CONVERT-001", ["CONVERT-001", "CONVERT-002", "CONVERT-003", "GUEST-007", "TEST-111", "TEST-158", "TEST-195"]),
            ("API-ADMIN-GUEST-CONVERT-001", ["ADMIN-035", "GUEST-007", "TEST-193", "TEST-195"]),
            ("API-ACCOUNT-SPINE-001", ["AUTH-010", "AUTH-012", "AUTH-015", "AUTH-016", "ADMIN-028", "ADMIN-033", "OAUTH-011", "OAUTH-012", "RESET-004", "FEEDBACK-005", "I18N-009", "TEST-112", "TEST-138", "TEST-158", "TEST-167"]),
            ("API-ADMIN-SESSIONS-001", ["SESSION-006", "SESSION-007", "SESSION-008", "ADMIN-028", "TEST-143"]),
            ("STATIC-MARKETING-001", ["MARKETING-001", "MARKETING-002", "MARKETING-003", "TEST-107"]),
        )
        # Read the compatibility runner and the extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "player_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be inspected without execution.
        spec = importlib.util.spec_from_file_location("player_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture registrations while retaining Node execution ownership in the runner callback.
        captured = []
        def capture(case_id, requirements, callback):
            # Retain immutable evidence without invoking a focused suite.
            captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture, lambda *_args: None)
        # Bind exact case, requirement, and callback ownership in historical order.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "run_wellness_tests", "run_whats_new_tests", "run_self_service_batch_tests", "run_guest_conversion_tests",
            "run_admin_guest_conversion_tests", "run_account_spine_tests", "run_admin_session_control_tests", "run_marketing_site_tests",
        ))
        # Reject duplicate registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation through the runner-owned recorder and Node executor.
        delegation = "api_player_foundation.run_cases(run_case,run_game_frontend_node_test)"
        self.assertEqual(runner_source.count(delegation), 1)
        # Preserve the boundary after specialized-game acceptance and before GameCore ownership.
        self.assertLess(runner_source.index("api_specialized_game_acceptance.run_cases("), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("api_gamecore_mobile_foundation.run_cases("))
        # Keep subprocess and listener construction outside the extracted registration owner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove GameCore and mobile-foundation registrations moved as one exact listener-free area.
    def test_api_gamecore_mobile_foundation_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("API-GAMECORE-001", ["GAMECORE-001", "GAMECORE-002", "GAMECORE-007", "GAMECORE-009", "TEST-127", "TEST-235", "TEST-236", "TEST-237", "TEST-238", "TEST-239", "TEST-240", "TEST-246"]),
            ("API-GAMECORE-005", ["GAMECORE-005", "GAMECORE-006", "GAMECORE-007", "STORAGE-017", "TEST-233", "TEST-234", "TEST-235", "TEST-236", "TEST-237", "TEST-238", "TEST-239", "TEST-240", "TEST-245"]),
            ("API-GAMECORE-002", ["GAMECORE-003", "LEDGER-033", "TEST-164"]),
            ("API-GAMECORE-004", ["LEDGER-032", "GAMECORE-004", "GAMECORE-008", "TEST-157", "TEST-241"]),
            ("API-GAMECORE-003", ["CORE-031"]),
            ("API-GAME-ACTION-LIFECYCLE-001", ["CORE-031", "STORAGE-013", "TEST-174"]),
            ("API-MOBILE-CORE-001", ["CORE-032", "AUTH-019", "SEC-016", "SESSION-013", "TEST-172"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "gamecore_mobile_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be inspected without execution.
        spec = importlib.util.spec_from_file_location("gamecore_mobile_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registration identity without running any focused suite.
        captured = []
        def capture(case_id, requirements, callback):
            # Preserve all ownership dimensions for one fail-closed equality proof.
            captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture)
        # Bind permanent IDs, requirement mappings, order, and focused callback ownership.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "_run_simple_game_core_tests", "_run_simple_game_atomic_tests", "_run_settlement_adapter_tests",
            "_run_catalog_settlement_boundary_tests", "_run_game_action_contract_tests",
            "_run_game_action_contract_tests", "_run_mobile_core_security_tests",
        ))
        # Reject duplicate registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the original player-foundation to catalog-expansion boundary.
        delegation = "api_gamecore_mobile_foundation.run_cases(run_case)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("api_player_foundation.run_cases("), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("api_catalog_expansion.run_cases("))
        # Keep process, listener, and server lifecycle out of the extracted owner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)
        self.assertNotIn("start_server", area_source)

    # Prove catalog-expansion registrations moved as one exact listener-free area.
    def test_api_catalog_expansion_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("API-COLOR-WHEEL-001", ["CWHEEL-001", "CWHEEL-002", "TEST-128"]),
            ("API-POKER-DICE-001", ["PDICE-001", "PDICE-002", "TEST-129"]),
            ("API-BOULE-001", ["BOULE-001", "BOULE-002", "TEST-130"]),
            ("API-FARO-001", ["FARO-001", "FARO-002", "TEST-131"]),
            ("API-TRENTE-ET-QUARANTE-001", ["TEQ-001", "TEQ-002", "TEST-119"]),
            ("API-PACHINKO-001", ["PACH-001", "PACH-002", "TEST-120"]),
            ("API-COIN-PUSHER-001", ["COINP-001", "COINP-002", "TEST-121"]),
            ("API-MARBLE-RACE-001", ["MARBLE-001", "MARBLE-002", "TEST-122"]),
            ("API-PATTERN-DRAW-001", ["PATTERN-001", "PATTERN-002", "TEST-123"]),
            ("API-LUCKY-GRID-001", ["LGRID-001", "LGRID-002", "TEST-124"]),
            ("API-DAILY-DRAW-LAB-001", ["DDLAB-001", "DDLAB-002", "TEST-125"]),
            ("API-FOUR-CARD-POKER-001", ["FOURCP-001", "FOURCP-002", "TEST-126"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "catalog_expansion.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be inspected without execution.
        spec = importlib.util.spec_from_file_location("catalog_expansion_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registration identity without running any focused game suite.
        captured = []
        def capture(case_id, requirements, callback):
            # Preserve all ownership dimensions for one fail-closed equality proof.
            captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture)
        # Bind permanent IDs, requirement mappings, order, and focused callback ownership.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "_run_color_wheel_tests", "_run_poker_dice_tests", "_run_boule_tests", "_run_faro_tests",
            "_run_trente_et_quarante_tests", "_run_pachinko_tests", "_run_coin_pusher_tests",
            "_run_marble_race_tests", "_run_pattern_draw_tests", "_run_lucky_grid_tests",
            "_run_daily_draw_lab_tests", "_run_four_card_poker_tests",
        ))
        # Reject duplicate registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation after GameCore/Mobile and before Keno/Admin ownership.
        delegation = "api_catalog_expansion.run_cases(run_case)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("api_gamecore_mobile_foundation.run_cases("), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("api_keno_admin_foundation.run_cases("))
        # Keep subprocess and listener lifecycle out of this extracted registration owner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)

    # Prove Keno and Admin-foundation registrations moved as one exact listener-free area.
    def test_api_keno_admin_foundation_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("UI-KENO-BALL-RAIL-001", ["KENO-026", "TEST-113"]),
            ("API-KENO-ECONOMICS-001", ["KENO-027", "TEST-147"]),
            ("UI-ADMIN-LEDGER-LABELS-001", ["ADMIN-027", "TEST-132"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "keno_admin_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be inspected without execution.
        spec = importlib.util.spec_from_file_location("keno_admin_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registration identity without running any focused suite.
        captured = []
        def capture(case_id, requirements, callback):
            # Preserve all ownership dimensions for one fail-closed equality proof.
            captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture)
        # Bind permanent IDs, requirement mappings, order, and focused callback ownership.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "_run_keno_ball_rail_tests", "_run_keno_economics_tests", "_run_admin_ledger_label_tests",
        ))
        # Reject duplicate registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the original catalog-expansion to security/UI boundary.
        delegation = "api_keno_admin_foundation.run_cases(run_case)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("api_catalog_expansion.run_cases("), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("api_security_ui_foundation.run_cases("))
        # Keep process, listener, and server lifecycle out of the extracted owner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)
        self.assertNotIn("start_server", area_source)

    # Prove security and UI-foundation registrations moved as one exact listener-free area.
    def test_api_security_ui_foundation_area_registration_ownership_is_exact(self):
        # Define the exact reviewed cases and requirement mappings in historical order.
        expected_cases = (
            ("API-MAGIC-LINK-001", ["MAGIC-001", "MAGIC-002", "MAGIC-003", "TEST-118"]),
            ("API-SEC-PREVIEW-001", ["SEC-010", "SESSION-006", "ADMIN-024", "AUTH-007", "TEST-047"]),
            ("FRONTEND-SAFETY-001", ["SEC-013", "SEC-015", "UX-021", "UX-027", "CORE-028", "ROU-043", "TEENP-002", "MOTION-010", "AUTO-015", "AUDIO-010", "ADMIN-032", "TEST-136", "TEST-153", "TEST-155", "TEST-156"]),
            ("GOV-INNER-HTML-001", ["CORE-033", "SEC-017", "TEST-186"]),
            ("UI-REPEAT-BET-001", ["UX-022", "TEST-137"]),
        )
        # Read the compatibility runner and extracted owner as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        area_path = API_CASES_ROOT / "security_ui_foundation.py"
        area_source = area_path.read_text(encoding="utf-8")
        # Load only the registration owner so callbacks can be inspected without execution.
        spec = importlib.util.spec_from_file_location("security_ui_foundation_area", area_path)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Capture exact registration identity without running any focused suite.
        captured = []
        def capture(case_id, requirements, callback):
            # Preserve all ownership dimensions for one fail-closed equality proof.
            captured.append((case_id, requirements, callback.__name__))
        module.run_cases(capture)
        # Bind permanent IDs, requirement mappings, order, and focused callback ownership.
        self.assertEqual(tuple((case_id, requirements) for case_id, requirements, _ in captured), expected_cases)
        self.assertEqual(tuple(callback for _, _, callback in captured), (
            "_run_magic_link_tests", "_run_restricted_preview_security_tests", "_run_frontend_safety_tests",
            "_run_inner_html_template_tests", "_run_repeat_bet_tests",
        ))
        # Reject duplicate registration ownership in the compatibility runner.
        for case_id, _ in expected_cases:
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation after the extracted Keno/Admin block and before authentication.
        delegation = "api_security_ui_foundation.run_cases(run_case)"
        self.assertEqual(runner_source.count(delegation), 1)
        self.assertLess(runner_source.index("api_keno_admin_foundation.run_cases("), runner_source.index(delegation))
        self.assertLess(runner_source.index(delegation), runner_source.index("api_auth.run_cases("))
        # Keep process, listener, and server lifecycle out of the extracted owner.
        self.assertNotIn("subprocess.run", area_source)
        self.assertNotIn("ServerThread", area_source)
        self.assertNotIn("start_server", area_source)

    # Prove listener-free authentication infrastructure moved as one exact ordered area.
    def test_api_auth_area_registration_ownership_is_exact(self):
        # Define the exact reviewed registrations moved by this slice in historical execution order.
        expected_ids = (
            "OAUTH-MOCK-001", "API-AUTH-DEPLOYMENT-001", "API-SEC-001", "API-OTT-001",
            "API-MAIL-001", "API-INVITE-001", "API-VERIFIED-EMAIL-001", "API-RESET-001",
        )
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit authentication area module.
        auth_source = (API_CASES_ROOT / "auth.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", auth_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute an authentication gate twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation at the historical registration point.
        self.assertEqual(runner_source.count("api_auth.run_cases(run_case,run_oauth_mock_tests,validate_deployment_bootstrap,run_server_authority_tests)"), 1)

    # Prove the listener-free feedback registration moved to one exact area owner.
    def test_api_feedback_area_registration_ownership_is_exact(self):
        # Define the exact reviewed registration moved by this slice.
        expected_ids = ("API-FEEDBACK-001",)
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit feedback area module.
        feedback_source = (API_CASES_ROOT / "feedback.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", feedback_source))
        # Require the complete reviewed area to move without adding or dropping an ID.
        self.assertEqual(extracted_ids, expected_ids)
        # Reject duplicated ownership that could execute the feedback gate twice.
        self.assertNotRegex(runner_source, r"\brun_case\(\s*['\"]API\-FEEDBACK\-001['\"]")
        # Require one explicit area delegation at the historical registration point.
        self.assertEqual(runner_source.count("api_feedback.run_cases(run_case)"), 1)

        # Prove delegation remains between the adjacent authentication and Guest Trial areas.
        self.assertLess(runner_source.index("api_auth.run_cases("), runner_source.index("api_feedback.run_cases("))
        # Reject ordering drift that would change the historical API-lane execution sequence.
        self.assertLess(runner_source.index("api_feedback.run_cases("), runner_source.index("api_guest.run_cases("))

    # Prove the live Guest/Admin registration moved without transferring server lifecycle ownership.
    def test_api_admin_guest_area_registration_ownership_is_exact(self):
        # Define the exact reviewed registration moved by this slice.
        expected_ids = ("API-ADMIN-GUEST-001",)
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit live Guest/Admin area module.
        area_source = (API_CASES_ROOT / "admin_guest.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", area_source))
        # Require the complete reviewed area to move without adding or dropping an ID.
        self.assertEqual(extracted_ids, expected_ids)
        # Reject duplicated ownership that could execute the live Guest/Admin gate twice.
        self.assertNotRegex(runner_source, r"\brun_case\(\s*['\"]API\-ADMIN\-GUEST\-001['\"]")
        # Require one explicit area delegation with the existing runner-owned base and validator.
        delegation = "api_admin_guest.run_cases(run_case,base,validate_guest_admin_api)"
        # Reject missing or duplicated delegation in the compatibility runner.
        self.assertEqual(runner_source.count(delegation), 1)
        # Isolate the initial live-server window before the next inline case body begins.
        live_window = runner_source.split("proc,base=start_server()", 1)[1].split("def nonfinite_money_api():", 1)[0]
        # Preserve login before registration so the validator receives the historical Admin session.
        self.assertLess(live_window.index("login_default_user(base)"), live_window.index(delegation))
        # Keep server startup, login, and validator implementation in the compatibility runner.
        self.assertIn("proc,base=start_server()", runner_source)
        # Reject accidental listener or validator ownership expansion into the extracted area.
        self.assertNotIn("start_server", area_source)
        # Keep the live validator outside the area owner so this slice moves registration only.
        self.assertNotIn("def validate_guest_admin_api", area_source)

    # Prove listener-free Guest Trial registrations moved as one exact ordered area.
    def test_api_guest_area_registration_ownership_is_exact(self):
        # Define the exact reviewed registrations moved by this slice in historical execution order.
        expected_ids = ("API-GUEST-LIFECYCLE-001", "API-GUEST-ANALYTICS-001", "API-GUEST-CONTRACT-001")
        # Read the compatibility runner and extracted area as inert source text.
        runner_source = BROWSER_RUNNER.read_text(encoding="utf-8")
        # Bind ownership to the one explicit Guest Trial area module.
        guest_source = (API_CASES_ROOT / "guest.py").read_text(encoding="utf-8")
        # Extract exact literal registration order from the new area module.
        extracted_ids = tuple(re.findall(r"\brun_case\(\s*['\"]([^'\"]+)['\"]", guest_source))
        # Require the whole reviewed area to move in its original order.
        self.assertEqual(extracted_ids, expected_ids)
        # Require every moved registration to be absent from the compatibility runner.
        for case_id in expected_ids:
            # Reject duplicated ownership that could execute a Guest Trial gate twice.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one explicit area delegation at the historical registration point.
        self.assertEqual(runner_source.count("api_guest.run_cases(run_case,validate_guest_lifecycle,validate_guest_analytics,validate_guest_contracts)"), 1)

    # Prove semantic game colors remain route- or component-scoped without a global important cascade. (#717)
    def test_semantic_game_color_namespaces_are_scoped_without_important(self):
        # Read each production style owner as inert text so this focused oracle opens no listener or browser.
        stylesheet = self.workflow_text(ROOT / "web" / "styles.css")
        # Read Color Wheel's external route-owned stylesheet independently from the shared stylesheet.
        color_wheel_styles = self.workflow_text(ROOT / "web" / "games" / "color_wheel.css")
        # Read Roulette's external route-owned stylesheet independently from other game modules.
        roulette_styles = self.workflow_text(ROOT / "web" / "games" / "roulette.css")
        # Read Trente et Quarante's external card-style owner after its lifecycle-adopter extraction.
        trente_styles = self.workflow_text(ROOT / "web" / "games" / "trente_et_quarante.css")
        # Bind the source header to the permanent grep-policy explanation requested by issue #717.
        namespace_note = "/* CSS namespace gate (#717): bare `.red`, `.black`, and `.green` rules are forbidden; route and card scopes own semantic game colors. */"
        # Require the namespace rule to remain visible before every executable stylesheet rule.
        self.assertEqual(stylesheet.splitlines()[0], namespace_note)
        # Reject the three bare semantic selectors that previously leaked into unrelated game namespaces.
        self.assertIsNone(re.search(r"(?m)^\s*\.(?:red|black|green)\s*\{", stylesheet))
        # Isolate the shared playing-card suit rule without depending on unrelated stylesheet ordering.
        playing_card_rule = stylesheet.split(".playing-card.red", 1)[1].split("}", 1)[0]
        # Preserve the exact red suit foreground and ivory card face after removing the cascade conflict.
        self.assertIn("color: #b10020;", playing_card_rule)
        self.assertIn("background: #fbf7e9;", playing_card_rule)
        # Reject a priority override on the scoped card face because no global color fallback remains.
        self.assertNotIn("!important", playing_card_rule)
        # Bind Color Wheel's route-owned gradients to their exact production stops.
        for selector, start, end in (
            ("red", "#d6323d", "#8e1822"),
            ("black", "#2a2a2a", "#0e0e0e"),
            ("green", "#0f9c4c", "#0a5f2e"),
        ):
            # Require every Color Wheel semantic control to remain owned by its formatted external stylesheet.
            self.assertRegex(color_wheel_styles, rf"\.cw-bet\.{selector}\s*\{{\s*background:\s*linear-gradient\(180deg,\s*{start},\s*{end}\);\s*\}}")
        # Bind the exact red card foreground to the formatted game-owned stylesheet.
        self.assertRegex(trente_styles, r"\.teq-card\.red\s*\{\s*color:\s*#b41b29;\s*\}")
        # Bind the exact black card foreground to the same route-owned stylesheet.
        self.assertRegex(trente_styles, r"\.teq-card\.black\s*\{\s*color:\s*#161616;\s*\}")
        # Enumerate every Roulette selector that previously needed an important counter-override.
        roulette_selectors = (
            ".roulette-premium .table-cell.red",
            ".roulette-premium .table-cell.black",
            ".roulette-premium .table-cell.green",
            ".roulette-result-pocket.red",
            ".roulette-result-pocket.black",
            ".roulette-result-pocket.green",
            ".roulette-history-pills span.red",
            ".roulette-history-pills span.black",
            ".roulette-history-pills span.green",
            ".roulette-history-pills span.result-cell",
        )
        # Check every formerly conflicting Roulette rule through one exact scoped oracle.
        for selector in roulette_selectors:
            # Require the external route stylesheet to retain exactly one owner for the semantic selector.
            matching_rules = re.findall(rf"(?m)^{re.escape(selector)}\s*\{{([^}}]*)\}}", roulette_styles)
            # Reject missing or duplicate selector ownership after the lifecycle stylesheet extraction.
            self.assertEqual(len(matching_rules), 1)
            # Isolate only the selected external rule body for the priority assertion.
            rule_body = matching_rules[0]
            # Reject all important priority from the former global-color cascade war.
            self.assertNotIn("!important", rule_body)

    # Prove the complete auth-backend/PWA affinity family has one external owner and one runner delegation.
    def test_browser_auth_backend_pwa_affinity_registration_ownership_is_exact(self):
        # Read the compatibility runner and extracted owner as inert source so this gate opens no Browser or listener.
        runner_source = self.workflow_text(BROWSER_RUNNER)
        # Read the complete affinity owner independently of its import path.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "auth_backend_pwa.py")
        # Bind the exact permanent producer/consumer identities declared by browser_sharding.py.
        expected_ids = ("BR-AUTH-BACKEND-001", "BR-PWA-001", "BR-PWA-UPDATE-001")
        # Extract only literal permanent registrations from the new owner.
        owner_ids = tuple(re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", owner_source))
        # Require exact identity and historical order without invented or duplicate cases.
        self.assertEqual(owner_ids, expected_ids)
        # Reject any remaining inline registration in the compatibility runner.
        for case_id in expected_ids:
            # Keep each permanent identity under exactly one executable source owner.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the group's exact historical position.
        self.assertEqual(runner_source.count("browser_auth_backend_pwa.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser,base,packaged_version,screenshots,ROOT,DEFAULT_AUTH_EMAIL,DEFAULT_AUTH_PASSWORD,PlaywrightTimeoutError)"), 1)
        # Require the extracted owner to retain the complete owning-shard execution guard.
        self.assertEqual(owner_source.count("if browser_shard_owns_group('auth_backend_pwa'):"), 1)
        # Require the extracted owner to advance all three source positions on non-owning shards.
        self.assertEqual(owner_source.count("skip_browser_affinity('auth_backend_pwa')"), 1)
        # Import the extracted owner without starting the compatibility runner.
        from tests.cases.browser import auth_backend_pwa
        # Retain the exact skip identity emitted by a non-owning shard.
        skipped_groups = []
        # Reject any accidental case execution on a shard that does not own the complete group.
        reject_case = lambda *_args: self.fail("non-owner executed an auth-backend/PWA case")
        # Execute the non-owner path with every Browser dependency absent so setup access fails the test immediately.
        auth_backend_pwa.run_cases(reject_case, lambda group_name: False, skipped_groups.append, None, None, None, None, None, None, None, None)
        # Require one atomic skip for the exact complete affinity group.
        self.assertEqual(skipped_groups, ["auth_backend_pwa"])

    # Prove the complete disposable guest-lifecycle affinity family has one external owner and one runner delegation.
    def test_browser_guest_lifecycle_affinity_registration_ownership_is_exact(self):
        # Read the compatibility runner and extracted owner as inert source so this gate opens no Browser or listener.
        runner_source = self.workflow_text(BROWSER_RUNNER)
        # Read the complete guest owner independently of its import path.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "guest_lifecycle.py")
        # Bind the exact permanent guest lifecycle identities declared by browser_sharding.py.
        expected_ids = ("BR-GUEST-TRIAL-001", "BR-GUEST-REFRESH-001", "BR-GUEST-CONVERT-ANALYTICS-001")
        # Extract only literal permanent registrations from the new owner.
        owner_ids = tuple(re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", owner_source))
        # Require exact identity and historical order without invented or duplicate cases.
        self.assertEqual(owner_ids, expected_ids)
        # Reject any remaining inline registration in the compatibility runner.
        for case_id in expected_ids:
            # Keep each permanent identity under exactly one executable source owner.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the group's exact historical position.
        self.assertEqual(runner_source.count("browser_guest_lifecycle.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser,base,screenshots,ROOT,read_i18n_json,auth_core,guest_analytics)"), 1)
        # Require one owner-level guard without repeated partial setup checks.
        self.assertEqual(owner_source.count("browser_shard_owns_group('guest_lifecycle')"), 1)
        # Require the extracted owner to advance all three source positions on non-owning shards.
        self.assertEqual(owner_source.count("skip_browser_affinity('guest_lifecycle')"), 1)
        # Import the extracted owner without starting the compatibility runner.
        from tests.cases.browser import guest_lifecycle
        # Retain the exact skip identity emitted by a non-owning shard.
        skipped_groups = []
        # Reject any accidental case execution on a shard that does not own the complete group.
        reject_case = lambda *_args: self.fail("non-owner executed a guest-lifecycle case")
        # Execute the non-owner path with every Browser dependency absent so setup access fails the test immediately.
        guest_lifecycle.run_cases(reject_case, lambda group_name: False, skipped_groups.append, None, None, None, None, None, None, None)
        # Require one atomic skip for the exact complete affinity group.
        self.assertEqual(skipped_groups, ["guest_lifecycle"])

    # Prove the reduced auth/lobby affinity families share one external owner and runner delegation.
    def test_browser_auth_lobby_affinity_registration_ownership_is_exact(self):
        # Read the compatibility runner and extracted owner as inert source so this gate opens no Browser or listener.
        runner_source = self.workflow_text(BROWSER_RUNNER)
        # Read the complete auth/lobby owner independently of its import path.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "auth_lobby.py")
        # Bind each reduced affinity tuple while preserving the complete historical source order.
        expected_groups = {
            "auth_public": ("BR-STATIC-CACHE-001", "BR-MARKETING-001", "BR-SHELL-BRAND-GUEST-001", "BR-OAUTH-001", "BR-OAUTH-SIGNUP-001", "BR-VERIFIED-EMAIL-001", "BR-TOUCH-TARGET-AUTH-001"),
            "auth_session": ("BR-AUTH-LOGIN-001", "BR-TERMS-001", "BR-AUTH-SHELL-001", "BR-OAUTH-RUNTIME-001", "BR-TOKEN-001", "BR-SEC-001", "BR-AUTH-LOCALE-001", "BR-AUTH-LOGOUT-001"),
            "lobby_shell": ("BR-TOKEN-FRACTION-001", "BR-SHELL-001", "BR-TOUCH-TARGET-001", "BR-SHELL-BRAND-001", "BR-TOKEN-WALLET-001", "BR-LOBBY-001", "BR-CATALOG-NAV-001", "BR-CATALOG-I18N-RU-001", "BR-LOBBY-RESP-001"),
        }
        # Flatten the insertion-ordered tuples into the unchanged registration stream.
        expected_ids = tuple(case_id for group_ids in expected_groups.values() for case_id in group_ids)
        # Extract only literal permanent registrations from the new owner.
        owner_ids = tuple(re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", owner_source))
        # Require exact identity and historical order without invented or duplicate cases.
        self.assertEqual(owner_ids, expected_ids)
        # Reject any remaining inline registration in the compatibility runner.
        for case_id in expected_ids:
            # Keep each permanent identity under exactly one executable source owner.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the group's exact historical position.
        self.assertEqual(runner_source.count("browser_auth_lobby.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser_shard_owns,page,base,ROOT,visual_matrix,read_i18n_json,casino_config,assert_condition,shot,catalog_evidence,region_evidence,wallet_evidence,footer_evidence,game_evidence,console_errors,http_errors,provider_requests)"), 1)
        # Require one exact owner decision and one exact skip for every reduced contiguous family.
        for group_name in expected_groups:
            # Resolve ownership once before any setup can mutate browser state.
            self.assertEqual(owner_source.count(f"browser_shard_owns_group('{group_name}')"), 1)
            # Advance only the named family on non-owning shards.
            self.assertEqual(owner_source.count(f"skip_browser_affinity('{group_name}')"), 1)
        # Require each owner to establish its canonical independent starting state before its first case.
        self.assertLess(owner_source.index("initial_shell_response=page.goto(base"), owner_source.index("run_case('BR-STATIC-CACHE-001'"))
        self.assertLess(owner_source.index("page.get_by_test_id('auth-locale-select').select_option('ru-RU')"), owner_source.index("run_case('BR-AUTH-LOGIN-001'"))
        self.assertLess(owner_source.index("lobby_login=page.request.post"), owner_source.index("run_case('BR-TOKEN-FRACTION-001'"))
        # Require teardown to persist the neutral locale so a later full-page game reload cannot inherit owner-specific Russian state.
        self.assertIn("page.get_by_test_id('personal-settings-locale').select_option('en-US')", owner_source)
        self.assertIn("with page.expect_response(lambda response: response.url.endswith('/api/v2/me/settings') and response.request.method=='PATCH') as post_affinity_settings_info:", owner_source)
        self.assertIn("assert post_affinity_settings_info.value.json()['data']['settings']['locale']=='en-US'", owner_source)
        # Import the extracted owner without starting the compatibility runner.
        from tests.cases.browser import auth_lobby
        # Retain the exact skip identity emitted by a non-owning shard.
        skipped_groups = []
        # Reject any accidental case execution on a shard that does not own the complete group.
        reject_case = lambda *_args: self.fail("non-owner executed an auth/lobby case")
        # Execute the non-owner path with every page dependency absent so setup access fails the test immediately.
        auth_lobby.run_cases(reject_case, lambda group_name: False, skipped_groups.append, *([None] * 17))
        # Require one ordered skip for each exact contiguous reduced family.
        self.assertEqual(skipped_groups, ["auth_public", "auth_session", "lobby_shell"])

    # Prove the independent Roulette, Slots, and Keno affinity families share one source owner and runner delegation.
    def test_browser_roulette_slots_keno_affinity_registration_ownership_is_exact(self):
        # Read the compatibility runner and extracted owner as inert source so this gate opens no Browser or listener.
        runner_source = self.workflow_text(BROWSER_RUNNER)
        # Read the complete multi-game owner independently of its import path.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "roulette_slots_keno.py")
        # Bind each reduced affinity tuple while preserving the complete historical source order.
        expected_groups = {
            "roulette": (
                "BR-ROU-FORMAL-SETTINGS-001", "BR-ROU-HITMAP-001", "BR-ROU-REFUND-001", "BR-ROU-SLIP-AUDIT-001", "BR-ROU-PREMIUM-001",
                "BR-I18N-GAMESTATE-ROU-001", "BR-ROU-MOTION-CURVE-001", "BR-ROU-SPINNING-COPY-001",
                "BR-ROU-LOCKED-REMOVE-001", "BR-ROU-001", "BR-AUTO-START-FAIL-001", "BR-AUTO-ROU-001",
                "BR-ROU-REDUCED-MOTION-001",
            ),
            "slots": ("BR-MONEY-LABEL-001", "BR-SLOTS-PAYLINE-001", "BR-SLOT-LINE-BET-001", "BR-SLOT-ECONOMICS-001", "BR-SLOT-001"),
            "keno": ("BR-KENO-EDGE-001", "BR-KENO-001"),
        }
        # Flatten the three insertion-ordered tuples into the unchanged permanent registration stream.
        expected_ids = tuple(case_id for group_ids in expected_groups.values() for case_id in group_ids)
        # Extract only literal permanent registrations from the new owner.
        owner_ids = tuple(re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", owner_source))
        # Require exact identity and historical order without invented or duplicate cases.
        self.assertEqual(owner_ids, expected_ids)
        # Reject any remaining inline registration in the compatibility runner.
        for case_id in expected_ids:
            # Keep each permanent identity under exactly one executable source owner.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the group's exact historical position.
        self.assertEqual(runner_source.count("browser_roulette_slots_keno.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,page,base,ROOT,browser_player_id,visual_matrix,browser_save_player_game_state,roulette_i18n_failure_diagnostic,slots_engine,keno_engine,shot,viewport_shot,region_evidence,game_evidence,console_errors,page_errors,http_errors,evidence_commit,evidence_branch,screenshots)"), 1)
        # Require every parent fixture to use the server-authenticated runner identity instead of browser-global fallback state. (issue #1014)
        self.assertEqual(owner_source.count("=browser_player_id"), 5)
        # Reject the historical localStorage/default-human identity fallback from the fixture owner.
        self.assertNotIn("casino.currentPlayerId", owner_source)
        # Require one exact owner guard and one exact skip for each reduced contiguous group.
        for group_name in expected_groups:
            # Keep every producer/consumer family behind one owner decision.
            self.assertEqual(owner_source.count(f"browser_shard_owns_group('{group_name}')"), 1)
            # Advance only that group's source positions on a non-owning shard.
            self.assertEqual(owner_source.count(f"skip_browser_affinity('{group_name}')"), 1)
        # Require every reduced group to mount its canonical route before its first permanent case.
        self.assertLess(owner_source.index("page.goto(base+'/games/roulette'"), owner_source.index("run_case('BR-ROU-HITMAP-001'"))
        self.assertLess(owner_source.index("page.goto(base+'/games/slots'"), owner_source.index("run_case('BR-MONEY-LABEL-001'"))
        self.assertLess(owner_source.index("page.goto(base+'/games/keno'"), owner_source.index("run_case('BR-KENO-EDGE-001'"))
        # Import the extracted owner without starting the compatibility runner.
        from tests.cases.browser import roulette_slots_keno
        # Retain the exact skip identity emitted by a non-owning shard.
        skipped_groups = []
        # Reject any accidental case execution on a shard that owns none of the reduced groups.
        reject_case = lambda *_args: self.fail("non-owner executed a Roulette/Slots/Keno case")
        # Execute the non-owner path with every page dependency absent so setup access fails the test immediately.
        roulette_slots_keno.run_cases(reject_case, lambda group_name: False, skipped_groups.append, *([None] * 19))
        # Require one ordered skip for each exact contiguous reduced group.
        self.assertEqual(skipped_groups, ["roulette", "slots", "keno"])

    # Prove the reduced table-game and Admin affinity families share one external owner and runner delegation.
    def test_browser_bingo_admin_affinity_registration_ownership_is_exact(self):
        # Read the compatibility runner and extracted owner as inert source so this gate opens no Browser or listener.
        runner_source = self.workflow_text(BROWSER_RUNNER)
        # Read the complete final affinity owner independently of its import path.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "bingo_admin.py")
        # Bind each reduced affinity tuple while preserving the complete historical source order.
        expected_groups = {
            "table_games": ("BR-BINGO-PURCHASE-001", "BR-BINGO-001", "BR-BINGO-FORMAL-REPLAY-001", "BR-AD-FORMAL-REPLAY-001", "BR-BJ-NATURAL-PAYOUT-001", "BR-BJ-001", "BR-BJ-I18N-001", "BR-BJ-INSURANCE-NET-001", "BR-BAC-COPY-001", "BR-BAC-FRESH-SHOE-001", "BR-BAC-MUTATION-001", "BR-BAC-001", "BR-I18N-ROUTES-001", "BR-WELLNESS-001"),
            "feedback_admin": ("BR-FEEDBACK-001", "BR-ADMIN-NAV-AUTH-001", "BR-ADMIN-001", "BR-ADMIN-DIAGNOSTICS-001", "BR-ADMIN-ECONOMICS-001", "BR-ADMIN-SESSION-POLICY-001", "BR-ADMIN-LEDGER-LABELS-001", "BR-ADMIN-FEEDBACK-001", "BR-ADMIN-OAUTH-001", "BR-ADMIN-MAIL-001", "BR-INVITE-001", "BR-OPS-001"),
            "admin_presentation": ("BR-ADMIN-PRACTICE-OPPONENT-001", "BR-ADMIN-USERS-001", "BR-ADMIN-GUEST-001", "BR-AUDIO-001", "BR-I18N-FOUNDATION-001", "BR-I18N-ADMIN-001"),
        }
        # Flatten the insertion-ordered tuples into the unchanged registration stream.
        expected_ids = tuple(case_id for group_ids in expected_groups.values() for case_id in group_ids)
        # Extract only literal permanent registrations from the new owner.
        owner_ids = tuple(re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", owner_source))
        # Require exact identity and historical order without invented or duplicate cases.
        self.assertEqual(owner_ids, expected_ids)
        # Reject any remaining inline registration in the compatibility runner.
        for case_id in expected_ids:
            # Keep each permanent identity under exactly one executable source owner.
            self.assertNotRegex(runner_source, rf"\brun_case\(\s*['\"]{re.escape(case_id)}['\"]")
        # Require one delegation at the group's exact historical position.
        self.assertEqual(runner_source.count("browser_bingo_admin.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,page,base,ROOT,casino_config.DATA_DIR,browser_player_id,visual_matrix,browser_save_player_game_state,blackjack_engine,wait_for_bingo_terminal_render,require_bingo_terminal_auto_payload,require_bingo_terminal_reload_payload,guest_analytics,prepare_admin_feedback_draft,save_admin_feedback_triage,collect_normal_admin_navigation,assert_route_i18n,auth_core,DEFAULT_AUTH_EMAIL,DEFAULT_AUTH_PASSWORD,EXPECTED_MODULE_ROWS,VERSION_MANIFEST,read_i18n_json,browser_write_json,shot,region_evidence,game_evidence,console_errors,page_errors,http_errors,screenshots)"), 1)
        # Require Operations degradation to target the invocation-scoped provider root instead of checkout data. (issue #1014)
        self.assertIn("players_path=browser_data_dir/'players.json'", owner_source)
        # Reject the historical checkout-relative fixture mutation from the extracted owner.
        self.assertNotIn("ROOT/'data'/'players.json'", owner_source)
        # Require one exact owner decision and one exact skip for every reduced contiguous family.
        for group_name in expected_groups:
            # Resolve ownership once before any setup can mutate browser state.
            self.assertEqual(owner_source.count(f"browser_shard_owns_group('{group_name}')"), 1)
            # Advance only the named family on non-owning shards.
            self.assertEqual(owner_source.count(f"skip_browser_affinity('{group_name}')"), 1)
        # Require each owner to establish its canonical independent starting state before its first case.
        self.assertLess(owner_source.index("page.get_by_test_id('nav-bingo').click()"), owner_source.index("run_case('BR-BINGO-PURCHASE-001'"))
        self.assertLess(owner_source.index("feedback_login=page.request.post"), owner_source.index("run_case('BR-FEEDBACK-001'"))
        self.assertLess(owner_source.index("presentation_login=page.request.post"), owner_source.index("run_case('BR-ADMIN-PRACTICE-OPPONENT-001'"))
        # Import the extracted owner without starting the compatibility runner.
        from tests.cases.browser import bingo_admin
        # Retain the exact skip identity emitted by a non-owning shard.
        skipped_groups = []
        # Reject any accidental case execution on a shard that does not own the complete group.
        reject_case = lambda *_args: self.fail("non-owner executed a Bingo/Admin case")
        # Execute the non-owner path with every page dependency absent so setup access fails the test immediately.
        bingo_admin.run_cases(reject_case, lambda group_name: False, skipped_groups.append, *([None] * 30))
        # Require one ordered skip for each exact contiguous reduced family.
        self.assertEqual(skipped_groups, ["table_games", "feedback_admin", "admin_presentation"])

    # Prove declared producer/consumer groups fit one deterministic shard and guard their bodies.
    def test_browser_shard_affinity_groups_are_contiguous_and_guarded(self):
        # Parse the exact browser runner source without importing it.
        source, tree = self.browser_runner_syntax()
        # Select the one browser runner function that owns all permanent BR cases.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Import the listener-free runner module so the test uses its exact reviewed packer.
        from tests import runner as browser_runner_module
        # Discover inline and extracted permanent IDs at their exact cross-file source positions.
        case_ids = browser_runner_module.browser_case_ids()
        # Bind the complete inventory after adding the Acey-Deucey formal lifecycle regression. (TEST-092)
        self.assertEqual(len(case_ids), 133)
        # Read the first extracted Browser affinity owner for guard-location checks below.
        auth_backend_pwa_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "auth_backend_pwa.py")
        # Read the extracted disposable guest-lifecycle owner for guard-location checks below.
        guest_lifecycle_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "guest_lifecycle.py")
        # Read the extracted auth/lobby owner for guard-location checks below.
        auth_lobby_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "auth_lobby.py")
        # Read the extracted Roulette/Slots/Keno owner for guard-location checks below.
        roulette_slots_keno_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "roulette_slots_keno.py")
        # Read the extracted Bingo-through-Admin owner for guard-location checks below.
        bingo_admin_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "bingo_admin.py")
        # Parse the extracted game-family owner so its Keno integrity callbacks remain structurally inspected.
        roulette_slots_keno_tree = ast.parse(roulette_slots_keno_source)
        # Compute the same deterministic six-runner partition used by the workflow.
        shard_sets = browser_runner_module.browser_shard_case_sets(6)
        # Recompute from identical inputs to prove packing replay is deterministic.
        replayed_shard_sets = browser_runner_module.browser_shard_case_sets(6)
        # Require exact ordered ownership equality across repeated packing.
        self.assertEqual(replayed_shard_sets, shard_sets)
        # Require every approved ordinary runner to own at least one case.
        self.assertTrue(all(shard_sets))
        # Load the reviewed profile through the production strict validator.
        durations = browser_runner_module.browser_case_durations()
        # Apply the production median rule for any future unmeasured literal case.
        default_duration = sorted(durations.values())[len(durations) // 2] if durations else 1
        # Compute each ordered shard's reviewed aggregate weight.
        shard_loads = tuple(sum(durations.get(case_id, default_duration) for case_id in shard_cases) for shard_cases in shard_sets)
        # Bind deterministic load totals after packing the three formal lifecycle regressions. (TEST-092, TEST-242)
        self.assertEqual(shard_loads, (228, 226, 227, 226, 226, 227))
        # Reject a degenerate or materially imbalanced assignment even if union remains exact.
        self.assertLessEqual(max(shard_loads) - min(shard_loads), 3)
        # Prove additional runners now reduce the reviewed full-run floor beyond six shards.
        seven_shard_loads=tuple(sum(durations.get(case_id,default_duration) for case_id in shard_cases) for shard_cases in browser_runner_module.browser_shard_case_sets(7))
        # Require seven runners to improve on six and eight runners to cross below the former 178-second floor.
        eight_shard_loads=tuple(sum(durations.get(case_id,default_duration) for case_id in shard_cases) for shard_cases in browser_runner_module.browser_shard_case_sets(8))
        # Pin both monotonic improvement and the issue's concrete floor-breaking outcome.
        self.assertLess(max(seven_shard_loads),max(shard_loads)); self.assertLess(max(eight_shard_loads),178)
        # Require exact union and nonduplication across all declared owners.
        self.assertEqual(sorted(case_id for shard_cases in shard_sets for case_id in shard_cases), sorted(case_ids))
        # Locate the one permanent Keno owner call that carries both edge and economics acceptance.
        keno_owner_call = next(node for node in ast.walk(roulette_slots_keno_tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_case" and ast.literal_eval(node.args[0]) == "BR-KENO-EDGE-001")
        # Read the owner call's permanent requirement mapping without executing Browser code.
        keno_owner_requirements = ast.literal_eval(keno_owner_call.args[1])
        # Require the combined owner to map both the Keno economics requirement and its test requirement.
        self.assertTrue({"KENO-027", "TEST-147"}.issubset(set(keno_owner_requirements)))
        # Require the combined owner to invoke the named complete-acceptance callback.
        self.assertIsInstance(keno_owner_call.args[2], ast.Name)
        # Pin the callback identity so a later refactor cannot silently drop either economics body.
        self.assertEqual(keno_owner_call.args[2].id, "keno_complete_acceptance")
        # Locate the one permanent semantic game-color Browser owner.
        color_owner_call = next(node for node in ast.walk(runner) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_case" and ast.literal_eval(node.args[0]) == "BR-GAME-COLOR-001")
        # Require the new Browser owner to map only its authorized product and test requirements.
        self.assertEqual(ast.literal_eval(color_owner_call.args[1]), ["UX-024", "TEST-149"])
        # Require the owner to invoke the complete named 32-cell callback.
        self.assertIsInstance(color_owner_call.args[2], ast.Name)
        # Pin the callback identity so the evidence body cannot be replaced by a shallow predicate.
        self.assertEqual(color_owner_call.args[2].id, "semantic_game_colors")
        # Locate the complete callback inside its extracted Browser owner.
        keno_complete_callback = next(node for node in ast.walk(roulette_slots_keno_tree) if isinstance(node, ast.FunctionDef) and node.name == "keno_complete_acceptance")
        # Read every direct helper call from the complete callback in source order.
        keno_complete_calls = [statement.value.func.id for statement in keno_complete_callback.body if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Name)]
        # Require one complete 64-cell matrix pass followed by one route/restoration economics pass.
        self.assertEqual(keno_complete_calls, ["keno_edge_containment", "keno_economics_route_behavior"])
        # Parse the extracted shard policy where ownership data now lives. (TEST-242)
        _sharding_source, sharding_tree = self.browser_sharding_syntax()
        # Locate the literal affinity declaration at extracted module scope.
        affinity_node = next(node for node in sharding_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "BROWSER_CASE_AFFINITY_GROUPS" for target in node.targets))
        # Read only literal strings and tuples from the tracked declaration.
        affinity_groups = ast.literal_eval(affinity_node.value)
        # Require every producer/consumer group introduced by the controller repair.
        self.assertEqual(set(affinity_groups), {"auth_backend_pwa", "guest_lifecycle", "auth_public", "auth_session", "lobby_shell", "roulette", "slots", "keno", "table_games", "feedback_admin", "admin_presentation"})
        # Locate the reviewed game-to-affinity declaration used only for detector-scoped Browser runs. (issue #1014)
        game_affinity_node = next(node for node in sharding_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "BROWSER_GAME_AFFINITY_GROUPS" for target in node.targets))
        # Require only complete single-game Roulette, Slots, and Keno families to be detector-selectable.
        self.assertEqual(ast.literal_eval(game_affinity_node.value), {"roulette": "roulette", "slots": "slots", "keno": "keno"})
        # Keep the independent semantic-color matrix outside every legacy producer/consumer affinity group.
        self.assertNotIn("BR-GAME-COLOR-001", {case_id for group_case_ids in affinity_groups.values() for case_id in group_case_ids})
        # Validate every group against exact case identity and one-shard ownership.
        for group_name, group_case_ids in affinity_groups.items():
            # Reject a misspelled, duplicated, or removed permanent case.
            self.assertEqual(len(group_case_ids), len(set(group_case_ids)), group_name)
            # Resolve exact source positions for every group member.
            positions = [case_ids.index(case_id) for case_id in group_case_ids]
            # Require one contiguous source range so bulk skip accounting cannot hide unrelated cases.
            self.assertEqual(positions, list(range(positions[0], positions[0] + len(positions))), group_name)
            # Resolve the deterministic packed owner of each grouped case.
            owners = {index for index, shard_cases in enumerate(shard_sets) for case_id in group_case_ids if case_id in shard_cases}
            # Require all producers and consumers to execute on one shard.
            self.assertEqual(len(owners), 1, group_name)
            # Extracted Browser affinities own their guard and skip outside the compatibility runner.
            if group_name in {"auth_backend_pwa", "guest_lifecycle", "auth_public", "auth_session", "lobby_shell", "roulette", "slots", "keno", "table_games", "feedback_admin", "admin_presentation"}:
                # Bind the exact source-level delegation alias and external owner for this family.
                delegation_alias, owner_source = {
                    "auth_backend_pwa": ("browser_auth_backend_pwa", auth_backend_pwa_source),
                    "guest_lifecycle": ("browser_guest_lifecycle", guest_lifecycle_source),
                    "auth_public": ("browser_auth_lobby", auth_lobby_source),
                    "auth_session": ("browser_auth_lobby", auth_lobby_source),
                    "lobby_shell": ("browser_auth_lobby", auth_lobby_source),
                    "roulette": ("browser_roulette_slots_keno", roulette_slots_keno_source),
                    "slots": ("browser_roulette_slots_keno", roulette_slots_keno_source),
                    "keno": ("browser_roulette_slots_keno", roulette_slots_keno_source),
                    "table_games": ("browser_bingo_admin", bingo_admin_source),
                    "feedback_admin": ("browser_bingo_admin", bingo_admin_source),
                    "admin_presentation": ("browser_bingo_admin", bingo_admin_source),
                }[group_name]
                # Require one source-level delegation so cross-file discovery preserves the group's exact position.
                self.assertEqual(source.count(f"{delegation_alias}.run_cases("), 1)
                # Require the extracted owner to resolve this group exactly once before its guarded body.
                self.assertEqual(owner_source.count(f"browser_shard_owns_group('{group_name}')"),1)
                # Require non-owning shards to advance the complete family atomically.
                self.assertIn(f"skip_browser_affinity('{group_name}')", owner_source)
            # Guarded bulk ranges require both an execution guard and explicit unowned accounting.
            else:
                # Require the complete inline body to sit beneath its declared group owner.
                self.assertIn(f"if browser_shard_owns_group('{group_name}'):", source)
                # Require unowned guarded bodies to advance their exact literal positions.
                self.assertIn(f"skip_browser_affinity('{group_name}')", source)

    # Prove hostile duration profile values fail with one fixed diagnostic and no mutation.
    def test_browser_duration_profile_is_strict_bounded_and_value_free(self):
        # Import the listener-free runner module without starting Browser or a server.
        from tests import runner as browser_runner_module
        # Preserve the tracked path and shared runner state across isolated hostile inputs.
        original_path = browser_runner_module.BROWSER_DURATION_PROFILE_PATH
        # Snapshot mutable globals that strict profile reads must never change.
        original_results = list(browser_runner_module.RESULTS)
        # Build exact hostile JSON bytes, including an integer too large for float coercion.
        hostile_payloads = (
            b'{"BR-AB-001": true}',
            ('{"BR-AB-001": %s}' % (10 ** 400)).encode("ascii"),
            b'{"BR-AB-001": NaN}',
            b'{"BR-AB-001": Infinity}',
            b'{"BR-AB-001": 0}',
            b'{"BR-AB-001": 3601}',
            b'{"BR-AB-001": "12"}',
            b'{"BR-AB-001": 12, "BR-AB-001": 13}',
            b'{"BR-NOT-A-CASE": 12}',
            b'[',
        )
        # Guarantee shared module restoration even if one hostile assertion fails.
        try:
            # Use one disposable path so tracked profile bytes remain untouched.
            with tempfile.TemporaryDirectory() as temp_dir:
                # Point the strict loader at a task-local synthetic profile.
                profile_path = Path(temp_dir) / "browser_case_durations.json"
                # Route every isolated call to the disposable profile.
                browser_runner_module.BROWSER_DURATION_PROFILE_PATH = profile_path
                # Exercise every malformed or hostile value independently.
                for payload in hostile_payloads:
                    # Persist the exact hostile bytes for this read.
                    profile_path.write_bytes(payload)
                    # Require the one fixed value-free failure, including for the huge integer.
                    with self.assertRaisesRegex(AssertionError, "^browser duration profile is invalid$") as raised:
                        # Invoke the production strict profile reader directly.
                        browser_runner_module.browser_case_durations()
                    # Require dynamic parser or filesystem causes to remain suppressed.
                    self.assertIsNone(raised.exception.__cause__)
                    # Prove a rejected read preserved the exact hostile bytes.
                    self.assertEqual(profile_path.read_bytes(), payload)
                    # Prove no result evidence was mutated by a rejected read.
                    self.assertEqual(browser_runner_module.RESULTS, original_results)
                # Build a syntactically oversized payload before any JSON parse.
                oversized = b" " * (browser_runner_module.BROWSER_DURATION_PROFILE_MAX_BYTES + 1)
                # Persist the exact oversized bytes.
                profile_path.write_bytes(oversized)
                # Require the same fixed value-free failure.
                with self.assertRaisesRegex(AssertionError, "^browser duration profile is invalid$") as raised:
                    # Invoke the production strict profile reader.
                    browser_runner_module.browser_case_durations()
                # Require no dynamic exception cause for oversized input either.
                self.assertIsNone(raised.exception.__cause__)
                # Prove oversized input remains byte-identical.
                self.assertEqual(profile_path.read_bytes(), oversized)
        # Restore the tracked path before any later test can import this shared module.
        finally:
            # Rebind the exact original tracked profile path.
            browser_runner_module.BROWSER_DURATION_PROFILE_PATH = original_path

    # Prove the regeneration tool rejects hostile measurements before changing its profile.
    def test_browser_duration_generator_rejects_hostile_measurements_atomically(self):
        # Resolve the reviewed generator source inside the approved tooling path.
        generator_path = ROOT / "scripts" / "generate_browser_durations.py"
        # Build an isolated module spec without invoking the CLI writer.
        spec = importlib.util.spec_from_file_location("browser_duration_generator_test", generator_path)
        # Require the exact tracked module to be importable.
        self.assertIsNotNone(spec)
        # Create the isolated module object.
        generator = importlib.util.module_from_spec(spec)
        # Execute only the generator definitions.
        spec.loader.exec_module(generator)
        # Use disposable profile and evidence paths so the tracked file cannot change.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Point the module at a valid one-row synthetic profile.
            profile_path = Path(temp_dir) / "browser_case_durations.json"
            # Seed one exact reviewed weight.
            profile_path.write_text('{"BR-AB-001": 13}\n', encoding="utf-8")
            # Replace only this imported module's tracked output path.
            generator.PROFILE_PATH = profile_path
            # Create a disposable shard evidence directory.
            evidence_dir = Path(temp_dir) / "evidence"
            # Materialize the directory before writing one artifact.
            evidence_dir.mkdir()
            # Bind one hostile huge integer measurement to a known Browser case.
            hostile = '{"results":[{"test_id":"BR-AB-001","duration_seconds":%s}]}' % (10 ** 400)
            # Persist the hostile shard artifact.
            (evidence_dir / f"browser_results_shard_0_of_{BROWSER_SHARD_COUNT}.json").write_text(hostile, encoding="utf-8")
            # Capture the exact profile bytes before validation.
            before = profile_path.read_bytes()
            # Require the fixed value-free evidence error without OverflowError.
            with self.assertRaisesRegex(ValueError, "^browser duration evidence is invalid$"):
                # Validate and collect without opening the tracked output.
                generator.collect(evidence_dir)
            # Prove the hostile measurement did not change the profile.
            self.assertEqual(profile_path.read_bytes(), before)

    # Prove duration evidence is additive only to active Browser result rows.
    def test_browser_duration_publication_preserves_other_result_schemas(self):
        # Import the shared listener-free runner helpers without starting a server.
        from tests import runner as browser_runner_module
        # Preserve every shared runner global this focused test changes.
        original_results = browser_runner_module.RESULTS
        # Preserve the active reporter exactly.
        original_progress = browser_runner_module.ACTIVE_PROGRESS
        # Preserve packed shard ownership exactly.
        original_shard_cases = browser_runner_module.BROWSER_SHARD_CASES
        # Preserve affected-game filtering exactly.
        original_affected_games = browser_runner_module.BROWSER_AFFECTED_GAMES
        # Preserve source-order accounting exactly.
        original_sequence = browser_runner_module.BROWSER_CASE_SEQ

        # Provide the minimal Browser reporter surface used by run_case.
        class FakeBrowserProgress:
            # Accept one case-start notification without side effects.
            def start_item(self, _test_id):
                # Return no value just like the production reporter.
                return None

            # Accept one terminal notification without side effects.
            def finish_item(self, _status):
                # Return no value just like the production reporter.
                return None

        # Raise one fixed live Browser failure for FAIL timing coverage.
        def failing_case():
            # Exercise the raising case-body branch.
            raise RuntimeError("browser failure")

        # Guarantee every shared global is restored even if an assertion fails.
        try:
            # Isolate result collection from the imported runner's prior evidence.
            browser_runner_module.RESULTS = []
            # Disable Browser instrumentation for an ordinary shared run_case call.
            browser_runner_module.ACTIVE_PROGRESS = None
            # Disable packed ownership and affected-game filtering.
            browser_runner_module.BROWSER_SHARD_CASES = None
            # Keep all cases selected.
            browser_runner_module.BROWSER_AFFECTED_GAMES = None
            # Execute one ordinary non-Browser case.
            browser_runner_module.run_case("UNIT-DURATION-SHAPE", ["TEST-002"], lambda: True)
            # Require the exact historical row schema with no duration field.
            self.assertEqual(browser_runner_module.RESULTS, [{"test_id": "UNIT-DURATION-SHAPE", "requirements": ["TEST-002"], "status": "PASS", "message": ""}])
            # Reset only the isolated result list before Browser branch coverage.
            browser_runner_module.RESULTS = []
            # Activate the Browser reporter context that authorizes duration evidence.
            browser_runner_module.ACTIVE_PROGRESS = FakeBrowserProgress()
            # Exercise one passing Browser case.
            browser_runner_module.run_case("BR-DURATION-PASS", ["TEST-010"], lambda: True)
            # Exercise one raising Browser case.
            with self.assertRaisesRegex(RuntimeError, "^browser failure$"):
                # Run the fixed failing body.
                browser_runner_module.run_case("BR-DURATION-FAIL", ["TEST-010"], failing_case)
            # Exercise one predicate-failure Browser case.
            with self.assertRaisesRegex(AssertionError, "case predicate returned False"):
                # Return False so run_case owns the failure record.
                browser_runner_module.run_case("BR-DURATION-PREDICATE", ["TEST-010"], lambda: False)
            # Require timing on PASS, raising FAIL, and predicate FAIL rows.
            self.assertEqual([row["test_id"] for row in browser_runner_module.RESULTS], ["BR-DURATION-PASS", "BR-DURATION-FAIL", "BR-DURATION-PREDICATE"])
            # Inspect every Browser row's bounded numeric measurement.
            for row in browser_runner_module.RESULTS:
                # Require a non-boolean integer or float duration.
                self.assertIn(type(row.get("duration_seconds")), (int, float))
                # Require the emitted duration to stay within the governed Browser bound.
                self.assertGreaterEqual(row["duration_seconds"], 0)
                # Require the emitted duration to stay within the existing suite timeout budget.
                self.assertLessEqual(row["duration_seconds"], browser_runner_module.BROWSER_DURATION_MAX_SECONDS)
        # Restore the shared runner exactly for every later focused test.
        finally:
            # Restore the original result-list identity.
            browser_runner_module.RESULTS = original_results
            # Restore the original reporter.
            browser_runner_module.ACTIVE_PROGRESS = original_progress
            # Restore the original packed ownership.
            browser_runner_module.BROWSER_SHARD_CASES = original_shard_cases
            # Restore the original affected-game selection.
            browser_runner_module.BROWSER_AFFECTED_GAMES = original_affected_games
            # Restore the original source-order position.
            browser_runner_module.BROWSER_CASE_SEQ = original_sequence

    # Prove inline assertions cannot execute outside an owning shard or callback.
    def test_browser_inline_assertions_are_affinity_owned(self):
        # Parse exact browser source and retain text for ancestor inspection.
        source, tree = self.browser_runner_syntax()
        # Select the browser runner whose nested callbacks are isolated by run_case.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Build parent links for precise callback and guard ancestry.
        parents = {}
        # Visit every syntax node inside the browser runner.
        for node in ast.walk(runner):
            # Link every direct child back to its parent.
            for child in ast.iter_child_nodes(node):
                # Retain the unique syntax parent for upward ownership checks.
                parents[child] = node
        # Inspect every assertion that can execute directly in run_browser_tests.
        for assertion in (node for node in ast.walk(runner) if isinstance(node, ast.Assert)):
            # Walk upward until the browser runner or a nested callback is reached.
            ancestor = parents.get(assertion)
            # Track whether a declared owner guard or owner-conditioned loop dominates the assertion.
            owned = False
            # Inspect every syntax ancestor of this assertion.
            while ancestor is not None and ancestor is not runner:
                # Assertions inside a nested callback execute only through their owning run_case.
                if isinstance(ancestor, (ast.FunctionDef, ast.Lambda)):
                    # Mark callback-owned assertions as structurally isolated.
                    owned = True
                    # Stop because outer source placement cannot execute the callback body.
                    break
                # Treat declared group guards and owner-conditioned guest loops as explicit affinity.
                if isinstance(ancestor, (ast.If, ast.For)) and "browser_shard_owns_group" in (ast.get_source_segment(source, ancestor.test if isinstance(ancestor, ast.If) else ancestor.iter) or ""):
                    # Mark this inline assertion as affinity-owned.
                    owned = True
                    # Stop after finding the nearest valid ownership boundary.
                    break
                # Continue toward the browser runner.
                ancestor = parents.get(ancestor)
            # Reject the original line-7010 failure class and any future unowned inline assertion.
            self.assertTrue(owned, f"unowned inline browser assertion at line {assertion.lineno}")

    # Prove PWA browser acceptance follows current module metadata rather than a stale release literal.
    def test_browser_pwa_assertions_use_current_packaged_version(self):
        # Read exact runner source and isolate the browser function.
        source, tree = self.browser_runner_syntax()
        # Select the one browser runner function.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Read only the browser function's source for stale identity checks.
        runner_source = ast.get_source_segment(source, runner)
        # Read the extracted PWA affinity owner whose assertions now consume the runner-provided version.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "auth_backend_pwa.py")
        # Combine the delegation owner and its extracted body for stale-literal inspection.
        complete_source = runner_source + owner_source
        # Require canonical module metadata to provide the acceptance identity.
        self.assertIn("packaged_version=json.loads((ROOT/'modules'/'module-manifest.json')", runner_source)
        # Require service-worker registration and page identity checks to use that value.
        self.assertIn("f'{base}/sw.js?v={packaged_version}'", complete_source)
        # Reject any hard-coded packaged release in worker query strings or page-version assertions.
        self.assertIsNone(re.search(r"sw\.js\?v=\d+\.\d+\.\d+", complete_source))
        # Reject the stale equality form that previously required manual release edits.
        self.assertIsNone(re.search(r"CasinoPwa\?\.version===['\"]\d+\.\d+\.\d+", complete_source))

    # Prove isolated route-i18n coverage produces every state-dependent interpolation it consumes.
    def test_browser_route_i18n_declares_visible_state_producers(self):
        # Read exact runner source without importing Playwright.
        source, tree = self.browser_runner_syntax()
        # Select the browser runner and isolate its source.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Read the complete browser function for declared-driver inspection.
        runner_source = ast.get_source_segment(source, runner)
        # Read the extracted shared-shell and Admin owner that contains the route interpolation producers.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "bingo_admin.py")
        # Combine runner delegation and owner source so every reviewed producer remains visible to policy.
        complete_source = runner_source + owner_source
        # Require the Slots history interpolation to own one visible spin producer.
        self.assertIn("'games/slots':drive_slots_interpolation", complete_source)
        # Require the Keno final-draw interpolation to own one visible draw producer.
        self.assertIn("'games/keno':drive_keno_interpolation", complete_source)
        # Require every route-specific producer to execute after mount and before audit.
        self.assertIn("if interpolation_driver: interpolation_driver()", complete_source)
        # Require state production to use only current player-visible action controls.
        self.assertIn("page.get_by_test_id('slots-spin').click()", complete_source)
        # Require the Keno driver to use the real draw action rather than a hidden API shortcut.
        self.assertIn("page.get_by_test_id('keno-draw').click()", complete_source)

    # Prove expected normal-role denials cannot poison the final browser-error invariant.
    def test_browser_admin_affinity_clears_only_expected_denial_observations(self):
        # Read the extracted Admin owner without importing its Browser runtime.
        owner_source = self.workflow_text(ROOT / "tests" / "cases" / "browser" / "bingo_admin.py")
        # Locate the normal-role authorization producer on the Admin-owned shard.
        producer_index = owner_source.index("normal_admin_navigation=collect_normal_admin_navigation()")
        # Locate the bounded expected-denial cleanup after that producer.
        cleanup_index = owner_source.index("console_errors.clear(); http_errors.clear()", producer_index)
        # Locate Admin login after the normal-role denial evidence is retained.
        admin_login_index = owner_source.index("admin_browser_login=page.request.post", producer_index)
        # Require expected 403 observations to clear only after collection and before Admin activity.
        self.assertLess(producer_index, cleanup_index)
        # Preserve final invariant signal for every unexpected Admin-side browser failure.
        self.assertLess(cleanup_index, admin_login_index)

    # Prove changed-file routing restricts only unambiguous game-owned changes and fails closed otherwise.
    def test_browser_affected_game_detector_is_conservative(self):
        # Execute the dependency-free detector CLI with one changed-path packet.
        def detect(paths):
            # Send newline-delimited repository paths exactly as the workflow does.
            result = subprocess.run([sys.executable, str(AFFECTED_BROWSER_GAMES)], input="\n".join(paths), text=True, capture_output=True, cwd=ROOT, check=False)
            # Require detector execution itself to remain healthy.
            self.assertEqual(result.returncode, 0, result.stderr)
            # Return the single documented routing token.
            return result.stdout.strip()
        # Restrict one unambiguous game-owned change to that game.
        self.assertEqual(detect(["casino/games/craps/engine.py"]), "craps")
        # Sort multiple unambiguous game owners deterministically.
        self.assertEqual(detect(["web/games/slots.js", "tests/games/craps/test_api.py"]), "craps,slots")
        # Force full coverage for shared runtime code.
        self.assertEqual(detect(["web/core/api.js"]), "FULL")
        # Force full coverage for a path that resembles a game but is absent from the catalog.
        self.assertEqual(detect(["casino/games/not_a_catalog_game/api.py"]), "FULL")
        # Report no browser-relevant ownership for game documentation and retained evidence only.
        self.assertEqual(detect(["docs/games/craps.md", "docs/evidence/craps/current.json"]), "NONE")

    # Prove pull requests may select affected cases while main, manual, and ambiguous work remain complete.
    def test_browser_workflow_routes_prs_and_preserves_full_coverage(self):
        # Read the complete workflow as inert policy text.
        workflow_text = self.workflow_text(BROWSER_WORKFLOW)
        # Require protected-main pushes to run the complete detector-to-aggregate path.
        self.assertIn("push:\n    branches:\n      - main", workflow_text)
        # Require pull-request game detection and the explicit full-suite label.
        self.assertIn("gh api --paginate", workflow_text)
        self.assertIn("'full-browser'", workflow_text)
        # Require non-pull-request events to resolve to full coverage.
        self.assertIn('if [ "${IS_PR}" != "true" ]', workflow_text)
        # Require each shard to consume the detector-owned game selection.
        self.assertIn("${{ needs.detect_affected_games.outputs.games_arg }}", workflow_text)
        # Require the historical aggregate to depend on both detection and shard execution.
        self.assertIn("      - detect_affected_games\n      - browser_tests_shard", workflow_text)
        # Require the aggregate to fail when detection fails even if shard artifacts exist.
        self.assertIn('test "${{ needs.detect_affected_games.result }}" = "success"', workflow_text)
        # Preserve every separately authorized formal profile.
        self.assertIn("formal_ui_50000:", workflow_text)
        self.assertIn("baccarat_sustained_2000:", workflow_text)
        self.assertIn("concurrent_browser_138:", workflow_text)

    # Prove explicit detector selection controls aggregate coverage and cannot be forged by shard artifacts.
    def test_browser_aggregate_verifies_detector_owned_selection(self):
        # Import the listener-free runner module so source discovery and synthetic declarations match real packing.
        from tests import runner as browser_runner_module
        # Expand the permanent Browser inventory across the runner and reviewed area owners.
        case_ids = browser_runner_module.browser_case_ids()
        # Parse the extracted shard policy where affected-game ownership now lives. (TEST-242)
        _sharding_source, sharding_tree = self.browser_sharding_syntax()
        # Locate the literal affected-game acceptance map in the pure policy module.
        mapping_node = next(node for node in sharding_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "BROWSER_GAME_ACCEPTANCE_CASES" for target in node.targets))
        # Read only the literal game-to-case mapping.
        game_cases = ast.literal_eval(mapping_node.value)
        # Derive exact selection through the production classifier so game-owned affinity families cannot drift from the aggregate oracle.
        expected = browser_runner_module.browser_expected_case_ids({"acey_deucey"})
        # Require the selected game's dedicated case to remain present.
        self.assertIn(game_cases["acey_deucey"], expected)
        # Require every unselected Roulette, Slots, and Keno affinity member to be absent atomically.
        self.assertFalse(set(expected) & {case_id for group_name in ("roulette", "slots", "keno") for case_id in browser_runner_module.BROWSER_CASE_AFFINITY_GROUPS[group_name]})
        # Compute the exact governed ownership declarations from the sole test oracle.
        shard_sets = browser_runner_module.browser_shard_case_sets(BROWSER_SHARD_COUNT)
        # Create one disposable complete-shard result packet.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write each deterministic packed shard result with an exact self-description.
            for index, owned_set in enumerate(shard_sets):
                # Sort the governed ownership exactly as the real runner writes it.
                owned = sorted(owned_set)
                # Build passing evidence for owned cases that survive detector selection.
                results = [{"test_id": case_id, "status": "PASS"} for case_id in owned if case_id in set(expected)]
                # Bind worker identity, detector selection, and exact ownership beside its results.
                payload = {"shard_index": index, "shard_count": BROWSER_SHARD_COUNT, "affected_games": ["acey_deucey"], "owned_cases": owned, "results": results}
                # Write the exact filename consumed by the aggregate verifier.
                (Path(temp_dir) / f"browser_results_shard_{index}_of_{BROWSER_SHARD_COUNT}.json").write_text(json.dumps(payload), encoding="utf-8")
            # Run the real aggregate CLI without invoking a browser or listener.
            verified = subprocess.run([sys.executable, str(TEST_ENTRYPOINT), "--verify-browser-shards", temp_dir, "--shard-count", str(BROWSER_SHARD_COUNT), "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require exact selected-case coverage to pass.
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            # Forge one shard's declaration while keeping all case rows unchanged.
            forged_path = Path(temp_dir) / f"browser_results_shard_0_of_{BROWSER_SHARD_COUNT}.json"
            # Read the existing evidence before changing only its self-description.
            forged = json.loads(forged_path.read_text(encoding="utf-8"))
            # Claim a different detector selection to simulate an untrusted artifact.
            forged["affected_games"] = ["craps"]
            # Persist the forged declaration for the negative regression.
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            # Re-run the real aggregate verifier against the same expected detector input.
            rejected = subprocess.run([sys.executable, str(TEST_ENTRYPOINT), "--verify-browser-shards", temp_dir, "--shard-count", str(BROWSER_SHARD_COUNT), "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require the forged shard selection to fail closed.
            self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
            # Retain a focused diagnostic proving the expected-selection mismatch was detected.
            self.assertIn("affected games", rejected.stdout)
            # Restore the exact detector selection before forging only ownership.
            forged["affected_games"] = ["acey_deucey"]
            # Remove one governed case while keeping the declaration otherwise well formed.
            forged["owned_cases"] = forged["owned_cases"][1:]
            # Persist the missing-owner forgery.
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            # Re-run the real aggregate verifier against the incomplete declaration.
            missing_owner = subprocess.run([sys.executable, str(TEST_ENTRYPOINT), "--verify-browser-shards", temp_dir, "--shard-count", str(BROWSER_SHARD_COUNT), "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require each shard's exact owned_cases declaration, not merely result union.
            self.assertNotEqual(missing_owner.returncode, 0, missing_owner.stdout + missing_owner.stderr)
            # Pin the bounded ownership diagnostic.
            self.assertIn("owned_cases mismatch", missing_owner.stdout)
            # Duplicate one remaining owned id to test declaration-level nonduplication.
            forged["owned_cases"] = sorted(shard_sets[0]) + [sorted(shard_sets[0])[0]]
            # Persist the duplicate-owner forgery.
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            # Re-run aggregate verification against the duplicated declaration.
            duplicate_owner = subprocess.run([sys.executable, str(TEST_ENTRYPOINT), "--verify-browser-shards", temp_dir, "--shard-count", str(BROWSER_SHARD_COUNT), "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require duplicate ownership to fail closed.
            self.assertNotEqual(duplicate_owner.returncode, 0, duplicate_owner.stdout + duplicate_owner.stderr)
            # Pin the fixed declaration diagnostic.
            self.assertIn("invalid owned_cases", duplicate_owner.stdout)

    # Prove a single affected game skips every unselected single-game affinity family before setup executes. (issue #1014)
    def test_affected_game_selection_skips_complete_game_affinities(self):
        # Import the listener-free runner so production discovery and selection stay single-sourced.
        from tests import runner as browser_runner_module
        # Select Big Six Wheel exactly like the affected-game workflow argument.
        selected = browser_runner_module.browser_expected_case_ids({"big_six_wheel"})
        # Require the dedicated Big Six case and a common security case to remain selected.
        self.assertIn("BR-BIG-SIX-001", selected)
        # Require shared cross-game qualification to remain present rather than over-filtering the suite.
        self.assertIn("BR-SEC-PREVIEW-001", selected)
        # Inspect each reviewed single-game stateful family independently.
        for group_name in ("roulette", "slots", "keno"):
            # Require the complete family to be absent, never only one producer or consumer.
            self.assertFalse(set(selected) & set(browser_runner_module.BROWSER_CASE_AFFINITY_GROUPS[group_name]), group_name)
            # Require the guarded owner predicate to report deselection before any setup body can execute.
            original_games = browser_runner_module.BROWSER_AFFECTED_GAMES
            # Preserve shared runner state even when one group assertion fails.
            try:
                # Install the exact detector-owned game set used by this proof.
                browser_runner_module.BROWSER_AFFECTED_GAMES = {"big_six_wheel"}
                # Require the complete guarded owner to take its skip path.
                self.assertFalse(browser_runner_module.browser_shard_owns_group(group_name), group_name)
            # Restore the imported runner's global selection for every later test.
            finally:
                # Rebind the exact prior selection object.
                browser_runner_module.BROWSER_AFFECTED_GAMES = original_games

    # Prove ordinary sharding does not alter formal 50k or sustained Baccarat governance.
    def test_browser_sharding_preserves_formal_and_baccarat_jobs(self):
        # Read the complete workflow as inert text.
        workflow_text = self.workflow_text(BROWSER_WORKFLOW)
        # Require exact aggregate result accounting through the historical branch-protection context.
        self.assertIn("      - browser_tests_shard", workflow_text)
        # Preserve the explicit formal 50,000-cycle authorization input and exact aggregate.
        self.assertIn("formal_ui_50000:", workflow_text)
        # Preserve the exact formal cycle count and source-commit-bound aggregate.
        self.assertIn("--total-cycles 50000", workflow_text)
        # Preserve the separately authorized sustained Baccarat input and exact runner.
        self.assertIn("baccarat_sustained_2000:", workflow_text)
        # Require the focused Baccarat command to remain independent of ordinary shard execution.
        self.assertIn("python -m tests.baccarat_sustained", workflow_text)

    # Prove one canonical test constant is the sole reviewed alignment boundary for workflow shard count. (TEST-242)
    def test_browser_workflow_matches_canonical_shard_count(self):
        # Read the workflow once so one named assertion owns every count-bearing representation.
        workflow_text = self.workflow_text(BROWSER_WORKFLOW)
        # Derive the complete matrix text from the one canonical test constant.
        expected_matrix = "shard: [" + ", ".join(str(index) for index in range(BROWSER_SHARD_COUNT)) + "]"
        # Derive the exact runner argument from the same constant.
        expected_argument = f"--shard-count {BROWSER_SHARD_COUNT}"
        # Compare matrix presence and both worker/aggregate arguments in one named fail-closed assertion.
        self.assertEqual((expected_matrix in workflow_text, workflow_text.count(expected_argument)), (True, 2), "Browser workflow shard count does not match BROWSER_SHARD_COUNT")

    # Prove scheduled/manual profile refresh uses exact successful shard evidence and opens only a reviewable PR. (TOOL-017, TEST-183)
    def test_browser_duration_profile_workflow_is_bounded_and_reviewable(self):
        # Read the workflow as inert policy text without contacting GitHub.
        workflow_text = self.workflow_text(BROWSER_DURATION_WORKFLOW)
        # Require both the scheduled maintenance lane and an operator-visible on-demand trigger.
        self.assertIn("schedule:", workflow_text)
        self.assertIn("workflow_dispatch:", workflow_text)
        # Require the latest successful protected-main Browser run rather than untrusted PR evidence.
        self.assertIn("actions/workflows/browser-tests.yml/runs?", workflow_text)
        self.assertIn("branch=main", workflow_text)
        self.assertIn("status=success", workflow_text)
        # Require exact shard artifact download with merged result filenames.
        self.assertIn("pattern: browser-test-artifacts-shard-*", workflow_text)
        self.assertIn("merge-multiple: true", workflow_text)
        # Require the strict tracked generator and focused policy suite before publication.
        self.assertIn("python scripts/generate_browser_durations.py logs/test-runs", workflow_text)
        self.assertIn("python -m unittest tests.cicd_deployment_tests", workflow_text)
        # Require no-change runs to stop before branch, push, or PR creation.
        self.assertIn("git diff --quiet -- tests/browser_case_durations.json", workflow_text)
        # Require an existing automated profile branch or PR to suppress duplicate publication.
        self.assertIn("gh pr list --state open --base main --json headRefName", workflow_text)
        self.assertIn("git ls-remote --heads origin 'refs/heads/codex/browser-duration-profile-*'", workflow_text)
        self.assertIn("changed=blocked", workflow_text)
        # Require the workflow to stage only the reviewed duration profile.
        self.assertIn("git add -- tests/browser_case_durations.json", workflow_text)
        # Require a draft review boundary and the repository's issue-lifecycle metadata section.
        self.assertIn("gh pr create --draft", workflow_text)
        self.assertIn("## Issues resolved", workflow_text)
        # Require the token-authored PR to dispatch all nine unchanged qualification workflows against its exact branch head.
        expected_workflows = ("ci.yml", "browser-tests.yml", "long-suite-100.yml", "release.yml", "docs.yml", "comment-density.yml", "contract-tests.yml", "module-boundaries.yml", "codex-review.yml")
        # Require each exact workflow dispatch once so the resulting draft can become genuinely green.
        self.assertTrue(all(workflow_text.count(f"gh workflow run {workflow_name} --ref") == 1 for workflow_name in expected_workflows))
        # Require ordinary Browser coverage rather than a formal or sustained qualification profile.
        self.assertIn("-f formal_ui_50000=false -f baccarat_sustained_2000=false -f concurrent_browser_138=false -f profile_refresh=true", workflow_text)
        # Require the profile workflow to own the Actions write permission needed for explicit dispatch.
        self.assertIn("actions: write", workflow_text)
        # Require the unpublished manual candidate to consume the exact canonical packaged version.
        self.assertIn('gh workflow run release.yml --ref "${BRANCH_NAME}" -f app_version="${app_version}" -f recovery_action=candidate', workflow_text)
        # Require every newly dispatchable simple gate to retain its historical job body unchanged.
        for workflow_name in ("ci.yml", "docs.yml", "comment-density.yml", "contract-tests.yml", "module-boundaries.yml", "codex-review.yml"):
            # Inspect only the declared trigger surface for the bounded dispatch hook.
            self.assertIn("workflow_dispatch:", self.workflow_text(ROOT / ".github" / "workflows" / workflow_name))
        # Reject direct protected-main pushes and automatic merge behavior.
        self.assertNotIn("git push origin main", workflow_text)
        self.assertNotIn("gh pr merge", workflow_text)


# Run focused evidence directly when invoked by a developer or release validator.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
