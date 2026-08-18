# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import annotations so provider type hints can refer to classes declared later.
from __future__ import annotations
# Import process-exit hooks so cached MySQL pools release idle connections on shutdown.
import atexit
# Import deep-copy support so indexed reads cannot mutate cached durable events.
import copy
# Import portable operating-system error numbers for exact lock-contention classification.
import errno
# Import required dependency so action fingerprints are derived from canonical transaction semantics.
import hashlib
# Import required dependency so process-lock helpers can be expressed as context managers.
from contextlib import contextmanager
# Import required dependency so decimal balances use one explicit cents rule.
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
from casino.config import DATA_DIR, DEFAULT_STORAGE_PROVIDER, GAME_DATA_DIR, LOG_DIR, SCHEMA_VERSION
# Import required dependency so provider-created rows use the app timestamp format.
from casino.core.clock import utc_now
# Import the immutable route-free game-action execution and resolution contract.
from casino.core.game_action import GameActionExecutor, GameActionMovement, GameActionPlan, GameActionReceipt, GameActionResolution, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, validate_execution_request, validate_resolution_request
# Preserve the historical pool-configuration import used by storage fixtures and live validation.
from casino.core.mysql_pool import MySQLPoolConfig
# Import and re-export the provider-neutral storage contract and shared helpers.
from casino.core.storage_base import HISTORY_FIELDS, MySQLConfig, StorageProvider, _action_details, _action_fingerprint, _action_scope, _decode_json, _history_from_row, _ledger_event, _ledger_from_row, _money, _money_decimal, _normalizable_players_document, _normalize_action_key, _quantized_money, _quantized_money_decimal, _validate_action_replay, _validate_wallet_normalization_replay, _validated_players_document, _validated_strict_document, _wallet_normalization_event
# Import the JSON reset lifecycle and shared private epoch constants.
from casino.core.storage_reset import JsonResetMixin, _GAME_ACTION_EPOCH_STORAGE_VERSION, _GAME_ACTION_MAX_EPOCH, _GAME_ACTION_STORAGE_VERSION
# Import and re-export the JSON game-action lifecycle and private recovery-stage set.
from casino.core.storage_game_actions_json import JsonGameActionMixin, _GAME_ACTION_STAGES
# Import and re-export the complete MySQL provider from its transitional package module.
from casino.core.storage_mysql_provider import MySQLStorageProvider, _BorrowedMySQLConnection
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
# Store the canonical fake-money quantum shared by migration and ordinary writes. (LEDGER-036)
_MONEY_QUANTUM = Decimal("0.01")
# Bound fake-money values to the signed-cent range already enforced by game actions.
_MAX_MONEY = Decimal("90000000000000000")
# Compact the append-only ledger-action journal only after a bounded growth interval. (LEDGER-034)
_LEDGER_ACTION_COMPACT_BYTES = 512 * 1024


# Return the process-shared reentrant lock for one exact JSON data root.
def _json_gate_lock(root_key: str) -> threading.RLock:
    # Serialize first construction so provider instances cannot receive different locks.
    with _JSON_GATE_REGISTRY_LOCK:
        # Reuse an existing lock or construct the sole lock for this root.
        return _JSON_GATE_LOCKS.setdefault(root_key, threading.RLock())


