# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Ledger-only, retry-safe orchestration for Fan-Tan rounds."""

# Import deep-copy support for detached optimistic state snapshots.
import copy
# Import cryptographic index selection for production pile counts.
import secrets
# Import the shared UTC clock for settled response timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import standard conflict and validation errors for request identity enforcement.
from casino.errors import ConflictError, ValidationError
# Import pure Fan-Tan calculations and state helpers.
from casino.games.fan_tan import engine
# Import the stable game identity for every ledger event.
from casino.games.fan_tan.rules import GAME_ID

# Bound caller-supplied action identifiers before persistence.
MAX_ACTION_ID_LENGTH = 128
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_fan_tan_atomic_baseline"
# Name every state field owned by Fan-Tan transitions.
_GAME_STATE_KEYS = ("recent_rounds",)


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old Fan-Tan key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "fan_tan_action_id", **kwargs)


# Expose the provider-atomic writer behind an injectable test seam.
def update_state(game_id: str, player_id: str, mutator, factory):
    # Delegate to the shared cross-process read-modify-write boundary.
    return update_player_game_state(game_id, player_id, mutator, factory)


# Coordinate player state, entropy, and exactly-once ledger actions for one Fan-Tan play.
class FanTanService:
    # Capture injectable seams so deterministic tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, randbelow=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the authenticated-player resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Publish state through the provider-current callback boundary by default.
        self.state_updater = state_updater or update_state
        # Use cryptographic uniform selection unless a focused test supplies a deterministic source.
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

    # Capture detached values for every Fan-Tan-owned state field.
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
            raise ConflictError("Fan-Tan state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Fan-Tan-owned fields on current state.
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
                raise ConflictError("Fan-Tan state changed during this action; reload and retry")
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

    # Validate a required action identity used for safe network retries.
    def _action_id(self, value) -> str:
        # Normalize only string ids and reject empty, oversized, or control-character values.
        action_id = value.strip() if isinstance(value, str) else ""
        # Branch when the public idempotency identity is not safe to persist.
        if not action_id or len(action_id) > MAX_ACTION_ID_LENGTH or any(ord(character) < 32 for character in action_id):
            # Require clients to send one stable identity per Fan-Tan play attempt.
            raise ValidationError("action_id must be a non-empty string of at most 128 characters")
        # Return the bounded identity without changing caller-visible casing.
        return action_id

    # Return the current isolated game state and immutable rules metadata.
    def state(self, player_id: str) -> dict:
        # Load only the session-bound player's game document.
        state = self._load(player_id)
        # Read the backend-owned rules and paytable.
        meta = engine.metadata()
        # Return game-owned state without exposing another player's balance or action history.
        return {"game": GAME_ID, "state": {"recent_rounds": list(state.get("recent_rounds", []))}, **meta}

    # Execute or replay one ledger-backed Fan-Tan round.
    def play(self, player_id: str, request: dict) -> dict:
        # Require an object payload before reading request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Fan-Tan play body must be an object")
        # Validate the retry identity required by the additive v1 proposal.
        action_id = self._action_id(request.get("action_id"))
        # Normalize all residue wagers before looking up an existing request.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Compute a semantic request fingerprint that detects conflicting retries.
        request_fingerprint = engine.wager_fingerprint(wagers)
        # Load only state owned by the authenticated player resolved upstream.
        state = self._load(player_id)
        # Resolve a settled retry from the bounded state cache first.
        existing_round = engine.find_round(state, action_id)
        # Branch when the client repeats a settled request.
        if existing_round:
            # Reject reuse with different wager content.
            if existing_round.get("request_fingerprint") != request_fingerprint:
                # Preserve exactly-once semantics for this action identity.
                raise ConflictError("Fan-Tan action_id was already used with different wagers")
            # Return the original round without issuing any ledger action or entropy call.
            return {"round": existing_round, "replayed": True, "ledger": {"wager": None, "settlement": None}}
        # Derive one stable round id so crash retries address the same ledger events.
        round_id = engine.round_id_for(player_id, action_id)
        # Select a counted pile before debit so the debit event can recover it after a crash.
        proposed_pile_count = engine.select_pile_count(self.randbelow)
        # Calculate the total debit from already normalized wagers.
        total_wager = round(sum(wagers.values()), 2)
        # Build stable debit details containing all information needed to reconstruct settlement.
        debit_details = {"action_id": action_id, "wagers": wagers, "pile_count": proposed_pile_count}
        # Apply the full round wager as one atomic ledger debit with a deterministic action key.
        debit_event, debit_replayed = self.ledger_gateway.apply_once(player_id=player_id, signed_amount=-total_wager, transaction_type="FAN_TAN_WAGER_DEBIT", round_id=round_id, action_id=f"{round_id}:wager", fingerprint=request_fingerprint, details=debit_details)
        # Recover the originally committed pile count when a retry follows a post-debit crash.
        pile_count = int((debit_event.get("details") or {}).get("pile_count", proposed_pile_count))
        # Calculate the exact settlement from the committed count.
        settlement = engine.settle(wagers, pile_count)
        # Start with no credit event for losing rounds.
        credit_event = None
        # Track whether an existing payout was reused for response evidence.
        credit_replayed = False
        # Branch when at least one winning residue wager returns stake plus winnings.
        if settlement["total_return"] > 0:
            # Build stable settlement details without changing the original wager identity.
            credit_details = {"action_id": action_id, "residue": settlement["residue"], "pile_count": pile_count, "settlements": settlement["settlements"]}
            # Apply the total return as one atomic ledger credit with its own deterministic action key.
            credit_event, credit_replayed = self.ledger_gateway.apply_once(player_id=player_id, signed_amount=settlement["total_return"], transaction_type="FAN_TAN_SETTLEMENT_CREDIT", round_id=round_id, action_id=f"{round_id}:settlement", fingerprint=request_fingerprint, details=credit_details)
        # Prefer the committed debit timestamp so reconstructed retries preserve round timing.
        settled_at = debit_event.get("ts") or self.clock()
        # Build the stable settled round returned by state and action endpoints.
        round_row = {"round_id": round_id, "action_id": action_id, "request_fingerprint": request_fingerprint, "player_id": player_id, "status": "settled", "wagers": wagers, "settled_at": settled_at, **settlement}
        # Record the round only after all required ledger actions have committed.
        engine.record_round(state, round_row)
        # Persist reload-safe state; ledger keys allow safe reconstruction if this write fails.
        self._save(player_id, state)
        # Return ledger evidence without exposing unrelated player history.
        return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}}
