"""Focused Mississippi Stud engine and service tests. (#143, MSTUD-001/002)"""

# Import deep copy so the in-memory state store isolates every saved document.
import copy
# Import a deterministic seeded PRNG for the house-edge property check.
import random
# Import the standard unittest framework used by the repository's focused suites.
import unittest
# Import Counter for the house-edge heuristic strategy helper.
from collections import Counter

# Import the shared shuffled-deck primitive for the house-edge simulation.
from casino.core.cards import shuffled_deck
# Import the shared ace-high rank values for strategy thresholds.
from casino.core.poker import RANK_VALUES
# Import the pure engine and the stateful service under test.
from casino.games.mississippi_stud import engine, service
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


# Build a Mississippi Stud service bound to in-memory fakes and a fixed fixture.
def _service(fixture, ledger=None, memory=None):
    # Use the supplied fakes or fresh ones for an isolated round.
    fake_ledger = ledger or FakeLedger()
    # Use the supplied state store or a fresh one.
    store = memory or MemoryState()
    # Compose the service with all seams injected and one pinned deal fixture.
    return service.MississippiStudService(ledger_gateway=service.CoreLedgerGateway(debit=fake_ledger.debit, credit=fake_ledger.credit, read_recent=fake_ledger.read_recent), state_loader=store.load, state_saver=store.save, get_player=lambda pid: {"player_id": pid, "balance": fake_ledger.balance}, clock=lambda: "2026-07-25T00:00:00Z", fixture_factory=lambda action_id: fixture), fake_ledger, store


# Play all three streets with a fixed one-times bet and return the settled round.
def _play_through(svc, player_id, round_id, tag, multiplier=1):
    # Bet each of the three streets in turn.
    result = None
    # Place one bet per street using a distinct action id.
    for street in range(1, engine.STREETS + 1):
        # Post the street bet and capture the latest response.
        result = svc.decide(player_id, round_id, {"action_id": f"{tag}-s{street}", "decision": "bet", "multiplier": multiplier})
    # Return the terminal settled response.
    return result


