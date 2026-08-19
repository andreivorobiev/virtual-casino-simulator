# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused exactly-once settlement tests for the shared simple-game core. (#73 expansion, GAMECORE-001/002)"""

# Import deep-copy support for provider-shaped state fixtures.
import copy
# Import paths for catalog-wide player-lock and unchanged JSON-gate source evidence.
from pathlib import Path
# Import bounded thread coordination for same-player and cross-player lock evidence.
import threading
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative ledger and player boundaries for balance assertions.
from casino.core import ledger, players
# Import the bounded registry and shared action-lock seam under test. (GAMECORE-009)
from casino.core.player_locks import PlayerLockStriper, player_action_lock
# Import the shared wager-and-settle core under test.
from casino.core.simple_game import SimpleWagerGame, round_id_for
# Import the standard bounded application errors every rejection uses.
from casino.errors import ConflictError, ValidationError

# Resolve the checked repository root for source-boundary evidence.
ROOT = Path(__file__).resolve().parents[1]


# Draw one deterministic die from an injected random function for a stable test.
def _entropy(randbelow) -> dict:
    # Draw a single 1..6 face so the resolver is easy to reason about.
    return {"face": randbelow(6) + 1}


# Validate a coin-flip-style bet: stake on a chosen face, paying 5x on a match.
def _validate_bet(request: dict) -> tuple:
    # Read the chosen face and stake.
    face = int(request.get("face", 0))
    # Read the stake as a bounded positive integer.
    stake = int(request.get("stake", 0))
    # Reject an out-of-range face.
    if face < 1 or face > 6:
        # Fail closed on an invalid selection.
        raise ValidationError("face must be 1..6")
    # Reject a non-positive stake.
    if stake <= 0:
        # Fail closed on an empty wager.
        raise ValidationError("stake must be positive")
    # Build the authoritative wager, its total stake, and a stable content fingerprint.
    return {"face": face, "stake": stake}, float(stake), f"{face}:{stake}"


# Resolve deterministically from the committed wager and committed entropy.
def _resolve(wager: dict, entropy: dict) -> dict:
    # Pay five times the stake on a matching face, nothing otherwise.
    if entropy["face"] == wager["face"]:
        # Return the winning settlement.
        return {"outcome": "win", "total_return": wager["stake"] * 5, "detail": {"face": entropy["face"]}}
    # Return the losing settlement with no return.
    return {"outcome": "lose", "total_return": 0, "detail": {"face": entropy["face"]}}


# Simulate provider-current document callbacks without bypassing the atomic mutator shape.
class MemoryState:
    # Start with no player documents and one optional pre-publication hook.
    def __init__(self) -> None:
        # Retain detached provider-owned documents by player id.
        self.documents = {}
        # Allow one test to publish a concurrent provider transition after a stale load.
        self.before_update = None

    # Build one fresh shared-core state document.
    @staticmethod
    def _default() -> dict:
        # Match the production helper's game-owned default fields.
        return {"game": "unit_flip", "recent_rounds": []}

    # Return a detached snapshot so callers cannot mutate provider state directly.
    def load(self, player_id: str) -> dict:
        # Copy the exact current document or a fresh default.
        return copy.deepcopy(self.documents.get(player_id, self._default()))

    # Apply one callback against provider-current state.
    def update(self, player_id: str, mutator) -> dict:
        # Run a configured concurrent publication exactly once before the caller callback.
        if self.before_update is not None:
            # Detach the hook before execution so recursive or failed updates cannot repeat it.
            hook, self.before_update = self.before_update, None
            # Let the test modify only the provider-owned document.
            hook(self.documents.setdefault(player_id, self._default()))
        # Execute the production mutator against a detached provider-current copy.
        updated = mutator(copy.deepcopy(self.documents.get(player_id, self._default())))
        # Publish only after the callback returns successfully.
        self.documents[player_id] = copy.deepcopy(updated)
        # Return detached committed authority to the core.
        return copy.deepcopy(updated)


