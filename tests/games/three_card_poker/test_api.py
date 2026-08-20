# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session, persistence, and exactly-once Three Card Poker API tests."""

# Import deep-copy support to model provider document boundaries.
import copy
# Import JSON support for exact disposable provider bytes.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for independent stale-load workers.
import subprocess
# Import the active interpreter selected by the repository test runner.
import sys
# Import task-owned temporary directories for provider bytes and gates.
import tempfile
# Import bounded polling for worker rendezvous.
import time
# Import unittest for dependency-free focused coverage.
import unittest
# Import portable paths for exact checkout and worker files.
from pathlib import Path

# Import deterministic ownership for every fresh-process race worker.
from tests.process_race import ProcessRacePool

# Import stable public errors for conflict and insufficient-funds assertions.
from casino.errors import ConflictError, InsufficientFundsError
# Import the isolated router used by focused game tests.
from casino.router import Router
# Import only this game's API, engine, and service modules.
from casino.games.three_card_poker import api, engine, service


# Simulate player-scoped persistence without touching repository runtime data.
class MemoryRepository:
    # Start with no persisted player documents.
    def __init__(self):
        # Store detached documents by player id.
        self.documents = {}

    # Load one detached player state document.
    def load(self, player_id: str) -> dict:
        # Return saved state or a fresh production-shaped default.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Apply one callback to provider-current state and publish its detached result.
    def update(self, player_id: str, mutator) -> dict:
        # Give the callback a detached document so failed transitions cannot leak.
        current = copy.deepcopy(self.documents.get(player_id, engine.default_state()))
        # Apply the complete transition inside this fake provider boundary.
        updated = mutator(current)
        # Store a detached result so later loads remain isolated.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return an independent authoritative value to the service.
        return copy.deepcopy(updated)


# Record ledger-shaped events and enforce fake balances.
class RecordingLedger:
    # Seed deterministic balances for isolated players.
    def __init__(self, balances=None, *, lost_response_types=(), before_failure=None):
        # Store mutable two-decimal fake balances.
        self.balances = dict(balances or {"session-player": 1000.0, "other-player": 1000.0})
        # Retain append-only committed event evidence.
        self.events = []
        # Allow one deterministic rejection before a movement reaches the ledger.
        self.fail_next = False
        # Select movement types whose first committed response is lost.
        self.lost_response_types = set(lost_response_types)
        # Retain one optional sibling publication before a rejected movement.
        self.before_failure = before_failure
        # Count every mutation callback attempt by transaction vocabulary.
        self.apply_calls = {}

    # Find a committed event matching every prepared intent dimension.
    def find_intent(self, intent: dict):
        # Search newest-first for exact ownership and action identity.
        for event in reversed(self.events):
            # Normalize structured event details.
            details = event.get("details") or {}
            # Return only the exact stable prepared movement.
            if event["player_id"] == intent["player_id"] and event["game"] == intent["game"] and event["round_id"] == intent["round_id"] and event["transaction_type"] == intent["transaction_type"] and details.get("three_card_poker_action_id") == intent["action_id"]:
                # Return detached evidence like a storage provider read.
                return copy.deepcopy(event)
        # Report that no movement committed yet.
        return None

    # Apply one prepared movement atomically to the fake balance and ledger.
    def transact(self, intent: dict) -> dict:
        # Count the attempted movement before failure or commit handling.
        transaction_type = intent["transaction_type"]
        # Advance the exact movement-type attempt count.
        self.apply_calls[transaction_type] = self.apply_calls.get(transaction_type, 0) + 1
        # Fail before committing when the focused schedule requests rejection.
        if self.fail_next:
            # Consume the one-shot pre-commit failure.
            self.fail_next = False
            # Publish an unrelated sibling at the exact rollback boundary when supplied.
            if self.before_failure is not None:
                # Invoke the bounded sibling seam once.
                self.before_failure()
            # Surface a stable public-shaped error from the movement boundary.
            raise InsufficientFundsError(details={"player_id": intent["player_id"], "amount": intent["amount"]})
        # Convert debit instructions to signed negative movement.
        signed_amount = -intent["amount"] if intent["direction"] == "debit" else intent["amount"]
        # Read the current player balance.
        before = round(float(self.balances[intent["player_id"]]), 2)
        # Calculate the proposed balance.
        after = round(before + signed_amount, 2)
        # Reject overdraws through the same public error class as shared ledger.
        if after < 0:
            # Preserve useful fake-ledger diagnostics.
            raise InsufficientFundsError(details={"player_id": intent["player_id"], "balance": before, "amount": signed_amount})
        # Build one ledger-shaped append-only event.
        event = {
            "ledger_id": f"ledger-{len(self.events) + 1}",  # Assign stable test evidence id.
            "player_id": intent["player_id"],  # Preserve session ownership.
            "game": intent["game"],  # Preserve game ownership.
            "round_id": intent["round_id"],  # Preserve round ownership.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "amount": signed_amount,  # Preserve signed ledger amount.
            "balance_before": before,  # Preserve the prior balance.
            "balance_after": after,  # Preserve the committed balance.
            "details": copy.deepcopy(intent["details"]),  # Preserve replay details.
        }
        # Commit the fake balance with the event.
        self.balances[intent["player_id"]] = after
        # Append the immutable movement evidence.
        self.events.append(copy.deepcopy(event))
        # Lose the response only after the immutable movement is committed.
        if transaction_type in self.lost_response_types:
            # Consume the one-shot transport failure stage.
            self.lost_response_types.remove(transaction_type)
            # Surface an ambiguous response so normal recovery must find proof.
            raise RuntimeError(f"lost {transaction_type} response")
        # Return detached committed evidence.
        return copy.deepcopy(event)

    # Return one player-shaped wallet snapshot.
    def player(self, player_id: str) -> dict:
        # Expose only fields needed by game responses.
        return {"player_id": player_id, "balance": self.balances[player_id]}


