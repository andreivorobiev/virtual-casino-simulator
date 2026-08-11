# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Admin-route tests for the disabled OAuth integration.

Requirements: OAUTH-001, OAUTH-002, and TEST-045.
"""

# Import unittest so route behavior runs without provider SDKs or network access.
import unittest

# Import the disabled OAuth route registration and direct payload projection.
from casino.core.oauth.api import provider_diagnostic_payload, register
# Import the shared in-process router so route inventory and authorization stay exact.
from casino.router import Router
# Import the standard authorization error for direct-dispatch assertions.
from casino.errors import ForbiddenError


# Verify the shared integration exposes the exact disabled-by-default v2 surface.
class OAuthApiTests(unittest.TestCase):
    # Build one isolated router with a synthetic environment and no live configuration.
    def _router(self, environment=None):
        # Create a fresh route collection so tests do not mutate the application singleton.
        router = Router()
        # Register only the OAuth diagnostic adapter against the injected mapping.
        register(router, {} if environment is None else environment)
        # Return the isolated router for direct dispatch.
        return router

    # Verify route registration stays limited to exact reviewed provider routes.
    def test_route_inventory_exposes_exact_v2_oauth_surface(self):
        # Read the exact registered route patterns from the isolated router.
        routes = [(route.method, route.pattern) for route in self._router().routes]
        # Require exactly the additive Admin, public, callback, current-user, and unlink routes.
        self.assertEqual(routes, [("GET", "/api/v2/admin/oauth/providers"), ("GET", "/api/v2/auth/oauth/providers"), ("POST", "/api/v2/auth/oauth/(?P<provider>google|facebook)/start"), ("GET", "/api/v2/auth/oauth/(?P<provider>google|facebook)/callback"), ("GET", "/api/v2/me/oauth/providers"), ("POST", "/api/v2/me/oauth/(?P<provider>google|facebook)/unlink")])
        # Reject any frozen v1 or unrestricted provider route.
        self.assertFalse(any(pattern.startswith("/api/v1") or "signup" in pattern or "exchange" in pattern for _, pattern in routes))

    # Verify a normal authenticated user cannot read configuration diagnostics.
    def test_direct_dispatch_requires_admin_role(self):
        # Build the minimum normal-user context accepted by the shared auth guard.
        context = {"user": {"roles": ["player"], "role": "player", "status": "active"}}
        # Require the route-level guard to reject direct router dispatch.
        with self.assertRaises(ForbiddenError):
            # Attempt the Admin route without passing through the application's central prefix guard.
            self._router().dispatch("GET", "/api/v2/admin/oauth/providers", context=context)

    # Verify complete synthetic configuration never becomes runtime availability.
    def test_admin_diagnostics_are_allowlisted_and_runtime_disabled(self):
        # Supply synthetic values that must never appear in the serialized response.
        environment = {"CASINO_OAUTH_ENABLED_GOOGLE": "true", "CASINO_GOOGLE_CLIENT_ID": "synthetic-client-id", "CASINO_GOOGLE_CLIENT_SECRET": "synthetic-client-secret", "CASINO_OAUTH_PUBLIC_BASE_URL": "http://localhost:8767", "CASINO_OAUTH_DIGEST_KEY": "synthetic-digest-key-with-at-least-32-bytes"}
        # Dispatch through an Admin context while opening no provider connection.
        payload = self._router(environment).dispatch("GET", "/api/v2/admin/oauth/providers", context={"user": {"roles": ["admin"], "role": "admin", "status": "active"}})
        # Index the stable provider rows for focused assertions.
        providers = {provider["provider"]: provider for provider in payload["providers"]}
        # Require the local password provider to remain the sole runtime-available option.
        self.assertTrue(providers["local"]["runtime_available"])
        # Distinguish inert configuration readiness from unavailable Google runtime behavior.
        self.assertTrue(providers["google"]["configuration_ready"])
        # Keep Google unavailable even when synthetic configuration is structurally complete.
        self.assertFalse(providers["google"]["runtime_available"])
        # Keep Facebook unavailable independently.
        self.assertFalse(providers["facebook"]["runtime_available"])
        # Serialize only for secret-absence assertions without printing the result.
        serialized = repr(payload)
        # Reject the synthetic public identifier from the Admin response.
        self.assertNotIn("synthetic-client-id", serialized)
        # Reject the synthetic provider secret from the Admin response.
        self.assertNotIn("synthetic-client-secret", serialized)

    # Verify the payload schema contains no live adapter or action URL fields.
    def test_diagnostic_projection_has_exact_allowlisted_keys(self):
        # Build default diagnostics from an empty injected environment.
        payload = provider_diagnostic_payload({})
        # Define the complete allowlist published by the additive auth contract.
        expected_keys = {"provider", "flow", "status", "configuration_ready", "runtime_available", "enabled_requested", "network_released", "client_id_configured", "client_secret_configured", "callback_url", "missing_variables", "problems"}
        # Require exactly local, Google, and Facebook in stable order.
        self.assertEqual([row["provider"] for row in payload["providers"]], ["local", "google", "facebook"])
        # Require every row to match the fixed secret-safe schema exactly.
        self.assertTrue(all(set(row) == expected_keys for row in payload["providers"]))
        # Reject fields that could cause a browser or operator to start an OAuth flow.
        self.assertTrue(all(not ({"authorization_url", "token", "code", "claims"} & set(row)) for row in payload["providers"]))


# Run focused tests when this module is invoked directly.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
