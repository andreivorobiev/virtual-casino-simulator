# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Acey-Deucey / In-Between rules for GitHub issue #149."""

# Import hashing so deal action ids produce stable reload-safe round ids.
import hashlib
# Import finite-number checks for play-token wager validation.
import math

# Import shared standard-card primitives without depending on another game module.
from casino.core.cards import RANKS, coerce_card, shuffled_deck
# Import public conflict and validation errors for game-owned rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, route payload, and ledger row owned by this game.
GAME_ID = "acey_deucey"
# Rank cards deuce through ace while ignoring suits for in-between decisions.
RANK_VALUES = {rank: value for value, rank in enumerate(RANKS, start=2)}
# Retain bounded completed history so one player document cannot grow forever.
RECENT_ROUND_LIMIT = 20


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one active deal slot, bounded history, and durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive play-token wager before any ledger movement.
def normalize_wager(value) -> float:
    # Reject booleans because Python treats them as numeric subclasses.
    if isinstance(value, bool):
        # Keep invalid values out of game state and ledger details.
        raise ValidationError("Acey-Deucey wager must be between 0.01 and 100000 play tokens")
    # Convert supported JSON numbers and numeric strings to ledger precision.
    try:
        # Round to the shared two-decimal token precision.
        wager = round(float(value), 2)
    # Convert malformed input into a stable public validation error.
    except (TypeError, ValueError):
        # Avoid echoing caller-controlled input in the diagnostic.
        raise ValidationError("Acey-Deucey wager must be between 0.01 and 100000 play tokens") from None
    # Reject zero, negative, non-finite, and oversized ledger amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Preserve the same range text for every invalid numeric shape.
        raise ValidationError("Acey-Deucey wager must be between 0.01 and 100000 play tokens")
    # Return the canonical wager amount.
    return wager


# Derive one stable route id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the identity so route-safe ids never include caller text.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Keep enough digest material for local collision resistance.
    return f"ad_{digest[:24]}"


# Deal two exposed boundary cards and one hidden result card without replacement.
def deal_cards(*, seed=None) -> tuple[str, str, str]:
    # Use shared secure shuffling in production and injected seeds in focused tests.
    deck = shuffled_deck(seed=seed)
    # Return compact card codes so persisted state stays JSON-friendly.
    return deck[0].code, deck[1].code, deck[2].code


# Return rank values for the two boundary cards in ascending order.
def boundary_values(left_card, right_card) -> tuple[int, int]:
    # Normalize the left boundary through the shared card primitive.
    left_value = RANK_VALUES[coerce_card(left_card).rank]
    # Normalize the right boundary independently so suits never matter.
    right_value = RANK_VALUES[coerce_card(right_card).rank]
    # Return low and high values for strict-inside comparisons.
    return min(left_value, right_value), max(left_value, right_value)


# Target house edge applied uniformly to every spread. (issue #408)
HOUSE_EDGE = 0.035

# Cards left in the shoe once both boundary cards are exposed.
REMAINING_AFTER_BOUNDARIES = 50

# Cards sharing one rank, used to convert a rank spread into a card count.
CARDS_PER_RANK = 4


# Price the inside wager for one spread so the house edge does not depend on what the player sees.
def inside_return_multiplier(spread: int) -> float:
    """Return the total return multiplier for a strict inside win at this spread.

    The player wagers after both boundaries are public, so a flat multiplier is mispriced: a wide
    spread is far more likely to land inside than a narrow one. Betting only the wide spreads was
    therefore strictly profitable (issue #408). Scaling the return by the actual inside probability
    removes that choice: P(inside) = CARDS_PER_RANK * spread / REMAINING_AFTER_BOUNDARIES, so a
    multiplier of (1 - HOUSE_EDGE) / P(inside) leaves the same edge at every spread.
    """
    # Reject a spread outside the complete single-deck boundary range.
    if spread < 1 or spread > len(RANK_VALUES) - 2:
        # Fail closed rather than returning an absent or nonsensical multiplier.
        raise ValidationError("Acey-Deucey boundaries leave no inside rank to wager on")
    # Convert the rank spread into the exact probability of a strict inside result.
    inside_probability = (CARDS_PER_RANK * spread) / REMAINING_AFTER_BOUNDARIES
    # Price the return so expected value stays below one at every spread.
    return round((1 - HOUSE_EDGE) / inside_probability, 2)


