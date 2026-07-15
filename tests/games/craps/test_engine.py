"""Focused pure-rule tests for the issue #90 Craps engine."""

# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public validation errors used by invalid rule inputs.
from casino.errors import ValidationError
# Import only the isolated game engine under test.
from casino.games.craps import engine


# Verify the compact Pass Line and Don't Pass rules without storage or ledger access.
class CrapsEngineTests(unittest.TestCase):
    # Build one deterministic pending round for rule-table checks.
    def make_round(self, bet_type="pass_line", wager=5, suffix="1"):
        # Delegate to the public pure constructor with stable audit fields.
        return engine.create_round("player-one", bet_type, wager, f"start-{suffix}", round_id=f"craps-{suffix}", created_at="2026-07-14T00:00:00.000Z")

    # Confirm supported identifiers, wagers, and dice reject malformed inputs.
    def test_validation_boundaries(self):
        # Verify both public line wager identifiers remain stable and ordered.
        self.assertEqual(("pass_line", "dont_pass"), engine.BET_TYPES)
        # Reject an unsupported proposition bet outside the isolated first slice.
        with self.assertRaises(ValidationError):
            # Attempt to validate a deliberately unsupported field bet.
            engine.require_bet_type("field")
        # Reject booleans instead of treating true as a one-token wager.
        with self.assertRaises(ValidationError):
            # Attempt to normalize a boolean wager.
            engine.require_wager(True)
        # Reject numeric strings because OpenAPI requires a JSON number.
        with self.assertRaises(ValidationError):
            # Attempt compatibility coercion from a numeric-looking string.
            engine.require_wager("5.00")
        # Reject values carrying precision smaller than one play-token cent.
        with self.assertRaises(ValidationError):
            # Attempt to normalize a three-decimal numeric wager.
            engine.require_wager(1.001)
        # Reject non-finite wagers before ledger-compatible state is built.
        with self.assertRaises(ValidationError):
            # Attempt to normalize a NaN wager.
            engine.require_wager(float("nan"))
        # Accept integer JSON numbers and normalize them to ledger shape.
        self.assertEqual(5.0, engine.require_wager(5))
        # Accept a numeric value already exact to two decimal places.
        self.assertEqual(5.25, engine.require_wager(5.25))
        # Reject dice collections with fewer than two faces.
        with self.assertRaises(ValidationError):
            # Attempt to validate one die instead of an ordered pair.
            engine.require_dice([6])
        # Reject impossible seven-valued die faces.
        with self.assertRaises(ValidationError):
            # Attempt to validate an out-of-range second face.
            engine.require_dice([1, 7])

    # Confirm every immediate come-out result mirrors Pass and Don't Pass correctly.
    def test_come_out_terminal_table(self):
        # Define bet, dice, outcome, resolution, returned amount, and transaction type cases.
        cases = [
            ("pass_line", [3, 4], "win", "natural", 10.0, "CRAPS_PAYOUT_CREDIT"),  # Pass wins on seven.
            ("dont_pass", [3, 4], "loss", "natural", 0.0, None),  # Don't Pass loses on seven.
            ("pass_line", [1, 1], "loss", "craps", 0.0, None),  # Pass loses on two.
            ("dont_pass", [1, 1], "win", "craps", 10.0, "CRAPS_PAYOUT_CREDIT"),  # Don't Pass wins on two.
            ("pass_line", [6, 6], "loss", "bar_twelve", 0.0, None),  # Pass loses on twelve.
            ("dont_pass", [6, 6], "push", "bar_twelve", 5.0, "CRAPS_PUSH_REFUND"),  # Don't Pass pushes on twelve.
        ]
        # Exercise every mirrored come-out table row independently.
        for index, (bet_type, dice, outcome, resolution, amount, transaction_type) in enumerate(cases):
            # Name each table case clearly when an assertion fails.
            with self.subTest(bet_type=bet_type, dice=dice):
                # Create a fresh pending line wager for this rule row.
                round_state = self.make_round(bet_type=bet_type, suffix=str(index))
                # Apply the authoritative deterministic come-out dice.
                roll = engine.apply_roll(round_state, dice, f"roll-{index}", created_at="2026-07-14T00:00:01.000Z")
                # Verify every immediate row closes the round.
                self.assertEqual("settled", round_state["phase"])
                # Verify the line-specific terminal classification.
                self.assertEqual(outcome, round_state["outcome"])
                # Verify the stable localization-safe resolution key.
                self.assertEqual(resolution, roll["resolution"])
                # Verify returned credit math distinguishes payout, refund, and loss.
                self.assertEqual(amount, engine.settlement_amount(round_state))
                # Verify ledger transaction selection matches the outcome.
                self.assertEqual(transaction_type, engine.settlement_transaction_type(round_state))

    # Confirm a Pass point persists across no-decision rolls and pays on a hit.
    def test_point_lifecycle_and_reload_fields(self):
        # Create one deterministic Pass Line wager.
        round_state = self.make_round(bet_type="pass_line", wager=4, suffix="point")
        # Establish point eight on the come-out roll.
        established = engine.apply_roll(round_state, [4, 4], "roll-point-1", created_at="2026-07-14T00:00:01.000Z")
        # Verify the round remains active in point phase.
        self.assertEqual("point", round_state["phase"])
        # Verify point eight is durable in state and the roll audit.
        self.assertEqual(8, round_state["point"])
        # Verify the transition exposes the exact point-establishment key.
        self.assertEqual("point_established", established["resolution"])
        # Roll five without changing the active point.
        continued = engine.apply_roll(round_state, [2, 3], "roll-point-2", created_at="2026-07-14T00:00:02.000Z")
        # Verify a non-terminal roll keeps the point after the action.
        self.assertEqual(8, continued["point_after"])
        # Verify the stable no-decision key for frontend status.
        self.assertEqual("no_decision", continued["resolution"])
        # Hit point eight to complete the Pass Line wager.
        completed = engine.apply_roll(round_state, [3, 5], "roll-point-3", created_at="2026-07-14T00:00:03.000Z")
        # Verify the point-hit key and terminal win.
        self.assertEqual("point_hit", completed["resolution"])
        # Verify the completed round is a Pass win.
        self.assertEqual("win", round_state["outcome"])
        # Verify one-based roll indexes remain stable across reload rendering.
        self.assertEqual([1, 2, 3], [roll["roll_index"] for roll in round_state["rolls"]])
        # Verify the returned credit includes the four-token stake and winnings.
        self.assertEqual(8.0, engine.settlement_amount(round_state))

    # Confirm Don't Pass wins when seven appears before the established point.
    def test_dont_pass_seven_out(self):
        # Create one deterministic Don't Pass wager.
        round_state = self.make_round(bet_type="dont_pass", wager=3, suffix="seven")
        # Establish point six without settling the line.
        engine.apply_roll(round_state, [3, 3], "roll-seven-1", created_at="2026-07-14T00:00:01.000Z")
        # Roll seven before repeating the point.
        terminal = engine.apply_roll(round_state, [4, 3], "roll-seven-2", created_at="2026-07-14T00:00:02.000Z")
        # Verify the exact seven-out resolution key.
        self.assertEqual("seven_out", terminal["resolution"])
        # Verify Don't Pass wins on the seven-out.
        self.assertEqual("win", round_state["outcome"])
        # Verify the even-money returned credit is twice the wager.
        self.assertEqual(6.0, engine.settlement_amount(round_state))

    # Confirm durable action history preserves exact dice without public mutation leaks.
    def test_roll_replay_and_archive_lookup(self):
        # Create one state document holding a fresh active round.
        state = engine.default_state()
        # Build one deterministic Pass Line round.
        round_state = self.make_round(suffix="archive")
        # Install the round in the only actionable state slot.
        state["active_round"] = round_state
        # Settle immediately with a natural seven.
        first = engine.apply_roll(round_state, [3, 4], "roll-archive", created_at="2026-07-14T00:00:01.000Z")
        # Replay the exact action directly through the pure engine.
        second = engine.apply_roll(round_state, [1, 1], "roll-archive", created_at="2026-07-14T00:00:02.000Z")
        # Verify replay returns the original roll rather than the supplied new dice.
        self.assertEqual(first, second)
        # Verify the round contains only one authoritative roll action.
        self.assertEqual(1, len(round_state["rolls"]))
        # Archive the terminal round into the private durable journal.
        engine.archive_round(state, round_state)
        # Verify the active slot is empty after terminal archival.
        self.assertIsNone(state["active_round"])
        # Verify global action lookup finds the retained roll and owning round.
        action = engine.action_for_request(state, "roll-archive")
        # Verify the retained action kind is a roll.
        self.assertEqual("roll", action[0])
        # Build a detached public state snapshot.
        public = engine.public_state(state)
        # Mutate the public dice copy to test response isolation.
        public["recent_rounds"][0]["rolls"][0]["dice"][0] = 6
        # Verify the persisted authoritative first die remains unchanged.
        self.assertEqual(3, round_state["rolls"][0]["dice"][0])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
