# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-atomic Teen Patti state evidence. (TEENP-003, TEST-232)"""

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
# Import Teen Patti-owned state rules and service orchestration.
from casino.games.teen_patti import engine, service


# Simulate provider-current player documents for deterministic callback tests.
class MemoryUpdater:
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
        # Execute the production callback against detached current state.
        updated = mutator(copy.deepcopy(self.document))
        # Persist only the callback result after successful validation.
        self.document = copy.deepcopy(updated)
        # Return detached provider authority to the service.
        return copy.deepcopy(updated)


# Prove provider-current comparison and stale-writer rejection locally and across processes.
class TeenPattiAtomicStateTests(unittest.TestCase):
    # Build one service over a provider-shaped in-memory document.
    @staticmethod
    def _service(repository: MemoryUpdater) -> service.TeenPattiService:
        # Inject only state and harmless read seams; no ledger call is needed here.
        return service.TeenPattiService(ledger_gateway=object(), state_loader=repository.load, state_updater=repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": 100.0})

    # Build one compact terminal row for publication fixtures.
    @staticmethod
    def _round(round_id: str) -> dict:
        # Return enough identity to distinguish competing publications.
        return {"round_id": round_id, "phase": "settled", "payout": 0.0}

    # Reject fabricated detached state before entering provider storage.
    def test_missing_baseline_fails_before_storage(self) -> None:
        # Build one empty provider-shaped document and service.
        repository = MemoryUpdater()
        # Bind production comparison logic to the deterministic provider seam.
        game = self._service(repository)
        # Reject state that did not originate from the tracked loader.
        with self.assertRaises(ConflictError):
            # Attempt to publish an untracked default document.
            game._save("atomic-player", engine.default_state())
        # Prove storage never saw the invalid publication.
        self.assertEqual(0, repository.update_calls)

    # Preserve sibling fields when the desired Teen Patti bytes already won.
    def test_identical_publication_is_idempotent_and_private(self) -> None:
        # Build one empty provider-shaped document and service.
        repository = MemoryUpdater()
        # Bind production comparison logic to the deterministic provider seam.
        game = self._service(repository)
        # Capture a tracked provider state.
        state = game._load("atomic-player")
        # Publish unrelated provider metadata after the tracked read.
        repository.document["atomic_markers"] = ["sibling"]
        # Accept the identical game-owned state without replacing the document.
        game._save("atomic-player", state)
        # Preserve unrelated provider metadata exactly.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])
        # Keep private optimistic metadata outside persistent storage.
        self.assertNotIn(service._ATOMIC_BASELINE_KEY, repository.document)
        # Keep private optimistic metadata outside the frozen public state.
        self.assertNotIn(service._ATOMIC_BASELINE_KEY, engine.public_state(state))

    # Reject one stale terminal publication after another action wins.
    def test_stale_publication_conflicts(self) -> None:
        # Seed one common empty state for competing actions.
        repository = MemoryUpdater()
        # Bind production comparison logic to the deterministic provider seam.
        game = self._service(repository)
        # Capture two independently stale copies.
        first = game._load("atomic-player")
        # Capture another operation before either publishes.
        second = game._load("atomic-player")
        # Prepare the first operation's settled history.
        first["recent_rounds"].append(self._round("teen-alpha"))
        # Prepare a different result against the stale baseline.
        second["recent_rounds"].append(self._round("teen-beta"))
        # Commit the first publication.
        game._save("atomic-player", first)
        # Reject the incompatible stale second publication.
        with self.assertRaises(ConflictError):
            # Attempt to overwrite the winning settled history.
            game._save("atomic-player", second)
        # Preserve only the winning action identity.
        self.assertEqual("teen-alpha", repository.document["recent_rounds"][0]["round_id"])

    # Prevent stale recovery cleanup from erasing a newer publication.
    def test_stale_cleanup_cannot_erase_concurrent_winner(self) -> None:
        # Seed one empty shared provider state.
        repository = MemoryUpdater()
        # Bind production comparison logic to the deterministic provider seam.
        game = self._service(repository)
        # Load the operation state that will later attempt cleanup.
        rejected = game._load("atomic-player")
        # Prepare and publish the first active round.
        rejected["active_round"] = {"round_id": "teen-rejected", "phase": "decision"}
        # Bind the first action identity beside its active round.
        rejected["action_receipts"]["deal-rejected"] = {"stage": "deal", "round_id": "teen-rejected"}
        # Commit the prepared state and advance its tracked baseline.
        game._save("atomic-player", rejected)
        # Load that state for a newer authoritative settlement.
        winning = game._load("atomic-player")
        # Move the prepared result into settled history.
        winning["recent_rounds"].append(self._round("teen-winner"))
        # Clear the winning operation's active slot.
        winning["active_round"] = None
        # Publish the newer authoritative state.
        game._save("atomic-player", winning)
        # Model rejected-operation cleanup from its now-stale baseline.
        rejected["active_round"] = None
        # Release its older action receipt.
        rejected["action_receipts"].pop("deal-rejected")
        # Reject cleanup that would erase the newer authoritative round.
        with self.assertRaises(ConflictError):
            # Attempt the stale recovery cleanup.
            game._save("atomic-player", rejected)
        # Preserve the already-published winning terminal row.
        self.assertEqual(["teen-winner"], [row["round_id"] for row in repository.document["recent_rounds"]])

    # Prove two stale fresh processes produce one winner and one conflict.
    def test_fresh_process_round_race_preserves_sibling(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve the disposable JSON provider data root.
            data_root = Path(temporary) / "data"
            # Resolve this player's exact Teen Patti state document.
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
from casino.games.teen_patti import service
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
game = service.TeenPattiService(ledger_gateway=object(), get_player=lambda player_id: {'player_id': player_id, 'balance': 100.0})
state = game._load('atomic-player')
state['recent_rounds'].append({'round_id': f'teen-{tag}', 'phase': 'settled', 'payout': 0.0})
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Teen Patti atomic race release timed out')
try:
    game._save('atomic-player', state)
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
            # Read the still-unmodified document after both stale loads.
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
            # Require exactly one publication and one stale conflict.
            self.assertEqual(["CONFLICT", "PASS"], outcomes)
            # Read the single provider-authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exactly one winning Teen Patti identity.
            self.assertIn(final["recent_rounds"][0]["round_id"], {"teen-alpha", "teen-beta"})
            # Preserve the unrelated sibling through the winning provider update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Reject private optimistic metadata from persistent JSON bytes.
            self.assertNotIn(service._ATOMIC_BASELINE_KEY, final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
