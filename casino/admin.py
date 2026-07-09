# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import hashlib
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
from casino.core import players, ledger, history, logger, autoplay, settings
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json, write_json
# Import required dependency so this module can use its public functions or constants.
from casino.bots import profiles
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
    # Set state to the persisted user-management state or a new default state.
    state = read_json(ADMIN_USERS_PATH, _default_admin_users)
    # Branch when the stored payload is malformed.
    if not isinstance(state, dict) or "users" not in state:
        # Set state to a fresh default so Admin can recover from invalid files.
        state = _default_admin_users()
    # Return the normalized state to callers.
    return state


# Define the _save_admin_users function used by this module.
def _save_admin_users(state):
    # Set the schema marker so future migrations can identify this payload.
    state["schema_version"] = "admin-users-v1"
    # Persist the user-management state through the shared JSON store.
    write_json(ADMIN_USERS_PATH, state)


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


# Define the _hash_password function used by this module.
def _hash_password(password):
    # Set salt to a fresh random value for the stored password verifier.
    salt = secrets.token_hex(12)
    # Set digest to a PBKDF2 hash so raw passwords are not stored.
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    # Return a self-describing verifier string for future auth service consumption.
    return f"pbkdf2_sha256$100000${salt}${digest}"


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
    # Set user to the persisted beta account metadata.
    user = {
        # Store the durable Admin user id.
        "user_id": new_id("user"),
        # Store the linked wallet id used for ledger-backed balances.
        "player_id": player["player_id"],
        # Store the normalized email for lookup and display.
        "email": email,
        # Store the display name for Admin tables.
        "display_name": display_name,
        # Store the role without enabling external identity providers.
        "role": _clean_text(body.get("role"), "role", required=False, default="beta_player") or "beta_player",
        # Store the current account status.
        "status": "active",
        # Store the salted password verifier for future auth service consumption.
        "password_hash": _hash_password(password),
        # Require the user to rotate generated or Admin-set credentials.
        "password_reset_required": True,
        # Start password versioning for reset auditability.
        "password_version": 1,
        # Store terms acceptance time only when Admin marks it accepted.
        "terms_accepted_at": utc_now() if _as_bool(body.get("terms_accepted")) else None,
        # Store the display language preference without touching browser-local Admin controls.
        "language": language,
        # Store the format locale preference without changing ledger semantics.
        "format_locale": format_locale,
        # Store whether browser locale resolution should remain preferred.
        "use_browser_locale": _as_bool(body.get("use_browser_locale", True)),
        # Store creation time for Admin inspection.
        "created_at": utc_now(),
        # Store update time for Admin inspection.
        "updated_at": utc_now(),
    }
    # Append the new user before applying the ledger grant.
    state["users"].append(user)
    # Persist user metadata before ledger crediting so details can reference the id.
    _save_admin_users(state)
    # Branch when Admin grants starting tokens.
    if initial_tokens:
        # Credit the linked wallet through the ledger to preserve token invariants.
        ledger.credit(player["player_id"], initial_tokens, "ADMIN_TOKEN_GRANT", "admin", None, {"reason": "admin_user_create", "user_id": user["user_id"]})
    # Return the public user plus the temporary password for one-time Admin handoff.
    return {"user": _public_admin_user(user), "temporary_password": password}


# Define the set_admin_user_status function used by this module.
def set_admin_user_status(user_id, status):
    # Set state to the persisted Admin user registry.
    state = _load_admin_users()
    # Set user to the requested account record.
    user = _user_by_id(state, user_id)
    # Set user["status"] to the requested active/inactive state.
    user["status"] = status
    # Set user["updated_at"] to the current audit timestamp.
    user["updated_at"] = utc_now()
    # Update the linked player status through the public player service.
    players.update_player(user["player_id"], lambda player: player.update({"status": status}))
    # Persist the updated account state.
    _save_admin_users(state)
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
    # Set user["password_hash"] to the new salted verifier.
    user["password_hash"] = _hash_password(password)
    # Set user["password_reset_required"] so the next auth flow can require rotation.
    user["password_reset_required"] = True
    # Increment the password version for Admin inspection.
    user["password_version"] = int(user.get("password_version", 0)) + 1
    # Set user["password_reset_at"] to the current reset audit timestamp.
    user["password_reset_at"] = utc_now()
    # Set user["updated_at"] to the current audit timestamp.
    user["updated_at"] = utc_now()
    # Persist the reset metadata.
    _save_admin_users(state)
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
    # Set user["terms_accepted_at"] based on the requested status.
    user["terms_accepted_at"] = utc_now() if accepted else None
    # Set user["updated_at"] to the current audit timestamp.
    user["updated_at"] = utc_now()
    # Persist the terms status update.
    _save_admin_users(state)
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
        return {"bots": profiles.list_bots(), "capabilities": profiles.capabilities()}
