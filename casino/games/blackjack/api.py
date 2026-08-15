# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Blackjack API actions, provider-atomic hand persistence, and exactly-once settlement orchestration.
# Import deep-copy support for exact prepared-action rollback and settlement comparison.
import copy

from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.core.validation import require_amount, require_player_id
# Import the descriptor allowlist so the handler cannot drift from central router coercion.
from casino.core.game_rules import clamp_state_rules, declared_fields
from casino.core import players, logger
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
from casino.games.blackjack import engine
from casino.errors import ValidationError, ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "blackjack"
# Bind every Blackjack movement to one storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "hand_id")
# Reserve one private state key for a money action prepared before its ledger effects complete.
PENDING_ACTION_KEY = "_blackjack_pending_action"

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the exposed_round function used by this module.
def exposed_round(rnd):
    if not rnd: return None
    # Set copy to the value needed for the next operation.
    copy = {**rnd, "dealer": {**rnd["dealer"]}}
    if copy["dealer"].get("hole_card_hidden") and copy["dealer"].get("cards"):
        # Set copy["dealer"] to the value needed for the next operation.
        copy["dealer"] = {**copy["dealer"], "cards": [copy["dealer"]["cards"][0], "??"]}
    return copy

# Define the state_payload function used by this module.
def state_payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    return {"game": GAME_ID, "state": {"rules": state.get("rules"), "shoe_count": len(state.get("shoe",[])), "rounds": {rid: exposed_round(r) for rid,r in state.get("rounds",{}).items()}}, "player": players.get_player(player_id), "players": visible_players}

# Replace one caller-owned snapshot with the authoritative provider result. (BJ-033)
def _refresh_state(state: dict, authoritative: dict) -> None:
    # Remove stale top-level fields before copying the complete latest document.
    state.clear()
    # Copy provider-owned state into the existing response object identity.
    state.update(authoritative)


# Clamp descriptor-owned rules before an atomic callback reaches the engine. (BJ-033, SEC-014)
def _canonical_state(current: dict) -> dict:
    # Reuse the catalog-owned defaults and domains without duplicating Blackjack limits.
    repaired, _repaired_fields = clamp_state_rules(GAME_ID, current)
    # Return the repaired latest document for engine consumption and publication.
    return repaired


# Compare one terminal round while ignoring only final publication markers. (BJ-033)
def _settlement_shape(rnd: dict) -> dict:
    # Copy the complete round so validation never mutates provider or caller state.
    shape = copy.deepcopy(rnd)
    # Normalize the sole round field changed by final publication.
    shape["status"] = "settled_pending_credit"
    # Remove only the display marker written after an exact settlement claim.
    for hand in shape.get("hands", []):
        # Keep cards, wager, outcome, and payout exact while ignoring the terminal marker.
        hand.pop("credited", None)
    # Return the complete comparable round shape.
    return shape


# Commit one pure Blackjack round transition against the latest provider document. (BJ-033)
def commit_round_transition(player_id: str, state: dict, transition) -> dict:
    # Capture the stable round selected while the provider owns the mutation boundary.
    selected = {}

    # Execute one engine transition inside the JSON/MySQL atomic read-modify-write boundary.
    def commit(current: dict) -> dict:
        # Repair persisted table rules before the latest document reaches game math.
        current = _canonical_state(current)
        # Refuse a second action until the prepared money action is durably reconciled.
        if current.get(PENDING_ACTION_KEY) is not None:
            # Preserve prepared cards and wallet intent for explicit retry recovery.
            raise ConflictError("Blackjack wager state requires settlement recovery")
        # Apply the supplied pure engine transition to the authoritative latest state.
        rnd = transition(current)
        # Capture only the generated or selected stable identity outside provider ownership.
        selected["round_id"] = rnd["round_id"]
        # Return the complete document for atomic publication.
        return current

    # Publish the complete transition through the shared provider boundary.
    committed = update_player_game_state(GAME_ID, player_id, commit, engine.default_state)
    # Refresh the caller so later settlement and response code sees preserved sibling fields.
    _refresh_state(state, committed)
    # Resolve the affected round from the authoritative returned document.
    return engine.get_round(state, selected["round_id"])


