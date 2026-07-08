# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_game_state, save_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import require_amount, require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import ledger, players
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import required dependency so this module can use its public functions or constants.
from casino.games.keno import engine

# Set GAME_ID to the value needed for the next operation.
GAME_ID="keno"

# Define the payload function used by this module.
def payload(state=None):
    # Set state to the value needed for the next operation.
    state = state or load_game_state(GAME_ID, engine.default_state)
    # Return the computed value to the caller.
    return {"game":GAME_ID, "state":state, "player": players.get_player("human"), "players": players.list_players(), "paytable": engine.PAYTABLE}


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/keno/state")
    # Define the state function used by this module.
    def state(body, query): return payload()

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/keno/tickets")
    # Define the ticket function used by this module.
    def ticket(body, query):
        # Set player_id to the value needed for the next operation.
        player_id=require_player_id(body); amount=require_amount(body.get("amount"))
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Set item to the value needed for the next operation.
        item=engine.add_ticket(state, player_id, body.get("spots",[]), amount)
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(player_id, amount, "KENO_TICKET_PURCHASED", GAME_ID, None, {"ticket_id": item["ticket_id"], "spots": item["spots"]})
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID, state); return {"ticket": item, **payload(state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/keno/tickets/(?P<ticket_id>[^/]+)")
    # Define the clear function used by this module.
    def clear(body, query, ticket_id):
        # Set player_id to the value needed for the next operation.
        player_id = body.get("player_id") or query.get("player_id") or "human"
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Set item to the value needed for the next operation.
        item=engine.remove_ticket(state,ticket_id,player_id)
        # Execute this statement as part of the module's documented control flow.
        ledger.credit(player_id,item["amount"],"KENO_TICKET_REFUND",GAME_ID,None,{"ticket_id":ticket_id})
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID,state); return {"cleared":item, **payload(state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/keno/draw")
    # Define the draw function used by this module.
    def draw(body, query):
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Set d to the value needed for the next operation.
        d=engine.draw(state); settlements=[]
        # Iterate through the collection to process each item.
        for r in d["results"]:
            # Set t to the value needed for the next operation.
            t=r["ticket"]; credit=None
            # Branch when the following condition is true.
            if r["payout"]>0: credit=ledger.credit(t["player_id"],r["payout"],"KENO_PAYOUT_CREDIT",GAME_ID,d["round_id"],{"ticket_id":t["ticket_id"],"catch_count":r["catch_count"]})
            # Set bal to the value needed for the next operation.
            bal=players.get_player(t["player_id"])["balance"]
            # Execute this statement as part of the module's documented control flow.
            append_history(GAME_ID,d["round_id"],t["player_id"],"ticket",f"{len(t['spots'])} spots",t["amount"],"win" if r["payout"] else "loss",r["payout"],bal,{"drawn":d["drawn"],"spots":t["spots"],"catches":r["catches"]})
            # Execute this statement as part of the module's documented control flow.
            settlements.append({"result":r,"ledger":credit})
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID,state); return {"draw":d,"settlements":settlements,"bot_tickets":[], **payload(state)}
