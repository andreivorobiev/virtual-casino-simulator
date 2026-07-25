"""Focused Teen Patti Practice engine and service tests. (#150, TEENP-001/002)"""

# Import deep copy so the in-memory state store isolates every saved document.
import copy
# Import a deterministic seeded PRNG for the house-edge property check.
import random
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the shared shuffled-deck primitive for the house-edge simulation.
from casino.core.cards import shuffled_deck
# Import the shared ace-high rank values for strategy thresholds.
from casino.core.poker import RANK_VALUES
# Import the pure engine and the stateful service under test.
from casino.games.teen_patti import engine, service
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


# Build a Teen Patti service bound to in-memory fakes and a fixed fixture.
def _service(fixture, ledger=None, memory=None):
    # Use the supplied fakes or fresh ones for an isolated round.
    fake_ledger = ledger or FakeLedger()
    # Use the supplied state store or a fresh one.
    store = memory or MemoryState()
    # Compose the service with all seams injected and one pinned deal fixture.
    return service.TeenPattiService(ledger_gateway=service.CoreLedgerGateway(debit=fake_ledger.debit, credit=fake_ledger.credit, read_recent=fake_ledger.read_recent), state_loader=store.load, state_saver=store.save, get_player=lambda pid: {"player_id": pid, "balance": fake_ledger.balance}, clock=lambda: "2026-07-25T00:00:00Z", fixture_factory=lambda action_id: fixture), fake_ledger, store


