# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Four Card Poker engine and service tests. (#141, FOURCP-001/002)"""

# Import deep copy so the in-memory state store isolates every saved document.
import copy
# Import JSON support for exact disposable provider bytes.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import a deterministic seeded PRNG for the house-edge property check.
import random
# Import subprocess support for independent stale-load workers.
import subprocess
# Import the active interpreter selected by the repository test runner.
import sys
# Import task-owned temporary directories for provider bytes and gates.
import tempfile
# Import bounded polling for worker rendezvous.
import time
# Import the standard unittest framework used by the repository's focused suites.
import unittest
# Import portable paths for exact checkout and worker files.
from pathlib import Path

# Import the shared shuffled-deck primitive for the house-edge simulation.
from casino.core.cards import shuffled_deck
# Import the shared ace-high rank values for strategy thresholds.
from casino.core.poker import RANK_VALUES
# Import the pure engine and the stateful service under test.
from casino.games.four_card_poker import engine, service
# Import the standard bounded application errors the service raises.
from casino.errors import ConflictError, InsufficientFundsError, ValidationError


# Provide a minimal in-memory shared-ledger fake with balance enforcement.
class FakeLedger:
    # Start every fake wallet with a generous play-token balance.
    def __init__(self, balance: float = 100000.0, *, lost_response_types=(), before_failure=None):
        # Track committed ledger events for the apply-once recovery scan.
        self.events = []
        # Track the current balance so overdraws can be rejected.
        self.balance = balance
        # Allow one deterministic failure before a movement reaches the ledger.
        self.fail_next = False
        # Select movement types whose first committed response is lost.
        self.lost_response_types = set(lost_response_types)
        # Retain one optional sibling publication before a rejected movement.
        self.before_failure = before_failure
        # Count every mutation callback attempt by transaction vocabulary.
        self.apply_calls = {}

    # Reject an overdraw and otherwise append one debit event.
    def debit(self, player_id, amount, transaction_type, game, round_id, details):
        # Count the attempted debit before failure or commit handling.
        self.apply_calls[transaction_type] = self.apply_calls.get(transaction_type, 0) + 1
        # Fail before committing when the focused schedule requests rejection.
        if self.fail_next:
            # Consume the one-shot pre-commit failure.
            self.fail_next = False
            # Publish an unrelated sibling at the exact rollback boundary when supplied.
            if self.before_failure is not None:
                # Invoke the bounded sibling seam once.
                self.before_failure()
            # Surface the same standard validation-shaped failure used by request tests.
            raise ValidationError("rejected Four Card Poker debit")
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
        # Lose the response only after the immutable debit is committed.
        if transaction_type in self.lost_response_types:
            # Consume the one-shot transport failure stage.
            self.lost_response_types.remove(transaction_type)
            # Surface an ambiguous response so normal recovery must find proof.
            raise RuntimeError(f"lost {transaction_type} response")
        # Return the immutable committed event.
        return event

    # Append one credit event and increase the balance.
    def credit(self, player_id, amount, transaction_type, game, round_id, details):
        # Count the attempted credit before committing or losing its response.
        self.apply_calls[transaction_type] = self.apply_calls.get(transaction_type, 0) + 1
        # Increase the balance by the returned tokens.
        self.balance = round(self.balance + amount, 2)
        # Build one signed committed event.
        event = {"ledger_id": f"L{len(self.events)}", "player_id": player_id, "game": game, "round_id": round_id, "transaction_type": transaction_type, "amount": round(amount, 2), "details": details}
        # Append and return the committed event.
        self.events.append(event)
        # Lose the response only after the immutable credit is committed.
        if transaction_type in self.lost_response_types:
            # Consume the one-shot transport failure stage.
            self.lost_response_types.remove(transaction_type)
            # Surface an ambiguous response so reload recovery owns reconciliation.
            raise RuntimeError(f"lost {transaction_type} response")
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

    # Apply one callback to provider-current state and publish its detached result.
    def update(self, player_id, mutator):
        # Give the callback a detached document so failed transitions cannot leak.
        current = copy.deepcopy(self.docs.get(player_id) or engine.default_state())
        # Apply the complete transition inside this fake provider boundary.
        updated = mutator(current)
        # Store a detached result so later loads remain isolated.
        self.docs[player_id] = copy.deepcopy(updated)
        # Return an independent authoritative value to the service.
        return copy.deepcopy(updated)


