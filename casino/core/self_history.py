"""Reusable self-scoped ledger pagination for authenticated player surfaces. (#352)

This module owns only the privacy and pagination boundary shared by personal history and later
player-facing receipt views. It does not become another ledger authority: every row comes from the
configured ledger provider, is rechecked against the session-bound player, and is returned newest
first through one bounded page shape.
"""

# Import callable typing for the optional surface-owned row filter.
from collections.abc import Callable

# Import the authoritative ledger facade instead of reading provider files directly.
from casino.core import ledger

# Bound every self-service page so a hostile query cannot request an unbounded ledger read.
MAX_PAGE_SIZE = 50
# Use one stable default across current and future self-history surfaces.
DEFAULT_PAGE_SIZE = 20
# Bound the source window independently from the caller-controlled page size.
LEDGER_READ_CEILING = 1000
# Publish only a short correlation tail instead of a raw durable round identifier.
REFERENCE_LENGTH = 8


# Parse one caller-controlled pagination value without allowing malformed strings to become a 500.
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


# Derive one non-secret display reference from an optional durable round identifier.
def display_reference(round_id) -> str:
    # Normalize the provider value without trusting its type.
    raw = str(round_id or "")
    # Publish no placeholder when the ledger movement has no round binding.
    if not raw:
        # Return the explicit empty reference.
        return ""
    # Return only the short uppercase tail so the durable identifier is never republished.
    return raw[-REFERENCE_LENGTH:].upper()


# Read one bounded newest-first ledger page for the session-bound player.
def read_page(user, *, page=1, page_size=DEFAULT_PAGE_SIZE, row_filter: Callable[[dict], bool] | None = None) -> dict:
    # Resolve the ledger subject from authenticated server context only.
    player_id = str((user or {}).get("player_id") or "")
    # Normalize the caller-controlled page index.
    index = _bounded_positive_int(page, 1)
    # Preserve the historical zero-as-default behavior while rejecting every malformed value safely.
    requested_size = page_size or DEFAULT_PAGE_SIZE
    # Clamp the caller-controlled page size to the shared ceiling.
    size = _bounded_positive_int(requested_size, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    # Return an explicit empty page when the authenticated principal has no ledger subject.
    if not player_id:
        # Publish the reusable internal page shape without exposing any other player's rows.
        return {"rows": [], "page": index, "page_size": size, "total": 0, "has_more": False}
    # Read only the bounded source window for the session-derived player identity.
    rows = ledger.read_recent(player_id, LEDGER_READ_CEILING)
    # Recheck ownership after the provider read so a future provider regression cannot leak a neighbour.
    owned = [row for row in rows if str(row.get("player_id") or "") == player_id]
    # Apply only the surface-owned filter after the mandatory ownership filter.
    filtered = [row for row in owned if row_filter(row)] if row_filter is not None else owned
    # Convert the provider's chronological result into stable newest-first presentation order.
    ordered = list(reversed(filtered))
    # Compute the bounded offset from normalized pagination inputs.
    start = (index - 1) * size
    # Slice only the requested page from the bounded owned window.
    selected = ordered[start:start + size]
    # Return raw owned rows only to the trusted surface mapper plus reusable pagination metadata.
    return {"rows": selected, "page": index, "page_size": size, "total": len(ordered), "has_more": start + size < len(ordered)}
