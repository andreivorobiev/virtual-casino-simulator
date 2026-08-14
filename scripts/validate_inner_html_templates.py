# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Enforce monotonic migration from raw innerHTML writes to tagged templates."""

# Import JSON support for the reviewed debt baseline.
import json
# Import CLI parsing for the optional immutable pull-request baseline.
import argparse
# Import portable paths for repository-contained JavaScript discovery.
from pathlib import Path
# Import regular expressions for the deliberately narrow assignment scanner.
import re

# Resolve the repository root independently of the caller working directory.
ROOT = Path(__file__).resolve().parents[1]
# Bind the reviewed remaining-debt inventory used by local and hosted gates.
BASELINE_PATH = ROOT / "tests" / "inner_html_template_baseline.json"
# Capture one same-line right-hand side without attempting to parse unrelated JavaScript syntax.
ASSIGNMENT_RE = re.compile(r"\.innerHTML\s*=\s*([^;\r\n]+)")
# Match same-line Admin insertion calls whose payload starts at the governed template tag.
ADMIN_INSERT_ADJACENT_RE = re.compile(r"\.insertAdjacentHTML\([^,\r\n]+,\s*html`")


# Count assignments that do not start with the escape-by-default tagged helper. (SEC-017)
def scan_unmigrated(root: Path = ROOT) -> dict[str, int]:
    # Collect only files with at least one remaining untagged write.
    counts = {}
    # Walk checked-in browser JavaScript in stable path order.
    for path in sorted((root / "web").rglob("*.js")):
        # Read source as reviewed UTF-8 text without executing browser code.
        source = path.read_text(encoding="utf-8")
        # Count right-hand sides whose first token is not the governed html tag.
        count = sum(1 for match in ASSIGNMENT_RE.finditer(source) if not match.group(1).lstrip().startswith("html`"))
        # Publish only active debt so deleted assignments naturally burn down.
        if count:
            # Use portable repository-relative names for deterministic CI output.
            counts[path.relative_to(root).as_posix()] = count
    # Return the complete current debt inventory.
    return counts


# Load one exact per-file debt inventory and reject malformed counts. (SEC-017)
def load_baseline(path: Path) -> dict[str, int]:
    # Load the exact reviewed per-file ceiling.
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Read only the governed mapping from the versioned envelope.
    baseline = payload.get("maximum_unmigrated_assignments")
    # Reject missing or scalar baselines that cannot bind individual source paths.
    if not isinstance(baseline, dict):
        # Raise one stable failure category for malformed governance bytes.
        raise AssertionError("innerHTML template baseline must contain a path-count mapping")
    # Reject absolute, non-JavaScript, Boolean, negative, or otherwise non-integer inventory entries.
    if any(not isinstance(path, str) or not path.startswith("web/") or not path.endswith(".js") or isinstance(count, bool) or not isinstance(count, int) or count < 0 for path, count in baseline.items()):
        # Fail closed before comparing source or historical debt.
        raise AssertionError("innerHTML template baseline contains an invalid path or count")
    # Return a stable plain mapping for exact and monotonic comparisons.
    return dict(sorted(baseline.items()))


# Reject any candidate baseline that raises or introduces historical debt. (SEC-017)
def validate_baseline_monotonicity(candidate: dict[str, int], previous_path: Path | None) -> None:
    # Skip the PR-only transition proof when a local caller has no immutable base bytes.
    if previous_path is None:
        return
    # Load the exact pull-request base inventory selected by CI.
    previous = load_baseline(previous_path)
    # Collect new positive debt and increases in one focused diagnostic mapping.
    violations = {path: count for path, count in candidate.items() if count > previous.get(path, 0)}
    # Reject every non-monotonic baseline transition before accepting current source.
    if violations:
        # Report only repository paths and counts, never source contents.
        details = ", ".join(f"{path}:{previous.get(path, 0)}->{count}" for path, count in sorted(violations.items()))
        # Raise one stable category for the exact-base CI gate.
        raise AssertionError(f"innerHTML template baseline increased: {details}")


# Compare current debt to the exact checked-in baseline and optional immutable predecessor. (SEC-017)
def validate(root: Path = ROOT, baseline_path: Path = BASELINE_PATH, previous_baseline_path: Path | None = None) -> dict[str, int]:
    # Load and validate the candidate inventory before reading browser source.
    baseline = load_baseline(baseline_path)
    # Prove the candidate inventory never increases relative to the immutable PR base.
    validate_baseline_monotonicity(baseline, previous_baseline_path)
    # Recount current source on every invocation so stale generated evidence cannot pass.
    current = scan_unmigrated(root)
    # Require exact source-to-baseline equality so every reduction burns down the reviewed inventory.
    if current != baseline:
        # Identify every changed path without emitting source contents.
        paths = sorted(set(current) | set(baseline))
        # Format deterministic candidate and observed counts for review.
        details = ", ".join(f"{path}:{baseline.get(path, 0)}!={current.get(path, 0)}" for path in paths if baseline.get(path, 0) != current.get(path, 0))
        # Reject stale reductions, increases, and new files through one exactness boundary.
        raise AssertionError(f"innerHTML template baseline does not match source: {details}")
    # Require Admin to remain completely migrated instead of accepting historical debt there.
    if current.get("web/admin.js", 0):
        # Fail on the highest-risk surface even if a future baseline edit attempts to permit it.
        raise AssertionError("Admin innerHTML writes must use the html tagged template")
    # Read Admin source to govern its secondary markup insertion sink as well as assignments.
    admin_source = (root / "web" / "admin.js").read_text(encoding="utf-8") if (root / "web" / "admin.js").exists() else ""
    # Count every adjacent insertion before comparing it with template-tagged payloads.
    admin_insertions = admin_source.count(".insertAdjacentHTML(")
    # Count only calls whose payload begins with the canonical escape-by-default tag.
    governed_admin_insertions = len(ADMIN_INSERT_ADJACENT_RE.findall(admin_source))
    # Reject any Admin insertion that bypasses the canonical tagged template.
    if admin_insertions != governed_admin_insertions:
        # Keep the diagnostic stable without echoing potentially hostile source text.
        raise AssertionError("Admin insertAdjacentHTML writes must use the html tagged template")
    # Return current counts so tests and logs can prove monotonic state.
    return current


# Run the validator from local and hosted repository gates.
def main(argv=None) -> int:
    # Describe the exact-base option used only by pull-request CI and focused tests.
    parser = argparse.ArgumentParser(description="Validate escape-by-default innerHTML migration governance.")
    # Accept the immutable event-base inventory without resolving a moving Git ref inside the validator.
    parser.add_argument("--previous-baseline", type=Path)
    # Parse caller arguments before scanning tracked source.
    args = parser.parse_args(argv)
    # Validate current source against the reviewed baseline.
    current = validate(previous_baseline_path=args.previous_baseline)
    # Report aggregate debt without dumping source text.
    print(f"innerHTML template validation passed: {sum(current.values())} remaining across {len(current)} files")
    # Return success after every assignment is within its ceiling.
    return 0


# Support direct deterministic execution from CI and developer shells.
if __name__ == "__main__":
    # Exit with the validator result so regressions fail the owning job.
    raise SystemExit(main())
