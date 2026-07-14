"""Deterministic Casino War rules without wallet or transport side effects.

Requirements: CARD-001, LEDGER-005, LEDGER-006, LEDGER-023.
"""

# Import shared immutable card values and deterministic shoe construction.
from casino.core.cards import Card, coerce_card, shuffled_deck
# Import timestamps so persisted rounds expose stable creation metadata.
from casino.core.clock import utc_now
# Import identifiers so production rounds and shoes remain collision resistant.
from casino.core.ids import new_id
# Import domain errors so API adapters receive consistent validation failures.
from casino.errors import ConflictError, ValidationError

# Identify every persisted and ledger event produced by this game.
GAME_ID = "casino_war"
# Rank cards from deuce through ace according to Casino War rules.
RANK_VALUES = {rank: value for value, rank in enumerate(("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"), start=2)}
# Retain enough settled rounds for reload-safe game-local history.
ROUND_HISTORY_LIMIT = 20


# Build a new player-scoped state document with fixed standard table rules.
def default_state() -> dict:
    # Return JSON-shaped state that the shared state store can persist unchanged.
    return {
        # Store fixed rules together so API clients can explain table behavior.
        "rules": {
            "decks": 6,  # Use the common six-deck Casino War shoe.
            "burn_cards": 3,  # Burn three cards before the war comparison.
            "initial_win_return": 2.0,  # Return stake plus an even-money win.
            "surrender_return": 0.5,  # Return half the original wager on surrender.
            "war_win_return": 3.0,  # Pay the original wager and push the war wager.
            "war_ties_favor_player": True,  # Treat a second tie as a player win.
        },
        "shoe": [],  # Persist compact ASCII card codes for reload safety.
        "shoe_id": None,  # Identify the current shoe without exposing entropy.
        "shoes_dealt": 0,  # Report shoe replacement as player-facing table data.
        "rounds": {},  # Store round objects by stable round id.
        "round_order": [],  # Preserve deterministic newest-round ordering.
        "requests": {},  # Map client action ids to replay-safe round commands.
        "ledger_actions": {},  # Record committed ledger action ids and event ids.
    }


# Convert one shared Card into the public API card object.
def card_payload(card) -> dict:
    # Normalize strings and mappings through the merged CARD-001 primitive.
    normalized = coerce_card(card)
    # Return encoding-safe identity fields for backend and frontend consumers.
    return {"rank": normalized.rank, "suit": normalized.suit, "code": normalized.code}


# Validate and normalize one play-token wager.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Raise the shared validation error used by all public API handlers.
        raise ValidationError("Casino War wager must be a positive play-token amount")
    # Convert supported numeric input while reporting malformed values consistently.
    try:
        # Round to the ledger's two-decimal precision.
        amount = round(float(value), 2)
    # Convert type and value failures into the public validation error shape.
    except (TypeError, ValueError):
        # Raise a value-free message suitable for API clients.
        raise ValidationError("Casino War wager must be a positive play-token amount") from None
    # Reject zero, negative, and non-finite values before any round is created.
    if amount <= 0 or amount != amount or amount in (float("inf"), float("-inf")):
        # Keep invalid wagers away from engine and ledger state.
        raise ValidationError("Casino War wager must be a positive play-token amount")
    # Return the ledger-compatible amount.
    return amount


# Replace an exhausted shoe while supporting deterministic test seeds.
def ensure_shoe(state: dict, *, seed=None, required_cards: int = 7) -> None:
    # Reuse the existing shoe when it can finish the next atomic action.
    if len(state.get("shoe", [])) >= required_cards:
        # Leave the persisted shoe and its identifier unchanged.
        return
    # Read the configured deck count from the fixed table rules.
    decks = int(state.get("rules", {}).get("decks", 6))
    # Build through CARD-001 so seeded tests and production entropy use one primitive.
    cards = shuffled_deck(decks=decks, seed=seed)
    # Persist compact ASCII codes rather than encoding-sensitive suit glyphs.
    state["shoe"] = [card.code for card in cards]
    # Assign a fresh identifier without exposing the shuffle seed.
    state["shoe_id"] = new_id("cwshoe")
    # Increment the public shoe counter for table history.
    state["shoes_dealt"] = int(state.get("shoes_dealt", 0)) + 1


