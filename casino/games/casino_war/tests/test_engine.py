"""Deterministic Casino War engine tests for issue #82."""

# Import unittest for repository-standard dependency-free tests.
import unittest

# Import the pure engine under test.
from casino.games.casino_war import engine
# Import shared domain errors for invalid transition assertions.
from casino.errors import ConflictError, ValidationError


# Verify rank comparison, standard tie choices, and deterministic shoe behavior.
class CasinoWarEngineTests(unittest.TestCase):
    # Build a fresh state with a caller-arranged draw order.
    def state_with_draws(self, draw_order: list[str]) -> dict:
        # Start from production table rules and storage shape.
        state = engine.default_state()
        # Reverse draw order because the engine pops cards from the shoe end.
        state["shoe"] = list(reversed(draw_order))
        # Identify the deterministic fixture shoe.
        state["shoe_id"] = "fixture-shoe"
        # Return the prepared state.
        return state

    # Confirm suits never break ties and ace ranks high.
    def test_compare_cards_uses_rank_only(self):
        # Assert equal ranks tie across different suits.
        self.assertEqual(engine.compare_cards("7H", "7S"), 0)
        # Assert ace beats king.
        self.assertEqual(engine.compare_cards("AC", "KD"), 1)
        # Assert deuce loses to three.
        self.assertEqual(engine.compare_cards("2C", "3C"), -1)

    # Confirm an initial win requests one debit and the full even-money return.
    def test_initial_player_win_emits_ordered_ledger_intents(self):
        # Arrange an ace for the player and deuce for the dealer plus war capacity.
        state = self.state_with_draws(["AH", "2S", "3C", "4C", "5C", "6C", "7C"])
        # Deal the deterministic round.
        round_item = engine.start_round(state, "player-1", 25, "action-start-001", round_id="cw-test-1", created_at="2026-07-13T00:00:00Z")
        # Assert the expected terminal result and total return.
        self.assertEqual((round_item["outcome"], round_item["payout"]), ("player_win", 50.0))
        # Assert debit precedes settlement credit.
        self.assertEqual([intent["direction"] for intent in round_item["ledger_intents"]], ["debit", "credit"])
        # Assert every instruction carries player, game, round, and stable action details.
        self.assertTrue(all(intent["player_id"] == "player-1" and intent["game"] == "casino_war" and intent["round_id"] == "cw-test-1" and intent["details"]["casino_war_action_id"] for intent in round_item["ledger_intents"]))

    # Confirm surrender returns exactly half of the original wager.
    def test_surrender_after_tie_returns_half_ante(self):
        # Arrange an initial seven tie plus enough remaining cards for state validity.
        state = self.state_with_draws(["7H", "7S", "2C", "3C", "4C", "5C", "6C"])
        # Deal into the explicit decision phase.
        round_item = engine.start_round(state, "player-1", 25, "action-start-002", round_id="cw-test-2")
        # Select surrender with its own command id.
        engine.surrender(state, round_item["round_id"], "action-surrender-001")
        # Assert the half-return rule and terminal outcome.
        self.assertEqual((round_item["outcome"], round_item["payout"]), ("surrender", 12.5))
        # Assert no matching war debit was created.
        self.assertEqual([intent["direction"] for intent in round_item["ledger_intents"]], ["debit", "credit"])

    # Confirm war burns three cards and a second tie favors the player.
    def test_war_burns_three_and_second_tie_favors_player(self):
        # Arrange initial sevens, three burns, and tied nines in exact deal order.
        state = self.state_with_draws(["7H", "7S", "2D", "3D", "4D", "9H", "9S"])
        # Deal the initial tie.
        round_item = engine.start_round(state, "player-1", 40, "action-start-003", round_id="cw-test-3")
        # Resolve the tie through war.
        engine.go_to_war(state, round_item["round_id"], "action-war-001")
        # Assert exactly three audit-visible burn cards.
        self.assertEqual([card["code"] for card in round_item["burn_cards"]], ["2D", "3D", "4D"])
        # Assert the documented player-favoring second-tie outcome.
        self.assertEqual((round_item["outcome"], round_item["payout"]), ("war_tie_win", 120.0))
        # Assert ante debit, war debit, and final credit remain ordered.
        self.assertEqual([intent["direction"] for intent in round_item["ledger_intents"]], ["debit", "debit", "credit"])

    # Confirm a player cannot bypass the required decision state.
    def test_invalid_decisions_fail_closed(self):
        # Arrange a non-tie initial win.
        state = self.state_with_draws(["KH", "2S", "3C", "4C", "5C", "6C", "7C"])
        # Deal the terminal comparison.
        round_item = engine.start_round(state, "player-1", 10, "action-start-004", round_id="cw-test-4")
        # Assert war is rejected outside the tie decision phase.
        with self.assertRaises(ConflictError):
            # Attempt the invalid transition.
            engine.go_to_war(state, round_item["round_id"], "action-war-002")
        # Assert invalid wager input never creates a new round.
        with self.assertRaises(ValidationError):
            # Attempt a zero-value wager in fresh state.
            engine.start_round(self.state_with_draws(["AH", "2S", "3C", "4C", "5C", "6C", "7C"]), "player-1", 0, "action-start-005")


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest discovery for this file.
    unittest.main()
