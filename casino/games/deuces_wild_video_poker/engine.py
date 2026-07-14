"""Deterministic full-pay Deuces Wild engine for GitHub issue #92.

Existing requirements: CARD-001, POKER-001, LEDGER-005, and LEDGER-023.
Permanent Deuces Wild requirement IDs remain reserved for the #77 integration owner.
"""

# Import rank counters for wild-card category feasibility checks.
from collections import Counter
# Import stable digest support for retry-derived round identifiers.
import hashlib
# Import finite-number checks before any ledger-compatible wager is accepted.
import math
# Import independent random generators for production entropy and deterministic tests.
import random

# Reuse shared card construction, normalization, and non-mutating shuffle primitives from #96.
from casino.core.cards import RANKS, coerce_card, create_deck, shuffle_cards
# Reuse the standard evaluator for natural hands while keeping wild substitution game-local.
from casino.core.poker import evaluate_five
# Import public conflict and validation errors for engine boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state, route, catalog, and ledger record owned by this game.
GAME_ID = "deuces_wild_video_poker"
# Treat every deuce as a wild card under the frozen game profile.
WILD_RANK = "2"
# Bound reload-safe completed history in each player-scoped state document.
RECENT_ROUND_LIMIT = 20
# Bound one wager before it reaches the shared ledger service.
MAX_WAGER = 100_000
# List royal ranks once for natural and wild royal recognition.
ROYAL_RANKS = frozenset({"10", "J", "Q", "K", "A"})
# List every five-card straight rank set, including the ace-low wheel.
STRAIGHT_RANK_SETS = (
    frozenset({"A", "2", "3", "4", "5"}),  # Recognize the ace-low wheel.
    *(frozenset(RANKS[index:index + 5]) for index in range(0, 9)),  # Recognize deuce-low through ten-high runs.
)
# Freeze the documented full-pay returned-credit multipliers in strength order.
PAYTABLE = {
    "natural_royal_flush": 800,  # Return eight hundred credits for a deuce-free royal flush.
    "four_deuces": 200,  # Return two hundred credits for all four physical deuces.
    "wild_royal_flush": 25,  # Return twenty-five credits for a royal completed by deuces.
    "five_of_a_kind": 15,  # Return fifteen credits for five equal ranks using wild deuces.
    "straight_flush": 9,  # Return nine credits for a non-royal straight flush.
    "four_of_a_kind": 5,  # Return five credits for four equal ranks.
    "full_house": 3,  # Return three credits for a three-plus-two grouping.
    "flush": 2,  # Return two credits for five cards of one suit.
    "straight": 2,  # Return two credits for five consecutive ranks.
    "three_of_a_kind": 1,  # Return the wager for three equal ranks.
    "no_win": 0,  # Return no credits for every non-qualifying result.
}


# Build an empty player-owned document for state loading and isolated tests.
def default_state() -> dict:
    # Return one actionable round, bounded history, and replay records for client action IDs.
    return {"active_round": None, "recent_rounds": [], "actions": {}}


# Normalize one positive ledger-compatible play-token wager.
def require_wager(value) -> float:
    # Reject booleans explicitly because Python otherwise treats them as numbers.
    if isinstance(value, bool):
        # Keep the diagnostic stable for every non-numeric wager boundary.
        raise ValidationError("wager must be numeric")
    # Convert numeric input while translating malformed values consistently.
    try:
        # Round play-token wagers to the ledger's two-decimal precision.
        wager = round(float(value), 2)
    # Convert missing, textual, and unsupported values into a public validation error.
    except (TypeError, ValueError):
        # Explain the game-owned field instead of a generic amount field.
        raise ValidationError("wager must be numeric")
    # Reject NaN and infinities because comparisons cannot enforce ledger bounds on them.
    if not math.isfinite(wager):
        # Keep non-finite JSON-adjacent values outside state and action fingerprints.
        raise ValidationError("wager must be a finite number")
    # Require the smallest non-zero amount accepted by the shared ledger.
    if wager < 0.01:
        # Reject zero and negative wagers before state or entropy changes.
        raise ValidationError("wager must be at least 0.01")
    # Keep one action inside the shared ledger's conservative local boundary.
    if wager > MAX_WAGER:
        # Reject oversized actions without silently clamping token movement.
        raise ValidationError(f"wager must be at most {MAX_WAGER}")
    # Return the canonical amount used by fingerprints, state, and settlement.
    return wager


