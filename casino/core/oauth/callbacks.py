"""Exact callback URL, state, nonce, and query validation for issue #70.

Requirements: OAUTH-003. These helpers do not register public routes.
"""

# Import URL-safe encoding support for standards-compatible PKCE challenges.
import base64
# Import SHA-256 support for the PKCE S256 transformation.
import hashlib
# Import constant-time comparison support for state and nonce validation.
import hmac
# Import IP parsing so future public callbacks cannot use raw address literals.
import ipaddress
# Import regular expressions so provider error codes can be safely allowlisted.
import re
# Import cryptographic randomness for state and nonce generation.
import secrets
# Import dataclass helpers so sensitive callback fields stay out of representations.
from dataclasses import dataclass, field
# Import mapping types so raw query data can be validated before router flattening.
from typing import Mapping
# Import URL parsing so callback bases can be validated without network access.
from urllib.parse import urlsplit

# Import the provider registry so callback paths cannot accept unknown identifiers.
from casino.core.oauth.providers import get_provider_spec
# Import standard errors for future envelope-compatible route integration.
from casino.errors import UnauthorizedError, ValidationError

# Reserve the exact callback path shape documented by issue #75.
CALLBACK_PATH_TEMPLATE = "/api/v2/auth/oauth/{provider}/callback"
# Reserve the current local callback ports documented by issue #75.
RESERVED_LOCAL_PORTS = frozenset({8765, 8766, 8767})
# Retain only stable OAuth/OIDC error identifiers and collapse every provider-specific value.
PROVIDER_ERROR_CODES = frozenset({"account_selection_required", "access_denied", "consent_required", "interaction_required", "invalid_request", "invalid_request_object", "invalid_request_uri", "invalid_scope", "login_required", "request_not_supported", "request_uri_not_supported", "server_error", "temporarily_unavailable", "unauthorized_client", "unsupported_response_type"})
# Accept only RFC 7636 unreserved characters in PKCE verifier values.
PKCE_VERIFIER_RE = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
# Bound state and nonce values while allowing standard URL-safe random encodings.
MIN_PROOF_LENGTH = 32
# Bound state and nonce values well below general callback-value limits.
MAX_PROOF_LENGTH = 512
# Accept only the bounded URL-safe ASCII alphabet produced for server-owned state and nonce values.
OPAQUE_PROOF_RE = re.compile(rf"^[A-Za-z0-9_-]{{{MIN_PROOF_LENGTH},{MAX_PROOF_LENGTH}}}$")
# Accept conservative public DNS host labels without raw IP or path ambiguity.
PUBLIC_HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
# Reject dotted legacy numeric host forms that some URL clients interpret as IP addresses.
LEGACY_NUMERIC_HOST_RE = re.compile(r"^(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))+$", re.IGNORECASE)
# Bound opaque callback values so malformed requests cannot create unbounded memory or log data.
MAX_CALLBACK_VALUE_LENGTH = 4096


# Store one newly generated state and nonce while suppressing both from representations.
@dataclass(frozen=True)
class OAuthFlowSecrets:  # Group the two secret flow proofs without exposing either value.
    # Store the anti-forgery state without exposing it through repr output.
    state: str = field(repr=False)
    # Store the OpenID Connect replay nonce without exposing it through repr output.
    nonce: str = field(repr=False)
    # Store the PKCE verifier without exposing it through repr output.
    pkce_verifier: str = field(repr=False)


# Store one validated callback result while suppressing the authorization code from repr output.
@dataclass(frozen=True)
class CallbackParameters:  # Group one validated success or sanitized provider-error outcome.
    # Store the exact supported provider identifier.
    provider: str
    # Store the authorization code only for the future exchange call.
    code: str | None = field(default=None, repr=False)
    # Store a sanitized provider error code when authorization was denied or cancelled.
    error_code: str | None = None

    # Report whether this callback may proceed to a mocked or future code exchange.
    @property
    def succeeded(self) -> bool:  # Compute success without exposing the authorization code.
        # Return true only when a code exists and no provider error was reported.
        return bool(self.code) and self.error_code is None

    # Return only secret-safe callback facts for diagnostics or tests.
    def diagnostic(self) -> dict:
        # Publish booleans and a sanitized error identifier without code or state values.
        return {"provider": self.provider, "succeeded": self.succeeded, "authorization_code_present": bool(self.code), "error_code": self.error_code}


