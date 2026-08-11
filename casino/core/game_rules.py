# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure validation helpers for descriptor-owned game rule domains."""

# Import finite-number checks so descriptor bounds cannot contain NaN or infinity.
import math
# Import dynamic modules so engine-owned defaults remain referenced by descriptor instead of duplicated.
import importlib
# Cache default-factory resolution because immutable descriptors do not change within a process.
from functools import lru_cache
# Import the mapping protocol so malformed descriptor objects fail with focused diagnostics.
from collections.abc import Mapping

# Import the standard validation envelope for future request-path integration.
from casino.errors import ValidationError
# Reuse the shared finite-number boundary so NaN and infinity fail consistently.
from casino.core.validation import require_finite_number

# Define the closed schema vocabulary shared by catalog validation and future runtime enforcement.
RULE_KINDS = frozenset({"bool", "enum", "int", "number"})
# Define the only supported top-level keys so misspelled governance fields cannot pass silently.
RULE_SCHEMA_KEYS = frozenset({"defaults", "defaults_key", "fields", "settings_route"})
# Define the only supported field keys so safety flags and bounds remain machine-checkable.
RULE_FIELD_KEYS = frozenset({"allocates", "default", "kind", "max", "min", "settles", "values"})


# Report whether one descriptor number is finite while rejecting booleans masquerading as integers.
def _is_finite_number(value) -> bool:
    # Reject booleans before numeric checks because bool subclasses int in Python.
    if isinstance(value, bool):
        # Return false so true and false can never become numeric bounds.
        return False
    # Accept only built-in numeric values that convert to a finite float.
    return isinstance(value, (int, float)) and math.isfinite(float(value))


# Compare an enum value with strict types so True cannot match the numeric member 1.
def _enum_contains(values: list, value) -> bool:
    # Require both type and value equality for every declared member.
    return any(type(candidate) is type(value) and candidate == value for candidate in values)


# Resolve the current internal catalog lazily so importing this pure module cannot create a cycle.
def _catalog_games(catalog=None):
    # Use an injected catalog for listener-free fixtures and focused failure tests.
    if catalog is not None:
        # Return the caller-owned sequence without copying or normalizing it.
        return catalog
    # Import only when a runtime caller needs the canonical catalog.
    from casino.config import GAMES
    # Return the internal catalog whose public projection already strips rule descriptors.
    return GAMES


# Return one internal rule schema by stable catalog game identifier.
def schema_for(game_id: str, *, catalog=None):
    # Visit the selected catalog once because its size is bounded by repository validation.
    for game in _catalog_games(catalog):
        # Ignore malformed fixture rows that cannot own a stable game identifier.
        if not isinstance(game, Mapping) or game.get("id") != game_id:
            # Continue until the requested game is found.
            continue
        # Read the internal descriptor without exposing it through the public registry.
        schema = game.get("rules")
        # Return only an object schema because scalar metadata cannot be enforced safely.
        return schema if isinstance(schema, Mapping) else None
    # Report absence without inventing a schema for an unknown game.
    return None


# Return the complete sorted allowlist declared by one game descriptor.
def declared_fields(game_id: str, *, catalog=None) -> tuple[str, ...]:
    # Resolve the descriptor from the same internal catalog used by validation.
    schema = schema_for(game_id, catalog=catalog)
    # Return no fields when the game has no governed settings surface.
    if not isinstance(schema, Mapping):
        # Keep undeclared games inert for future central integration.
        return ()
    # Read the declared field map without accepting a scalar substitute.
    fields = schema.get("fields")
    # Return no fields when catalog validation has not supplied a usable map.
    if not isinstance(fields, Mapping):
        # Fail inertly here because the catalog gate owns structural diagnostics.
        return ()
    # Return deterministic names so handlers and tests never depend on JSON object order.
    return tuple(sorted(field for field in fields if isinstance(field, str) and field))


