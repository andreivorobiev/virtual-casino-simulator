# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import require_amount, require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import players, logger
# Import the shared id factory so pre-session purchases have stable settlement identities.
from casino.core.ids import new_id
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import required dependency so this module can use its public functions or constants.
from casino.games.bingo import engine
# Import bot capability profiles so every session seats funded competitor cards. (issue #405)
from casino.bots import profiles

# Set GAME_ID to the value needed for the next operation.
GAME_ID="bingo"
# Bind every Bingo movement to one storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "card_id")
# Seat at most three competitor cards per session so the human card must genuinely race to win. (issue #405)
MAX_BOT_CARDS = 3
# Always present exactly this many competitor cards so the house edge cannot be thinned by disabling bots. (issue #452)
COMPETITOR_CARDS = 3
# Own the synthetic house spoiler identity that fills unfunded competitor seats without a wallet or a payout. (issue #452)
HOUSE_COMPETITOR_ID = "bingo_house"

# Define the fund_bot_players function used by this module.
def fund_bot_players(player_id, amount, pattern, purchase_id):
    # Collect only bots whose card purchase actually debited a bot wallet. (issue #405)
    funded=[]
    # Iterate through the eligible bingo bots, bounded to the per-session seat limit.
    for bot in profiles.eligible_bots(GAME_ID)[:MAX_BOT_CARDS]:
        # Never seat the requesting player's own wallet as its competitor.
        if bot.get("player_id") == player_id:
            # Skip the colliding identity.
            continue
        # Price the bot card from its configured bingo stake, falling back to the human card price.
        stake = round(float(bot.get("stake") or amount), 2)
        # Start protected funding so an unfundable bot shrinks the field instead of failing the purchase.
        try:
            # Debit the BOT wallet with the same event type the bot controller uses for mid-session joins.
            ev, _replayed = SETTLEMENT.apply_once(player_id=bot["player_id"], signed_amount=-stake, transaction_type="BOT_BINGO_CARD_PURCHASED", round_id=purchase_id, action_key=f"{purchase_id}:bot:{bot['player_id']}:wager", request_fingerprint=f"{purchase_id}:{bot['player_id']}:{pattern}:{stake}", details={"bot_id": bot.get("bot_id"), "strategy_id": bot.get("strategy_id"), "pattern": pattern})
        # Handle the expected failure path for the protected logic.
        except Exception as exc:
            # Fail closed: a wallet that cannot pay gets no card, so no uncharged card can ever win a payout. (issue #405)
            logger.warning("bingo_bot_card_skipped", bot_id=bot.get("bot_id"), message=str(exc))
            # Continue seating the remaining fundable bots.
            continue
        # Record the funded competitor in the shape engine.start_session consumes for bot cards.
        funded.append({"player_id": bot["player_id"], "amount": stake, "bot_id": bot.get("bot_id"), "ledger_id": ev.get("ledger_id")})
    # Return the funded competitor list to the card purchase flow.
    return funded

# Seat a fixed competitor field so the paytable's house edge holds regardless of the admin bot roster. (issue #452)
def seat_competitors(player_id, amount, pattern, purchase_id):
    # Fund real bot competitor cards first so genuine bot wallets carry real stakes and can win real payouts. (issue #405)
    seats = fund_bot_players(player_id, amount, pattern, purchase_id)
    # Fill every remaining competitor seat with a synthetic house spoiler card so the field is always full. (issue #452)
    for _ in range(max(0, COMPETITOR_CARDS - len(seats))):
        # A house card races the human at the human's stake for display parity but is never funded and never paid. (issue #452)
        seats.append({"player_id": HOUSE_COMPETITOR_ID, "amount": amount, "source": "house"})
    # Return the always-full competitor field to the card purchase flow.
    return seats

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Set visible_players to the value needed for private game payloads.
    visible_players = [p for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]
    # Return the computed value to the caller.
    return {"game":GAME_ID,"state":state,"player":players.get_player(player_id),"players":visible_players}


