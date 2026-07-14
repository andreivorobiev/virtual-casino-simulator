# Issue #94 isolated handoff evidence

Branch: `codex/game-multi-hand-video-poker`

Base at implementation start: `ff8e0dd566691bad3991348abc8eaf8dbdc0eaf6` (`main`)

## Delivered isolated slice

- Deterministic Jacks-or-Better engine using #96 shared card and poker primitives.
- Required 3, 5, and 10-hand modes with one common held-card source hand.
- Session-compatible player-scoped API and reload-safe state.
- Exactly-once local-simulator token design with one aggregate wager debit, one aggregate payout credit, persisted recovery markers, ledger replay detection, and no direct balance mutation.
- Timer-free, reduced-motion-aware frontend module using the shared accessible card renderer.
- Complete EN/RU game domain resources with no player-visible literals owned by the frontend module.
- Explicit additive OpenAPI v1 contract and module-owned #110 catalog descriptor.
- Focused engine, API, frontend-static, and catalog long-driver tests under a game-specific path.

## Shared integration intentionally blocked

The following actions belong to active PR #110 and integration lane #77 and are not performed here:

- Add `multi_hand_video_poker: 1.0.0` to `modules/module-manifest.json` after #110 establishes the canonical catalog/version interface.
- Merge or rebase onto #110 so catalog loading, backend registration, frontend lazy routing, authenticated-player replacement, validator discovery, and long-suite discovery become active.
- Add central requirement IDs and generated requirement documents.
- Add the central browser driver/run-list wiring if #110's descriptor discovery requires a conventional driver relocation.
- Add the `multi_hand_video_poker` surface to `tests/visual/visual_matrix.json`.
- Capture real-backend `after_pass` browser evidence after the shared route is registered.

## Proposed visual matrix row for #77

- Surface: `multi_hand_video_poker`
- Route: `/games/multi_hand_video_poker`
- Selector: `[data-testid='multi-hand-video-poker']`
- States: `ready`, `choose_holds`, `settled_3_hands`, `settled_5_hands`, `settled_10_hands`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`

## Evidence classification

No screenshot in this isolated branch is claimed as `after_pass`. The frontend cannot be reached through the real shared shell until #110/#77 registers the module descriptor and visual row. Focused validation evidence is recorded in `validation.md` after execution.
