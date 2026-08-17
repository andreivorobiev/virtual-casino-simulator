# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for the isolated Hi-Lo game."""

# Import deep-copy support for detached optimistic state snapshots.
import copy
# Import canonical JSON encoding for semantic action fingerprints.
import json
# Import regular expressions for bounded public action identities.
import re
# Import hashing so changed retries fail even when amounts happen to match.
import hashlib
# Import a reentrant lock for single-process state and ledger reconciliation.
import threading

# Import the only approved player-balance mutation service.
from casino.core import players
# Import the shared audit clock used by other game modules.
from casino.core.clock import utc_now
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic state and rule helpers.
from casino.games.hi_lo import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local history to preserve retry recovery for the supported simulator.
# Serialize action-id lookup and ledger writes inside the one-process server.
_ACTION_LOCK = threading.RLock()
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_hi_lo_atomic_baseline"
# Name every state field owned by Hi-Lo transitions.
_GAME_STATE_KEYS = ("active_round", "recent_rounds", "action_receipts")


# Validate one required client action identity without echoing hostile input.
def require_action_id(value) -> str:
    # Accept only bounded URL-safe strings.
    if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
        # Explain the stable public boundary.
        raise ValidationError("action_id must be 1-128 URL-safe characters")
    # Return the exact identity so retries remain byte-for-byte stable.
    return value


# Hash one canonical request body subset for conflicting-retry detection.
def request_fingerprint(payload: dict) -> str:
    # Encode sorted compact JSON so mapping insertion order cannot change identity.
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    # Return a fixed-width lowercase digest suitable for persisted audit details.
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old Hi-Lo key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "hi_lo_action_id", **kwargs)


# Persist player-scoped game documents through the selected storage provider.
class StateRepository:
    # Load one authenticated player's document.
    def load(self, player_id: str) -> dict:
        # Delegate provider selection and legacy defaults to shared state storage.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Apply one transition while the provider owns its cross-process boundary.
    def update(self, player_id: str, mutator) -> dict:
        # Delegate current-state loading, rollback, and publication atomically.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state)


