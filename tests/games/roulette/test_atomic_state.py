# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process and failure-boundary evidence for Roulette atomic state."""

# Import copy support for provider-like detached state transitions.
import copy
# Import JSON support for durable fixture and child evidence inspection.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for fresh independent Python workers.
import subprocess
# Import the active interpreter used by the repository test runner.
import sys
# Import temporary directories for task-owned provider and rendezvous files.
import tempfile
# Import bounded polling for child-process readiness.
import time
# Import the standard unit-test framework used by the central runner.
import unittest
# Import portable paths for repository, state, and rendezvous ownership.
from pathlib import Path
# Import focused patching support for deterministic in-memory provider seams.
from unittest import mock

# Import the production Roulette state transitions under test.
from casino.games.roulette import api, engine, rules


# Prove every Roulette mutation publishes against the provider-owned latest document. (ROU-073, TEST-202)
class RouletteAtomicStateTests(unittest.TestCase):
    # Build one complete player row accepted by the isolated JSON provider.
    _PLAYER = {"player_id": "atomic-player", "display_name": "Atomic Roulette", "type": "human", "balance": 100.0, "created_at": "2026-08-14T00:00:00Z", "updated_at": "2026-08-14T00:00:00Z", "status": "active"}

    # Return the canonical red outside-bet catalog entry.
    @staticmethod
    def _red_bet() -> dict:
        # Select the exact double-zero catalog item used by public manual bets.
        return next(entry for entry in rules.catalog("double") if entry["type"] == "red")

    # Build one complete open-round state with bounded test-owned sibling evidence.
    def _state(self, *, bets=None) -> dict:
        # Return the established engine shape with deterministic identities and timestamps.
        return {"open_round": {"round_id": "rou-atomic", "status": "open", "bets": copy.deepcopy(bets or [])}, "last_results": [], "mode": "double", "zero_rule": "normal", "last_bet_template": [], "visual": {"current_pocket": None, "current_angle": 0}, "atomic_markers": ["seed"]}

    # Bootstrap the wallet through a fresh process bound to the isolated provider root.
    def _bootstrap_wallet(self, repository_root: Path, environment: dict) -> None:
        # Serialize the exact player fixture without reflecting any external input.
        player_json = json.dumps(self._PLAYER, sort_keys=True)
        # Define one dependency-free provider bootstrap statement.
        source = f"from casino.core.storage import get_storage_provider; get_storage_provider().bootstrap_players({{'players': [{player_json}]}})"
        # Execute through the same provider selection used by settlement.
        completed = subprocess.run([sys.executable, "-c", source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
        # Require the isolated wallet bootstrap to complete cleanly.
        self.assertEqual(completed.returncode, 0, completed.stderr)

    # Return one isolated JSON-provider environment and durable Roulette state path.
    def _environment(self, temporary: str) -> tuple[Path, dict, Path]:
        # Resolve this exact checkout for child imports.
        repository_root = Path(__file__).resolve().parents[3]
        # Own every provider byte inside the disposable directory.
        data_root = Path(temporary) / "data"
        # Copy the caller environment before replacing runtime-owned paths.
        environment = os.environ.copy()
        # Select the disposable JSON provider in every fresh interpreter.
        environment["CASINO_STORAGE_PROVIDER"] = "json"
        # Bind state and ledger writes to the task-owned directory.
        environment["CASINO_DATA_DIR"] = str(data_root)
        # Keep child logs inside the same disposable owner boundary.
        environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
        # Bind imports to this exact worktree.
        environment["PYTHONPATH"] = str(repository_root)
        # Resolve the exact player-game document shared by workers.
        state_path = data_root / "games" / "roulette" / "atomic-player.json"
        # Return all exact process and persistence bindings.
        return repository_root, environment, state_path

    # Start two stale-load workers and release them through independently owned gates.
    def _start_workers(self, repository_root: Path, environment: dict, temporary_root: Path, modes: tuple[str, str]):
        # Define one worker that preloads state before its provider-owned transition.
        worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError
from casino.games.roulette import api, engine, rules
class FixedWheel:
    def choice(self, values):
        return '2'
engine._SYSTEM_RANDOM = FixedWheel()
state = load_player_game_state('roulette', 'atomic-player', engine.default_state)
mode = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Roulette atomic race release timed out')
if mode == 'purchase':
    red = next(entry for entry in rules.catalog('double') if entry['type'] == 'red')
    specification = {'bet_type': 'red', 'amount': 5.0, 'covered_numbers': red['covered_numbers'], 'label': red['label'], 'source': 'manual', 'transaction_type': 'ROULETTE_BET_PLACED', 'fingerprint': lambda bet: f"{bet['bet_id']}:{bet['type']}:{bet['covered_numbers']}:5.0", 'details': lambda bet: {'bet_id': bet['bet_id'], 'covered_numbers': bet['covered_numbers'], 'bet_type': bet['type']}}
    bets, marker = api.prepare_bet_purchase('atomic-player', state, [specification])
    api.settle_prepared_bet_action('atomic-player', state, marker)
    print('purchased')
elif mode == 'settings':
    try:
        api.update_settings('atomic-player', state, {'mode': 'single'})
    except ConflictError:
        print('refused')
    else:
        print('changed')
elif mode == 'spin-commit':
    api.commit_pending_spin('atomic-player', state)
    print('committed')
elif mode == 'spin-finalize':
    api.finalize_pending_spin('atomic-player', state, state[api.PENDING_SPIN_KEY])
    print('finalized')
elif mode == 'spin-settle':
    api.settle_pending_spin('atomic-player', state, state[api.PENDING_SPIN_KEY])
    print('settled')
else:
    def mark(current):
        current.setdefault('atomic_markers', []).append(mode)
        return current
    update_player_game_state('roulette', 'atomic-player', mark, engine.default_state)
    print('marked')
"""
        # Retain child processes and their readiness paths for bounded release.
        workers = []
        # Start both workers against the same preloaded durable document.
        for index, mode in enumerate(modes):
            # Give each worker an independent readiness marker.
            ready_path = temporary_root / f"ready-{mode}-{index}"
            # Give each worker an independently releasable gate.
            go_path = temporary_root / f"go-{mode}-{index}"
            # Launch without a shell so interpreter and argument identity stay exact.
            process = subprocess.Popen([sys.executable, "-c", worker_source, mode, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Retain the complete worker control tuple.
            workers.append((process, ready_path, go_path))
        # Bound stale-load rendezvous so a failed child cannot hang the suite.
        deadline = time.monotonic() + 10
        # Wait until both children have loaded before releasing either transition.
        while not all(ready.exists() for _process, ready, _go in workers) and time.monotonic() < deadline:
            # Stop early when a child exits before declaring readiness.
            if any(process.poll() is not None for process, _ready, _go in workers):
                # Leave the loop so the explicit assertion reports diagnostics.
                break
            # Yield briefly without broadening the deterministic schedule.
            time.sleep(0.01)
        # Require both stale snapshots before the test selects provider order.
        self.assertTrue(all(ready.exists() for _process, ready, _go in workers))
        # Return live workers so each test can release simultaneous or ordered schedules.
        return workers

    # Collect one worker with bounded diagnostics.
    def _collect(self, worker) -> str:
        # Unpack the live child and its already-consumed control paths.
        process, _ready, _go = worker
        # Read terminal output with one bounded timeout.
        standard_output, standard_error = process.communicate(timeout=15)
        # Require the production transition to complete without child failure.
        self.assertEqual(process.returncode, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
        # Return the normalized semantic outcome.
        return standard_output.strip()

    # Prove a wager transition preserves one racing sibling update and debits once.
    def test_purchase_preserves_fresh_process_sibling_update(self) -> None:
        # Own all provider and rendezvous bytes inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve isolated process, environment, and state bindings.
            repository_root, environment, state_path = self._environment(temporary)
            # Bootstrap the wallet before any settlement action starts.
            self._bootstrap_wallet(repository_root, environment)
            # Create the game-state directory before publishing the baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Seed one complete empty Roulette state and sibling marker.
            state_path.write_text(json.dumps(self._state(), sort_keys=True), encoding="utf-8")
            # Start one purchase and one unrelated stale sibling transition.
            workers = self._start_workers(repository_root, environment, Path(temporary), ("purchase", "purchase-sibling"))
            # Release both stale workers against the provider lock.
            for _process, _ready, go_path in workers:
                # Publish each independent release marker once.
                go_path.write_text("go", encoding="utf-8")
            # Require both transitions to complete cleanly.
            self.assertEqual(sorted(self._collect(worker) for worker in workers), ["marked", "purchased"])
            # Read the provider-authoritative state after both writes.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one durable bet, both sibling markers, and no private action residue.
            self.assertEqual((len(persisted["open_round"]["bets"]), persisted["atomic_markers"], persisted.get(api.PENDING_BET_ACTION_KEY)), (1, ["seed", "purchase-sibling"], None))
            # Define a fresh-process wallet and ledger evidence reader.
            evidence_source = "import json; from casino.core import players; from casino.core.settlement import GameSettlementGateway; gateway=GameSettlementGateway('roulette','bet_id'); print(json.dumps({'balance':players.get_player('atomic-player')['balance'],'rows':gateway.read_recent('atomic-player',20)}))"
            # Read durable evidence without sharing provider caches from this process.
            evidence_result = subprocess.run([sys.executable, "-c", evidence_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the isolated proof reader to complete cleanly.
            self.assertEqual(evidence_result.returncode, 0, evidence_result.stderr)
            # Decode the exact wallet and append-only movement rows.
            evidence = json.loads(evidence_result.stdout.strip())
            # Select only the established manual Roulette debit.
            wager_rows = [row for row in evidence["rows"] if row["transaction_type"] == "ROULETTE_BET_PLACED"]
            # Require one five-unit debit and the exact resulting wallet balance.
            self.assertEqual((evidence["balance"], len(wager_rows), wager_rows[0]["amount"]), (95.0, 1, -5.0))

    # Prove provider order makes stale settings refuse after a committed wager.
    def test_provider_ordered_settings_cannot_erase_committed_bet(self) -> None:
        # Own all provider and rendezvous bytes inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve isolated process, environment, and state bindings.
            repository_root, environment, state_path = self._environment(temporary)
            # Bootstrap the wallet used by the winning purchase transition.
            self._bootstrap_wallet(repository_root, environment)
            # Create the game-state directory before publishing the baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Seed the exact no-bet state both workers preload.
            state_path.write_text(json.dumps(self._state(), sort_keys=True), encoding="utf-8")
            # Start purchase and settings workers from the same stale state.
            workers = self._start_workers(repository_root, environment, Path(temporary), ("purchase", "settings"))
            # Release and complete the purchase first to define provider order.
            workers[0][2].write_text("go", encoding="utf-8")
            # Require the first action to publish its wager successfully.
            self.assertEqual(self._collect(workers[0]), "purchased")
            # Release the stale settings worker only after the wager is terminal.
            workers[1][2].write_text("go", encoding="utf-8")
            # Require provider-current validation to refuse the obsolete mode change.
            self.assertEqual(self._collect(workers[1]), "refused")
            # Read the final provider-owned document.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require the bet and original mode to survive without recovery residue.
            self.assertEqual((persisted["mode"], len(persisted["open_round"]["bets"]), persisted.get(api.PENDING_BET_ACTION_KEY)), ("double", 1, None))

    # Prove committed spin and terminal result transitions preserve racing siblings.
    def test_spin_commit_and_finalization_preserve_process_siblings(self) -> None:
        # Own all provider and rendezvous bytes inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve isolated process, environment, and state bindings.
            repository_root, environment, state_path = self._environment(temporary)
            # Bootstrap the wallet read by zero-credit settlement history.
            self._bootstrap_wallet(repository_root, environment)
            # Build one losing red bet so state proof needs no wallet credit.
            red = self._red_bet()
            # Preserve the complete established durable bet shape.
            bet = {"bet_id": "bet-spin", "player_id": "atomic-player", "game": "roulette", "round_id": "rou-atomic", "type": "red", "label": red["label"], "covered_numbers": red["covered_numbers"], "amount": 5.0, "net_payout": red["net_payout"], "created_at": "2026-08-14T00:00:00Z", "source": "manual", "layout_kind": red.get("layout_kind")}
            # Create the state directory before publishing the open round.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Seed the exact wager set observed by both commit workers.
            state_path.write_text(json.dumps(self._state(bets=[bet]), sort_keys=True), encoding="utf-8")
            # Race entropy commitment against one unrelated stale sibling update.
            commit_workers = self._start_workers(repository_root, environment, Path(temporary), ("spin-commit", "commit-sibling"))
            # Release both provider transitions once.
            for _process, _ready, go_path in commit_workers:
                # Publish each independent release marker.
                go_path.write_text("go", encoding="utf-8")
            # Require both commit-stage transitions to complete.
            self.assertEqual(sorted(self._collect(worker) for worker in commit_workers), ["committed", "marked"])
            # Read the exact committed-but-private spin state.
            committed = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one exact pocket, preserved sibling, and no premature public result.
            self.assertEqual((committed[api.PENDING_SPIN_KEY]["round"]["result"], committed["atomic_markers"], committed["last_results"]), ("2", ["seed", "commit-sibling"], []))
            # Race two terminal settlement requests against the same zero-credit result.
            finalize_workers = self._start_workers(repository_root, environment, Path(temporary), ("spin-settle", "spin-settle"))
            # Release both settlement-stage transitions once.
            for _process, _ready, go_path in finalize_workers:
                # Publish each independent release marker.
                go_path.write_text("go", encoding="utf-8")
            # Require both requests to converge through one terminal commitment.
            self.assertEqual([self._collect(worker) for worker in finalize_workers], ["settled", "settled"])
            # Read the provider-authoritative terminal state.
            finalized = json.loads(state_path.read_text(encoding="utf-8"))
            # Require the commit sibling, one exact result, a fresh open round, and zero private residue.
            self.assertEqual((finalized["atomic_markers"], [item["result"] for item in finalized["last_results"]], finalized["open_round"]["status"], finalized.get(api.PENDING_SPIN_KEY)), (["seed", "commit-sibling"], ["2"], "open", None))
            # Define a fresh-process history evidence reader for the exact round.
            history_source = "import json; from casino.core import history; print(json.dumps(history.recent_history(20,'roulette')))"
            # Read history without sharing provider caches from this process.
            history_result = subprocess.run([sys.executable, "-c", history_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the isolated history read to complete cleanly.
            self.assertEqual(history_result.returncode, 0, history_result.stderr)
            # Require exactly one history row across both zero-credit contenders.
            self.assertEqual(len(json.loads(history_result.stdout.strip())), 1)

    # Build one in-memory provider seam that returns detached atomic results.
    @staticmethod
    def _memory_update(box: dict):
        # Return a helper compatible with update_player_game_state.
        def update(_game_id, _player_id, mutator, _default_factory):
            # Give the callback a detached provider-current document.
            working = copy.deepcopy(box["state"])
            # Apply one complete state transition.
            updated = mutator(working)
            # Persist a detached copy so later caller mutation cannot alter storage.
            box["state"] = copy.deepcopy(updated)
            # Return another detached copy like JSON/MySQL provider decoding.
            return copy.deepcopy(updated)
        # Expose the complete fake provider update boundary.
        return update

    # Build one prepared manual specification for deterministic failure tests.
    def _manual_specification(self) -> dict:
        # Resolve canonical red catalog semantics once.
        red = self._red_bet()
        # Return the exact existing manual transaction vocabulary.
        return {"bet_type": "red", "amount": 5.0, "covered_numbers": red["covered_numbers"], "label": red["label"], "source": "manual", "transaction_type": "ROULETTE_BET_PLACED", "fingerprint": lambda bet: f"{bet['bet_id']}:{bet['type']}:{bet['covered_numbers']}:5.0", "details": lambda bet: {"bet_id": bet["bet_id"], "covered_numbers": bet["covered_numbers"], "bet_type": bet["type"]}}

    # Build a settlement fake that fails before or after publishing immutable proof.
    class _FailingSettlement:
        # Store whether the injected failure leaves a committed row behind.
        def __init__(self, *, commits: bool):
            # Retain the requested failure boundary.
            self.commits = commits
            # Start without immutable ledger proof.
            self.event = None
            # Count mutation attempts for exactly-once assertions.
            self.apply_calls = 0

        # Fail the movement at the selected boundary.
        def apply_once(self, *, player_id, **movement):
            # Count the sole attempted movement.
            self.apply_calls += 1
            # Publish one exact immutable row only for the lost-response schedule.
            if self.commits:
                # Match the gateway proof dimensions used by reconciliation.
                self.event = {"ledger_id": "led-lost", "game": "roulette", "player_id": player_id, "amount": movement["signed_amount"], "transaction_type": movement["transaction_type"], "round_id": movement["round_id"], "details": {**movement["details"], "game_action_key": movement["action_key"], "request_fingerprint": movement["request_fingerprint"]}}
            # Surface the deterministic injected response failure.
            raise RuntimeError("injected settlement failure")

        # Return exact committed proof without issuing another movement.
        def find(self, _player_id, _action_key, **_dimensions):
            # Return the immutable row only after the lost-response boundary commits.
            return copy.deepcopy(self.event)

        # Validate recovered proof against the prepared movement dimensions.
        def validate_existing(self, event, *, transaction_type, round_id, signed_amount, request_fingerprint):
            # Require exact amount, type, round, and semantic fingerprint equality.
            if (event["transaction_type"], event["round_id"], event["amount"], event["details"]["request_fingerprint"]) != (transaction_type, round_id, signed_amount, request_fingerprint):
                # Fail the focused test immediately on divergent proof.
                raise AssertionError("Recovered settlement proof diverged")

    # Simulate one committed settlement whose first response is lost and whose retry replays proof.
    class _LostThenReplaySettlement:
        # Start without a committed row or mutation attempt.
        def __init__(self):
            # Retain the exact immutable event after the first invocation commits it.
            self.event = None
            # Count action invocations separately from durable commits.
            self.apply_calls = 0
            # Count the one simulated durable ledger commit.
            self.commits = 0

        # Commit once, lose the first response, then replay the same row.
        def apply_once(self, *, player_id, **movement):
            # Count every caller invocation under the stable action identity.
            self.apply_calls += 1
            # Publish the immutable row only on the first invocation.
            if self.event is None:
                # Count exactly one simulated provider commit.
                self.commits += 1
                # Preserve the complete proof dimensions used by the real gateway.
                self.event = {"ledger_id": "led-settlement", "game": "roulette", "player_id": player_id, "amount": movement["signed_amount"], "transaction_type": movement["transaction_type"], "round_id": movement["round_id"], "details": {**movement["details"], "game_action_key": movement["action_key"], "request_fingerprint": movement["request_fingerprint"]}}
                # Model a transport loss after the provider transaction commits.
                raise RuntimeError("injected lost settlement response")
            # Return the exact immutable row with the replay marker on retry.
            return copy.deepcopy(self.event), True

    # Prove an absent pre-ledger failure rolls back only its owned prepared bet.
    def test_preledger_failure_rolls_back_only_owned_bet(self) -> None:
        # Seed one sibling field that appears before preparation.
        box = {"state": self._state()}
        # Use an in-memory provider boundary with detached state copies.
        updater = self._memory_update(box)
        # Patch only the provider seam while preparing exact production state.
        with mock.patch.object(api, "update_player_game_state", side_effect=updater):
            # Load one caller snapshot from the same baseline.
            state = copy.deepcopy(box["state"])
            # Publish the prepared bet and private movement marker.
            _bets, marker = api.prepare_bet_purchase("atomic-player", state, [self._manual_specification()])
            # Publish one unrelated sibling after preparation but before settlement failure.
            box["state"]["atomic_markers"].append("concurrent")
            # Fail before any immutable ledger row exists.
            settlement = self._FailingSettlement(commits=False)
            # Patch the canonical money boundary only for this deterministic schedule.
            with mock.patch.object(api, "SETTLEMENT", settlement):
                # Require the original settlement error to surface.
                with self.assertRaisesRegex(RuntimeError, "injected settlement failure"):
                    # Reconcile the exact absent action and bounded rollback.
                    api.settle_prepared_bet_action("atomic-player", state, marker)
        # Require only the prepared bet to disappear while sibling state survives.
        self.assertEqual((box["state"]["open_round"]["bets"], box["state"]["atomic_markers"], box["state"].get(api.PENDING_BET_ACTION_KEY), settlement.apply_calls), ([], ["seed", "concurrent"], None, 1))

    # Prove a committed lost response retains the bet without a second debit.
    def test_lost_debit_response_keeps_exact_bet_and_releases_marker(self) -> None:
        # Seed one isolated provider-current state document.
        box = {"state": self._state()}
        # Use detached copies for every fake provider transition.
        updater = self._memory_update(box)
        # Patch only the provider-owned update seam.
        with mock.patch.object(api, "update_player_game_state", side_effect=updater):
            # Load a caller snapshot from the same baseline.
            state = copy.deepcopy(box["state"])
            # Publish the exact prepared wager and recovery marker.
            bets, marker = api.prepare_bet_purchase("atomic-player", state, [self._manual_specification()])
            # Add a sibling field after preparation to detect whole-document rollback.
            box["state"]["atomic_markers"].append("concurrent")
            # Fail only after publishing exact immutable debit proof.
            settlement = self._FailingSettlement(commits=True)
            # Patch the canonical settlement boundary for this one schedule.
            with mock.patch.object(api, "SETTLEMENT", settlement):
                # Require the lost response to surface after state reconciliation.
                with self.assertRaisesRegex(RuntimeError, "injected settlement failure"):
                    # Classify committed proof and retain the exact purchased bet.
                    api.settle_prepared_bet_action("atomic-player", state, marker)
        # Require one exact bet, preserved sibling state, released marker, and one movement attempt.
        self.assertEqual(([bet["bet_id"] for bet in box["state"]["open_round"]["bets"]], box["state"]["atomic_markers"], box["state"].get(api.PENDING_BET_ACTION_KEY), settlement.apply_calls), ([bets[0]["bet_id"]], ["seed", "concurrent"], None, 1))

    # Prove a committed lost refund response never restores or credits the bet twice.
    def test_lost_refund_response_keeps_bet_removed_and_releases_marker(self) -> None:
        # Resolve canonical red details for one complete durable wager.
        red = self._red_bet()
        # Build the exact bet that the refund action owns.
        bet = {"bet_id": "bet-refund", "player_id": "atomic-player", "game": "roulette", "round_id": "rou-atomic", "type": "red", "label": red["label"], "covered_numbers": red["covered_numbers"], "amount": 5.0, "net_payout": red["net_payout"], "created_at": "2026-08-14T00:00:00Z", "source": "manual", "layout_kind": red.get("layout_kind")}
        # Seed one exact open wager and a sibling field.
        box = {"state": self._state(bets=[bet])}
        # Use detached provider copies for prepare and reconciliation.
        updater = self._memory_update(box)
        # Patch only the provider update seam.
        with mock.patch.object(api, "update_player_game_state", side_effect=updater):
            # Load a caller snapshot from the same baseline.
            state = copy.deepcopy(box["state"])
            # Remove the exact bet and publish its immutable refund intent.
            removed, marker = api.prepare_bet_refund("atomic-player", state, [bet["bet_id"]])
            # Publish one unrelated sibling after preparation.
            box["state"]["atomic_markers"].append("concurrent")
            # Fail only after publishing exact immutable refund proof.
            settlement = self._FailingSettlement(commits=True)
            # Patch the canonical settlement boundary for this one schedule.
            with mock.patch.object(api, "SETTLEMENT", settlement):
                # Require the lost response to surface after terminal state reconciliation.
                with self.assertRaisesRegex(RuntimeError, "injected settlement failure"):
                    # Recover committed proof without issuing a second refund.
                    api.settle_prepared_bet_action("atomic-player", state, marker)
        # Require exact removal, preserved sibling state, released marker, and one movement attempt.
        self.assertEqual((removed, box["state"]["open_round"]["bets"], box["state"]["atomic_markers"], box["state"].get(api.PENDING_BET_ACTION_KEY), settlement.apply_calls), ([bet], [], ["seed", "concurrent"], None, 1))

    # Prove a committed lost payout response resumes the exact pocket and credit once.
    def test_lost_settlement_response_replays_exact_spin_without_duplicate_history(self) -> None:
        # Resolve canonical red details for one winning durable wager.
        red = self._red_bet()
        # Build the exact bet settled by the committed red pocket.
        bet = {"bet_id": "bet-settlement", "player_id": "atomic-player", "game": "roulette", "round_id": "rou-atomic", "type": "red", "label": red["label"], "covered_numbers": red["covered_numbers"], "amount": 5.0, "net_payout": red["net_payout"], "created_at": "2026-08-14T00:00:00Z", "source": "manual", "layout_kind": red.get("layout_kind")}
        # Seed one exact open round and sibling marker.
        box = {"state": self._state(bets=[bet])}
        # Use detached provider copies for commitment and terminal publication.
        updater = self._memory_update(box)
        # Define a deterministic red winning pocket.
        fixed_wheel = mock.Mock()
        # Return pocket one for the sole fresh entropy selection.
        fixed_wheel.choice.return_value = "1"
        # Patch only provider update and production entropy seams.
        with mock.patch.object(api, "update_player_game_state", side_effect=updater), mock.patch.object(engine, "_SYSTEM_RANDOM", fixed_wheel):
            # Load one caller snapshot from the same baseline.
            state = copy.deepcopy(box["state"])
            # Publish the exact pocket and priced outcome before settlement.
            pending = api.commit_pending_spin("atomic-player", state)
            # Add one unrelated sibling after entropy commitment.
            box["state"]["atomic_markers"].append("concurrent")
            # Commit once while losing the first provider response.
            settlement = self._LostThenReplaySettlement()
            # Patch wallet reads and history writes without mutating money outside the fake.
            with mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api.players, "get_player", return_value={"player_id": "atomic-player", "balance": 105.0}), mock.patch.object(api, "append_history") as append_history:
                # Require the first lost response to preserve the private commitment.
                with self.assertRaisesRegex(RuntimeError, "injected lost settlement response"):
                    # Attempt the exact committed payout once.
                    api.settle_pending_spin("atomic-player", state, pending)
                # Reload the exact pending commitment left by the failed response.
                pending_retry = copy.deepcopy(box["state"][api.PENDING_SPIN_KEY])
                # Replay immutable proof and finalize without resampling or recrediting.
                response = api.settle_pending_spin("atomic-player", state, pending_retry)
        # Require one provider commit, one replay invocation, one terminal result, and no duplicate history.
        self.assertEqual((settlement.commits, settlement.apply_calls, response[0]["ledger"]["ledger_id"], response[0]["replayed"], [item["result"] for item in box["state"]["last_results"]], box["state"]["atomic_markers"], box["state"].get(api.PENDING_SPIN_KEY), append_history.call_count, fixed_wheel.choice.call_count), (1, 2, "led-settlement", True, ["1"], ["seed", "concurrent"], None, 0, 1))

    # Prove failed clear-all rollback restores original bet ordering and siblings.
    def test_failed_clear_all_restores_original_bet_order(self) -> None:
        # Resolve canonical red details for three complete durable bets.
        red = self._red_bet()
        # Build three exact ordered bets owned by the same player.
        bets = [{"bet_id": f"bet-{index}", "player_id": "atomic-player", "game": "roulette", "round_id": "rou-atomic", "type": "red", "label": red["label"], "covered_numbers": red["covered_numbers"], "amount": float(index), "net_payout": red["net_payout"], "created_at": "2026-08-14T00:00:00Z", "source": "manual", "layout_kind": red.get("layout_kind")} for index in (1, 2, 3)]
        # Seed the provider with the exact original chip order.
        box = {"state": self._state(bets=bets)}
        # Use detached provider copies for prepare and rollback.
        updater = self._memory_update(box)
        # Patch only the provider update boundary.
        with mock.patch.object(api, "update_player_game_state", side_effect=updater):
            # Load a caller snapshot from the same baseline.
            state = copy.deepcopy(box["state"])
            # Atomically remove all bets and publish refund intents.
            _removed, marker = api.prepare_bet_refund("atomic-player", state)
            # Add one unrelated sibling after removal.
            box["state"]["atomic_markers"].append("concurrent")
            # Reject the first refund before any movement commits.
            settlement = self._FailingSettlement(commits=False)
            # Patch the settlement proof boundary for exact rollback.
            with mock.patch.object(api, "SETTLEMENT", settlement):
                # Require the original provider error to surface.
                with self.assertRaisesRegex(RuntimeError, "injected settlement failure"):
                    # Restore every definitively uncommitted removed bet.
                    api.settle_prepared_bet_action("atomic-player", state, marker)
        # Require exact original bet order, preserved siblings, and no marker residue.
        self.assertEqual(([bet["bet_id"] for bet in box["state"]["open_round"]["bets"]], box["state"]["atomic_markers"], box["state"].get(api.PENDING_BET_ACTION_KEY)), (["bet-1", "bet-2", "bet-3"], ["seed", "concurrent"], None))


# Run the focused suite when this file is executed directly.
if __name__ == "__main__":
    # Delegate discovery and exit status to unittest.
    unittest.main()
