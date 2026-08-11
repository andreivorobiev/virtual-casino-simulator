# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Frozen-v1 compatibility and browser-resource regressions for issue #409."""

# Import hashing for exact LF-stable contract and decision-record evidence.
import hashlib
# Import JSON parsing for manifests, resources, and compatibility artifacts.
import json
# Import repository-relative path handling without ambient working-directory assumptions.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest

# Resolve the repository root from this focused test module.
ROOT = Path(__file__).resolve().parents[3]
# Pin the frozen Andar Bahar OpenAPI artifact.
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "andar_bahar.v1.yaml"
# Pin the compatible-patch decision record.
COMPATIBILITY_PATH = ROOT / "contracts" / "compatibility" / "andar-bahar-side-pricing.json"


# Verify the additive contract and localized frontend remain compatible and reviewable.
class AndarBaharCompatibilityTests(unittest.TestCase):
    # Confirm exact-byte contract evidence and the frozen scalar boundary.
    def test_frozen_v1_contract_and_compatibility_record(self):
        # Read exact contract bytes so line-ending drift cannot hide behind text normalization.
        contract_bytes = OPENAPI_PATH.read_bytes()
        # Decode the LF-governed OpenAPI text for schema anchor assertions.
        contract = contract_bytes.decode("utf-8")
        # Parse the explicit compatible-patch record.
        compatibility = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
        # Parse the exact-byte digest map used by contract validation.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Parse the module descriptor that owns both contract artifacts.
        descriptor = json.loads((ROOT / "modules" / "andar_bahar.json").read_text(encoding="utf-8"))
        # Require LF-only bytes so Windows checkout conversion cannot generate a stale CI digest.
        self.assertNotIn(b"\r\n", contract_bytes)
        # Keep the additive side table optional while preserving the required legacy scalar.
        self.assertIn("required: [sides, deal_order, match_rank_only, return_multiplier]", contract)
        # Reject accidental promotion of the additive field into the frozen required list.
        self.assertNotIn("required: [sides, deal_order, match_rank_only, return_multiplier, return_multipliers]", contract)
        # Require deprecated integer-two scalar and both exact side-price schema values.
        for anchor in ("deprecated: true", "return_multipliers:", "enum: [1.9]", "enum: [2.0]"):
            # Name any missing frozen or additive schema boundary.
            self.assertIn(anchor, contract)
        # Require explicit unchanged v1 authority and retained scalar evidence.
        self.assertEqual((True, "unchanged", True), (compatibility["compatibility"]["api_v1_frozen"], compatibility["compatibility"]["routes"], "return_multiplier" in compatibility["response_rules"]["retained"]))
        # Require the game descriptor to own the new decision record.
        self.assertEqual(["contracts/compatibility/andar-bahar-side-pricing.json"], descriptor["compatibility"])
        # Freeze exact LF OpenAPI bytes in the shared contract digest artifact.
        self.assertEqual(hashlib.sha256(contract_bytes).hexdigest(), digests["contracts/openapi/andar_bahar.v1.yaml"])
        # Freeze the exact compatibility record independently.
        self.assertEqual(hashlib.sha256(COMPATIBILITY_PATH.read_bytes()).hexdigest(), digests["contracts/compatibility/andar-bahar-side-pricing.json"])

    # Confirm localized copy, old-server fallback, and mobile fixed-control clearance remain source-owned.
    def test_frontend_side_prices_and_mobile_clearance_contract(self):
        # Read the isolated browser module without executing a browser.
        source = (ROOT / "web" / "games" / "andar_bahar.js").read_text(encoding="utf-8")
        # Parse both governed game resource dictionaries.
        en = json.loads((ROOT / "web" / "i18n" / "en-US" / "games" / "andar_bahar.json").read_text(encoding="utf-8"))
        # Parse Russian copy independently for exact key parity.
        ru = json.loads((ROOT / "web" / "i18n" / "ru-RU" / "games" / "andar_bahar.json").read_text(encoding="utf-8"))
        # Require identical localization keys before hosted visual evidence.
        self.assertEqual(sorted(en), sorted(ru))
        # Require both price placeholders in both visible rule translations.
        self.assertTrue(all("{andar}" in resource["rules.return"] and "{bahar}" in resource["rules.return"] for resource in (en, ru)))
        # Require the additive table with a frozen-scalar fallback for old compatible servers.
        self.assertIn("rules.return_multipliers || { andar: rules.return_multiplier || 2, bahar: rules.return_multiplier || 2 }", source)
        # Require exact two-decimal formatting for the authoritative Andar player-facing price.
        self.assertIn("const andarPrice = Number(multipliers.andar).toFixed(2);", source)
        # Require exact two-decimal formatting for the authoritative Bahar player-facing price.
        self.assertIn("const baharPrice = Number(multipliers.bahar).toFixed(2);", source)
        # Require i18n interpolation to consume only the preformatted exact display tokens.
        self.assertIn("text('rules.return', { andar: andarPrice, bahar: baharPrice })", source)
        # Reject the obsolete one-price interpolation path.
        self.assertNotIn("text('rules.return', { multiplier })", source)
        # Reserve a bounded mobile feedback column and bottom clearance within the game-owned stylesheet.
        self.assertIn(".andar-shell{padding-bottom:64px}", source)
        # Keep the fixed reporting affordance bounded so its reserved column is exact.
        self.assertIn("body:has(.andar-shell) .report-problem-fab{width:144px", source)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