# Normalize held card positions into a stable sorted list.
def require_holds(value) -> list[int]:
    # Require a JSON array instead of iterating strings or mappings accidentally.
    if not isinstance(value, list):
        # Describe the public positional representation precisely.
        raise ValidationError("holds must be an array of card positions")
    # Reject booleans and non-integers before sorting positions.
    if any(isinstance(position, bool) or not isinstance(position, int) for position in value):
        # Keep Python's boolean/integer relationship out of the public contract.
        raise ValidationError("hold positions must be integers from 0 through 4")
    # Reject duplicates and positions outside the five-card hand.
    if len(set(value)) != len(value) or any(position < 0 or position > 4 for position in value):
        # Use one stable diagnostic for duplicate and out-of-range selection sets.
        raise ValidationError("hold positions must be unique integers from 0 through 4")
    # Sort positions so persisted state and response fingerprints remain deterministic.
    return sorted(value)


# Derive one opaque stable round identifier from the session player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Separate identity components with a null byte before hashing them.
    material = f"{player_id}\0{action_id}".encode("utf-8")
    # Return a URL-safe game-prefixed digest without exposing the player identifier.
    return f"dwvp_{hashlib.sha256(material).hexdigest()[:24]}"


# Fingerprint the private deterministic deal plan without exposing undealt cards.
def deal_plan_fingerprint(round_state: dict) -> str:
    # Read the durable private digest needed after replacement cards are discarded.
    stored = round_state.get("_deal_plan_fingerprint")
    # Read private replacements while an unsettled round still retains its complete plan.
    draw_pool = round_state.get("_draw_pool")
    # Recompute the digest whenever private cards remain available for integrity checking.
    if isinstance(draw_pool, list) and draw_pool:
        # Combine the visible initial hand and private replacement order canonically.
        plan = "|".join([*round_state.get("initial_hand", []), "--", *draw_pool])
        # Calculate a full digest so old ledger proof cannot attach to different cards.
        calculated = hashlib.sha256(plan.encode("utf-8")).hexdigest()
        # Reject altered persisted card state instead of trusting a now-stale digest.
        if stored is not None and stored != calculated:
            # Surface state-plan corruption before any debit recovery can proceed.
            raise ConflictError("Deuces Wild deal plan integrity check failed")
        # Return the verified or newly calculated plan identity.
        return calculated
    # Reuse the durable digest after settlement removes undealt private cards.
    if isinstance(stored, str) and stored:
        # Preserve the original wager fingerprint across completed-round retries.
        return stored
    # Fail closed when neither the full plan nor its durable digest remains available.
    raise ConflictError("Deuces Wild deal plan is unavailable")


# Normalize exactly five distinct standard cards for game-local scoring.
def _normalize_hand(cards) -> tuple:
    # Translate unsupported iterables into the same five-card validation boundary.
    try:
        # Normalize every card through the shared #96 primitive.
        normalized = tuple(coerce_card(card) for card in cards)
    # Convert invalid card shapes into a public game validation error.
    except (TypeError, ValueError):
        # Avoid leaking Python coercion diagnostics through game APIs or tests.
        raise ValidationError("hand must contain five valid distinct cards")
    # Require the exact draw-poker hand size.
    if len(normalized) != 5:
        # Reject incomplete and oversized hands consistently.
        raise ValidationError("hand must contain five valid distinct cards")
    # Require physical card uniqueness even though wild ranks may duplicate logical ranks.
    if len({card.code for card in normalized}) != 5:
        # Reject impossible duplicate-card fixtures before category evaluation.
        raise ValidationError("hand must contain five valid distinct cards")
    # Return immutable normalized cards for the remaining pure checks.
    return normalized


