"""Replay, ledger, reload, and session-bound controller tests for issue #84."""

# Import detached-copy support to model persistence boundaries accurately.
import copy
# Import unittest for dependency-free focused controller coverage.
import unittest

# Import the isolated API adapter and state factory under test.
from casino.games.red_dog import api, engine
# Import the shared router to prove authenticated context precedence.
from casino.router import Router
# Import public conflict and lookup errors for fail-closed assertions.
from casino.errors import ConflictError, NotFoundError


# Simulate player-scoped persistence without writing repository or user data.
class MemoryRepository:
    # Seed any number of player documents with detached state.
    def __init__(self, documents=None):
        # Copy every fixture so tests cannot mutate caller-owned objects.
        self.documents = copy.deepcopy(documents or {})
        # Count explicit saves for reload-safety diagnostics.
        self.save_count = 0

    # Load one detached player document.
    def load(self, player_id: str) -> dict:
        # Return an independent state copy or a fresh default for unknown players.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id: str, state: dict) -> None:
        # Persist a copy so later mutation requires another explicit save.
        self.documents[player_id] = copy.deepcopy(state)
        # Record the persistence boundary for focused diagnostics.
        self.save_count += 1


# Record append-only ledger events and support verified action recovery.
class RecordingLedger:
    # Start with no events and optional failure injection.
    def __init__(self, fail_transaction_type=None):
        # Retain committed events in append order.
        self.events = []
        # Fail the selected movement before it commits when requested.
        self.fail_transaction_type = fail_transaction_type

    # Calculate the signed event amount for one prepared intent.
    @staticmethod  # Keep event signing independent of adapter instances.
    def signed_amount(intent: dict) -> float:  # Return the ledger-signed amount for this test intent.
        # Represent debits as negative and credits as positive ledger values.
        return round(-intent["amount"] if intent["direction"] == "debit" else intent["amount"], 2)

    # Find one exact previously committed movement for crash recovery.
    def find_action(self, player_id: str, intent: dict):
        # Search newest-first for this player and stable game action id.
        for event in reversed(self.events):
            # Read structured recovery details from the recorded row.
            details = event.get("details") or {}
            # Skip events for another prepared movement.
            if details.get("red_dog_action_id") != intent["action_id"] or event["player_id"] != player_id:
                # Continue through older append-only rows.
                continue
            # Require the immutable transaction fingerprint to match exactly.
            matches = event["game"] == intent["game"] and event["round_id"] == intent["round_id"] and event["transaction_type"] == intent["transaction_type"] and event["amount"] == self.signed_amount(intent)
            # Fail the test adapter like production when one action id conflicts.
            if not matches:
                # Surface the same public conflict class as the production adapter.
                raise ConflictError("Recorded Red Dog action conflicts with its intent")
            # Return a detached committed event.
            return copy.deepcopy(event)
        # Report no prior movement when reconciliation must transact.
        return None

    # Append one prepared debit or credit as a ledger-shaped event.
    def transact(self, intent: dict) -> dict:
        # Inject an ordinary pre-commit failure for rollback coverage.
        if intent["transaction_type"] == self.fail_transaction_type:
            # Raise without appending any durable event.
            raise RuntimeError("Injected ledger rejection")
        # Build the immutable append-only event.
        event = {
            "ledger_id": f"ledger-{len(self.events) + 1}",  # Identify append order.
            "player_id": intent["player_id"],  # Preserve session ownership.
            "game": intent["game"],  # Preserve module ownership.
            "round_id": intent["round_id"],  # Preserve round correlation.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "amount": self.signed_amount(intent),  # Preserve signed token movement.
            "details": copy.deepcopy(intent["details"]),  # Preserve recovery metadata.
        }
        # Append exactly once to model the shared ledger.
        self.events.append(event)
        # Return a detached event to the controller.
        return copy.deepcopy(event)