# Publish the full spread-to-multiplier paytable so clients never recompute the price themselves.
def inside_paytable() -> dict:
    # Build one entry per legal spread from a single boundary pair up to the widest ace-to-two gap.
    return {spread: inside_return_multiplier(spread) for spread in range(1, len(RANK_VALUES) - 1)}


# Count ranks strictly between the two exposed boundary cards.
def inside_rank_count(left_card, right_card) -> int:
    # Read normalized low and high rank values.
    low, high = boundary_values(left_card, right_card)
    # Return zero for equal or adjacent boundaries.
    return max(high - low - 1, 0)


# Build one prepared deal that survives reload before the player chooses a wager.
def create_round(player_id: str, deal_action_id: str, *, left_card: str, right_card: str, third_card: str, round_id: str, created_at: str, request_fingerprint: str) -> dict:
    # Normalize the exposed left boundary card.
    left = coerce_card(left_card).code
    # Normalize the exposed right boundary card.
    right = coerce_card(right_card).code
    # Normalize the hidden third card.
    third = coerce_card(third_card).code
    # Reject impossible duplicate physical cards in the single-deck profile.
    if len({left, right, third}) != 3:
        # Fail closed rather than representing replacement-card behavior.
        raise ValidationError("Acey-Deucey cards must be dealt without replacement")
    # Return JSON-compatible prepared state with the third card private.
    return {
        "round_id": round_id,  # Correlate route, state, and ledger movements.
        "player_id": player_id,  # Bind state to the authenticated session player.
        "deal_action_id": deal_action_id,  # Preserve retry identity for the free deal.
        "request_fingerprint": request_fingerprint,  # Detect changed deal retries.
        "phase": "wager",  # Await play or pass before the third card is revealed.
        "left_card": left,  # Expose the first boundary card.
        "right_card": right,  # Expose the second boundary card.
        "_third_card": third,  # Persist but do not publish the result card yet.
        "inside_rank_count": inside_rank_count(left, right),  # Explain available inside ranks.
        "play_action_id": None,  # Reserve settlement retry identity.
        "play_fingerprint": None,  # Reserve conflicting-retry detection.
        "wager": 0.0,  # Store zero until the player chooses to play.
        "outcome": None,  # Reserve inside, outside, boundary_tie, or passed.
        "payout": 0.0,  # Store total returned tokens after play.
        "net": 0.0,  # Store returned tokens minus wager.
        "wager_status": "not_ready",  # Require no debit until play.
        "settlement_status": "not_ready",  # Require no credit until play.
        "created_at": created_at,  # Preserve injected audit time.
    }

# Classify the hidden third card against the exposed boundaries.
def classify_result(left_card, right_card, third_card) -> str:
    # Read strict boundary values after card normalization.
    low, high = boundary_values(left_card, right_card)
    # Resolve the third-card rank value without suit significance.
    third_value = RANK_VALUES[coerce_card(third_card).rank]
    # Treat matching either boundary as an explicit tie-edge loss.
    if third_value == low or third_value == high:
        # Return a stable outcome key for contract and locale resources.
        return "boundary_tie"
    # Treat strict rank inclusion as the only winning condition.
    if low < third_value < high:
        # Return the inside-win outcome.
        return "inside"
    # Treat every non-inside rank as an outside loss.
    return "outside"


