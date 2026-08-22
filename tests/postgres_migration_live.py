# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Apply PostgreSQL migrations to a newly created loopback PostgreSQL 16 target."""

# Import hashing for canonical receipt evidence.
import hashlib
# Import JSON for runner output and canonical receipt bytes.
import json
# Import environment copying for the isolated migration-runner process.
import os
# Import safe temporary-root cleanup.
import shutil
# Import loopback socket allocation for a fresh private PostgreSQL listener.
import socket
# Import subprocess execution for official initdb, pg_ctl, and the exact runner.
import subprocess
# Import the active isolated psycopg interpreter path.
import sys
# Import temporary-directory allocation outside the repository.
import tempfile
# Import portable paths for binaries, source, data, and logs.
from pathlib import Path
# Import high-entropy disposable passwords and target-binding keys.
import secrets

# Resolve the repository root independently of process cwd.
ROOT = Path(__file__).resolve().parents[1]
# Bind direct execution to this exact checked-out source tree.
if str(ROOT) not in sys.path:
    # Prepend only the canonical repository root before project imports.
    sys.path.insert(0, str(ROOT))

# Import psycopg only in this explicitly invoked optional live test.
import psycopg
# Import PostgreSQL-safe dynamic identifier and literal composition.
from psycopg import sql
# Import the exact mapping row factory used by the planned runtime provider.
from psycopg.rows import dict_row
# Import JSONB adaptation for real provider-schema DML.
from psycopg.types.json import Jsonb

# Import exact migration configuration and compatibility inspection.
from casino.core.postgres_migrations import DISPOSABLE_MARKER, MigrationConfig, verify_runtime_compatibility

# Resolve the exact migration runner under test.
RUNNER = ROOT / "scripts" / "postgres_migrate.py"
# Read the official portable PostgreSQL binary root from one explicit test variable.
POSTGRES_BIN = Path(os.environ.get("CASINO_POSTGRES_TEST_BIN", ""))
# Require one explicit live-test marker before creating any cluster or account.
LIVE_MARKER = "CASINO-POSTGRES-1057-LIVE"


# Publish one fixed secret-free phase marker for bounded live-run diagnosis.
def _phase(name: str) -> None:
    # Emit only a source-owned finite label and flush it immediately.
    print(f"PG1057-LIVE:{name}", file=sys.stderr, flush=True)


# Refuse accidental live execution before any filesystem or process mutation.
def _require_live_authorization() -> None:
    # Require the exact explicit test marker.
    if os.environ.get("CASINO_POSTGRES_LIVE_TEST") != LIVE_MARKER:
        # Stop without naming any configured target or path.
        raise RuntimeError("PostgreSQL disposable live test is not authorized")
    # Require official server-management binaries in the selected portable root.
    if not all((POSTGRES_BIN / name).is_file() for name in ("postgres.exe", "initdb.exe", "pg_ctl.exe")):
        # Stop without falling back to PATH or another installed server.
        raise RuntimeError("PostgreSQL disposable live-test binaries are unavailable")


# Reserve one currently free loopback TCP port for the short-lived cluster.
def _loopback_port() -> int:
    # Create an IPv4 TCP socket owned only during selection.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        # Prevent non-loopback binding.
        listener.bind(("127.0.0.1", 0))
        # Return the operating-system-selected port.
        return int(listener.getsockname()[1])


# Run one official PostgreSQL binary without publishing its path or output.
def _postgres_command(arguments: list[str]) -> None:
    # Execute the exact argument vector with shell interpretation disabled.
    completed = subprocess.run(arguments, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False)
    # Convert any binary failure into one value-free live-test result.
    if completed.returncode != 0:
        # Preserve no server output because it may include filesystem and role details.
        raise RuntimeError("PostgreSQL disposable cluster command failed")


# Run one exact migration CLI command and parse only its sanitized JSON record.
def _runner(command: str, environment: dict) -> dict:
    # Execute the repository runner with this isolated psycopg interpreter.
    completed = subprocess.run([sys.executable, str(RUNNER), command], cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120, check=False)
    # Require the runner's successful automation status.
    if completed.returncode != 0:
        # Preserve no child output beyond the runner's own process boundary.
        raise RuntimeError("PostgreSQL migration runner live command failed")
    # Parse the runner's single sanitized JSON line.
    payload = json.loads(completed.stdout)
    # Require one mapping rather than arbitrary child output.
    if type(payload) is not dict:
        # Refuse malformed automation evidence.
        raise RuntimeError("PostgreSQL migration runner live output is invalid")
    # Return the sanitized record for exact assertions.
    return payload


