# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Crown and Anchor API/service tests for issues #133 and #805."""

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
# Import unittest so the focused module can run without central discovery edits.
import unittest
# Import public conflict errors for idempotency assertions.
from casino.errors import ConflictError
# Import the isolated API adapter and pure engine under test.
from casino.games.crown_and_anchor import api, engine
# Import the service class so tests can inject deterministic seams.
from casino.games.crown_and_anchor.service import CrownAndAnchorService


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


# Capture game routes registered by the isolated adapter.
class FakeRouter:
    # Initialize empty route maps for GET and POST handlers.
    def __init__(self):
        # Store GET handlers by route pattern.
        self.gets = {}
        # Store POST handlers by route pattern.
        self.posts = {}

    # Register one GET handler using the production decorator contract.
    def get(self, path):
        # Return a decorator that records the handler.
        def decorator(handler):
            # Store the handler for focused assertions.
            self.gets[path] = handler
            # Return the handler unchanged.
            return handler
        # Return the decorator to the caller.
        return decorator

    # Register one POST handler using the production decorator contract.
    def post(self, path):
        # Return a decorator that records the handler.
        def decorator(handler):
            # Store the handler for focused assertions.
            self.posts[path] = handler
            # Return the handler unchanged.
            return handler
        # Return the decorator to the caller.
        return decorator


# Provide an in-memory exactly-once ledger gateway for service tests.
class FakeLedgerGateway:
    # Initialize an empty committed-event map.
    def __init__(self):
        # Store events by deterministic action key.
        self.events = {}
        # Store every gateway invocation for replay evidence.
        self.calls = []

    # Apply one signed movement only once.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, details):
        # Record each requested action before resolving replay.
        self.calls.append(action_key)
        # Branch when a retry has already committed this action.
        if action_key in self.events:
            # Return the original event and replay evidence.
            return self.events[action_key], True
        # Build a minimal append-only event shape.
        event = {"player_id": player_id, "amount": round(float(amount), 2), "transaction_type": transaction_type, "game": "crown_and_anchor", "round_id": round_id, "details": {**details, "idempotency_key": action_key}, "ts": "2026-07-14T00:00:00Z"}
        # Persist the committed event under its deterministic key.
        self.events[action_key] = event
        # Return the new event and non-replay evidence.
        return event, False


# Cover session-bound routing and exactly-once service behavior.
class CrownAndAnchorApiTests(unittest.TestCase):
    # Build a deterministic service for each test.
    def make_service(self, faces=None, repository=None, ledger=None):
        # Store player states behind one provider-current fake boundary.
        state_repository = repository or MemoryRepository()
        # Reuse a supplied ledger when testing crash recovery.
        ledger_gateway = ledger or FakeLedgerGateway()
        # Copy the requested deterministic dice faces.
        pending_faces = list(faces or [1, 2, 3])
        # Pop one deterministic face per dice roll.
        roller = lambda: pending_faces.pop(0)
        # Return a service with fake ports and exposed state.
        return CrownAndAnchorService(ledger_gateway=ledger_gateway, state_loader=state_repository.load, state_updater=state_repository.update, roll_die=roller, clock=lambda: "2026-07-14T00:00:00Z")

    # Confirm identical publication stays idempotent and preserves siblings.
    def test_atomic_publication_preserves_siblings_and_private_baseline(self):
        # Retain the fake provider so final bytes are directly observable.
        repository = MemoryRepository()
        # Build the service around the provider-current seams.
        service = self.make_service(repository=repository)
        # Load one tracked default document through the service boundary.
        state = service._load("player-a")
        # Add one deterministic settled row as the desired owned transition.
        state["recent_rounds"].append({"client_request_id": "atomic-same", "request_fingerprint": "a" * 64})
        # Publish the tracked transition through provider-current comparison.
        service._save("player-a", state)
        # Add unrelated metadata after the first game-owned publication.
        repository.documents["player-a"]["atomic_markers"] = ["sibling"]
        # Publish the exact same desired result from the advanced baseline.
        service._save("player-a", state)
        # Read the final provider-authoritative document.
        persisted = repository.documents["player-a"]
        # Verify the sibling survives and operation metadata never persists.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Keep the optimistic snapshot outside durable player state.
        self.assertNotIn("_crown_and_anchor_atomic_baseline", persisted)

    # Reject fabricated detached state before entering the provider updater.
    def test_missing_atomic_baseline_fails_before_update(self):
        # Retain a call list that must stay empty on fail-closed input.
        updates = []
        # Build a service with a provider seam that would reveal accidental entry.
        service = CrownAndAnchorService(state_updater=lambda *args: updates.append(args))
        # Reject an untracked default document as a stale publication.
        with self.assertRaises(ConflictError):
            # Attempt publication without the required provider-read baseline.
            service._save("player-a", {"game": "crown_and_anchor", "recent_rounds": []})
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
            state_path = data_root / "games" / "crown_and_anchor" / "session-player.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps({"game": "crown_and_anchor", "recent_rounds": []}, sort_keys=True), encoding="utf-8")
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
from casino.games.crown_and_anchor import engine
from casino.games.crown_and_anchor.service import CrownAndAnchorService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
request_id = sys.argv[3]
def load_state(player_id):
    state = load_player_game_state('crown_and_anchor', player_id, engine.default_state)
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
        return {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['amount'], 'transaction_type': kwargs['transaction_type'], 'game': 'crown_and_anchor', 'round_id': kwargs['round_id'], 'ts': '2026-08-15T01:00:00Z', 'details': dict(kwargs['details'])}, False
