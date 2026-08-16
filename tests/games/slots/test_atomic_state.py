# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Slots state. (SLOT-038, TEST-231)"""

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
# Import mock support for the provider-current callback seam.
from unittest import mock
# Import portable paths for repository and fixture identities.
from pathlib import Path

# Import the public stale-writer error for exact fail-closed assertions.
from casino.errors import ConflictError
# Import production state helpers and Slots-owned state rules.
from casino.games.slots import api, engine


# Simulate provider-current player documents for deterministic callback tests.
class MemoryUpdater:
    # Start with one optional detached provider document.
    def __init__(self, document=None):
        # Retain only provider bytes, never caller-owned references.
        self.document = copy.deepcopy(document or engine.default_state())
        # Count callbacks to prove invalid transitions fail before storage.
        self.update_calls = 0

    # Load one detached provider document.
    def load(self, _game_id, _player_id, _factory):
        # Return a copy so caller mutation cannot bypass update.
        return copy.deepcopy(self.document)

    # Apply one callback against exact current provider state.
    def update(self, _game_id, _player_id, mutator, _factory):
        # Record one provider-bound mutation attempt.
        self.update_calls += 1
        # Execute the production callback against a detached current document.
        updated = mutator(copy.deepcopy(self.document))
        # Persist only the callback result after successful validation.
        self.document = copy.deepcopy(updated)
        # Return a detached authoritative result.
        return copy.deepcopy(updated)


