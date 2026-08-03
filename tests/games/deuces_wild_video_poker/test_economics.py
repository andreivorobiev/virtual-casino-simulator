"""Economics regression: Deuces Wild is house-side after the four-of-a-kind reduction. (issue #456)

The full-pay schedule was player-positive under optimal hold (best-play RTP ~100.42%). Reducing the
four-of-a-kind return from 5 to 4 — the canonical deuces-wild house-edge lever, since wild deuces make
quads the highest-frequency paid hand — lowers optimal-play RTP to ~94.05% while leaving every other
tier and the natural hand-ranking order intact.

Optimal-play RTP for Deuces Wild requires evaluating all 32 holds against the full draw distribution
for each of the 2,598,960 deals; that inclusion-exclusion computation is far too slow for a unit test,
so it was verified offline (see contracts/compatibility/deuces-wild-house-edge.json). This suite guards
the corrected paytable itself against regression and checks the tier ordering the RTP depends on.
"""

# Import the standard unit-test framework.
import unittest

# Import the real engine so the guard reads the shipped paytable, not a copy.
from casino.games.deuces_wild_video_poker import engine


# The corrected house-side full schedule; four_of_a_kind is reduced from 5 to 4.
EXPECTED_PAYTABLE = {
    "natural_royal_flush": 800,  # Top jackpot for a deuce-free royal flush.
    "four_deuces": 200,  # Second jackpot for all four physical deuces.
    "wild_royal_flush": 25,  # Royal completed with wild deuces.
    "five_of_a_kind": 15,  # Five equal ranks using wild deuces.
    "straight_flush": 9,  # Non-royal straight flush.
    "four_of_a_kind": 4,  # Reduced quad return, the single house-edge lever. (issue #456)
    "full_house": 3,  # Three-plus-two grouping.
    "flush": 2,  # Five cards of one suit.
    "straight": 2,  # Five consecutive ranks.
    "three_of_a_kind": 1,  # Wager returned for three equal ranks.
    "no_win": 0,  # No return for a non-qualifying result.
}


# Group the paytable guards for the house-edged Deuces Wild schedule.
class DeucesWildEconomicsTests(unittest.TestCase):
    """Guard the house-edged paytable and the ordering its RTP depends on."""

    # Confirm the shipped schedule equals the corrected house-side paytable exactly.
    def test_paytable_matches_the_house_edged_schedule(self):
        # The shipped paytable must equal the corrected house-side schedule exactly.
        self.assertEqual(EXPECTED_PAYTABLE, dict(engine.PAYTABLE))

    # Confirm the single house-edge lever is the reduced quad return.
    def test_four_of_a_kind_was_reduced(self):
        # The four-of-a-kind tier must pay the reduced four credits.
        self.assertEqual(4, engine.PAYTABLE["four_of_a_kind"])

    # Confirm no reduction inverted the natural hand-ranking order.
    def test_tier_ordering_is_non_inverted(self):
        # List every tier from weakest to strongest by deuces-wild ranking.
        order = [
            "no_win", "three_of_a_kind", "straight", "flush", "full_house",  # Weakest tiers.
            "four_of_a_kind", "straight_flush", "five_of_a_kind",  # Middle tiers.
            "wild_royal_flush", "four_deuces", "natural_royal_flush",  # Strongest tiers.
        ]
        # Read each tier's return in that weakest-to-strongest order.
        returns = [engine.PAYTABLE[tier] for tier in order]
        # Each tier from weakest to strongest returns at least as much as the one below it.
        self.assertEqual(returns, sorted(returns), "a paytable reduction inverted the hand ranking")


# Run the suite directly for focused execution.
if __name__ == "__main__":
    # Delegate to the standard unittest runner.
    unittest.main()
