# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Durable bot profiles and player-account associations.
from __future__ import annotations
from casino.config import DATA_DIR, SCHEMA_VERSION
from casino.core.clock import utc_now
from casino.core.state_store import read_json, write_json
from casino.core import players
from casino.errors import ValidationError, NotFoundError

# Set BOTS_PATH to the value needed for the next operation.
BOTS_PATH = DATA_DIR / "bots.json"

# Set CAPABILITIES to the value needed for the next operation.
CAPABILITIES = {
    "roulette": {
        "supports_bots": True,
        "strategies": [
            {"id":"roulette_random_outside", "label":"Random Outside"},
            {"id":"roulette_red_black", "label":"Red/Black"},
            {"id":"roulette_random_number", "label":"Random Number"},
            {"id":"roulette_split_corner", "label":"Split/Corner"},
            {"id":"roulette_dozen_column", "label":"Dozens/Columns"},
            {"id":"roulette_racetrack", "label":"Racetrack/Snake"},
        ],
    },
    "baccarat": {
        "supports_bots": True,
        "strategies": [
            {"id":"baccarat_banker", "label":"Banker"},
            {"id":"baccarat_player", "label":"Player"},
            {"id":"baccarat_tie", "label":"Tie Chaser"},
            {"id":"baccarat_random", "label":"Random"},
            {"id":"baccarat_pattern", "label":"Pattern Follower"},
        ],
    },
    "keno": {
        "supports_bots": True,
        "strategies": [
            {"id":"keno_quick_pick_3", "label":"Quick Pick 3"},
            {"id":"keno_quick_pick_5", "label":"Quick Pick 5"},
            {"id":"keno_quick_pick_10", "label":"Quick Pick 10"},
            {"id":"keno_quick_pick_20", "label":"Quick Pick 20"},
        ],
    },
    "bingo": {
        "supports_bots": True,
        "strategies": [
            {"id":"bingo_standard_card", "label":"Standard Card"},
        ],
    },
    "slots": {"supports_bots": False, "strategies": []},
    "blackjack": {"supports_bots": False, "strategies": []},
}

