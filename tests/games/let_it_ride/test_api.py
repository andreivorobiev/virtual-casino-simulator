# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Replay, ledger, reload, session, and atomic-state tests for issues #134 and #841."""

# Import detached-copy support to model persistence boundaries accurately.
import copy
# Import unittest for dependency-free focused controller coverage.
import unittest

# Import the isolated API adapter and state factory under test.
from casino.games.let_it_ride import api, engine
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

    # Apply one callback against the latest provider-owned document.
    def update(self, player_id: str, mutator) -> dict:
        # Load a detached current document before entering the callback.
        current = self.load(player_id)
        # Let the game replace only fields it owns.
        updated = mutator(current)
        # Persist a detached complete provider result.
        self.documents[player_id] = copy.deepcopy(updated)
        # Record the provider-owned publication boundary.
        self.save_count += 1
        # Return another detached copy like the shared provider helper.
        return copy.deepcopy(updated)


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
            # Skip events for another prepared movement or another player.
            if details.get("let_it_ride_action_id") != intent["action_id"] or event["player_id"] != player_id:
                # Continue through older append-only rows.
                continue
            # Require the immutable transaction fingerprint to match exactly.
            matches = event["game"] == intent["game"] and event["round_id"] == intent["round_id"] and event["transaction_type"] == intent["transaction_type"] and event["amount"] == self.signed_amount(intent)
            # Fail the test adapter like production when one action id conflicts.
            if not matches:
                # Surface the same public conflict class as the production adapter.
                raise ConflictError("Recorded Let It Ride action conflicts with its intent")
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
class LetItRideApiTests(unittest.TestCase):
    # Build a player state whose final hand is a pair of tens.
    def pair_tens_state(self) -> dict:
        # Start from the production player-scoped schema.
        state = engine.default_state()
        # Arrange pop-order cards as player tens, kicker, and two community cards.
        state["shoe"] = ["9H", "4S", "3C", "10D", "10H"]
        # Assign stable deck telemetry for response assertions.
        state["shoe_id"] = "fixture-pair-tens"
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
        return api.LetItRideController(
            repository=repository,  # Persist only in detached in-memory player documents.
            ledger_adapter=recording_ledger,  # Record every wallet intent instead of touching shared balances.
            player_reader=lambda player_id: {"player_id": player_id, "balance": 1000.0},  # Return a deterministic read-only player snapshot.
            clock=lambda: "2026-07-14T00:00:00.000Z",  # Freeze lifecycle timestamps for exact state comparisons.
            id_factory=id_factory,  # Allocate predictable route-safe server ids.
        )

    # Refuse untracked publication before provider storage can observe a callback.
    def test_atomic_publication_requires_a_loaded_baseline(self):
        # Build isolated repository and ledger ports.
        repository = MemoryRepository()
        # Construct the controller through the normal focused seam.
        controller = self.controller(repository, RecordingLedger())
        # Reject a detached default that never passed through the controller loader.
        with self.assertRaisesRegex(ConflictError, "missing its atomic baseline"):
            # Attempt direct publication without a provider read.
            controller._save("bound-player", engine.default_state())
        # Prove the refusal occurred before creating provider state.
        self.assertNotIn("bound-player", repository.documents)

    # Accept one exact duplicate result while preserving provider-owned siblings.
    def test_atomic_publication_is_idempotent_and_preserves_siblings(self):
        # Build isolated repository and ledger ports.
        repository = MemoryRepository()
        # Construct the controller through the normal focused seam.
        controller = self.controller(repository, RecordingLedger())
        # Load one tracked empty state through the controller boundary.
        state = controller._load("bound-player")
        # Publish the canonical empty result once to establish durable bytes.
        controller._save("bound-player", state)
        # Add unrelated metadata after the caller's baseline advances.
        repository.documents["bound-player"]["atomic_markers"] = ["sibling"]
        # Publish the exact same game-owned result through idempotent comparison.
        controller._save("bound-player", state)
        # Read the complete provider-authoritative document after both updates.
        persisted = repository.load("bound-player")
        # Preserve the unrelated sibling while keeping operation metadata private.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Reject internal optimistic metadata from durable state bytes.
        self.assertNotIn("_let_it_ride_atomic_baseline", persisted)

    # Reject one stale writer after a competing game-owned publication wins.
    def test_atomic_publication_rejects_stale_game_state(self):
        # Build isolated repository and ledger ports.
        repository = MemoryRepository()
        # Construct the controller through the normal focused seam.
        controller = self.controller(repository, RecordingLedger())
        # Load two independent snapshots before either writer publishes.
        first = controller._load("bound-player")
        # Retain one competing snapshot over the same baseline.
        stale = controller._load("bound-player")
        # Give the first writer one unique terminal record.
        first["round_order"] = ["winner"]
        # Publish the first writer against the shared baseline.
        controller._save("bound-player", first)
        # Add one unrelated sibling beside the provider winner.
        repository.documents["bound-player"]["atomic_markers"] = ["sibling"]
        # Give the stale writer a distinct result over the old baseline.
        stale["round_order"] = ["loser"]
        # Reject the stale replacement rather than merging incompatible game state.
        with self.assertRaisesRegex(ConflictError, "state changed during this action"):
            # Attempt to publish the stale owned snapshot.
            controller._save("bound-player", stale)
        # Read the authoritative provider result after the conflict.
        persisted = repository.load("bound-player")
        # Retain only the winner and the unrelated sibling.
        self.assertEqual((["winner"], ["sibling"]), (persisted["round_order"], persisted["atomic_markers"]))

    # Prevent rejected opening cleanup from erasing a concurrent game-state winner.
    def test_rejected_wager_rollback_cannot_erase_concurrent_winner(self):
        # Seed a deterministic source document for the opening action.
        repository = MemoryRepository({"bound-player": self.pair_tens_state()})
        # Build a ledger adapter whose first movement publishes a competing winner.
        recording_ledger = RecordingLedger()
        # Construct the controller before installing the bounded failing seam.
        controller = self.controller(repository, recording_ledger)

        # Publish one provider winner before rejecting the fake ledger movement.
        def fail_after_concurrent_update(_intent):
            # Define the provider-current competing mutation.
            def publish_winner(current):
                # Mark the prepared round with one concurrent diagnostic field.
                current["rounds"][current["round_order"][-1]]["atomic_winner"] = True
                # Publish one unrelated sibling beside the winning game state.
                current["atomic_markers"] = ["provider-winner"]
                # Return the complete current document.
                return current

            # Commit the concurrent winner before the attempted rollback.
            repository.update("bound-player", publish_winner)
            # Fail before any append-only fake ledger movement can commit.
            raise RuntimeError("injected pre-ledger wager failure")

        # Install only the bounded failing transaction seam.
        recording_ledger.transact = fail_after_concurrent_update
        # Surface the cleanup conflict because another writer owns prepared state.
        with self.assertRaisesRegex(ConflictError, "state changed during this action"):
            # Attempt one money-bearing deal whose rollback is now stale.
            controller.start_round("bound-player", 5, "atomic-rollback-0001")
        # Read the exact provider-authoritative state after rejected cleanup.
        persisted = repository.load("bound-player")
        # Resolve the concurrently preserved prepared round.
        winning_round = persisted["rounds"][persisted["round_order"][-1]]
        # Preserve the concurrent marker and unrelated sibling.
        self.assertEqual((True, ["provider-winner"]), (winning_round["atomic_winner"], persisted["atomic_markers"]))
        # Prove the failure occurred before any wallet movement.
        self.assertEqual([], recording_ledger.events)

    # Confirm an exact opening retry reuses cards and one three-unit debit.
    def test_start_retry_is_exactly_once_and_conflicting_wager_fails(self):
        # Seed only the authenticated player's deterministic hand.
        repository = MemoryRepository({"bound-player": self.pair_tens_state()})
        # Record every requested wallet movement.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Execute the original opening command.
        first = controller.start_round("bound-player", 5, "deal-action-001")
        # Replay the same action id and normalized wager.
        replay = controller.start_round("bound-player", 5.0, "deal-action-001")
        # Verify one three-unit debit total.
        self.assertEqual([-15.0], [event["amount"] for event in recording_ledger.events])
        # Verify both responses identify the same cards and round.
        self.assertEqual(first["round"], replay["round"])
        # Verify the replay flag distinguishes the second response.
        self.assertTrue(replay["replayed"])
        # Reject the same action id with a different money payload.
        with self.assertRaises(ConflictError):
            # Attempt conflicting reuse without another ledger movement.
            controller.start_round("bound-player", 10, "deal-action-001")
        # Confirm conflict handling left the one original debit unchanged.
        self.assertEqual(1, len(recording_ledger.events))

    # Confirm pull and ride decisions settle exactly once in ledger order.
    def test_decision_retry_preserves_refund_and_payout_order(self):
        # Seed a qualifying pair-tens hand for the authenticated player.
        repository = MemoryRepository({"bound-player": self.pair_tens_state()})
        # Record opening wager, pull refund, and final payout.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Deal the first decision state.
        started = controller.start_round("bound-player", 5, "deal-action-002")
        # Pull one eligible wager before the first community card.
        controller.decide("bound-player", started["round"]["round_id"], "first", "pull", "pull-action-001")
        # Let the remaining wagers ride through final settlement.
        first = controller.decide("bound-player", started["round"]["round_id"], "second", "ride", "ride-action-001")
        # Replay the exact same second decision command.
        replay = controller.decide("bound-player", started["round"]["round_id"], "second", "ride", "ride-action-001")
        # Verify wager debit, refund credit, and payout credit remain in order.
        self.assertEqual(["LET_IT_RIDE_WAGER_DEBIT", "LET_IT_RIDE_REFUND_CREDIT", "LET_IT_RIDE_PAYOUT_CREDIT"], [event["transaction_type"] for event in recording_ledger.events])
        # Verify the exact signed movement amounts.
        self.assertEqual([-15.0, 5.0, 20.0], [event["amount"] for event in recording_ledger.events])
        # Verify replay returns the identical terminal round.
        self.assertEqual(first["round"], replay["round"])
        # Reject reuse of the decision id for the opposite decision.
        with self.assertRaises(ConflictError):
            # Attempt a conflicting second-decision fingerprint.
            controller.decide("bound-player", started["round"]["round_id"], "second", "pull", "ride-action-001")

    # Confirm state reload rebuilds lost markers from append-only ledger proof.
    def test_reload_recovers_committed_events_without_duplicates(self):
        # Seed a qualifying pair-tens hand.
        repository = MemoryRepository({"bound-player": self.pair_tens_state()})
        # Record the full settlement sequence.
        recording_ledger = RecordingLedger()
        # Execute the full round through one controller instance.
        controller = self.controller(repository, recording_ledger)
        # Commit opening wager and both decisions.
        started = controller.start_round("bound-player", 5, "deal-action-003")
        # Pull one wager.
        controller.decide("bound-player", started["round"]["round_id"], "first", "pull", "pull-action-002")
        # Settle the final result.
        controller.decide("bound-player", started["round"]["round_id"], "second", "ride", "ride-action-002")
        # Simulate a crash that lost only game-state ledger markers.
        repository.documents["bound-player"]["ledger_actions"] = {}
        # Construct a fresh controller to model process reload.
        reloaded = self.controller(repository, recording_ledger)
        # Read state so prepared movements reconcile from ledger proof.
        payload = reloaded.state("bound-player")
        # Verify reload did not append duplicate movements.
        self.assertEqual(3, len(recording_ledger.events))
        # Verify public settlement reports every durable action complete.
        self.assertEqual({"required_actions": 3, "committed_actions": 3, "complete": True}, payload["state"]["rounds"][0]["settlement"])

    # Confirm hostile caller ids cannot override an authenticated session binding.
    def test_router_session_binding_overrides_body_and_query_player_ids(self):
        # Seed only the authenticated player's state.
        repository = MemoryRepository({"bound-player": self.pair_tens_state()})
        # Record the wallet owner selected by the route.
        recording_ledger = RecordingLedger()
        # Register the isolated API on a focused router.
        router = Router()
        # Attach routes with an injected controller and no shared registration.
        api.register(router, self.controller(repository, recording_ledger))
        # Dispatch a hostile body and query id under a trusted bound context.
        payload = router.dispatch("POST", "/api/v1/games/let-it-ride/rounds?player_id=query-attacker", {"player_id": "body-attacker", "wager": 5, "action_id": "deal-action-004"}, {"bound_player_id": "bound-player", "user": {"player_id": "bound-player"}})
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
        repository = MemoryRepository({"player-one": self.pair_tens_state(), "player-two": self.pair_tens_state()})
        # Record movements for both players independently.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Start one player-one round.
        started = controller.start_round("player-one", 5, "deal-action-005")
        # Reject player two's attempt to act on player one's round id.
        with self.assertRaises(NotFoundError):
            # Use a distinct id so only state isolation determines the failure.
            controller.decide("player-two", started["round"]["round_id"], "first", "ride", "ride-action-003")
        # Verify player two received no ledger movement.
        self.assertFalse(any(event["player_id"] == "player-two" for event in recording_ledger.events))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Execute unittest's standard result handling.
    unittest.main()
