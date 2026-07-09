# Premium Shell, Lobby, Admin Prerenders

Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/7

Scope: proposal artifacts only. No production files under `web/`, `casino/`, `contracts/`, `tests/`, `docs/requirements/`, or `modules/` were edited.

## Preview Artifacts

| Preview | PNG | Source |
| --- | --- | --- |
| Premium lobby | `premium-lobby.png` | `premium-lobby.html` |
| Shared topbar/navigation/wallet shell | `shared-shell-wallet.png` | `shared-shell.html` |
| Admin dashboard | `admin-dashboard.png` | `admin-dashboard.html` |
| Admin Language/Locale | `admin-language-locale.png` | `admin-language-locale.html` |
| Responsive narrow sketch | `responsive-narrow.png` | `responsive-narrow.html` |

Shared source styling lives in `premium-shell.css`. Local raster assets live under `assets/`.

## Design Rationale

- The lobby follows the approved target direction: dark emerald casino room, gold trim, visible wallet, stable nav, trust/status rails, and rich game cards.
- The shared shell keeps wallet and route navigation fixed while game content occupies stable panel regions, preserving the current compact 1080p constraint.
- The admin redesign keeps a dense control-plane layout instead of a marketing feel: sidebar navigation, compact metrics, data tables, and log panels.
- The Language/Locale section proposes English and Russian as first ready locales, with a top-20 catalog layout that can scale without redesigning the admin surface.
- The narrow sketch compresses brand, wallet, and route controls into stacked rows while keeping the premium card treatment.

## State Coverage

- Lobby: all six current games, fake-money messaging, balance, ledger/status rail, bots/autoplay/stat tags.
- Shared shell: active Roulette route, human balance, round controls, autoplay readiness, reserved result area, action dock, right-side ledger/status rail.
- Admin dashboard: app version, players, bots, active autoplay, errors, requirements, recent ledger, sessions, telemetry logs.
- Admin Language/Locale: English/Russian selection, future language catalog, region/number/currency/date/fallback controls, browser persistence toggles, preview strings.
- Responsive: narrow lobby composition for mobile-sized review.

## Requirement Mapping

- Proposed future requirements: `UX-007`, `UX-008`, `I18N-002`.
- Existing requirements considered: `CORE-005`, `CORE-006`, `CORE-015`, `LEDGER-025`, `ADMIN-013`, `ADMIN-019`, `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-005`, `UX-006`.
- No contracts, APIs, ledgers, gameplay, module versions, or tests were changed in this proposal-only phase.

## Future Implementation File List

Likely implementation files for a later approved task:

- `web/styles.css` for shared shell, lobby cards, admin visual system, and responsive layout.
- `web/app.js` for lobby card metadata, shell state, wallet/status rail composition, and navigation affordances.
- `web/admin.html` for adding the proposed Language/Locale tab entry and admin shell structure.
- `web/admin.js` for dashboard rendering changes and future language/locale settings screen.
- Future i18n resources under an approved location such as `web/i18n/` or `web/core/i18n.js`.
- Future admin settings API/storage files if language persistence becomes server-backed.

## Asset Notes

AI-generated raster art was used through the built-in `image_gen` tool, then copied into this artifact folder:

- `assets/casino-backdrop.png`
- `assets/slot-machine.png`

Prompt summary: create a wide, cinematic dark casino lobby backdrop with roulette/card tables, warm gold practical lighting, polished dark wood, green felt, deep emerald/black/gold palette, no logos, no readable text, no UI, no watermark, and no close-up people. A second generated slot-machine image from the same premium casino direction was used for the Slots card.

Code-native CSS art was used for deterministic UI elements and secondary game surfaces so labels, wallet values, language controls, tables, and responsive behavior remain crisp.

## Rendering Notes

PNGs were rendered from the HTML sources with bundled Playwright/Chromium:

- Desktop previews: `1680x945`.
- Narrow preview: `390x844`.

No production validation scripts were required for this prerender-only task.

## Open Questions

- Should Language/Locale persist only in browser storage, or should Admin expose a server-backed global setting?
- Should the top-20 language list be ranked by global usage, project priority, or installed resource packs?
- Should the final implementation use generated raster card art, curated static assets, or CSS/canvas-native game illustrations for long-term maintainability?
- Should Admin Language/Locale be its own tab, or merged into a broader System/Preferences area?
