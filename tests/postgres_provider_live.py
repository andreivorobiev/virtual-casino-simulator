# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Exercise provider-core parity on one disposable PostgreSQL 16 target. (TEST-255)"""

# Import dynamic module loading for the independently owned session-mixin seam.
import importlib.util
# Import JSON for one bounded sanitized evidence record.
import json
# Import environment access for explicit disposable authorization and migration input.
import os
# Import safe cleanup for the verified temporary cluster root.
import shutil
# Import generated disposable role, database, password, and binding identities.
import secrets
# Import the active interpreter path for the accepted migration runner.
import sys
# Import temporary-directory allocation outside the repository.
import tempfile
# Import a synthetic module container for the disjoint session ownership seam.
from types import ModuleType
# Import portable paths for the source, binaries, data, and logs.
from pathlib import Path
# Import restoring module patches around isolated provider source loading.
from unittest import mock

# Resolve the repository root independently from process cwd.
ROOT = Path(__file__).resolve().parents[1]
# Prepend this exact checked-out source tree for direct execution.
if str(ROOT) not in sys.path:
    # Keep project imports bound to the candidate under test.
    sys.path.insert(0, str(ROOT))

# Import psycopg only from this explicitly selected live test.
import psycopg
# Import PostgreSQL-safe dynamic identifier and literal composition.
from psycopg import sql

# Import immutable PostgreSQL target and pool configuration.
from casino.core.postgres_pool import PostgresPoolConfig
from casino.core.storage.base import PostgresConfig
# Import the accepted migration runner contract and its official binary helpers.
from casino.core.postgres_migrations import DISPOSABLE_MARKER
from tests import postgres_migration_live

# Resolve the provider source owned by this lane.
PROVIDER_PATH = ROOT / "casino" / "core" / "storage" / "postgres_provider.py"
# Read the official portable PostgreSQL binary root from one explicit variable.
POSTGRES_BIN = Path(os.environ.get("CASINO_POSTGRES_TEST_BIN", ""))
# Require a distinct explicit marker before this test creates any process or identity.
LIVE_MARKER = "CASINO-POSTGRES-1058-LIVE"


# Define the independently reviewed session mixin without implementing session behavior here.
class StubPostgresSessionMixin:
    # Leave all first-class session methods to the disjoint session lane.
    pass


# Publish one fixed secret-free phase label for bounded live diagnosis.
def _phase(name: str) -> None:
    # Emit only a source-owned finite marker and flush immediately.
    print(f"PG1058-LIVE:{name}", file=sys.stderr, flush=True)


# Refuse accidental live execution before any filesystem or process mutation.
def _require_live_authorization() -> None:
    # Require the exact provider-live marker.
    if os.environ.get("CASINO_POSTGRES_LIVE_TEST") != LIVE_MARKER:
        # Stop without naming a target or configured value.
        raise RuntimeError("PostgreSQL provider live test is not authorized")
    # Require the same official PostgreSQL management binaries as the migration lane.
    if not all((POSTGRES_BIN / name).is_file() for name in ("postgres.exe", "initdb.exe", "pg_ctl.exe")):
        # Refuse PATH fallback or an unreviewed server installation.
        raise RuntimeError("PostgreSQL provider live-test binaries are unavailable")


# Load provider core against the real migration verifier and the disjoint session interface.
def _load_provider_module() -> ModuleType:
    # Build one session module exposing only the agreed mixin class.
    session_module = ModuleType("casino.core.storage.sessions_postgres")
    # Publish the exact composition name imported by provider core.
    session_module.PostgresSessionMixin = StubPostgresSessionMixin
    # Create a private module identity for this exact provider source file.
    spec = importlib.util.spec_from_file_location("tests._postgres_provider_live_under_test", PROVIDER_PATH)
    # Require a standard source loader before executing tracked code.
    if spec is None or spec.loader is None:
        # Fail before opening a PostgreSQL connection.
        raise RuntimeError("PostgreSQL provider live source could not be loaded")
    # Allocate the isolated module object.
    provider_module = importlib.util.module_from_spec(spec)
    # Replace only the independently owned session module during source execution.
    with mock.patch.dict(sys.modules, {"casino.core.storage.sessions_postgres": session_module}):
        # Execute the exact provider source with the real accepted migration seam.
        spec.loader.exec_module(provider_module)
    # Return the isolated production implementation.
    return provider_module