# Reveal and settle one prepared round without mutating balances directly.
def play_round(round_state: dict, wager, play_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Normalize the wager at the pure engine boundary.
    amount = normalize_wager(wager)
    # Replay only an exact already-settled play.
    if round_state.get("phase") == "settled":
        # Reject a changed action or wager after the terminal result exists.
        if round_state.get("play_action_id") != play_action_id or round_state.get("play_fingerprint") != request_fingerprint:
            # Preserve the original terminal decision.
            raise ConflictError("Acey-Deucey round was already settled by another action")
        # Return the settled round unchanged for idempotent service replay.
        return round_state
    # Require the player to still be in the wager decision phase.
    if round_state.get("phase") != "wager":
        # Reject stale or corrupt transitions explicitly.
        raise ConflictError("Acey-Deucey round cannot accept a play wager now")
    # Read the private third card prepared at deal time.
    third_card = round_state.get("_third_card")
    # Reject missing hidden state instead of drawing a replacement card.
    if not third_card:
        # Keep reload behavior deterministic and fail-closed.
        raise ConflictError("Acey-Deucey result card is unavailable")
    # Price this round from the spread the player could already see before wagering. (issue #408)
    spread = inside_rank_count(round_state["left_card"], round_state["right_card"])
    # Validate and capture the price before reveal, state mutation, receipts, or ledger movement.
    return_multiplier = inside_return_multiplier(spread)
    # Classify the third card against the strict in-between rule only after the wager is priceable.
    outcome = classify_result(round_state["left_card"], round_state["right_card"], third_card)
    # Return the spread-priced win only for a strict inside result; every other outcome loses.
    payout = round(amount * return_multiplier, 2) if outcome == "inside" else 0.0
    # Persist the play action identity.
    round_state["play_action_id"] = play_action_id
    # Persist the semantic retry fingerprint.
    round_state["play_fingerprint"] = request_fingerprint
    # Store the committed wager amount.
    round_state["wager"] = amount
    # Publish the formerly hidden third card.
    round_state["third_card"] = coerce_card(third_card).code
    # Retain the private representation until wager proof exists so a pre-debit crash can restore the prepared round.
    round_state["_third_card"] = coerce_card(third_card).code
    # Store the stable outcome key.
    round_state["outcome"] = outcome
    # Store the returned-token total.
    round_state["payout"] = payout
    # Store net result after the play wager debit.
    round_state["net"] = round(payout - amount, 2)
    # Mark the rule outcome terminal before the service performs ledger movement.
    round_state["phase"] = "settled"
    # Require the service to commit the wager debit.
    round_state["wager_status"] = "pending"
    # Require a credit only for strict inside wins.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Store injected completion time for deterministic tests.
    round_state["completed_at"] = completed_at
    # Return the mutable round for persistence.
    return round_state


# Restore one revealed play whose wager debit provably never committed.
def restore_uncommitted_play(state: dict, round_state: dict) -> None:
    # Read the prepared card from the new recovery field or a legacy revealed-only terminal row.
    third_card = round_state.get("_third_card") or round_state.get("third_card")
    # Refuse destructive cleanup when deterministic prepared state is unavailable.
    if not third_card:
        # Fail closed instead of replacing the original result card.
        raise ConflictError("Acey-Deucey result card is unavailable for wager recovery")
    # Read the round identity before moving it out of terminal history.
    round_id = round_state.get("round_id")
    # Read the uncommitted play identity so only its receipt is released.
    play_action_id = round_state.get("play_action_id")
    # Inspect any active decision before restoring this prepared round.
    active = state.get("active_round")
    # Reject conflicting state instead of overwriting another prepared round.
    if active is not None and active.get("round_id") != round_id:
        # Preserve both documents for explicit operator recovery.
        raise ConflictError("Acey-Deucey active round conflicts with wager recovery")
    # Restore the private deterministic card used by the original free deal.
    round_state["_third_card"] = coerce_card(third_card).code
    # Remove the revealed representation because no wager paid to expose it.
    round_state.pop("third_card", None)
    # Return the round to its original wager decision phase.
    round_state["phase"] = "wager"
    # Release the uncommitted play action identity.
    round_state["play_action_id"] = None
    # Release its semantic retry fingerprint.
    round_state["play_fingerprint"] = None
    # Restore the pre-play zero wager value.
    round_state["wager"] = 0.0
    # Clear the uncommitted rule outcome.
    round_state["outcome"] = None
    # Clear the uncommitted returned-token total.
    round_state["payout"] = 0.0
    # Clear the uncommitted net result.
    round_state["net"] = 0.0
    # Mark that no wager movement is ready.
    round_state["wager_status"] = "not_ready"
    # Mark that no payout movement is ready.
    round_state["settlement_status"] = "not_ready"
    # Remove a terminal timestamp that no longer describes the restored decision.
    round_state.pop("completed_at", None)
    # Remove any stale wager proof marker from the uncommitted shape.
    round_state.pop("wager_ledger_id", None)
    # Remove any stale payout proof marker from the uncommitted shape.
    round_state.pop("settlement_ledger_id", None)
    # Remove the non-funded terminal copy from bounded history.
    state["recent_rounds"] = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_id]
    # Restore the original round to the active decision slot.
    state["active_round"] = round_state
    # Release only the play receipt when no ledger movement owns it.
    if play_action_id:
        # Permit a safe retry with the same action identity after funds recover.
        state.setdefault("action_receipts", {}).pop(play_action_id, None)


