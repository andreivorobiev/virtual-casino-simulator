"""Ledger-only, retry-safe orchestration for Fan-Tan rounds."""

# Import cryptographic index selection for production pile counts.
import secrets
# Import the shared UTC clock for settled response timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistence helpers without changing shared state code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import standard conflict and validation errors for request identity enforcement.
from casino.errors import ConflictError, ValidationError
# Import pure Fan-Tan calculations and state helpers.
from casino.games.fan_tan import engine
# Import the stable game identity for every ledger event.
from casino.games.fan_tan.rules import GAME_ID

# Bound caller-supplied action identifiers before persistence.
MAX_ACTION_ID_LENGTH = 128


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old Fan-Tan key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "fan_tan_action_id", **kwargs)


# Coordinate player state, entropy, and exactly-once ledger actions for one Fan-Tan play.
class FanTanService:
    # Capture injectable seams so deterministic tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, randbelow=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the authenticated-player resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Use player-scoped persistence without mutating any shared state module.
        self.state_saver = state_saver or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Use cryptographic uniform selection unless a focused test supplies a deterministic source.
        self.randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins response time.
        self.clock = clock or utc_now

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
        state = self.state_loader(player_id)
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
        state = self.state_loader(player_id)
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
        self.state_saver(player_id, state)
        # Return ledger evidence without exposing unrelated player history.
        return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}}
