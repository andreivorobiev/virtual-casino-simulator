"""Session-bound, escrow-ledger API adapter for Texas Hold'em issue #95.

Requirements: SESSION-005, LEDGER-005, LEDGER-006, LEDGER-007, and LEDGER-023.
"""

# Import deep-copy support so rejected opening debits leave no phantom hand.
import copy
# Import regular expressions for bounded client idempotency keys.
import re
# Import a process-local lock for single-server retry serialization.
import threading

# Import shared ledger, player, and managed-account services without direct balance mutation.
from casino.core import ledger, players, practice_accounts
# Import the shared clock for persisted hand and action timestamps.
from casino.core.clock import utc_now
# Import the shared id generator for ledger-correlated hand identifiers.
from casino.core.ids import new_id
# Import player-scoped persistence so authenticated users never share hands.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import canonical player-id validation for router-bound identities.
from casino.core.validation import require_player_id
# Import public conflict, funds, and validation errors for stable route responses and escrow healing (issue #411).
from casino.errors import ConflictError, InsufficientFundsError, ValidationError
# Import only this game's deterministic rules through the allowed boundary.
from casino.games.texas_holdem_practice_table import engine

# Use one game id consistently across state, routes, and ledger details.
GAME_ID = engine.GAME_ID
# Accept UUID-like and namespaced action ids without arbitrary log text.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,96}$")
# Serialize prepared state, ledger recovery, and action replay locally.
_ACTION_LOCK = threading.RLock()


# Persist and load player-scoped practice-table state through the shared store.
class StateRepository:
    # Load one authenticated player's isolated state document.
    def load(self, player_id: str) -> dict:
        # Delegate schema and provider behavior to the shared state abstraction.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's complete reload-safe state document.
    def save(self, player_id: str, state: dict) -> None:
        # Delegate atomic document replacement or provider persistence.
        save_player_game_state(GAME_ID, player_id, state)


# Adapt prepared game intents to the only permitted wallet mutation service.
class LedgerAdapter:
    # Ensure the three allocated wallets have their one-time issue #189 funding.
    def ensure_accounts(self) -> list[dict]:
        # Collect immutable funding or exact-replay evidence for every fixed seat.
        results = []
        # Match the accepted allocation without importing across the game boundary.
        for opponent in engine.PRACTICE_OPPONENTS:
            # Reuse the exact funding identity and semantics exposed in Admin.
            action_key = f"practice:{GAME_ID}:{opponent['player_id']}:funding-v1"
            # Credit or replay the fixed seed through the public core accounting seam.
            result = practice_accounts.transact(opponent["player_id"], engine.PRACTICE_ACCOUNT_FUNDING, "PRACTICE_OPPONENT_FUNDED", action_key, GAME_ID, None, "credit", "fund_account", component="initial_funding", details={"seat_id": opponent["seat_id"], "controller_policy": opponent["policy"]})
            # Retain the immutable event for focused and Admin-audit evidence.
            results.append(result)
        # Return all three funding results to the controller boundary.
        return results

    # Find one previously committed movement by its stable game action id.
    def find_action(self, player_id: str, action_id: str):
        # Scan bounded local history newest-first for crash recovery evidence.
        for event in reversed(ledger.read_recent(player_id, 1_000_000)):
            # Read structured details without assuming every legacy row has them.
            details = event.get("details") or {}
            # Match the unique action plus player and game ownership dimensions.
            if event.get("game") == GAME_ID and details.get("texas_holdem_action_id") == action_id:
                # Return the already-committed append-only event.
                return event
        # Report that the prepared movement still needs committing.
        return None

    # Commit one positive debit or credit intent through casino.core.ledger.
    def transact(self, intent: dict) -> dict:
        # Route real bot wallets through the Admin-audited practice-account seam.
        if intent.get("managed_opponent"):
            # Map terminal components to the stable public controller vocabulary.
            controller_action = {"escrow": "reserve_stack", "refund": "refund_stack", "payout": "settle_payout"}[intent["details"]["component"]]
            # Commit or replay the bot movement under the owning human session context.
            result = practice_accounts.transact(intent["player_id"], intent["amount"], intent["transaction_type"], intent["action_id"], intent["game"], intent["round_id"], intent["direction"], controller_action, session_owner_id=intent["details"]["session_owner_id"], component=intent["details"]["component"], details=intent["details"])
            # Return the immutable shared ledger event expected by recovery logic.
            return result["event"]
        # Route opening escrow through the shared insufficient-funds path.
        if intent.get("direction") == "debit":
            # Commit or replay the human debit inside the storage action transaction.
            event, _replayed = ledger.debit_once(intent["player_id"], intent["amount"], intent["transaction_type"], intent["action_id"], intent["game"], intent["round_id"], intent["details"])
            # Return the immutable event while player responses retain request-level replay state.
            return event
        # Route refund and payout credits through the shared ledger path.
        if intent.get("direction") == "credit":
            # Commit or replay the human credit inside the storage action transaction.
            event, _replayed = ledger.credit_once(intent["player_id"], intent["amount"], intent["transaction_type"], intent["action_id"], intent["game"], intent["round_id"], intent["details"])
            # Return the immutable event while player responses retain request-level replay state.
            return event
        # Reject malformed engine instructions before wallet code is reached.
        raise ValidationError("Texas Hold'em ledger direction is invalid")


