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

# Import the shared self-scoped ledger reader so receipts reuse one privacy and pagination boundary.
from casino.core import self_history as activity

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
# Re-export the shared page ceiling for the receipt route and compatibility callers.
MAX_PAGE_SIZE = activity.MAX_PAGE_SIZE
# Re-export the shared default page size for the receipt route adapter.
DEFAULT_PAGE_SIZE = activity.DEFAULT_PAGE_SIZE


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
    # Delegate to the one accepted privacy-safe reference boundary shared with personal history.
    return activity.display_reference(round_id)


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
    interrupted = category == CATEGORY_REFUND and transaction_type.strip().upper().endswith(INTERRUPTED_SUFFIX)
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
def self_receipts(user, *, page=1, page_size=DEFAULT_PAGE_SIZE) -> dict:
    # Read the reusable owned page through the privacy boundary merged by the My Settings foundation.
    bounded = activity.read_page(user, page=page, page_size=page_size)
    # Remove trusted raw ledger rows before publishing the receipt-specific envelope.
    rows = bounded.pop("rows")
    # Publish one ledger-derived explanation per committed row plus shared pagination metadata.
    return {"receipts": [explain(row) for row in rows], **bounded}