# Model the immutable gateway contract while counting provider proof round-trips. (STORAGE-017)
class CountingLedgerGateway:
    # Start with no committed actions or provider calls.
    def __init__(self) -> None:
        # Retain immutable events by action key for replay reads.
        self.events = {}
        # Count apply-once provider calls.
        self.apply_calls = 0
        # Count read-only proof lookups.
        self.find_calls = 0

    # Apply or replay one deterministic event.
    def apply_once(self, **context):
        # Record one provider transaction call.
        self.apply_calls += 1
        # Read the immutable action identity.
        action_key = context["action_key"]
        # Return a prior exact event as a replay.
        if action_key in self.events:
            # Preserve the gateway tuple contract.
            return copy.deepcopy(self.events[action_key]), True
        # Build the bounded event fields consumed by SimpleWagerGame.
        event = {"ledger_id": f"ledger-{action_key}", "player_id": context["player_id"], "game": "unit_flip", "round_id": context["round_id"], "transaction_type": context["transaction_type"], "amount": context["signed_amount"], "details": copy.deepcopy(context["details"])}
        # Commit a detached immutable copy.
        self.events[action_key] = copy.deepcopy(event)
        # Return the newly committed event.
        return event, False

    # Find one prior exact event by its action identity.
    def find(self, **context):
        # Record one provider point lookup.
        self.find_calls += 1
        # Return a detached committed event for the requested action.
        return copy.deepcopy(self.events[context["action_key"]])


# Build one isolated game whose entropy is pinned for deterministic assertions.
def _game(forced_face: int = 3) -> SimpleWagerGame:
    # Force the entropy source so the drawn face is deterministic.
    return SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=_resolve, validate_bet=_validate_bet, entropy_source=lambda n: forced_face - 1)


