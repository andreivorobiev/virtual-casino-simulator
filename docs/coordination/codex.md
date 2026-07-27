# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-27T23:07:35Z.

## Current branch / active Codex work

- Codex is reconciling draft PR #455 / issue #351 on `codex/351-owner-rbac-core` from exact terminal-green v0.9.5.19 main `bceb5298`.
- Scope remains the bounded server-side owner-authority foundation: bootstrap-owner migration, additive-v2 owner-only Admin grants and revocations, frozen-v1 compatibility, transaction safety, session revocation, and listener-free regression proof.
- Permanent claims remain `AUTH-012`, `ADMIN-028`, and `TEST-138`; they were reserved durably on #351 before branch mutation.
- No browser-visible UI, provider change, DNS, billing, public signup, live OAuth, mail activation, invitation, public-exposure, credential, SSH-ingress, merge, release, or deployment mutation is included.

## Live queue snapshot

- Protected main and deployed v0.9.5.19 are exact `bceb5298`, containing merged #431, #323, and release work that #455 preserves.
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

- #455 owns its existing RBAC changes in `casino/admin.py`, `casino/core/auth.py`, the admin-users v2 contract/digest, account-spine tests, requirements, module versions, generated docs, and test discovery.
- Shared governance files are rebuilt from exact v0.9.5.19 main, preserving merged #431/#323/release state.
- Codex is not landing games, touching Claude branches, changing #453/#454/#460/#465, or editing #450.

## Decisions / handbacks

- Live diff and ownership readback found no material source overlap that displaces the explicitly released #455 lane.
- #455 remains draft and will return for exact-head validation and zero-thread handoff only; Codex will not ready, merge, release, or deploy it in this pass.
- The parent #351 remains open after this server foundation for its separately governed compatibility and Administrators-area UI work.