# Require an external provider before building an OAuth callback path.
def _require_external_provider(provider: str) -> str:
    # Resolve the exact provider identifier through the shared static registry.
    spec = get_provider_spec(provider)
    # Reject the unchanged local-password provider because it has no OAuth callback.
    if spec.flow == "password":
        # Raise a generic error without reflecting arbitrary input.
        raise ValidationError("Identity provider does not use OAuth callbacks")
    # Return the exact validated provider identifier.
    return spec.provider_id


# Return the exact callback path reserved for one external provider.
def canonical_callback_path(provider: str) -> str:
    # Validate the provider before interpolating it into a route-shaped string.
    provider_id = _require_external_provider(provider)
    # Return the canonical lower-case path with no trailing slash.
    return CALLBACK_PATH_TEMPLATE.format(provider=provider_id)


# Validate and canonicalize the configured callback base without contacting it.
def _canonical_public_base_url(public_base_url: str) -> str:
    # Reject non-text configuration instead of invoking arbitrary string conversion.
    if not isinstance(public_base_url, str):
        # Raise a value-free configuration diagnostic.
        raise ValidationError("OAuth public base URL is invalid")
    # Trim operator-supplied surrounding whitespace before structural validation.
    raw_base_url = public_base_url.strip()
    # Reject missing configuration without including any supplied value.
    if not raw_base_url:
        # Raise a value-free configuration diagnostic.
        raise ValidationError("OAuth public base URL is required")
    # Reject control characters before urlsplit can silently discard or normalize them.
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_base_url):
        # Raise a value-free configuration diagnostic.
        raise ValidationError("OAuth public base URL is invalid")
    # Start protected parsing so malformed brackets and ports become value-free diagnostics.
    try:
        # Parse the configured base locally without DNS, sockets, or provider traffic.
        parsed = urlsplit(raw_base_url)
        # Read parsed authority fields while the parser can still report malformed values.
        username = parsed.username
        # Read the optional password marker without retaining its value.
        password = parsed.password
        # Read and normalize the parsed hostname.
        hostname = (parsed.hostname or "").lower()
        # Ask the standard parser to validate numeric port range and syntax.
        port = parsed.port
    # Handle malformed authority syntax without reflecting any supplied value.
    except ValueError:
        # Raise a value-free diagnostic without retaining parser text in an exception cause.
        raise ValidationError("OAuth public base URL is invalid") from None
    # Reject credentials, query strings, fragments, and application subpaths.
    if username or password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        # Raise a value-free configuration diagnostic.
        raise ValidationError("OAuth public base URL must contain only scheme, host, and allowed port")
    # Reject missing hosts before scheme-specific checks.
    if not hostname:
        # Raise a value-free configuration diagnostic.
        raise ValidationError("OAuth public base URL host is required")
    # Permit HTTP only for the exact localhost callback matrix reserved by issue #75.
    if parsed.scheme == "http":
        # Reject IP aliases, unreserved ports, and absent explicit ports.
        if hostname != "localhost" or port not in RESERVED_LOCAL_PORTS:
            # Raise a value-free diagnostic so 127.0.0.1 is never silently substituted.
            raise ValidationError("HTTP OAuth callbacks require a reserved localhost port")
        # Return the exact local origin without a trailing slash.
        return f"http://localhost:{port}"
    # Require HTTPS for every non-local callback base.
    if parsed.scheme != "https":
        # Raise a value-free diagnostic for unsupported schemes.
        raise ValidationError("Public OAuth callbacks require HTTPS")
    # Reject explicit public ports because issue #75 reserves the default HTTPS origin shape.
    if port is not None:
        # Raise a value-free diagnostic so provider-console registration stays canonical.
        raise ValidationError("Public OAuth callback base must use the default HTTPS port")
    # Reject localhost and raw public IP literals for provider compatibility and safety.
    if hostname == "localhost":
        # Raise a value-free diagnostic for an invalid HTTPS local alias.
        raise ValidationError("HTTPS OAuth callbacks require an owned public hostname")
    # Reject legacy dotted numeric forms before they can masquerade as owned DNS names.
    if LEGACY_NUMERIC_HOST_RE.fullmatch(hostname):
        # Raise the same value-free diagnostic used for canonical IP literals.
        raise ValidationError("Public OAuth callbacks require an owned public hostname")
    # Start protected IP parsing so DNS hostnames continue to the hostname check.
    try:
        # Parse any address literal so it can be rejected explicitly.
        ipaddress.ip_address(hostname)
    # Treat normal DNS names as non-IP values.
    except ValueError:
        # Continue after confirming the host is not a raw address.
        pass
    # Reject raw IP literals that were parsed successfully.
    else:
        # Raise a value-free diagnostic for a provider-incompatible public base.
        raise ValidationError("Public OAuth callbacks require an owned public hostname")
    # Require a conservative fully qualified DNS hostname.
    if not PUBLIC_HOST_RE.fullmatch(hostname):
        # Raise a value-free diagnostic for malformed or single-label hosts.
        raise ValidationError("OAuth public hostname is invalid")
    # Return the canonical lower-case HTTPS origin without a trailing slash.
    return f"https://{hostname}"


