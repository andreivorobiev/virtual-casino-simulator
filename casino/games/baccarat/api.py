# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Baccarat API actions, validation, persistence, and exactly-once settlement orchestration.
# Import deep-copy support for immutable prepared wager recovery markers.
import copy

from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.core.validation import require_amount, require_player_id
# Import the descriptor allowlist so the handler cannot drift from central router coercion.
from casino.core.game_rules import declared_fields
from casino.core import players, logger
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
from casino.games.baccarat import engine
from casino.errors import ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "baccarat"
# Bind every Baccarat movement to the shared storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "bet_id")
# Reserve one private state key for a wager mutation prepared before its ledger effect completes.
PENDING_BET_ACTION_KEY = "_baccarat_pending_bet_action"

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})


# Replace one caller snapshot with the complete authoritative provider result. (BAC-028)
def _refresh_state(state: dict, authoritative: dict) -> None:
    # Remove stale top-level fields before copying the provider-owned document.
    state.clear()
    # Preserve the caller object's identity for existing response and recovery code.
    state.update(authoritative)


# Build the immutable movement owned by one prepared Baccarat wager action. (BAC-028)
def _bet_movement(kind: str, bet: dict) -> dict:
    # Preserve the established placement debit identity and audit dimensions.
    if kind == "placement":
        # Return the canonical signed movement consumed by the settlement gateway.
        return {"signed_amount": -bet["amount"], "transaction_type": "BACCARAT_BET_PLACED", "action_key": f"{bet['bet_id']}:wager", "round_id": bet["bet_id"], "request_fingerprint": f"{bet['bet_id']}:{bet['type']}:{bet['amount']}", "details": {"bet_id": bet["bet_id"], "bet_type": bet["type"]}}
    # Preserve the established refund credit identity and audit dimensions.
    if kind == "refund":
        # Return the canonical signed movement consumed by the settlement gateway.
        return {"signed_amount": bet["amount"], "transaction_type": "BACCARAT_BET_REFUND", "action_key": f"{bet['bet_id']}:refund", "round_id": bet["bet_id"], "request_fingerprint": f"{bet['bet_id']}:refund:{bet['amount']}", "details": {"bet_id": bet["bet_id"]}}
    # Reject an internal marker whose command vocabulary is not recognized.
    raise ValueError("Baccarat prepared wager action is invalid")


# Locate one exact open bet without mutating the provider-owned list. (BAC-028)
def _find_bet(state: dict, bet_id: str) -> tuple[int, dict] | None:
    # Inspect the current open-bet order for the requested stable identity.
    for index, bet in enumerate(state.get("open_bets", [])):
        # Return the index and bet only for the exact durable identity.
        if bet.get("bet_id") == bet_id:
            # Preserve the list position for a precise pre-ledger rollback.
            return index, bet
    # Report absence without inventing a bet or response.
    return None


# Prepare one bet placement against the provider-owned latest state. (BAC-028)
def prepare_bet_placement(player_id: str, state: dict, bet_type, amount) -> tuple[dict, dict]:
    # Retain the exact generated bet and marker outside the provider callback.
    selected = {}

    # Publish the new bet and its immutable debit intent in one atomic transition.
    def prepare(current: dict) -> dict:
        # Refuse overlap with another wallet-affecting wager transition.
        if current.get(PENDING_BET_ACTION_KEY) is not None:
            # Preserve the earlier recoverable action for explicit reconciliation.
            raise ConflictError("Baccarat wager state requires settlement recovery")
        # Refuse placement while a committed coup owns the current open-bet set.
        if current.get("pending_coup") is not None:
            # Prevent a new bet from being cleared by coup finalization.
            raise ConflictError("Baccarat committed coup state requires settlement recovery")
        # Apply validation, identity allocation, and bet insertion to the latest document.
        bet = engine.add_bet(current, player_id, bet_type, amount)
        # Build one bounded marker containing only action-owned state and ledger semantics.
        marker = {"kind": "placement", "bet": copy.deepcopy(bet), "bet_index": len(current["open_bets"]) - 1, "movement": _bet_movement("placement", bet)}
        # Publish the recovery marker before the debit can occur.
        current[PENDING_BET_ACTION_KEY] = marker
        # Retain caller-owned copies for settlement and the unchanged response envelope.
        selected.update({"bet": copy.deepcopy(bet), "marker": copy.deepcopy(marker)})
        # Return the complete latest document for atomic provider publication.
        return current

    # Commit wager state and its durable intent under the shared JSON/MySQL boundary.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Refresh the route snapshot with every sibling update preserved by the provider.
    _refresh_state(state, prepared)
    # Return immutable caller copies selected inside the atomic transition.
    return selected["bet"], selected["marker"]


