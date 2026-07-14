"""Focused Dragon Tiger session, persistence, and ledger-replay tests."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import a bounded thread pool for duplicate-request serialization coverage.
from concurrent.futures import ThreadPoolExecutor
# Import standard unit-test support.
import unittest

# Import shared cards for valid deterministic shoe fixtures.
from casino.core.cards import create_deck
# Import insufficient-funds behavior used by the shared ledger boundary.
from casino.errors import ConflictError, InsufficientFundsError, ValidationError
# Import the isolated router used by focused registration tests.
from casino.router import Router
# Import Dragon Tiger routes, engine, and service under test.
from casino.games.dragon_tiger import api, engine
# Import service orchestration separately for injected-port tests.
from casino.games.dragon_tiger.service import DragonTigerService


# Build a complete standard-8d fixture with controlled deal cards.
def rigged_shoe(dragon_card="KS", tiger_card="QH"):
    # Start with exactly eight standard decks.
    cards = [card.code for card in create_deck(engine.DECK_COUNT)]
    # Control burns followed by Dragon-first and Tiger-second cards.
    pop_order = ["2C", "3D", "4H", dragon_card, tiger_card]
    # Relocate one occurrence of each controlled card.
    for card in pop_order:
        # Preserve the exact eight-deck multiset.
        cards.remove(card)
    # Reverse the controlled tail for stack-pop order.
    cards.extend(reversed(pop_order))
    # Return the complete valid shoe.
    return cards


# Provide deep-copy player state with injectable save failures.
class MemoryRepository:
    # Initialize empty player documents and failure controls.
    def __init__(self):
        # Store committed state by authenticated player.
        self.states = {}
        # Count attempted saves for crash seam selection.
        self.save_count = 0
        # Fail selected save numbers once.
        self.fail_on = set()

    # Load a detached player document.
    def load(self, player_id):
        # Return committed state or a new default.
        return copy.deepcopy(self.states.get(player_id, engine.default_state()))

    # Save a detached player document or simulate interruption.
    def save(self, player_id, state):
        # Advance the deterministic save counter.
        self.save_count += 1
        # Simulate one configured provider interruption.
        if self.save_count in self.fail_on:
            # Consume the one-shot failure.
            self.fail_on.remove(self.save_count)
            # Raise after prior ledger work can already be durable.
            raise RuntimeError("simulated state save failure")
        # Persist a detached copy like JSON storage.
        self.states[player_id] = copy.deepcopy(state)


# Provide append-only apply-once ledger behavior without real balances/files.
class MemoryLedger:
    # Initialize fake balances and event history.
    def __init__(self):
        # Start the focused player with ample tokens.
        self.balances = {"session-player": 1000.0}
        # Retain committed events chronologically.
        self.events = []
        # Fail selected movements after mutating balance but before appending evidence.
        self.fail_without_event = set()

    # Find one stable action event.
    def find(self, player_id, action_key):
        # Search newest-first within the requested player's events.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"].get("idempotency_key") == action_key), None)

    # Validate replay compatibility like the production gateway.
    def validate_existing(self, event, *, amount, transaction_type, round_id, fingerprint):
        # Reject any differing amount, type, round, game, or fingerprint.
        if round(event["amount"], 2) != round(amount, 2) or event["transaction_type"] != transaction_type or event["round_id"] != round_id or event["game"] != engine.GAME_ID or event["details"].get("request_fingerprint") != fingerprint:
            # Match the production fail-closed conflict class.
            raise ConflictError("fake ledger conflict")

    # Commit or replay one signed movement.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, fingerprint, details):
        # Resolve a prior stable action first.
        existing = self.find(player_id, action_key)
        # Replay only compatible proof.
        if existing:
            # Validate semantic identity.
            self.validate_existing(existing, amount=amount, transaction_type=transaction_type, round_id=round_id, fingerprint=fingerprint)
            # Return original proof and replay status.
            return existing, True
        # Calculate the resulting balance.
        after = round(self.balances[player_id] + amount, 2)
        # Reject overdrafts like shared ledger storage.
        if after < 0:
            # Surface the shared insufficient-funds error.
            raise InsufficientFundsError()
        # Build the public ledger subset used by service recovery.
        event = {"ledger_id": f"led-{len(self.events) + 1}", "ts": "2026-07-14T00:00:00Z", "player_id": player_id, "game": engine.GAME_ID, "round_id": round_id, "transaction_type": transaction_type, "amount": amount, "details": {**details, "idempotency_key": action_key, "request_fingerprint": fingerprint}}
        # Commit the fake balance.
        self.balances[player_id] = after
        # Simulate the shared JSON provider's balance-before-event failure gap.
        if action_key in self.fail_without_event:
            # Consume the one-shot ambiguous failure.
            self.fail_without_event.remove(action_key)
            # Raise without append-only proof after the balance already changed.
            raise RuntimeError("simulated balance/event gap")
        # Append immutable-by-convention proof.
        self.events.append(event)
        # Return new proof and non-replay status.
        return event, False


# Verify session-bound exactly-once service behavior.
class DragonTigerServiceTests(unittest.TestCase):
    # Build fresh deterministic ports before each test.
    def setUp(self):
        # Create isolated persistent state.
        self.repository = MemoryRepository()
        # Create isolated append-only ledger state.
        self.ledger = MemoryLedger()
        # Construct the service with fixed cards and time.
        self.service = DragonTigerService(repository=self.repository, ledger_gateway=self.ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, shoe_factory=lambda: rigged_shoe(), clock=lambda: "2026-07-14T00:00:00Z")

    # Confirm exact retries do not deal or move balances twice.
    def test_exact_retry_replays_one_debit_and_credit(self):
        # Execute one deterministic Dragon win.
        first = self.service.play("session-player", {"action_id": "action-001", "bet": "dragon", "wager": 10})
        # Replay identical normalized input.
        second = self.service.play("session-player", {"action_id": "action-001", "bet": "dragon", "wager": 10})
        # Verify the same public round is returned.
        self.assertEqual(first["round"], second["round"])
        # Verify the duplicate is reported as replayed.
        self.assertTrue(second["replayed"])
        # Verify one wager and one settlement event exist.
        self.assertEqual(["DRAGON_TIGER_WAGER_DEBIT", "DRAGON_TIGER_SETTLEMENT_CREDIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify the net 1:1 result changed balance by ten.
        self.assertEqual(1010.0, self.ledger.balances["session-player"])

    # Confirm service response keys remain aligned with the game-owned OpenAPI schemas.
    def test_round_response_shape_matches_contract(self):
        # Execute one complete deterministic round.
        result = self.service.play("session-player", {"action_id": "action-shape", "bet": "dragon", "wager": 5})
        # Require exactly the documented round-response data fields.
        self.assertEqual({"game", "state", "player", "rules", "round", "ledger", "replayed"}, set(result))
        # Require exactly the documented public state fields.
        self.assertEqual({"shoe", "recent_rounds"}, set(result["state"]))
        # Require exactly the documented private-shoe summary fields.
        self.assertEqual({"shoe_number", "cards_remaining", "shuffle_pending"}, set(result["state"]["shoe"]))
        # Require exactly the documented immutable rules fields.
        self.assertEqual({"profile", "deck_count", "burn_count", "cut_cards", "bets"}, set(result["rules"]))
        # Require exactly the documented settled-round fields.
        self.assertEqual({"round_id", "action_id", "player_id", "status", "bet", "wager", "dragon_card", "tiger_card", "winner", "outcome", "total_return", "net", "settled_at", "shoe_number"}, set(result["round"]))
        # Verify returned state already contains the same settled round once.
        self.assertEqual([result["round"]], result["state"]["recent_rounds"])

    # Confirm simultaneous duplicate requests share one atomic ledger result.
    def test_concurrent_duplicate_replays_one_debit_and_credit(self):
        # Build the identical retry-safe request for both workers.
        request = {"action_id": "action-concurrent", "bet": "dragon", "wager": 10}
        # Run two callers against the process-local action boundary.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Collect both terminal responses after the duplicate race.
            results = list(executor.map(lambda _index: self.service.play("session-player", request), range(2)))
        # Verify one caller committed and the other replayed.
        self.assertEqual([False, True], sorted(result["replayed"] for result in results))
        # Verify both callers received the identical public round.
        self.assertEqual(results[0]["round"], results[1]["round"])
        # Verify concurrency still produced exactly one debit and one credit.
        self.assertEqual(2, len(self.ledger.events))
        # Verify the player received only one net win.
        self.assertEqual(1010.0, self.ledger.balances["session-player"])

    # Confirm idempotency and chronology survive beyond visible-history retention.
    def test_delayed_replay_uses_durable_action_index_without_reordering_history(self):
        # Execute one more action than the visible recent-round limit.
        for index in range(engine.RECENT_ROUND_LIMIT + 1):
            # Use a stable unique identity for every settled round.
            self.service.play("session-player", {"action_id": f"action-history-{index:03d}", "bet": "dragon", "wager": 1})
        # Snapshot the bounded chronology before replaying the evicted first round.
        recent_before = copy.deepcopy(self.repository.load("session-player")["recent_rounds"])
        # Remove the old action's provider events to prove replay no longer depends on a scan horizon.
        old_round_id = engine.round_id_for("session-player", "action-history-000")
        # Retain only unrelated fake ledger rows.
        self.ledger.events = [event for event in self.ledger.events if event["round_id"] != old_round_id]
        # Snapshot balance and surviving event count before delayed replay.
        before = (self.ledger.balances["session-player"], len(self.ledger.events))
        # Replay the first action after it has left visible history and provider evidence.
        replay = self.service.play("session-player", {"action_id": "action-history-000", "bet": "dragon", "wager": 1})
        # Verify durable state still returns the original action safely.
        self.assertTrue(replay["replayed"])
        # Verify the old action did not become the newest visible round.
        self.assertEqual(recent_before, self.repository.load("session-player")["recent_rounds"])
        # Verify delayed replay made no wallet movement or new ledger event.
        self.assertEqual(before, (self.ledger.balances["session-player"], len(self.ledger.events)))
        # Verify durable state retained original wager evidence for the response.
        self.assertEqual(old_round_id, replay["ledger"]["wager"]["round_id"])

    # Confirm one action identity cannot represent another bet.
    def test_conflicting_retry_fails_closed(self):
        # Commit one Dragon request.
        self.service.play("session-player", {"action_id": "action-002", "bet": "dragon", "wager": 2})
        # Reject the same action identity with Tiger input.
        with self.assertRaises(ConflictError):
            # Exercise semantic fingerprint conflict handling.
            self.service.play("session-player", {"action_id": "action-002", "bet": "tiger", "wager": 2})
        # Verify conflict did not add ledger events.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm retry recovers a debit committed before its marker save.
    def test_post_debit_save_failure_recovers_without_duplicate(self):
        # Fail the canonical prepared-state save after the debit.
        self.repository.fail_on.add(3)
        # Observe the simulated interruption.
        with self.assertRaises(RuntimeError):
            # Begin one winning round.
            self.service.play("session-player", {"action_id": "action-003", "bet": "dragon", "wager": 4})
        # Verify only the wager committed before the interruption.
        self.assertEqual(1, len(self.ledger.events))
        # Retry from persisted prepared cards and ledger proof.
        recovered = self.service.play("session-player", {"action_id": "action-003", "bet": "dragon", "wager": 4})
        # Verify recovery is explicit.
        self.assertTrue(recovered["replayed"])
        # Verify exactly one debit and one credit remain.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm retry recovers a credit committed before terminal state save.
    def test_post_credit_save_failure_recovers_without_duplicate(self):
        # Fail the terminal save after wager and settlement proof.
        self.repository.fail_on.add(5)
        # Observe the simulated interruption.
        with self.assertRaises(RuntimeError):
            # Begin one winning round.
            self.service.play("session-player", {"action_id": "action-004", "bet": "dragon", "wager": 6})
        # Verify both required movements committed once.
        self.assertEqual(2, len(self.ledger.events))
        # Retry from canonical prepared state and both ledger proofs.
        recovered = self.service.play("session-player", {"action_id": "action-004", "bet": "dragon", "wager": 6})
        # Verify recovery is explicit.
        self.assertTrue(recovered["replayed"])
        # Verify no third ledger event was created.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm losing rounds create no zero-value settlement credit.
    def test_loss_uses_one_debit_and_no_credit(self):
        # Bet Tiger against the deterministic Dragon-winning cards.
        result = self.service.play("session-player", {"action_id": "action-005", "bet": "tiger", "wager": 3})
        # Verify the public loss classification.
        self.assertEqual("loss", result["round"]["outcome"])
        # Verify only the wager event exists.
        self.assertEqual(1, len(self.ledger.events))
        # Verify the settlement proof is explicitly absent.
        self.assertIsNone(result["ledger"]["settlement"])

    # Confirm rejected wagers restore the private shoe and prepared state.
    def test_insufficient_funds_rolls_back_uncommitted_action(self):
        # Lower the authenticated player's balance below the requested wager.
        self.ledger.balances["session-player"] = 1.0
        # Snapshot the state expected after a rejected debit.
        initial_state = engine.default_state()
        # Reject the wager at the shared ledger boundary.
        with self.assertRaises(InsufficientFundsError):
            # Attempt one otherwise valid deterministic action.
            self.service.play("session-player", {"action_id": "action-insufficient", "bet": "dragon", "wager": 2})
        # Verify no wallet movement survived the rejection.
        self.assertEqual([], self.ledger.events)
        # Verify the failed action did not consume shoe cards or persist a marker.
        self.assertEqual(initial_state, self.repository.load("session-player"))
        # Verify the unchanged wallet remains authoritative.
        self.assertEqual(1.0, self.ledger.balances["session-player"])

    # Confirm an ambiguous debit gap blocks retry instead of charging twice.
    def test_missing_wager_evidence_fails_closed_without_second_debit(self):
        # Derive the exact player-scoped wager action key.
        round_id = engine.round_id_for("session-player", "action-gap-wager")
        # Fail after balance mutation but before fake evidence append.
        self.ledger.fail_without_event.add(f"{round_id}:wager")
        # Observe the simulated shared-provider ambiguity.
        with self.assertRaises(RuntimeError):
            # Start one otherwise valid winning request.
            self.service.play("session-player", {"action_id": "action-gap-wager", "bet": "dragon", "wager": 10})
        # Verify the first hidden movement changed balance without evidence.
        self.assertEqual(990.0, self.ledger.balances["session-player"])
        # Verify no append-only event can prove the outcome.
        self.assertEqual([], self.ledger.events)
        # Verify the durable pre-movement marker survived for safe recovery.
        self.assertEqual("wager_attempting", self.repository.load("session-player")["prepared_actions"]["action-gap-wager"]["status"])
        # Fail closed rather than repeating the possibly completed debit.
        with self.assertRaises(ConflictError):
            # Retry the identical public action.
            self.service.play("session-player", {"action_id": "action-gap-wager", "bet": "dragon", "wager": 10})
        # Verify retry neither moved balance nor invented evidence.
        self.assertEqual((990.0, 0), (self.ledger.balances["session-player"], len(self.ledger.events)))

    # Confirm an ambiguous settlement gap blocks retry instead of crediting twice.
    def test_missing_settlement_evidence_fails_closed_without_second_credit(self):
        # Derive the exact player-scoped settlement action key.
        round_id = engine.round_id_for("session-player", "action-gap-credit")
        # Fail after crediting balance but before fake evidence append.
        self.ledger.fail_without_event.add(f"{round_id}:settlement")
        # Observe the simulated shared-provider ambiguity.
        with self.assertRaises(RuntimeError):
            # Start one deterministic Dragon win.
            self.service.play("session-player", {"action_id": "action-gap-credit", "bet": "dragon", "wager": 10})
        # Verify debit and hidden credit produced the correct one-round balance.
        self.assertEqual(1010.0, self.ledger.balances["session-player"])
        # Verify only the durable wager event exists.
        self.assertEqual(["DRAGON_TIGER_WAGER_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify the durable pre-credit marker survived for safe recovery.
        self.assertEqual("settlement_attempting", self.repository.load("session-player")["prepared_actions"]["action-gap-credit"]["status"])
        # Fail closed rather than repeating the possibly completed credit.
        with self.assertRaises(ConflictError):
            # Retry the identical public action.
            self.service.play("session-player", {"action_id": "action-gap-credit", "bet": "dragon", "wager": 10})
        # Verify retry neither moved balance nor appended another event.
        self.assertEqual((1010.0, 1), (self.ledger.balances["session-player"], len(self.ledger.events)))

    # Confirm runtime validation matches the strict additive OpenAPI request schema.
    def test_round_request_rejects_contract_drift(self):
        # Define malformed cases that older coercive parsing could have accepted.
        invalid_requests = [
            {"action_id": " action-007", "bet": "dragon", "wager": 1},  # Reject trimmed action identities.
            {"action_id": "action-007", "bet": "Dragon", "wager": 1},  # Reject non-enum bet casing.
            {"action_id": "action-007", "bet": "dragon", "wager": "1"},  # Reject numeric strings.
            {"action_id": "action-007", "bet": "dragon", "wager": 1.001},  # Reject non-cent precision.
            {"action_id": "action-007", "bet": "dragon", "wager": 1, "debug": True},  # Reject extra fields.
        ]
        # Verify every malformed contract shape fails before state or ledger mutation.
        for request in invalid_requests:
            # Identify each failing input independently.
            with self.subTest(request=request):
                # Require the shared public validation class.
                with self.assertRaises(ValidationError):
                    # Exercise the complete service boundary.
                    self.service.play("session-player", request)
        # Verify strict rejections never touched the wallet.
        self.assertEqual([], self.ledger.events)


# Provide a route fake that records resolved players.
class RecordingService:
    # Initialize recorded calls.
    def __init__(self):
        # Retain state player IDs.
        self.state_players = []
        # Retain play calls.
        self.play_calls = []

    # Record one state request.
    def state(self, player_id):
        # Store the resolved identity.
        self.state_players.append(player_id)
        # Return a minimal marker payload.
        return {"player_id": player_id}

    # Record one round request.
    def play(self, player_id, body):
        # Store resolved identity and body.
        self.play_calls.append((player_id, dict(body)))
        # Return a minimal marker payload.
        return {"player_id": player_id}


# Verify shared router session binding reaches game handlers.
class DragonTigerApiTests(unittest.TestCase):
    # Confirm hostile caller IDs cannot override authenticated ownership.
    def test_bound_player_overrides_body_and_query_ids(self):
        # Create a focused router and recording service.
        router = Router()
        # Register only Dragon Tiger routes.
        recording = RecordingService()
        # Attach injected route handlers.
        api.register(router, service=recording)
        # Build the authenticated request context.
        context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}
        # Dispatch a state request with a hostile query identity.
        router.dispatch("GET", "/api/v1/games/dragon-tiger/state?player_id=attacker", {}, context=dict(context))
        # Dispatch a round request with a hostile body identity.
        router.dispatch("POST", "/api/v1/games/dragon-tiger/rounds", {"player_id": "attacker", "action_id": "action-006", "bet": "dragon", "wager": 1}, context=dict(context))
        # Verify both handlers received only the bound player.
        self.assertEqual(["session-player"], recording.state_players)
        # Verify the action also received only the bound player.
        self.assertEqual("session-player", recording.play_calls[0][0])

    # Confirm authenticated Admin identity also overrides compatibility inputs.
    def test_admin_player_overrides_body_and_resolver_ids(self):
        # Create a focused router and recording service.
        router = Router()
        # Register only Dragon Tiger routes.
        recording = RecordingService()
        # Attach injected route handlers.
        api.register(router, service=recording)
        # Build an authenticated Admin-like context without a non-Admin binding.
        context = {"user": {"player_id": "admin-player", "role": "admin", "status": "active"}}
        # Dispatch a hostile body identity through the shared compatibility resolver.
        router.dispatch("POST", "/api/v1/games/dragon-tiger/rounds", {"player_id": "victim-player", "action_id": "action-admin", "bet": "dragon", "wager": 1}, context=dict(context))
        # Verify the game-local boundary restored the authenticated Admin's player.
        self.assertEqual("admin-player", recording.play_calls[0][0])


# Run this focused suite directly when requested.
if __name__ == "__main__":
    # Exit through standard unittest result handling.
    unittest.main()