# Define the JsonStorageProvider that preserves default local file behavior.
class JsonStorageProvider(JsonGameActionMixin, JsonResetMixin, StorageProvider, GameActionExecutor):
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
        # Index cached rows by immutable ledger identity so projection checks stay constant-time. (issue #432)
        self._ledger_cache_by_id: dict[str, dict] = {}
        # Hold rows decoded from an unterminated trailing line without caching them. (issue #412)
        self._ledger_cache_tail_rows: list[dict] = []
        # Cache the parsed committed-action registry so wallet actions stop re-parsing it. (issue #412)
        self._actions_cache_registry: Any = None
        # Track the legacy snapshot identity used to seed the append-only action journal cache. (issue #432)
        self._actions_cache_snapshot_stat: tuple[int, int] | None = None
        # Track how many complete action-journal bytes have been applied to the cache. (issue #432)
        self._actions_cache_journal_offset = 0
        # Track the action-journal file identity at the cached offset. (issue #432)
        self._actions_cache_journal_stat: tuple[int, int] | None = None
        # Track the compacted-or-loaded journal size from which bounded growth is measured. (issue #432)
        self._actions_cache_compaction_floor = 0

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

    # Return the append-only action journal used for new constant-time commits. (LEDGER-034)
    def ledger_action_journal_path(self) -> Path:
        # Keep the journal beside the legacy snapshot so reset and backup semantics remain unchanged.
        return self.data_dir / "ledger_actions.jsonl"

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

    # Return the provider-private immutable execution/cancellation claim registry path.
    def game_action_claims_path(self) -> Path:
        # Keep lifecycle claims beside receipts under the same reset-safe global gate.
        return self.data_dir / ".game_actions" / "claims.json"

    # Return the provider-private reset epoch and readiness state path.
    def game_action_epoch_path(self) -> Path:
        # Keep the durable epoch inside the reset backup root for exact rollback.
        return self.data_dir / ".game_actions" / "epoch.json"

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
        # Discard the immutable ledger-id index built from the discarded rows.
        self._ledger_cache_by_id = {}
        # Discard rows decoded from an unterminated trailing line.
        self._ledger_cache_tail_rows = []

    # Forget the cached committed-action registry so the next read reloads from the file. (issue #412)
    def _drop_actions_cache(self) -> None:
        # Discard the cached parsed registry object.
        self._actions_cache_registry = None
        # Forget the legacy snapshot identity used by the discarded registry.
        self._actions_cache_snapshot_stat = None
        # Restart append-only journal parsing from the first complete record.
        self._actions_cache_journal_offset = 0
        # Forget the append-only journal identity used by the discarded registry.
        self._actions_cache_journal_stat = None
        # Restart bounded compaction growth accounting from an empty journal.
        self._actions_cache_compaction_floor = 0

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

    # Preserve one exact corrupt wallet payload under a stable content-derived forensic name. (STORAGE-014)
    def _preserve_corrupt_players(self, encoded: bytes) -> None:
        # Derive a non-secret identity that prevents repeated reads from multiplying backups.
        digest = hashlib.sha256(encoded).hexdigest()
        # Keep the forensic copy adjacent to the established players document.
        backup = self.players_path().with_name(f"players.json.corrupt-{digest}")
        try:
            # Create the content-addressed artifact only once without overwriting evidence.
            with backup.open("xb") as handle:
                # Write the exact corrupt bytes without decoding or normalization.
                handle.write(encoded)
                # Flush language buffers before asking the operating system for durability.
                handle.flush()
                # Persist the forensic bytes before reporting the recovery boundary.
                os.fsync(handle.fileno())
        # Accept a repeated observation only when the existing artifact is byte-identical.
        except FileExistsError:
            try:
                # Verify the content-addressed artifact instead of trusting its name alone.
                matches = backup.read_bytes() == encoded
            # Collapse forensic read failures without exposing a filesystem path.
            except OSError:
                # Fail closed when existing evidence cannot be verified.
                raise ConflictError("Wallet storage requires operator recovery") from None
            # Reject a mismatched pre-existing artifact as an operator-recovery condition.
            if not matches:
                # Preserve both source and ambiguous evidence without replacement.
                raise ConflictError("Wallet storage requires operator recovery")
        # Collapse forensic creation failures into the same value-free boundary.
        except OSError:
            # Leave the original players document untouched for operator inspection.
            raise ConflictError("Wallet storage requires operator recovery") from None

    # Read the money-bearing players document without ever substituting defaults for corruption. (STORAGE-014)
    def _read_players_document(self, default_factory: Callable[[], dict]) -> dict:
        # Ensure the local data root exists before the missing-file compatibility check.
        self.ensure_ready()
        # Resolve the authoritative wallet path exactly once.
        path = self.players_path()
        try:
            # Read the exact bytes so only true absence can select reviewed bootstrap defaults.
            encoded = path.read_bytes()
        # Preserve first-run bootstrap behavior only for a genuinely absent document.
        except FileNotFoundError:
            # Validate defaults through the same provider-neutral money boundary.
            return _validated_players_document(default_factory())
        # Treat every other filesystem failure as unavailable money state.
        except OSError:
            # Refuse without leaking the path or platform error.
            raise ConflictError("Wallet storage requires operator recovery") from None
        try:
            # Decode UTF-8 JSON with duplicate-key and non-finite-number rejection.
            state = json.loads(
                encoded.decode("utf-8"),
                object_pairs_hook=self._unique_json_object,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite number")),
            )
            # Validate every durable wallet before making the document observable.
            return _validated_players_document(state)
        # Classify malformed bytes and structural money corruption identically.
        except (UnicodeError, ValueError, RecursionError, ConflictError):
            # Preserve one exact forensic copy without changing the authoritative source.
            self._preserve_corrupt_players(encoded)
            # Return no replacement, partial wallet, or parser detail.
            raise ConflictError("Wallet storage requires operator recovery") from None

    # Read only structurally valid wallet bytes while allowing explicit sub-cent repair. (STORAGE-015)
    def _read_normalizable_players_document(self) -> dict:
        # Require an existing authoritative wallet document for the one-time operator pass.
        try:
            # Read the exact source bytes without selecting bootstrap defaults.
            encoded = self.players_path().read_bytes()
        # Treat a genuinely absent wallet collection as a clean empty first-run store.
        except FileNotFoundError:
            # Return the compatible empty document without creating any file.
            return {"schema_version": SCHEMA_VERSION, "players": []}
        # Classify every other unreadable wallet as an operator-recovery condition.
        except OSError:
            # Avoid creating money state from the normalization command.
            raise ConflictError("Wallet storage requires operator recovery") from None
        try:
            # Decode strict JSON while retaining finite sub-cent numeric values for repair.
            state = json.loads(encoded.decode("utf-8"), object_pairs_hook=self._unique_json_object, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite number")))
            # Accept only the exact wallet structure and finite nonnegative money values.
            return _normalizable_players_document(state)
        # Preserve every non-residue defect through the existing forensic boundary.
        except (UnicodeError, ValueError, RecursionError, ConflictError):
            # Retain one content-addressed copy of the unmodified source bytes.
            self._preserve_corrupt_players(encoded)
            # Refuse a partial or guessed normalization.
            raise ConflictError("Wallet storage requires operator recovery") from None

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

    # Attempt one exact operating-system file lock without waiting behind active work.
    @contextmanager
    def _try_exclusive_process_file_lock(self, path: Path):
        # Create the lock parent before opening the persistent lock target.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Open the same persistent one-byte target used by the blocking gate.
        with path.open("a+b") as handle:
            # Track whether this process acquired the lock and therefore must release it.
            acquired = False
            # Branch to the Windows byte-range locking implementation.
            if os.name == "nt":
                # Import the Windows runtime lock API only on Windows.
                import msvcrt
                # Ensure the file contains one byte that can be locked.
                if handle.seek(0, os.SEEK_END) == 0:
                    # Write and flush the shared lock byte once for a fresh root.
                    handle.write(b"0")
                    handle.flush()
                # Seek to the shared one-byte range before the nonblocking attempt.
                handle.seek(0)
                try:
                    # Fail immediately when another process owns the byte range.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                # Classify only an exact Windows lock contender as unavailable.
                except OSError as exc:
                    # Re-raise descriptor, filesystem, and unexpected lock failures.
                    if exc.errno not in {errno.EACCES, errno.EAGAIN} and getattr(exc, "winerror", None) not in {33, 36}:
                        # Preserve the original fail-closed operating-system error.
                        raise
                    # Yield false without reading or mutating provider state.
                    yield False
                    # Stop after the caller observes lock ownership elsewhere.
                    return
            # Use nonblocking advisory flock on POSIX development and CI hosts.
            else:
                # Import POSIX locking only where the module is available.
                import fcntl
                try:
                    # Fail immediately when another process owns the file lock.
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Classify only documented advisory-lock contention as unavailable.
                except OSError as exc:
                    # Re-raise descriptor, I/O, and other filesystem failures.
                    if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                        # Preserve the original fail-closed operating-system error.
                        raise
                    # Yield false without reading or mutating provider state.
                    yield False
                    # Stop after the caller observes lock ownership elsewhere.
                    return
            # Remember that the finally block owns an exact release obligation.
            acquired = True
            try:
                # Transfer control while the exact nonblocking lock is held.
                yield True
            finally:
                # Skip release only when acquisition never succeeded.
                if acquired and os.name == "nt":
                    # Import the Windows runtime lock API only on Windows.
                    import msvcrt
                    # Return to the locked byte before releasing it.
                    handle.seek(0)
                    # Release the exact byte range for the active executor.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                # Release the POSIX advisory lock when this process owns it.
                elif acquired:
                    # Import POSIX locking only where the module is available.
                    import fcntl
                    # Release the exact file lock.
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

    # Attempt the global JSON gate once so resolution can report active ownership.
    @contextmanager
    def _try_json_global_gate(self):
        # Canonicalize this provider root for shared thread and process identity.
        root_key = self._json_root_key()
        # Include the process ID so forked children never inherit nesting state.
        depth_key = (os.getpid(), root_key)
        # Resolve the process-shared reentrant thread lock.
        thread_gate = _json_gate_lock(root_key)
        # Attempt thread ownership without waiting behind an active executor.
        acquired_thread = thread_gate.acquire(blocking=False)
        # Report pending immediately when another thread owns the provider lifecycle.
        if not acquired_thread:
            # Transfer only the finite unavailable result.
            yield False
            # Stop without touching durable provider state.
            return
        try:
            # Read the call-thread's current nesting map or initialize one.
            depths = getattr(_JSON_GATE_LOCAL, "depths", {})
            # Reuse an already-held operating-system gate on a nested same-thread call.
            if depths.get(depth_key, 0):
                # Increment the exact root nesting depth before yielding.
                depths[depth_key] += 1
                # Retain the updated nesting map for public provider calls.
                _JSON_GATE_LOCAL.depths = depths
                try:
                    # Report immediate ownership while the outer call retains both locks.
                    yield True
                finally:
                    # Restore the previous nesting depth.
                    depths[depth_key] -= 1
                # Stop after the nested critical section.
                return
            # Attempt the stable reset-safe process lock first.
            with self._try_exclusive_process_file_lock(self.json_gate_path()) as stable_acquired:
                # Report active work elsewhere without touching reset-owned directories.
                if not stable_acquired:
                    # Return one pending ownership result.
                    yield False
                    # Stop before attempting the legacy wallet lock.
                    return
                # Refuse visibility while failed reset recovery still owns state.
                self._require_no_reset_recovery_locked()
                # Create only the data root needed for the legacy lock path.
                self.data_dir.mkdir(parents=True, exist_ok=True)
                # Attempt the shipped wallet lock second in the fixed lock order.
                with self._try_exclusive_process_file_lock(self.ledger_lock_path()) as legacy_acquired:
                    # Report active legacy work without reading action state.
                    if not legacy_acquired:
                        # Return one pending ownership result.
                        yield False
                        # Stop before provider readiness work.
                        return
                    # Recheck reset recovery after both exact locks are held.
                    self._require_no_reset_recovery_locked()
                    # Create remaining provider directories only under complete ownership.
                    self._ensure_ready_direct()
                    # Remove only stale provider-owned temporary files.
                    self._cleanup_game_action_temps_locked()
                    # Mark the two operating-system locks held for nested public calls.
                    depths[depth_key] = 1
                    # Publish nesting state to this thread.
                    _JSON_GATE_LOCAL.depths = depths
                    try:
                        # Transfer complete nonblocking ownership to the resolver.
                        yield True
                    finally:
                        # Remove the outermost marker before releasing process locks.
                        depths.pop(depth_key, None)
        finally:
            # Release the process-shared thread gate after every outcome.
            thread_gate.release()

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
        prefixes = ("journal.json.tmp-", "receipts.json.tmp-", "states.json.tmp-", "claims.json.tmp-")
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
        # Read the wallet document strictly so corruption never selects bootstrap defaults.
        return self._read_players_document(default_factory)

    # Save players without acquiring another gate or invoking recovery.
    def _save_players_document(self, state: dict) -> None:
        # Copy the state so callers do not observe schema mutation side effects.
        saved_state = dict(state)
        # Preserve the current schema version on every saved player document.
        saved_state["schema_version"] = SCHEMA_VERSION
        # Refuse any internal writer that attempts to publish non-cent wallet state.
        _validated_players_document(saved_state)
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

    # Scan or repair JSON wallet residue under the complete money-state gate. (STORAGE-015, LEDGER-036)
    def normalize_wallet_balances(self, *, apply: bool = False) -> dict:
        # Reject operator mutation attempted from inside a game-action planner.
        self._reject_planner_mutation()
        # Serialize the scan with every provider-local operation.
        with self.lock:
            # Serialize the pass with reset, wallet, ledger, and game-action writers across processes.
            with self._ledger_process_lock():
                # Converge any earlier durable money action before inspecting its wallet projection.
                self._recover_all_json_actions_locked()
                # Read the structurally strict document through the residue-aware operator boundary.
                state = self._read_normalizable_players_document()
                # Collect exact stored and normalized values without mutating the source yet.
                residues = []
                # Visit every wallet exactly once while the global gate remains held.
                for player in state["players"]:
                    # Decode the exact stored decimal value already accepted by the strict reader.
                    stored = _money_decimal(player["balance"])
                    # Derive the canonical cent value using the documented provider-neutral rule.
                    normalized = _quantized_money_decimal(stored)
                    # Record only values that contain genuine sub-cent residue.
                    if stored != normalized:
                        # Retain the row and exact decimal pair for an optional apply pass.
                        residues.append((player, stored, normalized))
                # Return the read-only scan result without writing players or ledger rows.
                if not apply:
                    # Publish bounded counts only, never player identities or stored values.
                    return {"provider": self.name, "checked": len(state["players"]), "residue_count": len(residues), "normalized_count": 0, "clean": not residues, "applied": False}
                # Refresh the append-only ledger identity cache before deterministic replay checks.
                self._ledger_rows()
                # Publish every required audit row before changing the compatible wallet document.
                for player, stored, normalized in residues:
                    # Build the deterministic ledger-visible operator adjustment.
                    event = _wallet_normalization_event(player["player_id"], stored, normalized)
                    # Reuse an earlier row when a prior process appended it before a stopped player write.
                    existing = self._ledger_cache_by_id.get(event["ledger_id"])
                    # Append only a previously unseen normalization identity.
                    if existing is None:
                        # Write the complete append-only evidence while the process gate is held.
                        self._append_jsonl(self.ledger_path(), event)
                        # Refresh the cache so later rows in this batch see the durable append.
                        self._ledger_rows()
                    else:
                        # Require the earlier deterministic row to describe this exact residue.
                        _validate_wallet_normalization_replay(existing, event)
                    # Replace the durable wallet value only after its audit evidence exists.
                    player["balance"] = _quantized_money(normalized)
                    # Record the operator pass as the latest wallet update.
                    player["updated_at"] = utc_now()
                # Publish the complete normalized player document once after all audit rows are durable.
                if residues:
                    # Use the existing atomic JSON replacement boundary.
                    self._save_players_document(state)
                # Prove the resulting in-memory document satisfies the ordinary exact-cent reader.
                _validated_players_document(state)
                # Return bounded completion evidence for the operator command.
                return {"provider": self.name, "checked": len(state["players"]), "residue_count": len(residues), "normalized_count": len(residues), "clean": True, "applied": True}

    # Insert one player through the deterministic provider-owned identity boundary.
    def insert_player(self, player: dict) -> dict:
        # Reuse the exactly-once insert-or-read semantics already required by invitations.
        return self.ensure_player(player)

    # Insert only missing bootstrap players under one JSON wallet boundary. (STORAGE-012, issue #431)
    def bootstrap_players(self, state: dict) -> None:
        # Reject bootstrap mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard the complete bootstrap batch from concurrent local threads.
        with self.lock:
            # Serialize bootstrap with every wallet action across processes.
            with self._json_global_gate():
                # Complete every recoverable action before adding missing wallets.
                self._recover_all_json_actions_locked()
                # Load the current document without inventing unrelated defaults.
                current = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Index durable identifiers so repeated or racing bootstrap calls are harmless.
                identifiers = {row.get("player_id") for row in current.get("players", []) if isinstance(row, dict)}
                # Track whether this call contributed any previously missing row.
                changed = False
                # Visit each bounded bootstrap row exactly once.
                for player in state.get("players", []):
                    # Ignore an already durable identifier without overwriting wallet or lifecycle fields.
                    if player.get("player_id") in identifiers:
                        # Continue to the remaining default rows.
                        continue
                    # Detach and cents-normalize the missing wallet before publication.
                    inserted = {**player, "balance": _quantized_money(player.get("balance", 0))}
                    # Append the validated row while the cross-process wallet gate remains held.
                    current["players"].append(inserted)
                    # Reserve the identifier against duplicates inside the same supplied batch.
                    identifiers.add(player.get("player_id"))
                    # Record that the normalized document must be published once.
                    changed = True
                # Persist only when at least one missing row was appended.
                if changed:
                    # Publish the complete JSON document atomically under the held wallet boundary.
                    self._save_players_document(current)

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
                        # Quantize every direct wallet update through the canonical cents boundary.
                        player["balance"] = _quantized_money(player.get("balance", 0))
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
                # Detach and cents-normalize the new wallet before publication.
                inserted = {**player, "balance": _quantized_money(player.get("balance", 0))}
                # Append the validated copy so caller mutation cannot alter persisted state after return.
                state["players"].append(inserted)
                # Persist the complete deterministic player document while the process lock remains held.
                self._save_players_document(state)
                # Return the newly committed compatible row.
                return dict(inserted)

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
                # Index the same row by immutable ledger identity for O(1) projection proof.
                self._ledger_cache_by_id[event["ledger_id"]] = event
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
        # Refresh the incremental ledger cache before checking immutable identity membership. (issue #432)
        self._ledger_rows()
        # Stop when both balance and ledger projection already completed earlier.
        if event["ledger_id"] in self._ledger_cache_by_id:
            # Treat the ledger row as proof that this action was fully projected.
            return
        # Load the current player document without invoking another process lock.
        state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
        # Find the wallet owned by the committed action.
        player = next((row for row in state.get("players", []) if row.get("player_id") == event["player_id"]), None)
        # Fail closed when recovery cannot locate the committed wallet.
        if player is None:
            # Preserve the journal for operator recovery instead of discarding money state.
            raise ConflictError("Committed ledger action references a missing player", {"ledger_id": event["ledger_id"], "player_id": event["player_id"]})
        # Normalize the currently projected fake-money balance.
        current_balance = _quantized_money(player.get("balance", 0))
        # Apply the committed balance transition when projection stopped before players.json.
        if current_balance == _quantized_money(event["balance_before"]):
            # Move the wallet to the committed post-transaction balance exactly once.
            player["balance"] = _quantized_money(event["balance_after"])
            # Stamp recovery as a player update for downstream admin views.
            player["updated_at"] = utc_now()
            # Persist the recovered wallet state before appending the missing ledger row.
            self._save_players_document(state)
        # Accept a balance that already reached the committed after-state before a lost response.
        elif current_balance != _quantized_money(event["balance_after"]):
            # Reject divergent state because guessing could duplicate or erase later money actions.
            raise ConflictError("Committed ledger action cannot be recovered from divergent wallet state", {"ledger_id": event["ledger_id"], "balance": current_balance})
        # Append the original committed event after the wallet transition is durable.
        self._append_jsonl(self.ledger_path(), event)

    # Read a file identity without requiring the file to exist. (issue #432)
    def _optional_file_stat(self, path: Path) -> tuple[int, int] | None:
        # Start protected stat logic so absent compatibility files remain ordinary.
        try:
            # Read the file size and nanosecond modification identity.
            stat = os.stat(path)
        # Treat a missing path as an absent optional source.
        except OSError:
            # Return no identity for an absent optional file.
            return None
        # Return the stable pair used by the provider-local cache guard.
        return stat.st_size, stat.st_mtime_ns

    # Add the in-memory pending set required for bounded crash recovery. (LEDGER-034)
    def _normalize_actions_registry(self, registry: Any) -> dict:
        # Fail closed when a durable registry is not the expected object shape.
        if not isinstance(registry, dict) or not isinstance(registry.get("actions", {}), dict):
            # Reject inconsistent money-action state instead of silently rearming identities.
            raise ConflictError("Ledger action index is inconsistent")
        # Preserve the versioned registry shape used by existing stores.
        registry.setdefault("schema_version", 1)
        # Preserve a monotonic next sequence even for a legacy empty snapshot.
        registry.setdefault("next_sequence", 1)
        # Index only unprojected identities so steady-state recovery is O(pending), not O(history).
        registry["_pending"] = {identity for identity, record in registry["actions"].items() if isinstance(record, dict) and record.get("projected") is not True}
        # Return the normalized mutable in-memory view.
        return registry

    # Apply one durable append-only action-journal record to the cached registry. (LEDGER-034)
    def _apply_action_journal_record(self, registry: dict, record: Any) -> None:
        # Reject malformed records before they can weaken exactly-once identity state.
        if not isinstance(record, dict) or record.get("op") not in {"commit", "project", "settled"} or not isinstance(record.get("identity"), str):
            # Fail closed because skipping a corrupt commit could duplicate a money action.
            raise ConflictError("Ledger action journal is inconsistent")
        # Read the unambiguous canonical identity shared by both record kinds.
        identity = record["identity"]
        # Apply a logical commit before any compatible wallet projection.
        if record["op"] == "commit":
            # Read the immutable action record carried by the commit line.
            action = record.get("action")
            # Require every committed line to carry a structured event and monotonic sequence.
            if not isinstance(action, dict) or not isinstance(action.get("event"), dict) or not isinstance(action.get("sequence"), int):
                # Preserve the journal for operator recovery instead of guessing missing money state.
                raise ConflictError("Ledger action journal is inconsistent")
            # Read any previously committed identity from the legacy snapshot or earlier journal tail.
            existing = registry["actions"].get(identity)
            # Compare immutable fields while ignoring a later in-memory projection acknowledgement.
            comparable_existing = ({**existing, "projected": False} if isinstance(existing, dict) else existing)
            # Permit only byte-semantic duplicate commit records, which are harmless after a lost acknowledgement.
            if existing is not None and comparable_existing != action:
                # Reject two different immutable actions under one canonical identity.
                raise ConflictError("Ledger action journal identity conflicts", {"action_key": action.get("action_key")})
            # Publish the immutable action record into the provider-owned point index.
            registry["actions"][identity] = action
            # Mark the identity pending until a durable project record follows.
            registry["_pending"].add(identity)
            # Advance the next sequence beyond every accepted durable commit.
            registry["next_sequence"] = max(int(registry.get("next_sequence", 1)), int(action["sequence"]) + 1)
            # Stop after applying the commit record.
            return
        # Rebuild one compacted settled action from its immutable ledger row.
        if record["op"] == "settled":
            # Require compact records to retain monotonic order and ledger identity.
            if not isinstance(record.get("sequence"), int) or not isinstance(record.get("ledger_id"), str):
                # Fail closed on a compact record that cannot reconstruct exact action state.
                raise ConflictError("Ledger action journal is inconsistent")
            # Decode the canonical identity tuple carried unchanged through compaction.
            try:
                # Parse the unambiguous player, scope, and action-key fragments.
                identity_parts = json.loads(identity)
            # Normalize invalid identity JSON to the action-index recovery boundary.
            except json.JSONDecodeError:
                # Preserve compacted bytes for operator inspection.
                raise ConflictError("Ledger action journal is inconsistent") from None
            # Require exactly three string identity fragments.
            if not isinstance(identity_parts, list) or len(identity_parts) != 3 or any(not isinstance(part, str) for part in identity_parts):
                # Reject an identity that cannot match the provider write seam.
                raise ConflictError("Ledger action journal is inconsistent")
            # Refresh the append-only ledger cache before resolving the compact reference.
            self._ledger_rows()
            # Resolve the immutable event by its provider-owned ledger identity.
            event = self._ledger_cache_by_id.get(record["ledger_id"])
            # Require every settled compact record to reference one durable compatible row.
            if not isinstance(event, dict):
                # Fail closed instead of accepting an identity whose replay proof is missing.
                raise ConflictError("Ledger action journal requires operator recovery")
            # Read storage-owned fingerprint evidence from the committed event.
            details = event.get("details") if isinstance(event.get("details"), dict) else {}
            # Reconstruct the in-memory action record without retaining duplicate event bytes on disk.
            compact_action = {"sequence": record["sequence"], "player_id": identity_parts[0], "action_scope": identity_parts[1], "action_key": identity_parts[2], "action_fingerprint": details.get("ledger_action_fingerprint"), "projected": True, "event": event}
            # Read an optional matching legacy snapshot record.
            existing = registry["actions"].get(identity)
            # Reject a snapshot/journal disagreement on immutable ledger identity.
            if isinstance(existing, dict) and isinstance(existing.get("event"), dict) and existing["event"].get("ledger_id") != event.get("ledger_id"):
                # Preserve both sources for operator recovery.
                raise ConflictError("Ledger action journal identity conflicts", {"action_key": identity_parts[2]})
            # Publish the reconstructed point-index record.
            registry["actions"][identity] = compact_action
            # Keep the settled identity out of the bounded recovery set.
            registry["_pending"].discard(identity)
            # Advance the next sequence beyond the compact record.
            registry["next_sequence"] = max(int(registry.get("next_sequence", 1)), int(record["sequence"]) + 1)
            # Stop after applying the compact settled record.
            return
        # Read the corresponding committed action before accepting its projection marker.
        action = registry["actions"].get(identity)
        # Require a project record to refer to one known immutable commit.
        if not isinstance(action, dict) or not isinstance(action.get("event"), dict):
            # Fail closed on orphan projection markers.
            raise ConflictError("Ledger action journal is inconsistent")
        # Require the marker to bind the exact committed ledger event identity.
        if record.get("ledger_id") != action["event"].get("ledger_id"):
            # Reject a marker that could acknowledge a different wallet transition.
            raise ConflictError("Ledger action journal projection conflicts", {"action_key": action.get("action_key")})
        # Mark the compatible-file projection complete after its durable marker is read.
        action["projected"] = True
        # Remove the settled identity from the bounded recovery set.
        registry["_pending"].discard(identity)

    # Parse complete append-only journal bytes and apply them in durable order. (LEDGER-034)
    def _apply_action_journal_bytes(self, registry: dict, payload: bytes) -> None:
        # Require a newline-terminated tail because a partial commit cannot be ignored safely.
        if payload and not payload.endswith(b"\n"):
            # Fail closed until an operator resolves the interrupted append.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Visit each physical record in append order.
        for line in payload.splitlines():
            # Reject blank records because the format is one object per line.
            if not line:
                # Preserve the journal rather than accepting an ambiguous gap.
                raise ConflictError("Ledger action journal is inconsistent")
            # Start protected JSON decoding for one durable line.
            try:
                # Decode the UTF-8 JSON object without replacement semantics.
                record = json.loads(line.decode("utf-8"))
            # Normalize malformed bytes to the public fail-closed conflict boundary.
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Preserve the journal for explicit operator recovery.
                raise ConflictError("Ledger action journal is inconsistent") from None
            # Apply the validated record to the in-memory index.
            self._apply_action_journal_record(registry, record)

    # Read the committed-action registry from one legacy snapshot plus an incremental journal. (LEDGER-034)
    def _read_actions_registry(self) -> Any:
        # Discover interrupted compaction files before trusting either durable source.
        temporaries = tuple(self.data_dir.glob("ledger_actions.jsonl.tmp-*"))
        # Fail closed while any unpublished checkpoint remains unresolved.
        if temporaries:
            # Preserve the old journal and temporary bytes for operator comparison.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Capture the optional legacy snapshot identity before deciding whether the cache is reusable.
        snapshot_stat = self._optional_file_stat(self.ledger_actions_path())
        # Capture the optional append-only journal identity under the held process lock.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Require an absent journal to stay absent, or an existing journal to grow monotonically.
        journal_monotonic = (journal_stat is None and self._actions_cache_journal_stat is None) or (journal_stat is not None and journal_stat[0] >= self._actions_cache_journal_offset)
        # Reuse the cached registry when the immutable snapshot is unchanged and the journal only grew.
        cache_reusable = self._actions_cache_registry is not None and self._actions_cache_snapshot_stat == snapshot_stat and journal_monotonic
        # Refresh only the new journal tail for the ordinary multi-process append case.
        if cache_reusable:
            # Return immediately when the journal identity is byte-for-byte unchanged.
            if self._actions_cache_journal_stat == journal_stat:
                # Reuse the existing provider-owned point index.
                return self._actions_cache_registry
            # Reject a same-size rewrite because append-only history must never change in place.
            if journal_stat is not None and journal_stat[0] == self._actions_cache_journal_offset:
                # Force a complete validation rebuild below.
                cache_reusable = False
            # Apply only bytes appended by another process when the file grew monotonically.
            elif journal_stat is not None:
                # Open the journal in binary mode so offsets are platform-independent.
                with self.ledger_action_journal_path().open("rb") as handle:
                    # Seek to the first unapplied durable byte.
                    handle.seek(self._actions_cache_journal_offset)
                    # Read exactly the newly observed append-only tail.
                    payload = handle.read(journal_stat[0] - self._actions_cache_journal_offset)
                # Apply the complete tail to the existing point index.
                self._apply_action_journal_bytes(self._actions_cache_registry, payload)
                # Advance the parsed offset to the observed durable file size.
                self._actions_cache_journal_offset = journal_stat[0]
                # Bind the refreshed cache to the new journal identity.
                self._actions_cache_journal_stat = journal_stat
                # Return the incrementally refreshed registry.
                return self._actions_cache_registry
            # Return the cached snapshot-derived registry when no journal exists.
            elif journal_stat is None:
                # Keep the zero journal offset bound to an absent journal.
                self._actions_cache_journal_offset = 0
                # Remember that no journal identity exists.
                self._actions_cache_journal_stat = None
                # Return the cached registry without reparsing the snapshot.
                return self._actions_cache_registry
        # Build one call-local sentinel that only legacy snapshot corruption can return.
        sentinel = object()
        # Read the existing compatible snapshot when one exists.
        parsed = self._read_json(self.ledger_actions_path(), lambda: sentinel) if snapshot_stat is not None else self._empty_action_registry()
        # Refuse to forget durable identities when the legacy snapshot cannot be decoded.
        if parsed is sentinel:
            # Drop process-local cache state before surfacing the recovery boundary.
            self._drop_actions_cache()
            # Fail closed instead of returning an empty action registry.
            raise ConflictError("Ledger action index requires operator recovery")
        # Normalize the snapshot and build its bounded pending set.
        registry = self._normalize_actions_registry(parsed)
        # Apply the complete journal after the legacy snapshot baseline.
        if journal_stat is not None:
            # Read the exact bytes observed by the pre-read stat call.
            with self.ledger_action_journal_path().open("rb") as handle:
                # Read only the stable length captured while the process lock is held.
                payload = handle.read(journal_stat[0])
            # Apply every complete append-only record in order.
            self._apply_action_journal_bytes(registry, payload)
        # Cache the combined provider-owned action index.
        self._actions_cache_registry = registry
        # Bind the cache to the legacy snapshot identity.
        self._actions_cache_snapshot_stat = snapshot_stat
        # Record the complete applied journal length.
        self._actions_cache_journal_offset = journal_stat[0] if journal_stat is not None else 0
        # Bind the cache to the append-only journal identity.
        self._actions_cache_journal_stat = journal_stat
        # Treat a completely validated restart image as the next bounded-growth baseline.
        self._actions_cache_compaction_floor = journal_stat[0] if journal_stat is not None else 0
        # Return the combined compatible registry.
        return registry

    # Durably append one action record and update the already-locked cache. (LEDGER-034)
    def _append_action_journal_record(self, registry: dict, record: dict) -> None:
        # Reject planner-side mutation before opening the durable journal.
        self._reject_planner_mutation()
        # Ensure the ordinary provider directories exist before appending.
        self.ensure_ready()
        # Serialize the record deterministically with one platform-independent newline.
        payload = (json.dumps(record, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        # Create the target parent without touching any unrelated data path.
        self.ledger_action_journal_path().parent.mkdir(parents=True, exist_ok=True)
        # Open the append-only journal in binary mode so byte offsets and newlines are stable.
        with self.ledger_action_journal_path().open("ab") as handle:
            # Append the complete logical commit or projection marker in one write call.
            handle.write(payload)
            # Flush Python buffering before requesting filesystem durability.
            handle.flush()
            # Require the journal bytes to reach the operating-system durable boundary.
            os.fsync(handle.fileno())
        # Apply the just-persisted record to the caller's in-memory registry.
        self._apply_action_journal_record(registry, record)
        # Refresh the journal identity after the durable append.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Fail closed if the just-written journal cannot be stated.
        if journal_stat is None:
            # Preserve all files for operator recovery.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Cache the caller registry containing this exact durable record.
        self._actions_cache_registry = registry
        # Bind the cache to the unchanged legacy snapshot identity.
        self._actions_cache_snapshot_stat = self._optional_file_stat(self.ledger_actions_path())
        # Advance the parsed offset to the complete durable journal size.
        self._actions_cache_journal_offset = journal_stat[0]
        # Bind the cache to the current journal identity.
        self._actions_cache_journal_stat = journal_stat

    # Rewrite a bounded journal checkpoint without duplicate settled event payloads. (LEDGER-034)
    def _compact_action_journal(self, registry: dict) -> None:
        # Order records by their monotonic logical commit sequence.
        ordered = sorted(registry.get("actions", {}).items(), key=lambda item: int(item[1].get("sequence", 0)))
        # Build one compact or pending record for every durable action identity.
        records = []
        # Visit each committed identity exactly once.
        for identity, action in ordered:
            # Store only a ledger reference after compatible projection is durable.
            if action.get("projected") is True:
                # Append one compact settled record without duplicate event bytes.
                records.append({"op": "settled", "identity": identity, "sequence": int(action["sequence"]), "ledger_id": action["event"]["ledger_id"]})
            # Preserve the complete immutable event while crash recovery remains pending.
            else:
                # Append one full logical commit record for the unresolved crash window.
                records.append({"op": "commit", "identity": identity, "action": action})
        # Serialize every checkpoint record with stable binary newlines.
        payload = b"".join((json.dumps(record, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8") for record in records)
        # Build a process-and-thread-unique sibling used for atomic publication.
        tmp = self.ledger_action_journal_path().with_suffix(f".jsonl.tmp-{os.getpid()}-{threading.get_ident()}")
        # Write the complete checkpoint without exposing partial replacement bytes.
        with tmp.open("wb") as handle:
            # Publish the exact compact payload into the private temporary file.
            handle.write(payload)
            # Flush Python buffering before the durability boundary.
            handle.flush()
            # Require the complete compact checkpoint to reach durable storage.
            os.fsync(handle.fileno())
        # Retry bounded Windows sharing violations while preserving atomic replacement.
        for attempt in range(20):
            # Start protected replacement so transient scanner handles can release.
            try:
                # Atomically replace the old append-only history with its equivalent checkpoint.
                tmp.replace(self.ledger_action_journal_path())
                # Stop after successful checkpoint publication.
                break
            # Handle only transient Windows sharing failures.
            except PermissionError:
                # Surface the final failure without deleting recovery bytes.
                if attempt == 19:
                    # Re-raise the original filesystem failure.
                    raise
                # Wait one bounded increasing interval before retrying.
                time.sleep(0.01 * (attempt + 1))
        # Read the newly published journal identity.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Require the checkpoint file to remain visible after atomic publication.
        if journal_stat is None:
            # Fail closed while preserving the provider directory for recovery.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Keep the already-equivalent in-memory point index cached.
        self._actions_cache_registry = registry
        # Bind the cache to the unchanged legacy compatibility snapshot.
        self._actions_cache_snapshot_stat = self._optional_file_stat(self.ledger_actions_path())
        # Mark the entire compact checkpoint as parsed.
        self._actions_cache_journal_offset = journal_stat[0]
        # Bind the cache to the compact journal identity.
        self._actions_cache_journal_stat = journal_stat
        # Measure the next compaction only after another full threshold of append-only growth.
        self._actions_cache_compaction_floor = journal_stat[0]

    # Compact only after a bounded amount of append-only growth. (LEDGER-034)
    def _maybe_compact_action_journal(self, registry: dict) -> None:
        # Read the current journal identity after a completed projection marker.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Keep ordinary actions append-only until the configured growth threshold is reached.
        if journal_stat is None or journal_stat[0] - self._actions_cache_compaction_floor < _LEDGER_ACTION_COMPACT_BYTES:
            # Return without any whole-history write in the common path.
            return
        # Publish one compact equivalent checkpoint at the bounded threshold.
        self._compact_action_journal(registry)

    # Recover only unprojected journaled actions before allowing a later wallet mutation. (LEDGER-034)
    def _recover_committed_actions(self, registry: dict | None = None) -> dict:
        # Load the combined snapshot/journal index when the caller did not pass one.
        registry = registry or self._read_actions_registry()
        # Read the canonical action map from the normalized registry.
        actions = registry.get("actions", {})
        # Resolve only pending identities in original monotonic order.
        pending = sorted((actions[identity] for identity in tuple(registry.get("_pending", set()))), key=lambda item: int(item.get("sequence", 0)))
        # Replay each crash-window transition exactly once.
        for action in pending:
            # Project the immutable event into compatible wallet and ledger files.
            self._project_committed_action(action["event"])
            # Rebuild the canonical identity used by the journal marker.
            identity = self._action_identity(action["player_id"], action["action_scope"], action["action_key"])
            # Durably acknowledge the completed projection without rewriting historical actions.
            self._append_action_journal_record(registry, {"op": "project", "identity": identity, "ledger_id": action["event"]["ledger_id"]})
        # Compact only after all recoverable actions have durable projection markers.
        self._maybe_compact_action_journal(registry)
        # Return the settled registry so the transaction can reuse its in-memory view.
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
        before = _quantized_money(player.get("balance", 0))
        # Compute the balance after the proposed mutation.
        after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
        # Reject transactions that would overdraw the fake-money wallet.
        if after < 0:
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
        amount = _quantized_money(amount)
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
        amount = _quantized_money(amount)
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
                before = _quantized_money(player.get("balance", 0))
                # Compute the balance after the proposed mutation.
                after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
                # Reject actions that would overdraw the fake-money wallet.
                if after < 0:
                    # Raise the standard insufficient-funds error before committing the identity.
                    raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
                # Build the immutable event returned by every later replay.
                event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, committed_details)
                # Allocate the next monotonic recovery sequence.
                sequence = int(registry.get("next_sequence", 1))
                # Build the immutable action record stored before compatible projection.
                action = {"sequence": sequence, "player_id": player_id, "action_scope": scope, "action_key": action_key, "action_fingerprint": fingerprint, "projected": False, "event": event}
                # Append the logical commit durably without rewriting prior action history. (LEDGER-034)
                self._append_action_journal_record(registry, {"op": "commit", "identity": identity, "action": action})
                # Project the committed transition into the compatible player and ledger files.
                self._project_committed_action(event)
                # Append one compact marker after both compatible projections succeed. (LEDGER-034)
                self._append_action_journal_record(registry, {"op": "project", "identity": identity, "ledger_id": event["ledger_id"]})
                # Compact only after bounded journal growth and a complete settled action.
                self._maybe_compact_action_journal(registry)
                # Return the newly committed event with a non-replay marker.
                return event, False

    # Find one committed JSON ledger action without scanning ledger history. (LEDGER-033)
    def find_ledger_action(self, player_id: str, game: str | None, action_key: str) -> dict | None:
        # Normalize the indexed caller-owned key before durable lookup.
        action_key = _normalize_action_key(action_key)
        # Normalize the game-or-core namespace exactly as the write path does.
        scope = _action_scope(game)
        # Build the identical unambiguous key used by transact_ledger_once.
        identity = self._action_identity(player_id, scope, action_key)
        # Serialize recovery and lookup with local provider operations.
        with self.lock:
            # Serialize recovery and lookup with independent JSON provider processes.
            with self._ledger_process_lock():
                # Complete every durable logical commit before exposing its event.
                self._recover_all_json_actions_locked()
                # Read the stat-guarded action index once after recovery settles it.
                registry = self._read_actions_registry()
                # Read the indexed record without traversing unrelated actions.
                record = registry.get("actions", {}).get(identity) if isinstance(registry, dict) else None
                # Report a miss without falling back to unbounded ledger history.
                if not isinstance(record, dict):
                    # Preserve the public optional-result contract.
                    return None
                # Read the immutable committed event stored by the logical action journal.
                event = record.get("event")
                # Fail closed when an indexed record lacks a structured event.
                if not isinstance(event, dict):
                    # Reject corrupt action-index state instead of authorizing a fresh write.
                    raise ConflictError("Ledger action index is inconsistent", {"action_key": action_key})
                # Return a detached event so readers cannot mutate the provider cache.
                return copy.deepcopy(event)

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


# Seed players idempotently through the configured provider.
def bootstrap_players(default_factory: Callable[[], dict]) -> None:
    # Get the active storage provider.
    provider = get_storage_provider()
    # Ensure backing storage exists before checking player bootstrap state.
    provider.ensure_ready()
    # Delegate the complete row set so each provider owns one race-free bootstrap boundary. (issue #431)
    provider.bootstrap_players(default_factory())
