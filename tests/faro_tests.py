# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Faro rules and settlement tests on the shared core. (#146, FARO-001/002)"""

# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative player boundary for balance assertions.
from casino.core import players
# Import the shared settlement core.
from casino.core.simple_game import SimpleWagerGame
# Import the Faro pure rules under test.
from casino.games.faro import engine, rules
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError


# Build a Faro core whose two dealt card indices are pinned for deterministic assertions.
def _game(banker_idx, player_idx):
    # Recover the two raw randbelow return values that reproduce the desired distinct card indices.
    draws = iter([banker_idx, player_idx if player_idx < banker_idx else player_idx - 1])
    # Compose the shared core with a sequence-backed entropy source.
    return SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type="FARO_WAGER_DEBIT", settlement_transaction_type="FARO_SETTLEMENT_CREDIT", entropy=engine.entropy, resolve=engine.resolve, validate_bet=engine.validate_bet, entropy_source=lambda n: next(draws))


# Convert a rank index and suit offset into a concrete deck card index.
def _card(rank_index, suit=0):
    # Return the card index for the rank's given suit within the fifty-two-card deck.
    return rank_index * rules.SUITS + suit


# Verify Faro settles win, lose, push, and split correctly and stays house-positive.
class FaroTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Faro {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every deal.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Require a matching player card to win even money.
    def test_player_match_wins_even_money(self) -> None:
        # Deal a banker of rank five and a player of the chosen rank one (index 0).
        result = _game(_card(5), _card(0)).play(self.pid, {"request_id": "win", "rank": 1, "stake": 10})
        # Require the win and a total return of twice the stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 20))
        # Require the wallet to reflect the net win.
        self.assertEqual(self._balance(), 1010.0)

    # Require a matching banker card to lose the whole stake.
    def test_banker_match_loses(self) -> None:
        # Deal a banker of the chosen rank one and a player of rank five.
        result = _game(_card(0), _card(5)).play(self.pid, {"request_id": "lose", "rank": 1, "stake": 10})
        # Require the loss and only the debited stake.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        self.assertEqual(self._balance(), 990.0)

    # Require neither card matching to return the stake as a push.
    def test_no_match_pushes(self) -> None:
        # Deal a banker of rank five and a player of rank seven against a chosen rank one.
        result = _game(_card(5), _card(7)).play(self.pid, {"request_id": "push", "rank": 1, "stake": 10})
        # Require the push and a full stake return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("push", 10))
        # Require the wallet to be unchanged after the push.
        self.assertEqual(self._balance(), 1000.0)

    # Require both cards sharing the chosen rank to take half the stake as a split.
    def test_split_takes_half(self) -> None:
        # Deal two cards of the chosen rank one from different suits.
        result = _game(_card(0, 0), _card(0, 1)).play(self.pid, {"request_id": "split", "rank": 1, "stake": 10})
        # Require the split and a half-stake return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("split", 5))
        # Require the wallet to reflect the half loss.
        self.assertEqual(self._balance(), 995.0)

    # Require invalid ranks and stakes to be rejected before any wallet movement.
    def test_invalid_requests_rejected(self) -> None:
        # Enumerate rejected requests spanning bad rank and bad stake.
        for bad in ({"request_id": "x1", "rank": 0, "stake": 10}, {"request_id": "x2", "rank": 14, "stake": 10}, {"request_id": "x3", "rank": 1, "stake": 0}, {"request_id": "x4", "rank": 1, "stake": 1.5}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid deal.
                    _game(_card(0), _card(5)).play(self.pid, bad)
        # Require the wallet to be untouched.
        self.assertEqual(self._balance(), 1000.0)

    # Require a retried deal to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game(_card(5), _card(0))
        # Play the first deal.
        first = game.play(self.pid, {"request_id": "dup", "rank": 1, "stake": 10})
        # Record the balance after the first settlement.
        after = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "dup", "rank": 1, "stake": 10})
        # Require the replay flag, the same dealt cards, and an unchanged wallet.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["detail"], first["round"]["detail"])
        self.assertEqual(self._balance(), after)

    # Require the paytable to keep the expected return below one across every possible deal.
    def test_house_edge_is_positive(self) -> None:
        # Fix a chosen rank; by symmetry every rank shares the same expected return.
        chosen = 0
        # Accumulate the total return over all ordered pairs of distinct cards for a unit stake.
        total = 0.0
        # Enumerate every possible banker card.
        for banker in range(rules.DECK):
            # Enumerate every possible distinct player card.
            for player in range(rules.DECK):
                # Skip the impossible deal where both cards are the same physical card.
                if player == banker:
                    # A single card cannot be dealt twice.
                    continue
                # Read whether each card matches the chosen rank.
                player_match = player // rules.SUITS == chosen
                banker_match = banker // rules.SUITS == chosen
                # Add the settlement multiplier for this exact deal.
                if player_match and banker_match:
                    # A split returns half the stake.
                    total += rules.SPLIT_MULTIPLIER
                elif player_match:
                    # A win returns twice the stake.
                    total += rules.WIN_MULTIPLIER
                elif banker_match:
                    # A loss returns nothing.
                    total += 0
                else:
                    # A push returns the whole stake.
                    total += rules.PUSH_MULTIPLIER
        # Compute the expected return per unit stake over all equally likely ordered deals.
        expected_return = total / (rules.DECK * (rules.DECK - 1))
        # Require a strict house edge driven entirely by the split half-loss.
        self.assertLess(expected_return, 1.0, f"Faro pays back {expected_return} which is not house-positive")
