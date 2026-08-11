# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Coin Pusher rules and settlement tests on the shared core. (#156, COINP-001/002)"""

# Import product for the exhaustive house-edge proof over every shelf-and-push combination.
from itertools import product
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Coin Pusher pure rules under test.
from casino.games.coin_pusher import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Coin Pusher core whose shelf fill and push are pinned for deterministic assertions.
def _game(shelf_start, push):
    # Yield the forced shelf fill then the forced push across the two entropy draws.
    draws = iter([shelf_start, push])
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="COIN_PUSHER_WAGER_DEBIT", settlement_transaction_type="COIN_PUSHER_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(draws))


# Verify Coin Pusher cascades and pays correctly and stays house-positive.
class CoinPusherTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Coin {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every drop.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a pile that stays below the threshold to drop nothing and lose.
    def test_no_cascade_loses(self) -> None:
        # Land an empty shelf with no push so the pile only reaches one.
        result = _game(0, 0).play(self.pid, {"request_id": "no-cascade", "stake": 10})
        # Require the loss, no cascaded coins, and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["coins"], result["round"]["total_return"]), ("lose", 0, 0))
        self.assertEqual(self._balance(), 990.0)

    # Require a single tipped coin to pay its small multiplier.
    def test_single_cascade_pays_small(self) -> None:
        # Land a shelf of eleven with no push so the pile reaches exactly the threshold and one coin falls.
        result = _game(11, 0).play(self.pid, {"request_id": "one-coin", "stake": 10})
        # Require the win, one cascaded coin, and the small multiplier total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["detail"]["coins"], result["round"]["total_return"]), ("win", 1, round(10 * 1.5, 2)))

    # Require a full four-coin cascade to pay the jackpot multiplier.
    def test_full_cascade_pays_jackpot(self) -> None:
        # Land a full shelf with a maximum push so four coins cascade off the edge.
        result = _game(11, 3).play(self.pid, {"request_id": "jackpot", "stake": 10})
        # Require the win, four cascaded coins, and the jackpot total return.
        self.assertEqual((result["round"]["detail"]["coins"], result["round"]["total_return"]), (4, 10 * 16.0))
        # Require the wallet to reflect the jackpot win.
        self.assertEqual(self._balance(), 1000.0 - 10 + 160.0)

    # Require an invalid stake to be rejected before any wallet movement.
    def test_invalid_stake_rejected(self) -> None:
        # Enumerate rejected stakes.
        for bad in ({"request_id": "b1", "stake": 0}, {"request_id": "b2", "stake": -5}, {"request_id": "b3", "stake": 1.5}, {"request_id": "b4"}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid drop.
                    _game(11, 3).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried drop to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game(11, 3)
        # Play the first drop.
        first = game.play(self.pid, {"request_id": "dup", "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "stake": 10})
        # Require the replay flag, the same committed shelf, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"], first["round"]["detail"])
        self.assertEqual(self._balance(), after)

    # Require the cascade table to keep the expected return below one across every shelf and push.
    def test_house_edge_is_positive(self) -> None:
        # Sum the total return over all equally likely shelf-and-push combinations for a unit stake.
        total = sum(rules.CASCADE_PAYOUTS.get(engine.cascade(shelf, push), 0) for shelf, push in product(range(rules.SHELF_SLOTS), range(rules.PUSH_SLOTS)))
        # Compute the expected return per unit stake over the forty-eight equally likely combinations.
        expected_return = total / (rules.SHELF_SLOTS * rules.PUSH_SLOTS)
        # Require a strict house edge so the cascade table never pays back a stake on average.
        self.assertLess(expected_return, 1.0, f"Coin Pusher pays back {expected_return} which is not house-positive")
