# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Mississippi Stud state. (MSTUD-003, TEST-226)"""

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

# Import production state helpers used to construct an actionable round.
from casino.games.mississippi_stud import engine, service


# Prove stale processes publish through the provider-owned latest document.
class MississippiStudAtomicStateTests(unittest.TestCase):
    # Build one first-street round shared by both stale workers.
    def _initial_state(self) -> dict:
        # Start from the exact game-owned default document.
        state = engine.default_state()
        # Bind the opening request to one stable semantic fingerprint.
        fingerprint = service.request_fingerprint({"stage": "deal", "ante": 1.0})
        # Prepare one deterministic opening round without a wallet call.
        round_state = engine.create_round("atomic-player", 1, "atomic-deal-0001", round_id="mstud_atomic_round", created_at="2026-08-16T00:00:00Z", request_fingerprint=fingerprint, fixture={"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]})
        # Mark the opening wager already committed so only state publication races.
        round_state["opening_status"] = "complete"
        # Retain one stable opening ledger identifier.
        round_state["opening_ledger_id"] = "atomic-ante-ledger"
        # Publish the actionable round in the game-owned slot.
        state["active_round"] = round_state
        # Retain the durable opening receipt exactly as the service does.
        state["action_receipts"]["atomic-deal-0001"] = {"stage": "deal", "round_id": "mstud_atomic_round", "request_fingerprint": fingerprint}
        # Return the complete first-street production state.
        return state

    # Prove two stale fresh processes produce one terminal winner and one conflict.
    def test_fresh_process_terminal_race_preserves_sibling_and_never_resurrects(self) -> None:
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
from casino.games.mississippi_stud import engine, service
tag = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
game = service.MississippiStudService()
state = game._load('atomic-player')
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Mississippi Stud atomic race release timed out')
round_state = state['active_round']
action_id = f'atomic-fold-{tag}-0001'
fingerprint = service.request_fingerprint({'stage': 'decision', 'round_id': 'mstud_atomic_round', 'street': 1, 'decision': 'fold'})
engine.fold_round(round_state, action_id, completed_at=f'2026-08-16T00:0{1 if tag == "alpha" else 2}:00Z', request_fingerprint=fingerprint)
engine.archive_round(state, round_state)
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
            # Require the active slot to remain retired after the terminal winner.
            self.assertIsNone(final["active_round"])
            # Require exactly one retained terminal result with one winning fold identity.
            self.assertEqual((1, "settled"), (len(final["recent_rounds"]), final["recent_rounds"][0]["phase"]))
            # Preserve the unrelated sibling through the winning provider-current update.
            self.assertEqual(["sibling"], final["atomic_markers"])
            # Retain only the original opening action receipt.
            self.assertEqual(["atomic-deal-0001"], sorted(final["action_receipts"]))
            # Reject the private optimistic baseline from persistent JSON bytes.
            self.assertNotIn("_mississippi_stud_atomic_baseline", final)


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