# Prepare one bet refund against the provider-owned latest state. (BAC-028)
def prepare_bet_refund(player_id: str, state: dict, bet_id: str) -> tuple[dict, dict]:
    # Retain the exact removed bet and marker outside the provider callback.
    selected = {}

    # Remove the bet and publish its immutable refund intent atomically.
    def prepare(current: dict) -> dict:
        # Refuse overlap with another wallet-affecting wager transition.
        if current.get(PENDING_BET_ACTION_KEY) is not None:
            # Preserve the earlier recoverable action for explicit reconciliation.
            raise ConflictError("Baccarat wager state requires settlement recovery")
        # Refuse a refund while a committed coup owns the bet.
        if current.get("pending_coup") is not None:
            # Prevent refunding a bet whose exact outcome is already committed.
            raise ConflictError("Baccarat committed coup state requires settlement recovery")
        # Resolve the bet's authoritative list position before removing it.
        located = _find_bet(current, bet_id)
        # Delegate the established public validation message when the bet is absent.
        bet = engine.remove_bet(current, bet_id, player_id)
        # Retain the pre-action position after the engine verifies exact player ownership.
        bet_index = located[0] if located is not None else 0
        # Build one bounded marker containing only action-owned state and ledger semantics.
        marker = {"kind": "refund", "bet": copy.deepcopy(bet), "bet_index": bet_index, "movement": _bet_movement("refund", bet)}
        # Publish the recovery marker before the refund can occur.
        current[PENDING_BET_ACTION_KEY] = marker
        # Retain caller-owned copies for settlement and the unchanged response envelope.
        selected.update({"bet": copy.deepcopy(bet), "marker": copy.deepcopy(marker)})
        # Return the complete latest document for atomic provider publication.
        return current

    # Commit bet removal and its durable intent under the shared provider boundary.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Refresh the route snapshot with every sibling update preserved by the provider.
    _refresh_state(state, prepared)
    # Return immutable caller copies selected inside the atomic transition.
    return selected["bet"], selected["marker"]


# Restore only one uncommitted prepared wager action while preserving sibling updates. (BAC-028)
def _rollback_bet_action(player_id: str, state: dict, marker: dict) -> None:
    # Define an exact compare-and-restore transition under provider ownership.
    def rollback(current: dict) -> dict:
        # Require the exact marker so another action is never erased.
        if current.get(PENDING_BET_ACTION_KEY) != marker:
            # Preserve divergent state and immutable recovery evidence.
            raise ConflictError("Baccarat wager state requires operator recovery")
        # Resolve the action-owned bet from the latest open-bet set.
        located = _find_bet(current, marker["bet"]["bet_id"])
        # Roll back a placement by removing only its exact prepared bet.
        if marker["kind"] == "placement":
            # Reject replacement or mutation of the action-owned bet.
            if located is None or located[1] != marker["bet"]:
                # Preserve the current document for operator-led reconciliation.
                raise ConflictError("Baccarat wager state requires operator recovery")
            # Remove only the exact prepared placement without touching sibling bets.
            current["open_bets"].pop(located[0])
        # Roll back a refund by restoring only its exact removed bet.
        elif marker["kind"] == "refund":
            # Refuse to duplicate or overwrite a bet recreated by another transition.
            if located is not None:
                # Preserve both versions instead of guessing which bet is authoritative.
                raise ConflictError("Baccarat wager state requires operator recovery")
            # Bound the original position to the current sibling-list length.
            bet_index = min(max(int(marker["bet_index"]), 0), len(current.get("open_bets", [])))
            # Reinsert the exact bet while preserving all unrelated entries.
            current.setdefault("open_bets", []).insert(bet_index, copy.deepcopy(marker["bet"]))
        # Reject malformed action kinds before releasing their recovery evidence.
        else:
            # Keep the unknown marker intact for explicit operator recovery.
            raise ConflictError("Baccarat wager state requires operator recovery")
        # Release only the exact action marker after its state is restored.
        current.pop(PENDING_BET_ACTION_KEY, None)
        # Return the complete repaired document.
        return current

    # Publish rollback atomically and refresh the caller's current state.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, rollback, engine.default_state))


