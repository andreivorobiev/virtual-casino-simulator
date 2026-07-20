"""De-identified guest-trial telemetry retained for the Admin Guest Trials section. (issue #317)"""

# Import required dependency so this module can use its public functions or constants.
from datetime import datetime, timezone

# Import the shared data root so analytics live beside other governed runtime state.
from casino.config import DATA_DIR, SCHEMA_VERSION
# Import the shared clock so analytics timestamps match session and ledger records.
from casino.core.clock import utc_now
# Import the shared id helper so analytics identifiers stay bounded and random.
from casino.core.ids import new_id
# Import atomic JSON persistence so concurrent guest activity cannot lose records.
from casino.core.state_store import read_json, update_json

# Store the de-identified trial summary document path in its own analytics namespace.
TRIALS_PATH = DATA_DIR / "analytics" / "guest_trials.json"
# Retain at most this many trial summaries across the single-node preview.
MAX_TRIALS = 500
# Suppress activity-touch writes when the last event is newer than this many seconds.
TOUCH_MIN_SECONDS = 60

# Build a new empty de-identified trials document.
def default_trials() -> dict:
    # Return the canonical schema-stamped container with no trial rows.
    return {"schema_version": SCHEMA_VERSION, "trials": []}

# Parse one stored ISO timestamp into an aware datetime for window math.
def _parse(value: str) -> datetime:
    # Convert the shared Z suffix into an offset the standard parser accepts.
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

# Record the start of one guest trial and return its random analytics identifier.
def record_started() -> str:
    # Mint a random analytics id unrelated to the guest's session cookie or player id.
    analytics_id = new_id("gtrial")
    # Capture one timestamp for both the start and first activity marker.
    now = utc_now()
    # Define the atomic mutation appending the new de-identified summary row.
    def mutate(state: dict) -> dict:
        # Normalize malformed persisted state into the canonical container.
        if not isinstance(state, dict) or "trials" not in state:
            state = default_trials()
        # Append a summary holding no user, player, session, or network identifiers.
        state.setdefault("trials", []).append({"analytics_id": analytics_id, "started_at": now, "last_event_at": now, "ended_at": None, "end_reason": None, "duration_seconds": None})
        # Drop the oldest rows beyond the bounded retention cap.
        state["trials"] = state["trials"][-MAX_TRIALS:]
        # Return the mutated document for atomic persistence.
        return state
    # Persist the started trial atomically beside other analytics writes.
    update_json(TRIALS_PATH, mutate, default_trials)
    # Return the analytics id so the caller can bind it one-way onto the guest record.
    return analytics_id

# Record server-observed guest activity for the Admin active-now window.
def record_event(analytics_id: str) -> None:
    # Ignore callers without a bound analytics id so registered users never write here.
    if not analytics_id:
        # Return without touching the analytics store.
        return
    # Capture the observation instant once for the write decision and the update.
    now = utc_now()
    # Define the atomic mutation refreshing the trial's last-activity marker.
    def mutate(state: dict) -> dict:
        # Walk the bounded trial rows to find the active summary.
        for trial in state.get("trials", []):
            # Match the caller's analytics id against open trials only.
            if trial.get("analytics_id") == analytics_id and not trial.get("ended_at"):
                # Skip the write when the marker is fresh so request paths stay cheap.
                if (_parse(now) - _parse(trial.get("last_event_at") or trial.get("started_at"))).total_seconds() >= TOUCH_MIN_SECONDS:
                    # Refresh the last server-observed activity marker.
                    trial["last_event_at"] = now
        # Return the mutated document for atomic persistence.
        return state
    # Persist the refreshed marker atomically.
    update_json(TRIALS_PATH, mutate, default_trials)

# Record the irreversible end of one guest trial with its reason.
def record_ended(analytics_id: str, reason: str = "ended") -> None:
    # Ignore callers without a bound analytics id.
    if not analytics_id:
        # Return without touching the analytics store.
        return
    # Capture the end instant for duration math.
    now = utc_now()
    # Define the atomic mutation closing the trial summary.
    def mutate(state: dict) -> dict:
        # Walk the bounded trial rows to find the open summary.
        for trial in state.get("trials", []):
            # Close only the matching open trial exactly once.
            if trial.get("analytics_id") == analytics_id and not trial.get("ended_at"):
                # Stamp the end time for the retained non-resumable summary.
                trial["ended_at"] = now
                # Record the bounded end reason for the Admin funnel view.
                trial["end_reason"] = reason if reason in ("ended", "expired", "revoked") else "ended"
                # Record the completed duration in whole seconds.
                trial["duration_seconds"] = max(0, int((_parse(now) - _parse(trial.get("started_at") or now)).total_seconds()))
                # Refresh the final activity marker to the end instant.
                trial["last_event_at"] = now
        # Return the mutated document for atomic persistence.
        return state
    # Persist the closed summary atomically.
    update_json(TRIALS_PATH, mutate, default_trials)

# Build the Admin Guest Trials summary from the retained de-identified rows.
def summary(active_window_seconds: int = 300, recent_limit: int = 25) -> dict:
    # Read the bounded analytics document without mutating it.
    state = read_json(TRIALS_PATH, default_trials)
    # Normalize malformed persisted state into an empty container.
    trials = state.get("trials", []) if isinstance(state, dict) else []
    # Capture one comparison instant for the active-now window.
    now = _parse(utc_now())
    # Count trials whose last server event falls inside the configured active window.
    active_now = sum(1 for trial in trials if not trial.get("ended_at") and (now - _parse(trial.get("last_event_at") or trial.get("started_at"))).total_seconds() <= active_window_seconds)
    # Count ended trials by their bounded end reason for the funnel tiles.
    ended = sum(1 for trial in trials if trial.get("end_reason") == "ended")
    # Count expired trials separately so lifecycle cleanup stays visible.
    expired = sum(1 for trial in trials if trial.get("end_reason") == "expired")
    # Return totals plus the newest de-identified rows for the Admin table.
    return {"started_total": len(trials), "active_now": active_now, "ended_total": ended, "expired_total": expired, "active_window_seconds": active_window_seconds, "recent": list(reversed(trials[-recent_limit:]))}
