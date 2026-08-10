# Payload projection and worker-topology decision

Source program: GitHub issue #323. Requirement: `TEST-166`.

## Decision

The deployed process topology remains one Gunicorn worker with two threads. The repository's fail-closed multiprocess inventory (`TEST-160`) still classifies a second worker as blocked, so this slice does not change worker, thread, pool, service, provider, or production settings.

The current client instead reduces repeated response work through two explicit compatibility projections:

- `/api/v1/casino/state?projection=shell` returns only application version, descriptor-driven games, and the server-owned online count. It does not load the full player, recent-history, recent-ledger, or duplicate catalog summaries that the shell never reads.
- Roulette requests `projection=play` on state-bearing calls. Those responses retain game state, player, scoreboard, statistics, ledger, round, and settlement data while omitting only the immutable mode-specific bet catalog. The frontend loads that catalog through the existing `/api/v1/games/roulette/bet-catalog` route once per wheel mode and reuses it across actions and remounts.

## Compatibility boundary

The complete frozen-v1 responses remain the default. Unknown, malformed, or duplicate projection values do not activate compact behavior. No game rule, wager, payout, settlement, state persistence, identity, or authorization path changes.

## Acceptance budget

Listener-free `PERF-PAYLOAD-PROJECTION-001` evidence requires the shell projection to be less than half the deterministic full-response size and the Roulette play projection to be less than one quarter of the corresponding response when measured against bounded representative fixtures. It also proves compact shell requests never call the omitted storage owners and that every state-bearing Roulette route shares the same projection boundary.

The Roulette frontend suite additionally proves the catalog is loaded once for the active mode and reused after a real route remount. Normal exact-head API, contract, Browser, Long, requirements, version, module-boundary, comment-density, and diff gates remain mandatory.

## Remaining operational evidence

This repository change does not claim the issue's production latency targets or authorize a production load test. Those targets require comparable isolated-provider or separately authorized read-only operational evidence. Scaling stays on the current topology unless that evidence shows a need for an owner cost/topology decision.
