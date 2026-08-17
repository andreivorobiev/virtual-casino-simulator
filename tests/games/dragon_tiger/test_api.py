# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared-settlement, recovery, and frozen API tests for issue #871."""

# Import deep-copy support so fake persistence models JSON boundaries.
import copy
# Import a bounded thread pool for duplicate-request serialization coverage.
from concurrent.futures import ThreadPoolExecutor
# Import filesystem paths for structural source assertions.
from pathlib import Path
# Import standard unit-test support.
import unittest

# Import shared cards for valid deterministic shoe fixtures.
from casino.core.cards import create_deck
# Import public money and validation errors asserted at service boundaries.
from casino.errors import ConflictError, InsufficientFundsError, ValidationError
# Import Dragon Tiger routes, rules, and shared-backed service.
from casino.games.dragon_tiger import api, engine
# Import the service class explicitly for focused dependency injection.
from casino.games.dragon_tiger.service import DragonTigerService
# Import the isolated router used by frozen registration tests.
from casino.router import Router


# Build a complete standard-8d fixture with controlled deal cards.
def rigged_shoe(dragon_card="KS", tiger_card="QH"):
    # Start with exactly eight standard decks.
    cards = [card.code for card in create_deck(engine.DECK_COUNT)]
    # Control burns followed by Dragon-first and Tiger-second cards.
    pop_order = ["2C", "3D", "4H", dragon_card, tiger_card]
    # Relocate one occurrence of every controlled card.
    for card in pop_order:
        # Preserve the exact eight-deck multiset.
        cards.remove(card)
    # Reverse the controlled tail for stack-pop order.
    cards.extend(reversed(pop_order))
    # Return the complete valid shoe.
    return cards


# Simulate player-scoped state documents with provider-current callbacks.
class MemoryRepository:
    # Start with no persisted game documents.
    def __init__(self):
        # Store detached documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so every mutation requires an explicit provider callback.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Update one player document through the production-shaped callback seam.
    def update(self, player_id, mutator):
        # Load provider-current state inside the fake atomic boundary.
        current = copy.deepcopy(self.documents.get(player_id, engine.default_state()))
        # Apply one game-owned mutation against current authority.
        updated = mutator(current)
        # Persist detached bytes like JSON storage.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return detached provider authority.
        return copy.deepcopy(updated)


# Persist one selected provider transition and then simulate a lost response.
class PersistThenFailRepository(MemoryRepository):
    # Capture the exact state predicate for one crash boundary.
    def __init__(self, predicate):
        # Initialize ordinary detached provider storage first.
        super().__init__()
        # Retain the bounded state predicate supplied by the focused test.
        self._predicate = predicate
        # Arm exactly one post-persistence response failure.
        self._armed = True

    # Commit provider-current mutation before optionally losing its response.
    def update(self, player_id, mutator):
        # Persist through the ordinary fake provider boundary.
        authoritative = super().update(player_id, mutator)
        # Fail once only when the requested crash state is durable.
        if self._armed and self._predicate(authoritative):
            # Consume the one-shot fault before surfacing it.
            self._armed = False
            # Model a provider write whose response is lost after commit.
            raise RuntimeError("simulated lost provider response")
        # Return normal detached authority for every other transition.
        return authoritative


