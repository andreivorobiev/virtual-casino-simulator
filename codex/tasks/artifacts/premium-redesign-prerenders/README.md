# Premium Casino Redesign Prerenders

Coordinator review package for issues:

- Epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/3
- I18n locale plan: https://github.com/andreivorobiev/virtual-casino-simulator/issues/4
- Table game prerenders: https://github.com/andreivorobiev/virtual-casino-simulator/issues/5
- Machine and draw game prerenders: https://github.com/andreivorobiev/virtual-casino-simulator/issues/6
- Shell, lobby, and admin prerenders: https://github.com/andreivorobiev/virtual-casino-simulator/issues/7

Scope: proposal artifacts only. No production files under `web/`, `casino/`, `contracts/`, `tests/`, `docs/requirements/`, or `modules/` were edited for this package.

## Review Order

1. Compare the requested visual target in `reference/target-lobby.png` against `shell-lobby-admin/premium-lobby.png`.
2. Review shared casino shell behavior in `shell-lobby-admin/shared-shell-wallet.png`.
3. Review Admin and language/locale direction in `shell-lobby-admin/admin-dashboard.png` and `shell-lobby-admin/admin-language-locale.png`.
4. Review table-game state fidelity in `table-games/contact-sheet.png`, then inspect individual Roulette, Blackjack, and Baccarat states.
5. Review machine/draw-game state fidelity under `machine-draw-games/png/`.
6. Review the localization architecture and English/Russian samples under `i18n-plan/`.

## Artifact Map

Shell, lobby, admin:

- `shell-lobby-admin/premium-lobby.png`
- `shell-lobby-admin/shared-shell-wallet.png`
- `shell-lobby-admin/admin-dashboard.png`
- `shell-lobby-admin/admin-language-locale.png`
- `shell-lobby-admin/responsive-narrow.png`
- Source HTML/CSS and generated assets in `shell-lobby-admin/`

Table games:

- `table-games/contact-sheet.png`
- Roulette: `roulette-betting-setup.png`, `roulette-spinning-reveal.png`, `roulette-settled-result.png`
- Blackjack: `blackjack-initial-deal.png`, `blackjack-active-decision.png`, `blackjack-split-multi-hand.png`, `blackjack-settled-result.png`
- Baccarat: `baccarat-wager-setup.png`, `baccarat-card-reveal.png`, `baccarat-result-road-history.png`
- Source HTML/CSS/render helper in `table-games/`

Machine and draw games:

- Slots: `slots-idle-reels.png`, `slots-spin-in-progress.png`, `slots-win-payline-reveal.png`, `slots-free-spin-progressive-context.png`
- Keno: `keno-spot-selection.png`, `keno-draw-in-progress.png`, `keno-result-paytable-comparison.png`
- Bingo: `bingo-card-purchase-ready.png`, `bingo-ball-call-in-progress.png`, `bingo-winning-pattern-highlight.png`
- Source HTML/CSS/render helper and generated backdrops in `machine-draw-games/`

I18n:

- `i18n-plan/resource-architecture.md`
- `i18n-plan/string-inventory.md`
- `i18n-plan/implementation-test-plan.md`
- `i18n-plan/samples/en-US.json`
- `i18n-plan/samples/ru-RU.json`

## Proposal Principles

- Match the approved premium direction: dark casino shell, gold trim, red primary actions, visible fake-money wallet, and high-fidelity game imagery.
- Keep game stages spatially stable so round progress, autoplay, results, and language changes do not reset or jump the layout.
- Use AI-generated raster art only where it adds atmosphere; use code-native UI, cards, tables, chips, reels, boards, and controls where deterministic implementation matters.
- Extract future UI strings into resource files with English and Russian as the first validation pair.
- Add module version bumps only in the future implementation phase when production modules actually change.

## Implementation Gate

This package is intended for user review before the larger production implementation. Once approved, split implementation into separate GitHub-managed worker tasks by surface:

- Shared shell, lobby, and admin language/locale
- Roulette
- Blackjack
- Baccarat
- Slots
- Keno
- Bingo
- I18n runtime and resource extraction
- Browser validation and visual regression
