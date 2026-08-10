"""Owner-controlled administrator grants, revocations, and privacy-safe audit history. (#351)"""

# Import hashing for replay keys and the immutable audit chain.
import hashlib
# Import canonical JSON encoding for deterministic request and audit digests.
import json

# Import the canonical identity/session authority rather than duplicating account logic.
from casino.core import auth
# Import the shared UTC clock for durable audit timestamps.
from casino.core.clock import utc_now
# Import opaque identifiers for audit rows.
from casino.core.ids import new_id
# Import the provider-neutral atomic document boundary.
from casino.core.state_store import update_json
# Import stable application errors for stale, invalid, and forbidden requests.
from casino.errors import ConflictError, ForbiddenError, ValidationError

# Version the role-control section embedded in the canonical identity document.
ROLE_STATE_VERSION = 1
# Seed the first audit row with a fixed non-record digest.
AUDIT_GENESIS_DIGEST = "0" * 64
# Bound retained immutable audit history on the single-node restricted preview.
MAX_AUDIT_ROWS = 4096
# Bound replay receipts while preserving recent deterministic retries.
MAX_RECEIPTS = 4096
# Bound owner reasons so secrets or large payloads cannot enter role audit.
MAX_REASON_LENGTH = 256


# Return the empty role-control state used when upgrading an existing identity document.
def _default_role_state() -> dict:
    # Keep revision, immutable audit, and replay receipts under one provider transaction.
    return {"schema_version": ROLE_STATE_VERSION, "revision": 0, "audit": [], "receipts": {}}


# Validate or materialize the role-control section without normalizing malformed evidence.
def _role_state(state: dict) -> dict:
    # Materialize only an absent section so older valid identity documents upgrade compatibly.
    if "admin_roles" not in state:
        # Attach the reviewed empty state under the current identity transaction.
        state["admin_roles"] = _default_role_state()
    # Read the candidate section after optional materialization.
    role_state = state.get("admin_roles")
    # Require the exact owned object shape before any privileged mutation or list response.
    if not isinstance(role_state, dict) or role_state.get("schema_version") != ROLE_STATE_VERSION or type(role_state.get("revision")) is not int or not isinstance(role_state.get("audit"), list) or not isinstance(role_state.get("receipts"), dict):
        # Preserve malformed bytes for operator recovery rather than silently replacing them.
        raise RuntimeError("Administrator role storage requires operator recovery")
    # Return the validated provider-owned mapping.
    return role_state


# Build one canonical SHA-256 digest from a JSON-safe mapping.
def _digest(payload: dict) -> str:
    # Serialize with fixed ordering and separators so JSON and MySQL workers agree exactly.
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    # Return the lowercase digest without retaining any password or credential.
    return hashlib.sha256(encoded).hexdigest()


# Return the bounded account projection used by the separate Administrators surface.
def _public_account(user: dict) -> dict:
    # Publish only fields already visible in canonical Admin user management plus role metadata.
    return {
        "user_id": str(user.get("user_id") or ""),
        "display_name": str(user.get("display_name") or ""),
        "email": str(user.get("email") or ""),
        "status": str(user.get("status") or "inactive"),
        "roles": auth.roles_for_user(user),
        "role_version": int(user.get("role_version", 0)),
        "protected_owner": auth.PLATFORM_OWNER_ROLE in auth.roles_for_user(user),
    }


# Resolve the actor from current durable state rather than trusting a stale session snapshot.
def _owner_from_state(state: dict, actor_id: str) -> dict:
    # Find one exact canonical account under the same transaction used for role decisions.
    actor = next((user for user in state.get("users", []) if user.get("user_id") == actor_id), None)
    # Require current active owner authority before revealing or mutating role-control state.
    auth.require_platform_owner(actor or {})
    # Return the current canonical owner record.
    return actor


# List current administrators, eligible accounts, and the global optimistic revision.
def listing(actor: dict) -> dict:
    # Require owner authority at the service boundary for direct tests and non-HTTP callers.
    auth.require_platform_owner(actor or {})
    # Load the canonical identity document through the configured storage provider.
    state = auth.load_users()
    # Re-resolve owner authority from durable state so revoked sessions gain no stale access.
    _owner_from_state(state, str((actor or {}).get("user_id") or ""))
    # Validate the role-control section before returning any management data.
    role_state = _role_state(state)
    # Exclude disposable guests and malformed identities from the eligible account list.
    accounts = [user for user in state.get("users", []) if not auth.is_guest(user) and user.get("status") == "active"]
    # Publish current administrators in stable display order.
    administrators = sorted((_public_account(user) for user in accounts if auth.is_admin(user)), key=lambda row: (row["display_name"].lower(), row["user_id"]))
    # Publish only active non-Admin accounts as grant candidates.
    eligible = sorted((_public_account(user) for user in accounts if not auth.is_admin(user)), key=lambda row: (row["display_name"].lower(), row["user_id"]))
    # Return one bounded owner-only management projection.
    return {"revision": role_state["revision"], "administrators": administrators, "eligible_accounts": eligible}


