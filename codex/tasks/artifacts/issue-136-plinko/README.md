# Issue #136 Plinko Isolated Slice

This artifact records the promotion proof and boundaries for the issue #136 Plinko worker branch.

## Distinct/countable proof

Plinko is materially distinct from the existing countable modules because its primary mechanic is a server-committed pegboard path that resolves to a bucket multiplier. The current catalog modules are roulette number/wheel settlement, slots reels, blackjack/baccarat/card tables, keno/bingo draws, video poker hands, Casino War, Big Six, Red Dog, Dragon Tiger, and Hi-Lo. None of those modules owns a committed left/right peg path with transparent bucket multipliers and client replay-only animation.

Countable status is therefore: distinct isolated module proposal, pending #77 shared integration. This branch does not claim catalog count acceptance.

## Owned files

- `casino/games/plinko/**`
- `web/games/plinko.js`
- `web/i18n/en-US/games/plinko.json`
- `web/i18n/ru-RU/games/plinko.json`
- `contracts/openapi/plinko.v1.yaml`
- `tests/games/plinko/**`
- `codex/tasks/artifacts/issue-136-plinko/**`

## Blockers for #77

- Allocate permanent `PLINKO-001` through `PLINKO-005` requirement IDs.
- Move the parked descriptor into `modules/plinko.json` and update `modules/module-manifest.json`.
- Register catalog, compatibility digest, visual matrix, browser discovery, and long-suite driver centrally.
- Capture real shared-shell visual evidence after route integration.
