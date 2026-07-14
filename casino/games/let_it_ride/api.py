"""Session-bound Let It Ride API adapter with replay-safe ledger settlement.

Requirements: CORE-009, CORE-011, CORE-012, SESSION-005, LEDGER-005,
LEDGER-006, LEDGER-007, LEDGER-009, LEDGER-023, and LIR-PROPOSED-001
through LIR-PROPOSED-004.
"""

# Import detached-copy support so rejected prepared actions restore exact prior state.
import copy
# Import bounded action-id validation without accepting arbitrary log text.
import re
# Import a process-local lock for the supported single-process simulator runtime.
import threading

# Import the only shared wallet mutation and read-only player services allowed to games.
from casino.core import ledger, players
# Import the shared clock for deterministic injectable completion timestamps.
from casino.core.clock import utc_now
# Import the shared identifier factory for production round and shoe identities.
from casino.core.ids import new_id
# Import player-scoped persistence so authenticated users never share game state.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import canonical player validation for trusted context and focused router tests.
from casino.core.validation import require_player_id
# Import public conflict and validation errors for fail-closed retry handling.
from casino.errors import ConflictError, ValidationError
# Import only this game's pure engine through the allowed module boundary.
from casino.games.let_it_ride import engine

# Identify state documents, route payloads, and ledger audit rows consistently.
GAME_ID = engine.GAME_ID
# Accept UUID-like or namespaced action ids while bounding storage and log size.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
# Serialize prepared state, ledger scans, movements, and markers in this local process.
_ACTION_LOCK = threading.RLock()


# Persist Let It Ride state through the shared player-scoped provider abstraction.
class StateRepository:
    # Load one authenticated player's isolated game document.
    def load(self, player_id: str) -> dict:
        # Delegate schema metadata and JSON/MySQL selection to shared storage.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's prepared or committed game document.
    def save(self, player_id: str, state: dict) -> None:
        # Delegate atomic file replacement or provider persistence to shared storage.
        save_player_game_state(GAME_ID, player_id, state)


# Adapt stable game intents to the shared ledger-only wallet interface.
class LedgerAdapter:
    # Calculate the signed amount expected in an append-only ledger event.
    @staticmethod  # Keep signing independent of adapter instances.
    def _signed_amount(intent: dict) -> float:  # Return the ledger-signed amount for this intent.
        # Represent debits as negative events and credits as positive events.
        return round(-intent["amount"] if intent["direction"] == "debit" else intent["amount"], 2)

    # Find and verify a movement that may have committed before a state-marker crash.
    def find_action(self, player_id: str, intent: dict):
        # Scan the player's complete supported local ledger window newest first.
        for event in ledger.read_recent(player_id, 1_000_000):
            # Read structured details defensively for historical non-Let-It-Ride rows.
            details = event.get("details") or {}
            # Ignore rows without this exact derived ledger action id.
            if details.get("let_it_ride_action_id") != intent["action_id"]:
                # Continue scanning older player-owned rows.
                continue
            # Verify every ownership and money dimension before accepting replay proof.
            matches = (
                event.get("player_id") == player_id  # Require the authenticated player.
                and event.get("game") == GAME_ID  # Require this game module.
                and event.get("round_id") == intent["round_id"]  # Require this round.
                and event.get("transaction_type") == intent["transaction_type"]  # Require this movement type.
                and round(float(event.get("amount", 0)), 2) == self._signed_amount(intent)  # Require the exact signed amount.
            )
            # Reject a reused ledger action id whose immutable fingerprint differs.
            if not matches:
                # Fail closed instead of issuing or accepting another movement.
                raise ConflictError("Let It Ride ledger action conflicts with a committed event")
            # Return the fully verified append-only event.
            return event
        # Report no prior event when the prepared movement still needs applying.
        return None

    # Commit one prepared debit or credit through casino.core.ledger only.
    def transact(self, intent: dict) -> dict:
        # Route opening wagers through shared insufficient-funds handling.
        if intent["direction"] == "debit":
            # Return the durable shared-ledger debit event.
            return ledger.debit(intent["player_id"], intent["amount"], intent["transaction_type"], intent["game"], intent["round_id"], intent["details"])
        # Route pull refunds and payouts through the shared credit path.
        if intent["direction"] == "credit":
            # Return the durable shared-ledger credit event.
            return ledger.credit(intent["player_id"], intent["amount"], intent["transaction_type"], intent["game"], intent["round_id"], intent["details"])
        # Reject malformed internal intents before any wallet access.
        raise ValidationError("Let It Ride ledger direction is invalid")