# Prepare one money-adjacent transition and rollback metadata under the provider lock. (BJ-033)
def prepare_money_transition(player_id: str, state: dict, round_id: str | None, transition, movement_factory) -> tuple[dict, dict]:
    # Capture the exact prepared marker selected during the provider-owned transition.
    selected = {}

    # Publish cards, state, and immutable ledger intent before the first wallet side effect.
    def prepare(current: dict) -> dict:
        # Repair persisted table rules before the latest document reaches game math.
        current = _canonical_state(current)
        # Refuse overlapping prepared actions for this player document.
        if current.get(PENDING_ACTION_KEY) is not None:
            # Keep one recoverable action rather than combining unrelated wallet intents.
            raise ConflictError("Blackjack wager state requires settlement recovery")
        # Snapshot the authoritative shoe before the pure engine transition consumes cards.
        before_shoe = copy.deepcopy(current.get("shoe", []))
        # Snapshot an existing round or record absence for initial deal rollback.
        before_round = copy.deepcopy(current.get("rounds", {}).get(round_id)) if round_id is not None else None
        # Apply validation, entropy consumption, and round mutation to the latest document.
        rnd = transition(current)
        # Build bounded immutable movement descriptors from the committed round.
        movements = movement_factory(rnd)
        # Require at least one signed ledger movement for a prepared money action.
        if not movements:
            # Reject an internal programming error before any prepared state is published.
            raise ValueError("Blackjack prepared actions require ledger movements")
        # Persist exact before/after fields needed for non-destructive rollback.
        marker = {
            "round_id": rnd["round_id"],
            "before_round": before_round,
            "after_round": copy.deepcopy(rnd),
            "before_shoe": before_shoe,
            "after_shoe": copy.deepcopy(current.get("shoe", [])),
            "movements": copy.deepcopy(movements),
        }
        # Publish the private recovery marker beside the prepared round state.
        current[PENDING_ACTION_KEY] = marker
        # Retain a caller-owned marker for exact ledger reconciliation.
        selected["marker"] = marker
        # Return the complete provider-owned document.
        return current

    # Publish the prepared action atomically against the latest player state.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Refresh the caller with every sibling field retained by the provider.
    _refresh_state(state, prepared)
    # Resolve the affected prepared round from the authoritative state.
    rnd = engine.get_round(state, selected["marker"]["round_id"])
    # Return both public round state and its private settlement marker.
    return rnd, selected["marker"]


# Restore one uncommitted prepared action without overwriting sibling fields. (BJ-033)
def _rollback_prepared_action(player_id: str, state: dict, marker: dict) -> None:
    # Define one exact compare-and-restore mutation under the provider boundary.
    def rollback(current: dict) -> dict:
        # Require the exact prepared marker so another action is never erased.
        if current.get(PENDING_ACTION_KEY) != marker:
            # Fail closed when recovery ownership has changed.
            raise ConflictError("Blackjack wager state requires operator recovery")
        # Resolve the exact round created or changed by the prepared action.
        current_round = current.get("rounds", {}).get(marker["round_id"])
        # Refuse rollback after any same-round or shoe mutation escaped the action lock.
        if current_round != marker["after_round"] or current.get("shoe", []) != marker["after_shoe"]:
            # Preserve all evidence instead of overwriting divergent state.
            raise ConflictError("Blackjack wager state requires operator recovery")
        # Restore the authoritative pre-action shoe without touching sibling fields.
        current["shoe"] = copy.deepcopy(marker["before_shoe"])
        # Remove a newly created round when the prepared action was the initial deal.
        if marker["before_round"] is None:
            # Delete only the exact prepared round identity.
            current.setdefault("rounds", {}).pop(marker["round_id"], None)
        # Restore the exact prior round for double, split, or insurance rollback.
        else:
            # Replace only the action-owned round while preserving other rounds.
            current.setdefault("rounds", {})[marker["round_id"]] = copy.deepcopy(marker["before_round"])
        # Release the private action marker after exact rollback.
        current.pop(PENDING_ACTION_KEY, None)
        # Return the repaired latest document.
        return current

    # Publish rollback atomically and refresh the caller's response snapshot.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, rollback, engine.default_state))


