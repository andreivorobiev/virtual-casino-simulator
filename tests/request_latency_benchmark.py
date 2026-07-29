"""Listener-free request-latency baseline for TEST-148.

The module intentionally imports no Casino runtime package at module load.  An
explicit provider runner prepares isolated external state first and imports the
production WSGI adapter only after that boundary is complete.
"""

# Import command-line parsing for the explicit benchmark-only selector.
import argparse
# Import bounded thread-pool primitives for rolling request concurrency.
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
# Import in-memory byte streams for direct WSGI request bodies.
import io
# Import JSON encoding for requests and sanitized aggregate evidence.
import json
# Import finite-number checks for the evidence allowlist.
import math
# Import atomic filesystem replacement and test-only environment configuration.
import os
# Import portable paths for checkout containment and caller-owned output checks.
from pathlib import Path
# Import a strict source-commit pattern without accepting arbitrary provenance.
import re
# Import the active interpreter path for isolated provider child execution.
import subprocess
# Import standard error output for one fixed child failure message.
import sys
# Import caller-external temporary directories and atomic temporary files.
import tempfile
# Import monotonic high-resolution timing without emitting timestamps.
import time

# Resolve the exact checkout independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Identify the sanitized evidence schema.
EVIDENCE_SCHEMA = "request-latency-baseline/v1"
# Pin the four required concurrency levels.
CONCURRENCY_LEVELS = (1, 2, 4, 8)
# Warm every route row with a fixed number of untimed requests.
WARMUP_OPERATIONS = 8
# Measure exactly sixty-four operations in every route/concurrency row.
MEASURED_OPERATIONS = 64
# Raise only the test process allowance needed by this fixed benchmark.
TEST_RATE_ALLOWANCE = 10_000
# Validate exact Git source provenance before any benchmark work.
SOURCE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
# Name the three MySQL pool overrides that this baseline must leave unset.
MYSQL_POOL_OVERRIDE_KEYS = (
    "CASINO_MYSQL_POOL_SIZE",  # Preserve the default capacity.
    "CASINO_MYSQL_POOL_WAIT_MS",  # Preserve the default checkout wait.
    "CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS",  # Preserve the default connector deadline.
)
# Name every administrator or migrator capability forbidden in the benchmark child.
MYSQL_CHILD_CAPABILITY_KEYS = (
    "CASINO_MYSQL_TEST_ADMIN_USER",  # Withhold the disposable administrator identity.
    "CASINO_MYSQL_TEST_ADMIN_PASSWORD",  # Withhold the disposable administrator secret.
    "CASINO_MYSQL_MIGRATION_USER",  # Withhold the schema migrator identity.
    "CASINO_MYSQL_MIGRATION_PASSWORD",  # Withhold the schema migrator secret.
    "CASINO_MYSQL_MIGRATION_DATABASE",  # Withhold the migrator-owned target selector.
    "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY",  # Withhold private target-binding material.
)
# Enumerate the only low-cardinality route-family labels allowed in evidence.
ROUTE_FAMILIES = (
    "current_user",  # Measure the authenticated v2 current-user projection.
    "slots_state",  # Measure one game-owned state read.
    "roulette_state",  # Measure the second game-owned state read.
    "casino_state",  # Measure the aggregate authenticated state.
    "boule_spin",  # Measure one idempotency-capable mutation.
)
# Keep the four read families ahead of every mutation control and timed mutation.
READ_ROUTE_FAMILIES = ROUTE_FAMILIES[:-1]
# Pin the complete top-level evidence allowlist.
EVIDENCE_KEYS = frozenset({"schema", "source_commit", "provider", "rows"})
# Pin the complete per-row evidence allowlist.
ROW_KEYS = frozenset(
    {
        "route_family",  # Identify only one fixed low-cardinality family.
        "concurrency",  # Retain the fixed worker count.
        "p50_ms",  # Retain the aggregate nearest-rank median.
        "p95_ms",  # Retain the aggregate nearest-rank tail.
        "throughput_rps",  # Retain aggregate completed operations per second.
        "errors",  # Retain only the zero accepted-error count.
        "response_bytes",  # Retain only the total returned bytes.
    }
)
# Keep the synthetic restricted-preview origin outside real DNS.
SYNTHETIC_ORIGIN = "https://latency-benchmark.example.invalid"
# Keep the synthetic bootstrap identity inside the child process only.
SYNTHETIC_EMAIL = "request-latency@example.invalid"
# Keep the synthetic bootstrap credential inside the child process only.
SYNTHETIC_PASSWORD = "synthetic-request-latency-password-2026"


# Report one fixed benchmark failure without reflecting request or environment data.
class RequestLatencyBenchmarkError(RuntimeError):
    """Stable failure raised by the listener-free benchmark."""


# Retain one direct WSGI response without exposing request inputs in diagnostics.
class DirectResponse:
    # Store only the public status, response headers, and returned bytes.
    def __init__(self, status: str, headers: list[tuple[str, str]], body: bytes) -> None:
        # Preserve the public HTTP status line.
        self.status = status
        # Preserve application-authored headers for login cookie extraction.
        self.headers = list(headers)
        # Preserve the exact response bytes for size aggregation.
        self.body = body

    # Decode the standard JSON envelope after status validation.
    def payload(self) -> dict:
        # Start protected parsing so response bytes never enter diagnostics.
        try:
            # Parse only the bounded application response.
            value = json.loads(self.body.decode("utf-8"))
        # Convert malformed encoding or JSON into one value-free failure.
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Raise one fixed diagnostic without body content.
            raise RequestLatencyBenchmarkError("request returned an invalid envelope") from None
        # Reject any non-object response before route-specific checks.
        if not isinstance(value, dict):
            # Raise one fixed diagnostic without body content.
            raise RequestLatencyBenchmarkError("request returned an invalid envelope")
        # Return the parsed standard envelope.
        return value


