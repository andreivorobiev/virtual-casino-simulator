# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Scratch Cards state. (SCRATCH-006, TEST-229)"""

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
from casino.games.scratch_cards import engine
from casino.games.scratch_cards.service import ScratchCardsService


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
class ScratchCardsAtomicStateTests(unittest.TestCase):
    # Build one private ready card shared by competing reveal publications.
    @staticmethod
    def _initial_state() -> dict:
        # Start from the exact game-owned default document.
        state = engine.default_state()
        # Create one deterministic private board without invoking the ledger.
        card = {
            "card_id": "scratch_atomic_card",  # Bind one stable card identity.
            "client_request_id": "scratch-atomic-purchase",  # Preserve the purchase retry identity.
            "request_fingerprint": engine.purchase_fingerprint(1.0),  # Bind the wager meaning.
            "player_id": "atomic-player",  # Scope the private card to the fixture player.
            "status": "ready",  # Make independent partial reveals legal.
            "wager": 1.0,  # Retain the funded play-token amount.
            "revealed_positions": [],  # Begin with every cell covered.
            "scratch_actions": {},  # Begin with no immutable reveal identity.
            "purchased_at": "2026-08-16T00:00:00Z",  # Pin deterministic audit time.
            "outcome_roll": 0,  # Select the documented no-win tier privately.
            "winning_multiplier": 0,  # Record a losing card outcome.
            "prize_multipliers": [1, 1, 2, 2, 5, 5, 10, 25, 50],  # Keep no third match.
            "prizes": [1.0, 1.0, 2.0, 2.0, 5.0, 5.0, 10.0, 25.0, 50.0],  # Persist covered prizes.
            "payout": 0.0,  # Keep the fixture outside money movement.
            "wager_ledger_id": "scratch-atomic-ledger",  # Mark the purchase funded.
        }
        # Publish the actionable private card into the game-owned state.
        state["current_card"] = card
        # Return the complete provider document.
        return state

    # Reject fabricated detached state before entering provider storage.
    def test_missing_baseline_fails_before_storage(self) -> None:
        # Build production orchestration over one empty provider document.
        repository = MemoryRepository()
        # Construct the service with only the persistence seam exercised.
        service = ScratchCardsService(repository=repository)
        # Reject state that did not originate from the tracked loader.
        with self.assertRaises(ConflictError):
            # Attempt to publish an untracked default document.
            service._save_state("atomic-player", engine.default_state())
        # Prove storage never saw the invalid publication.
        self.assertEqual(0, repository.update_calls)

    # Preserve sibling fields when the desired game bytes already won.
    def test_identical_publication_is_idempotent_and_preserves_sibling(self) -> None:
        # Build production orchestration over one private ready card.
        repository = MemoryRepository(self._initial_state())
        # Construct the service with only the persistence seam exercised.
        service = ScratchCardsService(repository=repository)
        # Capture a tracked provider state.
        state = service._load_state("atomic-player")
        # Publish unrelated provider metadata after the tracked read.
        repository.document["atomic_markers"] = ["sibling"]
        # Accept the identical game-owned state without replacing the document.
        service._save_state("atomic-player", state)
        # Preserve unrelated provider metadata exactly.
        self.assertEqual(["sibling"], repository.document["atomic_markers"])
        # Keep private optimistic metadata outside storage.
        self.assertNotIn("_scratch_cards_atomic_baseline", repository.document)

    # Reject one stale reveal writer after another reveal wins.
    def test_stale_reveal_publication_conflicts(self) -> None:
        # Seed one shared private ready card.
        repository = MemoryRepository(self._initial_state())
        # Construct the service with only the persistence seam exercised.
        service = ScratchCardsService(repository=repository)
        # Capture two independently stale copies.
        first = service._load_state("atomic-player")
        # Capture another operation before either publishes.
        second = service._load_state("atomic-player")
        # Prepare one partial reveal in the first operation.
        first["current_card"]["revealed_positions"] = [0]
        # Record its immutable action identity privately.
        first["current_card"]["scratch_actions"]["scratch-alpha"] = {"fingerprint": "alpha", "positions": [0]}
        # Prepare a different partial reveal in the stale operation.
        second["current_card"]["revealed_positions"] = [1]
        # Record the competing immutable action identity privately.
        second["current_card"]["scratch_actions"]["scratch-beta"] = {"fingerprint": "beta", "positions": [1]}
        # Commit the first reveal publication.
        service._save_state("atomic-player", first)
        # Reject the incompatible stale second result.
        with self.assertRaises(ConflictError):
            # Attempt to overwrite the winning revealed position.
            service._save_state("atomic-player", second)
        # Preserve only the winning reveal and action record.
        self.assertEqual(([0], ["scratch-alpha"]), (repository.document["current_card"]["revealed_positions"], sorted(repository.document["current_card"]["scratch_actions"])))

    # Prevent action-owned cleanup from erasing a newer publication.
    def test_stale_cleanup_cannot_erase_concurrent_winner(self) -> None:
        # Seed one shared private ready card.
        repository = MemoryRepository(self._initial_state())
        # Construct the service with only the persistence seam exercised.
        service = ScratchCardsService(repository=repository)
        # Load the soon-to-be-rejected operation state.
        rejected = service._load_state("atomic-player")
        # Preserve its exact pre-action game state for cleanup.
        prior = copy.deepcopy(rejected)
        # Publish one prepared reveal for the rejected action.
        rejected["current_card"]["revealed_positions"] = [0]
        # Record its prepared immutable action identity.
        rejected["current_card"]["scratch_actions"]["scratch-rejected"] = {"fingerprint": "rejected", "positions": [0]}
        # Commit the prepared recovery state.
        service._save_state("atomic-player", rejected)
        # Load that preparation for a newer authoritative publication.
        winning = service._load_state("atomic-player")
        # Advance the same card to a newer terminal-style result.
        winning["current_card"]["status"] = "settled"
        # Publish the newer game-owned result.
        service._save_state("atomic-player", winning)
        # Reject cleanup based on the superseded prepared baseline.
        with self.assertRaises(ConflictError):
            # Attempt to restore the original covered card.
            service._restore_state("atomic-player", rejected, prior)
        # Preserve the concurrent terminal result and prepared reveal identity.
        self.assertEqual(("settled", [0]), (repository.document["current_card"]["status"], repository.document["current_card"]["revealed_positions"]))

    # Prove two stale fresh processes produce one reveal winner and one conflict.
    def test_fresh_process_reveal_race_preserves_sibling(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
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
from casino.games.scratch_cards.service import ScratchCardsService
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
service = ScratchCardsService()
state = service._load_state('atomic-player')
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Scratch Cards atomic race release timed out')
position = 0 if tag == 'alpha' else 1
action_id = f'scratch-{tag}'
card = state['current_card']
card['revealed_positions'] = [position]
card['scratch_actions'][action_id] = {'fingerprint': tag, 'positions': [position]}
card['status'] = 'scratching'
try:
    service._save_state('atomic-player', state)
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
            # Require exactly one reveal publication and one stale conflict.
            self.assertEqual(["CONFLICT", "PASS"], outcomes)
            # Read the single provider-authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exactly one revealed position and one winning action record.
            self.assertEqual((1, 1, "scratching"), (len(final["current_card"]["revealed_positions"]), len(final["current_card"]["scratch_actions"]), final["current_card"]["status"]))
            # Preserve the unrelated sibling through the winning provider update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Reject private optimistic metadata from persistent JSON bytes.
            self.assertNotIn("_scratch_cards_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
