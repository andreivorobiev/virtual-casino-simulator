# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""JSON filesystem, locking, cache, and planner infrastructure for storage providers."""

# Import annotations so the mixin can expose concrete path and factory types.
from __future__ import annotations
# Import portable operating-system error numbers for exact lock-contention classification.
import errno
# Import hashing so forensic wallet evidence and private roots retain stable identities.
import hashlib
# Import JSON parsing and encoding for exact durable document behavior.
import json
# Import operating-system primitives for containment, locking, fsync, and atomic publication.
import os
# Import file-copy support so ordinary corrupt non-wallet documents preserve existing evidence.
import shutil
# Import thread primitives for shared root gates and atomic temporary names.
import threading
# Import bounded delays for transient Windows replacement conflicts.
import time
# Import context managers for process, provider, and planner lock boundaries.
from contextlib import contextmanager
# Import concrete local paths used by the provider substrate.
from pathlib import Path
# Import generic document and factory types shared by inherited provider methods.
from typing import Any, Callable

# Import runtime roots and schema identity used by local JSON readiness and wallet validation.
from casino.config import DATA_DIR, LOG_DIR, SCHEMA_VERSION
# Import provider-neutral wallet validators used before any money state is exposed.
from casino.core.storage_base import _normalizable_players_document, _validated_players_document
# Import fixed public error boundaries without leaking filesystem details.
from casino.errors import ConflictError, ValidationError

# Guard construction of process-shared JSON root locks.
_JSON_GATE_REGISTRY_LOCK = threading.RLock()
# Share one reentrant thread gate across every provider instance for the same JSON root.
_JSON_GATE_LOCKS: dict[str, threading.RLock] = {}
# Track nested gate and planner state without leaking it across threads.
_JSON_GATE_LOCAL = threading.local()


# Return the process-shared reentrant lock for one exact JSON data root.
def _json_gate_lock(root_key: str) -> threading.RLock:
    # Serialize first construction so provider instances cannot receive different locks.
    with _JSON_GATE_REGISTRY_LOCK:
        # Reuse an existing lock or construct the sole lock for this root.
        return _JSON_GATE_LOCKS.setdefault(root_key, threading.RLock())


# Define the filesystem and concurrency substrate inherited by the concrete JSON provider.
class JsonInfrastructureMixin:
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
