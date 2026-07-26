# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import apply_rule_updates, require_amount, require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import ledger, players, logger
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import required dependency so this module can use its public functions or constants.
from casino.games.blackjack import engine
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError, ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "blackjack"

# Declare the legal domain of every client-settable table rule so the settings route cannot persist a
# value that settlement math or shoe construction would then trust. (issue #404)
RULE_DOMAIN = {
    # Restrict the shoe to real table sizes; an unbounded count would allocate 52*decks card strings.
    "decks": {"kind": "int", "min": 1, "max": 8},
    # Allow only the soft-17 switch as a true boolean.
    "dealer_hits_soft_17": {"kind": "bool"},
    # Restrict the natural payout to the three published table offers (3:2, 6:5, 1:1) that the UI shows.
    "blackjack_payout": {"kind": "enum", "values": [1.5, 1.2, 1]},
    # Bound resplitting to the standard maximum of four hands.
    "max_split_hands": {"kind": "int", "min": 1, "max": 4},
    # Allow only the double-after-split switch as a true boolean.
    "double_after_split": {"kind": "bool"},
    # Allow only the late-surrender switch as a true boolean.
    "late_surrender": {"kind": "bool"},
    # Allow only the split-aces switch as a true boolean.
    "split_aces_one_card": {"kind": "bool"},
}

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the exposed_round function used by this module.
def exposed_round(rnd):
    # Branch when the following condition is true.
    if not rnd: return None
    # Set copy to the value needed for the next operation.
    copy = {**rnd, "dealer": {**rnd["dealer"]}}
    # Branch when the following condition is true.
    if copy["dealer"].get("hole_card_hidden") and copy["dealer"].get("cards"):
        # Set copy["dealer"] to the value needed for the next operation.
        copy["dealer"] = {**copy["dealer"], "cards": [copy["dealer"]["cards"][0], "??"]}
    # Return the computed value to the caller.
    return copy

# Define the state_payload function used by this module.
def state_payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    # Return the computed value to the caller.
    return {"game": GAME_ID, "state": {"rules": state.get("rules"), "shoe_count": len(state.get("shoe",[])), "rounds": {rid: exposed_round(r) for rid,r in state.get("rounds",{}).items()}}, "player": players.get_player(player_id), "players": visible_players}

# Define the finish_if_needed function used by this module.
def finish_if_needed(state, rnd):
    # Set credits to the value needed for the next operation.
    credits=[]
    # Branch when the following condition is true.
    if rnd.get("status") == "settled_pending_credit":
        # Iterate through the collection to process each item.
        for h in rnd["hands"]:
            # Set due to the value needed for the next operation.
            due = round(float(h.get("payout_due",0)),2)
            # Branch when the following condition is true.
            if h.get("credited"):
                # Execute this statement as part of the module's documented control flow.
                continue
            # Branch when the following condition is true.
            if due > 0:
                # Execute this statement as part of the module's documented control flow.
                credits.append(ledger.credit(rnd["player_id"], due, "BLACKJACK_SETTLEMENT_CREDIT", GAME_ID, rnd["round_id"], {"hand_id": h["hand_id"], "outcome": h.get("outcome")}))
            # Set bal to the value needed for the next operation.
            bal = players.get_player(rnd["player_id"])["balance"]
            # Execute this statement as part of the module's documented control flow.
            append_history(GAME_ID, rnd["round_id"], rnd["player_id"], "hand", h["hand_id"], h["bet"], h.get("outcome","unknown"), due, bal, {"cards": h["cards"], "dealer": rnd["dealer"]["cards"]})
            # Set h["credited"] to the value needed for the next operation.
            h["credited"] = True
        # Execute this statement as part of the module's documented control flow.
        engine.settle_round(rnd)
    # Return the computed value to the caller.
    return credits

