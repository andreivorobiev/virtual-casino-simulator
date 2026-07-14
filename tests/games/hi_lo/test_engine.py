"""Deterministic rule tests for issue #85 and CARD-001."""

# Import the dependency-free standard test runner.
import unittest

# Import shared public errors for invalid transition assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated game engine under test.
from casino.games.hi_lo import engine


# Verify card ordering, settlement rules, and deterministic test seams.
class HiLoEngineTests(unittest.TestCase):
    # Build one prepared round with explicitly controlled cards.
    def round(self, current_card="5H", next_card="9S", wager=10):
        # Delegate to the production state constructor with stable audit fields.
        return engine.create_round("session-player", wager, "deal-1", current_card=current_card, next_card=next_card, round_id="hilo_0123456789abcdef01234567", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fingerprint")

    # Confirm the shared shuffle seam repeats and never deals one physical card twice.
    def test_deal_pair_is_deterministic_without_replacement(self):
        # Deal one stable pair from the seeded shared primitive.
        first = engine.deal_pair(seed="issue-85-deterministic")
        # Repeat the same deterministic fixture.
        second = engine.deal_pair(seed="issue-85-deterministic")
        # Verify stable test output for identical seeds.
        self.assertEqual(first, second)
        # Verify the two-card round never duplicates one physical card.
        self.assertNotEqual(first[0], first[1])

    # Confirm ace ranks high and suits never break equal-rank ties.
    def test_rank_comparison_is_ace_high_and_suit_neutral(self):
        # Verify an ace is higher than a king.
        self.assertEqual(1, engine.compare_cards("KH", "AS"))
        # Verify a deuce is lower than a three.
        self.assertEqual(-1, engine.compare_cards("3D", "2C"))
        # Verify equal ranks tie across different suits.
        self.assertEqual(0, engine.compare_cards("7H", "7S"))

    # Confirm correct higher and lower guesses return stake plus even-money winnings.
    def test_correct_guesses_return_twice_the_wager(self):
        # Define one winning vector for each legal direction.
        vectors = [("4H", "QC", "higher"), ("KS", "3D", "lower")]
        # Exercise both direction branches with stable fixtures.
        for current_card, next_card, guess in vectors:
            # Preserve the chosen direction in failure output.
            with self.subTest(guess=guess):
                # Build one prepared round for the vector.
                round_state = self.round(current_card, next_card, wager=12.5)
                # Settle through the public engine transition.
                engine.settle_round(round_state, guess, f"guess-{guess}", completed_at="2026-07-14T00:00:01Z", request_fingerprint=f"fingerprint-{guess}")
                # Verify the documented correct result and returned amount.
                self.assertEqual(("correct", 25.0, 12.5), (round_state["outcome"], round_state["payout"], round_state["net"]))
                # Verify the private reveal field is removed after settlement.
                self.assertNotIn("_next_card", round_state)

    # Confirm equal ranks refund the stake while a wrong prediction returns nothing.
    def test_tie_refund_and_incorrect_result(self):
        # Build equal ranks in different suits.
        tied = self.round("8H", "8S", wager=9)
        # Settle a direction that cannot break the rank tie.
        engine.settle_round(tied, "higher", "guess-tie", completed_at="2026-07-14T00:00:01Z", request_fingerprint="tie-fingerprint")
        # Verify a one-times refund and zero net movement.
        self.assertEqual(("tie", 9.0, 0.0), (tied["outcome"], tied["payout"], tied["net"]))
        # Build an intentionally wrong higher prediction.
        lost = self.round("KH", "3S", wager=9)
        # Settle the incorrect direction.
        engine.settle_round(lost, "higher", "guess-loss", completed_at="2026-07-14T00:00:01Z", request_fingerprint="loss-fingerprint")
        # Verify no returned-token credit is requested.
        self.assertEqual(("incorrect", 0.0, -9.0), (lost["outcome"], lost["payout"], lost["net"]))

    # Confirm malformed wagers, decisions, duplicate cards, and stale actions fail closed.
    def test_invalid_boundaries_and_repeated_transition(self):
        # Reject boolean wagers despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed wager boundary.
            engine.normalize_wager(True)
        # Reject non-finite ledger amounts.
        with self.assertRaises(ValidationError):
            # Exercise the infinity boundary.
            engine.normalize_wager(float("inf"))
        # Reject unsupported direction aliases.
        with self.assertRaises(ValidationError):
            # Exercise the decision enumeration boundary.
            engine.normalize_guess("up")
        # Reject one physical card dealt twice.
        with self.assertRaises(ValidationError):
            # Exercise the without-replacement invariant.
            self.round("AH", "AH")
        # Settle one valid round before attempting a changed retry.
        settled = self.round()
        # Apply the original terminal decision.
        engine.settle_round(settled, "higher", "guess-original", completed_at="2026-07-14T00:00:01Z", request_fingerprint="original")
        # Reject a changed action identity after settlement.
        with self.assertRaises(ConflictError):
            # Exercise the stale terminal transition.
            engine.settle_round(settled, "higher", "guess-other", completed_at="2026-07-14T00:00:02Z", request_fingerprint="other")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
