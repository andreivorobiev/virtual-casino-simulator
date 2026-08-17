# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free regression tests for the issue #430 boundary and #703 alias retirement."""

# Import Python syntax-tree support for repository-wide call-shape evidence.
import ast
# Import signature inspection for the exact canonical gateway boundary.
import inspect
# Import non-finite constants for money-boundary rejection cases.
import math
# Import unittest for the standalone focused suite.
import unittest
# Import portable repository paths for source-derived mutation-call validation.
from pathlib import Path

# Import the new route-free adapter under direct test.
from casino.core.settlement import GameSettlementGateway, LEGACY_PROOF_FALLBACK_LIMIT, SettlementAdapter
# Import public errors used by the adapter's stable failure contract.
from casino.errors import ConflictError, ValidationError
# Import the repository validator so the permanent test exercises its actual catalog-derived gate.
from scripts import validate_module_boundaries


# Build one committed ledger row with the canonical action evidence under test.
def _event(
    *,
    player_id="player-a",  # Select the fixture wallet identity.
    game="example-game",  # Select the fixture game namespace.
    round_id="round-1",  # Select the fixture round identity.
    transaction_type="wager",  # Select the fixture ledger meaning.
    amount=-5.0,  # Select the fixture signed movement.
    action_key="action-1",  # Select the fixture game action identity.
    request_fingerprint="fingerprint-1",  # Select the fixture request semantics.
    extra_details=None,  # Extend the fixture audit envelope when needed.
):  # Return one complete committed-event fixture.
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
        # Record every provider-indexed lookup for exact identity assertions.
        self.find_calls = []
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
        # Return this exact event from the provider point lookup.
        self.indexed_event = None

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

    # Return one provider-indexed action without scanning history.
    def find_action(self, player_id, game, action_key):
        # Record the canonical identity dimensions selected by the adapter.
        self.find_calls.append((player_id, game, action_key))
        # Return the configured exact event or miss.
        return self.indexed_event

    # Build an adapter bound only to these listener-free seams.
    def adapter(self) -> SettlementAdapter:
        # Inject every public-ledger boundary under test.
        return SettlementAdapter(debit_once=self.debit_once, credit_once=self.credit_once, find_action=self.find_action, read_recent=self.read_recent)


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
        # Return the exact identity selected by the provider index.
        seam.indexed_event = expected
        # Locate the committed action through every immutable dimension.
        result = seam.adapter().find_action(**self._arguments())
        # Return the exact stored object without reconstructing audit data.
        self.assertIs(result, expected)
        # Query only the canonical player, game, and action identity.
        self.assertEqual(seam.find_calls, [("player-a", "example-game", "action-1")])
        # Never scan recent history when the indexed seam is present.
        self.assertEqual(seam.read_calls, [])

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
            # Return the conflicting row from the indexed provider seam.
            seam.indexed_event = event
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
        # Return the winner during post-conflict indexed reconstruction.
        seam.indexed_event = winner
        # Attempt the same logical action with a different tentative entropy value.
        event, replayed = seam.adapter().apply_action_once(**self._arguments(), details={"entropy": 9})
        # Return the exact committed winner rather than the losing proposal.
        self.assertIs(event, winner)
        # Mark compatible recovery as a replay.
        self.assertIs(replayed, True)
        # Attempt the storage-atomic movement only once.
        self.assertEqual(len(seam.debit_calls), 1)
        # Perform exactly one post-conflict indexed proof lookup.
        self.assertEqual(seam.find_calls, [("player-a", "example-game", "action-1")])
        # Never scan history during indexed recovery.
        self.assertEqual(seam.read_calls, [])

    # Prove a provider conflict with no compatible winner preserves the original error.
    def test_provider_conflict_without_proof_reraises_original_error(self):
        # Build isolated ledger seams.
        seam = _LedgerSeam()
        # Retain one exact provider exception instance.
        original = ConflictError("Provider rejected conflicting action")
        # Raise the configured provider error on the money attempt.
        seam.debit_error = original
        # Return an index miss so no unrelated row can satisfy this request.
        seam.indexed_event = None
        # Capture the adapter's final conflict.
        with self.assertRaises(ConflictError) as captured:
            # Attempt the action through the storage-atomic seam.
            seam.adapter().apply_action_once(**self._arguments())
        # Preserve the exact provider exception when recovery finds nothing compatible.
        self.assertIs(captured.exception, original)
        # Perform one exact indexed recovery lookup after the provider conflict.
        self.assertEqual(seam.find_calls, [("player-a", "example-game", "action-1")])
        # Never scan history during indexed miss handling.
        self.assertEqual(seam.read_calls, [])

    # Prove an explicit legacy focused seam stays bounded without affecting production.
    def test_explicit_legacy_reader_uses_small_bounded_fallback(self):
        # Build one seam but intentionally omit its indexed callback.
        seam = _LedgerSeam()
        # Return the exact compatible event from the legacy injected reader.
        seam.rows = [_event()]
        # Construct the adapter with only the historical read seam.
        adapter = SettlementAdapter(debit_once=seam.debit_once, credit_once=seam.credit_once, read_recent=seam.read_recent)
        # Resolve the compatible proof through the fallback path.
        self.assertIs(adapter.find_action(**self._arguments()), seam.rows[0])
        # Keep the listener-free compatibility read small and deterministic.
        self.assertEqual(seam.read_calls, [("player-a", LEGACY_PROOF_FALLBACK_LIMIT)])


