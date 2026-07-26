# AGENTS.md - core module

Scope this Codex conversation to the `core` module unless the task explicitly lists impacted components.

## Allowed areas

The owned path set is declared by `modules/core.json`; that descriptor is authoritative if this
list ever drifts from it.

- `casino/core/`
- `casino/app.py`
- `casino/wsgi.py`
- `casino/router.py`
- `casino/errors.py`
- `casino/config.py`
- `casino/module_versions.py`
- `casino/games/registry.py`

## Rules

- Read the root `AGENTS.md` first.
- Read `modules/core.json` before editing.
- Reference impacted requirement IDs in every change.
- Update module version if source behavior or public contract changes.
- Update tests for this module when behavior changes.
- Do not modify unrelated game modules.
- Preserve dense line-level comments for Python and JavaScript.

## Validation

Run module-appropriate API/browser/contract tests plus:

```bash
python scripts/validate_module_boundaries.py
python scripts/validate_contracts.py
python scripts/validate_requirements.py
python scripts/check_comment_density.py
```
