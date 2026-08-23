# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Checksum-bound PostgreSQL migrations for guarded PostgreSQL 16 targets."""

# Import annotations so immutable records can refer to their own types.
from __future__ import annotations
# Import the abstract mapping shape used by psycopg dict-row connections.
from collections.abc import Mapping
# Import UTC timestamps for durable migration-state transitions.
from datetime import datetime, timezone
# Import immutable records for configuration, migrations, and inspected state.
from dataclasses import dataclass
# Import hashing for immutable catalog and keyed target identities.
import hashlib
# Import keyed hashing so persisted target bindings are not reversible identifiers.
import hmac
# Import JSON for canonical catalog and chain identities.
import json
# Import environment access only for deployment-owned PostgreSQL migration variables.
import os
# Import portable paths for packaged migration assets.
from pathlib import Path
# Import strict regular expressions for checksums, filenames, and disposable identifiers.
import re

# Resolve the immutable release root without relying on the process working directory.
ROOT = Path(__file__).resolve().parents[2]
# Resolve the only PostgreSQL migration catalog shipped with this release.
MIGRATION_ROOT = ROOT / "migrations" / "postgres"
# Name the checksum-bound catalog file.
CATALOG_PATH = MIGRATION_ROOT / "catalog.json"
# Identify the PostgreSQL catalog independently of MySQL and application schema versions.
CATALOG_SCHEMA = "casino-postgres-migration-catalog-v1"
# Allow application only to explicitly authorized new empty targets.
APPLY_POLICY_GUARDED_EMPTY = "guarded-empty-target-only"
# Require one explicit authorization marker before any connector or DDL operation.
DISPOSABLE_MARKER = "CASINO-POSTGRES-1057-DISPOSABLE"
# Require a separate owner-approved marker for a new production bootstrap.
PRODUCTION_MARKER = "CASINO-POSTGRES-1078-NEW-PRODUCTION"
# Accept only canonical lowercase SHA-256 strings in catalog and state evidence.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Accept only bounded lowercase PostgreSQL identifiers ending in this issue-owned suffix.
DISPOSABLE_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,54}_1057$")
# Accept only bounded ordinary PostgreSQL identifiers for the reviewed production target.
PRODUCTION_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
# Accept only an immutable exact release commit for production authorization.
RELEASE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# Name the two migration-control tables separately from application storage.
CONTROL_TABLES = frozenset({"casino_schema_migrations", "casino_schema_migration_state"})
# Enumerate required deployment-only variables without falling back to runtime PostgreSQL credentials.
MIGRATION_ENV = {
    # Require a deployment-selected loopback host.
    "host": "CASINO_POSTGRES_MIGRATION_HOST",
    # Require an issue-scoped disposable role.
    "user": "CASINO_POSTGRES_MIGRATION_USER",
    # Require a deployment-only database password.
    "password": "CASINO_POSTGRES_MIGRATION_PASSWORD",
    # Require an issue-scoped disposable database.
    "database": "CASINO_POSTGRES_MIGRATION_DATABASE",
    # Require a separate HMAC key for non-reversible target binding.
    "target_binding_key": "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY",
}
# Name the mutually exclusive disposable and production authorization inputs.
MIGRATION_AUTHORIZATION_ENV = {
    # Preserve the original issue-scoped disposable authorization marker.
    "disposable_marker": "CASINO_POSTGRES_MIGRATION_DISPOSABLE",
    # Read the owner-approved new-production marker independently.
    "production_marker": "CASINO_POSTGRES_MIGRATION_PRODUCTION",
    # Bind a production bootstrap to one immutable packaged release commit.
    "release_sha": "CASINO_POSTGRES_MIGRATION_RELEASE_SHA",
}


# Surface only fixed migration-policy diagnostics without target or driver details.
class MigrationError(RuntimeError):
    # Keep one dedicated exception type for CLI and test fail-closed boundaries.
    pass


# Store one immutable migration after catalog and exact-byte checksum validation.
@dataclass(frozen=True)
class Migration:
    # Preserve the contiguous numeric version.
    version: int
    # Preserve the stable reviewed identity.
    name: str
    # Preserve the exact descriptor checksum.
    checksum: str
    # Preserve exact driver statements without SQL splitting.
    statements: tuple[str, ...]


# Store connector options while making accidental formatting intrinsically redacted.
class RedactedConnectionOptions(dict):
    # Return one fixed representation rather than connection values.
    def __repr__(self) -> str:
        # Preserve only the mapping purpose.
        return "<redacted PostgreSQL migration connection options>"

    # Reuse the fixed representation for ordinary string conversion.
    def __str__(self) -> str:
        # Return no mapping values.
        return self.__repr__()


