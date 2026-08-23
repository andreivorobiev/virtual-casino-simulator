# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Complete ordinary PostgreSQL storage provider ownership."""

# Import annotations so provider method hints can refer to runtime-only connector shapes.
from __future__ import annotations

# Import context-manager support for reset, visibility, and operation transactions.
from contextlib import contextmanager
# Import exact decimal arithmetic for wallet and ledger persistence.
from decimal import Decimal
# Import deterministic hashing for target-scoped advisory-lock identities.
import hashlib
# Import canonical JSON encoding for PostgreSQL JSONB parameters.
import json
# Import thread primitives for readiness, planner, and reset ownership.
import threading
# Import generic callables and connector-owned values without importing psycopg eagerly.
from typing import Any, Callable

# Import the current document schema version projected by relational player reads.
from casino.config import SCHEMA_VERSION
# Import the canonical timestamp helper used by provider rows and documents.
from casino.core.clock import utc_now
# Import the provider-neutral exactly-once action executor contract.
from casino.core.game_action import GameActionExecutor
# Import the read-only PostgreSQL runtime catalog verifier owned by the migration lane.
from casino.core.postgres_migrations import MigrationError, verify_runtime_compatibility
# Import the bounded connector-neutral PostgreSQL pool and its fixed error categories.
from casino.core.postgres_pool import PostgresConnectionPool, PostgresPoolClosedError, PostgresPoolConfig, PostgresPoolConnectionError, PostgresPoolExhaustedError
# Import the provider-neutral storage contract, configuration, and shared row helpers.
from casino.core.storage.base import HISTORY_FIELDS, PostgresConfig, StorageProvider, _action_details, _action_fingerprint, _action_scope, _history_from_row, _ledger_event, _ledger_from_row, _money, _money_decimal, _normalize_action_key, _quantized_money, _quantized_money_decimal, _validate_action_replay, _validate_wallet_normalization_replay, _validated_players_document, _validated_strict_document, _wallet_normalization_event
# Import the shared reset-epoch ceiling used by the future game-action lane.
from casino.core.storage.reset import _GAME_ACTION_MAX_EPOCH
# Import first-class PostgreSQL exactly-once game-action ownership.
from casino.core.storage.game_actions_postgres import PostgresGameActionMixin
# Import first-class PostgreSQL session ownership from the disjoint session lane.
from casino.core.storage.sessions_postgres import PostgresSessionMixin
# Import stable application errors that must survive database translation unchanged.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError

# Track active PostgreSQL planners separately from reset and pool ownership.
_POSTGRES_PLANNER_LOCAL = threading.local()
# Serialize process-local reset target registration across equivalent provider instances.
_POSTGRES_RESET_REGISTRY_LOCK = threading.RLock()
# Track targets whose retained session currently owns reset or visibility lifecycle state.
_POSTGRES_RESET_TARGETS: set[tuple[str, int, str]] = set()


# Run connector cleanup statements without leaving psycopg in an implicit transaction.
class _PsycopgConnectionAdapter:
    # Store the selected psycopg module and its exact idle status value.
    def __init__(self, driver: Any) -> None:
        # Retain the connector module only inside the explicitly selected provider.
        self._driver = driver
        # Bind comparisons to psycopg's public libpq transaction-status enum.
        self._idle_status = driver.pq.TransactionStatus.IDLE

    # Read the current libpq transaction status without reconnecting.
    def _status(self, connection: Any) -> Any:
        # Return the same physical session's connector-owned status value.
        return connection.info.transaction_status

    # Execute one statement in temporary autocommit and restore the reviewed baseline.
    def _autocommit_statement(self, connection: Any, operation: str, *, fetch: bool = False) -> Any:
        # Refuse session commands while an earlier transaction remains active.
        if self._status(connection) != self._idle_status:
            # Force the pool to discard an uncertain non-idle session.
            raise RuntimeError("PostgreSQL session is not idle.")
        # Preserve the exact connector autocommit setting for unconditional restoration.
        prior_autocommit = connection.autocommit
        # Track the operation result without retaining connector diagnostics.
        result = None
        try:
            # Enter autocommit before DISCARD ALL or the wire check can begin a transaction.
            connection.autocommit = True
            # Open one connector cursor on the exact physical session.
            cursor = connection.cursor()
            try:
                # Execute the fixed wire-check statement for its closed operation enum.
                if operation == "wire_check":
                    # Verify this same physical PostgreSQL session without reconnecting.
                    cursor.execute("SELECT 1 AS wire_ok")
                # Execute the fixed advisory-lock cleanup statement.
                elif operation == "unlock_all":
                    # Release every advisory lock retained by this exact session.
                    cursor.execute("SELECT pg_advisory_unlock_all()")
                # Execute the fixed PostgreSQL session reset command.
                elif operation == "discard_all":
                    # Restore all other session-local state to server defaults.
                    cursor.execute("DISCARD ALL")
                else:
                    # Refuse every unreviewed adapter operation before connector access.
                    raise ValueError("Unsupported PostgreSQL adapter operation.")
                # Read one bounded result only for the wire-check statement.
                if fetch:
                    # Retain the connector-decoded one-row proof.
                    result = cursor.fetchone()
            finally:
                # Close the adapter-owned cursor before restoring connection state.
                cursor.close()
        finally:
            # Restore the exact pre-call autocommit policy even when execution fails.
            connection.autocommit = prior_autocommit
        # Require the complete operation and restoration path to remain transaction-idle.
        if self._status(connection) != self._idle_status:
            # Prevent an implicitly opened transaction from returning to the pool.
            raise RuntimeError("PostgreSQL session cleanup did not remain idle.")
        # Return only the optional one-row wire-check result.
        return result

    # Check the exact physical session without reconnecting or leaving INTRANS state.
    def is_healthy(self, connection: Any) -> bool:
        # Reject every non-idle or unknown status before issuing another command.
        if self._status(connection) != self._idle_status:
            # Report an unhealthy reusable-session candidate.
            return False
        # Execute one constant autocommit wire check on this same physical object.
        row = self._autocommit_statement(connection, "wire_check", fetch=True)
        # Require the dict-row factory's exact bounded result and an idle final status.
        return row == {"wire_ok": 1} and self._status(connection) == self._idle_status

    # Report whether psycopg exposes any non-idle transaction state.
    def in_transaction(self, connection: Any) -> bool:
        # Treat ACTIVE, INTRANS, INERROR, and UNKNOWN as requiring rollback or discard.
        return self._status(connection) != self._idle_status

    # Roll back one unfinished transaction and require exact idle recovery.
    def rollback(self, connection: Any) -> None:
        # Delegate transaction cleanup to psycopg on the same physical connection.
        connection.rollback()
        # Reject a connector that did not return to the idle state.
        if self._status(connection) != self._idle_status:
            # Force the pool to discard the uncertain session.
            raise RuntimeError("PostgreSQL rollback did not restore an idle session.")

    # Clear advisory locks and session-local state without opening a transaction.
    def reset(self, connection: Any) -> None:
        # Release any retained session advisory lock before general session reset.
        self._autocommit_statement(connection, "unlock_all")
        # Restore PostgreSQL session settings, prepared statements, and temporary state.
        self._autocommit_statement(connection, "discard_all")


