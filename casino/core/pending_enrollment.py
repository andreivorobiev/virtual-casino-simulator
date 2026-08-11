# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Recoverable verified-email signup without pre-verification identity state. (AUTH-018)"""

# Import hashes for privacy-safe recipient and idempotency lookup keys.
import hashlib
# Import constant-time comparisons for durable replay bindings.
import hmac
# Import canonical JSON encoding for one privacy-safe request fingerprint.
import json
# Import finite-number validation for the configured initial wallet credit.
import math
# Import timezone-aware parsing for durable fixed-window abuse controls.
from datetime import datetime, timedelta, timezone
# Import portable paths for provider-backed isolated tests.
from pathlib import Path
# Import dependency types for deterministic service fixtures.
from typing import Any, Callable

# Import disabled-by-default signup policy and bounded release settings.
from casino import config
# Import the canonical identity, wallet, ledger, mail, and token boundaries.
from casino.core import auth, ledger, logger, mail, one_time_tokens, players
# Import the shared application clock and opaque identifier factory.
from casino.core.clock import utc_now
# Import opaque identifiers without deriving them from mailbox content.
from casino.core.ids import new_id
# Import provider-aware atomic document reads and mutations.
from casino.core.state_store import read_json, update_json
# Import stable bounded errors used by the public v2 facade.
from casino.errors import ConflictError, ForbiddenError, RateLimitError, ValidationError

# Store pending signup state beside the governed authentication documents.
PENDING_ENROLLMENTS_PATH = config.DATA_DIR / "auth" / "pending_enrollments.json"
# Bind every bearer to the existing reviewed verification purpose.
PURPOSE = "email_verification"
# Restrict signup and mail content to translated locales.
LOCALES = frozenset({"en-US", "ru-RU"})
# Publish one non-enumerating failure category for every verify rejection.
GENERIC_VERIFICATION_DETAILS = {"reason": "verification_unavailable"}
# Publish one non-enumerating acknowledgement for initiation and resend.
PENDING_RECEIPT = {"status": "verification_pending"}
# Publish one non-enumerating failure category for cancellation ownership rejection.
GENERIC_CANCELLATION_DETAILS = {"reason": "cancellation_unavailable"}


# Build the canonical empty pending-enrollment document.
def default_pending_enrollments() -> dict:
    # Return a fresh schema-stamped collection for JSON and MySQL providers.
    return {"schema_version": config.SCHEMA_VERSION, "enrollments": [], "rate_events": []}


