# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-neutral first-class session lifecycle and concurrency tests. (SESSION-014, STORAGE-019, TEST-250)"""

# Import copy support so the relational model preserves provider detachment guarantees.
import copy
# Import source inspection so SQL lane ownership stays bound without a database service.
import inspect
# Import JSON decoding for exact durable-row and legacy-import evidence.
import json
# Import temporary roots so no configured authentication data is touched.
import tempfile
# Import threading primitives for simultaneous login and logout schedules.
import threading
# Import unittest for central-runner integration.
import unittest
# Import bounded worker pools for repeated concurrent provider calls.
from concurrent.futures import ThreadPoolExecutor
# Import fixed UTC instants for deterministic cap and expiry assertions.
from datetime import datetime, timezone
# Import portable paths for isolated JSON session registries.
from pathlib import Path

# Import both concrete and schema-aware provider owners under test.
from casino.core.storage import JsonStorageProvider
# Import the complete relational session module for fixed bridge-namespace source assertions.
from casino.core.storage import sessions_mysql as sessions_mysql_module
# Import the relational session mixin so its production lifecycle algorithm is exercised directly.
from casino.core.storage.sessions_mysql import MySQLSessionMixin
# Import the shared durable codec for direct plaintext-stripping regression evidence.
from casino.core.storage.sessions import durable_session_row
# Import the fixed corruption boundary used by legacy-import failure evidence.
from casino.errors import ConflictError, ValidationError


# Return one complete compatible session with deterministic times and caller-owned authority.
def _session(index: int, user_id: str, *, token: str | None = None, status: str = "active", expires_at: str = "2026-09-01T00:00:00.000Z") -> dict:
    # Derive one stable bearer when the caller does not select it explicitly.
    bearer = token or f"session-token-{index}"
    # Stagger activity by one second so cap eviction has an unambiguous oldest row.
    timestamp = f"2026-08-20T00:00:{index:02d}.000Z"
    # Return the complete durable-compatible auth-layer shape.
    return {"session_id": f"session-{index}", "user_id": user_id, "token": bearer, "csrf_token": f"csrf-{index}".ljust(32, "x"), "generation": 1, "status": status, "created_at": timestamp, "updated_at": timestamp, "expires_at": expires_at, "client": "provider-parity", "auth_method": "local"}


# Provide the no-I/O lease shape required by MySQL read methods in the transaction model.
class _ModelConnection:
    # Retain the model provider so cursor calls return its ignored transaction token.
    def __init__(self, provider) -> None:
        # Store the provider only for deterministic identity assertions.
        self.provider = provider
        # Start with no close evidence.
        self.closed = False

    # Return the model itself as an inert dictionary-cursor token.
    def cursor(self, dictionary: bool = False):
        # Require production reads to request dictionary rows.
        assert dictionary is True
        # Return the retained provider because overridden row primitives ignore SQL cursors.
        return self.provider

    # Record lease cleanup without changing model rows.
    def close(self) -> None:
        # Mark this request-local lease as returned.
        self.closed = True


