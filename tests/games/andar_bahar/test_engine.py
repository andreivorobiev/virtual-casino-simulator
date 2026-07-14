"""Deterministic rule tests for issue #140 and CARD-001."""

# Import the dependency-free standard test runner.
import unittest

# Import shared public errors for invalid transition assertions.
from casino.errors import ValidationError
# Import only the isolated game engine under test.
from casino.games.andar_bahar import engine


# Verify match-rank rules, alternating sequence, and deterministic test seams.
class AndarBaharEngineTests(unittest.TestCase):
    # Build one explicit fixture round with controlled outcome cards.
    def round(self, side="andar", wager=10):
        # Define a culturally standard joker plus alternating Andar/Bahar sequence.
        fixture = {"match_card": "7H", "dealt_cards": [{"side": "andar", "card": "2C", "matched": False}, {"side": "bahar", "card": "QS", "matched": False}, {"side": "andar", "card": "7D", "matched": True}]}
        # Delegate to the production state constructor with stable audit fields.
        return engine.play_round("session-player", wager, side, "play-1", round_id="andar_bahar_0123456789abcdef01234567", created_at="2026-07-14T00:00:00Z", request_fingerprint="play-fingerprint", fixture=fixture)

    # Confirm the shared shuffle seam repeats and resolves by rank match.
    def test_deal_sequence_is_deterministic_and_rank_matched(self):
        # Deal one stable sequence from the seeded shared primitive.
        first = engine.deal_sequence(seed="issue-140-deterministic")
        # Repeat the same deterministic fixture.
        second = engine.deal_sequence(seed="issue-140-deterministic")
        # Verify stable test output for identical seeds.
        self.assertEqual(first, second)
        # Read the exposed joker rank through the shared primitive.
        match_rank = first[0][:-1]
        # Verify the terminal reveal matches by rank.
        self.assertEqual(match_rank, first[1][-1]["card"][:-1])
        # Verify the first dealt card belongs to Andar.
        self.assertEqual("andar", first[1][0]["side"])

    # Confirm correct Andar/Bahar predictions return stake plus even-money winnings.
    def test_correct_side_returns_twice_the_wager(self):
        # Build one winning Andar prediction.
        round_state = self.round(side="andar", wager=12.5)
        # Verify the documented winner and returned amount.
        self.assertEqual(("andar", "win", 25.0, 12.5), (round_state["winning_side"], round_state["outcome"], round_state["payout"], round_state["net"]))
        # Verify the transparent sequence stops on the matching rank.
        self.assertTrue(round_state["dealt_cards"][-1]["matched"])

    # Confirm an incorrect side prediction returns no tokens.
    def test_incorrect_side_loses_the_wager(self):
        # Build one losing Bahar prediction against an Andar match.
        round_state = self.round(side="bahar", wager=9)
        # Verify no returned-token credit is requested.
        self.assertEqual(("loss", 0.0, -9.0), (round_state["outcome"], round_state["payout"], round_state["net"]))

    # Confirm malformed wagers, sides, sequence order, and match markers fail closed.
    def test_invalid_boundaries(self):
        # Reject boolean wagers despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed wager boundary.
            engine.normalize_wager(True)
        # Reject unsupported side aliases.
        with self.assertRaises(ValidationError):
            # Exercise the side enumeration boundary.
            engine.normalize_side("middle")
        # Reject a sequence that starts with Bahar.
        with self.assertRaises(ValidationError):
            # Exercise the alternating-order invariant.
            engine.validate_sequence("5H", [{"side": "bahar", "card": "5S", "matched": True}])
        # Reject a marker that lies about the rank match.
        with self.assertRaises(ValidationError):
            # Exercise match-marker consistency.
            engine.validate_sequence("5H", [{"side": "andar", "card": "9S", "matched": True}])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