# Coordinate pure engine transitions, prepared persistence, and ledger recovery.
class LetItRideController:
    # Store production ports while allowing focused tests to inject in-memory adapters.
    def __init__(self, *, repository=None, ledger_adapter=None, player_reader=None, clock=utc_now, id_factory=new_id, seed_factory=None):
        # Use shared player-scoped persistence unless a test supplies a repository.
        self.repository = repository or StateRepository()
        # Use casino.core.ledger unless a test supplies a recording adapter.
        self.ledger = ledger_adapter or LedgerAdapter()
        # Use read-only shared player lookup unless a test supplies a fixture reader.
        self.player_reader = player_reader or players.get_player
        # Store an injectable clock for stable round timestamps.
        self.clock = clock
        # Store an injectable id factory for stable round and shoe identities.
        self.id_factory = id_factory
        # Store an optional deterministic seed factory that production registration omits.
        self.seed_factory = seed_factory

    # Save one recovered or newly committed event marker immediately.
    def _mark_committed(self, player_id: str, state: dict, intent: dict, event: dict) -> None:
        # Record immutable audit identifiers without caching mutable balances.
        state.setdefault("ledger_actions", {})[intent["action_id"]] = {
            "ledger_id": event.get("ledger_id"),  # Link to the append-only event.
            "transaction_type": intent["transaction_type"],  # Preserve movement identity.
            "round_id": intent["round_id"],  # Preserve round correlation.
            "amount": round(float(event.get("amount", 0)), 2),  # Preserve signed audit amount.
        }
        # Persist after each movement so later intents cannot overtake it.
        self.repository.save(player_id, state)

    # Apply or recover every prepared round movement exactly once and in order.
    def _reconcile_round(self, player_id: str, state: dict, round_item: dict) -> dict:
        # Process wager, refunds, and returned credits in deterministic order.
        for intent in round_item.get("ledger_intents", []):
            # Skip movements already recorded in the player state document.
            if intent["action_id"] in state.setdefault("ledger_actions", {}):
                # Continue to the next prepared movement.
                continue
            # Recover a movement that committed before its state marker persisted.
            event = self.ledger.find_action(player_id, intent)
            # Commit only when no verified append-only event exists.
            if event is None:
                # Perform the only wallet-affecting operation in this controller.
                event = self.ledger.transact(intent)
            # Persist the verified or new event marker immediately.
            self._mark_committed(player_id, state, intent, event)
        # Return the reconciled prepared round.
        return round_item

    # Recover all retained prepared movements after reload or interruption.
    def _recover(self, player_id: str, state: dict) -> None:
        # Visit rounds in creation order so ledger history remains intuitive.
        for round_id in state.get("round_order", []):
            # Resolve each retained round defensively.
            round_item = state.get("rounds", {}).get(round_id)
            # Reconcile only rounds with at least one unmarked movement.
            if round_item and any(intent["action_id"] not in state.get("ledger_actions", {}) for intent in round_item.get("ledger_intents", [])):
                # Apply or recover all stored movements in their original order.
                self._reconcile_round(player_id, state, round_item)

    # Determine whether any movement from a failed prepared command is durable.
    def _any_committed(self, player_id: str, intents: list[dict]) -> bool:
        # Inspect each newly prepared intent through the same verified ledger scan.
        for intent in intents:
            # Treat a matching event as durable and therefore unsafe to roll back.
            if self.ledger.find_action(player_id, intent) is not None:
                # Stop after the first committed append-only movement.
                return True
        # Report no movement when every verified scan is empty.
        return False

    # Build the standard data payload wrapped globally by the application router.
    def _payload(self, player_id: str, state: dict, round_item: dict | None = None, *, replayed: bool = False) -> dict:
        # Return only public game state, affected round, player snapshot, and replay status.
        return {
            "game": GAME_ID,  # Identify the payload source.
            "state": engine.public_state(state),  # Hide deck order and unrevealed cards.
            "round": engine.public_round(round_item, state.get("ledger_actions")) if round_item else None,  # Include one affected round when applicable.
            "player": self.player_reader(player_id),  # Refresh wallet-adjacent player data read-only.
            "replayed": replayed,  # Distinguish exact idempotent recovery from a new command.
        }

    # Read player state and finish only movements already prepared before interruption.
    def state(self, player_id: str) -> dict:
        # Serialize reload recovery against concurrent commands in this process.
        with _ACTION_LOCK:
            # Load the authenticated player's isolated document.
            state = self.repository.load(player_id)
            # Recover any durable prepared action without creating new gameplay.
            self._recover(player_id, state)
            # Return sanitized reload-safe state.
            return self._payload(player_id, state)

    # Start or replay one three-unit wager under an immutable client action id.
    def start_round(self, player_id: str, wager, action_id: str) -> dict:
        # Validate the retry key before any state or ledger access.
        validated_action_id = require_action_id(action_id)
        # Normalize wager now so replay comparisons use canonical precision.
        normalized_wager = engine.normalize_wager(wager)
        # Serialize preparation, ledger scans, movements, and markers locally.
        with _ACTION_LOCK:
            # Load the authenticated player's latest document.
            state = self.repository.load(player_id)
            # Finish only prior prepared movements before evaluating a new command.
            self._recover(player_id, state)
            # Resolve a prior command with this client action id.
            previous = state.setdefault("requests", {}).get(validated_action_id)
            # Replay only an exact immutable start fingerprint.
            if previous is not None:
                # Reject action-id reuse for another command or wager amount.
                if previous.get("command") != "rounds" or previous.get("wager") != normalized_wager:
                    # Fail closed without dealing cards or moving play tokens.
                    raise ConflictError("Let It Ride action_id was already used with different request data")
                # Resolve the originally prepared round.
                round_item = engine.get_round(state, previous["round_id"])
                # Recover any marker interrupted after a committed event.
                self._reconcile_round(player_id, state, round_item)
                # Return the same logical result and current balance.
                return self._payload(player_id, state, round_item, replayed=True)
            # Preserve exact prior state for a wager rejected before any ledger commit.
            prior_state = copy.deepcopy(state)
            # Derive deterministic cards only through a non-production injected seam.
            seed = self.seed_factory(validated_action_id) if self.seed_factory else None
            # Create the full opening result and ordered intents before wallet mutation.
            round_item = engine.start_round(
                state,  # Pass the loaded authenticated-player document.
                player_id,  # Bind every prepared record to the trusted player.
                normalized_wager,  # Use the canonical two-decimal wager fingerprint.
                validated_action_id,  # Derive every movement from the validated public command id.
                seed=seed,  # Supply deterministic entropy only through an injected test seam.
                round_id=self.id_factory("lir"),  # Allocate the production or focused-test round identity.
                shoe_id=self.id_factory("lirshoe"),  # Allocate deck telemetry without exposing an entropy seed.
                created_at=self.clock(),  # Supply the injected audit timestamp.
            )
            # Store the immutable command fingerprint before the first ledger call.
            state["requests"][validated_action_id] = {"command": "rounds", "round_id": round_item["round_id"], "wager": normalized_wager}
            # Persist cards, request mapping, and intents before wallet mutation.
            self.repository.save(player_id, state)
            # Apply or recover the prepared opening debit.
            try:
                # Reconcile the three-unit wager debit.
                self._reconcile_round(player_id, state, round_item)
            # Restore prior state only when no append-only movement committed.
            except Exception:
                # Read the prepared wager intent for durable-commit classification.
                wager_intent = round_item["ledger_intents"][0]
                # Remove a phantom round after an ordinary pre-commit ledger rejection.
                if not self._any_committed(player_id, [wager_intent]):
                    # Restore the exact document that existed before the request.
                    self.repository.save(player_id, prior_state)
                # Preserve the original public or storage failure.
                raise
            # Return the new decision-ready result and refreshed balance.
            return self._payload(player_id, state, round_item, replayed=False)

    # Apply or replay one staged ride-or-pull decision.
    def decide(self, player_id: str, round_id: str, stage: str, decision, action_id: str) -> dict:
        # Validate the retry key before loading player-owned state.
        validated_action_id = require_action_id(action_id)
        # Normalize the public decision before fingerprinting the request.
        normalized_decision = engine.normalize_decision(decision)
        # Restrict internal callers to the two published stages.
        if stage not in {"first", "second"}:
            # Fail closed before state or ledger mutation.
            raise ValidationError("Let It Ride stage is invalid")
        # Serialize decision preparation and settlement locally.
        with _ACTION_LOCK:
            # Load the authenticated player's isolated document.
            state = self.repository.load(player_id)
            # Recover the opening wager or earlier prepared movements first.
            self._recover(player_id, state)
            # Resolve a prior command with this client action id.
            previous = state.setdefault("requests", {}).get(validated_action_id)
            # Replay only the exact command, round, stage, and decision fingerprint.
            if previous is not None:
                # Reject reuse for another round, stage, or decision.
                if previous.get("command") != "decision" or previous.get("round_id") != round_id or previous.get("stage") != stage or previous.get("decision") != normalized_decision:
                    # Fail closed without revealing cards or moving tokens.
                    raise ConflictError("Let It Ride action_id was already used with different request data")
                # Resolve the already transitioned round in this player's state.
                round_item = engine.get_round(state, round_id)
                # Recover any movement interrupted before its state marker.
                self._reconcile_round(player_id, state, round_item)
                # Return the same round and current wallet snapshot.
                return self._payload(player_id, state, round_item, replayed=True)
            # Preserve the exact pre-decision state for pre-commit failures.
            prior_state = copy.deepcopy(state)
            # Resolve the current player-owned round before tracking new intents.
            round_item = engine.get_round(state, round_id)
            # Record the existing intent count so rollback checks only this decision.
            existing_intent_count = len(round_item.get("ledger_intents", []))
            # Prepare reveal, optional refund, and optional final payout before side effects.
            engine.advance_decision(state, round_id, stage, normalized_decision, validated_action_id, completed_at=self.clock())
            # Store the immutable decision fingerprint before any new movement.
            state["requests"][validated_action_id] = {"command": "decision", "round_id": round_id, "stage": stage, "decision": normalized_decision}
            # Persist result state and ordered new intents first.
            self.repository.save(player_id, state)
            # Slice only movements introduced by this decision for rollback classification.
            new_intents = round_item.get("ledger_intents", [])[existing_intent_count:]
            # Apply or recover the complete round sequence in original order.
            try:
                # Skip marked prior movements and process only missing decision movements.
                self._reconcile_round(player_id, state, round_item)
            # Restore the actionable decision only when none of its movements committed.
            except Exception:
                # Keep prepared recovery state after a durable refund or payout event.
                if not self._any_committed(player_id, new_intents):
                    # Restore cards, deck, request map, and decision phase exactly.
                    self.repository.save(player_id, prior_state)
                # Preserve the original public or storage failure.
                raise
            # Return the newly advanced or settled result and refreshed balance.
            return self._payload(player_id, state, round_item, replayed=False)


