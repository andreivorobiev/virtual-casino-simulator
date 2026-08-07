"""Session-bound, retry-safe ledger adapter for Jacks-or-Better issue #91.

Confirmed requirements: LEDGER-005, LEDGER-006, LEDGER-007, and SESSION-005.
Proposed local traceability prefix: JOBVP (pending central allocation by #77).
"""

# Import regular-expression validation for bounded client action identifiers.
import re
# Import a process-local settlement lock for exactly-once local simulator actions.
import threading

# Import shared ledger and player services without mutating balances directly.
from casino.core import players
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the shared id generator for ledger-correlated round identifiers.
from casino.core.ids import new_id
# Import player-scoped state helpers so authenticated users never share active rounds.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import the canonical player-id validator used after shared router resolution.
from casino.core.validation import require_player_id
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic engine through the allowed module boundary.
from casino.games.jacks_or_better_video_poker import engine

# Use one game id consistently for state documents and ledger events.
GAME_ID = engine.GAME_ID
# Name the single wager movement for replay-safe ledger correlation.
WAGER_TRANSACTION_TYPE = "JOBVP_WAGER_DEBIT"
# Name the single returned-credit movement for replay-safe ledger correlation.
PAYOUT_TRANSACTION_TYPE = "JOBVP_PAYOUT_CREDIT"
# Bound client retry keys to conservative URL-safe identifier characters.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize state and ledger replay checks inside this local simulator process.
_SETTLEMENT_LOCK = threading.RLock()


# Resolve the player identity already replaced by the shared authenticated router.
def request_player_id(body: dict, query: dict) -> str:
    # Prefer query because current main replaces it from bound_player_id before dispatch.
    player_id = query.get("player_id") or body.get("player_id") or "human"
    # Validate the resolved value without accepting an empty identity.
    return require_player_id({"player_id": player_id})


# Validate one required idempotency key used for deal or draw retry recovery.
def require_action_id(value, field_name: str) -> str:
    # Require a bounded string whose characters remain safe in logs and JSON state.
    if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError(f"{field_name} must be 1-128 URL-safe characters")
    # Return the validated key unchanged for exact replay matching.
    return value


