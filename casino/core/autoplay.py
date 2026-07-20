# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from __future__ import annotations
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json, write_json
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError, NotFoundError

# Set AUTOPLAY_PATH to the value needed for the next operation.
AUTOPLAY_PATH = DATA_DIR / "autoplay.json"

# Set VALID_SPEEDS to the value needed for the next operation.
VALID_SPEEDS = {"slow", "medium", "fast"}
# Set VALID_STATUSES to the value needed for the next operation.
VALID_STATUSES = {"starting", "running", "pause_requested", "paused", "stop_requested", "stopped", "completed", "error"}


# Define the default_state function used by this module.
def default_state() -> dict:
    # Return the computed value to the caller.
    return {"schema_version": SCHEMA_VERSION, "sessions": []}


# Define the load_state function used by this module.
def load_state() -> dict:
    # Set st to the value needed for the next operation.
    st = read_json(AUTOPLAY_PATH, default_state)
    # Branch when the following condition is true.
    if not isinstance(st, dict) or "sessions" not in st:
        # Set st to the value needed for the next operation.
        st = default_state()
    # Return the computed value to the caller.
    return st


# Define the save_state function used by this module.
def save_state(st: dict) -> None:
    # Set st["schema_version"] to the value needed for the next operation.
    st["schema_version"] = SCHEMA_VERSION
    # Execute this statement as part of the module's documented control flow.
    write_json(AUTOPLAY_PATH, st)


# Define the list_sessions function used by this module.
def list_sessions(active_only: bool = False) -> list[dict]:
    # Set sessions to the value needed for the next operation.
    sessions = load_state().get("sessions", [])
    # Branch when the following condition is true.
    if active_only:
        # Return the computed value to the caller.
        return [s for s in sessions if s.get("status") in ("starting", "running", "pause_requested", "paused", "stop_requested")]
    # Return the computed value to the caller.
    return sessions[-200:]

# Define the get_session function used by this module.
def get_session(autoplay_id: str) -> dict:
    # Return the computed value to the caller.
    return _find(load_state(), autoplay_id)


# Define the start function used by this module.
def start(game_id: str, player_id: str = "human", speed: str = "medium", round_limit: int = 25, plan: dict | None = None, limits: dict | None = None) -> dict:
    # Branch when the following condition is true.
    if speed not in VALID_SPEEDS:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Autoplay speed must be slow, medium, or fast")
    # Set session to the value needed for the next operation.
    session = {
        # Execute this statement as part of the module's documented control flow.
        "autoplay_id": new_id("auto"),
        # Execute this statement as part of the module's documented control flow.
        "game_id": game_id,
        # Execute this statement as part of the module's documented control flow.
        "player_id": player_id,
        # Execute this statement as part of the module's documented control flow.
        "status": "running",
        # Execute this statement as part of the module's documented control flow.
        "speed": speed,
        # Execute this statement as part of the module's documented control flow.
        "round_limit": int(round_limit or 1),
        # Execute this statement as part of the module's documented control flow.
        "rounds_completed": 0,
        # Execute this statement as part of the module's documented control flow.
        "stop_requested": False,
        # Execute this statement as part of the module's documented control flow.
        "plan": plan or {},
        # Execute this statement as part of the module's documented control flow.
        "limits": limits or {},
        # Execute this statement as part of the module's documented control flow.
        "started_at": utc_now(),
        # Execute this statement as part of the module's documented control flow.
        "updated_at": utc_now(),
        # Execute this statement as part of the module's documented control flow.
        "last_action_at": None,
        # Execute this statement as part of the module's documented control flow.
        "events": [{"ts": utc_now(), "event": "autoplay_started"}],
    }
    # Set st to the value needed for the next operation.
    st = load_state()
    # Execute this statement as part of the module's documented control flow.
    st.setdefault("sessions", []).append(session)
    # Set st["sessions"] to the value needed for the next operation.
    st["sessions"] = st["sessions"][-200:]
    # Execute this statement as part of the module's documented control flow.
    save_state(st)
    # Return the computed value to the caller.
    return session


# Define the _find function used by this module.
def _find(st: dict, autoplay_id: str) -> dict:
    # Iterate through the collection to process each item.
    for s in st.get("sessions", []):
        # Branch when the following condition is true.
        if s.get("autoplay_id") == autoplay_id:
            # Return the computed value to the caller.
            return s
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Autoplay session {autoplay_id} was not found")


