# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic transaction-model tests for the schema-four MySQL action bridge."""

# Import deep copies so rollback never leaks transaction-local mutations.
from copy import deepcopy
# Import exact decimal balances used by the production provider.
from decimal import Decimal
# Import stable SHA-256 proof for immutable receipt bytes.
import hashlib
# Import source inspection for append-only SQL assertions.
import inspect
# Import thread-local reset ownership used by the production provider seam.
import threading
# Import a plain migration-state object for the fake schema seam.
from types import SimpleNamespace
# Import unittest for the standalone focused suite.
import unittest

# Import immutable provider-neutral action values.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionResolution, GameActionResources
# Import the production MySQL provider and secret-safe target descriptor without opening a connector.
from casino.core.storage import MySQLConfig, MySQLStorageProvider, _BorrowedMySQLConnection
# Import stable public conflict and validation behavior.
from casino.errors import ConflictError, ValidationError


# Model a connector lock-wait exception without importing mysql.connector.
class _LockWaitError(RuntimeError):
    # Preserve the exact server error number consumed by the resolver.
    errno = 1205


# Store one shared committed relational image across connection leases.
class _Database:
    # Initialize the minimum schema-four application rows.
    def __init__(self) -> None:
        # Seed one exact player wallet.
        self.players = {"human": {"player_id": "human", "balance": Decimal("10.00")}}
        # Store route-free JSON documents by exact resource key.
        self.documents = {}
        # Store immutable lifecycle claims by their three-part scope.
        self.claims = {}
        # Store immutable receipts by their three-part scope.
        self.receipts = {}
        # Store append-only ledger rows by exact ledger identity.
        self.ledger = {}
        # Store the schema-four singleton reset namespace and phase.
        self.epoch = {"state_id": 1, "current_epoch": 1, "phase": "ready"}
        # Model one server-scoped named-lock owner.
        self.named_lock = None
        # Allow one test to inject a bounded resolver lock wait.
        self.lock_wait_once = False
        # Allow one test to inject pooled-session restoration failure.
        self.restore_failure_once = False
        # Allow one test to interrupt exact reset phase-two finalization.
        self.finalize_failure_once = False

    # Return a detached transaction image.
    def snapshot(self) -> dict:
        # Copy every mutable relation so rollback is exact.
        return deepcopy({"players": self.players, "documents": self.documents, "claims": self.claims, "receipts": self.receipts, "ledger": self.ledger, "epoch": self.epoch})

    # Replace committed relations from one successful transaction.
    def commit(self, state: dict) -> None:
        # Publish each complete relation atomically in this deterministic fake.
        self.players, self.documents, self.claims, self.receipts, self.ledger, self.epoch = (state[name] for name in ("players", "documents", "claims", "receipts", "ledger", "epoch"))


# Model only the DB-API transaction methods used by the production bridge.
class _Connection:
    # Bind one lease to the shared committed database.
    def __init__(self, database: _Database) -> None:
        # Retain the shared committed store.
        self.database = database
        # Start outside a transaction.
        self.state = None
        # Count exact commit and rollback outcomes.
        self.commits = 0
        # Count rollback calls for failed lifecycle proof.
        self.rollbacks = 0
        # Track close without changing committed state.
        self.closed = False
        # Preserve the pooled-session lock wait setting.
        self.lock_wait = 50
        # Model connector autocommit-false SELECT preflight transaction state.
        self.implicit_transaction = False

    # Start one isolated transaction image.
    def start_transaction(self) -> None:
        # Reject the connector's nested-start failure when preflight was not cleared.
        if self.implicit_transaction:
            # Surface the production ordering defect deterministically.
            raise AssertionError("transaction already in progress")
        # Refuse nested transactions in the focused fake.
        if self.state is not None:
            # Surface a fixture defect.
            raise AssertionError("nested transaction")
        # Snapshot all relations together.
        self.state = self.database.snapshot()

    # Return one SQL cursor bound to this lease.
    def cursor(self, dictionary=False):
        # Preserve dictionary-row behavior requested by production.
        return _Cursor(self, dictionary=dictionary)

    # Publish the complete transaction image.
    def commit(self) -> None:
        # Commit only when a transaction is active.
        if self.state is not None:
            # Publish all relational changes atomically.
            self.database.commit(self.state)
            # End the transaction after publication.
            self.state = None
        # End any connector-owned implicit transaction as well.
        self.implicit_transaction = False
        # Count read-only and write commits alike.
        self.commits += 1

    # Discard the complete transaction image.
    def rollback(self) -> None:
        # Forget every transaction-local relation change.
        self.state = None
        # End a session-preflight implicit transaction before explicit start.
        self.implicit_transaction = False
        # Count the bounded rollback.
        self.rollbacks += 1

    # Close this lease without hidden commit behavior.
    def close(self) -> None:
        # Mark the exact lease closed.
        self.closed = True


