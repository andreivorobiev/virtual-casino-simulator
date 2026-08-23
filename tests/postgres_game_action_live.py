# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Exercise PostgreSQL game-action atomicity on one disposable PostgreSQL 16 target."""

# Import bounded worker execution for real execute-versus-resolve contention.
from concurrent.futures import ThreadPoolExecutor
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
# Import thread events for deterministic real row-lock contention.
import threading
# Import portable paths for source, binaries, data, and logs.
from pathlib import Path

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

# Import provider-neutral action values used by every real lifecycle call.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionResources
# Import immutable PostgreSQL target and pool configuration.
from casino.core.postgres_pool import PostgresPoolConfig
from casino.core.storage.base import PostgresConfig
# Import the real composed PostgreSQL provider.
from casino.core.storage.postgres_provider import PostgresStorageProvider
# Import the accepted disposable migration authorization marker.
from casino.core.postgres_migrations import DISPOSABLE_MARKER
# Import the stable conflict boundary expected for tombstone and reset rejection.
from casino.errors import ConflictError
# Reuse only the accepted migration lane's process, port, and runner helpers.
from tests import postgres_migration_live

# Read the official portable PostgreSQL binary root from one explicit variable.
POSTGRES_BIN = Path(os.environ.get("CASINO_POSTGRES_TEST_BIN", ""))
# Require a distinct explicit marker before this test creates any process or identity.
LIVE_MARKER = "CASINO-POSTGRES-1059-LIVE"


# Publish one fixed secret-free phase label for bounded live diagnosis.
def _phase(name: str) -> None:
    # Emit only a source-owned finite marker and flush immediately.
    print(f"PG1059-LIVE:{name}", file=sys.stderr, flush=True)


# Refuse accidental live execution before any filesystem or process mutation.
def _require_live_authorization() -> None:
    # Require the exact game-action live marker.
    if os.environ.get("CASINO_POSTGRES_GAME_ACTION_LIVE") != LIVE_MARKER:
        # Stop without naming a target or configured value.
        raise RuntimeError("PostgreSQL game-action live test is not authorized")
    # Require the same official PostgreSQL management binaries as the migration lane.
    if not all((POSTGRES_BIN / name).is_file() for name in ("postgres.exe", "initdb.exe", "pg_ctl.exe")):
        # Refuse PATH fallback or an unreviewed server installation.
        raise RuntimeError("PostgreSQL game-action live-test binaries are unavailable")


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
    # Authorize the accepted migration helper without broadening this live selector.
    environment["CASINO_POSTGRES_LIVE_TEST"] = "CASINO-POSTGRES-1057-LIVE"
    # Return caller-local configuration for the child runner.
    return environment


# Build one complete provider-neutral player row.
def _player(balance: float) -> dict:
    # Return the exact ordinary PostgreSQL player shape.
    return {"player_id": "human", "display_name": "Human", "type": "human", "balance": balance, "created_at": "2026-08-22T00:00:00+00:00", "updated_at": "2026-08-22T00:00:00+00:00", "status": "active"}


# Build one resource-bound identity without sharing mutable state.
def _identity(action_key: str, resources: GameActionResources, request: dict | None = None) -> GameActionIdentity:
    # Bind the caller key, complete resources, and canonical request into one fingerprint.
    return GameActionIdentity.create(game_id="slots", player_id="human", action_key=action_key, resources=resources, request=request or {"stake_cents": 100})


# Return one deterministic debit-and-payout plan for a live wallet and state row.
def _paid_plan(snapshot) -> GameActionPlan:
    # Read the declared state resource so a malformed snapshot still fails closed.
    snapshot.state_value("slots:human")
    # Return exact wager, payout, state, and outcome projections.
    return GameActionPlan.create(outcome={"round_id": "round-live"}, movements=(GameActionMovement(wallet_id="human", amount_cents=-100, reason="wager"), GameActionMovement(wallet_id="human", amount_cents=250, reason="payout")), state_updates={"slots:human": {"spins": 1}})