# Build one exact provider callback URL from a validated configured base.
def build_callback_url(public_base_url: str, provider: str) -> str:
    # Canonicalize the origin before adding any reserved path.
    base_url = _canonical_public_base_url(public_base_url)
    # Append the exact issue-#75 callback path with no trailing slash.
    return base_url + canonical_callback_path(provider)


# Generate fresh state and nonce values without persisting or logging them.
def new_flow_secrets() -> OAuthFlowSecrets:
    # Generate independent URL-safe state, nonce, and PKCE verifier values.
    return OAuthFlowSecrets(state=secrets.token_urlsafe(32), nonce=secrets.token_urlsafe(32), pkce_verifier=secrets.token_urlsafe(64))


# Derive the standards-compatible S256 PKCE challenge for one verifier.
def pkce_s256_challenge(verifier: str) -> str:
    # Require exact text and RFC 7636 length and character bounds.
    if not isinstance(verifier, str) or not PKCE_VERIFIER_RE.fullmatch(verifier):
        # Raise a generic error without exposing the verifier.
        raise ValidationError("OAuth PKCE verifier is invalid")
    # Hash the verifier exactly as ASCII without trimming or normalization.
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    # Return unpadded URL-safe base64 as required by the S256 method.
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# Validate one expected and returned opaque proof value using constant-time comparison.
def _validate_proof(actual: str, expected: str, label: str) -> None:
    # Reject non-text proof values instead of stringifying or normalizing them.
    if not isinstance(actual, str) or not isinstance(expected, str):
        # Raise a generic authentication error without exposing either value.
        raise UnauthorizedError(f"OAuth {label} is invalid")
    # Preserve the returned proof exactly because OAuth values are opaque.
    actual_value = actual
    # Preserve the retained proof exactly for constant-time comparison.
    expected_value = expected
    # Reject absent, Unicode, whitespace-bearing, or otherwise non-generated proof values.
    if not OPAQUE_PROOF_RE.fullmatch(actual_value) or not OPAQUE_PROOF_RE.fullmatch(expected_value):
        # Raise a generic authentication error without exposing either value.
        raise UnauthorizedError(f"OAuth {label} is invalid")
    # Compare values without data-dependent early exit.
    if not hmac.compare_digest(actual_value, expected_value):
        # Raise a generic authentication error without exposing either value.
        raise UnauthorizedError(f"OAuth {label} is invalid")


# Validate an OpenID Connect nonce returned inside a future verified ID token.
def validate_nonce(actual_nonce: str, expected_nonce: str) -> None:
    # Reuse the constant-time bounded proof check for nonce replay protection.
    _validate_proof(actual_nonce, expected_nonce, "nonce")


