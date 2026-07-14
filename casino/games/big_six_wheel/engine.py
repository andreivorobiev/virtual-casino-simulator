"""Pure validation, wheel selection, and payout calculations for Big Six Wheel."""

# Import hashing so retry-safe round ids and request fingerprints are deterministic.
import hashlib
# Import JSON normalization so semantically equal wager maps share one fingerprint.
import json
# Import decimal arithmetic so play-token settlements avoid binary floating-point drift.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Import finite-number checks for robust public amount validation.
import math
# Import the game's immutable wheel and paytable rules.
from casino.games.big_six_wheel.rules import GAME_ID, NET_ODDS, OUTCOME_ORDER, WHEEL_SEGMENTS
# Import project-standard domain errors for invalid or conflicting requests.
from casino.errors import ConflictError, ValidationError

# Store the two-decimal token precision used by the shared ledger.
TOKEN_QUANTUM = Decimal("0.01")
# Limit one wager to a generous simulator-safe amount before ledger validation.
MAX_WAGER = Decimal("1000000.00")


# Normalize one public amount into the shared two-decimal play-token precision.
def normalize_amount(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Surface a stable validation error for malformed wager payloads.
        raise ValidationError("Big Six wager amounts must be positive numbers")
    # Convert through text so decimal input remains stable across JSON number types.
    try:
        # Quantize half-up to match ordinary play-token display expectations.
        amount = Decimal(str(value)).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Convert decimal parsing failures into the project error envelope.
    except (InvalidOperation, TypeError, ValueError):
        # Surface a stable validation error for malformed wager payloads.
        raise ValidationError("Big Six wager amounts must be positive numbers")
    # Reject non-finite values, zero, negatives, and unreasonable simulator payloads.
    if not math.isfinite(float(amount)) or amount <= 0 or amount > MAX_WAGER:
        # Surface the accepted amount boundary without implying real-money value.
        raise ValidationError("Big Six wager amounts must be between 0.01 and 1000000.00 play tokens")
    # Return the normalized float expected by the existing ledger contract.
    return float(amount)


# Validate and normalize a map of outcome ids to play-token amounts.
def normalize_wagers(raw_wagers) -> dict[str, float]:
    # Require one JSON object so duplicate or ambiguous outcome rows are impossible.
    if not isinstance(raw_wagers, dict) or not raw_wagers:
        # Reject empty spins before any ledger action can occur.
        raise ValidationError("At least one Big Six wager is required")
    # Reject unknown machine ids rather than silently dropping player intent.
    unknown = sorted(set(raw_wagers) - set(OUTCOME_ORDER))
    # Branch when one or more unsupported targets were supplied.
    if unknown:
        # Include only safe machine keys in the validation detail.
        raise ValidationError("Unknown Big Six wager outcome", {"outcomes": unknown})
    # Preserve catalog order so fingerprints and responses remain deterministic.
    return {outcome: normalize_amount(raw_wagers[outcome]) for outcome in OUTCOME_ORDER if outcome in raw_wagers}


# Return a canonical digest that detects conflicting client-request replays.
def wager_fingerprint(wagers: dict[str, float]) -> str:
    # Serialize keys and values predictably before hashing the request identity.
    canonical = json.dumps(wagers, sort_keys=True, separators=(",", ":"))
    # Return a compact full SHA-256 digest suitable for ledger details.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive one stable round id from the authenticated player and client request id.
def round_id_for(player_id: str, client_request_id: str) -> str:
    # Hash both identities so ledger ids stay bounded and contain no private free-form text.
    digest = hashlib.sha256(f"{player_id}\0{client_request_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest for readable Big Six ledger and diagnostic rows.
    return f"bsw_{digest}"


# Select one wheel index through an injected cryptographic or deterministic source.
def select_index(randbelow) -> int:
    # Require an injectable callable so focused tests never depend on ambient randomness.
    if not callable(randbelow):
        # Reject invalid integration seams before a round is debited.
        raise TypeError("randbelow must be callable")
    # Convert the selected value once so custom deterministic sources can return integers.
    index = randbelow(len(WHEEL_SEGMENTS))
    # Reject booleans and out-of-range indices instead of biasing or wrapping results.
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(WHEEL_SEGMENTS):
        # Raise a programmer-facing range error for a broken entropy adapter.
        raise ValueError("randbelow returned an invalid Big Six wheel index")
    # Return the validated zero-based wheel position.
    return index


# Calculate the complete immutable-by-convention settlement for one selected index.
def settle(wagers: dict[str, float], result_index: int) -> dict:
    # Reject invalid persisted or injected indices before calculating payouts.
    if isinstance(result_index, bool) or not isinstance(result_index, int) or not 0 <= result_index < len(WHEEL_SEGMENTS):
        # Surface corrupted result data explicitly.
        raise ValidationError("Big Six result index is outside the wheel")
    # Read the winning outcome directly from the canonical clockwise wheel model.
    outcome = WHEEL_SEGMENTS[result_index]
    # Add all normalized wager amounts through Decimal arithmetic.
    total_wager = sum((Decimal(str(amount)) for amount in wagers.values()), Decimal("0"))
    # Read the winning stake or zero when the player did not cover this outcome.
    winning_stake = Decimal(str(wagers.get(outcome, 0.0)))
    # Return stake plus net winnings for the covered outcome only.
    total_return = winning_stake * Decimal(NET_ODDS[outcome] + 1)
    # Build one stable per-wager result row for UI and long-suite assertions.
    settlements = [
        # Report outcome, stake, net result, and win state without moving balances directly.
        {
            "outcome": target,  # Identify the covered symbol through its stable machine key.
            "amount": amount,  # Preserve the normalized play-token stake.
            "won": target == outcome,  # Expose win state without requiring client-side rule logic.
            "net": float((Decimal(str(amount)) * Decimal(NET_ODDS[target])) if target == outcome else -Decimal(str(amount))),  # Report net profit or loss for this wager.
        }
        # Preserve request order as normalized by the engine.
        for target, amount in wagers.items()
    ]
    # Return all values rounded to the shared ledger precision.
    return {
        "result_index": result_index,  # Preserve the physical wheel position used by animation.
        "outcome": outcome,  # Preserve the winning symbol used by presentation and history.
        "net_odds": NET_ODDS[outcome],  # Report the profile payout for the selected segment.
        "total_wager": float(total_wager.quantize(TOKEN_QUANTUM)),  # Report the single ledger debit amount.
        "total_return": float(total_return.quantize(TOKEN_QUANTUM)),  # Report the optional ledger credit amount.
        "net": float((total_return - total_wager).quantize(TOKEN_QUANTUM)),  # Report the complete round net.
        "settlements": settlements,  # Include one explanatory row per covered outcome.
    }


# Build a new empty player-owned state document.
def default_state() -> dict:
    # Keep only bounded settled history because open actions are reconstructed from ledger keys.
    return {"game": GAME_ID, "recent_rounds": []}


# Find a previously settled client request inside the bounded player state cache.
def find_round(state: dict, client_request_id: str) -> dict | None:
    # Scan newest-first so normal retries resolve quickly.
    return next((row for row in reversed(state.get("recent_rounds", [])) if row.get("client_request_id") == client_request_id), None)


# Record one settled round while retaining a bounded reload-safe history.
def record_round(state: dict, round_row: dict, limit: int = 100) -> dict:
    # Reject conflicting duplicate request ids before mutating caller state.
    existing = find_round(state, round_row["client_request_id"])
    # Branch when an existing request id points to different wager content.
    if existing and existing.get("request_fingerprint") != round_row.get("request_fingerprint"):
        # Fail closed because one idempotency identity cannot represent two actions.
        raise ConflictError("Big Six client_request_id was already used with different wagers")
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
