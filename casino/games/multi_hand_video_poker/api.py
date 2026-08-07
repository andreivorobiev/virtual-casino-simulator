"""Session-compatible, ledger-only API adapter for issue #94."""

# Import regular-expression validation for bounded client retry identifiers.
import re
# Import a process-local settlement lock for exactly-once local simulator actions.
import threading

# Import shared ledger, player, and clock services without mutating balances directly.
from casino.core import players
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the shared id generator for ledger-correlated round identifiers.
from casino.core.ids import new_id
# Import player-scoped state helpers so authenticated users never share active rounds.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import the canonical player-id validator used by current and future router paths.
from casino.core.validation import require_player_id
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic engine through the allowed module boundary.
from casino.games.multi_hand_video_poker import engine

# Use one game id consistently for state documents and ledger events.
GAME_ID = engine.GAME_ID
# Bound client retry keys to conservative URL-safe identifier characters.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize state and ledger replay checks inside this local simulator process.
_SETTLEMENT_LOCK = threading.RLock()


# Resolve the player identity already bound by current main or the #81 shared resolver.
def request_player_id(body: dict, query: dict) -> str:
    # Prefer query because current main replaces it from bound_player_id before dispatch.
    player_id = query.get("player_id") or body.get("player_id") or "human"
    # Validate the resolved value without accepting an empty identity.
    return require_player_id({"player_id": player_id})


# Validate the required idempotency key used for wager retry recovery.
def require_request_id(value) -> str:
    # Require a bounded string whose characters remain safe in logs and JSON state.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the validated key unchanged for exact replay matching.
    return value


