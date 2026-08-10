# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T19:21:35Z.

## Current branch / active Codex work

- Protected main, tag, release, and terminal-green production are exact v0.9.5.66 source `e8cd5e6f316d35028224c5946e90602f41cf984e`.
- Isolated branch `codex/enrollment-auth-queue-v67` owns only issue #333's remaining repository-controlled provider operational switches from exact v0.9.5.66 main.
- Google and Facebook remain default-off; external provider configuration, public signup, and public launch stay separately held by #336 and #209.

## Accepted scope and requirements

- The content lane adds durable owner-only Google/Facebook login kill switches, independent from enrollment signup flags, with optimistic revisions and hash-linked privacy-safe audit.
- Provider start, callback, and availability paths read the switch before credential-bearing adapter construction; enablement additionally requires existing secret-safe runtime and network-release readiness.
- Permanent requirements `OAUTH-012` and `TEST-167` map focused OAuth, account-spine, aggregate API, and Admin EN/RU Browser evidence.

## Version and contract allocation

- The content tuple remains package `0.9.5.66` while advancing application `9.60.0`, Core `9.39.3`, Admin `1.18.0`, contracts `1.58.0`, tests `1.73.0`, and docs `1.71.0`; tooling remains `1.27.1`.
- No provider credential, network call, public-policy activation, game, ledger, settlement, database schema, migration, paytable, or wagering-economics change is in scope.
- Any later release must use exact terminal-green v0.9.5.66 as the application-only schema-two predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held.
- Local validation covers focused OAuth/account tests, aggregate API discovery, contracts, requirements, versions, boundaries, comment density, generated docs, and diff hygiene; fresh hosted all-nine evidence remains mandatory before merge.
- #333 may close only after the accepted exact head merges. #69/#335/#336/#209 remain open unless their separate acceptance or external evidence is proven. No release, deployment, provider enablement, or public launch is claimed by this content work.
