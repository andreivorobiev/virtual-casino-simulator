# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process Dragon Tiger preparation evidence. (DT-006, TEST-221)"""

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

# Import the production engine used for exact persisted state.
from casino.games.dragon_tiger import engine


# Prove provider-current preparation serializes stale fresh processes.
class DragonTigerAtomicStateTests(unittest.TestCase):
    # Confirm two contenders deal one private result and preserve a concurrent sibling.
    def test_fresh_process_preparation_race_has_one_shoe_winner(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "atomic-player.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps({**engine.default_state(), "atomic_markers": ["seed"]}, sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting isolated JSON storage.
            environment = os.environ.copy()
            # Bind every child to disposable state and this exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one dependency-free worker that waits before provider preparation.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.cards import create_deck
from casino.games.dragon_tiger import engine
from casino.games.dragon_tiger.service import DragonTigerService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
action_id = sys.argv[3]
ready.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not release.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not release.exists():
    raise RuntimeError('Dragon Tiger preparation release timed out')
draws = []
def shoe_factory():
    draws.append('shoe')
    cards = [card.code for card in create_deck(engine.DECK_COUNT)]
    pop_order = ['2C', '3D', '4H', 'KS', 'QH']
    for card in pop_order:
        cards.remove(card)
    cards.extend(reversed(pop_order))
    return cards
game = DragonTigerService(shoe_factory=shoe_factory, clock=lambda: '2026-08-16T09:30:00Z', player_reader=lambda player_id: {'player_id': player_id, 'balance': 100})
wager = {'bet': 'dragon', 'wager': 2.0}
result = game.prepare(player_id='atomic-player', request_id=action_id, round_id=engine.round_id_for('atomic-player', action_id), fingerprint=engine.request_fingerprint('dragon', 2.0), wager=wager)
print('PASS:' + str(len(draws)) + ':' + result['entropy']['dragon_card'] + ':' + result['entropy']['tiger_card'] + ':' + str(int(result['replayed'])))
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start two contenders for the same provider-owned preparation.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), "atomic-preparation"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain process and gate ownership.
                workers.append((process, ready_path, release_path))
            # Bound the pre-preparation rendezvous.
            deadline = time.monotonic() + 10
            # Wait until both workers are ready to contend for authority.
            while not all(ready.exists() for _process, ready, _release in workers) and time.monotonic() < deadline:
                # Stop early if either worker failed before readiness.
                if any(process.poll() is not None for process, _ready, _release in workers):
                    # Leave polling for explicit diagnostics below.
                    break
                # Yield briefly without starting another action.
                time.sleep(0.01)
            # Require both contenders before publishing a concurrent sibling.
            self.assertTrue(all(ready.exists() for _process, ready, _release in workers))
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.dragon_tiger import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('dragon_tiger', 'atomic-player', add, engine.default_state)\n"
            # Commit the sibling before either preparation enters provider state.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release both contenders without choosing a winner locally.
            for _process, _ready, release in workers:
                # Open every bounded gate before collecting either result.
                release.write_text("go", encoding="utf-8")
            # Collect both provider-serialized preparation results.
            outputs = [process.communicate(timeout=20) for process, _ready, _release in workers]
            # Require both processes to return exact same authoritative cards.
            self.assertTrue(all(process.returncode == 0 and output.strip().startswith("PASS:") for (process, _ready, _release), (output, _error) in zip(workers, outputs)), outputs)
            # Split local shoe counts, cards, and replay flags from both workers.
            evidence = [output.strip().split(":") for output, _error in outputs]
            # Require exactly one shoe owner and one provider replay.
            self.assertEqual(([0, 1], ["KS", "KS"], ["QH", "QH"], [0, 1]), (sorted(int(row[1]) for row in evidence), sorted(row[2] for row in evidence), sorted(row[3] for row in evidence), sorted(int(row[4]) for row in evidence)))
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one private winner, exact shoe consumption, sibling preservation, and no terminal fabrication.
            self.assertEqual((persisted["prepared_actions"]["atomic-preparation"]["dragon_card"], len(persisted["shoe"]), persisted["recent_rounds"], persisted["atomic_markers"]), ("KS", engine.DECK_COUNT * 52 - engine.BURN_CARDS - engine.ROUND_CARDS, [], ["seed", "concurrent"]))
            # Reject legacy optimistic operation metadata from persistent JSON.
            self.assertNotIn("_dragon_tiger_atomic_baseline", persisted)


# Run this focused suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
