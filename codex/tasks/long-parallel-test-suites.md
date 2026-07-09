# Long Parallel Test Suites

## Goal

Add long-running casino validation suites with 100, 300, and 500 scenario profiles. Every scenario must exercise Roulette, Slots, Blackjack, Baccarat, Keno, and Bingo.

## Requirement IDs

- `TEST-031`: suite profiles for 100, 300, and 500 scenario runs.
- `TEST-032`: every scenario plays every game.
- `TEST-033`: deterministic shard-count and shard-index execution.
- `TEST-034`: disposable deployment copy support with cleanup.
- `TEST-035`: JSON reports with scenario, game, and requirement touch counts.
- `AUDIO-008`: browser audio verification observes voice and sound-effect events.
- `AUDIO-009`: repeated Baccarat announcements complete without being cancelled.

## Owned Files

- `tests/long_suites.py`
- `docs/long_test_suites.md`
- `docs/requirements/requirements.json`
- `docs/requirements/requirements_generated.md`
- `web/core/voice.js`
- `modules/tests.json`
- `modules/audio.json`
- `modules/docs.json`
- `modules/module-manifest.json`
- `casino/module_versions.py`

## Non-Goals

- No gameplay rule changes.
- No API contract changes.
- No ledger behavior changes.
- No game-engine imports or module-boundary changes.

## Validation

- Syntax checks for `tests/long_suites.py`, `casino/module_versions.py`, and `web/core/voice.js`.
- Existing bootstrap, API, browser, contract, boundary, requirement, version, docs, and comment-density validations.
- Long-suite deployment-copy smoke with cleanup verification.
- Full Suite 100 API deployment-copy run with preserved JSON report.

## Notes

Parallel long-suite runs must use `--copy-deployment` so each worker has an isolated runtime data directory. Same-checkout parallel runs are guarded by `logs/test-runs/long_suite_runtime.lock`.
