# Long Casino Test Suites

The long-suite runner lives at `tests/long_suites.py` and is intended for deployment-style validation, not quick local smoke checks.

## Suite Profiles

| Suite | Logical scenario tests | Minimum requirement touches | Default Baccarat audio repeats |
| --- | ---: | ---: | ---: |
| `100` | 100 | 10 | 10 |
| `300` | 300 | 20 | 20 |
| `500` | 500 | 30 | 30 |

Every scenario plays every game in the catalog, not a fixed subset: `load_game_drivers()` iterates `casino.config.GAMES` rather than a central allowlist, so the per-scenario work grows with the descriptor-driven catalog. Size a run accordingly. The runner also touches Admin audio settings, autoplay start/stop, and the requirements registry so the JSON report can prove requirement touch counts.

## Deployment-Style Run

Use a disposable environment when you want the run to behave like a deployment:

```powershell
$py = "C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py tests/long_suites.py --suite 100 --copy-deployment
```

By default, copied environments are created under `C:\Users\andre\Documents\Codex\casino-environments` and are deleted after the run. Add `--keep-env` only when debugging a failed environment.

## Pull Request Build

Suite `100` is wired into `.github/workflows/long-suite-100.yml` and runs on every pull request as four parallel matrix shards plus one aggregate gate job. The gate job reports the exact `Long Suite 100 / long_suite_100` check context that repository branch protection requires, and it fails unless every shard succeeded, so the required check can never pass vacuously.

Each shard runs:

```powershell
python tests/long_suites.py --suite 100 --shard-count 4 --shard-index <N> --copy-deployment
```

Shard `0` includes the browser audio verification path; shards `1` through `3` pass `--skip-browser-audio` and focus on API/gameplay volume, mirroring the soak lane. The four modulo partitions contain exactly 25 scenarios each with no overlap, while per-shard JSON reports are retained outside their disposable deployment copies under unique artifact names.

Superseded ordinary runs for the same pull request are cancelled automatically by workflow-and-PR concurrency groups. Main pushes and manual dispatches fall back to unique run IDs, so they cannot cancel each other or formal 50,000-cycle, Baccarat sustained, release, deployment, or manually selected soak work. Browser Tests includes its own workflow file in the pull-request path filter so execution-policy edits always receive fresh exact-head browser evidence.

## Browser Harness Knobs

Ordinary Playwright readiness waits use the single `CASINO_BROWSER_WAIT_MS` value declared in `.github/workflows/browser-tests.yml`; `tests/browser_timing.py` validates the same optional environment input for local runs and defaults to five seconds. Longer historical ten-second waits derive as `WAIT_MS * 2`. The parser rejects non-decimal, unsafe, or unbounded overrides, and source governance rejects reintroduced `timeout=5000` or `timeout=10000` literals. Changing the hosted wait budget is therefore one reviewed workflow-line edit rather than a sweep across Browser cases.

`tests/cicd_deployment_tests.py` owns the one ordinary Browser shard-count oracle used by its synthetic packets and CLI arguments. Exactly one named alignment test compares that constant with the workflow matrix and both worker/aggregate arguments; changing the constant produces one focused policy failure until `.github/workflows/browser-tests.yml` is updated. Exact shard union and affinity validation remain fail closed.

`.github/workflows/browser-duration-profile.yml` runs weekly and supports manual dispatch. It selects the newest successful protected-main Browser push, downloads only its ordinary shard artifacts, regenerates `tests/browser_case_durations.json` through the strict bounded parser, and runs the listener-free CI/CD policy suite. An unchanged profile publishes nothing, and any existing automated profile branch or pull request suppresses a duplicate. A changed profile creates one maintenance issue, pushes a run-owned branch containing only the profile, and opens a draft pull request that closes that issue only after review. Because GitHub suppresses recursive `pull_request` events for its workflow token, the publisher explicitly dispatches all nine unchanged qualification workflows against the exact branch head; the unpublished release-candidate lane receives the canonical packaged version and cannot publish. It never pushes directly to `main` or merges itself.

