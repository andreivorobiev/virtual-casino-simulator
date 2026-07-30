"""Durable, concurrency-safe enrollment policy resolution. (issue #333, slice 1)

Enrollment was governed only by process environment variables read once at import
(`casino/config.py` SIGNUP_ENABLED / INVITATIONS_ENABLED / ENROLLMENT_ENABLED), so changing who may
join required an operator to edit the environment and restart. This module introduces the durable
policy document those flags become the seed for.

Slice 1 is read-path only and deliberately behaviour-preserving: with no stored document the
resolved policy reproduces the environment baseline exactly, so the public endpoint publishes the
same values it published before. Later slices add enforcement, audit, the least-privilege
permission, readiness gating, and the Admin surface.

The policy is stored through StorageProvider.update_document, which owns read-modify-write
concurrency on both providers (JSON takes a cross-process sidecar lock; MySQL locks the document
row inside a transaction), so two Admins cannot interleave a change.
"""

# Import the configuration flags that seed the policy so the default stays the deployed behaviour.
from casino import config
# Import the storage provider accessor so the document uses the active backend.
from casino.core.storage import get_storage_provider
# Import the application log facade so enrollment decisions reach the audit trail.
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


# Restrict audit fields so no email, token, or credential material can be logged accidentally.
# This mirrors the allowlist convention in casino/core/one_time_tokens.py. (issue #333, slice 2)
AUDIT_FIELDS = frozenset({"route", "mode", "method", "decision", "reason", "actor_id", "previous_mode", "changed"})

# Enumerate the internal decision reasons so logs stay useful without becoming caller-visible state.
AUDIT_REASONS = frozenset({"allowed", "mode_closed", "method_disabled", "invitations_disabled", "unknown_route", "policy_changed", "policy_unchanged"})

# Name each governed enrollment route so a typo cannot silently bypass the policy.
ROUTE_SIGNUP = "signup"
# Redemption of an Admin invitation.
ROUTE_INVITATION = "invitation"
# Starting a provider sign-up flow.
ROUTE_OAUTH = "oauth"

# Map each governed route to the self-signup method it consumes, where one applies.
ROUTE_METHODS = {ROUTE_SIGNUP: "email"}


# Forward one sanitized enrollment decision to the application audit log.
def _audit(event: str, **fields) -> None:
    # Retain only explicitly approved non-secret audit keys.
    safe_fields = {key: value for key, value in fields.items() if key in AUDIT_FIELDS}
    # Collapse any unexpected internal reason so an unreviewed string cannot reach the log.
    if "reason" in safe_fields and safe_fields["reason"] not in AUDIT_REASONS:
        # Replace an unrecognized reason with the generic unknown-route category.
        safe_fields["reason"] = "unknown_route"
    # Emit through the standard info facade; enrollment decisions are operational, not errors.
    logger.info(event, **safe_fields)


# Decide whether one enrollment route may proceed, and record why either way.
def evaluate(route: str, *, method: str | None = None) -> dict:
    """Return the decision for ``route`` and emit exactly one audit event.

    Every governed enrollment entry point calls this instead of reading a flag, so the decision that
    is enforced and the decision that is audited can never disagree.
    """
    # Resolve the capabilities once so the decision and the audit describe the same state.
    resolved = capabilities()
    # Read the mode that gates every route.
    mode = resolved["mode"]
    # Resolve which self-signup method this route consumes, preferring an explicit caller override.
    consumed = method or ROUTE_METHODS.get(route)
    # Reject a route this release does not govern rather than silently allowing it.
    if route not in (ROUTE_SIGNUP, ROUTE_INVITATION, ROUTE_OAUTH):
        # Record the refusal so an unrouted caller is visible in the audit trail.
        _audit("enrollment_decision", route=route, mode=mode, decision="denied", reason="unknown_route")
        # Deny by default because an unknown route has no reviewed policy.
        return {"allowed": False, "reason": "unknown_route", "mode": mode}
    # Close every enrollment route while the mode is closed.
    if mode == MODE_CLOSED:
        # Record the mode-level refusal.
        _audit("enrollment_decision", route=route, mode=mode, method=consumed, decision="denied", reason="mode_closed")
        # Deny without disclosing which specific prerequisite is missing.
        return {"allowed": False, "reason": "mode_closed", "mode": mode}
    # Gate invitation redemption on the retained invitation capability.
    if route == ROUTE_INVITATION:
        # Refuse when invitations are not live even though the mode is open.
        if resolved["invitation_enrollment_enabled"] is not True:
            # Record the capability-level refusal.
            _audit("enrollment_decision", route=route, mode=mode, decision="denied", reason="invitations_disabled")
            # Deny invitation redemption.
            return {"allowed": False, "reason": "invitations_disabled", "mode": mode}
        # Record the allowed redemption.
        _audit("enrollment_decision", route=route, mode=mode, decision="allowed", reason="allowed")
        # Allow invitation redemption.
        return {"allowed": True, "reason": "allowed", "mode": mode}
    # Every remaining route consumes a public self-signup method, which requires self-signup mode.
    if mode != MODE_SELF_SIGNUP:
        # Record that a public method was attempted outside self-signup mode.
        _audit("enrollment_decision", route=route, mode=mode, method=consumed, decision="denied", reason="mode_closed")
        # Deny the public method.
        return {"allowed": False, "reason": "mode_closed", "mode": mode}
    # Require the specific method to be enabled, so enabling one provider never enables another.
    if not consumed or resolved["methods"].get(consumed) is not True:
        # Record the method-level refusal.
        _audit("enrollment_decision", route=route, mode=mode, method=consumed, decision="denied", reason="method_disabled")
        # Deny the disabled method.
        return {"allowed": False, "reason": "method_disabled", "mode": mode}
    # Record the allowed public enrollment.
    _audit("enrollment_decision", route=route, mode=mode, method=consumed, decision="allowed", reason="allowed")
    # Allow the public method.
    return {"allowed": True, "reason": "allowed", "mode": mode}


