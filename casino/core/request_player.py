# Provide one session-aware player resolver for current and future game endpoints.
from casino.core.validation import require_player_id  # Reuse canonical player-id validation.


# Resolve the only player id a game request may use under the authenticated request context.
def resolve_authenticated_player(context, body=None, query=None, default_player_id="human"):
    body = body or {}  # Normalize missing request bodies for read-only game endpoints.
    query = query or {}  # Normalize missing query mappings for action endpoints.
    bound_player_id = context.get("bound_player_id")  # Read the non-Admin session binding established by the handler.
    user_player_id = (context.get("user") or {}).get("player_id")  # Retain a safe fallback for authenticated contexts.
    requested_player_id = body.get("player_id") or query.get("player_id") or user_player_id or default_player_id  # Preserve Admin/test compatibility when no binding applies.
    player_id = bound_player_id or requested_player_id  # Give the authenticated session binding absolute precedence.
    return require_player_id({"player_id": player_id})  # Validate and return the canonical game player id.
