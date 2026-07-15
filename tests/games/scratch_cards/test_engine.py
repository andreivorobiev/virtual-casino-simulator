"""Focused Scratch Cards rule, validation, and public-masking tests for issue #87."""

# Import the dependency-free standard test runner.
import unittest
# Import a counter helper for match-three assertions.
from collections import Counter

# Import canonical validation errors raised by public engine helpers.
from casino.errors import ValidationError
# Import the pure isolated engine under direct test.
from casino.games.scratch_cards import engine


# Supply a deterministic sequence to the injected bounded entropy seam.
class SequenceRandom:
    # Store the selected outcome followed by optional shuffle choices.
    def __init__(self, *values):
        # Retain a mutable sequence for exact call-order verification.
        self.values = list(values)

    # Return the next bounded value or zero for remaining shuffle calls.
    def __call__(self, upper_bound):
        # Pop the next requested sample when one remains.
        value = self.values.pop(0) if self.values else 0
        # Fail the test immediately if a fixture violates the entropy contract.
        if not 0 <= value < upper_bound:
            # Raise an assertion with the active bound for diagnosis.
            raise AssertionError(f"fixture value {value} is outside {upper_bound}")
        # Return the deterministic bounded index.
        return value


# Verify the explicit match-three profile and hidden-prize boundary.
class ScratchCardsEngineTests(unittest.TestCase):
    # Prove a loss contains no accidental third matching prize.
    def test_loss_board_has_pairs_only(self):
        # Select outcome roll zero and deterministic swaps.
        ticket = engine.generate_ticket(2, SequenceRandom(0))
        # Count private multiplier occurrences for the pure rule assertion.
        counts = Counter(ticket["prize_multipliers"])
        # Verify the documented loss and zero payout.
        self.assertEqual((0, 0.0), (ticket["winning_multiplier"], ticket["payout"]))
        # Verify no losing prize appears three times.
        self.assertLess(max(counts.values()), engine.MATCH_COUNT)

    # Prove the highest outcome builds exactly one winning triple.
    def test_winning_board_and_payout_are_deterministic(self):
        # Select roll ninety-nine for the documented twenty-five-times prize.
        ticket = engine.generate_ticket(2, SequenceRandom(99))
        # Count private multiplier occurrences after deterministic shuffling.
        counts = Counter(ticket["prize_multipliers"])
        # Verify exactly three matching twenty-five-times cells.
        self.assertEqual(3, counts[25])
        # Verify the two-token matched prize settles to fifty play tokens.
        self.assertEqual((25, 50.0), (ticket["winning_multiplier"], ticket["payout"]))
        # Repeat the same entropy sequence for deterministic fixture parity.
        repeated = engine.generate_ticket(2, SequenceRandom(99))
        # Verify the complete private ticket is reproducible through the injected seam.
        self.assertEqual(ticket, repeated)

    # Prove public state exposes only explicitly scratched prize cells.
    def test_public_card_masks_every_covered_prize(self):
        # Generate a private winning ticket with recognizable prize values.
        ticket = engine.generate_ticket(1, SequenceRandom(99))
        # Build one internal partially scratched card record.
        card = {"card_id": "scr_test", "status": "scratching", "wager": 1.0, "purchased_at": "2026-07-14T00:00:00Z", "revealed_positions": [2], **ticket}
        # Sanitize private state through the production public boundary.
        public = engine.public_card(card)
        # Verify exactly one public cell includes a prize.
        self.assertEqual([2], [cell["position"] for cell in public["cells"] if "prize" in cell])
        # Serialize public data to catch accidental private-field leakage by key or value.
        public_text = repr(public)
        # Verify entropy, multipliers, and private full-board fields remain absent.
        self.assertNotIn("outcome_roll", public_text)
        # Verify the full private prize array is not copied into the response.
        self.assertNotIn("prizes", public_text)

    # Prove monetary and action inputs fail closed before service access.
    def test_public_validation_rejects_ambiguous_inputs(self):
        # Reject a wager outside the explicit UI and contract menu.
        with self.assertRaises(ValidationError):
            # Exercise the unsupported amount boundary.
            engine.normalize_wager(3)
        # Reject numeric-looking strings that violate the OpenAPI number type.
        with self.assertRaises(ValidationError):
            # Exercise strict JSON shape validation before Decimal parsing.
            engine.normalize_wager("1")
        # Reject values that would otherwise round into the smallest approved wager.
        with self.assertRaises(ValidationError):
            # Exercise exact pre-quantization membership enforcement.
            engine.normalize_wager(1.004)
        # Reject booleans as numeric cell indexes.
        with self.assertRaises(ValidationError):
            # Exercise strict zero-based position validation.
            engine.normalize_positions([True])
        # Reject duplicate positions instead of silently changing fingerprints.
        with self.assertRaises(ValidationError):
            # Exercise canonical uniqueness enforcement.
            engine.normalize_positions([1, 1])
        # Reject whitespace-padded retry identities.
        with self.assertRaises(ValidationError):
            # Exercise bounded visible-character action validation.
            engine.normalize_action_id(" action ", "action_id")
        # Reject internal whitespace so runtime behavior matches the contract pattern.
        with self.assertRaises(ValidationError):
            # Exercise immutable single-token action identity validation.
            engine.normalize_action_id("action two", "action_id")

    # Prove card identities are stable, bounded, and player-scoped.
    def test_card_id_is_stable_and_player_scoped(self):
        # Derive the same purchase identity twice for network recovery.
        first = engine.card_id_for("player-a", "request-87")
        # Repeat through the same public helper.
        second = engine.card_id_for("player-a", "request-87")
        # Verify deterministic equality for the same authenticated player.
        self.assertEqual(first, second)
        # Verify another authenticated player cannot collide with the same client text.
        self.assertNotEqual(first, engine.card_id_for("player-b", "request-87"))
        # Verify raw client text is absent from the public digest id.
        self.assertNotIn("request", first)


# Run this focused suite directly without central runner registration.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
