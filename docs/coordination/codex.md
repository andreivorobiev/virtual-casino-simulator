# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T19:46:20Z.

## Current branch / active Codex work

- Controller PR #484 merged normally at exact protected main `d9a8f860f9f5c67a3932bb755db96b1b39b87da7`, with parents exactly terminal-green v0.9.5.24 main `eb47dc03c58aff39f5392d51a822c3c87281624d` and accepted controller head `5d88e391c9d31ee31d5fa043ac67e026f3d2c4d2`.
- `codex/release-v0.9.5.25` serializes that accepted Browser shard-state controller as one unique immutable patch release.
- Deployed v0.9.5.24 remains the live release until v0.9.5.25 passes protected publication and trusted owner/static terminal-green deployment.
- No later PR may merge during this release/deployment hold.

## Live queue snapshot

- #484 preserves the accepted Claude #482 ancestry while repairing complete shard ownership, startup-validated affinity, case-neutral auth bootstrap, exact aggregate accounting, current packaged-version PWA checks, and unconditional final invariants/listener cleanup.
- Original PR #482 is durably closed as superseded; its external branch and worktree remain untouched. Issue #468 stays open for separately governed remaining CI timing and documentation work.
- Worker A #467 and Worker B checkpoints #388/#430 remain preserved and merge-held until terminal-green v0.9.5.25. Any further governed #467 qualification requires fresh owner authorization.
- #450 remains held and excluded. All other open proposals remain pending and cannot enter this serialized release.

## Requirement / version claims

- No permanent identifier is created, deleted, or reused by this release.
- The accepted #484 controller reuses the Browser and CI/CD requirements already mapped by issue #468; it allocates no new `TEST-*` identifier.
- v0.9.5.25 owns packaged application `0.9.5.25`, application `9.53.12`, tests/docs `1.64.11`, and contracts `1.49.6`.
- Core `9.27.2` and tooling `1.21.8` are preserved from accepted source. The exact immutable v0.9.5.24 release remains the application-only rollback predecessor; MySQL schema stays 2 and database rollback is prohibited.

## File claims / collision notes

- Release-owned changes are limited to packaged version surfaces, compatibility and rollback provenance, PWA/cache identity, release tests, release docs, generated governance, and coordination records.
- #467, #450, Worker B checkpoint source, other proposal source, gameplay economics, Admin/UI, production workflow, provider, DNS, ingress, secrets, signup, OAuth, mail, and invitation files are excluded.
- Any later proposal that overlaps shared docs or manifests must rebase and recalculate versions from terminal-green v0.9.5.25.

## Decisions / handbacks

- Affinity groups must be startup-valid, co-owned by one shard, and preserve exact single-job order.
- Every Browser case stays registered unconditionally for exact sequence accounting, while its stateful body runs only for the owning shard.
- The ordinary aggregate must fail closed unless four unique shard reports form one non-duplicating 105-case union.
- Unsharded execution, formal 50,000-cycle work, Baccarat sustained work, final browser-error invariants, and listener cleanup remain isolated.
