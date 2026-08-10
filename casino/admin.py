# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import numeric finiteness checks so malformed ledger amounts cannot poison Admin economics.
import math
# Import required dependency so this module can use its public functions or constants.
import secrets
# Import timestamp parsing for bounded Guest Trials Admin filters.
from datetime import datetime, timezone
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, GAME_DATA_DIR, LOG_DIR, DOCS_DIR, APP_VERSION, PASSWORD_RESET_ENABLED
# Import required dependency so this module can use its public functions or constants.
from casino.module_versions import list_module_revisions
# Import required dependency so this module can use its public functions or constants.
from casino.core import admin_roles, auth, players, ledger, history, logger, autoplay, feedback, settings, enrollment_policy, session_settings, rate_settings, guest_settings, mail
# Import secret-safe provider diagnostics without constructing a provider adapter or network transport.
from casino.core.oauth.api import provider_diagnostic_payload
# Import the de-identified guest-trial telemetry for the Admin Guest Trials section. (issue #317)
from casino.core import guest_analytics
# Import the invitation lifecycle for the Admin invitation-by-email section. (issue #332)
from casino.core import invitations
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json
# Import the provider visibility boundary for direct game-state tree inspection.
from casino.core.storage import get_storage_provider
# Import required dependency so this module can use its public functions or constants.
from casino.bots import profiles, practice_opponents
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ForbiddenError, NotFoundError, ValidationError

# Set REQ_PATH to the value needed for the next operation.
REQ_PATH = DOCS_DIR / "requirements.json"
# Set TEST_RESULTS_PATH to the value needed for the next operation.
TEST_RESULTS_PATH = LOG_DIR / "test-runs" / "latest_results.json"
# Set ADMIN_USERS_PATH to the value needed for the next operation.
ADMIN_USERS_PATH = DATA_DIR / "admin_users.json"
# Enumerate product-approved account lifecycle states for Admin-visible accounts.
ACCOUNT_STATUSES = frozenset({"active", "inactive", "suspended", "locked"})
# Enumerate product-approved roles; Guest Trial markers are never valid Admin account roles.
ACCOUNT_ROLES = frozenset({"player", "admin"})

# Parse one bounded Guest Trials list limit for v2 Admin routes.
def _guest_limit(value) -> int:
    # Start protected parsing so malformed query text receives a validation envelope.
    try:
        # Clamp valid integers to the contract's one-through-one-hundred range.
        return max(1, min(int(value or 25), 100))
    # Convert type and numeric failures into the public validation error.
    except (TypeError, ValueError):
        # Reject arbitrary text without echoing it into logs or responses.
        raise ValidationError("Guest trial limit must be an integer from 1 to 100")

# Validate the complete low-cardinality Guest Trials filter contract.
def _guest_filters(query: dict) -> dict:
    # Read each optional string without echoing it in any error message.
    locale = str(query.get("locale") or "")
    # Read the coarse device class.
    device = str(query.get("device") or "")
    # Read the lifecycle state.
    status = str(query.get("status") or "")
    # Read the registered catalog game slug.
    game = str(query.get("game") or "")
    # Read the first-round completion selector.
    completed = str(query.get("completed") or "")
    # Read the sanitized server error category.
    error_category = str(query.get("error_category") or "")
    # Reject any unsupported locale before analytics filtering.
    if locale and locale not in guest_analytics.ALLOWED_LOCALES:
        # Return a fixed diagnostic without reflecting query text.
        raise ValidationError("Guest trial locale filter is invalid")
    # Reject any unsupported device class.
    if device and device not in guest_analytics.ALLOWED_DEVICES:
        # Return a fixed diagnostic without reflecting query text.
        raise ValidationError("Guest trial device filter is invalid")
    # Reject any unsupported lifecycle state.
    if status and status not in guest_analytics.ALLOWED_STATUSES:
        # Return a fixed diagnostic without reflecting query text.
        raise ValidationError("Guest trial status filter is invalid")
    # Require game slugs to remain exact normalized catalog-style keys.
    if game and guest_analytics._game(game) != game:
        # Return a fixed diagnostic without reflecting query text.
        raise ValidationError("Guest trial game filter is invalid")
    # Reject unsupported completion selectors.
    if completed and completed not in guest_analytics.ALLOWED_COMPLETION_FILTERS:
        # Return a fixed diagnostic without reflecting query text.
        raise ValidationError("Guest trial completion filter is invalid")
    # Reject arbitrary exception categories.
    if error_category and error_category not in guest_analytics.ALLOWED_ERROR_CATEGORIES:
        # Return a fixed diagnostic without reflecting query text.
        raise ValidationError("Guest trial error filter is invalid")
    # Parse one optional ISO timestamp into the canonical UTC string form.
    def timestamp(name: str) -> str:
        # Read the selected time bound.
        value = str(query.get(name) or "")
        # Preserve an omitted bound.
        if not value:
            # Return the empty filter value.
            return ""
        # Start protected parsing so malformed dates become a standard validation envelope.
        try:
            # Parse a Z suffix through the standard offset format.
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # Require an explicit timezone so server locale never changes filter meaning.
            if parsed.tzinfo is None:
                # Raise into the fixed validation path.
                raise ValueError("timezone required")
            # Normalize to UTC with the repository's shared Z spelling.
            return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        # Replace every parsing failure with a fixed public diagnostic.
        except (TypeError, ValueError):
            # Name only the governed filter, never its supplied value.
            raise ValidationError(f"Guest trial {name} filter must be an ISO timestamp with timezone")
    # Parse the inclusive lower bound.
    since = timestamp("since")
    # Parse the inclusive upper bound.
    until = timestamp("until")
    # Reject a reversed time range deterministically.
    if since and until and datetime.fromisoformat(since.replace("Z", "+00:00")) > datetime.fromisoformat(until.replace("Z", "+00:00")):
        # Return a fixed ordering diagnostic.
        raise ValidationError("Guest trial since filter must not be after until")
    # Return the exact analytics-service arguments and bounded list limit.
    return {"recent_limit": _guest_limit(query.get("limit")), "locale": locale, "device": device, "status": status, "game": game, "completed": completed, "error_category": error_category, "since": since, "until": until}


# Define the _read_json_file function used by this module.
def _read_json_file(path: Path, default):
    # Start protected logic so failures can be handled safely.
    try:
        # Branch when the following condition is true.
        if path.exists():
            # Return the computed value to the caller.
            return json.loads(path.read_text(encoding="utf-8"))
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Intentionally leave this block empty.
        pass
    # Return the computed value to the caller.
    return default


# Define the _default_admin_users function used by this module.
def _default_admin_users():
    # Return the empty user-management state used before beta accounts exist.
    return {"schema_version": "admin-users-v1", "users": []}


# Define the _load_admin_users function used by this module.
def _load_admin_users():
    # Load the canonical auth registry used by both login and Admin user management.
    state = auth.load_users()
    # Track whether legacy reconciliation adds any canonical identities.
    changed = False
    # Read legacy Admin-only identities so existing local deployments can be reconciled once.
    legacy = read_json(ADMIN_USERS_PATH, _default_admin_users)
    # Iterate through valid legacy identities without creating duplicate canonical accounts.
    for user in legacy.get("users", []) if isinstance(legacy, dict) else []:
        # Skip identities already represented by durable id or normalized email.
        if any(existing.get("user_id") == user.get("user_id") or existing.get("email") == user.get("email") for existing in state.get("users", [])):
            # Continue with the next legacy identity.
            continue
        # Copy the legacy identity into the login-ready canonical registry.
        state.setdefault("users", []).append({**user, "username": user.get("email", ""), "roles": [user.get("role", "player")], "identity_provider": user.get("identity_provider", "local")})
        # Mark the canonical registry for persistence after reconciliation.
        changed = True
    # Persist only when reconciliation added identities to the canonical registry.
    if changed:
        # Save the reconciled canonical identities once.
        auth.save_users(state)
    # Return the canonical identity state to all Admin operations.
    return state


# Define the _save_admin_users function used by this module.
def _save_admin_users(state):
    # Persist Admin mutations through the canonical auth identity store.
    auth.save_users(state)


# Define the _clean_text function used by this module.
def _clean_text(value, field, *, required=True, default=""):
    # Set text to the stripped string representation used for validation.
    text = str(value if value is not None else default).strip()
    # Branch when required text is missing.
    if required and not text:
        # Raise an explicit validation error for Admin form feedback.
        raise ValidationError(f"{field} is required")
    # Return the normalized text.
    return text


# Normalize a role list for account-only Admin mutations.
def _clean_roles(value) -> list[str]:
    # Collapse absent or empty role input to the regular player role.
    supplied = value if isinstance(value, list) else [value]
    # Normalize each supplied role and discard blanks before validation.
    roles = [str(role or "").strip().lower() for role in supplied if str(role or "").strip()]
    # Default account identities to player when no role remains.
    roles = roles or ["player"]
    # Reject Guest Trial or arbitrary role values before privilege mutation.
    if any(role not in ACCOUNT_ROLES for role in roles):
        # Raise a bounded validation message without echoing caller role text.
        raise ValidationError("User role is invalid")
    # Preserve stable order while removing duplicates.
    return list(dict.fromkeys(roles))


