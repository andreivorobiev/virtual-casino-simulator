"""Pure Pai Gow Poker rules: a 53-card joker deck set into a five-card high
hand and a two-card low hand, compared against a house-way dealer.

The joker is a bug: it completes straights, flushes, and straight flushes, and
otherwise plays as an ace. Copies (ties on a hand) go to the dealer, and winning
even-money bets pay a five percent house commission.

Requirements: PGP-001, PGP-002.
"""

# Import deterministic hashing for stable round ids and math for wager bounds.
import hashlib
import math
# Import isolated randomness so seeded tests reproduce exact deals.
import random
# Import the shared immutable card so the fifty-two natural cards stay canonical.
from casino.core.cards import Card, coerce_card
# Import ace-high rank values so the joker evaluator matches the shared scale.
from casino.core.poker import RANK_VALUES
# Import the shared validation error for the pure engine boundary.
from casino.errors import ValidationError

# Identify this module for state documents, payloads, and ledger audit rows.
GAME_ID = "pai_gow_poker"
# Retain only a small, bounded window of settled rounds for reload safety.
RECENT_ROUND_LIMIT = 10
# Advertise the single post-deal decision to generic frontends.
DECISIONS = ("set",)

# Encode the single joker with a compact, persistence-safe sentinel code.
JOKER_CODE = "XJ"
# Order the fifty-two natural ranks so the joker can enumerate completions.
_NATURAL_RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
# Order suits so joker flush completions can pick a matching suit.
_NATURAL_SUITS = ("clubs", "diamonds", "hearts", "spades")
# Name the five-card categories from high card up through five of a kind.
FIVE_CATEGORIES = (
    "high_card", "pair", "two_pair", "three_of_a_kind", "straight",
    "flush", "full_house", "four_of_a_kind", "straight_flush", "five_aces",
)
# Fix the five percent commission charged on winning even-money settlements.
COMMISSION_RATE = 0.05


# Report whether a coerced card token represents the wild joker.
def is_joker(card) -> bool:
    # Treat the sentinel string form and any explicit joker marker as the joker.
    return card == JOKER_CODE or (isinstance(card, str) and card.strip().upper() == JOKER_CODE)


# Build the ordered fifty-three-card Pai Gow deck as codes for deterministic shuffling.
def build_deck_codes() -> list[str]:
    # Emit every natural card code followed by the single joker sentinel.
    return [Card(rank, suit).code for suit in _NATURAL_SUITS for rank in _NATURAL_RANKS] + [JOKER_CODE]


# Normalize any card token into either a shared Card or the joker sentinel.
def normalize(card):
    # Preserve the joker sentinel untouched so the evaluator can special-case it.
    if is_joker(card):
        # Return the canonical joker code regardless of input spelling.
        return JOKER_CODE
    # Delegate every natural card to the shared coercion for consistent validation.
    return coerce_card(card)


# Return the display or persistence code for a normalized card token.
def card_code(card) -> str:
    # Emit the joker sentinel directly.
    if is_joker(card):
        return JOKER_CODE
    # Emit the shared compact code for natural cards.
    return coerce_card(card).code


