"""Pure validation helpers for descriptor-owned game rule domains."""

# Import finite-number checks so descriptor bounds cannot contain NaN or infinity.
import math
# Import the mapping protocol so malformed descriptor objects fail with focused diagnostics.
from collections.abc import Mapping

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
