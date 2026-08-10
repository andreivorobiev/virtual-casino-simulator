"""Exactly-once settlement, CSPRNG shuffle, and read-side rules-clamp evidence for legacy blackjack and baccarat. (issues #403, #404, #420)"""

# Import environment access so durable state is routed into a disposable root before any casino import binds directories.
import os
# Import tempfile so isolated runtime roots live outside the repository data directory, mirroring tests/storage_tests.py.
import tempfile
# Import pathlib so isolated runtime paths stay platform-safe.
from pathlib import Path

# Create one module-scoped disposable runtime root before casino.config resolves its directory constants.
_RUNTIME_ROOT = tempfile.TemporaryDirectory(prefix="legacy-settlement-")
# Point persistent state at the disposable root so no test can touch the checked-in data directory.
os.environ["CASINO_DATA_DIR"] = str(Path(_RUNTIME_ROOT.name) / "data")
# Point application logs at the disposable root so logger writes never land in the repository.
os.environ["CASINO_LOG_DIR"] = str(Path(_RUNTIME_ROOT.name) / "logs")

# Import deep copies so pre-settlement snapshots stay independent of later mutations.
import copy
# Import random so tests can inject deterministic generators and detect CSPRNG defaults.
import random
# Import threading so racing settlement requests can rendezvous deterministically.
import threading
# Import the dependency-free standard test runner.
import unittest
# Import a two-worker pool so identical settlement requests genuinely overlap.
from concurrent.futures import ThreadPoolExecutor
# Import mock patching so the load seam can force both racers past the same pre-settle state.
from unittest.mock import patch

# Import core services after the environment override so every directory constant is disposable.
from casino.core import history, ledger, players, state_store, storage
# Import the conflict type expected when a changed action identity is reused.
from casino.errors import ConflictError
# Import the baccarat modules under repair.
from casino.games.baccarat import api as baccarat_api
# Import the baccarat engine for clamp and shuffle evidence.
from casino.games.baccarat import engine as baccarat_engine
# Import the blackjack modules under repair.
from casino.games.blackjack import api as blackjack_api
# Import the blackjack engine for clamp and shuffle evidence.
from casino.games.blackjack import engine as blackjack_engine


# Capture route decorators without starting a listener, mirroring tests/api/big_six_wheel_api_tests.py.
class FakeRouter:
    # Initialize route storage keyed by method and path.
    def __init__(self):
        # Store registered handlers for direct invocation.
        self.routes = {}

    # Build one decorator for GET registration.
    def get(self, path):
        # Capture the decorated handler under its method and path.
        return lambda handler: self.routes.setdefault(("GET", path), handler) or handler

    # Build one decorator for POST registration.
    def post(self, path):
        # Capture the decorated handler under its method and path.
        return lambda handler: self.routes.setdefault(("POST", path), handler) or handler

    # Build one decorator for DELETE registration.
    def delete(self, path):
        # Capture the decorated handler under its method and path.
        return lambda handler: self.routes.setdefault(("DELETE", path), handler) or handler


