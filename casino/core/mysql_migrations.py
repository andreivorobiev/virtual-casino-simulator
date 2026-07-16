"""Versioned MySQL migration and DDL-free runtime compatibility for MYSQL-005."""

# Import annotations so immutable migration records can reference their own types.
from __future__ import annotations
# Import UTC time handling for bounded backup-and-restore proof validity.
from datetime import datetime, timezone
# Import hashing for immutable migration, target, state, and plan identities.
import hashlib
# Import keyed hashing so target bindings cannot be dictionary-reversed from provider identifiers.
import hmac
# Import JSON for the canonical catalog, migration files, and proof contract.
import json
# Import environment access only for deployment-owned migration credentials.
import os
# Import portable paths for packaged migration assets and external proof files.
from pathlib import Path
# Import regular expressions for strict checksum and migration-file validation.
import re
# Import immutable records for migration configuration and inspected state.
from dataclasses import dataclass

# Resolve the release root without depending on the service working directory.
ROOT = Path(__file__).resolve().parents[2]
# Resolve the only canonical MySQL migration catalog shipped in the release.
MIGRATION_ROOT = ROOT / "migrations" / "mysql"
# Name the catalog whose file hashes make applied migrations immutable.
CATALOG_PATH = MIGRATION_ROOT / "catalog.json"
# Identify the machine-verifiable recovery proof shape consumed before any DDL.
BACKUP_PROOF_SCHEMA = "casino-mysql-backup-restore-proof-v1"
# Identify the catalog format independently of application and JSON data versions.
CATALOG_SCHEMA = "casino-mysql-migration-catalog-v1"
# Accept only lowercase SHA-256 strings in persisted migration evidence.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Name the two migration-control tables separately from application storage tables.
CONTROL_TABLES = frozenset({"casino_schema_migrations", "casino_schema_migration_state"})
# Name deployment-only variables so migration credentials can never fall back to runtime credentials.
MIGRATION_ENV = {
    # Require a deployment-selected MySQL endpoint.
    "host": "CASINO_MYSQL_MIGRATION_HOST",
    # Require an explicit deployment-only account.
    "user": "CASINO_MYSQL_MIGRATION_USER",
    # Require an external deployment-only secret.
    "password": "CASINO_MYSQL_MIGRATION_PASSWORD",
    # Require the exact deployment-selected schema.
    "database": "CASINO_MYSQL_MIGRATION_DATABASE",
    # Require a deployment-only HMAC key that is never persisted in proof records.
    "target_binding_key": "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY",
}


# Surface only fixed migration-policy diagnostics without connection details.
class MigrationError(RuntimeError):
    # Keep one dedicated exception type for CLI and startup fail-closed handling.
    pass


# Store one immutable migration after catalog and file-hash validation.
@dataclass(frozen=True)
class Migration:
    # Preserve the contiguous numeric order.
    version: int
    # Preserve the stable human-readable migration identity.
    name: str
    # Preserve the checksum applied to the target schema.
    checksum: str
    # Preserve exact single statements without delimiter-based parsing.
    statements: tuple[str, ...]


# Store connection options while making accidental formatting intrinsically redacted.
class RedactedConnectionOptions(dict):
    # Return one fixed representation rather than target or credential fields.
    def __repr__(self) -> str:
        # Preserve only the mapping purpose.
        return "<redacted MySQL migration connection options>"

    # Reuse the fixed representation for ordinary string conversion.
    def __str__(self) -> str:
        # Return no mapping values.
        return self.__repr__()


# Store the deployment-only connection values without exposing them to output.
@dataclass(frozen=True, repr=False)
class MigrationConfig:
    # Store the deployment-selected host.
    host: str
    # Store the deployment-selected TCP port.
    port: int
    # Store the deployment-only account name.
    user: str
    # Store the deployment-only password.
    password: str
    # Store the deployment-selected database name.
    database: str
    # Store the deployment-only key used solely to bind proof to a target.
    target_binding_key: str

    # Return one fixed representation rather than dataclass fields.
    def __repr__(self) -> str:
        # Preserve only the configuration purpose.
        return "<redacted MySQL migration configuration>"

    # Reuse the fixed representation for ordinary string conversion.
    def __str__(self) -> str:
        # Return no target or credential fields.
        return self.__repr__()

    # Load only migration-prefixed variables and never read runtime CASINO_MYSQL_* credentials.
    @classmethod
    def from_env(cls) -> MigrationConfig:
        # Collect required values under fixed internal names.
        values = {field: str(os.environ.get(environment, "")).strip() for field, environment in MIGRATION_ENV.items()}
        # Reject any missing deployment-only value before importing or connecting a driver.
        if any(not value for value in values.values()):
            # Avoid naming the missing value or echoing any supplied configuration.
            raise MigrationError("Deployment-only MySQL migration configuration is incomplete")
        # Require a high-entropy HMAC key rather than a short human password.
        if len(values["target_binding_key"].encode("utf-8")) < 32:
            # Stop before any target binding or connection attempt.
            raise MigrationError("Deployment-only MySQL target-binding key is invalid")
        # Keep target-binding and database-authentication secrets cryptographically separate.
        if hmac.compare_digest(values["target_binding_key"], values["password"]):
            # Reject secret reuse without revealing either value.
            raise MigrationError("Deployment-only MySQL target-binding key is invalid")
        # Read the migration-specific port independently of the runtime port variable.
        raw_port = str(os.environ.get("CASINO_MYSQL_MIGRATION_PORT", "3306")).strip()
        # Parse the bounded network port without retaining its input in errors.
        try:
            # Convert the fixed or explicit migration port to an integer.
            port = int(raw_port)
        # Reject malformed port configuration with a value-free diagnostic.
        except ValueError as exc:
            # Stop before any connection attempt.
            raise MigrationError("Deployment-only MySQL migration port is invalid") from exc
        # Reject out-of-range ports before a driver call.
        if not 1 <= port <= 65535:
            # Preserve the same value-free configuration diagnostic.
            raise MigrationError("Deployment-only MySQL migration port is invalid")
        # Return the isolated migration configuration.
        return cls(port=port, **values)

    # Convert only this deployment-only record into driver arguments.
    def kwargs(self) -> dict:
        # Return a fresh redacted-representation mapping accepted by connector keyword expansion.
        return RedactedConnectionOptions({"host": self.host, "port": self.port, "user": self.user, "password": self.password, "database": self.database})


