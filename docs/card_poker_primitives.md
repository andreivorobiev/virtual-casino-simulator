# Card and poker primitives

Requirements: `CARD-001`, `CARD-002`, `POKER-001`, `POKER-002`.

This primitive lane is intentionally unregistered. A game worker opts into the pieces it needs without editing another game package or inheriting a game-owned rule set.

## Backend cards and decks

Import from `casino.core.cards`:

- `Card(rank, suit)` stores a validated immutable card. Canonical suits are `clubs`, `diamonds`, `hearts`, and `spades`.
- `coerce_card(value)` accepts a `Card`, a `{rank, suit}` mapping, or compact strings such as `AS`, `10H`, and `A♠`.
- `create_deck(decks=1)` returns ordered standard cards. Multiple decks preserve stable deck, suit, and rank ordering.
- `shuffle_cards(cards, seed=...)` returns a normalized shuffled copy and never mutates the caller's list.
- `shuffled_deck(decks=1, seed=...)` creates and shuffles in one call.

Production callers should omit `seed`; the primitive then uses system randomness. Tests should provide a stable string or integer seed. Do not expose user-controlled seeds as a claim of casino-grade fairness: this is a toy simulator and the hook exists for reproducibility.

```python
from casino.core.cards import shuffled_deck

shoe = shuffled_deck(decks=1, seed="worker-fixture")
first_card = shoe.pop()
```

An advanced caller may inject a random-compatible object with a `shuffle(list)` method through `rng`. Supplying both `seed` and `rng` is an error.

## Poker evaluation

Import `evaluate_five` or `evaluate_hand` from `casino.core.poker`. Inputs use the same accepted card shapes as `coerce_card`.

- `evaluate_five(cards)` requires exactly five cards.
- `evaluate_hand(cards)` accepts five, six, or seven cards and returns the strongest five-card combination.
- The returned `HandRank` exposes `category` (`0` through `8`), `name`, `tiebreak`, `cards`, and `comparison_key`.
- Categories ascend from `high_card` through `straight_flush`. Ace-low wheels normalize to a five-high straight.

```python
from casino.core.poker import evaluate_hand

result = evaluate_hand(["AS", "KS", "QS", "JS", "10S", "2D", "2C"])
assert result.name == "straight_flush"
```

Game workers remain responsible for game-specific paytables. For example, Jacks-or-Better qualification and wild-card substitutions do not belong in this standard high-poker evaluator.

## Frontend renderer

Import from `web/core/cards.js`, and include `web/core/cards.css` from the consuming game's isolated stylesheet or page assembly:

```javascript
import { renderCard } from '../core/cards.js';

const held = renderCard('AH', { selected: true });
const hand = ['AH', '10D', '3C'].map(card => renderCard(card)).join('');
```

`renderCard` accepts compact strings or `{ rank, suit }` objects. Use `{ hidden: true }` or the compatibility marker `??` for a face-down card. The renderer:

- emits one `role="img"` label per visible or hidden card;
- hides decorative rank and suit glyphs from assistive technology;
- communicates selection through `aria-current` in addition to styling;
- sanitizes optional class tokens;
- uses no timers or automatic animation;
- exposes responsive flex and `clamp()` sizing hooks;
- removes decorative transitions and selected-card movement under `prefers-reduced-motion: reduce`.

`prefersReducedMotion()` is also exported for a consuming game that needs to decide whether to start its own optional animation. Timer ownership remains with the game or autoplay control plane, not the renderer.

## Focused validation

Run the isolated suites before handing the primitives to a game worker:

```powershell
python -m unittest tests.card_poker_primitives_tests
node tests/card_renderer_tests.js
```

These primitives are now consumed by the card and poker games discovered from `modules/*.json`, and each consuming game carries its own browser and visual evidence under its allocated visual-matrix row. Changes here affect every one of those rows, so re-run the consuming games' browser and visual gates.
