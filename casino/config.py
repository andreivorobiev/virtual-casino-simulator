# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path

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
