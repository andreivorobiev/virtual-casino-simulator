# AGENTS.md - docs module

Scope this Codex conversation to the `docs` module unless the task explicitly lists impacted components.

## Allowed areas

The owned path set is declared by `modules/docs.json`; that descriptor is authoritative if this
list ever drifts from it.

- `docs/`
- `AGENTS.md`
- `CLAUDE.md`
- `CODEX_START_HERE.md` (the catalog between the `GENERATED MARKDOWN INDEX` markers is produced by
  `scripts/generate_docs.py` — regenerate it, never hand-edit that block)
- `ENGINEERING_PRACTICES.md`
- `ARCHITECTURE.md`
- `RELEASE_NOTES.md`
- `LICENSE`
- `NOTICE`
- `CONTRIBUTING.md`

## Rules

- Read the root `AGENTS.md` first.
- Read `modules/docs.json` before editing.
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
