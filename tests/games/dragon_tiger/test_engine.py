# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic standard-8d Dragon Tiger engine tests."""

# Import standard unit-test support.
import unittest

# Import shared card construction for valid deterministic eight-deck fixtures.
from casino.core.cards import create_deck
# Import the pure engine under test.
from casino.games.dragon_tiger import engine


# Build a complete valid shoe with a controlled pop/deal sequence.
def rigged_shoe(dragon_card="KS", tiger_card="QH"):
    # Start from exactly eight standard decks.
    cards = [card.code for card in create_deck(engine.DECK_COUNT)]
    # Define three burns followed by Dragon-first and Tiger-second cards.
    pop_order = ["2C", "3D", "4H", dragon_card, tiger_card]
    # Remove one occurrence of every controlled card from the multiset.
    for card in pop_order:
        # Preserve exact eight-deck counts while relocating the card.
        cards.remove(card)
    # Append in reverse so stack pops occur in documented order.
    cards.extend(reversed(pop_order))
    # Return the complete deterministic standard-8d shoe.
    return cards


# Verify fixed rules, rank comparison, shoe lifecycle, and payouts.
class DragonTigerEngineTests(unittest.TestCase):
    # Confirm the named profile installs, burns, and deals in the required order.
    def test_standard_shoe_burn_and_dragon_first_deal(self):
        # Build fresh persistent state.
        state = engine.default_state()
        # Prepare a deterministic Dragon-winning round.
        prepared = engine.prepare_action(state, player_id="player-a", action_id="action-001", bet="dragon", wager=5, fingerprint="fingerprint", round_id="dt_round", created_at="2026-07-14T00:00:00Z", shoe_factory=lambda: rigged_shoe("KS", "QH"))
        # Verify the first post-burn card belongs to Dragon.
        self.assertEqual("KS", prepared["dragon_card"])
        # Verify the second post-burn card belongs to Tiger.
        self.assertEqual("QH", prepared["tiger_card"])
        # Verify three burns and two dealt cards leave 411 cards.
        self.assertEqual(411, len(state["shoe"]))
        # Verify the public shoe counter begins at one.
        self.assertEqual(1, state["shoe_number"])

    # Confirm ace-low comparison and suit-insensitive ties.
    def test_rank_only_comparison_uses_ace_low(self):
        # Verify a deuce beats an ace.
        self.assertEqual("tiger", engine.winner_for("AS", "2C"))
        # Verify equal ranks tie across different suits.
        self.assertEqual("tie", engine.winner_for("KH", "KS"))
        # Verify king remains the highest rank.
        self.assertEqual("dragon", engine.winner_for("KD", "QC"))

    # Confirm all specified returned-credit cases.
    def test_standard_payouts_and_half_loss(self):
        # Verify a Dragon win returns stake plus 1:1 winnings.
        self.assertEqual({"outcome": "win", "total_return": 20.0, "net": 10.0}, engine.settle("dragon", 10, "dragon"))
        # Verify an eleven-to-one Tie win returns twelve times stake.
        self.assertEqual({"outcome": "win", "total_return": 120.0, "net": 110.0}, engine.settle("tie", 10, "tie"))
        # Verify a Dragon bet returns half its stake on a tie.
        self.assertEqual({"outcome": "half_loss", "total_return": 5.0, "net": -5.0}, engine.settle("dragon", 10, "tie"))
        # Verify an unmatched bet loses fully without a credit.
        self.assertEqual({"outcome": "loss", "total_return": 0.0, "net": -10.0}, engine.settle("tiger", 10, "dragon"))

    # Confirm half-loss credits use explicit ledger-precision half-up rounding.
    def test_odd_cent_half_loss_rounds_half_up(self):
        # Verify fifteen cents returns eight cents rather than float or bankers rounding.
        self.assertEqual({"outcome": "half_loss", "total_return": 0.08, "net": -0.07}, engine.settle("dragon", 0.15, "tie"))
        # Verify twenty-five cents returns thirteen cents under the same policy.
        self.assertEqual({"outcome": "half_loss", "total_return": 0.13, "net": -0.12}, engine.settle("tiger", 0.25, "tie"))
        # Verify the minimum one-cent wager cannot create a fractional-cent credit.
        self.assertEqual({"outcome": "half_loss", "total_return": 0.01, "net": 0.0}, engine.settle("dragon", 0.01, "tie"))

    # Confirm stable request identity is semantic and player-scoped.
    def test_fingerprint_and_round_identity_are_deterministic(self):
        # Build the same normalized request fingerprint twice.
        first = engine.request_fingerprint("dragon", 2.0)
        # Rebuild the fingerprint from the same semantic input.
        second = engine.request_fingerprint("dragon", 2.0)
        # Verify exact stability.
        self.assertEqual(first, second)
        # Verify another bet changes conflict-detection proof.
        self.assertNotEqual(first, engine.request_fingerprint("tiger", 2.0))
        # Verify round IDs remain stable for one player/action pair.
        self.assertEqual(engine.round_id_for("player-a", "action-001"), engine.round_id_for("player-a", "action-001"))
        # Verify another authenticated player receives another round identity.
        self.assertNotEqual(engine.round_id_for("player-a", "action-001"), engine.round_id_for("player-b", "action-001"))

    # Confirm the fifty-two-card reserve triggers before an incomplete round.
    def test_cut_reserve_requires_fifty_four_remaining_cards(self):
        # Build state exactly large enough for one final two-card deal.
        state = {**engine.default_state(), "shoe": ["AS"] * 54}
        # Allow a round at reserve plus two cards.
        self.assertFalse(engine.shuffle_pending(state))
        # Remove one card below the required threshold.
        state["shoe"].pop()
        # Require replacement before another round.
        self.assertTrue(engine.shuffle_pending(state))


# Run this focused suite directly when requested.
if __name__ == "__main__":
    # Exit through standard unittest result handling.
    unittest.main()
