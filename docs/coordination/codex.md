# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-07T21:35:00Z.

## Current branch / active Codex work

- Protected main is exact settlement-interface merge `ea17b04238d1377afdcda7c366a0fd86b373e260`, with ordered parents terminal v0.9.5.58 source `ee8dfd4c7df3fb723a070f947e644cbce46eebdd` then accepted #635 head `1e2004ba8ddc3233da20d2a8b93d10126a7cd5f2`.
- Local-only `codex/release-v0.9.5.59` prepares the repository-standard release packet from exact protected main.
- Normal PR #635 is the sole content integration for issues #430 and #621 through #634; no issue content is imported a second time.

## Accepted scope and requirements

- PR #635 converges all 46 registered games on `GameSettlementGateway` and storage-atomic `SettlementAdapter` actions while preserving API envelopes, game rules, acceptance timing, payouts, and refunds.
- Requirements total exactly 911 unique rows after accepted additions `LEDGER-032`, `GAMECORE-004`, and `TEST-157`; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 738 regular files; repository documentation, tests, and the pull-request validator remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.59`, application `9.58.2`, contracts `1.55.3`, tests `1.69.4`, and docs `1.67.4`; tooling remains `1.25.2`.
- Content-owned Core `9.37.1`, Ledger `9.1.1`, all 46 game revisions, and every other manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.58 source `ee8dfd4c7df3fb723a070f947e644cbce46eebdd`, archive SHA-256 `381dcbb9440d0eb343e75193f0e0d6afa2d2be19fea5c422c54e1ae6a0d5619f`, and manifest SHA-256 `7ea9d6d4815efcb8969267dd78392b37e03692155c3c8975ccb5014b58f852a2` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.59.json`, plus only `tests/run_tests.py` for the #637 Browser rerender synchronization repair; the canonical package inventory remains exactly 738 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issues #430 and #621 through #634 were resolved by normal content PR #635. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
