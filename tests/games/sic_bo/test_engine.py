# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic Sic Bo rule tests mapped to DICE-001 and LEDGER-023."""

# Import the dependency-free standard unit-test runner.
import unittest

# Import project-standard validation errors for boundary assertions.
from casino.errors import ValidationError
# Import the isolated game engine for deterministic validation and settlement checks.
from casino.games.sic_bo import engine
# Import the immutable catalog separately for complete-position assertions.
from casino.games.sic_bo.rules import bet_catalog


# Verify the full table profile, dice seam, and payout arithmetic.
class SicBoEngineTests(unittest.TestCase):
    # Confirm the rules surface exposes exactly fifty unique positions.
    def test_complete_fifty_position_catalog(self):
        # Build a fresh public metadata catalog.
        catalog = bet_catalog()
        # Verify the regulator-compatible table position count.
        self.assertEqual(50, len(catalog))
        # Verify every machine identifier is unique.
        self.assertEqual(50, len({row["id"] for row in catalog}))
        # Verify all fifteen distinct two-number combinations are present.
        self.assertEqual(15, len([row for row in catalog if row["kind"] == "combo"]))
        # Verify exact totals cover four through seventeen with documented odds.
        self.assertEqual(list(range(4, 18)), [row["selection"] for row in catalog if row["kind"] == "total"])

    # Confirm injected bounded indices produce reproducible ordinary dice.
    def test_server_dice_seam_is_deterministic_and_bounded(self):
        # Store one zero-based deterministic sequence for faces one, three, and six.
        values = iter([0, 2, 5])
        # Roll through the same bounded source contract used by production entropy.
        dice = engine.roll_dice(lambda upper: next(values))
        # Verify exact one-based face conversion and reveal order.
        self.assertEqual([1, 3, 6], dice)
        # Reject a broken entropy source instead of wrapping an invalid result.
        with self.assertRaises(ValueError):
            # Exercise the upper-bound failure path.
            engine.roll_dice(lambda upper: upper)

    # Confirm every wager family and triple exception uses the documented odds.
    def test_wager_family_boundaries(self):
        # Cover small, total, combination, and one-of-a-kind with a non-triple result.
        ordinary = [1, 2, 4]
        # Verify non-triple small wins at even money.
        self.assertEqual(1, engine.winning_net_odds("small", ordinary))
        # Verify big loses for a total of seven.
        self.assertEqual(0, engine.winning_net_odds("big", ordinary))
        # Verify total seven uses the 12-to-1 row.
        self.assertEqual(12, engine.winning_net_odds("total:7", ordinary))
        # Verify a covered two-number combination wins at 5 to 1.
        self.assertEqual(5, engine.winning_net_odds("combo:1:4", ordinary))
        # Verify a single face occurrence pays 1 to 1.
        self.assertEqual(1, engine.winning_net_odds("single:2", ordinary))
        # Cover all triple-specific rules with three matching threes.
        triple = [3, 3, 3]
        # Verify range bets lose despite the total falling inside small.
        self.assertEqual(0, engine.winning_net_odds("small", triple))
        # Verify the exact total still wins on a triple.
        self.assertEqual(6, engine.winning_net_odds("total:9", triple))
        # Verify a specific double accepts at least two matching dice.
        self.assertEqual(8, engine.winning_net_odds("double:3", triple))
        # Verify the selected specific triple pays 150 to 1.
        self.assertEqual(150, engine.winning_net_odds("triple:3", triple))
        # Verify any triple pays 24 to 1.
        self.assertEqual(24, engine.winning_net_odds("any_triple", triple))
        # Verify three occurrences on a single-number position pay 3 to 1.
        self.assertEqual(3, engine.winning_net_odds("single:3", triple))

    # Confirm multiple positions settle through one exact aggregate return.
    def test_multi_position_settlement_uses_returned_credit_semantics(self):
        # Cover one even-money win, one 12-to-1 win, and one loss on a total of seven.
        wagers = {"small": 2, "total:7": 1, "double:6": 3}
        # Settle against a deterministic non-triple result.
        result = engine.settle(wagers, [1, 2, 4])
        # Verify the aggregate debit is the sum of all normalized positions.
        self.assertEqual(6.0, result["total_wager"])
        # Verify returned credits include both winning stakes plus net winnings.
        self.assertEqual(17.0, result["total_return"])
        # Verify complete net subtracts every covered position.
        self.assertEqual(11.0, result["net"])
        # Verify the aggregate outcome is a win.
        self.assertEqual("win", result["outcome"])
        # Verify every covered position receives one explanatory row.
        self.assertEqual(3, len(result["settlements"]))

    # Confirm normalization, semantic fingerprints, and state privacy fail safely.
    def test_validation_fingerprint_and_predebit_privacy(self):
        # Normalize equivalent maps supplied in different insertion order.
        first = engine.normalize_wagers({"total:7": 2, "small": 1})
        # Normalize the reverse insertion order.
        second = engine.normalize_wagers({"small": 1, "total:7": 2})
        # Verify canonical ordering produces one semantic retry fingerprint.
        self.assertEqual(engine.wager_fingerprint(first), engine.wager_fingerprint(second))
        # Build one prepared recovery row containing private dice.
        prepared = {"round_id": "sb_test", "action_id": "a", "player_id": "p", "request_fingerprint": "f", "wagers": {"small": 1.0}, "dice": [6, 6, 6], "phase": "prepared", "wager_status": "pending", "payout_status": "not_ready", "created_at": "2026-07-14T00:00:00Z"}
        # Verify public state does not reveal dice before ledger proof.
        self.assertNotIn("dice", engine.public_round(prepared))
        # Mark the wager complete to represent committed ledger evidence.
        prepared["wager_status"] = "complete"
        # Verify committed dice become available for reload rendering.
        self.assertEqual([6, 6, 6], engine.public_round(prepared)["dice"])
        # Reject unknown position identifiers before settlement.
        with self.assertRaises(ValidationError):
            # Exercise unknown-position validation.
            engine.normalize_wagers({"odd": 1})
        # Reject empty wager maps before entropy or ledger work.
        with self.assertRaises(ValidationError):
            # Exercise the required-wager boundary.
            engine.normalize_wagers({})
        # Reject excess precision instead of silently changing caller intent.
        with self.assertRaises(ValidationError):
            # Exercise the contract's exact one-cent multiple boundary.
            engine.normalize_wagers({"small": 1.005})
        # Reject malformed die vectors before rule evaluation.
        with self.assertRaises(ValidationError):
            # Exercise the exact three-dice boundary.
            engine.require_dice([1, 2])


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
