# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""PostgreSQL native session parity and boundary tests. (STORAGE-023, TEST-255)"""

# Import copy support so the transaction model can restore exact rollback snapshots.
import copy
# Import Python syntax inspection for exact literal SQL enforcement.
import ast
# Import source inspection for connector and SQL-boundary assertions.
import inspect
# Import JSON encoding for the host-provider canonical JSON seam.
import json
# Import the explicit live-test marker and disposable target settings.
import os
# Import thread synchronization for concurrent creator coverage.
import threading
# Import unittest for central-runner-compatible assertions.
import unittest
# Import one bounded worker pool for simultaneous session creation.
from concurrent.futures import ThreadPoolExecutor
# Import context-manager support for the host transaction seam.
from contextlib import contextmanager
# Import fixed UTC instants for deterministic expiry assertions.
from datetime import datetime, timezone

# Import the complete PostgreSQL session module for fixed-constant and source checks.
from casino.core.storage import sessions_postgres as sessions_postgres_module
# Import the production lifecycle mixin exercised by the transaction-faithful model.
from casino.core.storage.sessions_postgres import PostgresSessionMixin
# Import the fixed public conflict boundary used by malformed session evidence.
from casino.errors import ConflictError, ValidationError


# Return one complete compatible session with deterministic caller authority.
def _session(index: int, user_id: str, *, token: str | None = None, status: str = "active", expires_at: str = "2026-09-01T00:00:00.000Z") -> dict:
    # Derive one stable bearer when the caller does not select it explicitly.
    bearer = token or f"postgres-session-token-{index}"
    # Stagger activity so cap eviction has an unambiguous oldest row.
    timestamp = f"2026-08-20T00:00:{index:02d}.000Z"
    # Return the complete durable-compatible auth-layer shape.
    return {"session_id": f"postgres-session-{index}", "user_id": user_id, "token": bearer, "csrf_token": f"postgres-csrf-{index}".ljust(32, "x"), "generation": 1, "status": status, "created_at": timestamp, "updated_at": timestamp, "expires_at": expires_at, "client": "postgres-provider-parity", "auth_method": "local"}


