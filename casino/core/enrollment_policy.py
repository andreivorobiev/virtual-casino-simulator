"""Durable enrollment policy resolution and owner change control. (AUTH-013, AUTH-014)

Enrollment was governed only by process environment variables read once at import
(`casino/config.py` SIGNUP_ENABLED / INVITATIONS_ENABLED / ENROLLMENT_ENABLED), so changing who may
join required an operator to edit the environment and restart. This module introduces the durable
policy document those flags become the seed for.

The resolved policy reproduces the environment baseline exactly when no stored document exists.
Public signup and invitation redemption enforce that same resolved policy, and each decision is
written to the existing operational JSONL log before either route may mutate enrollment state.
Platform-owner policy changes use one provider transaction that commits the policy beside a
hash-linked actor/change audit. Readiness, UI, and provider enablement remain separate work.

The policy is read through the active StorageProvider so JSON and MySQL share one durable document
boundary. This slice adds no provider configuration and never changes production policy on its own.
"""

# Import deep copying so returned audit and policy snapshots cannot alias provider-owned state.
import copy
# Import ISO timestamp parsing for durable audit verification.
from datetime import datetime
# Import hashing for the provider-backed append-only actor/change audit chain.
import hashlib
# Import canonical JSON encoding for deterministic audit digests.
import json

# Import the configuration flags that seed the policy so the default stays the deployed behaviour.
from casino import config
# Import the storage provider accessor so the document uses the active backend.
from casino.core.storage import get_storage_provider
# Import the existing JSONL logger for bounded operational enrollment-decision records.
from casino.core import logger
# Import the shared production clock for durable audit timestamps.
from casino.core.clock import utc_now
# Import opaque identifiers for provider-backed audit rows.
from casino.core.ids import new_id
# Import stable validation and conflict envelopes for malformed and stale owner requests.
from casino.errors import ConflictError, ValidationError

# Name the durable document so both providers agree on one canonical key.
POLICY_DOCUMENT_KEY = "auth/enrollment_policy"

# Name the provider-private append-only audit collection stored beside the governed policy.
CHANGE_AUDIT_FIELD = "change_audit"

# Version the stored shape so a later slice can migrate it without guessing.
SCHEMA_VERSION = 1

# Version the immutable audit-row shape independently from the policy document.
CHANGE_AUDIT_VERSION = 1

# Bound operator reasons so no arbitrary, multiline, or secret-sized value enters durable audit.
MAX_CHANGE_REASON_LENGTH = 256

# Bound opaque actor identifiers to the current canonical identity width with defensive headroom.
MAX_CHANGE_ACTOR_LENGTH = 160

# Bound retained audit growth without silently deleting immutable prior actor/change evidence.
MAX_CHANGE_AUDIT_ENTRIES = 4096

# Seed the first hash-linked audit entry with one fixed non-record digest.
CHANGE_AUDIT_GENESIS_DIGEST = "0" * 64

# Enumerate the exact governed policy fields returned for application rollback.
POLICY_FIELDS = ("schema_version", "mode", "methods", "invitations_enabled")

# Enumerate the exact immutable audit fields before the self-digest is added.
CHANGE_AUDIT_PAYLOAD_FIELDS = ("audit_version", "audit_id", "actor_id", "reason", "at", "previous", "current", "impact", "previous_digest")

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


# Build the complete default provider document without mutating the environment baseline object.
def _document_default() -> dict:
    # Resolve the current deployed fallback once for the absent-document transaction seed.
    document = environment_baseline()
    # Start the provider-backed actor/change history empty for a newly materialized document.
    document[CHANGE_AUDIT_FIELD] = []
    # Return one complete document that the provider may persist inside its transaction.
    return document


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


