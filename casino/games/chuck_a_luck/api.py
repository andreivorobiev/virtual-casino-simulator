"""Additive v1 router registration for the isolated Chuck-a-Luck module."""

# Import the canonical player-id validator used by current game endpoints.
from casino.core.validation import require_player_id
# Import the isolated ledger-only service facade.
from casino.games.chuck_a_luck.service import ChuckALuckService


# Resolve the player identity already bound by the shared authenticated router.
def request_player_id(body: dict, query: dict) -> str:
    # Prefer query because current main replaces it from bound_player_id before dispatch.
    player_id = query.get("player_id") or body.get("player_id") or "human"
    # Validate the resolved value without accepting an empty identity.
    return require_player_id({"player_id": player_id})


# Register game-owned routes for catalog discovery or direct focused tests.
def register(router, service=None):
    # Create the production service unless an isolated test supplies injected dependencies.
    game_service = service or ChuckALuckService()

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/chuck-a-luck/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query):
        # Resolve the router-bound player before any persisted state read.
        return game_service.state(request_player_id(body, query))

    # Register one atomic idempotent wager, roll, and settlement action.
    @router.post(r"/api/v1/games/chuck-a-luck/rolls")
    # Execute or replay the complete roll for the bound player.
    def rolls(body, query):
        # Resolve the router-bound player before state, entropy, or ledger access.
        return game_service.roll(request_player_id(body, query), body)

    # Return the service so focused tests can inspect injected adapters.
    return game_service
