# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Validate and observe the restricted-preview edge without mutating deployment state."""

# Import argument parsing for the repository validator and read-only observation commands.
import argparse
# Import UTC timestamp helpers for sanitized observation evidence.
import datetime
# Import JSON support for the declarative edge policy and bounded HTTP responses.
import json
# Import environment access for the externally managed monitor credential.
import os
# Import portable paths for repository-contained policy and template validation.
import pathlib
# Import sockets only for the read-only TLS certificate validity probe.
import socket
# Import verified TLS support for HTTPS and certificate-expiration checks.
import ssl
# Import process time for certificate age calculation without exposing provider metadata.
import time
# Import the standard-library HTTPS client so the tool adds no runtime dependency.
import urllib.request

# Resolve the immutable repository root independently of the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Select the reviewed restricted-preview policy when the caller does not override it.
DEFAULT_POLICY = ROOT / "deploy" / "edge" / "restricted-preview.json"
# Name the root-managed environment value without ever printing its contents.
COOKIE_ENV = "CASINO_EDGE_MONITOR_COOKIE"
# Name the preferred root-managed bearer value without ever printing its contents.
AUTHORIZATION_ENV = "CASINO_EDGE_MONITOR_AUTHORIZATION"
# Keep all policy failures in a fixed secret-safe category vocabulary.
ALLOWED_ERROR_CODES = {"access_policy", "certificate_age", "certificate_unavailable", "credential_missing", "endpoint_body", "endpoint_headers", "endpoint_status", "endpoint_unavailable", "ingress_policy", "invalid_policy", "monitoring_policy", "origin_policy", "proxy_policy", "rollback_policy", "template_content", "template_path", "upstream_policy"}
# Define the complete fixed probe contract so additional public or privileged routes fail closed.
EXPECTED_PROBES = [("liveness", "/healthz", False, 200, {"status": "live"}), ("readiness", "/readyz", True, 200, {"ready": True, "storage_provider": "mysql"}), ("admin_operations", "/api/v2/admin/operations", True, 200, {"ready": True})]
# Define the exact hardened response headers already emitted by the #203 application boundary.
EXPECTED_HEADERS = {"Content-Security-Policy": "present", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY", "Strict-Transport-Security": "max-age=31536000"}


# Carry only a fixed category code across validation and observation failure boundaries.
class EdgeGateError(RuntimeError):
    # Initialize the exception after confirming the code is part of the public safe vocabulary.
    def __init__(self, code):
        # Replace programmer mistakes with the generic policy category instead of leaking values.
        safe_code = code if code in ALLOWED_ERROR_CODES else "invalid_policy"
        # Initialize the base exception with the fixed code for ordinary CLI exit handling.
        super().__init__(safe_code)
        # Retain the safe code without attaching paths, responses, or credential-bearing text.
        self.code = safe_code


# Disable every HTTP redirect so authenticated probes cannot carry session material to another request target.
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Refuse redirect construction for every status, method, and target.
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        # Return no follow-up request so urllib converts the redirect into a fixed endpoint failure.
        return None


# Raise one fixed fail-closed category when a required predicate does not hold.
def _require(predicate, code):
    # Stop immediately when repository or live evidence violates the reviewed contract.
    if not predicate:
        # Raise only the caller-selected secret-safe category.
        raise EdgeGateError(code)


# Read one JSON policy while converting syntax and filesystem failures to a fixed category.
def _read_policy(policy_path):
    # Start protected parsing so raw path and decoder details never reach CLI evidence.
    try:
        # Decode the reviewed UTF-8 policy into an in-memory object.
        policy = json.loads(pathlib.Path(policy_path).read_text(encoding="utf-8"))
    # Convert every local read or parse failure into the same safe policy category.
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        # Suppress the raw exception while preserving fail-closed behavior.
        raise EdgeGateError("invalid_policy") from exc
    # Require a mapping so later exact-key checks cannot be confused by another JSON type.
    _require(isinstance(policy, dict), "invalid_policy")
    # Return the decoded mapping for exact policy validation.
    return policy


# Resolve and read a repository template without permitting absolute paths or traversal.
def _read_template(root, relative_path):
    # Convert the declared template location to a portable relative path object.
    candidate_relative = pathlib.Path(relative_path)
    # Reject absolute and parent-traversing template declarations before filesystem access.
    _require(not candidate_relative.is_absolute() and ".." not in candidate_relative.parts, "template_path")
    # Resolve both sides so symlink and normalization tricks remain inside the repository root.
    resolved_root = pathlib.Path(root).resolve()
    # Resolve the declared template against the immutable repository root.
    resolved_candidate = (resolved_root / candidate_relative).resolve()
    # Start protected containment and read checks so raw host paths never enter evidence.
    try:
        # Require the final resolved file to remain underneath the repository root.
        resolved_candidate.relative_to(resolved_root)
        # Read the complete template as reviewed UTF-8 text.
        return resolved_candidate.read_text(encoding="utf-8")
    # Convert missing, unreadable, invalid, or escaping paths into one safe category.
    except (OSError, UnicodeError, ValueError) as exc:
        # Suppress the raw filesystem detail while preserving fail-closed behavior.
        raise EdgeGateError("template_path") from exc


# Require every reviewed snippet and reject every forbidden snippet in one inert template.
def _validate_template(text, required, forbidden=()):
    # Require every security-significant reviewed line without executing the template.
    for snippet in required:
        # Fail closed if a required literal has been removed or altered.
        _require(snippet in text, "template_content")
    # Reject forwarding, exposure, issuance, or database commands that the packet forbids.
    for snippet in forbidden:
        # Fail closed if any forbidden literal is present in the inert source.
        _require(snippet not in text, "template_content")


# Validate the exact declarative contract and all inert templates without network or subprocess use.
def validate_policy(policy_path=DEFAULT_POLICY, root=ROOT):
    # Decode the policy from the selected repository copy.
    policy = _read_policy(policy_path)
    # Require the exact schema and non-activated stage markers.
    _require(policy.get("schema") == "casino.edge-policy.v1", "invalid_policy")
    # Refuse any policy that claims deployment or activation has already occurred.
    _require(policy.get("stage") == "repository-preparation-only", "invalid_policy")
    # Bind the edge to the owner-confirmed same-origin HTTPS hostname only.
    _require(policy.get("canonical_origin") == "https://casino.tiltseven.com", "origin_policy")
    # Require the matching canonical Host value consumed by #203.
    _require(policy.get("canonical_host") == "casino.tiltseven.com", "origin_policy")
    # Require the complete application upstream to remain plain HTTP on fixed IPv4 loopback.
    _require(policy.get("upstream") == {"scheme": "http", "host": "127.0.0.1", "port": 8765}, "upstream_policy")
    # Extract the ingress policy for exact port and SSH-boundary checks.
    ingress = policy.get("ingress", {})
    # Allow only normal HTTP and HTTPS in the future cutover template.
    _require(ingress.get("public_tcp_ports") == [80, 443], "ingress_policy")
    # Preserve the database and both protected application/runtime ports as non-public.
    _require(ingress.get("protected_tcp_ports") == [3306, 8765, 8877], "ingress_policy")
    # Preserve source-restricted SSH rather than broadening administrative ingress.
    _require(ingress.get("ssh_source_restricted") is True, "ingress_policy")
    # Require the complete restricted-preview enrollment and Admin policy from #203.
    _require(policy.get("access") == {"manual_invites_only": True, "public_signup_enabled": False, "live_oauth_enabled": False, "admin_requires_authenticated_session": True}, "access_policy")
    # Extract the proxy header contract for exact replacement and clearing checks.
    proxy = policy.get("proxy", {})
    # Replace Host and trusted forwarding headers with edge-owned canonical values.
    _require(proxy.get("request_headers") == {"Host": "casino.tiltseven.com", "X-Forwarded-For": "$remote_addr", "X-Forwarded-Proto": "https"}, "proxy_policy")
    # Clear every other forwarding header so client-supplied chains cannot cross #203.
    _require(proxy.get("cleared_request_headers") == ["Forwarded", "X-Forwarded-Host", "X-Forwarded-Port"], "proxy_policy")
    # Require HTTP-01, nginx preflight, and keep-current-on-failure ACME behavior.
    _require(policy.get("acme") == {"challenge": "http-01", "preflight_command": "nginx -t", "keep_current_certificate_on_failure": True}, "invalid_policy")
    # Extract the bounded monitoring contract for exact allowlist validation.
    monitoring = policy.get("monitoring", {})
    # Require short network timeouts, bounded bodies, and a conservative certificate alert threshold.
    _require(monitoring.get("timeout_seconds") == 5, "monitoring_policy")
    # Cap response reads so a compromised edge cannot exhaust the monitor process.
    _require(monitoring.get("maximum_body_bytes") == 65536, "monitoring_policy")
    # Alert before certificate expiration without requesting or renewing a certificate.
    _require(monitoring.get("minimum_certificate_days_remaining") == 14, "monitoring_policy")
    # Require the exact #203 response security header contract.
    _require(monitoring.get("required_response_headers") == EXPECTED_HEADERS, "monitoring_policy")
    # Prefer a bearer monitor token and retain the legacy cookie name only as an explicit compatibility fallback.
    _require(monitoring.get("authentication") == {"preferred_header": "Authorization", "preferred_environment": AUTHORIZATION_ENV, "fallback_cookie_environment": COOKIE_ENV, "authenticated_paths": ["/readyz", "/api/v2/admin/operations"]}, "monitoring_policy")
    # Convert the JSON probe mappings to stable tuples for one exact comparison.
    probes = [(item.get("name"), item.get("path"), item.get("authenticated"), item.get("expected_status"), item.get("expected_json")) for item in monitoring.get("probes", []) if isinstance(item, dict)]
    # Reject missing, reordered, additional, public, or weakened probe declarations.
    _require(probes == EXPECTED_PROBES, "monitoring_policy")
    # Preserve application/edge-only rollback and prohibit schema reversal.
    _require(policy.get("rollback") == {"application_release": "atomic-symlink", "edge_configuration": "prevalidated-replacement", "database_rollback": "prohibited", "post_rollback_probe_required": True}, "rollback_policy")
    # Require the exact five inert template keys and repository-relative locations.
    expected_templates = {"nginx": "deploy/nginx/casino.conf.template", "acme_renewal_hook": "deploy/acme/casino-renewal-hook.sh.template", "monitor_service": "deploy/systemd/casino-edge-monitor.service.template", "monitor_timer": "deploy/systemd/casino-edge-monitor.timer.template", "rollback": "deploy/rollback/casino-edge-rollback.sh.template"}
    # Reject missing, additional, or redirected template declarations.
    _require(policy.get("templates") == expected_templates, "template_path")
    # Read the nginx source only after its path has passed exact declaration checks.
    nginx = _read_template(root, expected_templates["nginx"])
    # Require exact loopback, ACME, redirect, TLS, forwarding, clearing, and bounded proxy behavior.
    _validate_template(nginx, ("server 127.0.0.1:8765;", "listen 80;", "listen 443 ssl http2;", "server_name casino.tiltseven.com casino.andvor.com;", "location ^~ /.well-known/acme-challenge/", "return 308 https://casino.tiltseven.com$request_uri;", "ssl_certificate __TLS_FULLCHAIN_PATH__;", "ssl_certificate_key __TLS_PRIVATE_KEY_PATH__;", "proxy_pass http://casino_restricted_preview;", "proxy_set_header Host casino.tiltseven.com;", "proxy_set_header X-Forwarded-For $remote_addr;", "proxy_set_header X-Forwarded-Proto https;", "proxy_set_header Forwarded \"\";", "proxy_set_header X-Forwarded-Host \"\";", "proxy_set_header X-Forwarded-Port \"\";", "client_max_body_size 1m;"), ("$proxy_add_x_forwarded_for", "listen 8765", "listen 8877", "listen 3306", "proxy_pass http://0.0.0.0"))
    # Read and validate the renewal hook without invoking nginx or a certificate client.
    renewal = _read_template(root, expected_templates["acme_renewal_hook"])
    # Require fail-before-reload behavior and prohibit issuance from the renewal hook.
    _validate_template(renewal, ("set -eu", "nginx -t", "systemctl reload nginx"), ("certbot certonly", "acme.sh --issue"))
    # Read and validate the inactive read-only monitor service template.
    monitor_service = _read_template(root, expected_templates["monitor_service"])
    # Require least privilege, external secret loading, bounded execution, and the observe-only command.
    _validate_template(monitor_service, ("Type=oneshot", "User=casino-monitor", "EnvironmentFile=/etc/casino/edge-monitor.env", "edge_gate.py observe", "TimeoutStartSec=20s", "NoNewPrivileges=true"), ("edge_gate.py validate --activate", "ExecStart=nginx", "ExecStart=certbot"))
    # Read and validate the inactive periodic schedule template.
    monitor_timer = _read_template(root, expected_templates["monitor_timer"])
    # Require a bounded five-minute timer and no command-bearing timer directives.
    _validate_template(monitor_timer, ("OnBootSec=5min", "OnUnitActiveSec=5min", "RandomizedDelaySec=30s", "Persistent=true"), ("ExecStart=",))
    # Read and validate the explicitly application/edge-only rollback template.
    rollback = _read_template(root, expected_templates["rollback"])
    # Require candidate preflight, atomic links, service recovery, observation, and compensation.
    _validate_template(rollback, ("set -eu", ": \"$CASINO_NGINX_PREFLIGHT_CONFIG\"", "nginx -t -c \"$CASINO_NGINX_PREFLIGHT_CONFIG\"", "test -L /opt/casino/current", "test -L /etc/nginx/sites-enabled/casino.conf", "mv -Tf /opt/casino/current.next /opt/casino/current", "if ! systemctl restart casino || ! systemctl reload nginx || !", "edge_gate.py observe", "CASINO_CURRENT_RELEASE", "CASINO_CURRENT_NGINX", "systemctl restart casino || true", "systemctl reload nginx || true"), ("mysqldump ", "mysql ", "scripts/recovery.py", "listen 3306"))
    # Return the exact validated policy for the optional read-only observation phase.
    return policy


# Validate one externally managed monitor credential before any endpoint request.
def _monitor_header_from_environment(environ=None):
    # Use the live process environment unless a focused test supplies synthetic values.
    current_environment = os.environ if environ is None else environ
    # Read the preferred Authorization value without ever logging it.
    authorization = str(current_environment.get(AUTHORIZATION_ENV, "")).strip()
    # Prefer the bearer monitor token so deployment no longer depends on expiring browser cookies.
    if authorization:
        # Refuse malformed or unbounded authorization material before any network call.
        _require(authorization.startswith("Bearer ") and "\r" not in authorization and "\n" not in authorization and len(authorization) <= 4096, "credential_missing")
        # Return the exact header name and value to the request builder only.
        return ("Authorization", authorization)
    # Read the legacy cookie value only when the preferred bearer value is absent.
    cookie = str(current_environment.get(COOKIE_ENV, "")).strip()
    # Refuse missing, malformed, multiline, or unbounded legacy cookie material before any network call.
    _require("=" in cookie and "\r" not in cookie and "\n" not in cookie and len(cookie) <= 4096, "credential_missing")
    # Return the exact legacy header name and value to the request builder only.
    return ("Cookie", cookie)


# Fetch one bounded HTTPS JSON response and return only data needed for policy comparisons.
def _fetch_json(url, monitor_header, timeout, maximum_body_bytes):
    # Build the fixed read-only request headers without attaching credentials to anonymous liveness.
    headers = {"Accept": "application/json"}
    # Add the externally managed monitor credential only to explicitly authenticated probes.
    if monitor_header is not None:
        # Pass the secret directly to the request object without logging or persisting it.
        headers[monitor_header[0]] = monitor_header[1]
    # Construct one GET request so monitoring cannot mutate application state.
    request = urllib.request.Request(url, method="GET", headers=headers)
    # Build a dedicated client that refuses every redirect before it can copy authenticated headers.
    opener = urllib.request.build_opener(_NoRedirect)
    # Start protected transport and parsing so raw network, header, and body details never escape.
    try:
        # Use the default verified TLS context through the standard HTTPS client.
        with opener.open(request, timeout=timeout) as response:
            # Read at most one byte beyond the policy cap to detect oversized responses.
            payload_bytes = response.read(maximum_body_bytes + 1)
            # Retain the numeric status and response header object only for exact comparisons.
            status = response.status
            # Retain headers in memory without including them in success or failure output.
            response_headers = response.headers
    # Collapse transport, TLS, timeout, and HTTP failures into one fixed category.
    except Exception as exc:
        # Suppress all provider, address, certificate, and response detail.
        raise EdgeGateError("endpoint_unavailable") from exc
    # Reject bodies that exceed the reviewed memory and parsing bound.
    _require(len(payload_bytes) <= maximum_body_bytes, "endpoint_body")
    # Start protected UTF-8 JSON parsing without exposing the payload on failure.
    try:
        # Decode one response object for exact allowlisted value checks.
        payload = json.loads(payload_bytes.decode("utf-8"))
    # Collapse encoding and JSON syntax failures into one fixed category.
    except (UnicodeError, json.JSONDecodeError) as exc:
        # Suppress every raw response byte and decoder position.
        raise EdgeGateError("endpoint_body") from exc
    # Require an object rather than accepting attacker-controlled scalar or array responses.
    _require(isinstance(payload, dict), "endpoint_body")
    # Return only in-memory comparison inputs to the observation orchestrator.
    return status, response_headers, payload


# Validate and unwrap one exact repository-standard success envelope without accepting error or ambiguous shapes.
def validated_success_data(payload):
    # Require exactly the two canonical success-envelope fields and no unreviewed top-level metadata.
    _require(isinstance(payload, dict) and set(payload) == {"ok", "data"}, "endpoint_body")
    # Require the literal boolean success value rather than a truthy integer or string.
    _require(payload.get("ok") is True, "endpoint_body")
    # Require an object data payload because every reviewed operational probe returns named fields.
    _require(isinstance(payload.get("data"), dict), "endpoint_body")
    # Return only the validated data object for allowlisted probe-field comparisons.
    return payload["data"]


# Calculate verified certificate lifetime without emitting certificate or network identifiers.
def _certificate_days_remaining(host, timeout, now_epoch):
    # Build the platform-default trust and hostname-verification context.
    context = ssl.create_default_context()
    # Start protected connection and certificate extraction for secret-safe failure handling.
    try:
        # Open one bounded TCP connection to the canonical HTTPS service.
        with socket.create_connection((host, 443), timeout=timeout) as raw_socket:
            # Verify the certificate chain and canonical hostname during the TLS handshake.
            with context.wrap_socket(raw_socket, server_hostname=host) as tls_socket:
                # Read the verified peer certificate metadata in memory only.
                certificate = tls_socket.getpeercert()
        # Convert the standardized certificate expiration string to epoch seconds.
        expiry_epoch = ssl.cert_time_to_seconds(certificate["notAfter"])
    # Collapse DNS, socket, TLS, missing-field, and conversion failures into one safe category.
    except Exception as exc:
        # Suppress host, address, issuer, subject, and certificate text.
        raise EdgeGateError("certificate_unavailable") from exc
    # Return only whole remaining days for sanitized threshold evidence.
    return int((expiry_epoch - now_epoch) // 86400)


# Run the three reviewed read-only probes and return a fixed sanitized evidence shape.
def observe(policy, monitor_header, fetcher=_fetch_json, certificate_checker=_certificate_days_remaining, now_epoch=None):
    # Refuse missing, malformed, or unbounded monitor material before any network call.
    _require(isinstance(monitor_header, tuple) and len(monitor_header) == 2 and monitor_header[0] in {"Authorization", "Cookie"} and isinstance(monitor_header[1], str) and "\r" not in monitor_header[1] and "\n" not in monitor_header[1] and len(monitor_header[1]) <= 4096, "credential_missing")
    # Use the caller clock for deterministic tests or the current epoch for normal operation.
    observed_epoch = time.time() if now_epoch is None else now_epoch
    # Extract only the already validated monitoring and origin values.
    monitoring = policy["monitoring"]
    # Track fixed probe names and boolean results without storing response content.
    checks = {}
    # Execute only the exact three GET probes in their reviewed order.
    for probe in monitoring["probes"]:
        # Attach the secret monitor header only when the declarative probe requires authentication.
        probe_monitor_header = monitor_header if probe["authenticated"] else None
        # Fetch a bounded response from the exact same-origin path.
        status, headers, payload = fetcher(policy["canonical_origin"] + probe["path"], probe_monitor_header, monitoring["timeout_seconds"], monitoring["maximum_body_bytes"])
        # Require the exact reviewed HTTP status without accepting redirects.
        _require(status == probe["expected_status"], "endpoint_status")
        # Validate and unwrap the exact standard success envelope before inspecting operational fields.
        data = validated_success_data(payload)
        # Require every expected JSON field and value while ignoring approved extra sanitized telemetry.
        for key, expected_value in probe["expected_json"].items():
            # Fail closed if a health, storage, or Admin readiness signal differs.
            _require(data.get(key) == expected_value, "endpoint_body")
        # Require every #203 security header on each successful edge response.
        for header_name, expected_value in monitoring["required_response_headers"].items():
            # Read the response header in memory without copying it to evidence.
            observed_value = headers.get(header_name)
            # Require non-empty CSP while allowing its reviewed content to evolve under #203 governance.
            if expected_value == "present":
                # Reject missing or blank content-security policy headers.
                _require(isinstance(observed_value, str) and bool(observed_value.strip()), "endpoint_headers")
            # Require exact values for every other stable header.
            else:
                # Reject missing, duplicated, or altered stable security header values.
                _require(observed_value == expected_value, "endpoint_headers")
        # Record only the fixed policy-owned probe name and pass state.
        checks[probe["name"]] = True
    # Verify the canonical certificate and retain only whole remaining days.
    certificate_days = certificate_checker(policy["canonical_host"], monitoring["timeout_seconds"], observed_epoch)
    # Fail before emitting success when the certificate has crossed the reviewed alert threshold.
    _require(certificate_days >= monitoring["minimum_certificate_days_remaining"], "certificate_age")
    # Format one UTC second-resolution timestamp without exposing host or provider identifiers.
    observed_at = datetime.datetime.fromtimestamp(observed_epoch, datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    # Return one fixed allowlisted record that cannot contain paths, URLs, headers, bodies, or secrets.
    return {"schema": "casino.edge-observation.v1", "status": "pass", "observed_at": observed_at, "certificate_days_remaining": certificate_days, "checks": checks}


# Print one canonical JSON line for journal ingestion without logging command inputs.
def _emit(record):
    # Serialize fixed-key evidence deterministically for stable tests and monitoring.
    print(json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)


# Parse the command, run only validation or observation, and return a process status.
def main(argv=None, environ=None):
    # Create the two-command interface without any activation, rendering, or mutation action.
    parser = argparse.ArgumentParser(description="Validate or observe the Casino restricted-preview edge policy.")
    # Require an explicit read-only command.
    parser.add_argument("command", choices=("validate", "observe"))
    # Accept a repository policy path while defaulting to the reviewed immutable location.
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    # Parse caller arguments without accepting arbitrary provider or shell parameters.
    args = parser.parse_args(argv)
    # Start fixed-category error handling so CLI output remains secret-safe.
    try:
        # Validate the complete policy and every inert template before any observation.
        policy = validate_policy(args.policy, ROOT)
        # Return listener-free static validation evidence when requested.
        if args.command == "validate":
            # Emit only fixed check class names rather than filesystem or configuration values.
            _emit({"schema": "casino.edge-validation.v1", "status": "pass", "checks": ["access", "acme", "monitoring", "proxy", "rollback", "templates", "upstream"]})
            # Exit successfully after the non-mutating static pass.
            return 0
        # Read the monitor credential from the explicit runner environment or inherited service environment.
        monitor_header = _monitor_header_from_environment(environ)
        # Run the reviewed read-only observation and emit its sanitized result.
        _emit(observe(policy, monitor_header))
        # Exit successfully only after every live read-only gate passes.
        return 0
    # Convert every expected policy and observation failure to one fixed JSON record.
    except EdgeGateError as exc:
        # Emit no raw exception, path, URL, identifier, header, body, or secret.
        _emit({"schema": "casino.edge-gate-error.v1", "status": "fail", "reason": exc.code})
        # Return a stable nonzero status for systemd and cutover orchestration.
        return 1


# Run the CLI only when invoked directly rather than imported by focused tests.
if __name__ == "__main__":
    # Propagate the stable gate result to the caller.
    raise SystemExit(main())
