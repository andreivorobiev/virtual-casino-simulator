"""Disabled private invitation enrollment with recoverable lifecycle semantics. (INVITE-001..006)

The service composes the one-time-token and transactional-mail foundations without exposing a send
route, bearer, raw recipient, or live release action. Issuance and redemption remain independently
disabled by default. Redemption uses an account-free identity reservation plus caller-idempotent
token consumption so a process stop can resume without a burned token or active orphan account.
"""

# Import hashes for domain-separated privacy and idempotency digests.
import hashlib
# Import constant-time digest comparison for durable caller replay keys.
import hmac
# Import timestamp arithmetic for expiry, cooldown, rate, and retention policy.
from datetime import datetime, timedelta
# Import portable paths for isolated provider-backed tests.
from pathlib import Path
# Import dependency types for deterministic service tests.
from typing import Any, Callable

# Import disabled-by-default invitation policy and the shared data root.
from casino import config
# Import the canonical local identity provisioning boundary.
from casino.core import auth
# Import the privacy-safe application audit facade.
from casino.core import logger
# Import the approved provider-neutral mail foundation.
from casino.core import mail
# Import the purpose-bound token foundation.
from casino.core import one_time_tokens
# Import the shared production clock.
from casino.core.clock import utc_now
# Import opaque identifiers for invitation, audit, user, and player state.
from casino.core.ids import new_id
# Import provider-aware JSON/MySQL document transactions.
from casino.core.state_store import read_json, update_json
# Import standard bounded application errors.
from casino.errors import CasinoError, ConflictError, ForbiddenError, RateLimitError, ValidationError

# Store invitation state under the governed authentication namespace.
INVITATIONS_PATH = config.DATA_DIR / "auth" / "invitations.json"
# Bind every bearer to the fixed token-platform purpose.
PURPOSE = "invitation"
# Enumerate public lifecycle values without exposing internal recovery phases.
PUBLIC_STATUSES = frozenset({"delivery_failed", "expired", "pending", "redeeming", "redeemed", "revoked"})
# Enumerate accepted locales shared by Admin, mail, and public redemption surfaces.
LOCALES = frozenset({"en-US", "ru-RU"})
# Return one public error for every unauthenticated redemption rejection.
GENERIC_REDEMPTION_DETAILS = {"reason": "invitation_unavailable"}


# Build the canonical empty invitation document.
def default_invitations() -> dict:
    # Return a fresh schema-stamped collection for JSON and MySQL providers.
    return {"schema_version": config.SCHEMA_VERSION, "invitations": []}


