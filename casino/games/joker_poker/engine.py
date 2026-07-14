"""Deterministic single-hand Joker Poker rules for GitHub issue #130.

Requirements used: CARD-001, POKER-001, SESSION-005, and proposed JP-130-001 through JP-130-004.
"""

# Import hashing so one authenticated deal action derives one stable round id.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math
# Import random generators for secure production shuffles and deterministic tests.
import random

# Import the shared standard deck primitive while keeping joker rules game-owned.
from casino.core.cards import RANKS, create_deck, coerce_card
# Import the shared standard five-card evaluator for every non-joker substitution.
from casino.core.poker import RANK_VALUES, evaluate_five
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger event owned by this game.
GAME_ID = "joker_poker"
# Represent the single wild joker with an encoding-safe compact code.
JOKER_CODE = "JK"
# Bound reload-safe settled history so one player document cannot grow forever.
RECENT_ROUND_LIMIT = 20
# Preserve fixed hand size for video-poker hold and draw rules.
HAND_SIZE = 5
# Define the game-owned Joker Poker paytable in returned-credit multipliers.
PAYTABLE = {
    "natural_royal_flush": 800,  # Return the top prize only for a joker-free royal flush.
    "five_of_a_kind": 200,  # Return the wild-only category made by four natural equals plus the joker.
    "wild_royal_flush": 100,  # Return the joker-completed royal flush below a natural royal.
    "straight_flush": 50,  # Return fifty credits for any other straight flush.
    "four_of_a_kind": 17,  # Return the Kings-or-Better Joker Poker four-kind row.
    "full_house": 7,  # Return seven credits for a full house.
    "flush": 5,  # Return five credits for a flush.
    "straight": 3,  # Return three credits for a straight.
    "three_of_a_kind": 2,  # Return two credits for trips.
    "two_pair": 1,  # Return the original wager for two pair.
    "kings_or_better": 1,  # Return the original wager for a qualifying high pair.
    "no_win": 0,  # Return no credits for non-qualifying hands.
}
# Keep tie-breaking display order stable when multiple joker substitutions share a multiplier.
OUTCOME_ORDER = tuple(PAYTABLE.keys())
# Compare paytable rows by value first and canonical row order second.
OUTCOME_STRENGTH = {name: (multiplier, len(OUTCOME_ORDER) - index) for index, (name, multiplier) in enumerate(PAYTABLE.items())}


# Build one fresh player-scoped Joker Poker state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive play-token wager before cards or state are created.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Joker Poker wager must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        wager = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Joker Poker wager must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge ledger amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Joker Poker wager must be between 0.01 and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return wager


# Normalize held-card positions before persisting or drawing.
def normalize_holds(value) -> list[int]:
    # Require a JSON array so strings and mappings cannot become positions.
    if not isinstance(value, list):
        # Explain the accepted positional representation.
        raise ValidationError("holds must be an array of card positions")
    # Reject booleans and non-integers before sorting the positions.
    if any(isinstance(position, bool) or not isinstance(position, int) for position in value):
        # Keep the error independent of Python's boolean/integer relationship.
        raise ValidationError("hold positions must be integers from 0 through 4")
    # Reject duplicate or out-of-range positions.
    if len(set(value)) != len(value) or any(position < 0 or position >= HAND_SIZE for position in value):
        # Keep one stable diagnostic for every invalid position set.
        raise ValidationError("hold positions must be unique integers from 0 through 4")
    # Sort positions so persisted state and deterministic tests remain stable.
    return sorted(value)


# Normalize one public card code while accepting the game-owned joker.
def normalize_card_code(card) -> str:
    # Treat the joker as a special game-local card outside the standard primitive.
    if str(card).upper() == JOKER_CODE:
        # Return the compact joker code unchanged.
        return JOKER_CODE
    # Delegate every natural card to the shared #96 primitive.
    return coerce_card(card).code


