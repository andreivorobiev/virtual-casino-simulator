# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused fail-closed proof for issue #323 performance target enforcement."""

# Import deep copying so hostile rows never alias the valid fixture.
import copy
# Import JSON rendering for bounded external evidence fixtures.
import json
# Import temporary directories for caller-owned packets.
import tempfile
# Import the standard unit-test framework.
import unittest
# Import portable paths for checkout and fixture assertions.
from pathlib import Path

# Import the strict baseline schema for canonical fixture identities.
from tests import request_latency_benchmark as baseline
# Import the target gate under direct test.
from tests import performance_target_gate as gate

# Resolve the checkout for workflow-policy inspection.
ROOT = Path(__file__).resolve().parents[2]
# Use one stable full hexadecimal source identity.
SOURCE_COMMIT = "1" * 40


# Build one complete provider packet inside every target.
def valid_evidence(provider: str) -> dict:
    # Build the exact five-by-four grid in canonical order.
    rows = []
    # Visit every governed route family.
    for route_family in baseline.ROUTE_FAMILIES:
        # Visit every governed concurrency level.
        for concurrency in baseline.CONCURRENCY_LEVELS:
            # Append one comfortably passing aggregate row.
            rows.append(
                {
                    "route_family": route_family,  # Bind the fixed route family.
                    "concurrency": concurrency,  # Bind the fixed concurrency identity.
                    "p50_ms": 20.0,  # Stay below the warm-read median ceiling.
                    "p95_ms": 40.0,  # Stay below both tail ceilings.
                    "throughput_rps": 20.0,  # Stay above the strict throughput floor.
                    "errors": 0,  # Preserve complete success.
                    "response_bytes": 1024,  # Preserve one positive aggregate size.
                }
            )
    # Return the exact baseline allowlist.
    return {
        "schema": baseline.EVIDENCE_SCHEMA,  # Bind the accepted measurement schema.
        "source_commit": SOURCE_COMMIT,  # Bind immutable provenance.
        "provider": provider,  # Bind JSON or MySQL.
        "rows": rows,  # Bind the complete grid.
    }


