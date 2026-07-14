"""Deterministic pure-engine tests for Red Dog issue #84."""

# Import the standard dependency-free unit-test framework.
import unittest

# Import shared public errors for validation and stale-action assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated game engine under test.
from casino.games.red_dog import engine


# Verify all rule, paytable, shoe, and public-state branches deterministically.
class RedDogEngineTests(unittest.TestCase):
    # Build a short persisted shoe whose cards draw in the supplied order.
    def fixture_state(self, first: str, second: str, third: str) -> dict:
        # Start from the production player-scoped schema.
        state = engine.default_state()
        # Reverse the three codes because the engine draws from the list end.
        state["shoe"] = [third, second, first]
        # Assign stable telemetry without invoking production randomness.
        state["shoe_id"] = "shoe_fixture"
        # Return the isolated mutable test document.
        return state

    # Start one round with fixed audit metadata and an arranged three-card shoe.
    def start(self, first: str, second: str, third: str, wager=2, action_id="action-start-1"):
        # Build the player-scoped fixture document.
        state = self.fixture_state(first, second, third)
        # Create the complete prepared round through the public engine function.
        round_item = engine.start_round(state, "session-player", wager, action_id, round_id="rd_round", created_at="2026-07-14T00:00:00.000Z")
        # Return both persisted state and the owned round for assertions.
        return state, round_item

    # Confirm issue #96 produces a reproducible six-deck shoe without an API seed.
    def test_six_deck_seeded_shoe_is_deterministic(self):
        # Build the first fresh document.
        first_state = engine.default_state()
        # Build an independent second document.
        second_state = engine.default_state()
        # Deal the first reproducible opening vector.
        first_round = engine.start_round(first_state, "session-player", 1, "seed-action", seed="red-dog-six", round_id="rd_seed", shoe_id="shoe_seed", created_at="2026-07-14T00:00:00.000Z")
        # Repeat with exactly the same deterministic seams.
        second_round = engine.start_round(second_state, "session-player", 1, "seed-action", seed="red-dog-six", round_id="rd_seed", shoe_id="shoe_seed", created_at="2026-07-14T00:00:00.000Z")
        # Verify all prepared cards, outcomes, and intents reproduce exactly.
        self.assertEqual(first_round, second_round)
        # Verify the remaining six-deck shoe order also reproduces exactly.
        self.assertEqual(first_state["shoe"], second_state["shoe"])
        # Verify fixed table metadata advertises six decks.
        self.assertEqual(6, first_state["rules"]["decks"])
        # Count the automatic pair card only when equal opening ranks require it.
        cards_drawn = 3 if first_round["first_card"]["rank"] == first_round["second_card"]["rank"] else 2
        # Verify the shared primitive started with exactly 312 cards.
        self.assertEqual(312 - cards_drawn, len(first_state["shoe"]))

    # Confirm consecutive ranks push automatically without consuming a third card.
    def test_consecutive_cards_push_without_third_card(self):
        # Arrange consecutive five and six with an unused ace behind them.
        state, round_item = self.start("5C", "6D", "AS", wager=3)
        # Verify the stable automatic outcome and terminal phase.
        self.assertEqual(("settled", "consecutive_push"), (round_item["phase"], round_item["outcome"]))
        # Verify no third card was exposed or consumed.
        self.assertIsNone(round_item["third_card"])
        # Verify the unused third fixture card remains in the persisted shoe.
        self.assertEqual(["AS"], state["shoe"])
        # Verify only the original stake is returned.
        self.assertEqual(3.0, round_item["payout"])
        # Verify wager debit precedes the push refund credit.
        self.assertEqual(["debit", "credit"], [intent["direction"] for intent in round_item["ledger_intents"]])
        # Verify the two prepared amounts are equal and non-zero.
        self.assertEqual([3.0, 3.0], [intent["amount"] for intent in round_item["ledger_intents"]])

    # Confirm a matching pair card pays eleven-to-one profit plus returned stake.
    def test_pair_three_of_a_kind_returns_twelve_times_ante(self):
        # Arrange three sevens across different suits.
        unused_state, round_item = self.start("7C", "7D", "7H", wager=2)
        # Verify the pair path consumed and exposed the third card.
        self.assertEqual("7", round_item["third_card"]["rank"])
        # Verify the stable winning outcome and fixed odds.
        self.assertEqual(("three_of_a_kind", 11), (round_item["outcome"], round_item["odds"]))
        # Verify returned credit includes the stake plus eleven-to-one profit.
        self.assertEqual(24.0, round_item["payout"])
        # Verify one aggregate payout follows one wager debit.
        self.assertEqual(["RED_DOG_WAGER_DEBIT", "RED_DOG_PAYOUT_CREDIT"], [intent["transaction_type"] for intent in round_item["ledger_intents"]])

    # Confirm a non-matching third card after a pair returns only the ante.
    def test_pair_nonmatch_is_push(self):
        # Arrange a pair of sevens followed by a nine.
        unused_state, round_item = self.start("7C", "7D", "9H", wager=2)
        # Verify the distinct pair-push result key.
        self.assertEqual("pair_push", round_item["outcome"])
        # Verify only the original stake returns.
        self.assertEqual(2.0, round_item["payout"])
        # Verify the refund uses the game-owned credit type.
        self.assertEqual("RED_DOG_REFUND_CREDIT", round_item["ledger_intents"][-1]["transaction_type"])

    # Confirm every spread row pays its documented profit odds on a call.
    def test_call_uses_all_spread_paytable_rows(self):
        # Define opening and winning result fixtures for spreads one, two, three, four, and eleven.
        vectors = [
            ("3C", "5D", "4H", 1, 5),  # Cover the five-to-one spread-one row.
            ("3C", "6D", "4H", 2, 4),  # Cover the four-to-one spread-two row.
            ("3C", "7D", "5H", 3, 2),  # Cover the two-to-one spread-three row.
            ("3C", "8D", "5H", 4, 1),  # Cover the even-money spread-four row.
            ("2C", "AD", "KH", 11, 1),  # Cover the maximum even-money spread.
        ]
        # Exercise every required payout row independently.
        for first, second, third, spread, odds in vectors:
            # Preserve vector context in any failure output.
            with self.subTest(spread=spread):
                # Create the decision-ready opening deal.
                state, round_item = self.start(first, second, third, wager=1, action_id=f"start-spread-{spread}")
                # Verify opening state exposes the expected raise decision.
                self.assertEqual(("raise_decision", "spread_pending"), (round_item["phase"], round_item["outcome"]))
                # Verify calculated spread and paytable odds before the result card.
                self.assertEqual((spread, odds), (round_item["spread"], round_item["odds"]))
                # Complete the hand without a raise.
                engine.call_round(state, round_item["round_id"], f"call-spread-{spread}", completed_at="2026-07-14T00:00:01.000Z")
                # Verify strict-between winning classification.
                self.assertEqual("spread_win", round_item["outcome"])
                # Verify returned credit equals stake plus the documented profit.
                self.assertEqual(float(odds + 1), round_item["payout"])

    # Confirm boundary matches and outside ranks lose rather than push.
    def test_spread_requires_third_card_strictly_between(self):
        # Arrange a third card equal to the lower opening boundary.
        state, round_item = self.start("3C", "7D", "3H", wager=2)
        # Complete the ante-only call.
        engine.call_round(state, round_item["round_id"], "call-boundary", completed_at="2026-07-14T00:00:01.000Z")
        # Verify an equal boundary is a loss.
        self.assertEqual("spread_loss", round_item["outcome"])
        # Verify a loss creates no returned credit.
        self.assertEqual(0.0, round_item["payout"])
        # Verify only the original wager debit remains prepared.
        self.assertEqual(1, len(round_item["ledger_intents"]))

    # Confirm a raise matches the ante and applies odds to both committed stakes.
    def test_raise_matches_ante_and_pays_both_stakes(self):
        # Arrange a spread-three win on the third card.
        state, round_item = self.start("3C", "7D", "5H", wager=2)
        # Complete the matching raise action.
        engine.raise_round(state, round_item["round_id"], "raise-win-1", completed_at="2026-07-14T00:00:01.000Z")
        # Verify the raise equals the ante and doubles committed stakes.
        self.assertEqual((2.0, 4.0), (round_item["raise_wager"], round_item["total_wager"]))
        # Verify spread-three two-to-one profit applies to all four committed tokens.
        self.assertEqual(12.0, round_item["payout"])
        # Verify wager debit, raise debit, and payout credit remain ordered.
        self.assertEqual(["RED_DOG_WAGER_DEBIT", "RED_DOG_RAISE_DEBIT", "RED_DOG_PAYOUT_CREDIT"], [intent["transaction_type"] for intent in round_item["ledger_intents"]])

    # Confirm a losing raise keeps both debits and creates no zero credit.
    def test_losing_raise_has_two_debits_and_no_credit(self):
        # Arrange an outside third rank for a normal spread.
        state, round_item = self.start("3C", "7D", "KH", wager=2)
        # Complete the matching raise action.
        engine.raise_round(state, round_item["round_id"], "raise-loss-1", completed_at="2026-07-14T00:00:01.000Z")
        # Verify terminal loss and zero returned credit.
        self.assertEqual(("spread_loss", 0.0), (round_item["outcome"], round_item["payout"]))
        # Verify both committed stakes are represented by debit intents only.
        self.assertEqual(["debit", "debit"], [intent["direction"] for intent in round_item["ledger_intents"]])

    # Confirm malformed wagers and stale state transitions fail before mutation.
    def test_validation_and_phase_conflicts_fail_closed(self):
        # Reject boolean wagers despite Python numeric inheritance.
        with self.assertRaises(ValidationError):
            # Exercise the boolean boundary.
            engine.normalize_wager(True)
        # Reject non-finite wagers.
        with self.assertRaises(ValidationError):
            # Exercise infinity handling.
            engine.normalize_wager(float("inf"))
        # Build one unresolved normal spread.
        state, round_item = self.start("3C", "7D", "5H", wager=1)
        # Reject another round while the decision remains active.
        with self.assertRaises(ConflictError):
            # Attempt an overlapping wager with a different action id.
            engine.start_round(state, "session-player", 1, "overlap-action", round_id="rd_other", created_at="2026-07-14T00:00:00.000Z")
        # Complete the original call once.
        engine.call_round(state, round_item["round_id"], "call-once-1", completed_at="2026-07-14T00:00:01.000Z")
        # Reject a second engine transition after terminal settlement.
        with self.assertRaises(ConflictError):
            # Attempt a stale raise under a new action id.
            engine.raise_round(state, round_item["round_id"], "raise-stale-1", completed_at="2026-07-14T00:00:02.000Z")

    # Confirm public history is bounded without deleting exact-retry round bodies.
    def test_public_history_is_bounded_but_retry_state_is_retained(self):
        # Build one long-lived player document.
        state = engine.default_state()
        # Create one more settled round than the public history limit.
        for index in range(engine.ROUND_HISTORY_LIMIT + 1):
            # Install a fresh deterministic consecutive fixture for this round.
            state["shoe"] = ["AS", "6D", "5C"]
            # Create an automatically settled push with unique ids.
            engine.start_round(state, "session-player", 1, f"history-action-{index}", round_id=f"rd_{index}", created_at="2026-07-14T00:00:00.000Z")
        # Verify all internal round bodies remain available for exact retries.
        self.assertEqual(engine.ROUND_HISTORY_LIMIT + 1, len(state["rounds"]))
        # Verify only the newest bounded window is public.
        self.assertEqual(engine.ROUND_HISTORY_LIMIT, len(engine.public_state(state)["rounds"]))


# Run this focused suite when invoked directly by a bounded worker.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
