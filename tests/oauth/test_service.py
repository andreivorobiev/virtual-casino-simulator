"""Invite-only OAuth orchestration tests for issue #326.

Requirements: AUTH-002, OAUTH-003, OAUTH-004, OAUTH-007, OAUTH-008,
OAUTH-009, OAUTH-010, SESSION-006, SEC-010, and TEST-045.
"""

# Import temporary directories for isolated flow and link persistence.
import tempfile
# Import unittest and patching for canonical auth dependency injection.
import unittest
# Import paths for isolated storage construction.
from pathlib import Path
# Import mock patch for local user/session and audit boundaries.
from unittest.mock import patch

# Import the provider-neutral verified identity returned by the fake adapter.
from casino.core.oauth.models import VerifiedIdentity
# Import strict identity-link records for provider-session rollback tests.
from casino.core.oauth.identity_links import ExternalIdentityLink
# Import the stable flow document key for test-only state retrieval.
from casino.core.oauth.persistence import FLOW_DOCUMENT_KEY
# Import the invite-only service under test.
from casino.core.oauth.service import OAuthService, provider_session_is_authorized
# Import the isolated JSON storage provider.
from casino.core.storage import JsonStorageProvider
# Import stable public error classes for negative cases.
from casino.errors import ForbiddenError, NotFoundError, ProviderUnavailableError, UnauthorizedError, ValidationError

# Define a complete synthetic Google configuration with the exact public environment contract.
GOOGLE_ENV = {"CASINO_OAUTH_ENABLED_GOOGLE": "true", "CASINO_OAUTH_NETWORK_RELEASED_GOOGLE": "true", "CASINO_GOOGLE_CLIENT_ID": "synthetic-client", "CASINO_GOOGLE_CLIENT_SECRET": "synthetic-secret", "CASINO_OAUTH_PUBLIC_BASE_URL": "https://casino.example.test", "CASINO_OAUTH_DIGEST_KEY": "synthetic-digest-key-with-at-least-32-bytes"}
# Define a complete independent synthetic Facebook configuration.
FACEBOOK_ENV = {"CASINO_OAUTH_ENABLED_FACEBOOK": "true", "CASINO_OAUTH_NETWORK_RELEASED_FACEBOOK": "true", "CASINO_FACEBOOK_APP_ID": "synthetic-app", "CASINO_FACEBOOK_APP_SECRET": "synthetic-secret", "CASINO_OAUTH_PUBLIC_BASE_URL": "https://casino.example.test", "CASINO_OAUTH_DIGEST_KEY": "synthetic-digest-key-with-at-least-32-bytes"}
# Define one generated-shape browser cookie that contains no real user data.
BROWSER_COOKIE = "c" * 43


# Provide a deterministic adapter without provider credentials or network access.
class FakeAdapter:
    # Retain only the selected provider and a synthetic verified subject.
    def __init__(self, provider, *, fail_exchange=False):
        # Store the fixed provider identifier.
        self.provider = provider
        # Retain one fixed transport-failure mode for recovery-policy evidence.
        self.fail_exchange = fail_exchange
        # Retain generated state only inside the in-memory test double.
        self.state = None

    # Return a non-secret synthetic destination while recording no proofs.
    def authorization_url(self, *, redirect_uri, state, nonce, pkce_challenge):
        # Require all security fields before simulating provider navigation.
        if not all((redirect_uri, state, nonce, pkce_challenge)):
            # Fail the test double if orchestration omitted a required binding.
            raise AssertionError("flow security values are required")
        # Retain state only in this request-local fake so tests never read it from durable metadata.
        self.state = state
        # Return a fixed HTTPS URL with no serialized proof or provider configuration.
        return f"https://{self.provider}.example.invalid/authorize"

    # Return a verified provider subject while ignoring optional display email for linking.
    def exchange_code(self, *, code, redirect_uri, expected_nonce, pkce_verifier):
        # Require every retained one-time field to reach the exchange boundary.
        if not all((code, redirect_uri, expected_nonce, pkce_verifier)):
            # Fail the test double on incomplete flow context.
            raise AssertionError("exchange security values are required")
        # Simulate one fixed retryable provider/network failure without returning raw provider text.
        if self.fail_exchange:
            # Raise only the stable public 503 class used by the recoverable flow policy.
            raise ProviderUnavailableError()
        # Return a provider subject plus same-email metadata that must never auto-link.
        return VerifiedIdentity(provider=self.provider, subject=f"{self.provider}-subject", email="invite@example.invalid", email_verified=self.provider == "google", display_name="Synthetic Display")