# Prove provider-current comparison and stale-writer rejection locally and across processes.
class SlotsAtomicStateTests(unittest.TestCase):
    # Build one compact deterministic result row for publication fixtures.
    @staticmethod
    def _spin_row(round_id: str) -> dict:
        # Return enough immutable identity to distinguish competing publications.
        return {"round_id": round_id, "cost": 1.0, "payout": 0.0}

    # Patch production storage seams to one provider-shaped in-memory document.
    @staticmethod
    def _patch_storage(repository: MemoryUpdater):
        # Return both exact state-store patches as one nested context manager.
        return (
            mock.patch.object(api, "load_player_game_state", side_effect=repository.load),
            mock.patch.object(api, "update_player_game_state", side_effect=repository.update),
        )

    # Reject fabricated detached state before entering provider storage.
    def test_missing_baseline_fails_before_storage(self) -> None:
        # Build one empty provider-shaped document.
        repository = MemoryUpdater()
        # Route only provider updates through the deterministic seam.
        with mock.patch.object(api, "update_player_game_state", side_effect=repository.update):
            # Reject state that did not originate from the tracked loader.
            with self.assertRaises(ConflictError):
                # Attempt to publish an untracked default document.
                api._save_state("atomic-player", engine.default_state())
        # Prove storage never saw the invalid publication.
        self.assertEqual(0, repository.update_calls)

    # Preserve sibling fields when the desired game bytes already won.
    def test_identical_publication_is_idempotent_and_preserves_sibling(self) -> None:
        # Build production helpers over one default provider document.
        repository = MemoryUpdater()
        # Resolve the exact read and update patch pair.
        load_patch, update_patch = self._patch_storage(repository)
        # Exercise the production optimistic helpers with provider-shaped callbacks.
        with load_patch, update_patch:
            # Capture a tracked provider state.
            state = api._load_state("atomic-player")
            # Publish unrelated provider metadata after the tracked read.
            repository.document["atomic_markers"] = ["sibling"]
            # Accept the identical game-owned state without replacing the document.
            api._save_state("atomic-player", state)
        # Preserve unrelated provider metadata exactly.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])
        # Keep private optimistic metadata outside storage.
        self.assertNotIn("_slots_atomic_baseline", repository.document)
        # Keep private optimistic metadata outside the frozen v1 state payload.
        self.assertNotIn("_slots_atomic_baseline", api._public_state(state))

    # Publish optional bonus state and its later authoritative deletion exactly.
    def test_optional_game_fields_are_compared_and_deleted_atomically(self) -> None:
        # Seed both optional historical fields beside one unrelated sibling.
        repository = MemoryUpdater({**engine.default_state(), "free_spin_basis": {"active_lines": 20, "line_bet": 1.0}, "progressive_meters": {"20:1.00": 250.0}, "atomic_markers": ["sibling"]})
        # Resolve the exact read and update patch pair.
        load_patch, update_patch = self._patch_storage(repository)
        # Exercise tracked deletion through the provider callback.
        with load_patch, update_patch:
            # Load both optional fields into the optimistic baseline.
            state = api._load_state("atomic-player")
            # Model feature completion removing the trusted bonus basis.
            state.pop("free_spin_basis")
            # Model legacy progressive-map migration to the scalar field.
            state.pop("progressive_meters")
            # Publish both deletions without replacing sibling metadata.
            api._save_state("atomic-player", state)
        # Prove both optional game fields were removed authoritatively.
        self.assertNotIn("free_spin_basis", repository.document)
        # Prove the legacy optional meter map was removed authoritatively.
        self.assertNotIn("progressive_meters", repository.document)
        # Preserve the unrelated provider sibling through both deletions.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])

    # Reject one stale spin after another action wins.
    def test_stale_spin_publication_conflicts(self) -> None:
        # Seed one common empty state for competing actions.
        repository = MemoryUpdater()
        # Resolve the exact read and update patch pair.
        load_patch, update_patch = self._patch_storage(repository)
        # Exercise competing tracked copies through the same provider document.
        with load_patch, update_patch:
            # Capture two independently stale copies.
            first = api._load_state("atomic-player")
            # Capture another operation before either publishes.
            second = api._load_state("atomic-player")
            # Prepare the first action's settled result.
            first["last_spins"].append(self._spin_row("slot-alpha"))
            # Prepare a different action against the stale baseline.
            second["last_spins"].append(self._spin_row("slot-beta"))
            # Commit the first publication.
            api._save_state("atomic-player", first)
            # Reject the incompatible stale second publication.
            with self.assertRaises(ConflictError):
                # Attempt to overwrite the winning recent-spin history.
                api._save_state("atomic-player", second)
        # Preserve only the winning action identity.
        self.assertEqual("slot-alpha", repository.document["last_spins"][0]["round_id"])

    # Prevent stale action-owned cleanup from erasing a newer publication.
    def test_stale_cleanup_cannot_erase_concurrent_winner(self) -> None:
        # Seed one empty shared provider state.
        repository = MemoryUpdater()
        # Resolve the exact read and update patch pair.
        load_patch, update_patch = self._patch_storage(repository)
        # Exercise sequential winner and stale cleanup publications.
        with load_patch, update_patch:
            # Load the operation state that will later attempt cleanup.
            rejected = api._load_state("atomic-player")
            # Add the first operation's result before publishing it.
            rejected["last_spins"].append(self._spin_row("slot-rejected"))
            # Commit the first result and advance its tracked baseline.
            api._save_state("atomic-player", rejected)
            # Load that result for a newer authoritative publication.
            winning = api._load_state("atomic-player")
            # Append the newer action without removing the earlier result.
            winning["last_spins"].append(self._spin_row("slot-winner"))
            # Publish the newer complete history.
            api._save_state("atomic-player", winning)
            # Model rejected-operation cleanup from its now-stale baseline.
            rejected["last_spins"] = []
            # Reject cleanup that would erase the newer authoritative action.
            with self.assertRaises(ConflictError):
                # Attempt the stale action-owned cleanup.
                api._save_state("atomic-player", rejected)
        # Preserve both already-published authoritative rows.
        self.assertEqual(["slot-rejected", "slot-winner"], [row["round_id"] for row in repository.document["last_spins"]])

    # Prove two stale fresh processes produce one spin winner and one conflict.
    def test_fresh_process_spin_race_preserves_sibling(self) -> None:
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
from casino.games.slots import api
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
state = api._load_state('atomic-player')
state['last_spins'].append({'round_id': f'slot-{tag}', 'cost': 1.0, 'payout': 0.0})
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Slots atomic race release timed out')
try:
    api._save_state('atomic-player', state)
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
            # Require exactly one winning spin identity.
            self.assertIn(final["last_spins"][0]["round_id"], {"slot-alpha", "slot-beta"})
            # Preserve the unrelated sibling through the winning provider update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Reject private optimistic metadata from persistent JSON bytes.
            self.assertNotIn("_slots_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
