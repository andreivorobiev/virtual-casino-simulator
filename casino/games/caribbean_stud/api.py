"""Additive v1 route registration for the isolated Caribbean Stud module."""

# Import the shared authenticated player resolver so session binding always wins.
from casino.core.request_player import resolve_authenticated_player
# Import the game-local service that owns state and ledger orchestration.
from casino.games.caribbean_stud.service import CaribbeanStudService


# Resolve the identity already bound by the shared authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize optional context for direct focused route tests.
    request_context = context or {}
    # Delegate precedence and validation to the canonical shared player boundary.
    return resolve_authenticated_player(request_context, body, query)


# Register only game-owned routes without touching the shared application router.
def register(router, service=None, *, test_seed=None):
    # Build the production service unless a focused test injects one.
    game_service = service or CaribbeanStudService(shoe_factory=(lambda action_id: None) if test_seed is None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/caribbean-stud/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query, context=None):
        # Resolve the authenticated player before any state access.
        return game_service.state(request_player_id(body, query, context))

    # Register one idempotent ante-backed deal.
    @router.post(r"/api/v1/games/caribbean-stud/rounds")
    # Create or replay a prepared Caribbean Stud round.
    def rounds(body, query, context=None):
        # Resolve the authenticated player before any ledger access.
        return game_service.deal(request_player_id(body, query, context), body)

    # Register one idempotent call decision.
    @router.post(r"/api/v1/games/caribbean-stud/rounds/(?P<round_id>[A-Za-z0-9_-]+)/call")
    # Reveal and settle the active bound-player round.
    def call(body, query, round_id, context=None):
        # Resolve the authenticated player before locating the round.
        return game_service.call(request_player_id(body, query, context), round_id, body)

    # Register one idempotent fold decision.
    @router.post(r"/api/v1/games/caribbean-stud/rounds/(?P<round_id>[A-Za-z0-9_-]+)/fold")
    # Forfeit the ante without revealing the dealer hand.
    def fold(body, query, round_id, context=None):
        # Resolve the authenticated player before locating the round.
        return game_service.fold(request_player_id(body, query, context), round_id, body)

    # Return the service for focused tests and diagnostics.
    return game_service
