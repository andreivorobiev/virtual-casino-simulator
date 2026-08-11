# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Three Card Poker rule and deterministic-state tests."""

# Import unittest for dependency-free focused coverage.
import unittest

# Import the public validation error used by wager normalization.
from casino.errors import ValidationError
# Import only the game-local pure engine under test.
from casino.games.three_card_poker import engine


# Verify hand ordering, qualification, payouts, and public privacy.
class ThreeCardPokerEngineTests(unittest.TestCase):
    # Build a decision-ready round from an explicit six-card test plan.
    def round_from(self, player_cards, dealer_cards, *, ante=10, pair_plus=0):
        # Create a fresh player-scoped document.
        state = engine.default_state()
        # Deal the explicit player and dealer cards without production randomness.
        round_item = engine.start_round(state, "player-1", ante, pair_plus, "deal-test-1", round_id="tcp_round_1", created_at="2026-07-14T00:00:00.000Z", deck=[*player_cards, *dealer_cards])
        # Return both state and its owned mutable round.
        return state, round_item

    # Confirm every category follows Three Card Poker rather than five-card ordering.
    def test_category_order_and_tiebreaks(self):
        # Define one deterministic fixture for every ascending category.
        fixtures = [
            (["2C", "5D", "9H"], "high_card"),  # Use an unpaired mixed-suit hand.
            (["4C", "4D", "9H"], "pair"),  # Use one pair and kicker.
            (["2H", "6H", "9H"], "flush"),  # Use a non-consecutive flush.
            (["4C", "5D", "6H"], "straight"),  # Use a mixed-suit straight.
            (["7C", "7D", "7H"], "three_of_a_kind"),  # Use three equal ranks.
            (["QH", "KH", "AH"], "straight_flush"),  # Use the strongest category.
        ]
        # Evaluate each fixture through the game-local evaluator.
        ranks = [engine.evaluate_three(cards) for cards, _ in fixtures]
        # Verify stable machine names in expected order.
        self.assertEqual([name for _, name in fixtures], [rank.name for rank in ranks])
        # Verify numeric comparison keys increase with category strength.
        self.assertEqual(sorted(rank.comparison_key for rank in ranks), [rank.comparison_key for rank in ranks])

    # Confirm ace-low and ace-high straights use the chosen fixed ordering.
    def test_ace_low_and_ace_high_straights(self):
        # Evaluate the lowest permitted straight.
        ace_low = engine.evaluate_three(["AC", "2D", "3H"])
        # Evaluate the highest permitted straight.
        ace_high = engine.evaluate_three(["QC", "KD", "AH"])
        # Verify ace-deuce-trey normalizes to three-high.
        self.assertEqual(("straight", (3,)), (ace_low.name, ace_low.tiebreak))
        # Verify queen-king-ace normalizes to ace-high.
        self.assertEqual(("straight", (14,)), (ace_high.name, ace_high.tiebreak))
        # Verify the ace-high run compares stronger.
        self.assertGreater(ace_high.comparison_key, ace_low.comparison_key)

    # Confirm dealer qualification begins at queen-high and includes made hands.
    def test_dealer_qualification(self):
        # Verify jack-high does not qualify.
        self.assertFalse(engine.dealer_qualifies(engine.evaluate_three(["JC", "9D", "2H"])))
        # Verify queen-high qualifies.
        self.assertTrue(engine.dealer_qualifies(engine.evaluate_three(["QC", "9D", "2H"])))
        # Verify even a low pair qualifies automatically.
        self.assertTrue(engine.dealer_qualifies(engine.evaluate_three(["2C", "2D", "3H"])))

    # Confirm optional side-bet validation rejects negative sub-cent values before rounding.
    def test_negative_pair_plus_never_normalizes_to_zero(self):
        # Assert a negative fraction cannot cross the optional-zero boundary.
        with self.assertRaisesRegex(ValidationError, "pair_plus"):
            # Exercise the shared bet normalization path.
            engine.normalize_bets(10, -0.001)

    # Confirm seed injection reproduces the same private deal without caller mutation.
    def test_seeded_deal_is_deterministic_and_dealer_is_hidden(self):
        # Create independent state for the first seeded deal.
        first_state = engine.default_state()
        # Create independent state for the second seeded deal.
        second_state = engine.default_state()
        # Deal the first round from the shared seed seam.
        first = engine.start_round(first_state, "player-1", 5, 0, "seed-a", seed="same-seed", round_id="tcp_one", created_at="2026-07-14T00:00:00.000Z")
        # Deal the second round from identical entropy.
        second = engine.start_round(second_state, "player-1", 5, 0, "seed-b", seed="same-seed", round_id="tcp_two", created_at="2026-07-14T00:00:00.000Z")
        # Verify both complete private card plans match.
        self.assertEqual((first["player_hand"], first["dealer_hand"]), (second["player_hand"], second["dealer_hand"]))
        # Project the first round through the public privacy adapter.
        public = engine.public_round(first)
        # Verify player cards are immediately visible.
        self.assertEqual(first["player_hand"], public["player_hand"])
        # Verify every dealer card remains hidden during the decision.
        self.assertEqual(["??", "??", "??"], public["dealer_hand"])
        # Verify the private dealer rank is also hidden.
        self.assertIsNone(public["dealer_rank"])

    # Confirm the chosen Ante Bonus A and Pair Plus C returns use profit odds.
    def test_play_settlement_uses_fixed_paytables(self):
        # Deal a player ace-high straight flush against a qualifying queen-high dealer.
        state, round_item = self.round_from(["AS", "KS", "QS"], ["QH", "9D", "2C"], ante=10, pair_plus=5)
        # Commit to Play and prepare all terminal wallet movements.
        engine.decide(state, round_item["round_id"], "play", "decision-play-1", completed_at="2026-07-14T00:00:01.000Z")
        # Verify the matching Play wager equals Ante.
        self.assertEqual(10.0, round_item["play_wager"])
        # Verify both main wagers pay even money for a qualifying player win.
        self.assertEqual(40.0, round_item["payout_breakdown"]["ante_play_return"])
        # Verify Ante Bonus A contributes five units of profit.
        self.assertEqual(50.0, round_item["payout_breakdown"]["ante_bonus"])
        # Verify Pair Plus C returns stake plus forty units of profit.
        self.assertEqual(205.0, round_item["payout_breakdown"]["pair_plus_return"])
        # Verify one aggregate payout total contains every component.
        self.assertEqual(295.0, round_item["total_payout"])
        # Verify net subtracts initial and Play debits.
        self.assertEqual(270.0, round_item["net"])
        # Verify intents are ordered initial debit, Play debit, then payout credit.
        self.assertEqual(["initial_wager", "play_wager", "settlement"], [intent["details"]["stage"] for intent in round_item["ledger_intents"]])
        # Verify decision movement identifiers include round and client action ids.
        self.assertTrue(all(round_item["round_id"] in intent["action_id"] for intent in round_item["ledger_intents"][1:]))

    # Confirm dealer qualification, ties, losses, and independent Ante Bonus returns.
    def test_main_game_settlement_paths(self):
        # Describe deterministic hands and their expected main-game results.
        cases = [
            (["7C", "4D", "2H"], ["JC", "9D", "3S"], "dealer_not_qualified", 30.0, 0.0),  # Return winning Ante plus pushed Play against jack-high.
            (["QC", "9D", "2H"], ["QH", "9C", "2D"], "tie", 20.0, 0.0),  # Return both stakes when equal queen-high hands tie.
            (["QC", "8D", "2H"], ["KH", "3C", "2D"], "dealer_win", 0.0, 0.0),  # Lose both main wagers to a qualifying king-high dealer.
            (["2C", "3D", "4H"], ["QS", "KH", "AD"], "dealer_win", 0.0, 10.0),  # Preserve the straight Ante Bonus despite a stronger dealer straight.
        ]
        # Exercise every fixed settlement branch without random deals.
        for player_cards, dealer_cards, outcome, main_return, ante_bonus in cases:
            # Label failures with the expected public outcome.
            with self.subTest(outcome=outcome, player_cards=player_cards):
                # Build one isolated decision-ready round.
                state, round_item = self.round_from(player_cards, dealer_cards, ante=10)
                # Commit Play so dealer qualification and all returns are calculated.
                engine.decide(state, round_item["round_id"], "play", f"decision-{outcome}", completed_at="2026-07-14T00:00:01.000Z")
                # Verify the localized-outcome key selected by the rules branch.
                self.assertEqual(outcome, round_item["outcome"])
                # Verify the complete Ante-and-Play returned-credit component.
                self.assertEqual(main_return, round_item["payout_breakdown"]["ante_play_return"])
                # Verify Ante Bonus remains independent of dealer comparison.
                self.assertEqual(ante_bonus, round_item["payout_breakdown"]["ante_bonus"])

    # Confirm Fold forfeits both initial wager components without another movement.
    def test_fold_forfeits_ante_and_pair_plus(self):
        # Deal a side-bet-winning hand to prove Fold suppresses its return.
        state, round_item = self.round_from(["AS", "KS", "QS"], ["QH", "9D", "2C"], ante=10, pair_plus=5)
        # Fold the decision-ready round.
        engine.decide(state, round_item["round_id"], "fold", "decision-fold-1", completed_at="2026-07-14T00:00:01.000Z")
        # Verify no Play wager was added.
        self.assertEqual(0.0, round_item["play_wager"])
        # Verify neither initial component returns value.
        self.assertEqual(0.0, round_item["total_payout"])
        # Verify net reflects the complete initial forfeiture.
        self.assertEqual(-15.0, round_item["net"])
        # Verify only the original aggregate debit remains prepared.
        self.assertEqual(1, len(round_item["ledger_intents"]))
        # Verify dealer cards become visible after terminal decision preparation.
        self.assertNotIn("??", engine.public_round(round_item)["dealer_hand"])


# Run this focused suite directly for worker validation.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
