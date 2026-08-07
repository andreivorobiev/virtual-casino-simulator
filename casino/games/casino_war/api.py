"""Session-compatible Casino War API adapter with replay-safe ledger settlement.

Requirements: CORE-009, CORE-011, LEDGER-005, LEDGER-006, LEDGER-007,
LEDGER-023, SESSION-003, SESSION-004, and planned SESSION-005 from #81.
"""

# Import deep-copy support so failed prepared decisions can restore prior state.
import copy
# Import a process-local reentrant lock so duplicate local requests serialize.
import threading
# Import action-id validation for bounded idempotency keys.
import re

# Import the shared player reader without a game-owned wallet mutation boundary.
from casino.core import players
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped state persistence for reload-safe rounds.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import canonical player validation for direct-router and pre-#110 compatibility.
from casino.core.validation import require_player_id
# Import consistent public validation errors.
from casino.errors import ValidationError
# Import the pure Casino War rules engine.
from casino.games.casino_war import engine

# Identify this game in state, routes, and ledger rows.
GAME_ID = engine.GAME_ID
# Accept UUID-like and namespaced client action ids without arbitrary text.
ACTION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
# Serialize prepared state and ledger recovery in the current local server process.
_ACTION_LOCK = threading.RLock()


# Persist and load player-scoped Casino War state through the shared store.
class StateRepository:
    # Load one session player's game document.
    def load(self, player_id: str) -> dict:
        # Delegate schema migration and provider selection to the shared state store.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Save one session player's game document.
    def save(self, player_id: str, state: dict) -> None:
        # Delegate atomic file replacement or provider persistence to the shared store.
        save_player_game_state(GAME_ID, player_id, state)


# Construct the shared settlement gateway while retaining the controller seam name.
def LedgerAdapter():
    # Preserve the old Casino War action field beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "casino_war_action_id")


