# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Fan-Tan validation, count resolution, and settlement calculations."""

# Import hashing so retry-safe round ids and request fingerprints are deterministic.
import hashlib
# Import JSON normalization so semantically equal wager maps share one fingerprint.
import json
# Import decimal arithmetic so play-token settlements avoid binary floating-point drift.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Import finite-number checks for robust public wager validation.
import math
# Import project-standard domain errors for invalid or conflicting requests.
from casino.errors import ConflictError, ValidationError
# Import the immutable local Fan-Tan profile.
from casino.games.fan_tan.rules import GAME_ID, MAX_PILE_COUNT, MIN_PILE_COUNT, NET_ODDS, RESIDUES, outcome_catalog, rules_summary

# Store the two-decimal token precision used by the shared ledger.
TOKEN_QUANTUM = Decimal("0.01")
# Limit one residue wager to a generous simulator-safe amount before ledger validation.
MAX_WAGER = Decimal("1000000.00")


# Normalize one public play-token wager amount.
def normalize_amount(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Surface a stable validation error for malformed wager payloads.
        raise ValidationError("Fan-Tan wager amounts must be positive numbers")
    # Convert through text so decimal input remains stable across JSON number types.
    try:
        # Quantize half-up to match ordinary play-token display expectations.
        amount = Decimal(str(value)).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Convert decimal parsing failures into the project error envelope.
    except (InvalidOperation, TypeError, ValueError):
        # Surface a stable validation error for malformed wager payloads.
        raise ValidationError("Fan-Tan wager amounts must be positive numbers")
    # Reject non-finite values, zero, negatives, and unreasonable simulator payloads.
    if not math.isfinite(float(amount)) or amount <= 0 or amount > MAX_WAGER:
        # Surface the accepted amount boundary without implying real-money value.
        raise ValidationError("Fan-Tan wagers must be between 0.01 and 1000000.00 play tokens")
    # Return the normalized float expected by the existing ledger contract.
    return float(amount)


# Validate and normalize a residue-to-amount wager map.
def normalize_wagers(raw_wagers) -> dict[str, float]:
    # Require one JSON object so duplicate or ambiguous residue rows are impossible.
    if not isinstance(raw_wagers, dict) or not raw_wagers:
        # Reject empty plays before any ledger action can occur.
        raise ValidationError("At least one Fan-Tan residue wager is required")
    # Reject unknown residue ids rather than silently dropping player intent.
    unknown = sorted(set(raw_wagers) - set(RESIDUES))
    # Branch when one or more unsupported targets were supplied.
    if unknown:
        # Include only safe machine keys in the validation detail.
        raise ValidationError("Unknown Fan-Tan residue", {"residues": unknown})
    # Preserve residue order so fingerprints and responses remain deterministic.
    return {residue: normalize_amount(raw_wagers[residue]) for residue in RESIDUES if residue in raw_wagers}


# Return a canonical digest that detects conflicting client-request replays.
def wager_fingerprint(wagers: dict[str, float]) -> str:
    # Serialize keys and values predictably before hashing the request identity.
    canonical = json.dumps(wagers, sort_keys=True, separators=(",", ":"))
    # Return a compact full SHA-256 digest suitable for ledger details.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive one stable round id from the authenticated player and client action id.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash both identities so ledger ids stay bounded and contain no private free-form text.
    digest = hashlib.sha256(f"{player_id}\0{action_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest for readable Fan-Tan ledger and diagnostic rows.
    return f"ft_{digest}"


# Select one counted pile size through an injected cryptographic or deterministic source.
def select_pile_count(randbelow) -> int:
    # Require an injectable callable so focused tests never depend on ambient randomness.
    if not callable(randbelow):
        # Reject invalid integration seams before a round is debited.
        raise TypeError("randbelow must be callable")
    # Calculate the inclusive profile span for uniform selection.
    span = MAX_PILE_COUNT - MIN_PILE_COUNT + 1
    # Convert the selected offset once so custom deterministic sources can return integers.
    offset = randbelow(span)
    # Reject booleans and out-of-range offsets instead of biasing or wrapping results.
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset < span:
        # Raise a programmer-facing range error for a broken entropy adapter.
        raise ValueError("randbelow returned an invalid Fan-Tan pile offset")
    # Return the validated counted pile size.
    return MIN_PILE_COUNT + offset


# Resolve the Fan-Tan leftover residue after repeated groups of four.
def residue_for_count(pile_count: int) -> str:
    # Reject booleans and out-of-profile counts before calculating results.
    if isinstance(pile_count, bool) or not isinstance(pile_count, int) or not MIN_PILE_COUNT <= pile_count <= MAX_PILE_COUNT:
        # Surface corrupted result data explicitly.
        raise ValidationError("Fan-Tan pile count is outside the approved profile")
    # Convert modulo zero to the table outcome labeled four.
    residue = pile_count % 4 or 4
    # Return the public residue id used by wagers and i18n keys.
    return str(residue)


# Return each visible counting step for educational presentation.
def counting_steps(pile_count: int) -> list[dict]:
    # Validate the count before building the animation data.
    residue = residue_for_count(pile_count)
    # Compute how many complete groups of four are removed before the final visible residue.
    full_groups = (pile_count - int(residue)) // 4
    # Return a compact deterministic sequence that reduced-motion clients can render instantly.
    return [{"step": "pile", "remaining": pile_count}, {"step": "groups_of_four", "groups": full_groups}, {"step": "residue", "remaining": int(residue)}]


# Calculate the complete immutable-by-convention settlement for one counted pile.
def settle(wagers: dict[str, float], pile_count: int) -> dict:
    # Resolve and validate the winning residue before calculating payouts.
    residue = residue_for_count(pile_count)
    # Add all normalized wager amounts through Decimal arithmetic.
    total_wager = sum((Decimal(str(amount)) for amount in wagers.values()), Decimal("0"))
    # Read the winning stake or zero when the player did not cover this residue.
    winning_stake = Decimal(str(wagers.get(residue, 0.0)))
    # Return stake plus net winnings for the covered residue only.
    total_return = winning_stake * Decimal(NET_ODDS + 1)
    # Build one stable per-wager result row for UI and focused assertions.
    settlements = [{"residue": target, "amount": amount, "won": target == residue, "net": float((Decimal(str(amount)) * Decimal(NET_ODDS)) if target == residue else -Decimal(str(amount)))} for target, amount in wagers.items()]
    # Return all values rounded to the shared ledger precision.
    return {"pile_count": pile_count, "residue": residue, "net_odds": NET_ODDS, "counting_steps": counting_steps(pile_count), "total_wager": float(total_wager.quantize(TOKEN_QUANTUM)), "total_return": float(total_return.quantize(TOKEN_QUANTUM)), "net": float((total_return - total_wager).quantize(TOKEN_QUANTUM)), "settlements": settlements}


# Build a new empty player-owned state document.
def default_state() -> dict:
    # Keep only bounded settled history because open actions are reconstructed from ledger keys.
    return {"game": GAME_ID, "recent_rounds": []}


# Find a previously settled action inside the bounded player state cache.
def find_round(state: dict, action_id: str) -> dict | None:
    # Scan newest-first so normal retries resolve quickly.
    return next((row for row in reversed(state.get("recent_rounds", [])) if row.get("action_id") == action_id), None)


# Record one settled round while retaining a bounded reload-safe history.
def record_round(state: dict, round_row: dict, limit: int = 100) -> dict:
    # Reject conflicting duplicate action ids before mutating caller state.
    existing = find_round(state, round_row["action_id"])
    # Branch when an existing action id points to different wager content.
    if existing and existing.get("request_fingerprint") != round_row.get("request_fingerprint"):
        # Fail closed because one idempotency identity cannot represent two actions.
        raise ConflictError("Fan-Tan action_id was already used with different wagers")
    # Keep the original row when the same settled request is recorded again.
    if existing:
        # Return the stable original response row.
        return existing
    # Append the new row after all ledger actions have completed.
    state.setdefault("recent_rounds", []).append(round_row)
    # Retain only the newest bounded set for responsive state payloads.
    state["recent_rounds"] = state["recent_rounds"][-limit:]
    # Return the stored row for expression-friendly service code.
    return round_row


# Return the complete immutable rules view used by API and frontend modules.
def metadata() -> dict:
    # Combine profile and paytable in one backend-owned payload.
    return {"rules": rules_summary(), "outcomes": outcome_catalog()}
