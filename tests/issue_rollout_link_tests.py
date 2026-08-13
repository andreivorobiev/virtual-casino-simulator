# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free regression coverage for completed-issue rollout linkage."""

# Import path helpers for inert workflow inspection.
from pathlib import Path
# Import the standard test runner without network or listener dependencies.
import unittest
# Import HTTP status errors to model GitHub's concurrent label-creation race.
from urllib.error import HTTPError

# Import the pure enforcement seams and fixed durable-label identity.
from scripts.enforce_issue_rollout_link import COMMENT_MARKER, MISSING_LABEL, enforce_issue, explicit_rollout_numbers, timeline_pull_request_numbers

# Resolve the repository root independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Point at the issue-only default-branch workflow.
WORKFLOW = ROOT / ".github" / "workflows" / "issue-rollout-link.yml"


# Model only the authenticated repository calls made by the enforcement functions.
class FakeGitHubClient:
    # Build one isolated repository model for each test.
    def __init__(self, comments=None, timeline=None, pulls=None, label_exists=True, label_create_conflict=False):
        self.repository = "owner/repository"  # Bind candidates to one exact repository.
        self.comments = list(comments or [])  # Preserve issue comment order.
        self.timeline = list(timeline or [])  # Preserve timeline event order.
        self.pulls = dict(pulls or {})  # Map PR numbers to API response fixtures.
        self.label_exists = label_exists  # Model first-use label creation.
        self.label_create_conflict = label_create_conflict  # Model another run winning label creation after the first lookup.
        self.calls = []  # Record every mutation and lookup for assertions.

    # Return the configured comments or timeline for one exact issue path.
    def list_all(self, path):
        self.calls.append(("LIST", path, None))  # Record bounded list access.
        if "/comments" in path:  # Select the configured issue comments.
            return list(self.comments)  # Return a copy so callers cannot mutate the fixture.
        if "/timeline" in path:  # Select the configured issue timeline.
            return list(self.timeline)  # Return a copy for the same isolation guarantee.
        raise AssertionError(path)  # Fail a test that expands network scope unexpectedly.

    # Model merged-PR lookup plus exact label and comment mutations.
    def request(self, method, path, payload=None, allow_404=False):
        self.calls.append((method, path, payload))  # Record every exact API action.
        if method == "GET" and path.startswith("/pulls/"):  # Resolve a candidate PR fixture.
            return self.pulls.get(int(path.rsplit("/", 1)[1]))  # Return None for a missing/non-PR number.
        if method == "GET" and path.startswith("/labels/"):  # Resolve durable-label existence.
            return {"name": MISSING_LABEL} if self.label_exists else None  # Return the configured state.
        if method == "POST" and path == "/labels":  # Model first-use label creation.
            self.label_exists = True  # Make later calls observe the created label.
            if self.label_create_conflict:  # Reproduce GitHub's duplicate-label race response.
                raise HTTPError("https://api.github.test/labels", 422, "already exists", None, None)  # Surface the exact recoverable status.
            return payload  # Return the submitted shape like GitHub.
        if method in {"POST", "DELETE"}:  # Accept only the governed issue mutations.
            return None  # Model successful label/comment writes.
        raise AssertionError((method, path))  # Fail unexpected reads or broader writes.


# Build a repository-local merged PR response with the minimum reviewed fields.
def merged_pull(number=42, repository="owner/repository"):
    return {"number": number, "merged_at": "2026-08-13T00:00:00Z", "base": {"repo": {"full_name": repository}}}  # Return exact merged evidence.


