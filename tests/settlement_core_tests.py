"""Listener-free regression tests for the issue #430 settlement-core checkpoint."""

# Import non-finite constants for money-boundary rejection cases.
import math
# Import unittest for the standalone focused suite.
import unittest

# Import the new route-free adapter under direct test.
from casino.core.settlement import LEDGER_PROOF_SCAN_LIMIT, SettlementAdapter
# Import public errors used by the adapter's stable failure contract.
from casino.errors import ConflictError, ValidationError


# Build one committed ledger row with the canonical action evidence under test.
def _event(
    *,
    player_id="player-a",
    game="example-game",
    round_id="round-1",
    transaction_type="wager",
    amount=-5.0,
    action_key="action-1",
    request_fingerprint="fingerprint-1",
    extra_details=None,
):
    # Preserve supplied game-specific evidence before adding canonical fields.
    details = dict(extra_details or {})
    # Add the game-owned identity used by response and recovery lookup.
    details["game_action_key"] = action_key
    # Add the upstream semantic fingerprint used to distinguish changed reuse.
    details["request_fingerprint"] = request_fingerprint
    # Add the portable round identity duplicated inside ledger details.
    details["round_id"] = round_id
    # Return one complete JSON-compatible ledger event.
    return {
        # Record a stable ledger identity for exact-object assertions.
        "ledger_id": "ledger-1",
        # Record the authenticated wallet owner.
        "player_id": player_id,
        # Record the game action namespace.
        "game": game,
        # Record the round identity on the canonical ledger row.
        "round_id": round_id,
        # Record the movement meaning.
        "transaction_type": transaction_type,
        # Record the signed fake-money movement.
        "amount": amount,
        # Attach canonical plus game-specific audit evidence.
        "details": details,
    }


# Capture public-ledger calls while keeping focused tests provider-free.
class _LedgerSeam:
    # Initialize empty call logs and configurable outcomes.
    def __init__(self) -> None:
        # Record every debit-once call for sign-routing assertions.
        self.debit_calls = []
        # Record every credit-once call for sign-routing assertions.
        self.credit_calls = []
        # Record every recent-ledger lookup for bounded proof assertions.
        self.read_calls = []
        # Return this exact debit result unless a test configures an exception.
        self.debit_result = (_event(), False)
        # Return this exact credit result unless a test configures an exception.
        self.credit_result = (_event(transaction_type="payout", amount=7.5), False)
        # Raise this exception from debit-once when a race test configures it.
        self.debit_error = None
        # Raise this exception from credit-once when a race test configures it.
        self.credit_error = None
        # Return these exact rows from the bounded proof reader.
        self.rows = []

    # Capture a storage-atomic debit proposal.
    def debit_once(self, **kwargs):
        # Preserve a shallow snapshot so later caller mutation cannot change the assertion.
        self.debit_calls.append({**kwargs, "details": dict(kwargs["details"])})
        # Raise the configured provider conflict when requested.
        if self.debit_error is not None:
            # Preserve the exact exception instance for re-raise assertions.
            raise self.debit_error
        # Return the configured event and replay marker unchanged.
        return self.debit_result

    # Capture a storage-atomic credit proposal.
    def credit_once(self, **kwargs):
        # Preserve a shallow snapshot so later caller mutation cannot change the assertion.
        self.credit_calls.append({**kwargs, "details": dict(kwargs["details"])})
        # Raise the configured provider conflict when requested.
        if self.credit_error is not None:
            # Preserve the exact exception instance for re-raise assertions.
            raise self.credit_error
        # Return the configured event and replay marker unchanged.
        return self.credit_result

    # Return bounded player history for proof reconstruction.
    def read_recent(self, player_id, limit):
        # Record the exact player and bound selected by the adapter.
        self.read_calls.append((player_id, limit))
        # Return a fresh list so the adapter cannot mutate the seam's fixture.
        return list(self.rows)

    # Build an adapter bound only to these listener-free seams.
    def adapter(self) -> SettlementAdapter:
        # Inject all three public-ledger boundaries under test.
        return SettlementAdapter(debit_once=self.debit_once, credit_once=self.credit_once, read_recent=self.read_recent)


