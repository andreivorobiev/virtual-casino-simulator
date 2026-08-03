# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-03T07:02:32Z.

## Current branch / active Codex work

- Protected main is exact production-polish merge `7b7cb018dea9bfe4f244ea6f70f19c0247b32d88`, with ordered parents terminal v50 main `1fedfc905478e3701f19c23fe6c30648d8fed892` then accepted #571 head `e88578ff7b9bbdd5c158e04c272e3eb8ec3b97cb`.
- Terminal production remains exact v0.9.5.50 at clean MySQL schema 2 with schema-3 application held; no v0.9.5.51 publication, activation, or deployment is claimed.
- Local-only `codex/release-v0.9.5.51` prepares the repository-standard release packet from exact current main.

## Accepted scope and requirements

- Sole content PR #571 fixes Roulette board containment, separates safe static GET delivery from the API action rate budget, and reports unique active online sessions without exposing private player identities.
- The registry remains exactly 888 unique requirements. This release allocates no new requirement or Browser identifier.

## Version and contract allocation

- Release versions advance only to package `0.9.5.51`, application `9.56.7`, contracts `1.54.3`, tests `1.67.3`, and docs `1.65.3`; tooling remains `1.25.0`.
- Accepted source versions remain `core 9.36.1` and `roulette 9.5.1`; every other module remains exact current main.
- The new compatibility record binds exact v0.9.5.50 source `1fedfc905478e3701f19c23fe6c30648d8fed892`, archive SHA-256 `c11a5db2aaff75619584e920b401c607f1ca2f3c7e295b98f3eeb3a4fcb5f7f8`, and manifest SHA-256 `6a8ef2d0a155577def752f74b412d807740123d5801ecacfa3b60e8a00facf7a`.

## Rollback, queue, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held with catalog SHA-256 `0697ec36c1787bb5a0773b4f3c3e6db732fd4e231a69cff9b0d0625618a41bc3` and chain SHA-256 `083682e266576aa571e20f2baf6746b0ee28c8f81906c17dc96f05bed6a51a7b`; no migration changes.
- Issue #570 remains OPEN until terminal v0.9.5.51 production verification. Broader issues remain open unless their complete acceptance criteria are independently proven.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.51.json`; it changes no casino runtime, game source, workflow, provider, migration, API, ledger, or database source.
- Local validation is browser-free only; publication, activation, deployment, and issue closure require their normal exact-head gates.
