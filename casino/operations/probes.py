# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Dependency probes that return fixed, secret-safe Operations diagnostics."""

# Import operating-system access only for the dedicated build-SHA environment value.
import os
# Import JSON parsing so local readiness proves the bootstrapped store is readable.
import json
# Import regular expressions so build provenance is bounded to hexadecimal commit identifiers.
import re
# Import paths so local provider checks never depend on the process working directory.
from pathlib import Path

# Import the configured storage factory without reading provider credentials or paths.
from casino.core.storage import get_storage_provider
# Import only the packaged application release from the canonical #104 runtime interface.
from casino.module_versions import APP_VERSION

# Name the Operations-owned deployment input without changing the canonical version interface.
BUILD_SHA_ENV = "CASINO_BUILD_SHA"
# Accept abbreviated or full Git commit identifiers and reject every other environment value.
BUILD_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")
# Restrict provider disclosure to the two configured implementations supported by current core storage.
SUPPORTED_STORAGE_PROVIDERS = frozenset({"json", "mysql"})
# Bound each monitoring connection attempt so readiness cannot hang indefinitely.
MYSQL_PROBE_TIMEOUT_SECONDS = 3


# Normalize optional deployment provenance without echoing malformed or sensitive input.
def sanitize_build_sha(value) -> str | None:
    # Reject non-string values before any public response is built.
    if not isinstance(value, str):
        # Publish an explicit unavailable value instead of coercing arbitrary objects.
        return None
    # Remove harmless surrounding whitespace while preserving no other caller-controlled text.
    normalized = value.strip()
    # Reject secrets, paths, branch names, and malformed identifiers through the strict hex boundary.
    if not BUILD_SHA_PATTERN.fullmatch(normalized):
        # Return no provenance rather than leaking the invalid source value.
        return None
    # Normalize valid commit identifiers for deterministic API and smoke comparisons.
    return normalized.lower()


# Read the optional deployment SHA from one dedicated public-metadata environment key.
def environment_build_sha(environ=None) -> str | None:
    # Use the live process environment unless an isolated test supplies a value-only mapping.
    current_environment = os.environ if environ is None else environ
    # Sanitize the selected value before it can enter a response payload.
    return sanitize_build_sha(current_environment.get(BUILD_SHA_ENV))


# Build the public application identity while keeping #104 as the only release-version source.
def build_metadata(build_sha_source=environment_build_sha) -> dict:
    # Start with unavailable provenance so source failures cannot escape through the generic handler.
    build_sha = None
    # Protect the response from injected or environment-backed provenance source failures.
    try:
        # Normalize the source result even when a custom integration hook forgot to sanitize it.
        build_sha = sanitize_build_sha(build_sha_source())
    # Convert every ordinary source failure into a safe unavailable value.
    except Exception:
        # Preserve liveness because optional build provenance is not a runtime dependency.
        build_sha = None
    # Return only the canonical packaged release and optional validated commit identity.
    return {"app_version": APP_VERSION, "sha": build_sha}


# Reduce a provider object to the only names approved for public diagnostics.
def safe_provider_name(provider) -> str:
    # Protect attribute access because third-party or test providers may implement dynamic properties.
    try:
        # Read only the provider's documented public name and never its configuration object.
        provider_name = provider.name
    # Treat provider metadata failures as unsupported without returning their exception text.
    except Exception:
        # Use one stable fallback that reveals no class, module, or configuration detail.
        return "unknown"
    # Publish only explicitly supported provider identifiers.
    return provider_name if provider_name in SUPPORTED_STORAGE_PROVIDERS else "unknown"


# Close a DB-API object without allowing cleanup diagnostics to leak into probe responses.
def _close_quietly(resource) -> None:
    # Skip cleanup for resources that were never created.
    if resource is None:
        # Return without invoking dynamic attributes on a missing resource.
        return
    # Protect the stable probe result from connector-specific close failures.
    try:
        # Close the cursor or connection through its normal DB-API method.
        resource.close()
    # Suppress cleanup errors because callers receive only fixed readiness reason codes.
    except Exception:
        # Leave no connector error text or configuration values in the public result.
        return


