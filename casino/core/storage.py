# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import annotations so provider type hints can refer to classes declared later.
from __future__ import annotations
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
# Import required dependency so storage providers surface existing API errors.
from casino.errors import InsufficientFundsError, NotFoundError, ValidationError

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

    # Execute a ledger transaction and persist the resulting balance atomically.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Raise because concrete providers must enforce atomic ledger writes.
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

    # Return the local JSON players path.
    def players_path(self) -> Path:
        # Return the existing players file path under the configured data root.
        return self.data_dir / "players.json"

    # Return the local JSONL ledger path.
    def ledger_path(self) -> Path:
        # Return the existing ledger file path under the configured data root.
        return self.data_dir / "ledger.jsonl"

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

    # Reset local JSON storage by clearing the provider data directory.
    def reset(self) -> None:
        # Guard destructive local cleanup with the provider lock.
        with self.lock:
            # Remove only the configured data directory when it exists.
            if self.data_dir.exists():
                # Use shutil because the data directory may contain game subfolders.
                shutil.rmtree(self.data_dir)
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
            # Build a temp path next to the target for an atomic replace.
            tmp = path.with_suffix(path.suffix + ".tmp")
            # Serialize JSON in the existing pretty/sorted local format.
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            # Replace the target atomically after the full payload is written.
            tmp.replace(path)

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
                handle.write(json.dumps(event, sort_keys=True) + "\n")

    # Load players from the existing JSON document shape.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Read the players document or build defaults when absent.
        state = self._read_json(self.players_path(), default_factory)
        # Replace invalid payloads with the default player document.
        if not isinstance(state, dict) or "players" not in state:
            # Rebuild defaults when the stored shape is unusable.
            state = default_factory()
        # Return the player document expected by existing callers.
        return state

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
            # Load the current players document using an empty fallback.
            state = self.load_players(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
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

    # Execute a ledger transaction and balance update under one JSON lock.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Normalize the transaction amount to the app's fake-money precision.
        amount = round(float(amount), 2)
        # Reject zero-value ledger rows before touching player state.
        if amount == 0:
            # Raise a validation error consistent with the previous ledger module.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Guard the player update and ledger append with one lock.
        with self.lock:
            # Load the player document using an empty fallback for clear not-found errors.
            state = self.load_players(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
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

    # Read recent ledger events from the local JSONL file.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Ensure local directories exist before reading.
        self.ensure_ready()
        # Return an empty list when no ledger file exists yet.
        if not self.ledger_path().exists():
            # Return no rows for fresh local runs.
            return []
        # Store decoded rows in file order.
        rows = []
        # Iterate through JSONL rows from disk.
        for line in self.ledger_path().read_text(encoding="utf-8", errors="replace").splitlines():
            # Start protected decoding so one bad row does not hide later rows.
            try:
                # Parse the ledger row JSON object.
                event = json.loads(line)
            # Skip malformed historical rows.
            except Exception:
                # Continue reading subsequent ledger rows.
                continue
            # Keep rows that match the optional player filter.
            if player_id is None or event.get("player_id") == player_id:
                # Add the event to the in-memory result set.
                rows.append(event)
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
    def connect(self):
        # Return a new DB-API connection for one provider operation.
        return self._connector().connect(**self.config.kwargs())

    # Return the SQL statements that create the provider schema.
    @staticmethod
    def schema_statements() -> list[str]:  # Return schema DDL in dependency order.
        # Return schema statements in dependency order for fresh databases.
        return [
            # Create the players table that owns wallet balances.
            """
            CREATE TABLE IF NOT EXISTS casino_players (
              player_id VARCHAR(64) PRIMARY KEY,
              display_name VARCHAR(255) NOT NULL,
              player_type VARCHAR(32) NOT NULL,
              balance DECIMAL(18,2) NOT NULL,
              created_at VARCHAR(64) NOT NULL,
              updated_at VARCHAR(64) NOT NULL,
              status VARCHAR(32) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            # Create the ledger table that stores append-only wallet events.
            """
            CREATE TABLE IF NOT EXISTS casino_ledger (
              sequence_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              ledger_id VARCHAR(64) NOT NULL UNIQUE,
              ts VARCHAR(64) NOT NULL,
              player_id VARCHAR(64) NOT NULL,
              game VARCHAR(64) NULL,
              round_id VARCHAR(128) NULL,
              transaction_type VARCHAR(128) NOT NULL,
              amount DECIMAL(18,2) NOT NULL,
              balance_before DECIMAL(18,2) NOT NULL,
              balance_after DECIMAL(18,2) NOT NULL,
              details_json JSON NOT NULL,
              INDEX idx_casino_ledger_player_sequence (player_id, sequence_id),
              CONSTRAINT fk_casino_ledger_player FOREIGN KEY (player_id) REFERENCES casino_players(player_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            # Create the history table used by game settlement summaries.
            """
            CREATE TABLE IF NOT EXISTS casino_history (
              sequence_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              timestamp VARCHAR(64) NOT NULL,
              game VARCHAR(64) NOT NULL,
              round_id VARCHAR(128) NOT NULL,
              player_id VARCHAR(64) NOT NULL,
              bet_type VARCHAR(128) NOT NULL,
              bet_label VARCHAR(255) NOT NULL,
              amount DECIMAL(18,2) NOT NULL,
              outcome VARCHAR(128) NOT NULL,
              payout DECIMAL(18,2) NOT NULL,
              balance_after DECIMAL(18,2) NOT NULL,
              details_json JSON NOT NULL,
              schema_version VARCHAR(32) NOT NULL,
              INDEX idx_casino_history_game_sequence (game, sequence_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            # Create a small JSON document table for settings such as audio controls.
            """
            CREATE TABLE IF NOT EXISTS casino_documents (
              document_key VARCHAR(191) PRIMARY KEY,
              payload_json JSON NOT NULL,
              updated_at VARCHAR(64) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
        ]

    # Ensure the MySQL schema exists before reads and writes.
    def ensure_ready(self) -> None:
        # Open a connection for schema creation.
        connection = self.connect()
        # Start protected schema setup so the connection is always closed.
        try:
            # Open a cursor for DDL statements.
            cursor = connection.cursor()
            # Execute each schema statement in dependency order.
            for statement in self.schema_statements():
                # Create the table or leave the existing compatible table in place.
                cursor.execute(statement)
            # Commit schema creation before returning to callers.
            connection.commit()
        # Always close the connection after schema setup.
        finally:
            # Close the MySQL connection for this operation.
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
        # Branch when no players exist yet.
        if int(cursor.fetchone()[0]) == 0:
            # Build the default player document from the caller's factory.
            state = default_factory()
            # Insert each default player row.
            for player in state.get("players", []):
                # Insert one player with the current JSON-compatible field names.
                cursor.execute(
                    "INSERT INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Insert one seeded player row.
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

    # Save a full player document into MySQL.
    def save_players(self, state: dict) -> None:
        # Ensure schema exists before replacing player rows.
        self.ensure_ready()
        # Open a connection for the replace operation.
        connection = self.connect()
        # Start protected write logic so the connection is always closed.
        try:
            # Open a cursor for delete and insert statements.
            cursor = connection.cursor()
            # Clear dependent ledger rows because a full player replacement is reset/bootstrap-only.
            cursor.execute("DELETE FROM casino_ledger")
            # Clear existing player rows before inserting the provided state.
            cursor.execute("DELETE FROM casino_players")
            # Insert each player from the provided state.
            for player in state.get("players", []):
                # Insert a normalized player row.
                cursor.execute(
                    "INSERT INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",  # Insert one replacement player row.
                    (player["player_id"], player["display_name"], player.get("type", "human"), round(float(player.get("balance", 0)), 2), player.get("created_at", utc_now()), player.get("updated_at", utc_now()), player.get("status", "active")),  # Bind replacement player fields.
                )
            # Commit the replacement as one unit.
            connection.commit()
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


# Convert decimal database values into two-decimal floats for API compatibility.
def _money(value: Any) -> float:
    # Convert Decimals through string form to avoid binary surprises.
    if isinstance(value, Decimal):
        # Return the rounded float equivalent of the decimal amount.
        return round(float(value), 2)
    # Return the rounded float equivalent of regular numeric values.
    return round(float(value), 2)


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
    # Seed default players only when storage has no players yet.
    if not provider.has_players():
        # Persist the default player document through the active provider.
        provider.save_players(default_factory())
