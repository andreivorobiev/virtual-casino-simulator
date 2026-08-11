# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only, retry-safe Chuck-a-Luck orchestration."""

# Import bounded request validation for client retry identifiers.
import re
# Import cryptographic bounded random selection for production dice.
import secrets
# Import a process-local reentrant lock for exactly-once local actions.
import threading

# Import the shared player service without a game-owned ledger mutation boundary.
from casino.core import players
# Import the shared UTC clock for stable settled response timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistence helpers for authenticated session isolation.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict and validation errors for safe API boundaries.
from casino.errors import ConflictError, ValidationError
# Import only this game's pure engine and immutable rule metadata.
from casino.games.chuck_a_luck import engine, rules

# Bound request identifiers to conservative URL-safe characters and length.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize state, ledger proof, debit, settlement, and state-save operations locally.
_SETTLEMENT_LOCK = threading.RLock()
# Name the single aggregate wager debit consistently across recovery paths.
WAGER_TRANSACTION_TYPE = "CHUCK_A_LUCK_WAGER_DEBIT"
# Name the optional stake-plus-winnings aggregate credit consistently.
SETTLEMENT_TRANSACTION_TYPE = "CHUCK_A_LUCK_SETTLEMENT_CREDIT"


# Validate the required caller-stable identity used for network retries.
def require_request_id(value) -> str:
    # Require a bounded string whose characters remain safe in logs and JSON state.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the exact validated identity for stable hashing and comparisons.
    return value


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old idempotency key beside canonical action evidence.
    return GameSettlementGateway(rules.GAME_ID, "idempotency_key", **kwargs)


