# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Bingo economics regression tests for issue #405 (guaranteed-win session), #420 (CSPRNG draws), and #452 (house-edged paytable and guaranteed competitor field)."""

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
        self.provider.bootstrap_players(players.default_players())
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
        # Read the seated cards; the two default bots fund two seats and a house spoiler fills the third. (issue #452)
        cards = resp["session"]["cards"]
        # Confirm the guaranteed full four-card field is present before scripting the race. (issue #452)
        self.assertEqual(4, len(cards))
        # Confirm the third competitor seat is the synthetic house spoiler. (issue #452)
        self.assertEqual("house", cards[3]["source"])
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
        # Verify the bot wallet absorbed its stake and the rebalanced 6.3x four-corners payout. (issue #452)
        self.assertEqual(5026.5, self._balance(bot_card["player_id"]))
        # Verify the bot ledger shows the funding debit then the rebalanced payout credit. (issue #452)
        self.assertEqual([("BOT_BINGO_CARD_PURCHASED", -5.0), ("BINGO_PAYOUT_CREDIT", 31.5)], self._ledger_rows(bot_card["player_id"]))

    # Prove a lost state save replays one Bingo payout without a second credit or history row. (issue #403)
    def test_winning_card_settlement_replays_exactly_once(self):
        # Build one terminal winning card with a stable placement-time identity.
        card = {"card_id": "card_exactly_once", "player_id": "human", "amount": 5.0, "card": {"B": [1, 2, 3, 4, 5]}, "status": "won", "winner": True, "payout": 17.0, "winning_coords": [[0, 0]]}
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
        # Require the wallet to include exactly one rebalanced line payout. (issue #452)
        self.assertEqual(5017.0, self._balance("human"))

    # Test 3: the call cap ends a never-winning fresh session as no_win and the engine then fails closed. (issue #405)
    def test_call_cap_ends_fresh_session_no_win_and_fails_closed(self):
        # Build a deterministic solo session directly on the engine so the cap path is isolated from the competitor field.
        engine._rng = random.Random(99)
        # Start from a fresh default document.
        state = engine.default_state()
        # Start a solo human line session with no competitor cards.
        sess = engine.start_session(state, "human", 5, "line", bot_players=[])
        # Compute the 51 numbers absent from the card so no drawn ball can ever mark it.
        off_card = [n for n in range(1, 76) if n not in set(engine.numbers_on_card(sess["card"]))]
        # Script only off-card balls so the single card can never complete within the cap.
        engine._rng = _ScriptedRng(off_card, random.Random(1))
        # Draw the full default budget through the production engine call path.
        for _ in range(engine.MAX_CALLS_DEFAULT):
            # Advance one drawn ball at a time.
            engine.call_next(state)
        # Verify the session terminated as a capped loss. (issue #405)
        self.assertEqual("no_win", sess["status"])
        # Verify the loss paid nothing.
        self.assertEqual(0, sess["payout"])
        # Verify the capped card was marked lost so it can never be credited later.
        self.assertEqual("lost", sess["cards"][0]["status"])
        # Verify the active slot was released.
        self.assertIsNone(state["active_session"])
        # Verify the loss was archived with the recent sessions.
        self.assertEqual("no_win", state["last_sessions"][-1]["status"])
        # Verify the engine refuses any further draw once the session has terminated.
        with self.assertRaises(ConflictError):
            # Attempt one extra call after termination.
            engine.call_next(state)

    # Test 3b: the guaranteed field seats house spoilers when no bot can fund a seat, and house cards are never credited. (issue #452)
    def test_disabled_bots_still_seat_full_house_field(self):
        # Disable every default bot so no bot wallet can fund a competitor seat.
        profiles.update_bot("bot_1", {"enabled": False})
        # Disable the second default bot as well.
        profiles.update_bot("bot_2", {"enabled": False})
        # Build a deterministic layout.
        engine._rng = random.Random(3)
        # Purchase a human line card through the production route.
        resp = self._dispatch("POST", "/api/v1/games/bingo/cards", {"amount": 5, "pattern": "line"})
        # Read the seated cards.
        cards = resp["session"]["cards"]
        # Verify the field is still full despite every bot being disabled. (issue #452)
        self.assertEqual(4, len(cards))
        # Verify the human holds the first card.
        self.assertEqual("human", cards[0]["player_id"])
        # Verify all three competitor seats are synthetic house spoilers. (issue #452)
        self.assertTrue(all(c["source"] == "house" for c in cards[1:]))
        # Verify the human paid exactly one card price and no bot wallet was touched.
        self.assertEqual(4995.0, self._balance("human"))
        # Verify the synthetic house identity was never created as a real player.
        self.assertNotIn(bingo_api.HOUSE_COMPETITOR_ID, [p["player_id"] for p in players.list_players()])

    # Test 3c: settlement never credits a winning house spoiler card. (issue #452)
    def test_settlement_skips_house_cards(self):
        # Build a terminal session whose only winning card is a house spoiler.
        house = {"card_id": "hc", "player_id": bingo_api.HOUSE_COMPETITOR_ID, "amount": 5.0, "card": {}, "status": "won", "winner": True, "payout": 0, "source": "house", "winning_coords": []}
        # Build the session shape the settlement helper consumes.
        sess = {"session_id": "s_house", "player_id": "human", "amount": 5.0, "pattern": "line", "called": [1, 2, 3, 4, 5], "status": "won", "cards": [house]}
        # Verify settlement produces no credit for the house winner.
        self.assertEqual([], bingo_api.settle_if_done(sess))
        # Verify no payout row ever reached the synthetic house identity.
        self.assertEqual([], [r for r in ledger.read_recent(bingo_api.HOUSE_COMPETITOR_ID, 50) if r.get("transaction_type") == "BINGO_PAYOUT_CREDIT"])

    # Test 3d: resetting a fresh session refunds only real cards and never a synthetic house spoiler. (issue #452)
    def test_reset_before_calls_skips_house_cards(self):
        # Build a deterministic layout.
        engine._rng = random.Random(7)
        # Buy a card so a fresh session with two funded bots plus one house spoiler is seated.
        resp = self._dispatch("POST", "/api/v1/games/bingo/cards", {"amount": 5, "pattern": "line"})
        # Confirm the guaranteed four-card field including the house spoiler.
        self.assertEqual(4, len(resp["session"]["cards"]))
        # Reset before any ball is called through the production route.
        resp = self._dispatch("POST", "/api/v1/games/bingo/reset", {})
        # Verify the reset refunded only the human and the two funded bots, never the house spoiler. (issue #452)
        self.assertEqual(3, len(resp["refunds"]))
        # Verify the human's stake was returned in full.
        self.assertEqual(5000.0, self._balance("human"))
        # Verify no refund row targeted the synthetic house identity.
        self.assertEqual([], [r for r in ledger.read_recent(bingo_api.HOUSE_COMPETITOR_ID, 50) if r.get("transaction_type") == "BINGO_CARD_REFUND"])
        # Verify the active slot was released.
        self.assertIsNone(resp["state"]["active_session"])

    # Test 4: every pattern's calibrated multiplier yields a modest house edge at the guaranteed field. (issue #452)
    def test_every_pattern_is_house_edged(self):
        # Read the calibrated paytable and the Monte-Carlo win probabilities it was derived from.
        paytable, probability = engine.PAYTABLE, engine.MEASURED_WIN_PROBABILITY
        # Require every published pattern to carry a measured win probability.
        self.assertEqual(set(paytable), set(probability))
        # Check each pattern's expected return against its stake.
        for pattern, multiplier in paytable.items():
            # Compute expected return per unit staked: P(win) times the total-return multiplier.
            expected_return = probability[pattern] * multiplier
            # Require a house edge: the expected return must be strictly below the stake. (issue #452)
            self.assertLess(expected_return, 1.0, f"{pattern} is player-positive at x{multiplier}")
            # Require the edge to stay modest rather than punishing, matching the ~0.9/P calibration.
            self.assertLessEqual(0.05, 1.0 - expected_return, f"{pattern} edge is unexpectedly small")
            # Require the edge to remain within a sane band so a future miscalibration is caught.
            self.assertLessEqual(1.0 - expected_return, 0.16, f"{pattern} edge is unexpectedly large")
        # Require the prior player-positive multipliers to be gone so the exploit cannot silently return.
        self.assertNotEqual({"line": 10, "four_corners": 12, "postage_stamp": 15, "blackout": 50}, paytable)

    # Test 4b: the calibrated payouts settle at the expected rebalanced amounts. (issue #452)
    def test_payout_for_uses_rebalanced_multipliers(self):
        # Verify the line payout reflects the rebalanced 3.4x multiplier on a five-token stake.
        self.assertEqual(17.0, engine.payout_for("line", 5))
        # Verify the four-corners payout reflects the rebalanced 6.3x multiplier.
        self.assertEqual(31.5, engine.payout_for("four_corners", 5))
        # Verify the postage-stamp payout reflects the rebalanced 3.5x multiplier.
        self.assertEqual(17.5, engine.payout_for("postage_stamp", 5))
        # Verify blackout became a genuine long-shot jackpot rather than a punishing +90% house edge.
        self.assertEqual(3250.0, engine.payout_for("blackout", 5))

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