# Resolve the descriptor that owns one exact settings route.
def _schema_for_path(path: str, *, catalog=None):
    # Scan the bounded internal catalog for the exact route declared by one game.
    for game in _catalog_games(catalog):
        # Skip malformed rows before reading their internal rule metadata.
        if not isinstance(game, Mapping):
            # Continue to the remaining validated catalog entries.
            continue
        # Read only object descriptors because the catalog gate rejects every other shape.
        schema = game.get("rules")
        # Ignore games whose descriptor is absent or structurally unusable.
        if not isinstance(schema, Mapping):
            # Keep every undeclared game and non-settings route inert.
            continue
        # Return the descriptor only for an exact route match.
        if schema.get("settings_route") == path:
            # Stop at the owning descriptor after catalog validation proves route uniqueness.
            return schema
    # Return absence so undeclared paths preserve their original request object.
    return None


# Coerce one caller value through a structurally validated descriptor field.
def coerce_rule_value(field: str, value, spec: Mapping):
    # Fail closed if runtime integration is attempted with metadata the catalog gate should reject.
    if not isinstance(spec, Mapping) or spec.get("kind") not in RULE_KINDS:
        # Publish one stable message without exposing descriptor internals.
        raise ValidationError("Game rule configuration is unavailable")
    # Read the validated domain kind once for focused coercion.
    kind = spec["kind"]
    # Require strict booleans so strings and numeric truthiness cannot toggle table rules.
    if kind == "bool":
        # Reject every non-boolean representation without reflecting its supplied value.
        if not isinstance(value, bool):
            # Name only the descriptor-owned field in the public diagnostic.
            raise ValidationError(f"{field} must be true or false")
        # Preserve the canonical JSON boolean unchanged.
        return value
    # Resolve closed vocabularies without broad Python equality between bool and numbers.
    if kind == "enum":
        # Read the structurally validated member list.
        values = spec.get("values")
        # Fail closed if a future caller bypasses the catalog gate.
        if not isinstance(values, list) or not values:
            # Avoid publishing the malformed internal vocabulary.
            raise ValidationError("Game rule configuration is unavailable")
        # Treat a wholly numeric enum as numeric input while still rejecting booleans.
        if all(_is_finite_number(candidate) for candidate in values):
            # Reject bool before conversion because float(True) would otherwise become one.
            if isinstance(value, bool):
                # Use the same stable enum diagnostic as every other invalid member.
                raise ValidationError(f"{field} must be one of the configured values")
            # Convert numeric strings and JSON numbers through the shared finite gate.
            number = require_finite_number(value, field=field)
            # Return the descriptor-owned member so output type is canonical.
            for candidate in values:
                # Compare finite numeric magnitude only after bool and non-finite rejection.
                if float(candidate) == number:
                    # Preserve the exact int or float type stored in the descriptor.
                    return candidate
        # Preserve strict type-and-value matching for string or mixed vocabularies.
        elif _enum_contains(values, value):
            # Return the descriptor-owned value rather than the caller's equivalent object.
            return next(candidate for candidate in values if type(candidate) is type(value) and candidate == value)
        # Reject every member outside the closed descriptor vocabulary.
        raise ValidationError(f"{field} must be one of the configured values")
    # Reject bool before numeric conversion because it subclasses int in Python.
    if isinstance(value, bool):
        # Publish the numeric expectation without reflecting the caller value.
        raise ValidationError(f"{field} must be numeric")
    # Convert numeric strings and JSON numbers through the shared non-finite boundary.
    number = require_finite_number(value, field=field)
    # Require an exact whole number for allocation and count fields.
    if kind == "int":
        # Reject fractional values before narrowing their type.
        if number != int(number):
            # Name the descriptor field without echoing the rejected value.
            raise ValidationError(f"{field} must be a whole number")
        # Return a real integer so downstream code never receives a numeric string or float count.
        number = int(number)
    # Fail closed when malformed runtime metadata omits finite bounds.
    if not _is_finite_number(spec.get("min")) or not _is_finite_number(spec.get("max")):
        # Keep internal bound defects out of the public response.
        raise ValidationError("Game rule configuration is unavailable")
    # Enforce the inclusive lower bound declared by the module owner.
    if number < spec["min"]:
        # Report the safe descriptor bound without reflecting the request value.
        raise ValidationError(f"{field} must be at least {spec['min']}")
    # Enforce the inclusive upper bound that protects settlement and allocation.
    if number > spec["max"]:
        # Report the safe descriptor bound without reflecting the request value.
        raise ValidationError(f"{field} must be at most {spec['max']}")
    # Return a canonical int or finite float after all domain checks pass.
    return number


