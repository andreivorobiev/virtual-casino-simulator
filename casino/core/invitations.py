"""Admin email invitations and secure redemption into a canonical account. (issue #332)

Composes the one-time token platform (#331) and the transactional mail boundary (#330): an Admin
sends an invitation, the recipient redeems it with a verified email and password, and only then is a
canonical account created. An invitation authorizes enrollment; it never pre-creates an account,
player, wallet, or password, and never auto-links a social identity by email match. Redemption is
disabled by default and gated behind a separate release approval. Responses are generic and failures
are safe so an invitation's existence and status are not disclosed to an unauthenticated caller.
"""

# Import required dependency so recipient lookups use keyed digests in logs and audit events.
import hmac
# Import required dependency so recipient digests are one-way.
import hashlib
# Import required dependency so lifetime and cooldown math use aware timestamps.
from datetime import datetime, timedelta

# Import enrollment gating, cooldown, and the shared data root.
from casino.config import DATA_DIR, ENROLLMENT_ENABLED, INVITATION_RESEND_COOLDOWN_SECONDS, MAIL_DIGEST_KEY, SCHEMA_VERSION
# Import the one-time token platform for the invitation bearer lifecycle.
from casino.core import one_time_tokens
# Import the transactional mail boundary for canonical-origin delivery.
from casino.core import mail
# Import the canonical identity store so redemption creates a verified account only on success.
from casino.core import auth
# Import the shared clock so invitation timestamps match session and token records.
from casino.core.clock import utc_now
# Import the shared id helper so invitation and audit identifiers stay bounded and random.
from casino.core.ids import new_id
# Import atomic JSON persistence so concurrent redemption cannot double-enroll.
from casino.core.state_store import read_json, update_json
# Import the application logger so audit events omit every sensitive field.
from casino.core import logger
# Import standard application errors for stable fail-closed envelopes.
from casino.errors import ValidationError

# Store the invitation document path in the governed auth namespace.
INVITATIONS_PATH = DATA_DIR / "auth" / "invitations.json"
# Bind invitation tokens to the shared token platform under this fixed purpose.
PURPOSE = "invitation"

# Build a new empty invitation document.
def default_invitations() -> dict:
    # Return the canonical schema-stamped container with no invitation rows.
    return {"schema_version": SCHEMA_VERSION, "invitations": []}

# Parse one stored ISO timestamp into an aware datetime for cooldown math.
def _parse(value: str) -> datetime:
    # Convert the shared Z suffix into an offset the standard parser accepts.
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

# Normalize a recipient email so binding and lookup are deterministic.
def _normalize(email: str) -> str:
    # Return the trimmed lower-cased address.
    return str(email or "").strip().lower()

# Compute a keyed one-way digest so audit logs never carry a raw recipient address.
def _digest(email: str) -> str:
    # Return the HMAC-SHA256 hex digest of the normalized address.
    return hmac.new(MAIL_DIGEST_KEY.encode("utf-8"), _normalize(email).encode("utf-8"), hashlib.sha256).hexdigest()

# Present one invitation record to Admin without exposing the token or any verifier.
def _public(row: dict) -> dict:
    # Return only the least-privilege fields an Admin needs to inspect and act on the invitation.
    return {key: row.get(key) for key in ("invitation_id", "email", "status", "created_at", "expires_at", "redeemed_at", "revoked_at", "invited_by")}