# Score five natural cards on the shared category-and-tiebreak scale.
def _score_natural(cards) -> tuple:
    # Convert each card to its ace-high value for grouping and straight checks.
    values = sorted((RANK_VALUES[c.rank] for c in cards), reverse=True)
    # Count identical ranks to detect pairs, trips, and quads.
    counts = {}
    # Tally each rank value once.
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    # Detect a flush when every suit matches.
    is_flush = len({c.suit for c in cards}) == 1
    # Collect the distinct sorted values for straight detection.
    distinct = sorted(set(values))
    # Assume no straight until a run of five is confirmed.
    straight_high = None
    # Detect a natural five-value run.
    if len(distinct) == 5 and distinct[-1] - distinct[0] == 4:
        # Record the top card of the run.
        straight_high = distinct[-1]
    # Detect the ace-low wheel as a five-high straight.
    elif distinct == [2, 3, 4, 5, 14]:
        # Record the wheel as a five-high straight.
        straight_high = 5
    # Order the rank groups by count then value for stable tiebreaks.
    grouped = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))
    # Extract the group sizes to classify the hand shape.
    shape = sorted(counts.values(), reverse=True)
    # Extract the ranks in grouped order for tiebreak keys.
    ordered = tuple(rank for rank, _ in grouped)
    # Rank a straight flush above every made hand except five aces.
    if straight_high is not None and is_flush:
        return (8, (straight_high,))
    # Rank four of a kind by the quad then the kicker.
    if shape[0] == 4:
        return (7, ordered)
    # Rank a full house by the trips then the pair.
    if shape == [3, 2]:
        return (6, ordered)
    # Rank a flush by its five descending cards.
    if is_flush:
        return (5, tuple(values))
    # Rank a straight by its high card.
    if straight_high is not None:
        return (4, (straight_high,))
    # Rank trips by the set then the kickers.
    if shape[0] == 3:
        return (3, ordered)
    # Rank two pair by both pairs then the kicker.
    if shape == [2, 2, 1]:
        return (2, ordered)
    # Rank one pair by the pair then the kickers.
    if shape[0] == 2:
        return (1, ordered)
    # Rank the remaining hands purely by descending cards.
    return (0, tuple(values))


# Evaluate a five-card hand that may contain the wild joker.
def evaluate_five(cards) -> tuple:
    # Normalize every token so natural cards and the joker are handled uniformly.
    normalized = [normalize(c) for c in cards]
    # Separate the natural cards from the single optional joker.
    natural = [c for c in normalized if not is_joker(c)]
    # Reject malformed hands early so callers see a direct error.
    if len(normalized) != 5:
        raise ValueError("a five-card hand needs exactly five cards")
    # Score directly when no joker is present.
    if len(natural) == 5:
        return _score_natural(natural)
    # Recognize four natural aces plus the joker as the top-ranked five aces.
    if sum(1 for c in natural if c.rank == "A") == 4:
        return (9, (14,))
    # Track the best legal completion the bug rule allows.
    best = None
    # Enumerate every candidate rank and suit substitution for the joker.
    for rank in _NATURAL_RANKS:
        # Try each suit so flush completions can find a match.
        for suit in _NATURAL_SUITS:
            # Score the completed natural hand.
            score = _score_natural(natural + [Card(rank, suit)])
            # Allow the completion only when the bug acts as an ace or completes a straight or flush.
            legal = rank == "A" or score[0] in (4, 5, 8)
            # Skip completions that would use the bug as an ordinary wild card.
            if not legal:
                continue
            # Keep the strongest legal completion.
            if best is None or score > best:
                best = score
    # Fall back to the joker acting as a bare ace when nothing else is legal.
    return best if best is not None else _score_natural(natural + [Card("A", "spades")])


# Evaluate a two-card low hand where the joker plays as an ace.
def evaluate_two(cards) -> tuple:
    # Normalize both tokens for uniform handling.
    normalized = [normalize(c) for c in cards]
    # Reject malformed low hands early.
    if len(normalized) != 2:
        raise ValueError("a two-card hand needs exactly two cards")
    # Map the joker to an ace and read natural ranks directly.
    values = sorted((14 if is_joker(c) else RANK_VALUES[c.rank] for c in normalized), reverse=True)
    # Rank a matching pair above two unpaired cards.
    if values[0] == values[1]:
        return (1, tuple(values))
    # Rank unpaired cards by their descending values.
    return (0, tuple(values))


# Confirm a proposed split is legal because the high hand outranks the low hand.
def split_is_legal(high, low) -> bool:
    # A legal Pai Gow arrangement never sets the two-card hand above the five-card hand.
    return _compare_high_low(evaluate_five(high), evaluate_two(low)) >= 0


# Compare a five-card score against a two-card score on one ordered scale.
def _compare_high_low(high_score, low_score) -> int:
    # Promote both scores onto a shared axis so a two-card pair can never beat a made five-card hand.
    high_axis = _high_axis(high_score)
    # Map the two-card hand onto the same axis using pair-or-high-card only.
    low_axis = _low_axis(low_score)
    # Return the standard three-way comparison sign.
    return (high_axis > low_axis) - (high_axis < low_axis)


