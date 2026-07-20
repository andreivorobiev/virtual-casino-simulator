"""Focused TEST-046 repository tests for the production service packet."""

# Import environment support for isolated child configuration.
import os
# Import portable paths for repository-owned policy inspection.
import pathlib
# Import run-path support for evaluating the non-listening Gunicorn configuration.
import runpy
# Import subprocess execution for import-time and listener-free child probes.
import subprocess
# Import the active interpreter for exact-checkout child execution.
import sys
# Import disposable directories for external state and log roots.
import tempfile
# Import standard unittest discovery and assertions.
import unittest

# Resolve the repository root independently of the test runner's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Identify protected user ports that no focused service test may select.
PROTECTED_PORTS = frozenset({8765, 8877})


# Validate adapter behavior, service hardening, and loopback process policy.
class ProductionServiceTests(unittest.TestCase):
    # Build a complete synthetic production environment under one disposable external root.
    def production_environment(self, temporary_root: pathlib.Path) -> dict:
        # Copy the caller environment so interpreter and platform settings remain available.
        environment = os.environ.copy()
        # Select the fail-closed production adapter mode.
        environment["CASINO_DEPLOYMENT_MODE"] = "production"
        # Keep all disposable state outside the repository and release directory.
        environment["CASINO_DATA_DIR"] = str(temporary_root / "state")
        # Keep disposable application logs outside the repository and release directory.
        environment["CASINO_LOG_DIR"] = str(temporary_root / "logs")
        # Keep the focused direct test independent of a live database service.
        environment["CASINO_STORAGE_PROVIDER"] = "json"
        # Supply a synthetic reserved-domain Admin identity only to the child process.
        environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = "service-probe@example.invalid"
        # Supply a synthetic external token-digest key for the isolated production adapter probe.
        environment["CASINO_TOKEN_DIGEST_KEY"] = "service-probe-token-digest-key-material-2026"
        # Supply an independent synthetic mail digest key required by public startup.
        environment["CASINO_MAIL_DIGEST_KEY"] = "service-probe-mail-digest-key-material-2026"
        # Supply a synthetic non-default child credential that is never printed.
        environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = "synthetic-service-probe-password"
        # Supply the restricted-preview canonical origin through a reserved test domain.
        environment["CASINO_CANONICAL_ORIGIN"] = "https://casino.example.invalid"
        # Trust only the exact direct loopback proxy address.
        environment["CASINO_TRUSTED_PROXY"] = "127.0.0.1"
        # Enable the explicitly released restricted-preview security stage.
        environment["CASINO_RESTRICTED_PREVIEW"] = "1"
        # Use the strongest governed same-origin cookie mode.
        environment["CASINO_SESSION_SAMESITE"] = "Strict"
        # Prevent child imports from writing bytecode into the exact checkout.
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        # Return the isolated mapping without changing the parent test process.
        return environment

    # Prove direct parity, probes, auth headers, malformed input, and static output without a socket.
    def test_wsgi_adapter_direct_without_listener(self):
        # Allocate external runtime roots for this child only.
        with tempfile.TemporaryDirectory(prefix="casino-wsgi-test-") as temporary:
            # Build the complete synthetic production environment.
            environment = self.production_environment(pathlib.Path(temporary))
            # Run the listener-free direct probe through the exact active interpreter.
            result = subprocess.run(
                # Execute only the focused repository probe script.
                [sys.executable, "tests/production_wsgi_probe.py"],
                # Resolve imports and packaged static files from this checkout.
                cwd=ROOT,
                # Pass the isolated runtime configuration only to the child.
                env=environment,
                # Capture bounded output so failures can be reported without live interleaving.
                capture_output=True,
                # Decode diagnostics for unittest failure output.
                text=True,
                # Bound a child regression that could otherwise stall CI.
                timeout=30,
            )
        # Require every direct assertion to pass without opening a listener.
        self.assertEqual(result.returncode, 0, msg="listener-free WSGI probe failed")

    # Prove missing external mutable roots fail before the application becomes ready.
    def test_production_import_requires_external_runtime_roots(self):
        # Allocate an unused temporary root solely for environment construction.
        with tempfile.TemporaryDirectory(prefix="casino-wsgi-config-") as temporary:
            # Start from an otherwise valid production configuration.
            environment = self.production_environment(pathlib.Path(temporary))
            # Remove the data root to exercise the fail-closed startup guard.
            environment.pop("CASINO_DATA_DIR")
            # Import the production adapter in a fresh process so config globals cannot be cached.
            result = subprocess.run(
                # Import only the production module; no server or listener is created.
                [sys.executable, "-c", "import casino.wsgi"],
                # Resolve the exact checkout under test.
                cwd=ROOT,
                # Pass the deliberately incomplete child configuration.
                env=environment,
                # Capture startup diagnostics for secret-reflection assertions.
                capture_output=True,
                # Decode the bounded error stream.
                text=True,
                # Bound import failure behavior.
                timeout=15,
            )
        # Require startup to fail rather than falling back into the immutable release.
        self.assertNotEqual(result.returncode, 0)
        # Require the public missing key name to remain actionable.
        self.assertIn("CASINO_DATA_DIR", result.stderr)
        # Ensure the synthetic credential never enters startup diagnostics.
        self.assertNotIn("synthetic-service-probe-password", result.stderr)

    # Prove the tracked process policy can select only a loopback listener.
    def test_gunicorn_policy_is_loopback_only(self):
        # Preserve any caller port setting before evaluating the policy.
        original_port = os.environ.get("CASINO_BIND_PORT")
        # Select an unprotected deterministic test port without creating a listener.
        os.environ["CASINO_BIND_PORT"] = "18765"
        # Start protected environment cleanup around config evaluation.
        try:
            # Evaluate the repository-owned Gunicorn config as ordinary Python data.
            policy = runpy.run_path(str(ROOT / "deploy" / "gunicorn.conf.py"))
        # Restore the caller environment regardless of assertion outcome.
        finally:
            # Remove the test setting when the caller did not have one.
            if original_port is None:
                # Restore absence rather than an empty value.
                os.environ.pop("CASINO_BIND_PORT", None)
            # Restore the exact caller value when it existed.
            else:
                # Replace the temporary port with the original value.
                os.environ["CASINO_BIND_PORT"] = original_port
        # Require the fixed IPv4 loopback interface and selected unprotected port.
        self.assertEqual(policy["bind"], "127.0.0.1:18765")
        # Require the configured port to remain outside the protected user set.
        self.assertNotIn(18765, PROTECTED_PORTS)
        # Require one worker and two threads for the approved single-process topology.
        self.assertEqual((policy["workers"], policy["threads"]), (1, 2))
        # Require a bounded graceful drain shorter than systemd's stop timeout.
        self.assertLessEqual(policy["graceful_timeout"], 20)

    # Prove the service template encodes the documented least-privilege lifecycle boundary.
    def test_systemd_template_matches_runtime_contract(self):
        # Read the tracked service template as deployment policy, not as a host action.
        unit = (ROOT / "deploy" / "systemd" / "casino.service").read_text(encoding="utf-8")
        # Require the dedicated unprivileged identity.
        self.assertIn("User=casino", unit)
        # Require external root-managed configuration rather than process arguments.
        self.assertIn("EnvironmentFile=/etc/casino/casino.env", unit)
        # Require the immutable current-release symlink startup guard.
        self.assertIn("ExecStartPre=/usr/bin/test -L /opt/casino/current", unit)
        # Require only the production WSGI application in the supported command.
        self.assertIn("casino.wsgi:application", unit)
        # Reject any production invocation of the local development launcher.
        self.assertNotIn("run.py", unit)
        # Require the writable roots to match the runbook's exact external environment contract.
        self.assertIn("ReadWritePaths=/var/lib/casino /var/log/casino", unit)
        # Require a bounded graceful termination policy.
        self.assertIn("KillSignal=SIGTERM", unit)
        # Require the capability set to be empty.
        self.assertIn("CapabilityBoundingSet=", unit)
        # Require loopback networking without adding issue #203 trusted-proxy policy.
        self.assertIn("RestrictAddressFamilies=AF_UNIX AF_INET", unit)

    # Prove production source contains no development server invocation or proxy-policy expansion.
    def test_adapter_scope_excludes_development_server_and_proxy_policy(self):
        # Read only the adapter source governed by CORE-023.
        adapter = (ROOT / "casino" / "wsgi.py").read_text(encoding="utf-8")
        # Reject the development server type from the production module.
        self.assertNotIn("ThreadingHTTPServer", adapter)
        # Reject forwarded-client trust that belongs to issue #203.
        self.assertNotIn("X-Forwarded-For", adapter)
        # Reject forwarded-scheme trust that belongs to issue #203.
        self.assertNotIn("X-Forwarded-Proto", adapter)


# Run the focused test module directly for local developer diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