# Validate one exact canonical policy snapshot used by rollback and immutable audit evidence.
def _owned_policy(candidate) -> dict:
    # Require a mapping with no missing or extra durable policy fields.
    if not isinstance(candidate, dict) or set(candidate) != set(POLICY_FIELDS):
        # Reject malformed snapshots before they can enter an audit record or rollback request.
        raise ValidationError("enrollment policy document is invalid")
    # Require this release's exact non-boolean schema marker.
    if type(candidate.get("schema_version")) is not int or candidate["schema_version"] != SCHEMA_VERSION:
        # Refuse old, future, string, and boolean policy snapshots.
        raise ValidationError("enrollment policy document schema is invalid")
    # Require one reviewed closed-vocabulary mode.
    if type(candidate.get("mode")) is not str or candidate["mode"] not in MODES:
        # Keep the error value-free while naming the legal vocabulary.
        raise ValidationError(f"enrollment mode must be one of: {', '.join(MODES)}")
    # Require every method exactly once so rollback cannot inherit environment drift.
    methods = candidate.get("methods")
    # Reject absent, extra, or partial method collections.
    if not isinstance(methods, dict) or set(methods) != set(METHODS):
        # Name the fixed legal collection without echoing an arbitrary caller key.
        raise ValidationError(f"enrollment methods must be exactly: {', '.join(METHODS)}")
    # Require exact booleans for every independently governed method.
    if any(type(methods[method]) is not bool for method in METHODS):
        # Reject truthy strings and integer aliases instead of silently disabling them.
        raise ValidationError("enrollment method values must be booleans")
    # Require an exact boolean for invitation enrollment.
    if type(candidate.get("invitations_enabled")) is not bool:
        # Reject truthy aliases before durable mutation.
        raise ValidationError("invitations_enabled must be a boolean")
    # Return a detached canonical snapshot in stable field order.
    return {
        # Preserve the exact owned schema marker.
        "schema_version": SCHEMA_VERSION,
        # Preserve the validated mode.
        "mode": candidate["mode"],
        # Copy each exact method boolean.
        "methods": {method: methods[method] for method in METHODS},
        # Preserve the strict invitation capability.
        "invitations_enabled": candidate["invitations_enabled"],
    }


# Canonically digest one JSON-shaped audit payload without locale or spacing ambiguity.
def _digest(value) -> str:
    # Encode keys and separators deterministically before hashing.
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    # Return a lowercase SHA-256 identity suitable for the fixed audit contract.
    return hashlib.sha256(encoded).hexdigest()


# Validate one stored document shape while preserving legacy unowned-schema fallback.
def _policy_document_shape(value) -> bool:
    # Preserve AUTH-013 compatibility for legacy non-mapping documents.
    if not isinstance(value, dict):
        # Let normalize apply the deployed environment fallback without interpreting fields.
        return True
    # Read the exact schema marker before applying owned-shape validation.
    stored_schema_version = value.get("schema_version")
    # Preserve fallback for absent, boolean, old, future, or otherwise unowned schemas.
    if type(stored_schema_version) is not int or stored_schema_version != SCHEMA_VERSION:
        # Let normalize ignore every field in a shape this release does not own.
        return True
    # Allow only the canonical policy fields and optional actor/change history.
    allowed_fields = set(POLICY_FIELDS) | {CHANGE_AUDIT_FIELD}
    # Reject missing policy fields or arbitrary owned-schema additions.
    if set(value) not in (set(POLICY_FIELDS), allowed_fields):
        # Fail closed instead of normalizing malformed owned state.
        return False
    # Start protected canonical validation without disclosing stored values.
    try:
        # Require every owned policy field and exact scalar/container type.
        _owned_policy({field: value[field] for field in POLICY_FIELDS})
    # Collapse the public field validator into the provider-owned strict shape result.
    except (KeyError, ValidationError):
        # Reject malformed schema-owned state before normalization.
        return False
    # Require any present audit envelope to use the expected collection type.
    if CHANGE_AUDIT_FIELD in value and not isinstance(value[CHANGE_AUDIT_FIELD], list):
        # Defer detailed row verification only after this strict envelope check.
        return False
    # Accept the complete owned shape for detailed audit verification.
    return True


# Derive one provider-neutral revision from canonical policy and verified audit position.
def _revision(policy: dict, audit_rows: list[dict]) -> str:
    # Bind the current canonical policy plus audit count and head so ABA changes advance revision.
    material = {
        # Include the complete exact rollback-ready policy.
        "policy": _owned_policy(policy),
        # Include the verified append-only history length.
        "audit_count": len(audit_rows),
        # Include the verified head digest or fixed genesis for legacy documents.
        "audit_head": audit_rows[-1]["digest"] if audit_rows else CHANGE_AUDIT_GENESIS_DIGEST,
    }
    # Return a deterministic non-secret lowercase SHA-256 revision.
    return _digest(material)


# Validate one caller preview revision without reflecting hostile material.
def _expected_revision(value) -> str:
    # Require exactly one lowercase full SHA-256 string.
    if type(value) is not str or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        # Refuse missing, uppercase, short, boolean, and arbitrary revision values.
        raise ValidationError("enrollment policy revision is invalid")
    # Return the canonical revision unchanged.
    return value