# Exercise production PostgreSQL lifecycle algorithms over a transaction-faithful row model.
class _ModelPostgresSessions(PostgresSessionMixin):
    # Initialize one empty clean native registry with completed import authority.
    def __init__(self) -> None:
        # Retain the exact clean native schema selected by the provider readiness gate.
        self._schema_version = 5
        # Store one detached durable row per bearer digest.
        self.rows: dict[str, dict] = {}
        # Serialize every compound operation like PostgreSQL row locks do.
        self.lock = threading.RLock()
        # Model the completed import marker required before ordinary mutation.
        self.marker_payload: dict | None = {"schema_version": 1, "status": "complete"}
        # Retain marker and registry selection order for lock-order assertions.
        self.events: list[str] = []
        # Retain every host transaction policy requested by the mixin.
        self.commit_flags: list[bool] = []
        # Allow planner rejection tests to fail before opening a transaction.
        self.planner_active = False

    # Model successful checksum-bound readiness without external connector access.
    def ensure_ready(self) -> None:
        # Return because this isolated model already carries exact schema identity.
        return None

    # Reject session visibility and mutation from an active pure planner.
    def _reject_planner_mutation(self) -> None:
        # Match the provider-neutral planner purity boundary.
        if self.planner_active:
            # Raise before a transaction or row operation starts.
            raise ValidationError("Game action planner must be side-effect free")

    # Serialize JSON exactly as the host PostgreSQL provider does.
    @staticmethod
    def _canonical_json(value) -> str:
        # Return compact stable JSON suitable for explicit JSONB casts.
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    # Model one atomic read or write boundary with rollback on any BaseException.
    @contextmanager
    def _database_cursor(self, *, commit: bool = False):
        # Serialize the complete callback lifetime across concurrent creators.
        with self.lock:
            # Snapshot all modeled authority before caller code can mutate it.
            prior_rows = copy.deepcopy(self.rows)
            # Snapshot the marker independently from session rows.
            prior_marker = copy.deepcopy(self.marker_payload)
            # Record the exact commit policy requested by the production mixin.
            self.commit_flags.append(commit)
            try:
                # Yield the model as both inert connection and cursor tokens.
                yield self, self
            except BaseException:
                # Restore every modeled row exactly as transaction rollback would.
                self.rows = prior_rows
                # Restore importer authority after any failed operation.
                self.marker_payload = prior_marker
                # Preserve the original caller exception and traceback.
                raise

    # Model only the fixed registry-marker statement used by ordinary operations.
    def execute(self, statement: str, parameters: tuple | None = None) -> None:
        # Require the marker row-lock query and its bound constant identity.
        if statement == "SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE":
            # Bind the exact provider-private completion marker.
            assert parameters == (sessions_postgres_module._POSTGRES_SESSION_IMPORT_MARKER,)
            # Record stable marker ownership before a complete registry scan.
            self.events.append("marker")
            # Return after accepting the fixed modeled query.
            return
        # Refuse every unmodeled statement so tests cannot silently bypass coverage.
        raise AssertionError(statement)

    # Return the modeled marker through psycopg dict-row semantics.
    def fetchone(self) -> dict | None:
        # Preserve true absence separately from malformed marker payloads.
        return None if self.marker_payload is None else {"payload_json": copy.deepcopy(self.marker_payload)}

    # Select detached matching rows using the production predicate contract.
    def _select_postgres_sessions(self, _cursor, *, token_digest=None, session_id=None, user_id=None, for_update=False):
        # Record complete registry scans separately for marker-order evidence.
        if token_digest is None and session_id is None and user_id is None:
            # Append one registry event after production acquired the marker.
            self.events.append("registry")
        # Copy every row before filtering so callers cannot mutate durable authority.
        rows = [copy.deepcopy(row) for row in self.rows.values()]
        # Apply the unique token predicate when supplied.
        if token_digest is not None:
            # Retain only the exact bearer digest.
            rows = [row for row in rows if row["token_digest"] == token_digest]
        # Apply the opaque primary-key predicate when supplied.
        if session_id is not None:
            # Retain only the exact session identity.
            rows = [row for row in rows if row["session_id"] == session_id]
        # Apply the account predicate when supplied.
        if user_id is not None:
            # Retain only rows owned by the selected account.
            rows = [row for row in rows if row["user_id"] == user_id]
        # Return deterministic token order for complete scans.
        return sorted(rows, key=lambda row: row["token_digest"])

    # Insert one unique detached row inside the held model transaction.
    def _insert_postgres_session(self, _cursor, row: dict) -> None:
        # Reject digest or opaque-id collisions like PostgreSQL unique constraints.
        if row["token_digest"] in self.rows or any(existing["session_id"] == row["session_id"] for existing in self.rows.values()):
            # Surface the fixed recovery result without connector details.
            raise ConflictError("Session storage requires operator recovery")
        # Publish a detached row under its bearer digest.
        self.rows[row["token_digest"]] = copy.deepcopy(row)

    # Replace one selected row and optional rotated digest atomically.
    def _update_postgres_session(self, _cursor, prior: dict, row: dict) -> None:
        # Remove the exact predecessor selected under the transaction lock.
        removed = self.rows.pop(prior["token_digest"], None)
        # Refuse a missing predecessor without issuing replacement authority.
        if removed is None:
            # Match the production recovery boundary.
            raise ConflictError("Session storage requires operator recovery")
        # Reject replacement collision while restoring the predecessor.
        if row["token_digest"] in self.rows:
            # Restore original authority before surfacing the collision.
            self.rows[prior["token_digest"]] = removed
            # Match the production unique-index boundary.
            raise ConflictError("Session storage requires operator recovery")
        # Publish the complete detached replacement.
        self.rows[row["token_digest"]] = copy.deepcopy(row)

    # Delete one exact selected row under the transaction lock.
    def _delete_postgres_session(self, _cursor, row: dict) -> None:
        # Remove only the digest-owned model row.
        removed = self.rows.pop(row["token_digest"], None)
        # Refuse missing or ambiguous deletion evidence.
        if removed is None:
            # Match the production fixed recovery outcome.
            raise ConflictError("Session storage requires operator recovery")


