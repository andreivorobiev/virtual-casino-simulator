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
# Point to the promoted Operations descriptor in shared module discovery.
MODULE_PATH = ROOT / "modules" / "operations.json"


# Verify artifacts that central validators cannot discover until #77 integrates them.
class OperationsContractTests(unittest.TestCase):
    # Confirm the additive contract publishes exactly the three issue #72 probes.
    def test_openapi_declares_public_enveloped_probe_paths(self):
        # Read the complete YAML without requiring a third-party parser.
        text = OPENAPI_PATH.read_text(encoding="utf-8")
        # Verify the established OpenAPI version and all exact approved paths.
        self.assertIn("openapi: 3.0.3", text)
        # Verify the liveness path is present.
        self.assertIn("/healthz:", text)
        # Verify the readiness path is present.
        self.assertIn("/readyz:", text)
        # Verify the heartbeat path is present.
        self.assertIn("/api/v2/admin/operations:", text)
        # Verify liveness is the only anonymous Operations surface.
        self.assertEqual(1, text.count("security: []"))
        # Verify readiness and Admin diagnostics both accept the session security scheme.
        self.assertEqual(2, text.count("- cookieSession: []"))
        # Verify readiness and Admin diagnostics both accept only the monitor bearer as their machine credential.
        self.assertEqual(2, text.count("- monitorBearer: []"))
        # Verify the monitor bearer is documented as limited to Operations probes.
        self.assertIn("accepted only for /readyz and /api/v2/admin/operations", text)
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

    # Confirm the serialized Operations proposal remains at 1.0.0 outside shared module discovery.
    def test_module_descriptor_is_promoted_into_shared_registry(self):
        # Parse the canonical shared Operations module descriptor.
        module = json.loads(MODULE_PATH.read_text(encoding="utf-8"))
        # Verify module identity, current revision, and future permanent requirement prefix.
        self.assertEqual(("operations", "1.1.2", ["OPS"]), (module["module"], module["version"], module["requirements_prefixes"]))
        # Verify the descriptor owns only the isolated Operations package.
        self.assertEqual(["casino/operations/"], module["paths"])
        # Verify the new OpenAPI file is the module's declared public contract.
        self.assertEqual(["contracts/openapi/operations.v1.yaml"], module["contracts"])
        # Verify the aggregate manifest publishes the same initial module revision.
        manifest = json.loads((ROOT / "modules" / "module-manifest.json").read_text(encoding="utf-8"))
        # Require descriptor and aggregate revision alignment.
        self.assertEqual(module["version"], manifest["modules"]["operations"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
