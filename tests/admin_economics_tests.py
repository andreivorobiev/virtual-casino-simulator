# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free proof for Admin per-game payout-rate economics. (ADMIN-030, TEST-146)"""

# Import unittest for the dependency-free runner.
import unittest

# Import decimal values so the MySQL aggregation fake matches database money rows.
from decimal import Decimal

# Import the Admin module so tests exercise the shipped aggregation functions.
from casino import admin
# Import the production provider and provider-neutral aggregation oracle.
from casino.core.storage import MySQLStorageProvider
from casino.core.storage.base import _aggregate_player_economics

# Define one deterministic ledger window spanning house-side, player-positive, opponent, and non-game rows.
SYNTHETIC_EVENTS = [
    # Record one Slots wager.
    {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_WAGER_DEBIT", "amount": -100.0},
    # Record its return.
    {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_PAYOUT_CREDIT", "amount": 92.0},
    # Record one Keno wager.
    {"player_id": "p2", "game": "keno", "transaction_type": "KENO_WAGER_DEBIT", "amount": -50.0},
    # Record its return.
    {"player_id": "p2", "game": "keno", "transaction_type": "KENO_PAYOUT_CREDIT", "amount": 45.0},
    # Record a deliberately player-positive wager sample.
    {"player_id": "p3", "game": "buggy_game", "transaction_type": "BUGGY_WAGER_DEBIT", "amount": -100.0},
    # Return more than the wager to exercise the warning flag.
    {"player_id": "p3", "game": "buggy_game", "transaction_type": "BUGGY_PAYOUT_CREDIT", "amount": 150.0},
    # Record a real player's practice-table wager.
    {"player_id": "p4", "game": "texas_holdem_practice_table", "transaction_type": "TEXAS_HOLDEM_ESCROW_DEBIT", "amount": -50.0},
    # Record the real player's practice-table return.
    {"player_id": "p4", "game": "texas_holdem_practice_table", "transaction_type": "TEXAS_HOLDEM_PAYOUT_CREDIT", "amount": 48.0},
    # Record a funded opponent debit that must be excluded.
    {"player_id": "bot_1", "game": "texas_holdem_practice_table", "transaction_type": "PRACTICE_OPPONENT_ESCROW_DEBIT", "amount": -50.0},
    # Record a funded opponent return that must be excluded.
    {"player_id": "bot_1", "game": "texas_holdem_practice_table", "transaction_type": "PRACTICE_OPPONENT_PAYOUT", "amount": 50.0},
    # Record account funding that must be excluded.
    {"player_id": "bot_1", "game": "texas_holdem_practice_table", "transaction_type": "PRACTICE_OPPONENT_FUNDED", "amount": 100000.0},
    # Record a non-game wallet movement that must not create a game row.
    {"player_id": "p5", "game": None, "transaction_type": "SIGNUP_BONUS_CREDIT", "amount": 25.0},
]


# Drive the aggregation and drill-down over the deterministic ledger window.
class AdminEconomicsTests(unittest.TestCase):
    # Replace the ledger reader before each assertion.
    def setUp(self):
        # Preserve the production provider aggregation seam for exact restoration.
        self._original_economics = admin.ledger.economics
        # Retain a fresh event list so one test cannot mutate another test's window.
        self.events = list(SYNTHETIC_EVENTS)
        # Aggregate the newest bounded fixture rows through the same provider-neutral oracle.
        admin.ledger.economics = lambda window, game=None, recent=0: _aggregate_player_economics(self.events[-window:], game=game, recent=recent)

    # Restore the production reader after each assertion.
    def tearDown(self):
        # Reinstall the original provider aggregation function byte-for-byte.
        admin.ledger.economics = self._original_economics

    # Locate one game summary row.
    def _row(self, report, game):
        # Return the exact named row or let StopIteration fail the test.
        return next(row for row in report["games"] if row["game"] == game)

    # Prove wager, return, rate, and house-edge arithmetic.
    def test_per_game_payout_rate_and_house_edge(self):
        # Aggregate the synthetic window.
        report = admin.game_economics()
        # Read the Slots row.
        slots = self._row(report, "slots")
        # Require the expected 92-percent return and 8-percent house edge.
        self.assertEqual((100.0, 92.0, 0.92, 0.08, False), (slots["wagered"], slots["returned"], slots["payout_rate"], slots["house_edge"], slots["player_positive"]))
        # Require Keno's independent 90-percent rate.
        self.assertEqual(0.9, self._row(report, "keno")["payout_rate"])

    # Prove a rate above one is explicit rather than silently normalized.
    def test_player_positive_game_is_flagged(self):
        # Aggregate the synthetic window.
        report = admin.game_economics()
        # Read the deliberately player-positive row.
        buggy = self._row(report, "buggy_game")
        # Require the 150-percent rate and warning flag.
        self.assertEqual((1.5, True), (buggy["payout_rate"], buggy["player_positive"]))

    # Prove infrastructure and non-game movements cannot distort rates.
    def test_funded_opponent_and_non_game_rows_are_excluded(self):
        # Aggregate the synthetic window.
        report = admin.game_economics()
        # Read the practice-table row.
        practice = self._row(report, "texas_holdem_practice_table")
        # Require only the human player's 48-of-50 return.
        self.assertEqual((50.0, 48.0, 0.96), (practice["wagered"], practice["returned"], practice["payout_rate"]))
        # Require no phantom row for wallet-only movement.
        self.assertNotIn(None, [row["game"] for row in report["games"]])

    # Prove the drill-down retains type counts and recent evidence.
    def test_drill_down_breaks_down_by_transaction_type(self):
        # Request the Slots drill-down.
        detail = admin.game_economics_detail("slots")
        # Require its aggregate to match the summary.
        self.assertEqual((100.0, 92.0, 0.92, False), (detail["wagered"], detail["returned"], detail["payout_rate"], detail["player_positive"]))
        # Build the transaction-type count map.
        types = {row["transaction_type"]: row["count"] for row in detail["by_transaction_type"]}
        # Require one wager and one payout event.
        self.assertEqual({"SLOTS_WAGER_DEBIT": 1, "SLOTS_PAYOUT_CREDIT": 1}, types)
        # Require both recent rows as bounded evidence.
        self.assertEqual(2, len(detail["recent"]))

    # Prove a credit-only game publishes no unanchored ratio or house edge.
    def test_zero_wager_rate_is_null(self):
        # Replace the window with one return that has no corresponding wager.
        self.events = [{"player_id": "p6", "game": "credit_only", "transaction_type": "CREDIT_ONLY_PAYOUT", "amount": 10.0}]
        # Aggregate the credit-only row.
        row = self._row(admin.game_economics(), "credit_only")
        # Require explicit null ratios while preserving the observed return.
        self.assertEqual((0.0, 10.0, None, None, False), (row["wagered"], row["returned"], row["payout_rate"], row["house_edge"], row["player_positive"]))

    # Prove internal window and recent arguments cannot expand provider reads or response evidence.
    def test_window_and_recent_bounds_are_enforced(self):
        # Record every provider limit passed by the aggregation functions.
        limits = []
        # Return many valid rows while retaining the requested bound.
        def economics(window, game=None, recent=0):
            # Capture the exact provider bound.
            limits.append(window)
            # Return enough events to exercise the detail recent slice.
            events = [{"player_id": f"p{index}", "game": "slots", "transaction_type": "SLOTS_WAGER_DEBIT", "amount": -1.0} for index in range(75)]
            # Build the provider result while honoring the requested detail bound.
            return _aggregate_player_economics(events[-window:], game=game, recent=recent)
        # Install the recording provider seam.
        admin.ledger.economics = economics
        # Request values above both reviewed maxima.
        admin.game_economics(window=1_000_000)
        # Request an oversized detail evidence slice.
        detail = admin.game_economics_detail("slots", window=1_000_000, recent=500)
        # Require both provider calls to stop at the 100,000-row ceiling.
        self.assertEqual([100_000, 100_000], limits)
        # Require recent evidence to stop at 50 rows.
        self.assertEqual(50, len(detail["recent"]))

    # Prove malformed and non-finite historical amounts fail safe without false diagnostics.
    def test_malformed_amounts_are_excluded(self):
        # Publish hostile stored representations beside one valid wager.
        self.events = [
            # Keep one valid row so the game remains represented.
            {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_WAGER_DEBIT", "amount": -10.0},
            # Reject arbitrary text.
            {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_PAYOUT_CREDIT", "amount": "invalid"},
            # Reject a boolean that would otherwise coerce to one.
            {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_PAYOUT_CREDIT", "amount": True},
            # Reject non-finite numeric text.
            {"player_id": "p1", "game": "slots", "transaction_type": "SLOTS_PAYOUT_CREDIT", "amount": "NaN"},
        ]
        # Aggregate without raising or producing a non-JSON ratio.
        row = self._row(admin.game_economics(), "slots")
        # Require only the valid wager to count.
        self.assertEqual((10.0, 0.0, 0.0, 1), (row["wagered"], row["returned"], row["payout_rate"], row["events"]))
        # Require the drill-down to retain only the valid row.
        self.assertEqual(1, admin.game_economics_detail("slots")["events"])

    # Prove MySQL aggregates the bounded ledger window in SQL instead of returning every row to Python.
    def test_mysql_provider_uses_sql_aggregation_and_bounded_detail(self):
        # Retain each executed statement and its bound parameters.
        statements = []

        # Model the dictionary cursor result sets for summary, type detail, and recent evidence.
        class Cursor:
            # Start before the first scripted result.
            def __init__(self):
                # Track which statement result should be returned next.
                self.index = -1

            # Capture one provider query without a database connection.
            def execute(self, statement, values):
                # Advance to the result owned by this query.
                self.index += 1
                # Retain exact SQL and parameters for structural assertions.
                statements.append((statement, values))

            # Return the deterministic result for the most recent statement.
            def fetchall(self):
                # Return the selected-game aggregate first.
                if self.index == 0:
                    # Match MySQL DECIMAL and COUNT result types.
                    return [{"game": "slots", "wagered": Decimal("100.00"), "returned": Decimal("92.00"), "event_count": 2}]
                # Return two transaction-type buckets second.
                if self.index == 1:
                    # Preserve signed totals exactly like SUM(amount).
                    return [{"transaction_type": "SLOTS_PAYOUT_CREDIT", "event_count": 1, "total": Decimal("92.00")}, {"transaction_type": "SLOTS_WAGER_DEBIT", "event_count": 1, "total": Decimal("-100.00")}]
                # Return the chronological public ledger evidence last.
                return [{"ledger_id": "L1", "ts": "2026-08-19T00:00:00Z", "player_id": "p1", "game": "slots", "round_id": "r1", "transaction_type": "SLOTS_WAGER_DEBIT", "amount": Decimal("-100.00"), "balance_before": Decimal("500.00"), "balance_after": Decimal("400.00"), "details_json": "{}"}]

        # Model one read-only provider connection.
        class Connection:
            # Return the scripted dictionary cursor.
            def cursor(self, dictionary=False):
                # Require the production mapping mode.
                self.dictionary = dictionary
                # Return one cursor shared by all statements in this operation.
                return self._cursor

            # Record that the provider released the lease.
            def close(self):
                # Mark exact cleanup for the assertion.
                self.closed = True

        # Build the fake connection state.
        connection = Connection()
        # Install one cursor whose sequence spans all three queries.
        connection._cursor = Cursor()
        # Start with no observed close.
        connection.closed = False
        # Construct the provider without allocating a real pool.
        provider = object.__new__(MySQLStorageProvider)
        # Bypass schema readiness only inside this deterministic SQL-shape test.
        provider.ensure_ready = lambda: None
        # Return the fake read-only lease.
        provider.connect = lambda: connection
        # Request one game detail through the production MySQL implementation.
        evidence = provider.ledger_economics(100_000, game="slots", recent=50)
        # Require low-cardinality aggregates and one bounded public evidence row.
        self.assertEqual(({"game": "slots", "wagered": 100.0, "returned": 92.0, "events": 2}, 2, ["L1"]), (evidence["games"][0], len(evidence["by_transaction_type"]), [row["ledger_id"] for row in evidence["recent"]]))
        # Require aggregate SQL, a newest-window derived table, and no Python-side full ledger read.
        self.assertTrue(all("bounded_ledger" in statement and "LIMIT %s" in statement for statement, _values in statements))
        # Require the first two statements to aggregate inside MySQL.
        self.assertTrue(all("GROUP BY" in statement and ("SUM(" in statement or "COUNT(" in statement) for statement, _values in statements[:2]))
        # Require database collation not to broaden the exact Python game/type classification.
        self.assertTrue(all("BINARY" in statement for statement, _values in statements))
        # Require the detail evidence query to retain its separate bound and the lease to close.
        self.assertEqual((100_000, 50, True), (statements[2][1][0], statements[2][1][-1], connection.closed))


# Run the focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