# Store deployment-only PostgreSQL migration settings without exposing their values.
@dataclass(frozen=True, repr=False)
class MigrationConfig:
    # Store the literal loopback host.
    host: str
    # Store the bounded TCP port.
    port: int
    # Store the issue-scoped disposable migration role.
    user: str
    # Store the deployment-only database password.
    password: str
    # Store the issue-scoped disposable database name.
    database: str
    # Store the external target-binding key.
    target_binding_key: str
    # Store the explicit issue-owned disposable authorization marker when selected.
    disposable_marker: str = ""
    # Store the distinct owner-approved production bootstrap marker when selected.
    production_marker: str = ""
    # Bind production bootstrap authority to one immutable release commit.
    release_sha: str = ""

    # Return one fixed representation rather than dataclass fields.
    def __repr__(self) -> str:
        # Preserve only the configuration purpose.
        return "<redacted PostgreSQL migration configuration>"

    # Reuse the fixed representation for ordinary string conversion.
    def __str__(self) -> str:
        # Return no target or credential fields.
        return self.__repr__()

    # Load only migration-prefixed variables and never read runtime CASINO_POSTGRES_* credentials.
    @classmethod
    def from_env(cls) -> MigrationConfig:
        # Collect required connection values under fixed internal names without logging any value.
        values = {field: str(os.environ.get(environment, "")).strip() for field, environment in MIGRATION_ENV.items()}
        # Reject any missing deployment-only value before importing a connector.
        if any(not value for value in values.values()):
            # Avoid naming the missing field or echoing supplied configuration.
            raise MigrationError("Deployment-only PostgreSQL migration configuration is incomplete")
        # Require a high-entropy HMAC key rather than a short human password.
        if len(values["target_binding_key"].encode("utf-8")) < 32:
            # Stop before target binding or connection access.
            raise MigrationError("Deployment-only PostgreSQL target-binding key is invalid")
        # Keep authentication and target-binding secrets cryptographically separate.
        if hmac.compare_digest(values["target_binding_key"], values["password"]):
            # Reject secret reuse without exposing either value.
            raise MigrationError("Deployment-only PostgreSQL target-binding key is invalid")
        # Read mutually exclusive target authorization values without reporting any supplied value.
        authorization = {field: str(os.environ.get(environment, "")).strip() for field, environment in MIGRATION_AUTHORIZATION_ENV.items()}
        # Require exactly one authorization mode before connector import or target access.
        if bool(authorization["disposable_marker"]) == bool(authorization["production_marker"]):
            # Refuse both missing and dual-mode configurations through one fixed boundary.
            raise MigrationError("Deployment-only PostgreSQL migration authorization is invalid")
        # Require no release identity for disposable tests and one exact identity for production.
        release_valid = (bool(authorization["disposable_marker"]) and not authorization["release_sha"]) or (bool(authorization["production_marker"]) and bool(RELEASE_SHA_RE.fullmatch(authorization["release_sha"])))
        # Reject a missing, symbolic, short, or cross-mode release identity before connector access.
        if not release_valid:
            # Publish only the stable authorization category.
            raise MigrationError("Deployment-only PostgreSQL migration release identity is invalid")
        # Read the migration-specific port independently of the runtime port.
        raw_port = str(os.environ.get("CASINO_POSTGRES_MIGRATION_PORT", "5432")).strip()
        # Parse the bounded network port without retaining its input in errors.
        try:
            # Convert the fixed or explicit port to an integer.
            port = int(raw_port)
        # Reject malformed text with a value-free diagnostic.
        except ValueError as exc:
            # Stop before any connection attempt.
            raise MigrationError("Deployment-only PostgreSQL migration port is invalid") from exc
        # Reject out-of-range ports before a driver call.
        if not 1 <= port <= 65535:
            # Preserve the same value-free port diagnostic.
            raise MigrationError("Deployment-only PostgreSQL migration port is invalid")
        # Return the isolated migration configuration.
        return cls(port=port, **values, **authorization)

    # Convert only this deployment-owned record into psycopg/libpq arguments.
    def kwargs(self) -> RedactedConnectionOptions:
        # Return a fresh intrinsically redacted mapping with libpq's canonical dbname key.
        return RedactedConnectionOptions({"host": self.host, "port": self.port, "user": self.user, "password": self.password, "dbname": self.database})


# Store a fully validated read-only view of migration control state.
@dataclass(frozen=True)
class SchemaState:
    # Distinguish a database with no metadata from a versioned target.
    initialized: bool
    # Store the last fully applied contiguous version.
    current_version: int
    # Store uninitialized, clean, applying, or dirty status.
    status: str
    # Store the exact in-flight or interrupted version.
    applying_version: int | None
    # Store the digest of the applied migration prefix.
    catalog_sha256: str
    # Store the non-reversible target identity persisted with metadata.
    target_hmac_sha256: str | None
    # Store applied version, name, and checksum rows in order.
    applied: tuple[tuple[int, str, str], ...]
    # Refuse undocumented legacy or partially initialized application tables.
    application_tables_present: bool


# Hash exact bytes into the lowercase checksum format used by the catalog.
def sha256_bytes(payload: bytes) -> str:
    # Return the stable lowercase hexadecimal digest.
    return hashlib.sha256(payload).hexdigest()


