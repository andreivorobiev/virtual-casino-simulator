# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import base64
# Import required dependency so this module can use its public functions or constants.
import hashlib
# Import required dependency so this module can use its public functions or constants.
import hmac
# Import required dependency so this module can use its public functions or constants.
import secrets
# Import required dependency so this module can use its public functions or constants.
from datetime import datetime, timedelta, timezone
# Import required dependency so this module can use its public functions or constants.
from http.cookies import SimpleCookie
# Import required dependency so this module can use its public functions or constants.
from casino.config import AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME, AUTH_BOOTSTRAP_ADMIN_EMAIL, AUTH_BOOTSTRAP_ADMIN_PASSWORD, AUTH_SESSION_COOKIE, AUTH_SESSION_TTL_SECONDS, DATA_DIR, GUEST_INACTIVITY_SECONDS, GUEST_LIFETIME_SECONDS, GUEST_STARTING_BALANCE, GUEST_TRIALS_ENABLED, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core import players
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json, write_json, update_json
# Import restricted-preview cookie helpers without coupling the auth store to WSGI.
from casino.core.security import clear_csrf_cookie_header, csrf_cookie_header, new_csrf_token
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ForbiddenError, UnauthorizedError, ValidationError

# Set USERS_PATH to the value needed for the next operation.
USERS_PATH = DATA_DIR / "auth" / "users.json"
# Set SESSIONS_PATH to the value needed for the next operation.
SESSIONS_PATH = DATA_DIR / "auth" / "sessions.json"
# Set PASSWORD_ITERATIONS to the value needed for the next operation.
PASSWORD_ITERATIONS = 120_000
# Set PUBLIC_API_PATHS to the value needed for the next operation.
PUBLIC_API_PATHS = {"/api/v2/auth/login", "/api/v2/auth/guest", "/healthz"}
# Bound the accepted session lifetime to the restricted-preview review interval.
MAX_SESSION_TTL_SECONDS = 86_400
# Retain at most one thousand active session records across the single-node preview.
MAX_STORED_SESSIONS = 1_000
# Retain multiple concurrent sessions per account so simultaneous logins never evict each other. (SESSION-007)
MAX_SESSIONS_PER_USER = 256
# Enumerate durable account fields whose change invalidates existing privileges.
PRIVILEGE_FIELDS = ("role", "roles", "status", "password_hash", "password_version")

# Define the utc_datetime function used by this module.
def utc_datetime() -> datetime:
    # Return the computed value to the caller.
    return datetime.now(timezone.utc)

# Define the parse_time function used by this module.
def parse_time(value: str) -> datetime:
    # Return the computed value to the caller.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

# Define the default_users function used by this module.
def default_users() -> dict:
    # Return the computed value to the caller.
    return {"schema_version": SCHEMA_VERSION, "users": []}

# Define the default_sessions function used by this module.
def default_sessions() -> dict:
    # Return the computed value to the caller.
    return {"schema_version": SCHEMA_VERSION, "sessions": []}

# Define the load_users function used by this module.
def load_users() -> dict:
    # Set state to the value needed for the next operation.
    state = read_json(USERS_PATH, default_users)
    # Branch when the following condition is true.
    if not isinstance(state, dict) or "users" not in state:
        # Set state to the value needed for the next operation.
        state = default_users()
    # Return the computed value to the caller.
    return state

# Define the save_users function used by this module.
def save_users(state: dict) -> None:
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Execute this statement as part of the module's documented control flow.
    write_json(USERS_PATH, state)

# Define the load_sessions function used by this module.
def load_sessions() -> dict:
    # Set state to the value needed for the next operation.
    state = read_json(SESSIONS_PATH, default_sessions)
    # Branch when the following condition is true.
    if not isinstance(state, dict) or "sessions" not in state:
        # Set state to the value needed for the next operation.
        state = default_sessions()
    # Return the computed value to the caller.
    return state

# Define the save_sessions function used by this module.
def save_sessions(state: dict) -> None:
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Execute this statement as part of the module's documented control flow.
    write_json(SESSIONS_PATH, state)

# Define the export_auth_state function used by this module.
def export_auth_state() -> dict:
    # Return the computed value to the caller.
    return {"users": load_users(), "sessions": load_sessions()}

