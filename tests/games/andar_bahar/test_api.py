# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for GitHub issue #140."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import JSON serialization for real provider subprocess evidence.
import json
# Import environment selection for disposable child persistence.
import os
# Import filesystem paths for process rendezvous gates and state inspection.
from pathlib import Path
# Import child processes for fresh-interpreter race evidence.
import subprocess
# Import the current interpreter for exact child-runtime selection.
import sys
# Import disposable directories for isolated JSON provider documents.
import tempfile
# Import bounded polling for deterministic stale-load rendezvous.
import time
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict and validation errors for route assertions.
from casino.errors import ConflictError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.andar_bahar import api, engine
# Import the isolated service orchestration under test.
from casino.games.andar_bahar.service import AndarBaharService


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

    # Apply one callback to provider-current state and return detached authority.
    def update(self, game_id, player_id, mutator, factory):
        # Give the callback an isolated copy of the latest player document.
        current = copy.deepcopy(self.documents.get(player_id, factory()))
        # Apply the transition before publishing any result.
        updated = mutator(current)
        # Persist a detached copy only after the callback completes.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return detached provider-authoritative state to the service.
        return copy.deepcopy(updated)


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only committed event rows.
        self.events = []

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["andar_bahar_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, request_fingerprint, details):
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
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "andar_bahar_action_id": action_key, "request_fingerprint": request_fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class AndarBaharApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Define deterministic fixtures keyed by action id.
        self.fixtures = {"play-win": {"match_card": "7H", "dealt_cards": [{"side": "andar", "card": "2C", "matched": False}, {"side": "bahar", "card": "QS", "matched": False}, {"side": "andar", "card": "7D", "matched": True}]}, "play-loss": {"match_card": "9C", "dealt_cards": [{"side": "andar", "card": "4C", "matched": False}, {"side": "bahar", "card": "9S", "matched": True}]}, "play-bahar-win": {"match_card": "9C", "dealt_cards": [{"side": "andar", "card": "4C", "matched": False}, {"side": "bahar", "card": "9S", "matched": True}]}}
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = AndarBaharService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", fixture_factory=lambda action_id: self.fixtures.get(action_id))
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

    # Confirm identical publication stays idempotent and preserves provider siblings.
    def test_atomic_publication_preserves_siblings_and_private_baseline(self):
        # Load one tracked default document through the service boundary.
        state = self.service._load("session-player")
        # Add one deterministic durable receipt as the desired owned transition.
        state["action_receipts"]["atomic-same"] = {"stage": "play", "round_id": "ab_atomic_same", "request_fingerprint": "a" * 64}
        # Publish the tracked transition through provider-current comparison.
        self.service._save("session-player", state)
        # Add unrelated metadata after the first game-owned publication.
        self.repository.documents["session-player"]["atomic_markers"] = ["sibling"]
        # Publish the exact same desired result from the advanced baseline.
        self.service._save("session-player", state)
        # Read the final provider-authoritative document.
        persisted = self.repository.documents["session-player"]
        # Verify the sibling survives and operation metadata never persists.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Keep the optimistic snapshot outside durable player state.
        self.assertNotIn("_andar_bahar_atomic_baseline", persisted)

    # Confirm rejected wager rollback removes only action-owned prepared state.
    def test_rejected_debit_rollback_preserves_concurrent_sibling(self):
        # Build an empty wallet whose first debit must fail before any event.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh provider-current state for the rejected action.
        empty_repository = MemoryRepository()
        # Retain the ordinary ledger method before injecting a sibling transition.
        apply_once = empty_ledger.apply_once

        # Publish unrelated metadata immediately before the ledger rejects the debit.
        def reject_with_sibling(**kwargs):
            # Add a sibling directly to the provider-current document after preparation.
            empty_repository.documents["session-player"]["atomic_markers"] = ["concurrent"]
            # Delegate to the zero-balance ledger so no movement can commit.
            return apply_once(**kwargs)

        # Inject the concurrent provider update into the first debit boundary.
        empty_ledger.apply_once = reject_with_sibling
        # Build the atomic service against the isolated repository.
        empty_service = AndarBaharService(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_updater=empty_repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", fixture_factory=lambda action_id: self.fixtures["play-win"])
        # Reject the unaffordable action after its recovery state is prepared.
        with self.assertRaises(ValidationError):
            # Attempt one wager that cannot create a ledger event.
            empty_service.play("session-player", {"action_id": "atomic-rollback", "wager": 1, "side": "andar"})
        # Read the provider-authoritative document after rollback.
        persisted = empty_repository.documents["session-player"]
        # Verify action-owned state was removed while the sibling survived.
        self.assertEqual(([], {}, ["concurrent"]), (persisted["recent_rounds"], persisted["action_receipts"], persisted["atomic_markers"]))
        # Verify failure occurred before any append-only money movement.
        self.assertEqual([], empty_ledger.events)
        # Verify private optimistic state never entered provider bytes.
        self.assertNotIn("_andar_bahar_atomic_baseline", persisted)

    # Prove stale fresh processes preserve siblings and admit one terminal winner.
    def test_fresh_process_play_race_has_one_winner_and_zero_loser_ledger_calls(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "session-player.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps(engine.default_state(), sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind every child to the disposable state and exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one worker whose load pauses after capturing stale state.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError
from casino.games.andar_bahar import engine
from casino.games.andar_bahar.service import AndarBaharService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
action_id = sys.argv[3]
def load_state(player_id):
    state = load_player_game_state(engine.GAME_ID, player_id, engine.default_state)
    ready.write_text('ready', encoding='utf-8')
    deadline = time.monotonic() + 10
    while not release.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not release.exists():
        raise RuntimeError('release gate timeout')
    return state
class Ledger:
    def __init__(self):
        self.calls = []
    def find(self, player_id, action_id):
        return None
    def apply_once(self, **kwargs):
        self.calls.append(kwargs['action_key'])
        return {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['signed_amount'], 'transaction_type': kwargs['transaction_type'], 'game': engine.GAME_ID, 'round_id': kwargs['round_id'], 'details': dict(kwargs['details'])}, False
ledger = Ledger()
fixture = {'match_card': '9C', 'dealt_cards': [{'side': 'andar', 'card': '4C', 'matched': False}, {'side': 'bahar', 'card': '9S', 'matched': True}]}
game = AndarBaharService(ledger_gateway=ledger, state_loader=load_state, state_updater=update_player_game_state, get_player=lambda player_id: {'player_id': player_id, 'balance': 100.0}, clock=lambda: '2026-08-15T00:03:00Z', fixture_factory=lambda _action_id: fixture)
try:
    game.play('session-player', {'action_id': action_id, 'wager': 1, 'side': 'andar'})
    print('PASS:' + str(len(ledger.calls)))
except ConflictError:
    print('CONFLICT:' + str(len(ledger.calls)))
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start one provider winner candidate and one stale loser candidate.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"atomic-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.andar_bahar import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('andar_bahar', 'session-player', add, engine.default_state)\n"
            # Commit the sibling after both workers captured stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish and debit the winning round.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require one and only one ledger call from the provider winner.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:1"), winner_error)
            # Release the stale worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require conflict before the losing process reaches the ledger.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT:0"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one terminal winner, sibling preservation, and no overwrite.
            self.assertEqual((persisted["recent_rounds"][-1]["action_id"], persisted["recent_rounds"][-1]["wager_status"], persisted["atomic_markers"]), ("atomic-process-0", "complete", ["concurrent"]))
            # Verify private optimistic metadata never enters persistent bytes.
            self.assertNotIn("_andar_bahar_atomic_baseline", persisted)

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_win(self):
        # Start one play with two competing hostile caller identities.
        first = self.call("/api/v1/games/andar-bahar/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "play-win", "wager": 7, "side": "andar"})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/andar-bahar/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "play-win", "wager": 7, "side": "andar"})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify one wager debit and one payout credit exist after replay.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_WAGER_DEBIT"]))
        # Verify the winning payout credits the complete 1.90x Andar returned-token price.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_PAYOUT_CREDIT"]))
        # Verify the final fake balance reflects one debit and the 1.90x Andar return.
        self.assertEqual(106.3, self.ledger.balances["session-player"])
        # Verify old clients retain the required integer scalar while new clients receive both prices.
        self.assertEqual((2, int, {"andar": 1.9, "bahar": 2.0}), (first["rules"]["return_multiplier"], type(first["rules"]["return_multiplier"]), first["rules"]["return_multipliers"]))
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/andar-bahar/state?player_id=session-player", method="GET", context={"bound_player_id": "other-player", "user": {"player_id": "other-player"}})
        # Verify the other session cannot read the first player's history.
        self.assertEqual([], other_state["state"]["recent_rounds"])

    # Confirm conflicting retries and insufficient funds fail without extra movement.
    def test_play_conflict_and_rejected_debit_cleanup(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-win", "wager": 3, "side": "andar"})
        # Reject reuse of the same identity with a changed side.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-win", "wager": 3, "side": "bahar"})
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Create the isolated empty-balance service.
        empty_service = AndarBaharService(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_updater=empty_repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", fixture_factory=lambda action_id: self.fixtures["play-win"])
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable round.
            empty_service.play("session-player", {"action_id": "play-no-funds", "wager": 1, "side": "andar"})
        # Verify no history row is stranded after a non-committed debit.
        self.assertEqual([], empty_repository.documents["session-player"]["recent_rounds"])
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)

    # Confirm losing side records no zero-value settlement event.
    def test_loss_creates_no_settlement_event(self):
        # Play one losing Andar prediction where Bahar matches first.
        result = self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-loss", "wager": 4, "side": "andar"})
        # Verify the documented losing result and zero returned tokens.
        self.assertEqual(("bahar", "loss", 0.0, "complete"), (result["round"]["winning_side"], result["round"]["outcome"], result["round"]["payout"], result["round"]["settlement_status"]))
        # Verify the game never asks the shared ledger to append a zero credit.
        self.assertEqual([], [event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_PAYOUT_CREDIT"])
        # Verify only the wager debit changed the fake balance.
        self.assertEqual(96.0, self.ledger.balances["session-player"])

    # Confirm Bahar keeps even-money settlement through the public route and ledger.
    def test_bahar_win_retains_even_money_return(self):
        # Play one winning Bahar prediction through the real route adapter.
        result = self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-bahar-win", "wager": 7, "side": "bahar"})
        # Verify the exact winning side, 2.00x payout, and net result.
        self.assertEqual(("bahar", 14.0, 7.0), (result["round"]["winning_side"], result["round"]["payout"], result["round"]["net"]))
        # Verify exactly one payout credit used the side-priced amount.
        payout_events = [event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_PAYOUT_CREDIT"]
        # Require the returned-token ledger movement and resulting wallet value.
        self.assertEqual(([14.0], 107.0), ([event["amount"] for event in payout_events], self.ledger.balances["session-player"]))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
