# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import traceback as tb
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from casino.config import LOG_DIR
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now, date_stamp
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import append_jsonl

# Define the _path function used by this module.
def _path(kind: str) -> Path:
    # Return the computed value to the caller.
    return LOG_DIR / f"{kind}-{date_stamp()}.jsonl"

# Define the log function used by this module.
def log(level: str, event: str, **fields) -> dict:
    # Set rec to the value needed for the next operation.
    rec = {"ts": utc_now(), "level": level.upper(), "event": event, **fields}
    # Execute this statement as part of the module's documented control flow.
    append_jsonl(_path("app"), rec)
    # Return the computed value to the caller.
    return rec

# Define the info function used by this module.
def info(event: str, **fields) -> dict:
    # Return the computed value to the caller.
    return log("INFO", event, **fields)

# Define the warning function used by this module.
def warning(event: str, **fields) -> dict:
    # Return the computed value to the caller.
    return log("WARN", event, **fields)

# Define the error function used by this module.
def error(event: str, exc: BaseException | None = None, **fields) -> dict:
    # Set rec to the value needed for the next operation.
    rec = {"ts": utc_now(), "level": "ERROR", "event": event, **fields}
    # Branch when the following condition is true.
    if exc is not None:
        # Set rec["message"] to the value needed for the next operation.
        rec["message"] = str(exc)
        # Set rec["traceback"] to the value needed for the next operation.
        rec["traceback"] = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
    # Execute this statement as part of the module's documented control flow.
    append_jsonl(_path("errors"), rec)
    # Return the computed value to the caller.
    return rec

# Define the client function used by this module.
def client(event: str, **fields) -> dict:
    # Set rec to the value needed for the next operation.
    rec = {"ts": utc_now(), "level": "CLIENT", "event": event, **fields}
    # Execute this statement as part of the module's documented control flow.
    append_jsonl(_path("client"), rec)
    # Return the computed value to the caller.
    return rec

# Define the recent function used by this module.
def recent(kind: str = "app", limit: int = 50) -> list[dict]:
    # Set path to the value needed for the next operation.
    path = _path(kind)
    # Branch when the following condition is true.
    if not path.exists():
        # Return the computed value to the caller.
        return []
    # Set lines to the value needed for the next operation.
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    # Set out to the value needed for the next operation.
    out = []
    # Import required dependency so this module can use its public functions or constants.
    import json
    # Iterate through the collection to process each item.
    for line in lines:
        # Start protected logic so failures can be handled safely.
        try:
            # Execute this statement as part of the module's documented control flow.
            out.append(json.loads(line))
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Intentionally leave this block empty.
            pass
    # Return the computed value to the caller.
    return out
