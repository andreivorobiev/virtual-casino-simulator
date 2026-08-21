# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Disposable MySQL 8.4 migration, lifecycle, grants, restart, and lock evidence."""

# Import UTC timing for short-lived synthetic recovery proofs.
from datetime import datetime, timedelta, timezone
# Import process and thread isolation for advisory-lock, transaction, and session evidence.
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
# Import detached state snapshots for the real different-player settlement race.
import copy
# Import SHA-256 for canonical receipt-byte verification.
import hashlib
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
# Import bounded in-process concurrency for real MVCC claim/receipt races.
import threading
# Import a short deterministic assertion window for the blocked resolver.
import time

# Import the actual Admin bootstrap, player projection, migration policy, and storage provider.
from casino.core import auth, mysql_migrations, players, storage
# Import immutable game-action values for real disposable-provider lifecycle proof.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionResolution, GameActionResources
# Import the canonical bearer digest for schema-five backfill evidence.
from casino.core.storage.sessions import session_token_digest
# Import the shared per-player settlement helper for real MySQL concurrency evidence. (GAMECORE-009)
from casino.core.simple_game import SimpleWagerGame
# Import the canonical game-money gateway bound directly to the disposable provider.
from casino.core.settlement import GameSettlementGateway
# Import the stable conflict boundary for resolver-first refusal.
from casino.errors import ConflictError
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


# Attempt one held apply from a separate process without inheriting connection state.
def _locked_apply_worker(database: str, proof_path: str) -> str:
    # Build the exact process-local migration config.
    config = _migration_config(database)
    # Open an independent process-owned migrator connection.
    connection = _connector().connect(**config.kwargs())
    # Always close the process-owned connection.
    try:
        # Start protected apply so the fixed lock result can be returned.
        try:
            # Use a one-second timeout value that must remain unused by held policy.
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


# Seed one reviewed catalog prefix solely inside the disposable test fixture.
def _seed_catalog_prefix(connection, migrations, through_version: int) -> None:
    # Disable autocommit for migration metadata history/state DML.
    connection.autocommit = False
    # Establish the exact metadata boundary through the existing repository seam.
    mysql_migrations._initialize_metadata(connection, migrations)
    # Open one cursor for immutable fixture migration statements.
    cursor = connection.cursor()
    # Apply only the selected contiguous prefix in reviewed order.
    for migration in migrations[:through_version]:
        # Re-read the clean source prefix before each fixture transition.
        source_state = mysql_migrations.inspect_schema(connection, migrations)
        # Persist the exact applying marker before application DDL.
        mysql_migrations._mark_applying(connection, source_state, migration)
        # Execute every checksum-verified statement in the selected migration.
        for statement in migration.statements:
            # Apply one exact driver statement without SQL splitting.
            cursor.execute(statement)
        # Persist exact immutable history only after all statements succeed.
        mysql_migrations._mark_complete(connection, migration, migrations)


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


