# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Govern PostgreSQL migration immutability, hostile states, and guarded application."""

# Import in-memory output capture for secret-safe CLI assertions.
from contextlib import redirect_stdout
# Import filesystem copying for isolated hostile-catalog fixtures.
import shutil
# Import JSON for catalog mutation and CLI output validation.
import json
# Import environment access for namespace-isolation assertions.
import os
# Import temporary directories for disposable catalog fixtures.
import tempfile
# Import unit-test helpers for deterministic migration state models.
import unittest
# Import in-memory text streams for CLI output capture.
from io import StringIO
# Import portable paths for exact source and catalog inspection.
from pathlib import Path
# Import mocking for environment and connector failure seams.
from unittest import mock

# Import the PostgreSQL migration state machine under test.
from casino.core import postgres_migrations
# Import the deployment-only runner without invoking its command boundary.
from scripts import postgres_migrate

# Resolve repository-owned migration assets independently of process cwd.
ROOT = Path(__file__).resolve().parents[1]
# Resolve the canonical PostgreSQL catalog directory.
MIGRATIONS = ROOT / "migrations" / "postgres"


# Build one valid direct configuration with no ambient environment dependency.
def synthetic_config(*, database: str = "casino_test_1057", key: str = "k" * 32) -> postgres_migrations.MigrationConfig:
    # Return the exact issue-scoped disposable tuple accepted by the public guard.
    return postgres_migrations.MigrationConfig(
        # Keep tests on literal loopback.
        host="127.0.0.1",
        # Use the standard PostgreSQL port only as inert model data.
        port=5432,
        # Use a test-suffixed synthetic migration role.
        user="casino_migrate_1057",
        # Keep a distinct synthetic password out of assertions.
        password="synthetic-password",
        # Allow target-binding tests to vary only the database.
        database=database,
        # Allow target-binding tests to vary only the HMAC key.
        target_binding_key=key,
        # Supply the exact issue-owned disposable authorization marker.
        disposable_marker=postgres_migrations.DISPOSABLE_MARKER,
    )


# Build one valid release-bound production bootstrap configuration.
def production_config(*, release_sha: str = "a" * 40) -> postgres_migrations.MigrationConfig:
    # Return a loopback-only ordinary-role target with distinct production authorization.
    return postgres_migrations.MigrationConfig(
        # Keep the production database private to the application host.
        host="127.0.0.1",
        # Use the standard PostgreSQL port only as deterministic model data.
        port=5432,
        # Select the fixed least-privilege migration role planned for the host.
        user="casino_migrate",
        # Keep synthetic credentials distinct from the binding key.
        password="synthetic-production-password",
        # Select the dedicated production database identity.
        database="virtual_casino",
        # Use a synthetic high-entropy target-binding key.
        target_binding_key="q" * 32,
        # Supply the owner-approved production marker rather than the disposable marker.
        production_marker=postgres_migrations.PRODUCTION_MARKER,
        # Bind the authorization to one exact immutable release commit.
        release_sha=release_sha,
    )


