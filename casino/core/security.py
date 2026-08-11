# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Restricted-preview request security policy for SEC-010 and AUTH-007."""

# Import constant-time comparison for origin and CSRF values.
import hmac
# Import IP parsing so proxy trust is based on exact addresses rather than header presence.
import ipaddress
# Import process configuration without retaining any secret values in diagnostics.
import os
# Import bounded CSRF entropy from the operating system.
import secrets
# Import a process-local lock for the approved threaded Gunicorn worker.
import threading
# Import monotonic time for in-memory fixed-window request limiting.
import time
# Import ordered mappings so rate-limit capacity remains deterministic.
from collections import OrderedDict, deque
# Import immutable records for validated configuration and request identity.
from dataclasses import dataclass
# Import strict cookie parsing for the double-submit bootstrap token.
from http.cookies import CookieError, SimpleCookie
# Import URL parsing for the exact configured HTTPS origin.
from urllib.parse import urlsplit

# Import the standard application error envelope types.
from casino.errors import ForbiddenError, RateLimitError, ValidationError

# Name the explicit canonical-origin configuration used by production request validation.
CANONICAL_ORIGIN_ENV = "CASINO_CANONICAL_ORIGIN"
# Name the exact direct loopback proxy address trusted to supply forwarding metadata.
TRUSTED_PROXY_ENV = "CASINO_TRUSTED_PROXY"
# Name the fail-closed restricted-preview mode switch.
RESTRICTED_PREVIEW_ENV = "CASINO_RESTRICTED_PREVIEW"
# Name the governed SameSite setting for session and CSRF cookies.
SESSION_SAMESITE_ENV = "CASINO_SESSION_SAMESITE"
# Name the maximum accepted JSON request body setting.
MAX_BODY_BYTES_ENV = "CASINO_MAX_BODY_BYTES"
# Name the per-client fixed-window request count setting.
RATE_REQUESTS_ENV = "CASINO_RATE_LIMIT_REQUESTS"
# Name the fixed-window duration setting.
RATE_WINDOW_ENV = "CASINO_RATE_LIMIT_WINDOW_SECONDS"
# Name the host-only browser-readable double-submit cookie.
CSRF_COOKIE = "casino_csrf"
# Name the exact request header that carries the double-submit or session CSRF value.
CSRF_HEADER = "X-Csrf-Token"
# Enumerate methods that can change application or authentication state.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Allow only SameSite modes compatible with the owned same-origin preview.
ALLOWED_SAMESITE = frozenset({"Strict", "Lax"})
# Reject request bodies larger than one mebibyte even when an operator supplies a larger value.
ABSOLUTE_MAX_BODY_BYTES = 1_048_576
# Bound the number of distinct effective clients retained by the single production worker.
MAX_RATE_KEYS = 2_048
# Define the reviewed Content Security Policy for packaged same-origin browser assets.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        # Default every omitted resource class to the owned origin.
        "default-src 'self'",
        # Prevent injected markup from changing the document base.
        "base-uri 'none'",
        # Disable plugin content entirely.
        "object-src 'none'",
        # Deny every framing ancestor even when a legacy browser ignores X-Frame-Options.
        "frame-ancestors 'none'",
        # Permit form submission only back to the exact same origin.
        "form-action 'self'",
        # Load executable code only from packaged same-origin files.
        "script-src 'self'",
        # Retain existing reviewed inline style attributes while blocking remote styles.
        "style-src 'self' 'unsafe-inline'",
        # Permit packaged images plus existing data-URL interface artwork.
        "img-src 'self' data:",
        # Keep font loading on the owned origin.
        "font-src 'self'",
        # Keep API, event, and future socket connections on the owned origin.
        "connect-src 'self'",
        # Keep sound assets on the owned origin.
        "media-src 'self'",
        # Keep an optional application manifest on the owned origin.
        "manifest-src 'self'",
    )
)


