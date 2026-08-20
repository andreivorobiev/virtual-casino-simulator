# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process and failure-boundary evidence for Bingo atomic state."""

# Import copy support for provider-like detached documents.
import copy
# Import JSON support for durable worker state and evidence.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for independent stale-load workers.
import subprocess
# Import the active interpreter selected by the repository test runner.
import sys
# Import task-owned temporary directories for provider bytes and gates.
import tempfile
# Import bounded polling for worker rendezvous.
import time
# Import the standard unit-test framework.
import unittest
# Import portable paths for exact checkout and worker files.
from pathlib import Path

# Import deterministic ownership for every fresh-process race worker.
from tests.process_race import ProcessRacePool
# Import focused patching for deterministic provider and settlement seams.
from unittest import mock

# Import the production Bingo transitions under test.
from casino.games.bingo import api, engine
# Import the public conflict type used by overlap gates.
from casino.errors import ConflictError


# Prove every Bingo mutation publishes against provider-owned current state. (BINGO-028, TEST-203)
class BingoAtomicStateTests(unittest.TestCase):
    # Build one valid deterministic card whose first two balls do not win.
    @staticmethod
    def _card(*, card_id: str = "card-atomic", player_id: str = "atomic-player", status: str = "active", payout: float = 0.0) -> dict:
        # Return the complete established card shape.
        return {"card_id": card_id, "player_id": player_id, "amount": 5.0, "card": {"B": [1, 2, 3, 4, 5], "I": [16, 17, 18, 19, 20], "N": [31, 32, "FREE", 34, 35], "G": [46, 47, 48, 49, 50], "O": [61, 62, 63, 64, 65]}, "status": status, "winner": status == "won", "payout": payout, "source": "manual"}

    # Build one complete active provider document with sibling evidence.
    def _active_state(self) -> dict:
        # Build the active session consumed by engine.call_next and reset.
        session = {"session_id": "bingo-atomic", "player_id": "atomic-player", "amount": 5.0, "pattern": "line", "card": self._card()["card"], "cards": [self._card()], "called": [], "status": "active", "created_at": "2026-08-14T00:00:00Z", "winner": None, "winning_card_id": None, "payout": 0, "max_calls": 50}
        # Return established state plus a bounded unrelated sibling field.
        return {"active_session": session, "last_sessions": [], "atomic_markers": ["seed"]}

    # Build a terminal winning state and exact committed call marker.
    def _winning_state(self) -> tuple[dict, dict]:
        # Build the exact winning card selected for one payout.
        card = self._card(status="won", payout=17.0)
        # Retain the winning geometry consumed by history projection.
        card["winning_coords"] = [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]]
        # Build the immutable archived winning session.
        session = {"session_id": "bingo-win", "player_id": "atomic-player", "amount": 5.0, "pattern": "line", "card": card["card"], "cards": [card], "called": [1, 2, 3, 4, 5], "status": "won", "created_at": "2026-08-14T00:00:00Z", "completed_at": "2026-08-14T00:01:00Z", "winner": "atomic-player", "winning_card_id": card["card_id"], "payout": 17.0, "max_calls": 50}
        # Bind settlement to the exact provider-committed call action.
        marker = {"kind": "call", "status": "committed", "action_id": "call-win", "session_id": session["session_id"], "calls": [5], "terminal": True, "history_claims": []}
        # Return both provider state and detached marker evidence.
        return {"active_session": None, "last_sessions": [session], "atomic_markers": ["seed"], api.PENDING_ACTION_KEY: copy.deepcopy(marker)}, marker

    # Build one in-memory provider seam that returns detached results.
    @staticmethod
    def _memory_update(box: dict):
        # Return a helper compatible with update_player_game_state.
        def update(_game_id, _player_id, mutator, _default_factory):
            # Give the callback a detached provider-current document.
            working = copy.deepcopy(box["state"])
            # Apply one complete transition.
            updated = mutator(working)
            # Persist a detached copy to prevent caller-side mutation.
            box["state"] = copy.deepcopy(updated)
            # Return another detached provider decoding.
            return copy.deepcopy(updated)
        # Expose the complete fake provider update boundary.
        return update

    # Patch provider reads and updates around one detached in-memory document.
    def _provider_patches(self, box: dict):
        # Return both patches so tests can enter them together.
        return (mock.patch.object(api, "update_player_game_state", side_effect=self._memory_update(box)), mock.patch.object(api, "load_player_game_state", side_effect=lambda *_args, **_kwargs: copy.deepcopy(box["state"])))

    # Build a settlement fake that fails before or after immutable publication.
    class _FailingSettlement:
        # Retain failure policy and optional transaction filters.
        def __init__(self, *, committed_types=()):
            # Normalize transaction types whose first response is lost.
            self.committed_types = set(committed_types)
            # Store committed events by canonical action identity.
            self.events = {}
            # Count every mutation attempt by transaction type.
            self.apply_calls = {}

        # Commit selected transactions before losing the response; fail others before commit.
        def apply_once(self, *, player_id, action_key, **movement):
            # Count the sole action attempt for this ledger meaning.
            transaction_type = movement["transaction_type"]
            # Increment the bounded per-type invocation count.
            self.apply_calls[transaction_type] = self.apply_calls.get(transaction_type, 0) + 1
            # Publish exact immutable proof only for selected lost-response types.
            if transaction_type in self.committed_types:
                # Retain canonical proof dimensions for recovery validation.
                self.events[action_key] = {"ledger_id": f"ledger-{action_key}", "game": "bingo", "player_id": player_id, "amount": movement["signed_amount"], "transaction_type": transaction_type, "round_id": movement["round_id"], "details": {**movement["details"], "game_action_key": action_key, "request_fingerprint": movement["request_fingerprint"]}}
            # Surface the deterministic provider/transport failure.
            raise RuntimeError(f"injected {transaction_type} failure")

        # Return exact committed proof without retrying the money mutation.
        def find(self, _player_id, action_key, **_dimensions):
            # Return a detached immutable event when the selected failure committed.
            return copy.deepcopy(self.events.get(action_key))

        # Validate every immutable recovery dimension used by production.
        def validate_existing(self, event, *, transaction_type, round_id, signed_amount, request_fingerprint):
            # Require exact type, round, amount, and semantic fingerprint.
            if (event["transaction_type"], event["round_id"], event["amount"], event["details"]["request_fingerprint"]) != (transaction_type, round_id, signed_amount, request_fingerprint):
                # Fail the focused proof on any divergent row.
                raise AssertionError("Recovered Bingo settlement proof diverged")

    # Return one isolated JSON-provider environment and Bingo state path.
    @staticmethod
    def _environment(temporary: str) -> tuple[Path, dict, Path]:
        # Resolve this exact checkout for child imports.
        repository_root = Path(__file__).resolve().parents[3]
        # Own every provider byte inside the disposable directory.
        data_root = Path(temporary) / "data"
        # Copy the environment before replacing storage paths.
        environment = os.environ.copy()
        # Select the JSON provider for cross-process serialization.
        environment["CASINO_STORAGE_PROVIDER"] = "json"
        # Bind state and logs to the task-owned root.
        environment["CASINO_DATA_DIR"] = str(data_root)
        # Keep child logs inside the same disposable owner boundary.
        environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
        # Bind imports to this exact worktree.
        environment["PYTHONPATH"] = str(repository_root)
        # Resolve the one shared player-game document.
        state_path = data_root / "games" / "bingo" / "atomic-player.json"
        # Return exact process and persistence bindings.
        return repository_root, environment, state_path

    # Start two workers after both preload one stale Bingo snapshot.
    def _start_call_workers(self, repository_root: Path, environment: dict, temporary_root: Path, process_pool: ProcessRacePool):
        # Define one worker whose mutation refreshes provider authority after its stale preload.
        worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state
