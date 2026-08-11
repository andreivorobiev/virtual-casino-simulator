# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic rule tests for issue #138 Pai Gow Poker."""

# Import the dependency-free standard test runner.
import random
import unittest

# Import shared public errors for invalid transition assertions.
from casino.errors import ValidationError
# Import only the isolated game engine under test.
from casino.games.pai_gow_poker import engine


# Verify the joker evaluator, hand comparison, house way, and settlement.
class PaiGowPokerEngineTests(unittest.TestCase):
    # Confirm seeded deals are deterministic and contain no duplicate physical cards.
    def test_deal_is_deterministic_without_replacement(self):
        # Deal one stable table layout from the seeded joker deck.
        first = engine.deal_seven(seed="issue-138-deterministic")
        # Repeat the same deterministic deal.
        second = engine.deal_seven(seed="issue-138-deterministic")
        # Verify stable test output for identical seeds.
        self.assertEqual(first, second)
        # Combine every dealt card for duplicate checks.
        all_cards = [*first["player_cards"], *first["dealer_cards"]]
        # Verify one physical card is never dealt twice.
        self.assertEqual(len(all_cards), len(set(all_cards)))
        # Verify the layout splits seven player and seven dealer cards.
        self.assertEqual((7, 7), (len(first["player_cards"]), len(first["dealer_cards"])))

    # Confirm the joker completes straights and flushes but otherwise acts as an ace.
    def test_joker_is_a_bug_not_a_full_wild(self):
        # A joker completing broadway makes a straight flush.
        self.assertEqual(8, engine.evaluate_five(["10S", "JS", "QS", "XJ", "AS"])[0])
        # A joker beside an ace pairs the aces.
        self.assertEqual(1, engine.evaluate_five(["AS", "XJ", "2D", "7C", "9H"])[0])
        # A joker beside two kings cannot forge three kings, so it stays a pair by acting as an ace.
        self.assertEqual(1, engine.evaluate_five(["KS", "KD", "XJ", "2C", "9H"])[0])
        # Four natural aces plus the joker form the top-ranked five aces.
        self.assertEqual(9, engine.evaluate_five(["AS", "AD", "AH", "AC", "XJ"])[0])
        # In the two-card hand the joker plays as an ace.
        self.assertEqual((0, (14, 13)), engine.evaluate_two(["XJ", "KS"]))

    # Confirm the cross-hand rule keeps the two-card hand from outranking the five-card hand.
    def test_split_legality_rules(self):
        # A five-card two pair legally sits above a two-card queen pair.
        self.assertTrue(engine.split_is_legal(["AS", "AD", "KS", "KD", "2C"], ["QS", "QD"]))
        # A two-card pair may not sit above a five-card high-card hand.
        self.assertFalse(engine.split_is_legal(["AS", "KD", "QS", "JD", "9C"], ["2S", "2D"]))

    # Confirm the house way returns a legal arrangement for a random sample.
    def test_house_way_is_always_legal(self):
        # Use a fixed generator so the sample is reproducible.
        rng = random.Random(2026)
        # Build the ordered deck once.
        deck = engine.build_deck_codes()
        # Check many random seven-card hands.
        for _ in range(200):
            # Shuffle an independent copy.
            shuffled = deck[:]
            # Randomize the copy.
            rng.shuffle(shuffled)
            # Arrange the first seven cards by the house way.
            arranged = engine.set_house_way(shuffled[:7])
            # Verify the resulting split never sets the low hand above the high hand.
            self.assertTrue(engine.split_is_legal(arranged["high"], arranged["low"]))

    # Confirm the issue #407 house way sets a pair low instead of dumping the two weakest kickers.
    def test_house_way_splits_pairs_into_low_hand(self):
        # Build a two-pair seven-card fixture whose suits cannot complete a flush.
        seven = ["AS", "AD", "KH", "KC", "9D", "5C", "2H"]
        # Arrange the fixture by the corrected house way.
        arranged = engine.set_house_way(seven)
        # Verify the dealer low hand now holds a pair.
        self.assertEqual(1, engine.evaluate_two(arranged["low"])[0])
        # Verify the low hand is no longer the two weakest kickers the old high-first objective dumped there.
        self.assertNotEqual((0, (5, 2)), engine.evaluate_two(arranged["low"]))
        # Verify the pair-forward arrangement is still legal.
        self.assertTrue(engine.split_is_legal(arranged["high"], arranged["low"]))

    # Confirm the issue #407 low-first objective keeps the high hand above the low hand and reports honest scores.
    def test_house_way_low_first_objective_stays_legal(self):
        # Use a fixed generator so the sample is reproducible.
        rng = random.Random(407)
        # Build the ordered deck once.
        deck = engine.build_deck_codes()
        # Check several hundred random seven-card hands.
        for _ in range(300):
            # Shuffle an independent copy.
            shuffled = deck[:]
            # Randomize the copy.
            rng.shuffle(shuffled)
            # Arrange the first seven cards by the house way.
            arranged = engine.set_house_way(shuffled[:7])
            # Verify the resulting split never sets the low hand above the high hand.
            self.assertTrue(engine.split_is_legal(arranged["high"], arranged["low"]))
            # Verify the published high score matches the returned high hand after the low-first reorder.
            self.assertEqual(engine.evaluate_five(arranged["high"]), arranged["high_score"])
            # Verify the published low score matches the returned low hand.
            self.assertEqual(engine.evaluate_two(arranged["low"]), arranged["low_score"])

    # Confirm the issue #407 maximize-low exploit no longer holds a positive edge through settlement.
    def test_maximize_low_exploit_edge_is_negative(self):
        # Track the total player return across both seeded samples.
        total_net = 0.0
        # Track the total wagered units for the per-unit edge.
        total_wagered = 0.0
        # Replay the documented exploit under two independent seeds.
        for seed in (999, 12345):
            # Use a fixed generator so each sample is reproducible.
            rng = random.Random(seed)
            # Build the ordered deck once per seed.
            deck = engine.build_deck_codes()
            # Settle two thousand seeded exploit hands against the corrected dealer.
            for _ in range(2000):
                # Shuffle an independent copy.
                shuffled = deck[:]
                # Randomize the copy.
                rng.shuffle(shuffled)
                # Deal seven player cards then seven dealer cards without replacement.
                player_seven, dealer_seven = shuffled[:7], shuffled[7:14]
                # Rebuild the old exploit: enumerate every legal split and maximize the two-card hand.
                best = None
                # Try every two-card low hand the exploit could choose.
                for i in range(7):
                    # Pair the first low-card index with every later index.
                    for j in range(i + 1, 7):
                        # Collect the candidate low hand.
                        low = [player_seven[i], player_seven[j]]
                        # Collect the remaining five cards as the high hand.
                        high = [player_seven[k] for k in range(7) if k not in (i, j)]
                        # Skip splits the table would reject.
                        if not engine.split_is_legal(high, low):
                            continue
                        # Rank exploit candidates by the two-card hand first.
                        candidate = (engine.evaluate_two(low), engine.evaluate_five(high))
                        # Keep the strongest low-first candidate.
                        if best is None or candidate > best[0]:
                            best = (candidate, high, low)
                # Settle the exploit arrangement against the corrected house-way dealer.
                result = engine.settle(best[1], best[2], dealer_seven, 1)
                # Accumulate the returned tokens minus the one-unit ante.
                total_net += result["payout"] - 1
                # Accumulate the wagered unit.
                total_wagered += 1
        # Verify the former +0.238 per-unit player edge is gone.
        self.assertLess(total_net / total_wagered, 0)

    # Confirm settlement pays a win minus commission, forfeits a loss, and pushes a split.
    def test_settlement_outcomes(self):
        # Build a player hand that beats the dealer on both hands for a clean win.
        strong_high = ["AS", "AD", "AH", "KD", "KS"]
        # Build the player low hand.
        strong_low = ["QS", "QD"]
        # Build a weak dealer that loses both hands.
        weak_dealer = ["2C", "3D", "4H", "5S", "7C", "8D", "9H"]
        # Settle the winning arrangement for a ten-token ante.
        win = engine.settle(strong_high, strong_low, weak_dealer, 10)
        # Verify a win pays the ante back plus even money minus the five percent commission.
        self.assertEqual(("win", 19.5), (win["outcome"], win["payout"]))
        # Build a losing player hand against a strong dealer.
        weak_high = ["2S", "3D", "4H", "5C", "7S"]
        # Build the player low hand.
        weak_low = ["8S", "9D"]
        # Build a dealer that wins both hands.
        strong_dealer = ["AS", "AD", "AH", "KD", "KS", "QS", "QD"]
        # Settle the losing arrangement.
        loss = engine.settle(weak_high, weak_low, strong_dealer, 10)
        # Verify a loss forfeits the ante with no returned tokens.
        self.assertEqual(("loss", 0.0), (loss["outcome"], loss["payout"]))

    # Confirm a copied hand goes to the dealer and splits push.
    def test_copies_go_to_dealer_and_splits_push(self):
        # Build a dealer whose house-way split we can mirror for a copy on one hand.
        dealer = ["KS", "KD", "7C", "5D", "3H", "9S", "2C"]
        # Compute the dealer arrangement to copy its exact hands.
        arranged = engine.set_house_way(dealer)
        # Copy the dealer high hand exactly and beat the low hand for a split push.
        result = engine.settle(arranged["high"], ["AS", "AD"], dealer, 10)
        # Verify the copied high hand denies the player that hand, forcing a push.
        self.assertEqual("push", result["outcome"])
        # Verify a push returns the ante untouched.
        self.assertEqual(10.0, result["payout"])

    # Confirm malformed wagers, indices, and illegal splits fail closed.
    def test_invalid_boundaries(self):
        # Reject boolean wagers despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed wager boundary.
            engine.normalize_wager(True)
        # Reject non-finite ledger amounts.
        with self.assertRaises(ValidationError):
            # Exercise the infinity boundary.
            engine.normalize_wager(float("inf"))
        # Reject a set that is not two distinct positions.
        with self.assertRaises(ValidationError):
            # Exercise the set-index boundary.
            engine.normalize_set([0, 0])
        # Reject one physical card dealt twice through a fixture.
        with self.assertRaises(ValidationError):
            # Exercise duplicate fixture detection.
            engine.deal_seven(fixture={"player_cards": ["AS", "AS", "2D", "3D", "4D", "5D", "6D"], "dealer_cards": ["7C", "8C", "9C", "10C", "JC", "QC", "KC"]})
        # Build a prepared round for the illegal-split assertion.
        round_state = engine.create_round("session-player", 10, "deal-1", round_id="pgpoker_0123456789abcdef01234567", created_at="2026-07-24T00:00:00Z", request_fingerprint="deal-fingerprint", fixture={"player_cards": ["2S", "3D", "4H", "5C", "7S", "AS", "AD"], "dealer_cards": ["8C", "9C", "10C", "JC", "QC", "KC", "2C"]})
        # Reject an arrangement that sets the pair of aces low beneath a high-card five-card hand.
        with self.assertRaises(ValidationError):
            # Exercise the illegal-split boundary using the two ace positions as the low hand.
            engine.apply_set(round_state, "decision-1", (5, 6), completed_at="2026-07-24T00:00:01Z", request_fingerprint="set-fingerprint")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