# Draw one normalized card from the persisted shoe.
def draw_card(state: dict) -> Card:
    # Fail explicitly if a caller bypassed ensure_shoe.
    if not state.get("shoe"):
        # Report an engine-state conflict instead of silently changing the shoe.
        raise ConflictError("Casino War shoe is empty")
    # Pop from the end so tests can arrange deterministic draw order cheaply.
    return coerce_card(state["shoe"].pop())


# Compare two cards using Casino War rank-only ordering.
def compare_cards(player_card, dealer_card) -> int:
    # Resolve the player's normalized rank value.
    player_value = RANK_VALUES[coerce_card(player_card).rank]
    # Resolve the dealer's normalized rank value.
    dealer_value = RANK_VALUES[coerce_card(dealer_card).rank]
    # Return -1, 0, or 1 without considering suits.
    return (player_value > dealer_value) - (player_value < dealer_value)


# Build one stable ledger instruction for the side-effect adapter.
def ledger_intent(action_id: str, direction: str, amount: float, transaction_type: str, round_item: dict, stage: str) -> dict:
    # Return all fields required for an auditable ledger event.
    return {
        "action_id": action_id,  # Provide the game-owned idempotency key.
        "direction": direction,  # Restrict the adapter to debit or credit.
        "amount": round(float(amount), 2),  # Match ledger precision.
        "transaction_type": transaction_type,  # Identify the movement in Admin.
        "player_id": round_item["player_id"],  # Bind the event to the session player.
        "game": GAME_ID,  # Identify this game in the shared ledger.
        "round_id": round_item["round_id"],  # Tie every movement to one round.
        # Store structured audit details used for reload recovery.
        "details": {
            "casino_war_action_id": action_id,  # Support crash recovery by ledger scan.
            "stage": stage,  # Distinguish ante, war wager, and settlement.
            "outcome": round_item.get("outcome"),  # Record known result context.
            "wager": round_item["wager"],  # Preserve the original wager amount.
        },
    }


# Reject a new round while a prior round still needs a decision or ledger recovery.
def require_no_active_round(state: dict) -> None:
    # Inspect every retained round because reload recovery may leave one pending.
    for round_item in state.get("rounds", {}).values():
        # Treat a tie decision or unapplied ledger intent as active.
        if round_item.get("phase") in {"war_decision", "ledger_pending"}:
            # Require the caller to finish or recover the existing round first.
            raise ConflictError("Finish the active Casino War round before dealing again")


# Add a round to bounded player-scoped history.
def store_round(state: dict, round_item: dict) -> None:
    # Store the round by its stable identifier.
    state.setdefault("rounds", {})[round_item["round_id"]] = round_item
    # Append the identifier to deterministic display order.
    state.setdefault("round_order", []).append(round_item["round_id"])
    # Remove oldest rounds when history exceeds the game-local limit.
    while len(state["round_order"]) > ROUND_HISTORY_LIMIT:
        # Remove the oldest identifier from display order.
        oldest = state["round_order"].pop(0)
        # Remove its round body while tolerating already-pruned state.
        state["rounds"].pop(oldest, None)


