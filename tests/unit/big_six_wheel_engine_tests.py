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
# Import the pure game engine and orchestration source under direct test.
from casino.games.big_six_wheel import engine, service as service_module
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
        # Allow one test to publish a concurrent sibling immediately before the provider callback.
        self.before_update = None

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Return a deep copy so mutation requires explicit publication.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Update one player document through a provider-current callback.
    def update(self, game_id, player_id, mutator, factory):
        # Execute one scheduled provider-current publication before the tested mutator.
        if self.before_update is not None:
            # Detach the hook before execution so a failed callback cannot repeat it.
            hook, self.before_update = self.before_update, None
            # Apply the sibling update to exact provider-owned state.
            hook(self.documents.setdefault(player_id, factory()))
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
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint=None, details):
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

    # Find one committed event through the shared helper's exact action identity.
    def find(self, *, action_key, **_dimensions):
        # Return the immutable fake event or no proof for a losing settlement lookup.
        return self.events.get(action_key)


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

    # Require production orchestration to delegate money movement exclusively to SimpleWagerGame.
    def test_service_uses_shared_simple_wager_boundary(self):
        # Read exact tracked production source instead of trusting runtime monkeypatches.
        source = Path(service_module.__file__).read_text(encoding="utf-8")
        # Require one shared-helper construction and no direct compatibility gateway or apply-once call.
        self.assertEqual((source.count("SimpleWagerGame("), "GameSettlementGateway" in source, ".apply_once(" in source), (1, False, False))

    # Confirm shared publication merges distinct rounds and unrelated provider siblings.
    def test_atomic_publication_preserves_distinct_round_and_sibling(self):
        # Define one provider-current sibling and previously committed round.
        def publish_concurrent(current):
            # Preserve one unrelated field through the shared-helper callback.
            current["atomic_markers"] = ["sibling"]
            # Publish one distinct legacy-shaped round after the action's initial read.
            current["recent_rounds"] = [{"round_id": "bsw_other", "client_request_id": "other", "request_fingerprint": "other-fingerprint", "player_id": "player-a", "status": "settled", "wagers": {"one": 1.0}, "settled_at": "2026-07-12T00:00:00Z", **engine.settle({"one": 1.0}, 1)}]

        # Schedule the publication at the exact provider-owned update boundary.
        self.repository.before_update = publish_concurrent
        # Execute one distinct round from the stale initial state snapshot.
        result = self.service.spin("player-a", {"client_request_id": "atomic-same", "wagers": {"joker": 2}})
        # Read the final provider-authoritative direct-row document.
        persisted = self.repository.documents["player-a"]
        # Verify the unrelated sibling and both distinct terminal rounds survive.
        self.assertEqual((["sibling"], ["other", "atomic-same"]), (persisted["atomic_markers"], [row["client_request_id"] for row in persisted["recent_rounds"]]))
        # Preserve the exact frozen direct-row state shape without shared wrapper fields.
        self.assertEqual(result["round"], persisted["recent_rounds"][-1])
        # Keep shared-helper storage wrappers outside durable Big Six state.
        self.assertTrue(all("public" not in row and "request_id" not in row for row in persisted["recent_rounds"]))

    # Prove stale fresh processes preserve both distinct rounds and unrelated siblings.
    def test_fresh_process_spin_race_preserves_both_rounds(self):
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
        self.events = {}
    def apply_once(self, **kwargs):
        self.calls.append(kwargs['action_key'])
        if kwargs['action_key'] in self.events:
            return self.events[kwargs['action_key']], True
        event = {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['amount'], 'transaction_type': kwargs['transaction_type'], 'game': engine.GAME_ID, 'round_id': kwargs['round_id'], 'ts': '2026-08-15T00:03:00Z', 'details': dict(kwargs['details'])}
        self.events[kwargs['action_key']] = event
        return event, False
    def find(self, **kwargs):
        return self.events.get(kwargs['action_key'])
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
            # Release the first worker to publish its distinct round.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact first result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require one losing-round debit call from the first provider worker.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:1"), winner_error)
            # Release the stale worker only after the first distinct round is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the second provider-atomic merge result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require the second distinct action to publish without overwriting the first.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "PASS:1"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require both terminal rounds in commit order plus sibling preservation.
            self.assertEqual(([row["client_request_id"] for row in persisted["recent_rounds"]], persisted["atomic_markers"]), (["atomic-process-0", "atomic-process-1"], ["concurrent"]))
            # Verify shared helper wrappers never enter the frozen direct-row state shape.
            self.assertTrue(all("public" not in row and "request_id" not in row for row in persisted["recent_rounds"]))

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

    # Confirm the compatibility adapter retains the established 100-round direct-row history.
    def test_shared_helper_preserves_legacy_history_capacity_and_order(self):
        # Execute one more action than the published Big Six history bound.
        for index in range(101):
            # Use one losing wager so each round requires exactly one fake movement.
            self.service.spin("player-a", {"client_request_id": f"history-{index}", "wagers": {"one": 1}})
        # Read the frozen public state payload through the game-owned projection.
        state = self.service.state("player-a")
        # Require exactly the newest 100 direct rows in oldest-to-newest response order.
        self.assertEqual((100, "history-1", "history-100"), (len(state["recent_rounds"]), state["recent_rounds"][0]["client_request_id"], state["recent_rounds"][-1]["client_request_id"]))
        # Reject leakage of the shared helper's private wrapper representation.
        self.assertTrue(all("public" not in row and "request_id" not in row for row in state["recent_rounds"]))

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
