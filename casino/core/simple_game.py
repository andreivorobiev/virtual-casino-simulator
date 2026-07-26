"""Shared exactly-once wager-and-settle core for catalog games. (#73 expansion)

Every ledger-backed game repeats the same subtle money contract: draw server entropy, debit a wager,
settle deterministically, credit any return, and stay retry-safe across a lost response or a crashed
process. Re-implementing that per game multiplies the surface for money bugs. This core owns it once so a
game module supplies only its pure rules — a bet validator and a deterministic resolver — and inherits a
proven exactly-once settlement path.

The contract this core guarantees:

- One caller-stable request_id maps to one round; a retry replays the identical committed outcome.
- Server entropy is committed inside the wager ledger proof, so settlement is deterministic even when a
  crash forces recovery from the ledger alone.
- The wager debit and the settlement credit are each applied exactly once, guarded by ledger proof plus a
  request fingerprint, so the same identity can never move two different amounts.
- A request_id reused with different wager content fails closed as a conflict rather than double-spending.
"""

# Import hashing for the deterministic round identity.
import hashlib
# Import bounded request-id validation.
import re
# Import cryptographic bounded random draws for production entropy.
import secrets
# Import a process-local reentrant lock for exactly-once local settlement.
import threading

# Import the shared ledger and player services without mutating balances directly.
from casino.core import ledger, players
# Import the shared UTC clock for stable settled-response timestamps.
from casino.core.clock import utc_now
# Import player-scoped persistence for authenticated session isolation.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import the public conflict and validation errors for safe API boundaries.
from casino.errors import ConflictError, ValidationError

# Bound request identifiers to conservative URL-safe characters and length.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize state, ledger proof, debit, settlement, and persistence per process.
_SETTLEMENT_LOCK = threading.RLock()
# Scan a generous player-local history window for restart-safe ledger proof.
LEDGER_PROOF_SCAN_LIMIT = 1_000_000
# Bound the retained per-player recent-round history so state stays compact.
RECENT_ROUND_LIMIT = 25


# Validate the caller-stable identity used for network and crash retries.
def require_request_id(value) -> str:
    # Require a bounded URL-safe string so the value is safe in logs, JSON, and hashes.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the exact validated identity for stable hashing and comparison.
    return value


# Derive one deterministic round identity from the game, player, and request id.
def round_id_for(game_id: str, player_id: str, request_id: str) -> str:
    # Return a bounded hex digest so the round id never carries caller-controlled structure.
    return hashlib.sha256(f"{game_id}\0{player_id}\0{request_id}".encode("utf-8")).hexdigest()[:24]


# Adapt the shared ledger into a game-owned apply-once action interface.
class _LedgerGateway:
    # Bind the gateway to one game so proof can never be satisfied by another game's rows.
    def __init__(self, game_id: str) -> None:
        # Retain the owning game id for the proof predicate.
        self.game_id = game_id

    # Find one committed action matching every ownership and request dimension.
    def find(self, *, player_id, round_id, transaction_type, action_key, request_fingerprint):
        # Read only the authenticated player's recent ledger rows.
        rows = ledger.read_recent(player_id, LEDGER_PROOF_SCAN_LIMIT)
        # Scan newest-first for the deterministic action identity.
        for event in reversed(rows):
            # Read event details once for action-key and fingerprint checks.
            details = event.get("details") or {}
            # Skip rows that do not match every immutable action dimension.
            if not (event.get("player_id") == player_id and event.get("game") == self.game_id and event.get("round_id") == round_id and event.get("transaction_type") == transaction_type and details.get("idempotency_key") == action_key):
                # Continue until a row satisfies every ownership dimension.
                continue
            # Reject the same action identity reused for different wager content.
            if details.get("request_fingerprint") != request_fingerprint:
                # Fail closed instead of returning or duplicating a conflicting event.
                raise ConflictError(f"{self.game_id} request_id conflicts with committed ledger proof")
            # Return the fully matched committed ledger event.
            return event
        # Report no proof when the requested action has never committed.
        return None

    # Commit one debit or credit exactly once for the local simulator process.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint, details) -> tuple:
        # Serialize the proof-before-write sequence against concurrent duplicate requests.
        with _SETTLEMENT_LOCK:
            # Resolve any committed action before issuing another balance movement.
            existing = self.find(player_id=player_id, round_id=round_id, transaction_type=transaction_type, action_key=action_key, request_fingerprint=request_fingerprint)
            # Reuse exact committed proof for a normal or crash-recovery retry.
            if existing is not None:
                # Reject an action-key collision whose signed amount changed unexpectedly.
                if round(float(existing.get("amount", 0)), 2) != round(float(amount), 2):
                    # Fail closed because one action identity cannot move two amounts.
                    raise ConflictError(f"{self.game_id} ledger action amount conflicts with committed proof")
                # Return the original event and explicit replay evidence.
                return existing, True
            # Add action and fingerprint proof to the game-owned audit details.
            event_details = {**details, "idempotency_key": action_key, "request_fingerprint": request_fingerprint}
            # Route a negative signed amount through the only approved debit service.
            if amount < 0:
                # Commit the aggregate wager debit with full player, game, and round dimensions.
                event = ledger.debit(player_id, abs(amount), transaction_type, self.game_id, round_id, event_details)
            # Route a positive signed amount through the only approved credit service.
            else:
                # Commit the aggregate settlement credit with the same dimensions.
                event = ledger.credit(player_id, amount, transaction_type, self.game_id, round_id, event_details)
            # Return the freshly committed event and explicit first-write evidence.
            return event, False


