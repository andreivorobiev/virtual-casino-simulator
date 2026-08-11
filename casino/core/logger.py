# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Sanitized application and diagnostic event logging.
import traceback as tb
from pathlib import Path
from casino.config import LOG_DIR
from casino.core.clock import utc_now, date_stamp
from casino.core.state_store import append_jsonl

# Define the _path function used by this module.
def _path(kind: str) -> Path:
    return LOG_DIR / f"{kind}-{date_stamp()}.jsonl"

# Define the log function used by this module.
def log(level: str, event: str, **fields) -> dict:
    # Set rec to the value needed for the next operation.
    rec = {"ts": utc_now(), "level": level.upper(), "event": event, **fields}
    append_jsonl(_path("app"), rec)
    return rec

# Define the info function used by this module.
def info(event: str, **fields) -> dict:
    return log("INFO", event, **fields)

# Define the warning function used by this module.
def warning(event: str, **fields) -> dict:
    return log("WARN", event, **fields)

# Define the error function used by this module.
def error(event: str, exc: BaseException | None = None, **fields) -> dict:
    # Set rec to the value needed for the next operation.
    rec = {"ts": utc_now(), "level": "ERROR", "event": event, **fields}
    if exc is not None:
        # Set rec["message"] to the value needed for the next operation.
        rec["message"] = str(exc)
        # Set rec["traceback"] to the value needed for the next operation.
        rec["traceback"] = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
    append_jsonl(_path("errors"), rec)
    return rec

# Define the client function used by this module.
def client(event: str, **fields) -> dict:
    # Set rec to the value needed for the next operation.
    rec = {"ts": utc_now(), "level": "CLIENT", "event": event, **fields}
    append_jsonl(_path("client"), rec)
    return rec

# Define the recent function used by this module.
def recent(kind: str = "app", limit: int = 50) -> list[dict]:
    # Set path to the value needed for the next operation.
    path = _path(kind)
    if not path.exists():
        return []
    # Set lines to the value needed for the next operation.
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    # Set out to the value needed for the next operation.
    out = []
    import json
    for line in lines:
        # Start protected logic so failures can be handled safely.
        try:
            out.append(json.loads(line))
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Intentionally leave this block empty.
            pass
    return out
