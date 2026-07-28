# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import random
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "slots"
# Pick reel stops from OS entropy so spin outcomes cannot be predicted from seedable process state. (issue #420)
_rng = random.SystemRandom()
# Set SYMBOLS to the value needed for the next operation.
SYMBOLS = ["CHERRY", "LEMON", "BAR", "BELL", "SEVEN", "WILD", "SCATTER"]
# Set REELS to the value needed for the next operation.
REELS = [
    # Explain this executable/data line so future Codex changes preserve intent.
    ["CHERRY","LEMON","BAR","CHERRY","BELL","LEMON","WILD","BAR","CHERRY","SEVEN","LEMON","SCATTER","BELL","BAR"],
    # Explain this executable/data line so future Codex changes preserve intent.
    ["LEMON","CHERRY","BAR","BELL","LEMON","WILD","CHERRY","BAR","SEVEN","LEMON","BELL","SCATTER","BAR","CHERRY"],
    # Explain this executable/data line so future Codex changes preserve intent.
    ["BAR","LEMON","CHERRY","BELL","WILD","LEMON","BAR","CHERRY","SEVEN","SCATTER","BELL","LEMON","BAR","CHERRY"],
    # Explain this executable/data line so future Codex changes preserve intent.
    ["CHERRY","BAR","LEMON","BELL","CHERRY","WILD","BAR","LEMON","SEVEN","BELL","SCATTER","CHERRY","BAR","LEMON"],
    # Explain this executable/data line so future Codex changes preserve intent.
    ["LEMON","CHERRY","BAR","WILD","BELL","LEMON","CHERRY","BAR","SEVEN","SCATTER","BELL","LEMON","BAR","CHERRY"],
]
# Set PAYLINES to the value needed for the next operation.
PAYLINES = {
    # Execute this statement as part of the module's documented control flow.
    1: [[1,1,1,1,1]],
    # Execute this statement as part of the module's documented control flow.
    3: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2]],
    # Execute this statement as part of the module's documented control flow.
    5: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2],[0,1,2,1,0],[2,1,0,1,2]],
    # Execute this statement as part of the module's documented control flow.
    9: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2],[0,1,2,1,0],[2,1,0,1,2],[0,0,1,2,2],[2,2,1,0,0],[1,0,1,2,1],[1,2,1,0,1]],
    # Execute this statement as part of the module's documented control flow.
    20: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2],[0,1,2,1,0],[2,1,0,1,2],[0,0,1,2,2],[2,2,1,0,0],[1,0,1,2,1],[1,2,1,0,1],[0,1,1,1,0],[2,1,1,1,2],[1,0,0,0,1],[1,2,2,2,1],[0,1,0,1,0],[2,1,2,1,2],[0,2,0,2,0],[2,0,2,0,2],[1,0,2,0,1],[1,2,0,2,1],[0,2,1,0,2]],
}
# Line-pay multipliers per symbol/run-length, cut ~62% from the pre-rebalance table (~x0.375) so the line-pay component alone returns ~89% and total measured RTP lands ~92%. (economics rebalance, issue #456)
PAYTABLE = {
    # CHERRY low-pay run values rebalanced down from {3:5,4:20,5:80}. (economics rebalance, issue #456)
    "CHERRY": {3: 2, 4: 8, 5: 30},
    # LEMON low-pay run values rebalanced down from {3:4,4:15,5:60}. (economics rebalance, issue #456)
    "LEMON": {3: 2, 4: 6, 5: 23},
    # BAR mid-pay run values rebalanced down from {3:8,4:35,5:150}. (economics rebalance, issue #456)
    "BAR": {3: 3, 4: 13, 5: 56},
    # BELL mid-pay run values rebalanced down from {3:12,4:60,5:250}. (economics rebalance, issue #456)
    "BELL": {3: 4, 4: 23, 5: 94},
    # SEVEN top line-pay run values rebalanced down from {3:30,4:300,5:1200}. (economics rebalance, issue #456)
    "SEVEN": {3: 11, 4: 112, 5: 450},
    # WILD substitute-and-pay run values rebalanced down from {3:25,4:200,5:800}; 5-of-a-kind stays >0 so the all-Wild payline acceptance test keeps 20 wins. (economics rebalance, issue #456)
    "WILD": {3: 9, 4: 75, 5: 300},
}
# Scatter pays per visible-scatter count, cut hard from {3:5,4:20,5:100}: 3 scatters now arm free spins with no coin pay, and 4/5 pay only a token amount, because these flat (line_bet) pays otherwise inflate the 1-line RTP above the band; {4:1,5:5} keeps all line counts inside [0.90,0.94]. (economics rebalance, issue #456)
SCATTER_PAYS = {4: 1, 5: 5}
# Minimum visible scatters that both pay and arm free spins; held at 3 so the feature still triggers ~6.9%/spin. (economics rebalance, issue #456)
FREE_SPIN_SCATTER_THRESHOLD = 3
# Free spins granted per trigger, cut from 8 to 4 so the retrigger cascade (award*P(retrigger)<1) stays a modest bonus instead of ~55% of all spins. (economics rebalance, issue #456)
FREE_SPINS_AWARDED = 4
# Progressive reset/seed lowered from 1000 to 200 so the flat jackpot adds only a few RTP points rather than ~13%. (economics rebalance, issue #456)
PROGRESSIVE_SEED = 200.0
# Fraction of each paid wager fed into the progressive pool, unchanged from the historical 1%. (economics rebalance, issue #456)
PROGRESSIVE_RATE = 0.01

