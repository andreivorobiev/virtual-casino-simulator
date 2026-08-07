"""Ledger-only, retry-safe orchestration for Crown and Anchor rounds."""

# Import cryptographic randomness for production dice rolls.
import secrets
# Import shared clock helper for stable settled timestamps.
from casino.core.clock import utc_now
# Import the one approved play-token settlement compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped persistence helpers without changing shared storage code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict and validation errors for retry enforcement.
from casino.errors import ConflictError, ValidationError
# Import pure rules and state helpers from this game package only.
from casino.games.crown_and_anchor import engine
# Import stable game id and symbol metadata for ledger details and state payloads.
from casino.games.crown_and_anchor.rules import GAME_ID, symbol_catalog

# Bound caller-supplied idempotency identities before persistence.
MAX_CLIENT_REQUEST_ID_LENGTH = 128


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old idempotency key beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "idempotency_key", **kwargs)


# Coordinate player state, dice entropy, and exactly-once ledger movement.
class CrownAndAnchorService:
    # Capture injectable seams so focused tests avoid filesystem and ambient randomness.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, roll_die=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the authenticated route resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Use player-scoped persistence without mutating shared state modules.
        self.state_saver = state_saver or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Use cryptographic one-based dice unless a focused test supplies deterministic rolls.
        self.roll_die = roll_die or (lambda: secrets.randbelow(6) + 1)
        # Use the shared UTC clock unless a focused test pins timestamps.
        self.clock = clock or utc_now

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
        state = self.state_loader(player_id)
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
        state = self.state_loader(player_id)
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
        self.state_saver(player_id, state)
        # Return ledger evidence without exposing unrelated player history.
        return {"round": round_row, "replayed": debit_replayed or credit_replayed, "ledger": {"wager": debit_event, "settlement": credit_event}}
