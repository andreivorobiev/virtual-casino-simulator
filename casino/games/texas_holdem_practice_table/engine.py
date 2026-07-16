"""Deterministic fixed-ante Texas Hold'em practice-table rules for issue #95.

Requirements: CARD-001, POKER-001, LEDGER-005, LEDGER-006, and SESSION-005.
"""

# Import detached-copy support for immutable compact replay snapshots.
import copy
# Import finite-number checks so NaN cannot bypass wager bounds.
import math

# Import shared card construction so this game never owns another deck model.
from casino.core.cards import shuffled_deck
# Import the shared seven-card evaluator for Hold'em showdown ranking.
from casino.core.poker import evaluate_hand
# Import public domain errors for stable API boundary behavior.
from casino.errors import ConflictError, NotFoundError, ValidationError

# Identify every state document and ledger event owned by this game.
GAME_ID = "texas_holdem_practice_table"
# Retain bounded private hands while compact snapshots preserve older replay results.
RECENT_HAND_LIMIT = 20
# Require four fixed-limit decisions after the opening ante.
ACTION_PHASES = ("preflop", "flop", "turn", "river")
# Reveal the standard number of community cards at each betting transition.
REVEALED_BY_PHASE = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}
# Reserve one ante plus four possible calls from the wallet at hand start.
RESERVED_BET_UNITS = 5
# Match the one-time funded-account seed accepted for issue #189.
PRACTICE_ACCOUNT_FUNDING = 100_000.0
# Define the three localized server-managed seats and their real player wallets.
PRACTICE_OPPONENTS = (
    {"seat_id": "opponent_1", "player_id": "bot_1", "label_key": "opponents.ava", "policy": "practice_call"},  # Seat the first funded practice opponent.
    {"seat_id": "opponent_2", "player_id": "bot_2", "label_key": "opponents.mia", "policy": "practice_call"},  # Seat the second funded practice opponent.
    {"seat_id": "opponent_3", "player_id": "bot_3", "label_key": "opponents.zoe", "policy": "practice_call"},  # Seat the third funded practice opponent.
)


# Build an empty player-scoped state document for reload-safe storage.
def default_state() -> dict:
    # Return active state, bounded private history, compact snapshots, and receipts.
    return {"active_hand": None, "recent_hands": [], "replay_hands": {}, "requests": {}, "ledger_actions": {}}


# Normalize one fixed-limit wager before reserving the complete hand exposure.
def require_base_wager(value) -> float:
    # Require an actual JSON number and reject booleans or numeric strings.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # Match the additive OpenAPI number contract without input coercion.
        raise ValidationError("base_wager must be numeric")
    # Reject floating-point NaN and infinities before range comparisons.
    if isinstance(value, float) and not math.isfinite(value):
        # Prevent non-finite values from reaching persisted state or wallet code.
        raise ValidationError("base_wager must be finite")
    # Enforce the documented raw minimum before precision rounding.
    if value < 0.01:
        # Reject values that would otherwise round up into the allowed range.
        raise ValidationError("base_wager must be at least 0.01")
    # Enforce the documented raw maximum without overflowing float conversion.
    if value > 20_000:
        # Reject values that would otherwise round down into the allowed range.
        raise ValidationError("base_wager must be at most 20000")
    # Round an already finite, bounded wager to shared ledger precision.
    wager = round(float(value), 2)
    # Return the canonical two-decimal wager unit.
    return wager


# Construct one stable ledger instruction without calling wallet code from the engine.
def ledger_intent(action_id: str, direction: str, amount: float, transaction_type: str, hand: dict, component: str, seat: dict) -> dict:
    # Return every audit dimension required by the shared ledger policy.
    return {
        "action_id": action_id,  # Preserve the unique retry-safe movement identity.
        "direction": direction,  # Tell the adapter whether to debit or credit.
        "amount": round(float(amount), 2),  # Normalize the positive movement magnitude.
        "transaction_type": transaction_type,  # Preserve the game-specific audit type.
        "game": GAME_ID,  # Identify this module in append-only history.
        "round_id": hand["hand_id"],  # Correlate movement with the complete hand.
        "player_id": seat["player_id"],  # Bind the movement to the human or funded opponent wallet.
        "managed_opponent": seat.get("kind") == "server_bot",  # Select the Admin-audited opponent seam when required.
        # Group recovery metadata beneath the established ledger details field.
        "details": {
            "texas_holdem_action_id": action_id,  # Expose the recovery key to ledger scans.
            "component": component,  # Distinguish escrow, refund, and pot payout.
            "base_wager": hand["base_wager"],  # Preserve the fixed-limit unit.
            "reserved_amount": hand["reserved_amount"],  # Preserve the maximum reserved exposure.
            "seat_id": seat["seat_id"],  # Correlate the wallet movement with stable table order.
            "controller_policy": seat.get("policy"),  # Preserve the automated policy for Admin audit.
            "session_owner_id": hand["human_player_id"],  # Retain owner correlation only in server ledger details.
        },
    }


