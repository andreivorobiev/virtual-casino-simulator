"""Listener-free catalog rule-schema governance tests for SEC-014."""

# Import standard unit-test support for focused descriptor fixtures.
import unittest

# Import the canonical runtime catalog used by startup and validation.
from casino.config import GAMES
# Import pure schema checks so unsafe descriptor fixtures need no server or persisted data.
from casino.core.game_rules import validate_rule_schema
# Import the public registry projection to prove internal schemas never reach browser clients.
from casino.games.registry import list_games
# Import the two merged #404 domains so this inert bridge cannot drift before runtime migration.
from casino.games.baccarat.api import RULE_DOMAIN as BACCARAT_RULE_DOMAIN
# Import the blackjack domain separately so each descriptor remains owned by its game.
from casino.games.blackjack.api import RULE_DOMAIN as BLACKJACK_RULE_DOMAIN
# Import catalog helpers that discover real route registration without binding a listener.
from scripts.validate_game_catalog import resolve_callable, validate_settings_schema


# Prove settings routes, safety flags, defaults, and public projection remain descriptor-driven.
class GameRuleSchemaTests(unittest.TestCase):
    # Validate every current settings surface through its real backend registration callable.
    def test_current_settings_routes_have_valid_matching_descriptors(self):
        # Collect all catalog validation defects across every registered game.
        errors = []
        # Exercise every game so a fourth settings route cannot bypass the same gate.
        for game in GAMES:
            # Resolve the exact production registration callable from module-owned metadata.
            register = resolve_callable(game["backend"]["register"], f"{game['id']} backend register", errors)
            # Compare discovered routes, descriptor structure, safety flags, and engine defaults.
            validate_settings_schema(game, register, errors)
        # Require the full catalog to satisfy the rule-domain gate.
        self.assertEqual(errors, [])

    # Prove the new descriptors exactly mirror the already-merged #404 runtime domains.
    def test_descriptors_match_current_runtime_domains(self):
        # Index current catalog entries by stable game id for focused comparisons.
        games = {game["id"]: game for game in GAMES}
        # Compare the two routes already using the shared apply_rule_updates boundary.
        for game_id, runtime_domain in (("blackjack", BLACKJACK_RULE_DOMAIN), ("baccarat", BACCARAT_RULE_DOMAIN)):
            # Read only the core domain keys shared with the current runtime validator.
            descriptor_domain = {
                # Strip semantic governance flags and documented fallbacks before equality.
                field: {key: value for key, value in spec.items() if key in {"kind", "min", "max", "values"}}
                # Visit every field declared by this game's descriptor.
                for field, spec in games[game_id]["rules"]["fields"].items()
            }
            # Require the inert descriptor to describe exactly what the merged route enforces today.
            self.assertEqual(descriptor_domain, runtime_domain)
        # Require roulette's existing hand-written settings fields to be completely represented.
        self.assertEqual(set(games["roulette"]["rules"]["fields"]), {"mode", "zero_rule"})

    # Prove a future game cannot register settings without declaring its legal rule domain.
    def test_settings_route_without_descriptor_fails(self):
        # Register one synthetic settings surface without starting a listener.
        def register(router):
            # Add a no-op handler because only route metadata is under test.
            router.post(r"/api/v1/games/example/settings")(lambda body, query: {})
        # Build the minimal catalog identity required by the gate.
        game = {"id": "example"}
        # Collect focused diagnostics instead of raising on the first defect.
        errors = []
        # Validate the synthetic route against its deliberately missing descriptor.
        validate_settings_schema(game, register, errors)
        # Require the diagnostic to name the undeclared settings surface.
        self.assertTrue(any("settings route lacks game.rules" in error for error in errors))

    # Prove a descriptor cannot claim a settings route the backend does not own.
    def test_descriptor_without_matching_route_fails(self):
        # Reuse the shipped roulette defaults while registering no settings route.
        game = {
            # Give the fixture a stable identity used in diagnostics and route ownership.
            "id": "example",
            # Declare a structurally valid schema whose route is intentionally absent.
            "rules": {
                # Name the route that the no-op backend does not register.
                "settings_route": "/api/v1/games/example/settings",
                # Resolve a real listener-free default factory for schema validation.
                "defaults": "casino.games.roulette.engine:default_state",
                # Read the roulette defaults directly from their top-level state.
                "defaults_key": "",
                # Declare one valid closed field so only route parity fails.
                "fields": {"mode": {"kind": "enum", "values": ["single", "double"]}},
            },
        }
        # Collect route-parity diagnostics.
        errors = []
        # Validate against a backend that deliberately registers nothing.
        validate_settings_schema(game, lambda router: None, errors)
        # Require the missing registered route to fail closed.
        self.assertTrue(any("is not a registered POST route" in error for error in errors))

    # Prove allocation and settlement flags cannot be declared without bounded domains.
    def test_unsafe_semantic_flags_fail(self):
        # Declare unsafe resource and payout fields around a valid route/default envelope.
        schema = {
            # Name the fixture's settings route.
            "settings_route": "/api/v1/games/example/settings",
            # Supply a syntactically valid callable reference; this pure helper does not import it.
            "defaults": "example.module:defaults",
            # Project defaults from the top-level fixture object.
            "defaults_key": "",
            # Omit the upper allocation bound and both settlement bounds deliberately.
            "fields": {
                "decks": {"kind": "int", "min": 1, "allocates": True, "default": 6},
                "payout": {"kind": "number", "settles": True, "default": 1.5},
            },
        }
        # Validate the unsafe schema against explicit defaults without any runtime request.
        errors = validate_rule_schema("example", schema, {})
        # Require allocation safety to identify the missing finite maximum.
        self.assertTrue(any("allocates resources and requires a finite max" in error for error in errors))
        # Require settlement safety to identify the missing closed or bounded payout domain.
        self.assertTrue(any("affects settlement and requires an enum or finite min and max" in error for error in errors))

    # Prove engine defaults and explicit legacy fallbacks must satisfy the declared domain.
    def test_out_of_domain_default_fails_and_explicit_fallback_passes(self):
        # Build one valid bounded schema whose engine default is deliberately too large.
        schema = {
            # Name the fixture's settings route.
            "settings_route": "/api/v1/games/example/settings",
            # Supply a syntactically valid callable reference for the pure schema contract.
            "defaults": "example.module:defaults",
            # Read defaults from the nested rules mapping.
            "defaults_key": "rules",
            # Declare one bounded allocation field and one documented legacy fallback.
            "fields": {
                "decks": {"kind": "int", "min": 1, "max": 8, "allocates": True},
                "cut_cards_remaining": {"kind": "int", "min": 1, "max": 104, "allocates": True, "default": 14},
            },
        }
        # Validate an oversized engine default while allowing the explicit cut-card fallback.
        errors = validate_rule_schema("example", schema, {"rules": {"decks": 100}})
        # Require the oversized engine default to fail its declared maximum.
        self.assertTrue(any("rule default decks is above its maximum" in error for error in errors))
        # Require the documented fallback to avoid a false missing-default error.
        self.assertFalse(any("cut_cards_remaining has no engine or descriptor default" in error for error in errors))

    # Prove internal callable references and safety metadata never leak into public catalog payloads.
    def test_public_catalog_omits_internal_rule_schema(self):
        # Read the same public projection returned by catalog and state endpoints.
        public_games = list_games()
        # Require every public game record to withhold descriptor-owned rule internals.
        self.assertTrue(all("rules" not in game for game in public_games))


# Support the focused developer command documented in the pull-request evidence.
if __name__ == "__main__":
    # Execute only this listener-free test module.
    unittest.main()