# Define the update function used by this module.
def update(autoplay_id: str, **fields) -> dict:
    # Set st to the value needed for the next operation.
    st = load_state()
    # Set s to the value needed for the next operation.
    s = _find(st, autoplay_id)
    # Iterate through the collection to process each item.
    for k, v in fields.items():
        # Branch when the following condition is true.
        if k == "status" and v not in VALID_STATUSES:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Illegal autoplay status")
        # Set s[k] to the value needed for the next operation.
        s[k] = v
    # Set s["updated_at"] to the value needed for the next operation.
    s["updated_at"] = utc_now()
    # Execute this statement as part of the module's documented control flow.
    save_state(st)
    # Return the computed value to the caller.
    return s


# Define the stop function used by this module.
def stop(autoplay_id: str) -> dict:
    # Set st to the value needed for the next operation.
    st = load_state()
    # Set s to the value needed for the next operation.
    s = _find(st, autoplay_id)
    # Set s["stop_requested"] to the value needed for the next operation.
    s["stop_requested"] = True
    # Set s["status"] to the value needed for the next operation.
    s["status"] = "stop_requested" if s.get("status") == "running" else "stopped"
    # Execute this statement as part of the module's documented control flow.
    s.setdefault("events", []).append({"ts": utc_now(), "event": "stop_requested"})
    # Set s["updated_at"] to the value needed for the next operation.
    s["updated_at"] = utc_now()
    # Execute this statement as part of the module's documented control flow.
    save_state(st)
    # Return the computed value to the caller.
    return s


# Define the finish_stop function used by this module.
def finish_stop(autoplay_id: str) -> dict:
    # Return the computed value to the caller.
    return update(autoplay_id, status="stopped", stop_requested=True)


# Define the complete function used by this module.
def complete(autoplay_id: str) -> dict:
    # Return the computed value to the caller.
    return update(autoplay_id, status="completed")


# Define the tick function used by this module.
def tick(autoplay_id: str) -> dict:
    # Set st to the value needed for the next operation.
    st = load_state()
    # Set s to the value needed for the next operation.
    s = _find(st, autoplay_id)
    # Set s["rounds_completed"] to the value needed for the next operation.
    s["rounds_completed"] = int(s.get("rounds_completed", 0)) + 1
    # Set s["last_action_at"] to the value needed for the next operation.
    s["last_action_at"] = utc_now()
    # Execute this statement as part of the module's documented control flow.
    s.setdefault("events", []).append({"ts": utc_now(), "event": "autoplay_tick", "rounds_completed": s["rounds_completed"]})
    # Set s["updated_at"] to the value needed for the next operation.
    s["updated_at"] = utc_now()
    # Execute this statement as part of the module's documented control flow.
    save_state(st)
    # Return the computed value to the caller.
    return s


# Define the stop_all function used by this module.
def stop_all() -> list[dict]:
    # Set st to the value needed for the next operation.
    st = load_state(); out=[]
    # Iterate through the collection to process each item.
    for s in st.get("sessions", []):
        # Branch when the following condition is true.
        if s.get("status") in ("starting", "running", "pause_requested", "paused", "stop_requested"):
            # Set s["stop_requested"] to the value needed for the next operation.
            s["stop_requested"] = True; s["status"] = "stop_requested"; s["updated_at"] = utc_now(); s.setdefault("events", []).append({"ts": utc_now(), "event":"stop_all_requested"}); out.append(s)
    # Execute this statement as part of the module's documented control flow.
    save_state(st); return out

# Irreversibly stop every active control-plane session owned by one disposable player. (issue #317)
def stop_for_player(player_id: str) -> list[dict]:
    # Load the bounded autoplay registry before applying the player-scoped teardown.
    state = load_state()
    # Collect changed sessions for focused lifecycle evidence without exposing other players.
    stopped = []
    # Inspect every retained session because one guest may have used multiple compatible games.
    for session in state.get("sessions", []):
        # Ignore other players and already-terminal autoplay records.
        if session.get("player_id") != player_id or session.get("status") not in ("starting", "running", "pause_requested", "paused", "stop_requested"):
            # Continue without mutating unrelated or completed control-plane state.
            continue
        # Prevent any new atomic action from starting after guest teardown.
        session["stop_requested"] = True
        # Mark the server registration terminal because the owning principal can never authenticate again.
        session["status"] = "stopped"
        # Record one bounded lifecycle event without credentials or analytics identifiers.
        session.setdefault("events", []).append({"ts": utc_now(), "event": "player_session_ended"})
        # Refresh the server-owned activity marker for Admin diagnostics.
        session["updated_at"] = utc_now()
        # Return only the changed session objects to the trusted lifecycle caller.
        stopped.append(session)
    # Persist once so multiple active sessions end atomically within the local provider boundary.
    save_state(state)
    # Return the changed rows for focused tests and no public response.
    return stopped