# Apply or replay one prepared wager movement and publish terminal state. (BAC-028)
def settle_prepared_bet_action(player_id: str, state: dict, marker: dict) -> tuple[dict, bool]:
    # Read the immutable movement selected before any wallet side effect.
    movement = copy.deepcopy(marker["movement"])
    # Begin exact settlement so an ordinary pre-commit failure can restore state.
    try:
        # Commit or replay the bet debit/refund through the canonical gateway.
        event, replayed = SETTLEMENT.apply_once(player_id=player_id, **movement)
    # Classify the failure by immutable ledger proof before considering rollback.
    except Exception:
        # Look up the exact action without proposing another wallet mutation.
        committed = SETTLEMENT.find(player_id, movement["action_key"], round_id=movement["round_id"], transaction_type=movement["transaction_type"], request_fingerprint=movement["request_fingerprint"])
        # Roll back only when the action is definitively absent.
        if committed is None:
            # Restore the wager mutation without overwriting sibling fields.
            _rollback_bet_action(player_id, state, marker)
        # Validate any recovered proof before preserving the pending marker.
        else:
            # Bind the proof to exact game, round, amount, type, and fingerprint.
            SETTLEMENT.validate_existing(committed, transaction_type=movement["transaction_type"], round_id=movement["round_id"], signed_amount=movement["signed_amount"], request_fingerprint=movement["request_fingerprint"])
        # Re-raise the original domain or provider failure.
        raise

    # Define one exact compare-and-release transition after the movement is durable.
    def complete(current: dict) -> dict:
        # Resolve the action-owned bet from the provider's latest state.
        located = _find_bet(current, marker["bet"]["bet_id"])
        # Prove placement completion by exact bet presence.
        placement_complete = marker["kind"] == "placement" and located is not None and located[1] == marker["bet"]
        # Prove refund completion by exact bet absence.
        refund_complete = marker["kind"] == "refund" and located is None
        # Accept an overlapping finalizer only after the same state effect is terminal.
        if current.get(PENDING_BET_ACTION_KEY) is None and (placement_complete or refund_complete):
            # Return the already completed latest document unchanged.
            return current
        # Require the exact marker and action-owned bet effect before releasing it.
        if current.get(PENDING_BET_ACTION_KEY) != marker or not (placement_complete or refund_complete):
            # Preserve divergent state and immutable ledger proof for operator recovery.
            raise ConflictError("Baccarat wager state requires operator recovery")
        # Release only this action's private recovery marker.
        current.pop(PENDING_BET_ACTION_KEY, None)
        # Return the complete latest document for provider publication.
        return current

    # Publish completion atomically and refresh the caller's authoritative snapshot.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, complete, engine.default_state))
    # Return settlement evidence for focused exactly-once assertions.
    return event, replayed


# Resume one wager action that was prepared before an interruption. (BAC-028)
def resume_prepared_bet_action(player_id: str, state: dict) -> tuple[dict, bool] | None:
    # Read the private marker from the already loaded player document.
    marker = state.get(PENDING_BET_ACTION_KEY)
    # Keep ordinary requests cheap when no wager action needs recovery.
    if marker is None:
        # Report that no settlement evidence was produced.
        return None
    # Reconcile the exact immutable movement without generating a new bet identity.
    return settle_prepared_bet_action(player_id, state, copy.deepcopy(marker))


# Apply descriptor-owned settings to the provider-owned latest document. (BAC-028)
def update_settings(player_id: str, state: dict, body: dict, fields) -> None:
    # Define one latest-document settings transition that cannot cross active wager state.
    def apply(current: dict) -> dict:
        # Refuse settings changes while any open, prepared, or committed wager is active.
        if current.get("open_bets") or current.get(PENDING_BET_ACTION_KEY) is not None or current.get("pending_coup") is not None:
            # Preserve exact current rules and wager recovery evidence.
            raise ConflictError("Deal or clear open baccarat bets before changing settings")
        # Resolve the descriptor-owned default rules only inside the provider boundary.
        rules = current.setdefault("rules", engine.default_state()["rules"])
        # Copy only centrally coerced descriptor fields so this handler owns no parallel rule schema.
        for field in fields:
            # Preserve omitted rules while applying each validated caller update.
            if field in body:
                # Store the canonical router value for subsequent engine consumption.
                rules[field] = body[field]
        # Return the complete latest document for atomic provider publication.
        return current

    # Publish settings atomically and refresh the caller's current state.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, apply, engine.default_state))

