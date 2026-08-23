# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Disposable relational harnesses for the unchanged A-J storage contract. (TEST-257)"""

from __future__ import annotations

# Import dynamic loading so optional database drivers remain absent from default runs.
import importlib
# Import environment access for explicit disposable-service authorization.
import os
# Import portable paths for the private PostgreSQL cluster and reviewed binaries.
from pathlib import Path
# Import safe entropy for test-only database, role, account, and password identities.
import secrets
# Import bounded process execution for PostgreSQL emergency shutdown.
import subprocess
# Import temporary-root allocation outside the repository.
import tempfile
# Import structural values without importing either concrete provider module.
from typing import Any
# Import restoring environment patches around the public storage factory.
from unittest import mock

# Import only the provider-neutral storage facade used by all harness construction.
from casino.core import storage as storage_facade
# Import the public provider contract returned to the unchanged cases.
from casino.core.storage.base import StorageProvider


# Require the established disposable-MySQL service authorization marker.
MYSQL_MARKER_NAME = "CASINO_MYSQL_DISPOSABLE_TEST"
# Require the same literal value used by the accepted MySQL live matrix.
MYSQL_MARKER_VALUE = "1"
# Require a distinct opt-in before starting any PostgreSQL process.
POSTGRES_MARKER_NAME = "CASINO_POSTGRES_CONFORMANCE_LIVE"
# Bind the process authorization to this conformance lane.
POSTGRES_MARKER_VALUE = "CASINO-POSTGRES-1060-LIVE"
# Name the official PostgreSQL binary-root variable shared by accepted live gates.
POSTGRES_BIN_NAME = "CASINO_POSTGRES_TEST_BIN"
# Keep all absence outcomes value-free and provider-neutral.
ABSENT_REASON = "reviewed disposable reachability variables are absent"


# Build one provider through the selector facade while restoring every environment value.
def _provider_from_environment(environment: dict[str, str]) -> StorageProvider:
    """Construct one uncached provider through the reviewed storage factory."""

    # Apply target and credential values only for synchronous provider construction.
    with mock.patch.dict(os.environ, environment, clear=False):
        # Avoid the process-global provider cache so harnesses own exact lifecycle cleanup.
        provider = storage_facade._build_provider()
    # Return the provider whose immutable configuration retained the synthetic target.
    return provider


# Close a relational provider pool without imposing that extension on the base protocol.
def _close_provider(provider: StorageProvider | None) -> None:
    """Close an optional provider-owned pool exactly once."""

    # Stop when setup failed before provider construction.
    if provider is None:
        # Preserve the original create or case failure.
        return
    # Resolve the relational lifecycle hook without a concrete-provider import.
    close_pool = getattr(provider, "close_pool", None)
    # Release every idle or checked-in connection when the hook is available.
    if callable(close_pool):
        # Delegate exact shutdown semantics to the selected provider.
        close_pool()


