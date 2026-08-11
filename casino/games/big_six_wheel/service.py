# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Ledger-only, retry-safe orchestration for Big Six Wheel spins."""

# Import cryptographic index selection for production wheel outcomes.
import secrets
# Import the shared UTC clock for settled response timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistence helpers without changing shared state code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import standard conflict and validation errors for request identity enforcement.
from casino.errors import ConflictError, ValidationError
# Import pure Big Six calculations and state helpers.
from casino.games.big_six_wheel import engine
# Import the stable game identity for every ledger event.
from casino.games.big_six_wheel.rules import GAME_ID, outcome_catalog

# Bound caller-supplied idempotency identifiers before persistence.
MAX_CLIENT_REQUEST_ID_LENGTH = 128


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old idempotency key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "idempotency_key", **kwargs)


# Coordinate player state, entropy, and exactly-once ledger actions for one spin.
class BigSixWheelService:
    # Capture injectable seams so deterministic tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, randbelow=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the #81 authenticated-player resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Use player-scoped persistence without mutating any shared state module.
        self.state_saver = state_saver or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Use cryptographic uniform selection unless a focused test supplies a deterministic index.
        self.randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins response time.
        self.clock = clock or utc_now

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
        state = self.state_loader(player_id)
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
        state = self.state_loader(player_id)
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
        self.state_saver(player_id, state)
        # Return ledger evidence without exposing unrelated player history.
        return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}}
