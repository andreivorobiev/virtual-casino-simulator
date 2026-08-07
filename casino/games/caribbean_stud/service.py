"""Session-bound, ledger-only orchestration for isolated Caribbean Stud."""

# Import copy support so insufficient-funds rollback can restore decision state.
import copy
# Import canonical JSON encoding for semantic retry fingerprints.
import json
# Import action-id hashing for stable request fingerprints.
import hashlib
# Import bounded action identity validation.
import re
# Import process-local locks for one-server exactly-once sequences.
import threading

# Import the only approved wallet mutation service and player reader.
from casino.core import players
# Import the shared UTC clock used by existing game modules.
from casino.core.clock import utc_now
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistent state helpers.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict, funds, lookup, and validation errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError
# Import only this game's pure rules engine.
from casino.games.caribbean_stud import engine

# Require bounded log-safe action ids for every public movement or decision.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local ledger history to recover supported simulator retries.
# Serialize state and ledger read-before-write sections in the local process.
_ACTION_LOCK = threading.RLock()


# Validate one required public retry identity.
def require_action_id(value) -> str:
    # Accept only bounded URL-safe strings.
    if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
        # Explain the stable public boundary without echoing hostile input.
        raise ValidationError("Caribbean Stud action_id must be 1-128 URL-safe characters")
    # Return the exact identity so retries remain byte-for-byte stable.
    return value


