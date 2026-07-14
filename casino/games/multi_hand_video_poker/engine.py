"""Deterministic Jacks-or-Better engine for issue #94.

Requirements used: CARD-001 and POKER-001.
"""

# Import independent random generators for production entropy and deterministic tests.
import random

# Import shared card construction and shuffle primitives from the merged #96 lane.
from casino.core.cards import create_deck, shuffle_cards
# Import the shared standard five-card evaluator from the merged #96 lane.
from casino.core.poker import RANK_VALUES, evaluate_five
# Import the game-local validation error shape used by API callers.
from casino.errors import ConflictError, ValidationError

# Identify every ledger, state, and catalog record owned by this game.
GAME_ID = "multi_hand_video_poker"
# Restrict play to the three modes required by issue #94.
HAND_COUNTS = (3, 5, 10)
# Bound completed state so reload safety does not create unbounded documents.
RECENT_ROUND_LIMIT = 20
# Define Jacks-or-Better returned-credit multipliers for each qualifying result.
PAYTABLE = {
    "royal_flush": 250,  # Return two hundred fifty credits for a royal flush.
    "straight_flush": 50,  # Return fifty credits for a non-royal straight flush.
    "four_of_a_kind": 25,  # Return twenty-five credits for four of a kind.
    "full_house": 9,  # Return nine credits for a full house.
    "flush": 6,  # Return six credits for a flush.
    "straight": 4,  # Return four credits for a straight.
    "three_of_a_kind": 3,  # Return three credits for three of a kind.
    "two_pair": 2,  # Return two credits for two pair.
    "jacks_or_better": 1,  # Return the wager for a qualifying high pair.
    "no_win": 0,  # Return no credits for a losing hand.
}


# Build an empty player-scoped state document for isolated loading and tests.
def default_state() -> dict:
    # Return one active-round slot and a bounded reload-safe history collection.
    return {"active_round": None, "recent_rounds": []}


# Normalize and validate one required hand-count mode.
def require_hand_count(value) -> int:
    # Reject booleans explicitly because they are integer subclasses in Python.
    if isinstance(value, bool):
        # Surface the exact supported modes to API clients.
        raise ValidationError("hand_count must be 3, 5, or 10")
    # Convert numeric strings while translating malformed values consistently.
    try:
        # Parse the requested number of independent draw hands.
        hand_count = int(value)
    # Convert all parsing failures into the public validation error shape.
    except (TypeError, ValueError):
        # Surface the exact supported modes to API clients.
        raise ValidationError("hand_count must be 3, 5, or 10")
    # Reject modes outside the issue #94 acceptance set.
    if hand_count not in HAND_COUNTS:
        # Surface the exact supported modes to API clients.
        raise ValidationError("hand_count must be 3, 5, or 10")
    # Return the canonical integer mode for persisted state.
    return hand_count


# Normalize the wager applied independently to every generated hand.
def require_wager_per_hand(value) -> float:
    # Convert incoming numbers while rejecting missing or malformed values.
    try:
        # Round play-token wagers to the ledger's two-decimal precision.
        wager = round(float(value), 2)
    # Convert all parsing failures into the public validation error shape.
    except (TypeError, ValueError):
        # Explain the game-specific wager field instead of a generic amount field.
        raise ValidationError("wager_per_hand must be numeric")
    # Require a positive ledger-compatible wager.
    if wager < 0.01:
        # Match the ledger's minimum non-zero transaction precision.
        raise ValidationError("wager_per_hand must be at least 0.01")
    # Bound one request before multiplication by the ten-hand mode.
    if wager > 100_000:
        # Keep the resulting total wager within the shared ledger maximum.
        raise ValidationError("wager_per_hand must be at most 100000")
    # Return the normalized per-hand value.
    return wager


# Validate held positions shared across every final hand.
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


