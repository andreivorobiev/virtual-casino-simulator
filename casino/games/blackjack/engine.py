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
GAME_ID = "blackjack"
# Set RANKS to the value needed for the next operation.
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
# Set SUITS to the value needed for the next operation.
SUITS = ["♠","♥","♦","♣"]

# Define the make_shoe function used by this module.
def make_shoe(decks=6):
    # Set cards to the value needed for the next operation.
    cards = [r+s for _ in range(int(decks)) for s in SUITS for r in RANKS]
    # Execute this statement as part of the module's documented control flow.
    random.shuffle(cards)
    # Return the computed value to the caller.
    return cards

# Define the card_rank function used by this module.
def card_rank(card: str) -> str:
    # Return the computed value to the caller.
    return card[:-1]

# Define the card_value function used by this module.
def card_value(card: str) -> int:
    # Set r to the value needed for the next operation.
    r = card_rank(card)
    # Branch when the following condition is true.
    if r == "A": return 11
    # Branch when the following condition is true.
    if r in ("J","Q","K"): return 10
    # Return the computed value to the caller.
    return int(r)

# Define the hand_total function used by this module.
def hand_total(cards: list[str]) -> dict:
    # Set total to the value needed for the next operation.
    total = sum(card_value(c) for c in cards)
    # Set aces to the value needed for the next operation.
    aces = sum(1 for c in cards if card_rank(c) == "A")
    # Continue looping while the condition remains true.
    while total > 21 and aces:
        # Set total - to the value needed for the next operation.
        total -= 10; aces -= 1
    # Set hard_total to the value needed for the next operation.
    hard_total = sum(1 if card_rank(c)=="A" else card_value(c) for c in cards)
    # Set soft to the value needed for the next operation.
    soft = any(card_rank(c)=="A" for c in cards) and hard_total + 10 <= 21
    # Return the computed value to the caller.
    return {"total": total, "soft": soft, "blackjack": len(cards)==2 and total==21, "bust": total>21}

# Define the default_state function used by this module.
def default_state():
    # Return the computed value to the caller.
    return {"rules": {"decks":6, "dealer_hits_soft_17": False, "blackjack_payout": 1.5, "max_split_hands": 4, "double_after_split": True, "late_surrender": True, "split_aces_one_card": True}, "shoe": [], "rounds": {}}

# Define the draw function used by this module.
def draw(state):
    # Set decks to the value needed for the next operation.
    decks = int(state.get("rules",{}).get("decks",6))
    # Branch when the following condition is true.
    if len(state.get("shoe", [])) < 52:
        # Set state["shoe"] to the value needed for the next operation.
        state["shoe"] = make_shoe(decks)
    # Return the computed value to the caller.
    return state["shoe"].pop()

# Define the active_rounds_for_player function used by this module.
def active_rounds_for_player(state, player_id):
    # Return the computed value to the caller.
    return [r for r in state.get("rounds",{}).values() if r.get("player_id") == player_id and r.get("status") in ("player_turn","settled_pending_credit")]

# Define the new_round function used by this module.
def new_round(state, player_id, bet_amount):
    # Branch when the following condition is true.
    if active_rounds_for_player(state, player_id):
        # Raise an error so invalid input or state is reported explicitly.
        raise ConflictError("Finish the active blackjack round before dealing a new one")
    # Set rid to the value needed for the next operation.
    rid = new_id("bj")
    # Set hand_id to the value needed for the next operation.
    hand_id = new_id("hand")
    # Set player_cards to the value needed for the next operation.
    player_cards = [draw(state), draw(state)]
    # Set dealer_cards to the value needed for the next operation.
    dealer_cards = [draw(state), draw(state)]
    # Set rnd to the value needed for the next operation.
    rnd = {"round_id": rid, "player_id": player_id, "status": "player_turn", "created_at": utc_now(), "dealer": {"cards": dealer_cards, "hole_card_hidden": True}, "hands": [{"hand_id": hand_id, "cards": player_cards, "bet": bet_amount, "status": "active", "is_split_hand": False, "actions": []}], "active_hand_index": 0, "insurance": None, "even_money": None, "settlements": []}
    # Set state.setdefault("rounds", {})[rid] to the value needed for the next operation.
    state.setdefault("rounds", {})[rid] = rnd
    # Execute this statement as part of the module's documented control flow.
    auto_blackjacks(state, rnd)
    # Return the computed value to the caller.
    return rnd

