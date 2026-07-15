"""Deterministic single-hand 9/6 Jacks-or-Better rules for issue #91.

Confirmed requirements: CARD-001 and POKER-001.
Proposed local traceability prefix: JOBVP (pending central allocation by #77).
"""

# Import finite-number checks for safe fake-token wager normalization.
import math
# Import independent random generators for production entropy and deterministic tests.
import random

# Import shared card construction and shuffle primitives from the merged #96 lane.
from casino.core.cards import create_deck, shuffle_cards
# Import the shared standard five-card evaluator from the merged #96 lane.
from casino.core.poker import RANK_VALUES, evaluate_five
# Import game-safe conflict and validation errors for the API adapter boundary.
from casino.errors import ConflictError, ValidationError

# Identify every ledger, state, and catalog record owned by this game.
GAME_ID = "jacks_or_better_video_poker"
# Support the classic one-through-five coin wager choices.
COIN_CHOICES = (1, 2, 3, 4, 5)
# Bound one coin to the issue #91 fake-token wager ceiling.
MAX_COIN_VALUE = 20_000.0
# Bound completed state so reload safety does not create unbounded player documents.
RECENT_ROUND_LIMIT = 20
# Define the classic 9/6 Jacks-or-Better returned-credit table for one through five coins.
PAYTABLE = {
    "royal_flush": (250, 500, 750, 1000, 4000),  # Award the classic max-coin royal bonus.
    "straight_flush": (50, 100, 150, 200, 250),  # Scale non-royal straight flushes linearly.
    "four_of_a_kind": (25, 50, 75, 100, 125),  # Scale four-of-a-kind returned credits.
    "full_house": (9, 18, 27, 36, 45),  # Preserve the full-pay 9-for-1 full-house row.
    "flush": (6, 12, 18, 24, 30),  # Preserve the full-pay 6-for-1 flush row.
    "straight": (4, 8, 12, 16, 20),  # Scale straight returned credits linearly.
    "three_of_a_kind": (3, 6, 9, 12, 15),  # Scale trip returned credits linearly.
    "two_pair": (2, 4, 6, 8, 10),  # Return two credits per coin for two pair.
    "jacks_or_better": (1, 2, 3, 4, 5),  # Return the wager for a qualifying high pair.
    "no_win": (0, 0, 0, 0, 0),  # Return no credits for a losing hand.
}


# Build an empty player-scoped state document for isolated loading and tests.
def default_state() -> dict:
    # Return one active-round slot and a bounded reload-safe history collection.
    return {"active_round": None, "recent_rounds": []}


# Normalize the fake-token value represented by one selected coin.
def require_coin_value(value) -> float:
    # Reject booleans explicitly because they are numeric subclasses in Python.
    if isinstance(value, bool):
        # Explain the game-specific wager field at the validation boundary.
        raise ValidationError("coin_value must be numeric")
    # Convert incoming numeric values while translating malformed input consistently.
    try:
        # Round fake-token values to the ledger's two-decimal precision.
        coin_value = round(float(value), 2)
    # Convert all parsing failures into the public validation error shape.
    except (TypeError, ValueError):
        # Explain the game-specific wager field at the validation boundary.
        raise ValidationError("coin_value must be numeric")
    # Reject NaN and infinities before applying amount bounds.
    if not math.isfinite(coin_value):
        # Keep non-finite values from reaching persisted state or the ledger.
        raise ValidationError("coin_value must be finite")
    # Require a positive value compatible with two-decimal ledger precision.
    if coin_value < 0.01:
        # Match the shared ledger's minimum non-zero transaction precision.
        raise ValidationError("coin_value must be at least 0.01")
    # Keep one coin within the issue #91 fake-token wager ceiling.
    if coin_value > MAX_COIN_VALUE:
        # Report the per-coin maximum rather than a derived total.
        raise ValidationError("coin_value must be at most 20000")
    # Return the canonical two-decimal coin value for state and ledger records.
    return coin_value


