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
# Import required dependency so this module can use structured configuration values.
from dataclasses import dataclass
# Import required dependency so decimal balances use one explicit cents rule.
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
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
# Import the immutable route-free game-action execution and resolution contract.
from casino.core.game_action import GameActionExecutor, GameActionIdentity, GameActionMovement, GameActionPlan, GameActionReceipt, GameActionResolution, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, canonical_json_bytes, validate_execution_request, validate_resolution_request
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
# Track active MySQL planners separately from filesystem-root gate ownership.
_MYSQL_PLANNER_LOCAL = threading.local()
# Serialize process-local reset target registration across equivalent provider instances.
_MYSQL_RESET_REGISTRY_LOCK = threading.RLock()
# Track targets whose retained session currently owns the reset lifecycle.
_MYSQL_RESET_TARGETS: set[tuple[str, int, str]] = set()
# Version the provider-private durable action files independently from public storage.
_GAME_ACTION_STORAGE_VERSION = 1
# Store the canonical fake-money quantum shared by migration and ordinary writes. (LEDGER-036)
_MONEY_QUANTUM = Decimal("0.01")
# Bound fake-money values to the signed-cent range already enforced by game actions.
_MAX_MONEY = Decimal("90000000000000000")
# Version epoch-scoped lifecycle registries without rewriting legacy epoch-one bytes.
_GAME_ACTION_EPOCH_STORAGE_VERSION = 2
# Bound reset epochs to the signed BIGINT range shared by JSON and MySQL providers.
_GAME_ACTION_MAX_EPOCH = (1 << 63) - 1
# Enumerate the only durable recovery stages accepted from the private journal.
_GAME_ACTION_STAGES = {"prepared", "planned", "wallet_applied", "ledger_applied", "state_applied", "receipt_committed"}
# Compact the append-only ledger-action journal only after a bounded growth interval. (LEDGER-034)
_LEDGER_ACTION_COMPACT_BYTES = 512 * 1024


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


# Decode one numeric money value without silently accepting strings or booleans. (LEDGER-036)
def _money_decimal(value: Any) -> Decimal:
    # Accept only the numeric shapes already supported by JSON and MySQL providers.
    if type(value) not in {int, float, Decimal}:
        # Refuse values whose meaning depends on implicit coercion.
        raise ValidationError("Money value must be a finite number")
    try:
        # Convert through decimal text so persisted cents retain their intended value.
        decoded = Decimal(str(value))
    # Collapse malformed or unbounded conversions into one public validation boundary.
    except (InvalidOperation, ValueError, OverflowError):
        # Return no source value in the error message.
        raise ValidationError("Money value must be a finite number") from None
    # Reject infinity, NaN, or values outside the existing signed-cent range.
    if not decoded.is_finite() or abs(decoded) > _MAX_MONEY:
        # Preserve the same value-free validation diagnostic.
        raise ValidationError("Money value must be a finite number")
    # Return the exact decimal supplied by the caller or provider.
    return decoded


# Quantize one signed money value to the canonical integer-cent boundary. (LEDGER-036)
def _quantized_money_decimal(value: Any) -> Decimal:
    # Decode the finite bounded value before applying the documented rounding rule.
    decoded = _money_decimal(value)
    try:
        # Use deterministic half-even cents so every provider publishes the same result.
        return decoded.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)
    # Normalize decimal-context failures to the same bounded validation error.
    except InvalidOperation:
        # Avoid returning the rejected value or provider representation.
        raise ValidationError("Money value must be a finite number") from None


# Convert one signed money value into the existing JSON/API float shape at exact cents. (LEDGER-036)
def _quantized_money(value: Any) -> float:
    # Convert only after Decimal quantization so binary float residue cannot select a stored cent.
    return float(_quantized_money_decimal(value))


# Validate the wallet document shape used only by the explicit residue-normalization tool. (STORAGE-015)
def _normalizable_players_document(value: Any) -> dict:
    # Require the same durable top-level object and player collection as ordinary reads.
    if type(value) is not dict or type(value.get("players")) is not list:
        # Preserve structurally corrupt money state for operator recovery.
        raise ConflictError("Wallet storage requires operator recovery")
    # Track identities so the tool never guesses between duplicate wallets.
    player_ids = set()
    # Validate every row while deliberately allowing only finite sub-cent numeric residue.
    for player in value["players"]:
        # Require the provider-neutral player mapping shape.
        if type(player) is not dict:
            # Refuse malformed rows without publishing a partial repair.
            raise ConflictError("Wallet storage requires operator recovery")
        # Read and validate the unique durable wallet identity.
        player_id = player.get("player_id")
        # Reject absent, blank, non-string, or duplicate identifiers.
        if type(player_id) is not str or not player_id.strip() or player_id in player_ids:
            # Keep the complete source unchanged for explicit operator recovery.
            raise ConflictError("Wallet storage requires operator recovery")
        # Reserve the validated identity before inspecting its money value.
        player_ids.add(player_id)
        try:
            # Decode the exact stored number without rounding it yet.
            balance = _money_decimal(player.get("balance"))
        # Normalize public validation failures to the provider-owned recovery boundary.
        except ValidationError:
            # Preserve malformed money state rather than guessing a repair.
            raise ConflictError("Wallet storage requires operator recovery") from None
        # Reject negative wallets even when their only defect is fractional residue.
        if balance < 0:
            # Keep insolvent state unavailable for manual accounting review.
            raise ConflictError("Wallet storage requires operator recovery")
    # Return the unchanged document for an explicit scan or normalization pass.
    return value


