# Issue #134 Distinct Module Proof

Decision: promote through #77 as a canonical distinct game module.

Evidence:

- Let It Ride has a unique rule nucleus: three equal base wagers are committed up front, the player sees three personal cards, then may withdraw one eligible wager at each of two decision beats before the final five-card poker hand is evaluated with two community cards.
- Existing registered or draft card games in this repo do not implement that nucleus:
  - Multi-Hand Video Poker uses hold/draw poker hands and has no staged wager withdrawal or community cards.
  - Red Dog and Acey-Deucey resolve in-between/spread decisions, not a five-card poker result with staged wager pullbacks.
  - Casino War, Dragon Tiger, and Hi-Lo resolve high-card or higher/lower comparisons, not poker rankings.
  - Baccarat and Blackjack have fixed banking/drawing procedures and do not expose two pullback decisions on three equal wagers.
- The implementation uses shared card and poker primitives from `casino.core.cards` and `casino.core.poker`, but imports no existing game module.
- The canonical descriptor, permanent requirements, central tests, and visual row are integrated by #77 after distinctness and real-backend acceptance passed.

Countability: distinct and countable pending #77 shared catalog/router/manifest/requirements/visual-matrix/test-discovery integration.
