# Virtual Casino Simulator v9.1.0 Release Notes

## Release name
Control Plane + UX Stabilization Release

## Summary
v9.1.0 fixes the major control and UX issues identified after v9.0.0. It separates bot controllers from game modules, moves global sound and voice configuration into `/admin`, redesigns the admin console, centralizes autoplay, fixes the Roulette wheel result state, and stabilizes game screen layouts during actions.

## Module revisions

| Module | Revision |
|---|---:|
| Application | 9.1.0 |
| Core | 9.1.0 |
| Ledger | 9.0.1 |
| Players | 9.0.1 |
| Bot Controller | 1.0.0 |
| Autoplay Controller | 1.1.0 |
| Audio / Voice | 9.1.0 |
| Logging | 9.1.0 |
| Roulette | 9.1.0 |
| Slots | 9.0.1 |
| Blackjack | 9.0.1 |
| Baccarat | 9.0.1 |
| Keno | 9.0.1 |
| Bingo | 9.0.1 |
| Admin | 1.1.0 |
| Tests | 1.1.0 |
| Docs | 1.1.0 |

## Changes

### Bot controller separation
- Added `casino/bots/` with bot profiles, capabilities, strategies, and controller actions.
- Removed per-game bot settings endpoints from Roulette, Baccarat, Keno, and Bingo.
- Added `/api/v1/bots`, `/api/v1/bots/capabilities`, `/api/v1/games/{game_id}/eligible-bots`, and `/api/v1/games/{game_id}/bots/play-round`.
- Games no longer own bot configuration. Bots are controllers for player accounts.

### Global audio and voice
- Added persisted audio settings under `data/settings/audio.json`.
- Moved full sound and voice controls to `/admin -> Audio & Voice`.
- Roulette no longer renders the voice settings panel.
- Added master mute, SFX volume, voice volume, selected voice, rate, pitch, and per-game announcement toggles.

### Admin redesign
- Rebuilt `/admin` as a sidebar/topbar control plane.
- Added Dashboard, Players & Bots, Ledger, History, Telemetry, Game States, Audio & Voice, Autoplay, Requirements, Tests, and System tabs.
- Added editable bot strategies and stakes in Admin.
- Added Admin Stop All Autoplay.

### Autoplay controller
- Added server-registered autoplay sessions with `autoplay_id`.
- Added `/api/v1/autoplay/start`, `/stop`, `/tick`, `/complete`, `/finish-stop`, `/stop-all`, and session listing endpoints.
- Reworked browser autoplay to use shared session state and a central stop contract.
- Stop now prevents the next action from starting after the current atomic action is safe.
- Bingo autoplay now uses stepwise ball calls rather than one long auto-to-Bingo call.

### Roulette wheel and UX
- Roulette wheel no longer defaults to a fake `0` state when there has not been a spin.
- Roulette wheel highlights the latest actual spin result.
- Roulette bot actions happen through the bot controller before the spin.
- Added layout-stability styles for game stages, controls, result panels, and autoplay panels.

### Tests and documentation
- Requirement registry increased from 287 to 344 requirements.
- Added new `BOT`, `AUDIO`, `AUTO`, and `UX` requirement families.
- Updated API tests for bot controller, audio persistence, and autoplay lifecycle.
- Updated browser tests for Admin Audio and Roulette autoplay stop behavior.
- Generated `docs/requirements_validation_v9_1.pdf` and `docs/requirements_validation_v9_1.md`.

## Validation run in packaging environment

```bash
python -m py_compile run.py $(find casino -name '*.py') verify_rules.py tests/run_tests.py
python verify_rules.py
python tests/run_tests.py --api
node --check web/app.js
node --check web/core/*.js
node --check web/games/*.js
node --check web/admin.js
```

## Browser tests on your machine

```powershell
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 tests/run_tests.py --browser
```

## Known limitations
- Blackjack autoplay remains disabled unless a dedicated Blackjack strategy controller is added later.
- This is still fake-money entertainment software only; it has no real-money or regulated casino functionality.


## Documentation refresh
- Replaced the requirements/validation PDF with a redesigned landscape report.
- Split diagrams into separate clean views with non-overlapping connectors.
- Added clearer summaries, module tables, and requirement registry formatting.


## v9.1.1 - Repository Bootstrap + Codex Migration Payload

- GitHub/Codex governance payload added.
- Module manifests and API contract skeletons added.
- Commenting policy and checker added.
- CI workflow scaffolding and Codex prompts added.
- No intentional gameplay behavior changes from v9.1.0.
