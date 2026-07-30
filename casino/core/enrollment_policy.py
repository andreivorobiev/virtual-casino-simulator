"""Durable, concurrency-safe enrollment policy resolution. (AUTH-013)

Enrollment was governed only by process environment variables read once at import
(`casino/config.py` SIGNUP_ENABLED / INVITATIONS_ENABLED / ENROLLMENT_ENABLED), so changing who may
join required an operator to edit the environment and restart. This module introduces the durable
policy document those flags become the seed for.

The resolved policy reproduces the environment baseline exactly when no stored document exists.
Public signup and invitation redemption now enforce that same resolved policy, and each decision is
written to the existing operational JSONL log before either route may mutate enrollment state.
Least-privilege Admin mutation, readiness, immutable actor/change audit, and provider enablement
remain separate work.

The policy is read through the active StorageProvider so JSON and MySQL share one durable document
boundary. This slice exposes no application or Admin write path, and it never enables a method on
its own.
"""

# Import the configuration flags that seed the policy so the default stays the deployed behaviour.
from casino import config
# Import the storage provider accessor so the document uses the active backend.
from casino.core.storage import get_storage_provider
# Import the existing JSONL logger for bounded operational enrollment-decision records.
from casino.core import logger
# Import the validation envelope so a rejected policy value fails closed with a stable code.
from casino.errors import ValidationError

# Name the durable document so both providers agree on one canonical key.
POLICY_DOCUMENT_KEY = "auth/enrollment_policy"

# Version the stored shape so a later slice can migrate it without guessing.
SCHEMA_VERSION = 1

# Enumerate the enrollment modes exactly as issue #333 defines them.
MODE_CLOSED = "closed"
# Allow Admin invitations to be sent and redeemed, but no public method.
MODE_INVITE_ONLY = "invite-only"
# Allow invitations plus whichever public methods are independently enabled.
MODE_SELF_SIGNUP = "self-signup"

# Publish the ordered legal modes for validation and for the future Admin surface.
MODES = (MODE_CLOSED, MODE_INVITE_ONLY, MODE_SELF_SIGNUP)

# Name the self-signup methods that can be enabled independently of the mode.
METHODS = ("email", "google", "facebook")

# Name the only operational event this slice may emit.
AUDIT_EVENT = "enrollment_decision"

# Name each public enrollment route governed by this slice.
ROUTE_SIGNUP = "signup"
# Name private invitation redemption independently from public self-signup.
ROUTE_INVITATION = "invitation"

# Publish only reviewed route labels, plus one fixed collapse value for hostile callers.
AUDIT_ROUTES = frozenset({ROUTE_SIGNUP, ROUTE_INVITATION, "unknown"})
# Publish only the policy modes already owned by the durable document.
AUDIT_MODES = frozenset(MODES)
# Publish only the reviewed self-signup methods, plus one fixed collapse value.
AUDIT_METHODS = frozenset((*METHODS, "unknown"))
# Publish only fixed decision labels.
AUDIT_DECISIONS = frozenset({"allowed", "denied"})
# Publish only fixed reasons that reveal no identity, bearer, credential, or policy document value.
AUDIT_REASONS = frozenset({"allowed", "mode_closed", "self_signup_disabled", "method_disabled", "invitations_disabled", "unknown_route"})
# Retain only the reviewed low-cardinality fields in the operational JSONL record.
AUDIT_FIELDS = frozenset({"route", "mode", "method", "decision", "reason"})


# Identify a fixed logging failure without exposing an exception, path, or caller value.
class EnrollmentAuditError(RuntimeError):
    """Report that an enrollment decision could not be recorded before mutation."""


# Derive the environment baseline that the deployed release already behaves as.
def environment_baseline() -> dict:
    """Return the policy the current environment flags describe.

    This is the seed and the fallback. It must reproduce deployed behaviour exactly while no Admin
    write path exists; a separately governed transaction may store a reviewed document later.
    """
    # Treat public email signup as the only method the environment can currently enable.
    email_enabled = bool(config.SIGNUP_ENABLED)
    # Treat invitation enrollment as live only when both invitation flags agree, matching app.py.
    invitations_live = bool(config.INVITATIONS_ENABLED and config.ENROLLMENT_ENABLED)
    # Select the widest mode the environment justifies, so nothing is silently narrowed.
    if email_enabled:
        # Public signup implies the self-signup mode regardless of invitation state.
        mode = MODE_SELF_SIGNUP
    # Fall back to invite-only when invitations are the only live route.
    elif invitations_live:
        # Invitations may be sent and redeemed but no public method is open.
        mode = MODE_INVITE_ONLY
    # Otherwise no new enrollment is possible at all.
    else:
        # Closed is the restricted-preview default this project ships with.
        mode = MODE_CLOSED
    # Return the baseline with providers off, because no environment flag enables them today.
    return {
        # Record the schema so a stored copy is self-describing.
        "schema_version": SCHEMA_VERSION,
        # Record the resolved mode.
        "mode": mode,
        # Record each public method independently of the mode.
        "methods": {"email": email_enabled, "google": False, "facebook": False},
        # Preserve the invitation capability separately so mode changes cannot silently revoke it.
        "invitations_enabled": invitations_live,
    }