# Define the default_state function used by this module.
def default_state():
    # Seed a fresh player's progressive from PROGRESSIVE_SEED so new and post-jackpot pools agree after the rebalance. (economics rebalance, issue #456)
    return {"last_spins": [], "progressive": PROGRESSIVE_SEED, "free_spins": 0}

# Define the render_grid function used by this module.
def render_grid(stops):
    # Set grid to the value needed for the next operation.
    grid = [[], [], []]
    # Iterate through the collection to process each item.
    for reel, stop in zip(REELS, stops):
        # Set L to the value needed for the next operation.
        L = len(reel)
        # Set symbols to the value needed for the next operation.
        symbols = [reel[(stop-1)%L], reel[stop%L], reel[(stop+1)%L]]
        # Iterate through the collection to process each item.
        for r in range(3):
            # Execute this statement as part of the module's documented control flow.
            grid[r].append(symbols[r])
    # Return the computed value to the caller.
    return grid

# Define the evaluate function used by this module.
def evaluate(grid, active_lines, line_bet):
    # Branch when the following condition is true.
    if active_lines not in PAYLINES:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("active_lines must be one of 1,3,5,9,20")
    # Set wins to the value needed for the next operation.
    wins=[]; total=0.0
    # Iterate through the collection to process each item.
    for idx,line in enumerate(PAYLINES[active_lines]):
        # Set seq to the value needed for the next operation.
        seq = [grid[row][col] for col,row in enumerate(line)]
        # Set base to the value needed for the next operation.
        base = next((s for s in seq if s not in ("WILD", "SCATTER")), seq[0])
        # Set count to the value needed for the next operation.
        count=0
        # Iterate through the collection to process each item.
        for s in seq:
            # Branch when the following condition is true.
            if s == base or s == "WILD": count += 1
            # Handle the fallback branch when prior conditions did not match.
            else: break
        # Set mult to the value needed for the next operation.
        mult = PAYTABLE.get(base, {}).get(count, 0)
        # Branch when the following condition is true.
        if mult:
            # Set payout to the value needed for the next operation.
            payout = round(mult*line_bet,2); total += payout
            # Execute this statement as part of the module's documented control flow.
            wins.append({"line_index": idx, "line": line, "sequence": seq, "symbol": base, "count": count, "multiplier": mult, "payout": payout})
    # Set scatter_count to the value needed for the next operation.
    scatter_count = sum(1 for row in grid for s in row if s == "SCATTER")
    # Award free spins from the FREE_SPINS_AWARDED constant when the scatter count clears the threshold. (economics rebalance, issue #456)
    free_spins_awarded = FREE_SPINS_AWARDED if scatter_count >= FREE_SPIN_SCATTER_THRESHOLD else 0
    # Pay scatters from the rebalanced SCATTER_PAYS table (flat multiples of line_bet). (economics rebalance, issue #456)
    scatter_payout = round(line_bet * (SCATTER_PAYS.get(scatter_count, 0)),2)
    # Branch when the following condition is true.
    if scatter_payout:
        # Set total + to the value needed for the next operation.
        total += scatter_payout
        # Execute this statement as part of the module's documented control flow.
        wins.append({"scatter_count": scatter_count, "symbol":"SCATTER", "payout": scatter_payout, "kind":"scatter"})
    # Return the computed value to the caller.
    return {"wins": wins, "payout": round(total,2), "scatter_count": scatter_count, "free_spins_awarded": free_spins_awarded}

