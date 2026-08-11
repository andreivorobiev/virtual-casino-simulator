# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression coverage for PR-to-ticket closure governance."""

# Import the standard listener-free test runner.
import unittest

# Import the pure validator rather than invoking its process entry point.
from scripts.validate_pr_issue_lifecycle import validate_pull_request_payload


# Group the lifecycle acceptance and rejection cases.
class IssueLifecycleTests(unittest.TestCase):
    """Keep merged feature PRs from silently leaving delivered tickets open."""

    # Build one minimal event fixture shared by every lifecycle assertion.
    def payload(self, body: str) -> dict:
        """Build the minimal immutable GitHub event shape used by the validator."""
        # Return only the pull-request body because no identity or token is needed.
        return {"pull_request": {"body": body}}

    # Prove ordinary product work uses an automatic closing relationship.
    def test_accepts_native_closing_keyword(self):
        """A normal product PR closes at least one associated issue on merge."""
        # Require the exact template section plus GitHub-native closing syntax.
        self.assertEqual([], validate_pull_request_payload(self.payload("## Issues resolved\n\n- Fixes #579\n\n## Tests")))

    # Prove a merely related ticket cannot be presented as resolved.
    def test_rejects_non_closing_issue_reference(self):
        """A descriptive issue number cannot masquerade as automatic disposition."""
        # Require an actionable failure for the old `Issue: #N` style.
        self.assertTrue(validate_pull_request_payload(self.payload("## Issues resolved\n\n- Related to #579\n")))

    # Prove standard release wrappers retain their explicit narrow exception.
    def test_accepts_explicit_release_only_pr(self):
        """A standard release wrapper need not invent a second product issue."""
        # Preserve the one product-merge then one release-merge workflow.
        self.assertEqual([], validate_pull_request_payload(self.payload("Release-only: yes\n")))


# Support direct focused execution without affecting imported discovery.
if __name__ == "__main__":
    # Support direct focused execution in local and hosted qualification.
    unittest.main()
