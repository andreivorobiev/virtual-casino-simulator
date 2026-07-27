# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Prove exactly-once roulette and keno settlement money movement plus durable outside-bet layout metadata. (issues #403, #222)
# Import required dependency so the isolated runtime root is removed at interpreter exit.
import atexit
# Import required dependency so persisted state files can be parsed for shape assertions.
import json
# Import required dependency so isolation environment variables are set before casino imports resolve.
import os
# Import required dependency so temp directories can be wiped between and after tests.
import shutil
# Import required dependency so isolated data lives outside the checked-in data directory.
import tempfile
# Import required dependency so tests run under the standard unittest runner.
import unittest
# Import required dependency so isolated paths are platform-safe.
from pathlib import Path
# Import required dependency so RNG stubs are injected with automatic restoration.
from unittest import mock

# Create one isolated runtime root so this module never mutates checked-in data files.
_TMP_ROOT = tempfile.mkdtemp(prefix="csim_roulette_keno_")
# Point persistent state at the isolated root before casino.config resolves DATA_DIR at import time.
os.environ["CASINO_DATA_DIR"] = str(Path(_TMP_ROOT) / "data")
# Point application logs at the isolated root before casino.config resolves LOG_DIR at import time.
os.environ["CASINO_LOG_DIR"] = str(Path(_TMP_ROOT) / "logs")
# Force the JSON provider so tests never touch a configured MySQL database.
os.environ["CASINO_STORAGE_PROVIDER"] = "json"
# Register best-effort removal of the isolated runtime root at interpreter exit.
atexit.register(shutil.rmtree, _TMP_ROOT, ignore_errors=True)

# Import the resolved game-state directory so per-test wipes stay inside the isolated root.
from casino.config import GAME_DATA_DIR
# Import the history reader so replay gating can be asserted on outcome rows.
from casino.core import history
# Import core services after isolation so every write lands in the isolated root.
from casino.core import ledger, players, state_store, storage
# Import the fail-closed conflict type expected by losing settlement racers.
from casino.errors import ConflictError
# Import the keno API module under test.
from casino.games.keno import api as keno_api
# Import the keno engine so the ball-draw RNG can be scripted deterministically.
from casino.games.keno import engine as keno_engine
# Import the roulette API module under test.
from casino.games.roulette import api as roulette_api
# Import the roulette engine so the wheel RNG can be scripted deterministically.
from casino.games.roulette import engine as roulette_engine
# Import the roulette rules so tests bet with exact catalog covered-number sets.
from casino.games.roulette import rules as roulette_rules

# Name the roulette settings route once for handler lookups.
ROULETTE_SETTINGS = r"/api/v1/games/roulette/settings"
# Name the roulette bet-placement route once for handler lookups.
ROULETTE_BETS = r"/api/v1/games/roulette/bets"
# Name the roulette single-bet clear route once for handler lookups.
ROULETTE_CLEAR_ONE = r"/api/v1/games/roulette/bets/(?P<bet_id>[^/]+)"
# Name the roulette spin route once for handler lookups.
ROULETTE_SPIN = r"/api/v1/games/roulette/spin"
# Name the keno ticket-purchase route once for handler lookups.
KENO_TICKETS = r"/api/v1/games/keno/tickets"
# Name the keno draw route once for handler lookups.
KENO_DRAW = r"/api/v1/games/keno/draw"


# Capture registered route handlers without booting the full HTTP application.
class _RecordingRouter:
    # Initialize the handler registry for one test case.
    def __init__(self):
        # Store handlers keyed by method and route pattern.
        self.handlers = {}

    # Build one registration decorator for the given method and pattern.
    def _register(self, method, pattern):
        # Define the decorator that records the handler.
        def deco(fn):
            # Store the handler under its method and pattern.
            self.handlers[(method, pattern)] = fn
            # Return the handler unchanged like the production router.
            return fn
        # Return the recording decorator.
        return deco

    # Record GET handlers like casino.router.Router.get.
    def get(self, pattern):
        # Return the recording decorator for GET routes.
        return self._register("GET", pattern)

    # Record POST handlers like casino.router.Router.post.
    def post(self, pattern):
        # Return the recording decorator for POST routes.
        return self._register("POST", pattern)

    # Record DELETE handlers like casino.router.Router.delete.
    def delete(self, pattern):
        # Return the recording decorator for DELETE routes.
        return self._register("DELETE", pattern)


