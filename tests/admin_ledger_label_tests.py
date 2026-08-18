# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free Admin ledger-label source, resource, and wiring regression."""

# Import JSON parsing for installed Admin locale resources.
import json
# Import regular expressions for extracting the production rule table.
import re
# Import the standard test framework used by the central API suite.
import unittest
# Import repository-relative paths without depending on the caller's directory.
from pathlib import Path

# Resolve the repository root from this focused suite.
ROOT = Path(__file__).resolve().parents[1]
# Name the exact production helper source.
HELPER_PATH = ROOT / "web" / "core" / "admin_labels.js"
# Name the exact Admin surface source.
ADMIN_PATH = ROOT / "web" / "admin.js"
# Name the extracted Ledger-tab module source.
LEDGER_PATH = ROOT / "web" / "admin" / "ledger.js"


# Verify ADMIN-027 and TEST-132 without opening a listener or browser.
class AdminLedgerLabelTests(unittest.TestCase):
    """Prove production classification, locale parity, and both Admin render paths."""

    # Load immutable production inputs once for the focused class.
    @classmethod
    def setUpClass(cls):
        # Read the listener-free helper source.
        cls.helper_source = HELPER_PATH.read_text(encoding="utf-8")
        # Read the Admin renderer source.
        cls.admin_source = ADMIN_PATH.read_text(encoding="utf-8")
        # Read the extracted Ledger renderer source.
        cls.ledger_source = LEDGER_PATH.read_text(encoding="utf-8")
        # Join both Admin-owned sources for behavior-level occurrence checks.
        cls.surface_source = f"{cls.admin_source}\n{cls.ledger_source}"
        # Extract the ordered suffix-to-resource table from production JavaScript.
        cls.rules = re.findall(r"\['([^']+)', '(ledger\.events\.[^']+)'\]", cls.helper_source)
        # Load the canonical English Admin resources.
        cls.english = json.loads((ROOT / "web" / "i18n" / "en-US" / "admin.json").read_text(encoding="utf-8"))
        # Load the reviewed Russian Admin resources.
        cls.russian = json.loads((ROOT / "web" / "i18n" / "ru-RU" / "admin.json").read_text(encoding="utf-8"))

    # Mirror the production classifier from its extracted ordered data table.
    def classify(self, event_type: str) -> str:
        # Normalize the test event exactly as the JavaScript helper does.
        canonical = str(event_type or "").strip().upper()
        # Return the first matching reviewed resource key.
        for suffix, key in self.rules:
            # Respect production rule ordering for overlapping suffixes.
            if canonical.endswith(suffix):
                # Return the reviewed locale resource identity.
                return key
        # Preserve the production fail-closed unknown-event fallback.
        return "ledger.events.other"

    # Require every reviewed production rule to resolve in both installed locales.
    def test_locale_resource_parity(self):
        # Require a substantial explicit rule set rather than one generic debit/credit heuristic.
        self.assertGreaterEqual(len(self.rules), 30)
        # Collect the production suffixes so every identity has one deterministic position.
        suffixes = [suffix for suffix, _key in self.rules]
        # Reject duplicate suffixes that would obscure classification intent.
        self.assertEqual(len(suffixes), len(set(suffixes)))
        # Collect unique production rule keys plus the deliberate fallback.
        keys = sorted({key for _suffix, key in self.rules} | {"ledger.events.other"})
        # Inspect every production label resource.
        for key in keys:
            # Require non-empty canonical English operator copy.
            self.assertTrue(self.english.get(key, "").strip(), key)
            # Require non-empty reviewed Russian operator copy.
            self.assertTrue(self.russian.get(key, "").strip(), key)

    # Require representative reported and future identities to classify safely.
    def test_reported_and_fallback_classification(self):
        # Prove the exact reported payout example receives its reviewed action.
        self.assertEqual(self.classify("BINGO_PAYOUT_CREDIT"), "ledger.events.payoutCredit")
        # Prove a ticket purchase does not collapse into the generic purchase fallback.
        self.assertEqual(self.classify("KENO_TICKET_PURCHASED"), "ledger.events.ticketPurchased")
        # Prove the more-specific insurance credit wins before generic credit.
        self.assertEqual(self.classify("BLACKJACK_INSURANCE_CREDIT"), "ledger.events.insuranceCredit")
        # Prove future unrecognized identities never surface a source enum.
        self.assertEqual(self.classify("FUTURE_LEDGER_EVENT"), "ledger.events.other")
        # Prove the reported Russian payout copy is genuinely localized.
        self.assertEqual(self.russian[self.classify("BINGO_PAYOUT_CREDIT")], "Выплата начислена")

    # Require Dashboard and full Ledger to use the shared locale-backed path.
    def test_dashboard_and_ledger_wiring(self):
        # Require exactly two stable event-cell evidence hooks, one per Admin surface.
        self.assertEqual(self.surface_source.count('data-testid="admin-ledger-event"'), 2)
        # Require both surfaces to call the locale-bound shared helper.
        self.assertEqual(self.surface_source.count("ledgerEventLabel(row.transaction_type, row.game)"), 2)
        # Leave only the separately mapped practice-opponent fallback outside the two governed ledger surfaces.
        self.assertEqual(self.surface_source.count("humanLabel(row.transaction_type)"), 1)
        # Require the listener-free helper to be imported from the application-owned shared path.
        self.assertIn("from './core/admin_labels.js'", self.admin_source)

    # Require the first Admin split to keep one small dispatcher binding and readable module source.
    def test_ledger_tab_module_boundary(self):
        # Require the dispatcher to import the extracted Ledger factory exactly once.
        self.assertEqual(self.admin_source.count("from './admin/ledger.js'"), 1)
        # Reject the retired monolith-owned renderer implementation.
        self.assertNotIn("async function ledger()", self.admin_source)
        # Require the extracted module to own the frozen Ledger API call exactly once.
        self.assertEqual(self.ledger_source.count("/api/v1/admin/ledger?limit=500"), 1)
        # Keep every Ledger module source line within the governed review-width ceiling.
        self.assertLessEqual(max(map(len, self.ledger_source.splitlines())), 200)


# Support direct focused execution outside the central runner.
if __name__ == "__main__":
    # Run the focused class with normal unittest reporting.
    unittest.main()
