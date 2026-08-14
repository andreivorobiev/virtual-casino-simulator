# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for Keno draw and ticket state transitions."""

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

# Import the production Keno API helpers for direct idempotence assertions.
from casino.games.keno import api
# Import the expected fail-closed error for divergent commitments.
from casino.errors import ConflictError


# Prove Keno draw, ticket, and terminal transitions use the atomic state helper. (TEST-191, TEST-197)
class KenoAtomicStateTests(unittest.TestCase):
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
from casino.games.keno import api, engine
class ScriptedBalls:
    def sample(self, population, count):
        return list(range(1, 21))
engine._SYSTEM_RANDOM = ScriptedBalls()
state = load_player_game_state('keno', 'atomic-player', engine.default_state)
mode = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Keno atomic race release timed out')
if mode == 'commit':
    api.commit_pending_draw('atomic-player', state)
elif mode == 'finalize':
    api.finalize_committed_draw_state('atomic-player', state, state['pending_draw'])
elif mode == 'purchase':
    ticket, marker = api.prepare_ticket_purchase('atomic-player', state, [7, 14, 21], 5.0)
    api.settle_prepared_ticket_action('atomic-player', state, marker)
elif mode == 'refund':
    ticket, marker = api.prepare_ticket_refund('atomic-player', state, os.environ['KENO_ATOMIC_TICKET_ID'])
    api.settle_prepared_ticket_action('atomic-player', state, marker)
elif mode == 'refund-race':
    try:
        api.resume_prepared_ticket_action('atomic-player', state)
        ticket, marker = api.prepare_ticket_refund('atomic-player', state, os.environ['KENO_ATOMIC_TICKET_ID'])
        api.settle_prepared_ticket_action('atomic-player', state, marker)
    except (ConflictError, ValidationError):
        print('refused')
    else:
        print('settled')
