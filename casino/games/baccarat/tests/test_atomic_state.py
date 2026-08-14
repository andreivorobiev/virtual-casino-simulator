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
# Import production Baccarat helpers for real mutations and deterministic defaults.
from casino.games.baccarat import api, engine


# Prove Baccarat pending commitments, consumed shoes, and terminal history use atomic state. (TEST-192)
class BaccaratAtomicStateTests(unittest.TestCase):
    # Run one pair of fresh workers after both have loaded the same stale state document.
    def _run_pair(self, repository_root: Path, environment: dict, temporary_root: Path, first_mode: str, second_mode: str) -> list[str]:
        # Define one dependency-free worker that preloads state before its atomic transition.
        worker_source = """
import os
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError, ValidationError
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
elif mode == 'placement':
    bet, marker = api.prepare_bet_placement('atomic-player', state, 'player', 5.0)
    api.settle_prepared_bet_action('atomic-player', state, marker)
elif mode == 'refund':
    bet, marker = api.prepare_bet_refund('atomic-player', state, os.environ['BACCARAT_ATOMIC_BET_ID'])
    api.settle_prepared_bet_action('atomic-player', state, marker)
elif mode == 'refund-race':
    try:
        api.resume_prepared_bet_action('atomic-player', state)
        bet, marker = api.prepare_bet_refund('atomic-player', state, os.environ['BACCARAT_ATOMIC_BET_ID'])
        api.settle_prepared_bet_action('atomic-player', state, marker)
    except (ConflictError, ValidationError):
        print('refused')
    else:
        print('settled')
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
        # Return normalized worker outcomes for contention tests that distinguish winner and refusal.
        return [standard_output.strip() for standard_output, _standard_error, _return_code in completed]

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

    # Prove placement and refund preserve sibling updates and move money exactly once. (TEST-198)
    def test_bet_placement_and_refund_converge_across_processes(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the isolated JSON provider root shared by fresh interpreters.
            data_root = Path(temporary) / "data"
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[4]
            # Copy the caller environment before replacing runtime-owned paths.
            environment = os.environ.copy()
            # Select the disposable provider root in every fresh interpreter.
            environment["CASINO_DATA_DIR"] = str(data_root)
            # Keep child logs inside the same disposable owner boundary.
            environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
            # Require the JSON provider so cross-process state and ledger locks are exercised.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Bind imports to this exact worktree.
            environment["PYTHONPATH"] = str(repository_root)
            # Build one complete wallet row accepted by the production provider.
            bootstrap_source = """
from casino.core.storage import get_storage_provider
get_storage_provider().bootstrap_players({'players': [{'player_id': 'atomic-player', 'display_name': 'Atomic Baccarat', 'type': 'human', 'balance': 100.0, 'created_at': '2026-08-14T00:00:00Z', 'updated_at': '2026-08-14T00:00:00Z', 'status': 'active'}]})
"""
            # Seed the wallet through the same provider boundary used by settlement.
            bootstrap = subprocess.run([sys.executable, "-c", bootstrap_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the isolated provider bootstrap to complete cleanly.
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            # Resolve the exact Baccarat player document used by both worker pairs.
            state_path = data_root / "games" / "baccarat" / "atomic-player.json"
            # Create the game-state directory before publishing an empty baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Seed production defaults plus one sibling field every wager transition must preserve.
            initial = engine.default_state()
            # Add the independent sibling marker before publishing the baseline.
            initial["atomic_markers"] = ["seed"]
            # Publish one complete provider document without an open wager.
            state_path.write_text(json.dumps(initial), encoding="utf-8")
            # Race one prepared placement/debit against an unrelated stale sibling mutation.
            self._run_pair(repository_root, environment, Path(temporary), "placement", "placement-sibling")
            # Read the authoritative document after placement reconciliation.
            placed = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one visible bet, both sibling markers, and no private recovery residue.
            self.assertEqual((len(placed["open_bets"]), placed["atomic_markers"], placed.get("_baccarat_pending_bet_action")), (1, ["seed", "placement-sibling"], None))
            # Retain the exact server-generated bet identity for the refund worker.
            bet_id = placed["open_bets"][0]["bet_id"]
            # Bind only the stable bet identity into the isolated child environment.
            environment["BACCARAT_ATOMIC_BET_ID"] = bet_id
            # Race its prepared refund against a second unrelated stale sibling mutation.
            self._run_pair(repository_root, environment, Path(temporary), "refund", "refund-sibling")
            # Read the terminal document after refund reconciliation.
            refunded = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exact bet removal, all sibling fields, and zero private action residue.
            self.assertEqual((refunded["open_bets"], refunded["atomic_markers"], refunded.get("_baccarat_pending_bet_action")), ([], ["seed", "placement-sibling", "refund-sibling"], None))
            # Read wallet and ledger evidence from a fresh interpreter bound to the same provider.
            evidence_source = """
