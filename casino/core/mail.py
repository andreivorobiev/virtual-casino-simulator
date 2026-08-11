# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Disabled-by-default transactional-mail boundary with privacy-safe durable state. (MAIL-001..006)

This infrastructure prepares fixed enrollment and recovery messages without exposing a consumer
route. Provider delivery requires both the repository feature gate and an independent network
release gate. Persisted records contain keyed digests and bounded status metadata only.
"""

# Import hashing primitives so sensitive identifiers are represented only by keyed digests.
import hashlib
# Import HTML escaping so translated template values cannot create markup.
import html
# Import keyed hashing so recipient, token, payload, and idempotency values remain non-reversible.
import hmac
# Import JSON encoding only for the transient provider request body.
import json
# Import time primitives for bounded retry, rate, and retention policy.
import time
# Import the provider HTTP client lazily used only after every release gate passes.
import urllib.request
# Import provider HTTP status failures without ever consuming their response bodies.
import urllib.error
# Import safe query encoding for the fixed canonical-origin bearer link.
from urllib.parse import quote

# Import configuration through the module so isolated tests can inject explicit service values.
from casino import config
# Import the shared audit logger while keeping event fields non-sensitive.
from casino.core import logger
# Import the canonical UTC clock for human-readable audit timestamps.
from casino.core.clock import utc_now
# Import random opaque identifiers that reveal no recipient or token material.
from casino.core.ids import new_id
# Import atomic and read-only state helpers shared by JSON and MySQL providers.
from casino.core.state_store import read_json, update_json
# Import stable public errors for validation, collision, and rate-limit outcomes.
from casino.errors import ConflictError, RateLimitError, ValidationError

# Store the mail state below the configured provider-backed data root.
MAIL_STATE_PATH = config.DATA_DIR / "mail" / "deliveries.json"
# Publish the private state schema independently from the application storage schema.
MAIL_STATE_SCHEMA = "mail-state.v2"
# Keep supported purposes fixed so callers cannot supply arbitrary templates or redirect paths.
PURPOSES = frozenset({"invitation", "email_verification", "password_reset", "magic_link"})
# Keep supported locales fixed to the governed browser languages.
LOCALES = frozenset({"en-US", "ru-RU"})
# Map each purpose to one fixed same-origin path that callers cannot override.
PURPOSE_PATHS = {
    "invitation": "/enroll/invitation",
    "email_verification": "/enroll/verify",
    "password_reset": "/account/reset",
    "magic_link": "/account/magic-link",
}
# Name one brand so every transactional subject line rebrands from a single edit.
BRAND_NAME = "TiltSeven"
# Provide accessible English subject and explanatory copy for every authorized purpose.
ENGLISH_TEMPLATES = {
    "invitation": (f"Your {BRAND_NAME} invitation", "Use the secure link below to accept your private invitation."),
    "email_verification": (f"Verify your {BRAND_NAME} email", "Use the secure link below to verify your email address."),
    "password_reset": (f"Reset your {BRAND_NAME} password", "Use the secure link below to reset your password."),
    "magic_link": (f"Your {BRAND_NAME} sign-in link", "Use the secure link below to sign in to your existing private account."),
}
# Provide equivalent Russian subject and explanatory copy for every authorized purpose.
RUSSIAN_TEMPLATES = {
    "invitation": (f"Приглашение в {BRAND_NAME}", "Откройте защищённую ссылку ниже, чтобы принять личное приглашение."),
    "email_verification": (f"Подтвердите почту {BRAND_NAME}", "Откройте защищённую ссылку ниже, чтобы подтвердить адрес почты."),
    "password_reset": (f"Сбросьте пароль {BRAND_NAME}", "Откройте защищённую ссылку ниже, чтобы сбросить пароль."),
    "magic_link": (f"Ссылка для входа в {BRAND_NAME}", "Откройте защищённую ссылку ниже, чтобы войти в существующую личную учётную запись."),
}
# Collect translated templates behind the governed locale keys.
TEMPLATES = {"en-US": ENGLISH_TEMPLATES, "ru-RU": RUSSIAN_TEMPLATES}
# Classify terminal states that can never be retried by a repeated caller request.
TERMINAL_STATUSES = frozenset({"sent", "failed", "suppressed", "disabled", "release_held", "misconfigured", "uncertain"})


# Signal a provider failure that is known not to have accepted the request and may be retried.
class RetryableDeliveryError(Exception):
    """Known retryable provider failure with no sensitive response attached."""


# Signal an ambiguous provider result that must never be retried automatically.
class AmbiguousDeliveryError(Exception):
    """Provider result whose acceptance is unknown and requires operator reconciliation."""


# Signal a permanent or suppression-worthy provider rejection.
class PermanentDeliveryError(Exception):
    """Known permanent provider rejection with a fixed safe reason code."""

    # Preserve only an allowlisted reason code for state transitions and diagnostics.
    def __init__(self, reason: str = "provider_rejected"):
        # Initialize the base exception without a provider response or payload value.
        super().__init__(reason)
        # Constrain the stored reason to the supported non-sensitive categories.
        self.reason = reason if reason in {"provider_rejected", "bounced", "complaint", "invalid_recipient"} else "provider_rejected"


# Implement a transport that can never access the network.
class DisabledTransport:
    """Inert transport used for disabled and test configurations."""

    # Reject accidental invocation because disabled state is finalized before transport dispatch.
    def send(self, message: dict) -> None:
        # Raise a safe permanent error without inspecting the transient message.
        raise PermanentDeliveryError("provider_rejected")


# Implement the inert-by-default Postmark adapter behind both release gates.
class PostmarkTransport:
    """Minimal provider adapter that stores no request or response material."""

    # Capture the credential only in this ephemeral transport instance.
    def __init__(self, server_token: str):
        # Retain the configured credential in memory for the bounded request header.
        self._server_token = server_token

    # Submit a fully rendered transient message after the service has atomically claimed it.
    def send(self, message: dict) -> None:
        # Encode only the provider fields required for one transactional message.
        body = json.dumps({
            "From": message["from_address"],
            "To": message["recipient"],
            "Subject": message["subject"],
            "TextBody": message["text_body"],
            "HtmlBody": message["html_body"],
            "MessageStream": "outbound",
        }).encode("utf-8")
        # Construct the provider request while keeping the credential solely in its header.
        request = urllib.request.Request(
            "https://api.postmarkapp.com/email",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json", "X-Postmark-Server-Token": self._server_token},
        )
        # Start the bounded request without reading or retaining the raw provider response.
        try:
            # Treat a completed 2xx request as the only unambiguous success.
            with urllib.request.urlopen(request, timeout=10) as response:
                # Reject non-success status values without consuming a response body.
                if int(getattr(response, "status", 0)) < 200 or int(getattr(response, "status", 0)) >= 300:
                    # Treat a returned provider rejection as permanent and value-free.
                    raise PermanentDeliveryError("provider_rejected")
        # Preserve explicitly classified safe failures without wrapping them.
        except PermanentDeliveryError:
            # Re-raise the fixed safe failure category to the delivery state machine.
            raise
        # Classify an explicit non-success HTTP response without reading its body.
        except urllib.error.HTTPError as error:
            # Treat throttling and server-side rejection as known non-accepted retryable outcomes.
            if int(error.code) == 429 or 500 <= int(error.code) < 600:
                # Schedule only the service-owned bounded backoff, never provider-authored timing.
                raise RetryableDeliveryError("provider_temporarily_unavailable") from error
            # Treat other explicit HTTP rejections as permanent without provider response text.
            raise PermanentDeliveryError("provider_rejected") from error
        # Treat timeouts and connection failures as ambiguous because acceptance may have occurred.
        except Exception as error:
            # Raise a value-free ambiguous result and suppress raw exception text.
            raise AmbiguousDeliveryError("provider_result_unknown") from error


# Return a fresh canonical state document.
def default_state() -> dict:
    # Keep deliveries and recipient suppressions separate for bounded diagnostics and cleanup.
    return {"schema_version": MAIL_STATE_SCHEMA, "deliveries": {}, "suppressions": {}}


# Reject structurally malformed state instead of destructively normalizing it.
def _validate_state(state: object) -> dict:
    # Require the exact top-level object shape used by both JSON and MySQL providers.
    if not isinstance(state, dict) or state.get("schema_version") != MAIL_STATE_SCHEMA:
        # Fail without returning a replacement document so update_json cannot overwrite the source.
        raise RuntimeError("transactional mail state requires operator recovery")
    # Require both mutable collections to remain mappings.
    if not isinstance(state.get("deliveries"), dict) or not isinstance(state.get("suppressions"), dict):
        # Fail closed while preserving the malformed document unchanged.
        raise RuntimeError("transactional mail state requires operator recovery")
    # Return the validated state for an in-place atomic mutation.
    return state


# Compute a keyed digest without persisting or logging the source value.
def _digest(key: str, value: str) -> str:
    # Normalize the source only within this expression and return an HMAC-SHA256 hex digest.
    return hmac.new(key.encode("utf-8"), str(value).strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


# Render a fixed canonical-origin link without accepting caller-authored paths or hosts.
def _canonical_link(origin: str, purpose: str, token: str) -> str:
    # Require an absolute HTTPS origin without a path, query, fragment, or trailing slash ambiguity.
    normalized = str(origin or "").strip().rstrip("/")
    # Reject any non-HTTPS or structurally suspicious origin before rendering bearer material.
    if not normalized.startswith("https://") or any(character in normalized[8:] for character in ("/", "?", "#", "\\")):
        # Fail closed without echoing the configured origin.
        raise ValidationError("mail canonical origin is not a safe HTTPS origin", {"reason": "origin_not_https"})
    # Append the encoded bearer only to the purpose-owned same-origin path.
    return f"{normalized}{PURPOSE_PATHS[purpose]}?token={quote(token, safe='')}"


# Render accessible plain-text and HTML alternatives from fixed translated templates.
def _render(origin: str, from_address: str, purpose: str, locale: str, recipient: str, token: str) -> dict:
    # Resolve the authorized subject and explanatory sentence.
    subject, introduction = TEMPLATES[locale][purpose]
    # Build the transient canonical bearer link only after all inputs have been validated.
    link = _canonical_link(origin, purpose, token)
    # Build a concise plain-text alternative whose link purpose is clear without markup.
    text_body = f"{subject}\n\n{introduction}\n{link}\n\nIf you did not request this message, ignore it."
    # Escape every translated/transient value before including it in semantic HTML.
    html_body = f"<!doctype html><html lang=\"{html.escape(locale)}\"><body><main><h1>{html.escape(subject)}</h1><p>{html.escape(introduction)}</p><p><a href=\"{html.escape(link, quote=True)}\">{html.escape(subject)}</a></p><p>If you did not request this message, ignore it.</p></main></body></html>"
    # Return the transient provider payload; callers must never persist this mapping.
    return {"from_address": from_address, "recipient": recipient, "subject": subject, "text_body": text_body, "html_body": html_body}


# Own durable mail submission, retry, suppression, retention, and readiness behavior.
class MailService:
    """Provider-neutral transactional-mail state machine."""

    # Inject every configuration value and side effect so tests never need live provider state.
    def __init__(
        self,
        *,
        state_path=MAIL_STATE_PATH,
        enabled=False,
        network_enabled=False,
        provider="disabled",
        digest_key="",
        canonical_origin="",
        from_address="",
        sending_domain="",
        provider_token="",
        max_attempts=3,
        retry_base_seconds=60,
        rate_limit=5,
        rate_window_seconds=3600,
        retention_seconds=2592000,
        transport=None,
        epoch_clock=None,
    ):
        # Store the provider-backed state path.
        self.state_path = state_path
        # Store the repository feature gate independently from network release.
        self.enabled = bool(enabled)
        # Store the independent network release gate.
        self.network_enabled = bool(network_enabled)
        # Normalize the provider identifier to the fixed adapter allowlist.
        self.provider = str(provider or "disabled").strip().lower()
        # Retain the keyed-digest material in memory only.
        self.digest_key = str(digest_key or "")
        # Retain the canonical public origin for transient fixed links.
        self.canonical_origin = str(canonical_origin or "").strip()
        # Retain the sender address for transient provider payloads.
        self.from_address = str(from_address or "").strip()
        # Retain the verified domain declaration for readiness checks only.
        self.sending_domain = str(sending_domain or "").strip().lower()
        # Retain the provider credential in memory only.
        self.provider_token = str(provider_token or "")
        # Bound attempts to a small positive operator-controlled value.
        self.max_attempts = max(1, min(int(max_attempts), 10))
        # Bound exponential backoff to a positive base interval.
        self.retry_base_seconds = max(1, min(int(retry_base_seconds), 86400))
        # Bound accepted submissions per recipient window.
        self.rate_limit = max(1, min(int(rate_limit), 100))
        # Bound the rate window to one minute through one day.
        self.rate_window_seconds = max(60, min(int(rate_window_seconds), 86400))
        # Bound retention to one day through one year.
        self.retention_seconds = max(86400, min(int(retention_seconds), 31536000))
        # Inject a fake transport for tests or select the inert/default provider adapter.
        self.transport = transport if transport is not None else (PostmarkTransport(self.provider_token) if self.provider == "postmark" else DisabledTransport())
        # Inject a deterministic epoch clock for retry and retention tests.
        self.epoch_clock = epoch_clock if epoch_clock is not None else time.time

    # Report a secret-free readiness state and low-cardinality delivery summary.
    def readiness(self) -> dict:
        # Compute the configuration state without touching the network.
        status, reasons = self._configuration_status()
        # Start with zero counts when state is absent or requires operator recovery.
        counts = {state: 0 for state in ("sending", "sent", "retry_wait", "failed", "suppressed", "uncertain", "disabled", "release_held", "misconfigured")}
        # Start suppression diagnostics with a non-identifying count.
        suppressed_count = 0
        # Read current state for diagnostics without creating an outbox document.
        try:
            # Validate a present document or use a fresh in-memory default when absent.
            state = _validate_state(read_json(self.state_path, default_state))
            # Count only allowlisted status labels across stored delivery records.
            for record in state["deliveries"].values():
                # Increment a recognized state without exposing record identifiers.
                if isinstance(record, dict) and record.get("status") in counts:
                    # Add one to the matching diagnostic bucket.
                    counts[record["status"]] += 1
            # Report only the number of suppressed recipient digests.
            suppressed_count = len(state["suppressions"])
        # Mark unreadable structural state as unavailable without normalizing it.
        except RuntimeError:
            # Override configuration readiness because state recovery is required first.
            status, reasons = "unavailable", ["state_recovery_required"]
        # Return only booleans, allowlisted states/reasons, and aggregate counts.
        return {
            "schema_version": "transactional-mail-readiness.v2",
            "provider": self.provider if self.provider in {"disabled", "postmark"} else "unrecognized",
            "status": status,
            "checks": {
                "feature_enabled": self.enabled,
                "network_release_enabled": self.network_enabled,
                "canonical_origin_https": self._origin_valid(),
                "sender_identity_configured": self._sender_valid(),
                "provider_credential_configured": bool(self.provider_token) if self.provider == "postmark" else False,
                "digest_key_configured": self._digest_key_valid(),
            },
            "reasons": reasons,
            "delivery_summary": counts,
            "suppressed_recipients": suppressed_count,
        }

    # Submit or replay one caller-idempotent message through the atomic state machine.
    def submit(self, purpose: str, recipient: str, *, token: str, idempotency_key: str, locale: str = "en-US") -> dict:
        # Validate all transient inputs before computing digests or mutating state.
        normalized_recipient, normalized_token, normalized_idempotency = self._validate_submission(purpose, recipient, token, idempotency_key, locale)
        # Require a valid keyed-digest configuration even while provider delivery is disabled.
        if not self._digest_key_valid():
            # Fail before persistence rather than store predictable digests.
            raise ValidationError("transactional mail digest key is not configured", {"reason": "digest_key_invalid"})
        # Compute one-way identifiers used for lookup and collision detection.
        recipient_digest = _digest(self.digest_key, normalized_recipient)
        # Digest the bearer independently so no state record contains its value.
        token_digest = _digest(self.digest_key, normalized_token)
        # Digest the caller key so an operational data leak cannot replay a request.
        idempotency_digest = _digest(self.digest_key, normalized_idempotency)
        # Bind the idempotency key to the complete stable request meaning.
        payload_digest = _digest(self.digest_key, "|".join((purpose, locale, recipient_digest, token_digest)))
        # Capture the current epoch once for deterministic claim and rate decisions.
        now = float(self.epoch_clock())
        # Compute the safe pre-transport status and reasons from configuration.
        configuration_status, _ = self._configuration_status()
        # Track whether this process won the atomic transport claim.
        outcome = {"claimed": False, "delivery_id": None}

        # Claim a new or due delivery in one provider transaction.
        def claim(current: object) -> dict:
            # Refuse to normalize a malformed durable document.
            state = _validate_state(current)
            # Prune expired terminal metadata inside the same atomic mutation.
            self._prune_state(state, now)
            # Resolve an existing record by the caller-owned idempotency digest.
            record = state["deliveries"].get(idempotency_digest)
            # Enforce stable request meaning for every replay.
            if record is not None and record.get("payload_digest") != payload_digest:
                # Reject a key reused for a different purpose, recipient, locale, or token.
                raise ConflictError("mail idempotency key was reused with different inputs", {"reason": "idempotency_mismatch"})
            # Return terminal or in-flight records without invoking the transport again.
            if record is not None and record.get("status") != "retry_wait":
                # Publish the existing opaque identifier to the receipt builder.
                outcome["delivery_id"] = record.get("delivery_id")
                # Leave durable state unchanged for a safe replay.
                return state
            # Return a retry record before its bounded backoff becomes due.
            if record is not None and float(record.get("next_retry_at") or 0) > now:
                # Publish the existing opaque identifier without claiming a send.
                outcome["delivery_id"] = record.get("delivery_id")
                # Leave the retry schedule unchanged.
                return state
            # Enforce suppression before creating or retrying a delivery.
            if recipient_digest in state["suppressions"]:
                # Create a stable identifier for a first suppressed submission.
                delivery_id = record.get("delivery_id") if record else new_id("maildlv")
                # Persist only the suppression result and keyed request metadata.
                state["deliveries"][idempotency_digest] = self._record(delivery_id, purpose, locale, recipient_digest, payload_digest, "suppressed", now, attempts=int((record or {}).get("attempts", 0)), reason="recipient_suppressed")
                # Return the safe opaque identifier to this caller.
                outcome["delivery_id"] = delivery_id
                # Finish without a transport claim.
                return state
            # Enforce a bounded per-recipient submission window before a first attempt.
            if record is None and self._recent_recipient_count(state, recipient_digest, now) >= self.rate_limit:
                # Raise inside the transaction so no partial record is written.
                raise RateLimitError("transactional mail rate limit exceeded", {"reason": "recipient_rate_limited"})
            # Reuse the record identifier during retry or allocate a new opaque identifier.
            delivery_id = record.get("delivery_id") if record else new_id("maildlv")
            # Increment only provider attempts, not disabled or held submissions.
            attempts = int((record or {}).get("attempts", 0)) + (1 if configuration_status == "ready" else 0)
            # Transition ready work to sending; otherwise persist the exact safe configuration state.
            status = "sending" if configuration_status == "ready" else configuration_status
            # Persist the atomic claim or inert terminal result without transient content.
            state["deliveries"][idempotency_digest] = self._record(delivery_id, purpose, locale, recipient_digest, payload_digest, status, now, attempts=attempts)
            # Publish the claimed identifier to the current process.
            outcome["delivery_id"] = delivery_id
            # Only a ready transition to sending wins the provider claim.
            outcome["claimed"] = status == "sending"
            # Return the fully mutated state for atomic persistence.
            return state

        # Execute the complete claim through JSON locking or a MySQL row transaction.
        claimed_state = update_json(self.state_path, claim, default_state)
        # Read the persisted record selected by this idempotency digest.
        persisted = claimed_state["deliveries"][idempotency_digest]
        # Return inert, terminal, in-flight, or not-yet-due results without rendering bearer material.
        if not outcome["claimed"]:
            # Emit only an opaque audit identifier, purpose, and fixed status.
            logger.info("mail_delivery_state", delivery_id=outcome["delivery_id"], purpose=purpose, status=persisted["status"])
            # Return the minimum secret-free receipt.
            return self._receipt(persisted)
        # Render the transient message only for the process that won the atomic claim.
        message = _render(self.canonical_origin, self.from_address, purpose, locale, normalized_recipient, normalized_token)
        # Invoke the injected or provider transport outside the state transaction.
        try:
            # Send exactly once for this claimed attempt.
            self.transport.send(message)
        # Schedule a bounded retry only for a known non-accepted retryable failure.
        except RetryableDeliveryError:
            # Finalize a retry or terminal failure without sensitive error text.
            final = self._finalize(idempotency_digest, outcome["delivery_id"], "retryable", now)
        # Freeze ambiguous outcomes so automated retries cannot duplicate delivery.
        except AmbiguousDeliveryError:
            # Record the explicit operator-reconciliation state.
            final = self._finalize(idempotency_digest, outcome["delivery_id"], "uncertain", now)
        # Persist permanent rejection or suppression using only its fixed reason code.
        except PermanentDeliveryError as error:
            # Record the allowlisted permanent result.
            final = self._finalize(idempotency_digest, outcome["delivery_id"], error.reason, now)
        # Treat any unexpected transport exception as ambiguous to preserve at-most-once behavior.
        except Exception:
            # Never expose or persist exception text because provider libraries can echo payloads.
            final = self._finalize(idempotency_digest, outcome["delivery_id"], "uncertain", now)
        # Mark a completed provider request sent when no exception occurred.
        else:
            # Persist the successful terminal transition.
            final = self._finalize(idempotency_digest, outcome["delivery_id"], "sent", now)
        # Emit only the safe terminal status and opaque identifier.
        logger.info("mail_delivery_state", delivery_id=outcome["delivery_id"], purpose=purpose, status=final["status"])
        # Return the minimum secret-free receipt.
        return self._receipt(final)

    # Record an internally verified provider bounce, complaint, or invalid-recipient suppression.
    def record_suppression(self, recipient: str, reason: str) -> dict:
        # Restrict internal suppression reasons to fixed non-sensitive categories.
        if reason not in {"bounced", "complaint", "invalid_recipient"}:
            # Reject arbitrary reason strings that could carry provider response content.
            raise ValidationError("unsupported mail suppression reason", {"reason": "bad_suppression_reason"})
        # Require the digest key before accepting a recipient value.
        if not self._digest_key_valid() or not str(recipient or "").strip():
            # Fail without persisting raw or predictably hashed recipient material.
            raise ValidationError("mail suppression input is invalid", {"reason": "bad_suppression_input"})
        # Compute the only durable recipient representation.
        recipient_digest = _digest(self.digest_key, str(recipient).strip())
        # Capture the event time once.
        now = float(self.epoch_clock())

        # Atomically add suppression and update any matching nonterminal records.
        def suppress(current: object) -> dict:
            # Refuse to rewrite malformed durable state.
            state = _validate_state(current)
            # Store only the recipient digest, fixed reason, and audit timestamps.
            state["suppressions"][recipient_digest] = {"reason": reason, "created_at": now, "updated_at": utc_now()}
            # Visit delivery records without exposing their idempotency digest keys.
            for record in state["deliveries"].values():
                # Mark matching non-sent work suppressed so it cannot later retry.
                if isinstance(record, dict) and record.get("recipient_digest") == recipient_digest and record.get("status") not in {"sent", "uncertain"}:
                    # Persist the terminal suppression state.
                    record["status"] = "suppressed"
                    # Store only the fixed internal reason category.
                    record["reason"] = reason
                    # Update the bounded retention timestamp.
                    record["updated_epoch"] = now
                    # Store a readable application time without provider data.
                    record["updated_at"] = utc_now()
            # Return the mutated state for atomic persistence.
            return state

        # Persist the suppression through the configured storage provider.
        update_json(self.state_path, suppress, default_state)
        # Return a count-free acknowledgement without the recipient or its digest.
        return {"status": "suppressed", "reason": reason}

    # Validate submission values without echoing them in failures.
    def _validate_submission(self, purpose: str, recipient: str, token: str, idempotency_key: str, locale: str) -> tuple[str, str, str]:
        # Require one fixed purpose.
        if purpose not in PURPOSES:
            # Fail with a stable category only.
            raise ValidationError("unsupported transactional mail purpose", {"reason": "bad_purpose"})
        # Require one governed locale.
        if locale not in LOCALES:
            # Fail without echoing the supplied locale.
            raise ValidationError("unsupported transactional mail locale", {"reason": "bad_locale"})
        # Normalize the transient recipient once.
        normalized_recipient = str(recipient or "").strip().lower()
        # Reject empty, control-character, or implausibly long recipient values.
        if not normalized_recipient or "@" not in normalized_recipient or len(normalized_recipient) > 254 or any(character in normalized_recipient for character in "\r\n"):
            # Fail without returning the supplied address.
            raise ValidationError("transactional mail recipient is invalid", {"reason": "bad_recipient"})
        # Normalize the transient bearer without logging it.
        normalized_token = str(token or "").strip()
        # Require bounded non-empty bearer material.
        if not normalized_token or len(normalized_token) > 2048 or any(character in normalized_token for character in "\r\n"):
            # Fail without echoing the bearer.
            raise ValidationError("transactional mail token is invalid", {"reason": "bad_token"})
        # Normalize the caller-owned idempotency value.
        normalized_idempotency = str(idempotency_key or "").strip()
        # Require a bounded key with enough entropy for safe replay lookup.
        if len(normalized_idempotency) < 16 or len(normalized_idempotency) > 200 or any(character in normalized_idempotency for character in "\r\n"):
            # Fail without echoing the caller key.
            raise ValidationError("transactional mail idempotency key is invalid", {"reason": "bad_idempotency_key"})
        # Return normalized transient values to the submission flow.
        return normalized_recipient, normalized_token, normalized_idempotency

    # Compute the externally visible configuration state and safe reason codes.
    def _configuration_status(self) -> tuple[str, list[str]]:
        # Disabled feature state is intentional and takes precedence over incomplete provider config.
        if not self.enabled:
            # Report the single intentional disabled reason.
            return "disabled", ["feature_disabled"]
        # Collect incomplete or unsafe configuration reasons without exposing values.
        reasons = []
        # Require a supported provider adapter.
        if self.provider != "postmark":
            # Record a safe provider-selection category.
            reasons.append("provider_not_configured")
        # Require a safe canonical HTTPS origin.
        if not self._origin_valid():
            # Record a safe origin category.
            reasons.append("canonical_origin_invalid")
        # Require sender identity alignment to the declared sending domain.
        if not self._sender_valid():
            # Record a safe sender category.
            reasons.append("sender_identity_invalid")
        # Require a provider credential without revealing its form or length.
        if self.provider == "postmark" and not self.provider_token:
            # Record a safe credential category.
            reasons.append("provider_credential_missing")
        # Require a unique keyed digest in every enabled configuration.
        if not self._digest_key_valid():
            # Record a safe digest-key category.
            reasons.append("digest_key_invalid")
        # Report misconfiguration before evaluating the independent release gate.
        if reasons:
            # Return every bounded safe reason for Admin remediation.
            return "misconfigured", reasons
        # Hold all provider/network access until independently released.
        if not self.network_enabled:
            # Report only the separate release hold.
            return "release_held", ["network_release_held"]
        # All repository and independent release controls are satisfied.
        return "ready", []

    # Validate the canonical origin without rendering a token.
    def _origin_valid(self) -> bool:
        # Normalize a harmless trailing slash for validation.
        origin = self.canonical_origin.rstrip("/")
        # Accept only one HTTPS origin with no extra path, query, fragment, or backslash.
        return origin.startswith("https://") and bool(origin[8:]) and not any(character in origin[8:] for character in ("/", "?", "#", "\\"))

    # Validate that the configured sender belongs to the declared domain.
    def _sender_valid(self) -> bool:
        # Split only a simple mailbox form and reject control characters.
        if "@" not in self.from_address or any(character in self.from_address for character in "\r\n"):
            # Reject an absent or unsafe sender.
            return False
        # Compare the sender domain to the explicit verified-domain declaration.
        return self.from_address.rsplit("@", 1)[1].lower() == self.sending_domain and bool(self.sending_domain)

    # Validate the keyed-digest value against the known local default and strength floor.
    def _digest_key_valid(self) -> bool:
        # Require at least 32 bytes and reject the committed developer value.
        return len(self.digest_key.encode("utf-8")) >= 32 and self.digest_key != config.LOCAL_MAIL_DIGEST_KEY

    # Build one persistence-safe delivery record.
    def _record(self, delivery_id: str, purpose: str, locale: str, recipient_digest: str, payload_digest: str, status: str, now: float, *, attempts: int, reason: str | None = None) -> dict:
        # Store only opaque identifiers, keyed digests, allowlisted metadata, and bounded timestamps.
        record = {
            "delivery_id": delivery_id,
            "purpose": purpose,
            "locale": locale,
            "recipient_digest": recipient_digest,
            "payload_digest": payload_digest,
            "status": status,
            "attempts": attempts,
            "next_retry_at": None,
            "reason": reason,
            "created_epoch": now,
            "updated_epoch": now,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        # Return the persistence-safe mapping.
        return record

    # Count recent per-recipient submissions for the bounded rate window.
    def _recent_recipient_count(self, state: dict, recipient_digest: str, now: float) -> int:
        # Count only records for this digest whose creation time remains inside the window.
        return sum(1 for record in state["deliveries"].values() if isinstance(record, dict) and record.get("recipient_digest") == recipient_digest and float(record.get("created_epoch") or 0) >= now - self.rate_window_seconds)

    # Prune expired terminal delivery and suppression metadata without touching active work.
    def _prune_state(self, state: dict, now: float) -> None:
        # Select only terminal delivery keys older than the configured retention period.
        expired_deliveries = [key for key, record in state["deliveries"].items() if isinstance(record, dict) and record.get("status") in TERMINAL_STATUSES and float(record.get("updated_epoch") or 0) < now - self.retention_seconds]
        # Remove each expired delivery record inside the current atomic transaction.
        for key in expired_deliveries:
            # Delete the opaque-keyed record after its policy lifetime.
            del state["deliveries"][key]
        # Select only suppression records older than the same bounded retention period.
        expired_suppressions = [key for key, record in state["suppressions"].items() if isinstance(record, dict) and float(record.get("created_at") or 0) < now - self.retention_seconds]
        # Remove each expired suppression record.
        for key in expired_suppressions:
            # Delete the keyed suppression metadata after retention.
            del state["suppressions"][key]

    # Finalize a claimed transport attempt through another atomic state transition.
    def _finalize(self, idempotency_digest: str, delivery_id: str, result: str, now: float) -> dict:
        # Capture the finalized record for the current process.
        outcome = {"record": None}

        # Mutate only the exact sending claim owned by this delivery identifier.
        def finish(current: object) -> dict:
            # Refuse to normalize malformed durable state.
            state = _validate_state(current)
            # Resolve the claimed record through its keyed caller lookup.
            record = state["deliveries"].get(idempotency_digest)
            # Reject a stale or mismatched finalizer rather than overwrite newer state.
            if not isinstance(record, dict) or record.get("delivery_id") != delivery_id or record.get("status") != "sending":
                # Preserve the current record for a safe replay response when it exists.
                if isinstance(record, dict):
                    # Return the existing record to the outer caller.
                    outcome["record"] = dict(record)
                    # Leave durable state unchanged.
                    return state
                # Fail closed when the claim disappeared.
                raise ConflictError("mail delivery claim is no longer active", {"reason": "claim_lost"})
            # Mark a successful transport result terminal.
            if result == "sent":
                # Persist the sent state.
                record["status"] = "sent"
                # Clear any previous fixed failure reason.
                record["reason"] = None
            # Freeze an ambiguous transport result against automatic retries.
            elif result == "uncertain":
                # Persist the operator-reconciliation state.
                record["status"] = "uncertain"
                # Store only the fixed ambiguity reason.
                record["reason"] = "provider_result_unknown"
            # Schedule a known-safe retry while attempts remain.
            elif result == "retryable" and int(record.get("attempts", 0)) < self.max_attempts:
                # Persist the retry-wait state.
                record["status"] = "retry_wait"
                # Store only a fixed safe transient reason.
                record["reason"] = "provider_temporarily_unavailable"
                # Apply bounded exponential backoff from the completed attempt count.
                record["next_retry_at"] = now + min(self.retry_base_seconds * (2 ** max(0, int(record.get("attempts", 1)) - 1)), 86400)
            # Mark exhausted retries or permanent rejection failed.
            else:
                # Persist the terminal failure state.
                record["status"] = "failed"
                # Store only a fixed allowlisted reason.
                record["reason"] = "retry_exhausted" if result == "retryable" else result
            # Update the retention epoch after every final transition.
            record["updated_epoch"] = now
            # Store a readable application time without provider content.
            record["updated_at"] = utc_now()
            # Copy the record for the outer receipt builder.
            outcome["record"] = dict(record)
            # Return the mutated state for atomic persistence.
            return state

        # Persist the completion through the configured provider transaction.
        update_json(self.state_path, finish, default_state)
        # Return the finalized persistence-safe record.
        return outcome["record"]

    # Build the stable public receipt without recipient, token, URL, digests, or provider details.
    def _receipt(self, record: dict) -> dict:
        # Return only fields required for caller correlation and bounded retry behavior.
        return {
            "delivery_id": record["delivery_id"],
            "purpose": record["purpose"],
            "status": record["status"],
            "attempts": int(record.get("attempts", 0)),
            "next_retry_at": record.get("next_retry_at"),
        }


# Build the process service from disabled-by-default repository configuration.
def configured_service() -> MailService:
    # Return a fresh lightweight service so tests may adjust isolated environment-loaded config modules.
    return MailService(
        enabled=config.MAIL_ENABLED,
        network_enabled=config.MAIL_NETWORK_ENABLED,
        provider=config.MAIL_PROVIDER,
        digest_key=config.MAIL_DIGEST_KEY,
        canonical_origin=config.MAIL_CANONICAL_ORIGIN,
        from_address=config.MAIL_FROM_ADDRESS,
        sending_domain=config.MAIL_SENDING_DOMAIN,
        provider_token=config.MAIL_POSTMARK_SERVER_TOKEN,
        max_attempts=config.MAIL_MAX_ATTEMPTS,
        retry_base_seconds=config.MAIL_RETRY_BASE_SECONDS,
        rate_limit=config.MAIL_RATE_LIMIT,
        rate_window_seconds=config.MAIL_RATE_WINDOW_SECONDS,
        retention_seconds=config.MAIL_RETENTION_SECONDS,
    )


# Register the Admin-only v2 readiness endpoint without exposing a consumer send route.
def register(router) -> None:
    # Register diagnostics under the adapter-enforced Admin namespace.
    @router.get(r"/api/v2/admin/mail/readiness")
    # Return the secret-free readiness document through the standard response envelope.
    def mail_readiness(body, query, context):
        # Build current process diagnostics without any provider request.
        return configured_service().readiness()
