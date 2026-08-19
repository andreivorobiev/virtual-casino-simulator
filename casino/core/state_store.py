# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Provider-neutral state persistence facade plus intentionally local diagnostic logs.
import json
import shutil
import threading
from pathlib import Path
from typing import Any, Callable
from casino.config import DATA_DIR, GAME_DATA_DIR, LOG_DIR, SCHEMA_VERSION
from casino.core.clock import utc_now, date_stamp
# Import descriptor-owned read repair so poisoned game settings fail safe before engine consumption.
from casino.core.game_rules import clamp_state_rules
# Import required dependency so every JSON-shaped state operation uses the configured storage provider.
from casino.core.storage import get_storage_provider

# Serialize only intentionally local JSONL diagnostics and repair-notice deduplication.
_LOG_LOCK = threading.RLock()
# Remember value-free repair notices so a persistently corrupt row cannot flood one process log.
_RULE_REPAIR_LOGGED = set()

# Resolve the active provider and its canonical reference for one state path. (STORAGE-018)
def _provider_document(path: Path):
    # Resolve the configured provider once so one operation cannot cross provider boundaries.
    provider = get_storage_provider()
    # Delegate path containment and key translation to the provider that owns persistence.
    return provider, provider.document_reference(Path(path), DATA_DIR)

# Report provider-owned document existence without consulting a hybrid local file. (STORAGE-018)
def _document_exists(path: Path) -> bool:
    # Resolve the complete provider-owned document reference once for this observation.
    provider, document = _provider_document(path)
    # Delegate visibility and recovery ordering to the selected provider.
    return provider.document_exists(document)

# Define the ensure_dirs function used by this module.
def ensure_dirs() -> None:
    # Let the configured provider create or verify its complete persistence substrate.
    get_storage_provider().ensure_ready()
    # Keep diagnostic logs intentionally local because the provider contract owns JSON documents, not JSONL streams.
    _ensure_log_dirs()

# Create only the intentionally local diagnostic directories without touching provider state.
def _ensure_log_dirs() -> None:
    # Set LOG_DIR.mkdir(parents to the value needed for the next operation.
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    # Set (LOG_DIR / "test-runs").mkdir(parents to the value needed for the next operation.
    (LOG_DIR / "test-runs").mkdir(parents=True, exist_ok=True)

# Define the read_json function used by this module.
def read_json(path: Path, default: Any) -> Any:
    # Resolve the complete provider-owned document reference once for this read.
    provider, document = _provider_document(path)
    # Preserve lazy defaults and provider-owned recovery through the common contract.
    return provider.read_document(document, default)

# Read one JSON document without normalizing syntactically corrupt operator evidence. (SESSION-008)
def read_json_strict(path: Path, default: Any, invalid_message: str) -> Any:
    # Resolve the complete provider-owned document reference once for this strict read.
    provider, document = _provider_document(path)
    # Track a caller-owned default failure so it is never mistaken for provider corruption.
    default_failed = False

    # Preserve lazy default behavior while recording only an exception from caller code.
    def guarded_default() -> Any:
        # Share the failure flag with the outer recovery translator.
        nonlocal default_failed
        # Start caller-owned default construction without evaluating it early.
        try:
            # Return the caller's fresh missing-document value.
            return default() if callable(default) else default
        # Record and preserve any caller exception exactly.
        except Exception:
            # Prevent the outer handler from replacing this caller-owned failure.
            default_failed = True
            # Re-raise the original caller exception and traceback.
            raise
    # Translate only the provider's fixed recovery boundary into the caller-owned diagnostic.
    try:
        # Preserve exact missing/corrupt distinctions and bytes through the strict provider seam.
        return provider.read_document_strict(document, guarded_default)
    # Keep state_store's established caller-specific recovery message without exposing payload data.
    except RuntimeError as exc:
        # Preserve a RuntimeError intentionally raised by the caller's lazy default.
        if default_failed or str(exc) != "Stored document requires operator recovery":
            # Re-raise the original caller-owned exception unchanged.
            raise
        # Raise the fixed caller-owned message while discarding provider implementation detail.
        raise RuntimeError(invalid_message) from None

