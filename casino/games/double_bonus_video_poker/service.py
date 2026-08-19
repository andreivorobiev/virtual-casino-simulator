# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for isolated Double Bonus Video Poker (#131)."""

# Import deep-copy support for detached optimistic state snapshots.
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
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic state and rule helpers.
from casino.games.double_bonus_video_poker import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local history to preserve retry recovery for the supported simulator.
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_double_bonus_atomic_baseline"
# Name every state field owned by Double Bonus transitions.
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
    # Preserve the old Double Bonus key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "double_bonus_video_poker_action_id", **kwargs)


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
class DoubleBonusVideoPokerService:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, ledger_gateway=None, repository=None, get_player=None, clock=None, seed_factory=None, fixture_factory=None):
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
        # Provide exact fixture rounds for focused tests without randomness.
        self._fixture_factory = fixture_factory

    # Capture only the fields owned by Double Bonus transitions.
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

    # Publish one provider-current compare-and-replace transition. (DBVP-003)
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Reject fabricated or stale detached documents before storage access.
        if not isinstance(expected, dict):
            # Keep untracked state outside provider bytes.
            raise ConflictError("Double Bonus state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Double Bonus-owned fields on current state.
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
                raise ConflictError("Double Bonus state changed during this action; reload and retry")
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
            "state": engine.public_state(state),  # Hide the unrevealed replacement pile and fingerprints.
            "player": self._get_player(player_id),  # Expose the bound player's current wallet snapshot.
            "rules": {  # Group immutable table rules for generic frontend rendering.
                "hand_size": engine.HAND_SIZE,  # Document the five-card hand.
                "paytable": dict(engine.PAYTABLE),  # Publish the nine-six Double Bonus paytable rows.
            },
        }

    # Ensure a prepared round has one committed bet debit.
    def _ensure_opening(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Apply or recover the stable deal action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["bet"], transaction_type="DOUBLE_BONUS_VIDEO_POKER_WAGER_DEBIT", round_id=round_state["round_id"], action_key=round_state["start_action_id"], request_fingerprint=round_state["request_fingerprint"], details={"stage": "deal", "bet": round_state["bet"]})
        # Mark the debit complete only after ledger proof exists.
        round_state["opening_status"] = "complete"
        # Store the immutable ledger id for diagnostics and retry evidence.
        round_state["opening_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal reloads avoid a recovery scan.
        self._save(player_id, state)
        # Return the committed event and replay flag.
        return event, replayed

    # Ensure a terminal round has at most one returned-token credit.
    def _ensure_settlement(self, player_id: str, state: dict, round_state: dict) -> tuple[dict | None, bool]:
        # Skip zero-value ledger rows for losing hands.
        if not round_state.get("payout"):
            # Mark the no-credit settlement complete.
            round_state["settlement_status"] = "complete"
            # Persist the terminal marker for reload safety.
            self._save(player_id, state)
            # Return no event and no ledger replay.
            return None, False
        # Apply or recover the stable settlement through a derived action id.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="DOUBLE_BONUS_VIDEO_POKER_SETTLEMENT_CREDIT", round_id=round_state["round_id"], action_key=f"{round_state['draw_action_id']}:settlement", request_fingerprint=round_state["draw_fingerprint"], details={"stage": "settlement", "hand_tier": round_state.get("hand_tier"), "multiplier": round_state.get("multiplier")})
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
        if active and active.get("opening_status") == "pending":
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
        # Inspect retained settled rounds for a lost returned-token marker.
        for round_state in state.get("recent_rounds", []):
            # Complete only deterministic settlement that is explicitly pending.
            if round_state.get("settlement_status") == "pending":
                # Ensure the owed payout exactly once during recovery.
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

    # Deal or replay one video-poker hand after a retry-safe bet debit.
    def start_round(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Double Bonus round body must be an object")
        # Validate the deal action identity used for network retries.
        action_id = require_action_id(request.get("action_id") or request.get("request_id"))
        # Normalize the bet before constructing a semantic fingerprint.
        bet = engine.normalize_bet(request.get("bet"))
        # Bind the action identity to the exact normalized bet.
        fingerprint = request_fingerprint({"stage": "deal", "bet": bet})
        # Serialize state preparation, debit, and marker persistence.
        with player_action_lock(player_id):
            # Load the current player's state inside the critical section.
            state = self._load(player_id)
            # Recover any interrupted prior action before enforcing active-round rules.
            self._recover(player_id, state)
            # Load durable compact receipts that prevent reuse after round-history pruning.
            receipts = state.setdefault("action_receipts", {})
            # Find a retained deal with the same client action identity.
            existing = engine.round_for_start_action(state, action_id)
            # Replay the exact prepared or settled round when settings match.
            if existing is not None:
                # Reject action-id reuse with a changed bet.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail before a second ledger movement.
                    raise ConflictError("action_id was already used with a different Double Bonus bet")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = {"stage": "deal", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Ensure the original bet in case its marker was interrupted.
                opening_event, ledger_replayed = self._ensure_opening(player_id, state, existing)
                # Return the same round and ledger proof.
                return {"round": engine.public_round(existing), "opening": opening_event, "replayed": True, "ledger_replayed": ledger_replayed, **self._payload(player_id, state)}
            # Reject reuse when the action id already owns another command.
            if action_id in receipts or self._ledger.find(player_id, action_id) is not None:
                # Keep one action id bound to exactly one semantic command.
                raise ConflictError("action_id was already used for another Double Bonus action")
            # Prevent overlapping deals while a hand awaits its draw.
            if state.get("active_round") is not None:
                # Require the active draw first.
                raise ConflictError("Finish the active Double Bonus round before dealing again")
            # Derive deterministic cards only through the injected test hook.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Read an optional exact fixture for deterministic outcome tests.
            fixture = self._fixture_factory(action_id) if self._fixture_factory else None
            # Derive a stable route and ledger correlation id from authenticated input.
            round_id = engine.round_id_for(player_id, action_id)
            # Build prepared state before touching the shared ledger.
            round_state = engine.create_round(player_id, bet, action_id, round_id=round_id, created_at=self._clock(), request_fingerprint=fingerprint, seed=seed, fixture=fixture)
            # Persist the hidden deterministic table before any balance movement.
            state["active_round"] = round_state
            # Persist a compact action receipt before the bet can commit.
            receipts[action_id] = {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}
            # Save prepared state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Protect debit cleanup so insufficient funds does not strand a decision.
            try:
                # Apply or recover the one bet debit.
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
            # Return the visible dealt hand and committed bet evidence.
            return {"round": engine.public_round(round_state), "opening": opening_event, "replayed": ledger_replayed, **self._payload(player_id, state)}

    # Apply or replay one hold-and-draw decision.
    def decide(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Double Bonus decision body must be an object")
        # Validate the draw action identity used for network retries.
        action_id = require_action_id(request.get("action_id") or request.get("request_id"))
        # Normalize the hold selection.
        hold = engine.normalize_hold(request.get("hold"))
        # Bind the action to the exact round and hold selection.
        fingerprint = request_fingerprint({"stage": "draw", "round_id": round_id, "hold": list(hold)})
        # Serialize reveal, draw, archive, and settlement.
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
                raise NotFoundError("Double Bonus round was not found")
            # Require append-only bet proof before any draw can proceed.
            if round_state.get("opening_status") != "complete":
                # Fail closed rather than allowing a free draw.
                raise ConflictError("Double Bonus bet is not committed")
            # Load durable compact receipts that prevent cross-round action reuse.
            receipts = state.setdefault("action_receipts", {})
            # Replay only the original draw after settlement.
            if round_state.get("phase") == "settled":
                # Require the same action and fingerprint.
                if round_state.get("draw_action_id") != action_id or round_state.get("draw_fingerprint") != fingerprint:
                    # Reject a second terminal draw.
                    raise ConflictError("Double Bonus round was already drawn by another action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = {"stage": "draw", "round_id": round_id, "request_fingerprint": fingerprint}
                # Recover any settlement marker lost after ledger commit.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
                # Return the stable terminal result as a replay.
                return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": True, "ledger_replayed": settlement_replayed, **self._payload(player_id, state)}
            # Reject a new action id already bound to another command.
            if action_id in receipts or self._ledger.find(player_id, action_id) is not None:
                # Fail before drawing or settling another result.
                raise ConflictError("action_id was already used for another Double Bonus action")
            # Require this exact round to remain in the actionable slot.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming actionable.
                raise ConflictError("Only the active Double Bonus round can accept a draw")
            # Resolve the deterministic draw and settlement.
            engine.draw_round(round_state, action_id, hold, completed_at=self._clock(), request_fingerprint=fingerprint)
            # Record the durable draw identity.
            receipts[action_id] = {"stage": "draw", "round_id": round_id, "request_fingerprint": fingerprint}
            # Archive the complete result before issuing any returned-token credit.
            engine.archive_round(state, round_state)
            # Persist terminal cards and pending settlement for crash recovery.
            self._save(player_id, state)
            # Apply or recover the payout when one is due.
            settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
            # Return the revealed final hand and optional ledger proof.
            return {"round": engine.public_round(round_state), "settlement": settlement_event, "replayed": settlement_replayed, **self._payload(player_id, state)}