# Coordinate pure engine transitions, prepared persistence, and ledger recovery.
class CasinoWarController:
    # Store injectable ports so isolated tests never touch repository data or balances.
    def __init__(self, repository=None, ledger_adapter=None, player_reader=None):
        # Use shared persistence unless a test supplies an in-memory repository.
        self.repository = repository or StateRepository()
        # Use the shared ledger unless a test supplies a recording adapter.
        self.ledger = ledger_adapter or LedgerAdapter()
        # Use the shared player lookup unless an isolated test supplies a fixture.
        self.player_reader = player_reader or players.get_player

    # Save one committed ledger event marker into player state.
    def _mark_committed(self, player_id: str, state: dict, intent: dict, event: dict) -> None:
        # Record only stable audit identifiers and not balance snapshots in game state.
        state.setdefault("ledger_actions", {})[intent["action_id"]] = {
            "ledger_id": event.get("ledger_id"),  # Link to the append-only ledger event.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "round_id": intent["round_id"],  # Preserve round association.
        }
        # Persist after every movement so later actions cannot overtake it.
        self.repository.save(player_id, state)

    # Apply all prepared ledger intents exactly once in their stored order.
    def _reconcile_round(self, player_id: str, state: dict, round_item: dict) -> dict:
        # Process ante, optional war wager, and settlement in deterministic order.
        for intent in round_item.get("ledger_intents", []):
            # Skip actions already recorded in the player state document.
            if intent["action_id"] in state.setdefault("ledger_actions", {}):
                # Continue to the next required movement.
                continue
            # Recover an event that committed before a crash interrupted state saving.
            event = self.ledger.find_action(player_id, intent["action_id"])
            # Commit only when the append-only ledger has no matching action.
            if event is None:
                # Perform the only wallet-affecting call in this controller.
                event = self.ledger.transact(intent)
            # Persist the recovered or newly committed event marker immediately.
            self._mark_committed(player_id, state, intent, event)
        # Mark a terminal result settled only after all required movements are recorded.
        if round_item.get("phase") == "ledger_pending":
            # Transition the public phase after successful ordered reconciliation.
            round_item["phase"] = "settled"
            # Persist the terminal phase for reload safety.
            self.repository.save(player_id, state)
        # Return the reconciled round.
        return round_item

    # Recover prepared movements for all retained rounds after reload or interruption.
    def _recover(self, player_id: str, state: dict) -> None:
        # Visit rounds in creation order so ledger history remains intuitive.
        for round_id in state.get("round_order", []):
            # Resolve each retained round defensively.
            round_item = state.get("rounds", {}).get(round_id)
            # Reconcile only rounds that have unapplied intents or a pending phase.
            if round_item and (round_item.get("phase") == "ledger_pending" or any(intent["action_id"] not in state.get("ledger_actions", {}) for intent in round_item.get("ledger_intents", []))):
                # Apply or recover the stored movements exactly once.
                self._reconcile_round(player_id, state, round_item)

    # Build the standard data payload consumed by the frontend module.
    def _payload(self, player_id: str, state: dict, round_item: dict | None = None) -> dict:
        # Return game state and current player data under the global API envelope.
        return {
            "game": GAME_ID,  # Identify the response source.
            "state": engine.public_state(state),  # Expose only client-safe state.
            "round": engine.public_round(round_item, state.get("ledger_actions")) if round_item else None,  # Include the affected round when applicable.
            "player": self.player_reader(player_id),  # Refresh wallet-adjacent player data.
        }

    # Read player state and finish any already-prepared interrupted action.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against duplicate action requests in this process.
        with _ACTION_LOCK:
            # Load the session-bound player document.
            state = self.repository.load(player_id)
            # Recover only actions the player already requested before interruption.
            self._recover(player_id, state)
            # Return the reload-safe public state.
            return self._payload(player_id, state)

    # Deal one initial comparison under a replay-safe client action id.
    def start_round(self, player_id: str, wager, action_id: str) -> dict:
        # Serialize preparation and reconciliation for duplicate local requests.
        with _ACTION_LOCK:
            # Load the session-bound player document.
            state = self.repository.load(player_id)
            # Replay an earlier response without drawing or debiting again.
            previous = state.setdefault("requests", {}).get(action_id)
            # Handle a duplicate client request id.
            if previous:
                # Resolve the originally created round.
                round_item = engine.get_round(state, previous["round_id"])
                # Recover any movement interrupted between ledger and state persistence.
                self._reconcile_round(player_id, state, round_item)
                # Return the same logical round and current wallet state.
                return self._payload(player_id, state, round_item)
            # Preserve state so an ordinary insufficient-funds failure can leave no phantom round.
            prior_state = copy.deepcopy(state)
            # Build the deterministic round and its stable ledger intents before wallet mutation.
            round_item = engine.start_round(state, player_id, wager, action_id)
            # Map the client id before the first ledger call so crash recovery can find the round.
            state["requests"][action_id] = {"command": "start_round", "round_id": round_item["round_id"]}
            # Persist prepared cards, outcome, and action ids before wallet mutation.
            self.repository.save(player_id, state)
            # Reconcile the prepared ante and any immediate settlement.
            try:
                # Apply every required movement in engine order.
                self._reconcile_round(player_id, state, round_item)
            # Restore clean state only when the first ledger movement never committed.
            except Exception:
                # Read the first stable ante action for failure classification.
                ante = round_item["ledger_intents"][0]
                # Roll back the prepared round when no append-only ledger event exists.
                if self.ledger.find_action(player_id, ante["action_id"]) is None:
                    # Restore the exact pre-request document.
                    self.repository.save(player_id, prior_state)
                # Re-raise the original domain or storage error.
                raise
            # Return the settled or decision-ready round.
            return self._payload(player_id, state, round_item)

    # Execute surrender or war once under a replay-safe client action id.
    def decide(self, player_id: str, round_id: str, decision: str, action_id: str) -> dict:
        # Serialize preparation and reconciliation for duplicate local decisions.
        with _ACTION_LOCK:
            # Load the session-bound player document.
            state = self.repository.load(player_id)
            # Replay an earlier decision response without another debit or credit.
            previous = state.setdefault("requests", {}).get(action_id)
            # Handle a duplicate decision action id.
            if previous:
                # Reject reuse of one action id for a different command or round.
                if previous.get("command") != decision or previous.get("round_id") != round_id:
                    # Keep idempotency keys one-command-only.
                    raise ValidationError("Casino War action_id was already used for another command")
                # Resolve the originally transitioned round.
                round_item = engine.get_round(state, round_id)
                # Recover any interrupted ledger movement.
                self._reconcile_round(player_id, state, round_item)
                # Return the same logical decision result.
                return self._payload(player_id, state, round_item)
            # Preserve the tie-decision state in case the first new movement is rejected.
            prior_state = copy.deepcopy(state)
            # Execute the selected pure engine transition.
            if decision == "surrender":
                # Prepare the half-wager return.
                round_item = engine.surrender(state, round_id, action_id)
            # Handle the only other supported decision.
            elif decision == "war":
                # Prepare the matching war debit, cards, and possible settlement.
                round_item = engine.go_to_war(state, round_id, action_id)
            # Reject unexpected internal decision names.
            else:
                # Keep the controller's command vocabulary explicit.
                raise ValidationError("Casino War decision is invalid")
            # Map the client id before ledger movement for crash recovery.
            state["requests"][action_id] = {"command": decision, "round_id": round_id}
            # Persist the prepared decision and deterministic dealt cards.
            self.repository.save(player_id, state)
            # Identify the first new movement created by this decision.
            first_new_intent = next(intent for intent in round_item["ledger_intents"] if action_id in intent["action_id"])
            # Reconcile the prepared movement sequence.
            try:
                # Apply the war debit before settlement or the surrender credit once.
                self._reconcile_round(player_id, state, round_item)
            # Restore the tie decision only when no new movement committed.
            except Exception:
                # Check the append-only ledger in case state saving was interrupted.
                if self.ledger.find_action(player_id, first_new_intent["action_id"]) is None:
                    # Restore the actionable tie state after insufficient funds or validation failure.
                    self.repository.save(player_id, prior_state)
                # Re-raise the original domain or storage error.
                raise
            # Return the terminal settlement payload.
            return self._payload(player_id, state, round_item)


