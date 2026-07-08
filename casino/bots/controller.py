# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from __future__ import annotations
# Import required dependency so this module can use its public functions or constants.
import random
# Import required dependency so this module can use its public functions or constants.
from casino.bots import profiles
# Import required dependency so this module can use its public functions or constants.
from casino.core import ledger, logger, players
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_game_state, save_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError


# Define the _roulette_choice function used by this module.
def _roulette_choice(state, strategy_id):
    # Import required dependency so this module can use its public functions or constants.
    from casino.games.roulette import rules
    # Set mode to the value needed for the next operation.
    mode = state.get("mode", "double")
    # Set cat to the value needed for the next operation.
    cat = rules.catalog(mode)
    # Define the pick function used by this module.
    def pick(pred):
        # Set opts to the value needed for the next operation.
        opts = [b for b in cat if pred(b)]
        # Return the computed value to the caller.
        return random.choice(opts) if opts else None
    # Branch when the following condition is true.
    if strategy_id == "roulette_red_black":
        # Return the computed value to the caller.
        return pick(lambda b: b["type"] in ("red", "black"))
    # Branch when the following condition is true.
    if strategy_id == "roulette_random_number":
        # Return the computed value to the caller.
        return pick(lambda b: b["type"] == "straight" and b["covered_numbers"][0] not in ("0", "00"))
    # Branch when the following condition is true.
    if strategy_id == "roulette_split_corner":
        # Return the computed value to the caller.
        return pick(lambda b: b["type"] in ("split", "zero_split", "corner"))
    # Branch when the following condition is true.
    if strategy_id == "roulette_dozen_column":
        # Return the computed value to the caller.
        return pick(lambda b: b["type"] in ("dozen", "column"))
    # Branch when the following condition is true.
    if strategy_id == "roulette_racetrack":
        # Return the computed value to the caller.
        return pick(lambda b: b["type"] == "snake") or pick(lambda b: b["layout_kind"] == "outside")
    # Return the computed value to the caller.
    return pick(lambda b: b.get("layout_kind") == "outside")


# Define the play_roulette_round function used by this module.
def play_roulette_round() -> dict:
    # Import required dependency so this module can use its public functions or constants.
    from casino.games.roulette import engine
    # Set state to the value needed for the next operation.
    state = load_game_state("roulette", engine.default_state)
    # Set r to the value needed for the next operation.
    r = engine.ensure_open_round(state)
    # Set existing to the value needed for the next operation.
    existing = {b.get("player_id") for b in r.get("bets", [])}
    # Set placed to the value needed for the next operation.
    placed = []
    # Iterate through the collection to process each item.
    for bot in profiles.eligible_bots("roulette"):
        # Set player_id to the value needed for the next operation.
        player_id = bot["player_id"]
        # Branch when the following condition is true.
        if player_id in existing:
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set stake to the value needed for the next operation.
        stake = round(float(bot.get("stake") or 5), 2)
        # Set bdef to the value needed for the next operation.
        bdef = _roulette_choice(state, bot.get("strategy_id"))
        # Branch when the following condition is true.
        if not bdef:
            # Execute this statement as part of the module's documented control flow.
            continue
        # Start protected logic so failures can be handled safely.
        try:
            # Set item to the value needed for the next operation.
            item = engine.add_bet_to_state(state, player_id, bdef["type"], stake, bdef["covered_numbers"], bdef["label"], source="bot_controller")
            # Set ev to the value needed for the next operation.
            ev = ledger.debit(player_id, stake, "BOT_ROULETTE_BET_PLACED", "roulette", item["round_id"], {"bot_id": bot["bot_id"], "strategy_id": bot.get("strategy_id"), "bet_id": item["bet_id"], "covered_numbers": item["covered_numbers"]})
            # Execute this statement as part of the module's documented control flow.
            placed.append({"bot": bot, "action": "bet", "bet": item, "ledger": ev})
        # Handle the expected failure path for the protected logic.
        except Exception as exc:
            # Set logger.warning("bot_action_skipped", bot_id to the value needed for the next operation.
            logger.warning("bot_action_skipped", bot_id=bot.get("bot_id"), game="roulette", message=str(exc))
    # Execute this statement as part of the module's documented control flow.
    save_game_state("roulette", state)
    # Return the computed value to the caller.
    return {"game":"roulette", "actions": placed}


