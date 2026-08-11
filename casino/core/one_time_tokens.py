# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Inert purpose-bound one-time-token infrastructure for future approved auth consumers. (#331)

The module owns bearer generation, keyed verification, lifecycle state, and atomic consumption. It
does not expose routes, send mail, create or recover accounts, enable signup, or authorize live use.
"""

# Import hashes so bearer and binding material can be persisted only as domain-separated HMACs.
import hashlib
# Import constant-time comparison so verifier checks do not short-circuit on matching prefixes.
import hmac
# Import the operating-system-backed random source used only by the production service.
import secrets
# Import timestamp arithmetic for bounded lifetimes and retention.
from datetime import datetime, timedelta
# Import portable paths so focused tests can isolate the durable token document.
from pathlib import Path
# Import callable types for deterministic clock, randomness, identifiers, and audit injection.
from typing import Any, Callable

# Import bounded token policy and the locally safe persistence root.
from casino.config import DATA_DIR, SCHEMA_VERSION, TOKEN_DIGEST_KEY, TOKEN_MAX_ATTEMPTS, TOKEN_PURPOSE_MAX_TTL_SECONDS, TOKEN_PURPOSE_TTL_SECONDS, TOKEN_RETENTION_SECONDS
# Import the application audit facade while keeping its accepted fields allowlisted below.
from casino.core import logger
# Import the shared production clock used by every default service operation.
from casino.core.clock import utc_now
# Import opaque identifier generation for records and audit correlation.
from casino.core.ids import new_id
# Import the provider-aware atomic document helpers.
from casino.core.state_store import read_json, update_json
# Import the standard validation envelope used by future service consumers.
from casino.errors import ValidationError

# Store token state in the governed authentication namespace.
TOKENS_PATH = DATA_DIR / "auth" / "one_time_tokens.json"
# Limit production bearer generation to 256 bits of operating-system entropy.
TOKEN_BYTES = 32
# Publish the fixed purpose vocabulary without authorizing any consuming flow.
PURPOSES = frozenset(TOKEN_PURPOSE_TTL_SECONDS)
# Return exactly one public failure reason for every consumption rejection.
INVALID_TOKEN_DETAILS = {"reason": "invalid_token"}
# Return exactly one public failure reason for every malformed or conflicting initiation request.
INVALID_REQUEST_DETAILS = {"reason": "invalid_request"}
# Restrict audit fields so raw or derived credential material cannot be logged accidentally.
AUDIT_FIELDS = frozenset({"audit_id", "count", "purpose", "reason", "token_id"})
# Enumerate internal rejection classes so logs stay useful without becoming caller-visible state.
AUDIT_REASONS = frozenset({"consumed", "expired", "inactive_subject", "malformed", "not_found", "revoked", "session_mismatch", "subject_mismatch", "too_many_attempts"})


# Build the canonical empty document used by JSON and MySQL providers.
def default_tokens() -> dict:
    # Return a fresh collection so callers never share mutable defaults.
    return {"schema_version": SCHEMA_VERSION, "tokens": []}


# Emit only allowlisted, non-secret audit fields through the application logger.
def _production_audit(level: str, event: str, fields: dict) -> None:
    # Resolve the requested bounded log level from the application audit facade.
    sink = getattr(logger, level)
    # Emit the event without ever accepting arbitrary caller-owned fields.
    sink(event, **fields)


# Own one isolated token store plus injectable deterministic dependencies.
class TokenService:
    # Initialize an inert token service without registering routes or starting background work.
    def __init__(self, *, store_path: Path = TOKENS_PATH, digest_key: str = TOKEN_DIGEST_KEY, clock: Callable[[], str] = utc_now, token_factory: Callable[[], str] | None = None, id_factory: Callable[[str], str] = new_id, audit_sink: Callable[[str, str, dict], None] = _production_audit) -> None:
        # Persist the exact isolated document path selected by the caller.
        self.store_path = Path(store_path)
        # Normalize the external keyed-digest secret without logging or returning it.
        self.digest_key = str(digest_key or "")
        # Reject weak or absent keys before any bearer can be minted.
        if len(self.digest_key.encode("utf-8")) < 32:
            # Raise a value-free configuration error that never includes the supplied key.
            raise RuntimeError("One-time-token digest configuration must contain at least 32 bytes")
        # Reject malformed policy configuration before durable state can be changed.
        if TOKEN_MAX_ATTEMPTS <= 0 or TOKEN_MAX_ATTEMPTS > 10 or TOKEN_RETENTION_SECONDS <= 0 or TOKEN_RETENTION_SECONDS > 31536000 or set(TOKEN_PURPOSE_TTL_SECONDS) != set(TOKEN_PURPOSE_MAX_TTL_SECONDS) or any(value <= 0 or value > TOKEN_PURPOSE_MAX_TTL_SECONDS[purpose] for purpose, value in TOKEN_PURPOSE_TTL_SECONDS.items()):
            # Raise a value-free configuration error suitable for startup diagnostics.
            raise RuntimeError("One-time-token policy configuration must use positive bounds")
        # Retain the injected aware-string clock for deterministic expiry tests.
        self.clock = clock
        # Use the production random bearer factory unless an isolated test supplied one.
        self.token_factory = token_factory or self._production_token
        # Retain the injected opaque identifier factory for deterministic non-secret tests.
        self.id_factory = id_factory
        # Retain the bounded audit sink so tests can inspect only sanitized events.
        self.audit_sink = audit_sink

    # Generate one production bearer with 256 bits of operating-system entropy.
    @staticmethod
    def _production_token() -> str:
        # Return a URL-safe bearer suitable for later out-of-band delivery by an approved consumer.
        return secrets.token_urlsafe(TOKEN_BYTES)

    # Parse the repository timestamp format into an aware datetime.
    @staticmethod
    def _parse(value: str) -> datetime:
        # Convert the shared Z suffix into the offset form accepted by the standard parser.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    # Normalize a subject identifier for stable binding without retaining its raw value.
    @staticmethod
    def _normalize_subject(subject: str | None) -> str:
        # Return the trimmed case-folded identity used only as HMAC input.
        return str(subject or "").strip().casefold()

    # Compute one domain-separated keyed digest for a bearer or binding value.
    def _digest(self, domain: str, value: str) -> str:
        # Prefix the value with a fixed domain so equal inputs cannot substitute across field types.
        payload = f"{domain}\0{value}".encode("utf-8")
        # Return the HMAC-SHA256 verifier without exposing the external key.
        return hmac.new(self.digest_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Emit one bounded audit event after filtering both field names and internal reason values.
    def _audit(self, level: str, event: str, **fields: Any) -> None:
        # Retain only explicitly approved non-secret audit keys.
        safe_fields = {key: value for key, value in fields.items() if key in AUDIT_FIELDS}
        # Collapse any unexpected internal reason into the generic non-sensitive category.
        if "reason" in safe_fields and safe_fields["reason"] not in AUDIT_REASONS:
            # Replace an unrecognized reason before it reaches application logs.
            safe_fields["reason"] = "malformed"
        # Forward the sanitized event to the configured audit sink.
        self.audit_sink(level, event, safe_fields)

    # Raise the one public initiation error without disclosing which validation failed.
    @staticmethod
    def _invalid_request() -> None:
        # Use a stable message and reason for unknown purpose, malformed bounds, and active conflicts.
        raise ValidationError("one-time token request is invalid", dict(INVALID_REQUEST_DETAILS))

    # Raise the one public consumption error without disclosing record state or binding details.
    @staticmethod
    def _invalid_token() -> None:
        # Use a stable message and reason for every token rejection path.
        raise ValidationError("one-time token is invalid", dict(INVALID_TOKEN_DETAILS))

    # Validate one purpose and return its fixed policy lifetime.
    def _purpose_ttl(self, purpose: str, ttl_seconds: int | None) -> int:
        # Reject unknown purposes through the generic initiation envelope.
        if purpose not in PURPOSES:
            # Hide the requested value and the purpose allowlist from the caller.
            self._invalid_request()
        # Read the configured upper bound for the accepted purpose.
        maximum = TOKEN_PURPOSE_TTL_SECONDS[purpose]
        # Use the fixed purpose policy when no shorter lifetime was requested.
        if ttl_seconds is None:
            # Return the configured maximum lifetime.
            return maximum
        # Reject booleans, non-integers, non-positive values, and attempts to extend policy.
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds <= 0 or ttl_seconds > maximum:
            # Preserve one public initiation error for every malformed lifetime.
            self._invalid_request()
        # Return the validated shorter lifetime.
        return ttl_seconds

    # Validate a bounded attempt policy without silently replacing malformed caller input.
    def _attempt_limit(self, max_attempts: int | None) -> int:
        # Use the configured bound when the caller omitted an override.
        if max_attempts is None:
            # Return the fixed default attempt budget.
            return TOKEN_MAX_ATTEMPTS
        # Reject booleans, non-integers, non-positive values, and policy expansion.
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts <= 0 or max_attempts > TOKEN_MAX_ATTEMPTS:
            # Preserve the generic initiation envelope.
            self._invalid_request()
        # Return the validated bounded attempt budget.
        return max_attempts

    # Validate and return the canonical token document without repairing corruption destructively.
    @staticmethod
    def _state(state: Any) -> dict:
        # Reject a malformed container instead of erasing possibly recoverable security state.
        if not isinstance(state, dict) or not isinstance(state.get("tokens"), list):
            # Raise a value-free internal error that causes the provider transaction to roll back.
            raise RuntimeError("One-time-token storage is malformed")
        # Reject malformed rows before a mutation can publish partial repairs.
        if any(not isinstance(row, dict) for row in state["tokens"]):
            # Raise a value-free internal error and preserve the original durable document.
            raise RuntimeError("One-time-token storage is malformed")
        # Return the validated mutable document.
        return state

    # Decide whether a row is currently active at one captured instant.
    def _active(self, row: dict, now: str) -> bool:
        # Candidate replacement rows remain non-consumable until explicit atomic promotion.
        if row.get("activation_state") == "candidate":
            # Preserve the predecessor as the sole active bearer during delivery.
            return False
        # Terminal consumed or revoked rows can never be active.
        if row.get("consumed_at") or row.get("revoked_at"):
            # Return the terminal-state result immediately.
            return False
        # Treat malformed or missing expiry as inactive and fail closed.
        try:
            # Compare the absolute expiry against the captured operation instant.
            return self._parse(row.get("expires_at")) >= self._parse(now)
        # Convert malformed stored timestamps into an inactive decision.
        except (TypeError, ValueError):
            # Refuse to classify malformed state as redeemable.
            return False

    # Decide whether a terminal row has passed the fixed retention window.
    def _retention_elapsed(self, row: dict, now: str) -> bool:
        # Select the first terminal or expiry timestamp used by retention policy.
        reference = row.get("consumed_at") or row.get("revoked_at") or row.get("expires_at")
        # Retain malformed rows for explicit operator recovery rather than deleting them silently.
        if not reference:
            # Signal that cleanup must preserve this row.
            return False
        # Compare the captured cleanup instant with the terminal reference.
        try:
            # Return true only after the complete retention period has elapsed.
            return (self._parse(now) - self._parse(reference)).total_seconds() > TOKEN_RETENTION_SECONDS
        # Preserve malformed rows rather than turning cleanup into destructive repair.
        except (TypeError, ValueError):
            # Signal that the row must be retained for investigation.
            return False

    # Prepare one record and its raw bearer without persisting either yet.
    def _prepare(self, purpose: str, subject: str, *, ttl_seconds: int | None, session_binding: str, max_attempts: int | None) -> tuple[dict, dict]:
        # Validate purpose and lifetime before generating bearer material.
        lifetime = self._purpose_ttl(purpose, ttl_seconds)
        # Normalize and require the intended subject binding.
        normalized_subject = self._normalize_subject(subject)
        # Reject absent subject identity through the generic initiation envelope.
        if not normalized_subject:
            # Preserve the generic initiation envelope.
            self._invalid_request()
        # Validate a bounded attempt budget without silent fallback.
        attempt_limit = self._attempt_limit(max_attempts)
        # Generate the raw bearer through the injected production or deterministic factory.
        raw_token = str(self.token_factory() or "")
        # Reject malformed injected output before any durable record is created.
        if not raw_token:
            # Preserve a value-free internal error because production randomness must never be empty.
            raise RuntimeError("One-time-token randomness source returned an invalid value")
        # Capture one issue instant for every timestamp derived by this operation.
        now = self.clock()
        # Compute the bounded absolute expiry from the captured aware timestamp.
        expires_at = (self._parse(now) + timedelta(seconds=lifetime)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        # Allocate one opaque record identifier that is safe for audit and revocation.
        token_id = self.id_factory("ott")
        # Allocate one independent opaque audit correlation identifier.
        audit_id = self.id_factory("ottaudit")
        # Build the durable record with only domain-separated keyed digests.
        record = {
            # Persist the non-secret opaque token identifier.
            "token_id": token_id,
            # Persist the fixed policy purpose used for cross-purpose isolation.
            "purpose": purpose,
            # Persist only a keyed subject verifier, never the raw subject.
            "subject_digest": self._digest("subject", normalized_subject),
            # Persist only a keyed bearer verifier, never the raw bearer.
            "token_digest": self._digest("bearer", raw_token),
            # Persist a keyed session verifier only when session binding is requested.
            "session_digest": self._digest("session", session_binding) if session_binding else None,
            # Persist the single captured creation timestamp.
            "created_at": now,
            # Persist the bounded absolute expiry timestamp.
            "expires_at": expires_at,
            # Initialize the exactly-once consumption marker.
            "consumed_at": None,
            # Reserve a caller-owned replay binding for recoverable multi-document consumers.
            "consume_idempotency_digest": None,
            # Initialize the explicit revocation marker.
            "revoked_at": None,
            # Initialize the bounded failed-or-successful attempt counter.
            "attempts": 0,
            # Persist the validated attempt ceiling for this record.
            "max_attempts": attempt_limit,
            # Persist the non-secret audit correlation identifier.
            "audit_id": audit_id,
        }
        # Build the one-time issuance receipt containing the raw bearer exactly once.
        receipt = {"token_id": token_id, "token": raw_token, "purpose": purpose, "expires_at": expires_at}
        # Return the durable record and ephemeral issuance receipt separately.
        return record, receipt

    # Issue one token only when no active token already exists for the purpose and subject.
    def issue(self, purpose: str, subject: str, *, ttl_seconds: int | None = None, session_binding: str = "", max_attempts: int | None = None) -> dict:
        # Prepare non-persisted record material after strict input validation.
        record, receipt = self._prepare(purpose, subject, ttl_seconds=ttl_seconds, session_binding=session_binding, max_attempts=max_attempts)
        # Track the transaction outcome without placing raw values in durable state.
        outcome = {"created": False, "reason": "active_token_exists"}

        # Append the record under the provider's atomic document-mutation boundary.
        def mutate(raw_state: Any) -> dict:
            # Validate the current durable document without destructive repair.
            state = self._state(raw_state)
            # Capture the prepared issue instant for consistent activity checks.
            now = record["created_at"]
            # Prune only rows whose terminal retention period has elapsed.
            state["tokens"] = [row for row in state["tokens"] if not self._retention_elapsed(row, now)]
            # Reject an active record with the same purpose and subject under the same lock.
            if any(row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), record["subject_digest"]) and self._active(row, now) for row in state["tokens"]):
                # Return unchanged state so a concurrent issuer cannot create a duplicate active token.
                return state
            # Reject an impossible bearer or identifier collision before persistence.
            if any(hmac.compare_digest(str(row.get("token_digest", "")), record["token_digest"]) or row.get("token_id") == record["token_id"] for row in state["tokens"]):
                # Record only a bounded internal collision class.
                outcome["reason"] = "malformed"
                # Return unchanged state so no ambiguous verifier is introduced.
                return state
            # Append exactly one active record under the serialized mutation.
            state["tokens"].append(record)
            # Publish the non-secret success flag after the row is in the pending document.
            outcome["created"] = True
            # Return the complete mutated document for atomic commit.
            return state

        # Persist the issuance decision through JSON file locking or MySQL row locking.
        update_json(self.store_path, mutate, default_tokens)
        # Reject active conflicts and impossible collisions through one generic initiation envelope.
        if not outcome["created"]:
            # Emit only the bounded internal class without subject or bearer material.
            self._audit("warning", "one_time_token_issue_rejected", purpose=purpose, reason=outcome["reason"])
            # Preserve one public initiation error regardless of internal cause.
            self._invalid_request()
        # Record the successful issuance with opaque identifiers only.
        self._audit("info", "one_time_token_issued", token_id=record["token_id"], purpose=purpose, audit_id=record["audit_id"])
        # Return the ephemeral bearer exactly once to the approved future consumer.
        return receipt

    # Atomically revoke prior active tokens and issue one replacement for resend or reissue policy.
    def reissue(self, purpose: str, subject: str, *, ttl_seconds: int | None = None, session_binding: str = "", max_attempts: int | None = None) -> dict:
        # Prepare the replacement record before entering the durable mutation.
        record, receipt = self._prepare(purpose, subject, ttl_seconds=ttl_seconds, session_binding=session_binding, max_attempts=max_attempts)
        # Track the number of superseded active records for sanitized audit evidence.
        outcome = {"revoked": 0, "created": False}

        # Revoke and append inside one provider-owned atomic mutation.
        def mutate(raw_state: Any) -> dict:
            # Validate the current document without silently dropping malformed state.
            state = self._state(raw_state)
            # Capture the replacement issue instant for every lifecycle decision.
            now = record["created_at"]
            # Reject an impossible bearer or identifier collision before changing prior rows.
            if any(hmac.compare_digest(str(row.get("token_digest", "")), record["token_digest"]) or row.get("token_id") == record["token_id"] for row in state["tokens"]):
                # Return unchanged state so the caller receives a generic request failure.
                return state
            # Walk every durable row while the document transaction is locked.
            for row in state["tokens"]:
                # Select only an active row bound to the same purpose and subject.
                if row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), record["subject_digest"]) and self._active(row, now):
                    # Stamp revocation at the exact replacement issue instant.
                    row["revoked_at"] = now
                    # Count the superseded row for sanitized audit evidence.
                    outcome["revoked"] += 1
            # Prune rows only after the fixed terminal retention period.
            state["tokens"] = [row for row in state["tokens"] if not self._retention_elapsed(row, now)]
            # Append the one replacement record in the same atomic transaction.
            state["tokens"].append(record)
            # Publish the success flag only after the pending document contains the replacement.
            outcome["created"] = True
            # Return the complete document for one commit.
            return state

        # Publish revocations and replacement together under the provider transaction.
        update_json(self.store_path, mutate, default_tokens)
        # Reject an impossible collision through the generic initiation envelope.
        if not outcome["created"]:
            # Emit only a bounded non-secret internal classification.
            self._audit("warning", "one_time_token_reissue_rejected", purpose=purpose, reason="malformed")
            # Preserve one public initiation error.
            self._invalid_request()
        # Audit replacement with opaque identifiers and a bounded count only.
        self._audit("info", "one_time_token_reissued", token_id=record["token_id"], purpose=purpose, audit_id=record["audit_id"], count=outcome["revoked"])
        # Return the replacement bearer exactly once.
        return receipt

    # Prepare one non-consumable replacement while preserving the exact active predecessor. (AUTH-018)
    def prepare_candidate(self, purpose: str, subject: str, predecessor_token_id: str, *, ttl_seconds: int | None = None, session_binding: str = "", max_attempts: int | None = None) -> dict:
        # Prepare bearer material through the same purpose, subject, lifetime, and attempt validation.
        record, receipt = self._prepare(purpose, subject, ttl_seconds=ttl_seconds, session_binding=session_binding, max_attempts=max_attempts)
        # Mark the durable row non-consumable until provider delivery succeeds.
        record["activation_state"] = "candidate"
        # Bind promotion to one opaque predecessor without retaining subject material.
        record["predecessor_token_id"] = str(predecessor_token_id or "").strip()
        # Track the candidate creation decision across the provider transaction.
        outcome = {"created": False}

        # Append only beside the exact active predecessor under one document lock.
        def mutate(raw_state: Any) -> dict:
            # Validate the token document before inspecting predecessor state.
            state = self._state(raw_state)
            # Resolve the exact active predecessor by opaque identifier.
            predecessor = next((row for row in state["tokens"] if row.get("token_id") == record["predecessor_token_id"]), None)
            # Require equal purpose and subject plus current activity.
            predecessor_matches = predecessor is not None and predecessor.get("purpose") == purpose and hmac.compare_digest(str(predecessor.get("subject_digest", "")), record["subject_digest"]) and self._active(predecessor, record["created_at"])
            # Reject absent, changed, or inactive predecessor state generically.
            if not predecessor_matches:
                # Preserve the complete token document unchanged.
                return state
            # Retire expired candidate rows so an abandoned delivery cannot block replacement forever.
            for existing in state["tokens"]:
                # Touch only unconsumed, unrevoked candidates for this exact purpose and subject.
                if existing.get("activation_state") == "candidate" and not existing.get("consumed_at") and not existing.get("revoked_at") and existing.get("purpose") == purpose and hmac.compare_digest(str(existing.get("subject_digest", "")), record["subject_digest"]):
                    # Revoke only candidates whose governed bearer lifetime has elapsed.
                    if self._parse(existing.get("expires_at")) < self._parse(record["created_at"]):
                        # Preserve the retained audit row while removing its blocking state.
                        existing["revoked_at"] = record["created_at"]
            # Reject another live candidate or impossible bearer/id collision.
            if any((row.get("activation_state") == "candidate" and not row.get("consumed_at") and not row.get("revoked_at") and self._parse(row.get("expires_at")) >= self._parse(record["created_at"]) and row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), record["subject_digest"])) or hmac.compare_digest(str(row.get("token_digest", "")), record["token_digest"]) or row.get("token_id") == record["token_id"] for row in state["tokens"]):
                # Preserve existing active and candidate state.
                return state
            # Append the non-consumable candidate without touching the predecessor.
            state["tokens"].append(record)
            # Publish success only after the candidate row is part of the commit.
            outcome["created"] = True
            # Return the complete token document.
            return state
        # Commit candidate preparation through JSON locking or MySQL row locking.
        update_json(self.store_path, mutate, default_tokens)
        # Reject every predecessor or collision failure through the generic request boundary.
        if not outcome["created"]:
            # Emit only fixed purpose and bounded failure class.
            self._audit("warning", "one_time_token_candidate_rejected", purpose=purpose, reason="predecessor_unavailable")
            # Preserve the existing generic initiation error.
            self._invalid_request()
        # Audit only opaque lifecycle identifiers.
        self._audit("info", "one_time_token_candidate_prepared", token_id=record["token_id"], purpose=purpose, audit_id=record["audit_id"])
        # Return the candidate bearer exactly once to the delivery boundary.
        return receipt

    # Atomically activate one delivered candidate and revoke only its bound predecessor. (AUTH-018)
    def promote_candidate(self, candidate_token_id: str, predecessor_token_id: str) -> bool:
        # Normalize opaque identifiers without accepting control characters or absence.
        candidate_id, predecessor_id = str(candidate_token_id or "").strip(), str(predecessor_token_id or "").strip()
        # Reject malformed lifecycle identifiers before durable-state inspection.
        if not candidate_id or not predecessor_id or any(character in candidate_id + predecessor_id for character in "\r\n"):
            # Preserve the generic request boundary.
            self._invalid_request()
        # Capture one shared promotion instant.
        now = self.clock()
        # Track whether the exact two-row transition committed.
        outcome = {"promoted": False, "purpose": None, "audit_id": None}

        # Promote and revoke inside one provider-owned document transaction.
        def mutate(raw_state: Any) -> dict:
            # Validate the complete token document.
            state = self._state(raw_state)
            # Resolve exact candidate and predecessor rows.
            candidate = next((row for row in state["tokens"] if row.get("token_id") == candidate_id), None)
            # Resolve the opaque predecessor independently.
            predecessor = next((row for row in state["tokens"] if row.get("token_id") == predecessor_id), None)
            # Accept an exact lost-response replay after the atomic promotion already committed.
            already_promoted = candidate is not None and predecessor is not None and candidate.get("activation_state") == "active" and candidate.get("promoted_from_token_id") == predecessor_id and not candidate.get("consumed_at") and not candidate.get("revoked_at") and predecessor.get("revoked_at") and candidate.get("purpose") == predecessor.get("purpose") and hmac.compare_digest(str(candidate.get("subject_digest", "")), str(predecessor.get("subject_digest", "")))
            # Publish the prior committed result without changing either row.
            if already_promoted:
                # Bind opaque audit metadata for the ordinary successful return.
                outcome.update({"promoted": True, "purpose": candidate.get("purpose"), "audit_id": candidate.get("audit_id"), "replay": True})
                # Return the complete document unchanged.
                return state
            # Require a fresh candidate bound to the exact active predecessor.
            valid = candidate is not None and predecessor is not None and candidate.get("activation_state") == "candidate" and candidate.get("predecessor_token_id") == predecessor_id and not candidate.get("consumed_at") and not candidate.get("revoked_at") and self._parse(candidate.get("expires_at")) >= self._parse(now) and self._active(predecessor, now)
            # Require purpose and subject equality without exposing either value.
            valid = valid and candidate.get("purpose") == predecessor.get("purpose") and hmac.compare_digest(str(candidate.get("subject_digest", "")), str(predecessor.get("subject_digest", "")))
            # Preserve state when any binding changed.
            if not valid:
                # Return the complete document without mutation.
                return state
            # Make the delivered candidate consumable.
            candidate["activation_state"] = "active"
            # Retain only the opaque predecessor id for exact promotion replay recovery.
            candidate["promoted_from_token_id"] = predecessor_id
            # Remove the transitional candidate-only pointer after successful binding proof.
            candidate.pop("predecessor_token_id", None)
            # Revoke only the exact predecessor at the same captured instant.
            predecessor["revoked_at"] = now
            # Publish opaque audit fields after both mutations are staged.
            outcome.update({"promoted": True, "purpose": candidate.get("purpose"), "audit_id": candidate.get("audit_id")})
            # Return the complete token document for one atomic commit.
            return state
        # Commit promotion through the provider abstraction.
        update_json(self.store_path, mutate, default_tokens)
        # Audit successful promotion with opaque identifiers only.
        if outcome["promoted"] and not outcome.get("replay"):
            # Record the terminal replacement transition.
            self._audit("info", "one_time_token_candidate_promoted", token_id=candidate_id, purpose=outcome["purpose"], audit_id=outcome["audit_id"])
        # Return only whether the exact promotion committed.
        return outcome["promoted"]

    # Revoke one undelivered candidate without changing its predecessor. (AUTH-018)
    def discard_candidate(self, candidate_token_id: str) -> bool:
        # Normalize the opaque candidate identifier.
        candidate_id = str(candidate_token_id or "").strip()
        # Reject malformed lifecycle identifiers before durable-state inspection.
        if not candidate_id or any(character in candidate_id for character in "\r\n"):
            # Preserve the generic request boundary.
            self._invalid_request()
        # Capture one discard instant.
        now = self.clock()
        # Track only the bounded transition result.
        outcome = {"discarded": False, "purpose": None, "audit_id": None}

        # Revoke only a still-pending candidate under the provider lock.
        def mutate(raw_state: Any) -> dict:
            # Validate the complete token document.
            state = self._state(raw_state)
            # Resolve the exact candidate row.
            candidate = next((row for row in state["tokens"] if row.get("token_id") == candidate_id), None)
            # Preserve absent, active, or already terminal rows.
            if candidate is None or candidate.get("activation_state") != "candidate" or candidate.get("revoked_at") or candidate.get("consumed_at"):
                # Return the complete document unchanged.
                return state
            # Revoke only the non-consumable candidate.
            candidate["revoked_at"] = now
            # Publish opaque audit fields after staging the transition.
            outcome.update({"discarded": True, "purpose": candidate.get("purpose"), "audit_id": candidate.get("audit_id")})
            # Return the complete document for one commit.
            return state
        # Commit through JSON locking or MySQL row locking.
        update_json(self.store_path, mutate, default_tokens)
        # Audit only a successful bounded discard.
        if outcome["discarded"]:
            # Record no predecessor, subject, or bearer material.
            self._audit("info", "one_time_token_candidate_discarded", token_id=candidate_id, purpose=outcome["purpose"], audit_id=outcome["audit_id"])
        # Return only whether one candidate changed.
        return outcome["discarded"]

    # Authorize one currently active bearer without consuming it. (AUTH-018)
    def authorize_active(self, purpose: str, token: str, subject: str) -> dict:
        # Reject malformed purpose, bearer, or subject through the generic token boundary.
        normalized_subject = self._normalize_subject(subject)
        # Require the same fixed purpose and nonempty inputs as consumption.
        if purpose not in PURPOSES or not str(token or "") or not normalized_subject:
            # Avoid scanning durable state for malformed requests.
            self._invalid_token()
        # Compute independent bearer and subject verifiers in process memory only.
        token_digest = self._digest("bearer", str(token))
        # Bind authorization to the normalized recipient identity.
        subject_digest = self._digest("subject", normalized_subject)
        # Capture one consistent activity instant.
        now = self.clock()
        # Retain only opaque success metadata across the provider transaction.
        outcome = {}

        # Inspect the active token under the same provider serialization used by consumption.
        def inspect(raw_state: Any) -> dict:
            # Validate the complete token document before scanning rows.
            state = self._state(raw_state)
            # Resolve one matching purpose and bearer verifier.
            for row in state["tokens"]:
                # Skip every other purpose without exposing partial matches.
                if row.get("purpose") != purpose:
                    # Continue through the bounded retained collection.
                    continue
                # Compare the bearer verifier in constant time.
                if not hmac.compare_digest(str(row.get("token_digest", "")), token_digest):
                    # Continue without mutating attempt state.
                    continue
                # Require current activity and exact subject binding.
                if self._active(row, now) and hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest):
                    # Publish only opaque lifecycle identifiers.
                    outcome.update({"token_id": row.get("token_id"), "purpose": purpose, "audit_id": row.get("audit_id")})
                # Stop after the unique bearer verifier regardless of its state.
                break
            # Return the unchanged complete document.
            return state
        # Serialize authorization against concurrent promotion, revoke, and consume mutations.
        update_json(self.store_path, inspect, default_tokens)
        # Reject absent, stale, candidate, cross-recipient, revoked, or consumed bearers uniformly.
        if not outcome.get("token_id"):
            # Emit no subject or bearer data in internal audit.
            self._audit("warning", "one_time_token_authorization_rejected", purpose=purpose, reason="unavailable")
            # Preserve the generic token rejection envelope.
            self._invalid_token()
        # Audit only opaque identifiers for the accepted ownership proof.
        self._audit("info", "one_time_token_authorized", token_id=outcome["token_id"], purpose=purpose, audit_id=outcome.get("audit_id"))
        # Return no bearer or subject material.
        return outcome

    # Consume one bearer exactly once with mandatory purpose and subject binding.
    def consume(self, purpose: str, token: str, *, subject: str | None = None, session_binding: str = "", subject_active: bool = True, idempotency_key: str = "", include_replay_state: bool = False) -> dict:
        # Reject unknown purpose, empty bearer, absent subject, or malformed activity state uniformly.
        if purpose not in PURPOSES or not str(token or "") or not self._normalize_subject(subject) or not isinstance(subject_active, bool) or not isinstance(include_replay_state, bool):
            # Preserve the generic public consumption envelope without scanning durable state.
            self._invalid_token()
        # Compute the presented bearer verifier once without retaining the raw token.
        token_digest = self._digest("bearer", str(token))
        # Compute the mandatory normalized subject verifier once.
        subject_digest = self._digest("subject", self._normalize_subject(subject))
        # Compute an optional session verifier for rows that require browser/session binding.
        session_digest = self._digest("session", session_binding) if session_binding else None
        # Normalize the optional caller replay key used by recoverable enrollment consumers.
        normalized_idempotency = str(idempotency_key or "").strip()
        # Reject malformed replay keys without scanning durable token state.
        if normalized_idempotency and (len(normalized_idempotency) < 16 or len(normalized_idempotency) > 200 or any(character in normalized_idempotency for character in "\r\n")):
            # Preserve the generic public consumption envelope for unsafe replay metadata.
            self._invalid_token()
        # Digest caller replay metadata independently so the raw key never reaches storage.
        idempotency_digest = self._digest("consume-idempotency", normalized_idempotency) if normalized_idempotency else None
        # Capture one consume instant for every state decision and timestamp.
        now = self.clock()
        # Hold only non-secret outcome fields across the atomic mutation.
        outcome = {"reason": "not_found"}

        # Find, validate, and mark one record inside a single serialized mutation.
        def mutate(raw_state: Any) -> dict:
            # Validate the complete durable document before inspecting rows.
            state = self._state(raw_state)
            # Scan the fixed-purpose collection for the constant-time bearer verifier.
            for row in state["tokens"]:
                # Prevent cross-purpose substitution before comparing the bearer verifier.
                if row.get("purpose") != purpose:
                    # Continue to the next row without exposing whether another purpose matched.
                    continue
                # Compare the presented verifier in constant time.
                if not hmac.compare_digest(str(row.get("token_digest", "")), token_digest):
                    # Continue to the next candidate without exposing partial matches.
                    continue
                # Record revoked state only for sanitized internal audit.
                if row.get("revoked_at"):
                    # Classify the matching terminal row without mutating it.
                    outcome["reason"] = "revoked"
                    # Stop after resolving the unique verifier.
                    break
                # Return an idempotent success only for the exact prior subject, session, and caller replay key.
                if row.get("consumed_at"):
                    # Require an explicit replay key that matches the first successful consumption.
                    replay_matches = bool(idempotency_digest) and hmac.compare_digest(str(row.get("consume_idempotency_digest", "")), idempotency_digest)
                    # Preserve subject binding on replay even though the bearer verifier matched.
                    replay_matches = replay_matches and hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest)
                    # Preserve any session binding captured by the original issuance.
                    replay_matches = replay_matches and (not row.get("session_digest") or (session_digest is not None and hmac.compare_digest(str(row.get("session_digest", "")), session_digest)))
                    # Publish the same opaque receipt only when every recovery binding matches.
                    if replay_matches:
                        # Return the original opaque identifiers without changing counters or timestamps.
                        outcome.update({"token_id": row.get("token_id"), "purpose": purpose, "audit_id": row.get("audit_id"), "replayed": True})
                    # Classify every other replay as consumed for sanitized internal audit.
                    else:
                        # Keep the one-time boundary for callers that omit or change the replay key.
                        outcome["reason"] = "consumed"
                    # Stop after resolving the unique verifier.
                    break
                # Fail closed on malformed or elapsed expiry.
                if not self._active(row, now):
                    # Classify every non-terminal inactive row as expired internally.
                    outcome["reason"] = "expired"
                    # Stop after resolving the unique verifier.
                    break
                # Read the stored bounded attempt counters defensively.
                attempts = row.get("attempts")
                # Read the stored immutable attempt ceiling defensively.
                attempt_limit = row.get("max_attempts")
                # Fail closed when counters are malformed or exhausted.
                if not isinstance(attempts, int) or not isinstance(attempt_limit, int) or attempts < 0 or attempt_limit <= 0:
                    # Classify malformed persisted security state internally.
                    outcome["reason"] = "malformed"
                    # Stop without changing the malformed row.
                    break
                # Reject a record whose bounded attempt budget is exhausted.
                if attempts >= attempt_limit:
                    # Classify the exhausted budget internally.
                    outcome["reason"] = "too_many_attempts"
                    # Stop after resolving the unique verifier.
                    break
                # Require the exact subject binding on every consume call.
                if not hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest):
                    # Charge the mismatch against the bounded attempt budget.
                    row["attempts"] = attempts + 1
                    # Classify the binding rejection internally.
                    outcome["reason"] = "subject_mismatch"
                    # Stop after resolving the unique verifier.
                    break
                # Require the exact session binding whenever one was captured at issue time.
                if row.get("session_digest") and (session_digest is None or not hmac.compare_digest(str(row.get("session_digest", "")), session_digest)):
                    # Charge the mismatch against the bounded attempt budget.
                    row["attempts"] = attempts + 1
                    # Classify the session rejection internally.
                    outcome["reason"] = "session_mismatch"
                    # Stop after resolving the unique verifier.
                    break
                # Require the approved future consumer to attest that its bound subject remains active.
                if subject_active is not True:
                    # Charge inactive-subject rejection against the bounded attempt budget.
                    row["attempts"] = attempts + 1
                    # Classify the inactive-subject rejection internally.
                    outcome["reason"] = "inactive_subject"
                    # Stop after resolving the unique verifier.
                    break
                # Stamp exactly-once consumption while the provider mutation remains locked.
                row["consumed_at"] = now
                # Bind future recovery only to the explicit caller idempotency key, when supplied.
                row["consume_idempotency_digest"] = idempotency_digest
                # Count the successful redemption as a bounded attempt.
                row["attempts"] = attempts + 1
                # Publish only opaque success fields to the caller-owned outcome.
                outcome.update({"token_id": row.get("token_id"), "purpose": purpose, "audit_id": row.get("audit_id"), "replayed": False})
                # Stop after the unique verifier is consumed.
                break
            # Return the complete possibly mutated document for atomic persistence.
            return state

        # Serialize the complete consume decision through JSON or MySQL provider semantics.
        update_json(self.store_path, mutate, default_tokens)
        # Reject every unsuccessful result through the same public error.
        if "token_id" not in outcome:
            # Emit only purpose and the bounded internal class, never bearer or binding material.
            self._audit("warning", "one_time_token_rejected", purpose=purpose, reason=outcome["reason"])
            # Raise the uniform public consumption envelope.
            self._invalid_token()
        # Audit success using opaque identifiers only.
        self._audit("info", "one_time_token_consumed", token_id=outcome["token_id"], purpose=purpose, audit_id=outcome.get("audit_id"))
        # Return no bearer, subject, session, or digest material.
        receipt = {"token_id": outcome["token_id"], "purpose": purpose, "audit_id": outcome.get("audit_id")}
        # Expose replay classification only to explicitly approved recoverable state-machine consumers.
        if include_replay_state:
            # Add one non-secret boolean without changing the default public receipt contract.
            receipt["replayed"] = bool(outcome.get("replayed"))
        # Return the opaque receipt with the optional caller-approved replay classification.
        return receipt

    # Revoke one active token by opaque identifier.
    def revoke(self, token_id: str) -> bool:
        # Reject an absent identifier without scanning durable state.
        if not str(token_id or "").strip():
            # Preserve a generic initiation error for malformed revocation requests.
            self._invalid_request()
        # Capture one revocation instant.
        now = self.clock()
        # Track whether one active record changed.
        outcome = {"revoked": False, "purpose": None, "audit_id": None}

        # Apply revocation inside the provider-owned atomic mutation.
        def mutate(raw_state: Any) -> dict:
            # Validate the durable document before inspecting rows.
            state = self._state(raw_state)
            # Walk rows until the opaque identifier is found.
            for row in state["tokens"]:
                # Revoke only the matching currently active record.
                if row.get("token_id") == token_id and self._active(row, now):
                    # Stamp revocation at the captured instant.
                    row["revoked_at"] = now
                    # Publish the non-secret outcome flag.
                    outcome["revoked"] = True
                    # Retain the fixed purpose for sanitized audit.
                    outcome["purpose"] = row.get("purpose")
                    # Retain the opaque audit identifier for sanitized audit.
                    outcome["audit_id"] = row.get("audit_id")
                    # Stop after the unique identifier changes.
                    break
            # Return the complete possibly mutated document.
            return state

        # Publish revocation through the atomic provider boundary.
        update_json(self.store_path, mutate, default_tokens)
        # Audit successful revocation with opaque fields only.
        if outcome["revoked"]:
            # Emit the bounded successful lifecycle event.
            self._audit("info", "one_time_token_revoked", token_id=token_id, purpose=outcome["purpose"], audit_id=outcome["audit_id"])
        # Return only whether an active record changed.
        return outcome["revoked"]

    # Revoke every active token for one bound purpose and subject.
    def revoke_for_subject(self, purpose: str, subject: str) -> int:
        # Validate purpose through the fixed policy without changing its lifetime.
        self._purpose_ttl(purpose, None)
        # Normalize the mandatory subject binding.
        normalized_subject = self._normalize_subject(subject)
        # Reject an empty binding through the generic initiation envelope.
        if not normalized_subject:
            # Preserve one public request error.
            self._invalid_request()
        # Compute the domain-separated subject verifier once.
        subject_digest = self._digest("subject", normalized_subject)
        # Capture one bulk-revocation instant.
        now = self.clock()
        # Count changed records without retaining their identifiers.
        outcome = {"count": 0}

        # Apply bulk revocation inside one atomic document mutation.
        def mutate(raw_state: Any) -> dict:
            # Validate the current durable document.
            state = self._state(raw_state)
            # Inspect every row under the provider lock.
            for row in state["tokens"]:
                # Select active rows with the exact purpose and subject verifier.
                if row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest) and self._active(row, now):
                    # Stamp the shared captured revocation instant.
                    row["revoked_at"] = now
                    # Increment the bounded audit count.
                    outcome["count"] += 1
            # Return the complete mutated document.
            return state

        # Commit all matching revocations together.
        update_json(self.store_path, mutate, default_tokens)
        # Audit only the fixed purpose and bounded count.
        self._audit("info", "one_time_tokens_subject_revoked", purpose=purpose, count=outcome["count"])
        # Return the count without subject or verifier material.
        return outcome["count"]

    # Count active tokens for one fixed purpose and subject without mutation.
    def active_count(self, purpose: str, subject: str) -> int:
        # Validate the fixed purpose through the same initiation policy.
        self._purpose_ttl(purpose, None)
        # Normalize the mandatory subject binding.
        normalized_subject = self._normalize_subject(subject)
        # Reject an empty binding through the generic initiation envelope.
        if not normalized_subject:
            # Preserve one public request error.
            self._invalid_request()
        # Compute the subject verifier without retaining the raw subject.
        subject_digest = self._digest("subject", normalized_subject)
        # Capture one comparison instant.
        now = self.clock()
        # Validate the read-only durable document.
        state = self._state(read_json(self.store_path, default_tokens))
        # Count only exact-purpose, exact-subject, currently active rows.
        return sum(1 for row in state["tokens"] if row.get("purpose") == purpose and hmac.compare_digest(str(row.get("subject_digest", "")), subject_digest) and self._active(row, now))

    # Remove only terminal rows whose fixed retention period has elapsed.
    def cleanup(self) -> int:
        # Capture one cleanup instant for every row decision.
        now = self.clock()
        # Count pruned rows for sanitized health reporting.
        outcome = {"count": 0}

        # Apply bounded cleanup inside one provider-owned atomic mutation.
        def mutate(raw_state: Any) -> dict:
            # Validate the current durable document before removing anything.
            state = self._state(raw_state)
            # Retain every active, recent-terminal, or malformed row.
            kept = [row for row in state["tokens"] if not self._retention_elapsed(row, now)]
            # Record the exact bounded number of removed rows.
            outcome["count"] = len(state["tokens"]) - len(kept)
            # Replace only the validated row collection while preserving schema metadata.
            state["tokens"] = kept
            # Return the complete pruned document.
            return state

        # Commit cleanup through the same JSON/MySQL atomic boundary.
        update_json(self.store_path, mutate, default_tokens)
        # Audit only the bounded cleanup count.
        self._audit("info", "one_time_tokens_cleaned", count=outcome["count"])
        # Return the number of rows removed.
        return outcome["count"]


# Lazily construct the production service so importing the inert module never mutates state.
_DEFAULT_SERVICE: TokenService | None = None


# Return the single process-local production service facade.
def _service() -> TokenService:
    # Bind the lazily initialized module service for assignment.
    global _DEFAULT_SERVICE
    # Construct the service only when an approved future consumer calls it.
    if _DEFAULT_SERVICE is None:
        # Use the configured external digest key, shared clock, and operating-system randomness.
        _DEFAULT_SERVICE = TokenService()
    # Return the initialized inert service.
    return _DEFAULT_SERVICE


# Issue one purpose-bound token through the production service facade.
def issue(purpose: str, subject: str, *, ttl_seconds: int | None = None, session_binding: str = "", max_attempts: int | None = None) -> dict:
    # Delegate strict validation and atomic persistence to the production service.
    return _service().issue(purpose, subject, ttl_seconds=ttl_seconds, session_binding=session_binding, max_attempts=max_attempts)


# Atomically supersede active tokens and issue one replacement.
def reissue(purpose: str, subject: str, *, ttl_seconds: int | None = None, session_binding: str = "", max_attempts: int | None = None) -> dict:
    # Delegate reissue policy to the production service.
    return _service().reissue(purpose, subject, ttl_seconds=ttl_seconds, session_binding=session_binding, max_attempts=max_attempts)


# Prepare one non-consumable replacement while retaining its active predecessor.
def prepare_candidate(purpose: str, subject: str, predecessor_token_id: str, *, ttl_seconds: int | None = None, session_binding: str = "", max_attempts: int | None = None) -> dict:
    # Delegate candidate preparation to the provider-backed service.
    return _service().prepare_candidate(purpose, subject, predecessor_token_id, ttl_seconds=ttl_seconds, session_binding=session_binding, max_attempts=max_attempts)


# Promote one delivered candidate and revoke its predecessor atomically.
def promote_candidate(candidate_token_id: str, predecessor_token_id: str) -> bool:
    # Delegate the exact two-row lifecycle transition.
    return _service().promote_candidate(candidate_token_id, predecessor_token_id)


# Revoke one undelivered candidate without changing its predecessor.
def discard_candidate(candidate_token_id: str) -> bool:
    # Delegate candidate cleanup to the provider-backed service.
    return _service().discard_candidate(candidate_token_id)


# Authorize one active bearer without consuming its later verification use.
def authorize_active(purpose: str, token: str, subject: str) -> dict:
    # Delegate purpose, subject, expiry, and constant-time bearer validation.
    return _service().authorize_active(purpose, token, subject)


# Consume one bearer exactly once with mandatory subject binding.
def consume(purpose: str, token: str, *, subject: str | None = None, session_binding: str = "", subject_active: bool = True, idempotency_key: str = "", include_replay_state: bool = False) -> dict:
    # Delegate the atomic redemption decision to the production service.
    return _service().consume(purpose, token, subject=subject, session_binding=session_binding, subject_active=subject_active, idempotency_key=idempotency_key, include_replay_state=include_replay_state)


# Revoke one active token by opaque identifier.
def revoke(token_id: str) -> bool:
    # Delegate the atomic revocation decision to the production service.
    return _service().revoke(token_id)


# Revoke all active tokens for one purpose and subject.
def revoke_for_subject(purpose: str, subject: str) -> int:
    # Delegate the bulk revocation to the production service.
    return _service().revoke_for_subject(purpose, subject)


# Count active tokens for one purpose and subject.
def active_count(purpose: str, subject: str) -> int:
    # Delegate the read-only policy query to the production service.
    return _service().active_count(purpose, subject)


# Prune retained terminal rows whose fixed retention window elapsed.
def cleanup() -> int:
    # Delegate bounded cleanup to the production service.
    return _service().cleanup()
