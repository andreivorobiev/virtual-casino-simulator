"""Focused repository and disposable-MySQL evidence for TEST-048."""

# Import deep-copy JSON handling for proof tamper cases.
import json
# Import in-memory streams for secret-safe CLI output assertions.
import io
# Import output redirection for isolated command-line failure tests.
from contextlib import redirect_stderr, redirect_stdout
# Import source inspection for the runtime DDL-free invariant.
import inspect
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
        # Require the three explicit sequential migrations and exact-only compatibility.
        self.assertEqual([item.version for item in migrations], [1, 2, 3])
        # Require the separately versioned runtime window.
        self.assertEqual((minimum, expected), (3, 3))
        # Require canonical SHA-256 identities.
        self.assertRegex(catalog_sha256, r"^[0-9a-f]{64}$")
        # Require every listed migration to retain a distinct checksum.
        self.assertEqual(len({item.checksum for item in migrations}), 3)
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
        # Require one reviewed complete chain identity for the new catalog tail.
        self.assertEqual(mysql_migrations.migration_chain_digest(migrations), "083682e266576aa571e20f2baf6746b0ee28c8f81906c17dc96f05bed6a51a7b")

    # Prove schema three adds one bounded exact-scope receipt-capacity table and no journal.
    def test_schema_three_receipt_boundary_is_exact_and_bounded(self):
        # Load the checksum-verified schema-three migration through the production parser.
        migrations, expected, _, _ = mysql_migrations.load_catalog()
        # Select only the new receipt-capacity migration tail.
        migration = migrations[-1]
        # Require the exact stable migration identity.
        self.assertEqual((expected, migration.version, migration.name), (3, 3, "game-action-receipts"))
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

    # Prove the public migration runner applies exact 0-to-3 and 2-to-3 suffixes.
    def test_public_apply_supports_fresh_and_schema_two_upgrade(self):
        # Load the immutable plan used by both synthetic application paths.
        migrations, _, _, _ = mysql_migrations.load_catalog()
        # Build the exact states needed after each public runner transition.
        version_zero = clean_schema_state(migrations, 0)
        # Model a genuinely empty target before metadata initialization.
        uninitialized = clean_schema_state(migrations, 0, initialized=False)
        # Build every clean applied prefix.
        version_one = clean_schema_state(migrations, 1)
        # Preserve exact schema-two upgrade provenance.
        version_two = clean_schema_state(migrations, 2)
        # Preserve the final schema-three state.
        version_three = clean_schema_state(migrations, 3)
        # Exercise both the empty and exact schema-two source in one bounded table.
        cases = (
            # Fresh apply initializes metadata and executes all application migrations.
            ("fresh", [uninitialized, version_zero, version_one, version_two, version_three], migrations, True),
            # Exact upgrade executes only the additive schema-three tail.
            ("upgrade", [version_two, version_three], migrations[2:], False),
        )
        # Run each source-state transition independently.
        for label, states, expected_migrations, initializes in cases:
            # Allocate one statement-recording connector boundary.
            connection = FailureConnection()
            # Patch state/proof seams while exercising the real public apply loop.
            with self.subTest(label=label), mock.patch.object(mysql_migrations, "inspect_schema", side_effect=states), mock.patch.object(mysql_migrations, "schema_state_digest", return_value="b" * 64), mock.patch.object(mysql_migrations, "validate_backup_proof", return_value={}), mock.patch.object(mysql_migrations, "_initialize_metadata") as initialize, mock.patch.object(mysql_migrations, "_mark_applying") as mark_applying, mock.patch.object(mysql_migrations, "_mark_complete") as mark_complete, mock.patch.object(mysql_migrations, "verify_runtime_compatibility", return_value=version_three):
                # Apply through the unchanged production migration state machine.
                result = mysql_migrations.apply_migrations(connection, synthetic_config(), Path("synthetic-proof"))
            # Require exact clean schema-three completion.
            self.assertEqual((result.current_version, result.status), (3, "clean"))
            # Require metadata initialization only for the empty target.
            self.assertEqual(initialize.call_count, int(initializes))
            # Require applying and completion markers for the exact pending suffix.
            self.assertEqual([call.args[2] for call in mark_applying.call_args_list], list(expected_migrations))
            # Require exact completion records for the same suffix.
            self.assertEqual([call.args[1] for call in mark_complete.call_args_list], list(expected_migrations))
            # Extract only immutable application statements between lock operations.
            application_statements = [statement for statement, _ in connection.statements if not statement.startswith("SELECT ")]
            # Require exact statement order and no invented repair or journal SQL.
            self.assertEqual(application_statements, [statement for migration in expected_migrations for statement in migration.statements])

    # Prove release packaging binds and requires the exact schema-three inventory.
    def test_package_inventory_requires_schema_three(self):
        # Calculate release schema provenance from the selected source tree.
        inventory = package_app.mysql_schema_inventory(package_app.ROOT)
        # Require exact-only schema-three runtime compatibility.
        self.assertEqual((inventory["minimum_version"], inventory["expected_version"]), (3, 3))
        # Require the same deterministic chain as the migration runtime.
        self.assertEqual(inventory["migration_chain_sha256"], "083682e266576aa571e20f2baf6746b0ee28c8f81906c17dc96f05bed6a51a7b")
        # Require every immutable migration path in the archive's mandatory allowlist.
        self.assertTrue(
            {
                "migrations/mysql/0001_initial.json",
                "migrations/mysql/0002_action_identity.json",
                "migrations/mysql/0003_game_action_receipts.json",
                "migrations/mysql/catalog.json",
            }.issubset(package_app.REQUIRED_FILES)
        )
        # Read the tracked source inventory and add the new checkpoint file before commit.
        repository_paths = [*package_app.tracked_paths(package_app.ROOT), "migrations/mysql/0003_game_action_receipts.json"]
        # Select the exact package inventory through the production allowlist.
        selected = package_app.select_release_files(package_app.ROOT, repository_paths)
        # Require the schema-three descriptor to be physically packaged.
        self.assertIn("migrations/mysql/0003_game_action_receipts.json", selected)
        # Remove only the new migration from an otherwise complete source inventory.
        missing_three = [path for path in repository_paths if path != "migrations/mysql/0003_game_action_receipts.json"]
        # Require package selection to fail before creating an incomplete archive.
        with self.assertRaisesRegex(ValueError, "0003_game_action_receipts"):
            # Attempt selection without the catalog-required migration.
            package_app.select_release_files(package_app.ROOT, missing_three)

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
        # Require all three migration versions to remain pending.
        self.assertEqual([item.version for item in pending], [1, 2, 3])
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

    # Prove connection loss after DDL does not claim dirty-state persistence.
    def test_connection_loss_reports_unconfirmed_dirty_state(self):
        # Load the immutable catalog for the exact schema-two upgrade state.
        migrations, _, _, _ = mysql_migrations.load_catalog()
        # Model the clean schema-two source whose only pending migration is version three.
        state = clean_schema_state(migrations, 2)
        # Build the connection that loses transport on application SQL.
        connection = FailureConnection(fail_application_statement=True)
        # Capture the exact interrupted migration passed to dirty-state persistence.
        dirty_marker = mock.Mock(side_effect=ConnectionError("synthetic marker loss"))
        # Replace preflight/state helpers so this test targets failure semantics only.
        with mock.patch.object(mysql_migrations, "inspect_schema", return_value=state), mock.patch.object(mysql_migrations, "schema_state_digest", return_value="b" * 64), mock.patch.object(mysql_migrations, "validate_backup_proof", return_value={}), mock.patch.object(mysql_migrations, "_mark_applying", return_value=None), mock.patch.object(mysql_migrations, "_mark_dirty", dirty_marker):
            # Require the explicit unknown-dirty-state outcome.
            with self.assertRaisesRegex(mysql_migrations.MigrationError, "dirty state could not be confirmed"):
                # Apply against synthetic proof while all real connection identifiers remain unused.
                mysql_migrations.apply_migrations(connection, synthetic_config(), Path("synthetic-proof"))
        # Require the fail-closed marker to name only the interrupted schema-three migration.
        self.assertEqual(dirty_marker.call_args.args[1], migrations[2])
        # Require apply to force non-autocommit before the failed statement.
        self.assertFalse(connection.autocommit)
        # Require advisory lock release to be attempted after the primary failure.
        self.assertTrue(any(statement.startswith("SELECT RELEASE_LOCK") for statement, _ in connection.statements))

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
        # Return only the dirty state after the advisory lock is acquired.
        with mock.patch.object(mysql_migrations, "inspect_schema", return_value=dirty):
            # Require a reviewed forward-fix rather than replay.
            with self.assertRaisesRegex(mysql_migrations.MigrationError, "forward-fix"):
                # Attempt normal apply without bypass evidence.
                mysql_migrations.apply_migrations(connection, synthetic_config(), None)
        # Require no application statement or migration metadata mutation.
        self.assertTrue(all(statement.startswith("SELECT ") for statement, _ in connection.statements))

    # Prove unconfirmed advisory-lock release fails a successful no-op recheck.
    def test_lock_release_failure_fails_closed(self):
        # Load the exact expected state.
        migrations, expected, _, _ = mysql_migrations.load_catalog()
        # Build complete applied history.
        applied = tuple((item.version, item.name, item.checksum) for item in migrations)
        # Model exact clean compatibility.
        state = mysql_migrations.SchemaState(True, expected, "clean", None, mysql_migrations.migration_chain_digest(migrations), applied, True)
        # Build a connection that cannot confirm release.
        connection = FailureConnection(release_result=0)
        # Replace only schema reads because the test targets lock behavior.
        with mock.patch.object(mysql_migrations, "inspect_schema", return_value=state), mock.patch.object(mysql_migrations, "verify_runtime_compatibility", return_value=state):
            # Require the combined fail-closed release diagnostic.
            with self.assertRaisesRegex(mysql_migrations.MigrationError, "release could not be confirmed"):
                # Run the repeat-safe apply path with no pending migrations.
                mysql_migrations.apply_migrations(connection, synthetic_config(), None)

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