# Build the 53-card Joker Poker deck without changing shared card primitives.
def joker_deck() -> list[str]:
    # Convert the shared standard deck to compact codes before adding the joker.
    standard = [card.code for card in create_deck()]
    # Append exactly one game-owned joker card.
    return [*standard, JOKER_CODE]


# Deal one hand and private draw pool from a shuffled 53-card deck.
def deal_cards(*, seed=None) -> tuple[list[str], list[str]]:
    # Build a fresh one-joker deck for every round.
    deck = joker_deck()
    # Use deterministic entropy only when a focused test injects a seed.
    generator = random.Random(seed) if seed is not None else random.SystemRandom()
    # Shuffle the compact codes locally because the shared primitive rejects joker cards.
    generator.shuffle(deck)
    # Return the source hand and the remaining private draw pool.
    return deck[:HAND_SIZE], deck[HAND_SIZE:]


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter route paths.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"jp_{digest[:24]}"


# Detect a standard natural royal flush from five non-joker cards.
def is_royal_flush(cards) -> bool:
    # Evaluate the natural hand through the shared standard poker primitive.
    rank = evaluate_five(cards)
    # Require the straight-flush category and exact ten-through-ace ranks.
    return rank.name == "straight_flush" and {coerce_card(card).rank for card in cards} == {"10", "J", "Q", "K", "A"}


# Translate a non-joker five-card hand into the Joker Poker paytable.
def classify_natural(cards, *, wild: bool = False) -> tuple[str, int, str | None]:
    # Normalize every natural card before standard hand evaluation.
    normalized = [coerce_card(card) for card in cards]
    # Evaluate the standard five-card category through the shared primitive.
    rank = evaluate_five(normalized)
    # Distinguish natural and joker-completed royal flushes.
    if is_royal_flush(normalized):
        # Use the lower wild row whenever the joker supplied one royal card.
        outcome = "wild_royal_flush" if wild else "natural_royal_flush"
        # Return the row, multiplier, and no explicit joker substitute.
        return outcome, PAYTABLE[outcome], None
    # Apply the Kings-or-Better high-pair threshold for one-pair hands.
    if rank.name == "one_pair":
        # Read the pair value from the standard evaluator's first tie breaker.
        pair_value = rank.tiebreak[0]
        # Return the high-pair row only for kings or aces.
        outcome = "kings_or_better" if pair_value >= RANK_VALUES["K"] else "no_win"
        # Return the qualifying or losing row.
        return outcome, PAYTABLE[outcome], None
    # Preserve every standard category that has a Joker Poker paytable row.
    outcome = rank.name if rank.name in PAYTABLE else "no_win"
    # Return the row and its multiplier.
    return outcome, PAYTABLE[outcome], None


# Pick the strongest wild-joker substitution available to one final hand.
def classify_with_joker(cards) -> tuple[str, int, str | None]:
    # Normalize the public codes while preserving the joker marker.
    normalized = [normalize_card_code(card) for card in cards]
    # Reject malformed hands before any paytable selection.
    if len(normalized) != HAND_SIZE:
        # Keep the error specific to this game boundary.
        raise ValidationError("Joker Poker hands must contain exactly five cards")
    # Count the single game-owned joker.
    joker_count = normalized.count(JOKER_CODE)
    # Reject impossible hands with more than one joker.
    if joker_count > 1:
        # The rules profile freezes exactly one joker in the deck.
        raise ValidationError("Joker Poker supports exactly one joker")
    # Delegate ordinary hands to the natural classifier.
    if joker_count == 0:
        # Return the natural result without a joker substitution.
        return classify_natural(normalized, wild=False)
    # Split the natural cards away from the joker for substitution checks.
    natural_cards = [card for card in normalized if card != JOKER_CODE]
    # Count natural ranks to detect the wild-only five-of-a-kind row.
    rank_counts = {coerce_card(card).rank: [coerce_card(item).rank for item in natural_cards].count(coerce_card(card).rank) for card in natural_cards}
    # Recognize four natural equals plus the joker as five of a kind.
    if any(count == 4 for count in rank_counts.values()):
        # Return the frozen five-of-a-kind paytable row.
        return "five_of_a_kind", PAYTABLE["five_of_a_kind"], JOKER_CODE
    # Prepare a fallback losing result before checking all legal substitutions.
    best = ("no_win", PAYTABLE["no_win"], None)
    # Track natural codes already present so a joker never duplicates a physical card.
    used = set(natural_cards)
    # Try every absent standard card as the joker's optimal value.
    for replacement in [card.code for card in create_deck() if card.code not in used]:
        # Build a legal standard five-card hand for the shared evaluator.
        candidate = [*natural_cards, replacement]
        # Classify the candidate through the same paytable with wild royal handling.
        outcome, multiplier, _joker_as = classify_natural(candidate, wild=True)
        # Compare by paytable value and stable row order.
        if OUTCOME_STRENGTH[outcome] > OUTCOME_STRENGTH[best[0]]:
            # Store the strongest row and the selected joker substitute.
            best = (outcome, multiplier, replacement)
    # Return the strongest substitution result.
    return best