# Define the _baccarat_bet_type function used by this module.
def _baccarat_bet_type(strategy_id):
    # Branch when the following condition is true.
    if strategy_id == "baccarat_banker": return "banker"
    # Branch when the following condition is true.
    if strategy_id == "baccarat_player": return "player"
    # Branch when the following condition is true.
    if strategy_id == "baccarat_tie": return "tie"
    # Branch when the following condition is true.
    if strategy_id == "baccarat_pattern": return random.choice(["banker", "player", "banker", "tie"])
    # Return the computed value to the caller.
    return random.choice(["banker", "player", "tie"])


# Define the play_baccarat_round function used by this module.
def play_baccarat_round() -> dict:
    # Import required dependency so this module can use its public functions or constants.
    from casino.games.baccarat import engine
    # Set state to the value needed for the next operation.
    state = load_game_state("baccarat", engine.default_state)
    # Set existing to the value needed for the next operation.
    existing = {b.get("player_id") for b in state.get("open_bets", [])}
    # Set actions to the value needed for the next operation.
    actions = []
    # Iterate through the collection to process each item.
    for bot in profiles.eligible_bots("baccarat"):
        # Set player_id to the value needed for the next operation.
        player_id = bot["player_id"]
        # Branch when the following condition is true.
        if player_id in existing:
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set stake to the value needed for the next operation.
        stake = round(float(bot.get("stake") or 5), 2)
        # Set bet_type to the value needed for the next operation.
        bet_type = _baccarat_bet_type(bot.get("strategy_id"))
        # Start protected logic so failures can be handled safely.
        try:
            # Set item to the value needed for the next operation.
            item = engine.add_bet(state, player_id, bet_type, stake, source="bot_controller")
            # Set ev to the value needed for the next operation.
            ev = ledger.debit(player_id, stake, "BOT_BACCARAT_BET_PLACED", "baccarat", None, {"bot_id": bot["bot_id"], "strategy_id": bot.get("strategy_id"), "bet_id": item["bet_id"], "bet_type": bet_type})
            # Execute this statement as part of the module's documented control flow.
            actions.append({"bot": bot, "action": "bet", "bet": item, "ledger": ev})
        # Handle the expected failure path for the protected logic.
        except Exception as exc:
            # Set logger.warning("bot_action_skipped", bot_id to the value needed for the next operation.
            logger.warning("bot_action_skipped", bot_id=bot.get("bot_id"), game="baccarat", message=str(exc))
    # Execute this statement as part of the module's documented control flow.
    save_game_state("baccarat", state)
    # Return the computed value to the caller.
    return {"game":"baccarat", "actions": actions}


# Define the _keno_spots function used by this module.
def _keno_spots(strategy_id):
    # Set count to the value needed for the next operation.
    count = {"keno_quick_pick_3": 3, "keno_quick_pick_5": 5, "keno_quick_pick_10": 10, "keno_quick_pick_20": 20}.get(strategy_id, 5)
    # Return the computed value to the caller.
    return sorted(random.sample(range(1, 81), count))


