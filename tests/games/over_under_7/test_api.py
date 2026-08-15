# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once tests for issue #135."""

# Import deep-copy support so fake persistence models JSON boundaries.
import copy
# Import JSON encoding for real provider-state fixtures.
import json
# Import process environments for isolated provider workers.
import os
# Import filesystem paths for task-owned rendezvous gates.
from pathlib import Path
# Import child-process execution for true cross-process races.
import subprocess
# Import the active interpreter for exact worker parity.
import sys
# Import temporary directories for residue-free provider evidence.
import tempfile
# Import monotonic time for bounded rendezvous polling.
import time
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise route patterns.
from casino.router import Router
# Import public conflict and validation errors for route assertions.
from casino.errors import ConflictError, ValidationError
# Import the isolated API and engine modules.
from casino.games.over_under_7 import api, engine
# Import the isolated service under test.
from casino.games.over_under_7.service import OverUnder7Service


# Simulate player-scoped state documents without touching data files.
class MemoryRepository:
    # Start with no persisted documents.
    def __init__(self):
        # Store detached documents by player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Return a deep copy so mutation requires save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Update one player document through a provider-current callback.
    def update(self, game_id, player_id, mutator, factory):
        # Load current provider state or one fresh game default.
        current = copy.deepcopy(self.documents.get(player_id, factory()))
        # Apply the production-shaped callback to provider-current state.
        updated = mutator(current)
        # Persist a detached result to model JSON storage.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return a detached authoritative publication.
        return copy.deepcopy(updated)


# Record signed ledger events and enforce action-key replay in memory.
class RecordingLedger:
    # Seed deterministic balances for isolated players.
    def __init__(self, balances=None):
        # Store fake balances only inside this test adapter.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only event rows.
        self.events = []

    # Find one committed action key for a player.
    def find(self, player_id, action_key):
        # Search newest first using the game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"]["over_under_7_action_key"] == action_key), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, fingerprint, details):
        # Resolve any prior committed action.
        existing = self.find(player_id, action_key)
        # Reuse exact matching events.
        if existing is not None:
            # Reject semantic conflicts.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action conflict")
            # Return detached proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance.
        self.balances[player_id] = new_balance
        # Build the public ledger row used by service recovery.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "ts": "2026-07-14T00:00:00Z", "details": {**copy.deepcopy(details), "over_under_7_action_key": action_key, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, reload recovery, and ledger audit dimensions.
class OverUnder7ApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and ledger events.
        self.ledger = RecordingLedger()
        # Build deterministic dice values for exact-seven then under results.
        self.dice_values = iter([2, 3, 0, 4])
        # Build the isolated service without filesystem or ambient randomness.
        self.service = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda sides: next(self.dice_values), clock=lambda: "2026-07-14T00:00:00Z")
        # Register only game-owned routes on the real router.
        self.router = Router()
        # Inject the focused service.
        api.register(self.router, service=self.service)
        # Store the authenticated context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch through the shared router.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so requests remain isolated.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Confirm identical publication stays idempotent and preserves siblings.
    def test_atomic_publication_preserves_siblings_and_private_baseline(self):
        # Load one tracked default document through the service boundary.
        state = self.service._load("session-player")
        # Add one deterministic settled row as the desired owned transition.
        state["recent_rounds"].append({"action_id": "atomic-same", "request_fingerprint": "a" * 64})
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
        self.assertNotIn("_over_under_7_atomic_baseline", persisted)

    # Confirm rejected debit never publishes a round or loses a sibling.
    def test_rejected_debit_preserves_concurrent_sibling(self):
        # Build an empty wallet whose first debit must fail before any event.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh provider-current state for the rejected action.
        empty_repository = MemoryRepository()
        # Retain the ordinary ledger method before injecting a sibling update.
        apply_once = empty_ledger.apply_once

        # Publish unrelated metadata immediately before rejecting the debit.
        def reject_with_sibling(**kwargs):
            # Ensure one provider document exists for the concurrent sibling.
            current = empty_repository.documents.setdefault("session-player", engine.default_state())
            # Add metadata outside the game's owned state field.
            current["atomic_markers"] = ["concurrent"]
            # Delegate to the zero-balance ledger so no movement can commit.
            return apply_once(**kwargs)

        # Inject the concurrent provider update into the first debit boundary.
        empty_ledger.apply_once = reject_with_sibling
        # Build the atomic service against the isolated repository.
        empty_service = OverUnder7Service(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_updater=empty_repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, randbelow=lambda sides: 0, clock=lambda: "2026-07-14T00:00:00Z")
        # Reject the unaffordable action before any state publication.
        with self.assertRaises(ValidationError):
            # Attempt one wager that cannot create a ledger event.
            empty_service.play("session-player", {"action_id": "atomic-rollback", "wagers": {"under": 1}})
        # Read the provider-authoritative document after rejection.
        persisted = empty_repository.documents["session-player"]
        # Verify no terminal row exists while the sibling survives.
        self.assertEqual(([], ["concurrent"]), (persisted["recent_rounds"], persisted["atomic_markers"]))
        # Verify failure occurred before any append-only money movement.
        self.assertEqual([], empty_ledger.events)
        # Verify private optimistic state never entered provider bytes.
        self.assertNotIn("_over_under_7_atomic_baseline", persisted)

    # Prove stale fresh processes preserve siblings and expose one conflict.
    def test_fresh_process_play_race_has_one_state_winner(self):
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
from casino.games.over_under_7 import engine
from casino.games.over_under_7.service import OverUnder7Service
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
    def find(self, player_id, action_key):
        return None
    def apply_once(self, **kwargs):
        self.calls.append(kwargs['action_key'])
        return {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['signed_amount'], 'transaction_type': kwargs['transaction_type'], 'game': engine.GAME_ID, 'round_id': kwargs['round_id'], 'ts': '2026-08-15T00:03:00Z', 'details': dict(kwargs['details'])}, False
