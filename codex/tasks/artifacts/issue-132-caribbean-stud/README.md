# Issue #132 Isolated Draft Evidence

Branch: `codex/issue-132`

Game: Caribbean Stud

## Delivered Draft Slice

- Distinct/countable game proof for Caribbean Stud.
- Game-local backend package with pure engine, service, and route registration adapter.
- Session-bound state and exactly-once ledger movements for ante, call, and settlement.
- Fold decision that forfeits ante without revealing dealer hole cards.
- Game-local frontend module, EN/RU resources, and focused static UI checks.
- Additive OpenAPI v1 contract proposal.
- Module descriptor proposal outside auto-discovered `modules/`.
- Focused tests and driver proposal under game-specific paths.

## Shared Integration Not Claimed

This branch intentionally does not edit shared #77-owned files: catalog, router, shell navigation, aggregate manifests, permanent requirements, generated requirements, compatibility matrices, central test discovery, long-suite registry, visual matrix, release/version files, deployment, auth, OCI, or other games.

## Evidence Classification

No screenshot is claimed as `after_pass`. Browser-visible real-backend evidence requires #77 shared registration and visual matrix ownership.