# Create one initial hand and one independent replacement pool per final hand.
def create_round(player_id: str, hand_count, wager_per_hand, request_id: str, *, seed=None, round_id: str, created_at: str) -> dict:
    # Validate the required issue #94 mode before generating any cards.
    normalized_count = require_hand_count(hand_count)
    # Validate one hand's wager before calculating the ledger debit.
    normalized_wager = require_wager_per_hand(wager_per_hand)
    # Use a reproducible generator only when a test supplies a seed.
    generator = random.Random(seed) if seed is not None else random.SystemRandom()
    # Shuffle through the shared #96 primitive so card normalization stays centralized.
    shuffled = shuffle_cards(create_deck(), rng=generator)
    # Deal the common five-card source hand from the shuffled deck.
    initial_hand = shuffled[:5]
    # Exclude every source card from each independent replacement pool.
    remaining = shuffled[5:]
    # Precompute only five possible replacements per hand for reload-safe deterministic draws.
    draw_pools = [shuffle_cards(remaining, rng=generator)[:5] for _ in range(normalized_count)]
    # Return JSON-compatible state while keeping draw pools private from public payloads.
    return {
        "round_id": round_id,  # Store the stable idempotency and ledger correlation key.
        "request_id": request_id,  # Store the client retry key for exactly-once starts.
        "player_id": player_id,  # Bind state to the authenticated player assumption.
        "hand_count": normalized_count,  # Persist the selected three, five, or ten-hand mode.
        "wager_per_hand": normalized_wager,  # Persist the amount applied to every hand.
        "total_wager": round(normalized_wager * normalized_count, 2),  # Calculate the single ledger debit.
        "phase": "hold",  # Begin with one common source hand awaiting hold choices.
        "initial_hand": [card.code for card in initial_hand],  # Expose compact shared card codes.
        "holds": [],  # Start with no selected positions.
        "_draw_pools": [[card.code for card in pool] for pool in draw_pools],  # Persist private replacement plans.
        "wager_status": "pending",  # Record that API settlement must ensure the debit.
        "payout_status": "not_ready",  # Prevent credits before a draw result exists.
        "created_at": created_at,  # Record the injected clock value for auditability.
    }


# Store hold choices without dealing replacement cards.
def set_holds(round_state: dict, holds) -> dict:
    # Allow hold changes only while the common source hand is actionable.
    if round_state.get("phase") != "hold":
        # Reject stale browser actions after settlement.
        raise ConflictError("Hold choices are closed for this round")
    # Persist a canonical sorted position list shared across all hands.
    round_state["holds"] = require_holds(holds)
    # Return the same state object for simple API persistence.
    return round_state


# Translate the standard evaluator result into the game-owned Jacks-or-Better paytable.
def classify_hand(cards) -> tuple[str, int]:
    # Evaluate exactly five cards through the shared #96 poker primitive.
    rank = evaluate_five(cards)
    # Recognize a royal flush as the ace-high form of a standard straight flush.
    if rank.name == "straight_flush" and {card.rank for card in rank.cards} == {"10", "J", "Q", "K", "A"}:
        # Return the game-owned royal-flush row and multiplier.
        return "royal_flush", PAYTABLE["royal_flush"]
    # Recognize a one-pair win only when the pair is jacks or better.
    if rank.name == "one_pair":
        # Read the pair value from the standard evaluator's first tie breaker.
        pair_value = rank.tiebreak[0]
        # Return the high-pair row when the pair meets the Jacks-or-Better threshold.
        if pair_value >= RANK_VALUES["J"]:
            # Return the qualifying pair row and multiplier.
            return "jacks_or_better", PAYTABLE["jacks_or_better"]
        # Return a loss for tens or lower without changing the shared evaluator.
        return "no_win", PAYTABLE["no_win"]
    # Preserve every other standard category only when it has a game paytable row.
    outcome = rank.name if rank.name in PAYTABLE else "no_win"
    # Return the stable result key and its returned-credit multiplier.
    return outcome, PAYTABLE[outcome]