# Normalize one Admin-visible account status.
def _clean_status(value) -> str:
    # Lowercase and trim the requested lifecycle state.
    status = str(value or "active").strip().lower()
    # Reject unsupported lifecycle states.
    if status not in ACCOUNT_STATUSES:
        # Raise a bounded validation error.
        raise ValidationError("User status is invalid")
    # Return the canonical status value.
    return status


# Count active Admin accounts after applying an optional in-memory replacement.
def _active_admin_count(state: dict, replacement: dict | None = None) -> int:
    # Build the candidate user list with the replacement record substituted by user id.
    users = [replacement if replacement and user.get("user_id") == replacement.get("user_id") else user for user in state.get("users", [])]
    # Count active non-guest identities with ordinary Admin or inherited owner access.
    return sum(1 for user in users if not _is_guest_trial_user(user) and auth.is_admin(user))


# Reject mutations that would leave the product without any active Admin.
def _require_remaining_admin(state: dict, replacement: dict) -> None:
    # Check the simulated post-mutation registry.
    if _active_admin_count(state, replacement) < 1:
        # Fail closed before committing a lockout.
        raise ValidationError("At least one active Admin must remain")


# Count active platform owners after applying an optional in-memory replacement. (ADMIN-028)
def _active_platform_owner_count(state: dict, replacement: dict | None = None) -> int:
    # Substitute the candidate record so validation observes the exact post-mutation document.
    users = [replacement if replacement and user.get("user_id") == replacement.get("user_id") else user for user in state.get("users", [])]
    # Count only active durable accounts carrying bootstrap-managed owner authority.
    return sum(1 for user in users if not _is_guest_trial_user(user) and auth.is_platform_owner(user))


# Reject mutations that would remove or disable the last platform owner. (ADMIN-028)
def _require_remaining_platform_owner(state: dict, replacement: dict) -> None:
    # Check the complete post-mutation registry under the provider transaction.
    if _active_platform_owner_count(state, replacement) < 1:
        # Preserve at least one recoverable bootstrap authority.
        raise ValidationError("At least one active platform owner must remain")


# Validate the active Admin and owner invariants together. (ADMIN-028)
def _require_remaining_authority(state: dict, replacement: dict) -> None:
    # Preserve the existing Admin-surface availability invariant.
    _require_remaining_admin(state, replacement)
    # Preserve the stronger owner-delegation invariant.
    _require_remaining_platform_owner(state, replacement)


# Resolve an authenticated actor against current canonical state before a privileged role mutation. (ADMIN-028)
def _current_platform_owner(actor: dict | None) -> dict:
    # Read only the opaque actor id from request context.
    actor_id = str((actor or {}).get("user_id") or "")
    # Reject absent or synthetic identities before any account lookup.
    if not actor_id:
        # Return one enumeration-safe authorization failure.
        raise ForbiddenError("Platform owner role is required")
    # Resolve current durable authority so a stale session payload cannot retain owner power.
    current = auth.find_user_by_id(actor_id)
    # Require the canonical active owner role.
    auth.require_platform_owner(current or {})
    # Return the current actor for transaction-scoped validation and audit attribution.
    return current


# Extract one sparse proposal or exact rollback document from an owner Admin request. (AUTH-014)
def _enrollment_policy_changes(body, *, apply_request: bool):
    # Require one JSON object so arbitrary request bodies cannot control membership checks.
    if not isinstance(body, dict):
        # Fail through the standard validation envelope before provider access.
        raise ValidationError("enrollment policy request must be an object")
    # Name the request controls accepted by preview and apply.
    allowed = {"changes", "policy"}
    # Include exact confirmation, bounded reason, and preview revision only on the applying route.
    if apply_request:
        # Extend the allowlist without accepting any future field implicitly.
        allowed.update({"confirm", "reason", "revision"})
    # Reject arbitrary readiness, role, provider, or public-control fields.
    if set(body) - allowed:
        # Return a value-free unsupported-field diagnostic.
        raise ValidationError("enrollment policy request contains unsupported fields")
    # Require exactly one proposal representation.
    if ("changes" in body) == ("policy" in body):
        # Refuse missing or ambiguous proposal sources.
        raise ValidationError("enrollment policy request requires exactly one policy or changes object")
    # Convert an exact prior-policy response into a complete rollback change.
    if "policy" in body:
        # Reuse the module-owned exact policy validator.
        return enrollment_policy.changes_for_policy(body["policy"])
    # Return the sparse proposal for validation by the shared preview/apply computation.
    return body["changes"]


# Build the transaction validator for owner-authorized role mutations. (ADMIN-028)
def _owner_role_validator(actor_id: str):
    # Validate the complete post-mutation identity document under one provider lock.
    def validate(state: dict, replacement: dict) -> None:
        # Resolve the actor from the same post-mutation document used for persistence.
        actor = next((user for user in state.get("users", []) if user.get("user_id") == actor_id), None)
        # Reject an owner who lost authority before this mutation could commit.
        auth.require_platform_owner(actor or {})
        # Preserve both Admin access and bootstrap owner recovery.
        _require_remaining_authority(state, replacement)
    # Return the closure accepted by the canonical identity updater.
    return validate


# Record full Admin-account mutation metadata in the internal app audit log.
def _audit_user_change(event: str, before: dict, after: dict, actor: dict | None = None) -> None:
    # Emit before and after role/status/display/locale fields for Admin-only review.
    logger.info(event, actor_id=(actor or {}).get("user_id"), user_id=after.get("user_id"), email=after.get("email"), before={"status": before.get("status"), "roles": before.get("roles"), "display_name": before.get("display_name"), "locale": before.get("locale")}, after={"status": after.get("status"), "roles": after.get("roles"), "display_name": after.get("display_name"), "locale": after.get("locale")})


# Define the _as_bool function used by this module.
def _as_bool(value):
    # Branch when the value is already boolean.
    if isinstance(value, bool):
        # Return the boolean value unchanged.
        return value
    # Return a permissive truthy check for form and JSON inputs.
    return str(value).strip().lower() in {"1", "true", "yes", "on", "accepted"}


# Define the _temporary_password function used by this module.
def _temporary_password():
    # Return a short one-time password for Admin handoff to a beta user.
    return secrets.token_urlsafe(12)


# Define the _user_by_id function used by this module.
def _user_by_id(state, user_id):
    # Iterate through persisted users to find the requested account.
    for user in state["users"]:
        # Branch when the user id matches.
        if user.get("user_id") == user_id:
            # Return the matching persisted user record.
            return user
    # Raise a not-found error for missing Admin user operations.
    raise NotFoundError(f"Admin user {user_id} was not found")


# Define _is_guest_trial_user so Admin account management can keep temporary marketing users separate.
def _is_guest_trial_user(user):
    # Normalize every persisted role so malformed legacy casing cannot expose a temporary principal.
    roles = {str(role or "").lower() for role in auth.roles_for_user(user)}
    # Normalize the dedicated identity-provider marker independently from role state.
    identity_provider = str(user.get("identity_provider") or "").lower()
    # Exclude canonical and legacy guest markers from account management, even when a partial old row is malformed.
    return auth.is_guest(user) or bool(user.get("guest")) or identity_provider == "guest" or "guest" in roles


# Define _account_user_by_id to reject Guest Trials from regular user-management routes.
def _account_user_by_id(state, user_id):
    # Load the requested identity through the existing durable lookup.
    user = _user_by_id(state, user_id)
    # Branch when a disposable trial principal is being addressed through the wrong Admin area.
    if _is_guest_trial_user(user):
        # Hide guest principals from account-management routes; Guest Trials owns their lifecycle telemetry.
        raise NotFoundError("Admin account user was not found")
    # Return the managed account identity to the caller.
    return user


# Define the _ensure_unique_email function used by this module.
def _ensure_unique_email(state, email):
    # Iterate through persisted users to enforce unique beta account emails.
    for user in state["users"]:
        # Branch when the normalized email is already assigned.
        if (user.get("email") or "").lower() == email.lower():
            # Raise an explicit validation error instead of overwriting an account.
            raise ValidationError("email already exists", {"email": email})


# Define the _linked_player function used by this module.
def _linked_player(user):
    # Start protected logic so missing linked players do not hide the user record.
    try:
        # Return the linked player wallet through the public player service.
        return players.get_player(user.get("player_id"))
    # Handle missing linked player state with a synthetic inactive summary.
    except NotFoundError:
        # Return a diagnostic player-like summary when the wallet is missing.
        return {"player_id": user.get("player_id"), "balance": 0, "status": "missing"}