# Model enough PostgreSQL cursor behavior to exercise the complete migration state machine.
class ModelCursor:
    # Bind the cursor to its transaction-aware connection model.
    def __init__(self, connection):
        # Retain only the caller-owned model.
        self.connection = connection
        # Initialize no pending scalar result.
        self.one = None
        # Initialize no pending row collection.
        self.all = []
        # Initialize no selected scalar-column identity.
        self.one_columns = tuple()
        # Initialize no selected collection-column identity.
        self.all_columns = tuple()

    # Execute one exact statement against deterministic modeled state.
    def execute(self, statement, params=None):
        # Record statement text and detached parameters for mutation/read audits.
        self.connection.executed.append((statement, tuple(params or ())))
        # Raise the configured synthetic failure before changing modeled state.
        if self.connection.fail_fragment and self.connection.fail_fragment in statement:
            # Preserve a driver-like exception containing a value that public boundaries must hide.
            raise RuntimeError("driver-secret-target")
        # Reset pending rows for this operation.
        self.one, self.all, self.one_columns, self.all_columns = None, [], tuple(), tuple()
        # Return the configured server major as a positional psycopg row.
        if statement == "SHOW server_version_num":
            # Model official PostgreSQL 16.
            self.one = ("160011",)
            # Name the SHOW result exactly as psycopg dict_row does.
            self.one_columns = ("server_version_num",)
        # Return exact server-confirmed database and role identities.
        elif statement == "SELECT current_database(), current_user":
            # Bind the connection to its synthetic authorized target.
            self.one = (self.connection.config.database, self.connection.config.user)
            # Name both selected identity columns.
            self.one_columns = ("current_database", "current_user")
        # Return fixed cluster-level privilege facts for production migration role validation.
        elif statement.startswith("SELECT rolsuper, rolcreaterole"):
            # Expose the caller-selected five-boolean privilege tuple.
            self.one = tuple(self.connection.role_flags)
            # Name every selected privilege exactly as psycopg dict_row does.
            self.one_columns = ("rolsuper", "rolcreaterole", "rolcreatedb", "rolreplication", "rolbypassrls")
        # Acquire the session advisory lock unless explicitly blocked.
        elif statement.startswith("SELECT pg_try_advisory_lock"):
            # Model immediate fail-closed acquisition semantics.
            self.one = (self.connection.lock_available,)
            # Name the PostgreSQL advisory-lock result.
            self.one_columns = ("pg_try_advisory_lock",)
        # Release the session advisory lock unless explicitly made unconfirmable.
        elif statement.startswith("SELECT pg_advisory_unlock"):
            # Model the required affirmative unlock result.
            self.one = (self.connection.unlock_confirmed,)
            # Name the PostgreSQL advisory-unlock result.
            self.one_columns = ("pg_advisory_unlock",)
        # Return current Casino table inventory in stable order.
        elif "FROM pg_catalog.pg_tables" in statement:
            # Model tuple rows returned by default psycopg cursors.
            self.all = [(name,) for name in sorted(self.connection.tables)]
            # Name the selected table column for dict-row modeling.
            self.all_columns = ("tablename",)
        # Return the singleton migration state.
        elif statement.startswith("SELECT current_version, status"):
            # Return missing state as a missing row.
            self.one = None if self.connection.state is None else tuple(self.connection.state)
            # Name the exact state SELECT columns.
            self.one_columns = ("current_version", "status", "applying_version", "catalog_sha256", "target_hmac_sha256")
        # Return immutable applied history rows.
        elif statement.startswith("SELECT version, name, checksum"):
            # Copy rows so callers cannot mutate modeled history.
            self.all = list(self.connection.history)
            # Name the exact history SELECT columns.
            self.all_columns = ("version", "name", "checksum")
        # Track every created Casino table for later inspection.
        elif statement.startswith("CREATE TABLE "):
            # Extract the fixed unquoted table identifier from reviewed DDL.
            table = statement.split()[2]
            # Add this table to the current schema inventory.
            self.connection.tables.add(table)
        # Initialize the target-bound version-zero singleton.
        elif statement.startswith("INSERT INTO casino_schema_migration_state"):
            # Preserve current version, state, prefix digest, and target binding.
            self.connection.state = [0, "clean", None, params[0], params[1]]
        # Persist one immutable applied-migration history record.
        elif statement.startswith("INSERT INTO casino_schema_migrations"):
            # Store only the version, name, and checksum projection read by inspection.
            self.connection.history.append((params[0], params[1], params[2]))
        # Persist the committed applying marker.
        elif statement.startswith("UPDATE casino_schema_migration_state SET status = 'applying'"):
            # Require the modeled state to match the guarded clean prefix.
            if self.connection.state and self.connection.state[1] == "clean" and self.connection.state[0] == params[2]:
                # Set the exact next in-flight version.
                self.connection.state[1:3] = ["applying", params[0]]
                # Return the singleton identity through RETURNING.
                self.one = (1,)
                # Name the RETURNING column.
                self.one_columns = ("state_id",)
        # Persist the independently committed dirty marker.
        elif statement.startswith("UPDATE casino_schema_migration_state SET status = 'dirty'"):
            # Require the exact in-flight version before marking dirty.
            if self.connection.state and self.connection.state[1] == "applying" and self.connection.state[2] == params[2]:
                # Preserve current version while marking the interruption.
                self.connection.state[1:3] = ["dirty", params[0]]
                # Return the singleton identity through RETURNING.
                self.one = (1,)
                # Name the RETURNING column.
                self.one_columns = ("state_id",)
        # Complete one migration and advance its exact prefix digest.
        elif statement.startswith("UPDATE casino_schema_migration_state SET current_version"):
            # Require the exact applying version before clean transition.
            if self.connection.state and self.connection.state[1] == "applying" and self.connection.state[2] == params[3]:
                # Advance version, clear applying, and replace the prefix digest.
                self.connection.state[0:4] = [params[0], "clean", None, params[1]]
                # Return the singleton identity through RETURNING.
                self.one = (1,)
                # Name the RETURNING column.
                self.one_columns = ("state_id",)

    # Fetch the pending scalar result once.
    def fetchone(self):
        # Return missing rows unchanged.
        if self.one is None:
            # Preserve ordinary fetchone missing-row behavior.
            return None
        # Return a psycopg-style mapping when the model selects dict rows.
        if self.connection.dict_rows:
            # Bind every selected name to its positional value.
            return dict(zip(self.one_columns, self.one))
        # Return the modeled positional tuple by default.
        return self.one

    # Fetch the pending row collection.
    def fetchall(self):
        # Return psycopg-style mappings when the model selects dict rows.
        if self.connection.dict_rows:
            # Bind every row to the exact selected column names.
            return [dict(zip(self.all_columns, row)) for row in self.all]
        # Return detached positional rows by default.
        return list(self.all)


