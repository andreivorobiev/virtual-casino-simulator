# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import finite-number checks so hostile NaN and infinity values cannot bypass comparisons.
import math

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
    if amount < min_value:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError(f"amount must be at least {min_value}")
    if amount > max_value:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError(f"amount must be at most {max_value}")
    return amount

# Define the require_player_id function used by this module.
def require_player_id(data: dict) -> str:
    # Set player_id to the value needed for the next operation.
    player_id = data.get("player_id", "human")
    if not isinstance(player_id, str) or not player_id:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("player_id is required")
    return player_id