# Define the _public_admin_user function used by this module.
def _public_admin_user(user):
    # Set player to the linked wallet used for token balance inspection.
    player = _linked_player(user)
    # Set public_user to a copy that excludes password verifiers and guest-only analytics bindings.
    public_user = {k: v for k, v in user.items() if k not in ("password_hash", "guest_analytics_id")}
    # Set public_user["token_balance"] from the linked player wallet balance.
    public_user["token_balance"] = round(float(player.get("balance", 0)), 2)
    # Set public_user["token_state"] from account and wallet status together.
    public_user["token_state"] = "active" if user.get("status") == "active" and player.get("status") == "active" else "inactive"
    # Set public_user["player_status"] for Admin diagnostics.
    public_user["player_status"] = player.get("status", "unknown")
    # Set public_user["terms_status"] to a compact accepted/pending value.
    public_user["terms_status"] = "accepted" if user.get("terms_accepted_at") else "pending"
    # Publish the v2 contract's boolean terms status alongside the v1 compact label.
    public_user["terms_accepted"] = bool(user.get("terms_accepted_at")) or not bool(user.get("terms_required", True))
    # Publish the v2 active flag while preserving the legacy status string.
    public_user["active"] = user.get("status") == "active"
    # Publish the canonical username alias required by the v2 Admin contract.
    public_user["username"] = user.get("username") or user.get("email", "")
    # Publish a canonical role collection while retaining the legacy role field.
    public_user["roles"] = list(user.get("roles") or [user.get("role", "player")])
    # Publish the canonical locale from current or legacy metadata.
    public_user["locale"] = user.get("locale") or user.get("language") or "en-US"
    # Return the safe user payload.
    return public_user


# Define the list_admin_users function used by this module.
def list_admin_users():
    # Return public account payloads only so Guest Trials never mix into regular Users.
    return [_public_admin_user(user) for user in _load_admin_users()["users"] if not _is_guest_trial_user(user)]


# Define the create_admin_user function used by this module.
def create_admin_user(body):
    # Set state to the persisted Admin user registry.
    state = _load_admin_users()
    # Set email to the required normalized beta user email.
    email = _clean_text(body.get("email"), "email").lower()
    # Enforce unique emails before creating linked wallet state.
    _ensure_unique_email(state, email)
    # Set display_name to the required user-facing name.
    display_name = _clean_text(body.get("display_name"), "display_name")
    # Set language to the preserved per-account locale preference.
    language = _clean_text(body.get("language") or body.get("locale"), "language", required=False, default="en-US") or "en-US"
    # Set format_locale to the preserved number/date locale preference.
    format_locale = _clean_text(body.get("format_locale"), "format_locale", required=False, default="browser") or "browser"
    # Set initial_tokens to the requested ledger-backed token grant.
    initial_tokens = round(float(body.get("initial_tokens", body.get("token_balance", 5000)) or 0), 2)
    # Branch when the token grant is negative.
    if initial_tokens < 0:
        # Raise a validation error so Admin cannot create negative wallets.
        raise ValidationError("initial_tokens must not be negative")
    # Set password to the supplied password or a generated temporary value.
    password = body.get("password") or _temporary_password()
    # Set player to a linked wallet created with zero direct balance.
    player = players.create_player(display_name, "human", 0)
    # Normalize the requested role before enforcing the dedicated post-creation delegation boundary. (ADMIN-033)
    requested_roles = _clean_roles(body.get("role") or "player")
    # Prevent legacy v1 account creation from bypassing owner reauthentication and role audit.
    if requested_roles != ["player"]:
        # Require every new identity to exist as an ordinary active player before delegation.
        raise ValidationError("New accounts must be created as players before Admin delegation")
    # Create every new account at the ordinary player privilege level.
    role = "player"
    # Create the login identity through the same canonical auth service used by session login.
    user = auth.create_user(email, password, display_name, role, player["player_id"], not _as_bool(body.get("terms_accepted")), language)
    # Add Admin-facing locale and credential-rotation metadata to the canonical identity.
    user = auth.update_user_by_id(user["user_id"], lambda record: record.update({"format_locale": format_locale, "use_browser_locale": _as_bool(body.get("use_browser_locale", True)), "password_reset_required": True, "password_version": 1, "terms_accepted_at": utc_now() if _as_bool(body.get("terms_accepted")) else None}))
    # Record full Admin creation metadata for internal audit review.
    logger.info("admin_user_created", user_id=user.get("user_id"), email=user.get("email"), roles=user.get("roles"), status=user.get("status"))
    # Branch when Admin grants starting tokens.
    if initial_tokens:
        # Credit the linked wallet through the ledger to preserve token invariants.
        ledger.credit(player["player_id"], initial_tokens, "ADMIN_TOKEN_GRANT", "admin", None, {"reason": "admin_user_create", "user_id": user["user_id"]})
    # Return the public user plus the temporary password for one-time Admin handoff.
    return {"user": _public_admin_user(user), "temporary_password": password}


# Define the set_admin_user_status function used by this module.
def set_admin_user_status(user_id, status):
    # Load the requested account before applying the canonical auth mutation.
    current = _account_user_by_id(_load_admin_users(), user_id)
    # Normalize the requested lifecycle state.
    requested_status = _clean_status(status)
    # Capture the exact pre-mutation account inside the provider transaction for audit.
    before = {}
    # Define the status mutation applied under the identity-document lock.
    def mutate(record: dict) -> None:
        # Snapshot the committed pre-change account before replacing its lifecycle state.
        before.update(dict(record))
        # Store the validated lifecycle state.
        record["status"] = requested_status
    # Update status through auth so privilege changes revoke predecessor sessions.
    user = auth.update_user_by_id(user_id, mutate, state_validator=_require_remaining_authority)
    # Update the linked player status through the public player service.
    players.update_player(current["player_id"], lambda player: player.update({"status": requested_status}))
    # Record the full before/after status mutation for Admin audit.
    _audit_user_change("admin_user_status_changed", before, user)
    # Return the safe user payload after status change.
    return {"user": _public_admin_user(user)}


# Define the reset_admin_user_password function used by this module.
def reset_admin_user_password(user_id, body):
    # Set state to the persisted Admin user registry.
    state = _load_admin_users()
    # Set user to the requested account record.
    user = _account_user_by_id(state, user_id)
    # Set password to the provided password or generated reset value.
    password = body.get("password") or _temporary_password()
    # Replace the password through the canonical auth service so login sees the reset immediately.
    user = auth.set_user_password(user_id, password)
    # Return the one-time temporary password and safe user payload.
    return {"user": _public_admin_user(user), "temporary_password": password}


# Define the update_admin_user_terms function used by this module.
def update_admin_user_terms(user_id, body):
    # Set state to the persisted Admin user registry.
    state = _load_admin_users()
    # Set user to the requested account record.
    user = _account_user_by_id(state, user_id)
    # Set accepted to the requested terms acceptance state.
    accepted = _as_bool(body.get("accepted", body.get("terms_accepted")))
    # Store terms state through the canonical auth service used by the browser gate.
    user = auth.accept_terms(user_id, body.get("terms_version") or "private-beta-1", accepted, "admin")
    # Return the safe user payload after terms status change.
    return {"user": _public_admin_user(user)}


# Define the update_admin_user_locale function used by this module.
def update_admin_user_locale(user_id, body):
    # Set state to the persisted Admin user registry.
    state = _load_admin_users()
    # Set user to the requested account record.
    user = _account_user_by_id(state, user_id)
    # Set user["language"] from the Admin locale control payload.
    user["language"] = _clean_text(body.get("language"), "language", required=False, default=user.get("language", "en-US")) or "en-US"
    # Mirror the display language to the canonical v2 locale field.
    user["locale"] = user["language"]
    # Set user["format_locale"] from the Admin locale control payload.
    user["format_locale"] = _clean_text(body.get("format_locale"), "format_locale", required=False, default=user.get("format_locale", "browser")) or "browser"
    # Set user["use_browser_locale"] from the Admin locale control payload.
    user["use_browser_locale"] = _as_bool(body.get("use_browser_locale", user.get("use_browser_locale", True)))
    # Set user["updated_at"] to the current audit timestamp.
    user["updated_at"] = utc_now()
    # Persist the locale preferences update.
    _save_admin_users(state)
    # Return the safe user payload after locale update.
    return {"user": _public_admin_user(user)}