# Build migration-runner environment for only the newly created target.
def _migration_environment(port: int, role: str, password: str, database: str, binding_key: str) -> dict:
    # Copy the current isolated environment without publishing its values.
    environment = dict(os.environ)
    # Select literal loopback for the private listener.
    environment["CASINO_POSTGRES_MIGRATION_HOST"] = "127.0.0.1"
    # Select the operating-system-reserved private port.
    environment["CASINO_POSTGRES_MIGRATION_PORT"] = str(port)
    # Select the process-created migration/runtime role.
    environment["CASINO_POSTGRES_MIGRATION_USER"] = role
    # Supply the generated process-local password.
    environment["CASINO_POSTGRES_MIGRATION_PASSWORD"] = password
    # Select the process-created empty database.
    environment["CASINO_POSTGRES_MIGRATION_DATABASE"] = database
    # Bind receipts to a distinct generated test key.
    environment["CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY"] = binding_key
    # Authorize mutation only through the accepted disposable marker.
    environment["CASINO_POSTGRES_MIGRATION_DISPOSABLE"] = DISPOSABLE_MARKER
    # Return caller-local configuration for the child runner.
    return environment


# Exercise provider adapter, ordinary persistence, visibility, and reset on one live target.
def _exercise_provider(port: int, role: str, password: str, database: str) -> dict:
    # Load the exact production provider core with only the session ownership seam isolated.
    provider_module = _load_provider_module()
    # Build immutable runtime connection settings for the synthetic target.
    config = PostgresConfig("127.0.0.1", port, role, password, database)
    # Use one physical slot to prove retained reset borrowing and same-session reuse.
    pool_config = PostgresPoolConfig(capacity=1, checkout_wait_ms=500, connect_timeout_seconds=5)
    # Construct the real psycopg-backed provider without opening a connection yet.
    selected = provider_module.PostgresStorageProvider(config, pool_config)
    # Track terminal pool cleanup independently from test assertions.
    pool_closed = False
    # Start the complete provider lifecycle with unconditional pool shutdown.
    try:
        # Run the real config-free checksum-bound readiness verifier.
        selected.ensure_ready()
        # Require the exact clean schema-five result cached by the provider.
        if (selected._ready, selected._schema_version) != (True, 5):
            # Refuse incomplete runtime readiness evidence.
            raise RuntimeError("PostgreSQL provider readiness evidence is invalid")
        # Read the sole idle physical connection created by readiness.
        physical = selected._pool._idle[0]
        # Bind all status checks to psycopg's public libpq enum.
        idle_status = psycopg.pq.TransactionStatus.IDLE
        # Require readiness return to restore autocommit false and exact IDLE.
        if physical.autocommit is not False or physical.info.transaction_status != idle_status:
            # Reject a connection that cannot be safely reused.
            raise RuntimeError("PostgreSQL provider readiness left session state")
        # Acquire the exact same physical session from the capacity-one pool.
        lease = selected.connect()
        # Refuse silent reconnection during the first reuse.
        if lease._connection is not physical:
            # Preserve only a fixed identity-failure category.
            raise RuntimeError("PostgreSQL provider replaced its physical session")
        # Open one tracked request cursor.
        cursor = lease.cursor()
        # Start deliberate transaction residue without committing it.
        cursor.execute("SET LOCAL application_name = 'casino_provider_1058_live'")
        # Return the lease so rollback, DISCARD ALL, and wire-check execute.
        lease.close()
        # Require the same session to remain reusable and transaction-idle.
        if selected._pool._idle != [physical] or physical.autocommit is not False or physical.info.transaction_status != idle_status:
            # Reject reset or health behavior that leaves an implicit transaction.
            raise RuntimeError("PostgreSQL provider reset did not preserve idle state")
        # Bind the source-owned game-action taxonomy to only finite psycopg lock classes.
        lock_types = (psycopg.errors.LockNotAvailable(), psycopg.errors.DeadlockDetected())
        # Require both allowed lock outcomes and reject an unrelated integrity outcome.
        if not all(selected._is_game_action_lock_contention(error) for error in lock_types) or selected._is_game_action_lock_contention(psycopg.errors.UniqueViolation()):
            # Refuse a widened resolver taxonomy.
            raise RuntimeError("PostgreSQL game-action lock taxonomy is invalid")
        # Build one complete provider-neutral player.
        player = {"player_id": "provider-live", "display_name": "Provider Live", "type": "human", "balance": 100.0, "created_at": "2026-08-22T00:00:00+00:00", "updated_at": "2026-08-22T00:00:00+00:00", "status": "active"}
        # Insert-or-read the synthetic wallet through the public provider contract.
        durable_player = selected.ensure_player(player)
        # Require exact fake-money and identity projection.
        if (durable_player["player_id"], durable_player["balance"]) != ("provider-live", 100.0):
            # Reject a relational/public shape mismatch.
            raise RuntimeError("PostgreSQL provider player parity failed")
        # Execute one ordinary atomic debit.
        debit = selected.transact_ledger("provider-live", -1.25, "BET", game="roulette", round_id="round-live", details={"kind": "inside"})
        # Execute one storage-enforced idempotent debit.
        first_once, first_replayed = selected.transact_ledger_once("provider-live", -2.0, "BET", "provider-live-action", game="roulette", round_id="round-once", details={"kind": "straight"})
        # Replay the exact action without another wallet mutation.
        replay_once, replayed = selected.transact_ledger_once("provider-live", -2.0, "BET", "provider-live-action", game="roulette", round_id="round-once", details={"kind": "straight"})
        # Require exact cents and immutable replay identity.
        if debit["balance_after"] != 98.75 or first_replayed or not replayed or replay_once["ledger_id"] != first_once["ledger_id"]:
            # Reject ledger atomicity or idempotency drift.
            raise RuntimeError("PostgreSQL provider ledger parity failed")
        # Write one Unicode JSONB document.
        selected.write_document("provider/live.json", {"message": "готово", "count": 1})
        # Update the same row under its provider-owned row lock.
        updated = selected.update_document("provider/live.json", lambda value: {**value, "count": value["count"] + 1}, {})
        # Require exact decoded JSONB output.
        if updated != {"message": "готово", "count": 2} or selected.read_document("provider/live.json", {}) != updated:
            # Reject document encoding, locking, or read parity drift.
            raise RuntimeError("PostgreSQL provider document parity failed")
        # Build one complete history event using the existing public field shape.
        history = {"timestamp": "2026-08-22T00:00:01+00:00", "game": "roulette", "round_id": "round-live", "player_id": "provider-live", "bet_type": "inside", "bet_label": "red", "amount": 1.25, "outcome": "loss", "payout": 0.0, "balance_after": 98.75, "details_json": {"number": 1}, "schema_version": "1"}
        # Append one history event through the provider transaction boundary.
        selected.append_history(history)
        # Require exact recent history selection.
        if len(selected.recent_history(limit=1, game="roulette")) != 1:
            # Reject append or bounded-read parity drift.
            raise RuntimeError("PostgreSQL provider history parity failed")
        # Require a clean read-only wallet normalization scan.
        normalization = selected.normalize_wallet_balances(apply=False)
        # Bind the exact single-wallet no-residue result.
        if normalization != {"provider": "postgres", "checked": 1, "residue_count": 0, "normalized_count": 0, "clean": True, "applied": False}:
            # Reject cents or scan semantics drift.
            raise RuntimeError("PostgreSQL provider normalization parity failed")
        # Enter shared reset exclusion and reuse the retained capacity-one session.
        with selected.state_visibility_transaction():
            # Require an ordinary nested read to remain available.
            if selected.get_player("provider-live", lambda: {}) is None:
                # Reject lost visibility during the shared boundary.
                raise RuntimeError("PostgreSQL provider visibility parity failed")
        # Build a fresh wallet for reset-owned bootstrap.
        reset_player = {**player, "player_id": "provider-reset", "display_name": "Provider Reset", "balance": 25.0}
        # Clear mutable state, bootstrap through the retained lease, and publish ready.
        with selected.reset_transaction():
            # Require process-local target ownership while the boundary is active.
            if not selected._game_action_reset_is_active():
                # Reject a resolver-visible reset ownership gap.
                raise RuntimeError("PostgreSQL provider reset activity was not visible")
            # Reuse the sole physical session for ordinary bootstrap.
            selected.bootstrap_players({"players": [reset_player]})
        # Require reset ownership to clear after complete finalization.
        if selected._game_action_reset_is_active():
            # Reject stale process-local reset state.
            raise RuntimeError("PostgreSQL provider reset activity did not clear")
        # Require cleared documents, ledger, and history plus only the reset wallet.
        post_reset_players = selected.load_players(lambda: {"players": []})["players"]
        post_reset_clean = selected.read_document("provider/live.json", None) is None and selected.read_ledger_recent(limit=5) == [] and selected.recent_history(limit=5) == []
        # Bind exact reset/bootstrap public state.
        if [(row["player_id"], row["balance"]) for row in post_reset_players] != [("provider-reset", 25.0)] or not post_reset_clean:
            # Reject partial reset or visibility publication.
            raise RuntimeError("PostgreSQL provider reset parity failed")
        # Capture final pool metrics before shutdown.
        snapshot = selected.pool_snapshot()
        # Require one physical connection, reuse, rollback cleanup, and no discard/reconnect.
        if snapshot["physical_created"] != 1 or snapshot["reused"] < 1 or snapshot["rollback_cleanup"] < 1 or snapshot["discarded"] != 0 or snapshot["connector_error"] != 0:
            # Reject misleading same-session evidence.
            raise RuntimeError("PostgreSQL provider pool evidence is invalid")
        # Require the final idle object to remain the original physical session.
        if selected._pool._idle != [physical] or physical.autocommit is not False or physical.info.transaction_status != idle_status:
            # Reject any final connection-state residue.
            raise RuntimeError("PostgreSQL provider final session state is invalid")
        # Close the sole physical connection before target teardown.
        selected.close_pool()
        # Record terminal pool ownership for the unconditional cleanup path.
        pool_closed = True
        # Require zero active or idle pool capacity after shutdown.
        closed_snapshot = selected.pool_snapshot()
        # Bind the exact terminal gauges without publishing target identity.
        if (selected._pool._total, closed_snapshot["idle"], closed_snapshot["in_use"]) != (0, 0, 0):
            # Reject socket residue before database removal.
            raise RuntimeError("PostgreSQL provider pool cleanup was incomplete")
        # Return bounded source-owned evidence only.
        return {"schema_version": 5, "physical_created": 1, "same_session": True, "idle_after_health": True, "idle_after_reset": True, "autocommit_restored": True, "player_count_after_reset": 1, "ledger_replay": True, "document_jsonb": True, "history_append": True, "reset_ready": True, "pool_closed": True}
    finally:
        # Close every provider-owned socket after a failed assertion or operation.
        if not pool_closed:
            # Start best-effort shutdown without masking the primary failure.
            try:
                # Close all idle physical sessions and reject further checkout.
                selected.close_pool()
            # Preserve the original provider failure when shutdown also fails.
            except Exception:
                # Retain no connector or target detail.
                pass


