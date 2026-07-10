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
from casino.config import AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME, AUTH_BOOTSTRAP_ADMIN_EMAIL, AUTH_BOOTSTRAP_ADMIN_PASSWORD, AUTH_SESSION_COOKIE, AUTH_SESSION_TTL_SECONDS, DATA_DIR, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core import players
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json, write_json
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ForbiddenError, UnauthorizedError, ValidationError

# Set USERS_PATH to the value needed for the next operation.
USERS_PATH = DATA_DIR / "auth" / "users.json"
# Set SESSIONS_PATH to the value needed for the next operation.
SESSIONS_PATH = DATA_DIR / "auth" / "sessions.json"
# Set PASSWORD_ITERATIONS to the value needed for the next operation.
PASSWORD_ITERATIONS = 120_000
# Set PUBLIC_API_PATHS to the value needed for the next operation.
PUBLIC_API_PATHS = {"/api/v2/auth/login"}

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
        # Set salt to the value needed for the next operation.
        salt = base64.b64decode(salt_text.encode("ascii"))
        # Set expected to the value needed for the next operation.
        expected = base64.b64decode(digest_text.encode("ascii"))
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
    # Return the computed value to the caller.
    return {key: value for key, value in user.items() if key != "password_hash"}

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
def create_user(email: str, password: str, display_name: str, role: str = "player", player_id: str | None = None, terms_required: bool = True) -> dict:
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
    user = {"user_id": new_id("user"), "email": normalized, "display_name": display_name.strip() or normalized, "role": role, "status": "active", "player_id": bound_player["player_id"], "password_hash": hash_password(password), "terms_required": terms_required, "terms_accepted_at": None, "created_at": now, "updated_at": now, "identity_provider": "local"}
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("users", []).append(user)
    # Execute this statement as part of the module's documented control flow.
    save_users(state)
    # Return the computed value to the caller.
    return user

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

# Define the prune_sessions function used by this module.
def prune_sessions(state: dict) -> dict:
    # Set now to the value needed for the next operation.
    now = utc_datetime()
    # Set state["sessions"] to the value needed for the next operation.
    state["sessions"] = [session for session in state.get("sessions", []) if session.get("status") == "active" and parse_time(session.get("expires_at", "1970-01-01T00:00:00Z")) > now]
    # Return the computed value to the caller.
    return state

# Define the create_session function used by this module.
def create_session(user: dict, client: str = "") -> dict:
    # Set state to the value needed for the next operation.
    state = prune_sessions(load_sessions())
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set session to the value needed for the next operation.
    session = {"session_id": new_id("session"), "user_id": user["user_id"], "token": secrets.token_urlsafe(32), "status": "active", "created_at": now, "updated_at": now, "expires_at": session_expiry(), "client": client}
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("sessions", []).append(session)
    # Execute this statement as part of the module's documented control flow.
    save_sessions(state)
    # Return the computed value to the caller.
    return session

# Define the public_session function used by this module.
def public_session(session: dict) -> dict:
    # Return the computed value to the caller.
    return {key: value for key, value in session.items() if key != "token"}

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
    # Set session to the value needed for the next operation.
    session = create_session(user, client)
    # Return the computed value to the caller.
    return {"user": public_user(user), "session": {**public_session(session), "token": session["token"]}, "player": players.get_player(user["player_id"])}

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
    cookie = SimpleCookie(cookie_header)
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
    # Set state to the value needed for the next operation.
    state = prune_sessions(load_sessions())
    # Execute this statement as part of the module's documented control flow.
    save_sessions(state)
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
    # Set state to the value needed for the next operation.
    state = load_sessions()
    # Set changed to the value needed for the next operation.
    changed = False
    # Iterate through the collection to process each item.
    for session in state.get("sessions", []):
        # Branch when the session token matches.
        if token and hmac.compare_digest(session.get("token", ""), token):
            # Set session["status"] to the value needed for the next operation.
            session["status"] = "revoked"
            # Set session["updated_at"] to the value needed for the next operation.
            session["updated_at"] = utc_now()
            # Set changed to the value needed for the next operation.
            changed = True
    # Execute this statement as part of the module's documented control flow.
    save_sessions(state)
    # Return the computed value to the caller.
    return {"logged_out": changed}

# Define the current_user_payload function used by this module.
def current_user_payload(session: dict, user: dict) -> dict:
    # Set player to the value needed for the next operation.
    player = players.get_player(user["player_id"])
    # Return the computed value to the caller.
    return {"user": public_user(user), "session": public_session(session), "player": player, "terms": terms_status(user)}

# Define the terms_status function used by this module.
def terms_status(user: dict) -> dict:
    # Set required to the value needed for the next operation.
    required = bool(user.get("terms_required", True))
    # Set accepted_at to the value needed for the next operation.
    accepted_at = user.get("terms_accepted_at")
    # Return the computed value to the caller.
    return {"required": required, "accepted": (not required) or bool(accepted_at), "accepted_at": accepted_at}

# Define the cookie_header function used by this module.
def cookie_header(token: str) -> tuple[str, str]:
    # Return the computed value to the caller.
    return ("Set-Cookie", f"{AUTH_SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax")

# Define the clear_cookie_header function used by this module.
def clear_cookie_header() -> tuple[str, str]:
    # Return the computed value to the caller.
    return ("Set-Cookie", f"{AUTH_SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")

# Define the is_public_api_path function used by this module.
def is_public_api_path(path: str) -> bool:
    # Return the computed value to the caller.
    return path in PUBLIC_API_PATHS
