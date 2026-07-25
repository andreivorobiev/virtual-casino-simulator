"""Focused Poker Dice rules and settlement tests on the shared core. (#151, PDICE-001/002)"""

# Import product for the exhaustive house-edge proof.
from itertools import product
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Poker Dice pure rules under test.
from casino.games.poker_dice import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Poker Dice core whose five-die roll is pinned for deterministic assertions.
def _game(dice):
    # Draw the forced dice in order from an injected sequence so the roll is deterministic.
    sequence = iter(dice)
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="POKER_DICE_WAGER_DEBIT", settlement_transaction_type="POKER_DICE_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(sequence))


# Verify Poker Dice ranks and pays hands correctly and stays house-positive.
class PokerDiceTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Dice {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every roll.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require each hand category to pay its exact multiplier.
    def test_each_hand_pays_its_multiplier(self) -> None:
        # Map a representative forced roll to its expected category and total return on a 10 stake.
        cases = [([0, 0, 0, 0, 0], "five_of_a_kind", 800), ([0, 0, 0, 0, 1], "four_of_a_kind", 150), ([0, 0, 0, 1, 1], "full_house", 50), ([0, 1, 2, 3, 4], "straight", 40), ([0, 0, 0, 1, 2], "three_of_a_kind", 20)]
        # Check every paying category.
        for dice, hand, total in cases:
            # Isolate each case so a failure names the hand.
            with self.subTest(hand=hand):
                # Reset the wallet for a clean assertion.
                players.update_player(self.pid, lambda p: p.update({"balance": 1000.0}))
                # Roll the forced dice on a 10 stake.
                result = _game(dice).play(self.pid, {"request_id": f"r-{hand}", "stake": 10})
                # Require the classified hand and the exact total return.
                self.assertEqual((result["round"]["detail"]["hand"], result["round"]["total_return"]), (hand, total))

    # Require two pair, one pair, and high card to lose.
    def test_weak_hands_lose(self) -> None:
        # Map a representative forced roll to its non-paying category.
        for index, dice in enumerate(([0, 0, 1, 1, 2], [0, 0, 1, 2, 3], [0, 1, 2, 3, 5])):
            # Isolate each case.
            with self.subTest(dice=dice):
                # Reset the wallet for a clean assertion.
                players.update_player(self.pid, lambda p: p.update({"balance": 1000.0}))
                # Roll the forced weak hand on a 10 stake.
                result = _game(dice).play(self.pid, {"request_id": f"r-weak-{index}", "stake": 10})
                # Require a loss and only the debited stake.
                self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
                self.assertEqual(self._balance(), 990.0)

    # Require an invalid stake to be rejected before any wallet movement.
    def test_invalid_stake_rejected(self) -> None:
        # Enumerate rejected stakes.
        for bad in ({"request_id": "b1", "stake": 0}, {"request_id": "b2", "stake": -5}, {"request_id": "b3", "stake": 1.5}, {"request_id": "b4"}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid roll.
                    _game([0, 0, 0, 0, 0]).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried roll to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([0, 0, 0, 0, 0])
        # Play the first roll.
        first = game.play(self.pid, {"request_id": "r-dup", "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "r-dup", "stake": 10})
        # Require the replay flag and unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["dice"], first["round"]["detail"]["dice"])
        self.assertEqual(self._balance(), after)

    # Require the paytable to keep the expected return below one across every possible roll.
    def test_house_edge_is_positive(self) -> None:
        # Sum the total return over all equally likely rolls for a unit stake.
        total = sum(rules.PAYOUTS.get(engine.category(list(dice)), 0) for dice in product(range(6), repeat=5))
        # Compute the expected return per unit stake.
        expected_return = total / (6 ** 5)
        # Require a strict house edge so the game never pays back a stake on average.
        self.assertLess(expected_return, 1.0, f"Poker Dice pays back {expected_return} which is not house-positive")

    # Require the published paytable to match the real payout table.
    def test_paytable_is_honest(self) -> None:
        # Read the published catalog.
        catalog = rules.bet_catalog()
        # Require every listed hand's multiplier to equal the real payout.
        for entry in catalog["paytable"]:
            # Require the reported multiplier to match.
            self.assertEqual(entry["multiplier"], rules.PAYOUTS[entry["hand"]])
