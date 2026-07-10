# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import require_amount, require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import ledger, players, logger
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import required dependency so this module can use its public functions or constants.
from casino.games.baccarat import engine
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "baccarat"

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Set public to the value needed for the next operation.
    public = {k:v for k,v in state.items() if k != "shoe"}
    # Set public["shoe_count"] to the value needed for the next operation.
    public["shoe_count"] = len(state.get("shoe",[]))
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    # Return the computed value to the caller.
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
        # Branch when the following condition is true.
        if state.get("open_bets"):
            # Raise an error so invalid input or state is reported explicitly.
            raise ConflictError("Deal or clear open baccarat bets before changing settings")
        # Set rules to the value needed for the next operation.
        rules = state.setdefault("rules", engine.default_state()["rules"])
        # Iterate through the collection to process each item.
        for key in ["decks","tie_payout","banker_commission","tie_behavior","cut_cards_remaining"]:
            # Branch when the following condition is true.
            if key in body: rules[key] = body[key]
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state); return payload(player_id, state)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/baccarat/bets")
    # Define the bet function used by this module.
    def bet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query); amount = require_amount(body.get("amount"))
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set item to the value needed for the next operation.
        item = engine.add_bet(state, player_id, body.get("bet_type"), amount)
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(player_id, amount, "BACCARAT_BET_PLACED", GAME_ID, None, {"bet_id": item["bet_id"], "bet_type": item["type"]})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"bet": item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/baccarat/bets/(?P<bet_id>[^/]+)")
    # Define the clear function used by this module.
    def clear(body, query, bet_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set item to the value needed for the next operation.
        item = engine.remove_bet(state, bet_id, player_id)
        # Execute this statement as part of the module's documented control flow.
        ledger.credit(player_id, item["amount"], "BACCARAT_BET_REFUND", GAME_ID, None, {"bet_id": bet_id})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"cleared": item, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/baccarat/deal")
    # Define the deal function used by this module.
    def deal(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set coup to the value needed for the next operation.
        coup = engine.deal_coup(state)
        # Set settlements to the value needed for the next operation.
        settlements=[]
        # Iterate through the collection to process each item.
        for b in coup["bets"]:
            # Set res to the value needed for the next operation.
            res = engine.settle_bet(b, coup, state.get("rules",{}))
            # Set credit to the value needed for the next operation.
            credit = None
            # Branch when the following condition is true.
            if res["credit"] > 0:
                # Set credit to the value needed for the next operation.
                credit = ledger.credit(b["player_id"], res["credit"], "BACCARAT_SETTLEMENT_CREDIT", GAME_ID, coup["round_id"], {"bet_id": b["bet_id"], "outcome": res["outcome"]})
            # Set bal to the value needed for the next operation.
            bal = players.get_player(b["player_id"])["balance"]
            # Execute this statement as part of the module's documented control flow.
            append_history(GAME_ID, coup["round_id"], b["player_id"], b["type"], b["label"], b["amount"], res["outcome"], res["credit"], bal, coup)
            # Execute this statement as part of the module's documented control flow.
            settlements.append({"bet": b, "settlement": res, "ledger": credit})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Set logger.info("baccarat_coup_dealt", round_id to the value needed for the next operation.
        logger.info("baccarat_coup_dealt", round_id=coup["round_id"], winner=coup["winner"], bet_count=len(coup["bets"]))
        # Return the computed value to the caller.
        return {"coup": coup, "settlements": settlements, "bot_bets": [], **payload(player_id, state)}