# Build one normalized seat with a reserved table stack and opening ante.
def seat_state(seat_id: str, player_id: str, kind: str, label_key: str, reserved_amount: float, base_wager: float, policy: str | None = None) -> dict:
    # Return only serializable seat state so reload preserves every decision.
    return {
        "seat_id": seat_id,  # Identify table order independently of player identity.
        "player_id": player_id,  # Bind private settlement state to one real ledger wallet.
        "kind": kind,  # Distinguish the authenticated human from practice opponents.
        "label_key": label_key,  # Let the frontend localize every seat name.
        "policy": policy,  # Record the server policy used for automated actions.
        "hole_cards": [],  # Fill two private cards after every seat is created.
        "stack": round(reserved_amount - base_wager, 2),  # Move the opening ante into the pot.
        "contributed": base_wager,  # Track total table contribution for audit display.
        "folded": False,  # Keep every seat active at the opening deal.
        "acted": False,  # Require one decision during the preflop phase.
    }


# Create one reload-safe hand with a human and three server-managed opponents.
def create_hand(human_player_id: str, base_wager, request_id: str, *, seed=None, hand_id: str, created_at: str) -> dict:
    # Validate the fixed-limit wager before generating cards or intents.
    wager = require_base_wager(base_wager)
    # Calculate the single ledger escrow debit that covers every possible call.
    reserved_amount = round(wager * RESERVED_BET_UNITS, 2)
    # Build the authenticated human seat first so table order remains deterministic.
    seats = [seat_state("human", human_player_id, "human", "seats.you", reserved_amount, wager)]
    # Add every issue-scoped practice opponent without importing another module.
    for opponent in PRACTICE_OPPONENTS:
        # Give each funded server-managed seat the same fixed-limit reserved stack.
        seats.append(seat_state(opponent["seat_id"], opponent["player_id"], "server_bot", opponent["label_key"], reserved_amount, wager, opponent["policy"]))
    # Shuffle through the shared primitive with a test-only deterministic seam.
    deck = shuffled_deck(seed=seed)
    # Deal two private cards in standard round-robin table order.
    for _ in range(2):
        # Give one card to each seat before beginning the next pass.
        for seat in seats:
            # Remove the next shared-deck card and persist its compact code.
            seat["hole_cards"].append(deck.pop(0).code)
    # Burn before the flop so the stored plan follows standard Hold'em dealing.
    first_burn = deck.pop(0).code
    # Deal the three-card flop after the first burn.
    flop = [deck.pop(0).code for _ in range(3)]
    # Burn before the single turn card.
    second_burn = deck.pop(0).code
    # Deal the turn card from the shared shuffled deck.
    turn = deck.pop(0).code
    # Burn before the single river card.
    third_burn = deck.pop(0).code
    # Deal the final river card used at showdown.
    river = deck.pop(0).code
    # Build the complete private hand before any ledger movement occurs.
    hand = {
        "hand_id": hand_id,  # Correlate state, actions, and ledger movements.
        "request_id": request_id,  # Preserve the client start retry key.
        "human_player_id": human_player_id,  # Bind private state to the authenticated user.
        "base_wager": wager,  # Preserve the fixed contribution used on every street.
        "reserved_amount": reserved_amount,  # Preserve the single wallet escrow amount.
        "phase": "preflop",  # Begin with private cards and no visible board.
        "revealed_count": 0,  # Hide all planned community cards initially.
        "community_plan": [*flop, turn, river],  # Persist deterministic reload-safe board cards.
        "burn_cards": [first_burn, second_burn, third_burn],  # Retain private dealing evidence.
        "remaining_deck": [card.code for card in deck],  # Retain the private unused deck for diagnostics.
        "seats": seats,  # Persist human and server-managed table state.
        "pot": round(wager * len(seats), 2),  # Collect four opening antes in table state.
        "current_actor": "human",  # Give the authenticated player the first decision.
        "action_ids": {},  # Retain per-action replay receipts inside the hand.
        "action_log": [],  # Retain localized-display-ready action history.
        "ledger_intents": [],  # Prepare wallet movements before calling the ledger.
        "result": None,  # Leave showdown output empty until terminal play.
        "created_at": created_at,  # Preserve the injected audit timestamp.
    }
    # Prepare one escrow debit that covers each seat's ante and four possible calls.
    for seat in seats:
        # Keep the authenticated human's historical transaction vocabulary stable.
        transaction_type = "TEXAS_HOLDEM_ESCROW_DEBIT" if seat["kind"] == "human" else "PRACTICE_OPPONENT_ESCROW_DEBIT"
        # Use one player-scoped storage action identity per real table wallet.
        action_id = f"thpt:{request_id}:{seat['seat_id']}:escrow"
        # Persist every human and managed-opponent reserve before wallet reconciliation.
        hand["ledger_intents"].append(ledger_intent(action_id, "debit", reserved_amount, transaction_type, hand, "escrow", seat))
    # Return the complete prepared hand for persistence before wallet movement.
    return hand