# Prove exactly-once settlement, recovery safety, rules clamping, and CSPRNG shuffles for the two legacy games.
class LegacySettlementTests(unittest.TestCase):
    # Build isolated storage, players, and routers before every test.
    def setUp(self):
        # Create one per-test disposable root so durable action registries never leak between tests.
        self.tmp = tempfile.TemporaryDirectory(prefix="legacy-settlement-case-", ignore_cleanup_errors=True)
        # Derive the per-test data root shared by the provider and player-game state files.
        data_root = Path(self.tmp.name) / "data"
        # Build a JSON provider bound to the per-test data root.
        self.provider = storage.JsonStorageProvider(data_root)
        # Inject the isolated provider for all core storage callers.
        storage.set_provider_for_tests(self.provider)
        # Create the provider directories before any wallet or state write.
        self.provider.ensure_ready()
        # Point the state-store directory globals at the same per-test root so game state files are isolated too.
        self._dir_patches = [patch.object(state_store, "DATA_DIR", data_root), patch.object(state_store, "GAME_DATA_DIR", data_root / "games"), patch.object(state_store, "LOG_DIR", Path(self.tmp.name) / "logs")]
        # Activate every directory patch before handlers run.
        for directory_patch in self._dir_patches:
            # Start one scoped directory override.
            directory_patch.start()
        # Seed the default players so the human wallet exists with its 5000 starting balance.
        storage.get_storage_provider().bootstrap_players(players.default_players())
        # Register the real blackjack routes on an isolated router.
        self.blackjack_router = FakeRouter()
        # Capture the blackjack handlers for direct invocation.
        blackjack_api.register(self.blackjack_router)
        # Register the real baccarat routes on an isolated router.
        self.baccarat_router = FakeRouter()
        # Capture the baccarat handlers for direct invocation.
        baccarat_api.register(self.baccarat_router)

    # Restore shared state after every test.
    def tearDown(self):
        # Stop every scoped directory override.
        for directory_patch in self._dir_patches:
            # Stop one scoped directory override.
            directory_patch.stop()
        # Restore normal provider selection for later tests.
        storage.set_provider_for_tests(None)
        # Remove the per-test disposable root.
        self.tmp.cleanup()

    # Read the human settlement ledger rows for one transaction type.
    def settlement_rows(self, transaction_type):
        # Return only the rows whose type matches the requested settlement family.
        return [row for row in ledger.read_recent("human", 1000) if row.get("transaction_type") == transaction_type]

    # Build one deterministic pre-settlement blackjack state with a fixed round and hand identity.
    def blackjack_pending_state(self, dealer_cards, player_cards, bet=10.0):
        # Start from the engine's house-default state shape.
        state = blackjack_engine.default_state()
        # Fill the shoe with enough filler cards that no mid-test reshuffle can occur.
        state["shoe"] = ["2♠"] * 60
        # Build one active round whose durable identifiers are fixed for stable action keys.
        rnd = {"round_id": "bj_fixed_round", "player_id": "human", "status": "player_turn", "created_at": "2026-07-27T00:00:00.000Z", "dealer": {"cards": list(dealer_cards), "hole_card_hidden": True}, "hands": [{"hand_id": "hand_fixed_1", "cards": list(player_cards), "bet": bet, "status": "active", "is_split_hand": False, "actions": []}], "active_hand_index": 0, "insurance": None, "even_money": None, "settlements": []}
        # Store the round under its fixed identifier.
        state["rounds"] = {"bj_fixed_round": rnd}
        # Return the crafted pre-settlement state.
        return state

    # Wrap the real loader so two racers both read the same pre-settle state before either can commit.
    def rendezvous_loader(self, barrier):
        # Keep the real loader so storage behavior stays authentic.
        real_load = state_store.load_player_game_state

        # Define the loader that pauses each racer after its read completes.
        def load_and_wait(game_id, player_id, factory):
            # Load the durable state exactly as the production handler would.
            loaded = real_load(game_id, player_id, factory)
            # Hold both racers here so each one owns a pre-settlement copy before either settles.
            barrier.wait(timeout=10)
            # Return the pre-settlement state to the paused handler.
            return loaded

        # Return the rendezvous loader for patching into one game api module.
        return load_and_wait

    # Test 1: two concurrent identical stand requests must produce exactly one settlement credit. (issue #403)
    def test_blackjack_concurrent_settlement_credits_exactly_once(self):
        # Persist a deterministic player-nineteen versus dealer-seventeen round that settles without any draw.
        state_store.save_player_game_state("blackjack", "human", self.blackjack_pending_state(["10♠", "7♦"], ["10♥", "9♥"]))
        # Capture the real stand handler under test.
        handler = self.blackjack_router.routes[("POST", r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/stand")]
        # Create the two-party rendezvous that guarantees a true settlement race.
        barrier = threading.Barrier(2)
        # Patch only the blackjack module's loader so both requests read the same pre-settle state.
        with patch.object(blackjack_api, "load_player_game_state", side_effect=self.rendezvous_loader(barrier)):
            # Run both identical requests on overlapping threads.
            with ThreadPoolExecutor(max_workers=2) as pool:
                # Submit the same stand request twice against the one fixed round.
                futures = [pool.submit(handler, {"player_id": "human"}, {}, "bj_fixed_round") for _ in range(2)]
                # Collect both responses because neither racer may fail here.
                results = [future.result(timeout=30) for future in futures]
        # Read every settlement credit row committed by the race.
        rows = self.settlement_rows("BLACKJACK_SETTLEMENT_CREDIT")
        # Require exactly one committed settlement credit despite two settling requests.
        self.assertEqual(1, len(rows))
        # Require the single credit to carry the full nineteen-beats-seventeen payout.
        self.assertEqual(20.0, rows[0]["amount"])
        # Require exactly one balance delta over the 5000 starting wallet.
        self.assertEqual(5020.0, players.get_player("human")["balance"])
        # Require the committing request to report the event and the replaying request to report none.
        self.assertEqual({0, 1}, {len(result["credits"]) for result in results})
        # Iterate both responses for terminal-state evidence.
        for result in results:
            # Require each racer to observe the settled round.
            self.assertEqual("settled", result["round"]["status"])
        # Require exactly one history row because the replaying request must not duplicate side effects.
        self.assertEqual(1, len(history.recent_history(100, "blackjack")))

    # Test 2: replaying settlement from a pre-settle state after a lost save must not credit again. (issue #403)
    def test_blackjack_recovery_after_lost_state_save_does_not_recredit(self):
        # Build the deterministic pre-settlement state used for both the settle and the recovery replay.
        state = self.blackjack_pending_state(["10♠", "7♦"], ["10♥", "9♥"])
        # Snapshot the pre-settlement state before any handler mutates storage.
        snapshot = copy.deepcopy(state)
        # Persist the pre-settlement state as the durable starting point.
        state_store.save_player_game_state("blackjack", "human", state)
        # Capture the real stand handler under test.
        handler = self.blackjack_router.routes[("POST", r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/stand")]
        # Settle once so the ledger commit and the settled state save both complete.
        first = handler({"player_id": "human"}, {}, "bj_fixed_round")
        # Require the first settle to report its newly committed credit.
        self.assertEqual(1, len(first["credits"]))
        # Require the wallet to hold exactly one payout.
        self.assertEqual(5020.0, players.get_player("human")["balance"])
        # Simulate the crash window by restoring the pre-settle state as if the settled save never became durable.
        state_store.save_player_game_state("blackjack", "human", snapshot)
        # Re-run the identical settlement exactly as crash recovery would.
        second = handler({"player_id": "human"}, {}, "bj_fixed_round")
        # Require the recovery replay to report no new credit event.
        self.assertEqual(0, len(second["credits"]))
        # Require the recovery replay to still reach the settled terminal state.
        self.assertEqual("settled", second["round"]["status"])
        # Require the ledger to hold exactly one settlement credit across both runs.
        self.assertEqual(1, len(self.settlement_rows("BLACKJACK_SETTLEMENT_CREDIT")))
        # Require the wallet balance to remain unchanged by the replay.
        self.assertEqual(5020.0, players.get_player("human")["balance"])

    # Test 3: two concurrent baccarat deals must credit one placed bet exactly once. (issue #403)
    def test_baccarat_concurrent_deals_credit_each_bet_exactly_once(self):
        # Place one real player bet through the production bet handler.
        placed = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/bets")]({"player_id": "human", "bet_type": "player", "amount": 10}, {})
        # Capture the durable placement-time bet identity.
        bet_id = placed["bet"]["bet_id"]
        # Require the wager debit to have left the wallet before the race.
        self.assertEqual(4990.0, players.get_player("human")["balance"])
        # Load the persisted state so the shoe can be made deterministic.
        state = state_store.load_player_game_state("baccarat", "human", baccarat_engine.default_state)
        # Stack the shoe tail so pops deal player nine natural against banker seven and the player bet wins twenty.
        state["shoe"] = ["3♣"] * 20 + ["2♦", "K♠", "5♥", "9♠"]
        # Persist the stacked shoe as the shared pre-deal state.
        state_store.save_player_game_state("baccarat", "human", state)
        # Capture the real deal handler under test.
        handler = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/deal")]
        # Create the two-party rendezvous that guarantees a true settlement race.
        barrier = threading.Barrier(2)
        # Collect each racer's terminal outcome kind for order-independent assertions.
        outcomes = []
        # Patch only the baccarat module's loader so both deals read the same open bet.
        with patch.object(baccarat_api, "load_player_game_state", side_effect=self.rendezvous_loader(barrier)):
            # Run both identical deal requests on overlapping threads.
            with ThreadPoolExecutor(max_workers=2) as pool:
                # Submit the same deal request twice against the one open bet.
                futures = [pool.submit(handler, {"player_id": "human"}, {}) for _ in range(2)]
                # Resolve each racer while tolerating the loser's fail-closed conflict.
                for future in futures:
                    # Start protected result collection so the expected conflict is evidence rather than failure.
                    try:
                        # Record one successful deal response.
                        outcomes.append(("ok", future.result(timeout=30)))
                    # Capture the loser's fail-closed changed-identity conflict.
                    except ConflictError:
                        # Record the fail-closed outcome without a duplicate credit.
                        outcomes.append(("conflict", None))
        # Require exactly one winning deal and one fail-closed conflict.
        self.assertEqual(["conflict", "ok"], sorted(kind for kind, _ in outcomes))
        # Read the settlement rows committed for the placed bet identity.
        rows = [row for row in self.settlement_rows("BACCARAT_SETTLEMENT_CREDIT") if (row.get("details") or {}).get("bet_id") == bet_id]
        # Require exactly one committed credit for the single placed bet.
        self.assertEqual(1, len(rows))
        # Require the single credit to carry the even-money player payout.
        self.assertEqual(20.0, rows[0]["amount"])
        # Require exactly one balance delta over the post-wager wallet.
        self.assertEqual(5010.0, players.get_player("human")["balance"])

    # Test 4a: poisoned persisted blackjack rules must settle and reshuffle at clamped house defaults. (issue #404 read-side)
    def test_blackjack_poisoned_rules_settle_at_house_defaults(self):
        # Build a natural twenty-one against a dealer sixteen so settlement uses the payout rate and dealer play draws.
        state = self.blackjack_pending_state(["10♠", "6♦"], ["A♠", "K♠"])
        # Poison the persisted rules with a hostile payout rate and an absurd deck count.
        state["rules"] = {"blackjack_payout": 1000000, "decks": 100000000}
        # Empty the shoe so dealer play must rebuild it from the clamped deck count.
        state["shoe"] = []
        # Persist the poisoned pre-settlement state.
        state_store.save_player_game_state("blackjack", "human", state)
        # Settle through the real stand handler.
        self.blackjack_router.routes[("POST", r"/api/v1/games/blackjack/rounds/(?P<round_id>[^/]+)/stand")]({"player_id": "human"}, {}, "bj_fixed_round")
        # Read the single settlement credit committed under the poisoned rules.
        rows = self.settlement_rows("BLACKJACK_SETTLEMENT_CREDIT")
        # Require exactly one settlement credit.
        self.assertEqual(1, len(rows))
        # Require the natural to pay the clamped three-to-two default rather than the million-to-one poison.
        self.assertEqual(25.0, rows[0]["amount"])
        # Require the wallet to reflect only the clamped payout.
        self.assertEqual(5025.0, players.get_player("human")["balance"])
        # Reload the persisted state for shoe-size evidence.
        saved = state_store.load_player_game_state("blackjack", "human", blackjack_engine.default_state)
        # Require the rebuilt shoe to fit the clamped six-deck default rather than one hundred million decks.
        self.assertTrue(0 < len(saved["shoe"]) <= 6 * 52)
        # Require the bool payout poison to fail closed because True must never count as even money.
        self.assertEqual(25.0, blackjack_engine.natural_payout_due({"rules": {"blackjack_payout": True}}, 10))
        # Require the supported even-money integer rate to stay honored.
        self.assertEqual(20.0, blackjack_engine.natural_payout_due({"rules": {"blackjack_payout": 1}}, 10))
        # Require the supported six-to-five rate to stay honored.
        self.assertEqual(22.0, blackjack_engine.natural_payout_due({"rules": {"blackjack_payout": 1.2}}, 10))
        # Clamp one poisoned switch-and-ceiling pair directly for strict-type evidence.
        clamped = blackjack_engine._sanitized_rules({"rules": {"dealer_hits_soft_17": "yes", "max_split_hands": 99}})
        # Require the truthy string switch to fail closed to the boolean house default.
        self.assertFalse(clamped["dealer_hits_soft_17"])
        # Require the oversized split ceiling to fail closed to the four-hand house default.
        self.assertEqual(4, clamped["max_split_hands"])

    # Test 4b: poisoned persisted baccarat rules must settle and reshuffle at clamped house defaults. (issue #404 read-side)
    def test_baccarat_poisoned_rules_settle_at_house_defaults(self):
        # Build one banker bet fixture for commission evidence.
        banker_bet = {"bet_id": "bacbet_fixed_b", "player_id": "human", "type": "banker", "label": "Banker", "amount": 10}
        # Require the tiny in-range commission to stay honored rather than snapping to the default.
        self.assertEqual(20.0, baccarat_engine.settle_bet(banker_bet, {"winner": "banker"}, {"banker_commission": 0.0000001})["credit"])
        # Require the hostile commission to fail closed to the five-percent house default.
        self.assertEqual(19.5, baccarat_engine.settle_bet(banker_bet, {"winner": "banker"}, {"banker_commission": 5.0})["credit"])
        # Build one tie bet fixture for tie-rate evidence.
        tie_bet = {"bet_id": "bacbet_fixed_t", "player_id": "human", "type": "tie", "label": "Tie", "amount": 10}
        # Require the hostile tie rate to fail closed to the eight-to-one house default.
        self.assertEqual(90.0, baccarat_engine.settle_bet(tie_bet, {"winner": "tie"}, {"tie_payout": 1000})["credit"])
        # Require the supported nine-to-one tie rate to stay honored.
        self.assertEqual(100.0, baccarat_engine.settle_bet(tie_bet, {"winner": "tie"}, {"tie_payout": 9})["credit"])
        # Build one state whose deck count is poisoned for shoe-size evidence.
        state = baccarat_engine.default_state()
        # Poison the persisted deck count far beyond the supported table range.
        state["rules"]["decks"] = 100000000
        # Rebuild the shoe through the clamped consumption path.
        baccarat_engine.ensure_shoe(state)
        # Require the rebuilt shoe to fit the clamped eight-deck default after its burn ritual.
        self.assertTrue(0 < len(state["shoe"]) <= 8 * 52)
        # Require the route-accepted upper cut-card bound to survive read-side sanitation.
        self.assertEqual(104, baccarat_engine._sanitized_rules({"rules": {"cut_cards_remaining": 104}})["cut_cards_remaining"])
        # Require a cut threshold above the route domain to fail closed to the engine fallback.
        self.assertNotIn("cut_cards_remaining", baccarat_engine._sanitized_rules({"rules": {"cut_cards_remaining": 105}}))

    # Test 5: shuffles must accept an injected generator while production defaults to a CSPRNG. (issue #420)
    def test_shuffles_accept_injected_generator_and_default_to_csprng(self):
        # Require identical seeded generators to reproduce the identical blackjack shoe.
        self.assertEqual(blackjack_engine.make_shoe(2, rng=random.Random(1234)), blackjack_engine.make_shoe(2, rng=random.Random(1234)))
        # Require identical seeded generators to reproduce the identical baccarat shoe.
        self.assertEqual(baccarat_engine.make_shoe(2, rng=random.Random(1234)), baccarat_engine.make_shoe(2, rng=random.Random(1234)))
        # Require two default blackjack shuffles to differ as CSPRNG smoke evidence.
        self.assertNotEqual(blackjack_engine.make_shoe(6), blackjack_engine.make_shoe(6))
        # Require two default baccarat shuffles to differ as CSPRNG smoke evidence.
        self.assertNotEqual(baccarat_engine.make_shoe(8), baccarat_engine.make_shoe(8))
        # Require the blackjack production default generator to be the operating-system CSPRNG.
        self.assertIsInstance(blackjack_engine._SYSTEM_RNG, random.SystemRandom)
        # Require the baccarat production default generator to be the operating-system CSPRNG.
        self.assertIsInstance(baccarat_engine._SYSTEM_RNG, random.SystemRandom)
        # Require injected shuffles to reorder without adding or dropping any card.
        self.assertEqual(sorted(blackjack_engine.make_shoe(1)), sorted(blackjack_engine.make_shoe(1, rng=random.Random(7))))

    # Wrap the production baccarat state saver so exactly the finalize-phase save crashes once. (issue #555)
    def baccarat_finalize_crash(self):
        # Keep the production saver so passthrough calls stay real.
        real_save = baccarat_api.save_player_game_state
        # Count saves so only the second save of the interrupted deal request fails.
        calls = {"count": 0}
        # Define the injected saver used during the interrupted request.
        def crashing_save(game_id, player_id, state):
            # Advance the per-request save counter.
            calls["count"] += 1
            # Crash exactly on the finalize save so the commitment survives with credits already applied.
            if calls["count"] == 2:
                # Raise the injected interruption the test asserts on.
                raise RuntimeError("injected finalize crash")
            # Delegate every other save to the production helper.
            return real_save(game_id, player_id, state)
        # Return the counting saver for a patch.object new= injection.
        return crashing_save

    # Seed the deterministic winning shoe used by the commitment-replay proofs.
    def seed_winning_shoe(self):
        # Load the persisted baccarat state for the human player.
        state = state_store.load_player_game_state("baccarat", "human", baccarat_engine.default_state)
        # Install the deterministic shoe whose top four cards give Player a nine-to-seven win.
        state["shoe"] = ["3♣"] * 20 + ["2♦", "K♠", "5♥", "9♠"]
        # Persist the scripted shoe for the deal under test.
        state_store.save_player_game_state("baccarat", "human", state)

    # Prove an interrupted baccarat settlement resumes from its committed coup instead of redealing. (issues #430, #555)
    def test_baccarat_crash_after_commitment_replays_identical_coup(self):
        # Place the durable player bet whose settlement is interrupted.
        placed = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/bets")]({"player_id": "human", "bet_type": "player", "amount": 10}, {})
        # Store the durable bet identity minted at placement.
        bet_id = placed["bet"]["bet_id"]
        # Install the deterministic winning shoe under the placed bet.
        self.seed_winning_shoe()
        # Run the interrupted deal with the finalize-phase save crashing after credits commit.
        with patch.object(baccarat_api, "save_player_game_state", new=self.baccarat_finalize_crash()):
            # Require the injected finalize crash to surface to the caller.
            with self.assertRaises(RuntimeError):
                # Attempt the deal whose settlement is interrupted after crediting.
                self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/deal")]({"player_id": "human"}, {})
        # Read the committed coup persisted by the interrupted request.
        pending = state_store.load_player_game_state("baccarat", "human", baccarat_engine.default_state).get("pending_coup")
        # Require the commitment to carry the dealt cards and durable round identity.
        self.assertIsNotNone(pending)
        # Retry the deal as the post-crash recovery request.
        second = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/deal")]({"player_id": "human"}, {})
        # Require the retry to replay the committed coup under its original round identity.
        self.assertEqual(second["coup"]["round_id"], pending["round_id"])
        # Require the retry to replay the committed cards rather than dealing fresh ones.
        self.assertEqual(second["coup"]["player_cards"], pending["player_cards"])
        # Require exactly one settlement credit for the durable bet identity.
        rows = [row for row in self.settlement_rows("BACCARAT_SETTLEMENT_CREDIT") if (row.get("details") or {}).get("bet_id") == bet_id]
        # Require one credit row across the crash and the retry.
        self.assertEqual(1, len(rows))
        # Require the single credit to pay the deterministic player win.
        self.assertEqual(20.0, rows[0]["amount"])
        # Require the wallet to reflect one debit and one win credit only.
        self.assertEqual(5010.0, players.get_player("human")["balance"])
        # Require replay gating to keep exactly one baccarat outcome history row.
        self.assertEqual(1, len(history.recent_history(100, "baccarat")))
        # Read the persisted state after the successful retry.
        final_state = state_store.load_player_game_state("baccarat", "human", baccarat_engine.default_state)
        # Require the settlement commitment to be released by the retry.
        self.assertNotIn("pending_coup", final_state)
        # Require the shoe to be consumed exactly once across both requests.
        self.assertEqual(20, len(final_state["shoe"]))
        # Require exactly one finalized coup for the interrupted round.
        self.assertEqual(1, len(final_state.get("last_coups", [])))

    # Prove a new baccarat bet resumes a committed settlement first so finalize can never wipe the fresh bet. (issue #555)
    def test_baccarat_pending_settlement_resumes_before_new_bet(self):
        # Place the durable bet whose settlement is interrupted.
        placed = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/bets")]({"player_id": "human", "bet_type": "player", "amount": 10}, {})
        # Store the durable bet identity minted at placement.
        bet_id = placed["bet"]["bet_id"]
        # Install the deterministic winning shoe under the placed bet.
        self.seed_winning_shoe()
        # Run the interrupted deal with the finalize-phase save crashing after credits commit.
        with patch.object(baccarat_api, "save_player_game_state", new=self.baccarat_finalize_crash()):
            # Require the injected finalize crash to surface to the caller.
            with self.assertRaises(RuntimeError):
                # Attempt the deal whose settlement is interrupted after crediting.
                self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/deal")]({"player_id": "human"}, {})
        # Place a fresh bet; the handler must settle the committed coup before mutating.
        follow_up = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/bets")]({"player_id": "human", "bet_type": "banker", "amount": 5}, {})
        # Require the resumed settlement to keep exactly one credit row for the interrupted bet.
        rows = [row for row in self.settlement_rows("BACCARAT_SETTLEMENT_CREDIT") if (row.get("details") or {}).get("bet_id") == bet_id]
        # Require one credit row across the crash and the resume.
        self.assertEqual(1, len(rows))
        # Read the persisted state after the resume-then-bet request.
        state = state_store.load_player_game_state("baccarat", "human", baccarat_engine.default_state)
        # Require the fresh bet to be the only open bet after the resume.
        self.assertEqual([follow_up["bet"]["bet_id"]], [b["bet_id"] for b in state["open_bets"]])
        # Require the interrupted coup to be finalized exactly once.
        self.assertEqual(1, len(state.get("last_coups", [])))
        # Require the settlement commitment to be released by the resume.
        self.assertNotIn("pending_coup", state)

    # Prove baccarat bet refunds commit exactly once under the durable refund identity. (issue #555)
    def test_baccarat_refund_replays_after_crash_window(self):
        # Place the durable bet that is refunded twice across the crash window.
        placed = self.baccarat_router.routes[("POST", r"/api/v1/games/baccarat/bets")]({"player_id": "human", "bet_type": "player", "amount": 10}, {})
        # Store the durable bet identity minted at placement.
        bet_id = placed["bet"]["bet_id"]
        # Locate the durable per-player baccarat state document.
        state_path = state_store.player_game_state_path("baccarat", "human")
        # Snapshot the pre-clear durable state a crash would leave behind.
        pre_clear = state_path.read_bytes()
        # Refund the bet once through the production handler.
        first = self.baccarat_router.routes[("DELETE", r"/api/v1/games/baccarat/bets/(?P<bet_id>[^/]+)")]({"player_id": "human"}, {}, bet_id)
        # Restore the pre-clear snapshot to model a crash between refund commit and state save.
        state_path.write_bytes(pre_clear)
        # Clear the same durable bet a second time as the interrupted retry.
        second = self.baccarat_router.routes[("DELETE", r"/api/v1/games/baccarat/bets/(?P<bet_id>[^/]+)")]({"player_id": "human"}, {}, bet_id)
        # Require both clears to expose the same durable cleared bet.
        self.assertEqual(first["cleared"]["bet_id"], second["cleared"]["bet_id"])
        # Require exactly one refund row for the durable bet identity.
        refunds = [row for row in self.settlement_rows("BACCARAT_BET_REFUND") if (row.get("details") or {}).get("bet_id") == bet_id]
        # Require one refund row across both clears.
        self.assertEqual(1, len(refunds))
        # Require the wallet to end where it started after one debit and one refund.
        self.assertEqual(5000.0, players.get_player("human")["balance"])


# Execute the focused suite when a maintainer invokes this file directly.
if __name__ == "__main__":
    # Use the standard unittest entrypoint so local diagnostics match central execution.
    unittest.main()
