# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free Big Six production static-asset cache probe for issue #223."""

# Import in-memory streams for one standards-compliant WSGI request.
import io
# Import JSON serialization for the bounded parent-process result.
import json
# Import repository-root path resolution for direct script execution.
from pathlib import Path
# Import module path control so the exact checkout owns every imported package.
import sys

# Resolve the repository root from this tests/browser probe file.
ROOT = Path(__file__).resolve().parents[2]
# Put the exact checkout first without reading any installed Casino package.
sys.path.insert(0, str(ROOT))

# Import the production adapter only after the parent configures isolated production variables.
from casino.wsgi import application  # noqa: E402

# Retain one response status, header map, and bounded asset body.
response = {}


# Capture the WSGI status and headers without opening a network listener.
def start_response(status, response_headers):
    # Preserve the public status line for exact success validation.
    response["status"] = status
    # Normalize the public response headers into a direct lookup mapping.
    response["headers"] = dict(response_headers)


# Build the minimum server-authored environment for one static JavaScript request.
environ = {
    # Select the read-only static request method.
    "REQUEST_METHOD": "GET",
    # Request the exact lazy game module used by the browser route.
    "PATH_INFO": "/games/big_six_wheel.js",
    # Supply no query component for the canonical module path.
    "QUERY_STRING": "",
    # Identify only a direct synthetic loopback peer.
    "REMOTE_ADDR": "127.0.0.1",
    # Use the reserved synthetic authority configured by the parent process.
    "HTTP_HOST": "casino.example.invalid",
    # Supply an empty standards-compliant request stream.
    "wsgi.input": io.BytesIO(b""),
    # Declare no request body bytes.
    "CONTENT_LENGTH": "0",
    # Declare the standard WSGI protocol version.
    "wsgi.version": (1, 0),
    # Match the production adapter's multiprocess-capable execution contract.
    "wsgi.multiprocess": False,
    # Permit the same threaded behavior expected under the service runner.
    "wsgi.multithread": True,
    # Mark the direct probe as a one-shot non-reentrant request.
    "wsgi.run_once": False,
    # Provide an isolated standard-error sink without serializing private state.
    "wsgi.errors": io.StringIO(),
    # Keep the direct request on cleartext loopback because TLS belongs to the edge.
    "wsgi.url_scheme": "http",
}

# Join the bounded static response iterable into its complete asset bytes.
response["body"] = b"".join(application(environ, start_response))
# Require the production adapter to serve the exact module successfully.
if response.get("status") != "200 OK":
    raise AssertionError("production WSGI did not serve the Big Six module")
# Require old browser assets to be discarded by the deployed adapter policy.
if response["headers"].get("Cache-Control") != "no-store":
    raise AssertionError("production WSGI Big Six asset did not enforce no-store")
# Require the served bytes to include the current cumulative-motion implementation marker.
if b"MIN_SPIN_REVOLUTIONS" not in response["body"]:
    raise AssertionError("production WSGI served Big Six source without the motion marker")
# Emit only sanitized policy evidence for the parent qualification summary.
print(json.dumps({"status": "pass", "cache_control": "no-store", "current_source_marker": True}))