# Apply or replay every movement in one prepared action, then release its marker. (BJ-033)
def settle_prepared_action(player_id: str, state: dict, marker: dict) -> list[dict]:
    # Collect event and replay evidence in descriptor order.
    results = []
    # Start settlement so an ordinary pre-commit failure can restore the prepared state.
    try:
        # Apply debit before any optional credit exactly as the historical handler did.
        for movement in marker["movements"]:
            # Commit or replay the exact immutable movement through the shared gateway.
            event, replayed = SETTLEMENT.apply_once(player_id=player_id, **movement)
            # Preserve the result for the route-specific response adapter.
            results.append({"movement": movement, "event": event, "replayed": replayed})
    # Recover only an action whose ledger proof is definitively absent.
    except Exception:
        # Track whether any prepared movement already committed before the failure surfaced.
        committed = False
        # Inspect each immutable action identity without proposing another wallet mutation.
        for movement in marker["movements"]:
            # Read a compatible committed action when one exists.
            event = SETTLEMENT.find(player_id, movement["action_key"], round_id=movement["round_id"], transaction_type=movement["transaction_type"], request_fingerprint=movement["request_fingerprint"])
            # Validate the signed amount before treating the event as recovery proof.
            if event is not None:
                # Bind proof to the complete immutable movement dimensions.
                SETTLEMENT.validate_existing(event, transaction_type=movement["transaction_type"], round_id=movement["round_id"], signed_amount=movement["signed_amount"], request_fingerprint=movement["request_fingerprint"])
                # Prevent rollback after any debit or credit has committed.
                committed = True
        # Restore cards and round state only when every movement is provably absent.
        if not committed:
            # Publish exact rollback while retaining unrelated sibling updates.
            _rollback_prepared_action(player_id, state, marker)
        # Re-raise the original validation, funds, or provider error.
        raise

    # Define one exact compare-and-release transition after every movement settles.
    def complete(current: dict) -> dict:
        # Accept an overlapping replay only after another worker cleared the same action.
        if current.get(PENDING_ACTION_KEY) is None and current.get("rounds", {}).get(marker["round_id"]) == marker["after_round"] and current.get("shoe", []) == marker["after_shoe"]:
            # Return the already completed latest document unchanged.
            return current
        # Require the exact marker and action-owned state before releasing it.
        if current.get(PENDING_ACTION_KEY) != marker or current.get("rounds", {}).get(marker["round_id"]) != marker["after_round"] or current.get("shoe", []) != marker["after_shoe"]:
            # Preserve divergent state and immutable ledger proof for operator recovery.
            raise ConflictError("Blackjack wager state requires operator recovery")
        # Remove only the private marker after every wallet movement is durable.
        current.pop(PENDING_ACTION_KEY, None)
        # Return the complete latest document.
        return current

    # Publish completion against the latest provider state and refresh the caller.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, complete, engine.default_state))
    # Return ordered event evidence for the public response adapter.
    return results


# Resume one previously prepared wallet action before accepting another mutation. (BJ-033)
def resume_prepared_action(player_id: str, state: dict) -> list[dict]:
    # Read the private marker from the already loaded player state.
    marker = state.get(PENDING_ACTION_KEY)
    # Return no evidence when there is no interrupted action.
    if marker is None:
        # Keep the common mutation preflight cheap for ordinary requests.
        return []
    # Reconcile the immutable movement sequence without drawing or mutating again.
    return settle_prepared_action(player_id, state, copy.deepcopy(marker))


