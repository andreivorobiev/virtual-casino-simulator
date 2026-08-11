# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import future annotations so the tuple return hint parses on the supported interpreter.
from __future__ import annotations
# Import the shared schema version so the stored document stays consistent with peer settings docs.
from casino.config import SCHEMA_VERSION
# Import the configured storage provider so the policy persists in both JSON and MySQL modes.
from casino.core.storage import get_storage_provider
# Import the shared clock so a policy change can stamp a durable last-updated timestamp. (SESSION-010)
from casino.core.clock import utc_now

# Provider document key for the global registered-account session-timeout policy. (SESSION-009)
SESSION_DOCUMENT_KEY = "settings/session"

# Cap the actor identifier stored on the policy so an oversized value can never bloat the document. (SESSION-010)
MAX_ACTOR_LENGTH = 160

# Reviewed bounds so a stored or supplied value can never disable expiry or exceed the absolute ceiling.
MIN_IDLE_MINUTES = 1
# Cap the idle window at the 24-hour absolute ceiling so idle can never outlast the absolute limit.
MAX_IDLE_MINUTES = 1440
# Require at least a one-hour absolute lifetime so a misconfiguration cannot lock everyone out instantly.
MIN_ABSOLUTE_HOURS = 1
# Match the reviewed 24-hour absolute session ceiling enforced elsewhere by MAX_SESSION_TTL_SECONDS.
MAX_ABSOLUTE_HOURS = 24
# Allow no pre-expiration warning at all so the surface can be turned off without disabling expiry. (SESSION-011)
MIN_WARNING_MINUTES = 0
# Cap the pre-expiration warning window so it can never approach the idle window itself. (SESSION-011)
MAX_WARNING_MINUTES = 10

# Default policy: 30-minute idle logout, 12-hour absolute cap, and a stricter 15-minute idle window for admins.
DEFAULT_SESSION = {
    # Stamp the schema version so reads and writes stay aligned with the storage provider contract.
    "schema_version": SCHEMA_VERSION,
    # Enable idle enforcement by default so existing behavior is preserved until an owner disables it. (SESSION-011)
    "enabled": True,
    # Sign a registered account out after this many minutes without observed activity.
    "idle_timeout_minutes": 30,
    # Force re-authentication this many hours after login regardless of continued activity.
    "absolute_timeout_hours": 12,
    # Apply a stricter idle window to admin and owner accounts when enabled.
    "admin_stricter": True,
    # Use this shorter idle window for admin and owner accounts when the stricter policy is enabled.
    "admin_idle_timeout_minutes": 15,
    # Warn a signed-in account this many minutes before idle expiry so it can extend the session. (SESSION-011)
    "warning_minutes": 2,
    # Record when the policy was last changed so the Admin surface can show provenance. (SESSION-010)
    "updated_at": None,
    # Record the opaque owner id that last changed the policy without exposing any secret. (SESSION-010)
    "updated_by": None,
}


# Coerce and clamp one integer field into its reviewed range, falling back when the value is unusable.
def _clamp_int(value, low: int, high: int, fallback: int) -> int:
    # Start protected coercion so a malformed stored or supplied value cannot raise.
    try:
        # Parse the candidate into an integer number of minutes or hours.
        number = int(value)
    # Treat missing, non-numeric, and malformed values as the safe fallback.
    except (TypeError, ValueError):
        # Return the reviewed default rather than propagating a bad value.
        return fallback
    # Clamp the parsed number into the reviewed inclusive range.
    return max(low, min(high, number))


# Read the merged, re-clamped session-timeout policy document from the active storage provider.
def session_settings() -> dict:
    # Read the provider-backed policy document, defaulting to a fresh copy when absent.
    state = get_storage_provider().read_document(SESSION_DOCUMENT_KEY, DEFAULT_SESSION.copy)
    # Replace a corrupt non-dictionary document with the reviewed defaults.
    if not isinstance(state, dict):
        # Reset to a safe default policy before merging.
        state = DEFAULT_SESSION.copy()
    # Merge stored values over the defaults so newly added fields always have a value.
    merged = DEFAULT_SESSION.copy(); merged.update(state)
    # Re-clamp on read so a hand-edited or legacy document can never weaken the policy below its bounds.
    merged["idle_timeout_minutes"] = _clamp_int(merged.get("idle_timeout_minutes"), MIN_IDLE_MINUTES, MAX_IDLE_MINUTES, DEFAULT_SESSION["idle_timeout_minutes"])
    # Re-clamp the absolute lifetime into the reviewed hour range.
    merged["absolute_timeout_hours"] = _clamp_int(merged.get("absolute_timeout_hours"), MIN_ABSOLUTE_HOURS, MAX_ABSOLUTE_HOURS, DEFAULT_SESSION["absolute_timeout_hours"])
    # Re-clamp the admin idle window into the reviewed minute range.
    merged["admin_idle_timeout_minutes"] = _clamp_int(merged.get("admin_idle_timeout_minutes"), MIN_IDLE_MINUTES, MAX_IDLE_MINUTES, DEFAULT_SESSION["admin_idle_timeout_minutes"])
    # Coerce the stricter-admin flag to a strict boolean.
    merged["admin_stricter"] = bool(merged.get("admin_stricter", True))
    # Coerce the idle-enforcement enable flag to a strict boolean, defaulting to enabled. (SESSION-011)
    merged["enabled"] = bool(merged.get("enabled", True))
    # Re-clamp the pre-expiration warning window into its own reviewed minute range. (SESSION-011)
    merged["warning_minutes"] = _clamp_int(merged.get("warning_minutes"), MIN_WARNING_MINUTES, MAX_WARNING_MINUTES, DEFAULT_SESSION["warning_minutes"])
    # Keep the warning window strictly shorter than the effective idle window so a warning can never outlast the session.
    merged["warning_minutes"] = min(merged["warning_minutes"], max(0, merged["idle_timeout_minutes"] - 1))
    # Preserve a valid last-updated timestamp string, resetting any malformed value to absent.
    merged["updated_at"] = merged.get("updated_at") if isinstance(merged.get("updated_at"), str) else None
    # Preserve a bounded opaque actor string, resetting any malformed or oversized value to absent.
    merged["updated_by"] = merged.get("updated_by") if (isinstance(merged.get("updated_by"), str) and 0 < len(merged.get("updated_by")) <= MAX_ACTOR_LENGTH) else None
    # Stamp the current schema version consistent with the peer settings modules.
    merged["schema_version"] = SCHEMA_VERSION
    # Return the fully validated policy document.
    return merged


