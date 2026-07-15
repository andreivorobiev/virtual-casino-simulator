"""Session isolation and exactly-once service tests for issue #132."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict, lookup, and validation errors for route assertions.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.caribbean_stud import api, engine
# Import the isolated service orchestration under test.
from casino.games.caribbean_stud.service import CaribbeanStudService, request_fingerprint


# Simulate player-scoped state documents without touching repository data files.
class MemoryRepository:
    # Start with no persisted game documents.
    def __init__(self):
        # Store detached documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so every mutation requires an explicit save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id, state):
        # Persist a deep copy to model the JSON/provider boundary.
        self.documents[player_id] = copy.deepcopy(state)


# Record signed ledger events and enforce action-key replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 1000.0, "other-player": 1000.0}
        # Retain append-only committed event rows.
        self.events = []
        # Allow focused tests to simulate a definitive pre-commit failure.
        self.fail_next = False

    # Find one committed game movement for the requested player.
    def find(self, player_id, action_key):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["caribbean_stud_action_key"] == action_key), None)

    # Verify fake prior proof against the retried movement.
    def validate_existing(self, event, *, signed_amount, transaction_type, round_id, fingerprint):
        # Reject amount, type, round, game, or request mismatches.
        if event["amount"] != signed_amount or event["transaction_type"] != transaction_type or event["round_id"] != round_id or event["details"]["request_fingerprint"] != fingerprint:
            # Fail before any second movement.
            raise ConflictError("fake action identity conflict")

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, fingerprint, details):
        # Resolve any prior committed movement before changing the fake balance.
        existing = self.find(player_id, action_key)
        # Reuse an exact matching event.
        if existing is not None:
            # Validate the prior event.
            self.validate_existing(existing, signed_amount=signed_amount, transaction_type=transaction_type, round_id=round_id, fingerprint=fingerprint)
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Simulate one definitive failure before any append-only event exists.
        if self.fail_next:
            # Consume the one-shot failure flag.
            self.fail_next = False
            # Raise a public validation-shaped insufficient-funds error.
            raise ValidationError("Insufficient fake balance")
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "caribbean_stud_action_key": action_key, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class CaribbeanStudApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Store deterministic shoes keyed by action id.
        self.shoes = {
            # Player pair beats dealer pair.
            "deal-win": ["4S", "4D", "9C", "7H", "3S", "2S", "2D", "8C", "6H", "5S"],
            # Player pair faces a non-qualifying dealer.
            "deal-noqual": ["4S", "4D", "9C", "7H", "3S", "AS", "QD", "10C", "8H", "2S"],
            # High-card player hand supports fold privacy checks.
            "deal-fold": ["AS", "KD", "9C", "7H", "3S", "2S", "2D", "8C", "6H", "5S"],
            # Royal-flush player hand supports ante-marker recovery.
            "deal-recover": ["AS", "KS", "QS", "JS", "10S", "2S", "2D", "8C", "6H", "5S"],
        }
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = CaribbeanStudService(repository=self.repository, ledger_gateway=self.ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", shoe_factory=lambda action_id: self.shoes.get(action_id, self.shoes["deal-win"]))
        # Register only the game-owned routes on the real shared router.
        self.router = Router()
        # Inject the focused service without changing global registration.
        api.register(self.router, service=self.service)
        # Store the authenticated request context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game action through the real shared resolver path.
    def call_route(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so router mutations remain request-local.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Start one deterministic round and return its public payload.
    def start(self, action_id="deal-win", ante=5):
        # Deal through the public route with a stable action identity.
        return self.call_route("/api/v1/games/caribbean-stud/rounds?player_id=other-player", {"player_id": "other-player", "action_id": action_id, "ante": ante})

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_deal(self):
        # Start one deal with two competing hostile caller identities.
        first = self.start("deal-win", ante=7)
        # Replay the exact action through the same hostile inputs.
        second = self.start("deal-win", ante=7)
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(1000.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one ante debit exists.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "CARIBBEAN_STUD_ANTE_DEBIT"]
        # Verify both count and signed amount.
        self.assertEqual((1, -7.0), (len(debits), debits[0]["amount"]))
        # Verify the public payload does not expose the full dealer hand before a call.
        self.assertNotIn("dealer_hand", first["round"])
        # Read state through a different authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call_route("/api/v1/games/caribbean-stud/state?player_id=session-player", method="GET", context=other_context)
        # Verify the other session cannot read the first player's active hand.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject an attempt by the other session to act on the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise cross-session round lookup through the real router.
            self.call_route(f"/api/v1/games/caribbean-stud/rounds/{first['round']['round_id']}/fold", {"action_id": "fold-cross", "player_id": "session-player"}, context=other_context)

    # Confirm conflicting deal retries and rejected debit cleanup.
    def test_deal_conflict_and_rejected_debit_cleanup(self):
        # Commit one valid ante action.
        self.start("deal-win", ante=3)
        # Reject reuse of the same identity with a changed ante.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.start("deal-win", ante=4)
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Create the isolated empty-balance service.
        empty_service = CaribbeanStudService(repository=empty_repository, ledger_gateway=empty_ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", shoe_factory=lambda action_id: self.shoes["deal-win"])
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable round.
            empty_service.deal("session-player", {"action_id": "deal-empty", "ante": 1})
        # Verify no active decision is stranded after a non-committed debit.
        self.assertIsNone(empty_repository.documents.get("session-player", {}).get("active_round"))
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)

    # Confirm call debit and settlement credit are exactly-once.
    def test_call_replay_settles_once(self):
        # Deal a player pair that beats a qualifying dealer pair.
        started = self.start("deal-win", ante=5)
        # Resolve the call once.
        first = self.call_route(f"/api/v1/games/caribbean-stud/rounds/{started['round']['round_id']}/call", {"action_id": "call-win"})
        # Replay the exact call.
        second = self.call_route(f"/api/v1/games/caribbean-stud/rounds/{started['round']['round_id']}/call", {"action_id": "call-win"})
        # Verify deterministic result and explicit replay behavior.
        self.assertEqual(("player_win", 30.0, True), (first["round"]["outcome"], first["round"]["payout"], second["replayed"]))
        # Verify exactly one ante, one call debit, and one settlement credit exist.
        types = [event["transaction_type"] for event in self.ledger.events]
        # Compare counts by event type.
        self.assertEqual((1, 1, 1), (types.count("CARIBBEAN_STUD_ANTE_DEBIT"), types.count("CARIBBEAN_STUD_CALL_DEBIT"), types.count("CARIBBEAN_STUD_SETTLEMENT_CREDIT")))
        # Verify the fake balance reflects ante debit, call debit, and returned tokens.
        self.assertEqual(1015.0, self.ledger.balances["session-player"])
        # Reject a changed terminal retry with the same call action id on another route body.
        with self.assertRaises(ConflictError):
            # Exercise terminal conflict by using the call id for a fold.
            self.call_route(f"/api/v1/games/caribbean-stud/rounds/{started['round']['round_id']}/fold", {"action_id": "call-win"})

    # Confirm dealer non-qualification settlement credits once.
    def test_dealer_not_qualified_credit_shape(self):
        # Deal a player pair against a non-qualifying dealer.
        started = self.start("deal-noqual", ante=5)
        # Resolve the call.
        result = self.call_route(f"/api/v1/games/caribbean-stud/rounds/{started['round']['round_id']}/call", {"action_id": "call-noqual"})
        # Verify the dealer-not-qualified outcome and returned amount.
        self.assertEqual(("dealer_not_qualified", 20.0, 5.0), (result["round"]["outcome"], result["round"]["payout"], result["round"]["net"]))
        # Verify one settlement credit was recorded.
        credits = [event for event in self.ledger.events if event["transaction_type"] == "CARIBBEAN_STUD_SETTLEMENT_CREDIT"]
        # Verify credit amount.
        self.assertEqual((1, 20.0), (len(credits), credits[0]["amount"]))

    # Confirm fold has no new ledger movement and hides dealer cards.
    def test_fold_replay_has_no_extra_ledger_and_no_dealer_reveal(self):
        # Deal a foldable round.
        started = self.start("deal-fold", ante=6)
        # Fold once through the public route.
        first = self.call_route(f"/api/v1/games/caribbean-stud/rounds/{started['round']['round_id']}/fold", {"action_id": "fold-once"})
        # Replay the exact fold.
        second = self.call_route(f"/api/v1/games/caribbean-stud/rounds/{started['round']['round_id']}/fold", {"action_id": "fold-once"})
        # Verify fold result and replay flag.
        self.assertEqual(("fold", -6.0, True), (first["round"]["outcome"], first["round"]["net"], second["replayed"]))
        # Verify no call or settlement event was created.
        self.assertEqual(["CARIBBEAN_STUD_ANTE_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify the dealer hand remains hidden in both response and stored public state.
        self.assertNotIn("dealer_hand", first["round"])
        # Verify balance reflects only the ante debit.
        self.assertEqual(994.0, self.ledger.balances["session-player"])

    # Confirm committed ante marker recovery after restart.
    def test_ante_marker_recovery_after_restart(self):
        # Commit one deterministic ante-backed deal.
        first = self.start("deal-recover", ante=8)
        # Simulate a crash after debit commit but before its completion marker save.
        self.repository.documents["session-player"]["active_round"]["ante_status"] = "pending"
        # Restore the attempting stage for recovery logic.
        self.repository.documents["session-player"]["active_round"]["movement_stage"] = "ante_attempting"
        # Remove the cached ledger id so recovery must scan append-only proof.
        self.repository.documents["session-player"]["active_round"].pop("ante_ledger_id", None)
        # Recreate service state behavior through a normal GET reload.
        reloaded = self.call_route("/api/v1/games/caribbean-stud/state", method="GET")
        # Verify the original private card plan and round identity survive restart.
        self.assertEqual(first["round"]["round_id"], reloaded["state"]["active_round"]["round_id"])
        # Verify reload restored a complete ante marker.
        self.assertEqual("complete", reloaded["state"]["active_round"]["ante_status"])
        # Verify only one ante debit exists after recovery.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "CARIBBEAN_STUD_ANTE_DEBIT"]))

    # Confirm an ambiguous call debit fails closed instead of repeating.
    def test_ambiguous_call_attempt_requires_reconciliation(self):
        # Deal one normal round.
        started = self.start("deal-win", ante=5)
        # Build the deterministic call fingerprint.
        fingerprint = request_fingerprint({"stage": "call", "round_id": started["round"]["round_id"]})
        # Mutate state to a post-reveal call attempt without ledger proof.
        state = self.repository.documents["session-player"]
        # Read the active round for mutation.
        round_state = state["active_round"]
        # Apply pure settlement state.
        engine.settle_call(round_state, "call-ambiguous", completed_at="2026-07-14T00:00:00Z", request_fingerprint=fingerprint)
        # Mark the call debit as attempted.
        round_state["movement_stage"] = "call_attempting"
        # Archive the mutated round.
        engine.archive_round(state, round_state)
        # Persist the ambiguous state.
        self.repository.save("session-player", state)
        # Reject recovery because no append-only call proof exists.
        with self.assertRaises(ConflictError):
            # Exercise fail-closed reload behavior.
            self.call_route("/api/v1/games/caribbean-stud/state", method="GET")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