# Run the complete disposable target lifecycle and emit one sanitized record.
def main() -> int:
    # Refuse accidental execution before allocating any resource.
    _require_live_authorization()
    # Report explicit authorization without configured values.
    _phase("authorized")
    # Allocate one unique safe cluster root under the system temporary directory.
    cluster_root = Path(tempfile.mkdtemp(prefix="casino-postgres-1058-"))
    # Resolve the database data directory inside the verified root.
    data_root = cluster_root / "data"
    # Resolve the private server log inside the same root.
    log_path = cluster_root / "postgres.log"
    # Generate bounded role and database suffix entropy.
    nonce = secrets.token_hex(4)
    # Name the fresh role with the accepted migration lane's mandatory disposable suffix.
    role = f"casino_provider_{nonce}_1057"
    # Name the fresh database with the same migration-policy suffix.
    database = f"casino_provider_{nonce}_1057"
    # Generate a process-local database password.
    password = secrets.token_urlsafe(32)
    # Generate a distinct migration target-binding key.
    binding_key = secrets.token_urlsafe(48)
    # Reserve one currently free private loopback port.
    port = postgres_migration_live._loopback_port()
    # Track private cluster process state for unconditional cleanup.
    started = False
    # Track exact process-created database and role ownership.
    target_created = False
    # Initialize sanitized success evidence.
    evidence = {}
    # Start cluster, migration, provider, and cleanup as one fail-closed lifecycle.
    try:
        # Initialize one official PostgreSQL 16 cluster with local trust.
        postgres_migration_live._postgres_command([str(POSTGRES_BIN / "initdb.exe"), "-D", str(data_root), "-A", "trust", "-U", "casino_admin_1058", "--encoding=UTF8", "--no-locale"])
        # Report successful isolated cluster initialization.
        _phase("cluster_initialized")
        # Start only a literal-loopback disposable listener.
        postgres_migration_live._postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-l", str(log_path), "-o", f"-p {port} -h 127.0.0.1 -F", "-w", "start"])
        # Record the active process for guaranteed stop.
        started = True
        # Report private listener readiness.
        _phase("cluster_started")
        # Connect only to the new cluster's default database as its synthetic admin.
        admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1058", dbname="postgres", autocommit=True, connect_timeout=5)
        # Start exact target creation with unconditional admin cleanup.
        try:
            # Open one autocommit cursor for role and database DDL.
            cursor = admin.cursor()
            # Prove both generated identities were absent before creation.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Refuse adoption of any pre-existing target.
            if cursor.fetchone() != (0, 0):
                # Stop before ambiguous CREATE or DROP.
                raise RuntimeError("PostgreSQL provider disposable target already exists")
            # Create the fresh login role through safe identifier/literal composition.
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            # Create the fresh database owned only by that role.
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(database), sql.Identifier(role)))
            # Authorize cleanup only after both process-created identities exist.
            target_created = True
        finally:
            # Release admin connector state after target creation.
            admin.close()
        # Report fresh target creation without publishing identities.
        _phase("target_created")
        # Build migration input for only the synthetic target.
        environment = _migration_environment(port, role, password, database, binding_key)
        # Apply the accepted immutable five-version catalog through its real runner.
        applied = postgres_migration_live._runner("apply", environment)
        # Require exact clean schema-five migration completion.
        if (applied.get("current_version"), applied.get("status")) != (5, "clean"):
            # Refuse provider access to partial or dirty schema state.
            raise RuntimeError("PostgreSQL provider disposable migration failed")
        # Report exact schema readiness before runtime provider construction.
        _phase("migrations_applied")
        # Exercise adapter and provider core against the real migrated target.
        evidence = _exercise_provider(port, role, password, database)
        # Report complete provider evidence before target cleanup.
        _phase("provider_validated")
        # Reopen only the private cluster's default database for exact teardown.
        admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1058", dbname="postgres", autocommit=True, connect_timeout=5)
        # Start exact identity cleanup with unconditional admin close.
        try:
            # Open one autocommit teardown cursor.
            cursor = admin.cursor()
            # Terminate only sockets bound to the process-created database.
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
            # Drop only the database proven absent before this process created it.
            cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            # Drop only the role proven absent before this process created it.
            cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            # Verify exact zero role and database residue.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Require complete identity cleanup.
            if cursor.fetchone() != (0, 0):
                # Refuse a false cleanup result.
                raise RuntimeError("PostgreSQL provider target cleanup was incomplete")
            # Prevent duplicate drop attempts in the outer cleanup path.
            target_created = False
        finally:
            # Release teardown administrator state.
            admin.close()
        # Record exact identity cleanup without names.
        evidence["target_residue"] = {"roles": 0, "databases": 0}
        # Report successful target removal.
        _phase("target_removed")
    finally:
        # Attempt identity cleanup only for an active process-created target.
        if target_created and started:
            # Preserve the primary failure across best-effort teardown.
            try:
                # Connect only to the private listener's default database.
                admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1058", dbname="postgres", autocommit=True, connect_timeout=3)
                # Open one exact cleanup cursor.
                cursor = admin.cursor()
                # Terminate only connections to the generated database.
                cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
                # Drop only process-generated identities when still present.
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
                # Release the cleanup connector.
                admin.close()
            except Exception:
                # Retain no target or connector detail while process cleanup continues.
                pass
        # Stop the private PostgreSQL process when it is still active.
        if started:
            # Run the accepted bounded stop helper on the exact data directory.
            try:
                # Request fast shutdown before deleting any files.
                postgres_migration_live._postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-m", "fast", "-w", "stop"])
            except Exception:
                # Fall back to the accepted immediate shutdown only inside this private root.
                postgres_migration_live.subprocess.run([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-m", "immediate", "-w", "stop"], cwd=ROOT, stdout=postgres_migration_live.subprocess.DEVNULL, stderr=postgres_migration_live.subprocess.DEVNULL, timeout=60, check=False)
            # Report completion of the bounded stop attempt.
            _phase("cluster_stop_attempted")
        # Verify deletion remains confined to the allocated issue root.
        safe_root = cluster_root.parent == Path(tempfile.gettempdir()) and cluster_root.name.startswith("casino-postgres-1058-")
        # Remove only the verified private cluster tree.
        if safe_root:
            # Delete data and logs after listener shutdown.
            shutil.rmtree(cluster_root, ignore_errors=True)
            # Report completion of the bounded filesystem cleanup.
            _phase("cluster_remove_attempted")
    # Require complete filesystem cleanup after every successful lifecycle.
    if cluster_root.exists():
        # Refuse false zero-residue evidence.
        raise RuntimeError("PostgreSQL provider cluster cleanup was incomplete")
    # Record exact filesystem zero residue.
    evidence["cluster_root_removed"] = True
    # Print one bounded sorted evidence record.
    print(json.dumps(evidence, sort_keys=True))
    # Return standard success after target, pool, and filesystem cleanup.
    return 0


# Execute the live lifecycle only when directly selected.
if __name__ == "__main__":
    # Exit with the stable provider-live result.
    raise SystemExit(main())