# Hash one canonical request body subset for conflict detection.
def request_fingerprint(payload: dict) -> str:
    # Encode sorted compact JSON so insertion order cannot affect identity.
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    # Return a fixed-width lowercase digest suitable for persisted audit details.
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Persist player-scoped game documents through the shared storage provider.
class StateRepository:
    # Load one authenticated player's document.
    def load(self, player_id: str) -> dict:
        # Delegate JSON/MySQL selection and schema metadata to shared state storage.
        return load_player_game_state(engine.GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's document.
    def save(self, player_id: str, state: dict) -> None:
        # Delegate atomic file replacement or provider storage.
        save_player_game_state(engine.GAME_ID, player_id, state)


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old Caribbean Stud key beside canonical action evidence.
    return GameSettlementGateway(engine.GAME_ID, "caribbean_stud_action_key", **kwargs)


# Coordinate player state, deterministic hands, decisions, and ledger movements.
class CaribbeanStudService:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, repository=None, ledger_gateway=None, player_reader=None, clock=None, shoe_factory=None):
        # Use shared persistent state unless a test supplies memory storage.
        self.repository = repository or StateRepository()
        # Use the game-local shared-ledger adapter unless a test supplies a fake.
        self.ledger = ledger_gateway or CoreLedgerGateway()
        # Use the shared player reader unless a test supplies a fixture.
        self.player_reader = player_reader or players.get_player
        # Use the shared UTC clock unless a focused test pins timestamps.
        self.clock = clock or utc_now
        # Use production shuffle unless a test supplies deterministic ten-card shoes.
        self.shoe_factory = shoe_factory

    # Save one player document through the injected persistence boundary.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate without mutating shared storage configuration.
        self.repository.save(player_id, state)

    # Build the public state, rules, and current-player payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return only sanitized game state and documented fixed rules.
        return {"game": engine.GAME_ID, "state": engine.public_state(state), "player": self.player_reader(player_id), "rules": engine.rules_payload()}

    # Derive the stable ledger action key for one movement stage.
    def _key(self, action_id: str, stage: str) -> str:
        # Namespace the public action id by ledger stage.
        return f"{action_id}:{stage}"

    # Build ante ledger audit details from a prepared round.
    def _ante_details(self, round_state: dict) -> dict:
        # Return enough public and private context to validate recovery.
        return {"action_id": round_state["deal_action_id"], "stage": "ante", "ante": round_state["ante"], "player_hand": round_state["player_hand"], "dealer_upcard": round_state["dealer_upcard"], "player_rank": round_state["player_rank"]}

    # Build call debit audit details from a settled showdown.
    def _call_details(self, round_state: dict) -> dict:
        # Return the immutable decision and wager context.
        return {"action_id": round_state["call_action_id"], "stage": "call", "ante": round_state["ante"], "call_wager": round_state["call_wager"], "outcome": round_state["outcome"]}

    # Build settlement credit audit details from a settled showdown.
    def _settlement_details(self, round_state: dict) -> dict:
        # Return player-facing result context without any unrevealed state.
        return {"action_id": round_state["call_action_id"], "stage": "settlement", "ante": round_state["ante"], "call_wager": round_state["call_wager"], "payout": round_state["payout"], "outcome": round_state["outcome"], "dealer_qualifies": round_state["dealer_qualifies"]}

    # Mark a recovered or newly committed ante debit complete.
    def _mark_ante_complete(self, player_id: str, state: dict, round_state: dict, event: dict) -> None:
        # Store the committed ante marker.
        round_state["ante_status"] = "complete"
        # Store the immutable ledger identifier.
        round_state["ante_ledger_id"] = event.get("ledger_id")
        # Store the internal movement stage after proof exists.
        round_state["movement_stage"] = "ante_committed"
        # Persist the recovered or new proof marker.
        self._save(player_id, state)

    # Commit or recover the initial ante debit.
    def _ensure_ante(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Derive the stable ante movement key.
        action_key = self._key(round_state["deal_action_id"], "ante")
        # Record intent before calling the shared ledger boundary.
        round_state["movement_stage"] = "ante_attempting"
        # Persist intent so ambiguous provider failures never repeat silently.
        self._save(player_id, state)
        # Commit or recover the one ante debit.
        event, replayed = self.ledger.apply_once(player_id=player_id, signed_amount=-round_state["ante"], transaction_type="CARIBBEAN_STUD_ANTE_DEBIT", round_id=round_state["round_id"], action_key=action_key, fingerprint=round_state["deal_fingerprint"], details=self._ante_details(round_state))
        # Mark the ante complete only after append-only proof exists.
        self._mark_ante_complete(player_id, state, round_state, event)
        # Return proof and replay evidence.
        return event, replayed

    # Recover a pending ante marker without repeating ambiguous movement.
    def _recover_ante(self, player_id: str, state: dict, round_state: dict) -> None:
        # Skip already committed antes.
        if round_state.get("ante_status") == "complete":
            # No recovery is required.
            return
        # Derive the stable ante movement key.
        action_key = self._key(round_state["deal_action_id"], "ante")
        # Search for append-only proof.
        event = self.ledger.find(player_id, action_key)
        # Restore a lost marker when proof exists.
        if event is not None:
            # Validate proof before trusting recovered state.
            self.ledger.validate_existing(event, signed_amount=-round_state["ante"], transaction_type="CARIBBEAN_STUD_ANTE_DEBIT", round_id=round_state["round_id"], fingerprint=round_state["deal_fingerprint"])
            # Mark the ante complete from ledger evidence.
            self._mark_ante_complete(player_id, state, round_state, event)
            # Stop after recovery.
            return
        # Fail closed when a prior movement attempt became ambiguous.
        if round_state.get("movement_stage") == "ante_attempting":
            # Require explicit reconciliation instead of issuing a possible duplicate debit.
            raise ConflictError("Caribbean Stud ante outcome is uncertain and requires ledger reconciliation")
        # Clear an uncharged prepared round whose ante never committed.
        state["active_round"] = None
        # Release the action id because no balance movement committed.
        state.setdefault("action_receipts", {}).pop(round_state.get("deal_action_id"), None)
        # Persist cleanup so the player can deal again.
        self._save(player_id, state)

    # Mark a recovered or newly committed call debit complete.
    def _mark_call_complete(self, player_id: str, state: dict, round_state: dict, event: dict) -> None:
        # Store the committed call marker.
        round_state["call_status"] = "complete"
        # Store the immutable call ledger identifier.
        round_state["call_ledger_id"] = event.get("ledger_id")
        # Store the internal stage after call proof exists.
        round_state["movement_stage"] = "call_committed"
        # Persist the recovered or new marker.
        self._save(player_id, state)

    # Mark a recovered or newly committed settlement credit complete.
    def _mark_settlement_complete(self, player_id: str, state: dict, round_state: dict, event: dict | None) -> None:
        # Store the terminal settlement marker.
        round_state["settlement_status"] = "complete"
        # Store the optional immutable settlement ledger identifier.
        if event is not None:
            # Preserve proof only when a positive credit existed.
            round_state["settlement_ledger_id"] = event.get("ledger_id")
        # Store the terminal internal stage.
        round_state["movement_stage"] = "settled"
        # Persist the terminal marker.
        self._save(player_id, state)

    # Commit or recover a call debit and any returned-token credit.
    def _ensure_call_and_settlement(self, player_id: str, state: dict, round_state: dict) -> tuple[dict | None, dict | None, bool]:
        # Start with no call proof and no replay evidence.
        call_event, settlement_event, replayed = None, None, False
        # Commit or recover the required call debit first.
        if round_state.get("call_status") != "complete":
            # Derive the stable call debit key.
            call_key = self._key(round_state["call_action_id"], "call")
            # Record debit intent before touching the shared ledger.
            round_state["movement_stage"] = "call_attempting"
            # Persist intent for fail-closed recovery.
            self._save(player_id, state)
            # Commit or recover the 2x ante call debit.
            call_event, call_replayed = self.ledger.apply_once(player_id=player_id, signed_amount=-round_state["call_wager"], transaction_type="CARIBBEAN_STUD_CALL_DEBIT", round_id=round_state["round_id"], action_key=call_key, fingerprint=round_state["call_fingerprint"], details=self._call_details(round_state))
            # Mark the call debit complete only after proof exists.
            self._mark_call_complete(player_id, state, round_state, call_event)
            # Track replay evidence.
            replayed = replayed or call_replayed
        # Reuse existing call proof for replay responses.
        else:
            # Recover immutable proof for returned payloads when possible.
            call_event = self.ledger.find(player_id, self._key(round_state["call_action_id"], "call"))
        # Skip zero-return losses after the call debit is complete.
        if not round_state.get("payout"):
            # Mark no-credit settlement complete.
            self._mark_settlement_complete(player_id, state, round_state, None)
            # Return call proof and no settlement proof.
            return call_event, None, replayed
        # Commit or recover the positive returned-token credit.
        if round_state.get("settlement_status") != "complete":
            # Derive the stable settlement key.
            settlement_key = self._key(round_state["call_action_id"], "settlement")
            # Record credit intent before touching the shared ledger.
            round_state["movement_stage"] = "settlement_attempting"
            # Persist intent for fail-closed recovery.
            self._save(player_id, state)
            # Commit or recover the settlement credit.
            settlement_event, settlement_replayed = self.ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="CARIBBEAN_STUD_SETTLEMENT_CREDIT", round_id=round_state["round_id"], action_key=settlement_key, fingerprint=round_state["call_fingerprint"], details=self._settlement_details(round_state))
            # Mark the settlement complete only after proof exists.
            self._mark_settlement_complete(player_id, state, round_state, settlement_event)
            # Track replay evidence.
            replayed = replayed or settlement_replayed
        # Reuse existing settlement proof for replay responses.
        else:
            # Recover immutable proof for returned payloads when possible.
            settlement_event = self.ledger.find(player_id, self._key(round_state["call_action_id"], "settlement"))
        # Return both movement proofs and replay evidence.
        return call_event, settlement_event, replayed

    # Recover pending call and settlement markers without repeating ambiguous writes.
    def _recover_settled_round(self, player_id: str, state: dict, round_state: dict) -> None:
        # Recover only called rounds with ledger-moving call state.
        if round_state.get("call_action_id") and round_state.get("call_status") != "complete":
            # Derive the stable call debit key.
            call_key = self._key(round_state["call_action_id"], "call")
            # Search for append-only call proof.
            call_event = self.ledger.find(player_id, call_key)
            # Restore a lost call marker when proof exists.
            if call_event is not None:
                # Validate call debit proof before trusting it.
                self.ledger.validate_existing(call_event, signed_amount=-round_state["call_wager"], transaction_type="CARIBBEAN_STUD_CALL_DEBIT", round_id=round_state["round_id"], fingerprint=round_state["call_fingerprint"])
                # Mark the call debit complete from proof.
                self._mark_call_complete(player_id, state, round_state, call_event)
            # Fail closed when an attempted call debit lacks proof.
            elif round_state.get("movement_stage") == "call_attempting":
                # Require reconciliation instead of possibly repeating a debit.
                raise ConflictError("Caribbean Stud call outcome is uncertain and requires ledger reconciliation")
        # Recover only positive settlements that are still pending.
        if round_state.get("call_action_id") and round_state.get("payout") and round_state.get("settlement_status") != "complete":
            # Derive the stable settlement key.
            settlement_key = self._key(round_state["call_action_id"], "settlement")
            # Search for append-only settlement proof.
            settlement_event = self.ledger.find(player_id, settlement_key)
            # Restore a lost settlement marker when proof exists.
            if settlement_event is not None:
                # Validate settlement credit proof before trusting it.
                self.ledger.validate_existing(settlement_event, signed_amount=round_state["payout"], transaction_type="CARIBBEAN_STUD_SETTLEMENT_CREDIT", round_id=round_state["round_id"], fingerprint=round_state["call_fingerprint"])
                # Mark settlement complete from proof.
                self._mark_settlement_complete(player_id, state, round_state, settlement_event)
            # Fail closed when an attempted credit lacks proof.
            elif round_state.get("movement_stage") == "settlement_attempting":
                # Require reconciliation instead of possibly repeating a credit.
                raise ConflictError("Caribbean Stud settlement outcome is uncertain and requires ledger reconciliation")
        # Finish deterministic no-credit called losses when needed.
        if round_state.get("call_action_id") and not round_state.get("payout") and round_state.get("settlement_status") != "complete":
            # Mark the zero-credit settlement complete.
            self._mark_settlement_complete(player_id, state, round_state, None)

    # Recover all persisted movements before serving state or accepting a new action.
    def _recover_all(self, player_id: str, state: dict) -> None:
        # Recover the active ante if it is still pending.
        if state.get("active_round"):
            # Inspect only the authenticated player's active round.
            self._recover_ante(player_id, state, state["active_round"])
        # Recover terminal rounds whose call or settlement marker was interrupted.
        for round_state in list(state.get("recent_rounds", [])):
            # Reconcile only retained terminal rounds.
            self._recover_settled_round(player_id, state, round_state)

    # Read reload-safe state for one authenticated player.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against concurrent actions for the same local process.
        with _ACTION_LOCK:
            # Load the newest player-scoped document inside the lock.
            state = self.repository.load(player_id)
            # Recover committed or owed ledger movements before publishing state.
            self._recover_all(player_id, state)
            # Return sanitized state and current-player information.
            return self._payload(player_id, state)

    # Deal or replay one ante-backed Caribbean Stud round.
    def deal(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Caribbean Stud deal body must be an object")
        # Validate the deal action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the ante before constructing a semantic fingerprint.
        ante = engine.normalize_ante(request.get("ante"))
        # Bind the action identity to the exact normalized ante.
        fingerprint = request_fingerprint({"stage": "deal", "ante": ante})
        # Serialize state preparation, debit, and marker persistence.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self.repository.load(player_id)
            # Recover any interrupted prior action before enforcing active-round rules.
            self._recover_all(player_id, state)
            # Load durable compact receipts that prevent reuse after history pruning.
            receipts = state.setdefault("action_receipts", {})
            # Read any prior semantic owner for this action identity.
            receipt = receipts.get(action_id)
            # Find a retained deal with the same client action identity.
            existing = engine.round_for_deal_action(state, action_id)
            # Replay the exact prepared or settled round when settings match.
            if existing is not None:
                # Reject action-id reuse with a changed ante.
                if existing.get("deal_fingerprint") != fingerprint:
                    # Fail before a second ledger movement.
                    raise ConflictError("action_id was already used with a different Caribbean Stud ante")
                # Restore a compatible durable receipt.
                receipts[action_id] = {"stage": "deal", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Ensure the original ante marker exists.
                ante_event, ledger_replayed = self._ensure_ante(player_id, state, existing) if existing.get("ante_status") != "complete" else (self.ledger.find(player_id, self._key(action_id, "ante")), True)
                # Return the same round and ledger proof.
                return {**self._payload(player_id, state), "round": engine.public_round(existing), "ledger": {"ante": ante_event}, "replayed": True or ledger_replayed}
            # Reject an identity already retained for another stage.
            if engine.action_owner(state, action_id) is not None:
                # Keep one action id bound to exactly one semantic command.
                raise ConflictError("action_id was already used for another Caribbean Stud action")
            # Reject reuse when the owning round has aged out of bounded history.
            if receipt is not None:
                # Keep durable action identity at-most-once across retained state.
                raise ConflictError("action_id belongs to an older Caribbean Stud action")
            # Refuse to reconstruct cards if a committed debit outlived state.
            if self.ledger.find(player_id, self._key(action_id, "ante")) is not None:
                # Preserve the committed debit without presenting changed cards.
                raise ConflictError("Committed Caribbean Stud round state is unavailable")
            # Prevent overlapping antes while one decision awaits call or fold.
            if state.get("active_round") is not None:
                # Require a terminal decision first.
                raise ConflictError("Finish the active Caribbean Stud round before dealing again")
            # Use a deterministic test shoe only through the injected service seam.
            player_hand, dealer_hand = engine.deal_hands(cards=self.shoe_factory(action_id) if self.shoe_factory else None)
            # Derive a stable route and ledger correlation id from authenticated input.
            round_id = engine.round_id_for(player_id, action_id)
            # Build prepared state before touching the shared ledger.
            round_state = engine.create_round(player_id, ante, action_id, player_hand=player_hand, dealer_hand=dealer_hand, round_id=round_id, created_at=self.clock(), request_fingerprint=fingerprint)
            # Preserve prior state for definitive no-movement failures.
            prior_state = copy.deepcopy(state)
            # Persist the hidden deterministic dealer hand before any balance movement.
            state["active_round"] = round_state
            # Persist a compact action receipt before the ante can commit.
            receipts[action_id] = {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}
            # Save prepared state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Apply the ante debit with rollback only for definitive no-movement failures.
            try:
                # Apply or recover the one ante debit.
                ante_event, ledger_replayed = self._ensure_ante(player_id, state, round_state)
            # Roll back unaffordable or invalid shared-ledger debits when no proof exists.
            except (InsufficientFundsError, ValidationError):
                # Restore prior state only when the append-only ledger has no movement.
                if self.ledger.find(player_id, self._key(action_id, "ante")) is None:
                    # Restore pre-deal state and receipts.
                    self._save(player_id, prior_state)
                # Re-raise the public funds or validation error.
                raise
            # Return the visible round and committed ante evidence.
            return {**self._payload(player_id, state), "round": engine.public_round(round_state), "ledger": {"ante": ante_event}, "replayed": ledger_replayed}

    # Apply or replay one call decision and ledger settlement.
    def call(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Caribbean Stud call body must be an object")
        # Validate the call action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Bind the action identity to the exact round and call stage.
        fingerprint = request_fingerprint({"stage": "call", "round_id": round_id})
        # Serialize reveal, archive, call debit, and returned-token settlement.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self.repository.load(player_id)
            # Recover any interrupted movements before a new decision.
            self._recover_all(player_id, state)
            # Locate the round without crossing authenticated player state.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session round ids identically.
            if round_state is None:
                # Return the stable public lookup error.
                raise NotFoundError("Caribbean Stud round was not found")
            # Require committed ante proof before any call wager can settle.
            if round_state.get("ante_status") != "complete":
                # Fail closed rather than allowing free showdown.
                raise ConflictError("Caribbean Stud ante is not committed")
            # Load durable compact receipts that prevent cross-round action reuse.
            receipts = state.setdefault("action_receipts", {})
            # Build the expected receipt for this call.
            expected_receipt = {"stage": "call", "round_id": round_id, "request_fingerprint": fingerprint}
            # Read any durable receipt for this identity.
            receipt = receipts.get(action_id)
            # Read any retained owner for this identity.
            owner = engine.action_owner(state, action_id)
            # Reject reuse by another round or another stage.
            if owner is not None and (owner[0].get("round_id") != round_id or owner[1] != "call"):
                # Preserve one semantic action per id.
                raise ConflictError("action_id was already used for another Caribbean Stud action")
            # Reject a durable receipt owned by changed request content.
            if receipt is not None and receipt != expected_receipt:
                # Fail before revealing or settling another result.
                raise ConflictError("action_id was already used for another Caribbean Stud action")
            # Replay the original call after settlement.
            if round_state.get("phase") == "settled":
                # Require the same call action and fingerprint.
                if round_state.get("call_action_id") != action_id or round_state.get("call_fingerprint") != fingerprint:
                    # Reject a second terminal decision.
                    raise ConflictError("Caribbean Stud round was already settled by another action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Recover any pending call or settlement marker.
                call_event, settlement_event, ledger_replayed = self._ensure_call_and_settlement(player_id, state, round_state)
                # Return the stable terminal result as a replay.
                return {**self._payload(player_id, state), "round": engine.public_round(round_state), "ledger": {"call": call_event, "settlement": settlement_event}, "replayed": True or ledger_replayed}
            # Require this exact round to remain active.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming actionable.
                raise ConflictError("Only the active Caribbean Stud round can accept a call")
            # Preserve prior decision state for definitive no-movement failures.
            prior_state = copy.deepcopy(state)
            # Reveal and calculate the deterministic result without wallet mutation.
            engine.settle_call(round_state, action_id, completed_at=self.clock(), request_fingerprint=fingerprint)
            # Record the durable decision identity before any call debit.
            receipts[action_id] = expected_receipt
            # Archive the complete result before issuing any ledger movement.
            engine.archive_round(state, round_state)
            # Persist terminal cards and pending settlement for crash recovery.
            self._save(player_id, state)
            # Apply call debit and optional settlement credit.
            try:
                # Commit or recover all required movements.
                call_event, settlement_event, ledger_replayed = self._ensure_call_and_settlement(player_id, state, round_state)
            # Roll back an unaffordable call when no call debit proof exists.
            except (InsufficientFundsError, ValidationError):
                # Restore the pre-call active decision when no call debit committed.
                if self.ledger.find(player_id, self._key(action_id, "call")) is None:
                    # Restore the active decision state.
                    self._save(player_id, prior_state)
                # Re-raise the public funds or validation error.
                raise
            # Return the revealed result and ledger proof.
            return {**self._payload(player_id, state), "round": engine.public_round(round_state), "ledger": {"call": call_event, "settlement": settlement_event}, "replayed": ledger_replayed}

    # Apply or replay one fold decision without a new ledger movement.
    def fold(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state access.
            raise ValidationError("Caribbean Stud fold body must be an object")
        # Validate the fold action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Bind the action identity to the exact round and fold stage.
        fingerprint = request_fingerprint({"stage": "fold", "round_id": round_id})
        # Serialize terminal state updates.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self.repository.load(player_id)
            # Recover any interrupted ante before permitting a fold.
            self._recover_all(player_id, state)
            # Locate the round without crossing authenticated player state.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session round ids identically.
            if round_state is None:
                # Return the stable public lookup error.
                raise NotFoundError("Caribbean Stud round was not found")
            # Require committed ante proof before forfeiting it.
            if round_state.get("ante_status") != "complete":
                # Fail closed rather than allowing a free terminal round.
                raise ConflictError("Caribbean Stud ante is not committed")
            # Load durable compact receipts that prevent action reuse after pruning.
            receipts = state.setdefault("action_receipts", {})
            # Build the expected receipt for this fold.
            expected_receipt = {"stage": "fold", "round_id": round_id, "request_fingerprint": fingerprint}
            # Read any durable receipt for this identity.
            receipt = receipts.get(action_id)
            # Read any retained owner for this identity.
            owner = engine.action_owner(state, action_id)
            # Reject reuse by another round or another stage.
            if owner is not None and (owner[0].get("round_id") != round_id or owner[1] != "fold"):
                # Preserve one semantic action per id.
                raise ConflictError("action_id was already used for another Caribbean Stud action")
            # Reject a durable receipt owned by changed request content.
            if receipt is not None and receipt != expected_receipt:
                # Fail before changing terminal state.
                raise ConflictError("action_id was already used for another Caribbean Stud action")
            # Replay the original fold after settlement.
            if round_state.get("phase") == "settled":
                # Require the same fold action and fingerprint.
                if round_state.get("fold_action_id") != action_id or round_state.get("fold_fingerprint") != fingerprint:
                    # Reject a second terminal decision.
                    raise ConflictError("Caribbean Stud round was already settled by another action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Persist the restored receipt.
                self._save(player_id, state)
                # Return the stable terminal result as a replay.
                return {**self._payload(player_id, state), "round": engine.public_round(round_state), "ledger": {}, "replayed": True}
            # Require this exact round to remain active.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming actionable.
                raise ConflictError("Only the active Caribbean Stud round can accept a fold")
            # Resolve the deterministic fold result without revealing dealer cards.
            engine.settle_fold(round_state, action_id, completed_at=self.clock(), request_fingerprint=fingerprint)
            # Record the durable fold receipt before archiving.
            receipts[action_id] = expected_receipt
            # Archive the terminal fold result.
            engine.archive_round(state, round_state)
            # Persist terminal state.
            self._save(player_id, state)
            # Return the folded result and no new ledger movement.
            return {**self._payload(player_id, state), "round": engine.public_round(round_state), "ledger": {}, "replayed": False}
