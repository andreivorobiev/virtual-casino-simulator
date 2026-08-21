# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""MySQL first-class session rows with a held-schema keyed-document bridge."""

# Import annotations so the mixin stays independent of concrete-provider declaration order.
from __future__ import annotations
# Import deep-copy support so caller callbacks never retain decoded database row references.
import copy
# Import JSON encoding for canonical row payloads and the schema-two-to-four bridge.
import json
# Import UTC instants for provider-owned expiry sweeps.
from datetime import datetime, timezone
# Import portable path typing accepted by the shared legacy importer contract.
from pathlib import Path
# Import caller mutation and default-factory typing without importing auth.
from typing import Any, Callable

# Import the canonical MySQL JSON decoder and fixed provider contract types.
from casino.core.storage.base import _decode_json
# Import shared session validation, resolution, expiry, ordering, and credential hashing.
from casino.core.storage.sessions import durable_session_row, resolved_session_row, session_eviction_key, session_is_expired, session_token_digest
# Import the stable application timestamp used by importer metadata rows.
from casino.core.clock import utc_now
# Import the fixed conflict boundary used for malformed session persistence.
from casino.errors import ConflictError

# Name the document bridge rows used while migration application remains held on schemas two through four.
_MYSQL_SESSION_DOCUMENT_PREFIX = "auth/session/v2/row/"
# Name one provider-owned marker shared by the bridge and native schema-five table.
_MYSQL_SESSION_IMPORT_MARKER = "auth/session/v2/legacy-imported"
# Name the exact marker payload independently from application document schemas.
_MYSQL_SESSION_STORAGE_VERSION = 1


