# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Crown and Anchor validation, dice mapping, and settlement logic."""

# Import hashing so request fingerprints and retry-safe round ids are deterministic.
import hashlib
# Import JSON so semantically equal wager maps share one canonical fingerprint.
import json
# Import decimal arithmetic so token settlement avoids binary floating-point drift.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Import finite checks for robust public wager validation.
import math
# Import shared public errors for validation and idempotency conflicts.
from casino.errors import ConflictError, ValidationError
# Import this module's immutable dice and payout profile.
from casino.games.crown_and_anchor.rules import DICE_COUNT, FACE_TO_SYMBOL, NET_ODDS_BY_HITS, SYMBOL_ORDER

# Store the two-decimal precision used by the shared play-token ledger.
TOKEN_QUANTUM = Decimal("0.01")
# Bound one symbol wager to a simulator-safe maximum before ledger access.
MAX_WAGER = Decimal("1000000.00")
# Retain bounded state history while idempotent ledger keys remain append-only.
ROUND_HISTORY_LIMIT = 100


# Normalize one public amount into the shared two-decimal play-token precision.
def normalize_amount(value) -> float:
    # Reject booleans because Python otherwise treats them as numbers.
    if isinstance(value, bool):
        # Surface a stable validation error without echoing caller input.
        raise ValidationError("Crown and Anchor wagers must be positive play-token amounts")
    # Convert through text so integer, float, and string payloads normalize consistently.
    try:
        # Quantize half-up for ordinary token display semantics.
        amount = Decimal(str(value)).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Convert malformed decimal input into the public validation boundary.
    except (InvalidOperation, TypeError, ValueError):
        # Surface a stable validation error without leaking raw input.
        raise ValidationError("Crown and Anchor wagers must be positive play-token amounts")
    # Reject non-finite, zero, negative, and oversized simulator amounts.
    if not math.isfinite(float(amount)) or amount <= 0 or amount > MAX_WAGER:
        # Explain the accepted token range without implying real-money value.
        raise ValidationError("Crown and Anchor wagers must be between 0.01 and 1000000.00 play tokens")
    # Return the normalized ledger-compatible amount.
    return float(amount)


# Validate and normalize a symbol wager map.
def normalize_wagers(raw_wagers) -> dict[str, float]:
    # Require a non-empty object so one action has explicit symbol coverage.
    if not isinstance(raw_wagers, dict) or not raw_wagers:
        # Reject empty rounds before any dice or ledger action can occur.
        raise ValidationError("At least one Crown and Anchor symbol wager is required")
    # Detect unsupported targets before silently dropping player intent.
    unknown = sorted(set(raw_wagers) - set(SYMBOL_ORDER))
    # Branch when caller supplied one or more invalid symbol ids.
    if unknown:
        # Include only safe machine keys in error details.
        raise ValidationError("Unknown Crown and Anchor wager symbol", {"symbols": unknown})
    # Preserve canonical table order for deterministic fingerprints and responses.
    return {symbol: normalize_amount(raw_wagers[symbol]) for symbol in SYMBOL_ORDER if symbol in raw_wagers}


