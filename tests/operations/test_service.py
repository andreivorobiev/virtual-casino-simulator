"""Focused probe and service tests mapped to issue #72 Operations acceptance."""

# Import JSON serialization so secret-leak assertions inspect the complete public payload.
import json
# Import temporary directories so JSON probes never touch repository data.
import tempfile
# Import the standard unit-test runner for dependency-free focused checks.
import unittest
# Import patching support for deterministic permission failures.
from unittest.mock import patch
# Import paths for isolated provider documents.
from pathlib import Path

# Import the canonical packaged release only for exact source-of-truth comparison.
from casino.module_versions import APP_VERSION
# Import the concrete JSON provider for one temporary end-to-end readiness check.
from casino.core.storage import JsonStorageProvider
# Import the isolated probe helpers under test.
from casino.operations import probes
# Import the isolated status service under test.
from casino.operations.service import OperationsProbeService

# Map this focused suite to existing cross-cutting requirements pending permanent OPS allocation by #77.
REQUIREMENT_IDS = ("CORE-011", "CORE-012", "STORAGE-001", "STORAGE-003", "MYSQL-001", "TEST-038")


# Supply deterministic timestamps without accessing the system clock.
class SequenceClock:
    # Store the ordered timestamps that each probe call should consume.
    def __init__(self, *values):
        # Preserve the immutable test sequence as a mutable queue.
        self.values = list(values)

    # Return the next deterministic timestamp.
    def __call__(self):
        # Remove and return the first scheduled value.
        return self.values.pop(0)


# Model the existing JSON provider through only its public readiness seam.
class FakeJsonProvider:
    # Publish the supported provider name used by sanitized diagnostics.
    name = "json"

    # Track readiness calls and optionally simulate a sensitive provider failure.
    def __init__(self, data_dir):
        # Store an isolated temporary persistence root.
        self.data_dir = Path(data_dir)
        # Create the root so readiness can distinguish it from a missing store.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Store the primary player document path used by the concrete provider.
        self._players_path = self.data_dir / "players.json"
        # Write a minimal valid bootstrapped document without using repository data.
        self._players_path.write_text('{"schema_version":"test","players":[]}', encoding="utf-8")
        # Start with a healthy provider.
        self.fail = False
        # Count checks so liveness can prove it never touched storage.
        self.calls = 0

    # Return the primary JSON player document path.
    def players_path(self):
        # Record each concrete persistence check.
        self.calls += 1
        # Simulate provider metadata failure containing every forbidden diagnostic category.
        if self.fail:
            # Raise raw sensitive text that must never appear in a service result.
            raise RuntimeError("password=hunter2 token=abc C:\\private\\casino\\data")
        # Return the isolated primary store path.
        return self._players_path


# Model one DB-API cursor for a fresh MySQL connectivity check.
class FakeCursor:
    # Initialize query and cleanup observations.
    def __init__(self):
        # Start without an executed query.
        self.query = None
        # Start with an open cursor.
        self.closed = False

    # Capture the constant connectivity query.
    def execute(self, query):
        # Store the exact statement for a non-data-access assertion.
        self.query = query

    # Return the expected constant row.
    def fetchone(self):
        # Model a successful SELECT 1 result.
        return (1,)

    # Record deterministic cursor cleanup.
    def close(self):
        # Mark the cursor closed.
        self.closed = True


# Model one DB-API connection created for a MySQL heartbeat.
class FakeConnection:
    # Initialize one owned cursor and cleanup flag.
    def __init__(self):
        # Create the cursor returned by this connection.
        self.probe_cursor = FakeCursor()
        # Start with an open connection.
        self.closed = False

    # Return the owned cursor through the normal DB-API method.
    def cursor(self):
        # Expose the deterministic cursor to the probe.
        return self.probe_cursor

    # Record deterministic connection cleanup.
    def close(self):
        # Mark the connection closed.
        self.closed = True


# Model the configured MySQL provider without any credentials or network access.
class FakeMySQLProvider:
    # Publish the supported provider name used by sanitized diagnostics.
    name = "mysql"

    # Track every fresh connection created by monitoring.
    def __init__(self):
        # Start with no connectivity checks.
        self.connections = []
        # Retain connection options so the probe timeout remains testable.
        self.connection_options = []

    # Create a fresh fake connection for each check.
    def connect(self, **options):
        # Record bounded connector options without opening a real network connection.
        self.connection_options.append(options)
        # Build one isolated DB-API connection.
        connection = FakeConnection()
        # Retain it for query and cleanup assertions.
        self.connections.append(connection)
        # Return it to the probe.
        return connection


