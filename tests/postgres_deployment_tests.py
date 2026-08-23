# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Govern PostgreSQL production bootstrap, runtime checks, and grant templates."""

# Import output capture for secret-safe command assertions.
from contextlib import redirect_stdout
# Import environment access for explicit provider-selection tests.
import os
# Import in-memory text streams for bounded JSON output.
from io import StringIO
# Import portable paths for exact deployment-template inspection.
from pathlib import Path
# Import simple immutable result records for verifier fakes.
from types import SimpleNamespace
# Import dependency-free unit-test support.
import unittest
# Import deterministic call replacement for connector and verifier seams.
from unittest import mock

# Import the runtime target configuration used by the deployment check.
from casino.core.storage.base import PostgresConfig
# Import the production runtime checker without executing it.
from scripts import postgres_runtime_check

# Resolve exact repository deployment assets independently of process cwd.
ROOT = Path(__file__).resolve().parents[1]
# Bind the role/database creation template.
CREATE_TARGET = ROOT / "deploy" / "postgres" / "create-target.sql"
# Bind the post-migration runtime grant template.
FINALIZE_GRANTS = ROOT / "deploy" / "postgres" / "finalize-runtime-grants.sql"
# Bind the application service whose process must never inherit migration authority.
APPLICATION_SERVICE = ROOT / "deploy" / "systemd" / "casino.service"


# Model one runtime connection with deterministic cleanup evidence.
class RuntimeConnection:
    # Initialize no cleanup calls.
    def __init__(self):
        # Count read-transaction rollback.
        self.rollbacks = 0
        # Count physical connector closure.
        self.closes = 0

    # End the verifier's read transaction.
    def rollback(self):
        # Record one explicit rollback.
        self.rollbacks += 1

    # Release the physical connection.
    def close(self):
        # Record one explicit close.
        self.closes += 1


