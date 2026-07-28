# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T07:47:00Z.

## Current branch / active Codex work

- PR #470 merged normally at exact protected main `ae1ba6f945ed5cb43cd345e5b85732d961091b32`.
- `codex/release-v0.9.5.23` serializes the accepted safe CI qualification acceleration behind one unique immutable release and terminal-green trusted deployment.
- No other PR may merge during this release/deployment boundary; #450 remains held and excluded.
- Worker A/#467 and Worker B/#433 remain preserved but must reconcile shared tests/docs allocations after v0.9.5.23.

## Live queue snapshot

- Protected main is `ae1ba6f945ed5cb43cd345e5b85732d961091b32`; deployed immutable v0.9.5.22 remains exact `3ab40e11dd50df24423bb9b3a649e0ece6180cda` until v0.9.5.23 is terminal green.
- #468 remains open after its bounded same-PR cancellation and Long Suite 100 sharding slice; browser sharding, affected-game selection, and remaining overhead work stay separately governed.
- #433 remains open after its runtime-inert schema/catalog foundation; runtime enforcement and Admin UI remain separately governed.
- #450 remains excluded and cannot replace or disable the trusted owner/static deployment lane.

## Requirement / version claims

- No permanent requirement or TEST identifier was added, deleted, or reused by #470.
- #470 updates `TOOL-002` and `TEST-036`, owns tooling `1.21.7`, and owns tests/docs `1.64.5`.
- The v0.9.5.23 release advances application to `9.53.10`, contracts to `1.49.4`, and tests/docs to `1.64.6`.
- Worker B's frozen #433 follow-up must re-splice its provisional tests/docs `1.64.6` claim above the release after serialization clears.

## Decisions / handbacks

- Ordinary cancellation is limited to superseded runs for the same workflow and pull request; main pushes and manual dispatches use unique run IDs.
- Release, deployment, formal 50,000-cycle, Baccarat sustained, and manual soak work remain outside PR cancellation.
- Mandatory Long Suite 100 owns four exhaustive 25-scenario shards, shard-zero audio, unique terminal artifacts, tracked listener closure, and the exact fail-closed `long_suite_100` aggregate.
- Browser Tests self-triggers for its own workflow changes; #470 exact-head Browser evidence passed 105/105 without any formal or sustained dispatch.
