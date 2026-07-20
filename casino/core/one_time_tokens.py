"""Purpose-bound one-time token records shared by enrollment and recovery flows. (issue #331)

Infrastructure only: this module mints, stores, and consumes durable one-time tokens. It never sends
mail, creates users, changes providers, or authorizes live use. Callers (invitations, email
verification, password reset, magic-link) own their own policy and delivery; this module owns only the
token lifecycle. No raw token, recipient, or digest is ever logged, returned in an error, or persisted
in raw form.
"""

# Import required dependency so bearer values are cryptographically random.
import hmac
# Import required dependency so stored verifiers are keyed one-way digests.
import hashlib
# Import required dependency so bearer values are cryptographically random.
import secrets
# Import required dependency so lifetime math uses aware timestamps.
from datetime import datetime, timedelta, timezone

# Import the keyed-digest secret and data root so records live beside other governed auth state.
from casino.config import DATA_DIR, SCHEMA_VERSION, TOKEN_DIGEST_KEY, TOKEN_MAX_ATTEMPTS, TOKEN_PURPOSE_TTL_SECONDS, TOKEN_RETENTION_SECONDS
# Import the shared clock so token timestamps match session and ledger records.
from casino.core.clock import utc_now
# Import the shared id helper so token and audit identifiers stay bounded and random.
from casino.core.ids import new_id
# Import atomic JSON persistence so concurrent consumption cannot double-spend a token.
from casino.core.state_store import read_json, update_json
# Import the application logger so audit events omit every sensitive field.
from casino.core import logger
# Import standard application errors for stable fail-closed envelopes.
from casino.errors import ValidationError

# Store the token document path in the governed auth namespace.
TOKENS_PATH = DATA_DIR / "auth" / "one_time_tokens.json"
# Enumerate the only purposes a token may carry; anything else fails closed.
PURPOSES = frozenset(TOKEN_PURPOSE_TTL_SECONDS.keys())
# Size the random bearer value at 256 bits of entropy.
TOKEN_BYTES = 32

# Build a new empty token document.
def default_tokens() -> dict:
    # Return the canonical schema-stamped container with no token rows.
    return {"schema_version": SCHEMA_VERSION, "tokens": []}

# Parse one stored ISO timestamp into an aware datetime for lifetime math.
def _parse(value: str) -> datetime:
    # Convert the shared Z suffix into an offset the standard parser accepts.
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

# Compute a keyed one-way digest so raw bearer values and recipients are never stored.
def _digest(value: str) -> str:
    # Return the HMAC-SHA256 hex digest of the value under the configured server key.
    return hmac.new(TOKEN_DIGEST_KEY.encode("utf-8"), str(value or "").encode("utf-8"), hashlib.sha256).hexdigest()

# Normalize a subject identifier so binding comparisons are stable across callers.
def _normalize_subject(subject: str) -> str:
    # Return the trimmed lower-cased subject so recipient matching is deterministic.
    return str(subject or "").strip().lower()

# Resolve the effective lifetime for one purpose, honoring an explicit override.
def _ttl_for(purpose: str, ttl_seconds) -> int:
    # Prefer a caller override when it is a positive integer.
    if ttl_seconds is not None:
        # Reject a non-positive override before any record is created.
        if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
            # Fail closed on malformed lifetime input.
            raise ValidationError("token ttl must be a positive integer", {"reason": "bad_ttl"})
        # Use the validated override.
        return ttl_seconds
    # Fall back to the purpose default lifetime.
    return TOKEN_PURPOSE_TTL_SECONDS[purpose]

