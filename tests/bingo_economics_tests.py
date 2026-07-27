# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
"""Bingo economics regression tests for issue #405 (guaranteed-win session) and issue #420 (CSPRNG draws)."""

# Import atexit so the module-scoped scratch directory is always released at interpreter exit.
import atexit
# Import inspect so CSPRNG wiring can be proven at source level per the repository test idiom.
import inspect
# Import os so isolation environment variables can be set before any casino import.
import os
# Import random so tests can build seeded deterministic stand-ins for the module CSPRNG.
import random
# Import shutil so the isolated data root can be scrubbed between tests.
import shutil
# Import tempfile so all runtime state lives in a disposable directory per the storage_tests idiom.
import tempfile
# Import the dependency-free standard unit-test runner.
import unittest
# Import Path so scratch-root handling stays platform-safe.
from pathlib import Path

# Create the module-scoped scratch root before casino.config resolves its runtime directories.
_TMP = tempfile.TemporaryDirectory(prefix="bingo_econ_", ignore_cleanup_errors=True)
# Route persistent state into the scratch root so tests can never touch checked-in data files.
os.environ["CASINO_DATA_DIR"] = str(Path(_TMP.name) / "data")
# Route application logs into the scratch root for the same isolation guarantee.
os.environ["CASINO_LOG_DIR"] = str(Path(_TMP.name) / "logs")
# Force the JSON provider so an operator MySQL environment can never receive test traffic.
os.environ["CASINO_STORAGE_PROVIDER"] = "json"
# Release the scratch root when the test interpreter exits.
atexit.register(_TMP.cleanup)

# Import bot profiles after isolation so bots.json lands inside the scratch root.
from casino.bots import profiles
# Import the resolved data root to verify isolation actually bound before any destructive scrub.
from casino.config import DATA_DIR
# Import core services used for balance, ledger, and history assertions.
from casino.core import history, ledger, players, storage
# Import the envelope error expected from fail-closed call paths.
from casino.errors import ConflictError
# Import the bingo API module under test.
from casino.games.bingo import api as bingo_api
# Import the bingo engine module under test.
from casino.games.bingo import engine
# Import the slots engine only to prove its CSPRNG wiring for issue #420.
from casino.games.slots import engine as slots_engine
# Import the real shared router so tests exercise the production dispatch path.
from casino.router import Router

# Capture the untouched module CSPRNG instances before any test monkeypatches them.
_ORIGINAL_BINGO_RNG = engine._rng
# Capture the slots instance for the same issue #420 wiring proof.
_ORIGINAL_SLOTS_RNG = slots_engine._rng
# Record whether module-level environment isolation actually bound casino.config to the scratch root.
_ISOLATED = Path(os.environ["CASINO_DATA_DIR"]).resolve() == Path(DATA_DIR).resolve()


# Provide a deterministic engine._rng stand-in: scripted ball draws first, seeded fallback after.
class _ScriptedRng:
    # Initialize the scripted queue and the seeded fallback generator.
    def __init__(self, script, fallback):
        # Copy the scripted draw order so callers keep their own list.
        self.script = list(script)
        # Store the seeded fallback used once the script is exhausted.
        self.fallback = fallback

    # Return the next scripted ball, verifying it is still drawable.
    def choice(self, seq):
        # Branch while scripted draws remain.
        if self.script:
            # Pop the next scripted ball.
            value = self.script.pop(0)
            # Fail loudly if a scripted ball is no longer in the remaining pool.
            if value not in seq:
                # Raise a test-level failure rather than corrupting the session.
                raise AssertionError(f"scripted ball {value} is not drawable")
            # Return the scripted ball.
            return value
        # Delegate to the seeded fallback once the script is exhausted.
        return self.fallback.choice(seq)

    # Delegate card sampling to the seeded fallback for deterministic layouts.
    def sample(self, population, k):
        # Return the fallback's deterministic sample.
        return self.fallback.sample(population, k)


