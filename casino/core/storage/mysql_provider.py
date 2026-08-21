# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Complete MySQL storage provider ownership for the transitional package boundary."""

# Import annotations so provider method hints can refer to runtime-only protocol shapes.
from __future__ import annotations
# Import required dependency so deterministic reset lock names remain target-scoped.
import hashlib
# Import required dependency so MySQL JSON columns preserve canonical storage shapes.
import json
# Import required dependency so provider readiness, planner, and reset state remain thread-safe.
import threading
# Import required dependency so the reset lifecycle remains a bounded context manager.
from contextlib import contextmanager
# Import required dependency so MySQL wallet mutations keep exact cents arithmetic.
from decimal import Decimal
# Import required dependency so provider methods retain callable and DB-API contracts.
from typing import Any, Callable

# Import the current document schema version projected by MySQL player reads.
from casino.config import SCHEMA_VERSION
# Import the canonical timestamp helper used by MySQL rows and documents.
from casino.core.clock import utc_now
# Import the provider-neutral game-action executor contract.
from casino.core.game_action import GameActionExecutor
# Import read-only MySQL migration compatibility without exposing deployment credentials.
from casino.core.mysql_migrations import verify_runtime_compatibility
# Import the bounded process-local MySQL connection lifecycle.
from casino.core.mysql_pool import MySQLConnectionPool, MySQLPoolConfig
# Import the provider-neutral storage contract, configuration, and shared row helpers.
from casino.core.storage.base import ECONOMICS_EXCLUDED_TRANSACTION_FRAGMENTS, HISTORY_FIELDS, MySQLConfig, StorageProvider, _action_details, _action_fingerprint, _action_scope, _decode_json, _history_from_row, _ledger_event, _ledger_from_row, _money, _money_decimal, _normalizable_players_document, _normalize_action_key, _quantized_money, _quantized_money_decimal, _validate_action_replay, _validate_wallet_normalization_replay, _validated_players_document, _validated_strict_document, _wallet_normalization_event
# Import the shared bounded epoch ceiling used by reset lifecycle validation.
from casino.core.storage.reset import _GAME_ACTION_MAX_EPOCH
# Import canonical JSON lifecycle codecs reused without creating a concrete-provider cycle.
from casino.core.storage.game_actions_json import JsonGameActionMixin
# Import the schema-four MySQL lifecycle implementation inherited by the concrete provider.
from casino.core.storage.game_actions_mysql import MySQLGameActionMixin
# Import schema-aware first-class MySQL session ownership.
from casino.core.storage.sessions_mysql import MySQLSessionMixin
# Import stable public errors preserved by the extracted provider implementation.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError

# Track active MySQL planners separately from filesystem-root gate ownership.
_MYSQL_PLANNER_LOCAL = threading.local()
# Serialize process-local reset target registration across equivalent provider instances.
_MYSQL_RESET_REGISTRY_LOCK = threading.RLock()
# Track targets whose retained session currently owns the reset lifecycle.
_MYSQL_RESET_TARGETS: set[tuple[str, int, str]] = set()

# Define the MySQLStorageProvider for configured multi-user persistence.
# Define a no-close facade that lets reset bootstrap reuse its one owned pool lease.
class _BorrowedMySQLConnection:
    # Retain the reset-owned lease without transferring close authority.
    def __init__(self, connection: Any) -> None:
        # Store only the caller-owned lease for transparent DB-API delegation.
        self._connection = connection
        # Track operation-boundary cleanup without transferring outer close authority.
        self._closed = False

    # Delegate every DB-API attribute except the explicit no-close boundary below.
    def __getattr__(self, name: str) -> Any:
        # Preserve cursor and transaction behavior on the exact reset session.
        return getattr(self._connection, name)

    # Keep nested provider operations from returning the reset lease to the pool.
    def close(self) -> None:
        # Preserve idempotent DB-API close behavior for nested finally blocks.
        if self._closed:
            # Avoid repeated session cleanup after the operation already ended.
            return
        # End every implicit read or failed-write transaction before the next bootstrap helper.
        self._connection.rollback()
        # Mark cleanup complete only after the retained session is transaction-clean.
        self._closed = True


