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
    "natural_royal_flush": 800,
    "four_deuces": 200,
    "wild_royal_flush": 25,
    "five_of_a_kind": 15,
    "straight_flush": 9,
    "four_of_a_kind": 4,
    "full_house": 3,
    "flush": 2,
    "straight": 2,
    "three_of_a_kind": 1,
    "no_win": 0,
}


class DeucesWildEconomicsTests(unittest.TestCase):
    """Guard the house-edged paytable and the ordering its RTP depends on."""

    def test_paytable_matches_the_house_edged_schedule(self):
        # The shipped paytable must equal the corrected house-side schedule exactly.
        self.assertEqual(EXPECTED_PAYTABLE, dict(engine.PAYTABLE))

    def test_four_of_a_kind_was_reduced(self):
        # The single house-edge lever must be the reduced quad return.
        self.assertEqual(4, engine.PAYTABLE["four_of_a_kind"])

    def test_tier_ordering_is_non_inverted(self):
        # Stronger hands must never pay less than weaker ones, so no reduction inverts the ranking.
        order = ["no_win", "three_of_a_kind", "straight", "flush", "full_house",
                 "four_of_a_kind", "straight_flush", "five_of_a_kind", "wild_royal_flush",
                 "four_deuces", "natural_royal_flush"]
        returns = [engine.PAYTABLE[tier] for tier in order]
        # Each tier from weakest to strongest returns at least as much as the one below it.
        self.assertEqual(returns, sorted(returns), "a paytable reduction inverted the hand ranking")


if __name__ == "__main__":
    unittest.main()
