# Dragon Tiger isolated real-backend evidence

Evidence class: issue-scoped development evidence from the production handler with an in-memory module-revision shim. It is not visual-matrix `after_pass` evidence and does not claim shared #77 integration acceptance.

- Issue: [#83](https://github.com/andreivorobiev/virtual-casino-simulator/issues/83)
- Branch: `codex/issue-83-dragon-tiger`
- Tested source commit: `89d21089c8d1978dee165853b41d450b5f20fd97`
- Captured: 2026-07-14
- Backend: production `casino.app.Handler`, authenticated local session, disposable operating-system temporary storage
- Listener: PID `54488`, `127.0.0.1:61381`; PID stopped and port closure verified after capture
- Protected listener: port `8765` was never opened, contacted, stopped, or modified by this run

## Captures

| Artifact | Surface state | Locale | Viewport | Verified properties |
| --- | --- | --- | --- | --- |
| `isolated/desktop-primary-en-ready.png` | `ready` | en-US | `desktop_primary` 1920 x 1080 | Authenticated route, localized hidden-card ARIA, wager controls, full stage, rules, zero horizontal overflow |
| `isolated/desktop-primary-en-settled.png` | `settled` | en-US | `desktop_primary` 1920 x 1080 | Real ledger-backed cards and wallet refresh; stage width 1124 px exceeds the two rails' combined 720 px; stage bottom 691 px |
| `isolated/mobile-ru-settled.png` | `settled` top | ru-RU | requested browser viewport 390 x 844; captured content 375 x 812 | Stacked controls, localized action/state, 375 px document width within the 390 px outer viewport |
| `isolated/mobile-ru-stage-settled.png` | `settled` stage | ru-RU | requested browser viewport 390 x 844; captured content 375 x 812 | Localized visible cards and ARIA names, ledger result, stacked data rail, no horizontal overflow |

## Live behavior results

- A production-handler `GET` with hostile `player_id=victim-player` returned the authenticated session player in a standard success envelope.
- A production-handler `POST` with the same hostile field settled for the authenticated player only.
- Repeating `rebase-evidence-002` returned HTTP 200 with `replayed: true`, the exact same round, exact same ledger evidence, and unchanged balance.
- Reusing that action ID with another bet returned HTTP 409 in the standard error envelope.
- A focused 51-round delayed replay removed the first action from visible history and deleted its fake provider events; the durable action index still returned the original round/evidence without reordering history or moving balance.
- Reload on `/games/dragon_tiger` preserved locale, both card ARIA labels, shoe count, and recent history.
- Back to the lobby and Forward to the game restored the Dragon Tiger route after reload-safe state recovery.
- Desktop measurements reported `scrollWidth == innerWidth == 1920`, a 1124 px stage versus two approximately 360 px rails, and a 691 px stage bottom; mobile reported `scrollWidth 375 <= innerWidth 390`.
- The frontend renders localized inert loading controls until the initial state GET settles, preventing a late GET from overwriting a just-committed POST; pending retries remain enabled with the same immutable payload.
- The game module owns no timer or animation-frame callback; reduced-motion CSS removes route-local animation and transitions.

## #77 registered acceptance

The shared integration lane resolves the isolated blockers by registering `dragon_tiger: 1.0.0`, permanent `DT-001` through `DT-005`, the compatibility matrix and digest, the visual-matrix row, central API/browser/restart cases, and the catalog-discovered Long Suite 100 driver.

`BR-DT-001` generates 48 PNGs plus 48 self-describing JSON sidecars from the tested head under `logs/test-runs`. The matrix covers `ready`, `settled`, `tie_half_loss`, `exact_replay`, `reduced_motion`, and `route_restored` in en-US and ru-RU at desktop primary, desktop compact, tablet, and mobile viewports. The test rejects raw keys and English game/shell leakage in Russian, requires horizontal containment, and verifies the active localized navigation label remains visible.

`API-DT-001` proves hostile caller player IDs cannot override either authenticated session, exact replay preserves the round, ledger evidence, and balance, changed reuse fails with `CONFLICT`, and each player receives one isolated wager debit plus at most one settlement credit. `API-WALLET-RESTART-001` proves settled history and shoe metadata survive restart. Suite 100 discovers `tests.game_drivers.dragon_tiger:play` from catalog metadata and exercises one complete real-backend action plus exact retry in every scenario.

The persistent shared shell now localizes wallet, ledger, player, and connection status copy on locale changes, centers the active catalog route at desktop and mobile widths, and keeps every top-level route control reachable in one bounded horizontal scroll region at the governed compact desktop (issue #221, CORE-006). At the time of this capture the catalog exposed 13 route controls; the route set is discovered from `casino.config.GAMES` plus Lobby and the role-gated Admin control. The provider's separate balance/evidence write boundary remains explicitly fail-closed: missing evidence requires reconciliation and never triggers an automatic repeat movement.

## #1029 shared lifecycle slice

Issue [#1029](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1029) moves Dragon Tiger's route ownership, busy-state coordination, locale lifecycle, request identity, and same-origin stylesheet loading onto `web/core/game_lifecycle.js`. The extracted `web/games/dragon_tiger.css` preserves the established dominant-center desktop table, stacked narrow layouts, 46-pixel controls, and reduced-motion behavior without changing game rules, API payloads, settlement, replay, or localization.

The registered `BR-DT-001` case remains the authoritative browser gate across every Dragon Tiger visual-matrix state, both locales, and all four named viewports. It additionally proves singleton external game/card stylesheet links across mount and reload, computed desktop geometry and touch targets, no inline game stylesheet, route teardown with no orphaned game DOM, real settlement, exact replay, and retained stylesheet reuse. The committed desktop-primary screenshot is copied from that exact after-pass run and is not a synthetic mock.

| Artifact | Surface state | Locale | Viewport | Verified properties |
| --- | --- | --- | --- | --- |
| `issue-1029-after-pass-desktop-en-US.png` (418,151 bytes; SHA-256 `08996c550ecc7c7b331fa58d976f0638bc27116b174940cddcdfc7deb45306af`) | `settled` | en-US | `desktop_primary` 1920 x 1080 | External stylesheet adoption, dominant center stage, 46-pixel controls, real settled cards and wallet state, and zero horizontal overflow |
