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

## Honest blockers retained for #77

- The aggregate manifest and canonical revision map do not yet contain `dragon_tiger: 1.0.0`; catalog and version validators therefore fail at the expected shared boundary.
- Permanent `DT-001` through `DT-005`, compatibility inventories/digests, visual-matrix rows, and central test discovery remain unregistered.
- The shared shell retains English wallet/footer/status copy in ru-RU, including `PLAY TOKEN BALANCE`, `Ledger-backed outcomes`, and `Connected`; #77 must localize those shared strings before RU acceptance.
- The shared navigation clips the active `Dragon Tiger` label to `Dragon` at the desktop viewport edge, while the mobile carousel begins with a clipped `Лобби` and leaves the active route offscreen; #77 owns active-route visibility and shared-nav scrolling.
- The shared JSON provider stores balance and ledger evidence separately. Dragon Tiger now persists pre-movement stages and fails closed when evidence is absent, preventing a repeated debit or credit, but automatic reconciliation still requires a shared atomic/idempotent ledger primitive or an approved operational gate.

## Required post-integration acceptance

#77 must rerun the registered backend and visual matrix from its exact accepted head, including ready, settled, tie half-loss, exact replay, reduced motion, and route-restored states in both locales and all required viewports. Only those captures may be marked `after_pass`.
