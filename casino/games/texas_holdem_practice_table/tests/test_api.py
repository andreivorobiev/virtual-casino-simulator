# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session binding, escrow, retry, and recovery tests for issue #95."""

# Import detached-copy support so memory persistence matches JSON boundaries.
import copy
# Import unittest for dependency-free focused execution.
import unittest

# Import shared public errors for recording-ledger behavior assertions.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError
# Import the current router for game-local route tests without global registration.
from casino.router import Router
# Import only the isolated controller and engine under test.
from casino.games.texas_holdem_practice_table import api, engine


# Simulate player-scoped persistence without touching repository runtime data.
class MemoryRepository:
    # Start with no stored player documents.
    def __init__(self):
        # Retain detached state documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id: str) -> dict:
        # Return a deep copy so every mutation requires an explicit save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player-scoped document.
    def save(self, player_id: str, state: dict) -> None:
        # Persist a deep copy to model serialization boundaries.
        self.documents[player_id] = copy.deepcopy(state)


# Record append-only human and funded-opponent events through ledger-shaped operations.
class RecordingLedger:
    # Initialize one funded session player and no committed events.
    def __init__(self):
        # Retain chronological append-only event rows.
        self.events = []
        # Retain balances only inside this ledger test double.
        self.balances = {"bound-player": 100.0, "other-player": 100.0, "bot_1": 100_000.0, "bot_2": 100_000.0, "bot_3": 100_000.0}

    # Model the already accepted one-time funded-account prerequisite.
    def ensure_accounts(self) -> list[dict]:
        # Keep focused hand assertions independent from the separately tested funding events.
        return []

    # Find one committed action exactly as the production adapter does.
    def find_action(self, player_id: str, action_id: str):
        # Search newest-first for matching player, game, and details identity.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["texas_holdem_action_id"] == action_id), None)

    # Apply one prepared debit or credit inside the recording adapter.
    def transact(self, intent: dict) -> dict:
        # Read the current balance before applying the signed movement.
        before = self.balances[intent["player_id"]]
        # Convert the positive intent magnitude into a signed ledger amount.
        signed = -intent["amount"] if intent["direction"] == "debit" else intent["amount"]
        # Calculate the resulting two-decimal balance.
        after = round(before + signed, 2)
        # Reject overdrafts through the same public error type as core ledger.
        if after < 0:
            # Preserve normal insufficient-funds behavior for controller rollback.
            raise InsufficientFundsError()
        # Commit the resulting fake balance only through this adapter.
        self.balances[intent["player_id"]] = after
        # Build the ledger subset consumed by recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": intent["player_id"], "game": intent["game"], "round_id": intent["round_id"], "transaction_type": intent["transaction_type"], "amount": signed, "details": copy.deepcopy(intent["details"])}
        # Append the committed immutable-shaped event.
        self.events.append(event)
        # Return a detached committed row.
        return copy.deepcopy(event)