# Verify sign-in, explicit linking, replay, duplicate, redirect, and rollback boundaries.
class OAuthServiceTests(unittest.TestCase):
    # Create isolated storage and a stable canonical invite user before each test.
    def setUp(self):
        # Retain a temporary root until cleanup.
        self.temporary = tempfile.TemporaryDirectory()
        # Build the shared test provider beneath the temporary root.
        self.storage = JsonStorageProvider(Path(self.temporary.name) / "data")
        # Create all provider-owned directories.
        self.storage.ensure_ready()
        # Define one active private-invite local-password user.
        self.user = {"user_id": "user-synthetic", "status": "active", "player_id": "player-synthetic", "email": "invite@example.invalid", "password_hash": "local-password-hash", "identity_provider": "local"}
        # Define one initiating local session with no bearer material in source.
        self.session = {"session_id": "session-synthetic", "user_id": self.user["user_id"], "status": "active", "csrf_token": BROWSER_COOKIE, "auth_method": "local"}
        # Collect request-local fake adapters so tests can return the provider state without durable raw storage.
        self.adapters = []

    # Remove only the test-owned temporary root.
    def tearDown(self):
        # Clean up isolated flow and link documents.
        self.temporary.cleanup()

    # Construct a service with an exact provider adapter factory.
    def service(self, environment=None):
        # Build one adapter factory that records only in-memory test doubles.
        def adapter_factory(provider, _client_id, _client_secret):
            # Create the deterministic provider adapter without network access.
            adapter = FakeAdapter(provider)
            # Retain it only for the current test's generated-state handoff.
            self.adapters.append(adapter)
            # Return the isolated request-local adapter.
            return adapter
        # Return a test service whose adapters never use credentials or provider network access.
        return OAuthService(environ={} if environment is None else environment, storage=self.storage, adapter_factory=adapter_factory)

    # Build a minimal browser context with the stable owner cookie.
    def context(self, cookie=BROWSER_COOKIE):
        # Return only headers, client class, and response settings used by orchestration.
        return {"headers": {"Cookie": f"casino_csrf={cookie}", "X-Csrf-Token": cookie}, "client": "synthetic-client", "response_headers": [], "include_csrf_cookie": True, "secure_cookie": True, "session_samesite": "Lax"}

    # Read the newest request-local fake adapter state without durable raw proof storage.
    def newest_state(self):
        # Return only the last adapter that generated an authorization URL.
        return next(adapter.state for adapter in reversed(self.adapters) if adapter.state)

    # Prove both providers default unavailable and disabled starts create no flow.
    def test_providers_are_independently_disabled_by_default(self):
        # Construct an empty-environment service.
        service = self.service()
        # Require both public provider booleans to remain false.
        self.assertEqual(service.public_provider_status(), {"providers": [{"provider": "google", "available": False}, {"provider": "facebook", "available": False}]})
        # Reject a start without the explicit complete Google flag contract.
        with self.assertRaises(NotFoundError):
            # Attempt no provider navigation under default settings.
            service.start("google", {"action": "signin", "return_to": "/"}, self.context())
        # Require no durable flow from the rejected start.
        self.assertEqual(self.storage.read_document(FLOW_DOCUMENT_KEY, lambda: {"flows": []})["flows"], [])

    # Prove an unlinked subject cannot sign in even when email matches the invite user.
    def test_unlinked_matching_email_and_replay_fail_for_both_providers(self):
        # Exercise both independently enabled providers through the same no-auto-link policy.
        for provider, environment in (("google", GOOGLE_ENV), ("facebook", FACEBOOK_ENV)):
            # Label only the stable provider identifier.
            with self.subTest(provider=provider):
                # Construct one explicitly enabled synthetic provider service.
                service = self.service(environment)
                # Suppress audit filesystem writes and inject the canonical lookup only.
                with patch("casino.core.oauth.service.logger.info"), patch("casino.core.oauth.service.auth.find_user_by_id", return_value=self.user):
                    # Start provider sign-in without a user target.
                    service.start(provider, {"action": "signin", "return_to": "/"}, self.context())
                    # Read the server-generated state only from isolated persistence.
                    state = self.newest_state()
                    # Reject the first-use identity despite matching email metadata.
                    with self.assertRaises(UnauthorizedError):
                        # Complete no local session or user creation for an unlinked subject.
                        service.callback(provider, {"state": state, "code": "synthetic-code"}, self.context())
                    # Reject replay after the first callback atomically consumed the flow.
                    with self.assertRaises(UnauthorizedError):
                        # Attempt the same state a second time.
                        service.callback(provider, {"state": state, "code": "another-code"}, self.context())

    # Prove linking requires current canonical authentication and explicit confirmation.
    def test_explicit_link_then_prelinked_signin_succeeds(self):
        # Construct the enabled Google service over shared test persistence.
        service = self.service(GOOGLE_ENV)
        # Require explicit confirmation before any authentication or flow record.
        with self.assertRaises(ValidationError):
            # Attempt an unconfirmed link.
            service.start("google", {"action": "link", "return_to": "/"}, self.context())
        # Inject the current local session, active user, canonical lookup, and cookie builder.
        with patch("casino.core.oauth.service.logger.info"), patch("casino.core.oauth.service.auth.authenticate_headers", return_value=(self.session, self.user)), patch("casino.core.oauth.service.auth.find_user_by_id", return_value=self.user), patch("casino.core.oauth.service.auth.session_cookie_headers", return_value=[("Set-Cookie", "synthetic")]), patch("casino.core.oauth.service.auth.create_session", return_value={**self.session, "auth_method": "google"}) as create_session:
            # Reject a public-route cookie proof that does not match the authenticated session CSRF value.
            with self.assertRaises(ForbiddenError):
                # Attempt linking with a different generated-shape browser proof.
                service.start("google", {"action": "link", "return_to": "/", "confirm_link": True}, self.context("d" * 43))
            # Start the explicitly confirmed authenticated linking flow.
            service.start("google", {"action": "link", "return_to": "/", "confirm_link": True}, self.context())
            # Complete the link with the initiating session and browser.
            linked_context = self.context()
            # Invoke the exact one-time callback.
            result = service.callback("google", {"state": self.newest_state(), "code": "synthetic-code"}, linked_context)
            # Require link completion and a safe server-owned local redirect.
            self.assertEqual((result["status"], linked_context["redirect"]), ("linked", "/?oauth_provider=google&oauth_status=linked"))
            # Require linking not to create a replacement session.
            create_session.assert_not_called()
            # Start a new provider-only sign-in with no canonical target.
            service.start("google", {"action": "signin", "return_to": "/"}, self.context())
            # Complete sign-in through the now-durable provider-subject link.
            signin_context = self.context()
            # Exchange and issue one provider-tagged Casino session.
            signed_in = service.callback("google", {"state": self.newest_state(), "code": "synthetic-code-2"}, signin_context)
            # Require successful local-session completion and a safe redirect.
            self.assertEqual((signed_in["status"], signin_context["redirect"]), ("signed_in", "/?oauth_provider=google&oauth_status=signed_in"))
            # Require the canonical user and provider method at session issuance.
            create_session.assert_called_once_with(self.user, "synthetic-client", auth_method="google")

    # Prove duplicate callback parameters and browser-owner drift fail before exchange.
    def test_duplicate_parameters_and_browser_drift_fail_closed(self):
        # Construct the enabled service.
        service = self.service(GOOGLE_ENV)
        # Suppress secret-free audit writes for this focused callback test.
        with patch("casino.core.oauth.service.logger.info"):
            # Start one fresh sign-in flow.
            service.start("google", {"action": "signin", "return_to": "/"}, self.context())
            # Retain the generated state only inside this test method.
            state = self.newest_state()
            # Reject duplicate state before any durable claim.
            with self.assertRaises(ValidationError):
                # Supply two identical values so last-value flattening cannot occur.
                service.callback("google", {"state": [state, state], "code": "synthetic-code"}, self.context())
            # Reject a different browser cookie against the still-pending state.
            with self.assertRaises(UnauthorizedError):
                # Attempt callback ownership drift without token exchange.
                service.callback("google", {"state": state, "code": "synthetic-code"}, self.context("d" * 43))

    # Prove link start rejects caller-selected identities and unsafe redirects.
    def test_start_rejects_account_targets_and_open_redirects(self):
        # Construct the enabled service.
        service = self.service(GOOGLE_ENV)
        # Define target-selection and redirect attacks.
        cases = ({"action": "signin", "email": "invite@example.invalid"}, {"action": "signin", "user_id": self.user["user_id"]}, {"action": "signin", "subject": "provider-subject"}, {"action": "signin", "unexpected": True}, {"return_to": "/"}, {"action": "signin", "return_to": "https://attacker.invalid"}, {"action": "signin", "return_to": "//attacker.invalid"})
        # Require each attack to fail before flow persistence.
        for index, body in enumerate(cases):
            # Label only the bounded case index.
            with self.subTest(case=index):
                # Reject provider-driven identity targeting or open redirect destinations.
                with self.assertRaises(ValidationError):
                    # Attempt no durable flow for the invalid start.
                    service.start("google", body, self.context())
        # Require unlink to reject identity targets even when explicit confirmation is present.
        with self.assertRaises(ValidationError):
            # Attempt an unsupported current-user target before any link or session mutation.
            service.unlink("google", {"confirm_unlink": True, "user_id": self.user["user_id"]}, {"user": self.user})

    # Prove disabling a provider or unlinking immediately invalidates its sessions only.
    def test_provider_session_authorization_tracks_flag_and_link(self):
        # Construct the enabled service and one durable synthetic link.
        service = self.service(GOOGLE_ENV)
        # Save the exact provider-subject to canonical-user binding.
        service.links.save(ExternalIdentityLink(provider="google", subject="google-subject", user_id=self.user["user_id"], created_at="2026-07-19T00:00:00.000Z", updated_at="2026-07-19T00:00:00.000Z"))
        # Define a provider-authenticated session for the linked active user.
        provider_session = {**self.session, "auth_method": "google"}
        # Require the enabled provider and retained link to authorize the session.
        self.assertTrue(provider_session_is_authorized(provider_session, self.user, environ=GOOGLE_ENV, storage=self.storage))
        # Require flag rollback to invalidate the same provider session immediately.
        self.assertFalse(provider_session_is_authorized(provider_session, self.user, environ={}, storage=self.storage))
        # Delete only the exact user-provider binding.
        service.links.delete_for_user("google", self.user["user_id"])
        # Require unlink to invalidate the provider session even if configuration remains ready.
        self.assertFalse(provider_session_is_authorized(provider_session, self.user, environ=GOOGLE_ENV, storage=self.storage))
        # Preserve a legacy/local password session without provider configuration.
        self.assertTrue(provider_session_is_authorized(self.session, self.user, environ={}, storage=self.storage))

    # Prove configuration readiness alone cannot construct a provider adapter.
    def test_network_release_gate_prevents_adapter_construction(self):
        # Build complete provider settings while leaving the independent network latch false.
        environment = {key: value for key, value in GOOGLE_ENV.items() if key != "CASINO_OAUTH_NETWORK_RELEASED_GOOGLE"}
        # Count every adapter-construction attempt without retaining credentials.
        constructions = []
        # Build one factory that would reveal a release-gate failure without using network.
        def factory(provider, _client_id, _client_secret):
            # Record only the bounded provider identifier.
            constructions.append(provider)
            # Return an inert fake if the policy incorrectly reaches this boundary.
            return FakeAdapter(provider)
        # Construct the service with complete configuration but no release authority.
        service = OAuthService(environ=environment, storage=self.storage, adapter_factory=factory)
        # Reject provider start as unavailable under the independent gate.
        with self.assertRaises(NotFoundError):
            # Attempt no provider network or flow persistence.
            service.start("google", {"action": "signin", "return_to": "/"}, self.context())
        # Require adapter construction to remain completely inaccessible.
        self.assertEqual(constructions, [])

    # Prove a transient exchange releases the exact flow for one bounded same-state retry.
    def test_transient_exchange_failure_preserves_recoverable_flow(self):
        # Count request-local adapter constructions so only the first callback fails.
        constructions = {"count": 0}
        # Build deterministic adapters without any provider network access.
        def factory(provider, _client_id, _client_secret):
            # Advance one local request counter.
            constructions["count"] += 1
            # Fail only the second construction, which is the first callback exchange.
            adapter = FakeAdapter(provider, fail_exchange=constructions["count"] == 2)
            # Retain request-local generated state for this test.
            self.adapters.append(adapter)
            # Return the bounded fake adapter.
            return adapter
        # Construct the service under complete synthetic dual-gate configuration.
        service = OAuthService(environ=GOOGLE_ENV, storage=self.storage, adapter_factory=factory)
        # Prelink one provider subject so a recovered sign-in can complete without email matching.
        service.links.save(ExternalIdentityLink(provider="google", subject="google-subject", user_id=self.user["user_id"], created_at="2026-07-19T00:00:00.000Z", updated_at="2026-07-19T00:00:00.000Z"))
        # Suppress test audit writes and inject only canonical session dependencies.
        with patch("casino.core.oauth.service.logger.info"), patch("casino.core.oauth.service.auth.find_user_by_id", return_value=self.user), patch("casino.core.oauth.service.auth.session_cookie_headers", return_value=[]), patch("casino.core.oauth.service.auth.create_session", return_value={**self.session, "auth_method": "google"}):
            # Start one browser-bound provider sign-in.
            service.start("google", {"action": "signin", "return_to": "/"}, self.context())
            # Retain state only from the request-local fake adapter.
            state = self.newest_state()
            # Return a stable 503 while preserving the original flow proof and expiry.
            with self.assertRaises(ProviderUnavailableError):
                # Simulate the first transient provider exchange.
                service.callback("google", {"state": state, "code": "synthetic-code"}, self.context())
            # Retry the exact same callback after the durable claim was released.
            context = self.context()
            # Complete provider sign-in through the prior durable identity link.
            result = service.callback("google", {"state": state, "code": "synthetic-code"}, context)
            # Require the recovered flow to complete exactly once.
            self.assertEqual((result["status"], context["redirect"]), ("signed_in", "/?oauth_provider=google&oauth_status=signed_in"))


# Run focused tests when invoked directly.
if __name__ == "__main__":
    # Delegate reporting and status to unittest.
    unittest.main()
