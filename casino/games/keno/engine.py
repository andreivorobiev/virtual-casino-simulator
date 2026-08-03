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
# Publish one server-authoritative house-side paytable for every legal spot count. (KENO-027)
# Exact hypergeometric proof targets ideal unit-stake returns near ninety percent, while pick one
# uses the owner-approved lower exception needed to keep the frozen one-cent ticket house-side
# after the existing ``round(float(amount) * multiplier, 2)`` payout law. (issue #472)
# Every listed positive award is at least stake-neutral because the API and UI label it a win.
# Set PAYTABLE to the value needed for the next operation.
PAYTABLE = {
  # Keep the one-spot award below 3.50x so a one-cent win returns three cents, not four.
  1: {1: 3.49},
  # Price the two-spot jackpot at an exact house-side fifteen times the ticket.
  2: {2: 15},
  # Preserve strictly increasing awards while centering the three-spot ideal return near ninety percent.
  3: {2: 2.1, 3: 45},
  # Preserve a stake-positive first award and an increasing four-spot jackpot.
  4: {2: 1.3, 3: 6, 4: 120},
  # Preserve the five-spot shape while raising its formerly underpaying ideal return into band.
  5: {3: 2.5, 4: 25, 5: 620},
  # Use a stake-neutral first award instead of a positive award below one times the ticket.
  6: {3: 1, 4: 8, 5: 110, 6: 1700},
  # Keep every listed seven-spot award stake-neutral or better and strictly increasing.
  7: {3: 1, 4: 3, 5: 19, 6: 380, 7: 6600},
  # Retain the eight-spot award ladder while moving its ideal return into the approved band.
  8: {4: 1.9, 5: 10, 6: 95, 7: 1900, 8: 9600},
  # Rebalance the formerly player-positive nine-spot row after replacing its sub-stake first award.
  9: {4: 1, 5: 2.2, 6: 35, 7: 680, 8: 3400, 9: 13500},
  # Rebalance the formerly player-positive ten-spot row without changing its award ordering.
  10: {5: 1.9, 6: 17, 7: 170, 8: 2100, 9: 8600, 10: 43000},
  # Use a stake-neutral first award while keeping the eleven-spot jackpot house-side.
  11: {5: 1, 6: 7, 7: 75, 8: 750, 9: 3700, 10: 18500, 11: 74500},
  # Rebalance the formerly player-positive twelve-spot row into the approved ideal-return band.
  12: {6: 3.5, 7: 35, 8: 340, 9: 1700, 10: 6900, 11: 34500, 12: 103000},
  # Rebalance the formerly player-positive thirteen-spot row while retaining its jackpot shape.
  13: {6: 1.8, 7: 16, 8: 160, 9: 640, 10: 4800, 11: 16000, 12: 63500, 13: 127000},
  # Rebalance the formerly player-positive fourteen-spot row into the approved ideal-return band.
  14: {7: 7.5, 8: 80, 9: 400, 10: 2400, 11: 7900, 12: 39500, 13: 119000, 14: 199000},
  # Raise the formerly underpaying fifteen-spot row while preserving strictly increasing awards.
  15: {7: 3, 8: 40, 9: 190, 10: 940, 11: 9400, 12: 37500, 13: 94000, 14: 188000, 15: 469000},
  # Raise the formerly underpaying sixteen-spot row while preserving strictly increasing awards.
  16: {8: 24, 9: 110, 10: 570, 11: 3400, 12: 17000, 13: 57500, 14: 172000, 15: 459000, 16: 689000},
  # Raise the formerly underpaying seventeen-spot row while preserving strictly increasing awards.
  17: {8: 9.5, 9: 50, 10: 390, 11: 2000, 12: 9800, 13: 39500, 14: 118000, 15: 295000, 16: 491000, 17: 786000},
  # Raise the formerly underpaying eighteen-spot row while preserving strictly increasing awards.
  18: {9: 41, 10: 220, 11: 1100, 12: 5400, 13: 21500, 14: 86000, 15: 215000, 16: 538000, 17: 1076000, 18: 1291000},
  # Raise the formerly underpaying nineteen-spot row while preserving strictly increasing awards.
  19: {9: 22, 10: 110, 11: 550, 12: 3300, 13: 16500, 14: 55000, 15: 165000, 16: 441000, 17: 882000, 18: 1433000, 19: 1763000},
  # Raise the formerly underpaying twenty-spot row while preserving the largest catalog jackpot.
  20: {10: 52, 11: 510, 12: 2500, 13: 10000, 14: 51000, 15: 254000, 16: 1017000, 17: 2542000, 18: 5084000, 19: 7626000, 20: 10169000},
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

# Sample and price one draw without applying its terminal state mutations, so the caller can persist the committed entropy before any credit is issued. (issues #430, #555)
def commit_draw(state):
    # Refuse to sample entropy for an empty round.
    if not state.get("open_tickets"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Buy a Keno ticket first")
    # Draw twenty unique balls from the CSPRNG so results cannot be predicted from seeded Mersenne Twister state. (issue #420)
    drawn = sorted(_SYSTEM_RANDOM.sample(range(1,81), 20))
    # Mint the durable round identity that every settlement row of this draw will carry.
    rid = new_id("kendraw")
    # Set results to the value needed for the next operation.
    results=[]
    # Price every open ticket against the committed sample so a resumed retry replays identical payouts.
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
    # Return the complete committed draw; the caller persists it as the pending settlement before crediting.
    return {"round_id": rid, "timestamp": utc_now(), "drawn": drawn, "results": results}

# Apply one committed draw's terminal mutations exactly once and release the settlement commitment. (issue #555)
def finalize_draw(state, draw):
    # Clear every settled ticket so the next round starts empty.
    state["open_tickets"] = []
    # Append the settled draw to the recent history.
    state.setdefault("last_draws", []).append(draw)
    # Trim the recent history to its bounded tail.
    state["last_draws"] = state["last_draws"][-100:]
    # Release the commitment so the next draw samples fresh entropy.
    state.pop("pending_draw", None)
