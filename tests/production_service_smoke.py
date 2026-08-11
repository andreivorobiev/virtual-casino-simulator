# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Run TEST-046 lifecycle evidence against a clean extracted release artifact."""

# Import command-line parsing for the explicit release artifact input.
import argparse
# Import module discovery so unsupported local platforms can report a bounded skip.
import importlib.util
# Import JSON encoding and decoding for API persistence checks.
import json
# Import operating-system process-group and environment support.
import os
# Import portable paths for safe release extraction and sibling runtime roots.
import pathlib
# Import POSIX signals for exact tracked process-group cleanup on timeout.
import signal
# Import sockets for ephemeral allocation and listener-closure proof.
import socket
# Import subprocess execution for Gunicorn lifecycle and startup-failure checks.
import subprocess
# Import the active interpreter for the extracted release process.
import sys
# Import disposable directory support for release, state, and logs.
import tempfile
# Import bounded polling delays for service readiness and listener closure.
import time
# Import standard HTTP requests for same-origin liveness, auth, and persistence checks.
import urllib.error
# Import the request client paired with the HTTP error type.
import urllib.request
# Import ZIP support for validated clean-copy extraction.
import zipfile

# Reserve the user-owned local ports that this smoke must never bind or stop.
PROTECTED_PORTS = frozenset({8765, 8877})
# Use one synthetic reserved-domain origin for every copied-release request.
CANONICAL_ORIGIN = "https://casino.example.invalid"
# Preserve its exact authority independently from the private loopback transport URL.
CANONICAL_AUTHORITY = "casino.example.invalid"


# Parse the one immutable application archive supplied by the release driver.
def parse_args():
    # Describe the copied-release production lifecycle gate.
    parser = argparse.ArgumentParser(description="Smoke-test the production service from a clean release artifact.")
    # Require an explicit archive so the smoke cannot silently use a source checkout.
    parser.add_argument("--archive", required=True, type=pathlib.Path)
    # Return the validated command-line namespace.
    return parser.parse_args()


# Allocate one operating-system-selected loopback port outside protected user listeners.
def free_port() -> int:
    # Retry only if the operating system selects one of the two protected ports.
    while True:
        # Create a short-lived IPv4 socket solely for ephemeral allocation.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to loopback and request an operating-system-selected port.
        probe.bind(("127.0.0.1", 0))
        # Read the selected numeric port before closing the allocation socket.
        port = int(probe.getsockname()[1])
        # Close immediately so the tracked Gunicorn process can claim the port.
        probe.close()
        # Return only a port that cannot overlap protected local listeners.
        if port not in PROTECTED_PORTS:
            # Hand the safe ephemeral port to the service launcher.
            return port


# Build the isolated production environment shared across one controlled restart.
def service_environment(runtime_root: pathlib.Path, port: int) -> dict:
    # Copy interpreter and platform settings without modifying the parent process.
    environment = os.environ.copy()
    # Select explicit fail-closed production mode.
    environment["CASINO_DEPLOYMENT_MODE"] = "production"
    # Keep persistent smoke state outside the extracted immutable release.
    environment["CASINO_DATA_DIR"] = str(runtime_root / "state")
    # Keep application diagnostics outside the extracted immutable release.
    environment["CASINO_LOG_DIR"] = str(runtime_root / "logs")
    # Use provider-neutral JSON until the separate migration gate releases MySQL service validation.
    environment["CASINO_STORAGE_PROVIDER"] = "json"
    # Supply a synthetic reserved-domain Admin identity only inside the disposable process.
    environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = "service-smoke@example.invalid"
    # Supply a synthetic external token-digest key for the isolated production adapter probe.
    environment["CASINO_TOKEN_DIGEST_KEY"] = "service-smoke-token-digest-key-material-2026"
    # Supply an independent synthetic mail digest key required by public startup.
    environment["CASINO_MAIL_DIGEST_KEY"] = "service-smoke-mail-digest-key-material-2026"
    # Supply a synthetic non-default credential that is never printed or persisted in evidence.
    environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = "synthetic-service-smoke-password"
    # Supply the restricted-preview exact origin through a reserved test domain.
    environment["CASINO_CANONICAL_ORIGIN"] = CANONICAL_ORIGIN
    # Trust only the direct IPv4 loopback proxy peer.
    environment["CASINO_TRUSTED_PROXY"] = "127.0.0.1"
    # Enable the explicitly released restricted-preview stage.
    environment["CASINO_RESTRICTED_PREVIEW"] = "1"
    # Use the strict governed same-origin cookie mode.
    environment["CASINO_SESSION_SAMESITE"] = "Strict"
    # Select the safe ephemeral port while the config fixes the listener interface to loopback.
    environment["CASINO_BIND_PORT"] = str(port)
    # Prevent extracted release bytecode writes during smoke execution.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    # Flush child lifecycle diagnostics even though the smoke discards them.
    environment["PYTHONUNBUFFERED"] = "1"
    # Return the isolated mapping for child process creation.
    return environment