# Exercise the production MySQL session algorithms over one transaction-faithful row model.
class _ModelMySQLSessions(MySQLSessionMixin):
    # Initialize an empty native or compatibility-lane registry.
    def __init__(self, schema_version: int = 5) -> None:
        # Retain the selected clean runtime schema for lane assertions.
        self._schema_version = schema_version
        # Store one detached durable row per token digest.
        self.rows: dict[str, dict] = {}
        # Serialize every model transaction like the fixed importer-marker semaphore.
        self.lock = threading.RLock()
        # Retain exact registry-semaphore statements for concurrency and ordering evidence.
        self.registry_lock_statements: list[tuple[str, tuple]] = []
        # Model the import-first lifecycle with one canonical completed marker by default.
        self.marker_payload = {"schema_version": 1, "status": "complete"}

    # Model successful checksum-verified readiness without an external connector.
    def ensure_ready(self) -> None:
        # Return only after the configured schema identity is already available.
        return None

    # Preserve the planner-mutation contract in a route-free test owner.
    def _reject_planner_mutation(self) -> None:
        # No planner scope is active in provider-parity tests.
        return None

    # Return one request-local no-I/O connection used by read methods.
    def connect(self):
        # Allocate a distinct lease so cleanup remains observable per call.
        return _ModelConnection(self)

    # Model the fixed existing importer marker selected by production create transactions.
    def execute(self, statement: str, parameters: tuple) -> None:
        # Accept only the semaphore query needed by production create_session in this row model.
        assert statement == "SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE"
        # Bind every modeled lock to the exact private importer-marker identity.
        assert parameters == (sessions_mysql_module._MYSQL_SESSION_IMPORT_MARKER,)
        # Record one lock acquisition attempt while the outer transaction semaphore is held.
        self.registry_lock_statements.append((statement, parameters))

    # Return the canonical completed marker for one modeled registry-lock query.
    def fetchone(self) -> dict | None:
        # Match the connector dictionary-row shape consumed by the production helper.
        return None if self.marker_payload is None else {"payload_json": json.dumps(self.marker_payload, sort_keys=True)}

    # Execute one callback under the model's exclusive transaction boundary.
    def _mysql_session_transaction(self, operation):
        # Serialize the complete select/mutate/commit algorithm.
        with self.lock:
            # Invoke production lifecycle logic with inert connection and cursor tokens.
            return operation(self, self)

    # Select detached matching rows using the same predicates as native and bridge SQL.
    def _select_mysql_sessions(self, _cursor, *, token_digest=None, session_id=None, user_id=None, for_update=False):
        # Copy every row before filtering so callers cannot mutate stored model authority.
        rows = [copy.deepcopy(row) for row in self.rows.values()]
        # Apply the unique token digest predicate when present.
        if token_digest is not None:
            # Retain only the exact bearer identity.
            rows = [row for row in rows if row["token_digest"] == token_digest]
        # Apply the opaque session primary key when present.
        if session_id is not None:
            # Retain only the exact session identity.
            rows = [row for row in rows if row["session_id"] == session_id]
        # Apply the account-index predicate when present.
        if user_id is not None:
            # Retain only rows owned by the selected user.
            rows = [row for row in rows if row["user_id"] == user_id]
        # Return a deterministic credential-key order for complete scans.
        return sorted(rows, key=lambda row: row["token_digest"])

    # Insert one unique detached row inside the held model transaction.
    def _insert_mysql_session(self, _cursor, row: dict) -> None:
        # Reject token-digest or opaque-id collision like relational unique indexes.
        if row["token_digest"] in self.rows or any(existing["session_id"] == row["session_id"] for existing in self.rows.values()):
            # Surface the fixed storage-recovery result used by connector collisions.
            raise ConflictError("Session storage requires operator recovery")
        # Publish a detached row under its credential identity.
        self.rows[row["token_digest"]] = copy.deepcopy(row)

    # Replace one selected row and its optional rotated token index atomically.
    def _update_mysql_session(self, _cursor, prior: dict, row: dict) -> None:
        # Remove the exact predecessor digest selected under the transaction lock.
        removed = self.rows.pop(prior["token_digest"], None)
        # Refuse a missing predecessor instead of issuing replacement authority.
        if removed is None:
            # Match the production conflict boundary.
            raise ConflictError("Session storage requires operator recovery")
        # Reject replacement collision while preserving deterministic model failure.
        if row["token_digest"] in self.rows:
            # Restore the predecessor before surfacing the conflict.
            self.rows[prior["token_digest"]] = removed
            # Match the production unique-index recovery boundary.
            raise ConflictError("Session storage requires operator recovery")
        # Publish the complete detached replacement.
        self.rows[row["token_digest"]] = copy.deepcopy(row)

    # Delete one exact selected row under the transaction lock.
    def _delete_mysql_session(self, _cursor, row: dict) -> None:
        # Remove only the digest-owned model row.
        removed = self.rows.pop(row["token_digest"], None)
        # Refuse ambiguous or missing deletion evidence.
        if removed is None:
            # Match the production fixed recovery outcome.
            raise ConflictError("Session storage requires operator recovery")


