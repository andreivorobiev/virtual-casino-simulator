# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Resource parity checks for the isolated Caribbean Stud draft."""

# Import JSON parsing for paired locale resources.
import json
# Import regular expressions for placeholder and mojibake checks.
import re
# Import the dependency-free standard test runner.
import unittest
# Import path helpers for repository-relative resource reads.
from pathlib import Path

# Resolve the repository root from this focused test file.
ROOT = Path(__file__).resolve().parents[3]
# Resolve the English game-owned resource file.
EN_PATH = ROOT / "web" / "i18n" / "en-US" / "games" / "caribbean_stud.json"
# Resolve the Russian game-owned resource file.
RU_PATH = ROOT / "web" / "i18n" / "ru-RU" / "games" / "caribbean_stud.json"
# Match named interpolation placeholders in localized strings.
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


# Verify the two required locale files stay aligned.
class CaribbeanStudResourceTests(unittest.TestCase):
    # Load one JSON resource and its raw text.
    def load_resource(self, path):
        # Read the file as UTF-8 text.
        raw = path.read_text(encoding="utf-8")
        # Parse the JSON payload.
        parsed = json.loads(raw)
        # Return both forms for assertions.
        return raw, parsed

    # Confirm EN/RU keys, placeholders, and encoding stay compatible.
    def test_locale_parity_and_encoding(self):
        # Load the English resource.
        english_raw, english = self.load_resource(EN_PATH)
        # Load the Russian resource.
        russian_raw, russian = self.load_resource(RU_PATH)
        # Verify both locales expose the exact same keys.
        self.assertEqual(sorted(english), sorted(russian))
        # Check every localized value.
        for key, english_value in english.items():
            # Compare placeholder names independent of language word order.
            self.assertEqual(sorted(PLACEHOLDER_RE.findall(english_value)), sorted(PLACEHOLDER_RE.findall(russian[key])), key)
            # Require non-empty English copy.
            self.assertTrue(str(english_value).strip(), key)
            # Require non-empty Russian copy.
            self.assertTrue(str(russian[key]).strip(), key)
        # Reject common mojibake sequences from both raw resources.
        self.assertNotRegex(english_raw + russian_raw, r"Ã|Ð.|Ñ.|ï¿½")
        # Require explicit play-token framing in both locales.
        self.assertIn("play tokens", english["tokens.amount"])
        # Require the canonical Russian play-token phrase in the token formatter. (I18N-011)
        self.assertIn("игровых токенов", russian["tokens.amount"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
