"""Additive v1 router registration for the isolated Crown and Anchor module."""

# Import canonical player-id validation used by existing v1 game handlers.
from casino.core.validation import require_player_id
# Import the isolated service that owns state and ledger orchestration.
from casino.games.crown_and_anchor.service import CrownAndAnchorService

# Reuse one stateless service facade across route calls.
SERVICE = CrownAndAnchorService()


# Resolve the trusted session player while ignoring caller-supplied body or query ids.
def request_player_id(body, query, context=None) -> str:
    # Normalize direct-router tests and callers that omit request context.
    context = context or {}
    # Read the router-resolved identity established by shared request binding.
    resolved_player_id = context.get("resolved_player_id")
    # Read the normal authenticated binding established before game handlers run.
    bound_player_id = context.get("bound_player_id")
    # Retain the authenticated user fallback for compatible direct handler calls.
    user_player_id = (context.get("user") or {}).get("player_id")
    # Use trusted context only; body and query player_id values cannot override the session.
    player_id = bound_player_id or user_player_id or resolved_player_id or "human"
    # Validate the selected identifier through the shared player-id boundary.
    return require_player_id({"player_id": player_id})


# Register game-owned endpoints without touching the shared application router.
def register(router, service=None):
    # Use the production service unless focused tests inject an in-memory controller.
    active_service = service or SERVICE

    # Attach the reload-safe state endpoint through the existing router decorator contract.
    @router.get(r"/api/v1/games/crown-and-anchor/state")
    # Return session-owned state, rules, paytable, and settled history.
    def state(body, query, context=None):
        # Resolve the player identity already bound by the shared authenticated router.
        player_id = request_player_id(body, query, context)
        # Return raw data for the router's standard success envelope.
        return active_service.state(player_id)

    # Attach one idempotent play action through the existing router decorator contract.
    @router.post(r"/api/v1/games/crown-and-anchor/rounds")
    # Debit, roll, and settle one complete atomic Crown and Anchor action.
    def rounds(body, query, context=None):
        # Resolve the player identity already bound by the shared authenticated router.
        player_id = request_player_id(body, query, context)
        # Execute the request through the ledger-only service.
        return active_service.play(player_id, body)

    # Return the service so focused tests can inspect injected adapters.
    return active_service

