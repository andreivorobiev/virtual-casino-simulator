# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for GitHub issue #139."""

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

# Import deterministic ownership for every fresh-process race worker.
from tests.process_race import ProcessRacePool

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict, lookup, and validation errors for route assertions.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.casino_holdem import api, engine, service
# Import the isolated service orchestration under test.
from casino.games.casino_holdem.service import CasinoHoldemService


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

    # Apply one callback to provider-current state and publish its detached result.
    def update(self, player_id, mutator):
        # Give the callback a detached document so failed transitions cannot leak.
        current = copy.deepcopy(self.documents.get(player_id, engine.default_state()))
        # Apply the complete transition inside this fake provider boundary.
        updated = mutator(current)
        # Store a detached result so later loads remain isolated.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return an independent authoritative value to the service.
        return copy.deepcopy(updated)


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None, *, lost_response_types=(), before_failure=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 200.0, "other-player": 200.0}
        # Retain append-only committed event rows.
        self.events = []
        # Allow one focused test to simulate a pre-commit ledger failure.
        self.fail_next = False
        # Select movement types whose first committed response is lost.
        self.lost_response_types = set(lost_response_types)
        # Retain one optional sibling publication before a rejected movement.
        self.before_failure = before_failure
        # Count every mutation callback attempt by transaction vocabulary.
        self.apply_calls = {}

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["casino_holdem_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Count the attempted movement before failure or replay handling.
        self.apply_calls[transaction_type] = self.apply_calls.get(transaction_type, 0) + 1
        # Resolve any prior committed action before changing the fake balance.
        existing = self.find(player_id, action_key)
        # Reuse an exact matching event.
        if existing is not None:
            # Reject semantic conflicts like the production gateway.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != request_fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Simulate one failure before any append-only event exists.
        if self.fail_next:
            # Consume the one-shot failure flag.
            self.fail_next = False
            # Publish an unrelated sibling at the exact rollback boundary when supplied.
            if self.before_failure is not None:
                # Invoke the bounded sibling seam once.
                self.before_failure()
            # Raise a public validation-shaped insufficient-funds error.
            raise ValidationError("Insufficient play-token balance")
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient play-token balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "casino_holdem_action_id": action_key, "request_fingerprint": request_fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Lose the response only after the immutable movement is committed.
        if transaction_type in self.lost_response_types:
            # Consume the one-shot transport failure stage.
            self.lost_response_types.remove(transaction_type)
            # Surface an ambiguous response so normal recovery must find proof.
            raise RuntimeError(f"lost {transaction_type} response")
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class CasinoHoldemApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Provide deterministic card fixtures by deal action id.
        self.fixtures = {
            # Create a qualified-dealer player straight for call payout tests.
            "deal-win": {"player_cards": ["8H", "9D"], "dealer_cards": ["4S", "4C"], "community_cards": ["10C", "JH", "QS", "2D", "7C"]},
            # Create a generic flop that is safe for fold privacy tests.
            "deal-fold": {"player_cards": ["AH", "2D"], "dealer_cards": ["KC", "QS"], "community_cards": ["3H", "4D", "5S", "6C", "7H"]},
            # Create a player flush against a non-qualifying dealer for recovery tests.
            "deal-recover": {"player_cards": ["AH", "9H"], "dealer_cards": ["2C", "7D"], "community_cards": ["KH", "4H", "8H", "QS", "3D"]},
            # Create a strong qualified dealer result for rejected-call rollback tests.
            "deal-loss": {"player_cards": ["2H", "7D"], "dealer_cards": ["AS", "AC"], "community_cards": ["3C", "9H", "JD", "5S", "8C"]},
        }
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = CasinoHoldemService(repository=self.repository, ledger_gateway=self.ledger, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}", fixture_factory=lambda action_id: self.fixtures.get(action_id))
        # Register only the game-owned routes on the real shared router.
        self.router = Router()
        # Inject the focused service without changing global registration.
        api.register(self.router, service=self.service)
        # Store the authenticated request context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game action through the real shared resolver path.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so router mutations remain request-local.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Start one deterministic round through the public route.
    def start(self, action_id="deal-win", wager=5):
        # Deal through the API so ante settlement is exercised.
        return self.call("/api/v1/games/casino-holdem/rounds", {"action_id": action_id, "wager": wager})

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_ante_deal(self):
        # Start one deal with two competing hostile caller identities.
        first = self.call("/api/v1/games/casino-holdem/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-win", "wager": 7})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/casino-holdem/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-win", "wager": 7})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(200.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one ante debit exists.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_ANTE_DEBIT"]
        # Verify both count and signed amount.
        self.assertEqual((1, -7.0), (len(debits), debits[0]["amount"]))
        # Verify dealer, turn, and river cards are absent from the public payload.
        self.assertNotIn("dealer_cards", first["round"])
        # Verify the private dealer cards remain reload-safe in persisted state.
        self.assertIn("_dealer_cards", self.repository.documents["session-player"]["active_round"])
        # Read state through a different authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/casino-holdem/state?player_id=session-player", method="GET", context=other_context)
        # Verify the other session cannot read the first player's active flop.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject an attempt by the other session to decide the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise cross-session round lookup through the real router.
            self.call(f"/api/v1/games/casino-holdem/rounds/{first['round']['round_id']}/decision", {"action_id": "decision-cross-session", "decision": "call", "player_id": "session-player"}, context=other_context)

    # Confirm conflicting deal retries and insufficient funds fail without extra state.
    def test_deal_conflict_and_rejected_ante_cleanup(self):
        # Commit one valid ante action.
        self.start("deal-win", wager=3)
        # Reject reuse of the same identity with a changed wager.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/casino-holdem/rounds", {"action_id": "deal-win", "wager": 4})
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Reject the prepared debit before any immutable movement commits.
        empty_ledger.fail_next = True
        # Publish one unrelated sibling after preparation but before rejection.
        empty_ledger.before_failure = lambda: empty_repository.documents["session-player"].update({"atomic_markers": ["concurrent"]})
        # Create the isolated empty-balance service.
        empty_service = CasinoHoldemService(repository=empty_repository, ledger_gateway=empty_ledger, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", fixture_factory=lambda action_id: self.fixtures["deal-win"])
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable round.
            empty_service.start_round("session-player", {"action_id": "deal-no-funds", "wager": 1})
        # Verify no active decision is stranded after a non-committed ante.
        self.assertIsNone(empty_repository.documents["session-player"]["active_round"])
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)
        # Verify provider-current unrelated state survives action-owned rollback.
        self.assertEqual(["concurrent"], empty_repository.documents["session-player"]["atomic_markers"])
        # Verify the private optimistic baseline never enters persisted state.
        self.assertNotIn(service._ATOMIC_BASELINE_KEY, empty_repository.documents["session-player"])

    # Confirm call debits and settlement credits are replay-safe.
    def test_call_replay_and_settlement_recovery(self):
        # Deal a deterministic player-win round.
        started = self.start("deal-win", wager=5)
        # Decide to call once through the public route.
        first = self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-call", "decision": "call"})
        # Simulate a crash after credit but before the completion marker save.
        self.repository.documents["session-player"]["recent_rounds"][-1]["settlement_status"] = "pending"
        # Remove cached ledger id so reload must recover it from append-only proof.
        self.repository.documents["session-player"]["recent_rounds"][-1].pop("settlement_ledger_id", None)
        # Recreate service state behavior through a normal GET reload.
        reloaded = self.call("/api/v1/games/casino-holdem/state", method="GET")
        # Replay the same decision after reload.
        second = self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-call", "decision": "call"})
        # Verify deterministic result and explicit replay behavior.
        self.assertEqual(("player_win", 30.0, True), (first["round"]["outcome"], first["round"]["payout"], second["replayed"]))
        # Verify reload restored a complete settlement marker.
        self.assertEqual("complete", reloaded["state"]["recent_rounds"][-1]["settlement_status"])
        # Verify exactly one ante, one call, and one settlement event exist.
        self.assertEqual((1, 1, 1), (len([event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_ANTE_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_CALL_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_SETTLEMENT_CREDIT"])))
        # Verify settlement audit dimensions include the player, game, round, and action-derived id.
        settlement = [event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_SETTLEMENT_CREDIT"][0]
        # Compare core ledger dimensions.
        self.assertEqual(("session-player", engine.GAME_ID, started["round"]["round_id"], "decision-call:settlement"), (settlement["player_id"], settlement["game"], settlement["round_id"], settlement["details"]["casino_holdem_action_id"]))

    # Confirm a committed ante with a lost response recovers without another debit.
    def test_lost_ante_response_recovers_once(self):
        # Lose only the first committed ante-debit response.
        self.ledger.lost_response_types.add("CASINO_HOLDEM_ANTE_DEBIT")
        # Surface the injected post-commit response loss.
        with self.assertRaisesRegex(RuntimeError, "lost CASINO_HOLDEM_ANTE_DEBIT response"):
            # Issue one stable opening action.
            self.start("deal-lost-ante", wager=5)
        # Reconcile immutable proof through the normal state endpoint.
        recovered = self.service.state("session-player")
        # Replay the exact deal after recovery.
        replayed = self.start("deal-lost-ante", wager=5)
        # Require one event and stable decision-ready identity across recovery and replay.
        ante_events = [event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_ANTE_DEBIT"]
        # Compare the sole movement and authoritative round projection.
        self.assertEqual((len(ante_events), replayed["round"]["round_id"], recovered["state"]["active_round"]["round_id"]), (1, recovered["state"]["active_round"]["round_id"], recovered["state"]["active_round"]["round_id"]))
        # Verify the private optimistic baseline never enters persisted state.
        self.assertNotIn(service._ATOMIC_BASELINE_KEY, self.repository.documents["session-player"])

    # Confirm a committed call with a lost response settles without another debit.
    def test_lost_call_response_recovers_once(self):
        # Prepare one deterministic decision-ready round.
        started = self.start("deal-lost-call", wager=5)
        # Lose only the first committed call-debit response.
        self.ledger.lost_response_types.add("CASINO_HOLDEM_CALL_DEBIT")
        # Surface the injected post-commit response loss.
        with self.assertRaisesRegex(RuntimeError, "lost CASINO_HOLDEM_CALL_DEBIT response"):
            # Issue one stable Call action.
            self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-lost-call", "decision": "call"})
        # Recover call proof and terminal settlement through a normal read.
        recovered = self.service.state("session-player")
        # Replay the same terminal decision without a second movement.
        replayed = self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-lost-call", "decision": "call"})
        # Require one call movement and one authoritative terminal result.
        call_events = [event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_CALL_DEBIT"]
        # Compare event count and stable recovered round.
        self.assertEqual((len(call_events), replayed["round"], recovered["state"]["recent_rounds"][-1]), (1, recovered["state"]["recent_rounds"][-1], recovered["state"]["recent_rounds"][-1]))

    # Confirm a committed settlement with a lost response recovers without another credit.
    def test_lost_settlement_response_recovers_once(self):
        # Prepare the deterministic player-win round.
        started = self.start("deal-win", wager=5)
        # Lose only the first committed returned-token response.
        self.ledger.lost_response_types.add("CASINO_HOLDEM_SETTLEMENT_CREDIT")
        # Surface the injected post-commit response loss.
        with self.assertRaisesRegex(RuntimeError, "lost CASINO_HOLDEM_SETTLEMENT_CREDIT response"):
            # Issue one stable winning Call action.
            self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-lost-settlement", "decision": "call"})
        # Recover settlement proof through the normal state endpoint.
        recovered = self.service.state("session-player")
        # Replay the same terminal decision without another credit.
        replayed = self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-lost-settlement", "decision": "call"})
        # Require one returned-token movement and one authoritative terminal result.
        settlement_events = [event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_SETTLEMENT_CREDIT"]
        # Compare event count and stable recovered round.
        self.assertEqual((len(settlement_events), replayed["round"], recovered["state"]["recent_rounds"][-1]), (1, recovered["state"]["recent_rounds"][-1], recovered["state"]["recent_rounds"][-1]))

    # Confirm a fold settles exactly once without call or payout ledger rows.
    def test_fold_replay_creates_no_call_or_settlement_event(self):
        # Deal a deterministic fold round.
        started = self.start("deal-fold", wager=6)
        # Fold once through the public route.
        first = self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-fold", "decision": "fold"})
        # Replay the exact fold action.
        second = self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-fold", "decision": "fold"})
        # Verify terminal fold result and replay behavior.
        self.assertEqual(("folded", 0.0, True), (first["round"]["outcome"], first["round"]["payout"], second["replayed"]))
        # Verify no call or settlement ledger row was created.
        self.assertEqual((0, 0), (len([event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_CALL_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_SETTLEMENT_CREDIT"])))
        # Verify the player balance reflects only the ante debit.
        self.assertEqual(194.0, self.ledger.balances["session-player"])

    # Confirm a call debit failure restores the active decision state.
    def test_rejected_call_rolls_back_to_decision(self):
        # Deal one affordable ante.
        started = self.start("deal-loss", wager=40)
        # Lower the remaining balance below the required call amount.
        self.ledger.balances["session-player"] = 10.0
        # Reject the next prepared call before any immutable movement commits.
        self.ledger.fail_next = True
        # Publish one unrelated sibling after call preparation but before rejection.
        self.ledger.before_failure = lambda: self.repository.documents["session-player"].update({"atomic_markers": ["concurrent"]})
        # Reject the two-times ante call debit.
        with self.assertRaises(ValidationError):
            # Attempt an unaffordable call.
            self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-call-low-balance", "decision": "call"})
        # Verify the active round is still callable or foldable.
        active = self.repository.documents["session-player"]["active_round"]
        # Verify the call preparation was removed.
        self.assertEqual(("decision", None, "not_ready"), (active["phase"], active["decision"], active["call_status"]))
        # Verify no call debit event was committed.
        self.assertEqual([], [event for event in self.ledger.events if event["transaction_type"] == "CASINO_HOLDEM_CALL_DEBIT"])
        # Verify the unrelated provider-current sibling survived rollback.
        self.assertEqual(["concurrent"], self.repository.documents["session-player"]["atomic_markers"])

    # Prove stale fresh processes preserve siblings and one provider-winning decision.
    def test_fresh_process_fold_race_preserves_provider_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "session-player.json"
            # Create the state directory before seeding one active decision.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Build one production-shaped baseline document.
            baseline = engine.default_state()
            # Bind the exact deal fingerprint retained by normal replay checks.
            deal_fingerprint = service.request_fingerprint({"stage": "deal", "wager": 5.0})
            # Use one contract-shaped deterministic round identifier.
            round_id = "choldem_0123456789abcdef01234567"
            # Prepare one deterministic decision-ready round.
            active_round = engine.create_round("session-player", 5, "deal-process", round_id=round_id, created_at="2026-08-15T00:00:00Z", request_fingerprint=deal_fingerprint, fixture=self.fixtures["deal-fold"])
            # Bind immutable ante evidence so both workers race only movement-free Fold.
            active_round["ante_status"] = "complete"
            # Retain an exact ledger identity for reload-safe decision eligibility.
            active_round["ante_ledger_id"] = "ledger-opening"
            # Publish the active decision and durable deal receipt.
            baseline["active_round"] = active_round
            # Bind the opening action to its exact round and request fingerprint.
            baseline["action_receipts"]["deal-process"] = {"stage": "deal", "round_id": round_id, "request_fingerprint": deal_fingerprint}
            # Seed an unrelated sibling field that the game transition must not own.
            baseline["atomic_markers"] = ["seed"]
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
from casino.games.casino_holdem.service import CasinoHoldemService, StateRepository
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
            raise RuntimeError("Casino Hold'em race release timed out")
        return state
    def update(self, player_id, mutator):
        return base.update(player_id, mutator)
class NoLedger:
    def find(self, _player_id, _action_id):
        return None
    def apply_once(self, **_kwargs):
        raise RuntimeError("unexpected Casino Hold'em movement")
game = CasinoHoldemService(repository=RendezvousRepository(), ledger_gateway=NoLedger(), get_player=lambda player_id: {'player_id': player_id, 'balance': 195.0}, clock=lambda: '2026-08-15T00:01:00Z')
try:
    result = game.decide('session-player', 'choldem_0123456789abcdef01234567', {'action_id': action_id, 'decision': 'fold'})
    print('PASS:' + result['round']['decision_action_id'])
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
                process = process_pool.spawn([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"fold-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
            process_pool.wait_until_ready([(process, ready) for process, ready, _release in workers], timeout=0)
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.casino_holdem import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('casino_holdem', 'session-player', add, engine.default_state)\n"
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
            # Resolve the sole terminal round.
            terminal = persisted["recent_rounds"][-1]
            # Require the winning decision, sibling preservation, and no active-round resurrection.
            self.assertEqual((persisted["active_round"], terminal["phase"], terminal["decision_action_id"], persisted["atomic_markers"]), (None, "settled", "fold-process-0", ["seed", "concurrent"]))

    # Confirm conflicting terminal retries fail closed.
    def test_conflicting_decision_retry_fails_closed(self):
        # Deal one deterministic round.
        started = self.start("deal-fold", wager=5)
        # Fold once.
        self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-conflict", "decision": "fold"})
        # Reject reuse of the same decision identity with a changed decision.
        with self.assertRaises(ConflictError):
            # Exercise conflicting terminal semantics.
            self.call(f"/api/v1/games/casino-holdem/rounds/{started['round']['round_id']}/decision", {"action_id": "decision-conflict", "decision": "call"})


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
