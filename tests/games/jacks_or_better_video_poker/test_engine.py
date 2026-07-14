"""Focused 9/6 Jacks-or-Better engine tests for GitHub issue #91.

Confirmed requirements: CARD-001 and POKER-001.
JOBVP is a proposed local prefix only and is not claimed as centrally allocated.
"""

# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public validation errors for boundary assertions.
from casino.errors import ValidationError
# Import only the isolated game engine under test.
from casino.games.jacks_or_better_video_poker import engine


# Verify deterministic single-hand dealing, draw rules, and the classic paytable.
class JacksOrBetterVideoPokerEngineTests(unittest.TestCase):
    # Build one reproducible round with stable audit identifiers.
    def round(self, *, coin_value=1, coins=5, seed="issue-91"):
        # Delegate to the public engine constructor with injected deterministic metadata.
        return engine.create_round("session-player", coin_value, coins, "deal-action", seed=seed, round_id="jobvp_round", created_at="2026-07-14T00:00:00.000Z")

    # Confirm identical seeds and inputs produce the same persisted card plan.
    def test_deal_is_deterministic_and_private_pool_is_sanitized(self):
        # Build the first deterministic state vector.
        first = self.round(seed="deterministic-vector")
        # Build the same state vector again from identical inputs.
        second = self.round(seed="deterministic-vector")
        # Verify every persisted card and audit field is reproducible.
        self.assertEqual(first, second)
        # Verify the source and replacement cards do not overlap.
        self.assertEqual(10, len(set(first["initial_hand"] + first["_draw_pool"])))
        # Verify future replacement cards never appear in the public round payload.
        self.assertNotIn("_draw_pool", engine.public_round(first))

    # Confirm held positions survive while every discarded position draws in order.
    def test_holds_control_one_reload_safe_draw(self):
        # Build one deterministic five-coin round.
        round_state = self.round(seed="held-card-vector")
        # Capture the private replacement order before settlement removes it.
        replacements = list(round_state["_draw_pool"])
        # Hold alternating source cards in positions zero, two, and four.
        engine.set_holds(round_state, [0, 2, 4])
        # Complete the hand through one stable draw action key.
        engine.draw(round_state, "draw-action", completed_at="2026-07-14T00:00:01.000Z")
        # Verify all held positions match the source hand exactly.
        self.assertEqual([round_state["initial_hand"][index] for index in (0, 2, 4)], [round_state["final_hand"][index] for index in (0, 2, 4)])
        # Verify discarded positions consume the replacement pool in deal order.
        self.assertEqual(replacements[:2], [round_state["final_hand"][index] for index in (1, 3)])
        # Verify result values use the selected coin value and credit column.
        self.assertEqual(round(round_state["coin_value"] * round_state["payout_credits"], 2), round_state["total_payout"])
        # Verify the private replacement plan is removed after settlement.
        self.assertNotIn("_draw_pool", round_state)

    # Confirm every important qualification boundary maps through the shared evaluator.
    def test_paytable_classification_boundaries(self):
        # Define representative classic winning and losing category vectors.
        vectors = {
            "royal_flush": ["AS", "KS", "QS", "JS", "10S"],  # Cover the max-paytable category.
            "straight_flush": ["9S", "8S", "7S", "6S", "5S"],  # Cover a non-royal straight flush.
            "full_house": ["AS", "AD", "AC", "6H", "6S"],  # Cover the 9-for-1 full-house row.
            "flush": ["AS", "JS", "9S", "6S", "3S"],  # Cover the 6-for-1 flush row.
            "jacks_or_better": ["JS", "JD", "9C", "6H", "3S"],  # Cover the qualifying pair threshold.
            "no_win": ["10S", "10D", "9C", "6H", "3S"],  # Cover the non-qualifying pair boundary.
        }
        # Evaluate every fixture through the public game classifier.
        for expected, cards in vectors.items():
            # Preserve the expected paytable row in failure diagnostics.
            with self.subTest(outcome=expected):
                # Verify game-specific qualification without duplicating poker evaluation.
                self.assertEqual(expected, engine.classify_hand(cards))

    # Confirm the 9/6 rows and max-coin royal bonus use classic returned credits.
    def test_classic_paytable_and_max_coin_royal_bonus(self):
        # Verify full-house credits begin at nine and scale to forty-five.
        self.assertEqual((9, 18, 27, 36, 45), engine.PAYTABLE["full_house"])
        # Verify flush credits begin at six and scale to thirty.
        self.assertEqual((6, 12, 18, 24, 30), engine.PAYTABLE["flush"])
        # Verify four royal-flush coins return the ordinary linear amount.
        self.assertEqual(1000, engine.returned_credits("royal_flush", 4))
        # Verify five royal-flush coins receive the classic four-thousand-credit bonus.
        self.assertEqual(4000, engine.returned_credits("royal_flush", 5))

    # Confirm malformed wager, coin, and hold values fail before state mutation.
    def test_invalid_boundaries_are_rejected(self):
        # Reject coin counts outside the classic five columns.
        with self.assertRaises(ValidationError):
            # Exercise the unsupported sixth-coin boundary.
            self.round(coins=6)
        # Reject coin values above the issue #91 ceiling.
        with self.assertRaises(ValidationError):
            # Exercise the maximum fake-token value boundary.
            self.round(coin_value=20_000.01)
        # Reject duplicate held positions.
        with self.assertRaises(ValidationError):
            # Exercise duplicate selection validation.
            engine.set_holds(self.round(), [1, 1])
        # Reject out-of-range held positions.
        with self.assertRaises(ValidationError):
            # Exercise the upper position boundary.
            engine.set_holds(self.round(), [5])

    # Confirm completed history remains bounded and ordered newest-last.
    def test_archived_round_history_is_bounded(self):
        # Build one mutable state document for repeated archive operations.
        state = engine.default_state()
        # Archive more completed rounds than the configured retention limit.
        for index in range(engine.RECENT_ROUND_LIMIT + 3):
            # Build one minimal settled record with a stable increasing identifier.
            settled = {"round_id": f"round-{index}", "phase": "settled"}
            # Place the round in the active slot before archiving it normally.
            state["active_round"] = settled
            # Archive through the public bounded-history helper.
            engine.archive_round(state, settled)
        # Verify only the configured number of newest records remains.
        self.assertEqual(engine.RECENT_ROUND_LIMIT, len(state["recent_rounds"]))
        # Verify the newest record remains last for reload rendering.
        self.assertEqual("round-22", state["recent_rounds"][-1]["round_id"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
