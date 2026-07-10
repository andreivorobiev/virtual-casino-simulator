# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import shutil
# Import required dependency so this module can use its public functions or constants.
import threading
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from typing import Any, Callable
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, GAME_DATA_DIR, LOG_DIR, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so JSON-shaped state can use the configured storage provider.
from casino.core.storage import get_storage_provider, storage_provider_name

# Set _LOCK to the value needed for the next operation.
_LOCK = threading.RLock()

# Convert a data-directory path into the stable provider document key used by MySQL.
def _provider_document_key(path: Path) -> str | None:
    # Start protected path handling so files outside data/ retain normal filesystem behavior.
    try:
        # Return a portable relative key so copied deployments share the same document names.
        return path.resolve().relative_to(DATA_DIR.resolve()).as_posix()
    # Keep logs and other non-data files on disk when they are outside the provider root.
    except ValueError:
        # Return no key so the caller continues through the JSON file fallback.
        return None

# Define the ensure_dirs function used by this module.
def ensure_dirs() -> None:
    # Set DATA_DIR.mkdir(parents to the value needed for the next operation.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Set GAME_DATA_DIR.mkdir(parents to the value needed for the next operation.
    GAME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Set LOG_DIR.mkdir(parents to the value needed for the next operation.
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    # Set (LOG_DIR / "test-runs").mkdir(parents to the value needed for the next operation.
    (LOG_DIR / "test-runs").mkdir(parents=True, exist_ok=True)
    # Set (DATA_DIR / "settings").mkdir(parents to the value needed for the next operation.
    (DATA_DIR / "settings").mkdir(parents=True, exist_ok=True)

# Define the read_json function used by this module.
def read_json(path: Path, default: Any) -> Any:
    # Resolve the provider document key for persistent files under data/.
    document_key = _provider_document_key(path)
    # Route every JSON-shaped data document through MySQL when it is explicitly selected.
    if document_key is not None and storage_provider_name() == "mysql":
        # Preserve lazy default-factory behavior through the provider abstraction.
        return get_storage_provider().read_document(document_key, default)
    # Execute this statement as part of the module's documented control flow.
    ensure_dirs()
    # Manage this resource with automatic setup and cleanup.
    with _LOCK:
        # Branch when the following condition is true.
        if not path.exists():
            # Return the computed value to the caller.
            return default() if callable(default) else default
        # Start protected logic so failures can be handled safely.
        try:
            # Return the computed value to the caller.
            return json.loads(path.read_text(encoding="utf-8"))
        # Handle the expected failure path for the protected logic.
        except json.JSONDecodeError:
            # Set backup to the value needed for the next operation.
            backup = path.with_suffix(path.suffix + f".corrupt-{int(__import__('time').time())}")
            # Use this standard-library helper to perform the requested operation.
            shutil.copy2(path, backup)
            # Return the computed value to the caller.
            return default() if callable(default) else default

# Define the write_json function used by this module.
def write_json(path: Path, data: Any) -> None:
    # Resolve the provider document key for persistent files under data/.
    document_key = _provider_document_key(path)
    # Route every JSON-shaped data document through MySQL when it is explicitly selected.
    if document_key is not None and storage_provider_name() == "mysql":
        # Persist auth, sessions, game state, bots, autoplay, and settings as provider documents.
        get_storage_provider().write_document(document_key, data)
        # Stop before creating a hybrid JSON copy on disk.
        return
    # Execute this statement as part of the module's documented control flow.
    ensure_dirs()
    # Manage this resource with automatic setup and cleanup.
    with _LOCK:
        # Set path.parent.mkdir(parents to the value needed for the next operation.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Set tmp to the value needed for the next operation.
        tmp = path.with_suffix(path.suffix + ".tmp")
        # Set tmp.write_text(json.dumps(data, indent to the value needed for the next operation.
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        # Execute this statement as part of the module's documented control flow.
        tmp.replace(path)

# Define the append_jsonl function used by this module.
def append_jsonl(path: Path, event: dict) -> None:
    # Execute this statement as part of the module's documented control flow.
    ensure_dirs()
    # Manage this resource with automatic setup and cleanup.
    with _LOCK:
        # Set path.parent.mkdir(parents to the value needed for the next operation.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Manage this resource with automatic setup and cleanup.
        with path.open("a", encoding="utf-8") as f:
            # Set f.write(json.dumps(event, sort_keys to the value needed for the next operation.
            f.write(json.dumps(event, sort_keys=True) + "\n")

# Define the game_state_path function used by this module.
def game_state_path(game_id: str) -> Path:
    # Return the computed value to the caller.
    return GAME_DATA_DIR / f"{game_id}.json"

# Define the player_game_state_path function used by this module.
def player_game_state_path(game_id: str, player_id: str) -> Path:
    # Set safe_player_id to the value needed for filesystem-safe player state.
    safe_player_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(player_id or "human"))
    # Return the computed value to the caller.
    return GAME_DATA_DIR / game_id / f"{safe_player_id}.json"

# Define the load_game_state function used by this module.
def load_game_state(game_id: str, default_factory: Callable[[], dict]) -> dict:
    # Set state to the value needed for the next operation.
    state = read_json(game_state_path(game_id), default_factory)
    # Branch when the following condition is true.
    if not isinstance(state, dict):
        # Set state to the value needed for the next operation.
        state = default_factory()
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("schema_version", SCHEMA_VERSION)
    # Return the computed value to the caller.
    return state

