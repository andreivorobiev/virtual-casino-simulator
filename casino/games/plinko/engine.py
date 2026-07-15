"""Server-authoritative Plinko rules accepted for GitHub issue #136.

Permanent requirements: PLINKO-001 through PLINKO-005.
"""

# Import hashing so round ids are stable without exposing raw player ids.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math
# Import deterministic random support for the injectable test seam.
import random

# Import public validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger event owned by Plinko.
GAME_ID = "plinko"
# Fix the accepted rules profile to an eight-row pegboard.
ROWS = 8
# Publish transparent bucket multipliers from left edge to right edge.
MULTIPLIERS = (0.2, 0.5, 1.0, 1.5, 2.0, 5.0, 2.0, 1.5, 1.0)
# Bound reload-safe history so one player document remains compact.
RECENT_DROP_LIMIT = 20


# Build one fresh player-scoped Plinko state document.
def default_state() -> dict:
    # Return bounded history and durable action receipts for retry safety.
    return {"recent_drops": [], "action_receipts": {}}


# Normalize one positive play-token wager before any ledger movement.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numbers.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Plinko wager must be a positive play-token amount")
    # Convert supported numeric input into two-decimal ledger precision.
    try:
        # Round the amount to match shared ledger precision.
        wager = round(float(value), 2)
    # Translate missing or malformed values into a stable public error.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Plinko wager must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge ledger amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Report the accepted fake-token range.
        raise ValidationError("Plinko wager must be between 0.01 and 100000 play tokens")
    # Return the normalized wager used for fingerprints and settlement.
    return wager


# Derive one stable drop id from authenticated player and action identity.
def drop_id_for(player_id: str, action_id: str) -> str:
    # Hash namespaced input so hostile characters never enter persisted ids.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Return a compact id with enough digest material for local simulator uniqueness.
    return f"plinko_{digest[:24]}"


# Produce one committed peg path using production randomness or a deterministic seed.
def committed_path(*, seed=None) -> list[str]:
    # Use a local random generator so tests can inject deterministic paths.
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    # Return one left/right decision for each peg row.
    return ["R" if rng.randrange(2) else "L" for _ in range(ROWS)]


# Convert a committed path into its terminal bucket index.
def bucket_for_path(path: list[str]) -> int:
    # Validate the path shape before deriving the settlement bucket.
    if not isinstance(path, list) or len(path) != ROWS or any(step not in ("L", "R") for step in path):
        # Reject impossible or client-authored paths.
        raise ValidationError("Plinko path must contain the committed peg decisions")
    # Count right bounces to locate the zero-based bucket.
    return sum(1 for step in path if step == "R")


# Return the multiplier assigned to one terminal bucket.
def multiplier_for_bucket(bucket: int) -> float:
    # Reject any bucket outside the fixed profile.
    if not isinstance(bucket, int) or bucket < 0 or bucket >= len(MULTIPLIERS):
        # Keep impossible outcomes out of settlement.
        raise ValidationError("Plinko bucket is outside the rules profile")
    # Return the transparent bucket multiplier.
    return MULTIPLIERS[bucket]


# Build one authoritative drop result without touching the player wallet.
def create_drop(player_id: str, wager, action_id: str, *, path: list[str], drop_id: str, created_at: str, request_fingerprint: str) -> dict:
    # Normalize the wager at the pure engine boundary.
    amount = normalize_wager(wager)
    # Derive the terminal bucket from the server-committed path.
    bucket = bucket_for_path(path)
    # Read the transparent multiplier for that bucket.
    multiplier = multiplier_for_bucket(bucket)
    # Calculate returned play tokens after the committed outcome.
    payout = round(amount * multiplier, 2)
    # Return JSON-compatible state that animation can only replay.
    return {
        "drop_id": drop_id,  # Correlate state, API responses, and ledger rows.
        "player_id": player_id,  # Bind the result to the authenticated player.
        "action_id": action_id,  # Preserve the client retry identity.
        "request_fingerprint": request_fingerprint,  # Detect changed retries.
        "wager": amount,  # Store the exact debited play-token amount.
        "path": list(path),  # Commit the full peg path for client replay.
        "bucket": bucket,  # Publish the terminal bucket index.
        "multiplier": multiplier,  # Publish the transparent payout multiplier.
        "payout": payout,  # Store the returned-token amount.
        "net": round(payout - amount, 2),  # Store net result after the wager.
        "phase": "settled",  # Plinko resolves in one server-authoritative action.
        "debit_status": "pending",  # Require service ledger proof.
        "settlement_status": "pending" if payout else "complete",  # Skip zero credits.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Find a retained drop by its stable action identity.
def drop_for_action(state: dict, action_id: str):
    # Search newest-first through bounded history.
    return next((item for item in reversed(state.get("recent_drops", [])) if item.get("action_id") == action_id), None)


# Archive or replace one completed drop in bounded reload-safe history.
def archive_drop(state: dict, drop: dict) -> None:
    # Remove any older copy of this drop before appending.
    recent = [item for item in state.get("recent_drops", []) if item.get("drop_id") != drop.get("drop_id")]
    # Append the newest result in chronological order.
    recent.append(drop)
    # Retain only the bounded newest results.
    state["recent_drops"] = recent[-RECENT_DROP_LIMIT:]


# Remove internal retry fingerprints from one public drop payload.
def public_drop(drop):
    # Preserve null-like callers without creating placeholders.
    if drop is None:
        # Return JSON null through the router.
        return None
    # Exclude internal semantic fingerprints from public responses.
    return {key: value for key, value in drop.items() if key != "request_fingerprint"}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return bounded settled history while preserving storage schema metadata.
    return {
        # Sanitize each retained drop before it leaves the game boundary.
        "recent_drops": [public_drop(item) for item in state.get("recent_drops", [])],
        # Preserve shared storage schema metadata when it exists.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),
    }


# Replay one already-settled drop or reject a changed retry.
def assert_replay(drop: dict, fingerprint: str) -> None:
    # Reject an action id reused with a changed semantic request.
    if drop.get("request_fingerprint") != fingerprint:
        # Preserve the original committed outcome.
        raise ConflictError("action_id was already used with a different Plinko wager")
