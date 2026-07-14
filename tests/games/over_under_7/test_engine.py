"""Deterministic rule tests for issue #135 Over/Under 7."""

# Import the dependency-free standard test runner.
import unittest

# Import public validation errors for boundary assertions.
from casino.errors import ValidationError
# Import only the isolated game engine under test.
from casino.games.over_under_7 import engine


# Verify dice, paytable, wager, and settlement rules.
class OverUnder7EngineTests(unittest.TestCase):
    # Confirm deterministic dice seams and total classification.
    def test_roll_dice_and_classification(self):
        # Build a deterministic sequence of zero-based dice values.
        values = iter([0, 5])
        # Roll through the injectable seam.
        dice = engine.roll_dice(lambda sides: next(values))
        # Verify one-based dice pips are returned.
        self.assertEqual((1, 6), dice)
        # Verify all three proposition classes.
        self.assertEqual(("under", "seven", "over"), (engine.classify_total(6), engine.classify_total(7), engine.classify_total(8)))

    # Confirm transparent payout rows for under, seven, and over.
    def test_settlement_profile(self):
        # Define deterministic settlement vectors.
        vectors = [({"under": 5}, (2, 4), "under", 10.0, 5.0), ({"seven": 5}, (3, 4), "seven", 25.0, 20.0), ({"over": 5}, (6, 6), "over", 10.0, 5.0)]
        # Exercise each profile row.
        for wagers, dice, outcome, returned, net in vectors:
            # Preserve the outcome in assertion output.
            with self.subTest(outcome=outcome):
                # Settle the controlled dice result.
                result = engine.settle(engine.normalize_wagers(wagers), dice)
                # Verify outcome, total return, and net movement.
                self.assertEqual((outcome, returned, net), (result["outcome"], result["total_return"], result["net"]))
                # Verify the public paytable remains present.
                self.assertEqual(["under", "seven", "over"], [row["id"] for row in result["paytable"]])

    # Confirm multi-outcome coverage settles only winning rows.
    def test_multiple_wagers_disclose_each_row(self):
        # Normalize a wager map that covers all propositions.
        wagers = engine.normalize_wagers({"under": 2, "seven": 3, "over": 4})
        # Settle an exact-seven result.
        result = engine.settle(wagers, (1, 6))
        # Verify only the seven proposition wins.
        rows = {row["outcome"]: row for row in result["settlements"]}
        # Verify each row net is transparent.
        self.assertEqual((-2.0, 12.0, -4.0), (rows["under"]["net"], rows["seven"]["net"], rows["over"]["net"]))
        # Verify total return includes stake plus 4:1 net for exactly seven.
        self.assertEqual(15.0, result["total_return"])

    # Confirm invalid public inputs fail closed.
    def test_invalid_boundaries(self):
        # Reject boolean amounts.
        with self.assertRaises(ValidationError):
            # Exercise the numeric-subtype boundary.
            engine.normalize_amount(True)
        # Reject unknown wager targets.
        with self.assertRaises(ValidationError):
            # Exercise stable target validation.
            engine.normalize_wagers({"low": 1})
        # Reject invalid dice pips.
        with self.assertRaises(ValidationError):
            # Exercise corrupted result validation.
            engine.settle({"under": 1.0}, (0, 7))
        # Reject invalid deterministic seams.
        with self.assertRaises(ValueError):
            # Exercise broken randbelow output.
            engine.roll_dice(lambda sides: sides)


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
