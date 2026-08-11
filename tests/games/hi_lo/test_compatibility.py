# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Frozen-v1 compatibility and visible rank-price regressions for issue #406."""

# Import hashing for exact LF-stable contract and compatibility evidence.
import hashlib
# Import JSON parsing for descriptors, resources, and compatibility records.
import json
# Import repository-relative path handling without ambient checkout assumptions.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest

# Resolve the repository root from this focused game test module.
ROOT = Path(__file__).resolve().parents[3]
# Pin the additive frozen-v1 Hi-Lo contract.
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "hi_lo.v1.yaml"
# Pin the compatible rank-pricing decision record.
COMPATIBILITY_PATH = ROOT / "contracts" / "compatibility" / "hi-lo-rank-pricing.json"


# Verify additive rank pricing cannot erode frozen-v1 or visible-copy boundaries.
class HiLoCompatibilityTests(unittest.TestCase):
    # Confirm exact contract bytes preserve the legacy scalar and optional additions.
    def test_frozen_v1_contract_and_compatibility_record(self):
        # Read exact bytes so Windows line-ending drift cannot hide behind decoding.
        contract_bytes = OPENAPI_PATH.read_bytes()
        # Decode the LF-governed OpenAPI text for explicit schema anchors.
        contract = contract_bytes.decode("utf-8")
        # Parse the explicit compatible-patch decision record.
        compatibility = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
        # Parse exact-byte digests regenerated from the checked-out contract files.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Parse the game descriptor that owns both compatibility artifacts.
        descriptor = json.loads((ROOT / "modules" / "hi_lo.json").read_text(encoding="utf-8"))
        # Require LF-only bytes so Windows checkout conversion cannot create a stale CI digest.
        self.assertNotIn(b"\r\n", contract_bytes)
        # Preserve the original frozen required list without promoting additive rule fields.
        self.assertIn("required: [guesses, ace_high, suits_break_ties, correct_return_multiplier, tie_return_multiplier]", contract)
        # Reject accidental promotion of the additive server paytable into the required v1 shape.
        self.assertNotIn("required: [guesses, ace_high, suits_break_ties, correct_return_multiplier, tie_return_multiplier, correct_paytable", contract)
        # Require the deprecated integer-two scalar and exact edge declaration.
        for anchor in ("correct_return_multiplier:", "type: integer", "enum: [2]", "deprecated: true", "correct_paytable:", "enum: [0.035]"):
            # Name any missing frozen or additive schema boundary.
            self.assertIn(anchor, contract)
        # Require both extreme and middle exact prices in the frozen contract evidence.
        self.assertIn("'2': {type: number, enum: [0.96]}", contract)
        # Pin the hardest-to-predict middle-rank total return independently.
        self.assertIn("'8': {type: number, enum: [1.93]}", contract)
        # Preserve the declared additive compatibility and unchanged route authority.
        self.assertEqual((True, "unchanged", True), (compatibility["compatibility"]["api_v1_frozen"], compatibility["compatibility"]["routes"], "correct_return_multiplier" in compatibility["response_rules"]["retained"]))
        # Require the game descriptor to own the compatible-patch record.
        self.assertEqual(["contracts/compatibility/hi-lo-rank-pricing.json"], descriptor["compatibility"])
        # Freeze exact LF OpenAPI bytes in the shared digest map.
        self.assertEqual(hashlib.sha256(contract_bytes).hexdigest(), digests["contracts/openapi/hi_lo.v1.yaml"])
        # Freeze the compatibility record independently from the OpenAPI bytes.
        self.assertEqual(hashlib.sha256(COMPATIBILITY_PATH.read_bytes()).hexdigest(), digests["contracts/compatibility/hi-lo-rank-pricing.json"])

    # Confirm both locales display exact server prices and old-server fallback remains bounded.
    def test_frontend_rank_prices_are_exact_and_localized(self):
        # Read the isolated browser module without starting a browser.
        source = (ROOT / "web" / "games" / "hi_lo.js").read_text(encoding="utf-8")
        # Parse English game-owned resources for exact visible price placeholders.
        english = json.loads((ROOT / "web" / "i18n" / "en-US" / "games" / "hi_lo.json").read_text(encoding="utf-8"))
        # Parse Russian resources independently for key and placeholder parity.
        russian = json.loads((ROOT / "web" / "i18n" / "ru-RU" / "games" / "hi_lo.json").read_text(encoding="utf-8"))
        # Require identical localization key ownership before hosted evidence.
        self.assertEqual(sorted(english), sorted(russian))
        # Require exact range and active-price tokens in both governed locales.
        for resource in (english, russian):
            # Preserve both authoritative range placeholders and the literal multiplier suffix.
            self.assertTrue("{min}x" in resource["rules.correctReturn"] and "{max}x" in resource["rules.correctReturn"])
            # Preserve one exact current-rank placeholder and multiplier suffix.
            self.assertIn("{multiplier}x", resource["rules.currentReturn"])
        # Require exact two-decimal formatting before any localized interpolation.
        self.assertIn("const minDisplay = Number(minMultiplier).toFixed(2);", source)
        # Require the maximum endpoint to use the same stable format.
        self.assertIn("const maxDisplay = Number(maxMultiplier).toFixed(2);", source)
        # Require the current visible rank to select only the additive server table.
        self.assertIn("const activeMultiplier = paytable[activeRank];", source)
        # Preserve the deprecated scalar solely as a bounded loading fallback.
        self.assertIn("(rules.correct_return_multiplier || 2)", source)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
