"""Player-facing explanations derived from committed play-token ledger movements. (#161)

Every receipt is derived from data the ledger already committed: the signed amount, the transaction
type, the game, and the resulting balance. Nothing is inferred from client state, so a receipt can
never disagree with the authoritative balance it explains.

Classification is deliberately driven by the signed amount first and refined by the committed
transaction type second. The catalog is still expanding, so a per-game lookup table would silently
rot; instead an unrecognized transaction type degrades to a correct generic movement receipt rather
than a confidently wrong specific one. Receipts publish localization codes and allowlisted
parameters rather than prose, so EN and RU copy stays in the shell resources.
"""

# Import the authoritative ledger so receipts read committed movements only.
from casino.core import ledger

# Publish one stable code per explained movement category.
CATEGORY_STAKE = "stake"
# Publish the returned-wager category.
CATEGORY_REFUND = "refund"
# Publish the winning-settlement category.
CATEGORY_PAYOUT = "payout"
# Publish the balance-adjustment category used by grants and top-ups.
CATEGORY_ADJUSTMENT = "adjustment"

# Map each category to the localization key the shell renders.
MESSAGE_KEYS = {
    # Explain play tokens staked on a wager.
    CATEGORY_STAKE: "receipt.stake",
    # Explain play tokens returned without a settlement.
    CATEGORY_REFUND: "receipt.refund",
    # Explain play tokens won from a settled round.
    CATEGORY_PAYOUT: "receipt.payout",
    # Explain a balance adjustment that is not a wager outcome.
    CATEGORY_ADJUSTMENT: "receipt.adjustment",
}

# Mark transaction types that returned a stake because a round could not be completed.
INTERRUPTED_SUFFIX = "_AFTER_ERROR"
# Recognize the committed vocabulary that returns a previously staked wager.
REFUND_MARKER = "REFUND"
# Recognize the committed vocabulary that adds tokens outside gameplay.
ADJUSTMENT_MARKERS = ("_ADDED", "_GRANT")
# Bound one receipt read so a caller can never request an unbounded explanation set.
MAX_PAGE_SIZE = 50
# Return a stable default page size when the caller supplies none.
DEFAULT_PAGE_SIZE = 20
# Read a bounded ledger window large enough to paginate without loading unbounded history.
LEDGER_READ_CEILING = 1000
# Publish a short display reference rather than a raw durable round identifier.
REFERENCE_LENGTH = 8


# Classify one committed movement into a player-meaningful category.
def classify(transaction_type: str, amount: float) -> str:
    # Normalize the committed type without trusting its case or padding.
    kind = str(transaction_type or "").strip().upper()
    # Read the authoritative signed movement.
    value = float(amount or 0)
    # Treat any committed refund vocabulary as a returned wager regardless of direction.
    if REFUND_MARKER in kind:
        # Report the returned-wager category.
        return CATEGORY_REFUND
    # Treat an explicit non-gameplay credit as a balance adjustment.
    if value > 0 and any(kind.endswith(marker) for marker in ADJUSTMENT_MARKERS):
        # Report the adjustment category.
        return CATEGORY_ADJUSTMENT
    # Treat every other incoming movement as a settlement payout.
    if value > 0:
        # Report the payout category.
        return CATEGORY_PAYOUT
    # Treat every outgoing movement as a staked wager.
    if value < 0:
        # Report the stake category.
        return CATEGORY_STAKE
    # Treat a zero movement as an adjustment so an explanation still exists.
    return CATEGORY_ADJUSTMENT


# Derive a short display reference so a player can correlate a receipt without a raw identifier.
def _reference(round_id) -> str:
    # Normalize the committed round value.
    raw = str(round_id or "")
    # Publish nothing when the movement is not bound to a round.
    if not raw:
        # Return the explicit empty reference.
        return ""
    # Return only a short uppercase tail so the durable identifier is never republished.
    return raw[-REFERENCE_LENGTH:].upper()


# Build one player-facing receipt from a committed ledger row.
def explain(row) -> dict:
    # Treat a missing row as an unexplainable movement rather than raising into a player surface.
    record = row if isinstance(row, dict) else {}
    # Read the authoritative signed amount.
    amount = float(record.get("amount") or 0)
    # Read the committed transaction type.
    transaction_type = str(record.get("transaction_type") or "")
    # Classify the movement from committed data only.
    category = classify(transaction_type, amount)
    # Note when a stake was returned because the round could not be completed.
    interrupted = transaction_type.strip().upper().endswith(INTERRUPTED_SUFFIX)
    # Publish the localization code plus allowlisted parameters the shell will render.
    return {
        # Name the movement category.
        "category": category,
        # Name the localization key rather than emitting prose from the server.
        "message_key": "receipt.refund_after_error" if interrupted else MESSAGE_KEYS[category],
        # Publish the game whose round produced this movement.
        "game": str(record.get("game") or ""),
        # Publish the unsigned magnitude for display alongside a direction.
        "amount": round(abs(amount), 2),
        # Publish the authoritative direction of the committed movement.
        "direction": "debit" if amount < 0 else "credit",
        # Publish the authoritative balance the ledger recorded after this movement.
        "balance_after": record.get("balance_after"),
        # Publish the committed movement time.
        "occurred_at": record.get("ts"),
        # Publish only a short correlation reference, never the raw round identifier.
        "reference": _reference(record.get("round_id")),
        # State explicitly that every explained amount is a play token with no cash value.
        "play_tokens_only": True,
    }


# Read the authenticated session's own bounded, explained movements.
def self_receipts(user, *, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    # Resolve the ledger subject from the session only, never from a caller-supplied identifier.
    player_id = str((user or {}).get("player_id") or "")
    # Clamp the page size into the accepted bounds.
    size = max(1, min(int(page_size or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
    # Clamp the page index so a negative or zero page cannot wrap the slice.
    index = max(1, int(page or 1))
    # Return an explicit empty page when the session has no ledger subject.
    if not player_id:
        # Publish a stable empty envelope rather than another player's movements.
        return {"receipts": [], "page": index, "page_size": size, "total": 0, "has_more": False}
    # Read only this player's committed movements.
    rows = ledger.read_recent(player_id, LEDGER_READ_CEILING)
    # Drop any row not bound to this subject so a provider change can never leak another player.
    owned = [row for row in rows if str(row.get("player_id") or "") == player_id]
    # Order newest first so pagination stays stable and readable.
    ordered = list(reversed(owned))
    # Compute the slice start for the requested page.
    start = (index - 1) * size
    # Publish the bounded page of explanations.
    return {"receipts": [explain(row) for row in ordered[start:start + size]], "page": index, "page_size": size, "total": len(ordered), "has_more": start + size < len(ordered)}