# Exercise accepted evidence, every target boundary, containment, and CI wiring.
class PerformanceTargetGateTests(unittest.TestCase):
    # Prove the complete provider pair produces only sanitized decision facts.
    def test_accepts_complete_exact_source_provider_pair(self) -> None:
        # Evaluate two independent provider fixtures.
        packet = gate.evaluate(valid_evidence("json"), valid_evidence("mysql"))
        # Require the exact output schema and provenance.
        self.assertEqual(packet["schema"], gate.SCHEMA)
        # Require forty validated rows without copying timing samples.
        self.assertEqual(packet["rows_validated"], 40)
        # Require only the two approved providers.
        self.assertEqual(packet["providers"], ["json", "mysql"])
        # Reject raw row material in the accepted packet.
        self.assertNotIn("rows", packet)

    # Prove provider substitution and mixed commits fail closed.
    def test_rejects_duplicate_provider_and_mixed_source(self) -> None:
        # Reject two JSON packets even when each is valid independently.
        with self.assertRaisesRegex(gate.PerformanceTargetError, "providers are invalid"):
            # Evaluate the invalid duplicate-provider pair.
            gate.evaluate(valid_evidence("json"), valid_evidence("json"))
        # Build one valid MySQL packet for provenance tampering.
        mysql = valid_evidence("mysql")
        # Change only its immutable source identity.
        mysql["source_commit"] = "2" * 40
        # Reject mixed-head packets before target evaluation.
        with self.assertRaisesRegex(gate.PerformanceTargetError, "source commits differ"):
            # Evaluate the mismatched pair.
            gate.evaluate(valid_evidence("json"), mysql)

    # Prove every numeric issue target rejects its exact boundary violation.
    def test_rejects_each_latency_and_throughput_target_violation(self) -> None:
        # Enumerate one isolated hostile mutation and expected fixed failure.
        cases = (
            ("current_user", 1, "p50_ms", 100.001, "warm read median"),
            ("slots_state", 1, "p95_ms", 200.001, "warm read tail"),
            ("casino_state", 4, "p95_ms", 250.001, "concurrency-four tail"),
            ("roulette_state", 4, "throughput_rps", 3.37, "concurrency-four throughput"),
        )
        # Exercise each threshold independently.
        for route_family, concurrency, field, value, diagnostic in cases:
            # Name only fixed schema identities in unit output.
            with self.subTest(route_family=route_family, concurrency=concurrency, field=field):
                # Copy a complete valid packet.
                hostile = copy.deepcopy(valid_evidence("json"))
                # Locate the exact governed row.
                row = next(item for item in hostile["rows"] if item["route_family"] == route_family and item["concurrency"] == concurrency)
                # Apply the sole threshold violation.
                row[field] = value
                # Require the stable target-specific rejection.
                with self.assertRaisesRegex(gate.PerformanceTargetError, diagnostic):
                    # Validate the hostile packet.
                    gate.validate_targets(hostile)

    # Prove the gate does not misapply read targets to writes or higher load cohorts.
    def test_preserves_separate_write_and_higher_concurrency_diagnostics(self) -> None:
        # Copy one complete packet for bounded non-target diagnostics.
        evidence = valid_evidence("json")
        # Make the concurrency-four write slower than the read ceiling.
        write_row = next(item for item in evidence["rows"] if item["route_family"] == "boule_spin" and item["concurrency"] == 4)
        # Retain a positive diagnostic write tail outside the read acceptance target.
        write_row["p95_ms"] = 400.0
        # Make one concurrency-eight read slower than the single-request ceiling.
        load_row = next(item for item in evidence["rows"] if item["route_family"] == "casino_state" and item["concurrency"] == 8)
        # Retain a positive high-load diagnostic outside the governed cohorts.
        load_row["p50_ms"] = 250.0
        # Preserve percentile ordering for the hostile-but-valid diagnostic row.
        load_row["p95_ms"] = 500.0
        # Accept because neither row represents an issue-323 target cohort.
        gate.validate_targets(evidence)

    # Prove malformed bytes, oversized inputs, and repository output fail closed.
    def test_load_and_output_containment_fail_closed(self) -> None:
        # Allocate external paths without touching the checkout.
        with tempfile.TemporaryDirectory(prefix="performance-target-unit-") as temporary:
            # Resolve one task-owned input file.
            evidence_path = Path(temporary) / "evidence.json"
            # Write malformed JSON bytes.
            evidence_path.write_text("{", encoding="utf-8")
            # Reject malformed input under one stable diagnostic.
            with self.assertRaisesRegex(gate.PerformanceTargetError, "evidence is invalid"):
                # Load the malformed packet.
                gate.load_evidence(evidence_path)
            # Write one canonical valid packet.
            evidence_path.write_text(json.dumps(valid_evidence("json")), encoding="utf-8")
            # Require complete baseline validation during load.
            self.assertEqual(gate.load_evidence(evidence_path)["provider"], "json")
        # Reject a destination within tracked source.
        with self.assertRaisesRegex(gate.PerformanceTargetError, "outside the checkout"):
            # Resolve one forbidden checkout-contained output.
            gate.resolve_external_output(ROOT / "performance-target-forbidden.json")

    # Prove atomic output leaves no temporary residue and preserves exact bytes.
    def test_atomic_output_replaces_only_after_complete_packet(self) -> None:
        # Allocate an external caller-owned directory.
        with tempfile.TemporaryDirectory(prefix="performance-target-atomic-") as temporary:
            # Resolve the final acceptance packet.
            output = Path(temporary) / "accepted.json"
            # Build one valid decision packet.
            packet = gate.evaluate(valid_evidence("json"), valid_evidence("mysql"))
            # Write the packet atomically.
            gate.write_atomic(output, packet)
            # Require exact deterministic JSON round-trip.
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), packet)
            # Require no task-owned temporary residue.
            self.assertEqual(list(Path(temporary).glob(".performance-target-*.tmp")), [])

    # Prove hosted CI creates both packets, validates them, and retains evidence.
    def test_ci_wires_exact_json_mysql_target_gate(self) -> None:
        # Read the complete CI workflow as policy.
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        # Require the explicit listener-free JSON benchmark.
        self.assertIn("--request-latency json --request-latency-output", workflow)
        # Require MySQL measurement inside the guarded disposable migration lifecycle.
        self.assertIn("--mysql-migrations-live --request-latency mysql --request-latency-output", workflow)
        # Require the exact consumer command after both producers.
        self.assertIn("python tests/performance_target_gate.py", workflow)
        # Require source-bound aggregate evidence retention.
        self.assertIn("request-latency-evidence-${{ github.sha }}", workflow)


# Support focused direct execution.
if __name__ == "__main__":
    # Exit nonzero on any failed assertion.
    unittest.main()