# Verify authenticated ownership and exactly-once local retry recovery.
class TexasHoldemPracticeTableApiTests(unittest.TestCase):
    # Build memory ports and a deterministic controller before every test.
    def setUp(self):
        # Create fresh isolated state storage.
        self.repository = MemoryRepository()
        # Create one funded append-only recording ledger.
        self.ledger = RecordingLedger()
        # Build the controller with deterministic ids, clock, cards, and player data.
        self.controller = api.TexasHoldemPracticeTableController(self.repository, self.ledger, lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", id_factory=lambda prefix: "thpt_hand_1", seed_factory=lambda action_id: f"api:{action_id}")

    # Start one hand using a stable command id.
    def start(self, action_id="action-start-001", wager=2):
        # Delegate to the deterministic controller fixture.
        return self.controller.start_hand("bound-player", wager, action_id)

    # Confirm start retries reuse one hand and one escrow debit.
    def test_start_replay_is_exactly_once_and_changed_payload_conflicts(self):
        # Start the original ten-token escrow hand.
        first = self.start()
        # Replay the exact same action id and fixed-limit unit.
        second = self.start()
        # Verify both responses identify the same deterministic hand.
        self.assertEqual(first["hand"]["hand_id"], second["hand"]["hand_id"])
        # Verify four real-wallet reserve debits exist after replay.
        self.assertEqual([-10.0] * 4, [event["amount"] for event in self.ledger.events])
        # Verify the authenticated human and three fixed bot wallets each reserve once.
        self.assertEqual(["bound-player", "bot_1", "bot_2", "bot_3"], [event["player_id"] for event in self.ledger.events])
        # Verify replay metadata is explicit for the client.
        self.assertTrue(second["replayed"])
        # Reject the same action id reused for another wallet exposure.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting fixed-limit unit.
            self.start(wager=3)

    # Confirm idempotency keys follow the OpenAPI string contract exactly.
    def test_action_id_rejects_non_strings_and_trimmed_variants(self):
        # Exercise values that earlier coercion could convert into valid keys.
        for action_id in (12345678, True, None, " action-start-001 "):
            # Preserve the rejected value in focused-test diagnostics.
            with self.subTest(action_id=repr(action_id)):
                # Reject every non-exact contract value before state access.
                with self.assertRaises(ValidationError):
                    # Validate through the public route helper.
                    api.require_action_id({"action_id": action_id})

    # Confirm action retries cannot advance the board or pot twice.
    def test_decision_replay_advances_one_street_once(self):
        # Start one deterministic practice hand.
        started = self.start(wager=1)
        # Read the stable server hand id.
        hand_id = started["hand"]["hand_id"]
        # Apply one human call and immediate practice-opponent sequence.
        first = self.controller.act("bound-player", hand_id, "call", "action-call-001", "preflop")
        # Replay the exact same human action id and payload.
        second = self.controller.act("bound-player", hand_id, "call", "action-call-001", "preflop")
        # Verify both responses stop at the same flop state and pot.
        self.assertEqual(("flop", 8.0), (first["hand"]["phase"], first["hand"]["pot"]))
        # Verify replay did not consume another street or table unit.
        self.assertEqual((first["hand"]["community_cards"], first["hand"]["pot"]), (second["hand"]["community_cards"], second["hand"]["pot"]))
        # Verify no wallet movement occurs for already-reserved street calls.
        self.assertEqual(4, len(self.ledger.events))
        # Reject the same action id reused for a different decision.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting fold retry.
            self.controller.act("bound-player", hand_id, "fold", "action-call-001", "preflop")

    # Confirm a delayed surface cannot consume the next betting street under a new id.
    def test_expected_phase_rejects_stale_navigation_action(self):
        # Start one deterministic preflop hand.
        started = self.start(wager=1)
        # Advance the original intended decision through the complete opponent sequence.
        self.controller.act("bound-player", started["hand"]["hand_id"], "call", "action-first-001", "preflop")
        # Reject a second id emitted from a stale preflop surface after navigation.
        with self.assertRaises(ConflictError):
            # Attempt to spend the same human intent against the now-current flop.
            self.controller.act("bound-player", started["hand"]["hand_id"], "call", "action-stale-001", "preflop")
        # Verify the rejected command did not allocate another street contribution.
        active = self.repository.documents["bound-player"]["active_hand"]
        # Preserve both phase and pot as direct no-double-advance evidence.
        self.assertEqual(("flop", 8.0), (active["phase"], active["pot"]))

    # Confirm ledger rows recover after state-marker loss without duplicates.
    def test_reload_recovers_escrow_and_terminal_credit_markers(self):
        # Start a hand and commit its opening escrow debit.
        started = self.start(wager=1)
        # Read the private stored hand for deterministic winner arrangement.
        private = self.repository.documents["bound-player"]["active_hand"]
        # Give the human pocket aces for a guaranteed terminal payout.
        private["seats"][0]["hole_cards"] = ["AS", "AH"]
        # Give the three opponents lower pocket pairs.
        private["seats"][1]["hole_cards"] = ["KS", "KH"]
        # Give the second opponent pocket queens.
        private["seats"][2]["hole_cards"] = ["QS", "QH"]
        # Give the third opponent pocket jacks.
        private["seats"][3]["hole_cards"] = ["JS", "JH"]
        # Use a neutral board that preserves the human win.
        private["community_plan"] = ["2C", "3D", "4H", "8S", "9C"]
        # Persist the deterministic private fixture.
        self.repository.documents["bound-player"]["active_hand"] = private
        # Complete all four human decisions with unique ids.
        result = None
        # Exercise each fixed-limit betting phase.
        for index, phase in enumerate(engine.ACTION_PHASES):
            # Apply one call and all server-managed opponent actions.
            result = self.controller.act("bound-player", started["hand"]["hand_id"], "call", f"action-call-{index:03d}", phase)
        # Verify all four escrows and the human's winning pot credit were committed.
        self.assertEqual([-5.0, -5.0, -5.0, -5.0, 19.0], [event["amount"] for event in self.ledger.events])  # Winner receives the 20 pot less the 5% house rake. (issue #456)
        # Verify the terminal four-wallet settlement removes exactly the house rake from the total token supply. (issue #456)
        self.assertEqual(300_199.0, sum(self.ledger.balances.values()))
        # Verify the terminal hand was archived only after payout reconciliation.
        self.assertEqual("settled", result["hand"]["phase"])
        # Simulate loss of every durable marker after ledger rows committed.
        self.repository.documents["bound-player"]["ledger_actions"] = {}
        # Recreate the controller to model process-local service reload.
        reloaded = api.TexasHoldemPracticeTableController(self.repository, self.ledger, lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:01Z", id_factory=lambda prefix: "unused")
        # Trigger append-only recovery through the state endpoint behavior.
        payload = reloaded.state("bound-player")
        # Verify recovery reused all five existing ledger rows.
        self.assertEqual(5, len(self.ledger.events))
        # Verify the settled hand remains reload-safe and fully reconciled.
        self.assertTrue(payload["state"]["recent_hands"][0]["settlement"]["complete"])

    # Confirm public history bounds do not invalidate older durable retry receipts.
    def test_old_receipts_replay_after_public_history_window(self):
        # Generate one more unique server hand id than the public history limit.
        hand_ids = iter(f"thpt_hand_{index:03d}" for index in range(engine.RECENT_HAND_LIMIT + 1))
        # Build a controller whose state and ledger remain the existing memory fixtures.
        controller = api.TexasHoldemPracticeTableController(self.repository, self.ledger, lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", id_factory=lambda prefix: next(hand_ids), seed_factory=lambda action_id: f"archive:{action_id}")
        # Retain the first hand identity for a retry after newer public history evicts it.
        first_hand_id = None
        # Settle enough folded hands to move the first outside the public display window.
        for index in range(engine.RECENT_HAND_LIMIT + 1):
            # Allocate stable start and fold request identities for this hand.
            start_id, fold_id = f"start-old-{index:03d}", f"fold-old-{index:03d}"
            # Reserve one fixed-limit hand through the normal controller boundary.
            started = controller.start_hand("bound-player", 1, start_id)
            # Preserve the oldest hand id for delayed-retry assertions.
            first_hand_id = first_hand_id or started["hand"]["hand_id"]
            # Fold and reconcile the unused escrow through the normal action path.
            controller.act("bound-player", started["hand"]["hand_id"], "fold", fold_id, "preflop")
        # Read the private document after its oldest full hand was compacted.
        private_state = self.repository.documents["bound-player"]
        # Verify full private recovery history stays inside the configured limit.
        self.assertEqual(engine.RECENT_HAND_LIMIT, len(private_state["recent_hands"]))
        # Verify one sanitized snapshot preserves the evicted hand's replay result.
        self.assertEqual([first_hand_id], list(private_state["replay_hands"]))
        # Reject deck, intent, retry, and private-plan fields from compact snapshots.
        self.assertFalse({"community_plan", "burn_cards", "remaining_deck", "ledger_intents", "action_ids"} & set(private_state["replay_hands"][first_hand_id]))
        # Verify the client-facing state remains capped at the documented display limit.
        self.assertEqual(engine.RECENT_HAND_LIMIT, len(controller.state("bound-player")["state"]["recent_hands"]))
        # Snapshot append-only evidence before retrying the oldest start and fold.
        event_count = len(self.ledger.events)
        # Recreate the controller to prove compact receipts survive service reload.
        reloaded = api.TexasHoldemPracticeTableController(self.repository, self.ledger, lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:01Z", id_factory=lambda prefix: "unused", seed_factory=lambda action_id: f"unused:{action_id}")
        # Replay the oldest start command without another escrow debit or deal.
        replayed_start = reloaded.start_hand("bound-player", 1, "start-old-000")
        # Replay the oldest fold command without another refund or transition.
        replayed_fold = reloaded.act("bound-player", first_hand_id, "fold", "fold-old-000", "preflop")
        # Verify both delayed retries resolve the original logical hand.
        self.assertEqual((first_hand_id, first_hand_id), (replayed_start["hand"]["hand_id"], replayed_fold["hand"]["hand_id"]))
        # Verify neither delayed retry appended a duplicate ledger movement.
        self.assertEqual(event_count, len(self.ledger.events))

    # Confirm the router-bound session overrides hostile body and query ids.
    def test_router_session_binding_overrides_caller_player_ids(self):
        # Create one game-local router without shared registration changes.
        router = Router()
        # Register the recording controller on the isolated route set.
        api.register(router, self.controller)
        # Dispatch a hand start with conflicting body and query player ids.
        payload = router.dispatch("POST", "/api/v1/games/texas-holdem-practice-table/hands?player_id=other-player", {"player_id": "other-player", "base_wager": 1, "action_id": "action-bound-001"}, {"bound_player_id": "bound-player"})
        # Verify response ownership follows only the authenticated binding.
        self.assertEqual("bound-player", payload["player"]["player_id"])
        # Verify the hostile caller cannot move the other human wallet.
        self.assertNotIn("other-player", [event["player_id"] for event in self.ledger.events])
        # Verify the expected bound human and fixed opponent wallets were reserved.
        self.assertEqual({"bound-player", "bot_1", "bot_2", "bot_3"}, {event["player_id"] for event in self.ledger.events})
        # Verify every opponent movement retains Admin-auditable owner and seat dimensions.
        self.assertTrue(all(event["details"]["session_owner_id"] == "bound-player" and event["details"]["controller_policy"] == "practice_call" for event in self.ledger.events if event["player_id"].startswith("bot_")))
        # Verify active server-opponent cards remain redacted in the route payload.
        self.assertTrue(all(seat["hole_cards"] == ["??", "??"] for seat in payload["hand"]["seats"][1:]))

    # Confirm two authenticated player documents and wallets cannot cross-read or act.
    def test_two_player_state_and_wallet_isolation(self):
        # Start one escrow-backed hand for the bound player only.
        started = self.start(wager=1)
        # Read the second authenticated player's independent empty table state.
        other = self.controller.state("other-player")
        # Verify the active private hand is absent from the second state document.
        self.assertIsNone(other["state"]["active_hand"])
        # Reject an action attempt using the first player's otherwise valid hand id.
        with self.assertRaises(NotFoundError):
            # Resolve the hand only inside the second authenticated player's state.
            self.controller.act("other-player", started["hand"]["hand_id"], "call", "action-other-001", "preflop")
        # Verify only the owning player's wallet paid the opening escrow.
        self.assertEqual((95.0, 100.0), (self.ledger.balances["bound-player"], self.ledger.balances["other-player"]))
        # Verify the append-only movements retain one human and three funded opponent wallets.
        self.assertEqual(["bound-player", "bot_1", "bot_2", "bot_3"], [event["player_id"] for event in self.ledger.events])

    # Confirm insufficient funds remove a hand when no debit committed.
    def test_insufficient_funds_leave_no_actionable_hand(self):
        # Reduce the human balance below a five-unit reserve.
        self.ledger.balances["bound-player"] = 1.0
        # Reject a hand whose five-token escrow cannot be funded.
        with self.assertRaises(InsufficientFundsError):
            # Attempt the unfunded start command.
            self.start(wager=1)
        # Verify rollback removed the prepared active hand and request receipt.
        self.assertEqual(engine.default_state(), self.repository.documents["bound-player"])
        # Verify no append-only ledger row was created.
        self.assertEqual([], self.ledger.events)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