# Validate one bounded printable operator field without reflecting hostile material.
def _bounded_text(value, *, field: str, maximum: int) -> str:
    # Accept only a built-in string so hostile objects cannot control normalization.
    if type(value) is not str:
        # Return one fixed field-level error.
        raise ValidationError(f"enrollment policy {field} is invalid")
    # Trim boundary whitespace while preserving the reviewed human reason content.
    normalized = value.strip()
    # Reject empty, oversized, newline, control, and other non-printable material.
    if not normalized or len(normalized) > maximum or any(not character.isprintable() for character in normalized):
        # Return no caller material in the failure.
        raise ValidationError(f"enrollment policy {field} is invalid")
    # Return the bounded printable value.
    return normalized


# Validate one canonical opaque platform-owner account identifier.
def _owner_actor(value) -> str:
    # Apply the shared printable and length boundary first.
    actor_id = _bounded_text(value, field="actor", maximum=MAX_CHANGE_ACTOR_LENGTH)
    # Split the canonical identifier prefix from its fixed lowercase hexadecimal suffix.
    suffix = actor_id.removeprefix("user_")
    # Require the exact identity shape issued by the canonical account service.
    if not actor_id.startswith("user_") or len(suffix) != 16 or any(character not in "0123456789abcdef" for character in suffix):
        # Refuse arbitrary caller material before durable audit mutation.
        raise ValidationError("enrollment policy actor is invalid")
    # Return the canonical opaque user identifier.
    return actor_id


# Validate and detach the immutable provider-backed change audit from one raw policy document.
def _change_audit_from_document(document) -> list[dict]:
    # Treat a legacy canonical policy document as having no prior actor/change entries.
    if not isinstance(document, dict) or CHANGE_AUDIT_FIELD not in document:
        # Preserve pre-slice policy compatibility without inventing an audit event.
        return []
    # Read the provider-backed collection without defaulting malformed state.
    rows = document.get(CHANGE_AUDIT_FIELD)
    # Require a bounded list so malformed or unbounded audit state is never normalized away.
    if not isinstance(rows, list) or len(rows) > MAX_CHANGE_AUDIT_ENTRIES:
        # Preserve the original provider document for operator recovery.
        raise RuntimeError("Enrollment policy audit requires operator recovery")
    # Start verification at the fixed genesis digest.
    previous_digest = CHANGE_AUDIT_GENESIS_DIGEST
    # Retain the prior committed policy for exact append-only continuity checks.
    prior_current = None
    # Build a detached result only from fully verified rows.
    verified = []
    # Verify every immutable entry in stored order.
    for row in rows:
        # Require the complete fixed-shape payload plus its digest and no arbitrary fields.
        if not isinstance(row, dict) or set(row) != set((*CHANGE_AUDIT_PAYLOAD_FIELDS, "digest")):
            # Refuse visibility or mutation while the sole audit evidence is malformed.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Require the exact non-boolean audit schema marker.
        if type(row.get("audit_version")) is not int or row["audit_version"] != CHANGE_AUDIT_VERSION:
            # Preserve unknown audit versions for a later governed recovery.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Require one bounded provider-issued audit identifier.
        audit_id = row.get("audit_id")
        # Split the fixed provider namespace from its opaque lowercase hexadecimal suffix.
        audit_suffix = audit_id.removeprefix("enrollaudit_") if type(audit_id) is str else ""
        # Reject arbitrary identifiers or malformed prefixes without reflecting them.
        if type(audit_id) is not str or not audit_id.startswith("enrollaudit_") or len(audit_suffix) != 16 or any(character not in "0123456789abcdef" for character in audit_suffix):
            # Fail closed on an unverifiable audit identity.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Revalidate actor and reason through the same bounded contract used at creation.
        try:
            # Require a bounded opaque actor identifier.
            actor_id = _owner_actor(row.get("actor_id"))
            # Require a bounded printable operator reason.
            reason = _bounded_text(row.get("reason"), field="change reason", maximum=MAX_CHANGE_REASON_LENGTH)
            # Require exact canonical previous policy evidence.
            previous = _owned_policy(row.get("previous"))
            # Require exact canonical committed policy evidence.
            current_policy = _owned_policy(row.get("current"))
        # Collapse public validation categories into one operator-recovery boundary for durable state.
        except ValidationError:
            # Preserve the malformed row exactly as stored.
            raise RuntimeError("Enrollment policy audit requires operator recovery") from None
        # Require a bounded printable timestamp without accepting arbitrary structured values.
        at = row.get("at")
        # Enforce the shared UTC clock's compact ISO shape.
        if type(at) is not str or len(at) > 40 or not at.endswith("Z") or any(not character.isprintable() for character in at):
            # Refuse an unverifiable event time.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Parse the UTC instant so arbitrary printable text ending in Z cannot satisfy the contract.
        try:
            # Convert the canonical UTC suffix for the standard-library parser.
            parsed_at = datetime.fromisoformat(at[:-1] + "+00:00")
        # Preserve malformed timestamps as operator-recovery evidence.
        except ValueError:
            # Refuse the complete audit rather than normalizing its timestamp.
            raise RuntimeError("Enrollment policy audit requires operator recovery") from None
        # Require an explicit UTC offset after parsing.
        if parsed_at.utcoffset() is None or parsed_at.utcoffset().total_seconds() != 0:
            # Refuse a non-UTC audit instant.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Recompute the exact impact rather than trusting stored derived fields.
        expected_impact = impact(previous, current_policy)
        # Require the stored impact to equal the canonical capability computation.
        if row.get("impact") != expected_impact:
            # Preserve evidence when its declared effect no longer verifies.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Require each row to point to the exact preceding verified digest.
        if row.get("previous_digest") != previous_digest:
            # Refuse reordered, removed, or spliced audit rows.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Require each row after the first to begin at the prior committed policy.
        if prior_current is not None and previous != prior_current:
            # Refuse a broken actor/change sequence even if individual hashes were recomputed.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Rebuild the exact digest payload in reviewed field order.
        payload = {field: copy.deepcopy(row[field]) for field in CHANGE_AUDIT_PAYLOAD_FIELDS}
        # Require a lowercase full SHA-256 digest over the immutable payload.
        if type(row.get("digest")) is not str or row["digest"] != _digest(payload):
            # Refuse content tampering, short writes, or digest substitution.
            raise RuntimeError("Enrollment policy audit requires operator recovery")
        # Append one detached verified entry for safe caller inspection.
        verified.append(copy.deepcopy(row))
        # Advance the hash chain.
        previous_digest = row["digest"]
        # Advance the expected policy continuity.
        prior_current = current_policy
        # Keep local normalized values referenced so direct mutation of row aliases cannot matter.
        _ = (actor_id, reason)
    # Require the durable policy to equal the last audited committed state.
    if verified and normalize(document) != verified[-1]["current"]:
        # Refuse policy replacement that bypassed the owner transaction.
        raise RuntimeError("Enrollment policy audit requires operator recovery")
    # Return only the detached verified history.
    return verified


