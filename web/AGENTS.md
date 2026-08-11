# AGENTS.md - web browser shell

This is the closest scoped instruction file for every file under `web/`. `web/` is not itself a
module: its files are split across several module descriptors in `modules/`. Identify the descriptor
that owns the files you are touching, then scope this Codex conversation to that module unless the
task explicitly lists impacted components.

## Allowed areas

- `web/` — application shell, `web/core/` shared helpers, per-game frontends in `web/games/`,
  locale resources in `web/i18n/`, `web/styles.css`, `web/sw.js`, and `web/assets/`.
- `casino/admin.py`, which `modules/admin.json` owns together with the admin browser surface.

## Path ownership

Ownership is declared by the `paths` array of each descriptor in `modules/`; those descriptors are
authoritative, not this summary. Common cases:

- `web/index.html`, `web/app.js`, `web/styles.css`, `web/sw.js`, `web/manifest.webmanifest`,
  `web/i18n/`, `web/assets/`, and most of `web/core/` — `modules/application.json`
- `web/admin.html`, `web/admin.js` (with `casino/admin.py`) — `modules/admin.json`
- `web/core/voice.js` — `modules/audio.json`
- `web/core/autoplay.js` — `modules/autoplay.json`
- `web/core/bots.js` — `modules/bots.json`
- `web/games/<game_id>.js` and its `web/i18n/<locale>/games/<game_id>.json` domains — the matching
  `modules/<game_id>.json`

A few files under `web/` are not currently claimed by any descriptor. Confirm ownership with the
integration owner before changing one rather than assuming this file grants scope.

## Rules

- Read the root `AGENTS.md` first.
- Read the owning `modules/<module>.json` descriptor before editing.
- Reference impacted requirement IDs in every change.
- Update module version if source behavior or public contract changes.
- Update tests for this module when behavior changes.
- Do not modify unrelated game modules.
- Preserve exact first-party file headers and comments that explain purpose or non-obvious intent.

## Validation

Run module-appropriate API/browser/contract tests plus:

```bash
python scripts/validate_module_boundaries.py
python scripts/validate_contracts.py
python scripts/validate_requirements.py
python scripts/check_file_headers.py --check
```