# Return whether wild deuces can complete one straight from the natural ranks.
def _can_make_straight(natural_cards: tuple, wild_count: int) -> bool:
    # Collect fixed non-wild ranks because a physical natural card cannot change rank.
    natural_ranks = [card.rank for card in natural_cards]
    # Reject duplicate natural ranks because all five cards must participate in a straight.
    if len(set(natural_ranks)) != len(natural_ranks):
        # Report no feasible straight without mutating or discarding fixed cards.
        return False
    # Convert fixed ranks to a set for subset checks against every allowed run.
    fixed = frozenset(natural_ranks)
    # Accept a run only when all fixed ranks fit and every missing rank can use one deuce.
    return any(fixed.issubset(sequence) and len(sequence - fixed) == wild_count for sequence in STRAIGHT_RANK_SETS)


# Return whether all cards can form a three-plus-two grouping using wild deuces.
def _can_make_full_house(rank_counts: Counter, wild_count: int) -> bool:
    # Consider every distinct choice of trip rank and pair rank from the standard rank set.
    for trip_rank in RANKS:
        # Consider every possible pair rank independently of the trip rank.
        for pair_rank in RANKS:
            # Keep full-house groups distinct by definition.
            if pair_rank == trip_rank:
                # Continue to another candidate pair rank.
                continue
            # Reject fixed natural ranks that cannot fit either target group.
            if any(rank not in {trip_rank, pair_rank} for rank in rank_counts):
                # Continue because wild cards cannot change a natural card's rank.
                continue
            # Reject a fixed group already larger than its target size.
            if rank_counts.get(trip_rank, 0) > 3 or rank_counts.get(pair_rank, 0) > 2:
                # Continue to the next candidate grouping.
                continue
            # Count deuces needed to fill the chosen trip and pair.
            needed = 3 - rank_counts.get(trip_rank, 0) + 2 - rank_counts.get(pair_rank, 0)
            # Accept only when every wild deuce is consumed by this five-card grouping.
            if needed == wild_count:
                # Report the first feasible full-house assignment.
                return True
    # Report that no three-plus-two assignment consumes the complete hand.
    return False


# Classify one final hand under the documented full-pay Deuces Wild profile.
def classify_hand(cards) -> tuple[str, int]:
    # Normalize and validate physical cards through the shared card primitive.
    normalized = _normalize_hand(cards)
    # Separate wild deuces from fixed natural cards for category feasibility checks.
    natural_cards = tuple(card for card in normalized if card.rank != WILD_RANK)
    # Count physical deuces once for every wild-card branch.
    wild_count = len(normalized) - len(natural_cards)
    # Evaluate deuce-free hands through the shared standard poker primitive.
    if wild_count == 0:
        # Compute the standard category without duplicating #96 logic.
        standard = evaluate_five(normalized)
        # Recognize the deuce-free ace-high straight flush as the top natural royal.
        if standard.name == "straight_flush" and {card.rank for card in normalized} == ROYAL_RANKS:
            # Return the frozen top paytable row and multiplier.
            return "natural_royal_flush", PAYTABLE["natural_royal_flush"]
        # Preserve only standard categories paid by this Deuces Wild profile.
        outcome = standard.name if standard.name in PAYTABLE else "no_win"
        # Return the qualifying standard result or the stable losing row.
        return outcome, PAYTABLE[outcome]
    # Rank four physical deuces above every substitution they could represent.
    if wild_count == 4:
        # Return the dedicated four-deuces row and multiplier.
        return "four_deuces", PAYTABLE["four_deuces"]
    # Collect fixed natural suits for royal, straight-flush, and flush feasibility.
    natural_suits = {card.suit for card in natural_cards}
    # Collect fixed natural ranks for royal and grouped-hand feasibility.
    natural_ranks = {card.rank for card in natural_cards}
    # Recognize a royal completed by one or more wild deuces in one suit.
    if len(natural_suits) == 1 and natural_ranks.issubset(ROYAL_RANKS):
        # Return the wild royal row before lower five-kind possibilities.
        return "wild_royal_flush", PAYTABLE["wild_royal_flush"]
    # Count fixed natural ranks for five-, four-, full-house, and three-kind checks.
    rank_counts = Counter(card.rank for card in natural_cards)
    # Recognize five equal logical ranks when every natural rank already matches.
    if len(rank_counts) == 1 and max(rank_counts.values(), default=0) + wild_count == 5:
        # Return the five-of-a-kind row before straight flush.
        return "five_of_a_kind", PAYTABLE["five_of_a_kind"]
    # Recognize a suited straight completed by available wild deuces.
    if len(natural_suits) == 1 and _can_make_straight(natural_cards, wild_count):
        # Return the non-royal straight-flush row.
        return "straight_flush", PAYTABLE["straight_flush"]
    # Recognize four equal logical ranks with remaining cards acting as kickers.
    if max(rank_counts.values(), default=0) + wild_count >= 4:
        # Return the four-of-a-kind row after stronger wild categories.
        return "four_of_a_kind", PAYTABLE["four_of_a_kind"]
    # Recognize an exact three-plus-two grouping using every wild deuce.
    if _can_make_full_house(rank_counts, wild_count):
        # Return the full-house row before flush and straight.
        return "full_house", PAYTABLE["full_house"]
    # Recognize a flush when every natural card already shares one suit.
    if len(natural_suits) == 1:
        # Return the flush row because deuces can adopt the fixed suit.
        return "flush", PAYTABLE["flush"]
    # Recognize a straight in any suits when wild deuces fill all missing ranks.
    if _can_make_straight(natural_cards, wild_count):
        # Return the straight row after flush under the documented hierarchy.
        return "straight", PAYTABLE["straight"]
    # Recognize three equal logical ranks as the lowest qualifying result.
    if max(rank_counts.values(), default=0) + wild_count >= 3:
        # Return the wager through the three-of-a-kind multiplier.
        return "three_of_a_kind", PAYTABLE["three_of_a_kind"]
    # Return the stable losing row when no paid category is feasible.
    return "no_win", PAYTABLE["no_win"]


