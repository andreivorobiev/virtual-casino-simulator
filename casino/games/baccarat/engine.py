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
GAME_ID = "baccarat"
# Set RANKS to the value needed for the next operation.
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
# Set SUITS to the value needed for the next operation.
SUITS = ["♠","♥","♦","♣"]
# Hold one module-level CSPRNG so production shuffles never use the predictable Mersenne Twister default. (issue #420)
_SYSTEM_RNG = random.SystemRandom()

# Define the make_shoe function used by this module.
def make_shoe(decks=8, rng=None):
    # Set shoe to the value needed for the next operation.
    shoe = [r+s for _ in range(int(decks)) for s in SUITS for r in RANKS]
    # Shuffle with an injected deterministic generator in tests or the module CSPRNG in production. (issue #420)
    (_SYSTEM_RNG if rng is None else rng).shuffle(shoe)
    # Return the computed value to the caller.
    return shoe

# Define the rank function used by this module.
def rank(card): return card[:-1]
# Define the value function used by this module.
def value(card):
    # Set r to the value needed for the next operation.
    r=rank(card)
    # Branch when the following condition is true.
    if r=="A": return 1
    # Branch when the following condition is true.
    if r in ("10","J","Q","K"): return 0
    # Return the computed value to the caller.
    return int(r)
# Define the total function used by this module.
def total(cards): return sum(value(c) for c in cards) % 10

# Define the default_state function used by this module.
def default_state():
    # Return the computed value to the caller.
    return {"rules": {"decks":8, "tie_payout":8, "banker_commission":0.05, "tie_behavior":"push", "cut_cards_remaining":14}, "shoe": [], "shoe_id": None, "coup_number":0, "open_bets": [], "last_coups": []}

# Define the ensure_shoe function used by this module.
def ensure_shoe(state):
    # Read centrally repaired rules after state_store applies the descriptor domain. (SEC-014)
    rules = state["rules"]
    # Set decks to the value needed for the next operation.
    decks = int(rules["decks"])
    # Set cut to the value needed for the next operation.
    cut = int(rules.get("cut_cards_remaining", 14) or 14)
    # Branch when the following condition is true.
    if not state.get("shoe") or len(state["shoe"]) < cut:
        # Set state["shoe"] to the value needed for the next operation.
        state["shoe"] = make_shoe(decks)
        # Set state["shoe_id"] to the value needed for the next operation.
        state["shoe_id"] = new_id("shoe")
        # Set state["coup_number"] to the value needed for the next operation.
        state["coup_number"] = 0
        # Set first to the value needed for the next operation.
        first = state["shoe"].pop()
        # Set r to the value needed for the next operation.
        r = rank(first)
        # Set burn_n to the value needed for the next operation.
        burn_n = 10 if r in ("10","J","Q","K") else 1 if r == "A" else int(r)
        # Set burned to the value needed for the next operation.
        burned = [state["shoe"].pop() for _ in range(min(burn_n, len(state["shoe"])))]
        # Set state["burn"] to the value needed for the next operation.
        state["burn"] = {"first_card": first, "burned": burned, "burn_count": len(burned)}

# Define the draw function used by this module.
def draw(state):
    # Execute this statement as part of the module's documented control flow.
    ensure_shoe(state)
    # Return the computed value to the caller.
    return state["shoe"].pop()

