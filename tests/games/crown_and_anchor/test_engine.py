# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Crown and Anchor pure-engine tests for issue #133."""

# Import unittest so the focused module can run without central discovery edits.
import unittest
# Import public validation and conflict errors for negative-path assertions.
from casino.errors import ConflictError, ValidationError
# Import the isolated pure engine under test.
from casino.games.crown_and_anchor import engine


# Cover symbol-wager validation, dice mapping, and paytable settlement.
class CrownAndAnchorEngineTests(unittest.TestCase):
    # Verify three dice can pay one covered symbol multiple times in one round.
    def test_settle_counts_three_symbol_dice(self):
        # Normalize a two-symbol wager map in canonical order.
        wagers = engine.normalize_wagers({"crown": 2, "anchor": "3.00"})
        # Settle two crowns and one spade against the covered symbols.
        result = engine.settle(wagers, [1, 1, 6])
        # Assert ordered face-to-symbol mapping is stable.
        self.assertEqual(result["symbols"], ["crown", "crown", "spade"])
        # Assert the covered crown receives a two-hit return at two-to-one net.
        self.assertEqual(result["settlements"][0]["returned"], 6.0)
        # Assert uncovered dice do not pay the anchor stake.
        self.assertEqual(result["settlements"][1]["returned"], 0.0)
        # Assert aggregate net equals returned credits minus all covered stakes.
        self.assertEqual(result["net"], 1.0)

    # Verify invalid dice cannot be coerced into a settlement.
    def test_invalid_faces_fail_closed(self):
        # Assert out-of-range faces are rejected before settlement.
        with self.assertRaises(ValidationError):
            # Attempt to map an impossible die face.
            engine.symbols_from_faces([1, 2, 7])

    # Verify request ids cannot represent two different wager fingerprints.
    def test_record_round_rejects_conflicting_replay(self):
        # Create one empty player-owned state document.
        state = engine.default_state()
        # Store the first settled row under a client request id.
        engine.record_round(state, {"client_request_id": "same", "request_fingerprint": "one"})
        # Assert conflicting reuse of the same request id fails closed.
        with self.assertRaises(ConflictError):
            # Attempt to store a different command under the same public identity.
            engine.record_round(state, {"client_request_id": "same", "request_fingerprint": "two"})


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest's standard command-line runner.
    unittest.main()
