# Virtual Casino Simulator v9.1.1

## v9.1.1 repository bootstrap

This payload adds GitHub/Codex governance, module manifests, API contract skeletons, validation scripts, GitHub workflows, and the mandatory commenting policy. It does not intentionally change gameplay behavior from the v9.1.0 baseline.


Local play-token virtual casino with Roulette, Slots, Blackjack, Baccarat, Keno, and American Bingo.

## Run

Windows:

```text
Run Virtual Casino.bat
```

macOS:

```text
Run Virtual Casino.command
```

Admin console:

```text
http://127.0.0.1:8765/admin
```

## v9.1.0 gameplay baseline highlights

- Separated bot controller architecture.
- Redesigned `/admin` control plane.
- Global Sound & Voice settings live in Admin.
- Central autoplay sessions with working Stop behavior.
- Roulette wheel no longer defaults to fake zero state.
- Layout-stability changes reduce screen jerk during play.
- Requirement registry now includes 344 numbered requirements.

## Tests

API and rule tests:

```bash
python verify_rules.py
python tests/run_tests.py --api
```

Browser tests:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 tests/run_tests.py --browser
```

## Documents

- `docs/codex_parallel_workflow.md`
- `docs/requirements_validation_v9_1.pdf`
- `docs/requirements_validation_v9_1.md`
- `docs/requirements.json`
- `ARCHITECTURE.md`
- `RELEASE_NOTES.md`
