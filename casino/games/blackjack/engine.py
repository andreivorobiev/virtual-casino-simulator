# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Pure Blackjack shoe, hand, dealer, and payout state transitions.
import random
from casino.core.ids import new_id
from casino.core.clock import utc_now
from casino.errors import ValidationError, ConflictError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "blackjack"
# Set RANKS to the value needed for the next operation.
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
# Set SUITS to the value needed for the next operation.
SUITS = ["♠","♥","♦","♣"]
# Hold one module-level CSPRNG so production shuffles never use the predictable Mersenne Twister default. (issue #420)
_SYSTEM_RNG = random.SystemRandom()

# Define the make_shoe function used by this module.
def make_shoe(decks=6, rng=None):
    # Set cards to the value needed for the next operation.
    cards = [r+s for _ in range(int(decks)) for s in SUITS for r in RANKS]
    # Shuffle with an injected deterministic generator in tests or the module CSPRNG in production. (issue #420)
    (_SYSTEM_RNG if rng is None else rng).shuffle(cards)
    return cards

# Define the card_rank function used by this module.
def card_rank(card: str) -> str:
    return card[:-1]

# Define the card_value function used by this module.
def card_value(card: str) -> int:
    # Set r to the value needed for the next operation.
    r = card_rank(card)
    if r == "A": return 11
    if r in ("J","Q","K"): return 10
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
    return {"total": total, "soft": soft, "blackjack": len(cards)==2 and total==21, "bust": total>21}

# Define the default_state function used by this module.
def default_state():
    return {"rules": {"decks":6, "dealer_hits_soft_17": False, "blackjack_payout": 1.5, "max_split_hands": 4, "double_after_split": True, "late_surrender": True, "split_aces_one_card": True}, "shoe": [], "rounds": {}}

# Compute the total stake return for one natural at the configured table rate. (BJ-005, BJ-031)
def natural_payout_due(state, bet) -> float:
    # Read the centrally repaired table setting after state_store applies the descriptor domain. (SEC-014)
    payout_rate = float(state["rules"]["blackjack_payout"])
    # Return the original stake plus the configured natural profit at ledger precision.
    return round(float(bet) * (1 + payout_rate), 2)

# Define the draw function used by this module.
def draw(state):
    # Read the centrally repaired deck count after state_store applies the descriptor domain. (SEC-014)
    decks = int(state["rules"]["decks"])
    # Scale the cut threshold for a one-deck game while retaining the historical 52-card ceiling.
    rebuild_threshold = min(52, max(15, 13 * decks))
    if len(state.get("shoe", [])) < rebuild_threshold:
        # Set state["shoe"] to the value needed for the next operation.
        state["shoe"] = make_shoe(decks)
    return state["shoe"].pop()

# Define the active_rounds_for_player function used by this module.
def active_rounds_for_player(state, player_id):
    return [r for r in state.get("rounds",{}).values() if r.get("player_id") == player_id and r.get("status") in ("player_turn","settled_pending_credit")]

# Define the new_round function used by this module.
def new_round(state, player_id, bet_amount):
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
    auto_blackjacks(state, rnd)
    return rnd

# Define the auto_blackjacks function used by this module.
def auto_blackjacks(state, rnd):
    # Set dealer to the value needed for the next operation.
    dealer = hand_total(rnd["dealer"]["cards"])
    # Set hand to the value needed for the next operation.
    hand = hand_total(rnd["hands"][0]["cards"])
    if hand["blackjack"] or dealer["blackjack"]:
        # If dealer shows Ace and player has blackjack, allow even money before auto settlement through API.
        if hand["blackjack"] and card_rank(rnd["dealer"]["cards"][0]) == "A" and not dealer["blackjack"]:
            return
        # Set rnd["dealer"]["hole_card_hidden"] to the value needed for the next operation.
        rnd["dealer"]["hole_card_hidden"] = False
        # Set rnd["status"] to the value needed for the next operation.
        rnd["status"] = "settled_pending_credit"
        # Set h to the value needed for the next operation.
        h = rnd["hands"][0]
        if hand["blackjack"] and dealer["blackjack"]:
            # Set h["status"] to the value needed for the next operation.
            h["status"] = "push"; h["outcome"] = "push"; h["payout_due"] = h["bet"]
        # Branch when the prior condition failed and this condition is true.
        elif hand["blackjack"]:
            # Set h["status"] to the value needed for the next operation.
            h["status"] = "blackjack"; h["outcome"] = "blackjack"; h["payout_due"] = natural_payout_due(state, h["bet"])
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Set h["status"] to the value needed for the next operation.
            h["status"] = "loss"; h["outcome"] = "dealer_blackjack"; h["payout_due"] = 0