# Define the auto_blackjacks function used by this module.
def auto_blackjacks(state, rnd):
    # Set dealer to the value needed for the next operation.
    dealer = hand_total(rnd["dealer"]["cards"])
    # Set hand to the value needed for the next operation.
    hand = hand_total(rnd["hands"][0]["cards"])
    # Branch when the following condition is true.
    if hand["blackjack"] or dealer["blackjack"]:
        # If dealer shows Ace and player has blackjack, allow even money before auto settlement through API.
        # Branch when the following condition is true.
        if hand["blackjack"] and card_rank(rnd["dealer"]["cards"][0]) == "A" and not dealer["blackjack"]:
            # Return the computed value to the caller.
            return
        # Set rnd["dealer"]["hole_card_hidden"] to the value needed for the next operation.
        rnd["dealer"]["hole_card_hidden"] = False
        # Set rnd["status"] to the value needed for the next operation.
        rnd["status"] = "settled_pending_credit"
        # Set h to the value needed for the next operation.
        h = rnd["hands"][0]
        # Branch when the following condition is true.
        if hand["blackjack"] and dealer["blackjack"]:
            # Set h["status"] to the value needed for the next operation.
            h["status"] = "push"; h["outcome"] = "push"; h["payout_due"] = h["bet"]
        # Branch when the prior condition failed and this condition is true.
        elif hand["blackjack"]:
            # Set h["status"] to the value needed for the next operation.
            h["status"] = "blackjack"; h["outcome"] = "blackjack"; h["payout_due"] = round(h["bet"]*(1+float(state["rules"].get("blackjack_payout",1.5))),2)
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Set h["status"] to the value needed for the next operation.
            h["status"] = "loss"; h["outcome"] = "dealer_blackjack"; h["payout_due"] = 0

