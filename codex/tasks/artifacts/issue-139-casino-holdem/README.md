# Issue #139 Casino Hold'em Isolated Slice

This artifact packet records the proposal-only Casino Hold'em implementation slice for GitHub issue #139.

Scope included:

- Game-local backend package under `casino/games/casino_holdem/`.
- Standalone frontend module under `web/games/casino_holdem.js`.
- Paired EN/RU game resource files under `web/i18n/*/games/casino_holdem.json`.
- Additive game-owned OpenAPI file under `contracts/openapi/casino_holdem.v1.yaml`.
- Focused tests under `tests/games/casino_holdem/` and a proposal-only future driver under `tests/game_drivers/casino_holdem.py`.
- Descriptor proposal and distinct-module proof in this artifact folder.

Scope intentionally excluded:

- Shared catalog, router, application shell, aggregate manifest, permanent requirements, compatibility matrices, visual matrix, central test discovery, long-suite registry, and version files outside this proposal.
- Count acceptance or production integration, which remains owned by #77.