import json
from casino.core import players
from casino.core.settlement import GameSettlementGateway
gateway = GameSettlementGateway('baccarat', 'bet_id')
print(json.dumps({'balance': players.get_player('atomic-player')['balance'], 'rows': gateway.read_recent('atomic-player', 20)}))
"""
            # Execute the provider read without sharing this test process's configuration cache.
            evidence_result = subprocess.run([sys.executable, "-c", evidence_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the isolated provider read to complete cleanly.
            self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
            # Decode the exact final wallet and append-only rows.
            evidence = json.loads(evidence_result.stdout.strip())
            # Select the two Baccarat bet movement families from the durable ledger.
            bet_rows = [row for row in evidence["rows"] if row["transaction_type"] in {"BACCARAT_BET_PLACED", "BACCARAT_BET_REFUND"}]
            # Require one debit, one refund, one stable bet identity, and the restored wallet.
            self.assertEqual((evidence["balance"], sorted(row["transaction_type"] for row in bet_rows), {row["round_id"] for row in bet_rows}), (100.0, ["BACCARAT_BET_PLACED", "BACCARAT_BET_REFUND"], {bet_id}))

    # Prove two stale processes refunding the same bet produce one exact credit. (TEST-198)
    def test_same_bet_concurrent_refund_is_exactly_once(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the isolated JSON provider root shared by both contenders.
            data_root = Path(temporary) / "data"
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[4]
            # Copy the caller environment before replacing provider-owned paths.
            environment = os.environ.copy()
            # Select the disposable JSON provider in every fresh interpreter.
            environment["CASINO_DATA_DIR"] = str(data_root)
            # Keep child logs inside the same disposable owner boundary.
            environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
            # Require the cross-process JSON locks used by production state and settlement.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Bind imports to this exact worktree.
            environment["PYTHONPATH"] = str(repository_root)
            # Build one wallet whose prior bet debit is represented by its current balance.
            bootstrap_source = """
from casino.core.storage import get_storage_provider
get_storage_provider().bootstrap_players({'players': [{'player_id': 'atomic-player', 'display_name': 'Atomic Baccarat', 'type': 'human', 'balance': 95.0, 'created_at': '2026-08-14T00:00:00Z', 'updated_at': '2026-08-14T00:00:00Z', 'status': 'active'}]})
"""
            # Seed the wallet through the same provider boundary used by refund settlement.
            bootstrap = subprocess.run([sys.executable, "-c", bootstrap_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require isolated provider bootstrap to complete cleanly.
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            # Resolve and create the exact player-game document path.
            state_path = data_root / "games" / "baccarat" / "atomic-player.json"
            # Create the game-state directory before publishing the bet baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Define one exact open bet visible to both stale contenders.
            bet = {"bet_id": "bet-refund-race", "player_id": "atomic-player", "type": "player", "label": "Player", "amount": 5.0, "source": "manual"}
            # Seed defaults, the bet, and an unrelated sibling field contention must preserve.
            initial = engine.default_state()
            # Publish the exact contended bet in the default state.
            initial["open_bets"] = [bet]
            # Add the independent sibling marker before publishing the baseline.
            initial["atomic_markers"] = ["seed"]
            # Persist the shared stale-load baseline.
            state_path.write_text(json.dumps(initial), encoding="utf-8")
            # Bind only the stable server-issued bet identity into both workers.
            environment["BACCARAT_ATOMIC_BET_ID"] = bet["bet_id"]
            # Release both stale refund contenders through production state and ledger paths.
            outcomes = self._run_pair(repository_root, environment, Path(temporary), "refund-race", "refund-race")
            # Require one settlement winner and one fail-closed contender.
            self.assertEqual(sorted(outcomes), ["refused", "settled"])
            # Read the authoritative state after both workers terminate.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exact bet removal, sibling preservation, and zero private marker residue.
            self.assertEqual((state["open_bets"], state["atomic_markers"], state.get("_baccarat_pending_bet_action")), ([], ["seed"], None))
            # Read wallet and ledger evidence through a fresh provider process.
            evidence_source = """
