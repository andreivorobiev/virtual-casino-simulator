# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic rules, privacy, and settlement tests for issue #95."""

# Import unittest for dependency-free focused execution.
import unittest

# Import shared domain errors for invalid-transition assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated practice-table engine under test.
from casino.games.texas_holdem_practice_table import engine


# Verify shared-card dealing, street transitions, and strict public redaction.
class TexasHoldemPracticeTableEngineTests(unittest.TestCase):
    # Build one reproducible hand with stable audit metadata.
    def hand(self, seed="issue-95", wager=1):
        # Delegate through the public engine constructor and test-only seed seam.
        return engine.create_hand("session-player", wager, "action-start-001", seed=seed, hand_id="thpt_hand_1", created_at="2026-07-14T00:00:00Z")

    # Apply one human call and all immediate server-managed responses.
    def call_street(self, hand, index):
        # Build one stable human action id per betting phase.
        action_id = f"action-call-{index:03d}"
        # Apply the human through the same path used by automated seats.
        engine.apply_action(hand, "human", "call", action_id, created_at=f"2026-07-14T00:00:0{index + 1}Z")
        # Advance practice opponents until human control or settlement returns.
        engine.advance_opponents(hand, action_id, clock=lambda: "2026-07-14T00:00:09Z")
        # Return the transitioned hand for concise assertions.
        return hand

    # Confirm identical seeds produce identical complete private deal plans.
    def test_seeded_deal_is_deterministic_and_public_state_is_redacted(self):
        # Build two hands from identical deterministic inputs.
        first = self.hand(seed="stable-vector")
        # Rebuild the exact same hand without sharing references.
        second = self.hand(seed="stable-vector")
        # Verify hole cards, burns, board, and remaining deck all reproduce.
        self.assertEqual(first, second)
        # Build the active public response shape.
        public = engine.public_hand(first)
        # Verify the human's two cards remain visible to that authenticated player.
        self.assertNotEqual(["??", "??"], public["seats"][0]["hole_cards"])
        # Verify every active opponent is redacted to two face-down markers.
        self.assertTrue(all(seat["hole_cards"] == ["??", "??"] for seat in public["seats"][1:]))
        # Verify private dealing plans and ledger intents are absent from the whitelist.
        self.assertFalse({"community_plan", "burn_cards", "remaining_deck", "ledger_intents", "action_ids"} & set(public))

    # Confirm four fixed-limit calls reveal the standard streets and settle once.
    def test_four_calls_advance_preflop_flop_turn_river_and_showdown(self):
        # Start one one-token fixed-limit practice hand.
        hand = self.hand(seed="street-vector")
        # Apply the preflop decision and automatic opponent calls.
        self.call_street(hand, 0)
        # Verify the flop exposes exactly three cards and returns human control.
        self.assertEqual(("flop", 3, "human", 8.0), (hand["phase"], hand["revealed_count"], hand["current_actor"], hand["pot"]))
        # Apply the flop decision and automatic opponent calls.
        self.call_street(hand, 1)
        # Verify the turn exposes exactly four cards.
        self.assertEqual(("turn", 4, 12.0), (hand["phase"], hand["revealed_count"], hand["pot"]))
        # Apply the turn decision and automatic opponent calls.
        self.call_street(hand, 2)
        # Verify the river exposes exactly five cards.
        self.assertEqual(("river", 5, 16.0), (hand["phase"], hand["revealed_count"], hand["pot"]))
        # Apply the river decision and prepare terminal settlement.
        self.call_street(hand, 3)
        # Verify the full four-seat pot and terminal pending phase.
        self.assertEqual(("ledger_pending", 20.0, None), (hand["phase"], hand["pot"], hand["current_actor"]))
        # Verify every contender was evaluated through a standard poker rank.
        self.assertEqual(4, len(hand["result"]["hand_ranks"]))
        # Verify no unused human escrow remains after all four calls.
        self.assertEqual(0.0, hand["result"]["human_refund"])

    # Confirm folding returns unused escrow through a prepared ledger intent.
    def test_preflop_fold_prepares_exact_unused_reserve_refund(self):
        # Start a two-token hand with ten tokens reserved from the wallet.
        hand = self.hand(seed="fold-vector", wager=2)
        # Fold the authenticated human before any fixed-limit call.
        engine.apply_action(hand, "human", "fold", "action-fold-001", created_at="2026-07-14T00:00:01Z")
        # Let server-managed opponents complete their deterministic practice hand.
        engine.advance_opponents(hand, "action-fold-001", clock=lambda: "2026-07-14T00:00:02Z")
        # Verify the human loses only the two-token opening ante.
        self.assertEqual(("folded", 8.0, -2.0), (hand["result"]["human_outcome"], hand["result"]["human_refund"], hand["result"]["human_net"]))
        # Verify four real-wallet escrows precede refund and winner payout credits.
        self.assertEqual(["debit", "debit", "debit", "debit", "credit", "credit"], [intent["direction"] for intent in hand["ledger_intents"]])
        # Verify the refund is correlated with the same hand and unique action detail.
        refund = next(intent for intent in hand["ledger_intents"] if intent["player_id"] == "session-player" and intent["details"]["component"] == "refund")
        # Assert complete ledger audit dimensions on the prepared refund.
        self.assertEqual(("session-player", engine.GAME_ID, "thpt_hand_1", "refund"), (refund["player_id"], refund["game"], refund["round_id"], refund["details"]["component"]))

    # Confirm shared seven-card ranking awards a deterministic human win.
    def test_showdown_uses_shared_poker_rank_and_prepares_payout(self):
        # Start any valid hand before replacing only private test fixtures.
        hand = self.hand(seed="winner-fixture")
        # Give the human pocket aces.
        hand["seats"][0]["hole_cards"] = ["AS", "AH"]
        # Give each opponent a lower pocket pair.
        hand["seats"][1]["hole_cards"] = ["KS", "KH"]
        # Give the second opponent pocket queens.
        hand["seats"][2]["hole_cards"] = ["QS", "QH"]
        # Give the third opponent pocket jacks.
        hand["seats"][3]["hole_cards"] = ["JS", "JH"]
        # Use a board that cannot overtake or tie the pocket pairs.
        hand["community_plan"] = ["2C", "3D", "4H", "8S", "9C"]
        # Complete all four fixed-limit betting phases.
        for index in range(4):
            # Apply one human and automatic opponent decision sequence.
            self.call_street(hand, index)
        # Verify the shared evaluator identifies the human pair as strongest.
        self.assertEqual(("win", "one_pair", 19.0), (hand["result"]["human_outcome"], hand["result"]["hand_ranks"]["human"]["name"], hand["result"]["human_payout"]))  # 20 pot less the 5% house rake. (issue #456)
        # Verify all four reserves precede the human's distinct pot payout.
        self.assertEqual(["TEXAS_HOLDEM_ESCROW_DEBIT", "PRACTICE_OPPONENT_ESCROW_DEBIT", "PRACTICE_OPPONENT_ESCROW_DEBIT", "PRACTICE_OPPONENT_ESCROW_DEBIT", "TEXAS_HOLDEM_PAYOUT_CREDIT"], [intent["transaction_type"] for intent in hand["ledger_intents"]])
        # Verify every fixed opponent intent names its real funded wallet and owner context.
        self.assertEqual(["bot_1", "bot_2", "bot_3"], [intent["player_id"] for intent in hand["ledger_intents"] if intent["managed_opponent"]])

    # Confirm action ids replay identically and conflicting reuse fails closed.
    def test_action_id_replay_and_invalid_turns_fail_closed(self):
        # Start one deterministic actionable hand.
        hand = self.hand(seed="replay-vector")
        # Apply one human call under a stable id.
        engine.apply_action(hand, "human", "call", "action-replay-001", created_at="2026-07-14T00:00:01Z")
        # Snapshot the pot after the first valid allocation.
        pot = hand["pot"]
        # Replay the same action id and payload before opponent advancement.
        engine.apply_action(hand, "human", "call", "action-replay-001", created_at="2026-07-14T00:00:02Z")
        # Verify the reserved table stack was not allocated twice.
        self.assertEqual(pot, hand["pot"])
        # Reject the same id reused for a fold.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting replay payload.
            engine.apply_action(hand, "human", "fold", "action-replay-001", created_at="2026-07-14T00:00:03Z")
        # Reject unsupported raise behavior from this narrow practice profile.
        with self.assertRaises(ValidationError):
            # Exercise the intentionally unsupported action vocabulary.
            engine.apply_action(self.hand(), "human", "raise", "action-raise-001", created_at="2026-07-14T00:00:04Z")

    # Confirm invalid contract numbers never enter state or raise raw overflow.
    def test_invalid_contract_wagers_fail_before_hand_construction(self):
        # Exercise coercible types, non-finite numbers, overflow, and rounding edges.
        for wager in ("1", True, False, None, "nan", float("nan"), "inf", float("-inf"), 10**400, 0.005, 20_000.004):
            # Preserve the rejected input in focused-test diagnostics.
            with self.subTest(wager=repr(wager)):
                # Reject the wager before any hand state can be returned.
                with self.assertRaises(ValidationError):
                    # Attempt to construct a hand through the public engine boundary.
                    self.hand(wager=wager)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