# Generate distinct deterministic round identifiers.
class IdFactory:
    # Start before the first generated id.
    def __init__(self):
        # Retain a monotonic local sequence.
        self.sequence = 0

    # Return one prefixed stable id.
    def __call__(self, prefix: str) -> str:
        # Advance before constructing the id.
        self.sequence += 1
        # Return a router-safe identifier.
        return f"{prefix}_round_{self.sequence}"


# Verify bound sessions, action fingerprints, recovery, and ledger-only flows.
class ThreeCardPokerApiTests(unittest.TestCase):
    # Build fresh in-memory service ports and a local router before every test.
    def setUp(self):
        # Create empty provider-shaped state storage.
        self.repository = MemoryRepository()
        # Create recording fake wallet balances.
        self.ledger = RecordingLedger()
        # Build deterministic service dependencies.
        self.game_service = service.ThreeCardPokerService(repository=self.repository, ledger_adapter=self.ledger, player_reader=self.ledger.player, clock=lambda: "2026-07-14T00:00:00.000Z", id_factory=IdFactory(), seed_factory=lambda request_id: f"api:{request_id}")
        # Create a game-local router without shared registration changes.
        self.router = Router()
        # Register only the issue #93 endpoints.
        api.register(self.router, service=self.game_service)
        # Store the authenticated player context used by shared dispatch.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one focused route through the real session resolver path.
    def call(self, path, body=None, method="POST"):
        # Delegate with a fresh context copy so requests cannot leak mutations.
        return self.router.dispatch(method, path, body or {}, context=copy.deepcopy(self.context))

    # Deal one low-cost deterministic round for repeated tests.
    def deal(self, request_id="deal-action-1", ante=10, pair_plus=2):
        # Call the public route using only supported action inputs.
        return self.call("/api/v1/games/three-card-poker/rounds", {"request_id": request_id, "ante": ante, "pair_plus": pair_plus})

    # Confirm hostile player ids cannot escape the authenticated session.
    def test_session_binding_and_exact_deal_replay(self):
        # Submit conflicting body identity with one stable retry id.
        first = self.call("/api/v1/games/three-card-poker/rounds?player_id=other-player", {"player_id": "other-player", "request_id": "deal-session-1", "ante": 10, "pair_plus": 3})
        # Replay the exact same request and hostile identity.
        second = self.call("/api/v1/games/three-card-poker/rounds?player_id=other-player", {"player_id": "other-player", "request_id": "deal-session-1", "ante": 10, "pair_plus": 3})
        # Verify response ownership follows authenticated context.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify every ledger event follows authenticated context.
        self.assertTrue(all(event["player_id"] == "session-player" for event in self.ledger.events))
        # Verify exact replay returns the original server round.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify replay is labeled explicitly.
        self.assertTrue(second["replayed"])
        # Verify one aggregate initial debit covers both wagers.
        self.assertEqual(["THREE_CARD_POKER_INITIAL_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify dealer cards remain hidden while a decision is pending.
        self.assertEqual(["??", "??", "??"], second["round"]["dealer_hand"])

    # Confirm a deal identifier cannot be reused with changed normalized money.
    def test_altered_deal_retry_fails_closed(self):
        # Commit the original low-cost deal.
        self.deal(request_id="deal-conflict-1", ante=10, pair_plus=2)
        # Reuse the same id with an altered Ante.
        with self.assertRaises(ConflictError):
            # Assert the service rejects before another debit.
            self.deal(request_id="deal-conflict-1", ante=11, pair_plus=2)
        # Verify only the original movement remains.
        self.assertEqual(1, len(self.ledger.events))

    # Confirm Play and its aggregate payout are exactly-once across retries and marker loss.
    def test_play_replay_and_reload_recovery_do_not_duplicate_ledger(self):
        # Deal one deterministic decision-ready round.
        started = self.deal(request_id="deal-play-1", ante=10, pair_plus=2)
        # Capture the stable server round identifier.
        round_id = started["round"]["round_id"]
        # Commit the matching Play decision once.
        first = self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-play-1", "decision": "play"})
        # Replay the exact decision.
        second = self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-play-1", "decision": "play"})
        # Record event count after the exact replay.
        committed_count = len(self.ledger.events)
        # Simulate a crash that lost every post-ledger state marker.
        self.repository.documents["session-player"]["ledger_actions"] = {}
        # Build a fresh service instance over the same persisted ports.
        reloaded = service.ThreeCardPokerService(repository=self.repository, ledger_adapter=self.ledger, player_reader=self.ledger.player, clock=lambda: "2026-07-14T00:00:02.000Z", id_factory=IdFactory(), seed_factory=lambda request_id: f"api:{request_id}")
        # Trigger state recovery before public projection.
        recovered = reloaded.state("session-player")
        # Verify no event duplicated during replay or reload recovery.
        self.assertEqual(committed_count, len(self.ledger.events))
        # Verify one initial and one Play debit exist.
        self.assertEqual(1, sum(event["transaction_type"] == "THREE_CARD_POKER_INITIAL_DEBIT" for event in self.ledger.events))
        # Verify exactly one matching Play debit exists.
        self.assertEqual(1, sum(event["transaction_type"] == "THREE_CARD_POKER_PLAY_DEBIT" for event in self.ledger.events))
        # Verify exactly one aggregate payout credit exists for this deterministic winning seed.
        self.assertEqual(1, sum(event["transaction_type"] == "THREE_CARD_POKER_PAYOUT_CREDIT" for event in self.ledger.events))
        # Verify both action responses identify the same terminal result.
        self.assertEqual(first["round"], second["round"])
        # Verify the exact retry is labeled replayed.
        self.assertTrue(second["replayed"])
        # Verify reload projects no pending active round.
        self.assertIsNone(recovered["state"]["active_round"])
        # Verify settled dealer cards never retain hidden markers.
        self.assertNotIn("??", recovered["state"]["recent_rounds"][0]["dealer_hand"])

    # Confirm a rejected opening reverses only action-owned game fields.
    def test_rejected_opening_rollback_preserves_concurrent_sibling(self):
        # Publish one unrelated sibling after preparation but before rejection.
        self.ledger.before_failure = lambda: self.repository.documents["session-player"].update({"atomic_markers": ["concurrent"]})
        # Reject the first debit before any immutable movement exists.
        self.ledger.fail_next = True
        # Require the standard insufficient-funds-shaped rejection.
        with self.assertRaises(InsufficientFundsError):
            # Attempt one initial-wager deal.
            self.deal(request_id="deal-rejected-atomic", ante=10, pair_plus=2)
        # Read provider-current state after compare-and-restore.
        persisted = self.repository.documents["session-player"]
        # Require clean game state, sibling preservation, and zero movement.
        self.assertEqual((persisted["rounds"], persisted["requests"], persisted["atomic_markers"], self.ledger.events), ({}, {}, ["concurrent"], []))

    # Confirm a rejected Play restores the decision while preserving a sibling.
    def test_rejected_play_rollback_preserves_concurrent_sibling(self):
        # Commit one normal decision-ready opening.
        started = self.deal(request_id="deal-rejected-play", ante=10, pair_plus=0)
        # Resolve the stable round identifier before the rejected decision.
        round_id = started["round"]["round_id"]
        # Publish one unrelated sibling at the exact rejected-debit boundary.
        self.ledger.before_failure = lambda: self.repository.documents["session-player"].update({"atomic_markers": ["concurrent"]})
        # Reject only the next Play debit before it commits.
        self.ledger.fail_next = True
        # Require the original movement failure.
        with self.assertRaises(InsufficientFundsError):
            # Attempt one matching Play decision.
            self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "play-rejected-atomic", "decision": "play"})
        # Read the restored provider-authoritative document.
        persisted = self.repository.documents["session-player"]
        # Require the actionable round, released action id, preserved sibling, and only the opening debit.
        self.assertEqual((persisted["rounds"][round_id]["phase"], "play-rejected-atomic" in persisted["requests"], persisted["atomic_markers"], [event["transaction_type"] for event in self.ledger.events]), ("decision", False, ["concurrent"], ["THREE_CARD_POKER_INITIAL_DEBIT"]))

    # Confirm an initial debit whose response is lost recovers without a second debit.
    def test_lost_initial_response_recovers_once(self):
        # Lose only the first committed initial-debit response.
        self.ledger.lost_response_types.add("THREE_CARD_POKER_INITIAL_DEBIT")
        # Surface the injected post-commit response loss.
        with self.assertRaisesRegex(RuntimeError, "lost THREE_CARD_POKER_INITIAL_DEBIT response"):
            # Issue one stable opening action.
            self.deal(request_id="deal-lost-initial", ante=10, pair_plus=2)
        # Reconcile immutable proof through the normal state endpoint.
        recovered = self.game_service.state("session-player")
        # Replay the exact deal after recovery.
        replayed = self.deal(request_id="deal-lost-initial", ante=10, pair_plus=2)
        # Require one provider mutation, one event, and stable decision-ready identity.
        self.assertEqual((self.ledger.apply_calls["THREE_CARD_POKER_INITIAL_DEBIT"], len(self.ledger.events), replayed["round"]["round_id"], recovered["state"]["active_round"]["round_id"]), (1, 1, recovered["state"]["active_round"]["round_id"], recovered["state"]["active_round"]["round_id"]))
        # Require the private optimistic baseline never to persist.
        self.assertNotIn(service._ATOMIC_BASELINE_KEY, self.repository.documents["session-player"])

    # Confirm a Play debit whose response is lost settles without duplicating movement.
    def test_lost_play_response_recovers_once(self):
        # Prepare one deterministic decision-ready round.
        started = self.deal(request_id="deal-lost-play", ante=10, pair_plus=2)
        # Lose only the committed Play-debit response.
        self.ledger.lost_response_types.add("THREE_CARD_POKER_PLAY_DEBIT")
        # Surface the lost committed Play response.
        with self.assertRaisesRegex(RuntimeError, "lost THREE_CARD_POKER_PLAY_DEBIT response"):
            # Issue the stable Play action once.
            self.call(f"/api/v1/games/three-card-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-lost-play", "decision": "play"})
        # Recover Play proof and any payout through a normal read.
        recovered = self.game_service.state("session-player")
        # Replay the same terminal decision without any second movement.
        replayed = self.call(f"/api/v1/games/three-card-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-lost-play", "decision": "play"})
        # Require one opening and Play provider call with the stable terminal result.
        self.assertEqual((self.ledger.apply_calls["THREE_CARD_POKER_INITIAL_DEBIT"], self.ledger.apply_calls["THREE_CARD_POKER_PLAY_DEBIT"], replayed["round"], recovered["state"]["recent_rounds"][0]), (1, 1, recovered["state"]["recent_rounds"][0], recovered["state"]["recent_rounds"][0]))

    # Confirm a payout credit whose response is lost recovers without a second credit.
    def test_lost_payout_response_recovers_once(self):
        # Prepare the deterministic seed already proven to produce a payout.
        started = self.deal(request_id="deal-play-1", ante=10, pair_plus=2)
        # Lose only the first committed payout-credit response.
        self.ledger.lost_response_types.add("THREE_CARD_POKER_PAYOUT_CREDIT")
        # Surface the lost committed payout response.
        with self.assertRaisesRegex(RuntimeError, "lost THREE_CARD_POKER_PAYOUT_CREDIT response"):
            # Issue one stable winning Play action.
            self.call(f"/api/v1/games/three-card-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-lost-payout", "decision": "play"})
        # Recover payout proof through the normal state endpoint.
        recovered = self.game_service.state("session-player")
        # Replay the exact terminal action without another credit.
        replayed = self.call(f"/api/v1/games/three-card-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-lost-payout", "decision": "play"})
        # Require one movement per stage and the exact recovered result.
        self.assertEqual((self.ledger.apply_calls["THREE_CARD_POKER_INITIAL_DEBIT"], self.ledger.apply_calls["THREE_CARD_POKER_PLAY_DEBIT"], self.ledger.apply_calls["THREE_CARD_POKER_PAYOUT_CREDIT"], replayed["round"], recovered["state"]["recent_rounds"][0]), (1, 1, 1, recovered["state"]["recent_rounds"][0], recovered["state"]["recent_rounds"][0]))

    # Prove stale fresh processes preserve siblings and one provider-winning decision.
    def test_fresh_process_fold_race_preserves_provider_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "session-player.json"
            # Create the state directory before seeding one active decision.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Build one production-shaped baseline document.
            baseline = engine.default_state()
            # Prepare one deterministic decision-ready round and its initial intent.
            active_round = engine.start_round(baseline, "session-player", 10, 0, "deal-process", round_id="tcp_process_round", created_at="2026-08-15T00:00:00Z", deck=["2C", "3D", "5H", "QS", "9C", "7D"])
            # Read the exact prepared initial intent.
            initial_intent = active_round["ledger_intents"][0]
            # Bind the opening request fingerprint used by normal replay checks.
            baseline["requests"]["deal-process"] = {"command": "deal", "round_id": active_round["round_id"], "fingerprint": {"ante": 10.0, "pair_plus": 0.0}}
            # Seed committed initial-debit evidence so both workers race only the movement-free Fold.
            baseline["ledger_actions"][initial_intent["action_id"]] = {"ledger_id": "ledger-opening", "round_id": active_round["round_id"], "transaction_type": initial_intent["transaction_type"], "event": {"ledger_id": "ledger-opening", "player_id": "session-player", "game": engine.GAME_ID, "round_id": active_round["round_id"], "transaction_type": initial_intent["transaction_type"], "amount": -10.0, "details": copy.deepcopy(initial_intent["details"])}}
            # Seed an unrelated sibling field that the game transition must not own.
            baseline["atomic_markers"] = ["seed"]
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
from casino.games.three_card_poker.service import StateRepository, ThreeCardPokerService
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
            raise RuntimeError('Three Card Poker race release timed out')
        return state
    def update(self, player_id, mutator):
        return base.update(player_id, mutator)
