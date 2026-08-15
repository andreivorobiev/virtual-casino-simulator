# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Bot-wallet exhaustion, compensation, and self-heal tests for issue #411 Texas Hold'em escrow."""

# Import environment access so durable state is routed into a disposable root before any casino import binds directories.
import os
# Import required dependency so test data can be written outside the real data directory.
import tempfile
# Import the dependency-free standard test runner.
import unittest
# Import required dependency so isolated JSON provider paths are platform-safe.
from pathlib import Path

# Create one module-scoped disposable runtime root before casino.config resolves its directory constants.
_RUNTIME_ROOT = tempfile.TemporaryDirectory(prefix="thpt-escrow-")
# Point persistent state at the disposable root so no test can touch the checked-in data directory.
os.environ["CASINO_DATA_DIR"] = str(Path(_RUNTIME_ROOT.name) / "data")
# Point application logs at the disposable root so logger writes never land in the repository.
os.environ["CASINO_LOG_DIR"] = str(Path(_RUNTIME_ROOT.name) / "logs")

# Import the shared ledger and player services routed through the injected provider.
from casino.core import ledger, players, storage
# Import the public errors asserted at the escrow boundary.
from casino.errors import ConflictError, InsufficientFundsError
# Import the isolated controller module and engine under test.
from casino.games.texas_holdem_practice_table import api, engine