# Create and deliver one email invitation, honoring the resend cooldown, without creating any account.
def create(email: str, invited_by: str = "", *, ttl_seconds: int = None) -> dict:
    # Normalize the recipient before any binding or delivery.
    normalized = _normalize(email)
    # Reject an empty or malformed recipient before a token is minted.
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        # Fail closed on an invalid recipient without echoing the value.
        raise ValidationError("a valid recipient email is required", {"reason": "bad_email"})
    # Capture one create instant for cooldown and expiry math.
    now = utc_now()
    # Read the current invitations to enforce the per-recipient resend cooldown.
    state = read_json(INVITATIONS_PATH, default_invitations)
    # Find the most recent still-pending invitation for this recipient.
    recent = [row for row in (state.get("invitations", []) if isinstance(state, dict) else []) if row.get("email_digest") == _digest(normalized) and row.get("status") == "pending"]
    # Refuse a repeat invitation inside the cooldown window so a recipient cannot be flooded.
    if recent and (_parse(now) - _parse(max(row.get("created_at") for row in recent))).total_seconds() < INVITATION_RESEND_COOLDOWN_SECONDS:
        # Fail closed with a non-sensitive cooldown reason.
        raise ValidationError("an invitation was already sent recently", {"reason": "cooldown"})
    # Revoke any prior pending invitations so only the newest token can be redeemed.
    for row in recent:
        # Revoke the superseded token in the shared platform.
        one_time_tokens.revoke(row.get("token_id"))
        # Mark the superseded invitation revoked.
        _set_status(row.get("invitation_id"), "revoked")
    # Issue a one-time invitation token bound to this recipient.
    issued = one_time_tokens.issue(PURPOSE, normalized, ttl_seconds=ttl_seconds)
    # Deliver the canonical-origin redemption link through the mail boundary (captured locally while disabled).
    mail.send(PURPOSE, normalized, token=issued["token"])
    # Allocate a stable invitation id for Admin inspection.
    invitation_id = new_id("invite")
    # Build the invitation record; it authorizes enrollment but pre-creates no account, player, wallet, or password.
    record = {
        "invitation_id": invitation_id,
        "email": normalized,
        "email_digest": _digest(normalized),
        "status": "pending",
        "token_id": issued["token_id"],
        "invited_by": str(invited_by or ""),
        "created_at": now,
        "expires_at": issued["expires_at"],
        "redeemed_at": None,
        "revoked_at": None,
        "audit_id": new_id("inviteaudit"),
    }
    # Persist the invitation atomically.
    def mutate(document: dict) -> dict:
        # Normalize malformed persisted state into the canonical container.
        if not isinstance(document, dict) or "invitations" not in document:
            document = default_invitations()
        # Append the new pending invitation.
        document["invitations"].append(record)
        # Return the mutated document for atomic persistence.
        return document
    # Route the write through the shared atomic helper.
    update_json(INVITATIONS_PATH, mutate, default_invitations)
    # Emit a sensitive-field-free audit event.
    logger.info("invitation_created", invitation_id=invitation_id, audit_id=record["audit_id"])
    # Return the least-privilege Admin view of the new invitation.
    return _public(record)

# Set one invitation's terminal status atomically without exposing its token.
def _set_status(invitation_id: str, status: str) -> bool:
    # Track whether a matching invitation changed.
    changed = {"done": False}
    # Capture one status instant.
    now = utc_now()
    # Apply the status change atomically.
    def mutate(document: dict) -> dict:
        # Walk the stored rows to find the target invitation.
        for row in document.get("invitations", []) if isinstance(document, dict) else []:
            # Update only the matching, still-pending invitation.
            if row.get("invitation_id") == invitation_id and row.get("status") == "pending":
                # Apply the requested terminal status.
                row["status"] = status
                # Stamp the matching terminal timestamp.
                row["redeemed_at" if status == "redeemed" else "revoked_at"] = now
                # Record that a change occurred.
                changed["done"] = True
        # Return the mutated document for atomic persistence.
        return document if isinstance(document, dict) else default_invitations()
    # Persist the status change.
    update_json(INVITATIONS_PATH, mutate, default_invitations)
    # Return whether a change occurred.
    return changed["done"]

# Look up one invitation record by id for Admin operations.
def _find(invitation_id: str) -> dict:
    # Read the current invitations without mutating them.
    state = read_json(INVITATIONS_PATH, default_invitations)
    # Return the matching row or None.
    for row in state.get("invitations", []) if isinstance(state, dict) else []:
        # Match on the exact invitation id.
        if row.get("invitation_id") == invitation_id:
            # Return the matching row.
            return row
    # Signal that no invitation matched.
    return None

