# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import annotations so provider type hints can refer to classes declared later.
from __future__ import annotations
# Import process-exit hooks so cached MySQL pools release idle connections on shutdown.
import atexit
# Import required dependency so action fingerprints are derived from canonical transaction semantics.
import hashlib
# Import required dependency so process-lock helpers can be expressed as context managers.
from contextlib import contextmanager
# Import required dependency so this module can use structured configuration values.
from dataclasses import dataclass
# Import required dependency so decimal balances from MySQL can be normalized.
from decimal import Decimal
# Import required dependency so provider payloads can be serialized consistently.
import json
# Import required dependency so environment configuration can select the provider.
import os
# Import required dependency so JSON fallback storage can manage local files.
import shutil
# Import required dependency so reset rollback state can be preserved in one durable artifact.
import tarfile
# Import required dependency so JSON fallback writes remain process-thread atomic.
import threading
# Import required dependency so Windows replace retries can wait for transient file-handle release.
import time
# Import required dependency so local JSON fallback paths stay platform-safe.
from pathlib import Path
# Import required dependency so provider methods can accept default factories.
from typing import Any, Callable

# Import runtime paths and schema constants shared by all storage providers.
from casino.config import DATA_DIR, DEFAULT_MYSQL_DATABASE, DEFAULT_MYSQL_HOST, DEFAULT_MYSQL_PORT, DEFAULT_MYSQL_USER, DEFAULT_STORAGE_PROVIDER, GAME_DATA_DIR, LOG_DIR, SCHEMA_VERSION
# Import required dependency so provider-created rows use the app timestamp format.
from casino.core.clock import utc_now
# Import the immutable route-free game-action contract implemented only by the JSON provider.
from casino.core.game_action import GameActionExecutor, GameActionIdentity, GameActionMovement, GameActionPlan, GameActionReceipt, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, canonical_json_bytes, validate_execution_request
# Import required dependency so provider-created ledger rows use stable IDs.
from casino.core.ids import new_id
# Import read-only MySQL migration compatibility without exposing deployment credentials.
from casino.core.mysql_migrations import verify_runtime_compatibility
# Import the bounded process-local MySQL connection lifecycle.
from casino.core.mysql_pool import MySQLConnectionPool, MySQLPoolConfig
# Import required dependency so storage providers surface existing API errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError

# Set _PROVIDER_LOCK to guard lazy provider construction.
_PROVIDER_LOCK = threading.RLock()
# Set _PROVIDER to cache the selected provider for one process.
_PROVIDER: StorageProvider | None = None
# Set _TEST_PROVIDER to allow storage tests to inject an isolated provider.
_TEST_PROVIDER: StorageProvider | None = None
# Guard construction of process-shared JSON root locks.
_JSON_GATE_REGISTRY_LOCK = threading.RLock()
# Share one reentrant thread gate across every provider instance for the same JSON root.
_JSON_GATE_LOCKS: dict[str, threading.RLock] = {}
# Track nested gate and planner state without leaking it across threads.
_JSON_GATE_LOCAL = threading.local()
# Version the provider-private durable action files independently from public storage.
_GAME_ACTION_STORAGE_VERSION = 1
# Enumerate the only durable recovery stages accepted from the private journal.
_GAME_ACTION_STAGES = {"prepared", "planned", "wallet_applied", "state_applied", "receipt_committed"}


# Return the process-shared reentrant lock for one exact JSON data root.
def _json_gate_lock(root_key: str) -> threading.RLock:
    # Serialize first construction so provider instances cannot receive different locks.
    with _JSON_GATE_REGISTRY_LOCK:
        # Reuse an existing lock or construct the sole lock for this root.
        return _JSON_GATE_LOCKS.setdefault(root_key, threading.RLock())


# Define the MySQLConfig class that groups MySQL connection settings.
@dataclass(frozen=True)
class MySQLConfig:  # Group environment-derived MySQL connection settings.
    # Store the MySQL host selected by configuration.
    host: str
    # Store the MySQL TCP port selected by configuration.
    port: int
    # Store the MySQL username selected by configuration.
    user: str
    # Store the MySQL password selected by configuration.
    password: str
    # Store the MySQL database selected by configuration.
    database: str

    # Build a config object from environment variables.
    @classmethod
    def from_env(cls) -> MySQLConfig:  # Build a config object from environment variables.
        # Return the environment-backed configuration for a MySQL provider.
        return cls(
            # Read CASINO_MYSQL_HOST or use localhost for developer databases.
            host=os.getenv("CASINO_MYSQL_HOST", DEFAULT_MYSQL_HOST),
            # Read CASINO_MYSQL_PORT or use the standard MySQL port.
            port=int(os.getenv("CASINO_MYSQL_PORT", str(DEFAULT_MYSQL_PORT))),
            # Read CASINO_MYSQL_USER or use a local casino user convention.
            user=os.getenv("CASINO_MYSQL_USER", DEFAULT_MYSQL_USER),
            # Read CASINO_MYSQL_PASSWORD without logging or echoing the secret.
            password=os.getenv("CASINO_MYSQL_PASSWORD", ""),
            # Read CASINO_MYSQL_DATABASE or use the project database convention.
            database=os.getenv("CASINO_MYSQL_DATABASE", DEFAULT_MYSQL_DATABASE),
        )

    # Convert config fields to mysql.connector keyword arguments.
    def kwargs(self) -> dict:
        # Return a plain dict because mysql.connector accepts keyword parameters.
        return {"host": self.host, "port": self.port, "user": self.user, "password": self.password, "database": self.database}


# Apply one caller-owned strict document-shape predicate with a fixed recovery boundary.
def _validated_strict_document(value: Any, validator: Callable[[Any], bool] | None) -> Any:
    # Return the decoded provider value unchanged when no strict shape was requested.
    if validator is None:
        # Preserve ordinary provider behavior for all existing document callers.
        return value
    # Start protected validation so caller exceptions cannot disclose stored values or paths.
    try:
        # Require the security predicate to affirm the complete decoded value explicitly.
        valid = validator(value) is True
    # Collapse every validator failure into one fixed provider-owned recovery error.
    except Exception:
        # Preserve the stored document and hide validator or payload details.
        raise RuntimeError("Stored document requires operator recovery") from None
    # Reject every false or non-boolean predicate result.
    if not valid:
        # Preserve the stored document and return no payload-specific detail.
        raise RuntimeError("Stored document requires operator recovery")
    # Return the exact decoded value only after strict validation.
    return value


