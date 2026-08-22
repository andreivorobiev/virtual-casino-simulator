# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""PostgreSQL first-class session rows for the clean native schema."""

# Import annotations so the mixin remains independent of provider declaration order.
from __future__ import annotations

# Import deep-copy support so callbacks never retain decoded database row references.
import copy
# Import UTC instants for deterministic session expiry and cap enforcement.
from datetime import datetime, timezone
# Import portable path typing for the shared retired-document importer contract.
from pathlib import Path
# Import caller operation typing without coupling this module to the concrete provider.
from typing import Any, Callable

# Import the stable application timestamp used by importer metadata rows.
from casino.core.clock import utc_now
# Import the backend-neutral JSON decoder used for JSONB and modeled rows.
from casino.core.storage.base import _decode_json
# Import shared session validation, resolution, expiry, ordering, and credential hashing.
from casino.core.storage.sessions import durable_session_row, resolved_session_row, session_eviction_key, session_is_expired, session_token_digest
# Import the fixed recovery boundary for malformed or inconsistent session authority.
from casino.errors import ConflictError

# Name one provider-owned completed-import row shared with the MySQL session contract.
_POSTGRES_SESSION_IMPORT_MARKER = "auth/session/v2/legacy-imported"
# Name the exact marker payload independently from application document schemas.
_POSTGRES_SESSION_STORAGE_VERSION = 1
# Keep the provider-facing native failure independent from SQL, target, or credential details.
_POSTGRES_SESSION_RECOVERY_ERROR = "Session storage requires operator recovery"


