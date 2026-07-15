"""Session-bound, ledger-only orchestration for Over/Under 7 plays."""

# Import cryptographic randomness for production dice.
import secrets
# Import regular expressions for bounded public action identities.
import re
# Import a reentrant lock for local exactly-once ledger coordination.
import threading

# Import the only approved player-balance mutation service.
from casino.core import ledger, players
# Import the shared UTC clock for settled round timestamps.
from casino.core.clock import utc_now
# Import player-scoped persistence without shared storage edits.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import shared conflict and validation errors.
from casino.errors import ConflictError, ValidationError
# Import this game's pure engine and immutable rules.
from casino.games.over_under_7 import engine
# Import the stable game identity and paytable.
from casino.games.over_under_7.rules import GAME_ID, paytable

# Bound client action ids to log-safe characters and a conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local player history to recover retries after normal restarts.
LEDGER_SCAN_LIMIT = 1_000_000
# Serialize read-before-write checks in the local one-process simulator.
_ACTION_LOCK = threading.RLock()


# Validate one required action identity.
def require_action_id(value) -> str:
    # Accept only bounded URL-safe string identities.
    if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
        # Explain the public contract without echoing hostile text.
        raise ValidationError("action_id must be 1-128 URL-safe characters")
    # Return the original identity for stable retries.
    return value


# Adapt the shared ledger into a game action-id apply-once interface.
class CoreLedgerGateway:
    # Capture injectable shared-ledger functions for focused tests.
    def __init__(self, *, debit=ledger.debit, credit=ledger.credit, read_recent=ledger.read_recent):
        # Store the only allowed wager debit operation.
        self._debit = debit
        # Store the only allowed returned-token credit operation.
        self._credit = credit
        # Store player-scoped ledger lookup for reload recovery.
        self._read_recent = read_recent

    # Find one committed game action for an authenticated player.
    def find(self, player_id: str, action_key: str):
        # Read only this player's append-only ledger rows.
        rows = self._read_recent(player_id, LEDGER_SCAN_LIMIT)
        # Scan newest first for this game's stable action detail.
        return next((row for row in reversed(rows) if row.get("game") == GAME_ID and (row.get("details") or {}).get("over_under_7_action_key") == action_key), None)

    # Commit or recover one signed token movement exactly once.
    def apply_once(self, *, player_id: str, signed_amount: float, transaction_type: str, round_id: str, action_key: str, fingerprint: str, details: dict) -> tuple[dict, bool]:
        # Protect the lookup and append sequence from duplicate concurrent requests.
        with _ACTION_LOCK:
            # Resolve any previously committed action for this player and game.
            existing = self.find(player_id, action_key)
            # Reuse exact matches and reject semantic conflicts.
            if existing is not None:
                # Compare amount, type, round, and semantic request content.
                matches = round(float(existing.get("amount", 0)), 2) == round(float(signed_amount), 2) and existing.get("transaction_type") == transaction_type and existing.get("round_id") == round_id and (existing.get("details") or {}).get("request_fingerprint") == fingerprint
                # Reject one action key reused for another movement.
                if not matches:
                    # Fail closed before changing the wallet.
                    raise ConflictError("Over/Under 7 ledger action identity conflicts with an existing event")
                # Return immutable proof and replay evidence.
                return existing, True
            # Add stable action metadata to the ledger details.
            event_details = {**details, "over_under_7_action_key": action_key, "request_fingerprint": fingerprint}
            # Route debits through the approved ledger debit service.
            if signed_amount < 0:
                # Commit the positive debit magnitude.
                event = self._debit(player_id, abs(signed_amount), transaction_type, GAME_ID, round_id, event_details)
            # Route returned tokens through the approved ledger credit service.
            else:
                # Commit the returned stake or payout.
                event = self._credit(player_id, signed_amount, transaction_type, GAME_ID, round_id, event_details)
            # Return the new committed event and non-replay evidence.
            return event, False