# Model the fixed SQL boundaries used by the one-shot retired-document importer.
class _ImportModelPostgresSessions(_ModelPostgresSessions):
    # Initialize an absent marker and one optional aggregate source document.
    def __init__(self, source: dict | None) -> None:
        # Reuse native row and transaction ownership from the lifecycle model.
        super().__init__()
        # Start without completed import authority.
        self.marker_payload = None
        # Retain the caller-selected retired aggregate document.
        self.source = copy.deepcopy(source)
        # Track the result category selected by the latest statement.
        self.pending_result = "none"
        # Track whether the retired source was deleted after publication.
        self.source_deleted = False

    # Model only the fixed control, marker, source, and publication statements.
    def execute(self, statement: str, parameters: tuple | None = None) -> None:
        # Select the stable schema singleton used while the marker is absent.
        if statement == "SELECT current_version FROM casino_schema_migration_state WHERE state_id = 1 FOR UPDATE":
            # Select the exact dict-row control result for the next fetch.
            self.pending_result = "state"
            # Return without changing modeled authority.
            return
        # Select the exact optional marker row by its bound private identity.
        if statement == "SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE" and parameters == (sessions_postgres_module._POSTGRES_SESSION_IMPORT_MARKER,):
            # Select the marker result for the next fetch.
            self.pending_result = "marker"
            # Record stable lock order for later assertions.
            self.events.append("marker")
            # Return without changing modeled authority.
            return
        # Select the caller-supplied retired document after the marker decision.
        if statement == "SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE":
            # Select the optional aggregate source for the next fetch.
            self.pending_result = "source"
            # Return without changing modeled authority.
            return
        # Insert the completed marker with an explicitly cast bound JSONB payload.
        if statement == "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, CAST(%s AS JSONB), %s)":
            # Require publication under the exact private marker key.
            assert parameters is not None and parameters[0] == sessions_postgres_module._POSTGRES_SESSION_IMPORT_MARKER
            # Decode the host-canonical JSON into modeled JSONB authority.
            self.marker_payload = json.loads(parameters[1])
            # Return after staging the marker write.
            return
        # Delete the previously selected retired aggregate document.
        if statement == "DELETE FROM casino_documents WHERE document_key = %s":
            # Record exact retirement and one affected row.
            self.source_deleted = True
            # Expose one successful deletion through the DB-API field.
            self.rowcount = 1
            # Return after staging deletion.
            return
        # Refuse every unreviewed statement so import tests stay source-bound.
        raise AssertionError(statement)

    # Return one dict-row result selected by the latest fixed statement.
    def fetchone(self) -> dict | None:
        # Return the exact migration singleton identity.
        if self.pending_result == "state":
            # Expose only the sanitized native version field.
            return {"current_version": 5}
        # Return the current optional import marker.
        if self.pending_result == "marker":
            # Preserve true marker absence separately from malformed payloads.
            return None if self.marker_payload is None else {"payload_json": copy.deepcopy(self.marker_payload)}
        # Return the optional retired aggregate source.
        if self.pending_result == "source":
            # Preserve true source absence for lazy default evaluation.
            return None if self.source is None else {"payload_json": copy.deepcopy(self.source)}
        # Reject a fetch without a preceding modeled selection.
        raise AssertionError(self.pending_result)


# Capture SQL statements and row counts for direct helper boundary tests.
class _RecordingCursor:
    # Initialize one empty statement ledger and successful row count.
    def __init__(self) -> None:
        # Retain exact SQL and parameters in execution order.
        self.calls: list[tuple[str, tuple | None]] = []
        # Model one exact update or delete target by default.
        self.rowcount = 1
        # Supply caller-selected rows for selection validation.
        self.rows: list[dict] = []

    # Record one bound statement without executing a database operation.
    def execute(self, statement: str, parameters: tuple | None = None) -> None:
        # Append immutable call evidence for assertions.
        self.calls.append((statement, parameters))

    # Return detached configured rows through dict-row semantics.
    def fetchall(self) -> list[dict]:
        # Protect configured source rows from production validation mutation.
        return copy.deepcopy(self.rows)


# Bind the production mixin to one explicitly authorized disposable psycopg target.
class _LivePostgresSessions(PostgresSessionMixin):
    # Initialize one native-schema owner without importing psycopg for ordinary tests.
    def __init__(self) -> None:
        # Import the optional connector only after the explicit live-test marker is present.
        import psycopg
        # Import mapping-row construction to match the planned production provider.
        from psycopg.rows import dict_row
        # Retain the connector only inside this disposable live owner.
        self.driver = psycopg
        # Retain dict-row semantics for every runtime session query.
        self.dict_row = dict_row
        # Bind only the dedicated disposable target environment.
        self.options = {"host": os.environ["CASINO_POSTGRES_SESSION_HOST"], "port": int(os.environ["CASINO_POSTGRES_SESSION_PORT"]), "user": os.environ["CASINO_POSTGRES_SESSION_USER"], "password": os.environ.get("CASINO_POSTGRES_SESSION_PASSWORD", ""), "dbname": os.environ["CASINO_POSTGRES_SESSION_DATABASE"], "connect_timeout": 5}
        # Expose the exact migrated native version after the external runner succeeds.
        self._schema_version = 5

    # Model the production provider's successful checksum readiness result.
    def ensure_ready(self) -> None:
        # Return because the live harness applies and checks exact migration five first.
        return None

    # No action planner is active in this isolated provider test.
    def _reject_planner_mutation(self) -> None:
        # Return without changing connector or database state.
        return None

    # Serialize JSON exactly as the production PostgreSQL host provider.
    @staticmethod
    def _canonical_json(value) -> str:
        # Return stable compact ASCII JSON for explicit JSONB casting.
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    # Own one complete disposable read or write transaction.
    @contextmanager
    def _database_cursor(self, *, commit: bool = False):
        # Open one mapping-row connection to the explicitly disposable target.
        connection = self.driver.connect(**self.options, autocommit=False, row_factory=self.dict_row)
        try:
            # Open one dict-row cursor for the complete compound operation.
            cursor = connection.cursor()
            # Transfer control to the production session mixin.
            yield connection, cursor
            # Commit successful writes or end successful reads without retaining a snapshot.
            connection.commit() if commit else connection.rollback()
        except BaseException:
            # Roll back every partial write and row lock before preserving the exact failure.
            connection.rollback()
            # Preserve the original application or connector exception and traceback.
            raise
        finally:
            # Close the dedicated connection on every path.
            connection.close()


