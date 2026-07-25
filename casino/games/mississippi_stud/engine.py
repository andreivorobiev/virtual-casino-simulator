"""Deterministic Mississippi Stud rules for GitHub issue #143.

Mississippi Stud is a solo five-card stud where the player builds one hand from two hole cards and three
community cards and there is no dealer. The player posts an ante, then across three betting streets, before
each community card is exposed, either folds and forfeits every wager already made or bets one to three
times the ante. The completed five-card hand is paid on the total wagered amount: a pair of jacks or better
pays even money and richer hands pay up to five hundred to one for a royal flush, a pair of sixes through
tens returns every wager as a push, and a pair of fives or lower or no pair loses everything. Because low
pairs and non-pairs lose the whole stake, the disciplined strategy keeps the game house-positive, near a
4.9 percent edge on the ante under optimal play. All amounts are play tokens with no cash value.

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
GAME_ID = "mississippi_stud"
# Offer the two documented player choices at each betting street.
DECISIONS = ("bet", "fold")
# Bound each street bet to one, two, or three times the ante.
BET_MULTIPLIERS = (1, 2, 3)
# Run exactly three betting streets before the showdown.
STREETS = 3
# Bound reload-safe history so one player document cannot grow without limit.
RECENT_ROUND_LIMIT = 20
# Pay each winning hand tier its to-one multiplier applied to the total amount wagered.
PAYTABLE = {
    "royal_flush": 500,  # A royal flush pays five hundred to one.
    "straight_flush": 100,  # A straight flush pays one hundred to one.
    "four_of_a_kind": 40,  # Four of a kind pays forty to one.
    "full_house": 10,  # A full house pays ten to one.
    "flush": 6,  # A flush pays six to one.
    "straight": 4,  # A straight pays four to one.
    "three_of_a_kind": 3,  # Three of a kind pays three to one.
    "two_pair": 2,  # Two pair pays two to one.
    "pair_jacks_plus": 1,  # A pair of jacks or better pays even money.
}
# Read the lowest jacks-or-better pair rank once for the paytable classification.
_JACKS = RANK_VALUES["J"]
# Read the lowest pushing pair rank once for the paytable classification.
_SIX = RANK_VALUES["6"]


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive ante before cards or state are created.
def normalize_ante(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Mississippi Stud ante must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        ante = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Mississippi Stud ante must be a positive play-token amount") from None
    # Reject out-of-range, non-finite, and overlarge ledger amounts, leaving headroom for three-times bets.
    if ante < 0.01 or ante > 10_000 or not math.isfinite(ante):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Mississippi Stud ante must be between 0.01 and 10000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return ante


# Normalize the one-to-three-times street bet multiplier.
def normalize_multiplier(value) -> int:
    # Reject booleans and non-integers before range checks.
    if isinstance(value, bool) or not isinstance(value, int):
        # Keep malformed multipliers out of the wager math.
        raise ValidationError("Mississippi Stud bet multiplier must be 1, 2, or 3")
    # Require one of the three documented bet sizes.
    if value not in BET_MULTIPLIERS:
        # Report the accepted bet sizes.
        raise ValidationError("Mississippi Stud bet multiplier must be 1, 2, or 3")
    # Return the validated multiplier.
    return value


# Normalize the only player decision made at each street.
def normalize_decision(value) -> str:
    # Accept only strings so mappings and numeric aliases cannot become decisions.
    decision = value.strip().lower() if isinstance(value, str) else ""
    # Reject anything outside the two documented actions.
    if decision not in DECISIONS:
        # Keep the stable diagnostic suitable for the additive API contract.
        raise ValidationError("decision must be bet or fold")
    # Return the canonical lower-case decision.
    return decision


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter a route path.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"msstud_{digest[:24]}"


# Normalize fixture or shuffled cards into the Mississippi Stud layout.
def deal_layout(*, seed=None, fixture=None) -> dict:
    # Read explicit focused-test fixtures before using entropy.
    if fixture is not None:
        # Normalize the two fixture hole cards through shared validation.
        hole_cards = [coerce_card(card).code for card in fixture["hole_cards"]]
        # Normalize the three fixture community cards through shared validation.
        community_cards = [coerce_card(card).code for card in fixture["community_cards"]]
    # Deal a production or seeded test layout from one shuffled deck.
    else:
        # Shuffle through the shared primitive using secure entropy unless a seed is injected.
        cards = shuffled_deck(seed=seed)
        # Deal two hole cards and three community cards without replacement.
        hole_cards = [card.code for card in cards[0:2]]
        # Deal the three community cards after the hole cards for deterministic tests.
        community_cards = [card.code for card in cards[2:5]]
    # Reject malformed fixtures that do not match the table layout.
    if len(hole_cards) != 2 or len(community_cards) != 3:
        # Fail closed rather than producing partial public state.
        raise ValidationError("Mississippi Stud requires two hole cards and three community cards")
    # Combine every physical card for duplicate detection.
    all_cards = [*hole_cards, *community_cards]
    # Reject duplicated physical cards before state is persisted.
    if len(set(all_cards)) != len(all_cards):
        # Surface an impossible table layout as a validation error.
        raise ValidationError("Mississippi Stud cards must be dealt without replacement")
    # Return the public hole cards and the private community cards.
    return {"hole_cards": hole_cards, "community_cards": community_cards}


# Classify one completed five-card hand into its Mississippi Stud paytable outcome.
def classify_final(cards) -> tuple[str, str, float]:
    # Evaluate the standard five-card poker rank.
    rank = evaluate_five(cards)
    # Treat an ace-high straight flush as the distinct royal-flush paytable row.
    if rank.name == "straight_flush" and rank.tiebreak == (14,):
        # Return the royal-flush tier as a win.
        return "royal_flush", "win", PAYTABLE["royal_flush"]
    # Return every listed made hand above a pair as a win.
    if rank.name in PAYTABLE:
        # Return the matched paytable tier as a win.
        return rank.name, "win", PAYTABLE[rank.name]
    # Split one-pair hands by rank into the jacks-plus, push, and losing bands.
    if rank.name == "one_pair":
        # Read the pair rank for banding.
        pair_rank = rank.tiebreak[0]
        # A pair of jacks or better wins even money.
        if pair_rank >= _JACKS:
            # Return the jacks-plus win tier.
            return "pair_jacks_plus", "win", PAYTABLE["pair_jacks_plus"]
        # A pair of sixes through tens returns every wager as a push.
        if pair_rank >= _SIX:
            # Return the pushing pair tier.
            return "pair_6_to_10", "push", 0.0
        # A pair of fives or lower loses the whole stake.
        return "pair_2_to_5", "lose", 0.0
    # Any non-pair hand loses the whole stake.
    return "high_card", "lose", 0.0


# Build one reload-safe round after the ante is requested.
def create_round(player_id: str, ante, start_action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Normalize the ante at the pure engine boundary.
    ante_amount = normalize_ante(ante)
    # Deal all cards up front so reloads cannot change the eventual showdown.
    layout = deal_layout(seed=seed, fixture=fixture)
    # Return JSON-compatible prepared state with the community cards kept private until revealed.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "ante": ante_amount,  # Store the ante amount.
        "phase": "decision",  # Await one bet-or-fold decision at the current street.
        "street": 1,  # Begin at the first of three betting streets.
        "hole_cards": layout["hole_cards"],  # Publish the two hole cards.
        "community_revealed": [],  # Publish community cards only as each street resolves.
        "_community": layout["community_cards"],  # Persist the three community cards privately.
        "bets": {},  # Record each committed street bet by street index.
        "total_wager": ante_amount,  # Track the running total of ante and street bets.
        "opening_status": "pending",  # Require the service to ensure one ante debit.
        "bet_status": "not_ready",  # Prevent a street debit before a bet is prepared.
        "settlement_status": "not_ready",  # Prevent credits before terminal evaluation.
        "pending_street": None,  # Reserve the street index of a prepared but uncommitted bet.
        "pending_action_id": None,  # Reserve the retry identity of a prepared bet.
        "pending_fingerprint": None,  # Reserve the fingerprint of a prepared bet.
        "pending_multiplier": None,  # Reserve the multiplier of a prepared bet.
        "payout": 0.0,  # Reserve total returned play tokens.
        "net": None,  # Reserve final net movement.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Prepare a street bet before the service commits the street debit.
def prepare_bet(round_state: dict, action_id: str, multiplier: int, *, request_fingerprint: str) -> dict:
    # Treat an exact repeated prepare as idempotent.
    if round_state.get("bet_status") == "pending" and round_state.get("pending_action_id") == action_id:
        # Reject a changed multiplier for the already-prepared bet.
        if round_state.get("pending_fingerprint") != request_fingerprint:
            # Preserve the original prepared bet.
            raise ConflictError("Mississippi Stud bet was already prepared by another action")
        # Return the prepared round unchanged.
        return round_state
    # Require the decision phase and no other prepared bet.
    if round_state.get("phase") != "decision" or round_state.get("bet_status") == "pending":
        # Reject stale or overlapping bets.
        raise ConflictError("Mississippi Stud round cannot accept a bet in its current phase")
    # Store the street being bet.
    round_state["pending_street"] = round_state["street"]
    # Store the prepared bet retry identity.
    round_state["pending_action_id"] = action_id
    # Store the prepared bet fingerprint.
    round_state["pending_fingerprint"] = request_fingerprint
    # Store the prepared bet multiplier.
    round_state["pending_multiplier"] = multiplier
    # Compute the prepared street wager from the ante and multiplier.
    round_state["pending_wager"] = round(round_state["ante"] * multiplier, 2)
    # Require the service to commit or recover the street debit.
    round_state["bet_status"] = "pending"
    # Return the mutated round for persistence.
    return round_state


# Restore a street preparation when its debit did not commit.
def reset_uncommitted_bet(round_state: dict) -> dict:
    # Clear a prepared bet whose debit never committed.
    if round_state.get("bet_status") == "pending":
        # Remove the uncommitted prepared bet fields.
        for field in ("pending_street", "pending_action_id", "pending_fingerprint", "pending_multiplier", "pending_wager"):
            # Drop each reserved field.
            round_state.pop(field, None)
        # Mark the round ready for a fresh bet at the same street.
        round_state["bet_status"] = "not_ready"
    # Return the recovered active round.
    return round_state


# Advance one committed street bet: record it, reveal its community card, and settle after the third street.
def advance_after_bet(round_state: dict, *, completed_at: str) -> dict:
    # Require a committed street debit before advancing.
    if round_state.get("bet_status") != "complete":
        # Fail closed rather than advancing a free bet.
        raise ConflictError("Mississippi Stud street bet is not committed")
    # Read the street that was just bet.
    street = round_state["pending_street"]
    # Record the committed street bet under its street index.
    round_state["bets"][str(street)] = {"street": street, "multiplier": round_state["pending_multiplier"], "wager": round_state["pending_wager"], "action_id": round_state["pending_action_id"]}
    # Add the street wager to the running total.
    round_state["total_wager"] = round(round_state["total_wager"] + round_state["pending_wager"], 2)
    # Reveal the community card belonging to this street.
    round_state["community_revealed"] = [coerce_card(card).code for card in round_state["_community"][:street]]
    # Clear the prepared-bet reservation now that it is recorded.
    for field in ("pending_street", "pending_action_id", "pending_fingerprint", "pending_multiplier", "pending_wager"):
        # Drop each reserved field.
        round_state.pop(field, None)
    # Reset the bet status for the next street or terminal settlement.
    round_state["bet_status"] = "not_ready"
    # Settle after the third street or move to the next street.
    if street >= STREETS:
        # Resolve the completed five-card hand.
        _settle(round_state, completed_at=completed_at)
    else:
        # Advance to the next betting street.
        round_state["street"] = street + 1
    # Return the mutated round for persistence.
    return round_state


# Resolve the completed hand and compute the paytable settlement.
def _settle(round_state: dict, *, completed_at: str) -> None:
    # Reveal every community card at the showdown.
    community = [coerce_card(card).code for card in round_state["_community"]]
    # Publish the full community board.
    round_state["community_revealed"] = community
    # Classify the completed five-card hand.
    tier, result, multiplier = classify_final([*round_state["hole_cards"], *community])
    # Compute the returned tokens: a win pays the multiplier plus the returned stake, a push returns the stake, a loss returns nothing.
    payout = round(round_state["total_wager"] * (multiplier + 1), 2) if result == "win" else round_state["total_wager"] if result == "push" else 0.0
    # Store the final hand tier for display.
    round_state["hand_tier"] = tier
    # Store the paytable result classification.
    round_state["result"] = result
    # Store the applied to-one multiplier for transparency.
    round_state["multiplier"] = multiplier
    # Store aggregate returned play tokens.
    round_state["payout"] = payout
    # Store net movement after every debit.
    round_state["net"] = round(payout - round_state["total_wager"], 2)
    # Mark deterministic evaluation complete.
    round_state["phase"] = "settled"
    # Classify the player-facing outcome from the settlement result.
    round_state["outcome"] = {"win": "win", "push": "push", "lose": "lose"}[result]
    # Require one credit only when returned tokens are due.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Remove the private community cards now that their public equivalent exists.
    round_state.pop("_community", None)


# Resolve a fold decision, forfeiting every wager made so far.
def fold_round(round_state: dict, action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Treat an exact repeated fold as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed terminal decision.
        if round_state.get("outcome") != "folded" or round_state.get("fold_action_id") != action_id or round_state.get("fold_fingerprint") != request_fingerprint:
            # Preserve the original terminal state.
            raise ConflictError("Mississippi Stud round was already settled by another action")
        # Return the already-folded round.
        return round_state
    # Require the decision phase without a prepared bet for folding.
    if round_state.get("phase") != "decision" or round_state.get("bet_status") == "pending":
        # Reject stale actions after a bet is prepared.
        raise ConflictError("Mississippi Stud round cannot be folded in its current phase")
    # Store the terminal fold action identity.
    round_state["fold_action_id"] = action_id
    # Store the semantic fingerprint for retry checks.
    round_state["fold_fingerprint"] = request_fingerprint
    # Reveal the community cards up to the street where the player folded, for transparency.
    round_state["community_revealed"] = [coerce_card(card).code for card in round_state["_community"][:round_state["street"] - 1]]
    # Classify the folded result.
    round_state["outcome"] = "folded"
    # A fold forfeits every wager already made.
    round_state["result"] = "lose"
    # Store zero returned play tokens.
    round_state["payout"] = 0.0
    # Store net loss of the total wagered so far.
    round_state["net"] = -round_state["total_wager"]
    # Mark the round terminal.
    round_state["phase"] = "settled"
    # No returned-token credit is due for a fold.
    round_state["settlement_status"] = "complete"
    # Reset the bet status because no bet remains outstanding.
    round_state["bet_status"] = "not_ready"
    # Remove the private community cards because the fold forfeits the hand.
    round_state.pop("_community", None)
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


# Report whether a decision action id already committed a bet or fold on a round.
def decision_committed(round_state: dict, action_id: str) -> bool:
    # Match any recorded street bet action id.
    if any(bet.get("action_id") == action_id for bet in round_state.get("bets", {}).values()):
        # Report that the action already committed a street bet.
        return True
    # Match a terminal fold action id.
    return round_state.get("fold_action_id") == action_id


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
    private_fields = {"_community", "request_fingerprint", "pending_fingerprint", "fold_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide unrevealed community cards.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