ledger = Ledger()
faces = iter((2, 3, 4))
game = CrownAndAnchorService(ledger_gateway=ledger, state_loader=load_state, state_updater=update_player_game_state, roll_die=lambda: next(faces), clock=lambda: '2026-08-15T01:00:00Z')
try:
    game.play('session-player', {'client_request_id': request_id, 'wagers': {'crown': 1}})
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.crown_and_anchor import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('crown_and_anchor', 'session-player', add, engine.default_state)\n"
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
            self.assertNotIn("_crown_and_anchor_atomic_baseline", persisted)

    # Verify body and query player_id cannot override authenticated context.
    def test_request_player_id_prefers_session_context(self):
        # Resolve a trusted context identity despite hostile caller ids.
        player_id = api.request_player_id({"player_id": "attacker"}, {"player_id": "query"}, {"bound_player_id": "session-player"})
        # Assert the session-bound player wins.
        self.assertEqual(player_id, "session-player")

    # Verify the registered handler uses trusted identity and settles one round.
    def test_registered_round_uses_session_identity(self):
        # Create a fake router for isolated registration.
        router = FakeRouter()
        # Create a deterministic service with three crown hits.
        service = self.make_service([1, 1, 1])
        # Register the game-owned routes with the fake service.
        api.register(router, service=service)
        # Execute one round with a hostile body player id.
        payload = router.posts[r"/api/v1/games/crown-and-anchor/rounds"]({"player_id": "attacker", "client_request_id": "round-0001", "wagers": {"crown": 5}}, {}, context={"resolved_player_id": "trusted"})
        # Assert the public round is bound to the trusted session identity.
        self.assertEqual(payload["round"]["player_id"], "trusted")
        # Assert the three-hit payout returns stake plus three-to-one net.
        self.assertEqual(payload["round"]["total_return"], 20.0)

    # Verify exact retries reuse the original ledger movements and dice.
    def test_exact_retry_is_replayed_once(self):
        # Create a deterministic service with one prepared roll.
        service = self.make_service([1, 2, 3])
        # Execute one new command.
        first = service.play("player-a", {"client_request_id": "round-0002", "wagers": {"anchor": 2}})
        # Replay the exact same command after state persisted.
        second = service.play("player-a", {"client_request_id": "round-0002", "wagers": {"anchor": 2}})
        # Assert the retry reports replay status.
        self.assertTrue(second["replayed"])
        # Assert the dice result stays identical.
        self.assertEqual(second["round"]["faces"], first["round"]["faces"])

    # Verify a retry after debit commit reconstructs the committed dice and pays once.
    def test_post_debit_retry_recovers_committed_faces(self):
        # Retain one provider and ledger across the simulated interruption.
        repository, ledger = MemoryRepository(), FakeLedgerGateway()
        # Define the exact request whose debit reached durable ledger state.
        request = {"client_request_id": "round-crash", "wagers": {"crown": 2}}
        # Normalize the durable wager shape used by service fingerprints.
        wagers = engine.normalize_wagers(request["wagers"])
        # Derive the stable round identity used by both attempts.
        round_id = engine.round_id_for("player-a", request["client_request_id"])
        # Commit only the debit with a three-crown result before state publication.
        ledger.apply_once(player_id="player-a", amount=-2.0, transaction_type="CROWN_AND_ANCHOR_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", details={"client_request_id": request["client_request_id"], "request_fingerprint": engine.wager_fingerprint(wagers), "wagers": wagers, "faces": [1, 1, 1]})
        # Retry with different proposed dice so committed-ledger recovery is observable.
        recovering = self.make_service([2, 3, 4], repository=repository, ledger=ledger)
        # Resume settlement and state publication without another debit identity.
        result = recovering.play("player-a", request)
        # Require the committed three-crown result rather than the new proposal.
        self.assertEqual(([1, 1, 1], 8.0), (result["round"]["faces"], result["round"]["total_return"]))
        # Keep one durable debit and one durable settlement credit only.
        self.assertEqual(2, len(ledger.events))

    # Verify conflicting reuse of one request id fails before new dice or ledger actions.
    def test_conflicting_retry_rejected(self):
        # Create a deterministic service with one prepared roll.
        service = self.make_service([1, 2, 3])
        # Execute one new command.
        service.play("player-a", {"client_request_id": "round-0003", "wagers": {"anchor": 2}})
        # Assert different wagers under the same request id fail closed.
        with self.assertRaises(ConflictError):
            # Reuse the public identity with conflicting coverage.
            service.play("player-a", {"client_request_id": "round-0003", "wagers": {"crown": 2}})


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest's standard command-line runner.
    unittest.main()
