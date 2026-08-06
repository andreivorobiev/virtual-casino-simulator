# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-08-05.

## Pull requests I authored (drafts; I never merge)

| PR | Branch | What it is | State |
|---|---|---|---|
| (opening) | `claude/607-viewport-containment-action-stability` | Issue #607: viewport containment for every game surface with layout telemetry, plus no-refresh/no-scroll-reset action stability (UX-026/UX-027, BR-LAYOUT-CONTAIN-001/BR-ACTION-STABILITY-001) | in validation; PR link will be recorded on issue #607 |

Earlier reviewer-readiness stack (#558/#559/#561) and #518 have all been reconciled and merged by Codex controllers; no stale claims remain from that program.

## Active work — issue #607 (owner-directed, 2026-08-05)

Single PR covering both owner asks:

1. **Containment (UX-026).** Measured continuous fit for the fixed Roulette board (replaces the discrete scale ladder; explicit translate centering because grid safe-centering start-pins oversized items), minmax(0,…)/min-width:0 shrink repairs in marble_race, slots, baccarat, boule, faro, daily_draw_lab, a shared `auditLayoutContainment` helper, and `layout_overflow` telemetry through the frozen `/api/v1/log/client` route (Admin Telemetry visible). Evidence: 17-viewport × 46-route headless sweep — 26 flagged cells before, 0 after.
2. **Action stability (UX-027).** One shell-level route-outlet innerHTML interceptor preserves outlet scroll, internal rail scroll, and stable-identity focus across same-route rerenders for all 46 games and the lobby; collapse-clamp rescue only (never fights scroll anchoring); stranded focus parks on the game region; route changes still reset intentionally. No game render loops modified.

## File claims / high collision risk

- Owned: `web/core/ui.js`, `web/app.js`, `web/games/{roulette,marble_race,slots,baccarat,boule,faro,daily_draw_lab}.js`, `tests/run_tests.py` (two appended Browser cases only), `tests/frontend_safety.mjs`, `tests/browser_case_durations.json`, `tests/unit/request_latency_benchmark_tests.py` (count + allocation + version literals), `docs/requirements/requirements.json` (+UX-026, UX-027, TEST-154, TEST-155 → 904 rows), `docs/visual_design_standard.md` (new hard-rules section), regenerated `docs/requirements/requirements_generated.md`, module descriptors + aggregate manifest for the versions below, and the two coordination records.
- Version allocations above v0.9.5.55 main: application `9.57.0`, roulette `9.6.0`, slots `9.4.3`, baccarat `9.1.13`, marble_race/boule/faro `1.1.3`, daily_draw_lab `1.1.3`, tests `1.68.0`, docs `1.66.0`. Packaged application stays `0.9.5.55`; core, admin, contracts, tooling untouched.
- No contract, API, casino runtime Python, provider, or release-path changes.

## Questions / requests for Codex

- Review and integrate the #607 PR when it is handed back; oldest-first is fine — it stacks on nothing.

## Blockers I am waiting on (owner or Codex)

- None.
