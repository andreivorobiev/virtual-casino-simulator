# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from __future__ import annotations
# Import required dependency so this module can use its public functions or constants.
from casino.config import DATA_DIR, SCHEMA_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import read_json, write_json
# Import required dependency so this module can use its public functions or constants.
from casino.core import players
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError, NotFoundError

# Set BOTS_PATH to the value needed for the next operation.
BOTS_PATH = DATA_DIR / "bots.json"

# Set CAPABILITIES to the value needed for the next operation.
CAPABILITIES = {
    # Execute this statement as part of the module's documented control flow.
    "roulette": {
        # Execute this statement as part of the module's documented control flow.
        "supports_bots": True,
        # Execute this statement as part of the module's documented control flow.
        "strategies": [
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"roulette_random_outside", "label":"Random Outside"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"roulette_red_black", "label":"Red/Black"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"roulette_random_number", "label":"Random Number"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"roulette_split_corner", "label":"Split/Corner"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"roulette_dozen_column", "label":"Dozens/Columns"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"roulette_racetrack", "label":"Racetrack/Snake"},
        ],
    },
    # Execute this statement as part of the module's documented control flow.
    "baccarat": {
        # Execute this statement as part of the module's documented control flow.
        "supports_bots": True,
        # Execute this statement as part of the module's documented control flow.
        "strategies": [
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"baccarat_banker", "label":"Banker"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"baccarat_player", "label":"Player"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"baccarat_tie", "label":"Tie Chaser"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"baccarat_random", "label":"Random"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"baccarat_pattern", "label":"Pattern Follower"},
        ],
    },
    # Execute this statement as part of the module's documented control flow.
    "keno": {
        # Execute this statement as part of the module's documented control flow.
        "supports_bots": True,
        # Execute this statement as part of the module's documented control flow.
        "strategies": [
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"keno_quick_pick_3", "label":"Quick Pick 3"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"keno_quick_pick_5", "label":"Quick Pick 5"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"keno_quick_pick_10", "label":"Quick Pick 10"},
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"keno_quick_pick_20", "label":"Quick Pick 20"},
        ],
    },
    # Execute this statement as part of the module's documented control flow.
    "bingo": {
        # Execute this statement as part of the module's documented control flow.
        "supports_bots": True,
        # Execute this statement as part of the module's documented control flow.
        "strategies": [
            # Explain this executable/data line so future Codex changes preserve intent.
            {"id":"bingo_standard_card", "label":"Standard Card"},
        ],
    },
    # Execute this statement as part of the module's documented control flow.
    "slots": {"supports_bots": False, "strategies": []},
    # Execute this statement as part of the module's documented control flow.
    "blackjack": {"supports_bots": False, "strategies": []},
}

# Set DEFAULT_STRATEGIES to the value needed for the next operation.
DEFAULT_STRATEGIES = {
    # Execute this statement as part of the module's documented control flow.
    "bot_1": {"roulette":"roulette_random_outside", "baccarat":"baccarat_banker", "keno":"keno_quick_pick_5", "bingo":"bingo_standard_card"},
    # Execute this statement as part of the module's documented control flow.
    "bot_2": {"roulette":"roulette_red_black", "baccarat":"baccarat_random", "keno":"keno_quick_pick_10", "bingo":"bingo_standard_card"},
    # Execute this statement as part of the module's documented control flow.
    "bot_3": {"roulette":"roulette_split_corner", "baccarat":"baccarat_player", "keno":"keno_quick_pick_20", "bingo":"bingo_standard_card"},
}
# Set DEFAULT_ENABLED to the value needed for the next operation.
DEFAULT_ENABLED = {"bot_1": True, "bot_2": True, "bot_3": False}
# Set DEFAULT_STAKES to the value needed for the next operation.
DEFAULT_STAKES = {"roulette": 5, "baccarat": 5, "keno": 3, "bingo": 5}


# Define the _player_name function used by this module.
def _player_name(player_id: str) -> str:
    # Start protected logic so failures can be handled safely.
    try:
        # Return the computed value to the caller.
        return players.get_player(player_id).get("display_name", player_id)
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Return the computed value to the caller.
        return player_id


# Define the default_bots function used by this module.
def default_bots() -> dict:
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set bots to the value needed for the next operation.
    bots = []
    # Iterate through the collection to process each item.
    for player_id in ["bot_1", "bot_2", "bot_3"]:
        # Execute this statement as part of the module's documented control flow.
        bots.append({
            # Execute this statement as part of the module's documented control flow.
            "bot_id": player_id,
            # Execute this statement as part of the module's documented control flow.
            "player_id": player_id,
            # Execute this statement as part of the module's documented control flow.
            "display_name": _player_name(player_id),
            # Execute this statement as part of the module's documented control flow.
            "enabled": DEFAULT_ENABLED.get(player_id, False),
            # Execute this statement as part of the module's documented control flow.
            "strategies": DEFAULT_STRATEGIES.get(player_id, {}).copy(),
            # Execute this statement as part of the module's documented control flow.
            "stakes": DEFAULT_STAKES.copy(),
            # Execute this statement as part of the module's documented control flow.
            "created_at": now,
            # Execute this statement as part of the module's documented control flow.
            "updated_at": now,
        })
    # Return the computed value to the caller.
    return {"schema_version": SCHEMA_VERSION, "bots": bots}


