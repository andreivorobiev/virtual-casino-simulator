"""Focused deterministic engine and ledger-recovery tests for issue #89."""

# Import the dependency-free standard test runner.
import unittest

# Import the public conflict and validation errors asserted at game boundaries.
from casino.errors import ConflictError, ValidationError
# Import the isolated pure engine under test.
from casino.games.chuck_a_luck import engine
# Import the isolated service orchestrator under test.
from casino.games.chuck_a_luck.service import ChuckALuckService


# Provide an in-memory apply-once ledger with production-shaped evidence.
class FakeLedgerGateway:
    # Initialize committed events and call evidence.
    def __init__(self):
        # Store events by their deterministic action key.
        self.events = {}
        # Store every apply-once invocation, including safe replays.
        self.calls = []

    # Commit or recover one signed game action.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Record the public action request for debit and credit count assertions.
        self.calls.append({"player_id": player_id, "amount": amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "request_fingerprint": request_fingerprint, "details": details})
        # Return the original event when this deterministic action already committed.
        if action_key in self.events:
            # Preserve the same event identity and report replay recovery.
            return self.events[action_key], True
        # Build one production-shaped ledger event with complete audit dimensions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "game": "chuck_a_luck", "round_id": round_id, "transaction_type": transaction_type, "amount": amount, "ts": "2026-07-14T18:00:00Z", "details": {**details, "idempotency_key": action_key, "request_fingerprint": request_fingerprint}}
        # Persist the committed event under its unique action identity.
        self.events[action_key] = event
        # Report that this call created the event.
        return event, False

    # Find one committed event through every immutable proof dimension.
    def find(self, *, player_id, round_id, transaction_type, action_key, request_fingerprint):
        # Read the event addressed by the deterministic action key.
        event = self.events.get(action_key)
        # Return no proof when this action never committed.
        if event is None:
            # Preserve the production gateway's optional-result contract.
            return None
        # Require the fake event to match player, round, transaction, and request meaning.
        if event["player_id"] != player_id or event["round_id"] != round_id or event["transaction_type"] != transaction_type or event["details"]["request_fingerprint"] != request_fingerprint:
            # Surface a conflict instead of satisfying proof with unrelated fake data.
            raise ConflictError("Fake ledger proof dimensions conflict")
        # Return the original committed event.
        return event


