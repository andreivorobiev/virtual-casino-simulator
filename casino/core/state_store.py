# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import shutil
# Import required dependency so this module can use its public functions or constants.
import threading
# Import bounded retry timing for transient Windows atomic-replace sharing violations.
import time
# Import contextmanager so the cross-process file lock reads as a with-statement.
from contextlib import contextmanager
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import POSIX advisory locking when the running platform provides it.
try:
    # Bind the POSIX flock interface for cross-process session-file locking.
    import fcntl
# Fall back cleanly on platforms without POSIX advisory locks.
except ImportError:
    # Signal the absence of POSIX locking so callers degrade to the in-process lock.
    fcntl = None
# Import Windows byte-range locking when the running platform provides it.
try:
    # Bind the Windows locking interface for cross-process session-file locking.
    import msvcrt
# Fall back cleanly on platforms without the Windows locking module.
except ImportError:
    # Signal the absence of Windows locking so callers degrade to the in-process lock.
    msvcrt = None
# Import required dependency so this module can use its public functions or constants.
from typing import Any, Callable
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, GAME_DATA_DIR, LOG_DIR, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now, date_stamp
# Import descriptor-owned read repair so poisoned game settings fail safe before engine consumption.
from casino.core.game_rules import clamp_state_rules
# Import required dependency so JSON-shaped state can use the configured storage provider.
from casino.core.storage import get_storage_provider, storage_provider_name

# Set _LOCK to the value needed for the next operation.
_LOCK = threading.RLock()
# Remember value-free repair notices so a persistently corrupt row cannot flood one process log.
_RULE_REPAIR_LOGGED = set()

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

# Read one JSON document without normalizing syntactically corrupt operator evidence. (SESSION-008)
def read_json_strict(path: Path, default: Any, invalid_message: str) -> Any:
    # Resolve the provider document key for persistent files under data/.
    document_key = _provider_document_key(path)
    # Retain the existing provider read behavior when MySQL owns the canonical document.
    if document_key is not None and storage_provider_name() == "mysql":
        # Preserve lazy defaults while MySQL validates its JSON payload at the provider boundary.
        return get_storage_provider().read_document(document_key, default)
    # Ensure runtime directories exist before reading the default JSON provider.
    ensure_dirs()
    # Serialize this read against in-process JSON writers.
    with _LOCK:
        # Return the caller's default only when no document exists.
        if not path.exists():
            # Preserve lazy default-factory behavior for a genuinely absent document.
            return default() if callable(default) else default
        # Start strict decoding without creating a corrupt-file backup or replacement.
        try:
            # Decode the complete existing document while leaving its bytes untouched.
            return json.loads(path.read_text(encoding="utf-8"))
        # Convert syntax and encoding corruption into the caller's fixed recovery boundary.
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Preserve the original document exactly for operator recovery.
            raise RuntimeError(invalid_message) from None

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
        # Retry only transient Windows sharing violations while preserving atomic replace semantics.
        for attempt in range(5):
            # Start protected replacement of the complete temporary document.
            try:
                # Atomically publish the fully written JSON document.
                tmp.replace(path)
                # Stop after the first successful atomic publication.
                break
            # Handle a brief scanner/indexer handle without widening the persistence operation.
            except PermissionError:
                # Re-raise after the bounded final attempt so durable failures remain visible.
                if attempt == 4:
                    # Preserve the original platform error and traceback.
                    raise
                # Wait a small exponentially bounded interval while still holding the document locks.
                time.sleep(0.01 * (2 ** attempt))

