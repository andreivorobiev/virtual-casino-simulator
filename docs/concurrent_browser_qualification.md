# Concurrent browser qualification

Issue #225 owns the opt-in `BR-CONCURRENT-100-001` profile. It is qualification infrastructure,
not a production tuning or deployment path.

## Safety boundary

The runner accepts only an exact clean source checkout, an explicit `CASINO_225_DISPOSABLE=1`
marker, and a `CASINO_DATA_DIR` outside the repository. It binds its HTTP server only to loopback,
creates reserved-domain synthetic accounts, keeps credentials in process memory, and deletes the
complete test-owned data root after the exact listener closes. It does not target preview,
production, a public endpoint, a real account, a provider, or paid infrastructure.

The hosted job is disabled by default. It can run only through the Boolean
`concurrent_browser_100` workflow-dispatch input. Ordinary pull requests run the listener-free
planner, barrier, artifact, workflow, and safety tests but do not launch the 100-context profile.

## Observability-first sequence

The explicit hosted job runs the existing disposable-MySQL `TEST-141` packet first at concurrency
1, 2, 4, and 8. That packet records only p50, p95, throughput, errors, capacity, in-use, idle,
waiting, physical-created, reuse, discard, wait, timeout, rollback-cleanup, connector-error, and
fixed wait-bucket values. The browser controller accepts the preflight only when it is bound to the
same full source commit, contains all four levels, has zero errors and timeouts, leaves no lease or
waiter residue, and keeps physical creation within capacity.

The browser run then provisions exactly 100 users through the setup-only Admin API, creates 100
independent Chromium contexts, waits for all contexts at the rendered login gate, and releases
them together. Every task authenticates through the visible form, navigates through catalog UI,
and invokes the existing game-owned DOM driver for one complete action. Backend calls after the
run inspect only aggregate wallet, player-binding, ledger-identity, and action-key invariants.

Terminal evidence contains no per-user rows. It reports aggregate login and gameplay p50, p95,
p99, maximum, barrier population, peak gameplay, assigned and successful game counts, grouped
browser/page/HTTP failures, duplicate identifiers, nonnegative wallets, pool counters, context
closure, listener closure, and exact source commit.

## Current acceptance blocker

The issue was written when its acceptance criterion named 30 registered games and required at
least three concurrent users per game. Protected main now registers 46 games. Three users for
every current game requires 138 contexts, while the same issue requires exactly 100.

The planner keeps both literal constraints and therefore fails before opening a listener or
browser:

```text
catalog coverage requires 138 users (46 games x 3) but the formal profile requires exactly 100
```

The profile must not be dispatched until the owner chooses one coherent criterion. Valid choices
include preserving exactly 100 users with a lower current-catalog floor, preserving three users
per current game with an exact 138-user run, or defining a governed 30-game qualification subset.
This repository slice does not choose among those product-governance options and does not claim a
passing 100-browser result.

## Multi-process boundary

The MySQL pool is process-local. Possible physical connections equal worker processes multiplied
by configured pool capacity. This slice does not add a Gunicorn worker or change thread count.
Any later second-worker experiment must first budget aggregate physical connections, retain the
same fixed-cardinality measurements, and repeat the synchronized browser qualification in a
separately authorized disposable environment.