# Define the get_round function used by this module.
def get_round(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = state.get("rounds",{}).get(rid)
    # Branch when the following condition is true.
    if not rnd: raise ValidationError("Blackjack round not found")
    # Return the computed value to the caller.
    return rnd

# Define the active_hand function used by this module.
def active_hand(rnd):
    # Set idx to the value needed for the next operation.
    idx = rnd.get("active_hand_index", 0)
    # Branch when the following condition is true.
    if idx >= len(rnd["hands"]):
        # Return the computed value to the caller.
        return None
    # Return the computed value to the caller.
    return rnd["hands"][idx]

# Define the advance_hand_or_dealer function used by this module.
def advance_hand_or_dealer(state, rnd):
    # Iterate through the collection to process each item.
    for i,h in enumerate(rnd["hands"]):
        # Branch when the following condition is true.
        if h.get("status") == "active":
            # Set rnd["active_hand_index"] to the value needed for the next operation.
            rnd["active_hand_index"] = i; return rnd
    # Execute this statement as part of the module's documented control flow.
    dealer_play(state, rnd); return rnd

# Define the hit function used by this module.
def hit(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    # Branch when the following condition is true.
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    # Branch when the following condition is true.
    if not h or h["status"] != "active": raise ConflictError("No active hand")
    # Branch when the following condition is true.
    if h.get("split_aces_locked"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Split aces receive one card only under current table rules")
    # Execute this statement as part of the module's documented control flow.
    h["cards"].append(draw(state)); h["actions"].append("hit")
    # Set total to the value needed for the next operation.
    total = hand_total(h["cards"])
    # Branch when the following condition is true.
    if total["bust"]:
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "bust"; h["outcome"] = "bust"; h["payout_due"] = 0
        # Execute this statement as part of the module's documented control flow.
        advance_hand_or_dealer(state, rnd)
    # Return the computed value to the caller.
    return rnd

# Define the stand function used by this module.
def stand(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    # Branch when the following condition is true.
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    # Branch when the following condition is true.
    if not h: raise ConflictError("No active hand")
    # Set h["status"] to the value needed for the next operation.
    h["status"] = "stand"; h["actions"].append("stand")
    # Execute this statement as part of the module's documented control flow.
    advance_hand_or_dealer(state, rnd)
    # Return the computed value to the caller.
    return rnd

# Define the can_double function used by this module.
def can_double(state, h):
    # Branch when the following condition is true.
    if not h or len(h["cards"]) != 2: return False
    # Set actions to the value needed for the next operation.
    actions = [a for a in h.get("actions", []) if a not in ("split",)]
    # Branch when the following condition is true.
    if actions: return False
    # Branch when the following condition is true.
    if h.get("is_split_hand") and not state.get("rules",{}).get("double_after_split", True): return False
    # Branch when the following condition is true.
    if h.get("split_aces_locked"): return False
    # Return the computed value to the caller.
    return True

# Define the double_down function used by this module.
def double_down(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    # Branch when the following condition is true.
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    # Branch when the following condition is true.
    if not can_double(state, h): raise ValidationError("Double down is not allowed on this hand")
    # Set h["cards"].append(draw(state)); h["bet"] to the value needed for the next operation.
    h["cards"].append(draw(state)); h["bet"] = round(float(h["bet"])*2,2); h["actions"].append("double")
    # Set total to the value needed for the next operation.
    total = hand_total(h["cards"])
    # Branch when the following condition is true.
    if total["bust"]:
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "bust"; h["outcome"] = "bust"; h["payout_due"] = 0
    # Handle the fallback branch when prior conditions did not match.
    else:
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "stand"
    # Execute this statement as part of the module's documented control flow.
    advance_hand_or_dealer(state, rnd)
    # Return the computed value to the caller.
    return rnd

# Define the split function used by this module.
def split(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    # Branch when the following condition is true.
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    # Branch when the following condition is true.
    if not h or len(h["cards"]) != 2: raise ValidationError("Split requires an active two-card hand")
    # Branch when the following condition is true.
    if card_value(h["cards"][0]) != card_value(h["cards"][1]): raise ValidationError("Cards must have equal blackjack value to split")
    # Branch when the following condition is true.
    if len(rnd["hands"]) >= int(state["rules"].get("max_split_hands",4)): raise ValidationError("Maximum split hands reached")
    # Set c1,c2 to the value needed for the next operation.
    c1,c2 = h["cards"]
    # Set ace_split to the value needed for the next operation.
    ace_split = card_rank(c1) == "A" and card_rank(c2) == "A"
    # Set h1 to the value needed for the next operation.
    h1 = {"hand_id": h["hand_id"], "cards": [c1, draw(state)], "bet": h["bet"], "status": "active", "is_split_hand": True, "actions": ["split"], "split_from": h["hand_id"]}
    # Set h2 to the value needed for the next operation.
    h2 = {"hand_id": new_id("hand"), "cards": [c2, draw(state)], "bet": h["bet"], "status": "active", "is_split_hand": True, "actions": ["split"], "split_from": h["hand_id"]}
    # Branch when the following condition is true.
    if ace_split and state.get("rules",{}).get("split_aces_one_card", True):
        # Set h1["status"] to the value needed for the next operation.
        h1["status"] = "stand"; h1["split_aces_locked"] = True
        # Set h2["status"] to the value needed for the next operation.
        h2["status"] = "stand"; h2["split_aces_locked"] = True
    # Set idx to the value needed for the next operation.
    idx = rnd["active_hand_index"]
    # Set rnd["hands"][idx:idx+1] to the value needed for the next operation.
    rnd["hands"][idx:idx+1] = [h1,h2]
    # Set rnd["active_hand_index"] to the value needed for the next operation.
    rnd["active_hand_index"] = idx
    # Execute this statement as part of the module's documented control flow.
    advance_hand_or_dealer(state, rnd)
    # Return the computed value to the caller.
    return rnd

# Define the surrender function used by this module.
def surrender(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    # Branch when the following condition is true.
    if not state["rules"].get("late_surrender", True): raise ValidationError("Surrender is disabled")
    # Branch when the following condition is true.
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    # Set actions to the value needed for the next operation.
    actions = [a for a in h.get("actions", []) if a != "split"] if h else []
    # Branch when the following condition is true.
    if not h or len(h["cards"]) != 2 or actions: raise ValidationError("Surrender is only available as first action")
    # Set h["status"] to the value needed for the next operation.
    h["status"] = "surrender"; h["outcome"] = "surrender"; h["payout_due"] = round(float(h["bet"])/2,2); h["actions"].append("surrender")
    # Execute this statement as part of the module's documented control flow.
    advance_hand_or_dealer(state, rnd)
    # Return the computed value to the caller.
    return rnd

# Define the dealer_play function used by this module.
def dealer_play(state, rnd):
    # Set rnd["dealer"]["hole_card_hidden"] to the value needed for the next operation.
    rnd["dealer"]["hole_card_hidden"] = False
    # Continue looping while the condition remains true.
    while True:
        # Set total to the value needed for the next operation.
        total = hand_total(rnd["dealer"]["cards"])
        # Branch when the following condition is true.
        if total["bust"]: break
        # Branch when the following condition is true.
        if total["total"] < 17:
            # Execute this statement as part of the module's documented control flow.
            rnd["dealer"]["cards"].append(draw(state)); continue
        # Branch when the following condition is true.
        if total["total"] == 17 and total["soft"] and state["rules"].get("dealer_hits_soft_17"):
            # Execute this statement as part of the module's documented control flow.
            rnd["dealer"]["cards"].append(draw(state)); continue
        # Execute this statement as part of the module's documented control flow.
        break
    # Set dealer_total to the value needed for the next operation.
    dealer_total = hand_total(rnd["dealer"]["cards"])
    # Iterate through the collection to process each item.
    for h in rnd["hands"]:
        # Branch when the following condition is true.
        if h.get("outcome") in ("bust","surrender","blackjack","push","dealer_blackjack"):
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set ht to the value needed for the next operation.
        ht = hand_total(h["cards"])
        # Branch when the following condition is true.
        if ht["bust"]:
            # Set h["outcome"] to the value needed for the next operation.
            h["outcome"]="bust"; h["payout_due"] = 0
        # Branch when the prior condition failed and this condition is true.
        elif dealer_total["bust"]:
            # Set h["outcome"] to the value needed for the next operation.
            h["outcome"]="win"; h["payout_due"] = round(float(h["bet"])*2,2)
        # Branch when the prior condition failed and this condition is true.
        elif ht["total"] > dealer_total["total"]:
            # Set h["outcome"] to the value needed for the next operation.
            h["outcome"]="win"; h["payout_due"] = round(float(h["bet"])*2,2)
        # Branch when the prior condition failed and this condition is true.
        elif ht["total"] < dealer_total["total"]:
            # Set h["outcome"] to the value needed for the next operation.
            h["outcome"]="loss"; h["payout_due"] = 0
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Set h["outcome"] to the value needed for the next operation.
            h["outcome"]="push"; h["payout_due"] = float(h["bet"])
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "settled"
    # Set rnd["status"] to the value needed for the next operation.
    rnd["status"] = "settled_pending_credit"
    # Return the computed value to the caller.
    return rnd

# Define the settle_round function used by this module.
def settle_round(rnd):
    # Set rnd["status"] to the value needed for the next operation.
    rnd["status"] = "settled"
    # Return the computed value to the caller.
    return rnd
