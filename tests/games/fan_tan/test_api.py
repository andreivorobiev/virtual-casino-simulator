# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared-settlement, recovery, and API compatibility tests for #869."""

# Import deep-copy support so fake persistence models JSON boundaries.
import copy
# Import JSON encoding for real provider-state fixtures.
import json
# Import process environments for isolated provider workers.
import os
# Import filesystem paths for task-owned rendezvous gates.
from pathlib import Path
# Import child-process execution for true cross-process races.
import subprocess
# Import the active interpreter for exact worker parity.
import sys
# Import temporary directories for residue-free provider evidence.
import tempfile
# Import monotonic time for bounded rendezvous polling.
import time
# Import the dependency-free standard test runner.
import unittest

# Import the public conflict error asserted at retry boundaries.
from casino.errors import ConflictError
# Import the isolated game API and pure rules.
from casino.games.fan_tan import api, engine
# Import the shared-backed service under test.
from casino.games.fan_tan.service import FanTanService


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
    def update(self, game_id, player_id, mutator, factory):
        # Require the correct game namespace at every test mutation boundary.
        if game_id != "fan_tan":
            # Fail the fixture before it can mask a cross-game write.
            raise AssertionError(f"unexpected game id {game_id}")
        # Load current provider state or one fresh game default.
        current = copy.deepcopy(self.documents.get(player_id, factory()))
        # Apply the production-shaped callback to provider-current state.
        updated = mutator(current)
        # Persist a detached result to model JSON storage.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return a detached authoritative publication.
        return copy.deepcopy(updated)


# Persist one selected provider transition and then simulate a lost response.
class PersistThenFailRepository(MemoryRepository):
    # Capture the exact authoritative-state predicate for one crash boundary.
    def __init__(self, predicate):
        # Initialize ordinary detached provider storage first.
        super().__init__()
        # Retain the bounded state predicate supplied by the focused test.
        self._predicate = predicate
        # Arm exactly one post-persistence response failure.
        self._armed = True

    # Commit the provider-current mutation before optionally losing its response.
    def update(self, game_id, player_id, mutator, factory):
        # Persist through the ordinary in-memory provider callback boundary.
        authoritative = super().update(game_id, player_id, mutator, factory)
        # Fail once only when the requested crash boundary is now durable.
        if self._armed and self._predicate(authoritative):
            # Consume the one-shot fault before surfacing it.
            self._armed = False
            # Model a provider write whose response is lost after commit.
            raise RuntimeError("simulated lost provider response")
        # Return normal detached authority for every other transition.
        return authoritative


# Capture game routes registered by the isolated adapter.
class FakeRouter:
    # Initialize empty route maps for GET and POST handlers.
    def __init__(self):
        # Store GET handlers by route pattern.
        self.gets = {}
        # Store POST handlers by route pattern.
        self.posts = {}

    # Register one GET handler using the production decorator contract.
    def get(self, path):
        # Return a decorator that records the handler.
        def decorator(handler):
            # Store the handler for focused assertions.
            self.gets[path] = handler
            # Return the handler unchanged.
            return handler
        # Return the decorator to the caller.
        return decorator

    # Register one POST handler using the production decorator contract.
    def post(self, path):
        # Return a decorator that records the handler.
        def decorator(handler):
            # Store the handler for focused assertions.
            self.posts[path] = handler
            # Return the handler unchanged.
            return handler
        # Return the decorator to the caller.
        return decorator


