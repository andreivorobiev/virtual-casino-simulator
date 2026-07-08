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
from casino.games.slots import engine
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "slots"

# Define the payload function used by this module.
def payload(state=None):
    # Set state to the value needed for the next operation.
    state = state or load_game_state(GAME_ID, engine.default_state)
    # Return the computed value to the caller.
    return {"game": GAME_ID, "state": state, "player": players.get_player("human"), "config": {"symbols": engine.SYMBOLS, "paylines": list(engine.PAYLINES.keys()), "paytable": engine.PAYTABLE}}

# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/slots/state")
    # Define the state function used by this module.
    def state(body, query): return payload()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/slots/config")
    # Define the config function used by this module.
    def config(body, query): return payload()["config"]

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/slots/spin")
    # Define the spin function used by this module.
    def spin(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = require_player_id(body)
        # Start protected logic so failures can be handled safely.
        try:
            # Set active_lines to the value needed for the next operation.
            active_lines = int(body.get("active_lines", 5))
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("active_lines must be numeric")
        # Branch when the following condition is true.
        if active_lines not in engine.PAYLINES:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("active_lines must be one of 1,3,5,9,20")
        # Set line_bet to the value needed for the next operation.
        line_bet = require_amount(body.get("line_bet", 1))
        # Set state to the value needed for the next operation.
        state = load_game_state(GAME_ID, engine.default_state)
        # Set is_free to the value needed for the next operation.
        is_free = int(state.get("free_spins",0)) > 0
        # Set cost to the value needed for the next operation.
        cost = 0 if is_free else round(active_lines * line_bet, 2)
        # Set debit to the value needed for the next operation.
        debit = None
        # Branch when the following condition is true.
        if cost > 0:
            # Set debit to the value needed for the next operation.
            debit = ledger.debit(player_id, cost, "SLOTS_SPIN_DEBIT", GAME_ID, None, {"active_lines": active_lines, "line_bet": line_bet})
        # Set result to the value needed for the next operation.
        result = engine.spin(state, active_lines, line_bet)
        # Set credit to the value needed for the next operation.
        credit = None
        # Branch when the following condition is true.
        if result["payout"] > 0:
            # Set credit to the value needed for the next operation.
            credit = ledger.credit(player_id, result["payout"], "SLOTS_PAYOUT_CREDIT", GAME_ID, result["round_id"], {"wins": result["wins"]})
        # Set bal to the value needed for the next operation.
        bal = players.get_player(player_id)["balance"]
        # Execute this statement as part of the module's documented control flow.
        append_history(GAME_ID, result["round_id"], player_id, "spin", f"{active_lines} lines @ {line_bet}", cost, "win" if result["payout"] else "loss", result["payout"], bal, result)
        # Execute this statement as part of the module's documented control flow.
        save_game_state(GAME_ID, state)
        # Return the computed value to the caller.
        return {"spin": result, "debit": debit, "credit": credit, **payload(state)}
