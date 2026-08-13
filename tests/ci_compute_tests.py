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

    # Restrict optimized candidate builds to exact GitHub PR events and preserve full release validation.
    def test_release_pr_mode_is_narrow_and_release_events_stay_full(self):
        # Read the workflow to distinguish the optimized PR command from manual and release commands.
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        # Require exactly one optimized command and keep every non-PR command free of the flag.
        self.assertEqual(workflow.count("--use-pr-gate-evidence"), 1)
        self.assertIn('python scripts/make_release.py --release-tag "${{ github.event.release.tag_name }}" --previous-manifest previous/release-manifest.json', workflow)
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
