# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider
# Import the shared finite-number boundary before storage provider access.
from casino.core.validation import require_finite_number
from casino.errors import ValidationError


# Normalize one signed ledger amount before any provider or wallet access. (LEDGER-027)
def _normalize_amount(amount) -> float:
    # Convert and reject NaN or infinity before applying ledger precision.
    normalized = round(require_finite_number(amount, field="Ledger transaction amount"), 2)
    # Reject zero-value events so every ledger row has financial meaning.
    if normalized == 0:
        # Preserve the established public validation diagnostic.
        raise ValidationError("Ledger transaction amount cannot be zero")
    # Return the finite signed amount used by every public entry point.
    return normalized

# Define the transact function used by this module.
def transact(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Normalize the finite signed amount before selecting a storage provider. (LEDGER-027)
    amount = _normalize_amount(amount)
    # Return the provider-managed ledger event so balance and event writes are atomic where supported.
    return get_storage_provider().transact_ledger(player_id, amount, transaction_type, game, round_id, details)

# Execute or replay one storage-enforced money action identity.
def transact_once(player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
    # Normalize the finite signed amount before selecting a storage provider. (LEDGER-027)
    amount = _normalize_amount(amount)
    # Return the provider-owned event and replay marker from one atomic action transaction.
    return get_storage_provider().transact_ledger_once(player_id, amount, transaction_type, action_key, game, round_id, details)

# Find one committed storage action through the active provider's identity index. (LEDGER-033)
def find_action(player_id: str, game: str | None, action_key: str) -> dict | None:
    # Delegate the read-only point lookup without opening a second write-path connection.
    return get_storage_provider().find_ledger_action(player_id, game, action_key)

# Define the debit function used by this module.
def debit(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Normalize the finite magnitude before applying the debit sign. (LEDGER-027)
    amount = abs(_normalize_amount(amount))
    return transact(player_id, -amount, transaction_type, game, round_id, details)

# Debit or replay one storage-enforced money action identity.
def debit_once(player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
    # Normalize the finite magnitude before applying the debit sign. (LEDGER-027)
    amount = abs(_normalize_amount(amount))
    # Execute the action with a negative signed amount.
    return transact_once(player_id, -amount, transaction_type, action_key, game, round_id, details)

# Define the credit function used by this module.
def credit(player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
    # Normalize the finite magnitude before applying credit semantics. (LEDGER-027)
    amount = abs(_normalize_amount(amount))
    return transact(player_id, amount, transaction_type, game, round_id, details)

# Credit or replay one storage-enforced money action identity.
def credit_once(player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
    # Normalize the finite magnitude before applying credit semantics. (LEDGER-027)
    amount = abs(_normalize_amount(amount))
    # Execute the action with a positive signed amount.
    return transact_once(player_id, amount, transaction_type, action_key, game, round_id, details)

# Define the read_recent function used by this module.
def read_recent(player_id: str | None = None, limit: int = 100) -> list[dict]:
    # Return recent ledger events from the active storage provider.
    return get_storage_provider().read_ledger_recent(player_id, limit)


# Aggregate player-facing game economics inside the selected storage provider. (ADMIN-030)
def economics(window: int, game: str | None = None, recent: int = 0) -> dict:
    # Delegate the bounded window so MySQL can aggregate in SQL and JSON can use its cache.
    return get_storage_provider().ledger_economics(window, game=game, recent=recent)
