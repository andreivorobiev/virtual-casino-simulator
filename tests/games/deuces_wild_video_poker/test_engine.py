"""Focused deterministic engine tests for issue #92 and CARD-001/POKER-001."""

# Import deep-copy support for proving settled replay leaves state unchanged.
from copy import deepcopy
# Import the standard unit-test runner for dependency-free focused checks.
import unittest

# Import public conflict and validation errors for engine-boundary assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated Deuces Wild game engine under test.
from casino.games.deuces_wild_video_poker import engine


# Verify full-pay classification, deterministic cards, and strict input boundaries.
class DeucesWildVideoPokerEngineTests(unittest.TestCase):
    # Build one reproducible round with stable audit identifiers.
    def round(self, *, seed="issue-92"):
        # Delegate to the public constructor with injected deterministic metadata.
        return engine.create_round(
            "session-player",  # Bind the fixture to one authenticated player.
            2,  # Use a small positive two-token wager for payout calculations.
            "deal-action-0001",  # Supply a retry-safe client action identity.
            seed=seed,  # Control the complete initial and replacement card plan.
            round_id="dwvp_round",  # Keep assertions independent of digest formatting.
            created_at="2026-07-14T00:00:00.000Z",  # Freeze auditable creation metadata.
        )

    # Confirm all eleven frozen full-pay outcomes honor strongest-category precedence.
    def test_full_pay_outcomes_and_precedence(self):
        # Define one representative hand and expected multiplier for every paytable row.
        vectors = {
            "natural_royal_flush": (["AS", "KS", "QS", "JS", "10S"], 800),  # Cover the deuce-free top row.
            "four_deuces": (["2S", "2H", "2D", "2C", "9S"], 200),  # Rank four physical deuces above substitutions.
            "wild_royal_flush": (["2C", "AS", "KS", "QS", "JS"], 25),  # Rank a wild royal above straight flush and flush.
            "five_of_a_kind": (["2C", "2D", "2H", "KS", "KH"], 15),  # Rank five kings above four of a kind.
            "straight_flush": (["2C", "9S", "8S", "7S", "6S"], 9),  # Rank a suited wild straight above flush and straight.
            "four_of_a_kind": (["2C", "2D", "KS", "KH", "9C"], 5),  # Complete four kings from two fixed kings.
            "full_house": (["2C", "KS", "KH", "9S", "9H"], 3),  # Rank a wild full house above three of a kind.
            "flush": (["2C", "AS", "9S", "6S", "3S"], 2),  # Cover a non-straight wild flush.
            "straight": (["2C", "9S", "8D", "7H", "6S"], 2),  # Cover an unsuited wild straight.
            "three_of_a_kind": (["2C", "KS", "KH", "9D", "6C"], 1),  # Cover the lowest qualifying wild result.
            "no_win": (["AS", "KD", "9C", "6H", "3S"], 0),  # Cover a deuce-free high-card loss.
        }
        # Exercise every documented result through the public pure classifier.
        for expected_outcome, (cards, expected_multiplier) in vectors.items():
            # Preserve the expected paytable row in failure diagnostics.
            with self.subTest(outcome=expected_outcome):
                # Verify the strongest qualifying result and returned-credit multiplier.
                self.assertEqual((expected_outcome, expected_multiplier), engine.classify_hand(cards))
                # Verify the fixture remains aligned with the frozen exported paytable.
                self.assertEqual(expected_multiplier, engine.PAYTABLE[expected_outcome])
        # Verify the suite covers every row exactly once as the paytable evolves.
        self.assertEqual(set(engine.PAYTABLE), set(vectors))

    # Confirm one seed produces a stable complete standard-deck deal plan without duplicates.
    def test_deal_plan_is_deterministic_and_uses_each_card_once(self):
        # Build the first complete private card plan.
        first = self.round(seed="deterministic-plan")
        # Rebuild from identical injected inputs to model a pre-debit retry.
        second = self.round(seed="deterministic-plan")
        # Verify every persisted visible and private card is reproducible.
        self.assertEqual(first, second)
        # Combine the visible hand and private replacement order into one physical deck.
        complete_plan = [*first["initial_hand"], *first["_draw_pool"]]
        # Verify all fifty-two shared standard cards are present.
        self.assertEqual(52, len(complete_plan))
        # Verify no physical card appears twice anywhere in the deal plan.
        self.assertEqual(52, len(set(complete_plan)))
        # Verify ledger-safe plan fingerprints are stable for identical deals.
        self.assertEqual(engine.deal_plan_fingerprint(first), engine.deal_plan_fingerprint(second))
        # Build a distinct injected plan to prove the deterministic seam is effective.
        different = self.round(seed="different-plan")
        # Verify a different seed produces a different private proof.
        self.assertNotEqual(engine.deal_plan_fingerprint(first), engine.deal_plan_fingerprint(different))

    # Confirm held cards, retry behavior, and public sanitization survive reload-style use.
    def test_draw_preserves_holds_replays_and_hides_private_cards(self):
        # Build a deterministic pre-draw round containing its private replacement plan.
        round_state = self.round(seed="held-card-plan")
        # Preserve the source hand for exact positional assertions.
        initial_hand = list(round_state["initial_hand"])
        # Preserve the first two replacement cards consumed by positions one and three.
        replacements = list(round_state["_draw_pool"][:2])
        # Sanitize the pre-draw round as an API response would.
        public_before_draw = engine.public_round(round_state)
        # Verify the complete private replacement order is never exposed.
        self.assertNotIn("_draw_pool", public_before_draw)
        # Verify the private deal-plan digest is never exposed with public cards.
        self.assertNotIn("_deal_plan_fingerprint", public_before_draw)
        # Verify sanitization does not destroy the persisted reload-safe plan.
        self.assertIn("_draw_pool", round_state)
        # Persist an intentionally unsorted selection to verify canonical hold ordering.
        engine.set_holds(round_state, [4, 0, 2])
        # Verify the persisted selection is stable for reload and fingerprints.
        self.assertEqual([0, 2, 4], round_state["holds"])
        # Complete the one atomic draw with a retry-safe action identity.
        settled = engine.draw(round_state, "draw-action-0001", completed_at="2026-07-14T00:00:01.000Z")
        # Build the exact expected mix of held source cards and ordered replacements.
        expected_hand = [initial_hand[0], replacements[0], initial_hand[2], replacements[1], initial_hand[4]]
        # Verify the final hand preserves all selected positions and replacement order.
        self.assertEqual(expected_hand, settled["final_hand"])
        # Verify unused replacement cards are removed once the terminal hand is durable.
        self.assertNotIn("_draw_pool", settled)
        # Verify the original wager fingerprint remains stable after private cards are removed.
        self.assertEqual(round_state["_deal_plan_fingerprint"], engine.deal_plan_fingerprint(settled))
        # Snapshot every terminal field before exercising same-action replay.
        terminal_snapshot = deepcopy(settled)
        # Replay the same action after settlement with deliberately different metadata.
        replayed = engine.draw(settled, "draw-action-0001", completed_at="2099-01-01T00:00:00.000Z")
        # Verify the engine returns the same state object for an idempotent replay.
        self.assertIs(settled, replayed)
        # Verify replay cannot recompute cards, payout, or completion time.
        self.assertEqual(terminal_snapshot, replayed)
        # Reject a distinct action identity from settling the same round twice.
        with self.assertRaises(ConflictError):
            # Exercise the cross-action exactly-once boundary.
            engine.draw(settled, "draw-action-0002", completed_at="2026-07-14T00:00:02.000Z")

    # Confirm wagers reject Python edge cases and normalize ledger precision predictably.
    def test_wager_boundaries_and_precision(self):
        # List malformed, non-finite, too-small, and oversized wager values.
        invalid_values = (
            True,  # Reject booleans despite Python's integer inheritance.
            False,  # Reject the false boolean independently of the zero boundary.
            None,  # Reject absent wager input.
            "not-a-number",  # Reject non-numeric text.
            float("nan"),  # Reject non-comparable NaN values.
            float("inf"),  # Reject positive infinity before the maximum check.
            float("-inf"),  # Reject negative infinity before the minimum check.
            -1,  # Reject negative token movement.
            0,  # Reject a zero wager.
            0.004,  # Reject values that canonicalize below one cent.
            engine.MAX_WAGER + 0.01,  # Reject values above the maximum after cent rounding.
        )
        # Exercise every invalid wager through the public normalization boundary.
        for value in invalid_values:
            # Preserve the problematic value in failure diagnostics.
            with self.subTest(value=value):
                # Verify validation fails before any round state or entropy exists.
                with self.assertRaises(ValidationError):
                    # Normalize the candidate directly at the engine boundary.
                    engine.require_wager(value)
        # Verify fractional token input is canonicalized to ledger cent precision.
        self.assertEqual(1.24, engine.require_wager(1.239))
        # Verify a value rounding to the minimum cent remains accepted.
        self.assertEqual(0.01, engine.require_wager(0.009))
        # Verify the exact documented upper bound remains accepted.
        self.assertEqual(float(engine.MAX_WAGER), engine.require_wager(engine.MAX_WAGER))

    # Confirm hold selections reject invalid JSON shapes, values, and positions.
    def test_hold_boundaries_are_rejected_without_mutation(self):
        # List malformed arrays, element types, duplicates, and out-of-range positions.
        invalid_values = (
            None,  # Reject absent selection input.
            "0",  # Reject string iteration as card positions.
            {"position": 0},  # Reject mapping-shaped selections.
            (0,),  # Reject tuples because the API contract requires a JSON array.
            [True],  # Reject booleans despite Python's integer inheritance.
            [0.0],  # Reject floating-point positions.
            ["0"],  # Reject textual positions.
            [1, 1],  # Reject duplicate positions.
            [-1],  # Reject positions below the first card.
            [5],  # Reject positions beyond the fifth card.
        )
        # Exercise every invalid selection through the public normalization boundary.
        for value in invalid_values:
            # Preserve the problematic selection in failure diagnostics.
            with self.subTest(value=value):
                # Verify malformed holds fail with the public validation type.
                with self.assertRaises(ValidationError):
                    # Normalize the candidate directly at the engine boundary.
                    engine.require_holds(value)
        # Verify valid unsorted positions return one canonical ascending selection.
        self.assertEqual([0, 2, 4], engine.require_holds([4, 0, 2]))
        # Build a pristine round to prove a failed state mutation is atomic.
        round_state = self.round(seed="invalid-hold")
        # Attempt to persist a duplicate selection.
        with self.assertRaises(ValidationError):
            # Exercise validation from the mutating public method.
            engine.set_holds(round_state, [1, 1])
        # Verify the original empty selection remains unchanged after failure.
        self.assertEqual([], round_state["holds"])


# Run this focused suite when invoked directly by an issue #92 worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
