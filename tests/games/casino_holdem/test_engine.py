"""Deterministic rule tests for issue #139 and POKER-001."""

# Import the dependency-free standard test runner.
import unittest

# Import shared public errors for invalid transition assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated game engine under test.
from casino.games.casino_holdem import engine


# Verify table layout, dealer qualification, call payouts, and fold behavior.
class CasinoHoldemEngineTests(unittest.TestCase):
    # Build one prepared round with explicitly controlled cards.
    def round(self, fixture, wager=10):
        # Delegate to the production state constructor with stable audit fields.
        return engine.create_round("session-player", wager, "deal-1", round_id="choldem_0123456789abcdef01234567", created_at="2026-07-14T00:00:00Z", request_fingerprint="deal-fingerprint", fixture=fixture)

    # Confirm seeded deals are deterministic and contain no duplicate physical cards.
    def test_deal_layout_is_deterministic_without_replacement(self):
        # Deal one stable table layout from the seeded shared primitive.
        first = engine.deal_layout(seed="issue-139-deterministic")
        # Repeat the same deterministic fixture.
        second = engine.deal_layout(seed="issue-139-deterministic")
        # Verify stable test output for identical seeds.
        self.assertEqual(first, second)
        # Combine every dealt card for duplicate checks.
        all_cards = [*first["player_cards"], *first["dealer_cards"], *first["community_cards"]]
        # Verify one physical card is never dealt twice.
        self.assertEqual(len(all_cards), len(set(all_cards)))
        # Verify the public deal shape separates player, dealer, and board cards.
        self.assertEqual((2, 2, 5), (len(first["player_cards"]), len(first["dealer_cards"]), len(first["community_cards"])))

    # Confirm dealer qualification follows pair-of-fours-or-better.
    def test_dealer_qualification_boundary(self):
        # Build a dealer hand containing only a pair of threes.
        low_pair = engine.classify_hand(["3H", "3C", "9D", "JS", "2C", "5D", "8H"])
        # Build a dealer hand containing a pair of fours.
        qualifying_pair = engine.classify_hand(["4H", "4C", "9D", "JS", "2C", "5D", "8H"])
        # Verify low pair fails and four pair qualifies.
        self.assertEqual((False, True), (engine.dealer_qualifies(*low_pair), engine.dealer_qualifies(*qualifying_pair)))

    # Confirm non-qualifying dealer returns the call and pays ante by the player rank.
    def test_call_dealer_not_qualified_returns_call_and_pays_ante(self):
        # Build a board where the player makes a flush and dealer has no qualifying hand.
        fixture = {"player_cards": ["AH", "9H"], "dealer_cards": ["2C", "7D"], "community_cards": ["KH", "4H", "8H", "QS", "3D"]}
        # Create the prepared post-flop round.
        round_state = self.round(fixture, wager=10)
        # Mark the ante as committed before a decision.
        round_state["ante_status"] = "complete"
        # Prepare a call action.
        engine.prepare_call(round_state, "decision-call", request_fingerprint="call-fingerprint")
        # Mark the call debit as committed before showdown.
        round_state["call_status"] = "complete"
        # Resolve the deterministic called showdown.
        engine.resolve_called_round(round_state, completed_at="2026-07-14T00:00:01Z")
        # Verify dealer qualification, outcome, returned credits, and net movement.
        self.assertEqual((False, "dealer_not_qualified", "flush", 30.0, 20.0, 50.0, 20.0), (round_state["dealer_qualifies"], round_state["outcome"], round_state["player_rank"], round_state["ante_credit"], round_state["call_credit"], round_state["payout"], round_state["net"]))
        # Verify the complete board and dealer cards are public after a called showdown.
        self.assertEqual((5, 2), (len(round_state["community_cards"]), len(round_state["dealer_cards"])))

    # Confirm a qualified dealer showdown pays both ante and call on a player win.
    def test_call_player_win_against_qualified_dealer(self):
        # Build a player straight against a dealer one-pair qualifying hand.
        fixture = {"player_cards": ["8H", "9D"], "dealer_cards": ["4S", "4C"], "community_cards": ["10C", "JH", "QS", "2D", "7C"]}
        # Create the prepared post-flop round.
        round_state = self.round(fixture, wager=5)
        # Mark the ante as committed before a decision.
        round_state["ante_status"] = "complete"
        # Prepare a call action.
        engine.prepare_call(round_state, "decision-call", request_fingerprint="call-fingerprint")
        # Mark the call debit as committed before showdown.
        round_state["call_status"] = "complete"
        # Resolve the deterministic called showdown.
        engine.resolve_called_round(round_state, completed_at="2026-07-14T00:00:01Z")
        # Verify straight ante return and even-money call return.
        self.assertEqual(("player_win", "straight", 10.0, 20.0, 30.0, 15.0), (round_state["outcome"], round_state["player_rank"], round_state["ante_credit"], round_state["call_credit"], round_state["payout"], round_state["net"]))

    # Confirm a fold never reveals hidden cards or creates returned-token credits.
    def test_fold_settles_without_revealing_hidden_cards(self):
        # Build any valid prepared round.
        fixture = {"player_cards": ["AH", "2D"], "dealer_cards": ["KC", "QS"], "community_cards": ["3H", "4D", "5S", "6C", "7H"]}
        # Create the prepared post-flop round.
        round_state = self.round(fixture, wager=6)
        # Mark the ante as committed before a decision.
        round_state["ante_status"] = "complete"
        # Fold the round through the engine transition.
        engine.fold_round(round_state, "decision-fold", completed_at="2026-07-14T00:00:01Z", request_fingerprint="fold-fingerprint")
        # Verify terminal fold state and net ante loss.
        self.assertEqual(("settled", "folded", 0.0, -6.0), (round_state["phase"], round_state["outcome"], round_state["payout"], round_state["net"]))
        # Verify dealer and future board cards remain private after a fold.
        self.assertNotIn("dealer_cards", engine.public_round(round_state))
        # Verify no returned-token settlement is pending.
        self.assertEqual("complete", round_state["settlement_status"])

    # Confirm malformed wagers, duplicate fixtures, and stale transitions fail closed.
    def test_invalid_boundaries_and_stale_transitions(self):
        # Reject boolean wagers despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed wager boundary.
            engine.normalize_wager(True)
        # Reject non-finite ledger amounts.
        with self.assertRaises(ValidationError):
            # Exercise the infinity boundary.
            engine.normalize_wager(float("inf"))
        # Reject unsupported decision aliases.
        with self.assertRaises(ValidationError):
            # Exercise the decision enumeration boundary.
            engine.normalize_decision("raise")
        # Reject one physical card dealt twice.
        with self.assertRaises(ValidationError):
            # Exercise duplicate fixture detection.
            engine.deal_layout(fixture={"player_cards": ["AH", "AH"], "dealer_cards": ["KC", "QS"], "community_cards": ["3H", "4D", "5S", "6C", "7H"]})
        # Build a valid folded round.
        folded = self.round({"player_cards": ["AH", "2D"], "dealer_cards": ["KC", "QS"], "community_cards": ["3H", "4D", "5S", "6C", "7H"]})
        # Apply the original terminal fold.
        engine.fold_round(folded, "fold-action", completed_at="2026-07-14T00:00:01Z", request_fingerprint="fold-fingerprint")
        # Reject a changed terminal action identity.
        with self.assertRaises(ConflictError):
            # Exercise the stale terminal transition.
            engine.fold_round(folded, "other-action", completed_at="2026-07-14T00:00:02Z", request_fingerprint="other")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