# Define the spin function used by this module.
def spin(state, active_lines=5, line_bet=1.0):
    # Set active_lines to the value needed for the next operation.
    active_lines = int(active_lines)
    # Branch when the following condition is true.
    if active_lines not in PAYLINES: raise ValidationError("active_lines must be one of 1,3,5,9,20")
    # Set line_bet to the value needed for the next operation.
    line_bet = round(float(line_bet),2)
    # Branch when the following condition is true.
    if line_bet <= 0: raise ValidationError("line_bet must be positive")
    # Set free to the value needed for the next operation.
    free = int(state.get("free_spins",0)) > 0
    # Set cost to the value needed for the next operation.
    cost = 0.0 if free else round(active_lines * line_bet, 2)
    # Branch when the following condition is true.
    if free: state["free_spins"] = int(state.get("free_spins",0)) - 1
    # Draw each reel stop from the CSPRNG instance instead of the seedable module generator. (issue #420)
    stops = [_rng.randrange(len(r)) for r in REELS]
    # Set grid to the value needed for the next operation.
    grid = render_grid(stops)
    # Set result to the value needed for the next operation.
    result = evaluate(grid, active_lines, line_bet)
    # Branch when the following condition is true.
    if result["free_spins_awarded"]:
        # Set state["free_spins"] to the value needed for the next operation.
        state["free_spins"] = int(state.get("free_spins",0)) + result["free_spins_awarded"]
    # Grow the progressive pool by PROGRESSIVE_RATE of the paid wager (free spins contribute nothing since cost is 0). (economics rebalance, issue #456)
    state["progressive"] = round(float(state.get("progressive",PROGRESSIVE_SEED)) + cost*PROGRESSIVE_RATE, 2)
    # Branch when the following condition is true.
    if any(w.get("symbol") == "SEVEN" and w.get("count") == 5 for w in result["wins"]):
        # Set result["payout"] + to the value needed for the next operation.
        result["payout"] += state["progressive"]
        # Set result["progressive_hit"] to the value needed for the next operation.
        result["progressive_hit"] = state["progressive"]
        # Reset the pool to the rebalanced PROGRESSIVE_SEED after a jackpot instead of the old 1000. (economics rebalance, issue #456)
        state["progressive"] = PROGRESSIVE_SEED
    # Set round_id to the value needed for the next operation.
    round_id = new_id("slot")
    # Set spin_data to the value needed for the next operation.
    spin_data = {"round_id": round_id, "timestamp": utc_now(), "stops": stops, "grid": grid, "active_lines": active_lines, "line_bet": line_bet, "cost": cost, **result, "free_spin": free, "free_spins_remaining": state.get("free_spins",0), "progressive": state.get("progressive")}
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("last_spins", []).append(spin_data)
    # Set state["last_spins"] to the value needed for the next operation.
    state["last_spins"] = state["last_spins"][-100:]
    # Return the computed value to the caller.
    return spin_data