# Verify canonical build identity, sanitized dependencies, and heartbeat state.
class OperationsProbeServiceTests(unittest.TestCase):
    # Build a valid JSON provider rooted in an automatically cleaned temporary directory.
    def json_provider(self):
        # Create an isolated directory for this test.
        temporary_directory = tempfile.TemporaryDirectory()
        # Register deterministic cleanup with unittest.
        self.addCleanup(temporary_directory.cleanup)
        # Return the provider that owns the isolated directory.
        return FakeJsonProvider(temporary_directory.name)

    # Confirm liveness is storage-independent and consumes the merged canonical app version.
    def test_liveness_never_touches_storage_and_uses_canonical_version(self):
        # Create a factory that would fail the test if liveness constructed storage.
        def forbidden_provider_factory():
            # Raise an assertion because no dependency should be reached.
            raise AssertionError("liveness touched storage")
        # Build the service with deterministic time and valid mixed-case provenance.
        service = OperationsProbeService(provider_factory=forbidden_provider_factory, clock=lambda: "2026-07-14T10:00:00.000Z", build_sha_source=lambda: "ABCDEF1234567")
        # Execute the process-only liveness probe.
        payload = service.liveness()
        # Verify anonymous liveness contains no build, timestamp, or dependency detail.
        self.assertEqual({"status": "live"}, payload)

    # Confirm malformed or failing SHA sources become unavailable without degrading liveness.
    def test_build_sha_is_strictly_sanitized_and_optional(self):
        # Verify a path-like value cannot be reflected into public metadata.
        self.assertIsNone(probes.environment_build_sha({probes.BUILD_SHA_ENV: "C:\\private\\build"}))
        # Build a source that fails with raw secret text.
        def failing_source():
            # Raise a value that must be swallowed by build metadata handling.
            raise RuntimeError("token=secret")
        # Verify the fixed unavailable result contains only canonical version metadata.
        self.assertEqual({"app_version": APP_VERSION, "sha": None}, probes.build_metadata(failing_source))

    # Confirm a healthy JSON readiness check advances the process heartbeat.
    def test_json_readiness_reports_live_and_records_success(self):
        # Create an isolated provider that never touches repository data.
        provider = self.json_provider()
        # Build one deterministic readiness service.
        service = OperationsProbeService(provider_factory=lambda: provider, clock=lambda: "2026-07-14T10:01:00.000Z", build_sha_source=lambda: None)
        # Run the full dependency check.
        payload = service.readiness()
        # Verify healthy monitoring dimensions and provider disclosure.
        self.assertEqual(("live", True, "json", 1), (payload["status"], payload["ready"], payload["storage_provider"], provider.calls))
        # Verify the successful dependency timestamp is immediately visible.
        self.assertEqual(payload["checked_at"], payload["last_successful_heartbeat_at"])
        # Verify no degradation reasons appear on success.
        self.assertEqual([], payload["reasons"])

    # Confirm the concrete JSON provider passes through a temporary bootstrapped store.
    def test_concrete_json_provider_is_ready_in_temporary_storage(self):
        # Create an isolated directory for the concrete provider.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Build the production JSON provider against only the temporary data root.
            provider = JsonStorageProvider(Path(temporary_directory) / "data")
            # Bootstrap provider directories without touching repository data.
            provider.ensure_ready()
            # Persist a minimal valid primary player document through the isolated JSON writer.
            provider._save_players_document({"players": []})
            # Run the Operations readiness probe against the concrete provider.
            result = probes.probe_storage(lambda: provider)
        # Verify the real local provider reports healthy outside the temporary context.
        self.assertEqual({"status": "pass", "provider": "json"}, result)

    # Confirm MySQL readiness performs a fresh constant query and releases resources.
    def test_mysql_readiness_uses_select_one_and_closes_resources(self):
        # Create a connector-free MySQL provider double.
        provider = FakeMySQLProvider()
        # Build the service with deterministic metadata.
        service = OperationsProbeService(provider_factory=lambda: provider, clock=lambda: "2026-07-14T10:02:00.000Z", build_sha_source=lambda: None)
        # Run a live database connectivity check.
        payload = service.heartbeat()
        # Read the one connection created for this heartbeat.
        connection = provider.connections[0]
        # Verify the query touched no casino rows and both resources were closed.
        self.assertEqual(("SELECT 1", True, True), (connection.probe_cursor.query, connection.probe_cursor.closed, connection.closed))
        # Verify the connection attempt uses the approved bounded timeout.
        self.assertEqual([{"connection_timeout": probes.MYSQL_PROBE_TIMEOUT_SECONDS}], provider.connection_options)
        # Verify the public status identifies only the allowlisted provider.
        self.assertEqual(("mysql", True), (payload["storage_provider"], payload["ready"]))

    # Confirm degraded responses retain the previous success and never expose raw provider errors.
    def test_degraded_storage_is_sanitized_and_retains_last_success(self):
        # Create a provider that can transition from healthy to unavailable.
        provider = self.json_provider()
        # Supply one timestamp for success and one for the later failure.
        clock = SequenceClock("2026-07-14T10:03:00.000Z", "2026-07-14T10:04:00.000Z")
        # Build the shared process service.
        service = OperationsProbeService(provider_factory=lambda: provider, clock=clock, build_sha_source=lambda: None)
        # Establish the last successful heartbeat.
        first = service.heartbeat()
        # Make the same provider fail with sensitive raw text.
        provider.fail = True
        # Run a later failed heartbeat.
        second = service.heartbeat()
        # Verify the process is degraded and the prior success remains durable.
        self.assertEqual(("degraded", False, first["checked_at"]), (second["status"], second["ready"], second["last_successful_heartbeat_at"]))
        # Verify only the fixed storage reason is published.
        self.assertEqual([{"component": "storage", "code": "storage_unavailable"}], second["reasons"])
        # Serialize the full result before checking every injected sensitive fragment.
        serialized = json.dumps(second)
        # Verify the raw password, token, and internal path never escaped.
        self.assertNotIn("hunter2", serialized)
        # Verify the raw token never escaped.
        self.assertNotIn("token=abc", serialized)
        # Verify the internal path never escaped.
        self.assertNotIn("private", serialized)

    # Confirm successful timestamps never move backward when checks complete out of order.
    def test_last_successful_heartbeat_is_monotonic(self):
        # Create one always-ready provider.
        provider = self.json_provider()
        # Deliberately return a later timestamp before an earlier timestamp.
        clock = SequenceClock("2026-07-14T10:06:00.000Z", "2026-07-14T10:05:00.000Z")
        # Build the process service around the out-of-order clock.
        service = OperationsProbeService(provider_factory=lambda: provider, clock=clock, build_sha_source=lambda: None)
        # Record the later successful heartbeat first.
        first = service.readiness()
        # Complete an earlier-timestamped success afterward.
        second = service.readiness()
        # Verify the durable last-success timestamp did not regress.
        self.assertEqual(first["checked_at"], second["last_successful_heartbeat_at"])

    # Confirm the success timestamp is captured only after persistence checks complete.
    def test_success_timestamp_records_probe_completion(self):
        # Create one isolated ready provider with an observable path-check counter.
        provider = self.json_provider()
        # Define a clock that fails unless the storage probe already completed.
        def completion_clock():
            # Verify the provider path was resolved before time was captured.
            self.assertEqual(1, provider.calls)
            # Return the deterministic completion timestamp.
            return "2026-07-14T10:07:00.000Z"
        # Run readiness with the completion-aware clock.
        payload = OperationsProbeService(provider_factory=lambda: provider, clock=completion_clock, build_sha_source=lambda: None).readiness()
        # Verify both checked and last-success fields use completion time.
        self.assertEqual(("2026-07-14T10:07:00.000Z", "2026-07-14T10:07:00.000Z"), (payload["checked_at"], payload["last_successful_heartbeat_at"]))

    # Confirm unreadable or corrupt JSON persistence cannot report a false healthy state.
    def test_json_readiness_rejects_permission_and_corruption_failures(self):
        # Create one valid isolated provider for the permission boundary.
        permission_provider = self.json_provider()
        # Simulate a root that fails the concrete read/write access check.
        with patch("casino.operations.probes.os.access", return_value=False):
            # Run the provider probe without changing real filesystem permissions.
            permission_result = probes.probe_storage(lambda: permission_provider)
        # Verify the permission failure becomes one fixed storage reason.
        self.assertEqual({"status": "fail", "provider": "json", "reason_code": "storage_unavailable"}, permission_result)
        # Create a second isolated provider for corrupt-document coverage.
        corrupt_provider = self.json_provider()
        # Replace only its temporary player document with malformed JSON.
        corrupt_provider._players_path.write_text("{not-json", encoding="utf-8")
        # Run the read-only parser boundary.
        corruption_result = probes.probe_storage(lambda: corrupt_provider)
        # Verify corruption produces the same safe public result.
        self.assertEqual({"status": "fail", "provider": "json", "reason_code": "storage_unavailable"}, corruption_result)

    # Confirm unsupported provider identity is allowlisted and degraded safely.
    def test_unsupported_provider_name_is_not_reflected(self):
        # Create a provider whose name contains a forbidden connection string.
        provider = type("UnsafeProvider", (), {"name": "mysql://user:password@internal/database"})()
        # Run the standalone storage probe against the unsafe provider.
        result = probes.probe_storage(lambda: provider)
        # Verify only the stable unknown identifier and reason code remain.
        self.assertEqual({"status": "fail", "provider": "unknown", "reason_code": "storage_provider_unsupported"}, result)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
