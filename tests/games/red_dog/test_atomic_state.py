# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Red Dog state. (RD-006, TEST-228)"""

# Import deep-copy support for provider-shaped in-memory fixtures.
import copy
# Import JSON support for exact durable state inspection.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for fresh independent Python workers.
import subprocess
# Import the active interpreter used by the repository test runner.
import sys
# Import disposable directories for state and rendezvous ownership.
import tempfile
# Import bounded polling for child-process readiness.
import time
# Import the standard unit-test framework used by central discovery.
import unittest
# Import portable paths for repository and fixture identities.
from pathlib import Path

# Import deterministic ownership for every fresh-process race worker.
from tests.process_race import ProcessRacePool

# Import the public stale-writer error for exact fail-closed assertions.
from casino.errors import ConflictError
# Import production state helpers used to construct an actionable round.
from casino.games.red_dog import api, engine


# Simulate provider-current player documents for deterministic callback tests.
class MemoryRepository:
    # Start with one optional detached provider document.
    def __init__(self, document=None):
        # Retain only provider bytes, never caller-owned references.
        self.document = copy.deepcopy(document or engine.default_state())
        # Count callbacks to prove invalid transitions fail before storage.
        self.update_calls = 0

    # Load one detached provider document.
    def load(self, _player_id):
        # Return a copy so caller mutation cannot bypass update.
        return copy.deepcopy(self.document)

    # Apply one callback against exact current provider state.
    def update(self, _player_id, mutator):
        # Record one provider-bound mutation attempt.
        self.update_calls += 1
        # Execute the production callback against a detached current document.
        updated = mutator(copy.deepcopy(self.document))
        # Persist only the callback result after successful validation.
        self.document = copy.deepcopy(updated)
        # Return a detached authoritative result.
        return copy.deepcopy(updated)


