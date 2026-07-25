# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import JSON support so per-module game descriptors form the canonical runtime catalog.
import json
# Import required dependency so this module can use its public functions or constants.
import hashlib
# Import required dependency so this module can use its public functions or constants.
import ipaddress
# Import required dependency so this module can use its public functions or constants.
import os
# Import the packaged application release from the canonical version-manifest loader.
from casino.module_versions import APP_VERSION

# Set ROOT_DIR to the value needed for the next operation.
ROOT_DIR = Path(__file__).resolve().parents[1]
# Name the external runtime roots required by the supervised production service.
DATA_DIR_ENV = "CASINO_DATA_DIR"
# Keep application logs outside immutable release directories in production.
LOG_DIR_ENV = "CASINO_LOG_DIR"

# Resolve an optional runtime directory without accepting working-directory-relative state.
def _runtime_directory(environment_key: str, default: Path) -> Path:
    # Read only the selected path setting while preserving the existing local default.
    configured = str(os.environ.get(environment_key, "")).strip()
    # Return the source-tree default for developer and test runs that do not override it.
    if not configured:
        # Resolve the default once so path comparisons are deterministic.
        return default.resolve()
    # Expand an operator-owned home alias before absolute-path validation.
    candidate = Path(configured).expanduser()
    # Reject relative state roots because a release-symlink change could redirect persistence.
    if not candidate.is_absolute():
        # Name only the configuration key so diagnostics cannot disclose a private path value.
        raise RuntimeError(f"{environment_key} must be an absolute path")
    # Resolve harmless path aliases while retaining a location that need not exist yet.
    return candidate.resolve()