# Verify Mississippi Stud settles by paytable, runs three streets, and stays house-positive.
class MississippiStudTests(unittest.TestCase):
    # Classify one five-card hand through the engine paytable.
    def _tier(self, cards):
        # Return only the tier name for a completed hand.
        return engine.classify_final(cards)[0]

    # Require the paytable to band pairs into jacks-plus, push, and losing groups.
    def test_paytable_pair_bands(self) -> None:
        # Require a pair of jacks to win.
        self.assertEqual(engine.classify_final(["JS", "JH", "2C", "5D", "8S"]), ("pair_jacks_plus", "win", 1))
        # Require a pair of eights to push.
        self.assertEqual(engine.classify_final(["8S", "8H", "2C", "5D", "JS"]), ("pair_6_to_10", "push", 0.0))
        # Require a pair of threes to lose.
        self.assertEqual(engine.classify_final(["3S", "3H", "2C", "5D", "JS"]), ("pair_2_to_5", "lose", 0.0))
        # Require no pair to lose.
        self.assertEqual(engine.classify_final(["2C", "5D", "8S", "JS", "KH"])[1], "lose")
        # Require an ace-high straight flush to be the royal-flush tier.
        self.assertEqual(engine.classify_final(["10S", "JS", "QS", "KS", "AS"]), ("royal_flush", "win", 500))

    # Require a full three-street play on a paying hand to pay the paytable on the total wager.
    def test_full_play_pays_on_total_wager(self) -> None:
        # Deal a pair of jacks that never improves.
        fixture = {"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-1", "ante": 10})
        # Play all three streets at one time the ante.
        settled = _play_through(svc, "p1", deal["round"]["round_id"], "play-1")
        # Require a jacks-plus win, a forty-token total wager, and an even-money return netting the total.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["total_wager"], settled["round"]["payout"], settled["round"]["net"]), ("win", 40.0, 80.0, 40.0))

    # Require a pushing hand to return the entire wager for a flat result.
    def test_push_returns_total(self) -> None:
        # Deal a pair of eights that never improves.
        fixture = {"hole_cards": ["8S", "8H"], "community_cards": ["2C", "5D", "JS"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-2", "ante": 10})
        # Play all three streets.
        settled = _play_through(svc, "p1", deal["round"]["round_id"], "play-2")
        # Require the push to return the total wager and net zero.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["payout"], settled["round"]["net"]), ("push", 40.0, 0.0))

    # Require a losing hand to forfeit the whole stake.
    def test_losing_hand_takes_stake(self) -> None:
        # Deal a pair of threes that never improves.
        fixture = {"hole_cards": ["3S", "3H"], "community_cards": ["2C", "5D", "JS"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-3", "ante": 10})
        # Play all three streets into the losing hand.
        settled = _play_through(svc, "p1", deal["round"]["round_id"], "play-3")
        # Require the loss to return nothing and net the full total wager.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["payout"], settled["round"]["net"]), ("lose", 0.0, -40.0))

    # Require the community cards to reveal one per settled street.
    def test_community_reveals_progressively(self) -> None:
        # Deal a deterministic round.
        fixture = {"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-4", "ante": 10})
        # Require no community card before the first street bet.
        self.assertEqual(deal["round"]["community_revealed"], [])
        # Bet the first street and require one revealed community card.
        first = svc.decide("p1", deal["round"]["round_id"], {"action_id": "s1", "decision": "bet", "multiplier": 1})
        # Require exactly one community card and the second street pending.
        self.assertEqual((len(first["round"]["community_revealed"]), first["round"]["street"]), (1, 2))

    # Require a fold to forfeit only the wagers already made.
    def test_fold_forfeits_committed_wagers(self) -> None:
        # Deal a deterministic round.
        fixture = {"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-5", "ante": 10})
        # Bet the first street at one time the ante.
        svc.decide("p1", deal["round"]["round_id"], {"action_id": "s1", "decision": "bet", "multiplier": 1})
        # Fold on the second street.
        folded = svc.decide("p1", deal["round"]["round_id"], {"action_id": "fold", "decision": "fold"})
        # Require the fold to forfeit only the twenty tokens committed so far.
        self.assertEqual((folded["round"]["outcome"], folded["round"]["net"]), ("folded", -20.0))

    # Require a replayed street bet to return the advanced state without a second debit.
    def test_street_bet_replay_is_idempotent(self) -> None:
        # Deal a deterministic round.
        fixture = {"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-6", "ante": 10})
        # Bet the first street once.
        first = svc.decide("p1", deal["round"]["round_id"], {"action_id": "s1", "decision": "bet", "multiplier": 2})
        # Capture the balance after the first street bet.
        after = fake_ledger.balance
        # Replay the identical first-street bet.
        replay = svc.decide("p1", deal["round"]["round_id"], {"action_id": "s1", "decision": "bet", "multiplier": 2})
        # Require the replay flag and an unchanged balance.
        self.assertTrue(replay["replayed"])
        self.assertEqual(fake_ledger.balance, after)
        # Require the round to remain on the same advanced street.
        self.assertEqual(replay["round"]["street"], first["round"]["street"])

    # Require a reload after committed bets to recover without duplicate debits.
    def test_reload_recovers_committed_bets(self) -> None:
        # Deal a deterministic round through shared fakes.
        fixture = {"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]}
        # Build the first service instance with explicit fakes.
        ledger, store = FakeLedger(), MemoryState()
        # Deal and bet the first two streets.
        svc, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-7", "ante": 10})
        # Bet the first two streets.
        svc.decide("p1", deal["round"]["round_id"], {"action_id": "s1", "decision": "bet", "multiplier": 1})
        svc.decide("p1", deal["round"]["round_id"], {"action_id": "s2", "decision": "bet", "multiplier": 1})
        # Count the debits committed so far.
        before = len(ledger.events)
        # Rebuild a fresh service sharing the same ledger and state to simulate a reload.
        reloaded, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Read state through the reloaded service to trigger recovery.
        reloaded.state("p1")
        # Require no duplicate ledger events from the reload.
        self.assertEqual(len(ledger.events), before)

    # Require invalid antes, multipliers, and decisions to be rejected.
    def test_invalid_inputs_rejected(self) -> None:
        # Deal a deterministic round for the decision checks.
        fixture = {"hole_cards": ["JS", "JH"], "community_cards": ["2C", "5D", "8S"]}
        # Build the service.
        svc, fake_ledger, store = _service(fixture)
        # Require a non-positive ante to be rejected before any deal.
        with self.assertRaises(ValidationError):
            # Attempt a zero ante.
            svc.start_round("p1", {"action_id": "bad-1", "ante": 0})
        # Deal a valid round for the multiplier check.
        deal = svc.start_round("p1", {"action_id": "deal-8", "ante": 10})
        # Require an out-of-range bet multiplier to be rejected.
        with self.assertRaises(ValidationError):
            # Attempt a four-times bet.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "s1", "decision": "bet", "multiplier": 4})

    # Require the disciplined strategy to leave Mississippi Stud house-positive.
    def test_house_edge_is_positive(self) -> None:
        # Seed a deterministic PRNG so this house-edge property check never flakes.
        rng = random.Random(20260725)
        # Run a large fixed sample of real deals under a disciplined heuristic strategy.
        samples = 60000
        # Track total returns and total wagered tokens across the ante and street bets.
        total_return, total_wagered = 0.0, 0.0
        # Read the jack and six thresholds once for the strategy and paytable.
        jack, six = RANK_VALUES["J"], RANK_VALUES["6"]

        # Choose a two-card third-street bet size, or fold.
        def bet_two(cards):
            # Read the two hole-card values.
            values = sorted(RANK_VALUES[card.rank] for card in cards)
            # Bet three times with a pair of sixes or better.
            if values[0] == values[1] and values[0] >= six:
                # Raise strongly on a strong pair.
                return 3
            # Bet the minimum on any pair, two medium-or-high cards, or a high card.
            if values[0] == values[1] or (values[0] >= six and values[1] >= six) or values[1] >= jack:
                # Play the marginal hand for the minimum.
                return 1
            # Fold everything weaker.
            return 0

        # Choose a later-street bet size from the visible cards, or fold.
        def bet_more(cards):
            # Count ranks and suits to detect made hands and draws.
            rank_counts = Counter(RANK_VALUES[card.rank] for card in cards)
            # Read the best made-pair rank.
            best_pair = max((rank for rank, count in rank_counts.items() if count >= 2), default=0)
            # Read the largest same-suit count.
            flush_count = max(Counter(card.suit for card in cards).values())
            # Bet three times with a pair of sixes or better.
            if best_pair >= six:
                # Raise strongly on a paying pair.
                return 3
            # Bet three times with a completed flush draw at the last visible card.
            if flush_count == len(cards):
                # Raise strongly on a four-flush at fourth street.
                return 3
            # Bet the minimum on any pair, a near-flush, or two high cards.
            if best_pair >= 2 or flush_count >= len(cards) - 1 or sum(1 for card in cards if RANK_VALUES[card.rank] >= jack) >= 2:
                # Play the marginal hand for the minimum.
                return 1
            # Fold everything weaker.
            return 0

        # Deal many rounds and settle under the heuristic strategy.
        for _ in range(samples):
            # Draw one authoritative deal from the seeded shoe.
            cards = shuffled_deck(rng=rng)
            # Read the two hole cards and three community cards.
            hole, community = cards[0:2], cards[2:5]
            # Start every hand with the one-unit ante in the total.
            total = 1.0
            # Decide the third street from the two hole cards.
            multiplier = bet_two(hole)
            # Fold the third street when the strategy declines.
            if multiplier == 0:
                # Forfeit the ante and move on.
                total_wagered += total
                continue
            # Add the third-street bet to the total.
            total += multiplier
            # Decide the fourth street from the hole cards and the first community card.
            multiplier = bet_more([*hole, community[0]])
            # Fold the fourth street when the strategy declines.
            if multiplier == 0:
                # Forfeit the running total and move on.
                total_wagered += total
                continue
            # Add the fourth-street bet to the total.
            total += multiplier
            # Decide the fifth street from the hole cards and the first two community cards.
            multiplier = bet_more([*hole, community[0], community[1]])
            # Fold the fifth street when the strategy declines.
            if multiplier == 0:
                # Forfeit the running total and move on.
                total_wagered += total
                continue
            # Add the fifth-street bet to the total.
            total += multiplier
            # Classify the completed five-card hand.
            tier, result, mult = engine.classify_final([card.code for card in [*hole, *community]])
            # Pay a win, return a push, and forfeit a loss.
            total_return += total * (mult + 1) if result == "win" else total if result == "push" else 0.0
            # Add the completed total to the wagered sum.
            total_wagered += total
        # Require the disciplined strategy to return strictly less than it wagers.
        self.assertLess(total_return / total_wagered, 1.0, f"Mississippi Stud pays back {total_return / total_wagered} under the heuristic strategy")
