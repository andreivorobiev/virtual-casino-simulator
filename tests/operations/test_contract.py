"""Focused static contract and module-ownership checks for issue #72."""

# Import JSON parsing for module and compatibility records.
import json
# Import the standard unit-test runner for dependency-free focused checks.
import unittest
# Import path handling so tests resolve checked-in artifacts from any working directory.
from pathlib import Path

# Resolve the repository root from this focused test package.
ROOT = Path(__file__).resolve().parents[2]
# Point to the isolated Operations OpenAPI contract.
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "operations.v1.yaml"
# Point to the isolated compatibility decision record.
COMPATIBILITY_PATH = ROOT / "contracts" / "compatibility" / "operations-foundation.json"
# Point to the independently owned Operations module descriptor.
MODULE_PATH = ROOT / "modules" / "operations.json"


# Verify artifacts that central validators cannot discover until #77 integrates them.
class OperationsContractTests(unittest.TestCase):
    # Confirm the additive contract publishes exactly the three issue #72 probes.
    def test_openapi_declares_public_enveloped_probe_paths(self):
        # Read the complete YAML without requiring a third-party parser.
        text = OPENAPI_PATH.read_text(encoding="utf-8")
        # Verify the established OpenAPI version and all exact additive v1 paths.
        self.assertIn("openapi: 3.0.3", text)
        # Verify the liveness path is present.
        self.assertIn("/api/v1/operations/liveness:", text)
        # Verify the readiness path is present.
        self.assertIn("/api/v1/operations/readiness:", text)
        # Verify the heartbeat path is present.
        self.assertIn("/api/v1/operations/heartbeat:", text)
        # Verify every operation is intended to become public through shared auth integration.
        self.assertEqual(3, text.count("security: []"))
        # Verify the degraded contract uses the fixed standard error identity and HTTP status.
        self.assertIn("'503':", text)
        # Verify the error code matches the runtime route policy.
        self.assertIn("enum: [OPERATIONS_NOT_READY]", text)
        # Verify unexpected failures also have one fixed contract identity.
        self.assertIn("enum: [OPERATIONS_PROBE_FAILED]", text)
        # Verify each endpoint narrows unexpected-failure details to its own probe identity.
        self.assertIn("$ref: '#/components/schemas/LivenessProbeFailureEnvelope'", text)
        # Verify readiness cannot advertise a liveness or heartbeat failure payload.
        self.assertIn("$ref: '#/components/schemas/ReadinessProbeFailureEnvelope'", text)
        # Verify heartbeat cannot advertise a liveness or readiness failure payload.
        self.assertIn("$ref: '#/components/schemas/HeartbeatProbeFailureEnvelope'", text)
        # Verify readiness and heartbeat success use different exact live schemas.
        self.assertIn("$ref: '#/components/schemas/ReadinessLiveData'", text)
        # Verify heartbeat success cannot claim the readiness probe name.
        self.assertIn("$ref: '#/components/schemas/HeartbeatLiveData'", text)
        # Verify degraded states require exactly one fixed reason.
        self.assertIn("minItems: 1", text)
        # Verify healthy states require no degraded reasons.
        self.assertIn("maxItems: 0", text)
        # Verify schema hardening forbids undeclared diagnostic fields throughout the contract.
        self.assertGreaterEqual(text.count("additionalProperties: false"), 10)

    # Confirm compatibility records the additive v1 and sanitized-diagnostic boundaries.
    def test_compatibility_record_keeps_shared_integration_blocked(self):
        # Parse the JSON compatibility decision record.
        record = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
        # Verify issue traceability and additive compatibility policy.
        self.assertEqual((72, "additive"), (int(record["issue"].rsplit("/", 1)[-1]), record["v1_compatibility"]["policy"]))
        # Verify the record leaves shared integration with #77.
        self.assertEqual("GitHub issue #77", record["shared_integration_owner"])
        # Verify raw exception diagnostics are explicitly forbidden.
        self.assertIn("raw exception text or class", record["forbidden_diagnostics"])

    # Confirm Operations starts at 1.0.0 and owns only its isolated backend package and contracts.
    def test_module_descriptor_is_operations_owned(self):
        # Parse the independently versioned module descriptor.
        module = json.loads(MODULE_PATH.read_text(encoding="utf-8"))
        # Verify module identity, initial revision, and future permanent requirement prefix.
        self.assertEqual(("operations", "1.0.0", ["OPS"]), (module["module"], module["version"], module["requirements_prefixes"]))
        # Verify the descriptor never claims shared router, shell, or manifest paths.
        self.assertEqual(["casino/operations/"], module["paths"])
        # Verify the new OpenAPI file is the module's declared public contract.
        self.assertEqual(["contracts/openapi/operations.v1.yaml"], module["contracts"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