# Issue direct calls against the WSGI callable without creating a listener.
class DirectWSGIClient:
    # Bind the imported application only after provider setup is complete.
    def __init__(self, application) -> None:
        # Retain the application callable without importing a server package.
        self.application = application
        # Hold the child-only bearer after untimed authentication.
        self.token = ""
        # Hold the child-only session CSRF proof after untimed authentication.
        self.csrf_token = ""

    # Execute one WSGI request through a fresh standards-compliant environment.
    def request(self, method: str, path: str, body=None, authenticated: bool = True) -> DirectResponse:
        # Encode a request body only when the route needs one.
        raw_body = b"" if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        # Split the application path from its optional query string.
        path_info, _, query_string = path.partition("?")
        # Build the complete listener-free request environment.
        environ = {
            # Supply the normalized request method.
            "REQUEST_METHOD": method,
            # Supply the decoded application path.
            "PATH_INFO": path_info,
            # Supply the query separately under the WSGI contract.
            "QUERY_STRING": query_string,
            # Identify only the synthetic direct loopback peer.
            "REMOTE_ADDR": "127.0.0.1",
            # Use the exact configured reserved-domain authority.
            "HTTP_HOST": "latency-benchmark.example.invalid",
            # Provide a fresh request-owned byte stream.
            "wsgi.input": io.BytesIO(raw_body),
            # Declare the standard WSGI protocol version.
            "wsgi.version": (1, 0),
            # Mark the test as one process with concurrent threads.
            "wsgi.multiprocess": False,
            # Permit the same threaded behavior exercised by the benchmark.
            "wsgi.multithread": True,
            # Mark every direct request as non-reentrant.
            "wsgi.run_once": False,
            # Keep WSGI diagnostics in memory and outside evidence.
            "wsgi.errors": io.StringIO(),
            # Keep the listener-free call on direct loopback cleartext.
            "wsgi.url_scheme": "http",
            # Declare the exact bounded request length.
            "CONTENT_LENGTH": str(len(raw_body)),
        }
        # Declare JSON only for requests that carry a body.
        if body is not None:
            # Match the API's standard JSON request media type.
            environ["CONTENT_TYPE"] = "application/json"
        # Attach session authentication only after untimed setup completed.
        if authenticated:
            # Refuse an authenticated call before setup rather than timing a login failure.
            if not self.token:
                # Raise one fixed setup diagnostic.
                raise RequestLatencyBenchmarkError("authenticated setup is incomplete")
            # Carry the child-only bearer to the application.
            environ["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        # Attach origin and session CSRF proof to every authenticated mutation.
        if authenticated and method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Carry the exact configured synthetic origin.
            environ["HTTP_ORIGIN"] = SYNTHETIC_ORIGIN
            # Carry the session-owned CSRF proof.
            environ["HTTP_X_CSRF_TOKEN"] = self.csrf_token
        # Capture the status and ordered response headers.
        captured: dict = {}

        # Retain the WSGI response metadata for this request.
        def start_response(status, headers) -> None:
            # Store the public status line.
            captured["status"] = str(status)
            # Store the ordered response headers without logging them.
            captured["headers"] = list(headers)

        # Join the bounded application iterable into its complete response body.
        response_body = b"".join(self.application(environ, start_response))
        # Require the callable to invoke start_response.
        if "status" not in captured:
            # Fail with one fixed adapter diagnostic.
            raise RequestLatencyBenchmarkError("WSGI response metadata is missing")
        # Return the complete direct response.
        return DirectResponse(captured["status"], captured["headers"], response_body)

    # Authenticate once outside every warm-up and timed row.
    def authenticate(self) -> None:
        # Bootstrap one anonymous double-submit cookie through the packaged shell.
        bootstrap = self.request("GET", "/", authenticated=False)
        # Require the public shell before parsing its cookie.
        if bootstrap.status != "200 OK":
            # Fail without exposing the response.
            raise RequestLatencyBenchmarkError("authentication bootstrap failed")
        # Select the single CSRF cookie value from application-owned headers.
        cookie_header = next(
            (  # Search the ordered response header collection.
                value  # Return only the matching cookie header value.
                for name, value in bootstrap.headers  # Inspect application-owned response headers.
                if name.lower() == "set-cookie" and value.startswith("casino_csrf=")  # Select the bootstrap proof.
            ),
            "",  # Fall back to the absence sentinel.
        )
        # Reject a missing bootstrap cookie before login.
        if not cookie_header:
            # Raise one fixed cookie diagnostic.
            raise RequestLatencyBenchmarkError("authentication bootstrap proof is missing")
        # Extract only the generated cookie scalar.
        bootstrap_csrf = cookie_header.split(";", 1)[0].split("=", 1)[1]
        # Build the anonymous login request directly so it carries double-submit proof.
        raw_body = json.dumps(
            {"email": SYNTHETIC_EMAIL, "password": SYNTHETIC_PASSWORD},  # Keep credentials child-local.
            separators=(",", ":"),  # Use a deterministic compact request body.
        ).encode("utf-8")  # Encode exact WSGI request bytes.
        # Build the same direct WSGI environment used by ordinary calls.
        environ = {
            # Select the login mutation.
            "REQUEST_METHOD": "POST",
            # Target the frozen authentication route.
            "PATH_INFO": "/api/v2/auth/login",
            # Supply no query component.
            "QUERY_STRING": "",
            # Identify only direct loopback.
            "REMOTE_ADDR": "127.0.0.1",
            # Match the configured reserved-domain authority.
            "HTTP_HOST": "latency-benchmark.example.invalid",
            # Supply the encoded credential body in memory only.
            "wsgi.input": io.BytesIO(raw_body),
            # Declare the WSGI protocol version.
            "wsgi.version": (1, 0),
            # Keep the adapter inside one process.
            "wsgi.multiprocess": False,
            # Permit normal threaded application behavior.
            "wsgi.multithread": True,
            # Mark the call as non-reentrant.
            "wsgi.run_once": False,
            # Keep WSGI diagnostics in memory.
            "wsgi.errors": io.StringIO(),
            # Keep TLS outside this listener-free application baseline.
            "wsgi.url_scheme": "http",
            # Declare exact JSON request metadata.
            "CONTENT_TYPE": "application/json",
            # Declare the exact bounded body length.
            "CONTENT_LENGTH": str(len(raw_body)),
            # Match the production origin gate.
            "HTTP_ORIGIN": SYNTHETIC_ORIGIN,
            # Supply the anonymous double-submit cookie.
            "HTTP_COOKIE": f"casino_csrf={bootstrap_csrf}",
            # Supply the matching anonymous header proof.
            "HTTP_X_CSRF_TOKEN": bootstrap_csrf,
        }
        # Capture the login response without exposing credentials.
        captured: dict = {}

        # Retain the login status and headers.
        def start_response(status, headers) -> None:
            # Store the public status line.
            captured["status"] = str(status)
            # Store headers only until authentication completes.
            captured["headers"] = list(headers)

        # Invoke the direct WSGI adapter without a listener.
        login_body = b"".join(self.application(environ, start_response))
        # Require exact successful authentication.
        if captured.get("status") != "200 OK":
            # Raise one fixed authentication failure.
            raise RequestLatencyBenchmarkError("authentication setup failed")
        # Parse the standard success envelope.
        login_payload = json.loads(login_body.decode("utf-8"))
        # Read the session record only inside this child process.
        session = login_payload.get("data", {}).get("session", {})
        # Capture the bearer and CSRF values for later direct requests.
        self.token = str(session.get("token") or "")
        # Capture the separate session-owned CSRF proof.
        self.csrf_token = str(session.get("csrf_token") or "")
        # Require both secrets to exist before any benchmark row.
        if not self.token or not self.csrf_token:
            # Fail without including either value.
            raise RequestLatencyBenchmarkError("authenticated session proof is incomplete")


# Compute one nearest-rank percentile from non-empty nanosecond samples.
def _percentile_ms(samples_ns: list[int], percentile: float) -> float:
    # Reject missing measurements rather than emitting a fabricated zero.
    if not samples_ns:
        # Raise one fixed aggregation failure.
        raise RequestLatencyBenchmarkError("latency samples are missing")
    # Sort a private copy for deterministic nearest-rank selection.
    ordered = sorted(samples_ns)
    # Resolve the one-based nearest rank and convert it to a bounded index.
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    # Convert nanoseconds to milliseconds only for aggregate evidence.
    return round(ordered[index] / 1_000_000.0, 3)


# Execute a fixed operation count while keeping no more than concurrency futures pending.
def rolling_bounded_map(
    operation,  # Accept the index-addressed row operation.
    operation_count: int,  # Accept the fixed row operation count.
    concurrency: int,  # Accept one governed concurrency.
    *,  # Keep test seams keyword-only.
    executor_factory=ThreadPoolExecutor,  # Use real threads unless a unit injects accounting.
    wait_function=wait,  # Use FIRST_COMPLETED unless a unit injects deterministic progress.
) -> tuple[list, int]:  # Return completed results plus the pending high-water mark.
    # Reject invalid bounds before constructing worker threads.
    if operation_count < 1 or concurrency not in CONCURRENCY_LEVELS:
        # Raise one fixed scheduler diagnostic.
        raise RequestLatencyBenchmarkError("scheduler bounds are invalid")
    # Allocate the exact fixed-size worker pool for this row.
    executor = executor_factory(max_workers=concurrency)
    # Track only futures currently submitted and not yet collected.
    pending: set = set()
    # Retain completed results in completion order.
    results: list = []
    # Track the highest pending count for unit proof, never evidence output.
    maximum_pending = 0
    # Track the next operation index not yet submitted.
    next_index = 0
    # Protect shutdown even when an operation fails.
    try:
        # Prime at most N operations rather than pre-submitting the complete row.
        while next_index < min(operation_count, concurrency):
            # Submit one bounded operation.
            pending.add(executor.submit(operation, next_index))
            # Advance the unique operation index.
            next_index += 1
        # Record the initial bounded pending count.
        maximum_pending = max(maximum_pending, len(pending))
        # Continue until every submitted operation is collected.
        while pending:
            # Wait only until at least one operation completes.
            completed, _ = wait_function(pending, return_when=FIRST_COMPLETED)
            # Refuse a waiter that reports no progress.
            if not completed:
                # Raise one fixed scheduler failure.
                raise RequestLatencyBenchmarkError("scheduler made no progress")
            # Remove completed futures before replenishing the rolling window.
            pending.difference_update(completed)
            # Collect each completed result and surface operation failure.
            for future in completed:
                # Append the operation result without serializing diagnostics.
                results.append(future.result())
            # Refill at most the number of released slots.
            while next_index < operation_count and len(pending) < concurrency:
                # Submit exactly one next operation.
                pending.add(executor.submit(operation, next_index))
                # Advance the unique operation index.
                next_index += 1
            # Record the bounded pending high-water mark.
            maximum_pending = max(maximum_pending, len(pending))
    # Always join every worker before returning or propagating failure.
    finally:
        # Cancel only work that could not start after a failure and join active work.
        executor.shutdown(wait=True, cancel_futures=True)
    # Require exact result accounting.
    if len(results) != operation_count:
        # Reject incomplete scheduler output.
        raise RequestLatencyBenchmarkError("scheduler result count is incomplete")
    # Return results plus the internal high-water proof.
    return results, maximum_pending


# Require one successful standard API response and return its byte count.
def _successful_response_bytes(response: DirectResponse) -> int:
    # Require exact HTTP success.
    if response.status != "200 OK":
        # Raise one fixed route failure.
        raise RequestLatencyBenchmarkError("request row failed")
    # Collect the case-insensitive response length header.
    content_lengths = [str(value).strip() for name, value in response.headers if str(name).lower() == "content-length"]
    # Require exactly one unsigned decimal framing value.
    if len(content_lengths) != 1 or not re.fullmatch(r"[0-9]+", content_lengths[0]):
        # Raise one fixed framing failure without the header value.
        raise RequestLatencyBenchmarkError("request row failed")
    # Require framing to match the fully consumed response bytes.
    if int(content_lengths[0]) != len(response.body):
        # Raise one fixed framing failure without either size.
        raise RequestLatencyBenchmarkError("request row failed")
    # Start protected parsing so every timed failure uses one fixed diagnostic.
    try:
        # Parse the standard envelope.
        payload = response.payload()
    # Normalize malformed JSON, encoding, or non-object envelopes.
    except RequestLatencyBenchmarkError:
        # Raise the fixed row failure without chaining parser details.
        raise RequestLatencyBenchmarkError("request row failed") from None
    # Require a successful standard response with an object data payload.
    if payload.get("ok") is not True or not isinstance(payload.get("data"), dict):
        # Raise one fixed envelope failure.
        raise RequestLatencyBenchmarkError("request row failed")
    # Return only the aggregate-safe byte count.
    return len(response.body)


# Read one authoritative internal-only player balance from a standard response.
def _response_player_balance(payload: dict) -> float:
    # Read the public player projection without retaining any identity.
    player = payload.get("data", {}).get("player", {})
    # Prefer the explicit current-user token field and fall back to game response balance.
    balance = player.get("token_balance", player.get("balance"))
    # Reject booleans, missing values, and non-finite wallet state.
    if isinstance(balance, bool) or not isinstance(balance, (int, float)) or not math.isfinite(float(balance)):
        # Raise one fixed diagnostic that never includes the wallet value.
        raise RequestLatencyBenchmarkError("Boule wallet control failed")
    # Normalize only to the application's public hundredth-token boundary.
    return round(float(balance), 2)


# Read the authenticated wallet outside every timed row.
def _current_player_balance(client: DirectWSGIClient) -> float:
    # Request the authoritative current-user projection without timing it.
    response = client.request("GET", "/api/v2/me")
    # Require exact success before inspecting the internal-only player projection.
    if response.status != "200 OK":
        # Raise one fixed diagnostic without response or wallet content.
        raise RequestLatencyBenchmarkError("Boule wallet control failed")
    # Parse and normalize the internal-only current balance.
    return _response_player_balance(response.payload())


# Execute the fixed untimed Boule first/replay/conflict controls.
def _boule_controls(client: DirectWSGIClient) -> tuple[object, float]:
    # Use one stable control identity that never enters a timed row.
    payload = {"request_id": "latency-boule-control", "bet": "even", "stake": 1}
    # Execute the first control action outside timed work.
    first = client.request("POST", "/api/v1/games/boule/spins", payload)
    # Require exact first-action success.
    first_payload = first.payload()
    # Reject a failed or pre-replayed first control.
    if first.status != "200 OK" or first_payload.get("ok") is not True or first_payload["data"].get("replayed") is not False:
        # Raise one fixed control diagnostic.
        raise RequestLatencyBenchmarkError("Boule first-action control failed")
    # Capture the authoritative post-settlement wallet only for internal invariants.
    settled_balance = _response_player_balance(first_payload)
    # Replay the identical action outside timed work.
    replay = client.request("POST", "/api/v1/games/boule/spins", payload)
    # Parse the replay response.
    replay_payload = replay.payload()
    # Require explicit replay with the identical public round.
    if replay.status != "200 OK" or replay_payload.get("ok") is not True or replay_payload["data"].get("replayed") is not True or replay_payload["data"].get("round") != first_payload["data"].get("round") or _response_player_balance(replay_payload) != settled_balance:
        # Raise one fixed replay-control diagnostic.
        raise RequestLatencyBenchmarkError("Boule replay control failed")
    # Reuse the same key with changed content to prove conflict outside timed work.
    conflict = client.request(
        "POST",  # Reuse the mutation method.
        "/api/v1/games/boule/spins",  # Reuse the public Boule action.
        {"request_id": "latency-boule-control", "bet": "odd", "stake": 1},  # Change only semantic content.
    )
    # Parse the standard conflict envelope.
    conflict_payload = conflict.payload()
    # Require the stable conflict status and code.
    if conflict.status != "409 Conflict" or conflict_payload.get("error", {}).get("code") != "CONFLICT":
        # Raise one fixed conflict-control diagnostic.
        raise RequestLatencyBenchmarkError("Boule conflict control failed")
    # Require the changed-body conflict to leave the authoritative wallet unchanged.
    if _current_player_balance(client) != settled_balance:
        # Raise one fixed wallet diagnostic without emitting the balance.
        raise RequestLatencyBenchmarkError("Boule conflict wallet control failed")
    # Return only internal control state needed for the post-cap proof.
    return first_payload["data"].get("round"), settled_balance


# Re-prove the control receipt after timed keys exceed the compact state cache.
def _boule_receipt_cap_control(client: DirectWSGIClient, original_round) -> None:
    # Capture the authoritative wallet after timed actions and before receipt replay.
    current_balance = _current_player_balance(client)
    # Reuse the exact original control body only after all timed rows complete.
    replay = client.request(
        "POST",  # Reuse the public mutation method.
        "/api/v1/games/boule/spins",  # Reuse the public Boule action.
        {"request_id": "latency-boule-control", "bet": "even", "stake": 1},  # Recover the original control.
    )
    # Parse only the standard success envelope.
    payload = replay.payload()
    # Require durable round replay plus the route's current authoritative player projection.
    if replay.status != "200 OK" or payload.get("ok") is not True or payload["data"].get("replayed") is not True or payload["data"].get("round") != original_round or _response_player_balance(payload) != current_balance:
        # Raise one fixed receipt-cap failure.
        raise RequestLatencyBenchmarkError("Boule receipt-cap control failed")
    # Reuse the evicted control key with different content after the durable replay.
    conflict = client.request(
        "POST",  # Reuse the public mutation method.
        "/api/v1/games/boule/spins",  # Reuse the public Boule action.
        {"request_id": "latency-boule-control", "bet": "odd", "stake": 1},  # Change only semantic content.
    )
    # Parse only the standard conflict envelope.
    conflict_payload = conflict.payload()
    # Require the durable action fingerprint to remain conflict-safe after eviction.
    if conflict.status != "409 Conflict" or conflict_payload.get("error", {}).get("code") != "CONFLICT":
        # Raise one fixed receipt-cap conflict diagnostic.
        raise RequestLatencyBenchmarkError("Boule receipt-cap conflict control failed")
    # Require both receipt-cap replay and conflict to leave the wallet unchanged.
    if _current_player_balance(client) != current_balance:
        # Raise one fixed wallet diagnostic without emitting the balance.
        raise RequestLatencyBenchmarkError("Boule receipt-cap wallet control failed")


# Build one route operation using only fixed application paths.
def _route_operation(client: DirectWSGIClient, route_family: str, concurrency: int, phase: str):
    # Return the authenticated current-user read.
    if route_family == "current_user":
        # Ignore the unique index because this route is read-only.
        return lambda _index: client.request("GET", "/api/v2/me")
    # Return the authenticated Slots state read.
    if route_family == "slots_state":
        # Ignore the unique index because this route is read-only.
        return lambda _index: client.request("GET", "/api/v1/games/slots/state")
    # Return the authenticated Roulette state read.
    if route_family == "roulette_state":
        # Ignore the unique index because this route is read-only.
        return lambda _index: client.request("GET", "/api/v1/games/roulette/state")
    # Return the authenticated aggregate Casino state read.
    if route_family == "casino_state":
        # Ignore the unique index because this route is read-only.
        return lambda _index: client.request("GET", "/api/v1/casino/state")
    # Build a unique idempotency key for every timed or warm-up Boule operation.
    if route_family == "boule_spin":
        # Return one mutation callable whose key is unique across phase, concurrency, and index.
        return lambda index: client.request(
            "POST",  # Execute the public mutation.
            "/api/v1/games/boule/spins",  # Target the fixed Boule route.
            {
                "request_id": f"latency-boule-{phase}-{concurrency}-{index}",  # Give each operation a unique key.
                "bet": "even",  # Use one stable low-cost wager.
                "stake": 1,  # Keep every mutation inside the synthetic wallet.
            },
        )
    # Reject an unregistered family before any call.
    raise RequestLatencyBenchmarkError("route family is invalid")


# Warm and measure one route/concurrency row.
def _measure_row(client: DirectWSGIClient, route_family: str, concurrency: int) -> dict:
    # Resolve one warm-up operation with phase-unique Boule identities.
    warm_operation = _route_operation(client, route_family, concurrency, "warmup")

    # Execute one warm-up request and retain only validation.
    def warm(index: int) -> int:
        # Require success without timing or retaining payload content.
        return _successful_response_bytes(warm_operation(index))

    # Run the fixed warm-up through the same bounded scheduler.
    _, warm_pending = rolling_bounded_map(warm, WARMUP_OPERATIONS, concurrency)
    # Require the scheduler never to exceed the selected concurrency.
    if warm_pending > concurrency:
        # Raise one fixed bounded-submission failure.
        raise RequestLatencyBenchmarkError("warm-up scheduler exceeded concurrency")
    # Resolve one measured operation with a distinct key namespace.
    measured_operation = _route_operation(client, route_family, concurrency, "measured")

    # Time one request locally and retain only duration plus byte count.
    def measured(index: int) -> tuple[int, int]:
        # Capture the monotonic start immediately before direct WSGI dispatch.
        started = time.perf_counter_ns()
        # Execute one fixed route operation.
        response = measured_operation(index)
        # Capture completion immediately after the application returns.
        finished = time.perf_counter_ns()
        # Validate success and return only aggregate inputs.
        return finished - started, _successful_response_bytes(response)

    # Capture row wall time around only the fixed measured operations.
    row_started = time.perf_counter_ns()
    # Execute exactly sixty-four operations with a rolling bounded window.
    results, maximum_pending = rolling_bounded_map(measured, MEASURED_OPERATIONS, concurrency)
    # Capture row completion after every future is joined.
    row_elapsed_ns = time.perf_counter_ns() - row_started
    # Reject a nonpositive wall interval before throughput division.
    if row_elapsed_ns <= 0:
        # Raise one fixed clock/accounting failure.
        raise RequestLatencyBenchmarkError("measured row wall time is invalid")
    # Require the production scheduler never to pre-submit beyond N.
    if maximum_pending > concurrency:
        # Raise one fixed bounded-submission failure.
        raise RequestLatencyBenchmarkError("measured scheduler exceeded concurrency")
    # Extract only the duration samples for percentile aggregation.
    durations = [duration for duration, _ in results]
    # Sum response bytes without retaining any response content.
    response_bytes = sum(size for _, size in results)
    # Calculate aggregate throughput from fixed operation count and wall duration.
    throughput = MEASURED_OPERATIONS / (row_elapsed_ns / 1_000_000_000.0)
    # Return only the approved row fields.
    return {
        "route_family": route_family,  # Emit only the fixed family label.
        "concurrency": concurrency,  # Emit the governed worker count.
        "p50_ms": _percentile_ms(durations, 0.50),  # Emit the aggregate median.
        "p95_ms": _percentile_ms(durations, 0.95),  # Emit the aggregate tail.
        "throughput_rps": round(throughput, 3),  # Emit bounded aggregate throughput.
        "errors": 0,  # Accept evidence only after every operation succeeds.
        "response_bytes": response_bytes,  # Emit only the response-byte total.
    }


# Validate that evidence contains exactly the public aggregate schema.
def validate_evidence(evidence: dict) -> None:
    # Require the complete top-level allowlist without additions.
    if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_KEYS:
        # Fail closed on missing or private top-level fields.
        raise RequestLatencyBenchmarkError("evidence fields are invalid")
    # Require the exact schema identity.
    if evidence.get("schema") != EVIDENCE_SCHEMA:
        # Reject unknown evidence versions.
        raise RequestLatencyBenchmarkError("evidence schema is invalid")
    # Require exact hexadecimal source provenance.
    if not SOURCE_COMMIT_PATTERN.fullmatch(str(evidence.get("source_commit") or "")):
        # Reject a branch name or other dynamic identifier.
        raise RequestLatencyBenchmarkError("evidence source commit is invalid")
    # Restrict provider identity to the two approved low-cardinality values.
    if evidence.get("provider") not in {"json", "mysql"}:
        # Reject host or database-derived provider text.
        raise RequestLatencyBenchmarkError("evidence provider is invalid")
    # Require exactly five route families by four concurrency rows.
    rows = evidence.get("rows")
    # Reject non-list or wrong-cardinality row collections.
    if not isinstance(rows, list) or len(rows) != len(ROUTE_FAMILIES) * len(CONCURRENCY_LEVELS):
        # Fail closed on incomplete measurements.
        raise RequestLatencyBenchmarkError("evidence row count is invalid")
    # Track the complete expected route/concurrency grid.
    seen: set[tuple[str, int]] = set()
    # Validate every row independently.
    for row in rows:
        # Require the exact row allowlist.
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            # Reject extra identifiers, paths, samples, or diagnostics.
            raise RequestLatencyBenchmarkError("evidence row fields are invalid")
        # Normalize the fixed route/concurrency identity.
        identity = (row.get("route_family"), row.get("concurrency"))
        # Reject unknown or duplicate grid entries.
        if identity[0] not in ROUTE_FAMILIES or identity[1] not in CONCURRENCY_LEVELS or identity in seen:
            # Fail closed on ambiguous aggregate identity.
            raise RequestLatencyBenchmarkError("evidence row identity is invalid")
        # Record this unique grid entry.
        seen.add(identity)
        # Require finite positive aggregate timing values.
        for key in ("p50_ms", "p95_ms", "throughput_rps"):
            # Read the numeric aggregate without coercing strings.
            value = row.get(key)
            # Reject booleans, non-numbers, infinities, zero, negatives, and NaN.
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0:
                # Raise one fixed aggregate diagnostic.
                raise RequestLatencyBenchmarkError("evidence aggregate is invalid")
        # Require the tail percentile to be no lower than the median.
        if float(row["p95_ms"]) < float(row["p50_ms"]):
            # Reject impossible percentile ordering.
            raise RequestLatencyBenchmarkError("evidence percentile order is invalid")
        # Require zero integer errors in accepted baseline evidence.
        if row.get("errors") != 0 or isinstance(row.get("errors"), bool):
            # Refuse successful evidence with hidden failures.
            raise RequestLatencyBenchmarkError("evidence errors are nonzero")
        # Require a positive integer byte total.
        if not isinstance(row.get("response_bytes"), int) or isinstance(row.get("response_bytes"), bool) or row["response_bytes"] <= 0:
            # Reject floating or malformed size aggregates.
            raise RequestLatencyBenchmarkError("evidence response bytes are invalid")
    # Require the complete grid after duplicate checks.
    expected = {(route, concurrency) for route in ROUTE_FAMILIES for concurrency in CONCURRENCY_LEVELS}
    # Reject any missing route/concurrency pair.
    if seen != expected:
        # Fail closed on incomplete evidence.
        raise RequestLatencyBenchmarkError("evidence grid is incomplete")


# Resolve and validate one caller-owned output path outside the checkout.
def resolve_output_path(output_path: str | Path) -> Path:
    # Resolve harmless aliases without requiring the destination to exist.
    output = Path(output_path).expanduser().resolve()
    # Reject the checkout itself or any path beneath it.
    if output == ROOT.resolve() or ROOT.resolve() in output.parents:
        # Refuse benchmark evidence inside source control.
        raise RequestLatencyBenchmarkError("evidence output must be outside the checkout")
    # Require the caller to create and own the output directory.
    if not output.parent.is_dir():
        # Avoid creating an unrequested filesystem hierarchy.
        raise RequestLatencyBenchmarkError("evidence output directory is missing")
    # Reject a destination symlink so replacement cannot escape after validation.
    if output.exists() and output.is_symlink():
        # Fail closed on mutable output indirection.
        raise RequestLatencyBenchmarkError("evidence output must not be a symlink")
    # Return the validated absolute output.
    return output


# Atomically write validated evidence to the caller-owned external destination.
def write_evidence_atomic(output_path: str | Path, evidence: dict) -> Path:
    # Validate the exact allowlist before touching the destination.
    validate_evidence(evidence)
    # Resolve the caller-owned external output path.
    output = resolve_output_path(output_path)
    # Track the temporary path for fail-safe cleanup.
    temporary_path: Path | None = None
    # Protect atomic write and cleanup.
    try:
        # Allocate the temporary file beside the destination for same-filesystem replacement.
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".request-latency-",  # Identify only benchmark-owned temporary files.
            suffix=".tmp",  # Keep temporary identity distinct from JSON output.
            dir=str(output.parent),  # Keep replacement on the caller's filesystem.
        )
        # Retain the exact temporary path for cleanup.
        temporary_path = Path(temporary_name)
        # Open the owned descriptor without following another path lookup.
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            # Serialize only the validated aggregate evidence.
            json.dump(evidence, handle, indent=2, sort_keys=True)
            # Terminate the JSON document predictably.
            handle.write("\n")
            # Flush Python buffers before the durability boundary.
            handle.flush()
            # Flush the file descriptor before atomic replacement.
            os.fsync(handle.fileno())
        # Replace the caller-selected output atomically.
        os.replace(temporary_path, output)
        # Mark the temporary path consumed by replacement.
        temporary_path = None
    # Remove only the benchmark-owned temporary file after failure.
    finally:
        # Unlink a leftover temporary file without touching the destination.
        if temporary_path is not None and temporary_path.exists():
            # Remove only the exact file allocated above.
            temporary_path.unlink()
    # Return the written destination for caller-side digesting.
    return output


