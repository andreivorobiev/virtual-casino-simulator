# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Additive v1 route registration for the isolated Over/Under 7 module."""

# Import the shared authenticated player resolver so session binding always wins.
from casino.core.request_player import resolve_authenticated_player
# Import the game-local service that owns state and ledger orchestration.
from casino.games.over_under_7.service import OverUnder7Service


# Resolve the identity already bound by the shared authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize optional context for direct focused route tests.
    request_context = context or {}
    # Delegate precedence and validation to the canonical shared player boundary.
    return resolve_authenticated_player(request_context, body, query)


# Register only game-owned routes without touching the shared application router.
def register(router, service=None):
    # Build the production service unless a focused test injects one.
    game_service = service or OverUnder7Service()

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/over-under-7/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query, context=None):
        # Resolve the authenticated player before any state access.
        return game_service.state(request_player_id(body, query, context))

    # Register one idempotent dice play endpoint.
    @router.post(r"/api/v1/games/over-under-7/plays")
    # Debit, roll, settle, and replay one complete proposition action.
    def plays(body, query, context=None):
        # Resolve the authenticated player before any ledger access.
        return game_service.play(request_player_id(body, query, context), body)

    # Return the service for focused tests and diagnostics.
    return game_service
