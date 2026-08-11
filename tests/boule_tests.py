# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Boule rules and settlement tests on the shared core. (#148, BOULE-001/002)"""

# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Boule pure rules under test.
from casino.games.boule import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Boule core whose drawn number is pinned for deterministic assertions.
def _game(number):
    # Convert the inclusive one-to-nine number into the zero-based index the entropy shifts.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="BOULE_WAGER_DEBIT", settlement_transaction_type="BOULE_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: number - 1)


# Verify Boule pays its groups and single numbers correctly and stays house-positive.
class BouleTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Boule {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every spin.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a covered even-money bet to pay two times the stake.
    def test_even_money_pays_double_on_cover(self) -> None:
        # Draw a two, which is covered by low and even.
        result = _game(2).play(self.pid, {"request_id": "em-win", "bet": "even", "stake": 10})
        # Require the win and a total return of twice the stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 20))
        # Require the wallet to reflect the net win.
        self.assertEqual(self._balance(), 1010.0)

    # Require the house number to beat every even-money bet.
    def test_house_number_loses_every_even_money_bet(self) -> None:
        # Test each even-money group against a drawn five.
        for name in ("low", "high", "odd", "even"):
            # Isolate each group.
            with self.subTest(bet=name):
                # Reset the wallet for a clean assertion.
                players.update_player(self.pid, lambda p: p.update({"balance": 1000.0}))
                # Draw the house number five and bet the group.
                result = _game(5).play(self.pid, {"request_id": f"house-{name}", "bet": name, "stake": 10})
                # Require the loss, only the debited stake, and the house-number flag.
                self.assertEqual(result["round"]["outcome"], "lose")
                self.assertTrue(result["round"]["detail"]["house_number"])
                self.assertEqual(self._balance(), 990.0)

    # Require a straight single-number bet to pay eight times the stake, including on the house number.
    def test_straight_number_pays_eight(self) -> None:
        # Draw the house number five and bet it straight.
        result = _game(5).play(self.pid, {"request_id": "straight-5", "bet": "number", "number": 5, "stake": 10})
        # Require the win and a total return of eight times the stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 80))
        # Require the wallet to reflect the net win.
        self.assertEqual(self._balance(), 1070.0)

    # Require a straight bet on a non-matching number to lose.
    def test_straight_number_loses_on_miss(self) -> None:
        # Draw a three but bet on seven.
        result = _game(3).play(self.pid, {"request_id": "straight-miss", "bet": "number", "number": 7, "stake": 10})
        # Require the loss and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        self.assertEqual(self._balance(), 990.0)

    # Require invalid bets and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning bad bet family, bad number, and bad stake.
        for bad in ({"request_id": "x1", "bet": "corner", "stake": 10}, {"request_id": "x2", "bet": "number", "number": 0, "stake": 10}, {"request_id": "x3", "bet": "number", "number": 10, "stake": 10}, {"request_id": "x4", "bet": "low", "stake": 0}, {"request_id": "x5", "bet": "low", "stake": 1.5}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid spin.
                    _game(1).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried spin to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game(2)
        # Play the first spin.
        first = game.play(self.pid, {"request_id": "dup", "bet": "even", "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "bet": "even", "stake": 10})
        # Require the replay flag, the same drawn number, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["number"], first["round"]["detail"]["number"])
        self.assertEqual(self._balance(), after)

    # Require every bet to keep the expected return below one across all nine equally likely numbers.
    def test_house_edge_is_positive(self) -> None:
        # Check each even-money group's expected return.
        for name, covered in rules.EVEN_MONEY.items():
            # Compute the expected return: covered fraction times the even-money multiplier.
            expected = len(covered) / len(rules.NUMBERS) * rules.EVEN_MONEY_MULTIPLIER
            # Require a strict house edge.
            self.assertLess(expected, 1.0, f"Boule {name} pays back {expected}")
        # Compute a straight single-number bet's expected return.
        straight = 1 / len(rules.NUMBERS) * rules.NUMBER_MULTIPLIER
        # Require a strict house edge on the straight bet too.
        self.assertLess(straight, 1.0, f"Boule straight pays back {straight}")