# Strictly read and verify one coherent provider policy document.
def _policy_state() -> tuple[object, dict, dict, list[dict], str]:
    # Resolve the active provider once so read and later caller decisions share one abstraction.
    provider = get_storage_provider()
    # Distinguish a missing document from corrupt bytes or a non-object stored value.
    document = provider.read_document_strict(POLICY_DOCUMENT_KEY, _document_default, _policy_document_shape)
    # Normalize the retained legacy policy compatibility shape.
    policy = _owned_policy(normalize(document))
    # Verify every present actor/change row and its binding to the durable policy.
    audit_rows = _change_audit_from_document(document)
    # Return the provider, detached state, and deterministic ABA-safe revision.
    return provider, document, policy, audit_rows, _revision(policy, audit_rows)


# Read the durable policy, falling back to the environment baseline when none is stored.
def current() -> dict:
    """Return the effective stored policy for this deployment."""
    # Strictly read and verify the policy before public capability resolution.
    _, _, policy, _, _ = _policy_state()
    # Return one detached canonical policy.
    return policy


# Read one coherent owner-visible policy, capabilities, and verified audit snapshot.
def owner_view() -> dict:
    # Strictly read one coherent policy, audit, and ABA-safe revision.
    _, _, policy, audit_rows, revision = _policy_state()
    # Return detached owner-facing state and fixed vocabularies.
    return {
        # Publish the exact rollback-ready policy.
        "policy": policy,
        # Publish capabilities derived from that same policy.
        "capabilities": _capabilities_for(policy),
        # Publish the legal modes for a future separately governed UI.
        "modes": list(MODES),
        # Publish the independently governed method names.
        "methods": list(METHODS),
        # Publish only fully verified provider-backed audit rows.
        "audit": audit_rows,
        # Publish the exact revision required by a confirmed apply.
        "revision": revision,
    }