# Coerce declared fields for one exact settings route while leaving every other path inert.
def coerce_request(path: str, body, *, catalog=None):
    # Resolve the descriptor by exact route without interpreting caller-controlled path fragments.
    schema = _schema_for_path(path, catalog=catalog)
    # Preserve object identity for every undeclared path and all non-settings actions.
    if schema is None:
        # Return the original object byte-for-byte and reference-identically.
        return body
    # Require an object only after the request is known to target a governed settings route.
    if not isinstance(body, Mapping):
        # Publish a fixed message without reflecting scalar request content.
        raise ValidationError("Game settings body must be an object")
    # Read the field map whose structure is enforced by the catalog gate.
    fields = schema.get("fields")
    # Fail closed if runtime integration somehow bypasses repository validation.
    if not isinstance(fields, Mapping):
        # Do not guess a permissive rule surface from malformed metadata.
        raise ValidationError("Game rule configuration is unavailable")
    # Copy a governed request so the caller-owned object remains unchanged on success or failure.
    coerced = dict(body)
    # Visit every declared field rather than trusting request key order.
    for field in sorted(fields):
        # Preserve missing and unknown keys for the existing handler allowlist boundary.
        if field not in body:
            # Leave the current request copy untouched for this absent field.
            continue
        # Replace only declared values with their canonical validated representation.
        coerced[field] = coerce_rule_value(field, body[field], fields[field])
    # Return the validated request copy for a future central router hook.
    return coerced


# Resolve one descriptor-owned default factory through a bounded immutable reference.
@lru_cache(maxsize=32)
def _default_factory(reference: str):
    # Split the validated module-and-callable reference once.
    module_name, callable_name = reference.split(":", 1)
    # Import the owning game engine through the standard module loader.
    module = importlib.import_module(module_name)
    # Return the validated public factory without invoking it during import.
    return getattr(module, callable_name)


# Return the engine-owned default rule mapping for one validated schema.
def _default_rules(schema: Mapping) -> Mapping:
    # Resolve and invoke the immutable descriptor reference for a fresh state object.
    defaults_state = _default_factory(schema["defaults"])()
    # Fail closed if runtime metadata bypassed catalog validation.
    if not isinstance(defaults_state, Mapping):
        # Use the same fixed public diagnostic as malformed field metadata.
        raise ValidationError("Game rule configuration is unavailable")
    # Read nested rules when named, or the complete state for top-level Roulette settings.
    defaults = defaults_state.get(schema["defaults_key"]) if schema["defaults_key"] else defaults_state
    # Reject a scalar projection rather than inventing defaults.
    if not isinstance(defaults, Mapping):
        # Keep descriptor internals out of the public diagnostic.
        raise ValidationError("Game rule configuration is unavailable")
    # Return the engine-owned mapping for canonical repair values.
    return defaults


