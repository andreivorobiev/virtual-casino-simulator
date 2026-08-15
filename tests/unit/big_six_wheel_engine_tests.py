# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused issue-86 tests for Big Six rules, settlement, and exactly-once service behavior."""

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
# Import the standard dependency-free unit-test runner.
import unittest
# Import the project conflict error used for idempotency misuse.
from casino.errors import ConflictError
# Import the pure game engine under direct test.
from casino.games.big_six_wheel import engine
# Import the immutable wheel profile under direct test.
from casino.games.big_six_wheel.rules import NET_ODDS, SEGMENT_COUNTS, WHEEL_SEGMENTS
# Import the orchestration service with injectable storage, entropy, and ledger seams.
from casino.games.big_six_wheel.service import BigSixWheelService


# Simulate player-scoped state documents with provider-current callbacks.
class MemoryRepository:
    # Start with no persisted documents.
    def __init__(self):
        # Store detached documents by player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Return a deep copy so mutation requires explicit publication.
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


# Provide an in-memory ledger gateway that enforces the same action-key contract.
class FakeLedgerGateway:
    # Initialize stable event storage and call evidence.
    def __init__(self):
        # Store committed events by deterministic action key.
        self.events = {}
        # Store every gateway invocation so replay behavior is observable.
        self.calls = []

    # Apply or replay one event without touching any real player balance.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, details):
        # Record each requested action for exact call-count assertions.
        self.calls.append(action_key)
        # Return an existing event when the action key already committed.
        if action_key in self.events:
            # Reuse the original event as exactly-once evidence.
            return self.events[action_key], True
        # Build a minimal shared-ledger-shaped event for service recovery logic.
        event = {"player_id": player_id, "amount": amount, "transaction_type": transaction_type, "round_id": round_id, "ts": "2026-07-13T00:00:00Z", "details": {**details, "idempotency_key": action_key}}
        # Commit the event under its deterministic identity.
        self.events[action_key] = event
        # Return the new event and non-replay evidence.
        return event, False


# Verify the regulated profile and pure settlement calculations.
class BigSixWheelEngineTests(unittest.TestCase):
    # Confirm the wheel has exactly the documented distribution.
    def test_regulated_wheel_profile_counts(self):
        # Verify the physical profile contains exactly 54 ordered segments.
        self.assertEqual(54, len(WHEEL_SEGMENTS))
        # Verify each outcome count against immutable rule metadata.
        self.assertEqual(dict(SEGMENT_COUNTS), {outcome: WHEEL_SEGMENTS.count(outcome) for outcome in SEGMENT_COUNTS})
        # Verify the two unique symbols use the selected 45-to-1 profile.
        self.assertEqual((45, 45), (NET_ODDS["joker"], NET_ODDS["crest"]))

    # Confirm an injected index produces deterministic multi-wager settlement.
    def test_settlement_is_deterministic_for_selected_index(self):
        # Normalize two outcome wagers through the public validation path.
        wagers = engine.normalize_wagers({"one": 3, "joker": 2})
        # Select the first Joker segment deterministically.
        result = engine.settle(wagers, 0)
        # Verify the canonical outcome and total wager.
        self.assertEqual(("joker", 5.0), (result["outcome"], result["total_wager"]))
        # Verify a two-token Joker wager returns stake plus 45-to-1 net winnings.
        self.assertEqual(92.0, result["total_return"])
        # Verify losing covered outcomes remain visible in the result rows.
        self.assertEqual(-3.0, next(row["net"] for row in result["settlements"] if row["outcome"] == "one"))

    # Confirm equal client actions produce one stable round id without exposing raw identity.
    def test_round_id_is_stable_and_player_scoped(self):
        # Derive the same round twice for retry identity.
        first = engine.round_id_for("player-a", "request-17")
        # Repeat the derivation through the same public helper.
        second = engine.round_id_for("player-a", "request-17")
        # Verify deterministic replay identity.
        self.assertEqual(first, second)
        # Verify another authenticated player cannot collide with this round.
        self.assertNotEqual(first, engine.round_id_for("player-b", "request-17"))
        # Verify free-form request text is not included in the persisted round id.
        self.assertNotIn("request", first)