# Complete every requested hand from the common holds and independent pools.
def draw(round_state: dict, *, completed_at: str) -> dict:
    # Treat a repeated engine call after settlement as an idempotent read.
    if round_state.get("phase") == "settled":
        # Return the already-computed result without consuming new cards.
        return round_state
    # Require an actionable common source hand before drawing.
    if round_state.get("phase") != "hold":
        # Reject unknown or partially corrupted phases.
        raise ConflictError("This round cannot be drawn in its current phase")
    # Validate persisted holds again before using them as positions.
    holds = set(require_holds(round_state.get("holds", [])))
    # Read the shared initial hand used by every final lane.
    initial_hand = list(round_state["initial_hand"])
    # Read the private deterministic replacement pools.
    draw_pools = list(round_state.get("_draw_pools", []))
    # Reject incomplete private state instead of producing fewer hands.
    if len(draw_pools) != round_state["hand_count"]:
        # Surface persisted-state corruption as an explicit conflict.
        raise ConflictError("Replacement cards are unavailable for this round")
    # Collect one evaluated result for each selected hand lane.
    results = []
    # Deal every hand independently while preserving held source positions.
    for hand_index, pool in enumerate(draw_pools):
        # Iterate over this hand's private replacement cards in deal order.
        replacements = iter(pool)
        # Preserve held positions and fill every other position from the independent pool.
        cards = [card if position in holds else next(replacements) for position, card in enumerate(initial_hand)]
        # Translate the final cards into the game-specific paytable result.
        outcome, multiplier = classify_hand(cards)
        # Calculate this lane's returned play-token credit.
        payout = round(round_state["wager_per_hand"] * multiplier, 2)
        # Store the complete public result for deterministic display and reload.
        results.append({"hand_index": hand_index, "cards": cards, "outcome": outcome, "multiplier": multiplier, "payout": payout})
    # Calculate one aggregate credit so settlement uses a single ledger event.
    total_payout = round(sum(result["payout"] for result in results), 2)
    # Calculate aggregate net movement for player-facing result language.
    net = round(total_payout - round_state["total_wager"], 2)
    # Classify the aggregate outcome without exposing internal engine phases.
    aggregate_outcome = "win" if net > 0 else "push" if net == 0 else "loss"
    # Store all final hand lanes for the frontend and API.
    round_state["results"] = results
    # Store the one ledger credit amount requested by settlement.
    round_state["total_payout"] = total_payout
    # Store the player-facing net movement for summary presentation.
    round_state["net"] = net
    # Store the aggregate result classification for history and UI copy.
    round_state["outcome"] = aggregate_outcome
    # Mark card generation complete before API settlement begins.
    round_state["phase"] = "settled"
    # Mark a positive credit as pending while zero payouts need no ledger row.
    round_state["payout_status"] = "pending" if total_payout else "complete"
    # Store the injected completion timestamp for repeatable tests and audit state.
    round_state["completed_at"] = completed_at
    # Remove unused private draw cards after results are durable.
    round_state.pop("_draw_pools", None)
    # Return the completed JSON-compatible round.
    return round_state


# Find a round by its client idempotency key across active and recent state.
def round_for_request(state: dict, request_id: str):
    # Include the active round first because retry recovery prioritizes in-progress state.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first matching round while ignoring empty slots.
    return next((item for item in candidates if item and item.get("request_id") == request_id), None)


# Find a round by its server identifier across active and recent state.
def round_by_id(state: dict, round_id: str):
    # Include the active round first because actions target it during normal play.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first exact match while ignoring empty slots.
    return next((item for item in candidates if item and item.get("round_id") == round_id), None)


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
    # Copy every public field while excluding the private deterministic draw pools.
    return {key: value for key, value in round_state.items() if key != "_draw_pools"}


# Build a public state snapshot without mutating persisted engine state.
def public_state(state: dict) -> dict:
    # Return sanitized active and recent round records plus schema metadata when present.
    return {
        "active_round": public_round(state.get("active_round")),  # Sanitize the actionable round.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize reload history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage schema metadata.
    }