# Normalize the selected classic one-through-five coin count.
def require_coins(value) -> int:
    # Reject booleans explicitly because they are integer subclasses in Python.
    if isinstance(value, bool):
        # Surface the exact supported selection to API clients.
        raise ValidationError("coins must be an integer from 1 through 5")
    # Convert numeric strings while translating malformed values consistently.
    try:
        # Parse the requested number of wagered coins.
        coins = int(value)
    # Convert all parsing failures into the public validation error shape.
    except (TypeError, ValueError):
        # Surface the exact supported selection to API clients.
        raise ValidationError("coins must be an integer from 1 through 5")
    # Reject fractional numeric inputs that int would otherwise truncate.
    try:
        # Compare the parsed integer with the original numeric value exactly.
        is_integral = float(value) == coins
    # Reject values that cannot participate in the numeric comparison.
    except (TypeError, ValueError):
        # Treat malformed values as non-integral.
        is_integral = False
    # Require one of the five classic paytable columns.
    if not is_integral or coins not in COIN_CHOICES:
        # Surface the exact supported selection to API clients.
        raise ValidationError("coins must be an integer from 1 through 5")
    # Return the canonical integer coin count for persisted state.
    return coins


# Validate held positions for the single five-card draw hand.
def require_holds(value) -> list[int]:
    # Require a JSON array instead of silently iterating strings or mappings.
    if not isinstance(value, list):
        # Tell callers the accepted positional representation.
        raise ValidationError("holds must be an array of card positions")
    # Reject booleans and non-integers before sorting the positions.
    if any(isinstance(position, bool) or not isinstance(position, int) for position in value):
        # Keep the error independent of Python's boolean/integer relationship.
        raise ValidationError("hold positions must be integers from 0 through 4")
    # Reject duplicate or out-of-range positions.
    if len(set(value)) != len(value) or any(position < 0 or position > 4 for position in value):
        # Keep the same stable diagnostic for every invalid position set.
        raise ValidationError("hold positions must be unique integers from 0 through 4")
    # Sort positions so state and deterministic tests remain stable.
    return sorted(value)


# Create one initial five-card hand and a persisted deterministic replacement pool.
def create_round(player_id: str, coin_value, coins, deal_action_id: str, *, seed=None, round_id: str, created_at: str) -> dict:
    # Validate the coin value before generating any cards or money movement.
    normalized_coin_value = require_coin_value(coin_value)
    # Validate the one-through-five coin selection before selecting a paytable column.
    normalized_coins = require_coins(coins)
    # Use a reproducible generator only when an isolated test supplies a seed.
    generator = random.Random(seed) if seed is not None else random.SystemRandom()
    # Shuffle through the shared #96 primitive so deck normalization stays centralized.
    shuffled = shuffle_cards(create_deck(), rng=generator)
    # Deal the five visible source cards from the single shuffled deck.
    initial_hand = shuffled[:5]
    # Persist only the five cards ever needed to replace a fully discarded hand.
    draw_pool = shuffled[5:10]
    # Return JSON-compatible state while keeping future replacement cards private.
    return {
        "round_id": round_id,  # Store the stable ledger correlation identifier.
        "deal_action_id": deal_action_id,  # Store the client retry key for exactly-once deals.
        "draw_action_id": None,  # Reserve the retry key that will own final settlement.
        "player_id": player_id,  # Bind the round to the authenticated player identity.
        "coin_value": normalized_coin_value,  # Persist the fake-token value of one coin.
        "coins": normalized_coins,  # Persist the selected classic paytable column.
        "total_wager": round(normalized_coin_value * normalized_coins, 2),  # Calculate one ledger debit.
        "phase": "hold",  # Begin with the five-card source hand awaiting hold choices.
        "initial_hand": [card.code for card in initial_hand],  # Expose compact stable card codes.
        "holds": [],  # Start with no held positions.
        "_draw_pool": [card.code for card in draw_pool],  # Persist private reload-safe replacements.
        "wager_status": "pending",  # Record that API settlement must ensure the debit.
        "payout_status": "not_ready",  # Prevent credits before the draw result exists.
        "created_at": created_at,  # Record the injected clock value for auditability.
    }