# Define the add_bet function used by this module.
def add_bet(state, player_id, bet_type, amount, source="manual"):
    # Branch when the following condition is true.
    if bet_type not in ("player","banker","tie"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Baccarat bet_type must be player, banker, or tie")
    # Set bet to the value needed for the next operation.
    bet = {"bet_id": new_id("bacbet"), "player_id": player_id, "type": bet_type, "label": bet_type.title(), "amount": amount, "source": source}
    # Execute this statement as part of the module's documented control flow.
    state.setdefault("open_bets", []).append(bet)
    # Return the computed value to the caller.
    return bet

# Define the remove_bet function used by this module.
def remove_bet(state, bet_id, player_id):
    # Iterate through the collection to process each item.
    for i,b in enumerate(state.setdefault("open_bets", [])):
        # Branch when the following condition is true.
        if b["bet_id"] == bet_id and b["player_id"] == player_id:
            # Return the computed value to the caller.
            return state["open_bets"].pop(i)
    # Raise an error so invalid input or state is reported explicitly.
    raise ValidationError("Baccarat bet was not found")

# Deal and price one coup without applying its terminal state mutations, so the caller can persist the committed cards and consumed shoe before any credit is issued. (issues #430, #555)
def commit_coup(state, force=None):
    # Refuse to deal a coup with no staked bets.
    if not state.get("open_bets"):
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("Place a baccarat bet before dealing")
    # Execute this statement as part of the module's documented control flow.
    ensure_shoe(state)
    # Set state["coup_number"] to the value needed for the next operation.
    state["coup_number"] = int(state.get("coup_number",0)) + 1
    # Set rid to the value needed for the next operation.
    rid = new_id("bac")
    # Realistic Punto Banco deal order: Player, Banker, Player, Banker.
    # Set player to the value needed for the next operation.
    player = [draw(state)]
    # Set banker to the value needed for the next operation.
    banker = [draw(state)]
    # Execute this statement as part of the module's documented control flow.
    player.append(draw(state))
    # Execute this statement as part of the module's documented control flow.
    banker.append(draw(state))
    # Set pt, bt to the value needed for the next operation.
    pt, bt = total(player), total(banker)
    # Set natural to the value needed for the next operation.
    natural = pt in (8,9) or bt in (8,9)
    # Set player_third to the value needed for the next operation.
    player_third = None
    # Branch when the following condition is true.
    if not natural:
        # Branch when the following condition is true.
        if pt <= 5:
            # Set player_third to the value needed for the next operation.
            player_third = draw(state); player.append(player_third)
        # Set bt to the value needed for the next operation.
        bt = total(banker)
        # Branch when the following condition is true.
        if player_third is None:
            # Branch when the following condition is true.
            if bt <= 5: banker.append(draw(state))
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Set pv to the value needed for the next operation.
            pv = value(player_third)
            # Branch when the following condition is true.
            if bt <= 2: banker.append(draw(state))
            # Branch when the prior condition failed and this condition is true.
            elif bt == 3 and pv != 8: banker.append(draw(state))
            # Branch when the prior condition failed and this condition is true.
            elif bt == 4 and 2 <= pv <= 7: banker.append(draw(state))
            # Branch when the prior condition failed and this condition is true.
            elif bt == 5 and 4 <= pv <= 7: banker.append(draw(state))
            # Branch when the prior condition failed and this condition is true.
            elif bt == 6 and 6 <= pv <= 7: banker.append(draw(state))
    # Set pt, bt to the value needed for the next operation.
    pt, bt = total(player), total(banker)
    # Set winner to the value needed for the next operation.
    winner = "player" if pt > bt else "banker" if bt > pt else "tie"
    # Set coup to the value needed for the next operation.
    coup = {"round_id": rid, "shoe_id": state.get("shoe_id"), "coup_number": state["coup_number"], "timestamp": utc_now(), "player_cards": player, "banker_cards": banker, "player_total": pt, "banker_total": bt, "winner": winner, "natural": natural, "bets": state.get("open_bets", []), "shoe_remaining": len(state.get("shoe", [])), "burn": state.get("burn")}
    # Return the complete committed coup; the caller persists it and the consumed shoe before settlement.
    return coup

# Apply one committed coup's terminal mutations exactly once and release the settlement commitment. (issue #555)
def finalize_coup(state, coup):
    # Clear the settled bets so the next coup starts empty.
    state["open_bets"] = []
    # Append the settled coup to the recent history.
    state.setdefault("last_coups", []).append(coup)
    # Trim the recent history to its bounded tail.
    state["last_coups"] = state["last_coups"][-100:]
    # Release the commitment so the next deal draws from the persisted shoe position.
    state.pop("pending_coup", None)

# Define the settle_bet function used by this module.
def settle_bet(bet, coup, rules):
    # Set amount to the value needed for the next operation.
    amount = float(bet["amount"])
    # Branch when the following condition is true.
    if bet["type"] == coup["winner"]:
        # Branch when the following condition is true.
        if bet["type"] == "banker":
            # Return the computed value to the caller.
            return {"outcome":"win", "credit": round(amount * (2 - float(rules.get("banker_commission",0.05))), 2)}
        # Branch when the following condition is true.
        if bet["type"] == "tie":
            # Return the computed value to the caller.
            return {"outcome":"win", "credit": round(amount * (1 + float(rules.get("tie_payout",8))), 2)}
        # Return the computed value to the caller.
        return {"outcome":"win", "credit": round(amount * 2, 2)}
    # Branch when the following condition is true.
    if coup["winner"] == "tie" and bet["type"] in ("player","banker"):
        # Apply the descriptor-owned tie behavior explicitly instead of carrying a dead setting. (SEC-014)
        if rules["tie_behavior"] == "push":
            # Return the original stake for the only published Punto Banco tie behavior.
            return {"outcome":"push", "credit": amount}
    # Return the computed value to the caller.
    return {"outcome":"loss", "credit": 0.0}
