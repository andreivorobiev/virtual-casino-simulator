"""Route-free exactly-once settlement adapter for shared game cores. (issue #430)

The storage provider already owns atomic action identity, balance mutation, and durable
ledger projection. This module gives future game cores one public boundary that preserves
their audit details, adds stable game-level identity fields, and recovers only a compatible
winner after a concurrent request commits first. No route or game imports this checkpoint.
"""

# Import the public ledger boundary without reaching into provider implementations.
from casino.core import ledger
# Import the shared finite-number validator before money-sign routing.
from casino.core.validation import require_finite_number
# Import public errors for stable validation and fail-closed replay conflicts.
from casino.errors import ConflictError, ValidationError


# Bound proof reconstruction to the existing generous player-local history window.
LEDGER_PROOF_SCAN_LIMIT = 1_000_000
# Reserve canonical detail keys that callers may repeat only with identical values.
CANONICAL_DETAIL_KEYS = ("game_action_key", "request_fingerprint", "round_id")


# Require one non-empty internal identity string without silently stringifying objects.
def _require_identity(value, *, field: str) -> str:
    # Reject missing, non-string, and whitespace-only identities before ledger access.
    if not isinstance(value, str) or not value.strip():
        # Publish a fixed non-reflecting diagnostic for the named internal dimension.
        raise ValidationError(f"{field} is required")
    # Return the caller's exact identity so audit and compatibility fields remain unchanged.
    return value


# Normalize one finite non-zero signed amount before selecting debit or credit.
def _normalize_signed_amount(value) -> float:
    # Reject booleans because Python would otherwise treat them as one and zero.
    if isinstance(value, bool):
        # Keep the diagnostic aligned with the shared numeric boundary.
        raise ValidationError("Settlement amount must be numeric")
    # Convert the amount through the shared NaN and infinity rejection boundary.
    amount = round(require_finite_number(value, field="Settlement amount"), 2)
    # Reject values that become zero at ledger precision because they have no money meaning.
    if amount == 0:
        # Explain the signed settlement requirement without reflecting caller content.
        raise ValidationError("Settlement amount cannot be zero")
    # Return the normalized signed amount used for routing and replay comparison.
    return amount


# Add canonical action evidence without mutating or replacing caller audit details.
def _canonical_details(details, *, action_key: str, request_fingerprint: str, round_id: str) -> dict:
    # Accept no details as an empty audit extension.
    if details is None:
        # Start from a fresh mapping so provider metadata cannot leak to a caller object.
        normalized = {}
    # Accept only mappings because scalar details cannot preserve named audit evidence.
    elif isinstance(details, dict):
        # Copy every caller field so existing game-specific audit content survives unchanged.
        normalized = dict(details)
    # Reject malformed internal calls before they reach a provider.
    else:
        # Publish a stable type diagnostic without reflecting the supplied value.
        raise ValidationError("Settlement details must be an object")
    # Build the canonical evidence that every future game-core action will share.
    canonical = {
        # Record the game-owned action identity separately from storage-owned metadata.
        "game_action_key": action_key,
        # Record the upstream semantic fingerprint used for compatible race recovery.
        "request_fingerprint": request_fingerprint,
        # Repeat the round identity inside details for portable ledger audit queries.
        "round_id": round_id,
    }
    # Validate caller-supplied reserved fields before enriching the copied mapping.
    for key in CANONICAL_DETAIL_KEYS:
        # Reject a reserved field that disagrees with the authoritative function argument.
        if key in normalized and normalized[key] != canonical[key]:
            # Fail closed because ambiguous audit evidence must never reach a money write.
            raise ConflictError("Settlement details conflict with canonical action identity", {"field": key})
    # Add or confirm the canonical fields while leaving all other caller fields untouched.
    normalized.update(canonical)
    # Return the enriched copy used for the storage-atomic action.
    return normalized