class NoLedger:
    def find_intent(self, _intent):
        return None
    def transact(self, _intent):
        raise RuntimeError('unexpected Three Card Poker movement')
game = ThreeCardPokerService(repository=RendezvousRepository(), ledger_adapter=NoLedger(), player_reader=lambda player_id: {'player_id': player_id, 'balance': 990.0}, clock=lambda: '2026-08-15T00:01:00Z')
try:
    result = game.decide('session-player', 'tcp_process_round', {'action_id': action_id, 'decision': 'fold'})
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
                process = process_pool.spawn([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"fold-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
            process_pool.wait_until_ready([(process, ready) for process, ready, _release in workers], timeout=0)
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.three_card_poker import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('three_card_poker', 'session-player', add, engine.default_state)\n"
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
            # Resolve the sole terminal round.
            terminal = persisted["rounds"]["tcp_process_round"]
            # Require the winning decision, sibling preservation, and no actionable-round resurrection.
            self.assertEqual((terminal["phase"], terminal["decision_action_id"], persisted["atomic_markers"]), ("settled", "fold-process-0", ["seed", "concurrent"]))

    # Confirm a decision identifier cannot change round or command semantics.
    def test_altered_decision_retry_fails_closed(self):
        # Deal one decision-ready round.
        started = self.deal(request_id="deal-decision-conflict", ante=10, pair_plus=0)
        # Read the stable round identifier.
        round_id = started["round"]["round_id"]
        # Commit the original Play decision.
        self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-conflict-1", "decision": "play"})
        # Attempt to reuse the same action as Fold.
        with self.assertRaises(ConflictError):
            # Assert altered retry is rejected before movement.
            self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-conflict-1", "decision": "fold"})

    # Confirm Fold never adds Play debit or payout credit and survives reload.
    def test_fold_forfeits_initial_wagers_without_extra_movement(self):
        # Deal with both required and optional initial wagers.
        started = self.deal(request_id="deal-fold-1", ante=10, pair_plus=5)
        # Capture the server round id.
        round_id = started["round"]["round_id"]
        # Fold through the public decision action.
        folded = self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-fold-1", "decision": "fold"})
        # Verify only the aggregate initial debit exists.
        self.assertEqual(["THREE_CARD_POKER_INITIAL_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify response exposes no additional wager event.
        self.assertIsNone(folded["wager"])
        # Verify response exposes no payout event.
        self.assertIsNone(folded["settlement"])
        # Verify both initial components are forfeited.
        self.assertEqual((-15.0, 0.0), (folded["round"]["net"], folded["round"]["total_payout"]))
        # Verify terminal state moved into recent history.
        self.assertEqual(round_id, folded["state"]["recent_rounds"][0]["round_id"])

    # Confirm a rejected Play debit restores the actionable pre-decision state.
    def test_insufficient_play_wager_rolls_back_for_safe_retry(self):
        # Restrict the authenticated player to only the initial aggregate stake.
        self.ledger.balances["session-player"] = 15.0
        # Spend the full balance on Ante and Pair Plus.
        started = self.deal(request_id="deal-low-balance", ante=10, pair_plus=5)
        # Capture the pending round id.
        round_id = started["round"]["round_id"]
        # Attempt a matching Play wager with no remaining balance.
        with self.assertRaises(InsufficientFundsError):
            # Verify shared insufficient-funds semantics propagate.
            self.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", {"action_id": "decision-low-balance", "decision": "play"})
        # Load the restored persisted state directly.
        restored = self.repository.load("session-player")
        # Verify the round remains decision-ready.
        self.assertEqual("decision", restored["rounds"][round_id]["phase"])
        # Verify rejected action id was removed with rollback.
        self.assertNotIn("decision-low-balance", restored["requests"])
        # Verify no matching Play debit was appended.
        self.assertEqual(0, sum(event["transaction_type"] == "THREE_CARD_POKER_PLAY_DEBIT" for event in self.ledger.events))


# Run this focused module directly for worker validation.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