# Build one connector argument mapping for the fresh test target.
def _target_kwargs(port: int, role: str, password: str, database: str) -> dict:
    # Return only caller-local values that are never logged.
    return {"host": "127.0.0.1", "port": port, "user": role, "password": password, "dbname": database, "connect_timeout": 5}


# Exercise JSONB, identity, RETURNING, ON CONFLICT, constraints, and row locks.
def _exercise_postgres_semantics(connection) -> dict:
    # Open one cursor for committed provider-compatible DML.
    cursor = connection.cursor()
    # Insert one wallet needed by the ledger foreign key.
    cursor.execute("INSERT INTO casino_players (player_id, display_name, player_type, balance, created_at, updated_at, status) VALUES (%s, %s, %s, %s, %s, %s, %s)", ("player-live", "Live", "human", "100.00", "2026-08-22T00:00:00+00:00", "2026-08-22T00:00:00+00:00", "active"))
    # Insert one JSONB ledger row and return the generated identity.
    cursor.execute("INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, details_json, action_scope, action_key, action_fingerprint) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING sequence_id", ("ledger-live", "2026-08-22T00:00:01+00:00", "player-live", "roulette", "round-live", "BET", "-1.00", "100.00", "99.00", Jsonb({"source": "live"}), "roulette", "action-live", "f" * 64))
    # Require one positive generated bigint identity.
    sequence_id = int(cursor.fetchone()[0])
    # Attempt the singleton seed again through PostgreSQL-native conflict handling.
    cursor.execute("INSERT INTO casino_game_action_epoch_state (state_id, current_epoch, phase) VALUES (1, 1, 'ready') ON CONFLICT (state_id) DO NOTHING RETURNING state_id")
    # Require the existing singleton to produce no inserted row.
    conflict_skipped = cursor.fetchone() is None
    # Prepare one canonical receipt object and its application-owned byte digest.
    receipt = {"ok": True, "round_id": "round-live"}
    # Encode with the application canonical compact/sorted rule rather than jsonb::text.
    receipt_bytes = json.dumps(receipt, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode("utf-8")
    # Hash the exact canonical application JSON bytes.
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    # Insert the claim before its bound receipt.
    cursor.execute("INSERT INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, %s, %s)", (1, "roulette", "player-live", "receipt-live", "a" * 64, Jsonb({"wallet": "player-live"}), "execute"))
    # Insert the JSONB receipt bound to the immutable execute claim.
    cursor.execute("INSERT INTO casino_game_action_receipts (reset_epoch, game_id, player_id, action_key, request_fingerprint, claim_disposition, resources_json, receipt_json, receipt_sha256) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING receipt_json", (1, "roulette", "player-live", "receipt-live", "a" * 64, "execute", Jsonb({"wallet": "player-live"}), Jsonb(receipt), receipt_sha256))
    # Require psycopg to decode JSONB back to the exact application mapping.
    receipt_round_trip = cursor.fetchone()[0] == receipt
    # Build one valid first-class session payload with no bearer token.
    session = {"session_id": "session-live", "token_digest": "b" * 64, "user_id": "player-live", "status": "active", "created_at": "2026-08-22T00:00:02+00:00", "updated_at": "2026-08-22T00:00:02+00:00", "expires_at": "2026-08-23T00:00:02+00:00", "generation": 1}
    # Insert the valid JSONB session and return its durable identity.
    cursor.execute("INSERT INTO casino_sessions (session_id, token_digest, user_id, status, created_at, updated_at, expires_at, generation, session_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING session_id", (session["session_id"], session["token_digest"], session["user_id"], session["status"], session["created_at"], session["updated_at"], session["expires_at"], session["generation"], Jsonb(session)))
    # Require exact RETURNING identity.
    session_returned = cursor.fetchone() == ("session-live",)
    # Commit successful setup before deliberate constraint and lock failures.
    connection.commit()
    # Start one deliberate invalid-generation constraint check.
    try:
        # Copy the valid payload with a conflicting JSON generation.
        invalid = {**session, "session_id": "session-invalid", "token_digest": "c" * 64, "generation": 2}
        # Supply relational generation one so the JSONB payload constraint must fail.
        cursor.execute("INSERT INTO casino_sessions (session_id, token_digest, user_id, status, created_at, updated_at, expires_at, generation, session_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (invalid["session_id"], invalid["token_digest"], invalid["user_id"], invalid["status"], invalid["created_at"], invalid["updated_at"], invalid["expires_at"], 1, Jsonb(invalid)))
        # Fail if PostgreSQL accepted contradictory session evidence.
        raise RuntimeError("PostgreSQL session constraint did not fail closed")
    # Accept only PostgreSQL's exact check-constraint category.
    except psycopg.errors.CheckViolation:
        # Roll back the rejected statement without losing earlier committed evidence.
        connection.rollback()
    # Open a second connection to prove actual row-lock contention.
    contender = psycopg.connect(**connection.info.get_parameters(), autocommit=False)
    # Start protected lock exercise with guaranteed contender cleanup.
    try:
        # Lock the wallet row in the first session.
        cursor.execute("SELECT player_id FROM casino_players WHERE player_id = %s FOR UPDATE", ("player-live",))
        # Require the row to exist under lock.
        if cursor.fetchone() != ("player-live",):
            # Stop on missing row evidence.
            raise RuntimeError("PostgreSQL row-lock fixture is missing")
        # Open the competing cursor.
        competing_cursor = contender.cursor()
        # Bound only this transaction's lock wait to 100 milliseconds.
        competing_cursor.execute("SET LOCAL lock_timeout = '100ms'")
        # Start the expected lock-timeout proof.
        try:
            # Attempt to acquire the same row lock concurrently.
            competing_cursor.execute("SELECT player_id FROM casino_players WHERE player_id = %s FOR UPDATE", ("player-live",))
            # Fail if the second session acquired the held lock.
            raise RuntimeError("PostgreSQL row lock did not block a concurrent session")
        # Accept only the exact lock-unavailable category.
        except psycopg.errors.LockNotAvailable:
            # Restore the contender after its expected timeout.
            contender.rollback()
        # Release the first session row lock.
        connection.rollback()
    # Close the competing connection on every path.
    finally:
        # Release all contender-owned resources.
        contender.close()
    # Return bounded semantic evidence only.
    return {"identity_positive": sequence_id > 0, "on_conflict_skipped": conflict_skipped, "jsonb_round_trip": receipt_round_trip, "session_returning": session_returned, "constraint_failed_closed": True, "row_lock_blocked": True}


# Run the complete disposable lifecycle and print one sanitized evidence record.
def main() -> int:
    # Refuse accidental execution before allocating resources.
    _require_live_authorization()
    # Report authorization without any configured value.
    _phase("authorized")
    # Allocate a unique safe temporary cluster root.
    cluster_root = Path(tempfile.mkdtemp(prefix="casino-postgres-1057-"))
    # Resolve data and log paths strictly inside the allocated root.
    data_root = cluster_root / "data"
    # Resolve the pg_ctl log strictly inside the allocated root.
    log_path = cluster_root / "postgres.log"
    # Generate bounded lowercase target names ending in the required issue suffix.
    nonce = secrets.token_hex(4)
    # Name the fresh disposable migration role.
    role = f"casino_migrate_{nonce}_1057"
    # Name the fresh disposable database.
    database = f"casino_live_{nonce}_1057"
    # Generate one database password used only for this process.
    password = secrets.token_urlsafe(32)
    # Generate a distinct external target-binding key.
    binding_key = secrets.token_urlsafe(48)
    # Reserve one private loopback port.
    port = _loopback_port()
    # Track whether pg_ctl successfully started the disposable cluster.
    started = False
    # Track whether the disposable role and database were created.
    target_created = False
    # Initialize sanitized evidence sections.
    evidence = {}
    # Start the complete lifecycle with unconditional cleanup.
    try:
        # Initialize an official PostgreSQL cluster with local trust inside the disposable root.
        _postgres_command([str(POSTGRES_BIN / "initdb.exe"), "-D", str(data_root), "-A", "trust", "-U", "casino_admin_1057", "--encoding=UTF8", "--no-locale"])
        # Report successful private cluster initialization.
        _phase("cluster_initialized")
        # Start only a literal-loopback listener with durability shortcuts limited to disposable evidence.
        _postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-l", str(log_path), "-o", f"-p {port} -h 127.0.0.1 -F", "-w", "start"])
        # Record the active cluster for guaranteed stop.
        started = True
        # Report successful private listener startup.
        _phase("cluster_started")
        # Open the fresh cluster's default database as its synthetic admin.
        admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1057", dbname="postgres", autocommit=True, connect_timeout=5)
        # Start protected target creation and admin cleanup.
        try:
            # Open one autocommit cursor because CREATE DATABASE cannot run in a transaction.
            cursor = admin.cursor()
            # Prove neither generated role nor database existed before creation.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Refuse adoption of any pre-existing target.
            if cursor.fetchone() != (0, 0):
                # Stop before CREATE or DROP of ambiguous external state.
                raise RuntimeError("PostgreSQL disposable target already exists")
            # Create the fresh login role with safely composed identifier and literal.
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            # Create the fresh database owned by only that role.
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(database), sql.Identifier(role)))
            # Record that cleanup is authorized for these newly created identities.
            target_created = True
            # Report successful creation without publishing generated identities.
            _phase("target_created")
        # Close the admin connection after creation.
        finally:
            # Release admin-owned connector state.
            admin.close()
        # Build the exact separate migration environment for child runner commands.
        environment = dict(os.environ)
        # Select literal loopback.
        environment["CASINO_POSTGRES_MIGRATION_HOST"] = "127.0.0.1"
        # Select the private cluster port.
        environment["CASINO_POSTGRES_MIGRATION_PORT"] = str(port)
        # Select the fresh migration role.
        environment["CASINO_POSTGRES_MIGRATION_USER"] = role
        # Supply the fresh role password.
        environment["CASINO_POSTGRES_MIGRATION_PASSWORD"] = password
        # Select the fresh target database.
        environment["CASINO_POSTGRES_MIGRATION_DATABASE"] = database
        # Supply the distinct target-binding key.
        environment["CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY"] = binding_key
        # Supply the exact explicit disposable marker.
        environment["CASINO_POSTGRES_MIGRATION_DISPOSABLE"] = DISPOSABLE_MARKER
        # Prove the pre-apply dry-run sees exactly versions one through five.
        dry_run = _runner("dry-run", environment)
        # Report successful read-only plan validation.
        _phase("dry_run_validated")
        # Require exact pending version identities.
        if [row["version"] for row in dry_run.get("pending", [])] != [1, 2, 3, 4, 5]:
            # Stop before apply when the immutable plan diverges.
            raise RuntimeError("PostgreSQL disposable dry-run plan is invalid")
        # Apply all five descriptors through the real deployment-only runner.
        applied = _runner("apply", environment)
        # Report successful runner application before semantic inspection.
        _phase("migrations_applied")
        # Require exact clean version five.
        if (applied.get("current_version"), applied.get("status")) != (5, "clean"):
            # Refuse partial or dirty application evidence.
            raise RuntimeError("PostgreSQL disposable apply did not reach exact clean schema five")
        # Build the same deployment-only configuration for in-process read-only inspection.
        config = MigrationConfig("127.0.0.1", port, role, password, database, binding_key, DISPOSABLE_MARKER)
        # Open one mapping-row connection matching the planned PostgreSQL runtime provider.
        runtime_connection = psycopg.connect(**_target_kwargs(port, role, password, database), autocommit=False, row_factory=dict_row)
        # Start protected config-free readiness verification.
        try:
            # Require exact checksum-bound state through mapping rows and no migration configuration.
            state = verify_runtime_compatibility(runtime_connection)
            # End its SELECT-only transaction.
            runtime_connection.rollback()
        # Close the mapping-row runtime connection on every outcome.
        finally:
            # Release all readiness connector state.
            runtime_connection.close()
        # Report successful mapping-row runtime readiness.
        _phase("dict_row_runtime_validated")
        # Open the migrated target for real semantic evidence.
        connection = psycopg.connect(**_target_kwargs(port, role, password, database), autocommit=False)
        # Start protected semantic exercise.
        try:
            # Exercise PostgreSQL-only DML semantics and constraints.
            semantics = _exercise_postgres_semantics(connection)
            # Report successful identity/JSONB/conflict/constraint/lock semantics.
            _phase("semantics_validated")
            # Read exact table and data-type inventory.
            cursor = connection.cursor()
            # Select all Casino tables in stable order.
            cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema() AND tablename LIKE 'casino\\_%' ESCAPE '\\' ORDER BY tablename")
            # Collect the bounded table inventory.
            tables = [row[0] for row in cursor.fetchall()]
            # Select all JSONB columns from migrated tables.
            cursor.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = current_schema() AND data_type = 'jsonb' AND table_name LIKE 'casino\\_%' ESCAPE '\\' ORDER BY table_name, column_name")
            # Collect bounded JSONB identity evidence.
            jsonb_columns = [list(row) for row in cursor.fetchall()]
            # End the read-only inventory transaction.
            connection.rollback()
            # Retain only sanitized success evidence.
            evidence = {"server_major": 16, "applied_version": state.current_version, "history_versions": [row[0] for row in state.applied], "dict_row_runtime": True, "table_count": len(tables), "jsonb_columns": jsonb_columns, "semantics": semantics}
        # Close target DML connection before restart.
        finally:
            # Release all target-owned connection state.
            connection.close()
        # Stop the official cluster for restart durability proof.
        _postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-m", "fast", "-w", "stop"])
        # Record the stopped state before starting again.
        started = False
        # Report clean fast shutdown before restart.
        _phase("cluster_stopped_for_restart")
        # Restart the exact same data directory and private listener.
        _postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-l", str(log_path), "-o", f"-p {port} -h 127.0.0.1 -F", "-w", "start"])
        # Record the restarted state for cleanup.
        started = True
        # Report successful process restart.
        _phase("cluster_restarted")
        # Run the real runner's exact read-only compatibility check after restart.
        restarted = _runner("check", environment)
        # Require durable clean schema five after process restart.
        if (restarted.get("current_version"), restarted.get("status")) != (5, "clean"):
            # Refuse incomplete restart evidence.
            raise RuntimeError("PostgreSQL disposable restart verification failed")
        # Record the bounded restart result.
        evidence["restart_clean_version"] = 5
        # Report durable runner verification.
        _phase("restart_validated")
        # Open the default database to remove only newly created target identities.
        admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1057", dbname="postgres", autocommit=True, connect_timeout=5)
        # Start protected database and role teardown.
        try:
            # Open one autocommit cleanup cursor.
            cursor = admin.cursor()
            # Terminate only connections to the exact generated disposable database.
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
            # Drop only the database this process proved absent then created.
            cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            # Drop only the role this process proved absent then created.
            cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            # Prove zero database and account residue.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Require complete identity cleanup.
            if cursor.fetchone() != (0, 0):
                # Refuse a false cleanup claim.
                raise RuntimeError("PostgreSQL disposable target cleanup was incomplete")
            # Record the exact zero-residue result.
            evidence["target_residue"] = {"roles": 0, "databases": 0}
            # Prevent repeated drop attempts in the outer cleanup path.
            target_created = False
            # Report exact account/database zero residue.
            _phase("target_removed")
        # Close the admin cleanup connection.
        finally:
            # Release admin connector state.
            admin.close()
    # Clean database, role, cluster process, and files on every success or failure.
    finally:
        # Attempt identity cleanup only when this process created the target and the cluster is active.
        if target_created and started:
            # Start best-effort cleanup without masking the primary outcome.
            try:
                # Open the synthetic admin connection only to this private listener.
                admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1057", dbname="postgres", autocommit=True, connect_timeout=3)
                # Open one cleanup cursor.
                cursor = admin.cursor()
                # Terminate only exact target connections.
                cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
                # Drop only the process-created database if it still exists.
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
                # Drop only the process-created role if it still exists.
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
                # Close the cleanup connection.
                admin.close()
            # Continue to process and filesystem cleanup after any connector failure.
            except Exception:
                # Preserve no cleanup exception detail.
                pass
        # Stop the private cluster when it is still active.
        if started:
            # Run best-effort immediate stop with captured output.
            subprocess.run([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-m", "immediate", "-w", "stop"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False)
            # Report completion of the bounded stop attempt.
            _phase("cluster_stop_attempted")
        # Verify the cleanup target remains the allocated temporary issue root.
        safe_root = cluster_root.parent == Path(tempfile.gettempdir()) and cluster_root.name.startswith("casino-postgres-1057-")
        # Remove only the verified disposable cluster tree.
        if safe_root:
            # Delete data and logs after process stop.
            shutil.rmtree(cluster_root, ignore_errors=True)
            # Report completion of the bounded filesystem removal attempt.
            _phase("cluster_remove_attempted")
    # Require filesystem cleanup after the lifecycle.
    if cluster_root.exists():
        # Refuse a false cleanup result.
        raise RuntimeError("PostgreSQL disposable cluster cleanup was incomplete")
    # Record the exact zero-residue filesystem result.
    evidence["cluster_root_removed"] = True
    # Print one sanitized sorted evidence record.
    print(json.dumps(evidence, sort_keys=True))
    # Return success after target and cluster cleanup.
    return 0


# Execute the live lifecycle only when explicitly invoked.
if __name__ == "__main__":
    # Exit with the stable live-test result.
    raise SystemExit(main())
