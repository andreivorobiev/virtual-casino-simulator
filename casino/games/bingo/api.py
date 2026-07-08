# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_game_state, save_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import require_amount, require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import ledger, players, logger
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import required dependency so this module can use its public functions or constants.
from casino.games.bingo import engine

# Set GAME_ID to the value needed for the next operation.
GAME_ID="bingo"


# Define the payload function used by this module.
def payload(state=None):
    # Set state to the value needed for the next operation.
    state = state or load_game_state(GAME_ID, engine.default_state)
    # Return the computed value to the caller.
    return {"game":GAME_ID,"state":state,"player":players.get_player("human"),"players":players.list_players()}


# Define the settle_if_done function used by this module.
def settle_if_done(sess):
    # Set credits to the value needed for the next operation.
    credits=[]
    # Branch when the following condition is true.
    if sess and sess.get("status") == "won":
        # Iterate through the collection to process each item.
        for card in sess.get("cards", []):
            # Branch when the following condition is true.
            if card.get("status") == "won" and not card.get("credited"):
                # Set credit to the value needed for the next operation.
                credit=ledger.credit(card["player_id"], card["payout"], "BINGO_PAYOUT_CREDIT", GAME_ID, sess["session_id"], {"pattern":sess["pattern"], "calls":len(sess["called"]), "card_id": card["card_id"]}) if card["payout"] else None
                # Set bal to the value needed for the next operation.
                bal=players.get_player(card["player_id"])["balance"]
                # Execute this statement as part of the module's documented control flow.
                append_history(GAME_ID, sess["session_id"], card["player_id"], "card", sess["pattern"], card["amount"], "win", card["payout"], bal, {"called":sess["called"], "card":card["card"], "winning_coords": card.get("winning_coords", [])})
                # Set card["credited"] to the value needed for the next operation.
                card["credited"] = True
                # Execute this statement as part of the module's documented control flow.
                credits.append(credit)
    # Return the computed value to the caller.
    return credits


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/bingo/state")
    # Define the state function used by this module.
    def state(body, query): return payload()

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/cards")
    # Define the card function used by this module.
    def card(body, query):
        # Set player_id to the value needed for the next operation.
        player_id=require_player_id(body); amount=require_amount(body.get("amount")); pattern=body.get("pattern","line")
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(player_id, amount, "BINGO_CARD_PURCHASED", GAME_ID, None, {"pattern":pattern})
        # Start protected logic so failures can be handled safely.
        try:
            # Set sess to the value needed for the next operation.
            sess=engine.start_session(state, player_id, amount, pattern, bot_players=[])
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            ledger.credit(player_id, amount, "BINGO_CARD_REFUND_AFTER_ERROR", GAME_ID, None, {"pattern":pattern})
            # Execute this statement as part of the module's documented control flow.
            raise
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID,state); return {"session":sess, **payload(state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/call")
    # Define the call function used by this module.
    def call(body, query):
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Set sess,n to the value needed for the next operation.
        sess,n=engine.call_next(state); credits=settle_if_done(sess)
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID,state); return {"session":sess,"called":n,"label":engine.ball_label(n),"credits":credits, **payload(state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/auto")
    # Define the auto function used by this module.
    def auto(body, query):
        # Compatibility endpoint: only calls a small number of balls now. The browser-level
        # autoplay controller uses /call one tick at a time so Stop can be honored.
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Set sess,calls to the value needed for the next operation.
        sess,calls=engine.auto_play(state, int(body.get("max_calls",1))); credits=settle_if_done(sess)
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID,state); return {"session":sess,"calls":calls,"labels":[engine.ball_label(n) for n in calls],"credits":credits, **payload(state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/reset")
    # Define the reset function used by this module.
    def reset(body, query):
        # Set state to the value needed for the next operation.
        state=load_game_state(GAME_ID, engine.default_state)
        # Set sess to the value needed for the next operation.
        sess=state.get("active_session")
        # Set refunds to the value needed for the next operation.
        refunds=[]
        # Branch when the following condition is true.
        if sess and sess.get("status") == "active":
            # Branch when the following condition is true.
            if not sess.get("called"):
                # Iterate through the collection to process each item.
                for card in sess.get("cards", []):
                    # Execute this statement as part of the module's documented control flow.
                    refunds.append(ledger.credit(card["player_id"], card["amount"], "BINGO_CARD_REFUND", GAME_ID, sess["session_id"], {"card_id": card["card_id"]}))
                # Execute this statement as part of the module's documented control flow.
                append_history(GAME_ID, sess["session_id"], sess["player_id"], "session", sess["pattern"], sess["amount"], "refunded", sum(abs(r["amount"]) for r in refunds), players.get_player(sess["player_id"])["balance"], {"reason":"reset_before_calls"})
            # Handle the fallback branch when prior conditions did not match.
            else:
                # Execute this statement as part of the module's documented control flow.
                append_history(GAME_ID, sess["session_id"], sess["player_id"], "session", sess["pattern"], sess["amount"], "abandoned", 0, players.get_player(sess["player_id"])["balance"], {"called":sess.get("called",[])})
                # Set logger.warning("bingo_session_abandoned", session_id to the value needed for the next operation.
                logger.warning("bingo_session_abandoned", session_id=sess["session_id"], calls=len(sess.get("called",[])))
        # Set state["active_session"] to the value needed for the next operation.
        state["active_session"] = None
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID,state); return {"refunds":refunds, **payload(state)}
