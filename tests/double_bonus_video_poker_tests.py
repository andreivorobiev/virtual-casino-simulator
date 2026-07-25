"""Focused Double Bonus Video Poker engine and service tests. (#131, DBVP-001/002)"""

# Import deep copy so the in-memory state store isolates every saved document.
import copy
# Import a deterministic seeded PRNG for the house-edge property check.
import random
# Import Counter for the house-edge heuristic strategy helper.
from collections import Counter
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the shared shuffled-deck primitive for the house-edge simulation.
from casino.core.cards import shuffled_deck
# Import the shared ace-high rank values for strategy thresholds.
from casino.core.poker import RANK_VALUES
# Import the pure engine and the stateful service under test.
from casino.games.double_bonus_video_poker import engine, service
# Import the standard bounded application errors the service raises.
from casino.errors import ConflictError, InsufficientFundsError, ValidationError


# Provide a minimal in-memory shared-ledger fake with balance enforcement.
class FakeLedger:
    # Start every fake wallet with a generous play-token balance.
    def __init__(self, balance: float = 100000.0):
        # Track committed ledger events for the apply-once recovery scan.
        self.events = []
        # Track the current balance so overdraws can be rejected.
        self.balance = balance

    # Reject an overdraw and otherwise append one debit event.
    def debit(self, player_id, amount, transaction_type, game, round_id, details):
        # Fail closed when the debit would overdraw the fake wallet.
        if round(amount, 2) > round(self.balance, 2):
            # Raise the standard insufficient-funds error like the real ledger.
            raise InsufficientFundsError("insufficient play tokens")
        # Reduce the balance by the committed magnitude.
        self.balance = round(self.balance - amount, 2)
        # Build one signed committed event.
        event = {"ledger_id": f"L{len(self.events)}", "player_id": player_id, "game": game, "round_id": round_id, "transaction_type": transaction_type, "amount": -round(amount, 2), "details": details}
        # Append and return the committed event.
        self.events.append(event)
        # Return the immutable committed event.
        return event

    # Append one credit event and increase the balance.
    def credit(self, player_id, amount, transaction_type, game, round_id, details):
        # Increase the balance by the returned tokens.
        self.balance = round(self.balance + amount, 2)
        # Build one signed committed event.
        event = {"ledger_id": f"L{len(self.events)}", "player_id": player_id, "game": game, "round_id": round_id, "transaction_type": transaction_type, "amount": round(amount, 2), "details": details}
        # Append and return the committed event.
        self.events.append(event)
        # Return the immutable committed event.
        return event

    # Return every committed event for the apply-once recovery scan.
    def read_recent(self, player_id=None, limit=100):
        # Return a copy so callers cannot mutate committed proof.
        return list(self.events)


# Provide a deep-copying in-memory player-state store.
class MemoryState:
    # Start with no persisted documents.
    def __init__(self):
        # Hold one document per player id.
        self.docs = {}

    # Load a detached copy of one player's document or a fresh default.
    def load(self, player_id):
        # Return a deep copy so service mutations never leak into storage.
        return copy.deepcopy(self.docs.get(player_id) or engine.default_state())

    # Save a detached copy of one player's document.
    def save(self, player_id, state):
        # Store a deep copy so later loads are isolated.
        self.docs[player_id] = copy.deepcopy(state)


# Build a Double Bonus service bound to in-memory fakes and a fixed fixture.
def _service(fixture, ledger=None, memory=None):
    # Use the supplied fakes or fresh ones for an isolated round.
    fake_ledger = ledger or FakeLedger()
    # Use the supplied state store or a fresh one.
    store = memory or MemoryState()
    # Compose the service with all seams injected and one pinned deal fixture.
    return service.DoubleBonusVideoPokerService(ledger_gateway=service.CoreLedgerGateway(debit=fake_ledger.debit, credit=fake_ledger.credit, read_recent=fake_ledger.read_recent), state_loader=store.load, state_saver=store.save, get_player=lambda pid: {"player_id": pid, "balance": fake_ledger.balance}, clock=lambda: "2026-07-25T00:00:00Z", fixture_factory=lambda action_id: fixture), fake_ledger, store


