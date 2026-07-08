# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError

# Define the require_amount function used by this module.
def require_amount(value, *, min_value=0.01, max_value=1_000_000) -> float:
    # Start protected logic so failures can be handled safely.
    try:
        # Set amount to the value needed for the next operation.
        amount = round(float(value), 2)
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("amount must be numeric")
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
