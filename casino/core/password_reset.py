"""Disabled enumeration-safe password recovery for canonical local accounts. (#334)

The service composes the purpose-bound one-time-token foundation (#331) and the transactional-mail
foundation (#330). It never emails a password, never discloses whether an account exists, and never
weakens provider links or invitation rules. Recovery is disabled by default and every rejection
returns one generic result so initiation cannot be used as an account oracle.
"""

# Import hashes for domain-separated privacy digests used only in audit events.
import hashlib
# Import constant-time comparison for keyed digest handling.
import hmac
# Import dependency types for deterministic service tests.
from typing import Callable

# Import disabled-by-default recovery policy and shared configuration.
from casino import config
# Import the canonical local identity and credential boundary.
from casino.core import auth
# Import the privacy-safe application audit facade.
from casino.core import logger
# Import the approved provider-neutral mail foundation.
from casino.core import mail
# Import the purpose-bound token foundation.
from casino.core import one_time_tokens
# Import the shared production clock.
from casino.core.clock import utc_now
# Import standard bounded application errors.
from casino.errors import ValidationError

# Bind every recovery bearer to the fixed token-platform purpose.
PURPOSE = "password_reset"
# Return one identical acknowledgement for every initiation so existence is never disclosed.
GENERIC_ACCEPTED = {"status": "accepted"}
# Return one identical public error for every completion rejection.
GENERIC_FAILURE_DETAILS = {"reason": "reset_unavailable"}
# Restrict audit fields so no credential, bearer, or raw recipient can be logged.
AUDIT_FIELDS = frozenset({"audit_id", "outcome", "recipient_digest", "reason", "token_id", "user_id"})