# Prove PostgreSQL sessions retain provider-neutral semantics and safe SQL ownership.
class PostgresSessionProviderTests(unittest.TestCase):
    # Exercise native SQL, JSONB, row locks, rotation, and cleanup on disposable PostgreSQL 16.
    def test_disposable_postgres_16_session_lifecycle(self) -> None:
        # Evaluate authorization when the managed runner has installed its temporary marker.
        if os.environ.get("CASINO_POSTGRES_SESSION_LIVE") != "CASINO-POSTGRES-1058-SESSION-LIVE":
            # Preserve listener-free default execution without freezing import-time environment.
            self.skipTest("PostgreSQL session live test is not authorized")
        # Construct one live owner only after the runtime guard verifies explicit authorization.
        provider = _LivePostgresSessions()
        # Publish the exact completed marker through the real one-shot importer.
        provider.import_legacy_sessions("data/auth/sessions.json", lambda: {"sessions": []})
        # Release eight real creators together to exercise marker row serialization.
        barrier = threading.Barrier(8)

        # Create and resolve one independent bearer through actual PostgreSQL SQL.
        def create(index: int) -> str:
            # Wait until the complete bounded cohort is ready.
            barrier.wait(timeout=10)
            # Commit one native row under non-evicting caps.
            created = provider.create_session(_session(index, "shared-live-user"), 8, 16)
            # Resolve the exact bearer through the native unique index.
            return provider.get_session_by_token(created["token"])["session_id"]

        # Execute all creators concurrently against real PostgreSQL row locks.
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Materialize every result and surface each connector failure.
            created_ids = list(executor.map(create, range(8)))
        # Require all eight independent rows to survive.
        self.assertEqual(set(created_ids), {f"postgres-session-{index}" for index in range(8)})
        # Rotate one credential through a real JSONB and unique-index update.
        rotated = provider.rotate_session("postgres-session-0", "postgres-session-token-0", 1, "postgres-live-rotated", "postgres-live-csrf".ljust(32, "x"), "2026-08-20T01:00:00.000Z")
        # Require one exact generation advance and replacement bearer.
        self.assertEqual((rotated["generation"], rotated["token"]), (2, "postgres-live-rotated"))
        # Revoke all shared account sessions and count every active transition.
        self.assertEqual(provider.revoke_sessions_for_user("shared-live-user", "2026-08-20T02:00:00.000Z"), 8)
        # Sweep every revoked row through marker-before-registry locking.
        self.assertEqual(provider.expire_sessions(datetime(2026, 8, 21, tzinfo=timezone.utc), 16), 8)
        # Require a completely empty native registry after cleanup.
        self.assertEqual(provider.list_sessions(), [])

    # Prove one-shot import validates, publishes, retires, and then remains idempotent.
    def test_legacy_import_is_atomic_and_idempotent(self) -> None:
        # Build one aggregate source containing a valid auth-layer session.
        source = {"sessions": [_session(1, "legacy-user")]}
        # Construct an importer model with no completion marker.
        provider = _ImportModelPostgresSessions(source)
        # Track whether the default factory is incorrectly consulted.
        factory_calls = {"value": 0}

        # Return a reviewed empty aggregate only when the source is genuinely absent.
        def default_factory() -> dict:
            # Count evaluation so present-source and completed-marker paths stay observable.
            factory_calls["value"] += 1
            # Return the compatible empty container.
            return {"sessions": []}

        # Import the retired aggregate under one committed provider transaction.
        provider.import_legacy_sessions("data/auth/sessions.json", default_factory)
        # Require source authority to retire only after destination and marker publication.
        self.assertTrue(provider.source_deleted)
        # Require one exact completed marker and no unnecessary default evaluation.
        self.assertEqual((provider.marker_payload, factory_calls["value"]), ({"schema_version": 1, "status": "complete"}, 0))
        # Resolve the imported bearer through the production digest path.
        self.assertEqual(provider.get_session_by_token("postgres-session-token-1")["session_id"], "postgres-session-1")
        # Run the importer again with a factory that must remain unreachable.
        provider.import_legacy_sessions("data/auth/sessions.json", default_factory)
        # Require stable authority and no factory call after completed import.
        self.assertEqual((len(provider.rows), factory_calls["value"]), (1, 0))

    # Prove cap, rotation, revocation, deletion, and expiry over the production algorithm.
    def test_complete_lifecycle_is_native_and_provider_neutral(self) -> None:
        # Construct one transaction-faithful native provider model.
        provider = _ModelPostgresSessions()
        # Create three account sessions under a two-session account cap.
        provider.create_session(_session(1, "user-a"), 2, 8)
        # Retain the second active account credential.
        provider.create_session(_session(2, "user-a"), 2, 8)
        # Evict the deterministic oldest account row with the third credential.
        provider.create_session(_session(3, "user-a"), 2, 8)
        # Require the oldest bearer to stop resolving.
        self.assertIsNone(provider.get_session_by_token("postgres-session-token-1"))
        # Require newest-first bounded account inventory without plaintext bearers.
        listed = provider.list_sessions("user-a", limit=2)
        # Bind deterministic order and durable credential stripping.
        self.assertEqual(([row["session_id"] for row in listed], any("token" in row for row in listed)), (["postgres-session-3", "postgres-session-2"], False))
        # Rotate one bearer and CSRF pair through generation one.
        rotated = provider.rotate_session("postgres-session-2", "postgres-session-token-2", 1, "postgres-rotated-token-2", "postgres-rotated-csrf".ljust(32, "x"), "2026-08-20T01:00:00.000Z")
        # Require exact generation advance and one-time replacement authority.
        self.assertEqual((rotated["generation"], rotated["token"]), (2, "postgres-rotated-token-2"))
        # Require predecessor and stale generation attempts to miss generically.
        self.assertIsNone(provider.get_session_by_token("postgres-session-token-2"))
        # Preserve the current replacement on a stale compare-and-swap.
        self.assertIsNone(provider.rotate_session("postgres-session-2", "postgres-rotated-token-2", 1, "stale", "stale-csrf".ljust(32, "x"), "2026-08-20T01:01:00.000Z"))
        # Revoke the replacement exactly once.
        self.assertEqual(provider.revoke_session_by_token("postgres-rotated-token-2", "2026-08-20T01:02:00.000Z"), 1)
        # Require repeat revocation to remain idempotent.
        self.assertEqual(provider.revoke_session_by_id("postgres-session-2", "2026-08-20T01:03:00.000Z"), 0)
        # Sweep the revoked row while retaining the active newest row.
        self.assertEqual(provider.expire_sessions(datetime(2026, 8, 21, tzinfo=timezone.utc), 8), 1)
        # Delete the remaining selected account rows exactly.
        self.assertEqual(provider.delete_sessions_for_user("user-a"), 1)
        # Require no session authority to remain.
        self.assertEqual(provider.list_sessions(), [])

    # Prove simultaneous creators retain every row without cross-wired CSRF values.
    def test_parallel_create_preserves_rows_and_marker_lock_order(self) -> None:
        # Construct one provider whose transaction context serializes the modeled writes.
        provider = _ModelPostgresSessions()
        # Build sixteen same-wave sessions across shared and independent identities.
        sessions = [_session(index, "shared-user" if index < 8 else f"user-{index}") for index in range(16)]
        # Release every worker into the provider boundary together.
        barrier = threading.Barrier(len(sessions))

        # Create and immediately resolve one independent credential.
        def create(row: dict) -> tuple[str, str]:
            # Wait until every creator reached the deterministic rendezvous.
            barrier.wait(timeout=10)
            # Commit one row under caps above the bounded cohort.
            created = provider.create_session(row, 16, 32)
            # Resolve the exact credential through the unique digest path.
            resolved = provider.get_session_by_token(created["token"])
            # Return only opaque identity and CSRF proof.
            return resolved["session_id"], resolved["csrf_token"]

        # Execute the simultaneous creator cohort and surface every failure.
        with ThreadPoolExecutor(max_workers=len(sessions)) as executor:
            # Materialize all results before checking durable inventory.
            results = list(executor.map(create, sessions))
        # Require every opaque identity and its exact CSRF proof to survive.
        self.assertEqual(set(results), {(row["session_id"], row["csrf_token"]) for row in sessions})
        # Require every complete-registry scan to follow an immediately preceding marker lock.
        self.assertTrue(all(provider.events[index - 1] == "marker" for index, event in enumerate(provider.events) if event == "registry"))

    # Prove absent or malformed import authority fails before session insertion.
    def test_create_requires_exact_completed_import_marker(self) -> None:
        # Exercise missing and incomplete marker states independently.
        for marker in (None, {"schema_version": 1, "status": "pending"}):
            # Build fresh modeled authority for each state.
            provider = _ModelPostgresSessions()
            # Replace only the marker result before mutation.
            provider.marker_payload = marker
            # Require the fixed recovery boundary.
            with self.assertRaisesRegex(ConflictError, "^Session storage requires operator recovery$"):
                # Attempt direct creation without completed import authority.
                provider.create_session(_session(1, "marker-user"), 2, 4)
            # Preserve an empty registry after rollback.
            self.assertEqual(provider.rows, {})

    # Prove caller mutator failures retain exact identity and roll back every change.
    def test_mutator_exception_identity_and_rollback_are_preserved(self) -> None:
        # Seed one active row through the ordinary production path.
        provider = _ModelPostgresSessions()
        # Create one credential before the hostile callback.
        provider.create_session(_session(1, "callback-user"), 2, 4)
        # Capture exact durable authority before mutation.
        before = provider.list_sessions()
        # Create one unique caller-owned exception object.
        failure = LookupError("caller-owned-detail")

        # Raise the exact object after mutating only the detached callback copy.
        def fail(row: dict) -> dict:
            # Change the detached input so rollback and detachment are both tested.
            row["status"] = "revoked"
            # Surface the caller-owned object unchanged.
            raise failure

        # Capture the exact raised object without matching its sensitive message.
        with self.assertRaises(LookupError) as raised:
            # Execute the callback under a committed session operation.
            provider.update_session("postgres-session-1", fail)
        # Require exact object identity and byte-equivalent durable rows.
        self.assertIs(raised.exception, failure)
        # Require no detached callback mutation to reach storage.
        self.assertEqual(provider.list_sessions(), before)

    # Prove planner rejection happens before the host transaction seam.
    def test_planner_reentry_is_rejected_before_database_operation(self) -> None:
        # Construct one provider and mark its current thread as planner-owned.
        provider = _ModelPostgresSessions()
        # Activate the modeled purity boundary.
        provider.planner_active = True
        # Require read visibility to fail through the fixed provider-neutral category.
        with self.assertRaisesRegex(ValidationError, "^Game action planner must be side-effect free$"):
            # Attempt one digest lookup without opening a transaction.
            provider.get_session_by_token("planner-token")
        # Require no host transaction policy to have been requested.
        self.assertEqual(provider.commit_flags, [])

    # Prove native SQL uses bound values and explicit JSONB casts only.
    def test_native_write_sql_is_parameterized_and_jsonb_explicit(self) -> None:
        # Construct one provider only for direct helper and codec use.
        provider = _ModelPostgresSessions()
        # Validate one complete durable row through the normal creation codec.
        durable = provider.create_session(_session(1, "sql-user"), 2, 4)
        # Remove the request-local bearer before direct durable helper use.
        durable.pop("token")
        # Capture direct helper statements without changing model authority.
        cursor = _RecordingCursor()
        # Exercise one insert with JSONB payload binding.
        PostgresSessionMixin._insert_postgres_session(provider, cursor, durable)
        # Exercise one native update through the opaque primary key.
        PostgresSessionMixin._update_postgres_session(provider, cursor, durable, durable)
        # Exercise one exact deletion.
        PostgresSessionMixin._delete_postgres_session(provider, cursor, durable)
        # Require placeholders and explicit JSONB casts without interpolated identity values.
        self.assertTrue(all("%s" in statement and "postgres-session-1" not in statement for statement, _parameters in cursor.calls))
        # Require both JSONB writes to use explicit server-side casts.
        self.assertTrue(all("CAST(%s AS JSONB)" in cursor.calls[index][0] for index in (0, 1)))
        # Require every identity to remain inside bound parameter tuples.
        self.assertTrue(all(isinstance(parameters, tuple) for _statement, parameters in cursor.calls))

    # Prove split authority between indexes and JSONB fails closed.
    def test_native_row_index_mismatch_requires_recovery(self) -> None:
        # Build one valid durable row before introducing an indexed mismatch.
        provider = _ModelPostgresSessions()
        # Persist and list the canonical detached row.
        provider.create_session(_session(1, "row-user"), 2, 4)
        # Read the sole durable row from modeled authority.
        durable = provider.list_sessions()[0]
        # Construct one psycopg-style dict row with a hostile duplicated identity.
        raw = {**durable, "session_id": "wrong-id", "session_json": copy.deepcopy(durable)}
        # Require one fixed value-free recovery result.
        with self.assertRaisesRegex(ConflictError, "^Session storage requires operator recovery$"):
            # Validate the inconsistent cursor row directly.
            provider._session_from_postgres_row(raw)

    # Bind the mixin to the agreed connector-neutral host interface and SQL dialect.
    def test_source_has_no_connector_or_unbound_value_boundary(self) -> None:
        # Read the exact production mixin source under test.
        source = inspect.getsource(sessions_postgres_module)
        # Require no connector import, driver access, or duplicate provider transaction owner.
        self.assertNotIn("import psycopg", source)
        # Keep native error translation exclusively in the host provider.
        self.assertNotIn("_driver", source)
        # Require every write payload to cross the explicit JSONB cast boundary.
        self.assertIn("CAST(%s AS JSONB)", source)
        # Require marker locking to precede complete-registry mutations by named helper use.
        self.assertGreaterEqual(source.count("self._lock_postgres_session_registry(cursor)"), 3)
        # Require the mixin to delegate every database lifecycle to the reviewed host context.
        self.assertIn("self._database_cursor(commit=commit)", source)
        # Parse production source so every cursor execute statement can be inspected structurally.
        tree = ast.parse(source)
        # Select only method calls whose attribute name is execute.
        execute_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "execute"]
        # Require every executed SQL expression to be one fixed string literal.
        self.assertTrue(all(call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str) for call in execute_calls))


