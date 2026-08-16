# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused deterministic engine, atomic-state, and shared-settlement tests for #89, #825, and #863."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
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

# Import the public conflict and validation errors asserted at game boundaries.
from casino.errors import ConflictError, ValidationError
# Import the isolated pure engine under test.
from casino.games.chuck_a_luck import engine
# Import the isolated service orchestrator under test.
from casino.games.chuck_a_luck.service import ChuckALuckService


# Simulate player-scoped state documents with provider-current callbacks.
class MemoryRepository:
    # Start with no persisted game documents.
    def __init__(self):
        # Store detached documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so every mutation requires an explicit save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

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


# Persist one selected provider transition and then simulate a lost storage response.
class PersistThenFailRepository(MemoryRepository):
    # Capture the exact authoritative-state predicate that identifies one crash boundary.
    def __init__(self, predicate):
        # Initialize ordinary detached provider storage first.
        super().__init__()
        # Retain the bounded state predicate supplied by the focused test.
        self._predicate = predicate
        # Arm exactly one post-persistence response failure.
        self._armed = True

    # Commit the provider-current mutation before optionally losing its response.
    def update(self, player_id, mutator):
        # Persist through the ordinary in-memory provider callback boundary.
        authoritative = super().update(player_id, mutator)
        # Fail once only when the exact requested crash boundary is now durable.
        if self._armed and self._predicate(authoritative):
            # Consume the one-shot fault before surfacing it to the caller.
            self._armed = False
            # Model a provider write whose response is lost after commit.
            raise RuntimeError("simulated lost provider response")
        # Return normal detached provider authority for every other transition.
        return authoritative


