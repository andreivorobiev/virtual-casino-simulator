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
# Set WEB_DIR to the value needed for the next operation.
WEB_DIR = ROOT_DIR / "web"
# Set DATA_DIR to the value needed for the next operation.
DATA_DIR = ROOT_DIR / "data"
# Set GAME_DATA_DIR to the value needed for the next operation.
GAME_DATA_DIR = DATA_DIR / "games"
# Set LOG_DIR to the value needed for the next operation.
LOG_DIR = ROOT_DIR / "logs"
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
# Name the required public bootstrap settings without ever including their values in diagnostics.
PUBLIC_BOOTSTRAP_ENV_KEYS = ("CASINO_BOOTSTRAP_ADMIN_EMAIL", "CASINO_BOOTSTRAP_ADMIN_PASSWORD")
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
    # Reject either known local default so copying developer configuration cannot expose a public Admin account.
    if configured_email.lower() == LOCAL_BOOTSTRAP_ADMIN_EMAIL.lower() or configured_password_sha256 == LOCAL_BOOTSTRAP_ADMIN_PASSWORD_SHA256:
        # Raise a value-free diagnostic that tells the operator which settings need unique deployment values.
        raise RuntimeError("Public deployment rejects local bootstrap defaults; configure unique bootstrap Admin settings")

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