# Close one prepared round without wallet movement.
def pass_round(round_state: dict, pass_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Replay only an exact previous pass.
    if round_state.get("phase") == "passed":
        # Reject changed pass retries.
        if round_state.get("pass_action_id") != pass_action_id or round_state.get("pass_fingerprint") != request_fingerprint:
            # Preserve the original pass decision.
            raise ConflictError("Acey-Deucey round was already passed by another action")
        # Return the passed round unchanged.
        return round_state
    # Require a still-open boundary deal.
    if round_state.get("phase") != "wager":
        # Reject passing after play settlement or corruption.
        raise ConflictError("Acey-Deucey round cannot be passed now")
    # Store the pass action identity.
    round_state["pass_action_id"] = pass_action_id
    # Store the pass retry fingerprint.
    round_state["pass_fingerprint"] = request_fingerprint
    # Remove the hidden result because no wager paid to reveal it.
    round_state.pop("_third_card", None)
    # Store the stable pass outcome.
    round_state["outcome"] = "passed"
    # Mark the round terminal without settlement.
    round_state["phase"] = "passed"
    # Store the completion timestamp.
    round_state["completed_at"] = completed_at
    # Return the mutable round for persistence.
    return round_state


# Find one round by its free-deal action identity.
def round_for_deal_action(state: dict, action_id: str):
    # Search active and retained rounds for an exact deal identity.
    return next((item for item in [state.get("active_round"), *state.get("recent_rounds", [])] if item and item.get("deal_action_id") == action_id), None)


# Find one round by its server id within a player document.
def round_by_id(state: dict, round_id: str):
    # Search active and retained rounds without crossing session documents.
    return next((item for item in [state.get("active_round"), *state.get("recent_rounds", [])] if item and item.get("round_id") == round_id), None)


# Move a terminal round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Clear the active slot only when it still owns this round.
    if (state.get("active_round") or {}).get("round_id") == round_state.get("round_id"):
        # Release the next free deal.
        state["active_round"] = None
    # Remove an older copy before appending the newest terminal shape.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the terminal round in chronological order.
    recent.append(round_state)
    # Retain only the newest bounded history.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private fields from one public round payload.
def public_round(round_state):
    # Preserve JSON null for no active round.
    if round_state is None:
        # Return null to route callers.
        return None
    # Hide unrevealed cards and retry fingerprints.
    private_fields = {"_third_card", "request_fingerprint", "play_fingerprint", "pass_fingerprint"}
    # Return a detached shallow payload.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state payload.
def public_state(state: dict) -> dict:
    # Return active and recent rounds without private hidden cards.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide the result card until play.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
