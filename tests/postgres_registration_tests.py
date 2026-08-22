# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused PostgreSQL configuration and lazy-registration evidence. (STORAGE-020, TEST-252)"""

# Import process environment access for isolated configuration matrices.
import os
# Import lightweight namespaces for synthetic future-provider modules.
from types import SimpleNamespace
# Import standard unittest assertions for listener-free registration proofs.
import unittest
# Import patch helpers so no concrete connector or provider is constructed.
from unittest import mock

# Import canonical defaults that must remain aligned with the immutable config object.
from casino import config as casino_config
# Import the historical storage facade whose JSON/MySQL behavior must remain compatible.
from casino.core import storage
# Import the provider-neutral PostgreSQL value object for identity proof.
from casino.core.storage import base as storage_base
# Import the public validation boundary used by configuration and selection failures.
from casino.errors import ValidationError


# Bind the complete environment namespace owned by this registration lane.
POSTGRES_ENV_KEYS = (
    # Select the PostgreSQL host without affecting the application listener.
    "CASINO_POSTGRES_HOST",
    # Select the PostgreSQL TCP port as configuration text.
    "CASINO_POSTGRES_PORT",
    # Select the PostgreSQL role name.
    "CASINO_POSTGRES_USER",
    # Select the PostgreSQL password without ever publishing it.
    "CASINO_POSTGRES_PASSWORD",
    # Select the PostgreSQL database name.
    "CASINO_POSTGRES_DATABASE",
)