# Exercise paid, zero-cost, contention, resolver, and reset semantics on one live provider.
def _exercise_provider(port: int, role: str, password: str, database: str) -> dict:
    # Construct immutable target and pool settings reused across provider restart.
    config = PostgresConfig("127.0.0.1", port, role, password, database)
    pool_config = PostgresPoolConfig(capacity=4, checkout_wait_ms=2000, connect_timeout_seconds=5)
    # Construct the first runtime provider for fresh execution.
    selected = PostgresStorageProvider(config, pool_config)
    # Track terminal pool cleanup independently from assertions.
    pool_closed = False
    try:
        # Require the exact clean schema-five runtime prefix before state mutation.
        selected.ensure_ready()
        # Seed one real fake-money wallet through the public provider.
        selected.ensure_player(_player(10.0))
        # Declare the shared paid wallet and route-free state resource set.
        paid_resources = GameActionResources(wallet_ids=("human",), state_keys=("slots:human",))
        # Execute one fresh paid action.
        paid_identity = _identity("paid", paid_resources)
        paid_receipt, paid_replayed = selected.execute_game_action_once(identity=paid_identity, resources=paid_resources, planner=_paid_plan)
        # Require the first provider to publish a fresh action.
        if paid_replayed:
            # Reject a target that did not begin with an unused action identity.
            raise RuntimeError("PostgreSQL paid game action unexpectedly replayed")
        # Close every first-provider socket before reconstructing runtime state.
        selected.close_pool()
        # Mark the first provider closed so a reconstruction failure preserves clean ownership.
        pool_closed = True
        # Construct a distinct provider instance on the same migrated target.
        selected = PostgresStorageProvider(config, pool_config)
        # Transfer cleanup ownership to the restarted provider.
        pool_closed = False
        # Require restart readiness to reverify the exact schema-five catalog.
        selected.ensure_ready()
        # Replay after reconstruction without allowing a second planner call.
        replay_receipt, replayed = selected.execute_game_action_once(identity=paid_identity, resources=paid_resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("replay planner ran")))
        # Require one byte-semantic immutable result and exact restarted resolver commitment.
        if not replayed or replay_receipt != paid_receipt or selected.resolve_game_action(identity=paid_identity, resources=paid_resources).receipt != paid_receipt:
            # Reject replay, receipt, or resolver drift.
            raise RuntimeError("PostgreSQL paid game-action parity failed")
        # Execute and replay one state-only action with no invented ledger movement.
        zero_resources = GameActionResources(state_keys=("keno:human",))
        zero_identity = _identity("zero", zero_resources, {"view": "opened"})
        zero_receipt, zero_replayed = selected.execute_game_action_once(identity=zero_identity, resources=zero_resources, planner=lambda _snapshot: GameActionPlan.create(outcome={"ok": True}, state_updates={"keno:human": {"views": 1}}))
        zero_replay, zero_was_replayed = selected.execute_game_action_once(identity=zero_identity, resources=zero_resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("zero replay planner ran")))
        # Require exact state-only replay semantics.
        if zero_replayed or not zero_was_replayed or zero_replay != zero_receipt:
            # Reject zero-cost lifecycle drift.
            raise RuntimeError("PostgreSQL zero-cost game-action parity failed")
        # Prepare deterministic executor-owned claim contention.
        contention_identity = _identity("contention", paid_resources)
        planner_entered = threading.Event()
        planner_release = threading.Event()
        planner_calls = []
        # Hold the executing transaction after claim and resource locks are acquired.
        def contended_planner(snapshot):
            # Retain one exact planner observation.
            planner_calls.append(snapshot)
            # Signal that the claim is owned but remains uncommitted.
            planner_entered.set()
            # Bound the test-owned hold so a failed resolver cannot strand the worker.
            if not planner_release.wait(timeout=5):
                # Fail closed on orchestration drift.
                raise RuntimeError("PostgreSQL contention release was not observed")
            # Return the ordinary paid projection after the resolver has timed out.
            return _paid_plan(snapshot)
        # Use two workers so the resolver observes a real concurrent uncommitted claim.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Start the executor transaction first.
            executing = executor.submit(selected.execute_game_action_once, identity=contention_identity, resources=paid_resources, planner=contended_planner)
            # Require the planner to own the action before resolution starts.
            if not planner_entered.wait(timeout=5):
                # Refuse a synthetic or unordered contention result.
                raise RuntimeError("PostgreSQL contention planner did not start")
            # Start the resolver while the executor retains its transaction locks.
            resolving = executor.submit(selected.resolve_game_action, identity=contention_identity, resources=paid_resources)
            # Require the bounded PostgreSQL lock timeout to report pending.
            pending = resolving.result(timeout=3)
            # Allow the executor to finish only after pending is proven.
            planner_release.set()
            # Collect the single committed execution.
            contention_receipt, contention_replayed = executing.result(timeout=5)
        # Require one planner, one fresh commit, and later committed resolution.
        final_resolution = selected.resolve_game_action(identity=contention_identity, resources=paid_resources)
        if pending.status != "pending" or contention_replayed or len(planner_calls) != 1 or final_resolution.status != "committed" or final_resolution.receipt != contention_receipt:
            # Reject widened contention taxonomy or duplicate planning.
            raise RuntimeError("PostgreSQL execute-resolve contention parity failed")
        # Let the resolver win a separate immutable action key.
        tombstone_identity = _identity("resolver-first", paid_resources)
        if selected.resolve_game_action(identity=tombstone_identity, resources=paid_resources).status != "uncommitted":
            # Reject missing terminal tombstone authority.
            raise RuntimeError("PostgreSQL resolver-first parity failed")
        # Refuse later execution without invoking its planner.
        tombstone_planner_calls = []
        try:
            # Attempt to execute behind the committed resolver claim.
            selected.execute_game_action_once(identity=tombstone_identity, resources=paid_resources, planner=lambda snapshot: tombstone_planner_calls.append(snapshot))
            # Fail if execution replaced immutable resolver ownership.
            raise RuntimeError("PostgreSQL resolver-first execution was accepted")
        except ConflictError:
            # Preserve the expected fixed application boundary.
            pass
        # Require rejection before planner or mutable resource access.
        if tombstone_planner_calls:
            # Reject late planner execution behind a tombstone.
            raise RuntimeError("PostgreSQL resolver-first planner ran")
        # Reset mutable projections while retaining immutable epoch-one history.
        with selected.reset_transaction():
            # Require same-process execution rejection before checkout.
            try:
                # Attempt the existing paid key during unavailable reset phase.
                selected.execute_game_action_once(identity=paid_identity, resources=paid_resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("reset planner ran")))
                # Fail if reset permitted an executor.
                raise RuntimeError("PostgreSQL reset execution was accepted")
            except ConflictError:
                # Preserve the expected application conflict.
                pass
            # Require resolver pending without publishing a claim.
            if selected.resolve_game_action(identity=paid_identity, resources=paid_resources).status != "pending":
                # Reject visibility during reset bootstrap.
                raise RuntimeError("PostgreSQL reset resolver was not pending")
            # Bootstrap the fresh mutable wallet through the retained reset lease.
            selected.bootstrap_players({"players": [_player(20.0)]})
        # Reuse the exact caller key as fresh work only after epoch two is ready.
        epoch_two_receipt, epoch_two_replayed = selected.execute_game_action_once(identity=paid_identity, resources=paid_resources, planner=_paid_plan)
        # Require a fresh action distinct from epoch-one snapshot authority.
        if epoch_two_replayed or epoch_two_receipt == paid_receipt:
            # Reject cross-epoch replay or receipt collapse.
            raise RuntimeError("PostgreSQL reset epoch reuse failed")
        # Inspect bounded immutable and mutable evidence on one read-only transaction.
        with selected._database_cursor() as (_connection, cursor):
            # Count claims, receipts, ledger rows, and current wallet balance.
            cursor.execute("SELECT (SELECT count(*) FROM casino_game_action_claims) AS claims, (SELECT count(*) FROM casino_game_action_receipts) AS receipts, (SELECT count(*) FROM casino_ledger) AS ledger, (SELECT balance FROM casino_players WHERE player_id = %s) AS balance", ("human",))
            # Retain the exact bounded result.
            counts = cursor.fetchone()
            # Read immutable receipt epoch ownership.
            cursor.execute("SELECT reset_epoch FROM casino_game_action_receipts ORDER BY reset_epoch, action_key")
            # Collect only bounded epoch integers.
            receipt_epochs = [row["reset_epoch"] for row in cursor.fetchall()]
        # Require retained prior receipts, one fresh receipt, and reset-cleared mutable rows.
        if counts != {"claims": 5, "receipts": 4, "ledger": 2, "balance": counts["balance"]} or str(counts["balance"]) != "21.50" or receipt_epochs.count(1) != 3 or receipt_epochs.count(2) != 1:
            # Reject immutable-history, cleanup, or wallet projection drift.
            raise RuntimeError("PostgreSQL reset history evidence is invalid")
        # Close all provider-owned sockets before target teardown.
        selected.close_pool()
        # Record terminal pool ownership for unconditional cleanup.
        pool_closed = True
        # Require zero active or idle pool capacity after shutdown.
        snapshot = selected.pool_snapshot()
        if snapshot["idle"] != 0 or snapshot["in_use"] != 0:
            # Reject socket residue before database removal.
            raise RuntimeError("PostgreSQL game-action pool cleanup was incomplete")
        # Return bounded source-owned evidence only.
        return {"schema_version": 5, "paid": True, "restart_replay": True, "zero_cost": True, "execute_resolve_pending": True, "resolver_first": True, "planner_calls": 1, "reset_epoch_reuse": True, "receipt_epochs": {"one": 3, "two": 1}, "pool_closed": True}
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
    cluster_root = Path(tempfile.mkdtemp(prefix="casino-postgres-1059-"))
    # Resolve database data and log paths inside the verified root.
    data_root, log_path = cluster_root / "data", cluster_root / "postgres.log"
    # Generate bounded target identities ending in the migration policy's suffix.
    nonce = secrets.token_hex(4)
    # Name the fresh disposable role and database.
    role, database = f"casino_action_{nonce}_1057", f"casino_action_{nonce}_1057"
    # Generate process-local database and target-binding secrets.
    password, binding_key = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    # Reserve one currently free private loopback port.
    port = postgres_migration_live._loopback_port()
    # Track process and target state for unconditional cleanup.
    started, target_created = False, False
    # Initialize sanitized terminal evidence.
    evidence = {}
    try:
        # Initialize one official PostgreSQL 16 cluster with local trust.
        postgres_migration_live._postgres_command([str(POSTGRES_BIN / "initdb.exe"), "-D", str(data_root), "-A", "trust", "-U", "casino_admin_1059", "--encoding=UTF8", "--no-locale"])
        # Start only a literal-loopback disposable listener.
        postgres_migration_live._postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-l", str(log_path), "-o", f"-p {port} -h 127.0.0.1 -F", "-w", "start"])
        # Record the active process before opening an administrator connection.
        started = True
        # Report private listener readiness.
        _phase("cluster_started")
        # Connect only to the fresh cluster default database.
        admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1059", dbname="postgres", autocommit=True, connect_timeout=5)
        try:
            # Open one autocommit cursor for safe target creation.
            cursor = admin.cursor()
            # Prove both generated identities were absent before creation.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Refuse adoption of any pre-existing target.
            if cursor.fetchone() != (0, 0):
                # Stop before ambiguous create or drop.
                raise RuntimeError("PostgreSQL game-action target already exists")
            # Create the fresh login role and owned database through safe composition.
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(database), sql.Identifier(role)))
            # Authorize cleanup only after both process-created identities exist.
            target_created = True
        finally:
            # Release administrator state after target creation.
            admin.close()
        # Apply the accepted immutable five-version migration catalog.
        applied = postgres_migration_live._runner("apply", _migration_environment(port, role, password, database, binding_key))
        # Require exact clean schema-five completion.
        if (applied.get("current_version"), applied.get("status")) != (5, "clean"):
            # Refuse runtime access to a partial catalog.
            raise RuntimeError("PostgreSQL game-action migration failed")
        # Exercise the real composed provider against the migrated target.
        evidence = _exercise_provider(port, role, password, database)
        # Report complete game-action evidence before teardown.
        _phase("game_actions_validated")
        # Reopen only the private cluster's default database for exact teardown.
        admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1059", dbname="postgres", autocommit=True, connect_timeout=5)
        try:
            # Open one exact teardown cursor.
            cursor = admin.cursor()
            # Terminate only sockets bound to the process-created database.
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
            # Drop only the process-created database and role.
            cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            # Verify exact zero identity residue.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (role, database))
            # Require complete cleanup before clearing ownership.
            if cursor.fetchone() != (0, 0):
                # Refuse false cleanup evidence.
                raise RuntimeError("PostgreSQL game-action target cleanup was incomplete")
            # Prevent duplicate outer drop attempts.
            target_created = False
        finally:
            # Release teardown administrator state.
            admin.close()
        # Record exact identity cleanup without names.
        evidence["target_residue"] = {"roles": 0, "databases": 0}
    finally:
        # Attempt identity cleanup only for a process-created live target.
        if target_created and started:
            # Preserve the primary failure across best-effort teardown.
            try:
                # Open the fresh cluster administrator database only.
                admin = psycopg.connect(host="127.0.0.1", port=port, user="casino_admin_1059", dbname="postgres", autocommit=True, connect_timeout=3)
                # Terminate and drop only generated identities.
                cursor = admin.cursor()
                cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
                # Release cleanup connector state.
                admin.close()
            except Exception:
                # Retain no target or connector detail while process cleanup continues.
                pass
        # Stop the private PostgreSQL process when active.
        if started:
            # Request bounded fast shutdown before deleting files.
            try:
                # Stop the exact process owning this private data directory.
                postgres_migration_live._postgres_command([str(POSTGRES_BIN / "pg_ctl.exe"), "-D", str(data_root), "-m", "fast", "-w", "stop"])
            except Exception:
                # Preserve primary evidence while cleanup continues.
                pass
        # Verify deletion remains confined to the allocated issue root.
        safe_root = cluster_root.parent == Path(tempfile.gettempdir()) and cluster_root.name.startswith("casino-postgres-1059-")
        # Remove only the verified private cluster tree.
        if safe_root:
            # Delete data and logs after listener shutdown.
            shutil.rmtree(cluster_root, ignore_errors=True)
        # Report completion of the bounded cleanup attempt.
        _phase("cleanup_attempted")
    # Require complete filesystem cleanup after every successful lifecycle.
    if cluster_root.exists():
        # Refuse false zero-residue evidence.
        raise RuntimeError("PostgreSQL game-action cluster cleanup was incomplete")
    # Record exact filesystem zero residue.
    evidence["cluster_root_removed"] = True
    # Print one bounded sorted evidence record.
    print(json.dumps(evidence, sort_keys=True))
    # Return standard success after target, pool, and filesystem cleanup.
    return 0


# Execute the live lifecycle only when directly selected.
if __name__ == "__main__":
    # Exit with the stable game-action live result.
    raise SystemExit(main())
