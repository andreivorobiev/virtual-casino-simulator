# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import csv
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now

# Set HISTORY_FIELDS to the value needed for the next operation.
HISTORY_FIELDS = [
    # Execute this statement as part of the module's documented control flow.
    "timestamp", "game", "round_id", "player_id", "bet_type", "bet_label", "amount", "outcome", "payout", "balance_after", "details_json", "schema_version"
]

# Define the history_path function used by this module.
def history_path() -> Path:
    # Set DATA_DIR.mkdir(parents to the value needed for the next operation.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Return the computed value to the caller.
    return DATA_DIR / "history.csv"

# Define the append_history function used by this module.
def append_history(game: str, round_id: str, player_id: str, bet_type: str, bet_label: str, amount: float, outcome: str, payout: float, balance_after: float, details: dict | None = None) -> None:
    # Set path to the value needed for the next operation.
    path = history_path()
    # Set exists to the value needed for the next operation.
    exists = path.exists()
    # Manage this resource with automatic setup and cleanup.
    with path.open("a", newline="", encoding="utf-8") as f:
        # Set writer to the value needed for the next operation.
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        # Branch when the following condition is true.
        if not exists:
            # Execute this statement as part of the module's documented control flow.
            writer.writeheader()
        # Execute this statement as part of the module's documented control flow.
        writer.writerow({
            # Execute this statement as part of the module's documented control flow.
            "timestamp": utc_now(),
            # Execute this statement as part of the module's documented control flow.
            "game": game,
            # Execute this statement as part of the module's documented control flow.
            "round_id": round_id,
            # Execute this statement as part of the module's documented control flow.
            "player_id": player_id,
            # Execute this statement as part of the module's documented control flow.
            "bet_type": bet_type,
            # Execute this statement as part of the module's documented control flow.
            "bet_label": bet_label,
            # Execute this statement as part of the module's documented control flow.
            "amount": round(float(amount), 2),
            # Execute this statement as part of the module's documented control flow.
            "outcome": outcome,
            # Execute this statement as part of the module's documented control flow.
            "payout": round(float(payout), 2),
            # Execute this statement as part of the module's documented control flow.
            "balance_after": round(float(balance_after), 2),
            # Set "details_json": json.dumps(details or {}, sort_keys to the value needed for the next operation.
            "details_json": json.dumps(details or {}, sort_keys=True),
            # Execute this statement as part of the module's documented control flow.
            "schema_version": SCHEMA_VERSION,
        })

# Define the recent_history function used by this module.
def recent_history(limit: int = 100, game: str | None = None) -> list[dict]:
    # Set path to the value needed for the next operation.
    path = history_path()
    # Branch when the following condition is true.
    if not path.exists():
        # Return the computed value to the caller.
        return []
    # Manage this resource with automatic setup and cleanup.
    with path.open("r", newline="", encoding="utf-8") as f:
        # Set rows to the value needed for the next operation.
        rows = list(csv.DictReader(f))
    # Branch when the following condition is true.
    if game:
        # Set rows to the value needed for the next operation.
        rows = [r for r in rows if r.get("game") == game]
    # Return the computed value to the caller.
    return rows[-limit:]
