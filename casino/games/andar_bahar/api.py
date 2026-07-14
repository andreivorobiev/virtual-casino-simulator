"""Additive v1 route proposal for the isolated Andar Bahar module."""

# Import the shared authenticated player resolver so session binding always wins.
from casino.core.request_player import resolve_authenticated_player
# Import the game-local service that owns state and ledger orchestration.
from casino.games.andar_bahar.service import AndarBaharService


# Resolve the identity already bound by the shared authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize optional context for direct focused route tests.
    request_context = context or {}
    # Delegate precedence and validation to the canonical shared player boundary.
    return resolve_authenticated_player(request_context, body, query)


# Register only game-owned routes without touching the shared application router.
def register(router, service=None, *, test_seed=None):
    # Build the production service unless a focused test injects one.
    game_service = service or AndarBaharService(seed_factory=(lambda action_id: f"{test_seed}:{action_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/andar-bahar/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query, context=None):
        # Resolve the authenticated player before any state access.
        return game_service.state(request_player_id(body, query, context))

    # Register one idempotent wagered Andar/Bahar play action.
    @router.post(r"/api/v1/games/andar-bahar/rounds")
    # Create or replay a complete match-rank round.
    def rounds(body, query, context=None):
        # Resolve the authenticated player before any ledger access.
        return game_service.play(request_player_id(body, query, context), body)

    # Return the service for focused tests and diagnostics.
    return game_service
