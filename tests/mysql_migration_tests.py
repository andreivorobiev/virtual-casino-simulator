# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused repository and disposable-MySQL evidence for TEST-048."""

# Import deep-copy JSON handling for proof tamper cases.
import json
# Import SHA-256 for immutable predecessor migration bytes.
import hashlib
# Import in-memory streams for secret-safe CLI output assertions.
import io
# Import output redirection for isolated command-line failure tests.
from contextlib import redirect_stderr, redirect_stdout
# Import source inspection for the runtime DDL-free invariant.
import inspect
# Import environment copying for isolated direct-script execution.
import os
# Import a listener-free child process for extracted-release import proof.
import subprocess
# Import the active interpreter path for exact child execution.
import sys
# Import temporary files for synthetic proof records outside the repository.
import tempfile
# Import UTC time values for deterministic proof windows.
from datetime import datetime, timezone
# Import portable proof paths.
from pathlib import Path
# Import unittest assertions and patching support.
import unittest
# Import environment and function replacement for isolated failure injection.
from unittest import mock

# Import game-action bounds and the complete migration policy under test.
from casino.core import game_action, mysql_migrations
# Import the runtime provider whose readiness check must remain DDL-free.
from casino.core import storage
# Import the release inventory verifier that must package every migration.
from scripts import package_app


# Build one deployment-only synthetic configuration without ambient credentials.
def synthetic_config() -> mysql_migrations.MigrationConfig:
    # Return values used only by in-process tests and never by a connector.
    return mysql_migrations.MigrationConfig("127.0.0.1", 3306, "migration_test", "migration-password", "migration_test", "binding-key-material-for-tests-only-0001")


# Build one accepted synthetic proof for an exact pre-state.
def synthetic_proof(config, state, state_sha256, migrations, expected):
    # Preserve one deterministic quiesce timestamp.
    quiesced_at = "2026-07-16T18:00:00+00:00"
    # Preserve the complete immutable plan identity.
    chain = mysql_migrations.migration_chain_digest(migrations)
    # Assemble every proof section before HMAC signing.
    proof = {
        # Identify the accepted proof contract.
        "schema": mysql_migrations.BACKUP_PROOF_SCHEMA,
        # Bind target identity through deployment-keyed HMAC only.
        "target_hmac_sha256": mysql_migrations.target_fingerprint(config),
        # Bind the exact pre-migration version, status, and structural digest.
        "pre_migration": {"version": state.current_version, "status": state.status, "state_sha256": state_sha256},
        # Bind the intended complete migration plan.
        "plan": {"from_version": state.current_version, "to_version": expected, "migration_chain_sha256": chain},
        # Bind a still-active source quiesce boundary.
        "quiesce": {"active": True, "quiesced_at": quiesced_at},
        # Bind a completed checksum-addressed backup artifact.
        "backup": {"completed": True, "artifact_sha256": "a" * 64, "completed_at": "2026-07-16T18:10:00+00:00"},
        # Bind clean-target restore evidence to the exact artifact and pre-state.
        "restore": {"verified": True, "backup_artifact_sha256": "a" * 64, "restored_state_sha256": state_sha256, "verified_at": "2026-07-16T18:20:00+00:00", "expires_at": "2026-07-16T20:20:00+00:00"},
    }
    # Compute the exact target, state, plan, and timestamp-bound quiesce HMAC.
    proof["quiesce"]["boundary_hmac_sha256"] = mysql_migrations.quiesce_boundary_hmac(config, state, state_sha256, chain, expected, quiesced_at)
    # Sign every complete proof field except this self-referential HMAC.
    proof["proof_hmac_sha256"] = mysql_migrations.proof_hmac(proof, config)
    # Return the fully signed synthetic evidence.
    return proof


# Provide SELECT-only schema metadata for status, check, and dry-run tests.
class ReadOnlyCursor:
    # Initialize the cursor with one clean exact-compatible state.
    def __init__(self, connection):
        # Keep the parent connection for statement evidence.
        self.connection = connection
        # Store the next scalar row result.
        self.one = None
        # Store the next row collection.
        self.many = []

    # Execute one recognized read-only metadata query.
    def execute(self, statement, parameters=None):
        # Record the exact statement and optional parameters.
        self.connection.statements.append((statement, parameters))
        # Return every expected application and control table.
        if "INFORMATION_SCHEMA.TABLES" in statement and statement.startswith("SELECT TABLE_NAME FROM"):
            # Supply no tables for pending bootstrap or exact current tables for recheck.
            self.many = [] if self.connection.pending else [(name,) for name in sorted(mysql_migrations.CONTROL_TABLES | {"casino_players"})]
        # Return the singleton clean migration state.
        elif statement.startswith("SELECT current_version"):
            # Bind the complete catalog prefix.
            self.one = (self.connection.expected, "clean", None, mysql_migrations.migration_chain_digest(self.connection.migrations))
        # Return exact applied migration rows.
        elif statement.startswith("SELECT version"):
            # Mirror every immutable catalog row.
            self.many = [(item.version, item.name, item.checksum) for item in self.connection.migrations]
        # Return empty but valid structural rows for deterministic digest testing.
        elif statement.startswith("SELECT"):
            # Supply no additional metadata rows in this focused fake.
            self.many = []
        # Refuse any mutation in this SELECT-only fake.
        else:
            # Fail the test immediately on a non-read statement.
            raise AssertionError("non-SELECT statement reached read-only migration inspection")

    # Return the prepared scalar row.
    def fetchone(self):
        # Return and retain the deterministic scalar.
        return self.one

    # Return the prepared row collection.
    def fetchall(self):
        # Return a fresh list to model a consumed connector result.
        return list(self.many)


