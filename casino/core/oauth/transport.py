"""Bounded injectable HTTPS JSON transport for OAuth provider adapters.

Requirements: OAUTH-005 and SEC-010. This module never logs URLs, forms, headers,
tokens, provider payloads, or exception text.
"""

# Import JSON decoding for bounded provider responses.
import json
# Import protocol types so unit tests can replace all provider network traffic.
from typing import Mapping, Protocol
# Import form encoding and standard HTTPS request primitives.
from urllib import error, parse, request

# Import the stable retryable provider failure envelope.
from casino.errors import ProviderUnavailableError

# Bound every provider response before JSON parsing or memory growth.
MAX_PROVIDER_RESPONSE_BYTES = 1_048_576
# Bound one provider call so worker threads cannot wait indefinitely.
PROVIDER_TIMEOUT_SECONDS = 10


# Define the only transport surface consumed by Google and Facebook adapters.
class OAuthHttpTransport(Protocol):
    # Fetch bounded JSON from one adapter-owned HTTPS endpoint.
    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> Mapping[str, object]:
        # Protocol methods remain implementation-free for deterministic tests.
        ...

    # Post a form to one adapter-owned HTTPS endpoint and decode bounded JSON.
    def post_form(self, url: str, form: Mapping[str, str], headers: Mapping[str, str] | None = None) -> Mapping[str, object]:
        # Protocol methods remain implementation-free for deterministic tests.
        ...


# Implement the production provider transport using only fixed adapter-owned URLs.
class UrlLibOAuthTransport:
    # Decode one HTTPS request without exposing response or exception values.
    @staticmethod
    def _read_json(provider_request: request.Request) -> Mapping[str, object]:
        # Require HTTPS before any DNS lookup or socket connection begins.
        if parse.urlsplit(provider_request.full_url).scheme != "https":
            # Fail through the fixed provider envelope rather than naming the URL.
            raise ProviderUnavailableError()
        # Start protected I/O so provider and network diagnostics remain private.
        try:
            # Open the bounded request with a fixed timeout and default certificate verification.
            with request.urlopen(provider_request, timeout=PROVIDER_TIMEOUT_SECONDS) as response:
                # Read one extra byte so oversized responses are rejected deterministically.
                raw = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
        # Collapse HTTP, TLS, DNS, timeout, and socket failures into one safe class.
        except (error.HTTPError, error.URLError, TimeoutError, OSError):
            # Suppress response bodies, URLs, headers, and exception text.
            raise ProviderUnavailableError() from None
        # Reject oversized provider bodies before decoding.
        if len(raw) > MAX_PROVIDER_RESPONSE_BYTES:
            # Return the same fixed retryable provider failure.
            raise ProviderUnavailableError()
        # Start protected UTF-8 and JSON decoding.
        try:
            # Decode only a top-level JSON object accepted by provider adapters.
            payload = json.loads(raw.decode("utf-8"))
        # Collapse malformed provider data without retaining raw bytes.
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Return a fixed provider failure without parser details.
            raise ProviderUnavailableError() from None
        # Require a mapping so adapters never interpret arrays or scalars as tokens.
        if not isinstance(payload, Mapping):
            # Reject unexpected response shapes through the fixed envelope.
            raise ProviderUnavailableError()
        # Return request-local decoded data to the validating provider adapter.
        return payload

    # Fetch one fixed public metadata endpoint as bounded JSON.
    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> Mapping[str, object]:
        # Build a GET request without logging its URL or headers.
        provider_request = request.Request(url, headers=dict(headers or {}), method="GET")
        # Decode the response through the common bounded policy.
        return self._read_json(provider_request)

    # Post one secret-bearing form without placing its values in a URL.
    def post_form(self, url: str, form: Mapping[str, str], headers: Mapping[str, str] | None = None) -> Mapping[str, object]:
        # Encode the form directly into the request body so query and access logs cannot receive it.
        encoded = parse.urlencode(dict(form)).encode("ascii")
        # Add the form content type without mutating caller headers.
        request_headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", **dict(headers or {})}
        # Build a POST request whose representation is never logged by this module.
        provider_request = request.Request(url, data=encoded, headers=request_headers, method="POST")
        # Decode the response through the common bounded policy.
        return self._read_json(provider_request)
