# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Additive v1 route registration for the isolated Joker Poker module."""

# Import the shared authenticated player resolver so session binding always wins.
from casino.core.request_player import resolve_authenticated_player
# Import the game-local service that owns state and ledger orchestration.
from casino.games.joker_poker.service import JokerPokerService


# Resolve the identity already bound by the shared authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize optional context for direct focused route tests.
    request_context = context or {}
    # Delegate precedence and validation to the canonical shared player boundary.
    return resolve_authenticated_player(request_context, body, query)


# Register only game-owned routes without touching the shared application router.
def register(router, service=None, *, test_seed=None):
    # Build the production service unless a focused test injects one.
    game_service = service or JokerPokerService(seed_factory=(lambda action_id: f"{test_seed}:{action_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/joker-poker/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query, context=None):
        # Resolve the authenticated player before any state access.
        return game_service.state(request_player_id(body, query, context))

    # Register one idempotent wagered source-hand deal.
    @router.post(r"/api/v1/games/joker-poker/rounds")
    # Create or replay a prepared Joker Poker round.
    def rounds(body, query, context=None):
        # Resolve the authenticated player before any ledger access.
        return game_service.start_round(request_player_id(body, query, context), body)

    # Register reload-safe held-card selection.
    @router.post(r"/api/v1/games/joker-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/holds")
    # Save held source positions for the bound player's active round.
    def holds(body, query, round_id, context=None):
        # Resolve the authenticated player before locating the round.
        return game_service.set_holds(request_player_id(body, query, context), round_id, body)

    # Register one idempotent draw and payout settlement action.
    @router.post(r"/api/v1/games/joker-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/draw")
    # Complete and settle the active bound-player round.
    def draw(body, query, round_id, context=None):
        # Resolve the authenticated player before locating or settling the round.
        return game_service.draw(request_player_id(body, query, context), round_id, body)

    # Return the service for focused tests and diagnostics.
    return game_service
