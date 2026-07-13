"""Focused deterministic engine tests for issue #94 and POKER-001."""

# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public validation errors for boundary assertions.
from casino.errors import ValidationError
# Import only the new game engine under test.
from casino.games.multi_hand_video_poker import engine


# Verify deterministic 3, 5, and 10-hand gameplay behavior.
class MultiHandVideoPokerEngineTests(unittest.TestCase):
    # Build one reproducible round with stable audit identifiers.
    def round(self, hand_count=3, seed="issue-94"):
        # Delegate to the public engine constructor with injected deterministic metadata.
        return engine.create_round("session-player", hand_count, 2, "request-1", seed=seed, round_id="mhvp_round", created_at="2026-07-13T00:00:00.000Z")

    # Confirm every required mode builds the exact requested number of independent pools.
    def test_required_modes_are_deterministic(self):
        # Exercise all three issue #94 acceptance modes.
        for hand_count in engine.HAND_COUNTS:
            # Preserve the mode in failure diagnostics.
            with self.subTest(hand_count=hand_count):
                # Build the first deterministic state vector.
                first = self.round(hand_count, seed=f"mode-{hand_count}")
                # Build the same state vector again from identical inputs.
                second = self.round(hand_count, seed=f"mode-{hand_count}")
                # Verify every persisted card plan is reproducible.
                self.assertEqual(first, second)
                # Verify the private replacement plan has one lane per selected hand.
                self.assertEqual(hand_count, len(first["_draw_pools"]))

    # Confirm held source positions remain identical across every final lane.
    def test_holds_are_shared_across_ten_hands(self):
        # Build the largest required mode to cover all generated lanes.
        round_state = self.round(10, seed="shared-holds")
        # Hold alternating source cards in positions zero, two, and four.
        engine.set_holds(round_state, [0, 2, 4])
        # Complete every deterministic hand.
        engine.draw(round_state, completed_at="2026-07-13T00:00:01.000Z")
        # Verify every result preserves the same held source positions.
        for result in round_state["results"]:
            # Preserve the hand index in failure diagnostics.
            with self.subTest(hand_index=result["hand_index"]):
                # Compare each held final card with the common initial hand.
                self.assertEqual([round_state["initial_hand"][index] for index in (0, 2, 4)], [result["cards"][index] for index in (0, 2, 4)])
        # Verify the aggregate credit equals the sum of independently evaluated lanes.
        self.assertEqual(round(sum(item["payout"] for item in round_state["results"]), 2), round_state["total_payout"])
        # Verify private replacement plans are removed after settlement.
        self.assertNotIn("_draw_pools", round_state)

    # Confirm game-owned paytable qualifications use the shared poker evaluator correctly.
    def test_jacks_or_better_paytable_boundaries(self):
        # Define representative winning and losing category vectors.
        vectors = {
            "royal_flush": ["AS", "KS", "QS", "JS", "10S"],  # Cover the game-owned top paytable row.
            "straight_flush": ["9S", "8S", "7S", "6S", "5S"],  # Cover a non-royal straight flush.
            "jacks_or_better": ["JS", "JD", "9C", "6H", "3S"],  # Cover the qualifying pair threshold.
            "no_win": ["10S", "10D", "9C", "6H", "3S"],  # Cover the non-qualifying pair boundary.
        }
        # Evaluate every fixture through the public game classifier.
        for expected, cards in vectors.items():
            # Preserve the expected paytable row in failure diagnostics.
            with self.subTest(outcome=expected):
                # Verify the game-specific qualification and multiplier.
                self.assertEqual((expected, engine.PAYTABLE[expected]), engine.classify_hand(cards))

    # Confirm malformed modes, wagers, and holds fail before state mutation.
    def test_invalid_boundaries_are_rejected(self):
        # Reject unsupported single-hand play.
        with self.assertRaises(ValidationError):
            # Exercise the unsupported mode boundary.
            self.round(1)
        # Reject duplicate held positions.
        with self.assertRaises(ValidationError):
            # Exercise duplicate selection validation.
            engine.set_holds(self.round(), [1, 1])
        # Reject out-of-range held positions.
        with self.assertRaises(ValidationError):
            # Exercise the upper position boundary.
            engine.set_holds(self.round(), [5])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
