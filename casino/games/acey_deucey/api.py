"""Additive v1 route registration for catalog-integrated Acey-Deucey."""

# Import the shared authenticated player resolver so session binding wins.
from casino.core.request_player import resolve_authenticated_player
# Import the game-local service that owns state and ledger orchestration.
from casino.games.acey_deucey.service import AceyDeuceyService


# Resolve the identity already bound by the authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize optional context for focused route tests.
    request_context = context or {}
    # Delegate precedence and validation to the canonical session boundary.
    return resolve_authenticated_player(request_context, body, query)


# Register only game-owned additive routes.
def register(router, service=None, *, test_seed=None):
    # Build the production service unless a focused test injects one.
    game_service = service or AceyDeuceyService(seed_factory=(lambda action_id: f"{test_seed}:{action_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/acey-deucey/state")
    # Return state for the authenticated player.
    def state(body, query, context=None):
        # Resolve session-bound player identity before state access.
        return game_service.state(request_player_id(body, query, context))

    # Register one free boundary-card deal.
    @router.post(r"/api/v1/games/acey-deucey/rounds")
    # Create or replay a prepared boundary deal.
    def rounds(body, query, context=None):
        # Resolve session-bound player identity before state mutation.
        return game_service.deal(request_player_id(body, query, context), body)

    # Register one wagered play against a prepared deal.
    @router.post(r"/api/v1/games/acey-deucey/rounds/(?P<round_id>[A-Za-z0-9_-]+)/play")
    # Reveal and settle the active player-owned round.
    def play(body, query, round_id, context=None):
        # Resolve session-bound player identity before ledger movement.
        return game_service.play(request_player_id(body, query, context), round_id, body)

    # Register one pass action that closes the deal without wallet movement.
    @router.post(r"/api/v1/games/acey-deucey/rounds/(?P<round_id>[A-Za-z0-9_-]+)/pass")
    # Pass the active player-owned round.
    def pass_action(body, query, round_id, context=None):
        # Resolve session-bound player identity before state mutation.
        return game_service.pass_round(request_player_id(body, query, context), round_id, body)

    # Return the service for focused tests and diagnostics.
    return game_service
