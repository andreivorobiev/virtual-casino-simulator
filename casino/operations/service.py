"""Thread-safe Operations status aggregation for issue #72."""

# Import a re-entrant lock so overlapping monitoring calls retain monotonic heartbeat state.
import threading

# Import the shared UTC formatter for contract-compatible timestamps.
from casino.core.clock import utc_now
# Import only sanitized probe helpers and their safe default dependency sources.
from casino.operations.probes import build_metadata, environment_build_sha, probe_storage
# Import the configured provider factory used only when a dependency probe is requested.
from casino.core.storage import get_storage_provider

# Version the monitoring payload independently from the packaged application release.
OPERATIONS_SCHEMA_VERSION = 1


# Aggregate liveness, readiness, and heartbeat state without persisting diagnostics to user data.
class OperationsProbeService:
    # Store injectable dependencies so focused tests never touch repository data or external databases.
    def __init__(self, *, provider_factory=get_storage_provider, clock=utc_now, build_sha_source=environment_build_sha):
        # Store the lazy provider factory so liveness never constructs storage.
        self._provider_factory = provider_factory
        # Store the clock hook used for deterministic status timestamps.
        self._clock = clock
        # Store the optional deployment provenance source behind strict sanitizer handling.
        self._build_sha_source = build_sha_source
        # Guard the process-local last-successful heartbeat across request threads.
        self._heartbeat_lock = threading.RLock()
        # Start with no successful dependency heartbeat in this process lifetime.
        self._last_successful_heartbeat_at = None

    # Read the last successful dependency heartbeat under its synchronization boundary.
    def _last_successful_heartbeat(self) -> str | None:
        # Serialize the read with concurrent success updates.
        with self._heartbeat_lock:
            # Return the immutable timestamp value or the explicit unavailable state.
            return self._last_successful_heartbeat_at

    # Advance the last-successful timestamp monotonically for overlapping probe completions.
    def _record_success(self, checked_at: str) -> str:
        # Serialize comparison and assignment as one state transition.
        with self._heartbeat_lock:
            # Keep the latest ISO UTC timestamp when requests finish out of order.
            if self._last_successful_heartbeat_at is None or checked_at > self._last_successful_heartbeat_at:
                # Record only a successful dependency probe timestamp.
                self._last_successful_heartbeat_at = checked_at
            # Return the durable process-local value for the current response.
            return self._last_successful_heartbeat_at

    # Build metadata shared by every Operations response.
    def _base_payload(self, probe: str, checked_at: str) -> dict:
        # Return only schema, probe, time, canonical release, and sanitized optional SHA fields.
        return {"schema_version": OPERATIONS_SCHEMA_VERSION, "probe": probe, "checked_at": checked_at, "last_successful_heartbeat_at": self._last_successful_heartbeat(), "build": build_metadata(self._build_sha_source)}

    # Report process liveness without touching storage or any external dependency.
    def liveness(self) -> dict:
        # Return only the anonymous-safe process state without time, build, or dependency metadata.
        return {"status": "live"}

    # Run the shared dependency check for readiness or heartbeat requests.
    def _dependency_status(self, probe: str) -> dict:
        # Run the fully sanitized storage probe against the configured provider factory.
        storage = probe_storage(self._provider_factory)
        # Capture completion time after the dependency call so successful heartbeats are never pre-stamped.
        checked_at = self._clock()
        # Treat the storage dependency as ready only after its concrete check passes.
        ready = storage["status"] == "pass"
        # Advance the successful heartbeat for every complete readiness-equivalent check.
        if ready:
            # Record the latest successful dependency check before building the response.
            self._record_success(checked_at)
        # Build the common metadata after any successful timestamp update.
        payload = self._base_payload(probe, checked_at)
        # Report a responding healthy process as live and a dependency failure as degraded.
        payload["status"] = "live" if ready else "degraded"
        # Publish the explicit boolean used by monitoring and future Admin controls.
        payload["ready"] = ready
        # Publish only the allowlisted provider name selected by the storage probe.
        payload["storage_provider"] = storage["provider"]
        # Publish component checks without error strings or internal details.
        payload["checks"] = {"backend": {"status": "pass"}, "storage": {"status": storage["status"], "provider": storage["provider"]}}
        # Publish an empty list on success or one fixed component reason on degradation.
        payload["reasons"] = [] if ready else [{"component": "storage", "code": storage["reason_code"]}]
        # Return the complete sanitized dependency status for API policy handling.
        return payload

    # Report whether the backend and configured storage are currently ready.
    def readiness(self) -> dict:
        # Delegate to the common dependency path with the contract's readiness probe name.
        return self._dependency_status("readiness")

    # Run the monitoring heartbeat through the same dependency semantics as readiness.
    def heartbeat(self) -> dict:
        # Delegate to the common dependency path with the distinct heartbeat probe name.
        return self._dependency_status("heartbeat")
