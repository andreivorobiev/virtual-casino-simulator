# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic rule tests for issue #140 and CARD-001."""

# Import the dependency-free standard test runner.
import unittest
# Import exact rational arithmetic for house-edge proofs without floating-point drift.
from fractions import Fraction
# Import exact combination counts for first-match position enumeration.
from math import comb

# Import shared public errors for invalid transition assertions.
from casino.errors import ValidationError
# Import only the isolated game engine under test.
from casino.games.andar_bahar import engine


# Verify match-rank rules, alternating sequence, and deterministic test seams.
class AndarBaharEngineTests(unittest.TestCase):
    # Build one explicit fixture round with a controlled winning side.
    def round(self, side="andar", wager=10, winner="andar"):
        # Define the Andar-winning alternating reveal sequence.
        andar_fixture = [{"side": "andar", "card": "2C", "matched": False}, {"side": "bahar", "card": "QS", "matched": False}, {"side": "andar", "card": "7D", "matched": True}]
        # Define the Bahar-winning alternating reveal sequence.
        bahar_fixture = [{"side": "andar", "card": "2C", "matched": False}, {"side": "bahar", "card": "7D", "matched": True}]
        # Select the requested exact terminal side without changing production dealing.
        fixture = {"match_card": "7H", "dealt_cards": andar_fixture if winner == "andar" else bahar_fixture}
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

    # Confirm correct predictions use the selected side's exact returned-token price.
    def test_correct_side_uses_published_multiplier(self):
        # Build one winning Andar prediction.
        round_state = self.round(side="andar", wager=12.5)
        # Build one winning Bahar prediction at the unchanged even-money price.
        bahar_round = self.round(side="bahar", wager=12.5, winner="bahar")
        # Verify Andar returns 1.90x and its net is rounded to ledger precision.
        self.assertEqual(("andar", "win", 23.75, 11.25), (round_state["winning_side"], round_state["outcome"], round_state["payout"], round_state["net"]))
        # Verify Bahar retains the frozen even-money return.
        self.assertEqual(("bahar", "win", 25.0, 12.5), (bahar_round["winning_side"], bahar_round["outcome"], bahar_round["payout"], bahar_round["net"]))
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


# Prove the side prices against the exact first-match distribution. (AB-001, issue #409)
class AndarBaharEconomicsTests(unittest.TestCase):
    # Enumerate the earliest position occupied by one of the three remaining matching-rank cards.
    def test_exact_side_probabilities_and_rtp_are_house_positive(self):
        # Count all unordered placements of three rank matches among the fifty-one remaining cards.
        total_placements = comb(51, 3)
        # Count placements whose earliest matching card falls on an odd one-based Andar position.
        andar_placements = sum(comb(51 - position, 2) for position in range(1, 50, 2))
        # Derive the complementary Bahar placement count.
        bahar_placements = total_placements - andar_placements
        # Reduce both exact probabilities to the independently reported issue fractions.
        self.assertEqual((Fraction(429, 833), Fraction(404, 833)), (Fraction(andar_placements, total_placements), Fraction(bahar_placements, total_placements)))
        # Multiply exact win probability by each total-return price.
        andar_rtp = Fraction(andar_placements, total_placements) * Fraction(19, 10)
        # Multiply exact Bahar probability by its unchanged even-money total return.
        bahar_rtp = Fraction(bahar_placements, total_placements) * 2
        # Require both sides to remain below break-even with the approved 1.90x/2.00x prices.
        self.assertEqual((Fraction(8151, 8330), Fraction(808, 833)), (andar_rtp, bahar_rtp))
        # Fail if either future price reintroduces a player-positive side.
        self.assertTrue(andar_rtp < 1 and bahar_rtp < 1)

    # Keep the legacy scalar exact while exposing only the approved two-side table.
    def test_legacy_scalar_and_additive_table_are_exact(self):
        # Require the frozen scalar to remain an integer for old v1 clients.
        self.assertEqual((2, int), (engine.RETURN_MULTIPLIER, type(engine.RETURN_MULTIPLIER)))
        # Require the new table and lookup to preserve the owner-approved values.
        self.assertEqual(({"andar": 1.9, "bahar": 2.0}, 1.9, 2.0), (engine.RETURN_MULTIPLIERS, engine.return_multiplier("andar"), engine.return_multiplier("bahar")))
        # Reject unsupported pricing keys instead of falling back to the scalar.
        with self.assertRaises(ValidationError):
            # Exercise the fail-closed price lookup.
            engine.return_multiplier("middle")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
