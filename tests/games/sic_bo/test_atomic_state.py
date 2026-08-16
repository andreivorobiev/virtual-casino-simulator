# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Sic Bo state. (SIC-BO-006, TEST-230)"""

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

# Import the public stale-writer error for exact fail-closed assertions.
from casino.errors import ConflictError
# Import production state helpers and the provider-atomic service.
from casino.games.sic_bo import engine
from casino.games.sic_bo.service import SicBoService


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
class SicBoAtomicStateTests(unittest.TestCase):
    # Build one deterministic private prepared round for transition fixtures.
    @staticmethod
    def _prepared_round(action_id="sic-bo-atomic") -> dict:
        # Bind the recovery record to one stable semantic wager.
        wagers = {"small": 1.0}
        # Return the private pre-ledger state shape owned by the service.
        return {
            "round_id": engine.round_id_for("atomic-player", action_id),
            "action_id": action_id,
            "player_id": "atomic-player",
            "request_fingerprint": engine.wager_fingerprint(wagers),
            "wagers": wagers,
            "dice": [1, 2, 3],
            "phase": "prepared",
            "wager_status": "pending",
            "payout_status": "not_ready",
            "created_at": "2026-08-16T00:00:00Z",
        }

    # Reject fabricated detached state before entering provider storage.
    def test_missing_baseline_fails_before_storage(self) -> None:
        # Build production orchestration over one empty provider document.
        repository = MemoryRepository()
        # Construct the service with only the persistence seams exercised.
        service = SicBoService(state_loader=repository.load, state_updater=repository.update)
        # Reject state that did not originate from the tracked loader.
        with self.assertRaises(ConflictError):
            # Attempt to publish an untracked default document.
            service._save("atomic-player", engine.default_state())
        # Prove storage never saw the invalid publication.
        self.assertEqual(0, repository.update_calls)

    # Preserve sibling fields when the desired game bytes already won.
    def test_identical_publication_is_idempotent_and_preserves_sibling(self) -> None:
        # Build production orchestration over one default provider document.
        repository = MemoryRepository()
        # Construct the service with only the persistence seams exercised.
        service = SicBoService(state_loader=repository.load, state_updater=repository.update)
        # Capture a tracked provider state.
        state = service._load("atomic-player")
        # Publish unrelated provider metadata after the tracked read.
        repository.document["atomic_markers"] = ["sibling"]
        # Accept the identical game-owned state without replacing the document.
        service._save("atomic-player", state)
        # Preserve unrelated provider metadata exactly.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])
        # Keep private optimistic metadata outside storage.
        self.assertNotIn("_sic_bo_atomic_baseline", repository.document)

    # Reject one stale preparation after another action wins.
    def test_stale_preparation_publication_conflicts(self) -> None:
        # Seed one common empty state for competing actions.
        repository = MemoryRepository()
        # Construct the service with only the persistence seams exercised.
        service = SicBoService(state_loader=repository.load, state_updater=repository.update)
        # Capture two independently stale copies.
        first = service._load("atomic-player")
        # Capture another operation before either publishes.
        second = service._load("atomic-player")
        # Prepare the first action's private recovery record.
        first["active_round"] = self._prepared_round("sic-bo-alpha")
        # Prepare a different action against the stale baseline.
        second["active_round"] = self._prepared_round("sic-bo-beta")
        # Commit the first preparation publication.
        service._save("atomic-player", first)
        # Reject the incompatible stale second preparation.
        with self.assertRaises(ConflictError):
            # Attempt to overwrite the winning active round.
            service._save("atomic-player", second)
        # Preserve only the winning action identity.
        self.assertEqual("sic-bo-alpha", repository.document["active_round"]["action_id"])

    # Prevent action-owned cleanup from erasing a newer publication.
    def test_stale_cleanup_cannot_erase_concurrent_winner(self) -> None:
        # Seed one empty shared provider state.
        repository = MemoryRepository()
        # Construct the service with only the persistence seams exercised.
        service = SicBoService(state_loader=repository.load, state_updater=repository.update)
        # Load the soon-to-be-rejected operation state.
        rejected = service._load("atomic-player")
        # Publish its private preparation before the simulated ledger failure.
        rejected["active_round"] = self._prepared_round("sic-bo-rejected")
        # Commit the prepared recovery state and advance its baseline.
        service._save("atomic-player", rejected)
        # Load that preparation for a newer authoritative publication.
        winning = service._load("atomic-player")
        # Advance the same round to a committed-wager recovery marker.
        winning["active_round"]["phase"] = "settling"
        # Publish the newer game-owned result.
        service._save("atomic-player", winning)
        # Model the rejected operation's action-owned cleanup.
        rejected["active_round"] = None
        # Reject cleanup based on the superseded prepared baseline.
        with self.assertRaises(ConflictError):
            # Attempt to erase the winning committed-wager marker.
            service._save("atomic-player", rejected)
        # Preserve the concurrent authoritative phase.
        self.assertEqual("settling", repository.document["active_round"]["phase"])

    # Prove two stale fresh processes produce one preparation winner and one conflict.
    def test_fresh_process_preparation_race_preserves_sibling(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the disposable JSON provider data root.
            data_root = Path(temporary) / "data"
            # Resolve this player's exact game-state document.
            state_path = data_root / "games" / engine.GAME_ID / "atomic-player.json"
            # Create the player-game directory before publishing the fixture.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Persist one common pre-race state for both workers.
            state_path.write_text(json.dumps(engine.default_state()), encoding="utf-8")
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
from casino.games.sic_bo import engine
from casino.games.sic_bo.service import SicBoService
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
service = SicBoService()
state = service._load('atomic-player')
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Sic Bo atomic race release timed out')
action_id = f'sic-bo-{tag}'
wagers = {'small': 1.0}
state['active_round'] = {
    'round_id': engine.round_id_for('atomic-player', action_id),
    'action_id': action_id,
    'player_id': 'atomic-player',
    'request_fingerprint': engine.wager_fingerprint(wagers),
    'wagers': wagers,
    'dice': [1, 2, 3],
    'phase': 'prepared',
    'wager_status': 'pending',
    'payout_status': 'not_ready',
    'created_at': '2026-08-16T00:00:00Z',
}
try:
    service._save('atomic-player', state)
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
                process = subprocess.Popen([sys.executable, "-c", worker_source, tag, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
            self.assertTrue(all(ready.exists() for _, ready in processes))
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
            # Require exactly one preparation publication and one stale conflict.
            self.assertEqual(["CONFLICT", "PASS"], outcomes)
            # Read the single provider-authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exactly one winning private active action.
            self.assertIn(final["active_round"]["action_id"], {"sic-bo-alpha", "sic-bo-beta"})
            # Preserve the unrelated sibling through the winning provider update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Reject private optimistic metadata from persistent JSON bytes.
            self.assertNotIn("_sic_bo_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
