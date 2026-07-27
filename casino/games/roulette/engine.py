# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import random
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.games.roulette.rules import wheel, catalog, find_bet, color_of, roulette_numbers, dozen, column
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError, ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "roulette"
# Set EVEN_MONEY_TYPES to the value needed for the next operation.
EVEN_MONEY_TYPES = {"red","black","odd","even","low","high"}
# Use operating-system-backed randomness for production wheel results. (issue #420)
_SYSTEM_RANDOM = random.SystemRandom()

# Define the default_state function used by this module.
def default_state() -> dict:
    # Return the computed value to the caller.
    return {
        # Execute this statement as part of the module's documented control flow.
        "open_round": {"round_id": new_id("rou"), "status": "open", "bets": []},
        # Execute this statement as part of the module's documented control flow.
        "last_results": [],
        # Execute this statement as part of the module's documented control flow.
        "mode": "double",
        # Execute this statement as part of the module's documented control flow.
        "zero_rule": "normal",
        # Execute this statement as part of the module's documented control flow.
        "last_bet_template": [],
        # Execute this statement as part of the module's documented control flow.
        "visual": {"current_pocket": None, "current_angle": 0}
    }

# Define the ensure_open_round function used by this module.
def ensure_open_round(state: dict) -> dict:
    # Set r to the value needed for the next operation.
    r = state.setdefault("open_round", {})
    # Branch when the following condition is true.
    if r.get("status") != "open":
        # Set state["open_round"] to the value needed for the next operation.
        state["open_round"] = {"round_id": new_id("rou"), "status": "open", "bets": []}
    # Execute this statement as part of the module's documented control flow.
    state["open_round"].setdefault("bets", [])
    # Return the computed value to the caller.
    return state["open_round"]