# Define update_admin_user so the v2 PATCH contract mutates the canonical identity.
def update_admin_user(user_id, body, actor=None):
    # Reject disposable guest-trial identities before any canonical account mutation can run.
    _account_user_by_id(_load_admin_users(), user_id)
    # Keep privilege mutation in the dedicated reauthenticated Administrators workflow. (ADMIN-033)
    if "roles" in body:
        # Reject the historical generic-user shortcut so it cannot bypass reason, replay, or audit controls.
        raise ValidationError("Use the Administrators area to change account roles")
    # Ordinary account lifecycle updates do not carry role-delegation authority.
    owner = None
    # Capture the exact pre-mutation account inside the provider transaction for audit.
    before = {}
    # Define the canonical mutation applied to the requested identity.
    def mutate(user):
        # Snapshot the committed pre-change account before applying any requested field.
        before.update(dict(user))
        # Update active status only when the contract field is present.
        if "active" in body:
            # Map the boolean contract field to the durable status value.
            user["status"] = "active" if _as_bool(body.get("active")) else "inactive"
        # Update explicit lifecycle status only when the contract field is present.
        if "status" in body:
            # Store the canonical account lifecycle state.
            user["status"] = _clean_status(body.get("status"))
        # Update display name only when the contract field is present.
        if "display_name" in body:
            # Store the validated display name.
            user["display_name"] = _clean_text(body.get("display_name"), "display_name")
        # Update roles only when the contract field is present.
        if "roles" in body:
            # Reject direct mutation of bootstrap-managed platform-owner authority.
            if auth.PLATFORM_OWNER_ROLE in auth.roles_for_user(user):
                # Preserve owner recovery even when another owner account may exist.
                raise ForbiddenError("Platform owner role cannot be changed")
            # Normalize the requested assignable player/Admin role collection.
            requested_roles = _clean_roles(body.get("roles"))
            # Require an already-active account before granting new Admin authority.
            if "admin" in requested_roles and "admin" not in auth.roles_for_user(user) and before.get("status") != "active":
                # Reject combined activation/promotion and inactive-account privilege grants.
                raise ValidationError("Only an active account can be granted Admin")
            # Normalize the role list and preserve the compatible singular primary role.
            user["roles"] = requested_roles
            # Store the primary role for older clients.
            user["role"] = user["roles"][0]
        # Update locale metadata only when the contract field is present.
        if "locale" in body:
            # Store one locale across canonical and legacy aliases.
            user["locale"] = user["language"] = _clean_text(body.get("locale"), "locale")
    # Select the transaction validator that matches privilege or ordinary lifecycle changes.
    validator = _owner_role_validator(owner["user_id"]) if owner else _require_remaining_authority
    # Apply the mutation through the canonical auth service with transaction-scoped authority checks.
    user = auth.update_user_by_id(user_id, mutate, state_validator=validator)
    # Keep the bound player status aligned with the canonical account status.
    players.update_player(user["player_id"], lambda player: player.update({"status": user.get("status", "active")}))
    # Record the full before/after mutation for Admin audit review.
    _audit_user_change("admin_user_updated", before, user, owner or actor)
    # Return the Admin-safe canonical summary.
    return _public_admin_user(user)


# Define admin_user_state so v2 inspection stays scoped to one canonical user.
def admin_user_state(user_id):
    # Load the canonical user and linked player.
    user = _account_user_by_id(_load_admin_users(), user_id)
    # Read the linked wallet from the shared player provider.
    player = _linked_player(user)
    # Return only this user's balance, ledger count, and player-scoped game marker.
    return {"user_id": user["user_id"], "player_id": user["player_id"], "token_balance": round(float(player.get("balance", 0)), 2), "recent_ledger_count": len(ledger.read_recent(user["player_id"], 100)), "game_states": {}}


# Define the requirements function used by this module.
def requirements():
    # Return the computed value to the caller.
    return _read_json_file(REQ_PATH, {"requirements": []})


# Define the game_states function used by this module.
def game_states():
    # Resolve the active provider once so reset and direct state reads share one boundary.
    provider = get_storage_provider()
    # Hold JSON reset visibility while enumerating and reading the complete state snapshot.
    with provider.state_visibility_transaction():
        # Set states to the value needed for the next operation.
        states = {}
        # Branch when the following condition is true.
        if GAME_DATA_DIR.exists():
            # Recurse so per-game/per-player state files remain visible beside legacy flat files. (ADMIN-029)
            for p in sorted(GAME_DATA_DIR.rglob("*.json")):
                # Key each row by its root-relative path so nested player files stay distinct.
                key = p.relative_to(GAME_DATA_DIR).with_suffix("").as_posix()
                # Record the provider-stable file path and parsed state under the composite key.
                states[key] = {"path": str(p), "state": _read_json_file(p, {})}
        # Return the computed value to the caller from within stable visibility.
        return states


# Ledger transaction fragments owned by funded opponents or account seeding, excluded from player economics. (ADMIN-030)
_NON_PLAYER_LEDGER_FRAGMENTS = ("OPPONENT", "FUNDING", "FUND_ACCOUNT")
# Bound one economics read independently from caller-supplied values.
_ECONOMICS_MAX_WINDOW = 100_000
# Bound one detail payload so recent evidence cannot expand without governance.
_ECONOMICS_MAX_RECENT = 50


# Decide whether one ledger event represents a player-facing game movement instead of funding or opponent plumbing.
def _is_player_facing(event: dict) -> bool:
    # Read the type defensively so one malformed stored row cannot break the Admin economics view.
    transaction_type = str(event.get("transaction_type", ""))
    # Keep only game-bound movements whose type is outside the fixed infrastructure fragments.
    return bool(event.get("game")) and not any(fragment in transaction_type for fragment in _NON_PLAYER_LEDGER_FRAGMENTS)


# Clamp one integer control into its economics evidence range.
def _economics_bound(value, default: int, maximum: int) -> int:
    # Start protected coercion so malformed internal callers receive the reviewed default.
    try:
        # Parse the candidate into an integer count.
        parsed = int(value)
    # Replace missing, non-numeric, or malformed values with the reviewed default.
    except (TypeError, ValueError):
        # Return the reviewed default without echoing input.
        return default
    # Keep the count inside the one-through-maximum range.
    return max(1, min(parsed, maximum))


# Normalize one stored ledger amount or reject malformed/non-finite evidence.
def _economics_amount(event: dict):
    # Reject booleans because Python otherwise treats them as numeric one and zero.
    if isinstance(event.get("amount"), bool):
        # Exclude the malformed row.
        return None
    # Start protected conversion so hostile historical rows do not break diagnostics.
    try:
        # Convert accepted numeric representations to float for stable aggregation.
        amount = float(event.get("amount", 0) or 0)
    # Reject objects and text that cannot represent a numeric ledger amount.
    except (TypeError, ValueError):
        # Return no value so the entire malformed row is excluded.
        return None
    # Reject NaN and infinity because they cannot produce contract-safe JSON ratios.
    return amount if math.isfinite(amount) else None


# Aggregate wagered-versus-returned play tokens from the shared ledger into per-game payout rates. (ADMIN-030)
def game_economics(window: int = 100_000):
    # Clamp the window before calling the storage provider.
    window = _economics_bound(window, _ECONOMICS_MAX_WINDOW, _ECONOMICS_MAX_WINDOW)
    # Accumulate signed wager and return totals per game over one bounded recent window.
    by_game = {}
    # Read the shared ledger once so summary rows share the same source snapshot.
    for event in ledger.read_recent(limit=window):
        # Skip non-game and funded-opponent movements so rates reflect player-facing activity only.
        if not _is_player_facing(event):
            # Continue with the next event after rejecting infrastructure plumbing.
            continue
        # Normalize a missing amount to zero while preserving signed debit and credit semantics.
        amount = _economics_amount(event)
        # Exclude malformed or non-finite rows from both counts and totals.
        if amount is None:
            # Continue without publishing corrupted evidence.
            continue
        # Create the stable aggregate row on first use.
        aggregate = by_game.setdefault(event["game"], {"wagered": 0.0, "returned": 0.0, "events": 0})
        # Count every player-facing movement included in the rate window.
        aggregate["events"] += 1
        # Treat negative movements as wagered play tokens.
        if amount < 0:
            # Accumulate the unsigned wager amount.
            aggregate["wagered"] += -amount
        # Treat positive movements as returned play tokens.
        elif amount > 0:
            # Accumulate the return amount.
            aggregate["returned"] += amount
    # Build deterministic alphabetic output for stable Admin rendering and tests.
    rows = []
    # Derive rates for every game represented in the bounded window.
    for game in sorted(by_game):
        # Read the accumulated values for this game.
        aggregate = by_game[game]
        # Round token totals to the ledger's two-decimal presentation precision.
        wagered = round(aggregate["wagered"], 2)
        # Round returns independently before computing the published ratio.
        returned = round(aggregate["returned"], 2)
        # Publish no ratio until at least one wager anchors the denominator.
        rate = round(returned / wagered, 4) if wagered > 0 else None
        # Append the contract-shaped summary row.
        rows.append({"game": game, "wagered": wagered, "returned": returned, "events": aggregate["events"], "payout_rate": rate, "house_edge": round(1 - rate, 4) if rate is not None else None, "player_positive": bool(rate is not None and rate > 1.0)})
    # Publish the fixed window and its deterministic per-game rows.
    return {"window": window, "games": rows}