# Model one psycopg connection with exact state, history, and transaction evidence.
class ModelConnection:
    # Initialize an empty or caller-selected migration state.
    def __init__(self, config, *, initialized=False, version=0, status="clean", applying=None):
        # Retain the synthetic connection target.
        self.config = config
        # Require transactional mode by default.
        self.autocommit = False
        # Return positional tuples unless a test explicitly selects dict rows.
        self.dict_rows = False
        # Seed both control tables only for initialized state.
        self.tables = set(postgres_migrations.CONTROL_TABLES if initialized else ())
        # Load the immutable catalog for exact prefix rows.
        migrations = postgres_migrations.load_catalog()[0]
        # Seed exact applied history through the requested version.
        self.history = [(item.version, item.name, item.checksum) for item in migrations[:version]]
        # Seed a target-bound singleton only when initialized.
        self.state = None if not initialized else [version, status, applying, postgres_migrations.migration_chain_digest(migrations, version), postgres_migrations.target_fingerprint(config)]
        # Record every executed statement for read/write governance.
        self.executed = []
        # Allow advisory lock acquisition by default.
        self.lock_available = True
        # Confirm advisory lock release by default.
        self.unlock_confirmed = True
        # Disable synthetic statement failure by default.
        self.fail_fragment = None
        # Model one ordinary production migration role with no cluster-wide privileges.
        self.role_flags = (False, False, False, False, False)
        # Count explicit commits.
        self.commits = 0
        # Count explicit rollbacks.
        self.rollbacks = 0
        # Record whether the deployment runner closed this modeled connector.
        self.closed = False

    # Open one cursor bound to this model.
    def cursor(self):
        # Return a fresh result holder over shared state.
        return ModelCursor(self)

    # Record one committed transaction boundary.
    def commit(self):
        # Increment deterministic transaction evidence.
        self.commits += 1

    # Record one rollback or read-only transaction closure.
    def rollback(self):
        # Increment deterministic transaction evidence.
        self.rollbacks += 1

    # Record deterministic connector cleanup for CLI ownership tests.
    def close(self):
        # Mark the model closed without altering its persisted database state.
        self.closed = True


