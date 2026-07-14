"""Additive session-bound v1 routes for Three Card Poker.

Requirements: API-001 and SESSION-005.
"""

# Import the shared authenticated-player resolver used by every game request.
from casino.core.request_player import resolve_authenticated_player
# Import this game's replay-safe service.
from casino.games.three_card_poker.service import ThreeCardPokerService


# Resolve player identity through authenticated context before game access.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize direct-router tests and delegate precedence to the shared resolver.
    return resolve_authenticated_player(context or {}, body, query)


# Register only isolated Three Card Poker endpoints on a supplied router.
def register(router, service=None, *, test_seed=None):
    # Create production service ports unless focused tests inject a controller.
    game_service = service or ThreeCardPokerService(seed_factory=(lambda request_id: f"{test_seed}:{request_id}") if test_seed is not None else None)

    # Register the reload-safe authenticated state endpoint.
    @router.get(r"/api/v1/games/three-card-poker/state")
    # Return only the session-bound player's state.
    def state(body, query, context=None):
        # Resolve identity before any persistence or player read.
        player_id = request_player_id(body, query, context)
        # Reconcile pending work and return client-safe state.
        return game_service.state(player_id)

    # Register the idempotent initial deal endpoint.
    @router.post(r"/api/v1/games/three-card-poker/rounds")
    # Deal or replay one Ante and optional Pair Plus round.
    def rounds(body, query, context=None):
        # Resolve identity before interpreting wallet settings.
        player_id = request_player_id(body, query, context)
        # Delegate durable preparation and ledger reconciliation.
        return game_service.start_round(player_id, body)

    # Register the single terminal Play or Fold action endpoint.
    @router.post(r"/api/v1/games/three-card-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/decisions")
    # Apply or replay one decision for the bound player's round.
    def decisions(body, query, round_id, context=None):
        # Resolve identity before locating potentially private round state.
        player_id = request_player_id(body, query, context)
        # Delegate fingerprint validation and ordered ledger settlement.
        return game_service.decide(player_id, round_id, body)

    # Return the service for focused integration tests and diagnostics.
    return game_service
