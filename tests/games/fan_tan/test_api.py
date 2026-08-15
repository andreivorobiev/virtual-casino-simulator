# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for issues #137 and #807."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
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
# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict errors for route assertions.
from casino.errors import ConflictError
# Import the isolated route adapter and pure engine under test.
from casino.games.fan_tan import api, engine
# Import the isolated service orchestration under test.
from casino.games.fan_tan.service import FanTanService


# Simulate player-scoped state documents with provider-current callbacks.
class MemoryRepository:
    # Start with no persisted game documents.
    def __init__(self):
        # Store detached documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so every mutation requires an explicit save.
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


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only committed event rows.
        self.events = []
        # Record every gateway invocation so recovery call counts stay explicit.
        self.calls = []

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"]["fan_tan_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_id, fingerprint, details):
        # Record each requested action before resolving replay.
        self.calls.append(action_id)
        # Resolve any prior committed action before changing the fake balance.
        existing = self.find(player_id, action_id)
        # Reuse an exact matching event.
        if existing is not None:
            # Reject semantic conflicts like the production gateway.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance after the signed movement.
        self.balances[player_id] = round(self.balances[player_id] + signed_amount, 2)
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "fan_tan_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, and ledger audit dimensions.
class FanTanApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: 3, clock=lambda: "2026-07-14T00:00:00Z")
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
        self.assertNotIn("_fan_tan_atomic_baseline", persisted)

    # Reject fabricated detached state before entering the provider updater.
    def test_missing_atomic_baseline_fails_before_update(self):
        # Retain a call list that must stay empty on fail-closed input.
        updates = []
        # Build a service with a provider seam that would reveal accidental entry.
        service = FanTanService(state_updater=lambda *args: updates.append(args))
        # Reject an untracked default document as a stale publication.
        with self.assertRaises(ConflictError):
            # Attempt publication without the required provider-read baseline.
            service._save("session-player", {"game": "fan_tan", "recent_rounds": []})
        # Prove storage was never reached.
        self.assertEqual([], updates)

    # Prove stale fresh processes preserve siblings and expose one conflict.
    def test_fresh_process_round_race_has_one_state_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / "fan_tan" / "session-player.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps({"game": "fan_tan", "recent_rounds": []}, sort_keys=True), encoding="utf-8")
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
from casino.games.fan_tan import engine
from casino.games.fan_tan.service import FanTanService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
action_id = sys.argv[3]
def load_state(player_id):
    state = load_player_game_state('fan_tan', player_id, engine.default_state)
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
    def apply_once(self, **kwargs):
        self.calls.append(kwargs['action_id'])
        return {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['signed_amount'], 'transaction_type': kwargs['transaction_type'], 'game': 'fan_tan', 'round_id': kwargs['round_id'], 'ts': '2026-08-15T01:00:00Z', 'details': dict(kwargs['details'])}, False
ledger = Ledger()
game = FanTanService(ledger_gateway=ledger, state_loader=load_state, state_updater=update_player_game_state, randbelow=lambda span: 1, clock=lambda: '2026-08-15T01:00:00Z')
try:
    game.play('session-player', {'action_id': action_id, 'wagers': {'1': 1}})
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.fan_tan import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('fan_tan', 'session-player', add, engine.default_state)\n"
            # Commit the sibling after both workers captured stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish the winning round.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require one losing-round debit call from the provider winner.
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
            self.assertEqual((len(persisted["recent_rounds"]), persisted["recent_rounds"][-1]["action_id"], persisted["atomic_markers"]), (1, "atomic-process-0", ["concurrent"]))
            # Verify private optimistic metadata never enters persistent bytes.
            self.assertNotIn("_fan_tan_atomic_baseline", persisted)

    # Verify a retry after debit commit reconstructs the committed count and pays once.
    def test_post_debit_retry_recovers_committed_pile_count(self):
        # Define the exact request whose debit reached durable ledger state.
        request = {"action_id": "fan-crash", "wagers": {"4": 2}}
        # Normalize the durable wager shape used by service fingerprints.
        wagers = engine.normalize_wagers(request["wagers"])
        # Derive the stable round identity used by both attempts.
        round_id = engine.round_id_for("session-player", request["action_id"])
        # Commit only the debit with a winning residue-four result before state publication.
        self.ledger.apply_once(player_id="session-player", signed_amount=-2.0, transaction_type="FAN_TAN_WAGER_DEBIT", round_id=round_id, action_id=f"{round_id}:wager", fingerprint=engine.wager_fingerprint(wagers), details={"action_id": request["action_id"], "wagers": wagers, "pile_count": 52})
        # Retry with a different proposed pile so committed-ledger recovery is observable.
        recovering = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: 0, clock=lambda: "2026-07-14T00:00:00Z")
        # Resume settlement and state publication without another debit identity.
        result = recovering.play("session-player", request)
        # Require the committed residue-four result rather than the new proposal.
        self.assertEqual((52, "4", 8.0), (result["round"]["pile_count"], result["round"]["residue"], result["round"]["total_return"]))
        # Keep one durable debit and one durable settlement credit only.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_play(self):
        # Start one round with two competing hostile caller identities.
        first = self.call("/api/v1/games/fan-tan/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "fan-retry-1", "wagers": {"4": 5}})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/fan-tan/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "fan-retry-1", "wagers": {"4": 5}})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one wager debit and one settlement credit exist.
        self.assertEqual((1, 1), (len([event for event in self.ledger.events if event["transaction_type"] == "FAN_TAN_WAGER_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "FAN_TAN_SETTLEMENT_CREDIT"])))
        # Verify the winning round produced the documented net balance change.
        self.assertEqual(115.0, self.ledger.balances["session-player"])

    # Confirm conflicting action retries fail without duplicate ledger movements.
    def test_conflicting_retry_rejected(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/fan-tan/rounds", {"action_id": "fan-conflict", "wagers": {"1": 3}})
        # Reject reuse of the same identity with changed wagers.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/fan-tan/rounds", {"action_id": "fan-conflict", "wagers": {"1": 4}})
        # Verify the conflicting retry created no second debit.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "FAN_TAN_WAGER_DEBIT"]))

    # Confirm state is player-scoped and exposes transparent rules metadata.
    def test_state_is_session_scoped_with_rules(self):
        # Create one session-owned settled round.
        self.call("/api/v1/games/fan-tan/rounds", {"action_id": "fan-state", "wagers": {"4": 2}})
        # Read state through a different authenticated session while spoofing the first player.
        other = self.call("/api/v1/games/fan-tan/state?player_id=session-player", method="GET", context={"bound_player_id": "other-player", "user": {"player_id": "other-player"}})
        # Verify the other session sees no first-player history.
        self.assertEqual([], other["state"]["recent_rounds"])
        # Verify the backend owns the paytable and modulo-four profile.
        self.assertEqual(("counted-pile-modulo-four", 4), (other["rules"]["profile"], len(other["outcomes"])))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
