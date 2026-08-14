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


# Inject one ledger response failure while optionally preserving a committed event.
class FaultingLedger(RecordingLedger):
    # Bind the repository used to publish a concurrent sibling update during failure.
    def __init__(self, repository, *, commit_before_error: bool, events=None):
        # Seed any movements already committed before the faulting action.
        self.events = copy.deepcopy(events or [])
        # Retain the repository so the fault schedule can publish unrelated state.
        self.repository = repository
        # Select whether the simulated lost response committed before raising.
        self.commit_before_error = commit_before_error
        # Fail only the first transaction so reload recovery can finish later.
        self.failed = False

    # Publish a sibling update and raise once at the configured ledger boundary.
    def transact(self, intent: dict) -> dict:
        # Let recovery complete normally after the one injected failure.
        if self.failed:
            # Delegate subsequent movements to the recording ledger.
            return super().transact(intent)
        # Consume the one-shot failure before invoking any nested behavior.
        self.failed = True

        # Add one unrelated provider-owned field while the prepared action is pending.
        def publish_sibling(current: dict) -> dict:
            # Prove bounded rollback never replaces the complete player document.
            current["sibling_atomic"] = "preserved"
            # Publish the latest document through the atomic repository seam.
            return current

        # Commit the sibling field before the wallet outcome becomes visible.
        self.repository.update(intent["player_id"], publish_sibling)
        # Append the ledger event first when simulating a committed lost response.
        if self.commit_before_error:
            # Preserve the authoritative event for the controller's recovery scan.
            super().transact(intent)
        # Surface the transport-style failure after the selected durable effects.
        raise RuntimeError("injected Casino War ledger response failure")


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

    # Run two fresh processes from one stale snapshot and return their durable result.
    def run_preparation_race(self, seeded_state: dict, operation: str, modes: tuple[str, str]) -> tuple[dict, list[dict], dict | None]:
        # Own every child-process byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary_root:
            # Resolve the isolated JSON provider root selected by both workers.
            data_root = Path(temporary_root) / "data"
            # Resolve the exact player document used by the production state repository.
            state_path = data_root / "games" / "casino_war" / "atomic-player.json"
            # Create the game directory before publishing the shared stale snapshot.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Serialize a detached state so both workers observe identical starting bytes.
            state_path.write_text(json.dumps(seeded_state), encoding="utf-8")
            # Resolve this exact worktree for explicit child import binding.
            repository_root = Path(__file__).resolve().parents[4]
            # Copy the parent environment before replacing disposable runtime paths.
            environment = os.environ.copy()
            # Bind both processes to the same isolated JSON state root.
            environment["CASINO_DATA_DIR"] = str(data_root)
            # Keep child diagnostics inside the disposable owner boundary.
            environment["CASINO_LOG_DIR"] = str(Path(temporary_root) / "logs")
            # Exercise the operating-system document lock used by the JSON provider.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Force imports to this exact worktree rather than another checkout.
            environment["PYTHONPATH"] = str(repository_root)
            # Define the production provider bootstrap used when a race reaches settlement.
            bootstrap_source = """
from casino.core.storage import get_storage_provider
get_storage_provider().bootstrap_players({'players': [{'player_id': 'atomic-player', 'display_name': 'Atomic Casino War', 'type': 'human', 'balance': 100.0, 'created_at': '2026-08-14T00:00:00Z', 'updated_at': '2026-08-14T00:00:00Z', 'status': 'active'}]})
"""
            # Seed one complete wallet row through the same provider used by settlement.
            bootstrap = subprocess.run([sys.executable, "-c", bootstrap_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require isolated provider bootstrap to complete before either worker starts.
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            # Define one dependency-free worker for action/action and action/sibling races.
            worker_source = """
import json
import sys
import time
from pathlib import Path
from casino.games.casino_war import api
repository = api.StateRepository()
state = repository.load('atomic-player')
ready_path = Path(sys.argv[3])
go_path = Path(sys.argv[4])
result_path = Path(sys.argv[5])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Casino War preparation race timed out')
controller = api.CasinoWarController(repository, None, lambda player_id: {'player_id': player_id, 'balance': 1000.0})
if sys.argv[2] == 'sibling':
    def mark(current):
        current['sibling_atomic'] = 'preserved'
        return current
    repository.update('atomic-player', mark)
    result = {'mode': 'sibling'}
elif sys.argv[1] in {'start', 'settled-start'}:
    round_item, created, _ = controller._prepare_start('atomic-player', state, 25, 'action-race-771')
    if sys.argv[1] == 'settled-start':
        round_item = controller._reconcile_round('atomic-player', state, round_item)
    result = {'mode': 'action', 'created': created, 'round_id': round_item['round_id']}
else:
    round_id = state['round_order'][-1]
    round_item, created, _ = controller._prepare_decision('atomic-player', state, round_id, 'war', 'action-race-771')
    result = {'mode': 'action', 'created': created, 'round_id': round_item['round_id']}
result_path.write_text(json.dumps(result), encoding='utf-8')
"""
            # Resolve the one release marker shared by the process pair.
            go_path = Path(temporary_root) / "go"
            # Retain process, readiness, and result paths for bounded collection.
            processes = []
            # Launch both workers before releasing either stale snapshot.
            for index, mode in enumerate(modes):
                # Allocate an independent ready marker for this worker.
                ready_path = Path(temporary_root) / f"prepare-ready-{index}"
                # Allocate an independent structured result for this worker.
                result_path = Path(temporary_root) / f"prepare-result-{index}.json"
                # Start the worker without a shell so every argument stays exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, operation, mode, str(ready_path), str(go_path), str(result_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain all paths needed for deterministic assertions.
                processes.append((process, ready_path, result_path))
            # Bound readiness so a child failure cannot hang the suite.
            deadline = time.monotonic() + 10
            # Wait until both processes loaded the same stale snapshot.
            while not all(ready_path.exists() for _, ready_path, _ in processes) and time.monotonic() < deadline:
                # Stop early when a child exits before readiness.
                if any(process.poll() is not None for process, _, _ in processes):
                    # Let the explicit assertion below report the incomplete rendezvous.
                    break
                # Yield briefly without broadening the race schedule.
                time.sleep(0.01)
            # Require both stale reads before any provider transition begins.
            self.assertTrue(all(ready_path.exists() for _, ready_path, _ in processes))
            # Release both workers into the competing atomic updates.
            go_path.write_text("go", encoding="utf-8")
            # Collect each child with bounded diagnostics.
            completed = [(*process.communicate(timeout=15), process.returncode, result_path) for process, _, result_path in processes]
            # Require clean exits before interpreting their structured results.
            for standard_output, standard_error, return_code, _ in completed:
                # Include both output streams when a child fails.
                self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
            # Read the provider-published document after both transitions complete.
            final_state = json.loads(state_path.read_text(encoding="utf-8"))
            # Read each result only after its owning process exits successfully.
            results = [json.loads(result_path.read_text(encoding="utf-8")) for _, _, _, result_path in completed]
            # Start without wallet evidence when this race only exercises state preparation.
            evidence = None
            # Read production wallet and ledger rows when both workers reconciled the round.
            if operation == "settled-start":
                # Define a fresh-process authoritative settlement reader.
                evidence_source = """
import json
from casino.core import players
from casino.core.settlement import GameSettlementGateway
gateway = GameSettlementGateway('casino_war', 'casino_war_action_id')
print(json.dumps({'balance': players.get_player('atomic-player')['balance'], 'rows': gateway.read_recent('atomic-player', 20)}))
"""
                # Execute the read without sharing either contender's provider cache.
                evidence_result = subprocess.run([sys.executable, "-c", evidence_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
                # Require the durable read to complete cleanly.
                self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
                # Decode the exact final wallet and append-only rows.
                evidence = json.loads(evidence_result.stdout.strip())
            # Return detached evidence after the temporary filesystem closes.
            return final_state, results, evidence

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

    # Confirm one action identifier cannot cross start and decision command boundaries.
    def test_action_id_command_conflicts_are_rejected_atomically(self):
        # Seed a deterministic tie so both command families are available.
        repository = MemoryRepository("bound-player", self.tied_state())
        # Record the ordinary ante, war wager, and settlement movements.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Establish one unresolved round under a start-owned action identifier.
        started = controller.start_round("bound-player", 25, "action-start-conflict-771")
        # Reject reuse of the start identifier for a war decision.
        with self.assertRaisesRegex(api.ValidationError, "already used for another command"):
            # Attempt to claim the start key from the decision route.
            controller.decide("bound-player", started["round"]["round_id"], "war", "action-start-conflict-771")
        # Resolve the tie under its own decision-owned action identifier.
        controller.decide("bound-player", started["round"]["round_id"], "war", "action-war-conflict-771")
        # Reject reuse of the decision identifier from the start route.
        with self.assertRaisesRegex(api.ValidationError, "already used for another command"):
            # Attempt to claim the war key from a new-round request.
            controller.start_round("bound-player", 25, "action-war-conflict-771")
        # Require only the original ante, one war wager, and one settlement credit.
        self.assertEqual([event["amount"] for event in recording_ledger.events], [-25.0, -25.0, 75.0])

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

    # Confirm initial preparation preserves a sibling update and deduplicates one action across processes.
    def test_start_preparation_is_atomic_across_processes(self):
        # Race one start preparation against an unrelated top-level update.
        sibling_state, sibling_results, _ = self.run_preparation_race(self.winning_state(), "start", ("action", "sibling"))
        # Require the unrelated provider-owned field to survive the action publication.
        self.assertEqual(sibling_state["sibling_atomic"], "preserved")
        # Require exactly one prepared round and one durable request mapping.
        self.assertEqual((len(sibling_state["rounds"]), len(sibling_state["requests"])), (1, 1))
        # Require exactly two initial cards to be consumed from the existing shoe.
        self.assertEqual(len(sibling_state["shoe"]), 5)
        # Require the action worker to report preparation ownership.
        self.assertEqual([result["created"] for result in sibling_results if result["mode"] == "action"], [True])
        # Race two processes using the same exact client action identifier.
        duplicate_state, duplicate_results, _ = self.run_preparation_race(self.winning_state(), "start", ("action", "action"))
        # Require one winner and one replay without a second state transition.
        self.assertEqual(sorted(result["created"] for result in duplicate_results), [False, True])
        # Require both workers to resolve the same stable round identifier.
        self.assertEqual(len({result["round_id"] for result in duplicate_results}), 1)
        # Require one round, one mapping, and one pair of dealt cards after contention.
        self.assertEqual((len(duplicate_state["rounds"]), len(duplicate_state["requests"]), len(duplicate_state["shoe"])), (1, 1, 5))
        # Require one exact ante and settlement instruction sequence in the winning round.
        duplicate_round = next(iter(duplicate_state["rounds"].values()))
        # Reject duplicated debit or credit intent identities after contention.
        self.assertEqual(len({intent["action_id"] for intent in duplicate_round["ledger_intents"]}), len(duplicate_round["ledger_intents"]))

    # Confirm two same-action processes settle one exact debit and credit through production providers.
    def test_same_start_action_settles_exactly_once_across_processes(self):
        # Race both contenders through atomic preparation and the real settlement gateway.
        final_state, results, evidence = self.run_preparation_race(self.winning_state(), "settled-start", ("action", "action"))
        # Require one preparation winner and one replay of the same round.
        self.assertEqual(sorted(result["created"] for result in results), [False, True])
        # Require both processes to return the same stable identity.
        self.assertEqual(len({result["round_id"] for result in results}), 1)
        # Require the durable state to retain one settled logical round.
        self.assertEqual((len(final_state["rounds"]), next(iter(final_state["rounds"].values()))["phase"]), (1, "settled"))
        # Select the two Casino War movement families from the fresh provider read.
        movement_rows = [row for row in evidence["rows"] if row["transaction_type"] in {"CASINO_WAR_ANTE_DEBIT", "CASINO_WAR_SETTLEMENT_CREDIT"}]
        # Require one ante debit, one settlement credit, one round identity, and the exact final wallet.
        self.assertEqual((evidence["balance"], sorted(row["transaction_type"] for row in movement_rows), len({row["round_id"] for row in movement_rows})), (125.0, ["CASINO_WAR_ANTE_DEBIT", "CASINO_WAR_SETTLEMENT_CREDIT"], 1))

    # Confirm war preparation preserves a sibling update and deduplicates one action across processes.
    def test_decision_preparation_is_atomic_across_processes(self):
        # Build a deterministic tied round without invoking a wallet adapter.
        sibling_seed = self.tied_state()
        # Persist the unresolved tie that both child processes will load.
        engine.start_round(sibling_seed, "atomic-player", 25, "seed-start-771", round_id="round-race-771")
        # Race the war decision against an unrelated top-level update.
        sibling_state, sibling_results, _ = self.run_preparation_race(sibling_seed, "decision", ("action", "sibling"))
        # Require the sibling update to survive the war card publication.
        self.assertEqual(sibling_state["sibling_atomic"], "preserved")
        # Require one durable war mapping and exactly five additional consumed cards.
        self.assertEqual((sibling_state["requests"]["action-race-771"]["command"], len(sibling_state["shoe"])), ("war", 0))
        # Require the action worker to own the one prepared decision.
        self.assertEqual([result["created"] for result in sibling_results if result["mode"] == "action"], [True])
        # Build a fresh tied document for same-action contention.
        duplicate_seed = self.tied_state()
        # Persist the same unresolved round identity for both duplicate workers.
        engine.start_round(duplicate_seed, "atomic-player", 25, "seed-start-772", round_id="round-race-772")
        # Race two exact decision actions against the provider-owned lock.
        duplicate_state, duplicate_results, _ = self.run_preparation_race(duplicate_seed, "decision", ("action", "action"))
        # Require exactly one winning preparation and one replay.
        self.assertEqual(sorted(result["created"] for result in duplicate_results), [False, True])
        # Require both callers to resolve the same prepared round.
        self.assertEqual({result["round_id"] for result in duplicate_results}, {"round-race-772"})
        # Require one action mapping and one exact war-card consumption.
        self.assertEqual((len(duplicate_state["requests"]), len(duplicate_state["shoe"])), (1, 0))
        # Require the prepared round to retain one ante, one war debit, and at most one settlement credit.
        duplicate_round = duplicate_state["rounds"]["round-race-772"]
        # Reject duplicated movement identities in the exact winning decision.
        self.assertEqual(len({intent["action_id"] for intent in duplicate_round["ledger_intents"]}), len(duplicate_round["ledger_intents"]))

    # Confirm a failed ante restores action-owned history and preserves a concurrent sibling update.
    def test_start_failure_rolls_back_prepared_state_without_losing_sibling(self):
        # Seed a deterministic winning shoe and a full settled history.
        seeded_state = self.winning_state()
        # Fill the bounded history so the new preparation prunes one old round.
        for index in range(engine.ROUND_HISTORY_LIMIT):
            # Build the minimum settled body needed by the engine's active-round guard.
            round_item = {"round_id": f"old-round-{index}", "phase": "settled"}
            # Publish the round under its stable identity.
            seeded_state["rounds"][round_item["round_id"]] = round_item
            # Preserve its deterministic history position.
            seeded_state["round_order"].append(round_item["round_id"])
        # Retain exact pre-action shoe and history for rollback comparison.
        expected_shoe = copy.deepcopy(seeded_state["shoe"])
        # Create the detached repository used by the faulting ledger.
        repository = MemoryRepository("bound-player", seeded_state)
        # Fail before recording the ante while publishing an unrelated sibling field.
        faulting_ledger = FaultingLedger(repository, commit_before_error=False)
        # Build the isolated controller around the failure schedule.
        controller = self.controller(repository, faulting_ledger)
        # Require the original ledger failure to remain visible to the caller.
        with self.assertRaisesRegex(RuntimeError, "injected Casino War ledger response failure"):
            # Start one round that must be fully rolled back.
            controller.start_round("bound-player", 25, "action-start-rollback-771")
        # Load the exact provider state after bounded rollback.
        final_state = repository.load("bound-player")
        # Require unrelated sibling state to survive the rollback update.
        self.assertEqual(final_state["sibling_atomic"], "preserved")
        # Require the full pre-action history, including the pruned oldest round, to return.
        self.assertEqual(final_state["round_order"], seeded_state["round_order"])
        # Require every pre-action history body to remain exact.
        self.assertEqual(final_state["rounds"], seeded_state["rounds"])
        # Require cards, request mappings, and ledger history to remain unconsumed.
        self.assertEqual((final_state["shoe"], final_state["requests"], faulting_ledger.events), (expected_shoe, {}, []))

    # Confirm a failed war debit restores the tie while preserving prior money evidence and sibling state.
    def test_decision_failure_rolls_back_prepared_state_without_losing_sibling(self):
        # Seed a deterministic initial tie.
        repository = MemoryRepository("bound-player", self.tied_state())
        # Commit only the original ante through the ordinary ledger fixture.
        recording_ledger = RecordingLedger()
        # Build the controller used to establish the unresolved round.
        controller = self.controller(repository, recording_ledger)
        # Start the tie before replacing the ledger with a faulting decision adapter.
        started = controller.start_round("bound-player", 25, "action-start-tie-771")
        # Capture the exact unresolved state before war card preparation.
        before_decision = repository.load("bound-player")
        # Fail before recording the war debit while preserving the committed ante lookup.
        faulting_ledger = FaultingLedger(repository, commit_before_error=False, events=recording_ledger.events)
        # Route the decision through the one-shot failure adapter.
        controller.ledger = faulting_ledger
        # Require the original ledger failure to reach the caller.
        with self.assertRaisesRegex(RuntimeError, "injected Casino War ledger response failure"):
            # Attempt the matching-wager war decision.
            controller.decide("bound-player", started["round"]["round_id"], "war", "action-war-rollback-771")
        # Load the bounded rollback result.
        final_state = repository.load("bound-player")
        # Require the unrelated sibling field to survive.
        self.assertEqual(final_state["sibling_atomic"], "preserved")
        # Require the original tie round and shoe to be restored byte-for-byte.
        self.assertEqual((final_state["rounds"], final_state["shoe"]), (before_decision["rounds"], before_decision["shoe"]))
        # Require the failed decision mapping to be absent while the start mapping remains.
        self.assertEqual(final_state["requests"], before_decision["requests"])
        # Require the original ante to remain the only committed event.
        self.assertEqual(faulting_ledger.events, recording_ledger.events)

    # Confirm a committed lost response keeps prepared state and recovers without a second debit.
    def test_committed_lost_response_is_recovered_without_rollback(self):
        # Seed a deterministic immediate player win.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Commit the ante before raising the one simulated response failure.
        faulting_ledger = FaultingLedger(repository, commit_before_error=True)
        # Build the isolated controller around the lost-response schedule.
        controller = self.controller(repository, faulting_ledger)
        # Require the transport-style failure to remain visible after the committed debit.
        with self.assertRaisesRegex(RuntimeError, "injected Casino War ledger response failure"):
            # Start the round whose ante commits before the response is lost.
            controller.start_round("bound-player", 25, "action-start-lost-771")
        # Load the provider state before recovery to prove preparation was not rolled back.
        prepared_state = repository.load("bound-player")
        # Require the action mapping, round, and sibling update to remain durable.
        self.assertEqual((len(prepared_state["requests"]), len(prepared_state["rounds"]), prepared_state["sibling_atomic"]), (1, 1, "preserved"))
        # Recover the committed ante and remaining settlement through the public state path.
        recovered = controller.state("bound-player")
        # Require one debit and one settlement credit with no duplicate ante.
        self.assertEqual([event["amount"] for event in faulting_ledger.events], [-25.0, 50.0])
        # Require the recovered round to become terminal with both movements recorded.
        self.assertEqual((recovered["state"]["rounds"][0]["phase"], recovered["state"]["rounds"][0]["settlement"]["committed_actions"]), ("settled", 2))

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