# Create one reload-safe initial hand and private replacement plan.
def create_round(player_id: str, wager, deal_action_id: str, *, seed=None, round_id: str, created_at: str) -> dict:
    # Validate the wager before consuming entropy or building state.
    normalized_wager = require_wager(wager)
    # Use a reproducible generator only when an isolated test supplies a seed.
    generator = random.Random(seed) if seed is not None else random.SystemRandom()
    # Shuffle a shared standard deck without adding game-owned card primitives.
    shuffled = shuffle_cards(create_deck(), rng=generator)
    # Deal the initial five-card hand from the beginning of the shuffled deck.
    initial_hand = shuffled[:5]
    # Persist every possible replacement in order so reload cannot change a draw.
    draw_pool = shuffled[5:]
    # Build JSON-compatible private state prepared before any ledger movement.
    round_state = {
        "round_id": round_id,  # Store the stable player/action-derived round key.
        "player_id": player_id,  # Bind the round to the authenticated session player.
        "deal_action_id": deal_action_id,  # Store the client retry identity for the wager action.
        "wager": normalized_wager,  # Store the exact aggregate wager debited once.
        "phase": "hold",  # Begin with an actionable five-card hold decision.
        "initial_hand": [card.code for card in initial_hand],  # Expose compact shared card codes.
        "holds": [],  # Begin with no selected card positions.
        "_draw_pool": [card.code for card in draw_pool],  # Keep replacements private but reload-safe.
        "wager_status": "pending",  # Require API reconciliation through the shared ledger.
        "payout_status": "not_ready",  # Prevent payout reconciliation before a final result.
        "created_at": created_at,  # Preserve the injected audit timestamp.
    }
    # Persist a private digest so settled deal retries can validate the original wager.
    round_state["_deal_plan_fingerprint"] = deal_plan_fingerprint(round_state)
    # Return the complete reload-safe round plan.
    return round_state


# Persist the complete selected hold set without drawing replacement cards.
def set_holds(round_state: dict, holds) -> dict:
    # Allow changes only while the initial hand is actionable.
    if round_state.get("phase") != "hold":
        # Reject stale selection actions after draw settlement.
        raise ConflictError("Hold choices are closed for this round")
    # Store the canonical sorted positions so repeated set operations are idempotent.
    round_state["holds"] = require_holds(holds)
    # Return the same state object for simple service persistence.
    return round_state