# Prove the settlement checkpoint is additive, atomic, and fail closed.
class SettlementAdapterTests(unittest.TestCase):
    # Return the shared valid action arguments used by focused variants.
    def _arguments(self) -> dict:
        # Build one complete internal action identity without route or game dependencies.
        return {
            # Select a fixed game namespace.
            "game_id": "example-game",
            # Select a fixed authenticated wallet.
            "player_id": "player-a",
            # Select a signed wager debit.
            "signed_amount": -5,
            # Select the wager transaction meaning.
            "transaction_type": "wager",
            # Select a fixed round identity.
            "round_id": "round-1",
            # Select a fixed game-level action key.
            "action_key": "action-1",
            # Select an upstream semantic request digest.
            "request_fingerprint": "fingerprint-1",
        }

    # Prove negative amounts route to debit-once and preserve every caller detail.
    def test_debit_routing_adds_canonical_details_without_mutating_caller(self):
        # Build isolated ledger seams.
        seam = _LedgerSeam()
        # Build one caller-owned details object with nested audit content.
        caller_details = {"bet_id": "bet-7", "outcome": {"number": 17}}
        # Keep the exact configured provider result for identity comparison.
        expected = seam.debit_result
        # Apply a value requiring two-decimal normalization.
        result = seam.adapter().apply_action_once(**{**self._arguments(), "signed_amount": -5.126}, details=caller_details)
        # Return the provider tuple without wrapping or changing its replay marker.
        self.assertIs(result, expected)
        # Route only the negative movement through debit-once.
        self.assertEqual(len(seam.debit_calls), 1)
        # Never invoke the credit path for a negative movement.
        self.assertEqual(seam.credit_calls, [])
        # Pass the positive debit magnitude at ledger precision.
        self.assertEqual(seam.debit_calls[0]["amount"], 5.13)
        # Preserve every caller field in the provider audit envelope.
        self.assertEqual(seam.debit_calls[0]["details"]["bet_id"], "bet-7")
        # Preserve nested caller evidence by value.
        self.assertEqual(seam.debit_calls[0]["details"]["outcome"], {"number": 17})
        # Add the game-owned action identity.
        self.assertEqual(seam.debit_calls[0]["details"]["game_action_key"], "action-1")
        # Add the upstream request fingerprint.
        self.assertEqual(seam.debit_calls[0]["details"]["request_fingerprint"], "fingerprint-1")
        # Add the portable round identity.
        self.assertEqual(seam.debit_calls[0]["details"]["round_id"], "round-1")
        # Leave the caller-owned mapping completely unchanged.
        self.assertEqual(caller_details, {"bet_id": "bet-7", "outcome": {"number": 17}})
        # Avoid any proof-before-write history scan on the ordinary commit path.
        self.assertEqual(seam.read_calls, [])

    # Prove positive amounts route to credit-once and preserve provider replay evidence.
    def test_credit_routing_returns_provider_replay_exactly(self):
        # Build isolated ledger seams.
        seam = _LedgerSeam()
        # Configure the provider to report an exact replay.
        seam.credit_result = (_event(transaction_type="payout", amount=7.5), True)
        # Apply one positive settlement credit.
        result = seam.adapter().apply_action_once(**{**self._arguments(), "signed_amount": 7.5, "transaction_type": "payout"})
        # Return the exact configured provider tuple.
        self.assertIs(result, seam.credit_result)
        # Route only the positive movement through credit-once.
        self.assertEqual(len(seam.credit_calls), 1)
        # Never invoke the debit path for a positive movement.
        self.assertEqual(seam.debit_calls, [])
        # Preserve the exact positive amount.
        self.assertEqual(seam.credit_calls[0]["amount"], 7.5)
        # Avoid a history scan when the provider resolves replay itself.
        self.assertEqual(seam.read_calls, [])

    # Prove malformed money and detail inputs fail before any ledger seam runs.
    def test_validation_rejects_nonfinite_zero_boolean_and_scalar_details(self):
        # Enumerate each dangerous signed-amount representation.
        invalid_amounts = (
            # Reject positive infinity.
            math.inf,
            # Reject negative infinity.
            -math.inf,
            # Reject NaN.
            math.nan,
            # Reject exact zero.
            0,
            # Reject values that round to zero at ledger precision.
            0.004,
            # Reject bool-as-number.
            True,
        )
        # Exercise every invalid amount independently.
        for amount in invalid_amounts:
            # Keep one fresh seam so call absence is attributable.
            seam = _LedgerSeam()
            # Identify the invalid representation without putting it in a public diagnostic.
            with self.subTest(amount=amount):
                # Require the public validation envelope.
                with self.assertRaises(ValidationError):
                    # Attempt the malformed action without opening storage.
                    seam.adapter().apply_action_once(**{**self._arguments(), "signed_amount": amount})
                # Prove no money function ran.
                self.assertEqual((seam.debit_calls, seam.credit_calls), ([], []))
        # Build a fresh seam for malformed detail shape proof.
        seam = _LedgerSeam()
        # Require object-only audit details.
        with self.assertRaisesRegex(ValidationError, "^Settlement details must be an object$"):
            # Pass a scalar that cannot preserve named audit evidence.
            seam.adapter().apply_action_once(**self._arguments(), details="not-an-object")
        # Prove the malformed detail shape never reached money movement.
        self.assertEqual((seam.debit_calls, seam.credit_calls), ([], []))

    # Prove callers cannot override canonical audit identity fields.
    def test_conflicting_reserved_details_fail_before_ledger_access(self):
        # Exercise every reserved detail independently.
        for key in ("game_action_key", "request_fingerprint", "round_id"):
            # Keep one fresh seam so call absence is attributable.
            seam = _LedgerSeam()
            # Identify only the reserved field name in the focused test report.
            with self.subTest(key=key):
                # Require a fail-closed conflict rather than silently replacing evidence.
                with self.assertRaisesRegex(ConflictError, "^Settlement details conflict with canonical action identity$"):
                    # Supply one conflicting reserved value.
                    seam.adapter().apply_action_once(**self._arguments(), details={key: "different"})
                # Prove no money function ran after ambiguous evidence.
                self.assertEqual((seam.debit_calls, seam.credit_calls), ([], []))

    # Prove lookup ignores other player/game/action rows and returns exact matching proof.
    def test_find_action_is_scoped_and_returns_exact_event(self):
        # Build isolated ledger seams.
        seam = _LedgerSeam()
        # Build the exact event that alone may satisfy the lookup.
        expected = _event()
        # Mix unrelated identities around the valid row.
        seam.rows = [
            # Keep a same-named action under another player isolated.
            _event(player_id="player-b"),
            # Keep a same-named action under another game isolated.
            _event(game="other-game"),
            # Keep another action key in the same game isolated.
            _event(action_key="action-2"),
            # Provide the exact compatible proof.
            expected,
        ]
        # Locate the committed action through every immutable dimension.
        result = seam.adapter().find_action(**self._arguments())
        # Return the exact stored object without reconstructing audit data.
        self.assertIs(result, expected)
        # Read only the authenticated player's bounded proof window.
        self.assertEqual(seam.read_calls, [("player-a", LEDGER_PROOF_SCAN_LIMIT)])

    # Prove reused scoped identities fail closed across round/type/amount/fingerprint.
    def test_find_action_rejects_changed_scoped_identity_dimensions(self):
        # Define one conflicting event for each immutable dimension not in provider scope.
        conflicts = (
            # Reject reuse under another round.
            _event(round_id="round-2"),
            # Reject reuse under another transaction meaning.
            _event(transaction_type="payout"),
            # Reject reuse for another signed amount.
            _event(amount=-7.0),
            # Reject reuse for another request fingerprint.
            _event(request_fingerprint="fingerprint-2"),
        )
        # Exercise each conflict independently.
        for event in conflicts:
            # Keep one fresh seam and one candidate row.
            seam = _LedgerSeam()
            # Return the conflicting row from the defensive reader.
            seam.rows = [event]
            # Identify the ledger fixture without weakening the public error contract.
            with self.subTest(event=event):
                # Require fail-closed conflict for the reused scoped identity.
                with self.assertRaises(ConflictError):
                    # Search for the expected action dimensions.
                    seam.adapter().find_action(**self._arguments())

    # Prove a racing provider conflict can recover only a compatible committed winner.
    def test_provider_conflict_recovers_compatible_winner(self):
        # Build isolated ledger seams.
        seam = _LedgerSeam()
        # Simulate the losing provider call observing a different tentative detail fingerprint.
        seam.debit_error = ConflictError("Ledger action key was reused with different transaction semantics")
        # Publish the winner with the same logical request fingerprint but different tentative entropy.
        winner = _event(extra_details={"entropy": 7})
        # Return the winner during post-conflict reconstruction.
        seam.rows = [winner]
        # Attempt the same logical action with a different tentative entropy value.
        event, replayed = seam.adapter().apply_action_once(**self._arguments(), details={"entropy": 9})
        # Return the exact committed winner rather than the losing proposal.
        self.assertIs(event, winner)
        # Mark compatible recovery as a replay.
        self.assertIs(replayed, True)
        # Attempt the storage-atomic movement only once.
        self.assertEqual(len(seam.debit_calls), 1)
        # Perform exactly one post-conflict proof lookup.
        self.assertEqual(seam.read_calls, [("player-a", LEDGER_PROOF_SCAN_LIMIT)])

    # Prove a provider conflict with no compatible winner preserves the original error.
    def test_provider_conflict_without_proof_reraises_original_error(self):
        # Build isolated ledger seams.
        seam = _LedgerSeam()
        # Retain one exact provider exception instance.
        original = ConflictError("Provider rejected conflicting action")
        # Raise the configured provider error on the money attempt.
        seam.debit_error = original
        # Return only unrelated proof that must not satisfy this request.
        seam.rows = [_event(player_id="player-b"), _event(game="other-game")]
        # Capture the adapter's final conflict.
        with self.assertRaises(ConflictError) as captured:
            # Attempt the action through the storage-atomic seam.
            seam.adapter().apply_action_once(**self._arguments())
        # Preserve the exact provider exception when recovery finds nothing compatible.
        self.assertIs(captured.exception, original)
        # Perform one bounded recovery lookup after the provider conflict.
        self.assertEqual(seam.read_calls, [("player-a", LEDGER_PROOF_SCAN_LIMIT)])


# Run this focused checkpoint directly without central registration.
if __name__ == "__main__":
    # Exit non-zero when any listener-free regression fails.
    unittest.main()
