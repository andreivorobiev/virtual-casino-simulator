# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared-settlement, recovery, and API compatibility tests for #865."""

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

# Import public conflict and validation errors asserted at route boundaries.
from casino.errors import ConflictError, ValidationError
# Import the isolated game API and pure rules.
from casino.games.over_under_7 import api, engine
# Import the shared-backed service under test.
from casino.games.over_under_7.service import OverUnder7Service
# Import the real router to exercise frozen v1 route patterns.
from casino.router import Router


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
        if game_id != engine.GAME_ID:
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
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Record the public action request for debit and credit count assertions.
        self.calls.append({"player_id": player_id, "amount": amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "request_fingerprint": request_fingerprint, "details": copy.deepcopy(details)})
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
            if existing["player_id"] != player_id or existing["round_id"] != round_id or existing["transaction_type"] != transaction_type or existing["amount"] != amount or existing["details"]["request_fingerprint"] != request_fingerprint:
                # Match the production gateway's fail-closed conflict boundary.
                raise ConflictError("Fake ledger action dimensions conflict")
            # Preserve the same event identity and report replay recovery.
            return copy.deepcopy(existing), True
        # Calculate the candidate wallet balance before committing the event.
        candidate = round(self.balances[player_id] + amount, 2)
        # Reject an aggregate wager that would overdraw the fake wallet.
        if candidate < 0:
            # Preserve provider state and ledger bytes on rejection.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake wallet movement exactly once.
        self.balances[player_id] = candidate
        # Build one production-shaped ledger event with complete audit dimensions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "game": engine.GAME_ID, "round_id": round_id, "transaction_type": transaction_type, "amount": amount, "ts": "2026-07-14T00:00:00Z", "details": {**copy.deepcopy(details), "over_under_7_action_key": action_key, "request_fingerprint": request_fingerprint}}
        # Persist the committed event under its unique action identity.
        self.events[action_key] = event
        # Lose one response only after the immutable event exists.
        if suffix in self.fail_after:
            # Consume the one-shot fault before surfacing the transport-style error.
            self.fail_after.remove(suffix)
            # Force the caller to recover from exact committed proof.
            raise RuntimeError("simulated lost ledger response")
        # Report that this call created the event.
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


# Verify route binding, retries, private lifecycle, and exactly-once recovery.
class OverUnder7ApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and ledger events.
        self.ledger = FakeLedgerGateway()
        # Build deterministic exact-seven dice values.
        self.dice_values = iter([2, 3])
        # Build the isolated service without filesystem or ambient randomness.
        self.service = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda _sides: next(self.dice_values), clock=lambda: "2026-07-14T00:00:00Z")
        # Register only game-owned routes on the real router.
        self.router = Router()
        # Inject the focused service.
        api.register(self.router, service=self.service)
        # Store the authenticated context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch through the shared router.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so requests remain isolated.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Confirm provider-current preparation is idempotent and preserves siblings.
    def test_preparation_preserves_sibling_and_never_redraws(self):
        # Seed unrelated provider-owned metadata before entropy preparation.
        self.repository.documents["player-a"] = {"game": engine.GAME_ID, "recent_rounds": [], "atomic_markers": ["sibling"]}
        # Count each bounded entropy request across both identical preparations.
        draws = []
        # Build one service whose dice source records each requested span.
        service = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda sides: draws.append(sides) or 2, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
        # Normalize the exact wager used by the lifecycle seam.
        wagers = engine.normalize_wagers({"under": 1})
        # Bind one stable fingerprint and round identity.
        fingerprint = engine.wager_fingerprint(wagers)
        # Prepare the action for the first time through provider-current state.
        first = service.prepare(player_id="player-a", request_id="prepared", round_id=engine.round_id_for("player-a", "prepared"), fingerprint=fingerprint, wager=wagers)
        # Repeat the identical preparation without allowing another draw.
        second = service.prepare(player_id="player-a", request_id="prepared", round_id=engine.round_id_for("player-a", "prepared"), fingerprint=fingerprint, wager=wagers)
        # Require one two-die draw, exact replay, and sibling preservation.
        self.assertEqual(([6, 6], [3, 3], [3, 3], False, True, ["sibling"]), (draws, first["entropy"], second["entropy"], first["replayed"], second["replayed"], self.repository.documents["player-a"]["atomic_markers"]))
        # Keep prepared dice private from the frozen state payload.
        self.assertEqual({"recent_rounds": []}, service.state("player-a")["state"])

    # Prove fresh processes serialize preparation before entropy is drawn.
    def test_fresh_process_preparation_race_has_one_entropy_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / engine.GAME_ID / "player-a.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps({"game": engine.GAME_ID, "recent_rounds": [], "atomic_markers": ["seed"]}, sort_keys=True), encoding="utf-8")
            # Copy the environment before selecting the isolated JSON provider.
            environment = os.environ.copy()
            # Bind every child to disposable state and this exact checkout.
            environment.update({"CASINO_STORAGE_PROVIDER": "json", "CASINO_DATA_DIR": str(data_root), "CASINO_LOG_DIR": str(Path(temporary) / "logs"), "PYTHONPATH": str(repository_root)})
            # Define one worker that waits before entering provider-current preparation.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.games.over_under_7 import engine
