"""Pure rules tests for the issue #149 Acey-Deucey proposal."""

# Import the dependency-free standard test runner.
import unittest

# Import the pure engine under direct test.
from casino.games.acey_deucey import engine
# Import public validation errors for boundary assertions.
from casino.errors import ValidationError
import random
from casino.core import cards


# Verify deterministic rule classification and public state sanitization.
class AceyDeuceyEngineTests(unittest.TestCase):
    # Confirm strict inside wins while boundary ties and outside cards lose.
    def test_strict_inside_boundary_tie_and_outside_outcomes(self):
        # Verify a rank strictly inside the boundaries wins.
        self.assertEqual("inside", engine.classify_result("2H", "AS", "7C"))
        # Verify matching the lower boundary is an explicit tie-edge loss.
        self.assertEqual("boundary_tie", engine.classify_result("2H", "AS", "2C"))
        # Verify matching the upper boundary is also an explicit tie-edge loss.
        self.assertEqual("boundary_tie", engine.classify_result("2H", "AS", "AD"))
        # Verify a rank outside the interval loses.
        self.assertEqual("outside", engine.classify_result("8H", "10S", "QC"))

    # Confirm equal and adjacent boundaries expose zero inside ranks.
    def test_pair_and_adjacent_boundaries_have_no_inside_ranks(self):
        # Verify equal ranks have no strict inside possibilities.
        self.assertEqual(0, engine.inside_rank_count("7H", "7S"))
        # Verify adjacent ranks also have no strict inside possibilities.
        self.assertEqual(0, engine.inside_rank_count("7H", "8S"))

    # Confirm play reveals the result publicly while retaining private rollback material.
    def test_play_round_payout_table_and_private_recovery_card(self):
        # Create a prepared reload-safe round with a hidden inside result.
        round_state = engine.create_round("player-1", "deal-1", left_card="2H", right_card="AS", third_card="7C", round_id="round-1", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fp")
        # Settle the round through the pure play transition.
        settled = engine.play_round(round_state, 5, "play-1", completed_at="2026-07-14T00:00:01Z", request_fingerprint="play-fp")
        # Verify the spread-priced return rather than a hardcoded flat multiple, so this assertion tracks
        # the published paytable instead of going stale the next time the edge is retuned. (issue #408)
        expected_payout = round(5 * engine.inside_return_multiplier(engine.inside_rank_count("2H", "AS")), 2)
        # Confirm the outcome, the priced payout, and the derived net movement together.
        self.assertEqual(("inside", expected_payout, round(expected_payout - 5, 2)), (settled["outcome"], settled["payout"], settled["net"]))
        # Verify the private recovery card survives until service-level debit proof exists.
        self.assertEqual("7C", settled["_third_card"])
        # Verify the revealed third card is public after play.
        self.assertEqual("7C", settled["third_card"])
        # Sanitize the terminal round through the public projection.
        public = engine.public_round(settled)
        # Verify rollback material never appears in the browser/API payload.
        self.assertNotIn("_third_card", public)

    # Confirm invalid wagers never reach ledger orchestration.
    def test_wager_validation_rejects_invalid_values(self):
        # Reject booleans even though Python treats them as integers.
        with self.assertRaises(ValidationError):
            # Exercise the boolean boundary.
            engine.normalize_wager(True)
        # Reject zero-token wagers.
        with self.assertRaises(ValidationError):
            # Exercise the lower bound.
            engine.normalize_wager(0)


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()


# Prove the spread-priced return leaves the house ahead at every decision the player can see. (#408)
class AceyDeuceySpreadPricingTests(unittest.TestCase):
    # Verify the published paytable prices every legal spread below break-even.
    def test_every_spread_is_house_positive(self):
        # Walk the full published table rather than a sampled subset.
        for spread, multiplier in engine.inside_paytable().items():
            # Compute the exact inside probability for this spread from the fifty remaining cards.
            probability = engine.CARDS_PER_RANK * spread / engine.REMAINING_AFTER_BOUNDARIES
            # Expected value is the price multiplied by the chance of winning at that price.
            expected_value = multiplier * probability
            # Require the house to keep an edge at this spread, which is what issue #408 lacked.
            self.assertLess(expected_value, 1.0, f"spread {spread} returns {expected_value:.4f} to the player")
            # Require the edge to stay close to the declared target so no spread is punitive either.
            self.assertAlmostEqual(expected_value, 1 - engine.HOUSE_EDGE, delta=0.01)

    # Verify a spread that cannot contain an inside card has no price at all.
    def test_zero_spread_has_no_price(self):
        # Adjacent or equal boundaries leave nothing strictly inside, so pricing must fail closed.
        with self.assertRaises(ValidationError):
            # Request a price for an unplayable spread.
            engine.inside_return_multiplier(0)

    # Verify the strategy issue #408 described no longer beats the house.
    def test_documented_exploit_is_no_longer_profitable(self):
        # Reproduce the reported strategy: wait for a wide gap, then bet.
        staked = returned = 0.0
        # Use a fixed generator so the proof is deterministic.
        generator = random.Random(4080)
        # Deal enough rounds for the mean to settle.
        for _ in range(60000):
            # Draw a fresh shuffled deck through the shared card primitives.
            deck = cards.shuffled_deck(rng=generator)
            # Read the two public boundaries and the hidden third card.
            left, right, third = deck[0], deck[1], deck[2]
            # Measure the spread the player can see before choosing.
            spread = engine.inside_rank_count(left, right)
            # Skip the narrow gaps exactly as the reported exploit does.
            if spread < 7:
                continue
            # Commit a unit stake on this favourable-looking deal.
            staked += 1.0
            # Credit the spread-priced return only on a strict inside result.
            if engine.classify_result(left, right, third) == "inside":
                returned += engine.inside_return_multiplier(spread)
        # Require the house to retain an edge against the strategy that previously returned +33%.
        self.assertLess(returned / staked, 1.0, f"exploit returns {returned / staked:.4f}")
