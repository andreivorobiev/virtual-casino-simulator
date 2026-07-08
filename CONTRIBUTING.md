# Contributing

All work should happen through GitHub issues and pull requests.

## Required PR contents

- Summary of the change.
- Impacted module list.
- Requirement IDs.
- API contract impact statement.
- Version bumps.
- Tests run.
- Screenshots or browser traces for UI changes.
- Release notes when user-facing behavior changes.

## Branch naming

Use one of these patterns:

```text
agent/<module>-<short-description>
feature/<module>/<short-description>
bugfix/<module>/<short-description>
docs/<short-description>
release/app-<version>
release/<module>-<version>
```

## Module isolation

A PR should normally touch one module plus tests/docs/contracts for that module.
Cross-module PRs require an explicit impact analysis.

## Parallel Codex work

Use `docs/codex_parallel_workflow.md` when multiple chats work at the same time.
Start each worker chat from a GitHub issue or `codex/tasks/TASK_PACKET_TEMPLATE.md`.

## API changes

Any API change must update the OpenAPI contract and compatibility matrix in the same PR.
