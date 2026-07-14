"""Deterministic Let It Ride rules without transport or wallet side effects.

Requirements: CARD-001, POKER-001, LEDGER-005, LEDGER-006, LEDGER-007,
LEDGER-023, SESSION-005, and LIR-PROPOSED-001 through LIR-PROPOSED-004.
"""

# Import finite-number checks for ledger-compatible wager validation.
import math

# Import shared cards and deterministic deck support from the #96 primitive lane.
from casino.core.cards import coerce_card, shuffled_deck
# Import the shared standard poker evaluator instead of duplicating hand ranking.
from casino.core.poker import RANK_VALUES, evaluate_five
# Import the shared clock for pure-engine defaults used outside injected tests.
from casino.core.clock import utc_now
# Import the shared identifier factory for production round and shoe identities.
from casino.core.ids import new_id
# Import public conflict, lookup, and validation errors for stable API boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError

# Identify every state document, route payload, and ledger row owned by this module.
GAME_ID = "let_it_ride"
# Retain only the newest public history rows while keeping retry data in state.
ROUND_HISTORY_LIMIT = 20
# Bound one base wager so the three-unit opening debit remains inside ledger limits.
MAX_WAGER = 100_000.0
# Define the staged decisions supported by the table.
DECISIONS = ("ride", "pull")
# Define the Let It Ride profit paytable for qualifying five-card poker hands.
PAYTABLE = {
    "royal_flush": 1000,  # Pay one thousand to one profit for a royal flush.
    "straight_flush": 200,  # Pay two hundred to one profit for a straight flush.
    "four_of_a_kind": 50,  # Pay fifty to one profit for four of a kind.
    "full_house": 11,  # Pay eleven to one profit for a full house.
    "flush": 8,  # Pay eight to one profit for a flush.
    "straight": 5,  # Pay five to one profit for a straight.
    "three_of_a_kind": 3,  # Pay three to one profit for three of a kind.
    "two_pair": 2,  # Pay two to one profit for two pair.
    "pair_of_tens_or_better": 1,  # Pay even profit for a pair of tens or better.
    "no_win": 0,  # Pay no returned credit for a losing hand.
}


# Build one fresh player-scoped document for reload-safe state persistence.
def default_state() -> dict:
    # Return JSON-compatible rules, shoe, round, retry, and ledger-recovery state.
    return {
        "rules": {  # Publish fixed table rules for localized frontend explanation.
            "base_wagers": 3,  # Require three equal opening play-token wagers.
            "decision_beats": 2,  # Allow two withdraw-or-ride decisions.
            "final_wager_always_rides": True,  # Preserve the third mandatory wager.
            "paytable": dict(PAYTABLE),  # Publish the game-owned returned-credit table.
        },
        "shoe": [],  # Persist compact card codes so reload never changes prepared cards.
        "shoe_id": None,  # Identify the current deck without exposing entropy.
        "shoes_dealt": 0,  # Report deterministic deck replacement telemetry.
        "rounds": {},  # Store retained round objects by stable server id.
        "round_order": [],  # Preserve creation order for bounded public history.
        "requests": {},  # Map client action ids to immutable command fingerprints.
        "ledger_actions": {},  # Record committed or recovered ledger movements.
    }


# Convert one shared card value into the stable public API object.
def card_payload(card) -> dict:
    # Normalize strings, mappings, and Card instances through the shared primitive.
    normalized = coerce_card(card)
    # Return encoding-safe rank, suit, and compact code fields.
    return {"rank": normalized.rank, "suit": normalized.suit, "code": normalized.code}


# Validate and normalize one positive base wager.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Surface one stable public validation message.
        raise ValidationError("Let It Ride wager must be between 0.01 and 100000 play tokens")
    # Convert numeric JSON values and numeric strings to ledger precision.
    try:
        # Round to the shared ledger's two-decimal precision.
        amount = round(float(value), 2)
    # Translate malformed values into the standard game validation error.
    except (TypeError, ValueError):
        # Avoid echoing caller-controlled input in the error message.
        raise ValidationError("Let It Ride wager must be between 0.01 and 100000 play tokens") from None
    # Reject non-finite, sub-cent, and oversized wagers before state changes.
    if not math.isfinite(amount) or amount < 0.01 or amount > MAX_WAGER:
        # Keep invalid values away from persisted state and the ledger.
        raise ValidationError("Let It Ride wager must be between 0.01 and 100000 play tokens")
    # Return the canonical two-decimal base amount.
    return amount


# Validate one public ride-or-pull decision.
def normalize_decision(value) -> str:
    # Require an exact string decision instead of coercing arbitrary JSON values.
    if not isinstance(value, str):
        # Raise the stable decision diagnostic.
        raise ValidationError("Let It Ride decision must be ride or pull")
    # Normalize caller casing while preserving the limited decision vocabulary.
    decision = value.strip().lower()
    # Reject every value outside the two documented table actions.
    if decision not in DECISIONS:
        # Raise the stable decision diagnostic.
        raise ValidationError("Let It Ride decision must be ride or pull")
    # Return the canonical action keyword.
    return decision