# Verify ledger-only orchestration and crash/retry recovery.
class BigSixWheelServiceTests(unittest.TestCase):
    # Build an isolated service and its mutable test seams.
    def setUp(self):
        # Store player documents behind a provider-current fake boundary.
        self.repository = MemoryRepository()
        # Create the fake apply-once ledger adapter.
        self.ledger = FakeLedgerGateway()
        # Build the service with deterministic Joker selection and pinned time.
        self.service = BigSixWheelService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda size: 0, clock=lambda: "2026-07-13T00:00:00Z")

    # Confirm identical publication stays idempotent and preserves siblings.
    def test_atomic_publication_preserves_siblings_and_private_baseline(self):
        # Load one tracked default document through the service boundary.
        state = self.service._load("player-a")
        # Add one deterministic settled row as the desired owned transition.
        state["recent_rounds"].append({"client_request_id": "atomic-same", "request_fingerprint": "a" * 64})
        # Publish the tracked transition through provider-current comparison.
        self.service._save("player-a", state)
        # Add unrelated metadata after the first game-owned publication.
        self.repository.documents["player-a"]["atomic_markers"] = ["sibling"]
        # Publish the exact same desired result from the advanced baseline.
        self.service._save("player-a", state)
        # Read the final provider-authoritative document.
        persisted = self.repository.documents["player-a"]
        # Verify the sibling survives and operation metadata never persists.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Keep the optimistic snapshot outside durable player state.
        self.assertNotIn("_big_six_wheel_atomic_baseline", persisted)

    # Prove stale fresh processes preserve siblings and expose one conflict.
    def test_fresh_process_spin_race_has_one_state_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[2]
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
from casino.games.big_six_wheel import engine
from casino.games.big_six_wheel.service import BigSixWheelService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
request_id = sys.argv[3]
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
    def apply_once(self, **kwargs):
        self.calls.append(kwargs['action_key'])
        return {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['amount'], 'transaction_type': kwargs['transaction_type'], 'game': engine.GAME_ID, 'round_id': kwargs['round_id'], 'ts': '2026-08-15T00:03:00Z', 'details': dict(kwargs['details'])}, False
ledger = Ledger()
game = BigSixWheelService(ledger_gateway=ledger, state_loader=load_state, state_updater=update_player_game_state, randbelow=lambda _size: 0, clock=lambda: '2026-08-15T00:03:00Z')
try:
    game.spin('session-player', {'client_request_id': request_id, 'wagers': {'one': 1}})
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.big_six_wheel import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('big_six_wheel', 'session-player', add, engine.default_state)\n"
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
            self.assertEqual((len(persisted["recent_rounds"]), persisted["recent_rounds"][-1]["client_request_id"], persisted["atomic_markers"]), (1, "atomic-process-0", ["concurrent"]))
            # Verify private optimistic metadata never enters persistent bytes.
            self.assertNotIn("_big_six_wheel_atomic_baseline", persisted)

    # Confirm a normal retry returns one debit and one credit only.
    def test_retry_reuses_settled_round_without_new_ledger_actions(self):
        # Define one complete retry-safe request.
        request = {"client_request_id": "retry-1", "wagers": {"joker": 2}}
        # Execute the original atomic spin.
        first = self.service.spin("player-a", request)
        # Repeat the identical action identity.
        second = self.service.spin("player-a", request)
        # Verify both responses identify the same settled round.
        self.assertEqual(first["round"], second["round"])
        # Verify the state-cache retry is explicitly reported.
        self.assertTrue(second["replayed"])
        # Verify exactly one debit and one settlement credit were requested.
        self.assertEqual(2, len(self.ledger.calls))

    # Confirm a crash after ledger commit reconstructs the committed result and credits once.
    def test_post_debit_crash_retry_recovers_committed_index(self):
        # Define one complete retry-safe request.
        request = {"client_request_id": "crash-1", "wagers": {"joker": 2}}
        # Derive the stable round and request identity used by the service.
        round_id = engine.round_id_for("player-a", "crash-1")
        # Normalize and fingerprint the original wagers.
        wagers = engine.normalize_wagers(request["wagers"])
        # Precommit only the debit to simulate a crash before settlement and state save.
        self.ledger.apply_once(player_id="player-a", amount=-2.0, transaction_type="BIG_SIX_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", details={"client_request_id": "crash-1", "request_fingerprint": engine.wager_fingerprint(wagers), "wagers": wagers, "result_index": 0})
        # Retry with an entropy source that would choose another segment if recovery failed.
        recovering = BigSixWheelService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda size: 1, clock=lambda: "later")
        # Resume the interrupted action.
        result = recovering.spin("player-a", request)
        # Verify the committed Joker result wins instead of the new index-one proposal.
        self.assertEqual((0, "joker", 92.0), (result["round"]["result_index"], result["round"]["outcome"], result["round"]["total_return"]))
        # Verify the fake ledger contains only one debit and one credit identity.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm one idempotency identity cannot represent different wager content.
    def test_conflicting_request_identity_fails_closed(self):
        # Commit one settled request identity.
        self.service.spin("player-a", {"client_request_id": "same-id", "wagers": {"joker": 1}})
        # Reject a different wager map under the same client identity.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting replay boundary.
            self.service.spin("player-a", {"client_request_id": "same-id", "wagers": {"one": 1}})


# Run the focused suite directly without central runner registration.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
