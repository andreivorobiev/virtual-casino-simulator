"""Resource and proposal descriptor tests for Casino Hold'em issue #139."""

# Import JSON parsing for locale and descriptor validation.
import json
# Import pathlib for stable repository-relative file reads.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest

# Store ROOT so direct test execution can find proposal artifacts.
ROOT = Path(__file__).resolve().parents[3]


# Verify proposal artifacts and paired locale resources remain integration-ready.
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

    # Confirm the descriptor proposal is parked outside auto-discovered modules.
    def test_descriptor_proposal_is_not_autodiscovered(self):
        # Load the proposal descriptor.
        descriptor = self.load_json(Path("codex/tasks/artifacts/issue-139-casino-holdem/casino_holdem.module.proposal.json"))
        # Verify the descriptor is explicitly proposal-only.
        self.assertTrue(descriptor["proposal_only"])
        # Verify it declares the stable game id.
        self.assertEqual("casino_holdem", descriptor["game"]["id"])
        # Verify it points at the additive OpenAPI contract.
        self.assertIn("contracts/openapi/casino_holdem.v1.yaml", descriptor["contracts"])
        # Verify no auto-discovered modules descriptor was added.
        self.assertFalse((ROOT / "modules" / "casino_holdem.json").exists())
        # Verify the descriptor names #77 as the shared integration blocker.
        self.assertIn("#77", descriptor["blocked_on"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
