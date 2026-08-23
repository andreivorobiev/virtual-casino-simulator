# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Govern disposable relational registration without opening a listener. (TEST-257)"""

from __future__ import annotations

# Import environment access for restoring reachability and secret-isolation proofs.
import os
# Import unit-test assertions for the listener-free harness gate.
import unittest
# Import restoring patches for optional imports, provider construction, and environment state.
from unittest import mock

# Import fixed harness authorization names and constructors without optional database drivers.
from tests.storage_conformance import database_harnesses


class DatabaseHarnessGovernanceTests(unittest.TestCase):
    """Keep absent services inert and reject incomplete live authorization."""

    def test_absent_markers_skip_without_optional_import(self) -> None:
        """Require both database harnesses to stay listener- and driver-free by default."""

        # Remove every ambient variable so absence semantics are deterministic.
        with mock.patch.dict(os.environ, {}, clear=True):
            # Fail if reachability inspection attempts any optional module import.
            with mock.patch.object(database_harnesses.importlib, "import_module", side_effect=AssertionError("optional import attempted")) as loader:
                # Construct both harnesses without allocating a root, process, or connection.
                mysql_harness = database_harnesses.MySQLHarness()
                # Construct PostgreSQL independently so no shared state can imply reachability.
                postgres_harness = database_harnesses.PostgresHarness()
                # Require one fixed value-free absence reason for both registrations.
                self.assertEqual(database_harnesses.ABSENT_REASON, mysql_harness.unavailable_reason())
                # Require PostgreSQL to report the exact same provider-neutral category.
                self.assertEqual(database_harnesses.ABSENT_REASON, postgres_harness.unavailable_reason())
                # Prove marker inspection did not import a connector, migration runner, or provider.
                loader.assert_not_called()
                # Prove PostgreSQL did not allocate any filesystem root before authorization.
                self.assertIsNone(postgres_harness.root)

    def test_present_invalid_markers_fail_before_optional_import(self) -> None:
        """Reject malformed opt-ins instead of converting them into absence skips."""

        # Supply only invalid marker values and no credentials or binary path.
        environment = {
            database_harnesses.MYSQL_MARKER_NAME: "invalid",
            database_harnesses.POSTGRES_MARKER_NAME: "invalid",
        }
        # Isolate the malformed authorization from the developer environment.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Prove invalid authorization never reaches an optional module loader.
            with mock.patch.object(database_harnesses.importlib, "import_module", side_effect=AssertionError("optional import attempted")) as loader:
                # Require one fixed MySQL authorization category.
                with self.assertRaisesRegex(AssertionError, "Disposable MySQL conformance authorization is invalid"):
                    # Inspect the marker without creating any resource.
                    database_harnesses.MySQLHarness().unavailable_reason()
                # Require one fixed PostgreSQL authorization category.
                with self.assertRaisesRegex(AssertionError, "Disposable PostgreSQL conformance authorization is invalid"):
                    # Inspect the independent marker without creating any resource.
                    database_harnesses.PostgresHarness().unavailable_reason()
                # Prove neither failure path imported a driver or migration helper.
                loader.assert_not_called()

    def test_present_mysql_marker_requires_complete_loopback_reachability(self) -> None:
        """Fail closed on partial MySQL configuration without reading a secret value."""

        # Authorize the lane but omit every reviewed administrator field.
        environment = {database_harnesses.MYSQL_MARKER_NAME: database_harnesses.MYSQL_MARKER_VALUE}
        # Remove unrelated variables so no ambient endpoint can satisfy the gate.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Construct without importing mysql.connector.
            harness = database_harnesses.MySQLHarness()
            # Require the exact marker to select execution rather than a skip.
            self.assertIsNone(harness.unavailable_reason())
            # Require incomplete reachability to fail before connection setup.
            with self.assertRaisesRegex(AssertionError, "Disposable MySQL conformance reachability is incomplete"):
                # Validate only the bounded endpoint contract.
                harness._admin_kwargs()

    def test_present_postgres_marker_requires_reviewed_binaries(self) -> None:
        """Fail closed on missing PostgreSQL binaries before importing psycopg."""

        # Authorize the lane but omit the explicit binary root.
        environment = {database_harnesses.POSTGRES_MARKER_NAME: database_harnesses.POSTGRES_MARKER_VALUE}
        # Remove ambient PATH-like configuration from the proof.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Construct without allocating a cluster root.
            harness = database_harnesses.PostgresHarness()
            # Require the exact marker to select execution rather than a skip.
            self.assertIsNone(harness.unavailable_reason())
            # Require an explicit reviewed binary root with no PATH fallback.
            with self.assertRaisesRegex(AssertionError, "Disposable PostgreSQL conformance reachability is incomplete"):
                # Validate only the bounded binary contract.
                harness._validated_bin()
            # Prove validation failure allocated no private filesystem root.
            self.assertIsNone(harness.root)

    def test_provider_factory_environment_is_restored(self) -> None:
        """Keep generated target and credential values out of the ambient process."""

        # Build one sentinel provider without importing any concrete implementation.
        provider = object()
        # Use a dedicated secret-like name and value for restoration evidence.
        environment = {"CASINO_STORAGE_PROVIDER": "postgres", "CASINO_POSTGRES_PASSWORD": "generated-secret"}
        # Start from a deterministic environment with neither value present.
        with mock.patch.dict(os.environ, {}, clear=True):
            # Replace only the public facade's uncached selector factory.
            with mock.patch.object(database_harnesses.storage_facade, "_build_provider", return_value=provider) as factory:
                # Construct through the same bounded helper used by both relational harnesses.
                selected = database_harnesses._provider_from_environment(environment)
            # Require exact provider identity from the selector facade.
            self.assertIs(provider, selected)
            # Require one and only one synchronous selector invocation.
            factory.assert_called_once_with()
            # Prove provider selection did not retain the selected backend name.
            self.assertNotIn("CASINO_STORAGE_PROVIDER", os.environ)
            # Prove provider construction did not retain the generated secret.
            self.assertNotIn("CASINO_POSTGRES_PASSWORD", os.environ)


if __name__ == "__main__":
    # Support direct focused execution without central-runner mutation.
    unittest.main()
