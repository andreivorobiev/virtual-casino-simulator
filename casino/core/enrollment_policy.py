"""Durable, concurrency-safe enrollment policy resolution. (AUTH-013)

Enrollment was governed only by process environment variables read once at import
(`casino/config.py` SIGNUP_ENABLED / INVITATIONS_ENABLED / ENROLLMENT_ENABLED), so changing who may
join required an operator to edit the environment and restart. This module introduces the durable
policy document those flags become the seed for.

Slice 1 is read-path only and deliberately behaviour-preserving: with no stored document the
resolved policy reproduces the environment baseline exactly, so the public endpoint publishes the
same values it published before. Later slices add enforcement, audit, the least-privilege
permission, readiness gating, and the Admin surface.

The policy is read through the active StorageProvider so JSON and MySQL share one durable document
boundary. This slice exposes no application or Admin write path, and it never enables a method on
its own.
"""

# Import the configuration flags that seed the policy so the default stays the deployed behaviour.
from casino import config
# Import the storage provider accessor so the document uses the active backend.
from casino.core.storage import get_storage_provider
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


# Derive the environment baseline that the deployed release already behaves as.
def environment_baseline() -> dict:
    """Return the policy the current environment flags describe.

    This is the seed and the fallback. It must reproduce today's behaviour exactly, because slice 1
    ships with no Admin write path: every deployment resolves to this until an operator stores a
    document in a later slice.
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

    Keeping this derivation in one place means enforcement in the next slice cannot drift from what
    the public endpoint advertises.
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