# Prepare one isolated child runtime before importing the Casino WSGI adapter.
def _configure_child_environment(provider: str, runtime_root: Path) -> None:
    # Require the caller-selected provider before environment mutation.
    if provider not in {"json", "mysql"}:
        # Reject an unknown provider with one fixed diagnostic.
        raise RequestLatencyBenchmarkError("benchmark provider is invalid")
    # Require the child runtime root to remain outside the checkout.
    if runtime_root.resolve() == ROOT.resolve() or ROOT.resolve() in runtime_root.resolve().parents:
        # Reject source-owned mutable state.
        raise RequestLatencyBenchmarkError("benchmark runtime must be outside the checkout")
    # Require the disposable marker and loopback tuple before using MySQL.
    if provider == "mysql":
        # Require explicit disposable authorization inherited from the migration harness.
        if str(os.environ.get("CASINO_MYSQL_DISPOSABLE_TEST", "")).strip() != "1":
            # Fail before any WSGI import or database request.
            raise RequestLatencyBenchmarkError("MySQL benchmark target is not disposable")
        # Collect only normalized host values for fail-closed comparison.
        loopback_hosts = {
            str(os.environ.get(name, "")).strip().lower()  # Normalize one host without retaining it.
            for name in (  # Read the three guarded host roles.
                "CASINO_MYSQL_HOST",  # Inspect the DML-only runtime host.
                "CASINO_MYSQL_MIGRATION_HOST",  # Inspect the migration host.
                "CASINO_MYSQL_TEST_ADMIN_HOST",  # Inspect the disposable administrator host.
            )
        }
        # Require every runtime, migration, and disposable-admin target to be literal loopback.
        if loopback_hosts != {"127.0.0.1"}:
            # Fail without including any configured host value.
            raise RequestLatencyBenchmarkError("MySQL benchmark target is not loopback")
        # Parse only the three guarded endpoint ports.
        try:
            # Collect the runtime, migration, and disposable administrator ports.
            guarded_ports = {
                int(str(os.environ.get(name, "")).strip())  # Parse one bounded port fact.
                for name in (  # Read only the three endpoint roles.
                    "CASINO_MYSQL_PORT",  # Inspect the runtime DML port.
                    "CASINO_MYSQL_MIGRATION_PORT",  # Inspect the migration port.
                    "CASINO_MYSQL_TEST_ADMIN_PORT",  # Inspect the disposable administrator port.
                )
            }
        # Convert missing or malformed endpoint facts into one fixed refusal.
        except (TypeError, ValueError):
            # Fail before any runtime import.
            raise RequestLatencyBenchmarkError("MySQL benchmark target is not loopback") from None
        # Require all roles to select one valid loopback service.
        if len(guarded_ports) != 1 or not 1 <= next(iter(guarded_ports)) <= 65_535:
            # Reject split or invalid disposable endpoints.
            raise RequestLatencyBenchmarkError("MySQL benchmark target is not loopback")
    # Select the exact provider before importing any Casino runtime package.
    os.environ["CASINO_STORAGE_PROVIDER"] = provider
    # Select the production adapter without opening a server.
    os.environ["CASINO_DEPLOYMENT_MODE"] = "production"
    # Keep all mutable application state outside the checkout.
    os.environ["CASINO_DATA_DIR"] = str(runtime_root / "state")
    # Keep all child diagnostics outside the checkout and evidence.
    os.environ["CASINO_LOG_DIR"] = str(runtime_root / "logs")
    # Supply the synthetic bootstrap identity only to this child.
    os.environ["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = SYNTHETIC_EMAIL
    # Supply the synthetic bootstrap credential only to this child.
    os.environ["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = SYNTHETIC_PASSWORD
    # Supply an independent synthetic token-digest key.
    os.environ["CASINO_TOKEN_DIGEST_KEY"] = "request-latency-token-digest-key-material-2026"
    # Supply an independent synthetic mail-digest key.
    os.environ["CASINO_MAIL_DIGEST_KEY"] = "request-latency-mail-digest-key-material-2026"
    # Supply the reserved-domain canonical origin.
    os.environ["CASINO_CANONICAL_ORIGIN"] = SYNTHETIC_ORIGIN
    # Trust only the direct loopback peer.
    os.environ["CASINO_TRUSTED_PROXY"] = "127.0.0.1"
    # Keep the restricted-preview gates active.
    os.environ["CASINO_RESTRICTED_PREVIEW"] = "1"
    # Keep the strongest same-origin session-cookie mode.
    os.environ["CASINO_SESSION_SAMESITE"] = "Strict"
    # Provide a synthetic monitor digest required by production startup.
    os.environ["CASINO_EDGE_MONITOR_TOKEN_SHA256"] = "eef030561320bbeb84bbf72c8c3a82f1ca2db8f9e8f9a1d66867ac886a6fb10c"
    # Apply the fixed test-only request allowance.
    os.environ["CASINO_RATE_LIMIT_REQUESTS"] = str(TEST_RATE_ALLOWANCE)
    # Keep the allowance inside one fixed bounded window.
    os.environ["CASINO_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    # Prevent child imports from writing bytecode into the checkout.
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    # Remove every optional pool override so MySQL uses repository defaults.
    for key in MYSQL_POOL_OVERRIDE_KEYS:
        # Remove only the child-process environment entry.
        os.environ.pop(key, None)
    # Remove every administrator and migrator capability before WSGI import.
    for key in MYSQL_CHILD_CAPABILITY_KEYS:
        # Preserve only loopback host/port facts and runtime DML credentials.
        os.environ.pop(key, None)


# Resolve exact checkout provenance with one fixed, value-free failure boundary.
def _checkout_head() -> str:
    # Start the bounded read-only Git query without accepting caller assertions.
    try:
        # Resolve the immutable commit checked out in this exact worktree.
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # Execute only the exact provenance query.
            cwd=str(ROOT),  # Bind the query to this benchmark checkout.
            capture_output=True,  # Keep all command output out of diagnostics.
            text=True,  # Decode only the bounded commit response.
            timeout=10,  # Bound process startup and Git metadata access.
        )
    # Normalize timeout and launch failures without retaining command or OS text.
    except (subprocess.TimeoutExpired, OSError):
        # Raise one fixed provenance failure without exception chaining.
        raise RequestLatencyBenchmarkError("request-latency source commit is unavailable") from None
    # Normalize the bounded result only after successful process completion.
    resolved = result.stdout.strip().lower() if result.returncode == 0 else ""
    # Require one full lowercase immutable commit.
    if not SOURCE_COMMIT_PATTERN.fullmatch(resolved):
        # Refuse nonzero, malformed, or missing Git output.
        raise RequestLatencyBenchmarkError("request-latency source commit is unavailable")
    # Return only the verified checkout identity.
    return resolved


# Collect rows in the required read-before-mutation order.
def _collect_rows(client: DirectWSGIClient) -> list[dict]:
    # Retain only sanitized aggregate rows.
    rows: list[dict] = []
    # Complete every read family before any Boule mutation or control.
    for route_family in READ_ROUTE_FAMILIES:
        # Measure every required concurrency in deterministic order.
        for concurrency in CONCURRENCY_LEVELS:
            # Append only the approved aggregate row.
            rows.append(_measure_row(client, route_family, concurrency))
    # Prove Boule first, replay, conflict, and wallet invariants before timed mutations.
    original_round, _original_balance = _boule_controls(client)
    # Measure the one mutation family only after every GET row is terminal.
    for concurrency in CONCURRENCY_LEVELS:
        # Append one approved timed Boule row.
        rows.append(_measure_row(client, "boule_spin", concurrency))
    # Re-prove the original receipt after timed keys exceed compact state retention.
    _boule_receipt_cap_control(client, original_round)
    # Return the complete deterministic five-by-four inventory.
    return rows


# Close only the active provider's optional owned pool lifecycle.
def _close_active_provider(storage_module) -> None:
    # Resolve the active provider without changing provider selection.
    active_provider = storage_module.get_storage_provider()
    # Resolve the optional pool lifecycle hook.
    close_pool = getattr(active_provider, "close_pool", None)
    # Close MySQL idle connections while leaving JSON unchanged.
    if callable(close_pool):
        # Execute the provider-owned cleanup hook.
        close_pool()


# Run the complete listener-free benchmark inside one already isolated child.
def run_benchmark(provider: str, source_commit: str, output_path: str | Path) -> dict:
    # Validate provenance before application initialization.
    if not SOURCE_COMMIT_PATTERN.fullmatch(str(source_commit or "")):
        # Refuse non-commit source identities.
        raise RequestLatencyBenchmarkError("source commit is invalid")
    # Resolve the independent checkout identity before provider or output work.
    checkout_head = _checkout_head()
    # Reject stale or caller-spoofed provenance before application initialization.
    if source_commit != checkout_head:
        # Raise one fixed mismatch without reflecting either commit.
        raise RequestLatencyBenchmarkError("source commit does not match checkout")
    # Resolve the external destination before creating runtime state.
    output = resolve_output_path(output_path)
    # Allocate external runtime state that is removed after provider cleanup.
    with tempfile.TemporaryDirectory(prefix="casino-request-latency-") as temporary:
        # Resolve the external runtime root.
        runtime_root = Path(temporary).resolve()
        # Configure provider, auth, policy, rate, and roots before Casino imports.
        _configure_child_environment(provider, runtime_root)
        # Import the production WSGI application only after environment readiness.
        from casino.wsgi import application
        # Import the active provider accessor only after the same readiness boundary.
        from casino.core import storage

        # Bind one listener-free client before protected authentication and measurement.
        client = DirectWSGIClient(application)
        # Protect provider cleanup after every post-import setup or route failure.
        try:
            # Authenticate once outside every timed row.
            client.authenticate()
            # Collect the complete read-before-mutation aggregate inventory.
            rows = _collect_rows(client)
        # Always close provider-owned pool resources before temporary cleanup.
        finally:
            # Close only provider-owned resources through the focused helper.
            _close_active_provider(storage)
        # Build the complete allowlisted evidence object.
        evidence = {
            "schema": EVIDENCE_SCHEMA,  # Identify the strict aggregate schema.
            "source_commit": source_commit,  # Bind evidence to exact source.
            "provider": provider,  # Identify only JSON or MySQL.
            "rows": rows,  # Include only validated aggregate rows.
        }
        # Write only validated aggregate evidence atomically.
        write_evidence_atomic(output, evidence)
        # Return the same sanitized evidence for focused callers.
        return evidence


# Execute one provider benchmark in a clean child with no credential arguments.
def run_provider_subprocess(provider: str, source_commit: str, output_path: str | Path) -> None:
    # Validate output before constructing the child command.
    output = resolve_output_path(output_path)
    # Copy the current environment so a disposable MySQL callback can inherit its guarded tuple.
    environment = os.environ.copy()
    # Remove optional pool overrides so the child exercises exact defaults.
    for key in MYSQL_POOL_OVERRIDE_KEYS:
        # Remove only the child environment value.
        environment.pop(key, None)
    # Remove every disposable administrator or migrator capability.
    for key in MYSQL_CHILD_CAPABILITY_KEYS:
        # Preserve only guarded endpoint facts and runtime DML credentials.
        environment.pop(key, None)
    # Prevent the child from writing bytecode into the checkout.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    # Start a bounded child without surfacing its command, path, or environment.
    try:
        # Run only this explicit module selector in a fresh interpreter.
        result = subprocess.run(
            [
                sys.executable,  # Reuse the exact active interpreter.
                "-m",  # Execute the benchmark as an import-safe module.
                "tests.request_latency_benchmark",  # Select only the explicit child entry.
                "--provider",  # Name the fixed provider selector.
                provider,  # Pass only the low-cardinality provider identity.
                "--source-commit",  # Name exact provenance.
                source_commit,  # Pass only the validated hexadecimal commit.
                "--output",  # Name the caller-owned destination selector.
                str(output),  # Pass the validated external output path.
            ],
            # Resolve imports from the exact checkout.
            cwd=str(ROOT),
            # Inherit only the minimized guarded provider environment.
            env=environment,
            # Capture child diagnostics so no environment detail is reflected.
            capture_output=True,
            # Decode bounded output for process management only.
            text=True,
            # Bound the fixed baseline without creating a numeric acceptance threshold.
            timeout=900,
        )
    # Normalize timeout and bounded process-launch failures.
    except (subprocess.TimeoutExpired, OSError):
        # Raise only the fixed safe diagnostic without exception chaining.
        raise RequestLatencyBenchmarkError("request-latency benchmark child failed") from None
    # Reject any child failure with one fixed secret-safe message.
    if result.returncode != 0:
        # Avoid including child stdout, stderr, paths, or configuration.
        raise RequestLatencyBenchmarkError("request-latency benchmark child failed")


# Parse and run only the explicit benchmark child invocation.
def main() -> int:
    # Build the dependency-free explicit selector.
    parser = argparse.ArgumentParser()
    # Require one approved provider.
    parser.add_argument("--provider", choices=("json", "mysql"), required=True)
    # Require exact source provenance.
    parser.add_argument("--source-commit", required=True)
    # Require a caller-owned external evidence destination.
    parser.add_argument("--output", required=True)
    # Parse the explicit child arguments.
    arguments = parser.parse_args()
    # Run one provider and atomically write its evidence.
    run_benchmark(arguments.provider, arguments.source_commit, arguments.output)
    # Return success only after cleanup and atomic output replacement.
    return 0


# Support explicit module execution without affecting ordinary imports.
if __name__ == "__main__":
    # Convert stable benchmark failures into one bounded process status.
    try:
        # Exit with the explicit runner result.
        raise SystemExit(main())
    # Suppress all dynamic exception text from command output.
    except RequestLatencyBenchmarkError:
        # Print only one fixed safe diagnostic.
        print("request-latency benchmark failed", file=sys.stderr)
        # Exit nonzero after the fixed diagnostic.
        raise SystemExit(1)