# Summarize what a proposed policy would change, so an operator confirms an effect not a payload.
def impact(previous: dict, proposed: dict) -> dict:
    """Return the human-meaningful differences between two resolved policies."""
    # Compare the resolved capabilities rather than the raw documents, because the capabilities are
    # what actually gates a route: a mode change with no capability change is not worth confirming.
    before = _capabilities_for(previous)
    # Resolve the proposed capabilities the same way.
    after = _capabilities_for(proposed)
    # Collect only the fields that genuinely differ.
    changed = sorted(key for key in ("mode", "signup_enabled", "invitation_enrollment_enabled") if before[key] != after[key])
    # Report each method whose availability would flip.
    method_changes = sorted(method for method in METHODS if before["methods"][method] != after["methods"][method])
    # Return a compact, identifier-free summary.
    return {"changed": changed, "methods_changed": method_changes, "before": before, "after": after}


# Derive capabilities from an already-resolved policy without re-reading storage.
def _capabilities_for(policy: dict) -> dict:
    # Read the mode that gates every route.
    mode = policy["mode"]
    # Apply the same derivation the live resolver uses so preview and effect cannot diverge.
    return {
        # Publish the mode.
        "mode": mode,
        # Public email signup requires self-signup mode and the enabled method.
        "signup_enabled": mode == MODE_SELF_SIGNUP and policy["methods"]["email"] is True,
        # Invitation redemption requires a non-closed mode and the retained capability.
        "invitation_enrollment_enabled": mode != MODE_CLOSED and policy["invitations_enabled"] is True,
        # Publish the per-method flags.
        "methods": dict(policy["methods"]),
    }


# Apply an owner-authorized policy change atomically and record it.
def update(changes: dict, *, actor_id: str, reason: str) -> dict:
    """Persist ``changes`` over the current policy and return the previous state for rollback.

    The caller must already have proved platform-owner authority; this function owns validation,
    atomicity, and the audit record, not authorization.
    """
    # Require a non-empty operator reason so every change carries accountability.
    if not isinstance(reason, str) or not reason.strip():
        # Fail closed rather than recording an unexplained policy change.
        raise ValidationError("enrollment policy change requires a reason")
    # Reject any field outside the governed policy shape so nothing can be smuggled in.
    if set(changes or {}) - {"mode", "methods", "invitations_enabled"}:
        # Fail closed through the standard validation envelope.
        raise ValidationError("enrollment policy change contains unsupported fields")
    # Reject an unknown method key before the mutator runs, so a typo cannot be silently dropped.
    if isinstance((changes or {}).get("methods"), dict):
        # Compare the supplied method names against the declared set.
        if set(changes["methods"]) - set(METHODS):
            # Name the legal methods without echoing the rejected key.
            raise ValidationError(f"enrollment methods must be among: {', '.join(METHODS)}")
    # Capture the state being replaced so the caller can roll back to exactly it.
    previous = current()
    # Hold a box for the resolved proposal so it survives the mutator closure.
    resolved = {}

    # Merge the change over whatever is durably stored, inside the provider's lock.
    def mutate(stored):
        # Normalize the stored document first so a hand-edited file cannot widen the merge.
        base = normalize(stored)
        # Overlay the requested mode when supplied.
        merged = dict(base)
        # Copy the methods mapping so the base is never mutated in place.
        merged["methods"] = dict(base["methods"])
        # Apply each supported field that the caller supplied.
        for field in ("mode", "invitations_enabled"):
            # Only touch a field the caller actually sent.
            if field in (changes or {}):
                # Stage the raw value; normalize below performs the validation and coercion.
                merged[field] = changes[field]
        # Apply method flags individually so an omitted method keeps its current value.
        for method, value in ((changes or {}).get("methods") or {}).items():
            # Stage the raw value for normalization.
            merged["methods"][method] = value
        # Validate and coerce the merged result, raising on an unknown mode before anything persists.
        validated = normalize(merged)
        # Publish the resolved proposal to the enclosing scope.
        resolved.update(validated)
        # Return the document to persist.
        return validated

    # Persist through the provider primitive that owns read-modify-write concurrency on both backends.
    get_storage_provider().update_document(POLICY_DOCUMENT_KEY, mutate, environment_baseline)
    # Describe the effect of the change for the operator and the audit trail.
    summary = impact(previous, resolved)
    # Record the change with the actor, the previous mode, and which capabilities moved.
    _audit(
        "enrollment_policy_changed",
        actor_id=actor_id,
        mode=resolved["mode"],
        previous_mode=previous["mode"],
        changed=",".join(summary["changed"] + summary["methods_changed"]) or "none",
        decision="applied",
        reason="policy_changed" if (summary["changed"] or summary["methods_changed"]) else "policy_unchanged",
    )
    # Return both states plus the summary so the caller can present and reverse the change.
    return {"previous": previous, "current": resolved, "impact": summary}
