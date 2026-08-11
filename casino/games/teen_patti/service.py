# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for isolated Teen Patti Practice (#150)."""

# Import canonical JSON encoding for semantic action fingerprints.
import json
# Import hashing so changed retries fail even when wagers happen to match.
import hashlib
# Import regular expressions for bounded public action identities.
import re
# Import a reentrant lock for single-process state and ledger reconciliation.
import threading

# Import the only approved player-balance mutation service.
from casino.core import players
# Import the shared audit clock used by other game modules.
from casino.core.clock import utc_now
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistent state without editing shared storage code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic state and rule helpers.
from casino.games.teen_patti import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local history to preserve retry recovery for the supported simulator.
# Serialize action-id lookup and ledger writes inside the one-process server.
_ACTION_LOCK = threading.RLock()


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
    # Preserve the old Teen Patti key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "teen_patti_action_id", **kwargs)


# Coordinate player state, deterministic cards, and retry-safe ledger movements.
class TeenPattiService:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, get_player=None, clock=None, seed_factory=None, fixture_factory=None):
        # Use the game-local shared-ledger adapter unless a test supplies a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Load one authenticated player's isolated state document by default.
        self._load_state = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Save one authenticated player's isolated state document by default.
        self._save_state = state_saver or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Return read-only current-player information without balance mutation.
        self._get_player = get_player or players.get_player
        # Use the shared UTC clock unless a focused test pins timestamps.
        self._clock = clock or utc_now
        # Derive deterministic cards only through an injected non-production hook.
        self._seed_factory = seed_factory
        # Provide exact fixture rounds for focused tests without randomness.
        self._fixture_factory = fixture_factory

    # Save one player document through the injected persistence boundary.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate without mutating shared storage configuration.
        self._save_state(player_id, state)

    # Build the public state, rules, and current-player payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return only sanitized game state and documented fixed rules.
        return {
            "game": GAME_ID,  # Identify the module for generic clients.
            "state": engine.public_state(state),  # Hide unrevealed dealer cards and fingerprints.
            "player": self._get_player(player_id),  # Expose the bound player's current wallet snapshot.
            "rules": {  # Group immutable table rules for generic frontend rendering.
                "decisions": list(engine.DECISIONS),  # Advertise the legal decisions after the deal.
                "dealer_qualifies": "queen_high_or_better",  # Document the qualification profile.
                "bonus_multipliers": dict(engine.BONUS_MULTIPLIERS),  # Publish the Bonus paytable rows.
                "hand_rank_order": list(reversed(engine.THREE_CARD_CATEGORIES)),  # Publish the strongest-first ranking.
            },
        }

    # Ensure a prepared round has one committed ante debit.
    def _ensure_opening(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Apply or recover the stable deal action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["ante"], transaction_type="TEEN_PATTI_ANTE_DEBIT", round_id=round_state["round_id"], action_id=round_state["start_action_id"], fingerprint=round_state["request_fingerprint"], details={"stage": "ante", "ante": round_state["ante"]})
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
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["play_wager"], transaction_type="TEEN_PATTI_PLAY_DEBIT", round_id=round_state["round_id"], action_id=round_state["decision_action_id"], fingerprint=round_state["decision_fingerprint"], details={"stage": "play", "ante": round_state["ante"], "play_wager": round_state["play_wager"]})
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
        # Skip zero-value ledger rows for folds and dealer wins.
        if not round_state.get("payout"):
            # Mark the no-credit settlement complete.
            round_state["settlement_status"] = "complete"
            # Persist the terminal marker for reload safety.
            self._save(player_id, state)
            # Return no event and no ledger replay.
            return None, False
        # Apply or recover the stable settlement through a derived action id.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="TEEN_PATTI_SETTLEMENT_CREDIT", round_id=round_state["round_id"], action_id=f"{round_state['decision_action_id']}:settlement", fingerprint=round_state["decision_fingerprint"], details={"stage": "settlement", "outcome": round_state.get("outcome"), "ante_credit": round_state.get("ante_credit"), "play_credit": round_state.get("play_credit"), "bonus_credit": round_state.get("bonus_credit")})
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
                # Ensure the owed payout exactly once during recovery.
                self._ensure_settlement(player_id, state, round_state)

    # Read reload-safe state for one authenticated player.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against concurrent actions for the same local process.
        with _ACTION_LOCK:
            # Load the newest player-scoped document inside the lock.
            state = self._load_state(player_id)
            # Recover committed or owed ledger movements before publishing state.
            self._recover(player_id, state)
            # Return sanitized state and current-player information.
            return self._payload(player_id, state)

    # Deal or replay one opening hand after a retry-safe ante debit.
    def start_round(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Teen Patti round body must be an object")
        # Validate the deal action identity used for network retries.
        action_id = require_action_id(request.get("action_id") or request.get("request_id"))
        # Normalize the ante before constructing a semantic fingerprint.
        ante = engine.normalize_ante(request.get("ante"))
        # Bind the action identity to the exact normalized ante.
        fingerprint = request_fingerprint({"stage": "deal", "ante": ante})
        # Serialize state preparation, debit, and marker persistence.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self._load_state(player_id)
            # Recover any interrupted prior action before enforcing active-round rules.
            self._recover(player_id, state)
            # Load durable compact receipts that prevent reuse after round-history pruning.
            receipts = state.setdefault("action_receipts", {})
            # Find a retained deal with the same client action identity.
            existing = engine.round_for_start_action(state, action_id)
            # Replay the exact prepared or settled round when settings match.
            if existing is not None:
                # Reject action-id reuse with a changed ante.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail before a second ledger movement.
                    raise ConflictError("action_id was already used with a different Teen Patti ante")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = {"stage": "deal", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Ensure the original ante in case its marker was interrupted.
                opening_event, ledger_replayed = self._ensure_opening(player_id, state, existing)
                # Return the same round and ledger proof.
                return {"round": engine.public_round(existing), "opening": opening_event, "replayed": True, "ledger_replayed": ledger_replayed, **self._payload(player_id, state)}
            # Reject reuse when the action id already owns another command.
            if engine.action_owner(state, action_id) is not None or action_id in receipts or self._ledger.find(player_id, action_id) is not None:
                # Keep one action id bound to exactly one semantic command.
                raise ConflictError("action_id was already used for another Teen Patti action")
            # Prevent overlapping antes while a deal awaits play/fold.
            if state.get("active_round") is not None:
                # Require settlement of the active decision first.
                raise ConflictError("Finish the active Teen Patti round before dealing again")
            # Derive deterministic cards only through the injected test hook.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Read an optional exact fixture for deterministic outcome tests.
            fixture = self._fixture_factory(action_id) if self._fixture_factory else None
            # Derive a stable route and ledger correlation id from authenticated input.
            round_id = engine.round_id_for(player_id, action_id)
            # Build prepared state before touching the shared ledger.
            round_state = engine.create_round(player_id, ante, action_id, round_id=round_id, created_at=self._clock(), request_fingerprint=fingerprint, seed=seed, fixture=fixture)
            # Persist the hidden deterministic table before any balance movement.
            state["active_round"] = round_state
            # Persist a compact action receipt before the opening can commit.
            receipts[action_id] = {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}
            # Save prepared state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Protect debit cleanup so insufficient funds does not strand a decision.
            try:
                # Apply or recover the one ante debit.
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
            # Return the visible player cards and committed ante evidence.
            return {"round": engine.public_round(round_state), "opening": opening_event, "replayed": ledger_replayed, **self._payload(player_id, state)}

    # Apply or replay one play/fold decision and any settlement.
    def decide(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Teen Patti decision body must be an object")
        # Validate the decision action identity used for network retries.
        action_id = require_action_id(request.get("action_id") or request.get("request_id"))
        # Normalize the play-or-fold decision.
        decision = engine.normalize_decision(request.get("decision"))
        # Bind the action to the exact round and decision.
        fingerprint = request_fingerprint({"stage": "decision", "round_id": round_id, "decision": decision})
        # Serialize reveal, play debit, archive, and returned-token settlement.
        with _ACTION_LOCK:
            # Load only the authenticated player's latest document.
            state = self._load_state(player_id)
            # Recover or clear any interrupted action before allowing a decision.
            self._recover(player_id, state)
            # Find the target without exposing another player's round.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session round ids identically.
            if round_state is None:
                # Return the stable public lookup error.
                raise NotFoundError("Teen Patti round was not found")
            # Require append-only ante proof before any decision can proceed.
            if round_state.get("opening_status") != "complete":
                # Fail closed rather than allowing a free play or fold.
                raise ConflictError("Teen Patti ante is not committed")
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
                raise ConflictError("action_id was already used for another Teen Patti action")
            # Reject a durable receipt owned by a changed round or decision.
            if receipt is not None and receipt != expected_receipt:
                # Fail before revealing or settling another result.
                raise ConflictError("action_id was already used for another Teen Patti action")
            # Reject an action id whose retained state was pruned but ledger proof remains.
            if owner is None and self._ledger.find(player_id, action_id) is not None:
                # Fail before revealing or archiving a different round.
                raise ConflictError("action_id was already used for another Teen Patti action")
            # Replay only the original decision after settlement.
            if round_state.get("phase") == "settled":
                # Require the same action, decision, and fingerprint.
                if round_state.get("decision_action_id") != action_id or round_state.get("decision_fingerprint") != fingerprint:
                    # Reject a second terminal decision.
                    raise ConflictError("Teen Patti round was already settled by another action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Recover any settlement marker lost after ledger commit.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
                # Return the stable terminal result as a replay.
                return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": True, "ledger_replayed": settlement_replayed, **self._payload(player_id, state)}
            # Require this exact round to remain in the actionable slot.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming actionable.
                raise ConflictError("Only the active Teen Patti round can accept a decision")
            # Resolve folds without any extra ledger movement.
            if decision == "fold":
                # Apply the terminal fold transition.
                engine.fold_round(round_state, action_id, completed_at=self._clock(), request_fingerprint=fingerprint)
                # Persist the durable decision identity.
                receipts[action_id] = expected_receipt
                # Archive the terminal fold.
                engine.archive_round(state, round_state)
                # Persist terminal state before returning.
                self._save(player_id, state)
                # Return the folded result without a settlement ledger event.
                return {"round": engine.public_round(round_state), "settlement": None, "replayed": False, **self._payload(player_id, state)}
            # Prepare the play decision before touching the play wager.
            engine.prepare_play(round_state, action_id, request_fingerprint=fingerprint)
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
