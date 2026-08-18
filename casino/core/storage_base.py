# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-neutral storage configuration, contract, validation, and event helpers."""

# Import annotations so provider contract hints can refer to the declaring class.
from __future__ import annotations
# Import required dependency so the default reset boundary remains a context manager.
from contextlib import contextmanager
# Import required dependency so MySQL configuration remains an immutable value object.
from dataclasses import dataclass
# Import required dependency so provider money keeps the canonical cents rule.
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
# Import required dependency so action and normalization identities stay deterministic.
import hashlib
# Import required dependency so action and database row payloads keep canonical JSON shapes.
import json
# Import required dependency so MySQL provider configuration remains environment-backed.
import os
# Import required dependency so the base reset contract keeps legacy local cleanup behavior.
import shutil
# Import loaded-module access so the historical storage.DATA_DIR test seam remains compatible.
import sys
# Import concrete path typing for the compatibility reset-root seam.
from pathlib import Path
# Import required dependency so provider methods retain their existing callable contracts.
from typing import Any, Callable

# Import runtime paths and MySQL defaults used only by the provider-neutral contract/configuration.
from casino.config import DATA_DIR, DEFAULT_MYSQL_DATABASE, DEFAULT_MYSQL_HOST, DEFAULT_MYSQL_PORT, DEFAULT_MYSQL_USER
# Import the canonical timestamp helper used by provider-neutral ledger events.
from casino.core.clock import utc_now
# Import the canonical identifier helper used by provider-neutral ledger events.
from casino.core.ids import new_id
# Import stable public errors used by provider-neutral validation and replay boundaries.
from casino.errors import ConflictError, ValidationError

# Store the canonical fake-money quantum shared by migration and ordinary writes. (LEDGER-036)
_MONEY_QUANTUM = Decimal("0.01")
# Bound fake-money values to the signed-cent range already enforced by game actions.
_MAX_MONEY = Decimal("90000000000000000")


# Resolve the active legacy data root while the public storage module remains the compatibility owner.
def _active_data_dir() -> Path:
    # Read the historical module only when it has completed enough initialization to be registered.
    storage_module = sys.modules.get("casino.core.storage")
    # Preserve callers that patch casino.core.storage.DATA_DIR during isolated reset tests.
    return getattr(storage_module, "DATA_DIR", DATA_DIR)

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
        # Resolve the compatibility module's active local root at call time.
        data_dir = _active_data_dir()
        # Preserve the shipped route's local artifact cleanup for MySQL-like providers.
        if data_dir.exists():
            # Remove the complete legacy local data root before caller recreation.
            shutil.rmtree(data_dir)
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
