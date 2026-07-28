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
GAME_ID = "keno"
# Use operating-system-backed randomness for production number draws. (issue #420)
_SYSTEM_RANDOM = random.SystemRandom()
# Demo casino-style paytable. Keno paytables vary by house; rows 1-20 are explicit for validation.
# issue #456 economics rebalance: the previous table was PLAYER-POSITIVE for picks 9-14 (exact
# hypergeometric RTP on a 20-of-80 draw ran 106%-143%) while picks 1-6 and 15-20 paid far under a
# fair keno return. Every row is uniformly rescaled to a house-side ~91% RTP and clustered inside
# [88%,94%] for a modest, consistent ~9% house edge. Prize tiers keep the original shape (more hits
# always pays more; the full-catch jackpot is retained but sized so the row total stays house-side);
# only the lowest consolation tier is fine-tuned to hit the target. old->new RTP noted per row.
# Verified exactly (deterministic hypergeometric) and by seeded engine.draw()/settlement simulation.
# Multipliers may be fractional (settlement rounds payout to 2dp); the web client formats to 2dp. (issue #456)
# Set PAYTABLE to the value needed for the next operation.
PAYTABLE = {
  1: {1: 3.6},  # #456 pick  1:  75.00% -> 90.00% RTP (raised into band)
  2: {2: 15},  # #456 pick  2:  72.15% -> 90.19% RTP (raised into band)
  3: {2: 2.1, 3: 45},  # #456 pick  3:  86.03% -> 91.58% RTP (raised into band)
  4: {2: 1.3, 3: 6, 4: 120},  # #456 pick  4:  73.52% -> 90.35% RTP (raised into band)
  5: {3: 2.5, 4: 25, 5: 620},  # #456 pick  5:  73.22% -> 91.20% RTP (raised into band; 5-catch 500 -> 620)
  6: {3: 0.9, 4: 8, 5: 110, 6: 1700},  # #456 pick  6:  84.55% -> 90.49% RTP (raised into band)
  7: {3: 0.9, 4: 3, 5: 19, 6: 380, 7: 6600},  # #456 pick  7:  96.80% -> 91.74% RTP (trimmed)
  8: {4: 1.9, 5: 10, 6: 95, 7: 1900, 8: 9600},  # #456 pick  8:  94.71% -> 90.93% RTP (trimmed)
  9: {4: 0.6, 5: 3.5, 6: 35, 7: 680, 8: 3400, 9: 13500},  # #456 pick  9: 133.22% -> 90.57% RTP (PLAYER-POSITIVE fixed)
  10: {5: 1.9, 6: 17, 7: 170, 8: 2100, 9: 8600, 10: 43000},  # #456 pick 10: 106.00% -> 90.86% RTP (PLAYER-POSITIVE fixed)
  11: {5: 0.9, 6: 7, 7: 75, 8: 750, 9: 3700, 10: 18500, 11: 74500},  # #456 pick 11: 121.82% -> 91.30% RTP (PLAYER-POSITIVE fixed)
  12: {6: 3.5, 7: 35, 8: 340, 9: 1700, 10: 6900, 11: 34500, 12: 103000},  # #456 pick 12: 132.37% -> 91.10% RTP (PLAYER-POSITIVE fixed)
  13: {6: 1.8, 7: 16, 8: 160, 9: 640, 10: 4800, 11: 16000, 12: 63500, 13: 127000},  # #456 pick 13: 143.26% -> 91.11% RTP (PLAYER-POSITIVE fixed)
  14: {7: 7.5, 8: 80, 9: 400, 10: 2400, 11: 7900, 12: 39500, 13: 119000, 14: 199000},  # #456 pick 14: 114.60% -> 90.64% RTP (PLAYER-POSITIVE fixed)
  15: {7: 3, 8: 40, 9: 190, 10: 940, 11: 9400, 12: 37500, 13: 94000, 14: 188000, 15: 469000},  # #456 pick 15:  48.49% -> 90.90% RTP (raised into band)
  16: {8: 24, 9: 110, 10: 570, 11: 3400, 12: 17000, 13: 57500, 14: 172000, 15: 459000, 16: 689000},  # #456 pick 16:  39.64% -> 90.77% RTP (raised into band)
  17: {8: 9.5, 9: 50, 10: 390, 11: 2000, 12: 9800, 13: 39500, 14: 118000, 15: 295000, 16: 491000, 17: 786000},  # #456 pick 17:  46.32% -> 90.87% RTP (raised into band)
  18: {9: 41, 10: 220, 11: 1100, 12: 5400, 13: 21500, 14: 86000, 15: 215000, 16: 538000, 17: 1076000, 18: 1291000},  # #456 pick 18:  42.28% -> 90.67% RTP (raised into band)
  19: {9: 22, 10: 110, 11: 550, 12: 3300, 13: 16500, 14: 55000, 15: 165000, 16: 441000, 17: 882000, 18: 1433000, 19: 1763000},  # #456 pick 19:  41.29% -> 90.84% RTP (raised into band)
  20: {10: 52, 11: 510, 12: 2500, 13: 10000, 14: 51000, 15: 254000, 16: 1017000, 17: 2542000, 18: 5084000, 19: 7626000, 20: 10169000},  # #456 pick 20:   8.95% -> 91.05% RTP (raised into band)
}