# Store one completely validated restricted-preview configuration.
@dataclass(frozen=True)
class SecurityPolicy:
    # Preserve the exact normalized HTTPS origin used for request comparison.
    canonical_origin: str
    # Preserve the canonical host and optional port for documentation and tests.
    canonical_authority: str
    # Preserve the exact loopback address allowed to author forwarding metadata.
    trusted_proxy: str
    # Preserve the reviewed SameSite cookie mode.
    same_site: str
    # Preserve the maximum number of request bytes read from a WSGI stream.
    max_body_bytes: int
    # Preserve the allowed number of requests in one fixed window.
    rate_requests: int
    # Preserve the fixed-window duration in seconds.
    rate_window_seconds: int

    # Load and validate the complete production policy without exposing supplied values.
    @classmethod
    def from_environment(cls, environment=None):
        # Use the live process environment unless a value-only test mapping is supplied.
        current = os.environ if environment is None else environment
        # Require the deployment to declare that this is the restricted-preview stage.
        if str(current.get(RESTRICTED_PREVIEW_ENV, "")).strip().lower() not in {"1", "true"}:
            # Name only the missing policy switch in the fail-closed diagnostic.
            raise RuntimeError(f"{RESTRICTED_PREVIEW_ENV} must enable restricted preview")
        # Parse one exact absolute HTTPS origin from explicit external configuration.
        origin, authority = _parse_canonical_origin(str(current.get(CANONICAL_ORIGIN_ENV, "")).strip())
        # Parse one exact loopback address rather than trusting all local-looking headers.
        proxy = _parse_trusted_proxy(str(current.get(TRUSTED_PROXY_ENV, "")).strip())
        # Normalize the operator-selected SameSite value while retaining a reviewed default.
        same_site = str(current.get(SESSION_SAMESITE_ENV, "Strict")).strip().capitalize()
        # Reject None and ungoverned modes that would weaken same-origin cookie behavior.
        if same_site not in ALLOWED_SAMESITE:
            # Report only the public setting name, never the supplied value.
            raise RuntimeError(f"{SESSION_SAMESITE_ENV} must select Strict or Lax")
        # Parse the request body limit within reviewed lower and upper bounds.
        max_body_bytes = _bounded_integer(current, MAX_BODY_BYTES_ENV, 131_072, 1_024, ABSOLUTE_MAX_BODY_BYTES)
        # Parse the per-client request count within a useful but bounded range.
        rate_requests = _bounded_integer(current, RATE_REQUESTS_ENV, 1_200, 1, 10_000)
        # Parse the fixed-window duration within one second and one hour.
        rate_window_seconds = _bounded_integer(current, RATE_WINDOW_ENV, 60, 1, 3_600)
        # Return an immutable policy that request handling can safely share across threads.
        return cls(origin, authority, proxy, same_site, max_body_bytes, rate_requests, rate_window_seconds)


# Store the trusted effective transport identity for one request.
@dataclass(frozen=True)
class EffectiveRequest:
    # Preserve the effective scheme after exact direct-proxy validation.
    scheme: str
    # Preserve the effective client address used only for request bounds.
    client: str
    # Record whether the configured proxy supplied the effective values.
    proxied: bool


# Parse one bounded integer setting without reflecting its supplied value.
def _bounded_integer(environment, key: str, default: int, minimum: int, maximum: int) -> int:
    # Read the public setting or its reviewed default as text.
    raw = str(environment.get(key, default)).strip()
    # Start protected conversion so malformed configuration fails before service readiness.
    try:
        # Convert decimal text to its integer policy value.
        value = int(raw)
    # Replace conversion details with a value-free configuration diagnostic.
    except (TypeError, ValueError) as exc:
        # Raise an error that names only the public configuration key.
        raise RuntimeError(f"{key} must be a bounded integer") from exc
    # Reject values outside the reviewed interval.
    if value < minimum or value > maximum:
        # Keep the diagnostic stable and free of the supplied value.
        raise RuntimeError(f"{key} is outside the supported range")
    # Return the validated integer.
    return value