# Find a retained hand without exposing another player's state document.
def hand_by_id(state: dict, hand_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_hand"), *state.get("recent_hands", [])]
    # Return the exact retained hand while ignoring empty slots.
    return next((hand for hand in candidates if hand and hand.get("hand_id") == hand_id), None)


# Resolve one retained hand or raise a stable private lookup error.
def require_hand(state: dict, hand_id: str) -> dict:
    # Search only the authenticated player's state document.
    hand = hand_by_id(state, hand_id)
    # Reject unknown and cross-player identifiers identically.
    if hand is None:
        # Avoid revealing whether another player owns the supplied id.
        raise NotFoundError("Texas Hold'em practice hand was not found")
    # Return the retained player-owned hand.
    return hand


# Return one seat by its stable table identifier.
def require_seat(hand: dict, seat_id: str) -> dict:
    # Find the exact seat inside this hand's private table state.
    seat = next((item for item in hand.get("seats", []) if item.get("seat_id") == seat_id), None)
    # Reject invalid actors before any action or stack mutation.
    if seat is None:
        # Keep the action boundary explicit for injected controllers.
        raise ValidationError("Texas Hold'em seat is invalid")
    # Return the validated mutable seat state.
    return seat


# Return active seats in stable table order.
def active_seats(hand: dict) -> list[dict]:
    # Exclude folded seats while preserving original seat order.
    return [seat for seat in hand.get("seats", []) if not seat.get("folded")]


# Return the human choices allowed in the current public state.
def legal_actions(hand: dict) -> list[str]:
    # Offer no actions while settlement or history is being displayed.
    if hand.get("phase") not in ACTION_PHASES:
        # Return an empty list for terminal or corrupted phases.
        return []
    # Offer no human actions while a server-managed seat is acting.
    if hand.get("current_actor") != "human":
        # Keep controls disabled until automatic actions finish.
        return []
    # Read the authenticated seat's remaining reserved table stack.
    human = require_seat(hand, "human")
    # Permit a call only when one full fixed-limit unit remains reserved.
    actions = ["call"] if human.get("stack", 0) >= hand.get("base_wager", 0) else []
    # Always permit folding during an actionable human turn.
    actions.append("fold")
    # Return the complete stable action vocabulary.
    return actions


# Move play to the next seat or street after one validated action.
def advance_after_action(hand: dict, *, completed_at: str) -> None:
    # Settle immediately when every other seat has folded.
    if len(active_seats(hand)) == 1:
        # Award the current pot without requiring undealt community cards.
        settle_hand(hand, completed_at=completed_at)
        # Stop after terminal settlement preparation.
        return
    # Read stable table order for the remaining-action search.
    seats = hand.get("seats", [])
    # Locate the actor that just completed its decision.
    actor_index = next(index for index, seat in enumerate(seats) if seat.get("seat_id") == hand.get("current_actor"))
    # Search every later table seat before wrapping to the beginning.
    ordered = seats[actor_index + 1:] + seats[:actor_index + 1]
    # Find the next active seat that has not acted during this street.
    next_seat = next((seat for seat in ordered if not seat.get("folded") and not seat.get("acted")), None)
    # Continue the current street when another decision remains.
    if next_seat is not None:
        # Transfer action ownership to the next validated seat.
        hand["current_actor"] = next_seat["seat_id"]
        # Stop before any street transition.
        return
    # Read the current betting phase index after every active seat acted.
    phase_index = ACTION_PHASES.index(hand["phase"])
    # Resolve showdown after the river betting round completes.
    if phase_index == len(ACTION_PHASES) - 1:
        # Evaluate all active seven-card hands and prepare settlement credits.
        settle_hand(hand, completed_at=completed_at)
        # Stop after terminal settlement preparation.
        return
    # Advance to the next standard Hold'em street.
    next_phase = ACTION_PHASES[phase_index + 1]
    # Store the player-facing phase used by API and frontend translation.
    hand["phase"] = next_phase
    # Reveal the standard number of planned community cards for the new street.
    hand["revealed_count"] = REVEALED_BY_PHASE[next_phase]
    # Reset street-action markers for every seat still in the hand.
    for seat in active_seats(hand):
        # Require each active seat to decide once on the new street.
        seat["acted"] = False
    # Give the human first action when still active, otherwise continue with a server seat.
    hand["current_actor"] = next((seat["seat_id"] for seat in active_seats(hand) if seat["seat_id"] == "human"), active_seats(hand)[0]["seat_id"])


# Apply one human or server-managed action through the same validation path.
def apply_action(hand: dict, seat_id: str, action: str, action_id: str, *, created_at: str, automated: bool = False) -> dict:
    # Replay an identical already-applied action without mutating state twice.
    previous = hand.setdefault("action_ids", {}).get(action_id)
    # Handle a duplicate action id inside the retained hand.
    if previous is not None:
        # Reject one id reused for a different actor or decision.
        if previous.get("seat_id") != seat_id or previous.get("action") != action:
            # Keep action ids bound to exactly one logical command.
            raise ConflictError("action_id was already used for a different table action")
        # Return the already-transitioned hand for safe retry replay.
        return hand
    # Allow decisions only during the four fixed-limit betting phases.
    if hand.get("phase") not in ACTION_PHASES:
        # Reject stale clicks after settlement.
        raise ConflictError("This Texas Hold'em hand is no longer accepting actions")
    # Require strict turn order for humans and server-managed opponents alike.
    if hand.get("current_actor") != seat_id:
        # Prevent callers from skipping or impersonating a table seat.
        raise ConflictError("This seat is not the current actor")
    # Resolve the actor inside the private hand state.
    seat = require_seat(hand, seat_id)
    # Reject already-folded seats before reading the requested action.
    if seat.get("folded"):
        # Keep folded seats permanently inactive.
        raise ConflictError("This seat has already folded")
    # Normalize the two fixed-limit practice actions.
    normalized_action = str(action or "").strip().lower()
    # Reject decisions outside call or fold.
    if normalized_action not in {"call", "fold"}:
        # Keep the API vocabulary narrow and deterministic.
        raise ValidationError("action must be call or fold")
    # Capture the current phase before advancing the table.
    phase = hand["phase"]
    # Start with no additional table contribution for a fold.
    amount = 0.0
    # Move one reserved wager unit into the pot for a call.
    if normalized_action == "call":
        # Read the one fixed-limit contribution required this street.
        amount = hand["base_wager"]
        # Reject calls after the seat's reserved table stack is exhausted.
        if seat.get("stack", 0) < amount:
            # Fail closed instead of creating a negative virtual stack.
            raise ConflictError("This seat has no reserved stack for another call")
        # Subtract only from the already ledger-reserved table stack.
        seat["stack"] = round(seat["stack"] - amount, 2)
        # Add the fixed unit to this seat's cumulative contribution.
        seat["contributed"] = round(seat["contributed"] + amount, 2)
        # Add the reserved contribution to the shared table pot.
        hand["pot"] = round(hand["pot"] + amount, 2)
    # Mark a fold without any additional token allocation.
    else:
        # Remove the seat from all later streets and showdown comparison.
        seat["folded"] = True
    # Mark the seat as complete for this betting phase.
    seat["acted"] = True
    # Store the private replay receipt before advancing the table.
    hand["action_ids"][action_id] = {"seat_id": seat_id, "action": normalized_action, "phase": phase}
    # Append a localized-display-ready action record without backend prose.
    hand.setdefault("action_log", []).append({"action_id": action_id, "seat_id": seat_id, "action": normalized_action, "phase": phase, "amount": amount, "automated": bool(automated), "created_at": created_at})
    # Move to the next seat, street, or settlement through one shared transition.
    advance_after_action(hand, completed_at=created_at)
    # Return the mutated reload-safe hand.
    return hand


# Run server-managed practice seats until control returns to the human or settlement.
def advance_opponents(hand: dict, client_action_id: str, *, clock) -> dict:
    # Continue only while an actionable server-managed seat owns the turn.
    while hand.get("phase") in ACTION_PHASES and hand.get("current_actor") != "human":
        # Resolve the current automated seat through the same seat validator.
        seat = require_seat(hand, hand["current_actor"])
        # Fail closed if a non-opponent seat reached the automation path.
        if seat.get("kind") != "server_bot":
            # Prevent implicit automation of any future human or shared bot controller.
            raise ConflictError("Only server-managed practice opponents can act automatically")
        # Derive a stable retry id from the triggering command, phase, and seat.
        action_id = f"thpt:{client_action_id}:{hand['phase']}:{seat['seat_id']}"
        # Apply the fixed practice-call policy through the same engine validation path.
        apply_action(hand, seat["seat_id"], "call", action_id, created_at=clock(), automated=True)
    # Return after human control resumes or the hand reaches settlement.
    return hand


# Evaluate active seats, split the pot, and prepare human refund/payout credits.
def settle_hand(hand: dict, *, completed_at: str) -> dict:
    # Treat repeated settlement calls as idempotent reads.
    if hand.get("phase") in {"ledger_pending", "settled"}:
        # Return the already-prepared terminal hand unchanged.
        return hand
    # Read every non-folded seat in stable table order.
    contenders = active_seats(hand)
    # Reject impossible table state instead of inventing a winner.
    if not contenders:
        # Surface corruption explicitly for recovery diagnostics.
        raise ConflictError("Texas Hold'em hand has no active seats")
    # Prepare showdown rank metadata only when comparison is required.
    hand_ranks = {}
    # Award an uncontested pot without revealing undealt community cards.
    if len(contenders) == 1:
        # Select the only remaining active seat as winner.
        winners = contenders
    # Evaluate standard seven-card Hold'em when multiple seats remain.
    else:
        # Reveal the complete community board for showdown.
        hand["revealed_count"] = 5
        # Evaluate every active seat through the shared POKER-001 primitive.
        ranked = [(seat, evaluate_hand([*seat["hole_cards"], *hand["community_plan"]])) for seat in contenders]
        # Find the strongest standard category and deterministic tie breakers.
        best_key = max(rank.comparison_key for _, rank in ranked)
        # Retain every seat sharing the strongest comparison key.
        winners = [seat for seat, rank in ranked if rank.comparison_key == best_key]
        # Store localized-result keys and exact best-five cards for showdown display.
        hand_ranks = {seat["seat_id"]: {"name": rank.name, "best_cards": [card.code for card in rank.cards]} for seat, rank in ranked}
    # Convert the pot to integer cents for deterministic split handling.
    pot_cents = int(round(hand["pot"] * 100))
    # Calculate the equal whole-cent share for every winner.
    share_cents, remainder = divmod(pot_cents, len(winners))
    # Initialize every seat's terminal table payout at zero.
    payouts = {seat["seat_id"]: 0.0 for seat in hand.get("seats", [])}
    # Assign stable split shares and any remainder in table order.
    for index, winner in enumerate(winners):
        # Give one extra cent to the earliest winners until no remainder remains.
        winner_cents = share_cents + (1 if index < remainder else 0)
        # Store the exact two-decimal pot share.
        payouts[winner["seat_id"]] = winner_cents / 100
    # Resolve the authenticated human seat for player-facing settlement fields.
    human = require_seat(hand, "human")
    # Return any escrow amount not allocated to ante or calls.
    refund = round(human.get("stack", 0), 2)
    # Credit the human's pot share only when the human won or tied.
    payout = round(payouts.get("human", 0), 2)
    # Classify the player-facing terminal result without exposing evaluator internals.
    human_outcome = "folded" if human.get("folded") else "win" if winners == [human] else "split" if human in winners else "loss"
    # Store complete terminal data before any settlement credit is attempted.
    hand["result"] = {
        "winner_seat_ids": [seat["seat_id"] for seat in winners],  # Identify all split-pot winners.
        "payouts": payouts,  # Expose table-result shares for practice review.
        "hand_ranks": hand_ranks,  # Expose shared-evaluator result keys at showdown.
        "human_outcome": human_outcome,  # Drive localized result language.
        "human_refund": refund,  # Report unused escrow returned through the ledger.
        "human_payout": payout,  # Report the human pot share credited through the ledger.
        "human_return": round(refund + payout, 2),  # Summarize all terminal wallet credits.
        "human_net": round(refund + payout - hand["reserved_amount"], 2),  # Compare credits with the opening escrow debit.
    }
    # Reconcile unused escrow and pot shares for every real wallet at the table.
    for seat in hand.get("seats", []):
        # Return the portion of this seat's maximum exposure that was never contributed.
        seat_refund = round(seat.get("stack", 0), 2)
        # Read this seat's deterministic whole-cent pot share.
        seat_payout = round(payouts.get(seat["seat_id"], 0), 2)
        # Select stable human or managed-opponent audit transaction names.
        refund_type = "TEXAS_HOLDEM_ESCROW_REFUND_CREDIT" if seat["kind"] == "human" else "PRACTICE_OPPONENT_ESCROW_REFUND"
        # Select stable human or managed-opponent payout transaction names.
        payout_type = "TEXAS_HOLDEM_PAYOUT_CREDIT" if seat["kind"] == "human" else "PRACTICE_OPPONENT_PAYOUT"
        # Prepare one distinct refund action only when unused escrow remains.
        if seat_refund > 0:
            # Bind the refund identity to the hand and funded seat wallet.
            hand["ledger_intents"].append(ledger_intent(f"thpt:{hand['hand_id']}:{seat['seat_id']}:refund", "credit", seat_refund, refund_type, hand, "refund", seat))
        # Prepare one distinct payout action only when this seat won a pot share.
        if seat_payout > 0:
            # Bind the payout identity to the hand and funded seat wallet.
            hand["ledger_intents"].append(ledger_intent(f"thpt:{hand['hand_id']}:{seat['seat_id']}:payout", "credit", seat_payout, payout_type, hand, "payout", seat))
    # Mark settlement pending until the controller reconciles every ledger intent.
    hand["phase"] = "ledger_pending"
    # Clear turn ownership because no further table decision is legal.
    hand["current_actor"] = None
    # Preserve the deterministic terminal timestamp before wallet credits.
    hand["completed_at"] = completed_at
    # Return the prepared terminal hand for persistence and reconciliation.
    return hand


# Move a reconciled hand into bounded private and compact replay history.
def archive_hand(state: dict, hand: dict) -> None:
    # Require the ledger controller to finish settlement before archiving.
    if hand.get("phase") != "settled":
        # Prevent pending settlement from disappearing from the active slot.
        raise ConflictError("Texas Hold'em settlement is not complete")
    # Clear the active slot only when it still references this exact hand.
    if (state.get("active_hand") or {}).get("hand_id") == hand.get("hand_id"):
        # Remove the terminal hand from the actionable location.
        state["active_hand"] = None
    # Remove an older retained copy before appending idempotent recovery output.
    recent = [item for item in state.get("recent_hands", []) if item.get("hand_id") != hand.get("hand_id")]
    # Append the newest completed hand at the end for stable history order.
    recent.append(hand)
    # Identify full private records leaving the bounded display/recovery window.
    evicted = recent[:-RECENT_HAND_LIMIT]
    # Read or initialize sanitized snapshots keyed by stable hand identity.
    replay_hands = state.setdefault("replay_hands", {})
    # Compact every evicted full hand into an immutable public response snapshot.
    for evicted_hand in evicted:
        # Build the settled whitelist after every ledger marker was committed.
        snapshot = public_hand(evicted_hand, state.get("ledger_actions"))
        # Detach nested result and seat data before dropping the private record.
        replay_hands[evicted_hand["hand_id"]] = copy.deepcopy(snapshot)
    # Retain only the newest full private hands for display and recovery scans.
    state["recent_hands"] = recent[-RECENT_HAND_LIMIT:]


# Build one client-safe seat while redacting every active opponent hole card.
def public_seat(seat: dict, settled: bool) -> dict:
    # Reveal human cards throughout play and opponent cards only after settlement.
    reveal_cards = seat.get("kind") == "human" or settled
    # Return a strict public whitelist so policies and private data cannot leak.
    return {
        "seat_id": seat.get("seat_id"),  # Preserve stable frontend seat hooks.
        "kind": seat.get("kind"),  # Distinguish the human and server opponents.
        "label_key": seat.get("label_key"),  # Let the active locale name the seat.
        "hole_cards": list(seat.get("hole_cards", [])) if reveal_cards else ["??", "??"],  # Redact active opponent cards.
        "stack": seat.get("stack"),  # Show remaining reserved practice stack.
        "contributed": seat.get("contributed"),  # Show cumulative table contribution.
        "folded": bool(seat.get("folded")),  # Communicate inactive seats beyond color.
    }


# Build one client-safe hand without deck, burn, policy, or retry-key leakage.
def public_hand(hand, committed_actions: dict | None = None):
    # Preserve empty active-hand slots in state responses.
    if hand is None:
        # Return JSON null instead of a placeholder object.
        return None
    # Treat only fully reconciled history as showdown-safe for opponent cards.
    settled = hand.get("phase") == "settled"
    # Read committed ledger markers through an empty fallback for engine tests.
    committed = committed_actions or {}
    # Expose action history without private retry ids or backend policy fields.
    actions = [{key: item.get(key) for key in ("seat_id", "action", "phase", "amount", "automated", "created_at")} for item in hand.get("action_log", [])]
    # Return a strict public whitelist for reload-safe browser rendering.
    return {
        "hand_id": hand.get("hand_id"),  # Preserve the public action route identifier.
        "base_wager": hand.get("base_wager"),  # Show the fixed-limit unit.
        "reserved_amount": hand.get("reserved_amount"),  # Explain the opening escrow debit.
        "phase": hand.get("phase"),  # Drive localized player-facing status.
        "community_cards": list(hand.get("community_plan", []))[: int(hand.get("revealed_count", 0))],  # Reveal only dealt streets.
        "seats": [public_seat(seat, settled) for seat in hand.get("seats", [])],  # Redact opponent cards before settlement.
        "pot": hand.get("pot"),  # Show the current table pot.
        "current_actor": hand.get("current_actor"),  # Identify whose turn the server reports.
        "legal_actions": legal_actions(hand),  # Drive stable enabled controls.
        "action_log": actions,  # Provide bounded practice review history.
        "result": hand.get("result") if settled else None,  # Hide showdown result until credits reconcile.
        # Summarize durable wallet reconciliation without exposing internal intent payloads.
        "settlement": {
            "required_actions": len(hand.get("ledger_intents", [])),  # Count escrow/refund/payout movements.
            "committed_actions": sum(1 for intent in hand.get("ledger_intents", []) if intent.get("action_id") in committed),  # Count durable markers.
            "complete": settled,  # Report whether every terminal movement completed.
        },
        "created_at": hand.get("created_at"),  # Preserve hand audit timing.
        "completed_at": hand.get("completed_at"),  # Preserve terminal timing when present.
    }


# Build the complete client-safe player state in newest-first history order.
def public_state(state: dict) -> dict:
    # Read committed markers once for active and historical settlement evidence.
    committed = state.get("ledger_actions", {})
    # Select only the newest display window without exposing compact replay state.
    recent = list(state.get("recent_hands", []))[-RECENT_HAND_LIMIT:]
    # Return one active slot plus bounded newest-first settled history.
    return {
        "active_hand": public_hand(state.get("active_hand"), committed),  # Expose only the actionable hand.
        "recent_hands": [public_hand(hand, committed) for hand in reversed(recent)],  # Show newest completed hands first.
        # Publish fixed practice-table limits so the frontend can explain gameplay.
        "rules": {
            "opponent_count": len(PRACTICE_OPPONENTS),  # Describe the fixed server-opponent profile.
            "funded_opponents": True,  # Confirm every automatic seat settles through a real bot wallet.
            "reserved_bet_units": RESERVED_BET_UNITS,  # Explain the maximum opening escrow.
            "actions": ["call", "fold"],  # Publish the narrow practice action vocabulary.
        },
    }
