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


# Simulate a buggy service that returns caller-controlled diagnostics instead of raising.
class InjectedPayloadService:
    # Store the hostile or malformed return used by one route test.
    def __init__(self, payload):
        # Preserve the exact injected object so the API boundary must validate it.
        self.payload = payload

    # Return the injected object from liveness without service sanitization.
    def liveness(self):
        # Exercise the route's successful-return boundary.
        return self.payload

    # Return the injected object from readiness without service sanitization.
    def readiness(self):
        # Exercise the route's degraded-policy boundary.
        return self.payload

    # Return the injected object from heartbeat without service sanitization.
    def heartbeat(self):
        # Exercise the second dependency route's successful-return boundary.
        return self.payload


# Simulate a string subclass that spoofs allowlist equality while serializing hidden content.
class SpoofedString(str):
    # Construct one visible sentinel with a separate value accepted by unsafe comparisons.
    def __new__(cls, serialized_value, accepted_value):
        # Create the immutable string content that JSON serialization would expose.
        instance = super().__new__(cls, serialized_value)
        # Store the allowlisted value used only by hostile equality methods.
        instance.accepted_value = accepted_value
        # Return the configured hostile string instance.
        return instance

    # Pretend the sentinel equals one allowlisted public enum value.
    def __eq__(self, other):
        # Compare the other value against the hidden accepted literal.
        return other == self.accepted_value

    # Keep inequality consistent with the hostile equality result.
    def __ne__(self, other):
        # Invert the spoofed equality result.
        return not self.__eq__(other)

    # Match hash-based allowlists for the hidden accepted literal.
    def __hash__(self):
        # Return the accepted literal's hash instead of the serialized sentinel's hash.
        return hash(self.accepted_value)


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
        liveness = self.router.dispatch("GET", "/healthz")
        # Dispatch the dependency readiness request.
        readiness = self.router.dispatch("GET", "/readyz")
        # Dispatch the monitoring heartbeat request.
        heartbeat = self.router.dispatch("GET", "/api/v2/admin/operations")
        # Verify registration preserves the injected shared service instance.
        self.assertIs(service, registered)
        # Verify each route keeps its contract probe identity.
        self.assertEqual(({"status": "live"}, "readiness", "heartbeat"), (liveness, readiness["probe"], heartbeat["probe"]))
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
            self.router.dispatch("GET", "/readyz")
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
        self.assertEqual({"status": "live"}, self.router.dispatch("GET", "/healthz"))
        # Verify no mutating method was registered for monitoring paths.
        with self.assertRaises(NotFoundError):
            # Dispatch a forbidden POST shape through the real router matcher.
            self.router.dispatch("POST", "/healthz")

    # Confirm an unexpected clock failure is converted before the global raw-error handler.
    def test_unexpected_probe_failure_raises_fixed_sanitized_503(self):
        # Build a clock that raises raw sensitive and debug text.
        def failing_clock():
            # Raise the value that the Operations API boundary must consume.
            raise RuntimeError("password=secret C:\\private\\clock request_id=debug-42")
        # Register a service whose readiness clock fails unexpectedly.
        api.register(self.router, service=OperationsProbeService(provider_factory=lambda: ReadyProvider(self.temporary_directory.name), clock=failing_clock, build_sha_source=lambda: None))
        # Capture the fixed sanitized Operations failure.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch readiness through the isolated real router.
            self.router.dispatch("GET", "/readyz")
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
        self.assertEqual({"probe": "readiness", "component": "backend", "code": "operations_probe_failed"}, error.details)

    # Confirm an injected service cannot use the importable not-ready type to bypass sanitization.
    def test_service_raised_not_ready_error_is_resanitized(self):
        # Register the hostile injected service in the otherwise isolated router.
        api.register(self.router, service=InjectedNotReadyService())
        # Capture the final public error emitted by the liveness boundary.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch the route that must reject the service-owned error identity and details.
            self.router.dispatch("GET", "/healthz")
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

    # Confirm every route rejects returned diagnostics outside its exact public schema.
    def test_service_returned_diagnostics_are_rejected_without_leakage(self):
        # Define one unsafe return for each distinct route policy path.
        cases = (
            # Exercise undeclared fields on the liveness response path.
            ("liveness", {"probe": "liveness", "status": "live", "secret": "SENTINEL-LIVE"}),
            # Exercise a degraded readiness return that previously reached error details.
            ("readiness", {"ready": False, "secret": "SENTINEL-READY"}),
            # Exercise a truthy heartbeat return with an internal path field.
            ("heartbeat", {"ready": True, "path": "C:\\private\\SENTINEL-HEARTBEAT"}),
        )
        # Exercise all three routes without opening a listener.
        for probe, payload in cases:
            # Report the probe name if one boundary regresses.
            with self.subTest(probe=probe):
                # Use a fresh router so registrations remain isolated per case.
                router = Router()
                # Register the hostile successful-return service.
                api.register(router, service=InjectedPayloadService(payload))
                # Select the approved route for the probe under test.
                route = {"liveness": "/healthz", "readiness": "/readyz", "heartbeat": "/api/v2/admin/operations"}[probe]
                # Capture the fixed sanitized failure emitted for the malformed return.
                with self.assertRaises(CasinoError) as raised:
                    # Dispatch the exact route through the production router matcher.
                    router.dispatch("GET", route)
                # Read the converted public error after the assertion context completes.
                error = raised.exception
                # Verify every malformed return uses the fixed failure identity.
                self.assertEqual((api.PROBE_FAILED_CODE, api.PROBE_FAILED_MESSAGE, 503), (error.code, error.message, error.status))
                # Serialize the complete public error surface for leakage assertions.
                serialized = json.dumps({"message": error.message, "details": error.details})
                # Verify no injected sentinel fragment escaped through any endpoint.
                self.assertNotIn("SENTINEL", serialized)
                # Verify only the fixed endpoint-specific failure details remain.
                self.assertEqual({"probe": probe, "component": "backend", "code": "operations_probe_failed"}, error.details)

    # Confirm a malformed real service clock result cannot become public response text.
    def test_malformed_clock_return_is_rejected_without_leakage(self):
        # Build the concrete service with a caller-controlled clock return.
        service = OperationsProbeService(provider_factory=lambda: ReadyProvider(self.temporary_directory.name), clock=lambda: "token=secret C:\\private", build_sha_source=lambda: None)
        # Register the concrete service in the isolated router.
        api.register(self.router, service=service)
        # Capture the fixed sanitizer result from the readiness route.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch through the dependency-aware path without opening a listener.
            self.router.dispatch("GET", "/readyz")
        # Serialize every caller-visible error field.
        serialized = json.dumps({"message": raised.exception.message, "details": raised.exception.details})
        # Verify the unsafe clock return was completely discarded.
        self.assertNotIn("secret", serialized)
        # Verify internal path content was completely discarded.
        self.assertNotIn("private", serialized)
        # Verify the fixed readiness failure remains contract-compatible.
        self.assertEqual({"probe": "readiness", "component": "backend", "code": "operations_probe_failed"}, raised.exception.details)

    # Confirm hostile string subclasses cannot spoof any returned enum allowlist.
    def test_spoofed_enum_subclasses_are_rejected_without_leakage(self):
        # Build one deterministic healthy service for valid payload baselines.
        ready_service = OperationsProbeService(provider_factory=lambda: ReadyProvider(self.temporary_directory.name), clock=lambda: "2026-07-14T11:05:00.000Z", build_sha_source=lambda: None)
        # Build one deterministic degraded service for a valid reason baseline.
        degraded_service = OperationsProbeService(provider_factory=lambda: (_ for _ in ()).throw(RuntimeError("unavailable")), clock=lambda: "2026-07-14T11:06:00.000Z", build_sha_source=lambda: None)
        # Create a liveness payload whose status serializes a secret sentinel.
        liveness_status = ready_service.liveness()
        # Spoof equality with the required live status.
        liveness_status["status"] = SpoofedString("SENTINEL-STATUS", "live")
        # Create a healthy dependency payload whose top-level provider serializes a sentinel.
        top_provider = ready_service.readiness()
        # Spoof equality with the required JSON provider.
        top_provider["storage_provider"] = SpoofedString("SENTINEL-PROVIDER", "json")
        # Create a healthy dependency payload whose nested provider serializes a sentinel.
        nested_provider = ready_service.readiness()
        # Spoof equality with the matching top-level JSON provider.
        nested_provider["checks"]["storage"]["provider"] = SpoofedString("SENTINEL-NESTED-PROVIDER", "json")
        # Create a healthy dependency payload whose nested status serializes a sentinel.
        nested_status = ready_service.readiness()
        # Spoof equality with the required passing storage status.
        nested_status["checks"]["storage"]["status"] = SpoofedString("SENTINEL-CHECK", "pass")
        # Create a degraded payload whose public reason code serializes a sentinel.
        degraded_reason = degraded_service.readiness()
        # Spoof equality with the stable storage-unavailable reason.
        degraded_reason["reasons"][0]["code"] = SpoofedString("SENTINEL-REASON", "storage_unavailable")
        # Exercise every enum-bearing response layer through its real route policy.
        cases = (
            # Verify liveness status is rebuilt from an exact built-in string.
            ("liveness", liveness_status),
            # Verify the top-level dependency provider rejects subclasses.
            ("readiness", top_provider),
            # Verify the nested dependency provider rejects subclasses.
            ("readiness", nested_provider),
            # Verify the nested dependency status rejects subclasses.
            ("readiness", nested_status),
            # Verify the degraded reason code rejects subclasses.
            ("readiness", degraded_reason),
        )
        # Run all hostile payloads without starting a listener.
        for probe, payload in cases:
            # Report both probe and sentinel content when a subcase regresses.
            with self.subTest(probe=probe, payload=payload):
                # Use a fresh router so route registrations remain isolated.
                router = Router()
                # Register the hostile successful-return service.
                api.register(router, service=InjectedPayloadService(payload))
                # Select the approved route for the probe under test.
                route = {"liveness": "/healthz", "readiness": "/readyz", "heartbeat": "/api/v2/admin/operations"}[probe]
                # Capture the fixed failure that must replace the spoofed return.
                with self.assertRaises(CasinoError) as raised:
                    # Dispatch the exact affected route through the production matcher.
                    router.dispatch("GET", route)
                # Serialize every caller-visible error field.
                serialized = json.dumps({"message": raised.exception.message, "details": raised.exception.details})
                # Verify no underlying sentinel content escaped.
                self.assertNotIn("SENTINEL", serialized)
                # Verify the result used only the fixed probe-failure details.
                self.assertEqual({"probe": probe, "component": "backend", "code": "operations_probe_failed"}, raised.exception.details)

    # Confirm shape-valid but impossible timestamps are rejected as probe failures.
    def test_impossible_timestamp_is_rejected(self):
        # Build an otherwise valid readiness payload from the concrete service.
        payload = OperationsProbeService(provider_factory=lambda: ReadyProvider(self.temporary_directory.name), clock=lambda: "9999-99-99T99:99:99Z", build_sha_source=lambda: None).readiness()
        # Register the malformed successful return through the isolated route.
        api.register(self.router, service=InjectedPayloadService(payload))
        # Capture the fixed failure instead of returning an invalid OpenAPI date-time.
        with self.assertRaises(CasinoError) as raised:
            # Dispatch the readiness endpoint without opening a listener.
            self.router.dispatch("GET", "/readyz")
        # Verify the invalid timestamp used only the fixed failure path.
        self.assertEqual({"probe": "readiness", "component": "backend", "code": "operations_probe_failed"}, raised.exception.details)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