# Define the write_json function used by this module.
def write_json(path: Path, data: Any) -> None:
    # Resolve the complete provider-owned document reference once for this write.
    provider, document = _provider_document(path)
    # Delegate atomic publication and planner guards to the selected provider.
    provider.write_document(document, data)

# Apply an atomic read-modify-write so concurrent callers cannot lose each other's updates. (SESSION-007, CORE-021)
def update_json(path: Path, mutator: Callable[[Any], Any], default: Any) -> Any:
    # Resolve the complete provider-owned document reference once for this mutation.
    provider, document = _provider_document(path)
    # Delegate locking, rollback, and atomic publication to the provider contract.
    return provider.update_document(document, mutator, default)

# Apply an atomic mutation that refuses to normalize syntactically corrupt JSON. (SESSION-008)
def update_json_strict(path: Path, mutator: Callable[[Any], Any], default: Any, invalid_message: str) -> Any:
    # Resolve the complete provider-owned document reference once for this strict mutation.
    provider, document = _provider_document(path)
    # Track caller-owned execution so its RuntimeError is never rewritten as storage corruption.
    caller_failed = False

    # Preserve lazy default construction while marking only caller exceptions.
    def guarded_default() -> Any:
        # Share the caller-failure flag with the outer provider boundary.
        nonlocal caller_failed
        # Start caller-owned default construction without evaluating it early.
        try:
            # Return the caller's fresh absent-document state.
            return default() if callable(default) else default
        # Record and preserve any caller exception exactly.
        except Exception:
            # Prevent the provider recovery translator from replacing this failure.
            caller_failed = True
            # Re-raise the original caller exception and traceback.
            raise

    # Apply the caller mutation while marking only exceptions from caller code.
    def guarded_mutator(current: Any) -> Any:
        # Share the caller-failure flag with the outer provider boundary.
        nonlocal caller_failed
        # Start the caller-owned transition after provider strict validation.
        try:
            # Return the caller's complete updated document.
            return mutator(current)
        # Record and preserve any caller exception exactly.
        except Exception:
            # Prevent the provider recovery translator from replacing this failure.
            caller_failed = True
            # Re-raise the original caller exception and traceback.
            raise
    # Start the provider-owned strict transaction with a shape-neutral validation seam.
    try:
        # A true predicate selects strict decoding while preserving state_store's shape-neutral contract.
        return provider.update_document(document, guarded_mutator, guarded_default, validator=lambda _value: True)
    # Translate only the fixed provider recovery boundary into the caller-owned diagnostic.
    except RuntimeError as exc:
        # Preserve RuntimeError from either caller-owned callback unchanged.
        if caller_failed or str(exc) != "Stored document requires operator recovery":
            # Re-raise the original caller exception and traceback.
            raise
        # Preserve the source bytes or row and expose no provider-specific detail.
        raise RuntimeError(invalid_message) from None

# Define the append_jsonl function used by this module.
def append_jsonl(path: Path, event: dict) -> None:
    # Create only intentionally local log directories without opening a provider transaction.
    _ensure_log_dirs()
    # Serialize the append inside this process because JSONL diagnostics are intentionally local.
    with _LOG_LOCK:
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
    # Serialize notice deduplication with the local diagnostic reentrant lock.
    with _LOG_LOCK:
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
    return GAME_DATA_DIR / f"{game_id}.json"

# Define the player_game_state_path function used by this module.
def player_game_state_path(game_id: str, player_id: str) -> Path:
    # Set safe_player_id to the value needed for filesystem-safe player state.
    safe_player_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(player_id or "human"))
    return GAME_DATA_DIR / game_id / f"{safe_player_id}.json"

# Define the load_game_state function used by this module.
def load_game_state(game_id: str, default_factory: Callable[[], dict]) -> dict:
    # Set state to the value needed for the next operation.
    state = read_json(game_state_path(game_id), default_factory)
    if not isinstance(state, dict):
        # Set state to the value needed for the next operation.
        state = default_factory()
    state.setdefault("schema_version", SCHEMA_VERSION)
    # Repair descriptor-owned settings before the legacy state can reach any engine consumer.
    return _repair_loaded_game_rules(game_id, state)

