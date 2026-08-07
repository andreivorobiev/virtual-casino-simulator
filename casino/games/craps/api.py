"""Session-bound, ledger-only Craps API adapter for GitHub issue #90."""

# Import server-side entropy for authoritative production dice rolls.
import random
# Import deep-copy support for private durable ledger proof snapshots.
import copy
# Import regular-expression validation for bounded client retry identifiers.
import re
# Import a process-local settlement lock for exactly-once simulator actions.
import threading

# Import the read-only player service without a game-owned mutation boundary.
from casino.core import players
# Import the shared clock for persisted round and roll timestamps.
from casino.core.clock import utc_now
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import the shared id generator for ledger-correlated round identifiers.
from casino.core.ids import new_id
# Import player-scoped state helpers for authenticated reload isolation.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import the canonical player-id validator used after router resolution.
from casino.core.validation import require_player_id
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's pure engine through the allowed module boundary.
from casino.games.craps import engine

# Use one game id consistently for state documents and ledger events.
GAME_ID = engine.GAME_ID
# Bound client retry keys to conservative URL-safe identifier characters.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize state, dice, ledger replay, and recovery checks inside this process.
_SETTLEMENT_LOCK = threading.RLock()
# Use operating-system-backed randomness for production-only dice generation.
_SYSTEM_RANDOM = random.SystemRandom()


# Roll one authoritative ordered pair while tests inject deterministic results.
def roll_two_dice() -> list[int]:
    # Generate two independent one-based six-sided faces on the backend.
    return [_SYSTEM_RANDOM.randint(1, 6), _SYSTEM_RANDOM.randint(1, 6)]


# Resolve the player identity already bound by the shared router.
def request_player_id(body: dict, query: dict) -> str:
    # Prefer query because the router replaces it from bound_player_id before dispatch.
    player_id = query.get("player_id") or body.get("player_id") or "human"
    # Validate the resolved value without accepting an empty identity.
    return require_player_id({"player_id": player_id})


# Validate a required idempotency key used for starts and every roll.
def require_request_id(value) -> str:
    # Require a bounded string whose characters remain safe in state and logs.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the validated key unchanged for exact replay matching.
    return value


