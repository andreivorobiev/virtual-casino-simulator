# AGENTS.md - keno module

Scope this Codex conversation to the `keno` module unless the task explicitly lists impacted components.

## Allowed areas

- `casino/games/keno/`
- `web/games/keno.js`

## Rules

- Read the root `AGENTS.md` first.
- Read `modules/keno.json` before editing.
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