# Normalize one required client action id.
def require_action_id(body: dict) -> str:
    # Read and trim the caller's idempotency key.
    action_id = str(body.get("action_id") or "").strip()
    # Reject missing, oversized, or unsafe identifiers.
    if not ACTION_ID_RE.fullmatch(action_id):
        # Explain the stable API requirement without echoing caller input.
        raise ValidationError("Casino War action_id must be 8-128 letters, numbers, dots, colons, underscores, or hyphens")
    # Return the validated key for engine intent construction.
    return action_id


# Resolve a player id compatibly before and after the #81 router resolver lands.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize direct-router tests and pre-context callers.
    context = context or {}
    # Prefer #110's resolved id, then current bound context, then compatible explicit input.
    player_id = context.get("resolved_player_id") or context.get("bound_player_id") or body.get("player_id") or query.get("player_id") or "human"
    # Validate the selected identifier through the shared boundary.
    return require_player_id({"player_id": player_id})


# Register isolated routes for catalog-driven discovery after #110 merges.
def register(router, controller=None):
    # Use the production controller unless isolated tests inject recording ports.
    service = controller or CasinoWarController()

    # Register reload-safe state retrieval under the additive v1 game namespace.
    @router.get(r"/api/v1/games/casino-war/state")
    # Read the session-bound player's table state.
    def state(body, query, context=None):
        # Delegate recovery and response construction to the controller.
        return service.state(request_player_id(body, query, context))

    # Register initial deal under the additive v1 game namespace.
    @router.post(r"/api/v1/games/casino-war/rounds")
    # Start one replay-safe round.
    def start(body, query, context=None):
        # Resolve the session player before interpreting action data.
        player_id = request_player_id(body, query, context)
        # Delegate deterministic dealing and ledger settlement to the controller.
        return service.start_round(player_id, body.get("wager"), require_action_id(body))

    # Register the half-wager surrender decision.
    @router.post(r"/api/v1/games/casino-war/rounds/(?P<round_id>[^/]+)/surrender")
    # Settle one tied round by surrendering.
    def surrender(body, query, round_id, context=None):
        # Resolve the session player before loading player-scoped state.
        player_id = request_player_id(body, query, context)
        # Delegate the replay-safe surrender credit.
        return service.decide(player_id, round_id, "surrender", require_action_id(body))

    # Register the matching-wager war decision.
    @router.post(r"/api/v1/games/casino-war/rounds/(?P<round_id>[^/]+)/war")
    # Resolve one tied round through the war comparison.
    def war(body, query, round_id, context=None):
        # Resolve the session player before loading player-scoped state.
        player_id = request_player_id(body, query, context)
        # Delegate the ordered war debit and optional settlement credit.
        return service.decide(player_id, round_id, "war", require_action_id(body))

    # Return the service for focused integration tests and diagnostics.
    return service