# Coordinate deterministic hands, prepared persistence, and ledger recovery.
class TexasHoldemPracticeTableController:
    # Store injectable ports so focused tests never touch repository runtime data.
    def __init__(self, repository=None, ledger_adapter=None, player_reader=None, *, clock=utc_now, id_factory=new_id, seed_factory=None):
        # Use shared player-game persistence unless a test supplies memory storage.
        self.repository = repository or StateRepository()
        # Use the shared ledger unless a test supplies a recording adapter.
        self.ledger = ledger_adapter or LedgerAdapter()
        # Use the shared player lookup only for read-only response snapshots.
        self.player_reader = player_reader or players.get_player
        # Store an injectable clock for deterministic hand and action fixtures.
        self.clock = clock
        # Store an injectable server id generator for deterministic tests.
        self.id_factory = id_factory
        # Store an optional test-only seed factory that production leaves disabled.
        self.seed_factory = seed_factory

    # Save one committed ledger marker into the human player's state document.
    def _mark_committed(self, player_id: str, state: dict, intent: dict, event: dict) -> None:
        # Store only stable audit identifiers and not balance snapshots.
        state.setdefault("ledger_actions", {})[intent["action_id"]] = {
            "ledger_id": event.get("ledger_id"),  # Link state recovery to append-only history.
            "transaction_type": intent["transaction_type"],  # Preserve the movement type.
            "round_id": intent["round_id"],  # Preserve the complete hand association.
        }
        # Persist after each movement so later actions cannot overtake it.
        self.repository.save(player_id, state)

    # Apply or recover every prepared escrow/refund/payout intent exactly once.
    def _reconcile_hand(self, player_id: str, state: dict, hand: dict) -> dict:
        # Process movements in engine-defined escrow then settlement order.
        for intent in hand.get("ledger_intents", []):
            # Skip intents already recorded in the player-scoped state document.
            if intent["action_id"] in state.setdefault("ledger_actions", {}):
                # Continue to the next prepared movement.
                continue
            # Recover a row that committed before state-marker persistence.
            event = self.ledger.find_action(intent["player_id"], intent["action_id"])
            # Commit only when append-only history contains no matching action.
            if event is None:
                # Perform the only wallet-affecting call in this controller.
                event = self.ledger.transact(intent)
            # Persist the recovered or newly committed event immediately.
            self._mark_committed(player_id, state, intent, event)
        # Publish terminal state only after refund and payout movements reconcile.
        if hand.get("phase") == "ledger_pending":
            # Mark every terminal movement complete for public responses.
            hand["phase"] = "settled"
            # Archive the hand into bounded private and compact replay history.
            engine.archive_hand(state, hand)
            # Persist the terminal phase and active-slot cleanup together.
            self.repository.save(player_id, state)
        # Return the reconciled retained hand.
        return hand

    # Report whether a hand is still exactly as start_hand prepared it, before any table action (issue #411).
    @staticmethod
    def _is_prepared_hand(hand: dict) -> bool:
        # A prepared hand is still preflop, has no applied actions, and carries only opening escrow debits.
        return hand.get("phase") == "preflop" and not hand.get("action_log") and all(intent.get("direction") == "debit" and (intent.get("details") or {}).get("component") == "escrow" for intent in hand.get("ledger_intents", []))

    # Credit back every already-committed opening escrow of one failed prepared hand (issue #411).
    def _compensate_committed_escrows(self, hand: dict) -> int:
        # Count reversed escrows so callers can tell a clean failure from a compensated one.
        compensated = 0
        # Walk every prepared movement because any committed prefix may precede the failing seat.
        for intent in hand.get("ledger_intents", []):
            # Reverse only opening escrow debits and never terminal settlement credits.
            if intent.get("direction") != "debit" or (intent.get("details") or {}).get("component") != "escrow":
                # Skip movements outside the compensation contract.
                continue
            # Leave intents alone when append-only history shows their debit never committed.
            if self.ledger.find_action(intent["player_id"], intent["action_id"]) is None:
                # Continue to the next prepared movement.
                continue
            # Derive the deterministic exactly-once compensation identity from the committed escrow action.
            compensation_action_id = f"{intent['action_id']}:compensation"
            # Mirror the committed intent so the credit reverses the exact seat, magnitude, and hand.
            compensation = copy.deepcopy(intent)
            # Bind the compensation to its own durable action identity.
            compensation["action_id"] = compensation_action_id
            # Reverse the wallet direction while keeping the reserved magnitude.
            compensation["direction"] = "credit"
            # Keep the established human refund vocabulary and the managed-opponent refund vocabulary.
            compensation["transaction_type"] = "TEXAS_HOLDEM_ESCROW_REFUND_CREDIT" if intent.get("transaction_type") == "TEXAS_HOLDEM_ESCROW_DEBIT" else "PRACTICE_OPPONENT_ESCROW_REFUND"
            # Expose the compensation identity to append-only recovery scans.
            compensation["details"]["texas_holdem_action_id"] = compensation_action_id
            # Route managed-opponent compensation through the audited refund controller action.
            compensation["details"]["component"] = "refund"
            # Preserve the reversed escrow identity for Admin audit correlation.
            compensation["details"]["compensates_action_id"] = intent["action_id"]
            # Commit at most once, reusing any row an earlier interrupted heal already wrote.
            if self.ledger.find_action(compensation["player_id"], compensation_action_id) is None:
                # Issue the reversing credit through the only permitted wallet seam.
                self.ledger.transact(compensation)
            # Record one reversed escrow toward zero net wallet movement.
            compensated += 1
        # Return how many committed escrows were reversed.
        return compensated

    # Recover any interrupted movements in active or retained hands after reload.
    def _recover(self, player_id: str, state: dict) -> None:
        # Visit the active hand before bounded private history for event order.
        candidates = [state.get("active_hand"), *state.get("recent_hands", [])]
        # Inspect every retained hand defensively.
        for hand in candidates:
            # Ignore empty active slots.
            if hand is None:
                # Continue to the next retained record.
                continue
            # Check whether any prepared movement lacks a durable state marker.
            pending = any(intent.get("action_id") not in state.get("ledger_actions", {}) for intent in hand.get("ledger_intents", []))
            # Reconcile missing markers or terminal pending settlement.
            if pending or hand.get("phase") == "ledger_pending":
                # Contain an unfundable prepared hand instead of re-raising on every later route (issue #411).
                try:
                    # Recover only movements already prepared in durable game state.
                    self._reconcile_hand(player_id, state, hand)
                # Self-heal the bricked table by unwinding a prepared hand whose seat escrow cannot fund (issue #411).
                except InsufficientFundsError:
                    # Keep fail-closed behavior for history rows and any hand that advanced past its opening escrow.
                    if hand is not state.get("active_hand") or not self._is_prepared_hand(hand):
                        # Re-raise because only stranded prepared escrow is safe to unwind.
                        raise
                    # Credit back every committed escrow so net wallet movement returns to zero.
                    self._compensate_committed_escrows(hand)
                    # Clear the unfunded hand from the actionable slot so the table plays again.
                    state["active_hand"] = None
                    # Persist the healed document before continuing the original request.
                    self.repository.save(player_id, state)

    # Build the standard game data payload shared by every route.
    def _payload(self, player_id: str, state: dict, hand=None, *, replayed=False) -> dict:
        # Return only client-safe game state and a read-only player snapshot.
        return {
            "game": GAME_ID,  # Identify the response source.
            "state": engine.public_state(state),  # Redact decks and opponent cards.
            "hand": engine.public_hand(hand, state.get("ledger_actions")) if hand else None,  # Include the affected hand when applicable.
            "player": self.player_reader(player_id),  # Refresh wallet-adjacent balance data.
            "replayed": bool(replayed),  # Tell clients whether an idempotent request was reused.
        }

    # Replay a retained full hand or its compact settled response snapshot.
    def _replay_payload(self, player_id: str, state: dict, hand_id: str) -> dict:
        # Prefer a full retained hand while it remains inside private history.
        hand = engine.hand_by_id(state, hand_id)
        # Reconcile any full prepared record before constructing its response.
        if hand is not None:
            # Recover an interrupted movement exactly as a normal immediate retry does.
            self._reconcile_hand(player_id, state, hand)
            # Return the current logical hand without another deal or movement.
            return self._payload(player_id, state, hand, replayed=True)
        # Resolve the sanitized terminal snapshot retained for an older receipt.
        snapshot = state.get("replay_hands", {}).get(hand_id)
        # Fail closed if persisted request and replay records disagree.
        if snapshot is None:
            # Preserve the action identity without silently accepting it as new.
            raise ConflictError("action_id replay receipt is incomplete")
        # Build current player/state context while marking the request as replayed.
        payload = self._payload(player_id, state, replayed=True)
        # Return a detached immutable snapshot as the affected historical hand.
        payload["hand"] = copy.deepcopy(snapshot)
        # Return the complete standard game data response.
        return payload

    # Read player state and finish any already-prepared interrupted movement.
    def state(self, player_id: str) -> dict:
        # Serialize reload recovery against duplicate action requests.
        with _ACTION_LOCK:
            # Load the session-bound player's isolated table document.
            state = self.repository.load(player_id)
            # Recover only movements that were already durably prepared.
            self._recover(player_id, state)
            # Return the reload-safe public state.
            return self._payload(player_id, state)

    # Start or replay one escrow-backed practice hand.
    def start_hand(self, player_id: str, base_wager, action_id: str) -> dict:
        # Normalize the wager before comparing idempotent replay parameters.
        wager = engine.require_base_wager(base_wager)
        # Serialize preparation and reconciliation for duplicate local requests.
        with _ACTION_LOCK:
            # Ensure every fixed practice opponent has a real funded wallet before reserving exposure.
            self.ledger.ensure_accounts()
            # Load the latest player-scoped state under the action lock.
            state = self.repository.load(player_id)
            # Recover any earlier prepared movement before accepting a new command.
            self._recover(player_id, state)
            # Read an earlier command using the same client action id.
            previous = state.setdefault("requests", {}).get(action_id)
            # Replay one logically identical start command.
            if previous is not None:
                # Reject reuse for another command or changed wallet exposure.
                if previous.get("command") != "start_hand" or previous.get("base_wager") != wager:
                    # Keep one idempotency key bound to exactly one command payload.
                    raise ConflictError("action_id was already used with different hand settings")
                # Return the original full or compact hand without another debit or deal.
                return self._replay_payload(player_id, state, previous["hand_id"])
            # Prevent overlapping player-scoped hands.
            if state.get("active_hand") is not None:
                # Require the current table hand to settle first.
                raise ConflictError("Finish the active Texas Hold'em hand before starting another")
            # Preserve clean state so an uncommitted insufficient-funds failure can roll back.
            prior_state = copy.deepcopy(state)
            # Derive deterministic cards only through an injected non-production hook.
            seed = self.seed_factory(action_id) if self.seed_factory else None
            # Prepare the complete private hand and escrow intent before wallet movement.
            hand = engine.create_hand(player_id, wager, action_id, seed=seed, hand_id=self.id_factory("thpt"), created_at=self.clock())
            # Require every practice seat to cover its reserve before anything persists, so failure stays atomic (issue #411).
            for opponent in engine.PRACTICE_OPPONENTS:
                # Read each funded opponent wallet through the read-only player seam.
                if self.player_reader(opponent["player_id"])["balance"] < hand["reserved_amount"]:
                    # Fail closed with no persisted hand, no receipt, and no wallet movement.
                    raise ConflictError("Lower the wager - a practice seat cannot cover the reserved bets")
            # Place the prepared hand in the actionable player-scoped slot.
            state["active_hand"] = hand
            # Map the client command before the first ledger call for recovery.
            state["requests"][action_id] = {"command": "start_hand", "hand_id": hand["hand_id"], "base_wager": wager}
            # Persist cards, board plan, and escrow identity before wallet mutation.
            self.repository.save(player_id, state)
            # Reconcile the four opening escrow debits.
            try:
                # Apply or recover the prepared debits exactly once.
                self._reconcile_hand(player_id, state, hand)
            # Unwind every committed escrow so a mid-reconcile failure strands no wager (issue #411).
            except Exception:
                # Credit back any escrow prefix that committed before the failing seat.
                compensated = self._compensate_committed_escrows(hand)
                # Restore the exact pre-request document so no phantom hand stays actionable.
                restored = copy.deepcopy(prior_state)
                # Retire a wallet-touching identity because its escrow rows are now refunded (issue #411).
                if compensated:
                    # Keep the receipt so a same-id retry fails closed instead of replaying refunded escrow rows as live.
                    restored.setdefault("requests", {})[action_id] = {"command": "start_hand", "hand_id": hand["hand_id"], "base_wager": wager}
                # Persist the rolled-back document with zero net wallet movement.
                self.repository.save(player_id, restored)
                # Re-raise the original ledger or storage error.
                raise
            # Return the new preflop hand after committed wallet reservation.
            return self._payload(player_id, state, hand)

    # Apply or replay one human action plus immediate server-opponent responses.
    def act(self, player_id: str, hand_id: str, action: str, action_id: str, expected_phase: str) -> dict:
        # Normalize the narrow fixed-limit decision vocabulary.
        normalized_action = str(action or "").strip().lower()
        # Reject malformed actions before loading or mutating player state.
        if normalized_action not in {"call", "fold"}:
            # Keep the additive API vocabulary explicit.
            raise ValidationError("action must be call or fold")
        # Validate the client-observed phase before loading mutable hand state.
        normalized_phase = require_expected_phase(expected_phase)
        # Serialize state transitions and settlement recovery locally.
        with _ACTION_LOCK:
            # Load the latest session-bound player state.
            state = self.repository.load(player_id)
            # Recover any movement prepared by an earlier request first.
            self._recover(player_id, state)
            # Read an earlier command using the same client action id.
            previous = state.setdefault("requests", {}).get(action_id)
            # Replay one logically identical human action.
            if previous is not None:
                # Reject action ids reused across hands or decisions.
                if previous.get("command") != "act" or previous.get("hand_id") != hand_id or previous.get("action") != normalized_action or previous.get("expected_phase") != normalized_phase:
                    # Fail closed on conflicting retry payloads.
                    raise ConflictError("action_id was already used for a different table action")
                # Return the original full or compact hand without advancing twice.
                return self._replay_payload(player_id, state, hand_id)
            # Resolve the hand only inside this authenticated player's state.
            hand = engine.require_hand(state, hand_id)
            # Require actions to target the current active hand.
            if (state.get("active_hand") or {}).get("hand_id") != hand_id:
                # Reject stale actions against settled history.
                raise ConflictError("Only the active Texas Hold'em hand accepts actions")
            # Reject a new id created from a stale pre-navigation decision surface.
            if hand.get("phase") != normalized_phase:
                # Prevent one intended click from consuming a later betting street.
                raise ConflictError("The Texas Hold'em hand advanced beyond the expected phase")
            # Apply the human decision through the shared human/opponent engine path.
            engine.apply_action(hand, "human", normalized_action, action_id, created_at=self.clock())
            # Run fixed server-managed responses until human control returns or settlement.
            engine.advance_opponents(hand, action_id, clock=self.clock)
            # Map the command before any terminal refund or payout movement.
            state["requests"][action_id] = {"command": "act", "hand_id": hand_id, "action": normalized_action, "expected_phase": normalized_phase}
            # Persist the complete deterministic action sequence before settlement credits.
            self.repository.save(player_id, state)
            # Reconcile any newly prepared terminal refund and payout credits.
            self._reconcile_hand(player_id, state, hand)
            # Return the updated street or settled hand.
            return self._payload(player_id, state, hand)