# Hold a best-effort exclusive cross-process lock around a state document's read-modify-write. (SESSION-007, CORE-021)
@contextmanager
def _file_lock(path: Path):
    # Derive a sidecar lock file so the data document itself is never opened for locking.
    lock_path = path.with_suffix(path.suffix + ".lock")
    # Create the parent directory so the sidecar lock file can be opened.
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Open (or create) the sidecar lock file for the duration of the mutation.
    handle = open(lock_path, "a+")
    # Track whether an OS-level lock was actually acquired so release stays symmetric.
    acquired = False
    # Start protected acquisition so a platform quirk never breaks session persistence.
    try:
        # Acquire an exclusive advisory lock on POSIX systems when available.
        if fcntl is not None:
            # Block until the exclusive POSIX lock is held for this process.
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            # Record that the POSIX lock must be released later.
            acquired = True
        # Acquire an exclusive byte-range lock on Windows when available.
        elif msvcrt is not None:
            # Seek to the start so the single-byte range lock is deterministic.
            handle.seek(0)
            # Block-with-retry until the Windows byte-range lock is held.
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            # Record that the Windows lock must be released later.
            acquired = True
    # Degrade to the in-process lock when OS locking is unavailable under contention.
    except OSError:
        # Leave acquired False so the finally block does not attempt an unmatched release.
        acquired = False
    # Start the protected critical section guarded by whatever lock was obtained.
    try:
        # Yield control to the caller while the mutation runs under the lock.
        yield
    # Always release and close so no stale lock or descriptor leaks.
    finally:
        # Release the OS-level lock only when one was actually acquired.
        if acquired:
            # Start protected release so an unlock failure cannot mask the caller's result.
            try:
                # Release the POSIX advisory lock before closing the handle.
                if fcntl is not None:
                    # Unlock the POSIX advisory lock held on this descriptor.
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                # Release the Windows byte-range lock before closing the handle.
                elif msvcrt is not None:
                    # Seek to the same range that was locked before unlocking it.
                    handle.seek(0)
                    # Unlock the Windows byte-range lock held on this descriptor.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            # Ignore unlock failures during teardown so results still propagate.
            except OSError:
                # Intentionally leave this block empty because the handle is closed next.
                pass
        # Always close the sidecar handle even if unlock raised.
        handle.close()

# Apply an atomic read-modify-write so concurrent callers cannot lose each other's updates. (SESSION-007, CORE-021)
def update_json(path: Path, mutator: Callable[[Any], Any], default: Any) -> Any:
    # Resolve the provider document key for persistent files under data/.
    document_key = _provider_document_key(path)
    # Route the atomic mutation through the database provider when MySQL is selected.
    if document_key is not None and storage_provider_name() == "mysql":
        # Delegate the complete read-modify-write to the provider's cross-process transaction boundary.
        return get_storage_provider().update_document(document_key, mutator, default)
    # Ensure runtime directories exist before locking a JSON document.
    ensure_dirs()
    # Serialize the whole read-modify-write with the shared reentrant in-process lock.
    with _LOCK:
        # Create the parent directory so the lock and target files can be written.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Hold a best-effort cross-process file lock for the entire mutation.
        with _file_lock(path):
            # Read the current on-disk state or the lazy default when absent or corrupt.
            current = read_json(path, default)
            # Apply the caller-owned mutation to the current state.
            updated = mutator(current)
            # Write the mutated state through the same atomic temp-file replace.
            write_json(path, updated)
            # Return the persisted state to the caller.
            return updated

# Apply an atomic mutation that refuses to normalize syntactically corrupt JSON. (SESSION-008)
def update_json_strict(path: Path, mutator: Callable[[Any], Any], default: Any, invalid_message: str) -> Any:
    # Resolve the provider document key for persistent files under data/.
    document_key = _provider_document_key(path)
    # Retain the existing row-locking MySQL transaction for provider-backed documents.
    if document_key is not None and storage_provider_name() == "mysql":
        # Delegate validation, mutation, rollback, and commit to the MySQL provider boundary.
        return get_storage_provider().update_document(document_key, mutator, default)
    # Ensure runtime directories exist before locking the default JSON document.
    ensure_dirs()
    # Serialize the complete strict read-modify-write in this process.
    with _LOCK:
        # Create the parent only so the lock sidecar can protect an absent document.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Hold the established cross-process lock for the complete strict mutation.
        with _file_lock(path):
            # Read without the permissive corruption backup/default behavior.
            current = read_json_strict(path, default, invalid_message)
            # Apply the caller-owned mutation only after strict decoding succeeds.
            updated = mutator(current)
            # Publish the complete validated result through the existing atomic replace.
            write_json(path, updated)
            # Return the persisted state to the caller.
            return updated

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

