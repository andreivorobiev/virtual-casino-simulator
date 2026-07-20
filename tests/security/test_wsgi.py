"""Subprocess wrapper for listener-free restricted-preview WSGI hostile-client proof."""

# Import environment support for isolated child configuration.
import os
# Import portable paths for exact checkout execution.
import pathlib
# Import subprocess execution for fresh production imports.
import subprocess
# Import the active interpreter used by central discovery.
import sys
# Import disposable external data and log roots.
import tempfile
# Import unittest assertions.
import unittest

# Resolve the exact checkout root.
ROOT = pathlib.Path(__file__).resolve().parents[2]


# Validate production WSGI request security without opening a listener.
class RestrictedPreviewWSGITests(unittest.TestCase):
    # Run the complete hostile-client matrix in a fresh isolated process.
    def test_listener_free_wsgi_security_matrix(self):
        # Allocate external mutable roots outside the repository.
        with tempfile.TemporaryDirectory(prefix="casino-security-wsgi-") as temporary:
            # Resolve the disposable root once.
            root = pathlib.Path(temporary)
            # Copy parent process settings needed by the active interpreter.
            environment = os.environ.copy()
            # Select the production adapter path.
            environment["CASINO_DEPLOYMENT_MODE"] = "production"
            # Keep all state in the disposable root.
            environment["CASINO_DATA_DIR"] = str(root / "state")
            # Keep all logs in the disposable root for the redaction scan.
            environment["CASINO_LOG_DIR"] = str(root / "logs")
            # Use provider-neutral JSON for this repository-only test.
            environment["CASINO_STORAGE_PROVIDER"] = "json"
            # Supply a synthetic reserved-domain Admin identity.
            environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = "preview-admin@example.invalid"
            # Supply a synthetic external token-digest key for this isolated public-startup probe.
            environment["CASINO_TOKEN_DIGEST_KEY"] = "preview-token-digest-key-material-2026-only"
            # Supply a synthetic test-only credential that the probe never prints.
            environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = "synthetic-preview-password"
            # Use a synthetic reserved-domain canonical origin.
            environment["CASINO_CANONICAL_ORIGIN"] = "https://casino.example.invalid"
            # Trust exactly one direct IPv4 loopback proxy address.
            environment["CASINO_TRUSTED_PROXY"] = "127.0.0.1"
            # Enable only the released restricted-preview stage.
            environment["CASINO_RESTRICTED_PREVIEW"] = "1"
            # Select the strongest same-origin cookie policy.
            environment["CASINO_SESSION_SAMESITE"] = "Strict"
            # Exercise the focused 4 KiB request body bound.
            environment["CASINO_MAX_BODY_BYTES"] = "4096"
            # Keep the hostile matrix below a generous per-client request limit.
            environment["CASINO_RATE_LIMIT_REQUESTS"] = "1000"
            # Use the reviewed minute window.
            environment["CASINO_RATE_LIMIT_WINDOW_SECONDS"] = "60"
            # Prevent test imports from writing bytecode into the checkout.
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            # Execute the direct probe with the active interpreter.
            result = subprocess.run([sys.executable, "tests/security/security_wsgi_probe.py"], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60)
        # Require every hostile-client and compatible-flow assertion to pass.
        self.assertEqual(result.returncode, 0, msg=result.stderr[-2000:])

    # Require missing security configuration to fail before service readiness.
    def test_production_import_requires_canonical_origin(self):
        # Allocate external mutable roots for the startup-only child.
        with tempfile.TemporaryDirectory(prefix="casino-security-config-") as temporary:
            # Resolve the disposable root once.
            root = pathlib.Path(temporary)
            # Build an otherwise valid production environment.
            environment = os.environ.copy()
            # Select the production adapter.
            environment.update({"CASINO_DEPLOYMENT_MODE": "production", "CASINO_DATA_DIR": str(root / "state"), "CASINO_LOG_DIR": str(root / "logs"), "CASINO_STORAGE_PROVIDER": "json", "CASINO_BOOTSTRAP_ADMIN_EMAIL": "config-admin@example.invalid", "CASINO_BOOTSTRAP_ADMIN_PASSWORD": "synthetic-config-password", "CASINO_TOKEN_DIGEST_KEY": "config-token-digest-key-material-2026-only", "CASINO_TRUSTED_PROXY": "127.0.0.1", "CASINO_RESTRICTED_PREVIEW": "1", "PYTHONDONTWRITEBYTECODE": "1"})
            # Import the production adapter without opening a listener.
            result = subprocess.run([sys.executable, "-c", "import casino.wsgi"], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=20)
        # Require fail-closed startup.
        self.assertNotEqual(result.returncode, 0)
        # Require only the public missing setting name to remain actionable.
        self.assertIn("CASINO_CANONICAL_ORIGIN", result.stderr)
        # Require the synthetic credential not to appear in diagnostics.
        self.assertNotIn("synthetic-config-password", result.stderr)


# Run this focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
