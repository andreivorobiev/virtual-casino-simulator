"""Bounded, self-scoped round-replay artifacts derived from committed history. (#162)

Product direction (issue #162, 2026-07-23) fixes three rules this foundation enforces:

1. Replay snapshots are evidence/replay artifacts, never an alternate wallet or settlement source.
2. Retention is conservative and bounded: user-visible snapshots are kept for 30 days.
3. Replay and Practice Rewind (#159) are separate features that share this data foundation; this module
   is only the foundation and viewer feed, not the sandbox layer.

The foundation deliberately reads the already-committed authoritative history rather than writing a
second per-round store, so it can never disagree with settled outcomes and adds no write path into the
game flow. Every read derives its subject from the authenticated session, never from a caller id.
"""

# Import JSON parsing for the compact per-round detail already committed by the game flow.
import json
# Import date handling for the bounded retention window.
from datetime import datetime, timedelta, timezone

# Import the authoritative history the artifacts are derived from.
from casino.core import history
# Import the shared UTC clock so the retention window is deterministic in tests.
from casino.core.clock import utc_now
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError

# Keep user-visible replay artifacts for a conservative bounded window.
RETENTION_DAYS = 30
# Bound one page of replay artifacts so a caller can never request an unbounded read.
MAX_PAGE_SIZE = 25
# Return a stable default page size when the caller supplies none.
DEFAULT_PAGE_SIZE = 10
# Read a bounded history window large enough to paginate without loading unbounded rows.
HISTORY_READ_CEILING = 1000
# Publish only history fields that carry no durable identifier or internal audit material.
ARTIFACT_FIELDS = ("game", "bet_type", "bet_label", "amount", "outcome", "payout", "balance_after")


# Parse one caller-controlled pagination value without allowing malformed query text to become a 500.
def _bounded_positive_int(value, default: int, maximum: int | None = None) -> int:
    # Start protected conversion because HTTP query values arrive as untrusted strings.
    try:
        # Convert integer-compatible values through the canonical Python parser.
        parsed = int(value)
    # Replace missing, malformed, or object-shaped values with the documented default.
    except (TypeError, ValueError):
        # Preserve one deterministic fallback for every invalid representation.
        parsed = default
    # Clamp zero and negative values to the first valid position.
    parsed = max(1, parsed)
    # Apply the optional upper bound used by page sizes.
    if maximum is not None:
        # Prevent oversized caller values from widening the provider read.
        parsed = min(parsed, maximum)
    # Return the normalized positive integer.
    return parsed


# Resolve the ledger subject for one authenticated session without trusting caller input.
def _subject(user) -> str:
    # Read the session-bound player identity used to scope history.
    player_id = str((user or {}).get("player_id") or "")
    # Refuse to operate without an authenticated subject so nothing global is ever returned.
    if not player_id and not (user or {}).get("user_id"):
        # Fail closed rather than defaulting to a shared read.
        raise ValidationError("Replays require an authenticated session", {"reason": "no_subject"})
    # Return the ledger subject, which may be empty for a session with no bound player.
    return player_id


# Read the committed timestamp from a history row without trusting a single field name.
def _row_time(row) -> str:
    # Prefer the ledger-style short field, then the history timestamp field.
    return str(row.get("ts") or row.get("timestamp") or "")


# Report whether a committed row falls inside the retention window ending at the reference time.
def _within_retention(row, cutoff: str) -> bool:
    # Read the committed time.
    stamp = _row_time(row)
    # Keep a row without a parseable time rather than silently dropping recent history.
    if not stamp:
        # Treat an unstamped row as inside the window.
        return True
    # Compare lexically because both values are ISO-8601 UTC strings with identical shape.
    return stamp >= cutoff


# Derive the retention cutoff timestamp from the reference clock.
def _cutoff(now: str) -> str:
    # Parse the reference time, tolerating the trailing Z form used across the app.
    reference = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else datetime.now(timezone.utc)
    # Subtract the retention window.
    return (reference - timedelta(days=RETENTION_DAYS)).isoformat().replace("+00:00", "Z")


# Reduce one committed history row to a compact, identifier-free replay artifact.
def _artifact(row) -> dict:
    # Parse the compact committed detail, tolerating malformed stored JSON.
    try:
        # Read the structured per-round detail the game flow already committed.
        detail = json.loads(row.get("details_json") or "{}")
    # Treat unparsable detail as empty rather than failing the whole read.
    except (TypeError, ValueError):
        # Fall back to an empty detail.
        detail = {}
    # Publish only allowlisted presentation fields plus a bounded compact detail.
    artifact = {field: row.get(field) for field in ARTIFACT_FIELDS}
    # Attach the committed round time under one stable field name.
    artifact["occurred_at"] = _row_time(row)
    # Attach a short display reference rather than the raw durable round id.
    artifact["reference"] = str(row.get("round_id") or "")[-8:].upper()
    # Attach the bounded compact detail so the viewer can reconstruct the round shape.
    artifact["detail"] = detail if isinstance(detail, dict) else {}
    # State explicitly that this is a replay artifact and carries no cash value or settlement authority.
    artifact["settlement_authority"] = False
    # Return the compact artifact.
    return artifact


# Read the authenticated session's own bounded, in-retention replay artifacts.
def self_replays(user, *, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE, game: str = "", now: str = "") -> dict:
    # Derive the subject from the session only.
    player_id = _subject(user)
    # Resolve the reference clock, defaulting to now.
    reference = str(now or utc_now())
    # Preserve the historical zero-as-default behavior while rejecting malformed values safely.
    requested_size = page_size or DEFAULT_PAGE_SIZE
    # Clamp the caller-controlled page size into the accepted bounds.
    size = _bounded_positive_int(requested_size, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    # Clamp the caller-controlled page index so malformed or non-positive values cannot wrap the slice.
    index = _bounded_positive_int(page, 1)
    # Return an explicit empty page when the session has no ledger subject at all.
    if not player_id:
        # Publish a stable empty envelope rather than another player's rounds.
        return {"replays": [], "page": index, "page_size": size, "total": 0, "has_more": False, "retention_days": RETENTION_DAYS}
    # Read a bounded window of committed history, optionally narrowed to one game.
    rows = history.recent_history(HISTORY_READ_CEILING, game or None)
    # Keep only this subject's rows so a provider change can never leak another player.
    owned = [row for row in rows if str(row.get("player_id") or "") == player_id]
    # Compute the retention cutoff once.
    cutoff = _cutoff(reference)
    # Drop rows outside the conservative retention window.
    retained = [row for row in owned if _within_retention(row, cutoff)]
    # Order newest first so pagination stays stable and readable.
    ordered = list(reversed(retained))
    # Record the retained total before slicing.
    total = len(ordered)
    # Compute the slice start for the requested page.
    start = (index - 1) * size
    # Publish the bounded page of compact replay artifacts.
    return {"replays": [_artifact(row) for row in ordered[start:start + size]], "page": index, "page_size": size, "total": total, "has_more": start + size < total, "retention_days": RETENTION_DAYS}