# Define the default_state function used by this module.
def default_state():
    # Return the computed value to the caller.
    return {"open_tickets": [], "last_draws": []}

# Define the normalize_spots function used by this module.
def normalize_spots(spots):
    # Set nums to the value needed for the next operation.
    nums = sorted({int(x) for x in spots})
    # Branch when the following condition is true.
    if not 1 <= len(nums) <= 20: raise ValidationError("Pick 1 to 20 Keno spots")
    # Branch when the following condition is true.
    if nums[0] < 1 or nums[-1] > 80: raise ValidationError("Keno numbers must be 1 through 80")
    # Return the computed value to the caller.
    return nums

# Define the add_ticket function used by this module.
def add_ticket(state, player_id, spots, amount, source="manual"):
    # Set nums to the value needed for the next operation.
    nums = normalize_spots(spots)
    # Set ticket to the value needed for the next operation.
    ticket = {"ticket_id": new_id("keno"), "player_id": player_id, "spots": nums, "amount": amount, "source": source, "created_at": utc_now()}
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("open_tickets", []).append(ticket)
    # Return the computed value to the caller.
    return ticket

# Define the remove_ticket function used by this module.
def remove_ticket(state, ticket_id, player_id):
    # Iterate through the collection to process each item.
    for i,t in enumerate(state.setdefault("open_tickets", [])):
        # Branch when the following condition is true.
        if t["ticket_id"] == ticket_id and t["player_id"] == player_id:
            # Return the computed value to the caller.
            return state["open_tickets"].pop(i)
    # Raise an error so invalid input or state is reported explicitly.
    raise ValidationError("Keno ticket was not found")

# Define the draw function used by this module.
def draw(state):
    # Branch when the following condition is true.
    if not state.get("open_tickets"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Buy a Keno ticket first")
    # Draw twenty unique balls from the CSPRNG so results cannot be predicted from seeded Mersenne Twister state. (issue #420)
    drawn = sorted(_SYSTEM_RANDOM.sample(range(1,81), 20))
    # Set rid to the value needed for the next operation.
    rid = new_id("kendraw")
    # Set results to the value needed for the next operation.
    results=[]
    # Iterate through the collection to process each item.
    for t in state["open_tickets"]:
        # Set catches to the value needed for the next operation.
        catches = sorted(set(t["spots"]) & set(drawn))
        # Set picks to the value needed for the next operation.
        picks = len(t["spots"]); caught = len(catches)
        # Set row to the value needed for the next operation.
        row = PAYTABLE[picks]
        # Set mult to the value needed for the next operation.
        mult = row.get(caught, 0)
        # Set payout to the value needed for the next operation.
        payout = round(float(t["amount"])*mult, 2)
        # Execute this statement as part of the module's documented control flow.
        results.append({"ticket": t, "catches": catches, "catch_count": caught, "multiplier": mult, "payout": payout})
    # Set draw to the value needed for the next operation.
    draw = {"round_id": rid, "timestamp": utc_now(), "drawn": drawn, "results": results}
    # Set state["open_tickets"] to the value needed for the next operation.
    state["open_tickets"] = []
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("last_draws", []).append(draw)
    # Set state["last_draws"] to the value needed for the next operation.
    state["last_draws"] = state["last_draws"][-100:]
    # Return the computed value to the caller.
    return draw
