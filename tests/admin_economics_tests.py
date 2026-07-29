"""Listener-free proof that the Admin economics view aggregates per-game payout rates. (issue #456)

The Admin console publishes a continuous per-game payout rate (returned play tokens divided by wagered
play tokens) from the shared ledger, flags any game whose optimal-or-observed return exceeds one, and
excludes funded-opponent and account-seeding movements so the rate reflects real players. This suite
drives the real aggregation over a synthetic ledger window and checks the drill-down breakdown.
"""

# Import unittest for dependency-free execution.
import unittest

# Import the admin module under test so the aggregation exercises shipped code.
from casino import admin


# A synthetic recent-ledger window mixing house-side, player-positive, funded-opponent, and non-game rows.
SYNTHETIC_EVENTS = [
    {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_WAGER_DEBIT", "amount": -100.0},
    {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_PAYOUT_CREDIT", "amount": 92.0},
    {"player_id": "p2", "game": "keno", "transaction_type": "KENO_WAGER_DEBIT", "amount": -50.0},
    {"player_id": "p2", "game": "keno", "transaction_type": "KENO_PAYOUT_CREDIT", "amount": 45.0},
    {"player_id": "p3", "game": "buggy_game", "transaction_type": "BUGGY_WAGER_DEBIT", "amount": -100.0},
    {"player_id": "p3", "game": "buggy_game", "transaction_type": "BUGGY_PAYOUT_CREDIT", "amount": 150.0},
    # Practice table: only the human rows count; the funded opponent rows must be excluded.
    {"player_id": "p4", "game": "texas_holdem_practice_table", "transaction_type": "TEXAS_HOLDEM_ESCROW_DEBIT", "amount": -50.0},
    {"player_id": "p4", "game": "texas_holdem_practice_table", "transaction_type": "TEXAS_HOLDEM_PAYOUT_CREDIT", "amount": 48.0},
    {"player_id": "bot_1", "game": "texas_holdem_practice_table", "transaction_type": "PRACTICE_OPPONENT_ESCROW_DEBIT", "amount": -50.0},
    {"player_id": "bot_1", "game": "texas_holdem_practice_table", "transaction_type": "PRACTICE_OPPONENT_PAYOUT", "amount": 50.0},
    {"player_id": "bot_1", "game": "texas_holdem_practice_table", "transaction_type": "PRACTICE_OPPONENT_FUNDED", "amount": 100000.0},
    # A non-game wallet movement must never enter any per-game rate.
    {"player_id": "p5", "game": None, "transaction_type": "SIGNUP_BONUS_CREDIT", "amount": 25.0},
]


class AdminEconomicsTests(unittest.TestCase):
    """Drive the per-game payout-rate aggregation and drill-down over a fixed ledger window."""

    def setUp(self):
        # Redirect the ledger read to the deterministic synthetic window for the duration of each test.
        self._original_read_recent = admin.ledger.read_recent
        admin.ledger.read_recent = lambda limit=100: list(SYNTHETIC_EVENTS)

    def tearDown(self):
        # Restore the real ledger reader so other suites are unaffected.
        admin.ledger.read_recent = self._original_read_recent

    def _row(self, report, game):
        # Find one game's aggregated row in the economics report.
        return next(row for row in report["games"] if row["game"] == game)

    def test_per_game_payout_rate_and_house_edge(self):
        report = admin.game_economics()
        # Slots returned 92 of 100 wagered for a house-side 0.92 rate.
        slots = self._row(report, "slots")
        self.assertEqual((100.0, 92.0, 0.92, 0.08, False), (slots["wagered"], slots["returned"], slots["payout_rate"], slots["house_edge"], slots["player_positive"]))
        # Keno returned 45 of 50 for a 0.90 rate.
        self.assertEqual(0.9, self._row(report, "keno")["payout_rate"])

    def test_player_positive_game_is_flagged(self):
        report = admin.game_economics()
        # The buggy game returned 150 of 100, a player-positive 1.5 rate that must be flagged.
        buggy = self._row(report, "buggy_game")
        self.assertEqual((1.5, True), (buggy["payout_rate"], buggy["player_positive"]))

    def test_funded_opponent_and_non_game_rows_are_excluded(self):
        report = admin.game_economics()
        # The practice table rate reflects only the human's 48-of-50 return, not the opponent rows.
        practice = self._row(report, "texas_holdem_practice_table")
        self.assertEqual((50.0, 48.0, 0.96), (practice["wagered"], practice["returned"], practice["payout_rate"]))
        # A non-game movement must not create a phantom game row.
        self.assertNotIn(None, [row["game"] for row in report["games"]])

    def test_drill_down_breaks_down_by_transaction_type(self):
        detail = admin.game_economics_detail("slots")
        # The aggregate mirrors the summary row.
        self.assertEqual((100.0, 92.0, 0.92, False), (detail["wagered"], detail["returned"], detail["payout_rate"], detail["player_positive"]))
        # Both slot transaction types appear in the breakdown with their counts.
        types = {row["transaction_type"]: row["count"] for row in detail["by_transaction_type"]}
        self.assertEqual({"SLOTS_WAGER_DEBIT": 1, "SLOTS_PAYOUT_CREDIT": 1}, types)
        # The recent rows expose the underlying ledger events for inspection.
        self.assertEqual(2, len(detail["recent"]))


if __name__ == "__main__":
    unittest.main()