# Store a fully validated read-only view of migration control state.
@dataclass(frozen=True)
class SchemaState:
    # Distinguish a database with no migration metadata from a versioned database.
    initialized: bool
    # Store the last fully applied contiguous migration.
    current_version: int
    # Store uninitialized, clean, applying, or dirty status.
    status: str
    # Store the migration whose DDL may have partially auto-committed.
    applying_version: int | None
    # Store the checksum of the applied catalog prefix.
    catalog_sha256: str
    # Store applied version, name, and checksum rows in numeric order.
    applied: tuple[tuple[int, str, str], ...]
    # Refuse undocumented legacy or partially initialized application tables.
    application_tables_present: bool


# Hash exact bytes into the lowercase checksum format used throughout the packet.
def sha256_bytes(payload: bytes) -> str:
    # Return the stable lowercase hexadecimal digest.
    return hashlib.sha256(payload).hexdigest()


# Return the checksum of one contiguous applied migration prefix.
def migration_chain_digest(migrations: tuple[Migration, ...], through_version: int | None = None) -> str:
    # Use the complete catalog when no applied-prefix boundary is supplied.
    boundary = len(migrations) if through_version is None else through_version
    # Reject impossible prefix requests instead of silently truncating evidence.
    if boundary < 0 or boundary > len(migrations):
        # Keep the failure independent of file or host paths.
        raise MigrationError("MySQL migration prefix is invalid")
    # Bind version, name, and exact file checksum with deterministic JSON encoding.
    rows = [[migration.version, migration.name, migration.checksum] for migration in migrations[:boundary]]
    # Hash canonical compact JSON bytes so platforms produce the same plan identity.
    return sha256_bytes(json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


# Load and verify the canonical catalog plus every immutable JSON migration file.
def load_catalog(catalog_path: Path = CATALOG_PATH) -> tuple[tuple[Migration, ...], int, int, str]:
    # Read exact catalog bytes so release provenance can bind the same asset.
    catalog_bytes = catalog_path.read_bytes()
    # Parse the catalog only after retaining its exact checksum identity.
    catalog = json.loads(catalog_bytes.decode("utf-8"))
    # Reject another catalog format before consuming its fields.
    if catalog.get("schema") != CATALOG_SCHEMA:
        # Keep diagnostics independent of private extraction paths.
        raise MigrationError("MySQL migration catalog format is unsupported")
    # Parse the exact and minimum runtime compatibility versions.
    expected_version = int(catalog.get("expected_version", -1))
    # Parse the minimum version separately from application and JSON data schema values.
    minimum_version = int(catalog.get("minimum_runtime_version", -1))
    # Require an exact-only compatibility window for this restricted-preview gate.
    if expected_version < 1 or minimum_version != expected_version:
        # Refuse an unreviewed compatibility range.
        raise MigrationError("MySQL migration compatibility window is invalid")
    # Collect verified immutable migrations in catalog order.
    migrations = []
    # Iterate over catalog rows without scanning unlisted files for execution.
    for expected_index, row in enumerate(catalog.get("migrations", []), start=1):
        # Require contiguous versions with no skipped migration.
        if int(row.get("version", -1)) != expected_index:
            # Refuse a gapped or reordered catalog.
            raise MigrationError("MySQL migration catalog is not contiguous")
        # Accept only a basename matching the catalog version and JSON operation format.
        file_name = str(row.get("file", ""))
        # Reject traversal, aliases, and mismatched numeric prefixes.
        if not re.fullmatch(rf"{expected_index:04d}_[a-z0-9_]+\.json", file_name):
            # Stop before opening a path selected by malformed metadata.
            raise MigrationError("MySQL migration filename is invalid")
        # Resolve the migration beside the canonical catalog.
        migration_path = catalog_path.parent / file_name
        # Read exact bytes for applied-checksum immutability.
        migration_bytes = migration_path.read_bytes()
        # Compute the actual file checksum without newline normalization.
        checksum = sha256_bytes(migration_bytes)
        # Require the catalog checksum to be canonical and exact.
        if not SHA256_RE.fullmatch(str(row.get("sha256", ""))) or checksum != row.get("sha256"):
            # Refuse altered migration bytes before any database connection.
            raise MigrationError("MySQL migration checksum does not match the catalog")
        # Parse the checksum-verified migration document.
        document = json.loads(migration_bytes.decode("utf-8"))
        # Require internal identity to match catalog identity exactly.
        if int(document.get("version", -1)) != expected_index or str(document.get("name", "")) != str(row.get("name", "")):
            # Reject a renamed or substituted migration.
            raise MigrationError("MySQL migration identity does not match the catalog")
        # Normalize the explicit statement array without splitting SQL text.
        statements = tuple(str(statement).strip() for statement in document.get("statements", []))
        # Require at least one single driver statement and reject empty entries.
        if not statements or any(not statement for statement in statements):
            # Refuse a migration that cannot establish a deterministic state transition.
            raise MigrationError("MySQL migration statements are invalid")
        # Reject delimiter directives because JSON array elements are already exact statements.
        if any("DELIMITER" in statement.upper() for statement in statements):
            # Require stored-program work to remain one driver-supported statement per element.
            raise MigrationError("MySQL migration statements must not use client delimiters")
        # Append the verified immutable migration.
        migrations.append(Migration(expected_index, str(row["name"]), checksum, statements))
    # Freeze the catalog for callers and tests.
    frozen = tuple(migrations)
    # Require the expected version to name the catalog tail exactly.
    if len(frozen) != expected_version:
        # Prevent an expected-version constant from drifting from immutable files.
        raise MigrationError("MySQL migration catalog tail does not match expected version")
    # Return the verified catalog and exact catalog-file checksum.
    return frozen, expected_version, minimum_version, sha256_bytes(catalog_bytes)


# Return the expected schema metadata for runtime and release provenance.
def schema_contract() -> dict:
    # Verify the catalog before exposing its version or digest.
    migrations, expected, minimum, catalog_sha256 = load_catalog()
    # Return a fresh public record containing no connection details.
    return {
        # Preserve the distinct minimum runtime-compatible MySQL version.
        "minimum_version": minimum,
        # Preserve the exact restricted-preview MySQL schema version.
        "expected_version": expected,
        # Bind the migration catalog file included in the release.
        "catalog_sha256": catalog_sha256,
        # Bind the ordered migration file identity chain.
        "migration_chain_sha256": migration_chain_digest(migrations),
    }


# Read migration metadata and validate every applied checksum using SELECT statements only.
def inspect_schema(connection, migrations: tuple[Migration, ...] | None = None) -> SchemaState:
    # Load the immutable catalog when the caller did not already validate it.
    catalog = load_catalog()[0] if migrations is None else migrations
    # Open one ordinary cursor for read-only metadata inspection.
    cursor = connection.cursor()
    # Query only table names in the currently selected database.
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\' ORDER BY TABLE_NAME")
    # Normalize tuple or dictionary driver rows into a stable name set.
    table_names = {str(row[0] if not isinstance(row, dict) else row["TABLE_NAME"]) for row in cursor.fetchall()}
    # Compute which migration-control tables exist without creating either table.
    present_controls = table_names.intersection(CONTROL_TABLES)
    # Reject a partially created metadata boundary after an interrupted metadata DDL step.
    if present_controls and present_controls != CONTROL_TABLES:
        # Require a separately reviewed forward-fix instead of guessing state.
        raise MigrationError("MySQL migration metadata is incomplete and requires a forward-fix packet")
    # Record whether any non-control Casino table exists.
    application_tables_present = bool(table_names.difference(CONTROL_TABLES))
    # Represent a genuinely empty target without issuing a CREATE or INSERT.
    if not present_controls:
        # Return the checksum of the empty applied prefix.
        return SchemaState(False, 0, "uninitialized", None, migration_chain_digest(catalog, 0), tuple(), application_tables_present)
    # Read the singleton state row without accepting caller-selected identifiers.
    cursor.execute("SELECT current_version, status, applying_version, catalog_sha256 FROM casino_schema_migration_state WHERE state_id = 1")
    # Fetch the only allowed state record.
    row = cursor.fetchone()
    # Reject missing state after both control tables exist.
    if row is None:
        # Require explicit forward-fix evidence rather than inventing a version.
        raise MigrationError("MySQL migration state is missing and requires a forward-fix packet")
    # Normalize positional rows returned by mysql.connector.
    current_version = int(row[0])
    # Normalize the finite persisted status.
    status = str(row[1])
    # Preserve null for a clean state or the interrupted migration version.
    applying_version = None if row[2] is None else int(row[2])
    # Normalize the persisted applied-prefix checksum.
    catalog_sha256 = str(row[3])
    # Read every applied migration row in strict version order.
    cursor.execute("SELECT version, name, checksum FROM casino_schema_migrations ORDER BY version")
    # Normalize immutable applied rows for exact comparison.
    applied = tuple((int(item[0]), str(item[1]), str(item[2])) for item in cursor.fetchall())
    # Reject negative, future, or row-count-divergent current versions.
    if current_version < 0 or current_version > len(catalog) or len(applied) != current_version:
        # Refuse gaps and unknown future schema states before serving traffic.
        raise MigrationError("MySQL migration version state is incompatible")
    # Require the applied versions to be a contiguous prefix starting at one.
    if [item[0] for item in applied] != list(range(1, current_version + 1)):
        # Refuse reordered or gapped history.
        raise MigrationError("MySQL migration history is not contiguous")
    # Compare every applied name and checksum with immutable packaged migration bytes.
    for version, name, checksum in applied:
        # Resolve the one catalog row at the applied numeric position.
        migration = catalog[version - 1]
        # Reject an edited, renamed, or substituted already-applied migration.
        if name != migration.name or checksum != migration.checksum:
            # Require a reviewed forward-fix rather than accepting history rewrite.
            raise MigrationError("MySQL applied migration checksum is incompatible")
    # Require the state checksum to match the exact applied catalog prefix.
    if catalog_sha256 != migration_chain_digest(catalog, current_version):
        # Refuse state-row tampering or stale prefix identity.
        raise MigrationError("MySQL applied migration chain is incompatible")
    # Require clean state to carry no in-flight migration.
    if status == "clean" and applying_version is not None:
        # Reject contradictory metadata.
        raise MigrationError("MySQL migration state is inconsistent")
    # Require applying or dirty state to name the next known migration exactly.
    if status in {"applying", "dirty"} and applying_version != current_version + 1:
        # Refuse an arbitrary dirty marker or unknown repair target.
        raise MigrationError("MySQL migration dirty state is inconsistent")
    # Reject any persisted status outside the finite state machine.
    if status not in {"clean", "applying", "dirty"}:
        # Preserve a value-free diagnostic.
        raise MigrationError("MySQL migration status is incompatible")
    # Reject application tables with a falsely clean version-zero metadata state.
    if current_version == 0 and status == "clean" and application_tables_present:
        # Prevent unversioned legacy tables from being adopted implicitly.
        raise MigrationError("Unversioned MySQL application tables require a forward-fix packet")
    # Return the validated read-only state.
    return SchemaState(True, current_version, status, applying_version, catalog_sha256, applied, application_tables_present)


# Prove runtime compatibility using read-only statements and no migration credentials.
def verify_runtime_compatibility(connection) -> SchemaState:
    # Load the exact catalog and compatibility window shipped with this release.
    migrations, expected, minimum, _ = load_catalog()
    # Inspect version and checksums using only the runtime connection's read privileges.
    state = inspect_schema(connection, migrations)
    # Reject missing metadata, old state, future state, or any dirty/applying transition.
    if not state.initialized or state.status != "clean" or state.current_version != expected or state.current_version < minimum:
        # Avoid disclosing the observed schema version or database identity in service logs.
        raise MigrationError("MySQL runtime schema is not compatible with this release")
    # Return sanitized state for internal readiness evidence.
    return state


# Hash the selected target without retaining a reversible identifier in proof records.
def target_fingerprint(config: MigrationConfig) -> str:
    # Normalize only endpoint and database identity; account rotation does not change the target.
    payload = json.dumps([config.host.strip().lower(), config.port, config.database], separators=(",", ":")).encode("utf-8")
    # Return a deployment-keyed binding that cannot be dictionary-reversed without the external key.
    return hmac.new(config.target_binding_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# Compute the tamper-evident HMAC over every proof field except the HMAC itself.
def proof_hmac(proof: dict, config: MigrationConfig) -> str:
    # Copy the complete proof so caller-owned data is not mutated.
    unsigned = dict(proof)
    # Exclude only the self-referential signature field.
    unsigned.pop("proof_hmac_sha256", None)
    # Canonicalize nested content so all proof sections are integrity-bound.
    payload = json.dumps(unsigned, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode("utf-8")
    # Sign with the deployment-only target-binding key that is never persisted.
    return hmac.new(config.target_binding_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# Bind source quiesce to target, pre-state, exact plan, and quiesced timestamp.
def quiesce_boundary_hmac(config: MigrationConfig, state: SchemaState, state_sha256: str, migration_chain_sha256: str, expected_version: int, quiesced_at: str) -> str:
    # Build a canonical record containing no reversible target identifier.
    record = {
        # Bind the keyed target identity.
        "target_hmac_sha256": target_fingerprint(config),
        # Bind the exact structural pre-state.
        "state_sha256": state_sha256,
        # Bind the pre-migration version and finite status.
        "version": state.current_version,
        # Bind the finite migration status.
        "status": state.status,
        # Bind the complete immutable intended plan.
        "migration_chain_sha256": migration_chain_sha256,
        # Bind the exact expected plan tail.
        "expected_version": expected_version,
        # Bind the declared start of the still-active quiesce window.
        "quiesced_at": quiesced_at,
    }
    # Canonicalize and sign the boundary with the deployment-only key.
    payload = json.dumps(record, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode("utf-8")
    # Return only the HMAC, never the key or provider identifiers.
    return hmac.new(config.target_binding_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# Hash the exact pre-migration schema structure and version state using SELECT statements only.
def schema_state_digest(connection, state: SchemaState) -> str:
    # Open a cursor dedicated to deterministic information-schema reads.
    cursor = connection.cursor()
    # Read column structure for every Casino-owned table in stable order.
    cursor.execute("SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, COALESCE(COLUMN_DEFAULT, '<NULL>'), EXTRA FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\' ORDER BY TABLE_NAME, ORDINAL_POSITION")
    # Normalize driver scalars to strings so JSON encoding is platform-independent.
    columns = [["<NULL>" if value is None else str(value) for value in row] for row in cursor.fetchall()]
    # Read index structure separately because exact constraints affect compatibility.
    cursor.execute("SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\' ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX")
    # Normalize index scalars without exposing any row data.
    indexes = [["<NULL>" if value is None else str(value) for value in row] for row in cursor.fetchall()]
    # Read table engine and collation because both affect restored-schema equivalence.
    cursor.execute("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\' ORDER BY TABLE_NAME")
    # Normalize storage-engine metadata without reading application rows.
    tables = [["<NULL>" if value is None else str(value) for value in row] for row in cursor.fetchall()]
    # Read primary, unique, and foreign-key constraints with ordered referenced-column bindings.
    cursor.execute("SELECT tc.TABLE_NAME, tc.CONSTRAINT_NAME, tc.CONSTRAINT_TYPE, COALESCE(kcu.COLUMN_NAME, '<NULL>'), COALESCE(kcu.ORDINAL_POSITION, 0), COALESCE(kcu.REFERENCED_TABLE_NAME, '<NULL>'), COALESCE(kcu.REFERENCED_COLUMN_NAME, '<NULL>') FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON kcu.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA AND kcu.TABLE_NAME = tc.TABLE_NAME AND kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME WHERE tc.CONSTRAINT_SCHEMA = DATABASE() AND tc.TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\' ORDER BY tc.TABLE_NAME, tc.CONSTRAINT_NAME, kcu.ORDINAL_POSITION")
    # Normalize constraint and foreign-key evidence for exact restore comparison.
    constraints = [["<NULL>" if value is None else str(value) for value in row] for row in cursor.fetchall()]
    # Bind structural metadata to the validated migration state without application data.
    record = {
        # Preserve exact applied rows and checksums.
        "applied": [list(item) for item in state.applied],
        # Preserve an in-flight migration marker when present.
        "applying_version": state.applying_version,
        # Preserve exact schema columns only.
        "columns": columns,
        # Preserve exact constraints and foreign-key bindings.
        "constraints": constraints,
        # Preserve the last completed migration.
        "current_version": state.current_version,
        # Preserve exact schema indexes only.
        "indexes": indexes,
        # Preserve table engines and collations.
        "tables": tables,
        # Preserve the finite migration status.
        "status": state.status,
    }
    # Return a deterministic digest that contains no host, database, credential, or user data.
    return sha256_bytes(json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8"))


# Parse one UTC proof timestamp and reject non-UTC or malformed values.
def _proof_time(value) -> datetime:
    # Start protected ISO parsing so input is never echoed in diagnostics.
    try:
        # Convert a trailing Z to the standard-library UTC offset form.
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    # Reject malformed proof time fields.
    except (TypeError, ValueError) as exc:
        # Preserve a fixed proof-contract error.
        raise MigrationError("Backup and restore proof timestamps are invalid") from exc
    # Require an explicit UTC offset rather than accepting local time.
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        # Refuse timezone-ambiguous proof evidence.
        raise MigrationError("Backup and restore proof timestamps are invalid")
    # Normalize the timestamp to UTC for bounded comparisons.
    return parsed.astimezone(timezone.utc)


# Validate a current backup-and-clean-restore proof against the exact target and pre-state.
def validate_backup_proof(proof_path: Path, config: MigrationConfig, state: SchemaState, state_sha256: str, migrations: tuple[Migration, ...], expected_version: int, now: datetime | None = None) -> dict:
    # Start protected parsing so path, decoding, and hostile type values cannot leak.
    try:
        # Parse the external operator-owned proof without copying it into the release.
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    # Convert every file, decoding, and JSON failure into one fixed diagnostic.
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
        # Never echo the proof path or hostile content.
        raise MigrationError("Backup and restore proof could not be read") from exc
    # Require an object before any field lookup.
    if not isinstance(proof, dict):
        # Reject scalar and array proof payloads with a fixed diagnostic.
        raise MigrationError("Backup and restore proof fields are invalid")
    # Require a canonical full-proof HMAC before trusting any section.
    supplied_proof_hmac = str(proof.get("proof_hmac_sha256", ""))
    # Compare in constant time so all content tampering fails uniformly.
    if not SHA256_RE.fullmatch(supplied_proof_hmac) or not hmac.compare_digest(supplied_proof_hmac, proof_hmac(proof, config)):
        # Reject edited or copied evidence before field-specific validation.
        raise MigrationError("Backup and restore proof integrity is invalid")
    # Require the accepted machine-verifiable contract version.
    if proof.get("schema") != BACKUP_PROOF_SCHEMA:
        # Reject another proof shape before reading optional fields.
        raise MigrationError("Backup and restore proof contract is unsupported")
    # Require a one-way binding to the exact selected database target.
    if proof.get("target_hmac_sha256") != target_fingerprint(config):
        # Do not disclose either expected or observed target identity.
        raise MigrationError("Backup and restore proof does not match the migration target")
    # Read the exact pre-migration state contract.
    pre = proof.get("pre_migration", {})
    # Read each remaining nested proof record before conversion.
    plan = proof.get("plan", {})
    # Read the checksum-bound backup evidence.
    backup = proof.get("backup", {})
    # Read the clean-target restore evidence.
    restore = proof.get("restore", {})
    # Read the active quiesce evidence.
    quiesce = proof.get("quiesce", {})
    # Require object containers for every nested contract.
    if not all(isinstance(value, dict) for value in (pre, plan, backup, restore, quiesce)):
        # Reject hostile container types before field conversion.
        raise MigrationError("Backup and restore proof fields are invalid")
    # Require a clean or genuinely uninitialized source version.
    try:
        # Parse proof numeric fields inside a value-free error boundary.
        pre_version = int(pre.get("version", -1))
        # Parse plan endpoints before comparison.
        plan_from = int(plan.get("from_version", -1))
        # Parse the intended exact target version.
        plan_to = int(plan.get("to_version", -1))
    # Reject malformed numeric or container types without echoing content.
    except (AttributeError, TypeError, ValueError) as exc:
        # Keep the proof-contract failure fixed and secret-safe.
        raise MigrationError("Backup and restore proof fields are invalid") from exc
    # Require exact version, status, and structural-state identity.
    if pre_version != state.current_version or pre.get("status") != state.status or pre.get("state_sha256") != state_sha256:
        # Reject stale proof before metadata or application DDL.
        raise MigrationError("Backup and restore proof does not match the pre-migration state")
    # Bind both endpoints plus the complete immutable catalog chain.
    if plan_from != state.current_version or plan_to != expected_version or plan.get("migration_chain_sha256") != migration_chain_digest(migrations):
        # Refuse proof prepared for another migration plan.
        raise MigrationError("Backup and restore proof does not match the migration plan")
    # Validate only the artifact checksum and completion marker required by this gate.
    if backup.get("completed") is not True or not SHA256_RE.fullmatch(str(backup.get("artifact_sha256", ""))):
        # Avoid treating local snapshot presence as completed recovery evidence.
        raise MigrationError("Backup and restore proof does not include a completed backup")
    # Require successful restore plus exact structural equivalence to the pre-state.
    if restore.get("verified") is not True or restore.get("restored_state_sha256") != state_sha256 or restore.get("backup_artifact_sha256") != backup.get("artifact_sha256"):
        # Stop before DDL when clean-target restore evidence is absent or stale.
        raise MigrationError("Backup and restore proof does not include an exact clean-target restore")
    # Require a checksum-bound active quiesce record rather than an operator prose assertion.
    if quiesce.get("active") is not True or not SHA256_RE.fullmatch(str(quiesce.get("boundary_hmac_sha256", ""))):
        # Stop because a changing source invalidates the pre-state proof.
        raise MigrationError("Backup and restore proof does not include an active quiesce boundary")
    # Parse the source-quiesced timestamp.
    quiesced_at = _proof_time(quiesce.get("quiesced_at"))
    # Recompute the target, state, plan, and timestamp-bound quiesce HMAC.
    expected_quiesce_hmac = quiesce_boundary_hmac(config, state, state_sha256, migration_chain_digest(migrations), expected_version, str(quiesce.get("quiesced_at")))
    # Reject a copied or independently edited quiesce marker.
    if not hmac.compare_digest(str(quiesce.get("boundary_hmac_sha256")), expected_quiesce_hmac):
        # Require the source to remain at the exact proof-bound boundary.
        raise MigrationError("Backup and restore proof quiesce boundary is invalid")
    # Parse the completed backup timestamp.
    backup_completed_at = _proof_time(backup.get("completed_at"))
    # Parse the proof validity window.
    verified_at = _proof_time(restore.get("verified_at"))
    # Parse the explicit expiry boundary.
    expires_at = _proof_time(restore.get("expires_at"))
    # Use an injected UTC clock for deterministic tests or current UTC in production.
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    # Require strict quiesce, backup, restore, current-time, and short-expiry ordering.
    if not quiesced_at <= backup_completed_at <= verified_at <= current_time <= expires_at or (expires_at - verified_at).total_seconds() > 4 * 60 * 60:
        # Refuse stale, future, or excessively long-lived proof.
        raise MigrationError("Backup and restore proof is not current")
    # Return the validated record only for tests or caller-local audit; never log it.
    return proof


# Create the minimal migration metadata boundary only after proof validation.
def _initialize_metadata(connection, migrations: tuple[Migration, ...]) -> None:
    # Open one cursor for the two fixed metadata DDL statements.
    cursor = connection.cursor()
    # Create immutable applied-migration history with no application data.
    cursor.execute("CREATE TABLE casino_schema_migrations (version INT PRIMARY KEY, name VARCHAR(191) NOT NULL, checksum CHAR(64) NOT NULL, applied_at VARCHAR(64) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    # Create the singleton fail-closed state marker for MySQL DDL auto-commit handling.
    cursor.execute("CREATE TABLE casino_schema_migration_state (state_id TINYINT PRIMARY KEY, current_version INT NOT NULL, status VARCHAR(16) NOT NULL, applying_version INT NULL, catalog_sha256 CHAR(64) NOT NULL, updated_at VARCHAR(64) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    # Insert the clean empty-prefix state only after both metadata tables exist.
    cursor.execute("INSERT INTO casino_schema_migration_state (state_id, current_version, status, applying_version, catalog_sha256, updated_at) VALUES (1, 0, 'clean', NULL, %s, %s)", (migration_chain_digest(migrations, 0), datetime.now(timezone.utc).isoformat()))
    # Commit the minimal metadata boundary before any application DDL begins.
    connection.commit()


# Persist a pre-DDL applying marker so partial auto-commit cannot appear clean.
def _mark_applying(connection, state: SchemaState, migration: Migration) -> None:
    # Open a cursor for the guarded state transition.
    cursor = connection.cursor()
    # Update only the clean state and exact current version observed under the named lock.
    cursor.execute("UPDATE casino_schema_migration_state SET status = 'applying', applying_version = %s, updated_at = %s WHERE state_id = 1 AND status = 'clean' AND current_version = %s", (migration.version, datetime.now(timezone.utc).isoformat(), state.current_version))
    # Require exactly one state row to transition.
    if cursor.rowcount != 1:
        # Refuse concurrent or contradictory state changes.
        raise MigrationError("MySQL migration state changed before apply")
    # Commit the marker before the first application DDL statement.
    connection.commit()


# Persist a dirty marker after any statement failure without claiming DDL rollback.
def _mark_dirty(connection, migration: Migration) -> None:
    # Open a fresh cursor after the failed statement.
    cursor = connection.cursor()
    # Preserve the exact interrupted migration while leaving current_version unchanged.
    cursor.execute("UPDATE casino_schema_migration_state SET status = 'dirty', applying_version = %s, updated_at = %s WHERE state_id = 1", (migration.version, datetime.now(timezone.utc).isoformat()))
    # Commit the fail-closed marker independently of auto-committed application DDL.
    connection.commit()


# Record one fully completed migration and advance the applied catalog prefix.
def _mark_complete(connection, migration: Migration, migrations: tuple[Migration, ...]) -> None:
    # Open one cursor for history plus singleton state update.
    cursor = connection.cursor()
    # Insert immutable version, name, and checksum evidence after every statement succeeded.
    cursor.execute("INSERT INTO casino_schema_migrations (version, name, checksum, applied_at) VALUES (%s, %s, %s, %s)", (migration.version, migration.name, migration.checksum, datetime.now(timezone.utc).isoformat()))
    # Advance to a clean prefix only after history insertion is ready to commit.
    cursor.execute("UPDATE casino_schema_migration_state SET current_version = %s, status = 'clean', applying_version = NULL, catalog_sha256 = %s, updated_at = %s WHERE state_id = 1 AND status = 'applying' AND applying_version = %s", (migration.version, migration_chain_digest(migrations, migration.version), datetime.now(timezone.utc).isoformat(), migration.version))
    # Require the exact in-flight migration to complete.
    if cursor.rowcount != 1:
        # Refuse to mark another state as applied.
        raise MigrationError("MySQL migration completion state is inconsistent")
    # Commit history and clean-prefix state together after application DDL finished.
    connection.commit()


# Apply pending migrations under one target-derived advisory lock and verified recovery proof.
def apply_migrations(connection, config: MigrationConfig, proof_path: Path | None, lock_timeout_seconds: int = 30) -> SchemaState:
    # Load the complete immutable plan before touching the database.
    migrations, expected, _, _ = load_catalog()
    # Force transaction control for history and state DML without changing DDL auto-commit semantics.
    connection.autocommit = False
    # Verify the connector accepted non-autocommit mode.
    if bool(connection.autocommit):
        # Stop before lock or schema mutation when state DML cannot be controlled.
        raise MigrationError("MySQL migration connection must disable autocommit")
    # Derive a bounded non-identifying advisory-lock name from the keyed target digest.
    lock_name = "casino-migrate-" + target_fingerprint(config)[:40]
    # Open one cursor for MySQL advisory lock acquisition.
    lock_cursor = connection.cursor()
    # Acquire the named lock before the proof-bound state is re-read.
    lock_cursor.execute("SELECT GET_LOCK(%s, %s)", (lock_name, int(lock_timeout_seconds)))
    # Read the scalar lock result without logging names or target values.
    lock_row = lock_cursor.fetchone()
    # Refuse timeout, error, or missing lock evidence.
    if not lock_row or int(lock_row[0] or 0) != 1:
        # Stop without metadata or application writes.
        raise MigrationError("MySQL migration advisory lock is unavailable")
    # Retain any primary fixed migration outcome until lock release is attempted.
    primary_error = None
    # Retain the successful final state until lock release is confirmed.
    final_state = None
    # Run the proof-bound migration while the named lock is held.
    try:
        # Inspect checksum-bound state after winning the target lock.
        state = inspect_schema(connection, migrations)
        # Reject a dirty or applying state before considering new work.
        if state.status in {"dirty", "applying"}:
            # Require a new reviewed checksum-bound forward-fix packet.
            raise MigrationError("MySQL migration state is dirty and requires a forward-fix packet")
        # Reject unversioned application tables rather than adopting them implicitly.
        if not state.initialized and state.application_tables_present:
            # Preserve the explicit legacy-forward-fix boundary.
            raise MigrationError("Unversioned MySQL application tables require a forward-fix packet")
        # Return a repeat-safe read-only recheck when the exact expected version is already clean.
        if state.initialized and state.current_version == expected:
            # Reuse the exact runtime compatibility verifier before returning.
            # Store the repeat-safe final state for return after confirmed lock release.
            final_state = verify_runtime_compatibility(connection)
            # Release the advisory lock before taking the repeat-safe fast return.
            release_cursor = connection.cursor()
            # Release only this target-derived lock.
            release_cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
            # Require confirmation so a successful recheck never leaves an untracked lock.
            release_row = release_cursor.fetchone()
            # Refuse an unconfirmed release and let the common failure path retry once.
            if not release_row or int(release_row[0] or 0) != 1:
                # Preserve a fixed lock-state diagnostic.
                raise MigrationError("MySQL migration advisory lock release could not be confirmed")
            # Return after exact compatibility and lock release both succeed.
            return final_state
        # Require a proof path before metadata DDL or any pending application migration.
        if proof_path is None:
            # Stop before computing or changing schema metadata.
            raise MigrationError("A current backup and restore proof is required before migration")
        # Compute the exact locked pre-state structure without reading application rows.
        state_sha256 = schema_state_digest(connection, state)
        # Validate backup plus clean-target restore against this target, state, and plan.
        validate_backup_proof(proof_path, config, state, state_sha256, migrations, expected)
        # Establish metadata only after the empty target proof was accepted.
        if not state.initialized:
            # Create the minimal state boundary before application schema DDL.
            _initialize_metadata(connection, migrations)
            # Re-read the clean version-zero state after metadata creation.
            state = inspect_schema(connection, migrations)
        # Apply every remaining migration in strict contiguous order.
        for migration in migrations[state.current_version:]:
            # Persist the applying marker before any auto-committing DDL.
            _mark_applying(connection, state, migration)
            # Open a cursor for exact JSON-array statements without SQL splitting.
            cursor = connection.cursor()
            # Execute the immutable statement sequence under fail-closed dirty handling.
            try:
                # Apply each exact driver statement in reviewed order.
                for statement in migration.statements:
                    # Execute one statement; MySQL DDL may commit independently.
                    cursor.execute(statement)
                # Record completed history only after all statements succeeded.
                _mark_complete(connection, migration, migrations)
            # Mark any interrupted migration dirty and refuse automatic replay.
            except Exception as exc:
                # Start protected dirty marking because connection loss can make state unknown.
                try:
                    # Persist the known interrupted version without claiming transactional rollback.
                    _mark_dirty(connection, migration)
                # Report unknown state without replacing the primary failed-migration outcome.
                except Exception:
                    # Chain from the original migration failure, not the secondary marker failure.
                    raise MigrationError("MySQL migration failed and dirty state could not be confirmed; an explicit forward-fix is required") from exc
                # Surface only the fixed forward-fix requirement.
                raise MigrationError("MySQL migration failed and was marked dirty for an explicit forward-fix") from exc
            # Reinspect exact state before applying the next version.
            state = inspect_schema(connection, migrations)
        # Require exact runtime compatibility at the final state.
        # Store exact final compatibility until lock release succeeds.
        final_state = verify_runtime_compatibility(connection)
    # Retain the fixed primary outcome without leaking connector details.
    except MigrationError as exc:
        # Preserve the already sanitized migration result.
        primary_error = exc
    # Convert any unexpected connector failure into a fixed primary outcome.
    except Exception as exc:
        # Preserve no driver message or target detail.
        primary_error = MigrationError("MySQL migration outcome could not be confirmed")
        # Keep the original exception only as an internal cause.
        primary_error.__cause__ = exc
    # Attempt exact lock release after success or failure.
    try:
        # Use a fresh cursor because a failed DDL cursor may be unusable.
        release_cursor = connection.cursor()
        # Release only this target-derived lock.
        release_cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
        # Consume the scalar result so the connection has no unread rows.
        release_row = release_cursor.fetchone()
        # Require confirmation that this session owned and released the lock.
        if not release_row or int(release_row[0] or 0) != 1:
            # Treat unknown lock state as a fail-closed outcome.
            raise MigrationError("MySQL migration advisory lock release could not be confirmed")
    # Preserve both migration and lock-release outcomes in one fixed diagnostic.
    except Exception as exc:
        # Combine only sanitized migration text when a primary failure already exists.
        if primary_error is not None:
            # Retain primary outcome semantics and add the unconfirmed lock boundary.
            raise MigrationError(f"{primary_error}; advisory lock release could not be confirmed") from primary_error
        # Fail a successful migration handoff when lock release is not confirmed.
        raise MigrationError("MySQL migration advisory lock release could not be confirmed") from exc
    # Re-raise the original fixed migration outcome after confirmed lock release.
    if primary_error is not None:
        # Preserve its original cause for internal diagnostics.
        raise primary_error
    # Return only after final compatibility and lock release both succeeded.
    return final_state


# Return a non-mutating pending plan after validating any required proof.
def dry_run(connection, config: MigrationConfig, proof_path: Path | None) -> tuple[Migration, ...]:
    # Load the immutable plan without writing metadata.
    migrations, expected, _, _ = load_catalog()
    # Inspect state using SELECT statements only.
    state = inspect_schema(connection, migrations)
    # Refuse dirty, applying, or unversioned application state.
    if state.status in {"dirty", "applying"} or (not state.initialized and state.application_tables_present):
        # Preserve the same explicit forward-fix boundary as apply.
        raise MigrationError("MySQL migration state requires a forward-fix packet")
    # Select the immutable pending suffix without executing it.
    pending = migrations[state.current_version:]
    # Return immediately when no schema mutation would occur.
    if not pending:
        # Preserve an exact empty tuple for repeat-safe automation.
        return tuple()
    # Require proof even for dry-run plan authorization, while remaining database read-only.
    if proof_path is None:
        # Stop without metadata creation or advisory locks.
        raise MigrationError("A current backup and restore proof is required before migration")
    # Compute the exact current structure through read-only information-schema queries.
    state_sha256 = schema_state_digest(connection, state)
    # Validate the proof against the current pre-state and intended plan.
    validate_backup_proof(proof_path, config, state, state_sha256, migrations, expected)
    # Return the validated pending catalog records.
    return pending
