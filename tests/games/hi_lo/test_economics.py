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
from casino.core.cards import create_deck


class HiLoEconomicsTests(unittest.TestCase):
    """Assert the rank-priced paytable keeps a uniform positive house edge."""

    def test_every_rank_price_is_house_side(self):
        # Each rank's expected return (correct price times win probability plus the tie refund) is < 1.
        paytable = engine.correct_paytable()
        tie_probability = engine.TIE_PROBABILITY
        for rank, value in engine.RANK_VALUES.items():
            win_probability = engine._optimal_win_probability(value)
            rtp = paytable[rank] * win_probability + tie_probability
            # A house-side rank returns strictly less than one on expectation.
            self.assertLess(rtp, 1.0, f"rank {rank} best-play RTP {rtp:.4f} is player-positive")
            # The edge should be a realistic single-digit percentage rather than punitive.
            self.assertGreater(rtp, 0.90, f"rank {rank} RTP {rtp:.4f} is punitively low")
            # The edge must be the same at every rank (uniform pricing).
            self.assertAlmostEqual(rtp, 1 - engine.HOUSE_EDGE, delta=0.01,
                                   msg=f"rank {rank} edge drifted from the target")

    def test_real_engine_best_play_is_house_side(self):
        # Exact best-play return: for each current card take the better guess EV over all 51 next cards.
        cards = create_deck()
        total = 0.0
        for current in cards:
            expected = {"higher": 0.0, "lower": 0.0}
            for nxt in cards:
                if nxt.code == current.code:
                    continue
                for guess in engine.GUESSES:
                    prepared = engine.create_round(
                        "player", 1.0, "deal", current_card=current.code, next_card=nxt.code,
                        round_id="hilo_" + "0" * 22, created_at="t", request_fingerprint="f",
                    )
                    settled = engine.settle_round(prepared, guess, "guess", completed_at="t", request_fingerprint="f")
                    expected[guess] += settled["payout"]
            total += max(expected["higher"], expected["lower"]) / (len(cards) - 1)
        best_play_rtp = total / len(cards)
        # The exact best-play return must stay house-side.
        self.assertLess(best_play_rtp, 0.99, f"best-play RTP {best_play_rtp:.4f} is not house-side")
        self.assertGreater(best_play_rtp, 0.90, f"best-play RTP {best_play_rtp:.4f} is punitively low")


if __name__ == "__main__":
    unittest.main()