# Keep reset-owned pool leases available to synchronous capacity-one bootstrap calls.
class _BorrowedPostgresConnection:
    # Retain one reset- or visibility-owned lease without transferring close authority.
    def __init__(self, connection: Any) -> None:
        # Store the caller-owned lease for transparent DB-API delegation.
        self._connection = connection
        # Track idempotent nested-operation cleanup.
        self._closed = False

    # Delegate every connector attribute except the explicit no-close boundary.
    def __getattr__(self, name: str) -> Any:
        # Preserve cursor, commit, rollback, and transaction-state behavior.
        return getattr(self._connection, name)

    # End nested operation residue without returning the outer lease to the pool.
    def close(self) -> None:
        # Preserve idempotent DB-API close behavior for nested finally blocks.
        if self._closed:
            # Avoid duplicate cleanup after the nested operation already ended.
            return
        # Roll back only implicit read residue left after a nested operation.
        self._connection.rollback()
        # Mark this facade closed after the retained physical session is idle.
        self._closed = True


# Implement the complete ordinary PostgreSQL provider across sessions and game actions.
class PostgresStorageProvider(PostgresSessionMixin, PostgresGameActionMixin, StorageProvider, GameActionExecutor):
    # Store the provider name used by diagnostics and parity tests.
    name = "postgres"

    # Initialize the provider lazily from explicit or environment-backed configuration.
    def __init__(self, config: PostgresConfig | None = None, pool_config: PostgresPoolConfig | None = None) -> None:
        # Resolve the optional connector only after explicit PostgreSQL selection.
        self._driver, self._dict_row = self._connector()
        # Store validated connection configuration without opening a physical session.
        self.config = config or PostgresConfig.from_env()
        # Build one lazy bounded process-local pool around the provider adapter.
        self._pool = PostgresConnectionPool(self._open_physical_connection, _PsycopgConnectionAdapter(self._driver), pool_config)
        # Track whether this process completed exact read-only runtime compatibility verification.
        self._ready = False
        # Cache only the sanitized clean migration version for schema-aware session ownership.
        self._schema_version: int | None = None
        # Serialize first-use compatibility verification across concurrent request threads.
        self._ready_lock = threading.RLock()
        # Track same-thread reset and visibility lease borrowing.
        self._boundary_local = threading.local()

    # Import psycopg and its dict-row factory only inside the selected provider module.
    def _connector(self) -> tuple[Any, Any]:
        # Import the optional PostgreSQL connector at the explicit provider boundary.
        import psycopg
        # Import dict-row construction so every provider cursor has mapping semantics.
        from psycopg.rows import dict_row
        # Return the connector module and row factory without creating a connection.
        return psycopg, dict_row

    # Open one physical PostgreSQL connection with bounded timeout and reviewed defaults.
    def _open_physical_connection(self, connect_timeout_seconds: int) -> Any:
        # Add only connector policy to the immutable credential keyword mapping.
        options = {**self.config.kwargs(), "connect_timeout": connect_timeout_seconds, "autocommit": False, "row_factory": self._dict_row, "prepare_threshold": None, "options": "-c default_transaction_isolation=read\\ committed"}
        # Return one new READ COMMITTED physical session to the bounded pool.
        return self._driver.connect(**options)

    # Lease one request-scoped PostgreSQL connection from the bounded pool.
    def connect(self, **overrides: Any) -> Any:
        # Reject storage access from inside a future game-action planner.
        self._reject_planner_mutation()
        # Reject credential, target, row-factory, or session-policy overrides.
        if set(overrides) - {"connect_timeout_seconds"}:
            # Publish one fixed value-free provider validation error.
            raise ValueError("Unsupported PostgreSQL connection override.")
        # Reuse the retained reset or visibility lease for capacity-one nested calls.
        borrowed = getattr(self._boundary_local, "connection", None)
        # Return a no-close facade only while this thread owns the outer session.
        if borrowed is not None:
            # Prevent nested helpers from returning the sole lease early.
            return _BorrowedPostgresConnection(borrowed)
        # Preserve the bounded explicit connector-timeout test seam.
        connect_timeout_seconds = overrides.get("connect_timeout_seconds")
        # Acquire a request-scoped lease that the pool sanitizes on close.
        return self._pool.acquire(connect_timeout_seconds=connect_timeout_seconds)

    # Return secret-free pool policy, gauges, counters, and wait buckets.
    def pool_snapshot(self) -> dict:
        # Delegate the immutable evidence projection to the connector-neutral pool.
        return self._pool.snapshot()

    # Close idle physical sessions and reject future checkout.
    def close_pool(self) -> None:
        # Refuse lifecycle mutation from inside a supposedly pure planner.
        self._reject_planner_mutation()
        # Delegate terminal shutdown to the bounded pool.
        self._pool.close_all()

    # Return the configured target identity without credentials.
    def _planner_key(self) -> tuple[str, int, str]:
        # Normalize host case while preserving the configured port and database.
        return (self.config.host.lower(), self.config.port, self.config.database)

    # Return whether this thread is planning through this PostgreSQL target.
    def _planner_is_active(self) -> bool:
        # Read the thread-local target set without sharing a mutable default.
        providers = getattr(_POSTGRES_PLANNER_LOCAL, "providers", set())
        # Bind purity across equivalent provider instances for the same target.
        return self._planner_key() in providers

    # Reject provider access attempted from inside a future action planner.
    def _reject_planner_mutation(self) -> None:
        # Fail before opening a connection or changing lifecycle state.
        if self._planner_is_active():
            # Reuse the provider-neutral fixed purity error.
            raise ValidationError("Game action planner must be side-effect free")

    # Mark one synchronous future planner call as unable to re-enter this target mutably.
    @contextmanager
    def _planner_boundary(self):
        # Copy active target ownership so nesting stays thread-local.
        providers = set(getattr(_POSTGRES_PLANNER_LOCAL, "providers", set()))
        # Resolve this provider's target identity.
        planner_key = self._planner_key()
        # Reject recursive planning through the same provider target.
        if planner_key in providers:
            # Preserve the fixed provider-neutral validation boundary.
            raise ValidationError("Game action planner must be side-effect free")
        # Publish this target for the synchronous callback lifetime.
        providers.add(planner_key)
        # Store only the thread-local active set.
        _POSTGRES_PLANNER_LOCAL.providers = providers
        try:
            # Transfer control to the future caller-owned planner.
            yield
        finally:
            # Remove this target even when the planner raises.
            providers.discard(planner_key)
            # Retain independently active outer targets.
            _POSTGRES_PLANNER_LOCAL.providers = providers

    # Decide whether one failure belongs to psycopg or the bounded pool.
    def _is_database_error(self, error: BaseException) -> bool:
        # Match only connector and pool-owned categories, never arbitrary callbacks.
        return isinstance(error, (self._driver.Error, PostgresPoolClosedError, PostgresPoolConnectionError, PostgresPoolExhaustedError))

    # Classify only the finite PostgreSQL lock outcomes a game-action resolver may report.
    def _is_game_action_lock_contention(self, error: BaseException) -> bool:
        # Bind the connector-neutral hook to psycopg's public lock and deadlock categories.
        return isinstance(error, (self._driver.errors.LockNotAvailable, self._driver.errors.DeadlockDetected))

    # Translate one native database failure into a fixed application conflict.
    def _raise_database_error(self, error: BaseException) -> None:
        # Map database constraint conflicts to one fixed current-state category.
        if isinstance(error, self._driver.IntegrityError):
            # Omit SQL, target, constraint, value, and connector text.
            raise ConflictError("PostgreSQL storage conflicts with current state") from None
        # Translate every other connector or pool failure to one fixed availability boundary.
        if self._is_database_error(error):
            # Omit host, database, role, SQL, credentials, and native diagnostics.
            raise ConflictError("PostgreSQL storage is unavailable") from None
        # Return control when the caller owns this non-database failure.
        return

    # Roll back transaction residue without replacing an active caller failure.
    @staticmethod
    def _rollback_quietly(connection: Any) -> None:
        # Start protected cleanup because an uncertain connection will be discarded by its pool.
        try:
            # End the exact physical session's current transaction.
            connection.rollback()
        # Suppress cleanup detail while lease return performs final sanitation or discard.
        except Exception:
            # Preserve the primary application or translated error.
            pass

    # Own one complete read or write transaction with fixed native-error translation.
    @contextmanager
    def _database_cursor(self, *, commit: bool = False):
        # Require exact clean schema compatibility before ordinary data access.
        self.ensure_ready()
        # Start protected checkout so pool failures use the same provider boundary.
        try:
            # Acquire one request-scoped or retained-boundary connection.
            connection = self.connect()
        except BaseException as error:
            # Translate only connector-neutral pool failures.
            self._raise_database_error(error)
            # Preserve caller-owned validation and lifecycle failures.
            raise
        try:
            # Open one dict-row cursor; autocommit false starts on first SQL statement.
            cursor = connection.cursor()
            # Transfer the active transaction to one provider operation.
            yield connection, cursor
            # Commit successful mutations and their associated result validation.
            if commit:
                # Publish every write in the operation atomically.
                connection.commit()
            else:
                # End successful read-only transactions without retaining snapshots.
                connection.rollback()
        except BaseException as error:
            # Discard every partial database change before translating or preserving failure.
            self._rollback_quietly(connection)
            # Translate only native connector and pool errors.
            self._raise_database_error(error)
            # Preserve CasinoError, callback, codec, and validation identity and traceback.
            raise
        finally:
            # Return or retain the connection through the pool-owned cleanup path.
            connection.close()

    # Verify the exact checksum-bound PostgreSQL migration prefix before data access.
    def ensure_ready(self) -> None:
        # Refuse hidden provider access through a planner closure.
        self._reject_planner_mutation()
        # Return after this instance has completed the read-only compatibility gate.
        if self._ready:
            # Avoid repeated control-table reads on each operation.
            return
        # Serialize first-use verification across concurrent request threads.
        with self._ready_lock:
            # Return when another thread completed verification while this thread waited.
            if self._ready:
                # Reuse the exact compatibility result.
                return
            try:
                # Acquire one runtime-identity connection without migration configuration.
                connection = self.connect()
            except BaseException as error:
                # Translate only bounded pool failures.
                self._raise_database_error(error)
                # Preserve non-database caller failures.
                raise
            try:
                # Validate exact clean checksum history through the migration-owned SELECT-only seam.
                schema_state = verify_runtime_compatibility(connection)
                # Retain only the sanitized current version for session and reset logic.
                self._schema_version = schema_state.current_version
                # Mark readiness only after the complete verifier succeeds.
                self._ready = True
                # End the verifier's read transaction before the lease returns to the pool.
                connection.rollback()
            except BaseException as error:
                # Remove any failed read transaction without masking the compatibility result.
                self._rollback_quietly(connection)
                # Convert migration incompatibility to the fixed operator-recovery boundary.
                if isinstance(error, MigrationError):
                    # Hide observed version, checksum, target, and migration detail.
                    raise ConflictError("PostgreSQL storage schema requires operator recovery") from None
                # Translate connector failures without native text.
                self._raise_database_error(error)
                # Preserve unexpected caller-owned failures for test and programming visibility.
                raise
            finally:
                # Return or discard the readiness connection after exact cleanup.
                connection.close()

    # Re-run the migration-owned verifier inside a reset transaction.
    def _runtime_schema_state(self, connection: Any) -> Any:
        # Delegate all catalog/version/checksum interpretation to the accepted migration lane.
        return verify_runtime_compatibility(connection)

    # Derive one signed target-scoped PostgreSQL advisory-lock key.
    def _reset_lock_key(self) -> int:
        # Hash only non-secret normalized target identity.
        target = f"{self.config.host.lower()}:{self.config.port}/{self.config.database}"
        # Convert the first eight digest bytes to PostgreSQL's signed bigint domain.
        return int.from_bytes(hashlib.sha256(target.encode("utf-8")).digest()[:8], byteorder="big", signed=True)

    # Report process-local reset ownership without opening or waiting on a database session.
    def _game_action_reset_is_active(self) -> bool:
        # Serialize inspection against equivalent-provider reset registration and cleanup.
        with _POSTGRES_RESET_REGISTRY_LOCK:
            # Match only this normalized target identity, never credentials or object identity.
            return self._planner_key() in _POSTGRES_RESET_TARGETS

    # Validate the singleton game-action reset epoch row inside an active transaction.
    def _reset_epoch(self, cursor: Any, *, exclusive: bool) -> dict:
        # Use one fixed exclusive statement for reset ownership.
        if exclusive:
            # Lock the exact singleton against every action and reset writer.
            cursor.execute("SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state WHERE state_id = 1 FOR UPDATE")
        else:
            # Use one fixed shared statement for future action visibility.
            cursor.execute("SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state WHERE state_id = 1 FOR SHARE")
        # Fetch the sole expected lifecycle row.
        row = cursor.fetchone()
        # Require exact dict-row fields and singleton identity.
        if type(row) is not dict or set(row) != {"state_id", "current_epoch", "phase"} or row.get("state_id") != 1:
            # Preserve malformed lifecycle state for operator repair.
            raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
        # Require a real bounded integer epoch rather than connector coercion.
        if type(row["current_epoch"]) is not int or not 1 <= row["current_epoch"] <= _GAME_ACTION_MAX_EPOCH:
            # Refuse overflow or malformed lifecycle state.
            raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
        # Require one finite visibility phase.
        if type(row["phase"]) is not str or row["phase"] not in {"ready", "resetting"}:
            # Reject unknown reset visibility semantics.
            raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
        # Return the validated singleton for compare-and-set use.
        return row

    # Delete only reset-owned mutable projections inside the active reset transaction.
    def _clear_mutable_state(self, cursor: Any) -> None:
        # Delete first-class authentication sessions before account bootstrap.
        cursor.execute("DELETE FROM casino_sessions")
        # Delete ledger rows before players to satisfy the wallet foreign key.
        cursor.execute("DELETE FROM casino_ledger")
        # Delete visible game history for a fresh reset projection.
        cursor.execute("DELETE FROM casino_history")
        # Delete JSON documents before caller bootstrap restores reviewed defaults.
        cursor.execute("DELETE FROM casino_documents")
        # Delete player rows after every mutable dependent row.
        cursor.execute("DELETE FROM casino_players")

    # Acquire one fixed session-level PostgreSQL advisory lock without waiting.
    @staticmethod
    def _acquire_advisory_lock(cursor: Any, lock_key: int, *, shared: bool) -> bool:
        # Use one fixed shared statement for state visibility.
        if shared:
            # Bind the target key to the nonblocking shared primitive.
            cursor.execute("SELECT pg_try_advisory_lock_shared(%s) AS acquired", (lock_key,))
        else:
            # Bind the target key to the nonblocking exclusive primitive.
            cursor.execute("SELECT pg_try_advisory_lock(%s) AS acquired", (lock_key,))
        # Read the exact dict-row result.
        row = cursor.fetchone()
        # Accept only a literal true acquisition result.
        return type(row) is dict and row.get("acquired") is True

    # Release one session-level advisory lock held by the exact connection.
    @staticmethod
    def _release_advisory_lock(cursor: Any, lock_key: int, *, shared: bool) -> bool:
        # Use one fixed unlock statement matching shared ownership.
        if shared:
            # Release only the bound shared target key.
            cursor.execute("SELECT pg_advisory_unlock_shared(%s) AS released", (lock_key,))
        else:
            # Release only the bound exclusive target key.
            cursor.execute("SELECT pg_advisory_unlock(%s) AS released", (lock_key,))
        # Read the exact connector result.
        row = cursor.fetchone()
        # Accept only confirmed ownership release.
        return type(row) is dict and row.get("released") is True

    # Hold reset exclusion through clear, caller bootstrap, and phase publication.
    @contextmanager
    def reset_transaction(self):
        # Reject destructive provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Reject same-thread nested reset or visibility ownership.
        if getattr(self._boundary_local, "connection", None) is not None:
            # Preserve the outer boundary as the sole owner.
            raise ConflictError("PostgreSQL reset is already in progress")
        # Verify exact compatible schema before owning a server session.
        self.ensure_ready()
        # Resolve target identity before pool checkout.
        reset_target = self._planner_key()
        # Claim process-local ownership nonblockingly for capacity-one pools.
        with _POSTGRES_RESET_REGISTRY_LOCK:
            # Reject another equivalent provider already resetting this target.
            if reset_target in _POSTGRES_RESET_TARGETS:
                # Avoid waiting behind its retained outer lease.
                raise ConflictError("PostgreSQL reset is already in progress")
            # Reserve this target until unconditional cleanup.
            _POSTGRES_RESET_TARGETS.add(reset_target)
        try:
            # Acquire one outer lease retained through synchronous bootstrap.
            connection = self.connect()
        except BaseException as error:
            # Release provisional local ownership after failed checkout.
            with _POSTGRES_RESET_REGISTRY_LOCK:
                # Remove only this exact target reservation.
                _POSTGRES_RESET_TARGETS.discard(reset_target)
            # Translate pool failures without native connector detail.
            self._raise_database_error(error)
            # Preserve non-database lifecycle errors.
            raise
        # Bind the server lock to this target without credentials.
        lock_key = self._reset_lock_key()
        # Track confirmed session advisory-lock ownership.
        lock_acquired = False
        # Track the durable epoch advanced by phase one.
        reset_epoch: int | None = None
        # Preserve a primary body failure so cleanup cannot replace it.
        primary_failure: BaseException | None = None
        try:
            # Open one dict-row cursor on the retained session.
            cursor = connection.cursor()
            # Acquire exact target exclusion without waiting behind another process.
            if not self._acquire_advisory_lock(cursor, lock_key, shared=False):
                # End the preflight query before reporting contention.
                connection.rollback()
                # Preserve the nonblocking reset contract.
                raise ConflictError("PostgreSQL reset is already in progress")
            # Record ownership before any mutable transaction begins.
            lock_acquired = True
            # End the implicit advisory-lock query transaction while retaining the session lock.
            connection.rollback()
            # Re-verify checksum-bound exact schema on this reset session.
            schema_state = self._runtime_schema_state(connection)
            # Require the complete schema-five provider catalog.
            if not schema_state.initialized or schema_state.status != "clean" or schema_state.current_version != 5:
                # Refuse partial, old, future, or dirty state before deletion.
                raise ConflictError("PostgreSQL storage schema requires operator recovery")
            # Lock and validate the lifecycle singleton inside phase one.
            epoch_state = self._reset_epoch(cursor, exclusive=True)
            # Refuse signed-range overflow before changing the phase.
            if epoch_state["current_epoch"] >= _GAME_ACTION_MAX_EPOCH:
                # Preserve all storage for operator recovery.
                raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
            # Advance again even when explicitly recovering a prior resetting phase.
            reset_epoch = epoch_state["current_epoch"] + 1
            # Bind the new unavailable namespace to the exact earlier singleton.
            cursor.execute("UPDATE casino_game_action_epoch_state SET current_epoch = %s, phase = 'resetting' WHERE state_id = 1 AND current_epoch = %s AND phase = %s RETURNING state_id", (reset_epoch, epoch_state["current_epoch"], epoch_state["phase"]))
            # Require one exact compare-and-set result.
            if cursor.fetchone() != {"state_id": 1}:
                # Refuse ambiguous lifecycle ownership.
                raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
            # Delete only mutable provider projections, preserving claims and receipts.
            self._clear_mutable_state(cursor)
            # Commit phase one before caller bootstrap uses ordinary provider methods.
            connection.commit()
            # Publish this retained lease only to the current thread.
            self._boundary_local.connection = connection
            try:
                # Transfer control while advisory exclusion and resetting phase remain held.
                yield self
            finally:
                # End nested lease borrowing before phase finalization.
                self._boundary_local.connection = None
            # End any implicit transaction residue from the final nested operation.
            connection.rollback()
            # Re-verify exact runtime state without migration authority.
            final_schema_state = self._runtime_schema_state(connection)
            # Require schema five to remain exact before visibility publication.
            if not final_schema_state.initialized or final_schema_state.status != "clean" or final_schema_state.current_version != 5:
                # Leave the durable phase unavailable for recovery.
                raise ConflictError("PostgreSQL storage schema requires operator recovery")
            # Lock the exact singleton for phase-two compare-and-set.
            finalized_state = self._reset_epoch(cursor, exclusive=True)
            # Require the same reset epoch to remain unavailable.
            if finalized_state != {"state_id": 1, "current_epoch": reset_epoch, "phase": "resetting"}:
                # Preserve resetting rather than publishing ambiguous state.
                raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
            # Publish readiness only for this reset attempt's exact namespace.
            cursor.execute("UPDATE casino_game_action_epoch_state SET phase = 'ready' WHERE state_id = 1 AND current_epoch = %s AND phase = 'resetting' RETURNING state_id", (reset_epoch,))
            # Require one exact singleton transition.
            if cursor.fetchone() != {"state_id": 1}:
                # Preserve resetting on ambiguous finalization.
                raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
            # Commit ready only after all caller bootstrap writes are durable.
            connection.commit()
        except BaseException as error:
            # Preserve the exact original failure for cleanup-aware propagation.
            primary_failure = error
            # Discard only the current uncommitted transaction.
            self._rollback_quietly(connection)
            # Convert migration-state failures to the fixed schema boundary.
            if isinstance(error, MigrationError):
                # Hide all migration and target detail.
                raise ConflictError("PostgreSQL storage schema requires operator recovery") from None
            # Translate only native connector and pool errors.
            self._raise_database_error(error)
            # Preserve application and caller failures unchanged.
            raise
        finally:
            # Clear borrowing after every body or finalization outcome.
            self._boundary_local.connection = None
            # Track a release failure only when no primary failure is active.
            release_failure = False
            try:
                # Release only a lock this session proved it acquired.
                if lock_acquired:
                    # End any failed transaction before the unlock statement.
                    self._rollback_quietly(connection)
                    # Open one final dict-row cursor on the retained session.
                    release_cursor = connection.cursor()
                    # Require exact session ownership release.
                    release_failure = not self._release_advisory_lock(release_cursor, lock_key, shared=False)
                    # End the unlock query's implicit transaction.
                    connection.rollback()
            except Exception:
                # Mark uncertain release so pool reset or physical close must clear it.
                release_failure = True
            finally:
                try:
                    # Return or discard the retained outer lease.
                    connection.close()
                finally:
                    # Release process-local target ownership unconditionally.
                    with _POSTGRES_RESET_REGISTRY_LOCK:
                        # Allow a later explicit recovery attempt.
                        _POSTGRES_RESET_TARGETS.discard(reset_target)
            # Report release failure only when it cannot mask a primary body failure.
            if release_failure and primary_failure is None:
                # Publish one fixed target-free lock cleanup category.
                raise ConflictError("PostgreSQL reset lock release failed")

    # Reset mutable PostgreSQL state through the complete phase-owned boundary.
    def reset(self) -> None:
        # Reuse the same boundary with an intentionally empty bootstrap body.
        with self.reset_transaction():
            # Preserve direct reset behavior without additional writes.
            pass

    # Exclude reset while direct storage-backed state enumeration executes.
    @contextmanager
    def state_visibility_transaction(self):
        # Reject nested visibility or reset ownership on the same thread.
        if getattr(self._boundary_local, "connection", None) is not None:
            # Preserve the outer boundary without another lease.
            yield self
            # Finish the nested compatibility boundary.
            return
        # Require schema compatibility before retaining one visibility lease.
        self.ensure_ready()
        # Resolve the same target-scoped advisory key used by reset.
        lock_key = self._reset_lock_key()
        # Acquire one outer request-scoped connection.
        connection = self.connect()
        # Track confirmed shared advisory ownership.
        lock_acquired = False
        # Preserve body failures across best-effort release.
        primary_failure: BaseException | None = None
        try:
            # Open one dict-row cursor on the retained session.
            cursor = connection.cursor()
            # Acquire shared visibility exclusion without waiting behind reset.
            if not self._acquire_advisory_lock(cursor, lock_key, shared=True):
                # Refuse a snapshot while reset owns the target.
                raise ConflictError("PostgreSQL reset is already in progress")
            # Record exact shared lock ownership.
            lock_acquired = True
            # End the implicit preflight transaction while retaining the session lock.
            connection.rollback()
            # Reuse this connection for nested reads at pool capacity one.
            self._boundary_local.connection = connection
            try:
                # Transfer control while reset exclusion remains held.
                yield self
            finally:
                # End nested borrowing before unlock.
                self._boundary_local.connection = None
        except BaseException as error:
            # Retain the primary failure so cleanup cannot mask it.
            primary_failure = error
            # End any nested transaction residue.
            self._rollback_quietly(connection)
            # Translate connector failures only.
            self._raise_database_error(error)
            # Preserve caller and application errors unchanged.
            raise
        finally:
            # Clear thread-local borrowing after every outcome.
            self._boundary_local.connection = None
            # Track uncertain shared-lock cleanup.
            release_failure = False
            try:
                # Release only confirmed shared ownership.
                if lock_acquired:
                    # End any active transaction before the unlock query.
                    self._rollback_quietly(connection)
                    # Open one final cursor on the retained session.
                    release_cursor = connection.cursor()
                    # Require exact shared advisory-lock release.
                    release_failure = not self._release_advisory_lock(release_cursor, lock_key, shared=True)
                    # End the unlock query's implicit transaction.
                    connection.rollback()
            except Exception:
                # Force the pool cleanup path to handle uncertain session state.
                release_failure = True
            finally:
                # Return or discard the retained visibility connection.
                connection.close()
            # Avoid masking an earlier caller failure with cleanup evidence.
            if release_failure and primary_failure is None:
                # Surface one fixed visibility-lock recovery category.
                raise ConflictError("PostgreSQL visibility lock release failed")

    # Convert one PostgreSQL player row into the existing public shape.
    @staticmethod
    def _player_from_row(row: dict) -> dict:
        # Return only the established provider-neutral player fields.
        return {"player_id": row["player_id"], "display_name": row["display_name"], "type": row["player_type"], "balance": _money(row["balance"]), "created_at": row["created_at"], "updated_at": row["updated_at"], "status": row["status"]}

    # Require one PostgreSQL identity insert to return a positive sequence value.
    @staticmethod
    def _require_sequence_id(row: Any) -> int:
        # Accept only the exact one-column dict-row projection.
        if type(row) is not dict or set(row) != {"sequence_id"} or type(row["sequence_id"]) is not int or row["sequence_id"] <= 0:
            # Refuse ambiguous append-only ordering without exposing row content.
            raise ConflictError("PostgreSQL storage sequence requires operator recovery")
        # Return the validated identity for focused ordering evidence.
        return row["sequence_id"]

    # Encode one caller-owned JSON value into deterministic JSONB input text.
    @staticmethod
    def _canonical_json(value: Any) -> str:
        # Preserve Unicode while sorting keys and removing insignificant whitespace.
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    # Load all player rows without seeding or mutating a missing table.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Open one read-only transaction through the fixed schema/error boundary.
        with self._database_cursor() as (_connection, cursor):
            # Read wallets in stable primary-key order.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players ORDER BY player_id")
            try:
                # Convert every row into the historical document projection.
                players = [self._player_from_row(row) for row in cursor.fetchall()]
                # Validate the complete wallet document before exposing any balance.
                return _validated_players_document({"schema_version": SCHEMA_VERSION, "players": players})
            except (KeyError, TypeError, ValueError, OverflowError, ValidationError, ConflictError):
                # Preserve malformed relational money state for operator recovery.
                raise ConflictError("Wallet storage requires operator recovery") from None

    # Read one player through the primary-key index.
    def get_player(self, player_id: str, default_factory: Callable[[], dict]) -> dict | None:
        # Open one read-only point lookup.
        with self._database_cursor() as (_connection, cursor):
            # Select only the requested wallet row.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s", (player_id,))
            # Fetch at most one primary-key row.
            row = cursor.fetchone()
            # Preserve the provider-neutral missing result.
            if row is None:
                # Return no player without scanning unrelated wallets.
                return None
            try:
                # Convert and validate the selected money row.
                player = self._player_from_row(row)
                # Reuse the canonical complete wallet validator on one row.
                return _validated_players_document({"schema_version": SCHEMA_VERSION, "players": [player]})["players"][0]
            except (KeyError, TypeError, ValueError, OverflowError, ValidationError, ConflictError):
                # Preserve the malformed row for explicit operator repair.
                raise ConflictError("Wallet storage requires operator recovery") from None

    # Scan or repair wallet residue under deterministic row locks.
    def normalize_wallet_balances(self, *, apply: bool = False) -> dict:
        # Reject mutation or inspection attempted from inside a planner.
        self._reject_planner_mutation()
        # Commit only the explicit operator-owned apply path.
        with self._database_cursor(commit=apply) as (_connection, cursor):
            # Lock every wallet in deterministic identity order.
            cursor.execute("SELECT player_id, balance FROM casino_players ORDER BY player_id FOR UPDATE")
            # Materialize the bounded wallet set while locks remain held.
            rows = cursor.fetchall()
            # Collect exact residue facts without changing any row.
            residues: list[tuple[str, Decimal, Decimal]] = []
            # Inspect every durable wallet exactly once.
            for row in rows:
                try:
                    # Decode the exact provider money value.
                    stored = _money_decimal(row["balance"])
                    # Derive the canonical cents value under the shared rule.
                    normalized = _quantized_money_decimal(stored)
                except (KeyError, ValidationError):
                    # Preserve all wallets on malformed money state.
                    raise ConflictError("Wallet storage requires operator recovery") from None
                # Refuse insolvent wallets instead of treating them as residue.
                if stored < 0:
                    # Preserve the complete transaction for accounting recovery.
                    raise ConflictError("Wallet storage requires operator recovery")
                # Retain only genuine sub-cent differences.
                if stored != normalized:
                    # Preserve exact decimal values until the optional write path.
                    residues.append((row["player_id"], stored, normalized))
            # Return a bounded read-only report without mutation.
            if not apply:
                # Publish counts only, never wallet identities or source values.
                return {"provider": self.name, "checked": len(rows), "residue_count": len(residues), "normalized_count": 0, "clean": not residues, "applied": False}
            # Publish each audit row and wallet update in this same transaction.
            for player_id, stored, normalized in residues:
                # Build the deterministic provider-neutral audit event.
                event = _wallet_normalization_event(player_id, stored, normalized)
                # Read a prior compatible audit row by deterministic identity.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json FROM casino_ledger WHERE ledger_id = %s", (event["ledger_id"],))
                # Resolve interrupted or repeated operator execution.
                existing_row = cursor.fetchone()
                # Insert the immutable audit row when absent.
                if existing_row is None:
                    # Persist zero visible movement plus exact residue details.
                    cursor.execute("INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSONB)) RETURNING sequence_id", (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], Decimal("0.00"), normalized, normalized, event["action_scope"], event["action_key"], event["action_fingerprint"], self._canonical_json(event["details"])))
                    # Require explicit append-only sequence allocation.
                    self._require_sequence_id(cursor.fetchone())
                else:
                    # Convert the stored row into the complete replay shape.
                    existing = {**_ledger_from_row(existing_row), "action_scope": existing_row["action_scope"], "action_key": existing_row["action_key"], "action_fingerprint": existing_row["action_fingerprint"]}
                    # Reject deterministic-identity collision before wallet mutation.
                    _validate_wallet_normalization_replay(existing, event)
                # Publish the exact cent value on the already locked row.
                cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (normalized, utc_now(), player_id))
            # Return bounded evidence after the enclosing context commits.
            return {"provider": self.name, "checked": len(rows), "residue_count": len(residues), "normalized_count": len(residues), "clean": True, "applied": True}

    # Insert one player through the deterministic identity boundary.
    def insert_player(self, player: dict) -> dict:
        # Reject player insertion attempted from inside a planner.
        self._reject_planner_mutation()
        # Reuse the primary-key insert-or-read transaction.
        return self.ensure_player(player)

    # Insert every missing bootstrap wallet without replacing durable rows.
    def bootstrap_players(self, state: dict) -> None:
        # Reject bootstrap mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Own one transaction across the complete supplied batch.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Visit every candidate row in caller order.
            for player in state.get("players", []):
                # Insert only absent primary keys and preserve existing wallet/lifecycle state.
                cursor.execute("INSERT INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (player_id) DO NOTHING", (player["player_id"], player["display_name"], player.get("type", "human"), _quantized_money_decimal(player.get("balance", 0)), player.get("created_at", utc_now()), player.get("updated_at", utc_now()), player.get("status", "active")))

    # Update one player under a row-level PostgreSQL lock.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Own one complete row-locking write transaction.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Lock the exact player row until commit.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Fetch the locked row.
            row = cursor.fetchone()
            # Reject a missing player through the established public error.
            if row is None:
                # Preserve the exact existing player lookup diagnostic.
                raise NotFoundError(f"Player {player_id} was not found")
            try:
                # Convert stored money before invoking the caller updater.
                player = self._player_from_row(row)
            except (KeyError, TypeError, ValueError, OverflowError, ValidationError):
                # Preserve malformed relational wallet state.
                raise ConflictError("Wallet storage requires operator recovery") from None
            # Let the caller mutate the detached public player shape once.
            updater(player)
            # Quantize the updated wallet through the shared cents boundary.
            player["balance"] = _quantized_money(player.get("balance", 0))
            # Stamp one deterministic provider update time.
            player["updated_at"] = utc_now()
            # Persist the complete mutable player projection.
            cursor.execute("UPDATE casino_players SET display_name = %s, player_type = %s, balance = %s, updated_at = %s, status = %s WHERE player_id = %s", (player["display_name"], player.get("type", "human"), player["balance"], player["updated_at"], player.get("status", "active"), player_id))
            # Return the exact shape that the enclosing context commits.
            return player

    # Create one deterministic player or return its compatible existing row.
    def ensure_player(self, player: dict) -> dict:
        # Reject provisioning attempted from inside a planner.
        self._reject_planner_mutation()
        # Own one insert-or-read primary-key transaction.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Insert once without overwriting an existing wallet.
            cursor.execute("INSERT INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (player_id) DO NOTHING", (player["player_id"], player["display_name"], player.get("type", "human"), _quantized_money_decimal(player.get("balance", 0)), player["created_at"], player["updated_at"], player.get("status", "active")))
            # Lock and read the resulting durable row.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s FOR UPDATE", (player["player_id"],))
            # Resolve the inserted or pre-existing row.
            row = cursor.fetchone()
            # Reject impossible absence without committing partial state.
            if row is None:
                # Publish one fixed provisioning recovery category.
                raise ConflictError("Player provisioning did not produce durable state")
            try:
                # Convert the locked durable row through the money boundary.
                result = self._player_from_row(row)
            except (KeyError, TypeError, ValueError, OverflowError, ValidationError):
                # Preserve the malformed existing wallet.
                raise ConflictError("Wallet storage requires operator recovery") from None
            # Reject primary-key collision with incompatible player ownership.
            if result.get("type") != player.get("type"):
                # Keep the original row unchanged.
                raise ConflictError("Player provisioning identity conflicts with existing state")
            # Return the inserted or compatible committed row.
            return result

    # Execute one wallet mutation and ledger append atomically.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize fake money before opening a transaction.
        amount = _quantized_money(amount)
        # Reject zero-value rows through the existing validation contract.
        if amount == 0:
            # Preserve the standard ledger diagnostic.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Own the wallet lock, balance update, and append in one transaction.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Lock the selected wallet before computing its next balance.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the locked wallet row.
            row = cursor.fetchone()
            # Reject an unknown player without mutation.
            if row is None:
                # Preserve the established player lookup result.
                raise NotFoundError(f"Player {player_id} was not found")
            try:
                # Decode the exact stored cents balance.
                before = _money(row["balance"])
                # Compute the next cents balance without binary residue.
                after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
            except (KeyError, TypeError, ValueError, OverflowError, ValidationError):
                # Preserve malformed wallet state for operator recovery.
                raise ConflictError("Wallet storage requires operator recovery") from None
            # Reject an overdraw before wallet or ledger mutation.
            if after < 0:
                # Return the existing bounded insufficient-funds details.
                raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
            # Build the immutable public event before persistence.
            event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, details)
            # Update the already locked wallet row.
            cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (after, utc_now(), player_id))
            # Append the corresponding event and require explicit sequence allocation.
            cursor.execute("INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSONB)) RETURNING sequence_id", (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], self._canonical_json(event["details"])))
            # Validate the append-only ordering identity before commit.
            self._require_sequence_id(cursor.fetchone())
            # Return the exact event committed by the enclosing context.
            return event

    # Execute or replay one storage-enforced ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
        # Reject exactly-once wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize fake money before identity derivation.
        amount = _quantized_money(amount)
        # Reject zero-value rows before database access.
        if amount == 0:
            # Preserve the standard ledger diagnostic.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Normalize the indexed caller-owned key.
        action_key = _normalize_action_key(action_key)
        # Derive the game-or-core identity namespace.
        scope = _action_scope(game)
        # Derive exact semantic replay identity.
        fingerprint = _action_fingerprint(amount, transaction_type, game, round_id, details)
        # Add storage-owned identity metadata to the durable event.
        committed_details = _action_details(details, action_key, fingerprint)
        # Own identity lookup, wallet mutation, and append under one player lock.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Serialize all wallet actions for this player.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the locked wallet row.
            player_row = cursor.fetchone()
            # Reject unknown players before identity reservation.
            if player_row is None:
                # Preserve the established lookup result.
                raise NotFoundError(f"Player {player_id} was not found")
            # Read any prior event for the unique storage action identity.
            cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s AND action_scope = %s AND action_key = %s", (player_id, scope, action_key))
            # Fetch the optional immutable replay row.
            existing_row = cursor.fetchone()
            # Return a compatible prior event without another mutation.
            if existing_row is not None:
                try:
                    # Convert the relational row to the public event shape.
                    existing_event = _ledger_from_row(existing_row)
                except (KeyError, TypeError, ValueError, OverflowError, json.JSONDecodeError):
                    # Preserve malformed ledger state for explicit recovery.
                    raise ConflictError("PostgreSQL ledger storage requires operator recovery") from None
                # Reject changed semantic reuse before replay.
                _validate_action_replay(existing_event, fingerprint, action_key)
                # Return the original event with the explicit replay marker.
                return existing_event, True
            try:
                # Decode the exact locked wallet balance.
                before = _money(player_row["balance"])
                # Compute the next canonical cents balance.
                after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
            except (KeyError, TypeError, ValueError, OverflowError, ValidationError):
                # Preserve malformed wallet state.
                raise ConflictError("Wallet storage requires operator recovery") from None
            # Reject an overdraw without reserving action identity.
            if after < 0:
                # Return the existing bounded insufficient-funds details.
                raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
            # Build the immutable event returned by every later replay.
            event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, committed_details)
            # Update the already locked wallet.
            cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (after, utc_now(), player_id))
            # Append action identity, semantic digest, and wallet transition together.
            cursor.execute("INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSONB)) RETURNING sequence_id", (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], scope, action_key, fingerprint, self._canonical_json(event["details"])))
            # Require explicit append-only sequence allocation.
            self._require_sequence_id(cursor.fetchone())
            # Return the new event and non-replay marker after commit.
            return event, False

    # Find one committed ledger action through its unique identity index.
    def find_ledger_action(self, player_id: str, game: str | None, action_key: str) -> dict | None:
        # Normalize the complete indexed identity before opening a connection.
        action_key = _normalize_action_key(action_key)
        # Derive the same game-or-core scope used by the writer.
        scope = _action_scope(game)
        # Execute one read-only point lookup.
        with self._database_cursor() as (_connection, cursor):
            # Query the exact unique action index.
            cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s AND action_scope = %s AND action_key = %s", (player_id, scope, action_key))
            # Fetch at most one row.
            row = cursor.fetchone()
            # Preserve the optional missing result.
            if row is None:
                # Return no event for an unused identity.
                return None
            try:
                # Convert the exact row to the public ledger event.
                return _ledger_from_row(row)
            except (KeyError, TypeError, ValueError, OverflowError, json.JSONDecodeError):
                # Preserve corrupt evidence for operator recovery.
                raise ConflictError("PostgreSQL ledger storage requires operator recovery") from None

    # Read a bounded chronological window of recent ledger events.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Open one read-only bounded query.
        with self._database_cursor() as (_connection, cursor):
            # Select newest global rows when no player filter is present.
            if player_id is None:
                # Bind the caller limit as a parameter.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger ORDER BY sequence_id DESC LIMIT %s", (int(limit),))
            else:
                # Select newest rows through the player index.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s ORDER BY sequence_id DESC LIMIT %s", (player_id, int(limit)))
            # Reverse newest-first storage order to historical chronological order.
            rows = list(reversed(cursor.fetchall()))
            try:
                # Convert every bounded row into the established public event.
                return [_ledger_from_row(row) for row in rows]
            except (KeyError, TypeError, ValueError, OverflowError, json.JSONDecodeError):
                # Preserve malformed append-only evidence for recovery.
                raise ConflictError("PostgreSQL ledger storage requires operator recovery") from None

    # Aggregate economics from one provider-owned bounded ledger snapshot.
    def ledger_economics(self, window: int, game: str | None = None, recent: int = 0) -> dict:
        # Reuse the provider-neutral one-read aggregation contract.
        return StorageProvider.ledger_economics(self, window, game=game, recent=recent)

    # Append one normalized game-history event.
    def append_history(self, event: dict) -> None:
        # Reject history mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Preserve existing string JSON while encoding already-decoded test values.
        details_json = event["details_json"] if isinstance(event["details_json"], str) else self._canonical_json(event["details_json"])
        # Insert and validate one append-only history identity.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Bind every historical field plus explicit JSONB conversion.
            cursor.execute("INSERT INTO casino_history (timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSONB), %s) RETURNING sequence_id", tuple(event[field] for field in HISTORY_FIELDS[:-2]) + (details_json, event["schema_version"]))
            # Require explicit ordering identity before commit.
            self._require_sequence_id(cursor.fetchone())

    # Read recent history rows with an optional exact-game filter.
    def recent_history(self, limit: int = 100, game: str | None = None) -> list[dict]:
        # Open one read-only bounded query.
        with self._database_cursor() as (_connection, cursor):
            # Select through the game filter when supplied.
            if game:
                # Bind both filter and row limit.
                cursor.execute("SELECT timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version FROM casino_history WHERE game = %s ORDER BY sequence_id DESC LIMIT %s", (game, int(limit)))
            else:
                # Select newest global history rows.
                cursor.execute("SELECT timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version FROM casino_history ORDER BY sequence_id DESC LIMIT %s", (int(limit),))
            # Reverse the newest-first rows into historical order.
            rows = list(reversed(cursor.fetchall()))
            try:
                # Convert every bounded row to the CSV/API compatibility shape.
                return [_history_from_row(row) for row in rows]
            except (KeyError, TypeError, ValueError, OverflowError, json.JSONDecodeError):
                # Preserve malformed history evidence for operator recovery.
                raise ConflictError("PostgreSQL history storage requires operator recovery") from None

    # Read one named JSONB document with lazy missing-row defaults.
    def read_document(self, key: str, default: Any) -> Any:
        # Open one read-only point lookup.
        with self._database_cursor() as (_connection, cursor):
            # Query the canonical document primary key.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s", (key,))
            # Fetch the optional row.
            row = cursor.fetchone()
            # Evaluate the default only when the row is absent.
            if row is None:
                # Preserve existing factory and value semantics.
                return default() if callable(default) else default
            # Require the exact one-column mapping without coercion.
            if type(row) is not dict or set(row) != {"payload_json"}:
                # Preserve malformed relational projection for recovery.
                raise RuntimeError("Stored document requires operator recovery")
            # Return psycopg's already-decoded JSONB value.
            return row["payload_json"]

    # Report exact document existence without decoding or creating a row.
    def document_exists(self, key: str) -> bool:
        # Open one read-only primary-key lookup.
        with self._database_cursor() as (_connection, cursor):
            # Select one named constant through the canonical key.
            cursor.execute("SELECT 1 AS present FROM casino_documents WHERE document_key = %s", (key,))
            # Return true only for the exact expected dict-row result.
            return cursor.fetchone() == {"present": 1}

    # Read one security-sensitive document through the strict shape boundary.
    def read_document_strict(self, key: str, default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Reuse missing/default and decoded JSONB semantics.
        value = self.read_document(key, default)
        # Apply the provider-neutral fixed validator failure boundary.
        return _validated_strict_document(value, validator)

    # Upsert one complete JSONB document by canonical key.
    def write_document(self, key: str, data: Any) -> None:
        # Reject document mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Encode before database access so caller codec failures remain unchanged.
        payload = self._canonical_json(data)
        # Commit one primary-key upsert atomically.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Replace only the selected document and update timestamp.
            cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, CAST(%s AS JSONB), %s) ON CONFLICT (document_key) DO UPDATE SET payload_json = EXCLUDED.payload_json, updated_at = EXCLUDED.updated_at", (key, payload, utc_now()))

    # Mutate one document under a PostgreSQL row lock.
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Reject document mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Evaluate and encode the missing-row seed exactly once.
        initial = default() if callable(default) else default
        # Encode before database access so caller codec failures remain unchanged.
        initial_json = self._canonical_json(initial)
        # Own materialization, row lock, callback, and publication in one transaction.
        with self._database_cursor(commit=True) as (_connection, cursor):
            # Materialize an absent row without overwriting existing state.
            cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, CAST(%s AS JSONB), %s) ON CONFLICT (document_key) DO NOTHING", (key, initial_json, utc_now()))
            # Lock the canonical row through callback and update.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (key,))
            # Fetch the row guaranteed by the preceding insert-or-existing boundary.
            row = cursor.fetchone()
            # Require one exact decoded JSONB projection.
            if type(row) is not dict or set(row) != {"payload_json"}:
                # Preserve ambiguous state without callback execution.
                raise RuntimeError("Stored document requires operator recovery")
            # Validate security-sensitive structure while the row remains locked.
            current = _validated_strict_document(row["payload_json"], validator)
            # Invoke the caller-owned mutator exactly once.
            updated = mutator(current)
            # Canonically encode the complete updated value before SQL mutation.
            updated_json = self._canonical_json(updated)
            # Replace exactly the locked document row.
            cursor.execute("UPDATE casino_documents SET payload_json = CAST(%s AS JSONB), updated_at = %s WHERE document_key = %s", (updated_json, utc_now(), key))
            # Return only the value committed by the enclosing context.
            return updated