# Verify the shared core settles exactly once and stays retry-safe.
class SimpleGameCoreTests(unittest.TestCase):
    # Seed one fresh player wallet for each test.
    def setUp(self) -> None:
        # Create a real player with a known starting balance.
        self.player = players.create_player(f"Flip {self.id().rsplit('.',1)[1]}", "human", 1000.0)
        # Retain the player id used across every action.
        self.pid = self.player["player_id"]

    # Read the current authoritative balance.
    def _balance(self) -> float:
        # Return the player's current wallet balance.
        return players.get_player(self.pid)["balance"]

    # Prove the shared lock registry remains bounded and deterministically player-scoped. (TEST-246)
    def test_player_lock_registry_is_bounded_and_validated(self) -> None:
        # Build a deliberately small registry so bounded allocation is directly observable.
        registry = PlayerLockStriper(stripe_count=7)
        # Select the same identity twice without retaining any player-keyed mapping.
        first_index = registry.stripe_index("bounded-player")
        # Require stable selection, fixed capacity, and the same reusable lock object.
        self.assertEqual((7, first_index, registry.lock_for("bounded-player") is registry.lock_for("bounded-player")), (registry.stripe_count, registry.stripe_index("bounded-player"), True))
        # Reject boolean and non-positive registry sizes rather than allocating an unsafe fallback.
        for invalid_count in (True, 0, -1):
            # Require every invalid fixed-size configuration to fail at construction.
            with self.subTest(invalid_count=invalid_count), self.assertRaises(ValueError):
                # Exercise the configuration guard without allocating a registry.
                PlayerLockStriper(stripe_count=invalid_count)
        # Reject absent or empty identities before lock selection.
        for invalid_player in (None, ""):
            # Require malformed internal identities to fail closed.
            with self.subTest(invalid_player=invalid_player), self.assertRaises(ValueError):
                # Exercise the player-identity guard.
                registry.lock_for(invalid_player)
        # Bind the documented deadlock rule to the public lock seam.
        self.assertIn("before provider/JSON locks; never acquire a second player stripe", player_action_lock.__doc__)

    # Prove every legacy gateway migrated and the JSON provider retained its global gate. (TEST-246)
    def test_gateway_inventory_uses_player_stripes_and_json_gate_survives(self) -> None:
        # Bind the exact legacy gateway source inventory approved by issue 715.
        gateway_paths = (
            "casino/games/acey_deucey/service.py",
            "casino/games/andar_bahar/service.py",
            "casino/games/caribbean_stud/service.py",
            "casino/games/casino_holdem/service.py",
            "casino/games/casino_war/api.py",
            "casino/games/craps/api.py",
            "casino/games/deuces_wild_video_poker/api.py",
            "casino/games/double_bonus_video_poker/service.py",
            "casino/games/four_card_poker/service.py",
            "casino/games/hi_lo/service.py",
            "casino/games/jacks_or_better_video_poker/api.py",
            "casino/games/joker_poker/service.py",
            "casino/games/let_it_ride/api.py",
            "casino/games/mississippi_stud/service.py",
            "casino/games/multi_hand_video_poker/api.py",
            "casino/games/pai_gow_poker/service.py",
            "casino/games/plinko/service.py",
            "casino/games/red_dog/api.py",
            "casino/games/scratch_cards/service.py",
            "casino/games/teen_patti/service.py",
            "casino/games/texas_holdem_practice_table/api.py",
            "casino/games/three_card_poker/service.py",
        )
        # Require the reviewed inventory to remain exact rather than silently shrinking.
        self.assertEqual(len(gateway_paths), 22)
        # Inspect every migrated legacy action owner.
        for relative_path in gateway_paths:
            # Name the active file in any focused failure.
            with self.subTest(relative_path=relative_path):
                # Read the complete checked source without importing route modules.
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                # Require shared player stripes and reject both retired module-lock identities.
                self.assertIn("from casino.core.player_locks import player_action_lock", source)
                # Require at least one actual protected action, not an unused import.
                self.assertIn("with player_action_lock(player_id):", source)
                # Reject reintroduction of either retired process-wide game lock.
                self.assertNotIn("threading.RLock", source)
                # Reject the historical action-lock symbol.
                self.assertNotIn("_ACTION_LOCK", source)
                # Reject the historical settlement-lock symbol.
                self.assertNotIn("_SETTLEMENT_LOCK", source)
        # Read only the unchanged JSON provider source for its money-path gate proof.
        json_source = (ROOT / "casino/core/storage/json_provider.py").read_text(encoding="utf-8")
        # Isolate the exactly-once ledger mutation method from the following method.
        json_transaction = json_source.split("    def transact_ledger_once", 1)[1].split("\n    def ", 1)[0]
        # Require the existing in-process and cross-process JSON gates in their established order.
        self.assertLess(json_transaction.index("with self.lock:"), json_transaction.index("with self._ledger_process_lock():"))

    # Prove different player wallets can reach settlement concurrently without a process-wide gate. (TEST-246)
    def test_different_players_settle_concurrently(self) -> None:
        # Use the production stripe count to choose two identities that cannot share a stripe by accident.
        registry = PlayerLockStriper()
        # Fix one synthetic player identity.
        first_player = "stripe-player-a"
        # Select the first deterministic identity mapped to another stripe.
        second_player = next(candidate for candidate in (f"stripe-player-{index}" for index in range(1000)) if registry.stripe_index(candidate) != registry.stripe_index(first_player))
        # Require both resolver calls to rendezvous while their player stripes are held.
        resolver_barrier = threading.Barrier(2, timeout=3)
        # Protect only the synthetic provider document fixture, never the game settlement path.
        state_lock = threading.Lock()
        # Retain detached state documents by synthetic player id.
        documents = {}
        # Use one immutable fake gateway whose distinct action keys model MySQL row-level writes.
        gateway = CountingLedgerGateway()
        # Collect thread results without leaking exceptions across the assertion boundary.
        results = {}
        # Retain unexpected failures for the parent thread.
        errors = []

        # Load one detached provider-shaped state document.
        def load_state(player_id):
            # Serialize only fixture dictionary access.
            with state_lock:
                # Return the current detached state or one fresh game document.
                return copy.deepcopy(documents.get(player_id, {"game": "unit_flip", "recent_rounds": []}))

        # Publish one state mutation against fixture-current authority.
        def update_state(player_id, mutator):
            # Serialize only the in-memory provider callback.
            with state_lock:
                # Apply the production callback to a detached current document.
                updated = mutator(copy.deepcopy(documents.get(player_id, {"game": "unit_flip", "recent_rounds": []})))
                # Retain the committed detached document.
                documents[player_id] = copy.deepcopy(updated)
                # Return detached provider authority.
                return copy.deepcopy(updated)

        # Resolve only after both distinct players entered the protected action path.
        def resolve_concurrently(wager, entropy):
            # Fail the test if a process-wide lock prevents the second player from arriving.
            resolver_barrier.wait()
            # Reuse the deterministic production-shaped resolver.
            return _resolve(wager, entropy)

        # Return one synthetic point-read wallet for the response envelope.
        def get_player(player_id):
            # Preserve the requested identity and a deterministic post-settlement balance.
            return {"player_id": player_id, "balance": 14.0}

        # Build one helper shared by both distinct player requests.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=resolve_concurrently, validate_bet=_validate_bet, entropy_source=lambda _n: 2, ledger_gateway=gateway, state_loader=load_state, state_updater=update_state, get_player=get_player)

        # Execute one distinct player action and retain its result or error.
        def execute(player_id, request_id):
            try:
                # Run the complete wager, resolver rendezvous, settlement, and publication path.
                results[player_id] = game.play(player_id, {"request_id": request_id, "face": 3, "stake": 1})
            # Retain any failure for exact parent-thread handling.
            except BaseException as exc:
                # Preserve only the in-memory exception object.
                errors.append(exc)

        # Create both player workers before starting either one.
        threads = (threading.Thread(target=execute, args=(first_player, "stripe-a")), threading.Thread(target=execute, args=(second_player, "stripe-b")))
        # Start both different-player actions.
        for thread in threads:
            # Allow each player stripe to progress independently.
            thread.start()
        # Join both actions within one bounded evidence window.
        for thread in threads:
            # Wait for wallet and state publication to finish.
            thread.join(5)
        # Require both actions to finish without a broken rendezvous or hidden failure.
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        # Require no thread failure and one complete winning result per player.
        self.assertEqual((errors, set(results), gateway.apply_calls), ([], {first_player, second_player}, 4))

    # Prove two actions for the same player retain strict local serialization. (TEST-246)
    def test_same_player_actions_remain_serialized(self) -> None:
        # Signal when the first request reaches its resolver while holding the player stripe.
        first_entered = threading.Event()
        # Detect any second resolver entry before the first request releases the stripe.
        second_entered = threading.Event()
        # Release the first resolver only after the serialization assertion.
        release_first = threading.Event()
        # Protect the resolver-entry counter used only by this concurrency fixture.
        resolver_lock = threading.Lock()
        # Retain resolver entry count without relying on thread scheduling order.
        resolver_calls = []
        # Reuse one provider-shaped state fixture and one immutable ledger gateway.
        state = MemoryState()
        # Retain unexpected worker failures.
        errors = []

        # Block the first resolver and flag any premature second entry.
        def resolve_serially(wager, entropy):
            # Assign one stable entry ordinal under the fixture lock.
            with resolver_lock:
                # Record this resolver arrival.
                resolver_calls.append(threading.current_thread().name)
                # Capture the one-based arrival ordinal.
                ordinal = len(resolver_calls)
            # Hold only the first action while the parent probes the second.
            if ordinal == 1:
                # Tell the parent the player stripe is occupied inside resolution.
                first_entered.set()
                # Wait for the bounded parent-controlled release.
                if not release_first.wait(3):
                    # Fail explicitly instead of allowing a hung test.
                    raise AssertionError("same-player resolver release timed out")
            # Flag the second arrival only after it actually acquires the same player stripe.
            if ordinal == 2:
                # Publish proof that the second request reached resolution.
                second_entered.set()
            # Return one deterministic losing result so no credit path is required.
            return _resolve(wager, {"face": 1})

        # Return one synthetic point-read wallet after each debit.
        def get_player(player_id):
            # Preserve the exact same-player identity in the response envelope.
            return {"player_id": player_id, "balance": 8.0}

        # Build one helper whose two requests share a single player stripe.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=resolve_serially, validate_bet=_validate_bet, entropy_source=lambda _n: 0, ledger_gateway=CountingLedgerGateway(), state_loader=state.load, state_updater=state.update, get_player=get_player)

        # Execute one same-player request and retain any failure.
        def execute(request_id):
            try:
                # Run the complete request under the shared player stripe.
                game.play("same-player", {"request_id": request_id, "face": 3, "stake": 1})
            # Retain any failure for the parent assertion.
            except BaseException as exc:
                # Preserve only the in-memory exception object.
                errors.append(exc)

        # Start the first request and wait until it owns the stripe inside resolution.
        first_thread = threading.Thread(name="same-player-first", target=execute, args=("same-a",))
        # Launch the first request.
        first_thread.start()
        # Require the first action to reach the controlled resolver.
        self.assertTrue(first_entered.wait(3))
        # Start a second request for the exact same wallet.
        second_thread = threading.Thread(name="same-player-second", target=execute, args=("same-b",))
        # Launch the serialized contender.
        second_thread.start()
        # Require the second resolver to remain unreachable while the first holds the stripe.
        self.assertFalse(second_entered.wait(0.25))
        # Release the first request so the second can acquire the same stripe.
        release_first.set()
        # Join both requests within the bounded evidence window.
        first_thread.join(5)
        # Join the second request after ownership transfers.
        second_thread.join(5)
        # Require both threads to finish, no hidden errors, and exact entry order.
        self.assertEqual((first_thread.is_alive(), second_thread.is_alive(), errors, resolver_calls), (False, False, [], ["same-player-first", "same-player-second"]))

    # Require a winning round to debit the stake and credit the full return once.
    def test_winning_round_settles_once(self) -> None:
        # Retain one helper instance so its public proof lookup can be verified after settlement.
        game = _game(forced_face=3)
        # Play a stake on the forced winning face.
        result = game.play(self.pid, {"request_id": "r-win", "face": 3, "stake": 10})
        # Require the winning outcome and a 50-token return on a 10 stake at 5x.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 50))
        # Require both wallet movements to use storage-enforced atomic action identities.
        self.assertEqual((result["ledger"]["wager"]["details"]["ledger_action_key"], result["ledger"]["settlement"]["details"]["ledger_action_key"]), (f'{result["round"]["round_id"]}:wager', f'{result["round"]["round_id"]}:settlement'))
        # Pin the established default public round keys while optional adapters serve legacy games.
        self.assertEqual(set(result["round"]), {"round_id", "wager", "wager_total", "entropy", "total_return", "outcome", "detail", "net", "settled_at"})
        # Pin the canonical recovery fields retained inside the default wager proof.
        self.assertEqual({key: result["ledger"]["wager"]["details"][key] for key in ("request_id", "wager", "entropy", "settled_at")}, {"request_id": "r-win", "wager": {"face": 3, "stake": 10}, "entropy": {"face": 3}, "settled_at": result["round"]["settled_at"]})
        # Require the wallet to reflect exactly minus-stake plus-return once.
        self.assertEqual(self._balance(), 1000.0 - 10 + 50)
        # Read the committed wager through the same helper-owned gateway boundary.
        wager_proof = game.find_committed_action(player_id=self.pid, round_id=result["round"]["round_id"], request_fingerprint="3:10", action="wager")
        # Require exact immutable proof without another movement.
        self.assertEqual(result["ledger"]["wager"]["ledger_id"], wager_proof["ledger_id"])
        # Reject an unknown action role before persistent proof access.
        with self.assertRaisesRegex(ValueError, "wager or settlement"):
            # Exercise programmer-facing validation on the public lookup seam.
            game.find_committed_action(player_id=self.pid, round_id=result["round"]["round_id"], request_fingerprint="3:10", action="refund")

    # Require a losing round to debit the stake and credit nothing.
    def test_losing_round_debits_only(self) -> None:
        # Play a stake on a non-winning face.
        result = _game(forced_face=3).play(self.pid, {"request_id": "r-lose", "face": 5, "stake": 10})
        # Require the losing outcome and no return.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("lose", 0))
        # Require the wallet to reflect only the debited stake.
        self.assertEqual(self._balance(), 1000.0 - 10)

    # Require a retried request to replay the identical outcome without moving the wallet again.
    def test_retry_replays_without_double_spend(self) -> None:
        # Build one game instance reused across the retry.
        game = _game(forced_face=3)
        # Play the first request.
        first = game.play(self.pid, {"request_id": "r-dup", "face": 3, "stake": 20})
        # Record the balance after the first settlement.
        after_first = self._balance()
        # Replay the identical request.
        second = game.play(self.pid, {"request_id": "r-dup", "face": 3, "stake": 20})
        # Require the retry to be reported as a replay.
        self.assertTrue(second["replayed"])
        # Require the replayed outcome to match the original exactly.
        self.assertEqual(second["round"]["total_return"], first["round"]["total_return"])
        # Require the wallet to be unchanged by the replay.
        self.assertEqual(self._balance(), after_first)

    # Require fresh settlement to reuse in-hand state and event authority instead of rereading it.
    def test_fresh_response_reuses_committed_state_and_events(self) -> None:
        # Build provider-shaped state and immutable ledger fixtures.
        store = MemoryState()
        # Build the call-counting gateway.
        gateway = CountingLedgerGateway()
        # Count state loads independently from provider-current updates.
        state_loads = []
        # Count player point reads independently from state documents.
        player_reads = []

        # Load one state snapshot while recording the provider call.
        def load_state(player_id):
            # Record the exact player-scoped read.
            state_loads.append(player_id)
            # Delegate to provider-shaped detached state.
            return store.load(player_id)

        # Return one complete player projection through the point-read seam.
        def get_player(player_id):
            # Record the exact requested wallet identity.
            player_reads.append(player_id)
            # Return the frozen public player shape needed by the response.
            return {"player_id": player_id, "display_name": "Efficiency", "type": "human", "balance": 1040.0, "created_at": "2026-08-19T00:00:00Z", "updated_at": "2026-08-19T00:00:00Z", "status": "active"}

        # Build one winning helper entirely over the measured provider seams.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=_resolve, validate_bet=_validate_bet, entropy_source=lambda _n: 2, ledger_gateway=gateway, state_loader=load_state, state_updater=store.update, get_player=get_player)
        # Execute one fresh winning action.
        result = game.play("measured", {"request_id": "efficient", "face": 3, "stake": 10})
        # Require only the initial state load, two money commits, and one player point read.
        self.assertEqual((1, 2, 0, 1), (len(state_loads), gateway.apply_calls, gateway.find_calls, len(player_reads)))
        # Require response state to come from the updater's committed authority.
        self.assertEqual(store.documents["measured"], result["state"])
        # Require the response ledger to reuse exact in-hand committed event identities.
        self.assertEqual(("ledger-" + result["round"]["round_id"] + ":wager", "ledger-" + result["round"]["round_id"] + ":settlement"), (result["ledger"]["wager"]["ledger_id"], result["ledger"]["settlement"]["ledger_id"]))
        # Replay the same request through stored state.
        replay = game.play("measured", {"request_id": "efficient", "face": 3, "stake": 10})
        # Require replay to add one state read and two required proof reads, but no redundant state reload.
        self.assertEqual((2, 2, 2, 2, True), (len(state_loads), gateway.apply_calls, gateway.find_calls, len(player_reads), replay["replayed"]))

    # Require a request id reused with different wager content to fail closed.
    def test_request_id_content_conflict_fails_closed(self) -> None:
        # Build one game instance.
        game = _game(forced_face=3)
        # Play the original request.
        game.play(self.pid, {"request_id": "r-conflict", "face": 3, "stake": 10})
        # Require a reuse of the same id with a different stake to conflict.
        with self.assertRaises(ConflictError):
            # Attempt the conflicting reuse.
            game.play(self.pid, {"request_id": "r-conflict", "face": 3, "stake": 25})

    # Require settlement to recover deterministically from committed ledger proof after state loss.
    def test_recovers_from_committed_entropy_after_state_loss(self) -> None:
        # Use a provider-shaped in-memory state so it can be wiped mid-round to simulate a crash.
        store = MemoryState()
        # Supply different first and retry draws so any accidental entropy redraw changes the outcome.
        draws = iter((4, 2))
        # Supply different first and retry timestamps so public replay identity is also proven.
        timestamps = iter(("2026-07-26T00:00:00Z", "2026-07-26T00:01:00Z"))
        # Build a game whose loader and atomic updater use the wipeable provider fixture.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=_resolve, validate_bet=_validate_bet, entropy_source=lambda n: next(draws), clock=lambda: next(timestamps), state_loader=store.load, state_updater=store.update)
        # Play a winning round.
        first = game.play(self.pid, {"request_id": "r-crash", "face": 3, "stake": 10})
        # Record the balance after the first settlement.
        after_first = self._balance()
        # Simulate a crash that lost the saved per-player state entirely.
        store.documents.clear()
        # Replay the same request after state loss so proof must come from the ledger alone.
        second = game.play(self.pid, {"request_id": "r-crash", "face": 3, "stake": 10})
        # Require the recovered public round to equal the original committed outcome and timestamp exactly.
        self.assertEqual(second["round"], first["round"])
        # Require state-loss recovery to report that the committed wager proof was replayed.
        self.assertTrue(second["replayed"])
        # Require the wallet not to have moved a second time despite the lost state.
        self.assertEqual(self._balance(), after_first)

    # Require provider-current publication to retain a stale-read sibling and distinct round.
    def test_atomic_publication_merges_provider_current_state(self) -> None:
        # Build one provider-shaped state fixture.
        store = MemoryState()
        # Build one deterministic losing game over the injected provider seams.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=_resolve, validate_bet=_validate_bet, entropy_source=lambda n: 2, state_loader=store.load, state_updater=store.update)

        # Publish one unrelated sibling and distinct round after play captures its stale snapshot.
        def publish_concurrent(current: dict) -> None:
            # Retain unrelated provider metadata that the shared core does not own.
            current["atomic_markers"] = ["concurrent"]
            # Retain a separately committed round that must not be lost.
            current["recent_rounds"] = [{"request_id": "other", "request_fingerprint": "other:1", "round_id": "other-round", "total_return": 0, "public": {"round_id": "other-round"}}]

        # Schedule the concurrent publication at the provider boundary.
        store.before_update = publish_concurrent
        # Execute one distinct losing round from the previously loaded state.
        result = game.play(self.pid, {"request_id": "atomic-merge", "face": 5, "stake": 10})
        # Read exact provider-owned state after the atomic callback.
        persisted = store.documents[self.pid]
        # Preserve both the new round and the provider-current distinct round.
        self.assertEqual(["atomic-merge", "other"], [row["request_id"] for row in persisted["recent_rounds"]])
        # Preserve unrelated sibling metadata through the shared updater.
        self.assertEqual(["concurrent"], persisted["atomic_markers"])
        # Preserve the established response envelope and exact terminal round.
        self.assertEqual(result["round"], persisted["recent_rounds"][0]["public"])

    # Require an optional prepared-state lifecycle to own entropy and ordered recovery stages.
    def test_prepared_lifecycle_adapter_orders_terminal_stages(self) -> None:
        # Build one provider-shaped state fixture for shared terminal publication.
        store = MemoryState()
        # Retain every lifecycle callback name in exact execution order.
        stages = []

        # Provide the bounded lifecycle protocol used by prepared legacy games.
        class Lifecycle:
            # Publish authoritative private entropy before ledger movement.
            def prepare(self, **_context):
                # Record the first lifecycle stage.
                stages.append("prepare")
                # Return provider-owned entropy and time instead of using helper defaults.
                return {"entropy": {"face": 3}, "settled_at": "2026-08-16T00:00:00Z", "replayed": False}

            # Record immutable wager proof publication.
            def wager_committed(self, **_context):
                # Retain exact stage order for the assertion.
                stages.append("wager_committed")

            # Record deterministic settlement-intent publication.
            def settlement_resolved(self, **_context):
                # Retain exact stage order for the assertion.
                stages.append("settlement_resolved")

            # Record positive returned-credit proof publication.
            def settlement_committed(self, **_context):
                # Retain exact stage order for the assertion.
                stages.append("settlement_committed")

            # Freeze provider-owned terminal fields before helper history publication.
            def finalize(self, *, lifecycle_context, **_context):
                # Retain exact stage order for the assertion.
                stages.append("finalize")
                # Return the same bounded context for public-round construction.
                return lifecycle_context

            # Fail the test if a successful wager enters cleanup.
            def wager_failed(self, **_context):
                # Report an impossible successful-path callback immediately.
                raise AssertionError("successful lifecycle invoked wager_failed")

        # Build a winning helper whose default entropy seam must never execute.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=_resolve, validate_bet=_validate_bet, entropy_source=lambda _n: (_ for _ in ()).throw(AssertionError("helper redrew lifecycle entropy")), state_loader=store.load, state_updater=store.update, lifecycle=Lifecycle(), action_key_builder=lambda round_id, action: f"{round_id}:{'return' if action == 'settlement' else action}", legacy_action_detail_key="unit_action_key")
        # Execute one winning round through every positive-settlement lifecycle stage.
        result = game.play(self.pid, {"request_id": "lifecycle-win", "face": 3, "stake": 10})
        # Require lifecycle order, provider entropy, and configured suffix through canonical action evidence.
        self.assertEqual((["prepare", "wager_committed", "settlement_resolved", "settlement_committed", "finalize"], {"face": 3}, f'{result["round"]["round_id"]}:return', f'{result["round"]["round_id"]}:return'), (stages, result["round"]["entropy"], result["ledger"]["settlement"]["details"]["ledger_action_key"], result["ledger"]["settlement"]["details"]["game_action_key"]))
        # Preserve the configured historical audit field beside the authoritative universal key.
        self.assertEqual(f'{result["round"]["round_id"]}:return', result["ledger"]["settlement"]["details"]["unit_action_key"])

    # Require an incomplete lifecycle to fail before entropy or wallet movement.
    def test_incomplete_lifecycle_fails_before_wager(self) -> None:
        # Record the starting balance before constructing the malformed integration.
        starting_balance = self._balance()
        # Build a helper whose object supplies none of the required lifecycle stages.
        game = SimpleWagerGame(game_id="unit_flip", wager_transaction_type="UNIT_FLIP_WAGER_DEBIT", settlement_transaction_type="UNIT_FLIP_SETTLEMENT_CREDIT", entropy=_entropy, resolve=_resolve, validate_bet=_validate_bet, lifecycle=object())
        # Reject the missing prepare stage before any protected action starts.
        with self.assertRaisesRegex(TypeError, "lifecycle is missing prepare"):
            # Attempt one otherwise valid winning request.
            game.play(self.pid, {"request_id": "lifecycle-incomplete", "face": 3, "stake": 10})
        # Require the malformed adapter to leave the wallet untouched.
        self.assertEqual(starting_balance, self._balance())

    # Require an empty or malformed wager to be rejected before any wallet movement.
    def test_invalid_wager_is_rejected(self) -> None:
        # Build one game instance.
        game = _game()
        # Enumerate rejected requests.
        for bad in ({"request_id": "r1"}, {"request_id": "r2", "face": 9, "stake": 5}, {"request_id": "r3", "face": 3, "stake": 0}):
            # Isolate each case.
            with self.subTest(bad=bad):
                # Require a validation error and no balance change.
                with self.assertRaises(ValidationError):
                    # Attempt the invalid wager.
                    game.play(self.pid, bad)
        # Require the wallet to be untouched by any rejected wager.
        self.assertEqual(self._balance(), 1000.0)

    # Require a missing or malformed request id to be rejected.
    def test_request_id_is_required(self) -> None:
        # Require a missing request id to fail closed.
        with self.assertRaises(ValidationError):
            # Attempt a play with no request id.
            _game().play(self.pid, {"face": 3, "stake": 5})

    # Require the deterministic round id to be stable and game-scoped.
    def test_round_id_is_deterministic_and_scoped(self) -> None:
        # Require the same inputs to yield the same round id.
        self.assertEqual(round_id_for("g", "p", "r"), round_id_for("g", "p", "r"))
        # Require a different game to yield a different round id for the same player and request.
        self.assertNotEqual(round_id_for("g1", "p", "r"), round_id_for("g2", "p", "r"))