# Coordinate game state with ledger-only settlement through injectable dependencies.
class MultiHandVideoPokerService:
    # Store production dependencies while allowing isolated tests to use in-memory adapters.
    def __init__(self, *, load_state=load_player_game_state, save_state=save_player_game_state, debit=None, credit=None, read_ledger=None, get_player=players.get_player, clock=utc_now, id_factory=new_id, seed_factory=None):
        # Store the state loader used for player-scoped documents.
        self._load_state = load_state
        # Store the state writer used for crash-recovery markers.
        self._save_state = save_state
        # Store the only allowed wager debit operation.
        settlement = GameSettlementGateway(GAME_ID, debit=debit, credit=credit, read_recent=read_ledger)
        self._debit = settlement.debit
        # Store the only allowed payout credit operation.
        self._credit = settlement.credit
        # Store ledger history lookup for crash-safe replay detection.
        self._read_ledger = settlement.read_recent
        # Store player reads for response payloads without balance mutation.
        self._get_player = get_player
        # Store the clock hook for deterministic focused tests.
        self._clock = clock
        # Store the round-id hook for deterministic focused tests.
        self._id_factory = id_factory
        # Store an optional seed factory that production catalog registration leaves disabled.
        self._seed_factory = seed_factory

    # Load one authenticated player's isolated game state.
    def _load(self, player_id: str) -> dict:
        # Delegate through the standard player-game state storage abstraction.
        return self._load_state(GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's crash-recovery state.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate through the standard player-game state storage abstraction.
        self._save_state(GAME_ID, player_id, state)

    # Find a prior ledger event that proves an exactly-once movement already occurred.
    def _ledger_event(self, player_id: str, round_id: str, transaction_type: str):
        # Read a bounded recent window sufficient for the game's bounded round history.
        events = self._read_ledger(player_id, 500)
        # Match all three ownership fields so another game or player cannot satisfy replay.
        return next((event for event in events if event.get("game") == GAME_ID and event.get("round_id") == round_id and event.get("transaction_type") == transaction_type), None)

    # Ensure the round's aggregate wager has exactly one ledger debit.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict):
        # Look for a committed debit before issuing a potentially repeated movement.
        event = self._ledger_event(player_id, round_state["round_id"], "MHVP_WAGER_DEBIT")
        # Create the aggregate debit only when no committed ledger proof exists.
        if event is None:
            # Debit once for all selected hands and include complete audit dimensions.
            event = self._debit(player_id, round_state["total_wager"], "MHVP_WAGER_DEBIT", GAME_ID, round_state["round_id"], {"request_id": round_state["request_id"], "hand_count": round_state["hand_count"], "wager_per_hand": round_state["wager_per_hand"]})
        # Mark state only after a ledger event exists or has been recovered.
        round_state["wager_status"] = "complete"
        # Store the immutable ledger id for diagnostics and API evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal retries avoid even the recovery scan.
        self._save(player_id, state)
        # Return the committed or recovered ledger event.
        return event

    # Ensure the round's aggregate returned credits have at most one ledger credit.
    def _ensure_payout(self, player_id: str, state: dict, round_state: dict):
        # Skip ledger writes for zero payouts because shared ledger rows cannot be zero.
        if not round_state.get("total_payout"):
            # Mark the zero-credit settlement complete in state.
            round_state["payout_status"] = "complete"
            # Persist the terminal marker for reload-safe responses.
            self._save(player_id, state)
            # Return no event because no play-token movement occurred.
            return None
        # Look for a committed credit before issuing a potentially repeated movement.
        event = self._ledger_event(player_id, round_state["round_id"], "MHVP_PAYOUT_CREDIT")
        # Create the aggregate payout credit only when no committed ledger proof exists.
        if event is None:
            # Credit all qualifying hands in one auditable ledger event.
            event = self._credit(player_id, round_state["total_payout"], "MHVP_PAYOUT_CREDIT", GAME_ID, round_state["round_id"], {"hand_count": round_state["hand_count"], "wager_per_hand": round_state["wager_per_hand"], "outcome": round_state["outcome"], "results": [{"hand_index": result["hand_index"], "outcome": result["outcome"], "payout": result["payout"]} for result in round_state["results"]]})
        # Mark state only after a ledger event exists or has been recovered.
        round_state["payout_status"] = "complete"
        # Store the immutable ledger id for diagnostics and API evidence.
        round_state["payout_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal retries avoid even the recovery scan.
        self._save(player_id, state)
        # Return the committed or recovered ledger event.
        return event

    # Build the public state/player payload shared by every game route.
    def payload(self, player_id: str, state=None) -> dict:
        # Load state only when the caller has not already mutated an in-memory copy.
        current = state if state is not None else self._load(player_id)
        # Return sanitized game state and a read-only current-player snapshot.
        return {"game": GAME_ID, "state": engine.public_state(current), "player": self._get_player(player_id), "hand_counts": list(engine.HAND_COUNTS), "paytable": dict(engine.PAYTABLE)}

    # Start or replay one idempotent wagered round.
    def start_round(self, player_id: str, body: dict) -> dict:
        # Validate the client retry key before touching state or the ledger.
        request_id = require_request_id(body.get("request_id"))
        # Serialize the state-save, ledger-check, debit, and recovery markers.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Recover an earlier request before enforcing the one-active-round rule.
            existing = engine.round_for_request(state, request_id)
            # Return the same round and ensure any crash-interrupted wager when replayed.
            if existing is not None:
                # Ensure only active or settled requests with the same parameters are replayed.
                if existing["hand_count"] != engine.require_hand_count(body.get("hand_count")) or existing["wager_per_hand"] != engine.require_wager_per_hand(body.get("wager_per_hand")):
                    # Reject reuse of one idempotency key for different money movement.
                    raise ConflictError("request_id was already used with different round settings")
                # Recover a missing wager marker through ledger proof or one debit.
                wager_event = self._ensure_wager(player_id, state, existing)
                # Return the replayed round without creating a second round or debit.
                return {"round": engine.public_round(existing), "wager": wager_event, "replayed": True, **self.payload(player_id, state)}
            # Prevent a second wager while the current common hand awaits a draw.
            if state.get("active_round") is not None:
                # Require the player to finish the current round first.
                raise ConflictError("Finish the active round before dealing again")
            # Derive a deterministic test seed only through an injected non-production hook.
            seed = self._seed_factory(request_id) if self._seed_factory else None
            # Create the reload-safe round before issuing its aggregate ledger debit.
            round_state = engine.create_round(player_id, body.get("hand_count"), body.get("wager_per_hand"), request_id, seed=seed, round_id=self._id_factory("mhvp"), created_at=self._clock())
            # Store the pending round so a crash after debit can recover by round id.
            state["active_round"] = round_state
            # Persist the pending marker before any play-token movement.
            self._save(player_id, state)
            # Start protected debit handling so rejected wagers do not trap an empty round.
            try:
                # Ensure the aggregate wager through the exactly-once ledger guard.
                wager_event = self._ensure_wager(player_id, state, round_state)
            # Remove a non-debited pending round when the ledger rejects the wager.
            except Exception:
                # Clear the active slot only when no committed debit can be found.
                if self._ledger_event(player_id, round_state["round_id"], "MHVP_WAGER_DEBIT") is None:
                    # Remove the safe-to-retry pending state.
                    state["active_round"] = None
                    # Persist cleanup before propagating the original failure.
                    self._save(player_id, state)
                # Re-raise the original ledger or storage error.
                raise
            # Return the new common hand and committed wager evidence.
            return {"round": engine.public_round(round_state), "wager": wager_event, "replayed": False, **self.payload(player_id, state)}

    # Persist hold positions for reload-safe continuation.
    def set_holds(self, player_id: str, round_id: str, holds) -> dict:
        # Serialize hold changes against concurrent draws.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Read the only actionable round from the active slot.
            round_state = state.get("active_round")
            # Reject missing or stale round identifiers.
            if not round_state or round_state.get("round_id") != round_id:
                # Keep cross-player and unknown-round behavior indistinguishable.
                raise NotFoundError("Active video poker round was not found")
            # Validate and persist the shared hold positions through the engine.
            engine.set_holds(round_state, holds)
            # Save the selection before returning so reload preserves it.
            self._save(player_id, state)
            # Return the updated public common hand.
            return {"round": engine.public_round(round_state), **self.payload(player_id, state)}

    # Draw every hand and settle one aggregate payout exactly once.
    def draw(self, player_id: str, round_id: str) -> dict:
        # Serialize deterministic draw, pre-credit state, ledger check, and completion marker.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Find active or recent state so a repeated draw can recover settlement.
            round_state = engine.round_by_id(state, round_id)
            # Reject unknown identifiers without exposing another player's state.
            if round_state is None:
                # Return a stable lookup error for cross-session safety.
                raise NotFoundError("Video poker round was not found")
            # Record whether cards were already complete before this request began.
            replayed = round_state.get("phase") == "settled"
            # Complete cards only when this is the active hold-phase round.
            if round_state.get("phase") == "hold":
                # Read the active slot defensively before checking its identifier.
                active_round = state.get("active_round")
                # Reject drawing a historical hold-shaped record after state corruption.
                if not active_round or active_round.get("round_id") != round_id:
                    # Prevent an archived record from becoming actionable again.
                    raise ConflictError("Only the active round can be drawn")
                # Compute all final hands exactly once from persisted replacement pools.
                engine.draw(round_state, completed_at=self._clock())
                # Archive the completed result before issuing any payout credit.
                engine.archive_round(state, round_state)
                # Persist results first so a crash can resume credit by round id.
                self._save(player_id, state)
            # Reject unknown states rather than guessing a settlement action.
            elif round_state.get("phase") != "settled":
                # Explain the stale action as a state conflict.
                raise ConflictError("This round cannot be settled in its current phase")
            # Ensure the aggregate payout through the ledger recovery guard.
            payout_event = self._ensure_payout(player_id, state, round_state)
            # Return the completed hands and optional committed payout event.
            return {"round": engine.public_round(round_state), "payout": payout_event, "replayed": replayed, **self.payload(player_id, state)}


# Register the isolated routes for catalog discovery or direct focused tests.
def register(router, service=None, *, test_seed=None):
    # Create the production service unless an isolated test supplies its own dependencies.
    game_service = service or MultiHandVideoPokerService(seed_factory=(lambda request_id: f"{test_seed}:{request_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/multi-hand-video-poker/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query):
        # Resolve the router-bound player and return only that player's state.
        return game_service.payload(request_player_id(body, query))

    # Register the idempotent aggregate-wager deal endpoint.
    @router.post(r"/api/v1/games/multi-hand-video-poker/rounds")
    # Create or replay a round for the bound player.
    def rounds(body, query):
        # Resolve the router-bound player before any state or ledger access.
        return game_service.start_round(request_player_id(body, query), body)

    # Register reload-safe common hold selection.
    @router.post(r"/api/v1/games/multi-hand-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/holds")
    # Save shared hold positions for the bound player's active round.
    def holds(body, query, round_id):
        # Resolve the router-bound player before locating the round.
        return game_service.set_holds(request_player_id(body, query), round_id, body.get("holds"))

    # Register deterministic multi-hand draw and aggregate settlement.
    @router.post(r"/api/v1/games/multi-hand-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/draw")
    # Complete and settle the bound player's round.
    def draw(body, query, round_id):
        # Resolve the router-bound player before locating or settling the round.
        return game_service.draw(request_player_id(body, query), round_id)

    # Return the service so focused tests can inspect injected adapters.
    return game_service
