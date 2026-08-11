# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Sic Bo validation, deterministic dice seams, settlement, and state helpers.

Requirements used: DICE-001, LEDGER-005, LEDGER-006, and LEDGER-023.
"""

# Import hashing for stable round identities and semantic retry fingerprints.
import hashlib
# Import JSON normalization so equivalent wager maps share one fingerprint.
import json
# Import decimal arithmetic so settlements match ledger precision exactly.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Import standard domain errors for malformed or conflicting game actions.
from casino.errors import ConflictError, ValidationError
# Import only immutable game-owned rules through the local package boundary.
from casino.games.sic_bo.rules import BET_IDS, BET_ID_SET, FIXED_NET_ODDS, GAME_ID, TOTAL_NET_ODDS, bet_catalog

# Match the shared ledger's two-decimal play-token precision.
TOKEN_QUANTUM = Decimal("0.01")
# Bound one table position to a generous simulator-safe play-token wager.
MAX_POSITION_WAGER = Decimal("10000.00")
# Bound the aggregate debit across all fifty positions.
MAX_TOTAL_WAGER = Decimal("100000.00")
# Retain enough settled history for reload evidence without unbounded state growth.
RECENT_ROUND_LIMIT = 50


# Normalize one public play-token amount into ledger precision.
def normalize_amount(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Surface one stable boundary error without echoing caller content.
        raise ValidationError("Sic Bo wager amounts must be positive numbers")
    # Convert through text so JSON integers and floats share decimal semantics.
    try:
        # Parse the caller value without silently discarding excess precision.
        raw_amount = Decimal(str(value))
        # Reject infinities and NaN before quantization or float conversion.
        if not raw_amount.is_finite():
            # Route non-finite decimals through the stable validation path below.
            raise ValueError("non-finite Sic Bo wager")
        # Quantize only after retaining the exact caller-supplied decimal value.
        amount = raw_amount.quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Convert parser failures into the public validation envelope.
    except (InvalidOperation, TypeError, ValueError):
        # Reject malformed values before any state or ledger access.
        raise ValidationError("Sic Bo wager amounts must be positive numbers")
    # Reject values that violate the contract's two-decimal multiple boundary.
    if raw_amount != amount:
        # Refuse silent rounding because it could change an idempotent wager's intent.
        raise ValidationError("Sic Bo wager amounts cannot use more than two decimal places")
    # Reject zero, negative, and unreasonably large position wagers.
    if amount <= 0 or amount > MAX_POSITION_WAGER:
        # Report the play-token boundary without real-money wording.
        raise ValidationError("Each Sic Bo wager must be between 0.01 and 10000.00 play tokens")
    # Return the float shape consumed by the existing ledger contract.
    return float(amount)


# Validate and normalize a bet-id-to-amount object in canonical table order.
def normalize_wagers(raw_wagers) -> dict[str, float]:
    # Require a non-empty JSON object so each semantic position appears at most once.
    if not isinstance(raw_wagers, dict) or not raw_wagers:
        # Reject empty shakes before entropy, state, or ledger work begins.
        raise ValidationError("At least one Sic Bo wager is required")
    # Reject unsupported table positions rather than silently dropping intent.
    unknown = sorted(set(raw_wagers) - BET_ID_SET)
    # Branch when the caller supplied one or more unknown machine identifiers.
    if unknown:
        # Return only bounded position identifiers in diagnostic details.
        raise ValidationError("Unknown Sic Bo wager position", {"positions": unknown[:10]})
    # Normalize values while preserving the single canonical 50-position order.
    wagers = {bet_id: normalize_amount(raw_wagers[bet_id]) for bet_id in BET_IDS if bet_id in raw_wagers}
    # Sum through Decimal so aggregate-limit checks match later settlement math.
    total = sum((Decimal(str(amount)) for amount in wagers.values()), Decimal("0"))
    # Reject an aggregate debit beyond the documented simulator boundary.
    if total > MAX_TOTAL_WAGER:
        # Explain the aggregate limit without exposing any balance.
        raise ValidationError("Total Sic Bo wager cannot exceed 100000.00 play tokens")
    # Return the normalized canonical map used for fingerprints and ledger details.
    return wagers


# Return a stable digest that rejects conflicting retries of one action identity.
def wager_fingerprint(wagers: dict[str, float]) -> str:
    # Serialize keys and normalized values predictably before hashing.
    canonical = json.dumps(wagers, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 digest suitable for persisted state and ledger details.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive one bounded round id from authenticated player and caller action identity.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash free-form identities so ledger keys never expose them directly.
    digest = hashlib.sha256(f"{player_id}\0{action_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest so Sic Bo ledger events remain recognizable.
    return f"sb_{digest}"


# Validate exactly three ordinary six-sided die faces.
def require_dice(dice) -> list[int]:
    # Require a concrete three-item list or tuple from entropy or persisted recovery data.
    if not isinstance(dice, (list, tuple)) or len(dice) != 3:
        # Report corrupted or invalid dice without attempting settlement.
        raise ValidationError("Sic Bo requires exactly three dice")
    # Reject booleans and every face outside one through six.
    if any(isinstance(face, bool) or not isinstance(face, int) or face < 1 or face > 6 for face in dice):
        # Preserve the ordinary die boundary explicitly.
        raise ValidationError("Sic Bo die faces must be integers from 1 through 6")
    # Return a fresh list so callers cannot mutate persisted input by alias.
    return list(dice)


# Roll exactly three server-authoritative dice through an injected index source.
def roll_dice(randbelow) -> list[int]:
    # Require a callable source so tests never depend on ambient entropy.
    if not callable(randbelow):
        # Raise a programmer-facing integration error for a broken entropy seam.
        raise TypeError("randbelow must be callable")
    # Collect three independent one-based die faces in reveal order.
    dice = []
    # Draw exactly one bounded index for each physical die.
    for _ in range(3):
        # Read one zero-based face index from the injected source.
        index = randbelow(6)
        # Reject booleans and out-of-contract entropy results without wrapping bias.
        if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= 6:
            # Raise a programmer-facing error before any wager is debited.
            raise ValueError("randbelow returned an invalid Sic Bo die index")
        # Convert the validated zero-based index into a normal die face.
        dice.append(index + 1)
    # Return the complete authoritative result vector.
    return dice


# Return whether all three validated dice show the same face.
def is_triple(dice: list[int]) -> bool:
    # Compare all faces through set cardinality for one clear rule predicate.
    return len(set(dice)) == 1


# Calculate winning net odds for one legal position, or zero when it loses.
def winning_net_odds(bet_id: str, dice) -> int:
    # Validate authoritative or fixture dice before evaluating any rule.
    faces = require_dice(dice)
    # Reject internal callers that bypassed public wager normalization.
    if bet_id not in BET_ID_SET:
        # Surface the same stable invalid-position category used by requests.
        raise ValidationError("Unknown Sic Bo wager position")
    # Calculate the common total and triple predicate once per position.
    total = sum(faces)
    # Record the triple predicate because range bets explicitly exclude triples.
    triple = is_triple(faces)
    # Settle the small range only for non-triple totals from four through ten.
    if bet_id == "small":
        # Return even-money odds for a winning small result.
        return FIXED_NET_ODDS["small"] if not triple and 4 <= total <= 10 else 0
    # Settle the big range only for non-triple totals from eleven through seventeen.
    if bet_id == "big":
        # Return even-money odds for a winning big result.
        return FIXED_NET_ODDS["big"] if not triple and 11 <= total <= 17 else 0
    # Settle one exact-total position through the immutable regulator paytable.
    if bet_id.startswith("total:"):
        # Parse the canonical numeric suffix produced by the rules catalog.
        selected_total = int(bet_id.split(":", 1)[1])
        # Return the exact-total odds only when all three dice sum to it.
        return TOTAL_NET_ODDS[selected_total] if total == selected_total else 0
    # Settle one single-number position according to one, two, or three occurrences.
    if bet_id.startswith("single:"):
        # Parse the canonical selected face.
        selected_face = int(bet_id.split(":", 1)[1])
        # Use the occurrence count directly as the regulator-listed net odds.
        return faces.count(selected_face)
    # Settle one specific-double position when at least two matching faces appear.
    if bet_id.startswith("double:"):
        # Parse the selected repeated face.
        selected_face = int(bet_id.split(":", 1)[1])
        # Return the fixed double odds for two or three occurrences.
        return FIXED_NET_ODDS["double"] if faces.count(selected_face) >= 2 else 0
    # Settle the any-triple position before parsing specific triple suffixes.
    if bet_id == "any_triple":
        # Return the fixed any-triple odds when all faces match.
        return FIXED_NET_ODDS["any_triple"] if triple else 0
    # Settle one specific-triple position only when every face matches the selection.
    if bet_id.startswith("triple:"):
        # Parse the selected triple face.
        selected_face = int(bet_id.split(":", 1)[1])
        # Return the specific-triple odds only for that exact triple.
        return FIXED_NET_ODDS["triple"] if faces == [selected_face] * 3 else 0
    # Parse the two canonical distinct values from a combination position.
    _, left_text, right_text = bet_id.split(":")
    # Convert both canonical suffixes into die faces.
    left, right = int(left_text), int(right_text)
    # Return combination odds when each selected face appears at least once.
    return FIXED_NET_ODDS["combo"] if left in faces and right in faces else 0


# Calculate aggregate returned credits and explanatory rows for all wagers.
def settle(wagers: dict[str, float], dice) -> dict:
    # Re-normalize public-style input so direct engine callers cannot bypass limits.
    normalized = normalize_wagers(wagers)
    # Validate and copy the authoritative dice once for the settlement payload.
    faces = require_dice(dice)
    # Accumulate the aggregate debit through exact decimal arithmetic.
    total_wager = sum((Decimal(str(amount)) for amount in normalized.values()), Decimal("0"))
    # Start aggregate returned credits at zero before evaluating positions.
    total_return = Decimal("0")
    # Collect one stable row for every covered table position.
    settlements = []
    # Evaluate every normalized position in canonical board order.
    for bet_id, amount_value in normalized.items():
        # Convert the normalized float back into an exact decimal amount.
        amount = Decimal(str(amount_value))
        # Resolve winning net odds or zero for this authoritative result.
        net_odds = winning_net_odds(bet_id, faces)
        # Return stake plus net winnings only when this position wins.
        returned = (amount * Decimal(net_odds + 1)).quantize(TOKEN_QUANTUM) if net_odds else Decimal("0")
        # Add this position's returned credits into the aggregate payout.
        total_return += returned
        # Record one machine-readable settlement row for UI and audit details.
        settlements.append({
            "bet_id": bet_id,  # Identify the covered position without English copy.
            "amount": float(amount),  # Preserve the normalized play-token stake.
            "won": bool(net_odds),  # Expose the winning state without client rule logic.
            "net_odds": net_odds,  # Report the applied net odds, or zero for a loss.
            "return_amount": float(returned),  # Report stake plus winnings for this position.
            "net": float((returned - amount).quantize(TOKEN_QUANTUM)),  # Report position-level net result.
        })
    # Quantize aggregate values to the shared ledger precision.
    total_wager = total_wager.quantize(TOKEN_QUANTUM)
    # Quantize total returned credits after summing every winning position.
    total_return = total_return.quantize(TOKEN_QUANTUM)
    # Calculate the complete round net after the single aggregate debit.
    net = (total_return - total_wager).quantize(TOKEN_QUANTUM)
    # Describe the aggregate result without exposing internal settlement phases.
    outcome = "win" if net > 0 else "push" if net == 0 else "loss"
    # Return the immutable-by-convention settled result.
    return {
        "dice": faces,  # Preserve the authoritative reveal order.
        "total": sum(faces),  # Expose the three-die sum for table feedback.
        "triple": is_triple(faces),  # Expose triple status for range-bet explanation.
        "total_wager": float(total_wager),  # Report the single ledger debit amount.
        "total_return": float(total_return),  # Report the optional aggregate credit amount.
        "net": float(net),  # Report the complete play-token result.
        "outcome": outcome,  # Report localized-result lookup identity.
        "settlements": settlements,  # Preserve one explanatory row per wager.
    }


# Build one fresh player-owned state document.
def default_state() -> dict:
    # Keep one crash-recovery slot and bounded settled history.
    return {"game": GAME_ID, "active_round": None, "recent_rounds": []}


# Find an action in active or settled state for idempotent replay handling.
def round_for_action(state: dict, action_id: str) -> dict | None:
    # Prefer the active recovery slot because it may require ledger completion.
    active = state.get("active_round")
    # Return the active round when it owns this action identity.
    if active and active.get("action_id") == action_id:
        # Preserve object identity so the service can update recovery markers.
        return active
    # Scan newest-first so recent settled retries resolve quickly.
    return next((row for row in reversed(state.get("recent_rounds", [])) if row.get("action_id") == action_id), None)


# Return one public round while hiding unreconciled dice before a committed wager.
def public_round(round_state: dict | None) -> dict | None:
    # Preserve an empty active slot as JSON null.
    if round_state is None:
        # Return no round for ready state.
        return None
    # Copy only public audit, wager, and lifecycle fields.
    public = {key: round_state[key] for key in ("round_id", "action_id", "player_id", "request_fingerprint", "wagers", "phase", "wager_status", "payout_status", "created_at") if key in round_state}
    # Expose committed wager evidence when it exists.
    if round_state.get("wager_ledger_id"):
        # Copy the immutable ledger identifier for retry diagnostics.
        public["wager_ledger_id"] = round_state["wager_ledger_id"]
    # Reveal dice and settlement only after the aggregate wager is committed.
    if round_state.get("wager_status") == "complete":
        # Copy every settled game result field that is already available.
        for key in ("dice", "total", "triple", "total_wager", "total_return", "net", "outcome", "settlements"):
            # Include the field only after the service has calculated it.
            if key in round_state:
                # Copy lists and mappings through JSON-compatible deep normalization.
                public[key] = json.loads(json.dumps(round_state[key]))
    # Expose committed payout evidence when a positive credit occurred.
    if round_state.get("payout_ledger_id"):
        # Copy the immutable payout ledger identifier.
        public["payout_ledger_id"] = round_state["payout_ledger_id"]
    # Include the terminal timestamp only for completed rounds.
    if round_state.get("completed_at"):
        # Copy the stable completion time.
        public["completed_at"] = round_state["completed_at"]
    # Return the sanitized round snapshot.
    return public


# Return sanitized active and recent state for reload-safe browser rendering.
def public_state(state: dict) -> dict:
    # Serialize both the recovery slot and bounded history through public_round.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide private dice until debit proof exists.
        "recent_rounds": [public_round(row) for row in state.get("recent_rounds", [])],  # Sanitize every bounded history row.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),
    }


# Archive one completed round and clear its recovery slot exactly once.
def record_round(state: dict, round_state: dict, limit: int = RECENT_ROUND_LIMIT) -> dict:
    # Find an earlier archived action before changing caller state.
    existing = next((row for row in reversed(state.get("recent_rounds", [])) if row.get("action_id") == round_state.get("action_id")), None)
    # Reject one action identity that somehow reached different wager content.
    if existing and existing.get("request_fingerprint") != round_state.get("request_fingerprint"):
        # Fail closed rather than hiding state corruption.
        raise ConflictError("Sic Bo action_id was already used with different wagers")
    # Append only when this action is not already in bounded history.
    if existing is None:
        # Store a JSON-compatible copy detached from the active recovery object.
        state.setdefault("recent_rounds", []).append(json.loads(json.dumps(round_state)))
        # Retain only the newest configured history rows.
        state["recent_rounds"] = state["recent_rounds"][-limit:]
    # Clear the active slot only when it still references this completed action.
    if (state.get("active_round") or {}).get("action_id") == round_state.get("action_id"):
        # Release the crash-recovery slot for the next shake.
        state["active_round"] = None
    # Return the original archived row for response construction.
    return existing or round_state


# Return a fresh copy of the immutable bet metadata for state payloads.
def public_bets() -> list[dict]:
    # Rebuild catalog rows so response mutation cannot alter game rules.
    return bet_catalog()