# Provide one game's payout-rate drill-down with transaction-type counts and bounded recent rows. (ADMIN-030)
def game_economics_detail(game: str, window: int = 100_000, recent: int = 50):
    # Clamp the provider window and recent evidence bounds before reading.
    window = _economics_bound(window, _ECONOMICS_MAX_WINDOW, _ECONOMICS_MAX_WINDOW)
    # Clamp recent evidence independently from the provider window.
    recent = _economics_bound(recent, _ECONOMICS_MAX_RECENT, _ECONOMICS_MAX_RECENT)
    # Retain only the selected game's player-facing movements from the same bounded ledger window.
    events = [event for event in ledger.read_recent(limit=window) if event.get("game") == game and _is_player_facing(event) and _economics_amount(event) is not None]
    # Accumulate per-type detail alongside the overall wager and return totals.
    by_type = {}
    # Start the wager total at zero for an empty window.
    wagered = 0.0
    # Start the return total at zero for an empty window.
    returned = 0.0
    # Visit each filtered event once.
    for event in events:
        # Normalize a missing transaction type to a stable low-cardinality label.
        transaction_type = str(event.get("transaction_type", "unknown"))
        # Normalize a missing amount to zero while retaining its sign.
        amount = _economics_amount(event)
        # Create the per-type counter on first use.
        breakdown = by_type.setdefault(transaction_type, {"count": 0, "total": 0.0})
        # Count the event in its transaction-type bucket.
        breakdown["count"] += 1
        # Accumulate the signed amount for operator inspection.
        breakdown["total"] += amount
        # Add negative movements to wagered tokens.
        if amount < 0:
            # Convert the debit into a positive wager total.
            wagered += -amount
        # Add positive movements to returned tokens.
        elif amount > 0:
            # Preserve the credit as a positive return total.
            returned += amount
    # Round wagered tokens to display precision.
    wagered = round(wagered, 2)
    # Round returned tokens to display precision.
    returned = round(returned, 2)
    # Publish no payout ratio until the selected game has a wager.
    rate = round(returned / wagered, 4) if wagered > 0 else None
    # Return the summary, deterministic type breakdown, and bounded recent evidence.
    return {"game": game, "wagered": wagered, "returned": returned, "events": len(events), "payout_rate": rate, "house_edge": round(1 - rate, 4) if rate is not None else None, "player_positive": bool(rate is not None and rate > 1.0), "by_transaction_type": [{"transaction_type": name, "count": data["count"], "total": round(data["total"], 2)} for name, data in sorted(by_type.items())], "recent": events[:recent]}


