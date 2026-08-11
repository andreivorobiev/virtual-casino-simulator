# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Ledger-backed accounting seam for server-managed practice opponents."""

# Import finite-number checks so invalid token amounts never reach storage.
import math
# Import a strict action-key matcher for storage-enforced retry identities.
import re

# Import the shared wallet services used by every managed-account movement.
from casino.core import ledger, players
# Import stable public errors for invalid controller requests.
from casino.errors import ValidationError

# Identify ledger rows written through this server-managed controller seam.
CONTROLLER_KIND = "practice_opponent"
# Restrict action identities to portable storage and API-safe characters.
ACTION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,160}$")
# Enumerate the only supported wallet movement directions.
MOVEMENTS = {"debit", "credit"}


# Resolve an active bot-backed player account before any wallet operation.
def require_account(player_id: str) -> dict:
    # Load the canonical player record through the configured storage provider.
    account = players.get_player(player_id)
    # Reject human accounts so game controllers cannot impersonate a user wallet.
    if account.get("type") != "bot":
        # Surface one stable validation error at the controller boundary.
        raise ValidationError("Practice opponent accounts must be bot player accounts")
    # Reject inactive managed accounts before a game reserves their tokens.
    if account.get("status") != "active":
        # Preserve explicit Admin control over deactivated accounts.
        raise ValidationError("Practice opponent account is not active")
    # Return the validated canonical account snapshot.
    return account


# Normalize one positive finite token amount before choosing debit or credit.
def require_amount(value) -> float:
    # Reject booleans and non-numeric values before float conversion.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # Keep the public controller contract strict and predictable.
        raise ValidationError("Practice opponent amount must be numeric")
    # Convert the numeric input once for finite and positive checks.
    amount = float(value)
    # Reject NaN, infinities, zero, and negative magnitudes.
    if not math.isfinite(amount) or amount <= 0:
        # Prevent malformed amounts from reaching shared ledger code.
        raise ValidationError("Practice opponent amount must be positive and finite")
    # Return shared-ledger two-decimal precision.
    return round(amount, 2)


# Normalize one durable controller action identity.
def require_action_key(value) -> str:
    # Require an exact safe string rather than coercing arbitrary JSON values.
    if not isinstance(value, str) or not ACTION_KEY_PATTERN.fullmatch(value):
        # Explain the stable portable action-key boundary without echoing input.
        raise ValidationError("Practice opponent action key is invalid")
    # Return the validated identity unchanged for storage fingerprinting.
    return value


# Execute or replay one funded practice-opponent wallet movement.
def transact(player_id: str, amount, transaction_type: str, action_key: str, game_id: str, round_id: str | None, movement: str, controller_action: str, *, session_owner_id: str | None = None, component: str | None = None, details: dict | None = None) -> dict:
    # Validate account ownership before constructing audit metadata.
    account = require_account(player_id)
    # Normalize the positive magnitude shared by debit and credit paths.
    normalized_amount = require_amount(amount)
    # Validate the durable storage action identity.
    normalized_key = require_action_key(action_key)
    # Reject unsupported movement directions before wallet code runs.
    if movement not in MOVEMENTS:
        # Keep the public controller vocabulary limited to debit and credit.
        raise ValidationError("Practice opponent movement must be debit or credit")
    # Require stable audit dimensions for every game-owned movement.
    if not all(isinstance(value, str) and value.strip() for value in (transaction_type, game_id, controller_action)):
        # Prevent anonymous or untraceable opponent ledger rows.
        raise ValidationError("Practice opponent transaction metadata is incomplete")
    # Copy optional game details without allowing reserved audit fields to be replaced.
    audit_details = dict(details or {})
    # Mark the event as a server-managed practice-opponent controller action.
    audit_details.update({
        "controller_kind": CONTROLLER_KIND,  # Distinguish managed opponent events from human play.
        "controller_action": controller_action,  # Preserve the public controller command family.
        "bot_id": account["player_id"],  # Correlate the controller and player account identities.
        "practice_action_key": normalized_key,  # Publish the durable retry identity for Admin audit.
        "session_owner_id": session_owner_id,  # Correlate the hand owner only on Admin-visible evidence.
        "component": component,  # Distinguish funding, escrow, refund, and payout movements.
    })
    # Route negative movements through storage-enforced ledger debit semantics.
    if movement == "debit":
        # Execute or replay the exact debit atomically with its ledger event.
        event, replayed = ledger.debit_once(account["player_id"], normalized_amount, transaction_type, normalized_key, game_id, round_id, audit_details)
    # Route positive movements through storage-enforced ledger credit semantics.
    else:
        # Execute or replay the exact credit atomically with its ledger event.
        event, replayed = ledger.credit_once(account["player_id"], normalized_amount, transaction_type, normalized_key, game_id, round_id, audit_details)
    # Return the immutable event plus an explicit retry marker to the controller.
    return {"event": event, "replayed": replayed}


# Read recent managed-opponent ledger events for Admin audit presentation.
def recent_activity(limit: int = 100, game_id: str | None = None) -> list[dict]:
    # Clamp the caller limit to a bounded Admin-safe range.
    bounded_limit = max(1, min(int(limit), 1000))
    # Read a wider bounded ledger window before filtering controller-owned rows.
    rows = ledger.read_recent(limit=1000)
    # Retain only standardized practice-opponent events and an optional game.
    filtered = [row for row in rows if (row.get("details") or {}).get("controller_kind") == CONTROLLER_KIND and (game_id is None or row.get("game") == game_id)]
    # Return only the newest requested events in chronological order.
    return filtered[-bounded_limit:]