# Define the import_auth_state function used by this module.
def import_auth_state(snapshot: dict) -> None:
    # Branch when the snapshot includes user data to restore.
    if snapshot.get("users"):
        # Execute this statement as part of the module's documented control flow.
        save_users(snapshot["users"])
    # Branch when the snapshot includes session data to restore.
    if snapshot.get("sessions"):
        # Execute this statement as part of the module's documented control flow.
        save_sessions(snapshot["sessions"])

# Define the normalize_email function used by this module.
def normalize_email(email: str) -> str:
    # Return the computed value to the caller.
    return (email or "").strip().lower()

# Define the hash_password function used by this module.
def hash_password(password: str, salt: bytes | None = None) -> str:
    # Branch when the caller did not provide a salt.
    if salt is None:
        # Set salt to the value needed for the next operation.
        salt = secrets.token_bytes(16)
    # Set digest to the value needed for the next operation.
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    # Return the computed value to the caller.
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.b64encode(salt).decode('ascii')}${base64.b64encode(digest).decode('ascii')}"

# Define the verify_password function used by this module.
def verify_password(password: str, encoded: str) -> bool:
    # Start protected logic so malformed hashes fail closed.
    try:
        # Set algorithm,iterations,salt_text,digest_text to the value needed for the next operation.
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        # Branch when the stored algorithm is unsupported.
        if algorithm != "pbkdf2_sha256":
            # Return the computed value to the caller.
            return False
        # Decode canonical base64 verifiers while retaining compatibility with the legacy Admin hex format.
        legacy_hex = len(salt_text) == 24 and len(digest_text) == 64
        # Decode the salt using the format identified above.
        salt = salt_text.encode("ascii") if legacy_hex else base64.b64decode(salt_text.encode("ascii"))
        # Decode the expected digest using the same stored verifier format.
        expected = bytes.fromhex(digest_text) if legacy_hex else base64.b64decode(digest_text.encode("ascii"))
        # Set actual to the value needed for the next operation.
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        # Return the computed value to the caller.
        return hmac.compare_digest(actual, expected)
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Return the computed value to the caller.
        return False

# Define the public_user function used by this module.
def public_user(user: dict) -> dict:
    # Copy the durable identity without exposing its password verifier.
    result = {key: value for key, value in user.items() if key != "password_hash"}
    # Publish the username alias required by the v2 contract while email remains compatible.
    result["username"] = user.get("username") or user.get("email", "")
    # Publish the canonical role list while retaining the historical singular role field.
    result["roles"] = list(user.get("roles") or [user.get("role", "player")])
    # Publish the contract's active flag from the durable status value.
    result["active"] = user.get("status") == "active"
    # Publish the canonical locale from legacy or current account metadata.
    result["locale"] = user.get("locale") or user.get("language") or "en-US"
    # Return the contract-compatible identity summary.
    return result

# Define the find_user_by_email function used by this module.
def find_user_by_email(email: str) -> dict | None:
    # Set target to the value needed for the next operation.
    target = normalize_email(email)
    # Iterate through the collection to process each item.
    for user in load_users().get("users", []):
        # Branch when the following condition is true.
        if user.get("email") == target:
            # Return the computed value to the caller.
            return user
    # Return the computed value to the caller.
    return None

# Define the find_user_by_id function used by this module.
def find_user_by_id(user_id: str) -> dict | None:
    # Iterate through the collection to process each item.
    for user in load_users().get("users", []):
        # Branch when the following condition is true.
        if user.get("user_id") == user_id:
            # Return the computed value to the caller.
            return user
    # Return the computed value to the caller.
    return None

