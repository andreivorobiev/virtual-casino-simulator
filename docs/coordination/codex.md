# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T15:25:55Z.

## Current branch / active Codex work

- Protected main and terminal-green production are exact v0.9.5.38 `69995920`.
- `codex/430-mysql-schema3-receipts` preserves accepted checkpoint `d1c3bab1` as a direct child of that exact main and adds only governed schema-three capacity registration.
- The branch remains draft-only until exact-head local and hosted qualification completes; Integration alone may ready, merge, release, or deploy it.

## Live queue snapshot

- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 remains blocked on the remaining #430 MySQL composite and adoption sequence.
- Issues #430 and #471 remain open; this capacity checkpoint does not close either issue.
- Thirteen open PRs have no direct collision with the accepted eight substantive paths, while shared governance collisions remain sequencing-only and must rebase later.

## Requirement / version claims

- `MYSQL-007` is the only new permanent requirement and maps to existing central cases `MYSQL-MIGRATION-001` and `MYSQL-MIGRATION-LIVE-001`.
- Tooling advances compatibly from `1.21.12` to `1.22.0`; tests and docs advance from `1.64.42` to `1.64.43`.
- Package `0.9.5.38`, application `9.53.25`, core `9.31.0`, admin `1.13.3`, contracts `1.49.23`, storage, games, and every unrelated module remain unchanged.
- No STORAGE, CORE, TOOL, or generic TEST requirement ID is allocated.

## File claims / collision notes

- The accepted eight substantive files remain byte-identical to checkpoint `d1c3bab1`.
- Governance is limited to requirements source/generated output, tooling/tests/docs descriptors and aggregate manifest, central case mapping, version fixture, and Codex coordination.
- The complete branch ceiling is eighteen files and imports no hunk from #520, #524, #528, #525, #526, #518, #506, #483, #460, #454, excluded #450, or any stale checkpoint.

## Decisions / handbacks

- Schema three provisions checksum-bound exact action identity, request fingerprint, declared resources, complete paid-or-zero-cost receipt JSON, receipt SHA-256, and live UPDATE and DELETE refusal.
- `schema_state_digest()` does not bind CHECK clauses or trigger definitions; exact post-apply guard inspection or digest binding is a mandatory later migration-readiness dependency.
- No MySQL runtime provider, composite atomicity, route, game, Slots, ledger, saga, journal, production, release, deployment, scaling, or issue-closure claim is made.
