# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError

# Define the transact function used by this module.
def transact(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Set amount to the value needed for the next operation.
    amount = round(float(amount), 2)
    # Branch when the following condition is true.
    if amount == 0:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Ledger transaction amount cannot be zero")
    # Return the provider-managed ledger event so balance and event writes are atomic where supported.
    return get_storage_provider().transact_ledger(player_id, amount, transaction_type, game, round_id, details)

# Execute or replay one storage-enforced money action identity.
def transact_once(player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
    # Normalize the amount before the provider computes its semantic fingerprint.
    amount = round(float(amount), 2)
    # Reject zero-value actions before opening a storage transaction.
    if amount == 0:
        # Raise the standard ledger validation error.
        raise ValidationError("Ledger transaction amount cannot be zero")
    # Return the provider-owned event and replay marker from one atomic action transaction.
    return get_storage_provider().transact_ledger_once(player_id, amount, transaction_type, action_key, game, round_id, details)

# Define the debit function used by this module.
def debit(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Set amount to the value needed for the next operation.
    amount = abs(float(amount))
    # Return the computed value to the caller.
    return transact(player_id, -amount, transaction_type, game, round_id, details)

# Debit or replay one storage-enforced money action identity.
def debit_once(player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
    # Normalize caller input to a positive magnitude before applying debit sign.
    amount = abs(float(amount))
    # Execute the action with a negative signed amount.
    return transact_once(player_id, -amount, transaction_type, action_key, game, round_id, details)

# Define the credit function used by this module.
def credit(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Set amount to the value needed for the next operation.
    amount = abs(float(amount))
    # Return the computed value to the caller.
    return transact(player_id, amount, transaction_type, game, round_id, details)

# Credit or replay one storage-enforced money action identity.
def credit_once(player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
    # Normalize caller input to a positive magnitude before applying credit sign.
    amount = abs(float(amount))
    # Execute the action with a positive signed amount.
    return transact_once(player_id, amount, transaction_type, action_key, game, round_id, details)

# Define the read_recent function used by this module.
def read_recent(player_id: str | None = None, limit: int = 100) -> list[dict]:
    # Return recent ledger events from the active storage provider.
    return get_storage_provider().read_ledger_recent(player_id, limit)
