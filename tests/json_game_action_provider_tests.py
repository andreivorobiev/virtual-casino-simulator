# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused JSON Phase0c action-journal and reset-visibility tests for issue #430."""

# Import deterministic context cleanup for provider injection.
from contextlib import contextmanager
# Import portable error numbers for lock-contention adversarial proof.
import errno
# Import bounded process coordination for cross-process gate proof.
import multiprocessing
# Import exact JSON encoding for corrupt durable-state fixtures.
import json
# Import stable digests for proving the retired root-level lock identity is absent.
import hashlib
# Import filesystem identity helpers for preserved lock proof.
import os
# Import POSIX path rules for no-write proof of the exact production literals.
import posixpath
# Import the exact empty-queue signal for planner-count assertions.
import queue
# Import temporary isolated roots for every focused test.
from pathlib import Path
# Import module injection for platform-independent Windows lock-path tests.
import sys
# Import bounded local concurrency for reentrant visibility proof.
import threading
# Import bounded timing only for proving contenders remain blocked.
import time
# Import unittest and focused call replacement.
import unittest
from unittest import mock
# Import repository-supported temporary-directory allocation.
import tempfile

# Import the two route modules whose existing behavior now shares the provider boundary.
from casino import admin, app
# Import the storage module for generic-provider compatibility patches.
from casino.core import storage as storage_module
# Import immutable Phase0c action values used by the provider conformance cases.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionResolution, GameActionResources
# Import the JSON provider and test injection boundary.
from casino.core.storage import HISTORY_FIELDS, JsonStorageProvider, StorageProvider, bootstrap_players, set_provider_for_tests
# Import stable public failures asserted by hostile cases.
from casino.errors import ConflictError, ValidationError


# Build one complete compatible player document with an exact fake-money balance.
def _players(balance: int | float = 10) -> dict:
    # Return one deterministic player row sufficient for wallet projection.
    return {
        # Preserve the current public schema marker.
        "schema_version": 2,
        # Store one exact wallet owner.
        "players": [
            {
                # Bind the action wallet identity.
                "player_id": "human",
                # Preserve the required display field.
                "display_name": "Human",
                # Preserve the public player category.
                "type": "human",
                # Store the caller-selected exact balance.
                "balance": balance,
                # Use deterministic timestamps for byte-stable rollback proof.
                "created_at": "2026-01-01T00:00:00+00:00",
                # Use the same deterministic update timestamp.
                "updated_at": "2026-01-01T00:00:00+00:00",
                # Keep the player eligible for ordinary actions.
                "status": "active",
            }
        ],
    }


# Return the exact resource declaration shared by action tests.
def _resources(*, wallets: tuple[str, ...] = ("human",), states: tuple[str, ...] = ("slots:human",)) -> GameActionResources:
    # Build the bounded immutable declaration.
    return GameActionResources(wallet_ids=wallets, state_keys=states)


# Return one resource-bound action identity.
def _identity(*, action_key: str = "action-1", request: dict | None = None, resources: GameActionResources | None = None) -> GameActionIdentity:
    # Use the ordinary paid-action resources unless overridden.
    selected_resources = resources or _resources()
    # Use one deterministic request unless the caller supplies changed semantics.
    selected_request = request if request is not None else {"stake_cents": 100, "choice": "red"}
    # Build the canonical fingerprint and durable scope.
    return GameActionIdentity.create(game_id="slots", player_id="human", action_key=action_key, resources=selected_resources, request=selected_request)


# Return one paid action plan with exact signed integer-cent movements.
def _paid_plan(snapshot) -> GameActionPlan:
    # Require the expected exact wallet before returning a deterministic outcome.
    if snapshot.wallet_balance("human") != 1000:
        # Fail the fixture without provider mutation.
        raise AssertionError("unexpected wallet snapshot")
    # Return one debit, one payout, and one route-free state replacement.
    return GameActionPlan.create(
        # Preserve only bounded immutable outcome data.
        outcome={"round_id": "round-1", "payout_cents": 250},
        # Apply one paid wager and one payout.
        movements=(
            # Debit the exact fake-money wager.
            GameActionMovement(wallet_id="human", amount_cents=-100, reason="wager"),
            # Credit the exact fake-money result.
            GameActionMovement(wallet_id="human", amount_cents=250, reason="payout"),
        ),
        # Publish one bounded action-owned state value.
        state_updates={"slots:human": {"spins": 1}},
    )


# Return one complete history row for reset and planner-purity proof.
def _history_event(round_id: str = "round-before") -> dict:
    # Return every shipped CSV column exactly once.
    return {
        # Store a deterministic event timestamp.
        "timestamp": "2026-01-01T00:00:00+00:00",
        # Bind the history row to the example game.
        "game": "slots",
        # Bind the deterministic round identity.
        "round_id": round_id,
        # Bind the wallet owner.
        "player_id": "human",
        # Preserve one compatible wager type.
        "bet_type": "spin",
        # Preserve one compatible label.
        "bet_label": "test",
        # Store the exact wager amount.
        "amount": "1.00",
        # Store one compatible terminal outcome.
        "outcome": "win",
        # Store the exact payout.
        "payout": "2.50",
        # Store the exact resulting balance.
        "balance_after": "11.50",
        # Preserve the existing serialized details field.
        "details_json": "{}",
        # Preserve the current storage schema.
        "schema_version": "2",
    }


# Capture exact data-root inventory and file bytes except the persistent legacy lock.
def _data_snapshot(provider: JsonStorageProvider) -> dict[str, bytes | None]:
    # Return an empty inventory when the reset-owned root does not exist.
    if not provider.data_dir.exists():
        # Preserve the exact absence state.
        return {}
    # Initialize one deterministic relative-path inventory.
    snapshot = {}
    # Enumerate every provider entry in portable relative order.
    for entry in sorted(provider.data_dir.rglob("*"), key=lambda item: item.relative_to(provider.data_dir).as_posix()):
        # Skip only the separately preserved legacy lock identity.
        if entry == provider.ledger_lock_path():
            # Continue without comparing mutable lock bytes.
            continue
        # Derive the exact portable relative name.
        relative = entry.relative_to(provider.data_dir).as_posix()
        # Record directories separately from exact regular-file bytes.
        snapshot[relative] = None if entry.is_dir() else entry.read_bytes()
    # Return the complete exact snapshot.
    return snapshot


# Seed one provider with wallet, document, history, and game-state bytes.
def _seed_provider(provider: JsonStorageProvider) -> None:
    # Create the complete provider directory tree under the stable gate.
    provider.ensure_ready()
    # Persist one deterministic player wallet.
    provider.bootstrap_players(_players())
    # Persist one ordinary named document.
    provider.write_document("settings/example", {"enabled": True})
    # Persist one history row through the affected public path.
    provider.append_history(_history_event())
    # Create the game-state folder already owned by the provider root.
    provider.game_data_dir.mkdir(parents=True, exist_ok=True)
    # Persist one direct game-state file used by the shipped Admin reader.
    (provider.game_data_dir / "slots.json").write_text('{"round":"before"}', encoding="utf-8")


# Provider subclass that stops once at one durable action boundary.
class _ActionFailureProvider(JsonStorageProvider):
    # Initialize the isolated provider and selected failure point.
    def __init__(self, data_dir: Path, boundary: str) -> None:
        # Initialize normal JSON provider state.
        super().__init__(data_dir)
        # Store the exact boundary to fail once.
        self.boundary = boundary
        # Track whether the injected stop was consumed.
        self.failed = False

    # Inject one process-stop-like failure without changing production checkpoints.
    def _game_action_checkpoint(self, boundary: str) -> None:
        # Fail exactly once at the selected durable boundary.
        if boundary == self.boundary and not self.failed:
            # Mark the one-shot failure consumed.
            self.failed = True
            # Simulate an abrupt process termination visible to the caller.
            raise SystemExit(boundary)


# Provider subclass that tampers after rollback copying but before verification.
class _RestoreTamperProvider(JsonStorageProvider):
    # Initialize one exact post-copy tamper mode.
    def __init__(self, data_dir: Path, mode: str = "extra") -> None:
        # Initialize ordinary provider state.
        super().__init__(data_dir)
        # Store the selected hostile verification mode.
        self.mode = mode

    # Alter the restored tree at the selected verification checkpoint.
    def _reset_recovery_checkpoint(self, boundary: str) -> None:
        # Tamper only after copy and before exact verification.
        if boundary == "restore_copied":
            # Add one unexpected entry for extra-inventory proof.
            if self.mode == "extra":
                # Add one unexpected file.
                (self.data_dir / "unexpected.json").write_text("{}", encoding="utf-8")
            # Remove one expected file for missing-inventory proof.
            elif self.mode == "missing":
                # Remove the restored player document.
                self.players_path().unlink()
            # Truncate one expected file for short-write proof.
            elif self.mode == "short":
                # Replace the restored player bytes with an empty payload.
                self.players_path().write_bytes(b"")
            # Change one expected file without changing its physical size.
            elif self.mode == "content":
                # Read the complete restored bytes.
                payload = self.players_path().read_bytes()
                # Flip one deterministic byte while preserving length.
                self.players_path().write_bytes(payload[:-1] + bytes((payload[-1] ^ 1,)))


# Provider subclass that fails restored-directory durability verification.
class _RestoreFsyncFailureProvider(JsonStorageProvider):
    # Reject the final restored namespace durability boundary.
    def _fsync_reset_directories_locked(self) -> None:
        # Surface the fixed operator recovery boundary.
        raise ConflictError("JSON reset requires operator recovery")


# Provider subclass that fails one selected parent-directory durability call.
class _FsyncFailureProvider(JsonStorageProvider):
    # Initialize the provider and selected one-based durability call.
    def __init__(self, data_dir: Path, fail_call: int) -> None:
        # Initialize ordinary provider state.
        super().__init__(data_dir)
        # Store the selected durability call.
        self.fail_call = fail_call
        # Count publication durability calls.
        self.fsync_calls = 0

    # Fail exactly one selected directory durability boundary.
    def _fsync_game_action_parent(self, path: Path) -> None:
        # Count this exact publication boundary.
        self.fsync_calls += 1
        # Fail the selected call after atomic replacement.
        if self.fsync_calls == self.fail_call:
            # Surface the fixed durable write failure.
            raise ConflictError("Game action storage write failed")
        # Delegate all other durability calls to production behavior.
        return super()._fsync_game_action_parent(path)


# Run one paid action in a spawned process and return a sanitized result.
def _process_action(root: str, action_key: str, request: dict, output, planning) -> None:
    # Construct a fresh provider instance as an independent worker.
    provider = JsonStorageProvider(Path(root))
    # Build the shared declared resources.
    resources = _resources()
    # Build the worker-specific identity semantics.
    identity = _identity(action_key=action_key, request=request, resources=resources)
    # Define one planner that records invocation before returning immutable data.
    def counted_plan(snapshot):
        # Report one planner/RNG invocation to the parent.
        planning.put("planned")
        # Return the deterministic paid plan.
        return _paid_plan(snapshot)
    try:
        # Execute or replay the action under the cross-process gate.
        receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=counted_plan)
        # Return only convergence fields needed by the focused parent.
        output.put(("ok", replayed, receipt.identity.request_fingerprint))
    # Normalize expected durable-key conflicts for the parent assertion.
    except ConflictError:
        # Return one fixed conflict marker without exception text.
        output.put(("conflict",))


