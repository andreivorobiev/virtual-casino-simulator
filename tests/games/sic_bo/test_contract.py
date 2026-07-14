"""Focused additive v1 contract checks for the unregistered issue #88 slice."""

# Import repository-relative path handling for the game-owned OpenAPI document.
from pathlib import Path
# Import regular expressions for exact route and schema probes.
import re
# Import the dependency-free standard unit-test runner.
import unittest

# Resolve the repository root from this focused test directory.
ROOT = Path(__file__).resolve().parents[3]
# Read the proposed game-owned contract once as UTF-8 text.
CONTRACT = (ROOT / "contracts" / "openapi" / "sic_bo.v1.yaml").read_text(encoding="utf-8")


# Verify the contract remains aligned before #77 makes it catalog-discoverable.
class SicBoContractTests(unittest.TestCase):
    # Confirm only the two additive frozen-v1 routes are declared.
    def test_additive_v1_route_surface(self):
        # Require the repository's established OpenAPI document version.
        self.assertIn("openapi: 3.0.3", CONTRACT)
        # Extract every absolute API route declared at top-level path indentation.
        routes = re.findall(r"^  (/api/v1/[^:]+):$", CONTRACT, re.MULTILINE)
        # Preserve one state read and one complete idempotent round action only.
        self.assertEqual(["/api/v1/games/sic-bo/state", "/api/v1/games/sic-bo/rounds"], routes)
        # Require standard success and error envelope specializations.
        self.assertIn("required: [ok, data]", CONTRACT)
        # Require the shared error-envelope keys without exposing another response shape.
        self.assertIn("required: [ok, error]", CONTRACT)

    # Confirm public action, amount, position, and result boundaries match production.
    def test_runtime_boundaries_are_frozen_in_contract(self):
        # Require the same stable action identity fields validated by the service.
        self.assertIn("required: [action_id, wagers]", CONTRACT)
        # Require the service's maximum action-id length.
        self.assertIn("maxLength: 128", CONTRACT)
        # Require exact two-decimal play-token amounts without silent rounding.
        self.assertIn("multipleOf: 0.01", CONTRACT)
        # Require the complete table count in both metadata and wager boundaries.
        self.assertGreaterEqual(CONTRACT.count("maxItems: 50") + CONTRACT.count("maxProperties: 50"), 3)
        # Require only ascending distinct two-number combinations.
        self.assertIn("combo:(?:1:[2-6]|2:[3-6]|3:[4-6]|4:[5-6]|5:6)", CONTRACT)
        # Require exactly three bounded ordinary die faces.
        self.assertRegex(CONTRACT, r"dice:\s+type: array\s+minItems: 3\s+maxItems: 3\s+items: \{type: integer, minimum: 1, maximum: 6\}")
        # Require the server-owned aggregate outcome vocabulary consumed by localization.
        self.assertIn("outcome: {type: string, enum: [win, push, loss]}", CONTRACT)
        # Require explicit session precedence documentation for compatibility input.
        self.assertIn("Compatibility input overridden by the authenticated session resolver.", CONTRACT)


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
