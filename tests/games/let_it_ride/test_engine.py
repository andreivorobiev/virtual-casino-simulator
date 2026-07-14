"""Pure Let It Ride engine tests for issue #134."""

# Import dependency-free unittest coverage for the isolated engine.
import unittest

# Import only the game-local engine under test.
from casino.games.let_it_ride import engine
# Import public conflict errors for stale-action assertions.
from casino.errors import ConflictError


# Verify staged Let It Ride rules without router or ledger dependencies.
class LetItRideEngineTests(unittest.TestCase):
    # Build a deterministic state whose final hand is a pair of tens.
    def pair_tens_state(self) -> dict:
        # Start from the production player-scoped schema.
        state = engine.default_state()
        # Arrange pop-order cards as player tens, kicker, and two community cards.
        state["shoe"] = ["9H", "4S", "3C", "10D", "10H"]
        # Assign stable deck telemetry for response assertions.
        state["shoe_id"] = "fixture-pair-tens"
        # Return the deterministic document.
        return state

    # Confirm pair tens qualifies while a lower pair does not.
    def test_pair_of_tens_or_better_threshold(self):
        # Evaluate a qualifying pair of tens.
        tens = engine.classify_hand(["10H", "10D", "3C", "4S", "9H"])
        # Verify the Let It Ride threshold is tens, not jacks.
        self.assertEqual(("pair_of_tens_or_better", 1), tens)
        # Evaluate a nonqualifying pair of nines.
        nines = engine.classify_hand(["9H", "9D", "3C", "4S", "8H"])
        # Verify lower pairs do not return play-token credit.
        self.assertEqual(("no_win", 0), nines)

    # Confirm community cards reveal only at the documented decision beats.
    def test_community_cards_are_reload_safe_and_hidden_until_revealed(self):
        # Seed a deterministic pair-tens round.
        state = self.pair_tens_state()
        # Start one prepared round without ledger side effects.
        round_item = engine.start_round(state, "player-one", 5, "deal-action-001", round_id="lir_test_1", created_at="now")
        # Verify no community cards are public before the first decision.
        self.assertEqual([None, None], engine.public_round(round_item)["community_cards"])
        # Advance the first decision without pulling a wager.
        engine.advance_decision(state, "lir_test_1", "first", "ride", "ride-action-001", completed_at="later")
        # Verify exactly one community card is public after the first decision.
        self.assertEqual(["4S", None], [card["code"] if card else None for card in engine.public_round(round_item)["community_cards"]])
        # Advance the second decision and settle.
        engine.advance_decision(state, "lir_test_1", "second", "ride", "ride-action-002", completed_at="done")
        # Verify both community cards are public after settlement.
        self.assertEqual(["4S", "9H"], [card["code"] if card else None for card in engine.public_round(round_item)["community_cards"]])

    # Confirm pull decisions return eligible wagers while remaining wagers settle.
    def test_pull_refund_and_final_payout_are_prepared_in_order(self):
        # Seed a deterministic pair-tens round.
        state = self.pair_tens_state()
        # Start one prepared round with a five-token base unit.
        round_item = engine.start_round(state, "player-one", 5, "deal-action-002", round_id="lir_test_2", created_at="now")
        # Pull back the first eligible wager.
        engine.advance_decision(state, "lir_test_2", "first", "pull", "pull-action-001", completed_at="middle")
        # Let the remaining two wagers ride through final settlement.
        engine.advance_decision(state, "lir_test_2", "second", "ride", "ride-action-002", completed_at="done")
        # Verify one unit was returned before final settlement.
        self.assertEqual(1, round_item["withdrawn_units"])
        # Verify two units remained active for the pair-tens payout.
        self.assertEqual(2, round_item["active_units"])
        # Verify returned stake plus even-profit payout is prepared.
        self.assertEqual(20.0, round_item["payout"])
        # Verify net equals refund plus payout minus the initial three-unit wager.
        self.assertEqual(10.0, round_item["net"])
        # Verify ledger intents remain ordered as wager, refund, then payout.
        self.assertEqual(["LET_IT_RIDE_WAGER_DEBIT", "LET_IT_RIDE_REFUND_CREDIT", "LET_IT_RIDE_PAYOUT_CREDIT"], [intent["transaction_type"] for intent in round_item["ledger_intents"]])

    # Confirm out-of-order decisions fail closed.
    def test_second_decision_before_first_is_rejected(self):
        # Seed a deterministic pair-tens round.
        state = self.pair_tens_state()
        # Start one prepared round.
        engine.start_round(state, "player-one", 5, "deal-action-003", round_id="lir_test_3", created_at="now")
        # Reject a second decision before the first reveal.
        with self.assertRaises(ConflictError):
            # Attempt the invalid phase transition.
            engine.advance_decision(state, "lir_test_3", "second", "ride", "ride-action-003", completed_at="bad")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
