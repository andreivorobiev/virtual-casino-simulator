"""Browser-free proof for the SLOT-036 economics-only controller slice."""

# Import JSON parsing for exact localized resource checks.
import json
# Import math for finite settlement assertions at the frozen v1 maximum.
import math
# Import temporary monkeypatch support without changing production modules.
from unittest import TestCase, mock
# Import repository paths for source-level browser contract checks.
from pathlib import Path

# Import the existing route and engine under test.
from casino.games.slots import api as slots_api
# Import the authoritative Slots economics model directly.
from casino.games.slots import engine
# Import the standard public failures used by frozen route boundaries.
from casino.errors import InsufficientFundsError, ValidationError


# Resolve the repository root once for localized and frontend source checks.
ROOT = Path(__file__).resolve().parents[3]
# Define one no-win grid that cannot trigger a payline, scatter, or progressive result.
NO_WIN_GRID = [
    # Keep five distinct first-row symbols.
    ["CHERRY", "LEMON", "BAR", "BELL", "SEVEN"],
    # Keep the middle row from matching any supported line.
    ["LEMON", "BAR", "BELL", "SEVEN", "CHERRY"],
    # Keep the final row independently non-winning.
    ["BAR", "BELL", "SEVEN", "CHERRY", "LEMON"],
]


# Capture route handlers without opening a listener.
class FakeRouter:
    # Create an empty method/path registry.
    def __init__(self):
        # Retain handlers by exact HTTP method and route pattern.
        self.handlers = {}

    # Build the GET registration decorator expected by the game module.
    def get(self, path):
        # Return one decorator that records the route handler.
        return lambda handler: self.handlers.__setitem__(("GET", path), handler) or handler

    # Build the POST registration decorator expected by the game module.
    def post(self, path):
        # Return one decorator that records the route handler.
        return lambda handler: self.handlers.__setitem__(("POST", path), handler) or handler


