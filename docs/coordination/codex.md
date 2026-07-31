# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-31T08:11:49Z.

## Current branch / active Codex work

- PR #548 merged normally as protected main `ebe13e6b` after exact-current ancestry, all nine required workflow families, source-bound Browser/Long/release-candidate artifacts, and zero review state.
- Terminal-green published/released/live production remains exact v0.9.5.43 `84ccc1e468e2aef72ea5554442b0cde3761912bf`; MySQL remains clean at schema 2 and the held schema-3 migration was not invoked.
- `codex/release-v0.9.5.44` serializes the unique immutable release for the accepted catalog-derived shell-label integration. No other merge may advance until v0.9.5.44 is terminal green through the trusted deployment route.

## Live queue snapshot

- PR #548 is the sole content integration for the shell-label change. Durable #539 comment `5140717070` records that ancestry shell `088e3c1c` only made contributor head `7da00ef3` reachable, so GitHub's original-PR merged state is not a second content merge.
- Durable #525 comment `5140717509` keeps that dependent PR open and held through unique v0.9.5.44 terminal deployment, followed by fresh current-main reconciliation and exact-head qualification.
- #518, #506, #483, #460, and #454 remain held for later serialization. #450 remains held and excluded.

## Requirement / version claims

- Merged main owns complete static shell-label resources for all 46 catalog games in English and Russian, with the 40 added rows exactly derived from current descriptors and no new requirement or test identifier.
- Merged application revision is `9.54.0`; core remains `9.35.0`, admin `1.14.0`, tooling `1.23.0`, Roulette `9.5.0`, and Slots `9.4.0`.
- This release packet alone advances package `0.9.5.44`, application `9.54.1`, contracts `1.53.3`, and tests/docs `1.64.54`; every unrelated module remains unchanged.

## File claims / collision notes

- The release branch contains only the ordinary twenty-six release contract, documentation, localization, version, predecessor-test, PWA-version, generated, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, game JavaScript, game engine, economy, ledger, API/OpenAPI, provider, migration, workflow, grant, secret, or production configuration.
- Every open shared or stacked head must rebase and recalculate after terminal deployment.

## Decisions / handbacks

- v0.9.5.44 packages the accepted application `9.54.0` catalog-derived shell labels while the release-only application revision advances mechanically to `9.54.1`.
- Cold-open and deep-link fallback labels now match the hydrated catalog for all 46 games in both locales without changing route logic, APIs, games, economy, ledger, provider, public policy, readiness, or production configuration.
- Its compatibility record binds exact immutable v0.9.5.43 as the application-only schema-2 predecessor; database rollback is prohibited and schema migration remains held.
- #525 remains open and held through terminal deployment; every other merge remains serialized.
- Provider/public enablement, MySQL composite execution, schema-3 activation, issue closure, release deployment, and held #450 remain separately governed.