import json
from casino.core import players
from casino.core.settlement import GameSettlementGateway
gateway = GameSettlementGateway('baccarat', 'bet_id')
print(json.dumps({'balance': players.get_player('atomic-player')['balance'], 'rows': gateway.read_recent('atomic-player', 20)}))
"""
            # Execute the isolated authoritative read without sharing process caches.
            evidence_result = subprocess.run([sys.executable, "-c", evidence_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the durable read to complete cleanly.
            self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
            # Decode the final wallet and append-only rows.
            evidence = json.loads(evidence_result.stdout.strip())
            # Select only the refund row owned by the contended bet.
            refunds = [row for row in evidence["rows"] if row["transaction_type"] == "BACCARAT_BET_REFUND" and row["round_id"] == bet["bet_id"]]
            # Require one refund credit and the exact restored wallet value.
            self.assertEqual((evidence["balance"], len(refunds), refunds[0]["amount"]), (100.0, 1, 5.0))

    # Prove pre-ledger failures restore only the prepared wager mutation. (TEST-198)
    def test_bet_action_rollbacks_preserve_sibling_state(self) -> None:
        # Build one in-memory provider document with an unrelated sibling marker.
        document = engine.default_state()
        # Add the sibling marker that every rollback must preserve.
        document["atomic_markers"] = ["sibling"]

        # Execute production mutators against the isolated latest document.
        def update(game_id, player_id, mutator, default_factory):
            # Require every transition to remain in the selected Baccarat player scope.
            self.assertEqual((game_id, player_id), ("baccarat", "atomic-player"))
            # Apply one provider-owned transition to a detached current document.
            updated = mutator(json.loads(json.dumps(document)))
            # Replace the simulated provider document after successful publication.
            document.clear()
            # Copy the complete updated document into the next provider snapshot.
            document.update(json.loads(json.dumps(updated)))
            # Return an independent authoritative result to production code.
            return json.loads(json.dumps(document))

        # Patch only storage and settlement boundaries while retaining real bet mutations.
        with mock.patch.object(api, "update_player_game_state", side_effect=update), mock.patch.object(api.SETTLEMENT, "apply_once", side_effect=RuntimeError("pre-ledger failure")), mock.patch.object(api.SETTLEMENT, "find", return_value=None):
            # Retain a caller-owned state object refreshed by each transition.
            state = json.loads(json.dumps(document))
            # Prepare one placement in the authoritative document.
            bet, placement_marker = api.prepare_bet_placement("atomic-player", state, "player", 5.0)
            # Require the injected pre-ledger failure to trigger exact rollback.
            with self.assertRaises(RuntimeError):
                # Attempt settlement through the production recovery path.
                api.settle_prepared_bet_action("atomic-player", state, placement_marker)
            # Require no phantom bet or marker while retaining the sibling field.
            self.assertEqual((document["open_bets"], document["atomic_markers"], document.get("_baccarat_pending_bet_action")), ([], ["sibling"], None))
            # Seed the exact bet for refund rollback evidence.
            document["open_bets"] = [bet]
            # Refresh the caller snapshot before preparing the refund.
            state = json.loads(json.dumps(document))
            # Prepare removal and its immutable refund intent.
            cleared, refund_marker = api.prepare_bet_refund("atomic-player", state, bet["bet_id"])
            # Require the injected pre-ledger failure to trigger exact reinsertion.
            with self.assertRaises(RuntimeError):
                # Attempt refund settlement through the production recovery path.
                api.settle_prepared_bet_action("atomic-player", state, refund_marker)
            # Require the same bet and sibling marker with no private residue.
            self.assertEqual((document["open_bets"], document["atomic_markers"], document.get("_baccarat_pending_bet_action")), ([cleared], ["sibling"], None))

    # Prove settings use the latest document and refuse every active wager boundary. (TEST-198)
    def test_settings_are_atomic_and_refuse_active_wager_state(self) -> None:
        # Seed a provider document with a sibling field and the current production rules.
        document = engine.default_state()
        # Retain one unrelated field through every accepted settings update.
        document["atomic_markers"] = ["sibling"]

        # Execute production mutators against the isolated latest document.
        def update(game_id, player_id, mutator, default_factory):
            # Apply one detached provider-owned transition.
            updated = mutator(json.loads(json.dumps(document)))
            # Replace the simulated current document only after success.
            document.clear()
            # Preserve the complete new document for subsequent calls.
            document.update(json.loads(json.dumps(updated)))
            # Return an independent authoritative snapshot.
            return json.loads(json.dumps(document))

        # Route every settings transition through the isolated atomic provider seam.
        with mock.patch.object(api, "update_player_game_state", side_effect=update):
            # Apply one compatible rule change to the provider-owned latest document.
            state = json.loads(json.dumps(document))
            # Update only the declared setting supplied by the caller.
            api.update_settings("atomic-player", state, {"tie_payout": 9}, api.declared_fields(api.GAME_ID))
            # Require the changed rule, preserved omitted rules, and sibling field.
            self.assertEqual((document["rules"]["tie_payout"], document["rules"]["decks"], document["atomic_markers"]), (9, 8, ["sibling"]))
            # Exercise every state that must block a settings mutation.
            for blocker in ("open_bets", api.PENDING_BET_ACTION_KEY, "pending_coup"):
                # Restore a clean document before inserting this exact blocker.
                document.update({"open_bets": [], api.PENDING_BET_ACTION_KEY: None, "pending_coup": None})
                # Publish one truthy value of the selected active wager boundary.
                document[blocker] = [{}] if blocker == "open_bets" else {"kind": "pending"}
                # Refuse the change without altering provider-owned rules or sibling fields.
                with self.assertRaises(ConflictError):
                    # Attempt one rule change against the active wager state.
                    api.update_settings("atomic-player", state, {"tie_payout": 8}, api.declared_fields(api.GAME_ID))
                # Require the last accepted rule and sibling marker to remain exact.
                self.assertEqual((document["rules"]["tie_payout"], document["atomic_markers"]), (9, ["sibling"]))

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