# Add native first-class session ownership to the PostgreSQL provider.
class PostgresSessionMixin:
    # Require exact migration-five native session ownership before every row operation.
    def _require_postgres_session_storage(self) -> None:
        # Verify checksum-bound runtime readiness before consulting its sanitized version.
        self.ensure_ready()
        # Refuse held, dirty, future, or otherwise non-native schemas without partial access.
        if self._schema_version != 5:
            # Preserve every source row for explicit operator recovery.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)

    # Decode and verify the stable completed-import row under its transaction lock.
    def _lock_postgres_session_registry(self, cursor) -> None:
        # Lock the existing marker before any complete-registry row lock or insertion.
        cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (_POSTGRES_SESSION_IMPORT_MARKER,))
        # Read the marker under the transaction-owned exclusive row lock.
        marker = cursor.fetchone()
        # Decode the fixed marker without permitting malformed JSONB to escape this boundary.
        try:
            # Accept only the exact completed import authority object.
            complete = isinstance(marker, dict) and _decode_json(marker.get("payload_json")) == {"schema_version": _POSTGRES_SESSION_STORAGE_VERSION, "status": "complete"}
        # Normalize invalid connector values into the fixed recovery result.
        except (TypeError, ValueError):
            # Treat malformed evidence as incomplete without replacing it.
            complete = False
        # Refuse direct provider use that bypassed import or retained malformed authority.
        if not complete:
            # Preserve all session and legacy rows for operator inspection.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)

    # Convert one JSONB row into a validated canonical durable session.
    def _session_from_postgres_row(self, row: dict) -> dict:
        # Reject non-mapping cursor output before any partial field becomes authoritative.
        if not isinstance(row, dict):
            # Keep the complete unexpected row inside the provider recovery boundary.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
        # Decode connector strings or already-decoded JSONB objects uniformly.
        session = durable_session_row(_decode_json(row.get("session_json")))
        # Bind every indexed native column to the canonical JSONB payload.
        try:
            # Compare duplicated index values without coercing the canonical payload.
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
        # Normalize malformed indexed values into the fixed recovery boundary.
        except (TypeError, ValueError, OverflowError):
            # Preserve the inconsistent source row for operator inspection.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR) from None
        # Reject split authority between indexed columns and the canonical payload.
        if inconsistent:
            # Refuse all partial projections from the inconsistent row.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
        # Return the validated detached durable payload.
        return session

    # Select validated native session rows through reviewed indexed predicates.
    def _select_postgres_sessions(self, cursor, *, token_digest: str | None = None, session_id: str | None = None, user_id: str | None = None, for_update: bool = False) -> list[dict]:
        # Require exact native schema ownership before issuing session SQL.
        self._require_postgres_session_storage()
        # Select by the unique bearer digest for request authentication.
        if token_digest is not None:
            # Select the locked literal only for an explicit mutation transaction.
            if for_update:
                # Execute one fixed unique-index locking lookup with a bound digest.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE token_digest = %s FOR UPDATE", (token_digest,))
            else:
                # Execute one fixed read-only unique-index lookup with a bound digest.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE token_digest = %s", (token_digest,))
        # Select by the opaque primary id for touch, rotation, and revocation.
        elif session_id is not None:
            # Select the locked literal only for an explicit mutation transaction.
            if for_update:
                # Execute one fixed primary-key locking lookup with a bound identity.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE session_id = %s FOR UPDATE", (session_id,))
            else:
                # Execute one fixed read-only primary-key lookup with a bound identity.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE session_id = %s", (session_id,))
        # Select by the account index for inventory and bulk lifecycle operations.
        elif user_id is not None:
            # Select the locked literal only for an explicit mutation transaction.
            if for_update:
                # Preserve deterministic row order while locking the account rows.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE user_id = %s ORDER BY updated_at, created_at, session_id FOR UPDATE", (user_id,))
            else:
                # Preserve deterministic row order for the read-only account snapshot.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions WHERE user_id = %s ORDER BY updated_at, created_at, session_id", (user_id,))
        else:
            # Select the locked literal only for a complete-registry mutation.
            if for_update:
                # Lock the deterministic complete registry for caps, sweeps, or replacement.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions ORDER BY updated_at, created_at, session_id FOR UPDATE")
            else:
                # Read the deterministic complete registry without row locks.
                cursor.execute("SELECT session_id, token_digest, user_id, status, updated_at, expires_at, generation, session_json FROM casino_sessions ORDER BY updated_at, created_at, session_id")
        # Validate and detach every selected dictionary row before returning it.
        return [self._session_from_postgres_row(row) for row in cursor.fetchall()]

    # Insert one validated native session row through bound PostgreSQL parameters.
    def _insert_postgres_session(self, cursor, row: dict) -> None:
        # Serialize the complete canonical payload through the host provider codec.
        payload = self._canonical_json(row)
        # Bind indexed authority and canonical JSONB in one native insert.
        cursor.execute(
            "INSERT INTO casino_sessions (session_id, token_digest, user_id, status, created_at, updated_at, expires_at, generation, session_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSONB))",
            (row["session_id"], row["token_digest"], row["user_id"], row["status"], row["created_at"], row["updated_at"], row["expires_at"], row["generation"], payload),
        )

    # Replace one validated session under its held primary-key row lock.
    def _update_postgres_session(self, cursor, prior: dict, row: dict) -> None:
        # Serialize the complete canonical replacement payload once.
        payload = self._canonical_json(row)
        # Update every duplicated index and the canonical JSONB atomically.
        cursor.execute(
            "UPDATE casino_sessions SET token_digest = %s, user_id = %s, status = %s, created_at = %s, updated_at = %s, expires_at = %s, generation = %s, session_json = CAST(%s AS JSONB) WHERE session_id = %s",
            (row["token_digest"], row["user_id"], row["status"], row["created_at"], row["updated_at"], row["expires_at"], row["generation"], payload, prior["session_id"]),
        )
        # Require the exact selected predecessor to change once.
        if cursor.rowcount != 1:
            # Roll back through the host provider transaction boundary.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)

    # Delete one validated session under its held primary-key row lock.
    def _delete_postgres_session(self, cursor, row: dict) -> None:
        # Remove only the selected opaque session row.
        cursor.execute("DELETE FROM casino_sessions WHERE session_id = %s", (row["session_id"],))
        # Require one exact row removal without accepting a concurrent disappearance.
        if cursor.rowcount != 1:
            # Preserve ambiguous storage for explicit operator recovery.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)

    # Run one complete session operation through the provider-owned transaction boundary.
    def _postgres_session_operation(self, operation: Callable[[Any, Any], Any], *, commit: bool) -> Any:
        # Refuse provider access attempted from inside a supposedly pure planner.
        self._reject_planner_mutation()
        # Keep every statement and result validation inside one host-owned transaction.
        with self._database_cursor(commit=commit) as (connection, cursor):
            # Return the caller result only after the context completes its commit or rollback.
            return operation(connection, cursor)

    # Import the retired aggregate document exactly once inside one database transaction.
    def import_legacy_sessions(self, legacy_key: str | Path, default_factory: Callable[[], dict]) -> None:
        # Convert state-store paths to the portable document key used by relational storage.
        legacy_document_key = str(legacy_key).replace("\\", "/")

        # Own the singleton import decision, source, destination, and marker atomically.
        def import_rows(_connection, cursor) -> None:
            # Serialize first import while the marker may not yet exist using a stable control row.
            cursor.execute("SELECT current_version FROM casino_schema_migration_state WHERE state_id = 1 FOR UPDATE")
            # Require the exact clean native schema identity already verified by ensure_ready.
            state = cursor.fetchone()
            # Refuse missing or inconsistent singleton state without consulting legacy authority.
            if not isinstance(state, dict) or state.get("current_version") != 5:
                # Preserve every document and session row for operator recovery.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Lock the optional completed-import marker after the stable singleton mutex.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (_POSTGRES_SESSION_IMPORT_MARKER,))
            # Fetch the optional marker row.
            marker = cursor.fetchone()
            # Stop after verifying one exact prior completion marker.
            if marker is not None:
                # Decode and require the finite marker shape.
                if not isinstance(marker, dict) or _decode_json(marker.get("payload_json")) != {"schema_version": _POSTGRES_SESSION_STORAGE_VERSION, "status": "complete"}:
                    # Preserve malformed authority for operator recovery.
                    raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
                # Return without consulting the retired aggregate document.
                return None
            # Lock the exact legacy document while deciding first-run or import behavior.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (legacy_document_key,))
            # Fetch the optional aggregate source.
            source = cursor.fetchone()
            # Use the reviewed lazy seed only when the legacy document is genuinely absent.
            legacy = default_factory() if source is None else _decode_json(source.get("payload_json"))
            # Require the canonical aggregate container before the first destination write.
            if not isinstance(legacy, dict) or not isinstance(legacy.get("sessions"), list):
                # Preserve malformed source bytes without publishing completion.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Validate every legacy row and strip plaintext bearer material.
            rows = [durable_session_row(session) for session in legacy["sessions"]]
            # Reject duplicate digest or opaque identities before partial publication.
            if len({row["token_digest"] for row in rows}) != len(rows) or len({row["session_id"] for row in rows}) != len(rows):
                # Preserve the complete aggregate source for recovery.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Read every current first-class row under locks before collision checks.
            current = self._select_postgres_sessions(cursor, for_update=True)
            # Build current identities for exact interrupted-import replay validation.
            by_digest = {row["token_digest"]: row for row in current}
            # Build the opaque-id authority index separately.
            by_id = {row["session_id"]: row for row in current}
            # Import each validated source row independently inside this transaction.
            for row in rows:
                # Accept only an exact replay when either identity already exists.
                existing = by_digest.get(row["token_digest"]) or by_id.get(row["session_id"])
                # Refuse a collision without overwriting either authority.
                if existing is not None and existing != row:
                    # Preserve both source rows for operator recovery.
                    raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
                # Insert only a genuinely absent source row.
                if existing is None:
                    # Publish one native row through the schema-five table.
                    self._insert_postgres_session(cursor, row)
            # Serialize the exact completed marker with the provider-owned JSON codec.
            marker_payload = self._canonical_json({"schema_version": _POSTGRES_SESSION_STORAGE_VERSION, "status": "complete"})
            # Publish completion only after every destination row succeeds.
            cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, CAST(%s AS JSONB), %s)", (_POSTGRES_SESSION_IMPORT_MARKER, marker_payload, utc_now()))
            # Retire the aggregate source after marker and destination writes are staged.
            if source is not None:
                # Delete only the exact locked legacy document key.
                cursor.execute("DELETE FROM casino_documents WHERE document_key = %s", (legacy_document_key,))
                # Require the previously locked source to be removed once.
                if cursor.rowcount != 1:
                    # Refuse ambiguous legacy authority.
                    raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Return no secret-bearing result.
            return None

        # Execute the complete idempotent importer under one committed transaction.
        self._postgres_session_operation(import_rows, commit=True)

    # Create one session with deterministic per-account and global cap eviction.
    def create_session(self, session: dict, per_user_limit: int, total_limit: int) -> dict:
        # Validate internal caps before opening a transaction.
        if isinstance(per_user_limit, bool) or isinstance(total_limit, bool) or not isinstance(per_user_limit, int) or not isinstance(total_limit, int) or per_user_limit < 1 or total_limit < per_user_limit:
            # Refuse invalid policy without database contact.
            raise ValueError("Session storage limits are invalid")
        # Retain the request-local bearer separately from durable validation.
        token = session.get("token")
        # Validate and strip plaintext credential material before connection checkout.
        row = durable_session_row(session)

        # Own collision checks, eviction, and insertion in one transaction.
        def create(_connection, cursor) -> dict:
            # Serialize every complete-registry creator through the stable import marker.
            self._lock_postgres_session_registry(cursor)
            # Lock the bounded complete registry because the total cap spans all users.
            current = self._select_postgres_sessions(cursor, for_update=True)
            # Reject credential or opaque-id collision without replacement.
            if any(candidate["token_digest"] == row["token_digest"] or candidate["session_id"] == row["session_id"] for candidate in current):
                # Preserve existing authority for recovery.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Parse the creation timestamp as the deterministic sweep reference.
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
                # Delete one exact native row.
                self._delete_postgres_session(cursor, candidate)
            # Insert the new independent session row after deterministic cleanup.
            self._insert_postgres_session(cursor, row)
            # Return the detached request-local row after outer commit.
            return resolved_session_row(row, str(token))

        # Execute one committed transaction and return the compatible session.
        return self._postgres_session_operation(create, commit=True)

    # Resolve one session through the native unique digest index.
    def get_session_by_token(self, token: str) -> dict | None:
        # Hash the supplied bearer before database contact.
        digest = session_token_digest(token)

        # Read and validate the exact digest-selected row in one transaction.
        def read(_connection, cursor) -> dict | None:
            # Select only the unique digest-indexed row.
            rows = self._select_postgres_sessions(cursor, token_digest=digest)
            # Return the established missing result without revealing lookup detail.
            if not rows:
                # Avoid creating or scanning unrelated session rows.
                return None
            # Require exact unique-index behavior despite hostile model cursors.
            if len(rows) != 1:
                # Preserve conflicting authority for recovery.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Attach only the caller-supplied bearer to the detached request row.
            return resolved_session_row(rows[0], token)

        # End the successful read transaction without committing storage changes.
        return self._postgres_session_operation(read, commit=False)

    # List validated sessions with optional account and result bounds.
    def list_sessions(self, user_id: str | None = None, limit: int | None = None) -> list[dict]:
        # Reject invalid limits before database contact.
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            # Keep internal callers on one bounded contract.
            raise ValueError("Session result limit is invalid")

        # Read and detach the requested bounded snapshot.
        def read(_connection, cursor) -> list[dict]:
            # Select either the account index or complete bounded registry.
            rows = self._select_postgres_sessions(cursor, user_id=user_id)
            # Sort newest activity first with opaque id tie-breaking.
            rows.sort(key=session_eviction_key, reverse=True)
            # Return detached durable rows without bearer plaintext.
            return copy.deepcopy(rows if limit is None else rows[:limit])

        # End the successful read transaction without committing storage changes.
        return self._postgres_session_operation(read, commit=False)

    # Mutate one session by opaque id under its primary-key row lock.
    def update_session(self, session_id: str, mutator: Callable[[dict], dict | None]) -> dict | None:
        # Own exact selection and replacement in one explicit transaction.
        def update(_connection, cursor) -> dict | None:
            # Lock the unique opaque-id match.
            rows = self._select_postgres_sessions(cursor, session_id=session_id, for_update=True)
            # Return the established missing result without inserting a default.
            if not rows:
                # Preserve caller-visible absence.
                return None
            # Reject impossible duplicates from a hostile or malformed cursor.
            if len(rows) != 1:
                # Preserve conflicting rows for recovery.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Give the caller a detached complete row under the held lock.
            candidate = mutator(copy.deepcopy(rows[0]))
            # Treat None as a conditional no-change result.
            if candidate is None:
                # Return no committed replacement row.
                return None
            # Validate the replacement before database mutation.
            row = durable_session_row(candidate)
            # Forbid credential or opaque identity changes outside rotation.
            if row["session_id"] != rows[0]["session_id"] or row["token_digest"] != rows[0]["token_digest"]:
                # Preserve the original row without cross-index mutation.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
            # Replace only the selected native row.
            self._update_postgres_session(cursor, rows[0], row)
            # Return a detached durable copy after commit.
            return copy.deepcopy(row)

        # Execute and return the exact conditional transition result.
        return self._postgres_session_operation(update, commit=True)

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

        # Own unique lookup, collision check, and index replacement atomically.
        def rotate(_connection, cursor) -> dict | None:
            # Lock the exact current bearer row through its unique native index.
            rows = self._select_postgres_sessions(cursor, token_digest=current_digest, for_update=True)
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
            if self._select_postgres_sessions(cursor, token_digest=replacement_digest, for_update=True):
                # Preserve both authorities without replacement.
                raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)
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
            # Replace one native row inside this transaction.
            self._update_postgres_session(cursor, row, replacement)
            # Return the detached replacement with one-time plaintext authority.
            return resolved_session_row(replacement, replacement_token)

        # Execute the compare-and-swap transaction.
        return self._postgres_session_operation(rotate, commit=True)

    # Revoke one session selected by bearer digest.
    def revoke_session_by_token(self, token: str, updated_at: str) -> int:
        # Hash the bearer before database contact.
        digest = session_token_digest(token)

        # Own direct lookup and conditional lifecycle replacement.
        def revoke(_connection, cursor) -> int:
            # Lock only the digest-selected session.
            rows = self._select_postgres_sessions(cursor, token_digest=digest, for_update=True)
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
            self._update_postgres_session(cursor, rows[0], durable_session_row(replacement))
            # Return the exact changed count.
            return 1

        # Execute and return the conditional transition.
        return self._postgres_session_operation(revoke, commit=True)

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

    # Revoke active sessions for one account and optional external method.
    def revoke_sessions_for_user(self, user_id: str, updated_at: str, auth_method: str | None = None) -> int:
        # Own the account-index scan and replacements inside one transaction.
        def revoke(_connection, cursor) -> int:
            # Lock only rows belonging to the selected identity.
            rows = self._select_postgres_sessions(cursor, user_id=user_id, for_update=True)
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
                self._update_postgres_session(cursor, row, durable_session_row(replacement))
                # Count the active transition.
                changed += 1
            # Return the exact committed count.
            return changed

        # Execute and return the account-scoped transition count.
        return self._postgres_session_operation(revoke, commit=True)

    # Delete every session for one permanently ended disposable identity.
    def delete_sessions_for_user(self, user_id: str) -> int:
        # Own account selection and deletion inside one transaction.
        def delete(_connection, cursor) -> int:
            # Lock only rows belonging to the selected identity.
            rows = self._select_postgres_sessions(cursor, user_id=user_id, for_update=True)
            # Delete each validated exact row.
            for row in rows:
                # Remove one native credential row.
                self._delete_postgres_session(cursor, row)
            # Return the exact deleted count.
            return len(rows)

        # Execute and return the durable removal count.
        return self._postgres_session_operation(delete, commit=True)

    # Remove inactive, expired, and deterministic global overflow rows.
    def expire_sessions(self, now: datetime, total_limit: int) -> int:
        # Reject invalid limits before database contact.
        if isinstance(total_limit, bool) or not isinstance(total_limit, int) or total_limit < 1:
            # Keep cleanup on one bounded contract.
            raise ValueError("Session storage limits are invalid")

        # Own the complete bounded sweep inside one transaction.
        def sweep(_connection, cursor) -> int:
            # Use the same marker-before-registry order as create and replacement.
            self._lock_postgres_session_registry(cursor)
            # Lock the complete registry because the total cap spans identities.
            rows = self._select_postgres_sessions(cursor, for_update=True)
            # Sort active unexpired rows from oldest to newest.
            active = sorted((row for row in rows if row["status"] == "active" and not session_is_expired(row, now)), key=session_eviction_key)
            # Retain only the newest bounded active rows.
            keep_ids = {row["session_id"] for row in active[-total_limit:]}
            # Select every inactive, expired, or overflow row.
            removals = [row for row in rows if row["session_id"] not in keep_ids]
            # Delete validated selected rows one at a time.
            for row in removals:
                # Remove one exact native row.
                self._delete_postgres_session(cursor, row)
            # Return the exact removed count.
            return len(removals)

        # Execute and return the bounded cleanup count.
        return self._postgres_session_operation(sweep, commit=True)

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
            # Preserve the complete current registry for recovery.
            raise ConflictError(_POSTGRES_SESSION_RECOVERY_ERROR)

        # Own complete replacement inside one transaction.
        def replace(_connection, cursor) -> None:
            # Validate and lock the importer marker before the complete registry.
            self._lock_postgres_session_registry(cursor)
            # Lock and validate every current session before deletion.
            current = self._select_postgres_sessions(cursor, for_update=True)
            # Remove only first-class native session rows.
            for current_row in current:
                # Delete the exact current credential row.
                self._delete_postgres_session(cursor, current_row)
            # Publish every validated replacement independently.
            for row in rows:
                # Insert one native session row.
                self._insert_postgres_session(cursor, row)
            # Return no secret-bearing result.
            return None

        # Execute the complete replacement transaction.
        self._postgres_session_operation(replace, commit=True)
