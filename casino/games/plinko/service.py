# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for Plinko (#136, #845, PLINKO-006)."""

# Import deep-copy support for detached optimistic state snapshots.
import copy

# Import canonical JSON encoding for semantic action fingerprints.
import json
# Import hashing so changed retries fail even when amounts happen to match.
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
from casino.games.plinko import engine

# Use the same game id for state documents, API payloads, and ledger audit rows.
GAME_ID = engine.GAME_ID
# Bound client retry ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local history to preserve retry recovery for the supported simulator.
# Serialize action-id lookup and ledger writes inside the one-process server.
_ACTION_LOCK = threading.RLock()
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_plinko_atomic_baseline"
# Name every state field owned by Plinko transitions.
_GAME_STATE_KEYS = tuple(engine.default_state())


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
    # Preserve the old Plinko key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "plinko_action_id", **kwargs)


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


# Coordinate player state, deterministic paths, and retry-safe ledger movements.
class PlinkoService:
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
        # Derive deterministic paths only through an injected non-production hook.
        self._seed_factory = seed_factory

    # Capture only the fields owned by Plinko transitions.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Build one fresh compatibility baseline for absent predecessor fields.
        defaults = engine.default_state()
        # Detach nested drops and receipts from later engine mutation.
        return {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}

    # Load one document and bind its optimistic game-owned baseline.
    def _load(self, player_id: str) -> dict:
        # Read through the injected repository before provider mutation.
        state = self._repository.load(player_id)
        # Retain the exact game-owned values expected by the next publication.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting operation metadata.
        return state

    # Publish one provider-current compare-and-replace transition. (PLINKO-006)
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Reject fabricated or stale detached documents before storage access.
        if not isinstance(expected, dict):
            # Keep untracked state outside provider bytes.
            raise ConflictError("Plinko state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Plinko-owned fields on current state.
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
                raise ConflictError("Plinko state changed during this action; reload and retry")
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
            "state": engine.public_state(state),  # Hide internal retry fingerprints.
            "player": self._get_player(player_id),  # Expose the bound player's current wallet snapshot.
            "rules": {  # Group immutable table rules for generic frontend rendering.
                "rows": engine.ROWS,  # Publish the fixed pegboard row count.
                "multipliers": list(engine.MULTIPLIERS),  # Publish bucket multipliers transparently.
                "bucket_count": len(engine.MULTIPLIERS),  # Publish bucket count for stage rendering.
            },
        }

    # Ensure one drop has its wager debit committed.
    def _ensure_debit(self, player_id: str, state: dict, drop: dict) -> tuple[dict, bool]:
        # Apply or recover the stable action through the shared ledger.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-drop["wager"], transaction_type="PLINKO_WAGER_DEBIT", round_id=drop["drop_id"], action_key=drop["action_id"], request_fingerprint=drop["request_fingerprint"], details={"stage": "drop", "wager": drop["wager"], "bucket": drop["bucket"], "multiplier": drop["multiplier"], "path": drop["path"]})
        # Mark the debit complete only after ledger proof exists.
        drop["debit_status"] = "complete"
        # Store the immutable ledger id for diagnostics and retry evidence.
        drop["debit_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal reloads avoid a recovery scan.
        self._save(player_id, state)
        # Return the committed event and replay flag.
        return event, replayed

    # Ensure one drop has its returned-token credit committed when payout is nonzero.
    def _ensure_settlement(self, player_id: str, state: dict, drop: dict) -> tuple[dict | None, bool]:
        # Skip zero-value ledger rows when a bucket returns nothing.
        if not drop.get("payout"):
            # Mark zero settlement complete.
            drop["settlement_status"] = "complete"
            # Persist terminal state for reload safety.
            self._save(player_id, state)
            # Return no event and no ledger replay.
            return None, False
        # Apply or recover the returned-token credit through the same action id and fingerprint.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=drop["payout"], transaction_type="PLINKO_PAYOUT_CREDIT", round_id=drop["drop_id"], action_key=drop["action_id"] + ":payout", request_fingerprint=drop["request_fingerprint"], details={"stage": "settlement", "wager": drop["wager"], "bucket": drop["bucket"], "multiplier": drop["multiplier"], "path": drop["path"]})
        # Mark the settlement complete only after ledger proof exists.
        drop["settlement_status"] = "complete"
        # Store the immutable payout ledger id.
        drop["settlement_ledger_id"] = event.get("ledger_id")
        # Persist the recovered or newly committed marker.
        self._save(player_id, state)
        # Return the committed event and replay evidence.
        return event, replayed

    # Recover lost ledger markers for retained drops after reload.
    def _recover(self, player_id: str, state: dict) -> None:
        # Inspect every retained drop for interrupted debit or settlement markers.
        for drop in state.get("recent_drops", []):
            # Recover a pending debit only if ledger proof already exists.
            if drop.get("debit_status") == "pending":
                # Read committed proof without creating a second movement.
                event = self._ledger.find(player_id, drop.get("action_id"))
                # Restore the marker when the debit already committed.
                if event is not None:
                    # Mark the retained debit complete.
                    drop["debit_status"] = "complete"
                    # Restore the immutable ledger identifier.
                    drop["debit_ledger_id"] = event.get("ledger_id")
                    # Persist recovered state.
                    self._save(player_id, state)
            # Recover owed payout after a completed debit.
            if drop.get("debit_status") == "complete" and drop.get("settlement_status") == "pending":
                # Ensure the returned-token credit exactly once.
                self._ensure_settlement(player_id, state, drop)

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

    # Commit or replay one server-authoritative Plinko drop.
    def drop(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Plinko drop body must be an object")
        # Validate the drop action identity used for network retries.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the wager before constructing a semantic fingerprint.
        wager = engine.normalize_wager(request.get("wager"))
        # Bind the action identity to the exact normalized wager.
        fingerprint = request_fingerprint({"stage": "drop", "wager": wager})
        # Serialize state preparation, debit, settlement, and marker persistence.
        with _ACTION_LOCK:
            # Load the current player's state inside the critical section.
            state = self._load(player_id)
            # Recover any interrupted prior action before enforcing action rules.
            self._recover(player_id, state)
            # Load durable compact receipts that prevent reuse after history pruning.
            receipts = state.setdefault("action_receipts", {})
            # Read any prior semantic owner for this action identity.
            receipt = receipts.get(action_id)
            # Find a retained drop with the same client action identity.
            existing = engine.drop_for_action(state, action_id)
            # Replay the exact committed drop when settings match.
            if existing is not None:
                # Reject action-id reuse with a changed wager.
                engine.assert_replay(existing, fingerprint)
                # Build the canonical durable receipt for this retained drop.
                expected_receipt = {"stage": "drop", "drop_id": existing["drop_id"], "request_fingerprint": fingerprint}
                # Reject a corrupt receipt that maps the id to another command.
                if receipt is not None and receipt != expected_receipt:
                    # Preserve the original receipt instead of issuing a movement.
                    raise ConflictError("action_id was already used for another Plinko action")
                # Restore a missing receipt when loading an earlier compatible document.
                receipts[action_id] = expected_receipt
                # Ensure original debit and settlement markers survived interruption.
                debit_event, debit_replayed = self._ensure_debit(player_id, state, existing)
                # Ensure any returned-token credit survived interruption.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, existing)
                # Return the same drop and ledger proof.
                return {"drop": engine.public_drop(existing), "wager": debit_event, "settlement": settlement_event, "replayed": True or debit_replayed or settlement_replayed, **self._payload(player_id, state)}
            # Reject reuse when the owning drop has aged out of bounded history.
            if receipt is not None:
                # Keep the durable action identity at-most-once across retained state.
                raise ConflictError("action_id belongs to an older Plinko action")
            # Refuse to reconstruct a path if a committed debit outlived corrupt state.
            if self._ledger.find(player_id, action_id) is not None:
                # Preserve the committed debit without presenting a changed result.
                raise ConflictError("Committed Plinko drop state is unavailable")
            # Derive deterministic path only through the injected test hook.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Commit the path before any client animation can occur.
            path = engine.committed_path(seed=seed)
            # Derive a stable route and ledger correlation id from authenticated input.
            drop_id = engine.drop_id_for(player_id, action_id)
            # Build the settled drop before touching the shared ledger.
            drop = engine.create_drop(player_id, wager, action_id, path=path, drop_id=drop_id, created_at=self._clock(), request_fingerprint=fingerprint)
            # Archive the committed outcome before any balance movement.
            engine.archive_drop(state, drop)
            # Persist a compact action receipt before the wager can commit.
            receipts[action_id] = {"stage": "drop", "drop_id": drop_id, "request_fingerprint": fingerprint}
            # Save prepared state so post-debit crashes can recover safely.
            self._save(player_id, state)
            # Protect debit cleanup so insufficient funds does not strand a free outcome.
            try:
                # Apply or recover the one wager debit.
                debit_event, debit_replayed = self._ensure_debit(player_id, state, drop)
                # Apply or recover the returned-token credit.
                settlement_event, settlement_replayed = self._ensure_settlement(player_id, state, drop)
            # Clear only state proven to have no committed ledger movement.
            except Exception:
                # Check the append-only ledger before removing prepared recovery state.
                if self._ledger.find(player_id, action_id) is None:
                    # Remove the non-debited drop from bounded history.
                    state["recent_drops"] = [item for item in state.get("recent_drops", []) if item.get("drop_id") != drop_id]
                    # Release the action id because no balance movement committed.
                    receipts.pop(action_id, None)
                    # Persist cleanup before propagating the original error.
                    self._save(player_id, state)
                # Re-raise the original storage or ledger error.
                raise
            # Return the committed path, bucket, multiplier, and ledger evidence.
            return {"drop": engine.public_drop(drop), "wager": debit_event, "settlement": settlement_event, "replayed": debit_replayed or settlement_replayed, **self._payload(player_id, state)}
