"""Economics regression: Hi-Lo is house-side at every visible rank after rank pricing. (issue #406)

Flat even money let a player always guess the majority direction for a +50.7% edge. Pricing a correct
call at (1 - HOUSE_EDGE - tie_probability) / P(optimal guess wins) holds the same edge whether the
visible card is extreme or near the middle. This suite proves that analytically per rank and confirms
the aggregate best-play return through the real settlement path over every current/next card pair.
"""

# Import the standard unit-test framework.
import unittest

# Import the real Hi-Lo engine and the shared deck so the proof exercises shipped code.
from casino.games.hi_lo import engine
# Import the canonical deck constructor independently from the game engine.
from casino.core.cards import create_deck


# Group all rank-pricing economics proofs under one focused suite.
class HiLoEconomicsTests(unittest.TestCase):
    """Assert the rank-priced paytable keeps a uniform positive house edge."""

    # Pin the complete approved server table before checking its economics.
    def test_paytable_matches_the_approved_rank_prices(self):
        # Define every exact total-return multiplier from deuce through ace.
        expected = {"2": 0.96, "3": 1.05, "4": 1.16, "5": 1.28, "6": 1.44, "7": 1.65, "8": 1.93, "9": 1.65, "10": 1.44, "J": 1.28, "Q": 1.16, "K": 1.05, "A": 0.96}
        # Require settlement authority and the public rule table to share one immutable map.
        self.assertEqual(expected, engine.correct_paytable())

    # Prove every visible-card rank preserves a positive and realistic house edge.
    def test_every_rank_price_is_house_side(self):
        # Each rank's expected return (correct price times win probability plus the tie refund) is < 1.
        paytable = engine.correct_paytable()
        # Reuse the engine-owned refunded-tie probability in every rank calculation.
        tie_probability = engine.TIE_PROBABILITY
        # Evaluate the exact published price for each public rank.
        for rank, value in engine.RANK_VALUES.items():
            # Derive the optimal call's win probability from the real engine helper.
            win_probability = engine._optimal_win_probability(value)
            # Add the correct-call return and refunded-tie branch into one expected return.
            rtp = paytable[rank] * win_probability + tie_probability
            # A house-side rank returns strictly less than one on expectation.
            self.assertLess(rtp, 1.0, f"rank {rank} best-play RTP {rtp:.4f} is player-positive")
            # The edge should be a realistic single-digit percentage rather than punitive.
            self.assertGreater(rtp, 0.90, f"rank {rank} RTP {rtp:.4f} is punitively low")
            # The edge must be the same at every rank (uniform pricing).
            self.assertAlmostEqual(rtp, 1 - engine.HOUSE_EDGE, delta=0.01,
                                   msg=f"rank {rank} edge drifted from the target")

    # Exercise every real current/next-card settlement pair to pin aggregate best play.
    def test_real_engine_best_play_is_house_side(self):
        # Exact best-play return: for each current card take the better guess EV over all 51 next cards.
        cards = create_deck()
        # Accumulate one optimal expected return for every possible visible card.
        total = 0.0
        # Treat each card in the canonical deck as the visible opening card once.
        for current in cards:
            # Accumulate higher and lower settlement returns separately for this visible card.
            expected = {"higher": 0.0, "lower": 0.0}
            # Enumerate every possible next card from the same canonical deck.
            for nxt in cards:
                # Skip the physical card already exposed as the current card.
                if nxt.code == current.code:
                    # Continue with the remaining 51-card conditional distribution.
                    continue
                # Settle both legal player guesses through the real engine path.
                for guess in engine.GUESSES:
                    # Prepare one deterministic round with the selected physical card pair.
                    prepared = engine.create_round(
                        "player", 1.0, "deal", current_card=current.code, next_card=nxt.code,
                        round_id="hilo_" + "0" * 22, created_at="t", request_fingerprint="f",
                    )
                    # Settle the public guess so payout rounding matches production behavior.
                    settled = engine.settle_round(prepared, guess, "guess", completed_at="t", request_fingerprint="f")
                    # Add the returned-token amount to this direction's conditional total.
                    expected[guess] += settled["payout"]
            # Retain the better rational direction for this visible card.
            total += max(expected["higher"], expected["lower"]) / (len(cards) - 1)
        # Average the optimal conditional return across all 52 visible cards.
        best_play_rtp = total / len(cards)
        # The exact best-play return must stay house-side.
        self.assertLess(best_play_rtp, 0.99, f"best-play RTP {best_play_rtp:.4f} is not house-side")
        # Reject an accidentally punitive table even when it remains house-side.
        self.assertGreater(best_play_rtp, 0.90, f"best-play RTP {best_play_rtp:.4f} is punitively low")
        # Pin the exact rounded-table aggregate so later price drift is deliberate.
        self.assertAlmostEqual(0.9644042232, best_play_rtp, places=9)


# Support direct execution through the standard unittest command line.
if __name__ == "__main__":
    # Delegate result reporting and exit status to the unittest framework.
    unittest.main()
