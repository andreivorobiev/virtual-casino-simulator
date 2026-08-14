# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused non-finite money-boundary tests for CORE-025, LEDGER-027, MHVP-006, and TEST-055."""

# Import deep-copy support so a corrupt candidate cannot mutate the valid fixture.
import copy
# Import strict JSON parsing for persisted-player evidence.
import json
# Import disposable directory support so no repository runtime data is touched.
import tempfile
# Import the standard unit-test framework used by the central API runner.
import unittest
# Import portable paths for isolated JSON provider roots.
from pathlib import Path
# Import mock patching so ledger tests prove provider selection never occurs.
from unittest import mock

# Import the public ledger boundary under test.
from casino.core import ledger
# Import the JSON provider for strict persistence evidence.
from casino.core import storage
# Import shared client amount validation under test.
from casino.core.validation import require_amount
# Import the independent game-local wager boundary under test.
from casino.games.multi_hand_video_poker.engine import require_wager_per_hand
# Import the standard validation and corrupt-wallet error shapes expected by rejected values.
from casino.errors import ConflictError, ValidationError


# Raise from strict JSON parsing if a non-standard numeric constant reaches disk.
def _reject_json_constant(value: str):
    # Fail with the fixed parser token name only inside isolated test diagnostics.
    raise AssertionError(f"non-standard JSON constant persisted: {value}")


# Verify shared validation, ledger isolation, game validation, and JSON persistence.
class NonfiniteMoneyTests(unittest.TestCase):
    # Return every numeric and string representation that must fail closed.
    def nonfinite_values(self):
        # Cover NaN and both infinities through decoded numbers and string conversion.
        return (
            float("nan"),  # Exercise an already-decoded JSON NaN value.
            float("inf"),  # Exercise decoded positive infinity.
            float("-inf"),  # Exercise decoded negative infinity.
            "nan",  # Exercise the string form that bypasses strict JSON parsing.
            "inf",  # Exercise a positive-infinity string.
            "-inf",  # Exercise a negative-infinity string.
        )

    # Prove shared and game-local wager helpers reject before comparisons or rounding.
    def test_wager_validators_reject_every_nonfinite_form(self):
        # Iterate over every representation accepted by Python float conversion.
        for value in self.nonfinite_values():
            # Preserve only the safe type name in subtest diagnostics.
            with self.subTest(value_type=type(value).__name__):
                # Require the shared wager boundary to reject the value.
                with self.assertRaises(ValidationError):
                    # Exercise the validator used by Roulette, Blackjack, Baccarat, Keno, Slots, and Bingo.
                    require_amount(value)
                # Require the independent Multi-Hand Video Poker copy to reject the value.
                with self.assertRaises(ValidationError):
                    # Exercise the game-local field before state construction.
                    require_wager_per_hand(value)
        # Require an integer too large for float conversion to retain a validation response.
        with self.assertRaises(ValidationError):
            # Preserve the shared validator's prior overflow-to-400 compatibility behavior.
            require_amount(10**1000)
        # Require the game-local helper to inherit the same bounded conversion behavior.
        with self.assertRaises(ValidationError):
            # Exercise the identical overflow boundary through the MHVP wager field.
            require_wager_per_hand(10**1000)

    # Prove all public ledger entry points reject before selecting a storage provider.
    def test_every_ledger_entry_point_rejects_before_provider_access(self):
        # Build call adapters for signed, magnitude, and idempotent public functions.
        calls = (
            lambda value: ledger.transact("human", value, "TEST_NONFINITE"),  # Cover signed transactions.
            lambda value: ledger.transact_once("human", value, "TEST_NONFINITE", "nonfinite-action"),  # Cover signed idempotent transactions.
            lambda value: ledger.debit("human", value, "TEST_NONFINITE"),  # Cover debit magnitude normalization.
            lambda value: ledger.debit_once("human", value, "TEST_NONFINITE", "nonfinite-debit"),  # Cover idempotent debits.
            lambda value: ledger.credit("human", value, "TEST_NONFINITE"),  # Cover credit magnitude normalization.
            lambda value: ledger.credit_once("human", value, "TEST_NONFINITE", "nonfinite-credit"),  # Cover idempotent credits.
        )
        # Replace provider selection with a sentinel that must remain unused.
        with mock.patch.object(ledger, "get_storage_provider") as provider_selector:
            # Exercise every public entry point against every non-finite form.
            for call_index, call in enumerate(calls):
                # Iterate over decoded and string representations.
                for value in self.nonfinite_values():
                    # Preserve stable call and type identities in failure diagnostics.
                    with self.subTest(call=call_index, value_type=type(value).__name__):
                        # Require one standard validation failure.
                        with self.assertRaises(ValidationError):
                            # Attempt the invalid public money operation.
                            call(value)
            # Prove validation happened before storage selection or mutation.
            provider_selector.assert_not_called()

    # Prove the JSON provider cannot replace a valid wallet with non-standard JSON.
    def test_json_provider_preserves_finite_wallet_on_nonfinite_candidate(self):
        # Allocate an isolated provider root outside the repository checkout.
        with tempfile.TemporaryDirectory(prefix="casino-nonfinite-") as temporary:
            # Build the provider under the disposable root.
            provider = storage.JsonStorageProvider(Path(temporary) / "data")
            # Construct one finite wallet fixture without using shared runtime accounts.
            valid_state = {"schema_version": 8, "players": [{"player_id": "human", "display_name": "Test", "type": "human", "balance": 5000.0, "status": "active"}]}
            # Persist the accepted baseline through the isolated JSON writer under direct test control.
            provider._save_players_document(valid_state)
            # Capture the exact valid bytes before the corrupt candidate.
            original_bytes = provider.players_path().read_bytes()
            # Copy the fixture so only the candidate contains NaN.
            corrupt_state = copy.deepcopy(valid_state)
            # Inject the value that previously serialized as invalid JSON.
            corrupt_state["players"][0]["balance"] = float("nan")
            # Require the cents-aware player publisher to reject before atomic replacement.
            with self.assertRaises(ConflictError):
                # Attempt the guarded JSON wallet writer as the final durable defense layer.
                provider._save_players_document(corrupt_state)
            # Require the original finite document to remain byte-for-byte unchanged.
            self.assertEqual(original_bytes, provider.players_path().read_bytes())
            # Parse the retained document with a strict non-standard-constant hook.
            retained = json.loads(original_bytes.decode("utf-8"), parse_constant=_reject_json_constant)
            # Require the canonical finite balance to survive the rejected write.
            self.assertEqual(5000.0, retained["players"][0]["balance"])
            # Require no invalid ledger row to have been created by the storage-only check.
            self.assertFalse(provider.ledger_path().exists())


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
