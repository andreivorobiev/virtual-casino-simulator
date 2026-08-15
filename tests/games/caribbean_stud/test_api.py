# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for issue #132."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import JSON support for exact disposable provider bytes.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for independent stale-load workers.
import subprocess
# Import the active interpreter selected by the repository test runner.
import sys
# Import task-owned temporary directories for provider bytes and gates.
import tempfile
# Import bounded polling for worker rendezvous.
import time
# Import the standard dependency-free test runner.
import unittest
# Import portable paths for exact checkout and worker files.
from pathlib import Path

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

    # Apply one callback to the current document like the production atomic provider seam.
    def update(self, player_id, mutator):
        # Give the callback a detached current value so failed writes cannot leak mutation.
        current = copy.deepcopy(self.documents.get(player_id, engine.default_state()))
        # Apply the complete transition inside this fake provider boundary.
        updated = mutator(current)
        # Persist a detached result to model JSON serialization ownership.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return an independent authoritative value to the service.
        return copy.deepcopy(updated)


# Record signed ledger events and enforce action-key replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None, *, lost_response_types=(), before_failure=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 1000.0, "other-player": 1000.0}
        # Retain append-only committed event rows.
        self.events = []
        # Allow focused tests to simulate a definitive pre-commit failure.
        self.fail_next = False
        # Select movement types whose first committed response is lost.
        self.lost_response_types = set(lost_response_types)
        # Retain one optional callback that publishes a concurrent sibling before failure.
        self.before_failure = before_failure
        # Count every apply attempt by transaction vocabulary.
        self.apply_calls = {}

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
        # Count every call before replay or failure handling.
        self.apply_calls[transaction_type] = self.apply_calls.get(transaction_type, 0) + 1
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
            # Publish any deterministic concurrent sibling before the service rolls back.
            if self.before_failure is not None:
                # Invoke the bounded test seam exactly once.
                self.before_failure()
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
        # Simulate a provider or transport loss only after immutable proof commits.
        if transaction_type in self.lost_response_types:
            # Consume the one-shot lost-response stage.
            self.lost_response_types.remove(transaction_type)
            # Surface an unclassified transport failure so production recovery owns the next read.
            raise RuntimeError(f"lost {transaction_type} response")
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

    # Confirm a definitive pre-ledger failure reverses only action-owned game fields.
    def test_rejected_ante_rollback_preserves_concurrent_sibling(self):
        # Create isolated storage whose unrelated sibling changes during the failed debit.
        repository = MemoryRepository()

        # Publish one sibling value after preparation but before rollback.
        def publish_sibling():
            # Retain evidence outside Caribbean Stud's owned state fields.
            repository.documents["session-player"]["atomic_markers"] = ["concurrent"]

        # Fail the first movement before any immutable event exists.
        ledger = RecordingLedger(before_failure=publish_sibling)
        # Select the definitive pre-commit failure path.
        ledger.fail_next = True
        # Build the exact service with deterministic cards.
        service = CaribbeanStudService(repository=repository, ledger_gateway=ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", shoe_factory=lambda _action_id: self.shoes["deal-win"])
        # Require the original public validation error.
        with self.assertRaises(ValidationError):
            # Attempt one ante-backed deal.
            service.deal("session-player", {"action_id": "deal-rollback", "ante": 5})
        # Read the provider-owned document after compare-and-restore.
        persisted = repository.documents["session-player"]
        # Require actionable game state, sibling preservation, and zero committed event.
        self.assertEqual((persisted["active_round"], persisted["atomic_markers"], ledger.events), (None, ["concurrent"], []))

    # Confirm an ante debit whose response is lost recovers without a second movement.
    def test_lost_ante_response_recovers_once(self):
        # Create isolated persistence and one post-commit response loss.
        repository = MemoryRepository()
        # Lose only the first committed ante response.
        ledger = RecordingLedger(lost_response_types={"CARIBBEAN_STUD_ANTE_DEBIT"})
        # Build the production service around deterministic cards.
        service = CaribbeanStudService(repository=repository, ledger_gateway=ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", shoe_factory=lambda _action_id: self.shoes["deal-win"])
        # Surface the injected transport loss from the first request.
        with self.assertRaisesRegex(RuntimeError, "lost CARIBBEAN_STUD_ANTE_DEBIT response"):
            # Issue one stable deal action.
            service.deal("session-player", {"action_id": "deal-lost-ante", "ante": 5})
        # Reconcile immutable proof through the normal reload endpoint.
        recovered = service.state("session-player")
        # Replay the exact deal after recovery.
        replayed = service.deal("session-player", {"action_id": "deal-lost-ante", "ante": 5})
        # Require one movement attempt, one event, complete marker, and stable replay identity.
        self.assertEqual((ledger.apply_calls["CARIBBEAN_STUD_ANTE_DEBIT"], len(ledger.events), recovered["state"]["active_round"]["ante_status"], replayed["round"]["round_id"]), (1, 1, "complete", recovered["state"]["active_round"]["round_id"]))

    # Confirm a call debit whose response is lost recovers before settlement without duplication.
    def test_lost_call_debit_response_recovers_once(self):
        # Create isolated persistence and one lost call-debit response.
        repository = MemoryRepository()
        # Commit the call debit before surfacing its transport failure.
        ledger = RecordingLedger(lost_response_types={"CARIBBEAN_STUD_CALL_DEBIT"})
        # Build the deterministic winning service.
        service = CaribbeanStudService(repository=repository, ledger_gateway=ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", shoe_factory=lambda _action_id: self.shoes["deal-win"])
        # Prepare one ante-backed decision.
        started = service.deal("session-player", {"action_id": "deal-lost-call", "ante": 5})
        # Surface the lost committed call response.
        with self.assertRaisesRegex(RuntimeError, "lost CARIBBEAN_STUD_CALL_DEBIT response"):
            # Issue the stable call action once.
            service.call("session-player", started["round"]["round_id"], {"action_id": "call-lost-debit"})
        # Reconcile the debit marker through normal state recovery.
        service.state("session-player")
        # Replay the call so only the still-unissued settlement credit runs.
        replayed = service.call("session-player", started["round"]["round_id"], {"action_id": "call-lost-debit"})
        # Require exactly one ante, call, and settlement attempt with terminal state.
        self.assertEqual((ledger.apply_calls["CARIBBEAN_STUD_ANTE_DEBIT"], ledger.apply_calls["CARIBBEAN_STUD_CALL_DEBIT"], ledger.apply_calls["CARIBBEAN_STUD_SETTLEMENT_CREDIT"], replayed["round"]["settlement_status"]), (1, 1, 1, "complete"))

    # Confirm a settlement credit whose response is lost recovers without a second credit.
    def test_lost_settlement_response_recovers_once(self):
        # Create isolated persistence and one lost positive-credit response.
        repository = MemoryRepository()
        # Commit the settlement credit before surfacing its transport failure.
        ledger = RecordingLedger(lost_response_types={"CARIBBEAN_STUD_SETTLEMENT_CREDIT"})
        # Build the deterministic winning service.
        service = CaribbeanStudService(repository=repository, ledger_gateway=ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", shoe_factory=lambda _action_id: self.shoes["deal-win"])
        # Prepare the decision round.
        started = service.deal("session-player", {"action_id": "deal-lost-credit", "ante": 5})
        # Surface the lost committed credit response.
        with self.assertRaisesRegex(RuntimeError, "lost CARIBBEAN_STUD_SETTLEMENT_CREDIT response"):
            # Issue the stable call and its returned-token settlement.
            service.call("session-player", started["round"]["round_id"], {"action_id": "call-lost-credit"})
        # Recover both exact ledger markers through a normal read.
        recovered = service.state("session-player")
        # Replay the terminal call without any second wallet movement.
        replayed = service.call("session-player", started["round"]["round_id"], {"action_id": "call-lost-credit"})
        # Require one attempt for every stage and the same recovered terminal result.
        self.assertEqual((ledger.apply_calls["CARIBBEAN_STUD_ANTE_DEBIT"], ledger.apply_calls["CARIBBEAN_STUD_CALL_DEBIT"], ledger.apply_calls["CARIBBEAN_STUD_SETTLEMENT_CREDIT"], replayed["round"], recovered["state"]["recent_rounds"][-1]), (1, 1, 1, recovered["state"]["recent_rounds"][-1], recovered["state"]["recent_rounds"][-1]))

    # Prove stale fresh processes preserve siblings and one provider-winning decision.
    def test_fresh_process_fold_race_preserves_provider_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "session-player.json"
            # Create the state directory before seeding one active decision.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Build one deterministic decision round with committed ante proof.
            active_round = engine.create_round("session-player", 5, "deal-process", player_hand=self.shoes["deal-fold"][:5], dealer_hand=self.shoes["deal-fold"][5:], round_id=engine.round_id_for("session-player", "deal-process"), created_at="2026-08-14T00:00:00Z", request_fingerprint=request_fingerprint({"stage": "deal", "ante": 5.0}))
            # Mark the ante complete so both workers may race only the terminal decision.
            active_round.update({"ante_status": "complete", "ante_ledger_id": "ledger-ante", "movement_stage": "ante_committed"})
            # Seed an unrelated sibling field that the game transition must not own.
            baseline = {**engine.default_state(), "active_round": active_round, "atomic_markers": ["seed"]}
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps(baseline, sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind all child persistence to the disposable root.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one service worker whose repository load pauses after capturing stale state.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.errors import ConflictError
from casino.games.caribbean_stud.service import CaribbeanStudService, StateRepository
base = StateRepository()
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
action_id = sys.argv[3]
class RendezvousRepository:
    def load(self, player_id):
        state = base.load(player_id)
        ready.write_text('ready', encoding='utf-8')
        deadline = time.monotonic() + 10
        while not release.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not release.exists():
            raise RuntimeError('Caribbean Stud race release timed out')
        return state
    def update(self, player_id, mutator):
        return base.update(player_id, mutator)
class NoLedger:
    def find(self, _player_id, _action_key):
        return None
service = CaribbeanStudService(repository=RendezvousRepository(), ledger_gateway=NoLedger(), player_reader=lambda player_id: {'player_id': player_id, 'balance': 995.0}, clock=lambda: '2026-08-14T00:01:00Z')
try:
    result = service.fold('session-player', 'cs_' + __import__('hashlib').sha256(b'caribbean_stud:session-player:deal-process').hexdigest()[:24], {'action_id': action_id})
    print('PASS:' + result['round']['fold_action_id'])
except ConflictError:
    print('CONFLICT')
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start one winner candidate and one stale loser candidate.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"fold-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain process and gate ownership.
                workers.append((process, ready_path, release_path))
            # Bound the stale-load rendezvous.
            deadline = time.monotonic() + 10
            # Wait until both workers have captured the same initial document.
            while not all(ready.exists() for _process, ready, _release in workers) and time.monotonic() < deadline:
                # Stop early if either worker failed before readiness.
                if any(process.poll() is not None for process, _ready, _release in workers):
                    # Leave polling for the diagnostic assertion below.
                    break
                # Yield briefly without starting another action.
                time.sleep(0.01)
            # Require both stale snapshots before publishing a concurrent sibling.
            self.assertTrue(all(ready.exists() for _process, ready, _release in workers))
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.caribbean_stud import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('caribbean_stud', 'session-player', add, engine.default_state)\n"
            # Commit the sibling after both workers captured their stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish the winning fold.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=15)
            # Require the first fold to commit.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:fold-process-0"), winner_error)
            # Release the stale second worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require the second action to conflict instead of overwriting the winner.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Resolve the sole terminal history row.
            terminal = persisted["recent_rounds"][-1]
            # Require the winning decision, sibling preservation, and no active-round resurrection.
            self.assertEqual((persisted["active_round"], len(persisted["recent_rounds"]), terminal["fold_action_id"], persisted["atomic_markers"]), (None, 1, "fold-process-0", ["seed", "concurrent"]))

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
