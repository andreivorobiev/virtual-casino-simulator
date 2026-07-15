"""Deterministic rule tests for GitHub issue #132 Caribbean Stud."""

# Import the dependency-free standard test runner.
import unittest

# Import public errors for invalid transition assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated game engine under test.
from casino.games.caribbean_stud import engine


# Verify hand ranking, qualification, payout, and privacy rules.
class CaribbeanStudEngineTests(unittest.TestCase):
    # Build one prepared round with explicitly controlled cards.
    def round(self, player_hand=None, dealer_hand=None, ante=5):
        # Use a default high-card player hand.
        player_cards = player_hand or ["AS", "KD", "9C", "7H", "3S"]
        # Use a default dealer qualifying pair.
        dealer_cards = dealer_hand or ["2C", "2D", "8S", "10H", "QC"]
        # Delegate to the production state constructor with stable audit fields.
        return engine.create_round("session-player", ante, "deal-1", player_hand=player_cards, dealer_hand=dealer_cards, round_id="cs_0123456789abcdef01234567", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fingerprint")

    # Confirm deterministic deals use ten unique cards.
    def test_deal_hands_is_deterministic_without_replacement(self):
        # Deal one stable set of hands from the seeded shared primitive.
        first = engine.deal_hands(seed="issue-132-deterministic")
        # Repeat the same deterministic fixture.
        second = engine.deal_hands(seed="issue-132-deterministic")
        # Verify stable test output for identical seeds.
        self.assertEqual(first, second)
        # Verify player and dealer receive ten unique physical cards.
        self.assertEqual(10, len(set([*first[0], *first[1]])))

    # Confirm ace-king high is the minimum dealer qualification.
    def test_dealer_qualification_boundary(self):
        # Build a dealer ace-king high summary.
        ace_king = engine.hand_summary(["AS", "KD", "9C", "7H", "3S"])
        # Build a dealer ace-queen high summary.
        ace_queen = engine.hand_summary(["AS", "QD", "9C", "7H", "3S"])
        # Build a dealer one-pair summary.
        pair = engine.hand_summary(["2S", "2D", "9C", "7H", "3S"])
        # Verify the documented ace-king-or-better threshold.
        self.assertEqual((True, False, True), (engine.dealer_qualifies(ace_king), engine.dealer_qualifies(ace_queen), engine.dealer_qualifies(pair)))

    # Confirm dealer non-qualification pays ante and pushes call wager.
    def test_dealer_not_qualified_settlement(self):
        # Build a player pair against a dealer ace-queen high.
        round_state = self.round(player_hand=["4S", "4D", "9C", "7H", "3S"], dealer_hand=["AS", "QD", "10C", "8H", "2S"], ante=5)
        # Resolve the call through the pure engine.
        engine.settle_call(round_state, "call-1", completed_at="2026-07-14T00:00:01Z", request_fingerprint="call-fingerprint")
        # Verify the ante win plus call push total and net.
        self.assertEqual(("dealer_not_qualified", 20.0, 5.0), (round_state["outcome"], round_state["payout"], round_state["net"]))
        # Verify the dealer hand is revealed only after a call.
        self.assertEqual(["AS", "QD", "10C", "8H", "2S"], round_state["dealer_hand"])

    # Confirm qualified win, push, and dealer-win branches.
    def test_qualified_showdown_outcomes(self):
        # Define one vector for player win, exact push, and dealer win.
        vectors = [
            # Player pair outranks the dealer's lower pair.
            (["4S", "4D", "9C", "7H", "3S"], ["2S", "2D", "8C", "6H", "5S"], "player_win", 30.0, 15.0),
            # Matching ace-king high hands push.
            (["AS", "KD", "9C", "7H", "3S"], ["AH", "KC", "9D", "7C", "3D"], "push", 15.0, 0.0),
            # Dealer pair beats a qualifying player high-card hand.
            (["AS", "QD", "9C", "7H", "3S"], ["2S", "2D", "8C", "6H", "5S"], "dealer_win", 0.0, -15.0),
        ]
        # Exercise every qualified-showdown branch.
        for player_hand, dealer_hand, outcome, payout, net in vectors:
            # Keep vector details attached to assertion output.
            with self.subTest(outcome=outcome):
                # Build the controlled round.
                round_state = self.round(player_hand=player_hand, dealer_hand=dealer_hand, ante=5)
                # Resolve the call.
                engine.settle_call(round_state, f"call-{outcome}", completed_at="2026-07-14T00:00:01Z", request_fingerprint=f"fingerprint-{outcome}")
                # Verify documented outcome, returned tokens, and net.
                self.assertEqual((outcome, payout, net), (round_state["outcome"], round_state["payout"], round_state["net"]))

    # Confirm the royal flush call-bet table top award.
    def test_royal_flush_uses_top_call_odds(self):
        # Build a royal flush against a qualifying pair.
        round_state = self.round(player_hand=["AS", "KS", "QS", "JS", "10S"], dealer_hand=["2C", "2D", "8C", "6H", "5S"], ante=5)
        # Resolve the call through the pure engine.
        engine.settle_call(round_state, "call-royal", completed_at="2026-07-14T00:00:01Z", request_fingerprint="call-royal")
        # Verify the royal category and 100:1 call odds.
        self.assertEqual(("royal_flush", 100, 1020.0), (round_state["player_rank"]["name"], round_state["call_odds"], round_state["payout"]))

    # Confirm folding forfeits only the ante and does not reveal the dealer hand publicly.
    def test_fold_settlement_keeps_dealer_private(self):
        # Build a normal decision round.
        round_state = self.round(ante=7)
        # Resolve the fold.
        engine.settle_fold(round_state, "fold-1", completed_at="2026-07-14T00:00:01Z", request_fingerprint="fold-fingerprint")
        # Build the public version.
        public = engine.public_round(round_state)
        # Verify the terminal fold result and ante-only loss.
        self.assertEqual(("fold", 0.0, -7.0), (public["outcome"], public["payout"], public["net"]))
        # Verify the private dealer hand is not public after a fold.
        self.assertNotIn("_dealer_hand", public)
        # Verify no full dealer hand is published on fold.
        self.assertNotIn("dealer_hand", public)

    # Confirm malformed wagers, duplicate cards, and stale decisions fail closed.
    def test_invalid_boundaries_and_repeated_transition(self):
        # Reject boolean antes despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed ante boundary.
            engine.normalize_ante(True)
        # Reject non-finite ledger amounts.
        with self.assertRaises(ValidationError):
            # Exercise the infinity boundary.
            engine.normalize_ante(float("inf"))
        # Reject one physical card appearing twice across the round.
        with self.assertRaises(ValidationError):
            # Exercise the without-replacement invariant.
            self.round(player_hand=["AS", "AS", "9C", "7H", "3S"])
        # Settle one valid call before attempting a changed terminal action.
        settled = self.round()
        # Apply the original terminal call.
        engine.settle_call(settled, "call-original", completed_at="2026-07-14T00:00:01Z", request_fingerprint="original")
        # Reject a changed call identity after settlement.
        with self.assertRaises(ConflictError):
            # Exercise the stale terminal transition.
            engine.settle_call(settled, "call-other", completed_at="2026-07-14T00:00:02Z", request_fingerprint="other")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