# Issue one purpose-bound one-time token, returning the raw bearer exactly once.
def issue(purpose: str, subject: str, *, ttl_seconds=None, session_binding: str = "", max_attempts: int = None) -> dict:
    # Reject any purpose outside the fixed allowlist so tokens cannot be minted for unknown flows.
    if purpose not in PURPOSES:
        # Fail closed without echoing the requested purpose value.
        raise ValidationError("unknown token purpose", {"reason": "bad_purpose"})
    # Require a non-empty subject so every token is bound to an intended recipient.
    normalized_subject = _normalize_subject(subject)
    # Reject an empty recipient binding before a record is created.
    if not normalized_subject:
        # Fail closed on a missing subject binding.
        raise ValidationError("token subject is required", {"reason": "missing_subject"})
    # Mint a cryptographically random URL-safe bearer value returned to the caller only once.
    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    # Capture one issue instant for creation and expiry math.
    now = utc_now()
    # Resolve the effective lifetime for this purpose.
    lifetime = _ttl_for(purpose, ttl_seconds)
    # Compute the absolute expiry from the issue instant and lifetime.
    expires_at = (_parse(now) + timedelta(seconds=lifetime)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    # Allocate a stable record id used for revocation and audit without revealing the bearer.
    token_id = new_id("ott")
    # Build the stored record holding only keyed digests, never raw bearer or recipient values.
    record = {
        "token_id": token_id,
        "purpose": purpose,
        "subject_digest": _digest(normalized_subject),
        "token_digest": _digest(raw_token),
        "session_digest": _digest(session_binding) if session_binding else None,
        "created_at": now,
        "expires_at": expires_at,
        "consumed_at": None,
        "revoked_at": None,
        "attempts": 0,
        "max_attempts": max_attempts if isinstance(max_attempts, int) and max_attempts > 0 else TOKEN_MAX_ATTEMPTS,
        "audit_id": new_id("ottaudit"),
    }
    # Persist the record atomically, pruning expired rows in the same mutation.
    def mutate(state: dict) -> dict:
        # Normalize malformed persisted state into the canonical container.
        if not isinstance(state, dict) or "tokens" not in state:
            state = default_tokens()
        # Drop rows whose retention window has passed before appending the new record.
        state["tokens"] = [row for row in state["tokens"] if not _retention_elapsed(row, now)]
        # Append the new purpose-bound record.
        state["tokens"].append(record)
        # Return the mutated document for atomic persistence.
        return state
    # Route the write through the shared atomic helper (equivalent in JSON and MySQL).
    update_json(TOKENS_PATH, mutate, default_tokens)
    # Record a sensitive-field-free audit event for the issue.
    logger.info("one_time_token_issued", token_id=token_id, purpose=purpose, audit_id=record["audit_id"])
    # Return the record id plus the raw bearer once so the caller can deliver it out of band.
    return {"token_id": token_id, "token": raw_token, "purpose": purpose, "expires_at": expires_at}

# Decide whether a stored record has passed its retention window and may be pruned.
def _retention_elapsed(row: dict, now: str) -> bool:
    # Keep active, unconsumed, unrevoked, unexpired tokens regardless of age.
    reference = row.get("consumed_at") or row.get("revoked_at") or row.get("expires_at")
    # Retain rows without a reference timestamp rather than dropping them.
    if not reference:
        # Signal that the row must be retained.
        return False
    # Drop the row once the retention window past its terminal instant has elapsed.
    return (_parse(now) - _parse(reference)).total_seconds() > TOKEN_RETENTION_SECONDS

# Atomically consume one purpose-bound token, failing closed on every abuse case.
def consume(purpose: str, token: str, *, subject: str = None, session_binding: str = "") -> dict:
    # Reject any purpose outside the fixed allowlist so a token cannot be redeemed for an unknown flow.
    if purpose not in PURPOSES:
        # Fail closed without echoing the requested purpose value.
        raise ValidationError("unknown token purpose", {"reason": "bad_purpose"})
    # Reject an empty bearer before any record is scanned.
    if not token:
        # Fail closed on a missing bearer value.
        raise ValidationError("one-time token is invalid", {"reason": "missing_token"})
    # Compute the presented bearer's digest once for constant-time comparison.
    presented_digest = _digest(token)
    # Compute the optional subject digest for binding comparison.
    presented_subject_digest = _digest(_normalize_subject(subject)) if subject is not None else None
    # Compute the optional session digest for binding comparison.
    presented_session_digest = _digest(session_binding) if session_binding else None
    # Capture one consume instant for expiry and consumption math.
    now = utc_now()
    # Hold the resolved outcome across the atomic mutation so the caller sees a stable result.
    outcome = {}
    # Perform the whole find-validate-mark step inside one serialized mutation so replays cannot race.
    def mutate(state: dict) -> dict:
        # Treat malformed persisted state as an empty store.
        tokens = state.get("tokens", []) if isinstance(state, dict) else []
        # Locate a record whose purpose matches and whose stored digest matches in constant time.
        for row in tokens:
            # Restrict matching to the requested purpose so cross-purpose substitution fails closed.
            if row.get("purpose") != purpose:
                # Continue scanning other rows.
                continue
            # Compare the stored and presented bearer digests without early-exit timing leaks.
            if not hmac.compare_digest(str(row.get("token_digest", "")), presented_digest):
                # Continue scanning other rows.
                continue
            # Reject a revoked token before it can be redeemed.
            if row.get("revoked_at"):
                # Record the fail-closed reason for the audit and error.
                outcome["reason"] = "revoked"
                # Stop scanning after the matching record is resolved.
                break
            # Reject an already-consumed token so replays cannot succeed.
            if row.get("consumed_at"):
                # Record the replay reason.
                outcome["reason"] = "consumed"
                # Stop scanning after the matching record is resolved.
                break
            # Reject an expired token before it can be redeemed.
            if (_parse(now) - _parse(row.get("expires_at"))).total_seconds() > 0:
                # Record the expiry reason.
                outcome["reason"] = "expired"
                # Stop scanning after the matching record is resolved.
                break
            # Reject a token whose attempt budget is already exhausted.
            if row.get("attempts", 0) >= row.get("max_attempts", TOKEN_MAX_ATTEMPTS):
                # Record the throttle reason.
                outcome["reason"] = "too_many_attempts"
                # Stop scanning after the matching record is resolved.
                break
            # Enforce the subject binding when the caller supplies a subject to check.
            if presented_subject_digest is not None and not hmac.compare_digest(str(row.get("subject_digest", "")), presented_subject_digest):
                # Charge the mismatch against the attempt budget so brute force is bounded.
                row["attempts"] = row.get("attempts", 0) + 1
                # Record the binding-mismatch reason.
                outcome["reason"] = "subject_mismatch"
                # Stop scanning after the matching record is resolved.
                break
            # Enforce the session binding whenever one was captured at issue time.
            if row.get("session_digest") and (presented_session_digest is None or not hmac.compare_digest(str(row.get("session_digest")), presented_session_digest)):
                # Charge the mismatch against the attempt budget.
                row["attempts"] = row.get("attempts", 0) + 1
                # Record the session-binding reason.
                outcome["reason"] = "session_mismatch"
                # Stop scanning after the matching record is resolved.
                break
            # Mark the token consumed exactly once within the serialized mutation.
            row["consumed_at"] = now
            # Advance the attempt counter to reflect the successful redemption.
            row["attempts"] = row.get("attempts", 0) + 1
            # Publish the success details the caller needs without any sensitive field.
            outcome.update({"token_id": row["token_id"], "purpose": purpose, "audit_id": row.get("audit_id")})
            # Stop scanning after the matching record is resolved.
            break
        # Return the possibly-mutated document for atomic persistence.
        return state if isinstance(state, dict) else default_tokens()
    # Route the mutation through the shared atomic helper.
    update_json(TOKENS_PATH, mutate, default_tokens)
    # Fail closed uniformly when no record was successfully consumed.
    if "token_id" not in outcome:
        # Default an unmatched digest to a not-found reason without leaking which check failed.
        reason = outcome.get("reason", "not_found")
        # Emit a sensitive-field-free audit event for the rejected redemption.
        logger.warning("one_time_token_rejected", purpose=purpose, reason=reason)
        # Raise one uniform fail-closed error carrying only a non-sensitive reason code.
        raise ValidationError("one-time token is invalid", {"reason": reason})
    # Emit a sensitive-field-free audit event for the successful redemption.
    logger.info("one_time_token_consumed", token_id=outcome["token_id"], purpose=purpose, audit_id=outcome.get("audit_id"))
    # Return the redemption result without any raw bearer or recipient value.
    return outcome

# Revoke one token by id so a superseded or compromised token can no longer be consumed.
def revoke(token_id: str) -> bool:
    # Track whether a matching active token was revoked.
    revoked = {"done": False}
    # Capture one revoke instant.
    now = utc_now()
    # Apply the revocation atomically.
    def mutate(state: dict) -> dict:
        # Walk the stored rows to find the target token.
        for row in state.get("tokens", []) if isinstance(state, dict) else []:
            # Revoke only the matching, not-yet-terminal token.
            if row.get("token_id") == token_id and not row.get("revoked_at") and not row.get("consumed_at"):
                # Stamp the revocation instant.
                row["revoked_at"] = now
                # Record that a revocation occurred.
                revoked["done"] = True
        # Return the mutated document for atomic persistence.
        return state if isinstance(state, dict) else default_tokens()
    # Persist the revocation.
    update_json(TOKENS_PATH, mutate, default_tokens)
    # Audit the revocation without sensitive fields when one occurred.
    if revoked["done"]:
        # Emit the revocation audit event.
        logger.info("one_time_token_revoked", token_id=token_id)
    # Return whether a token was revoked.
    return revoked["done"]

# Revoke every active token for one purpose and subject so reissue invalidates prior tokens.
def revoke_for_subject(purpose: str, subject: str) -> int:
    # Compute the subject digest once for matching.
    subject_digest = _digest(_normalize_subject(subject))
    # Count how many active tokens were revoked.
    revoked = {"count": 0}
    # Capture one revoke instant.
    now = utc_now()
    # Apply the bulk revocation atomically.
    def mutate(state: dict) -> dict:
        # Walk the stored rows to find matching active tokens.
        for row in state.get("tokens", []) if isinstance(state, dict) else []:
            # Revoke each active token bound to this purpose and subject.
            if row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest) and not row.get("revoked_at") and not row.get("consumed_at"):
                # Stamp the revocation instant.
                row["revoked_at"] = now
                # Increment the revoked count.
                revoked["count"] += 1
        # Return the mutated document for atomic persistence.
        return state if isinstance(state, dict) else default_tokens()
    # Persist the bulk revocation.
    update_json(TOKENS_PATH, mutate, default_tokens)
    # Return the number of revoked tokens.
    return revoked["count"]