class MySQLHarness:
    """Own one schema-five database and two synthetic accounts on a disposable service."""

    # Publish the stable registry identity used in timing output.
    name = "mysql"
    # Enforce the issue's complete local disposable-provider budget.
    budget_seconds = 60.0
    # Exercise the full sixteen-operation thread waves against InnoDB.
    supports_true_concurrency = True

    def __init__(self) -> None:
        # Retain only a provider owned by this harness.
        self._provider: StorageProvider | None = None
        # Retain the disposable-service administrator connection for teardown.
        self._admin: Any | None = None
        # Retain the lazily imported live helper only after explicit authorization.
        self._live: Any | None = None
        # Track whether generated identities were proven absent before ownership.
        self._identities_owned = False
        # Generate bounded identifiers accepted by the existing MySQL fixture policy.
        nonce = secrets.token_hex(4)
        # Bind the database to the mandatory disposable suffix.
        self._database = f"casino_conf_{nonce}_204"
        # Create one schema-management identity separate from runtime access.
        self._migrator_user = f"casino_conf_m_{nonce}_204"
        # Create one least-privilege runtime identity.
        self._runtime_user = f"casino_conf_r_{nonce}_204"
        # Generate a migration-only secret that is never printed or persisted.
        self._migrator_password = secrets.token_urlsafe(32)
        # Generate an independent runtime secret.
        self._runtime_password = secrets.token_urlsafe(32)
        # Generate an independent migration target-binding key.
        self._binding_key = secrets.token_urlsafe(48)

    @property
    def root(self) -> None:
        """Return no filesystem root because this harness owns database identities."""

        # Let common cleanup assertions rely on exact database teardown instead.
        return None

    def unavailable_reason(self) -> str | None:
        """Skip only when the explicit disposable-service marker is wholly absent."""

        # Read only the finite authorization marker, never any credential.
        marker = os.environ.get(MYSQL_MARKER_NAME)
        # Treat a wholly absent marker as an ordinary unavailable local service.
        if marker is None:
            # Return one value-free skip category.
            return ABSENT_REASON
        # Reject present but incorrect authorization rather than skipping configuration drift.
        if marker != MYSQL_MARKER_VALUE:
            # Stop before importing a driver or reading an administrator secret.
            raise AssertionError("Disposable MySQL conformance authorization is invalid")
        # Require execution because an exact marker was supplied.
        return None

    def _admin_kwargs(self) -> dict[str, Any]:
        """Validate the reviewed loopback administrator endpoint without exposing values."""

        # Read required fields only after exact disposable authorization.
        host = str(os.environ.get("CASINO_MYSQL_TEST_ADMIN_HOST", "")).strip()
        # Read the synthetic administrator identity without logging it.
        user = str(os.environ.get("CASINO_MYSQL_TEST_ADMIN_USER", "")).strip()
        # Read the synthetic administrator secret without formatting it.
        password = str(os.environ.get("CASINO_MYSQL_TEST_ADMIN_PASSWORD", ""))
        # Read the port as text for one fixed conversion boundary.
        raw_port = str(os.environ.get("CASINO_MYSQL_TEST_ADMIN_PORT", "")).strip()
        # Reject incomplete settings before optional-driver import or network access.
        if host != "127.0.0.1" or not user or not password or not raw_port:
            # Publish no endpoint, account, secret, or missing-field name.
            raise AssertionError("Disposable MySQL conformance reachability is incomplete")
        try:
            # Parse only the reviewed loopback port.
            port = int(raw_port)
        except ValueError:
            # Collapse malformed text into the same value-free boundary.
            raise AssertionError("Disposable MySQL conformance reachability is incomplete") from None
        # Reject every value outside the complete TCP-port range.
        if not 1 <= port <= 65535:
            # Keep the error independent of the rejected port.
            raise AssertionError("Disposable MySQL conformance reachability is incomplete")
        # Return connector keywords only to the explicitly enabled create path.
        return {"host": host, "port": port, "user": user, "password": password}

    def _runtime_environment(self, admin_kwargs: dict[str, Any]) -> dict[str, str]:
        """Build isolated migration and runtime settings for the generated target."""

        # Normalize the validated port once for both identities.
        port = str(admin_kwargs["port"])
        # Return one caller-local map that is restored after construction.
        return {
            "CASINO_STORAGE_PROVIDER": "mysql",
            "CASINO_MYSQL_HOST": "127.0.0.1",
            "CASINO_MYSQL_PORT": port,
            "CASINO_MYSQL_USER": self._runtime_user,
            "CASINO_MYSQL_PASSWORD": self._runtime_password,
            "CASINO_MYSQL_DATABASE": self._database,
            "CASINO_MYSQL_POOL_SIZE": "16",
            "CASINO_MYSQL_POOL_WAIT_MS": "500",
            "CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS": "3",
            "CASINO_MYSQL_MIGRATION_HOST": "127.0.0.1",
            "CASINO_MYSQL_MIGRATION_PORT": port,
            "CASINO_MYSQL_MIGRATION_USER": self._migrator_user,
            "CASINO_MYSQL_MIGRATION_PASSWORD": self._migrator_password,
            "CASINO_MYSQL_MIGRATION_DATABASE": self._database,
            "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY": self._binding_key,
        }

    def _require_absent_identities(self, cursor: Any) -> None:
        """Refuse adoption or deletion of any pre-existing database or account."""

        # Count only the exact generated database name through a bound value.
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (self._database,))
        # Retain the database absence result before the next query.
        database_count = int(cursor.fetchone()[0])
        # Count only the two generated account names through bound values.
        cursor.execute("SELECT COUNT(*) FROM mysql.user WHERE User IN (%s, %s)", (self._migrator_user, self._runtime_user))
        # Reject any identity that this process did not create.
        if database_count != 0 or int(cursor.fetchone()[0]) != 0:
            # Stop before any DROP or CREATE statement.
            raise AssertionError("Disposable MySQL conformance target already exists")

    def _prepare_target(self, cursor: Any) -> None:
        """Create the isolated database and separate migration/runtime accounts."""

        # Record ownership after exact absence proof so partial setup remains safely removable.
        self._identities_owned = True
        # Create one utf8mb4 schema using the validated generated identifier.
        cursor.execute(f"CREATE DATABASE `{self._database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        # Create the migration account with a bound generated password.
        cursor.execute(f"CREATE USER '{self._migrator_user}'@'%' IDENTIFIED BY %s", (self._migrator_password,))
        # Create the distinct runtime account with its independent password.
        cursor.execute(f"CREATE USER '{self._runtime_user}'@'%' IDENTIFIED BY %s", (self._runtime_password,))
        # Grant schema setup only to the migration identity.
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{self._database}`.* TO '{self._migrator_user}'@'%'")

    def _grant_runtime(self, cursor: Any) -> None:
        """Grant only the accepted schema-five runtime operations."""

        # Permit checksum readiness and all current row-locking reads.
        cursor.execute(f"GRANT SELECT ON `{self._database}`.* TO '{self._runtime_user}'@'%'")
        # Grant ordinary DML only on mutable runtime tables.
        for table in ("casino_players", "casino_ledger", "casino_history", "casino_documents", "casino_sessions"):
            # Preserve least privilege while supporting the complete reset contract.
            cursor.execute(f"GRANT INSERT, UPDATE, DELETE ON `{self._database}`.`{table}` TO '{self._runtime_user}'@'%'")
        # Permit immutable game-action claims and receipts after #1059 composition.
        for table in ("casino_game_action_claims", "casino_game_action_receipts"):
            # Exclude update and delete authority from append-only evidence.
            cursor.execute(f"GRANT INSERT ON `{self._database}`.`{table}` TO '{self._runtime_user}'@'%'")
        # Permit only the singleton reset-epoch compare-and-set update.
        cursor.execute(f"GRANT UPDATE ON `{self._database}`.`casino_game_action_epoch_state` TO '{self._runtime_user}'@'%'")

    def create(self) -> StorageProvider:
        """Create, migrate, grant, and open one isolated MySQL provider."""

        # Reject duplicate lifecycle entry before reading configuration.
        if self._provider is not None or self._admin is not None:
            # Preserve one harness as the sole owner of its generated identities.
            raise AssertionError("MySQL conformance harness create must run exactly once")
        # Refuse accidental execution when the disposable marker is absent.
        if self.unavailable_reason() is not None:
            # The registered runner normally converts this state into an explicit skip.
            raise AssertionError("Disposable MySQL conformance service is unavailable")
        # Validate the complete endpoint before importing mysql.connector.
        admin_kwargs = self._admin_kwargs()
        # Load the accepted live helper only inside the authorized path.
        self._live = importlib.import_module("tests.mysql_migration_live")
        # Resolve its lazy optional connector after every safety check passed.
        connector = self._live._connector()
        # Open one administrator connection solely to the disposable loopback service.
        self._admin = connector.connect(**admin_kwargs)
        # Open one cursor for absence proof, isolated setup, and grants.
        cursor = self._admin.cursor()
        # Refuse ambiguous ownership before any mutation.
        self._require_absent_identities(cursor)
        # Create only the generated target identities.
        self._prepare_target(cursor)
        # Commit identity setup before connecting as the migrator.
        self._admin.commit()
        # Build environment values without publishing them process-wide beyond each patch.
        environment = self._runtime_environment(admin_kwargs)
        # Select the generated migration identity while building its immutable config.
        with mock.patch.dict(os.environ, environment, clear=False):
            # Reuse the accepted identifier validation and migration config seam.
            migration_config = self._live._migration_config(self._database)
            # Open the generated schema-management connection.
            migration_connection = connector.connect(**migration_config.kwargs())
            try:
                # Load the immutable accepted catalog.
                migrations, _expected, _digest, _source = self._live.mysql_migrations.load_catalog()
                # Seed the exact checksum-verified schema-five prefix through the test fixture seam.
                self._live._seed_catalog_prefix(migration_connection, migrations, 5)
            finally:
                # Release every migrator-owned connector resource.
                migration_connection.close()
        # Grant runtime operations only after complete schema creation.
        self._grant_runtime(cursor)
        # Commit least-privilege runtime grants before provider construction.
        self._admin.commit()
        # Construct the runtime provider through the selector facade without caching secrets.
        self._provider = _provider_from_environment(environment)
        # Verify exact schema-five readiness before returning the contract.
        self._provider.ensure_ready()
        # Return only the provider-neutral interface to unchanged cases.
        return self._provider

    def reset_fast(self) -> StorageProvider:
        """Reset mutable MySQL state without recreating schema or accounts."""

        # Require successful target creation before each group boundary.
        if self._provider is None:
            # Reject reset calls after partial or destroyed setup.
            raise AssertionError("MySQL conformance reset requires a created provider")
        # Reuse the production reset lifecycle and accepted epoch semantics.
        self._provider.reset()
        # Reconfirm cached runtime readiness without migration authority.
        self._provider.ensure_ready()
        # Return the retained provider for the next unchanged group.
        return self._provider

    def destroy(self) -> None:
        """Close the pool and remove every generated MySQL identity."""

        # Release runtime connections before attempting database deletion.
        _close_provider(self._provider)
        # Clear the provider reference even when later cleanup fails.
        self._provider = None
        # Preserve the administrator connection needed for exact teardown.
        admin = self._admin
        # Clear the retained field before connector cleanup can raise.
        self._admin = None
        try:
            # Skip database teardown only when setup never proved ownership.
            if admin is not None and self._identities_owned:
                # Open one administrator cursor on the disposable service.
                cursor = admin.cursor()
                # Drop only the generated database proven absent before setup.
                cursor.execute(f"DROP DATABASE IF EXISTS `{self._database}`")
                # Drop only the generated migration account.
                cursor.execute(f"DROP USER IF EXISTS '{self._migrator_user}'@'%'")
                # Drop only the generated runtime account.
                cursor.execute(f"DROP USER IF EXISTS '{self._runtime_user}'@'%'")
                # Commit complete identity removal.
                admin.commit()
                # Verify the database no longer exists.
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (self._database,))
                # Retain the database residue count before account verification.
                database_count = int(cursor.fetchone()[0])
                # Verify neither generated account remains.
                cursor.execute("SELECT COUNT(*) FROM mysql.user WHERE User IN (%s, %s)", (self._migrator_user, self._runtime_user))
                # Fail closed on any task-owned residue.
                if database_count != 0 or int(cursor.fetchone()[0]) != 0:
                    # Publish no identifier, endpoint, account, or secret.
                    raise AssertionError("Disposable MySQL conformance cleanup was incomplete")
        finally:
            # Release the administrator connector after every outcome.
            if admin is not None:
                # Close the exact test-owned physical connection.
                admin.close()
            # Prevent a later destroy call from deleting unowned identities.
            self._identities_owned = False


class PostgresHarness:
    """Own one private PostgreSQL 16 process, database, role, and provider."""

    # Publish the stable registry identity used in timing output.
    name = "postgres"
    # Enforce the issue's complete local disposable-provider budget.
    budget_seconds = 60.0
    # Exercise the full sixteen-operation thread waves against PostgreSQL locks.
    supports_true_concurrency = True

    def __init__(self) -> None:
        # Retain only a provider owned by this harness.
        self._provider: StorageProvider | None = None
        # Allocate no filesystem or listener until explicit create authorization.
        self._root: Path | None = None
        # Retain the private data directory for bounded process management.
        self._data_root: Path | None = None
        # Retain the reviewed binary root after validation.
        self._bin: Path | None = None
        # Retain lazy live helpers only after authorization.
        self._live: Any | None = None
        # Retain psycopg and safe SQL helpers for exact teardown.
        self._driver: Any | None = None
        self._sql: Any | None = None
        # Track the process and generated identity ownership independently.
        self._started = False
        # Track whether absence proof authorized database and role removal.
        self._identities_owned = False
        # Generate accepted migration-suffix identities without reading host state.
        nonce = secrets.token_hex(4)
        # Bind the role to the migration lane's mandatory disposable suffix.
        self._role = f"casino_conf_{nonce}_1057"
        # Bind the database to the same exact disposable suffix.
        self._database = f"casino_conf_{nonce}_1057"
        # Generate a process-local runtime/migration password.
        self._password = secrets.token_urlsafe(32)
        # Generate a separate migration target-binding key.
        self._binding_key = secrets.token_urlsafe(48)
        # Reserve no network endpoint until create starts the private cluster.
        self._port: int | None = None

    @property
    def root(self) -> Path | None:
        """Expose only the harness-owned private root for cleanup assertions."""

        # Return no credential, target identity, or server log contents.
        return self._root

    def unavailable_reason(self) -> str | None:
        """Skip only when the explicit process authorization marker is absent."""

        # Read only the finite lane marker, never any database configuration.
        marker = os.environ.get(POSTGRES_MARKER_NAME)
        # Treat a wholly absent marker as an ordinary unavailable local harness.
        if marker is None:
            # Return the same value-free category used for MySQL.
            return ABSENT_REASON
        # Reject a present but incorrect marker instead of silently skipping drift.
        if marker != POSTGRES_MARKER_VALUE:
            # Stop before reading a binary path or importing psycopg.
            raise AssertionError("Disposable PostgreSQL conformance authorization is invalid")
        # Require execution because exact authorization was supplied.
        return None

    def _validated_bin(self) -> Path:
        """Require the explicit official binary root before process creation."""

        # Resolve only the dedicated live-test variable after authorization.
        raw_path = str(os.environ.get(POSTGRES_BIN_NAME, "")).strip()
        # Reject missing binary configuration without PATH fallback.
        if not raw_path:
            # Publish no host filesystem path.
            raise AssertionError("Disposable PostgreSQL conformance reachability is incomplete")
        # Resolve the candidate root for exact executable checks.
        binary_root = Path(raw_path).resolve()
        # Require every management executable used by the lifecycle.
        if not all((binary_root / name).is_file() for name in ("postgres.exe", "initdb.exe", "pg_ctl.exe")):
            # Refuse an incomplete or unreviewed toolchain.
            raise AssertionError("Disposable PostgreSQL conformance reachability is incomplete")
        # Return the exact reviewed root without logging it.
        return binary_root

    def _runtime_environment(self) -> dict[str, str]:
        """Build isolated migration and runtime settings for the private target."""

        # Require a reserved private port before configuration construction.
        if self._port is None:
            # Reject internal lifecycle misuse with no endpoint detail.
            raise AssertionError("PostgreSQL conformance target is not initialized")
        # Normalize the private port once for both identities.
        port = str(self._port)
        # Import the fixed migration marker only inside the authorized live path.
        migration_marker = importlib.import_module("casino.core.postgres_migrations").DISPOSABLE_MARKER
        # Return one caller-local map restored after factory and runner use.
        return {
            "CASINO_STORAGE_PROVIDER": "postgres",
            "CASINO_POSTGRES_HOST": "127.0.0.1",
            "CASINO_POSTGRES_PORT": port,
            "CASINO_POSTGRES_USER": self._role,
            "CASINO_POSTGRES_PASSWORD": self._password,
            "CASINO_POSTGRES_DATABASE": self._database,
            "CASINO_POSTGRES_POOL_SIZE": "16",
            "CASINO_POSTGRES_POOL_WAIT_MS": "500",
            "CASINO_POSTGRES_CONNECT_TIMEOUT_SECONDS": "3",
            "CASINO_POSTGRES_MIGRATION_HOST": "127.0.0.1",
            "CASINO_POSTGRES_MIGRATION_PORT": port,
            "CASINO_POSTGRES_MIGRATION_USER": self._role,
            "CASINO_POSTGRES_MIGRATION_PASSWORD": self._password,
            "CASINO_POSTGRES_MIGRATION_DATABASE": self._database,
            "CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY": self._binding_key,
            "CASINO_POSTGRES_MIGRATION_DISPOSABLE": migration_marker,
        }

    def _admin_connection(self, *, timeout: int) -> Any:
        """Open the private cluster's synthetic administrator connection."""

        # Require driver, port, and started process before any connector access.
        if self._driver is None or self._port is None or not self._started:
            # Reject partial lifecycle access without target detail.
            raise AssertionError("PostgreSQL conformance administrator is unavailable")
        # Connect only to the process-created literal-loopback cluster.
        return self._driver.connect(host="127.0.0.1", port=self._port, user="casino_admin_1060", dbname="postgres", autocommit=True, connect_timeout=timeout)

    def _create_target(self) -> None:
        """Create one generated role and database after exact absence proof."""

        # Open one private administrator connection for nontransactional DDL.
        admin = self._admin_connection(timeout=5)
        try:
            # Open one autocommit cursor against only the private cluster.
            cursor = admin.cursor()
            # Prove both generated identities were absent before ownership.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (self._role, self._database))
            # Reject adoption of any unexpected pre-existing identity.
            if tuple(cursor.fetchone()) != (0, 0):
                # Stop before CREATE or later DROP authority.
                raise AssertionError("Disposable PostgreSQL conformance target already exists")
            # Record safe ownership so partial DDL remains removable.
            self._identities_owned = True
            # Create the generated login role through driver-safe identifier/literal composition.
            cursor.execute(self._sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(self._sql.Identifier(self._role), self._sql.Literal(self._password)))
            # Create the generated database owned only by the synthetic role.
            cursor.execute(self._sql.SQL("CREATE DATABASE {} OWNER {}").format(self._sql.Identifier(self._database), self._sql.Identifier(self._role)))
        finally:
            # Release administrator connector state after setup.
            admin.close()

    def create(self) -> StorageProvider:
        """Start, migrate, and open one isolated PostgreSQL provider."""

        # Reject duplicate lifecycle entry before reading configuration.
        if self._provider is not None or self._root is not None:
            # Preserve one harness as the sole owner of its cluster.
            raise AssertionError("PostgreSQL conformance harness create must run exactly once")
        # Refuse accidental process creation when the exact marker is absent.
        if self.unavailable_reason() is not None:
            # The registered runner normally converts this state into an explicit skip.
            raise AssertionError("Disposable PostgreSQL conformance service is unavailable")
        # Validate the complete reviewed binary root before optional-driver import.
        self._bin = self._validated_bin()
        # Import psycopg only after explicit authorization and binary validation.
        self._driver = importlib.import_module("psycopg")
        # Import driver-safe SQL composition beside the exact driver.
        self._sql = importlib.import_module("psycopg.sql")
        # Load accepted private-cluster and migration-runner helpers lazily.
        self._live = importlib.import_module("tests.postgres_migration_live")
        # Allocate one unique root under the system temporary directory.
        self._root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Keep data and logs confined to the verified task-owned root.
        self._data_root = self._root / "data"
        # Reserve one currently free literal-loopback port.
        self._port = self._live._loopback_port()
        # Initialize only the private PostgreSQL 16 cluster.
        self._live._postgres_command([str(self._bin / "initdb.exe"), "-D", str(self._data_root), "-A", "trust", "-U", "casino_admin_1060", "--encoding=UTF8", "--no-locale"])
        # Start one listener on literal loopback with durability disabled for disposable speed.
        self._live._postgres_command([str(self._bin / "pg_ctl.exe"), "-D", str(self._data_root), "-l", str(self._root / "postgres.log"), "-o", f"-p {self._port} -h 127.0.0.1 -F", "-w", "start"])
        # Record active process ownership before target creation.
        self._started = True
        # Create only the generated role and database.
        self._create_target()
        # Build exact migration and runtime settings after target creation.
        environment = self._runtime_environment()
        # Apply the accepted immutable catalog through its real migration runner.
        applied = self._live._runner("apply", {**os.environ, **environment})
        # Require exact clean schema-five completion before provider construction.
        if (applied.get("current_version"), applied.get("status")) != (5, "clean"):
            # Refuse provider access to partial, dirty, old, or future state.
            raise AssertionError("Disposable PostgreSQL conformance migration failed")
        # Construct the provider through the lazy selector facade.
        self._provider = _provider_from_environment(environment)
        # Verify checksum-bound schema readiness on the runtime identity.
        self._provider.ensure_ready()
        # Return only the provider-neutral interface to unchanged cases.
        return self._provider

    def reset_fast(self) -> StorageProvider:
        """Reset mutable PostgreSQL state without recreating schema or process."""

        # Require successful target creation before each group boundary.
        if self._provider is None:
            # Reject reset calls after partial or destroyed setup.
            raise AssertionError("PostgreSQL conformance reset requires a created provider")
        # Reuse the production two-phase reset and epoch recovery contract.
        self._provider.reset()
        # Reconfirm cached runtime readiness without migration authority.
        self._provider.ensure_ready()
        # Return the retained provider for the next unchanged group.
        return self._provider

    def _drop_identities(self) -> None:
        """Remove and verify only the generated database and role."""

        # Skip target DDL when setup never proved safe ownership.
        if not self._identities_owned or not self._started:
            # Preserve the active process for independent stop cleanup.
            return
        # Open one private administrator connector for exact teardown.
        admin = self._admin_connection(timeout=3)
        try:
            # Open one autocommit cursor on the private default database.
            cursor = admin.cursor()
            # Terminate only sessions bound to the generated database.
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (self._database,))
            # Drop only the process-generated database.
            cursor.execute(self._sql.SQL("DROP DATABASE IF EXISTS {}").format(self._sql.Identifier(self._database)))
            # Drop only the process-generated role.
            cursor.execute(self._sql.SQL("DROP ROLE IF EXISTS {}").format(self._sql.Identifier(self._role)))
            # Verify exact zero database and role residue.
            cursor.execute("SELECT (SELECT count(*) FROM pg_roles WHERE rolname = %s), (SELECT count(*) FROM pg_database WHERE datname = %s)", (self._role, self._database))
            # Fail closed if either generated identity remains.
            if tuple(cursor.fetchone()) != (0, 0):
                # Publish no role, database, port, path, or credential.
                raise AssertionError("Disposable PostgreSQL conformance cleanup was incomplete")
            # Prevent repeated removal after verified cleanup.
            self._identities_owned = False
        finally:
            # Release the teardown administrator connector.
            admin.close()

    def _stop_cluster(self) -> None:
        """Stop the exact private process with one bounded fallback."""

        # Stop when create failed before process startup.
        if not self._started or self._live is None or self._bin is None or self._data_root is None:
            # Preserve filesystem cleanup for a partially initialized root.
            return
        try:
            # Request a bounded fast stop before removing any data files.
            self._live._postgres_command([str(self._bin / "pg_ctl.exe"), "-D", str(self._data_root), "-m", "fast", "-w", "stop"])
        except Exception:
            # Fall back to immediate stop only for this verified private cluster.
            subprocess.run([str(self._bin / "pg_ctl.exe"), "-D", str(self._data_root), "-m", "immediate", "-w", "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=False)
        finally:
            # Prevent any later cleanup from assuming an active owned listener.
            self._started = False

    def destroy(self) -> None:
        """Close, drop, stop, and delete every PostgreSQL harness resource."""

        # Release runtime sessions before database termination and deletion.
        _close_provider(self._provider)
        # Clear the provider reference even when later cleanup fails.
        self._provider = None
        # Preserve the root for verified deletion and final residue assertion.
        root = self._root
        # Track the first cleanup failure while still attempting process and file teardown.
        cleanup_failure: BaseException | None = None
        try:
            # Remove generated database and role while the private cluster is active.
            self._drop_identities()
        except BaseException as error:
            # Retain only the first failure identity through remaining cleanup.
            cleanup_failure = error
        try:
            # Stop the exact process before deleting its data directory.
            self._stop_cluster()
        except BaseException as error:
            # Preserve an earlier identity-cleanup failure when one exists.
            if cleanup_failure is None:
                # Retain the process-stop failure for terminal reporting.
                cleanup_failure = error
        # Resolve the system temporary root once for containment validation.
        temp_root = Path(tempfile.gettempdir()).resolve()
        # Delete only a correctly prefixed direct child allocated by this harness.
        safe_root = root is not None and root.parent == temp_root and root.name.startswith("storage-conformance-postgres-")
        # Remove the private cluster tree after process-stop attempts.
        if safe_root:
            # Import filesystem deletion only at the exact bounded cleanup site.
            import shutil
            # Delete every private data and log byte.
            shutil.rmtree(root, ignore_errors=True)
        # Clear lifecycle fields so repeat destroy is non-destructive.
        self._root = None
        self._data_root = None
        self._bin = None
        self._live = None
        self._driver = None
        self._sql = None
        self._port = None
        # Require complete filesystem cleanup even after a successful database drop.
        if root is not None and root.exists() and cleanup_failure is None:
            # Publish no local path.
            cleanup_failure = AssertionError("Disposable PostgreSQL conformance cleanup was incomplete")
        # Surface the first cleanup failure after every bounded cleanup attempt.
        if cleanup_failure is not None:
            # Preserve its identity for the common lifecycle runner.
            raise cleanup_failure
