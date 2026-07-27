"""Listener-free tests for the root-managed monitor bearer/digest validator."""

# Import secret hashing for synthetic expected configuration.
import hashlib
# Import in-memory streams for secret-safe command output assertions.
import io
# Import permission-bit inspection for atomic repair evidence.
import stat
# Import temporary directories for isolated root-managed file fixtures.
import tempfile
# Import unittest for dependency-free operator-tool evidence.
import unittest
# Import redirected standard streams for command-boundary assertions.
from contextlib import redirect_stderr, redirect_stdout
# Import paths for synthetic environment files.
from pathlib import Path

# Import the tracked validator under test.
from scripts import validate_monitor_config
# Import the tracked non-shell observer runner under test.
from scripts import run_edge_monitor


# Prove monitor validation and repair never require a listener or real secret.
class MonitorConfigTests(unittest.TestCase):
    # Create isolated monitor and application environment files for every test.
    def setUp(self):
        # Own the temporary directory for the complete test lifetime.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve its path once for concise fixtures.
        self.root = Path(self.temporary.name)
        # Use a strong synthetic token that can never authenticate production.
        self.token = "synthetic-monitor-token-for-listener-free-tests"
        # Derive its canonical application-only digest.
        self.digest = hashlib.sha256(self.token.encode("utf-8")).hexdigest()
        # Point at the monitor-only root-managed fixture.
        self.monitor = self.root / "edge-monitor.env"
        # Point at the application-only root-managed fixture.
        self.application = self.root / "casino.env"
        # Write the raw synthetic bearer only to the monitor fixture.
        self.monitor.write_text(f"CASINO_EDGE_MONITOR_AUTHORIZATION=Bearer {self.token}\n", encoding="utf-8", newline="\n")
        # Write the matching digest and an unrelated application setting.
        self.application.write_text(f"CASINO_MODE=production\nCASINO_EDGE_MONITOR_TOKEN_SHA256={self.digest}\n", encoding="utf-8", newline="\n")

    # Remove all synthetic secret fixtures after every assertion.
    def tearDown(self):
        # Delegate cleanup to TemporaryDirectory.
        self.temporary.cleanup()

    # Prove a correctly split credential validates.
    def test_matching_pair_passes(self):
        # Exercise the listener-free public validator.
        validate_monitor_config.validate_pair(self.monitor, self.application)

    # Prove the runner preserves the exact Bearer value as one in-memory assignment.
    def test_non_shell_runner_preserves_authorization_value(self):
        # Replace the token with shell-significant bytes that remain inert outside a shell.
        token = "synthetic-monitor-token-$HOME-$(false)-semicolon;"
        # Write the exact scheme and token with the required separating space.
        self.monitor.write_text(f"CASINO_EDGE_MONITOR_AUTHORIZATION=Bearer {token}\n", encoding="utf-8", newline="\n")
        # Capture only the observer arguments and explicit environment seam.
        captured = {}

        # Model the edge observer without opening a listener or network connection.
        def capture_gate(argv=None, environ=None):
            # Copy the exact fixed command arguments for assertions.
            captured["argv"] = list(argv or [])
            # Copy the single explicit credential environment without rendering it.
            captured["environ"] = dict(environ or {})
            # Return the production observer's successful process status.
            return 0

        # Run the non-shell handoff against an inert policy path and capture seam.
        result = run_edge_monitor.run_observation(self.monitor, self.root / "policy.json", gate_main=capture_gate)
        # Require the observer status to propagate unchanged.
        self.assertEqual(result, 0)
        # Require the exact fixed read-only observer command.
        self.assertEqual(captured["argv"], ["observe", "--policy", str(self.root / "policy.json")])
        # Require only one exact Authorization assignment, including its scheme separator and inert metacharacters.
        self.assertEqual(captured["environ"], {"CASINO_EDGE_MONITOR_AUTHORIZATION": f"Bearer {token}"})

    # Prove runner parse failures never render the protected assignment.
    def test_non_shell_runner_failure_is_secret_safe(self):
        # Persist a malformed value containing an extra space after a synthetic sentinel.
        sentinel = "synthetic-secret-sentinel"
        # Write a value that the strict bearer grammar must reject before observation.
        self.monitor.write_text(f"CASINO_EDGE_MONITOR_AUTHORIZATION=Bearer {sentinel} extra\n", encoding="utf-8", newline="\n")
        # Capture the fixed command error boundary.
        output = io.StringIO()
        # Run the public command without any network-capable observer call.
        with redirect_stdout(output), redirect_stderr(output):
            # Invoke the same two fixed paths used by production.
            result = run_edge_monitor.main(["--monitor-env", str(self.monitor), "--policy", str(self.root / "policy.json")])
        # Require a fail-closed process result.
        self.assertEqual(result, 1)
        # Read the bounded combined command output.
        message = output.getvalue()
        # Reject the raw protected sentinel.
        self.assertNotIn(sentinel, message)
        # Require one fixed secret-safe failure category.
        self.assertIn("edge monitor configuration invalid", message)

    # Prove a mismatched digest blocks cutover.
    def test_mismatch_fails_closed(self):
        # Replace the digest with another canonical but incorrect value.
        self.application.write_text(f"CASINO_EDGE_MONITOR_TOKEN_SHA256={'0' * 64}\n", encoding="utf-8", newline="\n")
        # Require constant-time pair validation to reject it.
        with self.assertRaises(ValueError):
            # Exercise the exact public validator.
            validate_monitor_config.validate_pair(self.monitor, self.application)

    # Prove command failures never print the raw token or either digest.
    def test_command_failure_output_is_secret_safe(self):
        # Replace the digest with another canonical but incorrect value.
        wrong_digest = "0" * 64
        # Persist the mismatch in the application-only fixture.
        self.application.write_text(f"CASINO_EDGE_MONITOR_TOKEN_SHA256={wrong_digest}\n", encoding="utf-8", newline="\n")
        # Capture both process streams in memory.
        output = io.StringIO()
        # Run the public command boundary with redirected streams.
        with redirect_stdout(output), redirect_stderr(output):
            # Execute read-only validation against the isolated files.
            result = validate_monitor_config.main(["check", "--monitor-env", str(self.monitor), "--application-env", str(self.application)])
        # Require the deployment-blocking exit.
        self.assertEqual(result, 1)
        # Read the bounded combined operator message.
        message = output.getvalue()
        # Reject raw token disclosure.
        self.assertNotIn(self.token, message)
        # Reject configured digest disclosure.
        self.assertNotIn(wrong_digest, message)
        # Reject calculated digest disclosure.
        self.assertNotIn(self.digest, message)
        # Require one stable secret-free failure category.
        self.assertIn("monitor configuration invalid", message)

    # Prove malformed and duplicate protected assignments are rejected.
    def test_duplicate_assignment_fails_closed(self):
        # Add a second protected digest assignment with shell-ambiguous precedence.
        self.application.write_text(
            f"CASINO_EDGE_MONITOR_TOKEN_SHA256={self.digest}\nCASINO_EDGE_MONITOR_TOKEN_SHA256={self.digest}\n",
            encoding="utf-8",
            newline="\n",
        )
        # Require validation to reject the duplicate.
        with self.assertRaises(ValueError):
            # Exercise the exact public validator.
            validate_monitor_config.validate_pair(self.monitor, self.application)

    # Prove explicit repair changes only the digest and preserves permissions.
    def test_repair_is_atomic_and_preserves_unrelated_configuration(self):
        # Start from a canonical but mismatched digest.
        self.application.write_text(
            f"# retained comment\nCASINO_MODE=production\nCASINO_EDGE_MONITOR_TOKEN_SHA256={'0' * 64}\n",
            encoding="utf-8",
            newline="\n",
        )
        # Set restrictive synthetic permissions that repair must retain.
        self.application.chmod(0o640)
        # Capture the exact permission bits before repair.
        previous_mode = stat.S_IMODE(self.application.stat().st_mode)
        # Perform the explicit owner-mode digest repair.
        validate_monitor_config.repair_digest(self.monitor, self.application)
        # Read the repaired application configuration.
        repaired = self.application.read_text(encoding="utf-8")
        # Require unrelated comment and mode settings to remain unchanged.
        self.assertIn("# retained comment\nCASINO_MODE=production\n", repaired)
        # Require exactly one canonical derived digest assignment.
        self.assertEqual(repaired.count(f"CASINO_EDGE_MONITOR_TOKEN_SHA256={self.digest}"), 1)
        # Require restrictive permissions to be preserved.
        self.assertEqual(stat.S_IMODE(self.application.stat().st_mode), previous_mode)
        # Revalidate the installed pair after atomic replacement.
        validate_monitor_config.validate_pair(self.monitor, self.application)

    # Prove a symlink destination cannot redirect explicit repair.
    def test_repair_rejects_symlink_destination(self):
        # Skip only on platforms where test symlinks are unavailable.
        try:
            # Create a separate target that repair must never touch through a symlink.
            target = self.root / "redirected.env"
            # Seed the target with a mismatched digest.
            target.write_text(f"CASINO_EDGE_MONITOR_TOKEN_SHA256={'0' * 64}\n", encoding="utf-8", newline="\n")
            # Replace the normal application fixture with a symlink to the target.
            self.application.unlink()
            # Create the redirect under test.
            self.application.symlink_to(target)
        # Treat operating-system privilege denial as an unavailable platform feature.
        except OSError:
            # Skip without weakening production behavior.
            self.skipTest("symlink creation unavailable")
        # Require repair to reject the redirect.
        with self.assertRaises(ValueError):
            # Exercise the exact public repair helper.
            validate_monitor_config.repair_digest(self.monitor, self.application)
        # Prove the redirect target remains mismatched and untouched.
        self.assertIn("0" * 64, target.read_text(encoding="utf-8"))


# Run focused evidence directly for release validation.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