# Revoke one pending invitation so its token can no longer be redeemed.
def revoke(invitation_id: str) -> dict:
    # Find the target invitation.
    row = _find(invitation_id)
    # Fail closed when the invitation does not exist or is already terminal.
    if not row or row.get("status") != "pending":
        # Reject without echoing whether the id exists beyond the Admin boundary.
        raise ValidationError("invitation cannot be revoked", {"reason": "not_pending"})
    # Revoke the underlying one-time token.
    one_time_tokens.revoke(row.get("token_id"))
    # Mark the invitation revoked.
    _set_status(invitation_id, "revoked")
    # Emit a sensitive-field-free audit event.
    logger.info("invitation_revoked", invitation_id=invitation_id)
    # Return the updated Admin view.
    return _public(_find(invitation_id))

# Resend one pending invitation with a fresh token, honoring the cooldown.
def resend(invitation_id: str) -> dict:
    # Find the target invitation.
    row = _find(invitation_id)
    # Fail closed when the invitation is not pending.
    if not row or row.get("status") != "pending":
        # Reject a resend against a terminal or missing invitation.
        raise ValidationError("invitation cannot be resent", {"reason": "not_pending"})
    # Reuse the create path so cooldown, prior-token revocation, delivery, and audit stay identical.
    return create(row.get("email"), row.get("invited_by", ""))

# List invitations for the least-privilege Admin inspection surface.
def listing(limit: int = 100) -> list:
    # Read the current invitations without mutating them.
    state = read_json(INVITATIONS_PATH, default_invitations)
    # Return the most recent bounded window as Admin views, newest first.
    return [_public(row) for row in list(reversed((state.get("invitations", []) if isinstance(state, dict) else [])[-limit:]))]

# Redeem an invitation into a new canonical account with a verified email and password.
def redeem(token: str, email: str, password: str) -> dict:
    # Refuse redemption while enrollment is disabled so no account can be created before release approval.
    if not ENROLLMENT_ENABLED:
        # Fail closed with a generic, non-disclosing reason.
        raise ValidationError("enrollment is not available", {"reason": "enrollment_disabled"})
    # Normalize the claimed recipient before consuming the bearer.
    normalized = _normalize(email)
    # Require a password that meets the minimum strength before any account is created.
    if not isinstance(password, str) or len(password) < 8:
        # Fail closed on a weak or missing password.
        raise ValidationError("a valid password is required", {"reason": "bad_password"})
    # Consume the one-time invitation token bound to the claimed recipient; any failure is generic.
    try:
        # Atomically consume the bearer, enforcing purpose, subject binding, expiry, and single use.
        consumed = one_time_tokens.consume(PURPOSE, token, subject=normalized)
    # Convert every consume failure into one uniform redemption error that discloses nothing.
    except ValidationError:
        # Fail closed without revealing whether the token, subject, or state was the cause.
        raise ValidationError("invitation could not be redeemed", {"reason": "invalid_redemption"})
    # Create the canonical account only after the token is successfully consumed; never auto-link a social identity.
    try:
        # Enroll the verified account with the claimed email and chosen password.
        user = auth.create_user(normalized, password, normalized.split("@")[0], "player")
    # Convert a duplicate or invalid account into a generic redemption error.
    except Exception:
        # Fail closed without disclosing whether the account already existed.
        raise ValidationError("invitation could not be redeemed", {"reason": "invalid_redemption"})
    # Mark the invitation redeemed by matching its consumed token id.
    def mutate(document: dict) -> dict:
        # Walk the stored rows to find the invitation tied to the consumed token.
        for row in document.get("invitations", []) if isinstance(document, dict) else []:
            # Redeem only the matching pending invitation.
            if row.get("token_id") == consumed.get("token_id") and row.get("status") == "pending":
                # Mark the invitation redeemed.
                row["status"] = "redeemed"
                # Stamp the redemption instant.
                row["redeemed_at"] = utc_now()
        # Return the mutated document for atomic persistence.
        return document if isinstance(document, dict) else default_invitations()
    # Persist the redemption status atomically.
    update_json(INVITATIONS_PATH, mutate, default_invitations)
    # Emit a sensitive-field-free audit event for the enrollment.
    logger.info("invitation_redeemed", invitation_token_id=consumed.get("token_id"), user_id=user.get("user_id"))
    # Return a generic enrollment result without any credential or token.
    return {"status": "enrolled", "user_id": user.get("user_id")}
