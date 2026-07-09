# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
import os

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
# Set APP_VERSION to the value needed for the next operation.
APP_VERSION = "9.1.1"
# Set SCHEMA_VERSION to the value needed for the next operation.
SCHEMA_VERSION = "v9_1"
# Set AUTH_SESSION_COOKIE to the value needed for the next operation.
AUTH_SESSION_COOKIE = "casino_session"
# Set AUTH_SESSION_TTL_SECONDS to the value needed for the next operation.
AUTH_SESSION_TTL_SECONDS = int(os.environ.get("CASINO_SESSION_TTL_SECONDS", "86400"))
# Set AUTH_BOOTSTRAP_ADMIN_EMAIL to the value needed for the next operation.
AUTH_BOOTSTRAP_ADMIN_EMAIL = os.environ.get("CASINO_BOOTSTRAP_ADMIN_EMAIL", "admin@example.local")
# Set AUTH_BOOTSTRAP_ADMIN_PASSWORD to the value needed for the next operation.
AUTH_BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("CASINO_BOOTSTRAP_ADMIN_PASSWORD", "admin-password")
# Set AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME to the value needed for the next operation.
AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME = os.environ.get("CASINO_BOOTSTRAP_ADMIN_DISPLAY_NAME", "Bootstrap Admin")

# Set GAMES to the value needed for the next operation.
GAMES = [
    # Explain this executable/data line so future Codex changes preserve intent.
    {"id": "roulette", "label": "Roulette", "kind": "table"},
    # Explain this executable/data line so future Codex changes preserve intent.
    {"id": "slots", "label": "Slots", "kind": "machine"},
    # Explain this executable/data line so future Codex changes preserve intent.
    {"id": "keno", "label": "Keno", "kind": "draw"},
    # Explain this executable/data line so future Codex changes preserve intent.
    {"id": "bingo", "label": "Bingo", "kind": "draw"},
    # Explain this executable/data line so future Codex changes preserve intent.
    {"id": "blackjack", "label": "Blackjack", "kind": "table"},
    # Explain this executable/data line so future Codex changes preserve intent.
    {"id": "baccarat", "label": "Baccarat", "kind": "table"},
]