# Hold one reset transaction after complete post-bootstrap state is materialized.
def _process_hold_reset(root: str, ready, release) -> None:
    # Construct a fresh provider instance as an independent reset worker.
    provider = JsonStorageProvider(Path(root))
    # Hold both stable and legacy gates across the full reset body.
    with provider.reset_transaction():
        # Persist one complete post-reset wallet.
        provider.bootstrap_players(_players(20))
        # Persist one complete post-reset history row.
        provider.append_history(_history_event("round-after"))
        # Recreate one complete post-reset game state.
        (provider.game_data_dir / "slots.json").write_text('{"round":"after"}', encoding="utf-8")
        # Signal only after the complete post-reset state exists.
        ready.set()
        # Hold final visibility until the parent releases this exact boundary.
        release.wait(10)


# Read Admin game-state and history visibility from an independent process.
def _process_read_visibility(root: str, output) -> None:
    # Construct a fresh provider instance as an independent reader.
    provider = JsonStorageProvider(Path(root))
    # Inject the exact provider into the Admin module.
    set_provider_for_tests(provider)
    # Redirect only the focused Admin game-state root.
    admin.GAME_DATA_DIR = provider.game_data_dir
    try:
        # Read both affected surfaces after acquiring the shared gate.
        output.put((admin.game_states(), provider.recent_history(10)))
    finally:
        # Clear provider injection before the process exits.
        set_provider_for_tests(None)


# Append one history row through an independent provider process.
def _process_append_history(root: str, output) -> None:
    # Construct one independent provider writer.
    provider = JsonStorageProvider(Path(root))
    # Append the distinguishable post-reset contender row.
    provider.append_history(_history_event("round-contender"))
    # Report only successful completion.
    output.put("appended")


# Hold only the shipped legacy wallet lock as an old-version process would.
def _process_hold_legacy_lock(root: str, ready, release) -> None:
    # Construct a fresh provider only to reuse the exact current-main lock primitive.
    provider = JsonStorageProvider(Path(root))
    # Create the data root needed for the historical lock path.
    provider.data_dir.mkdir(parents=True, exist_ok=True)
    # Acquire only the historical ledger lock without the new stable gate.
    with provider._exclusive_process_file_lock(provider.ledger_lock_path()):
        # Signal after the legacy lock is held.
        ready.set()
        # Hold the legacy lock for the bounded parent assertion.
        release.wait(10)


# Read one wallet through the new stable-plus-legacy bridge.
def _process_read_wallet(root: str, output) -> None:
    # Construct an independent new provider.
    provider = JsonStorageProvider(Path(root))
    # Read the exact wallet after both process gates are acquired.
    output.put(provider.load_players(_players)["players"][0]["balance"])


# Probe fresh-process bootstrap behavior in the presence of retained reset material.
def _process_bootstrap_with_residue(root: str, output) -> None:
    # Construct a fresh provider after the parent created recovery residue.
    provider = JsonStorageProvider(Path(root))
    # Inject only this isolated provider.
    set_provider_for_tests(provider)
    # Track whether bootstrap reaches the caller-owned default factory.
    default_calls = []
    try:
        # Capture exact absent or partial data bytes before bootstrap.
        before = _data_snapshot(provider)
        try:
            # Attempt the shipped bootstrap path through public guarded readiness.
            bootstrap_players(lambda: default_calls.append(True) or _players())
        # Record the expected fixed recovery failure.
        except ConflictError as error:
            # Return only fixed message, call count, and exact no-change proof.
            output.put((str(error), len(default_calls), before == _data_snapshot(provider)))
        # Report an unexpected successful bootstrap without leaking state.
        else:
            # Return one fixed unexpected marker.
            output.put(("unexpected success", len(default_calls), before == _data_snapshot(provider)))
    finally:
        # Clear provider injection before process exit.
        set_provider_for_tests(None)


# Initialize the environment-selected JSON provider in a fresh interpreter.
def _process_initialize_environment_provider(output) -> None:
    # Construct the default provider only after child import consumed its inherited environment.
    provider = JsonStorageProvider()
    # Initialize the private stable gate and ordinary provider directories.
    provider.ensure_ready()
    # Return only canonical configured roots and control identities.
    output.put(
        (
            # Return the canonical data root selected from CASINO_DATA_DIR.
            provider._json_root_key(),
            # Return the canonical log root selected from CASINO_LOG_DIR.
            os.path.normcase(os.path.realpath(os.fspath(provider.log_dir))),
            # Return the verified private control root.
            os.fspath(provider._json_control_root()),
            # Prove the stable gate was initialized.
            provider.json_gate_path().is_file(),
        )
    )


# Minimal non-JSON provider used to prove old reset orchestration compatibility.
class _NonJsonResetProvider(StorageProvider):
    # Identify the fake as non-JSON without invoking MySQL.
    name = "mysql-like"

    # Initialize one reset-call counter.
    def __init__(self) -> None:
        # Count route-owned provider resets.
        self.reset_calls = 0

    # Preserve the existing provider reset hook.
    def reset(self) -> None:
        # Record exactly one provider reset invocation.
        self.reset_calls += 1


