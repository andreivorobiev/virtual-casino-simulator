# Scratch Cards evidence status

**Historical.** Records the isolated pre-integration verification for issue #87. Shared integration has since landed: `modules/scratch_cards.json` is an installed descriptor, `tests/visual/visual_matrix.json` carries a `scratch_cards` surface, and SCRATCH-001 through SCRATCH-005 are PASS in `docs/requirements/requirements.json`.

Evidence class: isolated pre-integration verification; not acceptance evidence.

Issue #87 owned focused engine, service, API, frontend, and isolated-browser checks. Those checks could prove masking, action behavior, paired locale copy, semantic controls, and responsive overflow in the game-owned surface. They could not prove registered lobby navigation, authenticated shared-shell wallet behavior, route restoration, or final real-backend settlement while #77 still owned the aggregate manifest and visual matrix.

No known-failing, manually assembled, mock-backend, or older-branch screenshot is presented as `after_pass` acceptance evidence.

## Isolated validation record

The readiness-refresh rerun on `origin/main` at `f8c836163eab3dc92d83e7bf875ee963c11bddcf` completed with 19 Python engine/service/API tests, 4 Node frontend tests, one full-remount pending-purchase recovery check, and the isolated browser harness across 2 locales and 4 viewports. The browser harness bound only to `127.0.0.1:59561` under PID `36916`, then reported `closed=true`; ports `8765` and `8877` and repository `data/` were not touched.

The first draft head stored the proposal under `modules/`, which made runtime descriptor discovery install an incomplete game before #77 owned canonical registration. CI, Browser Tests, and Long Suite then stopped at casino reset with `KeyError: 'scratch_cards'`. The correction moved the proposal out of `modules/`, outside runtime discovery. The descriptor is now installed at `modules/scratch_cards.json`, with its revision tracked in `modules/module-manifest.json`.

As recorded at the issue-87 rerun on `f8c836163eab3dc92d83e7bf875ee963c11bddcf`, repository rule, contract, boundary, requirement, version, catalog, and comment-density validators passed with the proposal uninstalled on rebased `origin/main`: 32 rule checks, 8 shared contracts and 12 installed catalog games, 445 requirements, packaged release `9.1.1` with 25 module revisions, and 12 current catalog games against target 20. Those totals are that snapshot only; the current packaged release and module revisions are owned by `modules/module-manifest.json`, the catalog is discovered from `casino.config.GAMES`, and requirement totals are owned by `docs/requirements/requirements.json`. Fresh exact-head shared API/browser/long-suite checks remain required after each push; even when green, they prove only that the installed catalog is unaffected, not Scratch Cards real-backend acceptance. This record does not claim shared-shell, registered-route, real-backend, or visual-matrix acceptance.

Evidence required from #77 after shared integration (integration has since landed; the delivered surface set is recorded in `tests/visual/visual_matrix.json`):

| Surface | State | Locales | Viewports | Required proof |
| --- | --- | --- | --- | --- |
| `scratch_cards` | `ready` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Wager, primary action, full stage, semantic covered cells, no overflow |
| `scratch_cards` | `revealing` | en-US, ru-RU | desktop primary, mobile | Partial prizes persist across reload without covered-value leakage |
| `scratch_cards` | `settled_win` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Backend match, one payout credit, wallet refresh, localized result |
| `scratch_cards` | `settled_no_win` | en-US, ru-RU | desktop primary, mobile | Zero payout, no zero-value credit, localized terminal state |
| `scratch_cards` | `reduced_motion` | en-US, ru-RU | desktop primary, mobile | No active transition/animation and no game-owned timer |
| `scratch_cards` | `route_restored` | en-US, ru-RU | desktop primary, mobile | Direct route, reload, Back, and Forward preserve the authenticated card |

Each future `after_pass` artifact must record branch, commit, surface, state, locale, viewport, and path under `docs/visual_design_standard.md`.