# Project a five-card score onto the cross-hand comparison axis.
def _high_axis(score) -> tuple:
    # A made five-card hand of pair or better always outranks any two-card hand.
    if score[0] >= 1:
        return (2, score)
    # A five-card high-card hand competes on its own descending ranks.
    return (0, score[1])


# Project a two-card score onto the cross-hand comparison axis.
def _low_axis(score) -> tuple:
    # A two-card pair sits above any five-card high-card hand but below any made five-card hand.
    if score[0] == 1:
        return (1, score[1])
    # A two-card high-card hand competes on its descending ranks.
    return (0, score[1])


# Compare two same-size hands, returning 1, 0, or -1.
def compare(a_score, b_score) -> int:
    # Reduce the tuple comparison to a stable three-way sign.
    return (a_score > b_score) - (a_score < b_score)


# Arrange seven cards by the standard house way, maximizing the legal high hand.
def set_house_way(seven):
    # Normalize all seven cards once for repeated evaluation.
    cards = [normalize(c) for c in seven]
    # Track the best legal split found so far.
    best = None
    # Try every two-card low hand, leaving the rest as the five-card high hand.
    for i in range(7):
        # Pair the first low-card index with every later index.
        for j in range(i + 1, 7):
            # Collect the two-card low hand.
            low = [cards[i], cards[j]]
            # Collect the remaining five cards as the high hand.
            high = [cards[k] for k in range(7) if k not in (i, j)]
            # Skip illegal arrangements where the low hand would outrank the high hand.
            if not split_is_legal(high, low):
                continue
            # Score both hands for comparison.
            candidate = (evaluate_five(high), evaluate_two(low))
            # Prefer the strongest high hand, breaking ties on the strongest low hand.
            if best is None or candidate > best[0]:
                best = (candidate, high, low)
    # Surface the chosen high and low hands with their scores.
    return {"high": best[1], "low": best[2], "high_score": best[0][0], "low_score": best[0][1]}


# Settle a fully set player hand against the house-way dealer hand.
def settle(player_high, player_low, dealer_seven, ante) -> dict:
    # Set the dealer with the deterministic house way.
    dealer = set_house_way(dealer_seven)
    # Score the player's chosen high and low hands.
    ph = evaluate_five(player_high)
    # Score the player's chosen low hand.
    pl = evaluate_two(player_low)
    # Compare the high hands, treating a tie as a dealer win by copy.
    high_cmp = compare(ph, dealer["high_score"])
    # Compare the low hands, treating a tie as a dealer win by copy.
    low_cmp = compare(pl, dealer["low_score"])
    # A player wins a hand only by strictly beating the dealer.
    player_high_wins = high_cmp > 0
    # A player wins the low hand only by strictly beating the dealer.
    player_low_wins = low_cmp > 0
    # Classify the round from the two hand results with copies going to the dealer.
    if player_high_wins and player_low_wins:
        # Winning both hands pays even money minus the house commission.
        outcome, payout = "win", ante * (1 + (1 - COMMISSION_RATE))
    elif not player_high_wins and not player_low_wins:
        # Losing or copying both hands forfeits the ante.
        outcome, payout = "loss", 0.0
    else:
        # Splitting the hands pushes the ante back untouched.
        outcome, payout = "push", ante
    # Return the settlement alongside the revealed dealer arrangement for display.
    return {
        "outcome": outcome,
        "payout": round(payout, 2),
        "commission_rate": COMMISSION_RATE,
        "high_win": player_high_wins,
        "low_win": player_low_wins,
        "dealer_high": [card_code(c) for c in dealer["high"]],
        "dealer_low": [card_code(c) for c in dealer["low"]],
    }


# ---------------------------------------------------------------------------
# Reload-safe round lifecycle used by the stateful service.
# ---------------------------------------------------------------------------


# Build the empty per-player document with one actionable slot and durable receipts.
def default_state() -> dict:
    # Return one active slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive ante before cards or state are created.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Pai Gow Poker ante must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        wager = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Pai Gow Poker ante must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge ledger amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Pai Gow Poker ante must be between 0.01 and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return wager


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter a route path.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"pgpoker_{digest[:24]}"


