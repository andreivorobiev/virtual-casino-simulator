# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused OAuth provider abstraction and claim-normalization tests for issue #70.

Requirements: OAUTH-005, USER-001, and TEST-045.
"""

# Import unittest so focused tests run without third-party dependencies.
import unittest

# Import the provider-neutral port and identity model for mock coverage.
from casino.core.oauth.models import OAuthProviderPort, VerifiedIdentity
# Import static provider definitions and allowlisted normalizers.
from casino.core.oauth.providers import FACEBOOK_SPEC, GOOGLE_SPEC, get_provider_spec, normalize_facebook_identity, normalize_google_identity
# Import the standard validation error for malformed claim assertions.
from casino.errors import ValidationError


# Implement a service-free provider port used only to exercise dependency injection.
class MockOAuthProvider:
    # Use the static Google spec without any live endpoint or credential.
    spec = GOOGLE_SPEC

    # Build a synthetic authorization URL without network traffic.
    def authorization_url(self, *, redirect_uri: str, state: str, nonce: str, pkce_challenge: str | None) -> str:
        # Require the Google mock's applicable nonce and PKCE context.
        if not nonce or not pkce_challenge:
            # Reject incomplete mock security context without provider traffic.
            raise ValidationError("Mock Google authorization security context is incomplete")
        # Return a deterministic mock URL suitable only for interface tests.
        return f"mock://authorize?redirect={len(redirect_uri)}&state={len(state)}&nonce={len(nonce)}&pkce={len(pkce_challenge or '')}"

    # Exchange a synthetic code entirely in memory.
    def exchange_code(self, *, code: str, redirect_uri: str, expected_nonce: str | None, pkce_verifier: str | None) -> VerifiedIdentity:
        # Require the Google mock's applicable retained nonce and PKCE verifier.
        if not expected_nonce or not pkce_verifier:
            # Reject incomplete mock exchange context before producing an identity.
            raise ValidationError("Mock Google exchange security context is incomplete")
        # Return a provider-neutral identity without retaining the code or redirect URI.
        return VerifiedIdentity(provider="google", subject="mock-subject", email_verified=True)


# Consume the provider port exactly as future integration code would consume an injected adapter.
def _use_mock_provider(provider: OAuthProviderPort) -> VerifiedIdentity:
    # Build a synthetic authorization URL to verify the port shape.
    provider.authorization_url(redirect_uri="http://localhost:8766/callback", state="s" * 43, nonce="n" * 43, pkce_challenge="p" * 43)
    # Return an in-memory identity from the synthetic exchange.
    return provider.exchange_code(code="synthetic-code", redirect_uri="http://localhost:8766/callback", expected_nonce="n" * 43, pkce_verifier="v" * 43)


# Validate static provider metadata and allowlisted identity normalization.
class ProviderAbstractionTests(unittest.TestCase):
    # Verify the static provider catalog preserves local login and minimum scopes.
    def test_provider_specs_are_minimal_and_exact(self):
        # Assert local password login remains enabled by default.
        self.assertTrue(get_provider_spec("local").enabled_by_default)
        # Assert Google requests only OpenID Connect identity scopes.
        self.assertEqual(GOOGLE_SPEC.scopes, ("openid", "email", "profile"))
        # Assert Facebook requests only public profile and email.
        self.assertEqual(FACEBOOK_SPEC.scopes, ("public_profile", "email"))
        # Assert unknown or case-drifted provider identifiers fail closed.
        with self.assertRaises(ValidationError):
            # Resolve no implicit provider alias.
            get_provider_spec("Google")

    # Verify Google claims are reduced to the allowlisted provider-neutral model.
    def test_google_claims_are_allowlisted_and_repr_safe(self):
        # Define synthetic personal and token values that must not leak through representations.
        claims = {"sub": "google-subject-123", "email": "User@Example.Test", "email_verified": True, "name": "Synthetic User", "picture": "https://images.example.test/avatar.png", "access_token": "synthetic-access-token", "refresh_token": "synthetic-refresh-token"}
        # Normalize the mocked claims without provider traffic.
        identity = normalize_google_identity(claims)
        # Assert provider identity and normalized email behavior.
        self.assertEqual(identity.provider, "google")
        # Assert email normalization does not imply automatic linking.
        self.assertEqual(identity.email, "user@example.test")
        # Assert the explicit provider verification flag is retained.
        self.assertTrue(identity.email_verified)
        # Assert personal subject data is absent from repr output.
        self.assertNotIn(claims["sub"], repr(identity))
        # Assert email data is absent from repr output.
        self.assertNotIn(claims["email"].lower(), repr(identity))
        # Assert token fields are never retained or represented.
        self.assertNotIn(claims["access_token"], repr(identity))
        # Assert diagnostics contain only presence booleans.
        self.assertNotIn(claims["name"], repr(identity.diagnostic()))
        # Normalize a subject with significant surrounding whitespace.
        opaque_identity = normalize_google_identity({"sub": " opaque-subject "})
        # Assert provider subjects remain byte-for-byte opaque compound keys.
        self.assertEqual(opaque_identity.subject, " opaque-subject ")

    # Verify Facebook claims are reduced without inventing verified email.
    def test_facebook_claims_are_allowlisted_without_email_trust(self):
        # Define one mocked provider payload with a nested HTTPS picture.
        claims = {"id": "facebook-subject-456", "email": "person@example.test", "name": "Synthetic Person", "picture": {"data": {"url": "https://images.example.test/facebook.png"}}}
        # Normalize the mocked claims without provider traffic.
        identity = normalize_facebook_identity(claims)
        # Assert the provider identifier is exact.
        self.assertEqual(identity.provider, "facebook")
        # Assert optional email is normalized for display-only metadata.
        self.assertEqual(identity.email, "person@example.test")
        # Assert Facebook email is not treated as explicitly verified by this package.
        self.assertFalse(identity.email_verified)
        # Assert the safe HTTPS avatar is retained in the in-memory identity.
        self.assertEqual(identity.avatar_url, "https://images.example.test/facebook.png")
        # Normalize a Facebook subject with significant surrounding whitespace.
        opaque_identity = normalize_facebook_identity({"id": " opaque-facebook-subject "})
        # Assert the distinct provider normalizer also preserves opaque subjects exactly.
        self.assertEqual(opaque_identity.subject, " opaque-facebook-subject ")

    # Verify malformed required claims fail and unsafe optional avatars are ignored.
    def test_claim_validation_fails_closed(self):
        # Assert a Google identity without a subject is rejected.
        with self.assertRaises(ValidationError):
            # Normalize no provider subject.
            normalize_google_identity({"email": "user@example.test"})
        # Assert malformed optional email is rejected without reflection.
        with self.assertRaises(ValidationError):
            # Normalize a mocked payload with invalid email syntax.
            normalize_facebook_identity({"id": "subject", "email": "not an email"})
        # Assert control-bearing optional email data is rejected without reflection.
        with self.assertRaises(ValidationError):
            # Normalize no email containing an embedded NUL character.
            normalize_google_identity({"sub": "subject", "email": "user@example.test\x00"})
        # Assert control-bearing optional display names are rejected without reflection.
        with self.assertRaises(ValidationError):
            # Normalize no display name containing a DEL character.
            normalize_facebook_identity({"id": "subject", "name": "unsafe\x7fname"})
        # Normalize an otherwise valid identity with an unsafe avatar scheme.
        identity = normalize_google_identity({"sub": "subject", "picture": "http://images.example.test/avatar.png"})
        # Assert unsafe optional avatar data is discarded.
        self.assertIsNone(identity.avatar_url)
        # Normalize an otherwise valid identity with malformed bracket syntax.
        malformed_avatar_identity = normalize_google_identity({"sub": "subject", "picture": "https://[broken"})
        # Assert malformed optional avatar data is safely discarded.
        self.assertIsNone(malformed_avatar_identity.avatar_url)
        # Normalize a Google identity whose avatar authority has a non-numeric port.
        malformed_google_port_identity = normalize_google_identity({"sub": "subject", "picture": "https://images.example.test:not-a-port/avatar.png"})
        # Assert deferred Google URL port parsing fails closed.
        self.assertIsNone(malformed_google_port_identity.avatar_url)
        # Normalize a Facebook identity whose nested avatar authority has a non-numeric port.
        malformed_facebook_port_identity = normalize_facebook_identity({"id": "subject", "picture": {"data": {"url": "https://images.example.test:not-a-port/avatar.png"}}})
        # Assert deferred Facebook URL port parsing fails closed.
        self.assertIsNone(malformed_facebook_port_identity.avatar_url)
        # Normalize an identity whose avatar contains parser-stripped control characters.
        control_avatar_identity = normalize_google_identity({"sub": "subject", "picture": "https://images.example.test/avatar.png\r\n"})
        # Assert the original control-bearing avatar string is never retained.
        self.assertIsNone(control_avatar_identity.avatar_url)

    # Verify future integration can use an injected provider port without network dependencies.
    def test_mock_provider_port_is_service_free(self):
        # Exchange a synthetic code through the in-memory mock adapter.
        identity = _use_mock_provider(MockOAuthProvider())
        # Assert the mock returns the provider-neutral identity model.
        self.assertIsInstance(identity, VerifiedIdentity)
        # Assert the mock provider identifier is preserved.
        self.assertEqual(identity.provider, "google")
        # Create the isolated Google mock for missing-context checks.
        provider = MockOAuthProvider()
        # Assert applicable nonce and PKCE context cannot be omitted at authorization start.
        with self.assertRaises(ValidationError):
            # Build no URL when the PKCE challenge is absent.
            provider.authorization_url(redirect_uri="http://localhost:8766/callback", state="s" * 43, nonce="n" * 43, pkce_challenge=None)
        # Assert applicable nonce and PKCE context cannot be omitted at code exchange.
        with self.assertRaises(ValidationError):
            # Exchange no code when retained proof context is absent.
            provider.exchange_code(code="synthetic-code", redirect_uri="http://localhost:8766/callback", expected_nonce=None, pkce_verifier=None)


# Run focused tests when this file is invoked directly.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