# Exercise immutable catalog, guard, hostile-state, transaction, and CLI behavior.
class PostgreSQLMigrationTests(unittest.TestCase):
    # Require exact contiguous checksums and the closed compatibility contract.
    def test_catalog_is_contiguous_checksum_bound_and_exact_version_five(self):
        # Load every immutable migration record.
        migrations, expected, minimum, catalog_sha256 = postgres_migrations.load_catalog()
        # Require exact versions one through five.
        self.assertEqual([item.version for item in migrations], [1, 2, 3, 4, 5])
        # Require a fresh-target exact-five runtime boundary.
        self.assertEqual((expected, minimum), (5, 5))
        # Require one canonical catalog checksum.
        self.assertRegex(catalog_sha256, r"^[0-9a-f]{64}$")
        # Require the published contract to remain guarded and empty-target-only.
        self.assertEqual(postgres_migrations.schema_contract()["apply_policy"], "guarded-empty-target-only")

    # Require reviewed PostgreSQL 16 dialect and complete storage inventory.
    def test_catalog_uses_postgres_identity_jsonb_constraints_and_separate_indexes(self):
        # Join exact statement text for bounded token auditing.
        sql = "\n".join(statement for migration in postgres_migrations.load_catalog()[0] for statement in migration.statements)
        # Require PostgreSQL-native identity, money, JSON, conflict, and referential syntax.
        for token in ("GENERATED BY DEFAULT AS IDENTITY", "DECIMAL(18,2)", "JSONB", "ON CONFLICT", "FOREIGN KEY", "CREATE INDEX", "CREATE UNIQUE INDEX"):
            # Assert every required dialect boundary appears.
            self.assertIn(token, sql)
        # Require all durable provider tables in the translated chain.
        for table in ("casino_players", "casino_ledger", "casino_history", "casino_documents", "casino_game_action_receipts", "casino_game_action_claims", "casino_game_action_epoch_state", "casino_sessions"):
            # Assert the reviewed table is created.
            self.assertIn(f"CREATE TABLE {table}", sql)
        # Reject MySQL-only storage and JSON syntax byte-for-byte.
        for token in ("ENGINE=", "AUTO_INCREMENT", "UNSIGNED", "CHARACTER SET", "JSON_EXTRACT", "JSON_UNQUOTE"):
            # Assert no descriptor retains the foreign dialect token.
            self.assertNotIn(token, sql.upper())

    # Prove deployment configuration never falls back to runtime credentials.
    def test_config_uses_only_migration_namespace_and_redacts_every_representation(self):
        # Supply valid migration variables plus hostile runtime values.
        environment = {
            # Select the explicit loopback migration host.
            "CASINO_POSTGRES_MIGRATION_HOST": "127.0.0.1",
            # Select the issue-owned migration role.
            "CASINO_POSTGRES_MIGRATION_USER": "casino_migrate_1057",
            # Supply a distinct migration password.
            "CASINO_POSTGRES_MIGRATION_PASSWORD": "migration-secret",
            # Select the issue-owned disposable database.
            "CASINO_POSTGRES_MIGRATION_DATABASE": "casino_test_1057",
            # Supply a distinct high-entropy binding key.
            "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "b" * 32,
            # Supply the exact explicit disposable marker.
            "CASINO_POSTGRES_MIGRATION_DISPOSABLE": postgres_migrations.DISPOSABLE_MARKER,
            # Prove the runtime password is ignored.
            "CASINO_POSTGRES_PASSWORD": "runtime-secret",
        }
        # Isolate the process environment for deterministic namespace validation.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Load the migration-only record.
            config = postgres_migrations.MigrationConfig.from_env()
        # Require the migration secret rather than runtime fallback.
        self.assertEqual(config.password, "migration-secret")
        # Require fixed redaction for configuration and connector mappings.
        self.assertNotIn("secret", repr(config) + repr(config.kwargs()) + str(config.kwargs()))

    # Refuse missing, reused, or malformed deployment-only configuration values.
    def test_config_rejects_incomplete_short_reused_key_and_bad_port(self):
        # Start from one complete valid environment.
        base = {
            # Bind to literal loopback.
            "CASINO_POSTGRES_MIGRATION_HOST": "127.0.0.1",
            # Use an issue-owned role.
            "CASINO_POSTGRES_MIGRATION_USER": "casino_migrate_1057",
            # Use a synthetic password.
            "CASINO_POSTGRES_MIGRATION_PASSWORD": "p" * 32,
            # Use an issue-owned database.
            "CASINO_POSTGRES_MIGRATION_DATABASE": "casino_test_1057",
            # Use a distinct binding key.
            "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "k" * 32,
            # Supply the explicit marker.
            "CASINO_POSTGRES_MIGRATION_DISPOSABLE": postgres_migrations.DISPOSABLE_MARKER,
        }
        # Build hostile overrides with fixed expected diagnostics.
        cases = [({}, "incomplete"), ({"CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "short"}, "target-binding"), ({"CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "p" * 32}, "target-binding"), ({"CASINO_POSTGRES_MIGRATION_PORT": "bad"}, "port")]
        # Exercise every configuration failure independently.
        for override, expected in cases:
            # Use an empty environment only for the incomplete case.
            environment = {} if not override else {**base, **override}
            # Isolate environment values from the developer machine.
            with self.subTest(expected=expected), mock.patch.dict(os.environ, environment, clear=True):
                # Require one fixed value-free migration error.
                with self.assertRaisesRegex(postgres_migrations.MigrationError, expected):
                    # Attempt to load the rejected configuration.
                    postgres_migrations.MigrationConfig.from_env()

    # Refuse every target outside the exact marker, loopback, and issue suffix boundary.
    def test_disposable_guard_rejects_marker_host_database_user_and_secret_reuse(self):
        # Build mutations over the frozen valid record.
        cases = {
            # Remove explicit authorization.
            "marker": {"disposable_marker": "1"},
            # Redirect the target off literal loopback.
            "host": {"host": "localhost"},
            # Remove the issue suffix from the database.
            "database": {"database": "casino"},
            # Remove the issue suffix from the role.
            "user": {"user": "casino"},
            # Reuse the database password as the HMAC key.
            "secret": {"password": "k" * 32},
        }
        # Exercise each direct-construction guard independently.
        for name, updates in cases.items():
            # Copy valid dataclass fields into a mutable mapping.
            fields = dict(vars(synthetic_config()))
            # Apply only the selected hostile change.
            fields.update(updates)
            # Require the same value-free disposable diagnostic.
            with self.subTest(name=name), self.assertRaisesRegex(postgres_migrations.MigrationError, "authorized disposable"):
                # Validate the hostile target.
                postgres_migrations.require_disposable_target(postgres_migrations.MigrationConfig(**fields))

    # Prove production configuration requires one distinct marker and exact immutable release identity.
    def test_production_authorization_is_release_bound_and_mutually_exclusive(self):
        # Build the complete production migration namespace without runtime fallbacks.
        environment = {
            # Keep the target on literal IPv4 loopback.
            "CASINO_POSTGRES_MIGRATION_HOST": "127.0.0.1",
            # Select the ordinary migration owner role.
            "CASINO_POSTGRES_MIGRATION_USER": "casino_migrate",
            # Supply a distinct synthetic migration password.
            "CASINO_POSTGRES_MIGRATION_PASSWORD": "p" * 32,
            # Select the dedicated application database.
            "CASINO_POSTGRES_MIGRATION_DATABASE": "virtual_casino",
            # Supply an independent high-entropy binding key.
            "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "k" * 32,
            # Supply the production-only authorization marker.
            "CASINO_POSTGRES_MIGRATION_PRODUCTION": postgres_migrations.PRODUCTION_MARKER,
            # Bind the request to one full immutable release commit.
            "CASINO_POSTGRES_MIGRATION_RELEASE_SHA": "a" * 40,
        }
        # Load the valid environment through the public parser.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Resolve the guarded production configuration.
            config = postgres_migrations.MigrationConfig.from_env()
        # Require the finite production mode rather than a disposable fallback.
        self.assertEqual(postgres_migrations.require_authorized_target(config), "production")
        # Build hostile authorization combinations that must fail before connector access.
        cases = ({"CASINO_POSTGRES_MIGRATION_RELEASE_SHA": "short"}, {"CASINO_POSTGRES_MIGRATION_DISPOSABLE": postgres_migrations.DISPOSABLE_MARKER}, {"CASINO_POSTGRES_MIGRATION_PRODUCTION": "wrong"})
        # Exercise malformed release, dual-mode, and wrong-marker inputs independently.
        for override in cases:
            # Load each rejected environment without retaining ambient configuration.
            with self.subTest(override=tuple(override)), mock.patch.dict(os.environ, {**environment, **override}, clear=True):
                # Require one fixed configuration or authorization failure.
                with self.assertRaises(postgres_migrations.MigrationError):
                    # Parse and validate the hostile production tuple.
                    rejected = postgres_migrations.MigrationConfig.from_env()
                    # Validate exact marker and identifier semantics when parsing succeeds.
                    postgres_migrations.require_authorized_target(rejected)

    # Prove production apply is one-time, empty-target-only, and rejects elevated roles.
    def test_production_apply_requires_new_empty_target_and_least_privileged_role(self):
        # Apply the exact catalog to one genuinely empty modeled production database.
        accepted = ModelConnection(production_config())
        # Run the guarded one-time bootstrap.
        final_state = postgres_migrations.apply_migrations(accepted, accepted.config)
        # Require exact clean schema five after all immutable descriptors.
        self.assertEqual((final_state.current_version, final_state.status), (5, "clean"))
        # Require the cluster-role privilege query before metadata creation.
        self.assertTrue(any(statement.startswith("SELECT rolsuper, rolcreaterole") for statement, _params in accepted.executed))
        # Seed an already initialized target that must never be upgraded through this production path.
        initialized = ModelConnection(production_config(), initialized=True, version=5)
        # Refuse a repeat production apply even when the target is clean and compatible.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "new empty target"):
            # Attempt the prohibited second production bootstrap.
            postgres_migrations.apply_migrations(initialized, initialized.config)
        # Seed a foreign current-schema table without migration metadata.
        foreign = ModelConnection(production_config())
        # Make the database non-empty without using a Casino-owned prefix.
        foreign.tables.add("operator_table")
        # Refuse implicit adoption of any pre-existing table.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "new empty target"):
            # Attempt to bootstrap the contaminated target.
            postgres_migrations.apply_migrations(foreign, foreign.config)
        # Model a migration role carrying one forbidden cluster-wide privilege.
        elevated = ModelConnection(production_config())
        # Grant synthetic superuser capability for the fail-closed proof.
        elevated.role_flags = (True, False, False, False, False)
        # Refuse the role before any schema DDL.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "overprivileged"):
            # Attempt bootstrap with the rejected role.
            postgres_migrations.apply_migrations(elevated, elevated.config)
        # Require no table creation after the privilege gate fails.
        self.assertFalse(elevated.tables)

    # Prove uninitialized inspection and dry-run use SELECT statements only.
    def test_uninitialized_dry_run_is_read_only_and_returns_all_versions(self):
        # Create one genuinely empty modeled target.
        connection = ModelConnection(synthetic_config())
        # Inspect without metadata creation.
        state = postgres_migrations.inspect_schema(connection, connection.config)
        # Require explicit version-zero uninitialized state.
        self.assertEqual((state.initialized, state.current_version, state.status), (False, 0, "uninitialized"))
        # Request the immutable pending plan.
        pending = postgres_migrations.dry_run(connection, connection.config)
        # Require all five contiguous versions.
        self.assertEqual([item.version for item in pending], [1, 2, 3, 4, 5])
        # Require no mutating SQL in either operation.
        self.assertTrue(all(statement.startswith("SELECT") for statement, _params in connection.executed))

    # Require exact clean state and target binding for compatibility.
    def test_clean_exact_state_is_compatible(self):
        # Seed a complete checksum-bound schema-five target.
        connection = ModelConnection(synthetic_config(), initialized=True, version=5)
        # Add one application table to prove versioned state permits storage.
        connection.tables.add("casino_players")
        # Verify exact compatibility.
        state = postgres_migrations.verify_runtime_compatibility(connection)
        # Require exact clean schema five.
        self.assertEqual((state.current_version, state.status), (5, "clean"))

    # Prove runtime verification reads no migration secret, marker, configuration, or target binding key.
    def test_runtime_verifier_is_config_free_and_treats_target_hmac_as_opaque(self):
        # Seed one exact clean schema-five target using synthetic migration evidence.
        connection = ModelConnection(synthetic_config(), initialized=True, version=5)
        # Replace the persisted target digest with another canonical deployment-owned digest.
        connection.state[4] = "a" * 64
        # Remove every environment variable so no migration configuration can be loaded.
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(postgres_migrations.MigrationConfig, "from_env", side_effect=AssertionError("runtime read migration config")):
            # Verify exact runtime compatibility with connection-only authority.
            state = postgres_migrations.verify_runtime_compatibility(connection)
        # Require exact clean schema five despite opaque non-reversible target evidence.
        self.assertEqual((state.current_version, state.status), (5, "clean"))
        # Require deployment inspection to keep enforcing its keyed target binding.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "target binding"):
            # Inspect the same copied state through the migration-runner boundary.
            postgres_migrations.inspect_schema(connection, connection.config)

    # Support psycopg dict_row results across runtime and migration SELECT boundaries.
    def test_dict_row_runtime_and_apply_paths_are_supported(self):
        # Seed one exact complete target using mapping results.
        runtime = ModelConnection(synthetic_config(), initialized=True, version=5)
        # Select psycopg dict-row behavior for every cursor.
        runtime.dict_rows = True
        # Require connection-only runtime compatibility with mapping rows.
        state = postgres_migrations.verify_runtime_compatibility(runtime)
        # Require exact clean schema five.
        self.assertEqual((state.current_version, state.status), (5, "clean"))
        # Build one empty mapping-row target for the deployment runner path.
        migration = ModelConnection(synthetic_config())
        # Select psycopg dict-row behavior before server and lock queries.
        migration.dict_rows = True
        # Apply the complete chain through mapping results.
        applied = postgres_migrations.apply_migrations(migration, migration.config)
        # Require exact clean schema five and all history rows.
        self.assertEqual((applied.current_version, applied.status, len(applied.applied)), (5, "clean", 5))

    # Require the config-free runtime verifier to fail closed on incomplete, dirty, or wrong versions.
    def test_runtime_verifier_rejects_incomplete_dirty_and_wrong_schema(self):
        # Build one partial metadata boundary.
        partial = ModelConnection(synthetic_config())
        # Add only one control table.
        partial.tables.add("casino_schema_migrations")
        # Build one structurally valid dirty state at version two.
        dirty = ModelConnection(synthetic_config(), initialized=True, version=2, status="dirty", applying=3)
        # Build one clean but incomplete schema-four state.
        incomplete = ModelConnection(synthetic_config(), initialized=True, version=4)
        # Exercise every hostile runtime state through connection-only authority.
        for name, connection in (("partial", partial), ("dirty", dirty), ("incomplete", incomplete)):
            # Require a fixed fail-closed migration result.
            with self.subTest(name=name), self.assertRaises(postgres_migrations.MigrationError):
                # Verify runtime compatibility without any migration configuration.
                postgres_migrations.verify_runtime_compatibility(connection)

    # Reject partial metadata, unversioned tables, gaps, foreign hashes, and future state.
    def test_hostile_schema_states_fail_closed(self):
        # Build one partial control boundary.
        partial = ModelConnection(synthetic_config())
        # Add only one control table.
        partial.tables.add("casino_schema_migrations")
        # Require a forward-fix result.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "metadata is incomplete"):
            # Inspect the partial boundary.
            postgres_migrations.inspect_schema(partial, partial.config)
        # Build unversioned application storage.
        unversioned = ModelConnection(synthetic_config())
        # Add one application table without metadata.
        unversioned.tables.add("casino_players")
        # Inspect still reports uninitialized plus application evidence.
        state = postgres_migrations.inspect_schema(unversioned, unversioned.config)
        # Require the explicit hostile flag.
        self.assertTrue(state.application_tables_present)
        # Require dry-run to refuse implicit adoption.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "forward-fix"):
            # Attempt the prohibited pending plan.
            postgres_migrations.dry_run(unversioned, unversioned.config)
        # Build exact version two before mutating history.
        foreign = ModelConnection(synthetic_config(), initialized=True, version=2)
        # Substitute one applied checksum.
        foreign.history[1] = (2, foreign.history[1][1], "f" * 64)
        # Require foreign history rejection.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "history does not match"):
            # Inspect the substituted history.
            postgres_migrations.inspect_schema(foreign, foreign.config)
        # Build exact version two before copying target-bound metadata.
        copied = ModelConnection(synthetic_config(), initialized=True, version=2)
        # Replace the persisted target digest with a foreign valid digest.
        copied.state[4] = "a" * 64
        # Require keyed target-binding rejection.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "target binding"):
            # Inspect the copied metadata.
            postgres_migrations.inspect_schema(copied, copied.config)
        # Build exact version two before introducing a history gap.
        gapped = ModelConnection(synthetic_config(), initialized=True, version=2)
        # Change the second numeric position to version three.
        gapped.history[1] = (3, gapped.history[1][1], gapped.history[1][2])
        # Require contiguous-prefix rejection.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "not contiguous"):
            # Inspect gapped history.
            postgres_migrations.inspect_schema(gapped, gapped.config)
        # Build a future state outside the packaged tail.
        future = ModelConnection(synthetic_config(), initialized=True, version=5)
        # Advance current_version without a corresponding packaged record.
        future.state[0] = 6
        # Require incompatible-version rejection.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "version state"):
            # Inspect future state.
            postgres_migrations.inspect_schema(future, future.config)

    # Require finite clean/applying/dirty combinations only.
    def test_state_machine_rejects_unknown_or_contradictory_status(self):
        # Build one exact version-two prefix for every hostile state.
        cases = [("unknown", None), ("clean", 3), ("applying", None), ("dirty", 4), ("applying", 6)]
        # Exercise each contradictory combination.
        for status, applying in cases:
            # Seed the selected persisted state.
            connection = ModelConnection(synthetic_config(), initialized=True, version=2, status=status, applying=applying)
            # Require one fixed finite-state rejection.
            with self.subTest(status=status, applying=applying), self.assertRaisesRegex(postgres_migrations.MigrationError, "state is invalid"):
                # Inspect the hostile state.
                postgres_migrations.inspect_schema(connection, connection.config)

    # Require altered descriptor bytes and shadow JSON inventory to fail before connection use.
    def test_hostile_catalog_checksum_and_inventory_are_rejected(self):
        # Allocate one temporary catalog directory.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve the isolated catalog root.
            target = Path(directory)
            # Copy only immutable JSON assets for hostile mutation.
            for source in MIGRATIONS.glob("*.json"):
                # Preserve exact bytes initially.
                shutil.copyfile(source, target / source.name)
            # Append harmless whitespace to change one exact descriptor checksum.
            (target / "0001_initial.json").write_bytes((target / "0001_initial.json").read_bytes() + b" ")
            # Require checksum failure before any database object exists.
            with self.assertRaisesRegex(postgres_migrations.MigrationError, "checksum"):
                # Load the altered chain.
                postgres_migrations.load_catalog(target / "catalog.json")
        # Allocate a second isolated catalog directory.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve the isolated inventory root.
            target = Path(directory)
            # Copy exact canonical JSON assets.
            for source in MIGRATIONS.glob("*.json"):
                # Preserve exact bytes for inventory-only hostility.
                shutil.copyfile(source, target / source.name)
            # Add one unlisted shadow descriptor.
            (target / "9999_shadow.json").write_text("{}", encoding="utf-8")
            # Require listener-free inventory rejection.
            with self.assertRaisesRegex(postgres_migrations.MigrationError, "inventory"):
                # Load the ambiguous directory.
                postgres_migrations.load_catalog(target / "catalog.json")

    # Apply all five migrations transactionally and prove repeat-safe exact state.
    def test_apply_reaches_exact_five_under_lock_and_is_repeat_safe(self):
        # Create one empty authorized modeled target.
        connection = ModelConnection(synthetic_config())
        # Apply every pending descriptor.
        state = postgres_migrations.apply_migrations(connection, connection.config)
        # Require exact clean schema five and contiguous history.
        self.assertEqual((state.current_version, state.status, len(state.applied)), (5, "clean", 5))
        # Require all application and migration-control tables.
        self.assertTrue({"casino_schema_migrations", "casino_schema_migration_state", "casino_players", "casino_sessions"}.issubset(connection.tables))
        # Require lock acquisition and confirmed release.
        self.assertTrue(any(statement.startswith("SELECT pg_try_advisory_lock") for statement, _params in connection.executed))
        # Require a successful unlock statement.
        self.assertTrue(any(statement.startswith("SELECT pg_advisory_unlock") for statement, _params in connection.executed))
        # Count descriptor CREATE/ALTER statements before repeat apply.
        mutation_count = sum(statement.startswith(("CREATE TABLE", "ALTER TABLE")) for statement, _params in connection.executed)
        # Reapply the exact complete target.
        repeated = postgres_migrations.apply_migrations(connection, connection.config)
        # Require repeat-safe exact state.
        self.assertEqual(repeated.current_version, 5)
        # Require no descriptor mutation on repeat apply.
        self.assertEqual(sum(statement.startswith(("CREATE TABLE", "ALTER TABLE")) for statement, _params in connection.executed), mutation_count)

    # Roll back failed PostgreSQL DDL, mark dirty, and still release the lock.
    def test_apply_failure_marks_dirty_and_releases_lock_without_driver_text(self):
        # Start from exact schema one so migration two fails before a modeled schema change.
        connection = ModelConnection(synthetic_config(), initialized=True, version=1)
        # Include one versioned application table.
        connection.tables.add("casino_players")
        # Fail on the first migration-two statement.
        connection.fail_fragment = "ADD COLUMN action_scope"
        # Require one fixed dirty-state outcome.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "marked dirty") as captured:
            # Apply the pending suffix.
            postgres_migrations.apply_migrations(connection, connection.config)
        # Require no driver or target text in the public outcome.
        self.assertNotIn("driver-secret", str(captured.exception))
        # Require exact interrupted version two without history advance.
        self.assertEqual((connection.state[0], connection.state[1], connection.state[2], len(connection.history)), (1, "dirty", 2, 1))
        # Require lock release even after failure.
        self.assertTrue(any(statement.startswith("SELECT pg_advisory_unlock") for statement, _params in connection.executed))

    # Refuse autocommit, unavailable locks, and unconfirmed unlocks.
    def test_apply_fails_closed_on_transaction_and_lock_boundaries(self):
        # Build one empty autocommit connection.
        autocommit = ModelConnection(synthetic_config())
        # Enable prohibited auto-commit mode.
        autocommit.autocommit = True
        # Require failure before any server statement.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "disable autocommit"):
            # Attempt the prohibited apply.
            postgres_migrations.apply_migrations(autocommit, autocommit.config)
        # Require zero connector statements.
        self.assertEqual(autocommit.executed, [])
        # Build one target whose lock is unavailable.
        unavailable = ModelConnection(synthetic_config())
        # Reject advisory-lock acquisition.
        unavailable.lock_available = False
        # Require fixed lock failure without metadata creation.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "lock is unavailable"):
            # Attempt apply without the lock.
            postgres_migrations.apply_migrations(unavailable, unavailable.config)
        # Require no schema table creation.
        self.assertFalse(unavailable.tables)
        # Build one target whose unlock cannot be confirmed.
        unconfirmed = ModelConnection(synthetic_config(), initialized=True, version=5)
        # Reject the unlock confirmation.
        unconfirmed.unlock_confirmed = False
        # Require the successful state not to escape an unknown lock boundary.
        with self.assertRaisesRegex(postgres_migrations.MigrationError, "release could not be confirmed"):
            # Attempt repeat-safe verification and unlock.
            postgres_migrations.apply_migrations(unconfirmed, unconfirmed.config)

    # Bind target HMAC to endpoint/database and external key without reversible output.
    def test_target_fingerprint_is_keyed_and_target_specific(self):
        # Compute the baseline non-reversible target identity.
        first = postgres_migrations.target_fingerprint(synthetic_config())
        # Change only the database.
        second = postgres_migrations.target_fingerprint(synthetic_config(database="casino_other_1057"))
        # Change only the HMAC key.
        third = postgres_migrations.target_fingerprint(synthetic_config(key="z" * 32))
        # Require three canonical distinct digests.
        self.assertEqual(len({first, second, third}), 3)
        # Require no reversible target text.
        self.assertNotIn("casino", first + second + third)

    # Prove runner configuration failures happen before connector import and remain sanitized.
    def test_runner_fails_before_connector_for_missing_config(self):
        # Capture machine output from one empty environment.
        output = StringIO()
        # Remove every ambient configuration value.
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(postgres_migrate, "_connect") as connector, redirect_stdout(output):
            # Run the explicit read-only status command.
            result = postgres_migrate.main(["status"])
        # Require the stable policy status.
        self.assertEqual(result, 2)
        # Require no connector import or access.
        connector.assert_not_called()
        # Require only a fixed incomplete-configuration diagnostic.
        self.assertIn("configuration is incomplete", output.getvalue())

    # Collapse unexpected connector content into one fixed secret-safe CLI outcome.
    def test_runner_hides_unexpected_connector_failure(self):
        # Build one complete valid runner environment.
        environment = {
            # Bind literal loopback.
            "CASINO_POSTGRES_MIGRATION_HOST": "127.0.0.1",
            # Select the issue-owned role.
            "CASINO_POSTGRES_MIGRATION_USER": "casino_migrate_1057",
            # Supply a synthetic password.
            "CASINO_POSTGRES_MIGRATION_PASSWORD": "secret-password",
            # Select the issue-owned database.
            "CASINO_POSTGRES_MIGRATION_DATABASE": "casino_test_1057",
            # Supply a distinct HMAC key.
            "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "b" * 32,
            # Supply the explicit marker.
            "CASINO_POSTGRES_MIGRATION_DISPOSABLE": postgres_migrations.DISPOSABLE_MARKER,
        }
        # Capture machine output while the connector raises target-bearing content.
        output = StringIO()
        # Isolate environment and inject one unexpected connector exception.
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(postgres_migrate, "_connect", side_effect=RuntimeError("secret-password remote-target")), redirect_stdout(output):
            # Run the explicit status command.
            result = postgres_migrate.main(["status"])
        # Require the distinct unexpected-failure status.
        self.assertEqual(result, 3)
        # Require the fixed safe result.
        self.assertIn("command failed safely", output.getvalue())
        # Require neither secret nor connector target text.
        self.assertNotIn("secret-password", output.getvalue())
        # Require neither secret nor connector target text.
        self.assertNotIn("remote-target", output.getvalue())

    # Prove the production CLI binds bootstrap authority to the exact verified release manifest.
    def test_runner_requires_matching_production_release_manifest_before_connect(self):
        # Build one complete production-only migration environment.
        environment = {
            # Keep the production database on literal loopback.
            "CASINO_POSTGRES_MIGRATION_HOST": "127.0.0.1",
            # Select the ordinary migration role.
            "CASINO_POSTGRES_MIGRATION_USER": "casino_migrate",
            # Supply a synthetic migration password.
            "CASINO_POSTGRES_MIGRATION_PASSWORD": "p" * 32,
            # Select the dedicated database.
            "CASINO_POSTGRES_MIGRATION_DATABASE": "virtual_casino",
            # Supply an independent target-binding key.
            "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": "k" * 32,
            # Supply the owner-approved production marker.
            "CASINO_POSTGRES_MIGRATION_PRODUCTION": postgres_migrations.PRODUCTION_MARKER,
            # Bind the environment to the accepted candidate commit.
            "CASINO_POSTGRES_MIGRATION_RELEASE_SHA": "a" * 40,
        }
        # Create two minimal manifest fixtures with matching and mismatched source identity.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve the matching manifest path.
            matching = Path(directory) / "matching.json"
            # Persist only the source shape consumed by the guarded runner.
            matching.write_text(json.dumps({"source": {"commit_sha": "a" * 40}}), encoding="utf-8")
            # Resolve a distinct but structurally valid manifest path.
            mismatched = Path(directory) / "mismatched.json"
            # Bind the hostile fixture to another exact commit.
            mismatched.write_text(json.dumps({"source": {"commit_sha": "b" * 40}}), encoding="utf-8")
            # Capture the pre-connect mismatch result.
            rejected_output = StringIO()
            # Refuse a different release without calling the connector seam.
            with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(postgres_migrate, "_connect") as rejected_connector, redirect_stdout(rejected_output):
                # Run the guarded apply command with the mismatched manifest.
                rejected = postgres_migrate.main(["apply", "--release-manifest", str(mismatched)])
            # Require the policy failure status and zero connector access.
            self.assertEqual(rejected, 2)
            # Prove release mismatch is the only published category.
            self.assertIn("release identity does not match", rejected_output.getvalue())
            # Require the connector to remain unopened.
            rejected_connector.assert_not_called()
            # Build the exact modeled target expected by the accepted environment.
            connection = ModelConnection(production_config())
            # Capture sanitized success output from one valid production bootstrap.
            accepted_output = StringIO()
            # Inject the model only after release identity is proven.
            with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(postgres_migrate, "_connect", return_value=connection), redirect_stdout(accepted_output):
                # Apply the exact catalog under the matching immutable manifest.
                accepted = postgres_migrate.main(["apply", "--release-manifest", str(matching)])
            # Require successful one-time application.
            self.assertEqual(accepted, 0)
            # Require exact schema-five evidence without target data.
            self.assertEqual(json.loads(accepted_output.getvalue())["current_version"], 5)

    # Bind direct script execution to the selected release rather than ambient modules.
    def test_runner_binds_to_repository_release_root(self):
        # Require the runner's canonical root to equal this checked-out repository.
        self.assertEqual(postgres_migrate.SCRIPT_ROOT, ROOT)


# Execute the focused suite only when invoked directly.
if __name__ == "__main__":
    # Use unittest's standard fail-closed runner.
    unittest.main()
