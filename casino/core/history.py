# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Durable per-player game history access through the configured storage provider.
import json
from casino.config import SCHEMA_VERSION
from casino.core.clock import utc_now
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider

# Define the append_history function used by this module.
def append_history(game: str, round_id: str, player_id: str, bet_type: str, bet_label: str, amount: float, outcome: str, payout: float, balance_after: float, details: dict | None = None) -> None:
    # Set event to the normalized history payload used by JSON and MySQL providers.
    event = {
        # Store the event timestamp.
        "timestamp": utc_now(),
        # Store the source game.
        "game": game,
        # Store the round or session ID.
        "round_id": round_id,
        # Store the owning player ID.
        "player_id": player_id,
        # Store the wager type.
        "bet_type": bet_type,
        # Store the wager label.
        "bet_label": bet_label,
        # Store the wager amount.
        "amount": round(float(amount), 2),
        # Store the settlement outcome.
        "outcome": outcome,
        # Store the payout amount.
        "payout": round(float(payout), 2),
        # Store the balance after settlement.
        "balance_after": round(float(balance_after), 2),
        # Store structured details as JSON text for CSV compatibility.
        "details_json": json.dumps(details or {}, sort_keys=True),
        # Store the schema version for future migrations.
        "schema_version": SCHEMA_VERSION,
    }
    # Persist the history event through the active storage provider.
    get_storage_provider().append_history(event)

# Define the recent_history function used by this module.
def recent_history(limit: int = 100, game: str | None = None) -> list[dict]:
    # Return recent history rows from the active storage provider.
    return get_storage_provider().recent_history(limit, game)
