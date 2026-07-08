# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from datetime import datetime, timezone

# Define the utc_now function used by this module.
def utc_now() -> str:
    # Return the computed value to the caller.
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

# Define the date_stamp function used by this module.
def date_stamp() -> str:
    # Return the computed value to the caller.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
