"""Pure rules tests for the issue #149 Acey-Deucey proposal."""

# Import the dependency-free standard test runner.
import unittest

# Import the pure engine under direct test.
from casino.games.acey_deucey import engine
# Import public validation errors for boundary assertions.
from casino.errors import ValidationError


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

    # Confirm playing a prepared round reveals the third card and pays only inside.
    def test_play_round_payout_table_and_private_card_cleanup(self):
        # Create a prepared reload-safe round with a hidden inside result.
        round_state = engine.create_round("player-1", "deal-1", left_card="2H", right_card="AS", third_card="7C", round_id="round-1", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fp")
        # Settle the round through the pure play transition.
        settled = engine.play_round(round_state, 5, "play-1", completed_at="2026-07-14T00:00:01Z", request_fingerprint="play-fp")
        # Verify the returned stake plus even-money profit.
        self.assertEqual(("inside", 10.0, 5.0), (settled["outcome"], settled["payout"], settled["net"]))
        # Verify the private card is removed from public terminal state.
        self.assertNotIn("_third_card", settled)
        # Verify the revealed third card is public after play.
        self.assertEqual("7C", settled["third_card"])

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