# Interpret the bounded SQL emitted by MySQLStorageProvider lifecycle methods.
class _Cursor:
    # Bind one cursor to a connection and row projection mode.
    def __init__(self, connection: _Connection, *, dictionary: bool) -> None:
        # Retain the active connection.
        self.connection = connection
        # Retain whether rows must be dictionaries.
        self.dictionary = dictionary
        # Initialize no pending result row.
        self.result = None
        # Initialize affected-row count.
        self.rowcount = 0

    # Return the transaction image or committed image for session-only statements.
    def _state(self) -> dict:
        # Require an active lifecycle transaction for application DML.
        if self.connection.state is None:
            # Surface a fixture/production ordering defect.
            raise AssertionError("application SQL outside transaction")
        # Return the isolated transaction state.
        return self.connection.state

    # Execute one reviewed production SQL statement.
    def execute(self, statement: str, params=()) -> None:
        # Normalize whitespace only for deterministic dispatch.
        sql = " ".join(statement.split())
        # Reset result and row count for this statement.
        self.result, self.rowcount = None, 0
        # Acquire the one server-scoped reset lock without waiting.
        if sql.startswith("SELECT GET_LOCK"):
            # Grant ownership only when absent or already held by this session.
            acquired = self.connection.database.named_lock in {None, self.connection}
            # Retain exact session ownership on success.
            if acquired:
                # Model MySQL's session-owned user lock.
                self.connection.database.named_lock = self.connection
            # Return the exact integer acquisition result.
            self.result = {"acquired": 1 if acquired else 0}
            # Stop after the session-level lock operation.
            return
        # Release only a named lock held by this same fake session.
        if sql.startswith("SELECT RELEASE_LOCK"):
            # Determine exact session ownership without changing foreign locks.
            released = self.connection.database.named_lock is self.connection
            # Clear the server-scoped owner only on exact release.
            if released:
                # Make the lock available to a later explicit reset.
                self.connection.database.named_lock = None
            # Return the reviewed one-or-zero result.
            self.result = {"released": 1 if released else 0}
            # Stop after release.
            return
        # Return the current pooled-session lock policy.
        if sql.startswith("SELECT @@SESSION.innodb_lock_wait_timeout"):
            # Model connector autocommit-false SELECT opening an implicit transaction.
            if self.connection.state is None:
                # Require production to clear this before explicit transaction start.
                self.connection.implicit_transaction = True
            # Return one dictionary row exactly like mysql.connector.
            self.result = {"lock_wait": self.connection.lock_wait}
            # Stop after the session read.
            return
        # Apply the bounded resolver session timeout.
        if sql.startswith("SET SESSION innodb_lock_wait_timeout"):
            # Read the parameterized restore or exact production one-second bound.
            value = params[0] if params else sql.rsplit(" ", 1)[-1]
            # Inject one restore-only failure after the resolver transaction ends.
            if params and self.connection.database.restore_failure_once:
                # Consume the one-shot restoration failure.
                self.connection.database.restore_failure_once = False
                # Surface a connector-like session reset error.
                raise RuntimeError("session restore failed")
            # Store the trusted integer selected by production.
            self.connection.lock_wait = int(value)
            # Stop after session policy mutation.
            return
        # Lock the singleton reset epoch for shared action or exclusive reset ownership.
        if sql.startswith("SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state"):
            # Return the transaction-local row when a transaction owns it.
            self.result = deepcopy(self._state()["epoch"])
            # Stop after exact singleton selection.
            return
        # Advance the singleton epoch and enter resetting through exact compare-and-set.
        if sql.startswith("UPDATE casino_game_action_epoch_state SET current_epoch"):
            # Split the expected replacement and exact prior state.
            next_epoch, prior_epoch, prior_phase = params
            # Match only the current transaction row.
            if self._state()["epoch"] == {"state_id": 1, "current_epoch": prior_epoch, "phase": prior_phase}:
                # Publish the new unavailable namespace transaction-locally.
                self._state()["epoch"] = {"state_id": 1, "current_epoch": next_epoch, "phase": "resetting"}
                # Report one exact singleton update.
                self.rowcount = 1
            # Stop after compare-and-set.
            return
        # Finalize one exact resetting namespace as ready.
        if sql.startswith("UPDATE casino_game_action_epoch_state SET phase = 'ready'"):
            # Read the bound expected epoch.
            expected_epoch = params[0]
            # Require exact resetting ownership.
            if self.connection.database.finalize_failure_once:
                # Consume the one-shot compare-and-set failure without changing phase.
                self.connection.database.finalize_failure_once = False
                # Stop with rowcount zero so production fails closed.
                return
            # Match only the exact bound resetting namespace.
            if self._state()["epoch"] == {"state_id": 1, "current_epoch": expected_epoch, "phase": "resetting"}:
                # Publish the ready phase without changing the epoch.
                self._state()["epoch"]["phase"] = "ready"
                # Report one exact singleton update.
                self.rowcount = 1
            # Stop after finalization.
            return
        # Delete mutable ledger rows during reset phase one.
        if sql == "DELETE FROM casino_ledger":
            # Clear only the transaction-local mutable ledger relation.
            self._state()["ledger"] = {}
            # Stop after reset deletion.
            return
        # Delete mutable history rows not otherwise modeled by this focused fake.
        if sql == "DELETE FROM casino_history":
            # Preserve a no-op because history is outside this focused model.
            return
        # Delete mutable state documents during reset phase one.
        if sql == "DELETE FROM casino_documents":
            # Clear only transaction-local documents.
            self._state()["documents"] = {}
            # Stop after reset deletion.
            return
        # Delete mutable players after their dependent ledger rows.
        if sql == "DELETE FROM casino_players":
            # Clear only transaction-local wallets.
            self._state()["players"] = {}
            # Stop after reset deletion.
            return
        # Bootstrap one missing player through the reset-borrowed connection.
        if sql.startswith("INSERT IGNORE INTO casino_players"):
            # Split the exact compatible player fields.
            player_id, display_name, player_type, balance, created_at, updated_at, status = params
            # Insert only when the current reset epoch has no row with this identity.
            if player_id not in self._state()["players"]:
                # Preserve the bounded row needed by later action snapshots.
                self._state()["players"][player_id] = {"player_id": player_id, "display_name": display_name, "player_type": player_type, "balance": Decimal(str(balance)), "created_at": created_at, "updated_at": updated_at, "status": status}
                # Report one new bootstrap row.
                self.rowcount = 1
            # Stop after idempotent bootstrap.
            return
        # Insert one immutable lifecycle claim without update semantics.
        if sql.startswith("INSERT IGNORE INTO casino_game_action_claims"):
            # Surface one injected lock wait before touching transaction state.
            if self.connection.database.lock_wait_once:
                # Consume the one-shot failure.
                self.connection.database.lock_wait_once = False
                # Raise the exact error shape mapped to pending.
                raise _LockWaitError("lock wait")
            # Split the exact bound claim values.
            reset_epoch, game_id, player_id, action_key, fingerprint, resources_json, disposition = params
            # Build the primary-key scope.
            key = (reset_epoch, game_id, player_id, action_key)
            # Insert only when no winner exists.
            if key not in self._state()["claims"]:
                # Preserve the complete immutable row.
                self._state()["claims"][key] = {"reset_epoch": reset_epoch, "game_id": game_id, "player_id": player_id, "action_key": action_key, "request_fingerprint": fingerprint, "resources_json": resources_json, "disposition": disposition}
                # Report one inserted row.
                self.rowcount = 1
            # Stop after insert-ignore semantics.
            return
        # Select and lock one lifecycle claim.
        if sql.startswith("SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition FROM casino_game_action_claims"):
            # Return the detached winning row when present.
            self.result = deepcopy(self._state()["claims"].get(tuple(params)))
            # Stop after the exact point lookup.
            return
        # Select one immutable receipt.
        if sql.startswith("SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition"):
            # Return the detached committed row when present.
            self.result = deepcopy(self._state()["receipts"].get(tuple(params)))
            # Stop after the exact point lookup.
            return
        # Lock one player wallet row.
        if sql.startswith("SELECT player_id, balance FROM casino_players"):
            # Return the detached wallet row when present.
            self.result = deepcopy(self._state()["players"].get(params[0]))
            # Stop after the exact point lookup.
            return
        # Create one empty state document without overwriting existing state.
        if sql.startswith("INSERT INTO casino_documents"):
            # Preserve only the exact resource key and payload.
            key, payload_json, _updated_at = params
            # Create a lockable row only when absent.
            self._state()["documents"].setdefault(key, payload_json)
            # Stop after insert-or-lock semantics.
            return
        # Lock one state document.
        if sql.startswith("SELECT payload_json FROM casino_documents"):
            # Model an ordinary read opening an implicit connector transaction outside explicit DML.
            if self.connection.state is None:
                # Retain the implicit transaction until borrowed close sanitizes the session.
                self.connection.implicit_transaction = True
                # Read the current committed document without creating it.
                payload = self.connection.database.documents.get(params[0])
            # Read the row-locking transaction-local document during explicit update flows.
            else:
                # Preserve the isolated transaction image selected by production.
                payload = self._state()["documents"].get(params[0])
            # Return the driver-like JSON column mapping only when the row exists.
            self.result = None if payload is None else {"payload_json": payload}
            # Stop after the exact point lookup.
            return
        # Update one exact wallet balance.
        if sql.startswith("UPDATE casino_players SET balance"):
            # Split the exact balance, timestamp, and wallet identity.
            balance, _updated_at, wallet_id = params
            # Replace the locked balance.
            self._state()["players"][wallet_id]["balance"] = balance
            # Report one updated row.
            self.rowcount = 1
            # Stop after wallet projection.
            return
        # Append one exact ledger movement.
        if sql.startswith("INSERT INTO casino_ledger"):
            # Retain columns in their production order.
            names = ("ledger_id", "ts", "player_id", "game", "round_id", "transaction_type", "amount", "balance_before", "balance_after", "action_scope", "action_key", "action_fingerprint", "details_json")
            # Build the complete append-only row.
            row = dict(zip(names, params))
            # Reject duplicate ledger identities inside one transaction.
            if row["ledger_id"] in self._state()["ledger"]:
                # Surface a fixture-equivalent uniqueness failure.
                raise AssertionError("duplicate ledger identity")
            # Append the exact row.
            self._state()["ledger"][row["ledger_id"]] = row
            # Report one inserted row.
            self.rowcount = 1
            # Stop after ledger append.
            return
        # Replace one exact state document.
        if sql.startswith("UPDATE casino_documents SET payload_json"):
            # Split exact canonical JSON, timestamp, and resource key.
            payload_json, _updated_at, state_key = params
            # Replace only the locked state row.
            self._state()["documents"][state_key] = payload_json
            # Report one updated row.
            self.rowcount = 1
            # Stop after state projection.
            return
        # Insert one immutable committed receipt.
        if sql.startswith("INSERT INTO casino_game_action_receipts"):
            # Split every explicit bound field; execute is a SQL literal.
            reset_epoch, game_id, player_id, action_key, fingerprint, resources_json, receipt_json, receipt_sha256 = params
            # Build the receipt primary key.
            key = (reset_epoch, game_id, player_id, action_key)
            # Reject duplicate immutable receipt rows.
            if key in self._state()["receipts"]:
                # Surface a fixture-equivalent uniqueness failure.
                raise AssertionError("duplicate receipt")
            # Preserve every exact stored field including execute ownership.
            self._state()["receipts"][key] = {"reset_epoch": reset_epoch, "game_id": game_id, "player_id": player_id, "action_key": action_key, "request_fingerprint": fingerprint, "resources_json": resources_json, "receipt_json": receipt_json, "receipt_sha256": receipt_sha256, "claim_disposition": "execute"}
            # Report one inserted row.
            self.rowcount = 1
            # Stop after receipt append.
            return
        # Reject any unexpected production SQL so tests cannot silently skip behavior.
        raise AssertionError(f"unexpected SQL: {sql}")

    # Return the current optional result row once.
    def fetchone(self):
        # Return the pending dictionary or None.
        return self.result