# Normalize any stored or supplied policy into the canonical shape without trusting its contents.
def normalize(candidate) -> dict:
    """Return a valid policy, rejecting unknown modes rather than defaulting around them."""
    # Start from the environment baseline so a partial document cannot widen access by omission.
    resolved = environment_baseline()
    # Ignore a non-mapping document instead of letting it replace policy with junk.
    if not isinstance(candidate, dict):
        # Return the baseline unchanged for any malformed stored value.
        return resolved
    # Read the stored schema marker before considering any capability override.
    stored_schema_version = candidate.get("schema_version")
    # Reject absent, boolean, string, old, or future shapes by preserving the deployed baseline.
    if type(stored_schema_version) is not int or stored_schema_version != SCHEMA_VERSION:
        # Never interpret fields from a document whose exact shape this release does not own.
        return resolved
    # Apply a stored mode only when it is one this release understands.
    stored_mode = candidate.get("mode")
    # Reject an unrecognized mode loudly so a typo cannot silently open enrollment.
    if stored_mode is not None:
        # Compare against the closed vocabulary rather than accepting any string.
        if stored_mode not in MODES:
            # Fail closed with a stable envelope naming the legal values.
            raise ValidationError(f"enrollment mode must be one of: {', '.join(MODES)}")
        # Store the validated mode.
        resolved["mode"] = stored_mode
    # Apply stored method flags one at a time so an unknown key cannot introduce a method.
    stored_methods = candidate.get("methods")
    # Only consider a mapping; anything else leaves the baseline methods in place.
    if isinstance(stored_methods, dict):
        # Visit the declared methods rather than whatever the document happens to contain.
        for method in METHODS:
            # Skip a method the document does not mention so the baseline stands.
            if method in stored_methods:
                # Coerce to a strict boolean so truthy strings cannot enable a provider.
                resolved["methods"][method] = stored_methods[method] is True
    # Apply the invitation capability when present, coerced the same strict way.
    if "invitations_enabled" in candidate:
        # Require an exact boolean so no truthy value can widen access.
        resolved["invitations_enabled"] = candidate["invitations_enabled"] is True
    # Return the canonical policy.
    return resolved


# Read the durable policy, falling back to the environment baseline when none is stored.
def current() -> dict:
    """Return the effective stored policy for this deployment."""
    # Read through the provider so JSON and MySQL share one code path.
    stored = get_storage_provider().read_document(POLICY_DOCUMENT_KEY, environment_baseline)
    # Normalize whatever came back so a hand-edited document cannot bypass validation.
    return normalize(stored)


# Resolve the concrete capability booleans the rest of the application asks about.
def capabilities() -> dict:
    """Return the effective enrollment capabilities implied by the current policy.

    Keeping this derivation in one place ensures current signup and invitation enforcement cannot
    drift from what the public endpoint advertises.
    """
    # Resolve the policy once so every derived value describes the same state.
    policy = current()
    # Read the mode that gates every route below.
    mode = policy["mode"]
    # Allow public email signup only in self-signup mode with the method enabled.
    signup_enabled = mode == MODE_SELF_SIGNUP and policy["methods"]["email"] is True
    # Allow invitation redemption in either non-closed mode while the capability is retained.
    invitation_enrollment_enabled = mode != MODE_CLOSED and policy["invitations_enabled"] is True
    # Return the derived capabilities alongside the policy that produced them.
    return {
        # Publish the mode so a client can explain why a control is unavailable.
        "mode": mode,
        # Publish public email signup availability.
        "signup_enabled": signup_enabled,
        # Publish invitation enrollment availability.
        "invitation_enrollment_enabled": invitation_enrollment_enabled,
        # Publish the per-method flags without exposing environment names or operator settings.
        "methods": dict(policy["methods"]),
    }


# Collapse one caller-supplied value into an exact reviewed vocabulary.
def _reviewed(value, allowed: frozenset[str], fallback: str) -> str:
    # Accept only exact built-in strings so hostile objects cannot control comparison or formatting.
    if type(value) is str and value in allowed:
        # Return the reviewed low-cardinality value unchanged.
        return value
    # Replace arbitrary, oversized, multiline, secret-like, or unknown values with one fixed label.
    return fallback


