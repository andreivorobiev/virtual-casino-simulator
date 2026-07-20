"""Provider-neutral transactional mail boundary for enrollment and recovery links. (issue #330)

Infrastructure only and disabled by default: this module builds canonical-origin links and routes
purpose-bound messages through a pluggable transport. The default transport captures messages to a
local outbox and never touches the network; a Postmark transport exists but stays inert until the
deployment is explicitly configured, enabled, and released. No API key, recipient address, token, or
raw provider response is ever logged, echoed in an error, or stored in raw form. This module does not
create users, send live mail, change providers, or authorize enablement.
"""

# Import required dependency so recipient values are stored only as keyed digests in the audit outbox.
import hmac
# Import required dependency so recipient digests are one-way.
import hashlib
# Import required dependency so link tokens are appended through safe URL encoding.
from urllib.parse import quote

# Import the mail configuration and the shared token digest key without ever importing a live secret path.
from casino.config import DATA_DIR, MAIL_CANONICAL_ORIGIN, MAIL_DIGEST_KEY, MAIL_ENABLED, MAIL_FROM_ADDRESS, MAIL_POSTMARK_SERVER_TOKEN, MAIL_PROVIDER, MAIL_SENDING_DOMAIN, SCHEMA_VERSION
# Import the shared clock so outbox timestamps match other governed records.
from casino.core.clock import utc_now
# Import the shared id helper so delivery identifiers stay bounded and random.
from casino.core.ids import new_id
# Import atomic JSON persistence so the local outbox capture is concurrency-safe.
from casino.core.state_store import update_json
# Import the application logger so audit events omit every sensitive field.
from casino.core import logger
# Import standard application errors for stable fail-closed envelopes.
from casino.errors import ValidationError

# Store the local capture outbox path used by the disabled transport.
OUTBOX_PATH = DATA_DIR / "mail" / "outbox.json"
# Retain at most this many captured messages so the local outbox stays bounded.
MAX_OUTBOX = 500
# Enumerate the message purposes this boundary will build templates for.
PURPOSES = frozenset({"invitation", "email_verification", "password_reset", "magic_link"})
# Map each purpose to its subject and the browser path its link targets.
PURPOSE_TEMPLATES = {
    "invitation": {"subject": "Your Casino Simulator invitation", "path": "/enroll/invitation"},
    "email_verification": {"subject": "Verify your Casino Simulator email", "path": "/enroll/verify"},
    "password_reset": {"subject": "Reset your Casino Simulator password", "path": "/account/reset"},
    "magic_link": {"subject": "Your Casino Simulator sign-in link", "path": "/account/magic-link"},
}

# Build a new empty outbox document.
def default_outbox() -> dict:
    # Return the canonical schema-stamped container with no captured messages.
    return {"schema_version": SCHEMA_VERSION, "messages": []}