# Script the roulette wheel RNG with a fixed pocket sequence.
class _ScriptedWheel:
    # Store the scripted pockets in call order.
    def __init__(self, *pockets):
        # Keep a private mutable copy of the scripted pockets.
        self._pockets = list(pockets)

    # Return the next scripted pocket instead of a random wheel slot.
    def choice(self, seq):
        # Pop the next scripted pocket in order.
        return self._pockets.pop(0)


# Script the keno ball RNG with a fixed twenty-number draw.
class _ScriptedBalls:
    # Store the scripted drawn numbers.
    def __init__(self, drawn):
        # Keep a private copy of the scripted draw.
        self._drawn = list(drawn)

    # Return the scripted draw instead of a random sample.
    def sample(self, population, k):
        # Return a fresh copy so callers cannot mutate the script.
        return list(self._drawn)


# Prove exactly-once settlement identities and persisted layout metadata through the public API handlers.
class RouletteKenoSettlementTests(unittest.TestCase):
    # Prepare an isolated provider and clean game state before each test.
    def setUp(self):
        # Create a per-test provider root so ledger and player files never leak between tests.
        self._provider_root = Path(tempfile.mkdtemp(prefix="provider_", dir=_TMP_ROOT))
        # Build a JSON provider bound to the per-test root.
        self._provider = storage.JsonStorageProvider(self._provider_root)
        # Inject the isolated provider for all core storage callers.
        storage.set_provider_for_tests(self._provider)
        # Ensure provider directories exist before seeding players.
        self._provider.ensure_ready()
        # Seed the default player document so the human wallet starts at 5000.
        players.save_players(players.default_players())
        # Remove per-player game state files left inside the shared isolated root by earlier tests.
        shutil.rmtree(GAME_DATA_DIR, ignore_errors=True)

    # Restore normal provider selection after each test.
    def tearDown(self):
        # Clear provider injection so later tests rebuild cleanly.
        storage.set_provider_for_tests(None)

    # Register the production roulette routes on a fresh recording router.
    def _roulette_routes(self):
        # Build a fresh recording router for this test.
        router = _RecordingRouter()
        # Register the production roulette handlers.
        roulette_api.register(router)
        # Return the captured handlers.
        return router.handlers

    # Register the production keno routes on a fresh recording router.
    def _keno_routes(self):
        # Build a fresh recording router for this test.
        router = _RecordingRouter()
        # Register the production keno handlers.
        keno_api.register(router)
        # Return the captured handlers.
        return router.handlers

    # Return the catalog entry for one bet type and optional label on the double-zero table.
    def _catalog_entry(self, bet_type, label=None):
        # Iterate the double-zero catalog for the requested entry.
        for entry in roulette_rules.catalog("double"):
            # Match on type and optionally on label.
            if entry["type"] == bet_type and (label is None or entry["label"] == label):
                # Return the first matching catalog entry.
                return entry
        # Fail the test when the catalog entry is missing.
        self.fail(f"catalog entry {bet_type}/{label} not found")

    # Place one manual red bet through the public bets handler.
    def _place_red_bet(self, handlers, amount=10.0):
        # Read the red catalog entry so the placement carries the exact covered-number set.
        red = self._catalog_entry("red")
        # Place the bet through the production handler.
        response = handlers[("POST", ROULETTE_BETS)]({"bet_type": "red", "amount": amount, "covered_numbers": red["covered_numbers"]}, {})
        # Return the durable placed-bet item.
        return response["bet"]

    # Return the human ledger rows committed under one storage action key.
    def _action_rows(self, action_key):
        # Filter recent human rows by the storage-owned action-key marker.
        return [row for row in ledger.read_recent("human", 200) if (row.get("details") or {}).get("ledger_action_key") == action_key]

    # Prove two racing spins settle one durable bet exactly once and the loser fails closed. (issue #403)
    def test_racing_spins_credit_one_settlement_and_fail_closed(self):
        # Capture the production roulette handlers.
        handlers = self._roulette_routes()
        # Select la partage so the two scripted racers produce different settlement amounts for the same bet.
        handlers[("POST", ROULETTE_SETTINGS)]({"zero_rule": "la_partage"}, {})
        # Place one durable red bet before the race.
        bet = self._place_red_bet(handlers)
        # Locate the durable per-player roulette state document.
        state_path = state_store.player_game_state_path("roulette", "human")
        # Snapshot the pre-spin durable state both racers observe.
        pre_spin = state_path.read_bytes()
        # Run racer A with a scripted red winner.
        with mock.patch.object(roulette_engine, "_SYSTEM_RANDOM", _ScriptedWheel("1")):
            # Settle the round with the first racing spin.
            first = handlers[("POST", ROULETTE_SPIN)]({}, {})
        # Verify racer A settled the bet as a first-time win.
        self.assertEqual(first["settlements"][0]["settlement"]["outcome"], "win")
        # Verify racer A committed a fresh, non-replayed credit.
        self.assertFalse(first["settlements"][0]["replayed"])
        # Restore the pre-spin snapshot so racer B settles the same durable round and bet.
        state_path.write_bytes(pre_spin)
        # Run racer B with a scripted green zero so la partage mints a different half-loss credit amount.
        with mock.patch.object(roulette_engine, "_SYSTEM_RANDOM", _ScriptedWheel("0")):
            # Require the losing racer to surface the fail-closed conflict instead of double-crediting.
            with self.assertRaises(ConflictError):
                # Attempt the second racing spin against the already-settled bet identity.
                handlers[("POST", ROULETTE_SPIN)]({}, {})
        # Read every committed row for the durable settlement action key.
        rows = self._action_rows(f"{bet['bet_id']}:settlement")
        # Require exactly one settlement credit for the bet identity.
        self.assertEqual(len(rows), 1)
        # Require the single committed credit to be racer A's full win return.
        self.assertEqual(rows[0]["amount"], 20.0)
        # Require the wallet to reflect one debit and one win credit only.
        self.assertEqual(players.get_player("human")["balance"], 5010.0)
        # Require the losing racer to have appended no duplicate outcome history.
        self.assertEqual(len(history.recent_history(50, "roulette")), 1)

    # Prove clearing the same durable bet twice refunds it exactly once. (issue #403)
    def test_replayed_clear_refunds_bet_exactly_once(self):
        # Capture the production roulette handlers.
        handlers = self._roulette_routes()
        # Place one durable red bet to refund.
        bet = self._place_red_bet(handlers)
        # Locate the durable per-player roulette state document.
        state_path = state_store.player_game_state_path("roulette", "human")
        # Snapshot the pre-clear durable state so the clear can be replayed.
        pre_clear = state_path.read_bytes()
        # Clear the bet the first time through the production handler.
        first = handlers[("DELETE", ROULETTE_CLEAR_ONE)]({}, {}, bet["bet_id"])
        # Restore the pre-clear snapshot to model a crash between refund commit and state save.
        state_path.write_bytes(pre_clear)
        # Clear the same durable bet a second time as the interrupted retry.
        second = handlers[("DELETE", ROULETTE_CLEAR_ONE)]({}, {}, bet["bet_id"])
        # Read every committed row for the durable refund action key.
        rows = self._action_rows(f"{bet['bet_id']}:refund")
        # Require exactly one refund row for the bet identity.
        self.assertEqual(len(rows), 1)
        # Require the replayed clear to return the original immutable refund event.
        self.assertEqual(second["ledger"]["ledger_id"], first["ledger"]["ledger_id"])
        # Require the wallet to end where it started after one debit and one refund.
        self.assertEqual(players.get_player("human")["balance"], 5000.0)

    # Prove two racing keno draws pay one durable ticket exactly once and the loser fails closed. (issue #403)
    def test_racing_keno_draws_pay_one_ticket_exactly_once(self):
        # Capture the production keno handlers.
        handlers = self._keno_routes()
        # Purchase one five-spot ticket before the race.
        purchase = handlers[("POST", KENO_TICKETS)]({"spots": [1, 2, 3, 4, 5], "amount": 5}, {})
        # Store the durable ticket identity minted at purchase.
        ticket_id = purchase["ticket"]["ticket_id"]
        # Locate the durable per-player keno state document.
        state_path = state_store.player_game_state_path("keno", "human")
        # Snapshot the pre-draw durable state both racers observe.
        pre_draw = state_path.read_bytes()
        # Run racer A with a scripted draw that catches all five spots.
        with mock.patch.object(keno_engine, "_SYSTEM_RANDOM", _ScriptedBalls(list(range(1, 21)))):
            # Settle the ticket with the first racing draw.
            first = handlers[("POST", KENO_DRAW)]({}, {})
        # Verify racer A paid the five-catch multiplier as a fresh, non-replayed credit.
        self.assertEqual(first["settlements"][0]["result"]["payout"], 2500.0)
        # Verify racer A's payout carried a non-replayed marker.
        self.assertFalse(first["settlements"][0]["replayed"])
        # Restore the pre-draw snapshot so racer B settles the same durable ticket.
        state_path.write_bytes(pre_draw)
        # Run racer B with a scripted draw that catches only three spots for a different payout amount.
        with mock.patch.object(keno_engine, "_SYSTEM_RANDOM", _ScriptedBalls([1, 2, 3] + list(range(21, 38)))):
            # Require the losing racer to surface the fail-closed conflict instead of double-paying.
            with self.assertRaises(ConflictError):
                # Attempt the second racing draw against the already-paid ticket identity.
                handlers[("POST", KENO_DRAW)]({}, {})
        # Read every committed row for the durable payout action key.
        rows = self._action_rows(f"{ticket_id}:payout")
        # Require exactly one payout row for the ticket identity.
        self.assertEqual(len(rows), 1)
        # Require the wallet to reflect one purchase debit and one payout credit only.
        self.assertEqual(players.get_player("human")["balance"], 5000.0 - 5.0 + 2500.0)

    # Prove a crash-window re-run replays the committed settlement without a second credit. (issue #403)
    def test_crash_window_rerun_replays_settlement_without_second_credit(self):
        # Capture the production roulette handlers.
        handlers = self._roulette_routes()
        # Place one durable red bet before the interrupted settlement.
        bet = self._place_red_bet(handlers)
        # Locate the durable per-player roulette state document.
        state_path = state_store.player_game_state_path("roulette", "human")
        # Snapshot the pre-spin durable state that a crash would leave behind.
        pre_spin = state_path.read_bytes()
        # Settle the round once with a scripted red winner.
        with mock.patch.object(roulette_engine, "_SYSTEM_RANDOM", _ScriptedWheel("1")):
            # Commit the settlement credit during the first run.
            first = handlers[("POST", ROULETTE_SPIN)]({}, {})
        # Restore the pre-spin snapshot to model a crash after the ledger commit but before the state save.
        state_path.write_bytes(pre_spin)
        # Re-run the spin with a different scripted red pocket that settles to the same credit amount.
        with mock.patch.object(roulette_engine, "_SYSTEM_RANDOM", _ScriptedWheel("3")):
            # Settle the recovered round as the post-crash retry.
            second = handlers[("POST", ROULETTE_SPIN)]({}, {})
        # Require the retry to mark the settlement as a storage replay.
        self.assertTrue(second["settlements"][0]["replayed"])
        # Require the retry to return the original immutable credit event.
        self.assertEqual(second["settlements"][0]["ledger"]["ledger_id"], first["settlements"][0]["ledger"]["ledger_id"])
        # Read every committed row for the durable settlement action key.
        rows = self._action_rows(f"{bet['bet_id']}:settlement")
        # Require exactly one settlement credit across both runs.
        self.assertEqual(len(rows), 1)
        # Require the wallet to reflect one debit and one win credit only.
        self.assertEqual(players.get_player("human")["balance"], 5010.0)
        # Require replay gating to prevent a duplicate outcome history row.
        self.assertEqual(len(history.recent_history(50, "roulette")), 1)

    # Prove a placed dozen bet persists the catalog layout kind for outside-chip rendering. (issue #222)
    def test_placed_dozen_bet_persists_catalog_layout_kind(self):
        # Capture the production roulette handlers.
        handlers = self._roulette_routes()
        # Read the second-dozen catalog entry so assertions compare against the catalog value.
        dozen = self._catalog_entry("dozen", "2nd 12")
        # Place the dozen bet through the production handler.
        response = handlers[("POST", ROULETTE_BETS)]({"bet_type": "dozen", "amount": 5, "covered_numbers": dozen["covered_numbers"]}, {})
        # Require the placed-bet response item to carry the catalog layout kind.
        self.assertEqual(response["bet"]["layout_kind"], dozen["layout_kind"])
        # Read the persisted per-player roulette state document from disk.
        persisted = json.loads(state_store.player_game_state_path("roulette", "human").read_text(encoding="utf-8"))
        # Read the persisted open bets for the current round.
        open_bets = persisted["open_round"]["bets"]
        # Require exactly one persisted open bet.
        self.assertEqual(len(open_bets), 1)
        # Require the persisted open bet to carry the catalog layout kind.
        self.assertEqual(open_bets[0]["layout_kind"], dozen["layout_kind"])
        # Require the catalog to classify dozen bets as outside-layout bets.
        self.assertEqual(dozen["layout_kind"], "outside")


# Run the module directly through the standard unittest entry point.
if __name__ == "__main__":
    # Execute all settlement and layout tests.
    unittest.main()
