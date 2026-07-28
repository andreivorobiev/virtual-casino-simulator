# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T21:20:37Z.

## Current branch / active Codex work

- Controller PR #486 merged normally at exact protected main `a51eab284fcc596725878d5d35a92b3aab6b69f7`, with parents exactly terminal-green v0.9.5.25 main `3707fb974163ee6dd44cc0664b354e359be68ecf` and accepted controller head `daa6517eb139332cefc5851e68525dc38ca41d59`.
- `codex/release-v0.9.5.26` serializes that accepted Acey-Deucey spread-pricing repair as one unique immutable patch release.
- Deployed v0.9.5.25 remains the live release until v0.9.5.26 passes protected publication and trusted owner/static terminal-green deployment.
- No later PR may merge during this release/deployment hold.

## Live queue snapshot

- #486 preserves the accepted Claude #465 ancestry while repairing Acey-Deucey zero-spread mutation safety, frozen-v1 compatibility evidence, localized controls, Long Suite pricing, and governed Browser coverage.
- Original PR #465 is GitHub-confirmed merged through preserved ancestry; its external branch and worktree remain untouched. Draft #473 must drop its duplicate Acey-Deucey scope before future reconciliation.
- Worker A #467 and Worker B checkpoints #388/#430/#434/#441 remain preserved and merge-held until terminal-green v0.9.5.26. Any governed #467 138-user qualification requires fresh owner authorization.
- #450 remains held and excluded. All other open proposals remain pending and cannot enter this serialized release.

## Requirement / version claims

- No permanent identifier is created, deleted, or reused by this release.
- The accepted #486 controller reuses `AD-001`, `API-AD-001`, and `BR-AD-001`; it allocates no new permanent requirement or `TEST-*` identifier.
- v0.9.5.26 owns packaged application `0.9.5.26`, application `9.53.13`, tests/docs `1.64.13`, and contracts `1.49.8`.
- Acey-Deucey `1.1.1`, core `9.27.2`, and tooling `1.21.8` are preserved from accepted source. The exact immutable v0.9.5.25 release remains the application-only rollback predecessor; MySQL schema stays 2 and database rollback is prohibited.

## File claims / collision notes

- Release-owned changes are limited to packaged version surfaces, compatibility and rollback provenance, PWA/cache identity, release tests, release docs, generated governance, and coordination records.
- #467, #450, Worker B checkpoint source, other proposal source, unrelated gameplay economics, Admin UI, production workflow, provider, DNS, ingress, secrets, signup, OAuth, mail, and invitation files are excluded.
- Any later proposal that overlaps shared docs or manifests must rebase and recalculate versions from terminal-green v0.9.5.26.

## Decisions / handbacks

- Equal or adjacent Acey-Deucey boundary cards have no honest inside price and are pass-only.
- Every playable spread uses the public server-owned constant-edge return table; settlement and compatibility fields must agree with that exact price.
- Frozen `/api/v1` keeps the numeric compatibility scalar while optional paytable and house-edge fields remain additive.
- No hidden-card reveal, receipt, state, or ledger mutation may precede rejection of an unpriceable Play action.
