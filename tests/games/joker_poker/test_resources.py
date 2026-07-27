"""Resource and canonical descriptor tests for Joker Poker issue #130."""

# Import JSON parsing for locale and descriptor validation.
import json
# Import pathlib for stable repository-relative file reads.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest

# Store ROOT so direct test execution can find canonical artifacts.
ROOT = Path(__file__).resolve().parents[3]


# Verify the descriptor and paired locale resources remain integration-ready.
class JokerPokerResourceTests(unittest.TestCase):
    # Load one repository-relative JSON file.
    def load_json(self, relative_path):
        # Return parsed JSON using UTF-8 resources.
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    # Confirm EN/RU resources expose identical flat keys and placeholders.
    def test_locale_key_parity(self):
        # Load the English resource file.
        english = self.load_json(Path("web/i18n/en-US/games/joker_poker.json"))
        # Load the Russian resource file.
        russian = self.load_json(Path("web/i18n/ru-RU/games/joker_poker.json"))
        # Verify exact key parity.
        self.assertEqual(sorted(english), sorted(russian))
        # Compare interpolation placeholders for every key.
        for key, value in english.items():
            # Extract English placeholder names.
            english_names = sorted(part.split("}", 1)[0] for part in str(value).split("{")[1:])
            # Extract Russian placeholder names.
            russian_names = sorted(part.split("}", 1)[0] for part in str(russian[key]).split("{")[1:])
            # Verify placeholder parity and non-empty copy.
            self.assertEqual(english_names, russian_names, key)
            # Reject blank values in either required locale.
            self.assertTrue(str(value).strip() and str(russian[key]).strip(), key)

    # Confirm the promoted descriptor uses permanent #77 allocations.
    def test_descriptor_is_canonical(self):
        # Load the canonical auto-discovered descriptor.
        descriptor = self.load_json(Path("modules/joker_poker.json"))
        # Verify the accepted module revision and catalog identity.
        self.assertEqual(("1.1.0", "joker_poker"), (descriptor["version"], descriptor["game"]["id"]))
        # Verify #77 assigned the collision-free position and permanent prefix.
        self.assertEqual((300, ["JP"]), (descriptor["game"]["sort_order"], descriptor["requirements_prefixes"]))
        # Verify the additive game contract remains declared.
        self.assertIn("contracts/openapi/joker_poker.v1.yaml", descriptor["contracts"])


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
