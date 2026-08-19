# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for isolated Four Card Poker (#141)."""

# Import copy support for detached optimistic snapshots and provider publication.
import copy
# Import canonical JSON encoding for semantic action fingerprints.
import json
# Import hashing so changed retries fail even when wagers happen to match.
import hashlib
# Import regular expressions for bounded public action identities.
import re
# Import bounded player-scoped serialization so unrelated wallets can proceed concurrently.
from casino.core.player_locks import player_action_lock

# Import the only approved player-balance mutation service.
from casino.core import players
# Import the shared audit clock used by other game modules.
from casino.core.clock import utc_now
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistent state without editing shared storage code.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic state and rule helpers.
from casino.games.four_card_poker import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local history to preserve retry recovery for the supported simulator.
# Keep one operation's optimistic comparison snapshot outside persistent game state.
_ATOMIC_BASELINE_KEY = "_four_card_poker_atomic_baseline"
# Name only the Four Card Poker fields one transition may replace.
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


# Persist player-scoped Four Card Poker documents through the selected provider.
class StateRepository:
    # Load one authenticated player's isolated document.
    def load(self, player_id: str) -> dict:
        # Delegate JSON/MySQL selection and default-state repair to shared storage.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Apply one transition while the selected provider owns its process boundary.
    def update(self, player_id: str, mutator) -> dict:
        # Delegate latest-state loading, callback rollback, and publication atomically.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state)


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old Four Card key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "four_card_poker_action_id", **kwargs)