# Prove first-class providers converge without one aggregate document or lost concurrent sessions.
class SessionStorageProviderTests(unittest.TestCase):
    # Allocate one isolated JSON root for every test.
    def setUp(self) -> None:
        # Create a disposable directory outside configured application state.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-session-storage-")
        # Bind the exact disposable data root.
        self.data_root = Path(self.temporary.name) / "data"

    # Prove an explicit bearer argument cannot leave an embedded plaintext credential durable.
    def test_durable_codec_strips_embedded_token_when_explicit_token_is_supplied(self) -> None:
        # Build one complete row carrying a deliberately different embedded bearer.
        source = _session(1, "codec-user", token="embedded-secret")
        # Validate with the explicit request credential used as authoritative lookup material.
        durable = durable_session_row(source, token="explicit-secret")
        # Require plaintext absence and one fixed one-way digest only.
        self.assertNotIn("token", durable)
        # Resolve the expected explicit credential through the public provider lifecycle codec.
        provider = _ModelMySQLSessions()
        # Create a matching row to prove the explicit credential, not the embedded credential, owns lookup.
        durable["token"] = "explicit-secret"
        # Persist and resolve through the production algorithm without retaining the supplied bearer.
        created = provider.create_session(durable, 2, 4)
        # Require only the explicit credential to authenticate the resulting row.
        self.assertEqual((created["token"], provider.get_session_by_token("explicit-secret")["session_id"]), ("explicit-secret", "session-1"))
        # Require the ignored embedded credential to have no authority.
        self.assertIsNone(provider.get_session_by_token("embedded-secret"))

    # Prove JSON session visibility and mutation cannot re-enter recoverable storage from a planner.
    def test_json_session_operations_reject_planner_reentry(self) -> None:
        # Construct one isolated provider without creating session state.
        provider = JsonStorageProvider(self.data_root)
        # Mark the current thread as executing one supposedly pure action planner.
        with provider._planner_boundary():
            # Exercise every session visibility path that may converge recoverable JSON work.
            for operation in (
                lambda: provider.get_session_by_token("planner-token"),
                lambda: provider.list_sessions(),
                lambda: provider.revoke_session_by_token("planner-token", "2026-08-20T00:00:00.000Z"),
            ):
                # Require refusal before any file, marker, or recovery mutation.
                with self.assertRaisesRegex(ValidationError, "^Game action planner must be side-effect free$"):
                    # Invoke one bounded provider operation under the active planner.
                    operation()
        # Require the rejected calls to leave the complete data root absent.
        self.assertFalse(self.data_root.exists())

    # Delete every isolated provider byte after each test.
    def tearDown(self) -> None:
        # Remove the complete temporary directory.
        self.temporary.cleanup()

    # Yield the real JSON provider and transaction-faithful MySQL lifecycle model.
    def _providers(self):
        # Construct a fresh JSON provider for this subtest.
        yield "json", JsonStorageProvider(self.data_root)
        # Construct a fresh native-schema MySQL lifecycle model.
        yield "mysql", _ModelMySQLSessions()

    # Prove cap, rotation, revocation, and expiry semantics are provider-neutral.
    def test_lifecycle_cap_rotation_and_expiry_are_provider_neutral(self) -> None:
        # Exercise the exact same lifecycle assertions on both provider owners.
        for name, provider in self._providers():
            # Isolate failures by provider identity.
            with self.subTest(provider=name):
                # Create the first account session.
                provider.create_session(_session(1, "user-a"), 2, 8)
                # Create the second account session.
                provider.create_session(_session(2, "user-a"), 2, 8)
                # Create a third session and deterministically evict the oldest account row.
                provider.create_session(_session(3, "user-a"), 2, 8)
                # Require the oldest bearer to be absent after cap enforcement.
                self.assertIsNone(provider.get_session_by_token("session-token-1"))
                # Require the two newest rows in deterministic newest-first order.
                self.assertEqual([row["session_id"] for row in provider.list_sessions("user-a")], ["session-3", "session-2"])
                # Require durable projections never to contain plaintext bearer authority.
                self.assertTrue(all("token" not in row for row in provider.list_sessions()))
                # Rotate the second credential and CSRF proof through generation one.
                rotated = provider.rotate_session("session-2", "session-token-2", 1, "rotated-token-2", "rotated-csrf-proof".ljust(32, "x"), "2026-08-20T01:00:00.000Z")
                # Require one exact generation advance and one-time replacement bearer.
                self.assertEqual((rotated["generation"], rotated["token"]), (2, "rotated-token-2"))
                # Require the predecessor credential to stop resolving.
                self.assertIsNone(provider.get_session_by_token("session-token-2"))
                # Require a stale compare-and-swap attempt to leave the replacement unchanged.
                self.assertIsNone(provider.rotate_session("session-2", "rotated-token-2", 1, "stale-replacement", "stale-csrf-proof".ljust(32, "x"), "2026-08-20T01:01:00.000Z"))
                # Revoke the replacement credential exactly once.
                self.assertEqual(provider.revoke_session_by_token("rotated-token-2", "2026-08-20T01:02:00.000Z"), 1)
                # Require idempotent repeat revocation.
                self.assertEqual(provider.revoke_session_by_token("rotated-token-2", "2026-08-20T01:03:00.000Z"), 0)
                # Sweep every revoked row while retaining the remaining active row.
                self.assertEqual(provider.expire_sessions(datetime(2026, 8, 21, tzinfo=timezone.utc), 8), 1)
                # Require only the third active session to remain.
                self.assertEqual([row["session_id"] for row in provider.list_sessions()], ["session-3"])

    # Prove direct relational mutation cannot invent or repair the import authority marker.
    def test_mysql_create_requires_completed_import_marker(self) -> None:
        # Exercise absent and malformed marker states independently.
        for marker in (None, {"schema_version": 1, "status": "pending"}):
            # Build a fresh transaction model for each fail-closed marker state.
            provider = _ModelMySQLSessions()
            # Replace only the modeled connector result before mutation begins.
            provider.marker_payload = marker
            # Require the fixed recovery boundary without publishing any session row.
            with self.assertRaisesRegex(ConflictError, "^Session storage requires operator recovery$"):
                # Attempt direct provider creation without a completed import lifecycle.
                provider.create_session(_session(1, "marker-user"), 2, 4)
            # Preserve empty authority and prove no implicit marker repair or session insert occurred.
            self.assertEqual(provider.rows, {})

    # Reproduce parallel same-user and different-user login/logout without lost or cross-wired rows.
    def test_parallel_login_logout_preserves_every_session_and_csrf(self) -> None:
        # Exercise both storage providers against the same simultaneous schedule.
        for name, provider in self._providers():
            # Isolate failures by provider identity.
            with self.subTest(provider=name):
                # Create sixteen workers: eight share one user and eight use distinct users.
                sessions = [_session(index, "shared-user" if index < 8 else f"user-{index}") for index in range(16)]
                # Release every create call at the same deterministic barrier.
                create_barrier = threading.Barrier(len(sessions))

                # Create and immediately read back one independent credential.
                def login(row: dict) -> tuple[str, str]:
                    # Wait until every worker is ready to enter the provider boundary.
                    create_barrier.wait(timeout=10)
                    # Commit one session with caps above this bounded cohort.
                    created = provider.create_session(row, 16, 32)
                    # Resolve the exact new bearer through the direct digest index.
                    resolved = provider.get_session_by_token(created["token"])
                    # Return only opaque identity and CSRF proof for equality checks.
                    return resolved["session_id"], resolved["csrf_token"]

                # Execute every login concurrently and surface every worker exception.
                with ThreadPoolExecutor(max_workers=len(sessions)) as executor:
                    # Materialize the complete result set before any logout begins.
                    created_results = list(executor.map(login, sessions))
                # Require every session id to survive without a lost update.
                self.assertEqual({result[0] for result in created_results}, {row["session_id"] for row in sessions})
                # Require every CSRF value to stay attached to its exact session.
                self.assertEqual({result[1] for result in created_results}, {row["csrf_token"] for row in sessions})
                # Require sixteen durable independent rows with no plaintext tokens.
                self.assertEqual((len(provider.list_sessions()), sum("token" in row for row in provider.list_sessions())), (16, 0))
                # Require every MySQL-model creator to traverse the fixed registry semaphore exactly once.
                if name == "mysql":
                    # Bind the concurrent schedule to sixteen single-pass transactions with no callback retry.
                    self.assertEqual(len(provider.registry_lock_statements), len(sessions))
                # Release every logout call at the same deterministic barrier.
                logout_barrier = threading.Barrier(len(sessions))

                # Revoke one exact bearer without touching another session.
                def logout(row: dict) -> int:
                    # Wait until every credential is ready to revoke concurrently.
                    logout_barrier.wait(timeout=10)
                    # Revoke only the caller's bearer.
                    return provider.revoke_session_by_token(row["token"], "2026-08-20T02:00:00.000Z")

                # Execute every logout concurrently and surface every worker exception.
                with ThreadPoolExecutor(max_workers=len(sessions)) as executor:
                    # Materialize every exact changed count.
                    revoked = list(executor.map(logout, sessions))
                # Require every logout to change exactly one active session.
                self.assertEqual(revoked, [1] * len(sessions))
                # Require no credential to resolve as active after the complete schedule.
                self.assertTrue(all(provider.get_session_by_token(row["token"])["status"] == "revoked" for row in sessions))

    # Prove the JSON importer retires the aggregate once and strips every plaintext bearer.
    def test_json_legacy_import_is_one_shot_and_secret_free(self) -> None:
        # Construct one real provider beside an explicit legacy aggregate path.
        provider = JsonStorageProvider(self.data_root)
        # Select the retired aggregate location used by auth compatibility startup.
        legacy_path = Path(self.temporary.name) / "auth" / "sessions.json"
        # Create its isolated parent before writing the historical fixture.
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        # Build one complete historical session containing plaintext bearer authority.
        legacy = {"schema_version": 1, "sessions": [_session(1, "legacy-user", token="legacy-token")]}
        # Persist exact historical JSON bytes.
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        # Import and retire the aggregate under the provider gate.
        provider.import_legacy_sessions(legacy_path, lambda: {"schema_version": 1, "sessions": []})
        # Require the retired source to be absent after completion.
        self.assertFalse(legacy_path.exists())
        # Require the imported bearer to resolve through its direct keyed row.
        self.assertEqual(provider.get_session_by_token("legacy-token")["session_id"], "session-1")
        # Require no plaintext token key in the sole keyed durable document.
        durable_files = list(provider.session_rows_path().glob("session-*.json"))
        # Bind exact single-row migration cardinality and secret-free content.
        self.assertEqual((len(durable_files), "token" in json.loads(durable_files[0].read_text(encoding="utf-8"))), (1, False))
        # Recreate a hostile aggregate after the completion marker exists.
        legacy_path.write_text("{not-json", encoding="utf-8")
        # Require the one-shot importer to ignore permanently retired authority.
        provider.import_legacy_sessions(legacy_path, lambda: {"schema_version": 1, "sessions": []})
        # Require the already imported row to remain exact.
        self.assertEqual(provider.get_session_by_token("legacy-token")["session_id"], "session-1")

    # Prove MySQL source owns indexed native rows and keyed bridge documents, never one session aggregate.
    def test_mysql_session_sql_lanes_are_first_class_and_schema_aware(self) -> None:
        # Read the bounded relational module so both class logic and fixed namespaces are visible.
        source = inspect.getsource(sessions_mysql_module)
        # Require native unique-token, primary-session, user, and expiry index ownership.
        for fragment in ("FROM casino_sessions WHERE token_digest = %s", "FROM casino_sessions WHERE session_id = %s", "FROM casino_sessions WHERE user_id = %s", "INSERT INTO casino_sessions", "UPDATE casino_sessions", "DELETE FROM casino_sessions"):
            # Bind every native lifecycle access path.
            self.assertIn(fragment, source)
        # Require schemas two through four to use one digest-keyed document per session.
        self.assertIn('auth/session/v2/row/', source)
        # Reject the retired aggregate auth document as a lifecycle row identity.
        self.assertNotIn('auth/sessions.json', source)
        # Require one explicit transaction boundary around relational mutations.
        self.assertIn("connection.start_transaction()", source)
        # Require successful commit and failure rollback before lease cleanup.
        self.assertTrue(all(fragment in source for fragment in ("connection.commit()", "connection.rollback()", "connection.close()")))
        # Require create to lock the completed import marker before taking the complete-registry range lock.
        create_source = inspect.getsource(MySQLSessionMixin.create_session)
        self.assertLess(create_source.index("_lock_mysql_session_registry(cursor)"), create_source.index("_select_mysql_sessions(cursor, for_update=True)"))
        # Require full replacement to use the identical marker-before-registry order without marker creation.
        replace_source = inspect.getsource(MySQLSessionMixin.replace_sessions)
        self.assertLess(replace_source.index("_lock_mysql_session_registry(cursor)"), replace_source.index("_select_mysql_sessions(cursor, for_update=True)"))
        self.assertNotIn("INSERT INTO casino_documents", replace_source)
        # Prohibit a retry loop from replaying arbitrary session transaction callbacks or create operations.
        transaction_source = inspect.getsource(MySQLSessionMixin._mysql_session_transaction)
        self.assertNotIn("while ", transaction_source)
        self.assertNotIn("for attempt", transaction_source)


# Support direct focused execution in local and CI validation.
if __name__ == "__main__":
    # Run the focused suite with standard unittest reporting.
    unittest.main()