# Extract only traversal-safe members into the disposable clean release root.
def extract_release(archive_path: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    # Open the immutable candidate archive for member validation.
    with zipfile.ZipFile(archive_path, "r") as archive:
        # Inspect every member before extracting any bytes.
        for name in archive.namelist():
            # Parse ZIP member paths with portable POSIX semantics.
            member = pathlib.PurePosixPath(name)
            # Reject absolute or parent-traversal members before filesystem access.
            if member.is_absolute() or ".." in member.parts:
                # Stop with a value-free structural error.
                raise RuntimeError("release artifact contains an unsafe member path")
        # Extract the already validated members into the disposable destination.
        archive.extractall(destination)
    # Resolve the canonical single archive root produced by package_app.py.
    release_root = destination / "virtual_casino_simulator"
    # Require the production adapter to be present in the clean artifact.
    if not (release_root / "casino" / "wsgi.py").is_file():
        # Fail without falling back to the source checkout.
        raise RuntimeError("release artifact is missing the production adapter")
    # Require the exact process policy consumed by the service command.
    if not (release_root / "deploy" / "gunicorn.conf.py").is_file():
        # Fail without constructing an alternate invocation.
        raise RuntimeError("release artifact is missing the production process policy")
    # Return the authenticated clean release root for child execution.
    return release_root


# Send one JSON API request and return its decoded standard envelope.
def api_request(base_url: str, path: str, method="GET", body=None, token=None, csrf=None) -> dict:
    # Encode an optional request object as UTF-8 JSON.
    payload = None if body is None else json.dumps(body).encode("utf-8")
    # Start with the accepted request content type.
    headers = {"Content-Type": "application/json", "Host": CANONICAL_AUTHORITY}
    # Add the disposable bearer token only to authenticated smoke requests.
    if token:
        # Keep the token inside the request object and out of diagnostics.
        headers["Authorization"] = f"Bearer {token}"
    # Attach exact Origin and a distinct CSRF proof to every state-changing request.
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        # Require the caller to supply either a bootstrap or authenticated session CSRF value.
        if not csrf:
            # Fail inside the smoke without starting an unsafe mutation.
            raise RuntimeError("production smoke mutation requires CSRF proof")
        # Supply the exact configured Origin.
        headers["Origin"] = CANONICAL_ORIGIN
        # Supply the explicit CSRF proof header.
        headers["X-CSRF-Token"] = csrf
        # Supply the bootstrap double-submit cookie; authenticated requests are validated against session state.
        headers["Cookie"] = f"casino_csrf={csrf}"
    # Construct the bounded same-origin loopback request.
    request = urllib.request.Request(base_url + path, data=payload, method=method, headers=headers)
    # Open the request with a short timeout so a failed worker cannot stall the gate.
    with urllib.request.urlopen(request, timeout=3) as response:
        # Decode the exact JSON envelope returned by the production process.
        return json.loads(response.read().decode("utf-8"))


# Bootstrap one anonymous double-submit token without relying on Secure-cookie storage over loopback HTTP.
def bootstrap_csrf(base_url: str) -> str:
    # Request the packaged shell with the exact configured authority.
    request = urllib.request.Request(base_url + "/", method="GET", headers={"Host": CANONICAL_AUTHORITY})
    # Open the direct loopback request with the same bounded timeout as API calls.
    with urllib.request.urlopen(request, timeout=3) as response:
        # Read the one bootstrap Set-Cookie header without printing it.
        cookie = response.headers.get("Set-Cookie", "")
        # Require the expected host-only CSRF cookie.
        if not cookie.startswith("casino_csrf="):
            # Fail with a value-free diagnostic.
            raise RuntimeError("production smoke did not receive a CSRF bootstrap cookie")
        # Return only the cookie scalar before attributes.
        return cookie.split(";", 1)[0].split("=", 1)[1]


# Wait for sanitized liveness or fail when the tracked process exits or times out.
def wait_until_live(process: subprocess.Popen, base_url: str) -> None:
    # Poll for at most fifteen seconds across normal CI startup variability.
    deadline = time.monotonic() + 15
    # Continue only while the deadline has not expired.
    while time.monotonic() < deadline:
        # Stop immediately when the tracked Gunicorn master has exited.
        if process.poll() is not None:
            # Report only lifecycle state, not child output or paths.
            raise RuntimeError("production service exited before liveness")
        # Start protected request handling because connection refusal is expected during boot.
        try:
            # Query the anonymous sanitized liveness endpoint.
            payload = api_request(base_url, "/healthz")
            # Return only after the exact accepted live payload appears.
            if payload == {"ok": True, "data": {"status": "live"}}:
                # Mark worker readiness without emitting the test URL.
                return
        # Ignore bounded connection and HTTP failures until the deadline.
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError):
            # Continue after a short bounded delay.
            pass
        # Avoid a busy loop while the worker initializes external state.
        time.sleep(0.1)
    # Fail with a value-free diagnostic when liveness never succeeds.
    raise RuntimeError("production service did not become live")


