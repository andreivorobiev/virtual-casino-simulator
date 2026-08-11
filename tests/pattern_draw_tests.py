# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Pattern Draw rules and settlement tests on the shared core. (#155, PATTERN-001/002)"""

# Import product for the exhaustive house-edge proof over every grid.
from itertools import product
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Pattern Draw pure rules under test.
from casino.games.pattern_draw import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Pattern Draw core whose nine-cell grid is pinned for deterministic assertions.
def _game(grid):
    # Draw the forced cell bits in order.
    bits = iter(grid)
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="PATTERN_DRAW_WAGER_DEBIT", settlement_transaction_type="PATTERN_DRAW_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(bits))


# Verify Pattern Draw settles each pattern bet correctly and stays house-positive.
class PatternDrawTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a generous starting balance for the jackpot bet.
        self.player = players.create_player(f"Pattern {self.id().rsplit('.',1)[1]}", "human", 10000.0)
        # Retain the player id used across every draw.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a completed top row to win the line bet.
    def test_line_bet_pays_on_any_line(self) -> None:
        # Light the top row only.
        result = _game([1, 1, 1, 0, 0, 0, 0, 0, 0]).play(self.pid, {"request_id": "line", "bet": "line", "stake": 10})
        # Require the win, the line multiplier total return, and the reported lit line.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"], result["round"]["detail"]["lit_lines"]), ("win", round(10 * 1.75, 2), [[0, 1, 2]]))

    # Require a grid with no completed line to lose the line bet.
    def test_line_bet_loses_without_a_line(self) -> None:
        # Light a grid with no full row, column, or diagonal.
        result = _game([1, 1, 0, 1, 0, 1, 0, 1, 1]).play(self.pid, {"request_id": "line-miss", "bet": "line", "stake": 10})
        # Require the loss and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        self.assertEqual(self._balance(), 9990.0)

    # Require the lit plus shape to win the cross bet.
    def test_cross_bet_pays_on_plus_shape(self) -> None:
        # Light exactly the cross cells one, three, four, five, and seven.
        result = _game([0, 1, 0, 1, 1, 1, 0, 1, 0]).play(self.pid, {"request_id": "cross", "bet": "cross", "stake": 10})
        # Require the win and the cross multiplier total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", round(10 * 30.0, 2)))

    # Require an all-lit grid to win the full jackpot bet.
    def test_full_bet_pays_jackpot(self) -> None:
        # Light every cell for the full grid.
        result = _game([1] * 9).play(self.pid, {"request_id": "full", "bet": "full", "stake": 10})
        # Require the win and the jackpot multiplier total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", round(10 * 480.0, 2)))
        # Require the wallet to reflect the jackpot win.
        self.assertEqual(self._balance(), 10000.0 - 10 + 4800.0)

    # Require invalid bets and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning bad bet and bad stake.
        for bad in ({"request_id": "x1", "bet": "diagonal", "stake": 10}, {"request_id": "x2", "bet": "line", "stake": 0}, {"request_id": "x3", "bet": "line", "stake": 1.5}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid draw.
                    _game([1] * 9).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 10000.0)

    # Require a retried draw to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([1, 1, 1, 0, 0, 0, 0, 0, 0])
        # Play the first draw.
        first = game.play(self.pid, {"request_id": "dup", "bet": "line", "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "bet": "line", "stake": 10})
        # Require the replay flag, the same grid, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["grid"], first["round"]["detail"]["grid"])
        self.assertEqual(self._balance(), after)

    # Require every pattern bet to keep the expected return below one across all 512 grids.
    def test_house_edge_is_positive(self) -> None:
        # Enumerate every possible grid once.
        grids = list(product((0, 1), repeat=rules.CELLS))
        # Check each pattern bet's expected return.
        for bet in rules.PAYOUTS:
            # Sum the bet's total return over all grids for a unit stake.
            total = sum(rules.PAYOUTS[bet] for grid in grids if engine.pattern_present(bet, grid))
            # Require the bet to return strictly less than the stake on average.
            self.assertLess(total / len(grids), 1.0, f"Pattern Draw {bet} pays back {total / len(grids)}")