# Parse and normalize one configured absolute HTTPS origin.
def _parse_canonical_origin(value: str) -> tuple[str, str]:
    # Reject absence before URL parsing can produce ambiguous empty components.
    if not value:
        # Name only the required external configuration key.
        raise RuntimeError(f"{CANONICAL_ORIGIN_ENV} must define one absolute HTTPS origin")
    # Parse the candidate with standard origin component semantics.
    parsed = urlsplit(value)
    # Require HTTPS, an authority, no user information, no query or fragment, and at most root path.
    invalid = parsed.scheme != "https" or not parsed.netloc or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment or parsed.path not in {"", "/"}
    # Reject malformed or expanded URL forms before normalizing the trailing slash.
    if invalid:
        # Keep the configuration value out of logs and exception text.
        raise RuntimeError(f"{CANONICAL_ORIGIN_ENV} must define one absolute HTTPS origin")
    # Require a valid hostname and port while suppressing parser value details.
    try:
        # Read the normalized hostname so invalid bracket or port syntax is evaluated.
        hostname = parsed.hostname
        # Read the optional port to trigger standard range validation.
        port = parsed.port
    # Replace malformed authority diagnostics with the public setting name.
    except ValueError as exc:
        # Fail closed without echoing the authority.
        raise RuntimeError(f"{CANONICAL_ORIGIN_ENV} must define one absolute HTTPS origin") from exc
    # Restrict deployment hostnames to lower-case ASCII DNS syntax for exact comparison.
    if not hostname or hostname != hostname.lower() or hostname.endswith(".") or any(ord(character) > 127 for character in hostname):
        # Reject ambiguous Unicode or case variants before request handling.
        raise RuntimeError(f"{CANONICAL_ORIGIN_ENV} must use a lower-case ASCII host")
    # Reconstruct the exact canonical authority with an optional validated port.
    authority = hostname if port is None else f"{hostname}:{port}"
    # Require the supplied authority to match the normalized value exactly.
    if parsed.netloc != authority:
        # Reject aliases, trailing dots, or alternate textual forms.
        raise RuntimeError(f"{CANONICAL_ORIGIN_ENV} must use one canonical authority")
    # Return the exact origin without a trailing root slash.
    return f"https://{authority}", authority


# Parse the one direct proxy address trusted to author effective request metadata.
def _parse_trusted_proxy(value: str) -> str:
    # Reject an absent proxy identity before forwarding headers can be considered.
    if not value:
        # Name only the required external setting.
        raise RuntimeError(f"{TRUSTED_PROXY_ENV} must define one loopback address")
    # Start protected address parsing so hostnames and address lists fail closed.
    try:
        # Parse an exact IPv4 or IPv6 literal.
        address = ipaddress.ip_address(value)
    # Replace the supplied value with a stable configuration diagnostic.
    except ValueError as exc:
        # Raise without echoing private network configuration.
        raise RuntimeError(f"{TRUSTED_PROXY_ENV} must define one loopback address") from exc
    # Require the direct proxy to be local to the application host.
    if not address.is_loopback:
        # Reject private, public, wildcard, and unspecified addresses equally.
        raise RuntimeError(f"{TRUSTED_PROXY_ENV} must define one loopback address")
    # Return the canonical textual address used for exact peer comparison.
    return str(address)


# Resolve scheme and client identity without trusting hostile forwarding headers.
def effective_request(environ: dict, policy: SecurityPolicy) -> EffectiveRequest:
    # Read the server-normalized HTTP authority used for host-only cookie scope.
    authority = str(environ.get("HTTP_HOST") or "").strip()
    # Require one exact configured authority with no list, user information, or alternate port.
    if not authority or "," in authority or "@" in authority or not hmac.compare_digest(authority, policy.canonical_authority):
        # Reject missing, malformed, and foreign Host values identically.
        raise ForbiddenError("Request authority is not allowed")
    # Read the server-authored direct peer address.
    direct_raw = str(environ.get("REMOTE_ADDR") or "").strip()
    # Start protected direct-peer parsing because rate keys must never consume arbitrary headers.
    try:
        # Normalize the direct peer as an exact IP literal.
        direct = str(ipaddress.ip_address(direct_raw))
    # Reject malformed server metadata before request dispatch.
    except ValueError as exc:
        # Return a fixed diagnostic that does not echo server or client data.
        raise ForbiddenError("Direct client metadata is invalid") from exc
    # Reject standardized or host/port forwarding metadata because this adapter does not consume it.
    if any(environ.get(key) for key in ("HTTP_FORWARDED", "HTTP_X_FORWARDED_HOST", "HTTP_X_FORWARDED_PORT")):
        # Prevent alternate forwarding grammars from bypassing exact policy.
        raise ForbiddenError("Unsupported forwarding metadata")
    # Read the only two proxy-authored values accepted by the policy.
    forwarded_for = str(environ.get("HTTP_X_FORWARDED_FOR") or "").strip()
    # Read the forwarded scheme independently so partial header sets can be rejected.
    forwarded_proto = str(environ.get("HTTP_X_FORWARDED_PROTO") or "").strip()
    # Branch when either forwarding header is present.
    if forwarded_for or forwarded_proto:
        # Require both values together and require the exact configured direct proxy peer.
        if not forwarded_for or not forwarded_proto or direct != policy.trusted_proxy:
            # Reject rather than ignore hostile or incomplete forwarding metadata.
            raise ForbiddenError("Forwarding metadata is not trusted")
        # Reject lists and alternate protocol tokens before parsing the effective client.
        if "," in forwarded_for or "," in forwarded_proto or forwarded_proto.lower() != "https":
            # Keep the fixed failure free of supplied addresses and schemes.
            raise ForbiddenError("Forwarding metadata is invalid")
        # Start protected effective-client parsing.
        try:
            # Canonicalize the sole edge-observed client address.
            client = str(ipaddress.ip_address(forwarded_for))
        # Reject hostnames, obfuscated lists, and malformed address text.
        except ValueError as exc:
            # Preserve the same fixed public failure class.
            raise ForbiddenError("Forwarding metadata is invalid") from exc
        # Return the trusted HTTPS edge identity for HSTS and rate limiting.
        return EffectiveRequest("https", client, True)
    # Normalize only the WSGI server-authored direct scheme when no forwarding metadata exists.
    scheme = str(environ.get("wsgi.url_scheme") or "http").strip().lower()
    # Restrict direct requests to standard cleartext or TLS scheme metadata.
    if scheme not in {"http", "https"}:
        # Reject malformed server metadata without echoing it.
        raise ForbiddenError("Direct request scheme is invalid")
    # Return the direct peer so caller headers never influence the rate-limit key.
    return EffectiveRequest(scheme, direct, False)