# Validate one required client idempotency key without coercing other JSON types.
def require_action_id(value) -> str:
    # Require an actual bounded string using conservative URL-safe characters.
    if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
        # Explain the stable contract without echoing caller-controlled input.
        raise ValidationError("Let It Ride action_id must be 8-128 letters, numbers, dots, colons, underscores, or hyphens")
    # Return the exact validated identifier for immutable fingerprinting.
    return value


# Resolve the trusted session player with absolute precedence over caller identifiers.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize direct focused-test calls that omit request context.
    context = context or {}
    # Read the router-resolved identity established by the shared session resolver.
    resolved_player_id = context.get("resolved_player_id")
    # Read the normal-user binding established by authenticated request handling.
    bound_player_id = context.get("bound_player_id")
    # Retain an authenticated user fallback for compatible direct handler calls.
    user_player_id = (context.get("user") or {}).get("player_id")
    # Use only trusted request context; compatibility body and query ids never select state.
    player_id = bound_player_id or user_player_id or resolved_player_id or "human"
    # Validate and return the canonical player identifier.
    return require_player_id({"player_id": player_id})


# Register isolated additive v1 routes for focused tests and later catalog discovery.
def register(router, controller=None):
    # Use the production controller unless an isolated test injects in-memory ports.
    service = controller or LetItRideController()

    # Register reload-safe state retrieval for the authenticated player.
    @router.get(r"/api/v1/games/let-it-ride/state")
    # Accept trusted request context so caller ids cannot override the session.
    def state(body, query, context=None):
        # Resolve the trusted player before reading any game state.
        return service.state(request_player_id(body, query, context))

    # Register the replay-safe three-unit opening wager and deal.
    @router.post(r"/api/v1/games/let-it-ride/rounds")
    # Accept trusted request context for the wager action.
    def rounds(body, query, context=None):
        # Resolve the trusted player before interpreting money fields.
        player_id = request_player_id(body, query, context)
        # Delegate prepared dealing and ledger-only settlement to the controller.
        return service.start_round(player_id, body.get("wager"), body.get("action_id"))

    # Register the first withdraw-or-ride decision before any community card is visible.
    @router.post(r"/api/v1/games/let-it-ride/rounds/(?P<round_id>[A-Za-z0-9_-]+)/first-decision")
    # Accept trusted request context for the first staged decision.
    def first_decision(body, query, round_id, context=None):
        # Resolve the trusted player before locating the player-owned round.
        player_id = request_player_id(body, query, context)
        # Delegate reveal, optional refund, and recovery to the controller.
        return service.decide(player_id, round_id, "first", body.get("decision"), body.get("action_id"))

    # Register the second withdraw-or-ride decision before final evaluation.
    @router.post(r"/api/v1/games/let-it-ride/rounds/(?P<round_id>[A-Za-z0-9_-]+)/second-decision")
    # Accept trusted request context for the second staged decision.
    def second_decision(body, query, round_id, context=None):
        # Resolve the trusted player before locating the player-owned round.
        player_id = request_player_id(body, query, context)
        # Delegate final reveal, optional refund, payout, and recovery to the controller.
        return service.decide(player_id, round_id, "second", body.get("decision"), body.get("action_id"))

    # Return the service so focused tests can inspect injected adapters.
    return service
