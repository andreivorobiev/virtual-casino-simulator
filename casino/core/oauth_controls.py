"""Durable external-provider operational kill switches. (OAUTH-012)

Signup method flags decide whether a new account may be created.  These switches are deliberately
separate: they decide whether an already-linked Google or Facebook identity may start or finish an
OAuth exchange.  Both switches default off, use the configured storage provider, require an
optimistic owner transaction, and retain a hash-linked privacy-safe audit.
"""

# Import detached copying so callers cannot alias provider-owned documents.
import copy
# Import hashing for deterministic audit-chain identities.
import hashlib
# Import canonical JSON encoding for stable digests.
import json

# Import the shared UTC clock for durable audit timestamps.
from casino.core.clock import utc_now
# Import opaque identifiers for immutable audit rows.
from casino.core.ids import new_id
# Import the configured JSON/MySQL storage boundary.
from casino.core.storage import get_storage_provider
# Import stable request errors for malformed and stale owner changes.
from casino.errors import ConflictError, ValidationError

# Name the provider-neutral durable document.
DOCUMENT_KEY = "auth/oauth_operational_controls"
# Version the exact stored shape.
SCHEMA_VERSION = 1
# Publish the only providers governed by this release.
PROVIDERS = ("google", "facebook")
# Bound retained security-control evidence without silently truncating it.
MAX_AUDIT_ROWS = 4096
# Seed the immutable chain with one fixed non-record digest.
AUDIT_GENESIS_DIGEST = "0" * 64


# Return the default-off restricted-preview document.
def _default_document() -> dict:
    # Keep every provider disabled until an owner change passes the separate release gate.
    return {"schema_version": SCHEMA_VERSION, "revision": 0, "providers": {provider: False for provider in PROVIDERS}, "audit": []}


# Encode one JSON-shaped value deterministically before hashing it.
def _digest(value) -> str:
    # Serialize stable keys and separators without locale-sensitive output.
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    # Return one lowercase SHA-256 identity.
    return hashlib.sha256(encoded).hexdigest()


# Validate one complete provider document without repairing malformed security state.
def _valid_document(value) -> bool:
    # Require the exact top-level security-control fields.
    if not isinstance(value, dict) or set(value) != {"schema_version", "revision", "providers", "audit"}:
        # Reject missing, extra, or non-object state.
        return False
    # Require this release's exact non-boolean schema and revision markers.
    if type(value.get("schema_version")) is not int or value["schema_version"] != SCHEMA_VERSION or type(value.get("revision")) is not int or value["revision"] < 0:
        # Fail closed on old, future, string, boolean, or negative markers.
        return False
    # Require exactly one strict boolean for each reviewed provider.
    if not isinstance(value.get("providers"), dict) or set(value["providers"]) != set(PROVIDERS) or any(type(value["providers"][provider]) is not bool for provider in PROVIDERS):
        # Reject partial, extended, or truthy-alias provider controls.
        return False
    # Require a bounded append-only audit collection.
    if not isinstance(value.get("audit"), list) or len(value["audit"]) > MAX_AUDIT_ROWS:
        # Preserve malformed or oversized evidence for operator recovery.
        return False
    # Start verification at the fixed genesis marker.
    previous_digest = AUDIT_GENESIS_DIGEST
    # Verify every retained row in committed order.
    for row in value["audit"]:
        # Require one exact privacy-safe audit shape.
        if not isinstance(row, dict) or set(row) != {"audit_id", "actor_id", "reason", "at", "previous", "current", "revision", "previous_digest", "digest"}:
            # Reject unknown or incomplete evidence.
            return False
        # Require bounded opaque metadata and the exact chain predecessor.
        if any(not isinstance(row.get(field), str) or not row[field] or len(row[field]) > 256 or any(not character.isprintable() for character in row[field]) for field in ("audit_id", "actor_id", "reason", "at")) or row.get("previous_digest") != previous_digest:
            # Reject unbounded, control-bearing, or discontinuous rows.
            return False
        # Require strict before/after provider maps and a positive exact revision.
        if any(not isinstance(row.get(field), dict) or set(row[field]) != set(PROVIDERS) or any(type(row[field][provider]) is not bool for provider in PROVIDERS) for field in ("previous", "current")) or type(row.get("revision")) is not int or row["revision"] < 1:
            # Reject unverifiable transition evidence.
            return False
        # Rebuild the immutable payload without its self-digest.
        payload = {key: row[key] for key in row if key != "digest"}
        # Require the exact deterministic self-digest.
        if row.get("digest") != _digest(payload):
            # Reject tampered evidence.
            return False
        # Advance the expected chain head.
        previous_digest = row["digest"]
    # Require the document revision to equal the append-only transition count.
    if value["revision"] != len(value["audit"]):
        # Reject an ABA-prone or partially committed document.
        return False
    # Accept the complete strict document.
    return True


# Read one verified detached operational-control snapshot.
def current() -> dict:
    # Resolve the active provider without caching process-local state.
    provider = get_storage_provider()
    # Read strictly so corrupt controls never become implicit enablement.
    document = provider.read_document_strict(DOCUMENT_KEY, _default_document, _valid_document)
    # Return a detached copy safe for callers and response serialization.
    return copy.deepcopy(document)