# Set WEB_DIR to the value needed for the next operation.
WEB_DIR = ROOT_DIR / "web"
# Resolve persistent state from an external environment setting or the local source-tree default.
DATA_DIR = _runtime_directory(DATA_DIR_ENV, ROOT_DIR / "data")
# Set GAME_DATA_DIR to the value needed for the next operation.
GAME_DATA_DIR = DATA_DIR / "games"
# Resolve application logs independently so service policy can cap and rotate them outside releases.
LOG_DIR = _runtime_directory(LOG_DIR_ENV, ROOT_DIR / "logs")
# Set DOCS_DIR to the value needed for the next operation.
DOCS_DIR = ROOT_DIR / "docs"
# Set DEFAULT_HOST to the value needed for the next operation.
DEFAULT_HOST = "127.0.0.1"
# Set DEFAULT_PORT to the value needed for the next operation.
DEFAULT_PORT = 8765
# Set SCHEMA_VERSION to the value needed for the next operation.
SCHEMA_VERSION = "v9_1"
# Set AUTH_SESSION_COOKIE to the value needed for the next operation.
AUTH_SESSION_COOKIE = "casino_session"
# Set AUTH_SESSION_TTL_SECONDS to the value needed for the next operation.
AUTH_SESSION_TTL_SECONDS = int(os.environ.get("CASINO_SESSION_TTL_SECONDS", "86400"))
# Preserve the developer-only one-time-token key so shared deployments can reject the known default. (issue #331)
LOCAL_TOKEN_DIGEST_KEY = "local-development-one-time-token-digest-key"
# Key one-time-token digests so stored verifiers remain non-reversible outside local development.
TOKEN_DIGEST_KEY = os.environ.get("CASINO_TOKEN_DIGEST_KEY", LOCAL_TOKEN_DIGEST_KEY)
# Bound the number of consume attempts per one-time token so a bearer cannot be brute-forced.
TOKEN_MAX_ATTEMPTS = int(os.environ.get("CASINO_TOKEN_MAX_ATTEMPTS", "5"))
# Retain terminal one-time-token records this many seconds past their end state before cleanup prunes them.
TOKEN_RETENTION_SECONDS = int(os.environ.get("CASINO_TOKEN_RETENTION_SECONDS", "1209600"))
# Keep email password recovery disabled until an owner-authorized release enables it. (issue #334)
PASSWORD_RESET_ENABLED = os.environ.get("CASINO_PASSWORD_RESET_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Keep optional passwordless magic-link login disabled until an owner-authorized release enables it. (issue #337)
MAGIC_LINK_ENABLED = os.environ.get("CASINO_MAGIC_LINK_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Preserve the developer-only mail digest key so every public startup rejects the known value. (MAIL-002)
LOCAL_MAIL_DIGEST_KEY = "local-development-transactional-mail-digest-key"
# Key every durable mail identifier independently from one-time-token verifier material.
MAIL_DIGEST_KEY = os.environ.get("CASINO_MAIL_DIGEST_KEY", LOCAL_MAIL_DIGEST_KEY)
# Keep the repository mail feature disabled until an owner-authorized configuration explicitly enables it.
MAIL_ENABLED = os.environ.get("CASINO_MAIL_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Require a second independent release control before any provider adapter can access the network.
MAIL_NETWORK_ENABLED = os.environ.get("CASINO_MAIL_NETWORK_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Select no provider by default so local and test startup remains inert.
MAIL_PROVIDER = os.environ.get("CASINO_MAIL_PROVIDER", "disabled").strip().lower()
# Configure one canonical HTTPS origin used by fixed-purpose links without authorizing exposure.
MAIL_CANONICAL_ORIGIN = os.environ.get("CASINO_MAIL_CANONICAL_ORIGIN", "").strip()
# Configure the provider sender identity without shipping a live default.
MAIL_FROM_ADDRESS = os.environ.get("CASINO_MAIL_FROM_ADDRESS", "").strip()
# Configure the verified sending domain independently from the mailbox identity.
MAIL_SENDING_DOMAIN = os.environ.get("CASINO_MAIL_SENDING_DOMAIN", "").strip().lower()
# Read the optional Postmark credential only for the inert adapter's runtime readiness gate.
MAIL_POSTMARK_SERVER_TOKEN = os.environ.get("CASINO_MAIL_POSTMARK_SERVER_TOKEN", "")
# Bound known-safe provider attempts before a delivery becomes terminally failed.
MAIL_MAX_ATTEMPTS = int(os.environ.get("CASINO_MAIL_MAX_ATTEMPTS", "3"))
# Set the initial retry delay used by bounded exponential backoff.
MAIL_RETRY_BASE_SECONDS = int(os.environ.get("CASINO_MAIL_RETRY_BASE_SECONDS", "60"))
# Bound accepted submissions per keyed recipient during one configured window.
MAIL_RATE_LIMIT = int(os.environ.get("CASINO_MAIL_RATE_LIMIT", "5"))
# Define the per-recipient rate window in seconds.
MAIL_RATE_WINDOW_SECONDS = int(os.environ.get("CASINO_MAIL_RATE_WINDOW_SECONDS", "3600"))
# Retain terminal delivery and suppression metadata for a bounded thirty-day default.
MAIL_RETENTION_SECONDS = int(os.environ.get("CASINO_MAIL_RETENTION_SECONDS", "2592000"))
# Fix absolute policy ceilings so environment configuration may shorten but never extend a purpose lifetime.
TOKEN_PURPOSE_MAX_TTL_SECONDS = {
    "invitation": 604800,  # Cap private invitation validity at seven days.
    "email_verification": 86400,  # Cap verification validity at one day.
    "password_reset": 3600,  # Cap reset validity at one hour.
    "magic_link": 900,  # Cap future magic-link validity at fifteen minutes.
}
# Define the default absolute lifetime of each token purpose; callers may shorten but not remove the allowlist.
TOKEN_PURPOSE_TTL_SECONDS = {
    "invitation": int(os.environ.get("CASINO_TOKEN_TTL_INVITATION", "604800")),  # Allow a bounded seven-day private invitation window.
    "email_verification": int(os.environ.get("CASINO_TOKEN_TTL_EMAIL_VERIFICATION", "86400")),  # Allow a bounded one-day verification window.
    "password_reset": int(os.environ.get("CASINO_TOKEN_TTL_PASSWORD_RESET", "3600")),  # Allow a bounded one-hour reset window.
    "magic_link": int(os.environ.get("CASINO_TOKEN_TTL_MAGIC_LINK", "900")),  # Allow a bounded fifteen-minute future magic-link window.
}
# Enable the account-free disposable guest trial entry within the restricted-preview boundary; configuration-driven per owner-approved #317.
GUEST_TRIALS_ENABLED = os.environ.get("CASINO_GUEST_TRIALS_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
# Grant each new guest trial this many free, non-cashable play tokens.
GUEST_STARTING_BALANCE = float(os.environ.get("CASINO_GUEST_STARTING_BALANCE", "5000"))
# End a guest trial after this many seconds without a server-observed action.
GUEST_INACTIVITY_SECONDS = int(os.environ.get("CASINO_GUEST_INACTIVITY_SECONDS", "1800"))
# Cap the absolute lifetime of any guest trial regardless of activity.
GUEST_LIFETIME_SECONDS = int(os.environ.get("CASINO_GUEST_LIFETIME_SECONDS", "14400"))
# Bound simultaneous disposable principals so anonymous entry cannot exhaust preview storage.
GUEST_MAX_ACTIVE = int(os.environ.get("CASINO_GUEST_MAX_ACTIVE", "100"))
# Bound accepted game mutations in one disposable session so anonymous traffic cannot grow state indefinitely.
GUEST_MAX_ACTIONS = int(os.environ.get("CASINO_GUEST_MAX_ACTIONS", "1000"))
# Bound one guest autoplay registration to a conservative number of rounds.
GUEST_AUTOPLAY_MAX_ROUNDS = int(os.environ.get("CASINO_GUEST_AUTOPLAY_MAX_ROUNDS", "25"))
# Publish the exact private-preview terms revision a guest must explicitly accept before creation.
GUEST_TERMS_VERSION = os.environ.get("CASINO_GUEST_TERMS_VERSION", "private-beta-1").strip()
# Keep Admin invitation issuance disabled until its separately authorized restricted-preview release. (issue #332)
INVITATIONS_ENABLED = os.environ.get("CASINO_INVITATIONS_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Keep public invitation redemption disabled independently from issuance and mail readiness. (issue #332)
ENROLLMENT_ENABLED = os.environ.get("CASINO_ENROLLMENT_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Keep open full-account signup disabled until owner-controlled public enrollment is ready.
SIGNUP_ENABLED = os.environ.get("CASINO_SIGNUP_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Keep passkey registration and authentication disabled until the WebAuthn ceremony is separately certified.
PASSKEYS_ENABLED = os.environ.get("CASINO_PASSKEYS_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Keep automated GitHub publication disabled unless an operator explicitly installs credentials and release gates.
FEEDBACK_GITHUB_PUBLICATION_ENABLED = os.environ.get("CASINO_FEEDBACK_GITHUB_PUBLICATION_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
# Suppress repeated delivery actions inside a bounded operator-visible cooldown.
INVITATION_RESEND_COOLDOWN_SECONDS = int(os.environ.get("CASINO_INVITATION_RESEND_COOLDOWN_SECONDS", "300"))
# Bound invitation mutations per Admin during one fixed policy window.
INVITATION_ADMIN_RATE_LIMIT = int(os.environ.get("CASINO_INVITATION_ADMIN_RATE_LIMIT", "20"))
# Bound invitation deliveries per keyed recipient during one fixed policy window.
INVITATION_RECIPIENT_RATE_LIMIT = int(os.environ.get("CASINO_INVITATION_RECIPIENT_RATE_LIMIT", "5"))
# Define the shared invitation rate window in seconds.
INVITATION_RATE_WINDOW_SECONDS = int(os.environ.get("CASINO_INVITATION_RATE_WINDOW_SECONDS", "86400"))
# Retain terminal invitation and audit metadata for at most one year by default.
INVITATION_RETENTION_SECONDS = int(os.environ.get("CASINO_INVITATION_RETENTION_SECONDS", "31536000"))
# Allow a pre-consumption browser claim to be recovered after a bounded abandoned interval.
INVITATION_CLAIM_TIMEOUT_SECONDS = int(os.environ.get("CASINO_INVITATION_CLAIM_TIMEOUT_SECONDS", "900"))
# Bound accepted authenticated problem reports per opaque reporter during one durable window. (issue #349)
FEEDBACK_RATE_LIMIT = int(os.environ.get("CASINO_FEEDBACK_RATE_LIMIT", "5"))
# Define the cross-process problem-report rate window in seconds.
FEEDBACK_RATE_WINDOW_SECONDS = int(os.environ.get("CASINO_FEEDBACK_RATE_WINDOW_SECONDS", "3600"))
# Retain terminal report content and normalized screenshots for ninety days by default.
FEEDBACK_TERMINAL_RETENTION_SECONDS = int(os.environ.get("CASINO_FEEDBACK_TERMINAL_RETENTION_SECONDS", "7776000"))
# Apply an absolute one-year privacy ceiling even when a report never reaches a terminal state.
FEEDBACK_MAX_RETENTION_SECONDS = int(os.environ.get("CASINO_FEEDBACK_MAX_RETENTION_SECONDS", "31536000"))
# Preserve the developer-only bootstrap email so public startup can reject the local identity default.
LOCAL_BOOTSTRAP_ADMIN_EMAIL = "admin@example.local"
# Preserve only a digest of the developer credential so validation never needs another plaintext copy.
LOCAL_BOOTSTRAP_ADMIN_PASSWORD_SHA256 = "8e70fdbd0400b7a21539fd15fb4ab86c129f7cbd99261dbb0d95c18df8dec177"
# Set AUTH_BOOTSTRAP_ADMIN_EMAIL to the value needed for the next operation.
AUTH_BOOTSTRAP_ADMIN_EMAIL = os.environ.get("CASINO_BOOTSTRAP_ADMIN_EMAIL", LOCAL_BOOTSTRAP_ADMIN_EMAIL)
# Set AUTH_BOOTSTRAP_ADMIN_PASSWORD to the value needed for the next operation.
AUTH_BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("CASINO_BOOTSTRAP_ADMIN_PASSWORD", "admin-password")
# Set AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME to the value needed for the next operation.
AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME = os.environ.get("CASINO_BOOTSTRAP_ADMIN_DISPLAY_NAME", "Bootstrap Admin")
# Name the explicit deployment-mode setting used to harden loopback and public startup consistently.
DEPLOYMENT_MODE_ENV = "CASINO_DEPLOYMENT_MODE"
# List the deployment modes that always require operator-provided bootstrap configuration.
PUBLIC_DEPLOYMENT_MODES = frozenset({"deployment", "production", "public"})
# List the explicit local modes accepted for developer and test startup.
LOCAL_DEPLOYMENT_MODES = frozenset({"development", "local", "test"})
# Name the external keyed-digest setting without ever reporting its value.
TOKEN_DIGEST_ENV_KEY = "CASINO_TOKEN_DIGEST_KEY"
# Name the independent mail digest setting without reporting its value.
MAIL_DIGEST_ENV_KEY = "CASINO_MAIL_DIGEST_KEY"
# Name the required public bootstrap settings without ever including their values in diagnostics.
PUBLIC_BOOTSTRAP_ENV_KEYS = ("CASINO_BOOTSTRAP_ADMIN_EMAIL", "CASINO_BOOTSTRAP_ADMIN_PASSWORD", TOKEN_DIGEST_ENV_KEY, MAIL_DIGEST_ENV_KEY)
# Require both mutable roots to be explicit when the production adapter is selected.
PRODUCTION_RUNTIME_ENV_KEYS = (DATA_DIR_ENV, LOG_DIR_ENV)
# Set DEFAULT_STORAGE_PROVIDER to keep local runs on JSON unless explicitly configured.
DEFAULT_STORAGE_PROVIDER = "json"
# Set DEFAULT_MYSQL_HOST to the developer-friendly MySQL host default.
DEFAULT_MYSQL_HOST = "127.0.0.1"
# Set DEFAULT_MYSQL_PORT to the standard MySQL TCP port.
DEFAULT_MYSQL_PORT = 3306
# Set DEFAULT_MYSQL_USER to the conventional local casino database user.
DEFAULT_MYSQL_USER = "casino"
# Set DEFAULT_MYSQL_DATABASE to the conventional local casino database name.
DEFAULT_MYSQL_DATABASE = "virtual_casino"

# Define the is_loopback_host function used to distinguish local-only server bindings.
def is_loopback_host(host: str) -> bool:
    # Normalize bracketed IPv6 and mixed-case host names before classifying the bind address.
    normalized = str(host or "").strip().lower().strip("[]")
    # Treat the conventional local hostname as loopback without depending on DNS resolution.
    if normalized == "localhost":
        # Return the computed value to the caller.
        return True
    # Start protected logic so invalid or wildcard host values fail closed as non-loopback.
    try:
        # Return the standard library's loopback classification for IPv4 and IPv6 literals.
        return ipaddress.ip_address(normalized).is_loopback
    # Handle hostnames and malformed addresses as externally reachable bindings.
    except ValueError:
        # Return the computed value to the caller.
        return False

# Define the validate_bootstrap_for_startup function used before any runtime state is mutated.
def validate_bootstrap_for_startup(host: str, environ=None) -> None:
    # Use the live process environment in production while allowing isolated mapping-based tests.
    current_environment = os.environ if environ is None else environ
    # Normalize the optional explicit deployment mode for predictable comparisons.
    deployment_mode = str(current_environment.get(DEPLOYMENT_MODE_ENV, "")).strip().lower()
    # Reject misspelled or unsupported explicit modes instead of silently weakening the guard.
    if deployment_mode and deployment_mode not in PUBLIC_DEPLOYMENT_MODES | LOCAL_DEPLOYMENT_MODES:
        # Raise an error that identifies only the configuration key, never any supplied value.
        raise RuntimeError(f"{DEPLOYMENT_MODE_ENV} must select a supported local or public deployment mode")
    # Require hardened bootstrap settings for any non-loopback bind or explicit public deployment mode.
    public_startup = not is_loopback_host(host) or deployment_mode in PUBLIC_DEPLOYMENT_MODES
    # Preserve convenient local bootstrap behavior when neither public signal is present.
    if not public_startup:
        # Return after confirming that local defaults are safe for this loopback-only process.
        return
    # Identify absent or blank required settings without collecting their sensitive values.
    missing_keys = [key for key in PUBLIC_BOOTSTRAP_ENV_KEYS if not str(current_environment.get(key, "")).strip()]
    # Fail before storage setup when an operator has not supplied every required public setting.
    if missing_keys:
        # Raise an error that names only the missing environment variables.
        raise RuntimeError("Public deployment requires explicit bootstrap configuration: " + ", ".join(missing_keys))
    # Read the explicit email only for comparison against the developer-only identity default.
    configured_email = str(current_environment[PUBLIC_BOOTSTRAP_ENV_KEYS[0]]).strip()
    # Read the explicit password only for comparison against the developer-only credential default.
    configured_password = str(current_environment[PUBLIC_BOOTSTRAP_ENV_KEYS[1]])
    # Hash the supplied password so comparison does not require another plaintext default in source.
    configured_password_sha256 = hashlib.sha256(configured_password.encode("utf-8")).hexdigest()
    # Read the external digest key only for value-free strength and known-default validation.
    configured_token_digest_key = str(current_environment[TOKEN_DIGEST_ENV_KEY])
    # Read the independent mail digest key only for value-free strength and known-default validation.
    configured_mail_digest_key = str(current_environment[MAIL_DIGEST_ENV_KEY])
    # Reject either known local default so copying developer configuration cannot expose a public Admin account.
    if configured_email.lower() == LOCAL_BOOTSTRAP_ADMIN_EMAIL.lower() or configured_password_sha256 == LOCAL_BOOTSTRAP_ADMIN_PASSWORD_SHA256:
        # Raise a value-free diagnostic that tells the operator which settings need unique deployment values.
        raise RuntimeError("Public deployment rejects local bootstrap defaults; configure unique bootstrap Admin settings")
    # Reject the known local token key and keys shorter than the 256-bit policy floor.
    if configured_token_digest_key == LOCAL_TOKEN_DIGEST_KEY or len(configured_token_digest_key.encode("utf-8")) < 32:
        # Raise a value-free diagnostic that never exposes digest-key material.
        raise RuntimeError("Public deployment requires a unique one-time-token digest key of at least 32 bytes")
    # Reject the known mail key and keys shorter than the 256-bit policy floor.
    if configured_mail_digest_key == LOCAL_MAIL_DIGEST_KEY or len(configured_mail_digest_key.encode("utf-8")) < 32:
        # Raise a value-free diagnostic that never exposes mail digest-key material.
        raise RuntimeError("Public deployment requires a unique transactional-mail digest key of at least 32 bytes")

# Validate immutable-release runtime boundaries before the WSGI application initializes state.
def validate_production_runtime(environ=None) -> None:
    # Use the live service environment unless an isolated test supplies a value-only mapping.
    current_environment = os.environ if environ is None else environ
    # Require the dedicated adapter to run only under the explicit production deployment mode.
    if str(current_environment.get(DEPLOYMENT_MODE_ENV, "")).strip().lower() != "production":
        # Name only the expected mode key without echoing any supplied configuration value.
        raise RuntimeError(f"{DEPLOYMENT_MODE_ENV} must be production for the production adapter")
    # Collect missing external roots without reading or reporting their values.
    missing_keys = [key for key in PRODUCTION_RUNTIME_ENV_KEYS if not str(current_environment.get(key, "")).strip()]
    # Fail before directory creation when mutable state would otherwise enter an immutable release.
    if missing_keys:
        # Report only public environment variable names for safe service diagnostics.
        raise RuntimeError("Production adapter requires external runtime directories: " + ", ".join(missing_keys))
    # Validate each configured path independently of module-imported process globals.
    for key in PRODUCTION_RUNTIME_ENV_KEYS:
        # Expand an operator home alias before checking absolute-path semantics.
        candidate = Path(str(current_environment[key]).strip()).expanduser()
        # Reject release-relative state and logs before any application initialization.
        if not candidate.is_absolute():
            # Keep the failure value-free so private host paths never enter logs.
            raise RuntimeError(f"{key} must be an absolute path")
        # Resolve the candidate for a stable containment check against the immutable source root.
        resolved = candidate.resolve()
        # Start protected containment handling because external roots normally are unrelated paths.
        try:
            # Detect any mutable root located inside the extracted immutable release directory.
            resolved.relative_to(ROOT_DIR.resolve())
        # Treat unrelated external paths as the required production configuration.
        except ValueError:
            # Continue validating the remaining external runtime key.
            continue
        # Reject a mutable path nested under the current release without disclosing that path.
        raise RuntimeError(f"{key} must be outside the immutable application release")

# Set MODULES_DIR to the directory whose independently owned descriptors form the game catalog.
MODULES_DIR = ROOT_DIR / "modules"
# Record the approved expansion target without registering games that have not landed yet.
GAME_CATALOG_TARGET = 20

# Define load_game_catalog so backend, frontend, validators, and tests consume one metadata source.
def load_game_catalog(modules_dir: Path = MODULES_DIR) -> list[dict]:
    # Collect catalog entries from independently owned module descriptors.
    games = []
    # Scan descriptors deterministically so source-control ordering never changes runtime navigation.
    for path in sorted(modules_dir.glob("*.json")):
        # Skip the aggregate version interface because #104 reserves it for canonical revisions.
        if path.name == "module-manifest.json":
            # Continue to the independently owned module descriptors.
            continue
        # Parse one module descriptor before deciding whether it represents a browser game.
        module = json.loads(path.read_text(encoding="utf-8"))
        # Read the optional game entry used only by playable game modules.
        game = module.get("game")
        # Ignore non-game modules without creating a second allowlist.
        if not game:
            # Continue scanning remaining module descriptors.
            continue
        # Copy metadata so runtime callers cannot mutate the parsed module object.
        entry = dict(game)
        # Require catalog identity to match the independently versioned module owner.
        if entry.get("id") != module.get("module"):
            # Fail startup with an actionable descriptor path instead of silently registering drift.
            raise RuntimeError(f"Game catalog id in {path.name} must match module {module.get('module')}")
        # Carry contract ownership into validators without duplicating it inside the game object.
        entry["contracts"] = list(module.get("contracts", []))
        # Carry source paths into validators so future modules are checked through their own descriptor.
        entry["paths"] = list(module.get("paths", []))
        # Add the entry after its module-owned metadata has been normalized.
        games.append(entry)
    # Sort by explicit catalog order and stable game id for predictable navigation and evidence.
    games.sort(key=lambda game: (int(game.get("sort_order", 9999)), game["id"]))
    # Reject duplicate identifiers before dynamic imports or browser routes become ambiguous.
    if len({game["id"] for game in games}) != len(games):
        # Fail closed because duplicate catalog ids could register conflicting API routes.
        raise RuntimeError("Game catalog contains duplicate ids")
    # Return fresh catalog entries to the runtime configuration facade.
    return games

# Load the canonical catalog once so every runtime consumer sees the same ordered entries.
GAMES = load_game_catalog()
