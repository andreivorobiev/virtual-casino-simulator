"""Session-bound, ledger-only orchestration for isolated Double Bonus Video Poker (#131)."""

# Import canonical JSON encoding for semantic action fingerprints.
import json
# Import hashing so changed retries fail even when wagers happen to match.
import hashlib
# Import regular expressions for bounded public action identities.
import re
# Import a reentrant lock for single-process state and ledger reconciliation.
import threading

# Import the only approved player-balance mutation service.
from casino.core import ledger, players
# Import the shared audit clock used by other game modules.
from casino.core.clock import utc_now
# Import player-scoped persistent state without editing shared storage code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic state and rule helpers.
from casino.games.double_bonus_video_poker import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local history to preserve retry recovery for the supported simulator.
LEDGER_SCAN_LIMIT = 1_000_000
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


# Adapt the shared ledger into a game action-id apply-once interface.
class CoreLedgerGateway:
    # Capture injectable shared-ledger functions for focused tests.
    def __init__(self, *, debit=ledger.debit, credit=ledger.credit, read_recent=ledger.read_recent):
        # Store the only allowed wager debit operation.
        self._debit = debit
        # Store the only allowed returned-token credit operation.
        self._credit = credit
        # Store player-scoped ledger lookup for crash recovery.
        self._read_recent = read_recent

    # Find a committed game action for one authenticated player.
    def find(self, player_id: str, action_id: str):
        # Read only the current player's ledger rows.
        rows = self._read_recent(player_id, LEDGER_SCAN_LIMIT)
        # Search newest-first for this game and stable action detail.
        return next((row for row in reversed(rows) if row.get("game") == GAME_ID and (row.get("details") or {}).get("double_bonus_video_poker_action_id") == action_id), None)

    # Commit or recover one debit or returned-token credit exactly once locally.
    def apply_once(self, *, player_id: str, signed_amount: float, transaction_type: str, round_id: str, action_id: str, fingerprint: str, details: dict) -> tuple[dict, bool]:
        # Protect the read-before-write sequence from concurrent duplicate requests.
        with _ACTION_LOCK:
            # Find any action already committed under this player and game.
            existing = self.find(player_id, action_id)
            # Reuse only an event whose complete semantic identity matches.
            if existing is not None:
                # Compare movement, route stage, round, and semantic request content.
                matches = round(float(existing.get("amount", 0)), 2) == round(float(signed_amount), 2) and existing.get("transaction_type") == transaction_type and existing.get("round_id") == round_id and (existing.get("details") or {}).get("request_fingerprint") == fingerprint
                # Reject one client identity reused for a different action.
                if not matches:
                    # Fail closed before any second balance mutation.
                    raise ConflictError("action_id was already used for a different Double Bonus action")
                # Return immutable ledger proof and replay evidence.
                return existing, True
            # Add the stable action and fingerprint to complete audit details.
            event_details = {**details, "double_bonus_video_poker_action_id": action_id, "request_fingerprint": fingerprint}
            # Route negative amounts through the approved debit service.
            if signed_amount < 0:
                # Commit the positive magnitude as one shared-ledger debit.
                event = self._debit(player_id, abs(signed_amount), transaction_type, GAME_ID, round_id, event_details)
            # Route positive returned tokens through the approved credit service.
            else:
                # Commit the returned payout as one shared-ledger credit.
                event = self._credit(player_id, signed_amount, transaction_type, GAME_ID, round_id, event_details)
            # Return the new committed event and non-replay evidence.
            return event, False


# Coordinate player state, deterministic cards, and retry-safe ledger movements.
class DoubleBonusVideoPokerService:
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
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["bet"], transaction_type="DOUBLE_BONUS_VIDEO_POKER_WAGER_DEBIT", round_id=round_state["round_id"], action_id=round_state["start_action_id"], fingerprint=round_state["request_fingerprint"], details={"stage": "deal", "bet": round_state["bet"]})
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
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="DOUBLE_BONUS_VIDEO_POKER_SETTLEMENT_CREDIT", round_id=round_state["round_id"], action_id=f"{round_state['draw_action_id']}:settlement", fingerprint=round_state["draw_fingerprint"], details={"stage": "settlement", "hand_tier": round_state.get("hand_tier"), "multiplier": round_state.get("multiplier")})
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
        with _ACTION_LOCK:
            # Load the newest player-scoped document inside the lock.
            state = self._load_state(player_id)
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
