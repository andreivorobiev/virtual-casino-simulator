# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused ledger, retry, reload, and privacy tests for issue #87 Scratch Cards."""

# Import deep-copy support for storage fakes that behave like JSON persistence.
import copy
# Import the dependency-free standard test runner.
import unittest

# Import canonical conflict, insufficient-funds, and not-found errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError
# Import the pure engine for default state and stable identity helpers.
from casino.games.scratch_cards import engine
# Import the orchestration service with injectable seams.
from casino.games.scratch_cards.service import ScratchCardsService


# Supply deterministic outcome selection followed by zero-valued shuffle swaps.
class SequenceRandom:
    # Store only the first documented outcome roll.
    def __init__(self, outcome_roll):
        # Preserve the first call separately from later shuffle calls.
        self.outcome_roll = outcome_roll
        # Track whether the outcome has already been returned.
        self.used = False

    # Return the outcome once and zero for every deterministic swap.
    def __call__(self, upper_bound):
        # Use the documented roll only for the one-hundred-slot outcome call.
        if not self.used:
            # Mark the outcome as consumed before returning it.
            self.used = True
            # Verify the fixture stays inside the engine request.
            if not 0 <= self.outcome_roll < upper_bound:
                # Fail loudly for a broken deterministic fixture.
                raise AssertionError("outcome fixture left the requested bound")
            # Return the selected outcome tier.
            return self.outcome_roll
        # Keep every Fisher-Yates swap deterministic after the outcome call.
        return 0


# Provide an in-memory apply-once ledger gateway with committed event recovery.
class FakeLedgerGateway:
    # Initialize committed events, call evidence, and optional debit failure.
    def __init__(self):
        # Store events by deterministic private action key.
        self.events = {}
        # Record every gateway invocation for exact call-count assertions.
        self.calls = []
        # Allow one test to reject the next debit before an event commits.
        self.reject_debits = False

    # Apply or replay one signed event without touching a real wallet.
    def apply_once(self, *, player_id, amount, transaction_type, card_id, action_key, details):
        # Record the full action identity before resolving its outcome.
        self.calls.append(action_key)
        # Reject configured wager debits through the canonical domain error.
        if self.reject_debits and amount < 0 and action_key not in self.events:
            # Simulate the shared provider's no-commit insufficient-funds path.
            raise InsufficientFundsError()
        # Return an existing atomic event for a safe retry.
        if action_key in self.events:
            # Read the immutable event before validating semantic replay content.
            existing = self.events[action_key]
            # Reject a changed amount or transaction meaning like the production gateway.
            if existing["amount"] != amount or existing["transaction_type"] != transaction_type:
                # Preserve one immutable financial meaning per action key.
                raise ConflictError("fake ledger action identity conflict")
            # Reject changed purchase or completion action metadata like production.
            if existing["details"].get("request_fingerprint") != details.get("request_fingerprint") or existing["details"].get("action_id") != details.get("action_id"):
                # Fail before returning a semantically unrelated committed event.
                raise ConflictError("fake ledger action content conflict")
            # Reuse the original event as exactly-once evidence.
            return copy.deepcopy(existing), True
        # Build a minimal shared-ledger-shaped event for service recovery logic.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "game": engine.GAME_ID, "round_id": card_id, "amount": amount, "transaction_type": transaction_type, "ts": "2026-07-14T00:00:00Z", "details": {**copy.deepcopy(details), "idempotency_key": action_key}}
        # Commit the event under its deterministic action key.
        self.events[action_key] = copy.deepcopy(event)
        # Return the new event and non-replay evidence.
        return event, False


