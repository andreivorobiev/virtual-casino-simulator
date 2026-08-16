# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused session, retry, and atomic-state tests for Jacks-or-Better issues #91 and #839.

Confirmed requirements include JOBVP-001 through JOBVP-006 and TEST-224.
"""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public route errors for fail-closed conflict and isolation assertions.
from casino.errors import ConflictError, NotFoundError
# Import the current router so the game remains reachable without global registration.
from casino.router import Router
# Import only the isolated game API and engine under test.
from casino.games.jacks_or_better_video_poker import api, engine


# Provide in-memory player state and ledger adapters for isolated API tests.
class FakeCasino:
    # Initialize multiple authenticated players without touching repository data files.
    def __init__(self):
        # Store player-scoped game documents by player id.
        self.states = {}
        # Store committed ledger events in chronological order.
        self.events = []
        # Store fake balances only inside the ledger adapter.
        self.balances = {"session-player": 10_000.0, "other-session": 10_000.0, "caller-player": 10_000.0}
        # Store a deterministic ledger id counter.
        self.ledger_sequence = 0
        # Store a deterministic round id counter.
        self.round_sequence = 0

    # Load a deep copy of one player-scoped state document.
    def load_state(self, game_id, player_id, factory):
        # Return persisted state or a fresh default without sharing references.
        return copy.deepcopy(self.states.get(player_id, factory()))

    # Save a deep copy of one player-scoped state document.
    def save_state(self, game_id, player_id, state):
        # Persist state under the bound player only.
        self.states[player_id] = copy.deepcopy(state)

    # Load one detached player document through the repository contract.
    def load(self, player_id):
        # Delegate to the historical fake helper with the game default factory.
        return self.load_state(engine.GAME_ID, player_id, engine.default_state)

    # Apply one callback against the latest provider-owned document.
    def update(self, player_id, mutator):
        # Load a detached current document before entering the callback.
        current = self.load(player_id)
        # Let the game replace only fields it owns.
        updated = mutator(current)
        # Persist a detached complete provider result.
        self.states[player_id] = copy.deepcopy(updated)
        # Return another detached copy like the shared provider helper.
        return copy.deepcopy(updated)

    # Create one deterministic server round identifier.
    def new_id(self, prefix):
        # Increment the deterministic round sequence.
        self.round_sequence += 1
        # Return one unique prefixed server identifier.
        return f"{prefix}_round_{self.round_sequence}"

    # Create one fake ledger event through the same signed-amount semantics as core ledger.
    def transact(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Increment the deterministic event id counter.
        self.ledger_sequence += 1
        # Read the balance before applying the signed ledger amount.
        before = self.balances[player_id]
        # Apply the signed amount only inside this ledger test double.
        after = round(before + amount, 2)
        # Reject overdrafts like the production ledger provider.
        if after < 0:
            # Raise a simple assertion because focused tests provision sufficient funds.
            raise AssertionError("fake ledger overdraft")
        # Store the balance after the ledger operation.
        self.balances[player_id] = after
        # Build the public ledger fields used by the game service replay scan.
        event = {"ledger_id": f"led_{self.ledger_sequence}", "player_id": player_id, "amount": amount, "transaction_type": transaction_type, "game": game, "round_id": round_id, "details": details or {}}
        # Append the committed event for retry recovery.
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


# Verify direct routes, authenticated isolation, and ledger replay guards.
class JacksOrBetterVideoPokerApiTests(unittest.TestCase):
    # Build an isolated router and deterministic service before every test.
    def setUp(self):
        # Create fresh in-memory state and ledger adapters.
        self.fake = FakeCasino()
        # Build the service with deterministic ids, timestamps, and card seeds.
        self.service = api.JacksOrBetterVideoPokerService(repository=self.fake, debit=self.fake.debit, credit=self.fake.credit, read_ledger=self.fake.read_ledger, get_player=self.fake.get_player, clock=lambda: "2026-07-14T00:00:00.000Z", id_factory=self.fake.new_id, seed_factory=lambda action_id: f"api:{action_id}")
        # Create a game-local router without touching the shared registry.
        self.router = Router()
        # Register only the issue #91 routes for focused tests.
        api.register(self.router, service=self.service)

    # Dispatch one game request with an authenticated test context.
    def call(self, path, body=None, method="POST", *, player_id="session-player"):
        # Build the current shared authenticated-player context shape.
        context = {"bound_player_id": player_id, "user": {"player_id": player_id}}
        # Delegate through the shared router so hostile caller ids are replaced centrally.
        return self.router.dispatch(method, path, body or {}, context=context)

    # Count ledger events of one game-owned movement type.
    def events(self, transaction_type):
        # Filter the fake ledger by its stable transaction type.
        return [event for event in self.fake.events if event["transaction_type"] == transaction_type]

    # Refuse untracked publication before provider storage can observe a callback.
    def test_atomic_publication_requires_a_loaded_baseline(self):
        # Construct one detached engine default that never passed through the repository.
        detached = engine.default_state()
        # Reject the missing optimistic snapshot with a stable game-owned conflict.
        with self.assertRaisesRegex(ConflictError, "missing its atomic baseline"):
            # Attempt direct publication without a provider read.
            self.service._save("session-player", detached)
        # Prove the refusal occurred before creating provider state.
        self.assertNotIn("session-player", self.fake.states)

    # Accept one exact duplicate result while preserving provider-owned siblings.
    def test_atomic_publication_is_idempotent_and_preserves_siblings(self):
        # Load one tracked empty state through the repository boundary.
        state = self.service._load("session-player")
        # Publish the canonical empty result once to establish durable bytes.
        self.service._save("session-player", state)
        # Add unrelated metadata after the caller's baseline advances.
        self.fake.states["session-player"]["atomic_markers"] = ["sibling"]
        # Publish the exact same game-owned result through idempotent comparison.
        self.service._save("session-player", state)
        # Read the complete provider-authoritative document after both updates.
        persisted = self.fake.load("session-player")
        # Preserve the unrelated sibling while keeping operation metadata private.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Reject internal optimistic metadata from durable state bytes.
        self.assertNotIn("_jobvp_atomic_baseline", persisted)

    # Reject one stale writer after a competing game-owned publication wins.
    def test_atomic_publication_rejects_stale_game_state(self):
        # Load two independent snapshots of the same provider-owned initial state.
        first = self.service._load("session-player")
        # Load the competing snapshot before either writer publishes.
        stale = self.service._load("session-player")
        # Give the first writer one unique terminal result.
        first["recent_rounds"] = [{"round_id": "winner", "phase": "settled"}]
        # Publish the first writer against the shared baseline.
        self.service._save("session-player", first)
        # Add one unrelated sibling beside the provider winner.
        self.fake.states["session-player"]["atomic_markers"] = ["sibling"]
        # Give the stale writer a distinct result over the old baseline.
        stale["recent_rounds"] = [{"round_id": "loser", "phase": "settled"}]
        # Reject the stale replacement rather than merging incompatible game state.
        with self.assertRaisesRegex(ConflictError, "state changed during this action"):
            # Attempt to publish the stale owned snapshot.
            self.service._save("session-player", stale)
        # Read the authoritative provider result after the conflict.
        persisted = self.fake.load("session-player")
        # Retain only the winner and the unrelated sibling.
        self.assertEqual(("winner", ["sibling"]), (persisted["recent_rounds"][0]["round_id"], persisted["atomic_markers"]))

    # Prevent rejected-debit cleanup from erasing a concurrent game-state winner.
    def test_rejected_wager_rollback_cannot_erase_concurrent_winner(self):
        # Replace the ledger debit with one provider winner followed by failure.
        def fail_after_concurrent_update(*_args, **_kwargs):
            # Change the prepared round through provider-current state.
            def publish_winner(current):
                # Mark the prepared hand with one concurrent diagnostic field.
                current["active_round"]["atomic_winner"] = True
                # Publish one unrelated sibling beside the winning game state.
                current["atomic_markers"] = ["provider-winner"]
                # Return the complete current document.
                return current

            # Commit the concurrent winner before the attempted rollback.
            self.fake.update("session-player", publish_winner)
            # Fail before any append-only fake ledger movement can commit.
            raise RuntimeError("injected pre-ledger wager failure")

        # Install only the bounded failing movement seam.
        self.service._debit = fail_after_concurrent_update
        # Surface the cleanup conflict because another writer owns prepared state.
        with self.assertRaisesRegex(ConflictError, "state changed during this action"):
            # Attempt one money-bearing deal whose rollback is now stale.
            self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "atomic-rollback-0001", "coin_value": 1, "coins": 1})
        # Read the exact provider-authoritative state after rejected cleanup.
        persisted = self.fake.load("session-player")
        # Preserve the concurrent marker and unrelated sibling.
        self.assertEqual((True, ["provider-winner"]), (persisted["active_round"]["atomic_winner"], persisted["atomic_markers"]))
        # Prove the failure occurred before any wallet movement.
        self.assertEqual([], self.fake.events)

    # Confirm hostile caller ids cannot escape the session and deal retry debits once.
    def test_session_binding_and_exactly_once_wager_recovery(self):
        # Start a five-coin wager while supplying hostile body and query identities.
        first = self.call("/api/v1/games/jacks-or-better-video-poker/rounds?player_id=caller-player", {"player_id": "caller-player", "action_id": "deal-1", "coin_value": 2, "coins": 5})
        # Simulate a crash after the ledger debit but before its state marker was durable.
        self.fake.states["session-player"]["active_round"]["wager_status"] = "pending"
        # Remove the cached event id so retry must recover from ledger history.
        self.fake.states["session-player"]["active_round"].pop("wager_ledger_id", None)
        # Replay the exact same deal action and wager settings.
        second = self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"player_id": "caller-player", "action_id": "deal-1", "coin_value": 2, "coins": 5})
        # Verify state and ledger ownership follow the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify the same server round is returned on retry.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify the replay is explicit for browser retry handling.
        self.assertTrue(second["replayed"])
        # Verify one debit covers coin value times the selected coin count exactly once.
        self.assertEqual(1, len(self.events(api.WAGER_TRANSACTION_TYPE)))
        # Read the committed wager event for complete audit-dimension assertions.
        wager_event = self.events(api.WAGER_TRANSACTION_TYPE)[0]
        # Verify the committed debit equals two fake tokens times five coins.
        self.assertEqual(-10.0, wager_event["amount"])
        # Verify the ledger event names the authenticated player, game, and server round.
        self.assertEqual(("session-player", engine.GAME_ID, first["round"]["round_id"]), (wager_event["player_id"], wager_event["game"], wager_event["round_id"]))
        # Verify the retry-safe deal action is retained in ledger details.
        self.assertEqual("deal-1", wager_event["details"]["deal_action_id"])
        # Verify no event or state was assigned to the hostile caller identity.
        self.assertFalse([event for event in self.fake.events if event["player_id"] == "caller-player"])

    # Confirm one deal key cannot be reused for different money parameters.
    def test_conflicting_deal_action_id_fails_closed(self):
        # Commit the first deal action with one coin value and column.
        self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "deal-conflict", "coin_value": 1, "coins": 5})
        # Reuse the same action id with a different coin count.
        with self.assertRaises(ConflictError):
            # Dispatch the conflicting money action through the public route.
            self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "deal-conflict", "coin_value": 1, "coins": 4})
        # Verify the conflict did not add a second wager event.
        self.assertEqual(1, len(self.events(api.WAGER_TRANSACTION_TYPE)))

    # Confirm holds survive reload and payout recovery never duplicates a credit.
    def test_reload_safe_holds_and_exactly_once_payout_recovery(self):
        # Start a deterministic max-coin round.
        started = self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "deal-royal", "coin_value": 1, "coins": 5})
        # Store the stable round id used by hold and draw routes.
        round_id = started["round"]["round_id"]
        # Replace the deterministic source with a known royal-flush acceptance vector.
        self.fake.states["session-player"]["active_round"]["initial_hand"] = ["AS", "KS", "QS", "JS", "10S"]
        # Persist all five held positions through the public action.
        held = self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{round_id}/holds", {"holds": [0, 1, 2, 3, 4]})
        # Verify the response and saved document retain the selection across loads.
        self.assertEqual([0, 1, 2, 3, 4], held["state"]["active_round"]["holds"])
        # Complete and settle the known max-coin royal once.
        first = self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{round_id}/draw", {"action_id": "draw-royal"})
        # Simulate a crash after payout credit but before its completion marker was durable.
        self.fake.states["session-player"]["recent_rounds"][-1]["payout_status"] = "pending"
        # Remove the cached payout id so retry must recover from ledger history.
        self.fake.states["session-player"]["recent_rounds"][-1].pop("payout_ledger_id", None)
        # Repeat the same draw action to exercise archived-round payout recovery.
        second = self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{round_id}/draw", {"action_id": "draw-royal"})
        # Verify the classic max-coin royal awards four thousand returned credits.
        self.assertEqual(4000, first["round"]["payout_credits"])
        # Verify the final cards and payout are stable across the retry.
        self.assertEqual(first["round"]["final_hand"], second["round"]["final_hand"])
        # Verify the repeated draw is explicitly reported as a replay.
        self.assertTrue(second["replayed"])
        # Verify the ledger contains exactly one returned-credit event.
        self.assertEqual(1, len(self.events(api.PAYOUT_TRANSACTION_TYPE)))
        # Read the committed payout event for complete audit-dimension assertions.
        payout_event = self.events(api.PAYOUT_TRANSACTION_TYPE)[0]
        # Verify settlement names the authenticated player, game, and same server round.
        self.assertEqual(("session-player", engine.GAME_ID, round_id), (payout_event["player_id"], payout_event["game"], payout_event["round_id"]))
        # Verify the retry-safe draw action and paytable outcome are retained in details.
        self.assertEqual(("draw-royal", "royal_flush"), (payout_event["details"]["action_id"], payout_event["details"]["outcome"]))
        # Verify the settled round is archived while the active slot remains clear.
        self.assertIsNone(second["state"]["active_round"])

    # Confirm draw action ids cannot be substituted or reused across rounds.
    def test_conflicting_draw_action_ids_fail_closed(self):
        # Start the first round that will own one draw action key.
        first = self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "deal-a", "coin_value": 1, "coins": 1})
        # Complete the first round with its immutable draw action id.
        self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{first['round']['round_id']}/draw", {"action_id": "draw-owned"})
        # Reject a different draw key for the already settled first round.
        with self.assertRaises(ConflictError):
            # Attempt to relabel the completed settlement action.
            self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{first['round']['round_id']}/draw", {"action_id": "draw-other"})
        # Start a second round after the first round is archived.
        second = self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "deal-b", "coin_value": 1, "coins": 1})
        # Reject reuse of the first round's draw key for the second round.
        with self.assertRaises(ConflictError):
            # Attempt to assign one action id to two server rounds.
            self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{second['round']['round_id']}/draw", {"action_id": "draw-owned"})

    # Confirm another authenticated session cannot observe or act on a private round.
    def test_cross_session_state_and_rounds_are_isolated(self):
        # Start one private round for the primary session.
        started = self.call("/api/v1/games/jacks-or-better-video-poker/rounds", {"action_id": "private-deal", "coin_value": 1, "coins": 1})
        # Read state as a different authenticated user.
        other_state = self.call("/api/v1/games/jacks-or-better-video-poker/state", method="GET", player_id="other-session")
        # Verify the other session receives its own empty state document.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject the other session attempting to change holds on the private round.
        with self.assertRaises(NotFoundError):
            # Dispatch the cross-session hold action through the same public route.
            self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{started['round']['round_id']}/holds", {"holds": [0]}, player_id="other-session")
        # Reject the other session attempting to settle the private round.
        with self.assertRaises(NotFoundError):
            # Dispatch the cross-session draw action through the same public route.
            self.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{started['round']['round_id']}/draw", {"action_id": "foreign-draw"}, player_id="other-session")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
