# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Mock-network Google and Facebook adapter tests for issue #326.

Requirements: OAUTH-003, OAUTH-005, OAUTH-010, SEC-010, and TEST-045.
"""

# Import URL-safe encoding for runtime-generated JWT fixtures.
import base64
# Import JSON encoding for compact signed-token construction.
import json
# Import cryptographic randomness so no token value is stored in the repository.
import secrets
# Import Unix time for provider expiry fixtures.
import time
# Import unittest for focused execution.
import unittest

# Import RSA signing primitives already required by the runtime dependency contract.
from cryptography.hazmat.primitives import hashes
# Import RSA padding and key generation for synthetic signed ID tokens.
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# Import concrete adapters and fixed endpoint identifiers for deterministic fakes.
from casino.core.oauth.adapters import FACEBOOK_DEBUG_ENDPOINT, FACEBOOK_PROFILE_ENDPOINT, FACEBOOK_TOKEN_ENDPOINT, GOOGLE_JWKS_ENDPOINT, GOOGLE_TOKEN_ENDPOINT, FacebookOAuthAdapter, GoogleOAuthAdapter
# Import stable provider authentication failures.
from casino.errors import UnauthorizedError


# Encode compact JSON or bytes as unpadded base64url.
def encoded(value) -> str:
    # Serialize mappings deterministically and preserve byte signatures unchanged.
    raw = value if isinstance(value, bytes) else json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    # Return the compact unpadded representation required by JWT and JWK.
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# Build one runtime-generated signed Google token and matching public JWK.
def google_fixture(claim_overrides=None, signing_key=None):
    # Generate a private key only in test memory when one was not supplied.
    private_key = signing_key or rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Read the public RSA numbers needed by Google's JWK shape.
    public_numbers = private_key.public_key().public_numbers()
    # Generate a non-secret synthetic key identifier for this test token.
    key_id = "synthetic-key"
    # Build the only accepted JOSE header.
    header = {"alg": "RS256", "kid": key_id, "typ": "JWT"}
    # Create fully valid OIDC claims using no real account data.
    claims = {"iss": "https://accounts.google.com", "aud": "synthetic-client", "sub": "synthetic-subject", "exp": int(time.time()) + 600, "iat": int(time.time()), "nonce": "n" * 43, "email": "display@example.invalid", "email_verified": True, "name": "Synthetic Display"}
    # Apply the focused negative-test claim mutation.
    claims.update(claim_overrides or {})
    # Construct the exact compact signed input.
    signed = f"{encoded(header)}.{encoded(claims)}".encode("ascii")
    # Sign with RSASSA-PKCS1-v1_5 and SHA-256 like Google's RS256 tokens.
    signature = private_key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    # Assemble the request-local compact token.
    token = signed.decode("ascii") + "." + encoded(signature)
    # Publish only the matching public key material to the fake JWK endpoint.
    jwk = {"keys": [{"kid": key_id, "kty": "RSA", "alg": "RS256", "use": "sig", "n": encoded(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")), "e": encoded(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big"))}]}
    # Return runtime-only token, JWK, and signing key for focused mutations.
    return token, jwk, private_key


# Provide a strict endpoint-keyed transport without sockets or provider credentials.
class FakeTransport:
    # Initialize exact response maps and request metadata.
    def __init__(self, *, posts=None, gets=None):
        # Retain synthetic mapping responses only for this test instance.
        self.posts = posts or {}
        # Retain synthetic GET mapping responses only for this test instance.
        self.gets = gets or {}
        # Collect endpoint and field names without logging field values.
        self.calls = []

    # Return one fixed GET response for an adapter-owned URL.
    def get_json(self, url, headers=None):
        # Record only the endpoint and header names for leakage assertions.
        self.calls.append(("GET", url, tuple(sorted((headers or {}).keys()))))
        # Return the preconfigured response mapping.
        return self.gets[url]

    # Return one fixed form response for an adapter-owned URL.
    def post_form(self, url, form, headers=None):
        # Record only the endpoint and form/header names, never their sensitive values.
        self.calls.append(("POST", url, tuple(sorted(form.keys())), tuple(sorted((headers or {}).keys()))))
        # Return the preconfigured response mapping.
        return self.posts[url]


# Validate full Google OIDC and Facebook token/app behavior without network access.
class OAuthAdapterTests(unittest.TestCase):
    # Prove a fully signed Google token validates every required binding.
    def test_google_validates_signature_issuer_audience_expiry_nonce_and_email(self):
        # Create a runtime-only signed token and matching public key.
        token, jwks, _key = google_fixture()
        # Inject exact token and JWK endpoint responses.
        transport = FakeTransport(posts={GOOGLE_TOKEN_ENDPOINT: {"id_token": token}}, gets={GOOGLE_JWKS_ENDPOINT: jwks})
        # Construct the adapter with synthetic configuration and no live transport.
        adapter = GoogleOAuthAdapter("synthetic-client", "synthetic-secret", transport)
        # Exchange a synthetic runtime code and require a verified provider identity.
        identity = adapter.exchange_code(code=secrets.token_urlsafe(24), redirect_uri="https://casino.example.test/api/v2/auth/oauth/google/callback", expected_nonce="n" * 43, pkce_verifier="v" * 64)
        # Assert subject is the identity key and verified email is metadata only.
        self.assertEqual((identity.provider, identity.subject, identity.email_verified), ("google", "synthetic-subject", True))
        # Require the code, secret, callback, and verifier to remain in a POST body boundary.
        self.assertEqual(transport.calls[0][0:2], ("POST", GOOGLE_TOKEN_ENDPOINT))

    # Prove each signed Google claim boundary independently fails closed.
    def test_google_rejects_claim_and_signature_failures(self):
        # Define invalid signed claim mutations with no token literals in source.
        cases = ({"iss": "https://issuer.invalid"}, {"aud": "other-client"}, {"exp": int(time.time()) - 600}, {"nonce": "x" * 43}, {"email_verified": False})
        # Exercise each complete signed but unacceptable token.
        for index, overrides in enumerate(cases):
            # Label only the stable numeric mutation index.
            with self.subTest(case=index):
                # Sign the invalid claims so failure cannot be attributed to malformed serialization.
                token, jwks, _key = google_fixture(overrides)
                # Inject the signed token and its matching key.
                adapter = GoogleOAuthAdapter("synthetic-client", "synthetic-secret", FakeTransport(posts={GOOGLE_TOKEN_ENDPOINT: {"id_token": token}}, gets={GOOGLE_JWKS_ENDPOINT: jwks}))
                # Require a fixed authentication failure before identity normalization.
                with self.assertRaises(UnauthorizedError):
                    # Attempt exchange with otherwise valid retained flow material.
                    adapter.exchange_code(code=secrets.token_urlsafe(24), redirect_uri="https://casino.example.test/api/v2/auth/oauth/google/callback", expected_nonce="n" * 43, pkce_verifier="v" * 64)
        # Generate a valid token and an unrelated public-key set.
        token, _signed_jwks, _key = google_fixture()
        # Generate another key set with the same identifier but different modulus.
        _other_token, unrelated_jwks, _other_key = google_fixture()
        # Construct the signature-confusion test adapter.
        adapter = GoogleOAuthAdapter("synthetic-client", "synthetic-secret", FakeTransport(posts={GOOGLE_TOKEN_ENDPOINT: {"id_token": token}}, gets={GOOGLE_JWKS_ENDPOINT: unrelated_jwks}))
        # Reject the token when signature verification uses an unrelated public key.
        with self.assertRaises(UnauthorizedError):
            # Attempt no identity resolution after signature failure.
            adapter.exchange_code(code=secrets.token_urlsafe(24), redirect_uri="https://casino.example.test/api/v2/auth/oauth/google/callback", expected_nonce="n" * 43, pkce_verifier="v" * 64)

    # Prove Facebook token debug binds validity, app, expiry, scope, and subject.
    def test_facebook_debugs_token_and_matches_profile_subject(self):
        # Generate a request-local access token rather than storing a fixture token.
        access_token = secrets.token_urlsafe(32)
        # Build a valid app-bound debug response with minimum scopes.
        debug = {"data": {"is_valid": True, "type": "USER", "app_id": "synthetic-app", "expires_at": int(time.time()) + 600, "data_access_expires_at": int(time.time()) + 600, "scopes": ["public_profile", "email"], "user_id": "facebook-subject"}}
        # Build allowlisted profile metadata with the same provider subject.
        profile = {"id": "facebook-subject", "name": "Synthetic Display", "email": "display@example.invalid"}
        # Inject every Graph response without network access.
        transport = FakeTransport(posts={FACEBOOK_TOKEN_ENDPOINT: {"access_token": access_token}, FACEBOOK_DEBUG_ENDPOINT: debug}, gets={FACEBOOK_PROFILE_ENDPOINT: profile})
        # Construct the adapter with synthetic app configuration.
        adapter = FacebookOAuthAdapter("synthetic-app", "synthetic-secret", transport)
        # Exchange a runtime-generated code and require the debugged subject.
        identity = adapter.exchange_code(code=secrets.token_urlsafe(24), redirect_uri="https://casino.example.test/api/v2/auth/oauth/facebook/callback", expected_nonce="n" * 43, pkce_verifier="v" * 64)
        # Assert the provider subject is authoritative while email remains unverified metadata.
        self.assertEqual((identity.provider, identity.subject, identity.email_verified), ("facebook", "facebook-subject", False))
        # Require profile retrieval to use a bearer header without a token-bearing URL.
        self.assertEqual(transport.calls[-1], ("GET", FACEBOOK_PROFILE_ENDPOINT, ("Authorization",)))

    # Prove Facebook rejects app, expiry, scope, and profile-subject drift.
    def test_facebook_rejects_debug_and_profile_failures(self):
        # Define isolated invalid debug mutations.
        cases = ({"app_id": "other-app"}, {"expires_at": int(time.time()) - 600}, {"scopes": ["email"]}, {"user_id": "different-subject"})
        # Exercise each invalid token/app binding.
        for index, mutation in enumerate(cases):
            # Label only the stable numeric case.
            with self.subTest(case=index):
                # Build a fresh valid baseline debug response.
                data = {"is_valid": True, "type": "USER", "app_id": "synthetic-app", "expires_at": int(time.time()) + 600, "scopes": ["public_profile", "email"], "user_id": "facebook-subject"}
                # Apply the selected invalid field.
                data.update(mutation)
                # Inject a matching normal profile so only the selected check fails.
                transport = FakeTransport(posts={FACEBOOK_TOKEN_ENDPOINT: {"access_token": secrets.token_urlsafe(32)}, FACEBOOK_DEBUG_ENDPOINT: {"data": data}}, gets={FACEBOOK_PROFILE_ENDPOINT: {"id": "facebook-subject"}})
                # Construct the isolated adapter.
                adapter = FacebookOAuthAdapter("synthetic-app", "synthetic-secret", transport)
                # Require a fixed authentication failure.
                with self.assertRaises(UnauthorizedError):
                    # Attempt exchange without real provider I/O.
                    adapter.exchange_code(code=secrets.token_urlsafe(24), redirect_uri="https://casino.example.test/api/v2/auth/oauth/facebook/callback", expected_nonce="n" * 43, pkce_verifier="v" * 64)


# Run focused tests when invoked directly.
if __name__ == "__main__":
    # Delegate reporting and status to unittest.
    unittest.main()
