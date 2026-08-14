# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Replay, ledger, and session-bound Casino War controller tests."""

# Import deep-copy support to simulate persistence boundaries.
import copy
# Import JSON serialization for the cross-process persisted-state fixture.
import json
# Import environment access for isolated child-process storage selection.
import os
# Import paths for isolated state and rendezvous files.
from pathlib import Path
# Import subprocess execution for a real two-process state race.
import subprocess
# Import the current Python executable for byte-identical child workers.
import sys
# Import temporary-directory ownership for disposable race evidence.
import tempfile
# Import bounded polling for the process rendezvous.
import time
# Import unittest for dependency-free focused tests.
import unittest

# Import the router so routes can be exercised without global registration.
from casino.router import Router
# Import the isolated API and pure state factory.
from casino.games.casino_war import api, engine


# Simulate player-scoped persistence without touching repository data files.
class MemoryRepository:
    # Seed one player's document with deterministic state.
    def __init__(self, player_id: str, state: dict):
        # Store a detached copy to model serialization.
        self.documents = {player_id: copy.deepcopy(state)}

    # Load one detached player document.
    def load(self, player_id: str) -> dict:
        # Return a fresh default only for unexpected test players.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id: str, state: dict) -> None:
        # Persist a copy so later mutations require another explicit save.
        self.documents[player_id] = copy.deepcopy(state)

    # Apply one latest-state mutation through the in-memory provider seam.
    def update(self, player_id: str, mutator) -> dict:
        # Copy the committed document so a failing callback cannot mutate stored state.
        working = self.load(player_id)
        # Apply the complete state transition before publishing it.
        updated = mutator(working)
        # Persist through the same detached-copy boundary as ordinary saves.
        self.save(player_id, updated)
        # Return a detached committed result to the controller.
        return self.load(player_id)


# Record append-only events and expose game action lookup for crash recovery.
class RecordingLedger:
    # Start with no committed events.
    def __init__(self):
        # Retain committed events in append order.
        self.events = []

    # Find one prior action exactly as the production adapter does.
    def find_action(self, player_id: str, action_id: str):
        # Search newest-first for the player's matching details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"]["casino_war_action_id"] == action_id), None)

    # Record one debit or credit as a ledger-shaped event.
    def transact(self, intent: dict) -> dict:
        # Build a stable event identifier from append order.
        event = {
            "ledger_id": f"ledger-{len(self.events) + 1}",  # Identify the event.
            "player_id": intent["player_id"],  # Preserve player ownership.
            "game": intent["game"],  # Preserve game ownership.
            "round_id": intent["round_id"],  # Preserve round ownership.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "amount": -intent["amount"] if intent["direction"] == "debit" else intent["amount"],  # Record signed amount.
            "details": copy.deepcopy(intent["details"]),  # Preserve the idempotency detail.
        }
        # Append once to simulate the shared append-only ledger.
        self.events.append(event)
        # Return the committed event to the controller.
        return copy.deepcopy(event)


