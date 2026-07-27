# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import annotations so provider type hints can refer to classes declared later.
from __future__ import annotations
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
# Import required dependency so provider-created ledger rows use stable IDs.
from casino.core.ids import new_id
# Import read-only MySQL migration compatibility without exposing deployment credentials.
from casino.core.mysql_migrations import verify_runtime_compatibility
# Import required dependency so storage providers surface existing API errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError

# Set _PROVIDER_LOCK to guard lazy provider construction.
_PROVIDER_LOCK = threading.RLock()
# Set _PROVIDER to cache the selected provider for one process.
_PROVIDER: StorageProvider | None = None
# Set _TEST_PROVIDER to allow storage tests to inject an isolated provider.
_TEST_PROVIDER: StorageProvider | None = None


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

    # Write a named JSON document such as audio settings.
    def write_document(self, key: str, data: Any) -> None:
        # Raise because concrete providers must persist settings documents.
        raise NotImplementedError

    # Mutate one named JSON document atomically under the provider's cross-process transaction boundary.
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any) -> Any:
        # Raise because concrete providers must own their read-modify-write concurrency semantics.
        raise NotImplementedError


# Define the JsonStorageProvider that preserves default local file behavior.
class JsonStorageProvider(StorageProvider):
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

    # Ensure local data folders exist before reads and writes.
    def ensure_ready(self) -> None:
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

    # Reset local JSON storage by clearing the provider data directory.
    def reset(self) -> None:
        # Guard destructive local cleanup with the provider lock.
        with self.lock:
            # Remove only the configured data directory when it exists.
            if self.data_dir.exists():
                # Use shutil because the data directory may contain game subfolders.
                shutil.rmtree(self.data_dir)
            # Drop the ledger tail cache so reads never serve pre-reset rows. (issue #412)
            self._drop_ledger_cache()
            # Drop the action-registry cache alongside its removed backing file. (issue #412)
            self._drop_actions_cache()
            # Recreate provider directories after clearing local state.
            self.ensure_ready()

    # Return true when the local players document exists.
    def has_players(self) -> bool:
        # Ensure directories exist before testing for the players file.
        self.ensure_ready()
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

    # Hold one operating-system lock across a JSON wallet transaction.
    @contextmanager
    def _ledger_process_lock(self):  # Hold one provider-local operating-system wallet lock.
        # Ensure the provider directory exists before opening its lock file.
        self.ensure_ready()
        # Open a persistent one-byte lock target shared by every provider process.
        with self.ledger_lock_path().open("a+b") as handle:
            # Branch to the Windows byte-range locking implementation.
            if os.name == "nt":
                # Import the Windows runtime lock API only on Windows.
                import msvcrt
                # Ensure the file contains one byte that can be locked.
                if handle.seek(0, os.SEEK_END) == 0:
                    # Write the lock byte once for a fresh provider directory.
                    handle.write(b"0")
                    # Flush the byte before locking it from another process.
                    handle.flush()
                # Seek to the byte range that represents the provider wallet lock.
                handle.seek(0)
                # Block until this process exclusively owns the byte range.
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                # Yield while the caller owns the cross-process wallet lock.
                try:
                    # Transfer control to the protected wallet operation.
                    yield
                # Always release the byte-range lock after the operation.
                finally:
                    # Return to the locked byte before unlocking it.
                    handle.seek(0)
                    # Release the byte range for the next process.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            # Use advisory flock on POSIX development and CI hosts.
            else:
                # Import POSIX locking only where the module is available.
                import fcntl
                # Block until this process exclusively owns the file lock.
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                # Yield while the caller owns the cross-process wallet lock.
                try:
                    # Transfer control to the protected wallet operation.
                    yield
                # Always release the advisory lock after the operation.
                finally:
                    # Release the file lock for the next process.
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    # Hold one operating-system lock across a named-document read-modify-write.
    @contextmanager
    def _document_process_lock(self, key: str):  # Serialize the same document across provider instances and processes.
        # Ensure the document parent exists before opening its sidecar lock target.
        self.document_lock_path(key).parent.mkdir(parents=True, exist_ok=True)
        # Open a persistent one-byte lock target shared by every provider instance for this key.
        with self.document_lock_path(key).open("a+b") as handle:
            # Branch to the Windows byte-range locking implementation.
            if os.name == "nt":
                # Import the Windows runtime lock API only on Windows.
                import msvcrt
                # Ensure the file contains one byte that can be locked.
                if handle.seek(0, os.SEEK_END) == 0:
                    # Write the lock byte once for a fresh document lock.
                    handle.write(b"0")
                    # Flush the byte before locking it from another process.
                    handle.flush()
                # Seek to the byte range that represents this document lock.
                handle.seek(0)
                # Block until this process exclusively owns the byte range.
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                # Yield while the caller owns the cross-process document lock.
                try:
                    # Transfer control to the protected document operation.
                    yield
                # Always release the byte-range lock after the operation.
                finally:
                    # Return to the locked byte before unlocking it.
                    handle.seek(0)
                    # Release the byte range for the next process.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            # Use advisory flock on POSIX development and CI hosts.
            else:
                # Import POSIX locking only where the module is available.
                import fcntl
                # Block until this process exclusively owns the file lock.
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                # Yield while the caller owns the cross-process document lock.
                try:
                    # Transfer control to the protected document operation.
                    yield
                # Always release the advisory lock after the operation.
                finally:
                    # Release the file lock for the next process.
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    # Append a JSONL ledger event to the local ledger file.
    def _append_jsonl(self, path: Path, event: dict) -> None:
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

    # Load players after recovering any committed action projection from a prior process.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Guard recovery and the player read from concurrent local threads.
        with self.lock:
            # Guard recovery and the player read from independent processes.
            with self._ledger_process_lock():
                # Project any action that committed before a process stopped or lost its response.
                self._recover_committed_actions()
                # Return the compatible player document after recovery.
                return self._load_players_document(default_factory)

    # Save players to the existing JSON document shape.
    def save_players(self, state: dict) -> None:
        # Copy the state so callers do not observe schema mutation side effects.
        saved_state = dict(state)
        # Preserve the current schema version on every saved player document.
        saved_state["schema_version"] = SCHEMA_VERSION
        # Write the normalized player document to disk.
        self._write_json(self.players_path(), saved_state)

    # Update one player with the existing callback semantics.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Guard read-modify-write with the provider lock.
        with self.lock:
            # Guard the read-modify-write operation from independent processes.
            with self._ledger_process_lock():
                # Recover committed ledger actions before applying a later player update.
                self._recover_committed_actions()
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
                        self.save_players(state)
                        # Return the updated player row to the caller.
                        return player
        # Raise a consistent not-found error when no player matched.
        raise NotFoundError(f"Player {player_id} was not found")

    # Create one deterministic player under the same cross-process wallet lock used by updates.
    def ensure_player(self, player: dict) -> dict:
        # Guard deterministic provisioning from concurrent threads.
        with self.lock:
            # Guard deterministic provisioning from independent processes.
            with self._ledger_process_lock():
                # Recover any committed ledger projection before changing the player document.
                self._recover_committed_actions()
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
                self.save_players(state)
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
            self.save_players(state)
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
        self.save_players(state)
        # Append the ledger event while the compound transaction lock is still held.
        self._append_jsonl(self.ledger_path(), event)
        # Return the committed ledger event to the caller.
        return event

    # Execute a ledger transaction and balance update under thread and process locks.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
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
                # Recover any earlier committed action before applying a later mutation.
                self._recover_committed_actions()
                # Execute the existing compatible transaction inside both locks.
                return self._transact_ledger_locked(player_id, amount, transaction_type, game, round_id, details)

    # Execute or replay one storage-enforced JSON ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
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
                # Load and recover all committed actions before inspecting wallet state.
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
                # Project any action that committed before its process stopped or lost a response.
                self._recover_committed_actions()
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
        # Import csv only for the JSON provider's CSV compatibility path.
        import csv
        # Ensure local directories exist before writing.
        self.ensure_ready()
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
        # Ensure local directories exist before reading.
        self.ensure_ready()
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
        # Reuse the local JSON helper for settings documents.
        return self._read_json(self.document_path(key), default)

    # Write a named JSON document to local storage.
    def write_document(self, key: str, data: Any) -> None:
        # Reuse the local JSON helper for settings documents.
        self._write_json(self.document_path(key), data)

    # Mutate one local document under the provider lock for direct provider callers.
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any) -> Any:
        # Serialize the direct provider read-modify-write inside this process.
        with self.lock:
            # Hold the same sidecar lock across every provider instance and process.
            with self._document_process_lock(key):
                # Resolve the exact document path once under the cross-process lock.
                path = self.document_path(key)
                # Evaluate the default only when the durable document is absent.
                if not path.exists():
                    # Preserve lazy default-factory behavior for new documents.
                    current = default() if callable(default) else default
                # Parse an existing document strictly so malformed evidence is never replaced by a default.
                else:
                    # Start protected parsing while keeping the original file untouched on failure.
                    try:
                        # Decode the current durable payload inside the complete mutation boundary.
                        current = json.loads(path.read_text(encoding="utf-8"))
                    # Preserve malformed state and publish an operator-recovery failure.
                    except json.JSONDecodeError:
                        # Copy the malformed payload for explicit recovery without replacing the source.
                        backup = path.with_suffix(path.suffix + f".corrupt-{int(time.time())}")
                        # Preserve a recoverable snapshot before aborting the mutation.
                        shutil.copy2(path, backup)
                        # Abort without invoking the mutator or writing a normalized document.
                        raise RuntimeError("Stored document requires operator recovery") from None
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

    # Initialize the MySQL provider from an explicit or environment config.
    def __init__(self, config: MySQLConfig | None = None) -> None:
        # Store the connection configuration without opening a connection yet.
        self.config = config or MySQLConfig.from_env()
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

    # Open a new MySQL connection using the configured credentials.
    def connect(self, **overrides):
        # Merge bounded caller-owned connector options without changing stored credentials.
        connection_options = {**self.config.kwargs(), **overrides}
        # Return a new DB-API connection for one provider operation.
        return self._connector().connect(**connection_options)

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
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any) -> Any:
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
            # Decode a detached current document for the caller-owned mutation.
            current = _decode_json(row["payload_json"])
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
    # Store the explicit test provider.
    _TEST_PROVIDER = provider
    # Clear the regular cache so later tests rebuild from environment.
    _PROVIDER = None


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
