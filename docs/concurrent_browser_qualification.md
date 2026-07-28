# Concurrent browser qualification

Issue #225 owns the opt-in `BR-CONCURRENT-138-001` profile. It is qualification infrastructure,
not a production tuning or deployment path.

## Safety boundary

The runner accepts only an exact clean source checkout, an explicit `CASINO_225_DISPOSABLE=1`
marker, and a `CASINO_DATA_DIR` outside the repository. It binds its HTTP server only to loopback,
creates reserved-domain synthetic accounts, keeps credentials in process memory, and deletes the
complete test-owned data root after the exact listener closes. It does not target preview,
production, a public endpoint, a real account, a provider, or paid infrastructure.

The hosted job is disabled by default. It can run only through the Boolean
`concurrent_browser_138` workflow-dispatch input. Ordinary pull requests run the listener-free
planner, barrier, artifact, workflow, and safety tests but do not launch the 138-context profile.
The job installs both the `mysql` and `recovery` optional dependency groups before TEST-141 so
the disposable preflight has its connector and the required encrypted-recovery backend.

## Observability-first sequence

The explicit hosted job runs the existing disposable-MySQL `TEST-141` packet first at concurrency
1, 2, 4, and 8. That packet records only p50, p95, throughput, errors, capacity, in-use, idle,
waiting, physical-created, reuse, discard, wait, timeout, rollback-cleanup, connector-error, and
fixed wait-bucket values. The browser controller accepts the preflight only when it is bound to the
same full source commit, contains all four levels, has zero errors and timeouts, leaves no lease or
waiter residue, and keeps physical creation within capacity.

The browser run then provisions exactly 138 users through the setup-only Admin API. It admits at
most 12 concurrent context-creation and public-shell navigation operations, releases each setup
slot after that independent context reaches the rendered login gate, waits for all 138 contexts,
and releases them together. This pre-barrier admission prevents browser startup from exhausting
the disposable runner without weakening the synchronized 138-context gameplay requirement.

Every task authenticates through the visible form, navigates through catalog UI, and invokes one
bounded game-owned DOM driver for a complete action. The qualification supplies explicit
one-action drivers for the fifteen catalog games that were absent from the inherited long-suite
driver, while retaining the inherited driver for the other thirty-one games. Expected anonymous
`GET /api/v2/me` 401 bootstrap and hydration probes are ignored only until the real rendered
login succeeds; the same failure after authentication remains a red diagnostic. Backend calls
after the run inspect only aggregate wallet, player-binding, ledger-identity, and action-key
invariants.

Terminal evidence contains no per-user rows. It reports aggregate login and gameplay p50, p95,
p99, maximum, setup admission limit and peak, barrier population, peak gameplay, assigned and
successful game counts, grouped browser/page/HTTP failures, duplicate identifiers, nonnegative
wallets, pool counters, context closure, listener closure, and exact source commit.

## Exact catalog coverage

The issue was written when its acceptance criterion named 30 registered games and required at
least three concurrent users per game. Protected main now registers 46 games. Three users for
every current game requires exactly 138 contexts. The owner selected that exact 138-user
population, preserving the three-users-per-game invariant without a subset or lowered floor.

The planner therefore requires all 46 registered games, exactly 138 synthetic users, and exactly
three deterministic assignments for every game. It rejects shortened or expanded populations
before opening a listener or browser. Catalog growth is also fail-closed: a future game addition
requires a separately governed population change before the hosted qualification can pass.

## Multi-process boundary

The MySQL pool is process-local. Possible physical connections equal worker processes multiplied
by configured pool capacity. This slice does not add a Gunicorn worker or change thread count.
Any later second-worker experiment must first budget aggregate physical connections, retain the
same fixed-cardinality measurements, and repeat the synchronized browser qualification in a
separately authorized disposable environment.
