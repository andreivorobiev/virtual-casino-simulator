# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Lucky Grid rules and settlement tests on the shared core. (#153, LGRID-001/002)"""

# Import combinations for the exhaustive house-edge proof over every prize placement.
from itertools import combinations
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Lucky Grid pure rules under test.
from casino.games.lucky_grid import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Convert a desired prize set into the pop-index sequence the selection draw consumes.
def _prize_sequence(prizes):
    # Track the cells still eligible to hide a prize.
    pool = list(range(rules.CELLS))
    # Record the pool index of each prize cell as it is placed.
    sequence = []
    # Walk the desired prizes recording where each sits in the shrinking pool.
    for cell in prizes:
        # The selection draw pops this cell from its current pool position.
        sequence.append(pool.index(cell))
        # Remove the placed cell so later indices reflect the shrinking pool.
        pool.remove(cell)
    # Return the exact draw sequence that reproduces the desired prizes.
    return sequence


# Build a Lucky Grid core whose prize placement is pinned for deterministic assertions.
def _game(prizes):
    # Draw the forced pop indices in order across the selection draw.
    draws = iter(_prize_sequence(prizes))
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="LUCKY_GRID_WAGER_DEBIT", settlement_transaction_type="LUCKY_GRID_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(draws))


# Verify Lucky Grid settles by match count correctly and stays house-positive.
class LuckyGridTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Lucky {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every reveal.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require matching all three prizes to pay the jackpot.
    def test_three_matches_pay_jackpot(self) -> None:
        # Hide the prizes exactly where the player picks.
        result = _game([0, 1, 2]).play(self.pid, {"request_id": "three", "picks": [0, 1, 2], "stake": 10})
        # Require the win, three matches, and the jackpot total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["match_count"], result["round"]["total_return"]), ("win", 3, round(10 * 25.0, 2)))
        # Require the wallet to reflect the jackpot win.
        self.assertEqual(self._balance(), 1000.0 - 10 + 250.0)

    # Require matching two prizes to pay the smaller multiple.
    def test_two_matches_pay_small(self) -> None:
        # Hide two prizes on picked cells and one elsewhere.
        result = _game([0, 1, 5]).play(self.pid, {"request_id": "two", "picks": [0, 1, 2], "stake": 10})
        # Require the win, two matches, and the small multiple total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["match_count"], result["round"]["total_return"]), ("win", 2, round(10 * 3.0, 2)))

    # Require matching one or no prizes to lose.
    def test_one_or_zero_matches_lose(self) -> None:
        # Test a single match and then no matches against the same picks.
        for prizes, matches in ([0, 5, 6], 1), ([5, 6, 7], 0):
            # Isolate each case.
            with self.subTest(prizes=prizes):
                # Reset the wallet for a clean assertion.
                players.update_player(self.pid, lambda p: p.update({"balance": 1000.0}))
                # Reveal against the fixed picks.
                result = _game(prizes).play(self.pid, {"request_id": f"lose-{matches}", "picks": [0, 1, 2], "stake": 10})
                # Require the loss, the expected match count, and only the debited stake.
                self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["match_count"], result["round"]["total_return"]), ("lose", matches, 0))
                self.assertEqual(self._balance(), 990.0)

    # Require invalid picks and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning wrong count, duplicates, out-of-range, and bad stake.
        for bad in ({"request_id": "x1", "picks": [0, 1], "stake": 10}, {"request_id": "x2", "picks": [0, 1, 1], "stake": 10}, {"request_id": "x3", "picks": [0, 1, 9], "stake": 10}, {"request_id": "x4", "picks": [0, 1, 2], "stake": 0}, {"request_id": "x5", "picks": [0, 1, 2], "stake": 1.5}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid reveal.
                    _game([0, 1, 2]).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried reveal to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([0, 1, 2])
        # Play the first reveal.
        first = game.play(self.pid, {"request_id": "dup", "picks": [0, 1, 2], "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "picks": [0, 1, 2], "stake": 10})
        # Require the replay flag, the same prizes, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["prizes"], first["round"]["detail"]["prizes"])
        self.assertEqual(self._balance(), after)

    # Require the paytable to keep the expected return below one across every prize placement.
    def test_house_edge_is_positive(self) -> None:
        # Fix a pick set; by symmetry every pick set shares the same expected return.
        picks = {0, 1, 2}
        # Sum the total return over all prize placements for a unit stake.
        total = sum(rules.PAYOUTS.get(len(picks & set(placement)), 0) for placement in combinations(range(rules.CELLS), rules.PICKS))
        # Compute the expected return per unit stake over the eighty-four placements.
        expected_return = total / len(list(combinations(range(rules.CELLS), rules.PICKS)))
        # Require a strict house edge so the paytable never pays back a stake on average.
        self.assertLess(expected_return, 1.0, f"Lucky Grid pays back {expected_return} which is not house-positive")