# Prove production deployment helpers without a network, listener, or database.
class PostgreSQLDeploymentTests(unittest.TestCase):
    # Build one safe loopback runtime configuration.
    def runtime_config(self, *, host="127.0.0.1"):
        # Return a synthetic password-bearing config whose values never enter assertions.
        return PostgresConfig(host=host, port=5432, user="casino_runtime", password="synthetic-secret", database="virtual_casino")

    # Require exact clean schema evidence and unconditional connector cleanup.
    def test_runtime_check_is_select_only_provider_bound_and_sanitized(self):
        # Create one deterministic runtime connector.
        connection = RuntimeConnection()
        # Capture the bounded machine-readable result.
        output = StringIO()
        # Supply only the explicit provider selector and replace every external boundary.
        with mock.patch.dict(os.environ, {"CASINO_STORAGE_PROVIDER": "postgres"}, clear=True), mock.patch.object(postgres_runtime_check.PostgresConfig, "from_env", return_value=self.runtime_config()), mock.patch.object(postgres_runtime_check.PostgresPoolConfig, "from_env", return_value=SimpleNamespace(connect_timeout_seconds=3)), mock.patch.object(postgres_runtime_check, "_connect", return_value=connection) as connector, mock.patch.object(postgres_runtime_check, "verify_runtime_compatibility", return_value=SimpleNamespace(current_version=5, status="clean")) as verifier, redirect_stdout(output):
            # Execute the fixed no-argument deployment check.
            result = postgres_runtime_check.main()
        # Require exact success and one connector/verifier call.
        self.assertEqual(result, 0)
        # Require the accepted target and timeout to reach the connector seam.
        connector.assert_called_once_with(self.runtime_config(), 3)
        # Require one SELECT-only compatibility verification.
        verifier.assert_called_once_with(connection)
        # Require both transaction cleanup and physical closure.
        self.assertEqual((connection.rollbacks, connection.closes), (1, 1))
        # Require only the reviewed provider/version/status facts.
        self.assertEqual(output.getvalue().strip(), '{"data": {"current_version": 5, "status": "clean", "storage_provider": "postgres"}, "ok": true}')

    # Refuse wrong providers and off-host targets before connector access.
    def test_runtime_check_fails_before_connect_for_wrong_provider_or_remote_host(self):
        # Exercise provider and host failures independently.
        cases = (("mysql", self.runtime_config()), ("postgres", self.runtime_config(host="db.example.invalid")))
        # Run both pre-connect failure shapes.
        for provider, config in cases:
            # Capture one fixed failure result.
            output = StringIO()
            # Replace configuration while forbidding connector access.
            with self.subTest(provider=provider), mock.patch.dict(os.environ, {"CASINO_STORAGE_PROVIDER": provider}, clear=True), mock.patch.object(postgres_runtime_check.PostgresConfig, "from_env", return_value=config), mock.patch.object(postgres_runtime_check, "_connect") as connector, redirect_stdout(output):
                # Execute the rejected runtime check.
                result = postgres_runtime_check.main()
            # Require the policy failure status and no connector call.
            self.assertEqual(result, 2)
            # Prove failure occurred before any network seam.
            connector.assert_not_called()
            # Publish only the fixed readiness category.
            self.assertIn("runtime schema is not ready", output.getvalue())

    # Collapse connector diagnostics that could carry credentials or target values.
    def test_runtime_check_hides_native_connector_failures(self):
        # Capture the bounded unexpected-failure result.
        output = StringIO()
        # Raise one intentionally sensitive native-like error at the connector seam.
        with mock.patch.dict(os.environ, {"CASINO_STORAGE_PROVIDER": "postgres"}, clear=True), mock.patch.object(postgres_runtime_check.PostgresConfig, "from_env", return_value=self.runtime_config()), mock.patch.object(postgres_runtime_check.PostgresPoolConfig, "from_env", return_value=SimpleNamespace(connect_timeout_seconds=3)), mock.patch.object(postgres_runtime_check, "_connect", side_effect=RuntimeError("synthetic-secret remote-target")), redirect_stdout(output):
            # Execute the failing deployment check.
            result = postgres_runtime_check.main()
        # Require the distinct unexpected-failure status.
        self.assertEqual(result, 3)
        # Require the fixed safe result without native text.
        self.assertIn("failed safely", output.getvalue())
        # Prove credential-shaped and target-shaped values are absent.
        self.assertNotIn("synthetic-secret", output.getvalue())
        # Prove the remote target is absent independently.
        self.assertNotIn("remote-target", output.getvalue())

    # Bind role creation and final grants to the reviewed least-privilege topology.
    def test_sql_templates_are_fixed_secret_safe_and_ddl_free_for_runtime(self):
        # Read the complete fixed target-creation template.
        creation = CREATE_TARGET.read_text(encoding="utf-8")
        # Read the complete post-migration grant template.
        grants = FINALIZE_GRANTS.read_text(encoding="utf-8")
        # Require environment-only password ingestion and exact fixed identities.
        for snippet in ("\\getenv casino_runtime_password CASINO_POSTGRES_PASSWORD", "\\getenv casino_migration_password CASINO_POSTGRES_MIGRATION_PASSWORD", "CREATE ROLE casino_migrate LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "CREATE ROLE casino_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "CREATE DATABASE virtual_casino OWNER casino_migrate", "REVOKE CREATE ON SCHEMA public FROM PUBLIC"):
            # Require every guarded role/database boundary literally.
            self.assertIn(snippet, creation)
        # Require complete runtime DML, sequence, and explicit no-DDL grants.
        for snippet in ("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO casino_runtime", "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO casino_runtime", "REVOKE CREATE ON SCHEMA public FROM casino_runtime", "REVOKE CREATE, TEMPORARY ON DATABASE virtual_casino FROM casino_runtime"):
            # Bind every accepted runtime privilege statement.
            self.assertIn(snippet, grants)
        # Refuse plaintext password placeholders and broad runtime role grants.
        for forbidden in ("synthetic-secret", "<password>", "GRANT ALL", "ALTER ROLE casino_runtime SUPERUSER", "CREATE EXTENSION"):
            # Reject unsafe or ambiguous privilege material from both templates.
            self.assertNotIn(forbidden, creation + grants)

    # Prove the application service strips the complete PostgreSQL migration namespace.
    def test_application_service_unsets_every_migration_authority_value(self):
        # Read only the inert checked-in systemd unit.
        service = APPLICATION_SERVICE.read_text(encoding="utf-8")
        # Require every connection, binding, mode, and release authorization variable to be removed.
        variables = ("HOST", "PORT", "USER", "PASSWORD", "DATABASE", "TARGET_BINDING_KEY", "DISPOSABLE", "PRODUCTION", "RELEASE_SHA")
        # Bind each complete environment name to the explicit UnsetEnvironment policy.
        for suffix in variables:
            # Reject any application unit that could inherit one deployment-only PostgreSQL value.
            self.assertIn(f"CASINO_POSTGRES_MIGRATION_{suffix}", service)


# Execute the focused suite only when invoked directly.
if __name__ == "__main__":
    # Use unittest's standard fail-closed runner.
    unittest.main()