from casino.games.bingo import api, engine
class FixedBalls:
    def choice(self, values):
        return min(values)
engine._rng = FixedBalls()
state = load_player_game_state('bingo', 'atomic-player', engine.default_state)
ready_path = Path(sys.argv[1])
go_path = Path(sys.argv[2])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Bingo atomic race release timed out')
api.resume_pending_action('atomic-player', state)
marker = api.commit_calls('atomic-player', state, 1)
_session, calls, _credits = api.settle_committed_call('atomic-player', state, marker)
print(calls[0])
"""
        # Retain both child processes and their independent release gates.
        workers = []
        # Create the exact two stale-load contenders.
        for index in range(2):
            # Give each child a task-owned readiness marker.
            ready_path = temporary_root / f"ready-call-{index}"
            # Give each child an independently ordered release gate.
            go_path = temporary_root / f"go-call-{index}"
            # Launch without a shell so interpreter and arguments remain exact.
            process = process_pool.spawn([sys.executable, "-c", worker_source, str(ready_path), str(go_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Retain the complete control tuple.
            workers.append((process, ready_path, go_path))
        # Bound rendezvous so a child failure cannot hang the suite.
        deadline = time.monotonic() + 10
        # Wait until both children hold stale preloaded snapshots.
        while not all(ready.exists() for _process, ready, _go in workers) and time.monotonic() < deadline:
            # Stop polling if either child exits early.
            if any(process.poll() is not None for process, _ready, _go in workers):
                # Leave the loop for explicit diagnostic assertions.
                break
            # Yield briefly while retaining deterministic gate ownership.
            time.sleep(0.01)
        # Require both workers to preload before provider ordering begins.
        process_pool.wait_until_ready([(process, ready) for process, ready, _go in workers], timeout=0)
        # Return live workers for ordered release.
        return workers

    # Collect one worker with bounded diagnostics.
    def _collect(self, worker) -> str:
        # Unpack the process from already-consumed control paths.
        process, _ready, _go = worker
        # Read terminal output with one bounded timeout.
        standard_output, standard_error = process.communicate(timeout=15)
        # Require clean production transition completion.
        self.assertEqual(process.returncode, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
        # Return the normalized semantic result.
        return standard_output.strip()

    # Prove two stale fresh processes publish distinct balls in provider order.
    def test_fresh_process_calls_preserve_order_without_marker_residue(self) -> None:
        # Own every provider and gate byte inside one temporary root.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve isolated process, environment, and durable state.
            repository_root, environment, state_path = self._environment(temporary)
            # Create the game-state directory before writing the baseline.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish one active session both workers will preload.
            state_path.write_text(json.dumps(self._active_state(), sort_keys=True), encoding="utf-8")
            # Start exactly two stale-load call workers.
            workers = self._start_call_workers(repository_root, environment, Path(temporary), process_pool)
            # Release and complete the first call before the second refreshes authority.
            workers[0][2].write_text("go", encoding="utf-8")
            # Require the first provider-ordered ball.
            self.assertEqual(self._collect(workers[0]), "1")
            # Release the second worker from its stale initial snapshot.
            workers[1][2].write_text("go", encoding="utf-8")
            # Require the second distinct provider-ordered ball.
            self.assertEqual(self._collect(workers[1]), "2")
            # Read final provider-authoritative state directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require exact order, no duplicate/drop, sibling preservation, and zero private residue.
            self.assertEqual((persisted["active_session"]["called"], persisted["atomic_markers"], persisted.get(api.PENDING_ACTION_KEY)), ([1, 2], ["seed"], None))

    # Prove a prepared purchase blocks call/reset and rollback preserves sibling state.
    def test_purchase_overlap_fails_closed_without_sibling_loss(self) -> None:
        # Seed one actionable document with an unrelated field.
        box = {"state": {"active_session": None, "last_sessions": [], "atomic_markers": ["seed"]}}
        # Patch both provider seams to detached in-memory transitions.
        update_patch, load_patch = self._provider_patches(box)
        # Enter both exact production storage seams.
        with update_patch, load_patch:
            # Prepare one purchase against the provider-current document.
            state = copy.deepcopy(box["state"])
            # Reserve the action before any wallet movement.
            marker = api.prepare_purchase("atomic-player", state, 5.0, "line")
            # Publish an unrelated sibling after preparation.
            box["state"]["atomic_markers"].append("concurrent")
            # Refuse a competing call while purchase recovery owns the slot.
            with self.assertRaises(ConflictError):
                # Attempt one provider-atomic ball selection.
                api.commit_calls("atomic-player", copy.deepcopy(box["state"]), 1)
            # Refuse a competing reset under the same ownership marker.
            with self.assertRaises(ConflictError):
                # Attempt provider-atomic reset selection.
                api.prepare_reset("atomic-player", copy.deepcopy(box["state"]))
            # Roll back only the exact uncommitted reservation.
            api.rollback_purchase("atomic-player", state, marker)
        # Require sibling evidence and public state to survive with no private residue.
        self.assertEqual((box["state"]["atomic_markers"], box["state"].get(api.PENDING_ACTION_KEY)), (["seed", "concurrent"], None))

    # Prove a committed call excludes another call and reset until exact finalization.
    def test_committed_call_blocks_call_and_reset_until_finalized(self) -> None:
        # Seed one active provider session.
        box = {"state": self._active_state()}
        # Patch both provider seams around detached current documents.
        update_patch, load_patch = self._provider_patches(box)
        # Select deterministic first-ball entropy.
        fixed_rng = mock.Mock()
        # Always choose the smallest provider-current remaining ball.
        fixed_rng.choice.side_effect = lambda values: min(values)
        # Enter provider, entropy, and wallet seams.
        with update_patch, load_patch, mock.patch.object(api.engine, "_rng", fixed_rng):
            # Commit one exact call while retaining its private marker.
            state = copy.deepcopy(box["state"])
            # Publish the provider-ordered ball and recovery owner.
            marker = api.commit_calls("atomic-player", state, 1)
            # Refuse a second call before terminal marker finalization.
            with self.assertRaises(ConflictError):
                # Attempt a competing ball selection.
                api.commit_calls("atomic-player", copy.deepcopy(box["state"]), 1)
            # Refuse reset while the same committed call owns response recovery.
            with self.assertRaises(ConflictError):
                # Attempt a competing reset selection.
                api.prepare_reset("atomic-player", copy.deepcopy(box["state"]))
            # Finalize the committed nonterminal call without money/history work.
            api.settle_committed_call("atomic-player", state, marker)
            # Require reset selection to become actionable after marker release.
            reset_marker = api.prepare_reset("atomic-player", state)
        # Require exact reset ownership of the once-called session and no second ball.
        self.assertEqual((reset_marker["session_id"], box["state"]["active_session"]["called"], box["state"][api.PENDING_ACTION_KEY]["kind"]), ("bingo-atomic", [1], "reset"))

    # Prove an absent human debit restores an actionable state without compensation.
    def test_preledger_purchase_failure_rolls_back_only_owned_marker(self) -> None:
        # Seed an empty provider document.
        box = {"state": {"active_session": None, "last_sessions": [], "atomic_markers": ["seed"]}}
        # Build a settlement that never publishes immutable proof.
        settlement = self._FailingSettlement()
        # Patch provider, bot roster, and money boundary deterministically.
        update_patch, load_patch = self._provider_patches(box)
        # Enter all bounded production seams.
        with update_patch, load_patch, mock.patch.object(api.profiles, "eligible_bots", return_value=[]), mock.patch.object(api, "SETTLEMENT", settlement):
            # Reserve one exact purchase.
            state = copy.deepcopy(box["state"])
            # Publish the private marker.
            marker = api.prepare_purchase("atomic-player", state, 5.0, "line")
            # Require the original absent-proof failure.
            with self.assertRaisesRegex(RuntimeError, "BINGO_CARD_PURCHASED"):
                # Attempt the no-retry purchase workflow.
                api.settle_purchase("atomic-player", state, marker)
        # Require one mutation attempt, no refund, no session, and no marker.
        self.assertEqual((settlement.apply_calls, box["state"]["active_session"], box["state"].get(api.PENDING_ACTION_KEY)), ({"BINGO_CARD_PURCHASED": 1}, None, None))

    # Prove a lost debit response creates one session without a second debit.
    def test_lost_purchase_debit_response_recovers_one_session(self) -> None:
        # Seed an empty provider document.
        box = {"state": {"active_session": None, "last_sessions": [], "atomic_markers": ["seed"]}}
        # Commit the human debit before injecting its response loss.
        settlement = self._FailingSettlement(committed_types={"BINGO_CARD_PURCHASED"})
        # Patch deterministic provider, roster, and settlement seams.
        update_patch, load_patch = self._provider_patches(box)
        # Enter all production boundaries.
        with update_patch, load_patch, mock.patch.object(api.profiles, "eligible_bots", return_value=[]), mock.patch.object(api, "SETTLEMENT", settlement):
            # Prepare one stable purchase identity.
            state = copy.deepcopy(box["state"])
            # Publish the action reservation.
            marker = api.prepare_purchase("atomic-player", state, 5.0, "line")
            # Recover the committed debit and publish one session.
            session = api.settle_purchase("atomic-player", state, marker)
        # Require exactly one debit attempt, one session, and no private residue.
        self.assertEqual((settlement.apply_calls, session["session_id"], box["state"]["active_session"]["session_id"], box["state"].get(api.PENDING_ACTION_KEY)), ({"BINGO_CARD_PURCHASED": 1}, session["session_id"], session["session_id"], None))

    # Prove a lost refund response compensates once and preserves actionable state.
    def test_lost_purchase_refund_response_never_double_credits(self) -> None:
        # Seed an empty provider document.
        box = {"state": {"active_session": None, "last_sessions": [], "atomic_markers": ["seed"]}}
        # Commit both the initial debit and compensation before losing their responses.
        settlement = self._FailingSettlement(committed_types={"BINGO_CARD_PURCHASED", "BINGO_CARD_REFUND_AFTER_ERROR"})
        # Patch provider and roster around one forced engine failure.
        update_patch, load_patch = self._provider_patches(box)
        # Enter bounded production seams and prevent card publication.
        with update_patch, load_patch, mock.patch.object(api.profiles, "eligible_bots", return_value=[]), mock.patch.object(api.engine, "start_session", side_effect=RuntimeError("injected session failure")), mock.patch.object(api, "SETTLEMENT", settlement):
            # Prepare the exact purchase marker.
            state = copy.deepcopy(box["state"])
            # Publish action ownership.
            marker = api.prepare_purchase("atomic-player", state, 5.0, "line")
            # Preserve the engine failure after exact debit/refund reconciliation.
            with self.assertRaisesRegex(RuntimeError, "session failure"):
                # Attempt the one no-retry purchase.
                api.settle_purchase("atomic-player", state, marker)
        # Require exactly one debit and refund attempt, no session, and no marker.
        self.assertEqual((settlement.apply_calls, box["state"]["active_session"], box["state"].get(api.PENDING_ACTION_KEY)), ({"BINGO_CARD_PURCHASED": 1, "BINGO_CARD_REFUND_AFTER_ERROR": 1}, None, None))

    # Prove a lost payout response publishes one credited card and one history row.
    def test_lost_payout_response_converges_credit_and_history_once(self) -> None:
        # Seed one terminal winning action.
        state_document, marker = self._winning_state()
        # Retain the provider-owned detached state.
        box = {"state": state_document}
        # Commit payout proof before losing its first response.
        settlement = self._FailingSettlement(committed_types={"BINGO_PAYOUT_CREDIT"})
        # Capture history append calls without external storage.
        history_rows = []
        # Patch provider, money, wallet, and history seams.
        update_patch, load_patch = self._provider_patches(box)
        # Enter all exact transition dependencies.
        with update_patch, load_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api.players, "get_player", return_value={"balance": 112.0}), mock.patch.object(api, "append_history", side_effect=lambda *args: history_rows.append(args)):
            # Settle the first contender from the committed marker.
            state = copy.deepcopy(box["state"])
            # Recover the lost response and finalize provider state.
            _session, _calls, credits = api.settle_committed_call("atomic-player", state, copy.deepcopy(marker))
            # Re-enter from a stale sibling snapshot to prove idempotent convergence.
            _session_two, _calls_two, credits_two = api.settle_committed_call("atomic-player", copy.deepcopy(state_document), copy.deepcopy(marker))
        # Require one movement attempt, replay-only response, one history row, one credited card, and no marker.
        self.assertEqual((settlement.apply_calls, credits, credits_two, len(history_rows), box["state"]["last_sessions"][0]["cards"][0].get("credited"), box["state"].get(api.PENDING_ACTION_KEY)), ({"BINGO_PAYOUT_CREDIT": 1}, [], [], 1, True, None))

    # Prove a lost reset-refund response clears only the exact selected session once.
    def test_lost_reset_refund_response_clears_selected_session_once(self) -> None:
        # Seed one fresh active card and sibling field.
        box = {"state": self._active_state()}
        # Commit refund proof before losing its first response.
        settlement = self._FailingSettlement(committed_types={"BINGO_CARD_REFUND"})
        # Capture history without external persistence.
        history_rows = []
        # Patch provider, settlement, wallet, and history seams.
        update_patch, load_patch = self._provider_patches(box)
        # Enter all exact reset dependencies.
        with update_patch, load_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api.players, "get_player", return_value={"balance": 100.0}), mock.patch.object(api, "append_history", side_effect=lambda *args: history_rows.append(args)):
            # Select one exact provider-current session.
            state = copy.deepcopy(box["state"])
            # Reserve reset ownership.
            marker = api.prepare_reset("atomic-player", state)
            # Reconcile the committed lost refund and clear the session.
            refunds = api.settle_prepared_reset("atomic-player", state, marker)
        # Require one refund attempt, one replayed event, one history, sibling preservation, and zero marker.
        self.assertEqual((settlement.apply_calls, len(refunds), len(history_rows), box["state"]["active_session"], box["state"]["atomic_markers"], box["state"].get(api.PENDING_ACTION_KEY)), ({"BINGO_CARD_REFUND": 1}, 1, 1, None, ["seed"], None))


# Run the focused suite directly when invoked outside the central runner.
if __name__ == "__main__":
    # Exit through unittest's standard command-line harness.
    unittest.main()