# Prove the gateway exposes one canonical mutation shape with historical read compatibility. (LEDGER-032, GAMECORE-008, TEST-241)
class GameSettlementGatewayTests(unittest.TestCase):
    # Build one compatibility gateway over listener-free storage-atomic seams.
    def _gateway(self):
        # Retain the seam separately for exact provider-call assertions.
        seam = _LedgerSeam()
        # Bind one historical detail key beside canonical evidence.
        gateway = GameSettlementGateway("example-game", "legacy_action_id", debit_once=seam.debit_once, credit_once=seam.credit_once, find_action=seam.find_action, read_recent=seam.read_recent)
        # Return both objects so tests can inspect calls without private adapter access.
        return gateway, seam

    # Prove the canonical call writes universal identity plus its configured historical audit field.
    def test_canonical_call_writes_canonical_and_configured_audit_evidence(self):
        # Build isolated seams for one canonical game call.
        gateway, seam = self._gateway()
        # Apply one complete canonical signed action.
        gateway.apply_once(player_id="player-a", signed_amount=-5, transaction_type="wager", round_id="round-1", action_key="action-1", request_fingerprint="fingerprint-1", details={"bet": "red"})
        # Read the exact provider details emitted by the canonical adapter.
        details = seam.debit_calls[0]["details"]
        # Preserve the configured historical audit field without accepting it as a method argument alias.
        self.assertEqual(details["legacy_action_id"], "action-1")
        # Publish the same action identity under the universal key.
        self.assertEqual(details["game_action_key"], "action-1")
        # Preserve the explicit caller-owned semantic fingerprint unchanged.
        self.assertEqual(details["request_fingerprint"], "fingerprint-1")
        # Preserve unrelated game-owned audit detail.
        self.assertEqual(details["bet"], "red")

    # Prove every retired mutation keyword fails at the Python call boundary.
    def test_retired_mutation_alias_keywords_are_rejected(self):
        # Build one gateway without opening a provider seam for invalid calls.
        gateway, seam = self._gateway()
        # Enumerate each retired keyword beside otherwise complete canonical dimensions.
        aliases = {
            # Reject the historical signed movement alias.
            "amount": -5,
            # Reject the Plinko entity alias.
            "drop_id": "round-1",
            # Reject the Scratch Card entity alias.
            "card_id": "round-1",
            # Reject the bespoke action identity alias.
            "ledger_action_id": "action-1",
            # Reject the public action identity alias.
            "action_id": "action-1",
            # Reject the historical fingerprint alias.
            "fingerprint": "fingerprint-1",
        }
        # Exercise every alias independently so no partial compatibility surface can return.
        for name, value in aliases.items():
            # Keep the focused failure labeled only by the internal keyword name.
            with self.subTest(name=name):
                # Build a complete canonical call and append the forbidden alias.
                arguments = {"player_id": "player-a", "signed_amount": -5, "transaction_type": "wager", "round_id": "round-1", "action_key": "action-1", "request_fingerprint": "fingerprint-1", "details": {"bet": "red"}, name: value}
                # Require Python to reject the unsupported keyword before ledger access.
                with self.assertRaises(TypeError):
                    # Attempt the forbidden compatibility call.
                    gateway.apply_once(**arguments)
        # Prove every rejected alias left both money seams untouched.
        self.assertEqual((seam.debit_calls, seam.credit_calls), ([], []))

    # Pin the exact public Python signature after retiring every mutation alias.
    def test_apply_once_signature_is_canonical_and_keyword_only(self):
        # Read the bound function signature without constructing provider seams.
        parameters = inspect.signature(GameSettlementGateway.apply_once).parameters
        # Require one receiver followed by the single documented mutation vocabulary.
        self.assertEqual(tuple(parameters), ("self", "player_id", "signed_amount", "transaction_type", "round_id", "action_key", "request_fingerprint", "details"))
        # Require every caller-controlled movement dimension to remain keyword-only.
        self.assertTrue(all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for name, parameter in parameters.items() if name != "self"))

    # Require callers to own one explicit string fingerprint instead of gateway synthesis.
    def test_apply_once_does_not_derive_missing_or_structured_fingerprints(self):
        # Build one gateway whose provider seams expose any accidental movement.
        gateway, seam = self._gateway()
        # Exercise every formerly derived empty or structured fingerprint shape.
        for request_fingerprint in (None, "", {"wager": "5.00"}):
            # Label failures by type without reflecting potentially sensitive content.
            with self.subTest(value_type=type(request_fingerprint).__name__):
                # Require canonical validation to reject the supplied non-identity.
                with self.assertRaises(ValidationError):
                    # Attempt one otherwise complete movement.
                    gateway.apply_once(player_id="player-a", signed_amount=-5, transaction_type="wager", round_id="round-1", action_key="action-1", request_fingerprint=request_fingerprint, details={"bet": "red"})
        # Prove no rejected fingerprint reached a debit or credit provider seam.
        self.assertEqual((seam.debit_calls, seam.credit_calls), ([], []))

    # Reject retired keyword conventions in every checked-in production gateway call.
    def test_production_apply_once_calls_use_no_retired_aliases(self):
        # Resolve the repository root from this focused test module.
        repository_root = Path(__file__).resolve().parents[1]
        # Include the shared helper plus every registered or future game source file.
        sources = [repository_root / "casino" / "core" / "simple_game.py", *(repository_root / "casino" / "games").rglob("*.py")]
        # Enumerate the exact retired mutation keywords that may never return.
        retired = {"amount", "drop_id", "card_id", "ledger_action_id", "action_id", "fingerprint"}
        # Retain file, line, and keyword diagnostics for one actionable assertion.
        violations = []
        # Parse each production source file instead of relying on formatting-sensitive grep.
        for source_path in sources:
            # Build one syntax tree from the checked-in UTF-8 source.
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
            # Inspect every call expression in the source tree.
            for node in ast.walk(tree):
                # Ignore calls whose target is not an attribute named apply_once.
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "apply_once":
                    # Continue to the next syntax node without inferring dynamic behavior.
                    continue
                # Record only explicit retired keywords; canonical double-star movement dictionaries stay runtime-tested.
                for keyword in node.keywords:
                    # Reject a retired explicit spelling while ignoring double-star entries whose name is dynamic.
                    if keyword.arg in retired:
                        # Publish a stable repository-relative diagnostic for correction.
                        violations.append(f"{source_path.relative_to(repository_root).as_posix()}:{node.lineno}:{keyword.arg}")
        # Require one canonical explicit calling convention across all production game code.
        self.assertEqual(violations, [])

    # Prove historical rows remain readable through the configured audit field.
    def test_historical_detail_alias_remains_read_compatible(self):
        # Build isolated seams with the configured predecessor detail key.
        gateway, seam = self._gateway()
        # Build a predecessor row whose canonical action key predates the shared field.
        historical = _event(extra_details={"legacy_action_id": "historical-action"})
        # Remove only the canonical action identity to model the immutable predecessor row.
        historical["details"].pop("game_action_key")
        # Return the predecessor row from the bounded historical reader.
        seam.rows = [historical]
        # Rebuild a gateway without the indexed seam so historical detail lookup is exercised.
        gateway = GameSettlementGateway("example-game", "legacy_action_id", debit_once=seam.debit_once, credit_once=seam.credit_once, read_recent=seam.read_recent)
        # Resolve the exact immutable predecessor event through its retired detail key.
        self.assertIs(gateway.find("player-a", "historical-action"), historical)

    # Prove the shared gateway routes prepared intent controllers through the same adapter.
    def test_prepared_intent_routes_through_storage_atomic_adapter(self):
        # Build isolated seams for one staged controller action.
        gateway, seam = self._gateway()
        # Submit the historical intent shape retained by four staged games.
        gateway.transact({"player_id": "player-a", "amount": 7, "transaction_type": "payout", "game": "example-game", "round_id": "round-1", "action_id": "settle-1", "direction": "credit", "details": {"stage": "settlement"}})
        # Require the prepared action to use only the atomic credit-once seam.
        self.assertEqual((len(seam.debit_calls), len(seam.credit_calls)), (0, 1))
        # Require canonical action evidence on the prepared controller path too.
        self.assertEqual(seam.credit_calls[0]["details"]["game_action_key"], "settle-1")


# Prove future catalog games cannot reintroduce a direct ledger money path. (TEST-157)
class CatalogSettlementBoundaryTests(unittest.TestCase):
    # Run the exact production validator against every registered game package.
    def test_all_registered_games_use_the_shared_settlement_boundary(self):
        # Collect focused diagnostics rather than trusting a hardcoded 46-game assertion.
        errors = []
        # Execute the same source-derived check used by the required validation command.
        validate_module_boundaries.check_game_settlement_boundary(errors)
        # Require no direct ledger import or mutation call anywhere under the catalog modules.
        self.assertEqual(errors, [])


# Run this focused checkpoint directly without central registration.
if __name__ == "__main__":
    # Exit non-zero when any listener-free regression fails.
    unittest.main()