# Coordinate game state with ledger-only settlement through injectable dependencies.
class CrapsService:
    # Store production dependencies while isolated tests use in-memory adapters.
    def __init__(self, *, load_state=load_player_game_state, save_state=save_player_game_state, debit=None, credit=None, read_ledger=None, get_player=players.get_player, clock=utc_now, id_factory=new_id, roller=roll_two_dice):
        # Store the state loader used for player-scoped documents.
        self._load_state = load_state
        # Store the state writer used for crash-recovery markers.
        self._save_state = save_state
        # Bind production and injected test seams behind the canonical settlement adapter.
        settlement = GameSettlementGateway(GAME_ID, "idempotency_key", debit=debit, credit=credit, read_recent=read_ledger)
        # Preserve the historical callback shape while routing through the shared adapter.
        self._debit = settlement.debit
        # Preserve the historical credit shape while routing through the shared adapter.
        self._credit = settlement.credit
        # Preserve bounded proof reads through the adapter-owned ledger seam.
        self._read_ledger = settlement.read_recent
        # Store player reads for response payloads without balance mutation.
        self._get_player = get_player
        # Store the clock hook for repeatable focused tests.
        self._clock = clock
        # Store the round-id hook for repeatable focused tests.
        self._id_factory = id_factory
        # Store the authoritative dice hook for deterministic test sequences.
        self._roller = roller

    # Load one authenticated player's isolated game state.
    def _load(self, player_id: str) -> dict:
        # Delegate through the standard player-game state storage abstraction.
        return self._load_state(GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's crash-recovery state.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate through the standard player-game state storage abstraction.
        self._save_state(GAME_ID, player_id, state)

    # Read complete same-player ledger history without a fixed recovery horizon.
    def _read_complete_ledger(self, player_id: str) -> list[dict]:
        # Begin with the ordinary recovery window while the JSON provider's tail cache prevents file re-parsing. (issue #412)
        limit = 500
        # Widen until the provider proves the returned window covers complete player history.
        while True:
            # Read the newest candidate window through the shared ledger API.
            events = self._read_ledger(player_id, limit)
            # Fail closed if a storage adapter violates the list contract.
            if not isinstance(events, list):
                # Avoid issuing money movement over unreadable recovery history.
                raise ConflictError("Craps ledger recovery history is malformed")
            # Return only after the window covers the complete player history.
            if len(events) < limit:
                # Return the full chronological proof collection.
                return events
            # Double without a fixed ceiling so old exactly-once evidence can never age out.
            limit *= 2

    # Find a unique prior ledger event by its deterministic game action key.
    def _ledger_event(self, player_id: str, round_id: str, idempotency_key: str):
        # Read complete history only for pending or legacy proof recovery.
        events = self._read_complete_ledger(player_id)
        # Match player-filtered events by game, round, and deterministic action key.
        matches = [event for event in events if event.get("game") == GAME_ID and event.get("round_id") == round_id and isinstance(event.get("details"), dict) and event["details"].get("idempotency_key") == idempotency_key]
        # Fail closed if shared storage already contains duplicate settlement proof.
        if len(matches) > 1:
            # Refuse to guess which duplicate movement is authoritative.
            raise ConflictError("Craps ledger contains duplicate action evidence")
        # Return the sole committed proof or no event when movement is still needed.
        return matches[0] if matches else None

    # Verify recovered ledger proof matches the expected amount and action details.
    def _verify_ledger_event(self, event: dict, player_id: str, round_id: str, expected_transaction_type: str, expected_amount: float, expected_details: dict) -> None:
        # Require a concrete event mapping before reading proof fields.
        if not isinstance(event, dict):
            # Refuse to trust malformed private or provider evidence.
            raise ConflictError("Craps ledger replay evidence is malformed")
        # Verify cached or scanned proof belongs to the authenticated player.
        if event.get("player_id") != player_id:
            # Prevent one player's cached event from satisfying another wallet.
            raise ConflictError("Craps ledger replay player conflicts with game state")
        # Verify game and round ownership independently of the action fingerprint.
        if event.get("game") != GAME_ID or event.get("round_id") != round_id:
            # Prevent unrelated event proof from authorizing this round.
            raise ConflictError("Craps ledger replay ownership conflicts with game state")
        # Reject transaction-type drift for an already-owned idempotency key.
        if event.get("transaction_type") != expected_transaction_type:
            # Prevent a second settlement under a different ledger row type.
            raise ConflictError("Craps ledger replay type conflicts with game state")
        # Translate malformed persisted amounts into a safe replay conflict.
        try:
            # Normalize the stored signed amount to shared ledger precision.
            actual_amount = round(float(event.get("amount")), 2)
        # Fail closed when persisted evidence cannot be interpreted.
        except (TypeError, ValueError, OverflowError):
            # Do not issue a second movement over malformed prior evidence.
            raise ConflictError("Craps ledger replay evidence is malformed")
        # Reject a reused proof whose signed amount differs from game state.
        if actual_amount != round(float(expected_amount), 2):
            # Prevent a conflicting retry from inheriting another movement.
            raise ConflictError("Craps ledger replay amount conflicts with game state")
        # Normalize absent or malformed detail payloads before exact comparisons.
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        # Compare each money-relevant field expected from the committed action.
        for key, value in expected_details.items():
            # Reject an event whose action fingerprint differs from persisted state.
            if details.get(key) != value:
                # Prevent silent recovery from unrelated or corrupted evidence.
                raise ConflictError("Craps ledger replay details conflict with game state")

    # Ensure a round has exactly one aggregate wager debit in this process model.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict):
        # Derive a deterministic action key independent of ledger transaction type.
        idempotency_key = f"{round_state['round_id']}:wager"
        # Define the exact audit fingerprint stored with the debit.
        details = {"idempotency_key": idempotency_key, "request_id": round_state["start_request_id"], "bet_type": round_state["bet_type"], "wager": round_state["wager"]}
        # Record whether state already claims the movement completed.
        completed = round_state.get("wager_status") == "complete"
        # Prefer private durable proof so completed retries require no ledger scan.
        cached = round_state.get("_wager_event")
        # Copy valid cached proof before verification or API return.
        event = copy.deepcopy(cached) if isinstance(cached, dict) else None
        # Scan complete history only for pending crash recovery or legacy state.
        if event is None:
            # Recover a committed debit by its deterministic action key.
            event = self._ledger_event(player_id, round_state["round_id"], idempotency_key)
        # Never reissue when a completed marker has lost its durable proof.
        if event is None and completed:
            # Fail closed rather than turning state corruption into a second debit.
            raise ConflictError("Completed Craps wager proof is unavailable")
        # Create the aggregate debit only when no committed ledger proof exists.
        if event is None:
            # Debit the line wager once with complete audit dimensions.
            event = self._debit(player_id, round_state["wager"], "CRAPS_WAGER_DEBIT", GAME_ID, round_state["round_id"], details)
        # Verify both recovered and newly returned events against persisted state.
        self._verify_ledger_event(event, player_id, round_state["round_id"], "CRAPS_WAGER_DEBIT", -round_state["wager"], details)
        # Reject disagreement between an existing completed marker and proof id.
        if completed and round_state.get("wager_ledger_id") not in (None, event.get("ledger_id")):
            # Prevent a replaced proof snapshot from satisfying completed state.
            raise ConflictError("Craps wager ledger id conflicts with game state")
        # Cache the full verified event inside private durable round state.
        round_state["_wager_event"] = copy.deepcopy(event)
        # Mark state only after a valid ledger event exists or was recovered.
        round_state["wager_status"] = "complete"
        # Store the immutable ledger id for diagnostics and API evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the marker so ordinary retries avoid recovery uncertainty.
        self._save(player_id, state)
        # Return the committed or recovered ledger event.
        return event

    # Ensure a terminal round has at most one payout or push-refund credit.
    def _ensure_settlement(self, player_id: str, state: dict, round_state: dict):
        # Require a terminal result before considering any returned credit.
        if round_state.get("phase") != "settled":
            # Reject premature settlement without touching the ledger.
            raise ConflictError("Craps settlement is not ready")
        # Derive the only allowed settlement transaction type from pure rules.
        transaction_type = engine.settlement_transaction_type(round_state)
        # Derive the exact returned play-token amount from the terminal outcome.
        amount = engine.settlement_amount(round_state)
        # Complete losses without creating forbidden zero-value ledger rows.
        if transaction_type is None:
            # Mark the terminal no-credit settlement complete.
            round_state["settlement_status"] = "complete"
            # Persist the loss marker for reload-safe replay.
            self._save(player_id, state)
            # Return no event because no balance movement occurred.
            return None
        # Read the terminal roll that owns this settlement action.
        terminal_roll = round_state["rolls"][-1]
        # Derive one settlement key shared by payout and push-refund outcomes.
        idempotency_key = f"{round_state['round_id']}:settlement"
        # Define the exact settlement fingerprint used for recovery validation.
        details = {"idempotency_key": idempotency_key, "request_id": terminal_roll["request_id"], "start_request_id": round_state["start_request_id"], "bet_type": round_state["bet_type"], "wager": round_state["wager"], "outcome": round_state["outcome"], "dice": list(terminal_roll["dice"]), "point": round_state["point"]}
        # Record whether state already claims the returned credit completed.
        completed = round_state.get("settlement_status") == "complete"
        # Prefer private durable proof so completed retries require no ledger scan.
        cached = round_state.get("_settlement_event")
        # Copy valid cached proof before verification or API return.
        event = copy.deepcopy(cached) if isinstance(cached, dict) else None
        # Scan complete history only for pending crash recovery or legacy state.
        if event is None:
            # Recover a committed payout/refund by its deterministic action key.
            event = self._ledger_event(player_id, round_state["round_id"], idempotency_key)
        # Never reissue when a completed marker has lost its durable proof.
        if event is None and completed:
            # Fail closed rather than turning state corruption into a second credit.
            raise ConflictError("Completed Craps settlement proof is unavailable")
        # Create the returned credit only when no committed proof exists.
        if event is None:
            # Credit the payout or refund through the shared ledger service only.
            event = self._credit(player_id, amount, transaction_type, GAME_ID, round_state["round_id"], details)
        # Verify recovered or new settlement evidence against terminal state.
        self._verify_ledger_event(event, player_id, round_state["round_id"], transaction_type, amount, details)
        # Reject disagreement between an existing completed marker and proof id.
        if completed and round_state.get("settlement_ledger_id") not in (None, event.get("ledger_id")):
            # Prevent a replaced proof snapshot from satisfying completed state.
            raise ConflictError("Craps settlement ledger id conflicts with game state")
        # Cache the full verified event inside private durable round state.
        round_state["_settlement_event"] = copy.deepcopy(event)
        # Mark settlement complete only after valid ledger evidence exists.
        round_state["settlement_status"] = "complete"
        # Store the immutable settlement ledger id for diagnostics.
        round_state["settlement_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal action replay remains read-only.
        self._save(player_id, state)
        # Return the committed payout or refund event.
        return event

    # Recover every retained terminal settlement before another wager can start.
    def _recover_pending_settlements(self, player_id: str, state: dict) -> None:
        # Inspect active-first retained rounds through the engine's stable lookup order.
        for round_state in engine.rounds(state):
            # Ignore active play and terminal rounds already proven complete.
            if round_state.get("phase") != "settled" or round_state.get("settlement_status") == "complete":
                # Continue without adding side effects to healthy retained state.
                continue
            # Recover or commit the pending payout/refund before a new debit is allowed.
            self._ensure_settlement(player_id, state, round_state)

    # Build the public state/player payload shared by every route.
    def payload(self, player_id: str, state=None) -> dict:
        # Load state only when the caller has not already mutated a current copy.
        current = state if state is not None else self._load(player_id)
        # Return exact contract fields without exposing private service details.
        return {"game": GAME_ID, "state": engine.public_state(current), "player": self._get_player(player_id), "bet_types": list(engine.BET_TYPES)}

    # Start or replay one retry-safe line-wager round.
    def start_round(self, player_id: str, body: dict) -> dict:
        # Validate the client retry key before touching state or the ledger.
        request_id = require_request_id(body.get("request_id"))
        # Normalize money-relevant fields before conflict comparisons.
        bet_type = engine.require_bet_type(body.get("bet_type"))
        # Normalize the requested wager before conflict comparisons.
        wager = engine.require_wager(body.get("wager"))
        # Serialize state save, ledger check, debit, and recovery markers.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Recover retained terminal money before accepting another wager.
            self._recover_pending_settlements(player_id, state)
            # Find any retained action already using this global retry id.
            action = engine.action_for_request(state, request_id)
            # Replay only an exact start action and reject cross-action reuse.
            if action is not None:
                # Unpack the persisted action owner for safe comparisons.
                kind, existing, _ = action
                # Reject reuse of a roll id as a new money-bearing start.
                if kind != "start":
                    # Fail closed before any active-round or ledger work.
                    raise ConflictError("request_id was already used for a Craps roll")
                # Reject the same start id with changed money-relevant settings.
                if existing["bet_type"] != bet_type or existing["wager"] != wager:
                    # Prevent one idempotency key from authorizing another debit.
                    raise ConflictError("request_id was already used with different round settings")
                # Recover a missing wager marker through ledger proof or one debit.
                wager_event = self._ensure_wager(player_id, state, existing)
                # Return the exact retained round without creating another debit.
                return {"round": engine.public_round(existing), "replayed": True, "wager_event": wager_event, **self.payload(player_id, state)}
            # Prevent a second line wager while a round remains actionable.
            if state.get("active_round") is not None:
                # Require terminal settlement before another start.
                raise ConflictError("Finish the active Craps round before starting another")
            # Create reload-safe pending state before issuing any ledger debit.
            round_state = engine.create_round(player_id, bet_type, wager, request_id, round_id=self._id_factory("craps"), created_at=self._clock())
            # Store the pending round so interrupted marker writes can recover.
            state["active_round"] = round_state
            # Persist the pending state before any play-token movement.
            self._save(player_id, state)
            # Protect cleanup so rejected debits do not trap an empty round.
            try:
                # Ensure the aggregate wager through the replay guard.
                wager_event = self._ensure_wager(player_id, state, round_state)
            # Remove only a round proven not to have moved balance.
            except Exception:
                # Check ledger proof before deciding whether cleanup is safe.
                if self._ledger_event(player_id, round_state["round_id"], f"{round_state['round_id']}:wager") is None:
                    # Clear the pending round when no debit committed.
                    state["active_round"] = None
                    # Persist cleanup before propagating the original error.
                    self._save(player_id, state)
                # Re-raise the ledger, storage, or validation failure.
                raise
            # Return the new round and committed wager evidence.
            return {"round": engine.public_round(round_state), "replayed": False, "wager_event": wager_event, **self.payload(player_id, state)}

    # Roll or replay one per-action request inside an active round.
    def roll(self, player_id: str, round_id: str, body: dict) -> dict:
        # Validate the per-roll retry key before consuming dice or state.
        request_id = require_request_id(body.get("request_id"))
        # Serialize action lookup, dice generation, persistence, and settlement.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Find any retained start or roll already using this action id.
            action = engine.action_for_request(state, request_id)
            # Replay only the exact roll on the exact path round.
            if action is not None:
                # Unpack the action owner and stable roll record.
                kind, owning_round, existing_roll = action
                # Reject start-id reuse or cross-round roll-id reuse.
                if kind != "roll" or owning_round.get("round_id") != round_id:
                    # Fail closed before consuming another dice result.
                    raise ConflictError("request_id was already used for another Craps action")
                # Recover settlement when the repeated roll was terminal.
                settlement = self._ensure_settlement(player_id, state, owning_round) if owning_round.get("phase") == "settled" else None
                # Return the same roll and round without consuming the roller.
                return {"round": engine.public_round(owning_round), "roll": dict(existing_roll), "settlement": settlement, "replayed": True, **self.payload(player_id, state)}
            # Read the only actionable round for this authenticated player.
            round_state = state.get("active_round")
            # Reject unknown, historical, or cross-session round identifiers uniformly.
            if not round_state or round_state.get("round_id") != round_id:
                # Avoid exposing another player's round existence.
                raise NotFoundError("Active Craps round was not found")
            # Recover or commit a crash-interrupted start before consuming dice.
            if round_state.get("wager_status") != "complete":
                # Ensure no pending-state-only round can roll or receive a free payout.
                self._ensure_wager(player_id, state, round_state)
            # Generate one authoritative pair only after every retry check passes.
            dice = self._roller()
            # Apply the pure rules with an injected timestamp and validated dice.
            roll = engine.apply_roll(round_state, dice, request_id, created_at=self._clock())
            # Archive terminal state before any returned credit is attempted.
            if round_state.get("phase") == "settled":
                # Move the terminal round into bounded retry-visible history.
                engine.archive_round(state, round_state)
            # Persist dice, point transition, and terminal outcome before settlement.
            self._save(player_id, state)
            # Recover or create the payout/refund only after terminal state is durable.
            settlement = self._ensure_settlement(player_id, state, round_state) if round_state.get("phase") == "settled" else None
            # Return the authoritative action plus current reload-safe state.
            return {"round": engine.public_round(round_state), "roll": dict(roll), "settlement": settlement, "replayed": False, **self.payload(player_id, state)}


# Register isolated Craps routes for catalog discovery or focused direct tests.
def register(router, service=None):
    # Create the production service unless a focused test supplies dependencies.
    game_service = service or CrapsService()

    # Register the authenticated player's reload-safe Craps state endpoint.
    @router.get(r"/api/v1/games/craps/state")
    # Return state for the identity already replaced by the shared router.
    def state(body, query):
        # Resolve the router-bound player before reading game state.
        return game_service.payload(request_player_id(body, query))

    # Register the idempotent line-wager round start endpoint.
    @router.post(r"/api/v1/games/craps/rounds")
    # Create or replay one round for the bound player.
    def rounds(body, query):
        # Resolve the router-bound player before state or ledger access.
        return game_service.start_round(request_player_id(body, query), body)

    # Register the per-action authoritative roll and settlement endpoint.
    @router.post(r"/api/v1/games/craps/rounds/(?P<round_id>[A-Za-z0-9_-]+)/rolls")
    # Roll or replay one action for the bound player's round.
    def rolls(body, query, round_id):
        # Resolve the router-bound player before locating or settling the round.
        return game_service.roll(request_player_id(body, query), round_id, body)

    # Return the service so focused tests can inspect injected adapters.
    return game_service
