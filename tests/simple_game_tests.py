# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused exactly-once settlement tests for the shared simple-game core. (#73 expansion, GAMECORE-001/002)"""

# Import deep-copy support for provider-shaped state fixtures.
import copy
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative ledger and player boundaries for balance assertions.
from casino.core import ledger, players
# Import the shared wager-and-settle core under test.
from casino.core.simple_game import SimpleWagerGame, round_id_for
# Import the standard bounded application errors every rejection uses.
from casino.errors import ConflictError, ValidationError


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

    # Require a winning round to debit the stake and credit the full return once.
    def test_winning_round_settles_once(self) -> None:
        # Play a stake on the forced winning face.
        result = _game(forced_face=3).play(self.pid, {"request_id": "r-win", "face": 3, "stake": 10})
        # Require the winning outcome and a 50-token return on a 10 stake at 5x.
        self.assertEqual((result["round"]["outcome"], result["round"]["total_return"]), ("win", 50))
        # Require both wallet movements to use storage-enforced atomic action identities.
        self.assertEqual((result["ledger"]["wager"]["details"]["ledger_action_key"], result["ledger"]["settlement"]["details"]["ledger_action_key"]), (f'{result["round"]["round_id"]}:wager', f'{result["round"]["round_id"]}:settlement'))
        # Require the wallet to reflect exactly minus-stake plus-return once.
        self.assertEqual(self._balance(), 1000.0 - 10 + 50)

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
