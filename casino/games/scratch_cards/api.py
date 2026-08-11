# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Additive v1 route registration for the isolated Scratch Cards module."""

# Import canonical player-id validation for legacy focused-router compatibility.
from casino.core.validation import require_player_id
# Import the isolated service that owns private state and ledger orchestration.
from casino.games.scratch_cards.service import ScratchCardsService

# Reuse one stateless service facade across registered route calls.
SERVICE = ScratchCardsService()


# Resolve the authoritative upstream session player before every game action.
def request_player_id(body, query, context=None) -> str:
    # Normalize optional request context for direct focused-handler tests.
    context = context or {}
    # Prefer the router-published identity, then its authenticated binding, before compatibility inputs.
    player_id = context.get("resolved_player_id") or context.get("bound_player_id") or body.get("player_id") or query.get("player_id") or "human"
    # Validate and return the single game player identity.
    return require_player_id({"player_id": player_id})


# Register game-owned endpoints without touching the shared application or registry.
def register(router):
    # Attach the reload-safe state endpoint through the existing router contract.
    @router.get(r"/api/v1/games/scratch-cards/state")
    # Return only the authenticated player's masked ticket state.
    def state(body, query, context=None):
        # Resolve the session-owned player with absolute context precedence.
        player_id = request_player_id(body, query, context)
        # Return raw data for the shared standard success envelope.
        return SERVICE.state(player_id)

    # Attach one retry-safe wager action for creating a private card.
    @router.post(r"/api/v1/games/scratch-cards/cards")
    # Prepare, debit, and return one masked card.
    def start_card(body, query, context=None):
        # Resolve the session-owned player with absolute context precedence.
        player_id = request_player_id(body, query, context)
        # Execute the purchase through the ledger-only game service.
        return SERVICE.start_card(player_id, body)

    # Attach partial reveal and final settlement to a player-owned card identity.
    @router.post(r"/api/v1/games/scratch-cards/cards/(?P<card_id>[A-Za-z0-9_-]+)/scratches")
    # Persist requested cells and settle only when all nine are visible.
    def scratch(body, query, card_id, context=None):
        # Resolve the session-owned player with absolute context precedence.
        player_id = request_player_id(body, query, context)
        # Execute the replay-safe reveal through the isolated service.
        return SERVICE.scratch(player_id, card_id, body)