# Exercise immutable lifecycle claims, receipt binding, and durable persistence.
def _exercise_game_action_receipts(connection):
    # Open one runtime-identity cursor against the fully migrated disposable target.
    cursor = connection.cursor()
    # Read the applied table engine through public server metadata.
    cursor.execute("SELECT ENGINE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'casino_game_action_receipts'")
    # Require the exact transactional storage engine after live application.
    assert str(cursor.fetchone()[0]).lower() == "innodb"
    # Read exact schema-four receipt column types and capacities without application values.
    cursor.execute("SELECT COLUMN_NAME, COLUMN_TYPE, COLLATION_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'casino_game_action_receipts' ORDER BY ORDINAL_POSITION")
    # Normalize the fixed structural rows for exact assertions.
    columns = {str(row[0]): (str(row[1]).lower(), None if row[2] is None else str(row[2]).lower()) for row in cursor.fetchall()}
    # Require the complete bounded storage shape.
    assert columns == {
        "reset_epoch": ("bigint unsigned", None),
        "game_id": ("varchar(191)", "utf8mb4_bin"),
        "player_id": ("varchar(191)", "utf8mb4_bin"),
        "action_key": ("varchar(191)", "utf8mb4_bin"),
        "request_fingerprint": ("char(64)", "ascii_bin"),
        "claim_disposition": ("varchar(16)", "ascii_bin"),
        "resources_json": ("text", "utf8mb4_bin"),
        "receipt_json": ("mediumtext", "utf8mb4_bin"),
        "receipt_sha256": ("char(64)", "ascii_bin"),
    }
    # Read exact primary-key ordering for one action-scope identity.
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'casino_game_action_receipts' AND INDEX_NAME = 'PRIMARY' ORDER BY SEQ_IN_INDEX")
    # Require the exact game/player/action scope boundary.
    assert [str(row[0]) for row in cursor.fetchall()] == ["reset_epoch", "game_id", "player_id", "action_key"]
    # Read exact schema-four claim columns and collations.
    cursor.execute("SELECT COLUMN_NAME, COLUMN_TYPE, COLLATION_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'casino_game_action_claims' ORDER BY ORDINAL_POSITION")
    # Normalize claim structural rows for exact assertions.
    claim_columns = {str(row[0]): (str(row[1]).lower(), None if row[2] is None else str(row[2]).lower()) for row in cursor.fetchall()}
    # Require the complete immutable claim shape.
    assert claim_columns == {
        "reset_epoch": ("bigint unsigned", None),
        "game_id": ("varchar(191)", "utf8mb4_bin"),
        "player_id": ("varchar(191)", "utf8mb4_bin"),
        "action_key": ("varchar(191)", "utf8mb4_bin"),
        "request_fingerprint": ("char(64)", "ascii_bin"),
        "resources_json": ("text", "utf8mb4_bin"),
        "disposition": ("varchar(16)", "ascii_bin"),
    }
    # Read the reset namespace singleton through its exact durable schema.
    cursor.execute("SELECT COLUMN_NAME, COLUMN_TYPE, COLLATION_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'casino_game_action_epoch_state' ORDER BY ORDINAL_POSITION")
    # Normalize the epoch control schema without exposing runtime values.
    epoch_columns = {str(row[0]): (str(row[1]).lower(), None if row[2] is None else str(row[2]).lower()) for row in cursor.fetchall()}
    # Require the bounded singleton, positive epoch, and binary phase representation.
    assert epoch_columns == {
        "state_id": ("tinyint unsigned", None),
        "current_epoch": ("bigint unsigned", None),
        "phase": ("varchar(16)", "ascii_bin"),
    }
    # Read the only seeded namespace control row.
    cursor.execute("SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state")
    # Require the initial namespace to be available at epoch one.
    assert tuple(cursor.fetchone()) == (1, 1, "ready")
    # Build one canonical bounded resource representation shared by paid and zero-cost receipts.
    resources = {"state_keys": ["roulette.round"], "wallet_ids": ["player_204"]}
    # Encode resource bytes in deterministic compact canonical form.
    resources_json = json.dumps(resources, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # Preserve representative paid and zero-cost receipt plans.
    plans = (
        # A paid action debits one declared wallet using signed integer cents.
        ("paid_204", "a" * 64, [{"amount_cents": -100, "reason": "stake", "wallet_id": "player_204"}], 1000, 900),
        # A zero-cost action has no synthetic money movement.
        ("zero_204", "b" * 64, [], 900, 900),
    )
    # Retain exact inserted rows for post-duplicate persistence equality.
    inserted = []
    # Insert each complete receipt representation once.
    for action_key, fingerprint, movements, before_cents, after_cents in plans:
        # Build the exact game-action identity.
        identity = {"action_key": action_key, "game_id": "roulette", "player_id": "player_204", "request_fingerprint": fingerprint}
        # Build one complete provider-neutral receipt graph.
        receipt = {
            "identity": identity,
            "plan": {"movements": movements, "outcome": {"accepted": True}, "state_updates": []},
            "resources": resources,
            "snapshot_after": {"state_values": [["roulette.round", {"phase": "settled"}]], "wallet_balances": [["player_204", after_cents]]},
            "snapshot_before": {"state_values": [["roulette.round", {"phase": "ready"}]], "wallet_balances": [["player_204", before_cents]]},
        }
        # Encode the exact canonical receipt bytes.
        receipt_json = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        # Hash the exact stored receipt representation independently of request semantics.
        receipt_sha256 = hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
        # Insert the immutable execute claim before its child receipt.
        cursor.execute(
            "INSERT INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, %s, 'execute')",
            (1, "roulette", "player_204", action_key, fingerprint, resources_json),
        )
        # Insert one exact-scope receipt bound to the execute claim.
        cursor.execute(
            "INSERT INTO casino_game_action_receipts (reset_epoch, game_id, player_id, action_key, request_fingerprint, claim_disposition, resources_json, receipt_json, receipt_sha256) VALUES (%s, %s, %s, %s, %s, 'execute', %s, %s, %s)",
            (1, "roulette", "player_204", action_key, fingerprint, resources_json, receipt_json, receipt_sha256),
        )
        # Retain the exact row expected after the duplicate attempt.
        inserted.append(("1", "roulette", "player_204", action_key, fingerprint, "execute", resources_json, receipt_json, receipt_sha256))
    # Durably commit both representative receipts before the duplicate attempt.
    connection.commit()
    # Require same-scope reuse with another fingerprint to fail on the unique boundary.
    try:
        # Attempt to reuse the paid action scope with different request semantics.
        cursor.execute(
            "INSERT INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, %s, 'uncommitted')",
            (1, "roulette", "player_204", "paid_204", "c" * 64, resources_json),
        )
    # Accept only one duplicate-key server refusal.
    except _connector().Error as exc:
        # Require exact-scope uniqueness rather than another schema failure.
        assert int(getattr(exc, "errno", 0) or 0) == 1062
        # Clear only the rejected statement transaction state.
        connection.rollback()
    # Fail if another request duplicated the exact scope.
    else:
        # Surface one fixed category without receipt content.
        raise AssertionError("game-action receipt scope reuse was accepted")
    # Read exact durable rows after the duplicate-key refusal.
    cursor.execute("SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, claim_disposition, resources_json, receipt_json, receipt_sha256 FROM casino_game_action_receipts ORDER BY action_key")
    # Normalize driver-returned text without parsing away exact bytes.
    persisted = [tuple(str(value) for value in row) for row in cursor.fetchall()]
    # Require both exact inserted rows and canonical receipt bytes/hash to persist.
    assert persisted == sorted(inserted, key=lambda row: row[3])
    # Insert one terminal resolver-first tombstone with no receipt.
    cursor.execute(
        "INSERT INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, %s, 'uncommitted')",
        (1, "roulette", "player_204", "uncommitted_204", "d" * 64, resources_json),
    )
    # Commit the immutable tombstone.
    connection.commit()
    # Refuse a receipt behind a non-execute claim through exact child constraints.
    try:
        # Attempt to attach execute-only receipt material to the tombstone scope.
        cursor.execute(
            "INSERT INTO casino_game_action_receipts (reset_epoch, game_id, player_id, action_key, request_fingerprint, claim_disposition, resources_json, receipt_json, receipt_sha256) VALUES (%s, %s, %s, %s, %s, 'execute', %s, %s, %s)",
            (1, "roulette", "player_204", "uncommitted_204", "d" * 64, resources_json, inserted[0][7], inserted[0][8]),
        )
    # Accept only check or foreign-key constraint refusal.
    except _connector().Error as exc:
        # Require server-enforced lifecycle binding rather than an unrelated syntax failure.
        assert int(getattr(exc, "errno", 0) or 0) in {3819, 1452}
        # Clear only the rejected child insertion.
        connection.rollback()
    # Fail if an uncommitted claim accepted a receipt.
    else:
        # Surface one fixed category.
        raise AssertionError("uncommitted game-action claim accepted a receipt")


# Exercise the production MySQL lifecycle provider against the disposable schema-five service.
def _exercise_game_action_provider() -> None:
    # Bind a new provider only to the already guarded disposable runtime identity.
    provider = storage.MySQLStorageProvider(
        storage.MySQLConfig(
            # Reuse the exact loopback host approved by the outer guard.
            host=os.environ["CASINO_MYSQL_HOST"],
            # Reuse the exact matched disposable service port.
            port=int(os.environ["CASINO_MYSQL_PORT"]),
            # Use only the least-privilege runtime identity.
            user=os.environ["CASINO_MYSQL_USER"],
            # Pass the synthetic runtime password without formatting or logging it.
            password=os.environ["CASINO_MYSQL_PASSWORD"],
            # Bind the provider to the disposable base database.
            database=os.environ["CASINO_MYSQL_DATABASE"],
        ),
        # Guarantee two simultaneous leases for the executor-versus-resolver race.
        pool_config=storage.MySQLPoolConfig(capacity=2, checkout_wait_ms=1000, connect_timeout_seconds=3),
    )
    try:
        # Build twelve complete sessions spanning one shared and six distinct identities.
        session_rows = [
            # Preserve one independent bearer and CSRF proof per concurrent login.
            {"session_id": f"live-session-{index}", "user_id": "live-shared" if index < 6 else f"live-user-{index}", "token": f"live-token-{index}", "csrf_token": f"live-csrf-{index}".ljust(32, "x"), "generation": 1, "status": "active", "created_at": f"2026-01-01T00:00:{index:02d}.000Z", "updated_at": f"2026-01-01T00:00:{index:02d}.000Z", "expires_at": "2027-01-01T00:00:00.000Z", "client": "mysql-live", "auth_method": "local"}
            # Materialize the bounded live cohort.
            for index in range(12)
        ]

        # Create and resolve one exact native-table session.
        def create_live_session(row):
            # Commit one independent first-class row with caps above this cohort.
            created = provider.create_session(row, 12, 24)
            # Resolve through the unique bearer digest index after commit.
            resolved = provider.get_session_by_token(created["token"])
            # Return only exact identity and CSRF proof.
            return resolved["session_id"], resolved["csrf_token"]

        # Execute the same-user and different-user login cohort concurrently.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Surface every connector or integrity failure in the parent thread.
            created_sessions = list(executor.map(create_live_session, session_rows))
        # Require all twelve identities and CSRF proofs without lost rows.
        assert {item[0] for item in created_sessions} == {row["session_id"] for row in session_rows} and {item[1] for item in created_sessions} == {row["csrf_token"] for row in session_rows}
        # Require durable list projections to omit every plaintext bearer.
        assert len(provider.list_sessions()) == 12 and all("token" not in row for row in provider.list_sessions())
        # Rotate one native token and CSRF pair through exact generation one.
        rotated_session = provider.rotate_session("live-session-0", "live-token-0", 1, "live-token-rotated", "live-csrf-rotated".ljust(32, "x"), "2026-01-01T01:00:00.000Z")
        # Require old-token invalidation and one generation advance.
        assert provider.get_session_by_token("live-token-0") is None and rotated_session["generation"] == 2 and rotated_session["token"] == "live-token-rotated"

        # Revoke one exact native-table bearer during the parallel logout cohort.
        def revoke_live_session(row):
            # Select the rotated bearer only for the first session.
            token = "live-token-rotated" if row["session_id"] == "live-session-0" else row["token"]
            # Revoke the selected active row exactly once.
            return provider.revoke_session_by_token(token, "2026-01-01T02:00:00.000Z")

        # Execute every logout concurrently through the same bounded pool.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Materialize every exact changed count.
            revoked_sessions = list(executor.map(revoke_live_session, session_rows))
        # Require zero lost revocations or unexpected misses.
        assert revoked_sessions == [1] * len(session_rows)
        # Sweep all revoked rows and prove the native table becomes empty.
        assert provider.expire_sessions(datetime(2026, 1, 2, tzinfo=timezone.utc), 24) == 12 and provider.list_sessions() == []
        # Create one deterministic synthetic wallet through the public provider seam.
        player = provider.ensure_player(
            {
                # Use a bounded test-only wallet identity.
                "player_id": "lifecycle_204",
                # Keep the display label non-secret and synthetic.
                "display_name": "Lifecycle 204",
                # Preserve the ordinary human wallet type.
                "type": "human",
                # Seed exact fake-money balance for debit and payout proof.
                "balance": 10.0,
                # Use one fixed compatible timestamp for deterministic fixture semantics.
                "created_at": "2026-01-01T00:00:00+00:00",
                # Keep the initial update timestamp identical.
                "updated_at": "2026-01-01T00:00:00+00:00",
                # Provision the disposable wallet as active.
                "status": "active",
            }
        )
        # Require the exact inserted wallet identity and balance.
        assert player["player_id"] == "lifecycle_204" and player["balance"] == 10.0
        # Name two separate wallets whose upper game locks must not serialize MySQL row transactions.
        striped_players = ("striped_a_204", "striped_b_204")
        # Create both synthetic wallets through the production provider seam.
        for striped_player in striped_players:
            # Seed one exact active wallet for the rendezvous action.
            provider.ensure_player({"player_id": striped_player, "display_name": striped_player, "type": "human", "balance": 10.0, "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00", "status": "active"})
        # Retain route-free per-player state while real wallet writes use MySQL.
        striped_documents = {}
        # Protect only the disposable state fixture, never provider settlement.
        striped_state_lock = threading.Lock()
        # Require both player resolvers to rendezvous after their independent wager commits.
        striped_resolver_barrier = threading.Barrier(2, timeout=5)
        # Retain successful results by player identity.
        striped_results = {}
        # Retain any concurrency failure for the parent-thread assertion.
        striped_errors = []

        # Commit one provider-atomic debit with the canonical action identity.
        def striped_debit_once(**context):
            # Translate the gateway's positive debit magnitude into a negative provider movement.
            return provider.transact_ledger_once(context["player_id"], -abs(context["amount"]), context["transaction_type"], context["action_key"], context["game"], context["round_id"], context["details"])

        # Commit one provider-atomic credit with the canonical action identity.
        def striped_credit_once(**context):
            # Preserve the gateway's positive credit magnitude at the provider boundary.
            return provider.transact_ledger_once(context["player_id"], abs(context["amount"]), context["transaction_type"], context["action_key"], context["game"], context["round_id"], context["details"])

        # Load one detached current document for the requested synthetic player.
        def striped_state_loader(player_id):
            # Serialize only fixture dictionary access.
            with striped_state_lock:
                # Return current state or one fresh shared-helper document.
                return copy.deepcopy(striped_documents.get(player_id, {"game": "mysql_lock_striping", "recent_rounds": []}))

        # Publish one callback against fixture-current state authority.
        def striped_state_updater(player_id, mutator):
            # Serialize only the in-memory document callback.
            with striped_state_lock:
                # Apply the production mutator to a detached current document.
                updated = mutator(copy.deepcopy(striped_documents.get(player_id, {"game": "mysql_lock_striping", "recent_rounds": []})))
                # Retain a detached committed document.
                striped_documents[player_id] = copy.deepcopy(updated)
                # Return detached provider authority.
                return copy.deepcopy(updated)

        # Return the exact real MySQL wallet through the point-read seam.
        def striped_get_player(player_id):
            # Use an empty fallback that can never satisfy either seeded identity.
            return provider.get_player(player_id, lambda: {"players": []})

        # Validate one bounded deterministic winning request.
        def striped_validate_bet(request):
            # Normalize the fixture wager to one token.
            stake = int(request.get("stake", 0))
            # Reject any unexpected fixture mutation before provider access.
            if stake != 1:
                # Surface one stable fixture failure.
                raise AssertionError("striped MySQL fixture stake changed")
            # Return canonical wager, total, and request fingerprint.
            return {"stake": stake}, float(stake), "stake:1"

        # Draw one deterministic winning face.
        def striped_entropy(randbelow):
            # Exercise the injected bound while returning a fixed face.
            return {"face": randbelow(1)}

        # Rendezvous two different players inside the old process-wide critical section location.
        def striped_resolve(wager, entropy):
            # Fail closed if an upper global lock prevents both MySQL-capable actions from arriving.
            striped_resolver_barrier.wait()
            # Return one exact five-token settlement for the one-token wager.
            return {"outcome": "win", "total_return": wager["stake"] * 5, "detail": {"face": entropy["face"]}}

        # Bind the canonical money adapter directly to the disposable least-privilege provider.
        striped_gateway = GameSettlementGateway("mysql_lock_striping", debit_once=striped_debit_once, credit_once=striped_credit_once, find_action=provider.find_ledger_action)
        # Build one shared helper whose upper lock is the behavior under test.
        striped_game = SimpleWagerGame(game_id="mysql_lock_striping", wager_transaction_type="MYSQL_STRIPED_WAGER_DEBIT", settlement_transaction_type="MYSQL_STRIPED_SETTLEMENT_CREDIT", entropy=striped_entropy, resolve=striped_resolve, validate_bet=striped_validate_bet, entropy_source=lambda _bound: 0, ledger_gateway=striped_gateway, state_loader=striped_state_loader, state_updater=striped_state_updater, get_player=striped_get_player)

        # Execute one complete different-player MySQL settlement.
        def execute_striped_player(player_id):
            try:
                # Run wager, rendezvous, payout, and state publication under one player stripe.
                striped_results[player_id] = striped_game.play(player_id, {"request_id": f"request-{player_id}", "stake": 1})
            # Retain any failure without exposing connector configuration.
            except BaseException as exc:
                # Preserve only the in-memory exception object.
                striped_errors.append(exc)

        # Construct both workers before starting either action.
        striped_threads = tuple(threading.Thread(target=execute_striped_player, args=(player_id,)) for player_id in striped_players)
        # Start both distinct wallet actions.
        for striped_thread in striped_threads:
            # Allow MySQL row-level concurrency beneath distinct player stripes.
            striped_thread.start()
        # Join both bounded actions after settlement and state publication.
        for striped_thread in striped_threads:
            # Wait for each action to finish without opening another connection.
            striped_thread.join(10)
        # Require the rendezvous, both terminal results, and no hidden worker failure.
        assert all(not striped_thread.is_alive() for striped_thread in striped_threads) and striped_errors == [] and set(striped_results) == set(striped_players)
        # Prove each real wallet committed exactly one debit and one credit independently.
        for striped_player in striped_players:
            # Read final point authority from MySQL.
            striped_wallet = provider.get_player(striped_player, lambda: {"players": []})
            # Read only this player's two new immutable rows.
            striped_rows = provider.read_ledger_recent(player_id=striped_player, limit=10)
            # Require the exact final balance and movement order without duplicate writes.
            assert striped_wallet["balance"] == 14.0 and [row["amount"] for row in striped_rows] == [-1.0, 5.0]
        # Declare one wallet and one route-free state resource.
        resources = GameActionResources(wallet_ids=("lifecycle_204",), state_keys=("game_action:lifecycle_204",))
        # Bind canonical action semantics to the declared resources.
        identity = GameActionIdentity.create(game_id="slots", player_id="lifecycle_204", action_key="execute_204", resources=resources, request={"stake_cents": 100})
        # Count the exact live planner invocation.
        planner_calls = []

        # Return one deterministic debit, payout, and state plan.
        def planner(snapshot):
            # Retain only the immutable planner input for at-most-once proof.
            planner_calls.append(snapshot)
            # Build the complete paid action plan.
            return GameActionPlan.create(
                # Return one bounded synthetic result object.
                outcome={"round_id": "round_204"},
                # Preserve exact movement order in integer cents.
                movements=(GameActionMovement(wallet_id="lifecycle_204", amount_cents=-100, reason="stake"), GameActionMovement(wallet_id="lifecycle_204", amount_cents=250, reason="payout")),
                # Publish one exact route-free state document.
                state_updates={"game_action:lifecycle_204": {"round_id": "round_204", "status": "settled"}},
            )

        # Execute the real schema-four relational transaction once.
        receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
        # Require one original action and one planner call.
        assert replayed is False and len(planner_calls) == 1
        # Replay without invoking replacement planner or RNG work.
        replay_receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("replay invoked planner")))
        # Require exact immutable receipt replay.
        assert replayed is True and replay_receipt == receipt
        # Resolve the execute winner to the same complete receipt.
        assert provider.resolve_game_action(identity=identity, resources=resources) == GameActionResolution(status="committed", receipt=receipt)
        # Read the exact committed wallet through the ordinary provider surface.
        wallets = {row["player_id"]: row for row in provider.load_players(lambda: {"players": []})["players"]}
        # Require debit and payout to converge on the expected balance.
        assert wallets["lifecycle_204"]["balance"] == 11.5
        # Read the same wallet through the production primary-key point seam.
        point_wallet = provider.get_player("lifecycle_204", lambda: {"players": []})
        # Require point and complete-document projections to remain byte-equivalent.
        assert point_wallet == wallets["lifecycle_204"]
        # Read the route-free state document committed with the receipt.
        assert provider.read_document("game_action:lifecycle_204", {}) == {"round_id": "round_204", "status": "settled"}
        # Read exact append-only movement rows for the synthetic wallet.
        ledger_rows = provider.read_ledger_recent(player_id="lifecycle_204", limit=10)
        # Require one row per movement and no duplicate replay projection.
        assert len(ledger_rows) == 2 and [row["amount"] for row in ledger_rows] == [-1.0, 2.5]
        # Aggregate the newest bounded game window through production MySQL SQL.
        economics = provider.ledger_economics(window=100, game="slots", recent=10)
        # Require exact totals, event count, type buckets, and chronological evidence identities.
        assert economics["games"] == [{"game": "slots", "wagered": 1.0, "returned": 2.5, "events": 2}] and len(economics["by_transaction_type"]) == 2 and [row["ledger_id"] for row in economics["recent"]] == [row["ledger_id"] for row in ledger_rows]
        # Bind a separate action for a real REPEATABLE READ claim/receipt race.
        race_identity = GameActionIdentity.create(game_id="slots", player_id="lifecycle_204", action_key="race_204", resources=resources, request={"stake_cents": 0})
        # Signal when the executor owns its uncommitted execute claim inside the planner.
        planner_entered = threading.Event()
        # Hold planner completion until the resolver is blocked on the same claim.
        release_planner = threading.Event()
        # Retain thread results without exposing connector details.
        race_results = {}
        # Retain unexpected thread failures for parent-thread assertion.
        race_errors = []

        # Execute one state-only action while retaining the claim row lock.
        def execute_race():
            try:
                # Define the held state-only planner.
                def held_planner(_snapshot):
                    # Signal only after the executor has inserted its claim and captured resources.
                    planner_entered.set()
                    # Wait a bounded interval for the resolver contender to begin.
                    if not release_planner.wait(5):
                        # Surface a deterministic local coordination failure.
                        raise AssertionError("resolver race did not release planner")
                    # Return one zero-cost state result.
                    return GameActionPlan.create(outcome={"round_id": "race_204"}, state_updates={"game_action:lifecycle_204": {"round_id": "race_204", "status": "settled"}})
                # Commit through the production transaction boundary.
                race_results["execute"] = provider.execute_game_action_once(identity=race_identity, resources=resources, planner=held_planner)
            # Retain any failure for a secret-free assertion in the parent thread.
            except BaseException as exc:
                # Store only the exception object in test memory.
                race_errors.append(exc)

        # Resolve the exact action while the execute claim is still uncommitted.
        def resolve_race():
            try:
                # Wait through the bounded claim lock and recover the committed receipt.
                race_results["resolve"] = provider.resolve_game_action(identity=race_identity, resources=resources)
            # Retain any failure for a secret-free assertion in the parent thread.
            except BaseException as exc:
                # Store only the exception object in test memory.
                race_errors.append(exc)

        # Launch the executor on the first pooled connection.
        executor_thread = threading.Thread(target=execute_race)
        # Start the exact action transaction.
        executor_thread.start()
        # Require the executor to reach its held planner under claim ownership.
        assert planner_entered.wait(5)
        # Launch the resolver on the second pooled connection.
        resolver_thread = threading.Thread(target=resolve_race)
        # Start the competing resolution transaction.
        resolver_thread.start()
        # Allow the resolver to establish its pre-commit snapshot and block on the claim.
        time.sleep(0.2)
        # Require the resolver to remain in flight before executor commit.
        assert resolver_thread.is_alive()
        # Allow the executor to commit claim, state, and receipt atomically.
        release_planner.set()
        # Join both bounded lifecycle calls.
        executor_thread.join(5)
        # Join the resolver after the claim lock releases.
        resolver_thread.join(5)
        # Require both lifecycle calls to terminate without hidden failure.
        assert not executor_thread.is_alive() and not resolver_thread.is_alive() and race_errors == []
        # Read the executor's exact newly committed receipt.
        race_receipt, race_replayed = race_results["execute"]
        # Require original execution rather than replay.
        assert race_replayed is False
        # Require the resolver's locking receipt read to observe the just-committed row.
        assert race_results["resolve"] == GameActionResolution(status="committed", receipt=race_receipt)
        # Bind a separate resolver-first action to the same declared resources.
        uncommitted_identity = GameActionIdentity.create(game_id="slots", player_id="lifecycle_204", action_key="uncommitted_204", resources=resources, request={"stake_cents": 200})
        # Commit the immutable no-result claim before execution.
        assert provider.resolve_game_action(identity=uncommitted_identity, resources=resources) == GameActionResolution(status="uncommitted")
        try:
            # Attempt late execution through the production schema-four provider.
            provider.execute_game_action_once(identity=uncommitted_identity, resources=resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("late executor invoked planner")))
        # Accept only the fixed resolver-first conflict boundary.
        except ConflictError as exc:
            # Require the exact value-free application error.
            assert str(exc) == "Game action was durably resolved as uncommitted"
        # Fail if the immutable uncommitted winner permitted late execution.
        else:
            # Surface one fixed proof failure.
            raise AssertionError("resolver-first lifecycle claim allowed late execution")
        # Retain a planner counter for the reset-unavailable executor proof.
        resetting_planner_calls = []
        # Hold the target-scoped reset through mutable deletion and same-session bootstrap.
        with provider.reset_transaction() as reset_provider:
            # Prove lifecycle execution cannot plan while the durable namespace is resetting.
            try:
                # Attempt the prior exact action key while reset owns the target.
                reset_provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda snapshot: resetting_planner_calls.append(snapshot))
            # Accept only the fixed unavailable lifecycle boundary.
            except ConflictError as exc:
                # Require value-free fail-closed semantics and zero planner calls.
                assert str(exc) == "Game action reset is in progress" and resetting_planner_calls == []
            # Fail if a resetting namespace admitted an action.
            else:
                # Surface one fixed availability failure.
                raise AssertionError("game action executed while reset was in progress")
            # Resolve the same action without allocating a claim or invoking a planner.
            assert reset_provider.resolve_game_action(identity=identity, resources=resources) == GameActionResolution(status="pending")
            # Bootstrap one fresh wallet through the retained capacity-one-compatible session.
            reset_player = reset_provider.ensure_player(
                {
                    # Reuse the same synthetic wallet identity in the new mutable namespace.
                    "player_id": "lifecycle_204",
                    # Preserve the non-secret fixture label.
                    "display_name": "Lifecycle 204",
                    # Preserve ordinary human wallet semantics.
                    "type": "human",
                    # Seed the same fake-money balance for fresh-action proof.
                    "balance": 10.0,
                    # Retain deterministic compatible timestamps.
                    "created_at": "2026-01-01T00:00:00+00:00",
                    # Keep the update timestamp identical.
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    # Restore an active wallet exactly as Admin reset bootstrap does.
                    "status": "active",
                }
            )
            # Require same-session bootstrap to publish the fresh wallet.
            assert reset_player["player_id"] == "lifecycle_204" and reset_player["balance"] == 10.0
        # Count one planner invocation under the now-ready fresh epoch.
        fresh_planner_calls = []

        # Return a compatible fresh result under the reused external action key.
        def fresh_planner(snapshot):
            # Retain the exact fresh-epoch snapshot for one-call proof.
            fresh_planner_calls.append(snapshot)
            # Create a zero-cost result so only namespace isolation is under test.
            return GameActionPlan.create(outcome={"round_id": "fresh_204"}, state_updates={"game_action:lifecycle_204": {"round_id": "fresh_204", "status": "settled"}})

        # Reuse the exact action key and semantics after reset without replaying epoch one.
        fresh_receipt, fresh_replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=fresh_planner)
        # Require one genuinely new action and one exact planner call.
        assert fresh_replayed is False and len(fresh_planner_calls) == 1 and fresh_receipt.plan.outcome == GameActionPlan.create(outcome={"round_id": "fresh_204"}).outcome
        # Open one ordinary runtime lease for retained-history and namespace assertions.
        evidence_connection = provider.connect()
        # Always return the evidence lease to the bounded pool.
        try:
            # Read only aggregate immutable history and the public singleton control.
            evidence_cursor = evidence_connection.cursor(dictionary=True)
            # Count matching exact action keys across both retained epochs.
            evidence_cursor.execute("SELECT reset_epoch, COUNT(*) AS claim_count FROM casino_game_action_claims WHERE game_id = %s AND player_id = %s AND action_key = %s GROUP BY reset_epoch ORDER BY reset_epoch", ("slots", "lifecycle_204", "execute_204"))
            # Require the old claim to remain and the same key to exist independently in epoch two.
            assert evidence_cursor.fetchall() == [{"reset_epoch": 1, "claim_count": 1}, {"reset_epoch": 2, "claim_count": 1}]
            # Read the exact ready namespace after successful reset finalization.
            evidence_cursor.execute("SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state")
            # Require one monotonic transition and no public receipt mutation.
            assert evidence_cursor.fetchone() == {"state_id": 1, "current_epoch": 2, "phase": "ready"}
            # End the connector-owned read transaction before returning the lease.
            evidence_connection.rollback()
        # Return the evidence lease on every assertion outcome.
        finally:
            # Preserve the pool's ordinary connection lifecycle.
            evidence_connection.close()
        # Bind one distinct epoch-two action for action-versus-reset row-lock ordering.
        ordering_identity = GameActionIdentity.create(game_id="slots", player_id="lifecycle_204", action_key="reset-ordering_204", resources=resources, request={"stake_cents": 0})
        # Signal after the action owns a shared epoch lock inside its planner.
        ordering_planner_entered = threading.Event()
        # Hold the action transaction until the reset contender is demonstrably waiting.
        release_ordering_planner = threading.Event()
        # Signal only when reset phase one finishes and its caller body begins.
        reset_body_entered = threading.Event()
        # Retain thread-safe bounded outcomes for parent-thread assertions.
        ordering_results = {}
        # Retain unexpected thread failures without printing connector details.
        ordering_errors = []

        # Execute one action while retaining shared ownership of epoch two.
        def execute_before_reset():
            try:
                # Define the held zero-cost action planner.
                def ordering_planner(_snapshot):
                    # Prove the action has passed claim and resource locking.
                    ordering_planner_entered.set()
                    # Wait only for the bounded reset-ordering assertion.
                    if not release_ordering_planner.wait(5):
                        # Surface deterministic local coordination failure.
                        raise AssertionError("reset ordering did not release planner")
                    # Return one exact state-only result.
                    return GameActionPlan.create(outcome={"round_id": "reset-ordering_204"}, state_updates={"game_action:lifecycle_204": {"round_id": "reset-ordering_204", "status": "settled"}})
                # Commit the action under the production schema-four transaction.
                ordering_results["execute"] = provider.execute_game_action_once(identity=ordering_identity, resources=resources, planner=ordering_planner)
            # Retain any failure for exact parent-thread handling.
            except BaseException as exc:
                # Store only the in-memory exception object.
                ordering_errors.append(exc)

        # Advance reset only after the prior action releases its shared epoch lock.
        def reset_after_action():
            try:
                # Hold named-lock and resetting phase through same-session bootstrap.
                with provider.reset_transaction() as reset_provider:
                    # Signal that phase one acquired exclusive epoch ownership and committed.
                    reset_body_entered.set()
                    # Recreate the sole wallet in the new mutable namespace.
                    reset_provider.ensure_player({"player_id": "lifecycle_204", "display_name": "Lifecycle 204", "type": "human", "balance": 10.0, "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00", "status": "active"})
            # Retain any reset failure for one secret-free assertion.
            except BaseException as exc:
                # Store only the in-memory exception object.
                ordering_errors.append(exc)

        # Start the action on one pool lease.
        ordering_action_thread = threading.Thread(target=execute_before_reset)
        # Launch the exact executor transaction.
        ordering_action_thread.start()
        # Require the action to retain shared epoch ownership in its planner.
        assert ordering_planner_entered.wait(5)
        # Start reset on the other pool lease.
        ordering_reset_thread = threading.Thread(target=reset_after_action)
        # Launch the exclusive reset contender.
        ordering_reset_thread.start()
        # Allow the reset to reach its exclusive singleton lock wait.
        time.sleep(0.2)
        # Require caller bootstrap not to begin before the action commits.
        assert not reset_body_entered.is_set()
        # Let the prior action commit claim, state, and receipt atomically.
        release_ordering_planner.set()
        # Join both bounded operations after lock ownership transfers.
        ordering_action_thread.join(5)
        # Join reset after phase two publishes ready.
        ordering_reset_thread.join(5)
        # Require exact action-before-reset order without hidden failure.
        assert not ordering_action_thread.is_alive() and not ordering_reset_thread.is_alive() and ordering_errors == [] and reset_body_entered.is_set()
        # Require the pre-reset action to have committed originally.
        assert ordering_results["execute"][1] is False
        # Resolve the retired exact key only in epoch three, never through its epoch-two receipt.
        assert provider.resolve_game_action(identity=ordering_identity, resources=resources) == GameActionResolution(status="uncommitted")
        # Build a capacity-one provider for the complete shipped Admin reset bootstrap chain.
        bootstrap_provider = storage.MySQLStorageProvider(provider.config, pool_config=storage.MySQLPoolConfig(capacity=1, checkout_wait_ms=1000, connect_timeout_seconds=3))
        # Preserve the outer JSON test selection before routing provider-backed documents to MySQL.
        previous_storage_provider = os.environ.get("CASINO_STORAGE_PROVIDER")
        # Select MySQL so state_store delegates auth and player documents instead of using local JSON.
        os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
        try:
            # Route provider-aware auth and player helpers through only this disposable target.
            storage.set_provider_for_tests(bootstrap_provider)
            # Require the live harness to exercise provider-aware JSON documents rather than local files.
            assert storage.storage_provider_name() == "mysql"
            # Require the configured selector and injected provider to resolve to the same disposable target.
            assert storage.get_storage_provider() is bootstrap_provider
            # Hold one physical session across clear, actual bootstrap helpers, and ready finalization.
            with bootstrap_provider.reset_transaction() as reset_provider:
                # Recreate the exact default player set through the shipped provider-neutral wrapper.
                storage.bootstrap_players(players.default_players)
                # Run the real read-create-promote Admin bootstrap chain under the retained session.
                bootstrapped_admin = auth.bootstrap_admin_from_env()
                # Require the configured bootstrap identity to end with exact owner authority.
                assert auth.PLATFORM_OWNER_ROLE in auth.roles_for_user(bootstrapped_admin)
                # Read users again so a trailing implicit document transaction is sanitized too.
                visible_users = auth.load_users().get("users", [])
                # Require the created Admin identity to be durably visible inside reset bootstrap.
                assert any(row.get("user_id") == bootstrapped_admin.get("user_id") for row in visible_users)
                # Materialize the unchanged reset response player projection before ready release.
                visible_players = players.list_players()
                # Require all defaults plus the Admin-bound wallet without exposing identities.
                assert len(visible_players) >= len(players.default_players()["players"])
                # Borrow the retained session only to prove GET_LOCK survives nested close cleanup.
                lock_evidence = reset_provider.connect()
                # Always sanitize this final borrowed read without returning the sole lease.
                try:
                    # Open a dictionary cursor for secret-free lock ownership evidence.
                    lock_cursor = lock_evidence.cursor(dictionary=True)
                    # Read only the session owner identifier for the already-derived lock name.
                    lock_cursor.execute("SELECT IS_USED_LOCK(%s) AS owner_id", (reset_provider._mysql_reset_lock_name(),))
                    # Require one current session owner while bootstrap remains unavailable.
                    assert lock_cursor.fetchone()["owner_id"] is not None
                # End the implicit evidence transaction while preserving the named lock.
                finally:
                    # Exercise the borrowed rollback-without-close boundary under a real connector.
                    lock_evidence.close()
            # Open the only capacity-one lease again after reset returned it to the pool.
            final_connection = bootstrap_provider.connect()
            # Always return the final read-only evidence lease.
            try:
                # Read exact final epoch and released named-lock state.
                final_cursor = final_connection.cursor(dictionary=True)
                # Require a fourth ready namespace after the complete reset bootstrap.
                final_cursor.execute("SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state")
                # Bind exact successful phase completion.
                assert final_cursor.fetchone() == {"state_id": 1, "current_epoch": 4, "phase": "ready"}
                # Prove the reset session released its target-scoped lock before pool reuse.
                final_cursor.execute("SELECT IS_FREE_LOCK(%s) AS is_free", (bootstrap_provider._mysql_reset_lock_name(),))
                # Require exact server confirmation rather than process-local inference.
                assert final_cursor.fetchone() == {"is_free": 1}
                # End the final connector-owned read transaction explicitly.
                final_connection.rollback()
            # Return the sole physical session to its pool.
            finally:
                # Exercise ordinary pooled lease cleanup after reset finalization.
                final_connection.close()
            # Require capacity one, no checked-out lease, and exactly one reusable physical session.
            pool_evidence = bootstrap_provider.pool_snapshot()
            # Prove no reset/bootstrap connection leak or hidden capacity expansion.
            assert (pool_evidence["capacity"], pool_evidence["in_use"], pool_evidence["idle"], pool_evidence["physical_created"]) == (1, 0, 1, 1)
        # Restore the process-wide test provider on every assertion or connector failure.
        finally:
            # Protect exact environment restoration even if pool cleanup surfaces a connector failure.
            try:
                # Clearing injection also closes the capacity-one provider's idle pool safely.
                storage.set_provider_for_tests(None)
            # Restore the outer provider selector on every cleanup outcome.
            finally:
                # Remove a test-only selector that was absent before this bounded live harness.
                if previous_storage_provider is None:
                    # Restore exact environment absence so later suites retain their original provider choice.
                    os.environ.pop("CASINO_STORAGE_PROVIDER", None)
                # Restore the exact non-secret prior selector when the outer workflow supplied one.
                else:
                    # Preserve the enclosing workflow's JSON selection after disposable MySQL evidence.
                    os.environ["CASINO_STORAGE_PROVIDER"] = previous_storage_provider
    finally:
        # Close every idle pooled disposable connection on success or failure.
        provider.close_pool()


