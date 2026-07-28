# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T02:52:00Z.

## Current branch / active Codex work

- Codex integration owns `codex/release-v0.9.5.21` from exact accepted session-control main `39e87bc6`.
- Scope is the unique immutable patch identity, PWA rotation, compatibility provenance, release tests, and governed documentation required before the next serialized merge.
- Permanent claims `SESSION-008` and `TEST-143` are now on protected main through merged PR #474.
- No Admin route, browser UI, provider configuration, schema migration, production mutation, or direct deployment is included.

## Live queue snapshot

- Accepted protected main before this release branch is `39e87bc6a95d5e7894403aed64d0332975580c7b`, containing merged PR #474.
- Immutable v0.9.5.20 at `dc5a4274` remains the exact deployed predecessor until v0.9.5.21 is qualified and deployed.
- PR #467's single authorized 138-browser qualification failed during dependency preflight before browsers or listeners started; it requires a fresh repaired head and new rerun authorization.
- Claude PR #473 carries stale shared versions and reuses merged `TEST-141`; it must reconcile and allocate a fresh permanent TEST ID before qualification.
- #450 remains an excluded deployment-workflow draft.

## Requirement / TEST ID claims

- No existing identifier is deleted or reused.
- `SESSION-008` and `TEST-143` remain assigned to the merged server-side session-control foundation.
- `TEST-139` remains reserved for the separately coordinated Claude #453 re-splice; open PR #467 owns `TEST-142`.

## File claims / collision notes

- The release branch owns only packaged-version, PWA, compatibility, release-test, requirements, generated-doc, localization, and release-documentation surfaces.
- Shared governance files are rebuilt from exact accepted session-control main `39e87bc6`, preserving merged #474 and all earlier terminal-green release state.
- Codex is not touching #450/#453/#454/#460/#465/#467/#470/#473 or any Claude/Worker branch.

## Decisions / handbacks

- PR #474 merged normally after independent strict-JSON repair review, fresh exact-head checks, and zero comments, reviews, or threads.
- This release packages the route-free session-control core without activating an Admin route, browser UI, or API contract.
- Exact immutable v0.9.5.20 remains the application-only predecessor; MySQL schema 2 remains exact and database rollback remains prohibited.
- Issue #351 remains open for Admin authorization/routes, reason capture, recent reauthentication, request idempotency, durable audit history, separate Administrators UI, EN/RU browser/accessibility evidence, and additive v2 contracts.
- After terminal-green deployment, the next exact-current-main eligible Worker A, Worker B, or Claude handoff may enter the serialized merge lane.
