"""Focused isolated-router tests for issue #72 Operations endpoint policy."""

# Import JSON serialization for complete degraded-payload leak checks.
import json
# Import temporary directories so API probes never touch repository data.
import tempfile
# Import the standard unit-test runner for dependency-free focused checks.
import unittest
# Import paths for isolated JSON provider documents.
from pathlib import Path

# Import the current standard API error and router used by production handlers.
from casino.errors import CasinoError, NotFoundError
# Import the isolated Operations API registrar.
from casino.operations import api
# Import the isolated service for injected route behavior.
from casino.operations.service import OperationsProbeService
# Import the current router without editing its shared registration call site.
from casino.router import Router


# Provide a healthy JSON dependency without touching filesystem data.
class ReadyProvider:
    # Publish the supported provider name.
    name = "json"

    # Create a valid primary document inside an isolated temporary root.
    def __init__(self, data_dir):
        # Store the temporary root expected by the concrete JSON probe.
        self.data_dir = Path(data_dir)
        # Create the isolated root directory.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Store the primary player document path.
        self._players_path = self.data_dir / "players.json"
        # Write a minimal valid provider document.
        self._players_path.write_text('{"schema_version":"test","players":[]}', encoding="utf-8")

    # Return the primary provider document path.
    def players_path(self):
        # Expose only the isolated file to the readiness probe.
        return self._players_path


# Simulate an injected or buggy service that raises the importable route-policy error itself.
class InjectedNotReadyService:
    # Raise unsafe details from inside the service boundary instead of route-owned policy.
    def liveness(self):
        # Include credential, path, and debug material that the API must discard.
        raise api.OperationsNotReadyError({"secret": "raw-token", "path": "C:\\internal", "request_id": "debug-72"})


