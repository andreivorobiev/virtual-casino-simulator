"""Additive v1 route registration for the isolated Hi-Lo module."""

# Import the shared authenticated player resolver so session binding always wins.
from casino.core.request_player import resolve_authenticated_player
# Import the game-local service that owns state and ledger orchestration.
from casino.games.hi_lo.service import HiLoService


# Resolve the identity already bound by the shared authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize optional context for direct focused route tests.
    request_context = context or {}
    # Delegate precedence and validation to the canonical shared player boundary.
    return resolve_authenticated_player(request_context, body, query)


# Register only game-owned routes without touching the shared application router.
def register(router, service=None, *, test_seed=None):
    # Build the production service unless a focused test injects one.
    game_service = service or HiLoService(seed_factory=(lambda action_id: f"{test_seed}:{action_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/hi-lo/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query, context=None):
        # Resolve the authenticated player before any state access.
        return game_service.state(request_player_id(body, query, context))

    # Register one idempotent wagered opening-card deal.
    @router.post(r"/api/v1/games/hi-lo/rounds")
    # Create or replay a prepared choice round.
    def rounds(body, query, context=None):
        # Resolve the authenticated player before any ledger access.
        return game_service.start_round(request_player_id(body, query, context), body)

    # Register one idempotent higher-or-lower settlement action.
    @router.post(r"/api/v1/games/hi-lo/rounds/(?P<round_id>[A-Za-z0-9_-]+)/guesses")
    # Reveal and settle the active bound-player round.
    def guesses(body, query, round_id, context=None):
        # Resolve the authenticated player before locating the round.
        return game_service.guess(request_player_id(body, query, context), round_id, body)

    # Return the service for focused tests and diagnostics.
    return game_service
