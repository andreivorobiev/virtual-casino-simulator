# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for CARD-001 and POKER-001 primitives."""

# Import the standard unit-test runner so this file remains dependency-free.
import unittest

# Import the card primitives under direct test.
from casino.core.cards import Card, coerce_card, create_deck, shuffle_cards, shuffled_deck
# Import the poker evaluators under direct test.
from casino.core.poker import evaluate_five, evaluate_hand


# Verify deck creation, normalization, and deterministic shuffle behavior.
class CardPrimitiveTests(unittest.TestCase):
    # Confirm one standard deck contains every unique card exactly once.
    def test_create_standard_deck(self):
        # Build a stable unshuffled deck.
        deck = create_deck()
        # Verify the expected card count and unique compact codes.
        self.assertEqual(52, len(deck))
        # Verify every standard card appears once.
        self.assertEqual(52, len({card.code for card in deck}))
        # Verify construction order remains deterministic for fixtures.
        self.assertEqual(("2C", "3C", "4C"), tuple(card.code for card in deck[:3]))

    # Confirm accepted string and object shapes normalize identically.
    def test_coerce_card_shapes(self):
        # Normalize compact ASCII, display-symbol, and mapping values.
        cards = [coerce_card("AS"), coerce_card("A♠"), coerce_card({"rank": "a", "suit": "spades"})]
        # Verify every representation becomes the same immutable card value.
        self.assertEqual([Card("A", "spades")] * 3, cards)
        # Verify display and persistence forms remain separate and stable.
        self.assertEqual(("AS", "A♠"), (cards[0].code, cards[0].display))

    # Confirm seeded shuffles are reproducible without mutating caller input.
    def test_seeded_shuffle_is_deterministic_and_non_mutating(self):
        # Build an ordered deck to detect accidental mutation.
        original = create_deck()
        # Capture the ordered codes before shuffling.
        ordered_codes = [card.code for card in original]
        # Shuffle twice through the public seed hook.
        first = shuffle_cards(original, seed="CARD-001-vector")
        # Repeat with the same seed to prove deterministic output.
        second = shuffled_deck(seed="CARD-001-vector")
        # Verify both calls return the exact same order.
        self.assertEqual([card.code for card in first], [card.code for card in second])
        # Verify shuffling did not change the caller-owned deck.
        self.assertEqual(ordered_codes, [card.code for card in original])
        # Pin the first five cards as a deterministic cross-worker fixture.
        self.assertEqual(["QS", "4C", "QC", "5D", "7C"], [card.code for card in first[:5]])

    # Confirm invalid deck and entropy combinations fail explicitly.
    def test_invalid_deck_and_shuffle_inputs(self):
        # Reject an empty shoe request.
        with self.assertRaises(ValueError):
            # Exercise the invalid count boundary.
            create_deck(0)
        # Reject competing deterministic sources.
        with self.assertRaises(ValueError):
            # Supply both hooks to prove ambiguity is not silently resolved.
            shuffle_cards(create_deck(), seed=1, rng=object())


# Verify standard hand categories, tie breakers, and seven-card selection.
class PokerPrimitiveTests(unittest.TestCase):
    # Confirm every five-card category has a deterministic classification vector.
    def test_five_card_category_vectors(self):
        # Define standard category fixtures from weakest through strongest.
        vectors = {
            "high_card": ["AS", "JD", "9C", "6H", "3S"],  # Cover an ungrouped hand.
            "one_pair": ["AS", "AD", "9C", "6H", "3S"],  # Cover one matching pair.
            "two_pair": ["AS", "AD", "9C", "9H", "3S"],  # Cover two matching pairs.
            "three_of_a_kind": ["AS", "AD", "AC", "6H", "3S"],  # Cover one triplet.
            "straight": ["9S", "8D", "7C", "6H", "5S"],  # Cover consecutive mixed suits.
            "flush": ["AS", "JS", "9S", "6S", "3S"],  # Cover five nonconsecutive spades.
            "full_house": ["AS", "AD", "AC", "6H", "6S"],  # Cover a triplet plus pair.
            "four_of_a_kind": ["AS", "AD", "AC", "AH", "3S"],  # Cover four equal ranks.
            "straight_flush": ["9S", "8S", "7S", "6S", "5S"],  # Cover the top category.
        }
        # Evaluate each fixture and compare its stable machine-readable name.
        for expected, cards in vectors.items():
            # Preserve the category name in subtest diagnostics.
            with self.subTest(category=expected):
                # Verify the evaluator identifies the intended category.
                self.assertEqual(expected, evaluate_five(cards).name)

    # Confirm ace-low straights compare below ordinary six-high straights.
    def test_wheel_straight_tiebreak(self):
        # Evaluate the special ace-low pattern.
        wheel = evaluate_five(["AS", "2D", "3C", "4H", "5S"])
        # Evaluate the next higher ordinary straight.
        six_high = evaluate_five(["2S", "3D", "4C", "5H", "6S"])
        # Verify the wheel normalizes to a five-high tie breaker.
        self.assertEqual((5,), wheel.tiebreak)
        # Verify the six-high straight wins comparison.
        self.assertGreater(six_high.comparison_key, wheel.comparison_key)

    # Confirm seven-card evaluation selects the best five-card combination.
    def test_seven_card_best_hand(self):
        # Evaluate a hold-em-shaped hand containing an ace-high flush.
        result = evaluate_hand(["AS", "JS", "9S", "6S", "3S", "AD", "AC"])
        # Verify the flush outranks the available three aces.
        self.assertEqual("flush", result.name)
        # Verify the selected best hand contains exactly five cards.
        self.assertEqual(5, len(result.cards))

    # Confirm pair kickers break otherwise equal one-pair hands deterministically.
    def test_pair_kicker_comparison(self):
        # Evaluate an ace-pair hand with a king kicker.
        king_kicker = evaluate_five(["AS", "AD", "KS", "8C", "2H"])
        # Evaluate the same pair with a queen kicker.
        queen_kicker = evaluate_five(["AH", "AC", "QS", "8D", "2C"])
        # Verify standard kicker ordering chooses the king-high side.
        self.assertGreater(king_kicker.comparison_key, queen_kicker.comparison_key)

    # Confirm incomplete and oversized inputs are rejected at the public boundary.
    def test_invalid_hand_sizes(self):
        # Reject fewer than five cards.
        with self.assertRaises(ValueError):
            # Exercise the lower size boundary.
            evaluate_hand(["AS", "KS", "QS", "JS"])
        # Reject more than seven cards.
        with self.assertRaises(ValueError):
            # Exercise the upper size boundary.
            evaluate_hand(["AS", "KS", "QS", "JS", "10S", "9D", "8C", "7H"])


# Run the focused unit suite when invoked as a standalone worker validation.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
