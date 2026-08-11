# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Live Google and Facebook authorization-code adapters with injectable transport.

Requirements: OAUTH-003, OAUTH-005, AUTH-004, and SEC-010. Tokens, codes, claims,
credentials, state, nonce, and PKCE material remain request-local and are never logged.
"""

# Import URL-safe decoding for Google JWT and JWK validation.
import base64
# Import constant-time comparison for provider identifiers and nonce claims.
import hmac
# Import strict JSON decoding for signed Google JWT components.
import json
# Import time so provider expiry checks can use an injectable current timestamp.
import time
# Import mapping types for bounded provider payload validation.
from typing import Mapping
# Import URL query encoding for provider authorization redirects.
from urllib.parse import urlencode

# Import provider-neutral identity models and static provider definitions.
from casino.core.oauth.models import VerifiedIdentity
# Import Facebook claim normalization after token/app verification.
from casino.core.oauth.providers.facebook import FACEBOOK_SPEC, normalize_facebook_identity
# Import Google claim normalization after complete OIDC verification.
from casino.core.oauth.providers.google import GOOGLE_SPEC, normalize_google_identity
# Import the injectable HTTPS transport contract and production implementation.
from casino.core.oauth.transport import OAuthHttpTransport, UrlLibOAuthTransport
# Import bounded public error classes without provider response values.
from casino.errors import ProviderUnavailableError, UnauthorizedError, ValidationError

# Use Google's published authorization-code endpoint.
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
# Use Google's published confidential-client token endpoint.
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# Use Google's published OIDC JWK set for local signature verification.
GOOGLE_JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"
# Accept the two issuer strings documented for Google ID tokens.
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
# Pin a supported Graph API version for reviewable Facebook token and profile semantics.
FACEBOOK_GRAPH_VERSION = "v23.0"
# Use Facebook's web authorization dialog for the server authorization-code flow.
FACEBOOK_AUTHORIZATION_ENDPOINT = f"https://www.facebook.com/{FACEBOOK_GRAPH_VERSION}/dialog/oauth"
# Use the versioned Graph token endpoint for server-side code exchange.
FACEBOOK_TOKEN_ENDPOINT = f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/oauth/access_token"
# Use token debugging to prove validity and the configured app binding.
FACEBOOK_DEBUG_ENDPOINT = f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/debug_token"
# Read the provider subject and display-only profile only after debug-token acceptance.
FACEBOOK_PROFILE_ENDPOINT = f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/me?fields=id,name,email,picture"
# Bound JWT components before base64 or JSON decoding.
MAX_JWT_COMPONENT_LENGTH = 16_384
# Allow one minute of provider/host clock skew without accepting stale tokens.
TOKEN_CLOCK_SKEW_SECONDS = 60


# Decode one unpadded base64url JWT or JWK component under a strict size bound.
def _base64url_decode(value: object) -> bytes:
    # Require bounded ASCII text before allocating decoded bytes.
    if not isinstance(value, str) or not value or len(value) > MAX_JWT_COMPONENT_LENGTH:
        # Reject malformed signed data without echoing it.
        raise UnauthorizedError("Provider identity token is invalid")
    # Reject characters outside the base64url alphabet before tolerant decoder padding.
    if any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for character in value):
        # Preserve one fixed token-validation failure.
        raise UnauthorizedError("Provider identity token is invalid")
    # Add only the required canonical base64 padding.
    padded = value + "=" * (-len(value) % 4)
    # Start protected decoding so malformed provider input remains value-free.
    try:
        # Decode as URL-safe base64 into request-local bytes.
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    # Collapse decoder failures into the fixed authentication error.
    except (ValueError, UnicodeEncodeError):
        # Suppress decoder details and supplied token material.
        raise UnauthorizedError("Provider identity token is invalid") from None


# Decode one JWT JSON component and require a mapping result.
def _jwt_mapping(component: str) -> Mapping[str, object]:
    # Start protected UTF-8 and JSON decoding of the already bounded bytes.
    try:
        # Decode the signed component without retaining the raw token after this call.
        payload = json.loads(_base64url_decode(component).decode("utf-8"))
    # Collapse malformed JSON into one authentication failure.
    except (UnicodeDecodeError, json.JSONDecodeError):
        # Suppress parser details and token material.
        raise UnauthorizedError("Provider identity token is invalid") from None
    # Require an object because arrays and scalars cannot carry validated claims.
    if not isinstance(payload, Mapping):
        # Reject unexpected signed payload shapes.
        raise UnauthorizedError("Provider identity token is invalid")
    # Return the request-local mapping to the validating adapter.
    return payload


# Parse a JSON Web Token into signed input, header, claims, and signature.
def _parse_jwt(token: object) -> tuple[bytes, Mapping[str, object], Mapping[str, object], bytes]:
    # Require bounded text before splitting the sensitive token.
    if not isinstance(token, str) or not token or len(token) > 32_768:
        # Reject absent or oversized ID tokens.
        raise UnauthorizedError("Provider identity token is invalid")
    # Split the compact serialization into exactly three components.
    parts = token.split(".")
    # Reject detached, encrypted, or otherwise ambiguous token forms.
    if len(parts) != 3:
        # Preserve the same fixed authentication failure.
        raise UnauthorizedError("Provider identity token is invalid")
    # Encode the signed input exactly as received for signature verification.
    try:
        # Preserve the ASCII compact header and payload bytes.
        signed = f"{parts[0]}.{parts[1]}".encode("ascii")
    # Reject non-ASCII compact serialization.
    except UnicodeEncodeError:
        # Suppress token material and encoding details.
        raise UnauthorizedError("Provider identity token is invalid") from None
    # Return decoded mappings and signature while keeping every value request-local.
    return signed, _jwt_mapping(parts[0]), _jwt_mapping(parts[1]), _base64url_decode(parts[2])


# Convert one provider numeric claim without accepting booleans or non-integers.
def _integer_claim(claims: Mapping[str, object], name: str) -> int:
    # Read the claim without stringifying it.
    value = claims.get(name)
    # Reject booleans and non-integer claim values.
    if isinstance(value, bool) or not isinstance(value, int):
        # Use one fixed authentication failure without naming supplied data.
        raise UnauthorizedError("Provider identity token is invalid")
    # Return the exact integer for expiry or issued-at validation.
    return value


# Verify a Google RS256 signature against one exact JWK key id.
def _verify_google_signature(signed: bytes, signature: bytes, header: Mapping[str, object], jwks: Mapping[str, object]) -> None:
    # Require the only accepted asymmetric algorithm and a bounded key identifier.
    key_id = header.get("kid")
    # Reject algorithm substitution and absent or oversized key ids.
    if header.get("alg") != "RS256" or not isinstance(key_id, str) or not key_id or len(key_id) > 256:
        # Stop before selecting or constructing a public key.
        raise UnauthorizedError("Google identity token signature is invalid")
    # Read the public key list only when the provider returned an array.
    keys = jwks.get("keys")
    # Reject malformed JWK metadata through a retryable provider failure.
    if not isinstance(keys, list):
        # Treat unusable provider metadata as temporary provider unavailability.
        raise ProviderUnavailableError()
    # Select exactly one RSA signing key matching the signed key identifier.
    matches = [key for key in keys if isinstance(key, Mapping) and key.get("kid") == key_id and key.get("kty") == "RSA" and key.get("alg") in {None, "RS256"} and key.get("use") in {None, "sig"}]
    # Reject missing or ambiguous rotated key metadata.
    if len(matches) != 1:
        # Do not fall back to another key or algorithm.
        raise UnauthorizedError("Google identity token signature is invalid")
    # Decode the exact modulus and exponent from the selected public JWK.
    modulus = int.from_bytes(_base64url_decode(matches[0].get("n")), "big")
    # Decode the exponent from the same selected public JWK.
    exponent = int.from_bytes(_base64url_decode(matches[0].get("e")), "big")
    # Reject unusable RSA parameters before importing cryptographic primitives.
    if modulus <= 0 or exponent < 3:
        # Preserve one fixed signature failure.
        raise UnauthorizedError("Google identity token signature is invalid")
    # Start protected cryptography import so missing runtime dependencies fail safely.
    try:
        # Import the invalid-signature marker without exposing backend details.
        from cryptography.exceptions import InvalidSignature
        # Import SHA-256 and PKCS#1 v1.5 verification primitives.
        from cryptography.hazmat.primitives import hashes
        # Import RSA public-number construction for the provider JWK.
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    # Treat a missing reviewed dependency as a provider-runtime availability failure.
    except ImportError:
        # Return the fixed retryable provider envelope.
        raise ProviderUnavailableError() from None
    # Start protected public-key construction and verification.
    try:
        # Construct the public key from the provider-owned RSA parameters.
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
        # Verify the exact compact signed bytes with RSASSA-PKCS1-v1_5 and SHA-256.
        public_key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
    # Collapse invalid signatures and malformed RSA parameters into one failure.
    except (InvalidSignature, ValueError):
        # Suppress key, signature, and cryptographic backend details.
        raise UnauthorizedError("Google identity token signature is invalid") from None


# Validate all required Google OIDC claims after signature verification.
def _validate_google_claims(claims: Mapping[str, object], client_id: str, expected_nonce: str, now: int) -> VerifiedIdentity:
    # Require one of Google's two documented issuer identifiers.
    if claims.get("iss") not in GOOGLE_ISSUERS:
        # Reject tokens issued by any other identity authority.
        raise UnauthorizedError("Google identity token claims are invalid")
    # Read the audience without coercing arrays or arbitrary objects.
    audience = claims.get("aud")
    # Accept one exact string audience for the configured confidential client.
    if isinstance(audience, str):
        # Require constant-time equality with the configured client id.
        audience_valid = hmac.compare_digest(audience, client_id)
    # Accept a multi-audience token only with both membership and exact authorized-party binding.
    elif isinstance(audience, list) and all(isinstance(value, str) for value in audience):
        # Require this client plus an exact azp claim under OIDC multi-audience rules.
        audience_valid = any(hmac.compare_digest(value, client_id) for value in audience) and isinstance(claims.get("azp"), str) and hmac.compare_digest(claims["azp"], client_id)
    # Reject every other audience representation.
    else:
        # Mark the audience invalid without serializing it.
        audience_valid = False
    # Stop on wrong audience before using any identity claim.
    if not audience_valid:
        # Return the fixed Google claims failure.
        raise UnauthorizedError("Google identity token claims are invalid")
    # Require expiry to remain valid beyond the accepted clock-skew window.
    if _integer_claim(claims, "exp") <= now - TOKEN_CLOCK_SKEW_SECONDS:
        # Reject stale signed identities.
        raise UnauthorizedError("Google identity token claims are invalid")
    # Require issued-at not to be materially in the future when present.
    if "iat" in claims and _integer_claim(claims, "iat") > now + TOKEN_CLOCK_SKEW_SECONDS:
        # Reject a token whose chronology cannot be trusted.
        raise UnauthorizedError("Google identity token claims are invalid")
    # Require the signed nonce and expected retained nonce as bounded text.
    nonce = claims.get("nonce")
    # Reject absent or non-text nonce claims before constant-time comparison.
    if not isinstance(nonce, str) or not isinstance(expected_nonce, str) or not nonce or not expected_nonce or not hmac.compare_digest(nonce, expected_nonce):
        # Prevent replay across browser authorization flows.
        raise UnauthorizedError("Google identity token nonce is invalid")
    # Require explicit verified-email metadata whenever Google returned an email for display.
    if claims.get("email") is not None and claims.get("email_verified") is not True:
        # Do not display or retain an unverified provider address.
        raise UnauthorizedError("Google verified email assertion is required")
    # Normalize only the allowlisted identity fields after every security check succeeds.
    return normalize_google_identity(claims)


# Implement the Google confidential web-server authorization-code flow.
class GoogleOAuthAdapter:
    # Expose static credential-free provider metadata through the shared port.
    spec = GOOGLE_SPEC

    # Initialize one adapter with configured credentials and injectable transport/time.
    def __init__(self, client_id: str, client_secret: str, transport: OAuthHttpTransport | None = None, clock=None):
        # Store the public client identifier outside dataclass/object representations used in logs.
        self._client_id = client_id
        # Store the confidential client secret only for request-local token exchange forms.
        self._client_secret = client_secret
        # Use the production bounded transport only when tests did not inject a fake.
        self._transport = transport or UrlLibOAuthTransport()
        # Use Unix time only through an injectable callable for deterministic expiry tests.
        self._clock = time.time if clock is None else clock

    # Build one Google authorization URL bound to state, nonce, callback, and PKCE.
    def authorization_url(self, *, redirect_uri: str, state: str, nonce: str, pkce_challenge: str | None) -> str:
        # Require a PKCE S256 challenge for every Google authorization request.
        if not isinstance(pkce_challenge, str) or not pkce_challenge:
            # Reject a weakened start flow before exposing an authorization URL.
            raise ValidationError("OAuth PKCE challenge is required")
        # Encode only the minimum authentication scopes and server-owned proof values.
        parameters = {"client_id": self._client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": " ".join(self.spec.scopes), "state": state, "nonce": nonce, "code_challenge": pkce_challenge, "code_challenge_method": "S256", "prompt": "select_account"}
        # Return the provider endpoint plus encoded request-local values without logging it.
        return GOOGLE_AUTHORIZATION_ENDPOINT + "?" + urlencode(parameters)

    # Exchange one code and return only a fully verified allowlisted Google identity.
    def exchange_code(self, *, code: str, redirect_uri: str, expected_nonce: str | None, pkce_verifier: str | None) -> VerifiedIdentity:
        # Require retained nonce and PKCE values before any provider request.
        if not isinstance(expected_nonce, str) or not expected_nonce or not isinstance(pkce_verifier, str) or not pkce_verifier:
            # Reject incomplete one-time flow context.
            raise UnauthorizedError("OAuth flow security context is invalid")
        # Exchange the authorization code in a POST body with the exact callback and verifier.
        token_response = self._transport.post_form(GOOGLE_TOKEN_ENDPOINT, {"code": code, "client_id": self._client_id, "client_secret": self._client_secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code", "code_verifier": pkce_verifier})
        # Read the sensitive ID token only into request-local memory.
        id_token = token_response.get("id_token")
        # Parse signed bytes, header, claims, and signature under strict bounds.
        signed, header, claims, signature = _parse_jwt(id_token)
        # Fetch the current public JWK set through the injectable bounded transport.
        jwks = self._transport.get_json(GOOGLE_JWKS_ENDPOINT)
        # Verify the asymmetric signature before trusting any claim.
        _verify_google_signature(signed, signature, header, jwks)
        # Validate issuer, audience, expiry, chronology, nonce, and displayed-email verification.
        return _validate_google_claims(claims, self._client_id, expected_nonce, int(self._clock()))


# Validate Facebook's debug-token response and return its provider subject.
def _validated_facebook_subject(debug_response: Mapping[str, object], app_id: str, now: int) -> str:
    # Require the documented nested data object.
    data = debug_response.get("data")
    # Reject missing or malformed debug data.
    if not isinstance(data, Mapping):
        # Stop before profile retrieval or local identity lookup.
        raise UnauthorizedError("Facebook access token is invalid")
    # Require Facebook to mark the token valid for a user identity.
    if data.get("is_valid") is not True or data.get("type") not in {None, "USER"}:
        # Reject invalid or non-user token types.
        raise UnauthorizedError("Facebook access token is invalid")
    # Require the token to be issued to the configured Casino application.
    returned_app_id = data.get("app_id")
    # Reject absent or mismatched app binding with constant-time comparison.
    if not isinstance(returned_app_id, str) or not hmac.compare_digest(returned_app_id, app_id):
        # Prevent tokens from another Facebook application authenticating locally.
        raise UnauthorizedError("Facebook access token app binding is invalid")
    # Require a finite future token expiry for the selected user-token flow.
    expires_at = data.get("expires_at")
    # Reject booleans, absent expiry, and expired user tokens.
    if isinstance(expires_at, bool) or not isinstance(expires_at, int) or expires_at <= now - TOKEN_CLOCK_SKEW_SECONDS:
        # Prevent expired or non-expiring non-user tokens from entering the identity path.
        raise UnauthorizedError("Facebook access token is invalid")
    # Enforce data-access expiry when Facebook supplies it.
    data_access_expires_at = data.get("data_access_expires_at")
    # Reject expired data access without using provider profile data.
    if data_access_expires_at is not None and (isinstance(data_access_expires_at, bool) or not isinstance(data_access_expires_at, int) or data_access_expires_at <= now - TOKEN_CLOCK_SKEW_SECONDS):
        # Preserve one fixed Facebook token failure.
        raise UnauthorizedError("Facebook access token is invalid")
    # Require the minimum public-profile permission when a scope list is returned.
    scopes = data.get("scopes")
    # Reject malformed or missing scope evidence rather than assuming consent.
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes) or "public_profile" not in scopes:
        # Stop before requesting profile information.
        raise UnauthorizedError("Facebook access token scope is invalid")
    # Read the stable Facebook user subject after app and token validation.
    subject = data.get("user_id")
    # Require bounded printable text without exposing it.
    if not isinstance(subject, str) or not subject or len(subject) > 255 or any(not character.isprintable() for character in subject):
        # Reject unusable provider identity keys.
        raise UnauthorizedError("Facebook access token subject is invalid")
    # Return the validated provider-owned subject for exact profile binding.
    return subject


# Implement Facebook's server authorization-code flow with token/app verification.
class FacebookOAuthAdapter:
    # Expose static credential-free provider metadata through the shared port.
    spec = FACEBOOK_SPEC

    # Initialize one adapter with configured app credentials and injectable transport/time.
    def __init__(self, app_id: str, app_secret: str, transport: OAuthHttpTransport | None = None, clock=None):
        # Store the public app identifier for authorization and debug-token binding.
        self._app_id = app_id
        # Store the app secret only for server-side forms and HMAC proof.
        self._app_secret = app_secret
        # Use the production bounded transport only when tests did not inject a fake.
        self._transport = transport or UrlLibOAuthTransport()
        # Use Unix time through an injectable callable for deterministic expiry tests.
        self._clock = time.time if clock is None else clock

    # Build one Facebook authorization URL bound to state, callback, and PKCE.
    def authorization_url(self, *, redirect_uri: str, state: str, nonce: str, pkce_challenge: str | None) -> str:
        # Require a PKCE S256 challenge for this selected authorization-code integration.
        if not isinstance(pkce_challenge, str) or not pkce_challenge:
            # Reject a weakened start flow before provider navigation.
            raise ValidationError("OAuth PKCE challenge is required")
        # Encode only minimum permissions and server-owned anti-forgery values.
        parameters = {"client_id": self._app_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": ",".join(self.spec.scopes), "state": state, "code_challenge": pkce_challenge, "code_challenge_method": "S256"}
        # Return the provider endpoint plus request-local values without logging it.
        return FACEBOOK_AUTHORIZATION_ENDPOINT + "?" + urlencode(parameters)

    # Exchange one code and return a debugged, app-bound, allowlisted Facebook identity.
    def exchange_code(self, *, code: str, redirect_uri: str, expected_nonce: str | None, pkce_verifier: str | None) -> VerifiedIdentity:
        # Require the retained PKCE verifier before any provider request.
        if not isinstance(pkce_verifier, str) or not pkce_verifier:
            # Reject incomplete one-time flow context.
            raise UnauthorizedError("OAuth flow security context is invalid")
        # Exchange the code in a POST body so code and app secret never enter a URL.
        token_response = self._transport.post_form(FACEBOOK_TOKEN_ENDPOINT, {"client_id": self._app_id, "client_secret": self._app_secret, "redirect_uri": redirect_uri, "code": code, "code_verifier": pkce_verifier})
        # Read the short-lived access token only into request-local memory.
        access_token = token_response.get("access_token")
        # Require bounded printable token text before HMAC or provider verification.
        if not isinstance(access_token, str) or not access_token or len(access_token) > 8192 or any(not character.isprintable() for character in access_token):
            # Reject malformed exchange responses without reflecting them.
            raise UnauthorizedError("Facebook access token is invalid")
        # Construct the app access proof only in request-local memory for debug-token verification.
        app_access_token = f"{self._app_id}|{self._app_secret}"
        # Debug the user token through a POST form so neither token enters a request URL.
        debug_response = self._transport.post_form(FACEBOOK_DEBUG_ENDPOINT, {"input_token": access_token, "access_token": app_access_token})
        # Validate token status, app id, expiry, scope, and provider subject.
        subject = _validated_facebook_subject(debug_response, self._app_id, int(self._clock()))
        # Fetch only allowlisted display fields using the already debugged user token as a bearer credential.
        profile = self._transport.get_json(FACEBOOK_PROFILE_ENDPOINT, {"Authorization": f"Bearer {access_token}"})
        # Require the profile subject to match the independently debugged token subject.
        profile_subject = profile.get("id")
        # Reject profile/token confusion before normalization.
        if not isinstance(profile_subject, str) or not hmac.compare_digest(profile_subject, subject):
            # Prevent a profile response from selecting another provider identity.
            raise UnauthorizedError("Facebook profile binding is invalid")
        # Require explicit email permission whenever optional email metadata was returned.
        if profile.get("email") is not None and "email" not in debug_response["data"]["scopes"]:
            # Reject provider metadata that is not backed by the debugged permission grant.
            raise UnauthorizedError("Facebook email permission is invalid")
        # Normalize only subject and display metadata after all token/app checks succeed.
        return normalize_facebook_identity(profile)


# Build the correct adapter for one validated configured provider.
def build_provider_adapter(provider: str, client_id: str, client_secret: str, transport: OAuthHttpTransport | None = None, clock=None):
    # Construct Google only for the exact Google provider identifier.
    if provider == "google":
        # Return the fully validating Google adapter.
        return GoogleOAuthAdapter(client_id, client_secret, transport, clock)
    # Construct Facebook only for the exact Facebook provider identifier.
    if provider == "facebook":
        # Return the token-debugging Facebook adapter.
        return FacebookOAuthAdapter(client_id, client_secret, transport, clock)
    # Reject local or unknown providers before credentials can be used.
    raise ValidationError("External identity provider is invalid")
