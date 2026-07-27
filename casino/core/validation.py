# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import finite-number checks so hostile NaN and infinity values cannot bypass comparisons.
import math

# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError


# Reject non-standard JSON numeric constants before a request reaches route handling. (CORE-025)
def reject_nonfinite_json_constant(_value: str):
    # Raise a fixed diagnostic without reflecting client-controlled request text.
    raise ValidationError("JSON numbers must be finite")


# Convert one caller value into a finite float for shared money boundaries. (CORE-025)
def require_finite_number(value, *, field="amount") -> float:
    # Start protected conversion so missing and malformed values share one public error.
    try:
        # Convert numeric strings and JSON numbers without applying money rounding yet.
        number = float(value)
    # Translate only expected conversion failures into the validation envelope.
    except (TypeError, ValueError, OverflowError):
        # Identify the caller-selected field without echoing its supplied value.
        raise ValidationError(f"{field} must be numeric")
    # Reject NaN and both infinities before any comparison or arithmetic occurs.
    if not math.isfinite(number):
        # Publish one stable diagnostic for every non-finite representation.
        raise ValidationError(f"{field} must be finite")
    # Return the finite unrounded value for the caller's domain-specific normalization.
    return number

# Define the require_amount function used by this module.
def require_amount(value, *, min_value=0.01, max_value=1_000_000) -> float:
    # Convert and reject non-finite inputs before rounding or bounds checks. (CORE-025)
    amount = round(require_finite_number(value), 2)
    # Branch when the following condition is true.
    if amount < min_value:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError(f"amount must be at least {min_value}")
    # Branch when the following condition is true.
    if amount > max_value:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError(f"amount must be at most {max_value}")
    # Return the computed value to the caller.
    return amount

# Coerce and bounds-check one caller-supplied table rule against its declared domain. (issue #404)
def _checked_rule_value(key: str, value, spec: dict):
    # Read the declared domain kind so each rule is validated by its own shape.
    kind = spec["kind"]
    # Handle boolean switches before numeric handling because bool is a subclass of int.
    if kind == "bool":
        # Accept only real booleans so truthy strings and numbers cannot enable a rule.
        if not isinstance(value, bool):
            # Name the rejected rule without echoing the caller-supplied value.
            raise ValidationError(f"{key} must be true or false")
        # Return the validated boolean unchanged.
        return value
    # Handle closed vocabularies where only listed members are legal.
    if kind == "enum":
        # Reject any value outside the declared member list.
        if value not in spec["values"]:
            # Publish the legal members so the caller can correct the request.
            raise ValidationError(f"{key} must be one of: {', '.join(str(v) for v in spec['values'])}")
        # Return the accepted member unchanged.
        return value
    # Reject booleans for numeric rules because True would otherwise pass as 1.
    if isinstance(value, bool):
        # Report the numeric expectation for the named rule.
        raise ValidationError(f"{key} must be numeric")
    # Convert through the shared finite-number gate so NaN and infinity cannot reach settlement math.
    number = require_finite_number(value, field=key)
    # Handle whole-number rules such as deck and split counts.
    if kind == "int":
        # Require an exact integer so fractional shoe sizes cannot be requested.
        if number != int(number):
            # Report the integral expectation for the named rule.
            raise ValidationError(f"{key} must be a whole number")
        # Narrow to int now that the value is known to be integral.
        number = int(number)
    # Enforce the declared lower bound for the rule.
    if number < spec["min"]:
        # Report the minimum without echoing the rejected value.
        raise ValidationError(f"{key} must be at least {spec['min']}")
    # Enforce the declared upper bound, which is what stops unbounded payout and shoe-size requests.
    if number > spec["max"]:
        # Report the maximum without echoing the rejected value.
        raise ValidationError(f"{key} must be at most {spec['max']}")
    # Return the validated numeric rule value.
    return number


# Apply caller-supplied table-rule updates through a declared per-game domain. (issue #404)
def apply_rule_updates(body: dict, rules: dict, spec: dict) -> dict:
    # Visit only the rules this game declares, so an undeclared key can never reach persisted state.
    for key, rule_spec in spec.items():
        # Skip any rule the caller did not attempt to change.
        if key not in body:
            # Leave the currently persisted value untouched.
            continue
        # Store the validated replacement so settlement math only ever reads in-domain values.
        rules[key] = _checked_rule_value(key, body[key], rule_spec)
    # Return the same rules mapping so callers can chain or persist it directly.
    return rules

# Define the require_player_id function used by this module.
def require_player_id(data: dict) -> str:
    # Set player_id to the value needed for the next operation.
    player_id = data.get("player_id", "human")
    # Branch when the following condition is true.
    if not isinstance(player_id, str) or not player_id:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("player_id is required")
    # Return the computed value to the caller.
    return player_id
