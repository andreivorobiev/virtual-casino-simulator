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
# Import a reentrant lock so nested autoplay lifecycle helpers preserve one registry transaction.
from threading import RLock

# Set AUTOPLAY_PATH to the value needed for the next operation.
AUTOPLAY_PATH = DATA_DIR / "autoplay.json"
# Serialize each complete registry read-modify-write transaction inside this application process.
AUTOPLAY_REGISTRY_LOCK = RLock()

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
    # Hold the registry lock so a list cannot observe the middle of a concurrent lifecycle write.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load one complete immutable-on-return registry snapshot.
        sessions = load_state().get("sessions", [])
    # Branch when the following condition is true.
    if active_only:
        # Return the computed value to the caller.
        return [s for s in sessions if s.get("status") in ("starting", "running", "pause_requested", "paused", "stop_requested")]
    # Return the computed value to the caller.
    return sessions[-200:]

# Define the get_session function used by this module.
def get_session(autoplay_id: str) -> dict:
    # Hold the same registry lock used by writers so a newly issued id remains immediately readable.
    with AUTOPLAY_REGISTRY_LOCK:
        # Return the matching row from one complete registry snapshot.
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
    # Serialize the complete append transaction so concurrent starts cannot overwrite sibling session ids.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load the latest registry only after this start owns the transaction.
        st = load_state()
        # Append the newly issued session without losing another request's committed row.
        st.setdefault("sessions", []).append(session)
        # Retain the documented bounded recent-session window.
        st["sessions"] = st["sessions"][-200:]
        # Commit the complete updated registry while this transaction still owns the lock.
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
    # Serialize lookup, mutation, and persistence so sibling lifecycle requests cannot erase each other.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load the latest registry after acquiring transaction ownership.
        st = load_state()
        # Resolve the exact retained session from that transaction snapshot.
        s = _find(st, autoplay_id)
        # Apply only the caller-owned validated lifecycle fields.
        for k, v in fields.items():
            # Reject unrecognized status transitions before mutating the retained row.
            if k == "status" and v not in VALID_STATUSES:
                # Raise an error so invalid input or state is reported explicitly.
                raise ValidationError("Illegal autoplay status")
            # Apply the validated field to the retained session.
            s[k] = v
        # Refresh the server-owned activity timestamp inside the same transaction.
        s["updated_at"] = utc_now()
        # Commit the complete registry before another lifecycle request can load it.
        save_state(st)
    # Return the computed value to the caller.
    return s


# Define the stop function used by this module.
def stop(autoplay_id: str) -> dict:
    # Serialize the complete stop transition with concurrent start, tick, and teardown transactions.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load the latest registry after acquiring transaction ownership.
        st = load_state()
        # Resolve the exact retained session from the latest snapshot.
        s = _find(st, autoplay_id)
        # Prevent the client controller from starting another atomic action.
        s["stop_requested"] = True
        # Preserve an in-flight action while marking every other state terminal.
        s["status"] = "stop_requested" if s.get("status") == "running" else "stopped"
        # Append one bounded server-owned lifecycle event.
        s.setdefault("events", []).append({"ts": utc_now(), "event": "stop_requested"})
        # Refresh the server-owned activity timestamp.
        s["updated_at"] = utc_now()
        # Commit the complete registry before releasing transaction ownership.
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
    # Serialize the complete tick transaction so concurrent sessions retain every server registration.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load the latest registry after acquiring transaction ownership.
        st = load_state()
        # Resolve the exact retained session from that transaction snapshot.
        s = _find(st, autoplay_id)
        # Increment only this session's completed-round counter.
        s["rounds_completed"] = int(s.get("rounds_completed", 0)) + 1
        # Stamp the server-owned action time.
        s["last_action_at"] = utc_now()
        # Append one bounded lifecycle event with the new aggregate count.
        s.setdefault("events", []).append({"ts": utc_now(), "event": "autoplay_tick", "rounds_completed": s["rounds_completed"]})
        # Refresh the server-owned activity timestamp.
        s["updated_at"] = utc_now()
        # Commit the complete registry before releasing transaction ownership.
        save_state(st)
    # Return the computed value to the caller.
    return s


# Define the stop_all function used by this module.
def stop_all() -> list[dict]:
    # Serialize the bulk transition with every individual session lifecycle request.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load one latest complete registry snapshot.
        st = load_state()
        # Collect only rows changed by this bulk request.
        out = []
        # Inspect every retained session inside the transaction.
        for s in st.get("sessions", []):
            # Change only active or already-requested sessions.
            if s.get("status") in ("starting", "running", "pause_requested", "paused", "stop_requested"):
                # Prevent another atomic action from starting.
                s["stop_requested"] = True
                # Preserve the stop-requested lifecycle boundary.
                s["status"] = "stop_requested"
                # Refresh the server-owned activity timestamp.
                s["updated_at"] = utc_now()
                # Append one bounded bulk-stop event.
                s.setdefault("events", []).append({"ts": utc_now(), "event": "stop_all_requested"})
                # Retain the changed row for the trusted caller.
                out.append(s)
        # Commit every bulk transition atomically inside this application process.
        save_state(st)
        # Return only the changed rows.
        return out

# Irreversibly stop every active control-plane session owned by one disposable player. (issue #317)
def stop_for_player(player_id: str) -> list[dict]:
    # Serialize player teardown with every concurrent start, tick, and stop transaction.
    with AUTOPLAY_REGISTRY_LOCK:
        # Load the bounded autoplay registry only after acquiring transaction ownership.
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
