"""Focused OAuth disabled-configuration diagnostic tests for issue #70.

Requirements: OAUTH-001, OAUTH-002, and TEST-045.
"""

# Import unittest so focused tests run without third-party dependencies.
import unittest

# Import inert configuration loading and secret-safe diagnostics.
from casino.core.oauth.configuration import load_oauth_configuration, oauth_diagnostics


# Validate fail-closed provider settings without touching the live process environment.
class OAuthConfigurationTests(unittest.TestCase):
    # Convert diagnostic tuples to stable provider-keyed dictionaries for assertions.
    def _diagnostics_by_provider(self, environment):
        # Load only the injected synthetic environment mapping.
        configuration = load_oauth_configuration(environment)
        # Return both the inert configuration and public provider-indexed diagnostics.
        return configuration, {diagnostic.provider: diagnostic for diagnostic in oauth_diagnostics(configuration)}

    # Verify local login remains available while external providers default to disabled.
    def test_empty_environment_preserves_local_and_disables_external(self):
        # Diagnose a completely empty injected environment.
        _, diagnostics = self._diagnostics_by_provider({})
        # Assert local password login remains ready and unchanged.
        self.assertEqual(diagnostics["local"].status, "ready")
        # Assert Google is safely disabled.
        self.assertEqual(diagnostics["google"].status, "disabled")
        # Assert Facebook is safely disabled.
        self.assertEqual(diagnostics["facebook"].status, "disabled")
        # Assert no external provider is available by default.
        self.assertFalse(diagnostics["google"].runtime_available)
        # Assert diagnostics identify missing setting names without values.
        self.assertIn("CASINO_GOOGLE_CLIENT_SECRET", diagnostics["google"].missing_variables)

    # Verify complete synthetic configuration becomes ready only after explicit enablement.
    def test_complete_explicit_configuration_is_ready_and_repr_safe(self):
        # Define synthetic values that must never appear in representations or diagnostics.
        client_id = "synthetic-google-client-id"
        # Define a synthetic secret that must never appear in representations or diagnostics.
        client_secret = "synthetic-google-client-secret"
        # Build a complete injected Google configuration on non-user port 8767.
        environment = {"CASINO_OAUTH_ENABLED_GOOGLE": "true", "CASINO_GOOGLE_CLIENT_ID": client_id, "CASINO_GOOGLE_CLIENT_SECRET": client_secret, "CASINO_OAUTH_PUBLIC_BASE_URL": "http://localhost:8767", "CASINO_OAUTH_DIGEST_KEY": "synthetic-digest-key-with-at-least-32-bytes"}
        # Diagnose only the injected configuration.
        configuration, diagnostics = self._diagnostics_by_provider(environment)
        # Assert Google is structurally ready for later integration.
        self.assertEqual(diagnostics["google"].status, "ready")
        # Assert inert configuration is ready while no runtime route or adapter is available.
        self.assertTrue(diagnostics["google"].configuration_ready)
        # Assert runtime availability remains false until the independent provider-network release.
        self.assertFalse(diagnostics["google"].runtime_available)
        # Assert the independent release latch remains false by default.
        self.assertFalse(diagnostics["google"].network_released)
        # Assert the exact public callback URL is available to Operations.
        self.assertEqual(diagnostics["google"].callback_url, "http://localhost:8767/api/v2/auth/oauth/google/callback")
        # Assert readiness diagnostics contain no missing variables.
        self.assertEqual(diagnostics["google"].missing_variables, ())
        # Assert the public client id is absent from the inert configuration representation.
        self.assertNotIn(client_id, repr(configuration))
        # Assert the provider secret is absent from the inert configuration representation.
        self.assertNotIn(client_secret, repr(configuration))
        # Assert neither configured value appears in public diagnostics.
        self.assertNotIn(client_id, repr(diagnostics["google"].as_dict()))
        # Assert neither configured value appears in public diagnostics.
        self.assertNotIn(client_secret, repr(diagnostics["google"].as_dict()))
        # Assert Facebook remains disabled independently.
        self.assertEqual(diagnostics["facebook"].status, "disabled")

    # Verify credentials without an explicit enable flag remain inert.
    def test_credentials_alone_do_not_enable_provider(self):
        # Build an injected configuration with credentials but no enable flag.
        environment = {"CASINO_GOOGLE_CLIENT_ID": "synthetic-id", "CASINO_GOOGLE_CLIENT_SECRET": "synthetic-secret", "CASINO_OAUTH_PUBLIC_BASE_URL": "https://casino.example.test"}
        # Diagnose only the injected configuration.
        _, diagnostics = self._diagnostics_by_provider(environment)
        # Assert Google remains disabled despite complete credential presence.
        self.assertEqual(diagnostics["google"].status, "disabled")
        # Assert the disabled provider is unavailable.
        self.assertFalse(diagnostics["google"].runtime_available)

    # Verify enabled-but-incomplete provider configuration fails closed.
    def test_enabled_incomplete_provider_is_misconfigured(self):
        # Define one synthetic client id while intentionally omitting its secret and base URL.
        environment = {"CASINO_OAUTH_ENABLED_FACEBOOK": "yes", "CASINO_FACEBOOK_APP_ID": "synthetic-app-id"}
        # Diagnose only the injected configuration.
        configuration, diagnostics = self._diagnostics_by_provider(environment)
        # Assert Facebook reports a fail-closed configuration state.
        self.assertEqual(diagnostics["facebook"].status, "misconfigured")
        # Assert incomplete configuration is unavailable.
        self.assertFalse(diagnostics["facebook"].runtime_available)
        # Assert only missing setting names are reported.
        self.assertEqual(diagnostics["facebook"].missing_variables, ("CASINO_FACEBOOK_APP_SECRET", "CASINO_OAUTH_PUBLIC_BASE_URL", "CASINO_OAUTH_DIGEST_KEY"))
        # Assert no synthetic identifier appears in the configuration representation.
        self.assertNotIn("synthetic-app-id", repr(configuration))

    # Verify invalid enable flags and callback bases are diagnostic rather than permissive.
    def test_invalid_configuration_values_fail_closed(self):
        # Define one unsafe base value that must not be reflected into diagnostics.
        unsafe_base = "http://127.0.0.1:8766/private"
        # Build an injected configuration with an invalid enable flag and unsafe base.
        environment = {"CASINO_OAUTH_ENABLED_GOOGLE": "sometimes", "CASINO_GOOGLE_CLIENT_ID": "synthetic-id", "CASINO_GOOGLE_CLIENT_SECRET": "synthetic-secret", "CASINO_OAUTH_PUBLIC_BASE_URL": unsafe_base}
        # Diagnose only the injected configuration.
        _, diagnostics = self._diagnostics_by_provider(environment)
        # Assert invalid explicit configuration is misconfigured and unavailable.
        self.assertEqual(diagnostics["google"].status, "misconfigured")
        # Assert the stable enable-flag problem code is present.
        self.assertIn("invalid_enable_flag", diagnostics["google"].problems)
        # Assert the stable callback-base problem code is present.
        self.assertIn("invalid_public_base_url", diagnostics["google"].problems)
        # Assert the configured base value is absent from public diagnostics.
        self.assertNotIn(unsafe_base, repr(diagnostics["google"].as_dict()))
        # Define an accidental credential marker embedded in malformed callback configuration.
        embedded_marker = "embedded-secret-marker"
        # Load the malformed callback base without enabling routes or opening a listener.
        malformed_configuration = load_oauth_configuration({"CASINO_OAUTH_PUBLIC_BASE_URL": f"https://user:{embedded_marker}@casino.example.test"})
        # Assert configuration representations suppress the entire raw callback base.
        self.assertNotIn(embedded_marker, repr(malformed_configuration))

    # Verify the independent provider-network latch is required and provider-scoped.
    def test_network_release_is_explicit_independent_and_provider_scoped(self):
        # Build complete Google settings while releasing only Google transport construction.
        environment = {"CASINO_OAUTH_ENABLED_GOOGLE": "true", "CASINO_OAUTH_NETWORK_RELEASED_GOOGLE": "true", "CASINO_GOOGLE_CLIENT_ID": "synthetic-id", "CASINO_GOOGLE_CLIENT_SECRET": "synthetic-secret", "CASINO_OAUTH_PUBLIC_BASE_URL": "https://casino.example.test", "CASINO_OAUTH_DIGEST_KEY": "synthetic-digest-key-with-at-least-32-bytes"}
        # Diagnose only the injected release snapshot.
        _, diagnostics = self._diagnostics_by_provider(environment)
        # Require Google runtime availability only after both independent gates are true.
        self.assertTrue(diagnostics["google"].runtime_available)
        # Keep Facebook unavailable under the independently scoped latch.
        self.assertFalse(diagnostics["facebook"].runtime_available)
        # Reject ambiguous release values without enabling runtime.
        _, invalid = self._diagnostics_by_provider({**environment, "CASINO_OAUTH_NETWORK_RELEASED_GOOGLE": "sometimes"})
        # Require a stable fail-closed problem code for operator diagnosis.
        self.assertIn("invalid_network_release_flag", invalid["google"].problems)


# Run focused tests when this file is invoked directly.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
