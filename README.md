# Virtual Casino Simulator

Packaged application release: `0.9.5.33`

Historical source baseline: `9.1.0`

Local play-token browser casino simulator with a descriptor-driven catalog of isolated games (Roulette, Slots, Blackjack, Baccarat, Keno, American Bingo and many more; the canonical catalog is discovered from the `modules/*.json` descriptors), isolated game state, ledger-backed wallet accounting, authenticated private-beta users, Admin telemetry, and optional JSON or MySQL persistence.

## Current repository status

This repository has advanced beyond the original v9.1.1 bootstrap snapshot. Packaged release v0.9.5.33 carries the accepted Slots economics-only slice for issue #471: one authoritative engine/API/browser/localization model governs the line-bet and line-count domain, scatter awards, four-spin bonus, earned free-spin basis, and a bounded paid-only progressive qualified at 20 lines and line bet 1.00. It retains exact visible-rank Hi-Lo and independent Andar/Bahar pricing, fail-closed affected-game Browser qualification, the route-free settlement foundation, governed exact 138-browser full-catalog qualification, all-game desktop control-reachability, governed Acey-Deucey spread pricing, deterministic Browser shard state, runtime-inert rule coercion, private-invite security, MySQL schema 2, provider-disablement, public-exposure gates, and exact v0.9.5.32 application-only rollback. It makes no durable action-reservation, cross-process, exactly-once, or composite state-and-ledger claim; that #430 Phase 0c remainder stays open on issue #471. Independently versioned modules continue to record compatible source changes. Current module revisions and requirement status are recorded in the canonical manifests and generated requirements document.

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
