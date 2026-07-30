"""Disposable MySQL 8.4 migration, runtime-grant, restart, and lock evidence for TEST-048."""

# Import UTC timing for short-lived synthetic recovery proofs.
from datetime import datetime, timedelta, timezone
# Import process isolation for advisory-lock and runtime transaction evidence.
from concurrent.futures import ProcessPoolExecutor
# Import JSON for synthetic proof files.
import json
# Import environment access for explicitly enabled disposable CI configuration.
import os
# Import strict identifier validation before disposable administrative SQL.
import re
# Import temporary directories for proof records outside the checkout.
import tempfile
# Import portable temporary proof paths.
from pathlib import Path

# Import the migration policy and runtime storage provider under test.
from casino.core import mysql_migrations, storage
# Import the established live provider restart and two-process DML matrix.
from tests import storage_tests

# Accept only simple synthetic identifiers before interpolating disposable DDL.
IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
# Require an explicit disposable-service marker so ambient databases are never touched.
DISPOSABLE_MARKER = "CASINO_MYSQL_DISPOSABLE_TEST"


# Validate one test-only database or account identifier before SQL interpolation.
def _identifier(value: str) -> str:
    # Normalize the explicit synthetic identifier.
    candidate = str(value).strip()
    # Reject provider, production, or punctuation-bearing identifiers.
    if not IDENTIFIER_RE.fullmatch(candidate) or not candidate.endswith("_204"):
        # Keep the failure independent of the rejected value.
        raise AssertionError("Disposable MySQL test identifier is invalid")
    # Return the validated synthetic identifier.
    return candidate


# Load explicit test-administrator configuration without reusing runtime or migrator credentials.
def _admin_kwargs() -> dict:
    # Require a newly created disposable service marker before reading connection settings.
    if os.environ.get(DISPOSABLE_MARKER) != "1":
        # Stop before importing a driver or connecting to any service.
        raise AssertionError("Disposable MySQL migration test is not explicitly enabled")
    # Read only test-admin-prefixed variables supplied by the ephemeral CI service.
    values = {name: str(os.environ.get(environment, "")).strip() for name, environment in {"host": "CASINO_MYSQL_TEST_ADMIN_HOST", "user": "CASINO_MYSQL_TEST_ADMIN_USER", "password": "CASINO_MYSQL_TEST_ADMIN_PASSWORD"}.items()}
    # Reject incomplete test administration configuration.
    if any(not value for value in values.values()):
        # Stop without falling back to local or runtime credentials.
        raise AssertionError("Disposable MySQL test administrator configuration is incomplete")
    # Parse the explicit ephemeral service port.
    port = int(os.environ.get("CASINO_MYSQL_TEST_ADMIN_PORT", "3306"))
    # Read migration and runtime endpoints before any connection is opened.
    migration_host = str(os.environ.get("CASINO_MYSQL_MIGRATION_HOST", "")).strip().lower()
    # Read the runtime host independently.
    runtime_host = str(os.environ.get("CASINO_MYSQL_HOST", "")).strip().lower()
    # Require every administrative, migration, and runtime host to be literal loopback.
    if values["host"].lower() != "127.0.0.1" or migration_host != "127.0.0.1" or runtime_host != "127.0.0.1":
        # Refuse even test-suffixed identifiers on a remote endpoint.
        raise AssertionError("Disposable MySQL test endpoints must be exact loopback")
    # Parse migration and runtime ports without falling back across identities.
    migration_port = int(os.environ.get("CASINO_MYSQL_MIGRATION_PORT", "0"))
    # Parse the runtime port independently.
    runtime_port = int(os.environ.get("CASINO_MYSQL_PORT", "0"))
    # Require all three connections to address the same ephemeral loopback service.
    if port != migration_port or port != runtime_port:
        # Stop before administrator access when service tuples differ.
        raise AssertionError("Disposable MySQL test endpoints do not match")
    # Return a fresh driver mapping without formatting or logging it.
    return {**values, "port": port}


# Open the optional connector only inside the explicitly enabled disposable matrix.
def _connector():
    # Import the CI-installed optional MySQL dependency.
    import mysql.connector
    # Return the driver module for exact error assertions.
    return mysql.connector