# Verify the complete isolated state and ledger orchestration contract.
class ScratchCardsServiceTests(unittest.TestCase):
    # Build fresh in-memory persistence and ledger seams before every test.
    def setUp(self):
        # Store private JSON-like documents by authenticated player id.
        self.states = {}
        # Create one reusable apply-once fake ledger.
        self.ledger = FakeLedgerGateway()

    # Read a detached state document like the real JSON provider.
    def load_state(self, player_id):
        # Return a copy so unsaved mutations cannot leak into persistence.
        return copy.deepcopy(self.states.get(player_id, engine.default_state()))

    # Persist a detached state document like the real JSON provider.
    def save_state(self, player_id, state):
        # Copy nested private data into the test store.
        self.states[player_id] = copy.deepcopy(state)

    # Build one service with a selected deterministic outcome tier.
    def service(self, outcome_roll=99, state_saver=None):
        # Return the production service over isolated test seams.
        return ScratchCardsService(ledger_gateway=self.ledger, state_loader=self.load_state, state_saver=state_saver or self.save_state, randbelow=SequenceRandom(outcome_roll), clock=lambda: "2026-07-14T00:00:00Z")

    # Prove identical purchase retries debit exactly once and preserve hidden prizes.
    def test_purchase_retry_reuses_one_masked_card_and_debit(self):
        # Build a deterministic winning-card service.
        service = self.service(99)
        # Define one complete purchase action.
        request = {"client_request_id": "purchase-1", "wager": 2}
        # Execute the original ledger-backed purchase.
        first = service.start_card("player-a", request)
        # Repeat the exact same network action.
        second = service.start_card("player-a", request)
        # Verify both responses preserve one card identity.
        self.assertEqual(first["card"]["card_id"], second["card"]["card_id"])
        # Verify the second response identifies the safe replay.
        self.assertTrue(second["replayed"])
        # Verify exactly one wager event exists.
        self.assertEqual(1, len(self.ledger.events))
        # Verify no covered public cell exposes a prize value.
        self.assertTrue(all("prize" not in cell for cell in first["card"]["cells"]))
        # Verify the action response redacts internal ledger details and fingerprints.
        self.assertNotIn("details", first["ledger"]["wager"])
        # Read the underlying player-visible ledger record for covered-value privacy.
        wager_details = next(iter(self.ledger.events.values()))["details"]
        # Verify no selected outcome or covered prize value is persisted in ledger details.
        self.assertFalse({"outcome_roll", "winning_multiplier", "prize_multipliers", "prizes", "payout"} & wager_details.keys())

    # Prove one purchase identity cannot represent a changed wager.
    def test_conflicting_purchase_identity_fails_closed(self):
        # Start one funded card under a stable request identity.
        service = self.service(0)
        # Commit the original one-token meaning.
        service.start_card("player-a", {"client_request_id": "same", "wager": 1})
        # Reject a different wager under the same identity.
        with self.assertRaises(ConflictError):
            # Exercise semantic request fingerprint enforcement.
            service.start_card("player-a", {"client_request_id": "same", "wager": 2})

    # Prove partial scratching survives a new service instance without leaking other cells.
    def test_partial_scratch_is_reload_safe_and_masked(self):
        # Start a deterministic winning card.
        service = self.service(99)
        # Fund the card and capture its stable identity.
        started = service.start_card("player-a", {"client_request_id": "partial", "wager": 1})
        # Reveal exactly one server-owned cell.
        partial = service.scratch("player-a", started["card"]["card_id"], {"action_id": "scratch-one", "positions": [4]})
        # Verify exactly one prize became public.
        self.assertEqual([4], [cell["position"] for cell in partial["card"]["cells"] if "prize" in cell])
        # Build a new service instance over the same persisted store.
        reloaded = self.service(0)
        # Read state through the reload-safe public endpoint helper.
        restored = reloaded.state("player-a")
        # Verify the same one-cell reveal and card identity survived reload.
        self.assertEqual(partial["card"], restored["current_card"])

    # Prove final reveal credits a winning prize at most once.
    def test_final_reveal_and_retry_issue_one_payout_credit(self):
        # Start a deterministic twenty-five-times winning card.
        service = self.service(99)
        # Fund the card with two play tokens.
        started = service.start_card("player-a", {"client_request_id": "winner", "wager": 2})
        # Reveal all nine positions under one retry identity.
        request = {"action_id": "reveal-all", "positions": list(range(engine.CELL_COUNT))}
        # Complete and settle the original action.
        first = service.scratch("player-a", started["card"]["card_id"], request)
        # Repeat the same reveal after settlement.
        second = service.scratch("player-a", started["card"]["card_id"], request)
        # Verify the matched prize is fifty play tokens.
        self.assertEqual(50.0, first["card"]["payout"])
        # Verify every prize is now authorized publicly.
        self.assertTrue(all("prize" in cell for cell in first["card"]["cells"]))
        # Verify purchase plus payout are the only ledger events.
        self.assertEqual(2, len(self.ledger.events))
        # Verify the repeated action is explicitly replayed.
        self.assertTrue(second["replayed"])

    # Prove a losing final reveal never attempts an invalid zero-value credit.
    def test_losing_card_creates_no_zero_payout_event(self):
        # Start a deterministic losing card.
        service = self.service(0)
        # Fund the card with one play token.
        started = service.start_card("player-a", {"client_request_id": "loser", "wager": 1})
        # Reveal the complete losing board.
        settled = service.scratch("player-a", started["card"]["card_id"], {"action_id": "lose-all", "positions": list(range(engine.CELL_COUNT))})
        # Verify the public terminal result is a no-win outcome.
        self.assertEqual(("no_win", 0.0), (settled["card"]["outcome"], settled["card"]["payout"]))
        # Verify only the wager debit exists in the ledger fake.
        self.assertEqual(1, len(self.ledger.events))

    # Prove a post-debit crash recovers persisted private state without ledger leakage or rerolling.
    def test_post_debit_crash_recovers_original_ticket(self):
        # Count saver calls so the funded-state save can fail after intent persistence.
        save_calls = {"count": 0}
        # Define a saver that persists intent then crashes before ready-state persistence.
        def crash_after_debit(player_id, state):
            # Advance the deterministic save boundary.
            save_calls["count"] += 1
            # Raise on the post-ledger ready-state save.
            if save_calls["count"] == 2:
                # Simulate process loss after the atomic debit event.
                raise RuntimeError("simulated post-debit crash")
            # Persist every earlier state transition normally.
            self.save_state(player_id, state)
        # Start a highest-tier winning ticket through the crash saver.
        crashing = self.service(99, state_saver=crash_after_debit)
        # Observe the simulated failure after one committed debit.
        with self.assertRaises(RuntimeError):
            # Execute the interrupted purchase.
            crashing.start_card("player-a", {"client_request_id": "crash-buy", "wager": 1})
        # Capture the private board that was durably stored before the wager debit.
        persisted_prizes = copy.deepcopy(self.states["player-a"]["current_card"]["prizes"])
        # Read the player-visible wager details emitted by the ledger fake.
        wager_details = next(iter(self.ledger.events.values()))["details"]
        # Verify the wager event cannot disclose covered cells or the preselected outcome.
        self.assertFalse({"outcome_roll", "winning_multiplier", "prize_multipliers", "prizes", "payout"} & wager_details.keys())
        # Reload through the public state boundary like a newly mounted browser route.
        recovery_state = self.service(0).state("player-a")
        # Verify the pending purchase publishes only its bounded retry identity and masked cells.
        self.assertEqual(("purchasing", "crash-buy"), (recovery_state["current_card"]["status"], recovery_state["current_card"]["pending_client_request_id"]))
        # Retry with the public recovery identity and an entropy source that would otherwise choose a loss.
        recovered = self.service(0).start_card("player-a", {"client_request_id": recovery_state["current_card"]["pending_client_request_id"], "wager": recovery_state["current_card"]["wager"]})
        # Verify no second debit was created.
        self.assertEqual(1, len(self.ledger.events))
        # Verify the pre-debit private state recovered the original board.
        self.assertEqual(persisted_prizes, self.states["player-a"]["current_card"]["prizes"])
        # Verify the recovered public card remains fully masked.
        self.assertTrue(all("prize" not in cell for cell in recovered["card"]["cells"]))

    # Prove a crash before the debit can be resumed after a full public-state reload.
    def test_pre_debit_crash_publishes_exact_purchase_retry(self):
        # Define a gateway that interrupts the action after intent persistence but before a commit.
        class PreDebitCrashGateway:
            # Raise a process-like interruption without creating any ledger event.
            def apply_once(self, **_kwargs):
                # Simulate loss of the request worker before the shared ledger transaction.
                raise RuntimeError("simulated pre-debit crash")
        # Build a crashing service over normal persisted game state.
        crashing = ScratchCardsService(ledger_gateway=PreDebitCrashGateway(), state_loader=self.load_state, state_saver=self.save_state, randbelow=SequenceRandom(99), clock=lambda: "2026-07-14T00:00:00Z")
        # Observe the interrupted purchase after its private intent was saved.
        with self.assertRaises(RuntimeError):
            # Start one stable five-token purchase identity.
            crashing.start_card("player-a", {"client_request_id": "pre-debit", "wager": 5})
        # Load only public state through a fresh service instance.
        restored = self.service(0).state("player-a")["current_card"]
        # Verify reload recovery has the exact public identity and wager but no covered values.
        self.assertEqual(("purchasing", "pre-debit", 5.0), (restored["status"], restored["pending_client_request_id"], restored["wager"]))
        # Resume using only fields available to the reloaded browser.
        recovered = self.service(0).start_card("player-a", {"client_request_id": restored["pending_client_request_id"], "wager": restored["wager"]})
        # Verify one debit funds the originally persisted masked card.
        self.assertEqual(("ready", 1), (recovered["card"]["status"], len(self.ledger.events)))

    # Prove a post-credit crash resumes settlement without a duplicate payout.
    def test_post_credit_crash_recovers_one_payout(self):
        # Start and persist a deterministic winning card normally.
        service = self.service(99)
        # Fund the card before installing the settlement crash saver.
        started = service.start_card("player-a", {"client_request_id": "credit-crash", "wager": 1})
        # Count only saves made by the reveal action.
        reveal_saves = {"count": 0}
        # Persist the settlement intent but crash before terminal state persistence.
        def crash_after_credit(player_id, state):
            # Advance the reveal save boundary.
            reveal_saves["count"] += 1
            # Raise on the second reveal save after the payout event exists.
            if reveal_saves["count"] == 2:
                # Simulate process loss after atomic credit.
                raise RuntimeError("simulated post-credit crash")
            # Persist the pre-credit settlement intent normally.
            self.save_state(player_id, state)
        # Build a service over the same state and ledger with the crash saver.
        crashing = self.service(0, state_saver=crash_after_credit)
        # Define one complete reveal retry identity.
        request = {"action_id": "credit-resume", "positions": list(range(engine.CELL_COUNT))}
        # Observe the simulated failure after payout commit.
        with self.assertRaises(RuntimeError):
            # Execute the interrupted final reveal.
            crashing.scratch("player-a", started["card"]["card_id"], request)
        # Verify purchase and payout are already the only committed events.
        self.assertEqual(2, len(self.ledger.events))
        # Resume through a fresh service instance with normal persistence.
        recovered = self.service(0).scratch("player-a", started["card"]["card_id"], request)
        # Verify no duplicate payout event was added.
        self.assertEqual(2, len(self.ledger.events))
        # Verify the recovered card is terminal and reports replay.
        self.assertEqual("settled", recovered["card"]["status"])
        # Verify the financial replay is visible to callers.
        self.assertTrue(recovered["replayed"])

    # Prove insufficient funds removes a prepared but non-funded ticket.
    def test_insufficient_funds_leaves_no_phantom_card(self):
        # Reject the next debit before an event can commit.
        self.ledger.reject_debits = True
        # Build one deterministic service over the rejecting ledger.
        service = self.service(99)
        # Observe the canonical insufficient-funds error.
        with self.assertRaises(InsufficientFundsError):
            # Attempt to start an unfunded card.
            service.start_card("player-a", {"client_request_id": "no-funds", "wager": 10})
        # Verify the rollback restored an empty current-card slot.
        self.assertIsNone(self.states["player-a"]["current_card"])
        # Verify no ledger event exists.
        self.assertEqual({}, self.ledger.events)

    # Prove action conflicts and cross-player lookups fail closed.
    def test_action_conflict_and_cross_player_privacy(self):
        # Start a deterministic card for player A only.
        service = self.service(0)
        # Fund and capture player A's stable card id.
        started = service.start_card("player-a", {"client_request_id": "private", "wager": 1})
        # Persist one partial scratch action identity.
        service.scratch("player-a", started["card"]["card_id"], {"action_id": "same-scratch", "positions": [0]})
        # Reject a new identity that attempts only an already revealed position.
        with self.assertRaises(ConflictError):
            # Prevent no-op flooding from evicting immutable action fingerprints.
            service.scratch("player-a", started["card"]["card_id"], {"action_id": "no-op-scratch", "positions": [0]})
        # Reject changed positions under the same action identity.
        with self.assertRaises(ConflictError):
            # Exercise state-level action fingerprint enforcement.
            service.scratch("player-a", started["card"]["card_id"], {"action_id": "same-scratch", "positions": [1]})
        # Return the same not-found shape when player B guesses player A's digest.
        with self.assertRaises(NotFoundError):
            # Exercise player-scoped card lookup isolation.
            service.scratch("player-b", started["card"]["card_id"], {"action_id": "guess", "positions": [0]})

    # Prove an evicted private card cannot be replaced by a free rerolled replay.
    def test_expired_purchase_retry_fails_closed_after_history_eviction(self):
        # Build a deterministic losing service so each completed card creates only one debit.
        service = self.service(0)
        # Start and settle the purchase whose state record will age out.
        original = service.start_card("player-a", {"client_request_id": "expired", "wager": 1})
        # Reveal the original card completely before later cards archive it.
        service.scratch("player-a", original["card"]["card_id"], {"action_id": "settle-expired", "positions": list(range(engine.CELL_COUNT))})
        # Create enough later terminal cards to evict the original private record.
        for index in range(engine.HISTORY_LIMIT + 1):
            # Start one later card under a unique immutable identity.
            later = service.start_card("player-a", {"client_request_id": f"later-{index}", "wager": 1})
            # Settle the later losing card so the next purchase can archive it.
            service.scratch("player-a", later["card"]["card_id"], {"action_id": f"settle-later-{index}", "positions": list(range(engine.CELL_COUNT))})
        # Capture state and ledger count before retrying the no-longer-retained identity.
        before_state = copy.deepcopy(self.states["player-a"])
        # Count one wager event per completed losing card.
        before_events = len(self.ledger.events)
        # Reject an entropy-changing replay whose original private board is no longer retained.
        with self.assertRaises(ConflictError):
            # Exercise ledger-level replay detection after bounded state eviction.
            self.service(99).start_card("player-a", {"client_request_id": "expired", "wager": 1})
        # Verify no substitute board or financial event survived the failed replay.
        self.assertEqual((before_state, before_events), (self.states["player-a"], len(self.ledger.events)))
        # Reject a changed-wager reuse through the ledger's immutable semantic checks.
        with self.assertRaises(ConflictError):
            # Exercise rollback when the production-like gateway raises before returning replay evidence.
            self.service(99).start_card("player-a", {"client_request_id": "expired", "wager": 2})
        # Verify the conflicting late retry also leaves state and ledger unchanged.
        self.assertEqual((before_state, before_events), (self.states["player-a"], len(self.ledger.events)))


# Run this focused suite directly without central runner registration.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
