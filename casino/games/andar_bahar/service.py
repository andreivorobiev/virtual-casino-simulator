# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for isolated Andar Bahar."""

# Import deep-copy support for detached optimistic state snapshots.
import copy
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
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict and validation errors for route boundaries.
from casino.errors import ConflictError, ValidationError
# Import only this game's deterministic state and rule helpers.
from casino.games.andar_bahar import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize action-id lookup and ledger writes inside the one-process server.
_ACTION_LOCK = threading.RLock()
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_andar_bahar_atomic_baseline"
# Name every state field owned by Andar Bahar transitions.
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
    # Preserve the old Andar Bahar key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "andar_bahar_action_id", **kwargs)


# Expose the provider-atomic writer behind an injectable test seam.
def update_state(game_id: str, player_id: str, mutator, factory):
    # Delegate to the shared cross-process read-modify-write boundary.
    return update_player_game_state(game_id, player_id, mutator, factory)


# Coordinate player state, deterministic cards, and retry-safe ledger movements.
class AndarBaharService:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, get_player=None, clock=None, seed_factory=None, fixture_factory=None):
        # Use the game-local shared-ledger adapter unless a test supplies a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Load one authenticated player's isolated state document by default.
        self._load_state = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Publish state through the provider-current callback boundary by default.
        self._update_state = state_updater or update_state
        # Return read-only current-player information without balance mutation.
        self._get_player = get_player or players.get_player
        # Use the shared UTC clock unless a focused test pins timestamps.
        self._clock = clock or utc_now
        # Derive deterministic cards only through an injected non-production hook.
        self._seed_factory = seed_factory
        # Provide exact fixture rounds for focused tests without randomness.
        self._fixture_factory = fixture_factory

    # Load one player document and capture its exact game-owned baseline.
    def _load(self, player_id: str) -> dict:
        # Read through the injected player-scoped persistence boundary.
        state = self._load_state(player_id)
        # Retain only the values this service may replace during the operation.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting private operation metadata.
        return state

    # Capture detached values for every Andar Bahar-owned state field.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Build one fresh compatibility baseline for absent predecessor fields.
        defaults = engine.default_state()
        # Normalize all current and predecessor documents to one complete shape.
        return {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}

    # Publish one player document through provider-current compare-and-replace.
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Refuse an untracked detached-document write before entering storage.
        if not isinstance(expected, dict):
            # Keep stale or fabricated state outside provider bytes.
            raise ConflictError("Andar Bahar state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Andar Bahar-owned fields on provider-current state.
        def publish(current: dict) -> dict:
            # Detach current owned values from unrelated provider metadata.
            observed = self._game_snapshot(current)
            # Accept exact same-result publication without rewriting siblings.
            if observed == desired:
                # Preserve the complete authoritative provider document.
                return current
            # Reject an operation whose owned baseline lost a concurrent race.
            if observed != expected:
                # Require the caller to recover from the authoritative winner.
                raise ConflictError("Andar Bahar state changed during this action; reload and retry")
            # Replace only the three fields governed by this game service.
            for key in _GAME_STATE_KEYS:
                # Publish detached JSON-compatible values without sibling loss.
                current[key] = copy.deepcopy(desired[key])
            # Return the complete provider document for atomic persistence.
            return current

        # Commit the transition through the provider's cross-process boundary.
        authoritative = self._update_state(GAME_ID, player_id, publish, engine.default_state)
        # Advance the operation baseline to the exact committed owned result.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(authoritative)

    # Build the public state, rules, and current-player payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return only sanitized game state and documented fixed rules.
        return {
            "game": GAME_ID,  # Identify the module for generic clients.
            "state": engine.public_state(state),  # Hide internal retry fingerprints.
            "player": self._get_player(player_id),  # Expose the bound player's current wallet snapshot.
            "rules": {  # Group immutable table rules for generic frontend rendering.
                "sides": list(engine.SIDES),  # Advertise the two legal side predictions.
                "deal_order": list(engine.DEAL_ORDER),  # Document Andar-first alternating reveal order.
                "match_rank_only": True,  # Explain that suits never decide the result.
                "return_multiplier": engine.RETURN_MULTIPLIER,  # Retain the deprecated frozen-v1 integer scalar.
                "return_multipliers": dict(engine.RETURN_MULTIPLIERS),  # Publish authoritative additive side prices.
            },
        }

    # Ensure a complete round has one committed wager debit.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Apply or recover the stable play action debit through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["wager"], transaction_type="ANDAR_BAHAR_WAGER_DEBIT", round_id=round_state["round_id"], action_id=round_state["action_id"], fingerprint=round_state["request_fingerprint"], details={"stage": "play", "wager": round_state["wager"], "selected_side": round_state["selected_side"], "match_card": round_state["match_card"]})
        # Mark the debit complete only after ledger proof exists.
        round_state["wager_status"] = "complete"
        # Store the immutable ledger id for diagnostics and retry evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal reloads avoid a recovery scan.
        self._save(player_id, state)
        # Return the committed event and replay flag.
        return event, replayed

    # Ensure a winning round has at most one returned-token credit.
    def _ensure_settlement(self, player_id: str, state: dict, round_state: dict) -> tuple[dict | None, bool]:
        # Skip zero-value ledger rows for an incorrect side prediction.
        if not round_state.get("payout"):
            # Mark the no-credit settlement complete.
            round_state["settlement_status"] = "complete"
            # Persist the terminal marker for reload safety.
            self._save(player_id, state)
            # Return no event and no ledger replay.
            return None, False
        # Apply or recover the stable play action payout through a derived action id.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="ANDAR_BAHAR_PAYOUT_CREDIT", round_id=round_state["round_id"], action_id=f"{round_state['action_id']}:settlement", fingerprint=round_state["request_fingerprint"], details={"stage": "settlement", "wager": round_state["wager"], "selected_side": round_state["selected_side"], "winning_side": round_state["winning_side"], "match_card": round_state["match_card"], "outcome": round_state["outcome"]})
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
        # Inspect retained settled rounds for lost debit or credit markers.
        for round_state in state.get("recent_rounds", []):
            # Recover a lost wager marker when a debit exists.
            if round_state.get("wager_status") == "pending":
                # Apply or recover the wager debit through exactly-once details.
                self._ensure_wager(player_id, state, round_state)
            # Recover a lost payout marker when a win is pending.
            if round_state.get("settlement_status") == "pending":
                # Ensure the owed payout exactly once during recovery.
                self._ensure_settlement(player_id, state, round_state)
        # Clear impossible active state because Andar Bahar plays atomically.
        if state.get("active_round") is not None:
            # Move the complete round into history before publishing state.
            engine.archive_round(state, state["active_round"])
            # Persist cleanup for reload-safe state.
            self._save(player_id, state)

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

    # Play or replay one complete Andar Bahar round atomically.
    def play(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Andar Bahar play body must be an object")
        # Validate the play action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the wager before constructing a semantic fingerprint.
        wager = engine.normalize_wager(request.get("wager"))
        # Normalize the selected side before constructing a semantic fingerprint.
        side = engine.normalize_side(request.get("side"))
        # Bind the action identity to the exact normalized wager and side.
        fingerprint = request_fingerprint({"stage": "play", "wager": wager, "side": side})
        # Serialize state preparation, debit, settlement, and marker persistence.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self._load(player_id)
            # Recover any interrupted prior action before enforcing idempotency.
            self._recover(player_id, state)
            # Load durable compact receipts that prevent reuse after history pruning.
            receipts = state.setdefault("action_receipts", {})
            # Read any prior semantic owner for this action identity.
            receipt = receipts.get(action_id)
            # Find a retained round with the same client action identity.
            existing = engine.round_for_action(state, action_id)
            # Replay the exact round when settings match.
            if existing is not None:
                # Reject action-id reuse with a changed wager or side.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail before a second ledger movement.
                    raise ConflictError("action_id was already used with different Andar Bahar inputs")
                # Build the canonical durable receipt for this retained play.
                expected_receipt = {"stage": "play", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Reject a corrupt receipt that maps the id to another semantic command.
                if receipt is not None and receipt != expected_receipt:
                    # Preserve the original receipt instead of issuing a movement.
                    raise ConflictError("action_id was already used for another Andar Bahar action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Ensure the original wager debit in case its marker was interrupted.
                wager_event, wager_replayed = self._ensure_wager(player_id, state, existing)
                # Ensure any winning payout in case its marker was interrupted.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, existing)
                # Return the same round and ledger proof.
                return {"round": engine.public_round(existing), "wager": wager_event, "settlement": settlement_event, "replayed": True, "ledger_replayed": wager_replayed or settlement_replayed, **self._payload(player_id, state)}
            # Reject reuse when the owning round has aged out of bounded history.
            if receipt is not None:
                # Keep the durable action identity at-most-once across retained state.
                raise ConflictError("action_id belongs to an older Andar Bahar action")
            # Refuse to reconstruct cards if a committed debit outlived corrupt state.
            if self._ledger.find(player_id, action_id) is not None:
                # Preserve the committed debit without presenting a changed result.
                raise ConflictError("Committed Andar Bahar round state is unavailable")
            # Derive deterministic cards only through the injected test hook.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Read an optional exact fixture for deterministic outcome tests.
            fixture = self._fixture_factory(action_id) if self._fixture_factory else None
            # Derive a stable route and ledger correlation id from authenticated input.
            round_id = engine.round_id_for(player_id, action_id)
            # Build complete state before touching the shared ledger.
            round_state = engine.play_round(player_id, wager, side, action_id, round_id=round_id, created_at=self._clock(), request_fingerprint=fingerprint, seed=seed, fixture=fixture)
            # Persist the terminal result before any balance movement for crash recovery.
            engine.archive_round(state, round_state)
            # Persist a compact action receipt before the wager can commit.
            receipts[action_id] = {"stage": "play", "round_id": round_id, "request_fingerprint": fingerprint}
            # Save prepared terminal state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Protect debit cleanup so insufficient funds does not strand a history row.
            try:
                # Apply or recover the one wager debit.
                wager_event, wager_replayed = self._ensure_wager(player_id, state, round_state)
                # Apply or recover the one payout credit when the side wins.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, round_state)
            # Clear only state proven to have no committed ledger movement.
            except Exception:
                # Check the append-only ledger before removing prepared recovery state.
                if self._ledger.find(player_id, action_id) is None:
                    # Remove the non-debited history row.
                    state["recent_rounds"] = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_id]
                    # Release the action id because no balance movement committed.
                    receipts.pop(action_id, None)
                    # Persist cleanup before propagating the original error.
                    self._save(player_id, state)
                # Re-raise the original storage or ledger error.
                raise
            # Return the transparent round and committed ledger evidence.
            return {"round": engine.public_round(round_state), "wager": wager_event, "settlement": settlement_event, "replayed": wager_replayed or settlement_replayed, **self._payload(player_id, state)}
