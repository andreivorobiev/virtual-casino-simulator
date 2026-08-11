# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Resource and canonical descriptor tests for Pai Gow Poker issue #138."""

# Import JSON parsing for locale and descriptor validation.
import json
# Import pathlib for stable repository-relative file reads.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest

# Store ROOT so direct test execution can find canonical artifacts.
ROOT = Path(__file__).resolve().parents[3]


# Verify canonical artifacts and paired locale resources remain integration-ready.
class PaiGowPokerResourceTests(unittest.TestCase):
    # Load one repository-relative JSON file.
    def load_json(self, relative_path):
        # Return parsed JSON using UTF-8 resources.
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    # Confirm EN/RU resources expose identical flat keys and placeholders.
    def test_locale_key_parity(self):
        # Load the English resource file.
        english = self.load_json(Path("web/i18n/en-US/games/pai_gow_poker.json"))
        # Load the Russian resource file.
        russian = self.load_json(Path("web/i18n/ru-RU/games/pai_gow_poker.json"))
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
        descriptor = self.load_json(Path("modules/pai_gow_poker.json"))
        # Verify the descriptor revision stays consistent with the canonical version manifest rather than a brittle literal.
        manifest = self.load_json(Path("modules/module-manifest.json"))
        self.assertEqual(manifest["modules"]["pai_gow_poker"], descriptor["version"])
        # Verify it declares the stable game id.
        self.assertEqual("pai_gow_poker", descriptor["game"]["id"])
        # Verify it points at the additive OpenAPI contract.
        self.assertIn("contracts/openapi/pai_gow_poker.v1.yaml", descriptor["contracts"])
        # Verify issue #73 allocated the collision-free catalog position.
        self.assertEqual(310, descriptor["game"]["sort_order"])
        # Verify the permanent requirement prefix replaces the proposal marker.
        self.assertEqual(["PGP"], descriptor["requirements_prefixes"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