# Provide one connection that records every status/check/dry-run statement.
class ReadOnlyConnection:
    # Load the exact catalog needed by cursor results.
    def __init__(self, pending=False):
        # Retain immutable migration rows.
        self.migrations, self.expected, _, _ = mysql_migrations.load_catalog()
        # Collect executed statements for mutation checks.
        self.statements = []
        # Select an empty uninitialized target for pending dry-run evidence.
        self.pending = pending

    # Return a fresh cursor sharing the evidence collection.
    def cursor(self):
        # Construct one read-only cursor.
        return ReadOnlyCursor(self)


# Provide an application-DDL failure or lock-release failure for apply semantics.
class FailureCursor:
    # Initialize a cursor over the failure-injecting connection.
    def __init__(self, connection):
        # Retain the parent state.
        self.connection = connection
        # Store the next scalar row.
        self.one = None

    # Execute lock or migration statements under controlled failure.
    def execute(self, statement, parameters=None):
        # Record exact statements for later assertions.
        self.connection.statements.append((statement, parameters))
        # Grant the named lock deterministically.
        if statement.startswith("SELECT GET_LOCK"):
            # Return successful acquisition.
            self.one = (1,)
        # Model release confirmation or failure.
        elif statement.startswith("SELECT RELEASE_LOCK"):
            # Return the configured release result.
            self.one = (self.connection.release_result,)
        # Inject connection loss on the first application migration statement.
        elif self.connection.fail_application_statement:
            # Model unknown server state after DDL dispatch.
            raise ConnectionError("synthetic connection loss")

    # Return the prepared scalar result.
    def fetchone(self):
        # Return the deterministic lock result.
        return self.one


# Provide minimal connector state needed by apply failure tests.
class FailureConnection:
    # Initialize requested application and release failures.
    def __init__(self, fail_application_statement=False, release_result=1):
        # Start with connector-default autocommit enabled so apply must disable it.
        self.autocommit = True
        # Retain whether an application statement loses the connection.
        self.fail_application_statement = fail_application_statement
        # Retain advisory release confirmation result.
        self.release_result = release_result
        # Collect executed lock and application statements.
        self.statements = []

    # Return one failure-injecting cursor.
    def cursor(self):
        # Construct the cursor over shared state.
        return FailureCursor(self)


# Build one exact clean state at a selected immutable migration prefix.
def clean_schema_state(migrations, version, *, initialized=True):
    # Preserve only the exact contiguous applied prefix.
    applied = tuple((item.version, item.name, item.checksum) for item in migrations[:version])
    # Return the migration state consumed by public apply seams.
    return mysql_migrations.SchemaState(initialized, version, "clean", None, mysql_migrations.migration_chain_digest(migrations, version), applied, version > 0)