# Count active (unconsumed, unrevoked, unexpired) tokens for a purpose and subject for resend policy.
def active_count(purpose: str, subject: str) -> int:
    # Read the store without mutating it.
    state = read_json(TOKENS_PATH, default_tokens)
    # Compute the subject digest once for matching.
    subject_digest = _digest(_normalize_subject(subject))
    # Capture one comparison instant.
    now = utc_now()
    # Count matching active tokens.
    return sum(1 for row in (state.get("tokens", []) if isinstance(state, dict) else []) if row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest) and not row.get("consumed_at") and not row.get("revoked_at") and (_parse(now) - _parse(row.get("expires_at"))).total_seconds() <= 0)

# Remove tokens whose retention window has elapsed so the store stays bounded.
def cleanup() -> int:
    # Capture one cleanup instant.
    now = utc_now()
    # Count how many rows are pruned.
    pruned = {"count": 0}
    # Apply the prune atomically.
    def mutate(state: dict) -> dict:
        # Read the current rows.
        rows = state.get("tokens", []) if isinstance(state, dict) else []
        # Keep only rows still within their retention window.
        kept = [row for row in rows if not _retention_elapsed(row, now)]
        # Record how many rows were dropped.
        pruned["count"] = len(rows) - len(kept)
        # Return the pruned document for atomic persistence.
        return {"schema_version": SCHEMA_VERSION, "tokens": kept}
    # Persist the prune.
    update_json(TOKENS_PATH, mutate, default_tokens)
    # Return the pruned count.
    return pruned["count"]
