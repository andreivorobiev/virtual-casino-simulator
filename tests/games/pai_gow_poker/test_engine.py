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
