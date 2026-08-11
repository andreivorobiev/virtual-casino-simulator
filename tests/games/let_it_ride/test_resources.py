# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Locale-resource coverage tests for GitHub issue #134."""

# Import JSON parsing for the paired locale files.
import json
# Import path helpers for repository-relative resource lookup.
from pathlib import Path
# Import the dependency-free standard test runner.
import unittest


# Verify the Let It Ride locale domains remain complete and leakage-free.
class LetItRideResourceTests(unittest.TestCase):
    # Resolve the repository root from this focused test file.
    root = Path(__file__).resolve().parents[3]

    # Load one game-owned locale domain.
    def load(self, locale):
        # Parse the requested JSON resource file.
        return json.loads((self.root / "web" / "i18n" / locale / "games" / "let_it_ride.json").read_text(encoding="utf-8"))

    # Confirm both locales expose identical keys.
    def test_locale_key_sets_match(self):
        # Load the English resource domain.
        english = self.load("en-US")
        # Load the Russian resource domain.
        russian = self.load("ru-RU")
        # Verify no raw fallback key can appear because a locale is missing entries.
        self.assertEqual(set(english), set(russian))

    # Confirm Russian copy is not English fallback text for player-facing values.
    def test_russian_domain_has_no_obvious_english_leakage(self):
        # Load the Russian resource domain.
        russian = self.load("ru-RU")
        # Inspect values that should be natural localized prose.
        prose_values = [value for key, value in russian.items() if not key.startswith("rank.") and not key.startswith("suit.")]
        # Verify common English table words are not leaked as fallback copy.
        self.assertFalse(any("play tokens" in value.lower() or "wager" in value.lower() for value in prose_values))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