# Verify pure rules, deterministic dice, and payout calculations.
class ChuckALuckEngineTests(unittest.TestCase):
    # Confirm injected zero-based samples produce one stable bounded roll.
    def test_dice_roll_is_deterministic_and_bounded(self):
        # Supply the exact three zero-based die selections in order.
        selections = iter([0, 5, 2])
        # Roll through the production entropy adapter seam.
        dice = engine.roll_dice(lambda sides: next(selections))
        # Require the expected one-based faces without ambient randomness.
        self.assertEqual([1, 6, 3], dice)

    # Confirm one invalid entropy adapter fails before settlement.
    def test_dice_roll_rejects_invalid_entropy_result(self):
        # Reject the upper-exclusive boundary instead of wrapping or biasing it.
        with self.assertRaises(ValueError):
            # Supply six even though valid zero-based d6 selections end at five.
            engine.roll_dice(lambda sides: sides)

    # Confirm the documented 1/2/3-match profile settles multiple number bets exactly.
    def test_settlement_uses_match_count_net_odds(self):
        # Normalize three distinct number wagers through the public validation seam.
        wagers = engine.normalize_wagers({"one": 2, "two": 3, "four": 1})
        # Settle two ones, one two, and no fours deterministically.
        result = engine.settle(wagers, [1, 1, 2])
        # Require one aggregate wager debit amount.
        self.assertEqual(6.0, result["total_wager"])
        # Require returned stakes plus net winnings for both matching numbers.
        self.assertEqual(12.0, result["total_return"])
        # Require aggregate net play-token change after all covered numbers.
        self.assertEqual(6.0, result["net"])
        # Index settlement rows by stable number id for exact assertions.
        rows = {row["target"]: row for row in result["settlements"]}
        # Require two matches to pay 2-to-1 net and return three times the stake.
        self.assertEqual((2, 2, 6.0), (rows["one"]["matches"], rows["one"]["net_multiplier"], rows["one"]["return_amount"]))
        # Require one match to pay 1-to-1 net and return twice the stake.
        self.assertEqual((1, 1, 6.0), (rows["two"]["matches"], rows["two"]["net_multiplier"], rows["two"]["return_amount"]))
        # Require a missing number to lose only its own stake.
        self.assertEqual((False, -1.0), (rows["four"]["won"], rows["four"]["net"]))

    # Confirm a triple uses the selected 3-to-1 net profile rather than a hidden side bet.
    def test_triple_number_bet_pays_three_to_one_net(self):
        # Settle one two-token wager against three matching sixes.
        result = engine.settle(engine.normalize_wagers({"six": 2}), [6, 6, 6])
        # Require triple context and a stake-plus-six-token return.
        self.assertEqual((True, 18, 8.0, 6.0), (result["is_triple"], result["total"], result["total_return"], result["net"]))

    # Confirm canonical wager normalization makes semantically equal retries identical.
    def test_wager_fingerprint_is_order_stable(self):
        # Normalize the first key order and integer amount spellings.
        first = engine.normalize_wagers({"two": 2, "one": 1})
        # Normalize the reverse key order and floating amount spellings.
        second = engine.normalize_wagers({"one": 1.0, "two": 2.0})
        # Require both normalized maps and fingerprints to match exactly.
        self.assertEqual((first, engine.wager_fingerprint(first)), (second, engine.wager_fingerprint(second)))

    # Confirm invalid number ids and nonpositive amounts fail before ledger access.
    def test_wager_validation_rejects_unknown_and_nonpositive_values(self):
        # Reject an unsupported layout number key.
        with self.assertRaises(ValidationError):
            # Exercise the unknown-key boundary.
            engine.normalize_wagers({"seven": 1})
        # Reject zero because it cannot represent a ledger wager.
        with self.assertRaises(ValidationError):
            # Exercise the minimum play-token boundary.
            engine.normalize_wagers({"one": 0})

    # Confirm retry round identity is stable per authenticated player without leaking request text.
    def test_round_id_is_stable_and_player_scoped(self):
        # Derive the same authenticated action twice.
        first = engine.round_id_for("player-a", "request-17")
        # Repeat the derivation with identical ownership dimensions.
        second = engine.round_id_for("player-a", "request-17")
        # Require stable replay identity.
        self.assertEqual(first, second)
        # Require another authenticated player to receive a distinct identity.
        self.assertNotEqual(first, engine.round_id_for("player-b", "request-17"))
        # Require the free-form client key not to appear in the persisted round id.
        self.assertNotIn("request", first)