# Commit one pending coup and its consumed shoe against the latest provider-owned document. (BAC-027)
def commit_pending_coup(player_id: str, state: dict) -> tuple[dict, bool]:
    # Capture the exact coup selected inside the atomic state transition.
    selected = {}
    # Define a latest-document transition that never deals behind an existing commitment.
    def commit(current: dict) -> dict:
        # Refuse a coup while a prepared wager debit or refund still requires settlement recovery.
        if current.get(PENDING_BET_ACTION_KEY) is not None:
            # Preserve the wager marker so deal recovery cannot consume or clear its exact bet.
            raise ConflictError("Baccarat wager state requires settlement recovery")
        # Reuse cards, bets, and shoe position already committed by a racing or interrupted request.
        coup = current.get("pending_coup")
        # Record whether this caller owns the fresh commitment or observed another request's winner.
        created = coup is None
        # Deal only while the provider owns the latest document and no coup is pending.
        if coup is None:
            # Deal and price every latest open bet while consuming the authoritative shoe once.
            coup = engine.commit_coup(current)
            # Publish the commitment before any settlement side effect can begin.
            current["pending_coup"] = coup
        # Retain the exact committed coup for the current response path.
        selected["coup"] = coup
        # Retain ownership so a stale concurrent request preserves the established conflict envelope.
        selected["created"] = created
        # Return the complete latest document for provider-owned publication.
        return current
    # Apply the commitment through the JSON/MySQL atomic document boundary.
    committed = update_player_game_state(GAME_ID, player_id, commit, engine.default_state)
    # Replace the caller's stale top-level view with the authoritative committed state.
    state.clear()
    # Copy every provider-published field into the existing caller-owned object.
    state.update(committed)
    # Return the exact coup and fresh-commit ownership selected under the provider boundary.
    return selected["coup"], selected["created"]

# Finalize one committed coup against the latest provider-owned state document. (BAC-027)
def finalize_committed_coup_state(player_id: str, state: dict, coup: dict) -> None:
    # Define an idempotent terminal transition for the complete committed coup.
    def finalize(current: dict) -> dict:
        # Read the commitment currently owned by the latest document.
        pending = current.get("pending_coup")
        # Finalize only when the expected coup is still pending.
        if pending is not None:
            # Refuse to clear or publish a different racing commitment.
            if pending != coup:
                # Preserve both sources for operator-led conflict recovery.
                raise ConflictError("Baccarat committed coup state requires operator recovery")
            # Apply the established terminal history and bet mutations once.
            engine.finalize_coup(current, pending)
        # Accept a replay only when the complete coup is already terminal.
        elif not any(item == coup for item in current.get("last_coups", []) if isinstance(item, dict)):
            # Reject missing, aliased, or unrelated state instead of inventing finalization.
            raise ConflictError("Baccarat committed coup state requires operator recovery")
        # Return the complete latest document for provider-owned publication.
        return current
    # Apply terminal publication through the JSON/MySQL atomic document boundary.
    finalized = update_player_game_state(GAME_ID, player_id, finalize, engine.default_state)
    # Remove stale top-level entries from the caller's pre-settlement snapshot.
    state.clear()
    # Refresh the caller so response state includes every preserved sibling update.
    state.update(finalized)

# Settle one committed coup exactly once, finalize its terminal state, and persist the finalized round. (issues #430, #555)
def settle_committed_coup(player_id: str, state: dict, coup: dict):
    # Collect per-bet settlement evidence for the deal response.
    settlements=[]
    # Settle every bet snapshotted when the coup's cards were committed.
    for b in coup["bets"]:
        # Price the bet against the committed coup under the current table rules.
        res = engine.settle_bet(b, coup, state.get("rules",{}))
        # Set credit to the value needed for the next operation.
        credit = None
        # Track storage replay evidence so a raced or recovered settlement never repeats side effects. (issue #403)
        replayed = False
        if res["credit"] > 0:
            # Commit or replay the payout under the durable placement-time bet action identity. (issue #403)
            credit, replayed = SETTLEMENT.apply_once(player_id=b["player_id"], signed_amount=res["credit"], transaction_type="BACCARAT_SETTLEMENT_CREDIT", action_key=f"{b['bet_id']}:settlement", round_id=coup["round_id"], request_fingerprint=f"{b['bet_id']}:{res['outcome']}:{res['credit']}", details={"bet_id": b["bet_id"], "outcome": res["outcome"]})
        # Append history only for the committing call so raced or recovered retries cannot duplicate rows. (issue #403)
        if not replayed:
            # Set bal to the value needed for the next operation.
            bal = players.get_player(b["player_id"])["balance"]
            append_history(GAME_ID, coup["round_id"], b["player_id"], b["type"], b["label"], b["amount"], res["outcome"], res["credit"], bal, coup)
        settlements.append({"bet": b, "settlement": res, "ledger": credit})
    # Publish the terminal coup against the latest state and release the exact commitment once.
    finalize_committed_coup_state(player_id, state, coup)
    # Return the settlement evidence for the deal response.
    return settlements

