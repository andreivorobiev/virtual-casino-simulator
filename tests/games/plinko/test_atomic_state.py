# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Plinko state. (PLINKO-006, TEST-227)"""

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
# Import production state helpers used to construct committed drops.
from casino.games.plinko import engine, service


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


# Prove provider-current comparison and stale-writer rejection locally.
class PlinkoAtomicStateTests(unittest.TestCase):
    # Build one deterministic completed drop for state-only publication.
    @staticmethod
    def _drop(tag: str) -> dict:
        # Bind one exact client action identity to this fixture.
        action_id = f"atomic-drop-{tag}"
        # Bind the persisted drop to one normalized semantic request.
        fingerprint = service.request_fingerprint({"stage": "drop", "wager": 2.0})
        # Derive one deterministic eight-step route without production randomness.
        path = engine.committed_path(seed=f"atomic:{tag}")
        # Construct the same terminal object used by production preparation.
        drop = engine.create_drop("atomic-player", 2, action_id, path=path, drop_id=f"plinko_atomic_{tag}", created_at="2026-08-16T00:00:00Z", request_fingerprint=fingerprint)
        # Mark both money stages complete so this fixture tests state ordering only.
        drop["debit_status"] = "complete"
        # Mark returned-token settlement complete without invoking a ledger.
        drop["settlement_status"] = "complete"
        # Return the complete game-owned fixture.
        return drop

    # Publish one fixture drop and its durable receipt into tracked state.
    @classmethod
    def _archive(cls, state: dict, tag: str) -> None:
        # Build the deterministic terminal drop.
        drop = cls._drop(tag)
        # Add the drop to the bounded public history.
        engine.archive_drop(state, drop)
        # Retain the action identity after public history pruning.
        state.setdefault("action_receipts", {})[drop["action_id"]] = {"stage": "drop", "drop_id": drop["drop_id"], "request_fingerprint": drop["request_fingerprint"]}

    # Reject fabricated detached state before entering provider storage.
    def test_missing_baseline_fails_before_storage(self) -> None:
        # Create one empty provider document.
        repository = MemoryRepository()
        # Build production state orchestration over the fake provider.
        game = service.PlinkoService(repository=repository)
        # Reject state that did not originate from the tracked loader.
        with self.assertRaises(ConflictError):
            # Attempt to publish an untracked default document.
            game._save("atomic-player", engine.default_state())
        # Prove storage never saw the invalid publication.
        self.assertEqual(0, repository.update_calls)

    # Preserve sibling fields when the desired game bytes already won.
    def test_identical_publication_is_idempotent_and_preserves_sibling(self) -> None:
        # Create one empty provider document.
        repository = MemoryRepository()
        # Build production state orchestration over the fake provider.
        game = service.PlinkoService(repository=repository)
        # Capture a tracked default state.
        state = game._load("atomic-player")
        # Publish unrelated provider metadata after the tracked read.
        repository.document["atomic_markers"] = ["sibling"]
        # Accept the identical game-owned state without replacing the document.
        game._save("atomic-player", state)
        # Preserve unrelated provider metadata exactly.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])
        # Keep private optimistic metadata outside storage.
        self.assertNotIn("_plinko_atomic_baseline", repository.document)

    # Reject one stale different terminal writer after a winner commits.
    def test_stale_different_publication_conflicts(self) -> None:
        # Create one empty provider document.
        repository = MemoryRepository()
        # Build production state orchestration over the fake provider.
        game = service.PlinkoService(repository=repository)
        # Capture two independently stale copies.
        first = game._load("atomic-player")
        # Capture another operation before either publishes.
        second = game._load("atomic-player")
        # Prepare the first terminal drop.
        self._archive(first, "alpha")
        # Prepare a different terminal drop from the same baseline.
        self._archive(second, "beta")
        # Commit the first operation through the provider callback.
        game._save("atomic-player", first)
        # Reject the incompatible stale second operation.
        with self.assertRaises(ConflictError):
            # Attempt to overwrite the winning game history.
            game._save("atomic-player", second)
        # Preserve only the winning terminal drop.
        self.assertEqual(["plinko_atomic_alpha"], [row["drop_id"] for row in repository.document["recent_drops"]])

    # Prevent rejected-debit cleanup from erasing a concurrent winner.
    def test_stale_cleanup_cannot_erase_concurrent_winner(self) -> None:
        # Create one empty provider document.
        repository = MemoryRepository()
        # Build production state orchestration over the fake provider.
        game = service.PlinkoService(repository=repository)
        # Load and publish one prepared action as production does before debit.
        rejected = game._load("atomic-player")
        # Add the soon-to-be-rejected preparation.
        self._archive(rejected, "rejected")
        # Commit the prepared recovery state.
        game._save("atomic-player", rejected)
        # Load the prepared state for a different concurrent winner.
        winning = game._load("atomic-player")
        # Add a distinct winning drop after preparation.
        self._archive(winning, "winner")
        # Publish the authoritative concurrent winner.
        game._save("atomic-player", winning)
        # Model action-owned cleanup after the original debit rejects.
        rejected["recent_drops"] = [row for row in rejected["recent_drops"] if row.get("drop_id") != "plinko_atomic_rejected"]
        # Release only the original rejected action receipt.
        rejected["action_receipts"].pop("atomic-drop-rejected", None)
        # Reject cleanup based on the superseded prepared baseline.
        with self.assertRaises(ConflictError):
            # Attempt the stale cleanup publication.
            game._save("atomic-player", rejected)
        # Preserve the concurrent winning drop in provider state.
        self.assertEqual("plinko_atomic_winner", repository.document["recent_drops"][-1]["drop_id"])

    # Prove two stale fresh processes produce one winner and one conflict.
    def test_fresh_process_terminal_race_preserves_sibling(self) -> None:
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
from casino.games.plinko import engine, service
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
game = service.PlinkoService()
state = game._load('atomic-player')
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Plinko atomic race release timed out')
action_id = f'atomic-drop-{tag}'
fingerprint = service.request_fingerprint({'stage': 'drop', 'wager': 2.0})
path = engine.committed_path(seed=f'atomic:{tag}')
drop = engine.create_drop('atomic-player', 2, action_id, path=path, drop_id=f'plinko_atomic_{tag}', created_at='2026-08-16T00:00:00Z', request_fingerprint=fingerprint)
drop['debit_status'] = 'complete'
drop['settlement_status'] = 'complete'
engine.archive_drop(state, drop)
state.setdefault('action_receipts', {})[action_id] = {'stage': 'drop', 'drop_id': drop['drop_id'], 'request_fingerprint': fingerprint}
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
            # Require exactly one publication and one stale conflict.
            self.assertEqual(["CONFLICT", "PASS"], outcomes)
            # Read the single provider-authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exactly one terminal drop and its matching receipt.
            self.assertEqual((1, 1), (len(final["recent_drops"]), len(final["action_receipts"])))
            # Preserve the unrelated sibling through the winning provider update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Reject private optimistic metadata from persistent JSON bytes.
            self.assertNotIn("_plinko_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