# Complete one held-card draw and calculate returned credits exactly once.
def draw(round_state: dict, draw_action_id: str, *, completed_at: str) -> dict:
    # Treat a same-action replay after settlement as an idempotent engine read.
    if round_state.get("phase") == "settled" and round_state.get("draw_action_id") == draw_action_id:
        # Return the already computed cards and payout without consuming replacements.
        return round_state
    # Reject a second action identity for an already settled round.
    if round_state.get("phase") == "settled":
        # Keep one round bound to one draw action and one payout key.
        raise ConflictError("Round was already settled by another action_id")
    # Require the only actionable pre-draw phase.
    if round_state.get("phase") != "hold":
        # Reject unknown or partially corrupted phases rather than guessing.
        raise ConflictError("This round cannot be drawn in its current phase")
    # Validate persisted holds again before using them as card positions.
    held_positions = set(require_holds(round_state.get("holds", [])))
    # Read the five-card source hand without changing persisted state yet.
    initial_hand = list(round_state.get("initial_hand", []))
    # Read the private replacement plan prepared before the wager debit.
    draw_pool = list(round_state.get("_draw_pool", []))
    # Reject missing or corrupted replacement state before partial settlement.
    if len(initial_hand) != 5 or len(draw_pool) < 5 - len(held_positions):
        # Surface reload corruption as a stable action conflict.
        raise ConflictError("Replacement cards are unavailable for this round")
    # Create an iterator so unheld positions consume replacement cards in deck order.
    replacements = iter(draw_pool)
    # Preserve held cards and replace every other card from the private plan.
    final_hand = [card if position in held_positions else next(replacements) for position, card in enumerate(initial_hand)]
    # Evaluate the final hand through the game-local wild-card classifier.
    outcome, multiplier = classify_hand(final_hand)
    # Calculate returned credits after the result is known.
    payout = round(round_state["wager"] * multiplier, 2)
    # Calculate net token movement for localized result presentation.
    net = round(payout - round_state["wager"], 2)
    # Classify the player-facing aggregate result without exposing internal phases.
    aggregate_outcome = "win" if net > 0 else "push" if net == 0 else "loss"
    # Store the client retry identity before payout reconciliation.
    round_state["draw_action_id"] = draw_action_id
    # Store the complete final hand for deterministic reload and display.
    round_state["final_hand"] = final_hand
    # Store the strongest documented paytable outcome key.
    round_state["result"] = outcome
    # Store the returned-credit multiplier used for audit evidence.
    round_state["multiplier"] = multiplier
    # Store the exact optional ledger credit amount.
    round_state["payout"] = payout
    # Store net movement separately from returned credits.
    round_state["net"] = net
    # Store win, push, or loss for player-facing status copy.
    round_state["outcome"] = aggregate_outcome
    # Mark deterministic card generation complete before any credit occurs.
    round_state["phase"] = "settled"
    # Mark a positive return pending while a losing round needs no zero ledger row.
    round_state["payout_status"] = "pending" if payout else "complete"
    # Store the injected completion time for tests and auditability.
    round_state["completed_at"] = completed_at
    # Remove unused private replacements once the final hand is durable.
    round_state.pop("_draw_pool", None)
    # Return the terminal JSON-compatible round.
    return round_state


# Find one round across the actionable slot and bounded recent history.
def round_by_id(state: dict, round_id: str):
    # Search the active round first because normal commands target it.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first exact identifier match while ignoring empty slots.
    return next((item for item in candidates if item and item.get("round_id") == round_id), None)


# Move one completed round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Clear the actionable slot only after final cards are computed.
    state["active_round"] = None
    # Remove an older copy before appending an idempotent retry result.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state["round_id"]]
    # Append the newest settled result in stable chronological order.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private replacement state from one public API round.
def public_round(round_state):
    # Preserve null active-round slots without constructing placeholders.
    if round_state is None:
        # Return the JSON-compatible null value.
        return None
    # Copy public fields while excluding every private underscore-prefixed key.
    return {key: value for key, value in round_state.items() if not key.startswith("_")}


# Build one public player-scoped state snapshot without mutating persistence.
def public_state(state: dict) -> dict:
    # Return sanitized active and recent rounds plus storage schema metadata when present.
    return {
        "active_round": public_round(state.get("active_round")),  # Sanitize the actionable round.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize reload history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage schema evidence.
    }
