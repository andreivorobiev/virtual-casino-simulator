# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Keno API actions, ticket persistence, draw execution, and settlement orchestration.
from casino.core.state_store import load_player_game_state, save_player_game_state
from casino.core.validation import require_amount, require_player_id
from casino.core import players
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
from casino.games.keno import engine

# Set GAME_ID to the value needed for the next operation.
GAME_ID="keno"
# Bind every Keno movement to the shared storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "ticket_id")

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Publish the state without the transient settlement commitment so the response shape stays contract-stable. (issue #555)
    public = {k: v for k, v in state.items() if k != "pending_draw"}
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    return {"game":GAME_ID, "state":public, "player": players.get_player(player_id), "players": visible_players, "paytable": engine.PAYTABLE}

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
    # Apply the terminal draw mutations exactly once and release the settlement commitment.
    engine.finalize_draw(state, d)
    # Persist the finalized round so the committed settlement can never run twice.
    save_player_game_state(GAME_ID, player_id, state)
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
        # Complete any interrupted settlement first so finalizing it can never wipe this new ticket. (issue #555)
        resume_pending_draw(player_id, state)
        # Set item to the value needed for the next operation.
        item=engine.add_ticket(state, player_id, body.get("spots",[]), amount)
        # Debit the purchase under its storage-atomic placement-time action identity so a recovered replay cannot double-charge. (issue #555)
        SETTLEMENT.apply_once(player_id=player_id, signed_amount=-amount, transaction_type="KENO_TICKET_PURCHASED", action_key=f"{item['ticket_id']}:wager", round_id=item["ticket_id"], request_fingerprint=f"{item['ticket_id']}:{item['spots']}:{amount}", details={"ticket_id": item["ticket_id"], "spots": item["spots"]})
        save_player_game_state(GAME_ID, player_id, state); return {"ticket": item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/keno/tickets/(?P<ticket_id>[^/]+)")
    # Define the clear function used by this module.
    def clear(body, query, ticket_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Complete any interrupted settlement first so a settled ticket can never be refunded afterwards. (issue #555)
        resume_pending_draw(player_id, state)
        # Set item to the value needed for the next operation.
        item=engine.remove_ticket(state,ticket_id,player_id)
        # Refund the durable ticket exactly once so a replayed clear returns the original event instead of minting a second refund. (issue #555)
        SETTLEMENT.apply_once(player_id=player_id, signed_amount=item["amount"], transaction_type="KENO_TICKET_REFUND", action_key=f"{ticket_id}:refund", round_id=ticket_id, request_fingerprint=f"{ticket_id}:refund:{item['amount']}", details={"ticket_id":ticket_id})
        save_player_game_state(GAME_ID, player_id, state); return {"cleared":item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/keno/draw")
    # Define the draw function used by this module.
    def draw(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Resume the draw committed by an interrupted request instead of sampling fresh entropy. (issue #555)
        d=state.get("pending_draw")
        # Branch when no settlement is pending so fresh entropy commits durably before any credit.
        if not d:
            # Sample and price the round without mutating terminal state.
            d=engine.commit_draw(state)
            # Persist the committed entropy atomically before the first settlement side effect.
            state["pending_draw"]=d; save_player_game_state(GAME_ID, player_id, state)
        # Settle every committed result exactly once and finalize the round.
        settlements=settle_committed_draw(player_id, state, d)
        # Return the same draw envelope this round has always published.
        return {"draw":d,"settlements":settlements,"bot_tickets":[], **payload(player_id, state)}
