# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free PostgreSQL provider-core tests. (STORAGE-023, TEST-255)"""

# Import AST inspection so every production SQL call stays literal and parameterized.
import ast
# Import exact decimal values matching psycopg's NUMERIC decoder.
from decimal import Decimal
# Import dynamic module loading for isolation from the still-disjoint migration/session lanes.
import importlib.util
# Import filesystem paths for exact production source inspection.
from pathlib import Path
# Import synthetic module and namespace helpers for connector-neutral models.
from types import ModuleType, SimpleNamespace
# Import standard unit-test assertions.
import unittest
# Import patching support for readiness and dependency isolation.
from unittest import mock

# Import accepted PostgreSQL configuration without importing the optional driver.
from casino.core.storage.base import PostgresConfig
# Import the public errors that provider translation must preserve.
from casino.errors import ConflictError, InsufficientFundsError

# Resolve the repository root from this tracked test file.
ROOT = Path(__file__).resolve().parents[1]
# Resolve the exact provider implementation owned by this lane.
PROVIDER_PATH = ROOT / "casino" / "core" / "storage" / "postgres_provider.py"


# Define the migration-owned fixed error type expected by the provider seam.
class StubMigrationError(RuntimeError):
    # Preserve one named category without implementation detail.
    pass


# Define the disjoint session mixin shape used only while loading this source candidate.
class StubPostgresSessionMixin:
    # Leave every real session method to the separately reviewed session lane.
    pass


# Load provider core while its independently owned dependency files remain outside this branch.
def _load_provider_module() -> ModuleType:
    # Build one migration module with the exact anticipated public names.
    migration_module = ModuleType("casino.core.postgres_migrations")
    # Publish the fixed migration error category.
    migration_module.MigrationError = StubMigrationError
    # Publish one inert verifier that focused tests replace explicitly.
    migration_module.verify_runtime_compatibility = lambda connection: SimpleNamespace(current_version=5, initialized=True, status="clean")
    # Build one session module with only the agreed mixin interface.
    session_module = ModuleType("casino.core.storage.sessions_postgres")
    # Publish the disjoint mixin class for provider composition.
    session_module.PostgresSessionMixin = StubPostgresSessionMixin
    # Create a private module identity for this exact source file.
    spec = importlib.util.spec_from_file_location("tests._postgres_provider_under_test", PROVIDER_PATH)
    # Require the standard loader to exist for a regular Python source file.
    if spec is None or spec.loader is None:
        # Fail the focused suite before any ambiguous import state.
        raise RuntimeError("PostgreSQL provider test module could not be loaded")
    # Allocate the isolated module object.
    provider_module = importlib.util.module_from_spec(spec)
    # Install only the two disjoint dependency stubs during source execution.
    with mock.patch.dict("sys.modules", {"casino.core.postgres_migrations": migration_module, "casino.core.storage.sessions_postgres": session_module}):
        # Execute the exact provider source without importing psycopg or opening a listener.
        spec.loader.exec_module(provider_module)
    # Return the loaded implementation for all focused tests.
    return provider_module


# Load the provider source once under the isolated dependency boundary.
provider = _load_provider_module()


# Model psycopg's public transaction-state enum values.
class FakeTransactionStatus:
    # Represent the exact reusable idle state.
    IDLE = "idle"
    # Represent one ordinary implicit transaction.
    INTRANS = "intrans"


# Define connector-owned error categories for fixed translation tests.
class FakeDatabaseError(Exception):
    # Preserve one native database family without target detail.
    pass


# Define the connector-owned integrity subclass.
class FakeIntegrityError(FakeDatabaseError):
    # Preserve one constraint-conflict family.
    pass


# Model only the psycopg attributes consumed by provider core.
class FakeDriver:
    # Publish the native database base class.
    Error = FakeDatabaseError
    # Publish the native constraint category.
    IntegrityError = FakeIntegrityError
    # Publish the libpq transaction-status namespace.
    pq = SimpleNamespace(TransactionStatus=FakeTransactionStatus)


