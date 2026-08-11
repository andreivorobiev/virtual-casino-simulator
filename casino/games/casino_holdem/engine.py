# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic Casino Hold'em rules for GitHub issue #139.

Requirements used: CARD-001, POKER-001, LEDGER-005, LEDGER-006, LEDGER-023, SESSION-005, TOKEN-001.
"""

# Import hashing so authenticated deal actions derive stable route ids.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math

# Import shared card primitives allocated by the merged #96 lane.
from casino.core.cards import coerce_card, shuffled_deck
# Import shared seven-card poker evaluation allocated by the merged #96 lane.
from casino.core.poker import RANK_VALUES, evaluate_hand
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger row owned by this game.
GAME_ID = "casino_holdem"
# Offer the two player decisions in the documented post-flop decision phase.
DECISIONS = ("call", "fold")
# Require the call wager to be exactly twice the original ante.
CALL_MULTIPLIER = 2
# Bound reload-safe history so one player document cannot grow without limit.
RECENT_ROUND_LIMIT = 20
# Define dealer qualification as one pair of fours or any stronger made hand.
DEALER_MINIMUM_PAIR_VALUE = RANK_VALUES["4"]
# Define returned-credit multipliers for the ante side when the player is paid.
ANTE_RETURN_MULTIPLIERS = {
    "royal_flush": 101,  # Return stake plus one hundred-to-one for a royal flush.
    "straight_flush": 21,  # Return stake plus twenty-to-one for a straight flush.
    "four_of_a_kind": 11,  # Return stake plus ten-to-one for four of a kind.
    "full_house": 4,  # Return stake plus three-to-one for a full house.
    "flush": 3,  # Return stake plus two-to-one for a flush.
    "straight": 2,  # Return stake plus even money for a straight.
    "three_of_a_kind": 2,  # Return stake plus even money for trips or lower.
    "two_pair": 2,  # Return stake plus even money for two pair.
    "one_pair": 2,  # Return stake plus even money for one pair.
    "high_card": 2,  # Return stake plus even money for high-card wins.
}


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive ante before cards or state are created.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Casino Hold'em ante must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        wager = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Casino Hold'em ante must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge ledger amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Casino Hold'em ante must be between 0.01 and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return wager


# Normalize the only player decision made after the flop.
def normalize_decision(value) -> str:
    # Accept only strings so mappings and numeric aliases cannot become decisions.
    decision = value.strip().lower() if isinstance(value, str) else ""
    # Reject anything outside the two documented actions.
    if decision not in DECISIONS:
        # Keep the stable diagnostic suitable for the additive API contract.
        raise ValidationError("decision must be call or fold")
    # Return the canonical lower-case decision.
    return decision


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter a route path.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"choldem_{digest[:24]}"


# Normalize fixture or shuffled cards into the Casino Hold'em layout.
def deal_layout(*, seed=None, fixture=None) -> dict:
    # Read explicit focused-test fixtures before using entropy.
    if fixture is not None:
        # Normalize fixture player hole cards through shared validation.
        player_cards = [coerce_card(card).code for card in fixture["player_cards"]]
        # Normalize fixture dealer hole cards through shared validation.
        dealer_cards = [coerce_card(card).code for card in fixture["dealer_cards"]]
        # Normalize fixture five-card board through shared validation.
        community_cards = [coerce_card(card).code for card in fixture["community_cards"]]
    # Deal a production or seeded test layout from one shuffled deck.
    else:
        # Shuffle through the shared primitive using secure entropy unless a seed is injected.
        cards = shuffled_deck(seed=seed)
        # Deal two player cards, two dealer cards, and five community cards without replacement.
        player_cards = [card.code for card in cards[0:2]]
        # Deal the dealer hole cards after the player cards for deterministic tests.
        dealer_cards = [card.code for card in cards[2:4]]
        # Deal flop, turn, and river from the same deck.
        community_cards = [card.code for card in cards[4:9]]
    # Reject malformed fixtures that do not match the table layout.
    if len(player_cards) != 2 or len(dealer_cards) != 2 or len(community_cards) != 5:
        # Fail closed rather than producing partial public state.
        raise ValidationError("Casino Hold'em requires two player cards, two dealer cards, and five community cards")
    # Combine every physical card for duplicate detection.
    all_cards = [*player_cards, *dealer_cards, *community_cards]
    # Reject duplicated physical cards before state is persisted.
    if len(set(all_cards)) != len(all_cards):
        # Surface an impossible table layout as a validation error.
        raise ValidationError("Casino Hold'em cards must be dealt without replacement")
    # Return public and private layout pieces in deterministic order.
    return {"player_cards": player_cards, "dealer_cards": dealer_cards, "community_cards": community_cards}


# Translate shared poker categories into the Casino Hold'em paytable keys.
def classify_hand(cards) -> tuple[str, tuple[int, ...]]:
    # Evaluate the best five from the seven-card table hand.
    rank = evaluate_hand(cards)
    # Treat ace-high straight flush with broadway cards as a royal flush.
    if rank.name == "straight_flush" and rank.tiebreak == (14,):
        # Return the distinct paytable row while preserving comparison strength separately.
        return "royal_flush", rank.comparison_key
    # Return every other shared category unchanged.
    return rank.name, rank.comparison_key


# Determine whether the dealer qualifies under the selected rules profile.
def dealer_qualifies(dealer_rank_name: str, dealer_key: tuple[int, ...]) -> bool:
    # Any made hand above one pair qualifies automatically.
    if dealer_key[0] > 1:
        # Return true for two pair or stronger categories.
        return True
    # High-card dealer hands do not qualify.
    if dealer_key[0] == 0:
        # Return false for non-pair dealer hands.
        return False
    # One-pair dealer hands qualify only when the pair is fours or better.
    return dealer_key[1] >= DEALER_MINIMUM_PAIR_VALUE


# Build one reload-safe round after the ante is requested.
def create_round(player_id: str, wager, start_action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Normalize the ante at the pure engine boundary.
    amount = normalize_wager(wager)
    # Deal all cards up front so reloads cannot change the eventual showdown.
    layout = deal_layout(seed=seed, fixture=fixture)
    # Return JSON-compatible prepared state with dealer, turn, and river kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "wager": amount,  # Store the ante amount.
        "phase": "decision",  # Await one call-or-fold decision after the flop.
        "player_cards": layout["player_cards"],  # Publish player hole cards.
        "community_cards": layout["community_cards"][:3],  # Publish only the flop before the decision.
        "_dealer_cards": layout["dealer_cards"],  # Persist dealer cards privately until showdown.
        "_turn_card": layout["community_cards"][3],  # Persist the turn privately until call settlement.
        "_river_card": layout["community_cards"][4],  # Persist the river privately until call settlement.
        "decision": None,  # Reserve the later call-or-fold decision.
        "decision_action_id": None,  # Reserve settlement retry identity.
        "ante_status": "pending",  # Require the service to ensure one ante debit.
        "call_status": "not_ready",  # Prevent call debits before the decision.
        "settlement_status": "not_ready",  # Prevent credits before terminal evaluation.
        "payout": 0.0,  # Reserve total returned play tokens.
        "net": None,  # Reserve final net movement.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Prepare a call decision before the service commits the call debit.
def prepare_call(round_state: dict, decision_action_id: str, *, request_fingerprint: str) -> dict:
    # Treat an exact repeated prepare as idempotent.
    if round_state.get("phase") == "called":
        # Reject changed action identities for the already-prepared call.
        if round_state.get("decision_action_id") != decision_action_id or round_state.get("decision_fingerprint") != request_fingerprint:
            # Preserve the original decision and ledger identity.
            raise ConflictError("Casino Hold'em call was already prepared by another action")
        # Return the prepared round unchanged.
        return round_state
    # Require the post-flop decision phase for a new call.
    if round_state.get("phase") != "decision":
        # Reject stale actions after settlement.
        raise ConflictError("Casino Hold'em round cannot accept a call in its current phase")
    # Store the player decision.
    round_state["decision"] = "call"
    # Store the settlement action identity for retry-safe call debit and payout.
    round_state["decision_action_id"] = decision_action_id
    # Store the semantic fingerprint for conflict detection.
    round_state["decision_fingerprint"] = request_fingerprint
    # Calculate the required two-times ante call wager.
    round_state["call_wager"] = round(round_state["wager"] * CALL_MULTIPLIER, 2)
    # Move into an intermediate state that can recover a committed call debit.
    round_state["phase"] = "called"
    # Require the service to commit or recover the call debit.
    round_state["call_status"] = "pending"
    # Keep settlement locked until the call debit is proven.
    round_state["settlement_status"] = "not_ready"
    # Return the mutated round for persistence.
    return round_state


# Restore a call preparation when its debit did not commit.
def reset_uncommitted_call(round_state: dict) -> dict:
    # Return only prepared-call rounds to the decision state.
    if round_state.get("phase") == "called":
        # Remove the uncommitted decision identity.
        round_state.pop("decision_action_id", None)
        # Remove the uncommitted decision fingerprint.
        round_state.pop("decision_fingerprint", None)
        # Remove the derived call wager.
        round_state.pop("call_wager", None)
        # Reset the visible decision.
        round_state["decision"] = None
        # Return the round to the call-or-fold choice.
        round_state["phase"] = "decision"
        # Mark call settlement unavailable again.
        round_state["call_status"] = "not_ready"
    # Return the recovered active round.
    return round_state


# Resolve a committed call into a terminal showdown without touching balances.
def resolve_called_round(round_state: dict, *, completed_at: str) -> dict:
    # Treat repeated resolution as an idempotent read.
    if round_state.get("phase") == "settled":
        # Return the stable terminal state.
        return round_state
    # Require the intermediate call state after call debit proof exists.
    if round_state.get("phase") != "called":
        # Reject stale or corrupt transitions explicitly.
        raise ConflictError("Casino Hold'em round is not ready for showdown")
    # Require call debit proof before any payout can be calculated.
    if round_state.get("call_status") != "complete":
        # Fail closed rather than settling a free call.
        raise ConflictError("Casino Hold'em call wager is not committed")
    # Read the private dealer and board cards persisted at deal time.
    dealer_cards = [coerce_card(card).code for card in round_state.get("_dealer_cards", [])]
    # Read the private turn card.
    turn_card = coerce_card(round_state.get("_turn_card")).code
    # Read the private river card.
    river_card = coerce_card(round_state.get("_river_card")).code
    # Publish the complete five-card board after the player calls.
    community_cards = [*round_state["community_cards"], turn_card, river_card]
    # Classify the player's best seven-card hand.
    player_rank, player_key = classify_hand([*round_state["player_cards"], *community_cards])
    # Classify the dealer's best seven-card hand.
    dealer_rank, dealer_key = classify_hand([*dealer_cards, *community_cards])
    # Determine whether the dealer hand is strong enough to qualify.
    qualifies = dealer_qualifies(dealer_rank, dealer_key)
    # Compare hands only when the dealer qualifies.
    comparison = (player_key > dealer_key) - (player_key < dealer_key)
    # Resolve the public showdown outcome.
    if not qualifies:
        # Non-qualifying dealer pays ante and pushes the call.
        outcome = "dealer_not_qualified"
    # Resolve a player win against a qualified dealer.
    elif comparison > 0:
        # Player beats the dealer at showdown.
        outcome = "player_win"
    # Resolve an exact poker tie against a qualified dealer.
    elif comparison == 0:
        # Equal best hands push both wagers.
        outcome = "push"
    # Resolve the dealer win case.
    else:
        # Dealer beats the player at showdown.
        outcome = "dealer_win"
    # Calculate returned credits for the ante wager.
    ante_credit = round(round_state["wager"] * ANTE_RETURN_MULTIPLIERS[player_rank], 2) if outcome in ("dealer_not_qualified", "player_win") else round_state["wager"] if outcome == "push" else 0.0
    # Calculate returned credits for the call wager.
    call_credit = round_state["call_wager"] if outcome in ("dealer_not_qualified", "push") else round(round_state["call_wager"] * 2, 2) if outcome == "player_win" else 0.0
    # Calculate one aggregate returned-token credit.
    payout = round(ante_credit + call_credit, 2)
    # Calculate total amount already debited through ante plus call.
    total_wagered = round(round_state["wager"] + round_state["call_wager"], 2)
    # Publish the formerly private cards and result details.
    round_state["dealer_cards"] = dealer_cards
    # Publish the complete community board.
    round_state["community_cards"] = community_cards
    # Store the player's paytable category.
    round_state["player_rank"] = player_rank
    # Store the dealer's category for transparency.
    round_state["dealer_rank"] = dealer_rank
    # Store dealer qualification result.
    round_state["dealer_qualifies"] = qualifies
    # Store the player-facing outcome.
    round_state["outcome"] = outcome
    # Store returned-credit components for audit and UI presentation.
    round_state["ante_credit"] = ante_credit
    # Store the call returned-credit component.
    round_state["call_credit"] = call_credit
    # Store aggregate returned play tokens.
    round_state["payout"] = payout
    # Store net movement after both debits.
    round_state["net"] = round(payout - total_wagered, 2)
    # Mark deterministic evaluation complete.
    round_state["phase"] = "settled"
    # Require one credit only when returned tokens are due.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Remove private card fields after their public equivalents exist.
    round_state.pop("_dealer_cards", None)
    # Remove the private turn card.
    round_state.pop("_turn_card", None)
    # Remove the private river card.
    round_state.pop("_river_card", None)
    # Return the same mutable round for service persistence.
    return round_state


# Resolve a fold decision without any extra ledger movement.
def fold_round(round_state: dict, decision_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat an exact repeated fold as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed terminal decision.
        if round_state.get("decision") != "fold" or round_state.get("decision_action_id") != decision_action_id or round_state.get("decision_fingerprint") != request_fingerprint:
            # Preserve the original terminal state.
            raise ConflictError("Casino Hold'em round was already settled by another action")
        # Return the already-folded round.
        return round_state
    # Require the decision phase for folding.
    if round_state.get("phase") != "decision":
        # Reject stale actions after a call is prepared.
        raise ConflictError("Casino Hold'em round cannot be folded in its current phase")
    # Store the player decision.
    round_state["decision"] = "fold"
    # Store the terminal action identity.
    round_state["decision_action_id"] = decision_action_id
    # Store the semantic fingerprint for retry checks.
    round_state["decision_fingerprint"] = request_fingerprint
    # Classify the result without revealing future cards.
    round_state["outcome"] = "folded"
    # Store zero returned play tokens.
    round_state["payout"] = 0.0
    # Store net loss of the already-debited ante.
    round_state["net"] = -round_state["wager"]
    # Mark the round terminal.
    round_state["phase"] = "settled"
    # No call debit is created for folds.
    round_state["call_status"] = "not_ready"
    # No returned-token credit is due for folds.
    round_state["settlement_status"] = "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
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
        # Match the deal action before the optional decision action.
        if item.get("start_action_id") == action_id:
            # Report the deal stage and owning round.
            return item, "deal"
        # Match a committed or prepared call/fold decision action.
        if item.get("decision_action_id") == action_id:
            # Report the decision stage and owning round.
            return item, "decision"
    # Return no owner when the action id remains unused in retained state.
    return None


# Move a terminal round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Normalize the optional active slot before reading its identifier.
    active_round = state.get("active_round") or {}
    # Clear the actionable slot only when it contains this exact round.
    if active_round.get("round_id") == round_state.get("round_id"):
        # Prevent further decisions against the terminal round.
        state["active_round"] = None
    # Remove any older copy before appending an idempotent settlement.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the newest terminal result in stable chronological order.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private recovery fields from one public round payload.
def public_round(round_state):
    # Preserve a null active-round slot without creating a placeholder.
    if round_state is None:
        # Return JSON null through the router.
        return None
    # Exclude hidden cards and internal fingerprints from public responses.
    private_fields = {"_dealer_cards", "_turn_card", "_river_card", "request_fingerprint", "decision_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide unrevealed dealer, turn, and river cards.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