# Inject deterministic transactional connections without provider configuration.
class _Provider(MySQLStorageProvider):
    # Initialize only the in-memory database and observed leases.
    def __init__(self, database: _Database, *, schema_version: int = 4) -> None:
        # Bind equivalent fake providers to one synthetic relational target identity.
        self.config = MySQLConfig(host="localhost", port=3306, user="runtime", password="synthetic", database="casino_test")
        # Retain the exact schema version accepted or rejected by lifecycle methods.
        self.schema_version = schema_version
        # Retain the shared relational image.
        self.database = database
        # Collect every connection for commit/rollback assertions.
        self.connections = []
        # Track reset borrowing exactly like the production provider.
        self._reset_local = threading.local()

    # Skip connector-backed ordinary readiness in this deterministic suite.
    def ensure_ready(self) -> None:
        # Preserve production planner-purity refusal before the fake no-op readiness path.
        self._reject_planner_mutation()
        # Keep the fake free of external connections.
        return None

    # Enforce the same exact schema-four lifecycle boundary as production.
    def _require_game_action_schema(self, _connection) -> None:
        # Model runtime compatibility SELECTs opening an implicit transaction only before start.
        if _connection.state is None:
            # Require production to clear preflight before explicit transaction entry.
            _connection.implicit_transaction = True
        # Reject clean compatible predecessors for lifecycle mutation.
        if self.schema_version != 4:
            # Publish the same fixed production conflict.
            raise ConflictError("MySQL game action lifecycle requires clean schema 4")

    # Return the clean fake migration state without issuing catalog SQL.
    def _runtime_schema_state(self, _connection):
        # Model one initialized clean schema selected by the fixture.
        return SimpleNamespace(initialized=True, status="clean", current_version=self.schema_version)

    # Lease one deterministic transaction connection.
    def connect(self, **_overrides):
        # Preserve production refusal of raw connection access from a planner.
        self._reject_planner_mutation()
        # Reuse the reset-owned session for same-thread bootstrap at capacity one.
        borrowed = getattr(self._reset_local, "connection", None)
        # Return a no-close facade without allocating a second fake lease.
        if borrowed is not None:
            # Preserve production reset ownership.
            return _BorrowedMySQLConnection(borrowed)
        # Construct one isolated lease over shared committed state.
        connection = _Connection(self.database)
        # Retain it for exact lifecycle assertions.
        self.connections.append(connection)
        # Return the DB-API-compatible fake.
        return connection