# Exercise the route-free JSON action journal and reset transaction.
class JsonGameActionProviderTests(unittest.TestCase):
    # Allocate one isolated provider root per focused test.
    def setUp(self) -> None:
        # Create a task-owned temporary parent outside repository data.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve one isolated provider data root.
        self.root = Path(self.temporary.name) / "data"
        # Construct the provider under test.
        self.provider = JsonStorageProvider(self.root)
        # Inject the provider for route modules used by focused cases.
        set_provider_for_tests(self.provider)

    # Remove provider injection and isolated bytes after each case.
    def tearDown(self) -> None:
        # Clear process-wide provider injection first.
        set_provider_for_tests(None)
        # Remove the exact task-owned temporary tree.
        self.temporary.cleanup()

    # Prove paid settlement, immutable replay, conflict-before-planner, and zero-cost receipt.
    def test_paid_zero_cost_replay_and_conflict_semantics(self):
        # Seed the exact wallet required by the paid plan.
        self.provider.bootstrap_players(_players())
        # Build the paid action resources and identity.
        resources = _resources()
        # Bind one durable key to its canonical request.
        identity = _identity(resources=resources)
        # Execute the new action once.
        receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
        # Require one new immutable commit.
        self.assertFalse(replayed)
        # Require exact debit-plus-credit wallet convergence.
        self.assertEqual(11.5, self.provider.load_players(_players)["players"][0]["balance"])
        # Require one append-only ledger row for each exact signed movement.
        ledger_rows = self.provider.read_ledger_recent("human", 10)
        # Preserve debit then payout order without duplicate replay rows.
        self.assertEqual([-1, 2.5], [row["amount"] for row in ledger_rows])
        # Require the exact action-owned state projection.
        self.assertEqual(1, dict(receipt.snapshot_after.state_value("slots:human").items)["spins"])
        # Count planner calls after the durable receipt exists.
        planner_calls = []
        # Replay without invoking the replacement planner.
        replay_receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda snapshot: planner_calls.append(snapshot))
        # Require exact immutable receipt replay.
        self.assertTrue(replayed)
        # Require the original receipt value.
        self.assertEqual(receipt, replay_receipt)
        # Require no planner or RNG call on replay.
        self.assertEqual([], planner_calls)
        # Build changed semantics under the same durable action key.
        conflict = _identity(resources=resources, request={"stake_cents": 200, "choice": "red"})
        # Reject the mismatch before planner or mutation.
        with self.assertRaises(ConflictError):
            # Attempt conflicting key reuse.
            self.provider.execute_game_action_once(identity=conflict, resources=resources, planner=lambda snapshot: planner_calls.append(snapshot))
        # Require no hidden planner invocation.
        self.assertEqual([], planner_calls)
        # Build one state-only zero-cost resource declaration.
        zero_resources = _resources(wallets=(), states=("free:human",))
        # Bind one distinct zero-cost durable key.
        zero_identity = _identity(action_key="free-1", resources=zero_resources, request={"free": True})
        # Build one zero-cost immutable plan.
        def zero_plan(_snapshot):
            # Return state and outcome with no wallet movement.
            return GameActionPlan.create(outcome={"free": True}, state_updates={"free:human": {"used": True}})
        # Execute the zero-cost action.
        zero_receipt, zero_replayed = self.provider.execute_game_action_once(identity=zero_identity, resources=zero_resources, planner=zero_plan)
        # Require one new zero-cost receipt.
        self.assertFalse(zero_replayed)
        # Require no movement rows.
        self.assertEqual((), zero_receipt.plan.movements)
        # Require wallet bytes remain unchanged.
        self.assertEqual(11.5, self.provider.load_players(_players)["players"][0]["balance"])

    # Prove JSON reset preserves immutable history while isolating fresh same-key work by epoch.
    def test_reset_epoch_preserves_history_blocks_gap_and_allows_fresh_key(self):
        # Seed the exact wallet required by the paid action.
        self.provider.bootstrap_players(_players())
        # Bind one durable action in implicit legacy epoch one.
        resources, identity = _resources(), _identity(action_key="reset-epoch", resources=_resources())
        # Commit the original action and its immutable lifecycle rows.
        first_receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
        # Require one new epoch-one commit.
        self.assertFalse(replayed)
        # Hold reset, fresh bootstrap, and phase release under the existing global gate.
        with self.provider.reset_transaction():
            # Require the new namespace to remain unavailable through caller bootstrap.
            self.assertEqual({"schema_version": 1, "current_epoch": 2, "phase": "resetting"}, json.loads(self.provider.game_action_epoch_path().read_text(encoding="utf-8")))
            # Refuse action execution before planner or another claim.
            with self.assertRaisesRegex(ConflictError, "reset is in progress"):
                # Keep a replacement planner unreachable.
                self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("reset gap invoked planner"))
            # Return finite pending without a tombstone while reset owns visibility.
            self.assertEqual(GameActionResolution(status="pending"), self.provider.resolve_game_action(identity=identity, resources=resources))
            # Bootstrap the exact compatible wallet inside the reentrant gate.
            self.provider.bootstrap_players(_players())
        # Publish the second namespace only after bootstrap succeeds.
        self.assertEqual({"schema_version": 1, "current_epoch": 2, "phase": "ready"}, json.loads(self.provider.game_action_epoch_path().read_text(encoding="utf-8")))
        # Execute the identical caller key as fresh work in epoch two.
        second_receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
        # Require a planner-backed fresh commit rather than old receipt replay.
        self.assertFalse(replayed)
        # Preserve equivalent deterministic result semantics without sharing lifecycle identity.
        self.assertEqual(first_receipt, second_receipt)
        # Resolve the current action through the provider-neutral public result shape.
        public_resolution = self.provider.resolve_game_action(identity=identity, resources=resources)
        # Render only public contract objects as an API/logging proxy.
        public_rendering = repr(second_receipt) + repr(public_resolution)
        # Keep private epoch field names and values out of receipts and resolutions.
        self.assertNotIn("reset_epoch", public_rendering)
        # Keep the private singleton control name out of public result material too.
        self.assertNotIn("current_epoch", public_rendering)
        # Read the complete private epoch-scoped receipt registry.
        receipt_registry = json.loads(self.provider.game_action_receipts_path().read_text(encoding="utf-8"))
        # Retain the same scope once in each immutable namespace.
        self.assertEqual({"1", "2"}, set(receipt_registry["receipts_by_epoch"]))
        # Read the corresponding claim history.
        claim_registry = json.loads(self.provider.game_action_claims_path().read_text(encoding="utf-8"))
        # Retain both execute claims without deleting or rewriting the old winner.
        self.assertEqual({"1", "2"}, set(claim_registry["claims_by_epoch"]))
        # Append only the current epoch's two ledger movements after reset cleared prior rows.
        self.assertEqual(2, len(self.provider.read_ledger_recent("human", 10)))

    # Prove JSON reset body/finalize failure restores epoch and every prior byte exactly.
    def test_reset_epoch_failure_restores_complete_legacy_bytes(self):
        # Seed one wallet and committed legacy epoch-one action.
        self.provider.bootstrap_players(_players())
        # Commit exact lifecycle and mutable state before rollback proof.
        self.provider.execute_game_action_once(identity=_identity(action_key="reset-rollback"), resources=_resources(), planner=_paid_plan)
        # Snapshot every provider byte before the failed reset begins.
        before = _data_snapshot(self.provider)
        # Fail caller bootstrap after phase resetting has been durably written.
        with self.assertRaisesRegex(RuntimeError, "bootstrap failed"):
            # Enter the exact reset transaction.
            with self.provider.reset_transaction():
                # Surface one caller-body failure.
                raise RuntimeError("bootstrap failed")
        # Restore the legacy missing-epoch-file shape and every immutable/mutable byte.
        self.assertEqual(before, _data_snapshot(self.provider))
        # Save the production epoch writer for a finalize-only failure seam.
        original_writer = self.provider._write_game_action_epoch
        # Define one failure that permits resetting publication but refuses ready release.
        def fail_ready(*, current_epoch, phase):
            # Interrupt only the final visibility transition.
            if phase == "ready":
                # Model one durable write failure before publication.
                raise OSError("synthetic finalize failure")
            # Delegate the resetting write unchanged.
            return original_writer(current_epoch=current_epoch, phase=phase)
        # Inject the phase-two write failure for one complete reset attempt.
        with mock.patch.object(self.provider, "_write_game_action_epoch", side_effect=fail_ready):
            # Normalize only the original synthetic failure after exact rollback.
            with self.assertRaisesRegex(OSError, "finalize failure"):
                # Run reset with a successful bounded bootstrap body.
                with self.provider.reset_transaction():
                    # Recreate the default wallet before finalization fails.
                    self.provider.bootstrap_players(_players())
        # Restore the complete pre-reset tree after finalize failure too.
        self.assertEqual(before, _data_snapshot(self.provider))

    # Prove resolver-first, executor-first, pending, conflicts, and legacy compatibility.
    def test_resolution_claims_are_immutable_planner_free_and_restart_safe(self):
        # Seed the exact wallet required by the paid plan.
        self.provider.bootstrap_players(_players())
        # Build one complete resource declaration.
        resources = _resources()
        # Resolve one unused identity before execution.
        resolver_first = _identity(action_key="resolver-first", resources=resources)
        # Commit the immutable no-result tombstone.
        resolution = self.provider.resolve_game_action(identity=resolver_first, resources=resources)
        # Return the exact provider-neutral terminal shape.
        self.assertEqual(GameActionResolution(status="uncommitted"), resolution)
        # Capture exact provider bytes after the first resolver claim.
        first_bytes = self.provider.game_action_claims_path().read_bytes()
        # Replay resolution without rewriting append-only claim bytes.
        self.assertEqual(resolution, self.provider.resolve_game_action(identity=resolver_first, resources=resources))
        # Preserve exact claim bytes on compatible replay.
        self.assertEqual(first_bytes, self.provider.game_action_claims_path().read_bytes())
        # Reject a late executor without invoking its planner.
        with self.assertRaisesRegex(ConflictError, "^Game action was durably resolved as uncommitted$"):
            # Attempt execution behind the resolver-owned tombstone.
            self.provider.execute_game_action_once(identity=resolver_first, resources=resources, planner=lambda _snapshot: self.fail("late executor invoked planner"))
        # Reject changed resolver semantics without rewriting the winning row.
        changed = _identity(action_key="resolver-first", resources=resources, request={"stake_cents": 200})
        # Require one fixed durable-semantic conflict.
        with self.assertRaisesRegex(ConflictError, "^Game action key conflicts with durable semantics$"):
            # Attempt changed semantic resolution.
            self.provider.resolve_game_action(identity=changed, resources=resources)
        # Preserve exact claim bytes after conflict.
        self.assertEqual(first_bytes, self.provider.game_action_claims_path().read_bytes())
        # Execute one distinct identity first.
        executor_first = _identity(action_key="executor-first", resources=resources)
        # Commit its complete receipt.
        receipt, replayed = self.provider.execute_game_action_once(identity=executor_first, resources=resources, planner=_paid_plan)
        # Require one new execution.
        self.assertFalse(replayed)
        # Resolve the exact immutable committed receipt.
        self.assertEqual(GameActionResolution(status="committed", receipt=receipt), self.provider.resolve_game_action(identity=executor_first, resources=resources))
        # Remove only claims to simulate an exact schema-three JSON receipt store.
        self.provider.game_action_claims_path().unlink()
        # Preserve exact receipt registry bytes across legacy committed resolution.
        receipt_bytes = self.provider.game_action_receipts_path().read_bytes()
        # Resolve the legacy receipt without backfilling or rewriting claims.
        self.assertEqual(GameActionResolution(status="committed", receipt=receipt), self.provider.resolve_game_action(identity=executor_first, resources=resources))
        # Keep the legacy receipt byte-for-byte unchanged.
        self.assertEqual(receipt_bytes, self.provider.game_action_receipts_path().read_bytes())
        # Keep the absent claim registry absent on legacy read compatibility.
        self.assertFalse(self.provider.game_action_claims_path().exists())
        # Hold the provider instance lock to model an active same-process executor.
        ready = threading.Event()
        # Collect the finite concurrent resolver result.
        output = []
        # Define one contender that resolves while the main thread owns execution.
        def contender():
            # Signal that the resolver thread started.
            ready.set()
            # Retain the finite provider-neutral result.
            output.append(self.provider.resolve_game_action(identity=_identity(action_key="pending", resources=resources), resources=resources))
        # Acquire the executor-owned instance lock before starting the contender.
        with self.provider.lock:
            # Start the resolver in another thread.
            worker = threading.Thread(target=contender)
            # Launch the bounded contender.
            worker.start()
            # Require the contender to reach its resolution call.
            self.assertTrue(ready.wait(2))
            # Allow the nonblocking call to complete while ownership remains held.
            worker.join(2)
            # Require no blocking behind active execution.
            self.assertFalse(worker.is_alive())
        # Return exact pending without durable claim mutation.
        self.assertEqual([GameActionResolution(status="pending")], output)

    # Prove nonblocking resolution masks only genuine lock contention.
    def test_nonblocking_lock_fails_closed_on_filesystem_and_descriptor_errors(self):
        # Build one fake Windows lock module so every failure path runs on every host.
        lock_module = mock.Mock(LK_NBLCK=1, LK_UNLCK=2)

        # Build one context-manager path around a caller-owned fake handle.
        def fake_path(handle):
            # Construct one path-like mock with a writable parent seam.
            path = mock.MagicMock()
            # Return the supplied handle from the binary append context.
            path.open.return_value.__enter__.return_value = handle
            # Preserve ordinary context exit behavior.
            path.open.return_value.__exit__.return_value = False
            # Return the complete path-like fixture.
            return path

        # Exercise seek, write, flush, and locking failures independently.
        failures = ("seek", "write", "flush", "locking")
        # Run the Windows branch deterministically even on POSIX CI.
        with mock.patch.object(storage_module.os, "name", "nt"), mock.patch.dict(sys.modules, {"msvcrt": lock_module}):
            # Visit each exact failing operation.
            for operation in failures:
                # Identify the bounded adversarial step.
                with self.subTest(operation=operation):
                    # Allocate a fresh binary-handle test double.
                    handle = mock.MagicMock()
                    # Return an empty file for lock-byte initialization by default.
                    handle.seek.return_value = 0
                    # Return one stable descriptor for the locking call.
                    handle.fileno.return_value = 7
                    # Reset the shared module behavior between cases.
                    lock_module.locking.reset_mock(side_effect=True)
                    # Inject one non-contention I/O failure at the selected boundary.
                    if operation == "locking":
                        # Fail the lock call with a descriptor-level I/O error.
                        lock_module.locking.side_effect = OSError(errno.EIO, "synthetic")
                    else:
                        # Fail the selected handle method before lock ownership.
                        getattr(handle, operation).side_effect = OSError(errno.EIO, "synthetic")
                    # Require the unexpected filesystem/descriptor error to propagate.
                    with self.assertRaises(OSError):
                        # Attempt the complete nonblocking lock context.
                        with self.provider._try_exclusive_process_file_lock(fake_path(handle)):
                            # Keep the protected body unreachable on acquisition failure.
                            self.fail("unexpected lock acquisition")
            # Allocate one fresh handle for exact contention classification.
            contender_handle = mock.MagicMock()
            # Require one existing lock byte so setup does not write.
            contender_handle.seek.return_value = 1
            # Return one stable descriptor for the contender.
            contender_handle.fileno.return_value = 8
            # Raise only the documented access-denied contention code.
            lock_module.locking.side_effect = OSError(errno.EACCES, "synthetic")
            # Convert genuine lock contention to the finite unavailable result.
            with self.provider._try_exclusive_process_file_lock(fake_path(contender_handle)) as acquired:
                # Require exact false without swallowing other failures.
                self.assertFalse(acquired)

    # Prove a stopped pre-planner reservation becomes terminal without a second planner.
    def test_resolver_converts_prepared_restart_to_uncommitted(self):
        # Allocate one isolated provider that stops at the prepared boundary.
        with tempfile.TemporaryDirectory() as directory:
            # Construct the one-shot provider.
            provider = _ActionFailureProvider(Path(directory) / "data", "prepared")
            # Seed the exact paid wallet.
            provider.bootstrap_players(_players())
            # Build the exact action semantics.
            resources = _resources()
            # Bind one restart-stable identity.
            identity = _identity(action_key="prepared-resolve", resources=resources)
            # Stop before planner invocation.
            with self.assertRaises(SystemExit):
                # Begin the original execution attempt.
                provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
            # Resolve through a fresh provider after the stopped owner disappears.
            restarted = JsonStorageProvider(provider.data_dir)
            # Commit one immutable uncommitted tombstone without planning.
            self.assertEqual(GameActionResolution(status="uncommitted"), restarted.resolve_game_action(identity=identity, resources=resources))
            # Remove the obsolete pre-planner journal.
            self.assertFalse(restarted.game_action_journal_path().exists())
            # Preserve the original wallet exactly.
            self.assertEqual(10, restarted.load_players(_players)["players"][0]["balance"])
            # Leave no ledger movement for the uncommitted action.
            self.assertEqual([], restarted.read_ledger_recent("human", 10))
            # Reject every late executor without planner/RNG.
            with self.assertRaisesRegex(ConflictError, "^Game action was durably resolved as uncommitted$"):
                # Attempt late execution behind the tombstone.
                restarted.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("late planner invoked"))

    # Prove every durable post-plan boundary converges on restart without new planner entropy.
    def test_restart_recovery_reuses_durable_plan_at_every_projection_boundary(self):
        # Exercise every post-plan write and cleanup checkpoint.
        for boundary in ("planned", "wallet_applied", "ledger_applied", "state_applied", "receipt_committed", "cleanup"):
            # Identify the exact injected boundary.
            with self.subTest(boundary=boundary):
                # Allocate an isolated data root for this failure boundary.
                with tempfile.TemporaryDirectory() as directory:
                    # Construct the one-shot failure provider.
                    provider = _ActionFailureProvider(Path(directory) / "data", boundary)
                    # Seed its exact paid-action wallet.
                    provider.bootstrap_players(_players())
                    # Build one unique identity for this boundary.
                    resources = _resources()
                    # Bind the boundary into the durable key only.
                    identity = _identity(action_key=f"action-{boundary}", resources=resources)
                    # Stop after the selected durable checkpoint.
                    with self.assertRaises(SystemExit):
                        # Execute the first action attempt.
                        provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
                    # Reopen through a fresh provider instance to simulate restart.
                    restarted = JsonStorageProvider(provider.data_dir)
                    # Track whether recovery incorrectly invokes new entropy.
                    planner_calls = []
                    # Recover the original immutable plan and receipt.
                    receipt, replayed = restarted.execute_game_action_once(identity=identity, resources=resources, planner=lambda snapshot: planner_calls.append(snapshot))
                    # Require receipt convergence.
                    self.assertTrue(replayed)
                    # Require the original planned payout.
                    self.assertEqual(250, dict(receipt.plan.outcome.items)["payout_cents"])
                    # Require no second planner call.
                    self.assertEqual([], planner_calls)
                    # Require exactly one wallet result.
                    self.assertEqual(11.5, restarted.load_players(_players)["players"][0]["balance"])
                    # Require exactly one debit and payout ledger row after every restart boundary.
                    self.assertEqual(2, len(restarted.read_ledger_recent("human", 10)))
                    # Require journal cleanup after convergence.
                    self.assertFalse(restarted.game_action_journal_path().exists())

    # Prove prepared restart retries planning while post-plan conflicts never recover first.
    def test_prepared_retry_and_post_plan_conflict_ordering(self):
        # Allocate one isolated prepared-stage failure root.
        with tempfile.TemporaryDirectory() as directory:
            # Construct the prepared-stage failure provider.
            provider = _ActionFailureProvider(Path(directory) / "data", "prepared")
            # Seed the exact paid wallet.
            provider.bootstrap_players(_players())
            # Build one durable action request.
            resources = _resources()
            # Bind one unique prepared-stage key.
            identity = _identity(action_key="prepared-retry", resources=resources)
            # Stop after durable reservation but before planner execution.
            with self.assertRaises(SystemExit):
                # Execute the first attempt.
                provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
            # Reopen through a fresh provider.
            restarted = JsonStorageProvider(provider.data_dir)
            # Track the one retry planner call.
            planner_calls = []
            # Define one valid counted planner.
            def counted(snapshot):
                # Record the exact retry snapshot.
                planner_calls.append(snapshot)
                # Return the ordinary paid plan.
                return _paid_plan(snapshot)
            # Retry after the pre-planner reservation.
            _receipt, replayed = restarted.execute_game_action_once(identity=identity, resources=resources, planner=counted)
            # Require the prepared reservation to retry as a new action.
            self.assertFalse(replayed)
            # Require exactly one retry planner call.
            self.assertEqual(1, len(planner_calls))
            # Require exactly one wallet settlement.
            self.assertEqual(11.5, restarted.load_players(_players)["players"][0]["balance"])
        # Exercise conflicts against two post-planner durable stages.
        for boundary in ("planned", "wallet_applied"):
            # Identify the exact pending stage.
            with self.subTest(boundary=boundary):
                # Allocate one isolated pending-stage root.
                with tempfile.TemporaryDirectory() as directory:
                    # Construct the one-shot pending-stage provider.
                    provider = _ActionFailureProvider(Path(directory) / "data", boundary)
                    # Seed the exact wallet.
                    provider.bootstrap_players(_players())
                    # Build the ordinary resources.
                    resources = _resources()
                    # Bind the original durable semantics.
                    original = _identity(action_key=f"conflict-{boundary}", resources=resources)
                    # Stop after the selected durable stage.
                    with self.assertRaises(SystemExit):
                        # Execute the original action attempt.
                        provider.execute_game_action_once(identity=original, resources=resources, planner=_paid_plan)
                    # Reopen through a new provider instance.
                    restarted = JsonStorageProvider(provider.data_dir)
                    # Capture every provider byte before conflicting retry.
                    before = _data_snapshot(restarted)
                    # Build changed semantics under the same durable scope.
                    conflict = _identity(action_key=f"conflict-{boundary}", resources=resources, request={"stake_cents": 200})
                    # Track planner calls that must not occur.
                    planner_calls = []
                    # Reject conflict before recovery projection.
                    with self.assertRaises(ConflictError):
                        # Attempt changed reuse.
                        restarted.execute_game_action_once(identity=conflict, resources=resources, planner=lambda snapshot: planner_calls.append(snapshot))
                    # Require no planner call.
                    self.assertEqual([], planner_calls)
                    # Require no journal, wallet, state, or receipt projection changed.
                    self.assertEqual(before, _data_snapshot(restarted))
                    # Recover the original semantics afterward.
                    _receipt, replayed = restarted.execute_game_action_once(identity=original, resources=resources, planner=lambda snapshot: planner_calls.append(snapshot))
                    # Require exact original receipt replay.
                    self.assertTrue(replayed)
                    # Require no new planner entropy for the durable plan.
                    self.assertEqual([], planner_calls)

    # Prove corrupt journals remain byte-exact and stale private temps are boundedly cleaned.
    def test_corrupt_journal_preservation_stale_temp_cleanup_and_fsync_recovery(self):
        # Seed one compatible wallet.
        self.provider.bootstrap_players(_players())
        # Create the private action directory.
        self.provider.game_action_journal_path().parent.mkdir(parents=True, exist_ok=True)
        # Persist one truncated journal.
        corrupt_bytes = b'{"schema_version":1,"stage":'
        # Write exact hostile bytes directly for recovery proof.
        self.provider.game_action_journal_path().write_bytes(corrupt_bytes)
        # Fail closed on the next affected read.
        with self.assertRaisesRegex(ConflictError, "Game action storage requires operator recovery"):
            # Attempt wallet visibility.
            self.provider.load_players(_players)
        # Require exact corrupt bytes remain unchanged.
        self.assertEqual(corrupt_bytes, self.provider.game_action_journal_path().read_bytes())
        # Remove only the hostile journal for the next independent case.
        self.provider.game_action_journal_path().unlink()
        # Seed all three exact private temp prefixes.
        stale_temps = [
            # Seed one journal temp.
            self.provider.game_action_journal_path().parent / "journal.json.tmp-stale",
            # Seed one receipt temp.
            self.provider.game_action_journal_path().parent / "receipts.json.tmp-stale",
            # Seed one lifecycle-claim temp.
            self.provider.game_action_journal_path().parent / "claims.json.tmp-stale",
            # Seed one state temp.
            self.provider.game_action_journal_path().parent / "states.json.tmp-stale",
        ]
        # Persist distinguishable stale bytes.
        for temporary in stale_temps:
            # Write only the exact provider-owned temp path.
            temporary.write_bytes(b"stale")
        # Capture all non-temp provider bytes.
        before = {key: value for key, value in _data_snapshot(self.provider).items() if ".tmp-stale" not in key}
        # Enter one affected read to clean stale private temps.
        self.provider.load_players(_players)
        # Require every exact stale temp removed.
        self.assertTrue(all(not temporary.exists() for temporary in stale_temps))
        # Require all permanent provider bytes unchanged.
        self.assertEqual(before, _data_snapshot(self.provider))
        # Allocate a fresh root for a post-replace planned-stage fsync failure.
        with tempfile.TemporaryDirectory() as directory:
            # Fail the second journal directory fsync, which publishes the complete plan.
            failing = _FsyncFailureProvider(Path(directory) / "data", 2)
            # Seed the exact wallet.
            failing.bootstrap_players(_players())
            # Build one durable request.
            resources = _resources()
            # Bind one unique action key.
            identity = _identity(action_key="fsync-planned", resources=resources)
            # Require the injected publication failure.
            with self.assertRaises(ConflictError):
                # Execute until the post-replace directory fsync fails.
                failing.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
            # Require the atomically replaced planned journal to remain recoverable.
            self.assertTrue(failing.game_action_journal_path().exists())
            # Reopen after the simulated process boundary.
            restarted = JsonStorageProvider(failing.data_dir)
            # Track prohibited replacement planner calls.
            planner_calls = []
            # Recover the durable planned outcome.
            receipt, replayed = restarted.execute_game_action_once(identity=identity, resources=resources, planner=lambda snapshot: planner_calls.append(snapshot))
            # Require exact replay recovery.
            self.assertTrue(replayed)
            # Require the original planned payout.
            self.assertEqual(250, dict(receipt.plan.outcome.items)["payout_cents"])
            # Require no replacement entropy.
            self.assertEqual([], planner_calls)

    # Prove planner failure and direct planner side effects leave all state retryable.
    def test_planner_failure_and_public_mutations_are_fail_closed(self):
        # Seed the exact paid wallet and one ordinary document.
        self.provider.bootstrap_players(_players())
        # Persist one ordinary document before planner execution.
        self.provider.write_document("settings/example", {"value": 1})
        # Capture exact pre-planner provider bytes.
        before = _data_snapshot(self.provider)
        # Build one action identity.
        resources = _resources()
        # Bind one retryable durable key.
        identity = _identity(action_key="planner-failure", resources=resources)
        # Define one planner that attempts each affected mutation.
        mutations = (
            # Attempt direct wallet replacement.
            lambda: self.provider.bootstrap_players(_players(99)),
            # Attempt row-scoped wallet update.
            lambda: self.provider.update_player("human", lambda row: row.update({"balance": 99})),
            # Attempt ordinary ledger mutation.
            lambda: self.provider.transact_ledger("human", -1, "TEST"),
            # Attempt once-only ledger mutation.
            lambda: self.provider.transact_ledger_once("human", -1, "TEST", "planner-ledger"),
            # Attempt named-document replacement.
            lambda: self.provider.write_document("settings/example", {"value": 2}),
            # Attempt named-document read-modify-write.
            lambda: self.provider.update_document("settings/example", lambda value: {"value": 2}, {}),
            # Attempt history mutation.
            lambda: self.provider.append_history(_history_event("planner")),
        )
        # Exercise every public mutation independently.
        for index, mutation in enumerate(mutations):
            # Identify only the mutation index.
            with self.subTest(index=index):
                # Define one planner that attempts the selected mutation.
                def hostile(_snapshot, selected=mutation):
                    # Invoke the affected public provider mutation.
                    selected()
                    # Return an unreachable valid plan.
                    return _paid_plan(_snapshot)
                # Reject the side effect before any state change.
                with self.assertRaises(ValidationError):
                    # Attempt the action with the hostile planner.
                    self.provider.execute_game_action_once(identity=identity, resources=resources, planner=hostile)
                # Require exact pre-planner bytes after rejection.
                self.assertEqual(before, _data_snapshot(self.provider))
        # Define a pure planner that raises its own failure.
        def failing(_snapshot):
            # Raise before returning a plan.
            raise RuntimeError("planner stopped")
        # Preserve planner failure without mutation.
        with self.assertRaises(RuntimeError):
            # Attempt the failing planner.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=failing)
        # Require no prepared journal residue.
        self.assertFalse(self.provider.game_action_journal_path().exists())
        # Retry the same key safely with the valid planner.
        receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
        # Require the retry to become the one new action.
        self.assertFalse(replayed)
        # Require the expected result.
        self.assertEqual(250, dict(receipt.plan.outcome.items)["payout_cents"])

    # Prove cross-process identical duplicates converge and conflicting duplicates do not both plan.
    def test_cross_process_duplicate_and_conflict_convergence(self):
        # Seed the shared paid-action wallet.
        self.provider.bootstrap_players(_players())
        # Use spawn so no thread-local or file-handle state is inherited.
        context = multiprocessing.get_context("spawn")
        # Create one process-safe result queue.
        output = context.Queue()
        # Create one process-safe planner invocation queue.
        planning = context.Queue()
        # Build two identical independent worker processes.
        workers = [
            # Configure each worker with the same durable identity.
            context.Process(target=_process_action, args=(str(self.root), "same-key", {"stake_cents": 100, "choice": "red"}, output, planning))
            # Create exactly two bounded contenders.
            for _index in range(2)
        ]
        # Start both contenders.
        for worker in workers:
            # Launch the independent provider process.
            worker.start()
        # Join each process with a bounded deadlock timeout.
        for worker in workers:
            # Wait for the process to finish.
            worker.join(15)
            # Require no deadlock or abnormal exit.
            self.assertEqual(0, worker.exitcode)
        # Read both sanitized convergence results.
        results = [output.get(timeout=2) for _index in range(2)]
        # Require two compatible receipts.
        self.assertEqual(["ok", "ok"], sorted(result[0] for result in results))
        # Require exactly one original action and one replay.
        self.assertEqual([False, True], sorted(result[1] for result in results))
        # Require exactly one cross-process planner/RNG invocation.
        self.assertEqual("planned", planning.get(timeout=2))
        # Require no second planner/RNG invocation.
        with self.assertRaises(queue.Empty):
            # Attempt a bounded second queue read.
            planning.get(timeout=0.1)
        # Require exactly one wallet settlement.
        self.assertEqual(11.5, self.provider.load_players(_players)["players"][0]["balance"])
        # Reset to a clean shared root for conflicting concurrency.
        self.provider.reset()
        # Restore the original wallet.
        self.provider.bootstrap_players(_players())
        # Create one process per conflicting request under the same key.
        conflicts = [
            # Use distinct request semantics for durable conflict.
            context.Process(target=_process_action, args=(str(self.root), "conflict-key", request, output, planning))
            # Enumerate the two exact conflicting requests.
            for request in ({"stake_cents": 100, "choice": "red"}, {"stake_cents": 200, "choice": "red"})
        ]
        # Start both conflicting contenders.
        for worker in conflicts:
            # Launch the independent provider process.
            worker.start()
        # Join both conflicting contenders.
        for worker in conflicts:
            # Wait with the same bounded timeout.
            worker.join(15)
            # Require normal handled exits.
            self.assertEqual(0, worker.exitcode)
        # Read both conflict results.
        conflict_results = [output.get(timeout=2) for _index in range(2)]
        # Require one new action and one pre-planner conflict.
        self.assertEqual(["conflict", "ok"], sorted(result[0] for result in conflict_results))
        # Require exactly one planner/RNG invocation across conflicting processes.
        self.assertEqual("planned", planning.get(timeout=2))
        # Require conflict to avoid a second planner/RNG invocation.
        with self.assertRaises(queue.Empty):
            # Attempt a bounded second queue read.
            planning.get(timeout=0.1)
        # Require exactly one settlement despite conflict.
        self.assertEqual(11.5, self.provider.load_players(_players)["players"][0]["balance"])

    # Prove app-body failures restore exact pre-reset bytes and clean staging.
    def test_reset_route_failures_restore_exact_state_and_response_projection_is_inside_gate(self):
        # Seed complete state spanning every cleared provider surface.
        _seed_provider(self.provider)
        # Capture exact pre-reset bytes.
        before = _data_snapshot(self.provider)
        # Build the current router once.
        router = app.build_router()
        # Resolve the exact shipped reset route.
        reset_route = next(route for route in router.routes if route.method == "POST" and route.regex.pattern == "^/api/v1/casino/reset$")
        # Enumerate each route-body boundary after destructive reset begins.
        boundaries = ("ensure", "players", "admin", "games", "visibility")
        # Exercise every injected caller-body failure.
        for boundary in boundaries:
            # Identify the exact failing boundary.
            with self.subTest(boundary=boundary):
                # Restore the complete seed before each independent case.
                if _data_snapshot(self.provider) != before:
                    # Replace divergent fixture state through one rollback-safe transaction.
                    with self.provider.reset_transaction():
                        # Restore deterministic player state.
                        self.provider.bootstrap_players(_players())
                        # Restore deterministic document state.
                        self.provider.write_document("settings/example", {"enabled": True})
                        # Restore deterministic history state.
                        self.provider.append_history(_history_event())
                        # Restore deterministic game-state bytes.
                        (self.provider.game_data_dir / "slots.json").write_text('{"round":"before"}', encoding="utf-8")
                # Build default no-op route dependencies.
                ensure = mock.Mock()
                # Build deterministic player bootstrap.
                bootstrap_players = mock.Mock(side_effect=lambda state: self.provider.bootstrap_players(state))
                # Build deterministic Admin bootstrap.
                bootstrap = mock.Mock()
                # Build deterministic catalog projection.
                games = mock.Mock(return_value=[{"game": "slots"}])
                # Build deterministic final player projection.
                visible = mock.Mock(return_value=_players()["players"])
                # Attach the selected injected failure.
                selected = {"ensure": ensure, "players": bootstrap_players, "admin": bootstrap, "games": games, "visibility": visible}[boundary]
                # Fail at the exact selected route-body boundary.
                selected.side_effect = RuntimeError("injected reset boundary")
                # Patch only route collaborators while preserving route auth invocation.
                with mock.patch.object(app.auth, "require_admin"), mock.patch.object(app, "ensure_dirs", ensure), mock.patch.object(self.provider, "bootstrap_players", bootstrap_players), mock.patch.object(app.auth, "bootstrap_admin_from_env", bootstrap), mock.patch.object(app, "list_games", games), mock.patch.object(app.players, "list_players", visible):
                    # Require the injected route failure.
                    with self.assertRaises(RuntimeError):
                        # Invoke the listener-free existing route handler.
                        reset_route.handler({}, {}, context={"user": {"roles": ["admin"]}})
                # Require exact byte-for-byte pre-reset restoration.
                self.assertEqual(before, _data_snapshot(self.provider))
                # Require no final or temporary reset recovery artifact.
                self.assertEqual([], list(self.provider._json_control_root().glob(f"{self.provider._reset_backup_prefix()}*")))

    # Prove cleanup errors rollback and unverifiable restore retains a fail-closed artifact.
    def test_reset_cleanup_and_restore_verification_fail_closed(self):
        # Seed complete pre-reset state.
        _seed_provider(self.provider)
        # Capture exact bytes before the attempted reset.
        before = _data_snapshot(self.provider)
        # Preserve the real cleanup method for the retry.
        real_remove = self.provider._remove_reset_backup
        # Count cleanup attempts.
        attempts = []
        # Fail only the first pre-commit cleanup call.
        def fail_once(backup):
            # Record this cleanup attempt.
            attempts.append(backup)
            # Fail the first call while leaving the single archive intact.
            if len(attempts) == 1:
                # Surface the fixed cleanup boundary.
                raise ConflictError("JSON reset cleanup failed")
            # Delegate the rollback cleanup retry.
            return real_remove(backup)
        # Inject one cleanup failure.
        with mock.patch.object(self.provider, "_remove_reset_backup", side_effect=fail_once):
            # Require the reset to report cleanup failure.
            with self.assertRaisesRegex(ConflictError, "JSON reset cleanup failed"):
                # Attempt a complete post-reset bootstrap body.
                with self.provider.reset_transaction():
                    # Persist a distinguishable post-reset wallet.
                    self.provider.bootstrap_players(_players(20))
        # Require exact pre-reset state rather than committed reset state.
        self.assertEqual(before, _data_snapshot(self.provider))
        # Require all recovery material removed after verified rollback.
        self.assertEqual([], list(self.provider._json_control_root().glob(f"{self.provider._reset_backup_prefix()}*")))
        # Construct one provider that tampers after rollback copy.
        tampering = _RestoreTamperProvider(self.root)
        # Force a body failure so rollback verification executes.
        with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
            # Enter the reset transaction.
            with tampering.reset_transaction():
                # Fail after destructive reset.
                raise RuntimeError("bootstrap failed")
        # Require the sole durable tar to remain for operator recovery.
        backups = list(tampering._json_control_root().glob(f"{tampering._reset_backup_prefix()}*.tar"))
        # Require exactly one recovery artifact.
        self.assertEqual(1, len(backups))
        # Capture partial state after the failed verification.
        partial = _data_snapshot(tampering)
        # Require every later affected read to fail before changing partial state.
        with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
            # Attempt an ordinary wallet read.
            tampering.load_players(_players)
        # Require exact partial bytes unchanged by the refused entry.
        self.assertEqual(partial, _data_snapshot(tampering))

    # Prove every restore verification failure retains the sole artifact and blocks visibility.
    def test_restore_inventory_content_archive_and_directory_durability_fail_closed(self):
        # Exercise every post-copy inventory and byte verification class.
        for mode in ("extra", "missing", "short", "content"):
            # Identify the exact hostile restore mode.
            with self.subTest(mode=mode):
                # Allocate one isolated provider root.
                with tempfile.TemporaryDirectory() as directory:
                    # Construct the selected hostile restore provider.
                    provider = _RestoreTamperProvider(Path(directory) / "data", mode)
                    # Seed complete pre-reset bytes.
                    _seed_provider(provider)
                    # Force rollback after destructive reset.
                    with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
                        # Enter the provider reset transaction.
                        with provider.reset_transaction():
                            # Trigger the caller-body rollback path.
                            raise RuntimeError("bootstrap failed")
                    # Require exactly one intact recovery artifact remains.
                    backups = list(provider._json_control_root().glob(f"{provider._reset_backup_prefix()}*.tar"))
                    # Require one operator-owned recovery snapshot.
                    self.assertEqual(1, len(backups))
                    # Capture the failed-restore partial state.
                    partial = _data_snapshot(provider)
                    # Require later visibility to fail before mutation.
                    with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
                        # Attempt one ordinary document read.
                        provider.read_document("settings/example", {})
                    # Require the failed state and archive remain unchanged.
                    self.assertEqual(partial, _data_snapshot(provider))
                    # Require the sole archive still exists.
                    self.assertTrue(backups[0].exists())
        # Allocate one isolated archive-corruption case.
        with tempfile.TemporaryDirectory() as directory:
            # Construct the ordinary provider.
            provider = JsonStorageProvider(Path(directory) / "data")
            # Seed complete pre-reset bytes.
            _seed_provider(provider)
            # Hold both gates while preparing an exact private backup.
            with provider.lock:
                # Enter the provider-wide process boundary.
                with provider._json_global_gate():
                    # Publish one valid durable snapshot.
                    backup = provider._create_reset_backup_locked()
                    # Clear provider state to require restoration.
                    provider._reset_locked()
                    # Corrupt the sole tar after durable publication.
                    backup.write_bytes(b"not-a-tar")
                    # Reject the malformed private archive.
                    with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
                        # Attempt restoration from hostile bytes.
                        provider._restore_reset_backup_locked(backup)
            # Require the corrupt recovery artifact remains.
            self.assertTrue(backup.exists())
            # Require every later affected operation to fail closed.
            with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
                # Attempt history visibility.
                provider.recent_history(10)
        # Allocate one restored-directory fsync failure case.
        with tempfile.TemporaryDirectory() as directory:
            # Construct the durability-failure provider.
            provider = _RestoreFsyncFailureProvider(Path(directory) / "data")
            # Seed complete pre-reset bytes.
            _seed_provider(provider)
            # Trigger rollback and its injected durability failure.
            with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
                # Enter one reset transaction.
                with provider.reset_transaction():
                    # Fail the caller body after clear.
                    raise RuntimeError("bootstrap failed")
            # Require the sole archive retained after unverifiable durability.
            self.assertEqual(1, len(list(provider._json_control_root().glob(f"{provider._reset_backup_prefix()}*.tar"))))

    # Prove same-thread nested aliases and mixed-version legacy locking cannot deadlock or race.
    def test_reentrant_alias_and_legacy_lock_bridge(self):
        # Seed the ordinary player wallet.
        self.provider.bootstrap_players(_players())
        # Construct one equivalent relative-spelling provider instance.
        alias = JsonStorageProvider(self.root.parent / "." / self.root.name)
        # Require one canonical process-gate identity.
        self.assertEqual(self.provider._json_root_key(), alias._json_root_key())
        # Require one stable external gate path.
        self.assertEqual(self.provider.json_gate_path(), alias.json_gate_path())
        # Capture nested-operation completion.
        result = []
        # Define one nested per-document read during update.
        def nested_document_update():
            # Update through the first provider while reading through its alias.
            updated = self.provider.update_document("settings/nested", lambda current: {"seen": alias.read_document("settings/nested", {}).get("value", 0) + 1}, {"value": 0})
            # Retain the completed result.
            result.append(updated)
        # Start the nested operation in a bounded thread.
        worker = threading.Thread(target=nested_document_update)
        # Launch the nested path.
        worker.start()
        # Join with a deadlock bound.
        worker.join(5)
        # Require nested same-root providers not to deadlock.
        self.assertFalse(worker.is_alive())
        # Require the exact persisted result.
        self.assertEqual([{"seen": 1}], result)
        # Use spawn for mixed-version lock proof.
        context = multiprocessing.get_context("spawn")
        # Signal when the legacy-only lock is held.
        ready = context.Event()
        # Release the legacy-only holder after the assertion.
        release = context.Event()
        # Collect the new-provider read result.
        output = context.Queue()
        # Build the historical lock holder.
        holder = context.Process(target=_process_hold_legacy_lock, args=(str(self.root), ready, release))
        # Start the historical holder.
        holder.start()
        # Require exact legacy lock acquisition.
        self.assertTrue(ready.wait(10))
        # Build the new provider reader.
        reader = context.Process(target=_process_read_wallet, args=(str(self.root), output))
        # Start the new provider reader.
        reader.start()
        # Allow an unbridged reader enough time to finish.
        time.sleep(0.25)
        # Require the new stable boundary to wait on the old ledger lock.
        self.assertTrue(reader.is_alive())
        # Release the historical lock.
        release.set()
        # Join both processes.
        holder.join(10)
        # Join the new reader.
        reader.join(10)
        # Require normal exits.
        self.assertEqual((0, 0), (holder.exitcode, reader.exitcode))
        # Require exact wallet visibility after serialization.
        self.assertEqual(10, output.get(timeout=2))

    # Prove stable control files remain private, reset-safe, packaged, and deployable.
    def test_stable_gate_and_reset_artifacts_use_the_writable_log_root(self):
        # Resolve the sole verified private control directory for this canonical data root.
        control_root = self.provider._json_control_root()
        # Require one bounded private namespace beneath canonical LOG_DIR.
        self.assertEqual(".casino-json", control_root.parent.name)
        # Require the canonical data-root digest to key the private directory identity.
        self.assertEqual(hashlib.sha256(self.provider._json_root_key().encode("utf-8")).hexdigest()[:16], control_root.name)
        # Require the stable gate to live inside the private per-data-root directory.
        self.assertEqual(control_root, self.provider.json_gate_path().parent)
        # Require collision-safe reset staging to use that same verified directory.
        self.assertEqual(control_root, self.provider._reset_backup_path().parent)
        # Require the configured local logs directory to be explicitly ignored.
        ignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
        # Require local control files to remain under the ignored log root.
        self.assertIn("logs/", ignore)
        # Read the tracked production service sandbox policy.
        service = (Path(__file__).resolve().parents[1] / "deploy" / "systemd" / "casino.service").read_text(encoding="utf-8")
        # Require the separately configured production log root to remain writable.
        self.assertIn("ReadWritePaths=/var/lib/casino /var/log/casino", service)
        # Require strict filesystem protection remains enabled.
        self.assertIn("ProtectSystem=strict", service)
        # Read the deterministic release packager source.
        packager = (Path(__file__).resolve().parents[1] / "scripts" / "package_app.py").read_text(encoding="utf-8")
        # Require all tracked casino source, including this provider boundary, in every package.
        self.assertIn('ALLOWED_PREFIXES = ("casino/",', packager)
        # Require allowlisted tracked prefixes to remain selected by the package builder.
        self.assertIn("return relative_path.startswith(ALLOWED_PREFIXES)", packager)
        # Resolve the exact production DATA_DIR literal without writing to it.
        production_data = posixpath.realpath("/var/lib/casino")
        # Resolve the exact production LOG_DIR literal without writing to it.
        production_log = posixpath.realpath("/var/log/casino")
        # Derive the exact production data-root digest with the provider algorithm.
        production_digest = hashlib.sha256(production_data.encode("utf-8")).hexdigest()[:16]
        # Derive the no-write private production control root.
        production_control = posixpath.realpath(posixpath.join(production_log, ".casino-json", production_digest))
        # Require the production control root beneath the configured writable log root.
        self.assertEqual(production_log, posixpath.commonpath((production_control, production_log)))
        # Require the production control root outside reset-owned application data.
        self.assertNotEqual(production_data, posixpath.commonpath((production_control, production_data)))
        # Read the environment-backed runtime path source.
        config_source = (Path(__file__).resolve().parents[1] / "casino" / "config.py").read_text(encoding="utf-8")
        # Require the exact two production directory selectors to remain supported.
        self.assertIn('DATA_DIR_ENV = "CASINO_DATA_DIR"', config_source)
        # Require the independent log-root selector to remain supported.
        self.assertIn('LOG_DIR_ENV = "CASINO_LOG_DIR"', config_source)
        # Construct the default local provider without invoking readiness.
        default_provider = JsonStorageProvider()
        # Reconstruct the exact retired root-level lock name for the default data identity.
        retired_name = f".casino-json-{hashlib.sha256(default_provider._json_root_key().encode('utf-8')).hexdigest()[:16]}.lock"
        # Require no leaked historical root-level lock remains in the checkout.
        self.assertFalse((Path(__file__).resolve().parents[1] / retired_name).exists())
        # Create the configured log root without entering provider readiness.
        self.provider.log_dir.mkdir(parents=True, exist_ok=True)
        # Place one old-location lookalike directly in LOG_DIR.
        unrelated = self.provider.log_dir / f"{self.provider._reset_backup_prefix()}outside-private-root.tar"
        # Persist distinguishable unrelated bytes.
        unrelated.write_bytes(b"unrelated")
        # Require the bounded private-root guard to ignore the direct LOG_DIR lookalike.
        self.provider.ensure_ready()
        # Require the unrelated direct LOG_DIR file remains untouched.
        self.assertEqual(b"unrelated", unrelated.read_bytes())

    # Prove environment-selected production topology initializes only the writable log analogue.
    def test_fresh_process_environment_roots_match_production_lock_topology(self):
        # Use spawn so config and storage read environment values in a new interpreter.
        context = multiprocessing.get_context("spawn")
        # Allocate one task-owned analogue of the production filesystem hierarchy.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve the analogue of /var/lib/casino.
            data_root = Path(directory) / "var" / "lib" / "casino"
            # Resolve the analogue of /var/log/casino.
            log_root = Path(directory) / "var" / "log" / "casino"
            # Create one child-safe result queue.
            output = context.Queue()
            # Install only the two production runtime directory variables before child import.
            with mock.patch.dict(os.environ, {"CASINO_DATA_DIR": os.fspath(data_root), "CASINO_LOG_DIR": os.fspath(log_root)}):
                # Build one fresh environment-selected process.
                worker = context.Process(target=_process_initialize_environment_provider, args=(output,))
                # Launch the fresh interpreter.
                worker.start()
                # Wait for bounded initialization completion.
                worker.join(10)
            # Require normal child exit.
            self.assertEqual(0, worker.exitcode)
            # Read the exact canonical topology.
            selected_data, selected_log, selected_control, gate_exists = output.get(timeout=2)
            # Require the child selected the environment data root.
            self.assertEqual(os.path.normcase(os.path.realpath(os.fspath(data_root))), selected_data)
            # Require the child selected the environment log root.
            self.assertEqual(os.path.normcase(os.path.realpath(os.fspath(log_root))), selected_log)
            # Require the private control root beneath only the writable log analogue.
            self.assertEqual(selected_log, os.path.commonpath((selected_control, selected_log)))
            # Require the private control root remains outside the reset-owned data analogue.
            self.assertNotEqual(selected_data, os.path.commonpath((selected_control, selected_data)))
            # Require stable gate initialization succeeded.
            self.assertTrue(gate_exists)
            # Require the exact task-owned retired root-level lock remains absent.
            self.assertFalse((Path(__file__).resolve().parents[1] / ".casino-json-4e2c2ceb000a0f46.lock").exists())

    # Prove distinct data roots sharing one log root receive collision-free private identities.
    def test_distinct_data_roots_share_log_without_control_or_residue_collision(self):
        # Allocate one shared configured log root.
        shared_log = self.root.parent / "shared-log"
        # Construct the first isolated data provider.
        first = JsonStorageProvider(self.root.parent / "first-data")
        # Bind the first provider to the shared log root.
        first.log_dir = shared_log
        # Construct the second isolated data provider.
        second = JsonStorageProvider(self.root.parent / "second-data")
        # Bind the second provider to the same shared log root.
        second.log_dir = shared_log
        # Require distinct canonical data identities.
        self.assertNotEqual(first._json_root_key(), second._json_root_key())
        # Require distinct digest-keyed private control roots.
        self.assertNotEqual(first._json_control_root(), second._json_control_root())
        # Require distinct stable gate targets.
        self.assertNotEqual(first.json_gate_path(), second.json_gate_path())
        # Initialize both independent gates and provider roots.
        first.ensure_ready()
        # Initialize the second provider independently.
        second.ensure_ready()
        # Require both stable gate files exist simultaneously.
        self.assertTrue(first.json_gate_path().is_file())
        # Require the second stable gate also exists.
        self.assertTrue(second.json_gate_path().is_file())
        # Signal after the first provider owns its independent global gate.
        first_entered = threading.Event()
        # Hold the first provider gate during the second provider operation.
        first_release = threading.Event()
        # Signal when the second provider finishes while the first remains held.
        second_finished = threading.Event()
        # Hold only the first canonical provider boundary.
        def hold_first():
            # Acquire the first provider's stable and compatibility locks.
            with first._json_global_gate():
                # Signal exact first-root ownership.
                first_entered.set()
                # Retain ownership for the bounded concurrency assertion.
                first_release.wait(5)
        # Mutate only the second canonical provider root.
        def write_second():
            # Persist one wallet through the second independent gate.
            second.bootstrap_players(_players())
            # Signal completion without releasing the first holder.
            second_finished.set()
        # Start the first independent gate holder.
        first_thread = threading.Thread(target=hold_first)
        # Launch the first holder.
        first_thread.start()
        # Require exact first-root gate acquisition.
        self.assertTrue(first_entered.wait(5))
        # Start the second-root operation concurrently.
        second_thread = threading.Thread(target=write_second)
        # Launch the second operation.
        second_thread.start()
        # Require the second root not to collide with the held first-root gate.
        self.assertTrue(second_finished.wait(2))
        # Release the first independent boundary.
        first_release.set()
        # Join the first thread within the deadlock bound.
        first_thread.join(5)
        # Join the second thread within the same bound.
        second_thread.join(5)
        # Require both independent operations to finish.
        self.assertFalse(first_thread.is_alive() or second_thread.is_alive())
        # Create one exact retained artifact for only the first data identity.
        first_residue = first._json_control_root() / f"{first._reset_backup_prefix()}isolated.tar"
        # Persist distinguishable retained recovery bytes.
        first_residue.write_bytes(b"first-only")
        # Require the first provider to fail closed on its own residue.
        with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
            # Attempt first-provider visibility.
            first.load_players(_players)
        # Require the second provider to remain independently usable.
        second.bootstrap_players(_players())
        # Require the second provider persisted its independent wallet.
        self.assertEqual(10, second.load_players(_players)["players"][0]["balance"])

    # Prove canonical overlap and escaping indirection fail before any artifact creation.
    def test_control_root_rejects_unsafe_overlap_before_filesystem_mutation(self):
        # Exercise equal, child, and dot-aliased child log roots.
        for label, log_root in (
            # Reject an exact shared reset and control root.
            ("equal", self.root),
            # Reject a lexical child of reset-owned data.
            ("child", self.root / "logs"),
            # Reject a dot-dot spelling that canonically enters reset-owned data.
            ("dot-dot", self.root.parent / "outside" / ".." / "data" / "logs"),
        ):
            # Identify the exact unsafe shape.
            with self.subTest(label=label):
                # Construct one non-mutating provider.
                provider = JsonStorageProvider(self.root)
                # Install only the hostile configured log spelling.
                provider.log_dir = log_root
                # Capture the exact absent reset-owned inventory.
                before = _data_snapshot(provider)
                # Reject the configuration before lock-parent creation.
                with self.assertRaisesRegex(ConflictError, "JSON storage control path is invalid"):
                    # Attempt the first ordinary gated operation.
                    provider.ensure_ready()
                # Require no data or lock artifact was created.
                self.assertEqual(before, _data_snapshot(provider))
        # Allocate a sibling path that can act as an escaping link target.
        external = self.root.parent / "external-control"
        # Allocate one configured log root without creating it through provider code.
        configured = self.root.parent / "configured-log"
        try:
            # Create the configured log root for the real indirection proof.
            configured.mkdir(parents=True)
            # Create the private namespace as a link that escapes canonical LOG_DIR.
            os.symlink(external, configured / ".casino-json", target_is_directory=True)
        # Skip only when the host disallows real symlink creation.
        except OSError:
            # Preserve deterministic containment coverage through the direct canonical cases.
            pass
        else:
            # Construct one provider with the escaping configured log root.
            provider = JsonStorageProvider(self.root)
            # Select the hostile indirection.
            provider.log_dir = configured
            # Capture exact pre-entry reset-owned bytes.
            before = _data_snapshot(provider)
            # Reject escaping indirection before following it for creation.
            with self.assertRaisesRegex(ConflictError, "JSON storage control path is invalid"):
                # Attempt one gated read.
                provider.load_players(_players)
            # Require no reset-owned mutation.
            self.assertEqual(before, _data_snapshot(provider))
            # Require no external target was created by the refused entry.
            self.assertFalse(external.exists())

    # Prove first-use control binding cannot drift to later mutable configuration.
    def test_control_root_binding_reuses_original_identity_after_configuration_drift(self):
        # Construct one fresh provider without creating its roots.
        provider = JsonStorageProvider(self.root.parent / "bound-data")
        # Select one safe configured log root before first use.
        provider.log_dir = self.root.parent / "bound-log"
        # Bind the verified canonical control identity without filesystem mutation.
        bound_control = provider._json_control_root()
        # Capture the exact stable gate path bound to that identity.
        bound_gate = provider.json_gate_path()
        # Capture one recovery path beneath the same bound identity.
        bound_backup = provider._reset_backup_path()
        # Change the mutable field after the control identity is bound.
        alternate_log = self.root.parent / "alternate-log"
        # Install a different safe-looking configured log root.
        provider.log_dir = alternate_log
        # Require later stable-gate lookup to remain on the original verified root.
        self.assertEqual(bound_gate, provider.json_gate_path())
        # Require later recovery lookup to remain under the original verified root.
        self.assertEqual(bound_control, provider._reset_backup_path().parent)
        # Require the earlier recovery path was also bound under the same root.
        self.assertEqual(bound_control, bound_backup.parent)
        # Require no alternate log or control artifact was created.
        self.assertFalse(alternate_log.exists())
        # Select a different data field after binding as a hostile state-root mutation.
        alternate_data = self.root.parent / "alternate-data"
        # Install the unsafe alternate state target.
        provider.data_dir = alternate_data
        # Reject data-root drift before any operation can use the old gate for new state.
        with self.assertRaisesRegex(ConflictError, "JSON storage control path is invalid"):
            # Attempt later stable-gate lookup.
            provider.json_gate_path()
        # Require no alternate data or lock artifact was created.
        self.assertFalse(alternate_data.exists())
        # Construct one provider for post-binding private-directory indirection.
        redirected = JsonStorageProvider(self.root.parent / "redirect-data")
        # Select an existing configured log root.
        redirected.log_dir = self.root.parent / "redirect-log"
        # Create only the configured log root.
        redirected.log_dir.mkdir(parents=True)
        # Bind the canonical private path before any private namespace exists.
        redirected_control = redirected._json_control_root()
        # Allocate one external indirection target.
        redirected_target = self.root.parent / "redirect-target"
        # Create the external target before linking.
        redirected_target.mkdir()
        try:
            # Replace the not-yet-created private namespace with escaping indirection.
            os.symlink(redirected_target, redirected.log_dir / ".casino-json", target_is_directory=True)
        # Preserve field-drift proof when host policy denies real symlinks.
        except OSError:
            # Continue because link creation is platform-dependent.
            pass
        else:
            # Refuse the changed filesystem identity before lock or backup creation.
            with self.assertRaisesRegex(ConflictError, "JSON storage control path is invalid"):
                # Reuse the already-bound control root through the gate accessor.
                redirected.json_gate_path()
            # Require no gate or snapshot file appeared in the alternate target.
            self.assertEqual([], list(redirected_target.iterdir()))
            # Require the originally verified identity was not replaced in memory.
            self.assertEqual(redirected_control, redirected._json_control_root_cache)

    # Prove canonical aliases share one stable inode and reset never replaces it.
    def test_control_root_alias_identity_order_and_stable_inode(self):
        # Construct an equivalent DATA_DIR spelling.
        alias = JsonStorageProvider(self.root.parent / "safe-alias-parent" / ".." / self.root.name)
        # Construct an equivalent dot-dot LOG_DIR spelling.
        alias.log_dir = self.provider.log_dir.parent / "safe-alias-parent" / ".." / self.provider.log_dir.name
        # Require exact canonical control-root identity.
        self.assertEqual(self.provider._json_control_root(), alias._json_control_root())
        # Require exact canonical stable lock identity.
        self.assertEqual(self.provider.json_gate_path(), alias.json_gate_path())
        # Record whether full readiness runs only after the legacy lock exists.
        readiness_observations = []
        # Preserve the real readiness implementation.
        real_readiness = self.provider._ensure_ready_direct
        # Observe lock ordering without weakening filesystem behavior.
        def observe_readiness():
            # Record the exact minimal root inventory before content readiness.
            readiness_observations.append(tuple(sorted(entry.name for entry in self.provider.data_dir.iterdir())))
            # Delegate to the real directory setup.
            return real_readiness()
        # Instrument only the remaining-readiness boundary.
        with mock.patch.object(self.provider, "_ensure_ready_direct", side_effect=observe_readiness):
            # Enter one ordinary provider operation.
            self.provider.ensure_ready()
        # Require full content readiness only after stable then legacy lock acquisition.
        self.assertEqual([(".ledger.lock",)], readiness_observations)
        # Capture stable and compatibility lock identities before reset.
        stable_before = self.provider.json_gate_path().stat()
        # Capture the legacy lock inode before reset.
        legacy_before = self.provider.ledger_lock_path().stat()
        # Perform one successful complete reset under both locks.
        with self.provider.reset_transaction():
            # Publish one post-reset wallet while both lock files remain open.
            self.provider.bootstrap_players(_players())
        # Require the stable lock object was never replaced.
        stable_after = self.provider.json_gate_path().stat()
        # Require exact platform file identity across reset.
        self.assertEqual((stable_before.st_dev, stable_before.st_ino), (stable_after.st_dev, stable_after.st_ino))
        # Require the legacy rollout lock object was never replaced.
        legacy_after = self.provider.ledger_lock_path().stat()
        # Require exact legacy file identity across reset.
        self.assertEqual((legacy_before.st_dev, legacy_before.st_ino), (legacy_after.st_dev, legacy_after.st_ino))
        # Allocate a genuine filesystem alias for platforms that permit test-owned links.
        data_alias_path = self.root.parent / "linked-data-alias"
        try:
            # Point the alias at the already initialized canonical data root.
            os.symlink(self.root, data_alias_path, target_is_directory=True)
        # Preserve the canonical dot-dot proof when host policy denies symlink creation.
        except OSError:
            # Continue because real indirection is explicitly platform-dependent.
            pass
        else:
            # Construct one provider through the genuine filesystem alias.
            linked_alias = JsonStorageProvider(data_alias_path)
            # Reuse the same canonical configured log root.
            linked_alias.log_dir = self.provider.log_dir
            # Require filesystem indirection to converge on the canonical data identity.
            self.assertEqual(self.provider._json_root_key(), linked_alias._json_root_key())
            # Require the indirection to converge on the exact same private control root.
            self.assertEqual(self.provider._json_control_root(), linked_alias._json_control_root())
            # Require the indirection to converge on the exact same stable gate file.
            self.assertEqual(self.provider.json_gate_path(), linked_alias.json_gate_path())

    # Prove retained final/temp residue blocks every affected public surface without DATA mutation.
    def test_retained_reset_artifacts_block_all_affected_entries_before_readiness(self):
        # Exercise both final and unpublished provider-owned residue names.
        for suffix in ("1.tar", "1.tar.tmp-dead"):
            # Identify the exact residue kind.
            with self.subTest(suffix=suffix):
                # Allocate a fresh isolated root for each residue kind.
                with tempfile.TemporaryDirectory() as directory:
                    # Construct one provider whose DATA_DIR is initially absent.
                    provider = JsonStorageProvider(Path(directory) / "data")
                    # Create only the separately writable external lock/recovery root.
                    provider._json_control_root().mkdir(parents=True, exist_ok=True)
                    # Create the exact owned sibling residue without creating DATA_DIR.
                    residue = provider._json_control_root() / f"{provider._reset_backup_prefix()}{suffix}"
                    # Persist arbitrary retained recovery bytes.
                    residue.write_bytes(b"retained")
                    # Capture exact absent data-root inventory.
                    before = _data_snapshot(provider)
                    # Build one valid action request for the refused action path.
                    resources = _resources()
                    # Bind the valid durable identity.
                    identity = _identity(resources=resources)
                    # Enumerate every affected entry point.
                    operations = (
                        # Refuse public directory readiness.
                        provider.ensure_ready,
                        # Refuse wallet visibility.
                        lambda: provider.load_players(_players),
                        # Refuse wallet mutation.
                        lambda: provider.bootstrap_players(_players()),
                        # Refuse ordinary ledger mutation.
                        lambda: provider.transact_ledger("human", -1, "TEST"),
                        # Refuse named-document visibility.
                        lambda: provider.read_document("settings/example", {}),
                        # Refuse named-document mutation.
                        lambda: provider.write_document("settings/example", {}),
                        # Refuse history visibility.
                        lambda: provider.recent_history(10),
                        # Refuse history mutation.
                        lambda: provider.append_history(_history_event()),
                        # Refuse action execution before snapshot or planner.
                        lambda: provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan),
                        # Refuse another reset before operator recovery.
                        provider.reset,
                    )
                    # Exercise each operation independently.
                    for index, operation in enumerate(operations):
                        # Identify only the operation index.
                        with self.subTest(operation=index):
                            # Require the same fixed retained-recovery error.
                            with self.assertRaisesRegex(ConflictError, "JSON reset requires operator recovery"):
                                # Attempt the affected operation.
                                operation()
                            # Require no DATA_DIR recreation or byte mutation.
                            self.assertEqual(before, _data_snapshot(provider))
                    # Require an unrelated sibling not to broaden owned matching.
                    unrelated = provider._json_control_root() / f"{provider._reset_backup_prefix()}unrelated.txt"
                    # Persist one non-owned sibling name.
                    unrelated.write_bytes(b"unrelated")
                    # Remove only the exact owned residue.
                    residue.unlink()
                    # Allow provider readiness despite the unrelated sibling.
                    provider.ensure_ready()

    # Prove fresh-process bootstrap cannot mutate absent or partial data under retained residue.
    def test_fresh_process_bootstrap_refuses_final_and_temp_residue_without_defaults(self):
        # Use spawn so provider construction and bootstrap begin in a fresh interpreter.
        context = multiprocessing.get_context("spawn")
        # Exercise final and staging residue against absent and partial data roots.
        for suffix in ("1.tar", "1.tar.tmp-dead"):
            # Exercise both exact pre-entry data-root states.
            for partial in (False, True):
                # Identify the exact hostile combination.
                with self.subTest(suffix=suffix, partial=partial):
                    # Allocate an isolated parent for this fresh-process case.
                    with tempfile.TemporaryDirectory() as directory:
                        # Construct a path-only provider in the parent without readiness mutation.
                        provider = JsonStorageProvider(Path(directory) / "data")
                        # Create only the separately writable external lock/recovery root.
                        provider._json_control_root().mkdir(parents=True, exist_ok=True)
                        # Create one distinguishable partial data tree when selected.
                        if partial:
                            # Create only the root without ordinary readiness directories.
                            provider.data_dir.mkdir()
                            # Persist one exact partial byte payload.
                            (provider.data_dir / "partial.json").write_bytes(b"partial")
                        # Create the exact retained final or staging artifact outside DATA_DIR.
                        residue = provider._json_control_root() / f"{provider._reset_backup_prefix()}{suffix}"
                        # Persist arbitrary retained recovery bytes.
                        residue.write_bytes(b"retained")
                        # Capture the parent-observed exact inventory before the fresh process.
                        before = _data_snapshot(provider)
                        # Create one process-safe output queue.
                        output = context.Queue()
                        # Build one fresh bootstrap process.
                        worker = context.Process(target=_process_bootstrap_with_residue, args=(str(provider.data_dir), output))
                        # Launch the fresh interpreter.
                        worker.start()
                        # Join with a bounded deadlock timeout.
                        worker.join(10)
                        # Require normal handled exit.
                        self.assertEqual(0, worker.exitcode)
                        # Read the sanitized refusal proof.
                        message, default_calls, unchanged = output.get(timeout=2)
                        # Require the exact fixed recovery boundary.
                        self.assertEqual("JSON reset requires operator recovery", message)
                        # Require the caller default factory never to run.
                        self.assertEqual(0, default_calls)
                        # Require exact child-observed no-change.
                        self.assertTrue(unchanged)
                        # Require exact parent-observed no-change.
                        self.assertEqual(before, _data_snapshot(provider))

    # Prove generic providers retain the shipped local cleanup and response behavior.
    def test_non_json_reset_preserves_provider_and_local_cleanup_semantics(self):
        # Construct one MySQL-like provider without database behavior.
        provider = _NonJsonResetProvider()
        # Inject the non-JSON provider for the listener-free route.
        set_provider_for_tests(provider)
        # Build the current router.
        router = app.build_router()
        # Resolve the exact shipped reset route.
        reset_route = next(route for route in router.routes if route.method == "POST" and route.regex.pattern == "^/api/v1/casino/reset$")
        # Allocate one isolated legacy local data root.
        local_data = Path(self.temporary.name) / "legacy-local-data"
        # Create one stale local game-state tree.
        (local_data / "games").mkdir(parents=True)
        # Persist one stale game-state file that old reset behavior removed.
        (local_data / "games" / "stale.json").write_text("{}", encoding="utf-8")
        # Track Admin authorization without changing its semantics.
        require_admin = mock.Mock()
        # Recreate the local root exactly where the old route called ensure_dirs.
        recreate = mock.Mock(side_effect=lambda: local_data.mkdir(parents=True, exist_ok=True))
        # Track default-player bootstrap without requiring fake provider player methods.
        bootstrap_players = mock.Mock()
        # Track Admin bootstrap.
        bootstrap_admin = mock.Mock()
        # Build the unchanged response projections.
        games = [{"game": "slots"}]
        # Build the unchanged player response.
        visible_players = _players()["players"]
        # Patch only the generic local cleanup root and route collaborators.
        with mock.patch.object(storage_module, "DATA_DIR", local_data), mock.patch.object(app.auth, "require_admin", require_admin), mock.patch.object(app, "ensure_dirs", recreate), mock.patch.object(provider, "bootstrap_players", bootstrap_players), mock.patch.object(app.auth, "bootstrap_admin_from_env", bootstrap_admin), mock.patch.object(app, "list_games", return_value=games), mock.patch.object(app.players, "list_players", return_value=visible_players):
            # Invoke the existing listener-free route.
            result = reset_route.handler({}, {}, context={"user": {"roles": ["admin"]}})
        # Require exact unchanged response fields.
        self.assertEqual({"games": games, "players": visible_players}, result)
        # Require authorization remains first and present.
        require_admin.assert_called_once()
        # Require the provider reset executes exactly once.
        self.assertEqual(1, provider.reset_calls)
        # Require stale local game-state bytes are removed.
        self.assertFalse((local_data / "games" / "stale.json").exists())
        # Require caller recreation still executes exactly once.
        recreate.assert_called_once_with()
        # Require both bootstrap operations remain present.
        bootstrap_players.assert_called_once()
        # Require Admin bootstrap remains present.
        bootstrap_admin.assert_called_once_with()

    # Prove history and Admin direct state reads wait for complete reset visibility.
    def test_cross_process_reset_blocks_history_and_admin_state_until_complete(self):
        # Seed complete pre-reset state.
        _seed_provider(self.provider)
        # Use spawn for independent process and lock state.
        context = multiprocessing.get_context("spawn")
        # Signal when complete post-reset state exists under the held gate.
        ready = context.Event()
        # Control final reset visibility.
        release = context.Event()
        # Collect the independent reader result.
        output = context.Queue()
        # Start one reset worker that holds visibility after bootstrap.
        reset_worker = context.Process(target=_process_hold_reset, args=(str(self.root), ready, release))
        # Launch the reset worker.
        reset_worker.start()
        # Require the reset body to reach complete post-bootstrap state.
        self.assertTrue(ready.wait(10))
        # Start one independent Admin/history reader while reset still owns the gate.
        reader = context.Process(target=_process_read_visibility, args=(str(self.root), output))
        # Launch the reader.
        reader.start()
        # Start one independent history append while reset still owns the gate.
        writer = context.Process(target=_process_append_history, args=(str(self.root), output))
        # Launch the writer.
        writer.start()
        # Allow a bounded interval in which an ungated reader would finish.
        time.sleep(0.25)
        # Require the reader to remain blocked until final visibility.
        self.assertTrue(reader.is_alive())
        # Require the writer to remain blocked until final visibility.
        self.assertTrue(writer.is_alive())
        # Release the exact reset transaction.
        release.set()
        # Join the reset worker.
        reset_worker.join(10)
        # Join the reader worker.
        reader.join(10)
        # Join the writer worker.
        writer.join(10)
        # Require all independent processes to exit normally.
        self.assertEqual((0, 0, 0), (reset_worker.exitcode, reader.exitcode, writer.exitcode))
        # Read both process results without assuming post-release ordering.
        results = [output.get(timeout=2), output.get(timeout=2)]
        # Select the Admin/history tuple from the writer marker.
        states, rows = next(result for result in results if result != "appended")
        # Require exactly the complete post-reset game state.
        self.assertEqual({"round": "after"}, states["slots"]["state"])
        # Require exactly the post-reset history row.
        self.assertIn([row["round_id"] for row in rows], (["round-after"], ["round-after", "round-contender"]))
        # Require the contender append to survive in final provider history.
        self.assertEqual(["round-after", "round-contender"], [row["round_id"] for row in self.provider.recent_history(10)])

    # Prove the reset route holds the gate through final response materialization.
    def test_reset_route_blocks_contender_until_response_snapshot_is_materialized(self):
        # Seed complete pre-reset state.
        _seed_provider(self.provider)
        # Build the current router.
        router = app.build_router()
        # Resolve the exact reset handler.
        reset_route = next(route for route in router.routes if route.method == "POST" and route.regex.pattern == "^/api/v1/casino/reset$")
        # Signal when final response projection begins under the context.
        projection_started = threading.Event()
        # Hold response projection for a bounded assertion window.
        projection_release = threading.Event()
        # Signal when the contender obtains provider visibility.
        contender_finished = threading.Event()
        # Capture route-thread failures.
        route_errors = []
        # Define final player projection that holds the reset context.
        def visible_players():
            # Signal that successful bootstrap has reached final response projection.
            projection_started.set()
            # Hold the projection while a contender attempts entry.
            projection_release.wait(5)
            # Return the unchanged response shape.
            return _players()["players"]
        # Define the listener-free reset invocation.
        def invoke_reset():
            try:
                # Patch only external bootstrap collaborators.
                with mock.patch.object(app.auth, "require_admin"), mock.patch.object(app, "ensure_dirs"), mock.patch.object(app.auth, "bootstrap_admin_from_env"), mock.patch.object(app, "list_games", return_value=[{"game": "slots"}]), mock.patch.object(app.players, "list_players", side_effect=visible_players):
                    # Invoke the existing route.
                    reset_route.handler({}, {}, context={"user": {"roles": ["admin"]}})
            # Record unexpected route failures for the parent assertion.
            except BaseException as error:
                # Preserve only the exception object in test memory.
                route_errors.append(error)
        # Define one competing provider read.
        def contend():
            # Attempt wallet visibility through a second provider instance.
            JsonStorageProvider(self.root).load_players(_players)
            # Signal only after the shared gate is acquired and released.
            contender_finished.set()
        # Start the reset route in one thread.
        route_thread = threading.Thread(target=invoke_reset)
        # Launch reset execution.
        route_thread.start()
        # Require final projection to begin under the held boundary.
        self.assertTrue(projection_started.wait(5))
        # Start the contender during response materialization.
        contender_thread = threading.Thread(target=contend)
        # Launch the competing read.
        contender_thread.start()
        # Allow an ungated contender enough time to finish.
        time.sleep(0.2)
        # Require the contender to remain blocked.
        self.assertFalse(contender_finished.is_set())
        # Release final response projection.
        projection_release.set()
        # Join both bounded threads.
        route_thread.join(5)
        # Join the contender after reset visibility commits.
        contender_thread.join(5)
        # Require the route to finish without hidden failures.
        self.assertEqual([], route_errors)
        # Require the contender to finish only after response materialization.
        self.assertTrue(contender_finished.is_set())


# Run this focused module directly without registering a new shared runner case.
if __name__ == "__main__":
    # Execute unittest's standard listener-free runner.
    unittest.main()
