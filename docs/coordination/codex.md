# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T20:34:06Z.

## Current branch / active Codex work

- Protected/released/live production is exact terminal-green v0.9.5.39 `9de0d53c`, with MySQL still clean at schema 2 and the held schema-3 migration uninvoked.
- `codex/520-enrollment-policy-controller` is an isolated replacement lane from exact current main; its ancestry preserves immutable contributor head `f81da5da` without mutating the external `claude/wb-333-enrollment-policy` branch or worktree.
- The controller imports only root #520's read-only/default-off enrollment-policy slice and remains local until independent Worker-B source and governance audit.

## Live queue snapshot

- #435 rank 001 remains externally blocked; #471 rank 003 remains architecture-blocked on separately governed #430 work.
- #333 rank 007 is the highest executable lane through root PR #520 and remains open after this bounded slice.
- Stacked #524/#528 remain held and untouched until the controller replacement merges, receives a unique release, and deploys terminal green.
- #450 remains held/excluded; no contributor, child-stack, provider, public, production, or release worktree is part of this lane.

## Requirement / version claims

- The controller allocates only `AUTH-013`, mapped to existing listener-free case `API-ENROLLMENT-POLICY-001`; no generic TEST or other permanent ID is allocated.
- The compatible-addition targets are core `9.33.0` and contracts `1.51.0`, with tests/docs `1.64.46`.
- Package `0.9.5.39`, application `9.53.26`, tooling `1.23.0`, and every unrelated module remain unchanged.

## File claims / collision notes

- Substantive scope is the contributor-owned policy resolver, the existing additive v2 policy route, focused policy/account-spine proof, strict auth-v2 mode schema, and restricted-preview compatibility v2.
- Shared requirements, generated documentation, module descriptors, runner registration, exact version fixture, contract digest, and Codex coordination are rebuilt only from exact v39 main.
- Open PR #539 adds one new shared generated/manifest collision after the owner packet but carries no `AUTH-013`, case, or target-version collision; every open shared head must rebase after sequencing.

## Decisions / handbacks

- Slice 1 reads a durable provider-backed enrollment policy with exact `closed`, `invite-only`, and `self-signup` modes while preserving the deployed environment as seed and fallback.
- Public enrollment methods remain default-off; the slice adds no Admin write, enforcement, audit, readiness, RBAC, UI, provider, signup, OAuth, mail, invitation, public-exposure, release, or deployment authority.
- `/api/v1` remains unchanged, #333 remains open, and the controller PR must use non-closing language.
- No push or draft PR is permitted until Worker B accepts the exact clean governed head; Integration remains sole ready/merge/release/deploy executor.
