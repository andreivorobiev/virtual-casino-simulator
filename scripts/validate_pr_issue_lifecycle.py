# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Require pull requests to bind delivered work to GitHub's automatic issue closure."""

# Import JSON support for the immutable Actions event payload.
import json
# Import environment access for GitHub event identity and path metadata.
import os
# Import path handling without shell or network dependencies.
import pathlib
# Import regular expressions for the stable PR-body contract.
import re

# Match GitHub's supported issue-closing keywords with a repository-local issue number. (TOOL-012)
CLOSING_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b")
# Find the governed section without treating later template sections as issue references.
SECTION_RE = re.compile(r"(?ims)^##\s+Issues resolved\s*$\n(.*?)(?=^##\s+|\Z)")
# Parse the single explicit release-only declaration without accepting arbitrary values or duplicates.
RELEASE_ONLY_RE = re.compile(r"(?im)^\s*Release-only:\s*(.*?)\s*$")
# Bind the narrow exception to the repository's standard immutable release branch convention. (TOOL-012)
RELEASE_HEAD_RE = re.compile(r"^codex/release-v(?P<version>\d+(?:\.\d+){2,})(?:-[a-z0-9][a-z0-9.-]*)?$")


# Validate the standard release wrapper from immutable pull-request metadata rather than authored prose alone.
def validate_release_only_exception(pull_request: dict) -> list[str]:
    """Return deterministic errors unless this is a standard main-targeting release wrapper."""
    # Read the immutable event fields without trusting missing or non-string values.
    base_ref = str((pull_request.get("base") or {}).get("ref") or "")
    head_ref = str((pull_request.get("head") or {}).get("ref") or "")
    title = str(pull_request.get("title") or "")
    # Require the protected integration base and canonical release branch before granting an exception.
    head_match = RELEASE_HEAD_RE.fullmatch(head_ref)
    if base_ref != "main" or head_match is None:
        # Keep the repair message stable and free of user-authored branch or title text.
        return ["'Release-only: yes' is permitted only for a codex/release-vN.N.N... head targeting main."]
    # Require the human-facing title to carry the same numeric version as the immutable branch.
    version = head_match.group("version")
    title_re = re.compile(rf"(?i)\brelease\b.*\bv{re.escape(version)}(?:\b|-)")
    if title_re.search(title) is None:
        # Identify the expected public version without echoing the untrusted title.
        return [f"Release-only PR title must identify branch version v{version}."]
    # Accept only after every standard-wrapper identity check passes.
    return []


# Validate one already-parsed event independently from process environment for focused tests.
def validate_pull_request_payload(payload: dict) -> list[str]:
    """Return deterministic lifecycle errors for one GitHub pull_request payload."""
    # Read the immutable PR envelope and authored body without trusting missing shapes or values.
    pull_request = payload.get("pull_request") or {}
    body = str(pull_request.get("body") or "")
    # Require at most one exact template declaration so duplicates and conflicts fail closed.
    release_only_values = [value.strip().lower() for value in RELEASE_ONLY_RE.findall(body)]
    if len(release_only_values) > 1:
        # Reject duplicated `yes`, duplicated `no`, and conflicting declarations uniformly.
        return ["PR body must contain at most one 'Release-only: yes|no' declaration."]
    if release_only_values and release_only_values[0] not in {"yes", "no"}:
        # Reject typos instead of silently treating an unknown exception request as ordinary metadata.
        return ["PR body release-only declaration must be exactly 'Release-only: yes' or 'Release-only: no'."]
    # Allow only an identity-bound standard release PR to proceed without inventing a ticket.
    if release_only_values == ["yes"]:
        # Return the immutable-metadata decision before examining product issue references.
        return validate_release_only_exception(pull_request)
    # Require the stable section so ticket disposition is reviewable before merge.
    section = SECTION_RE.search(body)
    if not section:
        # Report the missing stable section before examining references.
        return ["PR body must include a '## Issues resolved' section."]
    # Collect only GitHub-native closing references from the governed section.
    closing = CLOSING_RE.findall(section.group(1))
    # Reject descriptive issue references that would remain open after merge.
    if not closing:
        # Report a non-closing section so authors can use GitHub-native disposition.
        return ["The 'Issues resolved' section must contain at least one 'Fixes #N', 'Closes #N', or 'Resolves #N' entry."]
    # Successful validation has no diagnostic rows.
    return []


# Validate the current process event for direct CI execution.
def main() -> int:
    """Validate the current Actions event and print low-cardinality diagnostics."""
    # Skip protected-main pushes because GitHub closes issues from the reviewed PR body.
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        # Explain why protected-main pushes do not need a second PR-body check.
        print("Issue lifecycle validation skipped outside pull_request events.")
        # Return success because the reviewed PR event was already checked.
        return 0
    # Resolve the immutable event payload supplied by GitHub Actions.
    event_path = pathlib.Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    # Fail closed when a pull-request run has no readable metadata.
    if not event_path.is_file():
        # Emit one stable missing-payload diagnostic.
        print("Issue lifecycle validation failed: missing GITHUB_EVENT_PATH payload.")
        # Fail closed because lifecycle evidence cannot be reconstructed.
        return 1
    # Parse the local event file without network access or token permissions.
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    # Evaluate the governed body and retain every actionable error.
    errors = validate_pull_request_payload(payload)
    # Print each stable error so the author can repair the body without rerunning heavy suites blindly.
    for error in errors:
        # Prefix every independent repair message with the same low-cardinality label.
        print(f"Issue lifecycle validation failed: {error}")
    # Return failure when any issue-linkage contract is missing.
    return 1 if errors else 0


# Execute only when invoked as the CI command rather than imported by tests.
if __name__ == "__main__":
    # Exit with the deterministic validation status consumed by CI.
    raise SystemExit(main())