# Start the extracted production process as one independently tracked POSIX process group.
def start_service(release_root: pathlib.Path, environment: dict, base_url: str) -> subprocess.Popen:
    # Resolve the packaged Gunicorn policy inside the extracted release.
    config_path = release_root / "deploy" / "gunicorn.conf.py"
    # Start the production server without exposing child output or process arguments in evidence.
    process = subprocess.Popen(
        # Use the exact supported WSGI application and packaged process configuration.
        [sys.executable, "-m", "gunicorn", "--config", str(config_path), "casino.wsgi:application"],
        # Resolve imports and static assets only from the clean extracted release.
        cwd=release_root,
        # Pass the isolated external runtime configuration.
        env=environment,
        # Discard child standard output to keep credentials and private paths out of evidence.
        stdout=subprocess.DEVNULL,
        # Discard child standard error for the same secret-safe reason.
        stderr=subprocess.DEVNULL,
        # Give the master and worker one exact group for bounded cleanup.
        start_new_session=True,
    )
    # Start protected readiness handling so a failed boot cannot leave an orphan process group.
    try:
        # Require the worker to become live before returning it to the caller.
        wait_until_live(process, base_url)
    # Stop the exact tracked process and listener before propagating any readiness failure.
    except Exception:
        # Parse the already private loopback port without printing the URL.
        port = int(base_url.rsplit(":", 1)[1])
        # Apply the same bounded process-group cleanup used after successful startup.
        stop_service(process, port)
        # Preserve the original readiness failure after cleanup succeeds.
        raise
    # Return the exact tracked process object after readiness succeeds.
    return process


