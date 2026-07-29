"""Economics regression: Andar Bahar is house-side on both bets after side pricing. (issue #409)

The prior flat even-money return let a player guarantee a +3.0% edge by always backing Andar, which
receives the first card. Pricing each side at (1 - HOUSE_EDGE) / P(side wins) equalizes the edge, so
neither bet is player-positive under best play. This suite proves that analytically from the exact
first-match probability and cross-checks it by driving the real dealing and settlement path.
"""

# Import the standard unit-test framework.
import unittest
# Import a seeded RNG for the deterministic engine cross-check.
import random

# Import the real Andar Bahar engine so the proof exercises shipped code, not a re-implementation.
from casino.games.andar_bahar import engine


# Exact probability the first joker-rank match lands on each side (Andar holds the 26 odd positions).
EXACT_SIDE_PROBABILITY = {"andar": 10725 / 20825, "bahar": 1 - 10725 / 20825}


class AndarBaharEconomicsTests(unittest.TestCase):
    """Assert the side-priced paytable keeps a positive house edge on both bets."""

    def test_side_paytable_is_house_side_analytically(self):
        # Every published side price times its exact win probability must return below the wager.
        paytable = engine.side_paytable()
        for side, probability in EXACT_SIDE_PROBABILITY.items():
            rtp = paytable[side] * probability
            # A house-side bet returns strictly less than one on expectation.
            self.assertLess(rtp, 1.0, f"{side} best-play RTP {rtp:.4f} is player-positive")
            # The edge should be a realistic single-digit percentage, not a punitive one.
            self.assertGreater(rtp, 0.90, f"{side} RTP {rtp:.4f} is punitively low")

    def test_multiplier_matches_probability_pricing(self):
        # The published multiplier must equal the house-edge pricing formula for each side.
        for side, probability in EXACT_SIDE_PROBABILITY.items():
            expected = round((1 - engine.HOUSE_EDGE) / probability, 2)
            self.assertEqual(engine.side_return_multiplier(side), expected)

    def test_real_engine_settlement_is_house_side(self):
        # Drive the actual deal + settlement so the measured return reflects shipped behavior.
        master = random.Random(409409)
        for side in engine.SIDES:
            returned = 0.0
            trials = 40000
            for _ in range(trials):
                seed = master.getrandbits(63)
                match_card, dealt = engine.deal_sequence(seed=seed)
                settled = engine.create_round(
                    "player", 1.0, side, "action",
                    match_card=match_card, dealt_cards=dealt,
                    round_id="r" + "0" * 30, created_at="t", request_fingerprint="f",
                )
                returned += settled["payout"]
            measured_rtp = returned / trials
            # The seeded engine run must stay house-side well inside sampling noise.
            self.assertLess(measured_rtp, 0.99, f"measured {side} RTP {measured_rtp:.4f} not house-side")


if __name__ == "__main__":
    unittest.main()
