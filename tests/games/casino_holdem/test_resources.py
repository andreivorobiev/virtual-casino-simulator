"""Resource and canonical descriptor tests for Casino Hold'em issue #139."""

# Import JSON parsing for locale and descriptor validation.
import json
# Import pathlib for stable repository-relative file reads.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest

# Store ROOT so direct test execution can find canonical artifacts.
ROOT = Path(__file__).resolve().parents[3]


# Verify canonical artifacts and paired locale resources remain integration-ready.
class CasinoHoldemResourceTests(unittest.TestCase):
    # Load one repository-relative JSON file.
    def load_json(self, relative_path):
        # Return parsed JSON using UTF-8 resources.
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    # Confirm EN/RU resources expose identical flat keys and placeholders.
    def test_locale_key_parity(self):
        # Load the English resource file.
        english = self.load_json(Path("web/i18n/en-US/games/casino_holdem.json"))
        # Load the Russian resource file.
        russian = self.load_json(Path("web/i18n/ru-RU/games/casino_holdem.json"))
        # Verify exact key parity.
        self.assertEqual(sorted(english), sorted(russian))
        # Compare interpolation placeholders for every key.
        for key, value in english.items():
            # Extract English placeholder names.
            english_names = sorted(part.split("}", 1)[0] for part in str(value).split("{")[1:])
            # Extract Russian placeholder names.
            russian_names = sorted(part.split("}", 1)[0] for part in str(russian[key]).split("{")[1:])
            # Verify placeholder parity.
            self.assertEqual(english_names, russian_names, key)
            # Verify neither locale is blank.
            self.assertTrue(str(value).strip() and str(russian[key]).strip(), key)

    # Confirm the promoted descriptor is discoverable with its permanent allocation.
    def test_descriptor_is_canonical(self):
        # Load the canonical descriptor.
        descriptor = self.load_json(Path("modules/casino_holdem.json"))
        # Verify the descriptor uses the accepted module revision.
        self.assertEqual("1.0.0", descriptor["version"])
        # Verify it declares the stable game id.
        self.assertEqual("casino_holdem", descriptor["game"]["id"])
        # Verify it points at the additive OpenAPI contract.
        self.assertIn("contracts/openapi/casino_holdem.v1.yaml", descriptor["contracts"])
        # Verify #77 allocated the collision-free catalog position.
        self.assertEqual(290, descriptor["game"]["sort_order"])
        # Verify the permanent requirement prefix replaces the proposal marker.
        self.assertEqual(["CH"], descriptor["requirements_prefixes"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