# Verify controller settlement and authenticated route behavior without shared state.
class RedDogApiTests(unittest.TestCase):
    # Build a player state whose opening produces a normal spread.
    def spread_state(self, third="5H") -> dict:
        # Start from the production player-scoped schema.
        state = engine.default_state()
        # Arrange three, seven, then the requested third result in draw order.
        state["shoe"] = [third, "7D", "3C"]
        # Assign stable shoe telemetry for response assertions.
        state["shoe_id"] = "fixture-spread"
        # Return the deterministic document.
        return state

    # Build a player state whose pair produces an automatic three-of-a-kind win.
    def triple_state(self) -> dict:
        # Start from the production player-scoped schema.
        state = engine.default_state()
        # Arrange three matching ranks in draw order.
        state["shoe"] = ["7H", "7D", "7C"]
        # Assign stable shoe telemetry for response assertions.
        state["shoe_id"] = "fixture-triple"
        # Return the deterministic document.
        return state

    # Build a controller whose clock, ids, persistence, ledger, and player reads are deterministic.
    def controller(self, repository, recording_ledger):
        # Retain one counter for unique server identifiers.
        counter = {"value": 0}

        # Return stable distinct ids for round and shoe calls.
        def id_factory(prefix):
            # Increment before formatting the next identity.
            counter["value"] += 1
            # Return a route-safe server identifier.
            return f"{prefix}_test_{counter['value']}"

        # Construct the controller with no production data or wallet dependency.
        return api.RedDogController(
            # Persist only in detached in-memory player documents.
            repository=repository,
            # Record every wallet intent instead of touching shared balances.
            ledger_adapter=recording_ledger,
            # Return a deterministic read-only player snapshot.
            player_reader=lambda player_id: {"player_id": player_id, "balance": 1000.0},
            # Freeze lifecycle timestamps for exact state comparisons.
            clock=lambda: "2026-07-14T00:00:00.000Z",
            # Allocate predictable route-safe server ids.
            id_factory=id_factory,
        )

    # Confirm an exact opening retry reuses cards and one ante debit.
    def test_start_retry_is_exactly_once_and_conflicting_wager_fails(self):
        # Seed only the authenticated player's deterministic spread.
        repository = MemoryRepository({"bound-player": self.spread_state()})
        # Record every requested wallet movement.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Execute the original opening command.
        first = controller.start_round("bound-player", 10, "deal-action-001")
        # Replay the same action id and normalized wager.
        replay = controller.start_round("bound-player", 10.0, "deal-action-001")
        # Verify one ante debit total.
        self.assertEqual([-10.0], [event["amount"] for event in recording_ledger.events])
        # Verify both responses identify the same cards and round.
        self.assertEqual(first["round"], replay["round"])
        # Verify the replay flag distinguishes the second response.
        self.assertTrue(replay["replayed"])
        # Reject the same action id with a different money payload.
        with self.assertRaises(ConflictError):
            # Attempt conflicting reuse without another ledger movement.
            controller.start_round("bound-player", 20, "deal-action-001")
        # Confirm conflict handling left the one original debit unchanged.
        self.assertEqual(1, len(recording_ledger.events))

    # Confirm a matching raise debits once and credits all stakes once.
    def test_raise_retry_preserves_ledger_order_and_result(self):
        # Seed a spread-three win for the authenticated player.
        repository = MemoryRepository({"bound-player": self.spread_state("5H")})
        # Record ante, raise, and payout movements.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Deal the decision-ready opening.
        started = controller.start_round("bound-player", 10, "deal-action-002")
        # Resolve through a matching raise once.
        first = controller.decide("bound-player", started["round"]["round_id"], "raise", "raise-action-001")
        # Replay the exact same decision command.
        replay = controller.decide("bound-player", started["round"]["round_id"], "raise", "raise-action-001")
        # Verify ante, matching raise, and returned credit remain in order.
        self.assertEqual(["RED_DOG_WAGER_DEBIT", "RED_DOG_RAISE_DEBIT", "RED_DOG_PAYOUT_CREDIT"], [event["transaction_type"] for event in recording_ledger.events])
        # Verify spread-three odds return sixty tokens on two ten-token stakes.
        self.assertEqual([-10.0, -10.0, 60.0], [event["amount"] for event in recording_ledger.events])
        # Verify replay returns the identical terminal round.
        self.assertEqual(first["round"], replay["round"])
        # Reject reuse of the decision id for the opposite command.
        with self.assertRaises(ConflictError):
            # Attempt a conflicting call fingerprint.
            controller.decide("bound-player", started["round"]["round_id"], "call", "raise-action-001")

    # Confirm state reload rebuilds lost markers from append-only ledger proof.
    def test_reload_recovers_committed_events_without_duplicates(self):
        # Seed an automatic three-of-a-kind result.
        repository = MemoryRepository({"bound-player": self.triple_state()})
        # Record the ante and payout rows.
        recording_ledger = RecordingLedger()
        # Execute the automatic round through one controller instance.
        controller = self.controller(repository, recording_ledger)
        # Commit wager and returned credit once.
        controller.start_round("bound-player", 5, "deal-action-003")
        # Simulate a crash that lost only game-state ledger markers.
        repository.documents["bound-player"]["ledger_actions"] = {}
        # Construct a fresh controller to model process reload.
        reloaded = self.controller(repository, recording_ledger)
        # Read state so prepared movements reconcile from ledger proof.
        payload = reloaded.state("bound-player")
        # Verify reload did not append duplicate movements.
        self.assertEqual(2, len(recording_ledger.events))
        # Verify public settlement reports both durable actions complete.
        self.assertEqual({"required_actions": 2, "committed_actions": 2, "complete": True}, payload["state"]["rounds"][0]["settlement"])

    # Confirm an ordinary rejected raise restores the actionable state and shoe.
    def test_rejected_raise_rolls_back_before_any_new_commit(self):
        # Seed a spread decision whose third card would otherwise win.
        original_state = self.spread_state("5H")
        # Persist a detached fixture for the player.
        repository = MemoryRepository({"bound-player": original_state})
        # Reject only the matching raise debit after allowing the ante.
        recording_ledger = RecordingLedger(fail_transaction_type="RED_DOG_RAISE_DEBIT")
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Commit the opening ante and decision state.
        started = controller.start_round("bound-player", 10, "deal-action-004")
        # Preserve the shoe after the two opening cards.
        shoe_before_raise = copy.deepcopy(repository.documents["bound-player"]["shoe"])
        # Attempt the rejected matching raise.
        with self.assertRaises(RuntimeError):
            # Require rollback when no new decision movement committed.
            controller.decide("bound-player", started["round"]["round_id"], "raise", "raise-action-002")
        # Reload the restored player document.
        restored = repository.load("bound-player")
        # Verify the third card was restored to the persisted shoe.
        self.assertEqual(shoe_before_raise, restored["shoe"])
        # Verify the round still awaits the player's decision.
        self.assertEqual("raise_decision", restored["rounds"][started["round"]["round_id"]]["phase"])
        # Verify only the original ante is durable.
        self.assertEqual(["RED_DOG_WAGER_DEBIT"], [event["transaction_type"] for event in recording_ledger.events])

    # Confirm hostile caller ids cannot override an authenticated session binding.
    def test_router_session_binding_overrides_body_and_query_player_ids(self):
        # Seed only the authenticated player's state.
        repository = MemoryRepository({"bound-player": self.spread_state()})
        # Record the wallet owner selected by the route.
        recording_ledger = RecordingLedger()
        # Register the isolated API on a focused router.
        router = Router()
        # Attach routes with an injected controller and no shared registration.
        api.register(router, self.controller(repository, recording_ledger))
        # Dispatch a hostile body and query id under a trusted bound context.
        payload = router.dispatch("POST", "/api/v1/games/red-dog/rounds?player_id=query-attacker", {"player_id": "body-attacker", "wager": 10, "action_id": "deal-action-005"}, {"bound_player_id": "bound-player", "user": {"player_id": "bound-player"}})
        # Verify the response belongs only to the authenticated player.
        self.assertEqual("bound-player", payload["player"]["player_id"])
        # Verify every ledger movement uses the authenticated player.
        self.assertTrue(all(event["player_id"] == "bound-player" for event in recording_ledger.events))
        # Verify no attacker-owned document was created.
        self.assertNotIn("body-attacker", repository.documents)
        # Verify no query-selected document was created.
        self.assertNotIn("query-attacker", repository.documents)

    # Confirm another session cannot resolve or act on a bound player's round id.
    def test_round_state_is_private_between_players(self):
        # Seed separate deterministic documents for two authenticated players.
        repository = MemoryRepository({"player-one": self.spread_state(), "player-two": self.spread_state("6H")})
        # Record movements for both players independently.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Start one player-one round.
        started = controller.start_round("player-one", 10, "deal-action-006")
        # Reject player two's attempt to call player one's round id.
        with self.assertRaises(NotFoundError):
            # Use a distinct id so only state isolation determines the failure.
            controller.decide("player-two", started["round"]["round_id"], "call", "call-action-002")
        # Verify player two received no ledger movement.
        self.assertFalse(any(event["player_id"] == "player-two" for event in recording_ledger.events))


# Run this focused suite when invoked directly by a bounded worker.
if __name__ == "__main__":
    # Execute unittest's standard result handling.
    unittest.main()
