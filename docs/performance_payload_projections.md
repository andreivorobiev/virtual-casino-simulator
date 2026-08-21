# Payload projection and worker-topology decision

Source program: GitHub issue #323. Requirement: `TEST-166`.

## Decision

The reviewed process topology is one Gunicorn worker with sixteen threads and a sixteen-slot MySQL pool. `TEST-251` separately exercises a one-worker/32-thread qualification profile without changing production, provider, or deployment settings. A second worker multiplies the process-local connection ceiling and remains blocked until a target-specific connection-budget review passes.

The current client instead reduces repeated response work through two explicit compatibility projections:

- `/api/v1/casino/state?projection=shell` returns only application version, descriptor-driven games, and the server-owned online count. It does not load the full player, recent-history, recent-ledger, or duplicate catalog summaries that the shell never reads.
- Roulette requests `projection=play` on state-bearing calls. Those responses retain game state, player, scoreboard, statistics, ledger, round, and settlement data while omitting only the immutable mode-specific bet catalog. The frontend loads that catalog through the existing `/api/v1/games/roulette/bet-catalog` route once per wheel mode and reuses it across actions and remounts.

## Compatibility boundary

The complete frozen-v1 responses remain the default. Unknown, malformed, or duplicate projection values do not activate compact behavior. No game rule, wager, payout, settlement, state persistence, identity, or authorization path changes.

## Acceptance budget

Listener-free `PERF-PAYLOAD-PROJECTION-001` evidence requires the shell projection to be less than half the deterministic full-response size and the Roulette play projection to be less than one quarter of the corresponding response when measured against bounded representative fixtures. It also proves compact shell requests never call the omitted storage owners and that every state-bearing Roulette route shares the same projection boundary.

The Roulette frontend suite additionally proves the catalog is loaded once for the active mode and reused after a real route remount. Normal exact-head API, contract, Browser, Long, requirements, version, module-boundary, comment-density, and diff gates remain mandatory.

## Exact-source target gate

Hosted CI now produces comparable listener-free JSON and disposable-MySQL evidence from the exact checkout and fails closed unless every single-request warm authenticated game-state read stays at or below 100 ms p50 and 200 ms p95, while every concurrency-four game-state read stays at or below 250 ms p95 and strictly above the recorded 3.37 requests-per-second baseline. The same job retains both aggregate-only packets and one sanitized acceptance decision under `TEST-170`; the idempotent Boule write and concurrency-eight rows remain diagnostic rather than being mislabeled as the issue's read targets.

The accepted multiprocess inventory still blocks a second worker, and the payload projections already satisfy their reduction budgets. Therefore the completed target gate keeps the deployed one-worker/two-thread topology instead of turning a performance program into an unreviewed cost or process-safety change.
