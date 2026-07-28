"""Listener-free catalog rule-schema governance tests for SEC-014."""

# Import standard unit-test support for focused descriptor fixtures.
import unittest

# Import the canonical runtime catalog used by startup and validation.
from casino.config import GAMES
# Import pure schema and coercion checks so fixtures need no server or persisted data.
from casino.core.game_rules import coerce_request, declared_fields, schema_for, validate_rule_schema
# Import the public validation envelope so rejection messages can be checked directly.
from casino.errors import ValidationError
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
    # Prove internal schema lookup and deterministic field declaration use the canonical catalog.
    def test_internal_schema_lookup_and_declared_fields(self):
        # Resolve the Blackjack schema through the new behavior-neutral catalog reader.
        schema = schema_for("blackjack")
        # Require the exact governed route rather than a derived or caller-authored path.
        self.assertEqual(schema["settings_route"], "/api/v1/games/blackjack/settings")
        # Require deterministic field order for a future handler allowlist replacement.
        self.assertEqual(declared_fields("roulette"), ("mode", "zero_rule"))
        # Keep every game without a settings descriptor inert.
        self.assertEqual(declared_fields("slots"), ())
        # Return absence rather than inventing metadata for an unknown game.
        self.assertIsNone(schema_for("not-a-game"))

    # Prove every non-settings path preserves the exact original request object.
    def test_undeclared_path_is_reference_identical(self):
        # Build one object carrying nested data so accidental copying is observable.
        body = {"decks": "6", "nested": {"keep": True}}
        # Pass a real game action path that has no rule descriptor.
        result = coerce_request("/api/v1/games/blackjack/rounds", body)
        # Require exact object identity, not merely equality, for the inert boundary.
        self.assertIs(result, body)

    # Prove declared fields become canonical types while unknown keys remain untouched.
    def test_declared_request_values_are_coerced_without_mutating_input(self):
        # Supply numeric strings, a strict boolean, and one handler-ignored key.
        body = {
            "decks": "6",
            "blackjack_payout": "1.5",
            "dealer_hits_soft_17": False,
            "ignored": {"keep": "exact"},
        }
        # Coerce through the exact descriptor-owned settings route.
        result = coerce_request("/api/v1/games/blackjack/settings", body)
        # Require integer counts to become real integers.
        self.assertEqual(result["decks"], 6)
        # Require numeric enum strings to become the descriptor-owned float member.
        self.assertEqual(result["blackjack_payout"], 1.5)
        # Require strict booleans to remain unchanged.
        self.assertIs(result["dealer_hits_soft_17"], False)
        # Preserve unknown handler keys without interpreting or deleting them.
        self.assertIs(result["ignored"], body["ignored"])
        # Preserve the caller-owned request object for audit and retry safety.
        self.assertEqual(body["decks"], "6")
        # Return a distinct mapping only for a governed settings route.
        self.assertIsNot(result, body)

    # Prove every dangerous numeric representation fails before state or arithmetic exists.
    def test_numeric_domains_reject_nonfinite_fractional_boolean_and_bounds(self):
        # Enumerate one representative attack for each finite/type/range boundary.
        cases = (
            # Reject non-finite strings accepted by Python float conversion.
            ({"decks": "NaN"}, "decks must be finite"),
            # Reject overflowed JSON exponent values before any allocation.
            ({"decks": 1e999}, "decks must be finite"),
            # Reject fractional counts before integer narrowing.
            ({"decks": 2.5}, "decks must be a whole number"),
            # Reject bool-as-number despite Python's integer subclassing.
            ({"decks": True}, "decks must be numeric"),
            # Reject values below the descriptor minimum.
            ({"decks": 0}, "decks must be at least 1"),
            # Reject values above the finite allocation maximum.
            ({"decks": 9}, "decks must be at most 8"),
        )
        # Exercise every invalid request without opening a listener or state store.
        for body, message in cases:
            # Keep each failure independently attributable.
            with self.subTest(body=body):
                # Require the standard validation envelope for the future router hook.
                with self.assertRaisesRegex(ValidationError, f"^{message}$"):
                    # Coerce against the shipped Blackjack descriptor.
                    coerce_request("/api/v1/games/blackjack/settings", body)

    # Prove closed vocabularies reject truthiness and canonicalize numeric members.
    def test_closed_enums_are_strict_and_non_reflecting(self):
        # Accept a JSON integer that is numerically equal to the descriptor float member.
        payout = coerce_request("/api/v1/games/blackjack/settings", {"blackjack_payout": 1})
        # Return the exact descriptor-owned float representation.
        self.assertIs(type(payout["blackjack_payout"]), float)
        # Reject an unlisted numeric payout without reflecting it.
        with self.assertRaisesRegex(ValidationError, "^blackjack_payout must be one of the configured values$"):
            # Exercise a finite value outside the closed payout vocabulary.
            coerce_request("/api/v1/games/blackjack/settings", {"blackjack_payout": 1.4})
        # Reject a wrong-case string enum without permissive normalization.
        with self.assertRaisesRegex(ValidationError, "^mode must be one of the configured values$"):
            # Exercise Roulette's existing server-owned closed vocabulary.
            coerce_request("/api/v1/games/roulette/settings", {"mode": "Single"})
        # Reject a string pretending to be a boolean switch.
        with self.assertRaisesRegex(ValidationError, "^dealer_hits_soft_17 must be true or false$"):
            # Prove strict bool validation stays distinct from enum handling.
            coerce_request("/api/v1/games/blackjack/settings", {"dealer_hits_soft_17": "false"})

    # Prove scalar bodies fail only on a declared settings route with a fixed diagnostic.
    def test_declared_route_requires_object_without_reflection(self):
        # Keep one secret-like marker that must never appear in a public error.
        marker = "private-value-that-must-not-echo"
        # Require a fixed validation response for a governed route.
        with self.assertRaises(ValidationError) as captured:
            # Pass the marker as scalar content rather than a mapping.
            coerce_request("/api/v1/games/blackjack/settings", marker)
        # Require the stable object diagnostic.
        self.assertEqual(str(captured.exception), "Game settings body must be an object")
        # Prove caller content is absent from the public message.
        self.assertNotIn(marker, str(captured.exception))

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