# Read the privacy-safe immutable role audit in newest-first order.
def audit_history(actor: dict, *, limit: int = 100) -> dict:
    # Require owner authority before reading privilege-change history.
    auth.require_platform_owner(actor or {})
    # Clamp the requested list bound to the published one-through-two-hundred range.
    bounded_limit = max(1, min(int(limit), 200))
    # Load the canonical identity document through the provider-neutral boundary.
    state = auth.load_users()
    # Re-resolve the current actor before exposing audit metadata.
    _owner_from_state(state, str((actor or {}).get("user_id") or ""))
    # Validate the role-control section and return detached recent rows.
    role_state = _role_state(state)
    # Reverse a bounded copy so callers cannot mutate provider-owned state.
    rows = [dict(row) for row in role_state["audit"][-bounded_limit:]][::-1]
    # Return the current revision with the bounded history.
    return {"revision": role_state["revision"], "audit": rows}


# Apply one owner-confirmed administrator grant or revocation atomically.
def change(actor: dict, target_user_id: str, action: str, body: dict) -> dict:
    # Require the exact reviewed action vocabulary.
    if action not in {"grant", "revoke"}:
        # Reject future or malformed action names before account lookup.
        raise ValidationError("Administrator role action is invalid")
    # Require one field-allowlisted object so callers cannot smuggle role or account state.
    if not isinstance(body, dict) or set(body) != {"password", "reason", "idempotency_key", "revision"}:
        # Fail closed before reauthentication or persistence.
        raise ValidationError("Administrator role request contains unsupported fields")
    # Normalize the opaque target id without accepting an empty selector.
    target_id = str(target_user_id or "").strip()
    # Normalize and bound the human owner reason.
    reason = str(body.get("reason") or "").strip()
    # Normalize the caller-owned idempotency key without persisting it in plaintext.
    idempotency_key = str(body.get("idempotency_key") or "").strip()
    # Read the current optimistic revision as an exact integer.
    revision = body.get("revision")
    # Reject empty or overlong target ids.
    if not target_id or len(target_id) > 160:
        # Keep the validation message enumeration-safe.
        raise ValidationError("Administrator role target is invalid")
    # Require a concise explicit reason for every privilege mutation.
    if not reason or len(reason) > MAX_REASON_LENGTH or any(character in reason for character in "\r\n"):
        # Reject secrets-sized or multiline audit input.
        raise ValidationError("Administrator role reason is invalid")
    # Require a bounded caller key with enough entropy for deterministic retry handling.
    if len(idempotency_key) < 16 or len(idempotency_key) > 200 or any(character in idempotency_key for character in "\r\n"):
        # Reject unusable replay keys without reflecting them.
        raise ValidationError("Administrator role idempotency key is invalid")
    # Require a non-negative integer revision and reject booleans explicitly.
    if type(revision) is not int or revision < 0:
        # Return one stable optimistic-concurrency diagnostic.
        raise ValidationError("Administrator role revision is invalid")
    # Read the transient step-up password without storing or hashing it into audit fields.
    password = str(body.get("password") or "")
    # Bind the actor id from the authenticated context only.
    actor_id = str((actor or {}).get("user_id") or "")
    # Hash the replay lookup independently from request content.
    receipt_key = _digest({"actor_id": actor_id, "idempotency_key": idempotency_key})
    # Hash only non-secret request semantics for changed-key conflict detection.
    request_digest = _digest({"actor_id": actor_id, "target_user_id": target_id, "action": action, "reason": reason, "revision": revision})
    # Capture the committed result for the caller after persistence succeeds.
    outcome = {"result": None, "changed": False}

    # Define the complete identity-and-role-control mutation under one provider transaction.
    def mutate(state: dict) -> dict:
        # Reject malformed identity storage before privilege inspection.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve recoverable evidence rather than replacing it.
            raise RuntimeError("Authentication user storage is malformed")
        # Resolve the current durable owner under the transaction.
        current_actor = _owner_from_state(state, actor_id)
        # Require local-password step-up and fail closed for provider-only owners.
        if str(current_actor.get("identity_provider") or "local") != "local" or not auth.verify_password(password, str(current_actor.get("password_hash") or "")):
            # Reveal no account or verifier detail.
            raise ForbiddenError("Recent owner reauthentication is required")
        # Prevent self-targeting even though platform-owner authority itself is immutable here.
        if target_id == actor_id:
            # Keep personal settings and privilege delegation separate.
            raise ForbiddenError("Administrator role self-action is not allowed")
        # Validate or materialize the role-control section.
        role_state = _role_state(state)
        # Return an exact prior result for a byte-equivalent retry.
        existing_receipt = role_state["receipts"].get(receipt_key)
        # Handle a previously committed caller key deterministically.
        if existing_receipt is not None:
            # Reject the key when its non-secret request semantics changed.
            if not isinstance(existing_receipt, dict) or existing_receipt.get("request_digest") != request_digest:
                # Preserve the committed first action.
                raise ConflictError("Administrator role idempotency key was already used")
            # Return a detached replay result without another audit row or session revocation.
            outcome["result"] = dict(existing_receipt.get("result") or {})
            # Leave durable state unchanged.
            return state
        # Reject stale writes before resolving or mutating the target.
        if revision != role_state["revision"]:
            # Publish only the current safe revision needed for a fresh confirmation.
            raise ConflictError("Administrator role revision is stale", {"revision": role_state["revision"]})
        # Resolve the exact target without exposing whether another identifier exists.
        target = next((user for user in state["users"] if user.get("user_id") == target_id), None)
        # Require one active durable non-guest account.
        if not target or target.get("status") != "active" or auth.is_guest(target):
            # Collapse missing, inactive, and guest targets into one bounded result.
            raise ValidationError("Administrator role target is unavailable")
        # Protect bootstrap owner authority from every ordinary role action.
        if auth.PLATFORM_OWNER_ROLE in auth.roles_for_user(target):
            # Preserve the immutable owner recovery path.
            raise ForbiddenError("Platform owner role cannot be changed")
        # Snapshot the target's normalized pre-change role collection.
        before_roles = auth.roles_for_user(target)
        # Reject duplicate grants and revocations unless they are exact receipt replays.
        if (action == "grant" and "admin" in before_roles) or (action == "revoke" and "admin" not in before_roles):
            # Force callers to reconcile current state instead of fabricating success.
            raise ConflictError("Administrator role transition is no longer applicable", {"revision": role_state["revision"]})
        # Build the compatible post-change role collection without platform-owner scope.
        after_roles = [role for role in before_roles if role != "admin"]
        # Add ordinary Admin access for a grant while retaining player membership.
        if action == "grant":
            # Append the reviewed privilege exactly once.
            after_roles.append("admin")
        # Preserve ordinary player identity when revoking the only compatible Admin marker.
        if not after_roles:
            # Restore the canonical least-privilege role.
            after_roles = ["player"]
        # Remove duplicates while preserving deterministic order.
        after_roles = list(dict.fromkeys(after_roles))
        # Commit canonical plural and compatible singular role fields together.
        target["roles"] = after_roles
        # Prefer Admin as the legacy primary role only while it remains granted.
        target["role"] = "admin" if "admin" in after_roles else after_roles[0]
        # Increment the target-local role version for operator inspection.
        target["role_version"] = int(target.get("role_version", 0)) + 1
        # Stamp the canonical identity update time.
        target["updated_at"] = utc_now()
        # Increment the global role-control revision after the exact transition.
        role_state["revision"] += 1
        # Resolve the previous immutable audit digest or the fixed genesis marker.
        previous_digest = str(role_state["audit"][-1].get("digest") if role_state["audit"] else AUDIT_GENESIS_DIGEST)
        # Build the bounded immutable audit payload without password, email, or idempotency key.
        audit_payload = {"audit_id": new_id("role_audit"), "actor_id": actor_id, "target_user_id": target_id, "action": action, "reason": reason, "at": utc_now(), "before_roles": before_roles, "after_roles": after_roles, "revision": role_state["revision"], "previous_digest": previous_digest}
        # Attach the deterministic self-digest after every payload field is final.
        audit_row = {**audit_payload, "digest": _digest(audit_payload)}
        # Append the immutable row inside the same transaction as the role mutation.
        role_state["audit"].append(audit_row)
        # Refuse unbounded growth rather than silently deleting privilege evidence.
        if len(role_state["audit"]) > MAX_AUDIT_ROWS:
            # Preserve the complete original document by aborting the transaction.
            raise RuntimeError("Administrator role audit retention requires operator recovery")
        # Build the stable response returned for first commit and exact replay.
        result = {"revision": role_state["revision"], "action": action, "administrator": _public_account(target), "audit_id": audit_row["audit_id"], "replayed": False}
        # Store only digests and the safe response for deterministic retry handling.
        role_state["receipts"][receipt_key] = {"request_digest": request_digest, "result": result, "committed_at": audit_row["at"]}
        # Refuse unbounded receipt growth rather than guessing which replay guarantee to drop.
        if len(role_state["receipts"]) > MAX_RECEIPTS:
            # Preserve the complete original document for operator recovery.
            raise RuntimeError("Administrator role receipt retention requires operator recovery")
        # Publish a detached committed response to the outer caller.
        outcome["result"] = dict(result)
        # Record that post-commit session invalidation is required exactly once.
        outcome["changed"] = True
        # Preserve the canonical identity schema marker.
        state["schema_version"] = auth.SCHEMA_VERSION
        # Return the complete document for provider persistence.
        return state

    # Persist the role transition atomically through the configured JSON/MySQL provider.
    update_json(auth.USERS_PATH, mutate, auth.default_users)
    # Revoke every existing target session after a newly committed privilege transition.
    if outcome["changed"]:
        # Force fresh authentication so no browser retains pre-change privilege context.
        auth.revoke_sessions_for_user(target_id)
    # Mark exact receipt replays explicitly without changing the stored canonical result.
    if outcome["result"] and not outcome["changed"]:
        # Copy before adjusting the response-only replay marker.
        outcome["result"] = {**outcome["result"], "replayed": True}
    # Return the committed or replayed safe response.
    return outcome["result"]
