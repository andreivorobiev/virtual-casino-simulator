# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free proof for the #323 shell and Roulette payload projections."""

# Import deterministic JSON sizing for before/after projection assertions.
import json
# Import repository-root paths for static call-site coverage.
from pathlib import Path
# Import the standard test framework used by the central API gate.
import unittest
# Import bounded mocks so tests never read shared runtime state.
from unittest import mock

# Import the application router whose nested handler owns the shell projection.
from casino import app
# Import the isolated Roulette registrar and response projection.
from casino.games.roulette import api as roulette_api
# Import a fresh route table for game-local listener-free calls.
from casino.router import Router


# Resolve the exact checkout root without retaining a machine-specific path in evidence.
ROOT = Path(__file__).resolve().parents[2]


# Prove opt-in compact responses skip only redundant static or unrelated state. (TEST-166)
class PerformanceProjectionTests(unittest.TestCase):
    # Prove the shell projection avoids history, ledger, player-list, and duplicate catalog work.
    def test_shell_projection_preserves_navigation_and_presence_without_unrelated_state(self):
        # Build one descriptor large enough to make the full/compact comparison meaningful.
        games = [{"id": "roulette", "frontend": {"module": "./games/roulette.js", "i18n_domain": "games/roulette"}, "description": "x" * 512}]
        # Build bounded full-response rows that the shell never reads.
        history_rows = [{"player_id": "player-1", "summary": "history" * 32} for _ in range(25)]
        # Build bounded full-response ledger rows that the shell never reads.
        ledger_rows = [{"player_id": "player-1", "details": "ledger" * 32} for _ in range(25)]
        # Patch every runtime owner before building the shared route table.
        with mock.patch.object(app, "list_games", return_value=games), mock.patch.object(app, "catalog_summary", return_value={"large": "catalog" * 256}) as catalog_summary, mock.patch.object(app.players, "list_players", return_value=[{"player_id": "player-1"}]) as list_players, mock.patch.object(app.players, "get_player", return_value={"player_id": "player-1"}) as get_player, mock.patch.object(app.history, "recent_history", return_value=history_rows) as recent_history, mock.patch.object(app.ledger, "read_recent", return_value=ledger_rows) as recent_ledger, mock.patch.object(app.auth, "online_user_count", return_value=3), mock.patch.object(app.auth, "is_admin", return_value=False):
            # Build the complete application router without opening a listener.
            router = app.build_router()
            # Request the exact opt-in projection used by the current shell.
            compact = router.dispatch("GET", "/api/v1/casino/state?projection=shell", context={"bound_player_id": "player-1", "user": {"player_id": "player-1"}})
            # Require the complete compact allowlist and descriptor-driven navigation.
            self.assertEqual(set(compact), {"version", "games", "online_player_count"})
            # Require current presence and catalog descriptors to remain available.
            self.assertEqual((compact["games"], compact["online_player_count"]), (games, 3))
            # Prove unrelated storage and duplicate catalog owners were never called.
            for dependency in (catalog_summary, list_players, get_player, recent_history, recent_ledger):
                # Fail when the compact path accidentally reintroduces expensive full-state work.
                dependency.assert_not_called()
            # Request the unchanged complete response through the legacy default path.
            complete = router.dispatch("GET", "/api/v1/casino/state", context={"bound_player_id": "player-1", "user": {"player_id": "player-1"}})
            # Require every frozen complete-response key to remain published.
            self.assertEqual(set(complete), {"version", "games", "catalog", "players", "online_player_count", "recent_history", "recent_ledger"})
            # Require the legacy path to retain its original player, history, ledger, and catalog values.
            self.assertEqual((complete["recent_history"], complete["recent_ledger"], complete["online_player_count"]), (history_rows, ledger_rows, 3))
            # Prove the shell projection materially reduces deterministic response bytes.
            self.assertLess(len(json.dumps(compact, sort_keys=True)), len(json.dumps(complete, sort_keys=True)) // 2)

    # Prove Roulette removes only the immutable catalog when the current client opts in.
    def test_roulette_play_projection_preserves_player_state_stats_and_legacy_catalog(self):
        # Build one representative persisted state with the accepted single-zero mode.
        state = {"mode": "single", "zero_rule": "normal", "open_round": {"bets": []}, "last_results": []}
        # Build a deliberately large static catalog to pin meaningful payload reduction.
        catalog = [{"id": f"bet-{index}", "label": "catalog-label-" * 16, "covered_numbers": [str(index % 37)]} for index in range(256)]
        # Build one player row reused by the primary and scoreboard projections.
        player = {"player_id": "player-1", "display_name": "Player", "balance": 1000, "type": "human"}
        # Build the game-local listener-free router.
        router = Router()
        # Register only Roulette routes so no other game state is imported into the proof.
        roulette_api.register(router)
        # Patch state, player, catalog, and stats owners with deterministic values.
        with mock.patch.object(roulette_api, "load_player_game_state", return_value=state), mock.patch.object(roulette_api.players, "get_player", return_value=player), mock.patch.object(roulette_api.players, "list_players", return_value=[player]), mock.patch.object(roulette_api.rules, "catalog", return_value=catalog) as catalog_builder, mock.patch.object(roulette_api.engine, "stats", return_value={"roll_count": 0}):
            # Bind requests to the authenticated player through the shared resolver.
            context = {"bound_player_id": "player-1", "user": {"player_id": "player-1"}}
            # Request the unchanged complete legacy response.
            complete = router.dispatch("GET", "/api/v1/games/roulette/state", context=dict(context))
            # Require the complete catalog and every player-specific response field.
            self.assertEqual((complete["catalog"], set(complete)), (catalog, {"game", "state", "player", "players", "catalog", "stats"}))
            # Request the exact compact projection used by the current Roulette module.
            compact = router.dispatch("GET", "/api/v1/games/roulette/state?projection=play", context=dict(context))
            # Require only the static catalog to be absent.
            self.assertEqual(set(compact), {"game", "state", "player", "players", "stats"})
            # Require every non-catalog value to remain byte-equivalent after serialization.
            self.assertEqual(compact, {key: value for key, value in complete.items() if key != "catalog"})
            # Prove compact state did not rebuild the static rules catalog.
            self.assertEqual(catalog_builder.call_count, 1)
            # Require duplicate projection values to fail closed into the complete compatibility response.
            ambiguous = router.dispatch("GET", "/api/v1/games/roulette/state?projection=play&projection=play", context=dict(context))
            # Preserve the catalog whenever query parsing reports ambiguity.
            self.assertEqual(ambiguous["catalog"], catalog)
            # Prove player-state payload bytes shrink materially without changing money or state.
            self.assertLess(len(json.dumps(compact, sort_keys=True)), len(json.dumps(complete, sort_keys=True)) // 4)

    # Prove every Roulette mutation forwards the projection query into the shared response builder.
    def test_every_roulette_state_response_uses_the_shared_projection_boundary(self):
        # Read the exact tracked source rather than trusting runtime branch coverage alone.
        source = (ROOT / "casino" / "games" / "roulette" / "api.py").read_text(encoding="utf-8")
        # Collect executable response-builder calls while excluding the function declaration.
        call_lines = [line.strip() for line in source.splitlines() if "state_payload(" in line and not line.lstrip().startswith("def state_payload")]
        # Require all eight state-bearing endpoints to use the same projection boundary.
        self.assertEqual(len(call_lines), 8)
        # Reject any action that could accidentally retransmit the full static catalog.
        self.assertTrue(all("query=query" in line for line in call_lines))


# Run the focused suite when invoked directly during development.
if __name__ == "__main__":
    # Exit nonzero through unittest's standard fail-closed runner.
    unittest.main()
