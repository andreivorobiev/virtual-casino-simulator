# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use schema version metadata.
from casino.config import SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.errors import NotFoundError, ValidationError

# Define the default_players function used by this module.
def default_players() -> dict:
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Return the computed value to the caller.
    return {"schema_version": SCHEMA_VERSION, "players": [
        # Explain this executable/data line so future Codex changes preserve intent.
        {"player_id": "human", "display_name": "You", "type": "human", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
        # Explain this executable/data line so future Codex changes preserve intent.
        {"player_id": "bot_1", "display_name": "Ava", "type": "bot", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
        # Explain this executable/data line so future Codex changes preserve intent.
        {"player_id": "bot_2", "display_name": "Mia", "type": "bot", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
        # Explain this executable/data line so future Codex changes preserve intent.
        {"player_id": "bot_3", "display_name": "Zoe", "type": "bot", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
    ]}

# Define the load_players function used by this module.
def load_players() -> dict:
    # Set state to the configured provider's player document.
    state = get_storage_provider().load_players(default_players)
    # Branch when the following condition is true.
    if not isinstance(state, dict) or "players" not in state:
        # Set state to the value needed for the next operation.
        state = default_players()
    # Return the computed value to the caller.
    return state

# Define the save_players function used by this module.
def save_players(state: dict) -> None:
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Persist the player document through the active storage provider.
    get_storage_provider().save_players(state)

# Define the list_players function used by this module.
def list_players() -> list[dict]:
    # Return the computed value to the caller.
    return load_players()["players"]

# Define the get_player function used by this module.
def get_player(player_id: str) -> dict:
    # Iterate through the collection to process each item.
    for p in list_players():
        # Branch when the following condition is true.
        if p["player_id"] == player_id:
            # Return the computed value to the caller.
            return p
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Player {player_id} was not found")

# Define the update_player function used by this module.
def update_player(player_id: str, updater) -> dict:
    # Return the provider-managed update so JSON and MySQL share player semantics.
    return get_storage_provider().update_player(player_id, updater)

# Define the create_player function used by this module.
def create_player(display_name: str, kind: str = "human", balance: float = 5000.0) -> dict:
    # Branch when the following condition is true.
    if not display_name or not display_name.strip():
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("display_name is required")
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set player to the value needed for the next operation.
    player = {"player_id": new_id("player"), "display_name": display_name.strip(), "type": kind, "balance": round(float(balance),2), "created_at": now, "updated_at": now, "status": "active"}
    # Set state to the value needed for the next operation.
    state = load_players()
    # Execute this statement as part of the module's documented control flow.
    state["players"].append(player)
    # Execute this statement as part of the module's documented control flow.
    save_players(state)
    # Return the computed value to the caller.
    return player

# Define the ensure_player_for_user function used by this module.
def ensure_player_for_user(user_id: str, display_name: str, player_id: str | None = None) -> dict:
    # Branch when the caller supplied an existing player binding.
    if player_id:
        # Start protected logic so missing legacy players can be repaired.
        try:
            # Return the computed value to the caller.
            return get_player(player_id)
        # Handle the expected failure path for the protected logic.
        except NotFoundError:
            # Continue so a replacement player can be created for the user.
            pass
    # Set label to the value needed for the next operation.
    label = display_name.strip() if display_name and display_name.strip() else user_id
    # Return the computed value to the caller.
    return create_player(label, "human", 5000.0)
