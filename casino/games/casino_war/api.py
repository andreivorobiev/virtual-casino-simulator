# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-compatible Casino War API adapter with replay-safe ledger settlement.

Requirements: CORE-009, CORE-011, CW-006, CW-007, LEDGER-005, LEDGER-006,
LEDGER-007, LEDGER-023, SESSION-003, SESSION-004, and planned SESSION-005 from #81.
"""

# Import deep-copy support so failed prepared decisions can restore prior state.
import copy
# Import bounded player-scoped serialization so unrelated wallets can proceed concurrently.
from casino.core.player_locks import player_action_lock
# Import action-id validation for bounded idempotency keys.
import re

# Import the shared player reader without a game-owned wallet mutation boundary.
from casino.core import players
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped state persistence for reload-safe provider-owned transitions.
from casino.core.state_store import load_player_game_state, update_player_game_state
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


# Persist and load player-scoped Casino War state through the shared store.
class StateRepository:
    # Load one session player's game document.
    def load(self, player_id: str) -> dict:
        # Delegate schema migration and provider selection to the shared state store.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Apply one state transition while the selected provider owns its cross-process boundary.
    def update(self, player_id: str, mutator) -> dict:
        # Delegate latest-state loading, rollback, and publication to the shared atomic helper.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state)


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

    # Replace one caller snapshot with the complete authoritative provider result. (CW-007)
    @staticmethod
    def _refresh_state(state: dict, authoritative: dict) -> None:
        # Remove every stale top-level field from the caller-owned snapshot.
        state.clear()
        # Preserve object identity while adopting the provider-owned current document.
        state.update(authoritative)

    # Capture the exact shoe fields changed by round preparation. (CW-007)
    @staticmethod
    def _shoe_snapshot(state: dict) -> dict:
        # Return detached values so later engine mutation cannot alter the rollback boundary.
        return {key: copy.deepcopy(state.get(key)) for key in ("shoe", "shoe_id", "shoes_dealt")}

    # Restore the exact prepared shoe fields after a proven pre-ledger failure. (CW-007)
    @staticmethod
    def _restore_shoe(state: dict, snapshot: dict) -> None:
        # Replace only the three action-owned shoe fields while preserving every sibling key.
        for key, value in snapshot.items():
            # Publish a detached value so the marker cannot alias live provider state.
            state[key] = copy.deepcopy(value)

    # Prepare one initial round against the provider-owned latest document. (CW-007)
    def _prepare_start(self, player_id: str, state: dict, wager, action_id: str) -> tuple[dict, bool, dict | None]:
        # Retain the selected round, ownership, and rollback marker outside the callback.
        selected = {}

        # Allocate cards, request mapping, and ledger intents within one atomic state transition.
        def prepare(current: dict) -> dict:
            # Resolve duplicate action identity under the same provider lock as preparation.
            previous = current.setdefault("requests", {}).get(action_id)
            # Reuse the exact prepared round when another process already won this action.
            if previous is not None:
                # Reject reuse of one action id for a decision command.
                if previous.get("command") != "start_round":
                    # Keep idempotency keys one-command-only across every route.
                    raise ValidationError("Casino War action_id was already used for another command")
                # Resolve the established start-round replay mapping.
                round_item = engine.get_round(current, previous["round_id"])
                # Publish the winner's exact round identity to the caller.
                selected.update({"round_id": round_item["round_id"], "created": False, "marker": None})
                # Leave the provider-owned document unchanged on replay.
                return current
            # Capture the action-owned shoe fields before engine mutation.
            before_shoe = self._shoe_snapshot(current)
            # Capture bounded history before the engine may prune its oldest settled round.
            before_round_order = list(current.get("round_order", []))
            # Retain only history bodies that this preparation could prune.
            before_rounds = {round_id: copy.deepcopy(current["rounds"][round_id]) for round_id in before_round_order if round_id in current.get("rounds", {})}
            # Create the round and its stable ordered ledger intents against latest state.
            round_item = engine.start_round(current, player_id, wager, action_id)
            # Build the exact durable request mapping used by replay and rollback.
            request_entry = {"command": "start_round", "round_id": round_item["round_id"]}
            # Publish the mapping before any wallet movement can occur.
            current["requests"][action_id] = request_entry
            # Bind rollback to exact action-owned before/after state.
            marker = {"kind": "start", "action_id": action_id, "round_id": round_item["round_id"], "request": copy.deepcopy(request_entry), "before_shoe": before_shoe, "after_shoe": self._shoe_snapshot(current), "before_round_order": before_round_order, "after_round_order": list(current.get("round_order", [])), "pruned_rounds": {round_id: before_rounds[round_id] for round_id in before_rounds if round_id not in current.get("rounds", {})}, "after_round": copy.deepcopy(round_item)}
            # Return detached selection evidence after the provider transition commits.
            selected.update({"round_id": round_item["round_id"], "created": True, "marker": marker})
            # Publish the complete latest document atomically.
            return current

        # Commit preparation through the provider-owned state boundary.
        prepared = self.repository.update(player_id, prepare)
        # Refresh the caller snapshot with every sibling update preserved.
        self._refresh_state(state, prepared)
        # Resolve the exact selected round from the authoritative result.
        round_item = engine.get_round(state, selected["round_id"])
        # Return round, creation ownership, and rollback evidence.
        return round_item, selected["created"], selected["marker"]

    # Prepare one surrender or war decision against the latest document. (CW-007)
    def _prepare_decision(self, player_id: str, state: dict, round_id: str, decision: str, action_id: str) -> tuple[dict, bool, dict | None]:
        # Retain selection evidence outside the provider callback.
        selected = {}

        # Apply one exact decision while the provider owns the current player document.
        def prepare(current: dict) -> dict:
            # Resolve duplicate action identity under the same lock as the decision transition.
            previous = current.setdefault("requests", {}).get(action_id)
            # Reuse or reject an already claimed action key deterministically.
            if previous is not None:
                # Reject reuse for another decision or round exactly as the existing API did.
                if previous.get("command") != decision or previous.get("round_id") != round_id:
                    # Keep idempotency keys one-command-only.
                    raise ValidationError("Casino War action_id was already used for another command")
                # Resolve the winner's exact already-prepared round.
                round_item = engine.get_round(current, round_id)
                # Return replay ownership without mutating current state.
                selected.update({"created": False, "marker": None})
                # Leave the provider-owned document unchanged.
                return current
            # Capture the exact pre-decision round for bounded rollback.
            before_round = copy.deepcopy(engine.get_round(current, round_id))
            # Capture shoe fields because only war consumes more cards.
            before_shoe = self._shoe_snapshot(current)
            # Prepare the selected pure engine transition.
            if decision == "surrender":
                # Publish the half-wager return intent.
                round_item = engine.surrender(current, round_id, action_id)
            # Handle the only other supported decision.
            elif decision == "war":
                # Publish the matching wager, dealt cards, and settlement intent.
                round_item = engine.go_to_war(current, round_id, action_id)
            # Reject unexpected internal decision names.
            else:
                # Keep the controller's command vocabulary explicit.
                raise ValidationError("Casino War decision is invalid")
            # Build the exact durable request mapping used by replay and rollback.
            request_entry = {"command": decision, "round_id": round_id}
            # Publish the mapping before the first decision-owned movement can occur.
            current["requests"][action_id] = request_entry
            # Bind rollback to exact action-owned before/after state.
            marker = {"kind": "decision", "action_id": action_id, "round_id": round_id, "request": copy.deepcopy(request_entry), "before_shoe": before_shoe, "after_shoe": self._shoe_snapshot(current), "before_round": before_round, "after_round": copy.deepcopy(round_item)}
            # Retain creation ownership and rollback evidence.
            selected.update({"created": True, "marker": marker})
            # Publish the complete latest document atomically.
            return current

        # Commit the decision through the provider-owned state boundary.
        prepared = self.repository.update(player_id, prepare)
        # Refresh the caller snapshot with every sibling update preserved.
        self._refresh_state(state, prepared)
        # Resolve the exact selected round from the authoritative result.
        round_item = engine.get_round(state, round_id)
        # Return round, creation ownership, and rollback evidence.
        return round_item, selected["created"], selected["marker"]

    # Reverse only one exact prepared action after authoritative ledger absence. (CW-007)
    def _rollback_prepared(self, player_id: str, state: dict, marker: dict) -> None:
        # Define a compare-and-restore transition against the latest provider document.
        def rollback(current: dict) -> dict:
            # Require the exact request mapping so another action is never erased.
            if current.get("requests", {}).get(marker["action_id"]) != marker["request"]:
                # Preserve divergent current state for explicit recovery.
                raise ValidationError("Casino War prepared state requires operator recovery")
            # Resolve the current action-owned round without inventing missing state.
            current_round = engine.get_round(current, marker["round_id"])
            # Require the exact prepared round and shoe before restoring anything.
            if current_round != marker["after_round"] or self._shoe_snapshot(current) != marker["after_shoe"]:
                # Refuse to overwrite a committed or divergent successor transition.
                raise ValidationError("Casino War prepared state requires operator recovery")
            # Roll back an initial round by removing only its exact state and request entry.
            if marker["kind"] == "start":
                # Require the exact action-owned ordering result before restoring bounded history.
                if current.get("round_order", []) != marker["after_round_order"]:
                    # Preserve malformed or aliased history for operator recovery.
                    raise ValidationError("Casino War prepared state requires operator recovery")
                # Remove only this action-owned round body.
                current["rounds"].pop(marker["round_id"])
                # Restore only history bodies pruned by this exact preparation.
                current["rounds"].update(copy.deepcopy(marker["pruned_rounds"]))
                # Restore the exact bounded order that preceded preparation.
                current["round_order"] = list(marker["before_round_order"])
            # Roll back a decision by restoring its exact pre-decision round.
            elif marker["kind"] == "decision":
                # Replace only the action-owned round while preserving sibling rounds.
                current["rounds"][marker["round_id"]] = copy.deepcopy(marker["before_round"])
            # Reject malformed internal marker kinds before mutation completes.
            else:
                # Keep unknown state intact for operator-led recovery.
                raise ValidationError("Casino War prepared state requires operator recovery")
            # Restore only the shoe fields changed by this action.
            self._restore_shoe(current, marker["before_shoe"])
            # Release only the exact request mapping after state restoration.
            current["requests"].pop(marker["action_id"], None)
            # Return the complete latest document for atomic publication.
            return current

        # Commit bounded rollback and refresh the caller's authoritative snapshot.
        self._refresh_state(state, self.repository.update(player_id, rollback))

    # Save one committed ledger event marker into player state.
    def _mark_committed(self, player_id: str, state: dict, intent: dict, event: dict) -> None:
        # Define a merge-only transition so a sibling process cannot lose another committed marker.
        def record(current: dict) -> dict:
            # Record only stable audit identifiers and not balance snapshots in game state.
            current.setdefault("ledger_actions", {})[intent["action_id"]] = {
                "ledger_id": event.get("ledger_id"),  # Link to the append-only ledger event.
                "transaction_type": intent["transaction_type"],  # Preserve movement type.
                "round_id": intent["round_id"],  # Preserve round association.
            }
            # Return the complete latest state for provider-owned publication.
            return current
        # Persist the marker against the latest document under the cross-process boundary.
        committed = self.repository.update(player_id, record)
        # Remove the caller's stale top-level entries before copying the committed document.
        state.clear()
        # Refresh the caller's working snapshot without retaining a provider-owned object.
        state.update(committed)

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
            # Capture the stable round identity before refreshing the caller's working snapshot.
            round_id = round_item["round_id"]
            # Define a latest-document terminal transition that preserves sibling state updates.
            def settle(current: dict) -> dict:
                # Resolve the same prepared round from the provider-owned latest state.
                current_round = engine.get_round(current, round_id)
                # Transition the public phase after successful ordered reconciliation.
                current_round["phase"] = "settled"
                # Return the complete latest state for provider-owned publication.
                return current
            # Persist the terminal phase under the cross-process state boundary.
            settled = self.repository.update(player_id, settle)
            # Remove stale top-level entries before copying the terminal provider result.
            state.clear()
            # Refresh the caller snapshot so its response sees every concurrent preserved field.
            state.update(settled)
            # Resolve the refreshed terminal round for the return value.
            round_item = engine.get_round(state, round_id)
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
        with player_action_lock(player_id):
            # Load the session-bound player document.
            state = self.repository.load(player_id)
            # Recover only actions the player already requested before interruption.
            self._recover(player_id, state)
            # Return the reload-safe public state.
            return self._payload(player_id, state)

    # Deal one initial comparison under a replay-safe client action id.
    def start_round(self, player_id: str, wager, action_id: str) -> dict:
        # Serialize preparation and reconciliation for duplicate local requests.
        with player_action_lock(player_id):
            # Load the session-bound player document.
            state = self.repository.load(player_id)
            # Prepare or adopt one exact round against the provider-owned latest document.
            round_item, created, marker = self._prepare_start(player_id, state, wager, action_id)
            # Recover a racing or interrupted winner without drawing or debiting again.
            if not created:
                # Reconcile the winner's exact prepared movement sequence.
                round_item = self._reconcile_round(player_id, state, round_item)
                # Return the same logical round and current wallet state.
                return self._payload(player_id, state, round_item)
            # Reconcile the prepared ante and any immediate settlement.
            try:
                # Apply every required movement in engine order.
                round_item = self._reconcile_round(player_id, state, round_item)
            # Restore clean state only when the first ledger movement never committed.
            except Exception:
                # Read the first stable ante action for failure classification.
                ante = round_item["ledger_intents"][0]
                # Roll back the prepared round when no append-only ledger event exists.
                if self.ledger.find_action(player_id, ante["action_id"]) is None:
                    # Restore only the exact action-owned round, request, and shoe mutation.
                    self._rollback_prepared(player_id, state, marker)
                # Re-raise the original domain or storage error.
                raise
            # Return the settled or decision-ready round.
            return self._payload(player_id, state, round_item)

    # Execute surrender or war once under a replay-safe client action id.
    def decide(self, player_id: str, round_id: str, decision: str, action_id: str) -> dict:
        # Serialize preparation and reconciliation for duplicate local decisions.
        with player_action_lock(player_id):
            # Load the session-bound player document.
            state = self.repository.load(player_id)
            # Prepare or adopt one exact decision against the provider-owned latest document.
            round_item, created, marker = self._prepare_decision(player_id, state, round_id, decision, action_id)
            # Recover a racing or interrupted winner without repeating cards or movement.
            if not created:
                # Reconcile the winner's exact prepared movement sequence.
                round_item = self._reconcile_round(player_id, state, round_item)
                # Return the same logical decision result.
                return self._payload(player_id, state, round_item)
            # Identify the first new movement created by this decision.
            first_new_intent = next(intent for intent in round_item["ledger_intents"] if intent["action_id"].startswith(f"cw:{action_id}:"))
            # Reconcile the prepared movement sequence.
            try:
                # Apply the war debit before settlement or the surrender credit once.
                round_item = self._reconcile_round(player_id, state, round_item)
            # Restore the tie decision only when no new movement committed.
            except Exception:
                # Check the append-only ledger in case state saving was interrupted.
                if self.ledger.find_action(player_id, first_new_intent["action_id"]) is None:
                    # Restore only the exact action-owned decision, request, and shoe mutation.
                    self._rollback_prepared(player_id, state, marker)
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
