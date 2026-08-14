# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for Baccarat committed-coup state transitions."""

# Import JSON support for the shared durable fixture and result inspection.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for fresh independent Python workers.
import subprocess
# Import the active interpreter used by the repository test runner.
import sys
# Import temporary directories for task-owned state and rendezvous files.
import tempfile
# Import bounded polling for child-process readiness.
import time
# Import the standard unit-test framework used by the central runner.
import unittest
# Import portable paths for repository, state, and rendezvous ownership.
from pathlib import Path
# Import patching support for provider-neutral helper isolation.
from unittest import mock

# Import the expected fail-closed error for divergent commitments.
from casino.errors import ConflictError
# Import the production Baccarat API helpers for direct idempotence assertions.
from casino.games.baccarat import api


# Prove Baccarat pending commitments, consumed shoes, and terminal history use atomic state. (TEST-192)
class BaccaratAtomicStateTests(unittest.TestCase):
    # Run one pair of fresh workers after both have loaded the same stale state document.
    def _run_pair(self, repository_root: Path, environment: dict, temporary_root: Path, first_mode: str, second_mode: str) -> None:
        # Define one dependency-free worker that preloads state before its atomic transition.
        worker_source = """
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.games.baccarat import api, engine
state = load_player_game_state('baccarat', 'atomic-player', engine.default_state)
mode = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Baccarat atomic race release timed out')
if mode == 'commit':
    api.commit_pending_coup('atomic-player', state)
elif mode == 'finalize':
    api.finalize_committed_coup_state('atomic-player', state, state['pending_coup'])
else:
    def mark(current):
        current.setdefault('atomic_markers', []).append(mode)
        return current
    update_player_game_state('baccarat', 'atomic-player', mark, engine.default_state)
"""
        # Resolve one release file shared by this process pair only.
        go_path = temporary_root / f"go-{first_mode}-{second_mode}"
        # Retain child handles and readiness files for bounded diagnostics.
        processes = []
        # Start both workers against the same preloaded durable document.
        for index, mode in enumerate((first_mode, second_mode)):
            # Give each child an independent readiness marker.
            ready_path = temporary_root / f"ready-{first_mode}-{second_mode}-{index}"
            # Launch without a shell so argument and interpreter identity stay exact.
            process = subprocess.Popen([sys.executable, "-c", worker_source, mode, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Retain the worker alongside its readiness path.
            processes.append((process, ready_path))
        # Bound the stale-load rendezvous so a failed child cannot hang the suite.
        deadline = time.monotonic() + 10
        # Wait until both children have loaded before allowing either update.
        while not all(ready.exists() for _, ready in processes) and time.monotonic() < deadline:
            # Stop early when a child exits before declaring readiness.
            if any(process.poll() is not None for process, _ in processes):
                # Leave the loop so the explicit assertion reports the failure.
                break
            # Yield briefly without broadening the deterministic schedule.
            time.sleep(0.01)
        # Require both stale loads before releasing their competing transitions.
        self.assertTrue(all(ready.exists() for _, ready in processes))
        # Release the exact process pair once.
        go_path.write_text("go", encoding="utf-8")
        # Collect bounded diagnostics from each child.
        completed = [(*process.communicate(timeout=15), process.returncode) for process, _ in processes]
        # Require both workers to complete through the production atomic helper.
        for standard_output, standard_error, return_code in completed:
            # Preserve child diagnostics only when an assertion fails.
            self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")

    # Prove pending commit and terminal finalization preserve sibling fields and consume one shoe segment.
    def test_pending_commit_and_finalization_preserve_concurrent_process_updates(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the isolated JSON provider data root.
            data_root = Path(temporary) / "data"
            # Resolve the exact Baccarat player document used by both worker pairs.
            state_path = data_root / "games" / "baccarat" / "atomic-player.json"
            # Create the parent before publishing the deterministic pre-coup state.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Build one complete open bet consumed by the committed coup.
            bet = {"bet_id": "bet-atomic", "player_id": "atomic-player", "type": "player", "label": "Player", "amount": 5.0, "source": "manual"}
            # Seed a twenty-four-card shoe whose top four cards produce a natural Player win.
            shoe = ["3C"] * 20 + ["2D", "KS", "5H", "9S"]
            # Seed the complete production state shape without a pending commitment.
            initial = {"rules": {"decks": 8, "tie_payout": 8, "banker_commission": 0.05, "tie_behavior": "push", "cut_cards_remaining": 14}, "shoe": shoe, "shoe_id": "shoe-atomic", "coup_number": 0, "open_bets": [bet], "last_coups": []}
            # Publish the deterministic starting document for both processes.
            state_path.write_text(json.dumps(initial), encoding="utf-8")
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[4]
            # Copy the caller environment before replacing runtime-owned paths.
            environment = os.environ.copy()
            # Select the disposable provider root in both fresh interpreters.
            environment["CASINO_DATA_DIR"] = str(data_root)
            # Keep child logs inside the same disposable owner boundary.
            environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
            # Require the JSON provider so the cross-process file lock is exercised.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Bind imports to this exact worktree.
            environment["PYTHONPATH"] = str(repository_root)
            # Race pending commitment against one unrelated atomic marker.
            self._run_pair(repository_root, environment, Path(temporary), "commit", "commit-sibling")
            # Read the authoritative state after both stale workers publish.
            committed = json.loads(state_path.read_text(encoding="utf-8"))
            # Require the committed coup and sibling marker to coexist.
            self.assertEqual(("commit-sibling", 20), (committed["atomic_markers"][0], len(committed["shoe"])))
            # Capture the exact round identity used by terminal finalization.
            round_id = committed["pending_coup"]["round_id"]
            # Race terminal finalization against a second unrelated atomic marker.
            self._run_pair(repository_root, environment, Path(temporary), "finalize", "finalize-sibling")
            # Read the final provider-published state after both workers exit.
            finalized = json.loads(state_path.read_text(encoding="utf-8"))
            # Require both independent sibling updates to survive the two state transitions.
            self.assertEqual(finalized["atomic_markers"], ["commit-sibling", "finalize-sibling"])
            # Require the exact committed coup once in terminal history.
            self.assertEqual([item["round_id"] for item in finalized["last_coups"]], [round_id])
            # Require the pending commitment and settled bets to be cleared.
            self.assertNotIn("pending_coup", finalized)
            # Require no bet from the finalized coup to remain open.
            self.assertEqual(finalized["open_bets"], [])
            # Require the committed four-card natural to consume the shoe exactly once.
            self.assertEqual(len(finalized["shoe"]), 20)

    # Prove exact terminal replays are idempotent and aliased or divergent coups fail closed.
    def test_terminal_finalization_replay_is_exact_and_divergence_fails_closed(self) -> None:
        # Build one complete coup identity for an already terminal in-memory state.
        coup = {"round_id": "coup-terminal", "bets": [], "player_cards": ["9S", "KS"], "banker_cards": ["5H", "2D"]}
        # Capture calls to the shared atomic helper without selecting real storage.
        with mock.patch.object(api, "update_player_game_state") as update:
            # Execute the supplied mutator against an already finalized document.
            update.side_effect = lambda game_id, player_id, mutator, default: mutator({"open_bets": [], "last_coups": [coup]})
            # Retain a caller-owned stale snapshot for refresh evidence.
            state = {"pending_coup": coup}
            # Repeat finalization after another process already completed it.
            api.finalize_committed_coup_state("atomic-player", state, coup)
            # Require the authoritative terminal document without a duplicate history row.
            self.assertEqual([item["round_id"] for item in state["last_coups"]], ["coup-terminal"])
            # Replace the provider result with a same-id terminal coup whose card bytes diverge.
            update.side_effect = lambda game_id, player_id, mutator, default: mutator({"open_bets": [], "last_coups": [{**coup, "player_cards": ["8S"]}]})
            # Refuse round-id aliasing because only the complete committed coup is replay-safe.
            with self.assertRaises(ConflictError):
                # Attempt finalization with the stale original coup.
                api.finalize_committed_coup_state("atomic-player", state, coup)
            # Replace the provider result with a different live pending commitment.
            update.side_effect = lambda game_id, player_id, mutator, default: mutator({"open_bets": [], "last_coups": [], "pending_coup": {"round_id": "coup-other"}})
            # Refuse to clear or finalize the unrelated racing commitment.
            with self.assertRaises(ConflictError):
                # Attempt finalization with the stale original coup.
                api.finalize_committed_coup_state("atomic-player", state, coup)


# Run the focused module suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
