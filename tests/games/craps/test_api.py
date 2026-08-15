# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused session, reload, and retry-safety tests for issue #90 Craps."""

# Import deep-copy support so fake persistence matches document boundaries.
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
# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public conflict and validation errors asserted at route boundaries.
from casino.errors import ConflictError, ValidationError
# Import the current router so session replacement is exercised directly.
from casino.router import Router
# Import only the isolated game API and engine under test.
from casino.games.craps import api, engine


# Provide in-memory player state and ledger behavior without repository data files.
class FakeCasino:
    # Initialize two fake wallets while only the authenticated one may be touched.
    def __init__(self):
        # Store player-scoped game documents by resolved player id.
        self.states = {}
        # Store committed ledger events in chronological order.
        self.events = []
        # Store fake balances only inside this ledger adapter.
        self.balances = {"session-player": 100.0, "body-intruder": 500.0, "query-intruder": 500.0}
        # Store a deterministic ledger id counter.
        self.sequence = 0
        # Record state saves and ledger commits for crash-order assertions.
        self.timeline = []
        # Count injected credit failures used by terminal recovery tests.
        self.credit_failures_remaining = 0
        # Record requested ledger windows for unbounded recovery assertions.
        self.ledger_read_limits = []

    # Load a deep copy of one player-scoped state document.
    def load_state(self, game_id, player_id, factory):
        # Return persisted state or a fresh default without sharing references.
        return copy.deepcopy(self.states.get(player_id, factory()))

    # Apply one callback to provider-current state and publish its detached result.
    def update_state(self, game_id, player_id, mutator, factory):
        # Give the callback an isolated copy of the latest provider document.
        current = copy.deepcopy(self.states.get(player_id, factory()))
        # Apply the game transition before publishing any result.
        updated = mutator(current)
        # Persist a detached copy only after the callback returns successfully.
        self.states[player_id] = copy.deepcopy(updated)
        # Read active state or the newest private journal round for audit ordering.
        round_state = updated.get("active_round") or (updated.get("_round_journal") or updated.get("recent_rounds") or [None])[-1]
        # Record the persisted lifecycle markers before any later ledger operation.
        self.timeline.append({"kind": "save", "phase": round_state.get("phase") if round_state else None, "wager_status": round_state.get("wager_status") if round_state else None, "settlement_status": round_state.get("settlement_status") if round_state else None})
        # Return provider-authoritative state without sharing references.
        return copy.deepcopy(updated)

    # Seed a deep copy of one crash fixture before the service is rebuilt.
    def seed_state(self, player_id, state):
        # Persist fixture state under the router-resolved player only.
        self.states[player_id] = copy.deepcopy(state)
        # Read active state or the newest private journal round for audit ordering.
        round_state = state.get("active_round") or (state.get("_round_journal") or state.get("recent_rounds") or [None])[-1]
        # Record the persisted lifecycle markers before any later ledger operation.
        self.timeline.append({"kind": "save", "phase": round_state.get("phase") if round_state else None, "wager_status": round_state.get("wager_status") if round_state else None, "settlement_status": round_state.get("settlement_status") if round_state else None})

    # Create one fake signed ledger event and mutate balance only here.
    def transact(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Increment the deterministic event id counter.
        self.sequence += 1
        # Read the balance before applying the signed movement.
        before = self.balances[player_id]
        # Apply the movement at shared ledger precision.
        after = round(before + float(amount), 2)
        # Reject overdrafts because focused tests never expect them.
        if after < 0:
            # Surface unexpected test setup as an immediate assertion.
            raise AssertionError("fake ledger overdraft")
        # Store the balance after the only allowed fake mutation.
        self.balances[player_id] = after
        # Build the public ledger subset consumed by the service.
        event = {"ledger_id": f"led_{self.sequence}", "player_id": player_id, "amount": round(float(amount), 2), "transaction_type": transaction_type, "game": game, "round_id": round_id, "details": copy.deepcopy(details or {})}
        # Append the event for subsequent retry scans.
        self.events.append(event)
        # Record the committed movement after balance and event storage complete.
        self.timeline.append({"kind": "ledger", "transaction_type": transaction_type})
        # Return a detached event like a storage provider response.
        return copy.deepcopy(event)

    # Debit a positive wager through the fake signed ledger operation.
    def debit(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Delegate with one normalized negative signed amount.
        return self.transact(player_id, -abs(float(amount)), transaction_type, game, round_id, details)

    # Credit a positive payout or refund through the fake ledger operation.
    def credit(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Inject a failure before any credit movement when requested by a test.
        if self.credit_failures_remaining > 0:
            # Consume one configured failure so later retries may recover.
            self.credit_failures_remaining -= 1
            # Model storage failure without appending an event or moving balance.
            raise RuntimeError("injected credit failure")
        # Delegate with one normalized positive signed amount.
        return self.transact(player_id, abs(float(amount)), transaction_type, game, round_id, details)

    # Read recent events using the production chronological shape.
    def read_ledger(self, player_id=None, limit=100):
        # Record every requested recovery window before filtering rows.
        self.ledger_read_limits.append(limit)
        # Filter by player when requested and retain the newest bounded events.
        rows = [event for event in self.events if player_id is None or event["player_id"] == player_id][-limit:]
        # Return detached proof so service validation cannot mutate storage.
        return copy.deepcopy(rows)

    # Return a read-only player snapshot for API payloads.
    def get_player(self, player_id):
        # Expose only fields required by the additive game response.
        return {"player_id": player_id, "balance": self.balances[player_id]}


# Provide a queue-backed deterministic authoritative roller.
class DiceQueue:
    # Initialize an empty sequence, consumption counter, and shared audit timeline.
    def __init__(self, timeline):
        # Store queued ordered die pairs for future actions.
        self.values = []
        # Count actual roller calls so exact retries prove read-only.
        self.calls = 0
        # Store the fake casino timeline used for money-order assertions.
        self.timeline = timeline

    # Queue one or more ordered die pairs for later service calls.
    def add(self, *values):
        # Append detached list pairs in the supplied order.
        self.values.extend([list(value) for value in values])

    # Return the next deterministic pair when the service commits a new action.
    def __call__(self):
        # Fail clearly if a retry unexpectedly consumes another pair.
        if not self.values:
            # Surface missing test setup without generating fallback randomness.
            raise AssertionError("no deterministic dice remain")
        # Count only genuine new-action dice consumption.
        self.calls += 1
        # Record dice consumption between wager proof and terminal persistence.
        self.timeline.append({"kind": "dice"})
        # Remove and return the oldest queued pair.
        return self.values.pop(0)


# Verify the real router boundary, persisted state, and ledger recovery guards.
class CrapsApiTests(unittest.TestCase):
    # Build deterministic in-memory adapters before every test.
    def setUp(self):
        # Create fresh player, state, and ledger storage.
        self.fake = FakeCasino()
        # Create a fresh deterministic dice queue.
        self.dice = DiceQueue(self.fake.timeline)
        # Start deterministic round identifiers at zero.
        self.id_sequence = 0
        # Start deterministic audit timestamps at zero.
        self.clock_sequence = 0
        # Build the initial service and isolated router.
        self.rebuild_router()
        # Store the normal authenticated context used by current main.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Generate one unique deterministic round identifier.
    def next_id(self, prefix):
        # Increment the service-local test sequence.
        self.id_sequence += 1
        # Return an identifier compatible with the route regex.
        return f"{prefix}_round_{self.id_sequence}"

    # Generate one monotonically increasing deterministic timestamp.
    def now(self):
        # Increment the audit timestamp sequence.
        self.clock_sequence += 1
        # Return a stable ISO-shaped value for persisted assertions.
        return f"2026-07-14T00:00:{self.clock_sequence:02d}.000Z"

    # Recreate service and router while retaining fake persisted storage.
    def rebuild_router(self):
        # Inject every state, money, player, clock, id, and dice dependency.
        self.service = api.CrapsService(load_state=self.fake.load_state, update_state_callback=self.fake.update_state, debit=self.fake.debit, credit=self.fake.credit, read_ledger=self.fake.read_ledger, get_player=self.fake.get_player, clock=self.now, id_factory=self.next_id, roller=self.dice)
        # Create an isolated router without shared catalog registration.
        self.router = Router()
        # Register only Craps routes through the public package adapter.
        api.register(self.router, service=self.service)

    # Dispatch one game request through the real session-replacing router.
    def call(self, path, body=None, method="POST"):
        # Delegate with a fresh context copy so requests cannot leak mutation.
        return self.router.dispatch(method, path, body or {}, context=dict(self.context))

    # Count committed events by their transaction type.
    def events_of_type(self, transaction_type):
        # Return every event matching the requested stable type.
        return [event for event in self.fake.events if event["transaction_type"] == transaction_type]

    # Confirm identical publication is idempotent and preserves provider siblings.
    def test_atomic_publication_accepts_same_result_without_persisting_baseline(self):
        # Load one tracked empty document through the service boundary.
        state = self.service._load("session-player")
        # Prepare one deterministic pending round without moving the wallet.
        state["active_round"] = engine.create_round("session-player", "pass_line", 1, "atomic-same-start", round_id="craps_atomic_same", created_at=self.now())
        # Publish the prepared round through provider-current comparison.
        self.service._save("session-player", state)
        # Add unrelated metadata after the first game-owned publication.
        self.fake.states["session-player"]["atomic_markers"] = ["sibling"]
        # Publish the exact same game result again from the advanced baseline.
        self.service._save("session-player", state)
        # Verify the sibling survives and the private comparison key never persists.
        self.assertEqual(["sibling"], self.fake.states["session-player"]["atomic_markers"])
        # Reject operation metadata from provider-authoritative state.
        self.assertNotIn(api._ATOMIC_BASELINE_KEY, self.fake.states["session-player"])

    # Confirm action-owned rollback preserves provider-current sibling metadata.
    def test_failed_wager_rollback_preserves_concurrent_sibling(self):
        # Publish one unrelated sibling during the debit boundary before failing.
        def fail_debit(*_args, **_kwargs):
            # Append a sibling through the same provider-current callback contract.
            self.fake.update_state(engine.GAME_ID, "session-player", lambda current: {**current, "atomic_markers": ["concurrent"]}, engine.default_state)
            # Fail before any fake ledger event can move the wallet.
            raise RuntimeError("injected pre-ledger wager failure")

        # Rebuild the service with the bounded failing debit seam.
        self.service = api.CrapsService(load_state=self.fake.load_state, update_state_callback=self.fake.update_state, debit=fail_debit, credit=self.fake.credit, read_ledger=self.fake.read_ledger, get_player=self.fake.get_player, clock=self.now, id_factory=self.next_id, roller=self.dice)
        # Register the replacement service on a fresh isolated router.
        self.router = Router()
        # Expose only the Craps routes used by the focused request.
        api.register(self.router, service=self.service)
        # Surface the injected pre-ledger failure after bounded rollback.
        with self.assertRaisesRegex(RuntimeError, "pre-ledger wager failure"):
            # Attempt one money-bearing start whose prepared round must be removed.
            self.call("/api/v1/games/craps/rounds", {"request_id": "atomic-rollback-start", "bet_type": "pass_line", "wager": 2})
        # Read the provider-authoritative document after rollback.
        persisted = self.fake.states["session-player"]
        # Verify only the action-owned round was removed and the sibling survived.
        self.assertEqual((None, [], ["concurrent"]), (persisted["active_round"], persisted["_round_journal"], persisted["atomic_markers"]))
        # Verify failure occurred before any append-only wallet event.
        self.assertEqual([], self.fake.events)
        # Verify the private optimistic baseline never entered provider bytes.
        self.assertNotIn(api._ATOMIC_BASELINE_KEY, persisted)

    # Prove stale fresh processes preserve siblings and debit only one prepared round.
    def test_fresh_process_start_race_has_one_winner_and_zero_loser_ledger_calls(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "session-player.json"
            # Create the state directory before seeding one empty table.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps(engine.default_state(), sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind all child persistence to the disposable root and exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one service worker whose load pauses after capturing stale state.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError
from casino.games.craps import api, engine
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
request_id = sys.argv[3]
def load_state(game_id, player_id, factory):
    state = load_player_game_state(game_id, player_id, factory)
    ready.write_text('ready', encoding='utf-8')
    deadline = time.monotonic() + 10
    while not release.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not release.exists():
        raise RuntimeError('Craps race release timed out')
    return state
def update_state(game_id, player_id, mutator, factory):
    return update_player_game_state(game_id, player_id, mutator, factory)
calls = []
def debit(player_id, amount, transaction_type, game, round_id, details):
    calls.append(details['idempotency_key'])
    return {'ledger_id': 'ledger-' + str(len(calls)), 'player_id': player_id, 'amount': -abs(float(amount)), 'transaction_type': transaction_type, 'game': game, 'round_id': round_id, 'details': dict(details)}
game = api.CrapsService(load_state=load_state, update_state_callback=update_state, debit=debit, credit=lambda *_args, **_kwargs: None, read_ledger=lambda *_args, **_kwargs: [], get_player=lambda player_id: {'player_id': player_id, 'balance': 100.0}, clock=lambda: '2026-08-15T00:02:00Z', id_factory=lambda prefix: prefix + '_' + request_id, roller=lambda: [3, 4])
try:
    game.start_round('session-player', {'request_id': request_id, 'bet_type': 'pass_line', 'wager': 1})
    print('PASS:' + str(len(calls)))
except ConflictError:
    print('CONFLICT:' + str(len(calls)))
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.craps import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('craps', 'session-player', add, engine.default_state)\n"
            # Commit the sibling after both workers captured their stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish and debit the winning round.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require one and only one debit-shaped call from the provider winner.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:1"), winner_error)
            # Release the stale second worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require conflict before the losing process attempts any ledger call.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT:0"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one winner, sibling preservation, and no stale-round overwrite.
            self.assertEqual((persisted["active_round"]["start_request_id"], persisted["active_round"]["wager_status"], persisted["atomic_markers"]), ("atomic-process-0", "complete", ["concurrent"]))
            # Verify the private optimistic baseline never enters persisted bytes.
            self.assertNotIn(api._ATOMIC_BASELINE_KEY, persisted)

    # Confirm hostile player ids lose to the session and start retries debit once.
    def test_session_binding_start_replay_and_conflict(self):
        # Start through hostile query and body identities to exercise both replacements.
        first = self.call("/api/v1/games/craps/rounds?player_id=query-intruder", {"player_id": "body-intruder", "request_id": "start-safe-1", "bet_type": "pass_line", "wager": 5})
        # Verify the created round belongs only to the authenticated player.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify no hostile identity received a persisted game document.
        self.assertEqual(["session-player"], list(self.fake.states))
        # Verify neither hostile wallet changed.
        self.assertEqual(500.0, self.fake.balances["body-intruder"])
        # Verify the session wallet paid one five-token wager.
        self.assertEqual(95.0, self.fake.balances["session-player"])
        # Locate the first pending-state save in the operation timeline.
        pending_save_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("kind") == "save" and item.get("wager_status") == "pending")
        # Locate the one committed wager movement in the operation timeline.
        wager_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("transaction_type") == "CRAPS_WAGER_DEBIT")
        # Verify pending round state was durable before the wager debit began.
        self.assertLess(pending_save_index, wager_index)
        # Read the persisted active round to simulate a lost post-debit marker.
        persisted = self.fake.states["session-player"]["active_round"]
        # Reset the marker as if the ledger committed before state confirmation.
        persisted["wager_status"] = "pending"
        # Remove the cached ledger id so recovery must scan persisted events.
        persisted.pop("wager_ledger_id", None)
        # Remove private proof to model a crash before the completion save.
        persisted.pop("_wager_event", None)
        # Replay the exact request with the same hostile caller id.
        second = self.call("/api/v1/games/craps/rounds", {"player_id": "body-intruder", "request_id": "start-safe-1", "bet_type": "pass_line", "wager": 5})
        # Verify the service explicitly reports the retained action replay.
        self.assertTrue(second["replayed"])
        # Verify replay returns the same stable server round.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify recovery leaves exactly one wager debit.
        self.assertEqual(1, len(self.events_of_type("CRAPS_WAGER_DEBIT")))
        # Verify the deterministic wager key is stored with ledger evidence.
        self.assertEqual(f"{first['round']['round_id']}:wager", first["wager_event"]["details"]["idempotency_key"])
        # Reject reuse of one start id with changed money settings.
        with self.assertRaises(ConflictError):
            # Attempt a conflicting six-token replay.
            self.call("/api/v1/games/craps/rounds", {"request_id": "start-safe-1", "bet_type": "pass_line", "wager": 6})
        # Reject malformed retry identifiers before any new action.
        with self.assertRaises(ValidationError):
            # Attempt a request id containing a forbidden space.
            self.call("/api/v1/games/craps/rounds", {"request_id": "bad id", "bet_type": "pass_line", "wager": 5})

    # Confirm pending-state-only restart recovery debits before dice or payout.
    def test_pending_round_restart_recovers_wager_before_roll(self):
        # Build one state document representing a crash before the wager debit.
        state = engine.default_state()
        # Create the exact pending round that a start request persisted first.
        pending_round = engine.create_round("session-player", "pass_line", 1, "start-pending-restart", round_id="craps_pending_restart", created_at=self.now())
        # Install the pending round in the player's actionable slot.
        state["active_round"] = pending_round
        # Persist pending state without creating any ledger movement.
        self.fake.seed_state("session-player", state)
        # Queue a natural seven that would pay only after wager recovery.
        self.dice.add((3, 4))
        # Recreate service and router to model a fresh process reading the pending file.
        self.rebuild_router()
        # Roll through the restored round without replaying the original start call.
        result = self.call("/api/v1/games/craps/rounds/craps_pending_restart/rolls", {"request_id": "roll-after-pending-restart"})
        # Verify one wager debit committed before the winning settlement.
        self.assertEqual(["CRAPS_WAGER_DEBIT", "CRAPS_PAYOUT_CREDIT"], [event["transaction_type"] for event in self.fake.events])
        # Locate the original pending state save in the operation timeline.
        pending_save_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("kind") == "save" and item.get("wager_status") == "pending")
        # Locate the recovered wager debit in the operation timeline.
        debit_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("transaction_type") == "CRAPS_WAGER_DEBIT")
        # Locate the first and only authoritative dice consumption.
        dice_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("kind") == "dice")
        # Locate durable terminal state before returned credit.
        terminal_save_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("kind") == "save" and item.get("phase") == "settled" and item.get("settlement_status") == "pending")
        # Locate the returned winning credit in the operation timeline.
        payout_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("transaction_type") == "CRAPS_PAYOUT_CREDIT")
        # Verify pending state preceded debit, dice, terminal save, and payout in order.
        self.assertTrue(pending_save_index < debit_index < dice_index < terminal_save_index < payout_index)
        # Verify wager recovery prevents a free payout and produces the expected net win.
        self.assertEqual(101.0, result["player"]["balance"])
        # Replay the exact roll action after terminal archival.
        replay = self.call("/api/v1/games/craps/rounds/craps_pending_restart/rolls", {"request_id": "roll-after-pending-restart"})
        # Verify replay returns retained dice without another debit or payout.
        self.assertTrue(replay["replayed"])
        # Verify exact replay keeps one debit, one payout, and one roller call.
        self.assertEqual((1, 1, 1), (len(self.events_of_type("CRAPS_WAGER_DEBIT")), len(self.events_of_type("CRAPS_PAYOUT_CREDIT")), self.dice.calls))

    # Confirm point state survives service reload and payout recovery remains once-only.
    def test_reload_safe_point_and_terminal_roll_replay(self):
        # Queue point eight followed by an eight hit.
        self.dice.add((4, 4), (3, 5))
        # Start one five-token Pass Line round.
        started = self.call("/api/v1/games/craps/rounds", {"request_id": "start-point", "bet_type": "pass_line", "wager": 5})
        # Store the stable round id used by both roll actions.
        round_id = started["round"]["round_id"]
        # Establish point eight through the first public roll action.
        point = self.call(f"/api/v1/games/craps/rounds/{round_id}/rolls?player_id=query-intruder", {"player_id": "body-intruder", "request_id": "roll-point-1"})
        # Verify the point action remains active and unresolved.
        self.assertEqual("point", point["round"]["phase"])
        # Verify the exact authoritative dice are returned.
        self.assertEqual([4, 4], point["roll"]["dice"])
        # Recreate the service and router against the same fake persisted state.
        self.rebuild_router()
        # Read state through a fresh service instance to simulate reload.
        reloaded = self.call("/api/v1/games/craps/state", method="GET")
        # Verify the active point survives service reconstruction.
        self.assertEqual(8, reloaded["state"]["active_round"]["point"])
        # Hit point eight and settle the line wager.
        settled = self.call(f"/api/v1/games/craps/rounds/{round_id}/rolls", {"request_id": "roll-point-2"})
        # Verify the terminal result is a Pass Line win.
        self.assertEqual("win", settled["round"]["outcome"])
        # Verify one payout returns stake plus equal winnings.
        self.assertEqual(10.0, settled["settlement"]["amount"])
        # Locate terminal pending state saved before the returned credit.
        pending_settlement_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("kind") == "save" and item.get("phase") == "settled" and item.get("settlement_status") == "pending")
        # Locate the committed payout movement in the operation timeline.
        payout_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("transaction_type") == "CRAPS_PAYOUT_CREDIT")
        # Verify terminal dice and outcome were durable before payout credit.
        self.assertLess(pending_settlement_index, payout_index)
        # Read the retained terminal round for a lost-marker simulation.
        retained = self.fake.states["session-player"]["_round_journal"][-1]
        # Reset settlement state as if credit committed before marker persistence.
        retained["settlement_status"] = "pending"
        # Remove the cached id so recovery must scan by action key.
        retained.pop("settlement_ledger_id", None)
        # Remove private proof to model a crash before the completion save.
        retained.pop("_settlement_event", None)
        # Recreate service state once more before the retry.
        self.rebuild_router()
        # Replay the exact terminal roll action after the simulated reload.
        replay = self.call(f"/api/v1/games/craps/rounds/{round_id}/rolls", {"request_id": "roll-point-2"})
        # Verify the API distinguishes the retained action replay.
        self.assertTrue(replay["replayed"])
        # Verify exact replay never consumes a third dice pair.
        self.assertEqual(2, self.dice.calls)
        # Verify exactly one payout exists after recovery.
        self.assertEqual(1, len(self.events_of_type("CRAPS_PAYOUT_CREDIT")))
        # Verify the deterministic settlement key is stored with credit proof.
        self.assertEqual(f"{round_id}:settlement", replay["settlement"]["details"]["idempotency_key"])
        # Verify the final wallet equals start minus five plus ten.
        self.assertEqual(105.0, self.fake.balances["session-player"])
        # Verify terminal state is archived and no active round remains.
        self.assertIsNone(replay["state"]["active_round"])

    # Confirm a new start cannot bypass a retained pending terminal settlement.
    def test_new_start_recovers_pending_terminal_settlement_or_fails_closed(self):
        # Queue one natural seven for the first round's terminal result.
        self.dice.add((3, 4))
        # Configure both the original payout attempt and first recovery to fail.
        self.fake.credit_failures_remaining = 2
        # Start one five-token Pass Line round normally.
        started = self.call("/api/v1/games/craps/rounds", {"request_id": "start-pending-settlement", "bet_type": "pass_line", "wager": 5})
        # Attempt the terminal roll and preserve its pending state on credit failure.
        with self.assertRaises(RuntimeError):
            # Roll a natural seven whose first payout attempt is injected to fail.
            self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-pending-settlement"})
        # Recreate the service to model losing the browser's in-memory action response.
        self.rebuild_router()
        # Read reload state without triggering payout recovery on GET.
        reloaded = self.call("/api/v1/games/craps/state", method="GET")
        # Verify GET exposes the retained pending settlement for frontend replay.
        self.assertEqual("pending", reloaded["state"]["recent_rounds"][-1]["settlement_status"])
        # Verify read-only reload consumed neither the remaining failure nor a credit.
        self.assertEqual((1, 0), (self.fake.credit_failures_remaining, len(self.events_of_type("CRAPS_PAYOUT_CREDIT"))))
        # Reject a new wager while terminal recovery still fails.
        with self.assertRaises(RuntimeError):
            # Attempt a new round whose preflight settlement recovery fails closed.
            self.call("/api/v1/games/craps/rounds", {"request_id": "start-after-pending", "bet_type": "pass_line", "wager": 2})
        # Verify the failed preflight added no second wager debit.
        self.assertEqual(1, len(self.events_of_type("CRAPS_WAGER_DEBIT")))
        # Verify no new active round was created before recovery succeeded.
        self.assertIsNone(self.fake.states["session-player"]["active_round"])
        # Retry the same valid new start after injected failures are exhausted.
        recovered = self.call("/api/v1/games/craps/rounds", {"request_id": "start-after-pending", "bet_type": "pass_line", "wager": 2})
        # Verify the old settlement completed before the new wager became active.
        self.assertEqual("complete", recovered["state"]["recent_rounds"][-1]["settlement_status"])
        # Verify recovery then new debit produces the expected ledger sequence.
        self.assertEqual(["CRAPS_WAGER_DEBIT", "CRAPS_PAYOUT_CREDIT", "CRAPS_WAGER_DEBIT"], [event["transaction_type"] for event in self.fake.events])
        # Locate the recovered payout in the operation timeline.
        payout_index = next(index for index, item in enumerate(self.fake.timeline) if item.get("transaction_type") == "CRAPS_PAYOUT_CREDIT")
        # Locate both old and new wager debits in timeline order.
        debit_indexes = [index for index, item in enumerate(self.fake.timeline) if item.get("transaction_type") == "CRAPS_WAGER_DEBIT"]
        # Verify old settlement credit committed before the second wager debit.
        self.assertLess(payout_index, debit_indexes[1])
        # Verify old net win plus the new two-token wager yields 103 tokens.
        self.assertEqual(103.0, recovered["player"]["balance"])
        # Verify settlement recovery did not consume any additional dice.
        self.assertEqual(1, self.dice.calls)

    # Confirm Don't Pass twelve refunds once while a Pass craps loss credits nothing.
    def test_dont_pass_twelve_refund_and_loss(self):
        # Queue twelve for the push followed by two for the later Pass loss.
        self.dice.add((6, 6), (1, 1))
        # Start a seven-token Don't Pass round.
        started = self.call("/api/v1/games/craps/rounds", {"request_id": "start-push", "bet_type": "dont_pass", "wager": 7})
        # Roll twelve to trigger the bar-twelve push refund.
        pushed = self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-push"})
        # Verify the public terminal outcome is a push.
        self.assertEqual("push", pushed["round"]["outcome"])
        # Verify the returned event uses the explicit refund type.
        self.assertEqual("CRAPS_PUSH_REFUND", pushed["settlement"]["transaction_type"])
        # Verify the refund returns exactly the original wager.
        self.assertEqual(7.0, pushed["settlement"]["amount"])
        # Replay the exact push action without another credit.
        replay = self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-push"})
        # Verify the push replay is explicitly identified.
        self.assertTrue(replay["replayed"])
        # Verify one and only one push refund exists.
        self.assertEqual(1, len(self.events_of_type("CRAPS_PUSH_REFUND")))
        # Verify debit plus refund restores the starting wallet.
        self.assertEqual(100.0, self.fake.balances["session-player"])
        # Start a later two-token Pass Line round after archival.
        losing_start = self.call("/api/v1/games/craps/rounds", {"request_id": "start-loss", "bet_type": "pass_line", "wager": 2})
        # Roll two for an immediate Pass Line loss.
        lost = self.call(f"/api/v1/games/craps/rounds/{losing_start['round']['round_id']}/rolls", {"request_id": "roll-loss"})
        # Verify losses return no settlement ledger event.
        self.assertIsNone(lost["settlement"])
        # Verify loss state is terminal and fully marked without zero credit.
        self.assertEqual("complete", lost["round"]["settlement_status"])
        # Verify only the later wager remains deducted.
        self.assertEqual(98.0, self.fake.balances["session-player"])

    # Confirm retry ids cannot move between start actions or different rounds.
    def test_action_request_ids_fail_closed_across_actions(self):
        # Queue one natural seven used only by the first valid roll.
        self.dice.add((3, 4))
        # Start the first one-token Pass Line round.
        first = self.call("/api/v1/games/craps/rounds", {"request_id": "shared-start-id", "bet_type": "pass_line", "wager": 1})
        # Reject reuse of the start id as a roll action.
        with self.assertRaises(ConflictError):
            # Attempt to roll with the money-bearing start request id.
            self.call(f"/api/v1/games/craps/rounds/{first['round']['round_id']}/rolls", {"request_id": "shared-start-id"})
        # Complete the first round with a distinct action id.
        self.call(f"/api/v1/games/craps/rounds/{first['round']['round_id']}/rolls", {"request_id": "shared-roll-id"})
        # Start a second round after the first is archived.
        second = self.call("/api/v1/games/craps/rounds", {"request_id": "second-start-id", "bet_type": "pass_line", "wager": 1})
        # Reject reuse of the earlier round's roll id on the new path.
        with self.assertRaises(ConflictError):
            # Attempt the cross-round action-id replay without queued dice.
            self.call(f"/api/v1/games/craps/rounds/{second['round']['round_id']}/rolls", {"request_id": "shared-roll-id"})
        # Verify only the one valid roll consumed authoritative dice.
        self.assertEqual(1, self.dice.calls)

    # Confirm transaction-type drift cannot evade the settlement action key.
    def test_settlement_action_key_rejects_type_drift(self):
        # Queue one natural seven for an immediate Pass payout.
        self.dice.add((3, 4))
        # Start one three-token Pass Line round.
        started = self.call("/api/v1/games/craps/rounds", {"request_id": "start-drift", "bet_type": "pass_line", "wager": 3})
        # Settle the round with one valid payout event.
        self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-drift"})
        # Locate the committed settlement proof by deterministic action key.
        settlement = next(event for event in self.fake.events if event["details"].get("idempotency_key", "").endswith(":settlement"))
        # Corrupt only its transaction type to model type drift under the same key.
        settlement["transaction_type"] = "CRAPS_PUSH_REFUND"
        # Reset retained state so replay must validate the corrupted proof.
        retained = self.fake.states["session-player"]["_round_journal"][-1]
        # Mark settlement pending to mirror interrupted marker persistence.
        retained["settlement_status"] = "pending"
        # Remove the cached id so the action-key scan is mandatory.
        retained.pop("settlement_ledger_id", None)
        # Remove private proof so recovery validates the drifted provider event.
        retained.pop("_settlement_event", None)
        # Record event count before the conflicting retry.
        event_count = len(self.fake.events)
        # Reject the drifted proof instead of issuing a second settlement type.
        with self.assertRaises(ConflictError):
            # Replay the exact terminal action against corrupted type evidence.
            self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-drift"})
        # Verify fail-closed recovery appended no second ledger event.
        self.assertEqual(event_count, len(self.fake.events))

    # Confirm pending proof recovery widens beyond five hundred later events.
    def test_pending_recovery_has_no_fixed_ledger_horizon(self):
        # Queue one natural seven for a completed wager and payout pair.
        self.dice.add((3, 4))
        # Start a two-token Pass Line round.
        started = self.call("/api/v1/games/craps/rounds", {"request_id": "start-old-proof", "bet_type": "pass_line", "wager": 2})
        # Settle the round so both wager and payout proof initially exist.
        terminal = self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-old-proof"})
        # Read the canonical private journal round for crash-marker simulation.
        retained = self.fake.states["session-player"]["_round_journal"][-1]
        # Mark the wager pending as if its completion save was lost.
        retained["wager_status"] = "pending"
        # Remove the wager id cached by the lost completion save.
        retained.pop("wager_ledger_id", None)
        # Remove private wager proof so provider history recovery is required.
        retained.pop("_wager_event", None)
        # Mark settlement pending as if its completion save was also lost.
        retained["settlement_status"] = "pending"
        # Remove the settlement id cached by the lost completion save.
        retained.pop("settlement_ledger_id", None)
        # Remove private settlement proof so provider history recovery is required.
        retained.pop("_settlement_event", None)
        # Append six hundred same-player cross-game events after both old proofs.
        for index in range(600):
            # Alternate credit and debit noise so the wallet returns to its prior value.
            amount = 1 if index % 2 == 0 else -1
            # Use a distinct non-Craps transaction type for every direction.
            transaction_type = "NOISE_CREDIT" if amount > 0 else "NOISE_DEBIT"
            # Commit realistic later ledger traffic owned by another game.
            self.fake.transact("session-player", amount, transaction_type, "other_game", f"noise-{index}", {"idempotency_key": f"noise-{index}"})
        # Clear ordinary pre-noise read telemetry before the horizon recovery.
        self.fake.ledger_read_limits.clear()
        # Record total ledger rows before any exact retry.
        event_count = len(self.fake.events)
        # Replay the original start so settlement and wager proof both recover.
        start_replay = self.call("/api/v1/games/craps/rounds", {"request_id": "start-old-proof", "bet_type": "pass_line", "wager": 2})
        # Verify the retained first round remains the start action owner.
        self.assertEqual(started["round"]["round_id"], start_replay["round"]["round_id"])
        # Verify widening reached beyond the obsolete five-hundred-row window.
        self.assertGreaterEqual(max(self.fake.ledger_read_limits), 1000)
        # Record completed-proof read calls after durable caches are restored.
        completed_read_count = len(self.fake.ledger_read_limits)
        # Replay the completed start again through its private cached proof.
        second_start_replay = self.call("/api/v1/games/craps/rounds", {"request_id": "start-old-proof", "bet_type": "pass_line", "wager": 2})
        # Replay the terminal roll again through its private cached proof.
        roll_replay = self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": "roll-old-proof"})
        # Verify both completed actions remain explicit replays.
        self.assertTrue(second_start_replay["replayed"] and roll_replay["replayed"])
        # Verify completed cached proof performs no further ledger-history reads.
        self.assertEqual(completed_read_count, len(self.fake.ledger_read_limits))
        # Verify no debit, payout, or noise row was duplicated by any retry.
        self.assertEqual(event_count, len(self.fake.events))
        # Verify exactly one Craps debit and one Craps payout remain.
        self.assertEqual((1, 1), (len(self.events_of_type("CRAPS_WAGER_DEBIT")), len(self.events_of_type("CRAPS_PAYOUT_CREDIT"))))
        # Verify no retry consumed another authoritative dice pair.
        self.assertEqual(1, self.dice.calls)
        # Verify private cached proof is absent from the public round response.
        self.assertNotIn("_settlement_event", roll_replay["round"])
        # Verify the exact terminal roll remains unchanged after horizon recovery.
        self.assertEqual(terminal["roll"], roll_replay["roll"])

    # Confirm action ownership survives beyond the twenty-round public history slice.
    def test_private_action_journal_outlives_public_recent_history(self):
        # Queue one natural seven for each of twenty-two completed rounds.
        for _ in range(22):
            # Append one deterministic terminal pair per future roll action.
            self.dice.add((3, 4))
        # Initialize retained evidence for the first round and roll.
        first_started = None
        # Initialize retained terminal evidence for the first roll action.
        first_terminal = None
        # Complete twenty-two independent rounds to cross the public horizon.
        for index in range(22):
            # Start one cent-exact one-token Pass Line wager.
            started = self.call("/api/v1/games/craps/rounds", {"request_id": f"journal-start-{index}", "bet_type": "pass_line", "wager": 1})
            # Settle the round immediately with its queued natural seven.
            terminal = self.call(f"/api/v1/games/craps/rounds/{started['round']['round_id']}/rolls", {"request_id": f"journal-roll-{index}"})
            # Preserve the first action pair before later rounds leave public history.
            if index == 0:
                # Retain the first start response for exact identity comparison.
                first_started = started
                # Retain the first terminal response for exact roll comparison.
                first_terminal = terminal
        # Read the public state projection after twenty-two settlements.
        public = self.call("/api/v1/games/craps/state", method="GET")
        # Verify public recent history remains bounded to twenty rounds.
        self.assertEqual(20, len(public["state"]["recent_rounds"]))
        # Verify the earliest round has fallen outside the public projection.
        self.assertNotIn(first_started["round"]["round_id"], [item["round_id"] for item in public["state"]["recent_rounds"]])
        # Verify the private durable journal still owns all twenty-two rounds.
        self.assertEqual(22, len(self.fake.states["session-player"]["_round_journal"]))
        # Record money, dice, and ledger-read counts before old-action replay.
        before = (len(self.fake.events), self.dice.calls, len(self.fake.ledger_read_limits))
        # Replay the first start after it has aged out of public history.
        start_replay = self.call("/api/v1/games/craps/rounds", {"request_id": "journal-start-0", "bet_type": "pass_line", "wager": 1})
        # Replay the first terminal roll after it has aged out of public history.
        roll_replay = self.call(f"/api/v1/games/craps/rounds/{first_started['round']['round_id']}/rolls", {"request_id": "journal-roll-0"})
        # Verify both private-journal lookups are exact retained replays.
        self.assertTrue(start_replay["replayed"] and roll_replay["replayed"])
        # Verify the original server round id still owns both actions.
        self.assertEqual(first_started["round"]["round_id"], roll_replay["round"]["round_id"])
        # Verify the exact original roll record is returned unchanged.
        self.assertEqual(first_terminal["roll"], roll_replay["roll"])
        # Verify replay adds no event, dice consumption, or ledger scan.
        self.assertEqual(before, (len(self.fake.events), self.dice.calls, len(self.fake.ledger_read_limits)))
        # Verify private journal metadata never appears in public state.
        self.assertNotIn("_round_journal", roll_replay["state"])
        # Verify private event caches never appear in public round state.
        self.assertNotIn("_wager_event", roll_replay["round"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