# Coordinate state, dice, and retry-safe ledger movements.
class OverUnder7Service:
    # Capture production dependencies while exposing deterministic focused-test seams.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, get_player=None, randbelow=None, clock=None):
        # Use the game-local ledger adapter unless a test supplies a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Load one authenticated player's state document by default.
        self._load_state = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Save one authenticated player's state document by default.
        self._save_state = state_saver or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Return current-player information without direct balance mutation.
        self._get_player = get_player or players.get_player
        # Use cryptographic dice unless a focused test supplies deterministic values.
        self._randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins time.
        self._clock = clock or utc_now

    # Build the public state, rules, and player payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return only this player's game state and transparent paytable.
        return {"game": GAME_ID, "state": {"recent_rounds": list(state.get("recent_rounds", []))}, "player": self._get_player(player_id), "rules": {"dice": 2, "sides": 6, "paytable": paytable(), "profile": "under_7_exact_7_over_7"}}

    # Return reload-safe state for the authenticated player.
    def state(self, player_id: str) -> dict:
        # Load only the bound player's document.
        state = self._load_state(player_id)
        # Return the sanitized payload.
        return self._payload(player_id, state)

    # Execute or replay one complete dice proposition play.
    def play(self, player_id: str, request: dict) -> dict:
        # Require an object payload before reading action fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before dice, state, or ledger work.
            raise ValidationError("Over/Under 7 play body must be an object")
        # Validate the retry-safe action identity.
        action_id = require_action_id(request.get("action_id"))
        # Normalize all proposition wagers.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Bind the action identity to exact normalized wager content.
        fingerprint = engine.wager_fingerprint(wagers)
        # Serialize state lookup, ledger debit, dice recovery, and settlement.
        with _ACTION_LOCK:
            # Load the current player's latest document.
            state = self._load_state(player_id)
            # Resolve an exact retained retry without rolling dice.
            existing_round = engine.find_round(state, action_id)
            # Branch when state already contains this action.
            if existing_round is not None:
                # Reject changed request content for the same action id.
                if existing_round.get("request_fingerprint") != fingerprint:
                    # Fail before duplicate settlement.
                    raise ConflictError("Over/Under 7 action_id was already used with different wagers")
                # Return the stable prior result.
                return {"round": existing_round, "replayed": True, **self._payload(player_id, state)}
            # Derive one stable server round id.
            round_id = engine.round_id_for(player_id, action_id)
            # Check the append-only ledger for a prior debit after lost state.
            existing_debit = self._ledger.find(player_id, f"{round_id}:wager")
            # Reuse committed dice from a recovered wager event when present.
            if existing_debit is not None:
                # Reject changed request content before reconstructing settlement.
                if (existing_debit.get("details") or {}).get("request_fingerprint") != fingerprint:
                    # Preserve the committed wallet movement.
                    raise ConflictError("Committed Over/Under 7 wager action conflicts with request body")
                # Recover dice from the durable debit details.
                dice = tuple((existing_debit.get("details") or {}).get("dice", []))
            # Roll dice before debit so debit details can recover the exact result.
            else:
                # Select two dice through the injectable seam.
                dice = engine.roll_dice(self._randbelow)
            # Calculate the complete deterministic settlement.
            settlement = engine.settle(wagers, dice)
            # Build debit details containing every field needed for recovery.
            debit_details = {"action_id": action_id, "wagers": wagers, "dice": list(dice), "total": settlement["total"], "outcome": settlement["outcome"]}
            # Apply or recover the total wager debit exactly once.
            debit_event, debit_replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-settlement["total_wager"], transaction_type="OVER_UNDER_7_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", fingerprint=fingerprint, details=debit_details)
            # Start with no settlement credit for uncovered or losing outcomes.
            credit_event = None
            # Track credit replay evidence independently of debit replay.
            credit_replayed = False
            # Return tokens only when the winning proposition was covered.
            if settlement["total_return"] > 0:
                # Build credit details from the immutable settlement.
                credit_details = {"action_id": action_id, "outcome": settlement["outcome"], "dice": settlement["dice"], "total": settlement["total"], "settlements": settlement["settlements"]}
                # Apply or recover the returned-token credit exactly once.
                credit_event, credit_replayed = self._ledger.apply_once(player_id=player_id, signed_amount=settlement["total_return"], transaction_type="OVER_UNDER_7_SETTLEMENT_CREDIT", round_id=round_id, action_key=f"{round_id}:settlement", fingerprint=fingerprint, details=credit_details)
            # Use the committed debit timestamp when available for retry stability.
            settled_at = debit_event.get("ts") or self._clock()
            # Build the durable round row published by state and action endpoints.
            round_row = {"round_id": round_id, "action_id": action_id, "request_fingerprint": fingerprint, "player_id": player_id, "status": "settled", "settled_at": settled_at, "wagers": wagers, **settlement}
            # Record the settled round after required ledger movements exist.
            engine.record_round(state, round_row)
            # Persist reload-safe history.
            self._save_state(player_id, state)
            # Return state, player, and ledger evidence for focused tests.
            return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}, **self._payload(player_id, state)}