else:
    def mark(current):
        current.setdefault('atomic_markers', []).append(mode)
        return current
    update_player_game_state('keno', 'atomic-player', mark, engine.default_state)
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

    # Prove pending commit and terminal finalization preserve racing sibling fields.
    def test_pending_commit_and_finalization_preserve_concurrent_process_updates(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the isolated JSON provider data root.
            data_root = Path(temporary) / "data"
            # Resolve the exact Keno player document used by both worker pairs.
            state_path = data_root / "games" / "keno" / "atomic-player.json"
            # Create the parent before publishing the deterministic pre-draw state.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Build one complete open ticket consumed by the committed draw.
            ticket = {"ticket_id": "ticket-atomic", "player_id": "atomic-player", "spots": [1, 2, 3], "amount": 5.0, "source": "manual", "created_at": "2026-08-13T00:00:00Z"}
            # Seed the production state shape without a pending commitment.
            state_path.write_text(json.dumps({"open_tickets": [ticket], "last_draws": []}), encoding="utf-8")
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
            # Require the committed draw and sibling marker to coexist.
            self.assertEqual(("commit-sibling", 1), (committed["atomic_markers"][0], len(committed["pending_draw"]["results"])))
            # Capture the exact round identity used by terminal finalization.
            round_id = committed["pending_draw"]["round_id"]
            # Race terminal finalization against a second unrelated atomic marker.
            self._run_pair(repository_root, environment, Path(temporary), "finalize", "finalize-sibling")
            # Read the final provider-published state after both workers exit.
            finalized = json.loads(state_path.read_text(encoding="utf-8"))
            # Require both independent sibling updates to survive the two state transitions.
            self.assertEqual(finalized["atomic_markers"], ["commit-sibling", "finalize-sibling"])
            # Require the exact committed draw once in terminal history.
            self.assertEqual([item["round_id"] for item in finalized["last_draws"]], [round_id])
            # Require the pending commitment and settled tickets to be cleared.
            self.assertNotIn("pending_draw", finalized)
            # Require no ticket from the finalized draw to remain open.
            self.assertEqual(finalized["open_tickets"], [])

    # Prove purchase and refund preserve sibling updates and move money exactly once. (TEST-197)
    def test_ticket_purchase_and_refund_converge_across_processes(self) -> None:
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
get_storage_provider().bootstrap_players({'players': [{'player_id': 'atomic-player', 'display_name': 'Atomic Keno', 'type': 'human', 'balance': 100.0, 'created_at': '2026-08-14T00:00:00Z', 'updated_at': '2026-08-14T00:00:00Z', 'status': 'active'}]})
"""
            # Seed the wallet through the same provider boundary used by settlement.
            bootstrap = subprocess.run([sys.executable, "-c", bootstrap_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the isolated provider bootstrap to complete cleanly.
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            # Resolve the exact Keno player document used by both worker pairs.
            state_path = data_root / "games" / "keno" / "atomic-player.json"
            # Create the game-state directory before publishing an empty baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Seed one sibling field that every ticket transition must preserve.
            state_path.write_text(json.dumps({"open_tickets": [], "last_draws": [], "atomic_markers": ["seed"]}), encoding="utf-8")
            # Race one prepared purchase/debit against an unrelated stale sibling mutation.
            self._run_pair(repository_root, environment, Path(temporary), "purchase", "purchase-sibling")
            # Read the authoritative document after purchase reconciliation.
            purchased = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one visible ticket, both sibling markers, and no private recovery residue.
            self.assertEqual((len(purchased["open_tickets"]), purchased["atomic_markers"], purchased.get("_keno_pending_ticket_action")), (1, ["seed", "purchase-sibling"], None))
            # Retain the exact ticket identity for the refund worker.
            ticket_id = purchased["open_tickets"][0]["ticket_id"]
            # Bind only the server-generated ticket identity into the isolated child environment.
            environment["KENO_ATOMIC_TICKET_ID"] = ticket_id
            # Race its prepared refund against a second unrelated stale sibling mutation.
            self._run_pair(repository_root, environment, Path(temporary), "refund", "refund-sibling")
            # Read the terminal document after refund reconciliation.
            refunded = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exact ticket removal, all sibling fields, and zero private action residue.
            self.assertEqual((refunded["open_tickets"], refunded["atomic_markers"], refunded.get("_keno_pending_ticket_action")), ([], ["seed", "purchase-sibling", "refund-sibling"], None))
            # Read wallet and ledger evidence from a fresh interpreter bound to the same provider.
            evidence_source = """
import json
from casino.core import players
from casino.core.settlement import GameSettlementGateway
gateway = GameSettlementGateway('keno', 'ticket_id')
print(json.dumps({'balance': players.get_player('atomic-player')['balance'], 'rows': gateway.read_recent('atomic-player', 20)}))
"""
            # Execute the provider read without sharing this test process's configuration cache.
            evidence_result = subprocess.run([sys.executable, "-c", evidence_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the isolated provider read to complete cleanly.
            self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
            # Decode the exact final wallet and append-only rows.
            evidence = json.loads(evidence_result.stdout.strip())
            # Select the two ticket movement families from the durable ledger.
            ticket_rows = [row for row in evidence["rows"] if row["transaction_type"] in {"KENO_TICKET_PURCHASED", "KENO_TICKET_REFUND"}]
            # Require one debit, one refund, one stable ticket identity, and the restored wallet.
            self.assertEqual((evidence["balance"], sorted(row["transaction_type"] for row in ticket_rows), {row["round_id"] for row in ticket_rows}), (100.0, ["KENO_TICKET_PURCHASED", "KENO_TICKET_REFUND"], {ticket_id}))

    # Prove two stale processes refunding the same ticket produce one exact credit. (TEST-197)
    def test_same_ticket_concurrent_refund_is_exactly_once(self) -> None:
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
            # Build one wallet whose prior ticket debit is represented by its current balance.
            bootstrap_source = """
from casino.core.storage import get_storage_provider
get_storage_provider().bootstrap_players({'players': [{'player_id': 'atomic-player', 'display_name': 'Atomic Keno', 'type': 'human', 'balance': 95.0, 'created_at': '2026-08-14T00:00:00Z', 'updated_at': '2026-08-14T00:00:00Z', 'status': 'active'}]})
"""
            # Seed the wallet through the same provider boundary used by refund settlement.
            bootstrap = subprocess.run([sys.executable, "-c", bootstrap_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require isolated provider bootstrap to complete cleanly.
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            # Resolve and create the exact player-game document path.
            state_path = data_root / "games" / "keno" / "atomic-player.json"
            # Create the game-state directory before publishing the ticket baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Define one exact open ticket visible to both stale contenders.
            ticket = {"ticket_id": "ticket-refund-race", "player_id": "atomic-player", "spots": [7, 14, 21], "amount": 5.0, "source": "manual", "created_at": "2026-08-14T00:00:00Z"}
            # Seed one unrelated sibling field that contention must preserve.
            state_path.write_text(json.dumps({"open_tickets": [ticket], "last_draws": [], "atomic_markers": ["seed"]}), encoding="utf-8")
            # Bind only the stable server-issued ticket identity into both workers.
            environment["KENO_ATOMIC_TICKET_ID"] = ticket["ticket_id"]
            # Release both stale refund contenders through the production state and ledger paths.
            outcomes = self._run_pair(repository_root, environment, Path(temporary), "refund-race", "refund-race")
            # Require one settlement winner and one fail-closed contender.
            self.assertEqual(sorted(outcomes), ["refused", "settled"])
            # Read the authoritative state after both workers terminate.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exact ticket removal, sibling preservation, and zero private marker residue.
            self.assertEqual((state["open_tickets"], state["atomic_markers"], state.get("_keno_pending_ticket_action")), ([], ["seed"], None))
            # Read wallet and ledger evidence through a fresh provider process.
            evidence_source = """
import json
from casino.core import players
from casino.core.settlement import GameSettlementGateway
gateway = GameSettlementGateway('keno', 'ticket_id')
print(json.dumps({'balance': players.get_player('atomic-player')['balance'], 'rows': gateway.read_recent('atomic-player', 20)}))
"""
            # Execute the isolated authoritative read without sharing process caches.
            evidence_result = subprocess.run([sys.executable, "-c", evidence_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the durable read to complete cleanly.
            self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
            # Decode the final wallet and append-only rows.
            evidence = json.loads(evidence_result.stdout.strip())
            # Select only the refund rows owned by the contended ticket.
            refunds = [row for row in evidence["rows"] if row["transaction_type"] == "KENO_TICKET_REFUND" and row["round_id"] == ticket["ticket_id"]]
            # Require one refund credit and the exact restored wallet value.
            self.assertEqual((evidence["balance"], len(refunds), refunds[0]["amount"]), (100.0, 1, 5.0))

    # Prove pre-ledger failures restore only the prepared ticket mutation. (TEST-197)
    def test_ticket_action_rollbacks_preserve_sibling_state(self) -> None:
        # Build one in-memory provider document with an unrelated sibling marker.
        document = {"open_tickets": [], "last_draws": [], "atomic_markers": ["sibling"]}

        # Execute production mutators against the isolated latest document.
        def update(game_id, player_id, mutator, default_factory):
            # Require every transition to remain in the selected Keno player scope.
            self.assertEqual((game_id, player_id), ("keno", "atomic-player"))
            # Apply one provider-owned transition to a detached current document.
            updated = mutator(json.loads(json.dumps(document)))
            # Replace the simulated provider document after successful publication.
            document.clear()
            # Copy the complete updated document into the next provider snapshot.
            document.update(json.loads(json.dumps(updated)))
            # Return an independent authoritative result to production code.
            return json.loads(json.dumps(document))

        # Patch only storage and settlement boundaries while retaining real ticket mutations.
        with mock.patch.object(api, "update_player_game_state", side_effect=update), mock.patch.object(api.SETTLEMENT, "apply_once", side_effect=RuntimeError("pre-ledger failure")), mock.patch.object(api.SETTLEMENT, "find", return_value=None):
            # Retain a caller-owned state object refreshed by each transition.
            state = json.loads(json.dumps(document))
            # Prepare one purchase in the authoritative document.
            ticket, purchase_marker = api.prepare_ticket_purchase("atomic-player", state, [1, 2, 3], 5.0)
            # Require the injected pre-ledger failure to trigger exact rollback.
            with self.assertRaises(RuntimeError):
                # Attempt settlement through the production recovery path.
                api.settle_prepared_ticket_action("atomic-player", state, purchase_marker)
            # Require no phantom ticket or marker while retaining the sibling field.
            self.assertEqual(document, {"open_tickets": [], "last_draws": [], "atomic_markers": ["sibling"]})
            # Seed the exact ticket for refund rollback evidence.
            document["open_tickets"] = [ticket]
            # Refresh the caller snapshot before preparing the refund.
            state = json.loads(json.dumps(document))
            # Prepare removal and its immutable refund intent.
            cleared, refund_marker = api.prepare_ticket_refund("atomic-player", state, ticket["ticket_id"])
            # Require the injected pre-ledger failure to trigger exact reinsertion.
            with self.assertRaises(RuntimeError):
                # Attempt refund settlement through the production recovery path.
                api.settle_prepared_ticket_action("atomic-player", state, refund_marker)
            # Require the same ticket and sibling marker with no private residue.
            self.assertEqual((document["open_tickets"], document["atomic_markers"], document.get("_keno_pending_ticket_action")), ([cleared], ["sibling"], None))

    # Prove exact terminal replays are idempotent and divergent draws fail closed.
    def test_terminal_finalization_replay_is_exact_and_divergence_fails_closed(self) -> None:
        # Build one complete draw identity for an already terminal in-memory state.
        draw = {"round_id": "draw-terminal", "results": [], "drawn": [], "timestamp": "2026-08-13T00:00:00Z"}
        # Capture calls to the shared atomic helper without selecting real storage.
        with mock.patch.object(api, "update_player_game_state") as update:
            # Execute the supplied mutator against an already finalized document.
            update.side_effect = lambda game_id, player_id, mutator, default: mutator({"open_tickets": [], "last_draws": [draw]})
            # Retain a caller-owned stale snapshot for refresh evidence.
            state = {"pending_draw": draw}
            # Repeat finalization after another process already completed it.
            api.finalize_committed_draw_state("atomic-player", state, draw)
            # Require the authoritative terminal document without a duplicate history row.
            self.assertEqual([item["round_id"] for item in state["last_draws"]], ["draw-terminal"])
            # Replace the provider result with a same-id terminal draw whose result bytes diverge.
            update.side_effect = lambda game_id, player_id, mutator, default: mutator({"open_tickets": [], "last_draws": [{**draw, "drawn": [80]}]})
            # Refuse round-id aliasing because only the exact committed draw is replay-safe.
            with self.assertRaises(ConflictError):
                # Attempt finalization with the stale original draw.
                api.finalize_committed_draw_state("atomic-player", state, draw)
            # Replace the provider result with a different live pending commitment.
            update.side_effect = lambda game_id, player_id, mutator, default: mutator({"open_tickets": [], "last_draws": [], "pending_draw": {"round_id": "draw-other"}})
            # Refuse to clear or finalize the unrelated racing commitment.
            with self.assertRaises(ConflictError):
                # Attempt finalization with the stale original draw.
                api.finalize_committed_draw_state("atomic-player", state, draw)


# Run the focused module suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
