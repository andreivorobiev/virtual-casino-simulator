"""Deterministic Teen Patti Practice rules for GitHub issue #150.

Teen Patti is a three-card poker played against the dealer. The player antes, sees three cards, then folds
or makes a fixed Play wager equal to the ante. The dealer qualifies with a queen-high hand or better; if the
dealer does not qualify the ante pays even money and the Play pushes, and if the dealer qualifies the best
three-card hand wins both wagers even money with ties pushing. Teen Patti ranks a trail highest, then a pure
sequence, then a sequence, then a colour, a pair, and a high card, so a straight outranks a flush because
runs are scarcer with three cards. A Bonus pays on the player's own trail, pure sequence, or sequence
regardless of the dealer. The dealer's structural qualification keeps the game house-positive near a 3.4
percent edge on the ante under optimal play. All amounts are play tokens with no cash value.

Requirements used: CARD-001, LEDGER-005, LEDGER-006, SESSION-005, TOKEN-001.
"""

# Import hashing so authenticated deal actions derive stable route ids.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math
# Import Counter for three-card rank grouping.
from collections import Counter

# Import shared card primitives for normalization and shuffling.
from casino.core.cards import coerce_card, shuffled_deck
# Import the shared ace-high rank values used for comparisons.
from casino.core.poker import RANK_VALUES
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger row owned by this game.
GAME_ID = "teen_patti"
# Offer the two documented player decisions after the deal.
DECISIONS = ("play", "fold")
# Bound reload-safe history so one player document cannot grow without limit.
RECENT_ROUND_LIMIT = 20
# Name the three-card categories in ascending comparison strength; a sequence beats a colour.
THREE_CARD_CATEGORIES = ("high_card", "pair", "color", "sequence", "pure_sequence", "trail")
# Pay the Bonus on the player's own strong hand regardless of the dealer, as to-one winnings.
BONUS_MULTIPLIERS = {"trail": 5, "pure_sequence": 4, "sequence": 1}
# Read the queen threshold once for the dealer qualification rule.
_QUEEN = RANK_VALUES["Q"]


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive ante before cards or state are created.
def normalize_ante(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Teen Patti ante must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        ante = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Teen Patti ante must be a positive play-token amount") from None
    # Reject out-of-range, non-finite, and overlarge ledger amounts, leaving headroom for the play wager.
    if ante < 0.01 or ante > 50_000 or not math.isfinite(ante):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Teen Patti ante must be between 0.01 and 50000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return ante


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
    return f"teenp_{digest[:24]}"


# Evaluate one three-card Teen Patti hand into a comparable rank record.
def evaluate_three(cards) -> dict:
    # Normalize caller values through the shared card primitive.
    normalized = [coerce_card(card) for card in cards]
    # Require exactly three cards for the evaluator.
    if len(normalized) != 3:
        # Reject incomplete or oversized hands with a stable error.
        raise ValueError("evaluate_three requires exactly three cards")
    # Read the descending rank values.
    values = sorted((RANK_VALUES[card.rank] for card in normalized), reverse=True)
    # Read the distinct rank values.
    unique = sorted(set(values))
    # Recognize a colour when all three cards share a suit.
    flush = len({card.suit for card in normalized}) == 1
    # Recognize the ace-two-three lowest run and the ordinary three-in-a-row run.
    sequence_high = 3 if set(unique) == {14, 2, 3} else unique[-1] if len(unique) == 3 and unique[-1] - unique[0] == 2 else None
    # Count how many cards share each rank.
    counts = Counter(values)
    # Rank three equal cards as the top trail.
    if 3 in counts.values():
        # Compare trails by their shared rank.
        return _rank("trail", (values[0],), normalized)
    # Rank a suited run as a pure sequence below a trail.
    if sequence_high is not None and flush:
        # Compare pure sequences by their run high card.
        return _rank("pure_sequence", (sequence_high,), normalized)
    # Rank an unsuited run as a sequence below a pure sequence.
    if sequence_high is not None:
        # Compare sequences by their run high card.
        return _rank("sequence", (sequence_high,), normalized)
    # Rank a colour below a sequence.
    if flush:
        # Compare colours by all three descending ranks.
        return _rank("color", tuple(values), normalized)
    # Rank a pair below a colour.
    if 2 in counts.values():
        # Read the paired rank and the single kicker.
        pair = next(value for value, count in counts.items() if count == 2)
        # Read the unpaired kicker.
        kicker = next(value for value in values if value != pair)
        # Compare pairs by the pair rank then the kicker.
        return _rank("pair", (pair, kicker), normalized)
    # Rank a high-card hand by all three descending ranks.
    return _rank("high_card", tuple(values), normalized)


# Build one comparable three-card hand result record.
def _rank(name: str, tiebreak: tuple, cards: list) -> dict:
    # Return the category index, stable name, tiebreak tuple, and the card codes.
    return {"category": THREE_CARD_CATEGORIES.index(name), "name": name, "tiebreak": list(tiebreak), "cards": [card.code for card in cards]}


# Return the comparison key for a three-card hand result.
def comparison_key(rank: dict) -> tuple:
    # Prefix the tie breakers with the category strength.
    return (rank["category"], *rank["tiebreak"])


# Determine whether the dealer's three-card hand qualifies to play.
def dealer_qualifies(dealer_rank: dict) -> bool:
    # Any pair or better always qualifies.
    if dealer_rank["category"] >= THREE_CARD_CATEGORIES.index("pair"):
        # Report that the dealer plays.
        return True
    # A high-card dealer qualifies only with a queen or better.
    return dealer_rank["tiebreak"][0] >= _QUEEN


# Normalize fixture or shuffled cards into the Teen Patti layout.
def deal_layout(*, seed=None, fixture=None) -> dict:
    # Read explicit focused-test fixtures before using entropy.
    if fixture is not None:
        # Normalize the three fixture player cards through shared validation.
        player_cards = [coerce_card(card).code for card in fixture["player_cards"]]
        # Normalize the three fixture dealer cards through shared validation.
        dealer_cards = [coerce_card(card).code for card in fixture["dealer_cards"]]
    # Deal a production or seeded test layout from one shuffled deck.
    else:
        # Shuffle through the shared primitive using secure entropy unless a seed is injected.
        cards = shuffled_deck(seed=seed)
        # Deal three player cards and three dealer cards without replacement.
        player_cards = [card.code for card in cards[0:3]]
        # Deal the dealer cards after the player cards for deterministic tests.
        dealer_cards = [card.code for card in cards[3:6]]
    # Reject malformed fixtures that do not match the table layout.
    if len(player_cards) != 3 or len(dealer_cards) != 3:
        # Fail closed rather than producing partial public state.
        raise ValidationError("Teen Patti requires three player cards and three dealer cards")
    # Combine every physical card for duplicate detection.
    all_cards = [*player_cards, *dealer_cards]
    # Reject duplicated physical cards before state is persisted.
    if len(set(all_cards)) != len(all_cards):
        # Surface an impossible table layout as a validation error.
        raise ValidationError("Teen Patti cards must be dealt without replacement")
    # Return the public player cards and the private dealer cards.
    return {"player_cards": player_cards, "dealer_cards": dealer_cards}


# Build one reload-safe round after the ante is requested.
def create_round(player_id: str, ante, start_action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Normalize the ante at the pure engine boundary.
    ante_amount = normalize_ante(ante)
    # Deal all cards up front so reloads cannot change the eventual showdown.
    layout = deal_layout(seed=seed, fixture=fixture)
    # Return JSON-compatible prepared state with the dealer cards kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "ante": ante_amount,  # Store the ante amount.
        "phase": "decision",  # Await one play-or-fold decision after the deal.
        "player_cards": layout["player_cards"],  # Publish the three player cards.
        "_dealer_cards": layout["dealer_cards"],  # Persist the three dealer cards privately until showdown.
        "decision": None,  # Reserve the later play-or-fold decision.
        "play_wager": 0.0,  # Reserve the fixed play wager.
        "decision_action_id": None,  # Reserve settlement retry identity.
        "opening_status": "pending",  # Require the service to ensure one ante debit.
        "play_status": "not_ready",  # Prevent play debits before the decision.
        "settlement_status": "not_ready",  # Prevent credits before terminal evaluation.
        "payout": 0.0,  # Reserve total returned play tokens.
        "net": None,  # Reserve final net movement.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Prepare a play decision before the service commits the play debit.
def prepare_play(round_state: dict, decision_action_id: str, *, request_fingerprint: str) -> dict:
    # Treat an exact repeated prepare as idempotent.
    if round_state.get("phase") == "playing":
        # Reject changed action identities for the already-prepared play.
        if round_state.get("decision_action_id") != decision_action_id or round_state.get("decision_fingerprint") != request_fingerprint:
            # Preserve the original decision and ledger identity.
            raise ConflictError("Teen Patti play was already prepared by another action")
        # Return the prepared round unchanged.
        return round_state
    # Require the decision phase for a new play.
    if round_state.get("phase") != "decision":
        # Reject stale actions after settlement.
        raise ConflictError("Teen Patti round cannot accept a play in its current phase")
    # Store the player decision.
    round_state["decision"] = "play"
    # Store the settlement action identity for retry-safe play debit and payout.
    round_state["decision_action_id"] = decision_action_id
    # Store the semantic fingerprint for conflict detection.
    round_state["decision_fingerprint"] = request_fingerprint
    # Set the fixed play wager equal to the ante.
    round_state["play_wager"] = round_state["ante"]
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
        # Reset the derived play wager.
        round_state["play_wager"] = 0.0
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
        raise ConflictError("Teen Patti round is not ready for showdown")
    # Require play-debit proof before any payout can be calculated.
    if round_state.get("play_status") != "complete":
        # Fail closed rather than settling a free play.
        raise ConflictError("Teen Patti play wager is not committed")
    # Evaluate the player's three-card hand.
    player_rank = evaluate_three(round_state["player_cards"])
    # Read the private dealer cards persisted at deal time.
    dealer_cards = [coerce_card(card).code for card in round_state.get("_dealer_cards", [])]
    # Evaluate the dealer's three-card hand.
    dealer_rank = evaluate_three(dealer_cards)
    # Determine whether the dealer qualifies to play.
    qualifies = dealer_qualifies(dealer_rank)
    # Compare the two hands.
    comparison = (comparison_key(player_rank) > comparison_key(dealer_rank)) - (comparison_key(player_rank) < comparison_key(dealer_rank))
    # Resolve the public outcome from qualification and the comparison.
    if not qualifies:
        # A non-qualifying dealer pays the ante and pushes the play.
        outcome = "dealer_not_qualified"
    elif comparison > 0:
        # The player beats a qualifying dealer.
        outcome = "player_win"
    elif comparison == 0:
        # Equal hands push both wagers.
        outcome = "push"
    else:
        # The dealer beats the player.
        outcome = "dealer_win"
    # Return the ante at even money on a win or non-qualify, push it on a tie, and lose it otherwise.
    ante_credit = round(round_state["ante"] * 2, 2) if outcome in ("player_win", "dealer_not_qualified") else round_state["ante"] if outcome == "push" else 0.0
    # Push the play on a non-qualify, pay it even money on a win, push it on a tie, and lose it otherwise.
    play_credit = round(round_state["play_wager"] * 2, 2) if outcome == "player_win" else round_state["play_wager"] if outcome in ("dealer_not_qualified", "push") else 0.0
    # Pay the Bonus on the player's own strong hand regardless of the dealer.
    bonus_credit = round(round_state["ante"] * BONUS_MULTIPLIERS.get(player_rank["name"], 0), 2)
    # Calculate one aggregate returned-token credit.
    payout = round(ante_credit + play_credit + bonus_credit, 2)
    # Calculate the total amount already debited across the ante and play.
    total_wagered = round(round_state["ante"] + round_state["play_wager"], 2)
    # Publish the revealed dealer cards and both hands.
    round_state["dealer_cards"] = dealer_cards
    # Publish the player's evaluated hand.
    round_state["player_hand"] = player_rank
    # Publish the dealer's evaluated hand.
    round_state["dealer_hand"] = dealer_rank
    # Store dealer qualification for transparency.
    round_state["dealer_qualifies"] = qualifies
    # Store the player-facing outcome.
    round_state["outcome"] = outcome
    # Store returned-credit components for audit and UI presentation.
    round_state["ante_credit"] = ante_credit
    # Store the play returned-credit component.
    round_state["play_credit"] = play_credit
    # Store the Bonus returned-credit component.
    round_state["bonus_credit"] = bonus_credit
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
    # Remove the private dealer cards now that their public equivalent exists.
    round_state.pop("_dealer_cards", None)
    # Return the same mutable round for service persistence.
    return round_state


# Resolve a fold decision, forfeiting the ante.
def fold_round(round_state: dict, decision_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat an exact repeated fold as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed terminal decision.
        if round_state.get("outcome") != "folded" or round_state.get("decision_action_id") != decision_action_id or round_state.get("decision_fingerprint") != request_fingerprint:
            # Preserve the original terminal state.
            raise ConflictError("Teen Patti round was already settled by another action")
        # Return the already-folded round.
        return round_state
    # Require the decision phase for folding.
    if round_state.get("phase") != "decision":
        # Reject stale actions after a play is prepared.
        raise ConflictError("Teen Patti round cannot be folded in its current phase")
    # Store the player decision.
    round_state["decision"] = "fold"
    # Store the terminal action identity.
    round_state["decision_action_id"] = decision_action_id
    # Store the semantic fingerprint for retry checks.
    round_state["decision_fingerprint"] = request_fingerprint
    # Publish the player's own hand without revealing the folded dealer cards.
    round_state["player_hand"] = evaluate_three(round_state["player_cards"])
    # Classify the folded result.
    round_state["outcome"] = "folded"
    # Store the forfeited ante with no returned credit.
    round_state["payout"] = 0.0
    # Store net loss of the ante.
    round_state["net"] = -round_state["ante"]
    # Mark the round terminal.
    round_state["phase"] = "settled"
    # No play debit is created for folds.
    round_state["play_status"] = "not_ready"
    # No returned-token credit is due for folds.
    round_state["settlement_status"] = "complete"
    # Remove the private dealer cards because the fold forfeits the showdown.
    round_state.pop("_dealer_cards", None)
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
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
