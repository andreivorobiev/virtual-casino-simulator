# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Keno API actions, ticket persistence, draw execution, and settlement orchestration.
# Import deep-copy support for immutable prepared ticket-action recovery markers.
import copy

from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.core.validation import require_amount, require_player_id
from casino.core import players
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
# Import the fail-closed conflict boundary for divergent committed draw state.
from casino.errors import ConflictError
from casino.games.keno import engine

# Set GAME_ID to the value needed for the next operation.
GAME_ID="keno"
# Bind every Keno movement to the shared storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "ticket_id")
# Reserve one private state key for a ticket mutation prepared before its ledger effect completes.
PENDING_TICKET_ACTION_KEY = "_keno_pending_ticket_action"

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Publish the state without transient recovery commitments so the response shape stays contract-stable. (issues #555, #767)
    public = {k: v for k, v in state.items() if k not in {"pending_draw", PENDING_TICKET_ACTION_KEY}}
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    return {"game":GAME_ID, "state":public, "player": players.get_player(player_id), "players": visible_players, "paytable": engine.PAYTABLE}


# Replace one caller snapshot with the complete authoritative provider result. (KENO-029)
def _refresh_state(state: dict, authoritative: dict) -> None:
    # Remove stale top-level fields before copying the provider-owned document.
    state.clear()
    # Preserve the caller object's identity for existing response and recovery code.
    state.update(authoritative)


# Build the immutable movement owned by one prepared ticket action. (KENO-029)
def _ticket_movement(kind: str, ticket: dict) -> dict:
    # Select purchase debit or refund credit semantics without accepting another action kind.
    if kind == "purchase":
        # Return the existing purchase ledger identity and audit dimensions.
        return {"signed_amount": -ticket["amount"], "transaction_type": "KENO_TICKET_PURCHASED", "action_key": f"{ticket['ticket_id']}:wager", "round_id": ticket["ticket_id"], "request_fingerprint": f"{ticket['ticket_id']}:{ticket['spots']}:{ticket['amount']}", "details": {"ticket_id": ticket["ticket_id"], "spots": ticket["spots"]}}
    # Accept only the one remaining prepared ticket action.
    if kind == "refund":
        # Return the established durable refund identity and audit dimensions.
        return {"signed_amount": ticket["amount"], "transaction_type": "KENO_TICKET_REFUND", "action_key": f"{ticket['ticket_id']}:refund", "round_id": ticket["ticket_id"], "request_fingerprint": f"{ticket['ticket_id']}:refund:{ticket['amount']}", "details": {"ticket_id": ticket["ticket_id"]}}
    # Reject an internal marker whose command vocabulary is not recognized.
    raise ValueError("Keno prepared ticket action is invalid")


# Locate one exact ticket without mutating the provider-owned list. (KENO-029)
def _find_ticket(state: dict, ticket_id: str) -> tuple[int, dict] | None:
    # Inspect the current open-ticket order for the requested stable identity.
    for index, ticket in enumerate(state.setdefault("open_tickets", [])):
        # Return the index and ticket only for the exact durable identity.
        if ticket.get("ticket_id") == ticket_id:
            # Preserve the list position for a precise pre-ledger rollback.
            return index, ticket
    # Report absence without inventing a ticket or response.
    return None


# Prepare one ticket purchase against the provider-owned latest state. (KENO-029)
def prepare_ticket_purchase(player_id: str, state: dict, spots, amount) -> tuple[dict, dict]:
    # Retain the exact generated ticket and marker outside the provider callback.
    selected = {}

    # Publish the new ticket and its immutable debit intent in one atomic state transition.
    def prepare(current: dict) -> dict:
        # Refuse overlap with another wallet-affecting ticket transition.
        if current.get(PENDING_TICKET_ACTION_KEY) is not None:
            # Preserve the earlier recoverable action for explicit reconciliation.
            raise ConflictError("Keno ticket state requires settlement recovery")
        # Refuse a purchase while a draw owns the current open-ticket set.
        if current.get("pending_draw") is not None:
            # Prevent a newly purchased ticket from being cleared by draw finalization.
            raise ConflictError("Keno committed draw state requires settlement recovery")
        # Apply validation, identity allocation, and ticket insertion to the latest document.
        ticket = engine.add_ticket(current, player_id, spots, amount)
        # Build one bounded marker containing only action-owned state and ledger semantics.
        marker = {"kind": "purchase", "ticket": copy.deepcopy(ticket), "ticket_index": len(current["open_tickets"]) - 1, "movement": _ticket_movement("purchase", ticket)}
        # Publish the recovery marker before the debit can occur.
        current[PENDING_TICKET_ACTION_KEY] = marker
        # Retain caller-owned copies for settlement and the unchanged response envelope.
        selected.update({"ticket": copy.deepcopy(ticket), "marker": copy.deepcopy(marker)})
        # Return the complete latest document for atomic provider publication.
        return current

    # Commit ticket state and its durable intent under the shared JSON/MySQL boundary.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Refresh the route snapshot with every sibling update preserved by the provider.
    _refresh_state(state, prepared)
    # Return immutable caller copies selected inside the atomic transition.
    return selected["ticket"], selected["marker"]


# Prepare one ticket refund against the provider-owned latest state. (KENO-029)
def prepare_ticket_refund(player_id: str, state: dict, ticket_id: str) -> tuple[dict, dict]:
    # Retain the exact removed ticket and marker outside the provider callback.
    selected = {}

    # Remove the ticket and publish its immutable refund intent atomically.
    def prepare(current: dict) -> dict:
        # Refuse overlap with another wallet-affecting ticket transition.
        if current.get(PENDING_TICKET_ACTION_KEY) is not None:
            # Preserve the earlier recoverable action for explicit reconciliation.
            raise ConflictError("Keno ticket state requires settlement recovery")
        # Refuse a refund while a committed draw owns the ticket.
        if current.get("pending_draw") is not None:
            # Prevent refunding a ticket whose exact result is already committed.
            raise ConflictError("Keno committed draw state requires settlement recovery")
        # Resolve the ticket's authoritative list position before removing it.
        located = _find_ticket(current, ticket_id)
        # Delegate the established public validation message when the ticket is absent.
        ticket = engine.remove_ticket(current, ticket_id, player_id)
        # Retain the pre-action position after the engine verifies exact player ownership.
        ticket_index = located[0] if located is not None else 0
        # Build one bounded marker containing only action-owned state and ledger semantics.
        marker = {"kind": "refund", "ticket": copy.deepcopy(ticket), "ticket_index": ticket_index, "movement": _ticket_movement("refund", ticket)}
        # Publish the recovery marker before the refund can occur.
        current[PENDING_TICKET_ACTION_KEY] = marker
        # Retain caller-owned copies for settlement and the unchanged response envelope.
        selected.update({"ticket": copy.deepcopy(ticket), "marker": copy.deepcopy(marker)})
        # Return the complete latest document for atomic provider publication.
        return current

    # Commit ticket removal and its durable intent under the shared provider boundary.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Refresh the route snapshot with every sibling update preserved by the provider.
    _refresh_state(state, prepared)
    # Return immutable caller copies selected inside the atomic transition.
    return selected["ticket"], selected["marker"]


# Restore only one uncommitted prepared ticket action while preserving sibling updates. (KENO-029)
def _rollback_ticket_action(player_id: str, state: dict, marker: dict) -> None:
    # Define an exact compare-and-restore transition under provider ownership.
    def rollback(current: dict) -> dict:
        # Require the exact marker so another action is never erased.
        if current.get(PENDING_TICKET_ACTION_KEY) != marker:
            # Preserve divergent state and immutable recovery evidence.
            raise ConflictError("Keno ticket state requires operator recovery")
        # Resolve the action-owned ticket from the latest open-ticket set.
        located = _find_ticket(current, marker["ticket"]["ticket_id"])
        # Roll back a purchase by removing only its exact prepared ticket.
        if marker["kind"] == "purchase":
            # Reject replacement or mutation of the action-owned ticket.
            if located is None or located[1] != marker["ticket"]:
                # Preserve the current document for operator-led reconciliation.
                raise ConflictError("Keno ticket state requires operator recovery")
            # Remove only the exact prepared purchase without touching sibling tickets.
            current["open_tickets"].pop(located[0])
        # Roll back a refund by restoring only its exact removed ticket.
        elif marker["kind"] == "refund":
            # Refuse to duplicate or overwrite a ticket recreated by another transition.
            if located is not None:
                # Preserve both versions instead of guessing which ticket is authoritative.
                raise ConflictError("Keno ticket state requires operator recovery")
            # Bound the original position to the current sibling-list length.
            ticket_index = min(max(int(marker["ticket_index"]), 0), len(current["open_tickets"]))
            # Reinsert the exact ticket while preserving all unrelated entries.
            current["open_tickets"].insert(ticket_index, copy.deepcopy(marker["ticket"]))
        # Reject malformed action kinds before releasing their recovery evidence.
        else:
            # Keep the unknown marker intact for explicit operator recovery.
            raise ConflictError("Keno ticket state requires operator recovery")
        # Release only the exact action marker after its state is restored.
        current.pop(PENDING_TICKET_ACTION_KEY, None)
        # Return the complete repaired document.
        return current

    # Publish rollback atomically and refresh the caller's current state.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, rollback, engine.default_state))


# Apply or replay one prepared ticket movement and publish terminal state. (KENO-029)
def settle_prepared_ticket_action(player_id: str, state: dict, marker: dict) -> tuple[dict, bool]:
    # Read the immutable movement selected before any wallet side effect.
    movement = copy.deepcopy(marker["movement"])
    # Begin exact settlement so an ordinary pre-commit failure can restore state.
    try:
        # Commit or replay the ticket debit/refund through the canonical gateway.
        event, replayed = SETTLEMENT.apply_once(player_id=player_id, **movement)
    # Classify the failure by immutable ledger proof before considering rollback.
    except Exception:
        # Look up the exact action without proposing another wallet mutation.
        committed = SETTLEMENT.find(player_id, movement["action_key"], round_id=movement["round_id"], transaction_type=movement["transaction_type"], request_fingerprint=movement["request_fingerprint"])
        # Roll back only when the action is definitively absent.
        if committed is None:
            # Restore the ticket mutation without overwriting sibling fields.
            _rollback_ticket_action(player_id, state, marker)
        # Validate any recovered proof before preserving the pending marker.
        else:
            # Bind the proof to exact game, round, amount, type, and fingerprint.
            SETTLEMENT.validate_existing(committed, transaction_type=movement["transaction_type"], round_id=movement["round_id"], signed_amount=movement["signed_amount"], request_fingerprint=movement["request_fingerprint"])
        # Re-raise the original domain or provider failure.
        raise

    # Define one exact compare-and-release transition after the movement is durable.
    def complete(current: dict) -> dict:
        # Resolve the action-owned ticket from the provider's latest state.
        located = _find_ticket(current, marker["ticket"]["ticket_id"])
        # Prove purchase completion by exact ticket presence.
        purchase_complete = marker["kind"] == "purchase" and located is not None and located[1] == marker["ticket"]
        # Prove refund completion by exact ticket absence.
        refund_complete = marker["kind"] == "refund" and located is None
        # Accept an overlapping finalizer only after the same state effect is terminal.
        if current.get(PENDING_TICKET_ACTION_KEY) is None and (purchase_complete or refund_complete):
            # Return the already completed latest document unchanged.
            return current
        # Require the exact marker and action-owned ticket effect before releasing it.
        if current.get(PENDING_TICKET_ACTION_KEY) != marker or not (purchase_complete or refund_complete):
            # Preserve divergent state and immutable ledger proof for operator recovery.
            raise ConflictError("Keno ticket state requires operator recovery")
        # Release only this action's private recovery marker.
        current.pop(PENDING_TICKET_ACTION_KEY, None)
        # Return the complete latest document for provider publication.
        return current

    # Publish completion atomically and refresh the caller's authoritative snapshot.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, complete, engine.default_state))
    # Return settlement evidence for focused exactly-once assertions.
    return event, replayed


# Resume one ticket action that was prepared before an interruption. (KENO-029)
def resume_prepared_ticket_action(player_id: str, state: dict) -> tuple[dict, bool] | None:
    # Read the private marker from the already loaded player document.
    marker = state.get(PENDING_TICKET_ACTION_KEY)
    # Keep ordinary requests cheap when no ticket action needs recovery.
    if marker is None:
        # Report that no settlement evidence was produced.
        return None
    # Reconcile the exact immutable movement without generating a new ticket identity.
    return settle_prepared_ticket_action(player_id, state, copy.deepcopy(marker))

# Commit one pending draw against the latest provider-owned state document. (KENO-028)
def commit_pending_draw(player_id: str, state: dict) -> dict:
    # Capture the exact draw selected inside the atomic state transition.
    selected = {}
    # Define a latest-document transition that never samples behind an existing commitment.
    def commit(current: dict) -> dict:
        # Refuse to draw while a ticket debit or refund still requires reconciliation.
        if current.get(PENDING_TICKET_ACTION_KEY) is not None:
            # Keep the recoverable ticket action isolated from draw ownership.
            raise ConflictError("Keno ticket state requires settlement recovery")
        # Reuse entropy already committed by a racing or interrupted request.
        draw = current.get("pending_draw")
        # Sample only while the provider owns the latest document and no draw is pending.
        if draw is None:
            # Price every latest open ticket against one fresh draw.
            draw = engine.commit_draw(current)
            # Publish the commitment before any settlement side effect can begin.
            current["pending_draw"] = draw
        # Retain the exact committed draw for the current response path.
        selected["draw"] = draw
        # Return the complete latest document for provider-owned publication.
        return current
    # Apply the commitment through the JSON/MySQL atomic document boundary.
    committed = update_player_game_state(GAME_ID, player_id, commit, engine.default_state)
    # Replace the caller's stale top-level view with the authoritative committed state.
    state.clear()
    # Copy every provider-published field into the existing caller-owned object.
    state.update(committed)
    # Return the exact draw selected under the provider boundary.
    return selected["draw"]

# Finalize one committed draw against the latest provider-owned state document. (KENO-028)
def finalize_committed_draw_state(player_id: str, state: dict, draw: dict) -> None:
    # Define an idempotent terminal transition for the exact committed round.
    def finalize(current: dict) -> dict:
        # Read the commitment currently owned by the latest document.
        pending = current.get("pending_draw")
        # Finalize only when the expected draw is still pending.
        if pending is not None:
            # Refuse to clear or publish a different racing commitment.
            if pending != draw:
                # Preserve both sources for operator-led conflict recovery.
                raise ConflictError("Keno committed draw state requires operator recovery")
            # Apply the established terminal history and ticket mutations once.
            engine.finalize_draw(current, pending)
        # Accept a replay only when the same round is already terminal.
        elif not any(item == draw for item in current.get("last_draws", []) if isinstance(item, dict)):
            # Reject missing or unrelated state instead of inventing finalization.
            raise ConflictError("Keno committed draw state requires operator recovery")
        # Return the complete latest document for provider-owned publication.
        return current
    # Apply terminal publication through the JSON/MySQL atomic document boundary.
    finalized = update_player_game_state(GAME_ID, player_id, finalize, engine.default_state)
    # Remove stale top-level entries from the caller's pre-settlement snapshot.
    state.clear()
    # Refresh the caller so response state includes every preserved sibling update.
    state.update(finalized)

# Settle one committed draw exactly once, finalize its terminal state, and persist the finalized round. (issues #430, #555)
def settle_committed_draw(player_id: str, state: dict, d: dict):
    # Collect per-ticket settlement evidence for the draw response.
    settlements=[]
    # Settle every result priced when the draw's entropy was committed.
    for r in d["results"]:
        # Track the replay marker alongside the credit event for this durable ticket. (issue #403)
        t=r["ticket"]; credit=None; replayed=False
        # Credit each durable ticket exactly once, keeping the volatile catch count out of the fingerprinted details so a racing draw fails closed on ConflictError instead of double-paying. (issue #403)
        if r["payout"]>0: credit,replayed=SETTLEMENT.apply_once(player_id=t["player_id"], signed_amount=r["payout"], transaction_type="KENO_PAYOUT_CREDIT", action_key=f"{t['ticket_id']}:payout", round_id=d["round_id"], request_fingerprint=f"{t['ticket_id']}:{d['round_id']}:{r['payout']}", details={"ticket_id":t["ticket_id"]})
        # Set bal to the value needed for the next operation.
        bal=players.get_player(t["player_id"])["balance"]
        # Branch so history rows append only for first-time payouts and replays cannot duplicate them. (issue #403)
        if not replayed: append_history(GAME_ID,d["round_id"],t["player_id"],"ticket",f"{len(t['spots'])} spots",t["amount"],"win" if r["payout"] else "loss",r["payout"],bal,{"drawn":d["drawn"],"spots":t["spots"],"catches":r["catches"]})
        settlements.append({"result":r,"ledger":credit,"replayed":replayed})
    # Publish the terminal draw against the latest state and release the exact commitment once.
    finalize_committed_draw_state(player_id, state, d)
    # Return the settlement evidence for the draw response.
    return settlements

# Complete any committed-but-unfinalized draw before a new mutation, so an interrupted settlement is replayed rather than wiped or redrawn. (issue #555)
def resume_pending_draw(player_id: str, state: dict):
    # Read the draw committed before the interruption, when one exists.
    pending=state.get("pending_draw")
    # Replay the committed settlement so its tickets settle exactly once against the original entropy.
    if pending: settle_committed_draw(player_id, state, pending)

# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/keno/state")
    # Define the state function used by this module.
    def state(body, query): return payload(request_player_id(body, query))

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/keno/tickets")
    # Define the ticket function used by this module.
    def ticket(body, query):
        # Set player_id to the value needed for the next operation.
        player_id=request_player_id(body, query); amount=require_amount(body.get("amount"))
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Complete an interrupted ticket debit/refund before accepting another action.
        resume_prepared_ticket_action(player_id, state)
        # Complete any interrupted settlement first so finalizing it can never wipe this new ticket. (issue #555)
        resume_pending_draw(player_id, state)
        # Atomically publish the ticket and its exact debit intent before wallet mutation.
        item, marker=prepare_ticket_purchase(player_id, state, body.get("spots",[]), amount)
        # Apply or recover the immutable debit, then release the prepared marker.
        settle_prepared_ticket_action(player_id, state, marker)
        # Return the unchanged v1 purchase envelope from authoritative state.
        return {"ticket": item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/keno/tickets/(?P<ticket_id>[^/]+)")
    # Define the clear function used by this module.
    def clear(body, query, ticket_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Complete an interrupted ticket debit/refund before accepting another action.
        resume_prepared_ticket_action(player_id, state)
        # Complete any interrupted settlement first so a settled ticket can never be refunded afterwards. (issue #555)
        resume_pending_draw(player_id, state)
        # Atomically remove the ticket and publish its exact refund intent.
        item, marker=prepare_ticket_refund(player_id, state, ticket_id)
        # Apply or recover the immutable refund, then release the prepared marker.
        settle_prepared_ticket_action(player_id, state, marker)
        # Return the unchanged v1 clear envelope from authoritative state.
        return {"cleared":item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/keno/draw")
    # Define the draw function used by this module.
    def draw(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Complete any prepared ticket debit/refund before drawing its ticket set.
        resume_prepared_ticket_action(player_id, state)
        # Resume the draw committed by an interrupted request instead of sampling fresh entropy. (issue #555)
        d=state.get("pending_draw")
        # Branch when no settlement is pending so fresh entropy commits durably before any credit.
        if not d:
            # Commit fresh entropy against the provider-owned latest state before settlement.
            d=commit_pending_draw(player_id, state)
        # Settle every committed result exactly once and finalize the round.
        settlements=settle_committed_draw(player_id, state, d)
        # Return the same draw envelope this round has always published.
        return {"draw":d,"settlements":settlements,"bot_tickets":[], **payload(player_id, state)}
