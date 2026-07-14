"""Isolated additive v1 route registration for Operations probes."""

# Import regular expressions so caller-controlled strings must match public contract shapes.
import re
# Import timestamp parsing so shape-valid but impossible dates are rejected.
from datetime import datetime

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
# Accept only the canonical semantic-version shape published by the Operations contract.
APP_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
# Accept only bounded hexadecimal deployment provenance already allowed by the contract.
BUILD_SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
# Accept the UTC timestamp shape emitted by the canonical application clock.
TIMESTAMP_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")
# Enumerate every fixed degraded reason that can safely cross the API boundary.
DEGRADED_REASON_CODES = ("storage_unavailable", "database_unavailable", "storage_provider_unsupported")
# Enumerate provider identities approved for healthy monitoring responses.
READY_STORAGE_PROVIDERS = ("json", "mysql")
# Include the safe unknown state only when a dependency is degraded.
DEGRADED_STORAGE_PROVIDERS = ("json", "mysql", "unknown")
# Define the exact common response keys required by every Operations probe.
COMMON_PAYLOAD_KEYS = frozenset({"schema_version", "probe", "status", "checked_at", "last_successful_heartbeat_at", "build"})
# Define the exact dependency response keys required by readiness and heartbeat.
DEPENDENCY_PAYLOAD_KEYS = COMMON_PAYLOAD_KEYS | frozenset({"ready", "storage_provider", "checks", "reasons"})


# Mark the one sanitized degraded-status error that may cross the final boundary unchanged.
class OperationsNotReadyError(CasinoError):
    # Build the fixed 503 error from a service-owned sanitized payload.
    def __init__(self, payload):
        # Delegate only the established code, message, status, and safe details.
        super().__init__(NOT_READY_CODE, NOT_READY_MESSAGE, 503, payload)


# Require one plain dictionary with no undeclared fields before reading any values from it.
def _require_exact_dict(value, expected_keys) -> dict:
    # Reject custom mappings and dictionary subclasses whose accessors could run arbitrary code.
    if type(value) is not dict:
        # Raise only a local fixed diagnostic that the outer boundary always discards.
        raise ValueError("invalid Operations payload")
    # Reject missing or additional keys so undeclared diagnostics can never cross the boundary.
    if frozenset(value) != expected_keys:
        # Raise the same local fixed diagnostic without echoing key names or values.
        raise ValueError("invalid Operations payload")
    # Snapshot the exact built-in dictionary so later service-side mutation cannot alter validation.
    return value.copy()


# Require one exact built-in string and rebuild it from a fixed public enum tuple.
def _validated_enum(value, permitted_values) -> str:
    # Reject string subclasses whose overloaded equality could spoof an allowlisted value.
    if type(value) is not str:
        # Convert custom or non-string values through the fixed failure boundary.
        raise ValueError("invalid Operations payload")
    # Compare only exact built-in strings against fixed module-owned literals.
    for permitted_value in permitted_values:
        # Return the module-owned literal rather than the service-owned object on a match.
        if value == permitted_value:
            # Rebuild the canonical public enum value.
            return permitted_value
    # Reject arbitrary exact strings that are not part of the contract enum.
    raise ValueError("invalid Operations payload")


# Require one canonical UTC timestamp or an explicitly permitted null value.
def _validated_timestamp(value, *, nullable: bool) -> str | None:
    # Preserve null only for contract fields that explicitly allow an unavailable timestamp.
    if nullable and value is None:
        # Return the explicit unavailable state without coercion.
        return None
    # Reject non-strings and caller-controlled text outside the bounded timestamp grammar.
    if type(value) is not str or not TIMESTAMP_PATTERN.fullmatch(value):
        # Raise a fixed internal validation failure consumed by the final boundary.
        raise ValueError("invalid Operations payload")
    # Parse the bounded UTC value so impossible calendar and clock fields cannot pass validation.
    try:
        # Convert the terminal Z marker to the standard-library UTC offset form.
        datetime.fromisoformat(value[:-1] + "+00:00")
    # Reject shape-valid but impossible dates and times through the same fixed boundary.
    except ValueError:
        # Discard the invalid timestamp without reflecting its value.
        raise ValueError("invalid Operations payload") from None
    # Return the already bounded timestamp string.
    return value


