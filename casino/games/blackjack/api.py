# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Blackjack API actions, hand persistence, and exactly-once settlement orchestration.
from casino.core.state_store import load_player_game_state, save_player_game_state
from casino.core.validation import require_amount, require_player_id
# Import the descriptor allowlist so the handler cannot drift from central router coercion.
from casino.core.game_rules import declared_fields
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

# Define the finish_if_needed function used by this module.
def finish_if_needed(state, rnd):
    # Set credits to the value needed for the next operation.
    credits=[]
    if rnd.get("status") == "settled_pending_credit":
        for h in rnd["hands"]:
            # Set due to the value needed for the next operation.
            due = round(float(h.get("payout_due",0)),2)
            # Skip hands whose persisted display flag already survived a completed settlement save. (issue #403)
            if h.get("credited"):
                continue
            # Track storage replay evidence so a raced or recovered settlement never repeats side effects. (issue #403)
            replayed = False
            if due > 0:
                # Commit or replay the payout under the durable deal-time round-and-hand action identity. (issue #403)
                event, replayed = SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=due, transaction_type="BLACKJACK_SETTLEMENT_CREDIT", round_id=rnd["round_id"], action_key=f"{rnd['round_id']}:{h['hand_id']}:settlement", request_fingerprint=f"{rnd['round_id']}:{h['hand_id']}:{h.get('outcome')}:{due}", details={"hand_id": h["hand_id"], "outcome": h.get("outcome")})
                # Report only the newly committed event because a replay was already reported by the winning call. (issue #403)
                if not replayed:
                    credits.append(event)
            # Append history only for the committing call so raced or recovered retries cannot duplicate rows. (issue #403)
            if not replayed:
                # Set bal to the value needed for the next operation.
                bal = players.get_player(rnd["player_id"])["balance"]
                append_history(GAME_ID, rnd["round_id"], rnd["player_id"], "hand", h["hand_id"], h["bet"], h.get("outcome","unknown"), due, bal, {"cards": h["cards"], "dealer": rnd["dealer"]["cards"]})
            # Keep the display flag while the durable ledger action key remains the settlement authority. (issue #403)
            h["credited"] = True
        engine.settle_round(rnd)
    return credits