# Replace an exhausted deck before a round while preserving deterministic test seams.
def ensure_shoe(state: dict, *, seed=None, required_cards: int = 5, shoe_id: str | None = None) -> None:
    # Reuse the persisted deck when it can finish the next complete round.
    if len(state.get("shoe", [])) >= required_cards:
        # Leave both card order and shoe identity unchanged.
        return
    # Build and shuffle one standard deck through the shared #96 primitive.
    cards = shuffled_deck(decks=1, seed=seed)
    # Persist compact ASCII card codes for encoding-safe reload behavior.
    state["shoe"] = [card.code for card in cards]
    # Use an injected deterministic identity only when focused tests supply one.
    state["shoe_id"] = shoe_id or new_id("lirshoe")
    # Increment public deck telemetry after each replacement.
    state["shoes_dealt"] = int(state.get("shoes_dealt", 0)) + 1


# Remove one normalized card from the persisted shoe.
def draw_card(state: dict):
    # Reject corrupt or prematurely exhausted state instead of reshuffling mid-round.
    if not state.get("shoe"):
        # Preserve deterministic prepared outcomes by failing closed.
        raise ConflictError("Let It Ride deck cannot complete this round")
    # Pop from the end so focused tests can arrange short deterministic shoes cheaply.
    return coerce_card(state["shoe"].pop())


# Translate a standard five-card poker result into Let It Ride's paytable row.
def classify_hand(cards) -> tuple[str, int]:
    # Evaluate exactly five cards through the shared #96 poker primitive.
    rank = evaluate_five(cards)
    # Recognize a royal flush as the ace-high form of a straight flush.
    if rank.name == "straight_flush" and {card.rank for card in rank.cards} == {"10", "J", "Q", "K", "A"}:
        # Return the game-owned royal-flush row and profit multiplier.
        return "royal_flush", PAYTABLE["royal_flush"]
    # Recognize a one-pair win only when the pair is tens or better.
    if rank.name == "one_pair":
        # Read the pair value from the standard evaluator's first tie breaker.
        pair_value = rank.tiebreak[0]
        # Return the qualifying pair row at the Let It Ride threshold.
        if pair_value >= RANK_VALUES["10"]:
            # Return the even-profit qualifying pair row.
            return "pair_of_tens_or_better", PAYTABLE["pair_of_tens_or_better"]
        # Return a loss for nines or lower without changing the shared evaluator.
        return "no_win", PAYTABLE["no_win"]
    # Preserve every other standard category only when it has a game paytable row.
    outcome = rank.name if rank.name in PAYTABLE else "no_win"
    # Return the stable result key and profit multiplier.
    return outcome, PAYTABLE[outcome]


# Build one stable side-effect instruction for the shared ledger adapter.
def ledger_intent(client_action_id: str, suffix: str, direction: str, amount: float, transaction_type: str, round_item: dict, stage: str) -> dict:
    # Derive a unique game-owned ledger action from one client command.
    ledger_action_id = f"lir:{client_action_id}:{suffix}"
    # Return every audit dimension required by repository ledger policy.
    return {
        "action_id": ledger_action_id,  # Provide the crash-recovery and replay key.
        "client_action_id": client_action_id,  # Preserve the originating public command id.
        "direction": direction,  # Restrict the adapter to debit or credit.
        "amount": round(float(amount), 2),  # Match shared ledger precision.
        "transaction_type": transaction_type,  # Identify the movement in Admin telemetry.
        "player_id": round_item["player_id"],  # Bind movement to the resolved session player.
        "game": GAME_ID,  # Identify Let It Ride without relying on route text.
        "round_id": round_item["round_id"],  # Correlate all movements to one round.
        "details": {  # Store structured recovery and audit details in the append-only ledger row.
            "let_it_ride_action_id": ledger_action_id,  # Recover this exact movement.
            "client_action_id": client_action_id,  # Diagnose the originating public command.
            "stage": stage,  # Distinguish wager, withdrawal, and final payout.
            "wager": round_item["wager"],  # Preserve the base committed wager.
            "active_units": round_item.get("active_units", 3),  # Preserve riding unit count.
            "outcome": round_item.get("outcome"),  # Record the prepared result when known.
        },
    }


# Reject overlapping rounds while one staged decision remains active.
def require_no_active_round(state: dict) -> None:
    # Inspect retained rounds because reload may restore an actionable decision.
    for round_item in state.get("rounds", {}).values():
        # Treat only the documented decision phases as player-actionable.
        if round_item.get("phase") in {"first_decision", "second_decision"}:
            # Require completion before another three-unit wager can start.
            raise ConflictError("Finish the active Let It Ride round before dealing again")