# Normalize one required client action id for start and decision commands.
def require_action_id(body: dict) -> str:
    # Read the caller value without coercing another JSON type into a key.
    action_id = body.get("action_id")
    # Reject missing, oversized, or unsafe identifiers.
    if not isinstance(action_id, str) or not ACTION_ID_PATTERN.fullmatch(action_id):
        # Explain the stable boundary without echoing caller input.
        raise ValidationError("action_id must be 8-96 letters, numbers, dots, colons, underscores, or hyphens")
    # Return the validated key unchanged for exact replay matching.
    return action_id


# Normalize one required optimistic phase precondition for decision commands.
def require_expected_phase(value) -> str:
    # Normalize the public phase vocabulary without accepting terminal phases.
    phase = str(value or "").strip().lower()
    # Reject missing or unknown phase observations before any state mutation.
    if phase not in engine.ACTION_PHASES:
        # Keep stale-surface protection mandatory on the new additive route.
        raise ValidationError("expected_phase must be preflop, flop, turn, or river")
    # Return the validated betting phase for replay binding and comparison.
    return phase


# Resolve the player identity already bound by the authenticated game router.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Normalize direct-router and focused-test contexts.
    context = context or {}
    # Prefer the shared resolver and session binding over every caller-supplied id.
    player_id = context.get("resolved_player_id") or context.get("bound_player_id") or query.get("player_id") or body.get("player_id") or "human"
    # Validate the selected canonical player identifier.
    return require_player_id({"player_id": player_id})