# Build one prepared round that can survive reload before its wager debit commits.
def create_round(player_id: str, wager, start_action_id: str, *, initial_hand: list[str], draw_pool: list[str], round_id: str, created_at: str, request_fingerprint: str) -> dict:
    # Normalize the wager again at the pure engine boundary.
    amount = normalize_wager(wager)
    # Normalize the initial source hand through the game card boundary.
    source_cards = [normalize_card_code(card) for card in initial_hand]
    # Require exactly five visible source cards.
    if len(source_cards) != HAND_SIZE:
        # Reject corrupt test fixtures and malformed engine calls.
        raise ValidationError("Joker Poker source hand must contain five cards")
    # Reject duplicate physical cards in the visible hand.
    if len(set(source_cards)) != len(source_cards):
        # Preserve a real 53-card deal model.
        raise ValidationError("Joker Poker source hand cannot contain duplicates")
    # Normalize the private draw pool before persisting it.
    pool = [normalize_card_code(card) for card in draw_pool]
    # Reject duplicate cards across the visible hand and draw pool.
    if len(set([*source_cards, *pool])) != len([*source_cards, *pool]):
        # Preserve deterministic draw safety.
        raise ValidationError("Joker Poker draw pool cannot duplicate dealt cards")
    # Return JSON-compatible prepared state with draw cards kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting deal retries.
        "wager": amount,  # Store the single-hand wager.
        "phase": "hold",  # Await held-card choices.
        "initial_hand": source_cards,  # Expose the visible five-card source hand.
        "holds": [],  # Start with no selected held positions.
        "_draw_pool": pool,  # Persist the deterministic private draw order.
        "draw_action_id": None,  # Reserve settlement retry identity.
        "draw_fingerprint": None,  # Reserve draw semantic conflict detection.
        "result": None,  # Reserve the final hand classification.
        "total_payout": 0.0,  # Reserve the returned play-token amount.
        "net": None,  # Reserve the final net result after the wager.
        "wager_status": "pending",  # Require the service to ensure one debit.
        "settlement_status": "not_ready",  # Prevent credits before draw.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Persist held positions while the source hand remains actionable.
def set_holds(round_state: dict, holds) -> dict:
    # Allow hold changes only before the draw action settles the round.
    if round_state.get("phase") != "hold":
        # Reject stale browser actions after settlement.
        raise ConflictError("Joker Poker hold choices are closed")
    # Persist a canonical sorted position list.
    round_state["holds"] = normalize_holds(holds)
    # Return the same state object for simple API persistence.
    return round_state