# Finalize one payout-bearing round against the latest document exactly once. (BJ-033)
def finish_if_needed(state: dict, rnd: dict):
    # Return immediately for an action that remains in player turn.
    if rnd.get("status") != "settled_pending_credit":
        # Preserve the established empty credit list response.
        return []
    # Capture the complete terminal pricing before any ledger side effect begins.
    expected = copy.deepcopy(rnd)
    # Collect only newly committed credits for the established response field.
    credits = []
    # Apply every positive hand return under its durable round-and-hand identity.
    for hand in expected["hands"]:
        # Normalize the priced total return to ledger precision.
        due = round(float(hand.get("payout_due", 0)), 2)
        # Skip zero-return losses because they have no ledger action.
        if due <= 0:
            # Continue to the next priced hand.
            continue
        # Commit or replay the exact hand return before terminal state publication.
        event, replayed = SETTLEMENT.apply_once(player_id=expected["player_id"], signed_amount=due, transaction_type="BLACKJACK_SETTLEMENT_CREDIT", round_id=expected["round_id"], action_key=f"{expected['round_id']}:{hand['hand_id']}:settlement", request_fingerprint=f"{expected['round_id']}:{hand['hand_id']}:{hand.get('outcome')}:{due}", details={"hand_id": hand["hand_id"], "outcome": hand.get("outcome")})
        # Report only the newly committed event because replay proof is already durable.
        if not replayed:
            # Preserve the historical credits-list semantics.
            credits.append(event)
    # Capture the hand identities whose history publication this transition owns.
    claimed = []

    # Claim terminal display and history ownership against the latest round.
    def finalize(current: dict) -> dict:
        # Resolve the exact current round under provider ownership.
        current_round = engine.get_round(current, expected["round_id"])
        # Reject any card, wager, outcome, or payout divergence.
        if _settlement_shape(current_round) != _settlement_shape(expected):
            # Preserve both state and ledger evidence for explicit recovery.
            raise ConflictError("Blackjack settled round state requires operator recovery")
        # Mark only hands not already claimed by another finalizer.
        for hand in current_round["hands"]:
            # Skip terminal display rows another worker already claimed.
            if hand.get("credited"):
                # Continue without duplicating history.
                continue
            # Persist the exact hand identity claimed by this transition.
            claimed.append(hand["hand_id"])
            # Mark the hand terminal after its ledger movement is durable or unnecessary.
            hand["credited"] = True
        # Publish the exact terminal round once.
        engine.settle_round(current_round)
        # Return the complete latest document so sibling fields survive.
        return current

    # Publish terminal state atomically and refresh the caller snapshot.
    finalized = update_player_game_state(GAME_ID, expected["player_id"], finalize, engine.default_state)
    # Refresh before building history and the public response.
    _refresh_state(state, finalized)
    # Resolve the authoritative terminal round after the provider update.
    terminal = engine.get_round(state, expected["round_id"])
    # Map exact hand identities to their terminal public details.
    terminal_hands = {hand["hand_id"]: hand for hand in terminal["hands"]}
    # Append one history row only for each hand claimed by this finalizer.
    for hand_id in claimed:
        # Read the exact claimed terminal hand.
        hand = terminal_hands[hand_id]
        # Read the post-settlement wallet balance for the historical projection.
        balance = players.get_player(terminal["player_id"])["balance"]
        # Append one terminal row after state ownership excludes racing duplicates.
        append_history(GAME_ID, terminal["round_id"], terminal["player_id"], "hand", hand["hand_id"], hand["bet"], hand.get("outcome", "unknown"), round(float(hand.get("payout_due", 0)), 2), balance, {"cards": hand["cards"], "dealer": terminal["dealer"]["cards"]})
    # Return only newly committed credit events.
    return credits

# Define the has_active_round function used by this module.
def has_active_round(state):
    return any(r.get("status") in ("player_turn","settled_pending_credit") for r in state.get("rounds",{}).values())


# Apply descriptor-owned settings to the provider-owned latest document. (BJ-034)
def update_table_settings(player_id: str, state: dict, body: dict, fields) -> None:
    # Define one latest-document settings transition that cannot cross an active round.
    def apply(current: dict) -> dict:
        # Re-check the authoritative provider document instead of trusting the caller snapshot.
        if has_active_round(current):
            # Preserve exact current rounds, rules, shoe, and sibling state on conflict.
            raise ConflictError("Finish active blackjack rounds before changing table rules")
        # Resolve descriptor-owned defaults only while the provider owns publication.
        rules = current.setdefault("rules", engine.default_state()["rules"])
        # Copy only centrally coerced descriptor fields so this helper owns no parallel schema.
        for field in fields:
            # Preserve omitted rules while applying each validated caller update.
            if field in body:
                # Store the canonical router value for subsequent engine consumption.
                rules[field] = body[field]
        # Return the complete latest document for atomic provider publication.
        return current

    # Publish settings atomically and refresh the caller for the established response shape.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, apply, engine.default_state))


