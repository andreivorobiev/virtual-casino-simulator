# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Ledger-only, retry-safe orchestration for Crown and Anchor rounds."""

# Import deep-copy support for detached optimistic state snapshots.
import copy
# Import cryptographic randomness for production dice rolls.
import secrets
# Import shared clock helper for stable settled timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict and validation errors for retry enforcement.
from casino.errors import ConflictError, ValidationError
# Import pure rules and state helpers from this game package only.
from casino.games.crown_and_anchor import engine
# Import stable game id and symbol metadata for ledger details and state payloads.
from casino.games.crown_and_anchor.rules import GAME_ID, symbol_catalog

# Bound caller-supplied idempotency identities before persistence.
MAX_CLIENT_REQUEST_ID_LENGTH = 128
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_crown_and_anchor_atomic_baseline"
# Name every state field owned by Crown and Anchor transitions.
_GAME_STATE_KEYS = ("recent_rounds",)


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old idempotency key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "idempotency_key", **kwargs)


# Expose the provider-atomic writer behind an injectable test seam.
def update_state(game_id: str, player_id: str, mutator, factory):
    # Delegate to the shared cross-process read-modify-write boundary.
    return update_player_game_state(game_id, player_id, mutator, factory)


# Coordinate player state, dice entropy, and exactly-once ledger movement.
class CrownAndAnchorService:
    # Capture injectable seams so focused tests avoid filesystem and ambient randomness.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, roll_die=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the authenticated route resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Publish state through the provider-current callback boundary by default.
        self.state_updater = state_updater or update_state
        # Use cryptographic one-based dice unless a focused test supplies deterministic rolls.
        self.roll_die = roll_die or (lambda: secrets.randbelow(6) + 1)
        # Use the shared UTC clock unless a focused test pins timestamps.
        self.clock = clock or utc_now

    # Load one player document and capture its exact game-owned baseline.
    def _load(self, player_id: str) -> dict:
        # Read through the injected player-scoped persistence boundary.
        state = self.state_loader(player_id)
        # Retain only the values this service may replace during the operation.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting private operation metadata.
        return state

    # Capture detached values for every Crown and Anchor-owned state field.
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
            raise ConflictError("Crown and Anchor state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Crown and Anchor-owned fields on current state.
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
                raise ConflictError("Crown and Anchor state changed during this action; reload and retry")
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

    # Validate a required client action identity used for safe retries.
    def _client_request_id(self, value) -> str:
        # Normalize only string ids and reject empty, oversized, or control-character values.
        request_id = value.strip() if isinstance(value, str) else ""
        # Branch when the identity is unsafe to persist.
        if not request_id or len(request_id) > MAX_CLIENT_REQUEST_ID_LENGTH or any(ord(character) < 32 for character in request_id):
            # Require one stable identity per atomic play.
            raise ValidationError("client_request_id must be a non-empty string of at most 128 characters")
        # Return the exact bounded identity.
        return request_id

    # Return current isolated state and immutable rules metadata.
    def state(self, player_id: str) -> dict:
        # Load only the authenticated player's game document.
        state = self._load(player_id)
        # Return game-owned state without exposing another player's history.
        return {"game": GAME_ID, "symbols": symbol_catalog(), "paytable": {str(key): value for key, value in engine.NET_ODDS_BY_HITS.items()}, "recent_rounds": list(state.get("recent_rounds", []))}

    # Execute or replay one complete ledger-backed symbol dice round.
    def play(self, player_id: str, request: dict) -> dict:
        # Require an object payload before reading fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Crown and Anchor play body must be an object")
        # Validate the retry identity required by the additive v1 contract.
        client_request_id = self._client_request_id(request.get("client_request_id"))
        # Normalize all symbol wagers before looking up existing requests.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Compute a semantic request fingerprint that detects conflicting retries.
        request_fingerprint = engine.wager_fingerprint(wagers)
        # Load state owned only by the authenticated player.
        state = self._load(player_id)
        # Resolve a settled retry from bounded state first.
        existing_round = engine.find_round(state, client_request_id)
        # Branch when the client repeats an already-settled request.
        if existing_round:
            # Reject reuse with different wager content.
            if existing_round.get("request_fingerprint") != request_fingerprint:
                # Preserve exactly-once semantics for this public identity.
                raise ConflictError("Crown and Anchor client_request_id was already used with different wagers")
            # Return the stable original response without new dice or ledger calls.
            return {"round": existing_round, "replayed": True}
        # Derive one stable round id so crash retries address the same ledger events.
        round_id = engine.round_id_for(player_id, client_request_id)
        # Roll three dice before debit so the debit event can recover the result after interruption.
        proposed_faces = engine.roll_faces(self.roll_die)
        # Calculate the total debit from already normalized wagers.
        total_wager = round(sum(wagers.values()), 2)
        # Build debit details containing everything needed to reconstruct the settlement.
        debit_details = {"client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "wagers": wagers, "faces": proposed_faces}
        # Apply the full symbol coverage wager as one atomic ledger debit.
        debit_event, debit_replayed = self.ledger_gateway.apply_once(player_id=player_id, amount=-total_wager, transaction_type="CROWN_AND_ANCHOR_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", details=debit_details)
        # Recover the originally committed faces when retrying after a post-debit interruption.
        committed_faces = list((debit_event.get("details") or {}).get("faces", proposed_faces))
        # Calculate the exact settlement from the committed dice.
        settlement = engine.settle(wagers, committed_faces)
        # Start with no credit event for fully losing rounds.
        credit_event = None
        # Track whether an existing payout was reused for response evidence.
        credit_replayed = False
        # Branch when at least one covered symbol returns stake plus winnings.
        if settlement["total_return"] > 0:
            # Build stable settlement details without changing the wager identity.
            credit_details = {"client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "faces": committed_faces, "symbols": settlement["symbols"], "settlements": settlement["settlements"]}
            # Apply the aggregate returned credit as one deterministic ledger action.
            credit_event, credit_replayed = self.ledger_gateway.apply_once(player_id=player_id, amount=settlement["total_return"], transaction_type="CROWN_AND_ANCHOR_SETTLEMENT_CREDIT", round_id=round_id, action_key=f"{round_id}:settlement", details=credit_details)
        # Prefer the committed debit timestamp so recovered retries preserve round timing.
        settled_at = debit_event.get("ts") or self.clock()
        # Build the stable settled round returned by state and action endpoints.
        round_row = {"round_id": round_id, "client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "player_id": player_id, "status": "settled", "wagers": wagers, "settled_at": settled_at, **settlement}
        # Record the round only after all required ledger actions have committed.
        engine.record_round(state, round_row)
        # Persist reload-safe state; ledger keys allow safe reconstruction if this write fails.
        self._save(player_id, state)
        # Return ledger evidence without exposing unrelated player history.
        return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}}