# Verify ledger-only idempotency and crash recovery through isolated seams.
class ChuckALuckServiceTests(unittest.TestCase):
    # Build one deterministic player-scoped service before every test.
    def setUp(self):
        # Store isolated state documents by authenticated player id.
        self.states = {}
        # Create one apply-once in-memory ledger.
        self.ledger = FakeLedgerGateway()
        # Roll three ones so normal service assertions have a deterministic triple return.
        self.service = ChuckALuckService(ledger_gateway=self.ledger, state_loader=lambda player_id: self.states.setdefault(player_id, engine.default_state()), state_saver=lambda player_id, state: self.states.__setitem__(player_id, state), randbelow=lambda sides: 0, clock=lambda: "2026-07-14T18:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})

    # Confirm an identical retry returns one debit and at most one credit.
    def test_identical_retry_reuses_round_and_ledger_actions(self):
        # Define one stable aggregate wager action.
        request = {"request_id": "retry-1", "wagers": {"one": 2}}
        # Execute the original server-authoritative roll.
        first = self.service.roll("player-a", request)
        # Repeat the exact same player action identity.
        second = self.service.roll("player-a", request)
        # Require one immutable settled round across both calls.
        self.assertEqual(first["round"], second["round"])
        # Require the state-cache response to identify replay recovery.
        self.assertTrue(second["replayed"])
        # Require exactly one committed debit and one committed settlement credit.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm a post-debit crash retry recovers committed dice instead of rerolling.
    def test_post_debit_retry_recovers_committed_dice(self):
        # Define the original retry-safe public request.
        request = {"request_id": "crash-1", "wagers": {"two": 2}}
        # Normalize and fingerprint the original wager before precommitting its debit.
        wagers = engine.normalize_wagers(request["wagers"])
        # Derive the deterministic player-scoped round identity.
        round_id = engine.round_id_for("player-a", request["request_id"])
        # Commit only the wager with its original two-two-three result.
        self.ledger.apply_once(player_id="player-a", amount=-2.0, transaction_type="CHUCK_A_LUCK_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", request_fingerprint=engine.wager_fingerprint(wagers), details={"request_id": request["request_id"], "wagers": wagers, "dice": [2, 2, 3]})
        # Build a recovery service whose fresh entropy would otherwise roll three sixes.
        recovering = ChuckALuckService(ledger_gateway=self.ledger, state_loader=lambda player_id: self.states.setdefault(player_id, engine.default_state()), state_saver=lambda player_id, state: self.states.__setitem__(player_id, state), randbelow=lambda sides: 5, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
        # Resume the interrupted request through the public service action.
        result = recovering.roll("player-a", request)
        # Require the originally committed dice and payout to survive recovery.
        self.assertEqual(([2, 2, 3], 6.0), (result["round"]["dice"], result["round"]["total_return"]))
        # Require only one debit and one settlement identity after recovery.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm a post-credit crash retry does not duplicate the already committed payout.
    def test_post_credit_retry_reuses_both_ledger_events(self):
        # Define one triple-winning public request.
        request = {"request_id": "credit-crash", "wagers": {"one": 1}}
        # Normalize the wager and stable request proof.
        wagers = engine.normalize_wagers(request["wagers"])
        # Calculate its deterministic round and fingerprint.
        round_id = engine.round_id_for("player-a", request["request_id"])
        # Store the shared fingerprint once for both action details.
        fingerprint = engine.wager_fingerprint(wagers)
        # Precommit the original triple-one wager debit.
        self.ledger.apply_once(player_id="player-a", amount=-1.0, transaction_type="CHUCK_A_LUCK_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", request_fingerprint=fingerprint, details={"request_id": request["request_id"], "wagers": wagers, "dice": [1, 1, 1]})
        # Precommit the corresponding stake-plus-winnings credit.
        self.ledger.apply_once(player_id="player-a", amount=4.0, transaction_type="CHUCK_A_LUCK_SETTLEMENT_CREDIT", round_id=round_id, action_key=f"{round_id}:settlement", request_fingerprint=fingerprint, details={"request_id": request["request_id"], "dice": [1, 1, 1], "settlements": []})
        # Recover the missing state write through the normal service call.
        result = self.service.roll("player-a", request)
        # Require replay evidence and no third committed ledger event.
        self.assertTrue(result["replayed"])
        # Require the two original action identities to remain the complete ledger set.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm a losing number wager creates no forbidden zero-value payout row.
    def test_losing_roll_creates_only_wager_debit(self):
        # Build a service that deterministically rolls three sixes.
        losing = ChuckALuckService(ledger_gateway=self.ledger, state_loader=lambda player_id: self.states.setdefault(player_id, engine.default_state()), state_saver=lambda player_id, state: self.states.__setitem__(player_id, state), randbelow=lambda sides: 5, clock=lambda: "2026-07-14T18:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
        # Wager only on one so the result has no return.
        result = losing.roll("player-a", {"request_id": "loss-1", "wagers": {"one": 1}})
        # Require a zero return and absent settlement credit evidence.
        self.assertEqual((0.0, None), (result["round"]["total_return"], result["ledger"]["settlement"]))
        # Require only the aggregate wager debit to exist.
        self.assertEqual(1, len(self.ledger.events))

    # Confirm one request identity cannot represent different wager content.
    def test_conflicting_request_payload_fails_closed(self):
        # Commit the first meaning of this request identity.
        self.service.roll("player-a", {"request_id": "same-id", "wagers": {"one": 1}})
        # Reject a different number wager under the committed identity.
        with self.assertRaises(ConflictError):
            # Exercise the semantic fingerprint boundary.
            self.service.roll("player-a", {"request_id": "same-id", "wagers": {"two": 1}})

    # Confirm state and response history remain isolated by authenticated player.
    def test_player_state_isolation(self):
        # Settle one round for the first authenticated player.
        self.service.roll("player-a", {"request_id": "isolated", "wagers": {"one": 1}})
        # Read the untouched state for another authenticated player.
        other = self.service.state("player-b")
        # Require no cross-player round history in the second response.
        self.assertEqual([], other["state"]["recent_rounds"])


# Run the focused suite directly without central runner edits.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
