# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-29T05:17:00Z.

## Current branch / active Codex work

- PR #507 merged normally at exact protected main `157863f1` after its exact-current source, governance, hosted-check, and zero-review audit.
- `codex/release-v0.9.5.29` serializes the accepted #430 Phase 0a settlement foundation as one unique immutable patch release.
- Deployed v0.9.5.28 remains live until v0.9.5.29 passes protected publication and trusted owner/static terminal-green deployment.
- No later PR may merge during this release/deployment hold.

## Live queue snapshot

- #507 owns only the accepted route-free shared settlement adapter and its governed listener-free evidence.
- Worker A may continue #501 controller qualification in parallel but cannot ready, merge, release, or deploy it during this hold.
- #503 remains higher-priority for the next integration slot only if it returns exact-current and fully repaired after v0.9.5.29 deployment.
- #450 and every other unmerged proposal remain excluded.

## Requirement / version claims

- No permanent identifier is created, deleted, or reused by this release.
- The accepted #507 change owns `GAMECORE-003` and central case `API-GAMECORE-002`; no generic TEST ID was allocated.
- v0.9.5.29 owns packaged application `0.9.5.29`, application `9.53.16`, tests/docs `1.64.23`, and contracts `1.49.11`.
- Core `9.28.0`, tooling `1.21.9`, and every unrelated module are preserved from the accepted merge.

## File claims / collision notes

- Release-owned changes are limited to packaged version surfaces, compatibility and rollback provenance, PWA/cache identity, release tests, release docs, generated governance, and coordination records.
- #501, #503, #450, Phase 0b/0c, routes, games, provider implementations, production workflow, DNS, ingress, secrets, signup, OAuth, mail, and invitation files are excluded.
- Any later proposal overlapping shared docs or manifests must reconcile and recalculate versions from terminal-green v0.9.5.29.

## Decisions / handbacks

- The accepted adapter delegates one signed movement to the existing public storage-atomic `debit_once` or `credit_once` boundary and creates no provider or transaction engine.
- Canonical game action, request fingerprint, and round evidence are additive; provider replay remains exact and incompatible recovery fails closed.
- Exact immutable v0.9.5.28 remains the application-only rollback predecessor; MySQL schema stays 2 and database rollback is prohibited.