# Define the StorageProvider interface used by core modules.
class StorageProvider:
    # Store a human-readable provider name for diagnostics and tests.
    name = "base"

    # Ensure backing storage exists before callers read or write state.
    def ensure_ready(self) -> None:
        # Raise because concrete providers must create their own storage.
        raise NotImplementedError

    # Reset mutable casino storage for test and local reset flows.
    def reset(self) -> None:
        # Raise because concrete providers must clear their own storage.
        raise NotImplementedError

    # Hold a provider-owned reset boundary through caller bootstrap work.
    @contextmanager
    def reset_transaction(self):
        # Preserve existing non-JSON provider behavior by resetting before bootstrap.
        self.reset()
        # Preserve the shipped route's local artifact cleanup for MySQL-like providers.
        if DATA_DIR.exists():
            # Remove the complete legacy local data root before caller recreation.
            shutil.rmtree(DATA_DIR)
        # Yield the provider selected by the reset caller.
        yield self

    # Hold a provider-owned visibility boundary around direct storage-backed reads.
    @contextmanager
    def state_visibility_transaction(self):
        # Preserve non-JSON behavior because its state is not reset through JSON directories.
        yield self

    # Return true when at least one player has already been bootstrapped.
    def has_players(self) -> bool:
        # Raise because concrete providers must inspect their own player store.
        raise NotImplementedError

    # Load the player document shape used by the existing players API.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Raise because concrete providers must map their own storage rows.
        raise NotImplementedError

    # Save a full player document for bootstrap and reset compatibility.
    def save_players(self, state: dict) -> None:
        # Raise because concrete providers must map their own storage rows.
        raise NotImplementedError

    # Update one player using the existing updater callback contract.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Raise because concrete providers must preserve update semantics.
        raise NotImplementedError

    # Create one deterministic player exactly once or return its existing compatible row.
    def ensure_player(self, player: dict) -> dict:
        # Raise because concrete providers must serialize deterministic player provisioning.
        raise NotImplementedError

    # Execute a ledger transaction and persist the resulting balance atomically.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Raise because concrete providers must enforce atomic ledger writes.
        raise NotImplementedError

    # Execute or replay one storage-enforced ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
        # Raise because concrete providers must enforce action uniqueness with wallet persistence.
        raise NotImplementedError

    # Read recent ledger events with optional player filtering.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Raise because concrete providers must expose admin and player history.
        raise NotImplementedError

    # Append a normalized history event for game outcomes.
    def append_history(self, event: dict) -> None:
        # Raise because concrete providers must persist history rows.
        raise NotImplementedError

    # Return recent history rows with optional game filtering.
    def recent_history(self, limit: int = 100, game: str | None = None) -> list[dict]:
        # Raise because concrete providers must expose history rows.
        raise NotImplementedError

    # Read a named JSON document such as audio settings.
    def read_document(self, key: str, default: Any) -> Any:
        # Raise because concrete providers must persist settings documents.
        raise NotImplementedError

    # Read one security-sensitive document without corruption fallback or read-side writes.
    def read_document_strict(self, key: str, default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Raise because concrete providers must own strict missing/corrupt distinctions.
        raise NotImplementedError

    # Write a named JSON document such as audio settings.
    def write_document(self, key: str, data: Any) -> None:
        # Raise because concrete providers must persist settings documents.
        raise NotImplementedError

    # Mutate one named JSON document atomically under the provider's cross-process transaction boundary.
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Raise because concrete providers must own their read-modify-write concurrency semantics.
        raise NotImplementedError


# Define the JsonStorageProvider that preserves default local file behavior.
class JsonStorageProvider(StorageProvider, GameActionExecutor):
    # Store the provider name used by diagnostics and tests.
    name = "json"

    # Initialize the JSON provider with an optional data root for tests.
    def __init__(self, data_dir: Path | None = None) -> None:
        # Store the root data directory for this provider instance.
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        # Store the games directory used by existing per-game state helpers.
        self.game_data_dir = self.data_dir / "games"
        # Store the logs directory that remains file-backed for local diagnostics.
        self.log_dir = self.data_dir.parent / "logs" if data_dir is not None else LOG_DIR
        # Cache no control root until caller configuration is complete and first use validates it.
        self._json_control_root_cache: Path | None = None
        # Bind the eventual control root to one canonical DATA_DIR identity.
        self._json_control_data_key: str | None = None
        # Bind the eventual control root to one canonical LOG_DIR identity.
        self._json_control_log_key: str | None = None
        # Store the provider-local lock for compound JSON operations.
        self.lock = threading.RLock()
        # Track how many ledger.jsonl bytes have been parsed into the incremental cache. (issue #412)
        self._ledger_cache_offset = 0
        # Track the ledger file mtime at the cached offset so rewrites invalidate the cache. (issue #412)
        self._ledger_cache_mtime_ns: int | None = None
        # Cache decoded valid ledger rows in append order so reads stop re-parsing the file. (issue #412)
        self._ledger_cache_rows: list[dict] = []
        # Index cached row references by player so filtered history reads stay O(tail). (issue #412)
        self._ledger_cache_by_player: dict[Any, list[dict]] = {}
        # Hold rows decoded from an unterminated trailing line without caching them. (issue #412)
        self._ledger_cache_tail_rows: list[dict] = []
        # Track the (size, mtime_ns) identity of the parsed committed-action registry file. (issue #412)
        self._actions_cache_stat: tuple[int, int] | None = None
        # Cache the parsed committed-action registry so wallet actions stop re-parsing it. (issue #412)
        self._actions_cache_registry: Any = None

    # Return the local JSON players path.
    def players_path(self) -> Path:
        # Return the existing players file path under the configured data root.
        return self.data_dir / "players.json"

    # Return the local JSONL ledger path.
    def ledger_path(self) -> Path:
        # Return the existing ledger file path under the configured data root.
        return self.data_dir / "ledger.jsonl"

    # Return the local committed-action registry path.
    def ledger_actions_path(self) -> Path:
        # Return the provider journal that makes action identity durable before projection.
        return self.data_dir / "ledger_actions.json"

    # Return the cross-process wallet lock path.
    def ledger_lock_path(self) -> Path:
        # Return one provider-local lock file shared by all wallet-writing processes.
        return self.data_dir / ".ledger.lock"

    # Return the one lock path shared by every action-affected JSON projection.
    def json_gate_path(self) -> Path:
        # Reuse the verified private control root for the persistent global gate.
        return self._json_control_root() / "global.lock"

    # Return the provider-private recoverable game-action journal path.
    def game_action_journal_path(self) -> Path:
        # Keep incomplete action state outside public documents and ledger projections.
        return self.data_dir / ".game_actions" / "journal.json"

    # Return the provider-private immutable game-action receipt registry path.
    def game_action_receipts_path(self) -> Path:
        # Persist committed identities independently from append-only ledger compatibility.
        return self.data_dir / ".game_actions" / "receipts.json"

    # Return the provider-private action-managed game-state registry path.
    def game_action_states_path(self) -> Path:
        # Keep route-free state resources isolated until a later governed game adoption.
        return self.data_dir / ".game_actions" / "states.json"

    # Return one sidecar lock path for an atomic named-document mutation.
    def document_lock_path(self, key: str) -> Path:
        # Place the lock beside the selected document so independent documents do not block each other.
        return self.document_path(key).with_suffix(".json.lock")

    # Return the local CSV history path.
    def history_path(self) -> Path:
        # Return the existing history file path under the configured data root.
        return self.data_dir / "history.csv"

    # Return the local JSON document path for a named document key.
    def document_path(self, key: str) -> Path:
        # Return a namespaced JSON path so settings retain their current layout.
        return self.data_dir / f"{key}.json"

    # Create local data folders only after the caller owns the stable provider gate.
    def _ensure_ready_direct(self) -> None:
        # Create the root data directory for player, ledger, history, and settings files.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Create the per-game state directory used by state_store helpers.
        self.game_data_dir.mkdir(parents=True, exist_ok=True)
        # Create the log directory used by test and runtime diagnostics.
        self.log_dir.mkdir(parents=True, exist_ok=True)
        # Create the test-run log directory used by the existing test runner.
        (self.log_dir / "test-runs").mkdir(parents=True, exist_ok=True)
        # Create the settings directory used by the audio settings document.
        (self.data_dir / "settings").mkdir(parents=True, exist_ok=True)

    # Ensure local data folders exist under the provider-wide visibility boundary.
    def ensure_ready(self) -> None:
        # Reject directory mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Serialize directory creation with local provider operations.
        with self.lock:
            # Acquire the stable gate before recreating any reset-owned path.
            with self._json_global_gate():
                # The outer gate creates required directories before yielding.
                return None

    # Forget every cached ledger row so the next read reloads from the file. (issue #412)
    def _drop_ledger_cache(self) -> None:
        # Restart incremental parsing from the beginning of the ledger file.
        self._ledger_cache_offset = 0
        # Forget the cached file identity so any observed state forces a reload.
        self._ledger_cache_mtime_ns = None
        # Discard previously decoded append-order rows.
        self._ledger_cache_rows = []
        # Discard the per-player index built from the discarded rows.
        self._ledger_cache_by_player = {}
        # Discard rows decoded from an unterminated trailing line.
        self._ledger_cache_tail_rows = []

    # Forget the cached committed-action registry so the next read reloads from the file. (issue #412)
    def _drop_actions_cache(self) -> None:
        # Forget the cached registry file identity.
        self._actions_cache_stat = None
        # Discard the cached parsed registry object.
        self._actions_cache_registry = None

    # Clear JSON data while preserving the held legacy lock file and identity.
    def _reset_locked(self) -> None:
        # Resolve the exact lock entry that must survive reset.
        legacy_lock = self.ledger_lock_path()
        # Enumerate every current data-root child under stable and legacy locks.
        for child in tuple(self.data_dir.iterdir()):
            # Preserve the exact open legacy lock inode across the reset.
            if child == legacy_lock:
                # Continue without unlinking or replacing the interoperability lock.
                continue
            # Remove directories recursively using the existing reset semantics.
            if child.is_dir() and not child.is_symlink():
                # Delete only this exact data-root child tree.
                shutil.rmtree(child)
            # Remove files, symlinks, and other leaf entries without following them.
            else:
                # Delete only this exact data-root child.
                child.unlink()
        # Drop the ledger tail cache so reads never serve pre-reset rows. (issue #412)
        self._drop_ledger_cache()
        # Drop the action-registry cache alongside its removed backing file. (issue #412)
        self._drop_actions_cache()
        # Recreate every ordinary provider directory before caller bootstrap.
        self._ensure_ready_direct()

    # Return the stable prefix shared by this provider's reset recovery artifacts.
    def _reset_backup_prefix(self) -> str:
        # Return a fixed private prefix inside this canonical data root's control directory.
        return "reset-backup-"

    # Return one collision-resistant sibling path for a reset rollback snapshot.
    def _reset_backup_path(self) -> Path:
        # Keep one single-file rollback artifact in the verified private control root.
        return self._json_control_root() / f"{self._reset_backup_prefix()}{os.getpid()}-{os.urandom(8).hex()}.tar"

    # Reject unresolved reset recovery material before exposing provider state.
    def _require_no_reset_recovery_locked(self) -> None:
        try:
            # Resolve the verified private control root without creating any filesystem entry.
            control_root = self._json_control_root()
            # Discover only this canonical provider root's final recovery artifacts.
            backups = tuple(control_root.glob(f"{self._reset_backup_prefix()}*.tar"))
            # Discover only this canonical provider root's unpublished staging artifacts.
            temporaries = tuple(control_root.glob(f"{self._reset_backup_prefix()}*.tar.tmp-*"))
            # Combine the two exact provider-owned residue patterns.
            residues = backups + temporaries
        # Normalize discovery failures without exposing filesystem details.
        except OSError:
            # Require operator recovery when the private recovery boundary cannot be inspected.
            raise ConflictError("JSON reset requires operator recovery") from None
        # Fail closed while any prior reset recovery artifact remains unresolved.
        if residues:
            # Prevent later reads or writes from bypassing a failed reset boundary.
            raise ConflictError("JSON reset requires operator recovery")

    # Validate one private archive member before using its relative path.
    def _reset_archive_member_parts(self, name: str) -> tuple[str, ...]:
        # Reject empty, absolute, backslash, drive-like, and non-canonical archive names.
        if type(name) is not str or not name or name.startswith("/") or "\\" in name or ":" in name:
            # Preserve the private archive for operator recovery.
            raise ConflictError("JSON reset requires operator recovery")
        # Split the provider-created POSIX archive path without filesystem resolution.
        parts = tuple(name.split("/"))
        # Reject traversal, empty segments, and redundant current-directory segments.
        if any(part in {"", ".", ".."} for part in parts):
            # Preserve the private archive for operator recovery.
            raise ConflictError("JSON reset requires operator recovery")
        # Return the exact safe relative path components.
        return parts

    # Return the exact SHA-256 digest of one regular file without exposing its path.
    def _reset_file_digest(self, path: Path) -> str:
        # Initialize one deterministic streaming digest.
        digest = hashlib.sha256()
        try:
            # Open only the validated regular file in binary mode.
            with path.open("rb") as handle:
                # Read bounded chunks until the complete file has been hashed.
                while True:
                    # Read one bounded block without retaining file contents.
                    chunk = handle.read(1024 * 1024)
                    # Stop after the final empty read.
                    if not chunk:
                        # Leave the streaming loop after complete input.
                        break
                    # Incorporate this exact file block into the digest.
                    digest.update(chunk)
        # Normalize file-read failures without exposing private paths.
        except OSError:
            # Preserve the recovery artifact for operator review.
            raise ConflictError("JSON reset requires operator recovery") from None
        # Return the complete lowercase digest.
        return digest.hexdigest()

    # Flush restored directory entries before declaring rollback durable.
    def _fsync_reset_directories_locked(self) -> None:
        # Windows lacks a portable directory-handle fsync boundary.
        if os.name == "nt":
            # Rely on flushed files and atomic namespace operations on Windows.
            return
        # Enumerate deepest directories first, then the provider root itself.
        directories = sorted((entry for entry in self.data_dir.rglob("*") if entry.is_dir()), key=lambda entry: len(entry.parts), reverse=True)
        # Include the provider root whose direct children were restored.
        directories.append(self.data_dir)
        # Include the data-root parent whose child identity must remain durable.
        directories.append(self.data_dir.parent)
        # Flush each exact restored directory entry table.
        for directory in directories:
            # Track the raw descriptor for guaranteed release.
            descriptor = None
            try:
                # Open the exact directory without following a caller-provided path.
                descriptor = os.open(directory, os.O_RDONLY)
                # Flush contained entry names and metadata through the operating system.
                os.fsync(descriptor)
            # Normalize any durability failure into the recovery boundary.
            except OSError:
                # Preserve the sole rollback artifact.
                raise ConflictError("JSON reset requires operator recovery") from None
            finally:
                # Close only a descriptor successfully opened above.
                if descriptor is not None:
                    # Release the directory handle after flush or failure.
                    os.close(descriptor)

    # Copy complete pre-reset bytes into one durable artifact outside the reset root.
    def _create_reset_backup_locked(self) -> Path:
        # Allocate one collision-resistant final rollback path.
        backup = self._reset_backup_path()
        # Allocate one collision-resistant sibling temp used only by this transaction.
        temporary = backup.with_suffix(backup.suffix + f".tmp-{os.urandom(8).hex()}")
        # Track whether atomic publication consumed the temporary path.
        published = False
        try:
            # Resolve the legacy lock entry whose inode stays in place.
            legacy_lock = self.ledger_lock_path()
            # Open the private artifact exclusively so residue can never be overwritten.
            with temporary.open("xb") as raw_handle:
                # Stream one uncompressed archive whose file bytes remain exact.
                with tarfile.open(fileobj=raw_handle, mode="w", dereference=False) as archive:
                    # Walk every provider entry in deterministic relative-path order.
                    entries = sorted(self.data_dir.rglob("*"), key=lambda item: item.relative_to(self.data_dir).as_posix())
                    # Serialize every directory and regular file exactly once.
                    for entry in entries:
                        # Keep the separately preserved legacy lock out of rollback state.
                        if entry == legacy_lock:
                            # Continue because the open lock identity survives reset.
                            continue
                        # Reject links and special entries instead of copying external content.
                        if entry.is_symlink() or (not entry.is_dir() and not entry.is_file()):
                            # Preserve source state and fail before destructive reset.
                            raise ConflictError("JSON reset requires operator recovery")
                        # Derive the exact portable member name beneath the provider root.
                        member_name = entry.relative_to(self.data_dir).as_posix()
                        # Add this single entry without recursive duplicate traversal.
                        archive.add(entry, arcname=member_name, recursive=False)
                # Flush Python buffers after the complete tar stream is finalized.
                raw_handle.flush()
                # Flush exact rollback bytes through the operating system.
                os.fsync(raw_handle.fileno())
            # Publish the complete single-file recovery artifact atomically.
            temporary.replace(backup)
            # Record that the final path now owns the durable recovery bytes.
            published = True
            # Flush the sibling directory entry on platforms that support it.
            self._fsync_game_action_parent(backup)
        # Normalize every staging failure without exposing paths or source names.
        except BaseException:
            try:
                # Remove only an unpublished private temporary artifact.
                temporary.unlink(missing_ok=True)
            # Preserve the fixed recovery boundary even if temp cleanup fails.
            except OSError:
                # Require operator recovery without exposing filesystem details.
                raise ConflictError("JSON reset requires operator recovery") from None
            # Keep any published backup after a durability failure for operator recovery.
            if published:
                # Normalize the failure while retaining the only recovery artifact.
                raise ConflictError("JSON reset requires operator recovery") from None
            # Normalize pre-publication failures while original state remains untouched.
            raise ConflictError("JSON reset backup failed") from None
        # Return the complete durable private rollback artifact.
        return backup

    # Restore complete pre-reset bytes after a failed caller bootstrap.
    def _restore_reset_backup_locked(self, backup: Path) -> None:
        try:
            # Open the single durable rollback artifact without modifying it.
            with tarfile.open(backup, mode="r:") as archive:
                # Read the complete member table before destructive restoration.
                members = archive.getmembers()
                # Reject duplicate or case-colliding durable member identities.
                normalized_names = [os.path.normcase(member.name) for member in members]
                # Require every recorded entry to have one unique platform identity.
                if len(normalized_names) != len(set(normalized_names)):
                    # Preserve the archive and current partial state for operator recovery.
                    raise ConflictError("JSON reset requires operator recovery")
                # Validate every member before clearing partial post-reset state.
                for member in members:
                    # Accept only ordinary directories and regular files.
                    if not member.isdir() and not member.isfile():
                        # Reject links and special archive entries.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Validate the exact relative member path.
                    self._reset_archive_member_parts(member.name)
                # Record the exact expected directory and regular-file inventory.
                expected_inventory = {member.name: "directory" if member.isdir() else "file" for member in members}
                # Record exact file sizes and hashes before destructive restoration.
                expected_files = {}
                # Inspect every regular-file member in the intact archive.
                for member in members:
                    # Skip directory entries because their identity is verified by inventory.
                    if member.isdir():
                        # Continue to the next archive member.
                        continue
                    # Open the archived regular-file payload for pre-restore verification.
                    source = archive.extractfile(member)
                    # Reject a malformed archive missing regular-file bytes.
                    if source is None:
                        # Preserve the archive for operator recovery.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Initialize the member's exact streaming digest.
                    digest = hashlib.sha256()
                    # Track the exact number of bytes read from the archive.
                    byte_count = 0
                    # Consume the member under its archive-owned handle.
                    with source:
                        # Read bounded chunks until the member is complete.
                        while True:
                            # Read one bounded archive block.
                            chunk = source.read(1024 * 1024)
                            # Stop after the final empty read.
                            if not chunk:
                                # Leave the member loop after complete input.
                                break
                            # Add this block to the exact digest.
                            digest.update(chunk)
                            # Add this block length to the exact byte count.
                            byte_count += len(chunk)
                    # Require the physical payload length to match tar metadata.
                    if byte_count != member.size:
                        # Preserve the archive and current state for operator recovery.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Store the exact expected size and digest by safe member name.
                    expected_files[member.name] = (member.size, digest.hexdigest())
                # Remove every partial post-reset entry while preserving the held legacy lock.
                self._reset_locked()
                # Restore directories before their contained regular files.
                for member in sorted(members, key=lambda item: (not item.isdir(), item.name)):
                    # Resolve the validated destination beneath the provider root.
                    destination = self.data_dir.joinpath(*self._reset_archive_member_parts(member.name))
                    # Recreate an exact directory entry when the member is a directory.
                    if member.isdir():
                        # Create parents so nested empty directories are preserved.
                        destination.mkdir(parents=True, exist_ok=True)
                        # Continue to the next archive member after directory creation.
                        continue
                    # Create the validated parent before restoring file bytes.
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    # Open the archived regular-file payload.
                    source = archive.extractfile(member)
                    # Reject a malformed archive missing regular-file bytes.
                    if source is None:
                        # Preserve the archive for operator recovery.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Stream exact original bytes into a newly created destination.
                    with source, destination.open("xb") as target:
                        # Copy without interpreting JSON or changing byte content.
                        shutil.copyfileobj(source, target)
                        # Flush Python buffering before the restored file becomes visible.
                        target.flush()
                        # Flush restored file bytes through the operating system.
                        os.fsync(target.fileno())
            # Allow focused tests to alter restored bytes before durable verification.
            self._reset_recovery_checkpoint("restore_copied")
            # Build the exact restored inventory excluding the separately preserved legacy lock.
            actual_inventory = {}
            # Resolve the exact legacy lock entry excluded from the archive.
            legacy_lock = self.ledger_lock_path()
            # Enumerate every restored provider entry in deterministic order.
            for entry in sorted(self.data_dir.rglob("*"), key=lambda item: item.relative_to(self.data_dir).as_posix()):
                # Exclude only the stable legacy lock preserved across reset.
                if entry == legacy_lock:
                    # Continue without treating the lock as reset state.
                    continue
                # Derive the exact portable relative identity.
                relative_name = entry.relative_to(self.data_dir).as_posix()
                # Reject links and special files introduced during restoration.
                if entry.is_symlink() or (not entry.is_dir() and not entry.is_file()):
                    # Preserve the rollback artifact and fail closed.
                    raise ConflictError("JSON reset requires operator recovery")
                # Record the exact restored entry type.
                actual_inventory[relative_name] = "directory" if entry.is_dir() else "file"
            # Require exact restored names and types before deleting recovery material.
            if actual_inventory != expected_inventory:
                # Preserve the rollback artifact for operator recovery.
                raise ConflictError("JSON reset requires operator recovery")
            # Verify every restored regular file against archive size and digest.
            for relative_name, (expected_size, expected_digest) in expected_files.items():
                # Resolve the already-validated restored path.
                restored_path = self.data_dir.joinpath(*self._reset_archive_member_parts(relative_name))
                try:
                    # Read the exact restored byte length from filesystem metadata.
                    restored_size = restored_path.stat().st_size
                # Normalize stat failures without exposing private paths.
                except OSError:
                    # Preserve the archive for operator recovery.
                    raise ConflictError("JSON reset requires operator recovery") from None
                # Require exact physical byte length and streaming digest.
                if restored_size != expected_size or self._reset_file_digest(restored_path) != expected_digest:
                    # Preserve the archive for operator recovery.
                    raise ConflictError("JSON reset requires operator recovery")
            # Flush restored namespace entries before declaring verification durable.
            self._fsync_reset_directories_locked()
            # Mark exact durable restoration after inventory, byte, and namespace proof.
            self._reset_recovery_checkpoint("restore_verified")
            # Drop caches so later reads observe restored bytes rather than reset state.
            self._drop_ledger_cache()
            # Drop committed-action cache identities tied to removed post-reset files.
            self._drop_actions_cache()
        # Preserve the sole recovery artifact and normalize every restoration failure.
        except (OSError, tarfile.TarError, ConflictError):
            # Hold all later provider visibility at the operator-recovery boundary.
            raise ConflictError("JSON reset requires operator recovery") from None

    # Remove one exact reset rollback artifact after success or restoration.
    def _remove_reset_backup(self, backup: Path) -> None:
        try:
            # Atomically unlink the sole task-owned rollback artifact.
            backup.unlink()
        # Normalize cleanup failures without exposing the host path.
        except OSError:
            # Prevent releasing a reset boundary with silent task residue.
            raise ConflictError("JSON reset cleanup failed") from None

    # Hold reset, recreation, and caller bootstrap under one reentrant provider gate.
    @contextmanager
    def reset_transaction(self):
        # Reject destructive provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Serialize reset and nested bootstrap calls in this process.
        with self.lock:
            # Hold stable then legacy cross-process locks until final visibility.
            with self._json_global_gate():
                # Snapshot complete pre-reset bytes before destructive mutation.
                backup = self._create_reset_backup_locked()
                # Capture any reset or caller-body failure without releasing either gate.
                failure = None
                try:
                    # Clear provider state without replacing either lock identity.
                    self._reset_locked()
                    # Yield so app bootstrap writes remain inside the same reentrant boundary.
                    yield self
                # Capture clear or bootstrap failure for rollback under the held gate.
                except BaseException as error:
                    # Retain the original failure until restoration and cleanup succeed.
                    failure = error
                # Restore complete pre-reset bytes after clear or caller-body failure.
                if failure is not None:
                    try:
                        # Replace partial post-reset state before releasing visibility.
                        self._restore_reset_backup_locked(backup)
                        # Remove the recovery artifact only after exact restoration.
                        self._remove_reset_backup(backup)
                    # Preserve unresolved recovery material and block later provider entry.
                    except BaseException:
                        # Surface one fixed operator-recovery boundary.
                        raise ConflictError("JSON reset requires operator recovery") from None
                    # Re-raise the original body failure only after exact rollback and cleanup.
                    raise failure
                try:
                    # Commit success by atomically removing the sole recovery artifact.
                    self._remove_reset_backup(backup)
                # Convert cleanup failure into exact rollback before returning an error.
                except BaseException:
                    try:
                        # Restore the complete pre-reset state from the intact artifact.
                        self._restore_reset_backup_locked(backup)
                        # Retry exact artifact deletion after successful restoration.
                        self._remove_reset_backup(backup)
                    # Preserve recovery material and block later visibility on rollback failure.
                    except BaseException:
                        # Surface one fixed operator-recovery boundary.
                        raise ConflictError("JSON reset requires operator recovery") from None
                    # Report cleanup failure only after pre-reset state is restored.
                    raise ConflictError("JSON reset cleanup failed") from None

    # Reset local JSON storage through the complete provider-owned boundary.
    def reset(self) -> None:
        # Hold the reset transaction even when no caller bootstrap follows.
        with self.reset_transaction():
            # Preserve direct reset behavior without additional writes.
            pass

    # Hold one provider-wide visibility boundary for direct JSON tree readers.
    @contextmanager
    def state_visibility_transaction(self):
        # Serialize direct state enumeration with local provider operations.
        with self.lock:
            # Serialize direct state enumeration with reset and independent processes.
            with self._json_global_gate():
                # Converge any pending durable action before exposing provider state.
                self._recover_all_json_actions_locked()
                # Transfer control while the complete JSON tree remains stable.
                yield self

    # Return true when the local players document exists.
    def has_players(self) -> bool:
        # Guard recovery and the existence read from concurrent local threads.
        with self.lock:
            # Serialize with action-owned wallet recovery across processes.
            with self._json_global_gate():
                # Complete every recoverable wallet action before exposing existence.
                self._recover_all_json_actions_locked()
                # Return whether players have already been bootstrapped.
                return self.players_path().exists()

    # Read JSON from a local path with corruption fallback.
    def _read_json(self, path: Path, default: Any) -> Any:
        # Ensure local directories exist before reading.
        self.ensure_ready()
        # Guard reads and possible backup writes with the provider lock.
        with self.lock:
            # Return the caller default when the file does not exist yet.
            if not path.exists():
                # Evaluate default factories lazily to preserve existing behavior.
                return default() if callable(default) else default
            # Start protected parsing so corrupt files can be backed up.
            try:
                # Return the parsed JSON payload from disk.
                return json.loads(path.read_text(encoding="utf-8"))
            # Handle invalid JSON by preserving the corrupt file and returning defaults.
            except json.JSONDecodeError:
                # Build a timestamped backup path next to the corrupt file.
                backup = path.with_suffix(path.suffix + f".corrupt-{int(__import__('time').time())}")
                # Copy the corrupt file so manual recovery remains possible.
                shutil.copy2(path, backup)
                # Return the caller default after backing up the corrupt file.
                return default() if callable(default) else default

    # Write JSON to a local path atomically.
    def _write_json(self, path: Path, data: Any) -> None:
        # Reject direct provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure local directories exist before writing.
        self.ensure_ready()
        # Guard writes with the provider lock.
        with self.lock:
            # Create the target parent directory before writing a temp file.
            path.parent.mkdir(parents=True, exist_ok=True)
            # Build a process-and-thread-unique temp path so concurrent writers never share a handle.
            tmp = path.with_suffix(path.suffix + f".tmp-{os.getpid()}-{threading.get_ident()}")
            # Serialize JSON in the existing pretty/sorted local format.
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
            # Retry transient Windows sharing violations while preserving atomic replacement.
            for attempt in range(20):
                # Start protected replacement so antivirus or indexer handles can release briefly.
                try:
                    # Replace the target atomically after the full payload is written.
                    tmp.replace(path)
                    # Stop retrying after the replacement succeeds.
                    break
                # Handle only transient permission failures from Windows file sharing.
                except PermissionError:
                    # Re-raise the final failure with the original filesystem context.
                    if attempt == 19:
                        # Surface the persistent sharing violation to the caller.
                        raise
                    # Wait a short bounded interval before retrying the atomic replace.
                    time.sleep(0.01 * (attempt + 1))

    # Return one platform-canonical identity for the provider data root.
    def _json_root_key(self) -> str:
        # Normalize aliases and case so equivalent Windows spellings share one gate.
        return os.path.normcase(os.path.realpath(os.fspath(self.data_dir)))

    # Return whether one canonical path is equal to or contained beneath another.
    def _canonical_path_is_within(self, candidate: str, parent: str) -> bool:
        try:
            # Compare canonical roots without performing any filesystem mutation.
            return os.path.commonpath((candidate, parent)) == parent
        # Treat different drives or malformed platform roots as unprovable containment.
        except (OSError, ValueError):
            # Fail the caller's containment proof rather than guessing across roots.
            return False

    # Return the verified reset-safe control root beneath configured LOG_DIR.
    def _json_control_root(self) -> Path:
        # Reuse the first verified identity without consulting later mutable LOG_DIR configuration.
        if self._json_control_root_cache is not None:
            # Recheck only DATA_DIR because operations must never outgrow their bound gate identity.
            if self._json_root_key() != self._json_control_data_key:
                # Refuse state access through a gate derived for a different data root.
                raise ConflictError("JSON storage control path is invalid")
            # Re-resolve the cached path so later symlink or junction changes cannot redirect it.
            cached_control_root = os.path.normcase(os.path.realpath(os.fspath(self._json_control_root_cache)))
            # Require filesystem indirection to retain the originally verified identity.
            if cached_control_root != os.fspath(self._json_control_root_cache):
                # Refuse alternate lock or recovery publication after first use.
                raise ConflictError("JSON storage control path is invalid")
            # Return the exact verified path shared by every gate and reset artifact.
            return self._json_control_root_cache
        # Canonicalize DATA_DIR without creating the reset-owned tree.
        data_root = self._json_root_key()
        # Canonicalize LOG_DIR without creating the separately writable tree.
        log_root = os.path.normcase(os.path.realpath(os.fspath(self.log_dir)))
        # Reject an empty or relative-looking canonical identity before path derivation.
        if not data_root or not log_root or not os.path.isabs(data_root) or not os.path.isabs(log_root):
            # Surface one fixed configuration error without exposing host paths.
            raise ConflictError("JSON storage control path is invalid")
        # Reject LOG_DIR equal to or contained beneath reset-owned DATA_DIR.
        if self._canonical_path_is_within(log_root, data_root):
            # Prevent reset from deleting or replacing the stable lock inode.
            raise ConflictError("JSON storage control path is invalid")
        # Key one private bounded directory by the canonical DATA_DIR identity.
        root_digest = hashlib.sha256(data_root.encode("utf-8")).hexdigest()[:16]
        # Derive the lexical private path only beneath the canonical log root.
        control_candidate = Path(log_root) / ".casino-json" / root_digest
        # Resolve existing symlink, junction, reparse, and parent indirection without creation.
        control_root = os.path.normcase(os.path.realpath(os.fspath(control_candidate)))
        # Require the resolved private root to remain beneath the canonical LOG_DIR.
        if not self._canonical_path_is_within(control_root, log_root):
            # Refuse indirection that escapes the configured writable log boundary.
            raise ConflictError("JSON storage control path is invalid")
        # Require the resolved private root to remain outside reset-owned DATA_DIR.
        if self._canonical_path_is_within(control_root, data_root):
            # Refuse any alias that places stable state inside reset-owned data.
            raise ConflictError("JSON storage control path is invalid")
        # Cache only the verified canonical private root.
        self._json_control_root_cache = Path(control_root)
        # Bind future lookups to the exact canonical data identity.
        self._json_control_data_key = data_root
        # Bind future lookups to the exact canonical log identity.
        self._json_control_log_key = log_root
        # Return only the verified canonical root shared by locks and reset artifacts.
        return self._json_control_root_cache

    # Hold one exact operating-system file lock without a permissive fallback.
    @contextmanager
    def _exclusive_process_file_lock(self, path: Path):
        # Create the lock parent before opening the persistent lock target.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Open a persistent one-byte target shared by every provider process.
        with path.open("a+b") as handle:
            # Branch to the Windows byte-range locking implementation.
            if os.name == "nt":
                # Import the Windows runtime lock API only on Windows.
                import msvcrt
                # Ensure the file contains one byte that can be locked.
                if handle.seek(0, os.SEEK_END) == 0:
                    # Write the lock byte once for a fresh provider root.
                    handle.write(b"0")
                    # Flush the byte before locking it from another process.
                    handle.flush()
                # Seek to the shared one-byte range.
                handle.seek(0)
                # Block until this process exclusively owns the byte range.
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            # Use advisory flock on POSIX development and CI hosts.
            else:
                # Import POSIX locking only where the module is available.
                import fcntl
                # Block until this process exclusively owns the file lock.
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                # Transfer control while the exact cross-process lock is held.
                yield
            finally:
                # Release the Windows byte range owned by this process.
                if os.name == "nt":
                    # Import the Windows runtime lock API only on Windows.
                    import msvcrt
                    # Return to the locked byte before unlocking it.
                    handle.seek(0)
                    # Release the byte range for the next process.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                # Release the POSIX advisory lock on non-Windows hosts.
                else:
                    # Import POSIX locking only where the module is available.
                    import fcntl
                    # Release the file lock for the next process.
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    # Hold the one reentrant operating-system gate across action-affected JSON access.
    @contextmanager
    def _json_global_gate(self):
        # Canonicalize this provider root for process-shared lock and nesting identity.
        root_key = self._json_root_key()
        # Include the process ID so forked children never inherit a false nested state.
        depth_key = (os.getpid(), root_key)
        # Serialize all threads and provider instances for this exact data root.
        with _json_gate_lock(root_key):
            # Read the call-thread's current nesting map or initialize one.
            depths = getattr(_JSON_GATE_LOCAL, "depths", {})
            # Reuse the already-held operating-system lock for a nested provider call.
            if depths.get(depth_key, 0):
                # Increment the exact root nesting depth before yielding.
                depths[depth_key] += 1
                # Retain the updated map on the current thread.
                _JSON_GATE_LOCAL.depths = depths
                try:
                    # Transfer control without reacquiring the non-reentrant OS lock.
                    yield
                finally:
                    # Restore the prior nesting depth after the nested operation.
                    depths[depth_key] -= 1
                # Stop after the nested critical section completes.
                return
            # Acquire the canonical reset-safe lock before every legacy bridge.
            with self._exclusive_process_file_lock(self.json_gate_path()):
                # Refuse recovery residue before recreating any reset-owned directory.
                self._require_no_reset_recovery_locked()
                # Create only the data root needed to open the preserved legacy lock.
                self.data_dir.mkdir(parents=True, exist_ok=True)
                # Acquire the shipped wallet lock second for mixed-version interoperability.
                with self._exclusive_process_file_lock(self.ledger_lock_path()):
                    # Refuse visibility while a failed reset still owns recovery material.
                    self._require_no_reset_recovery_locked()
                    # Create remaining provider directories only after both gates are held.
                    self._ensure_ready_direct()
                    # Remove only stale provider-owned temps left by a stopped prior process.
                    self._cleanup_game_action_temps_locked()
                    # Mark both operating-system locks held before any nested public call.
                    depths[depth_key] = 1
                    # Retain the active nesting map on the current thread.
                    _JSON_GATE_LOCAL.depths = depths
                    try:
                        # Transfer control to the protected provider operation.
                        yield
                    finally:
                        # Remove the outermost marker before releasing legacy then stable locks.
                        depths.pop(depth_key, None)

    # Hold the global JSON gate across a legacy wallet transaction.
    @contextmanager
    def _ledger_process_lock(self):
        # Reuse the provider-wide gate so action and legacy wallet writes serialize.
        with self._json_global_gate():
            # Transfer control while the shared gate is held.
            yield

    # Hold the global JSON gate across a named-document operation.
    @contextmanager
    def _document_process_lock(self, key: str):
        # Resolve the exact legacy per-document sidecar path.
        document_lock = self.document_lock_path(key)
        # Build a process/root/key identity for reentrant same-thread calls.
        depth_key = (os.getpid(), self._json_root_key(), os.path.normcase(os.path.realpath(os.fspath(document_lock))))
        # Acquire the provider-wide gate first for one fixed lock order.
        with self._json_global_gate():
            # Read the current thread's per-document nesting map.
            depths = getattr(_JSON_GATE_LOCAL, "document_depths", {})
            # Reuse an already-held per-document lock on nested provider calls.
            if depths.get(depth_key, 0):
                # Increment the exact document nesting depth.
                depths[depth_key] += 1
                # Retain the updated thread-local map.
                _JSON_GATE_LOCAL.document_depths = depths
                try:
                    # Transfer control without reacquiring the legacy OS sidecar.
                    yield
                finally:
                    # Restore the prior nesting depth.
                    depths[depth_key] -= 1
                # Stop after the nested critical section.
                return
            # Bridge current-main processes still using only the per-key sidecar.
            with self._exclusive_process_file_lock(document_lock):
                # Mark the legacy sidecar held for nested calls.
                depths[depth_key] = 1
                # Retain the active map on the current thread.
                _JSON_GATE_LOCAL.document_depths = depths
                try:
                    # Transfer control while stable, legacy-wallet, and document locks are held.
                    yield
                finally:
                    # Remove the outermost per-document nesting marker.
                    depths.pop(depth_key, None)

    # Return whether this thread is executing a planner for this JSON root.
    def _planner_is_active(self) -> bool:
        # Read the thread-local active-root set without creating shared mutable defaults.
        roots = getattr(_JSON_GATE_LOCAL, "planner_roots", set())
        # Match this provider by its canonical data-root identity.
        return self._json_root_key() in roots

    # Reject provider mutation attempted from inside a supposedly pure planner.
    def _reject_planner_mutation(self) -> None:
        # Fail before any provider write while this root is being planned.
        if self._planner_is_active():
            # Publish the shared contract's fixed side-effect boundary.
            raise ValidationError("Game action planner must be side-effect free")

    # Mark one synchronous planner call as unable to mutate this provider root.
    @contextmanager
    def _planner_boundary(self):
        # Resolve the exact provider root shared by every instance in this thread.
        root_key = self._json_root_key()
        # Copy the thread-local active-root set so nesting is explicit.
        roots = set(getattr(_JSON_GATE_LOCAL, "planner_roots", set()))
        # Reject recursive action planning before invoking nested RNG.
        if root_key in roots:
            # Preserve the fixed planner-purity failure.
            raise ValidationError("Game action planner must be side-effect free")
        # Mark this root active for every provider instance on the current thread.
        roots.add(root_key)
        # Publish the active set to mutation guards.
        _JSON_GATE_LOCAL.planner_roots = roots
        try:
            # Transfer control to the caller-owned synchronous planner.
            yield
        finally:
            # Remove this root even when the planner raises.
            roots.discard(root_key)
            # Retain any unrelated active roots on this thread.
            _JSON_GATE_LOCAL.planner_roots = roots

    # Allow focused tests to inject process-stop boundaries without production behavior.
    def _game_action_checkpoint(self, boundary: str) -> None:
        # Keep the production provider checkpoint side-effect free.
        return None

    # Allow focused tests to inject reset-recovery verification failures.
    def _reset_recovery_checkpoint(self, boundary: str) -> None:
        # Keep the production reset-recovery checkpoint side-effect free.
        return None

    # Convert one immutable canonical value to ordinary JSON containers.
    def _plain_canonical(self, value) -> Any:
        # Reuse the contract's unique bounded encoding before decoding plain containers.
        return json.loads(canonical_json_bytes(value).decode("utf-8"))

    # Reject duplicate object keys while decoding provider-owned durable JSON.
    def _unique_json_object(self, pairs: list[tuple[str, Any]]) -> dict:
        # Build one ordinary object after checking every physical key.
        result = {}
        # Inspect pairs in the decoder's source order.
        for key, value in pairs:
            # Reject a repeated key instead of accepting last-value-wins corruption.
            if key in result:
                # Normalize duplicate keys into the private recovery boundary.
                raise ValueError("duplicate key")
            # Retain the unique decoded key and value.
            result[key] = value
        # Return the strictly decoded object.
        return result

    # Read one action-owned JSON file strictly without changing corrupt bytes.
    def _read_game_action_json(self, path: Path, default: Callable[[], Any]) -> Any:
        # Return a fresh default only when the durable file is genuinely absent.
        if not path.exists():
            # Evaluate the provider-owned default factory lazily.
            return default()
        # Decode the exact file while preserving every failure byte-for-byte.
        try:
            # Read and parse with duplicate-key rejection.
            return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=self._unique_json_object)
        # Normalize syntax, Unicode, recursion, digit-limit, and filesystem failures.
        except (OSError, UnicodeError, ValueError, RecursionError):
            # Fail closed without a backup, rewrite, path, or corrupt content disclosure.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Remove bounded stale private temps only while the global process gate is held.
    def _cleanup_game_action_temps_locked(self) -> None:
        # Resolve the sole provider-private action directory.
        parent = self.game_action_journal_path().parent
        # Return without creating a directory for a fresh provider.
        if not parent.exists():
            # Preserve a no-residue fresh read.
            return
        # Enumerate only the exact three owned temp-name prefixes.
        prefixes = ("journal.json.tmp-", "receipts.json.tmp-", "states.json.tmp-")
        try:
            # Inspect every current private-directory entry once.
            for candidate in parent.iterdir():
                # Skip permanent files and unrelated operator evidence.
                if not candidate.name.startswith(prefixes):
                    # Continue without touching non-owned entries.
                    continue
                # Reject links, directories, and special files instead of following them.
                if candidate.is_symlink() or not candidate.is_file():
                    # Preserve ambiguous residue for operator recovery.
                    raise ConflictError("Game action storage cleanup failed")
                # Remove only the exact provider-owned stale temp file.
                candidate.unlink()
        # Normalize filesystem enumeration and deletion failures.
        except OSError:
            # Fail closed without exposing private filesystem paths.
            raise ConflictError("Game action storage cleanup failed") from None

    # Flush a newly published private directory entry on platforms that support it.
    def _fsync_game_action_parent(self, path: Path) -> None:
        # Windows does not expose portable directory handles through os.open.
        if os.name == "nt":
            # Rely on the flushed file plus atomic replacement on the Windows path.
            return
        # Track the raw directory descriptor for guaranteed release.
        descriptor = None
        try:
            # Open only the containing directory without following a caller path.
            descriptor = os.open(path.parent, os.O_RDONLY)
            # Flush the replaced directory entry through the operating system.
            os.fsync(descriptor)
        # Normalize directory durability failures without path disclosure.
        except OSError:
            # Preserve the published file for journal-driven recovery.
            raise ConflictError("Game action storage write failed") from None
        finally:
            # Close only a descriptor successfully opened above.
            if descriptor is not None:
                # Release the directory handle after flush or failure.
                os.close(descriptor)

    # Atomically write one action-owned JSON file with a flushed durable temp.
    def _write_game_action_json(self, path: Path, data: Any) -> None:
        # Reject a direct private write attempted from a planner closure.
        self._reject_planner_mutation()
        # Serialize before touching the destination so invalid values preserve old bytes.
        try:
            # Produce one deterministic bounded JSON byte representation.
            payload = json.dumps(data, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
        # Normalize non-serializable or invalid internal durable values.
        except (TypeError, ValueError, OverflowError):
            # Surface one fixed provider-integrity failure.
            raise ConflictError("Game action storage is invalid") from None
        # Ensure the private parent exists before allocating the owned temp.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Build a collision-resistant owned temp name safe across PID/thread reuse.
        temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}-{threading.get_ident()}-{os.urandom(8).hex()}")
        try:
            # Open a new temp exclusively so stale residue is never overwritten.
            with temporary.open("xb") as handle:
                # Write the complete deterministic payload.
                handle.write(payload)
                # Flush Python buffering before the durability boundary.
                handle.flush()
                # Flush the file bytes through the operating system.
                os.fsync(handle.fileno())
            # Retry only transient Windows sharing violations during atomic publication.
            for attempt in range(20):
                # Start protected replacement so scanner handles can release.
                try:
                    # Publish the complete file atomically over any prior version.
                    temporary.replace(path)
                    # Durably publish the directory entry on supported platforms.
                    self._fsync_game_action_parent(path)
                    # Stop after successful publication.
                    break
                # Retry bounded transient sharing failures.
                except PermissionError:
                    # Re-raise the final failure through the fixed outer boundary.
                    if attempt == 19:
                        # Preserve control for the normalized handler below.
                        raise
                    # Wait a bounded interval before retrying the replace.
                    time.sleep(0.01 * (attempt + 1))
        # Normalize all filesystem publication failures without leaking paths.
        except OSError:
            # Surface one fixed provider-integrity failure.
            raise ConflictError("Game action storage write failed") from None
        finally:
            # Remove only the exact owned temp when publication did not consume it.
            try:
                # Unlink stale owned bytes without touching the destination.
                temporary.unlink(missing_ok=True)
            # Convert cleanup failure into the same fixed storage boundary.
            except OSError:
                # Surface one fixed provider-integrity failure.
                raise ConflictError("Game action storage cleanup failed") from None

    # Remove the private journal after its receipt is durably recoverable.
    def _remove_game_action_journal(self) -> None:
        # Reject a cleanup attempted from inside a planner.
        self._reject_planner_mutation()
        try:
            # Remove only the exact provider-private journal when present.
            self.game_action_journal_path().unlink(missing_ok=True)
            # Resolve the provider-private action directory after journal removal.
            private_directory = self.game_action_journal_path().parent
            # Remove a now-empty private directory after pre-plan failure.
            if private_directory.exists() and not any(private_directory.iterdir()):
                # Remove only the verified empty provider-private directory.
                private_directory.rmdir()
        # Normalize filesystem failures without exposing the operator path.
        except OSError:
            # Preserve a recoverable receipt and journal for the next provider entry.
            raise ConflictError("Game action storage cleanup failed") from None

    # Return the canonical durable scope key for one action identity.
    def _game_action_scope_key(self, identity: GameActionIdentity) -> str:
        # Encode the three bounded identity fragments without delimiter ambiguity.
        return json.dumps(list(identity.scope_key), separators=(",", ":"), ensure_ascii=False)

    # Serialize one exact action identity for journal or receipt storage.
    def _serialize_game_action_identity(self, identity: GameActionIdentity) -> dict:
        # Return only the four immutable identity fields.
        return {
            # Preserve the caller-stable action key.
            "action_key": identity.action_key,
            # Preserve the game namespace.
            "game_id": identity.game_id,
            # Preserve the authenticated owner.
            "player_id": identity.player_id,
            # Preserve the canonical request/resource fingerprint.
            "request_fingerprint": identity.request_fingerprint,
        }

    # Reconstruct one exact action identity from private durable JSON.
    def _deserialize_game_action_identity(self, value: Any) -> GameActionIdentity:
        # Require the exact durable identity field set.
        if type(value) is not dict or set(value) != {"action_key", "game_id", "player_id", "request_fingerprint"}:
            # Reject malformed durable identity state.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reconstruct through the contract's exact direct-validation boundary.
            return GameActionIdentity(
                # Restore the game namespace.
                game_id=value["game_id"],
                # Restore the authenticated owner.
                player_id=value["player_id"],
                # Restore the caller-stable action key.
                action_key=value["action_key"],
                # Restore the canonical semantic fingerprint.
                request_fingerprint=value["request_fingerprint"],
            )
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one exact bounded resource declaration.
    def _serialize_game_action_resources(self, resources: GameActionResources) -> dict:
        # Return the two canonical resource arrays.
        return {
            # Preserve the sorted state resource keys.
            "state_keys": list(resources.state_keys),
            # Preserve the sorted wallet resource identities.
            "wallet_ids": list(resources.wallet_ids),
        }

    # Reconstruct one exact bounded resource declaration.
    def _deserialize_game_action_resources(self, value: Any) -> GameActionResources:
        # Require the exact durable resource field set.
        if type(value) is not dict or set(value) != {"state_keys", "wallet_ids"}:
            # Reject malformed durable resource state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require ordinary JSON arrays before tuple construction.
        if type(value["state_keys"]) is not list or type(value["wallet_ids"]) is not list:
            # Reject coercible or object-shaped resource collections.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reconstruct through the contract's order, identity, and size checks.
            return GameActionResources(wallet_ids=tuple(value["wallet_ids"]), state_keys=tuple(value["state_keys"]))
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one immutable snapshot without leaking provider file layout.
    def _serialize_game_action_snapshot(self, snapshot: GameActionSnapshot) -> dict:
        # Return only canonical wallet and state resource values.
        return {
            # Preserve exact ordered state pairs with plain canonical values.
            "state_values": [[key, self._plain_canonical(value)] for key, value in snapshot.state_values],
            # Preserve exact ordered integer-cent wallet pairs.
            "wallet_balances": [[wallet_id, balance] for wallet_id, balance in snapshot.wallet_balances],
        }

    # Reconstruct one immutable snapshot against an already validated resource set.
    def _deserialize_game_action_snapshot(self, value: Any, resources: GameActionResources) -> GameActionSnapshot:
        # Require the exact durable snapshot field set.
        if type(value) is not dict or set(value) != {"state_values", "wallet_balances"}:
            # Reject malformed durable snapshot state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require ordinary JSON arrays for ordered pairs.
        if type(value["state_values"]) is not list or type(value["wallet_balances"]) is not list:
            # Reject coercible or object-shaped snapshot collections.
            raise ConflictError("Game action storage requires operator recovery")
        # Require exact two-item wallet pairs before dictionary construction.
        if any(type(entry) is not list or len(entry) != 2 for entry in value["wallet_balances"]):
            # Prevent malformed or duplicate-hiding wallet snapshots.
            raise ConflictError("Game action storage requires operator recovery")
        # Require exact two-item state pairs before dictionary construction.
        if any(type(entry) is not list or len(entry) != 2 for entry in value["state_values"]):
            # Prevent malformed or duplicate-hiding state snapshots.
            raise ConflictError("Game action storage requires operator recovery")
        # Read ordered wallet identities before converting to a mapping.
        wallet_ids = tuple(entry[0] for entry in value["wallet_balances"])
        # Read ordered state identities before converting to a mapping.
        state_keys = tuple(entry[0] for entry in value["state_values"])
        # Require exact declared coverage so duplicates cannot disappear in dictionaries.
        if wallet_ids != resources.wallet_ids or state_keys != resources.state_keys:
            # Reject missing, duplicate, reordered, or undeclared durable values.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reconstruct through the contract's canonical snapshot freezer.
            return GameActionSnapshot.create(
                # Bind the exact durable resources.
                resources=resources,
                # Restore exact integer-cent wallet values.
                wallet_balances={entry[0]: entry[1] for entry in value["wallet_balances"]},
                # Restore and refreeze canonical state values.
                state_values={entry[0]: entry[1] for entry in value["state_values"]},
            )
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one immutable validated game-action plan.
    def _serialize_game_action_plan(self, plan: GameActionPlan) -> dict:
        # Return only the canonical outcome and declared writes.
        return {
            # Preserve exact signed integer-cent movements in planner order.
            "movements": [
                {
                    # Preserve the exact movement delta.
                    "amount_cents": movement.amount_cents,
                    # Preserve the bounded provider-neutral reason.
                    "reason": movement.reason,
                    # Preserve the declared wallet identity.
                    "wallet_id": movement.wallet_id,
                }
                for movement in plan.movements
            ],
            # Preserve the complete immutable outcome as ordinary canonical JSON.
            "outcome": self._plain_canonical(plan.outcome),
            # Preserve exact sorted state replacements.
            "state_updates": [[key, self._plain_canonical(value)] for key, value in plan.state_updates],
        }

    # Reconstruct one immutable game-action plan from private durable JSON.
    def _deserialize_game_action_plan(self, value: Any) -> GameActionPlan:
        # Require the exact durable plan field set.
        if type(value) is not dict or set(value) != {"movements", "outcome", "state_updates"}:
            # Reject malformed durable plan state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require ordinary JSON arrays for movements and state updates.
        if type(value["movements"]) is not list or type(value["state_updates"]) is not list:
            # Reject coercible or object-shaped plan collections.
            raise ConflictError("Game action storage requires operator recovery")
        # Require exact two-item state pairs before dictionary construction.
        if any(type(entry) is not list or len(entry) != 2 for entry in value["state_updates"]):
            # Prevent malformed or duplicate-hiding state updates.
            raise ConflictError("Game action storage requires operator recovery")
        # Extract state keys for canonical order and duplicate proof.
        update_keys = tuple(entry[0] for entry in value["state_updates"])
        # Require exact string keys in canonical sorted unique order.
        if any(type(key) is not str for key in update_keys) or update_keys != tuple(sorted(set(update_keys))):
            # Reject ambiguous durable state-update identity.
            raise ConflictError("Game action storage requires operator recovery")
        # Build validated movement contract objects.
        movements = []
        # Inspect every durable movement before plan construction.
        for movement in value["movements"]:
            # Require the exact movement field set.
            if type(movement) is not dict or set(movement) != {"amount_cents", "reason", "wallet_id"}:
                # Reject malformed durable movement state.
                raise ConflictError("Game action storage requires operator recovery")
            try:
                # Reconstruct through exact identity and integer-cent checks.
                movements.append(GameActionMovement(wallet_id=movement["wallet_id"], amount_cents=movement["amount_cents"], reason=movement["reason"]))
            # Normalize contract validation without exposing corrupt values.
            except ValidationError:
                # Preserve the original durable bytes for operator repair.
                raise ConflictError("Game action storage requires operator recovery") from None
        try:
            # Reconstruct the complete immutable plan through the canonical freezer.
            return GameActionPlan.create(
                # Restore the complete outcome.
                outcome=value["outcome"],
                # Restore exact movement order.
                movements=movements,
                # Restore exact canonical state replacements.
                state_updates={entry[0]: entry[1] for entry in value["state_updates"]},
            )
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one immutable committed receipt.
    def _serialize_game_action_receipt(self, receipt: GameActionReceipt) -> dict:
        # Return the complete provider-neutral receipt graph.
        return {
            # Preserve the exact action identity.
            "identity": self._serialize_game_action_identity(receipt.identity),
            # Preserve the exact immutable plan.
            "plan": self._serialize_game_action_plan(receipt.plan),
            # Preserve the complete bounded resource set.
            "resources": self._serialize_game_action_resources(receipt.resources),
            # Preserve the immutable planner snapshot.
            "snapshot_before": self._serialize_game_action_snapshot(receipt.snapshot_before),
            # Preserve the exact committed projection.
            "snapshot_after": self._serialize_game_action_snapshot(receipt.snapshot_after),
        }

    # Reconstruct and self-validate one immutable committed receipt.
    def _deserialize_game_action_receipt(self, value: Any) -> GameActionReceipt:
        # Require the exact durable receipt field set.
        if type(value) is not dict or set(value) != {"identity", "plan", "resources", "snapshot_after", "snapshot_before"}:
            # Reject malformed durable receipt state.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct the exact durable identity first.
        identity = self._deserialize_game_action_identity(value["identity"])
        # Reconstruct the complete bounded resource declaration.
        resources = self._deserialize_game_action_resources(value["resources"])
        # Reconstruct the immutable planner input.
        snapshot_before = self._deserialize_game_action_snapshot(value["snapshot_before"], resources)
        # Reconstruct the immutable validated plan.
        plan = self._deserialize_game_action_plan(value["plan"])
        # Reconstruct the immutable committed projection.
        snapshot_after = self._deserialize_game_action_snapshot(value["snapshot_after"], resources)
        try:
            # Revalidate pure projection consistency through the contract receipt.
            return GameActionReceipt(identity=identity, resources=resources, snapshot_before=snapshot_before, plan=plan, snapshot_after=snapshot_after)
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Return the empty private receipt registry shape.
    def _empty_game_action_receipts(self) -> dict:
        # Version the registry and retain immutable receipts by durable scope.
        return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "receipts": {}}

    # Read and fully validate the immutable receipt registry.
    def _read_game_action_receipts(self) -> tuple[dict, dict[str, GameActionReceipt]]:
        # Strictly decode the registry without repairing corrupt bytes.
        registry = self._read_game_action_json(self.game_action_receipts_path(), self._empty_game_action_receipts)
        # Require the exact versioned registry shape.
        if type(registry) is not dict or set(registry) != {"receipts", "schema_version"}:
            # Reject unknown durable fields or container types.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the exact non-coercible storage version.
        if type(registry["schema_version"]) is not int or registry["schema_version"] != _GAME_ACTION_STORAGE_VERSION:
            # Reject unknown durable schema behavior.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one ordinary mapping of durable receipt records.
        if type(registry["receipts"]) is not dict:
            # Reject arrays, scalars, or custom durable receipt shapes.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct every receipt so unrelated corrupt entries cannot remain hidden.
        receipts = {}
        # Inspect each durable scope and receipt pair.
        for scope_key, record in registry["receipts"].items():
            # Require an exact string registry key.
            if type(scope_key) is not str:
                # Reject coercible or ambiguous scope identities.
                raise ConflictError("Game action storage requires operator recovery")
            # Reconstruct and self-validate the complete immutable receipt.
            receipt = self._deserialize_game_action_receipt(record)
            # Require the registry key to match the receipt identity exactly.
            if scope_key != self._game_action_scope_key(receipt.identity):
                # Reject misplaced or shadowed committed identities.
                raise ConflictError("Game action storage requires operator recovery")
            # Retain the validated receipt for caller lookup.
            receipts[scope_key] = receipt
        # Return both the writable plain registry and immutable validated view.
        return registry, receipts

    # Return the empty provider-private action state registry shape.
    def _empty_game_action_states(self) -> dict:
        # Version the registry and retain route-free state resources by canonical key.
        return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "states": {}}

    # Read and validate every provider-private action state value.
    def _read_game_action_states(self) -> dict:
        # Strictly decode the registry without repairing corrupt bytes.
        registry = self._read_game_action_json(self.game_action_states_path(), self._empty_game_action_states)
        # Require the exact versioned registry shape.
        if type(registry) is not dict or set(registry) != {"schema_version", "states"}:
            # Reject unknown durable fields or container types.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the exact non-coercible storage version.
        if type(registry["schema_version"]) is not int or registry["schema_version"] != _GAME_ACTION_STORAGE_VERSION:
            # Reject unknown durable schema behavior.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one ordinary mapping of bounded canonical values.
        if type(registry["states"]) is not dict:
            # Reject arrays, scalars, or custom durable state shapes.
            raise ConflictError("Game action storage requires operator recovery")
        # Validate every key and value through a bounded one-state snapshot freezer.
        for state_key, state_value in registry["states"].items():
            # Require an exact portable resource key already admitted by the contract.
            try:
                # Build a one-resource declaration to validate the durable key.
                resources = GameActionResources(state_keys=(state_key,))
                # Freeze and bound the durable value through the snapshot contract.
                GameActionSnapshot.create(resources=resources, wallet_balances={}, state_values={state_key: state_value})
            # Normalize contract validation without exposing corrupt values.
            except ValidationError:
                # Preserve the original durable bytes for operator repair.
                raise ConflictError("Game action storage requires operator recovery") from None
        # Return the validated writable registry.
        return registry

    # Convert one compatible JSON wallet balance to exact integer cents.
    def _json_wallet_cents(self, value: Any) -> int:
        # Accept only the exact numeric JSON types used by existing player documents.
        if type(value) not in {int, float}:
            # Reject booleans, strings, and custom numeric objects.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Convert through decimal text so existing two-decimal JSON values remain exact.
            decimal_value = Decimal(str(value))
            # Multiply by the fixed fake-money precision.
            scaled = decimal_value * 100
        # Normalize invalid and non-finite numeric states.
        except Exception:
            # Preserve the original players document for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Require a finite exact cent value without rounding.
        if not scaled.is_finite() or scaled != scaled.to_integral_value():
            # Reject hidden sub-cent or non-finite wallet state.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Convert the exact integral decimal into a contract integer.
            balance_cents = int(scaled)
            # Reuse snapshot validation for range and nonnegative checks.
            GameActionSnapshot.create(resources=GameActionResources(wallet_ids=("wallet",)), wallet_balances={"wallet": balance_cents}, state_values={})
        # Normalize contract validation without exposing the value.
        except (ValueError, OverflowError, ValidationError):
            # Preserve the original players document for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Return the exact integer-cent balance.
        return balance_cents

    # Convert exact integer cents back to a compatible JSON numeric balance.
    def _json_wallet_value(self, cents: int) -> int | float:
        # Preserve whole-token values as exact JSON integers at every supported magnitude.
        if cents % 100 == 0:
            # Return the exact whole-token integer without binary conversion.
            return cents // 100
        # Convert ordinary fractional balances through the shipped numeric shape.
        candidate = cents / 100
        # Require the compatible JSON number to round-trip to the exact cents.
        if self._json_wallet_cents(candidate) != cents:
            # Reject a projection that current JSON numeric storage cannot represent exactly.
            raise ValidationError("Game action resulting wallet is not JSON-cent exact")
        # Return the verified compatible fractional JSON number.
        return candidate

    # Read the players document strictly for an action-owned wallet snapshot.
    def _read_game_action_players(self) -> dict:
        # Strictly decode players without the legacy corruption fallback.
        state = self._read_game_action_json(self.players_path(), lambda: {"schema_version": SCHEMA_VERSION, "players": []})
        # Require the public player document object and exact player array.
        if type(state) is not dict or type(state.get("players")) is not list:
            # Preserve malformed wallet bytes for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery")
        # Return the validated outer shape for bounded declared-wallet lookup.
        return state

    # Capture one immutable snapshot after durable-key lookup and recovery.
    def _capture_game_action_snapshot(self, resources: GameActionResources) -> GameActionSnapshot:
        # Load the current wallet document strictly under the global gate.
        players = self._read_game_action_players()
        # Build exact integer-cent balances for the declared wallets only.
        wallet_balances = {}
        # Resolve every bounded declared wallet.
        for wallet_id in resources.wallet_ids:
            # Find all exact player rows so duplicate durable identities fail closed.
            matches = [row for row in players["players"] if type(row) is dict and row.get("player_id") == wallet_id]
            # Reject a missing wallet through the established public error shape.
            if not matches:
                # Surface the same not-found boundary as ordinary wallet operations.
                raise NotFoundError(f"Player {wallet_id} was not found")
            # Reject duplicate durable wallet identities.
            if len(matches) != 1:
                # Preserve the ambiguous players document for operator recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Convert the compatible balance to exact integer cents.
            wallet_balances[wallet_id] = self._json_wallet_cents(matches[0].get("balance", 0))
        # Load the provider-private route-free game-state registry.
        state_registry = self._read_game_action_states()
        # Snapshot absent state resources as empty canonical objects.
        state_values = {state_key: state_registry["states"].get(state_key, {}) for state_key in resources.state_keys}
        # Freeze and validate the complete bounded provider snapshot.
        return GameActionSnapshot.create(resources=resources, wallet_balances=wallet_balances, state_values=state_values)

    # Build the fixed durable journal envelope for one stage.
    def _game_action_journal_record(
        self,
        *,
        stage: str,
        identity: GameActionIdentity,
        resources: GameActionResources,
        snapshot_before: GameActionSnapshot,
        receipt: GameActionReceipt | None,
    ) -> dict:
        # Return the exact versioned durable recovery fields.
        return {
            # Preserve the action identity reserved before planning.
            "identity": self._serialize_game_action_identity(identity),
            # Preserve the receipt only after a plan is durable.
            "receipt": None if receipt is None else self._serialize_game_action_receipt(receipt),
            # Preserve the complete declared resources.
            "resources": self._serialize_game_action_resources(resources),
            # Version the private journal format.
            "schema_version": _GAME_ACTION_STORAGE_VERSION,
            # Preserve the planner input even before an outcome exists.
            "snapshot_before": self._serialize_game_action_snapshot(snapshot_before),
            # Record the exact recoverable stage.
            "stage": stage,
        }

    # Read and validate the private action journal without modifying its bytes.
    def _read_game_action_journal(self) -> dict | None:
        # Return no journal when the private path is genuinely absent.
        if not self.game_action_journal_path().exists():
            # Report a clean recovery boundary.
            return None
        # Strictly decode the existing journal.
        record = self._read_game_action_json(self.game_action_journal_path(), dict)
        # Require the exact fixed journal field set.
        if type(record) is not dict or set(record) != {"identity", "receipt", "resources", "schema_version", "snapshot_before", "stage"}:
            # Reject truncated or unknown durable journal state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the exact non-coercible storage version.
        if type(record["schema_version"]) is not int or record["schema_version"] != _GAME_ACTION_STORAGE_VERSION:
            # Reject unknown durable schema behavior.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one exact known stage string.
        if type(record["stage"]) is not str or record["stage"] not in _GAME_ACTION_STAGES:
            # Reject unknown recovery behavior without changing bytes.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct identity and resources before accepting any stage.
        identity = self._deserialize_game_action_identity(record["identity"])
        # Reconstruct the exact bounded resource set.
        resources = self._deserialize_game_action_resources(record["resources"])
        # Reconstruct the planner snapshot against the declared resources.
        snapshot_before = self._deserialize_game_action_snapshot(record["snapshot_before"], resources)
        # Require prepared state to contain no outcome receipt.
        if record["stage"] == "prepared":
            # Reject a receipt hidden in a supposedly pre-planner journal.
            if record["receipt"] is not None:
                # Preserve the ambiguous journal for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Return the validated reconstructed prepared record.
            return {"identity": identity, "receipt": None, "resources": resources, "snapshot_before": snapshot_before, "stage": record["stage"]}
        # Require every post-planner stage to contain one exact receipt.
        if record["receipt"] is None:
            # Reject a recovery stage without its immutable outcome.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct and validate the complete immutable receipt.
        receipt = self._deserialize_game_action_receipt(record["receipt"])
        # Require the receipt to match every duplicated journal identity field.
        if receipt.identity != identity or receipt.resources != resources or receipt.snapshot_before != snapshot_before:
            # Reject internally divergent durable recovery state.
            raise ConflictError("Game action storage requires operator recovery")
        # Return the validated reconstructed journal record.
        return {"identity": identity, "receipt": receipt, "resources": resources, "snapshot_before": snapshot_before, "stage": record["stage"]}

    # Persist one reconstructed journal at a new recovery stage.
    def _write_game_action_journal_stage(self, record: dict, stage: str) -> None:
        # Require a reviewed stage chosen by provider code.
        if stage not in _GAME_ACTION_STAGES:
            # Treat internal misuse as a fixed provider-integrity failure.
            raise ConflictError("Game action storage is invalid")
        # Publish the complete immutable recovery envelope atomically.
        self._write_game_action_json(
            self.game_action_journal_path(),
            self._game_action_journal_record(
                # Preserve the reserved action identity.
                identity=record["identity"],
                # Preserve the immutable planned receipt when present.
                receipt=record["receipt"],
                # Preserve the complete bounded resource set.
                resources=record["resources"],
                # Preserve the exact planner input snapshot.
                snapshot_before=record["snapshot_before"],
                # Advance to the selected recoverable stage.
                stage=stage,
            ),
        )
        # Retain the new stage in the in-memory recovery record.
        record["stage"] = stage

    # Compare and project the exact wallet component of one committed receipt.
    def _apply_game_action_wallets(self, receipt: GameActionReceipt) -> None:
        # Skip the physical players document for a state-only zero-cost action.
        if not receipt.resources.wallet_ids:
            # Finish without creating an unrelated wallet file.
            return
        # Load the complete player document strictly under the global gate.
        players = self._read_game_action_players()
        # Build fast lookup while rejecting duplicate player identities.
        rows_by_id = {}
        # Inspect every compatible player row.
        for row in players["players"]:
            # Ignore malformed unrelated rows exactly as legacy lookups do.
            if type(row) is not dict or type(row.get("player_id")) is not str:
                # Continue until a declared wallet needs strict resolution.
                continue
            # Reject duplicates for any declared wallet.
            if row["player_id"] in rows_by_id and row["player_id"] in receipt.resources.wallet_ids:
                # Preserve ambiguous wallet bytes for operator recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Retain the latest unique row identity.
            rows_by_id[row["player_id"]] = row
        # Convert immutable receipt wallet pairs to bounded lookup maps.
        before = dict(receipt.snapshot_before.wallet_balances)
        # Convert the committed wallet projection to a lookup map.
        after = dict(receipt.snapshot_after.wallet_balances)
        # Collect each declared wallet's current exact balance.
        current = {}
        # Inspect every declared wallet in canonical order.
        for wallet_id in receipt.resources.wallet_ids:
            # Reject a missing committed wallet without guessing recovery state.
            if wallet_id not in rows_by_id:
                # Preserve the journal for operator recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Decode the exact current integer-cent balance.
            current[wallet_id] = self._json_wallet_cents(rows_by_id[wallet_id].get("balance", 0))
        # Return when the complete wallet projection is already committed.
        if current == after:
            # Preserve exact idempotent recovery.
            return
        # Require the complete original snapshot before applying the transition.
        if current != before:
            # Reject mixed or divergent wallet state.
            raise ConflictError("Game action wallet state requires operator recovery")
        # Replace every declared wallet with its exact committed balance.
        for wallet_id in receipt.resources.wallet_ids:
            # Publish only the receipt's deterministic after value.
            rows_by_id[wallet_id]["balance"] = self._json_wallet_value(after[wallet_id])
            # Mark the player row as updated for existing admin compatibility.
            rows_by_id[wallet_id]["updated_at"] = utc_now()
        # Persist the complete compatible player document atomically.
        self._save_players_document(players)

    # Compare and project the exact game-state component of one committed receipt.
    def _apply_game_action_states(self, receipt: GameActionReceipt) -> None:
        # Skip the private state registry for a wallet-only action.
        if not receipt.resources.state_keys:
            # Finish without creating an unrelated state file.
            return
        # Load the complete action-managed state registry strictly.
        registry = self._read_game_action_states()
        # Convert immutable receipt state pairs into lookup maps.
        before = dict(receipt.snapshot_before.state_values)
        # Convert the committed state projection into a lookup map.
        after = dict(receipt.snapshot_after.state_values)
        # Freeze current durable values through a bounded snapshot for exact comparison.
        current_snapshot = GameActionSnapshot.create(
            # Bind the exact state-only resource declaration.
            resources=GameActionResources(state_keys=receipt.resources.state_keys),
            # Supply no wallet values to the state-only snapshot.
            wallet_balances={},
            # Treat absent resources exactly as their original empty-object snapshot.
            state_values={key: registry["states"].get(key, {}) for key in receipt.resources.state_keys},
        )
        # Convert the current immutable state pairs into a lookup map.
        current = dict(current_snapshot.state_values)
        # Return when the complete state projection is already committed.
        if current == after:
            # Preserve exact idempotent recovery.
            return
        # Require the complete original snapshot before applying the transition.
        if current != before:
            # Reject mixed or divergent state instead of compensating.
            raise ConflictError("Game action state requires operator recovery")
        # Replace every declared state resource with its exact committed value.
        for state_key in receipt.resources.state_keys:
            # Publish plain canonical JSON without leaking immutable wrapper types.
            registry["states"][state_key] = self._plain_canonical(after[state_key])
        # Persist the complete provider-private state registry atomically.
        self._write_game_action_json(self.game_action_states_path(), registry)

    # Commit one immutable receipt or verify an already committed identical receipt.
    def _commit_game_action_receipt(self, receipt: GameActionReceipt) -> None:
        # Read and validate every durable receipt before adding a new one.
        registry, receipts = self._read_game_action_receipts()
        # Derive the unambiguous durable identity key.
        scope_key = self._game_action_scope_key(receipt.identity)
        # Inspect an existing receipt when a failure occurred after its publication.
        existing = receipts.get(scope_key)
        # Reject any immutable receipt divergence at the same scope.
        if existing is not None and existing != receipt:
            # Preserve both journal and receipt bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Return when the exact immutable receipt is already durable.
        if existing is not None:
            # Preserve idempotent recovery without rewriting registry bytes.
            return
        # Add the complete serialized receipt under its exact scope.
        registry["receipts"][scope_key] = self._serialize_game_action_receipt(receipt)
        # Atomically publish the updated immutable receipt registry.
        self._write_game_action_json(self.game_action_receipts_path(), registry)

    # Recover one prepared or planned journal before affected state is exposed.
    def _recover_game_action_journal_locked(self, *, inject_failures: bool = False) -> GameActionReceipt | None:
        # Read and validate the private journal without changing corrupt bytes.
        record = self._read_game_action_journal()
        # Return immediately when no action requires recovery.
        if record is None:
            # Report no recovered receipt.
            return None
        # Clear a pre-planner reservation because no outcome or projection exists.
        if record["stage"] == "prepared":
            # Remove the no-op reservation before exposing wallet or state.
            self._remove_game_action_journal()
            # Report that no committed receipt was recovered.
            return None
        # Read the already validated immutable planned receipt.
        receipt = record["receipt"]
        # Project every declared wallet exactly once.
        self._apply_game_action_wallets(receipt)
        # Inject a process-stop boundary after wallet publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("wallet_applied")
        # Checkpoint the wallet projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "wallet_applied")
        # Project every declared state resource exactly once.
        self._apply_game_action_states(receipt)
        # Inject a process-stop boundary after state publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("state_applied")
        # Checkpoint the state projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "state_applied")
        # Commit or verify the immutable receipt registry.
        self._commit_game_action_receipt(receipt)
        # Inject a process-stop boundary after receipt publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("receipt_committed")
        # Checkpoint that every committed projection is now recoverable from its receipt.
        self._write_game_action_journal_stage(record, "receipt_committed")
        # Inject a process-stop boundary immediately before journal cleanup.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("cleanup")
        # Remove the journal only after the immutable receipt is durable.
        self._remove_game_action_journal()
        # Return the exact recovered or newly committed receipt.
        return receipt

    # Recover legacy ledger projection and game-action state in one fixed order.
    def _recover_all_json_actions_locked(self) -> None:
        # Complete any shipped logical ledger commit before snapshotting its wallet.
        self._recover_committed_actions()
        # Complete or clear the provider-private game-action journal next.
        self._recover_game_action_journal_locked()

    # Execute or replay one route-free provider-owned JSON game action.
    def execute_game_action_once(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
        planner: Callable[[GameActionSnapshot], GameActionPlan],
    ) -> tuple[GameActionReceipt, bool]:
        # Validate exact contract types before any durable lookup.
        validate_execution_request(identity=identity, resources=resources, planner=planner)
        # Reject recursive provider mutation from inside another planner.
        self._reject_planner_mutation()
        # Serialize same-process callers through the provider instance.
        with self.lock:
            # Serialize every affected JSON projection across instances and processes.
            with self._json_global_gate():
                # Complete any shipped logical ledger commit before reading wallets.
                self._recover_committed_actions()
                # Inspect an existing private journal before action-key lookup.
                pending = self._read_game_action_journal()
                # Preserve mismatch-before-mutation semantics for every same-scope journal stage.
                if pending is not None and pending["identity"].scope_key == identity.scope_key:
                    # Reject changed identity or resources before recovery projects any state.
                    if pending["identity"] != identity or pending["resources"] != resources:
                        # Never invoke the planner for conflicting durable key reuse.
                        raise ConflictError("Game action key conflicts with durable semantics")
                # Recover or clear every valid pending stage before receipt lookup.
                self._recover_game_action_journal_locked()
                # Load and validate the complete immutable receipt registry.
                _registry, receipts = self._read_game_action_receipts()
                # Derive the caller's unambiguous durable scope key.
                scope_key = self._game_action_scope_key(identity)
                # Inspect an earlier committed receipt before any resource snapshot.
                existing = receipts.get(scope_key)
                # Resolve exact replay or conflict without planner/RNG.
                if existing is not None:
                    # Reject fingerprint or resource mismatch before snapshot creation.
                    if existing.identity != identity or existing.resources != resources:
                        # Preserve the committed receipt and fixed conflict semantics.
                        raise ConflictError("Game action key conflicts with committed semantics")
                    # Return the original immutable receipt as a replay.
                    return existing, True
                # Capture exact declared wallet and game state only after durable lookup.
                snapshot_before = self._capture_game_action_snapshot(resources)
                # Build the pre-planner durable reservation.
                prepared = {
                    # Preserve the exact action identity.
                    "identity": identity,
                    # Record that no immutable outcome exists yet.
                    "receipt": None,
                    # Preserve the complete bounded resources.
                    "resources": resources,
                    # Preserve the exact planner input.
                    "snapshot_before": snapshot_before,
                    # Mark the pre-planner recovery stage.
                    "stage": "prepared",
                }
                # Durably publish the reservation before invoking planner/RNG.
                self._write_game_action_journal_stage(prepared, "prepared")
                # Inject a process-stop boundary before planner invocation.
                self._game_action_checkpoint("prepared")
                try:
                    # Mark provider mutation forbidden during the synchronous planner.
                    with self._planner_boundary():
                        # Invoke the new-action planner exactly once.
                        plan = planner(snapshot_before)
                    # Require the exact immutable contract plan type.
                    if type(plan) is not GameActionPlan:
                        # Reject arbitrary plan-like values before any projection.
                        raise ValidationError("Game action planner returned an invalid plan")
                    # Compute and validate the exact deterministic committed snapshot.
                    snapshot_after = apply_plan_to_snapshot(snapshot_before, plan)
                    # Construct the complete immutable receipt before publication.
                    receipt = GameActionReceipt(
                        # Bind the exact action identity.
                        identity=identity,
                        # Bind the complete declared resources.
                        resources=resources,
                        # Preserve the immutable planner input.
                        snapshot_before=snapshot_before,
                        # Preserve the complete validated plan.
                        plan=plan,
                        # Preserve the exact deterministic after snapshot.
                        snapshot_after=snapshot_after,
                    )
                # Clear a pre-planner reservation after any planner or validation failure.
                except BaseException:
                    # Remove only the no-mutation prepared journal.
                    self._remove_game_action_journal()
                    # Preserve the caller's original planner or contract exception.
                    raise
                # Attach the immutable receipt to the durable recovery record.
                prepared["receipt"] = receipt
                # Publish the complete planned outcome before any wallet or state write.
                self._write_game_action_journal_stage(prepared, "planned")
                # Inject a process-stop boundary after outcome durability.
                self._game_action_checkpoint("planned")
                # Apply and checkpoint every projection through restart-safe recovery.
                committed = self._recover_game_action_journal_locked(inject_failures=True)
                # Require the recovery path to return the just-planned immutable receipt.
                if committed != receipt:
                    # Reject impossible provider divergence without a public result.
                    raise ConflictError("Game action storage requires operator recovery")
                # Return the newly committed receipt with replay false.
                return receipt, False

    # Append a JSONL ledger event to the local ledger file.
    def _append_jsonl(self, path: Path, event: dict) -> None:
        # Reject direct provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Ensure local directories exist before writing.
        self.ensure_ready()
        # Guard append writes with the provider lock.
        with self.lock:
            # Create the target parent directory before appending.
            path.parent.mkdir(parents=True, exist_ok=True)
            # Open the file in append mode so prior ledger rows remain intact.
            with path.open("a", encoding="utf-8") as handle:
                # Write one sorted JSON object per line to preserve current format.
                handle.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")

    # Load players without acquiring another operating-system wallet lock.
    def _load_players_document(self, default_factory: Callable[[], dict]) -> dict:
        # Read the players document or build defaults when absent.
        state = self._read_json(self.players_path(), default_factory)
        # Replace invalid payloads with the default player document.
        if not isinstance(state, dict) or "players" not in state:
            # Rebuild defaults when the stored shape is unusable.
            state = default_factory()
        # Return the player document expected by existing callers.
        return state

    # Save players without acquiring another gate or invoking recovery.
    def _save_players_document(self, state: dict) -> None:
        # Copy the state so callers do not observe schema mutation side effects.
        saved_state = dict(state)
        # Preserve the current schema version on every saved player document.
        saved_state["schema_version"] = SCHEMA_VERSION
        # Write the normalized player document to disk.
        self._write_json(self.players_path(), saved_state)

    # Load players after recovering any committed action projection from a prior process.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Guard recovery and the player read from concurrent local threads.
        with self.lock:
            # Guard recovery and the player read from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before exposing players.
                self._recover_all_json_actions_locked()
                # Return the compatible player document after recovery.
                return self._load_players_document(default_factory)

    # Save players to the existing JSON document shape.
    def save_players(self, state: dict) -> None:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard recovery and the wallet write from concurrent local threads.
        with self.lock:
            # Serialize with every action-owned projection across processes.
            with self._json_global_gate():
                # Complete every recoverable action before a later wallet overwrite.
                self._recover_all_json_actions_locked()
                # Persist the compatible player document inside the held gate.
                self._save_players_document(state)

    # Update one player with the existing callback semantics.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard read-modify-write with the provider lock.
        with self.lock:
            # Guard the read-modify-write operation from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before applying a later update.
                self._recover_all_json_actions_locked()
                # Load the current players document using an empty fallback.
                state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Iterate through players to find the requested row.
                for player in state["players"]:
                    # Branch when this row matches the requested player ID.
                    if player["player_id"] == player_id:
                        # Let the caller mutate the player copy in place.
                        updater(player)
                        # Normalize balances to two decimal places.
                        player["balance"] = round(float(player.get("balance", 0)), 2)
                        # Stamp the update time for downstream admin views.
                        player["updated_at"] = utc_now()
                        # Persist the modified player document.
                        self._save_players_document(state)
                        # Return the updated player row to the caller.
                        return player
        # Raise a consistent not-found error when no player matched.
        raise NotFoundError(f"Player {player_id} was not found")

    # Create one deterministic player under the same cross-process wallet lock used by updates.
    def ensure_player(self, player: dict) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard deterministic provisioning from concurrent threads.
        with self.lock:
            # Guard deterministic provisioning from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before changing players.
                self._recover_all_json_actions_locked()
                # Load the current player collection without seeding unrelated defaults.
                state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Return an existing compatible row for an idempotent recovery attempt.
                for existing in state["players"]:
                    # Match only the deterministic invited-player identifier.
                    if existing.get("player_id") == player.get("player_id"):
                        # Reject an identifier collision with different ownership semantics.
                        if existing.get("type") != player.get("type"):
                            # Preserve the existing row and fail the provisioning saga closed.
                            raise ConflictError("Player provisioning identity conflicts with existing state")
                        # Return the already provisioned player without resetting balance or timestamps.
                        return existing
                # Append a detached copy so caller mutation cannot alter persisted state after return.
                state["players"].append(dict(player))
                # Persist the complete deterministic player document while the process lock remains held.
                self._save_players_document(state)
                # Return the newly committed compatible row.
                return dict(player)

    # Return the empty committed-action registry shape used by fresh JSON stores.
    def _empty_action_registry(self) -> dict:
        # Return a versioned registry with a monotonic recovery order.
        return {"schema_version": 1, "next_sequence": 1, "actions": {}}

    # Build a deterministic registry key from the canonical storage identity.
    def _action_identity(self, player_id: str, scope: str, action_key: str) -> str:
        # Serialize identity fragments so delimiters inside caller keys remain unambiguous.
        return json.dumps([player_id, scope, action_key], separators=(",", ":"))

    # Decode one physical JSONL line using the historical malformed-line skipping semantics. (issue #412)
    def _decode_ledger_line(self, line: str) -> dict | None:
        # Start protected decoding so one malformed historical row does not block recovery.
        try:
            # Decode the candidate ledger row.
            event = json.loads(line)
        # Skip malformed rows consistently with the public recent-ledger reader.
        except Exception:
            # Report no row so callers continue to later append-only rows.
            return None
        # Keep dictionary rows that expose a ledger identity.
        if isinstance(event, dict) and event.get("ledger_id"):
            # Return the valid decoded event.
            return event
        # Report no row for identity-free payloads.
        return None

    # Read valid ledger rows in their append order for recovery checks.
    def _ledger_rows(self) -> list[dict]:
        # Stat the append-only file once so unchanged content skips every re-parse. (issue #412)
        try:
            # Read the current size and modification identity of the ledger file.
            stat = os.stat(self.ledger_path())
        # Treat a missing file as an empty ledger exactly like the previous implementation.
        except OSError:
            # Drop cache state left behind by a removed or reset ledger file. (issue #412)
            self._drop_ledger_cache()
            # Avoid opening an absent ledger file.
            return []
        # Serve cached rows when the file identity matches the last parse. (issue #412)
        if stat.st_size == self._ledger_cache_offset and stat.st_mtime_ns == self._ledger_cache_mtime_ns:
            # Return the cached append-order view without touching file contents.
            return self._ledger_cache_rows
        # Reload from the start after truncation or an equal-size rewrite. (issue #412)
        if stat.st_size <= self._ledger_cache_offset:
            # Drop the cache because append-only growth can no longer explain the observed file.
            self._drop_ledger_cache()
        # Read only the bytes appended after the cached offset. (issue #412)
        with self.ledger_path().open("rb") as handle:
            # Position the reader at the first unparsed byte.
            handle.seek(self._ledger_cache_offset)
            # Read exactly the appended region observed by the stat call.
            appended = handle.read(stat.st_size - self._ledger_cache_offset)
        # Split at the final newline so an unterminated trailing line is never cached. (issue #412)
        boundary = appended.rfind(b"\n") + 1
        # Decode complete lines with the same replacement policy as the previous full-file read.
        for line in appended[:boundary].decode("utf-8", errors="replace").splitlines():
            # Decode the candidate line with the historical malformed-line skipping.
            event = self._decode_ledger_line(line)
            # Keep dictionary rows that expose a ledger identity.
            if event is not None:
                # Add the valid event to the cached recovery view.
                self._ledger_cache_rows.append(event)
                # Index the same row reference by player for O(tail) filtered reads.
                self._ledger_cache_by_player.setdefault(event.get("player_id"), []).append(event)
        # Advance the cache offset past every fully terminated parsed line. (issue #412)
        self._ledger_cache_offset += boundary
        # Remember the file identity that produced the cached content. (issue #412)
        self._ledger_cache_mtime_ns = stat.st_mtime_ns
        # Re-decode unterminated trailing bytes each call without caching them. (issue #412)
        self._ledger_cache_tail_rows = [row for row in (self._decode_ledger_line(line) for line in appended[boundary:].decode("utf-8", errors="replace").splitlines()) if row is not None]
        # Return cached rows plus any uncacheable trailing rows in commit order.
        return self._ledger_cache_rows + self._ledger_cache_tail_rows if self._ledger_cache_tail_rows else self._ledger_cache_rows

    # Project one durably committed action into players.json and ledger.jsonl.
    def _project_committed_action(self, event: dict) -> None:
        # Read current append-only rows so recovery never duplicates a ledger event.
        ledger_ids = {row["ledger_id"] for row in self._ledger_rows()}
        # Stop when both balance and ledger projection already completed earlier.
        if event["ledger_id"] in ledger_ids:
            # Treat the ledger row as proof that this action was fully projected.
            return
        # Load the current player document without invoking another process lock.
        state = self._read_json(self.players_path(), lambda: {"schema_version": SCHEMA_VERSION, "players": []})
        # Find the wallet owned by the committed action.
        player = next((row for row in state.get("players", []) if row.get("player_id") == event["player_id"]), None)
        # Fail closed when recovery cannot locate the committed wallet.
        if player is None:
            # Preserve the journal for operator recovery instead of discarding money state.
            raise ConflictError("Committed ledger action references a missing player", {"ledger_id": event["ledger_id"], "player_id": event["player_id"]})
        # Normalize the currently projected fake-money balance.
        current_balance = round(float(player.get("balance", 0)), 2)
        # Apply the committed balance transition when projection stopped before players.json.
        if current_balance == round(float(event["balance_before"]), 2):
            # Move the wallet to the committed post-transaction balance exactly once.
            player["balance"] = round(float(event["balance_after"]), 2)
            # Stamp recovery as a player update for downstream admin views.
            player["updated_at"] = utc_now()
            # Persist the recovered wallet state before appending the missing ledger row.
            self._save_players_document(state)
        # Accept a balance that already reached the committed after-state before a lost response.
        elif current_balance != round(float(event["balance_after"]), 2):
            # Reject divergent state because guessing could duplicate or erase later money actions.
            raise ConflictError("Committed ledger action cannot be recovered from divergent wallet state", {"ledger_id": event["ledger_id"], "balance": current_balance})
        # Append the original committed event after the wallet transition is durable.
        self._append_jsonl(self.ledger_path(), event)

    # Cache one just-written registry object under its durable file identity. (issue #412)
    def _store_actions_cache(self, registry: dict) -> None:
        # Start protected stat logic so cache upkeep never fails a completed write.
        try:
            # Read the identity of the file that now contains exactly this registry.
            stat = os.stat(self.ledger_actions_path())
        # Fail toward re-reading on the next call instead of caching unverified state.
        except OSError:
            # Drop the cache so the next reader consults the file directly.
            self._drop_actions_cache()
            # Stop without caching.
            return
        # Store the registry reference for later stat-matched reuse.
        self._actions_cache_registry = registry
        # Store the file identity used to validate later cache hits.
        self._actions_cache_stat = (stat.st_size, stat.st_mtime_ns)

    # Read the committed-action registry through a (size, mtime_ns) stat-guarded cache. (issue #412)
    def _read_actions_registry(self) -> Any:
        # Stat the registry file so unchanged content skips a full JSON re-parse.
        try:
            # Read the current size and modification identity of the registry file.
            stat = os.stat(self.ledger_actions_path())
        # Treat a missing registry exactly like the previous per-call default read.
        except OSError:
            # Drop any cache tied to a removed registry file.
            self._drop_actions_cache()
            # Return a fresh mutable empty registry as the historical default factory did.
            return self._empty_action_registry()
        # Serve the cached parsed registry when the file identity is unchanged. (issue #412)
        if self._actions_cache_registry is not None and self._actions_cache_stat == (stat.st_size, stat.st_mtime_ns):
            # Return the cached registry object without re-reading the file.
            return self._actions_cache_registry
        # Build one call-local sentinel that only the corruption fallback can return.
        sentinel = object()
        # Re-read through the historical corruption-tolerant JSON reader.
        parsed = self._read_json(self.ledger_actions_path(), lambda: sentinel)
        # Preserve the historical corrupt-file behavior of backing up and returning a fresh default.
        if parsed is sentinel:
            # Never cache a corruption fallback so every later call re-checks the file.
            self._drop_actions_cache()
            # Return a fresh mutable empty registry exactly like the previous implementation.
            return self._empty_action_registry()
        # Cache the parsed payload under the pre-read identity so later writes force a reload.
        self._actions_cache_registry = parsed
        # Store the file identity used to validate later cache hits.
        self._actions_cache_stat = (stat.st_size, stat.st_mtime_ns)
        # Return the freshly parsed registry payload.
        return parsed

    # Recover every journaled action before allowing a later wallet mutation.
    def _recover_committed_actions(self, registry: dict | None = None) -> dict:
        # Load the durable registry through the stat-guarded cache when the caller did not pass one. (issue #412)
        registry = registry or self._read_actions_registry()
        # Normalize malformed registry shapes to a safe empty action map.
        actions = registry.get("actions", {}) if isinstance(registry, dict) else {}
        # Track whether recovery completed any previously pending projections.
        recovered = False
        # Replay committed transitions in their original monotonic order.
        for record in sorted(actions.values(), key=lambda item: int(item.get("sequence", 0))):
            # Skip actions whose compatible files were already projected and acknowledged.
            if record.get("projected") is True:
                # Continue without rescanning the append-only ledger for settled actions.
                continue
            # Invalidate the registry cache before mutation so a failed projection cannot poison later reads. (issue #412)
            self._drop_actions_cache()
            # Project the recorded immutable event exactly once.
            self._project_committed_action(record["event"])
            # Mark projection complete only after both compatible files are durable.
            record["projected"] = True
            # Remember that the updated journal must be persisted before releasing the lock.
            recovered = True
        # Persist recovered projection markers so steady-state wallet reads remain constant-time.
        if recovered:
            # Atomically checkpoint the action journal after successful projection.
            self._write_json(self.ledger_actions_path(), registry)
            # Re-cache the checkpointed registry under its new durable file identity. (issue #412)
            self._store_actions_cache(registry)
        # Return the registry so the transaction can reuse its in-memory view.
        return registry

    # Execute a ledger transaction after both thread and process locks are held.
    def _transact_ledger_locked(self, player_id: str, amount: float, transaction_type: str, game: str | None, round_id: str | None, details: dict | None) -> dict:
        # Load the player document using an empty fallback for clear not-found errors.
        state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
        # Find the requested player in the document.
        player = next((row for row in state["players"] if row["player_id"] == player_id), None)
        # Raise a consistent not-found error when no player exists.
        if player is None:
            # Raise the same player lookup error shape used by players.get_player.
            raise NotFoundError(f"Player {player_id} was not found")
        # Capture the balance before the proposed mutation.
        before = round(float(player.get("balance", 0)), 2)
        # Compute the balance after the proposed mutation.
        after = round(before + amount, 2)
        # Reject transactions that would overdraw the fake-money wallet.
        if after < -1e-9:
            # Raise the existing insufficient-funds error with ledger details.
            raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
        # Store the new balance on the player row.
        player["balance"] = after
        # Stamp the player update time alongside the balance mutation.
        player["updated_at"] = utc_now()
        # Build the ledger event before persistence so both stores agree.
        event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, details)
        # Persist the player document before appending the ledger row under the same lock.
        self._save_players_document(state)
        # Append the ledger event while the compound transaction lock is still held.
        self._append_jsonl(self.ledger_path(), event)
        # Return the committed ledger event to the caller.
        return event

    # Execute a ledger transaction and balance update under thread and process locks.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = round(float(amount), 2)
        # Reject zero-value ledger rows before touching player state.
        if amount == 0:
            # Raise a validation error consistent with the previous ledger module.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Guard the wallet transaction from concurrent threads in this process.
        with self.lock:
            # Guard the wallet transaction from independent application processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before applying a later mutation.
                self._recover_all_json_actions_locked()
                # Execute the existing compatible transaction inside both locks.
                return self._transact_ledger_locked(player_id, amount, transaction_type, game, round_id, details)

    # Execute or replay one storage-enforced JSON ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = round(float(amount), 2)
        # Reject zero-value ledger rows before touching durable action state.
        if amount == 0:
            # Raise the standard ledger validation error.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Normalize the caller-owned identity fragment before storage lookup.
        action_key = _normalize_action_key(action_key)
        # Derive the game-or-core namespace used by both storage providers.
        scope = _action_scope(game)
        # Derive the semantic digest that distinguishes replay from changed reuse.
        fingerprint = _action_fingerprint(amount, transaction_type, game, round_id, details)
        # Build the unambiguous JSON registry key.
        identity = self._action_identity(player_id, scope, action_key)
        # Guard the action from concurrent threads in this process.
        with self.lock:
            # Guard the action from independent application processes.
            with self._ledger_process_lock():
                # Complete every legacy and provider-private wallet action in fixed order.
                self._recover_all_json_actions_locked()
                # Reload the settled legacy registry for this transaction's identity lookup.
                registry = self._recover_committed_actions()
                # Read an earlier commit for this identity when a retry arrives.
                existing = registry.get("actions", {}).get(identity)
                # Return the original event for an exact semantic replay.
                if existing is not None:
                    # Reject changed reuse before returning any prior money result.
                    _validate_action_replay(existing["event"], fingerprint, action_key)
                    # Return the original event with an explicit replay marker.
                    return existing["event"], True
                # Enrich details with storage-owned audit metadata only after hashing caller semantics.
                committed_details = _action_details(details, action_key, fingerprint)
                # Build the candidate wallet transition without persisting it yet.
                state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Find the wallet that owns this action identity.
                player = next((row for row in state["players"] if row["player_id"] == player_id), None)
                # Reject unknown players before writing the action journal.
                if player is None:
                    # Raise the standard player lookup error.
                    raise NotFoundError(f"Player {player_id} was not found")
                # Capture the balance before the proposed mutation.
                before = round(float(player.get("balance", 0)), 2)
                # Compute the balance after the proposed mutation.
                after = round(before + amount, 2)
                # Reject actions that would overdraw the fake-money wallet.
                if after < -1e-9:
                    # Raise the standard insufficient-funds error before committing the identity.
                    raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
                # Build the immutable event returned by every later replay.
                event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, committed_details)
                # Allocate the next monotonic recovery sequence.
                sequence = int(registry.get("next_sequence", 1))
                # Invalidate the registry cache before mutation so an interrupted commit cannot poison later reads. (issue #412)
                self._drop_actions_cache()
                # Store the action record as the logical commit before projecting balance and JSONL.
                registry.setdefault("actions", {})[identity] = {"sequence": sequence, "player_id": player_id, "action_scope": scope, "action_key": action_key, "action_fingerprint": fingerprint, "projected": False, "event": event}
                # Advance the sequence for the next distinct action.
                registry["next_sequence"] = sequence + 1
                # Persist the logical commit atomically before any wallet projection.
                self._write_json(self.ledger_actions_path(), registry)
                # Project the committed transition into the compatible player and ledger files.
                self._project_committed_action(event)
                # Mark the compatible-file projection complete after both writes succeed.
                registry["actions"][identity]["projected"] = True
                # Checkpoint the projection marker so later reads skip settled journal entries.
                self._write_json(self.ledger_actions_path(), registry)
                # Re-cache the settled registry under its final durable file identity. (issue #412)
                self._store_actions_cache(registry)
                # Return the newly committed event with a non-replay marker.
                return event, False

    # Read recent ledger events from the local JSONL file.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Guard recovery and the ledger read from concurrent local threads.
        with self.lock:
            # Guard recovery and the ledger read from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before exposing ledger state.
                self._recover_all_json_actions_locked()
                # Read all valid append-only rows after refreshing the incremental cache. (issue #412)
                rows = self._ledger_rows()
                # Apply the optional player filter used by player and Admin history views.
                if player_id is not None:
                    # Filter the combined view directly while rare unterminated trailing rows exist. (issue #412)
                    if self._ledger_cache_tail_rows:
                        # Keep only events owned by the requested player.
                        rows = [event for event in rows if event.get("player_id") == player_id]
                    # Use the per-player index for the ordinary fully-cached case. (issue #412)
                    else:
                        # Keep only events owned by the requested player without scanning other wallets.
                        rows = self._ledger_cache_by_player.get(player_id, [])
                # Return the requested tail of matching rows.
                return rows[-limit:]

    # Append a CSV history row using the existing local file format.
    def append_history(self, event: dict) -> None:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Import csv only for the JSON provider's CSV compatibility path.
        import csv
        # Serialize history mutation with reset and every provider operation.
        with self.lock:
            # Hold the stable and legacy process gates across the complete append.
            with self._json_global_gate():
                # Complete every recoverable action before exposing a later history row.
                self._recover_all_json_actions_locked()
                # Store whether the history file already exists before opening it.
                exists = self.history_path().exists()
                # Open the CSV file in append mode using the existing newline settings.
                with self.history_path().open("a", newline="", encoding="utf-8") as handle:
                    # Build a DictWriter with the canonical history columns.
                    writer = csv.DictWriter(handle, fieldnames=HISTORY_FIELDS)
                    # Write a header for a fresh history file.
                    if not exists:
                        # Persist the CSV header before the first data row.
                        writer.writeheader()
                    # Append the normalized history event.
                    writer.writerow(event)

    # Read recent history rows from the local CSV file.
    def recent_history(self, limit: int = 100, game: str | None = None) -> list[dict]:
        # Import csv only for the JSON provider's CSV compatibility path.
        import csv
        # Serialize history visibility with reset and every provider operation.
        with self.lock:
            # Hold the stable and legacy process gates across the complete read.
            with self._json_global_gate():
                # Complete every recoverable action before exposing history.
                self._recover_all_json_actions_locked()
                # Return no history for fresh local runs.
                if not self.history_path().exists():
                    # Return an empty result set when there is no local CSV yet.
                    return []
                # Open the CSV file using the existing newline settings.
                with self.history_path().open("r", newline="", encoding="utf-8") as handle:
                    # Decode every history row into dictionaries.
                    rows = list(csv.DictReader(handle))
                # Apply optional game filtering for admin and casino history endpoints.
                if game:
                    # Keep only rows for the requested game.
                    rows = [row for row in rows if row.get("game") == game]
                # Return the requested tail of matching rows.
                return rows[-limit:]

    # Read a named JSON document from local storage.
    def read_document(self, key: str, default: Any) -> Any:
        # Guard recovery and document reads from concurrent local threads.
        with self.lock:
            # Bridge the provider-wide and shipped per-document process locks.
            with self._document_process_lock(key):
                # Complete every recoverable action before exposing documents.
                self._recover_all_json_actions_locked()
                # Reuse the local JSON helper for settings documents.
                return self._read_json(self.document_path(key), default)

    # Read one local security document strictly without fallback backups or normalization.
    def read_document_strict(self, key: str, default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Guard recovery and strict document reads from concurrent local threads.
        with self.lock:
            # Bridge the provider-wide and shipped per-document process locks.
            with self._document_process_lock(key):
                # Complete every recoverable action before exposing documents.
                self._recover_all_json_actions_locked()
                # Resolve the exact durable document path once under both locks.
                path = self.document_path(key)
                # Read actual bytes so only FileNotFoundError can select the reviewed default.
                try:
                    # Read the exact stored payload without a separate existence check.
                    encoded = path.read_bytes()
                # Treat only a truly absent path as the missing-document compatibility case.
                except FileNotFoundError:
                    # Preserve lazy default-factory behavior without creating the document.
                    value = default() if callable(default) else default
                # Collapse every other filesystem failure without leaking its path or detail.
                except OSError:
                    # Refuse with one fixed value-free operator-recovery boundary.
                    raise RuntimeError("Stored document requires operator recovery") from None
                # Decode bytes that were read successfully without invoking backup behavior.
                else:
                    # Start protected decoding while preserving the original bytes on failure.
                    try:
                        # Decode UTF-8 JSON with exact duplicate-key rejection.
                        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=self._unique_json_object)
                    # Collapse malformed text, duplicate-key, deep, and numeric-limit failures.
                    except (UnicodeError, ValueError, RecursionError):
                        # Refuse with one fixed value-free operator-recovery boundary.
                        raise RuntimeError("Stored document requires operator recovery") from None
                # Require any caller-owned security shape without reflecting its contents.
                return _validated_strict_document(value, validator)

    # Write a named JSON document to local storage.
    def write_document(self, key: str, data: Any) -> None:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard recovery and document writes from concurrent local threads.
        with self.lock:
            # Bridge the provider-wide and shipped per-document process locks.
            with self._document_process_lock(key):
                # Complete every recoverable action before overwriting a document.
                self._recover_all_json_actions_locked()
                # Reuse the local JSON helper for settings documents.
                self._write_json(self.document_path(key), data)

    # Mutate one local document under the provider lock for direct provider callers.
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Serialize the direct provider read-modify-write inside this process.
        with self.lock:
            # Hold the same sidecar lock across every provider instance and process.
            with self._document_process_lock(key):
                # Complete every recoverable action before document mutation.
                self._recover_all_json_actions_locked()
                # Resolve the exact document path once under the cross-process lock.
                path = self.document_path(key)
                # Use the no-side-effect decoder only for a validator-bound security transaction.
                if validator is not None:
                    # Read actual text so only FileNotFoundError can select the default.
                    try:
                        # Read the exact current text while both process locks remain held.
                        encoded = path.read_bytes()
                    # Treat only a truly absent document as the reviewed initial state.
                    except FileNotFoundError:
                        # Preserve lazy default-factory behavior for a new document.
                        current = default() if callable(default) else default
                    # Collapse every other filesystem failure without path disclosure.
                    except OSError:
                        # Abort without a backup, temp, normalization, or mutator invocation.
                        raise RuntimeError("Stored document requires operator recovery") from None
                    # Decode an existing security document strictly under the update lock.
                    else:
                        # Start protected parsing while preserving the exact source bytes.
                        try:
                            # Reject invalid UTF-8, invalid JSON, and duplicate object keys.
                            current = json.loads(encoded.decode("utf-8"), object_pairs_hook=self._unique_json_object)
                        # Collapse every bounded parser failure into the fixed recovery boundary.
                        except (UnicodeError, ValueError, RecursionError):
                            # Abort without a backup, temp, normalization, or mutator invocation.
                            raise RuntimeError("Stored document requires operator recovery") from None
                # Preserve the legacy ordinary update decoder and corruption-backup semantics.
                elif not path.exists():
                    # Preserve lazy default-factory behavior for ordinary new documents.
                    current = default() if callable(default) else default
                # Parse an existing ordinary document through its unchanged last-key-wins decoder.
                else:
                    # Start protected legacy parsing.
                    try:
                        # Decode with the established ordinary document behavior.
                        current = json.loads(path.read_text(encoding="utf-8"))
                    # Preserve malformed state through the established backup path.
                    except json.JSONDecodeError:
                        # Copy the malformed payload for explicit recovery without replacing the source.
                        backup = path.with_suffix(path.suffix + f".corrupt-{int(time.time())}")
                        # Preserve a recoverable snapshot before aborting the mutation.
                        shutil.copy2(path, backup)
                        # Abort without invoking the mutator or writing a normalized document.
                        raise RuntimeError("Stored document requires operator recovery") from None
                # Validate the current security document while the complete transaction remains held.
                current = _validated_strict_document(current, validator)
                # Apply the caller-owned mutation while both process and thread locks are held.
                updated = mutator(current)
                # Atomically replace the complete JSON document only after successful validation and mutation.
                self._write_json(path, updated)
                # Return the exact value that was persisted.
                return updated


