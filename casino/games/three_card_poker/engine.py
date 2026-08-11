# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure deterministic Three Card Poker rules for GitHub issue #93.

Requirements: CARD-001, LEDGER-005, LEDGER-006, and LEDGER-007.
"""

# Import immutable result records for deterministic hand comparison.
from dataclasses import dataclass
# Import finite-number validation for public play-token wagers.
import math

# Import only shared card construction and normalization primitives from issue #96.
from casino.core.cards import Card, RANKS, coerce_card, create_deck, shuffle_cards
# Import stable domain errors for invalid round transitions.
from casino.errors import ConflictError, NotFoundError, ValidationError

# Identify state documents, routes, and ledger records owned by this game.
GAME_ID = "three_card_poker"
# Retain a bounded reload-safe list of completed rounds.
ROUND_HISTORY_LIMIT = 20
# Limit each wager component to the same conservative range used by accepted game contracts.
MAX_WAGER = 100000.0
# Map canonical card ranks to ace-high comparison values.
RANK_VALUES = {rank: value for value, rank in enumerate(RANKS, start=2)}
# Name three-card categories in ascending comparison order.
CATEGORY_NAMES = (
    "high_card",  # Category zero has no grouped ranks.
    "pair",  # Category one contains exactly one pair.
    "flush",  # Three suited cards rank below a straight in Three Card Poker.
    "straight",  # Three consecutive ranks outrank a flush.
    "three_of_a_kind",  # Three equal ranks outrank a straight.
    "straight_flush",  # Three suited consecutive ranks are strongest.
)
# Publish the chosen Ante Bonus A profit multipliers.
ANTE_BONUS = {
    "straight_flush": 5,  # Pay five units of profit for a straight flush.
    "three_of_a_kind": 4,  # Pay four units of profit for three of a kind.
    "straight": 1,  # Pay one unit of profit for a straight.
}
# Publish the chosen Pair Plus C profit multipliers.
PAIR_PLUS = {
    "straight_flush": 40,  # Pay forty units of profit for a straight flush.
    "three_of_a_kind": 30,  # Pay thirty units of profit for three of a kind.
    "straight": 6,  # Pay six units of profit for a straight.
    "flush": 3,  # Pay three units of profit for a flush.
    "pair": 1,  # Pay one unit of profit for a pair.
}


# Store one immutable three-card evaluation result.
@dataclass(frozen=True)
class ThreeCardRank:  # Define the immutable evaluated-hand result.
    # Store the ascending category strength.
    category: int
    # Store the stable machine-readable category name.
    name: str
    # Store category-specific tie breakers from strongest to weakest.
    tiebreak: tuple[int, ...]
    # Store the exact normalized cards producing this result.
    cards: tuple[Card, ...]

    # Expose one deterministic tuple for winner comparison.
    @property
    def comparison_key(self) -> tuple[int, ...]:  # Expose the complete winner key.
        # Prefix the tie breakers with category strength.
        return (self.category, *self.tiebreak)


# Build a fresh player-scoped state document.
def default_state() -> dict:
    # Return only JSON-shaped values suitable for either storage provider.
    return {
        "rounds": {},  # Store retained rounds by stable server identifier.
        "round_order": [],  # Preserve deterministic creation order.
        "requests": {},  # Bind client ids to command fingerprints.
        "ledger_actions": {},  # Record committed deterministic ledger actions.
    }


# Return the fixed public table configuration.
def public_rules() -> dict:
    # Detach paytable dictionaries so callers cannot mutate module constants.
    return {
        "dealer_qualifying_rank": "Q",  # Qualify queen-high or stronger hands.
        "play_wager_multiplier": 1,  # Require a Play wager equal to Ante.
        "ante_bonus": dict(ANTE_BONUS),  # Expose Ante Bonus A profit odds.
        "pair_plus": dict(PAIR_PLUS),  # Expose Pair Plus C profit odds.
    }


# Normalize one required or optional play-token amount.
def normalize_wager(value, field: str, *, allow_zero: bool = False) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Raise a stable validation message without echoing caller input.
        raise ValidationError(f"{field} must be a valid play-token amount")
    # Convert supported numeric input before applying rounded ledger precision.
    try:
        # Preserve the raw numeric sign and bound for strict validation.
        numeric = float(value)
    # Translate malformed values into a public domain error.
    except (TypeError, ValueError):
        # Suppress conversion details that could vary by Python version.
        raise ValidationError(f"{field} must be a valid play-token amount") from None
    # Reject non-finite raw values and values outside the documented range.
    if not math.isfinite(numeric) or numeric < 0 or numeric > MAX_WAGER:
        # Describe the accepted boundary consistently.
        qualifier = "zero or a positive" if allow_zero else "a positive"
        # Raise before cards, state, or ledger intents are created.
        raise ValidationError(f"{field} must be {qualifier} play-token amount up to {int(MAX_WAGER)}")
    # Round once so replay fingerprints match committed ledger amounts.
    amount = round(numeric, 2)
    # Reject values that round to zero when this component is required.
    if amount == 0 and not allow_zero:
        # Keep sub-cent Ante values away from zero-value ledger movement.
        raise ValidationError(f"{field} must be a positive play-token amount up to {int(MAX_WAGER)}")
    # Return the normalized two-decimal amount.
    return amount


# Normalize required Ante and optional Pair Plus values together.
def normalize_bets(ante, pair_plus=None) -> tuple[float, float]:
    # Require a strictly positive Ante.
    normalized_ante = normalize_wager(ante, "ante")
    # Treat an omitted Pair Plus value as zero.
    normalized_pair_plus = normalize_wager(0 if pair_plus is None else pair_plus, "pair_plus", allow_zero=True)
    # Return the stable values used by state and retry fingerprints.
    return normalized_ante, normalized_pair_plus


# Return the high card for a three-card straight or None when not consecutive.
def _straight_high(values: list[int]):
    # Remove duplicate ranks because pairs cannot form a straight.
    unique = sorted(set(values))
    # Treat ace-deuce-trey as the lowest Three Card Poker straight.
    if unique == [2, 3, 14]:
        # Rank the wheel as three-high.
        return 3
    # Recognize every other three-rank consecutive run, including queen-king-ace.
    if len(unique) == 3 and unique[-1] - unique[0] == 2:
        # Return its highest rank for comparisons.
        return unique[-1]
    # Report that the ranks do not form a straight.
    return None


# Evaluate exactly three cards under Three Card Poker ordering.
def evaluate_three(cards) -> ThreeCardRank:
    # Normalize every supported card representation through CARD-001.
    normalized = tuple(coerce_card(card) for card in cards)
    # Require exactly three cards at the game boundary.
    if len(normalized) != 3:
        # Keep this evaluator distinct from shared five-to-seven-card poker.
        raise ValueError("evaluate_three requires exactly three cards")
    # Reject impossible duplicate physical cards in fixtures or persisted state.
    if len({card.code for card in normalized}) != 3:
        # Fail closed instead of evaluating a malformed deal.
        raise ValueError("evaluate_three requires three distinct cards")
    # Convert ranks to numeric values for category and kicker comparisons.
    values = [RANK_VALUES[card.rank] for card in normalized]
    # Count each rank to identify a pair or three of a kind.
    counts = {value: values.count(value) for value in set(values)}
    # Sort groups by multiplicity and rank, strongest first.
    groups = sorted(((count, value) for value, count in counts.items()), reverse=True)
    # Recognize a flush when all three suits match.
    flush = len({card.suit for card in normalized}) == 1
    # Recognize a straight with ace-low normalization.
    straight_high = _straight_high(values)
    # Rank a straight flush above every other category.
    if flush and straight_high is not None:
        # Return the straight high card as its only tie breaker.
        return ThreeCardRank(5, CATEGORY_NAMES[5], (straight_high,), normalized)
    # Rank three equal cards immediately below a straight flush.
    if groups[0][0] == 3:
        # Compare trip rank directly.
        return ThreeCardRank(4, CATEGORY_NAMES[4], (groups[0][1],), normalized)
    # Rank a straight above a flush under Three Card Poker rules.
    if straight_high is not None:
        # Preserve the normalized high rank.
        return ThreeCardRank(3, CATEGORY_NAMES[3], (straight_high,), normalized)
    # Rank a flush by all descending card values.
    if flush:
        # Preserve every potential kicker.
        return ThreeCardRank(2, CATEGORY_NAMES[2], tuple(sorted(values, reverse=True)), normalized)
    # Rank one pair above an unpaired high-card hand.
    if groups[0][0] == 2:
        # Read the paired rank from the leading group.
        pair_rank = groups[0][1]
        # Find the only unpaired kicker.
        kicker = next(value for value in values if value != pair_rank)
        # Compare pair first and kicker second.
        return ThreeCardRank(1, CATEGORY_NAMES[1], (pair_rank, kicker), normalized)
    # Rank an unpaired hand by descending cards.
    return ThreeCardRank(0, CATEGORY_NAMES[0], tuple(sorted(values, reverse=True)), normalized)


# Convert one evaluated rank into a JSON-compatible public shape.
def rank_payload(rank: ThreeCardRank) -> dict:
    # Expose only comparison metadata, not duplicate card objects.
    return {
        "category": rank.category,  # Preserve numeric ordering for clients.
        "name": rank.name,  # Preserve the stable localization key.
        "tiebreak": list(rank.tiebreak),  # Convert the immutable tuple to JSON.
    }


# Report whether the dealer qualifies with queen-high or better.
def dealer_qualifies(rank: ThreeCardRank) -> bool:
    # Every pair or stronger category automatically qualifies.
    if rank.category > 0:
        # Return the qualifying result directly.
        return True
    # Require queen or stronger as the highest high-card tie breaker.
    return bool(rank.tiebreak and rank.tiebreak[0] >= RANK_VALUES["Q"])


# Reject a new deal while another round still needs a decision or recovery.
def require_no_active_round(state: dict) -> None:
    # Inspect every retained round because a crash may leave ledger work pending.
    for round_item in state.get("rounds", {}).values():
        # Treat decision and prepared ledger phases as active.
        if round_item.get("phase") in {"decision", "ledger_pending"}:
            # Require completion before another initial debit.
            raise ConflictError("Finish the active Three Card Poker round before dealing again")


# Build one deterministic ledger instruction for the service adapter.
def ledger_intent(action_id: str, client_action_id: str, direction: str, amount: float, transaction_type: str, round_item: dict, stage: str) -> dict:
    # Return every audit field required by repository policy.
    return {
        "action_id": action_id,  # Provide the game-owned idempotency key.
        "direction": direction,  # Restrict movement to debit or credit.
        "amount": round(float(amount), 2),  # Match ledger precision.
        "transaction_type": transaction_type,  # Identify Admin-visible movement.
        "player_id": round_item["player_id"],  # Bind the session player.
        "game": GAME_ID,  # Bind this game.
        "round_id": round_item["round_id"],  # Bind one stable round.
        "details": {  # Store structured audit and replay dimensions.
            "three_card_poker_action_id": action_id,  # Support ledger replay scans.
            "client_action_id": client_action_id,  # Preserve the public retry id.
            "stage": stage,  # Distinguish initial, Play, and payout movement.
            "ante": round_item["ante"],  # Preserve the Ante audit dimension.
            "pair_plus": round_item["pair_plus"],  # Preserve optional Pair Plus.
        },
    }


# Store one round and prune only old round bodies from public history.
def store_round(state: dict, round_item: dict) -> None:
    # Store the round by its stable identifier.
    state.setdefault("rounds", {})[round_item["round_id"]] = round_item
    # Append the identifier to creation order.
    state.setdefault("round_order", []).append(round_item["round_id"])
    # Remove oldest round bodies beyond the reload-history limit.
    while len(state["round_order"]) > ROUND_HISTORY_LIMIT:
        # Remove the oldest identifier from display order.
        oldest = state["round_order"].pop(0)
        # Remove its body while retaining request fingerprints to prevent duplicate reuse.
        state["rounds"].pop(oldest, None)


# Deal one decision-ready round and prepare its aggregate initial debit.
def start_round(state: dict, player_id: str, ante, pair_plus, request_id: str, *, seed=None, round_id: str, created_at: str, deck=None) -> dict:
    # Prevent overlapping active wagers for one authenticated player.
    require_no_active_round(state)
    # Normalize both wager components before dealing.
    normalized_ante, normalized_pair_plus = normalize_bets(ante, pair_plus)
    # Use an explicit deck only for pure focused tests.
    cards = [coerce_card(card) for card in deck] if deck is not None else shuffle_cards(create_deck(), seed=seed)
    # Require enough unique cards for one complete table deal.
    if len(cards) < 6 or len({card.code for card in cards[:6]}) != 6:
        # Reject malformed injected or persisted card plans.
        raise ValidationError("Three Card Poker requires six distinct deal cards")
    # Deal the player's three cards before the dealer's three cards.
    player_cards = tuple(cards[:3])
    # Retain the dealer cards privately until the decision settles.
    dealer_cards = tuple(cards[3:6])
    # Evaluate both hands now so retries never redraw or change an outcome.
    player_rank = evaluate_three(player_cards)
    # Evaluate the private dealer hand through the same local rules.
    dealer_rank = evaluate_three(dealer_cards)
    # Build the complete prepared round before any ledger movement.
    round_item = {
        "round_id": round_id,  # Store the stable server round identifier.
        "player_id": player_id,  # Bind state to the resolved session player.
        "deal_request_id": request_id,  # Bind the public retry key.
        "decision_action_id": None,  # Reserve the terminal action key.
        "phase": "decision",  # Await one Play or Fold decision.
        "decision": None,  # Record no decision before the player acts.
        "ante": normalized_ante,  # Persist the required Ante.
        "pair_plus": normalized_pair_plus,  # Persist optional Pair Plus.
        "total_initial_wager": round(normalized_ante + normalized_pair_plus, 2),  # Aggregate the initial debit.
        "play_wager": 0.0,  # Add the matching wager only after Play.
        "total_wager": round(normalized_ante + normalized_pair_plus, 2),  # Track all committed stake.
        "player_hand": [card.code for card in player_cards],  # Expose player cards immediately.
        "dealer_hand": [card.code for card in dealer_cards],  # Persist private dealer cards for reload.
        "player_rank": rank_payload(player_rank),  # Persist deterministic player evaluation.
        "dealer_rank": rank_payload(dealer_rank),  # Persist private dealer evaluation.
        "dealer_qualifies": None,  # Resolve qualification only at settlement.
        "outcome": None,  # Resolve the table outcome only at settlement.
        "total_payout": 0.0,  # Store the eventual aggregate credit.
        "payout_breakdown": {  # Reserve transparent settlement components.
            "ante_play_return": 0.0,  # Reserve the main wager return.
            "ante_bonus": 0.0,  # Reserve Ante Bonus profit.
            "pair_plus_return": 0.0,  # Reserve Pair Plus stake and profit return.
        },
        "net": None,  # Compute net only after the terminal decision.
        "created_at": created_at,  # Persist the injected creation timestamp.
        "completed_at": None,  # Reserve the settlement timestamp.
        "ledger_intents": [],  # Persist ordered replay-safe wallet instructions.
    }
    # Build the deterministic initial movement identifier.
    initial_action_id = f"tcp:{round_id}:{request_id}:initial-debit"
    # Prepare one debit covering Ante plus optional Pair Plus.
    round_item["ledger_intents"].append(ledger_intent(initial_action_id, request_id, "debit", round_item["total_initial_wager"], "THREE_CARD_POKER_INITIAL_DEBIT", round_item, "initial_wager"))
    # Store the prepared round before the service persists and reconciles it.
    store_round(state, round_item)
    # Return the mutable round owned by this state document.
    return round_item


# Resolve a retained round without leaking cross-player existence.
def get_round(state: dict, round_id: str) -> dict:
    # Read the round only from this authenticated player's document.
    round_item = state.get("rounds", {}).get(round_id)
    # Reject missing or pruned identifiers consistently.
    if round_item is None:
        # Use a not-found error suitable for cross-session privacy.
        raise NotFoundError("Three Card Poker round was not found")
    # Return the retained mutable round.
    return round_item


# Calculate one Play settlement under fixed table and side-bet rules.
def _settle_play(round_item: dict) -> None:
    # Reconstruct comparison keys from persisted JSON rank payloads.
    player_key = (round_item["player_rank"]["category"], *round_item["player_rank"]["tiebreak"])
    # Reconstruct the dealer comparison key identically.
    dealer_key = (round_item["dealer_rank"]["category"], *round_item["dealer_rank"]["tiebreak"])
    # Re-evaluate dealer qualification from the persisted hand for one canonical rule path.
    qualifies = dealer_qualifies(evaluate_three(round_item["dealer_hand"]))
    # Publish dealer qualification after the player commits to Play.
    round_item["dealer_qualifies"] = qualifies
    # Return Ante at even money and push Play when the dealer does not qualify.
    if not qualifies:
        # Distinguish the qualification outcome for localization and evidence.
        round_item["outcome"] = "dealer_not_qualified"
        # Return two Antes for the Ante and one Ante for the pushed Play wager.
        main_return = round(round_item["ante"] * 3, 2)
    # Pay both Ante and Play at even money when the player wins.
    elif player_key > dealer_key:
        # Record the qualifying player win.
        round_item["outcome"] = "player_win"
        # Return stake plus equal profit for both main wagers.
        main_return = round(round_item["ante"] * 4, 2)
    # Push both main wagers on an exact hand tie.
    elif player_key == dealer_key:
        # Record the table tie.
        round_item["outcome"] = "tie"
        # Return both staked main wagers without profit.
        main_return = round(round_item["ante"] * 2, 2)
    # Lose both main wagers when the qualifying dealer wins.
    else:
        # Record the dealer win.
        round_item["outcome"] = "dealer_win"
        # Return no main wager value.
        main_return = 0.0
    # Read the player's stable category name for both bonus tables.
    player_name = round_item["player_rank"]["name"]
    # Calculate Ante Bonus profit independently of the dealer result.
    ante_bonus = round(round_item["ante"] * ANTE_BONUS.get(player_name, 0), 2)
    # Read the Pair Plus profit multiplier for the player's hand.
    pair_plus_multiplier = PAIR_PLUS.get(player_name, 0)
    # Return the Pair Plus stake plus profit only for a qualifying side-bet hand.
    pair_plus_return = round(round_item["pair_plus"] * (pair_plus_multiplier + 1), 2) if pair_plus_multiplier else 0.0
    # Store the complete transparent payout breakdown.
    round_item["payout_breakdown"] = {
        "ante_play_return": main_return,  # Store main wager returns and profit.
        "ante_bonus": ante_bonus,  # Store bonus profit only.
        "pair_plus_return": pair_plus_return,  # Store side-bet stake plus profit.
    }
    # Aggregate every returned component into one optional payout credit.
    round_item["total_payout"] = round(main_return + ante_bonus + pair_plus_return, 2)


# Apply one Play or Fold decision and prepare any remaining ledger movements.
def decide(state: dict, round_id: str, decision, action_id: str, *, completed_at: str) -> dict:
    # Resolve the round only from this player-scoped state document.
    round_item = get_round(state, round_id)
    # Allow exactly one terminal transition.
    if round_item.get("phase") != "decision":
        # Reject a new action identifier after settlement.
        raise ConflictError("Three Card Poker round is no longer awaiting a decision")
    # Normalize the supported decision vocabulary.
    normalized_decision = str(decision or "").strip().lower()
    # Reject unexpected commands before state mutation.
    if normalized_decision not in {"play", "fold"}:
        # Keep public actions explicit and deterministic.
        raise ValidationError("decision must be play or fold")
    # Bind the client action before any new wallet movement.
    round_item["decision_action_id"] = action_id
    # Persist the normalized public decision.
    round_item["decision"] = normalized_decision
    # Settle a fold with no additional debit or credit.
    if normalized_decision == "fold":
        # Explicitly forfeit Ante and Pair Plus under the chosen table rules.
        round_item["outcome"] = "fold"
        # Reveal dealer qualification only after the round becomes terminal.
        round_item["dealer_qualifies"] = dealer_qualifies(evaluate_three(round_item["dealer_hand"]))
        # Keep Play wager at zero because no matching stake was placed.
        round_item["play_wager"] = 0.0
        # Keep total stake equal to the initial aggregate debit.
        round_item["total_wager"] = round_item["total_initial_wager"]
        # Return no value for either forfeited wager.
        round_item["total_payout"] = 0.0
        # Preserve the all-zero payout breakdown.
        round_item["payout_breakdown"] = {"ante_play_return": 0.0, "ante_bonus": 0.0, "pair_plus_return": 0.0}
    # Prepare the matching Play debit and final settlement.
    else:
        # Require a Play wager equal to the Ante.
        round_item["play_wager"] = round_item["ante"]
        # Add Play to all previously committed stake.
        round_item["total_wager"] = round(round_item["total_initial_wager"] + round_item["play_wager"], 2)
        # Build the deterministic Play movement identifier.
        play_action_id = f"tcp:{round_id}:{action_id}:play-debit"
        # Append the matching debit before any possible payout credit.
        round_item["ledger_intents"].append(ledger_intent(play_action_id, action_id, "debit", round_item["play_wager"], "THREE_CARD_POKER_PLAY_DEBIT", round_item, "play_wager"))
        # Calculate all main and side-bet returns from the persisted deal.
        _settle_play(round_item)
        # Add one aggregate credit only when money is due.
        if round_item["total_payout"] > 0:
            # Build the deterministic payout movement identifier.
            payout_action_id = f"tcp:{round_id}:{action_id}:payout-credit"
            # Prepare one credit containing transparent result details.
            payout_intent = ledger_intent(payout_action_id, action_id, "credit", round_item["total_payout"], "THREE_CARD_POKER_PAYOUT_CREDIT", round_item, "settlement")
            # Add outcome and component detail for Admin audit views.
            payout_intent["details"].update({"outcome": round_item["outcome"], "payout_breakdown": dict(round_item["payout_breakdown"])})
            # Append the payout after the matching Play debit.
            round_item["ledger_intents"].append(payout_intent)
    # Calculate net from all debits and the aggregate credit.
    round_item["net"] = round(round_item["total_payout"] - round_item["total_wager"], 2)
    # Persist the injected completion timestamp before ledger reconciliation.
    round_item["completed_at"] = completed_at
    # Mark the prepared terminal state pending until every intent is committed.
    round_item["phase"] = "ledger_pending"
    # Return the transitioned mutable round.
    return round_item


# Build a client-safe round without internal ledger instructions or hidden cards.
def public_round(round_item: dict | None) -> dict | None:
    # Preserve an empty active-round slot in state payloads.
    if round_item is None:
        # Return the explicit null value.
        return None
    # Copy every public field except replay instructions.
    exposed = {key: value for key, value in round_item.items() if key != "ledger_intents"}
    # Hide all dealer cards while the player still owns the decision.
    if round_item.get("phase") == "decision":
        # Render three stable hidden-card compatibility markers.
        exposed["dealer_hand"] = ["??", "??", "??"]
        # Hide the precomputed private dealer rank.
        exposed["dealer_rank"] = None
    # Return the detached public representation.
    return exposed


# Build newest-first player state for reload and route restoration.
def public_state(state: dict) -> dict:
    # Resolve retained rounds from newest to oldest.
    rounds = [state.get("rounds", {}).get(round_id) for round_id in reversed(state.get("round_order", []))]
    # Remove any stale identifiers left by defensive pruning.
    retained = [round_item for round_item in rounds if round_item is not None]
    # Find the only active decision or recovery round.
    active = next((round_item for round_item in retained if round_item.get("phase") != "settled"), None)
    # Return active state separately from terminal history.
    return {
        "active_round": public_round(active),  # Expose the actionable round or null.
        "recent_rounds": [public_round(round_item) for round_item in retained if round_item.get("phase") == "settled"],  # Expose bounded terminal history.
    }
