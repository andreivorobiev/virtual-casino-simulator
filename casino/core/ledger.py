# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import append_jsonl
# Import required dependency so this module can use its public functions or constants.
from casino.core import players
# Import required dependency so this module can use its public functions or constants.
from casino.errors import InsufficientFundsError, ValidationError

# Set LEDGER_PATH to the value needed for the next operation.
LEDGER_PATH = DATA_DIR / "ledger.jsonl"

# Define the transact function used by this module.
def transact(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Set amount to the value needed for the next operation.
    amount = round(float(amount), 2)
    # Branch when the following condition is true.
    if amount == 0:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Ledger transaction amount cannot be zero")
    # Set before_player to the value needed for the next operation.
    before_player = players.get_player(player_id)
    # Set before to the value needed for the next operation.
    before = round(float(before_player.get("balance", 0)), 2)
    # Set after to the value needed for the next operation.
    after = round(before + amount, 2)
    # Branch when the following condition is true.
    if after < -1e-9:
        # Raise an error so invalid input or state is reported explicitly.
        raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
    # Define the upd function used by this module.
    def upd(p):
        # Set p["balance"] to the value needed for the next operation.
        p["balance"] = after
    # Set after_player to the value needed for the next operation.
    after_player = players.update_player(player_id, upd)
    # Set event to the value needed for the next operation.
    event = {
        # Execute this statement as part of the module's documented control flow.
        "ts": utc_now(),
        # Execute this statement as part of the module's documented control flow.
        "ledger_id": new_id("led"),
        # Execute this statement as part of the module's documented control flow.
        "player_id": player_id,
        # Execute this statement as part of the module's documented control flow.
        "game": game,
        # Execute this statement as part of the module's documented control flow.
        "round_id": round_id,
        # Execute this statement as part of the module's documented control flow.
        "transaction_type": transaction_type,
        # Execute this statement as part of the module's documented control flow.
        "amount": amount,
        # Execute this statement as part of the module's documented control flow.
        "balance_before": before,
        # Execute this statement as part of the module's documented control flow.
        "balance_after": after_player["balance"],
        # Execute this statement as part of the module's documented control flow.
        "details": details or {},
    }
    # Execute this statement as part of the module's documented control flow.
    append_jsonl(LEDGER_PATH, event)
    # Return the computed value to the caller.
    return event

# Define the debit function used by this module.
def debit(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Set amount to the value needed for the next operation.
    amount = abs(float(amount))
    # Return the computed value to the caller.
    return transact(player_id, -amount, transaction_type, game, round_id, details)

# Define the credit function used by this module.
def credit(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Set amount to the value needed for the next operation.
    amount = abs(float(amount))
    # Return the computed value to the caller.
    return transact(player_id, amount, transaction_type, game, round_id, details)

# Define the read_recent function used by this module.
def read_recent(player_id: str | None = None, limit: int = 100) -> list[dict]:
    # Import required dependency so this module can use its public functions or constants.
    import json
    # Branch when the following condition is true.
    if not LEDGER_PATH.exists():
        # Return the computed value to the caller.
        return []
    # Set rows to the value needed for the next operation.
    rows = []
    # Iterate through the collection to process each item.
    for line in LEDGER_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        # Start protected logic so failures can be handled safely.
        try:
            # Set ev to the value needed for the next operation.
            ev = json.loads(line)
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            continue
        # Branch when the following condition is true.
        if player_id is None or ev.get("player_id") == player_id:
            # Execute this statement as part of the module's documented control flow.
            rows.append(ev)
    # Return the computed value to the caller.
    return rows[-limit:]