# Derive capabilities from one already canonical policy snapshot.
def _capabilities_for(policy: dict) -> dict:
    # Require a complete canonical snapshot so preview and apply cannot use partial semantics.
    canonical = _owned_policy(policy)
    # Read the mode that gates every route below.
    mode = canonical["mode"]
    # Allow public email signup only in self-signup mode with the method enabled.
    signup_enabled = mode == MODE_SELF_SIGNUP and canonical["methods"]["email"] is True
    # Allow invitation redemption in either non-closed mode while the capability is retained.
    invitation_enrollment_enabled = mode != MODE_CLOSED and canonical["invitations_enabled"] is True
    # Return the derived capabilities alongside the policy that produced them.
    return {
        # Publish the mode so a client can explain why a control is unavailable.
        "mode": mode,
        # Publish public email signup availability.
        "signup_enabled": signup_enabled,
        # Publish invitation enrollment availability.
        "invitation_enrollment_enabled": invitation_enrollment_enabled,
        # Publish the per-method flags without exposing environment names or operator settings.
        "methods": dict(canonical["methods"]),
    }


# Resolve the concrete capability booleans the rest of the application asks about.
def capabilities() -> dict:
    """Return the effective enrollment capabilities implied by the current policy.

    Keeping this derivation in one place ensures current signup, invitation enforcement, owner
    preview, and committed effect cannot drift from what the public endpoint advertises.
    """
    # Resolve the policy once so every derived value describes the same state.
    policy = current()
    # Use the shared pure derivation also used by preview and apply.
    return _capabilities_for(policy)


# Validate only the supported partial policy fields accepted by owner preview and apply.
def _validated_changes(changes) -> dict:
    # Require a JSON object instead of coercing arbitrary caller values.
    if not isinstance(changes, dict):
        # Refuse malformed request shape before provider access.
        raise ValidationError("enrollment policy change must be an object")
    # Reject any field outside the governed policy shape.
    if set(changes) - {"mode", "methods", "invitations_enabled"}:
        # Refuse smuggled role, readiness, provider, or other control fields.
        raise ValidationError("enrollment policy change contains unsupported fields")
    # Start one detached validated change collection.
    validated = {}
    # Validate a supplied mode against the closed vocabulary.
    if "mode" in changes:
        # Require an exact built-in string from the reviewed mode set.
        if type(changes["mode"]) is not str or changes["mode"] not in MODES:
            # Name only the legal modes.
            raise ValidationError(f"enrollment mode must be one of: {', '.join(MODES)}")
        # Retain the reviewed mode.
        validated["mode"] = changes["mode"]
    # Validate any supplied per-method changes.
    if "methods" in changes:
        # Require an object so lists and scalar aliases cannot be silently ignored.
        if not isinstance(changes["methods"], dict):
            # Return a fixed request-shape diagnostic.
            raise ValidationError("enrollment methods must be an object")
        # Reject unknown provider or method names without reflecting them.
        if set(changes["methods"]) - set(METHODS):
            # Name only the legal methods.
            raise ValidationError(f"enrollment methods must be among: {', '.join(METHODS)}")
        # Require exact booleans for every supplied method.
        if any(type(value) is not bool for value in changes["methods"].values()):
            # Reject truthy strings and integer aliases.
            raise ValidationError("enrollment method values must be booleans")
        # Detach the validated sparse method update.
        validated["methods"] = dict(changes["methods"])
    # Validate a supplied invitation capability.
    if "invitations_enabled" in changes:
        # Require an exact boolean rather than a truthy alias.
        if type(changes["invitations_enabled"]) is not bool:
            # Return one fixed field diagnostic.
            raise ValidationError("invitations_enabled must be a boolean")
        # Retain the strict invitation capability.
        validated["invitations_enabled"] = changes["invitations_enabled"]
    # Return one detached validated update.
    return validated


# Convert one exact prior-policy response into a complete application rollback change.
def changes_for_policy(policy) -> dict:
    # Validate the response document through the exact owned policy schema.
    canonical = _owned_policy(policy)
    # Return only fields accepted by the shared proposal function.
    return {
        # Restore the prior mode.
        "mode": canonical["mode"],
        # Restore every prior method flag without environment fallback.
        "methods": dict(canonical["methods"]),
        # Restore the prior invitation capability.
        "invitations_enabled": canonical["invitations_enabled"],
    }


