"""Focused Pachinko rules and settlement tests on the shared core. (#142, PACH-001/002)"""

# Import product for the exhaustive house-edge proof over every drop path.
from itertools import product
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Pachinko pure rules under test.
from casino.games.pachinko import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Pachinko core whose twelve bounces are pinned for deterministic assertions.
def _game(bounces):
    # Draw the forced left or right bounces in order.
    sequence = iter(bounces)
    # Compose the shared core with a sequence-backed entropy source that yields each bounce bit.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="PACHINKO_WAGER_DEBIT", settlement_transaction_type="PACHINKO_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(sequence))


# Verify Pachinko pays each pocket correctly and stays house-positive.
class PachinkoTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Pachinko {self.id().rsplit('.',1)[1]}", "human", 10000.0)
        # Retain the player id used across every drop.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require an all-right drop to land in the far jackpot pocket and pay the jackpot multiplier.
    def test_jackpot_pocket_pays_top_multiplier(self) -> None:
        # Bounce right twelve times to land in pocket twelve.
        result = _game([1] * rules.ROWS).play(self.pid, {"request_id": "jackpot", "stake": 10})
        # Require the landing pocket, the jackpot multiplier, and the total return.
        self.assertEqual((result["round"]["detail"]["pocket"], result["round"]["total_return"]), (rules.ROWS, 10 * 100.0))
        # Require the wallet to reflect the jackpot win.
        self.assertEqual(self._balance(), 10000.0 - 10 + 1000.0)

    # Require the most common centre pocket to pay its small multiplier and lose on net.
    def test_centre_pocket_loses_on_net(self) -> None:
        # Bounce right six times and left six times to land in the centre pocket six.
        result = _game([1, 0] * (rules.ROWS // 2)).play(self.pid, {"request_id": "centre", "stake": 10})
        # Require the centre pocket, a losing outcome, and the small total return.
        self.assertEqual((result["round"]["detail"]["pocket"], result["round"]["outcome"], result["round"]["total_return"]), (rules.ROWS // 2, "lose", round(10 * rules.POCKETS[rules.ROWS // 2], 2)))

    # Require a pocket paying exactly the stake to push the wallet flat.
    def test_even_pocket_pushes(self) -> None:
        # Bounce right four times and left eight times to land in pocket four, which pays exactly the stake.
        result = _game([1, 1, 1, 1] + [0] * 8).play(self.pid, {"request_id": "push", "stake": 10})
        # Require the push outcome and a full stake return.
        self.assertEqual((result["round"]["detail"]["pocket"], result["round"]["outcome"], result["round"]["total_return"]), (4, "push", 10))
        # Require the wallet to be unchanged after the push.
        self.assertEqual(self._balance(), 10000.0)

    # Require an invalid stake to be rejected before any wallet movement.
    def test_invalid_stake_rejected(self) -> None:
        # Enumerate rejected stakes.
        for bad in ({"request_id": "b1", "stake": 0}, {"request_id": "b2", "stake": -5}, {"request_id": "b3", "stake": 1.5}, {"request_id": "b4"}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid drop.
                    _game([1] * rules.ROWS).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 10000.0)

    # Require a retried drop to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([1] * rules.ROWS)
        # Play the first drop.
        first = game.play(self.pid, {"request_id": "dup", "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "stake": 10})
        # Require the replay flag, the same path, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"]["path"], first["round"]["detail"]["path"])
        self.assertEqual(self._balance(), after)

    # Require the pocket table to keep the expected return below one across every possible drop.
    def test_house_edge_is_positive(self) -> None:
        # Sum the total return over all equally likely twelve-bounce paths for a unit stake.
        total = sum(rules.POCKETS[sum(path)] for path in product((0, 1), repeat=rules.ROWS))
        # Compute the expected return per unit stake over the two-to-the-twelve equally likely paths.
        expected_return = total / (2 ** rules.ROWS)
        # Require a strict house edge so the pocket table never pays back a stake on average.
        self.assertLess(expected_return, 1.0, f"Pachinko pays back {expected_return} which is not house-positive")

    # Require the published catalog to match the real pocket table.
    def test_catalog_is_honest(self) -> None:
        # Read the published catalog.
        catalog = rules.bet_catalog()
        # Require the reported rows and pockets to match the real rules.
        self.assertEqual((catalog["rows"], tuple(catalog["pockets"])), (rules.ROWS, rules.POCKETS))