ledger = Ledger()
game = OverUnder7Service(ledger_gateway=ledger, state_loader=load_state, state_updater=update_player_game_state, get_player=lambda player_id: {'player_id': player_id, 'balance': 100.0}, randbelow=lambda _sides: 0, clock=lambda: '2026-08-15T00:03:00Z')
try:
    game.play('session-player', {'action_id': action_id, 'wagers': {'seven': 1}})
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.over_under_7 import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('over_under_7', 'session-player', add, engine.default_state)\n"
            # Commit the sibling after both workers captured stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish the winning round.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require one losing debit call from the provider winner.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:1"), winner_error)
            # Release the stale worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the explicit fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require conflict instead of a silent stale overwrite.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT:1"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one terminal winner, sibling preservation, and no overwrite.
            self.assertEqual((persisted["recent_rounds"][-1]["action_id"], persisted["atomic_markers"]), ("atomic-process-0", ["concurrent"]))
            # Verify private optimistic metadata never enters persistent bytes.
            self.assertNotIn("_over_under_7_atomic_baseline", persisted)

    # Confirm hostile player ids cannot override the authenticated session.
    def test_session_binding_and_exact_replay(self):
        # Play once with hostile caller-supplied ids.
        first = self.call("/api/v1/games/over-under-7/plays?player_id=other-player", {"player_id": "other-player", "action_id": "play-1", "wagers": {"seven": 5}})
        # Replay the exact action.
        second = self.call("/api/v1/games/over-under-7/plays?player_id=other-player", {"player_id": "other-player", "action_id": "play-1", "wagers": {"seven": 5}})
        # Verify ownership follows the session only.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance is untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same round is returned on retry.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one debit and one settlement credit exist.
        self.assertEqual((1, 1), (len([event for event in self.ledger.events if event["transaction_type"] == "OVER_UNDER_7_WAGER_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "OVER_UNDER_7_SETTLEMENT_CREDIT"])))
        # Verify exact-seven return used stake plus 4:1 net.
        self.assertEqual((25.0, 120.0), (first["round"]["total_return"], self.ledger.balances["session-player"]))

    # Confirm changed retries fail closed.
    def test_conflicting_retry_rejected(self):
        # Commit one valid play.
        self.call("/api/v1/games/over-under-7/plays", {"action_id": "play-conflict", "wagers": {"under": 3}})
        # Reject reuse with changed wagers.
        with self.assertRaises(ConflictError):
            # Exercise semantic action-id conflict.
            self.call("/api/v1/games/over-under-7/plays", {"action_id": "play-conflict", "wagers": {"under": 4}})
        # Verify no extra debit was created.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "OVER_UNDER_7_WAGER_DEBIT"]))

    # Confirm committed debit details recover a round after lost state.
    def test_reload_recovery_from_committed_debit(self):
        # Create a service that fails its atomic state update after ledger movements.
        class FailingRepository(MemoryRepository):
            # Fail all updates to simulate a post-ledger crash.
            def update(self, game_id, player_id, mutator, factory):
                # Raise after ledger events commit but before state publication.
                raise RuntimeError("simulated save crash")
        # Create isolated failing storage.
        failing_repository = FailingRepository()
        # Create a deterministic ledger.
        ledger = RecordingLedger()
        # Build an explicit two-die sequence that totals seven.
        dice_values = iter([2, 3])
        # Build a service with controlled exact-seven dice.
        service = OverUnder7Service(ledger_gateway=ledger, state_loader=failing_repository.load, state_updater=failing_repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, randbelow=lambda sides: next(dice_values), clock=lambda: "2026-07-14T00:00:00Z")
        # Allow the save failure to happen after ledger commit.
        with self.assertRaises(RuntimeError):
            # Execute the play once.
            service.play("session-player", {"action_id": "recover-play", "wagers": {"seven": 5}})
        # Create normal restarted storage for recovered state.
        restarted_repository = MemoryRepository()
        # Build a restarted service with normal storage but the same ledger.
        restarted = OverUnder7Service(ledger_gateway=ledger, state_loader=restarted_repository.load, state_updater=restarted_repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, randbelow=lambda sides: 0, clock=lambda: "2026-07-14T00:00:01Z")
        # Replay the same action and recover from debit/credit ledger proof.
        recovered = restarted.play("session-player", {"action_id": "recover-play", "wagers": {"seven": 5}})
        # Verify recovery did not append duplicate movements.
        self.assertEqual((True, 2), (recovered["replayed"], len(ledger.events)))
        # Verify dice came from durable ledger details rather than new randomness.
        self.assertEqual([3, 4], recovered["round"]["dice"])


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