# Load authoritative state and finish only actions already durably prepared. (BJ-033)
def load_mutation_state(player_id: str) -> dict:
    # Load through the established player-scoped compatibility boundary.
    state = load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Reconcile a wager action interrupted after prepared-state publication.
    resume_prepared_action(player_id, state)
    # Visit a stable identity list because each finalizer refreshes the caller state.
    for round_id in list(state.get("rounds", {})):
        # Resolve the current round after any preceding finalization refresh.
        rnd = state.get("rounds", {}).get(round_id)
        # Finish only a terminal transition whose exact payouts are already persisted.
        if rnd and rnd.get("status") == "settled_pending_credit":
            # Replay ledger effects and publish terminal state exactly once.
            finish_if_needed(state, rnd)
    # Return the fully reconciled snapshot used by the next mutation.
    return state

# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/blackjack/state")
    # Define the state function used by this module.
    def state(body, query): return state_payload(request_player_id(body, query))

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/settings")
    # Define the settings function used by this module.
    def settings(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Apply only centrally coerced fields against the provider-owned latest document. (BJ-034, SEC-014)
        update_table_settings(player_id, state, body, declared_fields(GAME_ID))
        # Preserve the frozen v1 response shape from the authoritative committed document.
        return state_payload(player_id, state)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds")
    # Define the deal function used by this module.
    def deal(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query); amount = require_amount(body.get("bet_amount"))
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Build the opening wager descriptor only after the provider allocates the exact round and hand.
        def initial_movement(rnd):
            # Read the stable opening hand identity from the prepared round.
            hand_id = rnd["hands"][0]["hand_id"]
            # Return the one immutable opening debit.
            return [{"signed_amount": -amount, "transaction_type": "BLACKJACK_INITIAL_BET", "round_id": rnd["round_id"], "action_key": f"{rnd['round_id']}:wager", "request_fingerprint": f"{rnd['round_id']}:{amount}", "details": {"hand_id": hand_id}}]
        # Prepare cards and the opening wager against the authoritative latest state.
        rnd, marker = prepare_money_transition(player_id, state, None, lambda current: engine.new_round(current, player_id, amount), initial_movement)
        # Commit or replay the prepared debit before terminal credit reconciliation.
        settle_prepared_action(player_id, state, marker)
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, engine.get_round(state, rnd["round_id"]))
        # Refresh the response round after prepared marker and terminal settlement publication.
        rnd = engine.get_round(state, rnd["round_id"])
        # Set logger.info("blackjack_round_dealt", round_id to the value needed for the next operation.
        logger.info("blackjack_round_dealt", round_id=rnd["round_id"], player_id=player_id, bet=amount)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/hit")
    # Define the hit function used by this module.
    def hit(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Commit the hit against the provider-owned latest shoe and active hand.
        rnd = commit_round_transition(player_id, state, lambda current: engine.hit(current, round_id))
        # Settle only when this exact hit completed the round.
        credits = finish_if_needed(state, rnd)
        # Resolve the authoritative round after optional terminal finalization.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/stand")
    # Define the stand function used by this module.
    def stand(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Commit stand and dealer play against the authoritative latest round.
        rnd = commit_round_transition(player_id, state, lambda current: engine.stand(current, round_id))
        # Apply or replay terminal credits after the exact cards and outcomes are durable.
        credits = finish_if_needed(state, rnd)
        # Resolve the authoritative terminal round for the response.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/double")
    # Define the double function used by this module.
    def double(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Capture immutable wager dimensions while the provider owns validation.
        dimensions = {}
        # Define the pure authoritative double transition.
        def transition(current):
            # Resolve the current round rather than trusting the caller's loaded snapshot.
            current_round = engine.get_round(current, round_id)
            # Resolve the exact active hand before doubling changes its wager.
            hand = engine.active_hand(current_round)
            # Preserve the established conflict for a missing active hand.
            if not hand:
                # Reject before any wallet movement.
                raise ConflictError("No active hand")
            # Capture the original wager and stable hand identity.
            dimensions.update({"amount": float(hand["bet"]), "hand_id": hand["hand_id"]})
            # Apply the exact engine transition against the latest shoe.
            return engine.double_down(current, round_id)
        # Build the matching double debit from provider-selected dimensions.
        def double_movement(_rnd):
            # Return the one immutable supplemental wager.
            return [{"signed_amount": -dimensions["amount"], "transaction_type": "BLACKJACK_DOUBLE_DEBIT", "round_id": round_id, "action_key": f"{round_id}:{dimensions['hand_id']}:double", "request_fingerprint": f"{round_id}:{dimensions['hand_id']}:double:{dimensions['amount']}", "details": {"hand_id": dimensions["hand_id"]}}]
        # Prepare the double and its exact rollback snapshot atomically.
        rnd, marker = prepare_money_transition(player_id, state, round_id, transition, double_movement)
        # Apply or replay the supplemental wager before any terminal payout.
        settle_prepared_action(player_id, state, marker)
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, engine.get_round(state, round_id))
        # Resolve the authoritative round after settlement publication.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/split")
    # Define the split function used by this module.
    def split(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Capture immutable split dimensions under provider ownership.
        dimensions = {}
        # Define the pure authoritative split transition.
        def transition(current):
            # Resolve the latest round and active hand.
            current_round = engine.get_round(current, round_id)
            # Read the hand before the split replaces it with two hands.
            hand = engine.active_hand(current_round)
            # Preserve the established conflict for a missing active hand.
            if not hand:
                # Reject before any wallet movement.
                raise ConflictError("No active hand")
            # Capture the matching wager and stable original hand identity.
            dimensions.update({"amount": float(hand["bet"]), "hand_id": hand["hand_id"]})
            # Apply the exact split rules and card draw to the latest state.
            return engine.split(current, round_id)
        # Build the matching split debit from provider-selected dimensions.
        def split_movement(_rnd):
            # Return the one immutable additional-hand wager.
            return [{"signed_amount": -dimensions["amount"], "transaction_type": "BLACKJACK_SPLIT_DEBIT", "round_id": round_id, "action_key": f"{round_id}:{dimensions['hand_id']}:split", "request_fingerprint": f"{round_id}:{dimensions['hand_id']}:split:{dimensions['amount']}", "details": {"hand_id": dimensions["hand_id"]}}]
        # Prepare the split and its exact rollback snapshot atomically.
        rnd, marker = prepare_money_transition(player_id, state, round_id, transition, split_movement)
        # Apply or replay the supplemental wager before optional terminal payout.
        settle_prepared_action(player_id, state, marker)
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, engine.get_round(state, round_id))
        # Resolve the authoritative round after settlement publication.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/surrender")
    # Define the surrender function used by this module.
    def surrender(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Commit surrender against the latest active hand and table rules.
        rnd = commit_round_transition(player_id, state, lambda current: engine.surrender(current, round_id))
        # Apply the exact half-stake return and publish terminal state.
        credits = finish_if_needed(state, rnd)
        # Resolve the authoritative terminal round for the response.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/insurance")
    # Define the insurance function used by this module.
    def insurance(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set amount to the value needed for the next operation.
        amount = require_amount(body.get("amount"))
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Capture the provider-priced insurance result for movement construction.
        dimensions = {}
        # Validate and prepare insurance inside the latest-document boundary.
        def transition(current):
            # Resolve the latest round instead of trusting a pre-lock snapshot.
            current_round = engine.get_round(current, round_id)
            # Reject insurance after player action or dealer reveal. (BJ-020, LEDGER-015)
            if current_round.get("status") != "player_turn" or not current_round.get("dealer", {}).get("hole_card_hidden"):
                # Raise before any ledger mutation so revealed rounds cannot create risk-free returns.
                raise ConflictError("Insurance is only available before the dealer hole card is revealed")
            # Reject a second purchase against the same round.
            if current_round.get("insurance"):
                # Preserve the established validation envelope.
                raise ValidationError("Insurance has already been purchased for this round")
            # Require an exposed dealer Ace.
            if engine.card_rank(current_round["dealer"]["cards"][0]) != "A":
                # Preserve the established validation envelope.
                raise ValidationError("Insurance is only available when dealer shows an Ace")
            # Calculate the latest authoritative maximum.
            maximum = round(float(current_round["hands"][0]["bet"]) / 2, 2)
            # Reject over-insurance before any wallet effect.
            if amount > maximum:
                # Preserve the established validation envelope.
                raise ValidationError("Insurance cannot exceed half the initial wager")
            # Price dealer blackjack from the already committed cards.
            dealer_blackjack = engine.hand_total(current_round["dealer"]["cards"])["blackjack"]
            # Calculate the exact total insurance return.
            payout = amount * 3 if dealer_blackjack else 0
            # Persist the public insurance result as the action's prepared state.
            current_round["insurance"] = {"amount": amount, "dealer_blackjack": dealer_blackjack, "payout": payout}
            # Retain immutable pricing for ledger descriptors.
            dimensions.update({"payout": payout})
            # Return the prepared current round.
            return current_round
        # Build ordered insurance debit and optional settlement credit descriptors.
        def insurance_movements(_rnd):
            # Start with the required insurance stake.
            movements = [{"signed_amount": -amount, "transaction_type": "BLACKJACK_INSURANCE_DEBIT", "round_id": round_id, "action_key": f"{round_id}:insurance:wager", "request_fingerprint": f"{round_id}:insurance:{amount}", "details": {}}]
            # Append the exact three-for-one return only for dealer blackjack.
            if dimensions["payout"]:
                # Preserve the historical settlement identity and amount.
                movements.append({"signed_amount": dimensions["payout"], "transaction_type": "BLACKJACK_INSURANCE_CREDIT", "round_id": round_id, "action_key": f"{round_id}:insurance:settlement", "request_fingerprint": f"{round_id}:insurance:settlement:{dimensions['payout']}", "details": {}})
            # Return the immutable movement sequence.
            return movements
        # Prepare insurance and its exact rollback state atomically.
        rnd, marker = prepare_money_transition(player_id, state, round_id, transition, insurance_movements)
        # Commit or replay stake and optional return in their established order.
        results = settle_prepared_action(player_id, state, marker)
        # Select the exact insurance credit event when one exists.
        credit = next((item["event"] for item in results if item["movement"]["signed_amount"] > 0), None)
        # Resolve the authoritative round after marker release.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credit": credit, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/even-money")
    # Define the even_money function used by this module.
    def even_money(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_mutation_state(player_id)
        # Define the pure even-money transition against authoritative cards.
        def transition(current):
            # Resolve the latest round and opening hand.
            current_round = engine.get_round(current, round_id)
            # Read the opening hand selected by the established rule.
            hand = current_round["hands"][0]
            # Reject a repeated even-money choice.
            if current_round.get("even_money"):
                # Preserve the established validation envelope.
                raise ValidationError("Even money has already been taken")
            # Require player blackjack against dealer Ace.
            if not engine.hand_total(hand["cards"])["blackjack"] or engine.card_rank(current_round["dealer"]["cards"][0]) != "A":
                # Preserve the established validation envelope.
                raise ValidationError("Even money is only available with player blackjack against dealer Ace")
            # Price the fixed even-money total return.
            hand["status"] = "even_money"; hand["outcome"] = "even_money"; hand["payout_due"] = round(float(hand["bet"]) * 2, 2)
            # Reveal and mark the exact terminal round.
            current_round["even_money"] = True; current_round["dealer"]["hole_card_hidden"] = False; current_round["status"] = "settled_pending_credit"
            # Return the transitioned round for stable identity capture.
            return current_round
        # Publish even money against the provider-owned latest document.
        rnd = commit_round_transition(player_id, state, transition)
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        # Resolve the authoritative terminal round for the response.
        rnd = engine.get_round(state, round_id)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}
