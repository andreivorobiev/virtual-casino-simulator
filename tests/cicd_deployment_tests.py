"""Listener-free CI/CD workflow policy tests for TOOL-008 and TEST-133."""

# Import path helpers so assertions read the checked-in workflow from any cwd.
from pathlib import Path
# Import unittest for dependency-free workflow policy checks.
import unittest

# Resolve the repository root from this focused test file.
ROOT = Path(__file__).resolve().parents[1]
# Point at the protected-main production deployment workflow.
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-production.yml"


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
        # Require final edge observation after restart and nginx reload.
        self.assertIn("scripts/edge_gate.py observe", text)

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


# Run focused evidence directly when invoked by a developer or release validator.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
