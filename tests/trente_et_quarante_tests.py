"""Focused Trente et Quarante rules and settlement tests on the shared core. (#147, TEQ-001/002)"""

# Import a deterministic seeded PRNG for the house-edge property check.
import random
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Trente et Quarante pure rules under test.
from casino.games.trente_et_quarante import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError

# Name a red ten card index so forced rows are easy to read.
RED_TEN = 9
# Name a red two card index that pushes a thirty row to thirty-two.
RED_TWO = 1
# Name a red ace card index that pushes a thirty row to thirty-one.
RED_ACE = 0
# Name a black ten card index for colour-bet forcing.
BLACK_TEN = 35


# Build a Trente et Quarante core whose two forced rows are dealt in order.
def _game(noir, rouge):
    # Draw the forced card indices in order across both rows.
    sequence = iter(noir + rouge)
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="TRENTE_ET_QUARANTE_WAGER_DEBIT", settlement_transaction_type="TRENTE_ET_QUARANTE_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(sequence))


# Verify Trente et Quarante settles its four bets, refait, and push correctly and stays house-positive.
class TrenteEtQuaranteTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"TEQ {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every coup.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require the lower-total row to win an even-money row bet.
    def test_row_bet_wins_when_row_is_closer_to_thirty_one(self) -> None:
        # Deal Noir to thirty-two and Rouge to thirty-one so Rouge is closer and wins.
        result = _game([RED_TEN, RED_TEN, RED_TEN, RED_TWO], [RED_TEN, RED_TEN, RED_TEN, RED_ACE]).play(self.pid, {"request_id": "rouge-win", "bet": "rouge", "stake": 10})
        # Require the win, a total return of twice the stake, and the correct winning row.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"], result["round"]["detail"]["winner"]), ("win", 20, "rouge"))
        # Require the wallet to reflect the net win.
        self.assertEqual(self._balance(), 1010.0)

    # Require the opposing row bet on the same deal to lose.
    def test_row_bet_loses_when_other_row_wins(self) -> None:
        # Deal the same coup but bet Noir, which is farther from thirty-one.
        result = _game([RED_TEN, RED_TEN, RED_TEN, RED_TWO], [RED_TEN, RED_TEN, RED_TEN, RED_ACE]).play(self.pid, {"request_id": "noir-lose", "bet": "noir", "stake": 10})
        # Require the loss and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        self.assertEqual(self._balance(), 990.0)

    # Require a couleur bet to win when the first card colour matches the winning row colour.
    def test_couleur_wins_when_first_card_matches_winning_colour(self) -> None:
        # Deal Rouge the winner with a red first card so couleur matches red.
        result = _game([RED_TEN, RED_TEN, RED_TEN, RED_TWO], [RED_TEN, RED_TEN, RED_TEN, RED_ACE]).play(self.pid, {"request_id": "couleur-win", "bet": "couleur", "stake": 10})
        # Require the win and a total return of twice the stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 20))

    # Require an inverse bet to win when the first card colour differs from the winning row colour.
    def test_inverse_wins_when_first_card_differs_from_winning_colour(self) -> None:
        # Deal Rouge the winner but with a black first card so inverse matches the mismatch.
        result = _game([BLACK_TEN, RED_TEN, RED_TEN, RED_TWO], [RED_TEN, RED_TEN, RED_TEN, RED_ACE]).play(self.pid, {"request_id": "inverse-win", "bet": "inverse", "stake": 10})
        # Require the win, twice the stake, and the recorded black first card.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"], result["round"]["detail"]["first_color"]), ("win", 20, "black"))

    # Require a refait at thirty-one to bar half the stake on any bet.
    def test_refait_at_thirty_one_bars_half(self) -> None:
        # Deal both rows to exactly thirty-one for the refait.
        result = _game([RED_TEN, RED_TEN, RED_TEN, RED_ACE], [RED_TEN, RED_TEN, RED_TEN, RED_ACE]).play(self.pid, {"request_id": "refait", "bet": "rouge", "stake": 10})
        # Require the refait outcome and a half-stake return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("refait", 5))
        # Require the wallet to reflect the half loss.
        self.assertEqual(self._balance(), 995.0)

    # Require any other tie to return the whole stake as a push.
    def test_non_refait_tie_pushes(self) -> None:
        # Deal both rows to thirty-two for a non-refait tie.
        result = _game([RED_TEN, RED_TEN, RED_TEN, RED_TWO], [RED_TEN, RED_TEN, RED_TEN, RED_TWO]).play(self.pid, {"request_id": "push", "bet": "noir", "stake": 10})
        # Require the push and a full stake return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("push", 10))
        # Require the wallet to be unchanged after the push.
        self.assertEqual(self._balance(), 1000.0)

    # Require invalid bets and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning bad bet and bad stake.
        for bad in ({"request_id": "x1", "bet": "green", "stake": 10}, {"request_id": "x2", "bet": "rouge", "stake": 0}, {"request_id": "x3", "bet": "rouge", "stake": 1.5}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid coup.
                    _game([RED_TEN, RED_TEN, RED_TEN, RED_ACE], [RED_TEN, RED_TEN, RED_TEN, RED_TWO]).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried coup to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game([RED_TEN, RED_TEN, RED_TEN, RED_TWO], [RED_TEN, RED_TEN, RED_TEN, RED_ACE])
        # Play the first coup.
        first = game.play(self.pid, {"request_id": "dup", "bet": "rouge", "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "bet": "rouge", "stake": 10})
        # Require the replay flag, the same dealt rows, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"], first["round"]["detail"])
        self.assertEqual(self._balance(), after)

    # Require the refait to keep the expected return below one for both a row bet and a colour bet.
    def test_house_edge_is_positive(self) -> None:
        # Seed a deterministic PRNG so this house-edge property check never flakes.
        rng = random.Random(20240724)
        # Run a large fixed sample of real deals for each representative bet.
        samples = 200_000
        # Accumulate the total return for a rouge row bet and a couleur colour bet.
        totals = {"rouge": 0.0, "couleur": 0.0}
        # Deal many coups and settle each representative bet on the same deal.
        for _ in range(samples):
            # Draw one authoritative deal from the seeded shoe.
            deal = engine.entropy(lambda n: rng.randrange(n))
            # Settle both representative bets on this deal for a unit stake.
            for bet in totals:
                # Add this bet's total return for the deal.
                totals[bet] += engine.resolve({"bet": bet, "stake": 1}, deal)["total_return"]
        # Require each representative bet to return strictly less than the stake on average.
        for bet, total in totals.items():
            # Require a strict house edge driven by the refait half-loss.
            self.assertLess(total / samples, 1.0, f"Trente et Quarante {bet} pays back {total / samples} which is not house-positive")
