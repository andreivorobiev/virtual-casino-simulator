# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import base64
# Import required dependency so this module can use its public functions or constants.
import hashlib
# Import required dependency so this module can use its public functions or constants.
import hmac
# Import regular expressions for exact reviewed public OAuth route matching.
import re
# Import process environment access for the root-managed deployment monitor credential.
import os
# Import required dependency so this module can use its public functions or constants.
import secrets
# Import required dependency so this module can use its public functions or constants.
from datetime import datetime, timedelta, timezone
# Import required dependency so this module can use its public functions or constants.
from http.cookies import SimpleCookie
# Import required dependency so this module can use its public functions or constants.
from casino.config import AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME, AUTH_BOOTSTRAP_ADMIN_EMAIL, AUTH_BOOTSTRAP_ADMIN_PASSWORD, AUTH_SESSION_COOKIE, AUTH_SESSION_TTL_SECONDS, DATA_DIR, GUEST_INACTIVITY_SECONDS, GUEST_LIFETIME_SECONDS, GUEST_MAX_ACTIONS, GUEST_MAX_ACTIVE, GUEST_STARTING_BALANCE, GUEST_TERMS_VERSION, GUEST_TRIALS_ENABLED, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core import players
# Import the de-identified guest-trial telemetry recorder for the Admin Guest Trials section. (issue #317)
from casino.core import guest_analytics
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import normal and strict document boundaries so session control preserves corrupt evidence.
from casino.core.state_store import read_json, read_json_strict, write_json, update_json, update_json_strict
# Import restricted-preview cookie helpers without coupling the auth store to WSGI.
from casino.core.security import csrf_cookie_header, new_csrf_token
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ConflictError, ForbiddenError, RateLimitError, UnauthorizedError, ValidationError

# Set USERS_PATH to the value needed for the next operation.
USERS_PATH = DATA_DIR / "auth" / "users.json"
# Set SESSIONS_PATH to the value needed for the next operation.
SESSIONS_PATH = DATA_DIR / "auth" / "sessions.json"
# Set PASSWORD_ITERATIONS to the value needed for the next operation.
PASSWORD_ITERATIONS = 120_000
# Set PUBLIC_API_PATHS to the value needed for the next operation.
PUBLIC_API_PATHS = {"/api/v2/auth/login", "/api/v2/auth/guest", "/api/v2/auth/redeem-invitation", "/api/v2/auth/enrollment-policy", "/api/v2/auth/signup", "/api/v2/auth/oauth/providers", "/api/v2/auth/csrf", "/healthz"}
# Bound the accepted session lifetime to the restricted-preview review interval.
MAX_SESSION_TTL_SECONDS = 86_400
# Retain at most one thousand active session records across the single-node preview.
MAX_STORED_SESSIONS = 1_000
# Retain multiple concurrent sessions per account so simultaneous logins never evict each other. (SESSION-007)
MAX_SESSIONS_PER_USER = 256
# Name the bootstrap-only authority that can delegate ordinary Admin access. (AUTH-012)
PLATFORM_OWNER_ROLE = "platform_owner"
# Enumerate roles that inherit access to the existing Admin surface. (AUTH-012)
ADMIN_ACCESS_ROLES = frozenset({"admin", PLATFORM_OWNER_ROLE})
# Enumerate durable account fields whose change invalidates existing privileges.
PRIVILEGE_FIELDS = ("role", "roles", "status", "password_hash", "password_version")
# Name the hash-only monitor-token setting used by production deployment checks.
EDGE_MONITOR_TOKEN_SHA256_ENV = "CASINO_EDGE_MONITOR_TOKEN_SHA256"
# Accept only one complete lowercase SHA-256 digest for the monitor-token verifier.
EDGE_MONITOR_TOKEN_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
# Limit the monitor principal to the two read-only Operations probes required by deployment.
MONITOR_AUTH_PATHS = frozenset({"/readyz", "/api/v2/admin/operations"})
# Bound the Admin session inventory so later routes cannot expose an unbounded identity document. (SESSION-008)
MAX_ADMIN_SESSION_RESULTS = 100
# Accept only the stable one-way session alias shape emitted by this module. (SESSION-008)
ADMIN_SESSION_ALIAS_PATTERN = re.compile(r"^[0-9a-f]{16}$")
# Publish only reviewed authentication-method classes instead of arbitrary stored strings. (SESSION-008)
ADMIN_SESSION_AUTH_METHODS = frozenset({"local", "google", "facebook"})
# Publish only reviewed lifecycle classes instead of arbitrary stored strings. (SESSION-008)
ADMIN_SESSION_STATUSES = frozenset({"active", "revoked"})

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
    return {"schema_version": SCHEMA_VERSION, "users": [], "reservations": []}

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
    # Add the compatible reservation collection when reading a pre-invitation identity document.
    state.setdefault("reservations", [])
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

# Enforce the explicit password policy used only by public invitation enrollment. (INVITE-003)
def validate_enrollment_password(password: str) -> None:
    # Require a bounded string so hashing cannot become an unbounded resource sink.
    if not isinstance(password, str) or len(password) < 12 or len(password) > 128:
        # Return one value-free policy error to the invitation facade.
        raise ValidationError("password does not meet enrollment policy")
    # Count independent character classes without retaining any derived password material.
    classes = sum((any(character.islower() for character in password), any(character.isupper() for character in password), any(character.isdigit() for character in password), any(not character.isalnum() for character in password)))
    # Require at least three classes so long single-pattern passwords do not pass accidentally.
    if classes < 3:
        # Keep the policy error free of supplied password details.
        raise ValidationError("password does not meet enrollment policy")

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
    # Copy the durable identity without exposing its password verifier or internal analytics binding.
    result = {key: value for key, value in user.items() if key not in ("password_hash", "guest_analytics_id")}
    # Publish the username alias required by the v2 contract while email remains compatible.
    result["username"] = user.get("username") or user.get("email") or ""
    # Publish the canonical role list while retaining the historical singular role field.
    result["roles"] = list(user.get("roles") or [user.get("role", "player")])
    # Publish the contract's active flag from the durable status value.
    result["active"] = user.get("status") == "active"
    # Publish the canonical locale from legacy or current account metadata.
    result["locale"] = user.get("locale") or user.get("language") or "en-US"
    # Publish the non-authoritative principal class so clients can render guest lifecycle controls explicitly.
    result["principal_type"] = "guest" if is_guest(user) else "account"
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
    # Read current uniqueness and invitation reservations before allocating a player wallet.
    current_state = load_users()
    # Reject a duplicate mailbox before any downstream player side effect.
    if any(user.get("email") == normalized for user in current_state.get("users", [])):
        # Preserve the existing canonical account.
        raise ValidationError("email already exists")
    # Reject a mailbox reserved by an in-progress invitation before creating a player.
    if any(reservation.get("email") == normalized for reservation in current_state.get("reservations", [])):
        # Prevent the normal account path from racing the invitation saga.
        raise ConflictError("email is reserved by an enrollment operation")
    # Set bound_player to the value needed for the next operation.
    bound_player = players.ensure_player_for_user(normalized, display_name, player_id)
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set user to the value needed for the next operation.
    user = {"user_id": new_id("user"), "email": normalized, "username": normalized, "display_name": display_name.strip() or normalized, "role": role, "roles": [role], "status": "active", "player_id": bound_player["player_id"], "password_hash": hash_password(password), "terms_required": terms_required, "terms_accepted_at": None, "locale": locale or "en-US", "language": locale or "en-US", "created_at": now, "updated_at": now, "identity_provider": "local"}
    # Serialize email uniqueness with invitation reservations instead of using a stale load/save pair.
    def append_user(state: dict) -> dict:
        # Preserve legacy documents while rejecting structurally unsafe user collections.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Fail without replacing recoverable identity data.
            raise RuntimeError("Authentication user storage is malformed")
        # Reject a duplicate canonical email inside the provider transaction.
        if any(stored.get("email") == normalized for stored in state.get("users", [])):
            # Preserve the existing account without publishing its identity.
            raise ValidationError("email already exists")
        # Reject email reservations held by an in-progress invitation redemption.
        if any(reservation.get("email") == normalized for reservation in state.setdefault("reservations", [])):
            # Prevent a parallel Admin/user flow from orphaning the invitation saga.
            raise ConflictError("email is reserved by an enrollment operation")
        # Reject a second durable account adopting the same player inside the provider transaction.
        if any(stored.get("player_id") == bound_player["player_id"] and not is_guest(stored) for stored in state.get("users", [])):
            # Preserve exactly one durable account owner for every wallet and ledger identity.
            raise ConflictError("player is already bound to an account")
        # Append the new canonical identity exactly once.
        state["users"].append(user)
        # Return the complete identity document for atomic persistence.
        return state
    # Publish the unique identity through the JSON/MySQL document transaction.
    update_json(USERS_PATH, append_user, default_users)
    # Return the computed value to the caller.
    return user

