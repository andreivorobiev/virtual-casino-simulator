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
# Permit standard release-only PRs to declare that they intentionally close no product ticket.
RELEASE_ONLY_RE = re.compile(r"(?im)^\s*Release-only:\s*yes\s*$")


# Validate one already-parsed event independently from process environment for focused tests.
def validate_pull_request_payload(payload: dict) -> list[str]:
    """Return deterministic lifecycle errors for one GitHub pull_request payload."""
    # Read the authored PR body without trusting missing or non-string values.
    body = str((payload.get("pull_request") or {}).get("body") or "")
    # Allow an explicitly declared standard release PR to proceed without inventing a ticket.
    if RELEASE_ONLY_RE.search(body):
        # Return success for the explicit non-product release wrapper.
        return []
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
