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
# Set PAYTABLE to the value needed for the next operation.
PAYTABLE = {
  # Execute this statement as part of the module's documented control flow.
  1:{1:3}, 2:{2:12}, 3:{2:2,3:42}, 4:{2:1,3:5,4:100}, 5:{3:2,4:20,5:500},
  # Execute this statement as part of the module's documented control flow.
  6:{3:1,4:7,5:100,6:1600}, 7:{3:1,4:3,5:20,6:400,7:7000},
  # Execute this statement as part of the module's documented control flow.
  8:{4:2,5:10,6:100,7:2000,8:10000}, 9:{4:1,5:5,6:50,7:1000,8:5000,9:20000},
  # Execute this statement as part of the module's documented control flow.
  10:{5:2,6:20,7:200,8:2500,9:10000,10:50000},
  # Execute this statement as part of the module's documented control flow.
  11:{5:1,6:10,7:100,8:1000,9:5000,10:25000,11:100000},
  # Execute this statement as part of the module's documented control flow.
  12:{6:5,7:50,8:500,9:2500,10:10000,11:50000,12:150000},
  # Execute this statement as part of the module's documented control flow.
  13:{6:3,7:25,8:250,9:1000,10:7500,11:25000,12:100000,13:200000},
  # Execute this statement as part of the module's documented control flow.
  14:{7:10,8:100,9:500,10:3000,11:10000,12:50000,13:150000,14:250000},
  # Execute this statement as part of the module's documented control flow.
  15:{7:2,8:20,9:100,10:500,11:5000,12:20000,13:50000,14:100000,15:250000},
  # Execute this statement as part of the module's documented control flow.
  16:{8:10,9:50,10:250,11:1500,12:7500,13:25000,14:75000,15:200000,16:300000},
  # Execute this statement as part of the module's documented control flow.
  17:{8:5,9:25,10:200,11:1000,12:5000,13:20000,14:60000,15:150000,16:250000,17:400000},
  # Execute this statement as part of the module's documented control flow.
  18:{9:20,10:100,11:500,12:2500,13:10000,14:40000,15:100000,16:250000,17:500000,18:600000},
  # Execute this statement as part of the module's documented control flow.
  19:{9:10,10:50,11:250,12:1500,13:7500,14:25000,15:75000,16:200000,17:400000,18:650000,19:800000},
  # Execute this statement as part of the module's documented control flow.
  20:{10:5,11:50,12:250,13:1000,14:5000,15:25000,16:100000,17:250000,18:500000,19:750000,20:1000000},
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