# Prove extraction, merged validation, idempotent labeling, exemptions, and workflow scope.
class IssueRolloutLinkTests(unittest.TestCase):
    # Build one completed issue fixture with optional enforcement labels.
    def issue(self, labels=(), state_reason="completed"):
        return {"number": 77, "state": "closed", "state_reason": state_reason, "body": "", "labels": [{"name": label} for label in labels]}  # Return the exact API shape.

    # Accept only explicit historical rollout statements from issue-authored text.
    def test_explicit_marker_excludes_unrelated_issue_references(self):
        issue = {"body": "Related to #9\nRolled out with PR #42"}  # Mix one unrelated issue with the governed marker.
        comments = [{"body": "See #10"}, {"body": "- Rolled out with #43"}]  # Exercise comment markers and noise.
        self.assertEqual(explicit_rollout_numbers(issue, comments), {42, 43})  # Keep only explicit rollout candidates.

    # Accept only cross-references whose source object is a pull request.
    def test_timeline_extracts_only_pull_request_cross_references(self):
        timeline = [
            {"event": "cross-referenced", "source": {"issue": {"number": 41}}},  # Reject issue-to-issue linkage.
            {"event": "mentioned", "source": {"issue": {"number": 42, "pull_request": {}}}},  # Reject the wrong event type.
            {"event": "cross-referenced", "source": {"issue": {"number": 43, "pull_request": {"url": "x"}}}},  # Accept a PR source.
        ]
        self.assertEqual(timeline_pull_request_numbers(timeline), {43})  # Return only the native PR cross-reference.

    # Clear a stale label when an explicit marker resolves to a merged repository-local PR.
    def test_merged_explicit_rollout_clears_missing_label(self):
        client = FakeGitHubClient(comments=[{"body": "Rolled out with #42"}], pulls={42: merged_pull()})  # Configure valid evidence.
        result = enforce_issue(client, self.issue(labels=[MISSING_LABEL]))  # Re-evaluate one labeled completed issue.
        self.assertEqual(result, "LINKED:#42")  # Report the exact merged PR.
        self.assertIn(("DELETE", f"/issues/77/labels/{MISSING_LABEL}", None), client.calls)  # Remove only the enforcement label.

    # Reject open, unmerged, or cross-repository PR candidates and mark the issue once.
    def test_unmerged_or_foreign_rollout_is_marked_missing_once(self):
        comments = [{"body": "Rolled out with #40\nRolled out with #41"}]  # Supply two non-qualifying PR candidates.
        pulls = {
            40: {"number": 40, "merged_at": None, "base": {"repo": {"full_name": "owner/repository"}}},  # Keep one PR unmerged.
            41: merged_pull(41, "other/repository"),  # Point the other at a different repository.
        }
        client = FakeGitHubClient(comments=comments, pulls=pulls, label_exists=False)  # Model first repository use.
        result = enforce_issue(client, self.issue())  # Enforce the completed issue.
        self.assertEqual(result, "MISSING")  # Preserve a visible unresolved disposition.
        self.assertEqual(sum(call[0:2] == ("POST", "/labels") for call in client.calls), 1)  # Create the durable label once.
        self.assertEqual(sum(call[0:2] == ("POST", "/issues/77/labels") for call in client.calls), 1)  # Apply the label once.
        comment_posts = [call for call in client.calls if call[0:2] == ("POST", "/issues/77/comments")]  # Select repair comments.
        self.assertEqual(len(comment_posts), 1)  # Post one repair comment.
        self.assertIn(COMMENT_MARKER, comment_posts[0][2]["body"])  # Bind its idempotency marker.

    # Avoid duplicate comments and labels when a later issue event rechecks the same gap.
    def test_repeated_missing_event_is_idempotent(self):
        client = FakeGitHubClient(comments=[{"body": f"{COMMENT_MARKER}\nExisting repair"}])  # Seed the workflow comment.
        result = enforce_issue(client, self.issue(labels=[MISSING_LABEL]))  # Re-run with the durable label present.
        self.assertEqual(result, "MISSING")  # Keep the unresolved state visible.
        self.assertFalse(any(call[0] == "POST" for call in client.calls))  # Perform no repeated mutation.

    # Accept a concurrent first-use label creator only after the canonical label becomes readable.
    def test_concurrent_label_creation_is_verified_and_continues(self):
        client = FakeGitHubClient(label_exists=False, label_create_conflict=True)  # Make another run win between GET and POST.
        result = enforce_issue(client, self.issue())  # Enforce the same completed issue after the race.
        self.assertEqual(result, "MISSING")  # Preserve the visible unresolved disposition.
        label_reads = [call for call in client.calls if call[0] == "GET" and call[1].startswith("/labels/")]  # Select label verification reads.
        self.assertEqual(len(label_reads), 2)  # Require absence detection plus post-conflict verification.
        self.assertIn(("POST", "/issues/77/labels", {"labels": [MISSING_LABEL]}), client.calls)  # Continue by applying the verified label.

    # Exempt not-planned closures, open issues, and PR-shaped issue-comment events without lookups.
    def test_not_planned_open_and_pull_request_events_are_exempt(self):
        candidates = (self.issue(state_reason="not_planned"), {**self.issue(), "state": "open"}, {**self.issue(), "pull_request": {"url": "x"}})  # Exercise all exemptions.
        for issue in candidates:  # Prove each non-governed shape independently.
            with self.subTest(issue=issue):  # Keep failures independently attributable.
                client = FakeGitHubClient()  # Create a fresh no-call client.
                self.assertEqual(enforce_issue(client, issue), "EXEMPT")  # Return the no-mutation result.
                self.assertEqual(client.calls, [])  # Avoid every API lookup and mutation.

    # Require the workflow to own only issue metadata and never reopen or mutate source.
    def test_workflow_scope_and_triggers_are_exact(self):
        text = WORKFLOW.read_text(encoding="utf-8")  # Inspect the inert workflow source.
        self.assertIn("issues:\n    types: [closed]", text)  # Enforce completed closures immediately.
        self.assertIn("issue_comment:\n    types: [created, edited]", text)  # Re-evaluate explicit repair markers.
        self.assertIn("schedule:", text)  # Retain the weekly straggler summary.
        self.assertIn("issues: write", text)  # Permit only the necessary label/comment writes.
        self.assertIn("pull-requests: read", text)  # Verify merged PR evidence without PR mutation.
        self.assertNotIn("contents: write", text)  # Reject source mutation.
        self.assertNotIn("state: open", text)  # Reject automatic issue reopening.
        self.assertIn("python scripts/enforce_issue_rollout_link.py", text)  # Invoke the reviewed enforcement boundary.


# Support focused local and hosted execution without test discovery side effects.
if __name__ == "__main__":
    unittest.main()  # Run only this listener-free suite.