# Own the recovery state machine over the token and mail foundations.
class PasswordResetService:
    # Initialize the disabled service without registering routes or starting background work.
    def __init__(self, *, enabled: bool = False, digest_key: str = "", token_service=None, mail_service=None, clock: Callable[[], str] = utc_now, audit_sink: Callable[..., None] = logger.info) -> None:
        # Retain the recovery release gate independently from mail and enrollment gates.
        self.enabled = bool(enabled)
        # Retain audit digest material in process memory only.
        self.digest_key = str(digest_key or "")
        # Use the production token facade unless an isolated test supplied a service.
        self.token_service = token_service or one_time_tokens
        # Resolve the configured mail service lazily so a disabled deployment stays inert.
        self._mail_service = mail_service
        # Retain the repository-compatible timestamp source.
        self.clock = clock
        # Retain the privacy-safe audit sink.
        self.audit_sink = audit_sink

    # Resolve the mail service only when a delivery is actually attempted.
    @property
    def mail_service(self):
        # Return the injected service or the configured provider-neutral one.
        return self._mail_service if self._mail_service is not None else mail.configured_service()

    # Compute one domain-separated keyed digest so audits never carry a raw mailbox.
    def _digest(self, value: str) -> str:
        # Reject absent digest material before any audit event is emitted.
        if len(self.digest_key.encode("utf-8")) < 32:
            # Raise a value-free configuration error that never includes the supplied key.
            raise RuntimeError("Password-reset digest configuration must contain at least 32 bytes")
        # Return the HMAC-SHA256 verifier of the normalized mailbox.
        return hmac.new(self.digest_key.encode("utf-8"), f"password_reset\0{value}".encode("utf-8"), hashlib.sha256).hexdigest()

    # Bind token-consumption recovery to the exact mailbox, bearer, replacement, and caller request.
    def _completion_replay_key(self, normalized: str, token: str, new_password: str, idempotency_key: str) -> str:
        # Derive a stable non-reversible replay key without persisting any raw completion input.
        return self._digest(f"complete\0{normalized}\0{token}\0{new_password}\0{idempotency_key}")

    # Emit one bounded audit event after filtering caller-supplied field names.
    def _audit(self, event: str, **fields) -> None:
        # Retain only explicitly approved non-secret audit keys.
        self.audit_sink(event, **{key: value for key, value in fields.items() if key in AUDIT_FIELDS})

    # Raise the single generic completion failure without disclosing which check failed.
    def _reject(self, reason: str):
        # Record the internal reason for operators without exposing it to the caller.
        self._audit("password_reset_rejected", reason=reason)
        # Raise one uniform public error for every rejection path.
        raise ValidationError("password reset is unavailable", dict(GENERIC_FAILURE_DETAILS))

    # Resolve one recoverable local account without ever revealing existence to the caller.
    def _recoverable_user(self, email: str):
        # Look up the canonical identity by normalized mailbox.
        user = auth.find_user_by_email(email)
        # Treat a missing account as non-recoverable.
        if not user:
            # Signal no recoverable account.
            return None
        # Treat a disabled or ended account as non-recoverable.
        if user.get("status") != "active":
            # Signal no recoverable account.
            return None
        # Treat a social-only or credential-free account as non-recoverable because there is no password to reset.
        if not str(user.get("password_hash") or ""):
            # Signal no recoverable account.
            return None
        # Return the recoverable canonical account.
        return user

    # Begin recovery for a mailbox, always returning one identical acknowledgement.
    def initiate(self, email: str, *, locale: str = "en-US", idempotency_key: str = "") -> dict:
        # Normalize the transient mailbox once without persisting it.
        normalized = auth.normalize_email(str(email or ""))
        # Treat malformed input exactly like a non-existent account so probing learns nothing.
        if not normalized or normalized.count("@") != 1 or len(normalized) > 254:
            # Return the identical acknowledgement without sending anything.
            return dict(GENERIC_ACCEPTED)
        # Compute the audit digest for a privacy-safe event.
        recipient_digest = self._digest(normalized)
        # Refuse to deliver while recovery is disabled, still returning the identical acknowledgement.
        if not self.enabled:
            # Record the gated attempt without disclosing anything to the caller.
            self._audit("password_reset_initiated", recipient_digest=recipient_digest, outcome="disabled")
            # Return the identical acknowledgement.
            return dict(GENERIC_ACCEPTED)
        # Resolve whether the mailbox maps to a recoverable local account.
        user = self._recoverable_user(normalized)
        # Return the identical acknowledgement when nothing is recoverable, sending no mail.
        if not user:
            # Record the non-recoverable attempt without revealing it to the caller.
            self._audit("password_reset_initiated", recipient_digest=recipient_digest, outcome="no_recoverable_account")
            # Return the identical acknowledgement.
            return dict(GENERIC_ACCEPTED)
        # Reissue so at most one recovery bearer is ever valid; per-recipient send throttling is enforced by the
        # mail foundation, which bounds deliveries across every purpose and rejects a flooded recipient below.

        issued = self.token_service.reissue(PURPOSE, normalized)
        # Start protected delivery so a mail failure never leaks account existence to the caller.
        try:
            # Deliver the canonical-origin recovery link through the approved mail foundation.
            self.mail_service.submit(PURPOSE, normalized, token=issued["token"], idempotency_key=str(idempotency_key or issued["token_id"]), locale=locale if locale in ("en-US", "ru-RU") else "en-US")
            # Record a successful delivery submission without the bearer or mailbox.
            self._audit("password_reset_initiated", recipient_digest=recipient_digest, token_id=issued["token_id"], outcome="delivered")
        # Convert every delivery failure into the same silent acknowledgement.
        except Exception:
            # Revoke the freshly issued bearer so an undelivered token cannot linger.
            self.token_service.revoke(issued["token_id"])
            # Record the delivery failure for operators only.
            self._audit("password_reset_initiated", recipient_digest=recipient_digest, outcome="delivery_failed")
        # Return the identical acknowledgement regardless of internal outcome.
        return dict(GENERIC_ACCEPTED)

    # Complete recovery by consuming the bearer and replacing the stored credential.
    def complete(self, token: str, email: str, new_password: str, *, idempotency_key: str = "") -> dict:
        # Refuse every completion while recovery is disabled.
        if not self.enabled:
            # Fail closed with the single generic error.
            self._reject("disabled")
        # Normalize the transient mailbox once.
        normalized = auth.normalize_email(str(email or ""))
        # Reject a missing bearer or mailbox before any credential work.
        if not token or not normalized:
            # Fail closed with the single generic error.
            self._reject("malformed")
        # Enforce the shared password policy before the bearer is spent so a weak password cannot burn a token.
        try:
            # Apply the canonical enrollment password rules.
            auth.validate_enrollment_password(str(new_password or ""))
        # Convert a policy violation into the single generic error.
        except Exception:
            # Fail closed without disclosing which rule failed.
            self._reject("weak_password")
        # Consume the purpose-bound bearer atomically; every abuse path raises.
        try:
            # Require the bearer to match this mailbox, this purpose, and remain unconsumed.
            consumed = self.token_service.consume(PURPOSE, token, subject=normalized, idempotency_key=self._completion_replay_key(normalized, str(token), str(new_password), str(idempotency_key or "")), include_replay_state=True)
        # Convert expiry, replay, revocation, tampering, and subject mismatch into one generic error.
        except Exception:
            # Fail closed without revealing which condition rejected the bearer.
            self._reject("invalid_token")
        # Resolve the recoverable account only after the bearer is successfully consumed.
        user = self._recoverable_user(normalized)
        # Fail closed when the account became inactive or credential-free between initiation and completion.
        if not user:
            # Fail closed with the single generic error.
            self._reject("no_recoverable_account")
        # Return the original minimal success when an exact retry follows an already committed credential write.
        if consumed.get("replayed") is True and auth.verify_password(str(new_password), str(user.get("password_hash") or "")):
            # Record only opaque replay completion metadata without rotating credentials or sessions again.
            self._audit("password_reset_completed", recipient_digest=self._digest(normalized), token_id=consumed.get("token_id"), user_id=user["user_id"], outcome="replayed")
            # Return the same minimal success as the first committed completion.
            return {"status": "reset"}
        # Replace the stored credential through the canonical identity boundary.
        auth.set_user_password(user["user_id"], str(new_password), require_reset=False)
        # Record the successful recovery without the bearer, mailbox, or credential.
        self._audit("password_reset_completed", recipient_digest=self._digest(normalized), token_id=consumed.get("token_id"), user_id=user["user_id"], outcome="completed")
        # Return a generic success that carries no credential or bearer material.
        return {"status": "reset"}


# Hold the lazily constructed default service for production callers.
_DEFAULT_SERVICE = None


# Resolve the configured process-wide recovery service.
def configured_service() -> PasswordResetService:
    # Reuse the process-wide service once constructed.
    global _DEFAULT_SERVICE
    # Build the service from configuration on first use.
    if _DEFAULT_SERVICE is None:
        # Construct with the deployment's recovery gate and audit digest material.
        _DEFAULT_SERVICE = PasswordResetService(enabled=config.PASSWORD_RESET_ENABLED, digest_key=config.MAIL_DIGEST_KEY)
    # Return the shared service.
    return _DEFAULT_SERVICE


# Begin recovery through the configured service.
def initiate(email: str, *, locale: str = "en-US", idempotency_key: str = "") -> dict:
    # Delegate to the configured service.
    return configured_service().initiate(email, locale=locale, idempotency_key=idempotency_key)


# Complete recovery through the configured service.
def complete(token: str, email: str, new_password: str, *, idempotency_key: str = "") -> dict:
    # Delegate to the configured service.
    return configured_service().complete(token, email, new_password, idempotency_key=idempotency_key)