# Clamp one loaded game state and emit at most one value-free repair notice per game/field set. (SEC-014)
def _repair_loaded_game_rules(game_id: str, state: dict) -> dict:
    # Apply the descriptor-owned defaults and domains directly to the caller's loaded state.
    repaired_state, repaired_fields = clamp_state_rules(game_id, state)
    # Skip logging when the state was already canonical or the game owns no settings schema.
    if not repaired_fields:
        # Return the canonical state without creating a log side effect.
        return repaired_state
    # Build a stable process-local key that contains no player or supplied value.
    notice_key = (game_id, repaired_fields)
    # Serialize notice deduplication with the existing state-store reentrant lock.
    with _LOCK:
        # Emit one safe warning only when this game/field repair has not been reported in this process.
        if notice_key not in _RULE_REPAIR_LOGGED:
            # Mark the notice before writing so recursive failures cannot duplicate it.
            _RULE_REPAIR_LOGGED.add(notice_key)
            # Append the value-free repair record without importing logger back into state_store.
            append_jsonl(LOG_DIR / f"app-{date_stamp()}.jsonl", {"ts": utc_now(), "level": "WARN", "event": "game_rules_repaired", "game_id": game_id, "fields": list(repaired_fields)})
    # Return the safe in-memory state; the next normal game save persists the repair atomically.
    return repaired_state

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
    # Repair descriptor-owned settings before the legacy state can reach any engine consumer.
    return _repair_loaded_game_rules(game_id, state)

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
    # Repair descriptor-owned settings before player-scoped state reaches any engine consumer.
    return _repair_loaded_game_rules(game_id, state)

# Apply one player-scoped game-state mutation through the existing atomic JSON/MySQL boundary. (STORAGE-001, STORAGE-002)
def update_player_game_state(
    game_id: str,
    player_id: str,
    mutator: Callable[[dict], dict],
    default_factory: Callable[[], dict],
) -> dict:
    # Resolve the same player-scoped document path used by the existing load and save helpers.
    path = player_game_state_path(game_id, player_id)

    # Build the absent-document seed while preserving the established legacy-human read fallback.
    def initial_state() -> dict:
        # Reuse legacy global human state only while no player-scoped document exists.
        if str(player_id or "human") == "human" and not path.exists() and game_state_path(game_id).exists():
            # Load through the provider-aware legacy helper so JSON and MySQL keep existing behavior.
            return load_game_state(game_id, default_factory)
        # Create a fresh caller-owned default for every genuinely absent or malformed document.
        return default_factory()

    # Normalize, mutate, and stamp one state while the selected provider holds its atomic boundary.
    def apply_mutation(current: Any) -> dict:
        # Match load_player_game_state by replacing a non-object payload with a fresh default.
        normalized = current if isinstance(current, dict) else initial_state()
        # Reject an invalid default before a provider can publish a non-object game-state document.
        if not isinstance(normalized, dict):
            # Raise a stable programming error while the atomic provider still owns rollback.
            raise ValueError("Player game-state defaults must be JSON objects")
        # Give the caller a copy so provider-owned decoded state cannot be mutated after rollback.
        working = dict(normalized)
        # Preserve the load helper's schema default before the caller evaluates the state.
        working.setdefault("schema_version", SCHEMA_VERSION)
        # Apply the caller's complete state transition inside the atomic read-modify-write boundary.
        updated = mutator(working)
        # Require a complete JSON object so partial or invalid results are never persisted.
        if not isinstance(updated, dict):
            # Raise before publication so JSON remains byte-identical and MySQL rolls back.
            raise ValueError("Player game-state mutators must return JSON objects")
        # Copy the result so timestamp and schema normalization do not alter caller-owned state.
        persisted = dict(updated)
        # Stamp the current schema exactly as the existing save helper does.
        persisted["schema_version"] = SCHEMA_VERSION
        # Stamp the successful atomic update exactly as the existing save helper does.
        persisted["updated_at"] = utc_now()
        # Return the complete document for atomic provider publication.
        return persisted

    # Delegate locking, provider selection, transaction commit, and rollback to the existing public seam.
    return update_json(path, apply_mutation, initial_state)

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
