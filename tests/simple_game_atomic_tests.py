# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Fresh-process provider-atomic evidence for the shared simple-game core. (GAMECORE-005, TEST-233)"""

# Import JSON support for exact durable-state inspection.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for independent stale readers and sibling publication.
import subprocess
# Import the active interpreter used by the repository test runner.
import sys
# Import disposable-directory ownership for provider and rendezvous bytes.
import tempfile
# Import bounded polling for child readiness.
import time
# Import the standard dependency-free test framework.
import unittest
# Import portable paths for repository and fixture identity.
from pathlib import Path


# Prove the shared helper merges distinct rounds against provider-current state across processes.
class SimpleGameAtomicStateTests(unittest.TestCase):
    # Preserve two independently committed rounds and one unrelated sibling publication.
    def test_fresh_process_distinct_rounds_and_sibling_survive(self) -> None:
        # Own all provider and rendezvous bytes inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the exact checkout used by each fresh interpreter.
            repository_root = Path(__file__).resolve().parents[1]
            # Resolve the disposable JSON provider root.
            data_root = Path(temporary) / "data"
            # Resolve this player's exact shared-core state document.
            state_path = data_root / "games" / "unit_flip" / "atomic-player.json"
            # Create the player-game directory before seeding provider state.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish one common baseline that both worker processes must load.
            state_path.write_text(json.dumps({"game": "unit_flip", "recent_rounds": []}, sort_keys=True), encoding="utf-8")
            # Copy the caller environment before selecting isolated runtime paths.
            environment = os.environ.copy()
            # Route every child to the disposable JSON provider and exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one worker that captures stale state before executing a complete losing round.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.simple_game import SimpleWagerGame
from casino.core.state_store import load_player_game_state, update_player_game_state
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
request_id = sys.argv[3]
def default_state():
    return {'game': 'unit_flip', 'recent_rounds': []}
def load_state(player_id):
    current = load_player_game_state('unit_flip', player_id, default_state)
    if not ready.exists():
        ready.write_text('ready', encoding='utf-8')
        deadline = time.monotonic() + 10
        while not release.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not release.exists():
            raise RuntimeError('simple-game release gate timed out')
    return current
def update_state(player_id, mutator):
    return update_player_game_state('unit_flip', player_id, mutator, default_state)
def entropy(randbelow):
    return {'face': randbelow(6) + 1}
def validate(request):
    wager = {'face': int(request['face']), 'stake': int(request['stake'])}
    return wager, float(wager['stake']), f"{wager['face']}:{wager['stake']}"
def resolve(wager, drawn):
    return {'outcome': 'lose', 'total_return': 0, 'detail': {'face': drawn['face']}}
class Gateway:
    def apply_once(self, **kwargs):
        details = {**kwargs['details'], 'ledger_action_key': kwargs['action_key'], 'request_fingerprint': kwargs['request_fingerprint']}
        return {'ledger_id': 'ledger-' + request_id, 'player_id': kwargs['player_id'], 'amount': kwargs['amount'], 'transaction_type': kwargs['transaction_type'], 'game': 'unit_flip', 'round_id': kwargs['round_id'], 'details': details}, False
    def find(self, **kwargs):
        return {'ledger_id': 'ledger-' + request_id, 'player_id': kwargs['player_id'], 'amount': -10.0, 'transaction_type': kwargs['transaction_type'], 'game': 'unit_flip', 'round_id': kwargs['round_id'], 'details': {'ledger_action_key': kwargs['action_key'], 'request_fingerprint': kwargs['request_fingerprint']}}
game = SimpleWagerGame(game_id='unit_flip', wager_transaction_type='UNIT_FLIP_WAGER_DEBIT', settlement_transaction_type='UNIT_FLIP_SETTLEMENT_CREDIT', entropy=entropy, resolve=resolve, validate_bet=validate, ledger_gateway=Gateway(), state_loader=load_state, state_updater=update_state, entropy_source=lambda _span: 2, clock=lambda: '2026-08-16T09:30:00Z', get_player=lambda player_id: {'player_id': player_id, 'balance': 90.0})
result = game.play('atomic-player', {'request_id': request_id, 'face': 5, 'stake': 10})
print('PASS:' + result['round']['round_id'])
"""
            # Resolve the one release marker shared by both stale readers.
            release_path = Path(temporary) / "release"
            # Retain both independent worker handles and readiness markers.
            workers = []
            # Start two distinct player actions without a shell.
            for index in range(2):
                # Allocate one unique readiness marker for this worker.
                ready_path = Path(temporary) / f"ready-{index}"
                # Start the exact interpreter and request identity.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"atomic-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain the worker and readiness ownership.
                workers.append((process, ready_path))
            # Bound the stale-load rendezvous so a broken worker cannot hang CI.
            deadline = time.monotonic() + 10
            # Wait until both workers captured the same original document.
            while not all(ready.exists() for _process, ready in workers) and time.monotonic() < deadline:
                # Stop early when a worker exits before readiness.
                if any(process.poll() is not None for process, _ready in workers):
                    # Leave polling for the diagnostic assertion below.
                    break
                # Yield briefly without changing process order.
                time.sleep(0.01)
            # Require both stale snapshots before publishing a sibling transition.
            self.assertTrue(all(ready.exists() for _process, ready in workers))
            # Define one provider-atomic unrelated sibling mutation.
            sibling_source = "from casino.core.state_store import update_player_game_state\ndef default_state():\n    return {'game': 'unit_flip', 'recent_rounds': []}\ndef add_sibling(state):\n    state['atomic_markers'] = ['concurrent']\n    return state\nupdate_player_game_state('unit_flip', 'atomic-player', add_sibling, default_state)\n"
            # Commit the sibling after both workers captured stale state.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the unrelated provider transition to complete.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release both distinct actions against provider-current state.
            release_path.write_text("go", encoding="utf-8")
            # Collect bounded worker results and exit codes.
            completed = [(*process.communicate(timeout=20), process.returncode) for process, _ready in workers]
            # Require both actions to complete rather than silently overwrite or conflict.
            for standard_output, standard_error, return_code in completed:
                # Preserve child diagnostics only when the proof fails.
                self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
                # Require the expected success marker from each complete action.
                self.assertTrue(standard_output.startswith("PASS:"), standard_output)
            # Read the final provider-authoritative JSON bytes.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require both distinct actions to survive regardless of serialization order.
            self.assertEqual({"atomic-0", "atomic-1"}, {row["request_id"] for row in final["recent_rounds"]})
            # Preserve the separately committed sibling field.
            self.assertEqual(["concurrent"], final["atomic_markers"])
            # Bound history exactly to the two committed actions in this fixture.
            self.assertEqual(2, len(final["recent_rounds"]))


# Run the focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate reporting and exit status to unittest.
    unittest.main()