# Define the canonical history fields shared by JSON and MySQL providers.
HISTORY_FIELDS = [
    # Store the event timestamp column.
    "timestamp",
    # Store the source game column.
    "game",
    # Store the round or session ID column.
    "round_id",
    # Store the owning player ID column.
    "player_id",
    # Store the wager type column.
    "bet_type",
    # Store the human-readable wager label column.
    "bet_label",
    # Store the wager amount column.
    "amount",
    # Store the outcome column.
    "outcome",
    # Store the payout column.
    "payout",
    # Store the balance after settlement column.
    "balance_after",
    # Store JSON details as a string for CSV compatibility.
    "details_json",
    # Store the app schema version for future migrations.
    "schema_version",
]


# Define the MySQLStorageProvider for configured multi-user persistence.
class MySQLStorageProvider(StorageProvider):
    # Store the provider name used by diagnostics and tests.
    name = "mysql"

    # Initialize the MySQL provider from explicit or environment connection and pool config.
    def __init__(self, config: MySQLConfig | None = None, pool_config: MySQLPoolConfig | None = None) -> None:
        # Store the connection configuration without opening a connection yet.
        self.config = config or MySQLConfig.from_env()
        # Build one lazy bounded pool for this process without opening a physical connection.
        self._pool = MySQLConnectionPool(self._open_physical_connection, pool_config)
        # Track whether this process has completed exact read-only schema compatibility verification.
        self._ready = False
        # Serialize first-use compatibility verification across concurrent request threads.
        self._ready_lock = threading.RLock()

    # Import mysql.connector only when the MySQL provider is selected.
    def _connector(self):
        # Start protected import so default JSON runs do not require the dependency.
        try:
            # Import the optional MySQL driver at runtime.
            import mysql.connector
        # Surface a focused dependency error when MySQL is configured without the driver.
        except ImportError as exc:
            # Raise a runtime error that names the optional dependency.
            raise RuntimeError("MySQL storage requires the optional mysql-connector-python dependency.") from exc
        # Return the imported connector module.
        return mysql.connector

    # Open one physical MySQL connection for the pool using fixed credentials and a bounded timeout.
    def _open_physical_connection(self, connection_timeout: int):
        # Add only the validated connector deadline to the configured credentials.
        connection_options = {**self.config.kwargs(), "connection_timeout": connection_timeout}
        # Return one new physical DB-API connection to the pool.
        return self._connector().connect(**connection_options)

    # Lease a request-scoped MySQL connection from the bounded process-local pool.
    def connect(self, **overrides):
        # Reject connector overrides that could cross credential, database, or session boundaries.
        if set(overrides) - {"connection_timeout"}:
            # Raise a fixed validation error without echoing option names or values.
            raise ValueError("Unsupported MySQL connection override.")
        # Preserve the established readiness-probe timeout seam while pooling ordinary operations.
        connection_timeout = overrides.get("connection_timeout")
        # Return a lease whose close sanitizes and returns the physical connection.
        return self._pool.acquire(connect_timeout_seconds=connection_timeout)

    # Return the internal secret-free pool evidence used by lifecycle tests and future contracted telemetry.
    def pool_snapshot(self) -> dict:
        # Return only fixed low-cardinality gauges, counters, policy, and wait buckets.
        return self._pool.snapshot()

    # Close idle physical sessions and make this provider reject future checkout.
    def close_pool(self) -> None:
        # Delegate fail-safe connection shutdown to the pool.
        self._pool.close_all()

    # Verify the exact MySQL migration state before reads and writes.
    def ensure_ready(self) -> None:
        # Return immediately after this provider instance has completed a read-only compatibility check.
        if self._ready:
            # Avoid repeating metadata reads on every document or game-state operation.
            return
        # Serialize the first schema check so request threads share one verified state.
        with self._ready_lock:
            # Return when another thread completed verification while this thread waited.
            if self._ready:
                # Reuse the schema compatibility established by the winning thread.
                return
            # Open a runtime-identity connection for SELECT-only compatibility verification.
            connection = self.connect()
            # Start protected schema verification so the connection is always closed.
            try:
                # Fail closed on missing, old, future, dirty, gapped, or checksum-mismatched state.
                verify_runtime_compatibility(connection)
                # Mark this provider ready only after exact read-only verification.
                self._ready = True
            # Always close the connection after schema verification.
            finally:
                # Close the runtime connection without issuing DDL or migration-state DML.
                connection.close()

    # Reset MySQL storage tables while preserving the schema.
    def reset(self) -> None:
        # Ensure tables exist before clearing them.
        self.ensure_ready()
        # Open a connection for reset statements.
        connection = self.connect()
        # Start protected reset logic so the connection is always closed.
        try:
            # Open a cursor for DML reset statements.
            cursor = connection.cursor()
            # Delete ledger rows before players to satisfy foreign keys.
            cursor.execute("DELETE FROM casino_ledger")
            # Delete history rows because MySQL starts fresh after reset.
            cursor.execute("DELETE FROM casino_history")
            # Delete JSON document rows because settings bootstrap from defaults.
            cursor.execute("DELETE FROM casino_documents")
            # Delete player rows after dependent ledger rows.
            cursor.execute("DELETE FROM casino_players")
            # Commit the reset as one unit.
            connection.commit()
        # Always close the connection after reset.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Return true when the MySQL players table has at least one row.
    def has_players(self) -> bool:
        # Ensure schema exists before checking player rows.
        self.ensure_ready()
        # Open a connection for the count query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a cursor that returns tuple rows.
            cursor = connection.cursor()
            # Count players to detect bootstrap state.
            cursor.execute("SELECT COUNT(*) FROM casino_players")
            # Return whether at least one player exists.
            return int(cursor.fetchone()[0]) > 0
        # Always close the connection after the count query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Insert default players when the MySQL table is empty.
    def _seed_players_if_empty(self, cursor, default_factory: Callable[[], dict]) -> None:
        # Count rows so seed data is only inserted into a fresh database.
        cursor.execute("SELECT COUNT(*) FROM casino_players")
        # Fetch the count row from tuple or dictionary cursors used by different callers.
        count_row = cursor.fetchone()
        # Normalize the aggregate value without depending on the cursor row representation.
        player_count = next(iter(count_row.values())) if isinstance(count_row, dict) else count_row[0]
        # Branch when no players exist yet.
        if int(player_count) == 0:
            # Build the default player document from the caller's factory.
            state = default_factory()
            # Insert each default player row.
            for player in state.get("players", []):
                # Use INSERT IGNORE so two processes racing this count-then-seed on a fresh database lose harmlessly instead of raising an unmapped IntegrityError out of the read path. (issue #431)
                cursor.execute(
                    "INSERT IGNORE INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Insert one seeded player row while keeping any concurrently seeded row.
                    (player["player_id"], player["display_name"], player.get("type", "human"), round(float(player.get("balance", 0)), 2), player.get("created_at", utc_now()), player.get("updated_at", utc_now()), player.get("status", "active")),  # Bind seeded player fields.
                )

    # Convert a MySQL player row into the existing API shape.
    def _player_from_row(self, row: dict) -> dict:
        # Return a dict with the current public player field names.
        return {"player_id": row["player_id"], "display_name": row["display_name"], "type": row["player_type"], "balance": _money(row["balance"]), "created_at": row["created_at"], "updated_at": row["updated_at"], "status": row["status"]}

    # Load players from MySQL and seed defaults when starting fresh.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Ensure schema exists before reading players.
        self.ensure_ready()
        # Open a connection for the bootstrap and read transaction.
        connection = self.connect()
        # Start protected read logic so the connection is always closed.
        try:
            # Open a dictionary cursor so row mapping is explicit.
            cursor = connection.cursor(dictionary=True)
            # Seed default players if this is a fresh MySQL database.
            self._seed_players_if_empty(cursor, default_factory)
            # Commit seed rows before reading the ordered player list.
            connection.commit()
            # Read players in stable order for deterministic API responses.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players ORDER BY player_id")
            # Convert database rows into the JSON-compatible state document.
            players = [self._player_from_row(row) for row in cursor.fetchall()]
            # Return the document shape expected by existing callers.
            return {"schema_version": SCHEMA_VERSION, "players": players}
        # Always close the connection after loading players.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Insert every missing player from one compatible document without replacing durable rows. (STORAGE-008, issue #431)
    def save_players(self, state: dict) -> None:
        # Ensure schema exists before inserting player rows.
        self.ensure_ready()
        # Open a connection for the bounded append operation.
        connection = self.connect()
        # Start protected transaction logic so failures roll back and the connection always closes.
        try:
            # Start one explicit transaction across all supplied player inserts.
            connection.start_transaction()
            # Open a cursor for bounded insert statements.
            cursor = connection.cursor()
            # Insert each supplied player without deleting or overwriting any existing row.
            for player in state.get("players", []):
                # Insert one normalized player only when its durable identifier is absent.
                cursor.execute(
                    "INSERT IGNORE INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Keep existing wallet and lifecycle state unchanged on a repeated seed.
                    (player["player_id"], player["display_name"], player.get("type", "human"), round(float(player.get("balance", 0)), 2), player.get("created_at", utc_now()), player.get("updated_at", utc_now()), player.get("status", "active")),  # Bind only the candidate insert fields.
                )
            # Commit all missing-player inserts as one unit.
            connection.commit()
        # Roll back every partial insert when the driver reports a failure.
        except Exception:
            # Restore the complete pre-call player table state.
            connection.rollback()
            # Preserve the original provider error for the standard API envelope.
            raise
        # Always close the connection after saving players.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Update one player in a MySQL transaction.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Ensure schema exists before updating players.
        self.ensure_ready()
        # Open a connection for the row-locking transaction.
        connection = self.connect()
        # Start protected transaction logic so the connection is always closed.
        try:
            # Start an explicit transaction for row-level locking.
            connection.start_transaction()
            # Open a dictionary cursor for the selected player row.
            cursor = connection.cursor(dictionary=True)
            # Lock the player row until the update commits.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the selected player row.
            row = cursor.fetchone()
            # Raise a consistent not-found error when the row does not exist.
            if row is None:
                # Roll back before surfacing the not-found error.
                connection.rollback()
                # Raise the same player lookup error shape used by players.get_player.
                raise NotFoundError(f"Player {player_id} was not found")
            # Convert the row into the public player shape for the updater.
            player = self._player_from_row(row)
            # Let the caller mutate the public player shape.
            updater(player)
            # Normalize the updated player row.
            player["balance"] = round(float(player.get("balance", 0)), 2)
            # Stamp the player update time.
            player["updated_at"] = utc_now()
            # Persist the updated fields.
            cursor.execute(
                "UPDATE casino_players SET display_name = %s, player_type = %s, balance = %s, updated_at = %s, status = %s WHERE player_id = %s",  # Update one locked player row.
                (player["display_name"], player.get("type", "human"), player["balance"], player["updated_at"], player.get("status", "active"), player_id),  # Bind updated player fields.
            )
            # Commit the row update.
            connection.commit()
            # Return the committed player row.
            return player
        # Roll back unexpected failures before re-raising them.
        except Exception:
            # Roll back any open transaction.
            connection.rollback()
            # Re-raise the original exception.
            raise
        # Always close the connection after the update attempt.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Create one deterministic player under a MySQL primary-key transaction.
    def ensure_player(self, player: dict) -> dict:
        # Ensure the relational schema exists before provisioning.
        self.ensure_ready()
        # Open one connection for the insert-or-read transaction.
        connection = self.connect()
        # Protect rollback and cleanup for every database outcome.
        try:
            # Start an explicit transaction so duplicate creators serialize on the primary key.
            connection.start_transaction()
            # Open a dictionary cursor for the committed row projection.
            cursor = connection.cursor(dictionary=True)
            # Insert the deterministic player once without overwriting any existing wallet state.
            cursor.execute(
                "INSERT IGNORE INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Preserve existing rows on an idempotent replay.
                (player["player_id"], player["display_name"], player.get("type", "human"), round(float(player.get("balance", 0)), 2), player["created_at"], player["updated_at"], player.get("status", "active")),  # Bind only normalized deterministic fields.
            )
            # Lock and read the resulting row before validating compatibility.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players WHERE player_id = %s FOR UPDATE", (player["player_id"],))
            # Resolve the inserted or pre-existing row.
            row = cursor.fetchone()
            # Reject an impossible missing row without committing partial state.
            if row is None:
                # Raise a stable provisioning conflict for the recoverable caller.
                raise ConflictError("Player provisioning did not produce durable state")
            # Convert the relational row into the public storage shape.
            result = self._player_from_row(row)
            # Reject a primary-key collision with incompatible player ownership semantics.
            if result.get("type") != player.get("type"):
                # Keep the original row unchanged and fail closed.
                raise ConflictError("Player provisioning identity conflicts with existing state")
            # Commit either the first insert or the compatible no-op replay.
            connection.commit()
            # Return the committed player row.
            return result
        # Roll back every failed provisioning attempt.
        except Exception:
            # Discard any partial insert or lock state.
            connection.rollback()
            # Preserve the original bounded application error.
            raise
        # Always release the provider connection.
        finally:
            # Close the database connection after commit or rollback.
            connection.close()

    # Execute a ledger transaction and player balance update atomically in MySQL.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Normalize the transaction amount to the app's fake-money precision.
        amount = round(float(amount), 2)
        # Reject zero-value ledger rows before touching player state.
        if amount == 0:
            # Raise a validation error consistent with the previous ledger module.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Ensure schema exists before writing ledger rows.
        self.ensure_ready()
        # Open a connection for the row-locking transaction.
        connection = self.connect()
        # Start protected transaction logic so the connection is always closed.
        try:
            # Start an explicit transaction so balance and ledger insert commit together.
            connection.start_transaction()
            # Open a dictionary cursor for row access.
            cursor = connection.cursor(dictionary=True)
            # Lock the player row to serialize concurrent wallet mutations.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the locked player row.
            row = cursor.fetchone()
            # Raise a consistent not-found error when the player does not exist.
            if row is None:
                # Roll back before raising the lookup error.
                connection.rollback()
                # Raise the same player lookup error shape used by players.get_player.
                raise NotFoundError(f"Player {player_id} was not found")
            # Capture the balance before the proposed mutation.
            before = _money(row["balance"])
            # Compute the balance after the proposed mutation.
            after = round(before + amount, 2)
            # Reject transactions that would overdraw the fake-money wallet.
            if after < -1e-9:
                # Roll back before surfacing insufficient funds.
                connection.rollback()
                # Raise the existing insufficient-funds error with ledger details.
                raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
            # Build the ledger event before persistence so the response matches the row.
            event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, details)
            # Update the locked player balance first within the open transaction.
            cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (after, utc_now(), player_id))
            # Insert the ledger row in the same transaction as the balance update.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Insert the atomic ledger event row.
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], json.dumps(event["details"], sort_keys=True)),  # Bind ledger event fields.
            )
            # Commit both balance and ledger mutations together.
            connection.commit()
            # Return the committed ledger event to the caller.
            return event
        # Roll back unexpected failures before re-raising them.
        except Exception:
            # Roll back any open transaction.
            connection.rollback()
            # Re-raise the original exception.
            raise
        # Always close the connection after the transaction attempt.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Execute or replay one storage-enforced MySQL ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
        # Normalize the transaction amount to the app's fake-money precision.
        amount = round(float(amount), 2)
        # Reject zero-value ledger rows before opening a database transaction.
        if amount == 0:
            # Raise the standard ledger validation error.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Normalize the indexed action key before using it in SQL.
        action_key = _normalize_action_key(action_key)
        # Derive the indexed game-or-core namespace.
        scope = _action_scope(game)
        # Derive the semantic digest used for replay conflict checks.
        fingerprint = _action_fingerprint(amount, transaction_type, game, round_id, details)
        # Add storage-owned metadata to the committed ledger details.
        committed_details = _action_details(details, action_key, fingerprint)
        # Ensure the migrated schema and unique index exist before writing.
        self.ensure_ready()
        # Open a connection for the row-locking action transaction.
        connection = self.connect()
        # Start protected transaction logic so rollback and close always run.
        try:
            # Start one transaction containing identity lookup, balance update, and ledger insertion.
            connection.start_transaction()
            # Open a dictionary cursor for player and ledger row mapping.
            cursor = connection.cursor(dictionary=True)
            # Lock the player row so independent processes serialize all actions for this wallet.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (player_id,))
            # Read the locked player row.
            player_row = cursor.fetchone()
            # Reject unknown players before identity lookup or mutation.
            if player_row is None:
                # Roll back the empty transaction before raising the lookup error.
                connection.rollback()
                # Raise the standard player lookup error.
                raise NotFoundError(f"Player {player_id} was not found")
            # Read a prior committed event for the same storage action identity.
            cursor.execute(
                "SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s AND action_scope = %s AND action_key = %s",  # Query the unique storage identity inside the wallet transaction.
                (player_id, scope, action_key),  # Bind the player, namespace, and caller action key.
            )
            # Fetch the prior row when this call is a replay.
            existing_row = cursor.fetchone()
            # Return the original committed event without another wallet mutation.
            if existing_row is not None:
                # Convert the database row into the public ledger event shape.
                existing_event = _ledger_from_row(existing_row)
                # Reject changed semantic reuse before returning the prior result.
                _validate_action_replay(existing_event, fingerprint, action_key)
                # End the read-only replay transaction and release the player lock.
                connection.commit()
                # Return the immutable original event with an explicit replay marker.
                return existing_event, True
            # Capture the wallet balance before the new action.
            before = _money(player_row["balance"])
            # Compute the wallet balance after the new action.
            after = round(before + amount, 2)
            # Reject actions that would overdraw the fake-money wallet.
            if after < -1e-9:
                # Roll back before surfacing insufficient funds.
                connection.rollback()
                # Raise the standard insufficient-funds error with transaction context.
                raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
            # Build the immutable event returned by all later replays.
            event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, committed_details)
            # Update the locked wallet balance inside the action transaction.
            cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (after, utc_now(), player_id))
            # Insert the action identity, semantic digest, and ledger row in the same transaction.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Persist the unique money action with its wallet transition.
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], scope, action_key, fingerprint, json.dumps(event["details"], sort_keys=True)),  # Bind action and ledger fields atomically.
            )
            # Commit identity reservation, balance mutation, and append-only event together.
            connection.commit()
            # Return the newly committed event with a non-replay marker.
            return event, False
        # Roll back any unexpected provider or database failure.
        except Exception:
            # Roll back all uncommitted identity, wallet, and ledger changes.
            connection.rollback()
            # Re-raise the original exception for standard API mapping.
            raise
        # Always close the connection after the action attempt.
        finally:
            # Close this operation's MySQL connection.
            connection.close()

    # Read recent ledger events from MySQL.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Ensure schema exists before reading ledger rows.
        self.ensure_ready()
        # Open a connection for the ledger query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a dictionary cursor for row mapping.
            cursor = connection.cursor(dictionary=True)
            # Build the filtered or unfiltered query.
            if player_id is None:
                # Read the newest ledger rows without a player filter.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger ORDER BY sequence_id DESC LIMIT %s", (int(limit),))
            # Handle the player-specific ledger path.
            else:
                # Read the newest ledger rows for the requested player.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s ORDER BY sequence_id DESC LIMIT %s", (player_id, int(limit)))
            # Convert reversed newest-first rows back to chronological order.
            rows = list(reversed(cursor.fetchall()))
            # Return JSON-compatible ledger event dictionaries.
            return [_ledger_from_row(row) for row in rows]
        # Always close the connection after the ledger query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Append one history event to MySQL.
    def append_history(self, event: dict) -> None:
        # Ensure schema exists before writing history.
        self.ensure_ready()
        # Open a connection for the insert.
        connection = self.connect()
        # Start protected insert logic so the connection is always closed.
        try:
            # Open a cursor for the insert statement.
            cursor = connection.cursor()
            # Insert one normalized history row.
            cursor.execute(
                "INSERT INTO casino_history (timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Insert one history event row.
                tuple(event[field] for field in HISTORY_FIELDS),  # Bind history fields in schema order.
            )
            # Commit the history insert.
            connection.commit()
        # Always close the connection after the insert.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Read recent history rows from MySQL.
    def recent_history(self, limit: int = 100, game: str | None = None) -> list[dict]:
        # Ensure schema exists before reading history.
        self.ensure_ready()
        # Open a connection for the history query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a dictionary cursor for row mapping.
            cursor = connection.cursor(dictionary=True)
            # Build the filtered or unfiltered query.
            if game:
                # Read the newest history rows for one game.
                cursor.execute("SELECT timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version FROM casino_history WHERE game = %s ORDER BY sequence_id DESC LIMIT %s", (game, int(limit)))
            # Handle the unfiltered history path.
            else:
                # Read the newest history rows across all games.
                cursor.execute("SELECT timestamp, game, round_id, player_id, bet_type, bet_label, amount, outcome, payout, balance_after, details_json, schema_version FROM casino_history ORDER BY sequence_id DESC LIMIT %s", (int(limit),))
            # Convert reversed newest-first rows back to chronological order.
            rows = list(reversed(cursor.fetchall()))
            # Return CSV-compatible dictionaries for existing API responses.
            return [_history_from_row(row) for row in rows]
        # Always close the connection after the history query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Read a named JSON document from MySQL.
    def read_document(self, key: str, default: Any) -> Any:
        # Ensure schema exists before reading the document.
        self.ensure_ready()
        # Open a connection for the document query.
        connection = self.connect()
        # Start protected query logic so the connection is always closed.
        try:
            # Open a dictionary cursor for the selected document.
            cursor = connection.cursor(dictionary=True)
            # Read the document payload by key.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s", (key,))
            # Fetch the optional document row.
            row = cursor.fetchone()
            # Return defaults when the document does not exist yet.
            if row is None:
                # Evaluate default factories lazily to preserve JSON helper semantics.
                return default() if callable(default) else default
            # Return the decoded JSON document.
            return _decode_json(row["payload_json"])
        # Always close the connection after the document query.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Read one MySQL security document through the existing strict decoder and shape boundary.
    def read_document_strict(self, key: str, default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Start protected decoding so malformed provider JSON uses the fixed recovery boundary.
        try:
            # Reuse the existing query, missing-row default, and strict MySQL JSON decoder.
            value = self.read_document(key, default)
        # Collapse only JSON text/type/limit failures without changing connection behavior.
        except (UnicodeError, ValueError, TypeError, RecursionError):
            # Preserve the stored row and return one value-free operator-recovery failure.
            raise RuntimeError("Stored document requires operator recovery") from None
        # Apply the same provider-neutral caller-owned shape contract.
        return _validated_strict_document(value, validator)

    # Write a named JSON document to MySQL.
    def write_document(self, key: str, data: Any) -> None:
        # Ensure schema exists before writing the document.
        self.ensure_ready()
        # Open a connection for the upsert.
        connection = self.connect()
        # Start protected upsert logic so the connection is always closed.
        try:
            # Open a cursor for the upsert statement.
            cursor = connection.cursor()
            # Upsert the JSON document by key.
            cursor.execute(
                "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE payload_json = VALUES(payload_json), updated_at = VALUES(updated_at)",  # Upsert one JSON document.
                (key, json.dumps(data, sort_keys=True), utc_now()),  # Bind document key, payload, and timestamp.
            )
            # Commit the document upsert.
            connection.commit()
        # Always close the connection after the upsert.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Mutate one document in a single row-locking MySQL transaction. (OTT-001)
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Verify the exact schema before opening a mutation transaction.
        self.ensure_ready()
        # Evaluate the default once so retries and the persisted seed share one canonical value.
        initial = default() if callable(default) else default
        # Open an independent connection so separate processes contend on the database row lock.
        connection = self.connect()
        # Start protected transaction logic so rollback and close are guaranteed.
        try:
            # Start an explicit transaction before creating or locking the canonical document row.
            connection.start_transaction()
            # Open a dictionary cursor so the stored JSON payload is accessed by its stable column name.
            cursor = connection.cursor(dictionary=True)
            # Materialize an absent row inside this transaction; concurrent inserts serialize on the unique key.
            cursor.execute(
                "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE document_key = VALUES(document_key)",  # Create the lockable row without overwriting existing state.
                (key, json.dumps(initial, sort_keys=True), utc_now()),  # Bind only the document key, non-secret initial payload, and timestamp.
            )
            # Lock the canonical row until the complete caller mutation commits.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (key,))
            # Read the row that the preceding upsert guarantees exists.
            row = cursor.fetchone()
            # Start protected strict decoding for an optional security-document validator.
            try:
                # Decode a detached current document for the caller-owned mutation.
                current = _decode_json(row["payload_json"])
            # Collapse malformed MySQL JSON only when strict security validation was requested.
            except (UnicodeError, ValueError, TypeError, RecursionError):
                # Preserve ordinary update exceptions for callers without the strict seam.
                if validator is None:
                    # Re-raise the original decoder failure unchanged.
                    raise
                # Abort this row transaction with one fixed operator-recovery failure.
                raise RuntimeError("Stored document requires operator recovery") from None
            # Validate the security document while the database row remains locked.
            current = _validated_strict_document(current, validator)
            # Apply the mutation while the row remains locked against every other process.
            updated = mutator(current)
            # Persist the complete updated document before releasing the row lock.
            cursor.execute(
                "UPDATE casino_documents SET payload_json = %s, updated_at = %s WHERE document_key = %s",  # Replace exactly the locked document row.
                (json.dumps(updated, sort_keys=True), utc_now(), key),  # Bind the canonical payload, timestamp, and locked key.
            )
            # Commit the mutation atomically so one-time consumers observe exactly one winner.
            connection.commit()
            # Return only after the updated document is durable.
            return updated
        # Roll back mutation or caller validation failures without publishing partial state.
        except Exception:
            # Release every transactional change made on this connection.
            connection.rollback()
            # Preserve the original exception and traceback for the caller.
            raise
        # Always close the transaction connection after success or failure.
        finally:
            # Release the database connection and any remaining server resources.
            connection.close()


# Convert decimal database values into two-decimal floats for API compatibility.
def _money(value: Any) -> float:
    # Convert Decimals through string form to avoid binary surprises.
    if isinstance(value, Decimal):
        # Return the rounded float equivalent of the decimal amount.
        return round(float(value), 2)
    # Return the rounded float equivalent of regular numeric values.
    return round(float(value), 2)


# Normalize and validate the caller-owned action key used for storage uniqueness.
def _normalize_action_key(action_key: str) -> str:
    # Convert string-compatible values while rejecting absent identities.
    normalized = str(action_key or "").strip()
    # Reject empty keys because they would collapse unrelated actions.
    if not normalized:
        # Surface the same validation error shape used by other ledger inputs.
        raise ValidationError("Ledger action key is required")
    # Bound keys to the indexed MySQL column width shared by both providers.
    if len(normalized) > 191:
        # Reject oversized keys before either provider opens a transaction.
        raise ValidationError("Ledger action key must be 191 characters or fewer")
    # Return the canonical non-empty identity fragment.
    return normalized


# Return the stable game-or-core namespace used in the unique action identity.
def _action_scope(game: str | None) -> str:
    # Keep game identities isolated while reserving a namespace for core wallet actions.
    return str(game or "core")


# Derive a semantic fingerprint so changed reuse cannot replay an earlier mutation.
def _action_fingerprint(amount: float, transaction_type: str, game: str | None, round_id: str | None, details: dict | None) -> str:
    # Build the canonical semantic payload without storage-owned metadata.
    semantic_payload = {
        # Include the signed fake-money amount in the conflict contract.
        "amount": round(float(amount), 2),
        # Include the transaction type so debit and payout meanings cannot collide.
        "transaction_type": transaction_type,
        # Include the game namespace selected for the action identity.
        "game": game,
        # Include the round or session identifier used for ledger traceability.
        "round_id": round_id,
        # Include caller details because changed wager or settlement semantics must conflict.
        "details": details or {},
    }
    # Serialize deterministically so independent processes derive the same digest.
    canonical = json.dumps(semantic_payload, sort_keys=True, separators=(",", ":"), default=str)
    # Return a fixed-width digest suitable for JSON and indexed MySQL storage.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Add storage-owned action metadata without mutating the caller's details object.
def _action_details(details: dict | None, action_key: str, fingerprint: str) -> dict:
    # Copy caller details so provider metadata never leaks back through shared references.
    normalized = dict(details or {})
    # Record the canonical action key for migration, audit, and JSON recovery.
    normalized["ledger_action_key"] = action_key
    # Record the semantic digest used to distinguish replay from changed reuse.
    normalized["ledger_action_fingerprint"] = fingerprint
    # Return the enriched ledger details payload.
    return normalized


# Validate that a committed action represents an exact semantic replay.
def _validate_action_replay(event: dict, fingerprint: str, action_key: str) -> None:
    # Read storage-owned metadata from the committed ledger event.
    stored_details = event.get("details") if isinstance(event.get("details"), dict) else {}
    # Reject reused identities whose committed semantic digest differs.
    if stored_details.get("ledger_action_fingerprint") != fingerprint:
        # Surface a stable conflict with the action key for API envelope details.
        raise ConflictError("Ledger action key was reused with different transaction semantics", {"action_key": action_key})
    # Reject corrupt registry entries whose stored key does not match their identity.
    if stored_details.get("ledger_action_key") != action_key:
        # Fail closed rather than replaying an ambiguously indexed money action.
        raise ConflictError("Ledger action registry is inconsistent", {"action_key": action_key})


# Decode a JSON value that may already be decoded by the MySQL driver.
def _decode_json(value: Any) -> Any:
    # Return already-decoded dict/list payloads directly.
    if isinstance(value, (dict, list)):
        # Return the driver-decoded JSON value.
        return value
    # Return an empty object when MySQL returns a null-like value unexpectedly.
    if value is None:
        # Return a safe empty details object.
        return {}
    # Decode string or bytes JSON payloads.
    return json.loads(value)


# Build a normalized ledger event in the public response shape.
def _ledger_event(player_id: str, amount: float, transaction_type: str, before: float, after: float, game: str | None, round_id: str | None, details: dict | None) -> dict:
    # Return the ledger event shape validated by the ledger schema.
    return {
        # Store the event timestamp.
        "ts": utc_now(),
        # Store a unique ledger event ID.
        "ledger_id": new_id("led"),
        # Store the affected player ID.
        "player_id": player_id,
        # Store the optional game ID.
        "game": game,
        # Store the optional round or session ID.
        "round_id": round_id,
        # Store the transaction type.
        "transaction_type": transaction_type,
        # Store the signed transaction amount.
        "amount": amount,
        # Store the balance before mutation.
        "balance_before": before,
        # Store the balance after mutation.
        "balance_after": after,
        # Store structured transaction details.
        "details": details or {},
    }


# Convert a MySQL ledger row into the public ledger event shape.
def _ledger_from_row(row: dict) -> dict:
    # Return the normalized ledger event.
    return {
        # Store the ledger event ID.
        "ledger_id": row["ledger_id"],
        # Store the event timestamp.
        "ts": row["ts"],
        # Store the affected player ID.
        "player_id": row["player_id"],
        # Store the optional game ID.
        "game": row["game"],
        # Store the optional round or session ID.
        "round_id": row["round_id"],
        # Store the transaction type.
        "transaction_type": row["transaction_type"],
        # Store the signed transaction amount.
        "amount": _money(row["amount"]),
        # Store the balance before mutation.
        "balance_before": _money(row["balance_before"]),
        # Store the balance after mutation.
        "balance_after": _money(row["balance_after"]),
        # Store structured transaction details.
        "details": _decode_json(row["details_json"]),
    }


# Convert a MySQL history row into the existing CSV/API shape.
def _history_from_row(row: dict) -> dict:
    # Return history fields with numeric values normalized for JSON responses.
    return {
        # Store the event timestamp.
        "timestamp": row["timestamp"],
        # Store the source game.
        "game": row["game"],
        # Store the round or session ID.
        "round_id": row["round_id"],
        # Store the owning player ID.
        "player_id": row["player_id"],
        # Store the wager type.
        "bet_type": row["bet_type"],
        # Store the wager label.
        "bet_label": row["bet_label"],
        # Store the wager amount.
        "amount": _money(row["amount"]),
        # Store the outcome.
        "outcome": row["outcome"],
        # Store the payout.
        "payout": _money(row["payout"]),
        # Store the balance after settlement.
        "balance_after": _money(row["balance_after"]),
        # Store details JSON as a string for compatibility with CSV-backed responses.
        "details_json": json.dumps(_decode_json(row["details_json"]), sort_keys=True),
        # Store the schema version.
        "schema_version": row["schema_version"],
    }


# Return the configured provider name with JSON as the local default.
def storage_provider_name() -> str:
    # Read the provider setting from the environment.
    return os.getenv("CASINO_STORAGE_PROVIDER", DEFAULT_STORAGE_PROVIDER).strip().lower() or DEFAULT_STORAGE_PROVIDER


# Build a provider instance for the current configuration.
def _build_provider() -> StorageProvider:
    # Read the selected provider name.
    name = storage_provider_name()
    # Return the JSON provider for the default local mode.
    if name == "json":
        # Build the local JSON fallback provider.
        return JsonStorageProvider()
    # Return the MySQL provider when explicitly configured.
    if name == "mysql":
        # Build the configured MySQL provider.
        return MySQLStorageProvider()
    # Reject unknown provider names with a clear validation error.
    raise ValidationError(f"Unsupported storage provider: {name}")


# Return the process-wide storage provider.
def get_storage_provider() -> StorageProvider:
    # Allow tests to inject an isolated provider without environment churn.
    if _TEST_PROVIDER is not None:
        # Return the injected test provider.
        return _TEST_PROVIDER
    # Use a lock so parallel requests share one lazily constructed provider.
    with _PROVIDER_LOCK:
        # Declare the module-level provider cache for assignment.
        global _PROVIDER
        # Build the provider the first time it is requested.
        if _PROVIDER is None:
            # Store the selected provider instance.
            _PROVIDER = _build_provider()
        # Return the cached provider.
        return _PROVIDER


# Inject a provider for storage tests.
def set_provider_for_tests(provider: StorageProvider | None) -> None:
    # Declare provider caches for assignment.
    global _TEST_PROVIDER, _PROVIDER
    # Preserve test and runtime provider instances before replacing the caches.
    previous_test_provider = _TEST_PROVIDER
    # Preserve the regular provider because test injection always invalidates that cache.
    previous_runtime_provider = _PROVIDER
    # Store the explicit test provider.
    _TEST_PROVIDER = provider
    # Clear the regular cache so later tests rebuild from environment.
    _PROVIDER = None
    # Close the regular cache, plus a test provider only when test injection is being cleared.
    providers_to_close = (previous_runtime_provider, previous_test_provider if provider is None else None)
    # Release eligible replaced MySQL pools without affecting the newly injected provider.
    for previous_provider in providers_to_close:
        # Skip empty caches, duplicate references, and the provider now being installed.
        if previous_provider is None or previous_provider is provider:
            # Continue to the next cached provider.
            continue
        # Resolve the optional lifecycle hook without imposing it on JSON providers.
        close_pool = getattr(previous_provider, "close_pool", None)
        # Close idle physical sessions when the replaced provider owns a pool.
        if callable(close_pool):
            # Execute the provider-owned shutdown hook.
            close_pool()


# Close process-wide cached MySQL pools during interpreter shutdown.
def _close_cached_provider_pools() -> None:
    # Deduplicate current test and runtime provider references by object identity.
    cached_providers = {id(provider): provider for provider in (_TEST_PROVIDER, _PROVIDER) if provider is not None}
    # Visit each distinct cached provider once.
    for provider in cached_providers.values():
        # Resolve the optional pool lifecycle hook without affecting JSON providers.
        close_pool = getattr(provider, "close_pool", None)
        # Close idle physical sessions when this cached provider owns a pool.
        if callable(close_pool):
            # Execute the provider-owned shutdown hook.
            close_pool()


# Register one module-level shutdown hook without retaining every test-created provider.
atexit.register(_close_cached_provider_pools)


# Seed players when the configured provider is fresh.
def bootstrap_players(default_factory: Callable[[], dict]) -> None:
    # Get the active storage provider.
    provider = get_storage_provider()
    # Ensure backing storage exists before checking player bootstrap state.
    provider.ensure_ready()
    # Keep the empty check as a fast path that skips provisioning on already-seeded storage. (issue #431)
    if not provider.has_players():
        # Route each seeded row through idempotent provisioning so the check-then-write race cannot clobber a concurrent bootstrap or wallet write. (issue #431)
        for player in default_factory().get("players", []):
            # Create or keep one default player exactly once under the provider's own locks.
            provider.ensure_player(player)
