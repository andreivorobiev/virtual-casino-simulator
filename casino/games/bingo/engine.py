# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import random
# Import required dependency so this module can use its public functions or constants.
from casino.core.ids import new_id
# Import required dependency so this module can use its public functions or constants.
from casino.core.clock import utc_now
# Import required dependency so this module can use its public functions or constants.
from casino.errors import ValidationError, ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID="bingo"
# Set COLUMNS to the value needed for the next operation.
COLUMNS = {"B": range(1,16), "I": range(16,31), "N": range(31,46), "G": range(46,61), "O": range(61,76)}
# Draw cards and balls from OS entropy so layouts and ball order cannot be predicted from seedable process state. (issue #420)
_rng = random.SystemRandom()
# Bound non-blackout sessions to 50 draws so a card race can genuinely end with no winner. (issue #405)
MAX_CALLS_DEFAULT = 50
# Give blackout a longer 60-draw budget because covering all 24 numbers needs a deeper ball stream. (issue #405)
MAX_CALLS_BLACKOUT = 60
# Record measured P(human wins) per pattern at the guaranteed four-card field from a seeded Monte Carlo (40k-300k trials). (issue #452)
MEASURED_WIN_PROBABILITY = {"line": 0.262, "four_corners": 0.142, "postage_stamp": 0.254, "blackout": 0.00136}
# Pay roughly 0.9 / P per pattern so every pattern carries a modest ~10% house edge instead of the prior player-positive returns. (issue #452)
PAYTABLE = {"line": 3.4, "four_corners": 6.3, "postage_stamp": 3.5, "blackout": 650}

# Define the call_cap_for function used by this module.
def call_cap_for(pattern):
    # Return the per-pattern ball budget stamped onto each session at start. (issue #405)
    return MAX_CALLS_BLACKOUT if pattern == "blackout" else MAX_CALLS_DEFAULT

# Define the ensure_call_cap function used by this module.
def ensure_call_cap(sess):
    # Read the persisted ball budget from the session.
    cap = sess.get("max_calls")
    # Fail-safe migrate persisted pre-cap sessions to the pattern default instead of unlimited free calls. (issue #405)
    if not isinstance(cap, int) or isinstance(cap, bool) or cap <= 0:
        # Derive the default budget from the session pattern.
        cap = call_cap_for(sess.get("pattern", "line"))
        # Stamp the migrated budget so the session state shape converges on the current schema.
        sess["max_calls"] = cap
    # Return the enforced budget to the caller.
    return cap

# Define the default_state function used by this module.
def default_state():
    # Return the computed value to the caller.
    return {"active_session": None, "last_sessions": []}

# Define the make_card function used by this module.
def make_card():
    # Set cols to the value needed for the next operation.
    cols = {}
    # Iterate through the collection to process each item.
    for col, rng in COLUMNS.items():
        # Sample the column from the CSPRNG so card layouts are unpredictable. (issue #420)
        cols[col] = _rng.sample(list(rng), 5)
    # Set cols["N"][2] to the value needed for the next operation.
    cols["N"][2] = "FREE"
    # Return the computed value to the caller.
    return cols