# Provide an in-memory apply-once gateway with production-shaped evidence.
class FakeLedgerGateway:
    # Initialize balances, immutable events, and failure controls.
    def __init__(self, balances=None):
        # Store deterministic fake wallets without touching shared player data.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0, "player-a": 100.0, "player-b": 100.0}
        # Store events by deterministic action key.
        self.events = {}
        # Retain every apply-once invocation, including safe replays.
        self.calls = []
        # Hold one-shot pre-commit failures by action suffix.
        self.fail_before = set()
        # Hold one-shot lost responses after immutable publication.
        self.fail_after = set()

    # Commit or recover one signed game action.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Record the public action request for debit and credit count assertions.
        self.calls.append({"player_id": player_id, "signed_amount": signed_amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "request_fingerprint": request_fingerprint, "details": copy.deepcopy(details)})
        # Resolve the bounded action role once for failure injection.
        suffix = action_key.rsplit(":", 1)[-1]
        # Fail once before publication when a test arms this exact role.
        if suffix in self.fail_before:
            # Consume the one-shot failure so an explicit retry can proceed.
            self.fail_before.remove(suffix)
            # Model a provider rejection with no committed movement.
            raise RuntimeError("simulated pre-commit ledger failure")
        # Return the original event when this deterministic action already committed.
        if action_key in self.events:
            # Read immutable proof once for exact conflict checks.
            existing = self.events[action_key]
            # Reject one identity reused with different money or semantics.
            if existing["player_id"] != player_id or existing["round_id"] != round_id or existing["transaction_type"] != transaction_type or existing["amount"] != signed_amount or existing["details"]["request_fingerprint"] != request_fingerprint:
                # Match the production gateway's fail-closed conflict boundary.
                raise ConflictError("Fake ledger action dimensions conflict")
            # Preserve the same event identity and report replay recovery.
            return copy.deepcopy(existing), True
        # Reject a fake debit that would overdraw the isolated wallet.
        if signed_amount < 0 and self.balances[player_id] + signed_amount < 0:
            # Surface one ordinary pre-commit wallet failure.
            raise RuntimeError("insufficient fake balance")
        # Apply the signed movement once to the isolated fake wallet.
        self.balances[player_id] = round(self.balances[player_id] + signed_amount, 2)
        # Build immutable production-shaped event evidence.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": "fan_tan", "round_id": round_id, "details": copy.deepcopy(details), "ts": "2026-07-14T00:00:00Z"}
        # Persist exact proof under the deterministic action identity.
        self.events[action_key] = copy.deepcopy(event)
        # Lose the first response only after the immutable event exists.
        if suffix in self.fail_after:
            # Consume the one-shot response loss.
            self.fail_after.remove(suffix)
            # Model transport loss after durable commit.
            raise RuntimeError("simulated lost ledger response")
        # Return detached proof and a new-action marker.
        return copy.deepcopy(event), False

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
            # Surface a conflict instead of satisfying proof with unrelated data.
            raise ConflictError("Fake ledger proof dimensions conflict")
        # Return detached immutable proof like the production adapter.
        return copy.deepcopy(event)