# Coordinate player state, deterministic cards, and retry-safe ledger movements.
class FourCardPokerService:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, repository=None, ledger_gateway=None, get_player=None, clock=None, seed_factory=None, fixture_factory=None):
        # Use provider-backed player state unless a focused test supplies memory storage.
        self._repository = repository or StateRepository()
        # Use the game-local shared-ledger adapter unless a test supplies a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Return read-only current-player information without balance mutation.
        self._get_player = get_player or players.get_player
        # Use the shared UTC clock unless a focused test pins timestamps.
        self._clock = clock or utc_now
        # Derive deterministic cards only through an injected non-production hook.
        self._seed_factory = seed_factory
        # Provide exact fixture rounds for focused tests without randomness.
        self._fixture_factory = fixture_factory

    # Capture only the game fields owned by Four Card Poker transitions.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Detach nested rounds and receipts from later engine mutation.
        return {key: copy.deepcopy(state.get(key, engine.default_state()[key])) for key in _GAME_STATE_KEYS}

    # Load one document and bind its provider-current baseline to this operation.
    def _load(self, player_id: str) -> dict:
        # Read through the injected repository before any local engine mutation.
        state = self._repository.load(player_id)
        # Retain the exact owned values the next publication expects to replace.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting the private baseline field.
        return state

    # Publish one compare-and-replace transition while preserving unrelated siblings.
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read or prior result.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Refuse an untracked whole-document write before entering provider storage.
        if not isinstance(expected, dict):
            # Keep accidental stale saves outside persistent player state.
            raise ConflictError("Four Card Poker state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only owned game fields against provider-latest state.
        def publish(current: dict) -> dict:
            # Capture provider-current game fields without metadata or unrelated siblings.
            observed = self._game_snapshot(current)
            # Accept exact same-result completion without overwriting provider-owned values.
            if observed == desired:
                # Preserve current metadata and siblings unchanged.
                return current
            # Reject a stale transition before it can replace another action's state.
            if observed != expected:
                # Require a fresh load and authoritative recovery from the winning transition.
                raise ConflictError("Four Card Poker state changed during this action; reload and retry")
            # Replace only the three fields owned by the Four Card Poker engine.
            for key, value in desired.items():
                # Publish detached values so later caller mutation cannot leak into storage.
                current[key] = copy.deepcopy(value)
            # Return the complete provider document with every sibling preserved.
            return current

        # Commit through the provider's cross-process read-modify-write boundary.
        authoritative = self._repository.update(player_id, publish)
        # Advance the private baseline to the exact committed game-owned result.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(authoritative)

    # Build the public state, rules, and current-player payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return only sanitized game state and documented fixed rules.
        return {
            "game": GAME_ID,  # Identify the module for generic clients.
            "state": engine.public_state(state),  # Hide unrevealed dealer cards and fingerprints.
            "player": self._get_player(player_id),  # Expose the bound player's current wallet snapshot.
            "rules": {  # Group immutable table rules for generic frontend rendering.
                "decisions": list(engine.DECISIONS),  # Advertise the legal decisions after the deal.
                "play_multipliers": list(engine.PLAY_MULTIPLIERS),  # Document the one-to-three-times play raise.
                "dealer_qualifies": "none",  # Document that the dealer never needs to qualify.
                "ante_bonus_multipliers": dict(engine.ANTE_BONUS_MULTIPLIERS),  # Publish the Ante Bonus paytable rows.
                "aces_up_multipliers": dict(engine.ACES_UP_MULTIPLIERS),  # Publish the Aces Up paytable rows.
            },
        }

    # Ensure a prepared round has one committed opening debit for the ante and Aces Up bet.
    def _ensure_opening(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Combine the ante and any Aces Up side bet into one opening debit.
        opening_amount = round(round_state["ante"] + round_state["aces_up"], 2)
        # Apply or recover the stable deal action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-opening_amount, transaction_type="FOUR_CARD_POKER_OPENING_DEBIT", round_id=round_state["round_id"], action_key=round_state["start_action_id"], request_fingerprint=round_state["request_fingerprint"], details={"stage": "deal", "ante": round_state["ante"], "aces_up": round_state["aces_up"]})
        # Mark the debit complete only after ledger proof exists.
        round_state["opening_status"] = "complete"
        # Store the immutable ledger id for diagnostics and retry evidence.
        round_state["opening_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal reloads avoid a recovery scan.
        self._save(player_id, state)
        # Return the committed event and replay flag.
        return event, replayed

    # Ensure a prepared play has one committed play debit.
    def _ensure_play(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Apply or recover the stable play action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["play_wager"], transaction_type="FOUR_CARD_POKER_PLAY_DEBIT", round_id=round_state["round_id"], action_key=round_state["decision_action_id"], request_fingerprint=round_state["decision_fingerprint"], details={"stage": "play", "ante": round_state["ante"], "play_wager": round_state["play_wager"], "multiplier": round_state["play_multiplier"]})
        # Mark the play debit complete only after ledger proof exists.
        round_state["play_status"] = "complete"
        # Store the immutable ledger id for diagnostics and retry evidence.
        round_state["play_ledger_id"] = event.get("ledger_id")
        # Persist the marker so reloads can safely resolve the showdown.
        self._save(player_id, state)
        # Return the committed event and replay flag.
        return event, replayed

    # Ensure a terminal round has at most one returned-token credit.
    def _ensure_settlement(self, player_id: str, state: dict, round_state: dict) -> tuple[dict | None, bool]:
        # Skip zero-value ledger rows for losses that return nothing.
        if not round_state.get("payout"):
            # Mark the no-credit settlement complete.
            round_state["settlement_status"] = "complete"
            # Persist the terminal marker for reload safety.
            self._save(player_id, state)
            # Return no event and no ledger replay.
            return None, False
        # Apply or recover the stable settlement through a derived action id.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="FOUR_CARD_POKER_SETTLEMENT_CREDIT", round_id=round_state["round_id"], action_key=f"{round_state['decision_action_id']}:settlement", request_fingerprint=round_state["decision_fingerprint"], details={"stage": "settlement", "outcome": round_state.get("outcome"), "ante_credit": round_state.get("ante_credit"), "play_credit": round_state.get("play_credit"), "ante_bonus_credit": round_state.get("ante_bonus_credit"), "aces_up_credit": round_state.get("aces_up_credit")})
        # Mark the returned-token movement complete only after ledger proof exists.
        round_state["settlement_status"] = "complete"
        # Store the immutable payout ledger id.
        round_state["settlement_ledger_id"] = event.get("ledger_id")
        # Persist the recovered or newly committed marker.
        self._save(player_id, state)
        # Return the committed event and replay evidence.
        return event, replayed

    # Recover ledger markers and completed settlement after a browser reload.
    def _recover(self, player_id: str, state: dict) -> None:
        # Inspect an active prepared round whose opening marker may have been lost.
        active = state.get("active_round")
        # Reconcile only when an active round exists.
        if active:
            # Clear a non-committed opening instead of charging from a read-only state request.
            if active.get("opening_status") == "pending":
                # Look for committed proof before deciding whether the action survived.
                event = self._ledger.find(player_id, active.get("start_action_id"))
                # Restore a lost opening marker when the debit already committed.
                if event is not None:
                    # Mark the committed opening complete.
                    active["opening_status"] = "complete"
                    # Restore the immutable ledger identifier.
                    active["opening_ledger_id"] = event.get("ledger_id")
                    # Persist recovered state before returning it.
                    self._save(player_id, state)
                # Remove a prepared round whose opening never committed before interruption.
                else:
                    # Clear the non-wagered decision safely.
                    state["active_round"] = None
                    # Release the uncommitted deal identity for a later safe retry.
                    state.setdefault("action_receipts", {}).pop(active.get("start_action_id"), None)
                    # Persist cleanup so the player may deal again.
                    self._save(player_id, state)
                    # Stop recovery because the active round was cleared.
                    return
            # Recover or roll back a play that was saved before its debit marker.
            if active.get("phase") == "playing" and active.get("play_status") == "pending":
                # Look for committed proof before resolving the showdown.
                event = self._ledger.find(player_id, active.get("decision_action_id"))
                # Restore the play marker only when the debit already committed.
                if event is not None:
                    # Mark the committed play complete.
                    active["play_status"] = "complete"
                    # Restore the immutable ledger identifier.
                    active["play_ledger_id"] = event.get("ledger_id")
                    # Persist recovered play proof before showdown.
                    self._save(player_id, state)
                # Return the round to decision when no play debit exists.
                else:
                    # Release the uncommitted decision identity.
                    state.setdefault("action_receipts", {}).pop(active.get("decision_action_id"), None)
                    # Restore a play/foldable decision state.
                    engine.reset_uncommitted_play(active)
                    # Persist rollback before publishing state.
                    self._save(player_id, state)
                    # Stop because there is no committed play to settle.
                    return
            # Resolve a committed play whose terminal state was interrupted.
            if active.get("phase") == "playing" and active.get("play_status") == "complete":
                # Complete deterministic showdown from persisted hidden cards.
                engine.resolve_playing_round(active, completed_at=self._clock())
                # Move the terminal round into bounded history.
                engine.archive_round(state, active)
                # Persist terminal state before returned-token recovery.
                self._save(player_id, state)
                # Ensure any owed returned-token credit exactly once.
                self._ensure_settlement(player_id, state, active)
        # Inspect retained settled rounds for a lost returned-token marker.
        for round_state in state.get("recent_rounds", []):
            # Complete only deterministic settlement that is explicitly pending.
            if round_state.get("settlement_status") == "pending":
                # Ensure the owed payout or Aces Up return exactly once during recovery.
                self._ensure_settlement(player_id, state, round_state)

    # Read reload-safe state for one authenticated player.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against concurrent actions for the same local process.
        with player_action_lock(player_id):
            # Load the newest player-scoped document inside the lock.
            state = self._load(player_id)
            # Recover committed or owed ledger movements before publishing state.
            self._recover(player_id, state)
            # Return sanitized state and current-player information.
            return self._payload(player_id, state)

    # Deal or replay one opening hand after a retry-safe opening debit.
    def start_round(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Four Card Poker round body must be an object")
        # Validate the deal action identity used for network retries.
        action_id = require_action_id(request.get("action_id") or request.get("request_id"))
        # Normalize the ante before constructing a semantic fingerprint.
        ante = engine.normalize_ante(request.get("ante"))
        # Normalize the optional Aces Up side bet.
        aces_up = engine.normalize_aces_up(request.get("aces_up"))
        # Bind the action identity to the exact normalized opening wagers.
        fingerprint = request_fingerprint({"stage": "deal", "ante": ante, "aces_up": aces_up})
        # Serialize state preparation, debit, and marker persistence.
        with player_action_lock(player_id):
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
                # Reject action-id reuse with a changed opening wager.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail before a second ledger movement.
                    raise ConflictError("action_id was already used with a different Four Card Poker opening")
                # Build the canonical durable receipt for this retained deal.
                expected_receipt = {"stage": "deal", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Reject a corrupt receipt that maps the id to another semantic command.
                if receipt is not None and receipt != expected_receipt:
                    # Preserve the original receipt instead of issuing a movement.
                    raise ConflictError("action_id was already used for another Four Card Poker action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Ensure the original opening in case its marker was interrupted.
                opening_event, ledger_replayed = self._ensure_opening(player_id, state, existing)
                # Return the same round and ledger proof.
                return {"round": engine.public_round(existing), "opening": opening_event, "replayed": True, "ledger_replayed": ledger_replayed, **self._payload(player_id, state)}
            # Reject an identity already retained for a decision action.
            if engine.action_owner(state, action_id) is not None:
                # Keep one action id bound to exactly one semantic command.
                raise ConflictError("action_id was already used for another Four Card Poker action")
            # Reject reuse when the owning round has aged out of bounded history.
            if receipt is not None:
                # Keep the durable action identity at-most-once across retained state.
                raise ConflictError("action_id belongs to an older Four Card Poker action")
            # Refuse to reconstruct cards if a committed debit outlived corrupt state.
            if self._ledger.find(player_id, action_id) is not None:
                # Preserve the committed debit without presenting a changed result.
                raise ConflictError("Committed Four Card Poker round state is unavailable")
            # Prevent overlapping openings while a deal awaits play/fold.
            if state.get("active_round") is not None:
                # Require settlement of the active decision first.
                raise ConflictError("Finish the active Four Card Poker round before dealing again")
            # Derive deterministic cards only through the injected test hook.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Read an optional exact fixture for deterministic outcome tests.
            fixture = self._fixture_factory(action_id) if self._fixture_factory else None
            # Derive a stable route and ledger correlation id from authenticated input.
            round_id = engine.round_id_for(player_id, action_id)
            # Build prepared state before touching the shared ledger.
            round_state = engine.create_round(player_id, ante, aces_up, action_id, round_id=round_id, created_at=self._clock(), request_fingerprint=fingerprint, seed=seed, fixture=fixture)
            # Persist the hidden deterministic table before any balance movement.
            state["active_round"] = round_state
            # Persist a compact action receipt before the opening can commit.
            receipts[action_id] = {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}
            # Save prepared state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Protect debit cleanup so insufficient funds does not strand a decision.
            try:
                # Apply or recover the one opening debit.
                opening_event, ledger_replayed = self._ensure_opening(player_id, state, round_state)
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
            # Return the visible player cards and committed opening evidence.
            return {"round": engine.public_round(round_state), "opening": opening_event, "replayed": ledger_replayed, **self._payload(player_id, state)}

    # Apply or replay one play/fold decision and any settlement.
    def decide(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Four Card Poker decision body must be an object")
        # Validate the decision action identity used for network retries.
        action_id = require_action_id(request.get("action_id") or request.get("request_id"))
        # Normalize the play-or-fold decision.
        decision = engine.normalize_decision(request.get("decision"))
        # Normalize the play multiplier only when playing; folds carry no raise.
        multiplier = engine.normalize_multiplier(request.get("multiplier", 1)) if decision == "play" else None
        # Bind the action to the exact round, decision, and raise size.
        fingerprint = request_fingerprint({"stage": "decision", "round_id": round_id, "decision": decision, "multiplier": multiplier})
        # Serialize reveal, play debit, archive, and returned-token settlement.
        with player_action_lock(player_id):
            # Load only the authenticated player's latest document.
            state = self._load(player_id)
            # Recover or clear any interrupted action before allowing a decision.
            self._recover(player_id, state)
            # Find the target without exposing another player's round.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session round ids identically.
            if round_state is None:
                # Return the stable public lookup error.
                raise NotFoundError("Four Card Poker round was not found")
            # Require append-only opening proof before any decision can proceed.
            if round_state.get("opening_status") != "complete":
                # Fail closed rather than allowing a free play or fold.
                raise ConflictError("Four Card Poker opening is not committed")
            # Load durable compact receipts that prevent cross-round action reuse.
            receipts = state.setdefault("action_receipts", {})
            # Read any prior semantic owner for this decision identity.
            receipt = receipts.get(action_id)
            # Build the canonical receipt expected for this exact decision.
            expected_receipt = {"stage": "decision", "round_id": round_id, "request_fingerprint": fingerprint}
            # Check whether this action id already belongs to a retained command.
            owner = engine.action_owner(state, action_id)
            # Reject reuse by another round or by the deal stage.
            if owner is not None and (owner[0].get("round_id") != round_id or owner[1] != "decision"):
                # Preserve one semantic action per id.
                raise ConflictError("action_id was already used for another Four Card Poker action")
            # Reject a durable receipt owned by a changed round or decision.
            if receipt is not None and receipt != expected_receipt:
                # Fail before revealing or settling another result.
                raise ConflictError("action_id was already used for another Four Card Poker action")
            # Reject an action id whose retained state was pruned but ledger proof remains.
            if owner is None and self._ledger.find(player_id, action_id) is not None:
                # Fail before revealing or archiving a different round.
                raise ConflictError("action_id was already used for another Four Card Poker action")
            # Replay only the original decision after settlement.
            if round_state.get("phase") == "settled":
                # Require the same action, decision, and fingerprint.
                if round_state.get("decision_action_id") != action_id or round_state.get("decision_fingerprint") != fingerprint:
                    # Reject a second terminal decision.
                    raise ConflictError("Four Card Poker round was already settled by another action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Recover any settlement marker lost after ledger commit.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
                # Return the stable terminal result as a replay.
                return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": True, "ledger_replayed": settlement_replayed, **self._payload(player_id, state)}
            # Require this exact round to remain in the actionable slot.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming actionable.
                raise ConflictError("Only the active Four Card Poker round can accept a decision")
            # Resolve folds, which still settle the independent Aces Up side bet.
            if decision == "fold":
                # Apply the terminal fold transition and compute any Aces Up return.
                engine.fold_round(round_state, action_id, completed_at=self._clock(), request_fingerprint=fingerprint)
                # Persist the durable decision identity.
                receipts[action_id] = expected_receipt
                # Archive the terminal fold.
                engine.archive_round(state, round_state)
                # Persist terminal state before returned-token recovery.
                self._save(player_id, state)
                # Apply or recover any Aces Up return owed on the fold.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
                # Return the folded result and optional Aces Up ledger proof.
                return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": settlement_replayed, **self._payload(player_id, state)}
            # Prepare the play decision before touching the play wager.
            engine.prepare_play(round_state, action_id, multiplier, request_fingerprint=fingerprint)
            # Record the durable decision identity before the play can commit.
            receipts[action_id] = expected_receipt
            # Persist the pending play for crash recovery.
            self._save(player_id, state)
            # Protect play cleanup so insufficient funds does not strand a playing state.
            try:
                # Apply or recover the play debit.
                play_event, play_replayed = self._ensure_play(player_id, state, round_state)
            # Clear only state proven to have no committed play movement.
            except Exception:
                # Check the append-only ledger before rolling the play preparation back.
                if self._ledger.find(player_id, action_id) is None:
                    # Release the decision action id because no play movement committed.
                    receipts.pop(action_id, None)
                    # Restore the decision phase.
                    engine.reset_uncommitted_play(round_state)
                    # Persist cleanup before propagating the original error.
                    self._save(player_id, state)
                # Re-raise the original storage or ledger error.
                raise
            # Resolve the deterministic showdown after the play debit is committed.
            engine.resolve_playing_round(round_state, completed_at=self._clock())
            # Archive the complete result before issuing any returned-token credit.
            engine.archive_round(state, round_state)
            # Persist terminal cards and pending settlement for crash recovery.
            self._save(player_id, state)
            # Apply or recover the payout when one is due.
            settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
            # Return the revealed result and optional ledger proof.
            return {"round": engine.public_round(round_state), "play": play_event, "settlement": settlement_event, "replayed": play_replayed or settlement_replayed, **self._payload(player_id, state)}
