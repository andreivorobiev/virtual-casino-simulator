# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Additive session-bound v1 route adapter for Sic Bo issue #88."""

# Import canonical player-id validation for direct focused-test compatibility.
from casino.core.validation import require_player_id
# Import the isolated game service without touching shared registration files.
from casino.games.sic_bo.service import SicBoService


# Resolve authenticated context before compatibility body or query identities.
def request_player_id(body: dict, query: dict, context=None) -> str:
    # Normalize optional context for direct handler and legacy test invocation.
    request_context = context or {}
    # Prefer the shared router's resolved identity, then its bound session identity.
    context_player = request_context.get("resolved_player_id") or request_context.get("bound_player_id") or (request_context.get("user") or {}).get("player_id")
    # Preserve body/query fallback only when no authenticated binding exists.
    compatibility_player = body.get("player_id") or query.get("player_id") or "human"
    # Validate the authoritative context choice or legacy fallback.
    return require_player_id({"player_id": context_player or compatibility_player})


# Register only game-owned routes into a supplied catalog or focused-test router.
def register(router, service=None):
    # Create the production service unless an isolated test injects adapters.
    game_service = service or SicBoService()

    # Register the reload-safe state and immutable rules endpoint.
    @router.get(r"/api/v1/games/sic-bo/state")
    # Return state for the authenticated session player only.
    def state(body, query, context=None):
        # Resolve upstream session identity before loading player-owned state.
        player_id = request_player_id(body, query, context)
        # Return raw data for the shared standard success envelope.
        return game_service.payload(player_id)

    # Register one complete idempotent multi-position shake action.
    @router.post(r"/api/v1/games/sic-bo/rounds")
    # Debit, reveal, and settle one authenticated player's round.
    def rounds(body, query, context=None):
        # Resolve upstream session identity before state or ledger access.
        player_id = request_player_id(body, query, context)
        # Execute or recover the action through ledger-only orchestration.
        return game_service.play(player_id, body)

    # Return the service for focused integration tests and deterministic seams.
    return game_service