# Reserve one email for a recoverable invitation saga without creating an account. (INVITE-003)
def reserve_invited_identity(email: str, invitation_id: str, user_id: str, player_id: str, expires_at: str) -> dict:
    # Normalize the mailbox used by every account and invitation lookup.
    normalized = normalize_email(email)
    # Capture the reservation result outside the provider transaction.
    result = {}
    # Insert or replay the exact reservation atomically.
    def reserve(state: dict) -> dict:
        # Reject malformed user state rather than repairing it destructively.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve the original document for operator recovery.
            raise RuntimeError("Authentication user storage is malformed")
        # Reject any already-created canonical account with this mailbox.
        if any(stored.get("email") == normalized and stored.get("invitation_id") != invitation_id for stored in state["users"]):
            # Keep the conflict generic at the invitation boundary.
            raise ConflictError("invited identity conflicts with an existing account")
        # Resolve the compatible reservation collection on older documents.
        reservations = state.setdefault("reservations", [])
        # Search for an existing reservation on this mailbox or invitation.
        for existing in reservations:
            # Return the exact same saga reservation idempotently.
            if existing.get("invitation_id") == invitation_id and existing.get("email") == normalized and existing.get("user_id") == user_id and existing.get("player_id") == player_id:
                # Publish only a detached internal copy.
                result.update(existing)
                # Leave the durable reservation unchanged.
                return state
            # Reject a different saga holding either the mailbox or deterministic identifiers.
            if existing.get("email") == normalized or existing.get("invitation_id") == invitation_id or existing.get("user_id") == user_id or existing.get("player_id") == player_id:
                # Prevent overlapping enrollment ownership.
                raise ConflictError("invited identity reservation conflicts with existing state")
        # Build the account-free reservation row with no password or bearer material.
        reservation = {"invitation_id": invitation_id, "email": normalized, "user_id": user_id, "player_id": player_id, "expires_at": expires_at, "created_at": utc_now()}
        # Append the reservation inside the same uniqueness decision.
        reservations.append(reservation)
        # Publish only the successfully committed metadata to the caller.
        result.update(reservation)
        # Return the complete identity document.
        return state
    # Persist the account-free reservation through the provider transaction.
    update_json(USERS_PATH, reserve, default_users)
    # Return the internal reservation used by the provisioning saga.
    return result

# Release one invitation reservation only while no canonical invited account exists. (INVITE-003)
def release_invited_identity(invitation_id: str) -> bool:
    # Track whether one reservation was removed.
    result = {"released": False}
    # Remove the exact account-free reservation atomically.
    def release(state: dict) -> dict:
        # Reject malformed user state rather than deleting recoverable identity data.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve the original document for operator recovery.
            raise RuntimeError("Authentication user storage is malformed")
        # Keep a reservation once a canonical account references the same invitation.
        if any(stored.get("invitation_id") == invitation_id for stored in state["users"]):
            # Return unchanged state because the provisioning saga owns cleanup.
            return state
        # Resolve the compatible reservation collection.
        reservations = state.setdefault("reservations", [])
        # Remove only the exact invitation reservation.
        retained = [reservation for reservation in reservations if reservation.get("invitation_id") != invitation_id]
        # Publish whether the collection changed.
        result["released"] = len(retained) != len(reservations)
        # Store the retained reservation collection.
        state["reservations"] = retained
        # Return the complete identity document.
        return state
    # Publish the release through the atomic document boundary.
    update_json(USERS_PATH, release, default_users)
    # Return whether an account-free reservation changed.
    return result["released"]