# Add one round to retained retry state while public history remains bounded separately.
def store_round(state: dict, round_item: dict) -> None:
    # Store the complete prepared round under its server identity.
    state.setdefault("rounds", {})[round_item["round_id"]] = round_item
    # Append the identity to deterministic display order.
    state.setdefault("round_order", []).append(round_item["round_id"])
    # Retain old bodies so exact action-id retries can always return their original round.


# Create one opening deal and prepare the three-unit wager before side effects.
def start_round(state: dict, player_id: str, wager, action_id: str, *, seed=None, round_id: str | None = None, shoe_id: str | None = None, created_at: str | None = None) -> dict:
    # Prevent another wager while an earlier round awaits a decision.
    require_no_active_round(state)
    # Normalize the base unit before cards or persisted state change.
    amount = normalize_wager(wager)
    # Ensure five cards are available so the round never reshuffles mid-hand.
    ensure_shoe(state, seed=seed, required_cards=5, shoe_id=shoe_id)
    # Deal the player hand from the persisted deck.
    player_cards = [draw_card(state) for _ in range(3)]
    # Deal both community cards immediately but reveal them in later phases.
    community_cards = [draw_card(state) for _ in range(2)]
    # Build the complete prepared public shape before any ledger adapter call.
    round_item = {
        "round_id": round_id or new_id("lir"),  # Use production or injected route-safe id.
        "player_id": player_id,  # Bind state to the authenticated player.
        "created_at": created_at or utc_now(),  # Preserve stable audit timing.
        "phase": "first_decision",  # Start after the three player cards are visible.
        "wager": amount,  # Store one base wager unit.
        "total_initial_wager": round(amount * 3, 2),  # Debit all three equal units at once.
        "active_units": 3,  # Begin with all three wagers riding.
        "withdrawn_units": 0,  # Track returned units after pull decisions.
        "decisions": [],  # Preserve the two staged ride-or-pull choices.
        "player_cards": [card_payload(card) for card in player_cards],  # Expose all player cards.
        "community_cards": [card_payload(card) for card in community_cards],  # Persist hidden and visible community cards.
        "revealed_community": 0,  # Reveal the first community only after the first decision.
        "outcome": "decision_pending",  # Await the first withdrawal decision.
        "multiplier": 0,  # Reserve paytable multiplier for terminal state.
        "payout": 0.0,  # Reserve returned active-wager credit for terminal state.
        "refund": 0.0,  # Reserve cumulative withdrawn wager refunds.
        "net": round(-amount * 3, 2),  # Show committed exposure before any returns.
        "ledger_intents": [],  # Persist ordered wallet instructions privately.
    }
    # Always prepare the opening debit as the first movement.
    round_item["ledger_intents"].append(ledger_intent(action_id, "wager", "debit", round_item["total_initial_wager"], "LET_IT_RIDE_WAGER_DEBIT", round_item, "wager"))
    # Store decision-ready state before the API performs movements.
    store_round(state, round_item)
    # Return the mutable round owned by the caller's player document.
    return round_item


# Return one round from this player's isolated state without leaking other sessions.
def get_round(state: dict, round_id: str) -> dict:
    # Resolve the server id only inside the current player document.
    round_item = state.get("rounds", {}).get(round_id)
    # Keep unknown and cross-player identifiers indistinguishable.
    if round_item is None:
        # Return the repository-standard lookup error.
        raise NotFoundError("Let It Ride round was not found")
    # Return the validated player-owned round.
    return round_item


