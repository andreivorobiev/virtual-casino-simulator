"""Session, persistence, and exactly-once Three Card Poker API tests."""

# Import deep-copy support to model provider document boundaries.
import copy
# Import unittest for dependency-free focused coverage.
import unittest

# Import stable public errors for conflict and insufficient-funds assertions.
from casino.errors import ConflictError, InsufficientFundsError
# Import the isolated router used by focused game tests.
from casino.router import Router
# Import only this game's API, engine, and service modules.
from casino.games.three_card_poker import api, engine, service


# Simulate player-scoped persistence without touching repository runtime data.
class MemoryRepository:
    # Start with no persisted player documents.
    def __init__(self):
        # Store detached documents by player id.
        self.documents = {}

    # Load one detached player state document.
    def load(self, player_id: str) -> dict:
        # Return saved state or a fresh production-shaped default.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player state document.
    def save(self, player_id: str, state: dict) -> None:
        # Persist a deep copy so later mutation requires another explicit save.
        self.documents[player_id] = copy.deepcopy(state)


# Record ledger-shaped events and enforce fake balances.
class RecordingLedger:
    # Seed deterministic balances for isolated players.
    def __init__(self, balances=None):
        # Store mutable two-decimal fake balances.
        self.balances = dict(balances or {"session-player": 1000.0, "other-player": 1000.0})
        # Retain append-only committed event evidence.
        self.events = []

    # Find a committed event matching every prepared intent dimension.
    def find_intent(self, intent: dict):
        # Search newest-first for exact ownership and action identity.
        for event in reversed(self.events):
            # Normalize structured event details.
            details = event.get("details") or {}
            # Return only the exact stable prepared movement.
            if event["player_id"] == intent["player_id"] and event["game"] == intent["game"] and event["round_id"] == intent["round_id"] and event["transaction_type"] == intent["transaction_type"] and details.get("three_card_poker_action_id") == intent["action_id"]:
                # Return detached evidence like a storage provider read.
                return copy.deepcopy(event)
        # Report that no movement committed yet.
        return None

    # Apply one prepared movement atomically to the fake balance and ledger.
    def transact(self, intent: dict) -> dict:
        # Convert debit instructions to signed negative movement.
        signed_amount = -intent["amount"] if intent["direction"] == "debit" else intent["amount"]
        # Read the current player balance.
        before = round(float(self.balances[intent["player_id"]]), 2)
        # Calculate the proposed balance.
        after = round(before + signed_amount, 2)
        # Reject overdraws through the same public error class as shared ledger.
        if after < 0:
            # Preserve useful fake-ledger diagnostics.
            raise InsufficientFundsError(details={"player_id": intent["player_id"], "balance": before, "amount": signed_amount})
        # Build one ledger-shaped append-only event.
        event = {
            "ledger_id": f"ledger-{len(self.events) + 1}",  # Assign stable test evidence id.
            "player_id": intent["player_id"],  # Preserve session ownership.
            "game": intent["game"],  # Preserve game ownership.
            "round_id": intent["round_id"],  # Preserve round ownership.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "amount": signed_amount,  # Preserve signed ledger amount.
            "balance_before": before,  # Preserve the prior balance.
            "balance_after": after,  # Preserve the committed balance.
            "details": copy.deepcopy(intent["details"]),  # Preserve replay details.
        }
        # Commit the fake balance with the event.
        self.balances[intent["player_id"]] = after
        # Append the immutable movement evidence.
        self.events.append(copy.deepcopy(event))
        # Return detached committed evidence.
        return copy.deepcopy(event)

    # Return one player-shaped wallet snapshot.
    def player(self, player_id: str) -> dict:
        # Expose only fields needed by game responses.
        return {"player_id": player_id, "balance": self.balances[player_id]}


# Generate distinct deterministic round identifiers.
class IdFactory:
    # Start before the first generated id.
    def __init__(self):
        # Retain a monotonic local sequence.
        self.sequence = 0

    # Return one prefixed stable id.
    def __call__(self, prefix: str) -> str:
        # Advance before constructing the id.
        self.sequence += 1
        # Return a router-safe identifier.
        return f"{prefix}_round_{self.sequence}"


