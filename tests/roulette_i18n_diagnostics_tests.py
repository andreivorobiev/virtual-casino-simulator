# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free proof for Roulette cumulative i18n diagnostics. (I18N-013, TEST-182)"""

# Import pathlib for exact tracked-source assertions.
import pathlib
# Import unittest for dependency-free focused execution.
import unittest

# Import the production Browser-runner formatter used by both cumulative assertions.
from tests.run_tests import roulette_i18n_failure_diagnostic

# Resolve the repository root from this focused test module.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Prove seeded missing keys remain actionable without opening a browser.
class RouletteI18nDiagnosticsTests(unittest.TestCase):
    # Require the runtime snapshot to expose the sorted missing-key inventory beside its count.
    def test_locale_state_exposes_missing_keys(self) -> None:
        # Read the exact production locale runtime.
        source = (ROOT / "web" / "core" / "i18n.js").read_text(encoding="utf-8")
        # Bind the public state to a deterministic sorted snapshot rather than the mutable Set.
        self.assertIn("missingKeyCount: missingKeys.size, missingKeys: [...missingKeys].sort()", source)

    # Force a representative missing key and require every requested diagnostic field.
    def test_seeded_missing_key_names_locale_domains_and_key(self) -> None:
        # Build the exact public shape returned after one Roulette lookup misses.
        state = {"locale": "ru-RU", "loadedDomains": ["common", "games/roulette"], "missingKeyCount": 1, "missingKeys": ["ru-RU|games/roulette|controls.seededMissing"]}
        # Format through the same helper used by both Browser assertions.
        diagnostic = roulette_i18n_failure_diagnostic(state)
        # Require the active locale rather than only the old bare count.
        self.assertIn("locale='ru-RU'", diagnostic)
        # Require loaded domain state for composition-race diagnosis.
        self.assertIn("loadedDomains=['common', 'games/roulette']", diagnostic)
        # Require the exact resource key that triggered fallback.
        self.assertIn("missingKeys=['ru-RU|games/roulette|controls.seededMissing']", diagnostic)

    # Require both cumulative Roulette assertions to retain the shared actionable formatter.
    def test_both_cumulative_assertions_use_diagnostic(self) -> None:
        # Read the exact central Browser runner once.
        source = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Count only assertion-message calls so the helper definition cannot satisfy the gate.
        self.assertEqual(source.count(", roulette_i18n_failure_diagnostic("), 2)


# Execute focused evidence directly for local and CI diagnostics.
if __name__ == "__main__":
    # Preserve normal unittest exit behavior.
    unittest.main()