# Set DEFAULT_STRATEGIES to the value needed for the next operation.
DEFAULT_STRATEGIES = {
    "bot_1": {"roulette":"roulette_random_outside", "baccarat":"baccarat_banker", "keno":"keno_quick_pick_5", "bingo":"bingo_standard_card"},
    "bot_2": {"roulette":"roulette_red_black", "baccarat":"baccarat_random", "keno":"keno_quick_pick_10", "bingo":"bingo_standard_card"},
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
        return players.get_player(player_id).get("display_name", player_id)
    # Handle the expected failure path for the protected logic.
    except Exception:
        return player_id


# Define the default_bots function used by this module.
def default_bots() -> dict:
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set bots to the value needed for the next operation.
    bots = []
    for player_id in ["bot_1", "bot_2", "bot_3"]:
        bots.append({
            "bot_id": player_id,
            "player_id": player_id,
            "display_name": _player_name(player_id),
            "enabled": DEFAULT_ENABLED.get(player_id, False),
            "strategies": DEFAULT_STRATEGIES.get(player_id, {}).copy(),
            "stakes": DEFAULT_STAKES.copy(),
            "created_at": now,
            "updated_at": now,
        })
    return {"schema_version": SCHEMA_VERSION, "bots": bots}


# Define the load_bots function used by this module.
def load_bots() -> dict:
    # Set state to the value needed for the next operation.
    state = read_json(BOTS_PATH, default_bots)
    if not isinstance(state, dict) or "bots" not in state:
        # Set state to the value needed for the next operation.
        state = default_bots()
    # Repair newly introduced fields if loading older files.
    for bot in state.get("bots", []):
        bot.setdefault("bot_id", bot.get("player_id"))
        bot.setdefault("player_id", bot.get("bot_id"))
        bot.setdefault("display_name", _player_name(bot.get("player_id")))
        bot.setdefault("enabled", True)
        bot.setdefault("strategies", DEFAULT_STRATEGIES.get(bot.get("bot_id"), {}).copy())
        bot.setdefault("stakes", DEFAULT_STAKES.copy())
    return state


# Define the save_bots function used by this module.
def save_bots(state: dict) -> None:
    # Set state["schema_version"] to the value needed for the next operation.
    state["schema_version"] = SCHEMA_VERSION
    write_json(BOTS_PATH, state)


# Define the list_bots function used by this module.
def list_bots() -> list[dict]:
    # Set bots to the value needed for the next operation.
    bots = load_bots().get("bots", [])
    # Set player_by_id to the value needed for the next operation.
    player_by_id = {p["player_id"]: p for p in players.list_players()}
    # Set out to the value needed for the next operation.
    out = []
    for b in bots:
        # Set row to the value needed for the next operation.
        row = dict(b)
        # Set p to the value needed for the next operation.
        p = player_by_id.get(row.get("player_id"), {})
        # Set row["balance"] to the value needed for the next operation.
        row["balance"] = p.get("balance")
        # Set row["player_type"] to the value needed for the next operation.
        row["player_type"] = p.get("type")
        out.append(row)
    return out


# Define the get_bot function used by this module.
def get_bot(bot_id: str) -> dict:
    for b in list_bots():
        if b.get("bot_id") == bot_id:
            return b
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Bot {bot_id} was not found")


# Define the update_bot function used by this module.
def update_bot(bot_id: str, updates: dict) -> dict:
    # Set state to the value needed for the next operation.
    state = load_bots()
    for b in state.get("bots", []):
        if b.get("bot_id") == bot_id:
            if "enabled" in updates:
                # Set b["enabled"] to the value needed for the next operation.
                b["enabled"] = bool(updates["enabled"])
            if "strategies" in updates:
                # Set strategies to the value needed for the next operation.
                strategies = updates.get("strategies") or {}
                for game_id, strategy_id in strategies.items():
                    if game_id not in CAPABILITIES or not CAPABILITIES[game_id].get("supports_bots"):
                        # Reject unsupported games without reflecting the caller-supplied identifier into the public envelope. (issue #418)
                        raise ValidationError("Bots are not supported for the requested game")
                    # Set legal to the value needed for the next operation.
                    legal = {s["id"] for s in CAPABILITIES[game_id]["strategies"]}
                    if strategy_id not in legal:
                        # Raise an error so invalid input or state is reported explicitly.
                        raise ValidationError(f"Strategy {strategy_id} is not legal for {game_id}")
                    # Set b.setdefault("strategies", {})[game_id] to the value needed for the next operation.
                    b.setdefault("strategies", {})[game_id] = strategy_id
            if "stakes" in updates:
                for game_id, amt in (updates.get("stakes") or {}).items():
                    # Set b.setdefault("stakes", {})[game_id] to the value needed for the next operation.
                    b.setdefault("stakes", {})[game_id] = max(1, round(float(amt), 2))
            # Set b["updated_at"] to the value needed for the next operation.
            b["updated_at"] = utc_now()
            save_bots(state)
            return get_bot(bot_id)
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Bot {bot_id} was not found")


# Define the capabilities function used by this module.
def capabilities() -> dict:
    return CAPABILITIES


# Define the eligible_bots function used by this module.
def eligible_bots(game_id: str) -> list[dict]:
    # Set cap to the value needed for the next operation.
    cap = CAPABILITIES.get(game_id, {"supports_bots": False, "strategies": []})
    if not cap.get("supports_bots"):
        return []
    # Set legal to the value needed for the next operation.
    legal = {s["id"] for s in cap.get("strategies", [])}
    # Set out to the value needed for the next operation.
    out = []
    for b in list_bots():
        # Set strat to the value needed for the next operation.
        strat = b.get("strategies", {}).get(game_id)
        if b.get("enabled") and strat in legal:
            # Set row to the value needed for the next operation.
            row = dict(b)
            # Set row["game_id"] to the value needed for the next operation.
            row["game_id"] = game_id
            # Set row["strategy_id"] to the value needed for the next operation.
            row["strategy_id"] = strat
            # Set row["stake"] to the value needed for the next operation.
            row["stake"] = b.get("stakes", {}).get(game_id, DEFAULT_STAKES.get(game_id, 5))
            out.append(row)
    return out