# Prove provider-current comparison and stale-writer rejection locally and across processes.
class RedDogAtomicStateTests(unittest.TestCase):
    # Build one decision-ready round shared by competing publications.
    @staticmethod
    def _initial_state() -> dict:
        # Start from the exact game-owned default document.
        state = engine.default_state()
        # Arrange three, seven, then a winning five in draw order.
        state["shoe"] = ["5H", "7D", "3C"]
        # Bind the fixture to one stable shoe identity.
        state["shoe_id"] = "red-dog-atomic-shoe"
        # Prepare one normal-spread opening without invoking a wallet.
        round_item = engine.start_round(state, "atomic-player", 2, "atomic-deal-0001", round_id="red_dog_atomic_round", created_at="2026-08-16T00:00:00Z")
        # Bind the opening request exactly as the production controller does.
        state["requests"]["atomic-deal-0001"] = {"command": "rounds", "round_id": round_item["round_id"], "wager": 2.0}
        # Mark the opening debit complete so this fixture races state only.
        wager_intent = round_item["ledger_intents"][0]
        # Store the same compact ledger marker written by production recovery.
        state["ledger_actions"][wager_intent["action_id"]] = {"ledger_id": "atomic-ante-ledger", "transaction_type": wager_intent["transaction_type"], "round_id": round_item["round_id"], "amount": -2.0}
        # Return the complete actionable production state.
        return state

    # Reject fabricated detached state before entering provider storage.
    def test_missing_baseline_fails_before_storage(self) -> None:
        # Build production orchestration over one empty provider document.
        repository = MemoryRepository()
        # Construct the controller with only the persistence seam exercised.
        controller = api.RedDogController(repository=repository)
        # Reject state that did not originate from the tracked loader.
        with self.assertRaises(ConflictError):
            # Attempt to publish an untracked default document.
            controller._save("atomic-player", engine.default_state())
        # Prove storage never saw the invalid publication.
        self.assertEqual(0, repository.update_calls)

    # Preserve sibling fields when the desired game bytes already won.
    def test_identical_publication_is_idempotent_and_preserves_sibling(self) -> None:
        # Build production orchestration over one empty provider document.
        repository = MemoryRepository()
        # Construct the controller with only the persistence seam exercised.
        controller = api.RedDogController(repository=repository)
        # Capture a tracked default state.
        state = controller._load("atomic-player")
        # Publish unrelated provider metadata after the tracked read.
        repository.document["atomic_markers"] = ["sibling"]
        # Accept the identical game-owned state without replacing the document.
        controller._save("atomic-player", state)
        # Preserve unrelated provider metadata exactly.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])
        # Keep private optimistic metadata outside storage.
        self.assertNotIn("_red_dog_atomic_baseline", repository.document)

    # Reject one stale terminal writer after a different decision wins.
    def test_stale_terminal_publication_conflicts(self) -> None:
        # Seed one shared actionable round.
        repository = MemoryRepository(self._initial_state())
        # Construct the controller with only the persistence seam exercised.
        controller = api.RedDogController(repository=repository)
        # Capture two independently stale copies.
        first = controller._load("atomic-player")
        # Capture another operation before either publishes.
        second = controller._load("atomic-player")
        # Prepare a call result in the first operation.
        engine.call_round(first, "red_dog_atomic_round", "atomic-call-alpha", completed_at="2026-08-16T00:01:00Z")
        # Track the first immutable decision fingerprint.
        first["requests"]["atomic-call-alpha"] = {"command": "call", "round_id": "red_dog_atomic_round"}
        # Prepare a matching raise result in the stale competing operation.
        engine.raise_round(second, "red_dog_atomic_round", "atomic-raise-beta", completed_at="2026-08-16T00:02:00Z")
        # Track the competing immutable decision fingerprint.
        second["requests"]["atomic-raise-beta"] = {"command": "raise", "round_id": "red_dog_atomic_round"}
        # Commit the first terminal publication.
        controller._save("atomic-player", first)
        # Reject the incompatible stale second result.
        with self.assertRaises(ConflictError):
            # Attempt to overwrite the winning call result.
            controller._save("atomic-player", second)
        # Preserve the single winning decision and exact total wager.
        self.assertEqual(("settled", 2.0), (repository.document["rounds"]["red_dog_atomic_round"]["phase"], repository.document["rounds"]["red_dog_atomic_round"]["total_wager"]))

    # Prevent action-owned cleanup from erasing a newer terminal winner.
    def test_stale_cleanup_cannot_erase_concurrent_winner(self) -> None:
        # Seed one shared actionable round.
        repository = MemoryRepository(self._initial_state())
        # Construct the controller with only the persistence seam exercised.
        controller = api.RedDogController(repository=repository)
        # Load the soon-to-be-rejected decision state.
        rejected = controller._load("atomic-player")
        # Preserve its exact actionable game state for cleanup.
        prior = copy.deepcopy(rejected)
        # Prepare one raise result and request mapping.
        engine.raise_round(rejected, "red_dog_atomic_round", "atomic-raise-rejected", completed_at="2026-08-16T00:01:00Z")
        # Track the prepared decision before any movement.
        rejected["requests"]["atomic-raise-rejected"] = {"command": "raise", "round_id": "red_dog_atomic_round"}
        # Publish the prepared recovery state.
        controller._save("atomic-player", rejected)
        # Load that preparation for a newer authoritative publication.
        winning = controller._load("atomic-player")
        # Bind one durable winning ledger marker to the prepared raise.
        winning["ledger_actions"]["rd:atomic-raise-rejected:raise"] = {"ledger_id": "atomic-raise-ledger", "transaction_type": "RED_DOG_RAISE_DEBIT", "round_id": "red_dog_atomic_round", "amount": -2.0}
        # Publish the newer game-owned result.
        controller._save("atomic-player", winning)
        # Reject cleanup based on the superseded prepared baseline.
        with self.assertRaises(ConflictError):
            # Attempt to restore the original actionable round.
            controller._restore("atomic-player", rejected, prior)
        # Preserve the concurrent durable marker and terminal phase.
        self.assertEqual(("settled", "atomic-raise-ledger"), (repository.document["rounds"]["red_dog_atomic_round"]["phase"], repository.document["ledger_actions"]["rd:atomic-raise-rejected:raise"]["ledger_id"]))

    # Prove two stale fresh processes produce one terminal winner and one conflict.
    def test_fresh_process_terminal_race_preserves_sibling(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve the disposable JSON provider data root.
            data_root = Path(temporary) / "data"
            # Resolve this player's exact game-state document.
            state_path = data_root / "games" / engine.GAME_ID / "atomic-player.json"
            # Create the player-game directory before publishing the fixture.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Persist one common pre-race state for both workers.
            state_path.write_text(json.dumps(self._initial_state()), encoding="utf-8")
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Copy the caller environment before replacing runtime-owned paths.
            environment = os.environ.copy()
            # Select only the disposable JSON provider root.
            environment["CASINO_DATA_DIR"] = str(data_root)
            # Keep child logs inside the same task-owned directory.
            environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
            # Require the JSON provider so its cross-process file lock is exercised.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Bind imports to this exact worktree rather than another checkout.
            environment["PYTHONPATH"] = str(repository_root)
            # Define one dependency-free worker that loads before the shared release.
            worker_source = """
import sys
import time
from pathlib import Path
from casino.errors import ConflictError
from casino.games.red_dog import api, engine
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
controller = api.RedDogController()
state = controller._load('atomic-player')
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Red Dog atomic race release timed out')
action_id = f'atomic-call-{tag}'
engine.call_round(state, 'red_dog_atomic_round', action_id, completed_at=f'2026-08-16T00:0{1 if tag == "alpha" else 2}:00Z')
state['requests'][action_id] = {'command': 'call', 'round_id': 'red_dog_atomic_round'}
try:
    controller._save('atomic-player', state)
except ConflictError:
    print(f'CONFLICT:{tag}')
else:
    print(f'PASS:{tag}')
"""
            # Resolve one release marker shared by the exact worker pair.
            go_path = Path(temporary) / "go"
            # Retain child handles and their unique readiness files.
            processes = []
            # Launch both workers without a shell or shared Python process.
            for tag in ("alpha", "beta"):
                # Allocate one readiness marker for this child.
                ready_path = Path(temporary) / f"ready-{tag}"
                # Start the exact interpreter with bounded pipe capture.
                process = process_pool.spawn([sys.executable, "-c", worker_source, tag, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain the process and marker for rendezvous validation.
                processes.append((process, ready_path))
            # Bound the stale-load rendezvous so a broken child cannot hang CI.
            deadline = time.monotonic() + 10
            # Wait until both children own the same stale baseline.
            while not all(ready.exists() for _, ready in processes) and time.monotonic() < deadline:
                # Stop early when a child exits before claiming readiness.
                if any(process.poll() is not None for process, _ in processes):
                    # Leave the loop for the explicit diagnostic assertion.
                    break
                # Yield briefly without changing worker order.
                time.sleep(0.01)
            # Require a complete stale-state rendezvous before release.
            process_pool.wait_until_ready([(process, ready) for process, ready in processes], timeout=0)
            # Read the still-unmodified game document after both stale loads.
            sibling_state = json.loads(state_path.read_text(encoding="utf-8"))
            # Add unrelated provider metadata that both publications must preserve.
            sibling_state["atomic_markers"] = ["sibling"]
            # Publish the sibling before either stale transition proceeds.
            state_path.write_text(json.dumps(sibling_state), encoding="utf-8")
            # Release both prepared workers exactly once.
            go_path.write_text("go", encoding="utf-8")
            # Collect bounded diagnostics and final exit codes.
            completed = [(*process.communicate(timeout=20), process.returncode) for process, _ in processes]
            # Require both legal completion and expected conflict paths to terminate.
            for standard_output, standard_error, return_code in completed:
                # Preserve output only when a child violates the proof.
                self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
            # Normalize the unordered race results for exact winner accounting.
            outcomes = sorted(standard_output.strip().split(":", 1)[0] for standard_output, _standard_error, _return_code in completed)
            # Require exactly one terminal publication and one stale conflict.
            self.assertEqual(["CONFLICT", "PASS"], outcomes)
            # Read the single provider-authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one terminal round and one winning decision request.
            winning_actions = sorted(action_id for action_id in final["requests"] if action_id.startswith("atomic-call-"))
            # Bind one exact terminal result without depending on race order.
            self.assertEqual((1, "settled"), (len(winning_actions), final["rounds"]["red_dog_atomic_round"]["phase"]))
            # Preserve the unrelated sibling through the winning provider update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Reject private optimistic metadata from persistent JSON bytes.
            self.assertNotIn("_red_dog_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
