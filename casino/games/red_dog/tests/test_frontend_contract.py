# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Static frontend, locale, driver, and OpenAPI checks for issue #84."""

# Import JSON parsing for exact locale parity checks.
import json
# Import filesystem paths independently of the current working directory.
from pathlib import Path
# Import regular expressions for translation and placeholder inspection.
import re
# Import unittest for dependency-free focused checks.
import unittest

# Resolve the repository root from this game-local test file.
ROOT = Path(__file__).resolve().parents[4]
# Point to the isolated frontend module.
FRONTEND = ROOT / "web" / "games" / "red_dog.js"
# Point to the English source dictionary.
ENGLISH = ROOT / "web" / "i18n" / "en-US" / "games" / "red_dog.json"
# Point to the Russian dictionary.
RUSSIAN = ROOT / "web" / "i18n" / "ru-RU" / "games" / "red_dog.json"
# Point to the additive game contract.
CONTRACT = ROOT / "contracts" / "openapi" / "red_dog.v1.yaml"
# Point to the game-local catalog driver proposal.
DRIVER = ROOT / "casino" / "games" / "red_dog" / "tests" / "long_driver.py"
# Point to the descriptor and shared-integration handoff.
INTEGRATION = ROOT / "casino" / "games" / "red_dog" / "INTEGRATION.md"
# Match named interpolation placeholders without treating ordinary braces as copy.
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")