# Register isolated routes for later catalog materialization by issue #77.
def register(router, controller=None, *, test_seed=None):
    # Use the production controller unless a focused test supplies recording ports.
    service = controller or TexasHoldemPracticeTableController(seed_factory=(lambda action_id: f"{test_seed}:{action_id}") if test_seed is not None else None)

    # Register reload-safe state retrieval under the additive v1 game namespace.
    @router.get(r"/api/v1/games/texas-holdem-practice-table/state")
    # Read the session-bound player's private practice-table state.
    def state(body, query, context=None):
        # Resolve the authenticated player before loading any hand state.
        return service.state(request_player_id(body, query, context))

    # Register one replay-safe escrow-backed hand start.
    @router.post(r"/api/v1/games/texas-holdem-practice-table/hands")
    # Deal one private hand for the session-bound player.
    def hands(body, query, context=None):
        # Resolve the authenticated player before interpreting wager input.
        player_id = request_player_id(body, query, context)
        # Delegate prepared persistence and exactly-once escrow handling.
        return service.start_hand(player_id, body.get("base_wager"), require_action_id(body))

    # Register fixed-limit human decisions under one shared action route.
    @router.post(r"/api/v1/games/texas-holdem-practice-table/hands/(?P<hand_id>[A-Za-z0-9_-]+)/actions")
    # Apply one human call or fold plus deterministic server responses.
    def actions(body, query, hand_id, context=None):
        # Resolve the authenticated player before locating the private hand.
        player_id = request_player_id(body, query, context)
        # Delegate retry-safe action validation, advancement, and settlement.
        return service.act(player_id, hand_id, body.get("action"), require_action_id(body), require_expected_phase(body.get("expected_phase")))

    # Return the controller for focused tests and diagnostics.
    return service
