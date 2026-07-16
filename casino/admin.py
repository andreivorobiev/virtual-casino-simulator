# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import secrets
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, GAME_DATA_DIR, LOG_DIR, DOCS_DIR, APP_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.module_versions import list_module_revisions
# Import required dependency so this module can use its public functions or constants.
from casino.core import auth, players, ledger, history, logger, autoplay, settings
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json
# Import required dependency so this module can use its public functions or constants.
from casino.bots import profiles, practice_opponents
# Import required dependency so this module can use its public functions or constants.
from casino.errors import NotFoundError, ValidationError

# Set REQ_PATH to the value needed for the next operation.
REQ_PATH = DOCS_DIR / "requirements.json"
# Set TEST_RESULTS_PATH to the value needed for the next operation.
TEST_RESULTS_PATH = LOG_DIR / "test-runs" / "latest_results.json"
# Set ADMIN_USERS_PATH to the value needed for the next operation.
ADMIN_USERS_PATH = DATA_DIR / "admin_users.json"


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


# Define the _ensure_unique_email function used by this module.
def _ensure_unique_email(state, email):
    # Iterate through persisted users to enforce unique beta account emails.
    for user in state["users"]:
        # Branch when the normalized email is already assigned.
        if user.get("email", "").lower() == email.lower():
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
    # Set public_user to a copy that excludes password verifiers.
    public_user = {k: v for k, v in user.items() if k != "password_hash"}
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
    # Return public user payloads for the Admin user-management table.
    return [_public_admin_user(user) for user in _load_admin_users()["users"]]


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
    # Normalize the requested role to the canonical player/Admin vocabulary.
    role = _clean_text(body.get("role"), "role", required=False, default="player") or "player"
    # Create the login identity through the same canonical auth service used by session login.
    user = auth.create_user(email, password, display_name, role, player["player_id"], not _as_bool(body.get("terms_accepted")), language)
    # Add Admin-facing locale and credential-rotation metadata to the canonical identity.
    user = auth.update_user_by_id(user["user_id"], lambda record: record.update({"format_locale": format_locale, "use_browser_locale": _as_bool(body.get("use_browser_locale", True)), "password_reset_required": True, "password_version": 1, "terms_accepted_at": utc_now() if _as_bool(body.get("terms_accepted")) else None}))
    # Branch when Admin grants starting tokens.
    if initial_tokens:
        # Credit the linked wallet through the ledger to preserve token invariants.
        ledger.credit(player["player_id"], initial_tokens, "ADMIN_TOKEN_GRANT", "admin", None, {"reason": "admin_user_create", "user_id": user["user_id"]})
    # Return the public user plus the temporary password for one-time Admin handoff.
    return {"user": _public_admin_user(user), "temporary_password": password}


# Define the set_admin_user_status function used by this module.
def set_admin_user_status(user_id, status):
    # Load the requested account before applying the canonical auth mutation.
    current = _user_by_id(_load_admin_users(), user_id)
    # Update status through auth so privilege changes revoke predecessor sessions.
    user = auth.update_user_by_id(user_id, lambda record: record.update({"status": status}))
    # Update the linked player status through the public player service.
    players.update_player(current["player_id"], lambda player: player.update({"status": status}))
    # Return the safe user payload after status change.
    return {"user": _public_admin_user(user)}


# Define the reset_admin_user_password function used by this module.
def reset_admin_user_password(user_id, body):
    # Set state to the persisted Admin user registry.
    state = _load_admin_users()
    # Set user to the requested account record.
    user = _user_by_id(state, user_id)
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
    user = _user_by_id(state, user_id)
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
    user = _user_by_id(state, user_id)
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
def update_admin_user(user_id, body):
    # Define the canonical mutation applied to the requested identity.
    def mutate(user):
        # Update active status only when the contract field is present.
        if "active" in body:
            # Map the boolean contract field to the durable status value.
            user["status"] = "active" if _as_bool(body.get("active")) else "inactive"
        # Update display name only when the contract field is present.
        if "display_name" in body:
            # Store the validated display name.
            user["display_name"] = _clean_text(body.get("display_name"), "display_name")
        # Update roles only when the contract field is present.
        if "roles" in body:
            # Normalize the role list and preserve the compatible singular primary role.
            user["roles"] = [str(role).strip().lower() for role in body.get("roles", []) if str(role).strip()]
            # Store the primary role for older clients.
            user["role"] = user["roles"][0] if user["roles"] else "player"
        # Update locale metadata only when the contract field is present.
        if "locale" in body:
            # Store one locale across canonical and legacy aliases.
            user["locale"] = user["language"] = _clean_text(body.get("locale"), "locale")
    # Apply the mutation through the canonical auth service.
    user = auth.update_user_by_id(user_id, mutate)
    # Keep the bound player status aligned with the canonical account status.
    players.update_player(user["player_id"], lambda player: player.update({"status": user.get("status", "active")}))
    # Return the Admin-safe canonical summary.
    return _public_admin_user(user)


# Define admin_user_state so v2 inspection stays scoped to one canonical user.
def admin_user_state(user_id):
    # Load the canonical user and linked player.
    user = _user_by_id(_load_admin_users(), user_id)
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
    # Set states to the value needed for the next operation.
    states = {}
    # Branch when the following condition is true.
    if GAME_DATA_DIR.exists():
        # Iterate through the collection to process each item.
        for p in sorted(GAME_DATA_DIR.glob("*.json")):
            # Set states[p.stem] to the value needed for the next operation.
            states[p.stem] = {"path": str(p), "state": _read_json_file(p, {})}
    # Return the computed value to the caller.
    return states


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
        return {"user": _public_admin_user(_user_by_id(state, user_id))}

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

    # Register the published v2 canonical user creation route.
    @router.post(r"/api/v2/admin/users")
    # Define admin_users_v2_create for login-ready identity creation.
    def admin_users_v2_create(body, query):
        # Map the published username field to the canonical email identifier.
        payload = {**body, "email": body.get("email") or body.get("username"), "display_name": body.get("display_name") or body.get("username"), "role": (body.get("roles") or ["player"])[0], "language": body.get("locale") or "en-US", "initial_tokens": body.get("initial_tokens", 0)}
        # Return the flat user summary required by the v2 envelope.
        return create_admin_user(payload)["user"]

    # Register the published v2 canonical user detail route.
    @router.get(r"/api/v2/admin/users/(?P<user_id>[^/]+)")
    # Define admin_users_v2_detail for one safe identity record.
    def admin_users_v2_detail(body, query, user_id):
        # Return the flat Admin-safe canonical identity.
        return _public_admin_user(_user_by_id(_load_admin_users(), user_id))

    # Register the published v2 canonical user update route.
    @router.patch(r"/api/v2/admin/users/(?P<user_id>[^/]+)")
    # Define admin_users_v2_update for roles, status, display name, and locale.
    def admin_users_v2_update(body, query, user_id):
        # Return the updated canonical identity summary.
        return update_admin_user(user_id, body)

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