# Deal seven player and seven dealer cards from the fifty-three-card joker deck.
def deal_seven(*, seed=None, fixture=None) -> dict:
    # Read explicit focused-test fixtures before using entropy.
    if fixture is not None:
        # Normalize fixture player cards through the joker-aware coercion.
        player_cards = [card_code(normalize(card)) for card in fixture["player_cards"]]
        # Normalize fixture dealer cards through the joker-aware coercion.
        dealer_cards = [card_code(normalize(card)) for card in fixture["dealer_cards"]]
    # Deal a production or seeded test layout from one shuffled joker deck.
    else:
        # Build the ordered fifty-three-card deck of stable codes.
        deck = build_deck_codes()
        # Shuffle deterministically when a seed is injected, else with system entropy.
        generator = random.Random(seed) if seed is not None else random.SystemRandom()
        # Shuffle the independent list so no shared deck state is mutated.
        generator.shuffle(deck)
        # Deal seven player cards followed by seven dealer cards without replacement.
        player_cards = deck[0:7]
        # Deal the dealer cards after the player cards for deterministic tests.
        dealer_cards = deck[7:14]
    # Reject malformed fixtures that do not match the table layout.
    if len(player_cards) != 7 or len(dealer_cards) != 7:
        # Fail closed rather than producing partial public state.
        raise ValidationError("Pai Gow Poker requires seven player cards and seven dealer cards")
    # Combine every physical card for duplicate detection.
    all_cards = [*player_cards, *dealer_cards]
    # Reject duplicated physical cards before state is persisted.
    if len(set(all_cards)) != len(all_cards):
        # Surface an impossible table layout as a validation error.
        raise ValidationError("Pai Gow Poker cards must be dealt without replacement")
    # Return public player cards and private dealer cards in deterministic order.
    return {"player_cards": player_cards, "dealer_cards": dealer_cards}


# Normalize a two-card low-hand set decision into sorted card indices.
def normalize_set(value) -> tuple[int, int]:
    # Accept the auto-set sentinel so beginners can defer to the house way.
    if isinstance(value, str) and value.strip().lower() in ("house_way", "house-way", "auto"):
        # Signal the house-way auto-set path with a sentinel tuple.
        return (-1, -1)
    # Require a two-element list of distinct card positions otherwise.
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        # Keep the stable diagnostic suitable for the additive API contract.
        raise ValidationError("set must be two card indices or 'house_way'")
    # Reject booleans and non-integer positions before range checks.
    try:
        # Coerce both positions to integers.
        low = tuple(int(index) for index in value)
    # Translate malformed indices into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("set indices must be integers 0-6") from None
    # Reject positions outside the seven-card hand or duplicated positions.
    if any(index < 0 or index > 6 for index in low) or low[0] == low[1]:
        # Report the accepted position range and distinctness rule.
        raise ValidationError("set indices must be two distinct positions 0-6")
    # Return the low-hand positions in stable sorted order.
    return tuple(sorted(low))


# Build one reload-safe round after the ante is requested.
def create_round(player_id: str, wager, start_action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Normalize the ante at the pure engine boundary.
    amount = normalize_wager(wager)
    # Deal all cards up front so reloads cannot change the eventual showdown.
    layout = deal_seven(seed=seed, fixture=fixture)
    # Return JSON-compatible prepared state with dealer cards kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "wager": amount,  # Store the ante amount.
        "phase": "setting",  # Await one set decision before showdown.
        "player_cards": layout["player_cards"],  # Publish all seven player cards for setting.
        "_dealer_cards": layout["dealer_cards"],  # Persist dealer cards privately until showdown.
        "created_at": created_at,  # Record the deal time for history.
        "decision": None,  # Reserve the later set decision.
        "decision_action_id": None,  # Reserve settlement retry identity.
        "decision_fingerprint": None,  # Reserve the decision fingerprint.
        "ante_status": "pending",  # Require the service to ensure one ante debit.
        "settlement_status": "not_ready",  # Prevent settlement before the set decision.
    }