# Exercise immutable files, proof integrity, and failure semantics without a database service.
class MySQLMigrationTests(unittest.TestCase):
    # Prove the catalog is contiguous, checksum-bound, and version-distinct from app data schema.
    def test_catalog_contract_is_exact(self):
        # Load the verified immutable migration catalog.
        migrations, expected, minimum, catalog_sha256 = mysql_migrations.load_catalog()
        # Require the four explicit sequential migrations and bridge runtime window.
        self.assertEqual([item.version for item in migrations], [1, 2, 3, 4])
        # Require the separately versioned runtime window.
        self.assertEqual((minimum, expected), (2, 4))
        # Require the public contract to bind the closed apply policy.
        self.assertEqual(mysql_migrations.schema_contract()["apply_policy"], "held")
        # Require canonical SHA-256 identities.
        self.assertRegex(catalog_sha256, r"^[0-9a-f]{64}$")
        # Require every listed migration to retain a distinct checksum.
        self.assertEqual(len({item.checksum for item in migrations}), 4)
        # Pin the two immutable predecessor files byte-for-byte.
        self.assertEqual(
            [item.checksum for item in migrations[:2]],
            [
                "f54c288ef95f2df274f6873936969c0d9207ff6f4e1329fe43c3f79cd91e0121",
                "c3bf013483a00bddd13cf7a9b3666ea029a0f447e7a04f6dbfa7f9074103c828",
            ],
        )
        # Pin both the unchanged schema-two prefix and the deterministic schema-three chain.
        self.assertEqual(mysql_migrations.migration_chain_digest(migrations, 2), "72fa8f8918022d5bcd29ba286bd96ab6f319ea0ea6aee5e376e1ff71c2eeedd8")
        # Pin the unchanged schema-three prefix containing exact legacy receipt bytes.
        self.assertEqual(mysql_migrations.migration_chain_digest(migrations, 3), "083682e266576aa571e20f2baf6746b0ee28c8f81906c17dc96f05bed6a51a7b")
        # Require one reviewed complete chain identity for the schema-four catalog tail.
        self.assertEqual(mysql_migrations.migration_chain_digest(migrations), "0fa4dcd42d590bc64b10323fd2362129776d5e0b4dcde8c6262070e615a7060b")

    # Prove catalog loading rejects absent or alternate apply policy.
    def test_catalog_apply_policy_is_exact_and_closed(self):
        # Parse the canonical catalog fixture once.
        canonical = json.loads(mysql_migrations.CATALOG_PATH.read_text(encoding="utf-8"))
        # Exercise a missing policy and an unreviewed enabling value.
        for policy in (None, "automatic"):
            # Allocate an isolated catalog directory.
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as temporary:
                # Resolve the synthetic migration root.
                migration_root = Path(temporary)
                # Copy every immutable migration byte-for-byte.
                for row in canonical["migrations"]:
                    # Preserve the exact checksum-selected file.
                    (migration_root / row["file"]).write_bytes((mysql_migrations.MIGRATION_ROOT / row["file"]).read_bytes())
                # Copy the catalog object before one policy mutation.
                altered = dict(canonical)
                # Remove or replace the policy as selected.
                if policy is None:
                    # Model an unbound legacy catalog.
                    altered.pop("apply_policy")
                else:
                    # Model a migration-enabling catalog.
                    altered["apply_policy"] = policy
                # Persist the synthetic catalog.
                catalog_path = migration_root / "catalog.json"
                # Write deterministic JSON bytes.
                catalog_path.write_text(json.dumps(altered), encoding="utf-8")
                # Require refusal before any database seam is available.
                with self.assertRaisesRegex(mysql_migrations.MigrationError, "apply policy"):
                    # Load the hostile catalog.
                    mysql_migrations.load_catalog(catalog_path)

    # Prove schema three adds one bounded exact-scope receipt-capacity table and no journal.
    def test_schema_three_receipt_boundary_is_exact_and_bounded(self):
        # Load the checksum-verified schema-three migration through the production parser.
        migrations, expected, _, _ = mysql_migrations.load_catalog()
        # Select only the new receipt-capacity migration tail.
        migration = migrations[2]
        # Require the exact stable migration identity.
        self.assertEqual((expected, migration.version, migration.name), (4, 3, "game-action-receipts"))
        # Require exactly one additive table and no stored enforcement object.
        self.assertEqual(len(migration.statements), 1)
        # Read the complete additive table statement once.
        create_table = migration.statements[0]
        # Require one and only one new application table.
        self.assertEqual(create_table.upper().count("CREATE TABLE "), 1)
        # Require the receipt-capacity table to use the transactional InnoDB engine.
        self.assertEqual(create_table.count("ENGINE=InnoDB"), 1)
        # Pin the exact binary-collated action-scope primary key.
        self.assertIn("PRIMARY KEY (game_id, player_id, action_key)", create_table)
        # Require every identity field to retain the contract's 191-character bound.
        for field in ("game_id", "player_id", "action_key"):
            # Require exact binary UTF-8 comparison without normalization.
            self.assertIn(f"{field} VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL", create_table)
        # Require lowercase exact-length semantic and receipt digests.
        self.assertIn("request_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL", create_table)
        # Preserve one independent checksum for exact canonical receipt bytes.
        self.assertIn("receipt_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL", create_table)
        # Require both lowercase hexadecimal constraints.
        self.assertEqual(create_table.count("REGEXP '^[0-9a-f]{64}$'"), 2)
        # Require separate canonical resource and complete receipt representations.
        self.assertIn("resources_json TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL", create_table)
        # Require enough bounded storage for the complete paid or zero-cost receipt graph.
        self.assertIn("receipt_json MEDIUMTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL", create_table)
        # Require exact object-shaped JSON and explicit byte ceilings.
        self.assertIn("OCTET_LENGTH(resources_json) BETWEEN 2 AND 16384", create_table)
        # Require an eight-mebibyte maximum for one complete canonical receipt.
        self.assertIn("OCTET_LENGTH(receipt_json) BETWEEN 2 AND 8388608", create_table)
        # Prove the resource bound can encode every declared identity at maximum contract width.
        self.assertGreaterEqual(16384, (game_action.MAX_WALLET_RESOURCES + game_action.MAX_STATE_RESOURCES) * (game_action.MAX_IDENTITY_LENGTH + 8))
        # Prove the receipt bound covers every independently bounded canonical state/outcome tree.
        receipt_tree_budget = (3 * game_action.MAX_STATE_RESOURCES + 1) * game_action.MAX_CANONICAL_BYTES
        # Require headroom for complete before/plan/after state plus identity and movement structure.
        self.assertGreater(8388608, receipt_tree_budget)
        # Reject any trigger, routine, saga, compensation, or journal object in this capacity slice.
        self.assertTrue(all(term not in " ".join(migration.statements).lower() for term in ("trigger", "procedure", "function", "journal", "saga", "compensation")))

    # Prove schema four adds immutable claims and binds byte-preserved receipts exactly.
    def test_schema_four_claim_boundary_and_receipt_binding_are_exact(self):
        # Load the checksum-verified catalog without touching a database.
        migrations, expected, minimum, _catalog_sha256 = mysql_migrations.load_catalog()
        # Select only the schema-four lifecycle migration.
        migration = migrations[3]
        # Require exact catalog identity and unchanged compatibility floor.
        self.assertEqual((minimum, expected, migration.version, migration.name), (2, 4, 4, "game-action-claims"))
        # Require the reviewed twelve-statement epoch/additive/backfill/binding sequence.
        self.assertEqual(12, len(migration.statements))
        # Join exact statements only for bounded forbidden-object proof.
        joined = "\n".join(migration.statements)
        # Require one exact singleton epoch and readiness table first.
        self.assertIn("CREATE TABLE casino_game_action_epoch_state", migration.statements[0])
        # Bind the singleton, signed-range epoch, and finite readiness phases.
        self.assertTrue(all(fragment in migration.statements[0] for fragment in ("CHECK (state_id = 1)", "current_epoch BETWEEN 1 AND 9223372036854775807", "phase IN ('ready', 'resetting')")))
        # Seed only the reviewed epoch-one ready singleton.
        self.assertEqual("INSERT INTO casino_game_action_epoch_state (state_id, current_epoch, phase) VALUES (1, 1, 'ready')", migration.statements[1])
        # Backfill every legacy receipt into epoch one before replacing its primary key.
        self.assertIn("ADD COLUMN reset_epoch BIGINT UNSIGNED NOT NULL DEFAULT 1", migration.statements[2])
        # Remove the epoch default before runtime can omit namespace ownership.
        self.assertEqual("ALTER TABLE casino_game_action_receipts ALTER COLUMN reset_epoch DROP DEFAULT", migration.statements[3])
        # Require the epoch-prefixed receipt primary key.
        self.assertIn("PRIMARY KEY (reset_epoch, game_id, player_id, action_key)", migration.statements[4])
        # Require one immutable claims table with the same epoch-prefixed scope key.
        self.assertIn("CREATE TABLE casino_game_action_claims", migration.statements[5])
        # Require exact reset-epoch action-scope ownership.
        self.assertIn("PRIMARY KEY (reset_epoch, game_id, player_id, action_key)", migration.statements[5])
        # Require the only two finite dispositions.
        self.assertIn("disposition IN ('execute', 'uncommitted')", migration.statements[5])
        # Require the composite semantic key used by the receipt foreign key.
        self.assertIn("UNIQUE KEY uq_game_action_claim_semantics (reset_epoch, game_id, player_id, action_key, disposition, request_fingerprint)", migration.statements[5])
        # Require legacy receipt backfill to copy identity, fingerprint, and resources without touching receipt bytes.
        self.assertEqual("INSERT INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, 'execute' FROM casino_game_action_receipts", migration.statements[6])
        # Require the temporary execute default only for backfill-compatible column creation.
        self.assertIn("claim_disposition", migration.statements[7])
        # Remove the default before runtime can insert implicit ownership.
        self.assertEqual("ALTER TABLE casino_game_action_receipts ALTER COLUMN claim_disposition DROP DEFAULT", migration.statements[8])
        # Require every receipt to remain execute-only.
        self.assertIn("CHECK (claim_disposition = 'execute')", migration.statements[9])
        # Require one exact child composite index.
        self.assertIn("(reset_epoch, game_id, player_id, action_key, claim_disposition, request_fingerprint)", migration.statements[10])
        # Require a no-cascade composite foreign key to the immutable winner.
        self.assertIn("REFERENCES casino_game_action_claims (reset_epoch, game_id, player_id, action_key, disposition, request_fingerprint) ON UPDATE RESTRICT ON DELETE RESTRICT", migration.statements[11])
        # Reject mutation helpers and stored execution objects from the bridge.
        self.assertTrue(all(term not in joined.lower() for term in ("trigger", "procedure", "function", "enum", "on duplicate key update", "delete from", "update casino_game_action")))
        # Preserve exact immutable schema-three descriptor bytes.
        self.assertEqual("7fcb2a4997796f170c914480b1a10ebc695c4751ed66679d64774373242c0e7b", hashlib.sha256((mysql_migrations.MIGRATION_ROOT / "0003_game_action_receipts.json").read_bytes()).hexdigest())

    # Prove held application refuses before connection state, lock, DDL, or metadata mutation.
    def test_public_apply_is_held_before_connection_access(self):
        # Allocate one hostile connection whose attributes and methods must stay untouched.
        connection = mock.Mock()
        # Require the fixed catalog-owned hold result.
        with self.assertRaisesRegex(mysql_migrations.MigrationError, "apply policy is held"):
            # Attempt application with otherwise complete synthetic inputs.
            mysql_migrations.apply_migrations(connection, synthetic_config(), Path("synthetic-proof"))
        # Require no cursor, autocommit assignment, lock, DDL, or state write.
        self.assertEqual(connection.mock_calls, [])

    # Prove release packaging binds and requires the exact schema-four inventory.
    def test_package_inventory_requires_schema_four(self):
        # Calculate release schema provenance from the selected source tree.
        inventory = package_app.mysql_schema_inventory(package_app.ROOT)
        # Require the schema-two-through-four bridge runtime window.
        self.assertEqual((inventory["minimum_version"], inventory["expected_version"]), (2, 4))
        # Require package provenance to bind the held application policy.
        self.assertEqual(inventory["apply_policy"], "held")
        # Require the same deterministic chain as the migration runtime.
        self.assertEqual(inventory["migration_chain_sha256"], "0fa4dcd42d590bc64b10323fd2362129776d5e0b4dcde8c6262070e615a7060b")
        # Require every immutable migration path in the archive's mandatory allowlist.
        self.assertTrue(
            {
                "migrations/mysql/0001_initial.json",
                "migrations/mysql/0002_action_identity.json",
                "migrations/mysql/0003_game_action_receipts.json",
                "migrations/mysql/0004_game_action_claims.json",
                "migrations/mysql/catalog.json",
            }.issubset(package_app.REQUIRED_FILES)
        )
        # Read the tracked source inventory and add the new checkpoint file before commit.
        repository_paths = [*package_app.tracked_paths(package_app.ROOT), "migrations/mysql/0004_game_action_claims.json"]
        # Select the exact package inventory through the production allowlist.
        selected = package_app.select_release_files(package_app.ROOT, repository_paths)
        # Require the schema-four descriptor to be physically packaged.
        self.assertIn("migrations/mysql/0004_game_action_claims.json", selected)
        # Remove only the new migration from an otherwise complete source inventory.
        missing_four = [path for path in repository_paths if path != "migrations/mysql/0004_game_action_claims.json"]
        # Require package selection to fail before creating an incomplete archive.
        with self.assertRaisesRegex(ValueError, "0004_game_action_claims"):
            # Attempt selection without the catalog-required migration.
            package_app.select_release_files(package_app.ROOT, missing_four)

    # Prove migration configuration never falls back to runtime credentials or weak/reused keys.
    def test_migration_configuration_is_isolated(self):
        # Supply only runtime variables and clear migration variables.
        with mock.patch.dict("os.environ", {"CASINO_MYSQL_HOST": "runtime", "CASINO_MYSQL_USER": "runtime"}, clear=True):
            # Require deployment configuration to fail rather than fall back.
            with self.assertRaises(mysql_migrations.MigrationError):
                # Load migration configuration under runtime-only input.
                mysql_migrations.MigrationConfig.from_env()
        # Build the complete deployment-only environment once.
        environment = {"CASINO_MYSQL_MIGRATION_HOST": "127.0.0.1", "CASINO_MYSQL_MIGRATION_USER": "migration", "CASINO_MYSQL_MIGRATION_PASSWORD": "separate-password", "CASINO_MYSQL_MIGRATION_DATABASE": "synthetic", "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY": "short"}
        # Reject a short dictionary-guessable target-binding key.
        with mock.patch.dict("os.environ", environment, clear=True), self.assertRaises(mysql_migrations.MigrationError):
            # Parse the weak configuration.
            mysql_migrations.MigrationConfig.from_env()
        # Reuse a strong secret deliberately to prove key separation.
        environment["CASINO_MYSQL_MIGRATION_PASSWORD"] = "x" * 32
        # Set the binding key equal to the migration password.
        environment["CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY"] = "x" * 32
        # Reject authentication-secret reuse.
        with mock.patch.dict("os.environ", environment, clear=True), self.assertRaises(mysql_migrations.MigrationError):
                # Parse the reused-secret configuration.
                mysql_migrations.MigrationConfig.from_env()

    # Prove configuration, connector options, exceptions, and CLI streams are intrinsically redacted.
    def test_configuration_and_cli_output_are_redacted(self):
        # Create target and credential sentinels long enough for the binding-key policy.
        config = mysql_migrations.MigrationConfig("private-host-sentinel", 3306, "private-user-sentinel", "private-password-sentinel", "private-database-sentinel", "private-binding-key-sentinel-material-0001")
        # Join every sensitive value for repeated absence checks.
        sentinels = (config.host, config.user, config.password, config.database, config.target_binding_key)
        # Format both the config and its connector mapping.
        rendered = repr(config) + str(config) + repr(config.kwargs()) + str(config.kwargs())
        # Require no target or credential value in accidental formatting.
        self.assertTrue(all(value not in rendered for value in sentinels))
        # Build a complete deployment environment with distinct secret values.
        environment = {"CASINO_MYSQL_MIGRATION_HOST": config.host, "CASINO_MYSQL_MIGRATION_USER": config.user, "CASINO_MYSQL_MIGRATION_PASSWORD": config.password, "CASINO_MYSQL_MIGRATION_DATABASE": config.database, "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY": config.target_binding_key}
        # Allocate isolated stdout and stderr streams.
        stdout = io.StringIO()
        # Allocate a separate error stream even though the CLI writes fixed JSON to stdout.
        stderr = io.StringIO()
        # Patch command input, environment, and a hostile driver exception.
        with mock.patch.dict("os.environ", environment, clear=True), mock.patch("sys.argv", ["mysql_migrate.py", "status"]), mock.patch("scripts.mysql_migrate._connect", side_effect=RuntimeError("private-driver-sentinel SELECT secret_sql")), redirect_stdout(stdout), redirect_stderr(stderr):
            # Import the CLI lazily so its main function can be invoked directly.
            from scripts import mysql_migrate
            # Require the fixed unexpected-failure status.
            self.assertEqual(mysql_migrate.main(), 3)
        # Combine both streams for one absence assertion.
        output = stdout.getvalue() + stderr.getvalue()
        # Require target, credentials, driver message, and SQL to remain absent.
        self.assertTrue(all(value not in output for value in sentinels))
        # Require hostile driver and SQL sentinels to remain absent.
        self.assertNotIn("private-driver-sentinel", output)
        # Require no hostile SQL fragment in output.
        self.assertNotIn("secret_sql", output)

    # Prove the deployment bridge checker requires exact schema two and no migration identity.
    def test_bridge_cli_checks_exact_schema_two_with_runtime_identity_only(self):
        # Import the deployment CLI after repository configuration is ready.
        from scripts import mysql_migrate
        # Load immutable prefixes for exact sanitized state fixtures.
        migrations, _, _, _ = mysql_migrations.load_catalog()
        # Exercise the allowed bridge state and the rejected schema-three state.
        for version, expected_status in ((2, 0), (3, 2)):
            # Build one exact clean prefix.
            state = clean_schema_state(migrations, version)
            # Allocate a closeable runtime connection sentinel.
            connection = mock.Mock()
            # Capture machine-readable output.
            stdout = io.StringIO()
            # Patch only the fixed runtime connection and SELECT-backed compatibility result.
            with self.subTest(version=version), mock.patch("sys.argv", ["mysql_migrate.py", "bridge-check-schema2"]), mock.patch.object(mysql_migrate, "_connect_runtime", return_value=connection), mock.patch.object(mysql_migrate, "verify_runtime_compatibility", return_value=state), mock.patch.object(mysql_migrate.MigrationConfig, "from_env") as migration_config, redirect_stdout(stdout):
                # Require the exact stable CLI status.
                self.assertEqual(mysql_migrate.main(), expected_status)
            # Require deployment-only migration credentials to remain unread.
            migration_config.assert_not_called()
            # Require connection cleanup on success and refusal.
            connection.close.assert_called_once()
            # Require policy output to carry no target data.
            self.assertNotIn("127.0.0.1", stdout.getvalue())

    # Prove the disposable live harness refuses remote or split service tuples before connecting.
    def test_disposable_live_guard_requires_matching_loopback(self):
        # Import only the guard without invoking a connector.
        from tests.mysql_migration_live import _admin_kwargs
        # Build a complete but remote synthetic endpoint configuration.
        environment = {"CASINO_MYSQL_DISPOSABLE_TEST": "1", "CASINO_MYSQL_TEST_ADMIN_HOST": "remote.example.test", "CASINO_MYSQL_TEST_ADMIN_PORT": "3306", "CASINO_MYSQL_TEST_ADMIN_USER": "root", "CASINO_MYSQL_TEST_ADMIN_PASSWORD": "synthetic", "CASINO_MYSQL_MIGRATION_HOST": "remote.example.test", "CASINO_MYSQL_MIGRATION_PORT": "3306", "CASINO_MYSQL_HOST": "remote.example.test", "CASINO_MYSQL_PORT": "3306"}
        # Require refusal before any driver import or connection.
        with mock.patch.dict("os.environ", environment, clear=True), self.assertRaisesRegex(AssertionError, "loopback"):
            # Evaluate the administrator guard only.
            _admin_kwargs()
        # Replace hosts with loopback but split the runtime port.
        environment.update({"CASINO_MYSQL_TEST_ADMIN_HOST": "127.0.0.1", "CASINO_MYSQL_MIGRATION_HOST": "127.0.0.1", "CASINO_MYSQL_HOST": "127.0.0.1", "CASINO_MYSQL_PORT": "3307"})
        # Require the tuple mismatch to fail closed.
        with mock.patch.dict("os.environ", environment, clear=True), self.assertRaisesRegex(AssertionError, "do not match"):
            # Evaluate the split-tuple guard.
            _admin_kwargs()

    # Prove full-proof and per-boundary HMACs reject tampering in every proof section.
    def test_backup_proof_hmac_rejects_all_section_tampering(self):
        # Load the immutable plan.
        migrations, expected, _, _ = mysql_migrations.load_catalog()
        # Model a genuinely empty uninitialized target.
        state = mysql_migrations.SchemaState(False, 0, "uninitialized", None, mysql_migrations.migration_chain_digest(migrations, 0), tuple(), False)
        # Use one synthetic structural digest.
        state_sha256 = "b" * 64
        # Build a valid signed proof.
        proof = synthetic_proof(synthetic_config(), state, state_sha256, migrations, expected)
        # Validate the unmodified proof through an external temporary file.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve one proof path outside the repository.
            proof_path = Path(temporary) / "proof.json"
            # Write the valid synthetic record.
            proof_path.write_text(json.dumps(proof), encoding="utf-8")
            # Require acceptance inside the deterministic validity window.
            mysql_migrations.validate_backup_proof(proof_path, synthetic_config(), state, state_sha256, migrations, expected, datetime(2026, 7, 16, 18, 30, tzinfo=timezone.utc))
            # Enumerate one tamper in every contract section plus the target and schema fields.
            mutations = [
                # Change the contract schema.
                lambda item: item.__setitem__("schema", "changed"),
                # Change the target binding.
                lambda item: item.__setitem__("target_hmac_sha256", "0" * 64),
                # Change pre-state evidence.
                lambda item: item["pre_migration"].__setitem__("state_sha256", "0" * 64),
                # Change the migration plan.
                lambda item: item["plan"].__setitem__("to_version", 1),
                # Change quiesce evidence.
                lambda item: item["quiesce"].__setitem__("active", False),
                # Change backup evidence.
                lambda item: item["backup"].__setitem__("artifact_sha256", "0" * 64),
                # Change restore evidence.
                lambda item: item["restore"].__setitem__("restored_state_sha256", "0" * 64),
            ]
            # Verify every copied-and-edited proof fails its unchanged HMAC.
            for mutate in mutations:
                # Deep copy through JSON to match persisted proof shapes.
                tampered = json.loads(json.dumps(proof))
                # Apply exactly one section tamper.
                mutate(tampered)
                # Replace the temporary proof bytes.
                proof_path.write_text(json.dumps(tampered), encoding="utf-8")
                # Require uniform integrity failure before section-specific trust.
                with self.assertRaisesRegex(mysql_migrations.MigrationError, "integrity"):
                    # Validate the tampered proof.
                    mysql_migrations.validate_backup_proof(proof_path, synthetic_config(), state, state_sha256, migrations, expected, datetime(2026, 7, 16, 18, 30, tzinfo=timezone.utc))
            # Re-sign an independently altered quiesce marker without updating its boundary HMAC.
            boundary_tampered = json.loads(json.dumps(proof))
            # Change the bound quiesce time.
            boundary_tampered["quiesce"]["quiesced_at"] = "2026-07-16T18:01:00+00:00"
            # Recompute the whole-proof HMAC to reach the independent boundary check.
            boundary_tampered["proof_hmac_sha256"] = mysql_migrations.proof_hmac(boundary_tampered, synthetic_config())
            # Persist the HMAC-valid but boundary-invalid proof.
            proof_path.write_text(json.dumps(boundary_tampered), encoding="utf-8")
            # Require the distinct quiesce-boundary failure.
            with self.assertRaisesRegex(mysql_migrations.MigrationError, "quiesce boundary"):
                # Validate the altered boundary.
                mysql_migrations.validate_backup_proof(proof_path, synthetic_config(), state, state_sha256, migrations, expected, datetime(2026, 7, 16, 18, 30, tzinfo=timezone.utc))

    # Prove malformed proof input never leaks its path or content.
    def test_backup_proof_errors_are_secret_safe(self):
        # Load the immutable plan.
        migrations, expected, _, _ = mysql_migrations.load_catalog()
        # Model an empty target.
        state = mysql_migrations.SchemaState(False, 0, "uninitialized", None, mysql_migrations.migration_chain_digest(migrations, 0), tuple(), False)
        # Allocate a temporary hostile proof filename.
        with tempfile.TemporaryDirectory() as temporary:
            # Include a sentinel that must never appear in the error.
            proof_path = Path(temporary) / "private-target-sentinel.json"
            # Write malformed hostile content.
            proof_path.write_text("{private-value-sentinel", encoding="utf-8")
            # Capture the fixed read failure.
            with self.assertRaises(mysql_migrations.MigrationError) as captured:
                # Attempt proof validation.
                mysql_migrations.validate_backup_proof(proof_path, synthetic_config(), state, "b" * 64, migrations, expected)
            # Require neither path nor hostile value in the message.
            self.assertNotIn("sentinel", str(captured.exception))

    # Prove status, check, and a no-op dry run execute SELECT statements only.
    def test_status_check_and_dry_run_are_select_only(self):
        # Construct the statement-recording exact-compatible connection.
        connection = ReadOnlyConnection()
        # Inspect status through the read-only metadata path.
        state = mysql_migrations.inspect_schema(connection, connection.migrations)
        # Verify runtime compatibility through the same read-only path.
        mysql_migrations.verify_runtime_compatibility(connection)
        # Verify a no-op dry run needs no proof and performs no writes.
        self.assertEqual(mysql_migrations.dry_run(connection, synthetic_config(), None), tuple())
        # Require every database statement to start with SELECT.
        self.assertTrue(connection.statements and all(statement.lstrip().upper().startswith("SELECT") for statement, _ in connection.statements))
        # Require exact current state for the fake.
        self.assertEqual(state.current_version, connection.expected)

    # Prove a non-empty proof-validated dry run also issues SELECT statements only.
    def test_pending_dry_run_is_select_only(self):
        # Build an empty target whose complete catalog remains pending.
        connection = ReadOnlyConnection(pending=True)
        # Inspect the uninitialized state through read-only metadata.
        state = mysql_migrations.inspect_schema(connection, connection.migrations)
        # Compute exact synthetic structural state through SELECT-only queries.
        state_sha256 = mysql_migrations.schema_state_digest(connection, state)
        # Build a valid signed proof for the empty target and complete plan.
        proof = synthetic_proof(synthetic_config(), state, state_sha256, connection.migrations, connection.expected)
        # Allocate the external synthetic proof outside the checkout.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve the temporary proof path.
            proof_path = Path(temporary) / "proof.json"
            # Persist the complete signed proof.
            proof_path.write_text(json.dumps(proof), encoding="utf-8")
            # Clear setup reads so the dry-run assertion is isolated.
            connection.statements.clear()
            # Validate the pending plan inside the proof validity window.
            with mock.patch.object(mysql_migrations, "datetime", wraps=mysql_migrations.datetime) as clock:
                # Return the deterministic proof-window time for now().
                clock.now.return_value = datetime(2026, 7, 16, 18, 30, tzinfo=timezone.utc)
                # Execute the non-mutating pending dry run.
                pending = mysql_migrations.dry_run(connection, synthetic_config(), proof_path)
        # Require all four migration versions to remain pending.
        self.assertEqual([item.version for item in pending], [1, 2, 3, 4])
        # Require every database statement during pending dry-run to be SELECT.
        self.assertTrue(connection.statements and all(statement.lstrip().upper().startswith("SELECT") for statement, _ in connection.statements))

    # Prove one missing metadata table fails closed without creating the other.
    def test_partial_metadata_creation_requires_forward_fix(self):
        # Build a minimal connection whose first query returns one control table.
        connection = mock.Mock()
        # Build the one cursor used by inspection.
        cursor = connection.cursor.return_value
        # Return only one half of the metadata boundary.
        cursor.fetchall.return_value = [("casino_schema_migrations",)]
        # Require a fixed forward-fix outcome.
        with self.assertRaisesRegex(mysql_migrations.MigrationError, "forward-fix"):
            # Inspect without issuing any repair DDL.
            mysql_migrations.inspect_schema(connection)
        # Require the only database command to be SELECT.
        self.assertTrue(cursor.execute.call_args.args[0].startswith("SELECT"))

    # Prove the CLI apply path refuses before credentials, connector import, or database access.
    def test_cli_apply_is_held_before_configuration_or_connection(self):
        # Import the deployment CLI without executing its command boundary.
        from scripts import mysql_migrate
        # Capture the fixed machine-readable result.
        stdout = io.StringIO()
        # Patch hostile seams that must remain unreachable.
        with mock.patch("sys.argv", ["mysql_migrate.py", "apply"]), mock.patch.object(mysql_migrate.MigrationConfig, "from_env") as config, mock.patch.object(mysql_migrate, "_connect") as connect, redirect_stdout(stdout):
            # Require the documented policy failure status.
            self.assertEqual(mysql_migrate.main(), 2)
        # Require neither migration credentials nor a connector to be touched.
        config.assert_not_called()
        # Require no network-capable connector call.
        connect.assert_not_called()
        # Require only the fixed held-policy error.
        self.assertIn("apply policy is held", stdout.getvalue())

    # Prove absolute script execution binds imports to its release root from an unrelated cwd.
    def test_absolute_cli_script_resolves_release_modules_from_unrelated_cwd(self):
        # Resolve the exact candidate script under test.
        script = package_app.ROOT / "scripts" / "mysql_migrate.py"
        # Copy the process environment without adding an import path.
        environment = os.environ.copy()
        # Remove caller import-path influence.
        environment.pop("PYTHONPATH", None)
        # Prevent user-site packages from masking candidate import defects.
        environment["PYTHONNOUSERSITE"] = "1"
        # Prevent bytecode residue in the unrelated working directory.
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        # Allocate a disposable unrelated working directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Run only argument help, which imports all candidate modules but opens no connector.
            result = subprocess.run([sys.executable, "-B", str(script), "--help"], cwd=temporary, env=environment, capture_output=True, text=True, timeout=30, check=False)
        # Require successful direct-script import and argument construction.
        self.assertEqual(result.returncode, 0, result.stderr)
        # Require the candidate bridge command in the resolved script output.
        self.assertIn("bridge-check-schema2", result.stdout)
        # Reject the reproduced ambient-cwd import failure.
        self.assertNotIn("ModuleNotFoundError", result.stderr)

    # Prove a persisted schema-two/applying-three dirty boundary never replays automatically.
    def test_dirty_schema_two_applying_three_requires_forward_fix(self):
        # Load the exact immutable migration plan.
        migrations, _, _, _ = mysql_migrations.load_catalog()
        # Preserve the exact applied schema-two prefix.
        applied = tuple((item.version, item.name, item.checksum) for item in migrations[:2])
        # Model a known interrupted schema-three transition.
        dirty = mysql_migrations.SchemaState(True, 2, "dirty", 3, mysql_migrations.migration_chain_digest(migrations, 2), applied, True)
        # Record every lock and potential application statement.
        connection = FailureConnection()
        # Replace inspection to prove the held guard precedes even dirty-state reads.
        with mock.patch.object(mysql_migrations, "inspect_schema", return_value=dirty):
            # Require the catalog-level hold before any replay decision.
            with self.assertRaisesRegex(mysql_migrations.MigrationError, "apply policy is held"):
                # Attempt normal apply without bypass evidence.
                mysql_migrations.apply_migrations(connection, synthetic_config(), None)
        # Require no lock, read, DDL, or metadata statement.
        self.assertEqual(connection.statements, [])

    # Prove clean schema-two, schema-three, and schema-four prefixes are runtime compatible.
    def test_runtime_accepts_only_clean_exact_schema_two_three_or_four_prefixes(self):
        # Load the checksum-bound complete catalog.
        migrations, _, _, _ = mysql_migrations.load_catalog()
        # Exercise both reviewed runtime versions.
        for version in (2, 3, 4):
            # Build one exact clean prefix state.
            state = clean_schema_state(migrations, version)
            # Patch only the SELECT-backed state reader.
            with self.subTest(version=version), mock.patch.object(mysql_migrations, "inspect_schema", return_value=state):
                # Require the runtime verifier to return the same exact version.
                self.assertEqual(mysql_migrations.verify_runtime_compatibility(mock.Mock()).current_version, version)
        # Reject old, future, and dirty states through the same fixed boundary.
        refused = (
            # Schema one is below the closed bridge window.
            clean_schema_state(migrations, 1),
            # Schema five is an unknown future state.
            mysql_migrations.SchemaState(True, 5, "clean", None, "0" * 64, tuple(), True),
            # Applying schema three is not runtime-visible.
            mysql_migrations.SchemaState(True, 2, "applying", 3, mysql_migrations.migration_chain_digest(migrations, 2), tuple(), True),
            # Dirty schema three is not runtime-visible.
            mysql_migrations.SchemaState(True, 2, "dirty", 3, mysql_migrations.migration_chain_digest(migrations, 2), tuple(), True),
        )
        # Require every unreviewed runtime state to fail closed.
        for state in refused:
            # Patch only the already checksum-valid state result.
            with self.subTest(version=state.current_version, status=state.status), mock.patch.object(mysql_migrations, "inspect_schema", return_value=state), self.assertRaisesRegex(mysql_migrations.MigrationError, "not compatible"):
                # Exercise the public readiness boundary.
                mysql_migrations.verify_runtime_compatibility(mock.Mock())

    # Prove runtime readiness source contains no DDL or migration-state DML.
    def test_runtime_readiness_is_ddl_free(self):
        # Read only the readiness method source.
        source = inspect.getsource(storage.MySQLStorageProvider.ensure_ready).upper()
        # Require the read-only compatibility verifier.
        self.assertIn("VERIFY_RUNTIME_COMPATIBILITY", source)
        # Reject every schema or migration-state mutation verb.
        for verb in ("CREATE ", "ALTER ", "DROP ", "INSERT ", "UPDATE ", "DELETE "):
            # Assert the runtime method contains no mutation statement.
            self.assertNotIn(verb, source)


# Support direct focused execution in local and CI validation.
if __name__ == "__main__":
    # Run the focused suite with standard unittest output.
    unittest.main()