# Define the create_user function used by this module.
def create_user(email: str, password: str, display_name: str, role: str = "player", player_id: str | None = None, terms_required: bool = True, locale: str = "en-US") -> dict:
    # Set normalized to the value needed for the next operation.
    normalized = normalize_email(email)
    # Branch when the following condition is true.
    if not normalized:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("email is required")
    # Branch when the following condition is true.
    if not password:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("password is required")
    # Set state to the value needed for the next operation.
    state = load_users()
    # Branch when the following condition is true.
    if any(user.get("email") == normalized for user in state.get("users", [])):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("email already exists")
    # Set bound_player to the value needed for the next operation.
    bound_player = players.ensure_player_for_user(normalized, display_name, player_id)
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set user to the value needed for the next operation.
    user = {"user_id": new_id("user"), "email": normalized, "username": normalized, "display_name": display_name.strip() or normalized, "role": role, "roles": [role], "status": "active", "player_id": bound_player["player_id"], "password_hash": hash_password(password), "terms_required": terms_required, "terms_accepted_at": None, "locale": locale or "en-US", "language": locale or "en-US", "created_at": now, "updated_at": now, "identity_provider": "local"}
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("users", []).append(user)
    # Execute this statement as part of the module's documented control flow.
    save_users(state)
    # Return the computed value to the caller.
    return user

# Report whether an identity record is a disposable guest-trial principal. (issue #317)
def is_guest(user: dict) -> bool:
    # Recognize a guest only by the dedicated role and provider so admin or player authority is never inferred.
    return bool(user) and "guest" in roles_for_user(user) and str(user.get("identity_provider") or "").lower() == "guest"

