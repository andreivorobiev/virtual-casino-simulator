# Premium Casino Redesign Implementation Epic

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Coordinator chat: Casino Simulator - Coordinator
- Approved prerender PR: https://github.com/andreivorobiev/virtual-casino-simulator/pull/10
- Base design branch: `codex/premium-redesign-prerenders`

## Goal

Implement the approved premium casino redesign across the real running app while preserving fake-money framing, gameplay behavior, ledger accounting, `/api/v1` compatibility, bot/autoplay behavior, and module isolation.

## Child Issues

- Shared shell/lobby/foundation: https://github.com/andreivorobiev/virtual-casino-simulator/issues/12
- I18n/Admin Language/Locale: https://github.com/andreivorobiev/virtual-casino-simulator/issues/13
- Roulette frontend: https://github.com/andreivorobiev/virtual-casino-simulator/issues/14
- Blackjack frontend: https://github.com/andreivorobiev/virtual-casino-simulator/issues/15
- Baccarat frontend: https://github.com/andreivorobiev/virtual-casino-simulator/issues/16
- Slots frontend: https://github.com/andreivorobiev/virtual-casino-simulator/issues/17
- Keno frontend: https://github.com/andreivorobiev/virtual-casino-simulator/issues/18
- Bingo frontend: https://github.com/andreivorobiev/virtual-casino-simulator/issues/19
- Integration and visual validation: https://github.com/andreivorobiev/virtual-casino-simulator/issues/20

## Coordination Rules

- Use `docs/visual_design_standard.md` as the authoritative UI policy and `tests/visual/visual_matrix.json` as the required surface/state/locale/viewport inventory.
- Land shared shell/lobby/foundation before game workers make heavy UI changes.
- Use stacked branches when a worker depends on shared foundation work.
- Avoid two workers editing the same file at the same time.
- Game workers own only their `web/games/<game>.js` file plus explicit tests/module metadata unless the coordinator expands scope.
- Shared CSS, layout tokens, static assets, and app shell live in the foundation task.
- I18n/Admin work owns resource files and Admin surfaces, and must coordinate before modifying shell or game render flows.

## Definition of Done

- All child PRs reference requirement IDs and issue numbers.
- Module versions and generated docs are updated when source modules or requirements change.
- Browser-visible changes have browser evidence.
- Final integration validates desktop and mobile layouts against PR #10 prerenders.
