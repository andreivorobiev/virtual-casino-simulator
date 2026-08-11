# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure dice, wager, and settlement rules for Over/Under 7."""

# Import hashing so authenticated action identities derive stable round ids.
import hashlib
# Import JSON normalization for semantic retry fingerprints.
import json
# Import decimal arithmetic so token math remains stable at two decimals.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Import finite checks for robust public amount validation.
import math

# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError
# Import this game's immutable identifiers and paytable.
from casino.games.over_under_7.rules import GAME_ID, NET_ODDS, OUTCOME_ORDER, WINNING_TOTALS, paytable

# Store shared ledger precision as a Decimal constant.
TOKEN_QUANTUM = Decimal("0.01")
# Bound one proposition amount to a generous simulator-safe ceiling.
MAX_WAGER = Decimal("1000000.00")
# Bound player-owned history so state documents remain small.
RECENT_ROUND_LIMIT = 100


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return bounded settled history because each play resolves atomically.
    return {"game": GAME_ID, "recent_rounds": []}


# Normalize one play-token amount to shared two-decimal precision.
def normalize_amount(value) -> float:
    # Reject booleans because Python treats them as numeric subtypes.
    if isinstance(value, bool):
        # Keep malformed payloads outside the shared ledger.
        raise ValidationError("Over/Under 7 wagers must be positive play-token amounts")
    # Convert through text so JSON numbers and strings normalize consistently.
    try:
        # Quantize half-up for player-facing token precision.
        amount = Decimal(str(value)).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Translate malformed values into the public error envelope.
    except (InvalidOperation, TypeError, ValueError):
        # Avoid echoing caller-controlled input.
        raise ValidationError("Over/Under 7 wagers must be positive play-token amounts") from None
    # Reject invalid, zero, negative, and unreasonable simulator amounts.
    if not math.isfinite(float(amount)) or amount <= 0 or amount > MAX_WAGER:
        # Report the accepted range without real-money framing.
        raise ValidationError("Over/Under 7 wagers must be between 0.01 and 1000000.00 play tokens")
    # Return the float representation expected by the existing ledger API.
    return float(amount)


# Normalize a wager map keyed by under, seven, or over.
def normalize_wagers(raw_wagers) -> dict[str, float]:
    # Require a non-empty object so one play has explicit player intent.
    if not isinstance(raw_wagers, dict) or not raw_wagers:
        # Reject empty plays before any dice or ledger work.
        raise ValidationError("At least one Over/Under 7 wager is required")
    # Detect unknown wager targets before dropping or reinterpreting them.
    unknown = sorted(set(raw_wagers) - set(OUTCOME_ORDER))
    # Reject any unsupported outcome keys.
    if unknown:
        # Include only stable machine keys in the error detail.
        raise ValidationError("Unknown Over/Under 7 wager target", {"outcomes": unknown})
    # Normalize in fixed order so responses and fingerprints stay deterministic.
    return {outcome: normalize_amount(raw_wagers[outcome]) for outcome in OUTCOME_ORDER if outcome in raw_wagers}


# Build a stable digest for conflicting-retry detection.
def wager_fingerprint(wagers: dict[str, float]) -> str:
    # Serialize with sorted keys and compact separators.
    encoded = json.dumps(wagers, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 digest for persisted audit details.
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Derive a bounded round id from authenticated player and client action identity.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespace and identities so route ids never contain free-form text.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough material for local collision resistance.
    return f"ou7_{digest[:24]}"


# Roll two six-sided dice through an injectable integer source.
def roll_dice(randbelow) -> tuple[int, int]:
    # Require an injectable callable so focused tests control dice outcomes.
    if not callable(randbelow):
        # Raise a programmer-facing seam error.
        raise TypeError("randbelow must be callable")
    # Draw the first die as a zero-based value and convert to one through six.
    first = randbelow(6)
    # Draw the second die independently using the same seam.
    second = randbelow(6)
    # Reject booleans and out-of-range values from broken deterministic seams.
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 or value >= 6 for value in (first, second)):
        # Surface a clear programmer-facing dice-seam failure.
        raise ValueError("randbelow returned an invalid die index")
    # Return ordinary one-based dice pips for state and UI.
    return first + 1, second + 1


# Classify one two-dice total against the documented profile.
def classify_total(total: int) -> str:
    # Treat totals below seven as the under proposition.
    if total < 7:
        # Return the stable machine key.
        return "under"
    # Treat exactly seven as the center proposition.
    if total == 7:
        # Return the stable machine key.
        return "seven"
    # Treat every higher legal total as the over proposition.
    return "over"


# Calculate a complete settlement without mutating balances.
def settle(wagers: dict[str, float], dice: tuple[int, int]) -> dict:
    # Validate each die before deriving the total.
    if len(dice) != 2 or any(isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 6 for value in dice):
        # Reject corrupted or invalid deterministic dice.
        raise ValidationError("Over/Under 7 dice must contain two values from 1 through 6")
    # Calculate the two-dice total.
    total = dice[0] + dice[1]
    # Identify the winning proposition.
    outcome = classify_total(total)
    # Sum all normalized stakes through Decimal arithmetic.
    total_wager = sum((Decimal(str(amount)) for amount in wagers.values()), Decimal("0"))
    # Read the winning stake or zero when the player did not cover the result.
    winning_stake = Decimal(str(wagers.get(outcome, 0.0)))
    # Return stake plus net odds for the winning proposition.
    total_return = winning_stake * Decimal(NET_ODDS[outcome] + 1)
    # Build a transparent row for every covered wager.
    rows = [
        # Report outcome, stake, win state, and net movement for the row.
        {"outcome": target, "amount": amount, "won": target == outcome, "net": float(((Decimal(str(amount)) * Decimal(NET_ODDS[target])) if target == outcome else -Decimal(str(amount))).quantize(TOKEN_QUANTUM))}
        # Preserve the player's normalized request order.
        for target, amount in wagers.items()
    ]
    # Return a JSON-compatible settled result.
    return {"dice": list(dice), "total": total, "outcome": outcome, "paytable": paytable(), "total_wager": float(total_wager.quantize(TOKEN_QUANTUM)), "total_return": float(total_return.quantize(TOKEN_QUANTUM)), "net": float((total_return - total_wager).quantize(TOKEN_QUANTUM)), "settlements": rows}


# Find a settled action in bounded player history.
def find_round(state: dict, action_id: str) -> dict | None:
    # Scan newest first so normal retries are cheap.
    return next((round_row for round_row in reversed(state.get("recent_rounds", [])) if round_row.get("action_id") == action_id), None)


# Record one settled round while rejecting changed retries.
def record_round(state: dict, round_row: dict) -> dict:
    # Resolve any existing retained round under this action identity.
    existing = find_round(state, round_row["action_id"])
    # Branch when the action identity already exists.
    if existing:
        # Reject changed semantic content under one action id.
        if existing.get("request_fingerprint") != round_row.get("request_fingerprint"):
            # Fail closed before a duplicate ledger movement can be represented.
            raise ConflictError("Over/Under 7 action_id was already used with different wagers")
        # Return the original row for exact retries.
        return existing
    # Append the new settled round.
    state.setdefault("recent_rounds", []).append(round_row)
    # Keep only the newest bounded history.
    state["recent_rounds"] = state["recent_rounds"][-RECENT_ROUND_LIMIT:]
    # Return the stored round for service code.
    return round_row