# Coerce and bound the opaque actor identifier recorded alongside a policy change. (SESSION-010)
def _clean_actor(actor_id) -> str | None:
    # Ignore any non-string or empty actor so provenance stays optional rather than malformed.
    if not isinstance(actor_id, str) or not actor_id.strip():
        # Record no actor rather than an unusable value.
        return None
    # Return the bounded actor identifier without interpreting or expanding it.
    return actor_id.strip()[:MAX_ACTOR_LENGTH]


# Persist a clamped update to the session-timeout policy and return the stored document.
def save_session_settings(updates: dict, *, actor_id=None) -> dict:
    # Start from the current validated policy so unspecified fields are preserved.
    state = session_settings()
    # Apply each supplied numeric field through the same clamp used on read.
    for key in ("idle_timeout_minutes", "absolute_timeout_hours", "admin_idle_timeout_minutes", "warning_minutes"):
        # Only touch fields the caller actually supplied.
        if key in (updates or {}):
            # Select the reviewed range for each independently-bounded field.
            if key == "absolute_timeout_hours":
                # Use the reviewed absolute-hours range.
                low, high = MIN_ABSOLUTE_HOURS, MAX_ABSOLUTE_HOURS
            elif key == "warning_minutes":
                # Use the dedicated warning-window range.
                low, high = MIN_WARNING_MINUTES, MAX_WARNING_MINUTES
            else:
                # Use the shared idle-minute range for both idle fields.
                low, high = MIN_IDLE_MINUTES, MAX_IDLE_MINUTES
            # Clamp the supplied value, keeping the existing value as the fallback.
            state[key] = _clamp_int(updates[key], low, high, state[key])
    # Apply the stricter-admin flag when supplied.
    if "admin_stricter" in (updates or {}):
        # Coerce the supplied flag to a strict boolean.
        state["admin_stricter"] = bool(updates["admin_stricter"])
    # Apply the idle-enforcement enable flag when supplied. (SESSION-011)
    if "enabled" in (updates or {}):
        # Coerce the supplied flag to a strict boolean.
        state["enabled"] = bool(updates["enabled"])
    # Keep the warning window strictly shorter than the effective idle window after any change. (SESSION-011)
    state["warning_minutes"] = min(_clamp_int(state.get("warning_minutes"), MIN_WARNING_MINUTES, MAX_WARNING_MINUTES, DEFAULT_SESSION["warning_minutes"]), max(0, state["idle_timeout_minutes"] - 1))
    # Stamp the durable last-updated timestamp so the Admin surface can show provenance. (SESSION-010)
    state["updated_at"] = utc_now()
    # Record the opaque owner actor without exposing any secret or session material. (SESSION-010)
    state["updated_by"] = _clean_actor(actor_id)
    # Persist the validated policy document through the active storage provider.
    get_storage_provider().write_document(SESSION_DOCUMENT_KEY, state)
    # Return the stored policy so callers echo the persisted values.
    return state


# Resolve the effective idle and absolute limits in seconds for one account, honoring the stricter admin policy.
def resolve_timeout_seconds(is_admin_user: bool) -> tuple[int, int]:
    # Read the current validated policy once.
    settings = session_settings()
    # Convert the absolute lifetime to seconds for direct comparison against elapsed time.
    absolute_seconds = settings["absolute_timeout_hours"] * 3600
    # Disabling the policy suspends only idle enforcement; the absolute cap always remains in force. (SESSION-011)
    if not settings["enabled"]:
        # Return the absolute limit for both bounds so no request is ever rejected for idleness alone.
        return absolute_seconds, absolute_seconds
    # Choose the stricter admin idle window only when the policy enables it for a privileged account.
    idle_minutes = settings["admin_idle_timeout_minutes"] if (settings["admin_stricter"] and is_admin_user) else settings["idle_timeout_minutes"]
    # Convert the selected idle window to seconds.
    idle_seconds = idle_minutes * 60
    # Never let the idle window exceed the absolute cap, which must always win.
    idle_seconds = min(idle_seconds, absolute_seconds)
    # Return the effective idle and absolute limits in seconds.
    return idle_seconds, absolute_seconds


# Resolve the pre-expiration warning window in seconds for a signed-in account. (SESSION-011)
def warning_seconds(is_admin_user: bool) -> int:
    # Read the current validated policy once.
    settings = session_settings()
    # Report no warning window when idle enforcement is disabled, since there is no idle expiry to warn about.
    if not settings["enabled"]:
        # Return zero so callers render no warning affordance.
        return 0
    # Convert the reviewed warning window to seconds for direct client comparison.
    return settings["warning_minutes"] * 60