# Compute a proposed canonical policy and its exact resolved capability impact.
def propose(changes, *, previous: dict | None = None) -> dict:
    """Return the policy and capability effect that both preview and apply use."""
    # Validate all caller-controlled fields before reading or mutating provider state.
    validated = _validated_changes(changes)
    # Strictly read the current policy and revision for an owner preview.
    if previous is None:
        # Resolve one audit-verified current state without any provider write.
        _, _, before, _, revision = _policy_state()
    # Validate the exact transaction-owned prior policy during apply.
    else:
        # Detach the exact prior policy supplied by the locked provider transaction.
        before = _owned_policy(previous)
        # Omit revision when the locked apply caller already owns and checks it.
        revision = None
    # Copy the complete prior policy so omitted fields remain exact.
    proposed = copy.deepcopy(before)
    # Apply a supplied mode.
    if "mode" in validated:
        # Replace only the governed mode.
        proposed["mode"] = validated["mode"]
    # Apply sparse method flags.
    if "methods" in validated:
        # Visit only reviewed method names present in the request.
        for method, enabled in validated["methods"].items():
            # Replace one strict method boolean.
            proposed["methods"][method] = enabled
    # Apply a supplied invitation capability.
    if "invitations_enabled" in validated:
        # Replace only the strict invitation boolean.
        proposed["invitations_enabled"] = validated["invitations_enabled"]
    # Revalidate the complete result as an exact rollback-ready snapshot.
    canonical = _owned_policy(proposed)
    # Return both exact states and their shared pure capability calculation.
    result = {"previous": before, "policy": canonical, "impact": impact(before, canonical)}
    # Publish the strict current revision only for a caller-visible preview.
    if revision is not None:
        # Bind apply to the exact policy and audit position used for this preview.
        result["revision"] = revision
    # Return the complete proposal.
    return result


# Summarize only resolved capability changes for operator confirmation.
def impact(previous: dict, proposed: dict) -> dict:
    """Return the exact capability differences between two canonical policies."""
    # Derive the previous public and invitation capabilities.
    before = _capabilities_for(previous)
    # Derive the proposed capabilities through the same pure function.
    after = _capabilities_for(proposed)
    # Record only top-level capability fields that change.
    changed = sorted(key for key in ("mode", "signup_enabled", "invitation_enrollment_enabled") if before[key] != after[key])
    # Record each independently governed method whose raw flag changes.
    method_changes = sorted(method for method in METHODS if before["methods"][method] != after["methods"][method])
    # Return a deterministic identifier-free impact summary.
    return {"changed": changed, "methods_changed": method_changes, "before": before, "after": after}


# Return the verified provider-backed owner actor/change audit.
def change_audit() -> list[dict]:
    # Strictly read and verify the complete policy state.
    _, _, _, audit_rows, _ = _policy_state()
    # Return the detached verified history.
    return audit_rows