# Define the get_round function used by this module.
def get_round(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = state.get("rounds",{}).get(rid)
    if not rnd: raise ValidationError("Blackjack round not found")
    return rnd

# Define the active_hand function used by this module.
def active_hand(rnd):
    # Set idx to the value needed for the next operation.
    idx = rnd.get("active_hand_index", 0)
    if idx >= len(rnd["hands"]):
        return None
    return rnd["hands"][idx]

# Define the advance_hand_or_dealer function used by this module.
def advance_hand_or_dealer(state, rnd):
    for i,h in enumerate(rnd["hands"]):
        if h.get("status") == "active":
            # Set rnd["active_hand_index"] to the value needed for the next operation.
            rnd["active_hand_index"] = i; return rnd
    dealer_play(state, rnd); return rnd

# Define the hit function used by this module.
def hit(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    if not h or h["status"] != "active": raise ConflictError("No active hand")
    if h.get("split_aces_locked"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Split aces receive one card only under current table rules")
    h["cards"].append(draw(state)); h["actions"].append("hit")
    # Set total to the value needed for the next operation.
    total = hand_total(h["cards"])
    if total["bust"]:
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "bust"; h["outcome"] = "bust"; h["payout_due"] = 0
        advance_hand_or_dealer(state, rnd)
    return rnd

# Define the stand function used by this module.
def stand(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    if not h: raise ConflictError("No active hand")
    # Set h["status"] to the value needed for the next operation.
    h["status"] = "stand"; h["actions"].append("stand")
    advance_hand_or_dealer(state, rnd)
    return rnd

# Define the can_double function used by this module.
def can_double(state, h):
    if not h or len(h["cards"]) != 2: return False
    # Set actions to the value needed for the next operation.
    actions = [a for a in h.get("actions", []) if a not in ("split",)]
    if actions: return False
    # Read the clamped switch so a poisoned persisted value cannot widen doubling exposure. (issue #404 read-side)
    if h.get("is_split_hand") and not state["rules"]["double_after_split"]: return False
    if h.get("split_aces_locked"): return False
    return True

# Define the double_down function used by this module.
def double_down(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    if not can_double(state, h): raise ValidationError("Double down is not allowed on this hand")
    # Set h["cards"].append(draw(state)); h["bet"] to the value needed for the next operation.
    h["cards"].append(draw(state)); h["bet"] = round(float(h["bet"])*2,2); h["actions"].append("double")
    # Set total to the value needed for the next operation.
    total = hand_total(h["cards"])
    if total["bust"]:
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "bust"; h["outcome"] = "bust"; h["payout_due"] = 0
    # Handle the fallback branch when prior conditions did not match.
    else:
        # Set h["status"] to the value needed for the next operation.
        h["status"] = "stand"
    advance_hand_or_dealer(state, rnd)
    return rnd

# Define the split function used by this module.
def split(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    if not h or len(h["cards"]) != 2: raise ValidationError("Split requires an active two-card hand")
    if card_value(h["cards"][0]) != card_value(h["cards"][1]): raise ValidationError("Cards must have equal blackjack value to split")
    # Read the clamped split ceiling so a poisoned persisted value cannot multiply wager exposure. (issue #404 read-side)
    if len(rnd["hands"]) >= state["rules"]["max_split_hands"]: raise ValidationError("Maximum split hands reached")
    # Set c1,c2 to the value needed for the next operation.
    c1,c2 = h["cards"]
    # Set ace_split to the value needed for the next operation.
    ace_split = card_rank(c1) == "A" and card_rank(c2) == "A"
    # Set h1 to the value needed for the next operation.
    h1 = {"hand_id": h["hand_id"], "cards": [c1, draw(state)], "bet": h["bet"], "status": "active", "is_split_hand": True, "actions": ["split"], "split_from": h["hand_id"]}
    # Set h2 to the value needed for the next operation.
    h2 = {"hand_id": new_id("hand"), "cards": [c2, draw(state)], "bet": h["bet"], "status": "active", "is_split_hand": True, "actions": ["split"], "split_from": h["hand_id"]}
    # Read the clamped switch so a poisoned persisted value cannot change split-ace settlement behavior. (issue #404 read-side)
    if ace_split and state["rules"]["split_aces_one_card"]:
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
    advance_hand_or_dealer(state, rnd)
    return rnd

# Define the surrender function used by this module.
def surrender(state, rid):
    # Set rnd to the value needed for the next operation.
    rnd = get_round(state, rid)
    # Read the clamped switch so a poisoned persisted value cannot toggle half-stake surrender returns. (issue #404 read-side)
    if not state["rules"]["late_surrender"]: raise ValidationError("Surrender is disabled")
    if rnd["status"] != "player_turn": raise ConflictError("Round is not in player turn")
    # Set h to the value needed for the next operation.
    h = active_hand(rnd)
    # Set actions to the value needed for the next operation.
    actions = [a for a in h.get("actions", []) if a != "split"] if h else []
    if not h or len(h["cards"]) != 2 or actions: raise ValidationError("Surrender is only available as first action")
    # Set h["status"] to the value needed for the next operation.
    h["status"] = "surrender"; h["outcome"] = "surrender"; h["payout_due"] = round(float(h["bet"])/2,2); h["actions"].append("surrender")
    advance_hand_or_dealer(state, rnd)
    return rnd

# Define the dealer_play function used by this module.
def dealer_play(state, rnd):
    # Set rnd["dealer"]["hole_card_hidden"] to the value needed for the next operation.
    rnd["dealer"]["hole_card_hidden"] = False
    # Continue looping while the condition remains true.
    while True:
        # Set total to the value needed for the next operation.
        total = hand_total(rnd["dealer"]["cards"])
        if total["bust"]: break
        if total["total"] < 17:
            rnd["dealer"]["cards"].append(draw(state)); continue
        # Read the clamped switch so a poisoned persisted value cannot alter dealer drawing and outcome money. (issue #404 read-side)
        if total["total"] == 17 and total["soft"] and state["rules"]["dealer_hits_soft_17"]:
            rnd["dealer"]["cards"].append(draw(state)); continue
        break
    # Set dealer_total to the value needed for the next operation.
    dealer_total = hand_total(rnd["dealer"]["cards"])
    for h in rnd["hands"]:
        if h.get("outcome") in ("bust","surrender","blackjack","push","dealer_blackjack"):
            continue
        # Set ht to the value needed for the next operation.
        ht = hand_total(h["cards"])
        # Distinguish an opening natural from a two-card twenty-one produced by a split.
        is_natural = ht["blackjack"] and not h.get("is_split_hand", False)
        if ht["bust"]:
            # Set h["outcome"] to the value needed for the next operation.
            h["outcome"]="bust"; h["payout_due"] = 0
        # Settle a deferred natural before ordinary dealer bust and total comparison. (BJ-031)
        elif is_natural:
            # Preserve the natural outcome and configured rate after even money is declined.
            h["outcome"]="blackjack"; h["payout_due"] = natural_payout_due(state, h["bet"])
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
        # Preserve the natural hand status while ordinary comparison outcomes become settled.
        h["status"] = "blackjack" if is_natural else "settled"
    # Set rnd["status"] to the value needed for the next operation.
    rnd["status"] = "settled_pending_credit"
    return rnd

# Define the settle_round function used by this module.
def settle_round(rnd):
    # Set rnd["status"] to the value needed for the next operation.
    rnd["status"] = "settled"
    return rnd
