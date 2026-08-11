# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Replay-safe state and ledger coordination for Three Card Poker.

Requirements: SESSION-005, STORAGE-001, STORAGE-002, LEDGER-005,
LEDGER-006, LEDGER-007, and LEDGER-009.
"""

# Import deep-copy support for persistence boundaries and safe rollback.
import copy
# Import bounded client-identifier validation.
import re
# Import a process-local lock for prepared state and ledger reconciliation.
import threading

# Import the read-only player service without a game-owned wallet mutation boundary.
from casino.core import players
# Import the shared clock for injectable lifecycle timestamps.
from casino.core.clock import utc_now
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import stable server-side identifier generation.
from casino.core.ids import new_id
# Import player-scoped persistence through the configured storage provider.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict and validation errors.
from casino.errors import ConflictError, ValidationError
# Import only this game's pure engine through the allowed module boundary.
from casino.games.three_card_poker import engine

# Identify every persistence and ledger record owned by this service.
GAME_ID = engine.GAME_ID
# Accept bounded URL-safe client retry identifiers.
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize prepared state and replay scans in this local simulator process.
_ACTION_LOCK = threading.RLock()


# Validate one public idempotency identifier without echoing its value.
def require_client_id(value, field: str) -> str:
    # Require a string matching the conservative persisted identifier alphabet.
    if not isinstance(value, str) or not CLIENT_ID_PATTERN.fullmatch(value):
        # Return a stable API validation error.
        raise ValidationError(f"{field} must be 1-128 URL-safe characters")
    # Return the validated identifier unchanged for exact replay matching.
    return value


# Persist Three Card Poker state through shared provider-aware helpers.
class StateRepository:
    # Load one authenticated player's state document.
    def load(self, player_id: str) -> dict:
        # Delegate provider selection and schema metadata to shared storage.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's state document.
    def save(self, player_id: str, state: dict) -> None:
        # Delegate atomic JSON replacement or provider persistence to shared storage.
        save_player_game_state(GAME_ID, player_id, state)


# Construct the shared settlement gateway while retaining the controller seam name.
def LedgerAdapter():
    # Preserve the old Three Card Poker field beside canonical action evidence.
    return GameSettlementGateway(GAME_ID, "three_card_poker_action_id")


# Coordinate pure engine transitions, durable state, and ledger replay.
class ThreeCardPokerService:
    # Store production ports while permitting isolated deterministic tests.
    def __init__(self, repository=None, ledger_adapter=None, player_reader=None, clock=utc_now, id_factory=new_id, seed_factory=None):
        # Use shared player-state persistence unless tests inject memory storage.
        self.repository = repository or StateRepository()
        # Use the shared ledger unless tests inject a recording adapter.
        self.ledger = ledger_adapter or LedgerAdapter()
        # Use the canonical player reader unless tests inject a fixture.
        self.player_reader = player_reader or players.get_player
        # Store a deterministic clock seam for focused tests.
        self.clock = clock
        # Store a deterministic round-id seam for focused tests.
        self.id_factory = id_factory
        # Store an optional seed factory that production registration leaves disabled.
        self.seed_factory = seed_factory

    # Persist one committed ledger event marker immediately after movement.
    def _mark_committed(self, player_id: str, state: dict, intent: dict, event: dict) -> None:
        # Retain a detached event snapshot for stable replay responses.
        state.setdefault("ledger_actions", {})[intent["action_id"]] = {
            "ledger_id": event.get("ledger_id"),  # Link to the append-only record.
            "round_id": intent["round_id"],  # Preserve round ownership.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "event": copy.deepcopy(event),  # Preserve the response evidence.
        }
        # Save after every movement so later intents cannot overtake it.
        self.repository.save(player_id, state)

    # Apply or recover every prepared ledger intent in stable order.
    def _reconcile_round(self, player_id: str, state: dict, round_item: dict) -> dict:
        # Collect event evidence by deterministic action identifier.
        events = {}
        # Process initial debit, optional Play debit, and payout credit in order.
        for intent in round_item.get("ledger_intents", []):
            # Read an already-persisted marker when normal state saving completed.
            marker = state.setdefault("ledger_actions", {}).get(intent["action_id"])
            # Reuse the stored event without another wallet mutation.
            if marker is not None:
                # Copy evidence so callers cannot mutate persisted marker data.
                events[intent["action_id"]] = copy.deepcopy(marker.get("event") or {"ledger_id": marker.get("ledger_id"), "round_id": marker.get("round_id"), "transaction_type": marker.get("transaction_type")})
                # Continue to the next movement.
                continue
            # Search the append-only ledger in case a crash preceded marker saving.
            event = self.ledger.find_intent(intent)
            # Commit only when no matching ledger proof exists.
            if event is None:
                # Perform the only wallet-affecting call in this service.
                event = self.ledger.transact(intent)
            # Persist the recovered or new proof before processing another intent.
            self._mark_committed(player_id, state, intent, event)
            # Return the same detached evidence to the current response.
            events[intent["action_id"]] = copy.deepcopy(event)
        # Publish a terminal phase only after every required movement is marked.
        if round_item.get("phase") == "ledger_pending":
            # Transition prepared settlement to the public terminal phase.
            round_item["phase"] = "settled"
            # Persist terminal state for reload-safe state responses.
            self.repository.save(player_id, state)
        # Return committed event evidence keyed by action id.
        return events

    # Recover every retained round that has pending or unmarked intents.
    def _recover(self, player_id: str, state: dict) -> None:
        # Visit retained rounds in creation order for intuitive ledger ordering.
        for round_id in state.get("round_order", []):
            # Resolve each body defensively after bounded pruning.
            round_item = state.get("rounds", {}).get(round_id)
            # Skip pruned or malformed identifiers.
            if round_item is None:
                # Continue without exposing storage internals.
                continue
            # Detect any intent whose state marker was interrupted.
            missing_marker = any(intent["action_id"] not in state.get("ledger_actions", {}) for intent in round_item.get("ledger_intents", []))
            # Reconcile pending settlements and interrupted markers before public exposure.
            if round_item.get("phase") == "ledger_pending" or missing_marker:
                # Apply or recover the exact prepared intent sequence.
                self._reconcile_round(player_id, state, round_item)

    # Resolve one retained round referenced by a client request record.
    def _recorded_round(self, state: dict, record: dict) -> dict:
        # Read the stored round body when it remains in bounded history.
        round_item = state.get("rounds", {}).get(record.get("round_id"))
        # Fail closed if an old request identifier points to pruned state.
        if round_item is None:
            # Prevent reuse from causing a second wallet movement.
            raise ConflictError("This client action identifier was already used by an expired round")
        # Return the retained replay target.
        return round_item

    # Return the event produced by one named ledger stage.
    def _event_for_stage(self, state: dict, round_item: dict, events: dict, stage: str):
        # Find the only prepared intent with this stage.
        intent = next((item for item in round_item.get("ledger_intents", []) if (item.get("details") or {}).get("stage") == stage), None)
        # Return null when this round did not require the movement.
        if intent is None:
            # Preserve the explicit nullable response field.
            return None
        # Prefer evidence returned by this reconciliation pass.
        if intent["action_id"] in events:
            # Return a detached copy for response safety.
            return copy.deepcopy(events[intent["action_id"]])
        # Fall back to the persisted event marker for already-settled state.
        marker = state.get("ledger_actions", {}).get(intent["action_id"], {})
        # Return its detached event evidence when available.
        return copy.deepcopy(marker.get("event")) if marker.get("event") is not None else None

    # Build one standard game data payload.
    def _payload(self, player_id: str, state: dict, round_item=None, *, wager=None, settlement=None, replayed=None) -> dict:
        # Start with fields shared by state and action responses.
        payload = {
            "game": GAME_ID,  # Identify the response source.
            "state": engine.public_state(state),  # Expose only client-safe state.
            "player": self.player_reader(player_id),  # Refresh the current wallet view.
            "rules": engine.public_rules(),  # Publish fixed table configuration.
        }
        # Add action-specific fields only when a round was affected.
        if round_item is not None:
            # Expose the detached round with dealer privacy applied.
            payload["round"] = engine.public_round(round_item)
            # Expose the relevant debit event or null.
            payload["wager"] = copy.deepcopy(wager)
            # Expose the payout credit event or null.
            payload["settlement"] = copy.deepcopy(settlement)
            # Distinguish new commands from exact replays.
            payload["replayed"] = bool(replayed)
        # Return the data object; the shared HTTP layer adds the envelope.
        return payload

    # Read player state after reconciling any already-prepared action.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against concurrent commands in this process.
        with _ACTION_LOCK:
            # Load only this authenticated player's state document.
            state = self.repository.load(player_id)
            # Complete pending ledger work before public state is projected.
            self._recover(player_id, state)
            # Return the reload-safe state payload.
            return self._payload(player_id, state)

    # Deal or replay one initial wagered round.
    def start_round(self, player_id: str, body: dict) -> dict:
        # Validate the required public retry identifier.
        request_id = require_client_id(body.get("request_id"), "request_id")
        # Normalize wagers before building a replay fingerprint.
        ante, pair_plus = engine.normalize_bets(body.get("ante"), body.get("pair_plus"))
        # Bind exact normalized money settings to the client identifier.
        fingerprint = {"ante": ante, "pair_plus": pair_plus}
        # Serialize state preparation, ledger recovery, and marker saving.
        with _ACTION_LOCK:
            # Load the latest player-scoped document.
            state = self.repository.load(player_id)
            # Recover older prepared work before accepting another command.
            self._recover(player_id, state)
            # Read any prior use of this globally player-scoped client id.
            previous = state.setdefault("requests", {}).get(request_id)
            # Replay only the exact original command and money fingerprint.
            if previous is not None:
                # Reject cross-command or altered-money reuse.
                if previous.get("command") != "deal" or previous.get("fingerprint") != fingerprint:
                    # Fail closed before state or wallet mutation.
                    raise ConflictError("request_id was already used with different round settings")
                # Resolve the originally prepared round.
                round_item = self._recorded_round(state, previous)
                # Recover any ledger marker interrupted after commit.
                events = self._reconcile_round(player_id, state, round_item)
                # Resolve the initial debit evidence.
                wager_event = self._event_for_stage(state, round_item, events, "initial_wager")
                # Return the original logical round explicitly marked replayed.
                return self._payload(player_id, state, round_item, wager=wager_event, settlement=None, replayed=True)
            # Preserve clean state so a rejected first debit leaves no phantom round.
            prior_state = copy.deepcopy(state)
            # Derive test entropy only from an injected non-production hook.
            seed = self.seed_factory(request_id) if self.seed_factory else None
            # Create the deterministic complete deal and initial intent.
            round_item = engine.start_round(state, player_id, ante, pair_plus, request_id, seed=seed, round_id=self.id_factory("tcp"), created_at=self.clock())
            # Bind the request fingerprint before the first ledger call.
            state["requests"][request_id] = {"command": "deal", "round_id": round_item["round_id"], "fingerprint": fingerprint}
            # Persist private dealer cards and initial intent before wallet mutation.
            self.repository.save(player_id, state)
            # Reconcile the prepared initial debit with rollback on a clean rejection.
            try:
                # Apply or recover the one aggregate initial debit.
                events = self._reconcile_round(player_id, state, round_item)
            # Restore pre-request state only when no debit committed.
            except Exception:
                # Read the stable first intent for failure classification.
                initial_intent = round_item["ledger_intents"][0]
                # Search ledger proof without relying on the failed marker save.
                committed = self.ledger.find_intent(initial_intent)
                # Restore the exact prior document when no wallet movement exists.
                if committed is None:
                    # Remove the rejected prepared round and request mapping.
                    self.repository.save(player_id, prior_state)
                # Preserve pending state after a committed debit and re-raise the original failure.
                raise
            # Resolve the committed initial debit evidence.
            wager_event = self._event_for_stage(state, round_item, events, "initial_wager")
            # Return the decision-ready round.
            return self._payload(player_id, state, round_item, wager=wager_event, settlement=None, replayed=False)

    # Apply or replay one Play or Fold decision.
    def decide(self, player_id: str, round_id: str, body: dict) -> dict:
        # Validate the required decision retry identifier.
        action_id = require_client_id(body.get("action_id"), "action_id")
        # Normalize decision vocabulary before fingerprint comparison.
        decision = str(body.get("decision") or "").strip().lower()
        # Reject invalid decisions before loading or mutating wallet state.
        if decision not in {"play", "fold"}:
            # Return the same public error as the pure engine.
            raise ValidationError("decision must be play or fold")
        # Bind round and decision to the globally player-scoped client id.
        fingerprint = {"round_id": round_id, "decision": decision}
        # Serialize decision preparation and all remaining ledger work.
        with _ACTION_LOCK:
            # Load the latest player-scoped document.
            state = self.repository.load(player_id)
            # Complete older prepared movements before interpreting the decision.
            self._recover(player_id, state)
            # Read any prior use of this client identifier.
            previous = state.setdefault("requests", {}).get(action_id)
            # Replay only an identical decision for the same round.
            if previous is not None:
                # Reject cross-command, cross-round, or altered-decision reuse.
                if previous.get("command") != "decision" or previous.get("fingerprint") != fingerprint:
                    # Fail closed before any wallet movement.
                    raise ConflictError("action_id was already used with a different decision")
                # Resolve the originally transitioned round.
                round_item = self._recorded_round(state, previous)
                # Recover any interrupted Play debit or payout marker.
                events = self._reconcile_round(player_id, state, round_item)
                # Resolve the optional Play debit evidence.
                wager_event = self._event_for_stage(state, round_item, events, "play_wager")
                # Resolve the optional payout credit evidence.
                settlement_event = self._event_for_stage(state, round_item, events, "settlement")
                # Return the same terminal round marked as replayed.
                return self._payload(player_id, state, round_item, wager=wager_event, settlement=settlement_event, replayed=True)
            # Preserve the actionable state for clean insufficient-funds rollback.
            prior_state = copy.deepcopy(state)
            # Resolve the current intent count before adding decision movements.
            round_item = engine.get_round(state, round_id)
            # Record how many intents belong to the original deal.
            prior_intent_count = len(round_item.get("ledger_intents", []))
            # Prepare the terminal engine transition and deterministic new intents.
            engine.decide(state, round_id, decision, action_id, completed_at=self.clock())
            # Bind the decision fingerprint before any new wallet movement.
            state["requests"][action_id] = {"command": "decision", "round_id": round_id, "fingerprint": fingerprint}
            # Persist the decision, revealed result, and intents before reconciliation.
            self.repository.save(player_id, state)
            # Capture only movements introduced by this decision.
            new_intents = round_item.get("ledger_intents", [])[prior_intent_count:]
            # Reconcile Play debit then payout, or settle Fold without movement.
            try:
                # Apply or recover every prepared intent in stable order.
                events = self._reconcile_round(player_id, state, round_item)
            # Restore the decision only when its first movement never committed.
            except Exception:
                # Select the first decision-owned movement when one exists.
                first_new_intent = new_intents[0] if new_intents else None
                # A movement-free Fold can safely restore after persistence failure.
                committed = None if first_new_intent is None else self.ledger.find_intent(first_new_intent)
                # Restore the pre-decision document when no decision movement committed.
                if committed is None:
                    # Make the same action id safely retryable after funds or storage recover.
                    self.repository.save(player_id, prior_state)
                # Preserve pending state after a committed Play debit and re-raise.
                raise
            # Resolve the optional matching Play debit.
            wager_event = self._event_for_stage(state, round_item, events, "play_wager")
            # Resolve the optional aggregate payout credit.
            settlement_event = self._event_for_stage(state, round_item, events, "settlement")
            # Return the terminal round and current wallet state.
            return self._payload(player_id, state, round_item, wager=wager_event, settlement=settlement_event, replayed=False)
