# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import future annotations so the tuple return hint parses on the supported interpreter.
from __future__ import annotations
# Import the shared schema version so the stored document stays consistent with peer settings docs.
from casino.config import SCHEMA_VERSION
# Import the configured storage provider so the policy persists in both JSON and MySQL modes.
from casino.core.storage import get_storage_provider

# Provider document key for the global registered-account session-timeout policy. (SESSION-008)
SESSION_DOCUMENT_KEY = "settings/session"

# Reviewed bounds so a stored or supplied value can never disable expiry or exceed the absolute ceiling.
MIN_IDLE_MINUTES = 1
# Cap the idle window at the 24-hour absolute ceiling so idle can never outlast the absolute limit.
MAX_IDLE_MINUTES = 1440
# Require at least a one-hour absolute lifetime so a misconfiguration cannot lock everyone out instantly.
MIN_ABSOLUTE_HOURS = 1
# Match the reviewed 24-hour absolute session ceiling enforced elsewhere by MAX_SESSION_TTL_SECONDS.
MAX_ABSOLUTE_HOURS = 24

# Default policy: 30-minute idle logout, 12-hour absolute cap, and a stricter 15-minute idle window for admins.
DEFAULT_SESSION = {
    # Stamp the schema version so reads and writes stay aligned with the storage provider contract.
    "schema_version": SCHEMA_VERSION,
    # Sign a registered account out after this many minutes without observed activity.
    "idle_timeout_minutes": 30,
    # Force re-authentication this many hours after login regardless of continued activity.
    "absolute_timeout_hours": 12,
    # Apply a stricter idle window to admin and owner accounts when enabled.
    "admin_stricter": True,
    # Use this shorter idle window for admin and owner accounts when the stricter policy is enabled.
    "admin_idle_timeout_minutes": 15,
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
    # Stamp the current schema version consistent with the peer settings modules.
    merged["schema_version"] = SCHEMA_VERSION
    # Return the fully validated policy document.
    return merged


# Persist a clamped update to the session-timeout policy and return the stored document.
def save_session_settings(updates: dict) -> dict:
    # Start from the current validated policy so unspecified fields are preserved.
    state = session_settings()
    # Apply each supplied numeric field through the same clamp used on read.
    for key in ("idle_timeout_minutes", "absolute_timeout_hours", "admin_idle_timeout_minutes"):
        # Only touch fields the caller actually supplied.
        if key in (updates or {}):
            # Select the reviewed range for the absolute-hours field or the shared minute range otherwise.
            low, high = (MIN_ABSOLUTE_HOURS, MAX_ABSOLUTE_HOURS) if key == "absolute_timeout_hours" else (MIN_IDLE_MINUTES, MAX_IDLE_MINUTES)
            # Clamp the supplied value, keeping the existing value as the fallback.
            state[key] = _clamp_int(updates[key], low, high, state[key])
    # Apply the stricter-admin flag when supplied.
    if "admin_stricter" in (updates or {}):
        # Coerce the supplied flag to a strict boolean.
        state["admin_stricter"] = bool(updates["admin_stricter"])
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
    # Choose the stricter admin idle window only when the policy enables it for a privileged account.
    idle_minutes = settings["admin_idle_timeout_minutes"] if (settings["admin_stricter"] and is_admin_user) else settings["idle_timeout_minutes"]
    # Convert the selected idle window to seconds.
    idle_seconds = idle_minutes * 60
    # Never let the idle window exceed the absolute cap, which must always win.
    idle_seconds = min(idle_seconds, absolute_seconds)
    # Return the effective idle and absolute limits in seconds.
    return idle_seconds, absolute_seconds
