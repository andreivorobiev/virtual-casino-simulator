"""Additive v1 router registration for the isolated Daily Draw Lab module on the settlement core. (#144)"""

# Import the canonical player-id validator used by current game endpoints.
from casino.core.validation import require_player_id
# Import the shared exactly-once wager-and-settle core.
from casino.core.simple_game import SimpleWagerGame
# Import this game's pure rules and immutable metadata.
from casino.games.daily_draw_lab import engine, rules


# Resolve the player identity already bound by the shared authenticated router.
def request_player_id(body: dict, query: dict) -> str:
    # Prefer query because current main replaces it from bound_player_id before dispatch.
    player_id = query.get("player_id") or body.get("player_id") or "human"
    # Validate the resolved value without accepting an empty identity.
    return require_player_id({"player_id": player_id})


# Build this game's settlement core bound to its pure rules.
def build_game() -> SimpleWagerGame:
    # Compose the shared core with Daily Draw Lab's entropy, validator, resolver, and public bet catalog.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="DAILY_DRAW_LAB_WAGER_DEBIT", settlement_transaction_type="DAILY_DRAW_LAB_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, public_bet_catalog=rules.bet_catalog)


# Register game-owned routes for catalog discovery or direct focused tests.
def register(router, service=None):
    # Create the production settlement core unless an isolated test supplies one.
    game = service or build_game()

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/daily-draw-lab/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query):
        # Resolve the router-bound player before any persisted state read.
        return game.state(request_player_id(body, query))

    # Register one atomic idempotent wager, draw, and settlement action.
    @router.post(r"/api/v1/games/daily-draw-lab/draws")
    # Execute or replay the complete draw for the bound player.
    def draws(body, query):
        # Resolve the router-bound player before state, entropy, or ledger access.
        return game.play(request_player_id(body, query), body)

    # Return the settlement core so focused tests can inspect it.
    return game