# Coordinate authenticated state, server entropy, and exactly-once ledger settlement.
class ChuckALuckService:
    # Capture injectable dependencies so focused tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, randbelow=None, clock=None, get_player=None):
        # Use the production apply-once ledger adapter unless a focused test supplies one.
        self._ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped production state loading unless a focused test supplies memory state.
        self._state_loader = state_loader or self._load_production_state
        # Use player-scoped production state saving unless a focused test supplies memory state.
        self._state_saver = state_saver or self._save_production_state
        # Use cryptographic uniform selection unless a focused test injects deterministic indices.
        self._randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins settlement time.
        self._clock = clock or utc_now
        # Use read-only player snapshots unless a focused test supplies an in-memory wallet.
        self._get_player = get_player or players.get_player

    # Load one authenticated player's isolated production game document.
    @staticmethod
    def _load_production_state(player_id: str) -> dict:  # Load the game document for one authenticated player.
        # Delegate through the shared player-scoped storage abstraction.
        return load_player_game_state(rules.GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's isolated production game document.
    @staticmethod
    def _save_production_state(player_id: str, state: dict) -> None:  # Save only one authenticated player's game document.
        # Delegate through the shared player-scoped storage abstraction.
        save_player_game_state(rules.GAME_ID, player_id, state)

    # Load one player document through the injected state dependency.
    def _load(self, player_id: str) -> dict:
        # Return only state owned by the already resolved authenticated player.
        return self._state_loader(player_id)

    # Save one player document through the injected state dependency.
    def _save(self, player_id: str, state: dict) -> None:
        # Persist only state owned by the already resolved authenticated player.
        self._state_saver(player_id, state)

    # Derive the deterministic action key for one round movement.
    @staticmethod
    def _action_key(round_id: str, action: str) -> str:  # Build one deterministic ledger movement identity.
        # Join the bounded round id and fixed action label without caller text.
        return f"{round_id}:{action}"

    # Find committed ledger proof for one wager or settlement action.
    def _proof(self, *, player_id: str, round_id: str, transaction_type: str, action: str, request_fingerprint: str):
        # Delegate exact ownership matching to the game-owned ledger gateway.
        return self._ledger_gateway.find(player_id=player_id, round_id=round_id, transaction_type=transaction_type, action_key=self._action_key(round_id, action), request_fingerprint=request_fingerprint)

    # Recover and validate the authoritative dice stored in committed debit details.
    @staticmethod
    def _committed_dice(debit_event: dict) -> list[int]:  # Recover the authoritative faces from committed wager proof.
        # Read game-owned audit details from the matched wager event.
        details = debit_event.get("details") or {}
        # Translate corrupt or missing committed dice into a settlement conflict.
        try:
            # Validate the exact three faces before calculating any payout.
            return engine.require_dice(details.get("dice"))
        # Keep persisted-ledger corruption distinct from a new client validation error.
        except ValidationError as error:
            # Fail closed because settlement cannot safely choose replacement entropy.
            raise ConflictError("Committed Chuck-a-Luck dice are unavailable or invalid") from error

    # Build the shared state/player/rules payload for every game endpoint.
    def payload(self, player_id: str, state=None) -> dict:
        # Load player-owned state only when a caller has not already mutated a copy.
        current = state if state is not None else self._load(player_id)
        # Return reload-safe game state, wallet snapshot, and immutable bet metadata.
        return {"game": rules.GAME_ID, "state": engine.public_state(current), "player": self._get_player(player_id), "bet_catalog": rules.bet_catalog()}

    # Return the current authenticated player's reload-safe game payload.
    def state(self, player_id: str) -> dict:
        # Reuse the common payload builder without touching the ledger or entropy.
        return self.payload(player_id)

    # Read ledger evidence for a state-cached settled replay.
    def _round_ledger(self, player_id: str, round_row: dict) -> dict:
        # Cache stable proof fields from the settled round.
        round_id = round_row["round_id"]
        # Cache the canonical wager fingerprint for both ledger actions.
        fingerprint = round_row["request_fingerprint"]
        # Find the required aggregate wager debit proof.
        wager_event = self._proof(player_id=player_id, round_id=round_id, transaction_type=WAGER_TRANSACTION_TYPE, action="wager", request_fingerprint=fingerprint)
        # Start with no settlement proof for a losing round.
        settlement_event = None
        # Find a credit proof only when the round returned stake plus winnings.
        if round_row.get("total_return", 0) > 0:
            # Resolve the optional aggregate credit through all immutable dimensions.
            settlement_event = self._proof(player_id=player_id, round_id=round_id, transaction_type=SETTLEMENT_TRANSACTION_TYPE, action="settlement", request_fingerprint=fingerprint)
        # Return only ledger events owned by this player and round.
        return {"wager": wager_event, "settlement": settlement_event}

    # Execute or replay one complete ledger-backed Chuck-a-Luck roll.
    def roll(self, player_id: str, request: dict) -> dict:
        # Require an object payload before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed calls before state, entropy, or ledger access.
            raise ValidationError("Chuck-a-Luck roll body must be an object")
        # Validate the caller-stable retry identity before any mutable operation.
        request_id = require_request_id(request.get("request_id"))
        # Normalize every face wager before state or ledger lookup.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Derive the semantic request fingerprint used for conflict detection.
        request_fingerprint = engine.wager_fingerprint(wagers)
        # Derive one stable player-scoped round identifier for ledger recovery.
        round_id = engine.round_id_for(player_id, request_id)
        # Serialize state cache, ledger proof, entropy, settlement, and persistence locally.
        with _SETTLEMENT_LOCK:
            # Load the latest state inside the same lock used by apply-once ledger checks.
            state = self._load(player_id)
            # Resolve a fully settled retry from the bounded player state first.
            existing_round = engine.find_round(state, request_id)
            # Return the original immutable state result for a normal retry.
            if existing_round is not None:
                # Reject reuse of one request identity for different wager content.
                if existing_round.get("request_fingerprint") != request_fingerprint:
                    # Fail closed without inspecting or moving the player's wallet.
                    raise ConflictError("Chuck-a-Luck request_id was already used with different wagers")
                # Recover player-owned ledger evidence for the settled state row.
                ledger_events = self._round_ledger(player_id, existing_round)
                # Return the same settled round and current reload-safe state.
                return {"round": engine.public_round(existing_round), "replayed": True, "ledger": ledger_events, **self.payload(player_id, state)}
            # Produce proposed server-authoritative dice for a never-seen or interrupted action.
            proposed_dice = engine.roll_dice(self._randbelow)
            # Calculate the one aggregate wager debit before touching the ledger.
            wager_total = engine.total_wager(wagers)
            # Store everything required to reconstruct the result after a post-debit crash.
            wager_details = {"request_id": request_id, "wagers": wagers, "dice": proposed_dice, "total_wager": wager_total}
            # Commit or recover the single aggregate wager debit.
            wager_event, wager_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=-wager_total, transaction_type=WAGER_TRANSACTION_TYPE, round_id=round_id, action_key=self._action_key(round_id, "wager"), request_fingerprint=request_fingerprint, details=wager_details)
            # Recover the original committed faces instead of trusting retry entropy.
            committed_dice = self._committed_dice(wager_event)
            # Calculate every return deterministically from committed wagers and dice.
            settlement = engine.settle(wagers, committed_dice)
            # Start with no credit event for a completely losing set of wagers.
            settlement_event = None
            # Track whether crash recovery reused a committed settlement credit.
            settlement_replayed = False
            # Credit stake plus net winnings only when at least one wager matched.
            if settlement["total_return"] > 0:
                # Build complete game-owned audit details for the aggregate return.
                settlement_details = {"request_id": request_id, "wagers": wagers, "dice": committed_dice, "total_return": settlement["total_return"], "settlements": settlement["settlements"]}
                # Commit or recover the one aggregate stake-plus-winnings credit.
                settlement_event, settlement_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=settlement["total_return"], transaction_type=SETTLEMENT_TRANSACTION_TYPE, round_id=round_id, action_key=self._action_key(round_id, "settlement"), request_fingerprint=request_fingerprint, details=settlement_details)
            # Prefer the committed debit time so reconstructed retries retain round timing.
            settled_at = wager_event.get("ts") or self._clock()
            # Build the stable settled row returned by state and action endpoints.
            round_row = {
                "round_id": round_id,  # Correlate state and both ledger actions.
                "request_id": request_id,  # Preserve the bounded client retry identity.
                "request_fingerprint": request_fingerprint,  # Preserve semantic conflict proof.
                "player_id": player_id,  # Bind the result to the authenticated player.
                "status": "settled",  # Expose one terminal state for this atomic game action.
                "wagers": wagers,  # Preserve normalized one-through-six stakes.
                **settlement,  # Include dice, totals, net, and per-wager audit rows.
                "settled_at": settled_at,  # Preserve stable committed timing across retries.
            }
            # Add the completed round only after every required ledger action committed.
            engine.record_round(state, round_row)
            # Persist bounded reload-safe history; ledger keys recover a failed save.
            self._save(player_id, state)
            # Report whether either ledger action came from earlier committed proof.
            replayed = wager_replayed or settlement_replayed
            # Return the settled action, scoped ledger evidence, and refreshed game payload.
            return {"round": engine.public_round(round_row), "replayed": replayed, "ledger": {"wager": wager_event, "settlement": settlement_event}, **self.payload(player_id, state)}