# Store hold choices without consuming replacement cards.
def set_holds(round_state: dict, holds) -> dict:
    # Allow hold changes only while the source hand is actionable.
    if round_state.get("phase") != "hold":
        # Reject stale browser actions after settlement.
        raise ConflictError("Hold choices are closed for this round")
    # Persist a canonical sorted position list for reload-safe continuation.
    round_state["holds"] = require_holds(holds)
    # Return the same state object for simple API persistence.
    return round_state


# Translate the standard evaluator result into a game-owned paytable outcome key.
def classify_hand(cards) -> str:
    # Evaluate exactly five cards through the shared #96 poker primitive.
    rank = evaluate_five(cards)
    # Recognize a royal flush as the ace-high form of a standard straight flush.
    if rank.name == "straight_flush" and {card.rank for card in rank.cards} == {"10", "J", "Q", "K", "A"}:
        # Return the game-owned top paytable row.
        return "royal_flush"
    # Recognize a one-pair win only when the pair is jacks or better.
    if rank.name == "one_pair":
        # Read the pair value from the standard evaluator's first tie breaker.
        pair_value = rank.tiebreak[0]
        # Return the qualifying high-pair row at the Jacks-or-Better threshold.
        return "jacks_or_better" if pair_value >= RANK_VALUES["J"] else "no_win"
    # Preserve every other standard category only when the paytable owns a row.
    return rank.name if rank.name in PAYTABLE else "no_win"


# Resolve returned credits from one game-owned outcome and selected coin column.
def returned_credits(outcome: str, coins) -> int:
    # Validate the selected column before indexing the immutable paytable row.
    normalized_coins = require_coins(coins)
    # Reject unknown outcomes instead of silently treating corrupted state as a loss.
    if outcome not in PAYTABLE:
        # Surface persisted or caller-owned outcome drift as a stable validation error.
        raise ValidationError("Unknown Jacks-or-Better outcome")
    # Select the zero-based classic paytable column for the requested coin count.
    return PAYTABLE[outcome][normalized_coins - 1]