# Verify isolated route registration and sanitized error-envelope inputs.
class OperationsApiTests(unittest.TestCase):
    # Build a fresh local router before every test.
    def setUp(self):
        # Create the isolated router with no shared application registrations.
        self.router = Router()
        # Create one temporary persistence root for healthy API probes.
        self.temporary_directory = tempfile.TemporaryDirectory()
        # Register deterministic cleanup after each test.
        self.addCleanup(self.temporary_directory.cleanup)

    # Confirm all three GET routes expose distinct probe semantics through one service.
    def test_register_exposes_liveness_readiness_and_heartbeat(self):
        # Provide deterministic timestamps for the three ordered requests.
        timestamps = iter(("2026-07-14T11:00:00.000Z", "2026-07-14T11:01:00.000Z", "2026-07-14T11:02:00.000Z"))
        # Build a safe service that never touches repository data.
        service = OperationsProbeService(provider_factory=lambda: ReadyProvider(self.temporary_directory.name), clock=lambda: next(timestamps), build_sha_source=lambda: "1234567")
        # Register only the issue #72 Operations routes.
        registered = api.register(self.router, service=service)
        # Dispatch the storage-independent liveness request.
        liveness = self.router.dispatch("GET", "/api/v1/operations/liveness")
        # Dispatch the dependency readiness request.
        readiness = self.router.dispatch("GET", "/api/v1/operations/readiness")
        # Dispatch the monitoring heartbeat request.
        heartbeat = self.router.dispatch("GET", "/api/v1/operations/heartbeat")
        # Verify registration preserves the injected shared service instance.
        self.assertIs(service, registered)
        # Verify each route keeps its contract probe identity.
        self.assertEqual(("liveness", "readiness", "heartbeat"), (liveness["probe"], readiness["probe"], heartbeat["probe"]))
        # Verify readiness-equivalent routes return healthy direct-router data.
        self.assertTrue(readiness["ready"] and heartbeat["ready"])
        # Verify the latest successful heartbeat advances across both dependency routes.
        self.assertEqual(heartbeat["checked_at"], heartbeat["last_successful_heartbeat_at"])

    # Confirm a dependency failure becomes one fixed sanitized 503 CasinoError.
    def test_degraded_readiness_raises_sanitized_503(self):
        # Build a provider factory that fails with credential and path material.
        def failing_provider_factory():
            # Raise raw diagnostics that must be consumed inside the Operations probe.
            raise RuntimeError("mysql://admin:secret@db/internal token=debug-id")
        # Build a service around the failing provider.
        service = OperationsProbeService(provider_factory=failing_provider_factory, clock=lambda: "2026-07-14T11:03:00.000Z", build_sha_source=lambda: None)
        # Register the degraded service in an isolated router.
        api.register(self.router, service=service)
        # Capture the standard error object used by the shared HTTP envelope handler.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch the readiness route that must fail with HTTP 503 policy.
            self.router.dispatch("GET", "/api/v1/operations/readiness")
        # Read the fixed error after the assertion context completes.
        error = raised.exception
        # Verify stable HTTP policy and public error identity.
        self.assertEqual((api.NOT_READY_CODE, api.NOT_READY_MESSAGE, 503), (error.code, error.message, error.status))
        # Serialize all public error details for leakage assertions.
        serialized = json.dumps(error.details)
        # Verify no credential fragment escaped.
        self.assertNotIn("secret", serialized)
        # Verify no internal host or path fragment escaped.
        self.assertNotIn("internal", serialized)
        # Verify no token or debug identifier escaped.
        self.assertNotIn("debug-id", serialized)
        # Verify clients still receive the fixed safe degraded reason.
        self.assertEqual([{"component": "storage", "code": "storage_unavailable"}], error.details["reasons"])

    # Confirm liveness remains available even when readiness dependencies fail.
    def test_liveness_survives_dependency_failure_and_routes_are_get_only(self):
        # Build a provider factory that must not be reached by liveness.
        def failing_provider_factory():
            # Raise if any dependency-aware operation invokes this factory.
            raise RuntimeError("unavailable")
        # Register the service with a storage-independent liveness path.
        api.register(self.router, service=OperationsProbeService(provider_factory=failing_provider_factory, clock=lambda: "2026-07-14T11:04:00.000Z", build_sha_source=lambda: None))
        # Verify the live process response succeeds without provider construction.
        self.assertEqual("live", self.router.dispatch("GET", "/api/v1/operations/liveness")["status"])
        # Verify no mutating method was registered for monitoring paths.
        with self.assertRaises(NotFoundError):
            # Dispatch a forbidden POST shape through the real router matcher.
            self.router.dispatch("POST", "/api/v1/operations/liveness")

    # Confirm an unexpected clock failure is converted before the global raw-error handler.
    def test_unexpected_probe_failure_raises_fixed_sanitized_503(self):
        # Build a clock that raises raw sensitive and debug text.
        def failing_clock():
            # Raise the value that the Operations API boundary must consume.
            raise RuntimeError("password=secret C:\\private\\clock request_id=debug-42")
        # Register a service whose liveness clock fails unexpectedly.
        api.register(self.router, service=OperationsProbeService(provider_factory=lambda: ReadyProvider(self.temporary_directory.name), clock=failing_clock, build_sha_source=lambda: None))
        # Capture the fixed sanitized Operations failure.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch liveness through the isolated real router.
            self.router.dispatch("GET", "/api/v1/operations/liveness")
        # Read the public error after conversion.
        error = raised.exception
        # Verify the fixed error identity and status.
        self.assertEqual((api.PROBE_FAILED_CODE, api.PROBE_FAILED_MESSAGE, 503), (error.code, error.message, error.status))
        # Serialize all details to test the complete public surface.
        serialized = json.dumps(error.details)
        # Verify password material was removed.
        self.assertNotIn("secret", serialized)
        # Verify the internal path was removed.
        self.assertNotIn("private", serialized)
        # Verify the request/debug identifier was removed.
        self.assertNotIn("debug-42", serialized)
        # Verify only the fixed backend reason remains.
        self.assertEqual({"probe": "liveness", "component": "backend", "code": "operations_probe_failed"}, error.details)

    # Confirm an injected service cannot use the importable not-ready type to bypass sanitization.
    def test_service_raised_not_ready_error_is_resanitized(self):
        # Register the hostile injected service in the otherwise isolated router.
        api.register(self.router, service=InjectedNotReadyService())
        # Capture the final public error emitted by the liveness boundary.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch the route that must reject the service-owned error identity and details.
            self.router.dispatch("GET", "/api/v1/operations/liveness")
        # Read the converted public error after the assertion context completes.
        error = raised.exception
        # Verify liveness exposes only its contracted fixed failure identity.
        self.assertEqual((api.PROBE_FAILED_CODE, api.PROBE_FAILED_MESSAGE, 503), (error.code, error.message, error.status))
        # Serialize the full public details surface for leak assertions.
        serialized = json.dumps(error.details)
        # Verify credential-like content was discarded.
        self.assertNotIn("raw-token", serialized)
        # Verify internal path content was discarded.
        self.assertNotIn("internal", serialized)
        # Verify debug identifiers were discarded.
        self.assertNotIn("debug-72", serialized)
        # Verify only the fixed liveness failure context remains.
        self.assertEqual({"probe": "liveness", "component": "backend", "code": "operations_probe_failed"}, error.details)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