# Clamp persisted descriptor-owned rules to canonical values without rewriting unrelated state. (SEC-014)
def clamp_state_rules(game_id: str, state, *, catalog=None):
    # Keep undeclared games and malformed outer state inert at this shared read boundary.
    if not isinstance(state, dict):
        # Return the original object and no repair evidence.
        return state, ()
    # Resolve the same internal descriptor used by request coercion and catalog validation.
    schema = schema_for(game_id, catalog=catalog)
    # Leave games without a governed settings route byte-for-byte untouched.
    if not isinstance(schema, Mapping):
        # Report no repaired fields for the inert path.
        return state, ()
    # Read the validated field map and engine-owned defaults once.
    fields = schema.get("fields")
    # Fail closed when runtime code somehow bypasses the catalog structure gate.
    if not isinstance(fields, Mapping):
        # Use the fixed configuration diagnostic rather than guessing a permissive domain.
        raise ValidationError("Game rule configuration is unavailable")
    # Resolve canonical defaults from the owning engine.
    defaults = _default_rules(schema)
    # Read the descriptor projection key once for nested or top-level state.
    defaults_key = schema.get("defaults_key")
    # Select the target mapping when the persisted shape remains usable.
    target = state.get(defaults_key) if defaults_key else state
    # Replace a poisoned nested rules scalar with a fresh mapping while preserving outer state.
    if defaults_key and not isinstance(target, dict):
        # Install an empty mapping that the field loop will populate from safe defaults.
        target = {}
        # Attach the repaired mapping to the exact descriptor-owned state key.
        state[defaults_key] = target
    # Fail closed if a top-level governed state somehow is not mutable after the outer dict check.
    if not isinstance(target, dict):
        # Keep the runtime error stable and value-free.
        raise ValidationError("Game rule configuration is unavailable")
    # Collect only descriptor field names so logs never contain persisted values.
    repaired = []
    # Visit declared fields deterministically for stable tests and notices.
    for field in sorted(fields):
        # Read the canonical fallback from engine state or the documented legacy default.
        default_value = defaults[field] if field in defaults else fields[field].get("default")
        # Start with the safe default for missing or rejected persisted values.
        canonical = default_value
        # Attempt to canonicalize a present persisted value through the same request domain.
        if field in target:
            # Isolate validation so one poisoned field does not block repair of the complete state.
            try:
                # Convert finite strings/numbers and strict enums to descriptor-owned representations.
                canonical = coerce_rule_value(field, target[field], fields[field])
            # Repair any stable validation rejection to the engine-owned default.
            except ValidationError:
                # Keep the default selected above without logging the rejected value.
                canonical = default_value
        # Compare both type and value so numeric canonicalization is persisted on the next normal save.
        if field not in target or type(target[field]) is not type(canonical) or target[field] != canonical:
            # Replace only this descriptor-owned field with its canonical safe value.
            target[field] = canonical
            # Record the field name for value-free repair evidence.
            repaired.append(field)
    # Return the repaired state and immutable deterministic field evidence.
    return state, tuple(repaired)


# Validate one field specification independently from any engine default.
def validate_field_spec(field: str, spec) -> list[str]:
    # Collect every defect so one validator run reports the complete repair packet.
    errors = []
    # Reject non-object field definitions before reading their keys.
    if not isinstance(spec, Mapping):
        # Identify the exact field whose descriptor shape is invalid.
        return [f"rule field {field} must be an object"]
    # Reject unknown keys so misspelled bounds or safety flags cannot be ignored.
    unknown = sorted(set(spec) - RULE_FIELD_KEYS)
    # Report all unsupported keys in one deterministic diagnostic.
    if unknown:
        # Name the field and keys without reflecting any runtime request value.
        errors.append(f"rule field {field} has unsupported keys: {', '.join(unknown)}")
    # Read the declared kind once for all shape-specific checks.
    kind = spec.get("kind")
    # Require one of the intentionally small supported domain kinds.
    if kind not in RULE_KINDS:
        # Report the invalid kind against the field that owns it.
        errors.append(f"rule field {field} has unsupported kind {kind}")
        # Return because remaining checks depend on a recognized kind.
        return errors
    # Validate the closed member list for enum fields.
    if kind == "enum":
        # Read the declared values without accepting tuples or scalar fallbacks.
        values = spec.get("values")
        # Require a non-empty JSON array because an empty enum can never accept its default.
        if not isinstance(values, list) or not values:
            # Report the missing closed vocabulary for this field.
            errors.append(f"rule field {field} enum values must be a non-empty list")
        # Reject numeric bounds on an enum because values already define its complete domain.
        if "min" in spec or "max" in spec:
            # Report the conflicting domain representations.
            errors.append(f"rule field {field} enum must not declare min or max")
    # Validate inclusive finite bounds for numeric fields.
    if kind in {"int", "number"}:
        # Require both bounds so settlement and allocation fields can never be half-bounded.
        if not _is_finite_number(spec.get("min")) or not _is_finite_number(spec.get("max")):
            # Report the missing or non-finite numeric domain.
            errors.append(f"rule field {field} must declare finite min and max")
        # Compare bounds only after both values passed finite-number validation.
        elif float(spec["min"]) > float(spec["max"]):
            # Report an inverted domain that would reject every value.
            errors.append(f"rule field {field} min must not exceed max")
        # Require integer bounds for integer fields so the descriptor does not imply fractional counts.
        if kind == "int" and any(_is_finite_number(spec.get(key)) and float(spec[key]) != int(spec[key]) for key in ("min", "max")):
            # Report fractional bounds on a whole-number rule.
            errors.append(f"rule field {field} integer bounds must be whole numbers")
        # Reject enum members on numeric fields so one field has only one source of truth.
        if "values" in spec:
            # Report the conflicting domain representation.
            errors.append(f"rule field {field} numeric domain must not declare values")
    # Reject numeric or enum metadata on boolean switches.
    if kind == "bool" and any(key in spec for key in ("min", "max", "values")):
        # Report unexpected domain metadata for a strict boolean.
        errors.append(f"rule field {field} boolean domain must not declare min, max, or values")
    # Require safety flags, when present, to be literal booleans.
    for flag in ("allocates", "settles"):
        # Reject strings or numeric truthiness that could disable a catalog safety gate.
        if flag in spec and not isinstance(spec[flag], bool):
            # Report the exact malformed semantic flag.
            errors.append(f"rule field {field} {flag} must be true or false")
    # Require allocation-driving values to carry a finite upper bound.
    if spec.get("allocates") is True and not _is_finite_number(spec.get("max")):
        # Report the missing denial-of-service boundary.
        errors.append(f"rule field {field} allocates resources and requires a finite max")
    # Require settlement-driving values to be closed or bounded on both sides.
    if spec.get("settles") is True and kind != "enum" and (not _is_finite_number(spec.get("min")) or not _is_finite_number(spec.get("max"))):
        # Report the missing payout-integrity boundary.
        errors.append(f"rule field {field} affects settlement and requires an enum or finite min and max")
    # Return every structural field defect to the catalog validator.
    return errors