# Own one recoverable email-verification and identity-activation saga.
class PendingEnrollmentService:
    # Compose the service from injectable provider-neutral foundations.
    def __init__(self, *, store_path: Path = PENDING_ENROLLMENTS_PATH, enabled: bool = False, digest_key: str = "", token_service=None, mail_service=None, clock: Callable[[], str] = utc_now, id_factory: Callable[[str], str] = new_id, audit_sink: Callable[..., None] = logger.info, phase_hook: Callable[[str], None] | None = None) -> None:
        # Persist the provider-backed pending-enrollment document path.
        self.store_path = Path(store_path)
        # Keep public signup independently disabled by default.
        self.enabled = bool(enabled)
        # Retain keyed-digest material in process memory only.
        self.digest_key = str(digest_key or "")
        # Reuse the reviewed token and transactional-mail platforms.
        self.token_service = token_service or one_time_tokens
        # Resolve the configured mail boundary lazily for local test injection.
        self.mail_service = mail_service or mail.configured_service()
        # Retain deterministic clocks and identifiers for recovery tests.
        self.clock = clock
        # Retain the opaque identifier factory.
        self.id_factory = id_factory
        # Retain the privacy-safe audit sink.
        self.audit_sink = audit_sink
        # Retain an optional test-only phase hook without changing production execution.
        self.phase_hook = phase_hook
        # Reject unsafe funding configuration before any mutation.
        if not math.isfinite(config.ACCOUNT_STARTING_BALANCE) or config.ACCOUNT_STARTING_BALANCE <= 0 or config.ACCOUNT_STARTING_BALANCE > 1_000_000:
            # Surface a value-free startup diagnostic rather than an unsafe partial signup.
            raise RuntimeError("Verified email enrollment policy is outside supported bounds")

    # Validate the complete durable document without destructive repair.
    @staticmethod
    def _state(value: Any) -> dict:
        # Require the exact mapping and row collection used by both storage providers.
        if not isinstance(value, dict) or not isinstance(value.get("enrollments"), list) or not isinstance(value.get("rate_events"), list) or any(not isinstance(row, dict) for row in value.get("enrollments", [])) or any(not isinstance(event, dict) for event in value.get("rate_events", [])):
            # Preserve malformed state for operator recovery.
            raise RuntimeError("Pending enrollment storage requires operator recovery")
        # Return the validated mutable document.
        return value

    # Validate one transient mailbox without echoing it in failures.
    @staticmethod
    def _email(value: str) -> str:
        # Normalize through the canonical account identity rule.
        normalized = auth.normalize_email(str(value or ""))
        # Reject empty, control-character, overlong, or structurally implausible mailboxes.
        if not normalized or len(normalized) > 254 or normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@") or any(character in normalized for character in "\r\n"):
            # Keep the public validation response free of supplied mailbox data.
            raise ValidationError("Signup request is invalid")
        # Return the validated transient mailbox.
        return normalized

    # Validate one caller replay key without persisting it.
    @staticmethod
    def _idempotency(value: str) -> str:
        # Normalize the caller-owned replay key once.
        normalized = str(value or "").strip()
        # Require bounded transport-safe entropy.
        if len(normalized) < 16 or len(normalized) > 200 or any(character in normalized for character in "\r\n"):
            # Reject malformed replay metadata without echoing it.
            raise ValidationError("Signup idempotency key is invalid")
        # Return the transient key for domain-separated digesting.
        return normalized

    # Compute one domain-separated keyed digest.
    def _digest(self, domain: str, value: str) -> str:
        # Require non-default 256-bit digest material before persisting lookup metadata.
        if len(self.digest_key.encode("utf-8")) < 32 or self.digest_key == config.LOCAL_MAIL_DIGEST_KEY:
            # Fail closed before any predictable privacy identifier is written.
            raise ValidationError("Signup verification is unavailable", dict(GENERIC_VERIFICATION_DETAILS))
        # Bind equal values to independent recipient and action domains.
        payload = f"{domain}\0{value}".encode("utf-8")
        # Return the non-reversible HMAC verifier.
        return hmac.new(self.digest_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Find one row by its server-owned identifier.
    @staticmethod
    def _find(state: dict, enrollment_id: str) -> dict | None:
        # Return the exact matching row without exposing collection order.
        return next((row for row in state["enrollments"] if row.get("enrollment_id") == enrollment_id), None)

    # Parse one repository timestamp for durable rate-window comparisons.
    @staticmethod
    def _parse_time(value: str) -> datetime:
        # Normalize the repository's UTC suffix for the standard ISO parser.
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        # Require an explicit offset so local wall-clock values cannot weaken the fixed window.
        if parsed.tzinfo is None:
            # Reject malformed rate evidence without rewriting it.
            raise RuntimeError("Pending enrollment rate evidence requires operator recovery")
        # Compare every accepted timestamp in UTC.
        return parsed.astimezone(timezone.utc)

    # Consume one durable action allowance keyed only by the trusted effective client digest.
    def _enforce_rate(self, state: dict, action: str, client_reference: str, now: str) -> None:
        # Bind the three public mutation classes to independent fixed ceilings.
        limits = {"initiate": config.EMAIL_ENROLLMENT_INITIATE_RATE_LIMIT, "resend": config.EMAIL_ENROLLMENT_RESEND_RATE_LIMIT, "verify": config.EMAIL_ENROLLMENT_VERIFY_RATE_LIMIT, "cancel": config.EMAIL_ENROLLMENT_CANCEL_RATE_LIMIT}
        # Reject unknown actions or unsafe deployment bounds before appending evidence.
        if action not in limits or limits[action] <= 0 or limits[action] > 10_000 or config.EMAIL_ENROLLMENT_RATE_WINDOW_SECONDS <= 0 or config.EMAIL_ENROLLMENT_RATE_WINDOW_SECONDS > 86_400 or config.EMAIL_ENROLLMENT_RATE_EVENT_CAP <= 0 or config.EMAIL_ENROLLMENT_RATE_EVENT_CAP > 100_000:
            # Fail closed rather than silently disabling enrollment abuse controls.
            raise RuntimeError("Verified email enrollment rate policy is outside supported bounds")
        # Normalize the trusted request-context identity without retaining it.
        client = str(client_reference or "service").strip()
        # Reject control characters or unbounded proxy metadata.
        if not client or len(client) > 256 or any(character in client for character in "\r\n"):
            # Preserve one fixed public rate classification.
            raise RateLimitError("Signup request rate limit is active")
        # Compute one action-specific non-reversible client verifier.
        client_digest = self._digest(f"rate-client:{action}", client)
        # Compute the inclusive start of the active fixed window.
        cutoff = self._parse_time(now) - timedelta(seconds=config.EMAIL_ENROLLMENT_RATE_WINDOW_SECONDS)
        # Retain only valid active evidence while failing closed on malformed timestamps.
        retained = [event for event in state["rate_events"] if self._parse_time(event.get("at")) >= cutoff]
        # Publish the pruned bounded collection before the limit decision.
        state["rate_events"] = retained
        # Reject the caller when its independent action allowance is exhausted.
        if sum(1 for event in retained if event.get("action") == action and hmac.compare_digest(str(event.get("client_digest", "")), client_digest)) >= limits[action]:
            # Return no recipient, token, address, count, or time detail.
            raise RateLimitError("Signup request rate limit is active")
        # Fail closed when distinct clients fill the complete active evidence capacity.
        if len(retained) >= config.EMAIL_ENROLLMENT_RATE_EVENT_CAP:
            # Preserve existing evidence rather than evicting an active abuse record.
            raise RateLimitError("Signup request rate limit is active")
        # Record only fixed action, keyed client verifier, and server time.
        retained.append({"action": action, "client_digest": client_digest, "at": now})

    # Remove terminal credential and recipient material while retaining replay digests and opaque audit ids.
    @staticmethod
    def _scrub_terminal_credentials(row: dict) -> None:
        # Remove every raw field that is unnecessary after completion or cancellation.
        for field in ("email", "password_hash", "display_name", "locale", "terms_version"):
            # Delete rather than null the terminal value so residue checks stay unambiguous.
            row.pop(field, None)

    # Prune only scrubbed terminal metadata after the bounded replay-retention window.
    def _prune_terminal(self, state: dict, now: str) -> None:
        # Require a positive bounded policy so configuration cannot disable cleanup silently.
        if config.EMAIL_ENROLLMENT_TERMINAL_RETENTION_SECONDS <= 0 or config.EMAIL_ENROLLMENT_TERMINAL_RETENTION_SECONDS > 31_536_000:
            # Preserve every row for operator recovery under unsafe policy.
            raise RuntimeError("Verified email enrollment retention policy is outside supported bounds")
        # Capture the absolute terminal retention cutoff once.
        cutoff = self._parse_time(now) - timedelta(seconds=config.EMAIL_ENROLLMENT_TERMINAL_RETENTION_SECONDS)
        # Preserve active, in-flight, malformed, and recent terminal rows.
        retained = []
        # Inspect every row without changing relative order.
        for row in state["enrollments"]:
            # Preserve all nonterminal lifecycle state regardless of age.
            if row.get("status") not in {"complete", "cancelled"}:
                # Append the unchanged active or recoverable row.
                retained.append(row)
                # Continue to the next lifecycle row.
                continue
            # Require terminal rows to be credential-scrubbed before cleanup classification.
            if {"email", "password_hash", "display_name", "locale", "terms_version"} & set(row):
                # Fail closed rather than deleting unexpected personal or credential material.
                raise RuntimeError("Pending enrollment terminal cleanup requires operator recovery")
            # Retain terminal replay metadata until its exact bounded age has elapsed.
            if self._parse_time(row.get("updated_at")) >= cutoff:
                # Preserve the recent terminal row unchanged.
                retained.append(row)
        # Publish the provider-atomic pruned collection.
        state["enrollments"] = retained

    # Expose one fixed phase label only to an injected provider-free crash harness.
    def _checkpoint(self, phase: str) -> None:
        # Call no hook during ordinary production composition.
        if self.phase_hook is not None:
            # Invoke the injected test boundary without passing recipient, bearer, or ids.
            self.phase_hook(phase)

    # Commit either a delivered candidate or the exact durable predecessor metadata.
    def _finish_delivery(self, enrollment_id: str, generation: int, candidate_token_id: str | None, accepted: bool) -> None:
        # Apply the exact replacement subrecord under the provider document lock.
        def finish(raw_state: Any) -> dict:
            # Validate durable pending state before finalization.
            state = self._state(raw_state)
            # Resolve the exact delivery owner.
            row = self._find(state, enrollment_id)
            # Resolve the bounded durable replacement packet.
            replacement = (row or {}).get("replacement")
            # Require the expected row and candidate identity before changing lifecycle state.
            if row is None or row.get("status") not in {"issuing", "delivery_pending"} or int(row.get("delivery_generation") or 0) != int(generation) or not isinstance(replacement, dict) or int(replacement.get("generation") or 0) != int(generation) or replacement.get("candidate_token_id") != candidate_token_id:
                # Preserve every concurrent or malformed generation.
                raise ConflictError("Signup delivery generation changed")
            # Publish the delivered and promoted candidate as current.
            if accepted:
                # Bind only opaque provider/token metadata from the durable replacement packet.
                row.update({"token_id": candidate_token_id, "expires_at": replacement.get("candidate_expires_at"), "mail_delivery_id": replacement.get("candidate_mail_delivery_id"), "delivery_status": "sent", "status": "pending", "updated_at": self.clock()})
            # Restore the exact predecessor after failed replacement.
            elif replacement.get("predecessor_token_id"):
                # Reinstate all prior public delivery metadata byte-for-value.
                row.update({"status": replacement.get("predecessor_status"), "token_id": replacement.get("predecessor_token_id"), "expires_at": replacement.get("predecessor_expires_at"), "mail_delivery_id": replacement.get("predecessor_mail_delivery_id"), "delivery_status": replacement.get("predecessor_delivery_status"), "updated_at": self.clock()})
            # Keep failed initial delivery recoverable without a token binding.
            else:
                # Publish one fixed failure state and clear candidate-only metadata.
                row.update({"status": "delivery_failed", "token_id": None, "expires_at": None, "mail_delivery_id": None, "delivery_status": "failed", "updated_at": self.clock()})
            # Remove only the completed bounded replacement packet.
            row.pop("replacement", None)
            # Return the complete pending document.
            return state
        # Persist one terminal delivery transition.
        update_json(self.store_path, finish, default_pending_enrollments)

    # Reconcile one crashed delivery phase before recipient lifecycle decisions.
    def _reconcile_delivery(self, recipient_digest: str) -> None:
        # Read the current provider-backed pending document without mutation.
        state = self._state(read_json(self.store_path, default_pending_enrollments))
        # Resolve only one in-flight row for the keyed recipient.
        row = next((candidate for candidate in state["enrollments"] if candidate.get("recipient_digest") == recipient_digest and candidate.get("status") in {"issuing", "delivery_pending"}), None)
        # Return immediately when no crash-recoverable delivery exists.
        if row is None:
            # Leave ordinary pending and terminal rows untouched.
            return
        # Require one complete bounded replacement packet.
        replacement = row.get("replacement")
        # Fail closed on malformed in-flight state.
        if not isinstance(replacement, dict) or int(replacement.get("generation") or 0) != int(row.get("delivery_generation") or 0) or replacement.get("phase") not in {"preparing", "candidate_prepared", "delivered", "promoted"}:
            # Preserve the row for operator recovery.
            raise RuntimeError("Pending enrollment delivery requires operator recovery")
        # Resolve only opaque candidate and predecessor identifiers.
        candidate_id = replacement.get("candidate_token_id")
        # Complete any provider-confirmed delivery, including a promotion lost response.
        if replacement.get("phase") in {"delivered", "promoted"} and candidate_id:
            # Promote a replacement idempotently or accept an already-active first delivery.
            promoted = self.token_service.promote_candidate(candidate_id, replacement.get("predecessor_token_id")) if replacement.get("predecessor_token_id") else True
            # Finalize the delivered generation only when promotion is proven.
            if promoted:
                # Commit the candidate as the current pending bearer.
                self._finish_delivery(row["enrollment_id"], int(row.get("delivery_generation") or 0), candidate_id, True)
                # Return after complete recovery.
                return
            # Discard an unpromotable replacement without touching its predecessor.
            self.token_service.discard_candidate(candidate_id)
            # Restore durable predecessor metadata.
            self._finish_delivery(row["enrollment_id"], int(row.get("delivery_generation") or 0), candidate_id, False)
            # Return after safe failure recovery.
            return
        # Validate the configured ambiguity window before stale-phase cleanup.
        if config.EMAIL_ENROLLMENT_DELIVERY_RECOVERY_SECONDS <= 0 or config.EMAIL_ENROLLMENT_DELIVERY_RECOVERY_SECONDS > 86_400:
            # Fail closed rather than guessing whether provider delivery occurred.
            raise RuntimeError("Verified email enrollment delivery recovery policy is outside supported bounds")
        # Leave a fresh pre-provider phase owned by its current worker.
        if self._parse_time(row.get("updated_at")) + timedelta(seconds=config.EMAIL_ENROLLMENT_DELIVERY_RECOVERY_SECONDS) > self._parse_time(self.clock()):
            # Avoid racing an in-progress provider submission.
            return
        # Revoke only an abandoned candidate after the complete ambiguity window.
        if candidate_id:
            # Discard a replacement candidate while preserving its predecessor.
            if replacement.get("predecessor_token_id"):
                # Remove only the non-consumable candidate.
                self.token_service.discard_candidate(candidate_id)
            else:
                # Revoke an abandoned first-delivery token.
                self.token_service.revoke(candidate_id)
        # Restore predecessor or first-delivery failure state from durable metadata.
        self._finish_delivery(row["enrollment_id"], int(row.get("delivery_generation") or 0), candidate_id, False)

    # Require the explicit signup and transactional-mail release boundaries.
    def _require_ready(self) -> None:
        # Preserve the endpoint while denying every mutation when signup is disabled.
        if not self.enabled:
            # Match the established disabled full-account signup boundary.
            raise ForbiddenError("Full account signup is disabled")
        # Inspect only the mail service's secret-free readiness result.
        readiness = self.mail_service.readiness()
        # Require the provider boundary to be ready before creating pending credential state.
        if readiness.get("status") != "ready":
            # Fail before token, pending credential, account, player, balance, or session state.
            raise ForbiddenError("Full account signup is unavailable")

    # Issue one current bearer and submit its fixed verification message.
    def _deliver(self, enrollment_id: str, reason: str) -> dict:
        # Capture the exact row and generation selected under the state lock.
        selected = {}

        # Begin one recoverable delivery generation.
        def begin(raw_state: Any) -> dict:
            # Validate the complete document before lifecycle mutation.
            state = self._state(raw_state)
            # Resolve the exact pending enrollment.
            row = self._find(state, enrollment_id)
            # Permit delivery only before verification owns the row.
            if row is None or row.get("status") not in {"reserved", "pending", "delivery_failed"}:
                # Preserve the existing lifecycle unchanged.
                raise ConflictError("Signup verification cannot be delivered")
            # Retain the prior generation only in memory so a failed replacement cannot invalidate it.
            selected.update({"previous_status": row.get("status"), "previous_token_id": row.get("token_id"), "previous_expires_at": row.get("expires_at"), "previous_mail_delivery_id": row.get("mail_delivery_id"), "previous_delivery_status": row.get("delivery_status")})
            # Advance the generation before issuing transient bearer material.
            row["delivery_generation"] = int(row.get("delivery_generation") or 0) + 1
            # Mark the bounded recoverable internal state.
            row["status"] = "issuing"
            # Clear only prior generation delivery metadata.
            row["delivery_status"] = None
            # Record one fixed lifecycle cause without caller-authored text.
            row["last_delivery_reason"] = reason
            # Persist every predecessor value required after a worker crash.
            row["replacement"] = {"generation": row["delivery_generation"], "phase": "preparing", "predecessor_status": selected["previous_status"], "predecessor_token_id": selected["previous_token_id"], "predecessor_expires_at": selected["previous_expires_at"], "predecessor_mail_delivery_id": selected["previous_mail_delivery_id"], "predecessor_delivery_status": selected["previous_delivery_status"], "candidate_token_id": None, "candidate_expires_at": None, "candidate_mail_delivery_id": None, "candidate_delivery_status": None, "started_at": self.clock()}
            # Refresh the operator-visible lifecycle time.
            row["updated_at"] = self.clock()
            # Publish a detached internal copy for token and mail calls.
            selected.update(dict(row))
            # Return the complete document for atomic commit.
            return state
        # Persist the generation claim before creating a raw bearer.
        update_json(self.store_path, begin, default_pending_enrollments)
        # Expose the exact post-prepare crash boundary to provider-free tests.
        self._checkpoint("delivery_prepared")
        # Prepare a non-consumable replacement when a predecessor must remain valid through delivery.
        issued = self.token_service.prepare_candidate(PURPOSE, selected["email"], selected["previous_token_id"]) if selected.get("previous_token_id") else self.token_service.issue(PURPOSE, selected["email"])

        # Bind the opaque token id and expiry to this exact generation.
        def token_ready(raw_state: Any) -> dict:
            # Validate current state before publishing token metadata.
            state = self._state(raw_state)
            # Resolve the generation owner.
            row = self._find(state, enrollment_id)
            # Reject any lifecycle or generation drift.
            if row is None or row.get("status") != "issuing" or int(row.get("delivery_generation") or 0) != int(selected["delivery_generation"]):
                # Keep the newer state authoritative.
                raise ConflictError("Signup delivery generation changed")
            # Require the durable replacement packet created by the same generation.
            replacement = row.get("replacement")
            # Reject malformed or already advanced delivery state.
            if not isinstance(replacement, dict) or int(replacement.get("generation") or 0) != int(selected["delivery_generation"]) or replacement.get("phase") != "preparing":
                # Preserve the row for exact recovery.
                raise ConflictError("Signup delivery generation changed")
            # Persist no bearer, only candidate opaque identity and expiry.
            replacement.update({"phase": "candidate_prepared", "candidate_token_id": issued["token_id"], "candidate_expires_at": issued["expires_at"]})
            # Advance the recoverable lifecycle without replacing the current predecessor fields.
            row.update({"status": "delivery_pending", "updated_at": self.clock()})
            # Return the complete document for atomic persistence.
            return state
        # Publish or revoke the new token as one fail-closed boundary.
        try:
            # Commit the opaque token identity before provider submission.
            update_json(self.store_path, token_ready, default_pending_enrollments)
            # Expose the exact post-token-ready crash boundary to provider-free tests.
            self._checkpoint("candidate_prepared")
        # Revoke an orphan generation if lifecycle drift rejects publication.
        except Exception:
            # Discard a non-consumable replacement or revoke a failed first-delivery token.
            if selected.get("previous_token_id"):
                # Preserve the active predecessor while removing only its candidate.
                self.token_service.discard_candidate(issued["token_id"])
            else:
                # Invalidate only the failed first-delivery token.
                self.token_service.revoke(issued["token_id"])
            # Restore the durable predecessor or first-delivery failure state.
            self._finish_delivery(enrollment_id, int(selected["delivery_generation"]), None, False)
            # Preserve the original bounded failure.
            raise
        # Build one stable provider idempotency key from opaque identifiers only.
        mail_key = f"{enrollment_id}-{selected['delivery_generation']}-{issued['token_id']}"
        # Submit the transient bearer through the existing mail state machine.
        try:
            # Send the purpose-owned same-origin verification link.
            receipt = self.mail_service.submit(PURPOSE, selected["email"], token=issued["token"], idempotency_key=mail_key, locale=selected["locale"])
        # Freeze every delivery failure as recoverable without retaining bearer material.
        except Exception:
            # Discard a failed replacement without touching its active predecessor.
            if selected.get("previous_token_id"):
                # Revoke only the non-consumable candidate.
                self.token_service.discard_candidate(issued["token_id"])
            else:
                # Revoke a failed first-delivery generation.
                self.token_service.revoke(issued["token_id"])

            # Persist recoverable delivery failure before re-raising.
            self._finish_delivery(enrollment_id, int(selected["delivery_generation"]), issued["token_id"], False)
            # Preserve the existing bounded public error class.
            raise

        # Persist the provider result before token promotion so a crash can finish exact delivery.
        def provider_recorded(raw_state: Any) -> dict:
            # Validate durable state before receipt publication.
            state = self._state(raw_state)
            # Resolve the exact delivery owner and replacement packet.
            row = self._find(state, enrollment_id)
            # Resolve the bounded candidate metadata.
            replacement = (row or {}).get("replacement")
            # Require the exact prepared candidate generation.
            if row is None or row.get("status") != "delivery_pending" or int(row.get("delivery_generation") or 0) != int(selected["delivery_generation"]) or not isinstance(replacement, dict) or int(replacement.get("generation") or 0) != int(selected["delivery_generation"]) or replacement.get("phase") != "candidate_prepared" or replacement.get("candidate_token_id") != issued["token_id"]:
                # Preserve concurrent state for recovery.
                raise ConflictError("Signup delivery generation changed")
            # Bind only opaque provider metadata and a fixed delivery result.
            replacement.update({"phase": "delivered" if receipt.get("status") == "sent" else "candidate_prepared", "candidate_mail_delivery_id": receipt.get("delivery_id"), "candidate_delivery_status": receipt.get("status")})
            # Refresh the ambiguity timestamp after provider return.
            row["updated_at"] = self.clock()
            # Return the complete pending document.
            return state
        # Commit provider receipt evidence before promotion or rollback.
        update_json(self.store_path, provider_recorded, default_pending_enrollments)
        # Expose the exact provider-sent crash boundary to provider-free tests.
        self._checkpoint("provider_recorded")

        # Revoke an undelivered candidate before restoring any predecessor generation.
        if receipt.get("status") != "sent":
            # Discard a replacement candidate or revoke an unsuccessful first bearer.
            if selected.get("previous_token_id"):
                # Preserve the predecessor as the sole active token.
                self.token_service.discard_candidate(issued["token_id"])
            else:
                # Invalidate only the unsuccessful first bearer.
                self.token_service.revoke(issued["token_id"])
        # Promote a delivered replacement and revoke its predecessor in one token-document transaction.
        replacement_promoted = receipt.get("status") == "sent" and bool(selected.get("previous_token_id")) and self.token_service.promote_candidate(issued["token_id"], selected["previous_token_id"])
        # Discard a delivered candidate whose exact predecessor binding could not be promoted.
        if receipt.get("status") == "sent" and selected.get("previous_token_id") and not replacement_promoted:
            # Keep the predecessor authoritative despite the unusable provider message.
            self.token_service.discard_candidate(issued["token_id"])
        # Treat an unpromotable delivered candidate as failed so the predecessor metadata is restored.
        delivery_accepted = receipt.get("status") == "sent" and (not selected.get("previous_token_id") or replacement_promoted)
        # Mark a successful promotion durably before the final pending-state transition.
        if delivery_accepted:
            # Persist the promoted phase so a lost final write remains recoverable.
            def promoted(raw_state: Any) -> dict:
                # Validate the complete pending document.
                state = self._state(raw_state)
                # Resolve the exact replacement packet.
                row = self._find(state, enrollment_id)
                # Require the exact delivered candidate.
                if row is None or row.get("status") != "delivery_pending" or int(row.get("delivery_generation") or 0) != int(selected["delivery_generation"]) or not isinstance(row.get("replacement"), dict) or int(row["replacement"].get("generation") or 0) != int(selected["delivery_generation"]) or row["replacement"].get("phase") != "delivered" or row["replacement"].get("candidate_token_id") != issued["token_id"]:
                    # Preserve concurrent state.
                    raise ConflictError("Signup delivery generation changed")
                # Publish only the fixed promoted phase.
                row["replacement"]["phase"] = "promoted"
                # Refresh the lifecycle timestamp.
                row["updated_at"] = self.clock()
                # Return the complete document.
                return state
            # Commit the promotion recovery marker.
            update_json(self.store_path, promoted, default_pending_enrollments)
            # Expose the post-promotion/pre-finalization crash boundary.
            self._checkpoint("candidate_promoted")
        # Persist the provider result without raw recipient or bearer output.
        self._finish_delivery(enrollment_id, int(selected["delivery_generation"]), issued["token_id"], delivery_accepted)
        # Expose the terminal delivery boundary after all durable documents agree.
        self._checkpoint("delivery_finalized")
        # Emit only opaque lifecycle identifiers.
        self.audit_sink("email_enrollment_delivery", enrollment_id=enrollment_id, status="pending" if delivery_accepted else "delivery_failed")
        # Return one enumeration-safe acknowledgement for every accepted request.
        return dict(PENDING_RECEIPT)

    # Begin one account-free, player-free, session-free email signup. (AUTH-018)
    def initiate(self, email: str, password: str, display_name: str, locale: str, terms_version: str, accepted: bool, idempotency_key: str, client_reference: str = "service") -> dict:
        # Require both public signup policy and provider readiness before pending state.
        self._require_ready()
        # Validate transient identity and consent fields.
        normalized = self._email(email)
        # Validate the password before deriving a verifier for pending state.
        auth.validate_enrollment_password(password)
        # Normalize the player-visible label.
        label = str(display_name or "").strip()[:80]
        # Require one bounded nonempty display name.
        if not label or any(character in label for character in "\r\n"):
            # Fail before any pending credential state.
            raise ValidationError("Signup request is invalid")
        # Require a governed locale and the exact current terms acknowledgement.
        if locale not in LOCALES or accepted is not True or str(terms_version or "") != config.GUEST_TERMS_VERSION:
            # Refuse stale, unsupported, or implied consent.
            raise ValidationError("Signup request is invalid")
        # Validate the caller replay key and compute non-reversible lookup verifiers.
        caller_key = self._idempotency(idempotency_key)
        # Digest the normalized recipient for pending-row lookup.
        recipient_digest = self._digest("recipient", normalized)
        # Digest the caller key independently from identity lookup.
        idempotency_digest = self._digest("initiate-idempotency", caller_key)
        # Encode the complete transient request meaning without relying on ambiguous delimiters.
        request_meaning = json.dumps({"email": normalized, "password": password, "display_name": label, "locale": locale, "terms_version": terms_version, "accepted": accepted}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        # Persist only a keyed verifier so terminal replay does not require retained credentials or profile data.
        initiate_request_digest = self._digest("initiate-request", request_meaning)
        # Reconcile one crashed generation before exact replay or recipient suppression classification.
        self._reconcile_delivery(recipient_digest)
        # Hash the password before any durable write and never store its raw value.
        password_hash = auth.hash_password(password)
        # Capture the newly reserved row or exact replay.
        selected = {"replay": False}

        # Reserve one pending enrollment without creating canonical identity or wallet state.
        def reserve(raw_state: Any) -> dict:
            # Validate the complete durable document.
            state = self._state(raw_state)
            # Apply bounded terminal cleanup in the same provider transaction as initiation.
            self._prune_terminal(state, self.clock())
            # Resolve an exact idempotent initiation replay.
            replay = next((row for row in state["enrollments"] if hmac.compare_digest(str(row.get("initiate_idempotency_digest", "")), idempotency_digest)), None)
            # Validate stable request meaning on caller-key reuse.
            if replay is not None:
                # Reject changed recipient, name, locale, terms, consent, or credential meaning by one keyed verifier.
                if not hmac.compare_digest(str(replay.get("initiate_request_digest", "")), initiate_request_digest):
                    # Preserve the original request and all identity state.
                    raise ConflictError("Signup idempotency key was reused with different inputs")
                # Publish the compatible row for safe replay.
                selected.update(dict(replay))
                # Mark the request as a replay.
                selected["replay"] = True
                # Leave durable state unchanged.
                return state
            # Charge only the first distinct initiation after exact replay classification.
            self._enforce_rate(state, "initiate", client_reference, self.clock())
            # Suppress another active recipient request so initiation cannot enumerate pending-address state.
            if any(row.get("recipient_digest") == recipient_digest and row.get("status") in {"reserved", "issuing", "delivery_pending", "pending", "verifying"} for row in state["enrollments"]):
                # Return the ordinary acknowledgement without creating a row or another delivery generation.
                selected["suppressed"] = True
                # Preserve the sole current pending row and bearer.
                return state
            # Capture one consistent creation instant.
            now = self.clock()
            # Allocate deterministic recovery identities once before any delivery.
            row = {"enrollment_id": self.id_factory("email_enrollment"), "email": normalized, "recipient_digest": recipient_digest, "password_hash": password_hash, "display_name": label, "locale": locale, "terms_version": terms_version, "status": "reserved", "delivery_generation": 0, "delivery_status": None, "token_id": None, "mail_delivery_id": None, "expires_at": None, "initiate_idempotency_digest": idempotency_digest, "initiate_request_digest": initiate_request_digest, "verification": None, "user_id": self.id_factory("user_email"), "player_id": self.id_factory("player_email"), "created_at": now, "updated_at": now, "verified_at": None, "cancelled_at": None}
            # Append only pending credentials and server-owned recovery metadata.
            state["enrollments"].append(row)
            # Publish a detached copy for token delivery.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Commit the account-free signup reservation.
        update_json(self.store_path, reserve, default_pending_enrollments)
        # Return the recipient-independent acknowledgement for a different-key pending-address lookup.
        if selected.get("suppressed"):
            # Avoid revealing pending state or replacing its current bearer.
            return dict(PENDING_RECEIPT)
        # Return an already delivered exact replay without another provider request.
        if selected.get("replay") and selected.get("status") in {"issuing", "delivery_pending", "pending", "complete", "cancelled"}:
            # Preserve the same enumeration-safe acknowledgement.
            return dict(PENDING_RECEIPT)
        # Deliver or recover the first verification generation.
        return self._deliver(selected["enrollment_id"], "initiate")

    # Replace a pending signup bearer while preserving an enumeration-safe response.
    def resend(self, email: str, locale: str, idempotency_key: str, client_reference: str = "service") -> dict:
        # Require the same disabled-by-default readiness as initiation.
        self._require_ready()
        # Validate transient inputs and bind the action to a digest only.
        normalized = self._email(email)
        # Require one governed locale and bounded replay key.
        if locale not in LOCALES:
            # Fail before any token replacement.
            raise ValidationError("Signup request is invalid")
        # Digest the transient recipient for row lookup.
        recipient_digest = self._digest("recipient", normalized)
        # Digest the caller action key for exact replay.
        action_digest = self._digest("resend-idempotency", self._idempotency(idempotency_key))
        # Reconcile a provider-confirmed or abandoned prior generation before resend classification.
        self._reconcile_delivery(recipient_digest)
        # Capture a resendable row when one exists.
        selected = {"replay": False}

        # Reserve the resend action atomically.
        def reserve(raw_state: Any) -> dict:
            # Validate durable state before recipient lookup.
            state = self._state(raw_state)
            # Apply bounded terminal cleanup in the same provider transaction as resend lookup.
            self._prune_terminal(state, self.clock())
            # Select only a pre-verification pending or failed row.
            row = next((candidate for candidate in state["enrollments"] if candidate.get("recipient_digest") == recipient_digest and candidate.get("status") in {"pending", "delivery_failed"}), None)
            # Return an exact completed resend replay without another generation or allowance.
            if row is not None and hmac.compare_digest(str(row.get("resend_idempotency_digest", "")), action_digest):
                # Mark the action as replayed.
                selected.update({"replay": True, **dict(row)})
                # Leave the row unchanged.
                return state
            # Charge only the first distinct resend before revealing no recipient lookup state.
            self._enforce_rate(state, "resend", client_reference, self.clock())
            # Return the generic acknowledgement when no active row exists.
            if row is None:
                # Leave all state unchanged to prevent mailbox enumeration.
                return state
            # Validate the fixed cooldown before any token generation can be replaced.
            if config.EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS < 0 or config.EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS > 86_400:
                # Fail closed rather than silently removing recipient protection.
                raise RuntimeError("Verified email enrollment resend policy is outside supported bounds")
            # Suppress address-only replacement while the latest delivery remains inside its cooldown.
            if self._parse_time(row.get("updated_at")) + timedelta(seconds=config.EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS) > self._parse_time(self.clock()):
                # Bind this accepted suppression so exact lost-response replay bypasses rate charging.
                row["resend_idempotency_digest"] = action_digest
                # Return the same acknowledgement used for absent recipients without changing the bearer.
                selected["suppressed"] = True
                # Preserve current token, delivery, and replay metadata.
                return state
            # Store only the accepted action verifier.
            row["resend_idempotency_digest"] = action_digest
            # Publish the selected row for delivery.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Commit the resend reservation.
        update_json(self.store_path, reserve, default_pending_enrollments)
        # Avoid a provider call for absent or exact replayed recipients.
        if not selected.get("enrollment_id") or selected.get("replay") or selected.get("suppressed"):
            # Return the same acknowledgement for every lookup result.
            return dict(PENDING_RECEIPT)
        # Deliver one replacement generation.
        try:
            # Attempt one bounded replacement whose candidate cannot invalidate the predecessor on failure.
            return self._deliver(selected["enrollment_id"], "resend")
        # Collapse provider throttling and delivery failure into the same absent-recipient acknowledgement.
        except Exception:
            # Preserve non-enumeration while the delivery helper has already restored the old bearer.
            return dict(PENDING_RECEIPT)

    # Cancel one still-pending signup only with its current delivered bearer.
    def cancel(self, token: str, email: str, idempotency_key: str, client_reference: str = "service") -> dict:
        # Preserve the disabled-by-default public signup boundary.
        if not self.enabled:
            # Reject before recipient lookup or token mutation.
            raise ForbiddenError("Full account signup is disabled")
        # Validate and digest the transient recipient request.
        normalized = self._email(email)
        # Normalize a bounded transient ownership bearer without persisting it.
        bearer = str(token or "")
        # Compute the recipient lookup verifier.
        recipient_digest = self._digest("recipient", normalized)
        # Compute the exact cancel replay verifier.
        action_digest = self._digest("cancel-idempotency", self._idempotency(idempotency_key))
        # Bind exact replay to the same recipient and bearer meaning without storing either raw value.
        request_digest = self._digest("cancel-request", json.dumps({"email": normalized, "token_digest": self._digest("cancel-bearer", bearer)}, sort_keys=True, separators=(",", ":")))
        # Reconcile any provider-confirmed delivery before terminal cancellation chooses its bearer.
        self._reconcile_delivery(recipient_digest)
        # Capture only opaque row and replay metadata.
        selected = {"replay": False}

        # Classify exact replay and charge only one distinct ownership attempt.
        def classify(raw_state: Any) -> dict:
            # Validate durable state before recipient lookup.
            state = self._state(raw_state)
            # Apply bounded terminal cleanup before replay classification.
            self._prune_terminal(state, self.clock())
            # Resolve one recipient row without exposing the lookup result.
            row = next((candidate for candidate in state["enrollments"] if candidate.get("recipient_digest") == recipient_digest), None)
            # Return one exact terminal replay before rate or bearer validation.
            if row is not None and row.get("status") == "cancelled" and hmac.compare_digest(str(row.get("cancel_idempotency_digest", "")), action_digest) and hmac.compare_digest(str(row.get("cancel_request_digest", "")), request_digest):
                # Mark only the stable terminal result.
                selected["replay"] = True
                # Leave terminal state unchanged.
                return state
            # Charge every first distinct cancel attempt independently from verification.
            self._enforce_rate(state, "cancel", client_reference, self.clock())
            # Publish a detached pre-verification lifecycle row when one exists.
            if row is not None and row.get("status") in {"issuing", "delivery_pending", "pending"}:
                # Retain only opaque identifiers and fixed status for the second guarded mutation.
                selected.update({"enrollment_id": row.get("enrollment_id"), "token_id": row.get("token_id"), "delivery_generation": int(row.get("delivery_generation") or 0), "status": row.get("status")})
            # Return the complete document without terminalizing before ownership proof.
            return state
        # Persist rate evidence and replay classification atomically.
        update_json(self.store_path, classify, default_pending_enrollments)
        # Return exact cancellation replay without requiring the now-revoked bearer to be active.
        if selected.get("replay"):
            # Preserve one stable terminal receipt.
            return {"status": "cancelled"}
        # Reject absent or nondelivered recipient state through the same ownership envelope.
        if not selected.get("enrollment_id"):
            # Reveal no recipient lifecycle state.
            self._invalid_cancellation()
        # Reject absent, unbounded, or control-character bearer material only after charging the distinct attempt.
        if len(bearer) < 16 or len(bearer) > 512 or any(character in bearer for character in "\r\n"):
            # Preserve one mailbox-independent ownership failure.
            self._invalid_cancellation()
        # Authorize the currently active recipient-bound bearer without consuming later verification use.
        try:
            # Resolve only the opaque current token identifier.
            authorized = self.token_service.authorize_active(PURPOSE, bearer, normalized)
        # Collapse every token-state rejection into one cancellation result.
        except Exception:
            # Reveal no stale, wrong, revoked, candidate, or cross-recipient classification.
            self._invalid_cancellation()
        # Expose the post-authorization/pre-terminalization race boundary to provider-free tests.
        self._checkpoint("cancel_authorized")

        # Commit terminal cancellation only when lifecycle and current bearer remain unchanged.
        def cancel_row(raw_state: Any) -> dict:
            # Validate durable state before recipient lookup.
            state = self._state(raw_state)
            # Resolve only the exact previously classified row.
            row = self._find(state, selected["enrollment_id"])
            # Require the same pre-verification lifecycle and active token binding.
            if row is None or row.get("status") not in {"issuing", "delivery_pending", "pending"} or int(row.get("delivery_generation") or 0) != int(selected["delivery_generation"]) or row.get("token_id") != authorized.get("token_id"):
                # Abort without changing terminal or concurrent delivery state.
                raise ConflictError("Signup cancellation ownership changed")
            # Retain only an opaque in-flight candidate id for post-commit revocation.
            selected["candidate_token_id"] = (row.get("replacement") or {}).get("candidate_token_id") if isinstance(row.get("replacement"), dict) else None
            # Persist the terminal lifecycle and exact replay verifier before token revocation.
            row.update({"status": "cancelled", "cancel_idempotency_digest": action_digest, "cancel_request_digest": request_digest, "cancelled_at": self.clock(), "updated_at": self.clock()})
            # Remove the now-terminal delivery recovery packet after capturing its opaque candidate id.
            row.pop("replacement", None)
            # Remove recipient, credential, and profile material as part of the same terminal commit.
            self._scrub_terminal_credentials(row)
            # Publish only opaque metadata to the revocation step.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Persist terminal cancellation atomically.
        try:
            # Serialize the terminal ownership decision through the provider document.
            update_json(self.store_path, cancel_row, default_pending_enrollments)
        # Collapse every concurrency loser into the same public ownership rejection.
        except Exception:
            # Preserve any concurrent terminal or delivery owner.
            self._invalid_cancellation()
        # Revoke the exact current generation if one existed.
        if selected.get("token_id"):
            # Token revocation is idempotent for exact replay.
            self.token_service.revoke(selected["token_id"])
        # Revoke an in-flight candidate without depending on predecessor state.
        if selected.get("candidate_token_id"):
            # Discard remains idempotent and cannot activate the candidate.
            if not self.token_service.discard_candidate(selected["candidate_token_id"]):
                # Revoke an already-promoted candidate so cancellation cannot leave an active bearer.
                self.token_service.revoke(selected["candidate_token_id"])
        # Return one recipient-independent completion receipt.
        return {"status": "cancelled"}

    # Consume one verification bearer and recoverably activate its account exactly once.
    def verify(self, token: str, email: str, idempotency_key: str, client_reference: str = "service") -> dict:
        # Reject every request generically while signup remains disabled.
        if not self.enabled:
            # Avoid disclosing policy or pending recipient state.
            self._invalid_verification()
        # Validate transient request values before any claim.
        normalized = self._email(email)
        # Validate and digest the caller replay key.
        caller_key = self._idempotency(idempotency_key)
        # Compute lookup and recovery verifiers.
        recipient_digest = self._digest("recipient", normalized)
        # Bind every recovery step to the caller-owned key.
        idempotency_digest = self._digest("verify-idempotency", caller_key)
        # Reconcile a durably delivered replacement so its emailed bearer can be verified after a crash.
        self._reconcile_delivery(recipient_digest)
        # Capture the exact pending row selected by the atomic claim.
        selected = {"complete_replay": False}

        # Establish or resume one caller-bound verification claim.
        def claim(raw_state: Any) -> dict:
            # Validate the complete pending document.
            state = self._state(raw_state)
            # Apply bounded terminal cleanup in the same provider transaction as verification claim.
            self._prune_terminal(state, self.clock())
            # Find one pending or recoverable row for this recipient.
            candidates = [row for row in state["enrollments"] if row.get("recipient_digest") == recipient_digest and row.get("status") in {"pending", "verifying", "complete"}]
            # Prefer an exact caller-bound recovery row.
            row = next((candidate for candidate in candidates if hmac.compare_digest(str((candidate.get("verification") or {}).get("idempotency_digest", "")), idempotency_digest)), None)
            # Charge only a first distinct verification attempt, never exact lost-response recovery.
            if row is None:
                # Bound absent recipients and changed callers before any public classification.
                self._enforce_rate(state, "verify", client_reference, self.clock())
            # Otherwise select the single pending generation.
            row = row or next((candidate for candidate in candidates if candidate.get("status") == "pending"), None)
            # Reject missing, cancelled, expired, or competing claims generically.
            if row is None:
                # Abort without changing durable state.
                self._invalid_verification()
            # Return an exact completed lost-response replay.
            if row.get("status") == "complete":
                # Mark the terminal replay for the caller.
                selected.update({**dict(row), "complete_replay": True})
                # Leave the terminal row unchanged.
                return state
            # Require exact caller ownership for an in-progress recovery.
            if row.get("status") == "verifying" and not hmac.compare_digest(str((row.get("verification") or {}).get("idempotency_digest", "")), idempotency_digest):
                # Keep the original recovery owner authoritative.
                self._invalid_verification()
            # Create the initial account-free claim before token consumption.
            if row.get("status") == "pending":
                # Persist only caller verifier and fixed recovery phase.
                row["verification"] = {"idempotency_digest": idempotency_digest, "phase": "claimed", "token_id": None, "last_error": None}
                # Move to the recoverable internal lifecycle.
                row["status"] = "verifying"
                # Refresh operator-visible lifecycle time.
                row["updated_at"] = self.clock()
            # Publish the selected recovery row.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Persist the pre-consumption claim.
        update_json(self.store_path, claim, default_pending_enrollments)
        # Return the generic terminal success without repeating side effects.
        if selected.get("complete_replay"):
            # Expose no account or wallet identifiers.
            return {"status": "enrolled"}
        # Reserve canonical mailbox uniqueness before consuming the bearer.
        try:
            # Reuse the account-free reservation boundary with the enrollment id as saga owner.
            auth.reserve_invited_identity(normalized, selected["enrollment_id"], selected["user_id"], selected["player_id"], selected["expires_at"])
            # Consume or replay the exact purpose/recipient-bound bearer.
            consumed = self.token_service.consume(PURPOSE, str(token or ""), subject=normalized, subject_active=True, idempotency_key=caller_key)
            # Require the current delivered generation.
            if consumed.get("token_id") != selected.get("token_id"):
                # Preserve the claim for generic failure recovery.
                raise ConflictError("Signup verification generation changed")
        # Release only claims that never crossed confirmed token consumption.
        except Exception:
            # Return the row to pending only while it remains at the claimed phase.
            def abandon(raw_state: Any) -> dict:
                # Validate durable state before claim release.
                state = self._state(raw_state)
                # Resolve the exact selected row.
                row = self._find(state, selected.get("enrollment_id"))
                # Release only this caller's pre-consumption claim.
                if row is not None and row.get("status") == "verifying" and (row.get("verification") or {}).get("phase") == "claimed" and hmac.compare_digest(str((row.get("verification") or {}).get("idempotency_digest", "")), idempotency_digest):
                    # Restore the delivered pending state.
                    row.update({"status": "pending", "verification": None, "updated_at": self.clock()})
                # Return the complete document.
                return state
            # Persist the safe account-free recovery state.
            update_json(self.store_path, abandon, default_pending_enrollments)
            # Release only an account-free reservation.
            auth.release_invited_identity(selected.get("enrollment_id"))
            # Collapse every public rejection.
            self._invalid_verification()

        # Record the token-consumed boundary before any account or wallet creation.
        def token_consumed(raw_state: Any) -> dict:
            # Validate durable state before phase advancement.
            state = self._state(raw_state)
            # Resolve the caller-owned recovery row.
            row = self._find(state, selected["enrollment_id"])
            # Require the exact recovery binding.
            if row is None or row.get("status") != "verifying" or not hmac.compare_digest(str((row.get("verification") or {}).get("idempotency_digest", "")), idempotency_digest):
                # Preserve all state for operator recovery.
                raise ConflictError("Signup verification claim changed")
            # Advance only after confirmed token consumption.
            row["verification"].update({"phase": "token_consumed", "token_id": consumed["token_id"], "last_error": None})
            # Refresh the lifecycle timestamp.
            row["updated_at"] = self.clock()
            # Return the complete document.
            return state
        # Commit the durable point after which same-key recovery owns the saga.
        update_json(self.store_path, token_consumed, default_pending_enrollments)
        # Provision and fund the inactive account under recoverable deterministic identifiers.
        try:
            # Create or replay the inactive canonical identity without a session.
            user = auth.provision_verified_email_user(normalized, selected["password_hash"], selected["display_name"], selected["locale"], selected["terms_version"], selected["enrollment_id"], selected["user_id"], selected["player_id"])
            # Create or replay a zero-balance inactive wallet.
            players.ensure_email_enrollment_player(selected["player_id"], selected["display_name"])
            # Credit configured initial funds through one deterministic ledger action.
            ledger.credit_once(selected["player_id"], config.ACCOUNT_STARTING_BALANCE, "ACCOUNT_STARTING_BALANCE", f"email-enrollment:{selected['enrollment_id']}:starting-balance", details={"enrollment_id": selected["enrollment_id"], "purpose": "verified_email_signup"})
            # Activate the funded wallet only after its ledger event is durable.
            players.activate_email_enrollment_player(selected["player_id"])
            # Activate the account last without silently creating any session.
            active_user = auth.activate_verified_email_user(selected["enrollment_id"], user["user_id"], user["player_id"])
        # Preserve every post-consumption partial result for exact-key retry.
        except Exception:
            # Store only a low-cardinality recovery cue.
            def recovery_required(raw_state: Any) -> dict:
                # Validate state before recording recoverable failure.
                state = self._state(raw_state)
                # Resolve the exact recovery row.
                row = self._find(state, selected["enrollment_id"])
                # Mark only the matching caller-owned in-progress saga.
                if row is not None and row.get("status") == "verifying" and isinstance(row.get("verification"), dict):
                    # Never persist exception text, mailbox, bearer, or credential material.
                    row["verification"]["last_error"] = "identity_or_wallet_provisioning"
                    # Refresh the lifecycle timestamp.
                    row["updated_at"] = self.clock()
                # Return the complete document.
                return state
            # Persist the recoverable operator state.
            update_json(self.store_path, recovery_required, default_pending_enrollments)
            # Return one generic public result.
            self._invalid_verification()

        # Commit the terminal pending-enrollment state after account and wallet activation.
        def finalize(raw_state: Any) -> dict:
            # Validate durable state before terminal transition.
            state = self._state(raw_state)
            # Resolve the exact caller-owned recovery row.
            row = self._find(state, selected["enrollment_id"])
            # Compare the durable caller verifier without leaking it through timing.
            same_caller = row is not None and hmac.compare_digest(str((row.get("verification") or {}).get("idempotency_digest", "")), idempotency_digest)
            # Accept only the exact active identity binding.
            if row is None or row.get("status") != "verifying" or not same_caller or active_user.get("user_id") != row.get("user_id") or active_user.get("player_id") != row.get("player_id"):
                # Preserve the active resources for exact-key operator recovery.
                raise ConflictError("Signup verification finalization changed")
            # Transition to terminal complete state.
            row.update({"status": "complete", "verified_at": self.clock(), "updated_at": self.clock()})
            # Retain only the fixed complete recovery binding.
            row["verification"].update({"phase": "complete", "last_error": None})
            # Remove pending recipient, credential, and profile material after canonical activation.
            self._scrub_terminal_credentials(row)
            # Return the complete document.
            return state
        # Persist the terminal state.
        update_json(self.store_path, finalize, default_pending_enrollments)
        # Emit opaque identifiers only after terminal convergence.
        self.audit_sink("email_enrollment_verified", enrollment_id=selected["enrollment_id"], user_id=active_user["user_id"])
        # Return an identifier-free success that instructs the browser to sign in explicitly.
        return {"status": "enrolled"}

    # Raise the single public verification error.
    @staticmethod
    def _invalid_verification() -> None:
        # Collapse disabled, malformed, expired, revoked, consumed, and raced requests.
        raise ValidationError("Signup verification is unavailable", dict(GENERIC_VERIFICATION_DETAILS))

    # Raise one public cancellation ownership error.
    @staticmethod
    def _invalid_cancellation() -> None:
        # Collapse absent, malformed, stale, revoked, candidate, cross-recipient, and raced requests.
        raise ValidationError("Signup cancellation is unavailable", dict(GENERIC_CANCELLATION_DETAILS))


# Build one lightweight configured facade from environment-loaded policy.
def configured_service() -> PendingEnrollmentService:
    # Compose the disabled-by-default service from approved foundations.
    return PendingEnrollmentService(enabled=config.SIGNUP_ENABLED, digest_key=config.MAIL_DIGEST_KEY)


# Begin one configured verified-email signup.
def initiate(email: str, password: str, display_name: str, locale: str, terms_version: str, accepted: bool, idempotency_key: str, client_reference: str = "service") -> dict:
    # Delegate validation, delivery, privacy, and lifecycle policy.
    return configured_service().initiate(email, password, display_name, locale, terms_version, accepted, idempotency_key, client_reference)


# Replace one configured verification delivery generation.
def resend(email: str, locale: str, idempotency_key: str, client_reference: str = "service") -> dict:
    # Delegate enumeration safety and token replacement.
    return configured_service().resend(email, locale, idempotency_key, client_reference)


# Verify and activate one configured pending enrollment.
def verify(token: str, email: str, idempotency_key: str, client_reference: str = "service") -> dict:
    # Delegate exactly-once activation without session creation.
    return configured_service().verify(token, email, idempotency_key, client_reference)


# Cancel one configured pending enrollment.
def cancel(token: str, email: str, idempotency_key: str, client_reference: str = "service") -> dict:
    # Delegate bearer ownership, rate control, terminalization, and token revocation.
    return configured_service().cancel(token, email, idempotency_key, client_reference)