# Coordinate authenticated state, server entropy, and exactly-once ledger settlement for one game.
class SimpleWagerGame:
    # Configure the core with one game's identity, rules, and injectable test seams.
    def __init__(self, *, game_id, wager_transaction_type, settlement_transaction_type, entropy, resolve, validate_bet, public_bet_catalog=None, ledger_gateway=None, state_loader=None, state_saver=None, entropy_source=None, clock=None, get_player=None) -> None:
        # Retain the fixed game identity used across every ledger and state dimension.
        self.game_id = str(game_id)
        # Retain the two aggregate transaction-type names used for recovery-stable proof.
        self.wager_transaction_type = str(wager_transaction_type)
        self.settlement_transaction_type = str(settlement_transaction_type)
        # Retain the pure callable that draws the game's server entropy from a random function.
        self._entropy = entropy
        # Retain the pure deterministic resolver mapping a validated bet plus entropy to a settlement.
        self._resolve = resolve
        # Retain the pure bet validator that normalizes caller input into an authoritative wager.
        self._validate_bet = validate_bet
        # Retain the optional public bet catalog builder for the state payload.
        self._public_bet_catalog = public_bet_catalog or (lambda: {})
        # Bind the ledger gateway to this game unless a focused test injects one.
        self._ledger_gateway = ledger_gateway or _LedgerGateway(self.game_id)
        # Use player-scoped production persistence unless a test injects loaders.
        self._state_loader = state_loader or (lambda player_id: load_player_game_state(self.game_id, player_id, self._default_state))
        self._state_saver = state_saver or (lambda player_id, state: save_player_game_state(self.game_id, player_id, state))
        # Use a cryptographic bounded random source unless a test pins entropy.
        self._entropy_source = entropy_source or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins settlement time.
        self._clock = clock or utc_now
        # Use the shared player read unless a test injects a wallet accessor.
        self._get_player = get_player or players.get_player

    # Build the empty per-player game document.
    def _default_state(self) -> dict:
        # Hold only this game's compact recent-round history.
        return {"game": self.game_id, "recent_rounds": []}

    # Build one deterministic ledger movement identity for a wager or settlement action.
    def _action_key(self, round_id: str, action: str) -> str:
        # Combine the round and action so the two movements never share an identity.
        return f"{round_id}:{action}"

    # Build the public state payload for one authenticated player.
    def state(self, player_id: str) -> dict:
        # Load the player's current document.
        current = self._state_loader(player_id)
        # Publish the compact game state, wallet, and bet catalog.
        return {"game": self.game_id, "state": current, "player": self._get_player(player_id), "bet_catalog": self._public_bet_catalog()}

    # Locate a prior round in state for replay detection.
    def _find_round(self, state: dict, request_id: str):
        # Scan the retained recent rounds for the matching request id.
        for round_row in state.get("recent_rounds", []):
            # Return the first round created by this request id.
            if round_row.get("request_id") == request_id:
                # Report the existing round for replay handling.
                return round_row
        # Report no prior round for a first-time request.
        return None

    # Execute or replay one atomic wager, entropy draw, and settlement for a player.
    def play(self, player_id: str, request: dict) -> dict:
        # Require the caller-stable retry identity before any state or ledger access.
        request_id = require_request_id((request or {}).get("request_id"))
        # Validate and normalize the caller's bet into an authoritative wager plus its total stake.
        wager, wager_total, fingerprint = self._validate_bet(request or {})
        # Reject a non-positive aggregate stake before touching the wallet.
        if wager_total <= 0:
            # Fail closed on an empty or malformed wager.
            raise ValidationError(f"{self.game_id} requires a positive wager")
        # Derive the deterministic round identity for this player and request.
        round_id = round_id_for(self.game_id, player_id, request_id)
        # Serialize state cache, ledger proof, entropy, settlement, and persistence locally.
        with _SETTLEMENT_LOCK:
            # Load the player's current document once inside the lock.
            state = self._state_loader(player_id)
            # Resolve any prior round created by this exact request.
            existing = self._find_round(state, request_id)
            # Handle a replay of a previously settled round.
            if existing is not None:
                # Reject a request id reused with different wager content.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail closed rather than settling two outcomes under one identity.
                    raise ConflictError(f"{self.game_id} request_id conflicts with a prior round")
                # Rebuild the ledger events for the replayed round from committed proof.
                ledger_events = self._round_ledger(player_id, existing)
                # Return the identical replayed round with explicit replay evidence.
                return {"round": existing["public"], "replayed": True, "ledger": ledger_events, **self.state(player_id)}
            # Draw tentative server entropy that becomes authoritative only if this request writes the wager proof.
            tentative_entropy = self._entropy(self._entropy_source)
            # Capture one tentative settlement timestamp alongside the entropy for exact crash-recovery replay.
            tentative_settled_at = self._clock()
            # Build the audit details that commit the wager, entropy, and public timestamp for deterministic recovery.
            wager_details = {"request_id": request_id, "wager": wager, "entropy": tentative_entropy, "settled_at": tentative_settled_at}
            # Apply or recover the aggregate wager debit and retain its authoritative committed proof.
            wager_event, wager_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=-wager_total, transaction_type=self.wager_transaction_type, round_id=round_id, action_key=self._action_key(round_id, "wager"), request_fingerprint=fingerprint, details=wager_details)
            # Read only the committed proof because a retry's tentative entropy must never replace the first draw.
            committed_wager_details = wager_event.get("details") or {}
            # Recover the exact normalized wager recorded with the debit.
            committed_wager = committed_wager_details.get("wager")
            # Recover the exact entropy recorded before the first debit.
            entropy = committed_wager_details.get("entropy")
            # Recover the exact public timestamp recorded before the first debit.
            settled_at = committed_wager_details.get("settled_at")
            # Fail closed if a malformed proof cannot reconstruct the identical authoritative round.
            if committed_wager != wager or entropy is None or not isinstance(settled_at, str) or not settled_at:
                # Reject incomplete or inconsistent proof rather than redrawing or fabricating settlement state.
                raise ConflictError(f"{self.game_id} committed wager proof is incomplete")
            # Resolve the deterministic outcome from the committed wager and committed entropy.
            settlement = self._resolve(committed_wager, entropy)
            # Read the total return the resolver computed.
            total_return = round(float(settlement.get("total_return", 0)), 2)
            # Apply the aggregate settlement credit exactly once when the round returned value.
            if total_return > 0:
                # Build the settlement audit details from the committed round.
                settlement_details = {"request_id": request_id, "entropy": entropy, "total_return": total_return, "outcome": settlement.get("outcome")}
                # Commit the single aggregate credit exactly once.
                self._ledger_gateway.apply_once(player_id=player_id, amount=total_return, transaction_type=self.settlement_transaction_type, round_id=round_id, action_key=self._action_key(round_id, "settlement"), request_fingerprint=fingerprint, details=settlement_details)
            # Build the public round record retained in compact player state.
            public_round = {"round_id": round_id, "wager": committed_wager, "wager_total": wager_total, "entropy": entropy, "total_return": total_return, "outcome": settlement.get("outcome"), "detail": settlement.get("detail", {}), "net": round(total_return - wager_total, 2), "settled_at": settled_at}
            # Build the compact stored round with replay and fingerprint bookkeeping.
            stored_round = {"request_id": request_id, "request_fingerprint": fingerprint, "round_id": round_id, "total_return": total_return, "public": public_round}
            # Prepend the new round and bound the retained history.
            state["recent_rounds"] = ([stored_round] + state.get("recent_rounds", []))[:RECENT_ROUND_LIMIT]
            # Persist only this player's document.
            self._state_saver(player_id, state)
            # Rebuild the freshly committed ledger events for the response.
            ledger_events = self._round_ledger(player_id, stored_round)
            # Return the settled round, its ledger proof, and the refreshed public state.
            return {"round": public_round, "replayed": wager_replayed, "ledger": ledger_events, **self.state(player_id)}

    # Rebuild the committed ledger events for one round from stored proof.
    def _round_ledger(self, player_id: str, stored_round: dict) -> dict:
        # Resolve the round identity and fingerprint once.
        round_id = stored_round["round_id"]
        fingerprint = stored_round["request_fingerprint"]
        # Find the committed wager debit for this round.
        wager_event = self._ledger_gateway.find(player_id=player_id, round_id=round_id, transaction_type=self.wager_transaction_type, action_key=self._action_key(round_id, "wager"), request_fingerprint=fingerprint)
        # Start with no settlement proof for a losing round.
        settlement_event = None
        # Find a credit proof only when the round returned value.
        if stored_round.get("total_return", 0) > 0:
            # Resolve the committed settlement credit for this round.
            settlement_event = self._ledger_gateway.find(player_id=player_id, round_id=round_id, transaction_type=self.settlement_transaction_type, action_key=self._action_key(round_id, "settlement"), request_fingerprint=fingerprint)
        # Return both committed events under stable keys.
        return {"wager": wager_event, "settlement": settlement_event}
