# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-backed runtime API rate-limit policy for SEC-015 and ADMIN-032."""

# Import operating-system configuration so the initial runtime policy honors an explicit deployment baseline.
import os
# Import a reentrant lock so request threads and the Admin save route share one coherent cached policy.
from threading import RLock

# Import the shared schema version so the stored document matches peer settings documents.
from casino.config import SCHEMA_VERSION
# Import the configured provider so the policy survives application restarts in JSON and MySQL modes.
from casino.core.storage import get_storage_provider

# Name the provider document reserved for the global application-request rate policy.
RATE_LIMIT_DOCUMENT_KEY = "settings/rate_limits"
# Keep at least one request per second available so a saved policy cannot make ordinary play unusable.
MIN_REQUESTS_PER_WINDOW = 60
# Preserve the existing reviewed hard ceiling against effectively unbounded request floods.
MAX_REQUESTS_PER_WINDOW = 10_000
# Permit short operational windows without accepting a zero-duration policy.
MIN_WINDOW_SECONDS = 1
# Preserve the existing reviewed one-hour maximum fixed window.
MAX_WINDOW_SECONDS = 3_600
# Raise the fresh-install allowance above the measured fast-autoplay request rate while retaining a bounded window.
DEFAULT_REQUESTS_PER_WINDOW = 1_200
# Retain the established one-minute fixed window as the understandable Admin default.
DEFAULT_WINDOW_SECONDS = 60
# Serialize cache initialization and updates across the approved threaded production worker.
_POLICY_LOCK = RLock()
# Remember the provider identity that owns the cached document so test-provider changes cannot leak state.
_CACHED_PROVIDER = None
# Hold one validated process-local policy copy after its first provider read.
_CACHED_POLICY = None


# Parse one initial integer deployment setting without letting malformed text escape into runtime request handling.
def _environment_default(name: str, fallback: int, minimum: int, maximum: int) -> int:
    # Start protected conversion because startup validation remains the authoritative fail-closed environment gate.
    try:
        # Parse the configured decimal text or the reviewed source default.
        value = int(str(os.environ.get(name, fallback)).strip())
    # Fall back only for standalone tests that import this module without production startup validation.
    except (TypeError, ValueError):
        # Return the reviewed source default for malformed test-only environments.
        return fallback
    # Clamp the initial document default into the same range enforced for Admin updates.
    return max(minimum, min(maximum, value))


# Build a fresh policy document from deployment defaults before any owner-authored setting exists.
def default_rate_limits() -> dict:
    # Return a new mapping so callers cannot mutate shared source constants.
    return {
        # Stamp the shared storage schema for provider compatibility.
        "schema_version": SCHEMA_VERSION,
        # Honor an explicit production allowance while using the autoplay-safe reviewed default otherwise.
        "requests_per_window": _environment_default("CASINO_RATE_LIMIT_REQUESTS", DEFAULT_REQUESTS_PER_WINDOW, MIN_REQUESTS_PER_WINDOW, MAX_REQUESTS_PER_WINDOW),
        # Honor an explicit production duration within the established fixed-window bounds.
        "window_seconds": _environment_default("CASINO_RATE_LIMIT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS, MIN_WINDOW_SECONDS, MAX_WINDOW_SECONDS),
    }


# Coerce and clamp one stored or supplied integer into its reviewed inclusive range.
def _clamp_int(value, minimum: int, maximum: int, fallback: int) -> int:
    # Start protected conversion so malformed provider content cannot break request handling.
    try:
        # Parse the candidate as a decimal integer.
        number = int(value)
    # Preserve the already-validated fallback when coercion fails.
    except (TypeError, ValueError):
        # Return the safe current or default value.
        return fallback
    # Return the parsed value constrained to the reviewed policy range.
    return max(minimum, min(maximum, number))


# Validate one provider document and merge missing fields from current deployment defaults.
def _validated_policy(state) -> dict:
    # Resolve fresh deployment defaults once for consistent fallback values.
    defaults = default_rate_limits()
    # Replace corrupt non-mapping state with the reviewed defaults.
    source = state if isinstance(state, dict) else {}
    # Clamp the application request allowance on every read.
    requests_per_window = _clamp_int(source.get("requests_per_window"), MIN_REQUESTS_PER_WINDOW, MAX_REQUESTS_PER_WINDOW, defaults["requests_per_window"])
    # Clamp the fixed-window duration independently on every read.
    window_seconds = _clamp_int(source.get("window_seconds"), MIN_WINDOW_SECONDS, MAX_WINDOW_SECONDS, defaults["window_seconds"])
    # Return only the canonical validated fields.
    return {"schema_version": SCHEMA_VERSION, "requests_per_window": requests_per_window, "window_seconds": window_seconds}


# Read the current provider-backed policy through one coherent process-local cache.
def rate_limits() -> dict:
    # Resolve the active provider before entering the cache lock.
    provider = get_storage_provider()
    # Share one validated document across request threads in the single production worker.
    with _POLICY_LOCK:
        # Declare cache bindings for replacement when provider identity changes.
        global _CACHED_PROVIDER, _CACHED_POLICY
        # Reload whenever tests or startup switch to a different provider instance.
        if provider is not _CACHED_PROVIDER or _CACHED_POLICY is None:
            # Read the provider document with a fresh callable default.
            stored = provider.read_document(RATE_LIMIT_DOCUMENT_KEY, default_rate_limits)
            # Cache only a validated canonical copy.
            _CACHED_POLICY = _validated_policy(stored)
            # Bind the cache to this exact provider instance.
            _CACHED_PROVIDER = provider
        # Return a copy so request and route callers cannot mutate shared cache state.
        return dict(_CACHED_POLICY)


# Persist one sparse owner update and publish it immediately to the current worker.
def save_rate_limits(updates: dict) -> dict:
    # Resolve the active provider once so write and cache publication cannot cross provider boundaries.
    provider = get_storage_provider()
    # Serialize read, validation, write, and cache publication as one in-process policy transition.
    with _POLICY_LOCK:
        # Declare cache bindings for the committed document.
        global _CACHED_PROVIDER, _CACHED_POLICY
        # Start from the current validated policy so omitted fields stay unchanged.
        current = rate_limits()
        # Copy only the supplied request allowance through its reviewed clamp.
        if "requests_per_window" in (updates or {}):
            # Clamp the owner input while retaining the prior value as a malformed-input fallback.
            current["requests_per_window"] = _clamp_int(updates["requests_per_window"], MIN_REQUESTS_PER_WINDOW, MAX_REQUESTS_PER_WINDOW, current["requests_per_window"])
        # Copy only the supplied duration through its reviewed clamp.
        if "window_seconds" in (updates or {}):
            # Clamp the owner input while retaining the prior value as a malformed-input fallback.
            current["window_seconds"] = _clamp_int(updates["window_seconds"], MIN_WINDOW_SECONDS, MAX_WINDOW_SECONDS, current["window_seconds"])
        # Stamp the current schema before persistence.
        current["schema_version"] = SCHEMA_VERSION
        # Commit the complete validated document through the provider contract.
        provider.write_document(RATE_LIMIT_DOCUMENT_KEY, current)
        # Publish the committed policy immediately to subsequent request checks.
        _CACHED_PROVIDER, _CACHED_POLICY = provider, dict(current)
        # Return an isolated committed copy to the Admin response.
        return dict(current)