# Cover frozen routes, shared lifecycle recovery, and provider-current publication.
class FanTanApiTests(unittest.TestCase):
    # Build deterministic dependencies for each test.
    def setUp(self):
        # Retain provider authority for direct private-state assertions.
        self.repository = MemoryRepository()
        # Retain fake ledger authority and wallet balances.
        self.ledger = FakeLedgerGateway()
        # Select the minimum pile count so residue one wins deterministically.
        offsets = iter([0])
        # Build the service with no filesystem or ambient wallet access.
        self.service = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: next(offsets), clock=lambda: "2026-07-14T00:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})

    # Register the isolated handlers and invoke one trusted-session route.
    def call(self, path, body, *, player_id="session-player"):
        # Capture route registration without opening a listener.
        router = FakeRouter()
        # Register the service instance under the frozen v1 patterns.
        api.register(router, service=self.service)
        # Dispatch GET or POST with hostile caller ids ignored by trusted context.
        handler = router.gets[path] if path.endswith("/state") else router.posts[path]
        # Invoke the raw handler with the authenticated player binding.
        return handler(body, {"player_id": "other-player"}, context={"bound_player_id": player_id})

    # Confirm preparation is provider-current, private, and never redraws on retry.
    def test_preparation_preserves_siblings_and_never_redraws(self):
        # Track every deterministic pile-count selection.
        draws = []
        # Return one approved offset through the injectable seam.
        values = iter([7])
        # Build one preparation-only service over shared provider authority.
        service = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: draws.append(span) or next(values), clock=lambda: "prepared", get_player=lambda player_id: {"player_id": player_id, "balance": 100.0})
        # Seed an unrelated provider sibling before preparation.
        self.repository.documents["player-a"] = {"game": "fan_tan", "recent_rounds": [], "atomic_markers": ["sibling"]}
        # Normalize the exact request identity and wager once.
        request_id, wagers = "prepare-once", engine.normalize_wagers({"4": 1})
        # Derive exact shared lifecycle dimensions.
        round_id, fingerprint = engine.round_id_for("player-a", request_id), engine.wager_fingerprint(wagers)
        # Persist one private preparation.
        first = service.prepare(player_id="player-a", request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=wagers)
        # Recover the exact same provider-owned preparation.
        second = service.prepare(player_id="player-a", request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=wagers)
        # Require one bounded draw, exact pile recovery, and replay classification.
        self.assertEqual(([32], 56, 56, False, True), (draws, first["entropy"], second["entropy"], first["replayed"], second["replayed"]))
        # Preserve the unrelated sibling beside private active state.
        self.assertEqual(["sibling"], self.repository.documents["player-a"]["atomic_markers"])
        # Keep the prepared pile out of the frozen nested public state response.
        self.assertNotIn("active_round", service.state("player-a")["state"])

    # Prove two real processes serialize one preparation and one entropy owner.
    def test_real_process_same_request_preparation_serializes_one_entropy_owner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / "fan_tan" / "player-a.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON with one unrelated sibling marker.
            state_path.write_text(json.dumps({"game": "fan_tan", "recent_rounds": [], "atomic_markers": ["seed"]}, sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind every child to disposable state and this exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one worker that waits before contending for provider authority.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.games.fan_tan import engine
from casino.games.fan_tan.service import FanTanService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
action_id = sys.argv[3]
ready.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not release.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not release.exists():
    raise RuntimeError('release gate timeout')
draws = []
def draw(span):
    draws.append(1)
    return 7
game = FanTanService(randbelow=draw)
wagers = engine.normalize_wagers({'4': 1})
result = game.prepare(player_id='player-a', request_id=action_id, round_id=engine.round_id_for('player-a', action_id), fingerprint=engine.wager_fingerprint(wagers), wager=wagers)
print('PASS:' + str(len(draws)) + ':' + str(result['entropy']) + ':' + str(int(result['replayed'])))
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start two contenders for the same provider-owned preparation.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), "atomic-preparation"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Retain process and gate ownership.
                workers.append((process, ready_path, release_path))
            # Bound the pre-preparation rendezvous.
            deadline = time.monotonic() + 10
            # Wait until both workers are ready to contend for authority.
            while not all(ready.exists() for _process, ready, _release in workers) and time.monotonic() < deadline:
                # Stop early if either worker failed before readiness.
                if any(process.poll() is not None for process, _ready, _release in workers):
                    # Leave polling for the diagnostic assertion below.
                    break
                # Yield briefly without starting another request.
                time.sleep(0.01)
            # Require both contenders before publishing a concurrent sibling.
            self.assertTrue(all(ready.exists() for _process, ready, _release in workers))
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.fan_tan import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('fan_tan', 'player-a', add, engine.default_state)\n"
            # Commit the sibling before either preparation enters provider state.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release both contenders without choosing a winner locally.
            for _process, _ready, release in workers:
                # Open each bounded gate before collecting either result.
                release.write_text("go", encoding="utf-8")
            # Collect both provider-serialized preparation results.
            outputs = [process.communicate(timeout=20) for process, _ready, _release in workers]
            # Require both processes to return the exact same authoritative pile.
            self.assertTrue(all(process.returncode == 0 and output.strip().startswith("PASS:") for (process, _ready, _release), (output, _error) in zip(workers, outputs)), outputs)
            # Split local draw counts, pile counts, and replay flags from both workers.
            evidence = [output.strip().split(":") for output, _error in outputs]
            # Require exactly one pile-count entropy owner and one provider replay.
            self.assertEqual(([0, 1], ["56", "56"], [0, 1]), (sorted(int(row[1]) for row in evidence), sorted(row[2] for row in evidence), sorted(int(row[3]) for row in evidence)))
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one active winner, sibling preservation, and no terminal fabrication.
            self.assertEqual((persisted["active_round"]["action_id"], persisted["active_round"]["pile_count"], persisted["recent_rounds"], persisted["atomic_markers"]), ("atomic-preparation", 56, [], ["seed", "concurrent"]))

    # Confirm frozen route projections and authenticated session binding.
    def test_session_binding_frozen_envelopes_and_exact_replay(self):
        # Execute one residue-one win with hostile caller-supplied identities.
        first = self.call("/api/v1/games/fan-tan/rounds", {"player_id": "other-player", "action_id": "round-1", "wagers": {"1": 5}})
        # Replay the exact request through the same trusted session.
        second = self.call("/api/v1/games/fan-tan/rounds", {"player_id": "other-player", "action_id": "round-1", "wagers": {"1": 5}})
        # Read the frozen state projection after settlement.
        state = self.call("/api/v1/games/fan-tan/state", {})
        # Require exact top-level action and state keys without helper leakage.
        self.assertEqual(({"round", "replayed", "ledger"}, {"game", "state", "rules", "outcomes"}), (set(first), set(state)))
        # Verify ownership follows the authenticated session only.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance is untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the exact public round is replayed byte-for-byte as a dict.
        self.assertEqual(first["round"], second["round"])
        # Verify one debit, one credit, residue return, balance, and replay.
        self.assertEqual((2, 20.0, 115.0, True), (len(self.ledger.events), first["round"]["total_return"], self.ledger.balances["session-player"], second["replayed"]))

    # Confirm an uncommitted wager failure clears private preparation.
    def test_precommit_wager_failure_clears_preparation(self):
        # Arm one rejection before the wager action becomes immutable.
        self.ledger.fail_before.add("wager")
        # Attempt one valid covered-symbol request through the public service.
        with self.assertRaisesRegex(RuntimeError, "pre-commit"):
            # Require the original provider error to surface unchanged.
            self.service.play("session-player", {"action_id": "precommit", "wagers": {"1": 1}})
        # Require safe cleanup to leave no invented active or terminal result.
        self.assertEqual(engine.default_state(), self.repository.documents["session-player"])
        # Retry explicitly with a fresh deterministic residue-one pile.
        retry_offsets = iter([0])
        retry = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: next(retry_offsets), clock=lambda: "2026-07-14T00:00:01Z", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Settle the explicit retry after the transient failure.
        recovered = retry.play("session-player", {"action_id": "precommit", "wagers": {"1": 1}})
        # Require exact pile count, one terminal row, and two movements.
        self.assertEqual((49, 1, 2), (recovered["round"]["pile_count"], len(self.repository.documents["session-player"]["recent_rounds"]), len(self.ledger.events)))

    # Confirm a lost wager response retains committed pile count for recovery.
    def test_lost_wager_response_recovers_exact_committed_result(self):
        # Arm one response loss after the debit event becomes immutable.
        self.ledger.fail_after.add("wager")
        # Execute one covered-symbol request whose first response is lost.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve the original transport-style error for the caller.
            self.service.play("session-player", {"action_id": "lost-wager", "wagers": {"1": 1}})
        # Require prepared pile count to remain durable beside the committed debit.
        self.assertEqual((49, "prepared", 1), (self.repository.documents["session-player"]["active_round"]["pile_count"], self.repository.documents["session-player"]["active_round"]["phase"], len(self.ledger.events)))
        # Recover with entropy that would visibly differ if redrawn.
        recovering = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: 31, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Retry the exact public request identity once.
        result = recovering.play("session-player", {"action_id": "lost-wager", "wagers": {"1": 1}})
        # Require exact pile recovery, replay evidence, and no duplicate movement.
        self.assertEqual((49, True, 2), (result["round"]["pile_count"], result["replayed"], len(self.ledger.events)))

    # Confirm a lost settlement response recovers one immutable credit.
    def test_lost_settlement_response_recovers_without_duplicate_credit(self):
        # Arm one response loss after the positive settlement credit commits.
        self.ledger.fail_after.add("settlement")
        # Execute one residue-one request through the public service.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve the first failed response while keeping both events durable.
            self.service.play("session-player", {"action_id": "lost-credit", "wagers": {"1": 1}})
        # Require deterministic result intent and both exact movements.
        self.assertEqual((4.0, "pending", 2), (self.repository.documents["session-player"]["active_round"]["total_return"], self.repository.documents["session-player"]["active_round"]["settlement_status"], len(self.ledger.events)))
        # Retry the identical request to reconstruct missing state and response.
        result = self.service.play("session-player", {"action_id": "lost-credit", "wagers": {"1": 1}})
        # Require one terminal round, explicit replay, and exactly two events.
        self.assertEqual((4.0, True, 2, 1), (result["round"]["total_return"], result["replayed"], len(self.ledger.events), len(self.repository.documents["session-player"]["recent_rounds"])))

    # Confirm every durable lifecycle write can lose its response and recover once.
    def test_provider_write_crash_boundaries_converge(self):
        # Name exact provider states after debit, result, credit, finalization, and archival.
        boundaries = {
            "post-debit": lambda state: isinstance(state.get("active_round"), dict) and state["active_round"].get("phase") == "settling" and "total_return" not in state["active_round"],
            "post-result": lambda state: isinstance(state.get("active_round"), dict) and state["active_round"].get("settlement_status") == "pending" and "settlement_ledger_id" not in state["active_round"],
            "post-credit": lambda state: isinstance(state.get("active_round"), dict) and bool(state["active_round"].get("settlement_ledger_id")),
            "post-finalize": lambda state: isinstance(state.get("active_round"), dict) and state["active_round"].get("phase") == "settled",
            "post-archive": lambda state: "active_round" not in state and len(state.get("recent_rounds", [])) == 1,
        }
        # Exercise every durable state boundary independently.
        for boundary, predicate in boundaries.items():
            # Label failures by the exact crash schedule under test.
            with self.subTest(boundary=boundary):
                # Create isolated provider and ledger authority for this schedule.
                repository, ledger = PersistThenFailRepository(predicate), FakeLedgerGateway()
                # Draw one residue-one pile before losing one provider response.
                values = iter([0])
                # Build the service against this isolated schedule.
                service = FanTanService(ledger_gateway=ledger, state_loader=repository.load, state_updater=repository.update, randbelow=lambda span: next(values), clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]})
                # Require the selected persisted transition to surface response loss.
                with self.assertRaisesRegex(RuntimeError, "lost provider response"):
                    # Execute one stable request identity per isolated schedule.
                    service.play("player-a", {"action_id": boundary, "wagers": {"1": 1}})
                # Resume with entropy that would redraw if provider proof were ignored.
                recovering = FanTanService(ledger_gateway=ledger, state_loader=repository.load, state_updater=repository.update, randbelow=lambda span: 31, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]})
                # Recover the exact interrupted public request.
                result = recovering.play("player-a", {"action_id": boundary, "wagers": {"1": 1}})
                # Require exact pile, one row, no active residue, and no duplicate money.
                self.assertEqual((49, 1, False, 2), (result["round"]["pile_count"], len(repository.documents["player-a"]["recent_rounds"]), "active_round" in repository.documents["player-a"], len(ledger.events)))

    # Confirm a historical debit proof recovers without canonical helper fields.
    def test_legacy_debit_proof_recovery_uses_event_time_and_pile_count(self):
        # Define one stable historical request and its normalized wager.
        request = {"action_id": "legacy-proof", "wagers": {"1": 1}}
        # Normalize the exact wager before constructing immutable proof.
        wagers = engine.normalize_wagers(request["wagers"])
        # Derive the established player-scoped round identity.
        round_id = engine.round_id_for("player-a", request["action_id"])
        # Store the semantic request fingerprint once.
        fingerprint = engine.wager_fingerprint(wagers)
        # Commit a pre-migration debit containing only historical field names.
        self.ledger.apply_once(player_id="player-a", signed_amount=-1.0, transaction_type="FAN_TAN_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", request_fingerprint=fingerprint, details={"action_id": request["action_id"], "request_fingerprint": fingerprint, "wagers": wagers, "pile_count": 49})
        # Build recovery whose fresh entropy and clock would visibly differ.
        recovering = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: 31, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Recover through the ordinary public service request.
        result = recovering.play("player-a", request)
        # Require committed pile, immutable event time, replay, and one new credit only.
        self.assertEqual((49, "2026-07-14T00:00:00Z", True, 2), (result["round"]["pile_count"], result["round"]["settled_at"], result["replayed"], len(self.ledger.events)))

    # Confirm terminal history is direct, oldest-to-newest, and bounded to one hundred.
    def test_history_retains_newest_one_hundred_direct_rounds(self):
        # Use residue-two piles against residue-one wagers so each round has one debit.
        service = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: 1, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Give the fake wallet enough tokens for the complete history exercise.
        self.ledger.balances["player-a"] = 1000000.0
        # Publish five more rounds than the documented history bound.
        for index in range(105):
            # Use one stable caller identity per completed request.
            service.play("player-a", {"action_id": f"history-{index:03d}", "wagers": {"1": 1}})
        # Read exact direct provider rows after bounded archival.
        rows = self.repository.documents["player-a"]["recent_rounds"]
        # Require direct oldest-to-newest rows for indices five through one hundred four.
        self.assertEqual((100, "history-005", "history-104", False), (len(rows), rows[0]["action_id"], rows[-1]["action_id"], any("public" in row for row in rows)))
        # Require one debit-only event per losing round without hidden credits.
        self.assertEqual(105, len(self.ledger.events))

    # Confirm changed retries fail closed before another movement.
    def test_conflicting_retry_rejected(self):
        # Commit one valid play.
        self.service.play("player-a", {"action_id": "round-conflict", "wagers": {"1": 1}})
        # Reject reuse with changed wagers.
        with self.assertRaises(ConflictError):
            # Exercise semantic request-id conflict.
            self.service.play("player-a", {"action_id": "round-conflict", "wagers": {"2": 1}})
        # Verify no extra debit was created.
        self.assertEqual(1, len([event for event in self.ledger.events.values() if event["transaction_type"] == "FAN_TAN_WAGER_DEBIT"]))

    # Confirm a losing symbol creates no forbidden zero-value credit row.
    def test_losing_play_creates_only_wager_debit(self):
        # Build a service that deterministically selects a residue-two pile.
        losing = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda span: 1, clock=lambda: "2026-07-14T00:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Wager only residue one so pile fifty has no return.
        result = losing.play("player-a", {"action_id": "loss-1", "wagers": {"1": 1}})
        # Require zero return and absent settlement credit evidence.
        self.assertEqual((0.0, None), (result["round"]["total_return"], result["ledger"]["settlement"]))
        # Require only the aggregate wager debit to exist.
        self.assertEqual(1, len(self.ledger.events))

    # Confirm state history remains isolated by authenticated player.
    def test_player_state_isolation(self):
        # Settle one round for the first authenticated player.
        self.service.play("player-a", {"action_id": "isolated", "wagers": {"1": 1}})
        # Read untouched state for another authenticated player.
        other = self.service.state("player-b")
        # Require no cross-player round history in the second response.
        self.assertEqual([], other["state"]["recent_rounds"])

    # Confirm source topology contains only the shared helper boundary.
    def test_service_source_uses_one_shared_coordinator(self):
        # Resolve exact service bytes from this checkout.
        source = Path(__file__).resolve().parents[3] / "casino" / "games" / "fan_tan" / "service.py"
        # Read the source inspected by central governance.
        text = source.read_text(encoding="utf-8")
        # Require one construction and no legacy direct settlement seams.
        self.assertEqual((1, False, False, False, False), (text.count("SimpleWagerGame("), "GameSettlementGateway" in text, "CoreLedgerGateway" in text, ".apply_once(" in text, "_ATOMIC_BASELINE_KEY" in text))


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