# Verify Teen Patti ranks three-card hands, settles every path, and stays house-positive.
class TeenPattiTests(unittest.TestCase):
    # Compare two three-card hands through the evaluator.
    def _key(self, codes):
        # Return the comparison key for a three-card hand.
        return engine.comparison_key(engine.evaluate_three(codes))

    # Require the three-card ranking to place a sequence above a colour and read runs.
    def test_three_card_ranking(self) -> None:
        # Require three of a kind to be the top trail.
        self.assertEqual(engine.evaluate_three(["AS", "AH", "AD"])["name"], "trail")
        # Require a suited run to be a pure sequence.
        self.assertEqual(engine.evaluate_three(["4S", "5S", "6S"])["name"], "pure_sequence")
        # Require an unsuited run to be a sequence.
        self.assertEqual(engine.evaluate_three(["4S", "5D", "6H"])["name"], "sequence")
        # Require a sequence to beat a colour because runs are scarcer with three cards.
        self.assertGreater(self._key(["4S", "5D", "6H"]), self._key(["2S", "5S", "9S"]))
        # Require the ace-two-three lowest run to be recognized as a sequence.
        self.assertEqual(engine.evaluate_three(["AS", "2H", "3D"])["name"], "sequence")

    # Require a played trail against a qualifying dealer to win the ante, play, and Bonus.
    def test_play_trail_win_pays_bonus(self) -> None:
        # Deal the player a trail and the dealer a qualifying queen-high hand.
        fixture = {"player_cards": ["AS", "AH", "AD"], "dealer_cards": ["QC", "7D", "2H"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-1", "ante": 10})
        # Play the round.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-1", "decision": "play"})
        # Require a player win, the trail Bonus of five to one, and the matching net.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["bonus_credit"], settled["round"]["net"]), ("player_win", 50.0, 70.0))

    # Require a non-qualifying dealer to pay the ante and push the play.
    def test_dealer_not_qualified_pushes_play(self) -> None:
        # Deal the player a high card and the dealer a non-qualifying seven-high hand.
        fixture = {"player_cards": ["KS", "9D", "4H"], "dealer_cards": ["7C", "5D", "2H"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-2", "ante": 10})
        # Play into the non-qualifying dealer.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-2", "decision": "play"})
        # Require the ante to win even money and the play to push for a net gain of the ante.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["net"]), ("dealer_not_qualified", 10.0))

    # Require the Bonus to pay a sequence even in a losing showdown.
    def test_bonus_pays_on_sequence_in_loss(self) -> None:
        # Deal the player a sequence but let the dealer win with a trail.
        fixture = {"player_cards": ["4S", "5D", "6H"], "dealer_cards": ["AS", "AH", "AC"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-3", "ante": 10})
        # Play into the losing showdown.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-3", "decision": "play"})
        # Require the dealer win but still pay the sequence Bonus of even money.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["bonus_credit"], settled["round"]["net"]), ("dealer_win", 10.0, -10.0))

    # Require a fold to forfeit only the ante.
    def test_fold_forfeits_ante(self) -> None:
        # Deal a deterministic round.
        fixture = {"player_cards": ["2C", "7D", "9H"], "dealer_cards": ["AS", "AH", "AC"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-4", "ante": 10})
        # Fold the weak hand.
        folded = svc.decide("p1", deal["round"]["round_id"], {"action_id": "fold-4", "decision": "fold"})
        # Require the fold to forfeit only the ante with no dealer reveal.
        self.assertEqual((folded["round"]["outcome"], folded["round"]["net"], "dealer_cards" in folded["round"]), ("folded", -10.0, False))

    # Require a replayed decision to return the identical settled round without a second movement.
    def test_decision_replay_is_idempotent(self) -> None:
        # Deal a winning round.
        fixture = {"player_cards": ["AS", "AH", "AD"], "dealer_cards": ["QC", "7D", "2H"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-5", "ante": 10})
        # Play once and record the balance.
        first = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-5", "decision": "play"})
        # Capture the balance after the first settlement.
        after = fake_ledger.balance
        # Replay the identical decision.
        second = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-5", "decision": "play"})
        # Require the replay flag, the same terminal round, and an unchanged balance.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"], first["round"])
        self.assertEqual(fake_ledger.balance, after)

    # Require a decision action id reused with a changed decision to fail closed.
    def test_conflicting_decision_reuse_rejected(self) -> None:
        # Deal a deterministic round.
        fixture = {"player_cards": ["AS", "AH", "AD"], "dealer_cards": ["QC", "7D", "2H"]}
        # Build the service and deal.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-6", "ante": 10})
        # Play once.
        svc.decide("p1", deal["round"]["round_id"], {"action_id": "act-6", "decision": "play"})
        # Require reuse of the same action id with a fold to conflict.
        with self.assertRaises(ConflictError):
            # Attempt a conflicting decision under the used action id.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "act-6", "decision": "fold"})

    # Require a reload after a committed deal to recover without a duplicate debit.
    def test_reload_recovers_committed_deal(self) -> None:
        # Deal a deterministic round through shared fakes.
        fixture = {"player_cards": ["AS", "AH", "AD"], "dealer_cards": ["QC", "7D", "2H"]}
        # Build the first service with explicit fakes.
        ledger, store = FakeLedger(), MemoryState()
        # Build the service and deal.
        svc, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Deal a ten-token ante round.
        svc.start_round("p1", {"action_id": "deal-7", "ante": 10})
        # Count the ante debits committed after the deal.
        before = len([event for event in ledger.events if event["transaction_type"] == "TEEN_PATTI_ANTE_DEBIT"])
        # Rebuild a fresh service sharing the ledger and state to simulate a reload.
        reloaded, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Read state through the reloaded service to trigger recovery.
        reloaded.state("p1")
        # Require exactly one ante debit to survive the reload with no duplicate.
        self.assertEqual((before, len([event for event in ledger.events if event["transaction_type"] == "TEEN_PATTI_ANTE_DEBIT"])), (1, 1))

    # Require an invalid ante and an invalid decision to be rejected.
    def test_invalid_inputs_rejected(self) -> None:
        # Deal a deterministic round for the decision check.
        fixture = {"player_cards": ["AS", "AH", "AD"], "dealer_cards": ["QC", "7D", "2H"]}
        # Build the service.
        svc, fake_ledger, store = _service(fixture)
        # Require a non-positive ante to be rejected before any deal.
        with self.assertRaises(ValidationError):
            # Attempt a zero ante.
            svc.start_round("p1", {"action_id": "bad-1", "ante": 0})
        # Deal a valid round for the decision check.
        deal = svc.start_round("p1", {"action_id": "deal-8", "ante": 10})
        # Require an unknown decision to be rejected.
        with self.assertRaises(ValidationError):
            # Attempt an invalid decision.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-8", "decision": "raise"})

    # Require the near-optimal strategy to leave the ante house-positive.
    def test_house_edge_is_positive(self) -> None:
        # Seed a deterministic PRNG so this house-edge property check never flakes.
        rng = random.Random(20260150)
        # Run a large fixed sample of real deals under the near-optimal strategy.
        samples = 60000
        # Track total returns and total wagered tokens for the ante and play.
        total_return, total_wagered = 0.0, 0.0
        # Read the queen threshold once for the play decision.
        queen = RANK_VALUES["Q"]
        # Deal many rounds and settle the ante and play under the strategy.
        for _ in range(samples):
            # Draw one authoritative deal from the seeded shoe.
            cards = shuffled_deck(rng=rng)
            # Evaluate the player's three-card hand.
            player = engine.evaluate_three([card.code for card in cards[0:3]])
            # Play with any pair or better, or a queen-high hand; otherwise fold.
            playable = player["category"] >= engine.THREE_CARD_CATEGORIES.index("pair") or player["tiebreak"][0] >= queen
            # Fold every weaker hand, forfeiting only the ante.
            if not playable:
                # Add the forfeited ante to the wagered total.
                total_wagered += 1.0
                # Continue to the next deal without a play wager.
                continue
            # Evaluate the dealer's three-card hand.
            dealer = engine.evaluate_three([card.code for card in cards[3:6]])
            # Determine whether the dealer qualifies.
            qualifies = engine.dealer_qualifies(dealer)
            # Compare the two hands.
            comparison = (engine.comparison_key(player) > engine.comparison_key(dealer)) - (engine.comparison_key(player) < engine.comparison_key(dealer))
            # Settle the ante on a win, a non-qualify, a tie, or a loss.
            ante_credit = 2.0 if (comparison > 0 or not qualifies) else 1.0 if comparison == 0 else 0.0
            # Settle the fixed play the same as Casino qualification rules.
            play_credit = 2.0 if (qualifies and comparison > 0) else 1.0 if (not qualifies or comparison == 0) else 0.0
            # Add the Bonus on the player's own strong hand for a unit ante.
            total_return += ante_credit + play_credit + engine.BONUS_MULTIPLIERS.get(player["name"], 0)
            # Add the ante and play to the wagered total.
            total_wagered += 2.0
        # Require the near-optimal strategy to return strictly less than it wagers.
        self.assertLess(total_return / total_wagered, 1.0, f"Teen Patti pays back {total_return / total_wagered} under near-optimal play")
