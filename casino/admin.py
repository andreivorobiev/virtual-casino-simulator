# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, GAME_DATA_DIR, LOG_DIR, DOCS_DIR, APP_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.module_versions import list_module_revisions
# Import required dependency so this module can use its public functions or constants.
from casino.core import players, ledger, history, logger, autoplay, settings
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json
# Import required dependency so this module can use its public functions or constants.
from casino.bots import profiles

# Set REQ_PATH to the value needed for the next operation.
REQ_PATH = DOCS_DIR / "requirements.json"
# Set TEST_RESULTS_PATH to the value needed for the next operation.
TEST_RESULTS_PATH = LOG_DIR / "test-runs" / "latest_results.json"


# Define the _read_json_file function used by this module.
def _read_json_file(path: Path, default):
    # Start protected logic so failures can be handled safely.
    try:
        # Branch when the following condition is true.
        if path.exists():
            # Return the computed value to the caller.
            return json.loads(path.read_text(encoding="utf-8"))
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Intentionally leave this block empty.
        pass
    # Return the computed value to the caller.
    return default


# Define the requirements function used by this module.
def requirements():
    # Return the computed value to the caller.
    return _read_json_file(REQ_PATH, {"requirements": []})


# Define the game_states function used by this module.
def game_states():
    # Set states to the value needed for the next operation.
    states = {}
    # Branch when the following condition is true.
    if GAME_DATA_DIR.exists():
        # Iterate through the collection to process each item.
        for p in sorted(GAME_DATA_DIR.glob("*.json")):
            # Set states[p.stem] to the value needed for the next operation.
            states[p.stem] = {"path": str(p), "state": _read_json_file(p, {})}
    # Return the computed value to the caller.
    return states


# Define the overview function used by this module.
def overview():
    # Set reqs to the value needed for the next operation.
    reqs = requirements().get("requirements", [])
    # Set counts to the value needed for the next operation.
    counts = {}
    # Iterate through the collection to process each item.
    for r in reqs:
        # Set counts[r.get("status", "UNKNOWN")] to the value needed for the next operation.
        counts[r.get("status", "UNKNOWN")] = counts.get(r.get("status", "UNKNOWN"), 0) + 1
    # Return the computed value to the caller.
    return {
        # Execute this statement as part of the module's documented control flow.
        "app_version": APP_VERSION,
        # Execute this statement as part of the module's documented control flow.
        "module_revisions": list_module_revisions(),
        # Execute this statement as part of the module's documented control flow.
        "players": players.list_players(),
        # Execute this statement as part of the module's documented control flow.
        "bots": profiles.list_bots(),
        # Execute this statement as part of the module's documented control flow.
        "bot_capabilities": profiles.capabilities(),
        # Set "autoplay_sessions": autoplay.list_sessions(active_only to the value needed for the next operation.
        "autoplay_sessions": autoplay.list_sessions(active_only=False),
        # Set "recent_ledger": ledger.read_recent(limit to the value needed for the next operation.
        "recent_ledger": ledger.read_recent(limit=50),
        # Execute this statement as part of the module's documented control flow.
        "recent_history": history.recent_history(50),
        # Execute this statement as part of the module's documented control flow.
        "logs": {"app": logger.recent("app", 50), "errors": logger.recent("errors", 50), "client": logger.recent("client", 50)},
        # Execute this statement as part of the module's documented control flow.
        "requirement_counts": counts,
        # Execute this statement as part of the module's documented control flow.
        "test_results": _read_json_file(TEST_RESULTS_PATH, {}),
        # Execute this statement as part of the module's documented control flow.
        "audio_settings": settings.audio_settings(),
    }


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/overview")
    # Define the admin_overview function used by this module.
    def admin_overview(body, query):
        # Return the computed value to the caller.
        return overview()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/dashboard")
    # Define the admin_dashboard function used by this module.
    def admin_dashboard(body, query):
        # Return the computed value to the caller.
        return overview()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/modules")
    # Define the admin_modules function used by this module.
    def admin_modules(body, query):
        # Return the computed value to the caller.
        return {"modules": list_module_revisions()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/requirements")
    # Define the admin_requirements function used by this module.
    def admin_requirements(body, query):
        # Return the computed value to the caller.
        return requirements()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/game-states")
    # Define the admin_states function used by this module.
    def admin_states(body, query):
        # Return the computed value to the caller.
        return {"states": game_states()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/logs")
    # Define the admin_logs function used by this module.
    def admin_logs(body, query):
        # Set kind to the value needed for the next operation.
        kind = query.get("kind", "app")
        # Set limit to the value needed for the next operation.
        limit = int(query.get("limit", 200))
        # Set logs to the value needed for the next operation.
        logs = logger.recent(kind, limit)
        # Set level to the value needed for the next operation.
        level = query.get("level")
        # Set game to the value needed for the next operation.
        game = query.get("game")
        # Set text to the value needed for the next operation.
        text = query.get("q")
        # Branch when the following condition is true.
        if level:
            # Set logs to the value needed for the next operation.
            logs = [r for r in logs if str(r.get("level","")) == level]
        # Branch when the following condition is true.
        if game:
            # Set logs to the value needed for the next operation.
            logs = [r for r in logs if str(r.get("game", r.get("game_id", ""))) == game]
        # Branch when the following condition is true.
        if text:
            # Set logs to the value needed for the next operation.
            logs = [r for r in logs if text.lower() in json.dumps(r).lower()]
        # Return the computed value to the caller.
        return {"kind": kind, "logs": logs}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/ledger")
    # Define the admin_ledger function used by this module.
    def admin_ledger(body, query):
        # Set rows to the value needed for the next operation.
        rows = ledger.read_recent(limit=int(query.get("limit", 500)))
        # Set player_id to the value needed for the next operation.
        player_id = query.get("player_id")
        # Set game to the value needed for the next operation.
        game = query.get("game")
        # Branch when the following condition is true.
        if player_id:
            # Set rows to the value needed for the next operation.
            rows = [r for r in rows if r.get("player_id") == player_id]
        # Branch when the following condition is true.
        if game:
            # Set rows to the value needed for the next operation.
            rows = [r for r in rows if r.get("game") == game]
        # Return the computed value to the caller.
        return {"ledger": rows}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/history")
    # Define the admin_history function used by this module.
    def admin_history(body, query):
        # Return the computed value to the caller.
        return {"history": history.recent_history(int(query.get("limit", 500)), query.get("game") or None)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/test-results")
    # Define the admin_test_results function used by this module.
    def admin_test_results(body, query):
        # Return the computed value to the caller.
        return {"results": _read_json_file(TEST_RESULTS_PATH, {})}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/audio-settings")
    # Define the get_audio function used by this module.
    def get_audio(body, query):
        # Return the computed value to the caller.
        return {"settings": settings.audio_settings()}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/audio-settings")
    # Define the save_audio function used by this module.
    def save_audio(body, query):
        # Return the computed value to the caller.
        return {"settings": settings.save_audio_settings(body)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/autoplay")
    # Define the get_autoplay function used by this module.
    def get_autoplay(body, query):
        # Return the computed value to the caller.
        return {"sessions": autoplay.list_sessions(active_only=False)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/admin/autoplay/stop-all")
    # Define the stop_all_autoplay function used by this module.
    def stop_all_autoplay(body, query):
        # Return the computed value to the caller.
        return {"sessions": autoplay.stop_all()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/admin/bots")
    # Define the admin_bots function used by this module.
    def admin_bots(body, query):
        # Return the computed value to the caller.
        return {"bots": profiles.list_bots(), "capabilities": profiles.capabilities()}