# Validate one value against a structurally valid field specification.
def validate_rule_value(field: str, value, spec: Mapping) -> str | None:
    # Read the already-validated kind once for focused value checks.
    kind = spec.get("kind")
    # Require real booleans for switches instead of truthy strings or numbers.
    if kind == "bool":
        # Return a diagnostic only when the value is not a literal bool.
        return None if isinstance(value, bool) else f"rule default {field} must be true or false"
    # Require strict member equality for closed enums.
    if kind == "enum":
        # Read a safe member list even when a caller invokes this helper before structural validation.
        values = spec.get("values") if isinstance(spec.get("values"), list) else []
        # Return a diagnostic when the value is outside the declared closed vocabulary.
        return None if _enum_contains(values, value) else f"rule default {field} is outside its enum"
    # Reject booleans and non-numeric values before numeric comparisons.
    if not _is_finite_number(value):
        # Report the expected finite numeric default.
        return f"rule default {field} must be finite and numeric"
    # Require an exact whole number for integer fields.
    if kind == "int" and float(value) != int(value):
        # Report the fractional default independently from range errors.
        return f"rule default {field} must be a whole number"
    # Reject values below the inclusive lower bound.
    if _is_finite_number(spec.get("min")) and float(value) < float(spec["min"]):
        # Report the lower-bound violation without formatting untrusted runtime data.
        return f"rule default {field} is below its minimum"
    # Reject values above the inclusive upper bound.
    if _is_finite_number(spec.get("max")) and float(value) > float(spec["max"]):
        # Report the upper-bound violation without formatting untrusted runtime data.
        return f"rule default {field} is above its maximum"
    # Report success when the default satisfies the declared domain.
    return None


