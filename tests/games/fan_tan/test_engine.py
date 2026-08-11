# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic Fan-Tan rules tests for GitHub issue #137."""

# Import the dependency-free standard test runner.
import unittest
# Import shared public errors for invalid transition assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated game engine under test.
from casino.games.fan_tan import engine


# Verify count resolution, paytable math, and deterministic seams.
class FanTanEngineTests(unittest.TestCase):
    # Confirm every modulo branch maps to the documented residue labels.
    def test_residue_mapping_uses_groups_of_four(self):
        # Verify non-zero modulo counts keep their visible remainder.
        self.assertEqual(("1", "2", "3"), (engine.residue_for_count(49), engine.residue_for_count(50), engine.residue_for_count(51)))
        # Verify modulo zero maps to the table outcome labeled four.
        self.assertEqual("4", engine.residue_for_count(52))

    # Confirm a winning residue returns stake plus three-to-one net winnings.
    def test_settlement_returns_transparent_three_to_one_paytable(self):
        # Normalize a mixed wager map before settlement.
        wagers = engine.normalize_wagers({"1": 2, "4": 5})
        # Settle a count that leaves residue four.
        result = engine.settle(wagers, 52)
        # Verify result residue, single debit amount, total return, and net.
        self.assertEqual(("4", 7.0, 20.0, 13.0), (result["residue"], result["total_wager"], result["total_return"], result["net"]))
        # Verify the educational counting data identifies groups and leftover residue.
        self.assertEqual({"step": "residue", "remaining": 4}, result["counting_steps"][-1])

    # Confirm validation boundaries fail before ledger access.
    def test_invalid_wagers_and_counts_fail_closed(self):
        # Reject boolean amounts despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed wager boundary.
            engine.normalize_amount(True)
        # Reject unsupported residue keys.
        with self.assertRaises(ValidationError):
            # Exercise the residue enumeration boundary.
            engine.normalize_wagers({"5": 1})
        # Reject counts outside the frozen simulator profile.
        with self.assertRaises(ValidationError):
            # Exercise the lower pile-count boundary.
            engine.residue_for_count(48)

    # Confirm deterministic identity helpers and duplicate state recording.
    def test_round_identity_and_duplicate_recording_are_stable(self):
        # Derive the same round id twice from the same player and action.
        self.assertEqual(engine.round_id_for("player", "action"), engine.round_id_for("player", "action"))
        # Build a fresh state document.
        state = engine.default_state()
        # Build a representative settled row.
        row = {"action_id": "a1", "request_fingerprint": "f1"}
        # Record the row once.
        engine.record_round(state, row)
        # Verify identical retries return the existing row.
        self.assertIs(row, engine.record_round(state, row))
        # Reject a conflicting duplicate action identity.
        with self.assertRaises(ConflictError):
            # Exercise the stale idempotency boundary.
            engine.record_round(state, {"action_id": "a1", "request_fingerprint": "f2"})


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
