"""Disabled optional passwordless magic-link login over the token and mail foundations. (#337)

This service composes the purpose-bound one-time-token platform (#331) and the transactional-mail
foundation (#330) into a passwordless login method, mirroring the disabled password-recovery service
(#334). It is a P3 roadmap item, disabled by default, and enabling it in production is a separate
owner-approved release step; this module only provides the inert implementation.

A magic-link bearer is bound to the fixed "magic_link" token purpose, so the platform's purpose binding
prevents it from ever being accepted as an invitation, verification, password-reset, or OAuth token, and
vice versa. Initiation is enumeration-safe: every mailbox receives one identical acknowledgement and a
link is delivered only for a recoverable local account. Completion consumes the bearer atomically and
creates a session; expiry, replay, revocation, tampering, and wrong-subject binding all fail closed with
one generic error. No raw token, mailbox, or credential is ever logged.
"""

# Import hashes for the domain-separated privacy digest used only in audit events.
import hashlib
# Import constant-time keyed digest handling.
import hmac
# Import dependency typing for deterministic service tests.
from typing import Callable

# Import the disabled-by-default magic-link release flag and shared configuration.
from casino import config
# Import the canonical local identity, session, and lookup boundary.
from casino.core import auth
# Import the privacy-safe application audit facade.
from casino.core import logger
# Import the approved provider-neutral mail foundation.
from casino.core import mail
# Import the purpose-bound one-time-token foundation.
from casino.core import one_time_tokens
# Import the shared production clock.
from casino.core.clock import utc_now
# Import the standard bounded application error.
from casino.errors import ValidationError

# Bind every magic-link bearer to the fixed, reserved token-platform purpose.
PURPOSE = "magic_link"
# Return one identical acknowledgement for every initiation so account existence is never disclosed.
GENERIC_ACCEPTED = {"status": "accepted"}
# Return one identical public error for every completion rejection.
GENERIC_FAILURE_DETAILS = {"reason": "login_link_unavailable"}
# Restrict audit fields so no bearer, credential, or raw mailbox can ever be logged.
AUDIT_FIELDS = frozenset({"audit_id", "outcome", "recipient_digest", "reason", "session_id", "token_id", "user_id"})


