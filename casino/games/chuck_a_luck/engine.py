"""Pure validation, deterministic dice, settlement, and state helpers for Chuck-a-Luck."""

# Import deep-copy support so public payloads cannot mutate persisted nested rows.
import copy
# Import hashing for stable player-scoped round identities and request fingerprints.
import hashlib
# Import JSON normalization so semantically equal wager maps share one fingerprint.
import json
# Import decimal arithmetic so play-token calculations avoid binary floating-point drift.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Import project-standard conflict and validation errors for public boundaries.
from casino.errors import ConflictError, ValidationError
# Import game-local immutable rule metadata without crossing another game boundary.
from casino.games.chuck_a_luck import rules

# Store the two-decimal precision used by the shared play-token ledger.
TOKEN_QUANTUM = Decimal("0.01")
# Bound each face wager before aggregate debit calculation.
MAX_WAGER = Decimal("1000000.00")
# Retain a bounded recent history for reload-safe browser restoration.
RECENT_ROUND_LIMIT = 100


# Normalize one public wager amount into shared ledger precision.
def normalize_amount(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Surface a stable client validation message without echoing supplied data.
        raise ValidationError("Chuck-a-Luck wager amounts must be positive numbers")
    # Convert through text so decimal inputs remain stable across JSON number types.
    try:
        # Quantize half-up to the simulator's two-decimal play-token precision.
        amount = Decimal(str(value)).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Translate malformed and non-quantizable values into the standard API error.
    except (InvalidOperation, TypeError, ValueError):
        # Surface the same safe diagnostic for every malformed amount.
        raise ValidationError("Chuck-a-Luck wager amounts must be positive numbers")
    # Reject non-finite, zero, negative, and unreasonable simulator wagers.
    if not amount.is_finite() or amount <= 0 or amount > MAX_WAGER:
        # Explain the accepted fake-money range without implying currency value.
        raise ValidationError("Chuck-a-Luck wagers must be between 0.01 and 1000000.00 play tokens")
    # Return the float representation expected by the existing ledger API.
    return float(amount)


# Validate and normalize a map of face identifiers to play-token amounts.
def normalize_wagers(raw_wagers) -> dict[str, float]:
    # Require one non-empty JSON object so a roll always has a wager.
    if not isinstance(raw_wagers, dict) or not raw_wagers:
        # Reject empty actions before entropy, state, or ledger access.
        raise ValidationError("At least one Chuck-a-Luck number wager is required")
    # Identify unsupported machine keys without silently discarding player intent.
    unknown = sorted(set(raw_wagers) - set(rules.WAGER_TARGETS))
    # Reject any target outside the one-through-six catalog.
    if unknown:
        # Include only safe machine identifiers in structured error details.
        raise ValidationError("Unknown Chuck-a-Luck wager target", {"targets": unknown})
    # Normalize amounts while preserving canonical face order for stable fingerprints.
    return {target: normalize_amount(raw_wagers[target]) for target in rules.WAGER_TARGETS if target in raw_wagers}


# Calculate the aggregate wager debit using exact decimal addition.
def total_wager(wagers: dict[str, float]) -> float:
    # Normalize again so direct engine callers receive the same validation boundary.
    normalized = normalize_wagers(wagers)
    # Add every face wager without binary floating-point drift.
    total = sum((Decimal(str(amount)) for amount in normalized.values()), Decimal("0"))
    # Return the shared-ledger-compatible two-decimal total.
    return float(total.quantize(TOKEN_QUANTUM))


# Return a canonical digest that detects conflicting request-id replays.
def wager_fingerprint(wagers: dict[str, float]) -> str:
    # Normalize the request before hashing so equivalent numeric inputs match.
    normalized = normalize_wagers(wagers)
    # Serialize keys and values predictably before deriving the digest.
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 digest suitable for ledger audit details.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive one stable bounded round id from the game, player, and client request.
def round_id_for(player_id: str, request_id: str) -> str:
    # Hash private free-form identities so ledger rows expose no raw request text.
    digest = hashlib.sha256(f"{rules.GAME_ID}\0{player_id}\0{request_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest for readable Chuck-a-Luck diagnostics.
    return f"cal_{digest}"


# Roll exactly three ordered six-sided dice through an injectable random source.
def roll_dice(randbelow) -> list[int]:
    # Require a callable seam so focused tests never depend on ambient randomness.
    if not callable(randbelow):
        # Raise a programmer-facing error for an invalid integration dependency.
        raise TypeError("randbelow must be callable")
    # Collect ordered one-based die faces for persistence and animation.
    dice = []
    # Request exactly the immutable rules-profile dice count.
    for _index in range(rules.DICE_COUNT):
        # Read one zero-based result from the injected bounded generator.
        result = randbelow(rules.DIE_SIDES)
        # Reject booleans and out-of-range values instead of wrapping biased results.
        if isinstance(result, bool) or not isinstance(result, int) or not 0 <= result < rules.DIE_SIDES:
            # Raise a programmer-facing error for a broken entropy adapter.
            raise ValueError("randbelow returned an invalid Chuck-a-Luck die index")
        # Convert the validated zero-based index into a public one-based face.
        dice.append(result + 1)
    # Return the complete ordered authoritative result.
    return dice


# Validate a persisted or injected three-die result.
def require_dice(value) -> list[int]:
    # Require a JSON-compatible array with exactly three faces.
    if not isinstance(value, list) or len(value) != rules.DICE_COUNT:
        # Surface invalid persisted or test state explicitly.
        raise ValidationError("Chuck-a-Luck dice must contain exactly three faces")
    # Reject booleans, non-integers, and faces outside one through six.
    if any(isinstance(face, bool) or not isinstance(face, int) or not 1 <= face <= rules.DIE_SIDES for face in value):
        # Preserve one stable diagnostic for every invalid face vector.
        raise ValidationError("Chuck-a-Luck die faces must be integers from 1 through 6")
    # Copy the result so settlement never mutates caller-owned storage.
    return list(value)


# Calculate every face-wager return for one authoritative three-die result.
def settle(wagers: dict[str, float], dice) -> dict:
    # Normalize direct engine inputs through the public wager boundary.
    normalized = normalize_wagers(wagers)
    # Validate and copy the committed ordered dice result.
    faces = require_dice(dice)
    # Collect one explanatory settlement row per covered face.
    settlements = []
    # Calculate returned stake and net winnings for each normalized wager.
    for target, amount in normalized.items():
        # Resolve the numeric die face owned by this stable wager identifier.
        face = rules.FACE_BY_TARGET[target]
        # Count matching dice to select the one-, two-, or three-to-one net payout.
        matches = faces.count(face)
        # Use zero net multiplier for a losing uncovered result.
        net_multiplier = rules.NET_PAYOUT_BY_MATCH_COUNT.get(matches, 0)
        # Convert the normalized stake back into exact decimal arithmetic.
        stake = Decimal(str(amount))
        # Return the stake plus count-multiple winnings only when at least one die matches.
        returned = stake * Decimal(net_multiplier + 1) if matches else Decimal("0")
        # Calculate this wager's net contribution after its original debit.
        net = returned - stake
        # Append the complete public audit row used by the API and frontend.
        settlements.append({
            "target": target,  # Identify the stable one-through-six wager key.
            "face": face,  # Expose the numeric die face covered by the wager.
            "amount": amount,  # Preserve the normalized original stake.
            "matches": matches,  # Report how many authoritative dice matched.
            "won": matches > 0,  # Expose the settlement branch without client recomputation.
            "net_multiplier": net_multiplier,  # Report net winnings per unit stake.
            "return_amount": float(returned.quantize(TOKEN_QUANTUM)),  # Report stake-plus-winnings credit contribution.
            "net": float(net.quantize(TOKEN_QUANTUM)),  # Report this wager's profit or loss.
        })
    # Add all normalized stakes into the single aggregate debit amount.
    wager_total = sum((Decimal(str(amount)) for amount in normalized.values()), Decimal("0"))
    # Add all winning stake-plus-winnings values into one aggregate credit amount.
    return_total = sum((Decimal(str(row["return_amount"])) for row in settlements), Decimal("0"))
    # Return complete deterministic round calculations without mutating balances.
    return {
        "dice": faces,  # Preserve exact server-authoritative ordered faces.
        "total": sum(faces),  # Expose the visual and diagnostic dice sum.
        "is_triple": len(set(faces)) == 1,  # Identify three identical dice for result copy.
        "total_wager": float(wager_total.quantize(TOKEN_QUANTUM)),  # Report the aggregate ledger debit magnitude.
        "total_return": float(return_total.quantize(TOKEN_QUANTUM)),  # Report the optional aggregate ledger credit.
        "net": float((return_total - wager_total).quantize(TOKEN_QUANTUM)),  # Report complete round profit or loss.
        "settlements": settlements,  # Include one explanatory row per wager target.
    }


# Build a new empty player-owned game state document.
def default_state() -> dict:
    # Keep only bounded settled history because interrupted work recovers from ledger proof.
    return {"game": rules.GAME_ID, "recent_rounds": []}


# Find a previously settled client request inside player-owned state.
def find_round(state: dict, request_id: str):
    # Scan newest-first so ordinary network retries resolve quickly.
    return next((row for row in reversed(state.get("recent_rounds", [])) if row.get("request_id") == request_id), None)


# Record one settled round while retaining bounded reload-safe history.
def record_round(state: dict, round_row: dict, limit: int = RECENT_ROUND_LIMIT) -> dict:
    # Resolve any earlier state row carrying the same client request identity.
    existing = find_round(state, round_row["request_id"])
    # Reject one request identity reused for semantically different wagers.
    if existing and existing.get("request_fingerprint") != round_row.get("request_fingerprint"):
        # Fail closed instead of replacing an already settled round.
        raise ConflictError("Chuck-a-Luck request_id was already used with different wagers")
    # Preserve the original immutable result when the same round is recorded twice.
    if existing:
        # Return the original row without appending a duplicate history entry.
        return existing
    # Append the newly settled row after every required ledger action has committed.
    state.setdefault("recent_rounds", []).append(copy.deepcopy(round_row))
    # Retain only the newest configured number of rounds for responsive reloads.
    state["recent_rounds"] = state["recent_rounds"][-limit:]
    # Return the stored row for response construction.
    return round_row


# Build a public state snapshot without sharing mutable persisted references.
def public_state(state: dict) -> dict:
    # Preserve bounded settled history and storage schema metadata when present.
    return {
        "recent_rounds": copy.deepcopy(state.get("recent_rounds", [])),  # Copy nested settlement rows for API isolation.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve provider schema evidence.
    }


# Copy one settled round before exposing it through an API response.
def public_round(round_row: dict) -> dict:
    # Deep-copy nested wager and settlement data so callers cannot mutate state.
    return copy.deepcopy(round_row)
