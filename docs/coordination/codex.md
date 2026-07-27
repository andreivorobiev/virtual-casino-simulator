# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-27T18:02:00Z.

## Current branch / active Codex work

- Codex integration is preparing `codex/release-v0.9.5.16` from exact accepted catalog-reconciliation main `89b254f7`.
- Scope is the unique immutable patch identity, PWA rotation, release provenance, and governed release documentation required before the next serial merge.
- No unmerged feature branch, held #450 infrastructure draft, provider change, DNS, billing, public signup, live OAuth, mail activation, invitation, public-exposure, credential, or SSH-ingress mutation is included.

## Live queue snapshot

- Accepted protected main before this release branch is `89b254f7`, containing merged PR #451.
- Immutable v0.9.5.15 at `8879672e` remains the exact deployed predecessor until v0.9.5.16 is qualified and deployed.
- #450 remains a parallel held deployment-workflow draft and is excluded from this release.
- Later feature PRs remain serialized behind terminal-green v0.9.5.16 deployment.

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

- PR #451 merged normally with exact-head checks and zero unresolved review threads.
- This release packages that accepted state without changing runtime catalog behavior.
- After terminal-green deployment, deeper #77 work should be issue-specific: either close/update stale umbrella text by owner decision, or release one concrete shared integration/admin/RBAC slice with its own acceptance gates.
