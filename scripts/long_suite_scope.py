# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Classify whether a pull-request diff requires Long Suite 100. (TOOL-017)"""

# Import standard input for the GitHub changed-file stream.
import sys


# Identify paths whose changes are documentation or release metadata only.
def is_documentation_only(path):
    # Normalize GitHub's repository-relative slash form before classification.
    normalized = path.strip().replace("\\", "/")
    # Treat an absent row as unsafe so malformed input runs the full suite.
    if not normalized:
        return False
    # Documentation trees and Markdown sources do not alter runtime or long-suite behavior.
    if normalized.startswith("docs/") or normalized.endswith(".md"):
        return True
    # Release identity, localized announcement, and module revision records are metadata-only inputs.
    return normalized in {
        "pyproject.toml",
        "RELEASE_NOTES.md",
        "CODEX_START_HERE.md",
        "modules/application.json",
        "modules/contracts.json",
        "modules/docs.json",
        "modules/module-manifest.json",
        "modules/tests.json",
        "modules/tooling.json",
        "web/core/pwa.js",
        "web/sw.js",
        "web/i18n/en-US/shell.json",
        "web/i18n/ru-RU/shell.json",
    } or normalized.startswith("contracts/compatibility/app-")


# Emit one fail-closed workflow decision for all changed paths received on standard input.
def main():
    # Retain each nonempty path exactly once for a deterministic all-rows decision.
    paths = sorted({line.strip() for line in sys.stdin if line.strip()})
    # Empty or any behavior-bearing diff runs every shard; only an entirely metadata-only diff skips.
    print("SKIP" if paths and all(is_documentation_only(path) for path in paths) else "RUN")
    # Return success after emitting exactly one accepted decision token.
    return 0


# Run only when invoked by the workflow or focused tests.
if __name__ == "__main__":
    # Propagate the explicit success result to the caller.
    raise SystemExit(main())