# Verify the browser slice remains localized, timer-clean, and integration-ready.
class RedDogFrontendContractTests(unittest.TestCase):
    # Load both required locale resources for repeated assertions.
    @classmethod  # Load immutable source fixtures once for this test class.
    def setUpClass(cls):  # Cache paired locale and frontend source fixtures.
        # Parse the English dictionary as the canonical source locale.
        cls.english = json.loads(ENGLISH.read_text(encoding="utf-8"))
        # Parse the paired Russian dictionary as the required translated locale.
        cls.russian = json.loads(RUSSIAN.read_text(encoding="utf-8"))
        # Read frontend source once for static contract checks.
        cls.source = FRONTEND.read_text(encoding="utf-8")

    # Confirm EN/RU keys, placeholders, and nonblank values remain exact peers.
    def test_locale_keys_and_placeholders_have_exact_parity(self):
        # Require both locale domains to expose the same owned key set.
        self.assertEqual(set(self.english), set(self.russian))
        # Require every player-visible and accessible resource to remain nonblank.
        self.assertTrue(all(str(value).strip() for value in [*self.english.values(), *self.russian.values()]))
        # Compare named placeholders key by key so interpolation cannot leak tokens.
        for key in self.english:
            # Extract source placeholders for this resource.
            english_placeholders = set(PLACEHOLDER_RE.findall(str(self.english[key])))
            # Extract translated placeholders for the paired resource.
            russian_placeholders = set(PLACEHOLDER_RE.findall(str(self.russian[key])))
            # Require exact placeholder parity for safe live locale switching.
            self.assertEqual(english_placeholders, russian_placeholders, key)

    # Confirm every literal frontend lookup exists in both locale dictionaries.
    def test_literal_translation_lookups_exist(self):
        # Extract static game-domain keys while leaving documented template families separate.
        keys = set(re.findall(r"text\('([^']+)'", self.source))
        # Require every static lookup in the canonical source dictionary.
        self.assertFalse(keys - set(self.english), f"Missing Red Dog i18n keys: {sorted(keys - set(self.english))}")
        # Enumerate every dynamic API-to-copy family used by the renderer.
        dynamic_keys = {
            *(f"phase.{value}" for value in ("raise_decision", "settled")),
            *(f"outcome.{value}" for value in ("spread_pending", "consecutive_push", "pair_push", "three_of_a_kind", "spread_win", "spread_loss")),
            *(f"rank.{value}" for value in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")),
            *(f"suit.{value}" for value in ("clubs", "diamonds", "hearts", "spades")),
        }
        # Require every dynamic key in the same source catalog.
        self.assertFalse(dynamic_keys - set(self.english), f"Missing dynamic Red Dog i18n keys: {sorted(dynamic_keys - set(self.english))}")

    # Confirm shared cards are localized and every game-owned lifecycle is timer-clean.
    def test_shared_cards_retry_and_cleanup_contract(self):
        # Require the merged CARD-002 renderer instead of game-owned card glyphs.
        self.assertIn("from '../core/cards.js'", self.source)
        # Require the merged card stylesheet rather than copied primitive CSS.
        self.assertIn("/core/cards.css", self.source)
        # Require default primitive ARIA labels to be replaced through game copy.
        self.assertIn("replace(/aria-label=", self.source)
        # Require uncertain commands to retain their action ids for exact retry.
        self.assertIn("retryActionIds", self.source)
        # Require unmount to release the locale listener and owned stylesheet.
        self.assertIn("unsubscribeLocale()", self.source)
        # Require unmount to remove only the link owned by this route.
        self.assertIn("ownedCardStyleLink.remove()", self.source)
        # Reject raw game-owned timeout loops.
        self.assertNotIn("setTimeout(", self.source)
        # Reject interval-driven autoplay or reveal behavior.
        self.assertNotIn("setInterval(", self.source)
        # Reject unmanaged animation-frame loops.
        self.assertNotIn("requestAnimationFrame(", self.source)
        # Require the catalog-ready stable stage selector.
        self.assertIn('data-testid="red-dog-table"', self.source)
        # Require reduced-motion behavior in the scoped stylesheet.
        self.assertIn("prefers-reduced-motion:reduce", self.source)

    # Confirm browser requests cannot supply or select another player identity.
    def test_frontend_uses_authenticated_session_without_player_override(self):
        # Reject the legacy body helper that accepts caller player overrides.
        self.assertNotIn("withCurrentPlayer", self.source)
        # Reject the legacy query helper that appends a browser-controlled player id.
        self.assertNotIn("currentPlayerPath", self.source)
        # Require direct authenticated state access through cookie credentials.
        self.assertIn("await api(`${API_ROOT}/state`)", self.source)

    # Confirm the additive contract and game-local driver cover every public action.
    def test_openapi_driver_and_descriptor_proposal(self):
        # Read the YAML contract without requiring a third-party parser.
        contract = CONTRACT.read_text(encoding="utf-8")
        # Require state, deal, call, and raise endpoints in the additive namespace.
        for path in ("/api/v1/games/red-dog/state:", "/api/v1/games/red-dog/rounds:", "/api/v1/games/red-dog/rounds/{round_id}/call:", "/api/v1/games/red-dog/rounds/{round_id}/raise:"):
            # Require each exact route in the published contract.
            self.assertIn(path, contract)
        # Require dedicated success and standard error envelopes.
        self.assertIn("RedDogEnvelope:", contract)
        # Require the failed response envelope.
        self.assertIn("ErrorEnvelope:", contract)
        # Keep the published wager floor aligned with two-decimal ledger precision.
        self.assertIn("minimum: 0.01", contract)
        # Keep the published wager ceiling aligned with engine validation.
        self.assertIn("maximum: 100000", contract)
        # Read the game-local long driver proposal.
        driver = DRIVER.read_text(encoding="utf-8")
        # Require only public Red Dog action routes in the driver.
        self.assertIn('/api/v1/games/red-dog/rounds", "POST"', driver)
        # Reject private test seeds and force-result controls from the driver.
        self.assertNotIn("force", driver.casefold())
        # Read the descriptor record after controlled shared integration.
        integration = INTEGRATION.read_text(encoding="utf-8")
        # Require the exact backend registration callable used by catalog discovery.
        self.assertIn('"backend": {"register": "casino.games.red_dog.api:register"}', integration)
        # Require the accepted presentation order from the #77 sequence.
        self.assertIn('"sort_order": 110', integration)
        # Require the canonical shared long-suite driver reference after integration.
        self.assertIn('"tests": {"long_driver": "tests.game_drivers.red_dog:play"}', integration)
        # Require the permanent requirement block to identify its central allocation.
        self.assertIn("Issue #77 allocates these identifiers", integration)


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest discovery for this file.
    unittest.main()
