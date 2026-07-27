# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-27T23:42:00Z.

## Current branch / active Codex work

- Codex integration is preparing `codex/release-v0.9.5.20` from exact accepted owner-RBAC main `12c8a670`.
- Scope is the unique immutable patch identity, PWA rotation, release provenance, and governed release documentation required before the next serial merge.
- Permanent claims `AUTH-012`, `ADMIN-028`, and `TEST-138` are now on protected main through merged PR #455.
- No browser-visible feature work, provider change, DNS, billing, public signup, live OAuth, mail activation, invitation, public-exposure, credential, SSH-ingress, or direct deployment mutation is included.

## Live queue snapshot

- Accepted protected main before this release branch is `12c8a670`, containing merged PR #455.
- Immutable v0.9.5.19 at `bceb5298` remains the exact deployed predecessor until v0.9.5.20 is qualified and deployed.
- #450 remains an excluded deployment-workflow draft.
- Claude PR #453 still carries a later duplicate `TEST-138` claim and Claude PR #460 still carries later duplicate `ADMIN-028` and `TEST-138` claims; those branches must re-splice rather than displace #455's earlier durable reservations.
- #460 also touches `casino/admin.py`, but its current game-state hunk is disjoint from #455's owner-RBAC helpers and routes. Codex is not editing the Claude branch.

## #77 / #73 / #66 catalog interpretation

- The installed catalog is descriptor-discovered from `modules/<game-id>.json`; protected main currently has 46 playable game descriptors.
- `GAME_CATALOG_TARGET = 20` is a historical readiness floor/reporting target, not a cap and not a command to add duplicate catalog infrastructure.
- #73 remains the game-portfolio umbrella for catalog quality and future expansion beyond the installed set.
- #77 remains the serialized shared-integration lane for descriptor promotion, shared catalog collision surfaces, requirements/test discovery, compatibility metadata, and acceptance evidence.
- #66 remains the broader program epic tying catalog work to multi-user, storage, operations, and release readiness.

## Requirement / TEST ID renames at merge

- No existing identifier is deleted or reused.
- #455 retains its earlier durable `AUTH-012`, `ADMIN-028`, and `TEST-138` allocations.
- Later duplicate claims in #453 and #460 must move to unique identifiers before those PRs can qualify.

## File claims / collision notes

- The release branch owns only packaged-version, PWA, compatibility, release-test, requirements, generated-doc, and release-documentation surfaces.
- Shared governance files are rebuilt from exact owner-RBAC main `12c8a670`, preserving merged #431/#323 and v0.9.5.19 release state.
- Codex is not landing games, touching Claude branches, changing #453/#454/#460/#465, or editing #450.

## Decisions / handbacks

- PR #455 merged normally with exact-head checks and zero unresolved review threads.
- This release packages the accepted server-side owner-gated Admin authority foundation without a database-schema migration or broader provider/public mutation.
- The parent #351 was reopened and remains open for frozen-v1 compatibility, Administrators-area UI, recent-reauth, idempotency, session, audit, MySQL, and browser evidence.
- After terminal-green deployment, the highest-priority eligible Worker A, Worker B, or Claude handback may enter the next serialized merge slot after current-main reconciliation.
