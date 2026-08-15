# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused session-binding and exactly-once API tests for issue #94."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import the current router so the game remains directly reachable without global registration.
from casino.router import Router
# Import only the isolated game API and engine under test.
from casino.games.multi_hand_video_poker import api, engine


# Provide an in-memory state and ledger adapter for isolated API tests.
class FakeCasino:
    # Initialize one authenticated player without touching repository data files.
    def __init__(self):
        # Store player-scoped game documents by player id.
        self.states = {}
        # Store committed ledger events in chronological order.
        self.events = []
        # Store fake balances only inside the ledger adapter.
        self.balances = {"session-player": 100.0}
        # Store a deterministic ledger id counter.
        self.sequence = 0

    # Load a deep copy of one player-scoped state document.
    def load(self, player_id):
        # Return persisted state or a fresh default without sharing references.
        return copy.deepcopy(self.states.get(player_id, engine.default_state()))

    # Apply one callback to the current player document like the production atomic seam.
    def update(self, player_id, mutator):
        # Give the mutator a detached copy so a rejected update cannot alter stored state.
        current = copy.deepcopy(self.states.get(player_id, engine.default_state()))
        # Apply the complete state transition inside this fake provider boundary.
        updated = mutator(current)
        # Persist and return independent copies like JSON serialization boundaries.
        self.states[player_id] = copy.deepcopy(updated)
        # Return a detached authoritative result to the game service.
        return copy.deepcopy(updated)

    # Create one fake ledger event through the same signed-amount semantics as core ledger.
    def transact(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Increment the deterministic event id counter.
        self.sequence += 1
        # Read the balance before applying the signed ledger amount.
        before = self.balances[player_id]
        # Apply the signed amount only inside this ledger test double.
        after = round(before + amount, 2)
        # Reject overdrafts like the production ledger provider.
        if after < 0:
            # Raise a simple assertion because this test never expects insufficient funds.
            raise AssertionError("fake ledger overdraft")
        # Store the balance after the ledger operation.
        self.balances[player_id] = after
        # Build the subset of public ledger fields used by the game service.
        event = {"ledger_id": f"led_{self.sequence}", "player_id": player_id, "amount": amount, "transaction_type": transaction_type, "game": game, "round_id": round_id, "details": details or {}}
        # Append the committed event for retry scans.
        self.events.append(event)
        # Return the committed event to the service.
        return event

    # Debit a positive wager through the fake signed ledger operation.
    def debit(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Delegate with a negative signed amount.
        return self.transact(player_id, -abs(amount), transaction_type, game, round_id, details)

    # Credit a positive payout through the fake signed ledger operation.
    def credit(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Delegate with a positive signed amount.
        return self.transact(player_id, abs(amount), transaction_type, game, round_id, details)

    # Read recent events using the production chronological shape.
    def read_ledger(self, player_id=None, limit=100):
        # Filter by player when requested and retain the newest bounded events.
        return [event for event in self.events if player_id is None or event["player_id"] == player_id][-limit:]

    # Return a read-only player snapshot for API payloads.
    def get_player(self, player_id):
        # Expose only the fields needed by this isolated game payload.
        return {"player_id": player_id, "balance": self.balances[player_id]}


# Verify direct route reachability, session binding, and ledger replay guards.
class MultiHandVideoPokerApiTests(unittest.TestCase):
    # Build an isolated router and service before every test.
    def setUp(self):
        # Create fresh in-memory state and ledger adapters.
        self.fake = FakeCasino()
        # Build the service with deterministic ids, timestamps, and cards.
        self.service = api.MultiHandVideoPokerService(repository=self.fake, debit=self.fake.debit, credit=self.fake.credit, read_ledger=self.fake.read_ledger, get_player=self.fake.get_player, clock=lambda: "2026-07-13T00:00:00.000Z", id_factory=lambda prefix: f"{prefix}_round", seed_factory=lambda request_id: f"api:{request_id}")
        # Create a game-local router without touching the global registry.
        self.router = Router()
        # Register only the issue #94 routes for focused tests.
        api.register(self.router, service=self.service)
        # Store the authenticated context used by current main and #81.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game request with the authenticated test context.
    def call(self, path, body=None, method="POST"):
        # Delegate to the current router so bound query identity is exercised.
        return self.router.dispatch(method, path, body or {}, context=dict(self.context))

    # Confirm a malicious body id cannot escape the router-bound session player.
    def test_session_binding_and_idempotent_wager(self):
        # Start one three-hand aggregate wager while supplying a stale body identity.
        first = self.call("/api/v1/games/multi-hand-video-poker/rounds", {"player_id": "other-player", "request_id": "retry-1", "hand_count": 3, "wager_per_hand": 2})
        # Simulate a crash after the ledger debit but before its state marker was durable.
        self.fake.states["session-player"]["active_round"]["wager_status"] = "pending"
        # Remove the cached event id so retry must recover from ledger history.
        self.fake.states["session-player"]["active_round"].pop("wager_ledger_id", None)
        # Replay the exact same request id and settings.
        second = self.call("/api/v1/games/multi-hand-video-poker/rounds", {"player_id": "other-player", "request_id": "retry-1", "hand_count": 3, "wager_per_hand": 2})
        # Verify state and ledger ownership follow the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify the same server round is returned on retry.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify one aggregate debit covers all three hands exactly once.
        debits = [event for event in self.fake.events if event["transaction_type"] == "MHVP_WAGER_DEBIT"]
        # Verify only one debit exists after the replay.
        self.assertEqual(1, len(debits))
        # Verify the aggregate debit equals three times the per-hand wager.
        self.assertEqual(-6.0, debits[0]["amount"])

    # Confirm holds persist and a repeated draw never duplicates a payout credit.
    def test_reload_safe_holds_and_idempotent_draw(self):
        # Start a deterministic five-hand round.
        started = self.call("/api/v1/games/multi-hand-video-poker/rounds", {"request_id": "draw-1", "hand_count": 5, "wager_per_hand": 1})
        # Store the stable round id used by hold and draw routes.
        round_id = started["round"]["round_id"]
        # Persist two common held positions.
        held = self.call(f"/api/v1/games/multi-hand-video-poker/rounds/{round_id}/holds", {"holds": [0, 3]})
        # Verify the response and saved document retain the selection.
        self.assertEqual([0, 3], held["round"]["holds"])
        # Complete and settle every generated hand once.
        first = self.call(f"/api/v1/games/multi-hand-video-poker/rounds/{round_id}/draw", {})
        # Simulate a crash after payout credit but before its completion marker was durable.
        self.fake.states["session-player"]["recent_rounds"][-1]["payout_status"] = "pending"
        # Remove the cached payout id so retry must recover from ledger history.
        self.fake.states["session-player"]["recent_rounds"][-1].pop("payout_ledger_id", None)
        # Repeat the draw to exercise archived-round payout recovery.
        second = self.call(f"/api/v1/games/multi-hand-video-poker/rounds/{round_id}/draw", {})
        # Verify both responses contain the same deterministic five results.
        self.assertEqual(first["round"]["results"], second["round"]["results"])
        # Verify the service distinguishes initial settlement from a replay.
        self.assertFalse(first["replayed"])
        # Verify the repeated draw is explicitly reported as a replay.
        self.assertTrue(second["replayed"])
        # Count aggregate payout credits after the repeated draw.
        credits = [event for event in self.fake.events if event["transaction_type"] == "MHVP_PAYOUT_CREDIT"]
        # Verify positive payouts have one credit and zero payouts have none.
        self.assertEqual(1 if first["round"]["total_payout"] else 0, len(credits))
        # Verify active state is cleared while the settled round remains reload-safe.
        self.assertIsNone(second["state"]["active_round"])
        # Verify the newest archived round is the completed round.
        self.assertEqual(round_id, second["state"]["recent_rounds"][-1]["round_id"])

    # Prove a rejected pre-debit wager rolls back only its owned prepared round. (MHVP-007, TEST-201)
    def test_pre_debit_failure_preserves_concurrent_sibling_state(self):
        # Publish a sibling field after preparation but before the injected debit rejects.
        def reject_debit(player_id, amount, transaction_type, game=None, round_id=None, details=None):
            # Apply one independent provider-current update during the money boundary.
            def publish_sibling(current):
                # Preserve one exact marker that the action-owned rollback must not erase.
                current["atomic_sibling"] = {"owner": "other-request"}
                # Return the complete latest document to the fake provider.
                return current

            # Commit the sibling publication before surfacing the wager failure.
            self.fake.update(player_id, publish_sibling)
            # Simulate a wallet rejection before any ledger event exists.
            raise RuntimeError("synthetic pre-debit rejection")

        # Build a service whose only changed seam is the rejecting debit.
        service = api.MultiHandVideoPokerService(repository=self.fake, debit=reject_debit, credit=self.fake.credit, read_ledger=self.fake.read_ledger, get_player=self.fake.get_player, clock=lambda: "2026-07-13T00:00:00.000Z", id_factory=lambda prefix: f"{prefix}_failed", seed_factory=lambda request_id: f"failure:{request_id}")
        # Require the original wallet failure to remain visible to the route boundary.
        with self.assertRaisesRegex(RuntimeError, "synthetic pre-debit rejection"):
            # Attempt one otherwise valid wagered round.
            service.start_round("session-player", {"request_id": "failure-1", "hand_count": 3, "wager_per_hand": 1})
        # Read the provider-current state after bounded rollback.
        current = self.fake.states["session-player"]
        # Require only the action-owned active round to be cleared.
        self.assertIsNone(current["active_round"])
        # Require the concurrently published sibling body to survive byte-for-byte.
        self.assertEqual({"owner": "other-request"}, current["atomic_sibling"])
        # Require zero money evidence because the injected debit never committed.
        self.assertEqual([], self.fake.events)

    # Prove a committed lost response remains recoverable and is never rolled back. (MHVP-007, TEST-201)
    def test_lost_debit_response_preserves_round_and_replays_one_event(self):
        # Commit through the established fake ledger and then lose only its response.
        def commit_then_fail(player_id, amount, transaction_type, game=None, round_id=None, details=None):
            # Append the exact immutable wager event before simulating transport loss.
            self.fake.debit(player_id, amount, transaction_type, game, round_id, details)
            # Surface a failure after durable money movement.
            raise RuntimeError("synthetic lost debit response")

        # Build a service whose debit seam loses the post-commit response.
        service = api.MultiHandVideoPokerService(repository=self.fake, debit=commit_then_fail, credit=self.fake.credit, read_ledger=self.fake.read_ledger, get_player=self.fake.get_player, clock=lambda: "2026-07-13T00:00:00.000Z", id_factory=lambda prefix: f"{prefix}_lost", seed_factory=lambda request_id: f"lost:{request_id}")
        # Require the synthetic response loss to propagate without erasing state.
        with self.assertRaisesRegex(RuntimeError, "synthetic lost debit response"):
            # Start one round whose debit commits before the exception.
            service.start_round("session-player", {"request_id": "lost-1", "hand_count": 3, "wager_per_hand": 2})
        # Require the prepared round to remain available for ledger-proof recovery.
        self.assertEqual("mhvp_lost", self.fake.states["session-player"]["active_round"]["round_id"])
        # Replay through the normal service so immutable ledger evidence completes the marker.
        recovered = self.service.start_round("session-player", {"request_id": "lost-1", "hand_count": 3, "wager_per_hand": 2})
        # Require the established round and explicit replay response.
        self.assertEqual(("mhvp_lost", True, "complete"), (recovered["round"]["round_id"], recovered["replayed"], recovered["round"]["wager_status"]))
        # Require the frozen public response fields to remain exact.
        self.assertEqual({"round", "wager", "replayed", "game", "state", "player", "hand_counts", "paytable"}, set(recovered))
        # Require exactly one aggregate debit despite the lost response and replay.
        self.assertEqual(1, sum(event["transaction_type"] == "MHVP_WAGER_DEBIT" for event in self.fake.events))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
