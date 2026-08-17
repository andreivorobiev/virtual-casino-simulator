# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Route-free exactly-once settlement adapter for shared game cores. (issue #430)

The storage provider already owns atomic action identity, balance mutation, and durable
ledger projection. This module gives future game cores one public boundary that preserves
their audit details, adds stable game-level identity fields, and recovers only a compatible
winner after a concurrent request commits first. No route or game imports this checkpoint.
"""

# Import hashing so compatibility intents receive deterministic semantic fingerprints.
import hashlib
# Import canonical JSON encoding for compatibility-intent fingerprints.
import json

# Import the public ledger boundary without reaching into provider implementations.
from casino.core import ledger
# Import the shared finite-number validator before money-sign routing.
from casino.core.validation import require_finite_number
# Import public errors for stable validation and fail-closed replay conflicts.
from casino.errors import ConflictError, ValidationError


# Bound only injected legacy test-seam proof reconstruction to a small local window.
LEGACY_PROOF_FALLBACK_LIMIT = 1_000
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
    def __init__(self, *, debit_once=None, credit_once=None, find_action=None, read_recent=None) -> None:
        # Retain the storage-atomic debit entry point.
        self._debit_once = debit_once or ledger.debit_once
        # Retain the storage-atomic credit entry point.
        self._credit_once = credit_once or ledger.credit_once
        # Use the provider action index in production while preserving explicitly injected legacy seams.
        self._find_action = find_action or (None if read_recent is not None else ledger.find_action)
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
        # Resolve the canonical storage identity directly when the provider seam is available.
        indexed_event = self._find_action(player_id, game_id, action_key) if self._find_action is not None else None
        # Use the indexed singleton in production or the bounded injected history in legacy focused tests.
        rows = ([indexed_event] if indexed_event is not None else []) if self._find_action is not None else self._read_recent(player_id, LEGACY_PROOF_FALLBACK_LIMIT)
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


# Present one canonical gateway while historical rows remain read-compatible. (LEDGER-032, GAMECORE-008)
class GameSettlementGateway:
    """Delegate game settlement actions to the canonical settlement adapter.

    All new money movements use the canonical signed action dimensions. Historical game-specific
    detail keys remain readable without extending the retired mutation-alias surface.
    """

    # Bind one game namespace and its historical action-detail audit key.
    def __init__(
        self,  # Retain this compatibility gateway instance.
        game_id,  # Namespace every movement to one registered game.
        legacy_action_detail_key=None,  # Preserve one established audit field without exposing a call alias.
        *,
        debit_once=None,  # Allow focused tests to inject a storage-atomic debit seam.
        credit_once=None,  # Allow focused tests to inject a storage-atomic credit seam.
        find_action=None,  # Allow focused tests to inject the provider point-lookup seam.
        read_recent=None,  # Allow focused tests to inject player-scoped proof rows.
        debit=None,  # Accept the old raw test seam without using it in production.
        credit=None,  # Accept the old raw test seam without using it in production.
    ) -> None:
        # Validate and retain the fixed game namespace before constructing any adapter.
        self.game_id = _require_identity(game_id, field="game_id")
        # Retain the optional established details key for immutable read and write audit compatibility.
        self.legacy_action_detail_key = legacy_action_detail_key
        # Record whether focused tests supplied non-atomic historical mutation callbacks.
        self._legacy_raw_seam = debit is not None or credit is not None
        # Wrap a legacy focused-test debit into the storage-atomic return shape when supplied.
        if debit is not None:
            # Translate keyword-only canonical calls into the historical positional test seam.
            def compatibility_debit_once(**kwargs):
                # Execute only the injected focused-test seam and mark the first write non-replayed.
                event = debit(kwargs["player_id"], kwargs["amount"], kwargs["transaction_type"], kwargs["game"], kwargs["round_id"], kwargs["details"])
                # Return the tuple shape guaranteed by the real storage-atomic ledger boundary.
                return event, False

            # Use the wrapped test seam instead of the production debit-once function.
            debit_once = compatibility_debit_once
        # Wrap a legacy focused-test credit into the storage-atomic return shape when supplied.
        if credit is not None:
            # Translate keyword-only canonical calls into the historical positional test seam.
            def compatibility_credit_once(**kwargs):
                # Execute only the injected focused-test seam and mark the first write non-replayed.
                event = credit(kwargs["player_id"], kwargs["amount"], kwargs["transaction_type"], kwargs["game"], kwargs["round_id"], kwargs["details"])
                # Return the tuple shape guaranteed by the real storage-atomic ledger boundary.
                return event, False

            # Use the wrapped test seam instead of the production credit-once function.
            credit_once = compatibility_credit_once
        # Build the one canonical adapter that owns every production money movement.
        self._adapter = SettlementAdapter(debit_once=debit_once, credit_once=credit_once, find_action=find_action, read_recent=read_recent)

    # Read one committed action by canonical identity while accepting historical detail rows.
    def find(self, player_id, action_key, *, round_id=None, transaction_type=None, request_fingerprint=None):
        # Validate the authenticated wallet before opening its history.
        player_id = _require_identity(player_id, field="player_id")
        # Validate the stable game action identity before scanning proof.
        action_key = _require_identity(action_key, field="action_key")
        # Resolve the storage identity directly when production or a focused indexed seam provides it.
        indexed_event = self._adapter._find_action(player_id, self.game_id, action_key) if self._adapter._find_action is not None else None
        # Use the indexed singleton or a bounded injected legacy-history fallback.
        rows = ([indexed_event] if indexed_event is not None else []) if self._adapter._find_action is not None else self._adapter._read_recent(player_id, LEGACY_PROOF_FALLBACK_LIMIT)
        # Inspect newest rows first so recovery sees the latest compatible event.
        for event in reversed(rows):
            # Ignore malformed rows and every other game namespace.
            if not isinstance(event, dict) or event.get("game") != self.game_id:
                # Continue until a structured row for this game is available.
                continue
            # Read structured audit details without trusting historical row shape.
            details = event.get("details") if isinstance(event.get("details"), dict) else {}
            # Accept the canonical key or the one-release historical key.
            canonical_match = details.get("game_action_key") == action_key
            # Check the legacy key only when this game declared one.
            legacy_match = bool(self.legacy_action_detail_key) and details.get(self.legacy_action_detail_key) == action_key
            # Return only a row bound to this stable action identity.
            if canonical_match or legacy_match:
                # Validate an optional round constraint supplied by older proof readers.
                if round_id is not None and event.get("round_id") != round_id:
                    # Fail closed when one action identity is reused across rounds.
                    raise ConflictError("Settlement proof conflicts with committed round")
                # Validate an optional transaction constraint supplied by older proof readers.
                if transaction_type is not None and event.get("transaction_type") != transaction_type:
                    # Fail closed when one action identity is reused for another movement type.
                    raise ConflictError("Settlement proof conflicts with transaction type")
                # Reject semantic reuse when the caller supplied a canonical fingerprint.
                if request_fingerprint is not None and details.get("request_fingerprint") != request_fingerprint:
                    # Prevent equal wager totals from satisfying different requests.
                    raise ConflictError("Settlement proof conflicts with request fingerprint")
                # Preserve the immutable provider event for existing recovery code.
                return event
        # Report that this action has not committed.
        return None

    # Preserve the historical method name used by intent-driven controllers.
    def find_action(self, player_id, action_id):
        # Accept a prepared intent or its stable action identity during controller convergence.
        if isinstance(action_id, dict):
            # Preserve the prepared movement dimensions for fail-closed proof validation.
            intent = action_id
            # Delegate the full prepared identity to the compatibility proof reader.
            return self.find(player_id, intent.get("action_id"), round_id=intent.get("round_id"), transaction_type=intent.get("transaction_type"), request_fingerprint=(intent.get("details") or {}).get("request_fingerprint"))
        # Delegate a scalar action identity to the shared canonical-or-legacy proof reader.
        return self.find(player_id, action_id)

    # Preserve the historical Three Card Poker lookup name during convergence.
    def find_intent(self, intent):
        # Require the prepared intent's player and action dimensions through one proof reader.
        return self.find_action(intent.get("player_id"), intent)

    # Expose bounded player-local proof reads for legacy recovery code during one release.
    def read_recent(self, player_id, limit=100):
        # Delegate reads through the adapter-owned ledger seam without exposing money functions.
        return self._adapter._read_recent(player_id, limit)

    # Derive one stable compatibility action key from established game details.
    def _legacy_action_key(self, transaction_type, round_id, details):
        # Read structured details defensively before checking known historical fields.
        details = details if isinstance(details, dict) else {}
        # Prefer the configured game-specific field, then common historical aliases.
        candidates = [details.get(self.legacy_action_detail_key)] if self.legacy_action_detail_key else []
        # Append common keys used by pre-convergence game services.
        candidates.extend(details.get(key) for key in ("idempotency_key", "action_id", "client_action_id", "request_id"))
        # Return the first non-empty stable identity supplied by the prepared game state.
        for candidate in candidates:
            # Accept only non-empty strings as durable provider action identities.
            if isinstance(candidate, str) and candidate:
                # Preserve the exact historical identity for compatibility.
                return candidate
        # Fall back to the round and transaction type, which distinguish wager from settlement.
        return f"{round_id}:{transaction_type}"

    # Preserve deterministic fingerprints only for retained legacy callback adapters.
    def _legacy_callback_fingerprint(self, *, player_id, signed_amount, transaction_type, round_id, action_key, details):
        # Copy injected callback details so compatibility normalization never mutates game state.
        event_details = dict(details or {})
        # Reuse a canonical fingerprint already owned by the legacy game callback.
        request_fingerprint = event_details.get("request_fingerprint")
        # Derive the exact historical digest only at this explicit source-local adapter boundary.
        if not isinstance(request_fingerprint, str) or not request_fingerprint.strip():
            # Preserve structured predecessor semantics outside the canonical string field.
            if request_fingerprint is not None:
                # Retain the exact old object for immutable proof compatibility.
                event_details["legacy_request_fingerprint"] = request_fingerprint
            # Encode the predecessor gateway dimensions byte-for-byte for compatible recovery.
            encoded = json.dumps({"game_id": self.game_id, "player_id": player_id, "movement": signed_amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "details": event_details}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            # Publish one explicit lowercase digest to the canonical mutation call.
            request_fingerprint = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        # Replace any absent or structured predecessor field with the canonical string evidence.
        event_details["request_fingerprint"] = request_fingerprint
        # Return the explicit fingerprint and detached details together.
        return request_fingerprint, event_details

    # Preserve the historical positive-magnitude debit callback shape for focused seams.
    def debit(self, player_id, amount, transaction_type, game, round_id, details):
        # Derive the stable game action identity from existing audit details.
        action_key = self._legacy_action_key(transaction_type, round_id, details)
        # Preserve the predecessor digest explicitly before entering the canonical call.
        request_fingerprint, event_details = self._legacy_callback_fingerprint(player_id=player_id, signed_amount=-abs(amount), transaction_type=transaction_type, round_id=round_id, action_key=action_key, details=details)
        # Commit or replay the negative movement through the canonical adapter.
        event, _replayed = self.apply_once(player_id=player_id, signed_amount=-abs(amount), transaction_type=transaction_type, round_id=round_id, action_key=action_key, request_fingerprint=request_fingerprint, details=event_details)
        # Return the historical event-only callback shape.
        return event

    # Preserve the historical positive-magnitude credit callback shape for focused seams.
    def credit(self, player_id, amount, transaction_type, game, round_id, details):
        # Derive the stable game action identity from existing audit details.
        action_key = self._legacy_action_key(transaction_type, round_id, details)
        # Preserve the predecessor digest explicitly before entering the canonical call.
        request_fingerprint, event_details = self._legacy_callback_fingerprint(player_id=player_id, signed_amount=abs(amount), transaction_type=transaction_type, round_id=round_id, action_key=action_key, details=details)
        # Commit or replay the positive movement through the canonical adapter.
        event, _replayed = self.apply_once(player_id=player_id, signed_amount=abs(amount), transaction_type=transaction_type, round_id=round_id, action_key=action_key, request_fingerprint=request_fingerprint, details=event_details)
        # Return the historical event-only callback shape.
        return event

    # Validate one already-loaded legacy proof against immutable action dimensions.
    def validate_existing(
        self,  # Retain the gateway namespace and compatibility policy.
        event,  # Inspect the immutable ledger row supplied by recovery code.
        *,
        transaction_type,  # Require the same ledger meaning.
        round_id,  # Require the same game round.
        signed_amount,  # Require the canonical signed movement name.
        request_fingerprint,  # Require the canonical fingerprint name.
    ) -> None:
        # Reject malformed proof before reading any dimensions.
        if not isinstance(event, dict):
            # Fail closed because non-object evidence cannot authorize recovery.
            raise ConflictError("Settlement proof is malformed")
        # Normalize the canonical signed amount at ledger precision.
        expected_amount = _normalize_signed_amount(signed_amount)
        # Read structured proof details once for canonical and transitional checks.
        event_details = event.get("details") if isinstance(event.get("details"), dict) else {}
        # Reject proof from another game, round, transaction, or signed movement.
        dimensions_match = event.get("game") == self.game_id and event.get("round_id") == round_id and event.get("transaction_type") == transaction_type and _normalize_signed_amount(event.get("amount")) == expected_amount
        # Fail closed when the immutable ledger dimensions do not match recovery state.
        if not dimensions_match:
            # Keep one stable conflict diagnostic across all compatibility callers.
            raise ConflictError("Settlement proof conflicts with immutable action dimensions")
        # Reject proof whose request semantics differ from the prepared action.
        if event_details.get("request_fingerprint") != request_fingerprint:
            # Prevent a coincidentally equal amount from satisfying another request.
            raise ConflictError("Settlement proof conflicts with request fingerprint")

    # Commit one canonical gateway call through the canonical adapter. (GAMECORE-008)
    def apply_once(
        self,  # Retain this gateway instance.
        *,
        player_id,  # Select the authenticated wallet.
        signed_amount,  # Require the canonical signed movement name.
        transaction_type,  # Preserve the established ledger meaning.
        round_id,  # Require one portable game round or entity identity.
        action_key,  # Require the canonical game action identity.
        request_fingerprint,  # Require the canonical semantic fingerprint name.
        details=None,  # Preserve game-specific audit evidence.
    ) -> tuple[dict, bool]:
        # Copy caller audit evidence so canonical validation never mutates game state.
        event_details = dict(details or {})
        # Preserve the configured historical audit field without extending the method's canonical signature.
        if self.legacy_action_detail_key:
            # Add the established field only when game-owned evidence did not supply a distinct entity identity.
            if self.legacy_action_detail_key not in event_details:
                # Keep downstream ledger audits compatible while the universal key remains authoritative.
                event_details[self.legacy_action_detail_key] = action_key
        # Emulate exactly-once replay only for injected historical test callbacks.
        if self._legacy_raw_seam:
            # Resolve a prior compatible event before a non-atomic fake can append again.
            existing = self._adapter.find_action(game_id=self.game_id, player_id=player_id, signed_amount=signed_amount, transaction_type=transaction_type, round_id=round_id, action_key=action_key, request_fingerprint=request_fingerprint)
            # Return immutable proof when the injected seam already committed this action.
            if existing is not None:
                # Mark the historical fake callback result as replayed.
                return existing, True
        # Delegate the complete movement to the one production settlement boundary.
        return self._adapter.apply_action_once(
            game_id=self.game_id,  # Keep provider idempotency game-scoped.
            player_id=player_id,  # Keep wallet ownership session-scoped.
            signed_amount=signed_amount,  # Route debit or credit by sign.
            transaction_type=transaction_type,  # Preserve current ledger vocabulary.
            round_id=round_id,  # Persist the caller-owned portable action scope.
            action_key=action_key,  # Use one storage-atomic idempotency identity.
            request_fingerprint=request_fingerprint,  # Bind retries to exact semantics.
            details=event_details,  # Preserve old and new audit fields together.
        )

    # Apply one prepared debit/credit intent used by staged game controllers.
    def transact(self, intent):
        # Require a mapping because scalar intents cannot express safe money semantics.
        if not isinstance(intent, dict):
            # Reject malformed internal calls before any ledger access.
            raise ValidationError("Settlement intent must be an object")
        # Read the established direction before calculating a signed movement.
        direction = intent.get("direction")
        # Convert the positive intent magnitude into the adapter's signed vocabulary.
        signed_amount = -abs(intent.get("amount", 0)) if direction == "debit" else abs(intent.get("amount", 0)) if direction == "credit" else None
        # Reject unknown directions rather than turning them into credits.
        if signed_amount is None:
            # Publish one stable internal validation diagnostic.
            raise ValidationError("Settlement intent direction is invalid")
        # Preserve structured intent details without mutating prepared state.
        details = dict(intent.get("details") or {})
        # Reuse an existing semantic fingerprint when the controller already persisted one.
        request_fingerprint = details.get("request_fingerprint")
        # Derive a deterministic fingerprint for older prepared intents.
        if not request_fingerprint:
            # Encode only immutable intent semantics with sorted compact JSON.
            encoded = json.dumps({"player_id": intent.get("player_id"), "amount": intent.get("amount"), "transaction_type": intent.get("transaction_type"), "game": intent.get("game"), "round_id": intent.get("round_id"), "action_id": intent.get("action_id"), "direction": direction, "details": details}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            # Store the fixed digest used to reject changed action reuse.
            request_fingerprint = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        # Delegate the prepared movement through the canonical adapter.
        event, _replayed = self.apply_once(
            player_id=intent.get("player_id"),  # Preserve authenticated/prepared wallet ownership.
            signed_amount=signed_amount,  # Route the prepared debit or credit.
            transaction_type=intent.get("transaction_type"),  # Preserve ledger meaning.
            round_id=intent.get("round_id"),  # Preserve prepared round identity.
            action_key=intent.get("action_id"),  # Publish caller-stable identity under the canonical name.
            request_fingerprint=request_fingerprint,  # Preserve or derive semantic identity.
            details=details,  # Preserve game-specific audit details.
        )
        # Return the immutable event expected by existing controller recovery code.
        return event


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
