# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-31T10:13:25Z.

## Current branch / active Codex work

- PR #550 merged normally as protected main `89ffbe1c` after exact-current ancestry, all nine required workflow families, six Browser shards plus aggregate, source-bound Browser/Long/release-candidate artifacts, and zero review state.
- Terminal-green published/released/live production remains exact v0.9.5.44 `40919ddb15fbae3f4196de992b4e92ef5bee63a0`; MySQL remains clean at schema 2 and the held schema-3 migration was not invoked.
- `codex/release-v0.9.5.45` serializes the unique immutable release for the accepted deterministic six-runner Browser shard rebalance. No other merge may advance until v0.9.5.45 is terminal green through the trusted deployment route.

## Live queue snapshot

- PR #550 is the sole content integration for the Browser shard rebalance. Durable #525 comment `5141718412` records that ancestry shell `6fc0814d` only made contributor head `768cc7fb` reachable, so GitHub's original-PR merged state is not a second content merge.
- Durable #502 comment `5141718883` records that stale closing text auto-closed the issue, that it was reopened, and that it remains OPEN at `stack-rank:024` through unique v0.9.5.45 terminal deployment.
- #518, #506, #483, #460, and #454 remain held for later serialization. #450 remains held and excluded.

## Requirement / version claims

- Merged main owns deterministic duration-balanced Browser qualification across six nonempty runners, strict fixed-diagnostic profile validation, Browser-only timing rows, and exact aggregate ownership/coverage checks without a new requirement or test identifier.
- Merged tests revision is `1.65.0` and tooling is `1.24.0`; application remains `9.54.1`, core `9.35.0`, admin `1.14.0`, Roulette `9.5.0`, and Slots `9.4.0`.
- This release packet alone advances package `0.9.5.45`, application `9.54.2`, contracts `1.53.4`, tests `1.65.1`, and docs `1.64.55`; tooling and every unrelated module remain unchanged.

## File claims / collision notes

- The release branch contains only the ordinary twenty-six release contract, documentation, localization, version, predecessor-test, PWA-version, generated, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, game JavaScript, game engine, economy, ledger, API/OpenAPI, provider, migration, workflow, grant, secret, or production configuration.
- Every open shared or stacked head must rebase and recalculate after terminal deployment.

## Decisions / handbacks

- v0.9.5.45 packages the accepted deterministic six-runner Browser shard rebalance while the release-only application revision advances mechanically to `9.54.2`.
- The release changes qualification tooling only: it makes no gameplay, product, public, provider, API, database, migration, ledger, shell-label, or application-visible behavior claim.
- Its compatibility record binds exact immutable v0.9.5.44 as the application-only schema-2 predecessor; database rollback is prohibited and schema migration remains held.
- Issue #502 remains OPEN through terminal deployment; every other merge remains serialized.
- Provider/public enablement, MySQL composite execution, schema-3 activation, issue closure, release deployment, and held #450 remain separately governed.