# Complete the held-card draw from the persisted replacement plan exactly once.
def draw(round_state: dict, action_id: str, *, completed_at: str) -> dict:
    # Treat a repeated engine call with the same action key as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject attempts to relabel an already settled money action.
        if round_state.get("draw_action_id") != action_id:
            # Fail closed because one round may have only one settlement action key.
            raise ConflictError("This round was already drawn with another action_id")
        # Return the already-computed result without consuming new cards.
        return round_state
    # Require an actionable source hand before drawing.
    if round_state.get("phase") != "hold":
        # Reject unknown or partially corrupted phases.
        raise ConflictError("This round cannot be drawn in its current phase")
    # Reject a second action key after crash recovery bound the first key.
    if round_state.get("draw_action_id") not in (None, action_id):
        # Keep retry identity immutable before any result calculation.
        raise ConflictError("This round is already bound to another action_id")
    # Bind the settlement retry key before deriving the result.
    round_state["draw_action_id"] = action_id
    # Validate persisted holds again before using them as positions.
    holds = set(require_holds(round_state.get("holds", [])))
    # Read the original source hand used for held positions.
    initial_hand = list(round_state.get("initial_hand", []))
    # Reject incomplete source state instead of producing a malformed result.
    if len(initial_hand) != 5:
        # Surface persisted-state corruption as an explicit conflict.
        raise ConflictError("The initial hand is unavailable for this round")
    # Read the private deterministic replacement cards in deal order.
    draw_pool = list(round_state.get("_draw_pool", []))
    # Calculate the exact number of replacements needed for unheld positions.
    replacement_count = 5 - len(holds)
    # Reject incomplete private state instead of producing fewer than five cards.
    if len(draw_pool) < replacement_count:
        # Surface persisted-state corruption as an explicit conflict.
        raise ConflictError("Replacement cards are unavailable for this round")
    # Create an iterator so replacement order remains stable across every position.
    replacements = iter(draw_pool)
    # Preserve held cards and replace every unheld source position in order.
    final_hand = [card if position in holds else next(replacements) for position, card in enumerate(initial_hand)]
    # Translate the completed hand into the game-owned paytable key.
    outcome = classify_hand(final_hand)
    # Resolve integer returned credits from the selected one-through-five coin column.
    payout_credits = returned_credits(outcome, round_state["coins"])
    # Convert returned credits to fake tokens through the selected coin value.
    total_payout = round(round_state["coin_value"] * payout_credits, 2)
    # Calculate net movement after the already committed wager debit.
    net = round(total_payout - round_state["total_wager"], 2)
    # Classify net movement for localized result presentation.
    net_result = "win" if net > 0 else "push" if net == 0 else "loss"
    # Store the complete public final hand for deterministic reload and display.
    round_state["final_hand"] = final_hand
    # Store the stable game-owned paytable result key.
    round_state["outcome"] = outcome
    # Store integer returned credits independently of coin value.
    round_state["payout_credits"] = payout_credits
    # Store the one ledger credit amount requested by settlement.
    round_state["total_payout"] = total_payout
    # Store the player-facing net fake-token movement.
    round_state["net"] = net
    # Store the aggregate win, push, or loss classification.
    round_state["net_result"] = net_result
    # Mark card generation complete before API settlement begins.
    round_state["phase"] = "settled"
    # Mark a positive credit as pending while zero payouts need no ledger row.
    round_state["payout_status"] = "pending" if total_payout else "complete"
    # Store the injected completion timestamp for repeatable tests and audit state.
    round_state["completed_at"] = completed_at
    # Remove unused private replacement cards after results are durable.
    round_state.pop("_draw_pool", None)
    # Return the completed JSON-compatible round.
    return round_state


# Return active and recent rounds in retry-priority order.
def _round_candidates(state: dict) -> list[dict]:
    # Include the active round first and omit empty slots.
    return [item for item in [state.get("active_round"), *state.get("recent_rounds", [])] if item]


# Find a round by its deal idempotency key across active and recent state.
def round_for_deal_action(state: dict, deal_action_id: str):
    # Return the first exact retry-key match in bounded reload-safe state.
    return next((item for item in _round_candidates(state) if item.get("deal_action_id") == deal_action_id), None)


# Find a round by its draw idempotency key across active and recent state.
def round_for_draw_action(state: dict, action_id: str):
    # Return the first exact settlement-key match in bounded reload-safe state.
    return next((item for item in _round_candidates(state) if item.get("draw_action_id") == action_id), None)


# Find a round by its server identifier across active and recent state.
def round_by_id(state: dict, round_id: str):
    # Return the first exact server-id match in bounded reload-safe state.
    return next((item for item in _round_candidates(state) if item.get("round_id") == round_id), None)


# Move one completed round into bounded reload-safe state.
def archive_round(state: dict, round_state: dict) -> None:
    # Remove the round from the actionable slot after deterministic draw completion.
    state["active_round"] = None
    # Remove an older copy before appending an idempotent retry result.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state["round_id"]]
    # Append the newest settled round at the end for stable display ordering.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private replacement cards from public API payloads.
def public_round(round_state):
    # Preserve null active-round slots in state payloads.
    if round_state is None:
        # Return null without constructing a placeholder object.
        return None
    # Copy every public field while excluding the private deterministic draw pool.
    return {key: value for key, value in round_state.items() if key != "_draw_pool"}


# Build a public state snapshot without mutating persisted engine state.
def public_state(state: dict) -> dict:
    # Return sanitized active and recent round records plus schema metadata when present.
    return {
        "active_round": public_round(state.get("active_round")),  # Sanitize the actionable round.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize reload history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage schema metadata.
    }
