# Codex task prompt: ledger

Read root `AGENTS.md`, then read `modules/ledger.json` and any nested `AGENTS.md` for this module.

## Scope

Work only on the `ledger` module unless the GitHub issue explicitly lists impacted modules.

## Before editing

- Identify requirement IDs.
- Identify API contracts impacted.
- Identify module version bump.
- Identify tests to run.

## Required validation

```bash
python scripts/validate_module_boundaries.py
python scripts/validate_contracts.py
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/check_comment_density.py
```

Add API or browser tests when behavior changes.
