# Post-Implementation Naming Alignment Cleanup Proposal

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/21
- Parent context: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Coordinator chat: Casino Simulator - Coordinator
- Timing: after the approved redesign implementation work lands

## Goal

Prepare a concise naming-alignment proposal so coordination artifacts no longer imply there are two implementation tracks, such as a `premium implementation` track versus a `regular implementation` track.

## Background

The `premium` label was used during planning to distinguish the approved high-fidelity redesign from an earlier rejected lobby-only proposal. Once implementation is complete, the project should describe the work as the normal approved casino redesign implementation.

## Non-Goals

- Do not perform this cleanup while active implementation workers are still using the current names.
- Do not change production UI, gameplay, API behavior, ledger behavior, bots, autoplay, contracts, or tests.
- Do not force-push or rewrite branch history.
- Do not rename artifacts in a way that breaks active PR links or worker handbacks.

## Scope

The future cleanup proposal should review:

- GitHub issue titles and bodies for issues #11 through #20.
- Task packet filenames and headings under `codex/tasks/`.
- PR titles and descriptions for redesign implementation PRs.
- Worker thread titles.
- Branch names only if renaming is low-risk and no active PR depends on them.
- Archived/superseded worker visibility.

## Proposed Naming Direction

- Prefer `Implementation` and `Approved Casino Redesign Implementation` for active work.
- Keep `premium` only as descriptive design language where useful, not as a separate workstream name.
- Leave immutable or historically useful references alone when renaming would add confusion.

## Acceptance Criteria

- Produce a table of old name, proposed new name, artifact type, risk, and recommendation.
- Ask the coordinator/user to approve before applying renames.
- Preserve traceability from issues, PRs, task packets, branches, and worker handbacks.
- Archive completed workers after their outcomes are captured in GitHub.

## Handback

Report the recommended rename plan, any artifacts that should remain unchanged for history, and the exact low-risk operations to apply after approval.
