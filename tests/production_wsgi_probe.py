"""Listener-free TEST-046 probe for the production WSGI transport adapter."""

# Import in-memory streams for synthetic WSGI request bodies.
import io
# Import JSON support for standard envelope assertions.
import json
# Import portable paths for exact checkout module resolution.
from pathlib import Path
# Import interpreter path control for direct script execution.
import sys

# Resolve the repository root independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Prepend the exact checkout so the probe never imports an unrelated installed package.
sys.path.insert(0, str(ROOT))

# Import the already environment-validated production application under test.
from casino.wsgi import application


# Call the WSGI adapter directly without creating any network listener.
def request(method: str, path: str, body=None, headers=None, content_length=None):
    # Encode a supplied JSON body exactly once for the WSGI input stream.
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    # Split the application path from its optional query string.
    path_info, _, query_string = path.partition("?")
    # Build the minimum standards-compliant WSGI environment for one direct request.
    environ = {
        # Select the request method consumed by application routing.
        "REQUEST_METHOD": method,
        # Supply the decoded application path.
        "PATH_INFO": path_info,
        # Supply the undecoded query component separately.
        "QUERY_STRING": query_string,
        # Identify only the direct synthetic loopback peer.
        "REMOTE_ADDR": "127.0.0.1",
        # Supply a valid WSGI byte stream for body parsing.
        "wsgi.input": io.BytesIO(payload),
        # Declare the standard WSGI protocol version.
        "wsgi.version": (1, 0),
        # Mark the listener-free test as a single process.
        "wsgi.multiprocess": False,
        # Permit the same threaded behavior expected from the production server.
        "wsgi.multithread": True,
        # Mark the synthetic call as non-reentrant.
        "wsgi.run_once": False,
        # Provide standard error without capturing or printing secrets.
        "wsgi.errors": io.StringIO(),
        # Keep the direct request on cleartext loopback because TLS belongs to the edge gate.
        "wsgi.url_scheme": "http",
    }
    # Add a content type only when the request carries a JSON body.
    if body is not None:
        # Match the API's declared JSON request media type.
        environ["CONTENT_TYPE"] = "application/json"
    # Use an explicit test value when malformed length behavior is under test.
    environ["CONTENT_LENGTH"] = str(len(payload)) if content_length is None else content_length
    # Translate caller-provided HTTP headers into WSGI server variables.
    for name, value in (headers or {}).items():
        # Preserve only synthetic test values in the direct environment.
        environ["HTTP_" + name.upper().replace("-", "_")] = value
    # Capture the status and headers supplied through start_response.
    response = {}

    # Record one WSGI response without creating a server object.
    def start_response(status, response_headers):
        # Retain the public status line for exact assertions.
        response["status"] = status
        # Normalize response headers into a direct assertion mapping.
        response["headers"] = dict(response_headers)

    # Join the bounded response iterable into its complete payload.
    response["body"] = b"".join(application(environ, start_response))
    # Return the direct response record to the probe sequence.
    return response


# Exercise sanitized anonymous liveness and exact response headers.
health = request("GET", "/healthz")
# Require a successful HTTP status line.
assert health["status"] == "200 OK"
# Require the standard JSON response media type.
assert health["headers"]["Content-Type"] == "application/json; charset=utf-8"
# Require no-store semantics for liveness and every other API response.
assert health["headers"]["Cache-Control"] == "no-store"
# Require the declared length to match the exact returned bytes.
assert int(health["headers"]["Content-Length"]) == len(health["body"])
# Parse the liveness envelope after transport assertions pass.
health_payload = json.loads(health["body"].decode("utf-8"))
# Require only the accepted sanitized live status inside the success envelope.
assert health_payload == {"ok": True, "data": {"status": "live"}}

# Authenticate with the synthetic test-only Admin supplied through the child environment.
login = request("POST", "/api/v2/auth/login", {"email": "service-probe@example.invalid", "password": "synthetic-service-probe-password"})
# Require the canonical successful login status.
assert login["status"] == "200 OK"
# Extract the synthetic session token only inside this disposable child process.
token = json.loads(login["body"].decode("utf-8"))["data"]["session"]["token"]
# Propagate the token through a direct WSGI Authorization header.
current_user = request("GET", "/api/v2/me", headers={"Authorization": f"Bearer {token}"})
# Require authenticated context propagation through the adapter.
assert current_user["status"] == "200 OK"
# Parse the authenticated response after status validation.
current_payload = json.loads(current_user["body"].decode("utf-8"))
# Require the current-user route to return the synthetic Admin identity.
assert current_payload["data"]["user"]["email"] == "service-probe@example.invalid"

# Send a non-numeric content length through the direct adapter boundary.
malformed = request("POST", "/api/v2/auth/login", body={}, content_length="not-a-number")
# Require a bounded client error instead of a generic server exception.
assert malformed["status"] == "400 Bad Request"
# Parse the malformed-input error envelope.
malformed_payload = json.loads(malformed["body"].decode("utf-8"))
# Require the standard validation code without reflecting the hostile length value.
assert malformed_payload["error"]["code"] == "VALIDATION_ERROR"
# Ensure the malformed value never appears in the response body.
assert b"not-a-number" not in malformed["body"]

# Serve the packaged frontend through the same direct adapter without a listener.
frontend = request("GET", "/")
# Require a successful static response.
assert frontend["status"] == "200 OK"
# Require non-empty packaged frontend bytes.
assert frontend["body"]
# Require the declared static length to match returned bytes.
assert int(frontend["headers"]["Content-Length"]) == len(frontend["body"])