class MySQLStorageProvider(MySQLSessionMixin, MySQLGameActionMixin, StorageProvider, GameActionExecutor):
    # Store the provider name used by diagnostics and tests.
    name = "mysql"

    # Initialize the MySQL provider from explicit or environment connection and pool config.
    def __init__(self, config: MySQLConfig | None = None, pool_config: MySQLPoolConfig | None = None) -> None:
        # Store the connection configuration without opening a connection yet.
        self.config = config or MySQLConfig.from_env()
        # Build one lazy bounded pool for this process without opening a physical connection.
        self._pool = MySQLConnectionPool(self._open_physical_connection, pool_config)
        # Track whether this process has completed exact read-only schema compatibility verification.
        self._ready = False
        # Cache only the sanitized verified migration version for schema-aware storage lanes.
        self._schema_version: int | None = None
        # Serialize first-use compatibility verification across concurrent request threads.
        self._ready_lock = threading.RLock()
        # Track same-thread reset lease borrowing without sharing authority across requests.
        self._reset_local = threading.local()

    # Import mysql.connector only when the MySQL provider is selected.
    def _connector(self):
        # Start protected import so default JSON runs do not require the dependency.
        try:
            # Import the optional MySQL driver at runtime.
            import mysql.connector
        # Surface a focused dependency error when MySQL is configured without the driver.
        except ImportError as exc:
            # Raise a runtime error that names the optional dependency.
            raise RuntimeError("MySQL storage requires the optional mysql-connector-python dependency.") from exc
        # Return the imported connector module.
        return mysql.connector

    # Open one physical MySQL connection for the pool using fixed credentials and a bounded timeout.
    def _open_physical_connection(self, connection_timeout: int):
        # Add only the validated connector deadline to the configured credentials.
        connection_options = {**self.config.kwargs(), "connection_timeout": connection_timeout}
        # Return one new physical DB-API connection to the pool.
        return self._connector().connect(**connection_options)

    # Lease a request-scoped MySQL connection from the bounded process-local pool.
    def connect(self, **overrides):
        # Reject raw connection access from inside a planner on this database target.
        self._reject_planner_mutation()
        # Reject connector overrides that could cross credential, database, or session boundaries.
        if set(overrides) - {"connection_timeout"}:
            # Raise a fixed validation error without echoing option names or values.
            raise ValueError("Unsupported MySQL connection override.")
        # Reuse the reset-owned lease for synchronous bootstrap calls at pool capacity one.
        borrowed = getattr(self._reset_local, "connection", None)
        # Return a no-close facade only while this thread owns an active reset session.
        if borrowed is not None:
            # Prevent nested bootstrap helpers from returning the sole lease early.
            return _BorrowedMySQLConnection(borrowed)
        # Preserve the established readiness-probe timeout seam while pooling ordinary operations.
        connection_timeout = overrides.get("connection_timeout")
        # Return a lease whose close sanitizes and returns the physical connection.
        return self._pool.acquire(connect_timeout_seconds=connection_timeout)

    # Return the internal secret-free pool evidence used by lifecycle tests and future contracted telemetry.
    def pool_snapshot(self) -> dict:
        # Return only fixed low-cardinality gauges, counters, policy, and wait buckets.
        return self._pool.snapshot()

    # Close idle physical sessions and make this provider reject future checkout.
    def close_pool(self) -> None:
        # Refuse provider lifecycle mutation from inside a supposedly pure planner.
        self._reject_planner_mutation()
        # Delegate fail-safe connection shutdown to the pool.
        self._pool.close_all()

    # Return the configured relational target key shared by equivalent provider instances.
    def _planner_key(self) -> tuple[str, int, str]:
        # Normalize host case while preserving exact port and database ownership.
        return (self.config.host.lower(), self.config.port, self.config.database)

    # Return whether this thread is planning through this configured database boundary.
    def _planner_is_active(self) -> bool:
        # Read the thread-local target set without sharing a mutable default.
        providers = getattr(_MYSQL_PLANNER_LOCAL, "providers", set())
        # Bind purity across equivalent provider instances for the same relational target.
        return self._planner_key() in providers

    # Return whether this process already owns an active reset for the same target.
    def _reset_is_active(self) -> bool:
        # Serialize registry observation with reset acquisition and release.
        with _MYSQL_RESET_REGISTRY_LOCK:
            # Match equivalent provider instances through the secret-free target key.
            return self._planner_key() in _MYSQL_RESET_TARGETS

    # Reject MySQL provider mutation attempted from inside an action planner.
    def _reject_planner_mutation(self) -> None:
        # Fail before opening a connection or changing provider lifecycle state.
        if self._planner_is_active():
            # Reuse the provider-neutral fixed purity error.
            raise ValidationError("Game action planner must be side-effect free")

    # Mark one synchronous planner call as unable to re-enter this provider mutably.
    @contextmanager
    def _planner_boundary(self):
        # Copy the active target set so nesting remains thread-local and explicit.
        providers = set(getattr(_MYSQL_PLANNER_LOCAL, "providers", set()))
        # Resolve this provider's secret-free relational target identity.
        planner_key = self._planner_key()
        # Reject recursive planning through the same target before another connection.
        if planner_key in providers:
            # Preserve the fixed provider-neutral validation boundary.
            raise ValidationError("Game action planner must be side-effect free")
        # Add this exact configured target for the synchronous callback lifetime.
        providers.add(planner_key)
        # Publish the active set only to this thread.
        _MYSQL_PLANNER_LOCAL.providers = providers
        try:
            # Transfer control to the caller-owned planner.
            yield
        finally:
            # Remove this target even when the planner raises.
            providers.discard(planner_key)
            # Retain any independently active outer database boundaries.
            _MYSQL_PLANNER_LOCAL.providers = providers

    # Verify the exact MySQL migration state before reads and writes.
    def ensure_ready(self) -> None:
        # Refuse hidden provider access through a planner closure before cached readiness.
        self._reject_planner_mutation()
        # Return immediately after this provider instance has completed a read-only compatibility check.
        if self._ready:
            # Avoid repeating metadata reads on every document or game-state operation.
            return
        # Serialize the first schema check so request threads share one verified state.
        with self._ready_lock:
            # Return when another thread completed verification while this thread waited.
            if self._ready:
                # Reuse the schema compatibility established by the winning thread.
                return
            # Open a runtime-identity connection for SELECT-only compatibility verification.
            connection = self.connect()
            # Start protected schema verification so the connection is always closed.
            try:
                # Fail closed on missing, old, future, dirty, gapped, or checksum-mismatched state.
                schema_state = verify_runtime_compatibility(connection)
                # Retain only the clean applied version, never target or credential metadata.
                self._schema_version = schema_state.current_version
                # Mark this provider ready only after exact read-only verification.
                self._ready = True
            # Always close the connection after schema verification.
            finally:
                # Close the runtime connection without issuing DDL or migration-state DML.
                connection.close()

    # Reuse the canonical Phase0c codecs without creating a second receipt format.
    _plain_canonical = JsonGameActionMixin._plain_canonical
    # Reuse duplicate-key rejection for immutable MySQL text fields.
    _unique_json_object = JsonGameActionMixin._unique_json_object
    # Reuse exact resource serialization for schema-three compatibility.
    _serialize_game_action_resources = JsonGameActionMixin._serialize_game_action_resources
    # Reuse delimiter-safe durable scope encoding for movement identities.
    _game_action_scope_key = JsonGameActionMixin._game_action_scope_key
    # Reuse exact resource reconstruction for conflict checks.
    _deserialize_game_action_resources = JsonGameActionMixin._deserialize_game_action_resources
    # Reuse exact identity reconstruction embedded in legacy receipts.
    _deserialize_game_action_identity = JsonGameActionMixin._deserialize_game_action_identity
    # Reuse exact identity serialization embedded in legacy receipts.
    _serialize_game_action_identity = JsonGameActionMixin._serialize_game_action_identity
    # Reuse immutable snapshot serialization.
    _serialize_game_action_snapshot = JsonGameActionMixin._serialize_game_action_snapshot
    # Reuse immutable snapshot reconstruction.
    _deserialize_game_action_snapshot = JsonGameActionMixin._deserialize_game_action_snapshot
    # Reuse immutable plan serialization.
    _serialize_game_action_plan = JsonGameActionMixin._serialize_game_action_plan
    # Reuse immutable plan reconstruction.
    _deserialize_game_action_plan = JsonGameActionMixin._deserialize_game_action_plan
    # Reuse the complete legacy-compatible receipt serialization.
    _serialize_game_action_receipt = JsonGameActionMixin._serialize_game_action_receipt
    # Reuse the complete legacy-compatible receipt reconstruction.
    _deserialize_game_action_receipt = JsonGameActionMixin._deserialize_game_action_receipt
    # Reuse exact JSON cent conversion for deterministic ledger event fields.
    _json_wallet_cents = JsonGameActionMixin._json_wallet_cents
    # Reuse compatible JSON numeric projection for ledger events.
    _json_wallet_value = JsonGameActionMixin._json_wallet_value
    # Reuse deterministic movement ledger construction across providers.
    _game_action_ledger_events = JsonGameActionMixin._game_action_ledger_events

    # Derive one bounded non-secret named lock for this exact relational reset target.
    def _mysql_reset_lock_name(self) -> str:
        # Serialize only the normalized host, port, and database identity.
        target = f"{self.config.host.lower()}:{self.config.port}/{self.config.database}"
        # Keep the lock name below MySQL's 64-character boundary.
        return f"casino-reset-{hashlib.sha256(target.encode('utf-8')).hexdigest()[:48]}"

    # Delete only reset-owned mutable projections inside an active transaction.
    def _clear_mysql_mutable_state(self, cursor) -> None:
        # Delete native authentication sessions before documents and account bootstrap.
        if getattr(self, "_schema_version", None) == 5:
            # Clear only mutable session rows; no lifecycle claim or receipt history is affected.
            cursor.execute("DELETE FROM casino_sessions")
        # Delete ledger rows before players to satisfy foreign keys.
        cursor.execute("DELETE FROM casino_ledger")
        # Delete history rows because reset starts a fresh visible outcome set.
        cursor.execute("DELETE FROM casino_history")
        # Delete JSON document rows because caller bootstrap restores reviewed defaults.
        cursor.execute("DELETE FROM casino_documents")
        # Delete player rows after dependent ledger rows.
        cursor.execute("DELETE FROM casino_players")

    # Hold a target-scoped reset lock through clear, caller bootstrap, and phase release.
    @contextmanager
    def reset_transaction(self):
        # Reject destructive provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Reject same-thread nested resets before borrowing can hide ownership.
        if getattr(self._reset_local, "connection", None) is not None:
            # Preserve the outer reset as the sole owner.
            raise ConflictError("MySQL reset is already in progress")
        # Verify the compatible schema before opening the owned reset lease.
        self.ensure_ready()
        # Resolve the process-wide target identity before pool checkout.
        reset_target = self._planner_key()
        # Claim local reset ownership nonblockingly for capacity-one pools.
        with _MYSQL_RESET_REGISTRY_LOCK:
            # Reject another provider instance already resetting this target.
            if reset_target in _MYSQL_RESET_TARGETS:
                # Avoid waiting for its retained sole pool lease.
                raise ConflictError("MySQL reset is already in progress")
            # Reserve this target until named-lock acquisition succeeds or cleanup runs.
            _MYSQL_RESET_TARGETS.add(reset_target)
        try:
            # Acquire the one pool lease retained across synchronous caller bootstrap.
            connection = self.connect()
        # Release local ownership if pool checkout itself fails.
        except BaseException:
            # Serialize exact registry cleanup across equivalent provider instances.
            with _MYSQL_RESET_REGISTRY_LOCK:
                # Remove only this target's provisional ownership.
                _MYSQL_RESET_TARGETS.discard(reset_target)
            # Preserve the original checkout failure.
            raise
        # Derive the fixed target-scoped named lock without credentials.
        lock_name = self._mysql_reset_lock_name()
        # Track whether this session owns the server lock for exact release.
        named_lock_acquired = False
        # Track whether schema four requires durable phase finalization.
        reset_epoch = None
        try:
            # Use dictionary rows for strict named-lock and epoch validation.
            cursor = connection.cursor(dictionary=True)
            # Attempt the target-scoped session lock without waiting behind another reset.
            cursor.execute("SELECT GET_LOCK(%s, 0) AS acquired", (lock_name,))
            # Read the exact finite acquisition result.
            lock_row = cursor.fetchone()
            # Reject contention, connector coercion, or server lock failure uniformly.
            if type(lock_row) is not dict or lock_row.get("acquired") != 1:
                # Avoid any reset phase or mutable-state change.
                raise ConflictError("MySQL reset is already in progress")
            # Record sole session ownership before any transaction begins.
            named_lock_acquired = True
            # End the implicit transaction opened by the named-lock preflight query.
            connection.rollback()
            # Start phase one across epoch ownership and mutable deletion.
            connection.start_transaction()
            # Re-read exact migration state inside the reset transaction.
            schema_state = self._runtime_schema_state(connection)
            # Activate durable epoch semantics on every clean schema containing migration four.
            if schema_state.initialized and schema_state.status == "clean" and schema_state.current_version in {4, 5}:
                # Lock the singleton exclusively before any mutable table deletion.
                epoch_state = self._mysql_game_action_epoch(cursor, exclusive=True)
                # Refuse namespace overflow without changing the existing phase.
                if epoch_state["current_epoch"] >= _GAME_ACTION_MAX_EPOCH:
                    # Preserve all relational state for operator recovery.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
                # Advance again even when recovering a prior failed resetting phase.
                reset_epoch = epoch_state["current_epoch"] + 1
                # Bind the new namespace and unavailable phase to the exact prior row.
                cursor.execute(
                    "UPDATE casino_game_action_epoch_state SET current_epoch = %s, phase = 'resetting' WHERE state_id = 1 AND current_epoch = %s AND phase = %s",
                    (reset_epoch, epoch_state["current_epoch"], epoch_state["phase"]),
                )
                # Require the singleton compare-and-set to update exactly once.
                if cursor.rowcount != 1:
                    # Refuse ambiguous reset ownership.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
            # Preserve compatible schema-two/three reset behavior without lifecycle access.
            elif not schema_state.initialized or schema_state.status != "clean" or schema_state.current_version not in {2, 3}:
                # Refuse dirty, partial, future, or unsupported schemas before deletion.
                raise ConflictError("MySQL storage schema requires operator recovery")
            # Delete only mutable projections; lifecycle claims and receipts remain append-only.
            self._clear_mysql_mutable_state(cursor)
            # Commit phase one so bootstrap can use the same session without holding row deletes.
            connection.commit()
            # Expose only a no-close facade to nested same-thread provider calls.
            self._reset_local.connection = connection
            try:
                # Yield while the named lock and resetting phase exclude every lifecycle action.
                yield self
            finally:
                # End lease borrowing before finalization or failure cleanup.
                self._reset_local.connection = None
            # Release schema-four lifecycle visibility only after caller bootstrap succeeds.
            if reset_epoch is not None:
                # Clear any connector transaction residue left by caller-owned reads.
                connection.rollback()
                # Start one exact phase-two transaction.
                connection.start_transaction()
                # Require schema four again before changing durable readiness.
                self._require_game_action_schema(connection)
                # Lock the exact singleton for compare-and-set finalization.
                finalized_state = self._mysql_game_action_epoch(cursor, exclusive=True)
                # Require the bound epoch to remain unavailable and unchanged.
                if finalized_state != {"state_id": 1, "current_epoch": reset_epoch, "phase": "resetting"}:
                    # Leave the durable phase unavailable for operator recovery.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
                # Publish ready only for this exact reset attempt's namespace.
                cursor.execute(
                    "UPDATE casino_game_action_epoch_state SET phase = 'ready' WHERE state_id = 1 AND current_epoch = %s AND phase = 'resetting'",
                    (reset_epoch,),
                )
                # Require one exact singleton transition.
                if cursor.rowcount != 1:
                    # Preserve resetting on ambiguous finalization.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
                # Commit the final ready phase after all bootstrap writes are durable.
                connection.commit()
        # Roll back only the current session transaction while retaining durable resetting phase.
        except BaseException:
            # Discard partial phase-one, bootstrap-call, or phase-two work on this lease.
            connection.rollback()
            # Preserve the original bounded failure.
            raise
        finally:
            # Clear borrowing even when yield or finalization exits exceptionally.
            self._reset_local.connection = None
            try:
                # Release only a named lock this session proved it acquired.
                if named_lock_acquired:
                    # End any implicit or failed transaction before the release query.
                    connection.rollback()
                    # Open one final dictionary cursor on the retained session.
                    release_cursor = connection.cursor(dictionary=True)
                    # Release the exact target-scoped user lock.
                    release_cursor.execute("SELECT RELEASE_LOCK(%s) AS released", (lock_name,))
                    # Require this session to report successful release.
                    release_row = release_cursor.fetchone()
                    # Treat missing ownership or connector coercion as a reset failure.
                    if type(release_row) is not dict or release_row.get("released") != 1:
                        # Prevent a pooled session with uncertain user-lock state from being trusted.
                        raise ConflictError("MySQL reset lock release failed")
            finally:
                try:
                    # Return or discard the sole outer lease after every outcome.
                    connection.close()
                finally:
                    # Release process-local target ownership even if pool cleanup fails.
                    with _MYSQL_RESET_REGISTRY_LOCK:
                        # Let later explicit reset attempts recover a durable resetting phase.
                        _MYSQL_RESET_TARGETS.discard(reset_target)

    # Reset MySQL mutable state through the complete phase-owned boundary.
    def reset(self) -> None:
        # Reuse the same reset transaction with an intentionally empty caller body.
        with self.reset_transaction():
            # Preserve direct reset behavior without additional bootstrap writes.
            pass

    # Convert a MySQL player row into the existing API shape.
    def _player_from_row(self, row: dict) -> dict:
        # Return a dict with the current public player field names.
        return {"player_id": row["player_id"], "display_name": row["display_name"], "type": row["player_type"], "balance": _money(row["balance"]), "created_at": row["created_at"], "updated_at": row["updated_at"], "status": row["status"]}

    # Load players from MySQL without mutating storage from a read path.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Ensure schema exists before reading players.
        self.ensure_ready()
        # Open a connection for the bootstrap and read transaction.
        connection = self.connect()
        # Start protected read logic so the connection is always closed.
        try:
            # Open a dictionary cursor so row mapping is explicit.
            cursor = connection.cursor(dictionary=True)
            # Read players in stable order for deterministic API responses.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players ORDER BY player_id")
            try:
                # Convert database rows into the JSON-compatible state document.
                players = [self._player_from_row(row) for row in cursor.fetchall()]
                # Validate the same complete money shape required from JSON storage.
                return _validated_players_document({"schema_version": SCHEMA_VERSION, "players": players})
            # Normalize corrupt row values without reflecting driver or stored details.
            except (TypeError, ValueError, OverflowError, ValidationError, ConflictError):
                # Preserve database state and require operator-led repair.
                raise ConflictError("Wallet storage requires operator recovery") from None
        # Always close the connection after loading players.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Read one player with an indexed predicate instead of scanning the wallet table.
    def get_player(self, player_id: str, default_factory: Callable[[], dict]) -> dict | None:
        # Ensure the compatible schema exists before querying one wallet.
        self.ensure_ready()
        # Borrow one connection for the point read.
        connection = self.connect()
        # Protect lease cleanup for every result and mapping failure.
        try:
            # Open a dictionary cursor so the established player mapper remains authoritative.
            cursor = connection.cursor(dictionary=True)
            # Select only the exact primary-key player row.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s", (player_id,))
            # Read at most the one row guaranteed by the primary key.
            row = cursor.fetchone()
            # Preserve the provider-neutral missing result.
            if row is None:
                # Return no player without loading unrelated wallets.
                return None
            # Convert and validate the selected money row through the existing strict mapper.
            try:
                # Build the established public player dictionary.
                player = self._player_from_row(row)
                # Validate this point row inside the canonical player document boundary.
                return _validated_players_document({"schema_version": SCHEMA_VERSION, "players": [player]})["players"][0]
            # Normalize malformed stored values to the fixed operator-recovery boundary.
            except (TypeError, ValueError, OverflowError, ValidationError, ConflictError):
                # Preserve the database row for explicit repair.
                raise ConflictError("Wallet storage requires operator recovery") from None
        # Always release the point-read connection.
        finally:
            # Return the lease to the provider pool.
            connection.close()

    # Scan or repair MySQL wallet residue in one row-locked transaction. (STORAGE-015, LEDGER-036)
    def normalize_wallet_balances(self, *, apply: bool = False) -> dict:
        # Reject operator mutation attempted from inside a game-action planner.
        self._reject_planner_mutation()
        # Require the ordinary compatible schema before opening the operator transaction.
        self.ensure_ready()
        # Borrow one connection for the complete scan or repair.
        connection = self.connect()
        # Protect rollback and lease cleanup for every result.
        try:
            # Start one transaction so every inspected wallet remains stable through commit.
            connection.start_transaction()
            # Open a dictionary cursor for explicit wallet and ledger projections.
            cursor = connection.cursor(dictionary=True)
            # Lock all wallet rows in deterministic identity order.
            cursor.execute("SELECT player_id, balance FROM casino_players ORDER BY player_id FOR UPDATE")
            # Materialize the bounded result set while the row locks remain held.
            rows = cursor.fetchall()
            # Collect exact residue pairs without mutating any row yet.
            residues = []
            # Visit every durable wallet exactly once.
            for row in rows:
                try:
                    # Decode the exact provider value without accepting coercion.
                    stored = _money_decimal(row["balance"])
                    # Derive the canonical cent value using the shared rounding rule.
                    normalized = _quantized_money_decimal(stored)
                # Normalize malformed database money to the fixed recovery boundary.
                except ValidationError:
                    # Keep every row unchanged for operator inspection.
                    raise ConflictError("Wallet storage requires operator recovery") from None
                # Refuse insolvent wallets instead of disguising them as rounding residue.
                if stored < 0:
                    # Preserve the complete transaction for explicit accounting recovery.
                    raise ConflictError("Wallet storage requires operator recovery")
                # Retain only rows whose source has genuine sub-cent residue.
                if stored != normalized:
                    # Store the exact row identity and decimal pair for the optional apply path.
                    residues.append((row["player_id"], stored, normalized))
            # End a read-only scan without publishing any row or audit mutation.
            if not apply:
                # Release all row locks before returning bounded counts.
                connection.rollback()
                # Return no wallet identities or source values.
                return {"provider": self.name, "checked": len(rows), "residue_count": len(residues), "normalized_count": 0, "clean": not residues, "applied": False}
            # Publish each normalization row and wallet update inside this same transaction.
            for player_id, stored, normalized in residues:
                # Build the deterministic provider-neutral audit event.
                event = _wallet_normalization_event(player_id, stored, normalized)
                # Read a possible earlier compatible row by deterministic ledger identity.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json FROM casino_ledger WHERE ledger_id = %s", (event["ledger_id"],))
                # Resolve an interrupted or repeated operator invocation.
                existing_row = cursor.fetchone()
                # Insert the immutable audit row when this exact repair was not recorded earlier.
                if existing_row is None:
                    # Persist the zero-cent visible adjustment plus exact residue details.
                    cursor.execute(
                        "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Append one deterministic operator audit row.
                        (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], Decimal("0.00"), normalized, normalized, event["action_scope"], event["action_key"], event["action_fingerprint"], json.dumps(event["details"], sort_keys=True, separators=(",", ":"))),  # Bind only cents-safe columns and exact residue metadata.
                    )
                else:
                    # Convert the relational row to the complete provider-neutral replay shape.
                    existing = {**_ledger_from_row(existing_row), "action_scope": existing_row["action_scope"], "action_key": existing_row["action_key"], "action_fingerprint": existing_row["action_fingerprint"]}
                    # Reject any deterministic-identity collision before changing the wallet.
                    _validate_wallet_normalization_replay(existing, event)
                # Publish the exact cent value on the already locked wallet row.
                cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (normalized, utc_now(), player_id))
            # Commit all audit rows and wallet changes atomically.
            connection.commit()
            # Return bounded completion evidence after the durable commit.
            return {"provider": self.name, "checked": len(rows), "residue_count": len(residues), "normalized_count": len(residues), "clean": True, "applied": True}
        # Roll back every malformed row, collision, or provider failure.
        except Exception:
            # Preserve the complete pre-call relational state.
            connection.rollback()
            # Re-raise the original bounded error.
            raise
        # Always release the provider connection after commit or rollback.
        finally:
            # Return or discard the connection through the existing pool boundary.
            connection.close()

    # Insert one player through the deterministic provider-owned identity boundary.
    def insert_player(self, player: dict) -> dict:
        # Reject player insertion attempted from inside a planner.
        self._reject_planner_mutation()
        # Reuse the primary-key transaction shared with invited-account provisioning.
        return self.ensure_player(player)

    # Insert every missing bootstrap row without replacing durable rows. (STORAGE-012, issue #431)
    def bootstrap_players(self, state: dict) -> None:
        # Reject bootstrap mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure schema exists before inserting player rows.
        self.ensure_ready()
        # Open a connection for the bounded append operation.
        connection = self.connect()
        # Start protected transaction logic so failures roll back and the connection always closes.
        try:
            # Start one explicit transaction across all supplied player inserts.
            connection.start_transaction()
            # Open a cursor for bounded insert statements.
            cursor = connection.cursor()
            # Insert each supplied player without deleting or overwriting any existing row.
            for player in state.get("players", []):
                # Insert one normalized player only when its durable identifier is absent.
                cursor.execute(
                    "INSERT IGNORE INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Keep existing wallet and lifecycle state unchanged on a repeated seed.
                    (player["player_id"], player["display_name"], player.get("type", "human"), _quantized_money_decimal(player.get("balance", 0)), player.get("created_at", utc_now()), player.get("updated_at", utc_now()), player.get("status", "active")),  # Bind only cents-normalized candidate fields.
                )
            # Commit all missing-player inserts as one unit.
            connection.commit()
        # Roll back every partial insert when the driver reports a failure.
        except Exception:
            # Restore the complete pre-call player table state.
            connection.rollback()
            # Preserve the original provider error for the standard API envelope.
            raise
        # Always close the connection after saving players.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Update one player in a MySQL transaction.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure schema exists before updating players.
        self.ensure_ready()
        # Open a connection for the row-locking transaction.
        connection = self.connect()
        # Start protected transaction logic so the connection is always closed.
        try:
            # Start an explicit transaction for row-level locking.
            connection.start_transaction()
            # Open a dictionary cursor for the selected player row.
            cursor = connection.cursor(dictionary=True)
            # Lock the player row until the update commits.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the selected player row.
            row = cursor.fetchone()
            # Raise a consistent not-found error when the row does not exist.
            if row is None:
                # Roll back before surfacing the not-found error.
                connection.rollback()
                # Raise the same player lookup error shape used by players.get_player.
                raise NotFoundError(f"Player {player_id} was not found")
            # Convert the row into the public player shape for the updater.
            player = self._player_from_row(row)
            # Let the caller mutate the public player shape.
            updater(player)
            # Quantize the updated wallet through the provider-neutral cents boundary.
            player["balance"] = _quantized_money(player.get("balance", 0))
            # Stamp the player update time.
            player["updated_at"] = utc_now()
            # Persist the updated fields.
            cursor.execute(
                "UPDATE casino_players SET display_name = %s, player_type = %s, balance = %s, updated_at = %s, status = %s WHERE player_id = %s",  # Update one locked player row.
                (player["display_name"], player.get("type", "human"), player["balance"], player["updated_at"], player.get("status", "active"), player_id),  # Bind updated player fields.
            )
            # Commit the row update.
            connection.commit()
            # Return the committed player row.
            return player
        # Roll back unexpected failures before re-raising them.
        except Exception:
            # Roll back any open transaction.
            connection.rollback()
            # Re-raise the original exception.
            raise
        # Always close the connection after the update attempt.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Create one deterministic player under a MySQL primary-key transaction.
    def ensure_player(self, player: dict) -> dict:
        # Reject deterministic player creation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure the relational schema exists before provisioning.
        self.ensure_ready()
        # Open one connection for the insert-or-read transaction.
        connection = self.connect()
        # Protect rollback and cleanup for every database outcome.
        try:
            # Start an explicit transaction so duplicate creators serialize on the primary key.
            connection.start_transaction()
            # Open a dictionary cursor for the committed row projection.
            cursor = connection.cursor(dictionary=True)
            # Insert the deterministic player once without overwriting any existing wallet state.
            cursor.execute(
                "INSERT IGNORE INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Preserve existing rows on an idempotent replay.
                (player["player_id"], player["display_name"], player.get("type", "human"), _quantized_money_decimal(player.get("balance", 0)), player["created_at"], player["updated_at"], player.get("status", "active")),  # Bind only cents-normalized deterministic fields.
            )
            # Lock and read the resulting row before validating compatibility.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s FOR UPDATE", (player["player_id"],))
            # Resolve the inserted or pre-existing row.
            row = cursor.fetchone()
            # Reject an impossible missing row without committing partial state.
            if row is None:
                # Raise a stable provisioning conflict for the recoverable caller.
                raise ConflictError("Player provisioning did not produce durable state")
            # Convert the relational row into the public storage shape.
            result = self._player_from_row(row)
            # Reject a primary-key collision with incompatible player ownership semantics.
            if result.get("type") != player.get("type"):
                # Keep the original row unchanged and fail closed.
                raise ConflictError("Player provisioning identity conflicts with existing state")
            # Commit either the first insert or the compatible no-op replay.
            connection.commit()
            # Return the committed player row.
            return result
        # Roll back every failed provisioning attempt.
        except Exception:
            # Discard any partial insert or lock state.
            connection.rollback()
            # Preserve the original bounded application error.
            raise
        # Always release the provider connection.
        finally:
            # Close the database connection after commit or rollback.
            connection.close()

    # Execute a ledger transaction and player balance update atomically in MySQL.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Reject wallet and ledger mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = _quantized_money(amount)
        # Reject zero-value ledger rows before touching player state.
        if amount == 0:
            # Raise a validation error consistent with the previous ledger module.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Ensure schema exists before writing ledger rows.
        self.ensure_ready()
        # Open a connection for the row-locking transaction.
        connection = self.connect()
        # Start protected transaction logic so the connection is always closed.
        try:
            # Start an explicit transaction so balance and ledger insert commit together.
            connection.start_transaction()
            # Open a dictionary cursor for row access.
            cursor = connection.cursor(dictionary=True)
            # Lock the player row to serialize concurrent wallet mutations.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the locked player row.
            row = cursor.fetchone()
            # Raise a consistent not-found error when the player does not exist.
            if row is None:
                # Roll back before raising the lookup error.
                connection.rollback()
                # Raise the same player lookup error shape used by players.get_player.
                raise NotFoundError(f"Player {player_id} was not found")
            # Capture the balance before the proposed mutation.
            before = _money(row["balance"])
            # Compute the balance after the proposed mutation.
            after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
            # Reject transactions that would overdraw the fake-money wallet.
            if after < 0:
                # Roll back before surfacing insufficient funds.
                connection.rollback()
                # Raise the existing insufficient-funds error with ledger details.
                raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
            # Build the ledger event before persistence so the response matches the row.
            event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, details)
            # Update the locked player balance first within the open transaction.
            cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (after, utc_now(), player_id))
            # Insert the ledger row in the same transaction as the balance update.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Insert the atomic ledger event row.
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], json.dumps(event["details"], sort_keys=True)),  # Bind ledger event fields.
            )
            # Commit both balance and ledger mutations together.
            connection.commit()
            # Return the committed ledger event to the caller.
            return event
        # Roll back unexpected failures before re-raising them.
        except Exception:
            # Roll back any open transaction.
            connection.rollback()
            # Re-raise the original exception.
            raise
        # Always close the connection after the transaction attempt.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Execute or replay one storage-enforced MySQL ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
        # Reject exactly-once ledger mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = _quantized_money(amount)
        # Reject zero-value ledger rows before opening a database transaction.
        if amount == 0:
            # Raise the standard ledger validation error.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Normalize the indexed action key before using it in SQL.
        action_key = _normalize_action_key(action_key)
        # Derive the indexed game-or-core namespace.
        scope = _action_scope(game)
        # Derive the semantic digest used for replay conflict checks.
        fingerprint = _action_fingerprint(amount, transaction_type, game, round_id, details)
        # Add storage-owned metadata to the committed ledger details.
        committed_details = _action_details(details, action_key, fingerprint)
        # Ensure the migrated schema and unique index exist before writing.
        self.ensure_ready()
        # Open a connection for the row-locking action transaction.
        connection = self.connect()
        # Start protected transaction logic so rollback and close always run.
        try:
            # Start one transaction containing identity lookup, balance update, and ledger insertion.
            connection.start_transaction()
            # Open a dictionary cursor for player and ledger row mapping.
            cursor = connection.cursor(dictionary=True)
            # Lock the player row so independent processes serialize all actions for this wallet.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the locked player row.
            player_row = cursor.fetchone()
            # Reject unknown players before identity lookup or mutation.
            if player_row is None:
                # Roll back the empty transaction before raising the lookup error.
                connection.rollback()
                # Raise the standard player lookup error.
                raise NotFoundError(f"Player {player_id} was not found")
            # Read a prior committed event for the same storage action identity.
            cursor.execute(
                "SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s AND action_scope = %s AND action_key = %s",  # Query the unique storage identity inside the wallet transaction.
                (player_id, scope, action_key),  # Bind the player, namespace, and caller action key.
            )
            # Fetch the prior row when this call is a replay.
            existing_row = cursor.fetchone()
            # Return the original committed event without another wallet mutation.
            if existing_row is not None:
                # Convert the database row into the public ledger event shape.
                existing_event = _ledger_from_row(existing_row)
                # Reject changed semantic reuse before returning the prior result.
                _validate_action_replay(existing_event, fingerprint, action_key)
                # End the read-only replay transaction and release the player lock.
                connection.commit()
                # Return the immutable original event with an explicit replay marker.
                return existing_event, True
            # Capture the wallet balance before the new action.
            before = _money(player_row["balance"])
            # Compute the wallet balance after the new action.
            after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
            # Reject actions that would overdraw the fake-money wallet.
            if after < 0:
                # Roll back before surfacing insufficient funds.
                connection.rollback()
                # Raise the standard insufficient-funds error with transaction context.
                raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
            # Build the immutable event returned by all later replays.
            event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, committed_details)
            # Update the locked wallet balance inside the action transaction.
            cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (after, utc_now(), player_id))
            # Insert the action identity, semantic digest, and ledger row in the same transaction.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Persist the unique money action with its wallet transition.
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], scope, action_key, fingerprint, json.dumps(event["details"], sort_keys=True)),  # Bind action and ledger fields atomically.
            )
            # Commit identity reservation, balance mutation, and append-only event together.
            connection.commit()
            # Return the newly committed event with a non-replay marker.
            return event, False
        # Roll back any unexpected provider or database failure.
        except Exception:
            # Roll back all uncommitted identity, wallet, and ledger changes.
            connection.rollback()
            # Re-raise the original exception for standard API mapping.
            raise
        # Always close the connection after the action attempt.
        finally:
            # Close this operation's MySQL connection.
            connection.close()

    # Find one committed MySQL ledger action through its unique identity index. (LEDGER-033)
    def find_ledger_action(self, player_id: str, game: str | None, action_key: str) -> dict | None:
        # Normalize the indexed caller-owned key before opening a connection.
        action_key = _normalize_action_key(action_key)
        # Normalize the game-or-core scope exactly as the write path does.
        scope = _action_scope(game)
        # Ensure the migrated unique action index exists before querying it.
        self.ensure_ready()
        # Open one read-only provider connection for the point lookup.
        connection = self.connect()
        # Protect cleanup so every result and failure closes the provider connection.
        try:
            # Open a dictionary cursor for public ledger-event mapping.
            cursor = connection.cursor(dictionary=True)
            # Query the existing unique identity index without locking the player row.
            cursor.execute(
                "SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s AND action_scope = %s AND action_key = %s",  # Use the same indexed predicate as transact_ledger_once.
                (player_id, scope, action_key),  # Bind the canonical wallet, scope, and action key.
            )
            # Read at most the one row guaranteed by the unique index.
            row = cursor.fetchone()
            # Return no event for an unused action identity.
            if row is None:
                # Preserve the optional-result provider contract.
                return None
            # Convert the indexed row into the established public ledger shape.
            return _ledger_from_row(row)
        # Always close the point-lookup connection.
        finally:
            # Release the provider connection without adding a write-path connection.
            connection.close()

    # Read recent ledger events from MySQL.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Ensure schema exists before reading ledger rows.
        self.ensure_ready()
        # Open a connection for the ledger query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a dictionary cursor for row mapping.
            cursor = connection.cursor(dictionary=True)
            # Build the filtered or unfiltered query.
            if player_id is None:
                # Read the newest ledger rows without a player filter.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger ORDER BY sequence_id DESC LIMIT %s", (int(limit),))
            # Handle the player-specific ledger path.
            else:
                # Read the newest ledger rows for the requested player.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s ORDER BY sequence_id DESC LIMIT %s", (player_id, int(limit)))
            # Convert reversed newest-first rows back to chronological order.
            rows = list(reversed(cursor.fetchall()))
            # Return JSON-compatible ledger event dictionaries.
            return [_ledger_from_row(row) for row in rows]
        # Always close the connection after the ledger query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Aggregate player-facing game economics in SQL without materializing the full window. (ADMIN-030)
    def ledger_economics(self, window: int, game: str | None = None, recent: int = 0) -> dict:
        # Ensure the compatible schema exists before querying the ledger.
        self.ensure_ready()
        # Borrow one connection so detail queries share one repeatable-read snapshot.
        connection = self.connect()
        # Protect lease cleanup across summary, type, and recent projections.
        try:
            # Open a dictionary cursor for named aggregate columns.
            cursor = connection.cursor(dictionary=True)
            # Build one fixed exclusion predicate for infrastructure transaction families.
            exclusions = " AND ".join("BINARY transaction_type NOT LIKE BINARY %s" for _fragment in ECONOMICS_EXCLUDED_TRANSACTION_FRAGMENTS)
            # Bind wildcard fragments without interpolating caller input into SQL.
            exclusion_values = tuple(f"%{fragment}%" for fragment in ECONOMICS_EXCLUDED_TRANSACTION_FRAGMENTS)
            # Restrict aggregation to the exact selected game only for drill-down requests.
            game_clause = " AND BINARY game = BINARY %s" if game is not None else ""
            # Bind the window, fixed exclusions, and optional game in statement order.
            base_values = (int(window), *exclusion_values, *((game,) if game is not None else ()))
            # Aggregate signed totals after selecting the newest raw ledger window.
            cursor.execute(
                f"SELECT MIN(game) AS game, SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS wagered, SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS returned, COUNT(*) AS event_count FROM (SELECT sequence_id, game, transaction_type, amount FROM casino_ledger ORDER BY sequence_id DESC LIMIT %s) AS bounded_ledger WHERE game IS NOT NULL AND game <> '' AND {exclusions}{game_clause} GROUP BY BINARY game ORDER BY BINARY game",
                base_values,
            )
            # Materialize only low-cardinality per-game aggregate rows.
            aggregate_rows = cursor.fetchall()
            # Convert database decimals into the provider-neutral raw aggregate shape.
            games = [{"game": row["game"], "wagered": float(row["wagered"] or 0), "returned": float(row["returned"] or 0), "events": int(row["event_count"])} for row in aggregate_rows]
            # Return summary-only evidence after the single aggregate query.
            if game is None:
                # Preserve the shared internal result keys for Admin rendering.
                return {"games": games, "by_transaction_type": [], "recent": []}
            # Aggregate signed totals and counts per transaction type inside the same bounded window.
            cursor.execute(
                f"SELECT MIN(transaction_type) AS transaction_type, COUNT(*) AS event_count, SUM(amount) AS total FROM (SELECT sequence_id, game, transaction_type, amount FROM casino_ledger ORDER BY sequence_id DESC LIMIT %s) AS bounded_ledger WHERE game IS NOT NULL AND game <> '' AND {exclusions}{game_clause} GROUP BY BINARY transaction_type ORDER BY BINARY transaction_type",
                base_values,
            )
            # Convert database values into the established detail bucket shape.
            by_type = [{"transaction_type": str(row["transaction_type"]), "count": int(row["event_count"]), "total": float(row["total"] or 0)} for row in cursor.fetchall()]
            # Select the historical oldest matching evidence from within the same newest-first raw window.
            cursor.execute(
                f"SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM (SELECT sequence_id, ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger ORDER BY sequence_id DESC LIMIT %s) AS bounded_ledger WHERE game IS NOT NULL AND game <> '' AND {exclusions}{game_clause} ORDER BY sequence_id ASC LIMIT %s",
                (*base_values, int(recent)),
            )
            # Convert bounded database rows into the frozen public ledger event shape.
            recent_rows = [_ledger_from_row(row) for row in cursor.fetchall()]
            # Return all drill-down dimensions from one consistent provider snapshot.
            return {"games": games, "by_transaction_type": by_type, "recent": recent_rows}
        # Always release the economics connection.
        finally:
            # Return the read-only lease to the provider pool.
            connection.close()

    # Append one history event to MySQL.
    def append_history(self, event: dict) -> None:
        # Reject history mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure schema exists before writing history.
        self.ensure_ready()
        # Open a connection for the insert.
        connection = self.connect()
        # Start protected insert logic so the connection is always closed.
        try:
            # Open a cursor for the insert statement.
            cursor = connection.cursor()
            # Insert one normalized history row.
            cursor.execute(
                "INSERT INTO casino_history (timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Insert one history event row.
                tuple(event[field] for field in HISTORY_FIELDS),  # Bind history fields in schema order.
            )
            # Commit the history insert.
            connection.commit()
        # Always close the connection after the insert.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Read recent history rows from MySQL.
    def recent_history(self, limit: int = 100, game: str | None = None) -> list[dict]:
        # Ensure schema exists before reading history.
        self.ensure_ready()
        # Open a connection for the history query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a dictionary cursor for row mapping.
            cursor = connection.cursor(dictionary=True)
            # Build the filtered or unfiltered query.
            if game:
                # Read the newest history rows for one game.
                cursor.execute("SELECT timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version FROM casino_history WHERE game = %s ORDER BY sequence_id DESC LIMIT %s", (game, int(limit)))
            # Handle the unfiltered history path.
            else:
                # Read the newest history rows across all games.
                cursor.execute("SELECT timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version FROM casino_history ORDER BY sequence_id DESC LIMIT %s", (int(limit),))
            # Convert reversed newest-first rows back to chronological order.
            rows = list(reversed(cursor.fetchall()))
            # Return CSV-compatible dictionaries for existing API responses.
            return [_history_from_row(row) for row in rows]
        # Always close the connection after the history query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Read a named JSON document from MySQL.
    def read_document(self, key: str, default: Any) -> Any:
        # Ensure schema exists before reading the document.
        self.ensure_ready()
        # Open a connection for the document query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a dictionary cursor for the selected document.
            cursor = connection.cursor(dictionary=True)
            # Read the document payload by key.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s", (key,))
            # Fetch the optional document row.
            row = cursor.fetchone()
            # Return defaults when the document does not exist yet.
            if row is None:
                # Evaluate default factories lazily to preserve JSON helper semantics.
                return default() if callable(default) else default
            # Return the decoded JSON document.
            return _decode_json(row["payload_json"])
        # Always close the connection after the document query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Report exact database document existence without decoding or creating a row. (STORAGE-018)
    def document_exists(self, key: str) -> bool:
        # Ensure schema compatibility before inspecting the canonical document table.
        self.ensure_ready()
        # Open one provider connection for the point lookup.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a compact ordinary cursor for one existence bit.
            cursor = connection.cursor()
            # Select one constant by the canonical document primary key.
            cursor.execute("SELECT 1 FROM casino_documents WHERE document_key = %s", (key,))
            # Return true only when the exact canonical row exists.
            return cursor.fetchone() is not None
        # Always close the provider connection after the point lookup.
        finally:
            # Release the connection and any implicit read transaction.
            connection.close()

    # Read one MySQL security document through the existing strict decoder and shape boundary.
    def read_document_strict(self, key: str, default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Start protected decoding so malformed provider JSON uses the fixed recovery boundary.
        try:
            # Reuse the existing query, missing-row default, and strict MySQL JSON decoder.
            value = self.read_document(key, default)
        # Collapse only JSON text/type/limit failures without changing connection behavior.
        except (UnicodeError, ValueError, TypeError, RecursionError):
            # Preserve the stored row and return one value-free operator-recovery failure.
            raise RuntimeError("Stored document requires operator recovery") from None
        # Apply the same provider-neutral caller-owned shape contract.
        return _validated_strict_document(value, validator)

    # Write a named JSON document to MySQL.
    def write_document(self, key: str, data: Any) -> None:
        # Reject document mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure schema exists before writing the document.
        self.ensure_ready()
        # Open a connection for the upsert.
        connection = self.connect()
        # Start protected upsert logic so the connection is always closed.
        try:
            # Open a cursor for the upsert statement.
            cursor = connection.cursor()
            # Upsert the JSON document by key.
            cursor.execute(
                "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE payload_json = VALUES(payload_json), updated_at = VALUES(updated_at)",  # Upsert one JSON document.
                (key, json.dumps(data, sort_keys=True), utc_now()),  # Bind document key, payload, and timestamp.
            )
            # Commit the document upsert.
            connection.commit()
        # Always close the connection after the upsert.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Mutate one document in a single row-locking MySQL transaction. (OTT-001)
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Reject document read-modify-write attempted from inside a planner.
        self._reject_planner_mutation()
        # Verify the exact schema before opening a mutation transaction.
        self.ensure_ready()
        # Evaluate the default once so retries and the persisted seed share one canonical value.
        initial = default() if callable(default) else default
        # Open an independent connection so separate processes contend on the database row lock.
        connection = self.connect()
        # Start protected transaction logic so rollback and close are guaranteed.
        try:
            # Start an explicit transaction before creating or locking the canonical document row.
            connection.start_transaction()
            # Open a dictionary cursor so the stored JSON payload is accessed by its stable column name.
            cursor = connection.cursor(dictionary=True)
            # Materialize an absent row inside this transaction; concurrent inserts serialize on the unique key.
            cursor.execute(
                "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE document_key = VALUES(document_key)",  # Create the lockable row without overwriting existing state.
                (key, json.dumps(initial, sort_keys=True), utc_now()),  # Bind only the document key, non-secret initial payload, and timestamp.
            )
            # Lock the canonical row until the complete caller mutation commits.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (key,))
            # Read the row that the preceding upsert guarantees exists.
            row = cursor.fetchone()
            # Start protected strict decoding for an optional security-document validator.
            try:
                # Decode a detached current document for the caller-owned mutation.
                current = _decode_json(row["payload_json"])
            # Collapse malformed MySQL JSON only when strict security validation was requested.
            except (UnicodeError, ValueError, TypeError, RecursionError):
                # Preserve ordinary update exceptions for callers without the strict seam.
                if validator is None:
                    # Re-raise the original decoder failure unchanged.
                    raise
                # Abort this row transaction with one fixed operator-recovery failure.
                raise RuntimeError("Stored document requires operator recovery") from None
            # Validate the security document while the database row remains locked.
            current = _validated_strict_document(current, validator)
            # Apply the mutation while the row remains locked against every other process.
            updated = mutator(current)
            # Persist the complete updated document before releasing the row lock.
            cursor.execute(
                "UPDATE casino_documents SET payload_json = %s, updated_at = %s WHERE document_key = %s",  # Replace exactly the locked document row.
                (json.dumps(updated, sort_keys=True), utc_now(), key),  # Bind the canonical payload, timestamp, and locked key.
            )
            # Commit the mutation atomically so one-time consumers observe exactly one winner.
            connection.commit()
            # Return only after the updated document is durable.
            return updated
        # Roll back mutation or caller validation failures without publishing partial state.
        except Exception:
            # Release every transactional change made on this connection.
            connection.rollback()
            # Preserve the original exception and traceback for the caller.
            raise
        # Always close the transaction connection after success or failure.
        finally:
            # Release the database connection and any remaining server resources.
            connection.close()
