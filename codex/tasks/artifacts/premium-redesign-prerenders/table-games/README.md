# Premium Table Game Prerenders

Proposal artifacts for issue #5. These are prerender-only source mockups and PNG captures for Roulette, Blackjack, and Baccarat. No production UI, gameplay, API, contract, test, requirement, or module files were edited.

## Files

- `table-game-prerenders.html` - static source mockup with one fixed 1600x900 article per state.
- `table-game-prerenders.css` - premium visual system, table geometry, stable rails, cards, chips, roads, and result drawers.
- `render-prerenders.mjs` - commented Playwright capture helper.
- `contact-sheet.png` - quick visual index of the required states.
- `roulette-betting-setup.png`
- `roulette-spinning-reveal.png`
- `roulette-settled-result.png`
- `blackjack-initial-deal.png`
- `blackjack-active-decision.png`
- `blackjack-split-multi-hand.png`
- `blackjack-settled-result.png`
- `baccarat-wager-setup.png`
- `baccarat-card-reveal.png`
- `baccarat-result-road-history.png`

## Design Rationale

- Matches the approved lobby direction: dark premium shell, gold trim, visible balance, stable navigation, rich table surfaces, and red-gold primary actions.
- Uses code-native mock assets rather than AI imagery because deterministic table geometry, cards, chips, action controls, and roads are more implementation-ready for these games.
- Keeps each game state in the same three-zone layout: left control rail, fixed central play stage, and right drawer for slips, scoreboards, stats, shoe data, settlements, or road history.
- Reserves vertical and horizontal space for result messages, bot/autoplay panels, cards, split hands, bet slips, stats, and road history so state changes do not move the main game area.

## State Coverage

- Roulette: betting setup, spinning/reveal, settled result.
- Blackjack: initial deal, active decision with Insurance visible, split/multi-hand layout, settled result.
- Baccarat: wager setup, card reveal, result with road history update.
- Bot/autoplay panels are shown where relevant. Blackjack explicitly shows autoplay disabled per current requirement behavior.

## Animation Notes

- Roulette: rotate wheel and counter-rotate ball using transform only; fade in reveal glow; lock result marker with opacity/scale; update stats and bet slip inside fixed regions.
- Blackjack: deal cards with translate/opacity; highlight active hand with opacity/box-shadow; split by transforming cards into pre-reserved lanes; keep all Hit, Stand, Double, Split, Surrender, and Insurance buttons mounted.
- Baccarat: peel/reveal cards with rotate/translate/opacity; keep third-card placeholder bays reserved; update road cells with opacity/scale; keep wager zones fixed.
- All proposed motion should avoid layout-changing animation and should preserve the action rail, stage, and drawer dimensions.

## Future Implementation File List

- `web/styles.css` for shared premium shell, table surfaces, cards, chips, drawers, and stable game-area rules.
- `web/games/roulette.js` for wheel/table markup, bet slip drawer, spin/reveal/result states, stats rail, bot/autoplay placement.
- `web/games/blackjack.js` for premium table layout, fixed action matrix, insurance state, split lanes, and settlement drawer.
- `web/games/baccarat.js` for wager zones, card reveal bays, road history grid, shoe drawer, bot/autoplay placement.
- `web/core/ui.js` only if shared card/chip helpers are extracted during implementation.
- `web/core/autoplay.js` and `web/core/bots.js` only if presentation hooks need shared control-plane styling.

## Requirement Mapping

- UX: validates the direction for `UX-001` through `UX-006`; proposes future coverage for premium redesign IDs `UX-007`, `UX-008`, and `UX-009`.
- Roulette: maps to `ROU-041` through `ROU-050` and `ROU-051` through `ROU-056`, with emphasis on real table layout, vector-style wheel behavior, chips, stats, bot/autoplay, and no fake zero state.
- Blackjack: maps to `BJ-028` through `BJ-030` plus action requirements `BJ-008` through `BJ-023`.
- Baccarat: maps to `BAC-020` through `BAC-024`, including cards, totals, winner, road history, shoe/burn info, bots, and autoplay.
- Ledger and control plane: maps visible balance and settlement surfaces to `LEDGER-005`, `LEDGER-006`, `LEDGER-010` through `LEDGER-017`, `LEDGER-025`, `AUTO-009`, `AUTO-011`, and `AUTO-014`.

## Open Questions

- Should Blackjack continue to show an explicit disabled autoplay panel, or should that space become a strategy/coach panel until a compatible bot controller exists?
- Should Baccarat implementation include only bead-road history first, or reserve space for derived roads in the same drawer?
- Should Roulette keep racetrack controls in the left rail on 1080p, or move advanced call bets into a drawer if browser tests show crowding?
- Should future production work introduce generated photographic table backgrounds, or keep the first implementation fully code-native for testability and maintainability?