# Provision or resume one invited local account after its token has been consumed. (INVITE-003)
def provision_invited_user(email: str, password: str, display_name: str, locale: str, terms_version: str, invitation_id: str, user_id: str, player_id: str) -> dict:
    # Normalize and validate all recipient-selected identity fields before persistence.
    normalized = normalize_email(email)
    # Enforce the dedicated enrollment password policy before hashing.
    validate_enrollment_password(password)
    # Normalize the bounded visible display name with a mailbox-local fallback.
    label = str(display_name or "").strip()[:80] or normalized.split("@", 1)[0]
    # Restrict enrollment locale to the two translated restricted-preview surfaces.
    accepted_locale = locale if locale in ("en-US", "ru-RU") else "en-US"
    # Capture one provisioning instant used by the first successful attempt.
    now = utc_now()
    # Hash the chosen password before the identity transaction and never persist the raw value.
    password_hash = hash_password(password)
    # Publish the durable identity selected by the transaction.
    result = {}
    # Create or replay the provisioning identity atomically.
    def provision(state: dict) -> dict:
        # Reject malformed user state rather than replacing security-sensitive data.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve the original document for operator recovery.
            raise RuntimeError("Authentication user storage is malformed")
        # Find an idempotent prior provisioning attempt for this invitation.
        existing = next((stored for stored in state["users"] if stored.get("invitation_id") == invitation_id), None)
        # Validate and replay the exact prior identity when it exists.
        if existing is not None:
            # Reject changed identity bindings or password meaning on a reused saga.
            if existing.get("email") != normalized or existing.get("user_id") != user_id or existing.get("player_id") != player_id or not verify_password(password, existing.get("password_hash", "")):
                # Keep the existing account unchanged and fail recovery closed.
                raise ConflictError("invited identity replay conflicts with existing state")
            # Publish the compatible existing identity.
            result.update(existing)
            # Leave durable state unchanged until final activation below.
            return state
        # Reject any unrelated canonical account claiming the invited mailbox.
        if any(stored.get("email") == normalized for stored in state["users"]):
            # Preserve the existing account and require operator resolution.
            raise ConflictError("invited identity conflicts with an existing account")
        # Require the exact account-free reservation established before token consumption.
        reservation = next((reserved for reserved in state.setdefault("reservations", []) if reserved.get("invitation_id") == invitation_id and reserved.get("email") == normalized and reserved.get("user_id") == user_id and reserved.get("player_id") == player_id), None)
        # Fail closed when the recovery boundary is absent or changed.
        if reservation is None:
            # Do not create an unreserved account from caller-owned identifiers.
            raise ConflictError("invited identity reservation is unavailable")
        # Build an inactive provisioning identity only after successful token consumption.
        user = {"user_id": user_id, "email": normalized, "username": normalized, "display_name": label, "role": "player", "roles": ["player"], "status": "provisioning", "player_id": player_id, "password_hash": password_hash, "terms_required": False, "terms_accepted_at": now, "terms_accepted_version": terms_version, "terms_acceptance_source": "invitation_redemption", "locale": accepted_locale, "language": accepted_locale, "created_at": now, "updated_at": now, "identity_provider": "local", "invitation_id": invitation_id}
        # Append the recoverable inactive identity.
        state["users"].append(user)
        # Publish the first provisioning result.
        result.update(user)
        # Return the complete identity document.
        return state
    # Persist or replay the inactive identity under the email reservation.
    update_json(USERS_PATH, provision, default_users)
    # Create or replay the deterministic wallet after the inactive identity is durable.
    players.ensure_invited_player(player_id, label)
    # Activate the identity and release its reservation in one user-document mutation.
    def activate(state: dict) -> dict:
        # Reject malformed state before account activation.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve the original document for recovery.
            raise RuntimeError("Authentication user storage is malformed")
        # Find the exact invited identity to activate.
        user = next((stored for stored in state["users"] if stored.get("invitation_id") == invitation_id and stored.get("user_id") == user_id), None)
        # Refuse to activate an absent or mismatched identity.
        if user is None or user.get("email") != normalized or user.get("player_id") != player_id:
            # Preserve every existing account and wallet binding.
            raise ConflictError("invited identity activation is unavailable")
        # Transition the recoverable identity to an active local account.
        user["status"] = "active"
        # Refresh the lifecycle timestamp on first activation or recovery replay.
        user["updated_at"] = utc_now()
        # Remove the account-free reservation now that canonical uniqueness is owned by the user row.
        state["reservations"] = [reserved for reserved in state.setdefault("reservations", []) if reserved.get("invitation_id") != invitation_id]
        # Publish the active identity to the caller.
        result.clear()
        # Copy the complete active identity for the internal saga.
        result.update(user)
        # Return the complete identity document.
        return state
    # Commit activation and reservation cleanup atomically.
    update_json(USERS_PATH, activate, default_users)
    # Return the durable active local account.
    return result

# Report whether an identity record is a disposable guest-trial principal. (issue #317)
def is_guest(user: dict) -> bool:
    # Recognize a guest only by the dedicated role and provider so admin or player authority is never inferred.
    return bool(user) and "guest" in roles_for_user(user) and str(user.get("identity_provider") or "").lower() == "guest"