# Return a new bounded double-submit token.
def new_csrf_token() -> str:
    # Use 256 bits of entropy encoded without cookie separators.
    return secrets.token_urlsafe(32)


# Extract the named cookie without exposing the complete Cookie header.
def cookie_value(headers: dict, name: str) -> str:
    # Read the request cookie string only into request-local memory.
    raw = str(headers.get("Cookie", ""))
    # Return absence without creating a parser object.
    if not raw:
        # Preserve a simple empty sentinel for constant-time validation callers.
        return ""
    # Start protected cookie parsing because malformed hostile syntax must fail closed.
    try:
        # Parse cookie pairs with the standard library's strict morsel handling.
        parsed = SimpleCookie(raw)
    # Convert parser details into a fixed request error.
    except CookieError as exc:
        # Avoid reflecting any cookie bytes in the public response.
        raise ForbiddenError("Request cookie is invalid") from exc
    # Read only the requested cookie morsel.
    morsel = parsed.get(name)
    # Return its scalar value or the absence sentinel.
    return morsel.value if morsel else ""


# Validate exact Origin and CSRF proof for every state-changing request.
def validate_request_integrity(method: str, headers: dict, policy: SecurityPolicy, expected_csrf: str | None = None) -> None:
    # Leave read-only methods unchanged.
    if method.upper() not in UNSAFE_METHODS:
        # Return before consulting browser-authored integrity headers.
        return
    # Read the one browser or non-browser Origin value.
    origin = str(headers.get("Origin", ""))
    # Require exact byte-for-byte origin equality, including scheme and optional port.
    if not origin or not hmac.compare_digest(origin, policy.canonical_origin):
        # Reject missing, null, malformed, and foreign origins with the same diagnostic.
        raise ForbiddenError("Request origin is not allowed")
    # Read the explicit CSRF proof header without logging or normalizing it.
    supplied = str(headers.get(CSRF_HEADER, ""))
    # Use the authenticated session token when available, otherwise the bootstrap double-submit cookie.
    expected = expected_csrf if expected_csrf is not None else cookie_value(headers, CSRF_COOKIE)
    # Require non-empty bounded values before constant-time comparison.
    if not supplied or not expected or len(supplied) > 128 or len(expected) > 128 or not hmac.compare_digest(supplied, expected):
        # Use one fixed failure for absent, malformed, and mismatched values.
        raise ForbiddenError("CSRF validation failed")


# Build the host-only browser-readable CSRF cookie for bootstrap or session rotation.
def csrf_cookie_header(token: str, same_site: str, secure: bool = True) -> tuple[str, str]:
    # Add Secure in production while keeping the helper explicit for isolated local tests.
    secure_attribute = "; Secure" if secure else ""
    # Omit Domain so the cookie remains host-only and scope it to the application root.
    return ("Set-Cookie", f"{CSRF_COOKIE}={token}; Path=/{secure_attribute}; SameSite={same_site}")


