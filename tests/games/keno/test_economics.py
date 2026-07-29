"""Browser-free proof for the KENO-027 paytable and settlement correction."""

# Import deep-copy support so interrupted draw state can be restored without aliasing.
import copy
# Import exact rational arithmetic for hypergeometric probability and ideal-return proof.
from fractions import Fraction
# Import JSON parsing for persisted current-ledger and localized resource assertions.
import json
# Import finite-number and IEEE-754 ulp helpers for the production rounding bound.
import math
# Import platform float constants for a conservative production-product error allowance.
import sys
# Import combination counts for the exact Keno outcome distribution.
from math import comb
# Import temporary provider roots so route settlement tests never touch checked-in data.
from pathlib import Path
# Import disposable-directory ownership for automatic test cleanup.
import tempfile
# Import the standard unittest assertions and patching seam.
from unittest import TestCase, mock

# Import production history so route outcomes are verified at their durable boundary.
from casino.core import history, ledger, players, storage
# Import the production Keno API route module under test.
from casino.games.keno import api as keno_api
# Import the single server-authoritative Keno economics model.
from casino.games.keno import engine


# Resolve the repository root once for contract, locale, visual, and source assertions.
ROOT = Path(__file__).resolve().parents[3]
# Store the exact number of equally likely twenty-ball draws.
DRAW_COMBINATIONS = comb(80, 20)
# Preserve the frozen v1 minimum and maximum ticket amounts.
MIN_AMOUNT = Fraction(1, 100)
MAX_AMOUNT = Fraction(1_000_000, 1)
# Enumerate every low-cent amount below one token before applying the analytic bound.
LOW_CENT_AMOUNTS = tuple(Fraction(cents, 100) for cents in range(1, 100))


# Return the exact hypergeometric probability for one picks/catches outcome class.
def exact_probability(picks, catches):
    # Count draws containing exactly the requested selected-number catches.
    matching_draws = comb(picks, catches) * comb(80 - picks, 20 - catches)
    # Return the exact probability without float approximation.
    return Fraction(matching_draws, DRAW_COMBINATIONS)


# Return one multiplier as the exact decimal rational declared in source.
def exact_multiplier(multiplier):
    # Convert through string form so finite decimal literals retain their authored value.
    return Fraction(str(multiplier))


# Return the exact ideal unit-stake RTP for one server paytable row.
def exact_ideal_rtp(picks):
    # Sum every paying catch class using exact probability and multiplier rationals.
    return sum(exact_probability(picks, catches) * exact_multiplier(multiplier) for catches, multiplier in engine.PAYTABLE[picks].items())


# Return realized RTP under the unchanged production float multiplication and Python round law.
def production_realized_rtp(picks, amount):
    # Convert the accepted cent amount to the same float consumed by production.
    production_amount = float(amount)
    # Accumulate exact hypergeometric weights against the actual production-rounded payout.
    realized_return = sum(
        # Convert the observable two-decimal payout back to an exact decimal rational for proof.
        exact_probability(picks, catches) * Fraction(str(round(production_amount * multiplier, 2)))
        # Visit every paying outcome in the authoritative row.
        for catches, multiplier in engine.PAYTABLE[picks].items()
    )
    # Divide by the exact accepted stake so the reported realized RTP remains a rational.
    return realized_return / amount


# Convert one positive float error budget to an exact rational strictly above that float.
def upward_float_fraction(value):
    # Move one representable float toward positive infinity to make conversion one-sided.
    upward = math.nextafter(float(value), math.inf)
    # Preserve that upward float exactly as a rational for later exact accumulation.
    return Fraction.from_float(upward)


# Return a conservative realized-RTP upper bound for every accepted amount at least one token.
def large_amount_rtp_upper_bound(picks):
    # Resolve the largest product scale reachable by this row and the frozen maximum stake.
    maximum_product = float(MAX_AMOUNT) * max(engine.PAYTABLE[picks].values())
    # Bound cent rounding, one product ulp, and four epsilon-scaled product errors conservatively.
    per_paid_outcome_error = upward_float_fraction(
        0.005 + math.ulp(maximum_product) + 4 * sys.float_info.epsilon * maximum_product
    )
    # Sum the exact probability of every paying outcome without a float conversion.
    paid_probability = sum(exact_probability(picks, catches) for catches in engine.PAYTABLE[picks])
    # Inflate the exact ideal return by a one-sided epsilon allowance for the runtime ratio.
    ratio_error = upward_float_fraction(4 * sys.float_info.epsilon * float(exact_ideal_rtp(picks)))
    # Divide by the smallest amount in this analytic range, one token, using exact rationals.
    return exact_ideal_rtp(picks) + paid_probability * per_paid_outcome_error + ratio_error


