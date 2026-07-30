# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T22:46:34Z.

## Current branch / active Codex work

- Protected main and terminal-green published/released/live production are exact v0.9.5.40 `3d769813`; MySQL remains clean at schema 2 and the held schema-3 migration was not invoked.
- `codex/524-enrollment-enforcement-controller` preserves exact v40 main as first parent and immutable contributor head `271d3615` as second parent through ancestry commit `c3045365`, whose tree equals current main.
- The controller is local and unpushed while bounded signup/invitation enforcement, operational decision-log hardening, contract truth, tests, and fresh governance undergo independent Worker-B review.

## Live queue snapshot

- #435 rank 001 remains externally blocked; #471 rank 003 remains architecture-blocked on separately governed #430 work.
- #333 rank 007 remains open after the read-only/default-off root slice; #524 is the sole active controller lane and #528 remains held and untouched.
- Open #539 collides only on generated requirements and the module manifest; #525 and older heads collide only on shared governance and must rebase or serialize later.
- #450 remains held/excluded; no provider, OAuth, Admin-write, child-stack, public-enable, or production configuration worktree is part of this lane.

## Requirement / version claims

- The controller changes only existing `AUTH-013`, still mapped solely to `API-ENROLLMENT-POLICY-001`; no generic TEST or other permanent ID is allocated.
- Proposed compatible revisions are core `9.34.0`, contracts `1.52.0`, and tests/docs `1.64.48`.
- Package `0.9.5.40`, application `9.53.27`, tooling `1.23.0`, and every unrelated module remain unchanged.

## File claims / collision notes

- Source changes are limited to the current v40 policy and app route seams; contributor source is reconciled manually after an ancestry-only merge, with stale `SIGNUP_ENABLED`/`DATA_DIR` hunks excluded.
- Contract changes are additive auth-v2/restricted-preview enforcement truth plus the authenticated digest; frozen v1 is unchanged.
- Tests bind bounded log values/failures, safe unknown-policy envelopes, exact account-spine routes, and signup/invitation allow-deny behavior without listeners, external providers/provider network, or live enrollment.

## Decisions / handbacks

- Public email signup and invitation redemption enforce the same resolved policy that the read-only endpoint publishes; existing login behavior and frozen v1 remain unchanged.
- Absent, non-mapping, and unowned-schema documents preserve the deployed environment seed/fallback; schema-v1 unknown modes map only the two public mutation routes to their existing safe denial envelopes.
- The existing JSONL sink is bounded operational enrollment-decision logging. It must succeed before account or invitation mutation and is not immutable/provider-backed actor/change audit; that remains deferred to #528.
- Admin mutation, readiness, RBAC, UI, OAuth/provider, live enablement, provider network, public exposure, release, deployment, issue closure, and #528 remain excluded.
