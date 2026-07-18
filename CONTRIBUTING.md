# Contributing

All work should happen through GitHub issues and pull requests.

Project-wide workflow rules are summarized in
[`ENGINEERING_PRACTICES.md`](ENGINEERING_PRACTICES.md) and apply equally to human
and AI-assisted contributions.

## Issue prioritization

Follow [`docs/issue_prioritization.md`](docs/issue_prioritization.md) when creating,
triaging, or relabeling issues. Every open issue must have exactly one of `P1`,
`P2`, or `P3`. The repository does not use `P4`.

## License and terms boundaries

Contributions to repository source code are expected to be compatible with the Apache License, Version 2.0 in `LICENSE`.

Do not add runtime behavior, documentation, examples, or issue text that presents Virtual Casino Simulator as a gambling site, real-money play, payment product, cash-out product, sweepstakes, sportsbook, lottery, or prize-redemption service. Play tokens must remain fake simulator values with no cash value and no redemption, sale, transfer, exchange, withdrawal, or conversion path.

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
