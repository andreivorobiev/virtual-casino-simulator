#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Enforce merged-PR rollout traceability for completed GitHub issues."""

# Import JSON for GitHub event, API request, and response envelopes.
import json
# Import environment variables for immutable Actions event and repository identity.
import os
# Import pathlib so the workflow event and summary are read without shell parsing.
import pathlib
# Import regular expressions for the explicit historical rollout marker.
import re
# Import sys so deterministic diagnostics reach the Actions log.
import sys
# Import URL quoting for repository-controlled label names.
import urllib.parse
# Import the standard HTTP client so the workflow needs no extra package.
import urllib.request
# Import HTTP status errors so label absence can be distinguished from API failure.
from urllib.error import HTTPError

# Name the durable workflow label applied to unresolved completed issues. (TOOL-014)
MISSING_LABEL = "needs-rollout-link"
# Mark the idempotent enforcement comment so later events never spam the issue.
COMMENT_MARKER = "<!-- rollout-link-enforcement -->"
# Match only an explicit rollout statement rather than arbitrary issue-body references.
ROLLOUT_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?Rolled out with\s+(?:PR\s+)?#(\d+)\b")
# Publish one fixed repair comment without leaking API or repository internals.
MISSING_COMMENT = f"{COMMENT_MARKER}\nThis completed issue has no verified merged pull-request rollout link. Add an explicit `Rolled out with #NNN` comment (where #NNN is a merged PR) or ensure the merged PR cross-references this issue; then the enforcement workflow will remove `{MISSING_LABEL}`."


# Provide the narrow authenticated REST calls used by the default-branch workflow.
class GitHubClient:
    # Bind one token and repository without ever printing either value.
    def __init__(self, token: str, repository: str):
        self.token = token  # Retain the workflow token only in process memory.
        self.repository = repository  # Retain the owner/name scope for repository-local calls.

    # Execute one JSON REST request and return its decoded response.
    def request(self, method: str, path: str, payload=None, allow_404: bool = False):
        url = f"https://api.github.com/repos/{self.repository}{path}"  # Constrain every request to the event repository.
        body = json.dumps(payload).encode("utf-8") if payload is not None else None  # Encode only explicit mutation bodies.
        request = urllib.request.Request(url, data=body, method=method)  # Build the exact HTTP method and path.
        request.add_header("Accept", "application/vnd.github+json")  # Request stable current REST response shapes.
        request.add_header("Authorization", f"Bearer {self.token}")  # Authenticate without placing the token in an argv.
        request.add_header("X-GitHub-Api-Version", "2022-11-28")  # Pin the reviewed API behavior.
        try:  # Convert only an explicitly allowed missing resource into None.
            with urllib.request.urlopen(request, timeout=30) as response:  # Bound every network wait.
                data = response.read()  # Read the bounded GitHub response before closing the connection.
        except HTTPError as exc:  # Inspect status without suppressing unrelated GitHub failures.
            if allow_404 and exc.code == 404:  # Treat an absent optional label or PR as a normal lookup miss.
                return None  # Return an unambiguous missing sentinel.
            raise  # Fail closed on authentication, permission, rate, or server errors.
        if not data:  # Accept GitHub's empty 204 response for deletion.
            return None  # Return no JSON value for an empty successful response.
        return json.loads(data.decode("utf-8"))  # Decode the authenticated JSON envelope.

    # Read all items from one repository endpoint using bounded standard pagination.
    def list_all(self, path: str) -> list:
        items = []  # Accumulate deterministic page order.
        separator = "&" if "?" in path else "?"  # Preserve any caller-supplied query.
        for page in range(1, 101):  # Bound pathological repositories to ten thousand rows.
            batch = self.request("GET", f"{path}{separator}per_page=100&page={page}")  # Fetch one full page.
            if not isinstance(batch, list):  # Refuse an unexpected API envelope.
                raise RuntimeError("GitHub list endpoint returned a non-list response")  # Keep the failure low-cardinality.
            items.extend(batch)  # Preserve GitHub order for stable audit summaries.
            if len(batch) < 100:  # Stop at the first terminal page.
                return items  # Return the complete bounded result.
        raise RuntimeError("GitHub list endpoint exceeded the 100-page safety bound")  # Fail instead of silently truncating.


# Extract only explicit historical rollout markers from issue-authored text.
def explicit_rollout_numbers(issue: dict, comments: list[dict]) -> set[int]:
    texts = [str(issue.get("body") or "")]  # Include the issue body for maintained historical records.
    texts.extend(str(comment.get("body") or "") for comment in comments)  # Include every fetched issue comment.
    return {int(match) for text in texts for match in ROLLOUT_RE.findall(text)}  # Deduplicate exact PR candidates.


