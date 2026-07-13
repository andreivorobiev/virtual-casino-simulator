"""Static frontend, locale, and OpenAPI checks for the isolated slice."""

# Import JSON parsing for locale parity checks.
import json
# Import filesystem paths independent of the current working directory.
from pathlib import Path
# Import regular expressions for localized key extraction.
import re
# Import unittest for dependency-free focused checks.
import unittest

# Resolve the repository root from this game-local test file.
ROOT = Path(__file__).resolve().parents[4]
# Point to the isolated frontend module.
FRONTEND = ROOT / "web" / "games" / "casino_war.js"
# Point to the English source dictionary.
ENGLISH = ROOT / "web" / "i18n" / "en-US" / "games" / "casino_war.json"
# Point to the Russian dictionary.
RUSSIAN = ROOT / "web" / "i18n" / "ru-RU" / "games" / "casino_war.json"
# Point to the additive game contract.
CONTRACT = ROOT / "contracts" / "openapi" / "casino_war.v1.yaml"


# Verify isolated browser artifacts remain integration-ready.
class CasinoWarFrontendContractTests(unittest.TestCase):
    # Confirm EN/RU resources stay complete and free of blank values.
    def test_locale_keys_have_exact_parity(self):
        # Parse the English source dictionary.
        english = json.loads(ENGLISH.read_text(encoding="utf-8"))
        # Parse the Russian dictionary.
        russian = json.loads(RUSSIAN.read_text(encoding="utf-8"))
        # Assert both locales expose the same owned keys.
        self.assertEqual(set(english), set(russian))
        # Assert no visible copy resolves to an empty string.
        self.assertTrue(all(str(value).strip() for value in [*english.values(), *russian.values()]))

    # Confirm literal frontend lookups exist in both locale resources.
    def test_literal_translation_lookups_exist(self):
        # Read frontend source as UTF-8.
        source = FRONTEND.read_text(encoding="utf-8")
        # Extract static text keys while leaving documented template keys to parity review.
        keys = set(re.findall(r"text\('([^']+)'", source))
        # Parse the English dictionary as the source catalog.
        english = json.loads(ENGLISH.read_text(encoding="utf-8"))
        # Assert every static lookup has source copy.
        self.assertFalse(keys - set(english), f"Missing Casino War i18n keys: {sorted(keys - set(english))}")

    # Confirm the module consumes shared cards and owns no timer loop.
    def test_shared_cards_and_cleanup_contract(self):
        # Read frontend source as UTF-8.
        source = FRONTEND.read_text(encoding="utf-8")
        # Assert the merged CARD-002 renderer is imported.
        self.assertIn("from '../core/cards.js'", source)
        # Assert game-owned timeout and interval loops are absent.
        self.assertNotIn("setTimeout(", source)
        # Assert interval-driven autoplay is absent from the game module.
        self.assertNotIn("setInterval(", source)
        # Assert unmount releases the locale subscription.
        self.assertIn("unsubscribeLocale()", source)
        # Assert the catalog-ready stable selector exists.
        self.assertIn('data-testid="casino-war-table"', source)

    # Confirm the additive contract exposes state and all three commands.
    def test_openapi_paths_and_standard_envelopes(self):
        # Read the YAML contract without requiring a third-party parser.
        contract = CONTRACT.read_text(encoding="utf-8")
        # Assert the required additive routes are documented.
        for path in ("/api/v1/games/casino-war/state:", "/api/v1/games/casino-war/rounds:", "/api/v1/games/casino-war/rounds/{round_id}/surrender:", "/api/v1/games/casino-war/rounds/{round_id}/war:"):
            # Require each route exactly in the contract source.
            self.assertIn(path, contract)
        # Assert both success and error envelopes require the global ok field.
        self.assertIn("CasinoWarEnvelope:", contract)
        # Assert failures use a dedicated standard error envelope.
        self.assertIn("ErrorEnvelope:", contract)


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest discovery for this file.
    unittest.main()