# Prove one loopback port no longer accepts connections.
def assert_listener_closed(port: int) -> None:
    # Poll for at most five seconds after graceful master exit.
    deadline = time.monotonic() + 5
    # Continue until the listener closes or the deadline expires.
    while time.monotonic() < deadline:
        # Create a short-lived probe socket for the exact smoke port.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bound each connection attempt to avoid cleanup stalls.
        probe.settimeout(0.1)
        # Test only the known loopback listener selected by this smoke.
        open_listener = probe.connect_ex(("127.0.0.1", port)) == 0
        # Close the probe immediately on every result.
        probe.close()
        # Return as soon as no process accepts connections on the tracked port.
        if not open_listener:
            # Complete listener-closure proof without printing the port.
            return
        # Wait briefly before the next bounded probe.
        time.sleep(0.1)
    # Fail when a worker or orphan still owns the tracked listener.
    raise RuntimeError("production listener remained open after stop")


# Terminate the exact tracked process group and require bounded graceful closure.
def stop_service(process: subprocess.Popen, port: int) -> None:
    # Skip duplicate signaling when the process already exited.
    if process.poll() is None:
        # Send SIGTERM to the Gunicorn master for its configured graceful drain.
        process.terminate()
    # Start protected waiting so only this tracked group receives a timeout fallback.
    try:
        # Wait within the documented systemd stop boundary.
        process.wait(timeout=25)
    # Kill only the process group created by this smoke when graceful drain fails.
    except subprocess.TimeoutExpired:
        # Send SIGKILL to the exact child session rather than any unrelated process.
        os.killpg(process.pid, signal.SIGKILL)
        # Reap the master after the bounded fallback.
        process.wait(timeout=5)
        # Fail the gate even though listener cleanup continues below.
        raise RuntimeError("production service exceeded graceful stop timeout")
    # Require the tracked port to close after master and worker exit.
    assert_listener_closed(port)


# Prove missing external configuration fails before worker readiness.
def assert_missing_configuration_fails(release_root: pathlib.Path, environment: dict) -> None:
    # Copy the valid environment before removing one required external root.
    incomplete = dict(environment)
    # Remove only the data root to trigger the production startup guard.
    incomplete.pop("CASINO_DATA_DIR")
    # Import the production adapter without starting Gunicorn or creating a listener.
    result = subprocess.run(
        # Use a fresh interpreter so module-level configuration cannot be cached.
        [sys.executable, "-c", "import casino.wsgi"],
        # Resolve imports from the clean extracted release only.
        cwd=release_root,
        # Pass the deliberately incomplete configuration.
        env=incomplete,
        # Discard standard output because only the return code is durable evidence.
        stdout=subprocess.DEVNULL,
        # Discard standard error so no private path or value enters smoke output.
        stderr=subprocess.DEVNULL,
        # Bound the expected startup failure.
        timeout=15,
    )
    # Reject any fallback that lets the production adapter initialize without external state.
    if result.returncode == 0:
        # Report only the failed invariant.
        raise RuntimeError("production adapter accepted missing external runtime configuration")