The former mega-groups are now reduced, contiguous families: public Auth, authenticated session, lobby shell, Roulette, Slots, Keno, table games, feedback/Admin operations, and Admin presentation. Each family establishes its own required anonymous, authenticated, game-route, or protected-Admin starting state before its first case, so duration packing can assign families independently without inheriting another shard's page or session state. With the reviewed duration profile, the maximum packed load drops from 219 seconds at six shards to 187 at seven and 165 at eight, crossing below the old 178-second floor. The reviewed case count, sorted IDs, source order, affinity validation, and aggregate shard-union gate remain unchanged.

## Parallel Shards

Ten workers can split Suite 500 like this:

```powershell
$py = "C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py tests/long_suites.py --suite 500 --shard-count 10 --shard-index 0 --copy-deployment
```

Launch shard indexes `0` through `9` in separate workers. Sharding is deterministic: scenario `n` belongs to worker `n % shard_count`.

Do not run parallel long suites against the same checkout. The runner creates a per-tree lock under `logs/test-runs/long_suite_runtime.lock` so accidental same-folder parallelism fails clearly instead of racing on `data/`. Use `--copy-deployment` for each worker to give every shard its own runtime data directory.

## Manual 300/500 Soak

`.github/workflows/long-suite-soak.yml` is a manual workflow. GitHub prompts for either Suite `300` or Suite `500`, then launches ten matrix shards with isolated disposable deployment copies. Shard `0` runs browser audio verification; shards `1` through `9` skip browser audio and focus on API/gameplay volume.

## Focused Baccarat 2,000-Round Qualification

Issue #265 has a stricter browser gate than the ordinary Baccarat smoke and the full-catalog allocation: one uninterrupted exact-source session must complete 2,000 consecutive settled-to-wager-ready coups through rendered controls. Acceptance evidence must come from one explicitly authorized `Browser Tests` workflow dispatch at the exact candidate head with `baccarat_sustained_2000=true` and `formal_ui_50000=false`. The hosted job invokes the immutable profile entry point:

```powershell
python -m tests.baccarat_sustained --output-root logs/test-runs/baccarat_sustained --progress-every 100
```

`BR-BAC-SUSTAINED-001` fixes the `BAC-026` / `TEST-099` profile at one disposable loopback runtime, one synthetic account, one browser context, exactly 2,000 Baccarat rounds, and one attempt per round. Every round places and clears a visible wager, places a fresh wager, activates the visible Deal control, and requires the next Deal control to become genuinely enabled after settlement. Any missing/replaced Deal target, wager-ready timeout, recovered retry, selected-game control shortfall, browser diagnostic, wallet/account isolation failure, incomplete governed screenshot inventory, or listener/runtime cleanup failure makes the report fail. Catalog nav/open controls for registered games deliberately excluded by this focused profile are recorded as out of scope; the selected Baccarat route and every full-catalog `TEST-092` control remain governed by the ordinary activation floor. Do not dispatch the hosted profile twice at one head; a failed run must be diagnosed and repaired before a separately authorized rerun.

The terminal report is written under `logs/test-runs/baccarat_sustained/` and records the exact 40-character source commit, `BR-BAC-SUSTAINED-001`, `BAC-026`, `TEST-099`, exact Deal activation count, cycle range, failure counters, isolation, and cleanup status. The profile uses disposable synthetic data only; it must never target restricted preview, production MySQL, live accounts, public endpoints, paid resources, or provider infrastructure.

## Audio Verification

Browser audio verification is enabled by default. It instruments `speechSynthesis` and `AudioContext` in Playwright, then verifies:

- voice events are observable without physical speakers;
- sound-effect paths emit events;
- repeated Baccarat deals produce matching voice starts and completions;
- no `voice_cancel` event occurs during the repeated Baccarat run.

Use `--skip-browser-audio` only for API-only stress runs where another worker is already covering `LONG-AUDIO-001`.

## Reports

Reports are written to `logs/test-runs/long_suite_<suite>_shard_<index>_of_<count>.json` unless `--json-report` is supplied. Reports include scenario evidence, per-game play counts, requirement count, minimum requirement touches, and audio event counts.
