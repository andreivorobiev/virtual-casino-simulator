# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused deterministic engine tests for issue #130 and POKER-001."""

# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public validation errors for boundary assertions.
from casino.errors import ConflictError, ValidationError
# Import only the new game engine under test.
from casino.games.joker_poker import engine


# Verify deterministic 53-card Joker Poker gameplay behavior.
class JokerPokerEngineTests(unittest.TestCase):
    # Build one reproducible round with stable audit identifiers.
    def round(self, seed="issue-130"):
        # Deal deterministic source and draw cards through the game-owned joker deck.
        initial_hand, draw_pool = engine.deal_cards(seed=seed)
        # Delegate to the public engine constructor with injected deterministic metadata.
        return engine.create_round("session-player", 2, "deal-1", initial_hand=initial_hand, draw_pool=draw_pool, round_id="jp_round", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fingerprint")

    # Confirm the frozen deck profile is distinct from standard no-joker poker.
    def test_joker_deck_is_53_cards_with_one_joker(self):
        # Build the complete game-owned deck.
        deck = engine.joker_deck()
        # Verify the deck has one extra joker card.
        self.assertEqual(53, len(deck))
        # Verify the joker appears exactly once.
        self.assertEqual(1, deck.count(engine.JOKER_CODE))
        # Verify all card codes remain unique.
        self.assertEqual(53, len(set(deck)))

    # Confirm deterministic dealing uses the injected seed only in tests.
    def test_deals_are_deterministic_under_seed(self):
        # Deal the first deterministic card plan.
        first = self.round(seed="same-seed")
        # Deal the same plan again from identical inputs.
        second = self.round(seed="same-seed")
        # Verify every persisted card plan is reproducible.
        self.assertEqual(first, second)
        # Verify private draw cards remain available before settlement.
        self.assertGreaterEqual(len(first["_draw_pool"]), 48)

    # Confirm the game-owned wild-joker paytable boundaries.
    def test_paytable_boundaries_include_wild_only_rows(self):
        # Define representative winning and losing category vectors.
        vectors = {
            "natural_royal_flush": ["AS", "KS", "QS", "JS", "10S"],  # Cover the natural top row.
            "wild_royal_flush": ["AS", "KS", "QS", "JS", "JK"],  # Cover a joker-completed royal.
            "five_of_a_kind": ["AS", "AD", "AH", "AC", "JK"],  # Cover the wild five-kind row.
            "kings_or_better": ["KS", "JK", "9C", "6H", "3S"],  # Cover high-pair qualification.
            "two_pair": ["10S", "10D", "9C", "9H", "3S"],  # Cover the wager-return two-pair row.
            "no_win": ["10S", "10D", "9C", "6H", "3S"],  # Cover the non-qualifying pair boundary.
        }
        # Evaluate every fixture through the public game classifier.
        for expected, cards in vectors.items():
            # Preserve the expected paytable row in failure diagnostics.
            with self.subTest(outcome=expected):
                # Verify the game-specific qualification and multiplier.
                self.assertEqual((expected, engine.PAYTABLE[expected]), engine.classify_with_joker(cards)[:2])

    # Confirm held positions remain fixed and private draw cards are discarded after settlement.
    def test_holds_drive_one_final_hand(self):
        # Build a deterministic source hand and draw pool.
        round_state = engine.create_round("session-player", 1, "deal-2", initial_hand=["AS", "KD", "7C", "4H", "JK"], draw_pool=["QS", "JS", "10S", "9S", "8S"], round_id="jp_draw", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fingerprint")
        # Hold the ace, king, and joker before drawing.
        engine.set_holds(round_state, [0, 1, 4])
        # Complete the hand with a stable draw action.
        engine.draw(round_state, "draw-1", completed_at="2026-07-14T00:00:01Z", request_fingerprint="draw-fingerprint")
        # Verify held positions remain unchanged in the final hand.
        self.assertEqual(["AS", "KD", "JK"], [round_state["result"]["cards"][index] for index in (0, 1, 4)])
        # Verify private draw cards are absent after terminal settlement.
        self.assertNotIn("_draw_pool", round_state)
        # Verify an exact repeated engine draw returns the same terminal result.
        self.assertEqual(round_state, engine.draw(round_state, "draw-1", completed_at="ignored", request_fingerprint="draw-fingerprint"))
        # Reject a changed terminal draw action.
        with self.assertRaises(ConflictError):
            # Exercise post-settlement conflict protection.
            engine.draw(round_state, "draw-2", completed_at="ignored", request_fingerprint="draw-fingerprint")

    # Confirm malformed wagers, holds, and joker counts fail before state mutation.
    def test_invalid_boundaries_are_rejected(self):
        # Reject a zero wager.
        with self.assertRaises(ValidationError):
            # Exercise the lower wager boundary.
            engine.normalize_wager(0)
        # Reject duplicate held positions.
        with self.assertRaises(ValidationError):
            # Exercise duplicate selection validation.
            engine.set_holds(self.round(), [1, 1])
        # Reject out-of-range held positions.
        with self.assertRaises(ValidationError):
            # Exercise the upper position boundary.
            engine.set_holds(self.round(), [5])
        # Reject impossible multiple-joker hands.
        with self.assertRaises(ValidationError):
            # Exercise the one-joker rules profile boundary.
            engine.classify_with_joker(["JK", "JK", "AS", "KS", "QS"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
