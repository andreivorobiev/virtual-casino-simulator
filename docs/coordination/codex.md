# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-21T04:23:24Z.

## Current branch / active Codex work

- Protected main is exact `c7b86e54ba5ae03953903514207ee526dc9bc719`, the deployed v0.9.5.84 source at the start of issue #1040.
- Isolated branch `codex/1040-concurrency-ceilings` implements the repository-only concurrency qualification packet for issue #1040.
- No production, database, provider, release, public-policy, or deployment mutation is authorized by this branch.

## Accepted scope and requirements

- `MYSQL-011` raises the process-local MySQL pool default to sixteen, permits an explicit one-through-sixty-four capacity, and exposes only bounded authenticated Admin saturation telemetry.
- `CORE-035` makes the existing production Gunicorn adapter the sole load-qualification serving stack with bounded worker and gthread controls.
- `TEST-251` adds exact-source 32-session JSON/MySQL CI evidence and an opt-in exact-100-session disposable-MySQL formal profile.
- `OPS-004`, `STORAGE-010`, and `TEST-220` are compatibly amended; requirements total exactly 1114 and the API case inventory is exactly 213.

## Version and contract allocation

- Packaged release remains `0.9.5.84`.
- Content-owned module revisions are application `9.72.0`, core `10.13.0`, admin `1.21.0`, operations `1.2.0`, tests `1.116.1`, docs `1.112.1`, contracts `1.63.0`, and tooling `1.45.0`; every other module remains exact protected-main values.
- The frozen `/api/v1` contract and all game, paytable, settlement, signup, OAuth, provider, billing, and public-launch behavior remain unchanged.

## Validation and handback

- Local focused Python evidence, requirements, versions, contracts, module boundaries, and catalog validation are green on the moving packet.
- Before merge, the immutable PR head must pass the full repository gates, ordinary 32-session JSON/MySQL hosted evidence, exact Admin Browser rows, and the opt-in 100-session MySQL Gunicorn profile.
- Issue #1040 closes only after exact-head formal evidence is posted to the issue and the normal non-bypass PR merge completes.
