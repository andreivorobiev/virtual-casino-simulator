# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import required dependency so this module can use its public functions or constants.
from casino.core.validation import require_player_id
# Import required dependency so this module can use its public functions or constants.
from casino.core import ledger, players
# Import required dependency so this module can use its public functions or constants.
from casino.core.history import append_history
# Import the shared opaque-id helper so debit, spin, credit, and history share one round.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.games.slots import engine
# Set GAME_ID to the value needed for the next operation.
GAME_ID = "slots"

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Return detached runtime rules so the browser never relies on stale embedded economics.
    return {"game": GAME_ID, "state": state, "player": players.get_player(player_id), "config": {"symbols": list(engine.SYMBOLS), "paylines": list(engine.PAYLINES.keys()), "paytable": {symbol: dict(table) for symbol, table in engine.PAYTABLE.items()}, "economics": engine.economics_config()}}

# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/slots/state")
    # Define the state function used by this module.
    def state(body, query): return payload(request_player_id(body, query))

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/slots/config")
    # Define the config function used by this module.
    def config(body, query): return payload(request_player_id(body, query))["config"]

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/slots/spin")
    # Define the spin function used by this module.
    def spin(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Normalize the submitted line count through the exact engine-owned closed vocabulary.
        active_lines = engine.normalize_active_lines(body.get("active_lines", 5))
        # Preserve the frozen v1 cent-normalized amount range at the game-owned boundary.
        line_bet = engine.normalize_line_bet(body.get("line_bet", 1))
        # Set state to the value needed for the next operation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Preview the exact current-route cost while a banked feature remains zero-cost.
        configuration = engine.effective_configuration(state, active_lines, line_bet)
        # Use the engine-owned cost equation before the current ledger debit.
        cost = configuration["cost"]
        # Allocate one round identity before money movement so every debit and settlement row reconciles.
        round_id = new_id("slot")
        # Set debit to the value needed for the next operation.
        debit = None
        # Branch when the following condition is true.
        if cost > 0:
            # Set debit to the value needed for the next operation.
            debit = ledger.debit(player_id, cost, "SLOTS_SPIN_DEBIT", GAME_ID, round_id, {"active_lines": configuration["active_lines"], "line_bet": configuration["line_bet"], "cost": cost})
        # Set result to the value needed for the next operation.
        result = engine.spin(state, active_lines, line_bet, round_id=round_id)
        # Set credit to the value needed for the next operation.
        credit = None
        # Branch when the following condition is true.
        if result["payout"] > 0:
            # Set credit to the value needed for the next operation.
            credit = ledger.credit(player_id, result["payout"], "SLOTS_PAYOUT_CREDIT", GAME_ID, result["round_id"], {"wins": result["wins"], "line_payout": result["line_payout"], "scatter_payout": result["scatter_payout"], "progressive_hit": result["progressive_hit"]})
        # Set bal to the value needed for the next operation.
        bal = players.get_player(player_id)["balance"]
        # Execute this statement as part of the module's documented control flow.
        append_history(GAME_ID, result["round_id"], player_id, "spin", f"{result['active_lines']} lines @ {result['line_bet']}", result["cost"], "win" if result["payout"] else "loss", result["payout"], bal, result)
        # Execute this statement as part of the module's documented control flow.
        save_player_game_state(GAME_ID, player_id, state)
        # Return the computed value to the caller.
        return {"spin": result, "debit": debit, "credit": credit, **payload(player_id, state)}
