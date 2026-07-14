"""Additive v1 router registration for the isolated Big Six Wheel module."""

# Import canonical player-id validation used by all existing v1 game handlers.
from casino.core.validation import require_player_id
# Import the isolated service that owns state and ledger orchestration.
from casino.games.big_six_wheel.service import BigSixWheelService

# Reuse one stateless service facade across route calls.
SERVICE = BigSixWheelService()


# Resolve the upstream-bound player id while retaining legacy focused-test compatibility.
def request_player_id(body, query, context=None) -> str:
    # Normalize direct-router tests and callers that predate the shared request context.
    context = context or {}
    # Prefer the authenticated resolver outputs before any compatibility body or query identity.
    player_id = context.get("resolved_player_id") or context.get("bound_player_id") or body.get("player_id") or query.get("player_id") or "human"
    # Validate the selected identifier through the shared player-id boundary.
    return require_player_id({"player_id": player_id})


# Register the game-owned endpoints without touching the shared application router.
def register(router):
    # Attach the state endpoint through the existing router decorator contract.
    @router.get(r"/api/v1/games/big-six-wheel/state")
    # Return session-owned state, rules, and settled history.
    def state(body, query, context=None):
        # Resolve the player identity already bound by the shared authenticated game router.
        player_id = request_player_id(body, query, context)
        # Return raw data for the router's standard success envelope.
        return SERVICE.state(player_id)

    # Attach one idempotent spin action through the existing router decorator contract.
    @router.post(r"/api/v1/games/big-six-wheel/spins")
    # Debit, resolve, and settle one complete atomic game action.
    def spin(body, query, context=None):
        # Resolve the player identity already bound by the shared authenticated game router.
        player_id = request_player_id(body, query, context)
        # Execute the request through the ledger-only service.
        return SERVICE.spin(player_id, body)
