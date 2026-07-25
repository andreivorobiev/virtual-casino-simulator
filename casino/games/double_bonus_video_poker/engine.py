"""Deterministic Double Bonus Video Poker rules for GitHub issue #131.

Double Bonus is a single-hand draw video poker on the standard nine-six pay schedule. The player bets,
receives five cards, holds any subset, and draws replacements for the rest; the completed five-card hand
is paid by the paytable. Double Bonus rewards four of a kind richly — four aces pay the most, then four
twos through fours, then four fives through kings — while trimming two pair to even money, and the nine-six
full house and flush keep the schedule house-positive at about a 0.89 percent edge under optimal play. All
amounts are play tokens with no cash value.

Requirements used: CARD-001, POKER-001, LEDGER-005, LEDGER-006, SESSION-005, TOKEN-001.
"""

# Import hashing so authenticated deal actions derive stable route ids.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math

# Import shared card primitives for normalization and shuffling.
from casino.core.cards import coerce_card, shuffled_deck
# Import the shared five-card poker evaluator and ace-high rank values.
from casino.core.poker import RANK_VALUES, evaluate_five
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger row owned by this game.
GAME_ID = "double_bonus_video_poker"
# Deal a five-card video-poker hand.
HAND_SIZE = 5
# Bound reload-safe history so one player document cannot grow without limit.
RECENT_ROUND_LIMIT = 20
# Read the jack and low-quad thresholds once for the paytable bands.
_JACK = RANK_VALUES["J"]
_FOUR = RANK_VALUES["4"]
_ACE = RANK_VALUES["A"]
# Publish the nine-six Double Bonus paytable as total returns for a one-unit bet.
PAYTABLE = {
    "royal_flush": 250,  # A natural royal flush returns two hundred fifty for one.
    "straight_flush": 50,  # A straight flush returns fifty for one.
    "four_aces": 160,  # Four aces return one hundred sixty for one.
    "four_2s_4s": 80,  # Four twos through fours return eighty for one.
    "four_5s_ks": 50,  # Four fives through kings return fifty for one.
    "full_house": 9,  # The nine-six full house returns nine for one.
    "flush": 6,  # The nine-six flush returns six for one.
    "straight": 5,  # A straight returns five for one.
    "three_of_a_kind": 3,  # Three of a kind returns three for one.
    "two_pair": 1,  # Double Bonus trims two pair to an even-money return.
    "jacks_or_better": 1,  # A pair of jacks or better returns even money.
}


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive bet before cards or state are created.
def normalize_bet(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Double Bonus bet must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        bet = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Double Bonus bet must be a positive play-token amount") from None
    # Reject out-of-range, non-finite, and overlarge ledger amounts.
    if bet < 0.01 or bet > 100_000 or not math.isfinite(bet):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Double Bonus bet must be between 0.01 and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return bet


# Normalize the caller's hold selection into a sorted tuple of card positions.
def normalize_hold(value) -> tuple:
    # Treat a missing hold as drawing five fresh cards.
    if value is None:
        # Return an empty hold.
        return ()
    # Require a list of card positions.
    if not isinstance(value, list):
        # Reject non-list hold selections.
        raise ValidationError("hold must be a list of card positions from 0 to 4")
    # Require every position to be a distinct integer within the hand.
    if any(not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < HAND_SIZE for index in value) or len(set(value)) != len(value):
        # Reject duplicate or out-of-range positions.
        raise ValidationError("hold positions must be distinct integers from 0 to 4")
    # Return the sorted hold for a stable fingerprint.
    return tuple(sorted(value))


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter a route path.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"dbvp_{digest[:24]}"


# Normalize fixture or shuffled cards into the Double Bonus layout.
def deal_layout(*, seed=None, fixture=None) -> dict:
    # Read explicit focused-test fixtures before using entropy.
    if fixture is not None:
        # Normalize the five fixture hand cards through shared validation.
        hand = [coerce_card(card).code for card in fixture["hand"]]
        # Normalize the five fixture replacement cards through shared validation.
        draw_pile = [coerce_card(card).code for card in fixture["draw_pile"]]
    # Deal a production or seeded test layout from one shuffled deck.
    else:
        # Shuffle through the shared primitive using secure entropy unless a seed is injected.
        cards = shuffled_deck(seed=seed)
        # Deal the five hand cards.
        hand = [card.code for card in cards[0:5]]
        # Reserve the next five cards as ordered replacements for any discards.
        draw_pile = [card.code for card in cards[5:10]]
    # Reject malformed fixtures that do not match the layout.
    if len(hand) != 5 or len(draw_pile) != 5:
        # Fail closed rather than producing partial public state.
        raise ValidationError("Double Bonus requires five hand cards and five replacement cards")
    # Combine every physical card for duplicate detection.
    all_cards = [*hand, *draw_pile]
    # Reject duplicated physical cards before state is persisted.
    if len(set(all_cards)) != len(all_cards):
        # Surface an impossible layout as a validation error.
        raise ValidationError("Double Bonus cards must be dealt without replacement")
    # Return the public hand and the private replacement pile.
    return {"hand": hand, "draw_pile": draw_pile}


# Classify one completed five-card hand into its Double Bonus paytable tier.
def classify(cards) -> tuple[str, int]:
    # Evaluate the standard five-card poker rank.
    rank = evaluate_five(cards)
    # Treat an ace-high straight flush as the distinct royal-flush tier.
    if rank.name == "straight_flush" and rank.tiebreak == (14,):
        # Return the royal-flush tier.
        return "royal_flush", PAYTABLE["royal_flush"]
    # Return a straight flush at its tier.
    if rank.name == "straight_flush":
        # Return the straight-flush tier.
        return "straight_flush", PAYTABLE["straight_flush"]
    # Split four of a kind into the Double Bonus quad bands.
    if rank.name == "four_of_a_kind":
        # Read the quad rank for banding.
        quad = rank.tiebreak[0]
        # Four aces pay the top quad band.
        if quad == _ACE:
            # Return the four-aces tier.
            return "four_aces", PAYTABLE["four_aces"]
        # Four twos through fours pay the middle quad band.
        if quad <= _FOUR:
            # Return the low-quad tier.
            return "four_2s_4s", PAYTABLE["four_2s_4s"]
        # Every other quad pays the base quad band.
        return "four_5s_ks", PAYTABLE["four_5s_ks"]
    # Return the remaining ranked tiers straight from the paytable.
    for name in ("full_house", "flush", "straight", "three_of_a_kind", "two_pair"):
        # Match the shared category name to a paytable row.
        if rank.name == name:
            # Return the matched tier.
            return name, PAYTABLE[name]
    # Pay a pair of jacks or better even money.
    if rank.name == "one_pair" and rank.tiebreak[0] >= _JACK:
        # Return the jacks-or-better tier.
        return "jacks_or_better", PAYTABLE["jacks_or_better"]
    # Any weaker hand pays nothing.
    return "nothing", 0


# Build one reload-safe round after the bet is requested.
def create_round(player_id: str, bet, start_action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Normalize the bet at the pure engine boundary.
    bet_amount = normalize_bet(bet)
    # Deal all cards up front so reloads cannot change the eventual draw.
    layout = deal_layout(seed=seed, fixture=fixture)
    # Return JSON-compatible prepared state with the replacement pile kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "bet": bet_amount,  # Store the bet amount.
        "phase": "draw",  # Await one hold-and-draw decision.
        "hand": layout["hand"],  # Publish the five dealt cards.
        "_draw_pile": layout["draw_pile"],  # Persist the five replacements privately until the draw.
        "hold": None,  # Reserve the later hold selection.
        "draw_action_id": None,  # Reserve settlement retry identity.
        "opening_status": "pending",  # Require the service to ensure one bet debit.
        "settlement_status": "not_ready",  # Prevent credits before the draw.
        "payout": 0.0,  # Reserve total returned play tokens.
        "net": None,  # Reserve final net movement.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Resolve the draw by replacing discards, evaluating the hand, and settling the paytable.
def draw_round(round_state: dict, action_id: str, hold: tuple, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat an exact repeated draw as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed terminal draw.
        if round_state.get("draw_action_id") != action_id or round_state.get("draw_fingerprint") != request_fingerprint:
            # Preserve the original terminal state.
            raise ConflictError("Double Bonus round was already drawn by another action")
        # Return the already-settled round.
        return round_state
    # Require the draw phase before settling.
    if round_state.get("phase") != "draw":
        # Reject stale actions after settlement.
        raise ConflictError("Double Bonus round cannot be drawn in its current phase")
    # Read the private replacement pile committed at deal time.
    draw_pile = [coerce_card(card).code for card in round_state.get("_draw_pile", [])]
    # Build the final hand by keeping held cards and replacing discards in order.
    replacement = iter(draw_pile)
    # Compose the final five cards position by position.
    final = [round_state["hand"][index] if index in hold else next(replacement) for index in range(HAND_SIZE)]
    # Classify the completed hand.
    tier, multiplier = classify(final)
    # Compute the total returned tokens as the paytable multiplier applied to the bet.
    payout = round(round_state["bet"] * multiplier, 2)
    # Store the hold selection for the record.
    round_state["hold"] = list(hold)
    # Store the settlement action identity for retry-safe payout.
    round_state["draw_action_id"] = action_id
    # Store the semantic fingerprint for retry checks.
    round_state["draw_fingerprint"] = request_fingerprint
    # Publish the completed hand.
    round_state["final_hand"] = final
    # Store the paytable tier.
    round_state["hand_tier"] = tier
    # Store the applied multiplier for transparency.
    round_state["multiplier"] = multiplier
    # Store aggregate returned play tokens.
    round_state["payout"] = payout
    # Store net movement after the bet.
    round_state["net"] = round(payout - round_state["bet"], 2)
    # Classify the player-facing outcome from the payout.
    round_state["outcome"] = "win" if payout > round_state["bet"] else "push" if payout == round_state["bet"] else "lose"
    # Mark deterministic evaluation complete.
    round_state["phase"] = "settled"
    # Require one credit only when returned tokens are due.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Remove the private replacement pile now that the final hand exists.
    round_state.pop("_draw_pile", None)
    # Return the same mutable round for service persistence.
    return round_state


# Find one round by its deal action identity across active and recent state.
def round_for_start_action(state: dict, action_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first exact identity match while ignoring empty slots.
    return next((item for item in candidates if item and item.get("start_action_id") == action_id), None)


# Find one round by its server identifier across active and recent state.
def round_by_id(state: dict, round_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first matching round while ignoring empty slots.
    return next((item for item in candidates if item and item.get("round_id") == round_id), None)


# Move a terminal round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Normalize the optional active slot before reading its identifier.
    active_round = state.get("active_round") or {}
    # Clear the actionable slot only when it contains this exact round.
    if active_round.get("round_id") == round_state.get("round_id"):
        # Prevent further draws against the terminal round.
        state["active_round"] = None
    # Remove any older copy before appending an idempotent settlement.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the newest terminal result in stable chronological order.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private recovery fields from one public round payload.
def public_round(round_state):
    # Preserve a null active-round slot without creating a placeholder.
    if round_state is None:
        # Return JSON null through the router.
        return None
    # Exclude hidden cards and internal fingerprints from public responses.
    private_fields = {"_draw_pile", "request_fingerprint", "draw_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide the unrevealed replacement pile.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