# Define the has_active_round function used by this module.
def has_active_round(state):
    return any(r.get("status") in ("player_turn","settled_pending_credit") for r in state.get("rounds",{}).values())

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
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        if has_active_round(state):
            # Raise an error so invalid input or state is reported explicitly.
            raise ConflictError("Finish active blackjack rounds before changing table rules")
        # Set rules to the value needed for the next operation.
        rules = state.setdefault("rules", engine.default_state()["rules"])
        # Copy only centrally coerced descriptor fields so this handler owns no parallel rule schema. (SEC-014)
        for field in declared_fields(GAME_ID):
            # Preserve omitted rules while applying each validated caller update.
            if field in body:
                # Store the canonical router value for subsequent engine consumption.
                rules[field] = body[field]
        save_player_game_state(GAME_ID, player_id, state)
        return state_payload(player_id, state)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds")
    # Define the deal function used by this module.
    def deal(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query); amount = require_amount(body.get("bet_amount"))
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Allocate and validate the authoritative round before attempting its storage-atomic debit.
        rnd = engine.new_round(state, player_id, amount)
        # Commit the opening wager under the new round identity through the shared adapter.
        SETTLEMENT.apply_once(player_id=player_id, signed_amount=-amount, transaction_type="BLACKJACK_INITIAL_BET", round_id=rnd["round_id"], action_key=f"{rnd['round_id']}:wager", request_fingerprint=f"{rnd['round_id']}:{amount}", details={"hand_id": rnd["hands"][0]["hand_id"]})
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
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
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.hit(state, round_id); credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/stand")
    # Define the stand function used by this module.
    def stand(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.stand(state, round_id); credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/double")
    # Define the double function used by this module.
    def double(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.get_round(state, round_id)
        # Set h to the value needed for the next operation.
        h = engine.active_hand(rnd)
        if not h: raise ConflictError("No active hand")
        # Set original_bet to the value needed for the next operation.
        original_bet = float(h["bet"]); original_hand_id = h["hand_id"]
        SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=-original_bet, transaction_type="BLACKJACK_DOUBLE_DEBIT", round_id=round_id, action_key=f"{round_id}:{original_hand_id}:double", request_fingerprint=f"{round_id}:{original_hand_id}:double:{original_bet}", details={"hand_id": original_hand_id})
        # Start protected logic so failures can be handled safely.
        try:
            # Set rnd to the value needed for the next operation.
            rnd = engine.double_down(state, round_id)
        # Handle the expected failure path for the protected logic.
        except Exception:
            SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=original_bet, transaction_type="BLACKJACK_DOUBLE_REFUND_AFTER_ERROR", round_id=round_id, action_key=f"{round_id}:{original_hand_id}:double-refund", request_fingerprint=f"{round_id}:{original_hand_id}:double-refund:{original_bet}", details={"hand_id": original_hand_id})
            raise
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/split")
    # Define the split function used by this module.
    def split(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.get_round(state, round_id)
        # Set h to the value needed for the next operation.
        h = engine.active_hand(rnd)
        if not h: raise ConflictError("No active hand")
        # Set original_bet to the value needed for the next operation.
        original_bet = float(h["bet"]); original_hand_id = h["hand_id"]
        SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=-original_bet, transaction_type="BLACKJACK_SPLIT_DEBIT", round_id=round_id, action_key=f"{round_id}:{original_hand_id}:split", request_fingerprint=f"{round_id}:{original_hand_id}:split:{original_bet}", details={"hand_id": original_hand_id})
        # Start protected logic so failures can be handled safely.
        try:
            # Set rnd to the value needed for the next operation.
            rnd = engine.split(state, round_id)
        # Handle the expected failure path for the protected logic.
        except Exception:
            SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=original_bet, transaction_type="BLACKJACK_SPLIT_REFUND_AFTER_ERROR", round_id=round_id, action_key=f"{round_id}:{original_hand_id}:split-refund", request_fingerprint=f"{round_id}:{original_hand_id}:split-refund:{original_bet}", details={"hand_id": original_hand_id})
            raise
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/surrender")
    # Define the surrender function used by this module.
    def surrender(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.surrender(state, round_id); credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
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
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.get_round(state, round_id)
        # Reject insurance once player action has ended or the dealer hole card is exposed. (BJ-020, LEDGER-015)
        if rnd.get("status") != "player_turn" or not rnd.get("dealer", {}).get("hole_card_hidden"):
            # Raise before any ledger mutation so revealed or settled rounds cannot create risk-free insurance returns.
            raise ConflictError("Insurance is only available before the dealer hole card is revealed")
        if rnd.get("insurance"):
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Insurance has already been purchased for this round")
        if engine.card_rank(rnd["dealer"]["cards"][0]) != "A":
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Insurance is only available when dealer shows an Ace")
        # Set max_ins to the value needed for the next operation.
        max_ins = round(float(rnd["hands"][0]["bet"])/2,2)
        if amount > max_ins:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Insurance cannot exceed half the initial wager")
        SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=-amount, transaction_type="BLACKJACK_INSURANCE_DEBIT", round_id=round_id, action_key=f"{round_id}:insurance:wager", request_fingerprint=f"{round_id}:insurance:{amount}", details={})
        # Set dealer_bj to the value needed for the next operation.
        dealer_bj = engine.hand_total(rnd["dealer"]["cards"])["blackjack"]
        # Set payout to the value needed for the next operation.
        payout = amount*3 if dealer_bj else 0
        # Set credit to the value needed for the next operation.
        credit = SETTLEMENT.apply_once(player_id=rnd["player_id"], signed_amount=payout, transaction_type="BLACKJACK_INSURANCE_CREDIT", round_id=round_id, action_key=f"{round_id}:insurance:settlement", request_fingerprint=f"{round_id}:insurance:settlement:{payout}", details={})[0] if payout else None
        # Set rnd["insurance"] to the value needed for the next operation.
        rnd["insurance"] = {"amount": amount, "dealer_blackjack": dealer_bj, "payout": payout}
        save_player_game_state(GAME_ID, player_id, state)
        return {"round": exposed_round(rnd), "credit": credit, **state_payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/even-money")
    # Define the even_money function used by this module.
    def even_money(body, query, round_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set rnd to the value needed for the next operation.
        rnd = engine.get_round(state, round_id)
        # Set h to the value needed for the next operation.
        h = rnd["hands"][0]
        if rnd.get("even_money"):
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Even money has already been taken")
        if not engine.hand_total(h["cards"])["blackjack"] or engine.card_rank(rnd["dealer"]["cards"][0]) != "A":
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Even money is only available with player blackjack against dealer Ace")
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "even_money"; h["outcome"] = "even_money"; h["payout_due"] = round(float(h["bet"])*2,2)
        # Set rnd["even_money"] to the value needed for the next operation.
        rnd["even_money"] = True; rnd["dealer"]["hole_card_hidden"] = False; rnd["status"] = "settled_pending_credit"
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        save_player_game_state(GAME_ID, player_id, state)
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}