# Extract pull-request cross-references from the issue timeline.
def timeline_pull_request_numbers(timeline: list[dict]) -> set[int]:
    numbers = set()  # Collect only repository-local PR candidates.
    for event in timeline:  # Inspect every timeline event returned by GitHub.
        if event.get("event") != "cross-referenced":  # Ignore labels, comments, commits, and unrelated lifecycle events.
            continue  # Advance without interpreting other event shapes.
        source_issue = ((event.get("source") or {}).get("issue") or {})  # Read the cross-reference source defensively.
        if not source_issue.get("pull_request"):  # Reject issue-to-issue references.
            continue  # Only a PR can qualify as rollout evidence.
        number = source_issue.get("number")  # Read the repository issue/PR number.
        if type(number) is int and number > 0:  # Reject booleans, strings, and invalid identifiers.
            numbers.add(number)  # Add the stable PR candidate.
    return numbers  # Return every distinct cross-referenced PR number.


# Resolve candidate numbers to merged PRs in this exact repository.
def merged_rollout_numbers(client: GitHubClient, candidates: set[int]) -> list[int]:
    merged = []  # Retain deterministic numeric order for summaries.
    for number in sorted(candidates):  # Avoid API-order instability.
        pull = client.request("GET", f"/pulls/{number}", allow_404=True)  # Distinguish issues and missing numbers from PRs.
        if not isinstance(pull, dict) or not pull.get("merged_at"):  # Require an actual merged PR.
            continue  # Open, closed-unmerged, and missing PRs cannot satisfy rollout traceability.
        base_repository = (((pull.get("base") or {}).get("repo") or {}).get("full_name"))  # Read the target repository.
        if base_repository != client.repository:  # Reject a similarly numbered PR from another repository.
            continue  # Keep evidence repository-local.
        merged.append(number)  # Record the verified merged rollout.
    return merged  # Return exact accepted PR identities.


# Evaluate one issue using its comments, timeline, and candidate PR records.
def verified_rollout_numbers(client: GitHubClient, issue: dict) -> list[int]:
    number = int(issue["number"])  # Bind every subordinate lookup to the exact issue.
    comments = client.list_all(f"/issues/{number}/comments")  # Read issue-authored rollout markers.
    timeline = client.list_all(f"/issues/{number}/timeline")  # Read GitHub-native PR cross-references.
    candidates = explicit_rollout_numbers(issue, comments)  # Collect explicit maintained markers.
    candidates.update(timeline_pull_request_numbers(timeline))  # Add native cross-reference candidates.
    return merged_rollout_numbers(client, candidates)  # Accept only merged repository-local PRs.


# Return whether a closed issue is governed as a completed disposition.
def is_completed_issue(issue: dict) -> bool:
    if issue.get("pull_request"):  # Exempt pull requests because issue_comment events share the issue webhook shape.
        return False  # Never label or comment on a pull request through this issue-only workflow.
    if issue.get("state") != "closed":  # Ignore open work entirely.
        return False  # Open issues have no closure evidence obligation yet.
    return issue.get("state_reason") != "not_planned"  # Treat null legacy closures as completed and exempt explicit not-planned decisions.


# Ensure the durable label exists while tolerating one concurrent first-use creator.
def ensure_missing_label(client: GitHubClient) -> None:
    encoded = urllib.parse.quote(MISSING_LABEL)  # Encode the stable repository label path segment.
    existing = client.request("GET", f"/labels/{encoded}", allow_404=True)  # Detect whether another run already created it.
    if isinstance(existing, dict):  # Avoid a redundant repository mutation when the label exists.
        return  # Preserve the existing canonical label.
    payload = {"name": MISSING_LABEL, "color": "d4c5f9", "description": "Completed issue missing a verified merged-PR rollout link"}  # Bind exact label metadata.
    try:  # Treat only GitHub's duplicate-label race as recoverable.
        client.request("POST", "/labels", payload)  # Create the durable label for first repository use.
    except HTTPError as exc:  # Inspect the mutation result without suppressing permission or server failures.
        if exc.code != 422:  # Reserve recovery for the duplicate/unprocessable race response.
            raise  # Fail closed on every unrelated GitHub error.
        winner = client.request("GET", f"/labels/{encoded}", allow_404=True)  # Verify a concurrent run actually created the label.
        if not isinstance(winner, dict) or winner.get("name") != MISSING_LABEL:  # Reject an unexplained validation error.
            raise RuntimeError("GitHub rejected rollout-link label creation without creating the canonical label") from exc  # Preserve the causal error.


# Add the missing-link label and one idempotent repair comment.
def mark_missing(client: GitHubClient, issue: dict) -> None:
    number = int(issue["number"])  # Bind all mutations to the exact completed issue.
    labels = {str(label.get("name")) for label in issue.get("labels", []) if isinstance(label, dict)}  # Read current labels.
    comments = client.list_all(f"/issues/{number}/comments")  # Read existing workflow comments before writing.
    ensure_missing_label(client)  # Create or verify the canonical label before applying it.
    if MISSING_LABEL not in labels:  # Avoid duplicate label mutations.
        client.request("POST", f"/issues/{number}/labels", {"labels": [MISSING_LABEL]})  # Add without replacing useful labels.
    if not any(COMMENT_MARKER in str(comment.get("body") or "") for comment in comments):  # Avoid repeated bot comments.
        client.request("POST", f"/issues/{number}/comments", {"body": MISSING_COMMENT})  # Post one actionable repair instruction.