# Apply one validated owner change and append its immutable audit inside the same provider transaction.
def update(changes, *, actor_id, reason, expected_revision) -> dict:
    """Commit policy plus actor/change evidence atomically and return exact rollback state."""
    # Validate caller changes before provider access.
    validated = _validated_changes(changes)
    # Validate the opaque canonical owner identifier without accepting control characters.
    actor = _owner_actor(actor_id)
    # Validate the nonempty bounded operator reason before provider access.
    explanation = _bounded_text(reason, field="change reason", maximum=MAX_CHANGE_REASON_LENGTH)
    # Validate the caller's preview revision before provider access.
    preview_revision = _expected_revision(expected_revision)
    # Resolve the provider once for strict preflight and the locked update.
    provider = get_storage_provider()
    # Refuse malformed bytes without backup creation before entering the mutation seam.
    provider.read_document_strict(POLICY_DOCUMENT_KEY, _document_default, _policy_document_shape)
    # Capture the exact committed result from inside the provider transaction.
    outcome = {}
    # Mutate policy and audit under the provider's cross-process document boundary.
    def mutate(document):
        # Verify every prior immutable audit entry before considering a new mutation.
        audit_rows = _change_audit_from_document(document)
        # Resolve the exact policy currently committed beside the verified history.
        previous = _owned_policy(normalize(document))
        # Recompute the ABA-safe current revision inside the provider-owned transaction.
        current_revision = _revision(previous, audit_rows)
        # Reject a stale preview before proposal computation, audit allocation, or document mutation.
        if current_revision != preview_revision:
            # Disclose no alternate current state through the standard conflict envelope.
            raise ConflictError("Enrollment policy preview is stale")
        # Refuse to delete immutable history when the governed capacity is exhausted.
        if len(audit_rows) >= MAX_CHANGE_AUDIT_ENTRIES:
            # Preserve the complete document for an explicit later retention decision.
            raise RuntimeError("Enrollment policy audit capacity requires operator recovery")
        # Compute the proposal through the exact same function used by preview.
        proposal = propose(validated, previous=previous)
        # Build the immutable provider-backed audit payload.
        payload = {
            # Bind the exact audit schema.
            "audit_version": CHANGE_AUDIT_VERSION,
            # Allocate one opaque event identity.
            "audit_id": new_id("enrollaudit"),
            # Record only the canonical opaque owner identity.
            "actor_id": actor,
            # Record the bounded printable reason.
            "reason": explanation,
            # Record the shared UTC event instant.
            "at": utc_now(),
            # Preserve the exact pre-transaction policy for rollback and review.
            "previous": copy.deepcopy(previous),
            # Preserve the exact committed policy.
            "current": copy.deepcopy(proposal["policy"]),
            # Preserve the shared capability impact computation.
            "impact": copy.deepcopy(proposal["impact"]),
            # Link this entry to the preceding immutable audit row.
            "previous_digest": audit_rows[-1]["digest"] if audit_rows else CHANGE_AUDIT_GENESIS_DIGEST,
        }
        # Add the deterministic self-digest after the complete payload is fixed.
        entry = {**payload, "digest": _digest(payload)}
        # Build the complete provider document from the canonical policy.
        updated_document = copy.deepcopy(proposal["policy"])
        # Append without truncating, replacing, or reordering prior immutable entries.
        updated_document[CHANGE_AUDIT_FIELD] = [*audit_rows, entry]
        # Derive the revision a later exact rollback must present.
        next_revision = _revision(proposal["policy"], updated_document[CHANGE_AUDIT_FIELD])
        # Publish a detached result only after every validation step succeeds.
        outcome.update({"previous": copy.deepcopy(previous), "previous_revision": current_revision, "current": copy.deepcopy(proposal["policy"]), "revision": next_revision, "impact": copy.deepcopy(proposal["impact"]), "audit": copy.deepcopy(entry)})
        # Persist policy and audit in one provider transaction.
        return updated_document
    # Execute the complete read/validate/append/write through the active JSON or MySQL provider.
    provider.update_document(POLICY_DOCUMENT_KEY, mutate, _document_default, _policy_document_shape)
    # Return the exact detached transaction receipt.
    return outcome


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
def evaluate(route, method: str = "email") -> dict:
    """Return one bounded method-specific signup or invitation decision after logging succeeds."""
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
    # Reject unknown signup methods through one bounded operational decision.
    if type(method) is not str or method not in METHODS:
        # Record only the fixed unknown method label before returning.
        _audit(AUDIT_EVENT, route=route, mode=mode, method="unknown", decision="denied", reason="method_disabled")
        # Preserve only the reviewed reason and mode.
        return {"allowed": False, "reason": "method_disabled", "mode": mode}
    # Deny public signup outside the explicit self-signup mode.
    if mode != MODE_SELF_SIGNUP:
        # Record the truthful invite-only refusal with only the reviewed method label.
        _audit(AUDIT_EVENT, route=route, mode=mode, method=method, decision="denied", reason="self_signup_disabled")
        # Preserve only the reviewed reason and mode.
        return {"allowed": False, "reason": "self_signup_disabled", "mode": mode}
    # Deny public signup unless its strict method flag is enabled.
    if resolved["methods"][method] is not True:
        # Record the fixed method refusal before account validation or creation.
        _audit(AUDIT_EVENT, route=route, mode=mode, method=method, decision="denied", reason="method_disabled")
        # Preserve only the reviewed reason and mode.
        return {"allowed": False, "reason": "method_disabled", "mode": mode}
    # Record the allowed signup before any identity or session mutation begins.
    _audit(AUDIT_EVENT, route=route, mode=mode, method=method, decision="allowed", reason="allowed")
    # Allow the existing signup route to retain its request validation and response contract.
    return {"allowed": True, "reason": "allowed", "mode": mode}