# Define the play_keno_round function used by this module.
def play_keno_round() -> dict:
    # Import required dependency so this module can use its public functions or constants.
    from casino.games.keno import engine
    # Set state to the value needed for the next operation.
    state = load_game_state("keno", engine.default_state)
    # Set existing to the value needed for the next operation.
    existing = {t.get("player_id") for t in state.get("open_tickets", [])}
    # Set actions to the value needed for the next operation.
    actions = []
    # Iterate through the collection to process each item.
    for bot in profiles.eligible_bots("keno"):
        # Set player_id to the value needed for the next operation.
        player_id = bot["player_id"]
        # Branch when the following condition is true.
        if player_id in existing:
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set stake to the value needed for the next operation.
        stake = round(float(bot.get("stake") or 3), 2)
        # Set spots to the value needed for the next operation.
        spots = _keno_spots(bot.get("strategy_id"))
        # Start protected logic so failures can be handled safely.
        try:
            # Set item to the value needed for the next operation.
            item = engine.add_ticket(state, player_id, spots, stake, source="bot_controller")
            # Set ev to the value needed for the next operation.
            ev = ledger.debit(player_id, stake, "BOT_KENO_TICKET_PURCHASED", "keno", None, {"bot_id": bot["bot_id"], "strategy_id": bot.get("strategy_id"), "ticket_id": item["ticket_id"], "spots": spots})
            # Execute this statement as part of the module's documented control flow.
            actions.append({"bot": bot, "action": "ticket", "ticket": item, "ledger": ev})
        # Handle the expected failure path for the protected logic.
        except Exception as exc:
            # Set logger.warning("bot_action_skipped", bot_id to the value needed for the next operation.
            logger.warning("bot_action_skipped", bot_id=bot.get("bot_id"), game="keno", message=str(exc))
    # Execute this statement as part of the module's documented control flow.
    save_game_state("keno", state)
    # Return the computed value to the caller.
    return {"game":"keno", "actions": actions}


# Define the play_bingo_round function used by this module.
def play_bingo_round() -> dict:
    # Import required dependency so this module can use its public functions or constants.
    from casino.games.bingo import engine
    # Set state to the value needed for the next operation.
    state = load_game_state("bingo", engine.default_state)
    # Set sess to the value needed for the next operation.
    sess = state.get("active_session")
    # Branch when the following condition is true.
    if not sess or sess.get("status") != "active":
        # Return the computed value to the caller.
        return {"game":"bingo", "actions": [], "message": "No active Bingo session"}
    # Set existing to the value needed for the next operation.
    existing = {c.get("player_id") for c in sess.get("cards", [])}
    # Set actions to the value needed for the next operation.
    actions = []
    # Iterate through the collection to process each item.
    for bot in profiles.eligible_bots("bingo"):
        # Set player_id to the value needed for the next operation.
        player_id = bot["player_id"]
        # Branch when the following condition is true.
        if player_id in existing:
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set stake to the value needed for the next operation.
        stake = round(float(bot.get("stake") or sess.get("amount") or 5), 2)
        # Start protected logic so failures can be handled safely.
        try:
            # Set ev to the value needed for the next operation.
            ev = ledger.debit(player_id, stake, "BOT_BINGO_CARD_PURCHASED", "bingo", sess.get("session_id"), {"bot_id": bot["bot_id"], "strategy_id": bot.get("strategy_id"), "pattern": sess.get("pattern")})
            # Set card to the value needed for the next operation.
            card = {"card_id": new_id("card"), "player_id": player_id, "amount": stake, "card": engine.make_card(), "status":"active", "winner": False, "payout":0, "source":"bot_controller", "created_at": utc_now()}
            # Execute this statement as part of the module's documented control flow.
            sess.setdefault("cards", []).append(card)
            # Execute this statement as part of the module's documented control flow.
            actions.append({"bot": bot, "action": "card", "card": card, "ledger": ev})
        # Handle the expected failure path for the protected logic.
        except Exception as exc:
            # Set logger.warning("bot_action_skipped", bot_id to the value needed for the next operation.
            logger.warning("bot_action_skipped", bot_id=bot.get("bot_id"), game="bingo", message=str(exc))
    # Execute this statement as part of the module's documented control flow.
    save_game_state("bingo", state)
    # Return the computed value to the caller.
    return {"game":"bingo", "actions": actions}


# Define the play_round function used by this module.
def play_round(game_id: str) -> dict:
    # Branch when the following condition is true.
    if game_id == "roulette": return play_roulette_round()
    # Branch when the following condition is true.
    if game_id == "baccarat": return play_baccarat_round()
    # Branch when the following condition is true.
    if game_id == "keno": return play_keno_round()
    # Branch when the following condition is true.
    if game_id == "bingo": return play_bingo_round()
    # Raise an error so invalid input or state is reported explicitly.
    raise ValidationError(f"Bots are not supported for {game_id}")
