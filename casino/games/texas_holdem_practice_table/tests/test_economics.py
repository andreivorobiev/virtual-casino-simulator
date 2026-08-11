# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Economics regression: the practice table holds a house edge after the pot rake. (issue #456)

Three server opponents always call and the human may only call or fold, so playing every hand to
showdown makes the human one of four equal contributors splitting the pot by best hand: an exact
break-even before the rake. The only skill is folding hopeless hands, whose edge is small in a
call-or-fold fixed-limit game against always-callers. Raking every settled pot therefore keeps even
best play house-side. This suite drives the real dealing and settlement path to confirm the rake is
withheld, the pot conservation identity holds, and the always-play return is below the wager.
"""

# Import unittest for dependency-free execution.
import unittest

# Import only the isolated practice-table engine under test.
from casino.games.texas_holdem_practice_table import engine


class TexasHoldemPracticeTableEconomicsTests(unittest.TestCase):
    """Confirm the rake creates a house edge without breaking pot accounting."""

    def _play_to_showdown(self, index):
        # Build one reproducible fixed-limit hand.
        hand = engine.create_hand("session-player", 1, f"start-{index:04d}", seed=f"econ-{index}",
                                  hand_id="thpt_hand_1", created_at="2026-07-14T00:00:00Z")
        # Call every street so the hand reaches a four-seat showdown.
        for street in range(4):
            action_id = f"call-{index:04d}-{street}"
            engine.apply_action(hand, "human", "call", action_id, created_at="2026-07-14T00:00:00Z")
            engine.advance_opponents(hand, action_id, clock=lambda: "2026-07-14T00:00:09Z")
        return hand

    def test_rake_is_withheld_and_pot_conserves(self):
        # A representative settled hand must withhold exactly the floored percentage rake.
        hand = self._play_to_showdown(0)
        result = hand["result"]
        pot_cents = int(round(hand["pot"] * 100))
        expected_rake = int(pot_cents * engine.PRACTICE_RAKE_RATE) / 100
        # The reported rake equals the floored percentage of the pot.
        self.assertEqual(expected_rake, result["rake"])
        # Every cent of the pot is either paid to a seat or taken as rake (no tokens created or lost).
        distributed = round(sum(result["payouts"].values()), 2)
        self.assertEqual(round(hand["pot"], 2), round(distributed + result["rake"], 2))
        # The rake must be a real positive withholding.
        self.assertGreater(result["rake"], 0.0)

    def test_always_play_return_is_house_side(self):
        # Drive many deterministic hands with the human calling to showdown every time.
        total_return = 0.0
        total_reserved = 0.0
        hands = 3000
        for index in range(hands):
            hand = self._play_to_showdown(index)
            # Accumulate the human's total wallet credits and opening escrow.
            total_return += hand["result"]["human_return"]
            total_reserved += hand["reserved_amount"]
        rtp = total_return / total_reserved
        # Always-play (the break-even baseline) must land house-side once the rake is applied.
        self.assertLess(rtp, 1.0, f"always-play RTP {rtp:.4f} is not house-side")
        # The edge should be a realistic single-digit-to-low-double-digit percentage, near the rake.
        self.assertGreater(rtp, 0.80, f"always-play RTP {rtp:.4f} is punitively low")


if __name__ == "__main__":
    unittest.main()
