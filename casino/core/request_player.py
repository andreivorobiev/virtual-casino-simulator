# Provide one session-aware player resolver for current and future game endpoints.
from casino.core.validation import require_player_id  # Reuse canonical player-id validation.


# Enumerate fields that a hostile game client may never authoritatively supply.
PROTECTED_GAME_FIELDS = frozenset({
    # Protect identity, privilege, and wallet ownership from mass assignment.
    "user_id", "role", "roles", "admin", "is_admin", "wallet_id", "balance", "token_balance",
    # Protect generated outcomes, settlement values, and random inputs from client control.
    "result", "force_result", "outcome", "payout", "winnings", "settlement", "settlement_total", "rng", "rng_seed", "seed", "random_seed",
    # Protect server-owned decks, dice, wheels, reels, bonus state, and round control fields.
    "card_order", "cards", "deck", "shoe", "dice", "reels", "reel_positions", "pocket", "wheel_pocket", "win", "win_state", "free_spins", "bonus", "jackpot", "state", "phase", "turn", "version",
})


# Remove protected game fields while preserving documented bounded intent and v1 compatibility extras.
def sanitize_game_intent(body=None) -> dict:
    # Copy the request so shared callers never retain a server-mutated hostile payload.
    sanitized = dict(body or {})
    # Inspect every supplied key without trusting its type or punctuation form.
    for key in tuple(sanitized):
        # Normalize hyphenated and mixed-case aliases before the protected-field comparison.
        normalized = str(key).strip().lower().replace("-", "_")
        # Remove every protected field so game code can only consume bounded intent.
        if normalized in PROTECTED_GAME_FIELDS:
            # Delete the original key while leaving allowed intent fields unchanged.
            sanitized.pop(key, None)
    # Return the canonical request projection used by the router.
    return sanitized


# Resolve the only player id a game request may use under the authenticated request context.
def resolve_authenticated_player(context, body=None, query=None, default_player_id="human"):
    body = body or {}  # Normalize missing request bodies for read-only game endpoints.
    query = query or {}  # Normalize missing query mappings for action endpoints.
    bound_player_id = context.get("bound_player_id")  # Read the non-Admin session binding established by the handler.
    user_player_id = (context.get("user") or {}).get("player_id")  # Retain a safe fallback for authenticated contexts.
    requested_player_id = body.get("player_id") or query.get("player_id") or user_player_id or default_player_id  # Preserve Admin/test compatibility when no binding applies.
    player_id = bound_player_id or requested_player_id  # Give the authenticated session binding absolute precedence.
    return require_player_id({"player_id": player_id})  # Validate and return the canonical game player id.
