# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed evidence for issue #710 CI compute filtering. (TOOL-017, TEST-183)"""

# Import environment patching for the PR-only release-driver guard.
from unittest import mock
# Import portable paths for exact repository workflow and source inspection.
import pathlib
# Import unit-test assertions without invoking GitHub Actions.
import unittest

# Import the pure diff classifier and release driver under test.
from scripts import long_suite_scope, make_release


# Resolve the checked-out repository independently of the caller directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Prove filtering saves workers without weakening required contexts or release evidence.
class CiComputeTests(unittest.TestCase):
    # Classify documentation-only and behavior-bearing diffs conservatively.
    def test_long_suite_scope_is_fail_closed(self):
        # Permit a representative docs/release metadata packet to skip the expensive shards.
        self.assertTrue(all(long_suite_scope.is_documentation_only(path) for path in ["docs/runbook.md", "modules/docs.json", "README.md"]))
        # Require runtime, test, dependency, and workflow changes to execute the complete suite.
        self.assertTrue(all(not long_suite_scope.is_documentation_only(path) for path in ["casino/app.py", "tests/run_tests.py", "requirements-dev.txt", ".github/workflows/long-suite-100.yml"]))

    # Bind the gate-job pattern and exact historical required context name.
    def test_long_suite_workflow_keeps_fail_closed_gate(self):
        # Read inert workflow text so the test starts no runner or network request.
        workflow = (ROOT / ".github" / "workflows" / "long-suite-100.yml").read_text(encoding="utf-8")
        # Preserve one exact required-context job while adding a separate scope classifier.
        self.assertEqual(workflow.splitlines().count("  long_suite_100:"), 1)
        self.assertEqual(workflow.splitlines().count("  long_suite_scope:"), 1)
        # Run shards only for the explicit RUN token and fail closed on detector errors or unexpected skip state.
        self.assertIn("needs.long_suite_scope.outputs.decision == 'RUN'", workflow)
        self.assertIn('test "${{ needs.long_suite_scope.result }}" = "success"', workflow)
        self.assertIn('test "${{ needs.long_suite_100_shard.result }}" = "skipped"', workflow)

    # Restrict optimized candidate builds to exact PR events and preserve full hosted-release verification.
    def test_release_pr_mode_is_narrow_and_release_events_verify_hosted_assets(self):
        # Read the workflow to distinguish the optimized PR command from manual and release-event checks.
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        # Require exactly one optimized command and keep every non-PR command free of the flag.
        self.assertEqual(workflow.count("--use-pr-gate-evidence"), 1)
        release_event_job = workflow.split("  publish-immutable-release:", 1)[1]
        # Bind the release event to the already-hosted tag, predecessor, checksums, and rollback package.
        self.assertIn("permissions:\n      contents: read", release_event_job)
        self.assertIn('python scripts/release_publication.py inspect-hosted --tag "${RELEASE_TAG}" --commit "$(git rev-parse HEAD)"', release_event_job)
        self.assertIn('gh release download "${RELEASE_TAG}" --pattern virtual_casino_simulator_package.zip --pattern release-manifest.json --pattern checksums.txt --dir published', release_event_job)
        self.assertIn('gh release download "${PREVIOUS_TAG}" --pattern release-manifest.json --dir previous', release_event_job)
        self.assertIn("python scripts/release_publication.py verify-checksums --directory published", release_event_job)
        self.assertIn('python scripts/resolve_release_predecessor.py --app-version "${APP_VERSION}" --verify-manifest previous/release-manifest.json', release_event_job)
        self.assertIn('python scripts/package_app.py --verify-only --archive published/virtual_casino_simulator_package.zip --manifest published/release-manifest.json --expected-commit "$(git rev-parse HEAD)" --expected-tag "${RELEASE_TAG}" --require-rollback', release_event_job)
        # Release-event verification must never rebuild, upload, replace, or publish hosted bytes.
        self.assertNotIn("scripts/make_release.py", release_event_job)
        for mutation in ("contents: write", "actions/upload-artifact", "gh release create", "gh release upload", "gh release edit", "gh release delete", "git tag", "git push"):
            self.assertNotIn(mutation, release_event_job)
        # Reject local use before validation, cleanup, or packaging can run.
        with mock.patch("sys.argv", ["make_release.py", "--use-pr-gate-evidence"]), mock.patch.dict("os.environ", {}, clear=True):
            # Exercise only the early authority guard; no subprocess is reachable.
            with self.assertRaisesRegex(SystemExit, "restricted to unpublished GitHub pull-request candidates"):
                make_release.main()
        # Bind every sibling context used as exact-head validator evidence.
        self.assertEqual(make_release.PR_GATE_VALIDATIONS, ["required-context:ci", "required-context:contract_tests", "required-context:module_boundaries", "required-context:docs"])


# Run focused diagnostics directly without workflow or repository mutation.
if __name__ == "__main__":
    # Use unittest's deterministic exit status.
    unittest.main()
