# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T14:35:00Z.

## Current branch / active Codex work

- Protected main, tag, release, and live production are exact terminal-green v0.9.5.62 source `3967dab1419bcc8ebfd7c8584a4bb9baa4665b34`.
- Isolated branch `codex/433-declarative-game-rules-v63` prepares the remaining runtime enforcement slice for issue #433 from exact v0.9.5.62 main.
- No other content lane, release, production action, or contributor worktree is being mutated.

## Accepted scope and requirements

- The #433 slice mounts descriptor-owned settings coercion centrally in the router, retires duplicated per-game rule domains, repairs poisoned persisted rules to engine defaults, and generates OpenAPI request schemas plus authority-matrix bounded fields from the same descriptors.
- Requirements total exactly 931 unique rows after allocating only `TEST-163`; existing `SEC-002`, `SEC-004`, and `SEC-014` are amended rather than duplicated.
- Scope is limited to Core rule handling, Blackjack/Baccarat/Roulette settings consumers, generated contracts, governance, and browser-free evidence; game paytables, settlement interfaces, provider accounts, and schema migration remain unchanged.

## Version and contract allocation

- Package `0.9.5.62` and application `9.59.3` remain unchanged until a separately qualified formal release.
- Content revisions are Core `9.39.0`, Blackjack `9.1.10`, Baccarat `9.1.15`, Roulette `9.6.3`, contracts `1.57.0`, tests `1.72.0`, docs `1.70.0`, and tooling `1.27.0`; all other module revisions remain exact v0.9.5.62 values.
- Frozen `/api/v1` response envelopes remain unchanged; invalid out-of-domain settings now fail with the existing validation envelope before handlers run.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- Local qualification includes focused descriptor, legacy settlement, router, matrix, generated-contract, full API, requirements, versions, docs, contracts, boundaries, catalog, rules, density, and diff gates.
- Issue #433 closes only after exact-head hosted qualification, normal non-bypass merge, one immutable formal release, and terminal-green deployment. No commit, push, PR, workflow, release, or production mutation is claimed by this working packet.