# Return the checksum of one contiguous applied migration prefix.
def migration_chain_digest(migrations: tuple[Migration, ...], through_version: int | None = None) -> str:
    # Use the complete catalog when no prefix boundary is supplied.
    boundary = len(migrations) if through_version is None else through_version
    # Reject impossible prefixes rather than silently truncating evidence.
    if type(boundary) is not int or boundary < 0 or boundary > len(migrations):
        # Keep the diagnostic independent of files and targets.
        raise MigrationError("PostgreSQL migration prefix is invalid")
    # Bind version, name, and exact descriptor checksum through canonical JSON.
    rows = [[migration.version, migration.name, migration.checksum] for migration in migrations[:boundary]]
    # Hash canonical compact bytes for platform-independent identity.
    return sha256_bytes(json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


# Parse one required exact integer without accepting booleans or coercible text.
def _exact_int(value, diagnostic: str) -> int:
    # Require JSON's integer shape rather than Python's Boolean subtype.
    if type(value) is not int:
        # Return only the caller-selected fixed diagnostic.
        raise MigrationError(diagnostic)
    # Return the validated integer unchanged.
    return value


# Load and verify the canonical catalog plus every immutable descriptor file.
def load_catalog(catalog_path: Path = CATALOG_PATH) -> tuple[tuple[Migration, ...], int, int, str]:
    # Start one fixed filesystem and JSON boundary that never reports paths or content.
    try:
        # Read exact catalog bytes for release provenance.
        catalog_bytes = catalog_path.read_bytes()
        # Parse the retained bytes as UTF-8 JSON.
        catalog = json.loads(catalog_bytes.decode("utf-8"))
    # Collapse malformed or unavailable assets into a value-free diagnostic.
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        # Preserve no extraction path or parser content.
        raise MigrationError("PostgreSQL migration catalog could not be loaded") from exc
    # Require the reviewed catalog format and guarded empty-target apply policy.
    if type(catalog) is not dict or catalog.get("schema") != CATALOG_SCHEMA or catalog.get("apply_policy") != APPLY_POLICY_GUARDED_EMPTY:
        # Refuse another provider or an unguarded application policy.
        raise MigrationError("PostgreSQL migration catalog policy is invalid")
    # Parse the exact and minimum compatibility bounds.
    expected_version = _exact_int(catalog.get("expected_version"), "PostgreSQL migration compatibility window is invalid")
    # Parse minimum version independently of application data versions.
    minimum_version = _exact_int(catalog.get("minimum_runtime_version"), "PostgreSQL migration compatibility window is invalid")
    # Require one closed non-empty compatibility window.
    if expected_version < 1 or minimum_version < 1 or minimum_version > expected_version:
        # Refuse empty, inverted, or negative bounds.
        raise MigrationError("PostgreSQL migration compatibility window is invalid")
    # Require an explicit catalog array before consuming any row.
    rows = catalog.get("migrations")
    # Refuse mappings, strings, and missing migration inventories.
    if type(rows) is not list:
        # Preserve one stable catalog diagnostic.
        raise MigrationError("PostgreSQL migration catalog is invalid")
    # Collect verified migrations and referenced filenames in catalog order.
    migrations = []
    # Collect names so unlisted JSON assets cannot become an ambiguous second chain.
    referenced_files = set()
    # Visit each declared row in its only valid contiguous position.
    for expected_index, row in enumerate(rows, start=1):
        # Require a mapping with the exact numeric version.
        if type(row) is not dict or _exact_int(row.get("version"), "PostgreSQL migration catalog is not contiguous") != expected_index:
            # Refuse gaps, booleans, and reordered rows.
            raise MigrationError("PostgreSQL migration catalog is not contiguous")
        # Accept only one basename matching its numeric position.
        file_name = row.get("file")
        # Reject traversal, aliases, and numeric-prefix drift.
        if type(file_name) is not str or not re.fullmatch(rf"{expected_index:04d}_[a-z0-9_]+\.json", file_name):
            # Stop before opening a malformed selected path.
            raise MigrationError("PostgreSQL migration filename is invalid")
        # Record the reviewed basename for the final exact inventory check.
        referenced_files.add(file_name)
        # Resolve the descriptor only beside the selected catalog.
        migration_path = catalog_path.parent / file_name
        # Start one fixed descriptor I/O and JSON boundary.
        try:
            # Read exact bytes for immutable checksum validation.
            migration_bytes = migration_path.read_bytes()
            # Parse the checksum-bound descriptor.
            document = json.loads(migration_bytes.decode("utf-8"))
        # Collapse filesystem and parser details into one fixed result.
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            # Preserve no path or parser input.
            raise MigrationError("PostgreSQL migration descriptor could not be loaded") from exc
        # Compute the exact descriptor checksum.
        checksum = sha256_bytes(migration_bytes)
        # Require canonical catalog checksum equality.
        if not SHA256_RE.fullmatch(str(row.get("sha256", ""))) or not hmac.compare_digest(checksum, str(row.get("sha256", ""))):
            # Refuse edited bytes before any connector access.
            raise MigrationError("PostgreSQL migration checksum does not match the catalog")
        # Require exact internal version and name identity.
        if type(document) is not dict or _exact_int(document.get("version"), "PostgreSQL migration identity does not match the catalog") != expected_index or document.get("name") != row.get("name") or type(row.get("name")) is not str:
            # Refuse renamed or substituted migration content.
            raise MigrationError("PostgreSQL migration identity does not match the catalog")
        # Require an explicit non-empty statement array without coercion.
        statement_rows = document.get("statements")
        # Refuse strings, mappings, and empty arrays.
        if type(statement_rows) is not list or not statement_rows or any(type(statement) is not str or not statement.strip() for statement in statement_rows):
            # Stop before returning an ambiguous transition.
            raise MigrationError("PostgreSQL migration statements are invalid")
        # Normalize harmless surrounding whitespace without splitting SQL.
        statements = tuple(statement.strip() for statement in statement_rows)
        # Reject client commands and MySQL-only dialect tokens from executable descriptors.
        forbidden = ("DELIMITER", "ENGINE=", "AUTO_INCREMENT", "UNSIGNED", "CHARSET=", "CHARACTER SET", "JSON_EXTRACT(", "JSON_UNQUOTE(", "`")
        # Refuse any statement containing a prohibited token.
        if any(any(token in statement.upper() for token in forbidden) or statement.lstrip().startswith("\\") for statement in statements):
            # Keep executable SQL PostgreSQL-driver-native.
            raise MigrationError("PostgreSQL migration statements contain unsupported dialect")
        # Append the fully verified immutable migration.
        migrations.append(Migration(expected_index, str(row["name"]), checksum, statements))
    # Freeze the catalog for callers and state validation.
    frozen = tuple(migrations)
    # Require the expected version to name the catalog tail exactly.
    if len(frozen) != expected_version:
        # Prevent version constants from drifting from immutable files.
        raise MigrationError("PostgreSQL migration catalog tail does not match expected version")
    # Require the directory's JSON inventory to equal catalog plus referenced descriptors.
    try:
        # Enumerate basenames only within the selected catalog directory.
        json_files = {path.name for path in catalog_path.parent.glob("*.json")}
    # Collapse directory access into the same fixed load boundary.
    except OSError as exc:
        # Preserve no local extraction path.
        raise MigrationError("PostgreSQL migration catalog could not be loaded") from exc
    # Reject shadow, abandoned, or unlisted JSON migration assets.
    if json_files != {catalog_path.name, *referenced_files}:
        # Require one listener-free immutable inventory.
        raise MigrationError("PostgreSQL migration catalog inventory is invalid")
    # Return the catalog and exact catalog-file checksum.
    return frozen, expected_version, minimum_version, sha256_bytes(catalog_bytes)


# Return expected schema metadata for tooling and provenance.
def schema_contract() -> dict:
    # Verify every immutable asset before exposing its identity.
    migrations, expected, minimum, catalog_sha256 = load_catalog()
    # Return a fresh value-free public record.
    return {
        # Preserve the exact required PostgreSQL schema version.
        "minimum_version": minimum,
        # Preserve the exact catalog tail.
        "expected_version": expected,
        # Bind the catalog file itself.
        "catalog_sha256": catalog_sha256,
        # Bind the ordered descriptor identity chain.
        "migration_chain_sha256": migration_chain_digest(migrations),
        # Publish the closed guarded empty-target application boundary.
        "apply_policy": APPLY_POLICY_GUARDED_EMPTY,
    }


# Resolve one exact migration authorization mode without exposing supplied values.
def migration_authorization_mode(config: MigrationConfig) -> str:
    # Require literal IPv4 loopback rather than hostname or remote resolution.
    host_valid = type(config.host) is str and config.host == "127.0.0.1"
    # Require valid field shapes for directly constructed configuration objects.
    fields_valid = type(config.port) is int and 1 <= config.port <= 65535 and type(config.password) is str and bool(config.password) and type(config.target_binding_key) is str and len(config.target_binding_key.encode("utf-8")) >= 32
    # Require password/key separation at the final public boundary too.
    secrets_valid = fields_valid and not hmac.compare_digest(config.password, config.target_binding_key)
    # Require exact field types before any constant-time marker comparison.
    authorization_types_valid = all(type(value) is str for value in (config.user, config.database, config.disposable_marker, config.production_marker, config.release_sha))
    # Stop before marker parsing when the common target boundary is malformed.
    if not all((host_valid, fields_valid, secrets_valid, authorization_types_valid)):
        # Preserve one value-free authorization result.
        raise MigrationError("PostgreSQL migration target is not authorized")
    # Recognize only the original issue-scoped disposable tuple.
    disposable_valid = hmac.compare_digest(config.disposable_marker, DISPOSABLE_MARKER) and not config.production_marker and not config.release_sha and bool(DISPOSABLE_IDENTIFIER_RE.fullmatch(config.user)) and bool(DISPOSABLE_IDENTIFIER_RE.fullmatch(config.database))
    # Return the closed disposable mode without weakening its identifier suffix.
    if disposable_valid:
        # Allow the original temporary-target proof to proceed unchanged.
        return "disposable"
    # Reject built-in administrator and template identities from the production target set.
    identifiers_safe = config.user not in {"postgres"} and config.database not in {"postgres", "template0", "template1"}
    # Recognize only the owner-approved production marker plus immutable release identity.
    production_valid = hmac.compare_digest(config.production_marker, PRODUCTION_MARKER) and not config.disposable_marker and identifiers_safe and bool(PRODUCTION_IDENTIFIER_RE.fullmatch(config.user)) and bool(PRODUCTION_IDENTIFIER_RE.fullmatch(config.database)) and bool(RELEASE_SHA_RE.fullmatch(config.release_sha))
    # Return the one-time production bootstrap mode only after its complete guard passes.
    if production_valid:
        # Distinguish production behavior without persisting a provider or host identifier.
        return "production"
    # Reject every unknown marker, mixed mode, reserved identity, or malformed release.
    raise MigrationError("PostgreSQL migration target is not authorized")


# Hash the selected target without persisting a reversible provider identifier.
def target_fingerprint(config: MigrationConfig) -> str:
    # Validate and retain only the finite authorization mode.
    mode = migration_authorization_mode(config)
    # Bind production metadata to its authorizing release while disposable identities remain release-neutral.
    release_identity = config.release_sha if mode == "production" else ""
    # Normalize endpoint, database, mode, and release identity; role rotation does not change target identity.
    payload = json.dumps([config.host.strip().lower(), config.port, config.database, mode, release_identity], separators=(",", ":")).encode("utf-8")
    # Return a deployment-keyed digest that requires the external key to reproduce.
    return hmac.new(config.target_binding_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# Reject every non-disposable or ambiguously named target before connector access or DDL.
def require_disposable_target(config: MigrationConfig) -> None:
    # Resolve the complete shared authorization boundary first.
    try:
        # Require the result to remain the original disposable mode.
        disposable_valid = migration_authorization_mode(config) == "disposable"
    # Collapse a general authorization refusal to the historical disposable diagnostic.
    except MigrationError:
        # Preserve the stable caller-facing category.
        disposable_valid = False
    # Stop through one value-free disposable-policy diagnostic on any mismatch.
    if not disposable_valid:
        # Refuse the target before any connection, lock, or schema mutation.
        raise MigrationError("PostgreSQL migration target is not an authorized disposable target")


# Require either the original disposable proof or the release-bound production bootstrap.
def require_authorized_target(config: MigrationConfig) -> str:
    # Delegate every common and mode-specific invariant to one closed resolver.
    return migration_authorization_mode(config)


# Normalize one exact SELECT row from tuple or psycopg dict-row results.
def _row_values(row, columns: tuple[str, ...]) -> tuple:
    # Accept mapping rows only when every selected column is present.
    if isinstance(row, Mapping):
        # Refuse missing keys without publishing native row content.
        if any(column not in row for column in columns):
            # Preserve one fixed connector-neutral result-shape diagnostic.
            raise MigrationError("PostgreSQL migration query result is invalid")
        # Return values in the reviewed SELECT order.
        return tuple(row[column] for column in columns)
    # Accept tuple-like positional rows only when they expose the exact selected width.
    if isinstance(row, (tuple, list)) and len(row) == len(columns):
        # Return one immutable normalized tuple.
        return tuple(row)
    # Reject arbitrary driver values and surprising result widths.
    raise MigrationError("PostgreSQL migration query result is invalid")


# Read migration metadata through one shared SELECT-only engine with an optional deployment binding.
def _inspect_schema(connection, catalog: tuple[Migration, ...], expected_target_hmac: str | None) -> SchemaState:
    # Open one cursor for metadata inspection.
    cursor = connection.cursor()
    # Query every ordinary table in the selected current schema so foreign residue cannot look empty.
    cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema() ORDER BY tablename")
    # Normalize positional or mapping driver rows into a stable set.
    table_names = {str(_row_values(row, ("tablename",))[0]) for row in cursor.fetchall()}
    # Compute which migration-control tables exist.
    present_controls = table_names.intersection(CONTROL_TABLES)
    # Reject a partially created metadata boundary.
    if present_controls and present_controls != CONTROL_TABLES:
        # Require an explicit forward-fix rather than guessing state.
        raise MigrationError("PostgreSQL migration metadata is incomplete and requires a forward-fix packet")
    # Record whether any non-control Casino table exists.
    application_tables_present = bool(table_names.difference(CONTROL_TABLES))
    # Represent a genuinely empty target without writing metadata.
    if not present_controls:
        # Return the checksum of the empty applied prefix.
        return SchemaState(False, 0, "uninitialized", None, migration_chain_digest(catalog, 0), None, tuple(), application_tables_present)
    # Read the one allowed state record.
    cursor.execute("SELECT current_version, status, applying_version, catalog_sha256, target_hmac_sha256 FROM casino_schema_migration_state WHERE state_id = 1")
    # Fetch the singleton state row.
    row = cursor.fetchone()
    # Reject missing state after both control tables exist.
    if row is None:
        # Require a reviewed forward-fix.
        raise MigrationError("PostgreSQL migration state is missing and requires a forward-fix packet")
    # Normalize the persisted scalar state.
    values = _row_values(row, ("current_version", "status", "applying_version", "catalog_sha256", "target_hmac_sha256"))
    # Normalize current version and finite status from the reviewed column order.
    current_version, status = int(values[0]), str(values[1])
    # Preserve null only for a clean state.
    applying_version = None if values[2] is None else int(values[2])
    # Normalize immutable prefix and target digests.
    catalog_sha256, target_hmac_sha256 = str(values[3]), str(values[4])
    # Read every applied migration row in strict numeric order.
    cursor.execute("SELECT version, name, checksum FROM casino_schema_migrations ORDER BY version")
    # Normalize applied rows for exact comparison.
    applied = tuple((int(values[0]), str(values[1]), str(values[2])) for values in (_row_values(item, ("version", "name", "checksum")) for item in cursor.fetchall()))
    # Reject negative, future, or row-count-divergent versions.
    if current_version < 0 or current_version > len(catalog) or len(applied) != current_version:
        # Refuse gaps and unknown future state.
        raise MigrationError("PostgreSQL migration version state is incompatible")
    # Require a contiguous applied prefix starting at one.
    if [item[0] for item in applied] != list(range(1, current_version + 1)):
        # Refuse reordered or gapped history.
        raise MigrationError("PostgreSQL migration history is not contiguous")
    # Compare every applied identity with packaged immutable bytes.
    for version, name, checksum in applied:
        # Resolve the exact packaged record at this numeric position.
        migration = catalog[version - 1]
        # Reject a renamed, edited, or substituted applied migration.
        if name != migration.name or not hmac.compare_digest(checksum, migration.checksum):
            # Require a forward-fix rather than accepting foreign history.
            raise MigrationError("PostgreSQL migration history does not match this release")
    # Require the persisted prefix digest to match exact applied bytes.
    if not SHA256_RE.fullmatch(catalog_sha256) or not hmac.compare_digest(catalog_sha256, migration_chain_digest(catalog, current_version)):
        # Refuse copied or tampered catalog state.
        raise MigrationError("PostgreSQL migration catalog state does not match this release")
    # Require a canonical persisted target binding even when runtime has no migration key.
    if not SHA256_RE.fullmatch(target_hmac_sha256):
        # Refuse malformed migration metadata through the shared read-only boundary.
        raise MigrationError("PostgreSQL migration target binding is invalid")
    # Compare the keyed target identity only for deployment/migration callers.
    if expected_target_hmac is not None and not hmac.compare_digest(target_hmac_sha256, expected_target_hmac):
        # Refuse metadata copied from another disposable migration target.
        raise MigrationError("PostgreSQL migration target binding does not match")
    # Require one of the finite reviewed state combinations.
    clean_valid = status == "clean" and applying_version is None
    # Require applying/dirty to identify exactly the next unapplied catalog version.
    interrupted_valid = status in {"applying", "dirty"} and applying_version == current_version + 1 and applying_version <= len(catalog)
    # Reject foreign status strings and contradictory state fields.
    if not clean_valid and not interrupted_valid:
        # Preserve one fail-closed state diagnostic.
        raise MigrationError("PostgreSQL migration state is invalid")
    # Reject unversioned application tables even when metadata exists at version zero.
    if current_version == 0 and application_tables_present:
        # Prevent implicit adoption of legacy application state.
        raise MigrationError("Unversioned PostgreSQL application tables require a forward-fix packet")
    # Return the fully validated read-only state.
    return SchemaState(True, current_version, status, applying_version, catalog_sha256, target_hmac_sha256, applied, application_tables_present)


# Inspect migration state with the deployment-only keyed target identity.
def inspect_schema(connection, config: MigrationConfig, migrations: tuple[Migration, ...] | None = None) -> SchemaState:
    # Load immutable assets before computing any target binding.
    catalog = load_catalog()[0] if migrations is None else migrations
    # Validate the complete state plus this migration configuration's keyed target identity.
    return _inspect_schema(connection, catalog, target_fingerprint(config))


# Inspect runtime state without reading migration configuration, marker, credentials, or HMAC key.
def inspect_runtime_schema(connection, migrations: tuple[Migration, ...] | None = None) -> SchemaState:
    # Load immutable assets when the runtime caller did not already validate them.
    catalog = load_catalog()[0] if migrations is None else migrations
    # Validate complete state while treating the canonical target HMAC as opaque deployment evidence.
    return _inspect_schema(connection, catalog, None)


# Prove deployment-runner compatibility including the keyed disposable-target binding.
def verify_migration_compatibility(connection, config: MigrationConfig) -> SchemaState:
    # Load the exact compatibility window shipped with this release.
    migrations, expected, minimum, _ = load_catalog()
    # Inspect checksum-bound state plus the deployment-only target binding.
    state = inspect_schema(connection, config, migrations)
    # Reject missing metadata, incomplete state, or out-of-window versions.
    if not state.initialized or state.status != "clean" or state.current_version < minimum or state.current_version > expected:
        # Avoid disclosing the observed version or migration target.
        raise MigrationError("PostgreSQL migration schema is not compatible with this release")
    # Return sanitized validated migration state.
    return state


# Prove exact runtime compatibility without any deployment-only secret or authorization marker.
def verify_runtime_compatibility(connection) -> SchemaState:
    # Load the exact required catalog tail shipped with this release.
    migrations, expected, _minimum, _ = load_catalog()
    # Inspect control-table completeness and immutable applied checksums without target-key access.
    state = inspect_runtime_schema(connection, migrations)
    # Require exact clean schema five rather than accepting a partial or future runtime state.
    if not state.initialized or state.status != "clean" or state.current_version != expected:
        # Avoid disclosing the observed schema state or opaque target evidence.
        raise MigrationError("PostgreSQL runtime schema is not compatible with this release")
    # Return sanitized validated state.
    return state


# Return a non-mutating pending suffix after fail-closed state validation.
def dry_run(connection, config: MigrationConfig) -> tuple[Migration, ...]:
    # Validate one reviewed target mode even for plan authorization.
    require_authorized_target(config)
    # Load the complete immutable plan.
    migrations = load_catalog()[0]
    # Inspect state using SELECT statements only.
    state = inspect_schema(connection, config, migrations)
    # Refuse dirty, applying, or unversioned application state.
    if state.status in {"dirty", "applying"} or (not state.initialized and state.application_tables_present):
        # Preserve one explicit forward-fix boundary.
        raise MigrationError("PostgreSQL migration state requires a forward-fix packet")
    # Return the exact pending immutable suffix without mutation.
    return migrations[state.current_version:]


# Create the minimal target-bound migration metadata transaction.
def _initialize_metadata(connection, config: MigrationConfig, migrations: tuple[Migration, ...]) -> None:
    # Open one cursor for fixed PostgreSQL metadata DDL and singleton insertion.
    cursor = connection.cursor()
    # Start protected transactional metadata creation.
    try:
        # Create immutable applied-migration history.
        cursor.execute("CREATE TABLE casino_schema_migrations (version INTEGER PRIMARY KEY, name VARCHAR(191) NOT NULL, checksum CHAR(64) NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'), applied_at VARCHAR(64) NOT NULL)")
        # Create the finite singleton migration state and keyed target binding.
        cursor.execute("CREATE TABLE casino_schema_migration_state (state_id SMALLINT PRIMARY KEY CHECK (state_id = 1), current_version INTEGER NOT NULL CHECK (current_version >= 0), status VARCHAR(16) NOT NULL CHECK (status IN ('clean', 'applying', 'dirty')), applying_version INTEGER NULL CHECK (applying_version IS NULL OR applying_version > 0), catalog_sha256 CHAR(64) NOT NULL CHECK (catalog_sha256 ~ '^[0-9a-f]{64}$'), target_hmac_sha256 CHAR(64) NOT NULL CHECK (target_hmac_sha256 ~ '^[0-9a-f]{64}$'), updated_at VARCHAR(64) NOT NULL)")
        # Insert the target-bound clean empty-prefix state.
        cursor.execute("INSERT INTO casino_schema_migration_state (state_id, current_version, status, applying_version, catalog_sha256, target_hmac_sha256, updated_at) VALUES (1, 0, 'clean', NULL, %s, %s, %s)", (migration_chain_digest(migrations, 0), target_fingerprint(config), datetime.now(timezone.utc).isoformat()))
        # Commit both tables and the singleton as one PostgreSQL transaction.
        connection.commit()
    # Roll back the complete metadata transaction on any failure.
    except Exception:
        # Restore a usable connection and leave no partial control boundary.
        connection.rollback()
        # Preserve the original connector exception for the sanitized apply boundary.
        raise


# Persist the committed pre-DDL applying marker for crash-safe fail-closed state.
def _mark_applying(connection, state: SchemaState, migration: Migration) -> None:
    # Open a cursor for one guarded state transition.
    cursor = connection.cursor()
    # Update only the exact clean prefix observed under the advisory lock.
    cursor.execute("UPDATE casino_schema_migration_state SET status = 'applying', applying_version = %s, updated_at = %s WHERE state_id = 1 AND status = 'clean' AND current_version = %s RETURNING state_id", (migration.version, datetime.now(timezone.utc).isoformat(), state.current_version))
    # Require the singleton transition to return its identity.
    if _row_values(cursor.fetchone(), ("state_id",)) != (1,):
        # Roll back the contradictory transition before failing closed.
        connection.rollback()
        # Refuse concurrent or foreign state changes.
        raise MigrationError("PostgreSQL migration state changed before apply")
    # Commit the marker independently before application DDL starts.
    connection.commit()


# Roll back failed DDL and persist its exact dirty version independently.
def _mark_dirty(connection, migration: Migration) -> None:
    # Restore the connection after the failed transactional migration.
    connection.rollback()
    # Open a fresh cursor for the durable dirty marker.
    cursor = connection.cursor()
    # Preserve the interrupted version without advancing applied history.
    cursor.execute("UPDATE casino_schema_migration_state SET status = 'dirty', applying_version = %s, updated_at = %s WHERE state_id = 1 AND status = 'applying' AND applying_version = %s RETURNING state_id", (migration.version, datetime.now(timezone.utc).isoformat(), migration.version))
    # Require the exact in-flight singleton to become dirty.
    if _row_values(cursor.fetchone(), ("state_id",)) != (1,):
        # Roll back an unconfirmed secondary state transition.
        connection.rollback()
        # Refuse to claim dirty state when it was not confirmed.
        raise MigrationError("PostgreSQL migration dirty state could not be confirmed")
    # Commit only the fail-closed marker.
    connection.commit()


# Execute one complete migration plus history and clean state in one transaction.
def _apply_one(connection, state: SchemaState, migration: Migration, migrations: tuple[Migration, ...]) -> None:
    # Persist the separate crash-visible applying marker first.
    _mark_applying(connection, state, migration)
    # Open one cursor for the exact descriptor and completion records.
    cursor = connection.cursor()
    # Start the transactional PostgreSQL DDL sequence.
    try:
        # Execute each checksum-bound driver statement in reviewed order.
        for statement in migration.statements:
            # Submit exactly one JSON-array statement without interpolation or splitting.
            cursor.execute(statement)
        # Record immutable applied identity inside the same DDL transaction.
        cursor.execute("INSERT INTO casino_schema_migrations (version, name, checksum, applied_at) VALUES (%s, %s, %s, %s)", (migration.version, migration.name, migration.checksum, datetime.now(timezone.utc).isoformat()))
        # Advance only the exact in-flight singleton and return its identity.
        cursor.execute("UPDATE casino_schema_migration_state SET current_version = %s, status = 'clean', applying_version = NULL, catalog_sha256 = %s, updated_at = %s WHERE state_id = 1 AND status = 'applying' AND applying_version = %s RETURNING state_id", (migration.version, migration_chain_digest(migrations, migration.version), datetime.now(timezone.utc).isoformat(), migration.version))
        # Require exact completion before commit.
        if _row_values(cursor.fetchone(), ("state_id",)) != (1,):
            # Refuse a contradictory state transition.
            raise MigrationError("PostgreSQL migration completion state is inconsistent")
        # Commit DDL, history, and clean prefix atomically.
        connection.commit()
    # Convert every descriptor or completion failure into durable dirty state.
    except Exception as exc:
        # Start protected dirty marking so its own failure cannot be mistaken for recovery.
        try:
            # Roll back all DDL and persist the exact interrupted version.
            _mark_dirty(connection, migration)
        # Report unknown state without replacing the primary failed-migration context.
        except Exception:
            # Preserve only the fixed forward-fix result.
            raise MigrationError("PostgreSQL migration failed and dirty state could not be confirmed; an explicit forward-fix is required") from exc
        # Surface one fixed dirty-state result after confirmed rollback and marker.
        raise MigrationError("PostgreSQL migration failed and was marked dirty for an explicit forward-fix") from exc


# Verify exact server and target identity after connection but before lock or mutation.
def _verify_connected_target(connection, config: MigrationConfig, authorization_mode: str) -> None:
    # Open one cursor for fixed non-secret server facts.
    cursor = connection.cursor()
    # Read the numeric PostgreSQL server version.
    cursor.execute("SHOW server_version_num")
    # Require the official PostgreSQL 16 major version.
    if int(_row_values(cursor.fetchone(), ("server_version_num",))[0]) // 10000 != 16:
        # Refuse another major without publishing the observed value.
        raise MigrationError("PostgreSQL migration requires PostgreSQL 16")
    # Read only the server-confirmed current database and role identities.
    cursor.execute("SELECT current_database(), current_user")
    # Require the connection to match the target authorized before connector access.
    if _row_values(cursor.fetchone(), ("current_database", "current_user")) != (config.database, config.user):
        # Refuse redirected connection configuration.
        raise MigrationError("PostgreSQL migration connection target is inconsistent")
    # Apply an additional least-privilege role gate only to production bootstrap authority.
    if authorization_mode == "production":
        # Read only fixed cluster-level privilege booleans for the current migration role.
        cursor.execute("SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls FROM pg_catalog.pg_roles WHERE rolname = current_user")
        # Require one ordinary login role with no cluster-wide administrative capability.
        role_flags = _row_values(cursor.fetchone(), ("rolsuper", "rolcreaterole", "rolcreatedb", "rolreplication", "rolbypassrls"))
        # Refuse a superuser, role manager, database creator, replication role, or row-security bypass.
        if role_flags != (False, False, False, False, False):
            # Publish no observed flag or role identity.
            raise MigrationError("PostgreSQL production migration role is overprivileged")
    # End the read-only verification transaction before session advisory locking.
    connection.rollback()


# Derive one signed 64-bit advisory-lock key from the keyed target digest.
def _advisory_lock_key(config: MigrationConfig) -> int:
    # Decode the first eight digest bytes as PostgreSQL's signed bigint lock key.
    return int.from_bytes(bytes.fromhex(target_fingerprint(config)[:16]), byteorder="big", signed=True)


# Apply all pending migrations under one target-derived session advisory lock.
def apply_migrations(connection, config: MigrationConfig) -> SchemaState:
    # Validate one exact target mode before reading connection state.
    authorization_mode = require_authorized_target(config)
    # Load every immutable descriptor before lock or mutation.
    migrations, expected, _, _ = load_catalog()
    # Require explicit transactional operation from psycopg.
    if bool(connection.autocommit):
        # Stop before server access when DDL cannot be transactional.
        raise MigrationError("PostgreSQL migration connection must disable autocommit")
    # Verify official PostgreSQL 16 and exact target identities.
    _verify_connected_target(connection, config, authorization_mode)
    # Derive the non-identifying session advisory-lock key.
    lock_key = _advisory_lock_key(config)
    # Open one cursor for immediate fail-closed lock acquisition.
    lock_cursor = connection.cursor()
    # Attempt the target-specific session lock without unbounded waiting.
    lock_cursor.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
    # Require affirmative acquisition before any metadata read or write.
    if _row_values(lock_cursor.fetchone(), ("pg_try_advisory_lock",)) != (True,):
        # Close the read transaction without mutating schema state.
        connection.rollback()
        # Report only the fixed lock category.
        raise MigrationError("PostgreSQL migration advisory lock is unavailable")
    # End the acquisition statement transaction while retaining the session lock.
    connection.commit()
    # Retain a sanitized primary failure until unlock is confirmed.
    primary_error = None
    # Retain successful final state until unlock succeeds.
    final_state = None
    # Run every state transition while owning the session lock.
    try:
        # Inspect target-bound checksum state after lock acquisition.
        state = inspect_schema(connection, config, migrations)
        # End the read-only inspection transaction before any state transition.
        connection.rollback()
        # Permit production mutation only for one genuinely empty, never-initialized target.
        if authorization_mode == "production" and (state.initialized or state.application_tables_present):
            # Refuse reruns, upgrades, adoption, and foreign current-schema tables.
            raise MigrationError("PostgreSQL production bootstrap requires a new empty target")
        # Refuse interrupted state and unversioned application tables.
        if state.status in {"dirty", "applying"} or (not state.initialized and state.application_tables_present):
            # Require an explicit checksum-bound forward-fix.
            raise MigrationError("PostgreSQL migration state requires a forward-fix packet")
        # Initialize only a genuinely empty disposable target.
        if not state.initialized:
            # Create metadata atomically with target binding.
            _initialize_metadata(connection, config, migrations)
            # Re-read the exact clean version-zero state.
            state = inspect_schema(connection, config, migrations)
            # End the read-only inspection transaction.
            connection.rollback()
        # Apply each remaining descriptor in contiguous order.
        for migration in migrations[state.current_version:]:
            # Execute transactional DDL and completion state.
            _apply_one(connection, state, migration, migrations)
            # Reinspect the exact prefix before advancing.
            state = inspect_schema(connection, config, migrations)
            # End the read-only inspection transaction.
            connection.rollback()
        # Require exact final runtime compatibility.
        final_state = verify_migration_compatibility(connection, config)
        # End the final read-only verification transaction.
        connection.rollback()
        # Require the final version to equal the catalog tail.
        if final_state.current_version != expected:
            # Refuse partial success.
            raise MigrationError("PostgreSQL migration did not reach the expected version")
    # Preserve already sanitized migration results.
    except MigrationError as exc:
        # Retain the primary result until lock release.
        primary_error = exc
    # Collapse unexpected connector failures into one fixed result.
    except Exception as exc:
        # Preserve no driver, SQL, or target text.
        primary_error = MigrationError("PostgreSQL migration outcome could not be confirmed")
        # Retain the original exception only as an internal cause.
        primary_error.__cause__ = exc
    # Always attempt exact session advisory-lock release.
    try:
        # Roll back any open failed or read-only transaction before unlock.
        connection.rollback()
        # Open a fresh cursor for lock release confirmation.
        release_cursor = connection.cursor()
        # Release only this target-derived session lock.
        release_cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        # Require confirmation that this session owned the lock.
        if _row_values(release_cursor.fetchone(), ("pg_advisory_unlock",)) != (True,):
            # Refuse unconfirmed lock state.
            raise MigrationError("PostgreSQL migration advisory lock release could not be confirmed")
        # End the unlock statement transaction.
        connection.commit()
    # Combine failure categories without exposing secondary connector details.
    except Exception as exc:
        # Preserve the primary fixed result when one already exists.
        if primary_error is not None:
            # Report both fail-closed boundaries using sanitized text only.
            raise MigrationError(f"{primary_error}; advisory lock release could not be confirmed") from primary_error
        # Fail an otherwise successful handoff when unlock is unknown.
        raise MigrationError("PostgreSQL migration advisory lock release could not be confirmed") from exc
    # Re-raise the primary sanitized outcome after confirmed unlock.
    if primary_error is not None:
        # Preserve its internal cause chain.
        raise primary_error
    # Return only after exact schema and lock-release confirmation.
    return final_state
