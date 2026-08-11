# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Fail closed unless exact-source JSON and MySQL latency evidence meets #323."""

# Import argument parsing for the explicit hosted-evidence command.
import argparse
# Import JSON parsing and deterministic accepted-packet rendering.
import json
# Import atomic file replacement primitives.
import os
# Import portable paths for external evidence containment.
from pathlib import Path
# Import temporary-file allocation beside the caller-owned output.
import tempfile

# Reuse the baseline's strict evidence schema instead of creating a weaker parser.
from tests import request_latency_benchmark as baseline

# Resolve the checkout so evidence files cannot be written into tracked source.
ROOT = Path(__file__).resolve().parents[1]
# Version the target decision independently from the measurement schema.
SCHEMA = "performance-target-gate/v1"
# Bound every input before parsing untrusted hosted artifact bytes.
MAX_EVIDENCE_BYTES = 1_048_576
# Preserve the issue's warm authenticated-read median target.
READ_P50_MAX_MS = 100.0
# Preserve the issue's warm authenticated-read tail target.
READ_P95_MAX_MS = 200.0
# Preserve the issue's concurrency-four tail target for reads and writes.
CONCURRENCY_FOUR_P95_MAX_MS = 250.0
# Require throughput to exceed the issue's recorded 3.37-rps baseline.
CONCURRENCY_FOUR_THROUGHPUT_MIN_RPS = 3.37
# Require exactly the two isolated providers used by the accepted baseline.
PROVIDERS = ("json", "mysql")


# Normalize every target failure to one stable exception type.
class PerformanceTargetError(RuntimeError):
    """Stable failure raised for invalid or out-of-budget aggregate evidence."""


# Reject a source-contained output before any evidence is read.
def resolve_external_output(path: str | Path) -> Path:
    # Resolve without requiring the future file to exist.
    output = Path(path).expanduser().resolve()
    # Reject the checkout and every descendant as an evidence destination.
    if output == ROOT or ROOT in output.parents:
        # Keep generated evidence outside tracked or untracked repository state.
        raise PerformanceTargetError("performance target output must be outside the checkout")
    # Require an existing caller-owned parent rather than creating arbitrary paths.
    if not output.parent.is_dir():
        # Fail closed when the destination boundary is absent.
        raise PerformanceTargetError("performance target output parent is unavailable")
    # Return the validated external path.
    return output


# Load one bounded aggregate packet without reflecting its contents in failures.
def load_evidence(path: str | Path) -> dict:
    # Resolve the input independently of the current directory.
    evidence_path = Path(path).expanduser().resolve()
    # Require one ordinary file before reading bytes.
    if not evidence_path.is_file() or evidence_path.is_symlink():
        # Reject absent, directory, or link inputs uniformly.
        raise PerformanceTargetError("performance target evidence is unavailable")
    # Reject oversized input before JSON parsing.
    if evidence_path.stat().st_size > MAX_EVIDENCE_BYTES:
        # Keep resource use bounded and diagnostics value-free.
        raise PerformanceTargetError("performance target evidence is oversized")
    # Parse one UTF-8 JSON object under a fixed failure boundary.
    try:
        # Decode the complete bounded packet.
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    # Normalize decoding, parsing, and filesystem races.
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        # Refuse malformed evidence without echoing its bytes or path.
        raise PerformanceTargetError("performance target evidence is invalid") from None
    # Reuse the baseline's complete schema, grid, type, and privacy allowlist.
    try:
        # Validate before reading target values.
        baseline.validate_evidence(evidence)
    # Hide baseline detail behind the target gate's stable boundary.
    except baseline.RequestLatencyBenchmarkError:
        # Reject any malformed or incomplete baseline packet.
        raise PerformanceTargetError("performance target evidence is invalid") from None
    # Return only fully validated aggregate evidence.
    return evidence


# Enforce the fixed issue targets for one validated provider packet.
def validate_targets(evidence: dict) -> None:
    # Inspect every complete route/concurrency row.
    for row in evidence["rows"]:
        # Apply the warm single-request budget only to authenticated read families.
        if row["route_family"] in baseline.READ_ROUTE_FAMILIES and row["concurrency"] == 1:
            # Reject a median above the approved warm-read target.
            if float(row["p50_ms"]) > READ_P50_MAX_MS:
                # Keep the failure free of provider, route, or timing detail.
                raise PerformanceTargetError("warm read median target failed")
            # Reject a tail above the approved warm-read target.
            if float(row["p95_ms"]) > READ_P95_MAX_MS:
                # Keep the failure low-cardinality for shared-runner logs.
                raise PerformanceTargetError("warm read tail target failed")
        # Apply the concurrency-four budget only to authenticated game-state reads.
        if row["route_family"] in baseline.READ_ROUTE_FAMILIES and row["concurrency"] == 4:
            # Reject a tail above the concurrency-four target.
            if float(row["p95_ms"]) > CONCURRENCY_FOUR_P95_MAX_MS:
                # Preserve one fixed target diagnostic.
                raise PerformanceTargetError("concurrency-four tail target failed")
            # Require throughput to improve on the recorded baseline strictly.
            if float(row["throughput_rps"]) <= CONCURRENCY_FOUR_THROUGHPUT_MIN_RPS:
                # Preserve one fixed target diagnostic.
                raise PerformanceTargetError("concurrency-four throughput target failed")