# Verify pre-flight solvency, compensating rollback, and stranded-escrow self-heal.
class TexasHoldemEscrowExhaustionTests(unittest.TestCase):
    # Build one isolated JSON store, funded seats, and a deterministic controller before every test.
    def setUp(self):
        # Create a temporary workspace so this test never mutates checked-in data files.
        self.tmp = tempfile.TemporaryDirectory()
        # Remove the isolated workspace after every test.
        self.addCleanup(self.tmp.cleanup)
        # Build an isolated data root for the JSON provider.
        self.data_root = Path(self.tmp.name) / "data"
        # Build a provider that uses the isolated data root.
        self.provider = storage.JsonStorageProvider(self.data_root)
        # Inject the isolated provider for all core storage callers.
        storage.set_provider_for_tests(self.provider)
        # Always clear provider injection after the isolated test run.
        self.addCleanup(storage.set_provider_for_tests, None)
        # Persist default players through the provider-backed players service.
        self.provider.bootstrap_players(players.default_players())
        # Reset the disposable-root state document so every test starts from an empty table.
        api.StateRepository().update("human", lambda _current: engine.default_state())
        # Fund the three fixed practice seats through the production one-time funding seam.
        api.LedgerAdapter().ensure_accounts()
        # Build a deterministic production-port controller over the injected provider.
        self.controller = api.TexasHoldemPracticeTableController(clock=lambda: "2026-07-26T00:00:00Z", id_factory=lambda prefix: f"{prefix}_hand_1", seed_factory=lambda action_id: f"escrow:{action_id}")

    # Debit one practice seat down to an exact remaining balance through the direct ledger seam.
    def drain(self, player_id, remaining):
        # Read the current funded balance before computing the drain amount.
        balance = players.get_player(player_id)["balance"]
        # Remove everything above the requested remainder in one auditable test debit.
        ledger.debit(player_id, round(balance - remaining, 2), "TEST_PRACTICE_SEAT_DRAIN", None, None, {"purpose": "issue-411-exhaustion"})

    # Read every committed row for one player and transaction type.
    def rows(self, player_id, transaction_type):
        # Filter the append-only provider history by owner and audit type.
        return [row for row in ledger.read_recent(player_id, 1000) if row.get("transaction_type") == transaction_type]

    # Write one stranded document exactly as production left it before the issue #411 fix.
    def strand(self, action_id, wager):
        # Prepare the complete private hand the interrupted start persisted.
        hand = engine.create_hand("human", wager, action_id, seed=f"strand:{action_id}", hand_id=f"thpt_stranded_{action_id}", created_at="2026-07-26T00:00:00Z")
        # Read the human opening escrow intent that committed before the bot failure.
        escrow = hand["ledger_intents"][0]
        # Commit or replay the human escrow debit exactly as the production adapter does.
        event, _replayed = ledger.debit_once(escrow["player_id"], escrow["amount"], escrow["transaction_type"], escrow["action_id"], engine.GAME_ID, hand["hand_id"], escrow["details"])
        # Build the persisted document shape the failed request left behind.
        state = engine.default_state()
        # Keep the unfunded hand stranded in the actionable slot.
        state["active_hand"] = hand
        # Keep the consumed client request receipt.
        state["requests"][action_id] = {"command": "start_hand", "hand_id": hand["hand_id"], "base_wager": float(wager)}
        # Keep the committed human escrow marker.
        state["ledger_actions"][escrow["action_id"]] = {"ledger_id": event.get("ledger_id"), "transaction_type": escrow["transaction_type"], "round_id": hand["hand_id"]}
        # Seed unrelated provider state that recovery must preserve.
        state["atomic_markers"] = ["stranded"]
        # Persist the stranded document through the production provider callback.
        api.StateRepository().update("human", lambda _current: state)
        # Return the identities needed by heal assertions.
        return hand, escrow

    # Confirm pre-flight solvency rejects the start atomically before any persistence or debit.
    def test_preflight_rejects_start_when_a_seat_cannot_cover_the_reserve(self):
        # Leave the first practice seat below the ten-token reserve of a two-token wager.
        self.drain("bot_1", 4.0)
        # Capture the human balance before the rejected command.
        before = players.get_player("human")["balance"]
        # Reject the start while every wallet and document stays untouched.
        with self.assertRaises(ConflictError):
            # Attempt the unfundable ten-token-reserve hand.
            self.controller.start_hand("human", 2, "escrow-preflight-00001")
        # Verify the human wallet never moved.
        self.assertEqual(before, players.get_player("human")["balance"])
        # Verify no game escrow row exists for the human.
        self.assertEqual([], self.rows("human", "TEXAS_HOLDEM_ESCROW_DEBIT"))
        # Verify the state route still answers normally instead of re-raising.
        payload = self.controller.state("human")
        # Verify no phantom hand stayed actionable.
        self.assertIsNone(payload["state"]["active_hand"])
        # Verify the rejected request consumed no durable receipt.
        self.assertEqual({}, api.StateRepository().load("human")["requests"])

    # Confirm a mid-reconcile bot failure compensates the committed human escrow to net zero.
    def test_mid_reconcile_failure_compensates_committed_human_escrow(self):
        # Fail exactly the first bot escrow after the human escrow commits.
        failing_action_id = "thpt:escrow-midfail-00001:opponent_1:escrow"

        # Wrap the production adapter with one targeted mid-reconcile fault.
        class FailingAdapter(api.LedgerAdapter):
            # Fail only the configured intent while every other movement stays real.
            def transact(self, intent):
                # Simulate the drained bot wallet at the exact production failure point.
                if intent["action_id"] == failing_action_id:
                    # Define one unrelated provider update that races the action-owned rollback.
                    def mark(current):
                        # Append one sibling marker outside the practice-table field set.
                        current.setdefault("atomic_markers", []).append("concurrent")
                        # Return the complete provider document for publication.
                        return current

                    # Commit the sibling after preparation but before the injected failure.
                    api.StateRepository().update("human", mark)
                    # Raise the same public error the storage provider raises.
                    raise InsufficientFundsError()
                # Delegate every other movement to the real provider-backed adapter.
                return super().transact(intent)

        # Build a controller whose second intent always fails mid-reconcile.
        controller = api.TexasHoldemPracticeTableController(ledger_adapter=FailingAdapter(), clock=lambda: "2026-07-26T00:00:00Z", id_factory=lambda prefix: f"{prefix}_hand_1")
        # Capture the human balance before the interrupted command.
        before = players.get_player("human")["balance"]
        # Propagate the original failure after the compensating rollback.
        with self.assertRaises(InsufficientFundsError):
            # Attempt the hand whose first bot escrow fails after the human debit commits.
            controller.start_hand("human", 2, "escrow-midfail-00001")
        # Verify the human escrow debit committed exactly once before the failure.
        self.assertEqual(1, len(self.rows("human", "TEXAS_HOLDEM_ESCROW_DEBIT")))
        # Read the compensating refund rows written by the rollback.
        refunds = self.rows("human", "TEXAS_HOLDEM_ESCROW_REFUND_CREDIT")
        # Verify exactly one compensation credit exists for the stranded escrow.
        self.assertEqual(1, len(refunds))
        # Verify the compensation uses the derived exactly-once action identity.
        self.assertEqual("thpt:escrow-midfail-00001:human:escrow:compensation", refunds[0]["details"]["texas_holdem_action_id"])
        # Verify the compensation names the escrow debit it reverses.
        self.assertEqual("thpt:escrow-midfail-00001:human:escrow", refunds[0]["details"]["compensates_action_id"])
        # Verify net human wallet movement is zero.
        self.assertEqual(before, players.get_player("human")["balance"])
        # Verify no phantom hand stayed actionable.
        self.assertIsNone(controller.state("human")["state"]["active_hand"])
        # Verify provider-current unrelated state survived compensating rollback.
        self.assertEqual(["concurrent"], api.StateRepository().load("human")["atomic_markers"])
        # Verify the private optimistic baseline never entered persisted state.
        self.assertNotIn(api._ATOMIC_BASELINE_KEY, api.StateRepository().load("human"))
        # Verify the consumed identity fails closed instead of replaying refunded escrow rows as live.
        with self.assertRaises(ConflictError):
            # Retry the identical command after its escrow was compensated.
            controller.start_hand("human", 2, "escrow-midfail-00001")

    # Confirm a stranded pre-fix document heals on the next state read and the table plays again.
    def test_stranded_prepared_hand_heals_and_table_recovers(self):
        # Leave the first practice seat with exactly one five-token reserve unit.
        self.drain("bot_1", 5.0)
        # Write the stranded production document with a committed ten-token human escrow.
        hand, escrow = self.strand("escrow-stranded-0001", 2)
        # Verify the stranded escrow debit reduced the human wallet.
        self.assertEqual(4990.0, players.get_player("human")["balance"])
        # Read state where the pre-fix controller re-raised forever.
        payload = self.controller.state("human")
        # Verify the previously bricked route now reports a playable empty table.
        self.assertIsNone(payload["state"]["active_hand"])
        # Verify exactly one compensation credit restored the stranded escrow.
        self.assertEqual(1, len(self.rows("human", "TEXAS_HOLDEM_ESCROW_REFUND_CREDIT")))
        # Verify the human wallet returned to its pre-hand balance.
        self.assertEqual(5000.0, players.get_player("human")["balance"])
        # Verify the unrelated sibling seeded beside the stranded hand survived healing.
        self.assertEqual(["stranded"], api.StateRepository().load("human")["atomic_markers"])
        # Start a smaller hand the still-poor seat can cover with its exact five-token balance.
        started = self.controller.start_hand("human", 1, "escrow-recover-00001")
        # Verify the healed table accepted a funded hand again.
        self.assertEqual("preflop", started["hand"]["phase"])
        # Verify the new five-token escrow committed normally.
        self.assertEqual(4995.0, players.get_player("human")["balance"])

    # Confirm running the heal twice writes exactly one compensation row.
    def test_heal_is_idempotent_across_repeated_recovery(self):
        # Leave the first practice seat unable to cover the stranded ten-token reserve.
        self.drain("bot_1", 5.0)
        # Write the stranded production document once.
        self.strand("escrow-idempotent-01", 2)
        # Heal through the first state read.
        self.controller.state("human")
        # Re-write the identical stranded document as if the healed save was lost.
        self.strand("escrow-idempotent-01", 2)
        # Heal again through a second state read.
        payload = self.controller.state("human")
        # Verify the second heal also cleared the actionable slot.
        self.assertIsNone(payload["state"]["active_hand"])
        # Verify exactly one human escrow debit exists across both passes.
        self.assertEqual(1, len(self.rows("human", "TEXAS_HOLDEM_ESCROW_DEBIT")))
        # Verify exactly one compensation row exists across both passes.
        self.assertEqual(1, len(self.rows("human", "TEXAS_HOLDEM_ESCROW_REFUND_CREDIT")))
        # Verify the human wallet holds exactly one net-zero cycle.
        self.assertEqual(5000.0, players.get_player("human")["balance"])


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
