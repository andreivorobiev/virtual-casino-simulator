# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-21T13:40:00Z.

## Current branch / active Codex work

- Protected main is exact `667bdf2b4a0b3d997d5bf18f9bf158fa49749c01`, including the catalog-derived 49-worker formal matrix from issue #1048.
- Isolated branch `codex/1050-formal-strategies` repairs the missing rendered-control strategies exposed by exact-main formal run `32480806914`.
- No production, database, provider, release, public-policy, deployment, API, game-engine, paytable, or settlement mutation is authorized by this branch.

## Accepted scope and requirements

- `TEST-092` keeps its exact 50,000-cycle, full-catalog, four-viewport, per-control, exact-source, and fail-closed aggregate contract.
- Every registered catalog game now maps to an implemented strategy family; unknown games and unknown families fail before action dispatch.
- The fifteen formerly hidden games from Color Wheel through Teen Patti receive explicit visible-choice, replay, decision, and terminal-readiness coverage; Double Bonus Video Poker stays on the existing draw-poker family.
- Stable control signatures distinguish the new board, choice, hand-setting, wager, decision, deal, and repeat identities.
- Requirements remain exactly 1114 and the frozen `/api/v1` contract remains unchanged.

## Version and validation allocation

- Packaged release remains `0.9.5.84`.
- Tests and docs receive compatible patch revisions; every runtime and game module remains at its exact protected-main revision.
- The frozen `/api/v1` contract and all game, paytable, settlement, signup, OAuth, provider, billing, and public-launch behavior remain unchanged.

## Validation and handback

- Local work is browser-free by policy: syntax, catalog/registry proofs, strategy state-machine unit seams, requirements, versions, contracts, boundaries, comments, headers, and rule gates run locally.
- The immutable exact-head PR must pass ordinary checks plus one 49-worker formal dispatch before merge and issue #1050 closure.
- One fresh exact-main formal dispatch after merge must repeat every worker, aggregate, and visual gate before parent #1041 can close.