# Rebuild public build metadata from exact keys and bounded contract values.
def _validated_build(value) -> dict:
    # Require exactly the two public build fields.
    build = _require_exact_dict(value, frozenset({"app_version", "sha"}))
    # Read the packaged version only after the mapping shape is fixed.
    app_version = build["app_version"]
    # Reject arbitrary strings in the public version field.
    if type(app_version) is not str or not APP_VERSION_PATTERN.fullmatch(app_version):
        # Convert the malformed return through the outer fixed failure boundary.
        raise ValueError("invalid Operations payload")
    # Read the optional deployment identifier only after shape validation.
    build_sha = build["sha"]
    # Reject every non-null value outside the strict lowercase hexadecimal contract.
    if build_sha is not None and (type(build_sha) is not str or not BUILD_SHA_PATTERN.fullmatch(build_sha)):
        # Convert unsafe provenance through the fixed failure boundary.
        raise ValueError("invalid Operations payload")
    # Rebuild a plain allowlisted object instead of returning the service-owned mapping.
    return {"app_version": app_version, "sha": build_sha}


# Validate and rebuild the common response fields shared by all probe types.
def _validated_common_payload(probe: str, payload: dict, expected_keys) -> dict:
    # Require the exact top-level keys before reading caller-controlled values.
    source = _require_exact_dict(payload, expected_keys)
    # Require the integer schema marker without accepting boolean equality with one.
    if type(source["schema_version"]) is not int or source["schema_version"] != 1:
        # Convert an unsupported response schema to the fixed probe-failure path.
        raise ValueError("invalid Operations payload")
    # Require and rebuild the exact route identity from the module-owned probe literal.
    public_probe = _validated_enum(source["probe"], (probe,))
    # Require and rebuild only the two statuses allowed anywhere in Operations payloads.
    public_status = _validated_enum(source["status"], ("live", "degraded"))
    # Rebuild only the common contract fields with bounded nested values.
    return {"schema_version": 1, "probe": public_probe, "status": public_status, "checked_at": _validated_timestamp(source["checked_at"], nullable=False), "last_successful_heartbeat_at": _validated_timestamp(source["last_successful_heartbeat_at"], nullable=True), "build": _validated_build(source["build"])}


# Validate and rebuild one liveness result against its exact public schema.
def _validated_liveness_payload(payload: dict) -> dict:
    # Validate the exact liveness keys and shared metadata.
    result = _validated_common_payload("liveness", payload, COMMON_PAYLOAD_KEYS)
    # A responding liveness probe may publish only the fixed live status.
    if result["status"] != "live":
        # Reject arbitrary or contradictory status strings.
        raise ValueError("invalid Operations payload")
    # Rebuild the one accepted liveness status from the module-owned literal.
    result["status"] = "live"
    # Return only the rebuilt, allowlisted liveness payload.
    return result


# Validate and rebuild readiness or heartbeat component checks.
def _validated_checks(value, *, ready: bool, provider: str) -> dict:
    # Require exactly the backend and storage checks.
    checks = _require_exact_dict(value, frozenset({"backend", "storage"}))
    # Require the fixed healthy backend check without permitting diagnostic fields.
    backend = _require_exact_dict(checks["backend"], frozenset({"status"}))
    # Require and rebuild the one fixed backend status literal.
    _validated_enum(backend["status"], ("pass",))
    # Require only the storage status and allowlisted provider identity.
    storage = _require_exact_dict(checks["storage"], frozenset({"status", "provider"}))
    # Require and rebuild the nested provider from the top-level canonical literal.
    nested_provider = _validated_enum(storage["provider"], (provider,))
    # Require and rebuild only the two contracted storage status literals.
    storage_status = _validated_enum(storage["status"], ("pass", "fail"))
    # Require the storage state to match the public readiness boolean.
    if storage_status != ("pass" if ready else "fail"):
        # Reject contradictory dependency states.
        raise ValueError("invalid Operations payload")
    # Rebuild the exact safe check object from validated fixed values.
    return {"backend": {"status": "pass"}, "storage": {"status": storage_status, "provider": nested_provider}}


# Validate and rebuild the fixed degraded-reason list.
def _validated_reasons(value, *, ready: bool) -> list:
    # Require the concrete list type so custom iterables cannot execute during serialization.
    if type(value) is not list:
        # Reject malformed reason containers through the fixed failure boundary.
        raise ValueError("invalid Operations payload")
    # Snapshot the exact built-in list so later service-side mutation cannot alter validation.
    reason_values = list(value)
    # Healthy responses must never carry a degraded reason.
    if ready:
        # Reject every non-empty healthy reason list.
        if reason_values:
            # Prevent arbitrary returned diagnostics from escaping through a healthy response.
            raise ValueError("invalid Operations payload")
        # Rebuild the contracted empty reason list.
        return []
    # Require exactly one copied reason after snapshotting the built-in list.
    if len(reason_values) != 1:
        # Reject missing or expanded diagnostics.
        raise ValueError("invalid Operations payload")
    # Require exactly the two contracted fields in the one degraded reason.
    reason = _require_exact_dict(reason_values[0], frozenset({"component", "code"}))
    # Require and rebuild the one fixed degraded component.
    component = _validated_enum(reason["component"], ("storage",))
    # Require and rebuild one allowlisted stable reason code.
    reason_code = _validated_enum(reason["code"], DEGRADED_REASON_CODES)
    # Rebuild the reason object from only validated enum values.
    return [{"component": component, "code": reason_code}]


