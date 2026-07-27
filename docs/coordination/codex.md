# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-27T22:10:00Z.

## Current branch / active Codex work

- Codex integration is preparing `codex/release-v0.9.5.19` from exact accepted MySQL-pool-lifecycle main `648014dd`.
- Scope is the unique immutable patch identity, PWA rotation, release provenance, and governed release documentation required before the next serial merge.
- No unmerged feature branch, held #450 infrastructure draft, provider change, DNS, billing, public signup, live OAuth, mail activation, invitation, public-exposure, credential, or SSH-ingress mutation is included.

## Live queue snapshot

- Accepted protected main before this release branch is `648014dd`, containing merged PR #464.
- Immutable v0.9.5.18 at `92fcf3ef` remains the exact deployed predecessor until v0.9.5.19 is qualified and deployed.
- #450 remains a parallel held deployment-workflow draft and is excluded from this release.
- #455 and every Claude or other feature PR remain merge-held behind terminal-green v0.9.5.19 deployment.

## #77 / #73 / #66 catalog interpretation

- The installed catalog is descriptor-discovered from `modules/<game-id>.json`; protected main currently has 46 playable game descriptors.
- `GAME_CATALOG_TARGET = 20` is a historical readiness floor/reporting target, not a cap and not a command to add duplicate catalog infrastructure.
- #73 remains the game-portfolio umbrella for catalog quality and future expansion beyond the installed set.
- #77 remains the serialized shared-integration lane for descriptor promotion, shared catalog collision surfaces, requirements/test discovery, compatibility metadata, and acceptance evidence.
- #66 remains the broader program epic tying catalog work to multi-user, storage, operations, and release readiness.

## Requirement / TEST ID renames at merge

- No requirement IDs or TEST IDs were allocated or renamed in this slice.

## File claims / collision notes

- Codex is not landing games in parallel.
- Codex is not touching Claude-owned active implementation files from stale `claude.md`, including auth/CSRF files or broad governance splices.
- If Claude restarts game catalog implementation, coordinate before editing `modules/module-manifest.json`, generated requirements, `tests/run_tests.py`, contracts, or visual matrix rows.

## Decisions / handbacks

- PR #464 merged normally with exact-head checks and zero unresolved review threads.
- This release packages the accepted bounded per-process MySQL connection lifecycle without a public contract, schema migration, or production database mutation.
- After terminal-green deployment, #455 or the highest-priority eligible Claude handback may enter the next serialized merge slot after current-main reconciliation.
