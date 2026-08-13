# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free CI/CD workflow policy tests for TOOL-002/008 and TEST-036/133."""

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
# Import unittest for dependency-free workflow policy checks.
import unittest

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
# Point at the browser runner whose inline state must be affinity-owned.
BROWSER_RUNNER = ROOT / "tests" / "run_tests.py"
# Point at the ordinary, formal, and sustained browser workflow.
BROWSER_WORKFLOW = ROOT / ".github" / "workflows" / "browser-tests.yml"
# Point at the pull-request affected-game detector.
AFFECTED_BROWSER_GAMES = ROOT / "scripts" / "affected_browser_games.py"


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

    # Prove deployment consumes hosted Release assets rather than untrusted local build outputs.
    def test_workflow_deploys_hosted_release_assets(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require post-publication download of the three canonical assets.
        self.assertIn('gh release download "${RELEASE_TAG}" --pattern virtual_casino_simulator_package.zip --pattern release-manifest.json --pattern checksums.txt --dir published --clobber', text)
        # Require hosted assets to be verified against exact commit, tag, and rollback provenance.
        self.assertIn('python scripts/package_app.py --verify-only --archive published/virtual_casino_simulator_package.zip --manifest published/release-manifest.json --expected-commit "${GITHUB_SHA}" --expected-tag "${RELEASE_TAG}" --require-rollback', text)
        # Require only the verified hosted directory to flow into deployment.
        self.assertIn("name: production-release-assets", text)
        # Reject deployment from the runner's local dist directory.
        self.assertNotIn("scp -P \"${port}\" dist/", text)

    # Prove host activation includes rollback and authenticated edge observation.
    def test_workflow_rolls_back_when_health_fails(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require the prior release symlink to be captured before mutation.
        self.assertIn('prior_release="$(readlink -f /opt/casino/current || true)"', text)
        # Require a rollback function instead of a one-way symlink move.
        self.assertIn("rollback() {", text)
        # Require atomic symlink movement through current.next.
        self.assertIn("mv -Tf /opt/casino/current.next /opt/casino/current", text)
        # Require the generated build-provenance fragment to be installed.
        self.assertIn("scripts/write_release_env.py", text)
        # Require the root-managed bearer and application digest to match before symlink cutover.
        monitor_validation = text.index("scripts/validate_monitor_config.py")
        # Locate the release symlink mutation that follows all pre-cutover gates.
        release_switch = text.index('ln -sfn "${release_root}" /opt/casino/current.next')
        # Prove read-only monitor validation precedes the production release switch.
        self.assertLess(monitor_validation, release_switch)
        # Locate rollback activation separately from the rollback function definition.
        rollback_trap = text.index("trap rollback ERR")
        # Prove pre-cutover monitor validation fails without invoking production rollback mutation.
        self.assertLess(monitor_validation, rollback_trap)
        # Prove rollback protection begins before the first release-owned environment mutation.
        self.assertLess(rollback_trap, text.index('install -m 0640 -o root -g root "${staging}/release.env" /etc/casino/release.env'))
        # Require workflow use to remain read-only; repair is an explicit owner operation.
        self.assertIn("scripts/validate_monitor_config.py\" check --monitor-env /etc/casino/edge-monitor.env --application-env /etc/casino/casino.env", text)
        # Require final edge observation through the packaged non-shell credential runner.
        self.assertIn("scripts/run_edge_monitor.py --monitor-env /etc/casino/edge-monitor.env --policy /opt/casino/current/deploy/edge/restricted-preview.json", text)
        # Reject shell sourcing because the Authorization assignment intentionally contains a scheme separator.
        self.assertNotIn(". /etc/casino/edge-monitor.env", text)
        # Reject a nested shell command boundary for any root-managed monitor value.
        self.assertNotIn("bash -lc", text)

    # Prove the bridge deployment keeps schema two unchanged and never invokes migration.
    def test_workflow_checks_schema_two_before_and_after_cutover_without_migration(self):
        # Read the inert workflow source.
        text = self.workflow_text()
        # Pin the command-scoped candidate-root binding used by both checks.
        bound_check = 'PYTHONPATH="${release_root}" /opt/casino/venv/bin/python "${release_root}/scripts/mysql_migrate.py" bridge-check-schema2'
        # Require exactly one pre-cutover and one post-activation proof.
        self.assertEqual(text.count(bound_check), 2)
        # Locate the pre-cutover proof.
        candidate_check = text.index(bound_check)
        # Locate the post-activation proof independently.
        activated_check = text.rindex(bound_check)
        # Require the candidate proof before rollback activation or production mutation.
        self.assertLess(candidate_check, text.index("trap rollback ERR"))
        # Require the post-activation proof after service restart and edge monitoring.
        self.assertGreater(activated_check, text.index("/opt/casino/current/scripts/run_edge_monitor.py"))
        # Require active selector identity to equal the same selected release root.
        selector_identity = 'test "$(readlink -f /opt/casino/current)" = "${release_root}"'
        # Prove selector identity before the second schema check.
        self.assertLess(text.index(selector_identity), activated_check)
        # Require both proofs before staging cleanup and trap removal.
        self.assertLess(activated_check, text.index('rm -rf "${staging}" "${prior_env}"'))
        # Reject any migration apply command in the production workflow.
        self.assertNotIn("mysql_migrate.py apply", text)
        # Reject backup proof or migration identity plumbing in the activation job.
        self.assertNotIn("--backup-proof", text)
        # Reject database rollback commands or server-global changes.
        self.assertNotIn("SET GLOBAL", text.upper())

    # Prove the workflow requires scoped SSH secrets and does not embed host identities.
    def test_workflow_requires_scoped_ssh_secrets(self):
        # Read the workflow source as inert text.
        text = self.workflow_text()
        # Require every SSH input to come from GitHub secrets.
        for secret_name in ("CASINO_DEPLOY_SSH_HOST", "CASINO_DEPLOY_SSH_USER", "CASINO_DEPLOY_SSH_KEY", "CASINO_DEPLOY_KNOWN_HOSTS"):
            # Check the exact secret reference appears in the workflow.
            self.assertIn(f"secrets.{secret_name}", text)
        # Reject checked-in production hostnames or usernames in the workflow body.
        self.assertNotIn("casino.tiltseven.com", text)
        # Reject the deprecated monitor cookie as a workflow-owned dependency.
        self.assertNotIn("CASINO_EDGE_MONITOR_COOKIE", text)


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
        # Require the aggregate to depend on the complete matrix result.
        self.assertIn("needs: long_suite_100_shard", workflow_text)
        # Ensure the aggregate executes for failed, cancelled, or skipped dependencies.
        self.assertIn('run: test "${{ needs.long_suite_100_shard.result }}" = "success"', workflow_text)
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

    # Prove the shared semantic fallbacks cannot flatten Color Wheel's route-owned gradients.
    def test_semantic_game_color_cascade_preserves_color_wheel_gradients(self):
        # Read the shared stylesheet as inert text so the focused oracle opens no listener or browser.
        stylesheet = self.workflow_text(ROOT / "web" / "styles.css")
        # Read Color Wheel's production stylesheet source as the canonical gradient owner.
        color_wheel_source = self.workflow_text(ROOT / "web" / "games" / "color_wheel.js")
        # Bind each route-qualified override to its exact existing production gradient stops.
        expected_overrides = {
            # Preserve the production red wager gradient with an explicit shared-cascade override.
            ".color-wheel .cw-bet.red": ("linear-gradient(180deg, #d6323d, #8e1822)", "linear-gradient(180deg,#d6323d,#8e1822)"),
            # Preserve the production green wager gradient with an explicit shared-cascade override.
            ".color-wheel .cw-bet.green": ("linear-gradient(180deg, #0f9c4c, #0a5f2e)", "linear-gradient(180deg,#0f9c4c,#0a5f2e)"),
        }
        # Check both semantic colors through one symmetric static oracle.
        for selector, (shared_gradient, production_gradient) in expected_overrides.items():
            # Require one route-qualified shared override so no unrelated red or green control is recolored.
            self.assertEqual(stylesheet.count(selector), 1)
            # Isolate the exact override body without depending on unrelated stylesheet ordering.
            rule_body = stylesheet.split(selector, 1)[1].split("}", 1)[0]
            # Require the shared fallback conflict to be resolved without flattening the gradient.
            self.assertIn(f"background: {shared_gradient} !important;", rule_body)
            # Require the copied stops to remain byte-for-byte aligned with Color Wheel's production source.
            self.assertIn(f"background:{production_gradient};", color_wheel_source)

    # Prove declared producer/consumer groups fit one deterministic shard and guard their bodies.
    def test_browser_shard_affinity_groups_are_contiguous_and_guarded(self):
        # Parse the exact browser runner source without importing it.
        source, tree = self.browser_runner_syntax()
        # Select the one browser runner function that owns all permanent BR cases.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Extract permanent literal IDs in deterministic source order.
        case_ids = re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", ast.get_source_segment(source, runner))
        # Require the current exact suite inventory after adding real multi-tab PWA update acceptance.
        self.assertEqual(len(case_ids), 117)
        # Import the listener-free runner module so the test uses its exact reviewed packer.
        from tests import run_tests as browser_runner_module
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
        # Pin the exact accepted current-profile distribution across six runners.
        self.assertEqual(shard_loads, (212, 212, 214, 214, 213, 213))
        # Reject a degenerate or materially imbalanced assignment even if union remains exact.
        self.assertLessEqual(max(shard_loads) - min(shard_loads), 2)
        # Require exact union and nonduplication across all declared owners.
        self.assertEqual(sorted(case_id for shard_cases in shard_sets for case_id in shard_cases), sorted(case_ids))
        # Locate the one permanent Keno owner call that carries both edge and economics acceptance.
        keno_owner_call = next(node for node in ast.walk(runner) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_case" and ast.literal_eval(node.args[0]) == "BR-KENO-EDGE-001")
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
        # Locate the complete callback inside the Browser runner.
        keno_complete_callback = next(node for node in ast.walk(runner) if isinstance(node, ast.FunctionDef) and node.name == "keno_complete_acceptance")
        # Read every direct helper call from the complete callback in source order.
        keno_complete_calls = [statement.value.func.id for statement in keno_complete_callback.body if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Name)]
        # Require one complete 64-cell matrix pass followed by one route/restoration economics pass.
        self.assertEqual(keno_complete_calls, ["keno_edge_containment", "keno_economics_route_behavior"])
        # Locate the literal affinity declaration at module scope.
        affinity_node = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "BROWSER_CASE_AFFINITY_GROUPS" for target in node.targets))
        # Read only literal strings and tuples from the tracked declaration.
        affinity_groups = ast.literal_eval(affinity_node.value)
        # Require every producer/consumer group introduced by the controller repair.
        self.assertEqual(set(affinity_groups), {"auth_backend_pwa", "guest_lifecycle", "auth_lobby", "roulette_slots_keno", "bingo_admin"})
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
            # Guest loops retain unconditional run_case accounting through owner-conditioned iterables.
            if group_name == "guest_lifecycle":
                # Require both disposable lifecycle loops to test the declared owner before any setup.
                self.assertGreaterEqual(source.count("browser_shard_owns_group('guest_lifecycle')"), 2)
            # Guarded bulk ranges require both an execution guard and explicit unowned accounting.
            else:
                # Require the complete inline body to sit beneath its declared group owner.
                self.assertIn(f"if browser_shard_owns_group('{group_name}'):", source)
                # Require unowned guarded bodies to advance their exact literal positions.
                self.assertIn(f"skip_browser_affinity('{group_name}')", source)

    # Prove hostile duration profile values fail with one fixed diagnostic and no mutation.
    def test_browser_duration_profile_is_strict_bounded_and_value_free(self):
        # Import the listener-free runner module without starting Browser or a server.
        from tests import run_tests as browser_runner_module
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
            (evidence_dir / "browser_results_shard_0_of_6.json").write_text(hostile, encoding="utf-8")
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
        from tests import run_tests as browser_runner_module
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
        # Require canonical module metadata to provide the acceptance identity.
        self.assertIn("packaged_version=json.loads((ROOT/'modules'/'module-manifest.json')", runner_source)
        # Require service-worker registration and page identity checks to use that value.
        self.assertIn("f'{base}/sw.js?v={packaged_version}'", runner_source)
        # Reject any hard-coded packaged release in worker query strings or page-version assertions.
        self.assertIsNone(re.search(r"sw\.js\?v=\d+\.\d+\.\d+", runner_source))
        # Reject the stale equality form that previously required manual release edits.
        self.assertIsNone(re.search(r"CasinoPwa\?\.version===['\"]\d+\.\d+\.\d+", runner_source))

    # Prove isolated route-i18n coverage produces every state-dependent interpolation it consumes.
    def test_browser_route_i18n_declares_visible_state_producers(self):
        # Read exact runner source without importing Playwright.
        source, tree = self.browser_runner_syntax()
        # Select the browser runner and isolate its source.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Read the complete browser function for declared-driver inspection.
        runner_source = ast.get_source_segment(source, runner)
        # Require the Slots history interpolation to own one visible spin producer.
        self.assertIn("'games/slots':drive_slots_interpolation", runner_source)
        # Require the Keno final-draw interpolation to own one visible draw producer.
        self.assertIn("'games/keno':drive_keno_interpolation", runner_source)
        # Require every route-specific producer to execute after mount and before audit.
        self.assertIn("if interpolation_driver: interpolation_driver()", runner_source)
        # Require state production to use only current player-visible action controls.
        self.assertIn("page.get_by_test_id('slots-spin').click()", runner_source)
        # Require the Keno driver to use the real draw action rather than a hidden API shortcut.
        self.assertIn("page.get_by_test_id('keno-draw').click()", runner_source)

    # Prove expected normal-role denials cannot poison the final browser-error invariant.
    def test_browser_admin_affinity_clears_only_expected_denial_observations(self):
        # Read exact browser source without importing its runtime.
        source, tree = self.browser_runner_syntax()
        # Select the browser runner and isolate its source.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Read the complete browser function for producer/cleanup ordering checks.
        runner_source = ast.get_source_segment(source, runner)
        # Locate the normal-role authorization producer on the Admin-owned shard.
        producer_index = runner_source.index("normal_admin_navigation=collect_normal_admin_navigation()")
        # Locate the bounded expected-denial cleanup after that producer.
        cleanup_index = runner_source.index("console_errors.clear(); http_errors.clear()", producer_index)
        # Locate Admin login after the normal-role denial evidence is retained.
        admin_login_index = runner_source.index("admin_browser_login=page.request.post", producer_index)
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
        # Parse the exact browser runner without importing Playwright or opening a listener.
        source, tree = self.browser_runner_syntax()
        # Select the browser runner and read permanent literal cases in source order.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Extract the permanent browser case inventory.
        case_ids = re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", ast.get_source_segment(source, runner))
        # Locate the literal affected-game acceptance map.
        mapping_node = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "BROWSER_GAME_ACCEPTANCE_CASES" for target in node.targets))
        # Read only the literal game-to-case mapping.
        game_cases = ast.literal_eval(mapping_node.value)
        # Keep shared cases and the one selected game's dedicated case.
        expected = [case_id for case_id in case_ids if case_id not in set(game_cases.values()) or case_id == game_cases["acey_deucey"]]
        # Import the listener-free runner module so synthetic declarations match real packing.
        from tests import run_tests as browser_runner_module
        # Compute the exact six-runner governed ownership declarations.
        shard_sets = browser_runner_module.browser_shard_case_sets(6)
        # Create one disposable six-shard result packet.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write each deterministic packed shard result with an exact self-description.
            for index, owned_set in enumerate(shard_sets):
                # Sort the governed ownership exactly as the real runner writes it.
                owned = sorted(owned_set)
                # Build passing evidence for owned cases that survive detector selection.
                results = [{"test_id": case_id, "status": "PASS"} for case_id in owned if case_id in set(expected)]
                # Bind worker identity, detector selection, and exact ownership beside its results.
                payload = {"shard_index": index, "shard_count": 6, "affected_games": ["acey_deucey"], "owned_cases": owned, "results": results}
                # Write the exact filename consumed by the aggregate verifier.
                (Path(temp_dir) / f"browser_results_shard_{index}_of_6.json").write_text(json.dumps(payload), encoding="utf-8")
            # Run the real aggregate CLI without invoking a browser or listener.
            verified = subprocess.run([sys.executable, str(BROWSER_RUNNER), "--verify-browser-shards", temp_dir, "--shard-count", "6", "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require exact selected-case coverage to pass.
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            # Forge one shard's declaration while keeping all case rows unchanged.
            forged_path = Path(temp_dir) / "browser_results_shard_0_of_6.json"
            # Read the existing evidence before changing only its self-description.
            forged = json.loads(forged_path.read_text(encoding="utf-8"))
            # Claim a different detector selection to simulate an untrusted artifact.
            forged["affected_games"] = ["craps"]
            # Persist the forged declaration for the negative regression.
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            # Re-run the real aggregate verifier against the same expected detector input.
            rejected = subprocess.run([sys.executable, str(BROWSER_RUNNER), "--verify-browser-shards", temp_dir, "--shard-count", "6", "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
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
            missing_owner = subprocess.run([sys.executable, str(BROWSER_RUNNER), "--verify-browser-shards", temp_dir, "--shard-count", "6", "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require each shard's exact owned_cases declaration, not merely result union.
            self.assertNotEqual(missing_owner.returncode, 0, missing_owner.stdout + missing_owner.stderr)
            # Pin the bounded ownership diagnostic.
            self.assertIn("owned_cases mismatch", missing_owner.stdout)
            # Duplicate one remaining owned id to test declaration-level nonduplication.
            forged["owned_cases"] = sorted(shard_sets[0]) + [sorted(shard_sets[0])[0]]
            # Persist the duplicate-owner forgery.
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            # Re-run aggregate verification against the duplicated declaration.
            duplicate_owner = subprocess.run([sys.executable, str(BROWSER_RUNNER), "--verify-browser-shards", temp_dir, "--shard-count", "6", "--games", "acey_deucey"], text=True, capture_output=True, cwd=ROOT, check=False)
            # Require duplicate ownership to fail closed.
            self.assertNotEqual(duplicate_owner.returncode, 0, duplicate_owner.stdout + duplicate_owner.stderr)
            # Pin the fixed declaration diagnostic.
            self.assertIn("invalid owned_cases", duplicate_owner.stdout)

    # Prove ordinary sharding does not alter formal 50k or sustained Baccarat governance.
    def test_browser_sharding_preserves_formal_and_baccarat_jobs(self):
        # Read the complete workflow as inert text.
        workflow_text = self.workflow_text(BROWSER_WORKFLOW)
        # Require exactly six duration-balanced ordinary Browser workers. (issue #502)
        self.assertIn("shard: [0, 1, 2, 3, 4, 5]", workflow_text)
        # Require exact aggregate result accounting through the historical branch-protection context.
        self.assertIn("      - browser_tests_shard", workflow_text)
        # Require literal-case union verification after every shard succeeds.
        self.assertIn("--verify-browser-shards logs/test-runs --shard-count 6", workflow_text)
        # Preserve the explicit formal 50,000-cycle authorization input and exact aggregate.
        self.assertIn("formal_ui_50000:", workflow_text)
        # Preserve the exact formal cycle count and source-commit-bound aggregate.
        self.assertIn("--total-cycles 50000", workflow_text)
        # Preserve the separately authorized sustained Baccarat input and exact runner.
        self.assertIn("baccarat_sustained_2000:", workflow_text)
        # Require the focused Baccarat command to remain independent of ordinary shard execution.
        self.assertIn("python -m tests.baccarat_sustained", workflow_text)


# Run focused evidence directly when invoked by a developer or release validator.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