# Run the complete MySQL 8.4 migration and DDL-free runtime matrix.
def run_mysql_migration_live_matrix(request_latency_callback=None):
    # Reject a malformed optional test callback before any administrator connection.
    if request_latency_callback is not None and not callable(request_latency_callback):
        # Keep the no-argument production path unchanged while failing closed on test misuse.
        raise TypeError("request_latency_callback must be callable")
    # Validate every synthetic database and account before connecting.
    base_database = _identifier(os.environ["CASINO_MYSQL_MIGRATION_DATABASE"])
    # Derive a separate explicit schema-two upgrade target.
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
                # Start a separate process that must refuse before attempting the held target lock.
                with ProcessPoolExecutor(max_workers=1) as executor:
                    # Capture only the fixed child outcome.
                    locked_result = executor.submit(_locked_apply_worker, base_database, str(base_proof)).result(timeout=30)
                # Require the child to return the catalog hold rather than lock contention.
                assert "apply policy is held" in locked_result
                # Release the parent-owned target lock.
                lock_cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                # Require release confirmation before fixture-only schema seeding.
                assert lock_cursor.fetchone()[0] == 1
                # Require direct public apply to refuse with the target still empty.
                try:
                    # Attempt the bridge-held public mutation boundary.
                    mysql_migrations.apply_migrations(base_connection, base_config, base_proof)
                # Accept only the fixed catalog policy result.
                except mysql_migrations.MigrationError as exc:
                    # Require exact held-policy semantics.
                    assert "apply policy is held" in str(exc)
                # Fail if bridge source applied any migration.
                else:
                    # Surface one fixed category.
                    raise AssertionError("held migration application was permitted")
                # Prove no metadata or application table was created by the held call.
                empty_cursor = base_connection.cursor()
                # Count only Casino-owned tables in the disposable database.
                empty_cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'casino\\_%' ESCAPE '\\\\'")
                # Require exact zero state before fixture-only DDL.
                assert int(empty_cursor.fetchone()[0]) == 0
                # Seed the checksum-verified full chain solely for runtime compatibility proof.
                migrations, _, _, _ = mysql_migrations.load_catalog()
                # Apply the complete fixture prefix through existing private test seams.
                _seed_catalog_prefix(base_connection, migrations, 5)
                # Inspect exact runtime state after fixture seeding.
                final_state = mysql_migrations.verify_runtime_compatibility(base_connection)
                # Require exact schema version five.
                assert final_state.current_version == 5 and final_state.status == "clean"
                # Require exact applied migration sequence.
                assert [item[0] for item in final_state.applied] == [1, 2, 3, 4, 5]
                # Open a fresh process-independent connector to model schema-five restart readiness.
                restarted_five = _connector().connect(**base_config.kwargs())
                # Always close the restarted schema-five connection.
                try:
                    # Require the complete chain to remain runtime compatible after reconnection.
                    assert mysql_migrations.verify_runtime_compatibility(restarted_five).current_version == 5
                # Release the restarted connection.
                finally:
                    # Close all connector-owned state.
                    restarted_five.close()
                # Prove held apply remains closed even at the complete schema-five tail.
                try:
                    # Attempt a no-proof application call at the full chain.
                    mysql_migrations.apply_migrations(base_connection, base_config, None)
                # Accept the same fixed hold.
                except mysql_migrations.MigrationError as exc:
                    # Require exact policy identity.
                    assert "apply policy is held" in str(exc)
                # Fail if full-chain state bypassed the hold.
                else:
                    # Surface one fixed category.
                    raise AssertionError("held migration tail recheck was permitted")
            # Always close the base migrator connection.
            finally:
                # Release all base connection resources.
                base_connection.close()
            # Build and open the isolated supported-upgrade target.
            upgrade_config = _migration_config(upgrade_database)
            # Connect as the deployment-only migrator.
            upgrade_connection = _connector().connect(**upgrade_config.kwargs())
            # Start protected exact schema-two seeding and runner upgrade.
            try:
                # Load the immutable four-step catalog.
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
                # Open the statement cursor used only for reviewed predecessor migrations.
                cursor = upgrade_connection.cursor()
                # Seed the exact immutable version-one and version-two prefix.
                for migration in migrations[:2]:
                    # Re-read the clean contiguous source before each transition.
                    source_state = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                    # Mark this predecessor applying before application DDL.
                    mysql_migrations._mark_applying(upgrade_connection, source_state, migration)
                    # Execute every exact predecessor statement without SQL splitting.
                    for statement in migration.statements:
                        # Execute one exact driver statement.
                        cursor.execute(statement)
                    # Persist only the completed predecessor checksum.
                    mysql_migrations._mark_complete(upgrade_connection, migration, migrations)
                # Require the exact supported clean schema-two state.
                version_two = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Prove migrations three and four remain pending.
                assert version_two.current_version == 2 and version_two.status == "clean"
                # Prove bridge runtime readiness accepts the exact immutable schema-two prefix.
                assert mysql_migrations.verify_runtime_compatibility(upgrade_connection).current_version == 2
                # Open a fresh connector to model schema-two application restart readiness.
                restarted_two = _connector().connect(**upgrade_config.kwargs())
                # Always close the restarted schema-two connection.
                try:
                    # Require exact prefix compatibility after reconnection.
                    assert mysql_migrations.verify_runtime_compatibility(restarted_two).current_version == 2
                # Release the restarted connection.
                finally:
                    # Close all connector-owned state.
                    restarted_two.close()
                # Mark the exact next transition dirty to prove automatic replay refusal.
                cursor.execute("UPDATE casino_schema_migration_state SET status = 'dirty', applying_version = 3 WHERE state_id = 1")
                # Persist the intentional interrupted-state fixture.
                upgrade_connection.commit()
                # Require runtime compatibility to reject dirty schema two.
                try:
                    # Inspect the exact dirty two/applying-three state.
                    mysql_migrations.verify_runtime_compatibility(upgrade_connection)
                # Accept only a fixed migration refusal.
                except mysql_migrations.MigrationError:
                    # Continue after the required fail-closed result.
                    pass
                # Fail if dirty schema two served runtime traffic.
                else:
                    # Surface one fixed category.
                    raise AssertionError("dirty schema-two migration state was accepted")
                # Require public apply to refuse automatic replay.
                try:
                    # Attempt normal application against the dirty boundary.
                    mysql_migrations.apply_migrations(upgrade_connection, upgrade_config, None)
                # Accept only the fixed forward-fix requirement.
                except mysql_migrations.MigrationError:
                    # Continue after required refusal.
                    pass
                # Fail if the interrupted migration replayed.
                else:
                    # Surface one fixed category.
                    raise AssertionError("dirty schema-three migration was replayed")
                # Restore the intentional fixture to exact clean schema two.
                cursor.execute("UPDATE casino_schema_migration_state SET status = 'clean', applying_version = NULL WHERE state_id = 1")
                # Commit source restoration before proof construction.
                upgrade_connection.commit()
                # Require held policy to continue refusing from clean schema two.
                try:
                    # Attempt the pending suffix through the public runner.
                    mysql_migrations.apply_migrations(upgrade_connection, upgrade_config, None)
                # Accept only the fixed catalog hold.
                except mysql_migrations.MigrationError as exc:
                    # Require exact held-policy identity.
                    assert "apply policy is held" in str(exc)
                # Fail if the bridge applied schema three.
                else:
                    # Surface one fixed category.
                    raise AssertionError("schema-two held suffix was applied")
                # Seed only migration three through the disposable fixture seam.
                source_state = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Mark exact schema three applying for fixture setup.
                mysql_migrations._mark_applying(upgrade_connection, source_state, migrations[2])
                # Execute the one checksum-verified schema-three statement.
                for statement in migrations[2].statements:
                    # Apply one exact driver statement in the disposable target.
                    cursor.execute(statement)
                # Complete the exact full-chain fixture state.
                mysql_migrations._mark_complete(upgrade_connection, migrations[2], migrations)
                # Require runtime readiness to accept the clean schema-three prefix.
                assert mysql_migrations.verify_runtime_compatibility(upgrade_connection).current_version == 3
                # Build one exact legacy schema-three receipt before claim backfill.
                legacy_resources = json.dumps({"state_keys": [], "wallet_ids": []}, sort_keys=True, separators=(",", ":"))
                # Build one canonical self-consistent zero-cost legacy receipt.
                legacy_receipt = json.dumps({"identity": {"action_key": "legacy_204", "game_id": "roulette", "player_id": "player_204", "request_fingerprint": "e" * 64}, "plan": {"movements": [], "outcome": {"legacy": True}, "state_updates": []}, "resources": {"state_keys": [], "wallet_ids": []}, "snapshot_after": {"state_values": [], "wallet_balances": []}, "snapshot_before": {"state_values": [], "wallet_balances": []}}, sort_keys=True, separators=(",", ":"))
                # Hash the exact receipt bytes independently.
                legacy_sha = hashlib.sha256(legacy_receipt.encode("utf-8")).hexdigest()
                # Insert the representative legacy schema-three row.
                cursor.execute("INSERT INTO casino_game_action_receipts (game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256) VALUES (%s, %s, %s, %s, %s, %s, %s)", ("roulette", "player_204", "legacy_204", "e" * 64, legacy_resources, legacy_receipt, legacy_sha))
                # Commit the legacy row before schema-four DDL backfill.
                upgrade_connection.commit()
                # Apply only migration four through the disposable fixture seam.
                source_state = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Mark exact schema four applying for fixture setup.
                mysql_migrations._mark_applying(upgrade_connection, source_state, migrations[3])
                # Execute every checksum-verified schema-four statement.
                for statement in migrations[3].statements:
                    # Apply one exact driver statement in the disposable target.
                    cursor.execute(statement)
                # Complete the full schema-four fixture state.
                mysql_migrations._mark_complete(upgrade_connection, migrations[3], migrations)
                # Require runtime readiness to accept exact clean schema four.
                assert mysql_migrations.verify_runtime_compatibility(upgrade_connection).current_version == 4
                # Read the backfilled claim and unchanged receipt bytes.
                cursor.execute("SELECT c.reset_epoch, r.reset_epoch, c.disposition, c.request_fingerprint, c.resources_json, r.claim_disposition, r.receipt_json, r.receipt_sha256 FROM casino_game_action_claims c JOIN casino_game_action_receipts r ON r.reset_epoch=c.reset_epoch AND r.game_id=c.game_id AND r.player_id=c.player_id AND r.action_key=c.action_key WHERE c.reset_epoch=1 AND c.game_id=%s AND c.player_id=%s AND c.action_key=%s", ("roulette", "player_204", "legacy_204"))
                # Require exact execute backfill and byte-for-byte legacy receipt preservation.
                assert tuple(str(value) for value in cursor.fetchone()) == ("1", "1", "execute", "e" * 64, legacy_resources, "execute", legacy_receipt, legacy_sha)
                # Build one secret-free schema-four bridge session for native-table backfill.
                bridge_session = {"session_id": "legacy-session-204", "token_digest": session_token_digest("legacy-session-token-204"), "user_id": "legacy-user-204", "csrf_token": "legacy-session-csrf-204".ljust(32, "x"), "generation": 1, "status": "active", "created_at": "2026-01-01T00:00:00.000Z", "updated_at": "2026-01-01T00:00:00.000Z", "expires_at": "2027-01-01T00:00:00.000Z", "client": "migration-live", "auth_method": "local"}
                # Encode the complete canonical durable row without plaintext bearer authority.
                bridge_payload = json.dumps(bridge_session, sort_keys=True, separators=(",", ":"))
                # Insert one exact keyed compatibility row before schema-five migration.
                cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s)", (f"auth/session/v2/row/{bridge_session['token_digest']}", bridge_payload, bridge_session["updated_at"]))
                # Commit the schema-four bridge source before native-table DDL.
                upgrade_connection.commit()
                # Mark exact schema five applying through the disposable fixture seam.
                source_state = mysql_migrations.inspect_schema(upgrade_connection, migrations)
                # Persist migration-five applying metadata before its DDL and backfill.
                mysql_migrations._mark_applying(upgrade_connection, source_state, migrations[4])
                # Execute every checksum-verified schema-five statement.
                for statement in migrations[4].statements:
                    # Apply one exact driver statement in reviewed order.
                    cursor.execute(statement)
                # Complete the full schema-five fixture state.
                mysql_migrations._mark_complete(upgrade_connection, migrations[4], migrations)
                # Require runtime readiness to accept exact clean schema five.
                assert mysql_migrations.verify_runtime_compatibility(upgrade_connection).current_version == 5
                # Read indexed columns and canonical bytes from the backfilled native row.
                cursor.execute("SELECT session_id, token_digest, user_id, status, generation, session_json FROM casino_sessions WHERE session_id=%s", (bridge_session["session_id"],))
                # Require exact index values and semantically exact secret-free payload.
                native_session = cursor.fetchone()
                assert tuple(str(value) for value in native_session[:5]) == (bridge_session["session_id"], bridge_session["token_digest"], bridge_session["user_id"], "active", "1") and json.loads(str(native_session[5])) == bridge_session and "token" not in json.loads(str(native_session[5]))
                # Require the compatibility row to be retired after successful backfill.
                cursor.execute("SELECT COUNT(*) FROM casino_documents WHERE document_key LIKE 'auth/session/v2/row/%'")
                # Require zero dual-authority bridge rows.
                assert int(cursor.fetchone()[0]) == 0
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
                cursor.execute("UPDATE casino_schema_migration_state SET current_version = 6 WHERE state_id = 1")
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
                # Restore current version and mark an unknown future transition dirty.
                cursor.execute("UPDATE casino_schema_migration_state SET current_version = 5, status = 'dirty', applying_version = 6 WHERE state_id = 1")
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
            # Grant database-scoped read rights needed by runtime compatibility and current locking reads.
            admin_cursor.execute(f"GRANT SELECT ON `{base_database}`.* TO '{runtime_user}'@'%'")
            # Grant compatible insertion, update, and delete only to established mutable runtime tables.
            for table in ("casino_players", "casino_ledger", "casino_history", "casino_documents", "casino_sessions"):
                # Preserve ordinary runtime DML while excluding lifecycle history and control rows.
                admin_cursor.execute(f"GRANT INSERT, UPDATE, DELETE ON `{base_database}`.`{table}` TO '{runtime_user}'@'%'")
            # Permit append-only lifecycle ownership without update or delete authority.
            for table in ("casino_game_action_claims", "casino_game_action_receipts"):
                # Grant only the insert operation required for immutable action history.
                admin_cursor.execute(f"GRANT INSERT ON `{base_database}`.`{table}` TO '{runtime_user}'@'%'")
            # Permit exact compare-and-set reset phase transitions on the singleton only.
            admin_cursor.execute(f"GRANT UPDATE ON `{base_database}`.`casino_game_action_epoch_state` TO '{runtime_user}'@'%'")
            # Commit the least-privilege grant.
            admin.commit()
            # Open a runtime-identity connection for compatibility and denial evidence.
            runtime_connection = _connector().connect(host=os.environ["CASINO_MYSQL_HOST"], port=int(os.environ.get("CASINO_MYSQL_PORT", "3306")), user=runtime_user, password=runtime_password, database=base_database)
            # Start protected runtime grant tests.
            try:
                # Prove runtime startup compatibility with SELECT only.
                assert mysql_migrations.verify_runtime_compatibility(runtime_connection).current_version == 5
                # Read actual grants through the runtime identity.
                runtime_cursor = runtime_connection.cursor()
                # Query current-user grants without administrator credentials.
                runtime_cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
                # Normalize grant text only in memory.
                grants = "\n".join(str(row[0]).upper() for row in runtime_cursor.fetchall())
                # Require the four approved DML privilege words across scoped grants.
                assert all(privilege in grants for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"))
                # Require no schema or grant-management privilege.
                assert all(privilege not in grants for privilege in ("CREATE", "ALTER", "DROP", "INDEX", "TRIGGER", "GRANT OPTION"))
                # Prove paid/zero-cost insertion, duplicate refusal, and exact persistence.
                _exercise_game_action_receipts(runtime_connection)
                # Prove the production lifecycle provider converges all relational projections.
                _exercise_game_action_provider()
                # Enumerate forbidden mutation against the two immutable lifecycle tables.
                immutable_denials = (
                    # Refuse claim disposition mutation.
                    "UPDATE casino_game_action_claims SET disposition='execute' WHERE action_key='uncommitted_204'",
                    # Refuse claim deletion.
                    "DELETE FROM casino_game_action_claims WHERE action_key='uncommitted_204'",
                    # Refuse receipt mutation.
                    "UPDATE casino_game_action_receipts SET receipt_sha256=receipt_sha256 WHERE action_key='paid_204'",
                    # Refuse receipt deletion.
                    "DELETE FROM casino_game_action_receipts WHERE action_key='paid_204'",
                    # Refuse creation of another reset namespace row.
                    "INSERT INTO casino_game_action_epoch_state (state_id, current_epoch, phase) VALUES (2, 1, 'ready')",
                    # Refuse deletion of the singleton reset namespace.
                    "DELETE FROM casino_game_action_epoch_state WHERE state_id=1",
                )
                # Require runtime grants to enforce append-only lifecycle rows.
                for statement in immutable_denials:
                    # Execute one expected table-level privilege denial.
                    try:
                        # Attempt mutation as the runtime identity.
                        runtime_cursor.execute(statement)
                    # Accept only connector database errors.
                    except _connector().Error as exc:
                        # Require a table-level command denial.
                        assert int(getattr(exc, "errno", 0) or 0) == 1142
                        # Clear statement transaction state.
                        runtime_connection.rollback()
                    # Fail if immutable lifecycle history was mutable.
                    else:
                        # Surface one fixed privilege category.
                        raise AssertionError("runtime lifecycle-row mutation was permitted")
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
