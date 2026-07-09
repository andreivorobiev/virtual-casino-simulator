# Premium Machine and Draw Game Prerenders

Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/6

Scope: proposal artifacts only for Slots, Keno, and Bingo. No production files under `web/`, `casino/`, `contracts/`, `tests/`, `docs/requirements/`, or `modules/` were edited.

## Artifact Map

Source mockups:

- `source/mockup.html`
- `source/mockup.css`
- `source/render-prerenders.js`

Generated backdrop assets:

- `assets/slots-backdrop.png`
- `assets/keno-backdrop.png`
- `assets/bingo-backdrop.png`

PNG prerenders:

- `png/slots-idle-reels.png`
- `png/slots-spin-in-progress.png`
- `png/slots-win-payline-reveal.png`
- `png/slots-free-spin-progressive-context.png`
- `png/keno-spot-selection.png`
- `png/keno-draw-in-progress.png`
- `png/keno-result-paytable-comparison.png`
- `png/bingo-card-purchase-ready.png`
- `png/bingo-ball-call-in-progress.png`
- `png/bingo-winning-pattern-highlight.png`

## Design Rationale

The proposal follows the approved lobby reference: a dark emerald/black casino shell, gold trim, red primary actions, persistent top navigation, visible fake-money balance, and a bottom status rail. Each game keeps a stable three-column layout: left control rail, center fixed game stage, and right details drawer for paytables, histories, drawn balls, cards in play, or bot results.

AI-generated raster art is used only as an atmospheric backdrop. Deterministic gameplay surfaces, including reels, paylines, Keno numbers, Bingo cards, result boxes, bot/autoplay panels, and paytable rows, are code-native HTML/CSS so implementation can map them directly to current frontend state.

## State Coverage

Slots:

- Idle reels with 5 reels x 3 rows, paylines, line bet, progressive, free spin count, autoplay ready panel, paytable, and recent spin drawer.
- Spin in progress with debited balance, disabled spin button, reel blur layer, autoplay session progress, and reserved result region.
- Win/payline reveal with highlighted symbols, SVG payline overlay, credited payout, active paytable row, and updated recent spin.
- Free spin/progressive context with scatter trigger, free spin bank, progressive meter, and feature summary.

Keno:

- Spot selection with 1-80 board, selected 10-spot ticket, buy/draw controls, bot strategies, autoplay repeat-ticket panel, and paytable preview.
- Draw in progress with 12 of 20 balls shown, live ball emphasis, selected/drawn/catch styling, bot result drawer, and autoplay stop-after-draw affordance.
- Result/paytable comparison with all 20 drawn balls, five catches, payout summary, highlighted paytable row, history-ready drawer, and replay/new draw controls.

Bingo:

- Card purchase/ready state with 75-ball B/I/N/G/O card, free center space, pattern selection, bot cards, and stepwise autoplay panel.
- Ball call in progress with fixed call display, latest ball, marked card cells, called-ball chips, cards-in-play drawer, and stop-before-next-call control.
- Winning pattern highlight with a top-row any-line win, winner/payout summary, completed autoplay state, session result drawer, and recent sessions.

## Animation Notes

- Slots: reel motion should use `transform` on reel strips or symbol stacks, plus opacity/blur during the in-progress state. Payline and win glow should be overlay layers that do not affect reel layout. The result box must remain fixed-height during ready, spinning, win, and bonus states.
- Keno: drawn balls should enter the draw rail with transform/opacity, then toggle board states for drawn and catch classes. Ticket, board, paytable, and bot drawers stay mounted throughout the draw sequence.
- Bingo: ball call should animate inside the fixed call display. Daubs should use opacity/scale on overlays inside cells. Winning pattern highlight should be an overlay or class change on existing cells, not a card reflow.
- Autoplay: status changes should swap labels/buttons inside a reserved panel. Stop should prevent the next action while allowing the current atomic spin/draw/call to complete.

## Requirement Mapping

- UX stability: `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-005`, `UX-006`.
- Future premium UX proposals: `UX-007`, `UX-008`, `UX-009`.
- Shared ledger and balance visibility: `LEDGER-018`, `LEDGER-019`, `LEDGER-020`, `LEDGER-021`, `LEDGER-022`, `LEDGER-023`, `LEDGER-025`.
- Slots: `SLOT-001` through `SLOT-026`, especially reel dimensions, paylines, scatter/free spins, progressive jackpot, paytable, recent spins, reel animation, win highlights, autoplay, speed, sound cue surface, and fake-money handling.
- Keno: `KENO-001` through `KENO-022`, especially 1-80 board, 1-20 spots, 20 unique drawn numbers, paytable display, selected/drawn/catch highlights, bot quick-picks, autoplay repeat-ticket behavior, history rows, and fake-money handling.
- Bingo: `BINGO-001` through `BINGO-024`, especially 75-ball rules, B/I/N/G/O columns, free center, patterns, marked cells, winning pattern highlight, bot cards, payouts, cards in play, stepwise autoplay, history rows, and fake-money handling.
- Autoplay specifics: `AUTO-010`, `AUTO-012`, `AUTO-013`.

## Implementation File List

Likely implementation touchpoints for a later approved production phase:

- `web/styles.css`
- `web/games/slots.js`
- `web/games/keno.js`
- `web/games/bingo.js`
- `web/core/autoplay.js`
- `web/core/bots.js` for Keno/Bingo panels and any Slots bot decision
- Browser tests for Slots, Keno, and Bingo state stability and visual selectors

No API, ledger, contract, module manifest, or requirement file changes are implied by this prerender-only task.

## Rendering Notes

Rendered with the bundled Codex Node runtime and Playwright:

```powershell
$env:NODE_PATH='C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules'
& 'C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' codex\tasks\artifacts\premium-redesign-prerenders\machine-draw-games\source\render-prerenders.js
```

Validation performed:

- Renderer completed successfully.
- All 10 PNG outputs were produced.
- All PNGs are 2048 x 1152.
- Visual spot checks covered Slots win/free-spin states, Keno result state, and Bingo call/win states.

## AI-Generated Art Notes

The built-in image generation path was used for three atmospheric backdrop images. The prompt direction was:

- Slots: luxury five-reel slot machine, dark emerald casino interior, brass trim, no logos or readable text.
- Keno: premium Keno table, numbered ball tray, electronic board ambience, dark green felt, no brand text.
- Bingo: luxury Bingo table, balls, daubers, card, warm gold lighting, no people or logos.

These images are proposal backdrops only. Production implementation can either use approved final bitmap assets or replace them with deterministic CSS/canvas treatments.

## Open Questions

- Slots currently has an autoplay panel in `web/games/slots.js` but no bot panel, while the lobby advertises bots. Should the production Slots redesign reserve a bot panel or keep Slots automation-only until a compatible bot controller is confirmed?
- The numeric payouts shown in prerenders are illustrative proposal values. Production must bind all result text to API state and current paytable data.
- Generated Keno/Bingo background imagery contains decorative, non-authoritative numbers. Implementation must ensure only code-native boards/cards represent actual game state.
- These PNGs target the desktop reference size. A later implementation phase should add compact 1080p and mobile browser coverage.
- Bingo daub markers intentionally reduce number legibility for a casino-card feel. Confirm whether production should keep numbers fully legible under daubs for accessibility.
