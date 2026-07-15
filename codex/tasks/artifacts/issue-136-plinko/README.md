# Issue #136 Plinko Integration Evidence

This artifact records the isolated implementation handoff and its later #77 promotion boundary.

## Distinct/countable proof

Plinko is materially distinct from the existing countable modules because its primary mechanic is a server-committed pegboard path that resolves to a bucket multiplier. The current catalog modules are roulette number/wheel settlement, slots reels, blackjack/baccarat/card tables, keno/bingo draws, video poker hands, Casino War, Big Six, Red Dog, Dragon Tiger, and Hi-Lo. None of those modules owns a committed left/right peg path with transparent bucket multipliers and client replay-only animation.

Countable status is therefore: distinct catalog-integrated module accepted through the serialized #77 lane.

## Owned files

- `casino/games/plinko/**`
- `web/games/plinko.js`
- `web/i18n/en-US/games/plinko.json`
- `web/i18n/ru-RU/games/plinko.json`
- `contracts/openapi/plinko.v1.yaml`
- `tests/games/plinko/**`
- `codex/tasks/artifacts/issue-136-plinko/**`

## Canonical integration

- `modules/plinko.json` owns sort order 230, canonical route `/games/plinko`, paired EN/RU metadata, and catalog discovery.
- Permanent `PLINKO-001` through `PLINKO-005` requirements map rules, session/restart behavior, ledger safety, browser localization, and discovered evidence.
- The parked proposal is retired atomically with compatibility metadata, visual matrix, central API/browser coverage, and the Long Suite driver.
- Acceptance uses exact-head real-backend EN/RU viewport evidence plus copied-deployment Long Suite 100.
