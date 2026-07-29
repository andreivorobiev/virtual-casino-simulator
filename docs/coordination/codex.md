# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-29T20:17:47Z.

## Current branch / active Codex work

- Immutable v0.9.5.34 is terminal green at exact protected and deployed main `3b6b82f3`.
- `codex/323-request-latency-baseline` owns the active bounded issue #323 listener-free JSON/MySQL request-latency baseline from exact v0.9.5.34.
- The branch is implementation-only and has no ready, merge, release, deployment, provider, ingress, or settings authority.

## Live queue snapshot

- #435 rank 001 remains externally blocked, #450 remains held/excluded, and #471 rank 003 remains blocked on #430 Phase 0c.
- #323 is P1 stack-rank 005 and is the highest actionable owner-released lane.
- The exact owned source surface is `tests/request_latency_benchmark.py`, `tests/unit/request_latency_benchmark_tests.py`, one optional callback seam in `tests/mysql_migration_live.py`, and minimal explicit selection/registration in `tests/run_tests.py`.

## Requirement / version claims

- TEST-148 is allocated only to the #323 request-latency baseline after live main/open-head collision readback.
- The proposal allocates tests/docs `1.64.34` from current `1.64.33`.
- Application `9.53.21`, core `9.28.0`, storage, contracts `1.49.18`, tooling `1.21.12`, every game module, and packaged application `0.9.5.34` remain unchanged.

## File claims / collision notes

- The baseline opens no listener and changes no application route, provider implementation, pool default, runtime, contract, game, deployment, or production surface.
- MySQL runs only inside the existing disposable loopback migration lifecycle after grants and before its unchanged cleanup; JSON uses external temporary state.
- #450, Claude worktrees, provider/public/DNS/billing/signup/OAuth/mail/invitation/ingress, Browser/Chromium, and every unrelated issue remain excluded.

## Decisions / handbacks

- Durable issue claim: `https://github.com/andreivorobiev/virtual-casino-simulator/issues/323#issuecomment-5122886053`.
- Evidence is aggregate-only and atomic outside the checkout; no latency threshold is introduced.
- Ordinary `--api` runs only TEST-148 unit/policy proof. Provider measurements require the explicit request-latency selector and output path.
