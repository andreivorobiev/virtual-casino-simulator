"""Pure Caribbean Stud rules for the isolated issue #132 draft slice."""

# Import hashing so player-scoped round ids never expose raw action ids.
import hashlib
# Import finite-number checks before ledger-compatible wagers are accepted.
import math

# Import shared card primitives from the approved #96 card package.
from casino.core.cards import RANKS, coerce_card, shuffled_deck
# Import shared five-card poker evaluation from the approved #96 poker package.
from casino.core.poker import evaluate_five
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger row owned by this game.
GAME_ID = "caribbean_stud"
# Keep bounded history small enough for single-player local state documents.
RECENT_ROUND_LIMIT = 20
# Define the fixed call wager multiplier for Caribbean Stud.
CALL_MULTIPLIER = 2
# Map ranks to numeric values for dealer qualification checks.
RANK_VALUES = {rank: value for value, rank in enumerate(RANKS, start=2)}
# Pay the call bet by standard Caribbean Stud odds after dealer qualification.
CALL_ODDS = {
    "high_card": 1,  # High card pays even money on the call bet.
    "one_pair": 1,  # One pair pays even money on the call bet.
    "two_pair": 2,  # Two pair pays 2:1 on the call bet.
    "three_of_a_kind": 3,  # Three of a kind pays 3:1 on the call bet.
    "straight": 4,  # Straight pays 4:1 on the call bet.
    "flush": 5,  # Flush pays 5:1 on the call bet.
    "full_house": 7,  # Full house pays 7:1 on the call bet.
    "four_of_a_kind": 20,  # Four of a kind pays 20:1 on the call bet.
    "straight_flush": 50,  # Straight flush pays 50:1 unless upgraded below.
    "royal_flush": 100,  # Royal flush pays 100:1 on the call bet.
}


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive ante before any card or ledger work.
def normalize_ante(value) -> float:
    # Reject booleans because Python otherwise treats them as numbers.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Caribbean Stud ante must be a positive play-token amount")
    # Convert numeric input to the ledger's two-decimal precision.
    try:
        # Round only after parsing so strings and integers share one boundary.
        ante = round(float(value), 2)
    # Translate malformed input into a stable public validation error.
    except (TypeError, ValueError):
        # Avoid echoing hostile values in public diagnostics.
        raise ValidationError("Caribbean Stud ante must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge local-simulator wagers.
    if ante < 0.01 or ante > 100_000 or not math.isfinite(ante):
        # Preserve the accepted range in one documented message.
        raise ValidationError("Caribbean Stud ante must be between 0.01 and 100000 play tokens")
    # Return the normalized wager used by fingerprints and ledger events.
    return ante


# Derive one stable route id from authenticated player and public deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so raw action ids never enter route paths.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"cs_{digest[:24]}"


# Normalize a five-card hand and reject impossible duplicate physical cards.
def normalize_hand(cards) -> list[str]:
    # Require exactly five entries for this table-poker game.
    if not isinstance(cards, (list, tuple)) or len(cards) != 5:
        # Keep incomplete or oversized fixtures outside the engine.
        raise ValidationError("Caribbean Stud hands must contain exactly five cards")
    # Normalize each supplied card through the shared primitive.
    try:
        # Convert every card to its compact ASCII state code.
        normalized = [coerce_card(card).code for card in cards]
    # Translate primitive parsing failures into a public validation shape.
    except ValueError as exc:
        # Hide the low-level parser representation from route callers.
        raise ValidationError("Caribbean Stud cards must use a standard deck") from exc
    # Reject impossible replacement of one physical card within a hand.
    if len(set(normalized)) != len(normalized):
        # Preserve the without-replacement invariant before ranking.
        raise ValidationError("Caribbean Stud cards must be dealt without replacement")
    # Return compact codes suitable for JSON state.
    return normalized


# Deal one player hand and one dealer hand without replacement.
def deal_hands(*, seed=None, cards=None) -> tuple[list[str], list[str]]:
    # Use injected cards only for focused deterministic tests.
    source_cards = cards if cards is not None else shuffled_deck(seed=seed)
    # Normalize the first ten physical cards in deal order.
    dealt = [coerce_card(card).code for card in source_cards[:10]]
    # Require enough cards for a complete one-player Caribbean Stud round.
    if len(dealt) != 10:
        # Reject malformed test shoes before state is built.
        raise ValidationError("Caribbean Stud requires ten cards for a round")
    # Reject duplicate physical cards across player and dealer hands.
    if len(set(dealt)) != len(dealt):
        # Preserve a single standard deck without replacement.
        raise ValidationError("Caribbean Stud cards must be dealt without replacement")
    # Return player cards first and dealer cards second.
    return dealt[:5], dealt[5:]


# Return the payout-table name for one evaluated player hand.
def payout_name(rank) -> str:
    # Identify an ace-high straight flush as the royal flush top award.
    if rank.name == "straight_flush" and rank.tiebreak == (14,):
        # Return the table name used by rules, UI, and ledger details.
        return "royal_flush"
    # Return the shared evaluator category for every other hand.
    return rank.name


# Convert an evaluated hand into a JSON-compatible public summary.
def hand_summary(cards) -> dict:
    # Evaluate exactly five normalized cards through the shared poker primitive.
    rank = evaluate_five(normalize_hand(cards))
    # Return comparison data without exposing dataclass internals.
    return {
        "name": payout_name(rank),  # Publish the payout-table category.
        "category": rank.category,  # Preserve numeric strength for tests and clients.
        "tiebreak": list(rank.tiebreak),  # Preserve deterministic comparison tie breakers.
    }


# Decide whether the dealer has ace-king high or a better made hand.
def dealer_qualifies(dealer_summary: dict) -> bool:
    # Any pair or better qualifies immediately.
    if dealer_summary["category"] >= 1:
        # Report a qualifying made hand.
        return True
    # High-card hands qualify only when their top two ranks are ace and king.
    return dealer_summary["tiebreak"][:2] == [14, 13]


# Compare two five-card poker summaries from the shared evaluator.
def compare_summaries(player_summary: dict, dealer_summary: dict) -> int:
    # Build the player's complete comparison tuple.
    player_key = (player_summary["category"], *player_summary["tiebreak"])
    # Build the dealer's complete comparison tuple.
    dealer_key = (dealer_summary["category"], *dealer_summary["tiebreak"])
    # Return positive, zero, or negative from the player's perspective.
    return (player_key > dealer_key) - (player_key < dealer_key)


# Build one prepared round that can survive reload before ante debit evidence.
def create_round(player_id: str, ante, deal_action_id: str, *, player_hand, dealer_hand, round_id: str, created_at: str, request_fingerprint: str) -> dict:
    # Normalize ante once at the pure engine boundary.
    amount = normalize_ante(ante)
    # Normalize the player cards through shared card validation.
    normalized_player = normalize_hand(player_hand)
    # Normalize the private dealer hand through the same boundary.
    normalized_dealer = normalize_hand(dealer_hand)
    # Reject a duplicated physical card across the two hands.
    if len(set([*normalized_player, *normalized_dealer])) != 10:
        # Preserve single-deck deal integrity.
        raise ValidationError("Caribbean Stud cards must be dealt without replacement")
    # Return JSON-compatible state with the dealer's full hand kept private.
    return {
        "round_id": round_id,  # Correlate routes, state, and ledger rows.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "deal_action_id": deal_action_id,  # Preserve ante retry identity.
        "deal_fingerprint": request_fingerprint,  # Detect changed ante retries.
        "ante": amount,  # Store the committed ante amount.
        "call_wager": round(amount * CALL_MULTIPLIER, 2),  # Store the fixed raise amount.
        "phase": "decision",  # Await fold or call.
        "player_hand": normalized_player,  # Publish the player's complete hand.
        "dealer_upcard": normalized_dealer[0],  # Publish exactly one dealer card.
        "_dealer_hand": normalized_dealer,  # Persist the full dealer hand privately.
        "player_rank": hand_summary(normalized_player),  # Publish the player's rank.
        "dealer_rank": None,  # Reserve the dealer rank until showdown.
        "dealer_qualifies": None,  # Reserve dealer qualification until call.
        "outcome": None,  # Reserve the terminal outcome.
        "payout": 0.0,  # Reserve total returned play tokens.
        "net": None,  # Reserve net result after committed wagers.
        "ante_status": "pending",  # Require service ledger proof.
        "call_status": "not_ready",  # Prevent a call debit before a call action.
        "settlement_status": "not_ready",  # Prevent credits before a call result.
        "created_at": created_at,  # Record injected audit time.
    }


# Resolve one call showdown without touching a player balance.
def settle_call(round_state: dict, call_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat exact repeated engine calls as idempotent reads.
    if round_state.get("phase") == "settled":
        # Reject a changed action identity after settlement.
        if round_state.get("call_action_id") != call_action_id:
            # Preserve the original terminal decision.
            raise ConflictError("Caribbean Stud round was already settled by another action")
        # Return the existing terminal round unchanged.
        return round_state
    # Require the decision phase before accepting a call.
    if round_state.get("phase") != "decision":
        # Reject corrupt or stale state transitions.
        raise ConflictError("Caribbean Stud round cannot accept a call in its current phase")
    # Read the private dealer hand persisted at deal time.
    dealer_hand = round_state.get("_dealer_hand")
    # Reject missing private state rather than generating replacement cards.
    if not dealer_hand:
        # Keep reload behavior fail-closed.
        raise ConflictError("Caribbean Stud dealer hand is unavailable")
    # Summarize the dealer hand through the shared poker evaluator.
    dealer_summary = hand_summary(dealer_hand)
    # Decide whether the dealer reaches ace-king high or better.
    qualifies = dealer_qualifies(dealer_summary)
    # Compare only when the dealer qualifies.
    comparison = compare_summaries(round_state["player_rank"], dealer_summary) if qualifies else 1
    # Read the fixed table odds for the player's hand category.
    odds = CALL_ODDS[round_state["player_rank"]["name"]]
    # Read the committed ante amount.
    ante = round_state["ante"]
    # Read the fixed call wager amount.
    call_wager = round_state["call_wager"]
    # Branch when the dealer does not qualify.
    if not qualifies:
        # Ante wins even money and the call wager pushes.
        outcome, payout = "dealer_not_qualified", round((ante * 2) + call_wager, 2)
    # Branch when the player beats the qualified dealer.
    elif comparison > 0:
        # Ante wins even money and the call wager receives table odds plus stake.
        outcome, payout = "player_win", round((ante * 2) + call_wager + (call_wager * odds), 2)
    # Branch when both five-card hands compare exactly equal.
    elif comparison == 0:
        # Both ante and call wagers push.
        outcome, payout = "push", round(ante + call_wager, 2)
    # Handle a qualified dealer win.
    else:
        # No returned-token credit is owed.
        outcome, payout = "dealer_win", 0.0
    # Store the public call action identity.
    round_state["call_action_id"] = call_action_id
    # Store the call semantic fingerprint for replay conflict detection.
    round_state["call_fingerprint"] = request_fingerprint
    # Publish the dealer hand only after a call.
    round_state["dealer_hand"] = normalize_hand(dealer_hand)
    # Publish the dealer rank after showdown.
    round_state["dealer_rank"] = dealer_summary
    # Publish dealer qualification after showdown.
    round_state["dealer_qualifies"] = qualifies
    # Store the terminal outcome.
    round_state["outcome"] = outcome
    # Store the total returned token amount.
    round_state["payout"] = payout
    # Store net after ante and call debits.
    round_state["net"] = round(payout - ante - call_wager, 2)
    # Store the hand-specific odds used for the call bet.
    round_state["call_odds"] = odds
    # Store the deterministic completion time.
    round_state["completed_at"] = completed_at
    # Mark the public game phase terminal before ledger settlement.
    round_state["phase"] = "settled"
    # Require the service to commit the call wager debit.
    round_state["call_status"] = "pending"
    # Require a credit only when returned tokens are due.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Return the mutated round for persistence.
    return round_state


# Resolve one fold decision without revealing the dealer's private hand.
def settle_fold(round_state: dict, fold_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat exact repeated fold calls as idempotent reads.
    if round_state.get("phase") == "settled":
        # Reject a changed action identity after terminal state.
        if round_state.get("fold_action_id") != fold_action_id:
            # Preserve the original terminal decision.
            raise ConflictError("Caribbean Stud round was already settled by another action")
        # Return the existing folded round unchanged.
        return round_state
    # Require the decision phase before accepting a fold.
    if round_state.get("phase") != "decision":
        # Reject stale or corrupted state transitions.
        raise ConflictError("Caribbean Stud round cannot accept a fold in its current phase")
    # Store the public fold action identity.
    round_state["fold_action_id"] = fold_action_id
    # Store the fold semantic fingerprint for replay conflict detection.
    round_state["fold_fingerprint"] = request_fingerprint
    # Store the terminal fold outcome.
    round_state["outcome"] = "fold"
    # Store zero returned tokens because the ante was already debited.
    round_state["payout"] = 0.0
    # Store the ante loss as the net result.
    round_state["net"] = -round_state["ante"]
    # Store the deterministic completion time.
    round_state["completed_at"] = completed_at
    # Mark the public game phase terminal.
    round_state["phase"] = "settled"
    # Mark no call wager as owed after folding.
    round_state["call_status"] = "not_ready"
    # Mark settlement complete because no returned-token credit exists.
    round_state["settlement_status"] = "complete"
    # Return the mutated round for persistence.
    return round_state


# Find one round by its deal action identity across active and recent state.
def round_for_deal_action(state: dict, action_id: str):
    # Search active state before bounded terminal history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first matching round while skipping empty slots.
    return next((item for item in candidates if item and item.get("deal_action_id") == action_id), None)


# Find one round by its server identifier across active and recent state.
def round_by_id(state: dict, round_id: str):
    # Search active state before bounded terminal history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the matching round while skipping empty slots.
    return next((item for item in candidates if item and item.get("round_id") == round_id), None)


# Find whether an action identity already belongs to a retained command.
def action_owner(state: dict, action_id: str):
    # Search every active and retained round for all public action stages.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Check each candidate independently.
    for item in candidates:
        # Skip empty active slots.
        if not item:
            # Continue to the next retained round.
            continue
        # Match the ante/deal action identity.
        if item.get("deal_action_id") == action_id:
            # Report the owning round and stage.
            return item, "deal"
        # Match the call decision identity.
        if item.get("call_action_id") == action_id:
            # Report the owning round and stage.
            return item, "call"
        # Match the fold decision identity.
        if item.get("fold_action_id") == action_id:
            # Report the owning round and stage.
            return item, "fold"
    # Report that no retained command owns the action id.
    return None


# Move a terminal round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Read the active slot defensively.
    active_round = state.get("active_round") or {}
    # Clear the active slot only when it still owns this round.
    if active_round.get("round_id") == round_state.get("round_id"):
        # Prevent a second decision against the same round.
        state["active_round"] = None
    # Remove any older copy before appending the terminal result.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the newest terminal round.
    recent.append(round_state)
    # Keep only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private fields from one public round payload.
def public_round(round_state):
    # Preserve a null active round as JSON null.
    if round_state is None:
        # Return no public round.
        return None
    # Exclude hidden cards, fingerprints, and internal movement stages.
    private_fields = {"_dealer_hand", "deal_fingerprint", "call_fingerprint", "fold_fingerprint", "movement_stage"}
    # Return a detached shallow payload containing only public fields.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving optional storage metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide the private dealer hand.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }


# Return immutable rules suitable for API and frontend rendering.
def rules_payload() -> dict:
    # Publish fixed rules without referencing shared catalog integration.
    return {
        "dealer_qualification": "ace_king_or_better",  # Document qualification.
        "call_multiplier": CALL_MULTIPLIER,  # Document call wager size.
        "call_odds": dict(CALL_ODDS),  # Publish the payout table.
        "dealer_upcards": 1,  # Document the single exposed dealer card.
    }