# Prove PostgreSQL registration stays deterministic, lazy, and fail-closed.
class PostgresRegistrationTests(unittest.TestCase):
    """Bind configuration values and the disabled-until-provider-core selector seam."""

    # Remove inherited PostgreSQL settings before every isolated test.
    def setUp(self):
        # Preserve exact prior presence and values for unconditional cleanup.
        self.prior_environment = {key: os.environ.get(key) for key in POSTGRES_ENV_KEYS}
        # Remove every lane-owned setting so tests start at canonical defaults.
        for key in POSTGRES_ENV_KEYS:
            # Delete only the selected synthetic configuration key.
            os.environ.pop(key, None)
        # Restore the caller process even when an assertion fails.
        self.addCleanup(self._restore_environment)

    # Restore the exact environment presence captured during setup.
    def _restore_environment(self):
        # Visit every lane-owned key once.
        for key, value in self.prior_environment.items():
            # Remove keys that were originally absent.
            if value is None:
                # Prevent synthetic test values from leaking into later cases.
                os.environ.pop(key, None)
            # Restore keys that were present before the test.
            else:
                # Preserve the caller-owned value byte-for-byte.
                os.environ[key] = value

    # Bind public identity, canonical defaults, and psycopg keyword translation.
    def test_defaults_and_public_identity_are_deterministic(self):
        # Build the immutable value object without importing or calling a connector.
        selected = storage.PostgresConfig.from_env()
        # Require one class identity across the base owner and historical facade.
        self.assertIs(storage.PostgresConfig, storage_base.PostgresConfig)
        # Bind the exact loopback-only repository defaults.
        self.assertEqual(
            selected,
            storage.PostgresConfig(
                # Bind the canonical loopback host.
                host=casino_config.DEFAULT_POSTGRES_HOST,
                # Bind the standard PostgreSQL port.
                port=casino_config.DEFAULT_POSTGRES_PORT,
                # Bind the local role convention.
                user=casino_config.DEFAULT_POSTGRES_USER,
                # Bind the intentionally empty local password default.
                password="",
                # Bind the local database convention.
                database=casino_config.DEFAULT_POSTGRES_DATABASE,
            ),
        )
        # Require psycopg/libpq's canonical dbname spelling at the future connector seam.
        self.assertEqual(
            selected.kwargs(),
            {
                # Retain the configured host.
                "host": "127.0.0.1",
                # Retain the integer port.
                "port": 5432,
                # Retain the configured role.
                "user": "casino",
                # Retain the empty local password.
                "password": "",
                # Translate only the public database field name.
                "dbname": "virtual_casino",
            },
        )

    # Accept deterministic overrides while trimming identifiers but never the password.
    def test_environment_overrides_preserve_secret_bytes(self):
        # Install synthetic non-routable values under the dedicated namespace.
        os.environ.update(
            {
                # Surround the host with harmless operator whitespace.
                "CASINO_POSTGRES_HOST": " pg.example.invalid ",
                # Select a valid non-default port.
                "CASINO_POSTGRES_PORT": "55432",
                # Surround the role name with harmless operator whitespace.
                "CASINO_POSTGRES_USER": " fixture_role ",
                # Preserve password whitespace as credential material.
                "CASINO_POSTGRES_PASSWORD": " synthetic secret ",
                # Surround the database name with harmless operator whitespace.
                "CASINO_POSTGRES_DATABASE": " fixture_db ",
            }
        )
        # Parse the complete override set before any provider exists.
        selected = storage.PostgresConfig.from_env()
        # Bind normalized identifiers and the unmodified password.
        self.assertEqual(selected, storage.PostgresConfig("pg.example.invalid", 55432, "fixture_role", " synthetic secret ", "fixture_db"))

    # Reject every malformed environment category through one secret-free message.
    def test_malformed_environment_fails_with_fixed_diagnostic(self):
        # Define representative text, range, and blank-identifier failures.
        malformed = (
            # Reject non-numeric ports.
            ("CASINO_POSTGRES_PORT", "secret-port"),
            # Reject the reserved zero port.
            ("CASINO_POSTGRES_PORT", "0"),
            # Reject ports above the TCP range.
            ("CASINO_POSTGRES_PORT", "65536"),
            # Reject an empty host after normalization.
            ("CASINO_POSTGRES_HOST", "   "),
            # Reject an empty role after normalization.
            ("CASINO_POSTGRES_USER", "   "),
            # Reject an empty database after normalization.
            ("CASINO_POSTGRES_DATABASE", "   "),
        )
        # Exercise every malformed field independently from defaults.
        for key, value in malformed:
            # Name only the configuration key in test diagnostics.
            with self.subTest(key=key):
                # Install the one rejected synthetic value.
                os.environ[key] = value
                # Require the fixed value-free public diagnostic.
                with self.assertRaisesRegex(ValidationError, "^PostgreSQL configuration is invalid$"):
                    # Parse without importing a driver or opening a connector.
                    storage.PostgresConfig.from_env()
                # Remove the rejected value before the next matrix cell.
                os.environ.pop(key, None)

    # Reject malformed direct construction through the same bounded contract.
    def test_direct_construction_is_validated_without_value_disclosure(self):
        # Supply a secret-bearing target while making only the port invalid.
        with self.assertRaisesRegex(ValidationError, "^PostgreSQL configuration is invalid$") as raised:
            # Construct the immutable object directly as future pool/provider callers will.
            storage.PostgresConfig("secret-target.invalid", True, "secret-role", "secret-password", "secret-db")
        # Prove no rejected target, role, password, or database entered the diagnostic.
        self.assertEqual(str(raised.exception), "PostgreSQL configuration is invalid")

    # Prove JSON and MySQL selections never visit the PostgreSQL import seam.
    def test_json_and_mysql_do_not_import_postgres_or_psycopg(self):
        # Exercise the absent-selector default plus both explicit established branches.
        for name, attribute in (
            (None, "JsonStorageProvider"),
            ("json", "JsonStorageProvider"),
            ("mysql", "MySQLStorageProvider"),
        ):
            # Name the selected provider in focused assertion output.
            with self.subTest(provider=name or "absent"):
                # Install the explicit selector, or a restoring environment patch for its absence.
                selector = {} if name is None else {"CASINO_STORAGE_PROVIDER": name}
                # Restore the process environment after each selector cell.
                with mock.patch.dict(os.environ, selector):
                    # Remove any inherited selector so the default-JSON boundary is exercised.
                    if name is None:
                        # Keep the removal scoped to the restoring environment patch.
                        os.environ.pop("CASINO_STORAGE_PROVIDER", None)
                    # Replace the concrete established provider so the proof opens no storage or connector.
                    with mock.patch.object(storage, attribute, return_value=object()) as constructor:
                        # Trap every dynamic import attempt during provider construction.
                        with mock.patch.object(storage.importlib, "import_module") as importer:
                            # Build only through the production selector.
                            selected = storage._build_provider()
                # Require the established constructor result.
                self.assertIsNotNone(selected)
                # Require exactly one established provider construction.
                constructor.assert_called_once_with()
                # Prove neither PostgreSQL nor psycopg was dynamically imported.
                importer.assert_not_called()

    # Resolve the future provider only after explicit PostgreSQL selection.
    def test_postgres_selection_uses_one_lazy_future_provider_import(self):
        # Create one inert result so no provider contract or connector is required in Lane 2.
        sentinel = object()
        # Model the future provider class as a callable constructor.
        provider_class = mock.Mock(return_value=sentinel)
        # Model the future module with only its documented class export.
        future_module = SimpleNamespace(PostgresStorageProvider=provider_class)
        # Select PostgreSQL explicitly for this one call.
        with mock.patch.dict(os.environ, {"CASINO_STORAGE_PROVIDER": "postgres"}):
            # Return the synthetic future module from the one lazy import.
            with mock.patch.object(storage.importlib, "import_module", return_value=future_module) as importer:
                # Exercise the production selector seam.
                selected = storage._build_provider()
        # Require the exact future module name and no psycopg import by this facade.
        importer.assert_called_once_with("casino.core.storage.postgres_provider")
        # Require one default construction compatible with the future provider core.
        provider_class.assert_called_once_with()
        # Return the exact constructed provider object.
        self.assertIs(selected, sentinel)

    # Collapse absent module, absent driver, missing class, and malformed class into one diagnostic.
    def test_incomplete_postgres_provider_fails_closed(self):
        # Define every incomplete lazy-resolution shape that this lane owns.
        failures = (
            # Model the provider module not existing before Lane 4.
            ModuleNotFoundError("secret target module missing"),
            # Model psycopg missing while the future module imports.
            ImportError("secret psycopg import detail"),
            # Model a future module missing its public provider class.
            SimpleNamespace(),
            # Model a future module publishing a non-callable class attribute.
            SimpleNamespace(PostgresStorageProvider=None),
            # Model a future provider whose constructor lazily discovers an absent driver.
            SimpleNamespace(PostgresStorageProvider=mock.Mock(side_effect=ImportError("secret lazy driver detail"))),
        )
        # Select PostgreSQL explicitly for the complete failure matrix.
        with mock.patch.dict(os.environ, {"CASINO_STORAGE_PROVIDER": "postgres"}):
            # Exercise every absent or malformed future-provider shape.
            for failure in failures:
                # Distinguish only the safe synthetic failure type.
                with self.subTest(failure=type(failure).__name__):
                    # Raise exception shapes and return module shapes through the same lazy seam.
                    effect = failure if isinstance(failure, Exception) else None
                    # Return only module-shaped failures when no exception is selected.
                    result = None if effect is not None else failure
                    # Patch the exact dynamic import boundary.
                    with mock.patch.object(storage.importlib, "import_module", side_effect=effect, return_value=result):
                        # Require one fixed provider-owned public message.
                        with self.assertRaisesRegex(ValidationError, "^PostgreSQL storage provider is unavailable$") as raised:
                            # Exercise the production selector without retry or fallback.
                            storage._build_provider()
                    # Prove native details and synthetic target text remain absent.
                    self.assertEqual(str(raised.exception), "PostgreSQL storage provider is unavailable")

    # Preserve the existing unknown-selector normalization and diagnostic behavior.
    def test_unknown_selector_behavior_is_unchanged(self):
        # Install whitespace and mixed case to exercise the historical normalization.
        with mock.patch.dict(os.environ, {"CASINO_STORAGE_PROVIDER": " Unsupported-Mode "}):
            # Require the established lower-case selector diagnostic.
            with self.assertRaisesRegex(ValidationError, "^Unsupported storage provider: unsupported-mode$"):
                # Exercise the same final branch used before PostgreSQL registration.
                storage._build_provider()


# Run the focused listener-free suite directly for local qualification.
if __name__ == "__main__":
    # Return the standard unittest process status.
    unittest.main()