# Compute the absolute-lifetime expiry for a new guest trial in the shared session timestamp format. (issue #317)
def guest_session_expiry() -> str:
    # Cap the guest at the configured absolute lifetime regardless of activity.
    return (utc_datetime() + timedelta(seconds=GUEST_LIFETIME_SECONDS)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

# Create one isolated, disposable guest-trial principal, wallet, and browser session. (issue #317)
def create_guest(client: str = "") -> dict:
    # Fail closed when the configuration-driven account-free entry is disabled.
    if not GUEST_TRIALS_ENABLED:
        # Never mint a guest principal outside the enabled restricted-preview entry.
        raise ForbiddenError("Guest trials are not available")
    # Seed a brand-new isolated player wallet with the configured non-cashable starting balance.
    guest_player = players.create_player("Guest trial", "guest", GUEST_STARTING_BALANCE)
    # Capture the creation instant for the record and analytics bounds.
    now = utc_now()
    # Resolve the absolute-lifetime expiry the session must not outlive.
    expires_at = guest_session_expiry()
    # Build a credential-free guest identity bound only to its own fresh player and holding the non-privileged guest role.
    user = {"user_id": new_id("guest"), "email": None, "username": None, "display_name": "Guest trial", "role": "guest", "roles": ["guest"], "status": "active", "player_id": guest_player["player_id"], "password_hash": "", "terms_required": False, "terms_accepted_at": now, "locale": "en-US", "language": "en-US", "created_at": now, "updated_at": now, "identity_provider": "guest", "guest": True, "guest_expires_at": expires_at}
    # Persist the guest identity through the same atomic user store as registered accounts.
    def add_user(state: dict) -> dict:
        # Normalize malformed state before appending the new guest identity.
        if not isinstance(state, dict) or "users" not in state:
            state = default_users()
        # Append the credential-free guest identity.
        state.setdefault("users", []).append(user)
        # Return the mutated user document for atomic persistence.
        return state
    update_json(USERS_PATH, add_user, default_users)
    # Issue a browser session for the guest identity.
    session = create_session(user, client)
    # Tighten the persisted session expiry from the registered-user TTL down to the guest lifetime cap.
    def cap_expiry(state: dict) -> dict:
        # Apply the guest lifetime to only this session record.
        for stored in state.get("sessions", []):
            # Match the freshly issued guest session by id.
            if stored.get("session_id") == session["session_id"]:
                # Overwrite its expiry with the guest lifetime bound.
                stored["expires_at"] = expires_at
        # Return the mutated session document for atomic persistence.
        return state
    update_json(SESSIONS_PATH, cap_expiry, default_sessions)
    # Reflect the capped expiry on the returned session copy for the caller.
    session["expires_at"] = expires_at
    # Return the guest principal and its session to the endpoint layer.
    return {"user": user, "session": session}

# Irreversibly end a guest trial so no cookie can restore its wallet, game state, history, or identity. (issue #317)
def end_guest_trial(user: dict) -> None:
    # Ignore any non-guest caller so a registered identity can never be revoked here.
    if not is_guest(user):
        # Return without action for non-guest principals.
        return
    # Remove every session belonging to the guest so the browser cookie stops resolving immediately.
    def revoke_sessions(state: dict) -> dict:
        # Drop the guest's sessions entirely, leaving no resumable credential.
        state["sessions"] = [stored for stored in state.get("sessions", []) if stored.get("user_id") != user["user_id"]]
        # Return the mutated session document for atomic persistence.
        return state
    update_json(SESSIONS_PATH, revoke_sessions, default_sessions)
    # Disable the guest identity so any stale token fails closed even before pruning.
    def disable_user(state: dict) -> dict:
        # Mark the guest identity ended without reusing it for any future authentication.
        for stored in state.get("users", []):
            # Match the guest identity by id.
            if stored.get("user_id") == user["user_id"]:
                # End the identity so its token can never resolve again.
                stored["status"] = "ended"
                # Stamp the update time for analytics and audit.
                stored["updated_at"] = utc_now()
        # Return the mutated user document for atomic persistence.
        return state
    update_json(USERS_PATH, disable_user, default_users)

# Build the guest browser-session cookie so closing the browser drops the disposable trial. (issue #317)
def guest_cookie_headers(session: dict, same_site: str = "Lax", secure: bool = False, include_csrf: bool = False) -> list[tuple[str, str]]:
    # Add Secure for the production boundary while preserving local HTTP developer compatibility.
    secure_attribute = "; Secure" if secure else ""
    # Omit Max-Age and Expires so the credential is a browser-session cookie cleared when the browser closes.
    headers = [("Set-Cookie", f"{AUTH_SESSION_COOKIE}={session['token']}; Path=/; HttpOnly{secure_attribute}; SameSite={same_site}")]
    # Add the browser-readable CSRF companion only in the production security boundary.
    if include_csrf:
        # Rotate the double-submit value to the guest session CSRF token.
        headers.append(csrf_cookie_header(session["csrf_token"], same_site, secure))
    # Return the guest session cookie set for response context extension.
    return headers

# Define the set_user_status function used by this module.
def set_user_status(email: str, status: str) -> dict:
    # Set normalized to the value needed for the next operation.
    normalized = normalize_email(email)
    # Set state to the value needed for the next operation.
    state = load_users()
    # Iterate through the collection to process each item.
    for user in state.get("users", []):
        # Branch when the following condition is true.
        if user.get("email") == normalized:
            # Set user["status"] to the value needed for the next operation.
            user["status"] = status
            # Set user["updated_at"] to the value needed for the next operation.
            user["updated_at"] = utc_now()
            # Execute this statement as part of the module's documented control flow.
            save_users(state)
            # Return the computed value to the caller.
            return user
    # Raise an error so invalid input or state is reported explicitly.
    raise ValidationError("user was not found")


# Define roles_for_user so authorization reads old and new identity records consistently.
def roles_for_user(user: dict) -> list[str]:
    # Return a normalized role list from the canonical collection or legacy singular value.
    return [str(role).lower() for role in (user.get("roles") or [user.get("role", "player")])]


# Define is_admin so all Admin APIs share one authorization decision.
def is_admin(user: dict) -> bool:
    # Return whether the authenticated active identity has the Admin role.
    return user.get("status") == "active" and "admin" in roles_for_user(user)


# Define require_admin so protected Admin endpoints fail closed before dispatch.
def require_admin(user: dict) -> None:
    # Reject authenticated users that do not hold the Admin role.
    if not is_admin(user):
        # Raise the standard forbidden response without exposing Admin data.
        raise ForbiddenError("Admin role is required")


# Define update_user_by_id so Admin and current-user flows mutate the canonical identity store.
def update_user_by_id(user_id: str, updater) -> dict:
    # Load the canonical user registry before applying an account mutation.
    state = load_users()
    # Iterate through identities to find the requested durable account.
    for user in state.get("users", []):
        # Branch when the durable user id matches the request.
        if user.get("user_id") == user_id:
            # Snapshot only privilege-bearing fields before the caller mutates the account.
            prior_privileges = tuple(user.get(field) for field in PRIVILEGE_FIELDS)
            # Apply the caller-owned mutation to the canonical record.
            updater(user)
            # Snapshot the same fields after mutation for an exact privilege-change decision.
            current_privileges = tuple(user.get(field) for field in PRIVILEGE_FIELDS)
            # Refresh the account audit timestamp after the mutation.
            user["updated_at"] = utc_now()
            # Persist the canonical registry after a successful mutation.
            save_users(state)
            # Invalidate every predecessor when role, status, or credential authority changed.
            if current_privileges != prior_privileges:
                # Force the affected identity to authenticate into a freshly rotated session.
                revoke_sessions_for_user(user_id)
            # Return the updated durable identity.
            return user
    # Raise a validation error when no canonical identity matches.
    raise ValidationError("user was not found")


# Define set_user_password so Admin resets produce login-ready canonical credentials.
def set_user_password(user_id: str, password: str) -> dict:
    # Reject empty replacement passwords before hashing.
    if not password:
        # Raise an explicit validation error for the Admin form.
        raise ValidationError("password is required")
    # Update the canonical password verifier and reset metadata together.
    return update_user_by_id(user_id, lambda user: user.update({"password_hash": hash_password(password), "password_reset_required": True, "password_version": int(user.get("password_version", 0)) + 1, "password_reset_at": utc_now()}))


# Define accept_terms so the browser and Admin share canonical terms metadata.
def accept_terms(user_id: str, terms_version: str | None = None, accepted: bool = True, source: str = "current_user") -> dict:
    # Store acceptance or revocation on the canonical identity record.
    return update_user_by_id(user_id, lambda user: user.update({"terms_required": not accepted, "terms_accepted_at": utc_now() if accepted else None, "terms_accepted_version": terms_version if accepted else None, "terms_acceptance_source": source if accepted else None}))

# Define the bootstrap_admin_from_env function used by this module.
def bootstrap_admin_from_env() -> dict:
    # Set existing to the value needed for the next operation.
    existing = find_user_by_email(AUTH_BOOTSTRAP_ADMIN_EMAIL)
    # Branch when an admin user already exists.
    if existing:
        # Return the computed value to the caller.
        return existing
    # Return the computed value to the caller.
    return create_user(AUTH_BOOTSTRAP_ADMIN_EMAIL, AUTH_BOOTSTRAP_ADMIN_PASSWORD, AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME, "admin", "human", False)

# Define the session_expiry function used by this module.
def session_expiry() -> str:
    # Return the computed value to the caller.
    return (utc_datetime() + timedelta(seconds=AUTH_SESSION_TTL_SECONDS)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

# Validate the configured session lifetime before the production worker becomes ready.
def validate_session_bounds() -> None:
    # Reject lifetimes too short for a usable session or longer than the reviewed maximum.
    if AUTH_SESSION_TTL_SECONDS < 300 or AUTH_SESSION_TTL_SECONDS > MAX_SESSION_TTL_SECONDS:
        # Name only the public setting so supplied values never enter diagnostics.
        raise RuntimeError("CASINO_SESSION_TTL_SECONDS is outside the supported restricted-preview range")

# Return whether one stored session is active and unexpired without propagating corrupt timestamps.
def _session_is_active(session: dict, now: datetime) -> bool:
    # Reject non-active records before parsing their expiry.
    if session.get("status") != "active":
        # Exclude revoked and malformed status values from the active registry.
        return False
    # Start protected expiry parsing so a damaged record fails closed.
    try:
        # Require the durable expiry to be later than the supplied UTC time.
        return parse_time(str(session.get("expires_at", ""))) > now
    # Treat missing, malformed, and non-string timestamps as expired.
    except (TypeError, ValueError):
        # Avoid retaining a session whose expiration cannot be proven.
        return False

# Define the prune_sessions function used by this module.
def prune_sessions(state: dict) -> dict:
    # Set now to the value needed for the next operation.
    now = utc_datetime()
    # Set state["sessions"] to the value needed for the next operation.
    state["sessions"] = [session for session in state.get("sessions", []) if isinstance(session, dict) and _session_is_active(session, now)][-MAX_STORED_SESSIONS:]
    # Return the computed value to the caller.
    return state

# Evict the least-recently-used active predecessors once one identity exceeds the per-user cap. (SESSION-007)
def _evict_user_sessions_over_cap(state: dict, user_id: str) -> None:
    # Collect this identity's active sessions in stored (oldest-first) order.
    active = [session for session in state.get("sessions", []) if session.get("user_id") == user_id and session.get("status") == "active"]
    # Compute how many predecessors exceed capacity while leaving room for the new session.
    overflow = len(active) - (MAX_SESSIONS_PER_USER - 1)
    # Stop when the identity is already within its retained per-user capacity.
    if overflow <= 0:
        # Return without evicting because no predecessor exceeds the cap.
        return
    # Order the identity's sessions by last use so the least-recently-used are evicted first.
    ordered = sorted(active, key=lambda session: (str(session.get("updated_at", "")), str(session.get("created_at", ""))))
    # Select the exact least-recently-used predecessors that must be evicted.
    evicted_ids = {session.get("session_id") for session in ordered[:overflow]}
    # Drop only the evicted predecessors while preserving every other stored session.
    state["sessions"] = [session for session in state.get("sessions", []) if session.get("session_id") not in evicted_ids]

# Define the create_session function used by this module.
def create_session(user: dict, client: str = "") -> dict:
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Build the durable session record with independent bearer and CSRF material.
    session = {"session_id": new_id("session"), "user_id": user["user_id"], "token": secrets.token_urlsafe(32), "csrf_token": new_csrf_token(), "status": "active", "created_at": now, "updated_at": now, "expires_at": session_expiry(), "client": client}
    # Define the atomic mutation that preserves concurrent same-user sessions. (SESSION-007)
    def mutate(state: dict) -> dict:
        # Normalize malformed persisted state into the canonical sessions container.
        if not isinstance(state, dict) or "sessions" not in state:
            # Reset to a fresh default sessions document before mutation.
            state = default_sessions()
        # Drop expired records and enforce the global retention cap before adding the replacement.
        prune_sessions(state)
        # Enforce the per-user cap by evicting least-recently-used predecessors instead of all of them.
        _evict_user_sessions_over_cap(state, user["user_id"])
        # Append the newly issued active session for this identity.
        state.setdefault("sessions", []).append(session)
        # Stamp the schema version consistent with save_sessions.
        state["schema_version"] = SCHEMA_VERSION
        # Return the mutated state for atomic persistence.
        return state
    # Persist the new session atomically so concurrent logins cannot lose each other's writes. (SESSION-007, CORE-021)
    update_json(SESSIONS_PATH, mutate, default_sessions)
    # Return the issued session to the caller.
    return session

# Define the public_session function used by this module.
def public_session(session: dict) -> dict:
    # Copy public session metadata without exposing the bearer token.
    result = {key: value for key, value in session.items() if key not in {"token", "client"}}
    # Publish the contract's issued_at alias from the durable creation timestamp.
    result["issued_at"] = session.get("issued_at") or session.get("created_at")
    # Return the contract-compatible session summary.
    return result

# Define the login function used by this module.
def login(email: str, password: str, client: str = "") -> dict:
    # Set user to the value needed for the next operation.
    user = find_user_by_email(email)
    # Branch when credentials do not match an active local user.
    if not user or not verify_password(password or "", user.get("password_hash", "")):
        # Raise an error so invalid input or state is reported explicitly.
        raise UnauthorizedError("Invalid email or password")
    # Branch when the user was disabled by an administrator.
    if user.get("status") != "active":
        # Raise an error so invalid input or state is reported explicitly.
        raise ForbiddenError("User is inactive")
    # Keep the restricted preview on manually provisioned local identities only.
    if str(user.get("identity_provider") or "local").lower() != "local":
        # Reject linked-provider identities until the separately held public-launch gate.
        raise ForbiddenError("Local invite access is required")
    # Set session to the value needed for the next operation.
    session = create_session(user, client)
    # Build the same canonical current-user payload used by session and shell refreshes.
    result = current_user_payload(session, user)
    # Include the bearer token for compatible non-cookie API clients.
    result["session"]["token"] = session["token"]
    # Return one authenticated source of truth for identity and wallet state.
    return result

# Define the extract_bearer_token function used by this module.
def extract_bearer_token(headers) -> str:
    # Set auth_header to the value needed for the next operation.
    auth_header = headers.get("Authorization", "")
    # Branch when the header includes a bearer token.
    if auth_header.lower().startswith("bearer "):
        # Return the computed value to the caller.
        return auth_header.split(" ", 1)[1].strip()
    # Return the computed value to the caller.
    return ""

# Define the extract_cookie_token function used by this module.
def extract_cookie_token(headers) -> str:
    # Set cookie_header to the value needed for the next operation.
    cookie_header = headers.get("Cookie", "")
    # Branch when the request has no cookies.
    if not cookie_header:
        # Return the computed value to the caller.
        return ""
    # Set cookie to the value needed for the next operation.
    # Start protected parsing so malformed hostile cookies fail as unauthenticated.
    try:
        # Parse request cookies without logging or reflecting their raw value.
        cookie = SimpleCookie(cookie_header)
    # Treat parser failures as an absent session credential.
    except Exception:
        # Return the same sentinel used when no cookie is present.
        return ""
    # Set morsel to the value needed for the next operation.
    morsel = cookie.get(AUTH_SESSION_COOKIE)
    # Return the computed value to the caller.
    return morsel.value if morsel else ""

# Define the authenticate_token function used by this module.
def authenticate_token(token: str) -> tuple[dict, dict]:
    # Branch when the token is missing.
    if not token:
        # Raise an error so invalid input or state is reported explicitly.
        raise UnauthorizedError()
    # Read a pruned in-memory view without persisting so concurrent logins are not clobbered. (SESSION-007)
    state = prune_sessions(load_sessions())
    # Iterate through the collection to process each item.
    for session in state.get("sessions", []):
        # Branch when the session token matches.
        if hmac.compare_digest(session.get("token", ""), token):
            # Set user to the value needed for the next operation.
            user = find_user_by_id(session.get("user_id", ""))
            # Branch when the session has no active user.
            if not user or user.get("status") != "active":
                # Raise an error so invalid input or state is reported explicitly.
                raise ForbiddenError("User is inactive")
            # Return the computed value to the caller.
            return session, user
    # Raise an error so invalid input or state is reported explicitly.
    raise UnauthorizedError("Session is invalid or expired")

# Define the authenticate_headers function used by this module.
def authenticate_headers(headers) -> tuple[dict, dict]:
    # Set token to the value needed for the next operation.
    token = extract_bearer_token(headers) or extract_cookie_token(headers)
    # Return the computed value to the caller.
    return authenticate_token(token)

# Define the logout function used by this module.
def logout(token: str) -> dict:
    # Track whether any stored session matched the supplied bearer token.
    changed = {"value": False}
    # Define the atomic revocation that only touches the matching session record. (SESSION-007)
    def mutate(state: dict) -> dict:
        # Normalize malformed persisted state into the canonical sessions container.
        if not isinstance(state, dict) or "sessions" not in state:
            # Reset to a fresh default sessions document before mutation.
            state = default_sessions()
        # Iterate through the collection to process each item.
        for session in state.get("sessions", []):
            # Branch when the session token matches.
            if token and hmac.compare_digest(session.get("token", ""), token):
                # Set session["status"] to the value needed for the next operation.
                session["status"] = "revoked"
                # Set session["updated_at"] to the value needed for the next operation.
                session["updated_at"] = utc_now()
                # Record that at least one matching session was revoked.
                changed["value"] = True
        # Stamp the schema version consistent with save_sessions.
        state["schema_version"] = SCHEMA_VERSION
        # Return the mutated state for atomic persistence.
        return state
    # Persist the revocation atomically so a concurrent login is never clobbered. (SESSION-007)
    update_json(SESSIONS_PATH, mutate, default_sessions)
    # Return the computed value to the caller.
    return {"logged_out": changed["value"]}

# Revoke every active session owned by one account after a privilege change.
def revoke_sessions_for_user(user_id: str) -> int:
    # Count changed records without retaining any token value.
    changed = {"value": 0}
    # Define the atomic account-scoped revocation applied under the session-file lock. (SESSION-007, SESSION-006)
    def mutate(state: dict) -> dict:
        # Normalize malformed persisted state into the canonical sessions container.
        if not isinstance(state, dict) or "sessions" not in state:
            # Reset to a fresh default sessions document before mutation.
            state = default_sessions()
        # Iterate through stored sessions without comparing caller-supplied credentials.
        for session in state.get("sessions", []):
            # Revoke only active records for the selected durable identity.
            if session.get("user_id") == user_id and session.get("status") == "active":
                # Mark the predecessor unusable immediately.
                session["status"] = "revoked"
                # Record a bounded audit timestamp without user or token data.
                session["updated_at"] = utc_now()
                # Count the revoked record for focused tests.
                changed["value"] += 1
        # Stamp the schema version consistent with save_sessions.
        state["schema_version"] = SCHEMA_VERSION
        # Return the mutated state for atomic persistence.
        return state
    # Persist the account-scoped revocation result atomically.
    update_json(SESSIONS_PATH, mutate, default_sessions)
    # Return only the number of invalidated predecessors.
    return changed["value"]

# Define the current_user_payload function used by this module.
def current_user_payload(session: dict, user: dict) -> dict:
    # Set player to the value needed for the next operation.
    player = players.get_player(user["player_id"])
    # Publish one authenticated player summary with an explicit play-token balance field.
    player_summary = {**player, "token_balance": round(float(player.get("balance", 0)), 2), "token_label": "play tokens"}
    # Return the canonical current-user payload used by login, session, shell, and wallet refreshes.
    return {"user": public_user(user), "session": public_session(session), "player": player_summary, "terms": terms_status(user)}

# Define the terms_status function used by this module.
def terms_status(user: dict) -> dict:
    # Set required to the value needed for the next operation.
    required = bool(user.get("terms_required", True)) and not bool(user.get("terms_accepted_at"))
    # Set accepted_at to the value needed for the next operation.
    accepted_at = user.get("terms_accepted_at")
    # Return the computed value to the caller.
    return {"required": required, "required_version": "private-beta-1", "accepted": not required, "accepted_version": user.get("terms_accepted_version"), "accepted_at": accepted_at}

# Define the cookie_header function used by this module.
def cookie_header(token: str, same_site: str = "Lax", secure: bool = False) -> tuple[str, str]:
    # Add Secure for every production cookie while preserving local HTTP developer compatibility.
    secure_attribute = "; Secure" if secure else ""
    # Omit Domain so the credential remains host-only and bound its lifetime explicitly.
    return ("Set-Cookie", f"{AUTH_SESSION_COOKIE}={token}; Path=/; Max-Age={AUTH_SESSION_TTL_SECONDS}; HttpOnly{secure_attribute}; SameSite={same_site}")

# Build all session-establishment cookies for browser and compatible API clients.
def session_cookie_headers(session: dict, same_site: str = "Lax", secure: bool = False, include_csrf: bool = False) -> list[tuple[str, str]]:
    # Start with the host-only HttpOnly session credential.
    headers = [cookie_header(session["token"], same_site, secure)]
    # Add the browser-readable CSRF companion only in the production security boundary.
    if include_csrf:
        # Rotate the double-submit value to the newly issued session CSRF token.
        headers.append(csrf_cookie_header(session["csrf_token"], same_site, secure))
    # Return a fresh list suitable for response context extension.
    return headers

# Define the clear_cookie_header function used by this module.
def clear_cookie_header(same_site: str = "Lax", secure: bool = False) -> tuple[str, str]:
    # Add Secure consistently with the credential being removed.
    secure_attribute = "; Secure" if secure else ""
    # Clear the host-only credential with both Max-Age and an epoch expiry.
    return ("Set-Cookie", f"{AUTH_SESSION_COOKIE}=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly{secure_attribute}; SameSite={same_site}")

# Build all logout cookie expirations for the production browser boundary.
def clear_cookie_headers(same_site: str = "Lax", secure: bool = False, include_csrf: bool = False) -> list[tuple[str, str]]:
    # Start with the authenticated session credential expiration.
    headers = [clear_cookie_header(same_site, secure)]
    # Clear the companion double-submit cookie when production set it.
    if include_csrf:
        # Prevent stale browser CSRF values from surviving logout.
        headers.append(clear_csrf_cookie_header(same_site, secure))
    # Return the complete ordered expiration header set.
    return headers

# Define the is_public_api_path function used by this module.
def is_public_api_path(path: str) -> bool:
    # Return the computed value to the caller.
    return path in PUBLIC_API_PATHS
