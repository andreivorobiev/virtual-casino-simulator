# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""First-class keyed JSON session rows with one-shot legacy import."""

# Import annotations so the mixin can refer to inherited provider helpers.
from __future__ import annotations
# Import deep-copy support so mutators never retain provider-owned row references.
import copy
# Import JSON decoding for strict per-session and legacy import boundaries.
import json
# Import UTC timestamps for expiry and deterministic cleanup.
from datetime import datetime, timezone
# Import portable filesystem paths for the keyed session registry.
from pathlib import Path
# Import caller mutation typing without coupling the mixin to auth.
from typing import Any, Callable

# Import the application schema marker retained in compatibility projections.
from casino.config import SCHEMA_VERSION
# Import first-class session codecs and ordering shared with relational providers.
from casino.core.storage.sessions import durable_session_row, resolved_session_row, session_eviction_key, session_is_expired, session_token_digest
# Import the fixed public conflict used for malformed or inconsistent session evidence.
from casino.errors import ConflictError

# Name the private registry format independently from public API and ordinary document schemas.
_JSON_SESSION_STORAGE_VERSION = 1
# Name only canonical per-session files so temp, marker, lock, and forensic files are never decoded as sessions.
_JSON_SESSION_FILE_PREFIX = "session-"


# Add keyed session ownership to the local JSON provider.
class JsonSessionMixin:
    # Return the private directory containing one durable document per bearer digest.
    def session_rows_path(self) -> Path:
        # Honor an exact injected legacy parent for isolated auth fixtures and migrations.
        override = getattr(self, "_session_rows_override", None)
        # Keep production authentication rows below data/auth when no fixture override exists.
        return override if override is not None else self.data_dir / "auth" / "sessions-v2"

    # Return the durable one-shot importer marker path.
    def session_import_marker_path(self) -> Path:
        # Keep migration completion separate from every credential-derived file name.
        return self.session_rows_path() / ".legacy-imported.json"

    # Return the exact keyed path for one already-validated bearer digest.
    def _session_row_path(self, token_digest: str) -> Path:
        # Construct one constant-format direct lookup path without caller-controlled separators.
        return self.session_rows_path() / f"{_JSON_SESSION_FILE_PREFIX}{token_digest}.json"

    # Decode one security-sensitive JSON file without fallback, backup, or normalization.
    def _read_session_json_locked(self, path: Path) -> Any:
        # Read exact bytes so only true absence can select an empty store.
        try:
            # Retain source bytes until strict decoding succeeds.
            encoded = path.read_bytes()
        # Preserve the missing-row distinction for direct bearer lookups.
        except FileNotFoundError:
            # Return no row without creating a file or marker.
            return None
        # Collapse every other filesystem failure without exposing the path.
        except OSError:
            # Refuse session visibility until an operator can inspect the source.
            raise ConflictError("Session storage requires operator recovery") from None
        # Decode strict UTF-8 JSON and reject duplicate object keys.
        try:
            # Reuse the provider's canonical duplicate-key rejection hook.
            return json.loads(encoded.decode("utf-8"), object_pairs_hook=self._unique_json_object)
        # Collapse malformed text and hostile nesting into the fixed recovery boundary.
        except (UnicodeError, ValueError, RecursionError):
            # Preserve the exact source bytes without rewriting or backing them up.
            raise ConflictError("Session storage requires operator recovery") from None

    # Publish one already-validated durable row at its digest-derived path.
    def _write_session_row_locked(self, row: dict) -> None:
        # Resolve the keyed path only from the canonical validated digest.
        path = self._session_row_path(row["token_digest"])
        # Reuse atomic fsync-and-replace publication while the session gate remains held.
        self._write_json(path, row)

    # Read and validate every keyed row under the provider-wide session boundary.
    def _session_rows_locked(self) -> list[tuple[Path, dict]]:
        # Return an empty registry when the private directory has not been created yet.
        if not self.session_rows_path().exists():
            # Preserve first-run read-only behavior without creating session state.
            return []
        # Start a deterministic path-ordered collection for collision checks and tests.
        rows: list[tuple[Path, dict]] = []
        # Inspect only canonical direct children whose names carry an exact bearer digest.
        for path in sorted(self.session_rows_path().glob(f"{_JSON_SESSION_FILE_PREFIX}[0-9a-f]*.json"), key=lambda item: item.name):
            # Read one exact per-session object without corruption fallback.
            value = self._read_session_json_locked(path)
            # Validate the complete durable shape before exposing any partial registry.
            row = durable_session_row(value)
            # Require path identity to match the digest inside the row.
            if path != self._session_row_path(row["token_digest"]):
                # Fail closed on renamed, aliased, or truncated credential files.
                raise ConflictError("Session storage requires operator recovery")
            # Retain the validated pair for atomic lifecycle operations.
            rows.append((path, row))
        # Reject duplicate opaque session identifiers across distinct token digests.
        if len({row["session_id"] for _path, row in rows}) != len(rows):
            # Preserve all conflicting files for operator recovery.
            raise ConflictError("Session storage requires operator recovery")
        # Return the complete validated registry.
        return rows

    # Enter the common recovery and cross-process boundary for every session operation.
    def _session_operation(self):
        # Reuse the provider's stable global gate because reset must exclude session visibility.
        return self._json_global_gate()

    # Import the retired aggregate session document exactly once. (SESSION-014)
    def import_legacy_sessions(self, legacy_key: str | Path, default_factory: Callable[[], dict]) -> None:
        # Reject hidden session mutation from inside a game-action planner.
        self._reject_planner_mutation()
        # Bind keyed rows beside an explicitly injected legacy path for isolated compatibility fixtures.
        if isinstance(legacy_key, Path):
            # Derive one private sibling directory without changing the retired source name.
            self._session_rows_override = legacy_key.resolve().parent / "sessions-v2"
        # Serialize migration with every local provider operation.
        with self.lock:
            # Exclude reset and independent processes for the complete idempotent import.
            with self._session_operation():
                # Complete recoverable wallet actions before changing shared provider state.
                self._recover_all_json_actions_locked()
                # Read an existing marker before consulting any retired credential document.
                marker = self._read_session_json_locked(self.session_import_marker_path())
                # Stop after verifying a prior importer completed with the exact format.
                if marker is not None:
                    # Reject tampered or future migration markers without reading legacy authority.
                    if marker != {"schema_version": _JSON_SESSION_STORAGE_VERSION, "status": "complete"}:
                        # Preserve the marker and every session row for operator inspection.
                        raise ConflictError("Session storage requires operator recovery")
                    # Return because the aggregate document is permanently retired as authority.
                    return
                # Resolve the exact legacy provider document path once under the held gate.
                legacy_path = self.document_path(legacy_key)
                # Read strict legacy bytes without ordinary corruption fallback.
                legacy = self._read_session_json_locked(legacy_path)
                # Select the caller's reviewed empty seed only when the legacy document is absent.
                if legacy is None:
                    # Evaluate the lazy default under the same migration boundary.
                    legacy = default_factory()
                # Require the canonical aggregate container before importing any session.
                if not isinstance(legacy, dict) or not isinstance(legacy.get("sessions"), list):
                    # Preserve malformed legacy evidence without creating a marker.
                    raise ConflictError("Session storage requires operator recovery")
                # Validate every legacy row and strip bearer plaintext before the first write.
                rows = [durable_session_row(session) for session in legacy["sessions"]]
                # Reject duplicate token or opaque session identities before partial publication.
                if len({row["token_digest"] for row in rows}) != len(rows) or len({row["session_id"] for row in rows}) != len(rows):
                    # Preserve the complete legacy source for operator recovery.
                    raise ConflictError("Session storage requires operator recovery")
                # Create the private registry directory only after complete source validation.
                self.session_rows_path().mkdir(parents=True, exist_ok=True)
                # Publish each independently keyed session idempotently under the held gate.
                for row in rows:
                    # Reject a conflicting partial prior import while accepting an exact replay.
                    existing = self._read_session_json_locked(self._session_row_path(row["token_digest"]))
                    # Stop when a partial import row has different durable bytes.
                    if existing is not None and durable_session_row(existing) != row:
                        # Preserve both source and keyed evidence for recovery.
                        raise ConflictError("Session storage requires operator recovery")
                    # Publish the row when it was not already committed by an interrupted import.
                    if existing is None:
                        # Write one credential-derived file without rewriting unrelated sessions.
                        self._write_session_row_locked(row)
                # Publish completion only after every source row is durable.
                self._write_json(self.session_import_marker_path(), {"schema_version": _JSON_SESSION_STORAGE_VERSION, "status": "complete"})
                # Retire the aggregate source after completion; a crash before this point remains idempotent.
                try:
                    # Remove only the exact legacy document, never its parent or unrelated auth state.
                    legacy_path.unlink(missing_ok=True)
                # Fail closed when retirement cannot be completed under the migration gate.
                except OSError:
                    # The marker still prevents the source from regaining authority on restart.
                    raise ConflictError("Session storage requires operator recovery") from None

    # Create one independently keyed durable session with deterministic cap eviction.
    def create_session(self, session: dict, per_user_limit: int, total_limit: int) -> dict:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Validate limits before entering durable storage.
        if isinstance(per_user_limit, bool) or isinstance(total_limit, bool) or not isinstance(per_user_limit, int) or not isinstance(total_limit, int) or per_user_limit < 1 or total_limit < per_user_limit:
            # Refuse invalid internal policy without writing session authority.
            raise ValueError("Session storage limits are invalid")
        # Capture the plaintext bearer only for the detached result.
        token = session.get("token")
        # Validate and strip plaintext before acquiring the storage boundary.
        row = durable_session_row(session)
        # Serialize local row enumeration, eviction, and publication.
        with self.lock:
            # Exclude reset and independent processes from the compound cap operation.
            with self._session_operation():
                # Complete recoverable wallet actions before shared provider mutation.
                self._recover_all_json_actions_locked()
                # Validate every existing row before deleting or publishing anything.
                existing = self._session_rows_locked()
                # Reject a credential or session-id collision without replacing authority.
                if any(candidate["token_digest"] == row["token_digest"] or candidate["session_id"] == row["session_id"] for _path, candidate in existing):
                    # Preserve both records for operator recovery.
                    raise ConflictError("Session storage requires operator recovery")
                # Use the new row's creation instant as the deterministic sweep reference.
                now = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")).astimezone(timezone.utc)
                # Remove inactive and absolutely expired rows before cap calculation.
                survivors = [(path, candidate) for path, candidate in existing if candidate["status"] == "active" and not session_is_expired(candidate, now)]
                # Collect this identity's active rows in deterministic least-recently-used order.
                owned = sorted(((path, candidate) for path, candidate in survivors if candidate["user_id"] == row["user_id"]), key=lambda item: session_eviction_key(item[1]))
                # Select predecessors that must leave room for the new account session.
                user_evictions = owned[: max(0, len(owned) - per_user_limit + 1)]
                # Exclude account evictions before applying the global bounded registry cap.
                user_eviction_paths = {path for path, _candidate in user_evictions}
                # Build remaining active rows in global eviction order.
                remaining = sorted(((path, candidate) for path, candidate in survivors if path not in user_eviction_paths), key=lambda item: session_eviction_key(item[1]))
                # Select the oldest remaining rows required to leave one global slot.
                global_evictions = remaining[: max(0, len(remaining) - total_limit + 1)]
                # Delete expired, revoked, account-overflow, and global-overflow files only after full validation.
                keep_paths = {path for path, _candidate in survivors} - user_eviction_paths - {path for path, _candidate in global_evictions}
                # Visit every current row once so obsolete credential files cannot remain resolvable.
                for path, _candidate in existing:
                    # Remove only rows excluded from the final active set.
                    if path not in keep_paths:
                        # Unlink the exact direct child while the global gate is held.
                        path.unlink()
                # Publish the new independent session row last.
                self._write_session_row_locked(row)
        # Return a detached request-local result carrying only the newly supplied bearer.
        return resolved_session_row(row, str(token))

    # Resolve one session through its direct bearer-digest path.
    def get_session_by_token(self, token: str) -> dict | None:
        # Reject planner re-entry because JSON visibility first performs recoverable provider work.
        self._reject_planner_mutation()
        # Derive the fixed path identity before entering filesystem state.
        digest = session_token_digest(token)
        # Serialize direct reads with local mutation and reset.
        with self.lock:
            # Exclude reset and independent process writes for one exact row read.
            with self._session_operation():
                # Complete recoverable wallet actions before publishing provider visibility.
                self._recover_all_json_actions_locked()
                # Read only the digest-selected session file.
                value = self._read_session_json_locked(self._session_row_path(digest))
                # Return the established missing result without scanning unrelated sessions.
                if value is None:
                    # Preserve enumeration resistance for unknown bearer credentials.
                    return None
                # Validate the durable row and attach only the caller-supplied request bearer.
                return resolved_session_row(value, token)

    # List validated sessions with optional account and result bounds.
    def list_sessions(self, user_id: str | None = None, limit: int | None = None) -> list[dict]:
        # Reject planner re-entry because complete visibility may converge recoverable provider work.
        self._reject_planner_mutation()
        # Reject invalid limits before touching provider state.
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            # Keep bounded callers on one exact internal contract.
            raise ValueError("Session result limit is invalid")
        # Serialize registry enumeration with local writers.
        with self.lock:
            # Exclude reset and independent process mutation for the complete snapshot.
            with self._session_operation():
                # Complete recoverable wallet actions before exposing session metadata.
                self._recover_all_json_actions_locked()
                # Select detached rows after complete registry validation.
                rows = [copy.deepcopy(row) for _path, row in self._session_rows_locked() if user_id is None or row["user_id"] == user_id]
        # Sort newest activity first with opaque id as the stable tie-break.
        rows.sort(key=session_eviction_key, reverse=True)
        # Apply the optional caller bound without exposing plaintext bearer material.
        return rows if limit is None else rows[:limit]

    # Mutate one opaque session row atomically without rewriting unrelated sessions.
    def update_session(self, session_id: str, mutator: Callable[[dict], dict | None]) -> dict | None:
        # Reject hidden mutation from inside a planner.
        self._reject_planner_mutation()
        # Serialize lookup and replacement with every local writer.
        with self.lock:
            # Exclude reset and independent processes across the exact row transition.
            with self._session_operation():
                # Complete recoverable wallet actions before changing shared provider state.
                self._recover_all_json_actions_locked()
                # Validate the complete registry before selecting one opaque id.
                matches = [(path, row) for path, row in self._session_rows_locked() if row["session_id"] == session_id]
                # Return the established missing result when no row matches.
                if not matches:
                    # Avoid creating session authority from an updater default.
                    return None
                # Reject impossible duplicates without changing either row.
                if len(matches) != 1:
                    # Preserve conflicting evidence for operator recovery.
                    raise ConflictError("Session storage requires operator recovery")
                # Give the caller a detached copy under the exact row boundary.
                updated = mutator(copy.deepcopy(matches[0][1]))
                # Treat an explicit None as a no-change result for conditional transitions.
                if updated is None:
                    # Return no committed row to the caller.
                    return None
                # Validate the complete replacement and forbid identity or digest changes here.
                row = durable_session_row(updated)
                # Require credential and opaque identity stability outside the rotation method.
                if row["session_id"] != matches[0][1]["session_id"] or row["token_digest"] != matches[0][1]["token_digest"]:
                    # Refuse cross-row mutation without replacing the original.
                    raise ConflictError("Session storage requires operator recovery")
                # Atomically replace only the selected per-session file.
                self._write_session_row_locked(row)
                # Return a detached durable copy containing no bearer plaintext.
                return copy.deepcopy(row)

    # Rotate one exact session bearer and CSRF pair under generation compare-and-swap.
    def rotate_session(self, session_id: str, token: str, expected_generation: int, replacement_token: str, replacement_csrf: str, updated_at: str) -> dict | None:
        # Reject hidden provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Resolve both credential identities before entering the storage gate.
        current_digest = session_token_digest(token)
        # Resolve the replacement digest separately so equality can fail closed.
        replacement_digest = session_token_digest(replacement_token)
        # Refuse replacement with the current credential because rotation must invalidate it.
        if current_digest == replacement_digest:
            # Return the same compare-and-swap miss shape as a changed session.
            return None
        # Serialize the two-path atomic visibility transition with local writers.
        with self.lock:
            # Exclude reset and independent processes while changing credential identity.
            with self._session_operation():
                # Complete recoverable wallet actions before session mutation.
                self._recover_all_json_actions_locked()
                # Read only the supplied current credential path.
                value = self._read_session_json_locked(self._session_row_path(current_digest))
                # Return a compare-and-swap miss for unknown credentials.
                if value is None:
                    # Avoid revealing whether the id or bearer failed.
                    return None
                # Validate the durable row before checking caller predicates.
                row = durable_session_row(value)
                # Require exact id, active lifecycle, and expected generation.
                if row["session_id"] != session_id or row["status"] != "active" or row["generation"] != expected_generation:
                    # Return one generic compare-and-swap miss without mutation.
                    return None
                # Reject a replacement digest that already belongs to another session.
                if self._read_session_json_locked(self._session_row_path(replacement_digest)) is not None:
                    # Preserve both authorities instead of overwriting either.
                    raise ConflictError("Session storage requires operator recovery")
                # Apply only the reviewed credential, generation, CSRF, issue, and activity fields.
                row["token_digest"] = replacement_digest
                # Replace the browser/native CSRF proof atomically with the bearer.
                row["csrf_token"] = replacement_csrf
                # Advance generation exactly once from the matched value.
                row["generation"] = expected_generation + 1
                # Record the replacement issuance time for native clients.
                row["issued_at"] = updated_at
                # Record activity at the same exact instant.
                row["updated_at"] = updated_at
                # Validate the complete replacement before publishing either path change.
                durable_session_row(row)
                # Publish the replacement digest path before removing the old credential path.
                self._write_session_row_locked(row)
                # Remove the predecessor path so it cannot resolve after the gate releases.
                self._session_row_path(current_digest).unlink()
                # Return the detached replacement with its one-time plaintext bearer.
                return resolved_session_row(row, replacement_token)

    # Revoke one digest-selected active session.
    def revoke_session_by_token(self, token: str, updated_at: str) -> int:
        # Reject hidden credential mutation from inside a game-action planner.
        self._reject_planner_mutation()
        # Resolve the direct lookup digest before constructing the conditional updater.
        digest = session_token_digest(token)
        # Retain the committed transition count outside the callback.
        changed = {"value": 0}

        # Revoke only an active matching row.
        def revoke(row: dict) -> dict:
            # Leave an already terminal row byte-identical.
            if row["status"] != "active" or row["token_digest"] != digest:
                # Return the unchanged durable row.
                return row
            # Mark the credential unusable before it can be observed again.
            row["status"] = "revoked"
            # Record the caller-owned common lifecycle timestamp.
            row["updated_at"] = updated_at
            # Count the sole active-to-revoked transition.
            changed["value"] = 1
            # Return the complete replacement.
            return row

        # Resolve the row directly so an unknown bearer does not scan every session id.
        with self.lock:
            # Exclude reset and independent process writes for the transition.
            with self._session_operation():
                # Complete recoverable wallet actions before session mutation.
                self._recover_all_json_actions_locked()
                # Read the exact selected row.
                value = self._read_session_json_locked(self._session_row_path(digest))
                # Return zero for an unknown bearer without creating state.
                if value is None:
                    # Preserve idempotent logout behavior.
                    return 0
                # Validate, mutate, validate again, and publish only this row.
                updated = durable_session_row(revoke(durable_session_row(value)))
                # Replace one independent session file atomically.
                self._write_session_row_locked(updated)
        # Return only whether an active credential changed.
        return changed["value"]

    # Revoke one session selected by opaque id.
    def revoke_session_by_id(self, session_id: str, updated_at: str) -> int:
        # Retain the exact transition count outside the callback.
        changed = {"value": 0}

        # Apply one conditional lifecycle transition.
        def revoke(row: dict) -> dict:
            # Change only a currently active row.
            if row["status"] == "active":
                # Make the session unusable immediately.
                row["status"] = "revoked"
                # Record the shared lifecycle timestamp.
                row["updated_at"] = updated_at
                # Count the committed transition once.
                changed["value"] = 1
            # Return the complete row for atomic publication.
            return row

        # Delegate row selection and strict replacement to the common id updater.
        self.update_session(session_id, revoke)
        # Return only whether an active row changed.
        return changed["value"]

    # Revoke active sessions for one account and optional external method.
    def revoke_sessions_for_user(self, user_id: str, updated_at: str, auth_method: str | None = None) -> int:
        # Reject hidden provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Count exact active transitions after full registry validation.
        changed = 0
        # Serialize the account-scoped scan and replacements.
        with self.lock:
            # Exclude reset and independent processes for the complete multi-row change.
            with self._session_operation():
                # Complete recoverable wallet actions before session mutation.
                self._recover_all_json_actions_locked()
                # Validate every row before publishing the first replacement.
                rows = self._session_rows_locked()
                # Visit only validated rows for the selected account.
                for _path, row in rows:
                    # Skip unrelated, inactive, or differently authenticated sessions.
                    if row["user_id"] != user_id or row["status"] != "active" or (auth_method is not None and row.get("auth_method", "local") != auth_method):
                        # Continue without rewriting an unrelated per-session file.
                        continue
                    # Make the selected credential unusable.
                    row["status"] = "revoked"
                    # Record the common lifecycle timestamp.
                    row["updated_at"] = updated_at
                    # Validate and publish only this selected row.
                    self._write_session_row_locked(durable_session_row(row))
                    # Count one active-to-revoked transition.
                    changed += 1
        # Return the exact number of changed rows.
        return changed

    # Delete every session for one permanently ended disposable identity.
    def delete_sessions_for_user(self, user_id: str) -> int:
        # Reject hidden provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Count exact deleted rows for tests and teardown evidence.
        deleted = 0
        # Serialize the account scan with local provider operations.
        with self.lock:
            # Exclude reset and independent processes across complete deletion.
            with self._session_operation():
                # Complete recoverable wallet actions before session deletion.
                self._recover_all_json_actions_locked()
                # Validate every row before deleting the first selected file.
                rows = self._session_rows_locked()
                # Visit validated keyed rows only.
                for path, row in rows:
                    # Skip unrelated account sessions.
                    if row["user_id"] != user_id:
                        # Continue without touching another identity.
                        continue
                    # Delete the exact direct per-session path.
                    path.unlink()
                    # Count the removed credential record.
                    deleted += 1
        # Return the exact removal count.
        return deleted

    # Remove inactive, expired, and deterministic overflow rows.
    def expire_sessions(self, now: datetime, total_limit: int) -> int:
        # Reject hidden provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Reject invalid internal limits before reading durable rows.
        if isinstance(total_limit, bool) or not isinstance(total_limit, int) or total_limit < 1:
            # Keep provider cleanup on one bounded contract.
            raise ValueError("Session storage limits are invalid")
        # Count exact removed rows after complete registry validation.
        removed = 0
        # Serialize sweep with local session mutations.
        with self.lock:
            # Exclude reset and independent processes across the bounded sweep.
            with self._session_operation():
                # Complete recoverable wallet actions before session deletion.
                self._recover_all_json_actions_locked()
                # Validate the complete registry before selecting removals.
                rows = self._session_rows_locked()
                # Keep only active, unexpired rows before the total cap.
                active = sorted(((path, row) for path, row in rows if row["status"] == "active" and not session_is_expired(row, now)), key=lambda item: session_eviction_key(item[1]))
                # Retain only the newest bounded active rows.
                keep = {path for path, _row in active[-total_limit:]}
                # Remove every row outside the final active bounded set.
                for path, _row in rows:
                    # Skip retained active rows.
                    if path in keep:
                        # Continue without rewriting healthy session bytes.
                        continue
                    # Delete one obsolete credential-derived file.
                    path.unlink()
                    # Count the exact removed row.
                    removed += 1
        # Return only the bounded cleanup count.
        return removed

    # Replace all first-class rows for compatibility fixtures and reset snapshots.
    def replace_sessions(self, sessions: list[dict]) -> None:
        # Reject hidden provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Require a bounded list before touching current session authority.
        if not isinstance(sessions, list):
            # Preserve the current store on invalid caller state.
            raise ValueError("Session replacement requires a list")
        # Validate every replacement and strip plaintext before deletion begins.
        rows = [durable_session_row(session) for session in sessions]
        # Reject duplicate credential or opaque identities before publication.
        if len({row["token_digest"] for row in rows}) != len(rows) or len({row["session_id"] for row in rows}) != len(rows):
            # Preserve the complete current registry for operator recovery.
            raise ConflictError("Session storage requires operator recovery")
        # Serialize complete replacement with every local provider operation.
        with self.lock:
            # Exclude reset and independent processes across full test publication.
            with self._session_operation():
                # Complete recoverable wallet actions before replacing session state.
                self._recover_all_json_actions_locked()
                # Validate current rows before deleting any credential file.
                current = self._session_rows_locked()
                # Remove only canonical current per-session files.
                for path, _row in current:
                    # Delete the exact direct child under the held gate.
                    path.unlink()
                # Ensure the registry exists before publishing replacements and marker.
                self.session_rows_path().mkdir(parents=True, exist_ok=True)
                # Publish each independent replacement row.
                for row in rows:
                    # Atomically write one keyed session document.
                    self._write_session_row_locked(row)
                # Mark the first-class store authoritative so any legacy fixture path stays retired.
                self._write_json(self.session_import_marker_path(), {"schema_version": _JSON_SESSION_STORAGE_VERSION, "status": "complete"})
