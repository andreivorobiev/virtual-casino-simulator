# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session binding and ledger retry tests for Acey-Deucey."""

# Import deep-copy support so fake persistence models JSON documents.
import copy
# Import hashing for exact frozen contract-byte identity checks.
import hashlib
# Import JSON parsing for compatibility, matrix, and digest artifacts.
import json
# Import process environments for isolated provider workers.
import os
# Import repository-relative path resolution for tracked contract evidence.
from pathlib import Path
# Import child-process execution for true cross-process races.
import subprocess
# Import the active interpreter for exact worker parity.
import sys
# Import temporary directories for residue-free provider evidence.
import tempfile
# Import monotonic time for bounded rendezvous polling.
import time
# Import the standard dependency-free test runner.
import unittest

# Import the shared router to exercise route binding.
from casino.router import Router
# Import public conflict, funds, lookup, and validation errors for assertions.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError
# Import the isolated route adapter and engine under test.
from casino.games.acey_deucey import api, engine
# Import the isolated service orchestration under test.
from casino.games.acey_deucey.service import AceyDeuceyService, request_fingerprint

# Resolve the repository root from this game-owned focused test directory.
ROOT = Path(__file__).resolve().parents[3]
# Point at the frozen-v1 OpenAPI contract under test.
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "acey_deucey.v1.yaml"
# Point at the compatible spread-pricing policy record.
COMPATIBILITY_PATH = ROOT / "contracts" / "compatibility" / "acey-deucey-spread-pricing.json"