# Add schema-aware first-class session ownership to the MySQL provider.
class MySQLSessionMixin:
    # Return whether the verified runtime schema owns the native session table.
    def _native_session_storage(self) -> bool:
        # Verify readiness before consulting the cached sanitized schema version.
        self.ensure_ready()
        # Select the table only on the exact clean migration-five schema.
        return self._schema_version == 5

    # Return one keyed bridge document identity for an already-validated bearer digest.
    def _session_document_key(self, token_digest: str) -> str:
        # Concatenate only the fixed prefix and canonical lowercase digest.
        return f"{_MYSQL_SESSION_DOCUMENT_PREFIX}{token_digest}"

    # Convert one native table row or bridge document row into a validated durable session.
    def _session_from_mysql_row(self, row: dict, native: bool) -> dict:
        # Select the complete canonical JSON payload from the backend-specific stable field.
        payload = row.get("session_json") if native else row.get("payload_json")
        # Decode connector strings, bytes, or already-decoded JSON objects uniformly.
        value = _decode_json(payload)
        # Validate the complete session before trusting duplicated indexed columns.
        session = durable_session_row(value)
        # Return directly after bridge validation because its primary key is checked by the caller.
        if not native:
            # Preserve one shared durable row shape across runtime-compatible schemas.
            return session
        # Bind every indexed native column to the canonical payload to prevent split authority.
        try:
            # Compare every duplicated index value without permitting coercion failures to escape.
            inconsistent = any(
                (
                    str(row.get("session_id")) != session["session_id"],
                    str(row.get("token_digest")) != session["token_digest"],
                    str(row.get("user_id")) != session["user_id"],
                    str(row.get("status")) != session["status"],
                    str(row.get("updated_at")) != session["updated_at"],
                    str(row.get("expires_at")) != session["expires_at"],
                    int(row.get("generation")) != session["generation"],
                )
            )
        # Normalize malformed native numeric columns into the fixed recovery boundary.
        except (TypeError, ValueError, OverflowError):
            # Preserve the inconsistent source row for operator inspection.
            raise ConflictError("Session storage requires operator recovery") from None
        # Reject any mismatch between native indexes and the canonical session payload.
        if inconsistent:
            # Preserve the inconsistent row and refuse all partial projections.
            raise ConflictError("Session storage requires operator recovery")
        # Return the validated canonical payload after index binding succeeds.
        return session

    # Select validated rows through native indexes or the held-schema bridge.
    def _select_mysql_sessions(self, cursor, *, token_digest: str | None = None, session_id: str | None = None, user_id: str | None = None, for_update: bool = False) -> list[dict]:
        # Resolve the storage lane once for the complete query.
        native = self._native_session_storage()
        # Append row locking only inside caller-owned explicit transactions.
        locking = " FOR UPDATE" if for_update else ""
        # Use native indexed predicates when schema five is active.
        if native:
            # Select by the unique bearer digest for request authentication.
            if token_digest is not None:
                # Execute one exact unique-index lookup.
                cursor.execute(f"SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE token_digest = %s{locking}", (token_digest,))
            # Select by the primary opaque id for touch, rotation, and targeted revocation.
            elif session_id is not None:
                # Execute one exact primary-key lookup.
                cursor.execute(f"SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE session_id = %s{locking}", (session_id,))
            # Select by the account index for caps, inventory, and bulk revocation.
            elif user_id is not None:
                # Execute one account-index lookup in deterministic row order.
                cursor.execute(f"SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE user_id = %s ORDER BY updated_at, created_at, session_id{locking}", (user_id,))
            # Select the bounded complete registry only for global sweep and compatibility snapshots.
            else:
                # Execute one deterministic complete row scan.
                cursor.execute(f"SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions ORDER BY updated_at, created_at, session_id{locking}")
            # Fetch native rows before validating duplicated index bindings.
            raw_rows = cursor.fetchall()
            # Validate and detach every selected row.
            return [self._session_from_mysql_row(row, True) for row in raw_rows]
        # Use one exact primary-key document lookup for bearer authentication on compatible schemas.
        if token_digest is not None:
            # Lock or read only the digest-derived document row.
            cursor.execute(f"SELECT document_key, payload_json FROM casino_documents WHERE document_key = %s{locking}", (self._session_document_key(token_digest),))
        # Scan the bounded session prefix when a non-token secondary lookup is required.
        else:
            # Lock or read only first-class session bridge rows, never unrelated documents.
            cursor.execute(f"SELECT document_key, payload_json FROM casino_documents WHERE document_key LIKE %s ORDER BY document_key{locking}", (f"{_MYSQL_SESSION_DOCUMENT_PREFIX}%",))
        # Decode and bind every selected bridge document key to its payload digest.
        selected: list[dict] = []
        # Inspect connector dictionary rows one at a time.
        for raw in cursor.fetchall():
            # Decode and validate the complete durable payload.
            session = self._session_from_mysql_row(raw, False)
            # Require the primary document key to match the canonical bearer digest.
            if raw.get("document_key") != self._session_document_key(session["token_digest"]):
                # Preserve inconsistent rows without exposing partial authority.
                raise ConflictError("Session storage requires operator recovery")
            # Apply secondary filters only after strict row validation.
            if session_id is not None and session["session_id"] != session_id:
                # Continue past unrelated opaque ids.
                continue
            # Apply account filtering without changing storage order.
            if user_id is not None and session["user_id"] != user_id:
                # Continue past unrelated identities.
                continue
            # Retain the validated matching row.
            selected.append(session)
        # Reject duplicate opaque ids across bridge rows.
        if len({session["session_id"] for session in selected}) != len(selected):
            # Preserve every conflicting source row for operator recovery.
            raise ConflictError("Session storage requires operator recovery")
        # Return only validated filtered rows.
        return selected

    # Insert one validated session through the active storage lane.
    def _insert_mysql_session(self, cursor, row: dict) -> None:
        # Serialize the canonical complete durable payload once.
        payload = json.dumps(row, sort_keys=True, separators=(",", ":"))
        # Insert one native row when schema five is active.
        if self._native_session_storage():
            # Bind indexes and the canonical payload in one statement.
            cursor.execute(
                "INSERT INTO casino_sessions (session_id, token_digest, user_id, status, created_at, updated_at, expires_at, generation, session_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (row["session_id"], row["token_digest"], row["user_id"], row["status"], row["created_at"], row["updated_at"], row["expires_at"], row["generation"], payload),
            )
            # Return after the native insert to avoid duplicate bridge authority.
            return
        # Insert one independently keyed bridge row on runtime-compatible schemas two through four.
        cursor.execute(
            "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s)",
            (self._session_document_key(row["token_digest"]), payload, row["updated_at"]),
        )

    # Replace one validated session through the active storage lane.
    def _update_mysql_session(self, cursor, prior: dict, row: dict) -> None:
        # Serialize the canonical complete replacement payload once.
        payload = json.dumps(row, sort_keys=True, separators=(",", ":"))
        # Update native indexed fields and payload under the primary-key lock.
        if self._native_session_storage():
            # Require the exact prior opaque id to update one row.
            cursor.execute(
                "UPDATE casino_sessions SET token_digest = %s, user_id = %s, status = %s, created_at = %s, updated_at = %s, expires_at = %s, generation = %s, session_json = %s WHERE session_id = %s",
                (row["token_digest"], row["user_id"], row["status"], row["created_at"], row["updated_at"], row["expires_at"], row["generation"], payload, prior["session_id"]),
            )
        # Replace bridge credential identity with delete-plus-insert inside the same transaction.
        elif prior["token_digest"] != row["token_digest"]:
            # Remove the exact predecessor primary-key document.
            cursor.execute("DELETE FROM casino_documents WHERE document_key = %s", (self._session_document_key(prior["token_digest"]),))
            # Insert the replacement credential row without exposing an intermediate commit.
            cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s)", (self._session_document_key(row["token_digest"]), payload, row["updated_at"]))
        # Update one stable bridge row for non-rotation lifecycle changes.
        else:
            # Replace only the digest-selected row under its held lock.
            cursor.execute("UPDATE casino_documents SET payload_json = %s, updated_at = %s WHERE document_key = %s", (payload, row["updated_at"], self._session_document_key(prior["token_digest"])))
        # Require exactly one selected row to change.
        if cursor.rowcount != 1:
            # Roll back through the caller's fixed recovery boundary.
            raise ConflictError("Session storage requires operator recovery")

    # Delete one validated session through the active storage lane.
    def _delete_mysql_session(self, cursor, row: dict) -> None:
        # Delete by native primary key when schema five is active.
        if self._native_session_storage():
            # Remove only the selected opaque session row.
            cursor.execute("DELETE FROM casino_sessions WHERE session_id = %s", (row["session_id"],))
        # Delete by exact bridge document primary key on compatible schemas.
        else:
            # Remove only the digest-derived session document.
            cursor.execute("DELETE FROM casino_documents WHERE document_key = %s", (self._session_document_key(row["token_digest"]),))
        # Require one exact row removal under the held transaction.
        if cursor.rowcount != 1:
            # Preserve ambiguous storage for operator recovery.
            raise ConflictError("Session storage requires operator recovery")

    # Run one explicit session transaction with guaranteed rollback and lease cleanup.
    def _mysql_session_transaction(self, operation: Callable[[Any, Any], Any]) -> Any:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Verify and cache the exact compatible schema before transaction checkout.
        self.ensure_ready()
        # Open one provider-owned connection for the complete lifecycle operation.
        connection = self.connect()
        # Start protected transaction logic so every failure releases locks and the lease.
        try:
            # Begin explicitly before any row-locking read.
            connection.start_transaction()
            # Open a dictionary cursor for canonical row mapping.
            cursor = connection.cursor(dictionary=True)
            # Execute the caller-owned bounded transition under this transaction.
            result = operation(connection, cursor)
            # Commit only after every row and index transition succeeds.
            connection.commit()
            # Return the detached provider result after durability.
            return result
        # Roll back caller, validation, connector, or collision failures uniformly.
        except Exception:
            # Release every partial write and row lock on this transaction.
            connection.rollback()
            # Preserve the original bounded exception and traceback.
            raise
        # Always close or sanitize the pool lease after the transaction.
        finally:
            # Return the request-owned session to the provider pool.
            connection.close()

    # Import the retired aggregate document exactly once inside one database transaction.
    def import_legacy_sessions(self, legacy_key: str | Path, default_factory: Callable[[], dict]) -> None:
        # Convert state-store paths to the same portable document key used by ordinary MySQL storage.
        legacy_document_key = str(legacy_key).replace("\\", "/")

        # Own marker, source, and destination rows under one transaction.
        def import_rows(_connection, cursor) -> None:
            # Lock the importer marker before consulting retired authority.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (_MYSQL_SESSION_IMPORT_MARKER,))
            # Fetch the optional completion row.
            marker = cursor.fetchone()
            # Stop after verifying one exact prior completion marker.
            if marker is not None:
                # Decode and require the finite marker shape.
                if _decode_json(marker["payload_json"]) != {"schema_version": _MYSQL_SESSION_STORAGE_VERSION, "status": "complete"}:
                    # Preserve all rows for operator recovery.
                    raise ConflictError("Session storage requires operator recovery")
                # Return without consulting the retired aggregate document.
                return
            # Lock the exact legacy document row while deciding first-run or import behavior.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (legacy_document_key,))
            # Fetch the optional aggregate source.
            source = cursor.fetchone()
            # Use the caller's reviewed empty seed only for a genuinely absent document.
            legacy = default_factory() if source is None else _decode_json(source["payload_json"])
            # Require the canonical aggregate container before the first destination write.
            if not isinstance(legacy, dict) or not isinstance(legacy.get("sessions"), list):
                # Preserve malformed source bytes without a completion marker.
                raise ConflictError("Session storage requires operator recovery")
            # Validate every legacy row and strip plaintext bearers before publication.
            rows = [durable_session_row(session) for session in legacy["sessions"]]
            # Reject duplicate digest or opaque identities before partial import.
            if len({row["token_digest"] for row in rows}) != len(rows) or len({row["session_id"] for row in rows}) != len(rows):
                # Preserve the complete source for recovery.
                raise ConflictError("Session storage requires operator recovery")
            # Read every current first-class row under locks before collision checks.
            current = self._select_mysql_sessions(cursor, for_update=True)
            # Build exact current identities for idempotent interrupted migration validation.
            by_digest = {row["token_digest"]: row for row in current}
            # Reject duplicate opaque ids already present in another credential row.
            by_id = {row["session_id"]: row for row in current}
            # Import each source row independently inside the same transaction.
            for row in rows:
                # Accept only an exact replay when this digest or id already exists.
                existing = by_digest.get(row["token_digest"]) or by_id.get(row["session_id"])
                # Refuse a collision without overwriting either authority.
                if existing is not None and existing != row:
                    # Preserve both rows for operator recovery.
                    raise ConflictError("Session storage requires operator recovery")
                # Insert only a genuinely absent source row.
                if existing is None:
                    # Publish one native or bridge row under the current schema lane.
                    self._insert_mysql_session(cursor, row)
            # Insert the exact completion marker only after every destination row succeeds.
            cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s)", (_MYSQL_SESSION_IMPORT_MARKER, json.dumps({"schema_version": _MYSQL_SESSION_STORAGE_VERSION, "status": "complete"}, sort_keys=True), utc_now()))
            # Retire the aggregate source row after marker and destination publication are staged.
            if source is not None:
                # Delete only the exact legacy document key.
                cursor.execute("DELETE FROM casino_documents WHERE document_key = %s", (legacy_document_key,))
                # Require the previously locked source to be removed once.
                if cursor.rowcount != 1:
                    # Refuse ambiguous legacy authority.
                    raise ConflictError("Session storage requires operator recovery")

        # Execute the complete idempotent import under one database transaction.
        self._mysql_session_transaction(import_rows)

    # Create one first-class session with deterministic account and global cap eviction.
    def create_session(self, session: dict, per_user_limit: int, total_limit: int) -> dict:
        # Validate internal caps before opening a transaction.
        if isinstance(per_user_limit, bool) or isinstance(total_limit, bool) or not isinstance(per_user_limit, int) or not isinstance(total_limit, int) or per_user_limit < 1 or total_limit < per_user_limit:
            # Refuse invalid policy without database contact.
            raise ValueError("Session storage limits are invalid")
        # Retain the request-local bearer separately from durable validation.
        token = session.get("token")
        # Validate and strip plaintext credential material before connection checkout.
        row = durable_session_row(session)

        # Own collision checks, eviction, and insert in one transaction.
        def create(_connection, cursor) -> dict:
            # Lock the bounded complete registry because the global cap spans every user.
            current = self._select_mysql_sessions(cursor, for_update=True)
            # Reject credential or opaque-id collision without replacement.
            if any(candidate["token_digest"] == row["token_digest"] or candidate["session_id"] == row["session_id"] for candidate in current):
                # Preserve existing authority for recovery.
                raise ConflictError("Session storage requires operator recovery")
            # Parse the new creation timestamp as the deterministic sweep reference.
            now = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")).astimezone(timezone.utc)
            # Keep only active unexpired predecessors before cap selection.
            survivors = [candidate for candidate in current if candidate["status"] == "active" and not session_is_expired(candidate, now)]
            # Sort this account's predecessors from least to most recently used.
            owned = sorted((candidate for candidate in survivors if candidate["user_id"] == row["user_id"]), key=session_eviction_key)
            # Select account overflow rows required to leave room for the new session.
            user_evictions = owned[: max(0, len(owned) - per_user_limit + 1)]
            # Exclude selected account rows before applying the global cap.
            user_eviction_ids = {candidate["session_id"] for candidate in user_evictions}
            # Sort remaining active rows for deterministic global eviction.
            remaining = sorted((candidate for candidate in survivors if candidate["session_id"] not in user_eviction_ids), key=session_eviction_key)
            # Select the oldest remaining rows needed to leave one global slot.
            global_evictions = remaining[: max(0, len(remaining) - total_limit + 1)]
            # Build the final keep set after both cap policies.
            keep_ids = {candidate["session_id"] for candidate in survivors} - user_eviction_ids - {candidate["session_id"] for candidate in global_evictions}
            # Remove every inactive, expired, or overflow predecessor under held locks.
            for candidate in current:
                # Skip rows selected for retention.
                if candidate["session_id"] in keep_ids:
                    # Continue without rewriting healthy authority.
                    continue
                # Delete one exact native or bridge row.
                self._delete_mysql_session(cursor, candidate)
            # Insert the new independent session row after deterministic cleanup.
            self._insert_mysql_session(cursor, row)
            # Return the detached request-local row after outer commit.
            return resolved_session_row(row, str(token))

        # Execute one transaction and return the committed compatible session.
        return self._mysql_session_transaction(create)

    # Resolve one session through the native unique index or keyed document primary key.
    def get_session_by_token(self, token: str) -> dict | None:
        # Verify readiness and derive the one-way lookup identity before database contact.
        self.ensure_ready()
        # Hash the supplied bearer without storing or logging it.
        digest = session_token_digest(token)
        # Open one read-only provider lease.
        connection = self.connect()
        # Protect lease cleanup across decoding and validation failure.
        try:
            # Open a dictionary cursor for backend-neutral row mapping.
            cursor = connection.cursor(dictionary=True)
            # Select only the unique digest-indexed row.
            rows = self._select_mysql_sessions(cursor, token_digest=digest)
            # Return the established missing result without revealing lookup detail.
            if not rows:
                # Avoid creating or scanning unrelated session rows.
                return None
            # Require unique-index behavior even on the document bridge.
            if len(rows) != 1:
                # Preserve conflicting authority for operator recovery.
                raise ConflictError("Session storage requires operator recovery")
            # Attach only the caller-supplied bearer to the detached request row.
            return resolved_session_row(rows[0], token)
        # Always close the read lease and its implicit transaction.
        finally:
            # Return or discard the connection through the pool boundary.
            connection.close()

    # List validated sessions through native account indexing or the bounded bridge prefix.
    def list_sessions(self, user_id: str | None = None, limit: int | None = None) -> list[dict]:
        # Reject invalid limits before database contact.
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            # Keep internal callers on one bounded contract.
            raise ValueError("Session result limit is invalid")
        # Verify readiness before a read-only provider checkout.
        self.ensure_ready()
        # Open one request-scoped read lease.
        connection = self.connect()
        # Protect cleanup across decoding or validation failure.
        try:
            # Use dictionary rows for canonical payload extraction.
            cursor = connection.cursor(dictionary=True)
            # Select either the account index or complete bounded registry.
            rows = self._select_mysql_sessions(cursor, user_id=user_id)
            # Sort newest activity first with opaque id tie-breaking.
            rows.sort(key=session_eviction_key, reverse=True)
            # Return detached durable rows without bearer plaintext.
            return copy.deepcopy(rows if limit is None else rows[:limit])
        # Always close the read lease and implicit transaction.
        finally:
            # Return or discard the connection through the pool boundary.
            connection.close()

    # Mutate one session by opaque id under a native or bridge row lock.
    def update_session(self, session_id: str, mutator: Callable[[dict], dict | None]) -> dict | None:
        # Own exact selection and replacement in one explicit transaction.
        def update(_connection, cursor) -> dict | None:
            # Lock the unique opaque-id match.
            rows = self._select_mysql_sessions(cursor, session_id=session_id, for_update=True)
            # Return the established missing result without inserting a default.
            if not rows:
                # Preserve caller-visible absence.
                return None
            # Reject impossible duplicates on the compatibility bridge.
            if len(rows) != 1:
                # Preserve conflicting rows for operator recovery.
                raise ConflictError("Session storage requires operator recovery")
            # Give the caller a detached complete row under the held lock.
            candidate = mutator(copy.deepcopy(rows[0]))
            # Treat None as a conditional no-change result.
            if candidate is None:
                # Return no committed row.
                return None
            # Validate the replacement before database mutation.
            row = durable_session_row(candidate)
            # Forbid credential or opaque identity changes outside rotation.
            if row["session_id"] != rows[0]["session_id"] or row["token_digest"] != rows[0]["token_digest"]:
                # Preserve the original row without cross-index mutation.
                raise ConflictError("Session storage requires operator recovery")
            # Replace only the selected native or bridge row.
            self._update_mysql_session(cursor, rows[0], row)
            # Return a detached durable copy after commit.
            return copy.deepcopy(row)

        # Execute and return the exact conditional transition result.
        return self._mysql_session_transaction(update)

    # Rotate one bearer and CSRF pair through exact compare-and-swap predicates.
    def rotate_session(self, session_id: str, token: str, expected_generation: int, replacement_token: str, replacement_csrf: str, updated_at: str) -> dict | None:
        # Hash current and replacement credentials before database contact.
        current_digest = session_token_digest(token)
        # Hash replacement authority separately for unique-index enforcement.
        replacement_digest = session_token_digest(replacement_token)
        # Reject a no-op replacement through the generic compare-and-swap miss.
        if current_digest == replacement_digest:
            # Avoid issuing dual equivalent credential state.
            return None

        # Own unique lookup, collision check, and index replacement in one transaction.
        def rotate(_connection, cursor) -> dict | None:
            # Lock the exact current bearer row through its native or bridge primary index.
            rows = self._select_mysql_sessions(cursor, token_digest=current_digest, for_update=True)
            # Return a generic miss when the supplied credential is unknown.
            if len(rows) != 1:
                # Avoid disclosing whether id, token, or generation differed.
                return None
            # Resolve the sole validated candidate.
            row = rows[0]
            # Require exact id, active lifecycle, and generation.
            if row["session_id"] != session_id or row["status"] != "active" or row["generation"] != expected_generation:
                # Return the same generic compare-and-swap miss.
                return None
            # Lock any replacement digest row to prove the unique target is unused.
            if self._select_mysql_sessions(cursor, token_digest=replacement_digest, for_update=True):
                # Preserve both authorities without replacement.
                raise ConflictError("Session storage requires operator recovery")
            # Apply only reviewed rotation fields.
            replacement = copy.deepcopy(row)
            # Replace the bearer lookup identity.
            replacement["token_digest"] = replacement_digest
            # Replace the CSRF proof atomically with bearer authority.
            replacement["csrf_token"] = replacement_csrf
            # Advance native generation exactly once.
            replacement["generation"] = expected_generation + 1
            # Record issuance and activity at the common timestamp.
            replacement["issued_at"] = updated_at
            # Record the same instant as last server activity.
            replacement["updated_at"] = updated_at
            # Validate the complete replacement before updating indexes.
            replacement = durable_session_row(replacement)
            # Replace one native or bridge row inside this transaction.
            self._update_mysql_session(cursor, row, replacement)
            # Return the detached replacement with one-time plaintext authority.
            return resolved_session_row(replacement, replacement_token)

        # Execute the compare-and-swap transaction.
        return self._mysql_session_transaction(rotate)

    # Revoke one session selected by bearer digest.
    def revoke_session_by_token(self, token: str, updated_at: str) -> int:
        # Hash the bearer before database contact.
        digest = session_token_digest(token)

        # Own direct lookup and conditional lifecycle replacement.
        def revoke(_connection, cursor) -> int:
            # Lock only the digest-selected session.
            rows = self._select_mysql_sessions(cursor, token_digest=digest, for_update=True)
            # Preserve idempotent unknown or already-revoked behavior.
            if len(rows) != 1 or rows[0]["status"] != "active":
                # Return zero without writing authority.
                return 0
            # Build the complete revoked replacement.
            replacement = copy.deepcopy(rows[0])
            # Mark the session unusable immediately.
            replacement["status"] = "revoked"
            # Record the shared lifecycle timestamp.
            replacement["updated_at"] = updated_at
            # Replace only this selected row.
            self._update_mysql_session(cursor, rows[0], durable_session_row(replacement))
            # Return the exact changed count.
            return 1

        # Execute and return the conditional transition.
        return self._mysql_session_transaction(revoke)

    # Revoke one session selected by opaque id.
    def revoke_session_by_id(self, session_id: str, updated_at: str) -> int:
        # Retain the exact transition count outside the callback.
        changed = {"value": 0}

        # Apply one conditional active-to-revoked transition.
        def revoke(row: dict) -> dict:
            # Change only an active session.
            if row["status"] == "active":
                # Mark the selected credential unusable.
                row["status"] = "revoked"
                # Record the common lifecycle timestamp.
                row["updated_at"] = updated_at
                # Count the committed transition once.
                changed["value"] = 1
            # Return the complete row for replacement.
            return row

        # Reuse exact opaque-id row locking and replacement.
        self.update_session(session_id, revoke)
        # Return only whether a row changed.
        return changed["value"]

    # Revoke active sessions for one account and optional external provider.
    def revoke_sessions_for_user(self, user_id: str, updated_at: str, auth_method: str | None = None) -> int:
        # Own the account-index scan and replacements inside one transaction.
        def revoke(_connection, cursor) -> int:
            # Lock only the selected account rows on schema five and the bounded bridge otherwise.
            rows = self._select_mysql_sessions(cursor, user_id=user_id, for_update=True)
            # Count exact active transitions.
            changed = 0
            # Visit validated selected rows.
            for row in rows:
                # Skip inactive or differently authenticated sessions.
                if row["status"] != "active" or (auth_method is not None and row.get("auth_method", "local") != auth_method):
                    # Continue without rewriting terminal rows.
                    continue
                # Build one complete revoked replacement.
                replacement = copy.deepcopy(row)
                # Mark the credential unusable.
                replacement["status"] = "revoked"
                # Record the common lifecycle timestamp.
                replacement["updated_at"] = updated_at
                # Replace only the selected row.
                self._update_mysql_session(cursor, row, durable_session_row(replacement))
                # Count the active transition.
                changed += 1
            # Return the exact committed count after outer transaction success.
            return changed

        # Execute and return the account-scoped transition count.
        return self._mysql_session_transaction(revoke)

    # Delete every session for one permanently ended disposable identity.
    def delete_sessions_for_user(self, user_id: str) -> int:
        # Own account selection and deletion inside one transaction.
        def delete(_connection, cursor) -> int:
            # Lock only rows belonging to the selected identity.
            rows = self._select_mysql_sessions(cursor, user_id=user_id, for_update=True)
            # Delete each validated exact row.
            for row in rows:
                # Remove one native or bridge credential row.
                self._delete_mysql_session(cursor, row)
            # Return the exact deleted count.
            return len(rows)

        # Execute and return the durable removal count.
        return self._mysql_session_transaction(delete)

    # Remove inactive, expired, and deterministic global overflow rows.
    def expire_sessions(self, now: datetime, total_limit: int) -> int:
        # Reject invalid limits before database contact.
        if isinstance(total_limit, bool) or not isinstance(total_limit, int) or total_limit < 1:
            # Keep cleanup on one bounded contract.
            raise ValueError("Session storage limits are invalid")

        # Own complete bounded sweep inside one transaction.
        def sweep(_connection, cursor) -> int:
            # Lock the complete bounded registry because the total cap spans identities.
            rows = self._select_mysql_sessions(cursor, for_update=True)
            # Sort active unexpired rows from oldest to newest.
            active = sorted((row for row in rows if row["status"] == "active" and not session_is_expired(row, now)), key=session_eviction_key)
            # Retain only the newest bounded active rows.
            keep_ids = {row["session_id"] for row in active[-total_limit:]}
            # Select every inactive, expired, or overflow row.
            removals = [row for row in rows if row["session_id"] not in keep_ids]
            # Delete validated selected rows one at a time.
            for row in removals:
                # Remove one exact native or bridge row.
                self._delete_mysql_session(cursor, row)
            # Return the exact removed count.
            return len(removals)

        # Execute and return the bounded cleanup count.
        return self._mysql_session_transaction(sweep)

    # Replace every first-class row for compatibility fixtures and reset snapshots.
    def replace_sessions(self, sessions: list[dict]) -> None:
        # Require a list before database contact.
        if not isinstance(sessions, list):
            # Preserve current authority on invalid caller state.
            raise ValueError("Session replacement requires a list")
        # Validate every replacement and strip plaintext before deletion begins.
        rows = [durable_session_row(session) for session in sessions]
        # Reject duplicate credential or opaque identities before opening a transaction.
        if len({row["token_digest"] for row in rows}) != len(rows) or len({row["session_id"] for row in rows}) != len(rows):
            # Preserve current authority for recovery.
            raise ConflictError("Session storage requires operator recovery")

        # Own complete replacement inside one transaction.
        def replace(_connection, cursor) -> None:
            # Lock and validate every current session before deletion.
            current = self._select_mysql_sessions(cursor, for_update=True)
            # Remove only first-class session rows through the active schema lane.
            for current_row in current:
                # Delete one exact current credential row.
                self._delete_mysql_session(cursor, current_row)
            # Publish every replacement independently.
            for row in rows:
                # Insert one native or bridge row.
                self._insert_mysql_session(cursor, row)
            # Lock the importer marker so replacement can make first-class rows authoritative.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (_MYSQL_SESSION_IMPORT_MARKER,))
            # Fetch the optional marker row.
            marker = cursor.fetchone()
            # Insert or replace only the fixed non-secret completion marker.
            if marker is None:
                # Create the authoritative marker beside ordinary documents.
                cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s)", (_MYSQL_SESSION_IMPORT_MARKER, json.dumps({"schema_version": _MYSQL_SESSION_STORAGE_VERSION, "status": "complete"}, sort_keys=True), utc_now()))
            else:
                # Restore the exact marker shape without touching session rows.
                cursor.execute("UPDATE casino_documents SET payload_json = %s, updated_at = %s WHERE document_key = %s", (json.dumps({"schema_version": _MYSQL_SESSION_STORAGE_VERSION, "status": "complete"}, sort_keys=True), utc_now(), _MYSQL_SESSION_IMPORT_MARKER))
            # Return no secret-bearing result.
            return None

        # Execute the complete replacement transaction.
        self._mysql_session_transaction(replace)
