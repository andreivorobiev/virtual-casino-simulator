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

Suite `100` is wired into `.github/workflows/long-suite-100.yml` and runs on every pull request. Treat the `Long Suite 100 / long_suite_100` check as mandatory once repository branch protection is updated to require it.

The workflow runs:

```powershell
python tests/long_suites.py --suite 100 --copy-deployment
```

This includes the browser audio verification path.

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