# Provide injectable public-ledger seams for focused listener-free proof.
class SettlementAdapter:
    # Bind the adapter to public ledger functions unless focused tests inject substitutes.
    def __init__(self, *, debit_once=None, credit_once=None, read_recent=None) -> None:
        # Retain the storage-atomic debit entry point.
        self._debit_once = debit_once or ledger.debit_once
        # Retain the storage-atomic credit entry point.
        self._credit_once = credit_once or ledger.credit_once
        # Retain the player-scoped proof reader used only after commit or conflict.
        self._read_recent = read_recent or ledger.read_recent

    # Locate and validate one committed action without allowing another scope to satisfy it.
    def find_action(
        self,  # Use this adapter's injected public-ledger seams.
        *,
        game_id,  # Scope proof to one registered game.
        player_id,  # Scope proof to one authenticated wallet.
        signed_amount,  # Match the exact signed money movement.
        transaction_type,  # Match the immutable ledger meaning.
        round_id,  # Match the immutable game round.
        action_key,  # Match the game-owned action identity.
        request_fingerprint,  # Match the upstream request semantics.
    ):  # Return the exact compatible event or no proof.
        # Validate the fixed game namespace before reading player history.
        game_id = _require_identity(game_id, field="game_id")
        # Validate the authenticated wallet identity before filtering ledger proof.
        player_id = _require_identity(player_id, field="player_id")
        # Normalize the expected signed amount for exact replay comparison.
        signed_amount = _normalize_signed_amount(signed_amount)
        # Validate the transaction meaning that distinguishes wager and settlement rows.
        transaction_type = _require_identity(transaction_type, field="transaction_type")
        # Validate the round identity used in both the ledger row and canonical details.
        round_id = _require_identity(round_id, field="round_id")
        # Validate the game-level action identity delegated to provider idempotency.
        action_key = _require_identity(action_key, field="action_key")
        # Validate the upstream semantic fingerprint used for compatible recovery.
        request_fingerprint = _require_identity(request_fingerprint, field="request_fingerprint")
        # Read only this player's bounded recent history for response or recovery proof.
        rows = self._read_recent(player_id, LEDGER_PROOF_SCAN_LIMIT)
        # Inspect newest rows first so a corrupt duplicate cannot hide a later conflict.
        for event in reversed(rows):
            # Ignore malformed non-object rows rather than trusting their shape.
            if not isinstance(event, dict):
                # Continue until a structured event is available.
                continue
            # Ignore another player's row if an injected or defensive reader returns one.
            if event.get("player_id") != player_id:
                # Preserve player isolation even when the provider seam over-returns.
                continue
            # Ignore another game's action namespace because storage scopes keys by game.
            if event.get("game") != game_id:
                # Prevent a same-named action in another game from becoming replay proof.
                continue
            # Read structured audit details once for action-key and fingerprint checks.
            event_details = event.get("details") if isinstance(event.get("details"), dict) else {}
            # Ignore rows that do not claim this game-level action identity.
            if event_details.get("game_action_key") != action_key:
                # Continue until the requested action identity is found.
                continue
            # Reject the same scoped identity reused under another round.
            if event.get("round_id") != round_id or event_details.get("round_id") != round_id:
                # Fail closed because provider action scope does not independently include round id.
                raise ConflictError("Settlement action key conflicts with committed round", {"action_key": action_key})
            # Reject the same scoped identity reused for another transaction meaning.
            if event.get("transaction_type") != transaction_type:
                # Fail closed because wager and settlement actions are not interchangeable.
                raise ConflictError("Settlement action key conflicts with transaction type", {"action_key": action_key})
            # Reject the same scoped identity reused for different request semantics.
            if event_details.get("request_fingerprint") != request_fingerprint:
                # Fail closed instead of replaying another wager or settlement request.
                raise ConflictError("Settlement action key conflicts with request fingerprint", {"action_key": action_key})
            # Normalize committed money defensively so corrupt non-finite proof cannot replay.
            try:
                # Reuse the same two-decimal signed comparison applied before a write.
                committed_amount = _normalize_signed_amount(event.get("amount"))
            # Convert malformed stored proof into a conflict rather than a caller validation error.
            except ValidationError as exc:
                # Fail closed because corrupted ledger evidence cannot authorize a replay.
                raise ConflictError("Settlement action proof has an invalid amount", {"action_key": action_key}) from exc
            # Reject the same scoped identity reused for a different signed movement.
            if committed_amount != signed_amount:
                # Fail closed because one action key may move one amount only.
                raise ConflictError("Settlement action key conflicts with committed amount", {"action_key": action_key})
            # Return the exact committed event for response reconstruction or recovery.
            return event
        # Report no compatible proof when this scoped action has not committed.
        return None

    # Commit or replay one signed storage-atomic game action.
    def apply_action_once(
        self,  # Use this adapter's injected public-ledger seams.
        *,
        game_id,  # Namespace provider idempotency to one game.
        player_id,  # Select the authenticated wallet.
        signed_amount,  # Route a debit or credit by sign.
        transaction_type,  # Persist the immutable ledger meaning.
        round_id,  # Persist the immutable game round.
        action_key,  # Delegate one game-owned action identity.
        request_fingerprint,  # Preserve upstream request semantics.
        details=None,  # Extend the audit envelope without replacement.
    ) -> tuple[dict, bool]:  # Return the exact event and replay marker.
        # Validate the game namespace before constructing canonical audit evidence.
        game_id = _require_identity(game_id, field="game_id")
        # Validate the authenticated wallet identity before any provider call.
        player_id = _require_identity(player_id, field="player_id")
        # Normalize the finite signed movement once for provider routing and recovery.
        signed_amount = _normalize_signed_amount(signed_amount)
        # Validate the immutable transaction meaning stored on the ledger row.
        transaction_type = _require_identity(transaction_type, field="transaction_type")
        # Validate the immutable round identity shared by the row and details.
        round_id = _require_identity(round_id, field="round_id")
        # Validate the game-level action key delegated to provider idempotency.
        action_key = _require_identity(action_key, field="action_key")
        # Validate the upstream request fingerprint used after a racing conflict.
        request_fingerprint = _require_identity(request_fingerprint, field="request_fingerprint")
        # Copy and enrich audit details without mutating the caller's mapping.
        event_details = _canonical_details(details, action_key=action_key, request_fingerprint=request_fingerprint, round_id=round_id)
        # Start the provider-owned atomic commit without a proof-before-write scan.
        try:
            # Route negative signed movements through the public debit-once boundary.
            if signed_amount < 0:
                # Return the provider's exact event and replay marker.
                return self._debit_once(
                    player_id=player_id,  # Debit only the authenticated wallet.
                    amount=abs(signed_amount),  # Give the debit boundary a positive magnitude.
                    transaction_type=transaction_type,  # Preserve the caller's ledger meaning.
                    action_key=action_key,  # Reuse the stable storage idempotency key.
                    game=game_id,  # Preserve the game namespace.
                    round_id=round_id,  # Preserve the game round.
                    details=event_details,  # Attach caller and canonical audit evidence.
                )
            # Route positive signed movements through the public credit-once boundary.
            return self._credit_once(
                player_id=player_id,  # Credit only the authenticated wallet.
                amount=signed_amount,  # Give the credit boundary a positive magnitude.
                transaction_type=transaction_type,  # Preserve the caller's ledger meaning.
                action_key=action_key,  # Reuse the stable storage idempotency key.
                game=game_id,  # Preserve the game namespace.
                round_id=round_id,  # Preserve the game round.
                details=event_details,  # Attach caller and canonical audit evidence.
            )
        # Recover only when another compatible request may have committed first.
        except ConflictError:
            # Read the winner's immutable proof after the provider rejects this proposal.
            recovered = self.find_action(
                game_id=game_id,  # Require the same game namespace.
                player_id=player_id,  # Require the same authenticated wallet.
                signed_amount=signed_amount,  # Require the same signed movement.
                transaction_type=transaction_type,  # Require the same ledger meaning.
                round_id=round_id,  # Require the same game round.
                action_key=action_key,  # Require the same game action identity.
                request_fingerprint=request_fingerprint,  # Require the same request semantics.
            )
            # Preserve the provider's original conflict when no compatible winner exists.
            if recovered is None:
                # Re-raise the active provider exception with its original traceback.
                raise
            # Return the compatible committed winner as an explicit replay.
            return recovered, True


# Bind production calls to the current public ledger implementation.
_DEFAULT_ADAPTER = SettlementAdapter()


# Commit or replay one signed game action through the default public-ledger adapter.
def apply_action_once(**kwargs) -> tuple[dict, bool]:
    # Delegate the complete keyword-only contract without adding route or game coupling.
    return _DEFAULT_ADAPTER.apply_action_once(**kwargs)


# Locate one committed action through the default public-ledger adapter.
def find_action(**kwargs):
    # Delegate the complete keyword-only proof dimensions to the shared adapter.
    return _DEFAULT_ADAPTER.find_action(**kwargs)
