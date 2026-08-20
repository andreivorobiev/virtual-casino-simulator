# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Multi-Hand Video Poker state."""

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

# Import the production engine for canonical round construction.
from casino.games.multi_hand_video_poker import engine


# Prove every game-state transition uses the provider-owned latest document. (MHVP-007, TEST-201)
class MultiHandVideoPokerAtomicStateTests(unittest.TestCase):
    # Build one wager-proven hold-phase round without touching a wallet.
    def _initial_state(self) -> dict:
        # Start from the exact game-owned default document.
        state = engine.default_state()
        # Create one deterministic three-hand round with persisted replacement pools.
        round_state = engine.create_round(
            "atomic-player",  # Bind the round to the isolated fixture player.
            3,  # Use the smallest supported hand count for compact state.
            1,  # Retain exact one-token-per-hand economics.
            "atomic-request",  # Bind one stable request identity.
            seed="mhvp-atomic",  # Produce repeatable cards across child processes.
            round_id="mhvp-atomic",  # Use one fixed route and lookup identity.
            created_at="2026-08-14T00:00:00Z",  # Avoid clock-owned fixture drift.
        )
        # Mark the aggregate debit complete so hold and draw are actionable.
        round_state["wager_status"] = "complete"
        # Preserve one immutable proof identifier without creating a ledger row.
        round_state["wager_ledger_id"] = "led-wager-atomic"
        # Publish the exact actionable round in the normal active slot.
        state["active_round"] = round_state
        # Return the complete production state shape.
        return state

    # Create one isolated JSON provider root and exact child environment.
    def _fixture(self, temporary: str) -> tuple[Path, Path, dict]:
        # Resolve the disposable provider data root.
        data_root = Path(temporary) / "data"
        # Resolve this player's exact game-state document.
        state_path = data_root / "games" / "multi_hand_video_poker" / "atomic-player.json"
        # Create the player-game directory before publishing the fixture.
        state_path.parent.mkdir(parents=True, exist_ok=True)
        # Persist one common pre-race state for every child.
        state_path.write_text(json.dumps(self._initial_state()), encoding="utf-8")
        # Resolve the exact checkout used for child imports.
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
        # Return all identities needed by the race harness.
        return repository_root, state_path, environment

    # Start two fresh workers only after both own the same stale pre-release snapshot.
    def _run_workers(self, repository_root: Path, environment: dict, temporary_root: Path, modes: tuple[str, str], process_pool: ProcessRacePool) -> list[str]:
        # Define a dependency-free worker using production state and engine boundaries.
        worker_source = """
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import NotFoundError
from casino.games.multi_hand_video_poker import api, engine
load_player_game_state('multi_hand_video_poker', 'atomic-player', engine.default_state)
mode = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
sequence_path = Path(sys.argv[4])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Multi-Hand Video Poker atomic race release timed out')
def credit(player_id, amount, transaction_type, game=None, round_id=None, details=None):
    return {'ledger_id': 'led-payout-atomic', 'player_id': player_id, 'amount': amount, 'transaction_type': transaction_type, 'game': game, 'round_id': round_id, 'details': details or {}}
service = api.MultiHandVideoPokerService(credit=credit, read_ledger=lambda player_id=None, limit=100: [], get_player=lambda player_id: {'player_id': player_id, 'balance': 97.0}, clock=lambda: '2026-08-14T00:01:00Z')
if mode == 'hold':
    service.set_holds('atomic-player', 'mhvp-atomic', [0])
elif mode == 'sibling':
    def mark(current):
        current.setdefault('atomic_markers', []).append('sibling')
        return current
    update_player_game_state('multi_hand_video_poker', 'atomic-player', mark, engine.default_state)
elif mode == 'hold-first':
    service.set_holds('atomic-player', 'mhvp-atomic', [0])
    sequence_path.write_text('hold', encoding='utf-8')
elif mode == 'draw-after-hold':
    sequence_deadline = time.monotonic() + 10
    while not sequence_path.exists() and time.monotonic() < sequence_deadline:
        time.sleep(0.01)
    if not sequence_path.exists():
        raise RuntimeError('Hold-first ordering marker timed out')
    service.draw('atomic-player', 'mhvp-atomic')
elif mode == 'draw-first':
    service.draw('atomic-player', 'mhvp-atomic')
    sequence_path.write_text('draw', encoding='utf-8')
elif mode == 'hold-after-draw':
    sequence_deadline = time.monotonic() + 10
    while not sequence_path.exists() and time.monotonic() < sequence_deadline:
        time.sleep(0.01)
    if not sequence_path.exists():
        raise RuntimeError('Draw-first ordering marker timed out')
    try:
        service.set_holds('atomic-player', 'mhvp-atomic', [0])
    except NotFoundError:
        print('not-found')
    else:
        raise RuntimeError('Stale hold resurrected a settled round')
else:
    raise RuntimeError('Unknown atomic race mode')
"""
        # Resolve one release marker shared by the exact worker pair.
        go_path = temporary_root / ("go-" + "-".join(modes))
        # Resolve one sequencing marker used by ordered hold/draw proofs.
        sequence_path = temporary_root / ("sequence-" + "-".join(modes))
        # Retain child handles and their unique readiness files.
        processes = []
        # Launch both workers without a shell or shared Python process.
        for index, mode in enumerate(modes):
            # Allocate one readiness marker for this child.
            ready_path = temporary_root / f"ready-{index}-{mode}"
            # Start the exact interpreter with bounded pipe capture.
            process = process_pool.spawn([sys.executable, "-c", worker_source, mode, str(ready_path), str(go_path), str(sequence_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Retain the process and marker for rendezvous validation.
            processes.append((process, ready_path))
        # Bound the stale-load rendezvous so a broken child cannot hang CI.
        deadline = time.monotonic() + 10
        # Wait until both children have loaded the same initial document.
        while not all(ready.exists() for _, ready in processes) and time.monotonic() < deadline:
            # Stop early when a child exits before claiming readiness.
            if any(process.poll() is not None for process, _ in processes):
                # Leave the loop for the explicit diagnostic assertion.
                break
            # Yield briefly without changing worker order.
            time.sleep(0.01)
        # Require a complete stale-state rendezvous before release.
        process_pool.wait_until_ready([(process, ready) for process, ready in processes], timeout=0)
        # Release both prepared workers exactly once.
        go_path.write_text("go", encoding="utf-8")
        # Collect bounded diagnostics and final exit codes.
        completed = [(*process.communicate(timeout=20), process.returncode) for process, _ in processes]
        # Require every legal transition or expected refusal to complete.
        for standard_output, standard_error, return_code in completed:
            # Preserve output only when the child violates the proof.
            self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
        # Return normalized child results for exact refusal evidence.
        return [standard_output.strip() for standard_output, _standard_error, _return_code in completed]

    # Prove a hold transition and unrelated sibling publication both survive stale loads.
    def test_hold_preserves_concurrent_sibling_update(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Build exact checkout, state, and child environment bindings.
            repository_root, state_path, environment = self._fixture(temporary)
            # Race one real hold transition against an unrelated top-level marker.
            self._run_workers(repository_root, environment, Path(temporary), ("hold", "sibling"), process_pool)
            # Read the single provider-authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require the hold and sibling marker together with the unchanged wager proof.
            self.assertEqual(([0], ["sibling"], "complete", "led-wager-atomic"), (final["active_round"]["holds"], final["atomic_markers"], final["active_round"]["wager_status"], final["active_round"]["wager_ledger_id"]))

    # Prove a committed hold is consumed by a later draw despite both stale preloads.
    def test_hold_then_draw_uses_provider_latest_selection(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Build exact checkout, state, and child environment bindings.
            repository_root, state_path, environment = self._fixture(temporary)
            # Force hold publication before the already-loaded draw request proceeds.
            outcomes = self._run_workers(repository_root, environment, Path(temporary), ("hold-first", "draw-after-hold"), process_pool)
            # Read the authoritative archived round after both transitions.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require both workers to complete without fallback output.
            self.assertEqual(["", ""], outcomes)
            # Require draw to consume the latest hold and archive exactly one round.
            self.assertEqual((None, 1, [0], "settled"), (final["active_round"], len(final["recent_rounds"]), final["recent_rounds"][-1]["holds"], final["recent_rounds"][-1]["phase"]))

    # Prove a committed draw makes an already-loaded stale hold non-actionable.
    def test_draw_then_hold_refuses_round_resurrection(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Build exact checkout, state, and child environment bindings.
            repository_root, state_path, environment = self._fixture(temporary)
            # Force draw publication before the already-loaded hold request proceeds.
            outcomes = self._run_workers(repository_root, environment, Path(temporary), ("draw-first", "hold-after-draw"), process_pool)
            # Read the authoritative terminal document after the expected refusal.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require only the stale hold worker to report its fixed refusal marker.
            self.assertEqual(["", "not-found"], outcomes)
            # Require no active-round resurrection and one unchanged settled history item.
            self.assertEqual((None, 1, [], "settled"), (final["active_round"], len(final["recent_rounds"]), final["recent_rounds"][-1]["holds"], final["recent_rounds"][-1]["phase"]))


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