# Validate one complete game rule descriptor and its resolved engine defaults.
def validate_rule_schema(game_id: str, schema, defaults_state) -> list[str]:
    # Collect schema and default defects for one deterministic validator report.
    errors = []
    # Reject missing or scalar descriptors before reading nested keys.
    if not isinstance(schema, Mapping):
        # Identify the catalog game whose settings route lacks a usable schema.
        return [f"catalog game {game_id} rules must be an object"]
    # Reject unknown top-level keys so the validator never ignores a misspelled control.
    unknown = sorted(set(schema) - RULE_SCHEMA_KEYS)
    # Report every unsupported top-level key together.
    if unknown:
        # Name the owning game and malformed keys.
        errors.append(f"catalog game {game_id} rules has unsupported keys: {', '.join(unknown)}")
    # Read the declared route as text without accepting implicit values.
    settings_route = schema.get("settings_route")
    # Require the frozen game-route namespace and settings suffix before exact registration parity.
    if not isinstance(settings_route, str) or not settings_route.startswith("/api/v1/games/") or not settings_route.endswith("/settings"):
        # Report the route identity defect.
        errors.append(f"catalog game {game_id} rules must declare an /api/v1/games/.../settings route")
    # Require a callable reference so defaults are checked against engine-owned state.
    if not isinstance(schema.get("defaults"), str) or ":" not in schema.get("defaults", ""):
        # Report the missing module-and-callable reference.
        errors.append(f"catalog game {game_id} rules must declare a defaults callable")
    # Require a string key, including the deliberate empty string for top-level rules.
    defaults_key = schema.get("defaults_key")
    # Reject omitted or non-string default projections.
    if not isinstance(defaults_key, str):
        # Report the invalid projection key.
        errors.append(f"catalog game {game_id} rules defaults_key must be a string")
    # Require at least one declared rule field.
    fields = schema.get("fields")
    # Reject missing, scalar, or empty field maps.
    if not isinstance(fields, Mapping) or not fields:
        # Report the empty domain and return because field iteration would be meaningless.
        errors.append(f"catalog game {game_id} rules fields must be a non-empty object")
        # Return top-level defects after the field map failed.
        return errors
    # Reject a non-object engine default before projecting rule values.
    if not isinstance(defaults_state, Mapping):
        # Report the malformed defaults factory result.
        errors.append(f"catalog game {game_id} rules defaults callable must return an object")
        # Use an empty object so field diagnostics remain deterministic.
        defaults_state = {}
    # Project nested rules when the descriptor names a key, or use the full state when it is empty.
    default_rules = defaults_state.get(defaults_key) if defaults_key else defaults_state
    # Reject a missing or scalar rule-default projection.
    if not isinstance(default_rules, Mapping):
        # Report the exact projection key without reflecting runtime player data.
        errors.append(f"catalog game {game_id} rules defaults_key does not resolve to an object")
        # Use an empty object so every field reports its missing default.
        default_rules = {}
    # Validate every declared field and its canonical default.
    for field in sorted(fields):
        # Read one field specification from the descriptor.
        spec = fields[field]
        # Require stable non-empty identifier keys.
        if not isinstance(field, str) or not field:
            # Report the malformed field key.
            errors.append(f"catalog game {game_id} has an invalid rule field name")
            # Skip value checks because the field cannot be addressed reliably.
            continue
        # Add structural defects before checking a default against the domain.
        field_errors = validate_field_spec(field, spec)
        # Prefix each field diagnostic with its owning catalog game.
        errors.extend(f"catalog game {game_id} {error}" for error in field_errors)
        # Skip default validation when the field specification is not an object.
        if not isinstance(spec, Mapping):
            # Continue to the remaining fields after the focused shape error.
            continue
        # Prefer the engine-owned default whenever the factory declares this rule.
        if field in default_rules:
            # Read the canonical engine default for domain validation.
            default_value = default_rules[field]
        # Permit an explicit descriptor fallback only for legacy engine code that already uses that fallback.
        elif "default" in spec:
            # Read the documented fallback rather than silently inventing a default.
            default_value = spec["default"]
        else:
            # Report a field that has no canonical or documented fallback.
            errors.append(f"catalog game {game_id} rule field {field} has no engine or descriptor default")
            # Continue because there is no value to validate.
            continue
        # Validate the selected default only when the structural kind is recognized.
        if spec.get("kind") in RULE_KINDS:
            # Calculate one focused default-domain diagnostic.
            default_error = validate_rule_value(field, default_value, spec)
            # Record the diagnostic when the default violates its own descriptor.
            if default_error:
                # Prefix the owning catalog game for actionable output.
                errors.append(f"catalog game {game_id} {default_error}")
    # Return the complete schema/default defect list.
    return errors