# Define the start_session function used by this module.
def start_session(state, player_id, amount, pattern="line", bot_players=None):
    # Branch when the following condition is true.
    if state.get("active_session") and state["active_session"].get("status") == "active":
        # Raise an error so invalid input or state is reported explicitly.
        raise ConflictError("A Bingo session is already active")
    # Branch when the following condition is true.
    if pattern not in ("line","four_corners","postage_stamp","blackout"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Unknown Bingo pattern")
    # Set cards to the value needed for the next operation.
    cards=[{"card_id": new_id("card"), "player_id": player_id, "amount": amount, "card": make_card(), "status":"active", "winner": False, "payout":0, "source":"manual"}]
    # Iterate through the collection to process each item.
    for bp in bot_players or []:
        # Execute this statement as part of the module's documented control flow.
        cards.append({"card_id": new_id("card"), "player_id": bp["player_id"], "amount": bp["amount"], "card": make_card(), "status":"active", "winner": False, "payout":0, "source": bp.get("source", "bot")})
    # Stamp the bounded ball budget at start so a session can no longer draw forever toward a guaranteed win. (issue #405)
    sess = {"session_id": new_id("bingo"), "player_id": player_id, "amount": amount, "pattern": pattern, "card": cards[0]["card"], "cards": cards, "called": [], "status":"active", "created_at": utc_now(), "winner": None, "winning_card_id": None, "payout": 0, "max_calls": call_cap_for(pattern)}
    # Set state["active_session"] to the value needed for the next operation.
    state["active_session"] = sess
    # Return the computed value to the caller.
    return sess

# Define the ball_label function used by this module.
def ball_label(n):
    # Set n to the value needed for the next operation.
    n=int(n)
    # Branch when the following condition is true.
    if 1 <= n <= 15: return f"B-{n}"
    # Branch when the following condition is true.
    if 16 <= n <= 30: return f"I-{n}"
    # Branch when the following condition is true.
    if 31 <= n <= 45: return f"N-{n}"
    # Branch when the following condition is true.
    if 46 <= n <= 60: return f"G-{n}"
    # Return the computed value to the caller.
    return f"O-{n}"

# Define the numbers_on_card function used by this module.
def numbers_on_card(card):
    # Set vals to the value needed for the next operation.
    vals=[]
    # Iterate through the collection to process each item.
    for c in "BINGO":
        # Iterate through the collection to process each item.
        for x in card[c]:
            # Branch when the following condition is true.
            if x != "FREE": vals.append(x)
    # Return the computed value to the caller.
    return vals

# Define the marked_grid_for_card function used by this module.
def marked_grid_for_card(card, called):
    # Set called to the value needed for the next operation.
    called = set(called or [])
    # Set grid to the value needed for the next operation.
    grid = []
    # Iterate through the collection to process each item.
    for r in range(5):
        # Set row to the value needed for the next operation.
        row=[]
        # Iterate through the collection to process each item.
        for c in "BINGO":
            # Set val to the value needed for the next operation.
            val = card[c][r]
            # Set row.append(True if val to the value needed for the next operation.
            row.append(True if val == "FREE" else val in called)
        # Execute this statement as part of the module's documented control flow.
        grid.append(row)
    # Return the computed value to the caller.
    return grid

# Define the marked_grid function used by this module.
def marked_grid(sess):
    # Return the computed value to the caller.
    return marked_grid_for_card(sess["card"], sess.get("called", []))

# Define the has_pattern_on_card function used by this module.
def has_pattern_on_card(card, called, pattern):
    # Set g to the value needed for the next operation.
    g = marked_grid_for_card(card, called); pat = pattern
    # Set winning to the value needed for the next operation.
    winning=[]
    # Branch when the following condition is true.
    if pat == "line":
        # Iterate through the collection to process each item.
        for r in range(5):
            # Branch when the following condition is true.
            if all(g[r][c] for c in range(5)): winning = [(r,c) for c in range(5)]; return True, winning
        # Iterate through the collection to process each item.
        for c in range(5):
            # Branch when the following condition is true.
            if all(g[r][c] for r in range(5)): winning = [(r,c) for r in range(5)]; return True, winning
        # Branch when the following condition is true.
        if all(g[i][i] for i in range(5)): return True, [(i,i) for i in range(5)]
        # Branch when the following condition is true.
        if all(g[i][4-i] for i in range(5)): return True, [(i,4-i) for i in range(5)]
        # Return the computed value to the caller.
        return False, []
    # Branch when the following condition is true.
    if pat == "four_corners":
        # Set coords to the value needed for the next operation.
        coords=[(0,0),(0,4),(4,0),(4,4)]; return all(g[r][c] for r,c in coords), coords
    # Branch when the following condition is true.
    if pat == "postage_stamp":
        # Iterate through the collection to process each item.
        for r,c in [(0,0),(0,3),(3,0),(3,3)]:
            # Set coords to the value needed for the next operation.
            coords=[(r+i,c+j) for i in range(2) for j in range(2)]
            # Branch when the following condition is true.
            if all(g[a][b] for a,b in coords): return True, coords
        # Return the computed value to the caller.
        return False, []
    # Branch when the following condition is true.
    if pat == "blackout":
        # Set coords to the value needed for the next operation.
        coords=[(r,c) for r in range(5) for c in range(5)]
        # Return the computed value to the caller.
        return all(all(row) for row in g), coords
    # Return the computed value to the caller.
    return False, []

# Define the has_pattern function used by this module.
def has_pattern(sess):
    # Set ok,_ to the value needed for the next operation.
    ok,_=has_pattern_on_card(sess["card"], sess.get("called",[]), sess.get("pattern","line")); return ok

# Define the payout_for function used by this module.
def payout_for(pattern, amount):
    # Return the house-edged total return for a winning card from the calibrated paytable. (issue #452)
    return round(float(amount) * PAYTABLE.get(pattern, PAYTABLE["line"]), 2)

# Define the finish_no_win function used by this module.
def finish_no_win(state, sess):
    # Mark the bounded session terminal as a loss with no winner and no payout. (issue #405)
    sess["status"] = "no_win"; sess["completed_at"] = utc_now(); sess["payout"] = 0
    # Iterate through the collection to process each item.
    for card in sess.get("cards", []):
        # Branch when the following condition is true.
        if card.get("status") == "active":
            # Mark the unfinished card lost so no later settlement path can ever credit it.
            card["status"] = "lost"
    # Archive the finished session exactly like the win path so the active slot is released.
    state.setdefault("last_sessions", []).append(sess)
    # Set state["last_sessions"] to the value needed for the next operation.
    state["last_sessions"] = state["last_sessions"][-50:]
    # Set state["active_session"] to the value needed for the next operation.
    state["active_session"] = None

# Define the call_next function used by this module.
def call_next(state):
    # Set sess to the value needed for the next operation.
    sess = state.get("active_session")
    # Branch when the following condition is true.
    if not sess or sess.get("status") != "active": raise ConflictError("No active Bingo session")
    # Enforce the per-session ball budget, fail-safe defaulting legacy sessions before any draw. (issue #405)
    cap = ensure_call_cap(sess)
    # Refuse another free draw when a legacy over-budget session already spent its cap; the caller must reset. (issue #405)
    if len(sess.get("called", [])) >= cap:
        # Fail closed instead of drawing beyond the bound.
        raise ConflictError("Bingo call limit reached")
    # Set remaining to the value needed for the next operation.
    remaining = [n for n in range(1,76) if n not in sess["called"]]
    # Branch when the following condition is true.
    if not remaining: raise ConflictError("No Bingo balls remaining")
    # Draw the ball from the CSPRNG so the stream cannot be predicted from process state. (issue #420)
    n = _rng.choice(remaining); sess["called"].append(n); sess["last_ball_label"] = ball_label(n)
    # Set winners to the value needed for the next operation.
    winners=[]
    # Iterate through the collection to process each item.
    for card in sess.get("cards", []):
        # Set ok, coords to the value needed for the next operation.
        ok, coords = has_pattern_on_card(card["card"], sess["called"], sess.get("pattern","line"))
        # Set card["marked_grid"] to the value needed for the next operation.
        card["marked_grid"] = marked_grid_for_card(card["card"], sess["called"])
        # Set card["winning_coords"] to the value needed for the next operation.
        card["winning_coords"] = coords if ok else []
        # Branch when the following condition is true.
        if ok and card.get("status") == "active":
            # A house spoiler card can end the human's session but is never paid, so no uncharged card ever collects. (issue #452)
            card_payout = payout_for(sess["pattern"], card["amount"]) if card.get("source") != "house" else 0
            # Set card["status"] to the value needed for the next operation.
            card["status"] = "won"; card["winner"] = True; card["payout"] = card_payout; winners.append(card)
    # Branch when the following condition is true.
    if winners:
        # Set win to the value needed for the next operation.
        win = winners[0]
        # Set sess["status"] to the value needed for the next operation.
        sess["status"] = "won"; sess["completed_at"] = utc_now(); sess["winner"] = win["player_id"]; sess["winning_card_id"] = win["card_id"]; sess["payout"] = win["payout"]; sess["winner_card"] = win
        # Execute this statement as part of the module's documented control flow.
        state.setdefault("last_sessions", []).append(sess)
        # Set state["last_sessions"] to the value needed for the next operation.
        state["last_sessions"] = state["last_sessions"][-50:]
        # Set state["active_session"] to the value needed for the next operation.
        state["active_session"] = None
    # End the session as a zero-payout loss once the ball budget is spent without a completed pattern. (issue #405)
    elif len(sess["called"]) >= cap:
        # Finalize and archive the bounded loss through the shared terminal helper.
        finish_no_win(state, sess)
    # Return the computed value to the caller.
    return sess, n

# Define the auto_play function used by this module.
def auto_play(state, max_calls=75):
    # Set calls to the value needed for the next operation.
    calls=[]; sess=None
    # Iterate through the collection to process each item.
    for _ in range(int(max_calls)):
        # Set sess,n to the value needed for the next operation.
        sess,n = call_next(state); calls.append(n)
        # Branch when the following condition is true.
        if sess.get("status") != "active": break
    # Return the computed value to the caller.
    return sess, calls