# Build one exact resource declaration.
def _resources() -> GameActionResources:
    # Bind one wallet and one route-free state document.
    return GameActionResources(wallet_ids=("human",), state_keys=("slots:human",))


# Build one resource-bound semantic identity.
def _identity(*, action_key="action-1", request=None) -> GameActionIdentity:
    # Reuse the exact resource fixture.
    resources = _resources()
    # Bind request semantics and resources into the canonical fingerprint.
    return GameActionIdentity.create(game_id="slots", player_id="human", action_key=action_key, resources=resources, request=request or {"stake_cents": 100})


# Return one deterministic debit-and-payout plan.
def _plan(_snapshot) -> GameActionPlan:
    # Preserve exact movement order and final state.
    return GameActionPlan.create(outcome={"round_id": "round-1"}, movements=(GameActionMovement(wallet_id="human", amount_cents=-100, reason="wager"), GameActionMovement(wallet_id="human", amount_cents=250, reason="payout")), state_updates={"slots:human": {"spins": 1}})


# Exercise production MySQL SQL against the deterministic transaction model.
class MySQLGameActionProviderTests(unittest.TestCase):
    # Allocate one fresh schema-four store per case.
    def setUp(self) -> None:
        # Construct the committed relational image.
        self.database = _Database()
        # Construct the production provider test seam.
        self.provider = _Provider(self.database)

    # Prove executor-first commit, replay, resolver, and exact relational projections.
    def test_execute_replay_and_resolution_commit_one_transaction(self):
        # Build exact shared semantics.
        resources, identity = _resources(), _identity()
        # Count planner calls across commit and replay.
        calls = []
        # Define one observable deterministic planner.
        def planner(snapshot):
            # Record the immutable snapshot once.
            calls.append(snapshot)
            # Return the exact fixture plan.
            return _plan(snapshot)
        # Execute the new action once.
        receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
        # Require one newly committed result.
        self.assertFalse(replayed)
        # Invoke planner/RNG semantics once.
        self.assertEqual(1, len(calls))
        # Commit exact final fake-money balance.
        self.assertEqual(Decimal("11.5"), self.database.players["human"]["balance"])
        # Append exactly one ledger row per movement.
        self.assertEqual(2, len(self.database.ledger))
        # Commit exact canonical state JSON.
        self.assertEqual('{"spins":1}', self.database.documents["slots:human"])
        # Preserve one execute claim and one receipt.
        self.assertEqual(("execute", 1), (self.database.claims[(1, *identity.scope_key)]["disposition"], len(self.database.receipts)))
        # Verify receipt bytes and stored checksum exactly.
        row = self.database.receipts[(1, *identity.scope_key)]
        # Bind checksum to exact binary-collated text.
        self.assertEqual(row["receipt_sha256"], hashlib.sha256(row["receipt_json"].encode("utf-8")).hexdigest())
        # Replay with a planner that must stay unreachable.
        replay_receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("replay invoked planner"))
        # Return the same immutable receipt semantics.
        self.assertTrue(replayed)
        # Preserve exact receipt value and all projections.
        self.assertEqual(receipt, replay_receipt)
        # Keep ledger append count unchanged.
        self.assertEqual(2, len(self.database.ledger))
        # Resolve the executor-owned committed result without planning.
        self.assertEqual(GameActionResolution(status="committed", receipt=receipt), self.provider.resolve_game_action(identity=identity, resources=resources))

    # Prove resolver-first wins permanently and changed reuse fails before resources.
    def test_resolver_first_blocks_late_execution_and_conflicts(self):
        # Build exact shared semantics.
        resources, identity = _resources(), _identity(action_key="resolver-first")
        # Commit one immutable no-result claim.
        self.assertEqual(GameActionResolution(status="uncommitted"), self.provider.resolve_game_action(identity=identity, resources=resources))
        # Preserve exact pre-execution relational state.
        before = self.database.snapshot()
        # Reject late execution before planner/RNG.
        with self.assertRaisesRegex(ConflictError, "^Game action was durably resolved as uncommitted$"):
            # Attempt execution behind the tombstone.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("late execution invoked planner"))
        # Preserve every committed relation exactly.
        self.assertEqual(before, self.database.snapshot())
        # Build changed semantics under the same action scope.
        changed = _identity(action_key="resolver-first", request={"stake_cents": 200})
        # Reject changed resolver reuse without rewriting the claim.
        with self.assertRaisesRegex(ConflictError, "^Game action key conflicts with durable semantics$"):
            # Attempt changed semantic resolution.
            self.provider.resolve_game_action(identity=changed, resources=resources)
        # Preserve every committed relation after conflict.
        self.assertEqual(before, self.database.snapshot())

    # Prove planner failure rolls back the execute claim and all provisional state.
    def test_planner_failure_rolls_back_every_relation(self):
        # Build exact shared semantics.
        resources, identity = _resources(), _identity(action_key="planner-failure")
        # Capture exact committed rows before execution.
        before = self.database.snapshot()
        # Require the original planner failure.
        with self.assertRaisesRegex(RuntimeError, "^planned failure$"):
            # Execute one planner that fails after snapshot capture.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: (_ for _ in ()).throw(RuntimeError("planned failure")))
        # Roll back claim, empty document seed, wallet, ledger, and receipt together.
        self.assertEqual(before, self.database.snapshot())
        # Permit a resolver to win after the rolled-back executor.
        self.assertEqual(GameActionResolution(status="uncommitted"), self.provider.resolve_game_action(identity=identity, resources=resources))

    # Prove a MySQL planner cannot re-enter any provider-owned mutable boundary.
    def test_planner_provider_mutation_is_rejected_before_connection_or_dml(self):
        # Build exact shared action semantics.
        resources = _resources()
        # Construct an equivalent provider instance for same-target closure proof.
        peer = _Provider(self.database)
        # Enumerate representative same-instance and equivalent-instance mutations.
        mutations = (
            # Attempt an ordinary provider-owned document upsert.
            lambda identity: self.provider.write_document("settings/example", {"value": 2}),
            # Attempt lifecycle resolution through the same provider instance.
            lambda identity: self.provider.resolve_game_action(identity=identity, resources=resources),
            # Attempt mutation through another provider bound to the same database target.
            lambda identity: peer.write_document("settings/example", {"value": 3}),
            # Attempt a hidden relational read through the equivalent provider target.
            lambda identity: peer.load_players(lambda: {"players": []}),
            # Attempt direct connector escape through the equivalent provider target.
            lambda identity: peer.connect(),
        )
        # Exercise each hostile planner under a distinct durable action key.
        for index, mutation in enumerate(mutations):
            # Identify only the mutation category.
            with self.subTest(index=index):
                # Bind one fresh exact action scope.
                identity = _identity(action_key=f"planner-mutation-{index}")
                # Capture committed relational state before the rejected callback.
                before = self.database.snapshot()
                # Capture connection count so the nested provider operation cannot open one.
                connection_count = len(self.provider.connections)
                # Define one hostile planner closure.
                def hostile(_snapshot, selected=mutation, current=identity):
                    # Attempt the selected provider mutation before returning a plan.
                    selected(current)
                    # Keep an otherwise valid plan unreachable.
                    return _plan(_snapshot)
                # Reject the side effect and roll back the outer transaction.
                with self.assertRaisesRegex(ValidationError, "^Game action planner must be side-effect free$"):
                    # Execute through the production MySQL planner boundary.
                    self.provider.execute_game_action_once(identity=identity, resources=resources, planner=hostile)
                # Preserve every committed relation after rollback.
                self.assertEqual(before, self.database.snapshot())
                # Permit only the outer transaction connection, never a nested lease.
                self.assertEqual(connection_count + 1, len(self.provider.connections))
                # Keep the equivalent provider free of a nested connection as well.
                self.assertEqual([], peer.connections)

    # Prove compatible schema predecessors stay readable but cannot use lifecycle DML.
    def test_lifecycle_methods_require_exact_schema_four_and_pending_is_finite(self):
        # Build exact shared semantics.
        resources, identity = _resources(), _identity(action_key="schema-boundary")
        # Exercise both compatible predecessor schemas.
        for version in (2, 3):
            # Identify the exact predecessor.
            with self.subTest(version=version):
                # Construct one provider whose ordinary runtime is compatible.
                provider = _Provider(_Database(), schema_version=version)
                # Reject executor before planner or DML.
                with self.assertRaisesRegex(ConflictError, "requires clean schema 4"):
                    # Attempt schema-four execution on an older clean schema.
                    provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("old schema invoked planner"))
                # Reject resolver before claim DML.
                with self.assertRaisesRegex(ConflictError, "requires clean schema 4"):
                    # Attempt schema-four resolution on an older clean schema.
                    provider.resolve_game_action(identity=identity, resources=resources)
        # Inject one bounded lock wait for the exact schema-four resolver.
        self.database.lock_wait_once = True
        # Return pending without a claim or resource mutation.
        self.assertEqual(GameActionResolution(status="pending"), self.provider.resolve_game_action(identity=identity, resources=resources))
        # Preserve the empty lifecycle relations.
        self.assertEqual(({}, {}, {}), (self.database.claims, self.database.receipts, self.database.ledger))
        # Restore the pooled session lock policy after pending resolution.
        self.assertEqual(50, self.provider.connections[-1].lock_wait)
        # Clear implicit preflight and timed-out transaction state separately.
        self.assertEqual(2, self.provider.connections[-1].rollbacks)

    # Prove resolver session restoration failure still closes the lease and remains replayable.
    def test_resolver_restore_failure_closes_connection_after_durable_result(self):
        # Build one exact resolver-first action.
        resources, identity = _resources(), _identity(action_key="restore-failure")
        # Inject one failure only when restoring the prior lock-wait value.
        self.database.restore_failure_once = True
        # Propagate the session-integrity failure instead of returning a reusable uncertain lease.
        with self.assertRaisesRegex(RuntimeError, "^session restore failed$"):
            # Commit the resolver-first claim before the failing restoration boundary.
            self.provider.resolve_game_action(identity=identity, resources=resources)
        # Require finally to close the exact failed connection.
        self.assertTrue(self.provider.connections[-1].closed)
        # Preserve the committed uncommitted claim despite the lost response.
        self.assertEqual("uncommitted", self.database.claims[(1, *identity.scope_key)]["disposition"])
        # Recover the exact terminal result on a clean retry.
        self.assertEqual(GameActionResolution(status="uncommitted"), self.provider.resolve_game_action(identity=identity, resources=resources))

    # Prove reset hides old lifecycle rows, blocks actions through bootstrap, and permits fresh key reuse.
    def test_reset_epoch_blocks_gap_and_reuses_one_session_at_capacity_one(self):
        # Build and commit one epoch-one action under the shared key.
        resources, identity = _resources(), _identity(action_key="reset-reuse")
        # Persist the old receipt and mutable projections.
        first_receipt, _replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=_plan)
        # Record the connection count before reset acquires its sole retained lease.
        prior_connections = len(self.provider.connections)
        # Hold the production reset boundary through caller bootstrap.
        with self.provider.reset_transaction():
            # Require phase one to retire the prior namespace durably.
            self.assertEqual({"state_id": 1, "current_epoch": 2, "phase": "resetting"}, self.database.epoch)
            # Preserve old immutable lifecycle rows while mutable projections are empty.
            self.assertEqual((1, 1, {}, {}, {}), (len(self.database.claims), len(self.database.receipts), self.database.players, self.database.documents, self.database.ledger))
            # Refuse execution before any claim, resource, or planner access.
            with self.assertRaisesRegex(ConflictError, "reset is in progress"):
                # Keep the planner unreachable during bootstrap.
                self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("reset gap invoked planner"))
            # Return finite pending for the nonblocking resolver.
            self.assertEqual(GameActionResolution(status="pending"), self.provider.resolve_game_action(identity=identity, resources=resources))
            # Keep the old claim count unchanged during the resetting gap.
            self.assertEqual(1, len(self.database.claims))
            # Read the missing Admin identity document through the same path bootstrap uses first.
            self.assertEqual({"schema_version": 1, "users": []}, self.provider.read_document("auth/users.json", lambda: {"schema_version": 1, "users": []}))
            # Resolve the retained physical reset lease after borrowed read cleanup.
            reset_connection = self.provider.connections[-1]
            # Require borrowed close to end the implicit SELECT transaction without releasing GET_LOCK.
            self.assertFalse(reset_connection.implicit_transaction)
            # Keep exact session-level named-lock ownership across the sanitized operation boundary.
            self.assertIs(self.database.named_lock, reset_connection)
            # Perform the next explicit document transaction exactly as Admin creation does.
            updated_users = self.provider.update_document("auth/users.json", lambda state: {**state, "users": [{"user_id": "admin-204", "roles": ["admin", "platform_owner"]}]}, lambda: {"schema_version": 1, "users": []})
            # Require explicit transaction start and commit to succeed after the prior read.
            self.assertEqual([{"user_id": "admin-204", "roles": ["admin", "platform_owner"]}], updated_users["users"])
            # Preserve the same reset-owned named lock after the document write closes its facade.
            self.assertIs(self.database.named_lock, reset_connection)
            # Bootstrap the fresh wallet through the borrowed no-close reset session.
            self.provider.bootstrap_players({"players": [{"player_id": "human", "display_name": "Human", "type": "human", "balance": 20, "created_at": "created", "updated_at": "updated", "status": "active"}]})
            # Reuse the retained outer lease rather than checking out another connection.
            self.assertEqual(prior_connections + 1, len(self.provider.connections))
        # Release exact ready visibility only after bootstrap commits.
        self.assertEqual({"state_id": 1, "current_epoch": 2, "phase": "ready"}, self.database.epoch)
        # Release the session-level named lock only after ready finalization.
        self.assertIsNone(self.database.named_lock)
        # Close the retained outer lease exactly once after lock release.
        self.assertTrue(reset_connection.closed)
        # Execute the same caller action key as fresh work in epoch two.
        second_receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=_plan)
        # Require a new action rather than stale epoch-one replay.
        self.assertFalse(replayed)
        # Distinguish the result through its fresh wallet snapshot.
        self.assertNotEqual(first_receipt.snapshot_before, second_receipt.snapshot_before)
        # Retain both immutable histories under distinct epoch-prefixed primary keys.
        self.assertEqual({1, 2}, {key[0] for key in self.database.receipts})

    # Prove failed reset bodies and finalizers stay unavailable until a later explicit reset.
    def test_reset_failure_leaves_resetting_and_later_reset_advances_again(self):
        # Fail the caller bootstrap after durable phase one commits epoch two.
        with self.assertRaisesRegex(RuntimeError, "body failed"):
            # Enter the reset boundary with no successful phase-two release.
            with self.provider.reset_transaction():
                # Surface the synthetic caller-body failure.
                raise RuntimeError("body failed")
        # Leave the durable namespace unavailable rather than silently reopening it.
        self.assertEqual({"state_id": 1, "current_epoch": 2, "phase": "resetting"}, self.database.epoch)
        # Permit a later explicit reset only after the prior named lock is released.
        with self.provider.reset_transaction():
            # Recovery advances again and re-clears any partial bootstrap state.
            self.assertEqual({"state_id": 1, "current_epoch": 3, "phase": "resetting"}, self.database.epoch)
            # Bootstrap the exact fresh wallet on the retained lease.
            self.provider.bootstrap_players({"players": [{"player_id": "human", "display_name": "Human", "type": "human", "balance": 30, "created_at": "created", "updated_at": "updated", "status": "active"}]})
        # Publish only the later fully bootstrapped namespace.
        self.assertEqual({"state_id": 1, "current_epoch": 3, "phase": "ready"}, self.database.epoch)
        # Inject one exact phase-two compare-and-set failure on the next reset.
        self.database.finalize_failure_once = True
        # Require finalization failure instead of releasing partial state.
        with self.assertRaisesRegex(ConflictError, "operator recovery"):
            # Complete a body whose phase release is deliberately refused.
            with self.provider.reset_transaction():
                # Bootstrap one row whose partial state will be cleared by recovery.
                self.provider.bootstrap_players({"players": [{"player_id": "human", "display_name": "Human", "type": "human", "balance": 40, "created_at": "created", "updated_at": "updated", "status": "active"}]})
        # Retain exact resetting phase after failed finalization.
        self.assertEqual({"state_id": 1, "current_epoch": 4, "phase": "resetting"}, self.database.epoch)
        # Run one explicit recovery reset and allow its empty body to finish.
        with self.provider.reset_transaction():
            # Advance beyond the failed owner and clear its partial bootstrap rows.
            self.assertEqual((5, {}), (self.database.epoch["current_epoch"], self.database.players))
        # End in the ready fifth namespace.
        self.assertEqual({"state_id": 1, "current_epoch": 5, "phase": "ready"}, self.database.epoch)

    # Prove equivalent providers cannot overlap one target-scoped reset.
    def test_concurrent_reset_is_nonblocking_and_does_not_mutate(self):
        # Construct an equivalent provider over the same target and committed state.
        peer = _Provider(self.database)
        # Let the first provider own phase one and the named reset lock.
        with self.provider.reset_transaction():
            # Capture the exact resetting state before the contender.
            before = self.database.snapshot()
            # Reject the contender before pool checkout or another epoch advance.
            with self.assertRaisesRegex(ConflictError, "already in progress"):
                # Attempt one overlapping explicit reset.
                with peer.reset_transaction():
                    # Keep the unreachable body explicit.
                    self.fail("concurrent reset body ran")
            # Preserve every committed relation and the first owner's phase.
            self.assertEqual(before, self.database.snapshot())
            # Keep the peer free of connection allocation under local ownership.
            self.assertEqual([], peer.connections)

    # Prove production SQL never updates or deletes immutable lifecycle rows.
    def test_lifecycle_sql_is_append_only_and_resolver_has_no_planner(self):
        # Read only the two production lifecycle methods.
        execute_source = inspect.getsource(MySQLStorageProvider.execute_game_action_once).upper()
        # Read the resolver source separately for no-planner proof.
        resolve_source = inspect.getsource(MySQLStorageProvider.resolve_game_action).upper()
        # Read the receipt selector for current-read MVCC proof.
        receipt_source = inspect.getsource(MySQLStorageProvider._select_mysql_game_action_receipt).upper()
        # Reject lifecycle-row update or delete statements.
        for source in (execute_source, resolve_source):
            # Reject mutable claim history.
            self.assertNotIn("UPDATE CASINO_GAME_ACTION_CLAIMS", source)
            # Reject claim deletion.
            self.assertNotIn("DELETE FROM CASINO_GAME_ACTION_CLAIMS", source)
            # Reject receipt mutation.
            self.assertNotIn("UPDATE CASINO_GAME_ACTION_RECEIPTS", source)
            # Reject receipt deletion.
            self.assertNotIn("DELETE FROM CASINO_GAME_ACTION_RECEIPTS", source)
        # Require resolver never to accept a planner parameter or invoke a planner callable.
        self.assertNotIn("PLANNER:", resolve_source)
        # Permit only the fail-closed purity guard's name, never a direct planner call.
        self.assertNotIn("PLANNER(", resolve_source)
        # Require a SELECT-only current read that bypasses stale consistent snapshots.
        self.assertIn("FOR SHARE", receipt_source)
        # Preserve append-only runtime grants by avoiding UPDATE-strength receipt locks.
        self.assertNotIn("FOR UPDATE", receipt_source)
        # Read the immutable claim selector for the same least-privilege current-read proof.
        claim_source = inspect.getsource(MySQLStorageProvider._claim_mysql_game_action).upper()
        # Require current shared locking after duplicate contenders serialize.
        self.assertIn("FOR SHARE", claim_source)
        # Avoid UPDATE-strength privileges on immutable claims.
        self.assertNotIn("FOR UPDATE", claim_source)


# Support direct focused execution in local and CI validation.
if __name__ == "__main__":
    # Run the focused suite with standard unittest output.
    unittest.main()