# Model one adapter-owned cursor on an exact physical connection.
class AdapterCursor:
    # Retain the connection and optional failure injection.
    def __init__(self, connection) -> None:
        # Store the exact owning connection for identity and state assertions.
        self.connection = connection
        # Track whether cleanup closed this cursor.
        self.closed = False

    # Execute one constant adapter statement.
    def execute(self, statement: str) -> None:
        # Record the exact reviewed statement.
        self.connection.statements.append(statement)
        # Raise only when the focused failure path is armed.
        if self.connection.fail_execute:
            # Surface a synthetic connector failure without external detail.
            raise FakeDatabaseError("synthetic native detail")
        # Model psycopg implicit transaction entry only outside autocommit.
        if not self.connection.autocommit:
            # Mark the exact physical session non-idle.
            self.connection.info.transaction_status = FakeTransactionStatus.INTRANS

    # Return the exact dict-row wire-check result.
    def fetchone(self) -> dict:
        # Publish the one fixed wire-check alias.
        return {"wire_ok": 1}

    # Close the adapter-owned cursor.
    def close(self) -> None:
        # Record exact cursor cleanup.
        self.closed = True


# Model one psycopg physical session for adapter lifecycle tests.
class AdapterConnection:
    # Start one reviewed autocommit-false idle session.
    def __init__(self) -> None:
        # Store the public transaction status object.
        self.info = SimpleNamespace(transaction_status=FakeTransactionStatus.IDLE)
        # Preserve the provider's reviewed baseline.
        self.autocommit = False
        # Record constant statements in execution order.
        self.statements: list[str] = []
        # Allow one test to force statement failure.
        self.fail_execute = False
        # Count rollback cleanup.
        self.rollback_calls = 0

    # Open one cursor on this exact physical object.
    def cursor(self) -> AdapterCursor:
        # Return an adapter cursor without reconnecting.
        return AdapterCursor(self)

    # Roll back and restore exact idle status.
    def rollback(self) -> None:
        # Count the connector cleanup call.
        self.rollback_calls += 1
        # Return the modeled session to IDLE.
        self.info.transaction_status = FakeTransactionStatus.IDLE


# Define a scripted dict-row cursor for provider transaction tests.
class ScriptedCursor:
    # Retain bounded fetch results and executed SQL.
    def __init__(self, fetchone_rows=None, fetchall_rows=None) -> None:
        # Copy one deterministic queue of point results.
        self.fetchone_rows = list(fetchone_rows or [])
        # Copy one deterministic queue of collection results.
        self.fetchall_rows = list(fetchall_rows or [])
        # Record every SQL string and bound parameter tuple.
        self.executed: list[tuple[str, object]] = []

    # Record one parameterized provider statement.
    def execute(self, statement: str, parameters=None) -> None:
        # Retain exact SQL and caller parameters for audit.
        self.executed.append((statement, parameters))

    # Return the next bounded point result.
    def fetchone(self):
        # Return the next scripted row or the missing result.
        return self.fetchone_rows.pop(0) if self.fetchone_rows else None

    # Return the next bounded result collection.
    def fetchall(self):
        # Return the next scripted collection or an empty set.
        return self.fetchall_rows.pop(0) if self.fetchall_rows else []


# Model one operation-scoped connection whose counters expose transaction cleanup.
class ScriptedConnection:
    # Retain one shared cursor and transaction counters.
    def __init__(self, cursor: ScriptedCursor) -> None:
        # Store the exact operation cursor.
        self.operation_cursor = cursor
        # Count successful commits.
        self.commit_calls = 0
        # Count read or failure rollbacks.
        self.rollback_calls = 0
        # Count lease close calls.
        self.close_calls = 0

    # Return the exact scripted cursor.
    def cursor(self) -> ScriptedCursor:
        # Reuse one deterministic cursor per operation.
        return self.operation_cursor

    # Commit one successful write transaction.
    def commit(self) -> None:
        # Record exact write publication.
        self.commit_calls += 1

    # Roll back one read or failed write transaction.
    def rollback(self) -> None:
        # Record exact cleanup.
        self.rollback_calls += 1

    # Return one modeled request lease.
    def close(self) -> None:
        # Record unconditional operation cleanup.
        self.close_calls += 1


# Build a provider instance without invoking optional-driver construction.
def _provider_with_connection(connection: ScriptedConnection):
    # Allocate the production class without its connector-loading initializer.
    selected = provider.PostgresStorageProvider.__new__(provider.PostgresStorageProvider)
    # Install the fake connector error hierarchy.
    selected._driver = FakeDriver
    # Mark schema readiness so focused row tests avoid the disjoint verifier.
    selected._ready = True
    # Supply one exact operation-scoped connection.
    selected.connect = lambda **overrides: connection
    # Supply the target fields required by planner checks.
    selected.config = PostgresConfig("127.0.0.1", 5432, "casino", "", "fixture")
    # Install empty same-thread reset and visibility borrowing state.
    selected._boundary_local = __import__("threading").local()
    # Return the isolated production provider instance.
    return selected


