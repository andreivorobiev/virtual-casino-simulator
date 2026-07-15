"""Session isolation and exactly-once service tests for GitHub issue #130."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict and lookup errors for route assertions.
from casino.errors import ConflictError, NotFoundError
# Import the isolated route adapter and pure engine under test.
from casino.games.joker_poker import api, engine
# Import the isolated service orchestration under test.
from casino.games.joker_poker.service import JokerPokerService, request_fingerprint


# Simulate player-scoped state documents without touching repository data files.
class MemoryRepository:
    # Start with no persisted game documents.
    def __init__(self):
        # Store detached documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so every mutation requires an explicit save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id, state):
        # Persist a deep copy to model the JSON/provider boundary.
        self.documents[player_id] = copy.deepcopy(state)


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only committed event rows.
        self.events = []

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["joker_poker_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_id, fingerprint, details):
        # Resolve any prior committed action before changing the fake balance.
        existing = self.find(player_id, action_id)
        # Reuse an exact matching event.
        if existing is not None:
            # Reject semantic conflicts like the production gateway.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise AssertionError("fake ledger overdraft")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "joker_poker_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class JokerPokerApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = JokerPokerService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}")
        # Register only the game-owned routes on the real shared router.
        self.router = Router()
        # Inject the focused service without changing global registration.
        api.register(self.router, service=self.service)
        # Store the authenticated request context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game action through the real shared resolver path.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so router mutations remain request-local.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Prepare one active fixture round with a committed wager marker.
    def prepared_round(self, action_id="deal-fixture", wager=1):
        # Compute the same deal fingerprint shape as production.
        fingerprint = request_fingerprint({"stage": "deal", "wager": float(wager)})
        # Derive the stable round id from player and action identity.
        round_id = engine.round_id_for("session-player", action_id)
        # Create a guaranteed wild royal source hand.
        round_state = engine.create_round("session-player", wager, action_id, initial_hand=["AS", "KS", "QS", "JS", "JK"], draw_pool=["2C", "3C", "4C", "5C", "6C"], round_id=round_id, created_at="2026-07-14T00:00:00Z", request_fingerprint=fingerprint)
        # Mark the fixture wager committed before testing settlement.
        round_state["wager_status"] = "complete"
        # Store the fake committed wager identifier.
        round_state["wager_ledger_id"] = "ledger-fixture"
        # Persist the active player document with a durable deal receipt.
        self.repository.save("session-player", {"active_round": round_state, "recent_rounds": [], "action_receipts": {action_id: {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}}})
        # Reflect the already-paid fixture wager in the fake balance.
        self.ledger.balances["session-player"] = round(100.0 - wager, 2)
        # Return the stable route id.
        return round_id

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_deal(self):
        # Start one deal with two competing hostile caller identities.
        first = self.call("/api/v1/games/joker-poker/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1", "wager": 7})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/joker-poker/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1", "wager": 7})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one wager debit exists.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "JOKER_POKER_WAGER_DEBIT"]
        # Verify both count and signed amount.
        self.assertEqual((1, -7.0), (len(debits), debits[0]["amount"]))
        # Verify private draw cards are absent from the public payload.
        self.assertNotIn("_draw_pool", first["round"])
        # Verify the private draw pool remains reload-safe in persisted state.
        self.assertIn("_draw_pool", self.repository.documents["session-player"]["active_round"])
        # Read state through a different authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/joker-poker/state?player_id=session-player", method="GET", context=other_context)
        # Verify the other session cannot read the first player's active hand.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject an attempt by the other session to draw the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise cross-session round lookup through the real router.
            self.call(f"/api/v1/games/joker-poker/rounds/{first['round']['round_id']}/draw", {"action_id": "draw-cross-session", "holds": []}, context=other_context)

    # Confirm conflicting deal retries fail before another debit.
    def test_deal_conflict_reuses_no_balance(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/joker-poker/rounds", {"action_id": "deal-conflict", "wager": 3})
        # Reject reuse of the same identity with a changed wager.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/joker-poker/rounds", {"action_id": "deal-conflict", "wager": 4})
        # Verify exactly one wager debit remains committed.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "JOKER_POKER_WAGER_DEBIT"]))

    # Confirm holds persist and a repeated draw never duplicates a payout credit.
    def test_hold_draw_replay_and_state_recovery(self):
        # Prepare a guaranteed wild royal hand.
        round_id = self.prepared_round(wager=1)
        # Persist all five cards as held through the public route.
        held = self.call(f"/api/v1/games/joker-poker/rounds/{round_id}/holds", {"holds": [0, 1, 2, 3, 4]})
        # Verify the response and saved document retain the selection.
        self.assertEqual([0, 1, 2, 3, 4], held["round"]["holds"])
        # Complete and settle the hand once.
        first = self.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", {"action_id": "draw-win", "holds": [0, 1, 2, 3, 4]})
        # Simulate a crash after credit but before the completion marker save.
        self.repository.documents["session-player"]["recent_rounds"][-1]["settlement_status"] = "pending"
        # Remove cached ledger id so reload must recover it from append-only proof.
        self.repository.documents["session-player"]["recent_rounds"][-1].pop("settlement_ledger_id", None)
        # Recreate service state behavior through a normal GET reload.
        reloaded = self.call("/api/v1/games/joker-poker/state", method="GET")
        # Replay the same draw after reload.
        second = self.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", {"action_id": "draw-win", "holds": [0, 1, 2, 3, 4]})
        # Verify deterministic result and explicit replay behavior.
        self.assertEqual(("wild_royal_flush", 100.0, True), (first["round"]["result"]["outcome"], first["round"]["total_payout"], second["replayed"]))
        # Verify reload restored a complete settlement marker.
        self.assertEqual("complete", reloaded["state"]["recent_rounds"][-1]["settlement_status"])
        # Verify exactly one payout credit exists after recovery and replay.
        credits = [event for event in self.ledger.events if event["transaction_type"] == "JOKER_POKER_PAYOUT_CREDIT"]
        # Verify the returned amount and complete audit dimensions.
        self.assertEqual((1, 100.0, "session-player", engine.GAME_ID, round_id, "draw-win"), (len(credits), credits[0]["amount"], credits[0]["player_id"], credits[0]["game"], credits[0]["round_id"], credits[0]["details"]["joker_poker_action_id"]))

    # Confirm a changed terminal draw retry fails closed.
    def test_conflicting_draw_retry_is_rejected(self):
        # Prepare a guaranteed wild royal hand.
        round_id = self.prepared_round(action_id="deal-terminal", wager=1)
        # Settle the round with one draw identity.
        self.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", {"action_id": "draw-terminal", "holds": [0, 1, 2, 3, 4]})
        # Reject the same draw identity with changed hold semantics.
        with self.assertRaises(ConflictError):
            # Exercise conflicting terminal fingerprint detection.
            self.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", {"action_id": "draw-terminal", "holds": []})
        # Verify the conflicting retry created no second payout credit.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "JOKER_POKER_PAYOUT_CREDIT"]))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