# Return a canonical digest for detecting conflicting request replays.
def wager_fingerprint(wagers: dict[str, float]) -> str:
    # Serialize the normalized map predictably before hashing.
    canonical = json.dumps(wagers, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 hex digest for durable comparison.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive one stable round id from the session player and client action id.
def round_id_for(player_id: str, client_request_id: str) -> str:
    # Hash the pair so ledger ids stay bounded and contain no user-controlled text.
    digest = hashlib.sha256(f"{player_id}\0{client_request_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest for readable Crown and Anchor diagnostics.
    return f"caa_{digest}"


# Validate three one-based dice faces from an injected source or persisted ledger event.
def symbols_from_faces(faces: list[int]) -> list[str]:
    # Require exactly three dice so the rules profile stays countable and stable.
    if not isinstance(faces, list) or len(faces) != DICE_COUNT:
        # Surface corrupted or invalid dice data explicitly.
        raise ValidationError("Crown and Anchor requires exactly three dice faces")
    # Build the symbol result while validating every one-based face.
    symbols = []
    # Walk each face in roll order for deterministic presentation.
    for face in faces:
        # Reject booleans and out-of-range faces instead of coercing to symbols.
        if isinstance(face, bool) or not isinstance(face, int) or face not in FACE_TO_SYMBOL:
            # Surface corrupted or invalid dice data explicitly.
            raise ValidationError("Crown and Anchor dice faces must be integers from 1 through 6")
        # Append the mapped symbol for settlement and UI.
        symbols.append(FACE_TO_SYMBOL[face])
    # Return the complete ordered symbol roll.
    return symbols


# Roll three dice through an injectable one-based die function.
def roll_faces(roll_die) -> list[int]:
    # Require an injectable callable so focused tests avoid ambient randomness.
    if not callable(roll_die):
        # Raise a programmer-facing type error for a broken entropy adapter.
        raise TypeError("roll_die must be callable")
    # Collect exactly three one-based faces from the supplied source.
    faces = [int(roll_die()) for _ in range(DICE_COUNT)]
    # Validate and map once so invalid test seams fail before ledger details are built.
    symbols_from_faces(faces)
    # Return the validated faces for durable ledger details.
    return faces


# Calculate one complete settled round from normalized wagers and committed dice faces.
def settle(wagers: dict[str, float], faces: list[int]) -> dict:
    # Convert committed faces into symbols after validating the fixed dice profile.
    symbols = symbols_from_faces(faces)
    # Count how many dice landed on each legal symbol.
    hit_counts = {symbol: symbols.count(symbol) for symbol in SYMBOL_ORDER}
    # Sum every normalized stake through Decimal arithmetic.
    total_wager = sum((Decimal(str(amount)) for amount in wagers.values()), Decimal("0"))
    # Build one explanatory settlement row per covered symbol.
    rows = []
    # Track the complete returned credit across all covered hits.
    total_return = Decimal("0")
    # Preserve canonical wager order in the response.
    for symbol, amount in wagers.items():
        # Read the number of matching dice for this covered symbol.
        hits = hit_counts[symbol]
        # Convert the stake once for precise arithmetic.
        stake = Decimal(str(amount))
        # Read the net odds for one, two, or three hits.
        net_odds = NET_ODDS_BY_HITS.get(hits, 0)
        # Return stake plus net winnings only when at least one die matches.
        returned = stake * Decimal(net_odds + 1) if hits else Decimal("0")
        # Add this covered symbol's returned credit.
        total_return += returned
        # Append the player-facing row.
        rows.append({"symbol": symbol, "amount": amount, "hits": hits, "net_odds": net_odds, "returned": float(returned.quantize(TOKEN_QUANTUM)), "net": float((returned - stake).quantize(TOKEN_QUANTUM))})
    # Return a complete immutable-by-convention settlement payload.
    return {"faces": faces, "symbols": symbols, "hit_counts": hit_counts, "total_wager": float(total_wager.quantize(TOKEN_QUANTUM)), "total_return": float(total_return.quantize(TOKEN_QUANTUM)), "net": float((total_return - total_wager).quantize(TOKEN_QUANTUM)), "settlements": rows}


# Build a fresh player-owned state document.
def default_state() -> dict:
    # Keep only bounded settled history because ledger action ids recover committed movements.
    return {"game": "crown_and_anchor", "recent_rounds": []}


# Find a previously settled request inside this player's bounded state cache.
def find_round(state: dict, client_request_id: str) -> dict | None:
    # Scan newest-first so normal browser retries resolve quickly.
    return next((row for row in reversed(state.get("recent_rounds", [])) if row.get("client_request_id") == client_request_id), None)


# Record one settled round while enforcing immutable request identity.
def record_round(state: dict, round_row: dict, limit: int = ROUND_HISTORY_LIMIT) -> dict:
    # Look for an existing request before mutating the player document.
    existing = find_round(state, round_row["client_request_id"])
    # Branch when this request id already exists with a different wager fingerprint.
    if existing and existing.get("request_fingerprint") != round_row.get("request_fingerprint"):
        # Fail closed because one retry identity cannot represent two commands.
        raise ConflictError("Crown and Anchor client_request_id was already used with different wagers")
    # Keep and return the original row for exact retries.
    if existing:
        # Return the original settled response.
        return existing
    # Append the settled row after every required ledger action is durable.
    state.setdefault("recent_rounds", []).append(round_row)
    # Retain only the newest bounded history for responsive state payloads.
    state["recent_rounds"] = state["recent_rounds"][-limit:]
    # Return the stored row for service code.
    return round_row