# Simulate player-scoped state documents without touching repository data files.
class MemoryRepository:
    # Start with no persisted documents.
    def __init__(self):
        # Store detached state documents by player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so service mutations require explicit saves.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document for direct crash-state fixtures.
    def save(self, player_id, state):
        # Persist a deep copy to model the provider boundary.
        self.documents[player_id] = copy.deepcopy(state)

    # Update one player document through a provider-current callback.
    def update(self, player_id, mutator):
        # Load current provider state or one fresh game default.
        current = copy.deepcopy(self.documents.get(player_id, engine.default_state()))
        # Apply the production-shaped callback to provider-current state.
        updated = mutator(current)
        # Persist a detached result to model JSON storage.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return a detached authoritative publication.
        return copy.deepcopy(updated)


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated players.
    def __init__(self):
        # Store fake balances only inside this ledger adapter.
        self.balances = {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only committed events.
        self.events = []

    # Find one committed Acey-Deucey ledger action.
    def find(self, player_id, ledger_action_id):
        # Search newest-first using the production details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["acey_deucey_action_id"] == ledger_action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Resolve any prior committed action before changing balance.
        existing = self.find(player_id, action_key)
        # Reuse exact matching events.
        if existing is not None:
            # Reject semantic conflicts like production.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != request_fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return detached proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject fake overdrafts.
        if new_balance < 0:
            # Raise the canonical shared insufficient-funds error.
            raise InsufficientFundsError("Insufficient play-token balance")
        # Commit the fake balance.
        self.balances[player_id] = new_balance
        # Build public ledger fields used by assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "acey_deucey_action_id": action_key, "request_fingerprint": request_fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, pass behavior, and ledger audit dimensions.
class AceyDeuceyApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before each test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = AceyDeuceyService(repository=self.repository, ledger_gateway=self.ledger, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}")
        # Register only game-owned routes on the shared router.
        self.router = Router()
        # Inject the focused service without global registration.
        api.register(self.router, service=self.service)
        # Store authenticated context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game action through the router.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with copied context so requests remain isolated.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Confirm identical atomic publication preserves unrelated provider siblings.
    def test_atomic_publication_preserves_siblings_and_private_baseline(self):
        # Load one tracked default document through the service boundary.
        state = self.service._load("session-player")
        # Add one deterministic receipt as the desired owned transition.
        state["action_receipts"]["atomic-same"] = {"stage": "deal", "round_id": "round-same", "request_fingerprint": "a" * 64}
        # Publish the tracked transition through provider-current comparison.
        self.service._save("session-player", state)
        # Add unrelated metadata after the first game-owned publication.
        self.repository.documents["session-player"]["atomic_markers"] = ["sibling"]
        # Publish the exact same desired result from the advanced baseline.
        self.service._save("session-player", state)
        # Read the final provider-authoritative document.
        persisted = self.repository.documents["session-player"]
        # Verify the sibling survives and operation metadata never persists.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Keep the optimistic snapshot outside durable player state.
        self.assertNotIn("_acey_deucey_atomic_baseline", persisted)

    # Reject fabricated detached state before entering the provider updater.
    def test_missing_atomic_baseline_fails_before_update(self):
        # Retain a call list that must stay empty on fail-closed input.
        updates = []

        # Expose a repository seam whose update would reveal accidental entry.
        class RejectingRepository:
            # Record forbidden writes without mutating any storage.
            def update(self, player_id, mutator):
                # Retain exact attempted arguments for the final assertion.
                updates.append((player_id, mutator))

        # Build a service whose write seam must remain untouched.
        service = AceyDeuceyService(repository=RejectingRepository())
        # Reject an untracked default document as a stale publication.
        with self.assertRaises(ConflictError):
            # Attempt publication without the required provider-read baseline.
            service._save("session-player", engine.default_state())
        # Prove storage was never reached.
        self.assertEqual([], updates)

    # Prove rejected-debit rollback cannot erase a provider-winning decision.
    def test_rejected_debit_rollback_preserves_concurrent_winner(self):
        # Extend memory storage with one deterministic provider-winner schedule.
        class RacingRepository(MemoryRepository):
            # Start with no documents and no provider updates.
            def __init__(self):
                # Initialize the ordinary detached document store.
                super().__init__()
                # Count atomic publications so only rollback loses the race.
                self.update_calls = 0

            # Publish normally once, then expose a concurrently committed deal.
            def update(self, player_id, mutator):
                # Count this provider-current publication attempt.
                self.update_calls += 1
                # Let the initial pending terminal state commit normally.
                if self.update_calls == 1:
                    # Delegate the first atomic transition unchanged.
                    return super().update(player_id, mutator)
                # Build the provider-winning free-deal identity.
                winner_action = "deal-provider-winner"
                # Derive the canonical free-deal request fingerprint.
                winner_fingerprint = request_fingerprint({"stage": "deal"})
                # Derive the stable provider-winning round identity.
                winner_round_id = engine.round_id_for(player_id, winner_action)
                # Create a different valid active decision before stale rollback enters.
                winner_round = engine.create_round(player_id, winner_action, left_card="4H", right_card="QS", third_card="8D", round_id=winner_round_id, created_at="2026-08-15T01:00:01Z", request_fingerprint=winner_fingerprint)
                # Persist the concurrent authoritative game-owned result first.
                self.documents[player_id] = {"active_round": winner_round, "recent_rounds": [], "action_receipts": {winner_action: {"stage": "deal", "round_id": winner_round_id, "request_fingerprint": winner_fingerprint}}, "atomic_markers": ["provider-winner"]}
                # Present the already-committed winner to the stale rollback callback.
                current = copy.deepcopy(self.documents[player_id])
                # Require the stale callback to raise instead of replacing the winner.
                return mutator(current)

        # Create the race-aware provider and an underfunded wallet gateway.
        repository, ledger = RacingRepository(), RecordingLedger()
        # Restrict the player below the attempted wager.
        ledger.balances["session-player"] = 5.0
        # Build the real service around the race-aware provider.
        service = AceyDeuceyService(repository=repository, ledger_gateway=ledger, get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, clock=lambda: "2026-08-15T01:00:00Z")
        # Build one prepared decision whose debit will be rejected.
        deal_action = "deal-rollback-race"
        # Derive the canonical free-deal fingerprint.
        deal_fingerprint = request_fingerprint({"stage": "deal"})
        # Derive the stable target round id.
        round_id = engine.round_id_for("session-player", deal_action)
        # Create the hidden result used by the losing play operation.
        round_state = engine.create_round("session-player", deal_action, left_card="3H", right_card="KS", third_card="8C", round_id=round_id, created_at="2026-08-15T01:00:00Z", request_fingerprint=deal_fingerprint)
        # Seed the prepared document without exercising the race hook.
        repository.save("session-player", {"active_round": round_state, "recent_rounds": [], "action_receipts": {deal_action: {"stage": "deal", "round_id": round_id, "request_fingerprint": deal_fingerprint}}, "atomic_markers": ["seed"]})
        # Require stale rollback to surface an explicit provider conflict.
        with self.assertRaises(ConflictError):
            # Attempt an unaffordable play whose cleanup loses the state race.
            service.play("session-player", round_id, {"action_id": "play-rollback-race", "wager": 10})
        # Read the authoritative concurrent winner after the failed rollback.
        persisted = repository.load("session-player")
        # Verify the winner remains active and the stale terminal round is absent.
        self.assertEqual(("deal-provider-winner", [], ["provider-winner"]), (persisted["active_round"]["deal_action_id"], persisted["recent_rounds"], persisted["atomic_markers"]))
        # Verify rejected debit created no wallet movement.
        self.assertEqual((5.0, []), (ledger.balances["session-player"], ledger.events))

    # Prove stale fresh processes preserve siblings and expose one pass winner.
    def test_fresh_process_pass_race_has_one_state_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / "acey_deucey" / "session-player.json"
            # Create the state directory before seeding one prepared round.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Bind one stable deal identity and round id for both contenders.
            deal_action_id = "atomic-deal"
            # Compute the same free-deal fingerprint used by production.
            deal_fingerprint = request_fingerprint({"stage": "deal"})
            # Derive one stable round identity from player and action.
            round_id = engine.round_id_for("session-player", deal_action_id)
            # Create the hidden-card decision both workers must observe.
            round_state = engine.create_round("session-player", deal_action_id, left_card="3H", right_card="KS", third_card="8C", round_id=round_id, created_at="2026-08-15T01:00:00Z", request_fingerprint=deal_fingerprint)
            # Build exact initial game-owned fields plus one unrelated sibling.
            initial_state = {"active_round": round_state, "recent_rounds": [], "action_receipts": {deal_action_id: {"stage": "deal", "round_id": round_id, "request_fingerprint": deal_fingerprint}}, "atomic_markers": ["seed"]}
            # Publish deterministic JSON for both child providers.
            state_path.write_text(json.dumps(initial_state, sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind every child to disposable state and this exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one worker whose repository pauses after capturing stale state.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError
from casino.games.acey_deucey import engine
from casino.games.acey_deucey.service import AceyDeuceyService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
round_id = sys.argv[3]
action_id = sys.argv[4]
class Repository:
    def load(self, player_id):
        state = load_player_game_state('acey_deucey', player_id, engine.default_state)
        ready.write_text('ready', encoding='utf-8')
        deadline = time.monotonic() + 10
        while not release.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not release.exists():
            raise RuntimeError('release gate timeout')
        return state
    def update(self, player_id, mutator):
        return update_player_game_state('acey_deucey', player_id, mutator, engine.default_state)
class Ledger:
    def find(self, player_id, action_id):
        return None
    def apply_once(self, **kwargs):
        raise AssertionError('pass must not reach the ledger')
game = AceyDeuceyService(repository=Repository(), ledger_gateway=Ledger(), get_player=lambda player_id: {'player_id': player_id, 'balance': 100.0}, clock=lambda: '2026-08-15T01:00:00Z')
try:
    game.pass_round('session-player', round_id, {'action_id': action_id})
    print('PASS')
except ConflictError:
    print('CONFLICT')
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start one provider winner candidate and one stale loser candidate.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), round_id, f"pass-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain process and gate ownership.
                workers.append((process, ready_path, release_path))
            # Bound the stale-load rendezvous.
            deadline = time.monotonic() + 10
            # Wait until both workers captured the same prepared document.
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.acey_deucey import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('acey_deucey', 'session-player', add, engine.default_state)\n"
            # Commit the sibling after both workers captured stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish the winning pass.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require the first process to publish one pass without ledger work.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS"), winner_error)
            # Release the stale worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the explicit fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require conflict instead of a silent stale overwrite.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one terminal winner with no active-round resurrection.
            self.assertEqual((persisted["active_round"], len(persisted["recent_rounds"]), persisted["recent_rounds"][0]["pass_action_id"]), (None, 1, "pass-process-0"))
            # Require both unrelated sibling values to survive the game action.
            self.assertEqual(["seed", "concurrent"], persisted["atomic_markers"])
            # Verify private optimistic metadata never enters persistent bytes.
            self.assertNotIn("_acey_deucey_atomic_baseline", persisted)

    # Prepare one active deterministic fixture round.
    def prepared_round(self, left_card, right_card, third_card, action_id="deal-fixture"):
        # Build the same deal fingerprint shape as production.
        fingerprint = request_fingerprint({"stage": "deal"})
        # Derive a stable round id.
        round_id = engine.round_id_for("session-player", action_id)
        # Create prepared state with a private result card.
        round_state = engine.create_round("session-player", action_id, left_card=left_card, right_card=right_card, third_card=third_card, round_id=round_id, created_at="2026-07-14T00:00:00Z", request_fingerprint=fingerprint)
        # Persist the active player document.
        self.repository.save("session-player", {"active_round": round_state, "recent_rounds": [], "action_receipts": {action_id: {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}}})
        # Return the stable route id.
        return round_id

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_free_deal(self):
        # Deal boundaries with competing hostile player ids.
        first = self.call("/api/v1/games/acey-deucey/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1"})
        # Replay the exact free deal.
        second = self.call("/api/v1/games/acey-deucey/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1"})
        # Verify round ownership follows the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify no ledger movement happens during the free boundary deal.
        self.assertEqual([], self.ledger.events)
        # Verify the same round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify the hidden third card is not public before play.
        self.assertNotIn("_third_card", first["round"])
        # Read through another authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Verify the other session cannot see the first player's active deal.
        other_state = self.call("/api/v1/games/acey-deucey/state?player_id=session-player", method="GET", context=other_context)
        # Confirm session isolation.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject cross-session play against the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise private round lookup through the real router.
            self.call(f"/api/v1/games/acey-deucey/rounds/{first['round']['round_id']}/play", {"action_id": "play-cross", "wager": 1}, context=other_context)

    # Confirm inside wins debit and credit exactly once under stable ledger ids.
    def test_inside_play_replay_is_exactly_once(self):
        # Prepare a guaranteed inside result.
        round_id = self.prepared_round("2H", "AS", "7C")
        # Play the round once.
        first = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-win", "wager": 5})
        # Replay the same play action.
        second = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-win", "wager": 5})
        # Verify the inside return against the published spread price rather than a flat multiple, so the
        # assertion tracks the paytable instead of pinning a value the edge retune would break. (issue #408)
        spread = engine.inside_rank_count("2H", "AS")
        # Resolve the exact server-owned return multiplier for this visible spread.
        expected_multiplier = engine.inside_return_multiplier(spread)
        # Derive the exact returned-token total from the public price.
        expected_payout = round(5 * expected_multiplier, 2)
        # Confirm outcome, priced payout, and derived net together.
        self.assertEqual(("inside", expected_payout, round(expected_payout - 5, 2)), (first["round"]["outcome"], first["round"]["payout"], first["round"]["net"]))
        # Keep the deprecated scalar and authoritative table aligned for the newest terminal round.
        self.assertEqual((expected_multiplier, expected_multiplier), (first["rules"]["inside_return_multiplier"], first["rules"]["inside_paytable"][spread]))
        # Verify replay reports the terminal result.
        self.assertTrue(second["replayed"])
        # Select wager debits and payout credits.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "ACEY_DEUCEY_WAGER_DEBIT"]
        # Select payout credits.
        credits = [event for event in self.ledger.events if event["transaction_type"] == "ACEY_DEUCEY_PAYOUT_CREDIT"]
        # Verify exactly one debit and one spread-priced payout credit.
        self.assertEqual((1, -5.0, 1, expected_payout), (len(debits), debits[0]["amount"], len(credits), credits[0]["amount"]))
        # Verify stable ledger action suffixes.
        self.assertEqual(("ad:play-win:wager", "ad:play-win:payout"), (debits[0]["details"]["acey_deucey_action_id"], credits[0]["details"]["acey_deucey_action_id"]))

    # Confirm outside and boundary ties create no zero-value credit.
    def test_losing_edge_cases_have_no_credit(self):
        # Prepare a boundary-tie loss.
        tie_round_id = self.prepared_round("2H", "AS", "2C", action_id="deal-tie")
        # Play the boundary-tie result.
        tie = self.call(f"/api/v1/games/acey-deucey/rounds/{tie_round_id}/play", {"action_id": "play-tie", "wager": 3})
        # Prepare a second outside loss after the first terminal round.
        outside_round_id = self.prepared_round("8H", "10S", "QC", action_id="deal-outside")
        # Play the outside result.
        outside = self.call(f"/api/v1/games/acey-deucey/rounds/{outside_round_id}/play", {"action_id": "play-outside", "wager": 4})
        # Verify both losing outcome keys.
        self.assertEqual(("boundary_tie", "outside"), (tie["round"]["outcome"], outside["round"]["outcome"]))
        # Verify only wager debits exist.
        self.assertEqual([], [event for event in self.ledger.events if event["transaction_type"] == "ACEY_DEUCEY_PAYOUT_CREDIT"])

    # Confirm equal or adjacent boundaries reject play before receipt, state, or ledger mutation.
    def test_unpriceable_boundaries_are_pass_only(self):
        # Prepare adjacent ranks whose inside probability is exactly zero.
        round_id = self.prepared_round("7H", "8S", "KC", action_id="deal-no-inside")
        # Snapshot the persisted prepared state before the hostile wager.
        before = self.repository.load("session-player")
        # Reject the wager at the pure price boundary.
        with self.assertRaises(ValidationError):
            # Exercise the real route and service orchestration.
            self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-no-inside", "wager": 4})
        # Prove the prepared hidden result and receipts remain byte-equivalent in data terms.
        self.assertEqual(before, self.repository.load("session-player"))
        # Prove no debit or credit reached the ledger.
        self.assertEqual([], self.ledger.events)
        # Read the pass-only round through the public response.
        visible = self.call("/api/v1/games/acey-deucey/state", method="GET")
        # Keep the old scalar field present while the authoritative table omits spread zero.
        self.assertEqual((2, False), (visible["rules"]["inside_return_multiplier"], "0" in visible["rules"]["inside_paytable"]))

    # Confirm the frozen-v1 route, envelope, pricing, matrix, and digest evidence stays exact.
    def test_spread_pricing_contract_and_compatibility_artifacts(self):
        # Read the OpenAPI text once for exact route and schema anchors.
        contract = OPENAPI_PATH.read_text(encoding="utf-8")
        # Parse the explicit compatible-patch decision record.
        compatibility = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
        # Parse the module-to-contract matrix used by repository governance.
        matrix = json.loads((ROOT / "contracts" / "compatibility" / "module-api-matrix.json").read_text(encoding="utf-8"))
        # Parse the frozen exact-byte digest map.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Preserve all four existing frozen-v1 routes, their authentication responses, and both envelopes.
        self.assertEqual((4, 4, True, True), (contract.count("  /api/v1/games/acey-deucey/"), contract.count("'401':"), "required: [ok, data]" in contract, "required: [ok, error]" in contract))
        # Require the legacy scalar, complete paytable, house edge, and pass-only boundary semantics.
        for anchor in ("inside_return_multiplier:", "inside_paytable:", "house_edge:", "zero means pass-only"):
            # Name a missing public boundary through the focused assertion.
            self.assertIn(anchor, contract)
        # Require the decision record to preserve frozen-v1 authority and the scalar field.
        self.assertEqual((True, "unchanged", True), (compatibility["compatibility"]["api_v1_frozen"], compatibility["compatibility"]["routes"], "inside_return_multiplier" in compatibility["response_rules"]["retained"]))
        # Keep the game module mapped only to its OpenAPI route contract.
        self.assertEqual(["contracts/openapi/acey_deucey.v1.yaml"], matrix["acey_deucey"])
        # Freeze the exact OpenAPI bytes in the shared digest artifact.
        self.assertEqual(hashlib.sha256(OPENAPI_PATH.read_bytes()).hexdigest(), digests["contracts/openapi/acey_deucey.v1.yaml"])
        # Freeze the exact compatibility-record bytes independently.
        self.assertEqual(hashlib.sha256(COMPATIBILITY_PATH.read_bytes()).hexdigest(), digests["contracts/compatibility/acey-deucey-spread-pricing.json"])

    # Confirm an overbet restores the original private decision for an affordable retry.
    def test_insufficient_play_wager_restores_active_round_for_safe_retry(self):
        # Restrict the authenticated player below the first attempted wager.
        self.ledger.balances["session-player"] = 5.0
        # Prepare a deterministic strict-inside result without wallet movement.
        round_id = self.prepared_round("2H", "AS", "7C", action_id="deal-overbet")
        # Attempt to reveal the result with an unaffordable wager.
        with self.assertRaises(InsufficientFundsError):
            # Exercise the real route and service rollback boundary.
            self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-overbet", "wager": 10})
        # Load the persisted document after rollback.
        restored = self.repository.load("session-player")
        # Verify the same round remains privately actionable with no terminal history.
        self.assertEqual((round_id, "wager", [], "7C"), (restored["active_round"]["round_id"], restored["active_round"]["phase"], restored["recent_rounds"], restored["active_round"]["_third_card"]))
        # Verify the failed play identity and wallet movement were both released.
        self.assertEqual((False, 5.0, []), ("play-overbet" in restored["action_receipts"], self.ledger.balances["session-player"], self.ledger.events))
        # Confirm read-only state no longer raises the prior permanent conflict.
        readable = self.call("/api/v1/games/acey-deucey/state", method="GET")
        # Verify the hidden result remains private after recovery.
        self.assertNotIn("third_card", readable["state"]["active_round"])
        # Retry the released action identity with an affordable wager.
        settled = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-overbet", "wager": 5})
        # Verify the retry settles once and creates one debit plus one spread-priced inside payout.
        expected_balance = round(5 * engine.inside_return_multiplier(engine.inside_rank_count("2H", "AS")), 2)
        # Confirm the terminal phase, the exactly-two ledger events, and the priced balance together.
        self.assertEqual(("settled", 2, expected_balance), (settled["round"]["phase"], len(self.ledger.events), self.ledger.balances["session-player"]))

    # Confirm reload repairs a legacy save-before-debit terminal row with no ledger proof.
    def test_reload_restores_legacy_pending_terminal_without_wager_proof(self):
        # Prepare one deterministic private decision.
        round_id = self.prepared_round("3H", "KS", "8C", action_id="deal-crash-window")
        # Load the stored round for a simulated process interruption.
        state = self.repository.load("session-player")
        # Resolve the active mutable round.
        round_state = state["active_round"]
        # Build the persisted terminal shape used before this recovery fix.
        play_fingerprint = request_fingerprint({"stage": "play", "round_id": round_id, "wager": 4.0})
        # Reveal and settle without committing a ledger debit.
        engine.play_round(round_state, 4, "play-crash-window", completed_at="2026-07-14T00:00:00Z", request_fingerprint=play_fingerprint)
        # Remove the new rollback field to model an already-stranded legacy document.
        round_state.pop("_third_card", None)
        # Archive the pending terminal shape exactly as the old service did.
        engine.archive_round(state, round_state)
        # Retain the old durable play receipt without ledger proof.
        state["action_receipts"]["play-crash-window"] = {"stage": "play", "round_id": round_id, "request_fingerprint": play_fingerprint}
        # Persist the simulated crash window.
        self.repository.save("session-player", state)
        # Reload through the public state endpoint to invoke recovery.
        recovered = self.call("/api/v1/games/acey-deucey/state", method="GET")
        # Verify recovery restores the same prepared round and removes terminal history.
        self.assertEqual((round_id, "wager", []), (recovered["state"]["active_round"]["round_id"], recovered["state"]["active_round"]["phase"], recovered["state"]["recent_rounds"]))
        # Verify the previously revealed card is private again.
        self.assertNotIn("third_card", recovered["state"]["active_round"])
        # Verify no balance movement or uncommitted receipt survives recovery.
        repaired = self.repository.load("session-player")
        # Assert the wallet, ledger, receipt, and restored private card all match the free deal.
        self.assertEqual((100.0, [], False, "8C"), (self.ledger.balances["session-player"], self.ledger.events, "play-crash-window" in repaired["action_receipts"], repaired["active_round"]["_third_card"]))

    # Confirm reload trusts committed debit proof without rollback or a second charge.
    def test_reload_preserves_pending_terminal_with_committed_wager_proof(self):
        # Prepare an outside result so only the wager debit needs recovery.
        round_id = self.prepared_round("3H", "KS", "AC", action_id="deal-committed-window")
        # Load the prepared document for a simulated post-debit interruption.
        state = self.repository.load("session-player")
        # Resolve the active mutable round.
        round_state = state["active_round"]
        # Bind the play to its exact round and normalized wager.
        play_fingerprint = request_fingerprint({"stage": "play", "round_id": round_id, "wager": 4.0})
        # Build terminal state before applying the matching debit proof.
        engine.play_round(round_state, 4, "play-committed-window", completed_at="2026-07-14T00:00:00Z", request_fingerprint=play_fingerprint)
        # Archive the pending terminal shape.
        engine.archive_round(state, round_state)
        # Retain its durable semantic receipt.
        state["action_receipts"]["play-committed-window"] = {"stage": "play", "round_id": round_id, "request_fingerprint": play_fingerprint}
        # Persist the crash-recoverable terminal state.
        self.repository.save("session-player", state)
        # Commit the exact append-only wager movement without saving its state marker.
        self.ledger.apply_once(player_id="session-player", signed_amount=-4.0, transaction_type="ACEY_DEUCEY_WAGER_DEBIT", round_id=round_id, action_key="ad:play-committed-window:wager", request_fingerprint=play_fingerprint, details={"stage": "play_wager", "wager": 4.0, "left_card": "3H", "right_card": "KS"})
        # Reload through the public route to reconcile the missing marker.
        recovered = self.call("/api/v1/games/acey-deucey/state", method="GET")
        # Verify committed terminal state remains archived and never returns active.
        self.assertEqual((None, "settled", "complete", 96.0), (recovered["state"]["active_round"], recovered["state"]["recent_rounds"][0]["phase"], recovered["state"]["recent_rounds"][0]["wager_status"], self.ledger.balances["session-player"]))
        # Inspect the repaired private document after proof reconciliation.
        repaired = self.repository.load("session-player")
        # Verify obsolete rollback material is discarded after proof becomes authoritative.
        self.assertNotIn("_third_card", repaired["recent_rounds"][0])
        # Replay the exact public play request after recovery.
        replayed = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-committed-window", "wager": 4})
        # Verify the same terminal result returns with no second ledger movement.
        self.assertEqual((True, 1, 96.0), (replayed["replayed"], len(self.ledger.events), self.ledger.balances["session-player"]))

    # Confirm pass closes the round without wallet movement or result reveal.
    def test_pass_has_no_ledger_movement_and_no_reveal(self):
        # Prepare an active deal with a hidden third card.
        round_id = self.prepared_round("3H", "JS", "7C", action_id="deal-pass")
        # Pass the round.
        result = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/pass", {"action_id": "pass-1"})
        # Verify pass terminal state.
        self.assertEqual(("passed", "passed"), (result["round"]["phase"], result["round"]["outcome"]))
        # Verify the third card remains unrevealed.
        self.assertNotIn("third_card", result["round"])
        # Verify no ledger events were created.
        self.assertEqual([], self.ledger.events)


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
