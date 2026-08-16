# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Dragon Tiger state. (DT-006, TEST-221)"""

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

# Import the production engine used to build exact persisted state.
from casino.games.dragon_tiger import engine


# Prove stale processes publish through the provider-owned latest document.
class DragonTigerAtomicStateTests(unittest.TestCase):
    # Build one prepared round shared by both stale workers.
    def _initial_state(self) -> dict:
        # Start from the exact game-owned default document.
        state = engine.default_state()
        # Define one complete private prepared action without wallet movement.
        prepared = {
            "round_id": "dt_atomic_round",  # Bind one stable terminal round.
            "action_id": "atomic-action-0001",  # Bind one retry identity.
            "request_fingerprint": "a" * 64,  # Preserve one semantic request.
            "player_id": "atomic-player",  # Bind the fixture owner.
            "status": "wager_committed",  # Model the post-debit recovery stage.
            "bet": "dragon",  # Preserve one normalized wager side.
            "wager": 2.0,  # Preserve one ledger-precision amount.
            "dragon_card": "KS",  # Make Dragon the deterministic winner.
            "tiger_card": "QH",  # Keep the opposing rank lower.
            "winner": "dragon",  # Preserve the computed outcome.
            "outcome": "win",  # Preserve the settlement class.
            "total_return": 4.0,  # Preserve stake plus winnings.
            "net": 2.0,  # Preserve net result.
            "created_at": "2026-08-16T00:00:00Z",  # Pin stable fixture time.
            "shoe_number": 1,  # Bind the prepared round to one shoe.
        }
        # Publish the private action exactly where recovery expects it.
        state["prepared_actions"][prepared["action_id"]] = prepared
        # Preserve recovery order for the same action.
        state["prepared_order"].append(prepared["action_id"])
        # Return the complete production state shape.
        return state

    # Prove two stale fresh processes produce one terminal winner and one conflict.
    def test_fresh_process_terminal_race_preserves_sibling_and_never_resurrects(self) -> None:
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
from casino.games.dragon_tiger import engine, service
mode = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
game_service = service.DragonTigerService()
state = game_service._load('atomic-player')
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Dragon Tiger atomic race release timed out')
prepared = state['prepared_actions']['atomic-action-0001']
round_item = engine.settled_round(prepared, f'2026-08-16T00:0{mode}:00Z')
engine.record_round(state, round_item, {'wager': {'ledger_id': 'atomic-wager'}, 'settlement': {'ledger_id': 'atomic-settlement'}})
try:
    game_service._save('atomic-player', state)
except ConflictError:
    print(f'CONFLICT:{mode}')
else:
    print(f'PASS:{mode}')
"""
            # Resolve one release marker shared by the exact worker pair.
            go_path = Path(temporary) / "go"
            # Retain child handles and their unique readiness files.
            processes = []
            # Launch both workers without a shell or shared Python process.
            for mode in ("1", "2"):
                # Allocate one readiness marker for this child.
                ready_path = Path(temporary) / f"ready-{mode}"
                # Start the exact interpreter with bounded pipe capture.
                process = subprocess.Popen([sys.executable, "-c", worker_source, mode, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
            # Add unrelated provider metadata that both game publications must preserve.
            sibling_state["atomic_markers"] = ["sibling"]
            # Publish the sibling before either stale game transition proceeds.
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
            # Require one terminal history item and no resurrected prepared action.
            self.assertEqual((1, {}, []), (len(final["recent_rounds"]), final["prepared_actions"], final["prepared_order"]))
            # Preserve the unrelated sibling through the winning provider-current update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Retain exactly one winning durable action record.
            self.assertEqual(["atomic-action-0001"], list(final["settled_actions"]))
            # Reject the private optimistic baseline from persistent JSON bytes.
            self.assertNotIn("_dragon_tiger_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