# Coordinate player state, deterministic cards, and retry-safe ledger movements.
class HiLoService:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, ledger_gateway=None, repository=None, get_player=None, clock=None, seed_factory=None):
        # Use the game-local shared-ledger adapter unless a test supplies a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Use shared persistent state unless a focused test supplies memory storage.
        self._repository = repository or StateRepository()
        # Return read-only current-player information without balance mutation.
        self._get_player = get_player or players.get_player
        # Use the shared UTC clock unless a focused test pins timestamps.
        self._clock = clock or utc_now
        # Derive deterministic cards only through an injected non-production hook.
        self._seed_factory = seed_factory

    # Capture only the fields owned by Hi-Lo transitions.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Build one fresh compatibility baseline for absent predecessor fields.
        defaults = engine.default_state()
        # Detach nested rounds and receipts from later engine mutation.
        return {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}

    # Load one document and bind its optimistic game-owned baseline.
    def _load(self, player_id: str) -> dict:
        # Read through the injected repository before provider mutation.
        state = self._repository.load(player_id)
        # Retain the exact game-owned values expected by the next publication.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting operation metadata.
        return state

    # Publish one provider-current compare-and-replace transition. (HILO-006)
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Reject fabricated or stale detached documents before storage access.
        if not isinstance(expected, dict):
            # Keep untracked state outside provider bytes.
            raise ConflictError("Hi-Lo state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Hi-Lo-owned fields on current state.
        def publish(current: dict) -> dict:
            # Detach provider-current game fields from unrelated siblings.
            observed = self._game_snapshot(current)
            # Accept an identical publication without rewriting siblings.
            if observed == desired:
                # Preserve the complete authoritative provider document.
                return current
            # Reject an operation whose game-owned baseline lost a race.
            if observed != expected:
                # Require recovery from the authoritative winning action.
                raise ConflictError("Hi-Lo state changed during this action; reload and retry")
            # Replace only the fields governed by this game service.
            for key, value in desired.items():
                # Publish detached values so caller mutation cannot leak later.
                current[key] = copy.deepcopy(value)
            # Return the complete document with every sibling preserved.
            return current

        # Commit through the provider's cross-process mutation boundary.
        authoritative = self._repository.update(player_id, publish)
        # Advance the in-memory baseline to the exact committed result.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(authoritative)

    # Build the public state, rules, and current-player payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return only sanitized game state and documented fixed rules.
        return {
            "game": GAME_ID,  # Identify the module for generic clients.
            "state": engine.public_state(state),  # Hide the unrevealed next card.
            "player": self._get_player(player_id),  # Expose the bound player's current wallet snapshot.
            "rules": {  # Group immutable table rules for generic frontend rendering.
                "guesses": list(engine.GUESSES),  # Advertise the two legal decisions.
                "ace_high": True,  # Explain rank ordering.
                "suits_break_ties": False,  # Explain equal-rank handling.
                "correct_return_multiplier": engine.CORRECT_RETURN_MULTIPLIER,  # Retain the deprecated frozen-v1 even-money scalar for legacy clients.
                "tie_return_multiplier": engine.TIE_RETURN_MULTIPLIER,  # Refund the wager on equal rank.
                "correct_paytable": engine.correct_paytable(),  # Publish the rank-priced correct return so clients never guess a price. (issue #406)
                "house_edge": engine.HOUSE_EDGE,  # State the constant edge the rank pricing holds at every current card. (issue #406)
            },
        }

    # Ensure a prepared round has one committed wager debit.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Apply or recover the stable deal action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["wager"], transaction_type="HI_LO_WAGER_DEBIT", round_id=round_state["round_id"], action_key=round_state["start_action_id"], request_fingerprint=round_state["request_fingerprint"], details={"stage": "deal", "wager": round_state["wager"], "current_card": round_state["current_card"]})
        # Mark the debit complete only after ledger proof exists.
        round_state["wager_status"] = "complete"
        # Store the immutable ledger id for diagnostics and retry evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal reloads avoid a recovery scan.
        self._save(player_id, state)
        # Return the committed event and replay flag.
        return event, replayed

    # Ensure a settled win or tie has at most one returned-token credit.
    def _ensure_settlement(self, player_id: str, state: dict, round_state: dict) -> tuple[dict | None, bool]:
        # Skip zero-value ledger rows for an incorrect prediction.
        if not round_state.get("payout"):
            # Mark the no-credit settlement complete.
            round_state["settlement_status"] = "complete"
            # Persist the terminal marker for reload safety.
            self._save(player_id, state)
            # Return no event and no ledger replay.
            return None, False
        # Use a distinct audit type for a tie refund versus a winning payout.
        transaction_type = "HI_LO_REFUND_CREDIT" if round_state.get("outcome") == "tie" else "HI_LO_PAYOUT_CREDIT"
        # Apply or recover the stable guess action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type=transaction_type, round_id=round_state["round_id"], action_key=round_state["guess_action_id"], request_fingerprint=round_state["guess_fingerprint"], details={"stage": "guess", "wager": round_state["wager"], "guess": round_state["guess"], "current_card": round_state["current_card"], "next_card": round_state["next_card"], "outcome": round_state["outcome"], "correct_return_multiplier": engine.correct_return_multiplier(round_state["current_card"])})
        # Mark the returned-token movement complete only after ledger proof exists.
        round_state["settlement_status"] = "complete"
        # Store the immutable refund or payout ledger id.
        round_state["settlement_ledger_id"] = event.get("ledger_id")
        # Persist the recovered or newly committed marker.
        self._save(player_id, state)
        # Return the committed event and replay evidence.
        return event, replayed

    # Recover ledger markers and completed settlement after a browser reload.
    def _recover(self, player_id: str, state: dict) -> None:
        # Inspect an active prepared round whose debit marker may have been lost.
        active = state.get("active_round")
        # Reconcile only a pending wager state.
        if active and active.get("wager_status") == "pending":
            # Find committed proof without charging from a read-only state request.
            event = self._ledger.find(player_id, active.get("start_action_id"))
            # Restore a lost state marker when the debit already committed.
            if event is not None:
                # Compare every semantic field before trusting recovered ledger proof.
                event_matches = event.get("transaction_type") == "HI_LO_WAGER_DEBIT" and event.get("round_id") == active.get("round_id") and round(float(event.get("amount", 0)), 2) == -round(float(active.get("wager", 0)), 2) and (event.get("details") or {}).get("request_fingerprint") == active.get("request_fingerprint")
                # Reject an action-id collision instead of marking the wrong debit complete.
                if not event_matches:
                    # Fail closed before publishing inconsistent state.
                    raise ConflictError("Recovered Hi-Lo wager action conflicts with prepared state")
                # Mark the committed wager complete.
                active["wager_status"] = "complete"
                # Restore the immutable ledger identifier.
                active["wager_ledger_id"] = event.get("ledger_id")
                # Persist recovered state before returning it.
                self._save(player_id, state)
            # Remove a prepared round whose debit never committed before interruption.
            else:
                # Clear the non-wagered choice safely.
                state["active_round"] = None
                # Release the uncommitted deal identity for a later safe retry.
                state.setdefault("action_receipts", {}).pop(active.get("start_action_id"), None)
                # Persist cleanup so the player may deal again.
                self._save(player_id, state)
        # Inspect retained settled rounds for a lost credit marker.
        for round_state in state.get("recent_rounds", []):
            # Complete only deterministic settlement that is explicitly pending.
            if round_state.get("settlement_status") == "pending":
                # Ensure the owed payout or refund exactly once during recovery.
                self._ensure_settlement(player_id, state, round_state)

    # Read reload-safe state for one authenticated player.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against concurrent actions for the same local process.
        with _ACTION_LOCK:
            # Load the newest player-scoped document inside the lock.
            state = self._load(player_id)
            # Recover committed or owed ledger movements before publishing state.
            self._recover(player_id, state)
            # Return sanitized state and current-player information.
            return self._payload(player_id, state)

    # Deal or replay one opening card after a retry-safe wager debit.
    def start_round(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Hi-Lo round body must be an object")
        # Validate the deal action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the wager before constructing a semantic fingerprint.
        wager = engine.normalize_wager(request.get("wager"))
        # Bind the action identity to the exact normalized wager.
        fingerprint = request_fingerprint({"stage": "deal", "wager": wager})
        # Serialize state preparation, debit, and marker persistence.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self._load(player_id)
            # Recover any interrupted prior action before enforcing active-round rules.
            self._recover(player_id, state)
            # Load durable compact receipts that prevent reuse after round-history pruning.
            receipts = state.setdefault("action_receipts", {})
            # Read any prior semantic owner for this action identity.
            receipt = receipts.get(action_id)
            # Find a retained deal with the same client action identity.
            existing = engine.round_for_start_action(state, action_id)
            # Replay the exact prepared or settled round when settings match.
            if existing is not None:
                # Reject action-id reuse with a changed wager.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail before a second ledger movement.
                    raise ConflictError("action_id was already used with a different Hi-Lo wager")
                # Build the canonical durable receipt for this retained deal.
                expected_receipt = {"stage": "deal", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Reject a corrupt receipt that maps the id to another semantic command.
                if receipt is not None and receipt != expected_receipt:
                    # Preserve the original receipt instead of issuing a movement.
                    raise ConflictError("action_id was already used for another Hi-Lo action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Ensure the original wager in case its marker was interrupted.
                wager_event, ledger_replayed = self._ensure_wager(player_id, state, existing)
                # Return the same round and ledger proof.
                return {"round": engine.public_round(existing), "wager": wager_event, "replayed": True, **self._payload(player_id, state)}
            # Reject an identity already retained for a guess action.
            if engine.action_owner(state, action_id) is not None:
                # Keep one action id bound to exactly one semantic command.
                raise ConflictError("action_id was already used for another Hi-Lo action")
            # Reject reuse when the owning round has aged out of bounded history.
            if receipt is not None:
                # Keep the durable action identity at-most-once across retained state.
                raise ConflictError("action_id belongs to an older Hi-Lo action")
            # Refuse to reconstruct cards if a committed debit outlived corrupt state.
            if self._ledger.find(player_id, action_id) is not None:
                # Preserve the committed debit without presenting a changed result.
                raise ConflictError("Committed Hi-Lo round state is unavailable")
            # Prevent overlapping wagers while one visible card awaits a choice.
            if state.get("active_round") is not None:
                # Require settlement of the active decision first.
                raise ConflictError("Finish the active Hi-Lo round before dealing again")
            # Derive deterministic cards only through the injected test hook.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Deal one visible and one private card through the shared primitive.
            current_card, next_card = engine.deal_pair(seed=seed)
            # Derive a stable route and ledger correlation id from authenticated input.
            round_id = engine.round_id_for(player_id, action_id)
            # Build prepared state before touching the shared ledger.
            round_state = engine.create_round(player_id, wager, action_id, current_card=current_card, next_card=next_card, round_id=round_id, created_at=self._clock(), request_fingerprint=fingerprint)
            # Persist the hidden deterministic result before any balance movement.
            state["active_round"] = round_state
            # Persist a compact action receipt before the wager can commit.
            receipts[action_id] = {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}
            # Save prepared state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Protect debit cleanup so insufficient funds does not strand a choice.
            try:
                # Apply or recover the one wager debit.
                wager_event, ledger_replayed = self._ensure_wager(player_id, state, round_state)
            # Clear only state proven to have no committed ledger movement.
            except Exception:
                # Check the append-only ledger before removing prepared recovery state.
                if self._ledger.find(player_id, action_id) is None:
                    # Clear the non-debited active round.
                    state["active_round"] = None
                    # Release the action id because no balance movement committed.
                    receipts.pop(action_id, None)
                    # Persist cleanup before propagating the original error.
                    self._save(player_id, state)
                # Re-raise the original storage or ledger error.
                raise
            # Return the visible card and committed wager evidence.
            return {"round": engine.public_round(round_state), "wager": wager_event, "replayed": ledger_replayed, **self._payload(player_id, state)}

    # Apply or replay one higher-or-lower decision and settlement.
    def guess(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Hi-Lo guess body must be an object")
        # Validate the settlement action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the two legal decision values.
        guess = engine.normalize_guess(request.get("guess"))
        # Bind the action to the exact round and direction.
        fingerprint = request_fingerprint({"stage": "guess", "round_id": round_id, "guess": guess})
        # Serialize reveal, archive, and returned-token settlement.
        with _ACTION_LOCK:
            # Load only the authenticated player's latest document.
            state = self._load(player_id)
            # Recover or clear any prepared wager before allowing a reveal action.
            self._recover(player_id, state)
            # Find the target without exposing another player's round.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session round ids identically.
            if round_state is None:
                # Return the stable public lookup error.
                raise NotFoundError("Hi-Lo round was not found")
            # Require append-only debit proof before any result can settle or credit.
            if round_state.get("wager_status") != "complete":
                # Fail closed rather than allowing a free prediction after interruption.
                raise ConflictError("Hi-Lo wager is not committed")
            # Load durable compact receipts that prevent cross-round action reuse.
            receipts = state.setdefault("action_receipts", {})
            # Read any prior semantic owner for this guess identity.
            receipt = receipts.get(action_id)
            # Build the canonical receipt expected for this exact decision.
            expected_receipt = {"stage": "guess", "round_id": round_id, "request_fingerprint": fingerprint}
            # Check whether this action id already belongs to a retained command.
            owner = engine.action_owner(state, action_id)
            # Reject reuse by another round or by the deal stage.
            if owner is not None and (owner[0].get("round_id") != round_id or owner[1] != "guess"):
                # Preserve one semantic action per id.
                raise ConflictError("action_id was already used for another Hi-Lo action")
            # Reject a durable receipt owned by a changed round or direction.
            if receipt is not None and receipt != expected_receipt:
                # Fail before revealing or settling another result.
                raise ConflictError("action_id was already used for another Hi-Lo action")
            # Reject an action id whose retained state was pruned but ledger proof remains.
            if owner is None and self._ledger.find(player_id, action_id) is not None:
                # Fail before revealing or archiving a different round.
                raise ConflictError("action_id was already used for another Hi-Lo action")
            # Replay only the original decision after settlement.
            if round_state.get("phase") == "settled":
                # Require the same action, direction, and fingerprint.
                if round_state.get("guess_action_id") != action_id or round_state.get("guess_fingerprint") != fingerprint:
                    # Reject a second terminal decision.
                    raise ConflictError("Hi-Lo round was already settled by another action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Recover any payout/refund marker lost after ledger commit.
                settlement_event, ledger_replayed = self._ensure_settlement(player_id, state, round_state)
                # Return the stable terminal result as a replay.
                return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": True, **self._payload(player_id, state)}
            # Require this exact round to remain in the actionable slot.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming actionable.
                raise ConflictError("Only the active Hi-Lo round can accept a guess")
            # Reveal and calculate the deterministic result without wallet mutation.
            engine.settle_round(round_state, guess, action_id, completed_at=self._clock(), request_fingerprint=fingerprint)
            # Record the durable decision identity before any returned-token credit.
            receipts[action_id] = expected_receipt
            # Archive the complete result before issuing any returned-token credit.
            engine.archive_round(state, round_state)
            # Persist terminal cards and pending settlement for crash recovery.
            self._save(player_id, state)
            # Apply or recover the payout/refund when one is due.
            settlement_event, ledger_replayed = self._ensure_settlement(player_id, state, round_state)
            # Return the revealed result and optional ledger proof.
            return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": ledger_replayed, **self._payload(player_id, state)}