# Define the set_mode function used by this module.
def set_mode(state: dict, mode: str) -> dict:
    # Branch when the following condition is true.
    if mode not in ("single", "double"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Roulette mode must be single or double")
    # Branch when the following condition is true.
    if state.get("mode") != mode:
        # Set r to the value needed for the next operation.
        r = ensure_open_round(state)
        # Branch when the following condition is true.
        if r.get("bets"):
            # Raise an error so invalid input or state is reported explicitly.
            raise ConflictError("Clear or spin open roulette bets before changing wheel mode")
        # Set state["mode"] to the value needed for the next operation.
        state["mode"] = mode
        # Set state["open_round"] to the value needed for the next operation.
        state["open_round"] = {"round_id": new_id("rou"), "status": "open", "bets": []}
        # Set state["last_bet_template"] to the value needed for the next operation.
        state["last_bet_template"] = []
    # Return the computed value to the caller.
    return state

# Define the add_bet_to_state function used by this module.
def add_bet_to_state(state: dict, player_id: str, bet_type: str, amount: float, covered_numbers=None, label=None, source="manual") -> dict:
    # Set mode to the value needed for the next operation.
    mode = state.get("mode", "double")
    # Set bet to the value needed for the next operation.
    bet = find_bet(mode, bet_type, covered_numbers=covered_numbers)
    # Branch when the following condition is true.
    if not bet:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Illegal roulette bet", {"bet_type": bet_type, "covered_numbers": covered_numbers})
    # Set r to the value needed for the next operation.
    r = ensure_open_round(state)
    # Persist the resolved catalog entry's layout kind with each open bet so the frontend can route outside chips to the outside rail. (issue #222)
    item = {"bet_id": new_id("bet"), "player_id": player_id, "game":"roulette", "round_id": r["round_id"], "type": bet["type"], "label": label or bet["label"], "covered_numbers": bet["covered_numbers"], "amount": round(float(amount),2), "net_payout": bet["net_payout"], "created_at": utc_now(), "source": source, "layout_kind": bet.get("layout_kind")}
    # Execute this statement as part of the module's documented control flow.
    r["bets"].append(item)
    # Return the computed value to the caller.
    return item

# Define the remove_bet_from_state function used by this module.
def remove_bet_from_state(state: dict, bet_id: str, player_id: str) -> dict:
    # Set r to the value needed for the next operation.
    r = ensure_open_round(state)
    # Branch when the following condition is true.
    if r.get("status") != "open":
        # Raise an error so invalid input or state is reported explicitly.
        raise ConflictError("Cannot clear a bet after spin starts")
    # Iterate through the collection to process each item.
    for i, bet in enumerate(r["bets"]):
        # Branch when the following condition is true.
        if bet["bet_id"] == bet_id and bet["player_id"] == player_id:
            # Return the computed value to the caller.
            return r["bets"].pop(i)
    # Raise an error so invalid input or state is reported explicitly.
    raise ValidationError("Bet was not found")

# Define the save_template_from_round function used by this module.
def save_template_from_round(state: dict, player_id="human"):
    # Set r to the value needed for the next operation.
    r = ensure_open_round(state)
    # Set template to the value needed for the next operation.
    template=[]
    # Iterate through the collection to process each item.
    for b in r.get("bets", []):
        # Branch when the following condition is true.
        if b.get("player_id") == player_id and b.get("source") != "en_prison":
            # Execute this statement as part of the module's documented control flow.
            template.append({"type": b["type"], "covered_numbers": b["covered_numbers"], "label": b["label"], "amount": b["amount"]})
    # Branch when the following condition is true.
    if template:
        # Set state["last_bet_template"] to the value needed for the next operation.
        state["last_bet_template"] = template[-200:]
    # Return the computed value to the caller.
    return template

# Define the spin_state function used by this module.
def spin_state(state: dict, forced_result: str | None = None) -> dict:
    # Set r to the value needed for the next operation.
    r = ensure_open_round(state)
    # Branch when the following condition is true.
    if r.get("status") != "open":
        # Raise an error so invalid input or state is reported explicitly.
        raise ConflictError("Round is not open")
    # Set legal_results to the value needed for the next operation.
    legal_results = set(wheel(state.get("mode", "double")))
    # Draw the live pocket from the CSPRNG while preserving the deterministic forced-result test hook. (issue #420)
    result = str(forced_result) if forced_result is not None else _SYSTEM_RANDOM.choice(wheel(state.get("mode", "double")))
    # Branch when the following condition is true.
    if result not in legal_results:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Forced result is not legal for current wheel mode")
    # Set r["status"] to the value needed for the next operation.
    r["status"] = "settled"
    # Set r["result"] to the value needed for the next operation.
    r["result"] = result
    # Set r["result_color"] to the value needed for the next operation.
    r["result_color"] = color_of(result)
    # Set r["settled_at"] to the value needed for the next operation.
    r["settled_at"] = utc_now()
    # Set last to the value needed for the next operation.
    last = state.setdefault("last_results", [])
    # Execute this statement as part of the module's documented control flow.
    last.append({"round_id": r["round_id"], "result": result, "color": color_of(result), "timestamp": r["settled_at"]})
    # Set state["last_results"] to the value needed for the next operation.
    state["last_results"] = last[-1000:]
    # Set settled to the value needed for the next operation.
    settled = r
    # Set state["open_round"] to the value needed for the next operation.
    state["open_round"] = {"round_id": new_id("rou"), "status": "open", "bets": []}
    # Return the computed value to the caller.
    return settled

# Define the settle_bet function used by this module.
def settle_bet(bet: dict, result: str, zero_rule: str = "normal") -> dict:
    # Set amount to the value needed for the next operation.
    amount = float(bet["amount"])
    # Set win to the value needed for the next operation.
    win = result in bet["covered_numbers"]
    # Branch when the following condition is true.
    if win:
        # Set total_return to the value needed for the next operation.
        total_return = round(amount * (float(bet["net_payout"]) + 1), 2)
        # Return the computed value to the caller.
        return {"outcome":"win", "credit": total_return, "profit": total_return - amount, "carry": False}
    # Branch when the following condition is true.
    if result in ("0","00","000") and bet["type"] in EVEN_MONEY_TYPES:
        # Branch when the following condition is true.
        if zero_rule == "la_partage":
            # Return the computed value to the caller.
            return {"outcome":"half_loss", "credit": round(amount / 2, 2), "profit": -round(amount / 2, 2), "carry": False}
        # Branch when the following condition is true.
        if zero_rule == "en_prison":
            # Return the computed value to the caller.
            return {"outcome":"en_prison_carry", "credit": 0.0, "profit": 0, "carry": True}
    # Return the computed value to the caller.
    return {"outcome":"loss", "credit": 0.0, "profit": -amount, "carry": False}

# Define the carry_en_prison_bet function used by this module.
def carry_en_prison_bet(state: dict, bet: dict) -> dict:
    # Set item to the value needed for the next operation.
    item = add_bet_to_state(state, bet["player_id"], bet["type"], float(bet["amount"]), bet["covered_numbers"], bet.get("label"), source="en_prison")
    # Set item["prison_parent_bet_id"] to the value needed for the next operation.
    item["prison_parent_bet_id"] = bet.get("bet_id")
    # Return the computed value to the caller.
    return item

# Define the stats function used by this module.
def stats(state: dict) -> dict:
    # Set rolls to the value needed for the next operation.
    rolls = state.get("last_results", [])[-1000:]
    # Set freq to the value needed for the next operation.
    freq = {}
    # Set colors to the value needed for the next operation.
    colors = {"red":0,"black":0,"green":0}
    # Set odd_even to the value needed for the next operation.
    odd_even = {"odd":0,"even":0,"green":0}
    # Set low_high to the value needed for the next operation.
    low_high = {"low":0,"high":0,"green":0}
    # Set dozens to the value needed for the next operation.
    dozens = {"1st 12":0,"2nd 12":0,"3rd 12":0,"green":0}
    # Set columns to the value needed for the next operation.
    columns = {"Column 1":0,"Column 2":0,"Column 3":0,"green":0}
    # Set streaks to the value needed for the next operation.
    streaks=[]; cur=None; count=0
    # Iterate through the collection to process each item.
    for r in rolls:
        # Set n to the value needed for the next operation.
        n = r.get("result")
        # Set freq[n] to the value needed for the next operation.
        freq[n] = freq.get(n,0)+1
        # Set colr to the value needed for the next operation.
        colr = r.get("color","green")
        # Set colors[colr] to the value needed for the next operation.
        colors[colr] = colors.get(colr,0)+1
        # Branch when the following condition is true.
        if n in ("0","00","000"):
            # Set odd_even["green"] + to the value needed for the next operation.
            odd_even["green"] += 1; low_high["green"] += 1; dozens["green"] += 1; columns["green"] += 1
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Set i to the value needed for the next operation.
            i=int(n)
            # Set odd_even["odd" if i%2 else "even"] + to the value needed for the next operation.
            odd_even["odd" if i%2 else "even"] += 1
            # Set low_high["low" if i < to the value needed for the next operation.
            low_high["low" if i <= 18 else "high"] += 1
            # Set dz to the value needed for the next operation.
            dz = dozen(n); columns[f"Column {column(n)}"] += 1
            # Branch when the following condition is true.
            if dz: dozens[["1st 12","2nd 12","3rd 12"][dz-1]] += 1
        # Branch when the following condition is true.
        if colr == cur: count += 1
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Branch when the following condition is true.
            if cur is not None: streaks.append({"color":cur,"length":count})
            # Set cur to the value needed for the next operation.
            cur=colr; count=1
    # Branch when the following condition is true.
    if cur is not None: streaks.append({"color":cur,"length":count})
    # Set mode to the value needed for the next operation.
    mode = state.get("mode","double")
    # Set allnums to the value needed for the next operation.
    allnums = (["0","00"] if mode == "double" else ["0"]) + [str(i) for i in range(1,37)]
    # Set hot to the value needed for the next operation.
    hot = sorted([(n, freq.get(n,0)) for n in allnums], key=lambda kv: (-kv[1], kv[0]))[:10]
    # Set cold to the value needed for the next operation.
    cold = sorted([(n, freq.get(n,0)) for n in allnums], key=lambda kv: (kv[1], kv[0]))[:10]
    # Return the computed value to the caller.
    return {"roll_count": len(rolls), "frequency": {n: freq.get(n,0) for n in allnums}, "colors": colors, "odd_even": odd_even, "low_high": low_high, "dozens": dozens, "columns": columns, "hot": hot, "cold": cold, "streaks": sorted(streaks, key=lambda x: -x["length"])[:8], "latest": rolls[-60:]}
