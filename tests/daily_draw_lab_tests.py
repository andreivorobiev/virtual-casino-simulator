# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Daily Draw Lab rules and settlement tests on the shared core. (#144, DDLAB-001/002)"""

# Import comb for the exact hypergeometric house-edge proof.
from math import comb
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Daily Draw Lab pure rules under test.
from casino.games.daily_draw_lab import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Convert a desired drawn set into the pop-index sequence the selection draw consumes.
def _draw_sequence(drawn):
    # Track the numbers still eligible to be drawn.
    pool = list(range(1, rules.POOL + 1))
    # Record the pool index of each drawn number as it is placed.
    sequence = []
    # Walk the desired draw recording where each number sits in the shrinking pool.
    for number in drawn:
        # The selection draw pops this number from its current pool position.
        sequence.append(pool.index(number))
        # Remove the drawn number so later indices reflect the shrinking pool.
        pool.remove(number)
    # Return the exact draw sequence that reproduces the desired numbers.
    return sequence


# Build a Daily Draw Lab core whose draw is pinned for deterministic assertions.
def _game(drawn):
    # Draw the forced pop indices in order across the selection draw.
    draws = iter(_draw_sequence(drawn))
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="DAILY_DRAW_LAB_WAGER_DEBIT", settlement_transaction_type="DAILY_DRAW_LAB_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(draws))


# Verify Daily Draw Lab settles by pick count and hits correctly and stays house-positive.
class DailyDrawLabTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a generous starting balance for the big jackpots.
        self.player = players.create_player(f"Daily {self.id().rsplit('.',1)[1]}", "human", 100000.0)
        # Retain the player id used across every draw.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a full five-number match to pay the top jackpot.
    def test_five_pick_jackpot(self) -> None:
        # Draw exactly the five numbers the player marked.
        result = _game([1, 2, 3, 4, 5]).play(self.pid, {"request_id": "jackpot", "picks": [1, 2, 3, 4, 5], "stake": 2})
        # Require the win, five hits, and the jackpot total return.
        self.assertEqual((result["round"]["detail"]["hit_count"], result["round"]["total_return"]), (5, round(2 * 10000.0, 2)))

    # Require a single-pick hit to pay its paytable multiplier.
    def test_single_pick_hit_pays(self) -> None:
        # Draw a set containing the one marked number.
        result = _game([7, 8, 9, 10, 11]).play(self.pid, {"request_id": "single", "picks": [7], "stake": 10})
        # Require the win, one hit, and the single-pick multiplier total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["hit_count"], result["round"]["total_return"]), ("win", 1, round(10 * 5.5, 2)))

    # Require a pick count and hit combination that pays nothing to lose.
    def test_paytable_miss_loses(self) -> None:
        # Mark three numbers but let the draw hit none, which the pick-three paytable does not pay.
        result = _game([20, 21, 22, 23, 24]).play(self.pid, {"request_id": "miss", "picks": [1, 2, 3], "stake": 10})
        # Require the loss, zero hits, and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["hit_count"], result["round"]["total_return"]), ("lose", 0, 0))
        self.assertEqual(self._balance(), 99990.0)

    # Require invalid picks and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning too many picks, duplicates, out-of-range, empty, and bad stake.
        for bad in ({"request_id": "x1", "picks": [1, 2, 3, 4, 5, 6], "stake": 10}, {"request_id": "x2", "picks": [1, 1], "stake": 10}, {"request_id": "x3", "picks": [0], "stake": 10}, {"request_id": "x4", "picks": [31], "stake": 10}, {"request_id": "x5", "picks": [], "stake": 10}, {"request_id": "x6", "picks": [1], "stake": 0}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid draw.
                    _game([1, 2, 3, 4, 5]).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 100000.0)

    # Require a retried draw to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([1, 2, 3, 4, 5])
        # Play the first draw.
        first = game.play(self.pid, {"request_id": "dup", "picks": [1, 2, 3], "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "picks": [1, 2, 3], "stake": 10})
        # Require the replay flag, the same draw, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["drawn"], first["round"]["detail"]["drawn"])
        self.assertEqual(self._balance(), after)

    # Require every pick count's paytable to keep the expected return below one.
    def test_house_edge_is_positive(self) -> None:
        # Read the total number of possible draws for the hypergeometric denominator.
        denom = comb(rules.POOL, rules.DRAW)
        # Check each supported pick count.
        for picks, table in rules.PAYTABLES.items():
            # Sum the expected return over every possible hit count for this pick count.
            expected_return = sum((comb(rules.DRAW, hits) * comb(rules.POOL - rules.DRAW, picks - hits) / comb(rules.POOL, picks)) * table.get(hits, 0) for hits in range(picks + 1))
            # Require the pick count's paytable to return strictly less than the stake on average.
            self.assertLess(expected_return, 1.0, f"Daily Draw Lab pick {picks} pays back {expected_return}")
