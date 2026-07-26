"""Deterministic Four Card Poker rules for GitHub issue #141.

Four Card Poker deals the player five cards to build their best four-card hand and the dealer six cards to
build the dealer's best four-card hand, giving the dealer a structural edge in place of any qualification
rule. The player posts an ante and an optional Aces Up side bet, sees their cards, then either folds or
raises with a Play wager of one to three times the ante. On a Play the best four-card hands are compared:
a player win pays the ante and Play even money and ties go to the player, while a loss takes both. Because
the dealer draws from six cards to the player's five it wins about two thirds of showdowns, so the
disciplined strategy folds every high-card hand and plays only a pair or better, leaving a house edge near
4.5 percent under optimal play. An Ante Bonus pays on the player's three of a kind or better regardless of
the dealer, and the independent Aces Up bet pays on a pair of aces or better whether the player folds or
plays. Four-card hand ranking places three of a kind above a flush and a straight because trips are scarcer
with four cards. All amounts are play tokens with no cash value.

Requirements used: CARD-001, LEDGER-005, LEDGER-006, SESSION-005, TOKEN-001.
"""

# Import hashing so authenticated deal actions derive stable route ids.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math
# Import combinations so best-four selection can scan every four-card subset.
from itertools import combinations

# Import shared card primitives for normalization and shuffling.
from casino.core.cards import coerce_card, shuffled_deck
# Import the shared ace-high rank values used for comparisons.
from casino.core.poker import RANK_VALUES
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger row owned by this game.
GAME_ID = "four_card_poker"
# Offer the two documented player decisions after the deal.
DECISIONS = ("play", "fold")
# Bound the Play raise to one, two, or three times the ante.
PLAY_MULTIPLIERS = (1, 2, 3)
# Bound reload-safe history so one player document cannot grow without limit.
RECENT_ROUND_LIMIT = 20
# Name the four-card categories in ascending comparison strength.
FOUR_CARD_CATEGORIES = (
    "high_card",  # Category zero has no grouped ranks.
    "one_pair",  # Category one has one pair.
    "two_pair",  # Category two has two pairs.
    "straight",  # Category three has four consecutive ranks.
    "flush",  # Category four has four cards of one suit.
    "three_of_a_kind",  # Category five has one triplet; trips beat a flush with four cards.
    "straight_flush",  # Category six has a four-card straight in one suit.
    "four_of_a_kind",  # Category seven has four equal ranks.
)
# Pay the Ante Bonus on the player's own hand regardless of the dealer, expressed as to-one winnings.
ANTE_BONUS_MULTIPLIERS = {"four_of_a_kind": 25, "straight_flush": 20, "three_of_a_kind": 2}
# Pay the independent Aces Up side bet on a pair of aces or better, expressed as to-one winnings.
ACES_UP_MULTIPLIERS = {"four_of_a_kind": 50, "straight_flush": 40, "three_of_a_kind": 9, "flush": 5, "straight": 4, "two_pair": 3, "pair_of_aces": 1}


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive wager amount before cards or state are created.
def _normalize_amount(value, *, label: str, minimum: float) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError(f"Four Card Poker {label} must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        amount = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError(f"Four Card Poker {label} must be a positive play-token amount") from None
    # Reject out-of-range, non-finite, and overlarge ledger amounts.
    if amount < minimum or amount > 100_000 or not math.isfinite(amount):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError(f"Four Card Poker {label} must be between {minimum} and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return amount


# Normalize the required ante wager.
def normalize_ante(value) -> float:
    # Require at least the shared ledger minimum for the ante.
    return _normalize_amount(value, label="ante", minimum=0.01)


# Normalize the optional Aces Up side bet, allowing zero to decline it.
def normalize_aces_up(value) -> float:
    # Treat a missing side bet as declined.
    if value is None:
        # Report a zero Aces Up bet.
        return 0.0
    # Accept an explicit zero to decline the side bet.
    if value == 0 and not isinstance(value, bool):
        # Report the declined side bet.
        return 0.0
    # Otherwise require a positive bounded side bet.
    return _normalize_amount(value, label="Aces Up bet", minimum=0.01)


# Normalize the Play raise multiplier chosen after the deal.
def normalize_multiplier(value) -> int:
    # Reject booleans and non-integers before range checks.
    if isinstance(value, bool) or not isinstance(value, int):
        # Keep malformed multipliers out of the wager math.
        raise ValidationError("Four Card Poker play multiplier must be 1, 2, or 3")
    # Require one of the three documented raise sizes.
    if value not in PLAY_MULTIPLIERS:
        # Report the accepted raise sizes.
        raise ValidationError("Four Card Poker play multiplier must be 1, 2, or 3")
    # Return the validated multiplier.
    return value


# Normalize the only player decision made after the deal.
def normalize_decision(value) -> str:
    # Accept only strings so mappings and numeric aliases cannot become decisions.
    decision = value.strip().lower() if isinstance(value, str) else ""
    # Reject anything outside the two documented actions.
    if decision not in DECISIONS:
        # Keep the stable diagnostic suitable for the additive API contract.
        raise ValidationError("decision must be play or fold")
    # Return the canonical lower-case decision.
    return decision


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter a route path.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"fourcp_{digest[:24]}"


# Return the four-card straight high value, or None when the ranks are not consecutive.
def _four_straight(values: list[int]):
    # Remove duplicate ranks because pairs cannot contribute twice to a straight.
    unique = sorted(set(values))
    # Treat ace as low only for the four-high wheel pattern.
    if unique == [2, 3, 4, 14]:
        # Rank the wheel below every other straight.
        return 4
    # Recognize four unique ranks spanning exactly three values.
    if len(unique) == 4 and unique[-1] - unique[0] == 3:
        # Return the highest rank for straight comparisons.
        return unique[-1]
    # Report that this rank set is not a four-card straight.
    return None


# Evaluate exactly four cards using Four Card Poker ordering, where trips beat a flush.
def evaluate_four(cards) -> dict:
    # Normalize caller values through the shared card primitive.
    normalized = [coerce_card(card) for card in cards]
    # Require exactly four cards for the focused evaluator.
    if len(normalized) != 4:
        # Reject incomplete or oversized hands with a stable error.
        raise ValueError("evaluate_four requires exactly four cards")
    # Convert ranks to numeric values for category comparisons.
    values = [RANK_VALUES[card.rank] for card in normalized]
    # Count each rank to identify pairs, trips, and quads.
    counts = {value: values.count(value) for value in set(values)}
    # Sort count groups by multiplicity and then rank, both strongest first.
    groups = sorted(((count, value) for value, count in counts.items()), reverse=True)
    # Recognize a flush when every card shares one suit.
    flush = len({card.suit for card in normalized}) == 1
    # Recognize a straight and retain its comparison high card.
    straight_high = _four_straight(values)
    # Rank four equal cards above every other category.
    if groups[0][0] == 4:
        # Compare quads by their rank alone.
        return _rank("four_of_a_kind", (groups[0][1],), normalized)
    # Rank a four-card straight flush below quads.
    if flush and straight_high is not None:
        # Compare straight flushes by their high card.
        return _rank("straight_flush", (straight_high,), normalized)
    # Rank three equal cards above a flush and a straight.
    if groups[0][0] == 3:
        # Compare the trip rank followed by the single kicker.
        kicker = next(value for value in values if value != groups[0][1])
        # Return the trips comparison tuple.
        return _rank("three_of_a_kind", (groups[0][1], kicker), normalized)
    # Rank a flush above a straight and two pair.
    if flush:
        # Compare flushes by all four ranks in descending order.
        return _rank("flush", tuple(sorted(values, reverse=True)), normalized)
    # Rank a straight above two pair.
    if straight_high is not None:
        # Compare straights by their high card.
        return _rank("straight", (straight_high,), normalized)
    # Rank two distinct pairs above one pair.
    if groups[0][0] == 2 and groups[1][0] == 2:
        # Sort both pairs strongest first.
        pairs = sorted((groups[0][1], groups[1][1]), reverse=True)
        # Return both pairs as the comparison tuple.
        return _rank("two_pair", (pairs[0], pairs[1]), normalized)
    # Rank one pair above a high-card hand.
    if groups[0][0] == 2:
        # Sort the two unpaired kickers strongest first.
        kickers = sorted((value for value in values if value != groups[0][1]), reverse=True)
        # Return the pair followed by both kickers.
        return _rank("one_pair", (groups[0][1], *kickers), normalized)
    # Rank an unpaired hand by all four descending card values.
    return _rank("high_card", tuple(sorted(values, reverse=True)), normalized)


# Build one comparable four-card hand result record.
def _rank(name: str, tiebreak: tuple, cards: list) -> dict:
    # Return the category index, stable name, tiebreak tuple, and the card codes.
    return {"category": FOUR_CARD_CATEGORIES.index(name), "name": name, "tiebreak": list(tiebreak), "cards": [card.code for card in cards]}


# Return the comparison key for a four-card hand result.
def comparison_key(rank: dict) -> tuple:
    # Prefix the tie breakers with the category strength.
    return (rank["category"], *rank["tiebreak"])


# Select the strongest four-card hand from a five- or six-card holding.
def best_four(cards) -> dict:
    # Normalize once so every four-card subset shares validated values.
    normalized = [coerce_card(card) for card in cards]
    # Evaluate every four-card subset and keep the strongest by comparison key.
    return max((evaluate_four(subset) for subset in combinations(normalized, 4)), key=comparison_key)


# Report the Aces Up qualification name for a four-card hand, or None when it does not qualify.
def aces_up_name(rank: dict):
    # Any two pair or better qualifies at its own category.
    if rank["category"] >= FOUR_CARD_CATEGORIES.index("two_pair"):
        # Return the hand category as the Aces Up paytable key.
        return rank["name"]
    # A single pair qualifies only when it is a pair of aces.
    if rank["name"] == "one_pair" and rank["tiebreak"][0] == RANK_VALUES["A"]:
        # Return the distinct pair-of-aces paytable key.
        return "pair_of_aces"
    # No lesser hand qualifies for the Aces Up side bet.
    return None


# Normalize fixture or shuffled cards into the Four Card Poker layout.
def deal_layout(*, seed=None, fixture=None) -> dict:
    # Read explicit focused-test fixtures before using entropy.
    if fixture is not None:
        # Normalize the five fixture player cards through shared validation.
        player_cards = [coerce_card(card).code for card in fixture["player_cards"]]
        # Normalize the six fixture dealer cards through shared validation.
        dealer_cards = [coerce_card(card).code for card in fixture["dealer_cards"]]
    # Deal a production or seeded test layout from one shuffled deck.
    else:
        # Shuffle through the shared primitive using secure entropy unless a seed is injected.
        cards = shuffled_deck(seed=seed)
        # Deal five player cards and six dealer cards without replacement.
        player_cards = [card.code for card in cards[0:5]]
        # Deal the dealer cards after the player cards for deterministic tests.
        dealer_cards = [card.code for card in cards[5:11]]
    # Reject malformed fixtures that do not match the table layout.
    if len(player_cards) != 5 or len(dealer_cards) != 6:
        # Fail closed rather than producing partial public state.
        raise ValidationError("Four Card Poker requires five player cards and six dealer cards")
    # Combine every physical card for duplicate detection.
    all_cards = [*player_cards, *dealer_cards]
    # Reject duplicated physical cards before state is persisted.
    if len(set(all_cards)) != len(all_cards):
        # Surface an impossible table layout as a validation error.
        raise ValidationError("Four Card Poker cards must be dealt without replacement")
    # Return the public and private layout pieces in deterministic order.
    return {"player_cards": player_cards, "dealer_cards": dealer_cards}


# Build one reload-safe round after the ante is requested.
def create_round(player_id: str, ante, aces_up, start_action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Normalize both opening wagers at the pure engine boundary.
    ante_amount = normalize_ante(ante)
    # Normalize the optional Aces Up side bet.
    aces_up_amount = normalize_aces_up(aces_up)
    # Deal all cards up front so reloads cannot change the eventual showdown.
    layout = deal_layout(seed=seed, fixture=fixture)
    # Return JSON-compatible prepared state with the dealer cards kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "ante": ante_amount,  # Store the ante amount.
        "aces_up": aces_up_amount,  # Store the optional Aces Up side bet.
        "phase": "decision",  # Await one play-or-fold decision after the deal.
        "player_cards": layout["player_cards"],  # Publish the five player cards.
        "_dealer_cards": layout["dealer_cards"],  # Persist the six dealer cards privately until showdown.
        "decision": None,  # Reserve the later play-or-fold decision.
        "play_multiplier": None,  # Reserve the chosen raise size.
        "play_wager": 0.0,  # Reserve the derived play wager.
        "decision_action_id": None,  # Reserve settlement retry identity.
        "opening_status": "pending",  # Require the service to ensure one opening debit.
        "play_status": "not_ready",  # Prevent play debits before the decision.
        "settlement_status": "not_ready",  # Prevent credits before terminal evaluation.
        "payout": 0.0,  # Reserve total returned play tokens.
        "net": None,  # Reserve final net movement.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Compute the Aces Up settlement component for the player's best four-card hand.
def _aces_up_credit(aces_up_amount: float, player_rank: dict) -> float:
    # Skip the component when the side bet was declined.
    if aces_up_amount <= 0:
        # Report a zero credit for a declined side bet.
        return 0.0
    # Read the Aces Up qualification name for the player's hand.
    name = aces_up_name(player_rank)
    # Read the qualifying multiplier, or zero when the hand does not qualify.
    multiplier = ACES_UP_MULTIPLIERS.get(name, 0) if name else 0
    # Return the total Aces Up return including the returned stake on a qualifying hand.
    return round(aces_up_amount * (multiplier + 1), 2) if multiplier else 0.0


# Prepare a play decision before the service commits the play debit.
def prepare_play(round_state: dict, decision_action_id: str, multiplier: int, *, request_fingerprint: str) -> dict:
    # Treat an exact repeated prepare as idempotent.
    if round_state.get("phase") == "playing":
        # Reject changed action identities or raise sizes for the already-prepared play.
        if round_state.get("decision_action_id") != decision_action_id or round_state.get("decision_fingerprint") != request_fingerprint:
            # Preserve the original decision and ledger identity.
            raise ConflictError("Four Card Poker play was already prepared by another action")
        # Return the prepared round unchanged.
        return round_state
    # Require the decision phase for a new play.
    if round_state.get("phase") != "decision":
        # Reject stale actions after settlement.
        raise ConflictError("Four Card Poker round cannot accept a play in its current phase")
    # Store the player decision.
    round_state["decision"] = "play"
    # Store the chosen raise multiplier.
    round_state["play_multiplier"] = multiplier
    # Store the settlement action identity for retry-safe play debit and payout.
    round_state["decision_action_id"] = decision_action_id
    # Store the semantic fingerprint for conflict detection.
    round_state["decision_fingerprint"] = request_fingerprint
    # Calculate the required play wager from the ante and multiplier.
    round_state["play_wager"] = round(round_state["ante"] * multiplier, 2)
    # Move into an intermediate state that can recover a committed play debit.
    round_state["phase"] = "playing"
    # Require the service to commit or recover the play debit.
    round_state["play_status"] = "pending"
    # Keep settlement locked until the play debit is proven.
    round_state["settlement_status"] = "not_ready"
    # Return the mutated round for persistence.
    return round_state


# Restore a play preparation when its debit did not commit.
def reset_uncommitted_play(round_state: dict) -> dict:
    # Return only prepared-play rounds to the decision state.
    if round_state.get("phase") == "playing":
        # Remove the uncommitted decision identity.
        round_state.pop("decision_action_id", None)
        # Remove the uncommitted decision fingerprint.
        round_state.pop("decision_fingerprint", None)
        # Reset the derived play wager and multiplier.
        round_state["play_wager"] = 0.0
        # Reset the chosen multiplier.
        round_state["play_multiplier"] = None
        # Reset the visible decision.
        round_state["decision"] = None
        # Return the round to the play-or-fold choice.
        round_state["phase"] = "decision"
        # Mark play settlement unavailable again.
        round_state["play_status"] = "not_ready"
    # Return the recovered active round.
    return round_state


# Resolve a committed play into a terminal showdown without touching balances.
def resolve_playing_round(round_state: dict, *, completed_at: str) -> dict:
    # Treat repeated resolution as an idempotent read.
    if round_state.get("phase") == "settled":
        # Return the stable terminal state.
        return round_state
    # Require the intermediate play state after play-debit proof exists.
    if round_state.get("phase") != "playing":
        # Reject stale or corrupt transitions explicitly.
        raise ConflictError("Four Card Poker round is not ready for showdown")
    # Require play-debit proof before any payout can be calculated.
    if round_state.get("play_status") != "complete":
        # Fail closed rather than settling a free play.
        raise ConflictError("Four Card Poker play wager is not committed")
    # Select the player's best four-card hand from their five cards.
    player_rank = best_four(round_state["player_cards"])
    # Read the private dealer cards persisted at deal time.
    dealer_cards = [coerce_card(card).code for card in round_state.get("_dealer_cards", [])]
    # Select the dealer's best four-card hand from their six cards.
    dealer_rank = best_four(dealer_cards)
    # Compare the two best hands with no dealer qualification.
    comparison = (comparison_key(player_rank) > comparison_key(dealer_rank)) - (comparison_key(player_rank) < comparison_key(dealer_rank))
    # Resolve the public outcome, awarding ties to the player as the six-card dealer already holds the structural edge.
    outcome = "player_win" if comparison >= 0 else "dealer_win"
    # Double the ante on a win and return none on a loss.
    ante_credit = round(round_state["ante"] * 2, 2) if outcome == "player_win" else 0.0
    # Settle the play wager the same way as the ante.
    play_credit = round(round_state["play_wager"] * 2, 2) if outcome == "player_win" else 0.0
    # Pay the Ante Bonus on the player's own hand regardless of the dealer, as added winnings.
    ante_bonus_credit = round(round_state["ante"] * ANTE_BONUS_MULTIPLIERS.get(player_rank["name"], 0), 2)
    # Settle the independent Aces Up side bet on the player's best four-card hand.
    aces_up_credit = _aces_up_credit(round_state["aces_up"], player_rank)
    # Calculate one aggregate returned-token credit.
    payout = round(ante_credit + play_credit + ante_bonus_credit + aces_up_credit, 2)
    # Calculate the total amount already debited across the opening bets and the play.
    total_wagered = round(round_state["ante"] + round_state["aces_up"] + round_state["play_wager"], 2)
    # Publish the formerly private dealer cards and the two best hands.
    _publish_result(round_state, dealer_cards, player_rank, dealer_rank, outcome)
    # Store returned-credit components for audit and UI presentation.
    round_state["ante_credit"] = ante_credit
    # Store the play returned-credit component.
    round_state["play_credit"] = play_credit
    # Store the ante-bonus returned-credit component.
    round_state["ante_bonus_credit"] = ante_bonus_credit
    # Store the Aces Up returned-credit component.
    round_state["aces_up_credit"] = aces_up_credit
    # Store aggregate returned play tokens.
    round_state["payout"] = payout
    # Store net movement after every debit.
    round_state["net"] = round(payout - total_wagered, 2)
    # Mark deterministic evaluation complete.
    round_state["phase"] = "settled"
    # Require one credit only when returned tokens are due.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Return the same mutable round for service persistence.
    return round_state


# Resolve a fold decision, settling only the independent Aces Up side bet.
def fold_round(round_state: dict, decision_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat an exact repeated fold as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed terminal decision.
        if round_state.get("decision") != "fold" or round_state.get("decision_action_id") != decision_action_id or round_state.get("decision_fingerprint") != request_fingerprint:
            # Preserve the original terminal state.
            raise ConflictError("Four Card Poker round was already settled by another action")
        # Return the already-folded round.
        return round_state
    # Require the decision phase for folding.
    if round_state.get("phase") != "decision":
        # Reject stale actions after a play is prepared.
        raise ConflictError("Four Card Poker round cannot be folded in its current phase")
    # Select the player's best four-card hand for the Aces Up settlement.
    player_rank = best_four(round_state["player_cards"])
    # Settle only the independent Aces Up side bet on a fold.
    aces_up_credit = _aces_up_credit(round_state["aces_up"], player_rank)
    # Store the player decision.
    round_state["decision"] = "fold"
    # Store the terminal action identity.
    round_state["decision_action_id"] = decision_action_id
    # Store the semantic fingerprint for retry checks.
    round_state["decision_fingerprint"] = request_fingerprint
    # Publish the player's best hand without revealing the folded dealer cards.
    round_state["player_hand"] = player_rank
    # Classify the folded result.
    round_state["outcome"] = "folded"
    # Store the ante and play components as forfeited on a fold.
    round_state["ante_credit"] = 0.0
    # No play wager exists on a fold.
    round_state["play_credit"] = 0.0
    # No ante bonus is paid on a fold.
    round_state["ante_bonus_credit"] = 0.0
    # Settle the independent Aces Up side bet even on a fold.
    round_state["aces_up_credit"] = aces_up_credit
    # Store the aggregate returned play tokens, which is only the Aces Up return.
    round_state["payout"] = aces_up_credit
    # Store net movement after the forfeited ante and any Aces Up return.
    round_state["net"] = round(aces_up_credit - round(round_state["ante"] + round_state["aces_up"], 2), 2)
    # Mark the round terminal.
    round_state["phase"] = "settled"
    # No play debit is created for folds.
    round_state["play_status"] = "not_ready"
    # Require a credit only when the Aces Up side bet won.
    round_state["settlement_status"] = "pending" if aces_up_credit else "complete"
    # Remove the private dealer cards because the fold forfeits the showdown.
    round_state.pop("_dealer_cards", None)
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Return the same mutable round for service persistence.
    return round_state


# Publish the revealed dealer cards, both best hands, and the outcome onto the round.
def _publish_result(round_state: dict, dealer_cards: list, player_rank: dict, dealer_rank: dict, outcome: str) -> None:
    # Publish the dealer's six cards after the showdown.
    round_state["dealer_cards"] = dealer_cards
    # Publish the player's best four-card hand.
    round_state["player_hand"] = player_rank
    # Publish the dealer's best four-card hand.
    round_state["dealer_hand"] = dealer_rank
    # Store the player-facing outcome.
    round_state["outcome"] = outcome
    # Remove the private dealer cards now that their public equivalent exists.
    round_state.pop("_dealer_cards", None)


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


# Find whether an action identity already belongs to any retained command.
def action_owner(state: dict, action_id: str):
    # Search every active and retained round for either action stage.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Inspect each retained round for a matching stage.
    for item in candidates:
        # Skip empty active slots.
        if not item:
            # Continue to the next retained round.
            continue
        # Match the deal action before the optional decision action.
        if item.get("start_action_id") == action_id:
            # Report the deal stage and owning round.
            return item, "deal"
        # Match a committed or prepared play/fold decision action.
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
    # Exclude hidden cards and internal fingerprints from public responses.
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