# Define the overview function used by this module.
def overview():
    # Set reqs to the value needed for the next operation.
    reqs = requirements().get("requirements", [])
    # Set counts to the value needed for the next operation.
    counts = {}
    # Iterate through the collection to process each item.
    for r in reqs:
        # Set counts[r.get("status", "UNKNOWN")] to the value needed for the next operation.
        counts[r.get("status", "UNKNOWN")] = counts.get(r.get("status", "UNKNOWN"), 0) + 1
    # Return the computed value to the caller.
    return {
        # Execute this statement as part of the module's documented control flow.
        "app_version": APP_VERSION,
        # Execute this statement as part of the module's documented control flow.
        "module_revisions": list_module_revisions(),
        # Execute this statement as part of the module's documented control flow.
        "players": players.list_players(),
        # Execute this statement as part of the module's documented control flow.
        "bots": profiles.list_bots(),
        # Execute this statement as part of the module's documented control flow.
        "bot_capabilities": profiles.capabilities(),
        # Publish funded practice-account allocation for Admin inspection.
        "practice_opponents": practice_opponents.list_accounts(),
        # Publish restart-safe controller ledger activity without private game state.
        "practice_opponent_activity": practice_opponents.recent_activity(50),
        # Set "autoplay_sessions": autoplay.list_sessions(active_only to the value needed for the next operation.
        "autoplay_sessions": autoplay.list_sessions(active_only=False),
        # Set "recent_ledger": ledger.read_recent(limit to the value needed for the next operation.
        "recent_ledger": ledger.read_recent(limit=50),
        # Execute this statement as part of the module's documented control flow.
        "recent_history": history.recent_history(50),
        # Execute this statement as part of the module's documented control flow.
        "logs": {"app": logger.recent("app", 50), "errors": logger.recent("errors", 50), "client": logger.recent("client", 50)},
        # Execute this statement as part of the module's documented control flow.
        "requirement_counts": counts,
        # Execute this statement as part of the module's documented control flow.
        "test_results": _read_json_file(TEST_RESULTS_PATH, {}),
        # Execute this statement as part of the module's documented control flow.
        "audio_settings": settings.audio_settings(),
    }


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/overview")
    # Define the admin_overview function used by this module.
    def admin_overview(body, query):
        # Return the computed value to the caller.
        return overview()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/dashboard")
    # Define the admin_dashboard function used by this module.
    def admin_dashboard(body, query):
        # Return the computed value to the caller.
        return overview()

    # Register the additive v2 Admin problem-report inbox. (ADMIN-025, issue #349)
    @router.get(r"/api/v2/admin/feedback/reports")
    # Return attachment-free summaries with optional governed filters.
    def admin_feedback_reports_v2(body, query):
        # Delegate validation and newest-first ordering to the feedback service.
        return {"reports": feedback.list_reports(query), "priorities": sorted(feedback.ALLOWED_PRIORITIES), "statuses": sorted(feedback.ALLOWED_STATUSES), "categories": sorted(feedback.ALLOWED_CATEGORIES), "impacts": sorted(feedback.ALLOWED_IMPACTS)}

    # Register one Admin report detail route with server-sanitized image evidence.
    @router.get(r"/api/v2/admin/feedback/reports/(?P<report_id>report_[A-Za-z0-9_-]+)")
    # Return one canonical internal report after the central Admin authorization gate.
    def admin_feedback_report_detail_v2(body, query, report_id):
        # Keep evidence and reporter linkage inside the Admin surface.
        return {"report": feedback.detail(report_id)}

    # Register the partial Admin triage update route.
    @router.patch(r"/api/v2/admin/feedback/reports/(?P<report_id>report_[A-Za-z0-9_-]+)")
    # Apply governed priority, lifecycle, notes, and an optional reviewed GitHub link.
    def admin_feedback_report_update_v2(body, query, report_id):
        # Return the complete updated report for immediate Admin rerendering.
        return {"report": feedback.update(report_id, body)}

    # Register an explicit safe GitHub-draft preparation action without external mutation.
    @router.post(r"/api/v2/admin/feedback/reports/(?P<report_id>report_[A-Za-z0-9_-]+)/github-draft")
    # Generate a reporter-free issue draft for Admin review and manual publication.
    def admin_feedback_github_draft_v2(body, query, report_id):
        # Return only title, body, and governed repository labels.
        return {"draft": feedback.github_draft(report_id)}

    # Register a metadata-only manual Admin export with no encoded attachment payloads.
    @router.get(r"/api/v2/admin/feedback/reports/(?P<report_id>report_[A-Za-z0-9_-]+)/export")
    # Return one privacy-safe export manifest after the central Admin authorization gate.
    def admin_feedback_export_v2(body, query, report_id):
        # Delegate evidence validation and payload removal to the feedback service.
        return {"export": feedback.export_report(report_id)}

    # Register explicit privacy deletion as a recoverable provider-neutral saga.
    @router.delete(r"/api/v2/admin/feedback/reports/(?P<report_id>report_[A-Za-z0-9_-]+)")
    # Scrub report content and evidence only after an idempotent Admin request.
    def admin_feedback_delete_v2(body, query, report_id):
        # Return only the minimal deletion receipt.
        return {"deletion": feedback.delete_report(report_id, body)}

    # Register bounded retention cleanup for explicit Admin operation.
    @router.post(r"/api/v2/admin/feedback/cleanup")
    # Apply terminal and absolute privacy ceilings while recovering interrupted deletions.
    def admin_feedback_cleanup_v2(body, query):
        # Return only policy and deletion counts.
        return {"cleanup": feedback.cleanup_retention()}

    # Register the owner-only coherent policy and immutable actor/change audit view. (AUTH-014)
    @router.get(r"/api/v2/admin/enrollment-policy")
    # Require current canonical owner authority even though the route is read-only.
    def admin_enrollment_policy_read_v2(body, query, context):
        # Resolve current durable owner authority rather than trusting a stale session payload.
        _current_platform_owner(context.get("user"))
        # Return one provider-coherent policy, capability, vocabulary, and verified audit snapshot.
        return enrollment_policy.owner_view()

    # Register owner-only policy impact preview without provider mutation. (AUTH-014)
    @router.post(r"/api/v2/admin/enrollment-policy/preview")
    # Compute the exact capability effect through the same pure function used by apply.
    def admin_enrollment_policy_preview_v2(body, query, context):
        # Reject ordinary Admins before validating proposal fields.
        _current_platform_owner(context.get("user"))
        # Extract one sparse proposal or exact prior-policy rollback document.
        changes = _enrollment_policy_changes(body, apply_request=False)
        # Return the exact current/proposed policies and shared capability impact without writing.
        return enrollment_policy.propose(changes)

    # Register owner-only confirmed policy apply with provider-backed actor/change evidence. (AUTH-014)
    @router.post(r"/api/v2/admin/enrollment-policy")
    # Commit policy and immutable audit inside one provider transaction.
    def admin_enrollment_policy_apply_v2(body, query, context):
        # Reject ordinary Admins before confirming or validating proposal fields.
        owner = _current_platform_owner(context.get("user"))
        # Require the exact boolean confirmation rather than a truthy alias.
        if not isinstance(body, dict) or body.get("confirm") is not True:
            # Refuse accidental or ambiguous mutation requests.
            raise ValidationError("enrollment policy change requires explicit confirmation")
        # Extract the proposal only after current owner authority and confirmation succeed.
        changes = _enrollment_policy_changes(body, apply_request=True)
        # Compute the exact resulting policy before any durable write or external enablement. (AUTH-015)
        proposal = enrollment_policy.propose(changes)
        # Read the current durable restricted-preview policy for capability-expansion comparison.
        previous_policy = proposal["previous"]
        # Read the fully normalized proposed policy rather than trusting sparse caller fields.
        proposed_policy = proposal["policy"]
        # Detect any newly enabled public identity method while external release approval remains held.
        enables_method = any(bool(proposed_policy.get("methods", {}).get(method)) and not bool(previous_policy.get("methods", {}).get(method)) for method in ("email", "google", "facebook"))
        # Detect a newly enabled invitation path under the same explicit release boundary.
        enables_invitations = bool(proposed_policy.get("invitations_enabled")) and not bool(previous_policy.get("invitations_enabled"))
        # Reject capability expansion until the separate Workroom/provider release decision exists.
        if enables_method or enables_invitations:
            # Preserve preview and disable/rollback controls without silently enabling public identity paths.
            raise ForbiddenError("Live enrollment enablement requires separate owner release approval")
        # Atomically commit policy plus immutable actor/change evidence with the canonical owner id.
        result = enrollment_policy.update(changes, actor_id=owner.get("user_id"), reason=body.get("reason"), expected_revision=body.get("revision"))
        # Return the exact prior policy for direct application rollback plus the committed receipt.
        return {"policy": result["current"], "previous": result["previous"], "previous_revision": result["previous_revision"], "revision": result["revision"], "impact": result["impact"], "audit": result["audit"]}

    # Publish one owner-only secret-safe enrollment readiness aggregate. (AUTH-015, OAUTH-011)
    @router.get(r"/api/v2/admin/enrollment-readiness")
    # Combine durable policy, mail, recovery, and provider diagnostics without enabling any method.
    def admin_enrollment_readiness_v2(body, query, context):
        # Require current durable owner authority before publishing configuration diagnostics.
        _current_platform_owner(context.get("user"))
        # Read the durable policy without writing or widening it.
        policy = enrollment_policy.current()
        # Read provider-neutral mail readiness without contacting a delivery provider.
        mail_readiness = mail.configured_service().readiness()
        # Read allowlisted OAuth diagnostics without constructing adapters or opening network traffic.
        oauth = provider_diagnostic_payload()
        # Index only the reviewed external providers by stable id.
        providers = {row.get("provider"): row for row in oauth.get("providers", []) if row.get("provider") in {"google", "facebook"}}
        # Compute email readiness from both recovery release and delivery readiness.
        email_ready = bool(PASSWORD_RESET_ENABLED and mail_readiness.get("status") == "ready")
        # Publish method-specific readiness separately from durable enable flags.
        methods = {
            # Bind email signup readiness to both reset release and delivery readiness.
            "email": {"enabled": bool(policy.get("methods", {}).get("email")), "ready": email_ready, "blockers": [] if email_ready else ["password_recovery_or_mail_not_ready"]},
            # Bind Google readiness to allowlisted diagnostics without contacting the provider.
            "google": {"enabled": bool(policy.get("methods", {}).get("google")), "ready": bool(providers.get("google", {}).get("runtime_available")), "blockers": list(providers.get("google", {}).get("problems") or providers.get("google", {}).get("missing_variables") or (["provider_not_ready"] if not providers.get("google", {}).get("runtime_available") else []))},
            # Bind Facebook readiness through the same secret-safe provider projection.
            "facebook": {"enabled": bool(policy.get("methods", {}).get("facebook")), "ready": bool(providers.get("facebook", {}).get("runtime_available")), "blockers": list(providers.get("facebook", {}).get("problems") or providers.get("facebook", {}).get("missing_variables") or (["provider_not_ready"] if not providers.get("facebook", {}).get("runtime_available") else []))},
        }
        # Keep live enablement held even when repository configuration is structurally ready.
        return {"policy": policy, "methods": methods, "mail": mail_readiness, "providers": oauth.get("providers", []), "live_enablement_authorized": False, "restricted_preview": True}

    # Publish a read-only launch gate dashboard that cannot activate any release control. (issue #209)
    @router.get(r"/api/v2/admin/launch-readiness")
    # Aggregate current in-repository prerequisites while preserving the separate owner approval gate.
    def admin_launch_readiness_v2(body, query, context):
        # Reuse the owner-only readiness projection without creating a second source of truth.
        enrollment = admin_enrollment_readiness_v2(body, query, context)
        # Compute whether every signup method is disabled in the current restricted-preview policy.
        methods_disabled = all(not bool(item.get("enabled")) for item in enrollment["methods"].values())
        # Return fixed gate states and explicit external holds, never a mutation affordance.
        return {"status": "held", "restricted_preview": True, "checks": [{"id": "enrollment_policy", "status": "pass" if methods_disabled else "review"}, {"id": "password_recovery", "status": "pass" if enrollment["methods"]["email"]["ready"] else "held"}, {"id": "google_provider", "status": "pass" if enrollment["methods"]["google"]["ready"] else "held"}, {"id": "facebook_provider", "status": "pass" if enrollment["methods"]["facebook"]["ready"] else "held"}, {"id": "owner_workroom_approval", "status": "held"}], "live_enablement_authorized": False}

    # Attach the v2 Admin summary route required for additive guest-trial reporting.
    @router.get(r"/api/v2/admin/guest-trials")
    # Publish filterable de-identified Guest Trials aggregates through the governed v2 contract. (issue #317)
    def admin_guest_trials_v2(body, query):
        # End inactive or absolute-expiry principals before reporting active counts.
        auth.expire_overdue_guests()
        # Apply only validated low-cardinality and bounded-time filters inside the analytics service.
        summary = guest_analytics.summary(**_guest_filters(query))
        # Return the contract-owned summary without auth, player, session, or network identifiers.
        return {"guest_trials": summary}

    # Attach the Admin-readable guest admission state beside its existing telemetry. (GUEST-001, ADMIN-032)
    @router.get(r"/api/v2/admin/guest-trials/settings")
    # Publish the current switch and fixed token grant without exposing provider configuration.
    def admin_guest_trial_settings_read_v2(body, query):
        # Return the provider-backed setting through the standard Admin envelope.
        return {"settings": guest_settings.guest_settings()}

    # Attach the owner-only no-restart guest admission update. (GUEST-001, ADMIN-032)
    @router.post(r"/api/v2/admin/guest-trials/settings")
    # Persist only the exact boolean gate while leaving current trials untouched.
    def admin_guest_trial_settings_update_v2(body, query, context):
        # Resolve current canonical owner authority before validating or writing the policy.
        _current_platform_owner(context.get("user"))
        # Commit the exact reviewed switch and return the fixed grant for immediate UI readback.
        return {"settings": guest_settings.save_guest_settings(body)}

    # Attach the v2 recent-session list as an explicit contract surface.
    @router.get(r"/api/v2/admin/guest-trials/sessions")
    # Publish only retained de-identified analytics rows for Admin drill-down. (issue #317)
    def admin_guest_trial_sessions_v2(body, query):
        # Reuse the same filtered summary so retention and lifecycle cleanup cannot diverge.
        summary = guest_analytics.summary(**_guest_filters(query))
        # Return rows plus active filters without exposing credential-backed state.
        return {"sessions": summary["recent"], "filters": summary["filters"]}

    # Attach the v2 analytics-only detail route.
    @router.get(r"/api/v2/admin/guest-trials/sessions/(?P<analytics_id>gtrial_[A-Za-z0-9_-]+)")
    # Return one retained de-identified Guest Trials detail row. (issue #317)
    def admin_guest_trial_detail_v2(body, query, analytics_id):
        # Read the analytics-only row after the router has enforced Admin authorization.
        trial = guest_analytics.detail(analytics_id)
        # Return the standard not-found envelope when retention removed the row.
        if not trial:
            # Avoid confirming any auth, player, or session identity because none is accepted by this route.
            raise NotFoundError("Guest trial analytics row was not found")
        # Return the bounded lifecycle and aggregate counters.
        return {"guest_trial": trial}

    # Attach the v2 manual retention trigger for Admin diagnostics and bounded CI tests.
    @router.post(r"/api/v2/admin/guest-trials/cleanup")
    # Run the same idempotent raw and aggregate retention used by Admin reads. (issue #317)
    def admin_guest_trials_cleanup_v2(body, query):
        # Apply retention without accepting a caller-authored path, cutoff, or destructive scope.
        result = guest_analytics.cleanup()
        # Return identifier-free counts and completion health.
        return {"cleanup": result}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/modules")
    # Define the admin_modules function used by this module.
    def admin_modules(body, query):
        # Return the computed value to the caller.
        return {"modules": list_module_revisions()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/requirements")
    # Define the admin_requirements function used by this module.
    def admin_requirements(body, query):
        # Return the computed value to the caller.
        return requirements()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/game-states")
    # Define the admin_states function used by this module.
    def admin_states(body, query):
        # Return the computed value to the caller.
        return {"states": game_states()}

    # Publish per-game payout-rate telemetry through the Admin v1 contract. (ADMIN-030)
    @router.get(r"/api/v1/admin/economics")
    # Return the bounded summary from the shared ledger.
    def admin_economics(body, query):
        # Return deterministic per-game payout rates.
        return game_economics()

    # Publish one game's economics drill-down through the same Admin authorization boundary. (ADMIN-030)
    @router.get(r"/api/v1/admin/economics/(?P<game>[a-z0-9_]+)")
    # Return transaction-type and recent-event evidence for one canonical game id.
    def admin_economics_detail(body, query, game):
        # Return the selected game's bounded economics detail.
        return game_economics_detail(game)

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/users")
    # Define the admin_users function used by this module.
    def admin_users(body, query):
        # Return the user-management list with ledger-derived token balances.
        return {"users": list_admin_users()}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/users")
    # Define the admin_create_user function used by this module.
    def admin_create_user(body, query):
        # Return the newly created beta user and one-time password value.
        return create_admin_user(body)

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/users/(?P<user_id>[^/]+)")
    # Define the admin_user_detail function used by this module.
    def admin_user_detail(body, query, user_id):
        # Set state to the persisted Admin user registry.
        state = _load_admin_users()
        # Return the requested safe user payload.
        return {"user": _public_admin_user(_account_user_by_id(state, user_id))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/users/(?P<user_id>[^/]+)/deactivate")
    # Define the admin_deactivate_user function used by this module.
    def admin_deactivate_user(body, query, user_id):
        # Return the user after moving the account and linked wallet inactive.
        return set_admin_user_status(user_id, "inactive")

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/users/(?P<user_id>[^/]+)/reactivate")
    # Define the admin_reactivate_user function used by this module.
    def admin_reactivate_user(body, query, user_id):
        # Return the user after moving the account and linked wallet active.
        return set_admin_user_status(user_id, "active")

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/users/(?P<user_id>[^/]+)/password-reset")
    # Define the admin_reset_user_password function used by this module.
    def admin_reset_user_password(body, query, user_id):
        # Return the reset user and one-time password value.
        return reset_admin_user_password(user_id, body)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/users/(?P<user_id>[^/]+)/terms")
    # Define the admin_update_user_terms function used by this module.
    def admin_update_user_terms(body, query, user_id):
        # Return the user after updating terms acceptance status.
        return update_admin_user_terms(user_id, body)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/users/(?P<user_id>[^/]+)/locale")
    # Define the admin_update_user_locale function used by this module.
    def admin_update_user_locale(body, query, user_id):
        # Return the user after updating account locale preferences.
        return update_admin_user_locale(user_id, body)

    # Register the published v2 canonical user listing route.
    @router.get(r"/api/v2/admin/users")
    # Define admin_users_v2_list for contract-compatible summaries.
    def admin_users_v2_list(body, query):
        # Return the canonical Admin user collection.
        return {"users": list_admin_users()}

    # Register the additive v2 invitation list and readiness surface without modifying frozen v1. (INVITE-004)
    @router.get(r"/api/v2/admin/invitations")
    # Return bounded privacy-safe invitation lifecycle views.
    def admin_invitations_v2(body, query, context):
        # Start protected bounded parsing so malformed query values never become server errors.
        try:
            # Parse the optional decimal limit while retaining the service-side ceiling.
            limit = int((query or {}).get("limit", 100))
        # Convert non-numeric and unbounded query values into the standard validation envelope.
        except (TypeError, ValueError) as exc:
            # Raise a value-free request diagnostic.
            raise ValidationError("Invitation limit must be an integer") from exc
        # Reject booleans, zero, negatives, and values beyond the published contract.
        if isinstance((query or {}).get("limit"), bool) or limit < 1 or limit > 200:
            # Preserve one bounded contract error.
            raise ValidationError("Invitation limit must be between 1 and 200")
        # Return readiness plus masked-recipient rows only.
        return invitations.listing(limit)

    # Register additive v2 Admin issuance behind the centralized Admin and CSRF gates. (INVITE-001)
    @router.post(r"/api/v2/admin/invitations")
    # Create and deliver one account-free invitation through approved foundations.
    def admin_create_invitation_v2(body, query, context):
        # Reject fields outside the exact v2 contract before transient recipient handling.
        if set(body or {}) - {"recipient", "locale", "idempotency_key"}:
            # Preserve a stable validation category without echoing field values.
            raise ValidationError("Invitation request contains unsupported fields")
        # Attribute the fixed action to the authenticated Admin from request context.
        actor_id = str((context.get("user") or {}).get("user_id", ""))
        # Delegate rate, delivery, privacy, and recovery policy to the invitation service.
        return invitations.create(str((body or {}).get("recipient", "")), actor_id, locale=str((body or {}).get("locale", "en-US")), idempotency_key=str((body or {}).get("idempotency_key", "")))

    # Register additive v2 resend with an opaque path identifier. (INVITE-001)
    @router.post(r"/api/v2/admin/invitations/(?P<invitation_id>invite_[A-Za-z0-9_-]+)/resend")
    # Replace one pending delivery generation through the recoverable saga.
    def admin_resend_invitation_v2(body, query, context, invitation_id):
        # Reject fields outside the exact caller-idempotency contract.
        if set(body or {}) - {"idempotency_key"}:
            # Keep the Admin error free of supplied values.
            raise ValidationError("Invitation resend contains unsupported fields")
        # Attribute the fixed resend action to the authenticated Admin.
        actor_id = str((context.get("user") or {}).get("user_id", ""))
        # Delegate cooldown, rate, token replacement, and mail delivery policy.
        return invitations.resend(invitation_id, actor_id, idempotency_key=str((body or {}).get("idempotency_key", "")))

    # Register additive v2 revocation before a redemption claim can own the invitation. (INVITE-001)
    @router.post(r"/api/v2/admin/invitations/(?P<invitation_id>invite_[A-Za-z0-9_-]+)/revoke")
    # Revoke one invitation idempotently even while issuance is disabled.
    def admin_revoke_invitation_v2(body, query, context, invitation_id):
        # Reject fields outside the exact caller-idempotency contract.
        if set(body or {}) - {"idempotency_key"}:
            # Keep the Admin error free of supplied values.
            raise ValidationError("Invitation revoke contains unsupported fields")
        # Attribute the fixed revoke action to the authenticated Admin.
        actor_id = str((context.get("user") or {}).get("user_id", ""))
        # Delegate state-first revocation and token invalidation.
        return invitations.revoke(invitation_id, actor_id, idempotency_key=str((body or {}).get("idempotency_key", "")))

    # Register bounded terminal metadata cleanup under the Admin boundary. (INVITE-006)
    @router.post(r"/api/v2/admin/invitations/cleanup")
    # Prune only unambiguously terminal rows beyond retention.
    def admin_cleanup_invitations_v2(body, query, context):
        # Require an empty object so cleanup cannot accept destructive caller scope.
        if body not in ({}, None):
            # Reject any uncontracted cleanup selector.
            raise ValidationError("Invitation cleanup contains unsupported fields")
        # Return only the bounded count removed by fixed policy.
        return {"removed": invitations.cleanup()}

    # Register the published v2 canonical user creation route.
    @router.post(r"/api/v2/admin/users")
    # Define admin_users_v2_create for login-ready identity creation.
    def admin_users_v2_create(body, query, context):
        # Treat a missing JSON body as an empty mapping before validation.
        body = body or {}
        # Normalize role input before mapping the v2 contract to the existing creation helper.
        roles = _clean_roles(body.get("roles") or body.get("role") or "player")
        # Require additive v2 account creation to produce an ordinary player before delegation.
        if roles != ["player"]:
            # Keep Admin grants on existing active accounts behind owner-authorized PATCH.
            raise ValidationError("New accounts must be created as players before Admin delegation")
        # Map the published username field to the canonical email identifier.
        payload = {**body, "email": body.get("email") or body.get("username"), "display_name": body.get("display_name") or body.get("username"), "role": roles[0], "language": body.get("locale") or "en-US", "initial_tokens": body.get("initial_tokens", 0)}
        # Return the flat user summary required by the v2 envelope.
        return create_admin_user(payload)["user"]

    # Register the published v2 canonical user detail route.
    @router.get(r"/api/v2/admin/users/(?P<user_id>[^/]+)")
    # Define admin_users_v2_detail for one safe identity record.
    def admin_users_v2_detail(body, query, user_id):
        # Return the flat Admin-safe canonical identity.
        return _public_admin_user(_account_user_by_id(_load_admin_users(), user_id))

    # Register the published v2 canonical user update route.
    @router.patch(r"/api/v2/admin/users/(?P<user_id>[^/]+)")
    # Define admin_users_v2_update for roles, status, display name, and locale.
    def admin_users_v2_update(body, query, context, user_id):
        # Return the updated canonical identity summary.
        return update_admin_user(user_id, body, actor=context.get("user"))

    # Register the separate owner-only administrator-management inventory. (ADMIN-033)
    @router.get(r"/api/v2/admin/administrators")
    # Return current administrators, eligible active accounts, and the optimistic revision.
    def admin_administrators_v2(body, query, context):
        # Delegate durable owner revalidation and safe projection to the role service.
        return admin_roles.listing(context.get("user") or {})

    # Register bounded privacy-safe administrator-role audit history. (ADMIN-033)
    @router.get(r"/api/v2/admin/administrators/audit")
    # Return newest immutable grant/revoke rows only to the current platform owner.
    def admin_administrator_audit_v2(body, query, context):
        # Start protected parsing so arbitrary query text becomes a standard validation result.
        try:
            # Parse the optional history bound before applying the service clamp.
            limit = int((query or {}).get("limit", 100))
        # Convert non-numeric limits without echoing supplied text.
        except (TypeError, ValueError) as exc:
            # Raise one fixed validation diagnostic.
            raise ValidationError("Administrator audit limit is invalid") from exc
        # Delegate owner revalidation and safe projection to the role service.
        return admin_roles.audit_history(context.get("user") or {}, limit=limit)

    # Register one reauthenticated administrator grant for an existing active account. (ADMIN-033)
    @router.post(r"/api/v2/admin/administrators/(?P<user_id>[^/]+)/grant")
    # Apply an atomic, versioned, replay-safe grant and revoke predecessor sessions.
    def admin_administrator_grant_v2(body, query, context, user_id):
        # Bind actor authority from the authenticated context and target from the opaque path only.
        return admin_roles.change(context.get("user") or {}, user_id, "grant", body or {})

    # Register one reauthenticated administrator revocation for an existing account. (ADMIN-033)
    @router.post(r"/api/v2/admin/administrators/(?P<user_id>[^/]+)/revoke")
    # Apply an atomic, versioned, replay-safe revocation and invalidate predecessor sessions.
    def admin_administrator_revoke_v2(body, query, context, user_id):
        # Bind actor authority from the authenticated context and target from the opaque path only.
        return admin_roles.change(context.get("user") or {}, user_id, "revoke", body or {})

    # Register the published v2 password reset route.
    @router.post(r"/api/v2/admin/users/(?P<user_id>[^/]+)/password")
    # Define admin_users_v2_password for login-ready password changes.
    def admin_users_v2_password(body, query, user_id):
        # Return the flat updated identity without exposing password material.
        return reset_admin_user_password(user_id, body)["user"]

    # Register the published v2 terms metadata update route.
    @router.patch(r"/api/v2/admin/users/(?P<user_id>[^/]+)/terms")
    # Define admin_users_v2_terms for canonical terms state updates.
    def admin_users_v2_terms(body, query, user_id):
        # Update canonical terms metadata before returning the contract status object.
        user = update_admin_user_terms(user_id, body)["user"]
        # Return the canonical v2 terms status.
        return auth.terms_status(_user_by_id(_load_admin_users(), user["user_id"]))

    # Register the published v2 scoped user-state route.
    @router.get(r"/api/v2/admin/users/(?P<user_id>[^/]+)/state")
    # Define admin_users_v2_state for wallet and ledger inspection.
    def admin_users_v2_state(body, query, user_id):
        # Return state scoped to the requested canonical identity only.
        return admin_user_state(user_id)

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/logs")
    # Define the admin_logs function used by this module.
    def admin_logs(body, query):
        # Set kind to the value needed for the next operation.
        kind = query.get("kind", "app")
        # Set limit to the value needed for the next operation.
        limit = int(query.get("limit", 200))
        # Set logs to the value needed for the next operation.
        logs = logger.recent(kind, limit)
        # Set level to the value needed for the next operation.
        level = query.get("level")
        # Set game to the value needed for the next operation.
        game = query.get("game")
        # Set text to the value needed for the next operation.
        text = query.get("q")
        # Branch when the following condition is true.
        if level:
            # Set logs to the value needed for the next operation.
            logs = [r for r in logs if str(r.get("level","")) == level]
        # Branch when the following condition is true.
        if game:
            # Set logs to the value needed for the next operation.
            logs = [r for r in logs if str(r.get("game", r.get("game_id", ""))) == game]
        # Branch when the following condition is true.
        if text:
            # Set logs to the value needed for the next operation.
            logs = [r for r in logs if text.lower() in json.dumps(r).lower()]
        # Return the computed value to the caller.
        return {"kind": kind, "logs": logs}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/ledger")
    # Define the admin_ledger function used by this module.
    def admin_ledger(body, query):
        # Set rows to the value needed for the next operation.
        rows = ledger.read_recent(limit=int(query.get("limit", 500)))
        # Set player_id to the value needed for the next operation.
        player_id = query.get("player_id")
        # Set game to the value needed for the next operation.
        game = query.get("game")
        # Branch when the following condition is true.
        if player_id:
            # Set rows to the value needed for the next operation.
            rows = [r for r in rows if r.get("player_id") == player_id]
        # Branch when the following condition is true.
        if game:
            # Set rows to the value needed for the next operation.
            rows = [r for r in rows if r.get("game") == game]
        # Return the computed value to the caller.
        return {"ledger": rows}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/history")
    # Define the admin_history function used by this module.
    def admin_history(body, query):
        # Return the computed value to the caller.
        return {"history": history.recent_history(int(query.get("limit", 500)), query.get("game") or None)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/test-results")
    # Define the admin_test_results function used by this module.
    def admin_test_results(body, query):
        # Return the computed value to the caller.
        return {"results": _read_json_file(TEST_RESULTS_PATH, {})}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/audio-settings")
    # Define the get_audio function used by this module.
    def get_audio(body, query):
        # Return the computed value to the caller.
        return {"settings": settings.audio_settings()}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/audio-settings")
    # Define the save_audio function used by this module.
    def save_audio(body, query):
        # Return the computed value to the caller.
        return {"settings": settings.save_audio_settings(body)}

    # Expose the registered-account timeout policy only to the current bootstrap-managed owner. (SESSION-009, ADMIN-031)
    @router.get(r"/api/v2/admin/session-settings")
    # Return the provider-backed validated policy under the v2 settings envelope.
    def get_session_settings(body, query, context=None):
        # Require current owner authority because the policy controls every registered session lifetime.
        _current_platform_owner((context or {}).get("user"))
        # Return the validated settings document.
        return {"settings": session_settings.session_settings()}

    # Persist an owner-authored timeout-policy update through the additive v2 contract. (SESSION-009, SESSION-010, ADMIN-031)
    @router.post(r"/api/v2/admin/session-settings")
    # Clamp and persist the supplied settings only after owner authorization.
    def save_session_settings_route(body, query, context=None):
        # Reject ordinary Admins before validating or writing policy fields, capturing the owner for provenance.
        owner = _current_platform_owner((context or {}).get("user"))
        # Persist the validated partial update, stamping the durable last-updated actor without exposing any secret. (SESSION-010)
        return {"settings": session_settings.save_session_settings(body or {}, actor_id=owner.get("user_id"))}

    # Expose the live application-request rate policy through an owner-only recovery-safe route. (SEC-015, ADMIN-032)
    @router.get(r"/api/v2/admin/rate-limits")
    # Return the provider-backed validated rate policy without exposing client counters.
    def get_rate_limits(body, query, context=None):
        # Require current platform-owner authority before publishing operational controls.
        _current_platform_owner((context or {}).get("user"))
        # Return only the canonical validated global policy.
        return {"settings": rate_settings.rate_limits()}

    # Persist a bounded live rate-policy update without restarting the application. (SEC-015, ADMIN-032)
    @router.post(r"/api/v2/admin/rate-limits")
    # Clamp and store only the reviewed sparse policy fields.
    def save_rate_limits_route(body, query, context=None):
        # Require current platform-owner authority before changing global request capacity.
        _current_platform_owner((context or {}).get("user"))
        # Persist the validated partial update and echo its effective values.
        return {"settings": rate_settings.save_rate_limits(body or {})}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/autoplay")
    # Define the get_autoplay function used by this module.
    def get_autoplay(body, query):
        # Return the computed value to the caller.
        return {"sessions": autoplay.list_sessions(active_only=False)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/autoplay/stop-all")
    # Define the stop_all_autoplay function used by this module.
    def stop_all_autoplay(body, query):
        # Return the computed value to the caller.
        return {"sessions": autoplay.stop_all()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/bots")
    # Define the admin_bots function used by this module.
    def admin_bots(body, query):
        # Return the computed value to the caller.
        return {"bots": profiles.list_bots(), "capabilities": profiles.capabilities(), "practice_opponents": practice_opponents.list_accounts(), "practice_opponent_activity": practice_opponents.recent_activity(100)}

    # Register the explicit Admin action that seeds real practice-opponent wallets.
    @router.post(r"/api/v1/admin/bots/practice-opponents/fund")
    # Fund or replay the fixed server-managed account allocation.
    def fund_practice_opponents(body, query):
        # Use the issue-scoped default game unless Admin supplies the same canonical id.
        game_id = body.get("game_id") or practice_opponents.TEXAS_HOLDEM_PRACTICE_GAME
        # Return immutable ledger and replay evidence for all three accounts.
        return {"game_id": game_id, "funding": practice_opponents.fund_accounts(game_id), "practice_opponents": practice_opponents.list_accounts(game_id), "practice_opponent_activity": practice_opponents.recent_activity(100, game_id)}