# Verify bound sessions, action fingerprints, recovery, and ledger-only flows.
class ThreeCardPokerApiTests(unittest.TestCase):
    # Build fresh in-memory service ports and a local router before every test.
    def setUp(self):
        # Create empty provider-shaped state storage.
        self.repository = MemoryRepository()
        # Create recording fake wallet balances.
        self.ledger = RecordingLedger()
        # Build deterministic service dependencies.
        self.game_service = service.ThreeCardPokerService(repository=self.repository, ledger_adapter=self.ledger, player_reader=self.ledger.player, clock=lambda: "2026-07-14T00:00:00.000Z", id_factory=IdFactory(), seed_factory=lambda request_id: f"api:{request_id}")
        # Create a game-local router without shared registration changes.
        self.router = Router()
        # Register only the issue #93 endpoints.
        api.register(self.router, service=self.game_service)
        # Store the authenticated player context used by shared dispatch.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one focused route through the real session resolver path.
    def call(self, path, body=None, method="POST"):
        # Delegate with a fresh context copy so requests cannot leak mutations.
        return self.router.dispatch(method, path, body or {}, context=copy.deepcopy(self.context))

    # Deal one low-cost deterministic round for repeated tests.
    def deal(self, request_id="deal-action-1", ante=10, pair_plus=2):
        # Call the public route using only supported action inputs.
        return self.call("/api/v1/games/three-card-poker/rounds", {"request_id": request_id, "ante": ante, "pair_plus": pair_plus})

    # Confirm hostile player ids cannot escape the authenticated session.
    def test_session_binding_and_exact_deal_replay(self):
        # Submit conflicting body identity with one stable retry id.
        first = self.call("/api/v1/games/three-card-poker/rounds?player_id=other-player", {"player_id": "other-player", "request_id": "deal-session-1", "ante": 10, "pair_plus": 3})
        # Replay the exact same request and hostile identity.
        second = self.call("/api/v1/games/three-card-poker/rounds?player_id=other-player", {"player_id": "other-player", "request_id": "deal-session-1", "ante": 10, "pair_plus": 3})
        # Verify response ownership follows authenticated context.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify every ledger event follows authenticated context.
        self.assertTrue(all(event["player_id"] == "session-player" for event in self.ledger.events))
        # Verify exact replay returns the original server round.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify replay is labeled explicitly.
        self.assertTrue(second["replayed"])
        # Verify one aggregate initial debit covers both wagers.
        self.assertEqual(["THREE_CARD_POKER_INITIAL_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify dealer cards remain hidden while a decision is pending.
        self.assertEqual(["??", "??", "??"], second["round"]["dealer_hand"])

    # Confirm a deal identifier cannot be reused with changed normalized money.
    def test_altered_deal_retry_fails_closed(self):
        # Commit the original low-cost deal.
        self.deal(request_id="deal-conflict-1", ante=10, pair_plus=2)
        # Reuse the same id with an altered Ante.
        with self.assertRaises(ConflictError):
            # Assert the service rejects before another debit.
            self.deal(request_id="deal-conflict-1", ante=11, pair_plus=2)
        # Verify only the original movement remains.
        self.assertEqual(1, len(self.ledger.events))

    # Confirm Play and its aggregate payout are exactly-once across retries and marker loss.
    def test_play_replay_and_reload_recovery_do_not_duplicate_ledger(self):
        # Deal one deterministic decision-ready round.
        started = self.deal(request_id="deal-play-1", ante=10, pair_plus=2)
        # Capture the stable server round identifier.
        round_id = started["round"]["round_id"]
        # Commit the matching Play decision once.
        first = self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-play-1", "decision": "play"})
        # Replay the exact decision.
        second = self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-play-1", "decision": "play"})
        # Record event count after the exact replay.
        committed_count = len(self.ledger.events)
        # Simulate a crash that lost every post-ledger state marker.
        self.repository.documents["session-player"]["ledger_actions"] = {}
        # Build a fresh service instance over the same persisted ports.
        reloaded = service.ThreeCardPokerService(repository=self.repository, ledger_adapter=self.ledger, player_reader=self.ledger.player, clock=lambda: "2026-07-14T00:00:02.000Z", id_factory=IdFactory(), seed_factory=lambda request_id: f"api:{request_id}")
        # Trigger state recovery before public projection.
        recovered = reloaded.state("session-player")
        # Verify no event duplicated during replay or reload recovery.
        self.assertEqual(committed_count, len(self.ledger.events))
        # Verify one initial and one Play debit exist.
        self.assertEqual(1, sum(event["transaction_type"] == "THREE_CARD_POKER_INITIAL_DEBIT" for event in self.ledger.events))
        # Verify exactly one matching Play debit exists.
        self.assertEqual(1, sum(event["transaction_type"] == "THREE_CARD_POKER_PLAY_DEBIT" for event in self.ledger.events))
        # Verify exactly one aggregate payout credit exists for this deterministic winning seed.
        self.assertEqual(1, sum(event["transaction_type"] == "THREE_CARD_POKER_PAYOUT_CREDIT" for event in self.ledger.events))
        # Verify both action responses identify the same terminal result.
        self.assertEqual(first["round"], second["round"])
        # Verify the exact retry is labeled replayed.
        self.assertTrue(second["replayed"])
        # Verify reload projects no pending active round.
        self.assertIsNone(recovered["state"]["active_round"])
        # Verify settled dealer cards never retain hidden markers.
        self.assertNotIn("??", recovered["state"]["recent_rounds"][0]["dealer_hand"])

    # Confirm a decision identifier cannot change round or command semantics.
    def test_altered_decision_retry_fails_closed(self):
        # Deal one decision-ready round.
        started = self.deal(request_id="deal-decision-conflict", ante=10, pair_plus=0)
        # Read the stable round identifier.
        round_id = started["round"]["round_id"]
        # Commit the original Play decision.
        self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-conflict-1", "decision": "play"})
        # Attempt to reuse the same action as Fold.
        with self.assertRaises(ConflictError):
            # Assert altered retry is rejected before movement.
            self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-conflict-1", "decision": "fold"})

    # Confirm Fold never adds Play debit or payout credit and survives reload.
    def test_fold_forfeits_initial_wagers_without_extra_movement(self):
        # Deal with both required and optional initial wagers.
        started = self.deal(request_id="deal-fold-1", ante=10, pair_plus=5)
        # Capture the server round id.
        round_id = started["round"]["round_id"]
        # Fold through the public decision action.
        folded = self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-fold-1", "decision": "fold"})
        # Verify only the aggregate initial debit exists.
        self.assertEqual(["THREE_CARD_POKER_INITIAL_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify response exposes no additional wager event.
        self.assertIsNone(folded["wager"])
        # Verify response exposes no payout event.
        self.assertIsNone(folded["settlement"])
        # Verify both initial components are forfeited.
        self.assertEqual((-15.0, 0.0), (folded["round"]["net"], folded["round"]["total_payout"]))
        # Verify terminal state moved into recent history.
        self.assertEqual(round_id, folded["state"]["recent_rounds"][0]["round_id"])

    # Confirm a rejected Play debit restores the actionable pre-decision state.
    def test_insufficient_play_wager_rolls_back_for_safe_retry(self):
        # Restrict the authenticated player to only the initial aggregate stake.
        self.ledger.balances["session-player"] = 15.0
        # Spend the full balance on Ante and Pair Plus.
        started = self.deal(request_id="deal-low-balance", ante=10, pair_plus=5)
        # Capture the pending round id.
        round_id = started["round"]["round_id"]
        # Attempt a matching Play wager with no remaining balance.
        with self.assertRaises(InsufficientFundsError):
            # Verify shared insufficient-funds semantics propagate.
            self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-low-balance", "decision": "play"})
        # Load the restored persisted state directly.
        restored = self.repository.load("session-player")
        # Verify the round remains decision-ready.
        self.assertEqual("decision", restored["rounds"][round_id]["phase"])
        # Verify rejected action id was removed with rollback.
        self.assertNotIn("decision-low-balance", restored["requests"])
        # Verify no matching Play debit was appended.
        self.assertEqual(0, sum(event["transaction_type"] == "THREE_CARD_POKER_PLAY_DEBIT" for event in self.ledger.events))


# Run this focused module directly for worker validation.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