# Prove connector lifecycle, SQL policy, and core row transactions listener-free.
class PostgresProviderTests(unittest.TestCase):
    # Prove adapter reset and wire check preserve IDLE on the same physical object.
    def test_adapter_reset_and_health_remain_idle_without_reconnect(self) -> None:
        # Build one production adapter around the fake public psycopg surface.
        adapter = provider._PsycopgConnectionAdapter(FakeDriver)
        # Allocate one exact physical session.
        connection = AdapterConnection()
        # Run complete cleanup before the final health check.
        adapter.reset(connection)
        # Require advisory cleanup and DISCARD ALL in fixed order.
        self.assertEqual(connection.statements, ["SELECT pg_advisory_unlock_all()", "DISCARD ALL"])
        # Require restored autocommit false and exact IDLE status.
        self.assertEqual((connection.autocommit, connection.info.transaction_status), (False, FakeTransactionStatus.IDLE))
        # Require the same object to pass one wire check.
        self.assertTrue(adapter.is_healthy(connection))
        # Require no implicit transaction after SELECT 1.
        self.assertEqual((connection.statements[-1], connection.autocommit, connection.info.transaction_status), ("SELECT 1 AS wire_ok", False, FakeTransactionStatus.IDLE))

    # Prove adapter exceptions restore autocommit and leave an idle discardable session.
    def test_adapter_failure_restores_autocommit_and_idle_status(self) -> None:
        # Build one adapter and exact physical session.
        adapter = provider._PsycopgConnectionAdapter(FakeDriver)
        connection = AdapterConnection()
        # Arm a synthetic native failure during the wire check.
        connection.fail_execute = True
        # Require the native failure to reach the pool's discard boundary.
        with self.assertRaises(FakeDatabaseError):
            # Exercise the same physical object without reconnect.
            adapter.is_healthy(connection)
        # Require unconditional policy restoration and no INTRANS residue.
        self.assertEqual((connection.autocommit, connection.info.transaction_status), (False, FakeTransactionStatus.IDLE))

    # Prove physical connection construction uses only reviewed psycopg options.
    def test_physical_connection_uses_dict_rows_and_bounded_timeout(self) -> None:
        # Allocate provider state without optional import.
        selected = provider.PostgresStorageProvider.__new__(provider.PostgresStorageProvider)
        # Install exact non-secret configuration.
        selected.config = PostgresConfig("127.0.0.1", 5432, "casino", "secret", "fixture")
        # Install one sentinel dict-row factory.
        selected._dict_row = object()
        # Capture connector keyword arguments.
        calls = []
        # Model psycopg connect without network access.
        selected._driver = SimpleNamespace(connect=lambda **kwargs: calls.append(kwargs) or object())
        # Open one modeled physical connection.
        created = selected._open_physical_connection(3)
        # Require one connector result and exact bounded options.
        self.assertIsNotNone(created)
        self.assertEqual(calls, [{"host": "127.0.0.1", "port": 5432, "user": "casino", "password": "secret", "dbname": "fixture", "connect_timeout": 3, "autocommit": False, "row_factory": selected._dict_row, "options": "-c default_transaction_isolation=read committed"}])

    # Prove readiness calls only the migration-owned no-secret verifier once.
    def test_readiness_uses_exact_runtime_verifier_once(self) -> None:
        # Build one connection whose cleanup is observable.
        connection = ScriptedConnection(ScriptedCursor())
        # Allocate production provider state without construction.
        selected = provider.PostgresStorageProvider.__new__(provider.PostgresStorageProvider)
        # Install exact provider dependencies.
        selected._driver = FakeDriver
        selected._ready = False
        selected._schema_version = None
        selected._ready_lock = __import__("threading").RLock()
        selected._boundary_local = SimpleNamespace(connection=None)
        selected.config = PostgresConfig("127.0.0.1", 5432, "casino", "", "fixture")
        selected.connect = lambda **overrides: connection
        # Track the exact verifier connection without configuration or secret inputs.
        calls = []
        # Return one exact clean schema-five state.
        verifier = lambda candidate: calls.append(candidate) or SimpleNamespace(current_version=5, initialized=True, status="clean")
        # Replace only the migration-owned public seam.
        with mock.patch.object(provider, "verify_runtime_compatibility", verifier):
            # Exercise first-use and cached readiness.
            selected.ensure_ready()
            selected.ensure_ready()
        # Require one call with only the exact connection object.
        self.assertEqual(calls, [connection])
        # Require clean cached version and unconditional lease cleanup.
        self.assertEqual((selected._ready, selected._schema_version, connection.rollback_calls, connection.close_calls), (True, 5, 1, 1))

    # Prove native errors are fixed and caller exceptions retain identity.
    def test_database_error_translation_is_fixed_and_callbacks_are_preserved(self) -> None:
        # Build one modeled operation connection.
        connection = ScriptedConnection(ScriptedCursor())
        # Build production provider state around it.
        selected = _provider_with_connection(connection)
        # Require fixed integrity-conflict text without native detail.
        with self.assertRaisesRegex(ConflictError, "^PostgreSQL storage conflicts with current state$"):
            # Translate one synthetic constraint error.
            selected._raise_database_error(FakeIntegrityError("secret constraint"))
        # Require fixed general availability text without native detail.
        with self.assertRaisesRegex(ConflictError, "^PostgreSQL storage is unavailable$"):
            # Translate one synthetic connector error.
            selected._raise_database_error(FakeDatabaseError("secret SQL and target"))
        # Create one caller-owned exception instance.
        caller_failure = RuntimeError("caller-owned")
        # Preserve exact exception identity through rollback and close.
        with self.assertRaises(RuntimeError) as raised:
            # Enter one production write transaction.
            with selected._database_cursor(commit=True):
                # Raise the exact caller-owned object.
                raise caller_failure
        # Require identity, rollback, and unconditional cleanup.
        self.assertIs(raised.exception, caller_failure)
        self.assertEqual((connection.rollback_calls, connection.close_calls, connection.commit_calls), (1, 1, 0))

    # Prove one wallet action uses FOR UPDATE, JSONB, RETURNING, and atomic commit.
    def test_ledger_transaction_is_atomic_and_sequence_bound(self) -> None:
        # Script one locked wallet and one returned append identity.
        cursor = ScriptedCursor(fetchone_rows=[{"player_id": "p1", "balance": Decimal("10.00")}, {"sequence_id": 7}])
        # Build one operation connection and provider.
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Execute one cents-safe debit.
        event = selected.transact_ledger("p1", -2.5, "BET", game="roulette", round_id="r1", details={"kind": "inside"})
        # Require the exact public transition.
        self.assertEqual((event["amount"], event["balance_before"], event["balance_after"]), (-2.5, 10.0, 7.5))
        # Require one commit, no rollback, and unconditional close.
        self.assertEqual((connection.commit_calls, connection.rollback_calls, connection.close_calls), (1, 0, 1))
        # Inspect the complete executed SQL sequence.
        statements = [statement for statement, _parameters in cursor.executed]
        # Require row locking and explicit append identity.
        self.assertIn("FOR UPDATE", statements[0])
        self.assertIn("CAST(%s AS JSONB)", statements[-1])
        self.assertTrue(statements[-1].endswith("RETURNING sequence_id"))

    # Prove insufficient funds rolls back without issuing wallet update or append.
    def test_insufficient_funds_rolls_back_without_partial_state(self) -> None:
        # Script one locked wallet below the requested debit.
        cursor = ScriptedCursor(fetchone_rows=[{"player_id": "p1", "balance": Decimal("1.00")}])
        # Build one operation connection and provider.
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Require the public insufficient-funds category.
        with self.assertRaises(InsufficientFundsError):
            # Attempt an overdraw.
            selected.transact_ledger("p1", -2, "BET")
        # Require only the locking SELECT and no update/insert.
        self.assertEqual(len(cursor.executed), 1)
        # Require rollback and unconditional close without commit.
        self.assertEqual((connection.commit_calls, connection.rollback_calls, connection.close_calls), (0, 1, 1))

    # Prove document update materializes once, locks, validates, and publishes atomically.
    def test_document_update_uses_on_conflict_row_lock_and_jsonb(self) -> None:
        # Script the canonical existing JSONB document.
        cursor = ScriptedCursor(fetchone_rows=[{"payload_json": {"count": 2}}])
        # Build one operation connection and provider.
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Increment through the real provider callback boundary.
        updated = selected.update_document("settings/demo.json", lambda current: {"count": current["count"] + 1}, {"count": 0})
        # Require exact callback output and one commit.
        self.assertEqual(updated, {"count": 3})
        self.assertEqual((connection.commit_calls, connection.close_calls), (1, 1))
        # Inspect fixed SQL order.
        statements = [statement for statement, _parameters in cursor.executed]
        # Require insert-if-absent, row lock, and JSONB replacement.
        self.assertIn("ON CONFLICT (document_key) DO NOTHING", statements[0])
        self.assertTrue(statements[1].endswith("FOR UPDATE"))
        self.assertIn("CAST(%s AS JSONB)", statements[2])

    # Prove document missing/default, strict, existence, Unicode, and large writes.
    def test_document_read_write_and_strict_boundaries_preserve_jsonb_shapes(self) -> None:
        # Build one large nested Unicode payload.
        payload = {"message": "добро пожаловать", "nested": {"rows": list(range(2048))}}
        # Script missing read, existing read, existence, strict read, and write operations.
        missing = ScriptedConnection(ScriptedCursor(fetchone_rows=[None]))
        existing = ScriptedConnection(ScriptedCursor(fetchone_rows=[{"payload_json": payload}]))
        present = ScriptedConnection(ScriptedCursor(fetchone_rows=[{"present": 1}]))
        strict = ScriptedConnection(ScriptedCursor(fetchone_rows=[{"payload_json": {"enabled": True}}]))
        write = ScriptedConnection(ScriptedCursor())
        # Supply one operation-scoped lease per public call.
        selected = _provider_with_connection(missing)
        connections = [missing, existing, present, strict, write]
        selected.connect = lambda **overrides: connections.pop(0)
        # Exercise every provider document read/write boundary.
        default_value = selected.read_document("missing", lambda: {"default": True})
        stored_value = selected.read_document("large", {})
        exists = selected.document_exists("large")
        strict_value = selected.read_document_strict("security", {}, validator=lambda value: value == {"enabled": True})
        selected.write_document("large", payload)
        # Require exact missing/default and decoded JSONB results.
        self.assertEqual((default_value, stored_value, exists, strict_value), ({"default": True}, payload, True, {"enabled": True}))
        # Require one canonical JSONB upsert with Unicode retained in parameters.
        statement, parameters = write.operation_cursor.executed[0]
        self.assertIn("ON CONFLICT (document_key) DO UPDATE", statement)
        self.assertIn("добро пожаловать", parameters[1])
        # Require one committed write and read-only cleanup for every read.
        self.assertEqual((write.commit_calls, missing.rollback_calls, existing.rollback_calls, present.rollback_calls, strict.rollback_calls), (1, 1, 1, 1, 1))

    # Prove wallet normalization scans all rows under locks without read-side mutation.
    def test_wallet_normalization_clean_scan_is_read_only(self) -> None:
        # Script two exact-cent PostgreSQL NUMERIC wallets.
        rows = [{"player_id": "p1", "balance": Decimal("1.00")}, {"player_id": "p2", "balance": Decimal("2.50")}]
        cursor = ScriptedCursor(fetchall_rows=[rows])
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Execute the explicit scan-only path.
        report = selected.normalize_wallet_balances(apply=False)
        # Require bounded clean evidence without identities or values.
        self.assertEqual(report, {"provider": "postgres", "checked": 2, "residue_count": 0, "normalized_count": 0, "clean": True, "applied": False})
        # Require deterministic complete row locking and rollback rather than commit.
        self.assertTrue(cursor.executed[0][0].endswith("ORDER BY player_id FOR UPDATE"))
        self.assertEqual((connection.commit_calls, connection.rollback_calls, connection.close_calls), (0, 1, 1))

    # Prove player reads validate money and preserve deterministic ordering.
    def test_player_load_and_point_read_preserve_public_shapes(self) -> None:
        # Build two exact NUMERIC rows in reverse input identity order.
        rows = [
            {"player_id": "p1", "display_name": "One", "player_type": "human", "balance": Decimal("12.34"), "created_at": "t1", "updated_at": "t2", "status": "active"},
            {"player_id": "p2", "display_name": "Two", "player_type": "bot", "balance": Decimal("0.00"), "created_at": "t1", "updated_at": "t2", "status": "active"},
        ]
        # Script one full read and one point read on separate operation connections.
        load_connection = ScriptedConnection(ScriptedCursor(fetchall_rows=[rows]))
        point_connection = ScriptedConnection(ScriptedCursor(fetchone_rows=[rows[1]]))
        # Build one provider and supply each request lease in call order.
        selected = _provider_with_connection(load_connection)
        connections = [load_connection, point_connection]
        selected.connect = lambda **overrides: connections.pop(0)
        # Load the complete validated document.
        state = selected.load_players(lambda: {"players": []})
        # Resolve one indexed player without invoking the default factory.
        player = selected.get_player("p2", lambda: (_ for _ in ()).throw(AssertionError("default called")))
        # Require exact public money and type projections.
        self.assertEqual([(row["player_id"], row["balance"]) for row in state["players"]], [("p1", 12.34), ("p2", 0.0)])
        self.assertEqual((player["player_id"], player["type"], player["balance"]), ("p2", "bot", 0.0))
        # Require read-only rollback and cleanup for both operations.
        self.assertEqual((load_connection.rollback_calls, point_connection.rollback_calls, load_connection.close_calls, point_connection.close_calls), (1, 1, 1, 1))

    # Prove bootstrap and deterministic ensure never overwrite an existing wallet.
    def test_bootstrap_and_ensure_use_primary_key_conflict_boundaries(self) -> None:
        # Define one complete deterministic player candidate.
        candidate = {"player_id": "p1", "display_name": "One", "type": "human", "balance": 5, "created_at": "t1", "updated_at": "t1", "status": "active"}
        # Script bootstrap with no result rows.
        bootstrap_cursor = ScriptedCursor()
        bootstrap_connection = ScriptedConnection(bootstrap_cursor)
        # Script ensure with the compatible resulting row.
        durable = {"player_id": "p1", "display_name": "One", "player_type": "human", "balance": Decimal("5.00"), "created_at": "t1", "updated_at": "t1", "status": "active"}
        ensure_cursor = ScriptedCursor(fetchone_rows=[durable])
        ensure_connection = ScriptedConnection(ensure_cursor)
        # Supply the two independent operation leases.
        selected = _provider_with_connection(bootstrap_connection)
        connections = [bootstrap_connection, ensure_connection]
        selected.connect = lambda **overrides: connections.pop(0)
        # Insert missing bootstrap rows once.
        selected.bootstrap_players({"players": [candidate]})
        # Insert-or-read the same deterministic identity.
        result = selected.ensure_player(candidate)
        # Require both insert statements to preserve existing state.
        self.assertIn("ON CONFLICT (player_id) DO NOTHING", bootstrap_cursor.executed[0][0])
        self.assertIn("ON CONFLICT (player_id) DO NOTHING", ensure_cursor.executed[0][0])
        # Require ensure to lock and return the compatible durable row.
        self.assertTrue(ensure_cursor.executed[1][0].endswith("FOR UPDATE"))
        self.assertEqual((result["player_id"], result["balance"]), ("p1", 5.0))
        # Require one atomic commit per provider operation.
        self.assertEqual((bootstrap_connection.commit_calls, ensure_connection.commit_calls), (1, 1))

    # Prove caller-owned player updates execute once under the row lock.
    def test_update_player_preserves_callback_and_row_lock(self) -> None:
        # Script one valid durable player row.
        row = {"player_id": "p1", "display_name": "One", "player_type": "human", "balance": Decimal("5.00"), "created_at": "t1", "updated_at": "t1", "status": "active"}
        cursor = ScriptedCursor(fetchone_rows=[row])
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Track exact callback execution count.
        calls = []
        # Update the detached public shape once.
        updated = selected.update_player("p1", lambda player: (calls.append(player["player_id"]), player.update(balance=Decimal("7.25"))))
        # Require exact callback identity, cents result, and atomic commit.
        self.assertEqual((calls, updated["balance"], connection.commit_calls), (["p1"], 7.25, 1))
        # Require the read lock before the update statement.
        self.assertTrue(cursor.executed[0][0].endswith("FOR UPDATE"))
        self.assertTrue(cursor.executed[1][0].startswith("UPDATE casino_players"))

    # Prove exactly-once ledger replay returns the immutable original event.
    def test_ledger_once_replay_does_not_mutate_wallet(self) -> None:
        # Build exact committed action metadata for the requested semantic identity.
        fingerprint = provider._action_fingerprint(-1.0, "BET", "roulette", "r1", {"kind": "inside"})
        details = provider._action_details({"kind": "inside"}, "a1", fingerprint)
        # Script the locked wallet and existing immutable ledger event.
        existing = {"ledger_id": "led_1", "ts": "t1", "player_id": "p1", "game": "roulette", "round_id": "r1", "transaction_type": "BET", "amount": Decimal("-1.00"), "balance_before": Decimal("5.00"), "balance_after": Decimal("4.00"), "details_json": details}
        cursor = ScriptedCursor(fetchone_rows=[{"player_id": "p1", "balance": Decimal("4.00")}, existing])
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Execute the same storage action identity.
        event, replayed = selected.transact_ledger_once("p1", -1, "BET", "a1", game="roulette", round_id="r1", details={"kind": "inside"})
        # Require immutable replay without another wallet update or insert.
        self.assertTrue(replayed)
        self.assertEqual((event["ledger_id"], event["balance_after"], len(cursor.executed)), ("led_1", 4.0, 2))
        # Require the read-only replay transaction to commit and release its lock.
        self.assertEqual((connection.commit_calls, connection.rollback_calls), (1, 0))

    # Prove recent ledger and economics use one bounded chronological snapshot.
    def test_recent_ledger_and_economics_are_bounded_and_chronological(self) -> None:
        # Build two newest-first database rows.
        newest = {"ledger_id": "led_2", "ts": "t2", "player_id": "p1", "game": "roulette", "round_id": "r2", "transaction_type": "PAYOUT", "amount": Decimal("2.00"), "balance_before": Decimal("4.00"), "balance_after": Decimal("6.00"), "details_json": {}}
        oldest = {"ledger_id": "led_1", "ts": "t1", "player_id": "p1", "game": "roulette", "round_id": "r1", "transaction_type": "BET", "amount": Decimal("-1.00"), "balance_before": Decimal("5.00"), "balance_after": Decimal("4.00"), "details_json": {}}
        # Supply equivalent windows for direct read and aggregate calls.
        first = ScriptedConnection(ScriptedCursor(fetchall_rows=[[newest, oldest]]))
        second = ScriptedConnection(ScriptedCursor(fetchall_rows=[[newest, oldest]]))
        selected = _provider_with_connection(first)
        connections = [first, second]
        selected.connect = lambda **overrides: connections.pop(0)
        # Read direct chronology and one game aggregate.
        events = selected.read_ledger_recent(limit=2)
        economics = selected.ledger_economics(2, game="roulette", recent=2)
        # Require oldest-first compatibility and exact signed totals.
        self.assertEqual([event["ledger_id"] for event in events], ["led_1", "led_2"])
        self.assertEqual(economics["games"], [{"game": "roulette", "wagered": 1.0, "returned": 2.0, "events": 2}])
        self.assertEqual([event["ledger_id"] for event in economics["recent"]], ["led_1", "led_2"])

    # Prove history append allocates a sequence and reads chronological rows.
    def test_history_append_and_recent_preserve_schema_and_order(self) -> None:
        # Define one complete provider-neutral history event.
        event = {"timestamp": "t1", "game": "roulette", "round_id": "r1", "player_id": "p1", "bet_type": "inside", "bet_label": "red", "amount": 1.0, "outcome": "win", "payout": 2.0, "balance_after": 6.0, "details_json": {"number": 1}, "schema_version": "1"}
        # Script append identity and newest-first read rows.
        append_connection = ScriptedConnection(ScriptedCursor(fetchone_rows=[{"sequence_id": 3}]))
        stored = {**event, "amount": Decimal("1.00"), "payout": Decimal("2.00"), "balance_after": Decimal("6.00"), "details_json": {"number": 1}}
        read_connection = ScriptedConnection(ScriptedCursor(fetchall_rows=[[stored]]))
        selected = _provider_with_connection(append_connection)
        connections = [append_connection, read_connection]
        selected.connect = lambda **overrides: connections.pop(0)
        # Append and read the exact game history.
        selected.append_history(event)
        rows = selected.recent_history(limit=5, game="roulette")
        # Require explicit sequence allocation and stable CSV-compatible details text.
        self.assertTrue(append_connection.operation_cursor.executed[0][0].endswith("RETURNING sequence_id"))
        self.assertEqual((rows[0]["amount"], rows[0]["details_json"], append_connection.commit_calls), (1.0, '{"number": 1}', 1))

    # Prove reset advances the lifecycle, clears only mutable rows, and returns ready.
    def test_reset_transaction_uses_target_lock_epoch_and_mutable_table_order(self) -> None:
        # Script advisory acquire, epoch, compare-set, final epoch, ready compare-set, and release.
        cursor = ScriptedCursor(fetchone_rows=[{"acquired": True}, {"state_id": 1, "current_epoch": 1, "phase": "ready"}, {"state_id": 1}, {"state_id": 1, "current_epoch": 2, "phase": "resetting"}, {"state_id": 1}, {"released": True}])
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Return exact schema-five state for both reset verification points.
        clean = SimpleNamespace(initialized=True, status="clean", current_version=5)
        with mock.patch.object(provider, "verify_runtime_compatibility", return_value=clean):
            # Execute direct reset with no bootstrap body.
            selected.reset()
        # Require phase-one and phase-two commits plus final lease cleanup.
        self.assertEqual((connection.commit_calls, connection.close_calls), (2, 1))
        # Extract exact executed SQL order.
        statements = [statement for statement, _parameters in cursor.executed]
        # Require nonblocking target lock and every mutable table deletion.
        self.assertEqual(statements[0], "SELECT pg_try_advisory_lock(%s) AS acquired")
        for table in ("casino_sessions", "casino_ledger", "casino_history", "casino_documents", "casino_players"):
            # Bind each provider-owned mutable table to reset deletion.
            self.assertIn(f"DELETE FROM {table}", statements)
        # Require the lifecycle return to ready and exact unlock.
        self.assertTrue(any("SET phase = 'ready'" in statement for statement in statements))
        self.assertEqual(statements[-1], "SELECT pg_advisory_unlock(%s) AS released")

    # Prove reset body failures retain identity and leave the durable phase unavailable.
    def test_reset_body_failure_preserves_original_and_does_not_publish_ready(self) -> None:
        # Script acquisition, phase-one epoch transition, and advisory release.
        cursor = ScriptedCursor(fetchone_rows=[{"acquired": True}, {"state_id": 1, "current_epoch": 1, "phase": "ready"}, {"state_id": 1}, {"released": True}])
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        clean = SimpleNamespace(initialized=True, status="clean", current_version=5)
        # Create one exact caller-owned failure object.
        failure = RuntimeError("caller bootstrap failed")
        # Preserve identity through rollback and advisory cleanup.
        with mock.patch.object(provider, "verify_runtime_compatibility", return_value=clean), self.assertRaises(RuntimeError) as raised:
            # Enter the complete reset boundary.
            with selected.reset_transaction():
                # Fail after durable phase one.
                raise failure
        # Require the exact original object and no ready publication.
        self.assertIs(raised.exception, failure)
        self.assertFalse(any("SET phase = 'ready'" in statement for statement, _parameters in cursor.executed))
        # Require only phase-one commit; resetting remains fail closed.
        self.assertEqual(connection.commit_calls, 1)

    # Prove state visibility takes and releases the matching shared target lock.
    def test_state_visibility_uses_shared_target_advisory_lock(self) -> None:
        # Script exact shared acquisition and release confirmations.
        cursor = ScriptedCursor(fetchone_rows=[{"acquired": True}, {"released": True}])
        connection = ScriptedConnection(cursor)
        selected = _provider_with_connection(connection)
        # Enter and leave the direct-state visibility boundary.
        with selected.state_visibility_transaction() as visible:
            # Require the exact provider identity inside the boundary.
            self.assertIs(visible, selected)
        # Require matched shared lock/unlock statements and unconditional close.
        statements = [statement for statement, _parameters in cursor.executed]
        self.assertEqual(statements, ["SELECT pg_try_advisory_lock_shared(%s) AS acquired", "SELECT pg_advisory_unlock_shared(%s) AS released"])
        self.assertEqual(connection.close_calls, 1)

    # Prove every production execute call uses a literal statement and bound placeholders.
    def test_sql_is_literal_parameterized_and_postgres_native(self) -> None:
        # Parse the exact tracked provider source.
        tree = ast.parse(PROVIDER_PATH.read_text(encoding="utf-8"))
        # Collect every cursor execute call.
        execute_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "execute"]
        # Require a substantial complete provider SQL inventory.
        self.assertGreaterEqual(len(execute_calls), 30)
        # Require every SQL argument to be a literal constant, never interpolation.
        self.assertTrue(all(node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) for node in execute_calls))
        # Join only the literal SQL text for dialect assertions.
        sql = "\n".join(node.args[0].value for node in execute_calls)
        # Reject MySQL-only syntax and named interpolation.
        for forbidden in ("INSERT IGNORE", "ON DUPLICATE KEY", "GET_LOCK", "RELEASE_LOCK", "BINARY ", "%("):
            # Require the forbidden dialect token to remain absent.
            self.assertNotIn(forbidden, sql)
        # Require PostgreSQL conflict, JSONB, row-lock, and sequence idioms.
        for required in ("ON CONFLICT", "CAST(%s AS JSONB)", "FOR UPDATE", "RETURNING sequence_id"):
            # Bind each accepted dialect feature to the tracked source.
            self.assertIn(required, sql)


# Run the focused suite when invoked directly.
if __name__ == "__main__":
    # Execute unittest with standard failure semantics.
    unittest.main()
