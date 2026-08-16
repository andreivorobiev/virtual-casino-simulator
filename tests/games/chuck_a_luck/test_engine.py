# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused deterministic engine, atomic-state, and ledger-recovery tests for issues #89 and #825."""

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
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create one apply-once in-memory ledger.
        self.ledger = FakeLedgerGateway()
        # Roll three ones so normal service assertions have a deterministic triple return.
        self.service = ChuckALuckService(ledger_gateway=self.ledger, repository=self.repository, randbelow=lambda sides: 0, clock=lambda: "2026-07-14T18:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})

    # Confirm identical publication stays idempotent and preserves siblings.
    def test_atomic_publication_preserves_siblings_and_private_baseline(self):
        # Load one tracked default document through the service boundary.
        state = self.service._load("player-a")
        # Add one deterministic settled row as the desired owned transition.
        state["recent_rounds"].append({"request_id": "atomic-same", "request_fingerprint": "a" * 64})
        # Publish the tracked transition through provider-current comparison.
        self.service._save("player-a", state)
        # Add unrelated metadata after the first game-owned publication.
        self.repository.documents["player-a"]["atomic_markers"] = ["sibling"]
        # Publish the exact same desired result from the advanced baseline.
        self.service._save("player-a", state)
        # Read the final provider-authoritative document.
        persisted = self.repository.documents["player-a"]
        # Verify the sibling survives and operation metadata never persists.
        self.assertEqual(["sibling"], persisted["atomic_markers"])
        # Keep the optimistic snapshot outside durable player state.
        self.assertNotIn("_chuck_a_luck_atomic_baseline", persisted)

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

        # Build the service around the rejecting update seam.
        service = ChuckALuckService(repository=RejectingRepository())
        # Reject an untracked default document as a stale publication.
        with self.assertRaises(ConflictError):
            # Attempt publication without the required provider-read baseline.
            service._save("player-a", engine.default_state())
        # Prove storage was never reached.
        self.assertEqual([], updates)

    # Prove a stale state publication cannot overwrite a concurrent winner or duplicate ledger events.
    def test_stale_publication_after_committed_ledger_preserves_winner_and_recovers_once(self):
        # Extend memory storage with one deterministic provider-winner schedule.
        class RacingRepository(MemoryRepository):
            # Present one concurrent winner before the first callback executes.
            def update(self, player_id, mutator):
                # Build a valid settled row owned by another concurrent request.
                winner_wagers = engine.normalize_wagers({"six": 1})
                # Calculate the terminal losing result without touching the fake ledger.
                winner_settlement = engine.settle(winner_wagers, [1, 2, 3])
                # Preserve one stable semantic fingerprint for the winner.
                winner_fingerprint = engine.wager_fingerprint(winner_wagers)
                # Persist the concurrent authoritative game-owned result first.
                self.documents[player_id] = {"recent_rounds": [{"round_id": engine.round_id_for(player_id, "provider-winner"), "request_id": "provider-winner", "request_fingerprint": winner_fingerprint, "player_id": player_id, "status": "settled", "wagers": winner_wagers, **winner_settlement, "settled_at": "2026-08-15T01:00:00Z"}], "atomic_markers": ["provider-winner"]}
                # Present the already-committed winner to the stale callback.
                return mutator(copy.deepcopy(self.documents[player_id]))

        # Create the race-aware provider with one deterministic winning ledger action.
        repository = RacingRepository()
        # Build the real service around the race-aware provider and existing ledger.
        service = ChuckALuckService(ledger_gateway=self.ledger, repository=repository, randbelow=lambda sides: 0, clock=lambda: "2026-08-15T01:00:00Z", get_player=lambda player_id: {"player_id": player_id, "balance": 100})
        # Define one stable request whose debit and credit commit before state publication.
        request = {"request_id": "stale-ledger", "wagers": {"one": 1}}
        # Require stale state publication to surface an explicit provider conflict.
        with self.assertRaises(ConflictError):
            # Execute the complete ledger-backed action whose save loses the race.
            service.roll("player-a", request)
        # Verify the provider-winning round and unrelated sibling remain authoritative.
        self.assertEqual(("provider-winner", ["provider-winner"]), (repository.documents["player-a"]["recent_rounds"][0]["request_id"], repository.documents["player-a"]["atomic_markers"]))
        # Require exactly one debit and one credit after the rejected publication.
        self.assertEqual(2, len(self.ledger.events))
        # Disable the one-shot race hook while retaining the provider-winning document.
        repository.update = MemoryRepository.update.__get__(repository, RacingRepository)
        # Recover the missing state row through the same public request identity.
        recovered = service.roll("player-a", request)
        # Require ledger replay and both terminal rounds without a duplicate movement.
        self.assertEqual((True, ["provider-winner", "stale-ledger"], 2), (recovered["replayed"], [row["request_id"] for row in repository.documents["player-a"]["recent_rounds"]], len(self.ledger.events)))

    # Prove stale fresh processes preserve siblings and expose one state winner.
    def test_fresh_process_round_race_has_one_state_winner(self):
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
            # Define one worker whose repository pauses after capturing stale state.
            worker_source = r"""
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError
from casino.games.chuck_a_luck import engine
from casino.games.chuck_a_luck.service import ChuckALuckService
ready = Path(sys.argv[1])
release = Path(sys.argv[2])
request_id = sys.argv[3]
class Repository:
    def load(self, player_id):
        state = load_player_game_state('chuck_a_luck', player_id, engine.default_state)
        ready.write_text('ready', encoding='utf-8')
        deadline = time.monotonic() + 10
        while not release.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not release.exists():
            raise RuntimeError('release gate timeout')
        return state
    def update(self, player_id, mutator):
        return update_player_game_state('chuck_a_luck', player_id, mutator, engine.default_state)
class Ledger:
    def __init__(self):
        self.calls = []
    def apply_once(self, **kwargs):
        self.calls.append(kwargs['action_key'])
        return {'ledger_id': 'ledger-' + str(len(self.calls)), 'player_id': kwargs['player_id'], 'amount': kwargs['amount'], 'transaction_type': kwargs['transaction_type'], 'game': 'chuck_a_luck', 'round_id': kwargs['round_id'], 'ts': '2026-08-15T01:00:00Z', 'details': {**kwargs['details'], 'idempotency_key': kwargs['action_key'], 'request_fingerprint': kwargs['request_fingerprint']}}, False
ledger = Ledger()
game = ChuckALuckService(ledger_gateway=ledger, repository=Repository(), randbelow=lambda span: 5, clock=lambda: '2026-08-15T01:00:00Z', get_player=lambda player_id: {'player_id': player_id, 'balance': 100})
try:
    game.roll('player-a', {'request_id': request_id, 'wagers': {'one': 1}})
    print('PASS:' + str(len(ledger.calls)))
except ConflictError:
    print('CONFLICT:' + str(len(ledger.calls)))
"""
            # Retain both independently loaded process contenders.
            workers = []
            # Start one provider winner candidate and one stale loser candidate.
            for index in range(2):
                # Allocate task-owned readiness and release gates.
                ready_path, release_path = Path(temporary) / f"ready-{index}", Path(temporary) / f"release-{index}"
                # Launch without a shell so interpreter and arguments remain exact.
                process = subprocess.Popen([sys.executable, "-c", worker_source, str(ready_path), str(release_path), f"atomic-process-{index}"], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
            sibling_source = "from casino.core.state_store import update_player_game_state\nfrom casino.games.chuck_a_luck import engine\ndef add(state):\n    state.setdefault('atomic_markers', []).append('concurrent')\n    return state\nupdate_player_game_state('chuck_a_luck', 'player-a', add, engine.default_state)\n"
            # Commit the sibling after both workers captured stale baselines.
            sibling = subprocess.run([sys.executable, "-c", sibling_source], cwd=repository_root, env=environment, capture_output=True, text=True, timeout=15)
            # Require the sibling provider transition to complete cleanly.
            self.assertEqual(sibling.returncode, 0, f"stdout={sibling.stdout!r} stderr={sibling.stderr!r}")
            # Release the first worker to publish the winning round.
            workers[0][2].write_text("go", encoding="utf-8")
            # Collect the exact winner result.
            winner_output, winner_error = workers[0][0].communicate(timeout=20)
            # Require one losing-round debit call from the provider winner.
            self.assertEqual((workers[0][0].returncode, winner_output.strip()), (0, "PASS:1"), winner_error)
            # Release the stale worker only after the winner is durable.
            workers[1][2].write_text("go", encoding="utf-8")
            # Collect the explicit fail-closed stale result.
            stale_output, stale_error = workers[1][0].communicate(timeout=15)
            # Require conflict instead of a silent stale overwrite.
            self.assertEqual((workers[1][0].returncode, stale_output.strip()), (0, "CONFLICT:1"), stale_error)
            # Read final provider-authoritative bytes directly.
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            # Require one terminal winner, sibling preservation, and no overwrite.
            self.assertEqual((len(persisted["recent_rounds"]), persisted["recent_rounds"][-1]["request_id"], persisted["atomic_markers"]), (1, "atomic-process-0", ["seed", "concurrent"]))
            # Verify private optimistic metadata never enters persistent bytes.
            self.assertNotIn("_chuck_a_luck_atomic_baseline", persisted)

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
