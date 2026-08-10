# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import require_amount, require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import players, logger
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import required dependency so this module can use its public functions or constants.
from casino.games.roulette import engine, rules
# Import required dependency so this module can use its public functions or constants.
from casino.games.roulette.rules import expand_call_bet
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError
# Import the descriptor allowlist so route behavior cannot drift from central coercion metadata.
from casino.core.game_rules import declared_fields

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "roulette"
# Bind every Roulette movement to one storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "bet_id")


# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while keeping legacy v1 calls on the human player.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})


# Define the scoreboards function used by this module.
def scoreboards(player_id: str):
    # Return the computed value to the caller.
    return [{"player_id": p["player_id"], "display_name": p["display_name"], "balance": p["balance"], "type": p["type"]} for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]


# Define the state_payload function used by this module.
def state_payload(player_id: str, state=None, query=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Build the player-specific response shared by legacy and compact callers. (TEST-166)
    payload = {"game": GAME_ID, "state": state, "player": players.get_player(player_id), "players": scoreboards(player_id), "stats": engine.stats(state)}
    # Preserve the frozen complete response unless the current client explicitly requests the play projection.
    if not isinstance(query, dict) or query.get("projection") != "play":
        # Retain the complete mode-specific bet catalog for every legacy caller.
        payload["catalog"] = rules.catalog(state.get("mode", "double"))
    # Return the compact or complete response without changing state, money, or settlement semantics.
    return payload


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/roulette/state")
    # Define the state function used by this module.
    def state(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Return the computed value to the caller.
        return state_payload(player_id, query=query)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/settings")
    # Define the settings function used by this module.
    def settings(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Resolve the canonical settings allowlist once from the module descriptor. (SEC-014)
        fields = declared_fields(GAME_ID)
        # Branch when the following condition is true.
        if "mode" in fields and "mode" in body:
            # Execute this statement as part of the module's documented control flow.
            engine.set_mode(state, body["mode"])
        # Branch when the following condition is true.
        if "zero_rule" in fields and "zero_rule" in body:
            # Set state["zero_rule"] to the value needed for the next operation.
            state["zero_rule"] = body["zero_rule"]
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return state_payload(player_id, state, query=query)

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/roulette/bet-catalog")
    # Define the catalog function used by this module.
    def catalog(body, query):
        # Set mode to the value needed for the next operation.
        mode = query.get("mode", "double")
        # Return the computed value to the caller.
        return {"catalog": rules.catalog(mode)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/bets")
    # Define the place_bet function used by this module.
    def place_bet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set amount to the value needed for the next operation.
        amount = require_amount(body.get("amount"))
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set item to the value needed for the next operation.
        item = engine.add_bet_to_state(state, player_id, body.get("bet_type"), amount, [str(x) for x in body.get("covered_numbers", [])], body.get("label"), source="manual")
        # Set led to the value needed for the next operation.
        led, _replayed = SETTLEMENT.apply_once(player_id=player_id, signed_amount=-amount, transaction_type="ROULETTE_BET_PLACED", round_id=item["round_id"], action_key=f"{item['bet_id']}:wager", request_fingerprint=f"{item['bet_id']}:{item['type']}:{item['covered_numbers']}:{amount}", details={"bet_id": item["bet_id"], "covered_numbers": item["covered_numbers"], "bet_type": item["type"]})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Set logger.info("roulette_bet_placed", player_id to the value needed for the next operation.
        logger.info("roulette_bet_placed", player_id=player_id, bet_id=item["bet_id"], amount=amount, bet_type=item["type"])
        # Return the computed value to the caller.
        return {"bet": item, "ledger": led, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/call-bet")
    # Define the call_bet function used by this module.
    def call_bet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set amount to the value needed for the next operation.
        amount = require_amount(body.get("amount"))
        # Set call_type to the value needed for the next operation.
        call_type = body.get("call_type")
        # Set number to the value needed for the next operation.
        number = body.get("number")
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set comps to the value needed for the next operation.
        comps = expand_call_bet(state.get("mode","double"), call_type, amount, number)
        # Branch when the following condition is true.
        if not comps:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Call bet produced no legal component bets", {"call_type": call_type})
        # Set placed to the value needed for the next operation.
        placed=[]; ledgers=[]
        # Iterate through the collection to process each item.
        for c in comps:
            # Set item to the value needed for the next operation.
            item = engine.add_bet_to_state(state, player_id, c["type"], float(c["amount"]), [str(x) for x in c["covered_numbers"]], c.get("label"), source="call_bet")
            # Execute this statement as part of the module's documented control flow.
            event, _replayed = SETTLEMENT.apply_once(player_id=player_id, signed_amount=-float(c["amount"]), transaction_type="ROULETTE_CALL_BET_PLACED", round_id=item["round_id"], action_key=f"{item['bet_id']}:wager", request_fingerprint=f"{item['bet_id']}:{call_type}:{item['covered_numbers']}:{c['amount']}", details={"call_type": call_type, "bet_id": item["bet_id"], "covered_numbers": item["covered_numbers"]})
            # Retain the historical event list response shape.
            ledgers.append(event)
            # Execute this statement as part of the module's documented control flow.
            placed.append(item)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"placed": placed, "ledger": ledgers, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/rebet")
    # Define the rebet function used by this module.
    def rebet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set template to the value needed for the next operation.
        template = state.get("last_bet_template") or []
        # Branch when the following condition is true.
        if not template:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("No roulette bet template is available for rebet")
        # Set placed to the value needed for the next operation.
        placed=[]; ledgers=[]
        # Iterate through the collection to process each item.
        for t in template:
            # Set item to the value needed for the next operation.
            item = engine.add_bet_to_state(state, player_id, t["type"], t["amount"], t["covered_numbers"], t.get("label"), source="rebet")
            # Execute this statement as part of the module's documented control flow.
            event, _replayed = SETTLEMENT.apply_once(player_id=player_id, signed_amount=-t["amount"], transaction_type="ROULETTE_REBET_PLACED", round_id=item["round_id"], action_key=f"{item['bet_id']}:wager", request_fingerprint=f"{item['bet_id']}:rebet:{t['amount']}", details={"bet_id": item["bet_id"]})
            # Retain the historical event list response shape.
            ledgers.append(event)
            # Execute this statement as part of the module's documented control flow.
            placed.append(item)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"placed": placed, "ledger": ledgers, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/roulette/bets/(?P<bet_id>[^/]+)")
    # Define the clear_bet function used by this module.
    def clear_bet(body, query, bet_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set bet to the value needed for the next operation.
        bet = engine.remove_bet_from_state(state, bet_id, player_id)
        # Refund each durable bet exactly once so a replayed clear returns the original event instead of minting a second refund. (issue #403)
        cred, _replayed = SETTLEMENT.apply_once(player_id=player_id, signed_amount=bet["amount"], transaction_type="ROULETTE_BET_REFUND", round_id=bet["round_id"], action_key=f"{bet_id}:refund", request_fingerprint=f"{bet_id}:refund:{bet['amount']}", details={"bet_id": bet_id})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"cleared": bet, "ledger": cred, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/clear")
    # Define the clear_all function used by this module.
    def clear_all(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set open_round to the value needed for the next operation.
        open_round = engine.ensure_open_round(state)
        # Set bets to the value needed for the next operation.
        bets = [b for b in list(open_round["bets"]) if b["player_id"] == player_id]
        # Iterate through the collection to process each item.
        for b in bets:
            # Execute this statement as part of the module's documented control flow.
            open_round["bets"].remove(b)
            # Refund each durable bet exactly once under the shared per-bet refund identity so replayed or overlapping clears cannot double-refund. (issue #403)
            SETTLEMENT.apply_once(player_id=player_id, signed_amount=b["amount"], transaction_type="ROULETTE_BET_REFUND", round_id=b["round_id"], action_key=f"{b['bet_id']}:refund", request_fingerprint=f"{b['bet_id']}:refund:{b['amount']}", details={"bet_id": b["bet_id"]})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"cleared": bets, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/spin")
    # Define the spin function used by this module.
    def spin(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Execute this statement as part of the module's documented control flow.
        engine.save_template_from_round(state, player_id)
        # Set zero_rule to the value needed for the next operation.
        zero_rule = state.get("zero_rule", "normal")
        # Set settled to the value needed for the next operation.
        settled = engine.spin_state(state)
        # Set settlements to the value needed for the next operation.
        settlements = []
        # Iterate through the collection to process each item.
        for bet in settled.get("bets", []):
            # Set res to the value needed for the next operation.
            res = engine.settle_bet(bet, settled["result"], zero_rule)
            # Set credit_ev to the value needed for the next operation.
            credit_ev = None
            # Set carried to the value needed for the next operation.
            carried = None
            # Track whether storage replayed an already-committed settlement credit for this durable bet. (issue #403)
            replayed = False
            # Branch when the following condition is true.
            if res.get("carry"):
                # Set carried to the value needed for the next operation.
                carried = engine.carry_en_prison_bet(state, bet)
            # Branch when the prior condition failed and this condition is true.
            elif res["credit"] > 0:
                # Credit each durable bet exactly once, keeping volatile result and outcome fields out of the fingerprinted details so a racing spin fails closed on ConflictError instead of double-paying. (issue #403)
                credit_ev, replayed = SETTLEMENT.apply_once(player_id=bet["player_id"], signed_amount=res["credit"], transaction_type="ROULETTE_SETTLEMENT_CREDIT", round_id=settled["round_id"], action_key=f"{bet['bet_id']}:settlement", request_fingerprint=f"{bet['bet_id']}:{settled['round_id']}:{res['credit']}", details={"bet_id": bet["bet_id"]})
            # Set bal to the value needed for the next operation.
            bal = players.get_player(bet["player_id"])["balance"]
            # Branch so history rows append only for first-time settlements and replays cannot duplicate them. (issue #403)
            if not replayed:
                # Execute this statement as part of the module's documented control flow.
                append_history(GAME_ID, settled["round_id"], bet["player_id"], bet["type"], bet["label"], bet["amount"], res["outcome"], res["credit"], bal, {"result": settled["result"], "color": settled["result_color"], "covered_numbers": bet["covered_numbers"], "carried_bet": carried})
            # Execute this statement as part of the module's documented control flow.
            settlements.append({"bet": bet, "settlement": res, "ledger": credit_ev, "carried_bet": carried, "replayed": replayed})
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Set logger.info("roulette_spin_result", round_id to the value needed for the next operation.
        logger.info("roulette_spin_result", round_id=settled["round_id"], result=settled["result"], color=settled["result_color"], bet_count=len(settled.get("bets",[])))
        # Return the computed value to the caller.
        return {"round": settled, "settlements": settlements, "bot_bets": [], **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/roulette/stats")
    # Define the stats function used by this module.
    def stats(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Return the computed value to the caller.
        return engine.stats(load_player_game_state(GAME_ID, player_id, engine.default_state))