# Compute the absolute-lifetime expiry for a new guest trial in the shared session timestamp format. (issue #317)
def guest_session_expiry() -> str:
    # Cap the guest at the configured absolute lifetime regardless of activity.
    return (utc_datetime() + timedelta(seconds=GUEST_LIFETIME_SECONDS)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

# Create one isolated, disposable guest-trial principal, wallet, and browser session. (issue #317)
def create_guest(client: str = "", accepted: bool = False, terms_version: str = "", locale: str = "en-US", device: str = "unknown") -> dict:
    # Fail closed when the configuration-driven account-free entry is disabled.
    if not GUEST_TRIALS_ENABLED:
        # Never mint a guest principal outside the enabled restricted-preview entry.
        raise ForbiddenError("Guest trials are not available")
    # Require the same explicit current-version acceptance used by invited accounts before creating state.
    if accepted is not True or str(terms_version or "").strip() != GUEST_TERMS_VERSION:
        # Reject missing, stale, or implied consent without creating a wallet, identity, or analytics row.
        raise ValidationError("Current guest-trial terms must be accepted")
    # End time-bounded trials before enforcing the anonymous-principal capacity limit.
    expire_overdue_guests()
    # Retain created objects outside the atomic mutation without publishing them before capacity succeeds.
    created = {}
    # Reserve capacity and persist the identity inside one user-store critical section.
    def add_user(state: dict) -> dict:
        # Normalize malformed state before appending the new guest identity.
        if not isinstance(state, dict) or "users" not in state:
            state = default_users()
        # Count active disposable identities inside the same mutation that appends the new one.
        active_guests = sum(1 for stored in state.get("users", []) if is_guest(stored) and stored.get("status") == "active")
        # Reject concurrent excess creation before any wallet or telemetry state is allocated.
        if active_guests >= GUEST_MAX_ACTIVE:
            # Preserve registered-login capacity without leaving an orphan guest resource.
            raise ForbiddenError("Guest trial capacity is temporarily full")
        # Seed a brand-new isolated player wallet only after the atomic capacity decision succeeds.
        guest_player = players.create_player("Guest trial", "guest", GUEST_STARTING_BALANCE)
        # Capture the creation instant for identity and analytics bounds.
        now = utc_now()
        # Resolve the absolute-lifetime expiry the session must not outlive.
        expires_at = guest_session_expiry()
        # Build a credential-free identity bound only to its fresh non-cashable wallet.
        user = {"user_id": new_id("guest"), "email": None, "username": None, "display_name": "Guest trial", "role": "guest", "roles": ["guest"], "status": "active", "player_id": guest_player["player_id"], "password_hash": "", "terms_required": False, "terms_accepted_at": now, "terms_accepted_version": GUEST_TERMS_VERSION, "terms_acceptance_source": "guest_entry", "locale": locale if locale in ("en-US", "ru-RU") else "en-US", "language": locale if locale in ("en-US", "ru-RU") else "en-US", "created_at": now, "updated_at": now, "identity_provider": "guest", "guest": True, "guest_expires_at": expires_at, "guest_analytics_id": guest_analytics.record_started(locale=locale, device=device, starting_balance=GUEST_STARTING_BALANCE)}
        # Append the credential-free guest identity.
        state.setdefault("users", []).append(user)
        # Publish the successfully reserved objects to the post-commit session step.
        created.update({"user": user, "expires_at": expires_at})
        # Return the mutated user document for atomic persistence.
        return state
    # Persist the capacity reservation and identity through the atomic user store.
    update_json(USERS_PATH, add_user, default_users)
    # Read only objects created by the successful atomic mutation.
    user, expires_at = created["user"], created["expires_at"]
    # Issue a browser session for the guest identity.
    session = create_session(user, client)
    # Generate an unguessable browser-context proof returned once and retained only in sessionStorage.
    browser_nonce = secrets.token_urlsafe(32)
    # Persist only a digest so storage disclosure cannot recreate the browser-context proof.
    browser_nonce_hash = hashlib.sha256(browser_nonce.encode("utf-8")).hexdigest()
    # Tighten the persisted session expiry from the registered-user TTL down to the guest lifetime cap.
    def cap_expiry(state: dict) -> dict:
        # Apply the guest lifetime to only this session record.
        for stored in state.get("sessions", []):
            # Match the freshly issued guest session by id.
            if stored.get("session_id") == session["session_id"]:
                # Overwrite its expiry with the guest lifetime bound.
                stored["expires_at"] = expires_at
                # Bind the credential to the creating browser context without retaining the raw proof.
                stored["guest_browser_nonce_hash"] = browser_nonce_hash
        # Return the mutated session document for atomic persistence.
        return state
    update_json(SESSIONS_PATH, cap_expiry, default_sessions)
    # Reflect the capped expiry on the returned session copy for the caller.
    session["expires_at"] = expires_at
    # Reflect only the digest on the internal session copy; the raw proof has a separate one-time field.
    session["guest_browser_nonce_hash"] = browser_nonce_hash
    # Return the guest principal and its session to the endpoint layer.
    return {"user": user, "session": session, "browser_nonce": browser_nonce}

# Irreversibly end a guest trial so no cookie can restore its wallet, game state, history, or identity. (issue #317)
def end_guest_trial(user: dict, reason: str = "ended") -> None:
    # Ignore any non-guest caller so a registered identity can never be revoked here.
    if not is_guest(user):
        # Return without action for non-guest principals.
        return
    # Capture the terminal fake-token balance before revocation for de-identified product aggregates.
    try:
        # Read only the guest-bound wallet selected by the authenticated server identity.
        ending_balance = players.get_player(user.get("player_id"))["balance"]
    # Preserve teardown even if a previously corrupted guest wallet is unavailable.
    except Exception:
        # Omit the optional aggregate rather than weakening credential revocation.
        ending_balance = None
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
    # Import the control-plane helper lazily so auth initialization remains cycle-free.
    from casino.core import autoplay
    # Stop every active guest-owned autoplay registration before revoking its wallet.
    autoplay.stop_for_player(user["player_id"])
    # Irreversibly revoke the disposable wallet pointer and remaining play-token balance.
    players.update_player(user["player_id"], lambda player: player.update({"status": "ended", "balance": 0.0, "display_name": "Ended guest trial", "updated_at": utc_now()}))
    # Close the de-identified trial summary with its bounded end reason for the Admin funnel. (issue #317)
    guest_analytics.record_ended(user.get("guest_analytics_id"), reason, ending_balance=ending_balance)

# Consume one guest game-action allowance before a state-changing route executes. (issue #317)
def consume_guest_action(session: dict, user: dict) -> int:
    # Leave registered identities outside the disposable-session ceiling.
    if not is_guest(user):
        # Return zero so callers can use one uniform control path.
        return 0
    # Track the persisted count returned by the atomic mutation.
    result = {"count": 0, "limited": False}
    # Define the session-scoped allowance update.
    def mutate(state: dict) -> dict:
        # Normalize malformed session storage before searching the authenticated row.
        if not isinstance(state, dict) or not isinstance(state.get("sessions"), list):
            # Replace invalid state with the canonical empty container.
            state = default_sessions()
        # Find only the already-authenticated guest session.
        for stored in state.get("sessions", []):
            # Skip every unrelated or inactive session.
            if stored.get("session_id") != session.get("session_id") or stored.get("status") != "active":
                # Continue without exposing whether another session exists.
                continue
            # Read the current bounded action count.
            current = int(stored.get("guest_action_count") or 0)
            # Reject any request at or beyond the configured ceiling without incrementing it.
            if current >= GUEST_MAX_ACTIONS:
                # Publish only the bounded result to the caller.
                result["limited"] = True
                result["count"] = current
                # Return unchanged session state.
                return state
            # Consume one allowance before the game mutation begins.
            stored["guest_action_count"] = current + 1
            # Publish the accepted count to the authenticated caller.
            result["count"] = current + 1
            # Mirror the count in the in-request session copy for consistent diagnostics.
            session["guest_action_count"] = current + 1
            # Return the mutated session document.
            return state
        # Treat a missing authenticated row as a generic limit failure.
        result["limited"] = True
        # Return state unchanged.
        return state
    # Persist the allowance atomically before gameplay starts.
    update_json(SESSIONS_PATH, mutate, default_sessions)
    # Fail closed with the standard sanitized rate-limit envelope.
    if result["limited"]:
        # Never expose the configured ceiling or current counter.
        raise RateLimitError("Guest trial action limit reached")
    # Return the accepted count for focused tests only.
    return result["count"]

# Lazily end guests whose absolute lifetime has passed so Admin analytics reflect expiry without a background job. (issue #317)
def expire_overdue_guests() -> int:
    # Read the user store once for the bounded expiry sweep.
    state = load_users()
    # Capture the comparison instant for lifetime checks.
    now = utc_datetime()
    # Read active sessions once so inactivity and absolute expiry use the same bounded snapshot.
    sessions = prune_sessions(load_sessions()).get("sessions", [])
    # Index the newest activity timestamp for each disposable identity without retaining credentials.
    last_activity = {}
    # Walk active sessions to build the bounded guest-activity index.
    for session in sessions:
        # Keep the newest timestamp when an identity somehow owns more than one active session.
        last_activity[session.get("user_id")] = max(last_activity.get(session.get("user_id"), ""), str(session.get("updated_at") or session.get("created_at") or ""))
    # Collect active guests past either the absolute lifetime or inactivity boundary.
    overdue = []
    # Evaluate each disposable identity independently so registered accounts remain untouched.
    for user in state.get("users", []):
        # Skip every non-active or non-guest identity before parsing guest-only timestamps.
        if not is_guest(user) or user.get("status") != "active":
            # Continue to the next stored identity.
            continue
        # Detect the configured absolute lifetime boundary.
        absolute_expired = bool(user.get("guest_expires_at")) and parse_time(user["guest_expires_at"]) <= now
        # Resolve the newest server-observed activity, falling back to creation when no session remains.
        activity_at = last_activity.get(user.get("user_id")) or user.get("created_at")
        # Detect the inactivity boundary without depending on client-authored events.
        inactive = bool(activity_at) and (now - parse_time(activity_at)).total_seconds() >= GUEST_INACTIVITY_SECONDS
        # Queue either time-bounded outcome for the standard irreversible teardown.
        if absolute_expired or inactive:
            # Retain only the user object needed by the teardown, never a session token.
            overdue.append(user)
    # End each overdue guest through the standard no-recovery teardown with the expired reason.
    for user in overdue:
        # Revoke the guest's sessions and identity, closing its analytics summary as expired.
        end_guest_trial(user, "expired")
    # Return the count so the Admin endpoint can report the sweep without identifiers.
    return len(overdue)

# Mark a page departure without ending same-context reloads; the browser nonce still prevents restoration elsewhere. (issue #317)
def mark_guest_departed(session: dict, user: dict) -> None:
    # Ignore non-guest identities so the signal cannot mutate registered sessions.
    if not is_guest(user):
        # Return without changing registered session state.
        return
    # Capture one server timestamp for the departure marker.
    now = utc_now()
    # Define the atomic session-scoped departure mutation.
    def mutate(state: dict) -> dict:
        # Find only the authenticated guest session without exposing its token.
        for stored in state.get("sessions", []):
            # Match the durable random session identifier.
            if stored.get("session_id") == session.get("session_id"):
                # Record the lifecycle signal used by cleanup diagnostics.
                stored["guest_departed_at"] = now
        # Return the mutated sessions document for atomic persistence.
        return state
    # Persist the marker without creating a resumable credential.
    update_json(SESSIONS_PATH, mutate, default_sessions)

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


# Define is_platform_owner so delegation checks never infer owner authority from Admin access. (AUTH-012)
def is_platform_owner(user: dict) -> bool:
    # Require an active canonical identity with the bootstrap-managed owner role.
    return user.get("status") == "active" and PLATFORM_OWNER_ROLE in roles_for_user(user)


# Define is_admin so all Admin APIs share one authorization decision.
def is_admin(user: dict) -> bool:
    # Return whether the active identity has ordinary Admin or inherited platform-owner access.
    return user.get("status") == "active" and bool(ADMIN_ACCESS_ROLES.intersection(roles_for_user(user)))


# Define require_admin so protected Admin endpoints fail closed before dispatch.
def require_admin(user: dict) -> None:
    # Reject authenticated users that do not hold the Admin role.
    if not is_admin(user):
        # Raise the standard forbidden response without exposing Admin data.
        raise ForbiddenError("Admin role is required")


# Define require_platform_owner so Admin delegation stays behind the bootstrap authority. (AUTH-012)
def require_platform_owner(user: dict) -> None:
    # Reject ordinary Admins and all non-owner identities without exposing role state.
    if not is_platform_owner(user):
        # Raise one bounded authorization result for every denied delegation attempt.
        raise ForbiddenError("Platform owner role is required")


# Define update_user_by_id so Admin and current-user flows mutate the canonical identity store.
def update_user_by_id(user_id: str, updater, *, state_validator=None) -> dict:
    # Capture the committed account and privilege decision outside the provider transaction.
    result = {"user": None, "privilege_changed": False}
    # Define the complete identity-document mutation so JSON and MySQL share one atomic boundary.
    def mutate_state(state: dict) -> dict:
        # Reject malformed identity storage rather than replacing recoverable account data.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve the original document for operator recovery.
            raise RuntimeError("Authentication user storage is malformed")
        # Iterate through identities to find the requested durable account under the provider lock.
        for user in state.get("users", []):
            # Skip every unrelated identity.
            if user.get("user_id") != user_id:
                # Continue to the next stored account.
                continue
            # Snapshot only privilege-bearing fields before the caller mutates the account.
            prior_privileges = tuple(user.get(field) for field in PRIVILEGE_FIELDS)
            # Apply the caller-owned mutation to the canonical record under the same transaction.
            updater(user)
            # Run an optional state-wide invariant after mutation but before persistence.
            if state_validator is not None:
                # Let the validator inspect the complete post-mutation identity document.
                state_validator(state, user)
            # Snapshot the same fields after mutation for an exact privilege-change decision.
            current_privileges = tuple(user.get(field) for field in PRIVILEGE_FIELDS)
            # Refresh the account audit timestamp after the mutation.
            user["updated_at"] = utc_now()
            # Publish a detached committed result for the caller after persistence succeeds.
            result["user"] = dict(user)
            # Record whether every predecessor session must be invalidated after commit.
            result["privilege_changed"] = current_privileges != prior_privileges
            # Stamp the canonical identity schema before persistence.
            state["schema_version"] = SCHEMA_VERSION
            # Return the complete identity document for atomic provider persistence.
            return state
        # Raise a validation error when no canonical identity matches.
        raise ValidationError("user was not found")
    # Persist the complete read-validate-write sequence through the JSON/MySQL transaction.
    update_json(USERS_PATH, mutate_state, default_users)
    # Invalidate every predecessor after a committed role, status, or credential-authority change.
    if result["privilege_changed"]:
        # Force the affected identity to authenticate into a freshly rotated session.
        revoke_sessions_for_user(user_id)
    # Return the committed detached identity.
    return result["user"]


# Define set_user_password so Admin and self-service recovery can share canonical credential rotation.
def set_user_password(user_id: str, password: str, *, require_reset: bool = True) -> dict:
    # Reject empty replacement passwords before hashing.
    if not password:
        # Raise an explicit validation error for the Admin form.
        raise ValidationError("password is required")
    # Update the canonical password verifier and caller-selected follow-up policy together.
    return update_user_by_id(user_id, lambda user: user.update({"password_hash": hash_password(password), "password_reset_required": bool(require_reset), "password_version": int(user.get("password_version", 0)) + 1, "password_reset_at": utc_now()}))


# Define accept_terms so the browser and Admin share canonical terms metadata.
def accept_terms(user_id: str, terms_version: str | None = None, accepted: bool = True, source: str = "current_user") -> dict:
    # Store acceptance or revocation on the canonical identity record.
    return update_user_by_id(user_id, lambda user: user.update({"terms_required": not accepted, "terms_accepted_at": utc_now() if accepted else None, "terms_accepted_version": terms_version if accepted else None, "terms_acceptance_source": source if accepted else None}))

# Define the bootstrap_admin_from_env function used by this module.
def bootstrap_admin_from_env() -> dict:
    # Set existing to the value needed for the next operation.
    existing = find_user_by_email(AUTH_BOOTSTRAP_ADMIN_EMAIL)
    # Branch when the configured bootstrap identity already exists.
    if existing:
        # Return the existing identity unchanged once the owner role migration has already landed.
        if PLATFORM_OWNER_ROLE in roles_for_user(existing):
            # Avoid needless privilege writes and session revocation on every process start.
            return existing
        # Promote only the configured bootstrap identity while preserving its compatible Admin role.
        return update_user_by_id(existing["user_id"], lambda user: user.update({"role": "admin", "roles": ["admin", PLATFORM_OWNER_ROLE]}))
    # Create the compatible Admin identity before attaching bootstrap-only owner authority.
    created = create_user(AUTH_BOOTSTRAP_ADMIN_EMAIL, AUTH_BOOTSTRAP_ADMIN_PASSWORD, AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME, "admin", "human", False)
    # Add owner authority atomically so ordinary account creation can never request it.
    return update_user_by_id(created["user_id"], lambda user: user.update({"role": "admin", "roles": ["admin", PLATFORM_OWNER_ROLE]}))

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
def create_session(user: dict, client: str = "", auth_method: str = "local") -> dict:
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Accept only password or reviewed provider methods in durable session metadata.
    if auth_method not in {"local", "google", "facebook"}:
        # Reject unreviewed authentication authorities before issuing bearer material.
        raise ValidationError("Session authentication method is invalid")
    # Build the durable session record with independent bearer and CSRF material.
    session = {"session_id": new_id("session"), "user_id": user["user_id"], "token": secrets.token_urlsafe(32), "csrf_token": new_csrf_token(), "status": "active", "created_at": now, "updated_at": now, "expires_at": session_expiry(), "client": client, "auth_method": auth_method}
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
    # Copy public session metadata without exposing the bearer token, client, or guest proof digest.
    result = {key: value for key, value in session.items() if key not in {"token", "client", "guest_browser_nonce_hash", "guest_departed_at", "guest_action_count"}}
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


# Read a valid root-managed monitor token verifier without caching deployment secrets.
def monitor_token_digest(environ=None) -> str:
    # Use the live process environment unless a focused test supplies a synthetic mapping.
    current_environment = os.environ if environ is None else environ
    # Normalize only whitespace and case around the public digest representation.
    digest = str(current_environment.get(EDGE_MONITOR_TOKEN_SHA256_ENV, "")).strip().lower()
    # Return no verifier unless the operator supplied one exact SHA-256 digest.
    if not EDGE_MONITOR_TOKEN_HASH_PATTERN.fullmatch(digest):
        # Preserve disabled behavior for local runs and malformed production configuration.
        return ""
    # Return the validated digest without exposing the underlying monitor token.
    return digest


# Authenticate one root-managed monitor token only for read-only Operations probes.
def authenticate_monitor_headers(headers, path: str, environ=None) -> tuple[dict, dict] | None:
    # Refuse every route outside the deployment-observation allowlist before reading credentials.
    if path not in MONITOR_AUTH_PATHS:
        # Return no monitor identity so ordinary session authentication remains authoritative.
        return None
    # Read the hash-only verifier from the supplied environment boundary.
    expected_digest = monitor_token_digest(environ)
    # Keep the monitor credential disabled unless deployment configuration explicitly supplies a verifier.
    if not expected_digest:
        # Return no monitor identity so missing configuration cannot grant access.
        return None
    # Extract the same bearer shape used by normal API clients without accepting cookies.
    token = extract_bearer_token(headers)
    # Reject missing, multiline, or unbounded bearer material before hashing it.
    if not token or "\r" in token or "\n" in token or len(token) > 4096:
        # Return no monitor identity so invalid material follows the normal unauthenticated path.
        return None
    # Hash the supplied token so comparison never stores or echoes plaintext bearer material.
    supplied_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    # Compare the two fixed-length digests with constant-time semantics.
    if not hmac.compare_digest(supplied_digest, expected_digest):
        # Return no monitor identity so unrelated bearer sessions are resolved normally.
        return None
    # Capture one timestamp for the ephemeral request-local monitor session.
    now = utc_now()
    # Build a non-persistent session facade that carries no reusable token, CSRF proof, or client data.
    session = {"session_id": "edge-monitor", "user_id": "edge-monitor", "status": "active", "created_at": now, "updated_at": now, "expires_at": now, "auth_method": "edge_monitor"}
    # Build the smallest Admin-compatible identity for the Operations authorization gate.
    user = {"user_id": "edge-monitor", "email": None, "username": "edge-monitor", "display_name": "Edge Monitor", "role": "admin", "roles": ["admin"], "status": "active", "player_id": "edge-monitor", "identity_provider": "edge_monitor", "monitor": True}
    # Return the ephemeral principal for this one read-only request only.
    return session, user


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


# Resolve only an active session's CSRF value for a static shell response without authenticating it. (AUTH-007, OAUTH-008)
def csrf_token_for_session_cookie(headers) -> str:
    # Read the opaque host-only session cookie without consulting bearer headers.
    token = extract_cookie_token(headers)
    # Return no authenticated proof when the browser has no session cookie.
    if not token:
        # Preserve anonymous shell bootstrap behavior.
        return ""
    # Read a pruned in-memory session view without refreshing activity or persisting state.
    state = prune_sessions(load_sessions())
    # Inspect only surviving active sessions for the exact opaque cookie.
    for session in state.get("sessions", []):
        # Skip every unrelated or non-active record without exposing identifiers.
        if session.get("status") != "active" or not hmac.compare_digest(str(session.get("token") or ""), token):
            # Continue to the next bounded session row.
            continue
        # Read the browser-readable session CSRF value without authenticating a guest browser proof.
        csrf_token = session.get("csrf_token")
        # Accept only the bounded generated proof shape used by application sessions.
        if isinstance(csrf_token, str) and 32 <= len(csrf_token) <= 128:
            # Return the exact session proof for the host-only double-submit cookie.
            return csrf_token
        # Reject a malformed matching session without substituting a durable value.
        return ""
    # Return no proof when the cookie is expired, revoked, or unknown.
    return ""

# Define the authenticate_token function used by this module.
def authenticate_token(token: str, guest_browser_nonce: str = "") -> tuple[dict, dict]:
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
            # Recheck external-provider rollback, link ownership, and active configuration on every request.
            if session.get("auth_method", "local") in {"google", "facebook"}:
                # Import lazily so the core auth module does not create an OAuth import cycle.
                from casino.core.oauth.service import provider_session_is_authorized
                # Revoke effective access immediately when a flag, release gate, or durable link disappears.
                if not provider_session_is_authorized(session, user):
                    # Reject the provider session without affecting local-password sessions.
                    raise UnauthorizedError("External provider session is no longer authorized")
            # Refresh the guest's de-identified activity marker so the Admin active-now window stays truthful. (issue #317)
            if is_guest(user):
                # End an expired absolute-lifetime session before any protected route can resume it.
                if user.get("guest_expires_at") and parse_time(user["guest_expires_at"]) <= utc_datetime():
                    # Revoke the complete disposable principal through the canonical teardown.
                    end_guest_trial(user, "expired")
                    # Reject the expired credential with the standard unauthenticated result.
                    raise UnauthorizedError("Guest trial expired")
                # End a session that exceeded the configured server-observed inactivity window.
                if (utc_datetime() - parse_time(session.get("updated_at") or session.get("created_at"))).total_seconds() >= GUEST_INACTIVITY_SECONDS:
                    # Revoke the complete disposable principal through the canonical teardown.
                    end_guest_trial(user, "inactive")
                    # Reject the inactive credential without exposing timestamps.
                    raise UnauthorizedError("Guest trial expired")
                # Hash the browser-context proof before constant-time comparison with storage.
                supplied_nonce_hash = hashlib.sha256(str(guest_browser_nonce or "").encode("utf-8")).hexdigest()
                # End the guest when a cookie is replayed outside its originating browser-session context.
                if not guest_browser_nonce or not hmac.compare_digest(str(session.get("guest_browser_nonce_hash") or ""), supplied_nonce_hash):
                    # Irreversibly close the replayed or contextless trial.
                    end_guest_trial(user, "browser_closed")
                    # Reject without revealing which component of the browser binding failed.
                    raise UnauthorizedError("Guest trial is not resumable")
                # Capture one timestamp used for both session activity and departure-marker clearing.
                activity_now = utc_now()
                # Define the atomic authenticated-activity mutation.
                def touch_guest_session(stored_state: dict) -> dict:
                    # Find only the authenticated session by its opaque identifier.
                    for stored in stored_state.get("sessions", []):
                        # Match the session without comparing or copying its bearer credential.
                        if stored.get("session_id") == session.get("session_id"):
                            # Refresh the server-observed inactivity marker.
                            stored["updated_at"] = activity_now
                            # Clear a page-departure marker when the same browser context resumes after reload.
                            stored.pop("guest_departed_at", None)
                    # Return the mutated sessions document for atomic persistence.
                    return stored_state
                # Persist activity atomically so concurrent requests cannot restore stale session state.
                update_json(SESSIONS_PATH, touch_guest_session, default_sessions)
                # Reflect the touch in the request-local session used by downstream code.
                session["updated_at"] = activity_now
                # Touch only the one-way analytics id; the summary never stores user, player, or session identifiers.
                guest_analytics.record_event(user.get("guest_analytics_id"))
            # Return the computed value to the caller.
            return session, user
    # Raise an error so invalid input or state is reported explicitly.
    raise UnauthorizedError("Session is invalid or expired")

# Define the authenticate_headers function used by this module.
def authenticate_headers(headers) -> tuple[dict, dict]:
    # Set token to the value needed for the next operation.
    token = extract_bearer_token(headers) or extract_cookie_token(headers)
    # Return the computed value to the caller.
    # Read the browser-context proof case-insensitively without retaining any other request header.
    guest_browser_nonce = next((str(value) for name, value in headers.items() if str(name).lower() == "x-guest-browser-nonce"), "")
    # Authenticate the credential and its optional guest-only browser binding together.
    return authenticate_token(token, guest_browser_nonce)

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

# Require a retained full account before exposing or mutating its session inventory. (SESSION-008)
def _require_session_control_target(user_id: str) -> dict:
    # Reject missing or non-string identifiers through one enumeration-safe response.
    if not isinstance(user_id, str) or not user_id.strip():
        # Avoid distinguishing absent, malformed, and guest identities to callers.
        raise ValidationError("Persistent account is required")
    # Resolve the canonical identity from the retained user store.
    user = find_user_by_id(user_id)
    # Reject unknown and disposable guest principals through the same bounded response.
    if not user or is_guest(user):
        # Keep the server-side boundary unavailable to temporary marketing identities.
        raise ValidationError("Persistent account is required")
    # Return the retained canonical account for future policy checks.
    return user

# Reject malformed session documents without rewriting recoverable operator evidence. (SESSION-008)
def _validated_session_rows(state: dict) -> list[dict]:
    # Require the canonical document and collection shapes before inspecting any row.
    if not isinstance(state, dict) or not isinstance(state.get("sessions"), list):
        # Abort before an atomic writer can publish a default or partial repair.
        raise RuntimeError("Session storage requires operator recovery")
    # Validate every row before a caller can mutate any matching session.
    for session in state["sessions"]:
        # Require the complete identity and lifecycle keys used by inventory and revocation.
        if not isinstance(session, dict) or not isinstance(session.get("session_id"), str) or not session.get("session_id") or not isinstance(session.get("user_id"), str) or not session.get("user_id") or not isinstance(session.get("status"), str) or not session.get("status"):
            # Preserve the complete malformed document for operator recovery.
            raise RuntimeError("Session storage requires operator recovery")
    # Return the validated rows without copying secret-bearing records.
    return state["sessions"]

# Derive a stable non-reversible lookup alias without exposing session or bearer material. (SESSION-008)
def admin_session_alias(session_id: str) -> str:
    # Reject empty identifiers so no shared alias can be created accidentally.
    if not isinstance(session_id, str) or not session_id:
        # Keep malformed persisted identifiers outside the Admin lookup namespace.
        raise RuntimeError("Session storage requires operator recovery")
    # Domain-separate the digest from any other identifier hash used by the application.
    material = f"admin-session\0{session_id}".encode("utf-8")
    # Return a compact stable alias suitable for exact Admin follow-up actions.
    return hashlib.sha256(material).hexdigest()[:16]

# Classify the stored client hint into a fixed privacy-safe family. (SESSION-008)
def _admin_session_client_family(client: object) -> str:
    # Normalize only in memory so the raw client value is never returned or persisted elsewhere.
    value = str(client or "").lower()
    # Detect tablet hints before generic mobile tokens such as Android.
    if any(token in value for token in ("ipad", "tablet")):
        # Publish the fixed tablet family.
        return "tablet"
    # Detect common handheld browser hints without exposing the exact device or agent.
    if any(token in value for token in ("mobile", "android", "iphone")):
        # Publish the fixed mobile family.
        return "mobile"
    # Detect command-line and API clients as a single coarse family.
    if any(token in value for token in ("curl", "python", "httpclient", "http-client", "api-client")):
        # Publish the fixed API family.
        return "api"
    # Detect common desktop browser and operating-system hints.
    if any(token in value for token in ("windows", "macintosh", "x11", "mozilla", "chrome", "safari", "firefox", "edge")):
        # Publish the fixed desktop family.
        return "desktop"
    # Keep IP addresses, novel user agents, and absent hints in one non-identifying bucket.
    return "unknown"

# Project one secret-bearing session row into the bounded Admin inventory shape. (SESSION-008)
def _admin_session_summary(session: dict) -> dict:
    # Normalize missing legacy authentication metadata to the historical local-login behavior.
    auth_method = session.get("auth_method") or "local"
    # Replace unreviewed stored values with a fixed non-identifying class.
    safe_auth_method = auth_method if auth_method in ADMIN_SESSION_AUTH_METHODS else "unknown"
    # Replace unreviewed stored lifecycle values with a fixed non-identifying class.
    safe_status = session["status"] if session["status"] in ADMIN_SESSION_STATUSES else "unknown"
    # Return only approved timestamps, fixed classes, and the one-way lookup alias.
    return {
        # Publish the stable alias used by targeted revocation.
        "session_alias": admin_session_alias(session["session_id"]),
        # Publish the durable creation timestamp without changing storage.
        "created_at": session.get("created_at"),
        # Prefer the latest activity timestamp while supporting legacy session rows.
        "last_activity_at": session.get("updated_at") or session.get("created_at"),
        # Publish the existing bounded expiry timestamp.
        "expires_at": session.get("expires_at"),
        # Publish only a fixed reviewed lifecycle class.
        "status": safe_status,
        # Publish only a fixed reviewed authentication-method class.
        "auth_method": safe_auth_method,
        # Publish only the fixed client family derived from the raw stored hint.
        "client_family": _admin_session_client_family(session.get("client")),
    }

# List one persistent account's bounded privacy-safe session inventory. (SESSION-008)
def list_admin_sessions_for_user(user_id: str, limit: int = MAX_ADMIN_SESSION_RESULTS) -> list[dict]:
    # Validate the target before touching secret-bearing session storage.
    _require_session_control_target(user_id)
    # Reject booleans and out-of-range values because bool is an int subclass in Python.
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > MAX_ADMIN_SESSION_RESULTS:
        # Keep every caller on the documented bounded inventory contract.
        raise ValidationError("Session result limit is invalid")
    # Read through the strict provider boundary so corrupt JSON cannot appear as an empty inventory.
    state = read_json_strict(SESSIONS_PATH, default_sessions, "Session storage requires operator recovery")
    # Validate the complete document before deriving any partial result.
    rows = _validated_session_rows(state)
    # Select only the exact target account without exposing unrelated identities.
    selected = [session for session in rows if session["user_id"] == user_id]
    # Sort newest activity first using compatible ISO timestamps and a stable identifier tie-break.
    selected.sort(key=lambda session: (str(session.get("updated_at") or session.get("created_at") or ""), str(session["session_id"])), reverse=True)
    # Return only the bounded privacy-safe projections.
    return [_admin_session_summary(session) for session in selected[:limit]]

# Revoke one active session by its one-way account-scoped Admin alias. (SESSION-008)
def revoke_admin_session_for_user(user_id: str, session_alias: str) -> int:
    # Validate the persistent target before entering the session transaction.
    _require_session_control_target(user_id)
    # Accept only the exact alias shape emitted by the inventory.
    if not isinstance(session_alias, str) or not ADMIN_SESSION_ALIAS_PATTERN.fullmatch(session_alias):
        # Reject malformed lookup material without reading or rewriting session state.
        raise ValidationError("Session alias is invalid")
    # Count only a newly committed active-to-revoked transition.
    changed = {"value": 0}
    # Define the complete targeted mutation under the provider transaction.
    def mutate(state: dict) -> dict:
        # Validate every row before changing any target record.
        rows = _validated_session_rows(state)
        # Resolve all exact account-and-alias matches without leaking whether another account owns the alias.
        matches = [session for session in rows if session["user_id"] == user_id and hmac.compare_digest(admin_session_alias(session["session_id"]), session_alias)]
        # Fail closed on a cryptographic alias collision instead of revoking multiple records.
        if len(matches) > 1:
            # Preserve the complete document for operator investigation.
            raise RuntimeError("Session storage requires operator recovery")
        # Revoke the sole matching active session when one exists.
        if matches and matches[0]["status"] == "active":
            # Make the selected session unusable immediately.
            matches[0]["status"] = "revoked"
            # Record the bounded lifecycle timestamp without changing any secret.
            matches[0]["updated_at"] = utc_now()
            # Record the single committed transition for idempotent callers.
            changed["value"] = 1
        # Preserve the canonical schema marker on a successful transaction.
        state["schema_version"] = SCHEMA_VERSION
        # Return the complete session document for atomic persistence.
        return state
    # Persist through the strict boundary so invalid JSON bytes are never normalized or overwritten.
    update_json_strict(SESSIONS_PATH, mutate, default_sessions, "Session storage requires operator recovery")
    # Return only whether one active session transitioned.
    return changed["value"]

# Revoke every active session for one retained full account through the Admin boundary. (SESSION-008)
def revoke_all_admin_sessions_for_user(user_id: str) -> int:
    # Validate the persistent target before entering the session transaction.
    _require_session_control_target(user_id)
    # Count exact active-to-revoked transitions.
    changed = {"value": 0}
    # Define the complete account-scoped mutation under the provider transaction.
    def mutate(state: dict) -> dict:
        # Validate every row before changing any target record.
        rows = _validated_session_rows(state)
        # Inspect each validated row while holding the atomic provider boundary.
        for session in rows:
            # Revoke only active records owned by the selected retained account.
            if session["user_id"] == user_id and session["status"] == "active":
                # Make the selected session unusable immediately.
                session["status"] = "revoked"
                # Record the bounded lifecycle timestamp without changing any secret.
                session["updated_at"] = utc_now()
                # Count the committed transition for idempotent callers.
                changed["value"] += 1
        # Preserve the canonical schema marker on a successful transaction.
        state["schema_version"] = SCHEMA_VERSION
        # Return the complete session document for atomic persistence.
        return state
    # Persist through the strict boundary so invalid JSON bytes are never normalized or overwritten.
    update_json_strict(SESSIONS_PATH, mutate, default_sessions, "Session storage requires operator recovery")
    # Return only the number of newly revoked active sessions.
    return changed["value"]

# Revoke active sessions created through one external provider while preserving local login.
def revoke_sessions_for_user_method(user_id: str, auth_method: str) -> int:
    # Reject local or unknown methods because unlink may target external providers only.
    if auth_method not in {"google", "facebook"}:
        # Prevent this helper from becoming a broad local-session revocation primitive.
        raise ValidationError("External session authentication method is invalid")
    # Count only exact active provider-session changes.
    changed = {"value": 0}
    # Define the complete provider-scoped session mutation.
    def mutate(state: dict) -> dict:
        # Require recognizable session storage so malformed evidence is never rewritten.
        if not isinstance(state, dict) or not isinstance(state.get("sessions"), list):
            # Abort without replacing the recoverable session document.
            raise RuntimeError("Session storage requires operator recovery")
        # Inspect every stored session under the shared atomic update lock.
        for session in state["sessions"]:
            # Reject malformed rows before any revocation can publish a partial repair.
            if not isinstance(session, dict):
                # Preserve the complete document for operator recovery.
                raise RuntimeError("Session storage requires operator recovery")
            # Revoke only active records for the exact user and provider method.
            if session.get("user_id") == user_id and session.get("auth_method") == auth_method and session.get("status") == "active":
                # Make this provider-authenticated session unusable immediately.
                session["status"] = "revoked"
                # Record a bounded audit timestamp without token or user data.
                session["updated_at"] = utc_now()
                # Count the exact provider-session revocation.
                changed["value"] += 1
        # Preserve the canonical schema marker on commit.
        state["schema_version"] = SCHEMA_VERSION
        # Return the complete mutated session document.
        return state
    # Persist the provider-scoped revocation atomically.
    update_json(SESSIONS_PATH, mutate, default_sessions)
    # Return only the number of revoked sessions.
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

# Build all logout cookie transitions for the production browser boundary.
def clear_cookie_headers(same_site: str = "Lax", secure: bool = False, include_csrf: bool = False) -> list[tuple[str, str]]:
    # Start with the authenticated session credential expiration.
    headers = [clear_cookie_header(same_site, secure)]
    # Rotate the companion double-submit cookie when production set it.
    if include_csrf:
        # Replace the revoked session CSRF value with a fresh anonymous bootstrap token so the still-open sign-in view keeps a valid double-submit pair without a shell reload. (issue #438)
        headers.append(csrf_cookie_header(new_csrf_token(), same_site, secure))
    # Return the complete ordered logout header set.
    return headers

# Define the is_public_api_path function used by this module.
def is_public_api_path(path: str) -> bool:
    # Keep fixed public routes on the explicit allowlist.
    if path in PUBLIC_API_PATHS:
        # Allow login, guest/redeem, provider availability, and liveness without a session.
        return True
    # Allow only exact reviewed Google/Facebook start and callback route shapes.
    return re.fullmatch(r"/api/v2/auth/oauth/(?:google|facebook)/(?:start|callback)", path) is not None