# Define the settle_if_done function used by this module.
def settle_if_done(sess):
    # Set credits to the value needed for the next operation.
    credits=[]
    # Branch when the following condition is true.
    if sess and sess.get("status") == "won":
        # Iterate through the collection to process each item.
        for card in sess.get("cards", []):
            # Credit only a real winning card; synthetic house spoilers end sessions but are never paid. (issue #452)
            if card.get("status") == "won" and card.get("source") != "house" and not card.get("credited"):
                # Commit or replay the payout under the durable session-card identity. (issue #403)
                credit,replayed=SETTLEMENT.apply_once(player_id=card["player_id"], signed_amount=card["payout"], transaction_type="BINGO_PAYOUT_CREDIT", round_id=sess["session_id"], action_key=f"{card['card_id']}:settlement", request_fingerprint=f"{card['card_id']}:{sess['session_id']}:{card['payout']}", details={"pattern":sess["pattern"], "card_id": card["card_id"]}) if card["payout"] else (None, False)
                # Append history and expose a new credit only for the storage-committing call. (issue #403)
                if not replayed:
                    # Read the post-commit wallet balance for the first outcome row.
                    bal=players.get_player(card["player_id"])["balance"]
                    # Append the immutable winning-card history once.
                    append_history(GAME_ID, sess["session_id"], card["player_id"], "card", sess["pattern"], card["amount"], "win", card["payout"], bal, {"called":sess["called"], "card":card["card"], "winning_coords": card.get("winning_coords", [])})
                    # Expose the newly committed credit to the caller.
                    credits.append(credit)
                # Set card["credited"] to the value needed for the next operation.
                card["credited"] = True
    # Record the capped zero-payout loss exactly once so bounded sessions leave an audit trail. (issue #405)
    elif sess and sess.get("status") == "no_win" and not sess.get("loss_recorded"):
        # Append one session-level history row mirroring the refund/abandon idiom, with zero payout.
        append_history(GAME_ID, sess["session_id"], sess["player_id"], "session", sess["pattern"], sess["amount"], "no_win", 0, players.get_player(sess["player_id"])["balance"], {"called": sess.get("called", []), "max_calls": sess.get("max_calls")})
        # Guard against duplicate audit rows if settlement is re-entered with the archived session.
        sess["loss_recorded"] = True
    # Return the computed value to the caller.
    return credits


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/bingo/state")
    # Define the state function used by this module.
    def state(body, query): return payload(request_player_id(body, query))

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/cards")
    # Define the card function used by this module.
    def card(body, query):
        # Set player_id to the value needed for the next operation.
        player_id=request_player_id(body, query); amount=require_amount(body.get("amount")); pattern=body.get("pattern","line")
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Allocate one purchase identity before the session exists so every refund is correlated.
        purchase_id = new_id("bingo-purchase")
        # Commit the human card stake through the shared settlement boundary.
        SETTLEMENT.apply_once(player_id=player_id, signed_amount=-amount, transaction_type="BINGO_CARD_PURCHASED", round_id=purchase_id, action_key=f"{purchase_id}:human:wager", request_fingerprint=f"{purchase_id}:{player_id}:{pattern}:{amount}", details={"pattern":pattern})
        # Track funded competitors outside the protected block so the failure path can refund them.
        bot_players=[]
        # Start protected logic so failures can be handled safely.
        try:
            # Seat a guaranteed full competitor field: funded bots plus synthetic house spoilers. (issue #405, #452)
            bot_players=seat_competitors(player_id, amount, pattern, purchase_id)
            # Seat the competitors so the human card must beat a full field to be paid. (issue #405)
            sess=engine.start_session(state, player_id, amount, pattern, bot_players=bot_players)
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            SETTLEMENT.apply_once(player_id=player_id, signed_amount=amount, transaction_type="BINGO_CARD_REFUND_AFTER_ERROR", round_id=purchase_id, action_key=f"{purchase_id}:human:refund", request_fingerprint=f"{purchase_id}:{player_id}:{pattern}:{amount}:refund", details={"pattern":pattern})
            # Iterate through the collection to process each item.
            for bp in bot_players:
                # Never refund a synthetic house seat: it was never debited from any wallet. (issue #452)
                if bp.get("source") == "house":
                    # Skip the unfunded spoiler seat.
                    continue
                # Return each already-debited bot stake so a failed start never strands bot funds. (issue #405)
                SETTLEMENT.apply_once(player_id=bp["player_id"], signed_amount=bp["amount"], transaction_type="BOT_BINGO_CARD_REFUND_AFTER_ERROR", round_id=purchase_id, action_key=f"{purchase_id}:bot:{bp['player_id']}:refund", request_fingerprint=f"{purchase_id}:{bp['player_id']}:{pattern}:{bp['amount']}:refund", details={"pattern":pattern, "bot_id": bp.get("bot_id")})
            # Execute this statement as part of the module's documented control flow.
            raise
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state); return {"session":sess, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/call")
    # Define the call function used by this module.
    def call(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set sess,n to the value needed for the next operation.
        sess,n=engine.call_next(state); credits=settle_if_done(sess)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state); return {"session":sess,"called":n,"label":engine.ball_label(n),"credits":credits, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/auto")
    # Define the auto function used by this module.
    def auto(body, query):
        # Compatibility endpoint: only calls a small number of balls now. The browser-level
        # autoplay controller uses /call one tick at a time so Stop can be honored.
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Set sess,calls to the value needed for the next operation.
        sess,calls=engine.auto_play(state, int(body.get("max_calls",1))); credits=settle_if_done(sess)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state); return {"session":sess,"calls":calls,"labels":[engine.ball_label(n) for n in calls],"credits":credits, **payload(player_id, state)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/bingo/reset")
    # Define the reset function used by this module.
    def reset(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set state to the value needed for the next operation.
        state=load_player_game_state(GAME_ID, player_id, engine.default_state)
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
                    # Never refund a synthetic house spoiler seat: it was never debited from any wallet. (issue #452)
                    if card.get("source") == "house":
                        # Skip the unfunded spoiler card.
                        continue
                    # Execute this statement as part of the module's documented control flow.
                    event, _replayed = SETTLEMENT.apply_once(player_id=card["player_id"], signed_amount=card["amount"], transaction_type="BINGO_CARD_REFUND", round_id=sess["session_id"], action_key=f"{card['card_id']}:refund", request_fingerprint=f"{card['card_id']}:{sess['session_id']}:{card['amount']}:refund", details={"card_id": card["card_id"]})
                    # Preserve the historical event list response shape.
                    refunds.append(event)
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
        save_player_game_state(GAME_ID, player_id, state); return {"refunds":refunds, **payload(player_id, state)}