# Create a migration config for one validated disposable database.
def _migration_config(database: str) -> mysql_migrations.MigrationConfig:
    # Load the base deployment-only synthetic config.
    base = mysql_migrations.MigrationConfig.from_env()
    # Return the same endpoint/account/key bound to the selected disposable database.
    return mysql_migrations.MigrationConfig(base.host, base.port, base.user, base.password, _identifier(database), base.target_binding_key)


# Write a current synthetic proof bound to one exact disposable pre-state.
def _proof(connection, config, directory: Path, name: str) -> Path:
    # Load the immutable plan and expected schema version.
    migrations, expected, _, _ = mysql_migrations.load_catalog()
    # Inspect exact migration state through read-only metadata.
    state = mysql_migrations.inspect_schema(connection, migrations)
    # Hash columns, indexes, constraints, engines, collations, and migration state.
    state_sha256 = mysql_migrations.schema_state_digest(connection, state)
    # Establish a current strict quiesce/backup/restore timeline.
    now = datetime.now(timezone.utc)
    # Record quiesce before the synthetic backup.
    quiesced = now - timedelta(minutes=3)
    # Record backup completion after quiesce.
    completed = now - timedelta(minutes=2)
    # Record clean-target restore verification after backup.
    verified = now - timedelta(minutes=1)
    # Use only a synthetic checksum because this matrix performs no #205 backup operation.
    artifact_sha256 = "a" * 64
    # Bind the complete immutable migration chain.
    chain = mysql_migrations.migration_chain_digest(migrations)
    # Render UTC timestamps in one stable form.
    quiesced_text = quiesced.isoformat()
    # Assemble the complete proof contract.
    proof = {
        # Identify the accepted proof contract.
        "schema": mysql_migrations.BACKUP_PROOF_SCHEMA,
        # Bind the exact target by keyed HMAC.
        "target_hmac_sha256": mysql_migrations.target_fingerprint(config),
        # Bind the exact pre-state.
        "pre_migration": {"version": state.current_version, "status": state.status, "state_sha256": state_sha256},
        # Bind the complete intended plan.
        "plan": {"from_version": state.current_version, "to_version": expected, "migration_chain_sha256": chain},
        # Record an active source quiesce boundary.
        "quiesce": {"active": True, "quiesced_at": quiesced_text},
        # Record a completed synthetic backup artifact.
        "backup": {"completed": True, "artifact_sha256": artifact_sha256, "completed_at": completed.isoformat()},
        # Record exact synthetic clean-target restore evidence.
        "restore": {"verified": True, "backup_artifact_sha256": artifact_sha256, "restored_state_sha256": state_sha256, "verified_at": verified.isoformat(), "expires_at": (verified + timedelta(hours=2)).isoformat()},
    }
    # Bind quiesce to target, state, plan, and timestamp.
    proof["quiesce"]["boundary_hmac_sha256"] = mysql_migrations.quiesce_boundary_hmac(config, state, state_sha256, chain, expected, quiesced_text)
    # Integrity-protect every proof section.
    proof["proof_hmac_sha256"] = mysql_migrations.proof_hmac(proof, config)
    # Resolve one external temporary proof file.
    proof_path = directory / f"{name}.json"
    # Write only synthetic evidence outside the repository.
    proof_path.write_text(json.dumps(proof, sort_keys=True), encoding="utf-8")
    # Return the external proof path for this disposable target.
    return proof_path


# Attempt one apply from a separate process while another connection owns the target lock.
def _locked_apply_worker(database: str, proof_path: str) -> str:
    # Build the exact process-local migration config.
    config = _migration_config(database)
    # Open an independent process-owned migrator connection.
    connection = _connector().connect(**config.kwargs())
    # Always close the process-owned connection.
    try:
        # Start protected apply so the fixed lock result can be returned.
        try:
            # Use a one-second lock wait against the parent-held lock.
            mysql_migrations.apply_migrations(connection, config, Path(proof_path), 1)
        # Capture only the fixed migration-policy diagnostic.
        except mysql_migrations.MigrationError as exc:
            # Return the sanitized error text for assertion.
            return str(exc)
        # Fail when the second process bypassed the held lock.
        return "unexpected-success"
    # Close the process connector without leaving a listener or service.
    finally:
        # Release all process-owned resources.
        connection.close()