# Complete any committed-but-unfinalized coup before a new mutation, so an interrupted settlement is replayed rather than wiped or redealt. (issue #555)
def resume_pending_coup(player_id: str, state: dict):
    # Read the coup committed before the interruption, when one exists.
    pending=state.get("pending_coup")
    # Replay the committed settlement so its bets settle exactly once against the original cards.
    if pending: settle_committed_coup(player_id, state, pending)

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Publish state without private shoe or recovery markers so the response shape stays contract-stable. (BAC-027, BAC-028)
    public = {k:v for k,v in state.items() if k not in ("shoe", "pending_coup", PENDING_BET_ACTION_KEY)}
    # Set public["shoe_count"] to the value needed for the next operation.
    public["shoe_count"] = len(state.get("shoe",[]))
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    return {"game": GAME_ID, "state": public, "player": players.get_player(player_id), "players": visible_players}


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/baccarat/state")
    # Define the state function used by this module.
    def state(body, query): return payload(request_player_id(body, query))

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/baccarat/settings")
    # Define the settings function used by this module.
    def settings(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Apply descriptor-owned fields against the provider-owned latest document. (BAC-028, SEC-014)
        update_settings(player_id, state, body, declared_fields(GAME_ID))
        # Return the established contract envelope with the refreshed authoritative state.
        return payload(player_id, state)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/baccarat/bets")
    # Define the bet function used by this module.
    def bet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query); amount = require_amount(body.get("amount"))
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Finish an interrupted wager debit or refund before allocating another bet identity. (BAC-028)
        resume_prepared_bet_action(player_id, state)
        # Complete any interrupted settlement first so finalizing it can never wipe this new bet. (issue #555)
        resume_pending_coup(player_id, state)
        # Prepare the bet and immutable debit intent under the provider document lock. (BAC-028)
        item, marker = prepare_bet_placement(player_id, state, body.get("bet_type"), amount)
        # Settle the exact prepared debit and release its recovery marker. (BAC-028)
        settle_prepared_bet_action(player_id, state, marker)
        return {"bet": item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/baccarat/bets/(?P<bet_id>[^/]+)")
    # Define the clear function used by this module.
    def clear(body, query, bet_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Finish an interrupted wager debit or refund before selecting a bet to clear. (BAC-028)
        resume_prepared_bet_action(player_id, state)
        # Complete any interrupted settlement first so a settled bet can never be refunded afterwards. (issue #555)
        resume_pending_coup(player_id, state)
        # Prepare exact bet removal and its immutable refund intent atomically. (BAC-028)
        item, marker = prepare_bet_refund(player_id, state, bet_id)
        # Settle the exact prepared refund and release its recovery marker. (BAC-028)
        settle_prepared_bet_action(player_id, state, marker)
        return {"cleared": item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/baccarat/deal")
    # Define the deal function used by this module.
    def deal(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Finish any prepared bet debit or refund before dealing from the open-bet set. (BAC-028)
        resume_prepared_bet_action(player_id, state)
        # Resume the coup committed by an interrupted request instead of dealing fresh cards. (issue #555)
        coup = state.get("pending_coup")
        # Branch when no settlement is pending so the dealt cards and consumed shoe commit durably before any credit.
        if not coup:
            # Commit fresh cards and the consumed shoe against provider-owned latest state.
            coup, created = commit_pending_coup(player_id, state)
            # Preserve the established concurrent-request conflict after adopting the winning exact commitment.
            if not created:
                # Let a later recovery request resume the committed coup without dealing or settling twice here.
                raise ConflictError("Baccarat coup was committed by another request")
        # Settle every committed bet exactly once and finalize the round.
        settlements = settle_committed_coup(player_id, state, coup)
        # Set logger.info("baccarat_coup_dealt", round_id to the value needed for the next operation.
        logger.info("baccarat_coup_dealt", round_id=coup["round_id"], winner=coup["winner"], bet_count=len(coup["bets"]))
        return {"coup": coup, "settlements": settlements, "bot_bets": [], **payload(player_id, state)}