# Script one exact twenty-ball sample while preserving the engine's sample interface.
class ScriptedBalls:
    # Store the exact draw returned to the production engine.
    def __init__(self, drawn):
        # Copy the draw so engine sorting cannot mutate the test input.
        self.drawn = list(drawn)

    # Return the exact draw instead of consuming operating-system entropy.
    def sample(self, population, count):
        # Verify the engine still requests twenty unique values from the 1-80 population.
        if list(population) != list(range(1, 81)) or count != 20:
            # Fail loudly if the production draw contract changes.
            raise AssertionError("unexpected Keno sample contract")
        # Return a fresh copy for the current engine action.
        return list(self.drawn)


# Raise from the RNG seam so restoration is proven on failure as well as success.
class FailingBalls:
    # Raise the injected failure at the same boundary used by production entropy.
    def sample(self, population, count):
        # Surface a fixed diagnostic without consuming any random state.
        raise RuntimeError("injected Keno draw failure")


# Capture Keno route handlers without opening an HTTP listener.
class RecordingRouter:
    # Initialize one empty method/path handler registry.
    def __init__(self):
        # Store production handlers keyed by exact method and frozen route.
        self.handlers = {}

    # Build one route decorator for the requested method and path.
    def _register(self, method, path):
        # Record the decorated handler without altering it.
        return lambda handler: self.handlers.__setitem__((method, path), handler) or handler

    # Record GET handlers through the router-compatible interface.
    def get(self, path):
        # Return the GET registration decorator.
        return self._register("GET", path)

    # Record POST handlers through the router-compatible interface.
    def post(self, path):
        # Return the POST registration decorator.
        return self._register("POST", path)

    # Record DELETE handlers through the router-compatible interface.
    def delete(self, path):
        # Return the DELETE registration decorator.
        return self._register("DELETE", path)