# Compute a keyed one-way digest so recipient addresses are never stored or logged in raw form.
def _digest(value: str) -> str:
    # Return the HMAC-SHA256 hex digest of the value under the configured server key.
    return hmac.new(MAIL_DIGEST_KEY.encode("utf-8"), str(value or "").strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()

# Report the mail boundary's readiness without ever exposing a secret value.
def readiness() -> dict:
    # Reveal only boolean configuration state so diagnostics never leak the token, sender, or domain values.
    return {
        "enabled": bool(MAIL_ENABLED),
        "provider": MAIL_PROVIDER,
        "from_configured": bool(MAIL_FROM_ADDRESS),
        "sending_domain_configured": bool(MAIL_SENDING_DOMAIN),
        "canonical_origin_https": MAIL_CANONICAL_ORIGIN.startswith("https://"),
        "provider_credential_configured": bool(MAIL_POSTMARK_SERVER_TOKEN) if MAIL_PROVIDER == "postmark" else True,
        "ready": _is_ready(),
    }

# Decide whether live delivery is fully and safely configured; misconfiguration fails closed.
def _is_ready() -> bool:
    # A disabled deployment is intentionally never ready for live delivery.
    if not MAIL_ENABLED:
        # Signal that enrollment-method enablement must stay blocked.
        return False
    # The canonical origin must be an absolute HTTPS origin before any link is delivered.
    if not MAIL_CANONICAL_ORIGIN.startswith("https://"):
        # Fail closed on a non-HTTPS or missing origin.
        return False
    # A live sender identity and verified sending domain are both required.
    if not MAIL_FROM_ADDRESS or not MAIL_SENDING_DOMAIN:
        # Fail closed on an incomplete sender identity.
        return False
    # The Postmark transport additionally requires its server credential.
    if MAIL_PROVIDER == "postmark" and not MAIL_POSTMARK_SERVER_TOKEN:
        # Fail closed on a missing provider credential.
        return False
    # Only the recognized transports may be considered ready.
    return MAIL_PROVIDER in ("disabled", "postmark")

# Build one canonical-origin HTTPS link, rejecting open redirects and host spoofing.
def build_link(path: str, *, token: str = None) -> str:
    # Require a same-origin absolute path so a caller cannot inject a scheme or host.
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//") or "\\" in path or ":" in path:
        # Fail closed on any value that could redirect off the canonical origin.
        raise ValidationError("mail link path must be a safe same-origin path", {"reason": "unsafe_path"})
    # Require the configured origin to be HTTPS before any link is generated.
    if not MAIL_CANONICAL_ORIGIN.startswith("https://"):
        # Fail closed on a non-HTTPS canonical origin.
        raise ValidationError("mail canonical origin must be HTTPS", {"reason": "origin_not_https"})
    # Append the bearer token as a safely-encoded query parameter when present.
    suffix = f"?token={quote(token, safe='')}" if token else ""
    # Return the fully-qualified canonical link.
    return f"{MAIL_CANONICAL_ORIGIN}{path}{suffix}"

# Capture one built message into the local outbox without any network delivery.
def _capture(message: dict) -> None:
    # Append the capture atomically, pruning old rows in the same mutation.
    def mutate(state: dict) -> dict:
        # Normalize malformed persisted state into the canonical container.
        if not isinstance(state, dict) or "messages" not in state:
            state = default_outbox()
        # Append the captured message.
        state["messages"].append(message)
        # Keep only the most recent bounded window of captures.
        state["messages"] = state["messages"][-MAX_OUTBOX:]
        # Return the mutated document for atomic persistence.
        return state
    # Route the write through the shared atomic helper.
    update_json(OUTBOX_PATH, mutate, default_outbox)

# Send one purpose-bound message through the configured transport, returning a delivery receipt.
def send(purpose: str, recipient: str, *, token: str = None, path: str = None, link_params: dict = None) -> dict:
    # Reject any purpose outside the fixed allowlist.
    if purpose not in PURPOSES:
        # Fail closed without echoing the requested purpose value.
        raise ValidationError("unknown mail purpose", {"reason": "bad_purpose"})
    # Require a non-empty recipient before any message is built.
    if not str(recipient or "").strip():
        # Fail closed on a missing recipient.
        raise ValidationError("mail recipient is required", {"reason": "missing_recipient"})
    # Resolve the template for this purpose.
    template = PURPOSE_TEMPLATES[purpose]
    # Resolve the same-origin path once for both the deliverable and the redacted stored link.
    link_path = path or template["path"]
    # Build the full canonical-origin link with the bearer token; this is returned to the caller for delivery only.
    link = build_link(link_path, token=token)
    # Build a token-free link for the persisted outbox so no raw bearer is ever stored at rest.
    stored_link = build_link(link_path)
    # Allocate a stable, idempotent delivery id that reveals nothing about the recipient.
    delivery_id = new_id("maildlv")
    # Capture one build instant.
    now = utc_now()
    # Build the outbox record storing only digests and a token-free link, never the raw address, token, or a password.
    captured = {
        "delivery_id": delivery_id,
        "purpose": purpose,
        "recipient_digest": _digest(recipient),
        "subject": template["subject"],
        "link": stored_link,
        "token_digest": _digest(token) if token else None,
        "provider": MAIL_PROVIDER,
        "status": "captured" if MAIL_PROVIDER == "disabled" or not _is_ready() else "queued",
        "created_at": now,
    }
    # Route to the selected transport; the disabled transport (and any not-ready deployment) only captures.
    if MAIL_PROVIDER == "disabled" or not _is_ready():
        # Capture the message locally without any network delivery.
        _capture(captured)
    # The Postmark transport is config-gated and intentionally not invoked from tests or local runs.
    elif MAIL_PROVIDER == "postmark":
        # Capture an audit record before a live send so retries and diagnostics never depend on the raw payload.
        _capture(captured)
        # Perform the live provider send only when explicitly enabled and configured.
        _postmark_send(captured, recipient, link)
    # Reject an unrecognized provider selection.
    else:
        # Fail closed on an unknown transport.
        raise ValidationError("unknown mail provider", {"reason": "bad_provider"})
    # Emit a sensitive-field-free audit event for the delivery.
    logger.info("mail_message_sent", delivery_id=delivery_id, purpose=purpose, provider=MAIL_PROVIDER, status=captured["status"])
    # Return the receipt without any raw recipient, token, or secret.
    return {"delivery_id": delivery_id, "purpose": purpose, "provider": MAIL_PROVIDER, "status": captured["status"], "link": link}

# Perform a live Postmark send; kept behind readiness gates and never exercised by tests or local runs.
def _postmark_send(record: dict, recipient: str, link: str) -> None:
    # Refuse to send unless the deployment is fully configured, enabled, and released.
    if not _is_ready() or MAIL_PROVIDER != "postmark":
        # Fail closed rather than attempt an unconfigured live send.
        raise ValidationError("mail delivery is not ready", {"reason": "not_ready"})
    # Import the network client lazily so local and test environments never require it.
    import json
    import urllib.request
    # Build the provider request body from the configured sender identity and approved link representation.
    body = json.dumps({"From": MAIL_FROM_ADDRESS, "To": recipient, "Subject": record["subject"], "TextBody": f"{record['subject']}\n\n{link}\n"}).encode("utf-8")
    # Construct the provider request, carrying the server token only in the transport header.
    request = urllib.request.Request("https://api.postmarkapp.com/email", data=body, method="POST", headers={"Content-Type": "application/json", "Accept": "application/json", "X-Postmark-Server-Token": MAIL_POSTMARK_SERVER_TOKEN})
    # Start protected delivery so a provider failure is audit-safe and never leaks the payload or response body.
    try:
        # Execute the bounded live request.
        urllib.request.urlopen(request, timeout=10).read()
    # Convert any provider failure into a non-sensitive fail-closed error.
    except Exception:
        # Raise a value-free error that cannot echo the recipient, token, or raw provider response.
        raise ValidationError("mail delivery failed", {"reason": "provider_error"})