# Deal an initial Casino War comparison and emit stable ledger instructions.
def start_round(state: dict, player_id: str, wager, action_id: str, *, seed=None, round_id: str | None = None, created_at: str | None = None) -> dict:
    # Prevent overlapping decisions and ledger recovery for one player.
    require_no_active_round(state)
    # Normalize the wager before cards or state change.
    amount = normalize_wager(wager)
    # Ensure the initial deal plus a possible war can finish from one shoe.
    ensure_shoe(state, seed=seed, required_cards=7)
    # Draw the player card first according to Casino War dealing order.
    player_card = draw_card(state)
    # Draw the dealer card second according to Casino War dealing order.
    dealer_card = draw_card(state)
    # Build the complete round before any wallet adapter is called.
    round_item = {
        "round_id": round_id or new_id("cw"),  # Use an injected id in deterministic tests.
        "player_id": player_id,  # Keep state bound to the resolved session player.
        "created_at": created_at or utc_now(),  # Preserve a stable display timestamp.
        "phase": "war_decision",  # Replace this below for non-tie outcomes.
        "wager": amount,  # Record the original ante.
        "war_wager": 0.0,  # Add the matching war wager only on that decision.
        "player_card": card_payload(player_card),  # Expose the initial player card.
        "dealer_card": card_payload(dealer_card),  # Expose the initial dealer card.
        "burn_cards": [],  # Keep burned identities audit-visible after war.
        "war_player_card": None,  # Reserve stable UI space for the war card.
        "war_dealer_card": None,  # Reserve stable UI space for the dealer war card.
        "outcome": "tie",  # A tie remains unresolved until the player decides.
        "payout": 0.0,  # Store total credit, including returned stakes.
        "ledger_intents": [],  # Persist replay-safe money instructions.
    }
    # Always debit the initial wager through the shared ledger adapter.
    round_item["ledger_intents"].append(ledger_intent(f"cw:{action_id}:ante", "debit", amount, "CASINO_WAR_ANTE_DEBIT", round_item, "ante"))
    # Compare the initial cards without suit tie breakers.
    comparison = compare_cards(player_card, dealer_card)
    # Settle an initial player win at even money.
    if comparison > 0:
        # Record the player-facing outcome.
        round_item["outcome"] = "player_win"
        # Credit stake plus even-money winnings.
        round_item["payout"] = round(amount * state["rules"]["initial_win_return"], 2)
        # Mark the round for ledger reconciliation.
        round_item["phase"] = "ledger_pending"
        # Add the stable settlement credit after the ante instruction.
        round_item["ledger_intents"].append(ledger_intent(f"cw:{action_id}:settlement", "credit", round_item["payout"], "CASINO_WAR_SETTLEMENT_CREDIT", round_item, "initial_win"))
    # Settle an initial dealer win with no credit.
    elif comparison < 0:
        # Record the losing outcome without generating a zero-value ledger event.
        round_item["outcome"] = "dealer_win"
        # Mark the round settled once its ante debit commits.
        round_item["phase"] = "ledger_pending"
    # Keep an initial tie in the explicit decision phase.
    else:
        # Preserve the tie outcome until surrender or war is selected.
        round_item["phase"] = "war_decision"
    # Persist the new round in bounded history.
    store_round(state, round_item)
    # Return the mutable round owned by the caller's state document.
    return round_item


# Return one retained round or report a stable validation failure.
def get_round(state: dict, round_id: str) -> dict:
    # Read the requested round from player-scoped state.
    round_item = state.get("rounds", {}).get(round_id)
    # Reject missing and cross-player-inaccessible identifiers alike.
    if not round_item:
        # Avoid leaking any round details in the failure.
        raise ValidationError("Casino War round was not found")
    # Return the stored round for a validated state transition.
    return round_item


# Settle an initial tie by returning half the original wager.
def surrender(state: dict, round_id: str, action_id: str) -> dict:
    # Load the retained round from this player's state.
    round_item = get_round(state, round_id)
    # Allow surrender only from the unresolved tie decision.
    if round_item.get("phase") != "war_decision":
        # Reject replay under a new action id after the decision was made.
        raise ConflictError("Casino War surrender is only available after an initial tie")
    # Record the terminal surrender outcome.
    round_item["outcome"] = "surrender"
    # Return half the original wager according to fixed table rules.
    round_item["payout"] = round(round_item["wager"] * state["rules"]["surrender_return"], 2)
    # Mark settlement as pending until the ledger adapter commits it.
    round_item["phase"] = "ledger_pending"
    # Add one stable credit instruction for crash-safe replay.
    round_item["ledger_intents"].append(ledger_intent(f"cw:{action_id}:surrender", "credit", round_item["payout"], "CASINO_WAR_SURRENDER_CREDIT", round_item, "surrender"))
    # Return the transitioned round.
    return round_item


