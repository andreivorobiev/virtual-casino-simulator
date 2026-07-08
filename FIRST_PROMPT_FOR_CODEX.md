# First prompt for Codex

You are working in the `virtual-casino-simulator` repository.

## Task: Repository Bootstrap Validation v9.1.1

Read these files first:

1. `AGENTS.md`
2. `CODEX_START_HERE.md`
3. `modules/module-manifest.json`
4. `contracts/compatibility/app-9.1.1.json`
5. `docs/github_codex_migration_plan.md`

Then run:

```bash
python scripts/bootstrap_repo.py
python verify_rules.py
python tests/run_tests.py --api
python scripts/validate_contracts.py
python scripts/validate_module_boundaries.py
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/check_comment_density.py
```

Do not change gameplay behavior for this first task. Only fix repository-bootstrap, governance, contract, test, documentation, or commenting-policy issues.

When complete, produce a pull request summary that states:

- which requirement IDs were touched,
- which modules were touched,
- which module versions changed,
- whether API contracts changed,
- which validation commands passed,
- and whether gameplay behavior changed.