# Verify Double Bonus classifies hands, draws deterministically, and stays house-positive.
class DoubleBonusVideoPokerTests(unittest.TestCase):
    # Require the Double Bonus paytable to band four of a kind and trim two pair.
    def test_paytable_bands(self) -> None:
        # Require four aces to pay the top quad band.
        self.assertEqual(engine.classify(["AS", "AH", "AD", "AC", "KH"]), ("four_aces", 160))
        # Require four twos through fours to pay the middle quad band.
        self.assertEqual(engine.classify(["3S", "3H", "3D", "3C", "KH"]), ("four_2s_4s", 80))
        # Require four fives through kings to pay the base quad band.
        self.assertEqual(engine.classify(["KS", "KH", "KD", "KC", "2H"]), ("four_5s_ks", 50))
        # Require two pair to pay only even money.
        self.assertEqual(engine.classify(["AS", "AH", "KD", "KC", "2H"]), ("two_pair", 1))
        # Require a pair of jacks to pay even money and a pair of tens to pay nothing.
        self.assertEqual((engine.classify(["JS", "JH", "2C", "5D", "8S"])[0], engine.classify(["10S", "10H", "2C", "5D", "8S"])[0]), ("jacks_or_better", "nothing"))

    # Require holding three aces and drawing the fourth to pay four aces.
    def test_draw_completes_four_aces(self) -> None:
        # Deal three aces with an ace waiting in the replacement pile.
        fixture = {"hand": ["AS", "AH", "AD", "2C", "3D"], "draw_pile": ["AC", "KH", "4C", "5D", "6S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token round.
        deal = svc.start_round("p1", {"action_id": "deal-1", "bet": 10})
        # Hold the three aces and draw two replacements.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-1", "hold": [0, 1, 2]})
        # Require four aces, a one-hundred-sixty-times return, and the matching net.
        self.assertEqual((settled["round"]["hand_tier"], settled["round"]["payout"], settled["round"]["net"]), ("four_aces", 1600.0, 1590.0))

    # Require holding a made hand to keep it unchanged through the draw.
    def test_hold_all_keeps_made_hand(self) -> None:
        # Deal a pat pair of jacks.
        fixture = {"hand": ["JS", "JH", "3C", "6D", "9S"], "draw_pile": ["AC", "KH", "4C", "5D", "6S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token round.
        deal = svc.start_round("p1", {"action_id": "deal-2", "bet": 10})
        # Hold the two jacks and draw three replacements that do not improve.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-2", "hold": [0, 1]})
        # Require a jacks-or-better win at even money.
        self.assertEqual((settled["round"]["hand_tier"], settled["round"]["payout"], settled["round"]["net"]), ("jacks_or_better", 10.0, 0.0))

    # Require a busted draw to return nothing.
    def test_losing_hand_returns_nothing(self) -> None:
        # Deal a hand that draws to nothing.
        fixture = {"hand": ["2C", "5D", "8S", "JH", "KS"], "draw_pile": ["3C", "6D", "9S", "4H", "7C"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token round.
        deal = svc.start_round("p1", {"action_id": "deal-3", "bet": 10})
        # Draw five fresh cards by holding nothing.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-3", "hold": []})
        # Require the loss to return nothing and net the whole bet.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["payout"], settled["round"]["net"]), ("lose", 0.0, -10.0))

    # Require a replayed draw to return the identical settled hand without a second credit.
    def test_draw_replay_is_idempotent(self) -> None:
        # Deal a winning draw.
        fixture = {"hand": ["AS", "AH", "AD", "2C", "3D"], "draw_pile": ["AC", "KH", "4C", "5D", "6S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token round.
        deal = svc.start_round("p1", {"action_id": "deal-4", "bet": 10})
        # Draw once and record the balance.
        first = svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-4", "hold": [0, 1, 2]})
        # Capture the balance after the first settlement.
        after = fake_ledger.balance
        # Replay the identical draw.
        second = svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-4", "hold": [0, 1, 2]})
        # Require the replay flag, the same final hand, and an unchanged balance.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"]["final_hand"], first["round"]["final_hand"])
        self.assertEqual(fake_ledger.balance, after)

    # Require a draw action id reused with a changed hold to fail closed.
    def test_conflicting_draw_reuse_rejected(self) -> None:
        # Deal a deterministic round.
        fixture = {"hand": ["AS", "AH", "AD", "2C", "3D"], "draw_pile": ["AC", "KH", "4C", "5D", "6S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token round.
        deal = svc.start_round("p1", {"action_id": "deal-5", "bet": 10})
        # Draw once holding the three aces.
        svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-5", "hold": [0, 1, 2]})
        # Require reuse of the same action id with a different hold to conflict.
        with self.assertRaises(ConflictError):
            # Attempt a conflicting draw under the used action id.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-5", "hold": [0, 1]})

    # Require a reload after a committed deal to recover without a duplicate debit.
    def test_reload_recovers_committed_deal(self) -> None:
        # Deal a deterministic round through shared fakes.
        fixture = {"hand": ["AS", "AH", "AD", "2C", "3D"], "draw_pile": ["AC", "KH", "4C", "5D", "6S"]}
        # Build the first service with explicit fakes.
        ledger, store = FakeLedger(), MemoryState()
        # Build the service and deal.
        svc, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Deal a ten-token round.
        svc.start_round("p1", {"action_id": "deal-6", "bet": 10})
        # Count the wager debits committed after the deal.
        before = len([event for event in ledger.events if event["transaction_type"] == "DOUBLE_BONUS_VIDEO_POKER_WAGER_DEBIT"])
        # Rebuild a fresh service sharing the ledger and state to simulate a reload.
        reloaded, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Read state through the reloaded service to trigger recovery.
        reloaded.state("p1")
        # Require exactly one wager debit to survive the reload with no duplicate.
        self.assertEqual((before, len([event for event in ledger.events if event["transaction_type"] == "DOUBLE_BONUS_VIDEO_POKER_WAGER_DEBIT"])), (1, 1))

    # Require invalid bets and hold selections to be rejected.
    def test_invalid_inputs_rejected(self) -> None:
        # Deal a deterministic round for the hold check.
        fixture = {"hand": ["AS", "AH", "AD", "2C", "3D"], "draw_pile": ["AC", "KH", "4C", "5D", "6S"]}
        # Build the service.
        svc, fake_ledger, store = _service(fixture)
        # Require a non-positive bet to be rejected before any deal.
        with self.assertRaises(ValidationError):
            # Attempt a zero bet.
            svc.start_round("p1", {"action_id": "bad-1", "bet": 0})
        # Deal a valid round for the hold check.
        deal = svc.start_round("p1", {"action_id": "deal-7", "bet": 10})
        # Require an out-of-range hold position to be rejected.
        with self.assertRaises(ValidationError):
            # Attempt to hold a sixth nonexistent card.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "draw-7", "hold": [0, 5]})

    # Require the nine-six paytable to stay house-positive under a disciplined strategy.
    def test_house_edge_is_positive(self) -> None:
        # Seed a deterministic PRNG so this house-edge property check never flakes.
        rng = random.Random(20260131)
        # Run a large fixed sample of real deals under a decent draw heuristic.
        samples = 40000
        # Track the total returned tokens for a one-unit bet.
        total_return = 0.0
        # Read the jack threshold once for the strategy.
        jack = RANK_VALUES["J"]

        # Choose which card positions to hold with a decent video-poker heuristic.
        def choose_hold(hand):
            # Read rank and suit values once.
            values = [RANK_VALUES[card.rank] for card in hand]
            # Count ranks and suits for made hands and draws.
            rank_counts = Counter(values)
            suit_counts = Counter(card.suit for card in hand)
            # Hold every card of any rank that appears at least twice.
            pairs = [rank for rank, count in rank_counts.items() if count >= 2]
            # Hold made pairs, trips, and quads.
            if pairs:
                # Keep all cards forming a pair or better.
                return [index for index, value in enumerate(values) if value in pairs]
            # Hold a four-card flush.
            for suit, count in suit_counts.items():
                # Keep the four suited cards when a four-flush exists.
                if count == 4:
                    # Return the four suited positions.
                    return [index for index, card in enumerate(hand) if card.suit == suit]
            # Hold any high cards worth keeping.
            highs = [index for index, value in enumerate(values) if value >= jack]
            # Keep the high cards or draw five fresh cards.
            return highs

        # Deal many rounds and settle the draw under the heuristic.
        for _ in range(samples):
            # Draw one authoritative deal from the seeded shoe.
            cards = shuffled_deck(rng=rng)
            # Read the five dealt cards and the ordered replacement pile.
            hand, draw_pile = cards[0:5], cards[5:10]
            # Choose the held positions.
            hold = set(choose_hold(hand))
            # Build the final hand by keeping held cards and replacing discards in order.
            replacement = iter(draw_pile)
            # Compose the final five cards.
            final = [hand[index] if index in hold else next(replacement) for index in range(5)]
            # Add the paytable return for a unit bet.
            total_return += engine.classify([card.code for card in final])[1]
        # Require the disciplined strategy to return strictly less than the total bet.
        self.assertLess(total_return / samples, 1.0, f"Double Bonus pays back {total_return / samples} under the heuristic strategy")