# Coordinate game state with ledger-only settlement through injectable dependencies.
class JacksOrBetterVideoPokerService:
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
        # Store an optional seed factory that production registration leaves disabled.
        self._seed_factory = seed_factory

    # Load one authenticated player's isolated game state.
    def _load(self, player_id: str) -> dict:
        # Delegate through the standard player-game state storage abstraction.
        return self._load_state(GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's crash-recovery state.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate through the standard player-game state storage abstraction.
        self._save_state(GAME_ID, player_id, state)

    # Find prior ledger proof that one round movement already committed.
    def _ledger_event(self, player_id: str, round_id: str, transaction_type: str):
        # Read a bounded recent window sufficient for the game's bounded round history.
        events = self._read_ledger(player_id, 500)
        # Match player, game, round, and movement type so no foreign event can satisfy replay.
        return next((event for event in events if event.get("player_id") == player_id and event.get("game") == GAME_ID and event.get("round_id") == round_id and event.get("transaction_type") == transaction_type), None)

    # Ensure the round's coin wager has exactly one ledger debit.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict):
        # Look for a committed debit before issuing a potentially repeated movement.
        event = self._ledger_event(player_id, round_state["round_id"], WAGER_TRANSACTION_TYPE)
        # Create the debit only when no committed ledger proof exists.
        if event is None:
            # Debit coin value times coin count with complete action audit dimensions.
            event = self._debit(player_id, round_state["total_wager"], WAGER_TRANSACTION_TYPE, GAME_ID, round_state["round_id"], {"deal_action_id": round_state["deal_action_id"], "coin_value": round_state["coin_value"], "coins": round_state["coins"]})
        # Mark state only after a ledger event exists or has been recovered.
        round_state["wager_status"] = "complete"
        # Store the immutable ledger id for diagnostics and API evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the marker so normal retries avoid even the recovery scan.
        self._save(player_id, state)
        # Return the committed or recovered ledger event.
        return event

    # Ensure the round's returned credits have at most one ledger credit.
    def _ensure_payout(self, player_id: str, state: dict, round_state: dict):
        # Skip ledger writes for zero payouts because shared ledger rows cannot be zero.
        if not round_state.get("total_payout"):
            # Mark the zero-credit settlement complete in state.
            round_state["payout_status"] = "complete"
            # Persist the terminal marker for reload-safe responses.
            self._save(player_id, state)
            # Return no event because no fake-token movement occurred.
            return None
        # Look for a committed credit before issuing a potentially repeated movement.
        event = self._ledger_event(player_id, round_state["round_id"], PAYOUT_TRANSACTION_TYPE)
        # Create the returned-credit movement only when no committed ledger proof exists.
        if event is None:
            # Credit the complete 9/6 paytable return in one auditable ledger event.
            event = self._credit(player_id, round_state["total_payout"], PAYOUT_TRANSACTION_TYPE, GAME_ID, round_state["round_id"], {"action_id": round_state["draw_action_id"], "coin_value": round_state["coin_value"], "coins": round_state["coins"], "outcome": round_state["outcome"], "payout_credits": round_state["payout_credits"]})
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
        # Convert immutable paytable tuples to explicit JSON-friendly credit columns.
        paytable = {outcome: list(credits) for outcome, credits in engine.PAYTABLE.items()}
        # Return sanitized state, a read-only player snapshot, and authoritative game choices.
        return {"game": GAME_ID, "state": engine.public_state(current), "player": self._get_player(player_id), "coin_choices": list(engine.COIN_CHOICES), "paytable": paytable}

    # Start or replay one idempotent coin-wagered round.
    def start_round(self, player_id: str, body: dict) -> dict:
        # Validate the generic client action key before storing it as deal ownership.
        deal_action_id = require_action_id(body.get("action_id"), "action_id")
        # Normalize money parameters once for conflict-safe replay comparison.
        coin_value = engine.require_coin_value(body.get("coin_value"))
        # Normalize the paytable column once for conflict-safe replay comparison.
        coins = engine.require_coins(body.get("coins"))
        # Serialize the state-save, ledger-check, debit, and recovery markers.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Recover an earlier deal action before enforcing the one-active-round rule.
            existing = engine.round_for_deal_action(state, deal_action_id)
            # Return the same round and ensure any crash-interrupted wager when replayed.
            if existing is not None:
                # Reject reuse of one deal key for different fake-token movement.
                if existing["coin_value"] != coin_value or existing["coins"] != coins:
                    # Fail closed instead of silently relabeling a committed wager.
                    raise ConflictError("action_id was already used with different wager settings")
                # Recover a missing wager marker through ledger proof or one debit.
                wager_event = self._ensure_wager(player_id, state, existing)
                # Return the replayed round without creating a second round or debit.
                return {"round": engine.public_round(existing), "wager": wager_event, "replayed": True, **self.payload(player_id, state)}
            # Prevent a second wager while the current hand awaits a draw.
            if state.get("active_round") is not None:
                # Require the player to finish the current round first.
                raise ConflictError("Finish the active round before dealing again")
            # Derive a deterministic test seed only through an injected non-production hook.
            seed = self._seed_factory(deal_action_id) if self._seed_factory else None
            # Create the reload-safe round before issuing its ledger debit.
            round_state = engine.create_round(player_id, coin_value, coins, deal_action_id, seed=seed, round_id=self._id_factory("jobvp"), created_at=self._clock())
            # Store the pending round so a crash after debit can recover by round id.
            state["active_round"] = round_state
            # Persist the pending marker before any fake-token movement.
            self._save(player_id, state)
            # Start protected debit handling so rejected wagers do not trap an empty round.
            try:
                # Ensure the coin wager through the exactly-once ledger guard.
                wager_event = self._ensure_wager(player_id, state, round_state)
            # Remove a non-debited pending round when the ledger rejects the wager.
            except Exception:
                # Clear the active slot only when no committed debit can be found.
                if self._ledger_event(player_id, round_state["round_id"], WAGER_TRANSACTION_TYPE) is None:
                    # Remove the safe-to-retry pending state.
                    state["active_round"] = None
                    # Persist cleanup before propagating the original failure.
                    self._save(player_id, state)
                # Re-raise the original ledger or storage error.
                raise
            # Return the new hand and committed wager evidence.
            return {"round": engine.public_round(round_state), "wager": wager_event, "replayed": False, **self.payload(player_id, state)}

    # Persist held-card positions for reload-safe continuation.
    def set_holds(self, player_id: str, round_id: str, holds) -> dict:
        # Serialize hold changes against concurrent draws.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Read the only actionable round from the active slot.
            round_state = state.get("active_round")
            # Reject missing, stale, or cross-player round identifiers alike.
            if not round_state or round_state.get("round_id") != round_id:
                # Keep cross-session and unknown-round behavior indistinguishable.
                raise NotFoundError("Active Jacks-or-Better round was not found")
            # Validate and persist held positions through the deterministic engine.
            engine.set_holds(round_state, holds)
            # Save the selection before returning so reload preserves it.
            self._save(player_id, state)
            # Return the updated public hand and authoritative state snapshot.
            return {"round": engine.public_round(round_state), **self.payload(player_id, state)}

    # Draw the final hand and settle one payout exactly once.
    def draw(self, player_id: str, round_id: str, body: dict) -> dict:
        # Validate the draw retry key before touching state or the ledger.
        action_id = require_action_id(body.get("action_id"), "action_id")
        # Serialize action binding, deterministic draw, ledger check, and completion marker.
        with _SETTLEMENT_LOCK:
            # Load the latest player-scoped state inside the settlement lock.
            state = self._load(player_id)
            # Find any round already owned by this draw action key.
            action_round = engine.round_for_draw_action(state, action_id)
            # Reject reuse of one draw key for a different round.
            if action_round is not None and action_round.get("round_id") != round_id:
                # Fail closed instead of assigning one money action to two rounds.
                raise ConflictError("action_id was already used for another round")
            # Find active or recent state so a repeated draw can recover settlement.
            round_state = engine.round_by_id(state, round_id)
            # Reject unknown identifiers without exposing another player's state.
            if round_state is None:
                # Return a stable lookup error for cross-session safety.
                raise NotFoundError("Jacks-or-Better round was not found")
            # Reject a new action id after this round was already bound or settled.
            if round_state.get("draw_action_id") not in (None, action_id):
                # Keep the committed settlement identity immutable.
                raise ConflictError("This round was already drawn with another action_id")
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
                # Bind the draw action durably before result calculation begins.
                round_state["draw_action_id"] = action_id
                # Persist action ownership so crash retries cannot substitute another key.
                self._save(player_id, state)
                # Compute the final held-card result from the persisted replacement pool.
                engine.draw(round_state, action_id, completed_at=self._clock())
                # Archive the completed result before issuing any payout credit.
                engine.archive_round(state, round_state)
                # Persist results first so a crash can resume credit by round id.
                self._save(player_id, state)
            # Reject unknown states rather than guessing a settlement action.
            elif round_state.get("phase") != "settled":
                # Explain the stale action as a state conflict.
                raise ConflictError("This round cannot be settled in its current phase")
            # Ensure the returned credits through the ledger recovery guard.
            payout_event = self._ensure_payout(player_id, state, round_state)
            # Return the completed hand and optional committed payout event.
            return {"round": engine.public_round(round_state), "payout": payout_event, "replayed": replayed, **self.payload(player_id, state)}


# Register the isolated routes for descriptor discovery or direct focused tests.
def register(router, service=None, *, test_seed=None):
    # Create the production service unless an isolated test supplies its own dependencies.
    game_service = service or JacksOrBetterVideoPokerService(seed_factory=(lambda deal_action_id: f"{test_seed}:{deal_action_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/jacks-or-better-video-poker/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query):
        # Resolve the router-bound player and return only that player's state.
        return game_service.payload(request_player_id(body, query))

    # Register the idempotent coin-wager deal endpoint.
    @router.post(r"/api/v1/games/jacks-or-better-video-poker/rounds")
    # Create or replay a round for the bound player.
    def rounds(body, query):
        # Resolve the router-bound player before any state or ledger access.
        return game_service.start_round(request_player_id(body, query), body)

    # Register reload-safe held-card selection.
    @router.post(r"/api/v1/games/jacks-or-better-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/holds")
    # Save held positions for the bound player's active round.
    def holds(body, query, round_id):
        # Resolve the router-bound player before locating the round.
        return game_service.set_holds(request_player_id(body, query), round_id, body.get("holds"))

    # Register deterministic held-card draw and payout settlement.
    @router.post(r"/api/v1/games/jacks-or-better-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/draw")
    # Complete and settle the bound player's round.
    def draw(body, query, round_id):
        # Resolve the router-bound player before locating or settling the round.
        return game_service.draw(request_player_id(body, query), round_id, body)

    # Return the service so focused tests can inspect injected adapters.
    return game_service