# Own one isolated invitation state machine plus injectable foundations.
class InvitationService:
    # Initialize the disabled service without registering routes or starting background work.
    def __init__(self, *, store_path: Path = INVITATIONS_PATH, enabled: bool = False, enrollment_enabled: bool = False, digest_key: str = "", token_service=None, mail_service=None, clock: Callable[[], str] = utc_now, id_factory: Callable[[str], str] = new_id, audit_sink: Callable[..., None] = logger.info) -> None:
        # Persist the exact provider-backed invitation document path.
        self.store_path = Path(store_path)
        # Retain the Admin issuance feature gate independently from mail/network release.
        self.enabled = bool(enabled)
        # Retain the public redemption gate independently from issuance.
        self.enrollment_enabled = bool(enrollment_enabled)
        # Retain recipient/audit digest material in process memory only.
        self.digest_key = str(digest_key or "")
        # Use the production token facade unless an isolated test supplied a service.
        self.token_service = token_service or one_time_tokens
        # Use the configured mail service unless an isolated test supplied one.
        self.mail_service = mail_service or mail.configured_service()
        # Retain the repository-compatible timestamp source.
        self.clock = clock
        # Retain opaque identifier generation for deterministic tests.
        self.id_factory = id_factory
        # Retain the privacy-safe audit sink without accepting caller-defined field names.
        self.audit_sink = audit_sink
        # Reject unsafe or unbounded invitation policy before any durable mutation.
        if config.INVITATION_RESEND_COOLDOWN_SECONDS < 1 or config.INVITATION_ADMIN_RATE_LIMIT < 1 or config.INVITATION_RECIPIENT_RATE_LIMIT < 1 or config.INVITATION_RATE_WINDOW_SECONDS < 60 or config.INVITATION_RETENTION_SECONDS < 86400 or config.INVITATION_CLAIM_TIMEOUT_SECONDS < 60:
            # Raise a value-free startup diagnostic naming no supplied configuration.
            raise RuntimeError("Invitation policy configuration must use positive bounded values")

    # Parse one repository timestamp into an aware datetime.
    @staticmethod
    def _parse(value: str) -> datetime:
        # Convert the shared Z suffix into the offset form accepted by the standard parser.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    # Normalize one invited mailbox without publishing it.
    @staticmethod
    def _email(value: str) -> str:
        # Return the canonical lower-cased mailbox used by token and account bindings.
        return auth.normalize_email(str(value or ""))

    # Validate one mailbox conservatively without echoing it in errors.
    @classmethod
    def _validate_email(cls, value: str) -> str:
        # Normalize the transient mailbox once.
        normalized = cls._email(value)
        # Reject empty, control-character, overlong, and structurally implausible values.
        if not normalized or len(normalized) > 254 or normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@") or any(character in normalized for character in "\r\n"):
            # Keep the error free of the supplied recipient.
            raise ValidationError("invitation recipient is invalid", {"reason": "invalid_recipient"})
        # Return the validated transient mailbox.
        return normalized

    # Validate one caller idempotency key without persisting it.
    @staticmethod
    def _idempotency(value: str) -> str:
        # Normalize the transient key once.
        normalized = str(value or "").strip()
        # Require enough entropy and a bounded transport-safe length.
        if len(normalized) < 16 or len(normalized) > 200 or any(character in normalized for character in "\r\n"):
            # Reject malformed caller replay metadata without echoing it.
            raise ValidationError("invitation idempotency key is invalid", {"reason": "invalid_idempotency"})
        # Return the validated caller key for transient downstream use.
        return normalized

    # Validate one Admin actor identifier.
    @staticmethod
    def _actor(value: str) -> str:
        # Normalize the authenticated opaque identity from request context.
        normalized = str(value or "").strip()
        # Require an authenticated actor and a bounded identifier.
        if not normalized or len(normalized) > 160 or any(character in normalized for character in "\r\n"):
            # Fail before any invitation mutation.
            raise ForbiddenError("Admin invitation actor is unavailable")
        # Return the internal opaque actor identifier.
        return normalized

    # Compute one domain-separated keyed digest.
    def _digest(self, domain: str, value: str) -> str:
        # Reject absent, weak, or committed developer digest material before mutation.
        if len(self.digest_key.encode("utf-8")) < 32 or self.digest_key == config.LOCAL_MAIL_DIGEST_KEY:
            # Preserve a value-free readiness failure.
            raise ValidationError("invitation digest configuration is unavailable", {"reason": "digest_key_invalid"})
        # Prefix the input so equal values cannot substitute across recipient and idempotency fields.
        payload = f"{domain}\0{value}".encode("utf-8")
        # Return the HMAC-SHA256 verifier without exposing the external key.
        return hmac.new(self.digest_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Mask a mailbox for Admin display without exposing the stored recipient.
    @staticmethod
    def _mask(email: str) -> str:
        # Split the already validated transient mailbox into local and domain fragments.
        local, domain = email.split("@", 1)
        # Split the domain so its public suffix remains recognizable for operator disambiguation.
        domain_parts = domain.split(".")
        # Mask the domain label while preserving a bounded suffix.
        masked_domain = f"{domain_parts[0][:1]}***" + (f".{domain_parts[-1]}" if len(domain_parts) > 1 else "")
        # Return one leading local character plus fixed masking.
        return f"{local[:1]}***@{masked_domain}"

    # Validate durable invitation state without destructive normalization.
    @staticmethod
    def _state(value: Any) -> dict:
        # Reject a malformed root or collection while preserving it for operator recovery.
        if not isinstance(value, dict) or not isinstance(value.get("invitations"), list):
            # Abort the provider transaction with no replacement document.
            raise RuntimeError("Invitation storage requires operator recovery")
        # Reject malformed rows before any mutation can publish a partial repair.
        if any(not isinstance(row, dict) for row in value["invitations"]):
            # Preserve the original durable document.
            raise RuntimeError("Invitation storage requires operator recovery")
        # Return the validated mutable state.
        return value

    # Append one privacy-safe lifecycle event to an invitation row.
    def _event(self, row: dict, actor_id: str, reason: str, old_status: str | None, new_status: str) -> None:
        # Build one bounded event containing only opaque actor and lifecycle metadata.
        event = {"audit_id": self.id_factory("inviteaudit"), "actor_id": actor_id, "reason": reason, "old_status": old_status, "new_status": new_status, "at": self.clock()}
        # Append the event to the bounded per-invitation history.
        row.setdefault("history", []).append(event)
        # Retain only the newest fifty fixed-shape events.
        row["history"] = row["history"][-50:]
        # Refresh the invitation update timestamp from the same captured event instant.
        row["updated_at"] = event["at"]

    # Report one public status, deriving expiry without mutating the stored row.
    def _status(self, row: dict) -> str:
        # Treat pending delivery as expired once its absolute token lifetime elapsed.
        if row.get("status") == "pending":
            # Start protected parsing so malformed expiry fails closed to a recovery state.
            try:
                # Publish expired only when the complete validity window elapsed.
                if self._parse(str(row.get("expires_at", ""))) < self._parse(self.clock()):
                    # Return the terminal display state without deleting the row.
                    return "expired"
            # Preserve malformed security state as delivery failure for operator attention.
            except (TypeError, ValueError):
                # Avoid classifying malformed expiry as redeemable.
                return "delivery_failed"
        # Collapse internal issuance phases into the pending Admin lifecycle.
        if row.get("status") in {"reserved", "issuing", "delivery_pending"}:
            # Present a stable pending state while the recoverable delivery saga is incomplete.
            return "pending"
        # Return a recognized public state or a safe recovery-required fallback.
        return row.get("status") if row.get("status") in PUBLIC_STATUSES else "delivery_failed"

    # Project one invitation into a raw-recipient-free Admin view.
    def _public(self, row: dict) -> dict:
        # Return only bounded lifecycle and masked-recipient metadata.
        return {
            "invitation_id": row.get("invitation_id"),
            "recipient_hint": row.get("recipient_hint"),
            "status": self._status(row),
            "delivery_status": row.get("delivery_status"),
            "locale": row.get("locale"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "expires_at": row.get("expires_at"),
            "redeemed_at": row.get("redeemed_at"),
            "revoked_at": row.get("revoked_at"),
            "invited_by": row.get("invited_by"),
            "history": [dict(event) for event in row.get("history", [])[-20:]],
        }

    # Require both invitation issuance and the existing mail foundation to be independently ready.
    def _require_issuance_ready(self) -> None:
        # Fail closed while the repository invitation feature remains disabled.
        if not self.enabled:
            # Keep Admin diagnostics distinct from public redemption errors.
            raise ForbiddenError("Invitation issuance is disabled")
        # Read only the secret-free mail readiness document.
        readiness = self.mail_service.readiness()
        # Require the separately released mail/network state before minting a deliverable token.
        if readiness.get("status") != "ready":
            # Avoid creating an invitation whose bearer cannot reach the recipient.
            raise ForbiddenError("Invitation delivery is not ready")

    # Enforce fixed actor and recipient rate windows under the invitation document lock.
    def _enforce_rates(self, state: dict, actor_id: str, recipient_digest: str, now: str) -> None:
        # Compute the inclusive start of the configured rate window.
        window_start = self._parse(now) - timedelta(seconds=config.INVITATION_RATE_WINDOW_SECONDS)
        # Count recent invitations created by this authenticated Admin.
        actor_count = sum(1 for row in state["invitations"] if row.get("invited_by") == actor_id and self._safe_time(row.get("created_at")) >= window_start)
        # Reject Admin bursts beyond the configured bound.
        if actor_count >= config.INVITATION_ADMIN_RATE_LIMIT:
            # Return the standard bounded rate-limit category.
            raise RateLimitError("Admin invitation rate limit exceeded")
        # Count recent delivery generations for the keyed recipient.
        recipient_count = sum(int(row.get("delivery_generation") or 0) for row in state["invitations"] if row.get("recipient_digest") == recipient_digest and self._safe_time(row.get("created_at")) >= window_start)
        # Reject recipient flooding across create and resend operations.
        if recipient_count >= config.INVITATION_RECIPIENT_RATE_LIMIT:
            # Return the standard bounded rate-limit category.
            raise RateLimitError("Invitation recipient rate limit exceeded")

    # Parse one stored timestamp defensively for rate and retention comparisons.
    def _safe_time(self, value: str) -> datetime:
        # Start protected parsing so malformed rows are retained rather than removed.
        try:
            # Return the parsed repository timestamp.
            return self._parse(str(value or ""))
        # Map malformed values to the earliest comparable instant.
        except (TypeError, ValueError):
            # Preserve the row while excluding it from current-window counts.
            return datetime.min.replace(tzinfo=self._parse(self.clock()).tzinfo)

    # Find one invitation by opaque identifier from a validated document.
    @staticmethod
    def _find(state: dict, invitation_id: str) -> dict | None:
        # Return the matching row without exposing collection order.
        return next((row for row in state["invitations"] if row.get("invitation_id") == invitation_id), None)

    # Deliver or redeliver one invitation through a recoverable token/mail saga.
    def _deliver(self, invitation_id: str, actor_id: str, reason: str) -> dict:
        # Capture the row and recipient selected by the atomic generation transition.
        selected = {}
        # Advance one delivery generation before creating any external transient bearer.
        def begin(raw_state: Any) -> dict:
            # Validate the durable document without repairing it.
            state = self._state(raw_state)
            # Find the exact Admin-selected invitation.
            row = self._find(state, invitation_id)
            # Reject absent or terminal invitations without revealing recipient data.
            if row is None or row.get("status") not in {"reserved", "issuing", "delivery_failed", "pending"}:
                # Preserve terminal state and require an explicit new invitation when appropriate.
                raise ConflictError("Invitation cannot be delivered in its current state")
            # Reject a concurrent active issuance before another token generation can be allocated.
            if row.get("status") == "issuing" and (self._parse(self.clock()) - self._safe_time(row.get("updated_at"))).total_seconds() < config.INVITATION_CLAIM_TIMEOUT_SECONDS:
                # Require the exact caller to retry after the bounded pre-token recovery window.
                raise ConflictError("Invitation delivery is already in progress")
            # Enforce fixed actor and recipient windows for every delivery generation.
            self._enforce_rates(state, actor_id, str(row.get("recipient_digest") or ""), self.clock())
            # Increment the durable generation before issuing a replacement token.
            row["delivery_generation"] = int(row.get("delivery_generation") or 0) + 1
            # Transition to the recoverable issuing phase.
            prior = row.get("status")
            # Store the internal issuing state while no raw bearer exists durably.
            row["status"] = "issuing"
            # Clear only prior delivery identifiers; terminal history remains intact.
            row["delivery_status"] = None
            # Record the fixed Admin action reason.
            self._event(row, actor_id, reason, prior, "issuing")
            # Publish a detached internal copy for transient token and mail calls.
            selected.update(dict(row))
            # Return the complete invitation document.
            return state
        # Persist the generation boundary through JSON locking or MySQL row locking.
        update_json(self.store_path, begin, default_invitations)
        # Revoke any orphaned prior bearer and issue exactly one current generation token.
        issued = self.token_service.reissue(PURPOSE, selected["recipient"])
        # Persist the opaque token identity before attempting delivery.
        def token_ready(raw_state: Any) -> dict:
            # Validate current state before recording the issued generation.
            state = self._state(raw_state)
            # Resolve the invitation that owns this generation.
            row = self._find(state, invitation_id)
            # Reject a concurrent generation change without persisting an ambiguous bearer.
            if row is None or int(row.get("delivery_generation") or 0) != int(selected.get("delivery_generation") or 0) or row.get("status") != "issuing":
                # Keep the newer state authoritative.
                raise ConflictError("Invitation delivery generation changed")
            # Record only the opaque token identifier and absolute expiry.
            row["token_id"] = issued["token_id"]
            # Record the policy-derived expiry used by Admin and redemption checks.
            row["expires_at"] = issued["expires_at"]
            # Transition to delivery-pending before the provider boundary.
            row["status"] = "delivery_pending"
            # Refresh the update time without adding a second Admin action history row.
            row["updated_at"] = self.clock()
            # Return the complete document.
            return state
        # Start protected token-state publication so a failed generation cannot leave an active orphan bearer.
        try:
            # Commit the opaque token boundary before mail submission.
            update_json(self.store_path, token_ready, default_invitations)
        # Revoke the just-issued token when a concurrent lifecycle change rejects publication.
        except Exception:
            # Invalidate only this generation's opaque token identity.
            self.token_service.revoke(issued["token_id"])
            # Preserve the original bounded conflict or storage failure.
            raise
        # Build a stable generation key containing only opaque identifiers.
        mail_idempotency = f"{invitation_id}-{selected['delivery_generation']}-{issued['token_id']}"
        # Start protected delivery so known failures leave an explicit recoverable state.
        try:
            # Submit the transient bearer through the already-approved mail state machine.
            receipt = self.mail_service.submit(PURPOSE, selected["recipient"], token=issued["token"], idempotency_key=mail_idempotency, locale=selected["locale"])
        # Convert every bounded mail or persistence failure into a recoverable invitation state.
        except Exception:
            # Revoke the generation token so an undelivered bearer cannot remain active.
            self.token_service.revoke(issued["token_id"])
            # Mark this generation failed without deleting its audit trail.
            def delivery_failed(raw_state: Any) -> dict:
                # Validate the document before the failure transition.
                state = self._state(raw_state)
                # Resolve only the generation attempted by this process.
                row = self._find(state, invitation_id)
                # Apply failure only while the exact token remains current.
                if row is not None and row.get("token_id") == issued["token_id"]:
                    # Publish the operator-visible recoverable status.
                    row["status"] = "delivery_failed"
                    # Record a fixed low-cardinality delivery result.
                    row["delivery_status"] = "failed"
                    # Refresh the lifecycle timestamp.
                    row["updated_at"] = self.clock()
                # Return the complete document.
                return state
            # Persist the recoverable failure state.
            update_json(self.store_path, delivery_failed, default_invitations)
            # Re-raise the original bounded error to the Admin caller.
            raise
        # Persist the secret-free delivery receipt and pending invitation state.
        def delivered(raw_state: Any) -> dict:
            # Validate the document before finalizing delivery.
            state = self._state(raw_state)
            # Resolve only the current token generation.
            row = self._find(state, invitation_id)
            # Reject a concurrent replacement instead of overwriting newer state.
            if row is None or row.get("token_id") != issued["token_id"]:
                # Preserve the newer generation.
                raise ConflictError("Invitation delivery generation changed")
            # Store the opaque mail delivery identifier for operator correlation.
            row["mail_delivery_id"] = receipt.get("delivery_id")
            # Store only the fixed mail lifecycle state.
            row["delivery_status"] = receipt.get("status")
            # Accept only a completed provider submission as a redeemable pending invitation.
            row["status"] = "pending" if receipt.get("status") == "sent" else "delivery_failed"
            # Refresh the lifecycle timestamp.
            row["updated_at"] = self.clock()
            # Return the complete document.
            return state
        # Publish the final delivery outcome atomically.
        final_state = update_json(self.store_path, delivered, default_invitations)
        # Resolve the finalized row for the Admin receipt.
        final_row = self._find(self._state(final_state), invitation_id)
        # Emit only opaque identifiers and fixed lifecycle state.
        self.audit_sink("invitation_delivery_state", invitation_id=invitation_id, status=final_row.get("status"), delivery_id=final_row.get("mail_delivery_id"))
        # Return the privacy-safe Admin projection.
        return self._public(final_row)

    # Create one account-free invitation reservation and deliver its bearer.
    def create(self, recipient: str, actor_id: str, *, locale: str, idempotency_key: str) -> dict:
        # Require the independently released invitation and mail foundations.
        self._require_issuance_ready()
        # Validate transient caller values before durable mutation.
        normalized = self._validate_email(recipient)
        # Validate the authenticated actor from the Admin request context.
        actor = self._actor(actor_id)
        # Restrict translated invitation mail to the governed locales.
        if locale not in LOCALES:
            # Reject unsupported UI and mail content without echoing the value.
            raise ValidationError("invitation locale is invalid", {"reason": "invalid_locale"})
        # Validate and digest the caller replay key.
        caller_key = self._idempotency(idempotency_key)
        # Compute recipient and caller digests without storing their raw lookup keys.
        recipient_digest = self._digest("recipient", normalized)
        # Compute the caller replay verifier independently.
        idempotency_digest = self._digest("admin-idempotency", caller_key)
        # Capture either the new invitation or an exact idempotent replay.
        selected = {"replay": False}
        # Reserve one invitation row inside the provider transaction.
        def reserve(raw_state: Any) -> dict:
            # Validate the complete durable document.
            state = self._state(raw_state)
            # Return an exact same-meaning caller replay without creating another row.
            for row in state["invitations"]:
                # Compare only the stored idempotency verifier in constant time.
                if hmac.compare_digest(str(row.get("create_idempotency_digest", "")), idempotency_digest):
                    # Reject changed recipient or locale meaning on key reuse.
                    if row.get("recipient_digest") != recipient_digest or row.get("locale") != locale or row.get("invited_by") != actor:
                        # Preserve the original invitation unchanged.
                        raise ConflictError("Invitation idempotency key was reused with different inputs")
                    # Publish the matching row for safe replay or delivery recovery.
                    selected.update(dict(row))
                    # Mark that no new rate slot or row was created.
                    selected["replay"] = True
                    # Return state unchanged.
                    return state
            # Reject another active invitation for the same recipient so Admin must use resend.
            if any(row.get("recipient_digest") == recipient_digest and self._status(row) in {"pending", "redeeming"} for row in state["invitations"]):
                # Avoid minting multiple concurrently redeemable bearers.
                raise ConflictError("An active invitation already exists for this recipient")
            # Enforce actor and recipient policy before allocating identifiers.
            self._enforce_rates(state, actor, recipient_digest, self.clock())
            # Capture one creation instant for every initial field.
            now = self.clock()
            # Build the account-free invitation row; raw recipient remains private durable delivery data only.
            row = {"invitation_id": self.id_factory("invite"), "recipient": normalized, "recipient_digest": recipient_digest, "recipient_hint": self._mask(normalized), "status": "reserved", "delivery_status": None, "delivery_generation": 0, "token_id": None, "mail_delivery_id": None, "locale": locale, "invited_by": actor, "create_idempotency_digest": idempotency_digest, "created_at": now, "updated_at": now, "expires_at": None, "redeemed_at": None, "revoked_at": None, "redemption": None, "history": []}
            # Record the fixed creation transition with no caller-authored text.
            self._event(row, actor, "admin_invite", None, "reserved")
            # Append exactly one account-free invitation reservation.
            state["invitations"].append(row)
            # Publish a detached internal copy to the delivery step.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Persist the reservation through JSON locking or MySQL row locking.
        update_json(self.store_path, reserve, default_invitations)
        # Return an already finalized exact replay without delivering twice.
        if selected.get("replay") and selected.get("status") in {"pending", "redeemed", "revoked"}:
            # Return only the privacy-safe Admin projection.
            return self._public(selected)
        # Recover an incomplete create by revoking any orphan and delivering a new generation.
        return self._deliver(selected["invitation_id"], actor, "admin_invite")

    # Resend one pending or failed invitation through a fresh token generation.
    def resend(self, invitation_id: str, actor_id: str, *, idempotency_key: str) -> dict:
        # Require the independently released invitation and mail foundations.
        self._require_issuance_ready()
        # Validate the authenticated actor and caller replay key.
        actor = self._actor(actor_id)
        # Digest the action key without persisting its raw value.
        action_digest = self._digest("admin-idempotency", self._idempotency(idempotency_key))
        # Track the selected row after cooldown and idempotency checks.
        selected = {"replay": False}
        # Reserve the resend action atomically.
        def reserve(raw_state: Any) -> dict:
            # Validate the durable document before lookup.
            state = self._state(raw_state)
            # Resolve the opaque Admin-selected invitation.
            row = self._find(state, str(invitation_id or ""))
            # Reject absent or non-resendable lifecycle states.
            if row is None or row.get("status") not in {"pending", "delivery_failed"}:
                # Preserve terminal or in-progress state.
                raise ConflictError("Invitation cannot be resent in its current state")
            # Return an exact action replay without another delivery.
            if hmac.compare_digest(str(row.get("last_action_idempotency_digest", "")), action_digest):
                # Publish the same row for the caller.
                selected.update(dict(row))
                # Mark the action as a no-op replay.
                selected["replay"] = True
                # Leave durable state unchanged.
                return state
            # Enforce the cooldown from the last completed or attempted delivery.
            if (self._parse(self.clock()) - self._safe_time(row.get("updated_at"))).total_seconds() < config.INVITATION_RESEND_COOLDOWN_SECONDS:
                # Reject a recipient-flooding resend before token replacement.
                raise RateLimitError("Invitation resend cooldown is active")
            # Store only the digest of the accepted action key.
            row["last_action_idempotency_digest"] = action_digest
            # Publish a detached copy to the delivery step.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Persist the resend reservation.
        update_json(self.store_path, reserve, default_invitations)
        # Return the exact completed action replay without a second message.
        if selected.get("replay"):
            # Return only the safe Admin view.
            return self._public(selected)
        # Reissue and deliver a fresh bearer through the recoverable generation saga.
        return self._deliver(selected["invitation_id"], actor, "admin_resend")

    # Revoke one pending invitation before another redemption claim begins.
    def revoke(self, invitation_id: str, actor_id: str, *, idempotency_key: str) -> dict:
        # Validate the authenticated actor even when issuance is disabled for emergency revocation.
        actor = self._actor(actor_id)
        # Digest the caller key so repeated Admin clicks remain idempotent.
        action_digest = self._digest("admin-idempotency", self._idempotency(idempotency_key))
        # Publish the token identifier selected by the atomic lifecycle transition.
        selected = {}
        # Transition the invitation before revoking the token so redemption cannot claim it concurrently.
        def transition(raw_state: Any) -> dict:
            # Validate the complete durable state.
            state = self._state(raw_state)
            # Resolve the opaque Admin-selected invitation.
            row = self._find(state, str(invitation_id or ""))
            # Reject an absent invitation without exposing recipient state.
            if row is None:
                # Return a stable Admin conflict.
                raise ConflictError("Invitation cannot be revoked")
            # Return an exact prior revoke action idempotently.
            if row.get("status") == "revoked" and hmac.compare_digest(str(row.get("last_action_idempotency_digest", "")), action_digest):
                # Publish the terminal row for the safe receipt.
                selected.update(dict(row))
                # Leave durable state unchanged.
                return state
            # Revoke only a pending, failed, or incomplete delivery before redemption owns it.
            if row.get("status") not in {"reserved", "issuing", "delivery_pending", "delivery_failed", "pending"}:
                # Preserve redemption or terminal state.
                raise ConflictError("Invitation cannot be revoked in its current state")
            # Capture the prior internal lifecycle for audit.
            prior = row.get("status")
            # Store the fixed terminal state before touching token storage.
            row["status"] = "revoked"
            # Store the exact idempotency verifier for safe replay.
            row["last_action_idempotency_digest"] = action_digest
            # Stamp the terminal instant.
            row["revoked_at"] = self.clock()
            # Append one fixed privacy-safe lifecycle event.
            self._event(row, actor, "admin_revoke", prior, "revoked")
            # Publish a detached internal row for token revocation.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Persist the authoritative invitation transition.
        update_json(self.store_path, transition, default_invitations)
        # Revoke the current token when one has been issued; a replay is harmless.
        if selected.get("token_id"):
            # Delegate exact active-token revocation to the token platform.
            self.token_service.revoke(selected["token_id"])
        # Emit only opaque lifecycle identifiers.
        self.audit_sink("invitation_revoked", invitation_id=selected.get("invitation_id"), actor_id=actor)
        # Return the raw-recipient-free Admin view.
        return self._public(selected)

    # Reserve and redeem one invitation through a recoverable multi-document saga.
    def redeem(self, token: str, recipient: str, password: str, display_name: str, locale: str, terms_version: str, accepted: bool, idempotency_key: str) -> dict:
        # Reject every request through one public envelope while redemption remains disabled.
        if not self.enrollment_enabled:
            # Preserve the invitation without creating a reservation, account, player, or wallet.
            self._invalid_redemption()
        # Normalize and validate transient request fields before durable mutation.
        normalized = self._validate_email(recipient)
        # Normalize the player-visible label before any reservation or token mutation.
        label = str(display_name or "").strip()
        # Require a nonempty bounded name without control characters.
        if not label or len(label) > 80 or any(character in label for character in "\r\n"):
            # Collapse display-name validation into the generic public boundary.
            self._invalid_redemption()
        # Require the current translated locale for account defaults.
        if locale not in LOCALES:
            # Collapse locale probing into the generic public envelope.
            self._invalid_redemption()
        # Require affirmative acceptance of the exact current terms revision.
        if accepted is not True or str(terms_version or "") != config.GUEST_TERMS_VERSION:
            # Refuse stale, missing, or implied consent before identity reservation.
            self._invalid_redemption()
        # Validate the enrollment password before a token can be consumed.
        try:
            # Apply the canonical enrollment password policy without storing derived metadata here.
            auth.validate_enrollment_password(password)
        # Collapse password-policy detail into the generic unauthenticated response.
        except ValidationError:
            # Avoid disclosing which request field failed.
            self._invalid_redemption()
        # Validate the caller replay key before consuming a bearer.
        caller_key = self._idempotency(idempotency_key)
        # Compute durable recipient and replay verifiers without storing raw lookup values.
        recipient_digest = self._digest("recipient", normalized)
        # Bind the recovery claim to the caller key.
        idempotency_digest = self._digest("redemption-idempotency", caller_key)
        # Capture the claimed invitation and recovery identifiers.
        selected = {"already_redeemed": False}
        # Establish or resume one pre-consumption claim atomically.
        def claim(raw_state: Any) -> dict:
            # Validate the complete durable document.
            state = self._state(raw_state)
            # Find pending, redeeming, or redeemed rows bound to this recipient.
            candidates = [row for row in state["invitations"] if row.get("recipient_digest") == recipient_digest and row.get("status") in {"pending", "redeeming", "redeemed"}]
            # Prefer an exact idempotent recovery when one exists.
            row = next((candidate for candidate in candidates if hmac.compare_digest(str((candidate.get("redemption") or {}).get("idempotency_digest", "")), idempotency_digest)), None)
            # Otherwise select the single current pending invitation.
            row = row or next((candidate for candidate in candidates if candidate.get("status") == "pending"), None)
            # Track whether an abandoned pre-consumption claim may be safely recovered by this caller.
            takeover = False
            # Search only claims that never crossed the token-consumption boundary.
            if row is None:
                # Inspect each redeeming row for a bounded abandoned claim.
                for candidate in candidates:
                    # Read the internal recovery metadata without exposing it.
                    recovery = candidate.get("redemption") or {}
                    # Skip post-consumption or malformed claims because only the original caller may resume them.
                    if candidate.get("status") != "redeeming" or recovery.get("phase") != "claimed":
                        # Continue to another candidate.
                        continue
                    # Allow takeover only after the configured complete timeout elapsed.
                    if (self._parse(self.clock()) - self._safe_time(recovery.get("claimed_at"))).total_seconds() >= config.INVITATION_CLAIM_TIMEOUT_SECONDS:
                        # Select the abandoned account-free claim for recovery.
                        row = candidate
                        # Mark the bounded pre-consumption takeover path.
                        takeover = True
                        # Stop after the single active recipient invitation.
                        break
            # Reject absence, expiry, or an incompatible in-progress claim generically.
            if row is None or self._status(row) != ("redeemed" if row.get("status") == "redeemed" else row.get("status")):
                # Abort the transaction through the public generic error.
                self._invalid_redemption()
            # Return the exact completed replay without touching token or identity state.
            if row.get("status") == "redeemed":
                # Publish the successful terminal state to the caller.
                selected.update(dict(row))
                # Mark the completed idempotent replay.
                selected["already_redeemed"] = True
                # Leave durable state unchanged.
                return state
            # Inspect an existing in-progress claim.
            if row.get("status") == "redeeming":
                # Rebind an abandoned pre-consumption claim while retaining deterministic identity ids.
                if takeover:
                    # Replace only the caller replay verifier and claim timestamp before any token is consumed.
                    row["redemption"].update({"idempotency_digest": idempotency_digest, "claimed_at": self.clock(), "last_error": None})
                    # Refresh the lifecycle timestamp for operator visibility.
                    row["updated_at"] = self.clock()
                    # Publish the recovered deterministic claim.
                    selected.update(dict(row))
                    # Return the complete document.
                    return state
                # Require the exact caller replay verifier for any post-consumption recovery.
                if not hmac.compare_digest(str((row.get("redemption") or {}).get("idempotency_digest", "")), idempotency_digest):
                    # Refuse a competing browser after the claim began.
                    self._invalid_redemption()
                # Publish the existing deterministic recovery state.
                selected.update(dict(row))
                # Leave durable state unchanged.
                return state
            # Capture one claim instant before deterministic identifiers are allocated.
            now = self.clock()
            # Build the recoverable account-free claim metadata.
            redemption = {"idempotency_digest": idempotency_digest, "phase": "claimed", "claimed_at": now, "user_id": self.id_factory("user_invite"), "player_id": self.id_factory("player_invite"), "last_error": None}
            # Transition from pending to the internal recovery state.
            row["status"] = "redeeming"
            # Persist no password, token, caller key, or raw bearer in the claim.
            row["redemption"] = redemption
            # Refresh the lifecycle timestamp.
            row["updated_at"] = now
            # Publish a detached internal copy for the reservation and token steps.
            selected.update(dict(row))
            # Return the complete document.
            return state
        # Persist the claim through JSON locking or MySQL row locking.
        update_json(self.store_path, claim, default_invitations)
        # Return a completed exact replay without re-running side effects.
        if selected.get("already_redeemed"):
            # Return one generic success with no user, recipient, token, or audit identifier.
            return {"status": "enrolled"}
        # Read the deterministic recovery identifiers from the claimed row.
        redemption = dict(selected.get("redemption") or {})
        # Reserve canonical email uniqueness without creating an account or wallet.
        try:
            # Persist the account-free reservation before token consumption.
            auth.reserve_invited_identity(normalized, selected["invitation_id"], redemption["user_id"], redemption["player_id"], selected["expires_at"])
            # Consume or idempotently replay the exact purpose/subject-bound bearer.
            consumed = self.token_service.consume(PURPOSE, str(token or ""), subject=normalized, subject_active=True, idempotency_key=caller_key)
            # Reject a valid bearer that belongs to another invitation generation.
            if consumed.get("token_id") != selected.get("token_id"):
                # Preserve both invitation records and fail closed.
                raise ConflictError("Invitation token generation does not match the claim")
        # Release only pre-consumption claims after a generic token or reservation failure.
        except Exception:
            # Revert the invitation claim only when token consumption was not confirmed.
            def abandon(raw_state: Any) -> dict:
                # Validate the durable document before releasing the account-free claim.
                state = self._state(raw_state)
                # Resolve the exact claimed invitation.
                row = self._find(state, selected.get("invitation_id"))
                # Release only the same caller claim that remains before token consumption.
                if row is not None and row.get("status") == "redeeming" and (row.get("redemption") or {}).get("phase") == "claimed" and hmac.compare_digest(str((row.get("redemption") or {}).get("idempotency_digest", "")), idempotency_digest):
                    # Return the invitation to pending so the real recipient can retry.
                    row["status"] = "pending"
                    # Remove account-free recovery metadata containing no credential material.
                    row["redemption"] = None
                    # Refresh the lifecycle timestamp.
                    row["updated_at"] = self.clock()
                # Return the complete document.
                return state
            # Persist the safe pre-consumption release.
            update_json(self.store_path, abandon, default_invitations)
            # Release the matching account-free email reservation when no user exists.
            auth.release_invited_identity(selected.get("invitation_id"))
            # Collapse every failure into the one public response.
            self._invalid_redemption()
        # Track whether a concurrent exact-key worker already committed the terminal state.
        completed_replay = {"matched": False}
        # Record successful token consumption before provisioning identity state.
        def token_consumed(raw_state: Any) -> dict:
            # Validate durable state before advancing the recovery phase.
            state = self._state(raw_state)
            # Resolve the exact claimed invitation.
            row = self._find(state, selected["invitation_id"])
            # Read only structured recovery metadata before comparing replay bindings.
            recovery_state = row.get("redemption") if isinstance(row, dict) and isinstance(row.get("redemption"), dict) else {}
            # Compare the exact caller binding without exposing its stored verifier through timing.
            same_caller = hmac.compare_digest(str(recovery_state.get("idempotency_digest", "")), idempotency_digest)
            # Compare the deterministic identity references retained by the original claim.
            same_identity = hmac.compare_digest(str(recovery_state.get("user_id", "")), str(redemption.get("user_id", ""))) and hmac.compare_digest(str(recovery_state.get("player_id", "")), str(redemption.get("player_id", "")))
            # Compare the opaque consumed-token identifier returned to this exact caller.
            same_token = hmac.compare_digest(str(recovery_state.get("token_id", "")), str(consumed.get("token_id", "")))
            # Accept a concurrent worker's completed state only when every durable replay binding matches.
            if row is not None and row.get("status") == "redeemed" and recovery_state.get("phase") == "complete" and same_caller and same_identity and same_token:
                # Mark the terminal replay so this worker skips all remaining identity side effects.
                completed_replay["matched"] = True
                # Leave the already-committed invitation byte-for-byte unchanged.
                return state
            # Require the same caller claim before changing recovery state.
            if row is None or row.get("status") != "redeeming" or not same_caller:
                # Preserve all state and require operator recovery.
                raise ConflictError("Invitation redemption claim changed")
            # Advance the durable recovery phase after exact token confirmation.
            row["redemption"]["phase"] = "token_consumed"
            # Store only the opaque token identifier for recovery correlation.
            row["redemption"]["token_id"] = consumed["token_id"]
            # Refresh the lifecycle timestamp.
            row["updated_at"] = self.clock()
            # Return the complete document.
            return state
        # Commit the token-consumed recovery boundary.
        update_json(self.store_path, token_consumed, default_invitations)
        # Return the generic success when another exact-key worker already finalized the invitation.
        if completed_replay["matched"]:
            # Avoid re-running user, wallet, history, or audit effects after terminal convergence.
            return {"status": "enrolled"}
        # Provision or resume the inactive user, deterministic wallet, terms acceptance, and activation.
        try:
            # Delegate the recoverable identity saga after the bearer is confirmed.
            user = auth.provision_invited_user(normalized, password, label, locale, terms_version, selected["invitation_id"], redemption["user_id"], redemption["player_id"])
        # Preserve the token-consumed claim for same-key retry after any provisioning failure.
        except Exception:
            # Mark only a fixed recovery category in invitation state.
            def recovery_required(raw_state: Any) -> dict:
                # Validate the durable document before recording recovery state.
                state = self._state(raw_state)
                # Resolve the exact claimed invitation.
                row = self._find(state, selected["invitation_id"])
                # Store a low-cardinality operator cue only on the matching claim.
                if row is not None and row.get("status") == "redeeming" and isinstance(row.get("redemption"), dict):
                    # Avoid exception text, recipient, password, or bearer material.
                    row["redemption"]["last_error"] = "identity_provisioning"
                    # Refresh the lifecycle timestamp.
                    row["updated_at"] = self.clock()
                # Return the complete document.
                return state
            # Persist the recoverable operator state.
            update_json(self.store_path, recovery_required, default_invitations)
            # Return the same non-disclosing public error.
            self._invalid_redemption()
        # Track whether this worker performs the one durable terminal transition.
        finalized = {"changed": False}
        # Finalize the invitation after the canonical identity and wallet are active.
        def finalize(raw_state: Any) -> dict:
            # Validate the durable document before terminal transition.
            state = self._state(raw_state)
            # Resolve the exact invitation claim.
            row = self._find(state, selected["invitation_id"])
            # Read recovery metadata without accepting a malformed terminal row.
            recovery = row.get("redemption") if isinstance(row, dict) and isinstance(row.get("redemption"), dict) else {}
            # Compare the caller binding without leaking the stored verifier through timing.
            same_caller = hmac.compare_digest(str(recovery.get("idempotency_digest", "")), idempotency_digest)
            # Compare the deterministic identity references created by this exact claim.
            same_identity = hmac.compare_digest(str(recovery.get("user_id", "")), str(user.get("user_id", ""))) and hmac.compare_digest(str(recovery.get("player_id", "")), str(user.get("player_id", "")))
            # Accept a concurrent worker's already-committed terminal state only for the exact replay.
            if row is not None and row.get("status") == "redeemed" and recovery.get("phase") == "complete" and same_caller and same_identity:
                # Leave the terminal document and lifecycle history byte-for-byte unchanged.
                return state
            # Require the same in-progress caller recovery binding and active identity reference.
            if row is None or row.get("status") != "redeeming" or not same_caller or not same_identity:
                # Preserve active account state and surface operator recovery on retry.
                raise ConflictError("Invitation redemption finalization changed")
            # Transition to the terminal redeemed state.
            row["status"] = "redeemed"
            # Stamp the successful terminal instant.
            row["redeemed_at"] = self.clock()
            # Record only opaque active identity references in recovery metadata.
            row["redemption"].update({"phase": "complete", "user_id": user.get("user_id"), "player_id": user.get("player_id"), "last_error": None})
            # Append a system lifecycle event without a caller-controlled reason.
            self._event(row, "system", "recipient_redeem", "redeeming", "redeemed")
            # Mark this worker as the sole terminal transition owner.
            finalized["changed"] = True
            # Return the complete document.
            return state
        # Commit the terminal invitation state.
        update_json(self.store_path, finalize, default_invitations)
        # Emit one opaque lifecycle audit only from the worker that committed the transition.
        if finalized["changed"]:
            # Publish no recipient, bearer, password, or caller key in the audit event.
            self.audit_sink("invitation_redeemed", invitation_id=selected["invitation_id"], user_id=user.get("user_id"))
        # Return one generic success without account, recipient, token, or audit details.
        return {"status": "enrolled"}

    # Raise the one public invitation-redemption error.
    @staticmethod
    def _invalid_redemption() -> None:
        # Use a stable message and reason for disabled, invalid, expired, revoked, replayed, and raced requests.
        raise ValidationError("invitation could not be redeemed", dict(GENERIC_REDEMPTION_DETAILS))

    # Return a bounded Admin list plus secret-free readiness and recovery counts.
    def listing(self, limit: int = 100) -> dict:
        # Bound the Admin query without accepting booleans or unbounded scans.
        bounded = max(1, min(int(limit), 200))
        # Read current state without creating or repairing a document.
        state = self._state(read_json(self.store_path, default_invitations))
        # Order newest rows first and project only privacy-safe fields.
        rows = [self._public(row) for row in reversed(state["invitations"][-bounded:])]
        # Read existing mail readiness without provider or network access.
        mail_readiness = self.mail_service.readiness()
        # Return only fixed booleans, safe status, counts, and invitation projections.
        return {"enabled": self.enabled, "redemption_enabled": self.enrollment_enabled, "mail_status": mail_readiness.get("status"), "recovery_required": sum(1 for row in state["invitations"] if row.get("status") in {"reserved", "issuing", "delivery_pending", "redeeming"}), "invitations": rows}

    # Prune only terminal metadata beyond the fixed retention period.
    def cleanup(self) -> int:
        # Capture one cleanup instant for every row decision.
        now = self._parse(self.clock())
        # Count rows removed by the successful provider transaction.
        result = {"count": 0}
        # Remove only unambiguously terminal rows after complete retention.
        def prune(raw_state: Any) -> dict:
            # Validate the complete durable state before deleting anything.
            state = self._state(raw_state)
            # Retain active, recovery, malformed-time, and recent terminal rows.
            retained = []
            # Evaluate each row independently.
            for row in state["invitations"]:
                # Select the terminal timestamp only for redeemed or revoked rows.
                reference = row.get("redeemed_at") if row.get("status") == "redeemed" else row.get("revoked_at") if row.get("status") == "revoked" else None
                # Retain nonterminal rows and malformed terminal timestamps for operator recovery.
                if not reference or (now - self._safe_time(reference)).total_seconds() <= config.INVITATION_RETENTION_SECONDS:
                    # Preserve this row unchanged.
                    retained.append(row)
            # Count only rows whose terminal retention safely elapsed.
            result["count"] = len(state["invitations"]) - len(retained)
            # Store the bounded retained collection.
            state["invitations"] = retained
            # Return the complete document.
            return state
        # Publish cleanup through JSON locking or MySQL row locking.
        update_json(self.store_path, prune, default_invitations)
        # Return the number of pruned terminal rows.
        return result["count"]


# Build one lightweight configured service per call so isolated tests can replace environment-loaded dependencies.
def configured_service() -> InvitationService:
    # Return the disabled-by-default service composed from approved foundations.
    return InvitationService(enabled=config.INVITATIONS_ENABLED, enrollment_enabled=config.ENROLLMENT_ENABLED, digest_key=config.MAIL_DIGEST_KEY)


# Create one invitation through the configured production facade.
def create(recipient: str, actor_id: str, *, locale: str, idempotency_key: str) -> dict:
    # Delegate validation, rate limits, recovery, token, and mail policy to the service.
    return configured_service().create(recipient, actor_id, locale=locale, idempotency_key=idempotency_key)


# Resend one invitation through the configured production facade.
def resend(invitation_id: str, actor_id: str, *, idempotency_key: str) -> dict:
    # Delegate the fresh generation and recoverable delivery saga.
    return configured_service().resend(invitation_id, actor_id, idempotency_key=idempotency_key)


# Revoke one invitation through the configured production facade.
def revoke(invitation_id: str, actor_id: str, *, idempotency_key: str) -> dict:
    # Delegate the state-first terminal transition and token revocation.
    return configured_service().revoke(invitation_id, actor_id, idempotency_key=idempotency_key)


# Redeem one invitation through the configured production facade.
def redeem(token: str, recipient: str, password: str, display_name: str, locale: str, terms_version: str, accepted: bool, idempotency_key: str) -> dict:
    # Start protected delegation so every bounded domain rejection shares one public response.
    try:
        # Delegate the recoverable identity saga to the configured disabled-by-default service.
        return configured_service().redeem(token, recipient, password, display_name, locale, terms_version, accepted, idempotency_key)
    # Collapse validation, conflict, forbidden, and rate-limit state into one non-enumerating envelope.
    except CasinoError as error:
        # Preserve an already generic invitation rejection without changing its stable message.
        if error.code == "VALIDATION_ERROR" and error.details == GENERIC_REDEMPTION_DETAILS:
            # Re-raise the exact generic boundary error.
            raise
        # Hide all other bounded state, policy, and input details from the anonymous caller.
        InvitationService._invalid_redemption()


# List bounded invitation diagnostics through the configured production facade.
def listing(limit: int = 100) -> dict:
    # Delegate privacy-safe projections and readiness counts.
    return configured_service().listing(limit)


# Prune terminal invitation metadata through the configured production facade.
def cleanup() -> int:
    # Delegate bounded non-destructive retention cleanup.
    return configured_service().cleanup()