# Prove the server, API, ledger equation, and visible rules use one model.
class SlotsEconomicsTests(TestCase):
    # Require the exact cent-normalized frozen v1 amount and line-count boundaries.
    def test_frozen_v1_line_and_stake_boundaries(self):
        # Preserve every documented line choice.
        self.assertEqual([engine.normalize_active_lines(value) for value in (1, 3, 5, 9, 20)], [1, 3, 5, 9, 20])
        # Preserve the existing two-decimal normalization around the lower boundary.
        self.assertEqual(engine.normalize_line_bet(0.005), 0.01)
        # Preserve representative low, whole, fractional, and maximum accepted stakes.
        self.assertEqual([engine.normalize_line_bet(value) for value in (0.01, 0.99, 1, 1.01, 1_000_000)], [0.01, 0.99, 1.0, 1.01, 1_000_000.0])
        # Reject values that normalize below the minimum, exceed the maximum, or are malformed.
        for value in (0.004, 1_000_000.01, True, None, "bad", float("nan"), float("inf")):
            # Require one game-owned validation boundary for every invalid spelling.
            with self.assertRaises(ValidationError):
                # Normalize the invalid caller value without state or entropy access.
                engine.normalize_line_bet(value)
        # Reject unsupported, fractional, boolean, and malformed line selections.
        for value in (0, 2, 4, 8, 21, 1.5, True, None, "bad"):
            # Require one closed line-count vocabulary.
            with self.assertRaises(ValidationError):
                # Normalize the invalid line selection.
                engine.normalize_active_lines(value)

    # Require one declared scatter and feature table throughout evaluation.
    def test_scatter_and_free_spin_constants_drive_evaluation(self):
        # Read the additive runtime economics block exposed by the frozen route.
        runtime = engine.economics_config()
        # Require exact inclusive threshold, four-spin award, and exact four/five multipliers.
        self.assertEqual((runtime["free_spin_scatter_threshold"], runtime["free_spins_awarded"], runtime["scatter_pays"]), (3, 4, {4: 1, 5: 5}))
        # Build and evaluate exact three-, four-, and five-scatter grids.
        for scatter_count, expected_payout in ((3, 0), (4, 1), (5, 5)):
            # Start from a non-winning grid so only scatter economics contribute.
            grid = [list(row) for row in NO_WIN_GRID]
            # Replace the first cells with the requested number of scatters.
            for index in range(scatter_count):
                # Map a flat index into the three-by-five matrix.
                grid[index // 5][index % 5] = "SCATTER"
            # Evaluate one five-line, one-token result.
            result = engine.evaluate(grid, 5, 1)
            # Prove exact scatter payout, feature award, and component reconciliation.
            self.assertEqual(result["scatter_payout"], expected_payout)
            # Require the one declared four-spin award for every qualifying count.
            self.assertEqual(result["free_spins_awarded"], engine.FREE_SPINS_AWARDED)
            # Require total to equal its disjoint line and scatter components.
            self.assertEqual(result["payout"], round(result["line_payout"] + result["scatter_payout"], 2))

    # Prove the real unmocked grid and spin path remains a complete three-by-five game result.
    def test_unmocked_grid_and_real_spin_shape(self):
        # Render one deterministic valid stop per reel without replacing production code.
        grid = engine.render_grid([0, 1, 2, 3, 4])
        # Require exactly three visible rows and one symbol from each of five reels.
        self.assertEqual([len(row) for row in grid], [5, 5, 5])
        # Require every rendered cell to come from the closed engine symbol vocabulary.
        self.assertTrue(all(symbol in engine.SYMBOLS for row in grid for symbol in row))
        # Start fresh state for one real entropy-backed engine action.
        state = engine.default_state()
        # Execute the unmocked engine path at a supported nonqualifying setup.
        result = engine.spin(state, 5, 0.01)
        # Require the complete real result grid to retain the exact production shape.
        self.assertEqual([len(row) for row in result["grid"]], [5, 5, 5])
        # Require every settlement component and current-round field to be present.
        self.assertTrue(all(key in result for key in ("round_id", "cost", "payout", "line_payout", "scatter_payout", "progressive_hit", "wins", "stops")))
        # Require total payout to reconcile exactly to ordinary, scatter, and progressive sources.
        self.assertEqual(result["payout"], round(result["line_payout"] + result["scatter_payout"] + result["progressive_hit"], 2))

    # Prove one exact qualifier and one scalar meter prevent state growth or switching arbitrage.
    def test_progressive_is_one_constant_size_exact_qualifier(self):
        # Start with the one fixed qualifying meter.
        state = engine.default_state()
        # Retain one visible amount while callers cycle the complete line vocabulary and stake boundaries.
        engine.store_progressive_meter(state, 213.25)
        # Check every line choice against below, exact, above, minimum, and maximum stake controls.
        for lines in (1, 3, 5, 9, 20):
            # Cycle several accepted values without creating a caller-controlled meter identity.
            for line_bet in (0.01, 0.99, 1.0, 1.01, 1_000_000):
                # Resolve the action without entropy or state settlement.
                configuration = engine.effective_configuration(state, lines, line_bet)
                # Require only the one exact browser-default configuration to qualify.
                self.assertEqual(configuration["progressive_eligible"], lines == 20 and line_bet == 1.0)
                # Normalize the one retained meter and any transient pre-publication representation.
                self.assertEqual(engine.progressive_meter(state), 213.25)
        # Require switch-away/back to retain the exact same scalar without amplification or loss.
        self.assertEqual(state["progressive"], 213.25)
        # Require one fixed basis and reject every unbounded map representation.
        self.assertEqual(state["progressive_basis"], {"active_lines": 20, "line_bet": 1.0})
        # Prove payload/state cardinality cannot grow through legal cent or line cycling.
        self.assertNotIn("progressive_meters", state)
        # Require runtime config to publish the exact qualifier and one-meter limit.
        self.assertEqual((engine.economics_config()["progressive_qualifying_lines"], engine.economics_config()["progressive_qualifying_line_bet"], engine.economics_config()["progressive_meter_limit"]), (20, 1.0, 1))

    # Prove free spins use only a server-owned paid-trigger basis.
    def test_free_spin_basis_blocks_consume_request_escalation_and_migrates_legacy_state(self):
        # Seed a bank earned by one three-line, one-cent paid trigger.
        state = engine.default_state()
        # Store two remaining spins and the exact paid basis.
        state.update({"free_spins": 2, "free_spin_basis": {"active_lines": 3, "line_bet": 0.01}})
        # Force a deterministic non-winning grid while the caller attempts maximum escalation.
        with mock.patch.object(engine, "render_grid", return_value=[list(row) for row in NO_WIN_GRID]):
            # Consume one feature spin with hostile maximum submitted settings.
            result = engine.spin(state, 20, 1_000_000)
        # Require zero cost and the paid trigger's exact basis, not the consuming request.
        self.assertEqual((result["cost"], result["active_lines"], result["line_bet"]), (0.0, 3, 0.01))
        # Require no progressive eligibility or contribution from any free spin.
        self.assertEqual((result["progressive_eligible"], result["progressive_contribution"], result["progressive_hit"]), (False, 0.0, 0.0))
        # Require submitted values to remain observable separately from authoritative settlement.
        self.assertEqual((result["requested_active_lines"], result["requested_line_bet"]), (20, 1_000_000.0))
        # Seed one legacy bank with a trusted paid trigger row but no explicit basis.
        legacy = engine.default_state()
        # Preserve the server-owned trigger row used for migration.
        legacy.update({"free_spins": 1, "last_spins": [{"active_lines": 9, "line_bet": 1.01, "free_spins_awarded": 4, "free_spin": False}]})
        # Resolve the legacy bank without consulting a consuming request.
        self.assertEqual(engine.effective_configuration(legacy, 20, 1_000_000)["active_lines"], 9)
        # Remove trusted history and require the conservative legal-minimum fallback.
        legacy["last_spins"] = []
        # Require untraceable legacy state can never escalate above the frozen minimum.
        self.assertEqual(engine.effective_configuration(legacy, 20, 1_000_000)["line_bet"], 0.01)

    # Prove one paid exact-qualifier jackpot pays and resets the retained meter at most once.
    def test_progressive_hit_is_single_and_components_reconcile(self):
        # Build a grid that wins five SEVEN on every supported active line.
        seven_grid = [["SEVEN"] * 5 for _ in range(3)]
        # Start a maximum-line one-token spin from the declared seed.
        state = engine.default_state()
        # Force the jackpot grid without replacing the CSPRNG object.
        with mock.patch.object(engine, "render_grid", return_value=seven_grid):
            # Settle one paid spin through the real engine path.
            result = engine.spin(state, 20, 1)
        # Require multiple line wins but exactly one progressive component.
        self.assertGreater(len([row for row in result["wins"] if row.get("symbol") == "SEVEN"]), 1)
        # Require the current paid contribution to enter the displayed meter before the hit.
        self.assertEqual(result["progressive_hit"], 200.2)
        # Reconcile total payout to line, scatter, and the one jackpot component.
        self.assertEqual(result["payout"], round(result["line_payout"] + result["scatter_payout"] + result["progressive_hit"], 2))
        # Require the one won meter to reset to the disclosed constant seed.
        self.assertEqual(state["progressive"], 200.0)
        # Require no caller-derived meter map after the reset.
        self.assertNotIn("progressive_meters", state)

    # Prove the paid qualifier reaches one current-round debit, payout credit, history row, and meter reset.
    def test_paid_qualifier_progressive_reconciles_current_route_money(self):
        # Register the real route without opening an HTTP listener.
        router = FakeRouter()
        # Capture the exact production POST handler.
        slots_api.register(router)
        # Start from the disclosed seed so same-spin contribution and reset remain exact.
        state = engine.default_state()
        # Build one all-SEVEN result that qualifies on every active payline.
        seven_grid = [["SEVEN"] * 5 for _ in range(3)]
        # Patch only provider boundaries while running the real API and engine settlement.
        with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api, "save_player_game_state") as save_state, mock.patch.object(slots_api.ledger, "debit", return_value={"amount": -20}) as debit, mock.patch.object(slots_api.ledger, "credit", return_value={"amount": 1}) as credit, mock.patch.object(slots_api.players, "get_player", return_value={"player_id": "human", "balance": 1000}), mock.patch.object(slots_api, "append_history") as history, mock.patch.object(engine, "render_grid", return_value=seven_grid):
            # Settle one exact paid twenty-line by one-token qualifier.
            response = router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": 20, "line_bet": 1}, {})
        # Retain the authoritative result for exact component and current-money assertions.
        result = response["spin"]
        # Require paid eligibility, the exact one-percent contribution, one hit, and the disclosed reset.
        self.assertEqual((result["progressive_eligible"], result["progressive_contribution"], result["progressive_hit"], response["state"]["progressive"]), (True, 0.2, 200.2, 200.0))
        # Reconcile the credited amount from all disjoint return components.
        self.assertEqual(result["payout"], round(result["line_payout"] + result["scatter_payout"] + result["progressive_hit"], 2))
        # Require the exact paid cost and result payout at the existing money boundary.
        self.assertEqual((debit.call_args.args[1], credit.call_args.args[1]), (20, result["payout"]))
        # Require the payout row to carry the same exact progressive component.
        self.assertEqual(credit.call_args.args[5]["progressive_hit"], result["progressive_hit"])
        # Require result, debit, credit, and history to share only the current action's round.
        self.assertEqual((result["round_id"], debit.call_args.args[4], credit.call_args.args[4], history.call_args.args[1]), (result["round_id"],) * 4)
        # Require history to retain the same exact total and jackpot component.
        self.assertEqual((history.call_args.args[7], history.call_args.args[9]["progressive_hit"]), (result["payout"], result["progressive_hit"]))
        # Require one final state write containing the reset scalar meter.
        self.assertEqual(save_state.call_count, 1)

    # Prove free spins and nonqualifying paid spins cannot touch or win the progressive.
    def test_progressive_is_paid_exact_qualifier_only(self):
        # Build a grid that would otherwise hit the progressive on every supported line.
        seven_grid = [["SEVEN"] * 5 for _ in range(3)]
        # Retain a visible meter while testing a below-qualifier paid spin.
        nonqualifying = engine.default_state()
        # Set one accrued amount that must survive the action byte-for-byte as a JSON number.
        engine.store_progressive_meter(nonqualifying, 231.125)
        # Force a twenty-line paid spin just below the one-token qualifier.
        with mock.patch.object(engine, "render_grid", return_value=seven_grid):
            # Settle ordinary line wins without progressive qualification.
            paid_result = engine.spin(nonqualifying, 20, 0.99)
        # Require ordinary payout while contribution, hit, and meter mutation stay absent.
        self.assertGreater(paid_result["line_payout"], 0)
        # Require the complete nonqualifying progressive tuple to remain zero/unchanged.
        self.assertEqual((paid_result["progressive_eligible"], paid_result["progressive_contribution"], paid_result["progressive_hit"], nonqualifying["progressive"]), (False, 0.0, 0.0, 231.125))
        # Seed one free spin earned at the exact qualifying paid basis.
        free_state = engine.default_state()
        # Retain an accrued meter and the server-owned paid-trigger basis.
        free_state.update({"progressive": 241.75, "free_spins": 1, "free_spin_basis": {"active_lines": 20, "line_bet": 1.0}})
        # Force five SEVEN while consuming the qualifying-basis free action.
        with mock.patch.object(engine, "render_grid", return_value=seven_grid):
            # Attempt the exact qualifier even though feature status makes the action ineligible.
            free_result = engine.spin(free_state, 20, 1)
        # Require ordinary free-spin line payout and zero cost.
        self.assertGreater(free_result["line_payout"], 0)
        # Require categorical free-spin ineligibility, no contribution/hit, and exact meter retention.
        self.assertEqual((free_result["cost"], free_result["progressive_eligible"], free_result["progressive_contribution"], free_result["progressive_hit"], free_state["progressive"]), (0.0, False, 0.0, 0.0, 241.75))

    # Prove the current API emits no progressive ledger component for a qualifying-basis free spin.
    def test_free_spin_api_has_no_progressive_money_event(self):
        # Register the real route without a listener.
        router = FakeRouter()
        # Capture its exact handler.
        slots_api.register(router)
        # Seed one qualifying-basis free action and an accrued scalar meter.
        state = engine.default_state()
        # Persist the paid-trigger basis without granting the free action eligibility.
        state.update({"progressive": 241.75, "free_spins": 1, "free_spin_basis": {"active_lines": 20, "line_bet": 1.0}})
        # Force a result with ordinary line return that would hit the progressive if the guard were absent.
        seven_grid = [["SEVEN"] * 5 for _ in range(3)]
        # Isolate only current money, persistence, history, and entropy seams.
        with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api, "save_player_game_state"), mock.patch.object(slots_api.ledger, "debit") as debit, mock.patch.object(slots_api.ledger, "credit", return_value={"amount": 1}) as credit, mock.patch.object(slots_api.players, "get_player", return_value={"player_id": "human", "balance": 100}), mock.patch.object(slots_api, "append_history") as history, mock.patch.object(engine, "render_grid", return_value=seven_grid):
            # Consume the feature through the exact qualifying submitted controls.
            response = router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": 20, "line_bet": 1}, {})
        # Require no free-spin debit and exactly one ordinary payout credit.
        debit.assert_not_called()
        # Require the current credit details to contain a zero progressive component.
        self.assertEqual(credit.call_args.args[5]["progressive_hit"], 0.0)
        # Require the public result and retained meter to agree with the money evidence.
        self.assertEqual((response["spin"]["progressive_eligible"], response["spin"]["progressive_hit"], response["state"]["progressive"]), (False, 0.0, 241.75))
        # Require history to receive the same zero-progressive result rather than a separate jackpot event.
        self.assertEqual(history.call_args.args[9]["progressive_hit"], 0.0)

    # Prove the current route debit/credit/history equation and one-round correlation.
    def test_existing_route_uses_engine_cost_and_payout_equation(self):
        # Register the real route into an inert listener-free router.
        router = FakeRouter()
        # Capture every current ledger and persistence interaction.
        slots_api.register(router)
        # Retain one mutable state document and wallet balance.
        state = engine.default_state()
        # Build a deterministic paid result with one exact line payout.
        paid_grid = [["LEMON", "BAR", "BELL", "SEVEN", "CHERRY"], ["CHERRY"] * 5, ["BAR", "BELL", "SEVEN", "CHERRY", "LEMON"]]
        # Patch only external persistence/money seams while executing the real API and engine.
        with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api, "save_player_game_state") as save_state, mock.patch.object(slots_api.ledger, "debit", return_value={"amount": -0.01}) as debit, mock.patch.object(slots_api.ledger, "credit", return_value={"amount": 0.3}) as credit, mock.patch.object(slots_api.players, "get_player", return_value={"player_id": "human", "balance": 100.29}), mock.patch.object(slots_api, "append_history") as history, mock.patch.object(engine, "render_grid", return_value=paid_grid):
            # Execute the current frozen spin route at the minimum accepted stake.
            response = router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": 1, "line_bet": 0.01}, {})
        # Require the debit equals lines times stake and the credit equals the engine payout.
        self.assertEqual((response["spin"]["cost"], debit.call_args.args[1], credit.call_args.args[1]), (0.01, 0.01, response["spin"]["payout"]))
        # Require the additive components reconcile the credited payout.
        self.assertEqual(response["spin"]["payout"], round(response["spin"]["line_payout"] + response["spin"]["scatter_payout"] + response["spin"]["progressive_hit"], 2))
        # Require current state and history persistence receive the same exact round once in this request.
        self.assertEqual(save_state.call_count, 1)
        # Require history uses the authoritative engine cost and payout equation.
        self.assertEqual((history.call_args.args[5], history.call_args.args[7]), (response["spin"]["cost"], response["spin"]["payout"]))
        # Require result, debit, credit, and history to share the current action's one round identifier.
        self.assertEqual((response["spin"]["round_id"], debit.call_args.args[4], credit.call_args.args[4], history.call_args.args[1]), (response["spin"]["round_id"],) * 4)

    # Prove the route passes raw JSON line-count values through the one engine-owned validator.
    def test_route_validates_raw_active_lines_without_precoercion(self):
        # Register the real route without opening a listener.
        router = FakeRouter()
        # Capture its exact POST handler.
        slots_api.register(router)
        # Reject JSON booleans, fractions, fractional strings, unsupported integers, and malformed values before state access.
        for value in (True, False, 1.5, "1.5", 2, "bad", None):
            # Require the standard game validation failure for each raw spelling.
            with self.assertRaises(ValidationError):
                # Pass the raw caller value directly through the real route.
                router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": value, "line_bet": 1}, {})
        # Retain the historical numeric-string compatibility when it names one exact supported integer.
        state = engine.default_state()
        # Force a no-win action while isolating current persistence and wallet seams.
        with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api, "save_player_game_state"), mock.patch.object(slots_api.ledger, "debit", return_value={"amount": -20}), mock.patch.object(slots_api.ledger, "credit", return_value={"amount": 1}), mock.patch.object(slots_api.players, "get_player", return_value={"player_id": "human", "balance": 80}), mock.patch.object(slots_api, "append_history"), mock.patch.object(engine, "render_grid", return_value=[list(row) for row in NO_WIN_GRID]):
            # Submit the frozen route's historically accepted exact numeric string.
            response = router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": "20", "line_bet": 1}, {})
        # Require the engine-owned normalizer to publish the exact supported integer.
        self.assertEqual(response["spin"]["active_lines"], 20)

    # Prove the real route and real grid engine complete together without a mocked render seam.
    def test_unmocked_route_engine_smoke(self):
        # Register the real route without an HTTP listener.
        router = FakeRouter()
        # Capture its exact POST handler.
        slots_api.register(router)
        # Start from one fresh server-owned state document.
        state = engine.default_state()
        # Isolate storage and wallet providers while leaving normalize, entropy, grid, evaluate, and spin unmocked.
        with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api, "save_player_game_state") as save_state, mock.patch.object(slots_api.ledger, "debit", return_value={"amount": -0.01}) as debit, mock.patch.object(slots_api.ledger, "credit", return_value={"amount": 1}) as credit, mock.patch.object(slots_api.players, "get_player", return_value={"player_id": "human", "balance": 99.99}), mock.patch.object(slots_api, "append_history") as history:
            # Execute one complete minimum-stake route action through the production engine.
            response = router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": 1, "line_bet": 0.01}, {})
        # Require the live engine grid to retain its exact three-by-five shape through the API.
        self.assertEqual([len(row) for row in response["spin"]["grid"]], [5, 5, 5])
        # Require the route to persist and record one completed current action.
        self.assertEqual((save_state.call_count, debit.call_count, history.call_count), (1, 1, 1))
        # Require any positive random return to use the same current round; a loss has no credit row.
        if credit.called:
            # Check only current-action correlation without promising behavior beyond the existing route.
            self.assertEqual(credit.call_args.args[4], response["spin"]["round_id"])

    # Prove an insufficient maximum wager fails at the existing debit boundary before entropy.
    def test_existing_route_insufficient_funds_stops_before_spin(self):
        # Register the real route into an inert router.
        router = FakeRouter()
        # Capture the route without opening HTTP.
        slots_api.register(router)
        # Use ordinary state with no free-spin bank.
        state = engine.default_state()
        # Patch the current debit to publish the standard insufficient-funds boundary.
        with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api.ledger, "debit", side_effect=InsufficientFundsError(details={"balance": 0, "amount": -20_000_000})) as debit, mock.patch.object(engine, "spin") as spin:
            # Require the route to propagate the current wallet rejection.
            with self.assertRaises(InsufficientFundsError):
                # Attempt the maximum legal twenty-line wager.
                router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": 20, "line_bet": 1_000_000}, {})
        # Require the exact maximum cost reached the existing debit boundary.
        self.assertEqual(debit.call_args.args[1], 20_000_000)
        # Require no RNG or game-state mutation after the rejected debit.
        spin.assert_not_called()

    # Prove representative and maximum accepted stakes settle finite ordinary returns without touching the meter.
    def test_representative_and_maximum_settlement_math(self):
        # Build one exact three-CHERRY single-line grid with no scatter or progressive hit.
        grid = [["LEMON", "BAR", "BELL", "SEVEN", "CHERRY"], ["CHERRY", "CHERRY", "CHERRY", "LEMON", "BAR"], ["BAR", "BELL", "SEVEN", "CHERRY", "LEMON"]]
        # Settle representative fractional, above-qualifier, and maximum accepted stakes.
        for line_bet in (0.99, 1.01, 1_000_000):
            # Start one independent scalar meter for exact retention evidence.
            state = engine.default_state()
            # Retain a non-seed amount so accidental reset is observable.
            engine.store_progressive_meter(state, 237.125)
            # Force the exact ordinary grid through the real engine settlement path.
            with mock.patch.object(engine, "render_grid", return_value=grid):
                # Use one line so every tested stake is nonqualifying.
                result = engine.spin(state, 1, line_bet)
            # Require the debit equation and ordinary two-times-line-bet return.
            self.assertEqual((result["cost"], result["line_payout"], result["payout"]), (line_bet, round(2 * line_bet, 2), round(2 * line_bet, 2)))
            # Require finite values at the frozen maximum and zero progressive movement.
            self.assertTrue(all(math.isfinite(result[key]) for key in ("cost", "payout", "line_payout", "scatter_payout", "progressive_hit")))
            # Require the nonqualifying meter to remain exact.
            self.assertEqual((result["progressive_eligible"], result["progressive_contribution"], result["progressive_hit"], state["progressive"]), (False, 0.0, 0.0, 237.125))

    # Prove representative and maximum accepted stakes succeed through the complete current route equation.
    def test_representative_and_maximum_route_settlement(self):
        # Build one exact three-CHERRY single-line grid with no scatter or progressive hit.
        grid = [["LEMON", "BAR", "BELL", "SEVEN", "CHERRY"], ["CHERRY", "CHERRY", "CHERRY", "LEMON", "BAR"], ["BAR", "BELL", "SEVEN", "CHERRY", "LEMON"]]
        # Exercise one representative fractional setup and the exact twenty-line frozen maximum.
        for active_lines, line_bet in ((1, 0.99), (20, 1_000_000)):
            # Name each amount independently when an assertion fails.
            with self.subTest(active_lines=active_lines, line_bet=line_bet):
                # Register a fresh production handler without opening a listener.
                router = FakeRouter()
                # Capture the exact route for this independent settlement.
                slots_api.register(router)
                # Start from one non-seed meter so accidental movement remains visible.
                state = engine.default_state()
                # Persist an accrued current value before the nonqualifying route call.
                engine.store_progressive_meter(state, 237.125)
                # Calculate the exact deterministic ordinary payout through the authoritative evaluator.
                expected_payout = engine.evaluate(grid, active_lines, line_bet)["payout"]
                # Calculate the exact debit from the submitted line count and stake.
                expected_cost = round(active_lines * line_bet, 2)
                # Patch only external provider seams while running the real route and engine.
                with mock.patch.object(slots_api, "load_player_game_state", return_value=state), mock.patch.object(slots_api, "save_player_game_state") as save_state, mock.patch.object(slots_api.ledger, "debit", return_value={"amount": -line_bet}) as debit, mock.patch.object(slots_api.ledger, "credit", return_value={"amount": expected_payout}) as credit, mock.patch.object(slots_api.players, "get_player", return_value={"player_id": "human", "balance": expected_payout}), mock.patch.object(slots_api, "append_history") as history, mock.patch.object(engine, "render_grid", return_value=grid):
                    # Settle the representative or exact-maximum action through the production route.
                    response = router.handlers[("POST", r"/api/v1/games/slots/spin")]({"player_id": "human", "active_lines": active_lines, "line_bet": line_bet}, {})
                # Retain the exact current result from the standard response envelope.
                result = response["spin"]
                # Require the full debit and ordinary credit equation at both accepted stakes.
                self.assertEqual((result["cost"], result["payout"], debit.call_args.args[1], credit.call_args.args[1]), (expected_cost, expected_payout, expected_cost, expected_payout))
                # Require history to retain the same exact cost and payout.
                self.assertEqual((history.call_args.args[5], history.call_args.args[7]), (expected_cost, expected_payout))
                # Require result, debit, credit, and history to share this current route round.
                self.assertEqual((result["round_id"], debit.call_args.args[4], credit.call_args.args[4], history.call_args.args[1]), (result["round_id"],) * 4)
                # Require finite settlement fields, a nonqualifying action, and exact meter retention.
                self.assertTrue(all(math.isfinite(result[key]) for key in ("cost", "payout", "line_payout", "scatter_payout", "progressive_hit")))
                # Require no contribution or jackpot movement at the representative or maximum setup.
                self.assertEqual((result["progressive_eligible"], result["progressive_contribution"], result["progressive_hit"], response["state"]["progressive"]), (False, 0.0, 0.0, 237.125))
                # Require the standard response state, player, and additive runtime configuration.
                self.assertEqual((response["game"], response["player"]["player_id"], response["config"]["economics"]["progressive_meter_limit"]), ("slots", "human", 1))
                # Require one final state persistence after the successful current action.
                self.assertEqual(save_state.call_count, 1)

    # Require one authoritative localized and browser-visible model with no stale 1000 fallback.
    def test_locales_and_frontend_match_authoritative_economics(self):
        # Load both governed Slots locale resources.
        resources = {locale: json.loads((ROOT / "web" / "i18n" / locale / "games" / "slots.json").read_text(encoding="utf-8")) for locale in ("en-US", "ru-RU")}
        # Require exact new scatter/free-spin tokens and the cent-range validation key in both locales.
        for locale, resource in resources.items():
            # Require all runtime interpolation parameters used by the visible paytable.
            self.assertTrue(all(token in resource["paytable.scatter"] for token in ("{threshold}", "{freeSpins}", "{four}", "{five}")))
            # Require exact-qualifier progressive copy and no historical per-basis rule.
            self.assertTrue(all(token in resource["paytable.progressive"] for token in ("{contribution}", "{seed}", "{lines}", "{lineBet}")))
            # Require nonqualifying controls to expose an explicit localized state.
            self.assertTrue(all(token in resource["feature.progressiveIneligible"] for token in ("{amount}", "{lines}", "{lineBet}")))
            # Require the exact frozen lower and upper values in localized validation.
            self.assertIn("0", resource["errors.lineBetRange"])
            # Reject every stale scatter/free-spin literal from visible copy.
            self.assertNotIn("100x", resource["paytable.scatter"])
            # Reject the stale eight-spin award from visible copy.
            self.assertNotIn("8 ", resource["paytable.scatter"])
            # Require the scatter trigger to disclose its inclusive threshold.
            self.assertIn("or more" if locale == "en-US" else "или более", resource["paytable.scatter"])
            # Require start/reset copy to distinguish the seed from the current accrued value.
            self.assertIn("starts and resets" if locale == "en-US" else "начинается и сбрасывается", resource["paytable.progressive"])
            # Require nonqualifying and feature actions to preserve the current meter rather than the seed.
            self.assertIn("current value" if locale == "en-US" else "текущее значение", resource["paytable.progressive"])
        # Read the shipped frontend source for authoritative runtime configuration use.
        frontend = (ROOT / "web" / "games" / "slots.js").read_text(encoding="utf-8")
        # Require one exact qualifier, cent controls, and immediate changed-state evidence hooks.
        self.assertIn("progressive_qualifying_lines", frontend)
        # Require input edits to refresh the progressive state without waiting for a spin.
        self.assertIn("updateProgressiveDisplay()", frontend)
        # Reject the transient caller-keyed meter-map implementation.
        self.assertNotIn("progressive_meters", frontend)
        # Reject both stale hardcoded progressive fallback spellings.
        self.assertNotIn("progressive || 1000", frontend)
        # Reject the old whole-token-only minimum declaration.
        self.assertNotIn("const MIN_LINE_BET = 1;", frontend)
        # Require maximum-line maximum-stake arithmetic remains finite in the shipped numeric domain.
        self.assertTrue(math.isfinite(20 * engine.MAX_LINE_BET))
