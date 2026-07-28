"""Listener-free CI/CD workflow policy tests for TOOL-002/008 and TEST-036/133."""

# Import Python syntax inspection for listener-free browser ownership policy tests.
import ast
# Import path helpers so assertions read the checked-in workflow from any cwd.
from pathlib import Path
# Import regular expressions for deterministic literal browser case discovery.
import re
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

    # Prove declared producer/consumer groups fit one deterministic shard and guard their bodies.
    def test_browser_shard_affinity_groups_are_contiguous_and_guarded(self):
        # Parse the exact browser runner source without importing it.
        source, tree = self.browser_runner_syntax()
        # Select the one browser runner function that owns all permanent BR cases.
        runner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_browser_tests")
        # Extract permanent literal IDs in deterministic source order.
        case_ids = re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", ast.get_source_segment(source, runner))
        # Require the current exact suite inventory and balanced 27/26/26/26 allocation.
        self.assertEqual(len(case_ids), 105)
        # Compute the same half-open contiguous partition used by the production runner.
        ranges = [(0, 27), (27, 53), (53, 79), (79, 105)]
        # Locate the literal affinity declaration at module scope.
        affinity_node = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "BROWSER_CASE_AFFINITY_GROUPS" for target in node.targets))
        # Read only literal strings and tuples from the tracked declaration.
        affinity_groups = ast.literal_eval(affinity_node.value)
        # Require every producer/consumer group introduced by the controller repair.
        self.assertEqual(set(affinity_groups), {"auth_backend_pwa", "guest_lifecycle", "auth_lobby", "roulette_slots_keno", "bingo_admin"})
        # Validate every group against exact case identity and one-shard ownership.
        for group_name, group_case_ids in affinity_groups.items():
            # Reject a misspelled, duplicated, or removed permanent case.
            self.assertEqual(len(group_case_ids), len(set(group_case_ids)), group_name)
            # Resolve exact source positions for every group member.
            positions = [case_ids.index(case_id) for case_id in group_case_ids]
            # Require one contiguous source range so bulk skip accounting cannot hide unrelated cases.
            self.assertEqual(positions, list(range(positions[0], positions[0] + len(positions))), group_name)
            # Resolve the deterministic owner of each position.
            owners = {index for position in positions for index, shard_range in enumerate(ranges) if shard_range[0] <= position < shard_range[1]}
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

    # Prove ordinary sharding does not alter formal 50k or sustained Baccarat governance.
    def test_browser_sharding_preserves_formal_and_baccarat_jobs(self):
        # Read the complete workflow as inert text.
        workflow_text = self.workflow_text(BROWSER_WORKFLOW)
        # Require exactly four ordinary browser shard identities.
        self.assertIn("shard: [0, 1, 2, 3]", workflow_text)
        # Require exact aggregate result accounting through the historical branch-protection context.
        self.assertIn("needs: browser_tests_shard", workflow_text)
        # Require literal-case union verification after every shard succeeds.
        self.assertIn("--verify-browser-shards logs/test-runs --shard-count 4", workflow_text)
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
