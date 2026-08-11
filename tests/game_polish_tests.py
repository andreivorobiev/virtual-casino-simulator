# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free acceptance for the cross-game copy and keyboard-focus repair."""

# Import JSON parsing so canonical locale resources can be checked without a browser.
import json
# Import unittest so the focused contract joins the central API validation runner.
import unittest
# Import paths so every assertion reads files from the checked repository root.
from pathlib import Path

# Resolve the repository root once for deterministic resource and stylesheet reads.
ROOT = Path(__file__).resolve().parents[1]


# Verify the exact copy and focus contract introduced by TEST-117.
class GamePolishTests(unittest.TestCase):
    # Load one canonical locale resource as UTF-8 JSON.
    def resource(self, locale, game):
        # Return the parsed game-owned dictionary without starting the application.
        return json.loads((ROOT / "web" / "i18n" / locale / "games" / f"{game}.json").read_text(encoding="utf-8"))

    # Require corrected return semantics, identifier privacy, and complete Russian terminology.
    def test_exact_localized_copy_contract(self):
        # Load every resource changed by the bounded copy repair.
        resources = {(locale, game): self.resource(locale, game) for locale in ("en-US", "ru-RU") for game in ("baccarat", "caribbean_stud", "joker_poker", "multi_hand_video_poker", "roulette", "slots")}
        # Require Caribbean Stud to use the same Call term as its public action.
        self.assertEqual(resources[("en-US", "caribbean_stud")]["paytable.title"], "Call payout schedule")
        # Require the Russian Caribbean Stud heading to use the corresponding localized Call term.
        self.assertEqual(resources[("ru-RU", "caribbean_stud")]["paytable.title"], "Таблица выплат за колл")
        # Require both video-poker paytables to describe total returned credits rather than profit odds.
        self.assertEqual(resources[("en-US", "joker_poker")]["paytable.multiplier"], "{value}× returned")
        # Require the multi-hand paytable to share the same total-return convention.
        self.assertEqual(resources[("en-US", "multi_hand_video_poker")]["paytable.multiplier"], "{value}× returned")
        # Require the Russian Joker Poker paytable to preserve the total-return meaning.
        self.assertEqual(resources[("ru-RU", "joker_poker")]["paytable.multiplier"], "возврат {value}×")
        # Require the Russian multi-hand paytable to preserve the total-return meaning.
        self.assertEqual(resources[("ru-RU", "multi_hand_video_poker")]["paytable.multiplier"], "возврат {value}×")
        # Require Slots history to omit the raw round identifier in both installed locales.
        self.assertEqual(resources[("en-US", "slots")]["history.row"], "{lines} lines")
        # Require the Russian Slots history row to omit the same internal identifier.
        self.assertEqual(resources[("ru-RU", "slots")]["history.row"], "{lines} линий")
        # Require grammatical Russian Roulette ranges at both outside-bet boundaries.
        self.assertEqual((resources[("ru-RU", "roulette")]["bets.low"], resources[("ru-RU", "roulette")]["bets.high"]), ("от 1 до 18", "от 19 до 36"))
        # Require Baccarat's Russian status copy to contain no borrowed English burn term.
        self.assertEqual(resources[("ru-RU", "baccarat")]["status.burnVisible"], "Видна сжигаемая карта")
        # Require Baccarat's Russian natural-check labels to use the localized term consistently.
        self.assertEqual(resources[("ru-RU", "baccarat")]["stage.natural"], resources[("ru-RU", "baccarat")]["status.naturalCheck"])
        # Require the completed Russian natural-check phrase rather than the former mixed-language wording.
        self.assertEqual(resources[("ru-RU", "baccarat")]["status.naturalCheck"], "Проверка натуральной")

    # Require one low-specificity fallback that remains overridable by game-owned focus styles.
    def test_shared_game_focus_fallback_contract(self):
        # Read the checked shared stylesheet as text so the listener-free gate remains deterministic.
        stylesheet = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        # Pin the zero-specificity selector to the four supported in-game control classes.
        selector = ":where(#view.screen.game-screen button, #view.screen.game-screen input, #view.screen.game-screen select, #view.screen.game-screen [tabindex]):focus-visible"
        # Require the shared selector to exist exactly once so duplicate fallbacks cannot drift.
        self.assertEqual(stylesheet.count(selector), 1)
        # Isolate the declared rule body without depending on unrelated stylesheet ordering.
        rule_body = stylesheet.split(selector, 1)[1].split("}", 1)[0]
        # Require a high-contrast nonzero outline and a positive offset around focused controls.
        self.assertIn("outline: 3px solid var(--gold);", rule_body)
        # Require the ring to remain visually separated from the dark control boundary.
        self.assertIn("outline-offset: 2px;", rule_body)


# Execute the focused suite when a maintainer invokes this file directly.
if __name__ == "__main__":
    # Use the standard unittest entrypoint so local diagnostics match central execution.
    unittest.main()
