# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared five-to-seven-card poker hand evaluation primitives.

Requirements: POKER-001.
"""

# Import immutable result records for safe comparison and serialization adapters.
from dataclasses import dataclass
# Import combinations so seven-card hands can select the strongest five cards.
from itertools import combinations

# Import shared card normalization instead of duplicating deck parsing rules.
from casino.core.cards import Card, RANKS, coerce_card

# Map canonical ranks to poker comparison values with ace high.
RANK_VALUES = {rank: value for value, rank in enumerate(RANKS, start=2)}
# Name categories in ascending comparison order.
CATEGORY_NAMES = (
    "high_card",  # Category zero has no grouped ranks.
    "one_pair",  # Category one has one pair.
    "two_pair",  # Category two has two pairs.
    "three_of_a_kind",  # Category three has one triplet.
    "straight",  # Category four has five consecutive ranks.
    "flush",  # Category five has one shared suit.
    "full_house",  # Category six combines a triplet and pair.
    "four_of_a_kind",  # Category seven has four equal ranks.
    "straight_flush",  # Category eight combines a straight and flush.
)


# Store a comparable poker result and the exact best five cards.
@dataclass(frozen=True)
class HandRank:  # Define the immutable evaluated-hand result.
    # Store the ascending category strength from zero through eight.
    category: int
    # Store the stable machine-readable category name.
    name: str
    # Store category-specific rank values in descending comparison order.
    tiebreak: tuple[int, ...]
    # Store the five cards that produced this result.
    cards: tuple[Card, ...]

    # Expose one tuple suitable for deterministic winner comparison.
    @property
    def comparison_key(self) -> tuple[int, ...]:  # Expose the complete winner key.
        # Prefix tie breakers with the category strength.
        return (self.category, *self.tiebreak)


# Return the high-card value for a straight or None when ranks are not consecutive.
def _straight_high(values: list[int]):
    # Remove duplicate ranks because pairs cannot contribute twice to a straight.
    unique = sorted(set(values))
    # Treat ace as low only for the five-high wheel pattern.
    if unique == [2, 3, 4, 5, 14]:
        # Rank a wheel below every other straight.
        return 5
    # Recognize five unique ranks spanning exactly four values.
    if len(unique) == 5 and unique[-1] - unique[0] == 4:
        # Return the highest rank for straight comparisons.
        return unique[-1]
    # Report that this rank set is not a straight.
    return None


# Evaluate exactly five cards using standard high-poker ordering.
def evaluate_five(cards) -> HandRank:
    # Normalize caller values through the shared card primitive.
    normalized = tuple(coerce_card(card) for card in cards)
    # Require exactly five cards for the focused evaluator.
    if len(normalized) != 5:
        # Direct callers to evaluate_hand when they have six or seven cards.
        raise ValueError("evaluate_five requires exactly five cards")
    # Convert ranks to numeric values for category comparisons.
    values = [RANK_VALUES[card.rank] for card in normalized]
    # Count each rank to identify pairs, trips, and quads.
    counts = {value: values.count(value) for value in set(values)}
    # Sort count groups by multiplicity and then rank, both strongest first.
    groups = sorted(((count, value) for value, count in counts.items()), reverse=True)
    # Recognize a flush when every card has the same suit.
    flush = len({card.suit for card in normalized}) == 1
    # Recognize a straight and retain its comparison high card.
    straight_high = _straight_high(values)
    # Rank a straight flush above every other standard category.
    if flush and straight_high is not None:
        # Return the category and its single high-card tie breaker.
        return HandRank(8, CATEGORY_NAMES[8], (straight_high,), normalized)
    # Rank four equal cards above a full house.
    if groups[0][0] == 4:
        # Compare quads first and then the remaining kicker.
        return HandRank(7, CATEGORY_NAMES[7], (groups[0][1], groups[1][1]), normalized)
    # Rank a three-plus-two grouping as a full house.
    if groups[0][0] == 3 and groups[1][0] == 2:
        # Compare the trip rank before the pair rank.
        return HandRank(6, CATEGORY_NAMES[6], (groups[0][1], groups[1][1]), normalized)
    # Rank a flush using all five ranks in descending order.
    if flush:
        # Preserve every descending rank as a possible tie breaker.
        return HandRank(5, CATEGORY_NAMES[5], tuple(sorted(values, reverse=True)), normalized)
    # Rank a non-flush straight using its normalized high card.
    if straight_high is not None:
        # Use the wheel-aware straight high value for comparison.
        return HandRank(4, CATEGORY_NAMES[4], (straight_high,), normalized)
    # Rank three equal cards above two pair.
    if groups[0][0] == 3:
        # Compare the trip rank followed by both descending kickers.
        kickers = sorted((value for value in values if value != groups[0][1]), reverse=True)
        # Return the complete deterministic comparison tuple.
        return HandRank(3, CATEGORY_NAMES[3], (groups[0][1], *kickers), normalized)
    # Rank two distinct pairs above one pair.
    if groups[0][0] == 2 and groups[1][0] == 2:
        # Sort pair ranks strongest first independent of input order.
        pairs = sorted((groups[0][1], groups[1][1]), reverse=True)
        # Find the only rank that is not part of either pair.
        kicker = next(value for value in values if value not in pairs)
        # Return both pairs and the kicker as the comparison tuple.
        return HandRank(2, CATEGORY_NAMES[2], (pairs[0], pairs[1], kicker), normalized)
    # Rank one pair above a high-card hand.
    if groups[0][0] == 2:
        # Capture the pair rank identified by the leading count group.
        pair = groups[0][1]
        # Sort all unpaired kickers strongest first.
        kickers = sorted((value for value in values if value != pair), reverse=True)
        # Return the pair followed by all three kickers.
        return HandRank(1, CATEGORY_NAMES[1], (pair, *kickers), normalized)
    # Rank an unpaired hand by all five descending card values.
    return HandRank(0, CATEGORY_NAMES[0], tuple(sorted(values, reverse=True)), normalized)


# Evaluate the strongest five-card result from a five-, six-, or seven-card hand.
def evaluate_hand(cards) -> HandRank:
    # Normalize once so repeated five-card combinations share validated values.
    normalized = tuple(coerce_card(card) for card in cards)
    # Bound the evaluator to standard video-poker and table-poker hand sizes.
    if not 5 <= len(normalized) <= 7:
        # Reject incomplete or oversized hands with a stable error.
        raise ValueError("evaluate_hand requires five, six, or seven cards")
    # Evaluate every possible five-card selection from the normalized hand.
    candidates = (evaluate_five(candidate) for candidate in combinations(normalized, 5))
    # Return the candidate with the strongest category and tie breakers.
    return max(candidates, key=lambda result: result.comparison_key)