# Verify exactly-once replay and session resolver compatibility.
class CasinoWarApiTests(unittest.TestCase):
    # Build deterministic state where the player wins immediately.
    def winning_state(self) -> dict:
        # Start from the production state shape.
        state = engine.default_state()
        # Arrange player ace, dealer deuce, and sufficient remaining cards.
        state["shoe"] = list(reversed(["AH", "2S", "3C", "4C", "5C", "6C", "7C"]))
        # Identify the fixture shoe.
        state["shoe_id"] = "fixture-win"
        # Return the prepared state.
        return state

    # Build deterministic state where the initial cards tie.
    def tied_state(self) -> dict:
        # Start from the production state shape.
        state = engine.default_state()
        # Arrange initial sevens, burns, and a player-winning war comparison.
        state["shoe"] = list(reversed(["7H", "7S", "2D", "3D", "4D", "KH", "9S"]))
        # Identify the fixture shoe.
        state["shoe_id"] = "fixture-tie"
        # Return the prepared state.
        return state

    # Create one controller with recording ports.
    def controller(self, repository, recording_ledger):
        # Return a controller whose player payload is deterministic.
        return api.CasinoWarController(repository, recording_ledger, lambda player_id: {"player_id": player_id, "balance": 1000.0})

    # Confirm retrying the same command never repeats debit or settlement credit.
    def test_start_round_replay_is_exactly_once(self):
        # Seed one player with a winning deterministic round.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Record all wallet movements.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Execute the original command.
        first = controller.start_round("bound-player", 25, "action-start-101")
        # Replay the exact client command.
        second = controller.start_round("bound-player", 25, "action-start-101")
        # Assert one ante debit and one settlement credit total.
        self.assertEqual([event["amount"] for event in recording_ledger.events], [-25.0, 50.0])
        # Assert both responses identify the same logical round.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Require both the original and replay response to use the refreshed terminal state object.
        self.assertEqual((first["round"]["phase"], second["round"]["phase"]), ("settled", "settled"))

    # Confirm a crash after ledger commit but before marker save is recovered by scan.
    def test_reload_recovers_committed_events_without_duplicates(self):
        # Seed and execute one immediate win.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Record the committed events.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Commit the ante and settlement once.
        controller.start_round("bound-player", 25, "action-start-102")
        # Simulate state-marker loss after both append-only events committed.
        repository.documents["bound-player"]["ledger_actions"] = {}
        # Trigger reload recovery through the state endpoint behavior.
        payload = controller.state("bound-player")
        # Assert recovery reused the two existing events.
        self.assertEqual(len(recording_ledger.events), 2)
        # Assert state markers were reconstructed and settlement remains complete.
        self.assertEqual(payload["state"]["rounds"][0]["settlement"]["committed_actions"], 2)

    # Confirm two processes cannot lose a committed marker or terminal phase transition.
    def test_atomic_reconciliation_preserves_concurrent_process_updates(self):
        # Own every child-process state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary_root:
            # Resolve the isolated state root selected by both fresh Python processes.
            data_root = Path(temporary_root) / "data"
            # Resolve the exact Casino War player document path used by the JSON provider.
            state_path = data_root / "games" / "casino_war" / "atomic-player.json"
            # Create the parent before seeding the shared stale snapshot.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Start from the production document shape.
            seeded_state = engine.default_state()
            # Add the minimal pending round consumed by terminal reconciliation.
            seeded_state["rounds"] = {"round-atomic": {"round_id": "round-atomic", "phase": "ledger_pending", "settlement": {"intents": []}}}
            # Retain the same round in deterministic public-history order.
            seeded_state["round_order"] = ["round-atomic"]
            # Publish one deterministic state that both workers load before release.
            state_path.write_text(json.dumps(seeded_state), encoding="utf-8")
            # Resolve this repository root for explicit child import binding.
            repository_root = Path(__file__).resolve().parents[4]
            # Inherit the caller environment before replacing runtime-owned directories.
            environment = os.environ.copy()
            # Select the disposable JSON state root in each fresh interpreter.
            environment["CASINO_DATA_DIR"] = str(data_root)
            # Keep child logs inside the same disposable owner boundary.
            environment["CASINO_LOG_DIR"] = str(Path(temporary_root) / "logs")
            # Require the JSON provider so the operating-system document lock is exercised.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Bind imports to this exact worktree even when the parent has another active checkout.
            environment["PYTHONPATH"] = str(repository_root)
            # Define one dependency-free worker that loads stale state before the shared release file exists.
            worker_source = """
import sys
import time
from pathlib import Path
from casino.games.casino_war import api
repository = api.StateRepository()
state = repository.load('atomic-player')
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('atomic race release timed out')
controller = api.CasinoWarController(repository, None, lambda player_id: {'player_id': player_id, 'balance': 1000.0})
if sys.argv[1] == 'marker':
    controller._mark_committed('atomic-player', state, {'action_id': 'action-atomic', 'transaction_type': 'CASINO_WAR_WAGER', 'round_id': 'round-atomic'}, {'ledger_id': 'ledger-atomic'})
else:
    controller._reconcile_round('atomic-player', state, state['rounds']['round-atomic'])
"""
            # Resolve the single release file shared by the process pair.
            go_path = Path(temporary_root) / "go"
            # Retain both child handles for bounded lifecycle checks.
            processes = []
            # Start the marker and settlement workers against the same preloaded document.
            for index, mode in enumerate(("marker", "settle")):
                # Give each worker an independent ready marker.
                ready_path = Path(temporary_root) / f"ready-{index}"
                # Launch without a shell so argument identity stays exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, mode, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain the process and its corresponding readiness path.
                processes.append((process, ready_path))
            # Bound the pre-release rendezvous so a child failure cannot hang the suite.
            deadline = time.monotonic() + 10
            # Wait until both workers have loaded the same stale document.
            while not all(ready_path.exists() for _, ready_path in processes) and time.monotonic() < deadline:
                # Stop early when a worker exits before declaring readiness.
                if any(process.poll() is not None for process, _ in processes):
                    # Leave the loop so the explicit readiness assertion reports the failure.
                    break
                # Yield briefly without widening the race boundary.
                time.sleep(0.01)
            # Require both stale loads before permitting either write.
            self.assertTrue(all(ready_path.exists() for _, ready_path in processes))
            # Release both processes into the competing state transitions.
            go_path.write_text("go", encoding="utf-8")
            # Collect deterministic diagnostics and require both workers to complete.
            completed = [(*process.communicate(timeout=15), process.returncode) for process, _ in processes]
            # Inspect each child independently so a failure reports its exact process diagnostics.
            for standard_output, standard_error, return_code in completed:
                # Require a clean worker exit while retaining stdout and stderr in the assertion message.
                self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
            # Load the provider-published final document after both processes exit.
            final_state = json.loads(state_path.read_text(encoding="utf-8"))
            # Prove the marker process survived the competing terminal publication.
            self.assertEqual(final_state["ledger_actions"]["action-atomic"]["ledger_id"], "ledger-atomic")
            # Prove the terminal phase process survived the competing marker publication.
            self.assertEqual(final_state["rounds"]["round-atomic"]["phase"], "settled")

    # Confirm war replay creates only ante, matching wager, and one settlement.
    def test_war_replay_is_exactly_once(self):
        # Seed a deterministic initial tie.
        repository = MemoryRepository("bound-player", self.tied_state())
        # Record wallet movements.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Deal the initial tie and ante debit.
        started = controller.start_round("bound-player", 40, "action-start-103")
        # Resolve through war once.
        first = controller.decide("bound-player", started["round"]["round_id"], "war", "action-war-101")
        # Replay the same decision command.
        second = controller.decide("bound-player", started["round"]["round_id"], "war", "action-war-101")
        # Assert one ante debit, one war debit, and one total settlement credit.
        self.assertEqual([event["amount"] for event in recording_ledger.events], [-40.0, -40.0, 120.0])
        # Assert the replay returns the same terminal outcome.
        self.assertEqual((first["round"]["outcome"], second["round"]["outcome"]), ("war_win", "war_win"))

    # Confirm the route adapter gives session binding precedence over hostile body ids.
    def test_router_context_binding_overrides_body_player(self):
        # Seed only the authenticated player's state.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Record wallet ownership.
        recording_ledger = RecordingLedger()
        # Build and register the isolated controller on a local router.
        router = Router()
        # Register without touching the global application registry.
        api.register(router, self.controller(repository, recording_ledger))
        # Dispatch with a conflicting body player and a session-bound context.
        payload = router.dispatch("POST", "/api/v1/games/casino-war/rounds", {"player_id": "other-player", "wager": 10, "action_id": "action-start-104"}, {"bound_player_id": "bound-player"})
        # Assert the response and every ledger event belong to the session player.
        self.assertEqual(payload["player"]["player_id"], "bound-player")
        # Assert hostile body input never reached wallet ownership.
        self.assertTrue(all(event["player_id"] == "bound-player" for event in recording_ledger.events))


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest discovery for this file.
    unittest.main()