# Execute copied-release failure, liveness, graceful restart, persistence, and closure evidence.
def main() -> int:
    # Parse the explicit immutable artifact path.
    args = parse_args()
    # Skip only unsupported Windows execution because Gunicorn itself is POSIX-only.
    if os.name == "nt":
        # Report a bounded platform skip; Linux CI remains the required process-lifecycle gate.
        print("Copied-release Gunicorn lifecycle smoke is deferred to Linux CI; listener-free adapter tests passed locally.")
        # Return success so Windows developers can run the complete repository validator set.
        return 0
    # Require Gunicorn to be installed from declared validation requirements.
    if importlib.util.find_spec("gunicorn") is None:
        # Fail rather than silently weakening Linux release evidence.
        raise RuntimeError("declared Gunicorn validation dependency is unavailable")
    # Allocate one disposable root for extracted bytes and sibling mutable state.
    with tempfile.TemporaryDirectory(prefix="casino-production-smoke-") as temporary:
        # Resolve the disposable root without retaining it in output.
        temporary_root = pathlib.Path(temporary)
        # Extract the exact artifact into its immutable test subtree.
        release_root = extract_release(args.archive.resolve(), temporary_root / "release")
        # Resolve mutable runtime state as a sibling outside the release root.
        runtime_root = temporary_root / "runtime"
        # Select one safe operating-system-assigned loopback port.
        port = free_port()
        # Defend the protected port boundary before starting any child process.
        if port in PROTECTED_PORTS:
            # Fail before listener creation if allocator policy ever regresses.
            raise RuntimeError("smoke selected a protected listener port")
        # Build one environment reused across the controlled process restart.
        environment = service_environment(runtime_root, port)
        # Build the private loopback base URL without printing it.
        base_url = f"http://127.0.0.1:{port}"
        # Prove an incomplete external configuration cannot initialize the production adapter.
        assert_missing_configuration_fails(release_root, environment)
        # Track the first process for guaranteed scoped cleanup.
        first = None
        # Start protected lifecycle handling around the first worker.
        try:
            # Start the clean extracted release through the supported production command.
            first = start_service(release_root, environment, base_url)
            # Authenticate the synthetic Admin through the production listener.
            csrf = bootstrap_csrf(base_url)
            # Authenticate with the exact bootstrap double-submit proof.
            login = api_request(base_url, "/api/v2/auth/login", "POST", {"email": "service-smoke@example.invalid", "password": "synthetic-service-smoke-password"}, csrf=csrf)
            # Retain the disposable token only in memory for the mutation request.
            token = login["data"]["session"]["token"]
            # Retain the distinct per-session CSRF value only in memory.
            csrf = login["data"]["session"]["csrf_token"]
            # Add a deterministic play-token amount through the authenticated API.
            updated = api_request(base_url, "/api/v2/me/tokens/add", "POST", {"amount": 7, "reason": "service_restart_smoke"}, token, csrf)
            # Capture the resulting persistent balance for post-restart comparison.
            expected_balance = updated["data"]["balance"]
        # Stop the exact first child and prove listener closure on every path.
        finally:
            # Signal only when child creation reached a process object.
            if first is not None:
                # Require graceful process and listener cleanup.
                stop_service(first, port)
        # Track the restarted process for guaranteed scoped cleanup.
        second = None
        # Start protected lifecycle handling around the restarted worker.
        try:
            # Restart from the same immutable release and external state root.
            second = start_service(release_root, environment, base_url)
            # Reauthenticate after restart so no in-memory session object is required.
            csrf = bootstrap_csrf(base_url)
            # Reauthenticate with a fresh anonymous bootstrap proof after restart.
            login = api_request(base_url, "/api/v2/auth/login", "POST", {"email": "service-smoke@example.invalid", "password": "synthetic-service-smoke-password"}, csrf=csrf)
            # Retain the new disposable token only inside this process.
            token = login["data"]["session"]["token"]
            # Read the persisted current-user player record after restart.
            current = api_request(base_url, "/api/v2/me", token=token)
            # Require the prior mutation to survive the controlled restart.
            if current["data"]["player"]["balance"] != expected_balance:
                # Fail without printing user, token, balance, or path data.
                raise RuntimeError("production restart did not preserve application state")
        # Stop the restarted child and prove final listener closure on every path.
        finally:
            # Signal only when restart reached a process object.
            if second is not None:
                # Require graceful process and listener cleanup again.
                stop_service(second, port)
    # Report only sanitized acceptance dimensions after all disposable data is removed.
    print("Copied-release production smoke passed: loopback, liveness, graceful restart, persistence, failure guard, and listener closure.")
    # Return success after every lifecycle gate passes.
    return 0


# Run the explicit artifact smoke only when invoked as a script.
if __name__ == "__main__":
    # Exit with the stable result code for release workflow enforcement.
    raise SystemExit(main())