# Return whether one exact external provider is operationally enabled.
def enabled(provider: str) -> bool:
    # Reject local and unknown provider names by returning the secure default.
    if provider not in PROVIDERS:
        # Keep unreviewed providers unavailable.
        return False
    # Resolve the durable switch on every request so rollback needs no restart.
    return current()["providers"][provider] is True


# Validate a sparse provider-switch change without accepting future fields.
def _validated_changes(changes) -> dict:
    # Require one object keyed only by reviewed providers.
    if not isinstance(changes, dict) or not changes or set(changes) - set(PROVIDERS):
        # Fail closed on missing, scalar, or unknown-provider input.
        raise ValidationError("OAuth operational changes are invalid")
    # Require strict booleans rather than truthy aliases.
    if any(type(value) is not bool for value in changes.values()):
        # Preserve an unambiguous mutation contract.
        raise ValidationError("OAuth operational values must be booleans")
    # Return one detached sparse update.
    return dict(changes)


# Preview a sparse switch change without writing provider state.
def propose(changes) -> dict:
    # Validate every caller field before reading current controls.
    validated = _validated_changes(changes)
    # Read one coherent verified current document.
    before = current()
    # Copy the strict provider map for a proposed result.
    after = dict(before["providers"])
    # Apply only the reviewed sparse booleans.
    after.update(validated)
    # Report exact changed providers and lockout impact without credentials.
    changed = [provider for provider in PROVIDERS if before["providers"][provider] != after[provider]]
    # Return the revision-bound preview used by the confirmed apply route.
    return {"revision": before["revision"], "previous": dict(before["providers"]), "providers": after, "impact": {"providers_changed": changed, "existing_login_disabled": [provider for provider in changed if after[provider] is False]}}


# Commit one confirmed owner change with optimistic concurrency and immutable audit.
def update(changes, *, actor_id, reason, expected_revision) -> dict:
    # Validate sparse provider booleans before storage access.
    validated = _validated_changes(changes)
    # Normalize bounded human and opaque actor evidence.
    actor = str(actor_id or "").strip()
    # Normalize the required owner reason without logging it elsewhere.
    why = str(reason or "").strip()
    # Require bounded printable, single-line evidence and a non-boolean revision.
    if not actor or len(actor) > 160 or any(not character.isprintable() for character in actor) or not why or len(why) > 256 or any(not character.isprintable() for character in why) or any(character in why for character in "\r\n") or type(expected_revision) is not int or expected_revision < 0:
        # Reject ambiguous audit and concurrency input before mutation.
        raise ValidationError("OAuth operational change metadata is invalid")
    # Capture the committed response outside the provider transaction.
    result = {"value": None}
    # Resolve the configured provider once for the atomic document update.
    provider = get_storage_provider()

    # Define one complete transition under the provider lock.
    def mutate(document) -> dict:
        # Require the same strict shape used by reads.
        if not _valid_document(document):
            # Preserve malformed durable security state for operator recovery.
            raise RuntimeError("OAuth operational controls require operator recovery")
        # Reject stale previews before computing or appending a transition.
        if document["revision"] != expected_revision:
            # Publish only the safe current revision needed to re-preview.
            raise ConflictError("OAuth operational control revision is stale", {"revision": document["revision"]})
        # Snapshot the exact prior provider switches.
        previous = dict(document["providers"])
        # Apply only reviewed sparse provider booleans.
        document["providers"].update(validated)
        # Reject no-op audit spam as a stale operator action.
        if document["providers"] == previous:
            # Require the caller to refresh its intended transition.
            raise ConflictError("OAuth operational controls are unchanged", {"revision": document["revision"]})
        # Advance the exact optimistic revision.
        document["revision"] += 1
        # Resolve the preceding immutable chain digest.
        previous_digest = document["audit"][-1]["digest"] if document["audit"] else AUDIT_GENESIS_DIGEST
        # Build the privacy-safe transition payload.
        payload = {"audit_id": new_id("oauthaudit"), "actor_id": actor, "reason": why, "at": utc_now(), "previous": previous, "current": dict(document["providers"]), "revision": document["revision"], "previous_digest": previous_digest}
        # Attach the deterministic self-digest after every payload field is final.
        row = {**payload, "digest": _digest(payload)}
        # Append the immutable transition under the same lock as the switches.
        document["audit"].append(row)
        # Refuse unbounded evidence growth without truncating history.
        if len(document["audit"]) > MAX_AUDIT_ROWS:
            # Abort the provider transaction for operator recovery.
            raise RuntimeError("OAuth operational control audit retention requires operator recovery")
        # Capture one detached committed response.
        result["value"] = {"revision": document["revision"], "previous": previous, "providers": dict(document["providers"]), "audit": dict(row)}
        # Return the complete strict document for atomic persistence.
        return document

    # Commit through the JSON/MySQL-neutral provider transaction.
    provider.update_document(DOCUMENT_KEY, mutate, _default_document)
    # Return the exact committed transition.
    return result["value"]