# Run this module against one self-managed disposable PostgreSQL 16 cluster.
def _run_managed_live_suite() -> int:
    # Import safe temporary-root cleanup only for explicit managed live execution.
    import shutil
    # Import high-entropy disposable identity and credential generation.
    import secrets
    # Import isolated temporary-directory allocation outside the repository.
    import tempfile
    # Import portable paths for the official PostgreSQL binary root.
    from pathlib import Path
    # Reuse the migration lane's proven subprocess/runner helpers and connector imports.
    from tests import postgres_migration_live as live
    # Bind the official binary root supplied by the explicit test command.
    live.POSTGRES_BIN = Path(os.environ["CASINO_POSTGRES_TEST_BIN"])
    # Require the same official binary inventory before allocating a cluster.
    live._require_live_authorization()
    # Allocate one unique issue-scoped cluster root under the operating-system temp directory.
    cluster_root = Path(tempfile.mkdtemp(prefix="casino-postgres-1058-session-"))
    # Keep all database files below the verified disposable root.
    data_root = cluster_root / "data"
    # Keep server output below the same disposable root.
    log_path = cluster_root / "postgres.log"
    # Derive collision-resistant target names ending in the migration lane's required suffix.
    nonce = secrets.token_hex(4)
    # Name one disposable session-test login role.
    role = f"casino_session_{nonce}_1057"
    # Name one disposable session-test database.
    database = f"casino_session_{nonce}_1057"
    # Generate one database password retained only by this process.
    password = secrets.token_urlsafe(32)
    # Generate one independent target-binding key retained only by this process.
    binding_key = secrets.token_urlsafe(48)
    # Reserve one currently free literal-loopback port.
    port = live._loopback_port()
    # Track whether the private cluster requires unconditional shutdown.
    started = False
    # Track whether the generated target requires identity cleanup.
    target_created = False
    # Start the complete managed lifecycle with unconditional cleanup.
    try:
        # Initialize an official PostgreSQL cluster using local trust inside the private root.
        live._postgres_command([str(live.POSTGRES_BIN / "initdb.exe"), "-D", str(data_root), "-A", "trust", "-U", "casino_admin_1058", "--encoding=UTF8", "--no-locale"])
        # Start only one loopback listener with disposable durability shortcuts.
        live._postgres_command([str(live.POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-l", str(log_path), "-o", f"-p {port} -h 127.0.0.1 -F", "-w", "start"])
        # Record active process ownership for cleanup.
        started = True
        # Open the private cluster's default database as its synthetic admin.
        admin = live.psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1058", dbname="postgres", autocommit=True, connect_timeout=5)
        try:
            # Open one autocommit cursor because database creation cannot run in a transaction.
            cursor = admin.cursor()
            # Prove the generated role and database are both absent before creation.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Refuse adoption of any pre-existing target identity.
            if cursor.fetchone() != (0, 0):
                # Stop before any ambiguous create or drop operation.
                raise RuntimeError("PostgreSQL session live target already exists")
            # Create the fresh login role through identifier/literal-safe composition.
            cursor.execute(live.sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(live.sql.Identifier(role), live.sql.Literal(password)))
            # Create the fresh database owned only by the generated role.
            cursor.execute(live.sql.SQL("CREATE DATABASE {} OWNER {}").format(live.sql.Identifier(database), live.sql.Identifier(role)))
            # Authorize cleanup only after both identities were freshly created.
            target_created = True
        finally:
            # Close the synthetic admin connection after creation.
            admin.close()
        # Build the exact deployment-only environment for the migration runner.
        environment = dict(os.environ)
        # Select literal loopback for the disposable target.
        environment["CASINO_POSTGRES_MIGRATION_HOST"] = "127.0.0.1"
        # Select the private listener port.
        environment["CASINO_POSTGRES_MIGRATION_PORT"] = str(port)
        # Select the generated migration role.
        environment["CASINO_POSTGRES_MIGRATION_USER"] = role
        # Supply the generated database password.
        environment["CASINO_POSTGRES_MIGRATION_PASSWORD"] = password
        # Select the generated database.
        environment["CASINO_POSTGRES_MIGRATION_DATABASE"] = database
        # Supply the independent target-binding key.
        environment["CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY"] = binding_key
        # Supply the exact migration-owned disposable marker.
        environment["CASINO_POSTGRES_MIGRATION_DISPOSABLE"] = live.DISPOSABLE_MARKER
        # Apply the exact accepted migration catalog through the deployment-only runner.
        applied = live._runner("apply", environment)
        # Require exact clean native schema five before session execution.
        if (applied.get("current_version"), applied.get("status")) != (5, "clean"):
            # Refuse partial or dirty live evidence.
            raise RuntimeError("PostgreSQL session live migration is incomplete")
        # Publish only process-local target settings consumed by the explicit live owner.
        os.environ.update({"CASINO_POSTGRES_SESSION_HOST": "127.0.0.1", "CASINO_POSTGRES_SESSION_PORT": str(port), "CASINO_POSTGRES_SESSION_USER": role, "CASINO_POSTGRES_SESSION_PASSWORD": password, "CASINO_POSTGRES_SESSION_DATABASE": database})
        # Load this module's complete suite after target settings are available.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(PostgresSessionProviderTests)
        # Execute focused model and live cases through one verbose-free runner.
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        # Return success only when every focused and live case passed.
        return 0 if result.wasSuccessful() else 1
    finally:
        # Remove generated target identities only while the private cluster is active.
        if target_created and started:
            try:
                # Open one synthetic admin connection solely to the private listener.
                admin = live.psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1058", dbname="postgres", autocommit=True, connect_timeout=3)
                # Open one exact-target cleanup cursor.
                cursor = admin.cursor()
                # Terminate only sessions attached to the generated database.
                cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
                # Drop only the database this process proved absent then created.
                cursor.execute(live.sql.SQL("DROP DATABASE IF EXISTS {}").format(live.sql.Identifier(database)))
                # Drop only the role this process proved absent then created.
                cursor.execute(live.sql.SQL("DROP ROLE IF EXISTS {}").format(live.sql.Identifier(role)))
                # Close the private admin connection after exact cleanup.
                admin.close()
            except Exception:
                # Preserve the primary test result while cluster-root removal destroys residue.
                pass
        # Stop the exact private cluster process on every path.
        if started:
            # Use the migration lane's proven DEVNULL subprocess boundary.
            live._postgres_command([str(live.POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-m", "immediate", "-w", "stop"])
        # Resolve both paths before recursive deletion safety validation.
        resolved_root = cluster_root.resolve()
        # Resolve the operating-system temp directory for containment comparison.
        resolved_temp = Path(tempfile.gettempdir()).resolve()
        # Refuse deletion when the generated root escaped the exact temp parent.
        if resolved_temp not in resolved_root.parents:
            # Stop without deleting an ambiguous filesystem target.
            raise RuntimeError("PostgreSQL session live cleanup path is invalid")
        # Remove the complete stopped disposable cluster tree.
        shutil.rmtree(resolved_root, ignore_errors=False)


# Run this focused module directly for disposable developer evidence.
if __name__ == "__main__":
    # Select self-managed live execution only through two exact explicit markers.
    if os.environ.get("CASINO_POSTGRES_SESSION_MANAGED_LIVE") == "CASINO-POSTGRES-1058-MANAGED-LIVE":
        # Exit with the managed suite's exact focused result.
        raise SystemExit(_run_managed_live_suite())
    # Execute ordinary unittest without importing the central API runner.
    unittest.main()