# Validate the provider-neutral wallet document before any balance is exposed or mutated. (STORAGE-014)
def _validated_players_document(value: Any) -> dict:
    # Require the durable top-level object and player collection without fallback normalization.
    if type(value) is not dict or type(value.get("players")) is not list:
        # Refuse malformed money state through one value-free recovery boundary.
        raise ConflictError("Wallet storage requires operator recovery")
    # Track durable player identities so ambiguous duplicate wallets cannot be selected.
    player_ids = set()
    # Validate every stored wallet row before returning any part of the document.
    for player in value["players"]:
        # Require the mapping shape used by both storage providers.
        if type(player) is not dict:
            # Preserve malformed state for operator-led recovery.
            raise ConflictError("Wallet storage requires operator recovery")
        # Accept only one non-empty string identity per durable wallet.
        player_id = player.get("player_id")
        # Reject absent, non-string, blank, or duplicate wallet identities.
        if type(player_id) is not str or not player_id.strip() or player_id in player_ids:
            # Keep the invalid document unavailable instead of guessing an owner.
            raise ConflictError("Wallet storage requires operator recovery")
        # Reserve the identity before validating its money value.
        player_ids.add(player_id)
        # Read the stored balance without accepting booleans or string coercion.
        balance = player.get("balance")
        # Support JSON integers/floats and MySQL Decimal values only.
        if type(balance) not in {int, float, Decimal}:
            # Refuse a value whose money meaning depends on coercion.
            raise ConflictError("Wallet storage requires operator recovery")
        try:
            # Convert through the canonical money decoder before exact-cent validation.
            scaled = _money_decimal(balance) * 100
        # Collapse malformed or unbounded numeric conversions into the fixed boundary.
        except ValidationError:
            # Return no stored value, path, or parser detail.
            raise ConflictError("Wallet storage requires operator recovery") from None
        # Require a finite, nonnegative, exact-cent balance inside the signed ledger range.
        if not scaled.is_finite() or scaled != scaled.to_integral_value() or not 0 <= scaled <= 9_000_000_000_000_000_000:
            # Preserve impossible wallet money for explicit recovery.
            raise ConflictError("Wallet storage requires operator recovery")
    # Return the unchanged validated document to the provider caller.
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

    # Load the player document shape used by the existing players API.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Raise because concrete providers must map their own storage rows.
        raise NotImplementedError

    # Scan or normalize durable wallet balances through one provider-owned boundary. (STORAGE-015)
    def normalize_wallet_balances(self, *, apply: bool = False) -> dict:
        # Raise because concrete providers must preserve their own locking and audit semantics.
        raise NotImplementedError

    # Insert one new player through a row-scoped, lock-correct provider boundary.
    def insert_player(self, player: dict) -> dict:
        # Raise because concrete providers must serialize player creation.
        raise NotImplementedError

    # Insert only missing bootstrap rows without replacing existing player state.
    def bootstrap_players(self, state: dict) -> None:
        # Raise because concrete providers must make bootstrap idempotent.
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

    # Find one committed storage action through the provider's canonical identity index. (LEDGER-033)
    def find_ledger_action(self, player_id: str, game: str | None, action_key: str) -> dict | None:
        # Raise because concrete providers must implement their own indexed identity lookup.
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
                # Converge every recoverable action before retiring its mutable epoch.
                self._recover_all_json_actions_locked()
                # Read the exact ready epoch before creating rollback material.
                epoch_state = self._read_game_action_epoch()
                # Refuse nested or stale reset ownership.
                if epoch_state["phase"] != "ready" or epoch_state["current_epoch"] >= _GAME_ACTION_MAX_EPOCH:
                    # Keep every provider byte unchanged at the fixed recovery boundary.
                    raise ConflictError("Game action reset requires operator recovery")
                # Capture the epoch that remains immutable history after this reset.
                current_epoch = epoch_state["current_epoch"]
                # Validate and retain every committed receipt across the reset.
                receipt_registry, _receipts = self._read_game_action_receipts(current_epoch)
                # Validate and retain every execute or uncommitted claim across the reset.
                claim_registry, _claims = self._read_game_action_claims(current_epoch)
                # Convert legacy epoch-one receipts only inside the reset transaction.
                if receipt_registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION:
                    # Preserve each serialized legacy receipt unchanged under epoch one.
                    receipt_registry = {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "receipts_by_epoch": {"1": copy.deepcopy(receipt_registry["receipts"])}}
                # Convert legacy epoch-one claims only inside the reset transaction.
                if claim_registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION:
                    # Preserve each serialized legacy claim unchanged under epoch one.
                    claim_registry = {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "claims_by_epoch": {"1": copy.deepcopy(claim_registry["claims"])}}
                # Derive the next namespace without permitting wraparound.
                next_epoch = current_epoch + 1
                # Snapshot complete pre-reset bytes before destructive mutation.
                backup = self._create_reset_backup_locked()
                # Capture any reset or caller-body failure without releasing either gate.
                failure = None
                try:
                    # Clear provider state without replacing either lock identity.
                    self._reset_locked()
                    # Restore immutable receipt history after mutable state is cleared.
                    self._write_game_action_json(self.game_action_receipts_path(), receipt_registry)
                    # Restore immutable claim and tombstone history beside receipts.
                    self._write_game_action_json(self.game_action_claims_path(), claim_registry)
                    # Publish the new namespace as unavailable throughout caller bootstrap.
                    self._write_game_action_epoch(current_epoch=next_epoch, phase="resetting")
                    # Yield so app bootstrap writes remain inside the same reentrant boundary.
                    yield self
                    # Release the exact bootstrapped namespace only after the caller body succeeds.
                    self._write_game_action_epoch(current_epoch=next_epoch, phase="ready")
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

    # Return the implicit legacy epoch state used before the first successful reset.
    def _empty_game_action_epoch(self) -> dict:
        # Preserve existing epoch-one lifecycle files without an eager rewrite.
        return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "current_epoch": 1, "phase": "ready"}

    # Read and validate the provider-private reset epoch state.
    def _read_game_action_epoch(self) -> dict:
        # Decode the epoch control file or project the compatible legacy epoch-one default.
        state = self._read_game_action_json(self.game_action_epoch_path(), self._empty_game_action_epoch)
        # Require the exact finite singleton state shape.
        if type(state) is not dict or set(state) != {"current_epoch", "phase", "schema_version"}:
            # Preserve malformed control bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the exact private epoch-state schema version.
        if type(state["schema_version"]) is not int or state["schema_version"] != _GAME_ACTION_STORAGE_VERSION:
            # Reject unknown durable epoch semantics.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one bounded non-coercible current epoch.
        if type(state["current_epoch"]) is not int or not 1 <= state["current_epoch"] <= _GAME_ACTION_MAX_EPOCH:
            # Refuse missing, boolean, zero, negative, or overflowing epochs.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one finite reset readiness phase.
        if type(state["phase"]) is not str or state["phase"] not in {"ready", "resetting"}:
            # Reject unknown lifecycle visibility states.
            raise ConflictError("Game action storage requires operator recovery")
        # Return a detached plain state for caller-owned phase transitions.
        return dict(state)

    # Publish one exact provider-private reset epoch state atomically.
    def _write_game_action_epoch(self, *, current_epoch: int, phase: str) -> None:
        # Validate the epoch before writing any control bytes.
        if type(current_epoch) is not int or not 1 <= current_epoch <= _GAME_ACTION_MAX_EPOCH:
            # Fail closed rather than wrapping a durable namespace.
            raise ConflictError("Game action storage requires operator recovery")
        # Accept only the two reviewed visibility phases.
        if phase not in {"ready", "resetting"}:
            # Reject internal phase drift before publication.
            raise ConflictError("Game action storage requires operator recovery")
        # Atomically persist the complete bounded control document.
        self._write_game_action_json(
            self.game_action_epoch_path(),
            {"schema_version": _GAME_ACTION_STORAGE_VERSION, "current_epoch": current_epoch, "phase": phase},
        )

    # Require the current JSON lifecycle namespace to be available for actions.
    def _ready_game_action_epoch(self) -> int:
        # Read the exact durable singleton state under the caller's global gate.
        state = self._read_game_action_epoch()
        # Refuse action visibility during an incomplete reset.
        if state["phase"] != "ready":
            # Preserve reset-owned state without creating a claim.
            raise ConflictError("Game action reset is in progress")
        # Return the bounded current namespace.
        return state["current_epoch"]

    # Return the empty private receipt registry shape for one current epoch.
    def _empty_game_action_receipts(self, reset_epoch: int = 1) -> dict:
        # Preserve the exact legacy container only for the implicit first epoch.
        if reset_epoch == 1:
            # Retain backwards-compatible receipt bytes before any reset.
            return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "receipts": {}}
        # Use the epoch-scoped registry after the first successful reset.
        return {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "receipts_by_epoch": {str(reset_epoch): {}}}

    # Read and fully validate the immutable receipt registry.
    def _read_game_action_receipts(self, reset_epoch: int = 1) -> tuple[dict, dict[str, GameActionReceipt]]:
        # Strictly decode the registry without repairing corrupt bytes.
        registry = self._read_game_action_json(self.game_action_receipts_path(), lambda: self._empty_game_action_receipts(reset_epoch))
        # Recognize the exact legacy epoch-one registry without rewriting it.
        if type(registry) is dict and set(registry) == {"receipts", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_STORAGE_VERSION:
            # Reject legacy bytes after the durable namespace has advanced.
            if reset_epoch != 1 or type(registry["receipts"]) is not dict:
                # Preserve incompatible durable rows for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Read the sole legacy epoch-one receipt mapping.
            receipt_records = registry["receipts"]
            # Validate the complete one-epoch retained registry below.
            retained_receipt_records = ((1, receipt_records),)
        # Recognize only the reviewed epoch-scoped registry shape.
        elif type(registry) is dict and set(registry) == {"receipts_by_epoch", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_EPOCH_STORAGE_VERSION:
            # Require an ordinary epoch mapping.
            if type(registry["receipts_by_epoch"]) is not dict:
                # Reject arrays, scalars, or unknown containers.
                raise ConflictError("Game action storage requires operator recovery")
            # Validate every retained epoch key and nested mapping before current lookup.
            for epoch_key, records in registry["receipts_by_epoch"].items():
                # Accept only canonical positive decimal epochs no newer than current state.
                if type(epoch_key) is not str or not epoch_key.isdigit() or str(int(epoch_key)) != epoch_key or not 1 <= int(epoch_key) <= reset_epoch or type(records) is not dict:
                    # Preserve malformed or future lifecycle history unchanged.
                    raise ConflictError("Game action storage requires operator recovery")
            # Read only the current epoch while retaining older immutable rows.
            receipt_records = registry["receipts_by_epoch"].get(str(reset_epoch), {})
            # Validate every retained epoch so corruption cannot hide outside current lookup.
            retained_receipt_records = tuple((int(epoch_key), records) for epoch_key, records in registry["receipts_by_epoch"].items())
        # Reject every unknown durable registry version or field set.
        else:
            # Preserve malformed bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct every receipt so unrelated corrupt entries cannot remain hidden.
        receipts = {}
        # Inspect every retained epoch and its durable receipt pairs.
        for retained_epoch, records in retained_receipt_records:
            # Validate each complete immutable row in this epoch.
            for scope_key, record in records.items():
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
                # Retain only the caller's current namespace for public lookup.
                if retained_epoch == reset_epoch:
                    # Expose this validated current-epoch receipt.
                    receipts[scope_key] = receipt
        # Return both the writable plain registry and immutable validated view.
        return registry, receipts

    # Return the empty append-only lifecycle claim registry shape for one epoch.
    def _empty_game_action_claims(self, reset_epoch: int = 1) -> dict:
        # Preserve the exact legacy container only in epoch one.
        if reset_epoch == 1:
            # Retain backwards-compatible claim bytes before any reset.
            return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "claims": {}}
        # Use the epoch-scoped container after reset advances the namespace.
        return {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "claims_by_epoch": {str(reset_epoch): {}}}

    # Read and fully validate immutable execution and cancellation claims.
    def _read_game_action_claims(self, reset_epoch: int = 1) -> tuple[dict, dict[str, dict]]:
        # Strictly decode the registry so malformed bytes remain available for operator recovery.
        registry = self._read_game_action_json(self.game_action_claims_path(), lambda: self._empty_game_action_claims(reset_epoch))
        # Recognize the exact legacy epoch-one registry without rewriting it.
        if type(registry) is dict and set(registry) == {"claims", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_STORAGE_VERSION:
            # Reject legacy claims outside their only valid epoch.
            if reset_epoch != 1 or type(registry["claims"]) is not dict:
                # Preserve incompatible durable rows for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Read the sole legacy epoch-one claim mapping.
            claim_records = registry["claims"]
            # Validate the complete one-epoch retained registry below.
            retained_claim_records = ((1, claim_records),)
        # Recognize only the reviewed epoch-scoped registry shape.
        elif type(registry) is dict and set(registry) == {"claims_by_epoch", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_EPOCH_STORAGE_VERSION:
            # Require one ordinary retained-epoch mapping.
            if type(registry["claims_by_epoch"]) is not dict:
                # Reject arrays, scalars, or unknown containers.
                raise ConflictError("Game action storage requires operator recovery")
            # Validate every retained epoch before current lookup.
            for epoch_key, records in registry["claims_by_epoch"].items():
                # Accept only canonical positive decimal epochs no newer than current state.
                if type(epoch_key) is not str or not epoch_key.isdigit() or str(int(epoch_key)) != epoch_key or not 1 <= int(epoch_key) <= reset_epoch or type(records) is not dict:
                    # Preserve malformed or future lifecycle history unchanged.
                    raise ConflictError("Game action storage requires operator recovery")
            # Read only the current epoch while retaining earlier immutable tombstones.
            claim_records = registry["claims_by_epoch"].get(str(reset_epoch), {})
            # Validate every retained epoch so hidden corruption remains fail closed.
            retained_claim_records = tuple((int(epoch_key), records) for epoch_key, records in registry["claims_by_epoch"].items())
        # Reject unknown registry versions and shapes.
        else:
            # Preserve malformed bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct every row before allowing any claim lookup.
        claims = {}
        # Validate every retained epoch and its opaque immutable claim rows.
        for retained_epoch, records in retained_claim_records:
            # Inspect every exact scope and record in this epoch.
            for scope_key, record in records.items():
                # Require exact claim fields with a finite disposition.
                if type(scope_key) is not str or type(record) is not dict or set(record) != {"disposition", "identity", "resources"} or record.get("disposition") not in {"execute", "uncommitted"}:
                    # Preserve malformed claim bytes unchanged.
                    raise ConflictError("Game action storage requires operator recovery")
                # Reconstruct identity and resources through the provider-neutral contract.
                identity = self._deserialize_game_action_identity(record["identity"])
                # Reconstruct the canonical declared resource set.
                resources = self._deserialize_game_action_resources(record["resources"])
                # Require the registry key to match its exact three-part identity.
                if scope_key != self._game_action_scope_key(identity):
                    # Reject misplaced or shadowed lifecycle claims.
                    raise ConflictError("Game action storage requires operator recovery")
                # Retain only the caller's current namespace for lifecycle lookup.
                if retained_epoch == reset_epoch:
                    # Expose validated contract objects and the finite disposition.
                    claims[scope_key] = {"identity": identity, "resources": resources, "disposition": record["disposition"]}
        # Return the writable plain registry and validated immutable-semantics view.
        return registry, claims

    # Insert one immutable JSON lifecycle claim or verify exact compatible replay.
    def _commit_game_action_claim(self, identity: GameActionIdentity, resources: GameActionResources, disposition: str, reset_epoch: int = 1) -> str:
        # Require provider-owned finite disposition selection.
        if disposition not in {"execute", "uncommitted"}:
            # Treat internal misuse as fixed storage corruption risk.
            raise ConflictError("Game action storage is invalid")
        # Read and validate all existing claims before appending a new row.
        registry, claims = self._read_game_action_claims(reset_epoch)
        # Derive the unambiguous durable scope key.
        scope_key = self._game_action_scope_key(identity)
        # Inspect prior immutable ownership when another executor or resolver won.
        existing = claims.get(scope_key)
        # Reject changed fingerprint, resources, or disposition without rewriting the winner.
        if existing is not None:
            # Preserve exact semantic conflicts before planner or resource access.
            if existing["identity"] != identity or existing["resources"] != resources:
                # Keep the immutable winning row unchanged.
                raise ConflictError("Game action key conflicts with durable semantics")
            # Report the immutable winning disposition without changing it.
            return existing["disposition"]
        # Append the exact immutable row under its canonical scope.
        # Select the exact current-epoch mutable mapping without exposing older rows.
        claim_records = registry["claims"] if registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION else registry["claims_by_epoch"].setdefault(str(reset_epoch), {})
        # Append only inside the captured reset epoch.
        claim_records[scope_key] = {
            # Preserve the finite lifecycle winner.
            "disposition": disposition,
            # Preserve canonical identity and fingerprint fields.
            "identity": self._serialize_game_action_identity(identity),
            # Preserve canonical declared resources.
            "resources": self._serialize_game_action_resources(resources),
        }
        # Atomically publish the complete append-only registry under the global gate.
        self._write_game_action_json(self.game_action_claims_path(), registry)
        # Report that this caller inserted the selected winning disposition.
        return disposition

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
        # Reuse the forensic wallet reader so every action sees the same fail-closed state.
        return self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})

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
        reset_epoch: int,
    ) -> dict:
        # Return the exact versioned durable recovery fields.
        return {
            # Preserve the action identity reserved before planning.
            "identity": self._serialize_game_action_identity(identity),
            # Preserve the receipt only after a plan is durable.
            "receipt": None if receipt is None else self._serialize_game_action_receipt(receipt),
            # Preserve the complete declared resources.
            "resources": self._serialize_game_action_resources(resources),
            # Bind recovery to the exact reset namespace that created the action.
            "reset_epoch": reset_epoch,
            # Version the epoch-bound private journal format.
            "schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION,
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
        # Resolve the exact current reset namespace before accepting recovery bytes.
        current_epoch = self._read_game_action_epoch()["current_epoch"]
        # Accept only the shipped legacy journal shape in epoch one.
        if type(record) is dict and set(record) == {"identity", "receipt", "resources", "schema_version", "snapshot_before", "stage"} and record.get("schema_version") == _GAME_ACTION_STORAGE_VERSION:
            # Reject a legacy journal after reset has advanced the namespace.
            if current_epoch != 1:
                # Preserve stale recovery bytes for operator inspection.
                raise ConflictError("Game action storage requires operator recovery")
            # Project the compatible implicit legacy epoch.
            reset_epoch = 1
        # Accept the exact epoch-bound journal format only for the current namespace.
        elif type(record) is dict and set(record) == {"identity", "receipt", "reset_epoch", "resources", "schema_version", "snapshot_before", "stage"} and record.get("schema_version") == _GAME_ACTION_EPOCH_STORAGE_VERSION:
            # Require one exact current bounded epoch.
            if type(record["reset_epoch"]) is not int or record["reset_epoch"] != current_epoch:
                # Refuse cross-reset recovery into current mutable state.
                raise ConflictError("Game action storage requires operator recovery")
            # Retain the validated epoch for reconstructed state.
            reset_epoch = record["reset_epoch"]
        # Reject every truncated, future, or unknown journal shape.
        else:
            # Preserve unknown durable journal bytes.
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
            return {"identity": identity, "receipt": None, "reset_epoch": reset_epoch, "resources": resources, "snapshot_before": snapshot_before, "stage": record["stage"]}
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
        return {"identity": identity, "receipt": receipt, "reset_epoch": reset_epoch, "resources": resources, "snapshot_before": snapshot_before, "stage": record["stage"]}

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
                # Preserve the exact reset namespace across every checkpoint.
                reset_epoch=record["reset_epoch"],
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
    def _commit_game_action_receipt(self, receipt: GameActionReceipt, reset_epoch: int = 1) -> None:
        # Read and validate every durable receipt before adding a new one.
        registry, receipts = self._read_game_action_receipts(reset_epoch)
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
        # Select the exact current-epoch mapping without altering older rows.
        receipt_records = registry["receipts"] if registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION else registry["receipts_by_epoch"].setdefault(str(reset_epoch), {})
        # Add the complete serialized receipt under its epoch-scoped identity.
        receipt_records[scope_key] = self._serialize_game_action_receipt(receipt)
        # Atomically publish the updated immutable receipt registry.
        self._write_game_action_json(self.game_action_receipts_path(), registry)

    # Build deterministic append-only ledger rows for one immutable planned receipt.
    def _game_action_ledger_events(self, receipt: GameActionReceipt) -> tuple[dict, ...]:
        # Track the exact running balance for each declared wallet in planner order.
        balances = dict(receipt.snapshot_before.wallet_balances)
        # Collect one immutable ledger row per nonzero movement.
        events = []
        # Serialize the exact action scope once for deterministic movement identities.
        scope_key = self._game_action_scope_key(receipt.identity)
        # Visit movements in the immutable planner order.
        for index, movement in enumerate(receipt.plan.movements):
            # Read the exact integer-cent balance before this movement.
            before_cents = balances[movement.wallet_id]
            # Compute the exact integer-cent balance after this movement.
            after_cents = before_cents + movement.amount_cents
            # Bind the ledger identity to the complete action scope and movement index.
            ledger_digest = hashlib.sha256(f"{scope_key}:{index}".encode("utf-8")).hexdigest()
            # Construct a compatible ledger event with provider-owned recovery metadata.
            event = {
                # Use one deterministic bounded identifier so crash recovery can detect a prior append.
                "ledger_id": f"gac_{ledger_digest[:60]}",
                # Timestamp the first durable append; replay validates every other immutable field.
                "ts": utc_now(),
                # Preserve the exact affected wallet identity.
                "player_id": movement.wallet_id,
                # Preserve the exact game namespace.
                "game": receipt.identity.game_id,
                # Bind traceability to the caller action key within the legacy field bound.
                "round_id": receipt.identity.action_key[:128],
                # Preserve the provider-neutral movement reason under a distinct namespace.
                "transaction_type": f"game_action_{movement.reason}"[:128],
                # Convert exact cents to the established JSON ledger number shape.
                "amount": self._json_wallet_value(movement.amount_cents),
                # Preserve the exact balance before this movement.
                "balance_before": self._json_wallet_value(before_cents),
                # Preserve the exact balance after this movement.
                "balance_after": self._json_wallet_value(after_cents),
                # Retain immutable action identity evidence without game-specific payloads.
                "details": {
                    # Store the caller-stable action key.
                    "game_action_key": receipt.identity.action_key,
                    # Store the semantic request and resource digest.
                    "game_action_request_fingerprint": receipt.identity.request_fingerprint,
                    # Store the exact movement position for ordered replay proof.
                    "game_action_movement_index": index,
                },
            }
            # Append the exact planned ledger row.
            events.append(event)
            # Advance the wallet-local running balance for later movements.
            balances[movement.wallet_id] = after_cents
        # Return an immutable event sequence for recovery.
        return tuple(events)

    # Append or verify every deterministic ledger row for one planned receipt.
    def _apply_game_action_ledger(self, receipt: GameActionReceipt) -> None:
        # Read all valid append-only rows once under the global action gate.
        existing_rows = {row["ledger_id"]: row for row in self._ledger_rows()}
        # Visit the exact deterministic rows in planner movement order.
        for event in self._game_action_ledger_events(receipt):
            # Resolve an earlier append from a stopped process by deterministic identity.
            existing = existing_rows.get(event["ledger_id"])
            # Verify every immutable field while permitting the original append timestamp.
            if existing is not None:
                # Compare the complete semantic row after substituting the preserved timestamp.
                expected = {**event, "ts": existing.get("ts")}
                # Reject a duplicate identifier whose action semantics diverge.
                if existing != expected:
                    # Preserve the append-only ledger and journal for operator recovery.
                    raise ConflictError("Game action ledger requires operator recovery")
                # Continue without appending a duplicate movement.
                continue
            # Append the new deterministic movement while the global gate remains held.
            self._append_jsonl(self.ledger_path(), event)
            # Retain it for duplicate detection within this receipt.
            existing_rows[event["ledger_id"]] = event

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
        # Publish or validate the immutable execute winner before any projection.
        winning_disposition = self._commit_game_action_claim(receipt.identity, receipt.resources, "execute", record["reset_epoch"])
        # Refuse an impossible planned outcome behind a resolver-owned tombstone.
        if winning_disposition != "execute":
            # Preserve journal and claim bytes for explicit operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Project every declared wallet exactly once.
        self._apply_game_action_wallets(receipt)
        # Inject a process-stop boundary after wallet publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("wallet_applied")
        # Checkpoint the wallet projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "wallet_applied")
        # Append or verify every movement ledger row before publishing game state.
        self._apply_game_action_ledger(receipt)
        # Inject a process-stop boundary after ledger publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("ledger_applied")
        # Checkpoint the append-only ledger projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "ledger_applied")
        # Project every declared state resource exactly once.
        self._apply_game_action_states(receipt)
        # Inject a process-stop boundary after state publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("state_applied")
        # Checkpoint the state projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "state_applied")
        # Commit or verify the immutable receipt registry.
        self._commit_game_action_receipt(receipt, record["reset_epoch"])
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
                # Require one ready durable namespace before any journal or resource access.
                reset_epoch = self._ready_game_action_epoch()
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
                _registry, receipts = self._read_game_action_receipts(reset_epoch)
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
                # Read immutable lifecycle claims only after legacy receipt compatibility.
                _claim_registry, claims = self._read_game_action_claims(reset_epoch)
                # Inspect a resolver or stopped executor winner for this exact scope.
                claim = claims.get(scope_key)
                # Resolve a durable claim before any resource snapshot or planner call.
                if claim is not None:
                    # Reject changed identity or resources against the immutable row.
                    if claim["identity"] != identity or claim["resources"] != resources:
                        # Preserve mismatch-before-planner semantics.
                        raise ConflictError("Game action key conflicts with durable semantics")
                    # Refuse late execution after a resolver-owned uncommitted claim.
                    if claim["disposition"] == "uncommitted":
                        # Keep the tombstone immutable and prevent any resource mutation.
                        raise ConflictError("Game action was durably resolved as uncommitted")
                    # An execute claim without its receipt or journal cannot be repaired safely.
                    raise ConflictError("Game action storage requires operator recovery")
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
                    # Bind every recovery stage to the captured reset namespace.
                    "reset_epoch": reset_epoch,
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
                # Publish the immutable execute winner after the receipt is recoverable.
                winning_disposition = self._commit_game_action_claim(identity, resources, "execute", reset_epoch)
                # Refuse any impossible resolver win without projecting the plan.
                if winning_disposition != "execute":
                    # Preserve the planned journal and tombstone for operator recovery.
                    raise ConflictError("Game action storage requires operator recovery")
                # Apply and checkpoint every projection through restart-safe recovery.
                committed = self._recover_game_action_journal_locked(inject_failures=True)
                # Require the recovery path to return the just-planned immutable receipt.
                if committed != receipt:
                    # Reject impossible provider divergence without a public result.
                    raise ConflictError("Game action storage requires operator recovery")
                # Return the newly committed receipt with replay false.
                return receipt, False

    # Resolve one JSON action through the same process-wide ownership boundary.
    def resolve_game_action(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
    ) -> GameActionResolution:
        # Validate exact contract types before attempting any provider lock.
        validate_resolution_request(identity=identity, resources=resources)
        # Reject recursive lifecycle resolution from inside a planner.
        self._reject_planner_mutation()
        # Attempt the provider-instance lock without waiting behind active execution.
        lock_acquired = self.lock.acquire(blocking=False)
        # Report active ownership without reading partially projected state.
        if not lock_acquired:
            # Return the provider-neutral finite pending result.
            return GameActionResolution(status="pending")
        try:
            # Attempt both process locks once so resolution never stalls an HTTP worker.
            with self._try_json_global_gate() as gate_acquired:
                # Report active ownership when another process retains either gate.
                if not gate_acquired:
                    # Return no receipt or partial state while execution is in flight.
                    return GameActionResolution(status="pending")
                # Treat reset-owned visibility as finite pending without a claim.
                epoch_state = self._read_game_action_epoch()
                # Keep reset isolation provider-neutral for nonblocking resolution.
                if epoch_state["phase"] != "ready":
                    # Return without journal recovery or immutable lifecycle mutation.
                    return GameActionResolution(status="pending")
                # Capture the exact ready namespace for every later lookup.
                reset_epoch = epoch_state["current_epoch"]
                # Complete any legacy logical money action before inspecting wallets.
                self._recover_committed_actions()
                # Derive the unambiguous durable action scope.
                scope_key = self._game_action_scope_key(identity)
                # Inspect a provider-private journal before committing a resolver claim.
                pending = self._read_game_action_journal()
                # Resolve the same scope through exact fingerprint and resource semantics.
                if pending is not None and pending["identity"].scope_key == identity.scope_key:
                    # Reject changed semantic reuse before any journal recovery mutation.
                    if pending["identity"] != identity or pending["resources"] != resources:
                        # Preserve the active or recoverable journal unchanged.
                        raise ConflictError("Game action key conflicts with durable semantics")
                    # Let the resolver win only while no planner outcome exists.
                    if pending["stage"] == "prepared":
                        # Remove the no-mutation reservation under exclusive ownership.
                        self._remove_game_action_journal()
                        # Append the immutable uncommitted tombstone.
                        winner = self._commit_game_action_claim(identity, resources, "uncommitted", reset_epoch)
                        # Require the resolver to retain its exact winning disposition.
                        if winner != "uncommitted":
                            # Refuse inconsistent lifecycle history.
                            raise ConflictError("Game action storage requires operator recovery")
                        # Return the terminal no-result state.
                        return GameActionResolution(status="uncommitted")
                    # Recover every planned or later stage to its immutable receipt.
                    self._recover_game_action_journal_locked()
                # Recover or clear an unrelated journal before reading shared registries.
                elif pending is not None:
                    # Complete its valid lifecycle under the same global gate.
                    self._recover_game_action_journal_locked()
                # Read committed receipts first for schema-3 JSON compatibility.
                _receipt_registry, receipts = self._read_game_action_receipts(reset_epoch)
                # Inspect the exact caller scope after all recoverable projection work.
                receipt = receipts.get(scope_key)
                # Return a compatible legacy or schema-4 committed result.
                if receipt is not None:
                    # Reject changed identity or resources before returning prior outcome data.
                    if receipt.identity != identity or receipt.resources != resources:
                        # Preserve the immutable committed receipt.
                        raise ConflictError("Game action key conflicts with committed semantics")
                    # Return the complete provider-neutral committed resolution.
                    return GameActionResolution(status="committed", receipt=receipt)
                # Read immutable lifecycle claims after legacy receipt lookup.
                _claim_registry, claims = self._read_game_action_claims(reset_epoch)
                # Inspect an earlier resolver or executor winner.
                claim = claims.get(scope_key)
                # Validate exact compatible claim reuse before returning its state.
                if claim is not None:
                    # Reject changed semantic reuse without rewriting the winner.
                    if claim["identity"] != identity or claim["resources"] != resources:
                        # Preserve mismatch-before-mutation semantics.
                        raise ConflictError("Game action key conflicts with durable semantics")
                    # Return a resolver-owned tombstone as the terminal no-result state.
                    if claim["disposition"] == "uncommitted":
                        # Return no receipt for an action that never committed.
                        return GameActionResolution(status="uncommitted")
                    # An execute claim without a receipt or journal needs operator repair.
                    raise ConflictError("Game action storage requires operator recovery")
                # Atomically append the resolver-owned tombstone as the first claim.
                winner = self._commit_game_action_claim(identity, resources, "uncommitted", reset_epoch)
                # Require this exact resolver to retain the immutable winning state.
                if winner != "uncommitted":
                    # Reject an impossible disposition transition.
                    raise ConflictError("Game action storage requires operator recovery")
                # Return the durable terminal no-result state.
                return GameActionResolution(status="uncommitted")
        finally:
            # Release the provider-instance lock after every finite or exceptional outcome.
            self.lock.release()

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
# Define a no-close facade that lets reset bootstrap reuse its one owned pool lease.
class _BorrowedMySQLConnection:
    # Retain the reset-owned lease without transferring close authority.
    def __init__(self, connection: Any) -> None:
        # Store only the caller-owned lease for transparent DB-API delegation.
        self._connection = connection
        # Track operation-boundary cleanup without transferring outer close authority.
        self._closed = False

    # Delegate every DB-API attribute except the explicit no-close boundary below.
    def __getattr__(self, name: str) -> Any:
        # Preserve cursor and transaction behavior on the exact reset session.
        return getattr(self._connection, name)

    # Keep nested provider operations from returning the reset lease to the pool.
    def close(self) -> None:
        # Preserve idempotent DB-API close behavior for nested finally blocks.
        if self._closed:
            # Avoid repeated session cleanup after the operation already ended.
            return
        # End every implicit read or failed-write transaction before the next bootstrap helper.
        self._connection.rollback()
        # Mark cleanup complete only after the retained session is transaction-clean.
        self._closed = True


class MySQLStorageProvider(StorageProvider, GameActionExecutor):
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
        # Track same-thread reset lease borrowing without sharing authority across requests.
        self._reset_local = threading.local()

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
        # Reject raw connection access from inside a planner on this database target.
        self._reject_planner_mutation()
        # Reject connector overrides that could cross credential, database, or session boundaries.
        if set(overrides) - {"connection_timeout"}:
            # Raise a fixed validation error without echoing option names or values.
            raise ValueError("Unsupported MySQL connection override.")
        # Reuse the reset-owned lease for synchronous bootstrap calls at pool capacity one.
        borrowed = getattr(self._reset_local, "connection", None)
        # Return a no-close facade only while this thread owns an active reset session.
        if borrowed is not None:
            # Prevent nested bootstrap helpers from returning the sole lease early.
            return _BorrowedMySQLConnection(borrowed)
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
        # Refuse provider lifecycle mutation from inside a supposedly pure planner.
        self._reject_planner_mutation()
        # Delegate fail-safe connection shutdown to the pool.
        self._pool.close_all()

    # Return the configured relational target key shared by equivalent provider instances.
    def _planner_key(self) -> tuple[str, int, str]:
        # Normalize host case while preserving exact port and database ownership.
        return (self.config.host.lower(), self.config.port, self.config.database)

    # Return whether this thread is planning through this configured database boundary.
    def _planner_is_active(self) -> bool:
        # Read the thread-local target set without sharing a mutable default.
        providers = getattr(_MYSQL_PLANNER_LOCAL, "providers", set())
        # Bind purity across equivalent provider instances for the same relational target.
        return self._planner_key() in providers

    # Return whether this process already owns an active reset for the same target.
    def _reset_is_active(self) -> bool:
        # Serialize registry observation with reset acquisition and release.
        with _MYSQL_RESET_REGISTRY_LOCK:
            # Match equivalent provider instances through the secret-free target key.
            return self._planner_key() in _MYSQL_RESET_TARGETS

    # Reject MySQL provider mutation attempted from inside an action planner.
    def _reject_planner_mutation(self) -> None:
        # Fail before opening a connection or changing provider lifecycle state.
        if self._planner_is_active():
            # Reuse the provider-neutral fixed purity error.
            raise ValidationError("Game action planner must be side-effect free")

    # Mark one synchronous planner call as unable to re-enter this provider mutably.
    @contextmanager
    def _planner_boundary(self):
        # Copy the active target set so nesting remains thread-local and explicit.
        providers = set(getattr(_MYSQL_PLANNER_LOCAL, "providers", set()))
        # Resolve this provider's secret-free relational target identity.
        planner_key = self._planner_key()
        # Reject recursive planning through the same target before another connection.
        if planner_key in providers:
            # Preserve the fixed provider-neutral validation boundary.
            raise ValidationError("Game action planner must be side-effect free")
        # Add this exact configured target for the synchronous callback lifetime.
        providers.add(planner_key)
        # Publish the active set only to this thread.
        _MYSQL_PLANNER_LOCAL.providers = providers
        try:
            # Transfer control to the caller-owned planner.
            yield
        finally:
            # Remove this target even when the planner raises.
            providers.discard(planner_key)
            # Retain any independently active outer database boundaries.
            _MYSQL_PLANNER_LOCAL.providers = providers

    # Verify the exact MySQL migration state before reads and writes.
    def ensure_ready(self) -> None:
        # Refuse hidden provider access through a planner closure before cached readiness.
        self._reject_planner_mutation()
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

    # Require exact clean schema four before exposing the inert lifecycle write bridge.
    def _runtime_schema_state(self, connection):
        # Delegate read-only catalog verification through one overridable test seam.
        return verify_runtime_compatibility(connection)

    # Require exact clean schema four before exposing the inert lifecycle write bridge.
    def _require_game_action_schema(self, connection) -> None:
        # Re-read control metadata on this transaction connection rather than trusting readiness cache.
        state = self._runtime_schema_state(connection)
        # Accept no older compatible schema because claims do not exist before migration four.
        if not state.initialized or state.status != "clean" or state.current_version != 4:
            # Keep ordinary schema-two/three runtime reads available while lifecycle writes fail closed.
            raise ConflictError("MySQL game action lifecycle requires clean schema 4")

    # Lock and validate the singleton MySQL reset epoch inside an active transaction.
    def _mysql_game_action_epoch(self, cursor, *, exclusive: bool = False) -> dict:
        # Select shared lifecycle visibility for actions or exclusive ownership for reset.
        lock_clause = "FOR UPDATE" if exclusive else "FOR SHARE"
        # Read the exact singleton row with the requested transaction lock.
        cursor.execute(f"SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state WHERE state_id = 1 {lock_clause}")
        # Fetch the sole expected control row.
        row = cursor.fetchone()
        # Require one exact dictionary row from the schema-four singleton.
        if type(row) is not dict or set(row) != {"current_epoch", "phase", "state_id"}:
            # Refuse absent, duplicate-projected, or malformed control state.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Require the fixed singleton identity without coercion.
        if type(row["state_id"]) is not int or row["state_id"] != 1:
            # Preserve the relational row for operator repair.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Require one bounded signed-range epoch shared with JSON.
        if type(row["current_epoch"]) is not int or not 1 <= row["current_epoch"] <= _GAME_ACTION_MAX_EPOCH:
            # Refuse overflow or connector coercion.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Require one finite reset phase.
        if type(row["phase"]) is not str or row["phase"] not in {"ready", "resetting"}:
            # Reject unknown visibility semantics.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Return the validated row for same-transaction use.
        return row

    # Convert one exact MySQL decimal balance into provider-neutral integer cents.
    def _mysql_game_action_cents(self, value: Any) -> int:
        # Convert through decimal string form to avoid binary floating-point normalization.
        scaled = Decimal(str(value)) * Decimal(100)
        # Require an exact finite integral-cent value.
        if not scaled.is_finite() or scaled != scaled.to_integral_value():
            # Preserve malformed wallet rows for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Validate exact range and nonnegative semantics through a one-wallet snapshot.
            snapshot = GameActionSnapshot.create(resources=GameActionResources(wallet_ids=("wallet",)), wallet_balances={"wallet": int(scaled)}, state_values={})
        # Normalize contract validation into the provider recovery boundary.
        except (ValueError, OverflowError, ValidationError):
            # Preserve the original relational row unchanged.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Return the exact validated integer-cent balance.
        return snapshot.wallet_balance("wallet")

    # Decode one canonical text JSON field from the immutable lifecycle tables.
    def _decode_mysql_game_action_json(self, value: Any) -> Any:
        # Accept only bytes or text from the binary-collated TEXT columns.
        if isinstance(value, bytes):
            # Decode exact UTF-8 without replacement.
            raw = value.decode("utf-8")
        # Preserve driver-returned text exactly.
        elif type(value) is str:
            # Retain the raw text for canonical byte comparison.
            raw = value
        # Reject driver coercion or unexpected JSON-native shapes.
        else:
            # Preserve the row for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reject duplicate object keys while decoding immutable receipt material.
            decoded = json.loads(raw, object_pairs_hook=self._unique_json_object)
        # Normalize malformed UTF-8 or JSON without exposing stored bytes.
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            # Preserve the row for explicit operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None
        # Require the stored text to equal the unique canonical representation byte-for-byte.
        if canonical_json_bytes(decoded).decode("utf-8") != raw:
            # Refuse ambiguous whitespace, ordering, or numeric encodings.
            raise ConflictError("Game action storage requires operator recovery")
        # Return the strictly decoded canonical object.
        return decoded

    # Decode and validate one immutable MySQL receipt row.
    def _mysql_game_action_receipt(self, row: dict) -> GameActionReceipt:
        # Decode the complete canonical resource declaration.
        resources_value = self._decode_mysql_game_action_json(row["resources_json"])
        # Reconstruct exact resources through the provider-neutral validator.
        resources = self._deserialize_game_action_resources(resources_value)
        # Decode the complete canonical receipt graph.
        receipt_value = self._decode_mysql_game_action_json(row["receipt_json"])
        # Hash the exact stored bytes before accepting their semantic content.
        receipt_bytes = row["receipt_json"] if isinstance(row["receipt_json"], bytes) else str(row["receipt_json"]).encode("utf-8")
        # Hash the exact binary-collated text returned by the provider.
        receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()
        # Require the immutable row checksum to match exactly.
        if receipt_digest != row["receipt_sha256"]:
            # Refuse a corrupted or normalized receipt row.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct and self-validate the complete immutable receipt.
        receipt = self._deserialize_game_action_receipt(receipt_value)
        # Require duplicated row identity and resource fields to agree exactly.
        if receipt.identity.scope_key != (row["game_id"], row["player_id"], row["action_key"]) or receipt.identity.request_fingerprint != row["request_fingerprint"] or receipt.resources != resources:
            # Preserve inconsistent immutable lifecycle rows.
            raise ConflictError("Game action storage requires operator recovery")
        # Require every receipt child row to name only the execute disposition.
        if row.get("claim_disposition") != "execute":
            # Refuse a receipt detached from executable ownership.
            raise ConflictError("Game action storage requires operator recovery")
        # Return the exact provider-neutral committed receipt.
        return receipt

    # Read one immutable receipt under the caller's active transaction.
    def _select_mysql_game_action_receipt(self, cursor, identity: GameActionIdentity, reset_epoch: int) -> GameActionReceipt | None:
        # Query the exact primary-key scope and all immutable receipt bytes.
        cursor.execute(
            "SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition FROM casino_game_action_receipts WHERE reset_epoch = %s AND game_id = %s AND player_id = %s AND action_key = %s FOR SHARE",
            (reset_epoch, *identity.scope_key),
        )
        # Read the optional committed row.
        row = cursor.fetchone()
        # Preserve the unused-key result without inventing a receipt.
        if row is None:
            # Return no committed outcome.
            return None
        # Require the selected immutable row to remain in the captured namespace.
        if type(row.get("reset_epoch")) is not int or row["reset_epoch"] != reset_epoch:
            # Refuse connector coercion or cross-epoch row drift.
            raise ConflictError("Game action storage requires operator recovery")
        # Decode and validate the complete immutable row.
        return self._mysql_game_action_receipt(row)

    # Insert or inspect one immutable lifecycle claim under transaction ownership.
    def _claim_mysql_game_action(self, cursor, identity: GameActionIdentity, resources: GameActionResources, disposition: str, reset_epoch: int) -> tuple[str, bool]:
        # Serialize exact resources once for unique and compatibility checks.
        resources_json = canonical_json_bytes(self._serialize_game_action_resources(resources)).decode("utf-8")
        # Attempt one append-only insert without updating an existing winner.
        cursor.execute(
            "INSERT IGNORE INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (reset_epoch, *identity.scope_key, identity.request_fingerprint, resources_json, disposition),
        )
        # Remember whether this transaction inserted the immutable winning row.
        inserted = cursor.rowcount == 1
        # Lock and read the winning primary-key row after duplicate contenders serialize.
        cursor.execute(
            "SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition FROM casino_game_action_claims WHERE reset_epoch = %s AND game_id = %s AND player_id = %s AND action_key = %s FOR SHARE",
            (reset_epoch, *identity.scope_key),
        )
        # Require the just-inserted or prior winning claim to exist.
        row = cursor.fetchone()
        # Reject impossible disappearance under the same transaction.
        if row is None:
            # Preserve transactional state for rollback.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the winning claim to belong to the captured epoch exactly.
        if type(row.get("reset_epoch")) is not int or row["reset_epoch"] != reset_epoch:
            # Refuse connector coercion or namespace drift.
            raise ConflictError("Game action storage requires operator recovery")
        # Decode exact resources before comparing semantic reuse.
        stored_resources = self._deserialize_game_action_resources(self._decode_mysql_game_action_json(row["resources_json"]))
        # Reject changed identity fingerprint or resources without invoking a planner.
        if row["request_fingerprint"] != identity.request_fingerprint or stored_resources != resources:
            # Keep the original immutable claim unchanged.
            raise ConflictError("Game action key conflicts with durable semantics")
        # Return the finite winning disposition and whether this transaction inserted it.
        return row["disposition"], inserted

    # Capture exact locked MySQL wallet and state resources for one planner.
    def _capture_mysql_game_action_snapshot(self, cursor, resources: GameActionResources) -> GameActionSnapshot:
        # Collect exact integer-cent wallet balances by declared identity.
        wallet_balances = {}
        # Lock wallets in canonical resource order to prevent cross-action deadlocks.
        for wallet_id in resources.wallet_ids:
            # Lock one exact wallet row for the complete lifecycle transaction.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (wallet_id,))
            # Read the required wallet row.
            row = cursor.fetchone()
            # Reject missing wallets through the established provider boundary.
            if row is None:
                # Preserve the transaction for rollback by the caller.
                raise NotFoundError(f"Player {wallet_id} was not found")
            # Convert the decimal balance to exact integer cents.
            wallet_balances[wallet_id] = self._mysql_game_action_cents(row["balance"])
        # Collect exact route-free game-state documents.
        state_values = {}
        # Lock states in canonical resource order alongside wallet rows.
        for state_key in resources.state_keys:
            # Create the exact lockable empty document without overwriting prior state.
            cursor.execute(
                "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE document_key = VALUES(document_key)",
                (state_key, "{}", utc_now()),
            )
            # Lock the exact state row for snapshot and later replacement.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (state_key,))
            # Read the state row established by the insert-or-lock operation.
            row = cursor.fetchone()
            # Reject impossible row disappearance.
            if row is None:
                # Fail closed within the transaction.
                raise ConflictError("Game action state requires operator recovery")
            # Decode the existing provider JSON shape.
            state_values[state_key] = _decode_json(row["payload_json"])
        # Freeze and validate the complete bounded provider snapshot.
        return GameActionSnapshot.create(resources=resources, wallet_balances=wallet_balances, state_values=state_values)

    # Insert exact ledger movements inside the active game-action transaction.
    def _insert_mysql_game_action_ledger(self, cursor, receipt: GameActionReceipt) -> None:
        # Build deterministic movement rows from immutable before/after snapshots.
        for event in self._game_action_ledger_events(receipt):
            # Insert each append-only ledger row with a dedicated compatible action namespace.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], "game_action", event["ledger_id"], receipt.identity.request_fingerprint, json.dumps(event["details"], sort_keys=True, separators=(",", ":"))),
            )

    # Execute or replay one schema-four MySQL game action in one transaction.
    def execute_game_action_once(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
        planner: Callable[[GameActionSnapshot], GameActionPlan],
    ) -> tuple[GameActionReceipt, bool]:
        # Validate exact provider-neutral types before any connection or row lock.
        validate_execution_request(identity=identity, resources=resources, planner=planner)
        # Reject recursive execution from inside another planner on this provider.
        self._reject_planner_mutation()
        # Fail before pool checkout when this process owns reset bootstrap at capacity one.
        if self._reset_is_active():
            # Preserve claim-zero and planner-zero reset exclusion.
            raise ConflictError("Game action reset is in progress")
        # Ensure ordinary runtime compatibility before opening the action transaction.
        self.ensure_ready()
        # Open one connection for claim, resources, ledger, state, and receipt.
        connection = self.connect()
        try:
            # Start one row-locking lifecycle transaction.
            connection.start_transaction()
            # Require exact clean schema four inside the same lifecycle transaction.
            self._require_game_action_schema(connection)
            # Open a dictionary cursor for immutable row reconstruction.
            cursor = connection.cursor(dictionary=True)
            # Hold shared ownership of one ready reset epoch through the full action transaction.
            epoch_state = self._mysql_game_action_epoch(cursor)
            # Refuse every action while reset bootstrap remains incomplete.
            if epoch_state["phase"] != "ready":
                # Fail before claim insertion, resource access, or planner invocation.
                raise ConflictError("Game action reset is in progress")
            # Capture the exact immutable namespace for every lifecycle row.
            reset_epoch = epoch_state["current_epoch"]
            # Insert or serialize behind the exact lifecycle claim.
            disposition, inserted = self._claim_mysql_game_action(cursor, identity, resources, "execute", reset_epoch)
            # Reject a resolver-owned tombstone before snapshots or planner/RNG.
            if disposition == "uncommitted":
                # Preserve the winning claim and roll back only this caller's no-op work.
                raise ConflictError("Game action was durably resolved as uncommitted")
            # Read a compatible committed receipt after the execute claim lock is held.
            existing = self._select_mysql_game_action_receipt(cursor, identity, reset_epoch)
            # Resolve committed replay without another planner invocation.
            if existing is not None:
                # Reject changed resource or fingerprint reuse before returning the result.
                if existing.identity != identity or existing.resources != resources:
                    # Preserve immutable claim and receipt rows.
                    raise ConflictError("Game action key conflicts with committed semantics")
                # Commit the read-only transaction and release row ownership.
                connection.commit()
                # Return the original immutable committed receipt.
                return existing, True
            # Refuse a prior execute claim whose receipt is absent after lock acquisition.
            if not inserted:
                # Preserve the orphaned claim for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Lock and snapshot every declared wallet and state resource.
            snapshot_before = self._capture_mysql_game_action_snapshot(cursor, resources)
            # Prevent the synchronous planner from mutating this provider through a closure.
            with self._planner_boundary():
                # Invoke the caller planner once while the complete transaction owns resources.
                plan = planner(snapshot_before)
            # Require the exact immutable plan result type.
            if type(plan) is not GameActionPlan:
                # Reject plan-like objects before any committed projection.
                raise ValidationError("Game action planner returned an invalid plan")
            # Compute and validate the exact deterministic committed snapshot.
            snapshot_after = apply_plan_to_snapshot(snapshot_before, plan)
            # Construct the complete immutable receipt before any DML projection.
            receipt = GameActionReceipt(identity=identity, resources=resources, snapshot_before=snapshot_before, plan=plan, snapshot_after=snapshot_after)
            # Publish exact final wallet balances under the retained row locks.
            for wallet_id, balance_cents in receipt.snapshot_after.wallet_balances:
                # Update only the declared wallet row with exact decimal cents.
                cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (Decimal(balance_cents) / Decimal(100), utc_now(), wallet_id))
                # Require the locked wallet row to remain uniquely present.
                if cursor.rowcount != 1:
                    # Fail the complete transaction closed.
                    raise ConflictError("Game action wallet state requires operator recovery")
            # Append every movement ledger row inside the same transaction.
            self._insert_mysql_game_action_ledger(cursor, receipt)
            # Publish exact final state documents under their retained row locks.
            for state_key, state_value in receipt.snapshot_after.state_values:
                # Replace only one declared state row with canonical JSON.
                cursor.execute("UPDATE casino_documents SET payload_json = %s, updated_at = %s WHERE document_key = %s", (canonical_json_bytes(self._plain_canonical(state_value)).decode("utf-8"), utc_now(), state_key))
                # Require the locked state row to remain uniquely present.
                if cursor.rowcount != 1:
                    # Fail the complete transaction closed.
                    raise ConflictError("Game action state requires operator recovery")
            # Serialize exact receipt and resource bytes for immutable storage.
            resources_json = canonical_json_bytes(self._serialize_game_action_resources(resources)).decode("utf-8")
            # Serialize the complete receipt through the same legacy-compatible codec.
            receipt_json = canonical_json_bytes(self._serialize_game_action_receipt(receipt)).decode("utf-8")
            # Hash the exact receipt bytes stored in the binary-collated column.
            receipt_sha256 = hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
            # Insert the immutable receipt as the final transaction row.
            cursor.execute(
                "INSERT INTO casino_game_action_receipts (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'execute')",
                (reset_epoch, *identity.scope_key, identity.request_fingerprint, resources_json, receipt_json, receipt_sha256),
            )
            # Commit claim, wallets, ledger, state, and receipt atomically.
            connection.commit()
            # Return the newly committed immutable receipt.
            return receipt, False
        # Roll back every provider, planner, validation, or database failure.
        except Exception:
            # Discard all uncommitted lifecycle and resource changes.
            connection.rollback()
            # Preserve the original bounded error for callers and tests.
            raise
        finally:
            # Release the transaction connection after commit or rollback.
            connection.close()

    # Resolve one schema-four MySQL action without invoking its planner.
    def resolve_game_action(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
    ) -> GameActionResolution:
        # Validate exact provider-neutral types before any connection or lock attempt.
        validate_resolution_request(identity=identity, resources=resources)
        # Reject lifecycle mutation from inside an active planner on this provider.
        self._reject_planner_mutation()
        # Return finite pending before pool checkout during same-process reset bootstrap.
        if self._reset_is_active():
            # Preserve claim-zero and bounded capacity-one behavior.
            return GameActionResolution(status="pending")
        # Preserve ordinary compatible runtime readiness behavior.
        self.ensure_ready()
        # Open one connection for the finite resolver transaction.
        connection = self.connect()
        # Retain the original session lock-wait policy for pooled-connection restoration.
        original_lock_wait = None
        # Retain the cursor so finally can restore session state after commit or rollback.
        cursor = None
        try:
            # Open a dictionary cursor before the transaction to inspect session policy.
            cursor = connection.cursor(dictionary=True)
            # Read the current pooled-session lock-wait value without exposing it publicly.
            cursor.execute("SELECT @@SESSION.innodb_lock_wait_timeout AS lock_wait")
            # Retain the exact bounded integer for later restoration.
            original_lock_wait = int(cursor.fetchone()["lock_wait"])
            # Bound only this leased session before beginning the resolver transaction.
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 1")
            # End any implicit connector transaction opened by session preflight reads.
            connection.rollback()
            # Start one transaction whose insert races the execute claim.
            connection.start_transaction()
            # Require exact clean schema four inside the bounded resolver transaction.
            self._require_game_action_schema(connection)
            # Hold shared epoch ownership before any immutable lifecycle lookup or insert.
            epoch_state = self._mysql_game_action_epoch(cursor)
            # Treat reset bootstrap as finite pending without a claim.
            if epoch_state["phase"] != "ready":
                # End the read-only transaction before returning no outcome.
                connection.commit()
                # Preserve claim-zero and planner-zero reset behavior.
                return GameActionResolution(status="pending")
            # Capture the exact ready namespace for resolver competition.
            reset_epoch = epoch_state["current_epoch"]
            # Insert or serialize behind the exact lifecycle claim.
            disposition, _inserted = self._claim_mysql_game_action(cursor, identity, resources, "uncommitted", reset_epoch)
            # Return the durable resolver-owned tombstone when it won first.
            if disposition == "uncommitted":
                # Commit the immutable no-result claim.
                connection.commit()
                # Return the terminal provider-neutral state.
                return GameActionResolution(status="uncommitted")
            # Read the execute owner's immutable receipt after its claim lock releases.
            receipt = self._select_mysql_game_action_receipt(cursor, identity, reset_epoch)
            # Refuse an execute claim that became visible without its atomic receipt.
            if receipt is None:
                # Preserve the orphaned claim for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Reject changed compatible fields before returning outcome data.
            if receipt.identity != identity or receipt.resources != resources:
                # Preserve immutable execute history.
                raise ConflictError("Game action key conflicts with committed semantics")
            # Commit the read-only resolution transaction.
            connection.commit()
            # Return the complete immutable committed result.
            return GameActionResolution(status="committed", receipt=receipt)
        # Convert only MySQL lock wait/deadlock errors into a finite pending state.
        except Exception as exc:
            # Read the connector's numeric server error without importing provider classes.
            error_number = getattr(exc, "errno", None)
            # Release all statement and row locks from the timed-out resolver.
            connection.rollback()
            # Report active ownership for bounded lock wait or deadlock selection.
            if error_number in {1205, 1213}:
                # Return no partial receipt while execution remains uncertain.
                return GameActionResolution(status="pending")
            # Preserve every other provider or semantic failure.
            raise
        finally:
            try:
                # Restore the pooled session policy after the transaction has ended.
                if cursor is not None and original_lock_wait is not None:
                    # Reapply only the trusted integer read from this same session.
                    cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", (original_lock_wait,))
            finally:
                # Always return or discard the lease even when session restoration fails.
                connection.close()

    # Reuse the canonical Phase0c codecs without creating a second receipt format.
    _plain_canonical = JsonStorageProvider._plain_canonical
    # Reuse duplicate-key rejection for immutable MySQL text fields.
    _unique_json_object = JsonStorageProvider._unique_json_object
    # Reuse exact resource serialization for schema-three compatibility.
    _serialize_game_action_resources = JsonStorageProvider._serialize_game_action_resources
    # Reuse delimiter-safe durable scope encoding for movement identities.
    _game_action_scope_key = JsonStorageProvider._game_action_scope_key
    # Reuse exact resource reconstruction for conflict checks.
    _deserialize_game_action_resources = JsonStorageProvider._deserialize_game_action_resources
    # Reuse exact identity reconstruction embedded in legacy receipts.
    _deserialize_game_action_identity = JsonStorageProvider._deserialize_game_action_identity
    # Reuse exact identity serialization embedded in legacy receipts.
    _serialize_game_action_identity = JsonStorageProvider._serialize_game_action_identity
    # Reuse immutable snapshot serialization.
    _serialize_game_action_snapshot = JsonStorageProvider._serialize_game_action_snapshot
    # Reuse immutable snapshot reconstruction.
    _deserialize_game_action_snapshot = JsonStorageProvider._deserialize_game_action_snapshot
    # Reuse immutable plan serialization.
    _serialize_game_action_plan = JsonStorageProvider._serialize_game_action_plan
    # Reuse immutable plan reconstruction.
    _deserialize_game_action_plan = JsonStorageProvider._deserialize_game_action_plan
    # Reuse the complete legacy-compatible receipt serialization.
    _serialize_game_action_receipt = JsonStorageProvider._serialize_game_action_receipt
    # Reuse the complete legacy-compatible receipt reconstruction.
    _deserialize_game_action_receipt = JsonStorageProvider._deserialize_game_action_receipt
    # Reuse exact JSON cent conversion for deterministic ledger event fields.
    _json_wallet_cents = JsonStorageProvider._json_wallet_cents
    # Reuse compatible JSON numeric projection for ledger events.
    _json_wallet_value = JsonStorageProvider._json_wallet_value
    # Reuse deterministic movement ledger construction across providers.
    _game_action_ledger_events = JsonStorageProvider._game_action_ledger_events

    # Derive one bounded non-secret named lock for this exact relational reset target.
    def _mysql_reset_lock_name(self) -> str:
        # Serialize only the normalized host, port, and database identity.
        target = f"{self.config.host.lower()}:{self.config.port}/{self.config.database}"
        # Keep the lock name below MySQL's 64-character boundary.
        return f"casino-reset-{hashlib.sha256(target.encode('utf-8')).hexdigest()[:48]}"

    # Delete only reset-owned mutable projections inside an active transaction.
    def _clear_mysql_mutable_state(self, cursor) -> None:
        # Delete ledger rows before players to satisfy foreign keys.
        cursor.execute("DELETE FROM casino_ledger")
        # Delete history rows because reset starts a fresh visible outcome set.
        cursor.execute("DELETE FROM casino_history")
        # Delete JSON document rows because caller bootstrap restores reviewed defaults.
        cursor.execute("DELETE FROM casino_documents")
        # Delete player rows after dependent ledger rows.
        cursor.execute("DELETE FROM casino_players")

    # Hold a target-scoped reset lock through clear, caller bootstrap, and phase release.
    @contextmanager
    def reset_transaction(self):
        # Reject destructive provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Reject same-thread nested resets before borrowing can hide ownership.
        if getattr(self._reset_local, "connection", None) is not None:
            # Preserve the outer reset as the sole owner.
            raise ConflictError("MySQL reset is already in progress")
        # Verify the compatible schema before opening the owned reset lease.
        self.ensure_ready()
        # Resolve the process-wide target identity before pool checkout.
        reset_target = self._planner_key()
        # Claim local reset ownership nonblockingly for capacity-one pools.
        with _MYSQL_RESET_REGISTRY_LOCK:
            # Reject another provider instance already resetting this target.
            if reset_target in _MYSQL_RESET_TARGETS:
                # Avoid waiting for its retained sole pool lease.
                raise ConflictError("MySQL reset is already in progress")
            # Reserve this target until named-lock acquisition succeeds or cleanup runs.
            _MYSQL_RESET_TARGETS.add(reset_target)
        try:
            # Acquire the one pool lease retained across synchronous caller bootstrap.
            connection = self.connect()
        # Release local ownership if pool checkout itself fails.
        except BaseException:
            # Serialize exact registry cleanup across equivalent provider instances.
            with _MYSQL_RESET_REGISTRY_LOCK:
                # Remove only this target's provisional ownership.
                _MYSQL_RESET_TARGETS.discard(reset_target)
            # Preserve the original checkout failure.
            raise
        # Derive the fixed target-scoped named lock without credentials.
        lock_name = self._mysql_reset_lock_name()
        # Track whether this session owns the server lock for exact release.
        named_lock_acquired = False
        # Track whether schema four requires durable phase finalization.
        reset_epoch = None
        try:
            # Use dictionary rows for strict named-lock and epoch validation.
            cursor = connection.cursor(dictionary=True)
            # Attempt the target-scoped session lock without waiting behind another reset.
            cursor.execute("SELECT GET_LOCK(%s, 0) AS acquired", (lock_name,))
            # Read the exact finite acquisition result.
            lock_row = cursor.fetchone()
            # Reject contention, connector coercion, or server lock failure uniformly.
            if type(lock_row) is not dict or lock_row.get("acquired") != 1:
                # Avoid any reset phase or mutable-state change.
                raise ConflictError("MySQL reset is already in progress")
            # Record sole session ownership before any transaction begins.
            named_lock_acquired = True
            # End the implicit transaction opened by the named-lock preflight query.
            connection.rollback()
            # Start phase one across epoch ownership and mutable deletion.
            connection.start_transaction()
            # Re-read exact migration state inside the reset transaction.
            schema_state = self._runtime_schema_state(connection)
            # Activate durable epoch semantics only on exact clean schema four.
            if schema_state.initialized and schema_state.status == "clean" and schema_state.current_version == 4:
                # Lock the singleton exclusively before any mutable table deletion.
                epoch_state = self._mysql_game_action_epoch(cursor, exclusive=True)
                # Refuse namespace overflow without changing the existing phase.
                if epoch_state["current_epoch"] >= _GAME_ACTION_MAX_EPOCH:
                    # Preserve all relational state for operator recovery.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
                # Advance again even when recovering a prior failed resetting phase.
                reset_epoch = epoch_state["current_epoch"] + 1
                # Bind the new namespace and unavailable phase to the exact prior row.
                cursor.execute(
                    "UPDATE casino_game_action_epoch_state SET current_epoch = %s, phase = 'resetting' WHERE state_id = 1 AND current_epoch = %s AND phase = %s",
                    (reset_epoch, epoch_state["current_epoch"], epoch_state["phase"]),
                )
                # Require the singleton compare-and-set to update exactly once.
                if cursor.rowcount != 1:
                    # Refuse ambiguous reset ownership.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
            # Preserve compatible schema-two/three reset behavior without lifecycle access.
            elif not schema_state.initialized or schema_state.status != "clean" or schema_state.current_version not in {2, 3}:
                # Refuse dirty, partial, future, or unsupported schemas before deletion.
                raise ConflictError("MySQL storage schema requires operator recovery")
            # Delete only mutable projections; lifecycle claims and receipts remain append-only.
            self._clear_mysql_mutable_state(cursor)
            # Commit phase one so bootstrap can use the same session without holding row deletes.
            connection.commit()
            # Expose only a no-close facade to nested same-thread provider calls.
            self._reset_local.connection = connection
            try:
                # Yield while the named lock and resetting phase exclude every lifecycle action.
                yield self
            finally:
                # End lease borrowing before finalization or failure cleanup.
                self._reset_local.connection = None
            # Release schema-four lifecycle visibility only after caller bootstrap succeeds.
            if reset_epoch is not None:
                # Clear any connector transaction residue left by caller-owned reads.
                connection.rollback()
                # Start one exact phase-two transaction.
                connection.start_transaction()
                # Require schema four again before changing durable readiness.
                self._require_game_action_schema(connection)
                # Lock the exact singleton for compare-and-set finalization.
                finalized_state = self._mysql_game_action_epoch(cursor, exclusive=True)
                # Require the bound epoch to remain unavailable and unchanged.
                if finalized_state != {"state_id": 1, "current_epoch": reset_epoch, "phase": "resetting"}:
                    # Leave the durable phase unavailable for operator recovery.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
                # Publish ready only for this exact reset attempt's namespace.
                cursor.execute(
                    "UPDATE casino_game_action_epoch_state SET phase = 'ready' WHERE state_id = 1 AND current_epoch = %s AND phase = 'resetting'",
                    (reset_epoch,),
                )
                # Require one exact singleton transition.
                if cursor.rowcount != 1:
                    # Preserve resetting on ambiguous finalization.
                    raise ConflictError("MySQL game action lifecycle requires operator recovery")
                # Commit the final ready phase after all bootstrap writes are durable.
                connection.commit()
        # Roll back only the current session transaction while retaining durable resetting phase.
        except BaseException:
            # Discard partial phase-one, bootstrap-call, or phase-two work on this lease.
            connection.rollback()
            # Preserve the original bounded failure.
            raise
        finally:
            # Clear borrowing even when yield or finalization exits exceptionally.
            self._reset_local.connection = None
            try:
                # Release only a named lock this session proved it acquired.
                if named_lock_acquired:
                    # End any implicit or failed transaction before the release query.
                    connection.rollback()
                    # Open one final dictionary cursor on the retained session.
                    release_cursor = connection.cursor(dictionary=True)
                    # Release the exact target-scoped user lock.
                    release_cursor.execute("SELECT RELEASE_LOCK(%s) AS released", (lock_name,))
                    # Require this session to report successful release.
                    release_row = release_cursor.fetchone()
                    # Treat missing ownership or connector coercion as a reset failure.
                    if type(release_row) is not dict or release_row.get("released") != 1:
                        # Prevent a pooled session with uncertain user-lock state from being trusted.
                        raise ConflictError("MySQL reset lock release failed")
            finally:
                try:
                    # Return or discard the sole outer lease after every outcome.
                    connection.close()
                finally:
                    # Release process-local target ownership even if pool cleanup fails.
                    with _MYSQL_RESET_REGISTRY_LOCK:
                        # Let later explicit reset attempts recover a durable resetting phase.
                        _MYSQL_RESET_TARGETS.discard(reset_target)

    # Reset MySQL mutable state through the complete phase-owned boundary.
    def reset(self) -> None:
        # Reuse the same reset transaction with an intentionally empty caller body.
        with self.reset_transaction():
            # Preserve direct reset behavior without additional bootstrap writes.
            pass

    # Convert a MySQL player row into the existing API shape.
    def _player_from_row(self, row: dict) -> dict:
        # Return a dict with the current public player field names.
        return {"player_id": row["player_id"], "display_name": row["display_name"], "type": row["player_type"], "balance": _money(row["balance"]), "created_at": row["created_at"], "updated_at": row["updated_at"], "status": row["status"]}

    # Load players from MySQL without mutating storage from a read path.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Ensure schema exists before reading players.
        self.ensure_ready()
        # Open a connection for the bootstrap and read transaction.
        connection = self.connect()
        # Start protected read logic so the connection is always closed.
        try:
            # Open a dictionary cursor so row mapping is explicit.
            cursor = connection.cursor(dictionary=True)
            # Read players in stable order for deterministic API responses.
            cursor.execute("SELECT player_id, display_name, player_type, balance, created_at, updated_at, status FROM casino_players ORDER BY player_id")
            try:
                # Convert database rows into the JSON-compatible state document.
                players = [self._player_from_row(row) for row in cursor.fetchall()]
                # Validate the same complete money shape required from JSON storage.
                return _validated_players_document({"schema_version": SCHEMA_VERSION, "players": players})
            # Normalize corrupt row values without reflecting driver or stored details.
            except (TypeError, ValueError, OverflowError, ValidationError, ConflictError):
                # Preserve database state and require operator-led repair.
                raise ConflictError("Wallet storage requires operator recovery") from None
        # Always close the connection after loading players.
        finally:
            # Close the MySQL connection for this operation.
            connection.close()

    # Scan or repair MySQL wallet residue in one row-locked transaction. (STORAGE-015, LEDGER-036)
    def normalize_wallet_balances(self, *, apply: bool = False) -> dict:
        # Reject operator mutation attempted from inside a game-action planner.
        self._reject_planner_mutation()
        # Require the ordinary compatible schema before opening the operator transaction.
        self.ensure_ready()
        # Borrow one connection for the complete scan or repair.
        connection = self.connect()
        # Protect rollback and lease cleanup for every result.
        try:
            # Start one transaction so every inspected wallet remains stable through commit.
            connection.start_transaction()
            # Open a dictionary cursor for explicit wallet and ledger projections.
            cursor = connection.cursor(dictionary=True)
            # Lock all wallet rows in deterministic identity order.
            cursor.execute("SELECT player_id, balance FROM casino_players ORDER BY player_id FOR UPDATE")
            # Materialize the bounded result set while the row locks remain held.
            rows = cursor.fetchall()
            # Collect exact residue pairs without mutating any row yet.
            residues = []
            # Visit every durable wallet exactly once.
            for row in rows:
                try:
                    # Decode the exact provider value without accepting coercion.
                    stored = _money_decimal(row["balance"])
                    # Derive the canonical cent value using the shared rounding rule.
                    normalized = _quantized_money_decimal(stored)
                # Normalize malformed database money to the fixed recovery boundary.
                except ValidationError:
                    # Keep every row unchanged for operator inspection.
                    raise ConflictError("Wallet storage requires operator recovery") from None
                # Refuse insolvent wallets instead of disguising them as rounding residue.
                if stored < 0:
                    # Preserve the complete transaction for explicit accounting recovery.
                    raise ConflictError("Wallet storage requires operator recovery")
                # Retain only rows whose source has genuine sub-cent residue.
                if stored != normalized:
                    # Store the exact row identity and decimal pair for the optional apply path.
                    residues.append((row["player_id"], stored, normalized))
            # End a read-only scan without publishing any row or audit mutation.
            if not apply:
                # Release all row locks before returning bounded counts.
                connection.rollback()
                # Return no wallet identities or source values.
                return {"provider": self.name, "checked": len(rows), "residue_count": len(residues), "normalized_count": 0, "clean": not residues, "applied": False}
            # Publish each normalization row and wallet update inside this same transaction.
            for player_id, stored, normalized in residues:
                # Build the deterministic provider-neutral audit event.
                event = _wallet_normalization_event(player_id, stored, normalized)
                # Read a possible earlier compatible row by deterministic ledger identity.
                cursor.execute("SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json FROM casino_ledger WHERE ledger_id = %s", (event["ledger_id"],))
                # Resolve an interrupted or repeated operator invocation.
                existing_row = cursor.fetchone()
                # Insert the immutable audit row when this exact repair was not recorded earlier.
                if existing_row is None:
                    # Persist the zero-cent visible adjustment plus exact residue details.
                    cursor.execute(
                        "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",  # Append one deterministic operator audit row.
                        (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], Decimal("0.00"), normalized, normalized, event["action_scope"], event["action_key"], event["action_fingerprint"], json.dumps(event["details"], sort_keys=True, separators=(",", ":"))),  # Bind only cents-safe columns and exact residue metadata.
                    )
                else:
                    # Convert the relational row to the complete provider-neutral replay shape.
                    existing = {**_ledger_from_row(existing_row), "action_scope": existing_row["action_scope"], "action_key": existing_row["action_key"], "action_fingerprint": existing_row["action_fingerprint"]}
                    # Reject any deterministic-identity collision before changing the wallet.
                    _validate_wallet_normalization_replay(existing, event)
                # Publish the exact cent value on the already locked wallet row.
                cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (normalized, utc_now(), player_id))
            # Commit all audit rows and wallet changes atomically.
            connection.commit()
            # Return bounded completion evidence after the durable commit.
            return {"provider": self.name, "checked": len(rows), "residue_count": len(residues), "normalized_count": len(residues), "clean": True, "applied": True}
        # Roll back every malformed row, collision, or provider failure.
        except Exception:
            # Preserve the complete pre-call relational state.
            connection.rollback()
            # Re-raise the original bounded error.
            raise
        # Always release the provider connection after commit or rollback.
        finally:
            # Return or discard the connection through the existing pool boundary.
            connection.close()

    # Insert one player through the deterministic provider-owned identity boundary.
    def insert_player(self, player: dict) -> dict:
        # Reject player insertion attempted from inside a planner.
        self._reject_planner_mutation()
        # Reuse the primary-key transaction shared with invited-account provisioning.
        return self.ensure_player(player)

    # Insert every missing bootstrap row without replacing durable rows. (STORAGE-012, issue #431)
    def bootstrap_players(self, state: dict) -> None:
        # Reject bootstrap mutation attempted from inside a planner.
        self._reject_planner_mutation()
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
                    (player["player_id"], player["display_name"], player.get("type", "human"), _quantized_money_decimal(player.get("balance", 0)), player.get("created_at", utc_now()), player.get("updated_at", utc_now()), player.get("status", "active")),  # Bind only cents-normalized candidate fields.
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
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
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
            # Quantize the updated wallet through the provider-neutral cents boundary.
            player["balance"] = _quantized_money(player.get("balance", 0))
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
        # Reject deterministic player creation attempted from inside a planner.
        self._reject_planner_mutation()
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
                (player["player_id"], player["display_name"], player.get("type", "human"), _quantized_money_decimal(player.get("balance", 0)), player["created_at"], player["updated_at"], player.get("status", "active")),  # Bind only cents-normalized deterministic fields.
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
        # Reject wallet and ledger mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = _quantized_money(amount)
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
            after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
            # Reject transactions that would overdraw the fake-money wallet.
            if after < 0:
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
        # Reject exactly-once ledger mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = _quantized_money(amount)
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
            after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
            # Reject actions that would overdraw the fake-money wallet.
            if after < 0:
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

    # Find one committed MySQL ledger action through its unique identity index. (LEDGER-033)
    def find_ledger_action(self, player_id: str, game: str | None, action_key: str) -> dict | None:
        # Normalize the indexed caller-owned key before opening a connection.
        action_key = _normalize_action_key(action_key)
        # Normalize the game-or-core scope exactly as the write path does.
        scope = _action_scope(game)
        # Ensure the migrated unique action index exists before querying it.
        self.ensure_ready()
        # Open one read-only provider connection for the point lookup.
        connection = self.connect()
        # Protect cleanup so every result and failure closes the provider connection.
        try:
            # Open a dictionary cursor for public ledger-event mapping.
            cursor = connection.cursor(dictionary=True)
            # Query the existing unique identity index without locking the player row.
            cursor.execute(
                "SELECT ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json FROM casino_ledger WHERE player_id = %s AND action_scope = %s AND action_key = %s",  # Use the same indexed predicate as transact_ledger_once.
                (player_id, scope, action_key),  # Bind the canonical wallet, scope, and action key.
            )
            # Read at most the one row guaranteed by the unique index.
            row = cursor.fetchone()
            # Return no event for an unused action identity.
            if row is None:
                # Preserve the optional-result provider contract.
                return None
            # Convert the indexed row into the established public ledger shape.
            return _ledger_from_row(row)
        # Always close the point-lookup connection.
        finally:
            # Release the provider connection without adding a write-path connection.
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
        # Reject history mutation attempted from inside a planner.
        self._reject_planner_mutation()
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
        # Reject document mutation attempted from inside a planner.
        self._reject_planner_mutation()
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
        # Reject document read-modify-write attempted from inside a planner.
        self._reject_planner_mutation()
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