# Define the has_active_round function used by this module.
def has_active_round(state):
    # Return the computed value to the caller.
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
        # Branch when the following condition is true.
        if has_active_round(state):
            # Raise an error so invalid input or state is reported explicitly.
            raise ConflictError("Finish active blackjack rounds before changing table rules")
        # Set rules to the value needed for the next operation.
        rules = state.setdefault("rules", engine.default_state()["rules"])
        # Validate every caller-supplied rule against its declared domain before it can reach payout
        # math, because these values are read directly by natural_payout_due and make_shoe (issue #404).
        apply_rule_updates(body, rules, RULE_DOMAIN)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return state_payload(player_id, state)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/blackjack/rounds")
    # Define the deal function used by this module.
    def deal(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query); amount = require_amount(body.get("bet_amount"))
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(player_id, amount, "BLACKJACK_INITIAL_BET", GAME_ID, None, {})
        # Start protected logic so failures can be handled safely.
        try:
            # Set rnd to the value needed for the next operation.
            rnd = engine.new_round(state, player_id, amount)
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            ledger.credit(player_id, amount, "BLACKJACK_INITIAL_BET_REFUND_AFTER_ERROR", GAME_ID, None, {})
            # Execute this statement as part of the module's documented control flow.
            raise
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Set logger.info("blackjack_round_dealt", round_id to the value needed for the next operation.
        logger.info("blackjack_round_dealt", round_id=rnd["round_id"], player_id=player_id, bet=amount)
        # Return the computed value to the caller.
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
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
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
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
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
        # Branch when the following condition is true.
        if not h: raise ConflictError("No active hand")
        # Set original_bet to the value needed for the next operation.
        original_bet = float(h["bet"]); original_hand_id = h["hand_id"]
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(rnd["player_id"], original_bet, "BLACKJACK_DOUBLE_DEBIT", GAME_ID, round_id, {"hand_id": original_hand_id})
        # Start protected logic so failures can be handled safely.
        try:
            # Set rnd to the value needed for the next operation.
            rnd = engine.double_down(state, round_id)
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            ledger.credit(rnd["player_id"], original_bet, "BLACKJACK_DOUBLE_REFUND_AFTER_ERROR", GAME_ID, round_id, {"hand_id": original_hand_id})
            # Execute this statement as part of the module's documented control flow.
            raise
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
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
        # Branch when the following condition is true.
        if not h: raise ConflictError("No active hand")
        # Set original_bet to the value needed for the next operation.
        original_bet = float(h["bet"]); original_hand_id = h["hand_id"]
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(rnd["player_id"], original_bet, "BLACKJACK_SPLIT_DEBIT", GAME_ID, round_id, {"hand_id": original_hand_id})
        # Start protected logic so failures can be handled safely.
        try:
            # Set rnd to the value needed for the next operation.
            rnd = engine.split(state, round_id)
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            ledger.credit(rnd["player_id"], original_bet, "BLACKJACK_SPLIT_REFUND_AFTER_ERROR", GAME_ID, round_id, {"hand_id": original_hand_id})
            # Execute this statement as part of the module's documented control flow.
            raise
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
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
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
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
        # Branch when the following condition is true.
        if rnd.get("insurance"):
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Insurance has already been purchased for this round")
        # Branch when the following condition is true.
        if engine.card_rank(rnd["dealer"]["cards"][0]) != "A":
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Insurance is only available when dealer shows an Ace")
        # Set max_ins to the value needed for the next operation.
        max_ins = round(float(rnd["hands"][0]["bet"])/2,2)
        # Branch when the following condition is true.
        if amount > max_ins:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Insurance cannot exceed half the initial wager")
        # Execute this statement as part of the module's documented control flow.
        ledger.debit(rnd["player_id"], amount, "BLACKJACK_INSURANCE_DEBIT", GAME_ID, round_id, {})
        # Set dealer_bj to the value needed for the next operation.
        dealer_bj = engine.hand_total(rnd["dealer"]["cards"])["blackjack"]
        # Set payout to the value needed for the next operation.
        payout = amount*3 if dealer_bj else 0
        # Set credit to the value needed for the next operation.
        credit = ledger.credit(rnd["player_id"], payout, "BLACKJACK_INSURANCE_CREDIT", GAME_ID, round_id, {}) if payout else None
        # Set rnd["insurance"] to the value needed for the next operation.
        rnd["insurance"] = {"amount": amount, "dealer_blackjack": dealer_bj, "payout": payout}
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
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
        # Branch when the following condition is true.
        if rnd.get("even_money"):
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Even money has already been taken")
        # Branch when the following condition is true.
        if not engine.hand_total(h["cards"])["blackjack"] or engine.card_rank(rnd["dealer"]["cards"][0]) != "A":
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Even money is only available with player blackjack against dealer Ace")
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "even_money"; h["outcome"] = "even_money"; h["payout_due"] = round(float(h["bet"])*2,2)
        # Set rnd["even_money"] to the value needed for the next operation.
        rnd["even_money"] = True; rnd["dealer"]["hole_card_hidden"] = False; rnd["status"] = "settled_pending_credit"
        # Set credits to the value needed for the next operation.
        credits = finish_if_needed(state, rnd)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"round": exposed_round(rnd), "credits": credits, **state_payload(player_id, state)}