# Recreate only explicitly validated disposable databases and synthetic accounts.
def _prepare(admin, databases, migrator_user, migrator_password, runtime_user, runtime_password):
    # Open an administrative cursor inside the disposable service.
    cursor = admin.cursor()
    # Recreate every isolated database from empty state.
    for database in databases:
        # Drop only the validated test database.
        cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
        # Recreate the isolated utf8mb4 target.
        cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    # Remove any stale synthetic users inside this disposable service.
    cursor.execute(f"DROP USER IF EXISTS '{migrator_user}'@'%'")
    # Remove any stale runtime test user.
    cursor.execute(f"DROP USER IF EXISTS '{runtime_user}'@'%'")
    # Create the separate migrator identity with a bound parameter secret.
    cursor.execute(f"CREATE USER '{migrator_user}'@'%' IDENTIFIED BY %s", (migrator_password,))
    # Create the separate runtime identity with a bound parameter secret.
    cursor.execute(f"CREATE USER '{runtime_user}'@'%' IDENTIFIED BY %s", (runtime_password,))
    # Grant schema-management privileges only to the migrator on disposable targets.
    for database in databases:
        # Grant database-scoped migration privileges without grant option.
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{migrator_user}'@'%'")
    # Commit account and database setup inside the disposable service.
    admin.commit()


# Remove every database and account created by this matrix.
def _cleanup(admin, databases, migrator_user, runtime_user):
    # Open a fresh administrative cursor for deterministic teardown.
    cursor = admin.cursor()
    # Drop each validated isolated test database.
    for database in databases:
        # Remove only the test-suffixed database.
        cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
    # Drop the isolated migrator identity.
    cursor.execute(f"DROP USER IF EXISTS '{migrator_user}'@'%'")
    # Drop the isolated runtime identity.
    cursor.execute(f"DROP USER IF EXISTS '{runtime_user}'@'%'")
    # Commit teardown before the ephemeral CI service is destroyed.
    admin.commit()