# Resolve a set decision by arranging both hands and settling the round.
def apply_set(round_state: dict, decision_action_id: str, low_indices, *, completed_at: str, request_fingerprint: str) -> dict:
    # Read the seven dealt player cards.
    seven = round_state["player_cards"]
    # Auto-arrange by the house way when the player defers, else honor the chosen split.
    if low_indices == (-1, -1):
        # Compute the deterministic house-way arrangement for the player.
        arranged = set_house_way(seven)
        # Record the player low hand and high hand codes.
        player_low = [card_code(c) for c in arranged["low"]]
        # Record the player high hand codes.
        player_high = [card_code(c) for c in arranged["high"]]
        # Note that the arrangement used the house way.
        used_house_way = True
    # Honor an explicit legal player split.
    else:
        # Split the seven cards into the chosen low hand and the remaining high hand.
        player_low = [seven[index] for index in low_indices]
        # Collect the five high-hand cards from the untouched positions.
        player_high = [seven[index] for index in range(7) if index not in low_indices]
        # Reject any arrangement where the two-card hand outranks the five-card hand.
        if not split_is_legal(player_high, player_low):
            # Fail closed so the low hand can never beat the high hand.
            raise ValidationError("the two-card hand may not outrank the five-card hand")
        # Note that the player chose the arrangement.
        used_house_way = False
    # Settle the arranged hands against the house-way dealer.
    result = settle(player_high, player_low, round_state["_dealer_cards"], round_state["wager"])
    # Record the terminal decision identity for replay safety.
    round_state["decision_action_id"] = decision_action_id
    # Record the decision fingerprint for conflicting-retry detection.
    round_state["decision_fingerprint"] = request_fingerprint
    # Record the resolved decision descriptor for history.
    round_state["decision"] = "house_way" if used_house_way else "custom"
    # Publish the player's chosen high hand.
    round_state["player_high"] = player_high
    # Publish the player's chosen low hand.
    round_state["player_low"] = player_low
    # Publish the revealed dealer high hand.
    round_state["dealer_high"] = result["dealer_high"]
    # Publish the revealed dealer low hand.
    round_state["dealer_low"] = result["dealer_low"]
    # Publish per-hand win flags for the receipt view.
    round_state["high_win"] = result["high_win"]
    # Publish the low-hand win flag for the receipt view.
    round_state["low_win"] = result["low_win"]
    # Publish the settlement outcome label.
    round_state["outcome"] = result["outcome"]
    # Store the returned-token payout owed on settlement.
    round_state["payout"] = result["payout"]
    # Store the commission rate applied to winning bets.
    round_state["commission_rate"] = result["commission_rate"]
    # Record the settlement time for history.
    round_state["completed_at"] = completed_at
    # Move the round to its terminal phase.
    round_state["phase"] = "settled"
    # Require the service to ensure one returned-token credit when owed.
    round_state["settlement_status"] = "pending"
    # Return the settled round for archival and settlement.
    return round_state


# Find one round by the client deal action id across active and recent state.
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


# Find whether an action identity already belongs to any retained command.
def action_owner(state: dict, action_id: str):
    # Search every active and retained round for either action stage.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Inspect each retained round in turn.
    for item in candidates:
        # Skip empty active slots.
        if not item:
            # Continue to the next retained round.
            continue
        # Match the deal action before the optional decision action.
        if item.get("start_action_id") == action_id:
            # Report the deal stage and owning round.
            return item, "deal"
        # Match a committed set decision action.
        if item.get("decision_action_id") == action_id:
            # Report the decision stage and owning round.
            return item, "decision"
    # Return no owner when the action id remains unused in retained state.
    return None


# Move a terminal round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Normalize the optional active slot before reading its identifier.
    active_round = state.get("active_round") or {}
    # Clear the actionable slot only when it contains this exact round.
    if active_round.get("round_id") == round_state.get("round_id"):
        # Prevent further decisions against the terminal round.
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
    # Exclude hidden dealer cards and internal fingerprints from public responses.
    private_fields = {"_dealer_cards", "request_fingerprint", "decision_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide unrevealed dealer cards.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