# Provide an in-memory apply-once gateway with production-shaped evidence.
class FakeLedgerGateway:
    # Initialize balances, immutable events, and failure controls.
    def __init__(self, balances=None):
        # Store deterministic fake wallets without shared player data.
        self.balances = balances or {"session-player": 1000.0, "other-player": 100.0, "player-a": 1000.0, "player-b": 100.0}
        # Store events by deterministic action key.
        self.events = {}
        # Retain every apply-once call, including safe replays.
        self.calls = []
        # Hold one-shot failures before immutable publication.
        self.fail_before = set()
        # Hold one-shot lost responses after immutable publication.
        self.fail_after = set()

    # Commit or recover one signed game action.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Record every helper-owned movement request for count assertions.
        self.calls.append({"player_id": player_id, "amount": amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "request_fingerprint": request_fingerprint, "details": copy.deepcopy(details)})
        # Resolve the bounded movement role once for failure injection.
        suffix = action_key.rsplit(":", 1)[-1]
        # Fail once before publication when the test arms this role.
        if suffix in self.fail_before:
            # Consume the one-shot failure so explicit retry may proceed.
            self.fail_before.remove(suffix)
            # Model a definitive provider rejection with no movement.
            raise RuntimeError("simulated pre-commit ledger failure")
        # Return original proof when this action already committed.
        if action_key in self.events:
            # Read immutable proof once for exact conflict checks.
            existing = self.events[action_key]
            # Reject one identity reused with different money or meaning.
            if existing["player_id"] != player_id or existing["round_id"] != round_id or existing["transaction_type"] != transaction_type or existing["amount"] != amount or existing["details"]["request_fingerprint"] != request_fingerprint:
                # Match the production gateway conflict boundary.
                raise ConflictError("Fake Dragon Tiger ledger dimensions conflict")
            # Preserve the same event identity and report recovery.
            return copy.deepcopy(existing), True
        # Calculate candidate wallet balance before committing evidence.
        candidate = round(self.balances[player_id] + amount, 2)
        # Reject an aggregate wager that would overdraw the fake wallet.
        if candidate < 0:
            # Preserve provider state and ledger bytes on rejection.
            raise InsufficientFundsError()
        # Commit the fake wallet movement exactly once.
        self.balances[player_id] = candidate
        # Build one production-shaped immutable ledger event.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "game": engine.GAME_ID, "round_id": round_id, "transaction_type": transaction_type, "amount": amount, "ts": "2026-07-14T00:00:00Z", "details": {**copy.deepcopy(details), "idempotency_key": action_key, "request_fingerprint": request_fingerprint}}
        # Persist the committed event under its unique action identity.
        self.events[action_key] = event
        # Lose one response only after the immutable event exists.
        if suffix in self.fail_after:
            # Consume the one-shot fault before surfacing it.
            self.fail_after.remove(suffix)
            # Force caller recovery from exact committed proof.
            raise RuntimeError("simulated lost ledger response")
        # Report that this call created the event.
        return copy.deepcopy(event), False

    # Find one committed event through every immutable proof dimension.
    def find(self, *, player_id, round_id, transaction_type, action_key, request_fingerprint):
        # Read the event addressed by deterministic action key.
        event = self.events.get(action_key)
        # Return no proof when this action never committed.
        if event is None:
            # Preserve production gateway optional-result behavior.
            return None
        # Require player, round, type, and meaning to match.
        if event["player_id"] != player_id or event["round_id"] != round_id or event["transaction_type"] != transaction_type or event["details"]["request_fingerprint"] != request_fingerprint:
            # Surface conflict instead of satisfying proof with unrelated data.
            raise ConflictError("Fake Dragon Tiger proof dimensions conflict")
        # Return detached immutable proof like the production adapter.
        return copy.deepcopy(event)


