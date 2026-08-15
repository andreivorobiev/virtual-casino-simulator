# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Ledger-only, retry-safe orchestration for Big Six Wheel spins."""

# Import deep-copy support for detached optimistic state snapshots.
import copy
# Import cryptographic index selection for production wheel outcomes.
import secrets
# Import the shared UTC clock for settled response timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import standard conflict and validation errors for request identity enforcement.
from casino.errors import ConflictError, ValidationError
# Import pure Big Six calculations and state helpers.
from casino.games.big_six_wheel import engine
# Import the stable game identity for every ledger event.
from casino.games.big_six_wheel.rules import GAME_ID, outcome_catalog

# Bound caller-supplied idempotency identifiers before persistence.
MAX_CLIENT_REQUEST_ID_LENGTH = 128
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_big_six_wheel_atomic_baseline"
# Name every state field owned by Big Six Wheel transitions.
_GAME_STATE_KEYS = ("recent_rounds",)


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old idempotency key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "idempotency_key", **kwargs)


# Expose the provider-atomic writer behind an injectable test seam.
def update_state(game_id: str, player_id: str, mutator, factory):
    # Delegate to the shared cross-process read-modify-write boundary.
    return update_player_game_state(game_id, player_id, mutator, factory)


# Coordinate player state, entropy, and exactly-once ledger actions for one spin.
class BigSixWheelService:
    # Capture injectable seams so deterministic tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, randbelow=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the #81 authenticated-player resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Publish state through the provider-current callback boundary by default.
        self.state_updater = state_updater or update_state
        # Use cryptographic uniform selection unless a focused test supplies a deterministic index.
        self.randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins response time.
        self.clock = clock or utc_now

    # Load one player document and capture its exact game-owned baseline.
    def _load(self, player_id: str) -> dict:
        # Read through the injected player-scoped persistence boundary.
        state = self.state_loader(player_id)
        # Retain only the values this service may replace during the operation.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting private operation metadata.
        return state

    # Capture detached values for every Big Six Wheel-owned state field.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Build one fresh compatibility baseline for absent predecessor fields.
        defaults = engine.default_state()
        # Normalize current and predecessor documents to one complete shape.
        return {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}

    # Publish one player document through provider-current compare-and-replace.
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Refuse an untracked detached-document write before entering storage.
        if not isinstance(expected, dict):
            # Keep stale or fabricated state outside provider bytes.
            raise ConflictError("Big Six Wheel state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Big Six Wheel-owned fields on current state.
        def publish(current: dict) -> dict:
            # Detach current owned values from unrelated provider metadata.
            observed = self._game_snapshot(current)
            # Accept exact same-result publication without rewriting siblings.
            if observed == desired:
                # Preserve the complete authoritative provider document.
                return current
            # Reject an operation whose owned baseline lost a concurrent race.
            if observed != expected:
                # Require recovery from the authoritative winner.
                raise ConflictError("Big Six Wheel state changed during this action; reload and retry")
            # Replace only fields governed by this game service.
            for key in _GAME_STATE_KEYS:
                # Publish detached JSON-compatible values without sibling loss.
                current[key] = copy.deepcopy(desired[key])
            # Return the complete provider document for atomic persistence.
            return current

        # Commit the transition through the provider's cross-process boundary.
        authoritative = self.state_updater(GAME_ID, player_id, publish, engine.default_state)
        # Advance the operation baseline to the exact committed owned result.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(authoritative)

    # Validate a required client action identity used for safe network retries.
    def _client_request_id(self, value) -> str:
        # Normalize only string ids and reject empty, oversized, or control-character values.
        request_id = value.strip() if isinstance(value, str) else ""
        # Branch when the public idempotency identity is not safe to persist.
        if not request_id or len(request_id) > MAX_CLIENT_REQUEST_ID_LENGTH or any(ord(character) < 32 for character in request_id):
            # Require clients to send one stable identity per spin attempt.
            raise ValidationError("client_request_id must be a non-empty string of at most 128 characters")
        # Return the bounded identity without changing caller-visible casing.
        return request_id

    # Return the current isolated game state and immutable outcome metadata.
    def state(self, player_id: str) -> dict:
        # Load only the session-bound player's game document.
        state = self._load(player_id)
        # Return game-owned state without exposing another player's balance or action history.
        return {"game": GAME_ID, "outcomes": outcome_catalog(), "recent_rounds": list(state.get("recent_rounds", []))}

    # Execute or replay one ledger-backed spin request.
    def spin(self, player_id: str, request: dict) -> dict:
        # Require an object payload before reading request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Big Six spin body must be an object")
        # Validate the retry identity required by the additive v1 contract.
        client_request_id = self._client_request_id(request.get("client_request_id"))
        # Normalize all wagers before looking up an existing request.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Compute a semantic request fingerprint that detects conflicting retries.
        request_fingerprint = engine.wager_fingerprint(wagers)
        # Load only state owned by the authenticated player resolved upstream.
        state = self._load(player_id)
        # Resolve a settled retry from the bounded state cache first.
        existing_round = engine.find_round(state, client_request_id)
        # Branch when the client repeats a settled request.
        if existing_round:
            # Reject reuse with different wager content.
            if existing_round.get("request_fingerprint") != request_fingerprint:
                # Preserve exactly-once semantics for this client identity.
                raise ConflictError("Big Six client_request_id was already used with different wagers")
            # Return the original round without issuing any ledger action or entropy call.
            return {"round": existing_round, "replayed": True}
        # Derive one stable round id so crash retries address the same ledger events.
        round_id = engine.round_id_for(player_id, client_request_id)
        # Select an initial wheel index before debit so the debit event can recover it after a crash.
        proposed_index = engine.select_index(self.randbelow)
        # Calculate the total debit from already normalized wagers.
        total_wager = round(sum(wagers.values()), 2)
        # Build stable debit details containing all information needed to reconstruct settlement.
        debit_details = {"client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "wagers": wagers, "result_index": proposed_index}
        # Apply the full round wager as one atomic ledger debit with a deterministic action key.
        debit_event, debit_replayed = self.ledger_gateway.apply_once(player_id=player_id, amount=-total_wager, transaction_type="BIG_SIX_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", details=debit_details)
        # Recover the originally committed index when a retry follows a post-debit crash.
        result_index = int((debit_event.get("details") or {}).get("result_index", proposed_index))
        # Calculate the exact settlement from the committed wheel index.
        settlement = engine.settle(wagers, result_index)
        # Start with no credit event for losing rounds.
        credit_event = None
        # Track whether an existing payout was reused for response evidence.
        credit_replayed = False
        # Branch when at least one winning wager returns stake plus winnings.
        if settlement["total_return"] > 0:
            # Build stable settlement details without changing the original wager identity.
            credit_details = {"client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "outcome": settlement["outcome"], "result_index": result_index, "settlements": settlement["settlements"]}
            # Apply the total return as one atomic ledger credit with its own deterministic action key.
            credit_event, credit_replayed = self.ledger_gateway.apply_once(player_id=player_id, amount=settlement["total_return"], transaction_type="BIG_SIX_SETTLEMENT_CREDIT", round_id=round_id, action_key=f"{round_id}:settlement", details=credit_details)
        # Prefer the committed debit timestamp so reconstructed retries preserve round timing.
        settled_at = debit_event.get("ts") or self.clock()
        # Build the stable settled round returned by state and action endpoints.
        round_row = {"round_id": round_id, "client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "player_id": player_id, "status": "settled", "wagers": wagers, "settled_at": settled_at, **settlement}
        # Record the round only after all required ledger actions have committed.
        engine.record_round(state, round_row)
        # Persist reload-safe state; ledger keys allow safe reconstruction if this write fails.
        self._save(player_id, state)
        # Return ledger evidence without exposing unrelated player history.
        return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}}