# Own the passwordless-login state machine over the token and mail foundations.
class MagicLinkService:
    # Initialize the disabled service without registering routes or starting background work.
    def __init__(self, *, enabled: bool = False, digest_key: str = "", token_service=None, mail_service=None, session_factory: Callable[..., dict] | None = None, clock: Callable[[], str] = utc_now, audit_sink: Callable[..., None] = logger.info) -> None:
        # Retain the independent magic-link release gate.
        self.enabled = bool(enabled)
        # Retain audit digest material in process memory only.
        self.digest_key = str(digest_key or "")
        # Use the production token facade unless an isolated test supplied a service.
        self.token_service = token_service or one_time_tokens
        # Resolve the configured mail service lazily so a disabled deployment stays inert.
        self._mail_service = mail_service
        # Use the canonical session factory unless an isolated test supplied one.
        self.session_factory = session_factory or auth.create_session
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
            raise RuntimeError("Magic-link digest configuration must contain at least 32 bytes")
        # Return the HMAC-SHA256 verifier of the normalized mailbox under a distinct domain tag.
        return hmac.new(self.digest_key.encode("utf-8"), f"magic_link\0{value}".encode("utf-8"), hashlib.sha256).hexdigest()

    # Emit one bounded audit event after filtering caller-supplied field names.
    def _audit(self, event: str, **fields) -> None:
        # Retain only explicitly approved non-secret audit keys.
        self.audit_sink(event, **{key: value for key, value in fields.items() if key in AUDIT_FIELDS})

    # Raise the single generic completion failure without disclosing which check failed.
    def _reject(self, reason: str):
        # Record the internal reason for operators without exposing it to the caller.
        self._audit("magic_link_rejected", reason=reason)
        # Raise one uniform public error for every rejection path.
        raise ValidationError("login link is unavailable", dict(GENERIC_FAILURE_DETAILS))

    # Resolve one login-eligible local account without ever revealing existence to the caller.
    def _eligible_user(self, email: str):
        # Look up the canonical identity by normalized mailbox.
        user = auth.find_user_by_email(email)
        # Treat a missing account as ineligible.
        if not user:
            # Signal no eligible account.
            return None
        # Treat a disabled or ended account as ineligible so an inactive mailbox cannot be logged in.
        if user.get("status") != "active":
            # Signal no eligible account.
            return None
        # Treat social-only or credential-free identities as ineligible for a local-account login link.
        if str(user.get("identity_provider") or "local").lower() != "local" or not str(user.get("password_hash") or ""):
            # Signal no eligible local account.
            return None
        # Return the login-eligible canonical account.
        return user

    # Begin a passwordless login for a mailbox, always returning one identical acknowledgement.
    def initiate(self, email: str, *, locale: str = "en-US", idempotency_key: str = "") -> dict:
        # Normalize the transient mailbox once without persisting it.
        normalized = auth.normalize_email(str(email or ""))
        # Treat malformed input exactly like a non-existent account so probing learns nothing.
        if not normalized or normalized.count("@") != 1 or len(normalized) > 254:
            # Return the identical acknowledgement without sending anything.
            return dict(GENERIC_ACCEPTED)
        # Compute the audit digest for a privacy-safe event.
        recipient_digest = self._digest(normalized)
        # Refuse to deliver while magic-link login is disabled, still returning the identical acknowledgement.
        if not self.enabled:
            # Record the gated attempt without disclosing anything to the caller.
            self._audit("magic_link_initiated", recipient_digest=recipient_digest, outcome="disabled")
            # Return the identical acknowledgement.
            return dict(GENERIC_ACCEPTED)
        # Resolve whether the mailbox maps to a login-eligible local account.
        user = self._eligible_user(normalized)
        # Return the identical acknowledgement when nothing is eligible, sending no mail.
        if not user:
            # Record the ineligible attempt without revealing it to the caller.
            self._audit("magic_link_initiated", recipient_digest=recipient_digest, outcome="no_eligible_account")
            # Return the identical acknowledgement.
            return dict(GENERIC_ACCEPTED)
        # Reissue so at most one login bearer is ever valid; per-recipient send throttling stays in the mail foundation.
        issued = self.token_service.reissue(PURPOSE, normalized)
        # Start protected delivery so a mail failure never leaks account existence to the caller.
        try:
            # Deliver the canonical-origin login link through the approved mail foundation.
            self.mail_service.submit(PURPOSE, normalized, token=issued["token"], idempotency_key=str(idempotency_key or issued["token_id"]), locale=locale if locale in ("en-US", "ru-RU") else "en-US")
            # Record a successful delivery submission without the bearer or mailbox.
            self._audit("magic_link_initiated", recipient_digest=recipient_digest, token_id=issued["token_id"], outcome="delivered")
        # Convert every delivery failure into the same silent acknowledgement.
        except Exception:
            # Revoke the freshly issued bearer so an undelivered token cannot linger.
            self.token_service.revoke(issued["token_id"])
            # Record the delivery failure for operators only.
            self._audit("magic_link_initiated", recipient_digest=recipient_digest, outcome="delivery_failed")
        # Return the identical acknowledgement regardless of internal outcome.
        return dict(GENERIC_ACCEPTED)

    # Complete a passwordless login by consuming the bearer and creating a session.
    def complete(self, token: str, email: str, *, client: str = "", idempotency_key: str = "") -> dict:
        # Refuse every completion while magic-link login is disabled.
        if not self.enabled:
            # Fail closed with the single generic error.
            self._reject("disabled")
        # Normalize the transient mailbox once.
        normalized = auth.normalize_email(str(email or ""))
        # Reject a missing bearer or mailbox before any session work.
        if not token or not normalized:
            # Fail closed with the single generic error.
            self._reject("malformed")
        # Consume the purpose-bound bearer atomically; every abuse path raises.
        try:
            # Require the bearer to match this mailbox, this purpose, and remain unconsumed.
            consumed = self.token_service.consume(PURPOSE, token, subject=normalized, idempotency_key=str(idempotency_key or ""))
        # Convert expiry, replay, revocation, tampering, and subject mismatch into one generic error.
        except Exception:
            # Fail closed without revealing which condition rejected the bearer.
            self._reject("invalid_token")
        # Resolve the login-eligible account only after the bearer is successfully consumed.
        user = self._eligible_user(normalized)
        # Fail closed when the account became inactive between initiation and completion.
        if not user:
            # Fail closed with the single generic error.
            self._reject("no_eligible_account")
        # Create a session for the local account; the account is local so the session records the local method.
        session = self.session_factory(user, client=str(client or ""), auth_method="local")
        # Record the successful passwordless login with the magic-link provenance in the audit trail only.
        self._audit("magic_link_completed", recipient_digest=self._digest(normalized), token_id=consumed.get("token_id"), user_id=user["user_id"], session_id=session.get("session_id"), outcome="logged_in")
        # Return only the session material the caller needs to establish the browser session.
        return {"status": "logged_in", "session": {"token": session.get("token"), "csrf_token": session.get("csrf_token"), "expires_at": session.get("expires_at")}}


# Hold the lazily constructed default service for production callers.
_DEFAULT_SERVICE = None


# Resolve the configured process-wide magic-link service.
def configured_service() -> MagicLinkService:
    # Reuse the process-wide service once constructed.
    global _DEFAULT_SERVICE
    # Build the service from configuration on first use.
    if _DEFAULT_SERVICE is None:
        # Construct with the deployment's magic-link gate and audit digest material.
        _DEFAULT_SERVICE = MagicLinkService(enabled=config.MAGIC_LINK_ENABLED, digest_key=config.MAIL_DIGEST_KEY)
    # Return the shared service.
    return _DEFAULT_SERVICE


# Begin a passwordless login through the configured service.
def initiate(email: str, *, locale: str = "en-US", idempotency_key: str = "") -> dict:
    # Delegate to the configured service.
    return configured_service().initiate(email, locale=locale, idempotency_key=idempotency_key)


# Complete a passwordless login through the configured service.
def complete(token: str, email: str, *, client: str = "", idempotency_key: str = "") -> dict:
    # Delegate to the configured service.
    return configured_service().complete(token, email, client=client, idempotency_key=idempotency_key)