# Define the load_player_game_state function used by this module.
def load_player_game_state(game_id: str, player_id: str, default_factory: Callable[[], dict]) -> dict:
    # Set path to the player-scoped file so private sessions do not share in-progress state.
    path = player_game_state_path(game_id, player_id)
    # Branch when a legacy human state file should be honored for v1 compatibility.
    if str(player_id or "human") == "human" and not path.exists() and game_state_path(game_id).exists():
        # Return the legacy state so existing local data remains readable.
        return load_game_state(game_id, default_factory)
    # Set state to the value needed for the next operation.
    state = read_json(path, default_factory)
    # Branch when the stored payload is malformed.
    if not isinstance(state, dict):
        # Set state to a fresh default payload.
        state = default_factory()
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("schema_version", SCHEMA_VERSION)
    # Return the computed value to the caller.
    return state

# Define the save_game_state function used by this module.
def save_game_state(game_id: str, state: dict) -> None:
    # Set state to the value needed for the next operation.
    state = dict(state)
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Set state["updated_at"] to the value needed for the next operation.
    state["updated_at"] = utc_now()
    # Execute this statement as part of the module's documented control flow.
    write_json(game_state_path(game_id), state)

# Define the save_player_game_state function used by this module.
def save_player_game_state(game_id: str, player_id: str, state: dict) -> None:
    # Set state to a copy so callers keep their in-memory object identity.
    state = dict(state)
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Set state["updated_at"] to the value needed for the next operation.
    state["updated_at"] = utc_now()
    # Execute this statement as part of the module's documented control flow.
    write_json(player_game_state_path(game_id, player_id), state)

# Define the migrate_from_v7_if_needed function used by this module.
def migrate_from_v7_if_needed() -> None:
    """Best-effort migration of older monolithic files into v8 data layout.

    # Execute this statement as part of the module's documented control flow.
    We intentionally do not migrate half-finished hands/draws because v7 global state could be inconsistent.
    """
    # Execute this statement as part of the module's documented control flow.
    ensure_dirs()
    # Branch when configured storage is not JSON because MySQL starts fresh by design.
    if storage_provider_name() != "json":
        # Return without importing local legacy files into the configured database.
        return
    # Set marker to the value needed for the next operation.
    marker = DATA_DIR / ".v8_migration_complete"
    # Branch when the following condition is true.
    if marker.exists():
        # Return the computed value to the caller.
        return
    # Set root to the value needed for the next operation.
    root = DATA_DIR.parent
    # Set old_state to the value needed for the next operation.
    old_state = root / "casino_state.json"
    # Set old_history to the value needed for the next operation.
    old_history = root / "roulette_history.csv"
    # Set backup_dir to the value needed for the next operation.
    backup_dir = DATA_DIR / "backup_v7"
    # Branch when the following condition is true.
    if old_state.exists() or old_history.exists():
        # Set backup_dir.mkdir(exist_ok to the value needed for the next operation.
        backup_dir.mkdir(exist_ok=True)
    # Branch when the following condition is true.
    if old_state.exists():
        # Use this standard-library helper to perform the requested operation.
        shutil.copy2(old_state, backup_dir / old_state.name)
        # Start protected logic so failures can be handled safely.
        try:
            # Set old to the value needed for the next operation.
            old = json.loads(old_state.read_text(encoding="utf-8"))
            # Set bal to the value needed for the next operation.
            bal = old.get("balance") or old.get("player_balance") or old.get("human_balance")
            # Branch when the following condition is true.
            if isinstance(bal, (int, float)):
                # Set players_path to the value needed for the next operation.
                players_path = DATA_DIR / "players.json"
                # Branch when the following condition is true.
                if not players_path.exists():
                    # Execute this statement as part of the module's documented control flow.
                    write_json(players_path, {"schema_version": SCHEMA_VERSION, "players": [
                        # Explain this executable/data line so future Codex changes preserve intent.
                        {"player_id": "human", "display_name": "You", "type": "human", "balance": round(float(bal), 2), "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                        # Explain this executable/data line so future Codex changes preserve intent.
                        {"player_id": "bot_1", "display_name": "Ava", "type": "bot", "balance": 5000, "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                        # Explain this executable/data line so future Codex changes preserve intent.
                        {"player_id": "bot_2", "display_name": "Mia", "type": "bot", "balance": 5000, "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                        # Explain this executable/data line so future Codex changes preserve intent.
                        {"player_id": "bot_3", "display_name": "Zoe", "type": "bot", "balance": 5000, "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                    ]})
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Intentionally leave this block empty.
            pass
    # Branch when the following condition is true.
    if old_history.exists():
        # Use this standard-library helper to perform the requested operation.
        shutil.copy2(old_history, backup_dir / old_history.name)
        # Set history_path to the value needed for the next operation.
        history_path = DATA_DIR / "history.csv"
        # Branch when the following condition is true.
        if not history_path.exists():
            # Use this standard-library helper to perform the requested operation.
            shutil.copy2(old_history, history_path)
    # Set marker.write_text(utc_now(), encoding to the value needed for the next operation.
    marker.write_text(utc_now(), encoding="utf-8")
