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
from casino.games.baccarat import engine
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "baccarat"

# Declare the legal domain of every client-settable table rule so the settings route cannot persist a
# value that settle_bet or make_shoe would then trust. (issue #404)
RULE_DOMAIN = {
    # Restrict the shoe to real table sizes; an unbounded count would allocate 52*decks card strings.
    "decks": {"kind": "int", "min": 1, "max": 8},
    # Bound the tie payout to the two published offers (8:1 and 9:1) rather than any caller number.
    "tie_payout": {"kind": "enum", "values": [8, 9]},
    # Keep the banker commission inside a real house range so a negative value cannot inflate wins.
    "banker_commission": {"kind": "number", "min": 0, "max": 0.25},
    # Accept only the tie behaviour the engine actually implements.
    "tie_behavior": {"kind": "enum", "values": ["push"]},
    # Bound the cut-card depth to a sane portion of the shoe.
    "cut_cards_remaining": {"kind": "int", "min": 1, "max": 104},
}

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Settle one committed coup exactly once, finalize its terminal state, and persist the finalized round. (issues #430, #555)
def settle_committed_coup(player_id: str, state: dict, coup: dict):
    # Collect per-bet settlement evidence for the deal response.
    settlements=[]
    # Settle every bet snapshotted when the coup's cards were committed.
    for b in coup["bets"]:
        # Price the bet against the committed coup under the current table rules.
        res = engine.settle_bet(b, coup, state.get("rules",{}))
        # Set credit to the value needed for the next operation.
        credit = None
        # Track storage replay evidence so a raced or recovered settlement never repeats side effects. (issue #403)
        replayed = False
        # Branch when the following condition is true.
        if res["credit"] > 0:
            # Commit or replay the payout under the durable placement-time bet action identity. (issue #403)
            credit, replayed = ledger.credit_once(b["player_id"], res["credit"], "BACCARAT_SETTLEMENT_CREDIT", f"{b['bet_id']}:settlement", GAME_ID, coup["round_id"], {"bet_id": b["bet_id"], "outcome": res["outcome"]})
        # Append history only for the committing call so raced or recovered retries cannot duplicate rows. (issue #403)
        if not replayed:
            # Set bal to the value needed for the next operation.
            bal = players.get_player(b["player_id"])["balance"]
            # Execute this statement as part of the module's documented control flow.
            append_history(GAME_ID, coup["round_id"], b["player_id"], b["type"], b["label"], b["amount"], res["outcome"], res["credit"], bal, coup)
        # Execute this statement as part of the module's documented control flow.
        settlements.append({"bet": b, "settlement": res, "ledger": credit})
    # Apply the terminal coup mutations exactly once and release the settlement commitment.
    engine.finalize_coup(state, coup)
    # Persist the finalized round so the committed settlement can never run twice.
    save_player_game_state(GAME_ID, player_id, state)
    # Return the settlement evidence for the deal response.
    return settlements

# Complete any committed-but-unfinalized coup before a new mutation, so an interrupted settlement is replayed rather than wiped or redealt. (issue #555)
def resume_pending_coup(player_id: str, state: dict):
    # Read the coup committed before the interruption, when one exists.
    pending=state.get("pending_coup")
    # Replay the committed settlement so its bets settle exactly once against the original cards.
    if pending: settle_committed_coup(player_id, state, pending)

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Publish the state without the private shoe or the transient settlement commitment so the response shape stays contract-stable. (issue #555)
    public = {k:v for k,v in state.items() if k not in ("shoe", "pending_coup")}
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
        # Validate every caller-supplied rule against its declared domain before it can reach payout
        # math, because these values are read directly by settle_bet and make_shoe (issue #404).
        apply_rule_updates(body, rules, RULE_DOMAIN)
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
        # Complete any interrupted settlement first so finalizing it can never wipe this new bet. (issue #555)
        resume_pending_coup(player_id, state)
        # Set item to the value needed for the next operation.
        item = engine.add_bet(state, player_id, body.get("bet_type"), amount)
        # Debit the stake under its storage-atomic placement-time action identity so a recovered replay cannot double-charge. (issue #555)
        ledger.debit_once(player_id, amount, "BACCARAT_BET_PLACED", f"{item['bet_id']}:wager", GAME_ID, None, {"bet_id": item["bet_id"], "bet_type": item["type"]})
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
        # Complete any interrupted settlement first so a settled bet can never be refunded afterwards. (issue #555)
        resume_pending_coup(player_id, state)
        # Set item to the value needed for the next operation.
        item = engine.remove_bet(state, bet_id, player_id)
        # Refund the durable bet exactly once so a replayed clear returns the original event instead of minting a second refund. (issue #555)
        ledger.credit_once(player_id, item["amount"], "BACCARAT_BET_REFUND", f"{bet_id}:refund", GAME_ID, None, {"bet_id": bet_id})
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
        # Resume the coup committed by an interrupted request instead of dealing fresh cards. (issue #555)
        coup = state.get("pending_coup")
        # Branch when no settlement is pending so the dealt cards and consumed shoe commit durably before any credit.
        if not coup:
            # Deal and price the coup without mutating terminal state.
            coup = engine.commit_coup(state)
            # Persist the committed cards and shoe position atomically before the first settlement side effect.
            state["pending_coup"] = coup; save_player_game_state(GAME_ID, player_id, state)
        # Settle every committed bet exactly once and finalize the round.
        settlements = settle_committed_coup(player_id, state, coup)
        # Set logger.info("baccarat_coup_dealt", round_id to the value needed for the next operation.
        logger.info("baccarat_coup_dealt", round_id=coup["round_id"], winner=coup["winner"], bet_count=len(coup["bets"]))
        # Return the computed value to the caller.
        return {"coup": coup, "settlements": settlements, "bot_bets": [], **payload(player_id, state)}
