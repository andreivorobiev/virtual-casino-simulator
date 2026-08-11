# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Additive v1 Dragon Tiger routes with authenticated player binding."""

# Import canonical player-ID validation for direct-router compatibility.
from casino.core.validation import require_player_id
# Import the game-local service facade.
from casino.games.dragon_tiger.service import DragonTigerService


# Resolve only the player identity already bound by shared request handling.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize direct focused-test callers.
    context = context or {}
    # Read the authenticated user's canonical player even for Admin sessions that lack a shared binding.
    authenticated_player_id = (context.get("user") or {}).get("player_id")
    # Prefer authenticated identity over resolver output that may preserve Admin compatibility inputs.
    player_id = context.get("bound_player_id") or authenticated_player_id or context.get("resolved_player_id") or body.get("player_id") or query.get("player_id") or "human"
    # Validate the selected canonical player identity.
    return require_player_id({"player_id": player_id})


# Register game-owned endpoints without editing the shared application router.
def register(router, service=None):
    # Use production orchestration unless a focused test injects a fake.
    game_service = service or DragonTigerService()

    # Register the authenticated player's reload-safe state endpoint.
    @router.get(r"/api/v1/games/dragon-tiger/state")
    # Return only the resolved player's game state.
    def state(body, query, context=None):
        # Delegate recovery and public payload construction.
        return game_service.state(request_player_id(body, query, context))

    # Register one atomic replay-safe single-bet round endpoint.
    @router.post(r"/api/v1/games/dragon-tiger/rounds")
    # Deal and settle one standard-8d round.
    def start_round(body, query, context=None):
        # Resolve authenticated ownership before state or ledger access.
        player_id = request_player_id(body, query, context)
        # Delegate normalized action handling to the service.
        return game_service.play(player_id, body)

    # Return the service for focused integration tests.
    return game_service