# Prove one authoritative paytable is house-side through engine, API, ledger, UI, and evidence policy.
class KenoEconomicsTests(TestCase):
    # Prepare disposable provider and game-state seams before each route test.
    def setUp(self):
        # Own one temporary root for every provider instance used by this test.
        self.temporary_root = tempfile.TemporaryDirectory(prefix="keno_economics_")
        # Reset the provider counter used to isolate sub-scenarios.
        self.provider_index = 0
        # Start from a fresh Keno state document.
        self.state = engine.default_state()
        # Patch production state loading to return the test-owned current state.
        self.load_patch = mock.patch.object(keno_api, "load_player_game_state", side_effect=lambda *_args: self.state)
        # Patch production state saves while retaining mutation of the same in-memory object.
        self.save_patch = mock.patch.object(keno_api, "save_player_game_state")
        # Activate the state seams before route registration.
        self.load_patch.start()
        # Activate the save observer for exact call-count assertions.
        self.saved_state = self.save_patch.start()
        # Register cleanup before any assertion can interrupt the test.
        self.addCleanup(self.load_patch.stop)
        # Register save-patch cleanup before any assertion can interrupt the test.
        self.addCleanup(self.save_patch.stop)
        # Register provider cleanup so later suites return to normal provider selection.
        self.addCleanup(storage.set_provider_for_tests, None)
        # Register temporary-directory cleanup after provider use ends.
        self.addCleanup(self.temporary_root.cleanup)
        # Capture the exact production route set once.
        router = RecordingRouter()
        # Register every Keno v1 handler through the real module.
        keno_api.register(router)
        # Store handlers for listener-free route calls.
        self.handlers = router.handlers
        # Seed the first isolated runtime.
        self.reset_runtime()

    # Reset wallet, ledger, history, and Keno state for one independent route scenario.
    def reset_runtime(self, balance=20_000_000_000_000.0):
        # Allocate a distinct provider root so prior scenario rows cannot leak.
        self.provider_index += 1
        # Resolve the next isolated JSON provider directory.
        provider_root = Path(self.temporary_root.name) / f"provider-{self.provider_index}"
        # Build the production JSON provider against the disposable directory.
        provider = storage.JsonStorageProvider(provider_root)
        # Inject the provider for ledger, player, and history operations.
        storage.set_provider_for_tests(provider)
        # Ensure every provider-owned path exists before seeding.
        provider.ensure_ready()
        # Build the compatible player document.
        player_document = players.default_players()
        # Fund only the human player enough for exact maximum-stake jackpot tests.
        next(player for player in player_document["players"] if player["player_id"] == "human")["balance"] = balance
        # Persist the funded players through the production provider boundary.
        players.save_players(player_document)
        # Reset current game state to the compatible empty shape.
        self.state = engine.default_state()
        # Reset save-call accounting for the next route scenario.
        self.saved_state.reset_mock()

    # Build one deterministic draw with exactly catches selected numbers.
    def drawn_for(self, picks, catches):
        # Select the first legal numbers for a deterministic ticket.
        selected = list(range(1, picks + 1))
        # Keep exactly the requested selected prefix in the draw.
        caught = selected[:catches]
        # Fill remaining draw positions from numbers outside every possible selected set.
        misses = list(range(21, 81))[: 20 - catches]
        # Return a valid unique twenty-ball draw.
        return selected, caught + misses

    # Purchase and settle one deterministic ticket through the existing public handlers.
    def settle_route(self, picks, catches, amount, round_id=None):
        # Build exact selected and drawn number sets.
        selected, drawn = self.drawn_for(picks, catches)
        # Snapshot the wallet before the ticket debit.
        starting_balance = players.get_player("human")["balance"]
        # Purchase through the frozen v1 route.
        purchase = self.handlers[("POST", r"/api/v1/games/keno/tickets")]({"spots": selected, "amount": amount}, {})
        # Read the one durable ticket created by the route.
        ticket = purchase["ticket"]
        # Build the production RNG patch for this exact outcome.
        rng_patch = mock.patch.object(engine, "_SYSTEM_RANDOM", ScriptedBalls(drawn))
        # Optionally pin the current draw identity for exact replay proof.
        id_patch = mock.patch.object(engine, "new_id", return_value=round_id) if round_id else mock.patch.object(engine, "new_id", wraps=engine.new_id)
        # Execute one real engine/API/ledger/history settlement.
        with rng_patch, id_patch:
            # Call the frozen draw route.
            response = self.handlers[("POST", r"/api/v1/games/keno/draw")]({}, {})
        # Return all scenario objects needed by exact assertions.
        return starting_balance, purchase, ticket, response

    # Require exact probability coverage, monotonic rows, and increasing jackpots.
    def test_exact_probability_space_paytable_shape_and_ideal_rtp(self):
        # Track all valid picks/catches classes across the Keno domain.
        outcome_classes = 0
        # Track each row jackpot so top awards can be compared across spot counts.
        jackpots = []
        # Visit every legal picks count.
        for picks in range(1, 21):
            # Build the complete exact probability row including losing classes.
            probabilities = [exact_probability(picks, catches) for catches in range(picks + 1)]
            # Count every valid outcome class.
            outcome_classes += len(probabilities)
            # Require the exact hypergeometric row to exhaust the sample space.
            self.assertEqual(sum(probabilities), Fraction(1, 1))
            # Read the server-authoritative paying row.
            row = engine.PAYTABLE[picks]
            # Require each listed catch count to be valid for the row.
            self.assertTrue(all(0 <= catches <= picks for catches in row))
            # Require every positive award to be finite and at least stake-neutral.
            self.assertTrue(all(math.isfinite(float(multiplier)) and multiplier >= 1 for multiplier in row.values()))
            # Require strictly increasing catch counts and multipliers.
            self.assertEqual(list(row), sorted(row))
            # Require every successive listed award to exceed the previous award.
            self.assertTrue(all(current < following for current, following in zip(row.values(), list(row.values())[1:])))
            # Require the row's final award to be its full-catch jackpot.
            self.assertEqual(next(reversed(row)), picks)
            # Store the row jackpot for cross-row shape proof.
            jackpots.append(row[picks])
            # Calculate the exact ideal return.
            ideal = exact_ideal_rtp(picks)
            # Apply the explicit pick-one rounding exception band.
            if picks == 1:
                # Require the owner-approved 3.49x cap and its exact 87.25% ideal return.
                self.assertEqual((row[1], ideal), (3.49, Fraction(349, 400)))
            # Apply the normal near-ninety-percent ideal band to picks two through twenty.
            else:
                # Require every other exact ideal return to remain between eighty-eight and ninety-four percent.
                self.assertTrue(Fraction(88, 100) < ideal < Fraction(94, 100), (picks, float(ideal)))
        # Require exactly 230 outcome classes across one through twenty picks.
        self.assertEqual(outcome_classes, 230)
        # Require every larger spot-count jackpot to exceed the preceding row jackpot.
        self.assertTrue(all(current < following for current, following in zip(jackpots, jackpots[1:])))

    # Prove every frozen-v1 accepted amount remains house-side after production cent rounding.
    def test_realized_rtp_is_house_side_across_full_amount_domain(self):
        # Visit each server paytable row independently.
        for picks in range(1, 21):
            # Enumerate every low legal cent amount below one token under the real float-plus-round expression.
            low_results = [production_realized_rtp(picks, amount) for amount in LOW_CENT_AMOUNTS]
            # Require every enumerated low-cent realization to stay strictly house-side.
            self.assertLess(max(low_results), 1.0, (picks, max(low_results)))
            # Cross-check the exact frozen-v1 maximum accepted amount under the production expression.
            self.assertLess(production_realized_rtp(picks, MAX_AMOUNT), 1.0, picks)
            # Prove every amount at least one token with cent rounding and conservative IEEE-754 product error.
            self.assertLess(large_amount_rtp_upper_bound(picks), 1.0, (picks, large_amount_rtp_upper_bound(picks)))
        # Pin the one-cent pick-one behavior that forced the owner-approved exception.
        self.assertEqual(production_realized_rtp(1, MIN_AMOUNT), 0.75)
        # Pin the observed global low-cent maximum and its responsible nine-spot row below one.
        self.assertLess(max(production_realized_rtp(picks, amount) for picks in range(1, 21) for amount in LOW_CENT_AMOUNTS), 1.0)

    # Cross-check all 230 exact classes through real engine draw and prove RNG restoration.
    def test_every_outcome_class_matches_real_engine_and_rng_restores(self):
        # Capture the original operating-system RNG object identity.
        original_rng = engine._SYSTEM_RANDOM
        # Track every executed class.
        executed = 0
        # Visit every legal spot count.
        for picks in range(1, 21):
            # Visit every possible catch count including zero.
            for catches in range(picks + 1):
                # Build deterministic selected and drawn number sets.
                selected, drawn = self.drawn_for(picks, catches)
                # Start one fresh compatible state.
                state = engine.default_state()
                # Add one real ticket using a low-cent amount that exercises production rounding.
                ticket = engine.add_ticket(state, "human", selected, 0.03, source="economics-proof")
                # Patch only the production RNG object for this exact class.
                with mock.patch.object(engine, "_SYSTEM_RANDOM", ScriptedBalls(drawn)):
                    # Execute the real engine draw.
                    result = engine.draw(state)["results"][0]
                # Require the production RNG identity to be restored after every class.
                self.assertIs(engine._SYSTEM_RANDOM, original_rng)
                # Require exact catches and count from the deterministic draw.
                self.assertEqual((result["catches"], result["catch_count"]), (selected[:catches], catches))
                # Require the exact server paytable multiplier or zero for a losing class.
                expected_multiplier = engine.PAYTABLE[picks].get(catches, 0)
                # Require the real result to expose the same multiplier.
                self.assertEqual(result["multiplier"], expected_multiplier)
                # Require the existing float-plus-round production payout law exactly.
                self.assertEqual(result["payout"], round(float(ticket["amount"]) * expected_multiplier, 2))
                # Count the completed class.
                executed += 1
        # Require complete class coverage rather than a sampled subset.
        self.assertEqual(executed, 230)
        # Inject an entropy failure through the same patch context.
        with self.assertRaises(RuntimeError):
            # Patch the RNG only for the failing action.
            with mock.patch.object(engine, "_SYSTEM_RANDOM", FailingBalls()):
                # Execute a draw that reaches the injected sample failure.
                engine.draw({"open_tickets": [{"ticket_id": "failure", "player_id": "human", "spots": [1], "amount": 1}], "last_draws": []})
        # Require the production RNG identity after the failing context exits.
        self.assertIs(engine._SYSTEM_RANDOM, original_rng)

    # Require frozen routes and API paytable identity without a response-shape break.
    def test_frozen_v1_routes_and_api_paytable_identity(self):
        # Require the exact four existing route/method pairs and no replacement version.
        self.assertEqual(
            set(self.handlers),
            {
                ("GET", r"/api/v1/games/keno/state"),
                ("POST", r"/api/v1/games/keno/tickets"),
                ("DELETE", r"/api/v1/games/keno/tickets/(?P<ticket_id>[^/]+)"),
                ("POST", r"/api/v1/games/keno/draw"),
            },
        )
        # Read the existing state route.
        response = self.handlers[("GET", r"/api/v1/games/keno/state")]({}, {})
        # Require the API to expose the exact authoritative engine table.
        self.assertEqual(response["paytable"], engine.PAYTABLE)
        # Require existing compatible response keys to remain present.
        self.assertTrue({"game", "state", "player", "players", "paytable"}.issubset(response))
        # Read the frozen contract skeleton.
        contract = (ROOT / "contracts" / "openapi" / "keno.v1.yaml").read_text(encoding="utf-8")
        # Require every existing v1 route to remain declared.
        self.assertTrue(all(path in contract for path in ("/api/v1/games/keno/state:", "/api/v1/games/keno/tickets:", "/api/v1/games/keno/tickets/{ticket_id}:", "/api/v1/games/keno/draw:")))

    # Prove loss, first award, fractional rounding, jackpot, and maximum stake through real route money boundaries.
    def test_real_route_purchase_draw_ledger_and_history_equations(self):
        # Declare representative scenarios spanning no award through catalog jackpot and max stake.
        scenarios = (
            # Prove a one-spot loss at the frozen minimum.
            {"name": "loss", "picks": 1, "catches": 0, "amount": 0.01},
            # Prove the first listed one-spot award at the frozen minimum.
            {"name": "first", "picks": 1, "catches": 1, "amount": 0.01},
            # Prove fractional multiplier and cent rounding on a mid-tier nine-spot result.
            {"name": "fractional", "picks": 9, "catches": 5, "amount": 0.03},
            # Prove the exact visible catalog jackpot at a low accepted stake.
            {"name": "jackpot", "picks": 20, "catches": 20, "amount": 0.01},
            # Prove successful settlement at the exact maximum accepted amount and maximum jackpot together.
            {"name": "maximum_jackpot", "picks": 20, "catches": 20, "amount": 1_000_000},
        )
        # Execute every representative scenario in a fresh provider.
        for scenario in scenarios:
            # Report the named case if one assertion fails.
            with self.subTest(scenario["name"]):
                # Reset all wallet, ledger, history, and state rows.
                self.reset_runtime()
                # Settle one real route scenario.
                starting_balance, purchase, ticket, response = self.settle_route(scenario["picks"], scenario["catches"], scenario["amount"])
                # Read the one human result and settlement.
                result = response["draw"]["results"][0]
                # Resolve the authoritative multiplier and production payout.
                multiplier = engine.PAYTABLE[scenario["picks"]].get(scenario["catches"], 0)
                # Apply the unchanged production float and round law.
                payout = round(float(scenario["amount"]) * multiplier, 2)
                # Require engine result identity and settlement math.
                self.assertEqual((result["ticket"]["ticket_id"], result["multiplier"], result["payout"]), (ticket["ticket_id"], multiplier, payout))
                # Read durable current-player rows.
                rows = ledger.read_recent("human", 20)
                # Require one purchase debit with exact ticket identity and amount.
                debit_rows = [row for row in rows if row["transaction_type"] == "KENO_TICKET_PURCHASED"]
                # Require one debit and its exact signed amount.
                self.assertEqual((len(debit_rows), debit_rows[0]["amount"]), (1, -round(float(scenario["amount"]), 2)))
                # Require the purchase details to carry exact ticket and selected spots.
                self.assertEqual((debit_rows[0]["details"]["ticket_id"], debit_rows[0]["details"]["spots"]), (ticket["ticket_id"], list(range(1, scenario["picks"] + 1))))
                # Read payout credits separately from the ticket debit.
                credit_rows = [row for row in rows if row["transaction_type"] == "KENO_PAYOUT_CREDIT"]
                # Branch for a paying result.
                if payout > 0:
                    # Require exactly one current-draw payout credit.
                    self.assertEqual(len(credit_rows), 1)
                    # Require exact amount, round, ticket details, and durable action key.
                    self.assertEqual((credit_rows[0]["amount"], credit_rows[0]["round_id"], credit_rows[0]["details"]["ticket_id"], credit_rows[0]["details"]["ledger_action_key"]), (payout, response["draw"]["round_id"], ticket["ticket_id"], f"{ticket['ticket_id']}:payout"))
                # Branch for a losing result.
                else:
                    # Require no zero-value payout row.
                    self.assertEqual(credit_rows, [])
                # Read the one aligned Keno history row.
                history_rows = history.recent_history(20, "keno")
                # Require exactly one history outcome.
                self.assertEqual(len(history_rows), 1)
                # Require current draw, ticket amount, payout, and win/loss classification.
                self.assertEqual((history_rows[0]["round_id"], float(history_rows[0]["amount"]), float(history_rows[0]["payout"]), history_rows[0]["outcome"]), (response["draw"]["round_id"], float(scenario["amount"]), payout, "win" if payout else "loss"))
                # Require the final wallet equation after one debit and optional payout credit.
                self.assertEqual(players.get_player("human")["balance"], round(starting_balance - float(scenario["amount"]) + payout, 2))
                # Require finite public result fields at representative and maximum scale.
                self.assertTrue(all(math.isfinite(float(result[key])) for key in ("multiplier", "payout")))
                # Require one state save for purchase and one for draw.
                self.assertEqual(self.saved_state.call_count, 2)
                # Require existing response state, player, players, and paytable keys after mutation.
                self.assertTrue({"draw", "settlements", "bot_tickets", "state", "player", "players", "paytable"}.issubset(response))

    # Prove exact same-result settlement replay returns one immutable credit and one history row.
    def test_draw_replay_returns_original_credit_without_duplicate_history(self):
        # Reset the provider for one exact replay scenario.
        self.reset_runtime()
        # Build a deterministic five-spot jackpot draw.
        selected, drawn = self.drawn_for(5, 5)
        # Purchase one ticket through the real route.
        purchase = self.handlers[("POST", r"/api/v1/games/keno/tickets")]({"spots": selected, "amount": 5}, {})
        # Snapshot the durable pre-draw state.
        pre_draw = copy.deepcopy(self.state)
        # Pin both entropy and round identity for an exact same-result retry.
        with mock.patch.object(engine, "_SYSTEM_RANDOM", ScriptedBalls(drawn)), mock.patch.object(engine, "new_id", return_value="kendraw-economics-replay"):
            # Commit the first payout.
            first = self.handlers[("POST", r"/api/v1/games/keno/draw")]({}, {})
        # Restore only the pre-draw game state to model an interrupted state publication.
        self.state = copy.deepcopy(pre_draw)
        # Repeat the exact draw identity and result through the same existing route.
        with mock.patch.object(engine, "_SYSTEM_RANDOM", ScriptedBalls(drawn)), mock.patch.object(engine, "new_id", return_value="kendraw-economics-replay"):
            # Require the provider-owned action registry to return the original credit.
            second = self.handlers[("POST", r"/api/v1/games/keno/draw")]({}, {})
        # Read both settlement records.
        first_settlement = first["settlements"][0]
        # Read the replay settlement record.
        second_settlement = second["settlements"][0]
        # Require the second route call to expose the replay marker.
        self.assertTrue(second_settlement["replayed"])
        # Require the original immutable ledger identity and no second wallet mutation.
        self.assertEqual(second_settlement["ledger"]["ledger_id"], first_settlement["ledger"]["ledger_id"])
        # Read rows under the exact durable payout identity.
        action_rows = [row for row in ledger.read_recent("human", 20) if row["details"].get("ledger_action_key") == f"{purchase['ticket']['ticket_id']}:payout"]
        # Require one payout row across both calls.
        self.assertEqual(len(action_rows), 1)
        # Require replay gating to retain one history outcome.
        self.assertEqual(len(history.recent_history(20, "keno")), 1)

    # Prove visible copy, matrix inventory, and fixtures stay tied to authoritative economics.
    def test_frontend_locales_visual_matrix_and_fixture_policy(self):
        # Read both installed Keno locale resources.
        locales = {
            # Load exact English copy.
            "en-US": json.loads((ROOT / "web" / "i18n" / "en-US" / "games" / "keno.json").read_text(encoding="utf-8")),
            # Load exact Russian copy.
            "ru-RU": json.loads((ROOT / "web" / "i18n" / "ru-RU" / "games" / "keno.json").read_text(encoding="utf-8")),
        }
        # Require both locales to distinguish ideal unit return from realized play-token rounding.
        self.assertTrue(all("paytable.economicsNote" in resource and "{multiplier}" in resource["paytable.majorMultiplier"] for resource in locales.values()))
        # Reject currency-like cents wording from the fake-token economics disclosure.
        self.assertNotIn("cent", locales["en-US"]["paytable.economicsNote"].lower())
        # Require the English disclosure to name hundredths of a play token explicitly.
        self.assertIn("hundredths of a play token", locales["en-US"]["paytable.economicsNote"])
        # Read the production frontend source.
        frontend = (ROOT / "web" / "games" / "keno.js").read_text(encoding="utf-8")
        # Require exact major multiplier visibility instead of replacement by a generic label.
        self.assertIn("paytable.majorMultiplier", frontend)
        # Require both open-ticket and settled-history amounts to restore the live amount control.
        self.assertIn("amount = Number(ticket.amount)", frontend)
        # Require settled-history amount restoration for repeat and autoplay after reload.
        self.assertIn("amount = Number(result.ticket.amount)", frontend)
        # Require amount blur to synchronize state without rerendering and detaching the clicked Draw control.
        self.assertIn("addEventListener('change', readAmount)", frontend)
        # Reject the prior blur-time root replacement that swallowed the first public Draw click.
        self.assertNotIn("addEventListener('change', () => { readAmount(); render(); })", frontend)
        # Read the governed visual inventory.
        visual = json.loads((ROOT / "tests" / "visual" / "visual_matrix.json").read_text(encoding="utf-8"))
        # Resolve the single Keno matrix entry.
        keno_surface = next(surface for surface in visual["surfaces"] if surface["id"] == "keno")
        # Require all eight owner-approved states.
        self.assertEqual(keno_surface["states"], ["selection", "drawing", "result", "edge_idle", "edge_selected_focus_visible", "edge_final_caught", "route_restored", "repeat_available"])
        # Require both installed locales and all four global viewports.
        self.assertEqual((keno_surface["locales"], keno_surface["viewports"]), (["en-US", "ru-RU"], ["desktop_primary", "desktop_compact", "tablet", "mobile"]))
        # Read the hosted Browser harness as an inert policy artifact.
        browser_source = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Require fixtures to derive one-spot values from the authoritative table.
        self.assertIn("keno_engine.PAYTABLE[1][1]", browser_source)
        # Require a complete 64-cell evidence counter and exact numeric jackpot assertion.
        self.assertIn("keno_matrix_expected_cells=64", browser_source)
        # Require the Browser oracle to strip localized non-digits instead of matching a literal backslash-D token.
        self.assertIn(r"active_paytable_digits=re.sub(r'\D',''", browser_source)
        # Require the full-catalog jackpot value to be sourced from the server table.
        self.assertIn("keno_engine.PAYTABLE[20][20]", browser_source)