# Run the complete MySQL 8.4 migration and DDL-free runtime matrix.
def run_mysql_migration_live_matrix(request_latency_callback=None):
    # Reject a malformed optional test callback before any administrator connection.
    if request_latency_callback is not None and not callable(request_latency_callback):
        # Keep the no-argument production path unchanged while failing closed on test misuse.
        raise TypeError("request_latency_callback must be callable")
    # Validate every synthetic database and account before connecting.
    base_database = _identifier(os.environ["CASINO_MYSQL_MIGRATION_DATABASE"])
    # Derive a separate explicit version-one upgrade target.
    upgrade_database = _identifier("casino_upgrade_204")
    # Derive a separate proof-tamper target.
    tamper_database = _identifier("casino_tamper_204")
    # Freeze the complete database list for setup and cleanup.
    databases = (base_database, upgrade_database, tamper_database)
    # Require the runtime tuple to select the same base disposable database.
    if _identifier(os.environ["CASINO_MYSQL_DATABASE"]) != base_database:
        # Refuse split targets before administrator connection.
        raise AssertionError("Disposable MySQL runtime and migration targets do not match")
    # Validate the migration user from deployment-only config.
    migrator_user = _identifier(os.environ["CASINO_MYSQL_MIGRATION_USER"])
    # Read the synthetic migration secret without printing it.
    migrator_password = os.environ["CASINO_MYSQL_MIGRATION_PASSWORD"]
    # Validate the distinct runtime identity.
    runtime_user = _identifier(os.environ["CASINO_MYSQL_USER"])
    # Read the synthetic runtime secret without printing it.
    runtime_password = os.environ["CASINO_MYSQL_PASSWORD"]
    # Require separate migration and runtime identities and secrets.
    assert migrator_user != runtime_user and migrator_password != runtime_password
    # Open the disposable service administrator connection.
    admin = _connector().connect(**_admin_kwargs())
    # Allocate synthetic proof files outside the repository.
    with tempfile.TemporaryDirectory(prefix="casino-migration-live-") as temporary:
        # Resolve the temporary proof root.
        proof_root = Path(temporary)
        # Start protected setup and matrix execution so cleanup always runs.
        try:
            # Recreate empty isolated databases and separate accounts.
            _prepare(admin, databases, migrator_user, migrator_password, runtime_user, runtime_password)
            # Build base migration configuration.
            base_config = _migration_config(base_database)
            # Open one base migrator connection.
            base_connection = _connector().connect(**base_config.kwargs())
            # Start protected base migration and lock evidence.
            try:
                # Create proof for exact empty version zero.
                base_proof = _proof(base_connection, base_config, proof_root, "base")
                # Acquire the exact target lock in the parent connection.
                lock_name = "casino-migrate-" + mysql_migrations.target_fingerprint(base_config)[:40]
                # Open the parent lock cursor.
                lock_cursor = base_connection.cursor()
                # Acquire without waiting.
                lock_cursor.execute("SELECT GET_LOCK(%s, 0)", (lock_name,))
                # Require successful parent lock ownership.
                assert lock_cursor.fetchone()[0] == 1
                # Start a separate process that must time out on the same target lock.
                with ProcessPoolExecutor(max_workers=1) as executor:
                    # Capture only the fixed child outcome.
                    locked_result = executor.submit(_locked_apply_worker, base_database, str(base_proof)).result(timeout=30)
                # Require advisory serialization across processes.
                assert "advisory lock is unavailable" in locked_result
                # Release the parent-owned target lock.
                lock_cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                # Require release confirmation before normal apply.
                assert lock_cursor.fetchone()[0] == 1
                # Apply clean empty 0-to-1-to-2 under the real runner.
                final_state = mysql_migrations.apply_migrations(base_connection, base_config, base_proof)
                # Require exact schema version two.
                assert final_state.current_version == 2 and final_state.status == "clean"
                # Require exact applied migration sequence.
                assert [item[0] for item in final_state.applied] == [1, 2]
                # Prove repeat-safe exact recheck needs no backup proof or DDL.
                assert mysql_migrations.apply_migrations(base_connection, base_config, None).current_version == 2
            # Always close the base migrator connection.
            finally:
                # Release all base connection resources.
                base_connection.close()
            # Build and open the isolated supported-upgrade target.
            upgrade_config = _migration_config(upgrade_database)
            # Connect as the deployment-only migrator.
            upgrade_connection = _connector().connect(**upgrade_config.kwargs())
            # Start protected version-one seeding and runner upgrade.
            try:
                # Load the immutable two-step catalog.
                migrations, expected, _, _ = mysql_migrations.load_catalog()
                # Create and validate proof before metadata DDL in test setup.
                initial_proof = _proof(upgrade_connection, upgrade_config, proof_root, "upgrade-initial")
                # Inspect and hash the exact empty pre-state.
                initial_state = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Compute exact empty structural identity.
                initial_digest = mysql_migrations.schema_state_digest(upgrade_connection, initial_state)
                # Validate the complete recovery proof before setup DDL.
                mysql_migrations.validate_backup_proof(initial_proof, upgrade_config, initial_state, initial_digest, migrations, expected)
                # Disable autocommit for metadata history/state DML.
                upgrade_connection.autocommit = False
                # Establish the minimal migration metadata boundary.
                mysql_migrations._initialize_metadata(upgrade_connection, migrations)
                # Read clean version-zero metadata.
                version_zero = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Mark version one applying before application DDL.
                mysql_migrations._mark_applying(upgrade_connection, version_zero, migrations[0])
                # Execute exact version-one statements without SQL splitting.
                cursor = upgrade_connection.cursor()
                # Apply the reviewed initial-schema statements.
                for statement in migrations[0].statements:
                    # Execute one exact driver statement.
                    cursor.execute(statement)
                # Mark only the completed version-one checksum.
                mysql_migrations._mark_complete(upgrade_connection, migrations[0], migrations)
                # Require the supported clean version-one state.
                version_one = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Prove the isolated upgrade starts exactly at one.
                assert version_one.current_version == 1 and version_one.status == "clean"
                # Create a new exact version-one backup/restore proof.
                upgrade_proof = _proof(upgrade_connection, upgrade_config, proof_root, "upgrade")
                # Apply only the pending 1-to-2 suffix through the public runner.
                assert mysql_migrations.apply_migrations(upgrade_connection, upgrade_config, upgrade_proof).current_version == 2
                # Capture exact immutable rows for corruption/refusal cases.
                applied_rows = [(item.version, item.name, item.checksum) for item in migrations]
                # Corrupt one checksum in the disposable metadata.
                cursor.execute("UPDATE casino_schema_migrations SET checksum = %s WHERE version = 1", ("0" * 64,))
                # Commit the corruption fixture.
                upgrade_connection.commit()
                # Require checksum refusal.
                try:
                    # Inspect the corrupted history.
                    mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Accept only the fixed migration error.
                except mysql_migrations.MigrationError:
                    # Continue after expected refusal.
                    pass
                # Fail if corrupted checksum was accepted.
                else:
                    # Surface the missing refusal.
                    raise AssertionError("checksum mismatch was accepted")
                # Restore exact checksum fixture.
                cursor.execute("UPDATE casino_schema_migrations SET checksum = %s WHERE version = 1", (applied_rows[0][2],))
                # Delete version one to create a history gap.
                cursor.execute("DELETE FROM casino_schema_migrations WHERE version = 1")
                # Commit the gap fixture.
                upgrade_connection.commit()
                # Require gap refusal.
                try:
                    # Inspect the gapped history.
                    mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Accept only fixed migration refusal.
                except mysql_migrations.MigrationError:
                    # Continue after expected refusal.
                    pass
                # Fail if gap was accepted.
                else:
                    # Surface the missing refusal.
                    raise AssertionError("migration gap was accepted")
                # Restore exact version-one row.
                cursor.execute("INSERT INTO casino_schema_migrations (version, name, checksum, applied_at) VALUES (1, %s, %s, %s)", (applied_rows[0][1], applied_rows[0][2], datetime.now(timezone.utc).isoformat()))
                # Set an impossible future current version.
                cursor.execute("UPDATE casino_schema_migration_state SET current_version = 3 WHERE state_id = 1")
                # Commit the future fixture.
                upgrade_connection.commit()
                # Require future refusal.
                try:
                    # Inspect the unknown future state.
                    mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Accept only fixed migration refusal.
                except mysql_migrations.MigrationError:
                    # Continue after expected refusal.
                    pass
                # Fail if future state was accepted.
                else:
                    # Surface the missing refusal.
                    raise AssertionError("future migration state was accepted")
                # Restore current version and mark the next transition dirty.
                cursor.execute("UPDATE casino_schema_migration_state SET current_version = 2, status = 'dirty', applying_version = 3 WHERE state_id = 1")
                # Commit the dirty fixture.
                upgrade_connection.commit()
                # Require runtime refusal of dirty state.
                try:
                    # Verify exact runtime compatibility.
                    mysql_migrations.verify_runtime_compatibility(upgrade_connection)
                # Accept fixed dirty-state refusal.
                except mysql_migrations.MigrationError:
                    # Continue after expected refusal.
                    pass
                # Fail if dirty state was accepted.
                else:
                    # Surface the missing refusal.
                    raise AssertionError("dirty migration state was accepted")
                # Require normal apply to refuse dirty state without repair bypass.
                try:
                    # Attempt a normal no-proof apply.
                    mysql_migrations.apply_migrations(upgrade_connection, upgrade_config, None)
                # Accept fixed forward-fix refusal.
                except mysql_migrations.MigrationError:
                    # Continue after expected refusal.
                    pass
                # Fail if dirty state was cleared or accepted.
                else:
                    # Surface the missing refusal.
                    raise AssertionError("dirty migration state was applied")
            # Always close the upgrade migrator connection.
            finally:
                # Release upgrade connection resources.
                upgrade_connection.close()
            # Build the isolated proof-tamper target.
            tamper_config = _migration_config(tamper_database)
            # Connect as migrator to the empty tamper target.
            tamper_connection = _connector().connect(**tamper_config.kwargs())
            # Start protected tamper-before-DDL proof.
            try:
                # Create one valid empty-target proof.
                tamper_proof = _proof(tamper_connection, tamper_config, proof_root, "tamper")
                # Parse and edit the backup section without the HMAC key flow.
                tampered = json.loads(tamper_proof.read_text(encoding="utf-8"))
                # Change the artifact checksum without re-signing.
                tampered["backup"]["artifact_sha256"] = "0" * 64
                # Persist the tampered proof.
                tamper_proof.write_text(json.dumps(tampered), encoding="utf-8")
                # Require proof refusal.
                try:
                    # Attempt apply with tampered recovery evidence.
                    mysql_migrations.apply_migrations(tamper_connection, tamper_config, tamper_proof)
                # Accept only the fixed proof-integrity failure.
                except mysql_migrations.MigrationError:
                    # Continue after expected refusal.
                    pass
                # Fail if tampered proof was accepted.
                else:
                    # Surface the missing refusal.
                    raise AssertionError("tampered backup proof was accepted")
                # Verify refusal occurred before even migration metadata DDL.
                cursor = tamper_connection.cursor()
                # Count all Casino-owned tables on the untouched target.
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\'")
                # Require exact empty state.
                assert int(cursor.fetchone()[0]) == 0
            # Always close the tamper migrator connection.
            finally:
                # Release tamper connection resources.
                tamper_connection.close()
            # Grant runtime DML only after the base schema is fully migrated.
            admin_cursor = admin.cursor()
            # Grant database-scoped runtime SELECT and DML without schema privileges.
            admin_cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{base_database}`.* TO '{runtime_user}'@'%'")
            # Commit the least-privilege grant.
            admin.commit()
            # Open a runtime-identity connection for compatibility and denial evidence.
            runtime_connection = _connector().connect(host=os.environ["CASINO_MYSQL_HOST"], port=int(os.environ.get("CASINO_MYSQL_PORT", "3306")), user=runtime_user, password=runtime_password, database=base_database)
            # Start protected runtime grant tests.
            try:
                # Prove runtime startup compatibility with SELECT only.
                assert mysql_migrations.verify_runtime_compatibility(runtime_connection).current_version == 2
                # Read actual grants through the runtime identity.
                runtime_cursor = runtime_connection.cursor()
                # Query current-user grants without administrator credentials.
                runtime_cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
                # Normalize grant text only in memory.
                grants = "\n".join(str(row[0]).upper() for row in runtime_cursor.fetchall())
                # Require the four approved DML privileges.
                assert all(privilege in grants for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"))
                # Require no schema or grant-management privilege.
                assert all(privilege not in grants for privilege in ("CREATE", "ALTER", "DROP", "INDEX", "TRIGGER", "GRANT OPTION"))
                # Enumerate actual forbidden schema and grant-management attempts.
                generic_denials = frozenset({1044, 1045, 1142, 1227})
                denied_statements = (
                    # Attempt table creation.
                    ("CREATE TABLE casino_forbidden_204 (id INT)", generic_denials),
                    # Attempt an additive table change.
                    ("ALTER TABLE casino_documents ADD COLUMN forbidden_204 INT NULL", generic_denials),
                    # Attempt to drop an application table.
                    ("DROP TABLE casino_documents", generic_denials),
                    # Attempt a new index.
                    ("CREATE INDEX forbidden_204 ON casino_documents(updated_at)", generic_denials),
                    # MySQL 8.4 with binary logging may reject trigger creation as
                    # errno 1419 before it reaches the ordinary TRIGGER check.
                    (
                        "CREATE TRIGGER forbidden_204 BEFORE INSERT ON casino_documents "
                        "FOR EACH ROW SET NEW.updated_at = NEW.updated_at",
                        generic_denials | {1419},
                    ),
                    # Attempt grant management.
                    (f"GRANT SELECT ON `{base_database}`.* TO '{runtime_user}'@'%'", generic_denials),
                )
                # Require every forbidden statement to be denied by privilege enforcement.
                for statement, allowed_denials in denied_statements:
                    # Start protected execution for one expected denial.
                    try:
                        # Execute the forbidden operation as the runtime identity.
                        runtime_cursor.execute(statement)
                    # Accept only connector database errors.
                    except _connector().Error as exc:
                        # Require a privilege-denied server code, not a syntax error.
                        errno = int(getattr(exc, "errno", 0) or 0)
                        assert errno in allowed_denials
                        # Keep binary-log denial acceptance scoped only to triggers.
                        if errno == 1419:
                            assert statement.startswith("CREATE TRIGGER ")
                    # Fail if the runtime identity performed schema or grant management.
                    else:
                        # Surface only the fixed privilege category.
                        raise AssertionError("runtime schema or grant-management operation was permitted")
            # Always close the runtime evidence connection.
            finally:
                # Release runtime connector resources.
                runtime_connection.close()
            # Run representative runtime DML, restart, and two-process exact-once evidence.
            storage_tests.run_mysql_live_provider_path()
            # Run an optional credential-free test callback only after migration and runtime grants.
            if request_latency_callback is not None:
                # Invoke without arguments so administrator, migrator, and runtime credentials never cross the seam.
                request_latency_callback()
        # Always remove every disposable database and account.
        finally:
            # Teardown only validated `_204` targets and users.
            _cleanup(admin, databases, migrator_user, runtime_user)
            # Close the disposable administrator connection.
            admin.close()


# Support direct CI invocation without adding a persistent service.
if __name__ == "__main__":
    # Run the isolated live matrix and exit on assertion failure.
    run_mysql_migration_live_matrix()