# Validate and rebuild one readiness-equivalent payload against exact state invariants.
def _validated_dependency_payload(probe: str, payload: dict) -> dict:
    # Snapshot the exact dependency keys before reading any state-specific values.
    source = _require_exact_dict(payload, DEPENDENCY_PAYLOAD_KEYS)
    # Validate the shared metadata from the stable top-level snapshot.
    result = _validated_common_payload(probe, source, DEPENDENCY_PAYLOAD_KEYS)
    # Read the readiness marker from the exact plain source dictionary.
    ready = source["ready"]
    # Require a real boolean rather than truthy caller-controlled values.
    if type(ready) is not bool:
        # Convert malformed state to the fixed failure boundary.
        raise ValueError("invalid Operations payload")
    # Read the provider identity only after top-level shape validation.
    provider_source = source["storage_provider"]
    # Select the permitted provider set for the reported health state.
    permitted_providers = READY_STORAGE_PROVIDERS if ready else DEGRADED_STORAGE_PROVIDERS
    # Reject non-string, unsupported, or state-incompatible provider identities.
    provider = _validated_enum(provider_source, permitted_providers)
    # Require status and readiness to describe the same state.
    if result["status"] != ("live" if ready else "degraded"):
        # Reject contradictory status values.
        raise ValueError("invalid Operations payload")
    # Rebuild the accepted dependency status from its module-owned literal.
    result["status"] = "live" if ready else "degraded"
    # Healthy dependency probes must publish a successful heartbeat timestamp.
    if ready and result["last_successful_heartbeat_at"] is None:
        # Reject a contract-incomplete healthy response.
        raise ValueError("invalid Operations payload")
    # Add only validated dependency fields to the rebuilt common payload.
    result.update({"ready": ready, "storage_provider": provider, "checks": _validated_checks(source["checks"], ready=ready, provider=provider), "reasons": _validated_reasons(source["reasons"], ready=ready)})
    # Return the complete plain allowlisted payload.
    return result


# Select the exact public schema for the route that invoked the probe.
def _validated_probe_payload(probe: str, payload: dict) -> dict:
    # Route liveness through its storage-independent schema.
    if probe == "liveness":
        # Return only the rebuilt liveness response.
        return _validated_liveness_payload(payload)
    # Route dependency-aware probes through their shared strict schema.
    if probe in {"readiness", "heartbeat"}:
        # Preserve the exact route identity while validating shared fields.
        return _validated_dependency_payload(probe, payload)
    # Reject any accidental or caller-controlled probe identifier.
    raise ValueError("invalid Operations probe")


# Execute and validate one service operation behind a final fixed-error boundary.
def safe_probe(probe: str, operation, *, require_ready: bool = False):
    # Protect every service failure and malformed return, including importable error subclasses.
    try:
        # Rebuild the successful return through the exact allowlisted public schema.
        payload = _validated_probe_payload(probe, operation())
        # Evaluate route-level readiness policy while malformed key access is still protected.
        degraded = require_ready and not payload["ready"]
    # Convert every service or validation exception before the application can expose details.
    except Exception:
        # Return only the fixed backend component and reason code.
        raise CasinoError(PROBE_FAILED_CODE, PROBE_FAILED_MESSAGE, 503, {"probe": probe, "component": "backend", "code": "operations_probe_failed"}) from None
    # Convert only a validated degraded result into the standard not-ready error path.
    if degraded:
        # Raise the rebuilt payload whose complete shape and values were validated above.
        raise OperationsNotReadyError(payload)
    # Return only the rebuilt safe response object.
    return payload


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
        # Run service, return validation, and not-ready policy behind one fixed boundary.
        return safe_probe("readiness", operations_service.readiness, require_ready=True)

    # Register the monitoring heartbeat route as an additive v1 endpoint.
    @router.get(r"/api/v1/operations/heartbeat")
    # Return a healthy heartbeat or a sanitized standard 503 error.
    def heartbeat(body, query):
        # Run service, return validation, and not-ready policy behind one fixed boundary.
        return safe_probe("heartbeat", operations_service.heartbeat, require_ready=True)

    # Return the service so focused tests and later Admin integration can inspect shared heartbeat state.
    return operations_service
