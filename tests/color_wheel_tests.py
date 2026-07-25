"""Focused Color Wheel rules and settlement tests on the shared core. (#152, CWHEEL-001/002)"""

# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Color Wheel pure rules under test.
from casino.games.color_wheel import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Color Wheel core whose landed segment is pinned for deterministic assertions.
def _game(forced_segment: int) -> SimpleWagerGame:
    # Force the entropy source so the landed segment index is deterministic.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="COLOR_WHEEL_WAGER_DEBIT", settlement_transaction_type="COLOR_WHEEL_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: forced_segment)


# Verify Color Wheel pays correctly and stays house-positive.
class ColorWheelTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Wheel {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every spin.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a matching-colour bet to pay the colour multiplier once.
    def test_matching_color_pays_multiplier(self) -> None:
        # Segment 0 is red per the fixed layout; a red bet must win at 2x.
        result = _game(forced_segment=0).play(self.pid, {"request_id": "r-red", "color": "red", "stake": 10})
        # Require the win and the even-money total return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 20))
        # Require the wallet to reflect minus-stake plus-return.
        self.assertEqual(self._balance(), 1000.0 - 10 + 20)

    # Require a non-matching-colour bet to lose the stake.
    def test_non_matching_color_loses(self) -> None:
        # Segment 0 is red; a black bet must lose.
        result = _game(forced_segment=0).play(self.pid, {"request_id": "r-black", "color": "black", "stake": 10})
        # Require the loss and no return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        # Require the wallet to reflect only the debited stake.
        self.assertEqual(self._balance(), 1000.0 - 10)

    # Require the gold jackpot segment to pay its high multiplier.
    def test_gold_segment_pays_jackpot(self) -> None:
        # Segment 9 is gold per the fixed layout; a gold bet must win at 16x.
        result = _game(forced_segment=9).play(self.pid, {"request_id": "r-gold", "color": "gold", "stake": 5})
        # Require the winning total at the gold multiplier.
        self.assertEqual(result["round"]["total_return"], 80)

    # Require an unknown colour or malformed stake to be rejected before any wallet movement.
    def test_invalid_bets_are_rejected(self) -> None:
        # Enumerate rejected requests.
        for bad in ({"request_id": "b1", "color": "purple", "stake": 5}, {"request_id": "b2", "color": "red", "stake": 0}, {"request_id": "b3", "color": "red", "stake": 1.5}, {"request_id": "b4", "color": "red"}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid spin.
                    _game(forced_segment=0).play(self.pid, bad)
        # Require the wallet to be untouched by any rejected spin.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried spin to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game(forced_segment=9)
        # Play the first spin.
        first = game.play(self.pid, {"request_id": "r-dup", "color": "gold", "stake": 5})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "r-dup", "color": "gold", "stake": 5})
        # Require the replay flag and unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["total_return"], first["round"]["total_return"])
        self.assertEqual(self._balance(), after)

    # Require every payout to keep the expected return below one so the house always holds an edge.
    def test_every_bet_is_house_positive(self) -> None:
        # Check each colour's expected return across all twenty segments.
        for color, multiplier in rules.PAYOUTS.items():
            # Isolate each colour so a failure names it.
            with self.subTest(color=color):
                # Compute the expected return: probability of a matching segment times the multiplier.
                expected_return = (rules.SEGMENTS.count(color) / len(rules.SEGMENTS)) * multiplier
                # Require the expected return to stay strictly below one.
                self.assertLess(expected_return, 1.0, f"{color} pays back {expected_return} which is not house-positive")

    # Require the public bet catalog to report honest segment counts and multipliers.
    def test_bet_catalog_is_honest(self) -> None:
        # Read the published catalog.
        catalog = rules.bet_catalog()
        # Require the total segment count.
        self.assertEqual(catalog["segments"], 20)
        # Require each catalog entry to match the actual layout and payout.
        for entry in catalog["bets"]:
            # Require the reported segment count to equal the real layout count.
            self.assertEqual(entry["segments"], rules.SEGMENTS.count(entry["color"]))
            # Require the reported multiplier to equal the real payout.
            self.assertEqual(entry["multiplier"], rules.PAYOUTS[entry["color"]])