# Convert provider money values into cents-quantized floats for API compatibility. (LEDGER-036)
def _money(value: Any) -> float:
    # Reuse the one provider-neutral Decimal quantizer for database and JSON shapes.
    return _quantized_money(value)


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
        "amount": _quantized_money(amount),
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


# Build one deterministic ledger-visible audit row for a sub-cent wallet repair. (LEDGER-036)
def _wallet_normalization_event(player_id: str, stored: Decimal, normalized: Decimal) -> dict:
    # Encode the exact repair semantics without relying on binary floating-point text.
    semantic = {"player_id": player_id, "stored_balance": str(stored), "normalized_balance": str(normalized), "residue": str(normalized - stored), "rounding": "ROUND_HALF_EVEN", "canonical_unit": "integer_cents"}
    # Derive one stable identity so an interrupted JSON repair can resume without a duplicate row.
    fingerprint = hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    # Build the existing public ledger shape using cents-safe visible money columns.
    event = _ledger_event(player_id, 0.0, "WALLET_CENTS_NORMALIZATION", _quantized_money(normalized), _quantized_money(normalized), None, f"wallet-cents:{fingerprint[:32]}", semantic)
    # Replace the random ordinary identity with the deterministic repair identity.
    event["ledger_id"] = f"led_wallet_cents_{fingerprint[:40]}"
    # Bind the row to the existing provider action-index columns when MySQL persists it.
    event["action_scope"] = "core"
    # Store the bounded deterministic repair key used by the unique ledger index.
    event["action_key"] = f"wallet-cents:{fingerprint}"
    # Store the semantic digest for exact replay and forensic comparison.
    event["action_fingerprint"] = fingerprint
    # Return the complete append-only audit row.
    return event


# Require an earlier deterministic normalization row to match the exact repair semantics. (LEDGER-036)
def _validate_wallet_normalization_replay(existing: dict, expected: dict) -> None:
    # Compare every semantic and money field while permitting the original timestamp to differ.
    fields = ("ledger_id", "player_id", "game", "round_id", "transaction_type", "amount", "balance_before", "balance_after", "action_scope", "action_key", "action_fingerprint", "details")
    # Reject a collided identity rather than skipping a required audit row.
    if any(existing.get(field) != expected.get(field) for field in fields):
        # Preserve both sources for operator-led reconciliation.
        raise ConflictError("Wallet normalization audit requires operator recovery")


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


# Seed players idempotently through the configured provider.
def bootstrap_players(default_factory: Callable[[], dict]) -> None:
    # Get the active storage provider.
    provider = get_storage_provider()
    # Ensure backing storage exists before checking player bootstrap state.
    provider.ensure_ready()
    # Delegate the complete row set so each provider owns one race-free bootstrap boundary. (issue #431)
    provider.bootstrap_players(default_factory())