# Remove the workflow label after a merged rollout becomes verifiable.
def clear_missing(client: GitHubClient, issue: dict) -> None:
    labels = {str(label.get("name")) for label in issue.get("labels", []) if isinstance(label, dict)}  # Read current label names.
    if MISSING_LABEL in labels:  # Mutate only an issue currently marked by enforcement.
        encoded = urllib.parse.quote(MISSING_LABEL)  # Encode the repository label path segment.
        client.request("DELETE", f"/issues/{int(issue['number'])}/labels/{encoded}")  # Remove only the enforcement label.


# Enforce one event issue and return a concise outcome string.
def enforce_issue(client: GitHubClient, issue: dict) -> str:
    if not is_completed_issue(issue):  # Exempt open and explicitly not-planned issues.
        return "EXEMPT"  # Report a no-mutation disposition.
    merged = verified_rollout_numbers(client, issue)  # Resolve exact merged PR evidence.
    if merged:  # Accept one or more verified rollouts.
        clear_missing(client, issue)  # Remove stale enforcement state if present.
        return "LINKED:" + ",".join(f"#{number}" for number in merged)  # Report low-cardinality PR identities.
    mark_missing(client, issue)  # Preserve the completed issue but make missing evidence visible.
    return "MISSING"  # Report the unresolved state.


# Append one sanitized Actions summary without tokens, bodies, or comment text.
def write_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")  # Read the runner-owned summary path.
    if not summary_path:  # Permit focused local execution without Actions metadata.
        return  # Leave no local artifact when no summary was requested.
    with pathlib.Path(summary_path).open("a", encoding="utf-8") as handle:  # Append to other job summaries safely.
        handle.write("\n".join(lines) + "\n")  # Write only pre-sanitized low-cardinality rows.


# Sweep only already-labeled closed issues and clear labels whose rollout is now valid.
def sweep(client: GitHubClient) -> int:
    label = urllib.parse.quote(MISSING_LABEL)  # Encode the exact filter label.
    issues = client.list_all(f"/issues?state=closed&labels={label}")  # Read the durable unresolved queue.
    unresolved = []  # Collect exact issue numbers for the weekly summary.
    for issue in issues:  # Re-evaluate every labeled issue without reopening it.
        if issue.get("pull_request"):  # GitHub's issues endpoint also returns PR records.
            continue  # Ignore PRs because the rule governs product issues.
        result = enforce_issue(client, issue)  # Clear repaired links or retain missing labels idempotently.
        if result == "MISSING":  # Preserve only genuinely unresolved completed issues.
            unresolved.append(int(issue["number"]))  # Add the stable issue identity.
    write_summary(["## Completed issue rollout-link sweep", f"Unresolved: {len(unresolved)}", *(f"- #{number}" for number in unresolved)])  # Publish one weekly queue.
    print(f"Issue rollout-link sweep completed: unresolved={len(unresolved)}")  # Emit one log metric.
    return 0  # A missing link is reported and labeled, not a workflow infrastructure failure.


# Execute event or scheduled enforcement using immutable Actions metadata.
def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")  # Read the scoped Actions token from memory.
    repository = os.environ.get("GITHUB_REPOSITORY", "")  # Read the current owner/name identity.
    if not token or not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):  # Fail closed on missing workflow identity.
        print("Issue rollout-link enforcement failed: missing GitHub token or repository identity.")  # Keep the diagnostic secret-free.
        return 1  # Refuse unscoped API access.
    client = GitHubClient(token, repository)  # Create the repository-confined client.
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")  # Select event or sweep behavior.
    if event_name in {"schedule", "workflow_dispatch"}:  # Run the bounded durable-label sweep.
        return sweep(client)  # Return the sweep status directly.
    event_path = pathlib.Path(os.environ.get("GITHUB_EVENT_PATH", ""))  # Resolve the immutable event payload.
    if not event_path.is_file():  # Reject a missing issue event.
        print("Issue rollout-link enforcement failed: missing GITHUB_EVENT_PATH payload.")  # Emit fixed context.
        return 1  # Fail closed without an issue identity.
    payload = json.loads(event_path.read_text(encoding="utf-8"))  # Parse the runner-provided event.
    issue = payload.get("issue")  # Read the issue snapshot shared by issues and issue_comment events.
    if not isinstance(issue, dict) or type(issue.get("number")) is not int:  # Require an exact issue identity.
        print("Issue rollout-link enforcement failed: event has no issue identity.")  # Avoid reflecting payload content.
        return 1  # Refuse an ambiguous mutation.
    result = enforce_issue(client, issue)  # Apply the idempotent repository rule.
    write_summary(["## Completed issue rollout-link enforcement", f"Issue: #{issue['number']}", f"Result: {result}"])  # Record the exact outcome.
    print(f"Issue rollout-link enforcement: issue=#{issue['number']} result={result}")  # Emit low-cardinality evidence.
    return 0  # Missing linkage is handled through visible issue state rather than failing Actions.


# Run only as a workflow entry point, never during import-based tests.
if __name__ == "__main__":
    raise SystemExit(main())  # Return the deterministic workflow status.
