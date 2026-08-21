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
    def payload(self, body: str, *, base: str = "main", head: str = "codex/feature", title: str = "Feature change") -> dict:
        """Build the minimal immutable GitHub event shape used by the validator."""
        # Return the body plus immutable release identity fields without any token or network data.
        return {"pull_request": {"body": body, "base": {"ref": base}, "head": {"ref": head}, "title": title}}

    # Prove ordinary product work uses an automatic closing relationship.
    def test_accepts_native_closing_keyword(self):
        """A normal product PR closes at least one associated issue on merge."""
        # Require the exact template section plus GitHub-native closing syntax.
        self.assertEqual([], validate_pull_request_payload(self.payload("## Issues resolved\n\n- Fixes #579\n\nRelease-only: no\n\n## Tests")))

    # Prove a merely related ticket cannot be presented as resolved.
    def test_rejects_non_closing_issue_reference(self):
        """A descriptive issue number cannot masquerade as automatic disposition."""
        # Require an actionable failure for the old `Issue: #N` style.
        self.assertTrue(validate_pull_request_payload(self.payload("## Issues resolved\n\n- Related to #579\n")))

    # Prove standard release wrappers retain their explicit narrow exception.
    def test_accepts_explicit_release_only_pr(self):
        """A standard release wrapper need not invent a second product issue."""
        # Preserve the one product-merge then one identity-bound release-merge workflow. (TOOL-012)
        payload = self.payload("Release-only: yes\n", head="codex/release-v0.9.5.84", title="release: prepare v0.9.5.84")
        self.assertEqual([], validate_pull_request_payload(payload))

    # Prove historical named release variants retain the same numeric identity boundary.
    def test_accepts_release_suffix_when_title_identifies_numeric_version(self):
        """A standard bridge wrapper may suffix its branch without changing release identity."""
        # Preserve the accepted rollback-bridge naming convention while binding the numeric version.
        payload = self.payload("Release-only: yes\n", head="codex/release-v0.9.5.39-bridge", title="Release v0.9.5.39 MySQL rollback bridge")
        self.assertEqual([], validate_pull_request_payload(payload))

    # Prove authored prose cannot grant an exception to an ordinary content branch.
    def test_rejects_release_only_claim_on_product_branch(self):
        """A feature branch cannot orphan its delivered issue by claiming release-only status."""
        # Keep the title release-shaped so the immutable head remains the decisive rejection.
        payload = self.payload("Release-only: yes\n", head="codex/1065-lifecycle", title="Release v0.9.5.85")
        self.assertTrue(validate_pull_request_payload(payload))

    # Prove stacked or side-branch wrappers cannot use the protected-main exception.
    def test_rejects_release_only_claim_targeting_non_main_base(self):
        """A release-named head must still target protected main directly."""
        # Reject the same otherwise-valid wrapper metadata when it targets a pending branch.
        payload = self.payload("Release-only: yes\n", base="codex/feature", head="codex/release-v0.9.5.85", title="Release v0.9.5.85")
        self.assertTrue(validate_pull_request_payload(payload))

    # Prove the public title and immutable branch cannot describe different release versions.
    def test_rejects_release_title_version_mismatch(self):
        """A mismatched release title cannot hide the wrapper's real source identity."""
        # Supply a valid branch with a different title version and require a focused failure.
        payload = self.payload("Release-only: yes\n", head="codex/release-v0.9.5.85", title="Release v0.9.5.86")
        self.assertEqual(["Release-only PR title must identify branch version v0.9.5.85."], validate_pull_request_payload(payload))

    # Prove ambiguous template declarations fail before either exception or issue parsing.
    def test_rejects_duplicate_conflicting_or_invalid_release_only_declarations(self):
        """Release-only metadata has one exact fail-closed value."""
        # Exercise duplicate, conflicting, and misspelled exception declarations independently.
        bodies = [
            "Release-only: yes\nRelease-only: yes\n",
            "Release-only: yes\nRelease-only: no\n",
            "Release-only: maybe\n## Issues resolved\n- Fixes #579\n",
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.assertTrue(validate_pull_request_payload(self.payload(body, head="codex/release-v0.9.5.85", title="Release v0.9.5.85")))


# Support direct focused execution without affecting imported discovery.
if __name__ == "__main__":
    # Support direct focused execution in local and hosted qualification.
    unittest.main()
