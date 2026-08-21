# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-neutral first-class session storage helpers for SESSION-014."""

# Import annotations so helper return types remain compatible with provider subclasses.
from __future__ import annotations
# Import deep-copy support so provider callers never share mutable durable session records.
import copy
# Import hashing so bearer credentials become fixed one-way lookup identities.
import hashlib
# Import UTC timestamp parsing for provider-owned expiry sweeps.
from datetime import datetime, timezone
# Import generic row values without coupling storage to the auth module.
from typing import Any

# Import the fixed operator-recovery error used by security-sensitive session persistence.
from casino.errors import ConflictError

# Domain-separate session bearer digests from every other identifier hash in the application.
_SESSION_TOKEN_DIGEST_DOMAIN = b"casino-session-token\0"
# Bound durable strings before they can become paths, SQL parameters, or unbounded Admin records.
_SESSION_STRING_LIMIT = 4096
# Name the reviewed lifecycle values retained by first-class providers.
_SESSION_STATUSES = frozenset({"active", "revoked"})


# Convert one opaque bearer into the stable digest used by every provider lookup.
def session_token_digest(token: str) -> str:
    # Reject empty or non-string bearer material before hashing it into a shared namespace.
    if not isinstance(token, str) or not token or len(token) > _SESSION_STRING_LIMIT:
        # Return one value-free recovery boundary without reflecting credential material.
        raise ConflictError("Session storage requires operator recovery")
    # Hash the domain-separated UTF-8 credential into the common lowercase identity.
    return hashlib.sha256(_SESSION_TOKEN_DIGEST_DOMAIN + token.encode("utf-8")).hexdigest()


# Parse one stored UTC timestamp without accepting timezone-ambiguous values.
def _session_time(value: Any) -> datetime:
    # Start protected parsing so malformed stored content never escapes through diagnostics.
    try:
        # Parse the established trailing-Z representation and normalize it to UTC.
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    # Collapse every invalid timestamp into the fixed session recovery boundary.
    except (TypeError, ValueError, OverflowError):
        # Preserve the offending row for operator recovery.
        raise ConflictError("Session storage requires operator recovery") from None
    # Reject naive timestamps because server-local time cannot safely govern authentication.
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        # Preserve the offending row for operator recovery.
        raise ConflictError("Session storage requires operator recovery")
    # Return the normalized aware instant used for deterministic ordering and expiry.
    return parsed.astimezone(timezone.utc)


# Validate and detach one durable session row without retaining a plaintext bearer.
def durable_session_row(session: Any, token: str | None = None) -> dict:
    # Require an object before reading any identity or lifecycle field.
    if not isinstance(session, dict):
        # Preserve malformed provider evidence instead of normalizing it.
        raise ConflictError("Session storage requires operator recovery")
    # Copy the complete bounded record so forward-compatible guest metadata survives storage moves.
    row = copy.deepcopy(session)
    # Remove request-local plaintext bearer material before any provider persists the row.
    embedded_token = row.pop("token", None)
    # Prefer an explicit request credential while ensuring any embedded plaintext was still removed.
    supplied_token = embedded_token if token is None else token
    # Derive the lookup digest from a supplied bearer when the caller has not precomputed it.
    if supplied_token is not None:
        # Replace any caller-authored digest with the digest of the exact bearer being persisted.
        row["token_digest"] = session_token_digest(supplied_token)
    # Require the canonical fixed-size digest after legacy conversion or provider decoding.
    digest = row.get("token_digest")
    # Reject a missing, non-string, mixed-case, or non-hex digest.
    if not isinstance(digest, str) or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        # Preserve malformed security evidence without guessing credential identity.
        raise ConflictError("Session storage requires operator recovery")
    # Require the opaque session and account identities used by lifecycle operations.
    for field in ("session_id", "user_id"):
        # Resolve one required identifier without coercing hostile objects.
        value = row.get(field)
        # Reject empty, oversized, or non-string durable identifiers.
        if not isinstance(value, str) or not value or len(value) > 191:
            # Preserve malformed security evidence without partial publication.
            raise ConflictError("Session storage requires operator recovery")
    # Require the finite reviewed lifecycle state.
    if row.get("status") not in _SESSION_STATUSES:
        # Reject unknown status values before they can become accidentally active.
        raise ConflictError("Session storage requires operator recovery")
    # Require the three timestamps that govern ordering, activity, and absolute expiry.
    for field in ("created_at", "updated_at", "expires_at"):
        # Validate the exact stored timestamp while retaining its compatible string bytes.
        _session_time(row.get(field))
    # Read generation separately because bool is an int subclass.
    generation = row.get("generation", 1)
    # Require a positive bounded native-session generation.
    if isinstance(generation, bool) or not isinstance(generation, int) or not 1 <= generation <= 9223372036854775807:
        # Preserve malformed generation evidence without silently resetting it.
        raise ConflictError("Session storage requires operator recovery")
    # Store the compatible explicit generation for legacy rows that omitted it.
    row["generation"] = generation
    # Require the CSRF token used by browser sessions without exposing its content.
    csrf_token = row.get("csrf_token")
    # Accept only the bounded generated proof shape already enforced by auth callers.
    if not isinstance(csrf_token, str) or not 32 <= len(csrf_token) <= 191:
        # Preserve malformed security evidence without issuing replacement authority.
        raise ConflictError("Session storage requires operator recovery")
    # Bound every retained string so a legacy document cannot inflate per-session storage.
    if any(isinstance(value, str) and len(value) > _SESSION_STRING_LIMIT for value in row.values()):
        # Reject the complete row rather than truncating security or diagnostic metadata.
        raise ConflictError("Session storage requires operator recovery")
    # Return the detached durable row with no plaintext bearer field.
    return row


# Return one request-local session after verifying its exact supplied bearer digest.
def resolved_session_row(session: Any, token: str) -> dict:
    # Validate and detach the durable provider row before adding request-local authority.
    row = durable_session_row(session)
    # Require the caller bearer to match the indexed durable digest exactly.
    if row["token_digest"] != session_token_digest(token):
        # Fail closed without revealing which half of the lookup was inconsistent.
        raise ConflictError("Session storage requires operator recovery")
    # Attach the already-supplied bearer only to the detached request-local copy.
    row["token"] = token
    # Return the compatible auth-layer shape without changing durable provider bytes.
    return row


# Return whether one validated active session has passed its absolute expiry.
def session_is_expired(session: dict, now: datetime) -> bool:
    # Compare normalized aware instants so lexical or timezone variations cannot change policy.
    return _session_time(session.get("expires_at")) <= now.astimezone(timezone.utc)


# Return the stable deterministic ordering used for cap eviction and bounded sweeps.
def session_eviction_key(session: dict) -> tuple[datetime, datetime, str]:
    # Order first by last activity, then creation, then opaque id for deterministic ties.
    return (_session_time(session.get("updated_at")), _session_time(session.get("created_at")), str(session.get("session_id")))
