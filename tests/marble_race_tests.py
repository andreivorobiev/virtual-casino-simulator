# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Marble Race rules and settlement tests on the shared core. (#157, MARBLE-001/002)"""

# Import permutations for the exhaustive house-edge proof over every finishing order.
from itertools import permutations
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Marble Race pure rules under test.
from casino.games.marble_race import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Convert a desired finishing order into the pop-index sequence the selection shuffle consumes.
def _index_sequence(order):
    # Track the marbles still waiting to be placed.
    pool = list(range(len(rules.MARBLES)))
    # Record the pool index of each marble as it is placed.
    sequence = []
    # Walk the desired order recording where each marble sits in the shrinking pool.
    for marble in order:
        # The selection shuffle pops this marble from its current pool position.
        sequence.append(pool.index(marble))
        # Remove the placed marble so later indices reflect the shrinking pool.
        pool.remove(marble)
    # Return the exact draw sequence that reproduces the desired order.
    return sequence


# Build a Marble Race core whose finishing order is pinned for deterministic assertions.
def _game(order):
    # Draw the forced pop indices in order across the selection shuffle.
    draws = iter(_index_sequence(order))
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="MARBLE_RACE_WAGER_DEBIT", settlement_transaction_type="MARBLE_RACE_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(draws))


# Verify Marble Race settles win and podium bets correctly and stays house-positive.
class MarbleRaceTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Marble {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every race.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a win bet on the first-place marble to pay the win multiplier.
    def test_win_bet_pays_on_first_place(self) -> None:
        # Force marble two to win the race.
        result = _game([2, 0, 1, 3, 4, 5]).play(self.pid, {"request_id": "win", "bet": "win", "marble": 2, "stake": 10})
        # Require the win, the win multiplier total return, and the recorded winner.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"], result["round"]["detail"]["winner"]), ("win", round(10 * 5.7, 2), 2))
        # Require the wallet to reflect the net win.
        self.assertEqual(self._balance(), round(1000.0 - 10 + 57.0, 2))

    # Require a win bet on a non-winning marble to lose.
    def test_win_bet_loses_off_first_place(self) -> None:
        # Force marble two to win but bet on marble five.
        result = _game([2, 0, 1, 3, 4, 5]).play(self.pid, {"request_id": "win-miss", "bet": "win", "marble": 5, "stake": 10})
        # Require the loss and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        self.assertEqual(self._balance(), 990.0)

    # Require a podium bet on a top-three marble to pay the podium multiplier.
    def test_podium_bet_pays_in_top_three(self) -> None:
        # Force marble one to finish third, inside the podium.
        result = _game([2, 0, 1, 3, 4, 5]).play(self.pid, {"request_id": "podium", "bet": "podium", "marble": 1, "stake": 10})
        # Require the win and the podium multiplier total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", round(10 * 1.9, 2)))

    # Require a podium bet on a marble outside the top three to lose.
    def test_podium_bet_loses_off_podium(self) -> None:
        # Force marble four to finish fifth, outside the podium.
        result = _game([2, 0, 1, 3, 4, 5]).play(self.pid, {"request_id": "podium-miss", "bet": "podium", "marble": 4, "stake": 10})
        # Require the loss and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))

    # Require invalid bets, marbles, and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning bad bet, bad marble, and bad stake.
        for bad in ({"request_id": "x1", "bet": "place", "marble": 0, "stake": 10}, {"request_id": "x2", "bet": "win", "marble": 6, "stake": 10}, {"request_id": "x3", "bet": "win", "marble": -1, "stake": 10}, {"request_id": "x4", "bet": "win", "marble": 0, "stake": 0}, {"request_id": "x5", "bet": "win", "marble": 0, "stake": 1.5}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid race.
                    _game([0, 1, 2, 3, 4, 5]).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried race to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([2, 0, 1, 3, 4, 5])
        # Play the first race.
        first = game.play(self.pid, {"request_id": "dup", "bet": "win", "marble": 2, "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "bet": "win", "marble": 2, "stake": 10})
        # Require the replay flag, the same finishing order, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["order"], first["round"]["detail"]["order"])
        self.assertEqual(self._balance(), after)

    # Require both bets to keep the expected return below one across every finishing order.
    def test_house_edge_is_positive(self) -> None:
        # Enumerate every possible finishing order once.
        orders = list(permutations(range(len(rules.MARBLES))))
        # Fix a marble; by symmetry every marble shares the same expected return.
        marble = 0
        # Sum the win-bet return over all finishing orders for a unit stake.
        win_total = sum(rules.WIN_MULTIPLIER for order in orders if order[0] == marble)
        # Sum the podium-bet return over all finishing orders for a unit stake.
        podium_total = sum(rules.PODIUM_MULTIPLIER for order in orders if marble in order[:rules.PODIUM_SIZE])
        # Require each market to return strictly less than the stake on average.
        self.assertLess(win_total / len(orders), 1.0, f"Marble Race win pays back {win_total / len(orders)}")
        self.assertLess(podium_total / len(orders), 1.0, f"Marble Race podium pays back {podium_total / len(orders)}")
