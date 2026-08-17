# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Discover and validate the exact API-lane case inventory for #727 slices."""

# Import JSON parsing for the reviewed count and sorted identity baseline.
import json
# Import regular expressions for source-only literal registration discovery.
import re
# Import concrete path handling for the compatibility runner and extracted packages.
from pathlib import Path

# Match only literal central-runner registrations without importing test modules.
_CASE_RE = re.compile(r"\brun_case\(\s*['\"]([^'\"]+)['\"]")


# Return every source file that can own API-lane case registrations.
def api_case_source_paths(run_tests_path, cases_root):
    """Return the compatibility runner plus extracted API case modules."""
    # Normalize the historical compatibility entrypoint to one concrete path.
    runner_path = Path(run_tests_path)
    # Normalize the extracted case-package root before deterministic discovery.
    root_path = Path(cases_root)
    # Include Python case modules in stable path order after the historical runner.
    extracted_paths = sorted(root_path.rglob("*.py")) if root_path.is_dir() else []
    # Return one immutable source inventory for syntax-neutral discovery and policy scans.
    return (runner_path, *extracted_paths)


# Discover every non-Browser literal case identity across the current source topology.
def discover_api_case_ids(source_paths):
    """Return sorted API-lane IDs without importing the runner or case modules."""
    # Accumulate literal identities from each reviewed source path.
    case_ids = []
    # Inspect every compatibility and extracted case source exactly once.
    for source_path in source_paths:
        # Read source as inert UTF-8 text so discovery cannot start listeners or providers.
        source = Path(source_path).read_text(encoding="utf-8")
        # Inspect each literal registration while preserving duplicates for validation.
        for case_id in _CASE_RE.findall(source):
            # Exclude Browser registrations because their independent baseline already owns them.
            if not case_id.startswith("BR-"):
                # Retain the exact literal identity for count, duplication, and sorted-list checks.
                case_ids.append(case_id)
    # Return stable sorted identities so file moves cannot change the acceptance dimension.
    return tuple(sorted(case_ids))


# Validate current source identities against the reviewed before-state baseline.
def validate_api_case_inventory(case_ids, inventory_path):
    """Fail closed unless count and sorted IDs exactly match the reviewed baseline."""
    # Normalize caller identities without dropping duplicates or coercing values.
    current_ids = tuple(case_ids)
    # Parse the checked-in baseline as inert JSON.
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    # Use one value-free diagnostic so mismatches never dump growing case inventories.
    mismatch = "API case inventory does not match the reviewed baseline"
    # Require exactly the two acceptance dimensions authorized by #727.
    if not isinstance(inventory, dict) or set(inventory) != {"count", "case_ids"}:
        # Reject optional fields that could silently weaken or filter the baseline.
        raise AssertionError(mismatch)
    # Read the expected list only after the packet shape is exact.
    expected_ids = inventory["case_ids"]
    # Require a bounded integer count and a string-only identity list.
    if not isinstance(inventory["count"], int) or isinstance(inventory["count"], bool) or not isinstance(expected_ids, list) or not all(isinstance(case_id, str) for case_id in expected_ids):
        # Reject malformed or coercible inventory values before comparing source.
        raise AssertionError(mismatch)
    # Require the baseline itself to be sorted and duplicate-free.
    if expected_ids != sorted(expected_ids) or len(expected_ids) != len(set(expected_ids)):
        # Reject a baseline that could hide reorderings or duplicate registrations.
        raise AssertionError(mismatch)
    # Require current source discovery to be sorted and duplicate-free too.
    if current_ids != tuple(sorted(current_ids)) or len(current_ids) != len(set(current_ids)):
        # Reject duplicate or nondeterministic source registration evidence.
        raise AssertionError(mismatch)
    # Compare both required acceptance dimensions exactly.
    if inventory["count"] != len(current_ids) or tuple(expected_ids) != current_ids:
        # Fail closed on any missing, added, or renamed permanent case.
        raise AssertionError(mismatch)
    # Return the validated immutable inventory for optional runner diagnostics.
    return current_ids
