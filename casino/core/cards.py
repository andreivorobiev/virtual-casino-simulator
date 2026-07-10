"""Reusable playing-card and deterministic deck primitives.

Requirements: CARD-001.
"""

# Import immutable record support so card values are safe to share between games.
from dataclasses import dataclass
# Import the standard random implementations used for seeded and secure shuffles.
import random
# Import mapping support so API-shaped card payloads can be normalized.
from typing import Mapping

# Define ranks in stable deck-construction order from deuce through ace.
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
# Define suits in stable bridge order for reproducible unshuffled decks.
SUITS = ("clubs", "diamonds", "hearts", "spades")
# Map canonical suits to compact display symbols without making symbols identifiers.
SUIT_SYMBOLS = {"clubs": "♣", "diamonds": "♦", "hearts": "♥", "spades": "♠"}
# Accept compact and display-oriented suit spellings at the primitive boundary.
SUIT_ALIASES = {
    "C": "clubs",  # Normalize the compact clubs code.
    "D": "diamonds",  # Normalize the compact diamonds code.
    "H": "hearts",  # Normalize the compact hearts code.
    "S": "spades",  # Normalize the compact spades code.
    "♣": "clubs",  # Normalize the visual clubs symbol.
    "♦": "diamonds",  # Normalize the visual diamonds symbol.
    "♥": "hearts",  # Normalize the visual hearts symbol.
    "♠": "spades",  # Normalize the visual spades symbol.
    "CLUBS": "clubs",  # Normalize the full clubs name.
    "DIAMONDS": "diamonds",  # Normalize the full diamonds name.
    "HEARTS": "hearts",  # Normalize the full hearts name.
    "SPADES": "spades",  # Normalize the full spades name.
}


# Store a normalized card as an immutable value object for downstream engines.
@dataclass(frozen=True)
class Card:  # Define the shared immutable playing-card value.
    # Store the canonical poker rank.
    rank: str
    # Store the canonical lower-case suit name.
    suit: str

    # Validate and normalize constructor input immediately.
    def __post_init__(self):
        # Normalize rank casing so face-card input is consistent.
        normalized_rank = str(self.rank).upper()
        # Resolve suit aliases without requiring callers to know canonical names.
        normalized_suit = SUIT_ALIASES.get(str(self.suit).upper())
        # Reject ranks outside a standard fifty-two-card deck.
        if normalized_rank not in RANKS:
            # Raise a direct value error suitable for unit and API boundary handling.
            raise ValueError(f"Unsupported card rank: {self.rank}")
        # Reject suits outside a standard fifty-two-card deck.
        if normalized_suit not in SUITS:
            # Raise a direct value error suitable for unit and API boundary handling.
            raise ValueError(f"Unsupported card suit: {self.suit}")
        # Store the normalized rank despite the frozen public value contract.
        object.__setattr__(self, "rank", normalized_rank)
        # Store the normalized suit despite the frozen public value contract.
        object.__setattr__(self, "suit", normalized_suit)

    # Return a compact ASCII code that is safe for persisted game state.
    @property
    def code(self) -> str:  # Expose an encoding-safe compact identifier.
        # Use the uppercase suit initial to avoid encoding-dependent identifiers.
        return f"{self.rank}{self.suit[0].upper()}"

    # Return the familiar rank-and-symbol form for display adapters.
    @property
    def display(self) -> str:  # Expose familiar rank-and-suit display text.
        # Combine normalized rank and the corresponding suit symbol.
        return f"{self.rank}{SUIT_SYMBOLS[self.suit]}"


# Normalize supported card values into the shared immutable representation.
def coerce_card(card) -> Card:
    # Preserve already-normalized card objects without allocating replacements.
    if isinstance(card, Card):
        # Return the shared immutable card directly.
        return card
    # Normalize API-style objects containing rank and suit fields.
    if isinstance(card, Mapping):
        # Construct through Card so validation remains centralized.
        return Card(card.get("rank", ""), card.get("suit", ""))
    # Normalize compact strings such as AS, 10H, or A♠.
    if isinstance(card, str) and len(card.strip()) >= 2:
        # Remove surrounding whitespace before parsing the final suit token.
        compact = card.strip()
        # Treat the final character as the suit and the prefix as the rank.
        return Card(compact[:-1], compact[-1])
    # Reject ambiguous values rather than silently constructing invalid cards.
    raise ValueError(f"Unsupported card value: {card!r}")


# Create one or more ordered standard decks without mutating global state.
def create_deck(decks: int = 1) -> list[Card]:
    # Reject booleans and non-integer deck counts explicitly.
    if isinstance(decks, bool) or not isinstance(decks, int) or decks < 1:
        # Raise a stable error that callers can translate at their own boundary.
        raise ValueError("decks must be a positive integer")
    # Build each complete deck in stable suit-then-rank order.
    return [Card(rank, suit) for _ in range(decks) for suit in SUITS for rank in RANKS]


# Return a shuffled copy while supporting deterministic test seeds.
def shuffle_cards(cards, *, seed=None, rng=None) -> list[Card]:
    # Prevent ambiguous calls that provide two competing random sources.
    if seed is not None and rng is not None:
        # Require callers to choose either the seed hook or an injected generator.
        raise ValueError("seed and rng are mutually exclusive")
    # Normalize every input card before shuffling the independent copy.
    shuffled = [coerce_card(card) for card in cards]
    # Create an isolated deterministic generator whenever a seed is supplied.
    generator = random.Random(seed) if rng is None and seed is not None else rng
    # Use system randomness for production calls that do not inject test entropy.
    generator = generator if generator is not None else random.SystemRandom()
    # Shuffle only the new list so caller-owned decks remain unchanged.
    generator.shuffle(shuffled)
    # Return the independently shuffled normalized cards.
    return shuffled


# Create and shuffle a standard deck or shoe in one reusable operation.
def shuffled_deck(decks: int = 1, *, seed=None, rng=None) -> list[Card]:
    # Delegate construction and shuffling to their separately testable primitives.
    return shuffle_cards(create_deck(decks), seed=seed, rng=rng)