# Prove current MySQL connectivity even after the provider's schema-ready cache was set.
def _probe_mysql(provider) -> None:
    # Initialize resources so every partial connection path is safely cleaned up.
    connection = None
    # Initialize the cursor separately because connection creation may fail first.
    cursor = None
    # Protect both resources with deterministic cleanup.
    try:
        # Open a fresh provider-managed connection without inspecting its credential configuration.
        connection = provider.connect(connection_timeout=MYSQL_PROBE_TIMEOUT_SECONDS)
        # Open a standard cursor for a constant connectivity query.
        cursor = connection.cursor()
        # Execute a read-only constant query that touches no casino data.
        cursor.execute("SELECT 1")
        # Read the one expected row so deferred connector failures are observed.
        row = cursor.fetchone()
        # Reject missing or altered results as unavailable connectivity.
        if not row or row[0] != 1:
            # Raise an internal fixed error that the outer probe converts to a public reason code.
            raise RuntimeError("MySQL connectivity probe did not return the expected constant")
    # Always release cursor and connection resources after pass or failure.
    finally:
        # Close the cursor before returning its connection to the connector.
        _close_quietly(cursor)
        # Close the connection so monitoring cannot exhaust the pool over time.
        _close_quietly(connection)


# Prove the bootstrapped JSON store remains readable and its root remains writable.
def _probe_json(provider) -> None:
    # Resolve only concrete provider paths without publishing them in any result.
    data_dir = Path(provider.data_dir)
    # Resolve the canonical player document through the provider's public path helper.
    players_path = Path(provider.players_path())
    # Require the bootstrapped storage root to remain a real directory.
    if not data_dir.is_dir():
        # Raise a fixed internal failure that the outer probe converts to a safe reason code.
        raise RuntimeError("JSON storage root is unavailable")
    # Require read and write access needed by normal persistence operations.
    if not os.access(data_dir, os.R_OK | os.W_OK):
        # Raise no path or permission detail that could reach a caller accidentally.
        raise RuntimeError("JSON storage root is not readable and writable")
    # Require the startup-bootstrap player document before declaring the application ready.
    if not players_path.is_file() or not os.access(players_path, os.R_OK):
        # Treat a missing or unreadable primary store as unavailable readiness.
        raise RuntimeError("JSON player storage is unavailable")
    # Open the primary document read-only so the probe never mutates user state.
    with players_path.open("r", encoding="utf-8") as handle:
        # Parse the existing document so corrupt persistence cannot produce a false healthy status.
        player_state = json.load(handle)
    # Require the minimal provider-owned document shape used by runtime player services.
    if not isinstance(player_state, dict) or not isinstance(player_state.get("players"), list):
        # Convert an unusable but parseable document to the same safe unavailable result.
        raise RuntimeError("JSON player storage has an invalid shape")


# Check the configured storage dependency without returning exceptions, paths, hosts, or credentials.
def probe_storage(provider_factory=get_storage_provider) -> dict:
    # Default to an undisclosed provider until construction succeeds safely.
    provider_name = "unknown"
    # Protect the complete provider construction and connectivity path from the generic API handler.
    try:
        # Resolve the process-wide provider through the existing storage abstraction.
        provider = provider_factory()
        # Reduce provider metadata to the supported public allowlist.
        provider_name = safe_provider_name(provider)
        # Reject an unsupported provider before invoking arbitrary probe behavior.
        if provider_name == "unknown":
            # Return a stable reason code without exposing the provider's raw name or class.
            return {"status": "fail", "provider": "unknown", "reason_code": "storage_provider_unsupported"}
        # Check the local JSON provider through its public idempotent readiness seam.
        if provider_name == "json":
            # Verify the bootstrapped primary store without writing a probe marker.
            _probe_json(provider)
        # Check MySQL with a fresh constant query rather than trusting its cached schema-ready flag.
        else:
            # Exercise live database connectivity without reading application rows.
            _probe_mysql(provider)
    # Convert every provider or connector failure into a fixed public code.
    except Exception:
        # Distinguish database availability without exposing its host, database, or connector error.
        reason_code = "database_unavailable" if provider_name == "mysql" else "storage_unavailable"
        # Return only stable monitoring dimensions.
        return {"status": "fail", "provider": provider_name, "reason_code": reason_code}
    # Report a successful dependency check with no raw provider details.
    return {"status": "pass", "provider": provider_name}