# Provide an in-memory apply-once ledger with production-shaped evidence.
class FakeLedgerGateway:
    # Initialize committed events and call evidence.
    def __init__(self):
        # Store events by their deterministic action key.
        self.events = {}
        # Store every apply-once invocation, including safe replays.
        self.calls = []
        # Hold one-shot pre-commit failures by deterministic action suffix.
        self.fail_before = set()
        # Hold one-shot lost responses after an event becomes immutable.
        self.fail_after = set()

    # Commit or recover one signed game action.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint, details):
        # Record the public action request for debit and credit count assertions.
        self.calls.append({"player_id": player_id, "amount": amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "request_fingerprint": request_fingerprint, "details": details})
        # Fail once before publication when a test arms this exact action suffix.
        if action_key.rsplit(":", 1)[-1] in self.fail_before:
            # Consume the one-shot failure so an explicit retry can proceed.
            self.fail_before.remove(action_key.rsplit(":", 1)[-1])
            # Model a provider rejection with no committed movement.
            raise RuntimeError("simulated pre-commit ledger failure")
        # Return the original event when this deterministic action already committed.
        if action_key in self.events:
            # Reject one identity reused with a different semantic fingerprint.
            if self.events[action_key]["details"]["request_fingerprint"] != request_fingerprint:
                # Match the production gateway's fail-closed conflict boundary.
                raise ConflictError("Fake ledger action fingerprint conflicts")
            # Preserve the same event identity and report replay recovery.
            return self.events[action_key], True
        # Build one production-shaped ledger event with complete audit dimensions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "game": "chuck_a_luck", "round_id": round_id, "transaction_type": transaction_type, "amount": amount, "ts": "2026-07-14T18:00:00Z", "details": {**details, "idempotency_key": action_key, "request_fingerprint": request_fingerprint}}
        # Persist the committed event under its unique action identity.
        self.events[action_key] = event
        # Lose one response only after the immutable event exists.
        if action_key.rsplit(":", 1)[-1] in self.fail_after:
            # Consume the one-shot fault before surfacing the transport-style error.
            self.fail_after.remove(action_key.rsplit(":", 1)[-1])
            # Force the caller to recover from exact committed proof.
            raise RuntimeError("simulated lost ledger response")
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
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create one apply-once in-memory ledger.
        self.ledger = FakeLedgerGateway()
        # Roll three ones so normal service assertions have a deterministic triple return.
        self.service = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: 0, clock=lambda: "2026-07-14T18:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})

    # Confirm provider-current preparation is idempotent and preserves siblings.
    def test_preparation_preserves_sibling_and_never_redraws(self):
        # Seed unrelated provider-owned metadata before the game prepares entropy.
        self.repository.documents["player-a"] = {"game": "chuck_a_luck", "recent_rounds": [], "atomic_markers": ["sibling"]}
        # Count each bounded entropy request across both identical preparations.
        draws = []
        # Build one service whose dice source records every requested span.
        service = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: draws.append(sides) or 2, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
        # Normalize the exact wager used by the lifecycle seam.
        wagers = engine.normalize_wagers({"three": 1})
        # Bind one stable fingerprint and round identity.
        fingerprint = engine.wager_fingerprint(wagers)
        # Prepare the action for the first time through provider-current state.
        first = service.prepare(player_id="player-a", request_id="prepared", round_id=engine.round_id_for("player-a", "prepared"), fingerprint=fingerprint, wager=wagers)
        # Repeat the identical preparation without allowing another draw.
        second = service.prepare(player_id="player-a", request_id="prepared", round_id=engine.round_id_for("player-a", "prepared"), fingerprint=fingerprint, wager=wagers)
        # Require one three-die draw, exact replay, and sibling preservation.
        self.assertEqual(([6, 6, 6], [3, 3, 3], [3, 3, 3], False, True, ["sibling"]), (draws, first["entropy"], second["entropy"], first["replayed"], second["replayed"], self.repository.documents["player-a"]["atomic_markers"]))

    # Confirm one active recovery slot rejects a distinct request before entropy or money.
    def test_distinct_preparation_conflicts_without_redraw(self):
        # Prepare the first action through the normal service boundary.
        wagers = engine.normalize_wagers({"one": 1})
        # Store its exact semantic identity for lifecycle preparation.
        fingerprint = engine.wager_fingerprint(wagers)
        # Persist one active provider-owned result.
        self.service.prepare(player_id="player-a", request_id="first", round_id=engine.round_id_for("player-a", "first"), fingerprint=fingerprint, wager=wagers)
        # Reject another request while the first action remains recoverable.
        with self.assertRaises(ConflictError):
            # Attempt to allocate the only active recovery slot to a second request.
            self.service.prepare(player_id="player-a", request_id="second", round_id=engine.round_id_for("player-a", "second"), fingerprint=fingerprint, wager=wagers)
        # Require the first exact action to remain authoritative.
        self.assertEqual("first", self.repository.documents["player-a"]["active_round"]["request_id"])

    # Prove stale uncommitted cleanup cannot erase a concurrently advanced action.
    def test_stale_cleanup_preserves_advanced_wager_state(self):
        # Prepare one exact request before simulating a later lifecycle winner.
        wagers = engine.normalize_wagers({"one": 1})
        # Bind its immutable semantic identity.
        fingerprint = engine.wager_fingerprint(wagers)
        # Capture the lifecycle context used by a stale failure callback.
        context = self.service.prepare(player_id="player-a", request_id="advanced", round_id=engine.round_id_for("player-a", "advanced"), fingerprint=fingerprint, wager=wagers)
        # Advance provider authority as though another caller observed committed debit proof.
        self.repository.documents["player-a"]["active_round"].update({"phase": "settling", "wager_status": "complete", "wager_ledger_id": "ledger-1"})
        # Run stale cleanup with no proof returned to this losing caller.
        self.service.wager_failed(player_id="player-a", request_id="advanced", round_id=engine.round_id_for("player-a", "advanced"), fingerprint=fingerprint, wager=wagers, wager_total=1.0, lifecycle_context=context, committed_event=None, error=RuntimeError("stale failure"))
        # Require the advanced provider winner and its proof marker to survive.
        self.assertEqual(("settling", "ledger-1"), (self.repository.documents["player-a"]["active_round"]["phase"], self.repository.documents["player-a"]["active_round"]["wager_ledger_id"]))

    # Prove fresh processes serialize preparation before entropy is drawn.
    def test_fresh_process_preparation_race_has_one_entropy_winner(self):
        # Own every provider and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve this exact checkout for child imports.
            repository_root = Path(__file__).resolve().parents[3]
            # Bind provider state to the task-owned disposable root.
            data_root = Path(temporary) / "data"
            # Resolve the exact player-game document used by both workers.
            state_path = data_root / "games" / "chuck_a_luck" / "player-a.json"
            # Create the state directory before seeding one empty game document.
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Publish exact initial JSON for both child providers.
            state_path.write_text(json.dumps({"recent_rounds": [], "atomic_markers": ["seed"]}, sort_keys=True), encoding="utf-8")
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
from casino.games.chuck_a_luck import engine
from casino.games.chuck_a_luck.service import ChuckALuckService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
request_id = sys.argv[3]
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
game = ChuckALuckService(state_loader=lambda player_id: load_player_game_state('chuck_a_luck', player_id, engine.default_state), state_updater=lambda player_id, mutator: update_player_game_state('chuck_a_luck', player_id, mutator, engine.default_state), randbelow=randbelow, clock=lambda: '2026-08-15T01:00:00Z', get_player=lambda player_id: {'player_id': player_id, 'balance': 100})
wagers = engine.normalize_wagers({'one': 1})
result = game.prepare(player_id='player-a', request_id=request_id, round_id=engine.round_id_for('player-a', request_id), fingerprint=engine.wager_fingerprint(wagers), wager=wagers)
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
            # Wait until both workers are ready to contend for provider authority.
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.chuck_a_luck import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('chuck_a_luck', 'player-a', add, engine.default_state)\n"
            # Commit the sibling before either preparation enters provider state.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release both contenders without choosing a winner in the test process.
            for _process, _ready, release in workers:
                # Open each bounded gate before collecting either result.
                release.write_text("go", encoding="utf-8")
            # Collect both provider-serialized preparation results.
            outputs = [process.communicate(timeout=20) for process, _ready, _release in workers]
            # Require both processes to return the exact same authoritative dice.
            self.assertTrue(all(process.returncode == 0 and output.strip().startswith("PASS:") for (process, _ready, _release), (output, error) in zip(workers, outputs)), outputs)
            # Split local draw counts, dice, and replay flags from both workers.
            evidence = [output.strip().split(":") for output, _error in outputs]
            # Require exactly one three-die entropy owner and one provider replay.
            self.assertEqual(([0, 3], ["6,6,6", "6,6,6"], [0, 1]), (sorted(int(row[1]) for row in evidence), sorted(row[2] for row in evidence), sorted(int(row[3]) for row in evidence)))
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one active winner, sibling preservation, and no terminal fabrication.
            self.assertEqual((persisted["active_round"]["request_id"], persisted["active_round"]["dice"], persisted["recent_rounds"], persisted["atomic_markers"]), ("atomic-preparation", [6, 6, 6], [], ["seed", "concurrent"]))

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
        recovering = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: 5, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
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

    # Confirm an uncommitted wager failure clears preparation and permits one explicit retry.
    def test_precommit_wager_failure_clears_preparation(self):
        # Arm one rejection before the wager action becomes immutable.
        self.ledger.fail_before.add("wager")
        # Attempt one valid winning request through the public service boundary.
        with self.assertRaisesRegex(RuntimeError, "pre-commit"):
            # Require the original provider error to surface unchanged.
            self.service.roll("player-a", {"request_id": "precommit", "wagers": {"one": 1}})
        # Require safe cleanup to leave no invented active or terminal result.
        self.assertEqual({"game": "chuck_a_luck", "recent_rounds": []}, self.repository.documents["player-a"])
        # Retry explicitly after the transient provider error.
        recovered = self.service.roll("player-a", {"request_id": "precommit", "wagers": {"one": 1}})
        # Require one exact settled result and two aggregate ledger movements.
        self.assertEqual(([1, 1, 1], 2), (recovered["round"]["dice"], len(self.ledger.events)))

    # Confirm a lost wager response retains committed dice for no-redraw recovery.
    def test_lost_wager_response_recovers_exact_committed_result(self):
        # Arm one response loss after the debit event becomes immutable.
        self.ledger.fail_after.add("wager")
        # Execute one winning request whose first response is intentionally lost.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve the original transport-style error for the caller.
            self.service.roll("player-a", {"request_id": "lost-wager", "wagers": {"one": 1}})
        # Require the exact prepared dice to remain durable beside the committed debit.
        self.assertEqual(([1, 1, 1], "prepared", 1), (self.repository.documents["player-a"]["active_round"]["dice"], self.repository.documents["player-a"]["active_round"]["phase"], len(self.ledger.events)))
        # Recover with a fresh service whose entropy would otherwise differ.
        recovering = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: 5, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
        # Retry the exact public action identity once.
        result = recovering.roll("player-a", {"request_id": "lost-wager", "wagers": {"one": 1}})
        # Require exact dice recovery, explicit replay evidence, and no duplicate movements.
        self.assertEqual(([1, 1, 1], True, 2), (result["round"]["dice"], result["replayed"], len(self.ledger.events)))

    # Confirm a lost settlement response recovers one immutable returned-credit action.
    def test_lost_settlement_response_recovers_without_duplicate_credit(self):
        # Arm one response loss after the positive settlement credit commits.
        self.ledger.fail_after.add("settlement")
        # Execute one triple-winning action through the public service.
        with self.assertRaisesRegex(RuntimeError, "lost ledger response"):
            # Preserve the first failed response while keeping both events durable.
            self.service.roll("player-a", {"request_id": "lost-credit", "wagers": {"one": 1}})
        # Require the deterministic result intent and both exact ledger movements.
        self.assertEqual((4.0, "pending", 2), (self.repository.documents["player-a"]["active_round"]["total_return"], self.repository.documents["player-a"]["active_round"]["settlement_status"], len(self.ledger.events)))
        # Retry the identical action to reconstruct the missing response and state writes.
        result = self.service.roll("player-a", {"request_id": "lost-credit", "wagers": {"one": 1}})
        # Require one terminal round, explicit replay, and exactly two events total.
        self.assertEqual((4.0, True, 2, 1), (result["round"]["total_return"], result["replayed"], len(self.ledger.events), len(result["state"]["recent_rounds"])))

    # Confirm every durable lifecycle write can lose its response and recover exactly once.
    def test_provider_write_crash_boundaries_converge(self):
        # Name exact provider states after debit, result, credit, finalization, and archival.
        boundaries = {
            "post-debit": lambda state: isinstance(state.get("active_round"), dict) and state["active_round"].get("phase") == "settling" and "total_return" not in state["active_round"],
            "post-result": lambda state: isinstance(state.get("active_round"), dict) and state["active_round"].get("settlement_status") == "pending" and "settlement_ledger_id" not in state["active_round"],
            "post-credit": lambda state: isinstance(state.get("active_round"), dict) and bool(state["active_round"].get("settlement_ledger_id")),
            "post-finalize": lambda state: isinstance(state.get("active_round"), dict) and state["active_round"].get("phase") == "settled",
            "post-archive": lambda state: state.get("active_round") is None and len(state.get("recent_rounds", [])) == 1,
        }
        # Exercise every durable state boundary independently for unambiguous evidence.
        for boundary, predicate in boundaries.items():
            # Label failures by the exact crash schedule under test.
            with self.subTest(boundary=boundary):
                # Create isolated provider and ledger authority for this schedule.
                repository, ledger = PersistThenFailRepository(predicate), FakeLedgerGateway()
                # Draw one triple-one result before losing exactly one provider response.
                service = ChuckALuckService(ledger_gateway=ledger, repository=repository, randbelow=lambda sides: 0, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
                # Require the selected persisted transition to surface a response failure.
                with self.assertRaisesRegex(RuntimeError, "lost provider response"):
                    # Execute one stable action identity per isolated schedule.
                    service.roll("player-a", {"request_id": boundary, "wagers": {"one": 1}})
                # Resume with entropy that would visibly redraw if provider proof were ignored.
                recovering = ChuckALuckService(ledger_gateway=ledger, repository=repository, randbelow=lambda sides: 5, clock=lambda: "later", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
                # Recover the exact interrupted public action.
                result = recovering.roll("player-a", {"request_id": boundary, "wagers": {"one": 1}})
                # Require exact dice, one archived row, no active residue, and no duplicate money.
                self.assertEqual(([1, 1, 1], 1, False, 2), (result["round"]["dice"], len(repository.documents["player-a"]["recent_rounds"]), "active_round" in repository.documents["player-a"], len(ledger.events)))

    # Confirm terminal history remains direct, oldest-to-newest, and bounded to one hundred.
    def test_history_retains_newest_one_hundred_direct_rounds(self):
        # Use deterministic sixes against one-only wagers so every round has one debit event.
        service = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: 5, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 1000000})
        # Publish five more rounds than the documented reload-safe history bound.
        for index in range(engine.RECENT_ROUND_LIMIT + 5):
            # Use one stable caller identity per completed action.
            service.roll("player-a", {"request_id": f"history-{index:03d}", "wagers": {"one": 1}})
        # Read exact direct provider rows after bounded archival.
        rows = self.repository.documents["player-a"]["recent_rounds"]
        # Require direct oldest-to-newest rows for indices five through one hundred four.
        self.assertEqual((100, "history-005", "history-104", False), (len(rows), rows[0]["request_id"], rows[-1]["request_id"], any("public" in row for row in rows)))
        # Require one debit-only event per losing round without hidden credits.
        self.assertEqual(105, len(self.ledger.events))

    # Confirm source topology contains only the shared helper orchestration boundary.
    def test_service_source_uses_one_shared_coordinator(self):
        # Read the exact module bytes inspected by central governance.
        source = Path(ChuckALuckService.__module__.replace(".", "/") + ".py")
        # Resolve the module path from this checkout rather than the process directory.
        text = (Path(__file__).resolve().parents[3] / source).read_text(encoding="utf-8")
        # Require one construction and no legacy direct settlement seams.
        self.assertEqual((1, False, False, False, False), (text.count("SimpleWagerGame("), "GameSettlementGateway" in text, "CoreLedgerGateway" in text, ".apply_once(" in text, "_SETTLEMENT_LOCK" in text))

    # Confirm a losing number wager creates no forbidden zero-value payout row.
    def test_losing_roll_creates_only_wager_debit(self):
        # Build a service that deterministically rolls three sixes.
        losing = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: 5, clock=lambda: "2026-07-14T18:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
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