# Return the fixed browser and transport headers required on every production response.
def response_security_headers(effective_scheme: str) -> list[tuple[str, str]]:
    # Start with policy headers that apply over direct loopback and HTTPS edge requests.
    headers = [
        # Apply the reviewed same-origin content loading policy.
        ("Content-Security-Policy", CONTENT_SECURITY_POLICY),
        # Prevent MIME sniffing from converting immutable assets into executable content.
        ("X-Content-Type-Options", "nosniff"),
        # Avoid sending preview routes to external referrers.
        ("Referrer-Policy", "no-referrer"),
        # Disable browser capabilities that the simulator does not use.
        ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()"),
        # Preserve legacy clickjacking protection alongside CSP frame ancestors.
        ("X-Frame-Options", "DENY"),
        # Isolate the top-level window from cross-origin opener relationships.
        ("Cross-Origin-Opener-Policy", "same-origin"),
        # Prevent other origins from embedding packaged application resources.
        ("Cross-Origin-Resource-Policy", "same-origin"),
    ]
    # Emit HSTS only when trusted server or proxy metadata proves the effective request used HTTPS.
    if effective_scheme == "https":
        # Use a one-year host-only policy without affecting sibling subdomains.
        headers.append(("Strict-Transport-Security", "max-age=31536000"))
    # Return a fresh list so response code may append cookie headers safely.
    return headers


# Enforce one fixed-window request bound keyed only by trusted effective client identity.
class RateLimiter:
    # Initialize an empty bounded client registry and injectable monotonic clock.
    def __init__(self, policy: SecurityPolicy, clock=None):
        # Retain the immutable request-count policy.
        self.policy = policy
        # Use monotonic process time unless a deterministic test clock is supplied.
        self.clock = time.monotonic if clock is None else clock
        # Preserve insertion order for deterministic capacity handling.
        self.clients = OrderedDict()
        # Serialize pruning and consumption across the approved gthread worker threads.
        self.lock = threading.Lock()

    # Remove expired timestamps and empty client keys across the entire bounded registry.
    def _prune(self, cutoff: float) -> None:
        # Inspect a stable key snapshot because empty entries are removed in place.
        for client in list(self.clients):
            # Read the timestamp deque owned by this trusted effective client.
            entries = self.clients[client]
            # Drop every timestamp that is no longer inside the current window.
            while entries and entries[0] <= cutoff:
                # Release one expired allowance record.
                entries.popleft()
            # Remove an empty client so one-shot address churn cannot exhaust capacity forever.
            if not entries:
                # Release the bounded registry slot after its window expires.
                del self.clients[client]

    # Consume one request allowance or raise the standard 429 error.
    def check(self, client: str, rotate_capacity: bool = False, requests_per_window: int | None = None, window_seconds: int | None = None) -> None:
        # Read the monotonic timestamp once for this decision.
        now = float(self.clock())
        # Resolve the live owner-authored allowance or retain the immutable deployment fallback.
        allowed_requests = self.policy.rate_requests if requests_per_window is None else max(1, min(10_000, int(requests_per_window)))
        # Resolve the live owner-authored window or retain the immutable deployment fallback.
        active_window_seconds = self.policy.rate_window_seconds if window_seconds is None else max(1, min(3_600, int(window_seconds)))
        # Calculate the oldest timestamp still inside the fixed window.
        cutoff = now - active_window_seconds
        # Serialize the complete read-prune-check-append sequence across worker threads.
        with self.lock:
            # Reclaim expired capacity globally before considering a new effective client.
            self._prune(cutoff)
            # Reject a new effective client when the bounded registry is still full.
            if client not in self.clients and len(self.clients) >= MAX_RATE_KEYS:
                # Rotate the oldest probe-only client so unrelated traffic cannot starve monitoring.
                if rotate_capacity:
                    # Remove exactly one oldest bounded key before admitting the new probe client.
                    self.clients.popitem(last=False)
                # Preserve strict capacity failure for application traffic.
                else:
                    # Avoid evicting active application protection under a client-address flood.
                    raise RateLimitError()
            # Allocate a bounded timestamp deque for the trusted key.
            entries = self.clients.setdefault(client, deque())
            # Reject when the current window already contains the allowed count.
            if len(entries) >= allowed_requests:
                # Return a fixed diagnostic without exposing client or timing data.
                raise RateLimitError()
            # Record the accepted request after every validation branch passes.
            entries.append(now)
            # Refresh insertion order so active clients remain grouped deterministically.
            self.clients.move_to_end(client)