# Complete the hand from held cards and the private draw pool.
def draw(round_state: dict, draw_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat an exact repeated engine call after settlement as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed action identity after settlement.
        if round_state.get("draw_action_id") != draw_action_id:
            # Preserve the original terminal result.
            raise ConflictError("Joker Poker round was already settled by another draw")
        # Reject a changed semantic fingerprint after settlement.
        if round_state.get("draw_fingerprint") != request_fingerprint:
            # Preserve the original terminal result.
            raise ConflictError("Joker Poker round was already settled by another draw")
        # Return the existing result without consuming private cards.
        return round_state
    # Require the only actionable draw phase.
    if round_state.get("phase") != "hold":
        # Reject corrupt or stale transitions explicitly.
        raise ConflictError("Joker Poker round cannot draw in its current phase")
    # Validate persisted holds again before using them as positions.
    holds = set(normalize_holds(round_state.get("holds", [])))
    # Read the five visible source cards.
    source_cards = list(round_state["initial_hand"])
    # Read the deterministic private draw pool.
    draw_pool = list(round_state.get("_draw_pool") or [])
    # Reject missing private state instead of generating replacement entropy.
    if len(draw_pool) < HAND_SIZE:
        # Keep deterministic reload behavior fail-closed.
        raise ConflictError("Joker Poker draw cards are unavailable")
    # Create an iterator over private replacement cards.
    replacements = iter(draw_pool)
    # Preserve held cards and fill unheld positions from the private pool.
    final_cards = [card if position in holds else next(replacements) for position, card in enumerate(source_cards)]
    # Classify the final hand under game-owned wild-joker rules.
    outcome, multiplier, joker_as = classify_with_joker(final_cards)
    # Calculate the one returned-credit amount for the single hand.
    payout = round(round_state["wager"] * multiplier, 2)
    # Store the public result payload.
    round_state["result"] = {"cards": final_cards, "outcome": outcome, "multiplier": multiplier, "payout": payout, "joker_as": joker_as}
    # Store the returned play-token amount.
    round_state["total_payout"] = payout
    # Store net movement after the original wager.
    round_state["net"] = round(payout - round_state["wager"], 2)
    # Store the settlement action identity for safe retries.
    round_state["draw_action_id"] = draw_action_id
    # Store the semantic fingerprint that detects conflicting retries.
    round_state["draw_fingerprint"] = request_fingerprint
    # Mark deterministic card evaluation complete before ledger settlement.
    round_state["phase"] = "settled"
    # Require one credit only for positive returned credits.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Remove private draw cards after terminal results are durable.
    round_state.pop("_draw_pool", None)
    # Return the same mutable round for service persistence.
    return round_state


# Find one round by its deal action identity across active and recent state.
def round_for_start_action(state: dict, action_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first exact identity match while ignoring empty slots.
    return next((item for item in candidates if item and item.get("start_action_id") == action_id), None)


# Find one round by its server identifier across active and recent state.
def round_by_id(state: dict, round_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first matching round while ignoring empty slots.
    return next((item for item in candidates if item and item.get("round_id") == round_id), None)


# Find whether an action identity already belongs to any retained command.
def action_owner(state: dict, action_id: str):
    # Search every active and retained round for either action stage.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the matching round and stage for conflict detection.
    for item in candidates:
        # Skip empty active slots.
        if not item:
            # Continue to the next retained round.
            continue
        # Match the deal action before the optional draw action.
        if item.get("start_action_id") == action_id:
            # Report the deal stage and owning round.
            return item, "deal"
        # Match a committed or prepared draw action.
        if item.get("draw_action_id") == action_id:
            # Report the draw stage and owning round.
            return item, "draw"
    # Return no owner when the action id remains unused in retained state.
    return None


# Move a settled round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Normalize the optional active slot before reading its identifier.
    active_round = state.get("active_round") or {}
    # Clear the actionable slot only when it contains this exact round.
    if active_round.get("round_id") == round_state.get("round_id"):
        # Prevent further hold edits against the settled round.
        state["active_round"] = None
    # Remove any older copy before appending an idempotent settlement.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the newest settled result in stable chronological order.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private recovery fields from one public round payload.
def public_round(round_state):
    # Preserve a null active-round slot without creating a placeholder.
    if round_state is None:
        # Return JSON null through the router.
        return None
    # Exclude draw cards and internal fingerprints from public responses.
    private_fields = {"_draw_pool", "request_fingerprint", "draw_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide private draw cards.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