# Build a Four Card Poker service bound to in-memory fakes and a fixed fixture.
def _service(fixture, ledger=None, memory=None):
    # Use the supplied fakes or fresh ones for an isolated round.
    fake_ledger = ledger or FakeLedger()
    # Use the supplied state store or a fresh one.
    store = memory or MemoryState()
    # Compose the service with all seams injected and one pinned deal fixture.
    return service.FourCardPokerService(repository=store, ledger_gateway=service.CoreLedgerGateway(debit=fake_ledger.debit, credit=fake_ledger.credit, read_recent=fake_ledger.read_recent), get_player=lambda pid: {"player_id": pid, "balance": fake_ledger.balance}, clock=lambda: "2026-07-24T00:00:00Z", fixture_factory=lambda action_id: fixture), fake_ledger, store


# Verify Four Card Poker ranks hands, settles every path, and stays house-positive.
class FourCardPokerTests(unittest.TestCase):
    # Compare two card-code hands through the four-card evaluator.
    def _key(self, codes):
        # Return the comparison key for a four-card hand.
        return engine.comparison_key(engine.evaluate_four(codes))

    # Require the four-card ranking to place trips above a flush and a straight.
    def test_four_card_ranking_order(self) -> None:
        # Require four of a kind to be the top category.
        self.assertEqual(engine.evaluate_four(["AS", "AH", "AD", "AC"])["name"], "four_of_a_kind")
        # Require a four-card straight flush to rank as such.
        self.assertEqual(engine.evaluate_four(["9S", "10S", "JS", "QS"])["name"], "straight_flush")
        # Require three of a kind to beat a flush with four cards.
        self.assertGreater(self._key(["AS", "AH", "AD", "2C"]), self._key(["2S", "5S", "9S", "KS"]))
        # Require a flush to beat a straight.
        self.assertGreater(self._key(["2S", "5S", "9S", "KS"]), self._key(["9S", "10H", "JD", "QC"]))
        # Require the ace-low wheel to be recognized as a straight with high card four.
        self.assertEqual((engine.evaluate_four(["AS", "2H", "3D", "4C"])["name"], engine.evaluate_four(["AS", "2H", "3D", "4C"])["tiebreak"]), ("straight", [4]))

    # Require the Aces Up qualifier to accept a pair of aces but reject a lesser pair.
    def test_aces_up_qualifier(self) -> None:
        # Require a pair of aces to qualify.
        self.assertEqual(engine.aces_up_name(engine.evaluate_four(["AS", "AH", "5D", "9C"])), "pair_of_aces")
        # Require a pair of kings to fail the qualifier.
        self.assertIsNone(engine.aces_up_name(engine.evaluate_four(["KS", "KH", "5D", "9C"])))

    # Require a played pair of aces against a dealer high card to win the ante and play.
    def test_play_win_pays_ante_and_play(self) -> None:
        # Deal the player a pair of aces and the dealer six low cards with no made hand.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Build the service and deal the round.
        svc, fake_ledger, store = _service(fixture)
        # Start the round with a ten-token ante and no Aces Up bet.
        deal = svc.start_round("p1", {"action_id": "deal-1", "ante": 10})
        # Read the deterministic round id for the decision route.
        round_id = deal["round"]["round_id"]
        # Play at one time the ante.
        settled = svc.decide("p1", round_id, {"action_id": "play-1", "decision": "play", "multiplier": 1})
        # Require a player win and the even-money ante plus play return.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["payout"], settled["round"]["net"]), ("player_win", 40.0, 20.0))

    # Require a played weak hand against a dealer trips to lose both wagers.
    def test_play_loss_takes_both(self) -> None:
        # Deal the player a high-card hand and the dealer three kings.
        fixture = {"player_cards": ["2C", "3D", "5H", "7S", "9C"], "dealer_cards": ["KS", "KH", "KD", "2S", "3C", "4H"]}
        # Build the service and deal the round.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-2", "ante": 10})
        # Play at one time the ante against the stronger dealer.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-2", "decision": "play", "multiplier": 1})
        # Require a dealer win, no return, and the full loss of ante and play.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["payout"], settled["round"]["net"]), ("dealer_win", 0.0, -20.0))

    # Require an exact hand tie to be awarded to the player.
    def test_tie_goes_to_player(self) -> None:
        # Deal identical ace-king-nine-five best hands to both sides.
        fixture = {"player_cards": ["AS", "KH", "9D", "5C", "2H"], "dealer_cards": ["AD", "KS", "9H", "5S", "3C", "2D"]}
        # Build the service and deal the round.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-3", "ante": 10})
        # Play at one time the ante into the tie.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-3", "decision": "play", "multiplier": 1})
        # Require the tie to pay the player like a win.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["net"]), ("player_win", 20.0))

    # Require the Ante Bonus to pay on the player's three of a kind regardless of the dealer.
    def test_ante_bonus_pays_on_trips(self) -> None:
        # Deal the player trip queens but let the dealer win with a straight flush.
        fixture = {"player_cards": ["QS", "QH", "QD", "5C", "2H"], "dealer_cards": ["6S", "7S", "8S", "9S", "2C", "3D"]}
        # Build the service and deal the round.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-4", "ante": 10})
        # Play at one time the ante into a losing showdown.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-4", "decision": "play", "multiplier": 1})
        # Require the dealer win but still pay the trips Ante Bonus of two times the ante.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["ante_bonus_credit"], settled["round"]["payout"]), ("dealer_win", 20.0, 20.0))

    # Require the Aces Up side bet to pay even on a fold.
    def test_fold_still_settles_aces_up(self) -> None:
        # Deal the player a pair of aces so the Aces Up side bet wins.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Build the service and deal the round with an Aces Up side bet.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante and a four-token Aces Up bet.
        deal = svc.start_round("p1", {"action_id": "deal-5", "ante": 10, "aces_up": 4})
        # Fold the ante while keeping the independent side bet live.
        settled = svc.decide("p1", deal["round"]["round_id"], {"action_id": "fold-5", "decision": "fold"})
        # Require the fold to forfeit the ante but pay the pair-of-aces Aces Up return of two times the bet.
        self.assertEqual((settled["round"]["outcome"], settled["round"]["aces_up_credit"], settled["round"]["net"]), ("folded", 8.0, -6.0))

    # Require a replayed decision to return the identical settled round without a second movement.
    def test_decision_replay_is_idempotent(self) -> None:
        # Deal a deterministic winning round.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Build the service and deal the round.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-6", "ante": 10})
        # Play once and record the balance.
        first = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-6", "decision": "play", "multiplier": 2})
        # Capture the balance after the first settlement.
        after = fake_ledger.balance
        # Replay the identical decision.
        second = svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-6", "decision": "play", "multiplier": 2})
        # Require the replay flag, the same terminal round, and an unchanged balance.
        self.assertTrue(second["replayed"])
        self.assertEqual(second["round"], first["round"])
        self.assertEqual(fake_ledger.balance, after)

    # Require a decision action id reused with a changed decision to fail closed.
    def test_conflicting_decision_reuse_rejected(self) -> None:
        # Deal a deterministic round.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Build the service and deal the round.
        svc, fake_ledger, store = _service(fixture)
        # Deal a ten-token ante round.
        deal = svc.start_round("p1", {"action_id": "deal-7", "ante": 10})
        # Play once at one time the ante.
        svc.decide("p1", deal["round"]["round_id"], {"action_id": "act-7", "decision": "play", "multiplier": 1})
        # Require reuse of the same action id with a different raise to conflict.
        with self.assertRaises(ConflictError):
            # Attempt a conflicting decision under the used action id.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "act-7", "decision": "play", "multiplier": 3})

    # Require a reload after a committed deal to recover the round without a duplicate debit.
    def test_reload_recovers_committed_deal(self) -> None:
        # Deal a deterministic round through a shared ledger and state store.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Build the service with explicit fakes so a fresh service can share them.
        ledger, store = FakeLedger(), MemoryState()
        # Build the first service instance and deal.
        svc, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Deal a ten-token ante round.
        svc.start_round("p1", {"action_id": "deal-8", "ante": 10})
        # Count the opening debits committed after the deal.
        opening_events = [event for event in ledger.events if event["transaction_type"] == "FOUR_CARD_POKER_OPENING_DEBIT"]
        # Rebuild a fresh service sharing the same ledger and state to simulate a reload.
        reloaded, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Read state through the reloaded service to trigger recovery.
        reloaded.state("p1")
        # Require exactly one opening debit to survive the reload with no duplicate.
        self.assertEqual(len(opening_events), 1)
        self.assertEqual(len([event for event in ledger.events if event["transaction_type"] == "FOUR_CARD_POKER_OPENING_DEBIT"]), 1)

    # Confirm a rejected opening reverses only action-owned game fields.
    def test_rejected_opening_rollback_preserves_concurrent_sibling(self) -> None:
        # Build the exact winning fixture used by normal settlement tests.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Own isolated provider-current state for this schedule.
        store = MemoryState()

        # Publish one unrelated sibling after preparation but before rollback.
        def publish_sibling():
            # Retain evidence outside Four Card Poker's owned state fields.
            store.docs["p1"]["atomic_markers"] = ["concurrent"]

        # Reject the first debit before any immutable movement exists.
        ledger = FakeLedger(before_failure=publish_sibling)
        # Select the one-shot pre-commit failure path.
        ledger.fail_next = True
        # Build the real service around provider-like state and settlement seams.
        svc, _, _ = _service(fixture, ledger=ledger, memory=store)
        # Require the original validation failure from the movement boundary.
        with self.assertRaisesRegex(ValidationError, "rejected Four Card Poker debit"):
            # Attempt one opening-backed deal.
            svc.start_round("p1", {"action_id": "deal-rollback", "ante": 10})
        # Read provider-owned state after compare-and-restore.
        persisted = store.docs["p1"]
        # Require actionable game state, sibling preservation, and zero movement.
        self.assertEqual((persisted["active_round"], persisted["atomic_markers"], ledger.events), (None, ["concurrent"], []))

    # Confirm an opening debit whose response is lost recovers without a second movement.
    def test_lost_opening_response_recovers_once(self) -> None:
        # Build one deterministic winning fixture.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Lose only the first committed opening response.
        ledger = FakeLedger(lost_response_types={"FOUR_CARD_POKER_OPENING_DEBIT"})
        # Build the service and provider-like state fixture.
        svc, _, store = _service(fixture, ledger=ledger)
        # Surface the injected post-commit response loss.
        with self.assertRaisesRegex(RuntimeError, "lost FOUR_CARD_POKER_OPENING_DEBIT response"):
            # Issue one stable opening action.
            svc.start_round("p1", {"action_id": "deal-lost-opening", "ante": 10})
        # Reconcile immutable proof through the normal state endpoint.
        recovered = svc.state("p1")
        # Replay the exact deal after recovery.
        replayed = svc.start_round("p1", {"action_id": "deal-lost-opening", "ante": 10})
        # Require one provider mutation, one event, a complete marker, and stable replay identity.
        self.assertEqual((ledger.apply_calls["FOUR_CARD_POKER_OPENING_DEBIT"], len(ledger.events), recovered["state"]["active_round"]["opening_status"], replayed["round"]["round_id"]), (1, 1, "complete", recovered["state"]["active_round"]["round_id"]))
        # Require the private optimistic baseline never to persist.
        self.assertNotIn(service._ATOMIC_BASELINE_KEY, store.docs["p1"])

    # Confirm a play debit whose response is lost settles without duplicating any movement.
    def test_lost_play_response_recovers_once(self) -> None:
        # Build one deterministic winning fixture with a positive settlement.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Lose only the committed play-debit response.
        ledger = FakeLedger(lost_response_types={"FOUR_CARD_POKER_PLAY_DEBIT"})
        # Build the exact service around isolated state.
        svc, _, _store = _service(fixture, ledger=ledger)
        # Prepare one opening-backed decision.
        started = svc.start_round("p1", {"action_id": "deal-lost-play", "ante": 10})
        # Surface the lost committed play response.
        with self.assertRaisesRegex(RuntimeError, "lost FOUR_CARD_POKER_PLAY_DEBIT response"):
            # Issue the stable play action once.
            svc.decide("p1", started["round"]["round_id"], {"action_id": "play-lost-debit", "decision": "play", "multiplier": 1})
        # Recover play proof and terminal settlement through a normal read.
        recovered = svc.state("p1")
        # Replay the same terminal decision without any second movement.
        replayed = svc.decide("p1", started["round"]["round_id"], {"action_id": "play-lost-debit", "decision": "play", "multiplier": 1})
        # Require one opening, play, and settlement provider call with stable terminal state.
        self.assertEqual((ledger.apply_calls["FOUR_CARD_POKER_OPENING_DEBIT"], ledger.apply_calls["FOUR_CARD_POKER_PLAY_DEBIT"], ledger.apply_calls["FOUR_CARD_POKER_SETTLEMENT_CREDIT"], replayed["round"], recovered["state"]["recent_rounds"][-1]), (1, 1, 1, recovered["state"]["recent_rounds"][-1], recovered["state"]["recent_rounds"][-1]))

    # Confirm a settlement credit whose response is lost recovers without a second credit.
    def test_lost_settlement_response_recovers_once(self) -> None:
        # Build one deterministic winning fixture with returned tokens.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Lose only the first committed settlement response.
        ledger = FakeLedger(lost_response_types={"FOUR_CARD_POKER_SETTLEMENT_CREDIT"})
        # Build the exact service around isolated state.
        svc, _, _store = _service(fixture, ledger=ledger)
        # Prepare one opening-backed decision.
        started = svc.start_round("p1", {"action_id": "deal-lost-credit", "ante": 10})
        # Surface the lost committed settlement response.
        with self.assertRaisesRegex(RuntimeError, "lost FOUR_CARD_POKER_SETTLEMENT_CREDIT response"):
            # Issue the stable winning play once.
            svc.decide("p1", started["round"]["round_id"], {"action_id": "play-lost-credit", "decision": "play", "multiplier": 1})
        # Recover immutable proof through the normal state endpoint.
        recovered = svc.state("p1")
        # Replay the exact terminal action without another credit.
        replayed = svc.decide("p1", started["round"]["round_id"], {"action_id": "play-lost-credit", "decision": "play", "multiplier": 1})
        # Require exactly one call for every movement and the exact recovered result.
        self.assertEqual((ledger.apply_calls["FOUR_CARD_POKER_OPENING_DEBIT"], ledger.apply_calls["FOUR_CARD_POKER_PLAY_DEBIT"], ledger.apply_calls["FOUR_CARD_POKER_SETTLEMENT_CREDIT"], replayed["round"], recovered["state"]["recent_rounds"][-1]), (1, 1, 1, recovered["state"]["recent_rounds"][-1], recovered["state"]["recent_rounds"][-1]))

    # Prove stale fresh processes preserve siblings and one provider-winning decision.
    def test_fresh_process_fold_race_preserves_provider_winner(self) -> None:
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "p1.json"
            # Create the state directory before seeding one active decision.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Build one deterministic decision round with committed opening proof.
            active_round = engine.create_round("p1", 10, 0, "deal-process", round_id=engine.round_id_for("p1", "deal-process"), created_at="2026-08-15T00:00:00Z", request_fingerprint=service.request_fingerprint({"stage": "deal", "ante": 10.0, "aces_up": 0.0}), fixture={"player_cards": ["2C", "3D", "5H", "7S", "9C"], "dealer_cards": ["KS", "KH", "KD", "2S", "3C", "4H"]})
            # Mark opening proof complete so both workers race only the terminal fold.
            active_round.update({"opening_status": "complete", "opening_ledger_id": "ledger-opening"})
            # Seed an unrelated sibling field that the game transition must not own.
            baseline = {**engine.default_state(), "active_round": active_round, "atomic_markers": ["seed"]}
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps(baseline, sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind all child persistence to the disposable root.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one service worker whose repository load pauses after capturing stale state.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.errors import ConflictError
from casino.games.four_card_poker import engine
from casino.games.four_card_poker.service import FourCardPokerService, StateRepository
base = StateRepository()
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
action_id = sys.argv[3]
class RendezvousRepository:
    def load(self, player_id):
        state = base.load(player_id)
        ready.write_text('ready', encoding='utf-8')
        deadline = time.monotonic() + 10
        while not release.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not release.exists():
            raise RuntimeError('Four Card Poker race release timed out')
        return state
    def update(self, player_id, mutator):
        return base.update(player_id, mutator)
class NoLedger:
    def find(self, _player_id, _action_key):
        return None
service = FourCardPokerService(repository=RendezvousRepository(), ledger_gateway=NoLedger(), get_player=lambda player_id: {'player_id': player_id, 'balance': 99990.0}, clock=lambda: '2026-08-15T00:01:00Z')
try:
    result = service.decide('p1', engine.round_id_for('p1', 'deal-process'), {'action_id': action_id, 'decision': 'fold'})
    print('PASS:' + result['round']['decision_action_id'])
except ConflictError:
    print('CONFLICT')
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start one winner candidate and one stale loser candidate.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"fold-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain process and gate ownership.
                workers.append((process, ready_path, release_path))
            # Bound the stale-load rendezvous.
            deadline = time.monotonic() + 10
            # Wait until both workers have captured the same initial document.
            while not all(ready.exists() for _process, ready, _release in workers) and time.monotonic() < deadline:
                # Stop early if either worker failed before readiness.
                if any(process.poll() is not None for process, _ready, _release in workers):
                    # Leave polling for the diagnostic assertion below.
                    break
                # Yield briefly without starting another action.
                time.sleep(0.01)
            # Require both stale snapshots before publishing a concurrent sibling.
            self.assertTrue(all(ready.exists() for _process, ready, _release in workers))
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.four_card_poker import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('four_card_poker', 'p1', add, engine.default_state)\n"
            # Commit the sibling after both workers captured their stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish the winning fold.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=15)
            # Require the first fold to commit.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:fold-process-0"), winner_error)
            # Release the stale second worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require the second action to conflict instead of overwriting the winner.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Resolve the sole terminal history row.
            terminal = persisted["recent_rounds"][-1]
            # Require the winning decision, sibling preservation, and no active-round resurrection.
            self.assertEqual((persisted["active_round"], len(persisted["recent_rounds"]), terminal["decision_action_id"], persisted["atomic_markers"]), (None, 1, "fold-process-0", ["seed", "concurrent"]))

    # Require an invalid ante and an invalid multiplier to be rejected.
    def test_invalid_inputs_rejected(self) -> None:
        # Deal a deterministic round for the multiplier check.
        fixture = {"player_cards": ["AS", "AH", "9C", "5D", "2H"], "dealer_cards": ["2C", "3D", "5S", "7H", "8C", "10D"]}
        # Build the service.
        svc, fake_ledger, store = _service(fixture)
        # Require a non-positive ante to be rejected before any deal.
        with self.assertRaises(ValidationError):
            # Attempt a zero ante.
            svc.start_round("p1", {"action_id": "bad-1", "ante": 0})
        # Deal a valid round for the decision check.
        deal = svc.start_round("p1", {"action_id": "deal-9", "ante": 10})
        # Require an out-of-range play multiplier to be rejected.
        with self.assertRaises(ValidationError):
            # Attempt a four-times raise that the table does not offer.
            svc.decide("p1", deal["round"]["round_id"], {"action_id": "play-9", "decision": "play", "multiplier": 4})

    # Require the optimal strategy to leave the ante and play house-positive.
    def test_house_edge_is_positive(self) -> None:
        # Seed a deterministic PRNG so this house-edge property check never flakes.
        rng = random.Random(20240724)
        # Run a large fixed sample of real deals under the disciplined optimal strategy.
        samples = 60000
        # Track total returns and total wagered tokens for the ante and play.
        total_return, total_wagered = 0.0, 0.0
        # Read the two-pair category index once for the raise decision.
        two_pair = engine.FOUR_CARD_CATEGORIES.index("two_pair")
        # Deal many rounds and settle the ante and play under optimal play.
        for _ in range(samples):
            # Draw one authoritative deal from the seeded shoe.
            cards = shuffled_deck(rng=rng)
            # Select the player's best four-card hand from five cards.
            player = engine.best_four([card.code for card in cards[0:5]])
            # Fold every high-card hand, forfeiting only the one-unit ante.
            if player["name"] == "high_card":
                # Add the forfeited ante to the wagered total.
                total_wagered += 1.0
                # Continue to the next deal without a play wager.
                continue
            # Raise to three times with two pair or better, otherwise play the minimum.
            multiplier = 3 if player["category"] >= two_pair else 1
            # Select the dealer's best four-card hand from six cards.
            dealer = engine.best_four([card.code for card in cards[5:11]])
            # Award ties to the player when comparing the two best hands.
            win = engine.comparison_key(player) >= engine.comparison_key(dealer)
            # Pay the ante, play, and Ante Bonus on this deal for a unit ante.
            total_return += (2.0 + multiplier * 2.0 if win else 0.0) + engine.ANTE_BONUS_MULTIPLIERS.get(player["name"], 0)
            # Add the ante and play to the wagered total.
            total_wagered += 1.0 + multiplier
        # Require the disciplined strategy to return strictly less than it wagers.
        self.assertLess(total_return / total_wagered, 1.0, f"Four Card Poker pays back {total_return / total_wagered} under optimal play")