# Apply one ride-or-pull decision and reveal or settle the next stage.
def advance_decision(state: dict, round_id: str, stage: str, decision, action_id: str, *, completed_at: str | None = None) -> dict:
    # Resolve the actionable round inside the current player document.
    round_item = get_round(state, round_id)
    # Normalize the public action before mutating the round.
    normalized_decision = normalize_decision(decision)
    # Map the public route stage to the required current phase.
    expected_phase = "first_decision" if stage == "first" else "second_decision"
    # Reject stale or out-of-order decision requests.
    if round_item.get("phase") != expected_phase:
        # Keep duplicate and cross-stage transitions fail-closed.
        raise ConflictError("Let It Ride decision is not available in this phase")
    # Append the public decision to the persisted decision trail.
    round_item["decisions"].append({"stage": stage, "decision": normalized_decision, "action_id": action_id})
    # Prepare a refund when the player withdraws one eligible wager unit.
    if normalized_decision == "pull":
        # Decrease the riding wager count before any potential settlement.
        round_item["active_units"] -= 1
        # Increase the returned wager count for public summary copy.
        round_item["withdrawn_units"] += 1
        # Add the current pull refund to cumulative returned stakes.
        round_item["refund"] = round(round_item["refund"] + round_item["wager"], 2)
        # Prepare the exactly-once returned-wager credit.
        round_item["ledger_intents"].append(ledger_intent(action_id, f"{stage}-refund", "credit", round_item["wager"], "LET_IT_RIDE_REFUND_CREDIT", round_item, f"{stage}_pull"))
    # Advance from the first decision to the first community-card reveal.
    if stage == "first":
        # Reveal one community card without evaluating the final hand yet.
        round_item["revealed_community"] = 1
        # Move the round to its second and final withdraw-or-ride decision.
        round_item["phase"] = "second_decision"
        # Publish a player-facing pending outcome for the next decision beat.
        round_item["outcome"] = "second_decision_pending"
        # Update public net exposure after an optional refund.
        round_item["net"] = round(round_item["refund"] - round_item["total_initial_wager"], 2)
        # Return the still-actionable round.
        return round_item
    # Reveal the final community card before evaluating the five-card poker hand.
    round_item["revealed_community"] = 2
    # Evaluate all three player cards plus both community cards.
    outcome, multiplier = classify_hand([card["code"] for card in round_item["player_cards"] + round_item["community_cards"]])
    # Store the stable paytable result key.
    round_item["outcome"] = outcome
    # Store the profit multiplier for UI and contract consumers.
    round_item["multiplier"] = multiplier
    # Calculate the active wager units that remained after both decisions.
    active_wager = round(round_item["wager"] * round_item["active_units"], 2)
    # Credit returned stake plus profit only for qualifying hands.
    round_item["payout"] = round(active_wager * (multiplier + 1), 2) if multiplier else 0.0
    # Prepare one aggregate returned-credit movement after any pull refunds.
    if round_item["payout"]:
        # Add the final payout intent under the second-decision action id.
        round_item["ledger_intents"].append(ledger_intent(action_id, "payout", "credit", round_item["payout"], "LET_IT_RIDE_PAYOUT_CREDIT", round_item, "final_payout"))
    # Store returned credits minus the original three-unit wager.
    round_item["net"] = round(round_item["refund"] + round_item["payout"] - round_item["total_initial_wager"], 2)
    # Mark the prepared result terminal before the API reconciles movements.
    round_item["phase"] = "settled"
    # Store a deterministic completion timestamp for reload-safe history.
    round_item["completed_at"] = completed_at or utc_now()
    # Return the prepared terminal round.
    return round_item


# Build one client-safe round without private ordered ledger instructions.
def public_round(round_item: dict, committed_actions: dict | None = None) -> dict:
    # Normalize missing committed state for pure engine tests.
    committed = committed_actions or {}
    # Copy every documented field while hiding prepared ledger internals.
    exposed = {key: value for key, value in round_item.items() if key != "ledger_intents"}
    # Hide unrevealed community cards while preserving stable slot count.
    exposed["community_cards"] = [
        card if index < int(round_item.get("revealed_community", 0)) else None  # Preserve visible cards and mask hidden slots.
        for index, card in enumerate(round_item.get("community_cards", []))  # Inspect every persisted community-card slot.
    ]
    # Count all movements required by the prepared deterministic result.
    required_count = len(round_item.get("ledger_intents", []))
    # Count committed or recovered movements by stable ledger action id.
    committed_count = sum(1 for intent in round_item.get("ledger_intents", []) if intent["action_id"] in committed)
    # Publish settlement progress without exposing internal action ids.
    exposed["settlement"] = {
        "required_actions": required_count,  # Report total prepared movements.
        "committed_actions": committed_count,  # Report durable ledger movements.
        "complete": round_item.get("phase") == "settled" and required_count == committed_count,  # Require game and wallet completion.
    }
    # Return a detached public object.
    return exposed


# Build newest-first public state for one authenticated player.
def public_state(state: dict) -> dict:
    # Read only the bounded newest display identities while retaining retry state privately.
    order = list(state.get("round_order", []))[-ROUND_HISTORY_LIMIT:]
    # Resolve sanitized rounds from newest to oldest.
    rounds = [public_round(state["rounds"][round_id], state.get("ledger_actions")) for round_id in reversed(order) if round_id in state.get("rounds", {})]
    # Return fixed rules, non-secret deck telemetry, and reload-safe history.
    return {
        "rules": dict(state.get("rules", {})),  # Expose the standard table configuration.
        "shoe_id": state.get("shoe_id"),  # Expose deck identity without its order.
        "shoe_count": len(state.get("shoe", [])),  # Expose remaining-card telemetry only.
        "shoes_dealt": int(state.get("shoes_dealt", 0)),  # Expose replacement count.
        "rounds": rounds,  # Provide bounded newest-first round history.
        "active_round": next((item for item in rounds if item.get("phase") in {"first_decision", "second_decision"}), None),  # Identify the only actionable round.
    }
