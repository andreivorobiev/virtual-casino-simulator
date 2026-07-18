# Engineering practices

These practices apply equally to human contributors and AI-assisted engineering
tools. No tool or vendor receives a separate source of truth.

## Implementation work

Follow `AGENTS.md` and any more-specific nested `AGENTS.md` before changing
source, tests, contracts, requirements, or release artifacts.

## Issue triage

For GitHub issue triage, priority assignment, or label cleanup, read and follow
[`docs/issue_prioritization.md`](docs/issue_prioritization.md) completely before
changing GitHub state. Every open issue must have exactly one of `P1`, `P2`, or
`P3`; `P4` must not be created or used.

Priority-only work does not authorize implementation, issue closure, pull
requests, merges, deployments, provider changes, or bypassing dependencies and
ownership.