# Group the issue #405 / #420 economics regression tests.
class BingoEconomicsTests(unittest.TestCase):
    # Build a first-boot isolated casino before every test.
    def setUp(self):
        # Refuse to run destructively when another module imported casino.config before isolation bound.
        if not _ISOLATED:
            # Skip instead of scrubbing a data directory this module does not own.
            self.skipTest("casino.config bound before CASINO_DATA_DIR isolation; run this module standalone")
        # Clear any provider injection left by an earlier test.
        storage.set_provider_for_tests(None)
        # Scrub every file the previous test persisted inside the isolated data root.
        if DATA_DIR.exists():
            # Iterate through the isolated root's children.
            for child in DATA_DIR.iterdir():
                # Remove directories such as games/ recursively.
                if child.is_dir():
                    # Delete the subtree, tolerating transient Windows handles.
                    shutil.rmtree(child, ignore_errors=True)
                # Remove flat files such as players.json, ledger.jsonl, and bots.json.
                else:
                    # Delete the file if it still exists.
                    child.unlink(missing_ok=True)
        # Build the isolated JSON provider over the scratch data root per the storage_tests idiom.
        self.provider = storage.JsonStorageProvider(DATA_DIR)
        # Inject the isolated provider for all core storage callers.
        storage.set_provider_for_tests(self.provider)
        # Ensure the isolated storage directories exist.
        self.provider.ensure_ready()
        # Seed the default human and bot wallets at 5000 each.
        players.save_players(players.default_players())
        # Build a fresh router and register only the bingo routes.
        self.router = Router()
        # Register the production bingo handlers on the shared router.
        bingo_api.register(self.router)
        # Remember the engine RNG active at test start so tearDown can restore it.
        self._entry_rng = engine._rng

    # Restore global state after every test.
    def tearDown(self):
        # Restore the engine RNG replaced by deterministic test doubles.
        engine._rng = self._entry_rng
        # Clear the provider injection for any later suite in this process.
        storage.set_provider_for_tests(None)

    # Dispatch one request through the production router with an unauthenticated local context.
    def _dispatch(self, method, path, body=None):
        # Return the raw handler payload exactly as the HTTP envelope would receive it.
        return self.router.dispatch(method, path, body or {}, context={})

    # Read one player's current wallet balance.
    def _balance(self, player_id):
        # Return the provider-backed balance value.
        return players.get_player(player_id)["balance"]

    # Read one player's ledger as (transaction_type, amount) pairs in commit order.
    def _ledger_rows(self, player_id):
        # Return the simplified rows used by economics assertions.
        return [(row["transaction_type"], row["amount"]) for row in ledger.read_recent(player_id, 200)]

    # Return the four corner numbers of a card in engine coordinate order.
    def _corners(self, card):
        # Map grid corners (0,0),(0,4),(4,0),(4,4) onto the B and O columns.
        return [card["B"][0], card["O"][0], card["B"][4], card["O"][4]]

    # Test 1: the API seats funded bot cards debited from bot wallets, never the human.
    def test_start_session_seats_funded_bot_cards(self):
        # Enable the third default bot so the full three-seat field competes. (issue #405)
        profiles.update_bot("bot_3", {"enabled": True})
        # Purchase one human card through the production /cards route.
        resp = self._dispatch("POST", "/api/v1/games/bingo/cards", {"amount": 5, "pattern": "line"})
        # Read the created session cards.
        cards = resp["session"]["cards"]
        # Verify the session is no longer a guaranteed-win solo race.
        self.assertGreater(len(cards), 1)
        # Verify one human card plus all three eligible bot cards were seated.
        self.assertEqual(4, len(cards))
        # Verify the first card belongs to the human purchaser.
        self.assertEqual("human", cards[0]["player_id"])
        # Verify each competitor card is bot-owned and engine-tagged as a bot card.
        self.assertEqual({"bot_1", "bot_2", "bot_3"}, {c["player_id"] for c in cards[1:]})
        # Verify the engine tagged competitor sources.
        self.assertTrue(all(c["source"] == "bot" for c in cards[1:]))
        # Verify the bounded ball budget was stamped at start. (issue #405)
        self.assertEqual(engine.MAX_CALLS_DEFAULT, resp["session"]["max_calls"])
        # Verify the human paid exactly one card price.
        self.assertEqual(4995.0, self._balance("human"))
        # Verify the human ledger holds only its own purchase and no bot funding.
        self.assertEqual([("BINGO_CARD_PURCHASED", -5.0)], self._ledger_rows("human"))
        # Iterate through the seated bots.
        for bot_id in ("bot_1", "bot_2", "bot_3"):
            # Verify each bot wallet paid its own configured five-token bingo stake.
            self.assertEqual(4995.0, self._balance(bot_id))
            # Verify the bot funding ledger row debited the BOT wallet with the controller event type.
            self.assertEqual([("BOT_BINGO_CARD_PURCHASED", -5.0)], self._ledger_rows(bot_id))

    # Test 2: when a bot card completes first the BOT wallet is credited and the human is not.
    def test_bot_first_completion_pays_bot_wallet_not_human(self):
        # Build deterministic card layouts from a seeded generator.
        engine._rng = random.Random(42)
        # Purchase a four-corners card so a scripted four-ball run can finish a card.
        resp = self._dispatch("POST", "/api/v1/games/bingo/cards", {"amount": 5, "pattern": "four_corners"})
        # Read the seated cards; defaults seat bot_1 and bot_2.
        cards = resp["session"]["cards"]
        # Confirm competitors are present before scripting the race.
        self.assertEqual(3, len(cards))
        # Read the first bot card and its owner.
        bot_card = cards[1]
        # Read the human corner numbers for the disjointness precondition.
        human_corners = set(self._corners(cards[0]["card"]))
        # Read the bot corner numbers that the script will call first.
        bot_corners = self._corners(bot_card["card"])
        # Require differing corner sets so only the bot can complete on the scripted balls.
        self.assertNotEqual(human_corners, set(bot_corners))
        # Script exactly the bot's corner balls so its card completes on the fourth call.
        engine._rng = _ScriptedRng(bot_corners, random.Random(7))
        # Drive four calls through the production /call route.
        for _ in range(4):
            # Advance the session one drawn ball at a time.
            resp = self._dispatch("POST", "/api/v1/games/bingo/call", {})
        # Verify the session ended with the bot as winner.
        self.assertEqual("won", resp["session"]["status"])
        # Verify the winning identity is the bot owner of the scripted card.
        self.assertEqual(bot_card["player_id"], resp["session"]["winner"])
        # Verify the winning card id matches the bot card.
        self.assertEqual(bot_card["card_id"], resp["session"]["winning_card_id"])
        # Verify exactly one settlement credit was produced.
        self.assertEqual(1, len(resp["credits"]))
        # Verify the settlement credited the BOT wallet.
        self.assertEqual(bot_card["player_id"], resp["credits"][0]["player_id"])
        # Verify the human genuinely lost: balance delta is exactly the card cost.
        self.assertEqual(4995.0, self._balance("human"))
        # Verify no payout row ever reached the human ledger.
        self.assertNotIn("BINGO_PAYOUT_CREDIT", [t for t, _ in self._ledger_rows("human")])
        # Verify the bot wallet absorbed its stake and the twelve-times four-corners payout.
        self.assertEqual(5055.0, self._balance(bot_card["player_id"]))
        # Verify the bot ledger shows the funding debit then the payout credit.
        self.assertEqual([("BOT_BINGO_CARD_PURCHASED", -5.0), ("BINGO_PAYOUT_CREDIT", 60.0)], self._ledger_rows(bot_card["player_id"]))

    # Prove a lost state save replays one Bingo payout without a second credit or history row. (issue #403)
    def test_winning_card_settlement_replays_exactly_once(self):
        # Build one terminal winning card with a stable placement-time identity.
        card = {"card_id": "card_exactly_once", "player_id": "human", "amount": 5.0, "card": {"B": [1, 2, 3, 4, 5]}, "status": "won", "winner": True, "payout": 50.0, "winning_coords": [[0, 0]]}
        # Build the terminal session shape consumed by the production settlement helper.
        session = {"session_id": "bingo_exactly_once", "player_id": "human", "amount": 5.0, "pattern": "line", "called": [1, 2, 3, 4, 5], "status": "won", "cards": [card]}
        # Settle the winning card for the first time.
        first = bingo_api.settle_if_done(session)
        # Require one newly committed credit in the first response.
        self.assertEqual(1, len(first))
        # Remove only the volatile display flag to model a crash before the state save.
        card.pop("credited")
        # Re-enter settlement against the same durable session and card identities.
        second = bingo_api.settle_if_done(session)
        # Require the recovery call to expose no second credit.
        self.assertEqual([], second)
        # Read payout rows committed for the winning wallet.
        payout_rows = [row for row in ledger.read_recent("human", 200) if row.get("transaction_type") == "BINGO_PAYOUT_CREDIT"]
        # Require exactly one storage-owned settlement action.
        self.assertEqual(1, len(payout_rows))
        # Require the action key to derive from the durable card identity.
        self.assertEqual("card_exactly_once:settlement", payout_rows[0]["details"]["ledger_action_key"])
        # Require exactly one outcome history row across both calls.
        self.assertEqual(1, len(history.recent_history(20, "bingo")))
        # Require the wallet to include exactly one fifty-token payout.
        self.assertEqual(5050.0, self._balance("human"))

    # Test 3: the call cap ends a never-winning session as no_win and fails closed afterwards.
    def test_call_cap_ends_session_no_win_and_fails_closed(self):
        # Disable both default bots so the capped solo path is exercised directly.
        profiles.update_bot("bot_1", {"enabled": False})
        # Disable the second default bot as well.
        profiles.update_bot("bot_2", {"enabled": False})
        # Build a deterministic solo card.
        engine._rng = random.Random(99)
        # Purchase the solo line card.
        resp = self._dispatch("POST", "/api/v1/games/bingo/cards", {"amount": 5, "pattern": "line"})
        # Confirm no bot could join while disabled.
        self.assertEqual(1, len(resp["session"]["cards"]))
        # Compute the 51 numbers absent from the card so no scripted ball can ever mark it.
        off_card = [n for n in range(1, 76) if n not in set(engine.numbers_on_card(resp["session"]["card"]))]
        # Script only off-card balls so the pattern can never complete within the cap.
        engine._rng = _ScriptedRng(off_card, random.Random(1))
        # Drive the full stream through the production /auto route in one request.
        resp = self._dispatch("POST", "/api/v1/games/bingo/auto", {"max_calls": 75})
        # Verify the stream stopped exactly at the fifty-call budget. (issue #405)
        self.assertEqual(engine.MAX_CALLS_DEFAULT, len(resp["calls"]))
        # Verify the session terminated as a loss.
        self.assertEqual("no_win", resp["session"]["status"])
        # Verify the loss paid nothing.
        self.assertEqual(0, resp["session"]["payout"])
        # Verify no settlement credit was produced.
        self.assertEqual([], resp["credits"])
        # Verify the capped card was marked lost so it can never be credited later.
        self.assertEqual("lost", resp["session"]["cards"][0]["status"])
        # Verify the active slot was released.
        self.assertIsNone(resp["state"]["active_session"])
        # Verify the loss was archived with the recent sessions.
        self.assertEqual("no_win", resp["state"]["last_sessions"][-1]["status"])
        # Verify the human kept only the card debit with no credit back.
        self.assertEqual(4995.0, self._balance("human"))
        # Verify the audit trail recorded one zero-payout no_win session row.
        self.assertIn("no_win", [row["outcome"] for row in history.recent_history(20, "bingo")])
        # Verify a further single call fails closed with the envelope conflict error.
        with self.assertRaises(ConflictError):
            # Attempt one extra call after termination.
            self._dispatch("POST", "/api/v1/games/bingo/call", {})
        # Verify the auto path fails closed identically.
        with self.assertRaises(ConflictError):
            # Attempt one extra auto batch after termination.
            self._dispatch("POST", "/api/v1/games/bingo/auto", {"max_calls": 5})

    # Test 4: across a seeded 30-session loop with three bots and the cap the human nets negative.
    def test_seeded_thirty_session_loop_human_net_is_negative(self):
        # Enable the third bot so all three competitor seats fill each session. (issue #405)
        profiles.update_bot("bot_3", {"enabled": True})
        # Replace the module CSPRNG with one seeded generator covering cards and draws.
        engine._rng = random.Random(20260726)
        # Record the starting human balance.
        start = self._balance("human")
        # Play thirty complete bounded sessions.
        for _ in range(30):
            # Buy a blackout card: its 50x payout against roughly 0.2% capped completion odds makes
            # negative expectation seed-robust, proving the guaranteed-win property is gone. (issue #405)
            resp = self._dispatch("POST", "/api/v1/games/bingo/cards", {"amount": 5, "pattern": "blackout"})
            # Verify the full four-card field was seated.
            self.assertEqual(4, len(resp["session"]["cards"]))
            # Verify the blackout budget was stamped.
            self.assertEqual(engine.MAX_CALLS_BLACKOUT, resp["session"]["max_calls"])
            # Drive the whole session in one bounded auto batch.
            resp = self._dispatch("POST", "/api/v1/games/bingo/auto", {"max_calls": 75})
            # Verify every session terminated within its budget.
            self.assertIsNone(resp["state"]["active_session"])
            # Verify the terminal status is either a genuine win or a capped loss.
            self.assertIn(resp["session"]["status"], ("won", "no_win"))
        # Verify the human's aggregate net over the loop is negative.
        self.assertLess(self._balance("human") - start, 0)

    # Test 5: persisted pre-cap sessions migrate to the default budget and enforce it.
    def test_legacy_session_without_max_calls_enforces_default_cap(self):
        # Build deterministic layouts for the legacy fixtures.
        engine._rng = random.Random(5)
        # Verify the line default budget is stamped at start.
        self.assertEqual(50, engine.start_session(engine.default_state(), "human", 5, "line")["max_calls"])
        # Verify the blackout budget is stamped at start.
        self.assertEqual(60, engine.start_session(engine.default_state(), "human", 5, "blackout")["max_calls"])
        # Build a state holding a session about to reach the budget.
        state = engine.default_state()
        # Start the session whose persisted shape will be aged below.
        sess = engine.start_session(state, "human", 5, "line")
        # Remove the budget field to simulate a session persisted before issue #405 shipped.
        del sess["max_calls"]
        # Compute the 51 numbers absent from the card.
        off_card = [n for n in range(1, 76) if n not in set(engine.numbers_on_card(sess["card"]))]
        # Age the session to one call below the default budget using only unmarkable balls.
        sess["called"] = list(off_card[:49])
        # Draw the fiftieth ball through the production call path.
        migrated, _n = engine.call_next(state)
        # Verify the fail-safe migration stamped the default budget on load. (issue #405)
        self.assertEqual(engine.MAX_CALLS_DEFAULT, migrated["max_calls"])
        # Verify the fiftieth ball ended the legacy session as a capped loss.
        self.assertEqual("no_win", migrated["status"])
        # Verify the loss paid nothing.
        self.assertEqual(0, migrated["payout"])
        # Verify the active slot was released.
        self.assertIsNone(state["active_session"])
        # Build a second state holding a legacy session already at the budget.
        state = engine.default_state()
        # Start the second aged session.
        sess = engine.start_session(state, "human", 5, "line")
        # Remove the budget field again.
        del sess["max_calls"]
        # Recompute the off-card pool for this card.
        off_card = [n for n in range(1, 76) if n not in set(engine.numbers_on_card(sess["card"]))]
        # Age the session exactly to the default budget.
        sess["called"] = list(off_card[:50])
        # Verify the engine refuses any further draw for the exhausted legacy session.
        with self.assertRaises(ConflictError):
            # Attempt the over-budget draw.
            engine.call_next(state)
        # Verify no extra ball was drawn by the refused call.
        self.assertEqual(50, len(state["active_session"]["called"]))
        # Verify the migration stamped the enforced budget even on the refusal path.
        self.assertEqual(engine.MAX_CALLS_DEFAULT, state["active_session"]["max_calls"])

    # Prove both engines draw from OS-entropy CSPRNG instances. (issue #420)
    def test_csprng_instances_wired_into_both_engines(self):
        # Verify the bingo module generator is a SystemRandom instance.
        self.assertIsInstance(_ORIGINAL_BINGO_RNG, random.SystemRandom)
        # Verify the slots module generator is a SystemRandom instance.
        self.assertIsInstance(_ORIGINAL_SLOTS_RNG, random.SystemRandom)
        # Verify card layout sampling routes through the module CSPRNG.
        self.assertIn("_rng.sample", inspect.getsource(engine.make_card))
        # Verify ball draws route through the module CSPRNG.
        self.assertIn("_rng.choice", inspect.getsource(engine.call_next))
        # Verify reel stops route through the slots module CSPRNG.
        self.assertIn("_rng.randrange", inspect.getsource(slots_engine.spin))
        # Verify neither engine still calls the seedable module-level generator for outcomes.
        self.assertNotIn("random.choice", inspect.getsource(engine.call_next))
        # Verify slots no longer calls the seedable module-level generator for stops.
        self.assertNotIn("random.randrange", inspect.getsource(slots_engine.spin))


# Run the focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
