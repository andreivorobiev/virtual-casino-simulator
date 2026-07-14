"""Isolated additive v1 route registration for Operations probes."""

# Import the standard API error so degraded probes receive a sanitized 503 envelope.
from casino.errors import CasinoError
# Import the Operations service without touching the shared application router.
from casino.operations.service import OperationsProbeService

# Publish one stable error code for monitoring clients and future Admin integration.
NOT_READY_CODE = "OPERATIONS_NOT_READY"
# Publish one fixed message that contains no provider or exception details.
NOT_READY_MESSAGE = "Application dependencies are not ready"
# Publish one stable code for unexpected Operations bugs or dependency-hook failures.
PROBE_FAILED_CODE = "OPERATIONS_PROBE_FAILED"
# Publish one fixed message that prevents the global raw-exception handler from reflecting failures.
PROBE_FAILED_MESSAGE = "Operations probe could not be completed"


# Mark the one sanitized degraded-status error that may cross the final boundary unchanged.
class OperationsNotReadyError(CasinoError):
    # Build the fixed 503 error from a service-owned sanitized payload.
    def __init__(self, payload):
        # Delegate only the established code, message, status, and safe details.
        super().__init__(NOT_READY_CODE, NOT_READY_MESSAGE, 503, payload)


# Convert a degraded service result into the existing standard error-envelope path.
def require_ready(payload: dict) -> dict:
    # Return healthy results through the normal ok/data envelope.
    if payload["ready"]:
        # Preserve the exact monitoring payload produced by the service.
        return payload
    # Raise a fixed 503 error whose details contain only the already sanitized status payload.
    raise OperationsNotReadyError(payload)


# Execute one service operation behind a final fixed-error sanitization boundary.
def safe_probe(probe: str, operation):
    # Protect every service failure, including importable public error subclasses.
    try:
        # Return only a successfully produced service payload to route-level policy.
        return operation()
    # Convert every service exception before the application can expose its details or error type.
    except Exception:
        # Return only the fixed backend component and reason code.
        raise CasinoError(PROBE_FAILED_CODE, PROBE_FAILED_MESSAGE, 503, {"probe": probe, "component": "backend", "code": "operations_probe_failed"}) from None


# Register Operations-owned routes into an isolated or later shared router.
def register(router, service=None):
    # Create the production service unless a focused test supplies safe dependency doubles.
    operations_service = service or OperationsProbeService()

    # Register the process-only liveness route as an additive v1 endpoint.
    @router.get(r"/api/v1/operations/liveness")
    # Return liveness without constructing or querying storage.
    def liveness(body, query):
        # Delegate through the final fixed-error boundary.
        return safe_probe("liveness", operations_service.liveness)

    # Register the dependency readiness route as an additive v1 endpoint.
    @router.get(r"/api/v1/operations/readiness")
    # Return healthy readiness or a sanitized standard 503 error.
    def readiness(body, query):
        # Run the service behind the sanitizer before applying the local not-ready policy.
        payload = safe_probe("readiness", operations_service.readiness)
        # Raise only the Operations-owned sanitized degradation built after service success.
        return require_ready(payload)

    # Register the monitoring heartbeat route as an additive v1 endpoint.
    @router.get(r"/api/v1/operations/heartbeat")
    # Return a healthy heartbeat or a sanitized standard 503 error.
    def heartbeat(body, query):
        # Run the service behind the sanitizer before applying the local not-ready policy.
        payload = safe_probe("heartbeat", operations_service.heartbeat)
        # Raise only the Operations-owned sanitized degradation built after service success.
        return require_ready(payload)

    # Return the service so focused tests and later Admin integration can inspect shared heartbeat state.
    return operations_service