# Define the load_player_game_state function used by this module.
def load_player_game_state(game_id: str, player_id: str, default_factory: Callable[[], dict]) -> dict:
    # Set path to the player-scoped file so private sessions do not share in-progress state.
    path = player_game_state_path(game_id, player_id)
    # Branch when a legacy human state file should be honored for v1 compatibility.
    if str(player_id or "human") == "human" and not _document_exists(path) and _document_exists(game_state_path(game_id)):
        # Return the legacy state so existing local data remains readable.
        return load_game_state(game_id, default_factory)
    # Set state to the value needed for the next operation.
    state = read_json(path, default_factory)
    # Branch when the stored payload is malformed.
    if not isinstance(state, dict):
        # Set state to a fresh default payload.
        state = default_factory()
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
        if str(player_id or "human") == "human" and not _document_exists(path) and _document_exists(game_state_path(game_id)):
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
    write_json(game_state_path(game_id), state)

# Define the save_player_game_state function used by this module.
def save_player_game_state(game_id: str, player_id: str, state: dict) -> None:
    # Set state to a copy so callers keep their in-memory object identity.
    state = dict(state)
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Set state["updated_at"] to the value needed for the next operation.
    state["updated_at"] = utc_now()
    write_json(player_game_state_path(game_id, player_id), state)

# Define the migrate_from_v7_if_needed function used by this module.
def migrate_from_v7_if_needed() -> None:
    """Best-effort migration of older monolithic files into v8 data layout.

    # Execute this statement as part of the module's documented control flow.
    We intentionally do not migrate half-finished hands/draws because v7 global state could be inconsistent.
    """
    ensure_dirs()
    # Resolve the configured provider's canonical reference for the local migration marker.
    marker_reference = get_storage_provider().document_reference(DATA_DIR / ".v8_migration_complete", DATA_DIR)
    # Branch when the provider translates local files into database document keys.
    if not isinstance(marker_reference, Path):
        # Return without importing local legacy files into a non-filesystem provider.
        return
    # Set marker to the value needed for the next operation.
    marker = DATA_DIR / ".v8_migration_complete"
    if marker.exists():
        return
    # Set root to the value needed for the next operation.
    root = DATA_DIR.parent
    # Set old_state to the value needed for the next operation.
    old_state = root / "casino_state.json"
    # Set old_history to the value needed for the next operation.
    old_history = root / "roulette_history.csv"
    # Set backup_dir to the value needed for the next operation.
    backup_dir = DATA_DIR / "backup_v7"
    if old_state.exists() or old_history.exists():
        # Set backup_dir.mkdir(exist_ok to the value needed for the next operation.
        backup_dir.mkdir(exist_ok=True)
    if old_state.exists():
        # Use this standard-library helper to perform the requested operation.
        shutil.copy2(old_state, backup_dir / old_state.name)
        # Start protected logic so failures can be handled safely.
        try:
            # Set old to the value needed for the next operation.
            old = json.loads(old_state.read_text(encoding="utf-8"))
            # Set bal to the value needed for the next operation.
            bal = old.get("balance") or old.get("player_balance") or old.get("human_balance")
            if isinstance(bal, (int, float)):
                # Set players_path to the value needed for the next operation.
                players_path = DATA_DIR / "players.json"
                if not players_path.exists():
                    write_json(players_path, {"schema_version": SCHEMA_VERSION, "players": [
                        {"player_id": "human", "display_name": "You", "type": "human", "balance": round(float(bal), 2), "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                        {"player_id": "bot_1", "display_name": "Ava", "type": "bot", "balance": 5000, "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                        {"player_id": "bot_2", "display_name": "Mia", "type": "bot", "balance": 5000, "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                        {"player_id": "bot_3", "display_name": "Zoe", "type": "bot", "balance": 5000, "created_at": utc_now(), "updated_at": utc_now(), "status": "active"},
                    ]})
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Intentionally leave this block empty.
            pass
    if old_history.exists():
        # Use this standard-library helper to perform the requested operation.
        shutil.copy2(old_history, backup_dir / old_history.name)
        # Set history_path to the value needed for the next operation.
        history_path = DATA_DIR / "history.csv"
        if not history_path.exists():
            # Use this standard-library helper to perform the requested operation.
            shutil.copy2(old_history, history_path)
    # Set marker.write_text(utc_now(), encoding to the value needed for the next operation.
    marker.write_text(utc_now(), encoding="utf-8")