# Read one callback parameter while rejecting duplicate or overlong values.
def _single_query_value(query: Mapping[str, object], name: str) -> str:
    # Read the raw value without serializing the query mapping.
    raw_value = query.get(name)
    # Treat list and tuple values as duplicate-aware query parser output.
    if isinstance(raw_value, (list, tuple)):
        # Reject duplicates or empty lists before selecting a value.
        if len(raw_value) != 1:
            # Raise a generic error that names only the expected parameter.
            raise ValidationError("OAuth callback parameters must occur once", {"parameter": name})
        # Select the only allowed value.
        raw_value = raw_value[0]
    # Treat an absent parameter as the empty value used by later required-field checks.
    if raw_value is None:
        # Return absence without stringifying arbitrary objects.
        return ""
    # Reject non-text query values instead of invoking arbitrary string conversion.
    if not isinstance(raw_value, str):
        # Raise a generic error that names only the expected parameter.
        raise ValidationError("OAuth callback parameter must be text", {"parameter": name})
    # Preserve the selected text exactly because OAuth query values are opaque.
    value = raw_value
    # Reject overlong values before any later exchange or diagnostic use.
    if len(value) > MAX_CALLBACK_VALUE_LENGTH:
        # Raise a generic error that names only the expected parameter.
        raise ValidationError("OAuth callback parameter is too long", {"parameter": name})
    # Return the normalized scalar, including an empty string for missing values.
    return value


# Read the callback state with duplicate rejection before a durable flow can be claimed.
def callback_state(query: Mapping[str, object]) -> str:
    # Reject non-mapping query data without serializing provider-controlled values.
    if not isinstance(query, Mapping):
        # Return the same bounded validation class as complete callback validation.
        raise ValidationError("OAuth callback query is invalid")
    # Reuse the single-value parser so duplicate state parameters can never select a flow.
    state = _single_query_value(query, "state")
    # Require the same generated opaque shape before persistence lookup.
    if not OPAQUE_PROOF_RE.fullmatch(state):
        # Reject absent or malformed state without revealing whether any flow exists.
        raise UnauthorizedError("OAuth state is invalid")
    # Return the exact opaque value only to the one-time flow repository.
    return state


# Validate one raw provider callback before any token exchange or session creation.
def validate_callback_query(provider: str, query: Mapping[str, object], expected_state: str) -> CallbackParameters:
    # Validate the external provider independently of callback parameter content.
    provider_id = _require_external_provider(provider)
    # Reject non-mapping query objects without serializing their contents.
    if not isinstance(query, Mapping):
        # Raise a generic request error suitable for a standard API envelope.
        raise ValidationError("OAuth callback query is invalid")
    # Reject duplicates for every returned parameter, including provider extension fields we do not consume.
    if any(isinstance(value, (list, tuple)) and len(value) != 1 for value in query.values()):
        # Prevent ambiguous parser normalization before any outcome field is selected.
        raise ValidationError("OAuth callback parameters must occur once")
    # Read state with duplicate detection before processing provider success or failure.
    returned_state = _single_query_value(query, "state")
    # Validate anti-forgery state using constant-time comparison.
    _validate_proof(returned_state, expected_state, "state")
    # Read success and error parameters independently so ambiguous callbacks fail closed.
    code = _single_query_value(query, "code")
    # Read only the provider error identifier and ignore error_description completely.
    provider_error = _single_query_value(query, "error")
    # Reject callbacks that contain both success and error outcomes.
    if code and provider_error:
        # Raise a generic error without exposing either provider value.
        raise ValidationError("OAuth callback outcome is ambiguous")
    # Return a secret-safe denied result when the provider supplied an error.
    if provider_error:
        # Replace provider-specific or secret-shaped error strings with one stable identifier.
        safe_error = provider_error if provider_error in PROVIDER_ERROR_CODES else "provider_error"
        # Return the sanitized denied result without error_description or state.
        return CallbackParameters(provider=provider_id, error_code=safe_error)
    # Require a success code when the provider did not report an error.
    if not code:
        # Raise a generic error without exposing the query mapping.
        raise ValidationError("OAuth callback authorization code is required")
    # Require printable ASCII VSCHAR while preserving significant leading or trailing spaces.
    if any(ord(character) < 32 or ord(character) > 126 for character in code):
        # Raise a generic error without reflecting the authorization code.
        raise ValidationError("OAuth callback authorization code is invalid")
    # Return the validated success result while keeping the code out of repr and diagnostics.
    return CallbackParameters(provider=provider_id, code=code)
