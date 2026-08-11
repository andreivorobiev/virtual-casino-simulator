# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Ledger-only, reload-safe, exactly-once Sic Bo orchestration for issue #88."""

# Import conservative action-id validation for persisted retry identities.
import re
# Import cryptographic bounded integers for production dice entropy.
import secrets
# Import one process-wide reentrant lock for state and ledger recovery sequences.
import threading

# Import the read-only players facade without a game-owned ledger mutation boundary.
from casino.core import players
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistence without changing shared storage code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict and validation errors for route envelopes.
from casino.errors import ConflictError, ValidationError
# Import pure validation, settlement, and state helpers from this game only.
from casino.games.sic_bo import engine
# Import the stable game identity for every ledger event.
from casino.games.sic_bo.rules import GAME_ID

# Serialize state preparation, ledger proof, movement, and archival in this local process.
_SETTLEMENT_LOCK = threading.RLock()
# Restrict client action identities to bounded log-safe characters.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old Sic Bo key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "sic_bo_action_id", **kwargs)


# Coordinate player state, dice entropy, and exactly-once settlement.
class SicBoService:
    # Capture injectable dependencies so focused tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, load_state=None, save_state=None, get_player=None, randbelow=None, clock=None):
        # Use the game-local shared-ledger adapter unless a test supplies a fake.
        self._ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the shared authenticated resolver.
        self._load_state = load_state or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Use player-scoped persistence without changing shared state code.
        self._save_state = save_state or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Use the read-only player facade for current wallet snapshots.
        self._get_player = get_player or players.get_player
        # Use cryptographic bounded integers unless a test injects deterministic dice.
        self._randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins lifecycle time.
        self._clock = clock or utc_now

    # Validate the stable identity required for safe action retries.
    def _action_id(self, value) -> str:
        # Require one bounded URL-safe string without coercing caller values.
        if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
            # Reject malformed identities before state, entropy, or ledger access.
            raise ValidationError("action_id must be 1-128 URL-safe characters")
        # Return the original case-sensitive action identity.
        return value

    # Load one authenticated player's isolated state document.
    def _load(self, player_id: str) -> dict:
        # Delegate through the injected or production player-scoped loader.
        return self._load_state(player_id)

    # Persist one authenticated player's recovery or settled state.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate through the injected or production player-scoped writer.
        self._save_state(player_id, state)

    # Build the public state, rules, and read-only wallet snapshot shared by routes.
    def payload(self, player_id: str, state=None) -> dict:
        # Load the latest state only when an action has not supplied its in-memory copy.
        current = state if state is not None else self._load(player_id)
        # Return game-owned state plus immutable rule metadata and current-player data.
        return {"game": GAME_ID, "state": engine.public_state(current), "bets": engine.public_bets(), "player": self._get_player(player_id)}

    # Return the deterministic action key for one ledger movement kind.
    def _ledger_action_key(self, round_id: str, kind: str) -> str:
        # Join bounded server identifiers without exposing caller text.
        return f"{round_id}:{kind}"

    # Return a prior committed movement for response or cleanup decisions.
    def _ledger_event(self, player_id: str, round_id: str, kind: str) -> dict | None:
        # Delegate exact lookup to the same gateway used for apply-once settlement.
        return self._ledger_gateway.find(player_id, self._ledger_action_key(round_id, kind))

    # Prepare one private result before movement so restart recovery is deterministic.
    def _prepare_round(self, player_id: str, action_id: str, wagers: dict[str, float], request_fingerprint: str) -> dict:
        # Derive a stable bounded round id from player and caller action identity.
        round_id = engine.round_id_for(player_id, action_id)
        # Roll three server-authoritative dice through the injectable entropy seam.
        dice = engine.roll_dice(self._randbelow)
        # Build the pending record saved before the aggregate wager debit.
        return {
            "round_id": round_id,  # Address both ledger action keys through one stable round.
            "action_id": action_id,  # Preserve the caller identity for exact replay matching.
            "player_id": player_id,  # Bind the recovery record to the authenticated session player.
            "request_fingerprint": request_fingerprint,  # Detect semantically conflicting retries.
            "wagers": wagers,  # Preserve canonical wager content for reload recovery.
            "dice": dice,  # Preserve the private result without exposing it before debit.
            "phase": "prepared",  # Mark the restart-safe pre-ledger state.
            "wager_status": "pending",  # Record that aggregate debit proof is still required.
            "payout_status": "not_ready",  # Prevent credit before result calculation.
            "created_at": self._clock(),  # Preserve one stable lifecycle start time.
        }

    # Return one previously settled action without repeating entropy or token movement.
    def _settled_replay(self, player_id: str, state: dict, round_state: dict) -> dict:
        # Recover the original aggregate wager event for scoped response evidence.
        wager_event = self._ledger_event(player_id, round_state["round_id"], "wager")
        # Recover an optional positive settlement event when one exists.
        payout_event = self._ledger_event(player_id, round_state["round_id"], "payout")
        # Return the stable round, current state, and explicit replay flag.
        return {"round": engine.public_round(round_state), "replayed": True, "ledger": {"wager": wager_event, "payout": payout_event}, **self.payload(player_id, state)}

    # Execute or recover one complete ledger-backed Sic Bo shake.
    def play(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before reading action or wager fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before any protected operation.
            raise ValidationError("Sic Bo round body must be an object")
        # Match the closed request schema while retaining the v1 compatibility player field.
        unexpected_fields = set(request) - {"action_id", "wagers", "player_id"}
        # Reject misspelled or speculative fields instead of silently discarding them.
        if unexpected_fields:
            # Keep the error deterministic without echoing arbitrary caller-controlled values.
            raise ValidationError("Sic Bo round body contains unsupported fields")
        # Validate the stable network-retry identity.
        action_id = self._action_id(request.get("action_id"))
        # Normalize all positions and amounts into canonical board order.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Calculate the semantic fingerprint used by state and ledger recovery.
        request_fingerprint = engine.wager_fingerprint(wagers)
        # Serialize the entire prepare, movement, recovery, and archive sequence.
        with _SETTLEMENT_LOCK:
            # Load the latest authenticated player state inside the process lock.
            state = self._load(player_id)
            # Resolve an active or archived action before generating new entropy.
            existing = engine.round_for_action(state, action_id)
            # Reject one action identity reused for different canonical wagers.
            if existing is not None and existing.get("request_fingerprint") != request_fingerprint:
                # Fail closed before any second movement can occur.
                raise ConflictError("Sic Bo action_id was already used with different wagers")
            # Return an already archived action without touching state or ledger.
            if existing is not None and existing.get("phase") == "settled" and state.get("active_round") is not existing:
                # Reuse the exact settled response and ledger evidence.
                return self._settled_replay(player_id, state, existing)
            # Prevent a new action from bypassing another interrupted settlement.
            if existing is None and state.get("active_round") is not None:
                # Require recovery of the committed active action first.
                raise ConflictError("Resume the active Sic Bo round before starting another")
            # Reuse prepared recovery state or create a new private result.
            round_state = existing or self._prepare_round(player_id, action_id, wagers, request_fingerprint)
            # Persist a new preparation before any aggregate wager movement.
            if existing is None:
                # Store the only actionable recovery record.
                state["active_round"] = round_state
                # Make the action and private dice durable before debit.
                self._save(player_id, state)
            # Build stable debit details sufficient to recover after a process restart.
            wager_details = {"action_id": action_id, "request_fingerprint": request_fingerprint, "wagers": wagers, "dice": list(round_state["dice"])}
            # Attempt the aggregate debit with cleanup only when no event committed.
            try:
                # Apply the single total wager through the shared ledger adapter.
                wager_event, wager_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=-sum(wagers.values()), transaction_type="SIC_BO_WAGER_DEBIT", round_id=round_state["round_id"], action_key=self._ledger_action_key(round_state["round_id"], "wager"), details=wager_details)
            # Preserve the original ledger or storage failure after safe cleanup.
            except Exception as error:
                # Check whether the debit committed before the failure surfaced.
                committed_wager = self._ledger_event(player_id, round_state["round_id"], "wager")
                # Clear a brand-new preparation after semantic collision with an aged ledger action.
                new_action_conflict = existing is None and isinstance(error, ConflictError)
                # Remove only state that cannot safely resume this proposed request.
                if committed_wager is None or new_action_conflict:
                    # Clear only the non-resumable proposal so the player can edit wagers.
                    state["active_round"] = None
                    # Persist cleanup before returning the original failure.
                    self._save(player_id, state)
                # Re-raise the original failure for the standard error envelope.
                raise
            # Recover the dice sealed into the committed debit event after a crash retry.
            committed_dice = engine.require_dice((wager_event.get("details") or {}).get("dice", round_state["dice"]))
            # Replace any newly proposed recovery dice with the committed result.
            round_state["dice"] = committed_dice
            # Mark the aggregate wager complete only after ledger proof exists.
            round_state["wager_status"] = "complete"
            # Store the immutable debit event id for API evidence.
            round_state["wager_ledger_id"] = wager_event.get("ledger_id")
            # Mark result calculation as the next recovery phase.
            round_state["phase"] = "settling"
            # Persist the committed-wager marker before calculating payout intent.
            self._save(player_id, state)
            # Calculate every position and aggregate returned credits from committed dice.
            settlement = engine.settle(wagers, committed_dice)
            # Merge the deterministic result into the recovery record.
            round_state.update(settlement)
            # Mark positive returned credits as pending and zero returns as complete.
            round_state["payout_status"] = "pending" if settlement["total_return"] > 0 else "complete"
            # Persist the known result before any payout credit.
            self._save(player_id, state)
            # Start without a payout event for fully losing rounds.
            payout_event = None
            # Track whether payout recovery reused an earlier committed event.
            payout_replayed = False
            # Credit stake plus winnings only when at least one covered position won.
            if settlement["total_return"] > 0:
                # Build stable credit details from the already-known result.
                payout_details = {"action_id": action_id, "request_fingerprint": request_fingerprint, "dice": committed_dice, "outcome": settlement["outcome"], "settlements": settlement["settlements"]}
                # Apply at most one aggregate returned-credit ledger event.
                payout_event, payout_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=settlement["total_return"], transaction_type="SIC_BO_PAYOUT_CREDIT", round_id=round_state["round_id"], action_key=self._ledger_action_key(round_state["round_id"], "payout"), details=payout_details)
                # Mark payout complete only after committed ledger proof exists.
                round_state["payout_status"] = "complete"
                # Store the immutable payout event id for API evidence.
                round_state["payout_ledger_id"] = payout_event.get("ledger_id")
                # Persist the recovered or newly committed payout marker.
                self._save(player_id, state)
            # Mark the public lifecycle complete after every required movement.
            round_state["phase"] = "settled"
            # Preserve a stable completion timestamp for history display.
            round_state["completed_at"] = self._clock()
            # Archive the completed action and clear the recovery slot.
            engine.record_round(state, round_state)
            # Persist reload-safe bounded history after settlement.
            self._save(player_id, state)
            # Report replay when any prior state or ledger proof was reused.
            replayed = existing is not None or wager_replayed or payout_replayed
            # Return settled round, ledger evidence, and current player-owned state.
            return {"round": engine.public_round(round_state), "replayed": replayed, "ledger": {"wager": wager_event, "payout": payout_event}, **self.payload(player_id, state)}