# Verify retries, private shoe lifecycle, frozen response, and exactly-once recovery.
class DragonTigerServiceTests(unittest.TestCase):
    # Build isolated provider, wallet, and deterministic cards before each test.
    def setUp(self):
        # Create fresh player-scoped storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and immutable ledger events.
        self.ledger = FakeLedgerGateway()
        # Build deterministic Dragon-winning service without files or ambient entropy.
        self.service = DragonTigerService(repository=self.repository, ledger_gateway=self.ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, shoe_factory=lambda: rigged_shoe(), clock=lambda: "2026-07-14T00:00:00Z")

    # Confirm provider-current preparation is idempotent and preserves siblings.
    def test_preparation_preserves_sibling_and_never_redeals(self):
        # Seed unrelated provider-owned metadata before private preparation.
        self.repository.documents["player-a"] = {**engine.default_state(), "atomic_markers": ["sibling"]}
        # Count complete shoe installations across identical preparations.
        draws = []
        # Build a service whose shoe seam records every invocation.
        service = DragonTigerService(repository=self.repository, ledger_gateway=self.ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, shoe_factory=lambda: draws.append("shoe") or rigged_shoe(), clock=lambda: "2026-08-16T01:00:00Z")
        # Bind one exact normalized request and its stable identities.
        wager = {"bet": "dragon", "wager": 2.0}
        # Derive exact semantic conflict proof once.
        fingerprint = engine.request_fingerprint(wager["bet"], wager["wager"])
        # Prepare the same action twice through provider authority.
        first = service.prepare(player_id="player-a", request_id="prepared-action", round_id=engine.round_id_for("player-a", "prepared-action"), fingerprint=fingerprint, wager=wager)
        # Repeat without permitting another shoe installation or deal.
        second = service.prepare(player_id="player-a", request_id="prepared-action", round_id=engine.round_id_for("player-a", "prepared-action"), fingerprint=fingerprint, wager=wager)
        # Require one deal, identical cards, replay evidence, and sibling preservation.
        self.assertEqual((["shoe"], "KS", "KS", False, True, ["sibling"]), (draws, first["entropy"]["dragon_card"], second["entropy"]["dragon_card"], first["replayed"], second["replayed"], self.repository.documents["player-a"]["atomic_markers"]))
        # Keep private dealt cards out of the frozen public state payload.
        self.assertEqual([], service._payload("player-a")["state"]["recent_rounds"])

    # Confirm exact retries do not deal or move balances twice.
    def test_exact_retry_replays_one_debit_and_credit(self):
        # Execute one deterministic Dragon win.
        first = self.service.play("session-player", {"action_id": "action-001", "bet": "dragon", "wager": 10})
        # Replay identical normalized input.
        second = self.service.play("session-player", {"action_id": "action-001", "bet": "dragon", "wager": 10})
        # Verify identical round, explicit replay, two events, and one net win.
        self.assertEqual((first["round"], True, 2, 1010.0), (second["round"], second["replayed"], len(self.ledger.events), self.ledger.balances["session-player"]))

    # Confirm service response keys remain aligned with frozen OpenAPI schemas.
    def test_round_response_shape_matches_contract(self):
        # Execute one complete deterministic round.
        result = self.service.play("session-player", {"action_id": "action-shape", "bet": "dragon", "wager": 5})
        # Require exact top-level, state, shoe, rules, and round key inventories.
        self.assertEqual(({"game", "state", "player", "rules", "round", "ledger", "replayed"}, {"shoe", "recent_rounds"}, {"shoe_number", "cards_remaining", "shuffle_pending"}, {"profile", "deck_count", "burn_count", "cut_cards", "bets"}, {"round_id", "action_id", "player_id", "status", "bet", "wager", "dragon_card", "tiger_card", "winner", "outcome", "total_return", "net", "settled_at", "shoe_number"}), (set(result), set(result["state"]), set(result["state"]["shoe"]), set(result["rules"]), set(result["round"])))
        # Require current state to contain the exact settled round once.
        self.assertEqual([result["round"]], result["state"]["recent_rounds"])

    # Confirm simultaneous duplicates share one atomic result.
    def test_concurrent_duplicate_replays_one_debit_and_credit(self):
        # Build the identical retry-safe request for both workers.
        request = {"action_id": "action-concurrent", "bet": "dragon", "wager": 10}
        # Run two callers against shared helper serialization.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Collect both terminal responses.
            results = list(executor.map(lambda _index: self.service.play("session-player", request), range(2)))
        # Require one commit, one replay, identical round, and exactly two movements.
        self.assertEqual(([False, True], results[0]["round"], 2), (sorted(result["replayed"] for result in results), results[1]["round"], len(self.ledger.events)))

    # Confirm durable action replay survives beyond visible history and provider ledger pruning.
    def test_delayed_replay_uses_durable_action_index_without_reordering_history(self):
        # Provide enough fake tokens for the complete bounded-history exercise.
        self.ledger.balances["session-player"] = 1000000.0
        # Execute one more action than the exact fifty-row visible limit.
        for index in range(engine.RECENT_ROUND_LIMIT + 1):
            # Use a stable unique identity for every settled round.
            self.service.play("session-player", {"action_id": f"action-history-{index:03d}", "bet": "tiger", "wager": 1})
        # Snapshot bounded chronology before replaying the evicted first round.
        recent_before = copy.deepcopy(self.repository.documents["session-player"]["recent_rounds"])
        # Remove old provider evidence to prove durable state no longer needs a scan horizon.
        old_round_id = engine.round_id_for("session-player", "action-history-000")
        # Delete only fake old-round ledger rows.
        self.ledger.events = {key: event for key, event in self.ledger.events.items() if event["round_id"] != old_round_id}
        # Snapshot wallet and event count before delayed replay.
        before = (self.ledger.balances["session-player"], len(self.ledger.events))
        # Replay the first action after visible history and provider proof eviction.
        replay = self.service.play("session-player", {"action_id": "action-history-000", "bet": "tiger", "wager": 1})
        # Require durable replay without chronology or money movement changes.
        self.assertEqual((True, old_round_id, recent_before, before), (replay["replayed"], replay["ledger"]["wager"]["round_id"], self.repository.documents["session-player"]["recent_rounds"], (self.ledger.balances["session-player"], len(self.ledger.events))))

    # Confirm one action identity cannot represent another bet.
    def test_conflicting_retry_fails_closed(self):
        # Commit one Dragon request.
        self.service.play("session-player", {"action_id": "action-002", "bet": "dragon", "wager": 2})
        # Reject the same action identity with Tiger meaning.
        with self.assertRaises(ConflictError):
            # Exercise semantic fingerprint conflict handling.
            self.service.play("session-player", {"action_id": "action-002", "bet": "tiger", "wager": 2})
        # Require no extra movement on conflict.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm definitive pre-commit wager failure restores shoe state.
    def test_precommit_wager_failure_restores_shoe_and_preparation(self):
        # Arm one rejection before the wager action becomes immutable.
        self.ledger.fail_before.add("wager")
        # Preserve the exact default state expected after rollback.
        expected = engine.default_state()
        # Surface the original provider failure.
        with self.assertRaisesRegex(RuntimeError, "pre-commit"):
            # Attempt one valid round whose deal must be rolled back.
            self.service.play("session-player", {"action_id": "precommit-action", "bet": "dragon", "wager": 2})
        # Require no money, shoe, preparation, or history mutation.
        self.assertEqual((expected, {}, 1000.0), (self.repository.documents["session-player"], self.ledger.events, self.ledger.balances["session-player"]))

    # Confirm a lost wager response retains committed cards for recovery.
    def test_lost_wager_response_recovers_exact_committed_result(self):
        # Arm one response loss after debit evidence publication.
        self.ledger.fail_after.add("wager")
        # Execute a round whose first response is lost.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve original transport-style error for caller retry.
            self.service.play("session-player", {"action_id": "lost-wager-action", "bet": "dragon", "wager": 2})
        # Require prepared cards and exactly one immutable debit.
        self.assertEqual(("KS", 1), (self.repository.documents["session-player"]["prepared_actions"]["lost-wager-action"]["dragon_card"], len(self.ledger.events)))
        # Recover with a shoe that would visibly differ if redrawn.
        recovering = DragonTigerService(repository=self.repository, ledger_gateway=self.ledger, player_reader=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, shoe_factory=lambda: rigged_shoe("2S", "AH"), clock=lambda: "later")
        # Retry the exact public action once.
        result = recovering.play("session-player", {"action_id": "lost-wager-action", "bet": "dragon", "wager": 2})
        # Require original cards, replay evidence, and only one debit plus credit.
        self.assertEqual(("KS", True, 2), (result["round"]["dragon_card"], result["replayed"], len(self.ledger.events)))

    # Confirm a lost settlement response recovers one immutable credit.
    def test_lost_settlement_response_recovers_without_duplicate_credit(self):
        # Arm one response loss after positive credit publication.
        self.ledger.fail_after.add("settlement")
        # Execute one deterministic Dragon win.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve first failed response while both events stay durable.
            self.service.play("session-player", {"action_id": "lost-credit-action", "bet": "dragon", "wager": 2})
        # Retry identical action to reconstruct terminal state and response.
        result = self.service.play("session-player", {"action_id": "lost-credit-action", "bet": "dragon", "wager": 2})
        # Require one terminal round, explicit replay, and exactly two events.
        self.assertEqual((4.0, True, 2, 1), (result["round"]["total_return"], result["replayed"], len(self.ledger.events), len(result["state"]["recent_rounds"])))

    # Confirm every durable lifecycle write can lose its response and recover once.
    def test_provider_write_crash_boundaries_converge(self):
        # Name provider states after debit, result, credit, finalization, and archival.
        boundaries = {
            "post-debit": lambda state: state.get("prepared_actions", {}).get("post-debit", {}).get("status") == "wager_committed",
            "post-result": lambda state: state.get("prepared_actions", {}).get("post-result", {}).get("status") == "settlement_attempting" and "settlement_ledger" not in state["prepared_actions"]["post-result"],
            "post-credit": lambda state: bool(state.get("prepared_actions", {}).get("post-credit", {}).get("settlement_ledger")),
            "post-finalize": lambda state: state.get("prepared_actions", {}).get("post-finalize", {}).get("status") == "settled",
            "post-archive": lambda state: "post-archive" in state.get("settled_actions", {}) and "post-archive" not in state.get("prepared_actions", {}),
        }
        # Exercise every durable boundary independently.
        for boundary, predicate in boundaries.items():
            # Label failures by exact crash schedule.
            with self.subTest(boundary=boundary):
                # Create isolated provider and ledger authority.
                repository, ledger = PersistThenFailRepository(predicate), FakeLedgerGateway({"player-a": 100.0})
                # Build one deterministic service for the selected schedule.
                service = DragonTigerService(repository=repository, ledger_gateway=ledger, shoe_factory=lambda: rigged_shoe(), clock=lambda: "2026-08-16T01:00:00Z", player_reader=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]})
                # Require the selected persisted transition to lose its response.
                with self.assertRaisesRegex(RuntimeError, "lost provider response"):
                    # Execute one stable action identity per isolated schedule.
                    service.play("player-a", {"action_id": boundary, "bet": "dragon", "wager": 1})
                # Resume with cards that would reveal an illegal redraw.
                recovering = DragonTigerService(repository=repository, ledger_gateway=ledger, shoe_factory=lambda: rigged_shoe("2S", "AH"), clock=lambda: "later", player_reader=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]})
                # Recover the exact interrupted public action.
                result = recovering.play("player-a", {"action_id": boundary, "bet": "dragon", "wager": 1})
                # Require original cards, one row, no private action, and no duplicate money.
                self.assertEqual(("KS", 1, False, 2), (result["round"]["dragon_card"], len(repository.documents["player-a"]["recent_rounds"]), boundary in repository.documents["player-a"]["prepared_actions"], len(ledger.events)))

    # Confirm a historical debit proof recovers without canonical helper fields or shoe consumption.
    def test_legacy_debit_proof_recovery_preserves_empty_shoe(self):
        # Define stable historical request and normalized meaning.
        request = {"action_id": "legacy-proof", "bet": "dragon", "wager": 1}
        # Derive established round and request fingerprint.
        round_id = engine.round_id_for("player-a", request["action_id"])
        # Bind immutable semantic identity once.
        fingerprint = engine.request_fingerprint(request["bet"], request["wager"])
        # Build historical proof fields without canonical entropy or request_id.
        details = {"action_id": request["action_id"], "request_fingerprint": fingerprint, "bet": "dragon", "wager": 1.0, "dragon_card": "KS", "tiger_card": "QH", "winner": "dragon", "outcome": "win", "total_return": 2.0, "net": 1.0, "created_at": "2026-07-14T00:00:00Z", "shoe_number": 0, "profile": engine.PROFILE_ID}
        # Commit the pre-migration debit exactly once.
        self.ledger.apply_once(player_id="player-a", amount=-1.0, transaction_type="DRAGON_TIGER_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", request_fingerprint=fingerprint, details=details)
        # Recover through ordinary service with a shoe seam that must remain unused.
        recovering = DragonTigerService(repository=self.repository, ledger_gateway=self.ledger, shoe_factory=lambda: (_ for _ in ()).throw(AssertionError("ledger-only recovery consumed a shoe")), clock=lambda: "later", player_reader=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Recover the historical action through frozen public input.
        result = recovering.play("player-a", request)
        # Require committed cards/time, replay, one new credit, empty shoe, and no visible history promotion.
        self.assertEqual(("KS", "2026-07-14T00:00:00Z", True, 2, [], 0), (result["round"]["dragon_card"], result["round"]["settled_at"], result["replayed"], len(self.ledger.events), result["state"]["recent_rounds"], result["state"]["shoe"]["cards_remaining"]))

    # Confirm terminal history stays direct, oldest-to-newest, and bounded to fifty.
    def test_history_retains_newest_fifty_direct_rounds(self):
        # Give fake wallet enough tokens for complete history exercise.
        self.ledger.balances["session-player"] = 1000000.0
        # Publish five more rounds than exact game history bound.
        for index in range(engine.RECENT_ROUND_LIMIT + 5):
            # Use one stable caller identity per completed action.
            self.service.play("session-player", {"action_id": f"history-{index:03d}", "bet": "tiger", "wager": 1})
        # Read exact direct provider rows after bounded archival.
        state = self.repository.documents["session-player"]
        # Require newest fifty visible, every durable action, and no helper wrapper leakage.
        self.assertEqual((50, "history-005", "history-054", 55, False), (len(state["recent_rounds"]), state["recent_rounds"][0]["action_id"], state["recent_rounds"][-1]["action_id"], len(state["settled_actions"]), any("public" in row for row in state["recent_rounds"])))

    # Confirm losing rounds create no zero-value settlement credit.
    def test_loss_uses_one_debit_and_no_credit(self):
        # Bet Tiger against deterministic Dragon-winning cards.
        result = self.service.play("session-player", {"action_id": "action-loss", "bet": "tiger", "wager": 3})
        # Require loss, absent settlement proof, and only one debit.
        self.assertEqual(("loss", None, 1), (result["round"]["outcome"], result["ledger"]["settlement"], len(self.ledger.events)))

    # Confirm runtime validation matches the strict frozen request schema.
    def test_round_request_rejects_contract_drift(self):
        # Define malformed cases that coercive parsing could accept.
        invalid_requests = [
            {"action_id": " action-007", "bet": "dragon", "wager": 1},
            {"action_id": "action-007", "bet": "Dragon", "wager": 1},
            {"action_id": "action-007", "bet": "dragon", "wager": "1"},
            {"action_id": "action-007", "bet": "dragon", "wager": 1.001},
            {"action_id": "action-007", "bet": "dragon", "wager": 1, "debug": True},
        ]
        # Verify every malformed shape fails before money movement.
        for request in invalid_requests:
            # Identify each failing input independently.
            with self.subTest(request=request):
                # Require the shared public validation class.
                with self.assertRaises(ValidationError):
                    # Exercise the complete service boundary.
                    self.service.play("session-player", request)
        # Require strict rejection to leave ledger empty.
        self.assertEqual({}, self.ledger.events)

    # Confirm source topology contains only one shared money coordinator.
    def test_service_source_uses_one_shared_coordinator(self):
        # Resolve exact service bytes from this checkout.
        source = Path(__file__).resolve().parents[3] / "casino" / "games" / "dragon_tiger" / "service.py"
        # Read source inspected by central governance.
        text = source.read_text(encoding="utf-8")
        # Require one helper construction and no legacy settlement aliases or locks.
        self.assertEqual((1, False, False, False, False, False), (text.count("SimpleWagerGame("), "GameSettlementGateway" in text, "CoreLedgerGateway" in text, ".apply_once(" in text, "_ACTION_LOCK" in text, "_ATOMIC_BASELINE_KEY" in text))


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
        router, recording = Router(), RecordingService()
        # Attach injected route handlers.
        api.register(router, service=recording)
        # Build authenticated request context.
        context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}
        # Dispatch state with hostile query identity.
        router.dispatch("GET", "/api/v1/games/dragon-tiger/state?player_id=attacker", {}, context=dict(context))
        # Dispatch round with hostile body identity.
        router.dispatch("POST", "/api/v1/games/dragon-tiger/rounds", {"player_id": "attacker", "action_id": "action-006", "bet": "dragon", "wager": 1}, context=dict(context))
        # Require both handlers to receive only bound player identity.
        self.assertEqual((["session-player"], "session-player"), (recording.state_players, recording.play_calls[0][0]))

    # Confirm authenticated Admin identity overrides compatibility input.
    def test_admin_player_overrides_body_and_resolver_ids(self):
        # Create focused router and recording service.
        router, recording = Router(), RecordingService()
        # Attach injected route handlers.
        api.register(router, service=recording)
        # Build authenticated Admin-like context without non-Admin binding.
        context = {"user": {"player_id": "admin-player", "role": "admin", "status": "active"}}
        # Dispatch hostile body identity through compatibility resolver.
        router.dispatch("POST", "/api/v1/games/dragon-tiger/rounds", {"player_id": "victim-player", "action_id": "action-admin", "bet": "dragon", "wager": 1}, context=dict(context))
        # Require game boundary to restore authenticated Admin player.
        self.assertEqual("admin-player", recording.play_calls[0][0])


# Run this focused suite directly when requested.
if __name__ == "__main__":
    # Exit through standard unittest result handling.
    unittest.main()