# Resolve an initial tie by placing a matching war wager and dealing again.
def go_to_war(state: dict, round_id: str, action_id: str) -> dict:
    # Load the retained round from this player's state.
    round_item = get_round(state, round_id)
    # Allow war only from the unresolved tie decision.
    if round_item.get("phase") != "war_decision":
        # Reject duplicate transitions under a different client action id.
        raise ConflictError("Casino War is only available after an initial tie")
    # Require the configured burn cards and comparison cards to remain in this shoe.
    required_cards = int(state["rules"]["burn_cards"]) + 2
    # Fail closed rather than replacing the shoe in the middle of a tied round.
    if len(state.get("shoe", [])) < required_cards:
        # Report the impossible or corrupt state explicitly.
        raise ConflictError("Casino War shoe cannot complete the tied round")
    # Draw and expose the fixed number of burn cards for auditability.
    round_item["burn_cards"] = [card_payload(draw_card(state)) for _ in range(int(state["rules"]["burn_cards"]))]
    # Deal the player's war card before the dealer's war card.
    player_card = draw_card(state)
    # Deal the dealer's final comparison card.
    dealer_card = draw_card(state)
    # Store both war cards in the public round shape.
    round_item["war_player_card"] = card_payload(player_card)
    # Store the dealer war card beside the player's card.
    round_item["war_dealer_card"] = card_payload(dealer_card)
    # Match the original wager for the war decision.
    round_item["war_wager"] = round_item["wager"]
    # Add the war wager debit before any possible settlement credit.
    round_item["ledger_intents"].append(ledger_intent(f"cw:{action_id}:war-wager", "debit", round_item["war_wager"], "CASINO_WAR_WAR_WAGER_DEBIT", round_item, "war_wager"))
    # Compare war cards with a second tie favoring the player.
    comparison = compare_cards(player_card, dealer_card)
    # Pay when the player card wins or ties under the fixed rule.
    if comparison >= 0:
        # Distinguish a second tie in history and localized UI.
        round_item["outcome"] = "war_tie_win" if comparison == 0 else "war_win"
        # Return both stakes and even-money profit on the original wager.
        round_item["payout"] = round(round_item["wager"] * state["rules"]["war_win_return"], 2)
        # Add one settlement credit after the matching war debit.
        round_item["ledger_intents"].append(ledger_intent(f"cw:{action_id}:settlement", "credit", round_item["payout"], "CASINO_WAR_SETTLEMENT_CREDIT", round_item, "war_win"))
    # Lose both wagers when the dealer's war card is higher.
    else:
        # Record the terminal dealer result without a zero credit.
        round_item["outcome"] = "war_loss"
        # Keep payout at zero because both debits remain settled.
        round_item["payout"] = 0.0
    # Mark every war result for ordered ledger reconciliation.
    round_item["phase"] = "ledger_pending"
    # Return the transitioned round.
    return round_item


# Build a client-safe round without internal ledger instruction details.
def public_round(round_item: dict, committed_actions: dict | None = None) -> dict:
    # Read committed actions through an empty fallback for pure engine tests.
    committed = committed_actions or {}
    # Copy only fields intended for the game API.
    exposed = {key: value for key, value in round_item.items() if key != "ledger_intents"}
    # Summarize settlement progress without exposing ledger internals.
    exposed["settlement"] = {
        "required_actions": len(round_item.get("ledger_intents", [])),  # Count required movements.
        "committed_actions": sum(1 for intent in round_item.get("ledger_intents", []) if intent["action_id"] in committed),  # Count committed movements.
        "complete": round_item.get("phase") == "settled",  # Report the terminal state directly.
    }
    # Return the detached public object.
    return exposed


# Build the public player-scoped state in newest-first display order.
def public_state(state: dict) -> dict:
    # Read retained order while tolerating migrated state without the field.
    order = list(state.get("round_order", []))
    # Resolve retained rounds from newest to oldest.
    rounds = [public_round(state["rounds"][round_id], state.get("ledger_actions")) for round_id in reversed(order) if round_id in state.get("rounds", {})]
    # Return table rules, shoe information, and bounded round history.
    return {
        "rules": dict(state.get("rules", {})),  # Expose fixed Casino War rules.
        "shoe_id": state.get("shoe_id"),  # Identify the current shoe.
        "shoe_count": len(state.get("shoe", [])),  # Report remaining cards without exposing order.
        "shoes_dealt": int(state.get("shoes_dealt", 0)),  # Report shoe replacements.
        "rounds": rounds,  # Provide newest-first reload-safe history.
        "active_round": next((item for item in rounds if item.get("phase") in {"war_decision", "ledger_pending"}), None),  # Identify the actionable round.
    }