# Forward one bounded operational enrollment decision to the existing JSONL logger.
def _audit(event, **fields) -> None:
    """Emit one value-bounded operational record, never an immutable actor/change audit."""
    # Ignore the caller event and always emit the sole reviewed enrollment event name.
    safe_event = AUDIT_EVENT
    # Collapse the route before it can reach the operational log.
    safe_fields = {"route": _reviewed(fields.get("route"), AUDIT_ROUTES, "unknown")}
    # Collapse the mode to the closed baseline when a hostile direct caller supplies an unknown value.
    safe_fields["mode"] = _reviewed(fields.get("mode"), AUDIT_MODES, MODE_CLOSED)
    # Collapse an unknown decision to denial so malformed audit input can never describe permission.
    safe_fields["decision"] = _reviewed(fields.get("decision"), AUDIT_DECISIONS, "denied")
    # Collapse an unknown reason to the fixed unknown-route refusal.
    safe_fields["reason"] = _reviewed(fields.get("reason"), AUDIT_REASONS, "unknown_route")
    # Include a method only when the decision path supplied one.
    if fields.get("method") is not None:
        # Collapse arbitrary method material to one reviewed value.
        safe_fields["method"] = _reviewed(fields.get("method"), AUDIT_METHODS, "unknown")
    # Start a fixed failure boundary so logger details cannot escape into a public route.
    try:
        # Write the bounded record before any governed enrollment mutation may start.
        logger.info(safe_event, **safe_fields)
    # Normalize every sink failure to one fixed local exception.
    except Exception:
        # Hide exception text, paths, record values, and logger implementation details.
        raise EnrollmentAuditError("Enrollment decision logging is unavailable") from None


# Decide whether one governed enrollment route may proceed and record the exact decision first.
def evaluate(route) -> dict:
    """Return one bounded signup or invitation decision after its operational log succeeds."""
    # Resolve one coherent policy snapshot for both enforcement and operational logging.
    resolved = capabilities()
    # Read the closed-vocabulary mode from the normalized policy.
    mode = resolved["mode"]
    # Reject every unreviewed route without reflecting its caller-supplied value.
    if type(route) is not str or route not in (ROUTE_SIGNUP, ROUTE_INVITATION):
        # Record only the fixed unknown route label.
        _audit(AUDIT_EVENT, route="unknown", mode=mode, decision="denied", reason="unknown_route")
        # Return only fixed reviewed values to the internal caller.
        return {"allowed": False, "reason": "unknown_route", "mode": mode}
    # Deny both routes while restricted-preview enrollment is closed.
    if mode == MODE_CLOSED:
        # Record the fixed mode-level refusal before returning.
        _audit(AUDIT_EVENT, route=route, mode=mode, decision="denied", reason="mode_closed")
        # Preserve the reviewed mode and reason without exposing stored policy fields.
        return {"allowed": False, "reason": "mode_closed", "mode": mode}
    # Evaluate invitation redemption independently from public signup methods.
    if route == ROUTE_INVITATION:
        # Deny redemption when the normalized invitation capability is not exactly enabled.
        if resolved["invitation_enrollment_enabled"] is not True:
            # Record the fixed capability refusal before returning.
            _audit(AUDIT_EVENT, route=route, mode=mode, decision="denied", reason="invitations_disabled")
            # Preserve only the reviewed reason and mode.
            return {"allowed": False, "reason": "invitations_disabled", "mode": mode}
        # Record the allowed redemption before the route may inspect or consume a bearer.
        _audit(AUDIT_EVENT, route=route, mode=mode, decision="allowed", reason="allowed")
        # Allow the existing invitation service to retain its generic envelopes and lifecycle.
        return {"allowed": True, "reason": "allowed", "mode": mode}
    # Deny public email signup outside the explicit self-signup mode.
    if mode != MODE_SELF_SIGNUP:
        # Record the truthful invite-only refusal with only the reviewed email-method label.
        _audit(AUDIT_EVENT, route=route, mode=mode, method="email", decision="denied", reason="self_signup_disabled")
        # Preserve only the reviewed reason and mode.
        return {"allowed": False, "reason": "self_signup_disabled", "mode": mode}
    # Deny public email signup unless its strict method flag is enabled.
    if resolved["methods"]["email"] is not True:
        # Record the fixed method refusal before account validation or creation.
        _audit(AUDIT_EVENT, route=route, mode=mode, method="email", decision="denied", reason="method_disabled")
        # Preserve only the reviewed reason and mode.
        return {"allowed": False, "reason": "method_disabled", "mode": mode}
    # Record the allowed signup before any identity or session mutation begins.
    _audit(AUDIT_EVENT, route=route, mode=mode, method="email", decision="allowed", reason="allowed")
    # Allow the existing signup route to retain its request validation and response contract.
    return {"allowed": True, "reason": "allowed", "mode": mode}