from casino.games.over_under_7.service import OverUnder7Service
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
def randbelow(span):
    draws.append(span)
    return 5
game = OverUnder7Service(state_loader=lambda player_id: load_player_game_state('over_under_7', player_id, engine.default_state), state_updater=update_player_game_state, randbelow=randbelow, clock=lambda: '2026-08-15T01:00:00Z', get_player=lambda player_id: {'player_id': player_id, 'balance': 100})
wagers = engine.normalize_wagers({'under': 1})
result = game.prepare(player_id='player-a', request_id=action_id, round_id=engine.round_id_for('player-a', action_id), fingerprint=engine.wager_fingerprint(wagers), wager=wagers)
print('PASS:' + str(len(draws)) + ':' + ','.join(str(face) for face in result['entropy']) + ':' + str(int(result['replayed'])))
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
                # Yield briefly without starting another action.
                time.sleep(0.01)
            # Require both contenders before publishing a concurrent sibling.
            self.assertTrue(all(ready.exists() for _process, ready, _release in workers))
            # Define one unrelated provider-atomic sibling update.
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.over_under_7 import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('over_under_7', 'player-a', add, engine.default_state)\n"
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
            # Require both processes to return the exact same authoritative dice.
            self.assertTrue(all(process.returncode == 0 and output.strip().startswith("PASS:") for (process, _ready, _release), (output, _error) in zip(workers, outputs)), outputs)
            # Split local draw counts, dice, and replay flags from both workers.
            evidence = [output.strip().split(":") for output, _error in outputs]
            # Require exactly one two-die entropy owner and one provider replay.
            self.assertEqual(([0, 2], ["6,6", "6,6"], [0, 1]), (sorted(int(row[1]) for row in evidence), sorted(row[2] for row in evidence), sorted(int(row[3]) for row in evidence)))
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one active winner, sibling preservation, and no terminal fabrication.
            self.assertEqual((persisted["active_round"]["action_id"], persisted["active_round"]["dice"], persisted["recent_rounds"], persisted["atomic_markers"]), ("atomic-preparation", [6, 6], [], ["seed", "concurrent"]))

    # Confirm hostile player ids cannot override the authenticated session.
    def test_session_binding_and_exact_replay(self):
        # Play once with hostile caller-supplied identities.
        first = self.call("/api/v1/games/over-under-7/plays?player_id=other-player", {"player_id": "other-player", "action_id": "play-1", "wagers": {"seven": 5}})
        # Replay the exact action.
        second = self.call("/api/v1/games/over-under-7/plays?player_id=other-player", {"player_id": "other-player", "action_id": "play-1", "wagers": {"seven": 5}})
        # Verify ownership follows the authenticated session only.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance is untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the exact public round is replayed byte-for-byte as a dict.
        self.assertEqual(first["round"], second["round"])
        # Verify one debit and one settlement credit exist.
        self.assertEqual((1, 1), (len([event for event in self.ledger.events.values() if event["transaction_type"] == "OVER_UNDER_7_WAGER_DEBIT"]), len([event for event in self.ledger.events.values() if event["transaction_type"] == "OVER_UNDER_7_SETTLEMENT_CREDIT"])))
        # Verify exact-seven return used stake plus 4:1 net.
        self.assertEqual((25.0, 120.0, True), (first["round"]["total_return"], self.ledger.balances["session-player"], second["replayed"]))

    # Confirm an uncommitted wager failure clears private preparation.
    def test_precommit_wager_failure_clears_preparation(self):
        # Arm one rejection before the wager action becomes immutable.
        self.ledger.fail_before.add("wager")
        # Attempt one valid exact-seven request through the public service.
        with self.assertRaisesRegex(RuntimeError, "pre-commit"):
            # Require the original provider error to surface unchanged.
            self.service.play("session-player", {"action_id": "precommit", "wagers": {"seven": 1}})
        # Require safe cleanup to leave no invented active or terminal result.
        self.assertEqual(engine.default_state(), self.repository.documents["session-player"])
        # Retry explicitly with fresh deterministic exact-seven entropy.
        retry_values = iter([2, 3])
        retry = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda _sides: next(retry_values), clock=lambda: "2026-07-14T00:00:01Z")
        # Settle the explicit retry after the transient failure.
        recovered = retry.play("session-player", {"action_id": "precommit", "wagers": {"seven": 1}})
        # Require exact dice, one terminal row, and two movements.
        self.assertEqual(([3, 4], 1, 2), (recovered["round"]["dice"], len(recovered["state"]["recent_rounds"]), len(self.ledger.events)))

    # Confirm a lost wager response retains committed dice for recovery.
    def test_lost_wager_response_recovers_exact_committed_result(self):
        # Arm one response loss after the debit event becomes immutable.
        self.ledger.fail_after.add("wager")
        # Execute one exact-seven request whose first response is lost.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve the original transport-style error for the caller.
            self.service.play("session-player", {"action_id": "lost-wager", "wagers": {"seven": 1}})
        # Require prepared dice to remain durable beside the committed debit.
        self.assertEqual(([3, 4], "prepared", 1), (self.repository.documents["session-player"]["active_round"]["dice"], self.repository.documents["session-player"]["active_round"]["phase"], len(self.ledger.events)))
        # Recover with entropy that would visibly differ if redrawn.
        recovering = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda _sides: 5, clock=lambda: "later")
        # Retry the exact public action identity once.
        result = recovering.play("session-player", {"action_id": "lost-wager", "wagers": {"seven": 1}})
        # Require exact dice recovery, replay evidence, and no duplicate movement.
        self.assertEqual(([3, 4], True, 2), (result["round"]["dice"], result["replayed"], len(self.ledger.events)))

    # Confirm a lost settlement response recovers one immutable credit.
    def test_lost_settlement_response_recovers_without_duplicate_credit(self):
        # Arm one response loss after the positive settlement credit commits.
        self.ledger.fail_after.add("settlement")
        # Execute one exact-seven action through the public service.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve the first failed response while keeping both events durable.
            self.service.play("session-player", {"action_id": "lost-credit", "wagers": {"seven": 1}})
        # Require deterministic result intent and both exact movements.
        self.assertEqual((5.0, "pending", 2), (self.repository.documents["session-player"]["active_round"]["total_return"], self.repository.documents["session-player"]["active_round"]["settlement_status"], len(self.ledger.events)))
        # Retry the identical action to reconstruct missing state and response.
        result = self.service.play("session-player", {"action_id": "lost-credit", "wagers": {"seven": 1}})
        # Require one terminal round, explicit replay, and exactly two events.
        self.assertEqual((5.0, True, 2, 1), (result["round"]["total_return"], result["replayed"], len(self.ledger.events), len(result["state"]["recent_rounds"])))

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
                # Draw one exact-seven result before losing one provider response.
                values = iter([2, 3])
                # Build the service against this isolated schedule.
                service = OverUnder7Service(ledger_gateway=ledger, state_loader=repository.load, state_updater=repository.update, randbelow=lambda _sides: next(values), clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]})
                # Require the selected persisted transition to surface response loss.
                with self.assertRaisesRegex(RuntimeError, "lost provider response"):
                    # Execute one stable action identity per isolated schedule.
                    service.play("player-a", {"action_id": boundary, "wagers": {"seven": 1}})
                # Resume with entropy that would redraw if provider proof were ignored.
                recovering = OverUnder7Service(ledger_gateway=ledger, state_loader=repository.load, state_updater=repository.update, randbelow=lambda _sides: 5, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]})
                # Recover the exact interrupted public action.
                result = recovering.play("player-a", {"action_id": boundary, "wagers": {"seven": 1}})
                # Require exact dice, one row, no active residue, and no duplicate money.
                self.assertEqual(([3, 4], 1, False, 2), (result["round"]["dice"], len(repository.documents["player-a"]["recent_rounds"]), "active_round" in repository.documents["player-a"], len(ledger.events)))

    # Confirm a historical debit proof recovers without canonical helper fields.
    def test_legacy_debit_proof_recovery_uses_event_time_and_dice(self):
        # Define one stable historical request and its normalized wager.
        request = {"action_id": "legacy-proof", "wagers": {"seven": 1}}
        # Normalize the exact wager before constructing immutable proof.
        wagers = engine.normalize_wagers(request["wagers"])
        # Derive the established player-scoped round identity.
        round_id = engine.round_id_for("player-a", request["action_id"])
        # Store the semantic request fingerprint once.
        fingerprint = engine.wager_fingerprint(wagers)
        # Commit a pre-migration debit containing only historical field names.
        self.ledger.apply_once(player_id="player-a", amount=-1.0, transaction_type="OVER_UNDER_7_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", request_fingerprint=fingerprint, details={"action_id": request["action_id"], "wagers": wagers, "dice": [3, 4], "total": 7, "outcome": "seven"})
        # Build recovery whose fresh entropy and clock would visibly differ.
        recovering = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda _sides: 5, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Recover through the ordinary public service action.
        result = recovering.play("player-a", request)
        # Require committed dice, immutable event time, replay, and one new credit only.
        self.assertEqual(([3, 4], "2026-07-14T00:00:00Z", True, 2), (result["round"]["dice"], result["round"]["settled_at"], result["replayed"], len(self.ledger.events)))

    # Confirm terminal history is direct, oldest-to-newest, and bounded to one hundred.
    def test_history_retains_newest_one_hundred_direct_rounds(self):
        # Use deterministic sixes against under-only wagers so each round has one debit.
        service = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda _sides: 5, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Give the fake wallet enough tokens for the complete history exercise.
        self.ledger.balances["player-a"] = 1000000.0
        # Publish five more rounds than the documented history bound.
        for index in range(engine.RECENT_ROUND_LIMIT + 5):
            # Use one stable caller identity per completed action.
            service.play("player-a", {"action_id": f"history-{index:03d}", "wagers": {"under": 1}})
        # Read exact direct provider rows after bounded archival.
        rows = self.repository.documents["player-a"]["recent_rounds"]
        # Require direct oldest-to-newest rows for indices five through one hundred four.
        self.assertEqual((100, "history-005", "history-104", False), (len(rows), rows[0]["action_id"], rows[-1]["action_id"], any("public" in row for row in rows)))
        # Require one debit-only event per losing round without hidden credits.
        self.assertEqual(105, len(self.ledger.events))

    # Confirm changed retries fail closed before another movement.
    def test_conflicting_retry_rejected(self):
        # Commit one valid play.
        self.call("/api/v1/games/over-under-7/plays", {"action_id": "play-conflict", "wagers": {"under": 3}})
        # Reject reuse with changed wagers.
        with self.assertRaises(ConflictError):
            # Exercise semantic action-id conflict.
            self.call("/api/v1/games/over-under-7/plays", {"action_id": "play-conflict", "wagers": {"under": 4}})
        # Verify no extra debit was created.
        self.assertEqual(1, len([event for event in self.ledger.events.values() if event["transaction_type"] == "OVER_UNDER_7_WAGER_DEBIT"]))

    # Confirm a losing proposition creates no forbidden zero-value credit row.
    def test_losing_play_creates_only_wager_debit(self):
        # Build a service that deterministically rolls two sixes.
        losing = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_updater=self.repository.update, randbelow=lambda _sides: 5, clock=lambda: "2026-07-14T00:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]})
        # Wager only under so total twelve has no return.
        result = losing.play("player-a", {"action_id": "loss-1", "wagers": {"under": 1}})
        # Require zero return and absent settlement credit evidence.
        self.assertEqual((0.0, None), (result["round"]["total_return"], result["ledger"]["settlement"]))
        # Require only the aggregate wager debit to exist.
        self.assertEqual(1, len(self.ledger.events))

    # Confirm state and response history remain isolated by authenticated player.
    def test_player_state_isolation(self):
        # Settle one round for the first authenticated player.
        self.service.play("player-a", {"action_id": "isolated", "wagers": {"seven": 1}})
        # Read untouched state for another authenticated player.
        other = self.service.state("player-b")
        # Require no cross-player round history in the second response.
        self.assertEqual([], other["state"]["recent_rounds"])

    # Confirm source topology contains only the shared helper boundary.
    def test_service_source_uses_one_shared_coordinator(self):
        # Resolve exact service bytes from this checkout.
        source = Path(__file__).resolve().parents[3] / "casino" / "games" / "over_under_7" / "service.py"
        # Read the source inspected by central governance.
        text = source.read_text(encoding="utf-8")
        # Require one construction and no legacy direct settlement seams.
        self.assertEqual((1, False, False, False, False), (text.count("SimpleWagerGame("), "GameSettlementGateway" in text, "CoreLedgerGateway" in text, ".apply_once(" in text, "_ACTION_LOCK" in text))


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
