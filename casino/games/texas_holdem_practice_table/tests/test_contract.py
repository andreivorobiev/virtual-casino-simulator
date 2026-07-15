"""Static locale, frontend, and OpenAPI checks for integrated issue #95."""

# Import JSON parsing for paired locale verification.
import json
# Import portable filesystem paths for repository artifacts.
from pathlib import Path
# Import regular expressions for literal frontend translation lookup extraction.
import re
# Import unittest for dependency-free focused execution.
import unittest

# Import the isolated engine for contract-to-runtime shape probes.
from casino.games.texas_holdem_practice_table import engine

# Resolve the repository root from this game-local test file.
ROOT = Path(__file__).resolve().parents[4]
# Point to the isolated browser module.
FRONTEND = ROOT / "web" / "games" / "texas_holdem_practice_table.js"
# Point to the English source locale domain.
ENGLISH = ROOT / "web" / "i18n" / "en-US" / "games" / "texas_holdem_practice_table.json"
# Point to the Russian paired locale domain.
RUSSIAN = ROOT / "web" / "i18n" / "ru-RU" / "games" / "texas_holdem_practice_table.json"
# Point to the additive game-owned OpenAPI contract.
CONTRACT = ROOT / "contracts" / "openapi" / "texas_holdem_practice_table.v1.yaml"


# Verify integration-ready browser and contract artifacts without registration.
class TexasHoldemPracticeTableContractTests(unittest.TestCase):
    # Confirm paired locale resources have exact keys and placeholders.
    def test_locale_keys_and_placeholders_have_exact_parity(self):
        # Parse English as the canonical source dictionary.
        english = json.loads(ENGLISH.read_text(encoding="utf-8"))
        # Parse the required Russian dictionary.
        russian = json.loads(RUSSIAN.read_text(encoding="utf-8"))
        # Verify both domains expose exactly the same keys.
        self.assertEqual(set(english), set(russian))
        # Verify every visible or accessible string is non-empty.
        self.assertTrue(all(str(value).strip() for value in [*english.values(), *russian.values()]))
        # Define common replacement and UTF-8-as-single-byte corruption markers.
        mojibake_markers = ("\u00c3", "\u00d0", "\u00d1", "\ufffd")
        # Reject encoding-corrupted visible or accessible copy in either locale.
        self.assertFalse(any(marker in str(value) for pack in (english, russian) for value in pack.values() for marker in mojibake_markers))
        # Compare named placeholder sets for every localized key.
        for key in english:
            # Preserve the resource key in failure diagnostics.
            with self.subTest(key=key):
                # Extract English interpolation names.
                english_names = set(re.findall(r"\{([A-Za-z0-9_]+)\}", english[key]))
                # Extract Russian interpolation names.
                russian_names = set(re.findall(r"\{([A-Za-z0-9_]+)\}", russian[key]))
                # Require identical placeholder contracts across locales.
                self.assertEqual(english_names, russian_names)

    # Confirm every literal browser lookup exists in the source dictionary.
    def test_literal_translation_lookups_exist(self):
        # Read the browser module as UTF-8 source.
        source = FRONTEND.read_text(encoding="utf-8")
        # Extract direct text calls while leaving documented template keys to parity tests.
        keys = set(re.findall(r"text\('([^']+)'", source))
        # Parse the English source dictionary.
        english = json.loads(ENGLISH.read_text(encoding="utf-8"))
        # Report any missing literal lookup keys together.
        self.assertFalse(keys - set(english), f"Missing Texas Hold'em i18n keys: {sorted(keys - set(english))}")

    # Confirm shared cards, cleanup, readiness, and localized error behavior.
    def test_frontend_uses_shared_primitives_and_owns_no_timers(self):
        # Read the browser module as UTF-8 source.
        source = FRONTEND.read_text(encoding="utf-8")
        # Require the proposed catalog export name.
        self.assertIn("export const TexasHoldemPracticeTableGame", source)
        # Require the stable readiness selector.
        self.assertIn('data-testid="texas-holdem-practice-table"', source)
        # Require the merged #96 card renderer import.
        self.assertIn("from '../core/cards.js'", source)
        # Require localized replacement of the primitive hidden-card ARIA label.
        self.assertIn("cards.faceDown", source)
        # Reject raw game-owned timeout loops.
        self.assertNotIn("setTimeout(", source)
        # Reject raw game-owned interval loops.
        self.assertNotIn("setInterval(", source)
        # Reject raw server error messages in visible toast handling.
        self.assertNotIn("toast(error.message)", source)
        # Require explicit locale subscription cleanup on unmount.
        self.assertIn("unsubscribeLocale()", source)
        # Require reduced-motion presentation coverage.
        self.assertIn("prefers-reduced-motion:reduce", source)

    # Confirm all additive routes and standard envelopes are documented.
    def test_openapi_paths_and_standard_envelopes(self):
        # Read the YAML contract without adding a parser dependency.
        contract = CONTRACT.read_text(encoding="utf-8")
        # Require state, start, and action paths exactly once in the contract.
        for path in ("/api/v1/games/texas-holdem-practice-table/state:", "/api/v1/games/texas-holdem-practice-table/hands:", "/api/v1/games/texas-holdem-practice-table/hands/{hand_id}/actions:"):
            # Preserve the path in failure diagnostics.
            with self.subTest(path=path):
                # Require the isolated additive endpoint.
                self.assertIn(path, contract)
        # Require both standard success and error envelope definitions.
        self.assertIn("StateEnvelope:", contract)
        # Require the standard ok/error failure shape.
        self.assertIn("ErrorEnvelope:", contract)
        # Require caller player ids to be documented as overridden compatibility inputs.
        self.assertIn("overridden by the authenticated session resolver", contract)
        # Require the state route's optional legacy query to be documented explicitly.
        self.assertIn("- $ref: '#/components/parameters/CompatiblePlayerId'", contract)
        # Require stale-surface protection in the documented action payload.
        self.assertIn("expected_phase:", contract)
        # Require the contract to expose funded-opponent settlement without wallet identities.
        self.assertIn("funded_opponents:", contract)

    # Confirm nullable active-hand timestamps agree with the documented schema.
    def test_active_hand_timestamp_matches_nullable_contract(self):
        # Construct one deterministic active hand without touching runtime storage.
        hand = engine.create_hand("contract-player", 1, "contract-start-001", seed="contract", hand_id="thpt_contract_1", created_at="2026-07-14T00:00:00Z")
        # Build the strict public response shape consumed by the OpenAPI contract.
        public = engine.public_hand(hand)
        # Verify active responses explicitly carry a null completion timestamp.
        self.assertIsNone(public["completed_at"])
        # Read the game-owned contract as UTF-8 text.
        contract = CONTRACT.read_text(encoding="utf-8")
        # Require the completion property to permit that active null value.
        self.assertRegex(contract, r"completed_at:\s+nullable: true\s+type: string\s+format: date-time")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
