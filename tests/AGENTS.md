# AGENTS.md - tests module

Scope this Codex conversation to the `tests` module unless the task explicitly lists impacted components.

## Allowed areas

- `tests/`
- `verify_rules.py`

## Rules

- Read the root `AGENTS.md` first.
- Read `modules/tests.json` before editing.
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
