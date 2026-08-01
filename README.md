# Virtual Casino Simulator

Packaged application release: `0.9.5.46`

Historical source baseline: `9.1.0`

Local play-token browser casino simulator with a descriptor-driven catalog of isolated games (Roulette, Slots, Blackjack, Baccarat, Keno, American Bingo and many more; the canonical catalog is discovered from the `modules/*.json` descriptors), isolated game state, ledger-backed wallet accounting, authenticated private-beta users, Admin telemetry, and optional JSON or MySQL persistence.

## Design decisions

- **Descriptor-driven game catalog.** Every game ships a descriptor at `modules/<id>.json` that owns its id, routes, backend callable, and frontend module; the backend, the frontend shell, and the validators all discover the catalog from those descriptors. There is no hardcoded game list anywhere.
- **Game isolation enforced by CI, not by review.** `scripts/validate_module_boundaries.py` scans real Python and JavaScript imports and fails the build on any cross-game import.
- **Exactly-once settlement.** The shared settlement core (`casino/core/simple_game.py`) commits each round's entropy inside the wager's ledger row, so a retry after a lost response replays the recorded outcome instead of redrawing it.
- **Server authority.** `sanitize_game_intent()` strips client-authored outcome fields from every game request, and the per-module `server-authority-matrix.json` is generated and validated in CI.
- **Compliance as a build gate.** `scripts/validate_token_terminology.py` runs in CI and rejects real-money wording in user-facing copy across both locales (en-US and ru-RU).
- **Two-agent development governance.** Claude authors and validates changes as pull requests; Codex independently reviews and is the sole merge executor. Merge duties are separated by policy (`docs/claude_codex_work_division.md`).

## Version sources

`modules/module-manifest.json` is the canonical aggregate version source:

- Top-level `application` is the packaged application release shown by runtime, API, browser, and Admin surfaces. It changes only with a formal application release artifact.
- Entries under `modules` are independent source-module revisions. They must be bumped when their owned source changes and may advance without changing the packaged application release.
- `modules.application` is the application module revision, not the packaged application release.
- Top-level `source_baseline` is historical source provenance and is not a current release number.

Runtime version metadata is loaded by `casino/module_versions.py`; `scripts/validate_versions.py` rejects drift between the aggregate manifest, module manifests, runtime values, package metadata, README, and starter documentation.

## Legal and play-token status

The repository source code is licensed under the Apache License, Version 2.0. See `LICENSE` and `NOTICE`.

The running app is a private beta toy simulator for local play-token use. It is not a gambling site, not real-money play, and not a payment or cash-out product. Play tokens, balances, chips, tickets, cards, spins, winnings, payouts, jackpots, and ledger entries have no cash value and cannot be redeemed, sold, traded, transferred, exchanged, withdrawn, or converted into money, prizes, goods, services, credits, cryptoassets, or anything else of value.

Private beta end-user terms and privacy expectations are documented in `docs/legal/terms.md` and `docs/legal/privacy.md`.

## Brand and marketing customization

Marketing and public brand surfaces are separated from the reusable simulator core. Start with `docs/marketing_customization.md` before renaming the app, replacing icons, adding a landing site, changing public domains, or preparing a downstream fork.

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

## Tests

API and rule tests:

```bash
python verify_rules.py
python tests/run_tests.py --api
```

Browser tests:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/run_tests.py --browser
```

Repository validation:

```bash
python scripts/validate_game_catalog.py
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/validate_contracts.py
python scripts/validate_module_boundaries.py
python scripts/generate_docs.py --check
python scripts/check_comment_density.py
```

## Documents

- `CODEX_START_HERE.md`
- `ENGINEERING_PRACTICES.md`
- `CLAUDE.md`
- `docs/engineering_skills.md`
- `docs/claude_codex_work_division.md`
- `docs/codex_parallel_workflow.md`
- `docs/marketing_customization.md`
- `docs/legal/README.md`
- `docs/legal/terms.md`
- `docs/legal/privacy.md`
- `docs/requirements/requirements.json`
- `docs/requirements/requirements_generated.md`
- `docs/visual_design_standard.md`
- `ARCHITECTURE.md`
- `RELEASE_NOTES.md`
