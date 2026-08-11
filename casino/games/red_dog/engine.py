# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic Red Dog rules without transport or wallet side effects.

Requirements: CARD-001, LEDGER-005, LEDGER-006, LEDGER-007, and LEDGER-023.
"""

# Import finite-number validation for ledger-compatible wager normalization.
import math

# Import shared immutable cards and six-deck deterministic shuffle support from issue #96.
from casino.core.cards import Card, coerce_card, shuffled_deck
# Import the shared clock for persisted audit timestamps.
from casino.core.clock import utc_now
# Import the shared identifier factory for production round and shoe identities.
from casino.core.ids import new_id
# Import public conflict, lookup, and validation errors for pure state transitions.
from casino.errors import ConflictError, NotFoundError, ValidationError

# Identify every state document and ledger event produced by this game.
GAME_ID = "red_dog"
# Rank cards from deuce through ace while ignoring suits under Red Dog rules.
RANK_VALUES = {rank: value for value, rank in enumerate(("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"), start=2)}
# Define the standard spread profit odds required by issue #84.
SPREAD_ODDS = {1: 5, 2: 4, 3: 2, **{spread: 1 for spread in range(4, 12)}}
# Retain a bounded newest-first public history without discarding retry identities.
ROUND_HISTORY_LIMIT = 20
# Bound one ante so a matching raise remains comfortably inside shared ledger limits.
MAX_WAGER = 100_000.0


# Build one fresh player-scoped document for reload-safe state persistence.
def default_state() -> dict:
    # Return JSON-compatible rules, shoe, round, retry, and ledger-recovery state.
    return {
        # Publish fixed table rules for localized frontend explanation.
        "rules": {
            "decks": 6,  # Use six standard decks from the shared card primitive.
            "raise_equals_ante": True,  # Restrict the raise action to one matching ante.
            "pair_profit_odds": 11,  # Pay eleven-to-one profit for three of a kind.
            "spread_odds": {str(spread): odds for spread, odds in SPREAD_ODDS.items()},  # Publish every spread payout.
        },
        "shoe": [],  # Persist compact card codes so reload never changes a prepared result.
        "shoe_id": None,  # Identify the current six-deck shoe without exposing entropy.
        "shoes_dealt": 0,  # Report deterministic shoe replacement telemetry.
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


# Validate and normalize one positive play-token ante.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Surface one stable public validation message.
        raise ValidationError("Red Dog wager must be between 0.01 and 100000 play tokens")
    # Convert numeric JSON values and numeric strings to ledger precision.
    try:
        # Round to the shared ledger's two-decimal precision.
        amount = round(float(value), 2)
    # Translate malformed values into the standard game validation error.
    except (TypeError, ValueError):
        # Avoid echoing caller-controlled input in the error message.
        raise ValidationError("Red Dog wager must be between 0.01 and 100000 play tokens") from None
    # Reject non-finite, sub-cent, and oversized wagers before state changes.
    if not math.isfinite(amount) or amount < 0.01 or amount > MAX_WAGER:
        # Keep invalid values away from persisted state and the ledger.
        raise ValidationError("Red Dog wager must be between 0.01 and 100000 play tokens")
    # Return the canonical two-decimal amount.
    return amount


# Replace an exhausted shoe before a round while preserving deterministic test seams.
def ensure_shoe(state: dict, *, seed=None, required_cards: int = 3, shoe_id: str | None = None) -> None:
    # Reuse the persisted shoe when it can finish the next complete round.
    if len(state.get("shoe", [])) >= required_cards:
        # Leave both card order and shoe identity unchanged.
        return
    # Build and shuffle exactly six standard decks through issue #96 primitives.
    cards = shuffled_deck(decks=6, seed=seed)
    # Persist compact ASCII card codes for encoding-safe reload behavior.
    state["shoe"] = [card.code for card in cards]
    # Use an injected deterministic identity only when focused tests supply one.
    state["shoe_id"] = shoe_id or new_id("rdshoe")
    # Increment public shoe telemetry after each replacement.
    state["shoes_dealt"] = int(state.get("shoes_dealt", 0)) + 1


# Remove one normalized card from the persisted shoe.
def draw_card(state: dict) -> Card:
    # Reject corrupt or prematurely exhausted state instead of silently reshuffling mid-round.
    if not state.get("shoe"):
        # Preserve deterministic prepared outcomes by failing closed.
        raise ConflictError("Red Dog shoe cannot complete this round")
    # Pop from the end so focused tests can arrange short deterministic shoes cheaply.
    return coerce_card(state["shoe"].pop())


# Calculate the number of ranks strictly between two initial cards.
def spread_between(first_card, second_card) -> int:
    # Resolve the first rank through the shared card boundary.
    first_value = RANK_VALUES[coerce_card(first_card).rank]
    # Resolve the second rank independently because suits never break ties.
    second_value = RANK_VALUES[coerce_card(second_card).rank]
    # Return zero for a pair or consecutive cards and one through eleven otherwise.
    return max(abs(first_value - second_value) - 1, 0)


# Determine whether the third rank falls strictly between the opening ranks.
def is_between(first_card, second_card, third_card) -> bool:
    # Read all three normalized rank values without considering suits.
    values = [RANK_VALUES[coerce_card(card).rank] for card in (first_card, second_card, third_card)]
    # Require strict inequality so matching either boundary loses a spread hand.
    return min(values[0], values[1]) < values[2] < max(values[0], values[1])


# Build one stable side-effect instruction for the shared ledger adapter.
def ledger_intent(client_action_id: str, suffix: str, direction: str, amount: float, transaction_type: str, round_item: dict, stage: str) -> dict:
    # Derive a unique game-owned ledger action from one client command.
    ledger_action_id = f"rd:{client_action_id}:{suffix}"
    # Return every audit dimension required by repository ledger policy.
    return {
        "action_id": ledger_action_id,  # Provide the crash-recovery and replay key.
        "client_action_id": client_action_id,  # Preserve the public command identity.
        "direction": direction,  # Restrict the adapter to debit or credit.
        "amount": round(float(amount), 2),  # Match shared ledger precision.
        "transaction_type": transaction_type,  # Identify the movement in Admin telemetry.
        "player_id": round_item["player_id"],  # Bind movement to the resolved session player.
        "game": GAME_ID,  # Identify Red Dog without relying on route text.
        "round_id": round_item["round_id"],  # Correlate all movements to one round.
        # Store structured recovery and audit details in the append-only ledger row.
        "details": {
            "red_dog_action_id": ledger_action_id,  # Recover this exact movement after interruption.
            "client_action_id": client_action_id,  # Diagnose the originating public command.
            "stage": stage,  # Distinguish ante, raise, refund, and payout movements.
            "wager": round_item["wager"],  # Preserve the original committed ante.
            "raise_wager": round_item.get("raise_wager", 0.0),  # Preserve an optional matching raise.
            "outcome": round_item.get("outcome"),  # Record the prepared result known to the engine.
        },
    }


# Reject overlapping rounds while one spread still awaits a call-or-raise decision.
def require_no_active_round(state: dict) -> None:
    # Inspect retained rounds because reload may restore an older actionable decision.
    for round_item in state.get("rounds", {}).values():
        # Treat only the documented decision phase as player-actionable.
        if round_item.get("phase") == "raise_decision":
            # Require completion before another wager can start.
            raise ConflictError("Finish the active Red Dog round before dealing again")


# Add one round to retained retry state while public history remains bounded separately.
def store_round(state: dict, round_item: dict) -> None:
    # Store the complete prepared round under its server identity.
    state.setdefault("rounds", {})[round_item["round_id"]] = round_item
    # Append the identity to deterministic display order.
    state.setdefault("round_order", []).append(round_item["round_id"])
    # Retain old bodies so exact action-id retries can always return their original round.


# Create one opening deal and prepare all automatic ledger movements before side effects.
def start_round(state: dict, player_id: str, wager, action_id: str, *, seed=None, round_id: str | None = None, shoe_id: str | None = None, created_at: str | None = None) -> dict:
    # Prevent another wager while an earlier spread decision remains open.
    require_no_active_round(state)
    # Normalize the ante before cards or persisted state change.
    amount = normalize_wager(wager)
    # Ensure three cards are available so pair and spread paths never reshuffle mid-round.
    ensure_shoe(state, seed=seed, required_cards=3, shoe_id=shoe_id)
    # Deal the first opening card from the persisted shoe.
    first = draw_card(state)
    # Deal the second opening card from the same shoe.
    second = draw_card(state)
    # Calculate the rank gap without suit significance.
    spread = spread_between(first, second)
    # Build the complete prepared public shape before any ledger adapter call.
    round_item = {
        "round_id": round_id or new_id("rd"),  # Use a collision-resistant production id or injected test id.
        "player_id": player_id,  # Bind state to the authenticated player.
        "created_at": created_at or utc_now(),  # Preserve stable audit timing.
        "first_card": card_payload(first),  # Expose the first opening card.
        "second_card": card_payload(second),  # Expose the second opening card.
        "third_card": None,  # Reserve the eventual result-card slot.
        "phase": "raise_decision",  # Replace this below for automatic outcomes.
        "outcome": "spread_pending",  # Await call or matching raise for a normal spread.
        "wager": amount,  # Record the original ante.
        "raise_wager": 0.0,  # Add a matching amount only through the raise action.
        "total_wager": amount,  # Track all committed stakes for payout calculation.
        "spread": spread if spread else None,  # Expose one through eleven only for spread hands.
        "odds": SPREAD_ODDS.get(spread),  # Publish the applicable spread profit odds.
        "payout": 0.0,  # Store returned credit including stakes after settlement.
        "net": 0.0,  # Reserve a stable player-facing result before settlement.
        "ledger_intents": [],  # Persist ordered wallet instructions privately.
    }
    # Always prepare the ante debit as the first movement.
    round_item["ledger_intents"].append(ledger_intent(action_id, "wager", "debit", amount, "RED_DOG_WAGER_DEBIT", round_item, "wager"))
    # Resolve equal opening ranks through the automatic pair path.
    if coerce_card(first).rank == coerce_card(second).rank:
        # Deal the mandatory third card immediately for a pair.
        third = draw_card(state)
        # Store the normalized third-card result for reload and UI evidence.
        round_item["third_card"] = card_payload(third)
        # Publish the fixed pair paytable odds for both pair outcomes.
        round_item["odds"] = 11
        # Settle three matching ranks at eleven-to-one profit plus returned stake.
        if coerce_card(third).rank == coerce_card(first).rank:
            # Record the winning automatic outcome.
            round_item["outcome"] = "three_of_a_kind"
            # Return twelve times the ante: stake plus eleven-to-one profit.
            round_item["payout"] = round(amount * 12, 2)
            # Prepare the complete returned credit after the ante debit.
            round_item["ledger_intents"].append(ledger_intent(action_id, "payout", "credit", round_item["payout"], "RED_DOG_PAYOUT_CREDIT", round_item, "three_of_a_kind"))
        # Treat a non-matching third rank as a push.
        else:
            # Record the pair-push result required by issue #84.
            round_item["outcome"] = "pair_push"
            # Return only the original ante.
            round_item["payout"] = amount
            # Prepare one refund credit after the committed wager.
            round_item["ledger_intents"].append(ledger_intent(action_id, "refund", "credit", amount, "RED_DOG_REFUND_CREDIT", round_item, "pair_push"))
        # Mark every automatic pair outcome terminal before persistence.
        round_item["phase"] = "settled"
        # Record zero for a push or returned credit minus ante for a win.
        round_item["net"] = round(round_item["payout"] - round_item["total_wager"], 2)
        # Use the opening timestamp as the deterministic automatic completion time.
        round_item["completed_at"] = round_item["created_at"]
    # Resolve consecutive opening ranks without drawing a third card.
    elif spread == 0:
        # Record the automatic consecutive push.
        round_item["outcome"] = "consecutive_push"
        # Return only the original ante.
        round_item["payout"] = amount
        # Prepare the push refund after the wager debit.
        round_item["ledger_intents"].append(ledger_intent(action_id, "refund", "credit", amount, "RED_DOG_REFUND_CREDIT", round_item, "consecutive_push"))
        # Mark the no-third-card result terminal.
        round_item["phase"] = "settled"
        # Record the push as no net token movement.
        round_item["net"] = 0.0
        # Use the opening timestamp as the deterministic automatic completion time.
        round_item["completed_at"] = round_item["created_at"]
    # Store automatic or decision-ready state before the API performs movements.
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
        raise NotFoundError("Red Dog round was not found")
    # Return the validated player-owned round.
    return round_item


# Complete one normal spread without adding a raise wager.
def call_round(state: dict, round_id: str, action_id: str, *, completed_at: str | None = None) -> dict:
    # Resolve the actionable round inside the current player document.
    round_item = get_round(state, round_id)
    # Allow a call only while a normal spread awaits its decision.
    if round_item.get("phase") != "raise_decision":
        # Reject duplicate transitions under a different action id.
        raise ConflictError("Red Dog call is only available during the raise decision")
    # Complete the prepared shoe without replacing it mid-round.
    third = draw_card(state)
    # Persist the result card before any possible payout movement.
    round_item["third_card"] = card_payload(third)
    # Preserve the ante-only total wager.
    round_item["total_wager"] = round_item["wager"]
    # Resolve strict-between win or outside/boundary loss.
    _settle_spread(round_item, third, action_id, completed_at=completed_at)
    # Return the prepared terminal round.
    return round_item


# Complete one normal spread after adding a matching raise wager.
def raise_round(state: dict, round_id: str, action_id: str, *, completed_at: str | None = None) -> dict:
    # Resolve the actionable round inside the current player document.
    round_item = get_round(state, round_id)
    # Allow a raise only while a normal spread awaits its decision.
    if round_item.get("phase") != "raise_decision":
        # Reject stale or duplicate transitions under a new action id.
        raise ConflictError("Red Dog raise is only available during the raise decision")
    # Match the ante exactly as required by the issue #84 table variant.
    round_item["raise_wager"] = round_item["wager"]
    # Record both committed stakes before calculating any payout.
    round_item["total_wager"] = round(round_item["wager"] + round_item["raise_wager"], 2)
    # Prepare the matching debit before revealing or paying the result.
    round_item["ledger_intents"].append(ledger_intent(action_id, "raise", "debit", round_item["raise_wager"], "RED_DOG_RAISE_DEBIT", round_item, "raise"))
    # Draw the third card from the already persisted shoe.
    third = draw_card(state)
    # Persist the deterministic result before ledger reconciliation.
    round_item["third_card"] = card_payload(third)
    # Resolve strict-between win or outside/boundary loss for both stakes.
    _settle_spread(round_item, third, action_id, completed_at=completed_at)
    # Return the prepared terminal round.
    return round_item


# Apply the spread paytable to all committed stakes and prepare an optional credit.
def _settle_spread(round_item: dict, third_card, action_id: str, *, completed_at: str | None = None) -> None:
    # Determine the third rank against the two strict opening boundaries.
    won = is_between(round_item["first_card"], round_item["second_card"], third_card)
    # Record the stable result key used by contract and localized UI.
    round_item["outcome"] = "spread_win" if won else "spread_loss"
    # Mark the prepared game result terminal before any credit is attempted.
    round_item["phase"] = "settled"
    # Store a deterministic completion timestamp for reload-safe history.
    round_item["completed_at"] = completed_at or utc_now()
    # Calculate returned stakes plus profit only for a strict-between win.
    if won:
        # Read the fixed integer profit multiplier for this spread.
        odds = int(round_item["odds"])
        # Apply the same odds to ante and optional raise, then include returned stakes.
        round_item["payout"] = round(round_item["total_wager"] * (odds + 1), 2)
        # Prepare one aggregate returned-credit movement after every debit.
        round_item["ledger_intents"].append(ledger_intent(action_id, "payout", "credit", round_item["payout"], "RED_DOG_PAYOUT_CREDIT", round_item, "spread_win"))
    # Keep losing hands at zero without creating invalid zero-value ledger rows.
    else:
        # Record the explicit zero returned credit for public state.
        round_item["payout"] = 0.0
    # Store returned credit minus every committed stake for localized summary copy.
    round_item["net"] = round(round_item["payout"] - round_item["total_wager"], 2)


# Build one client-safe round without private ordered ledger instructions.
def public_round(round_item: dict, committed_actions: dict | None = None) -> dict:
    # Normalize missing committed state for pure engine tests.
    committed = committed_actions or {}
    # Copy every documented field while hiding prepared ledger internals.
    exposed = {key: value for key, value in round_item.items() if key != "ledger_intents"}
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
    # Read only the bounded newest display identities while retaining older retry state privately.
    order = list(state.get("round_order", []))[-ROUND_HISTORY_LIMIT:]
    # Resolve sanitized rounds from newest to oldest.
    rounds = [public_round(state["rounds"][round_id], state.get("ledger_actions")) for round_id in reversed(order) if round_id in state.get("rounds", {})]
    # Return fixed rules, non-secret shoe telemetry, and reload-safe history.
    return {
        "rules": dict(state.get("rules", {})),  # Expose the standard table configuration.
        "shoe_id": state.get("shoe_id"),  # Expose shoe identity without its order.
        "shoe_count": len(state.get("shoe", [])),  # Expose remaining-card telemetry only.
        "shoes_dealt": int(state.get("shoes_dealt", 0)),  # Expose replacement count.
        "rounds": rounds,  # Provide bounded newest-first round history.
        "active_round": next((item for item in rounds if item.get("phase") == "raise_decision"), None),  # Identify the only actionable round.
    }
