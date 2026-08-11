# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-11T08:11:41Z.

## Current branch / active Codex work

- Protected main is exact verified-email enrollment merge `12e761dff8853cdcbcd38656b30f7d87ec839a95`, following terminal-green v0.9.5.72 source `d429eb362e83d363b2e9c940ef7b47d81145e4b9`.
- Isolated branch `codex/release-v0.9.5.73` prepares the repository-standard release packet from exact protected main.
- Normal PR #678 closed repository-controlled issue #69; the remaining queue continues after terminal v0.9.5.73 deployment.

## Accepted scope and requirements

- PR #678 adds disabled-by-default verified email/password pending enrollment with exactly-once activation and no pre-verification identity, wallet, balance, or session.
- Initiate, resend, verify, and bearer-owned cancel flows remain recoverable, rate-limited, provider-free by default, and terminally scrubbed with bounded retention.
- Requirements total exactly 947 after permanent `AUTH-018`, `USER-010`, and `TEST-171`; no release requirement identifier is allocated.

## Version and contract allocation

- Release versions advance only to package `0.9.5.73`, application `9.63.1`, contracts `1.60.1`, tests `1.78.1`, and docs `1.75.1`; tooling remains content-owned `1.29.2`.
- Core remains content-owned `9.41.0`, Players remains `9.1.2`, Ledger remains `9.1.2`, and every game revision remains exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.72 source `d429eb362e83d363b2e9c940ef7b47d81145e4b9`, archive SHA-256 `0e63e62fdbbc06ebc7d536a7beb1b55499d70c9d83a849868c4304a1836111ce`, and manifest SHA-256 `f646b26011bf998cc4c576d29aa49fb952f9eb827e029ecbfa15090e0da8e3c1`.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held.
- The canonical deployable inventory is exactly 756 regular files: terminal v0.9.5.72 inventory 754 plus the packaged pending-enrollment module and this compatibility record.
- Local validation is browser-free; fresh hosted all-nine evidence remains mandatory before normal merge and immutable publication.
- No live mail or provider traffic, provider-console change, public-signup activation, public-policy activation, public launch, database migration, runtime topology change, game behavior, settlement semantics, paytable, or wagering-economics change is claimed.