# Validate the exact provider pair and build one sanitized acceptance packet.
def evaluate(json_evidence: dict, mysql_evidence: dict) -> dict:
    # Bind packets by their declared provider rather than caller order alone.
    packets = {json_evidence["provider"]: json_evidence, mysql_evidence["provider"]: mysql_evidence}
    # Require exactly one JSON and one MySQL packet.
    if tuple(sorted(packets)) != PROVIDERS:
        # Reject duplicate or substituted providers.
        raise PerformanceTargetError("performance target providers are invalid")
    # Require both packets to describe the same immutable checkout.
    if packets["json"]["source_commit"] != packets["mysql"]["source_commit"]:
        # Reject mixed-head evidence without exposing either commit.
        raise PerformanceTargetError("performance target source commits differ")
    # Enforce the fixed targets against both isolated providers.
    for provider in PROVIDERS:
        # Validate one complete provider packet.
        validate_targets(packets[provider])
    # Return only the bounded decision facts, not timing samples.
    return {
        "schema": SCHEMA,  # Identify the fail-closed decision schema.
        "source_commit": packets["json"]["source_commit"],  # Bind the exact synthetic merge or protected-main checkout.
        "providers": list(PROVIDERS),  # Record the complete provider inventory.
        "rows_validated": 40,  # Record the fixed two-provider five-by-four grid.
        "targets": {
            "read_p50_max_ms": READ_P50_MAX_MS,  # Publish the accepted median ceiling.
            "read_p95_max_ms": READ_P95_MAX_MS,  # Publish the accepted read-tail ceiling.
            "concurrency_four_p95_max_ms": CONCURRENCY_FOUR_P95_MAX_MS,  # Publish the concurrency-four tail ceiling.
            "concurrency_four_throughput_min_rps": CONCURRENCY_FOUR_THROUGHPUT_MIN_RPS,  # Publish the strict throughput floor.
        },
    }


# Replace one external acceptance packet atomically.
def write_atomic(output: Path, packet: dict) -> None:
    # Render deterministic UTF-8 with one terminal newline.
    encoded = (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode("utf-8")
    # Allocate the temporary file beside its final destination.
    descriptor, temporary_name = tempfile.mkstemp(prefix=".performance-target-", suffix=".tmp", dir=str(output.parent))
    # Resolve the temporary path for cleanup on every branch.
    temporary = Path(temporary_name)
    # Protect both descriptor and temporary residue cleanup.
    try:
        # Open only the exact allocated descriptor.
        with os.fdopen(descriptor, "wb") as stream:
            # Write the complete deterministic packet.
            stream.write(encoded)
            # Flush Python buffering before durability sync.
            stream.flush()
            # Sync the file before replacement.
            os.fsync(stream.fileno())
        # Replace the final packet only after successful validation and write.
        os.replace(temporary, output)
    # Remove any temporary residue on failure.
    finally:
        # Unlink only the task-owned temporary file when replacement did not consume it.
        if temporary.exists():
            # Remove the bounded temporary artifact.
            temporary.unlink()


# Execute the explicit hosted target gate.
def main() -> int:
    # Build the dependency-free command interface.
    parser = argparse.ArgumentParser()
    # Require the JSON-provider aggregate packet.
    parser.add_argument("--json-evidence", required=True)
    # Require the MySQL-provider aggregate packet.
    parser.add_argument("--mysql-evidence", required=True)
    # Require one caller-owned external acceptance destination.
    parser.add_argument("--output", required=True)
    # Parse all three explicit paths.
    arguments = parser.parse_args()
    # Resolve output containment before reading inputs.
    output = resolve_external_output(arguments.output)
    # Load and validate both complete provider packets.
    packet = evaluate(load_evidence(arguments.json_evidence), load_evidence(arguments.mysql_evidence))
    # Publish the sanitized exact-source acceptance atomically.
    write_atomic(output, packet)
    # Report only the fixed accepted cardinality.
    print("Performance targets passed for 40 aggregate rows.")
    # Return success after durable output replacement.
    return 0


# Support only explicit command execution.
if __name__ == "__main__":
    # Normalize every governed failure to one fixed stderr line and nonzero status.
    try:
        # Exit with the explicit command result.
        raise SystemExit(main())
    # Suppress paths, commits, providers, and timing values from failures.
    except PerformanceTargetError:
        # Emit one stable failure line.
        print("performance target gate failed", file=__import__("sys").stderr)
        # Fail closed after the stable diagnostic.
        raise SystemExit(1)