# Define the load_bots function used by this module.
def load_bots() -> dict:
    # Set state to the value needed for the next operation.
    state = read_json(BOTS_PATH, default_bots)
    # Branch when the following condition is true.
    if not isinstance(state, dict) or "bots" not in state:
        # Set state to the value needed for the next operation.
        state = default_bots()
    # Repair newly introduced fields if loading older files.
    # Iterate through the collection to process each item.
    for bot in state.get("bots", []):
        # Execute this statement as part of the module's documented control flow.
        bot.setdefault("bot_id", bot.get("player_id"))
        # Execute this statement as part of the module's documented control flow.
        bot.setdefault("player_id", bot.get("bot_id"))
        # Execute this statement as part of the module's documented control flow.
        bot.setdefault("display_name", _player_name(bot.get("player_id")))
        # Execute this statement as part of the module's documented control flow.
        bot.setdefault("enabled", True)
        # Execute this statement as part of the module's documented control flow.
        bot.setdefault("strategies", DEFAULT_STRATEGIES.get(bot.get("bot_id"), {}).copy())
        # Execute this statement as part of the module's documented control flow.
        bot.setdefault("stakes", DEFAULT_STAKES.copy())
    # Return the computed value to the caller.
    return state


# Define the save_bots function used by this module.
def save_bots(state: dict) -> None:
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    # Execute this statement as part of the module's documented control flow.
    write_json(BOTS_PATH, state)


# Define the list_bots function used by this module.
def list_bots() -> list[dict]:
    # Set bots to the value needed for the next operation.
    bots = load_bots().get("bots", [])
    # Set player_by_id to the value needed for the next operation.
    player_by_id = {p["player_id"]: p for p in players.list_players()}
    # Set out to the value needed for the next operation.
    out = []
    # Iterate through the collection to process each item.
    for b in bots:
        # Set row to the value needed for the next operation.
        row = dict(b)
        # Set p to the value needed for the next operation.
        p = player_by_id.get(row.get("player_id"), {})
        # Set row["balance"] to the value needed for the next operation.
        row["balance"] = p.get("balance")
        # Set row["player_type"] to the value needed for the next operation.
        row["player_type"] = p.get("type")
        # Execute this statement as part of the module's documented control flow.
        out.append(row)
    # Return the computed value to the caller.
    return out


# Define the get_bot function used by this module.
def get_bot(bot_id: str) -> dict:
    # Iterate through the collection to process each item.
    for b in list_bots():
        # Branch when the following condition is true.
        if b.get("bot_id") == bot_id:
            # Return the computed value to the caller.
            return b
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Bot {bot_id} was not found")


# Define the update_bot function used by this module.
def update_bot(bot_id: str, updates: dict) -> dict:
    # Set state to the value needed for the next operation.
    state = load_bots()
    # Iterate through the collection to process each item.
    for b in state.get("bots", []):
        # Branch when the following condition is true.
        if b.get("bot_id") == bot_id:
            # Branch when the following condition is true.
            if "enabled" in updates:
                # Set b["enabled"] to the value needed for the next operation.
                b["enabled"] = bool(updates["enabled"])
            # Branch when the following condition is true.
            if "strategies" in updates:
                # Set strategies to the value needed for the next operation.
                strategies = updates.get("strategies") or {}
                # Iterate through the collection to process each item.
                for game_id, strategy_id in strategies.items():
                    # Branch when the following condition is true.
                    if game_id not in CAPABILITIES or not CAPABILITIES[game_id].get("supports_bots"):
                        # Raise an error so invalid input or state is reported explicitly.
                        raise ValidationError(f"Bots are not supported for {game_id}")
                    # Set legal to the value needed for the next operation.
                    legal = {s["id"] for s in CAPABILITIES[game_id]["strategies"]}
                    # Branch when the following condition is true.
                    if strategy_id not in legal:
                        # Raise an error so invalid input or state is reported explicitly.
                        raise ValidationError(f"Strategy {strategy_id} is not legal for {game_id}")
                    # Set b.setdefault("strategies", {})[game_id] to the value needed for the next operation.
                    b.setdefault("strategies", {})[game_id] = strategy_id
            # Branch when the following condition is true.
            if "stakes" in updates:
                # Iterate through the collection to process each item.
                for game_id, amt in (updates.get("stakes") or {}).items():
                    # Set b.setdefault("stakes", {})[game_id] to the value needed for the next operation.
                    b.setdefault("stakes", {})[game_id] = max(1, round(float(amt), 2))
            # Set b["updated_at"] to the value needed for the next operation.
            b["updated_at"] = utc_now()
            # Execute this statement as part of the module's documented control flow.
            save_bots(state)
            # Return the computed value to the caller.
            return get_bot(bot_id)
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Bot {bot_id} was not found")


# Define the capabilities function used by this module.
def capabilities() -> dict:
    # Return the computed value to the caller.
    return CAPABILITIES


# Define the eligible_bots function used by this module.
def eligible_bots(game_id: str) -> list[dict]:
    # Set cap to the value needed for the next operation.
    cap = CAPABILITIES.get(game_id, {"supports_bots": False, "strategies": []})
    # Branch when the following condition is true.
    if not cap.get("supports_bots"):
        # Return the computed value to the caller.
        return []
    # Set legal to the value needed for the next operation.
    legal = {s["id"] for s in cap.get("strategies", [])}
    # Set out to the value needed for the next operation.
    out = []
    # Iterate through the collection to process each item.
    for b in list_bots():
        # Set strat to the value needed for the next operation.
        strat = b.get("strategies", {}).get(game_id)
        # Branch when the following condition is true.
        if b.get("enabled") and strat in legal:
            # Set row to the value needed for the next operation.
            row = dict(b)
            # Set row["game_id"] to the value needed for the next operation.
            row["game_id"] = game_id
            # Set row["strategy_id"] to the value needed for the next operation.
            row["strategy_id"] = strat
            # Set row["stake"] to the value needed for the next operation.
            row["stake"] = b.get("stakes", {}).get(game_id, DEFAULT_STAKES.get(game_id, 5))
            # Execute this statement as part of the module's documented control flow.
            out.append(row)
    # Return the computed value to the caller.
    return out
