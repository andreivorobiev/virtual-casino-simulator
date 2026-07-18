# Baccarat mutation-serialization evidence

Evidence class: `after_pass` for the issue #252 Baccarat result surface.

Source branch: `codex/252-baccarat-mutation-serialization`

Tested source commit: `ef3680a338c07052378a5cc36c10571eb8867717`

The capture used the real authenticated application, the production Baccarat service, and the shared ledger through visible browser controls. Runtime state used the JSON provider under a disposable temporary directory; no shared checkout state or user runtime was read or changed.

## Acceptance result

- A single visible Banker wager produced one committed debit and one settled human bet.
- The result drawer contains exactly one settlement row and the backend has no phantom open wager.
- The serialized mutation boundary returned to `aria-busy="false"` after settlement.
- The governed `desktop_compact` viewport has document width `1440` and client width `1440`, proving no page-level horizontal overflow.
- Visual inspection confirmed the Baccarat title, wager controls, cards, result, settlement, shoe, and road are legible and contained. The visible `◈` character is the intentional `U+25C8` play-token marker; byte and DOM checks confirmed it is not a replacement glyph.

The source was also validated by `BR-BAC-MUTATION-001` in the full real-browser suite: `61/61` cases passed with no final console, page, or unexpected network errors. The normal unauthenticated `/api/v2/me` probe used to present the login gate returned the expected `401` before authenticated capture.

The supervised listener used process `44744` on `127.0.0.1:50182`. The process and listener were explicitly stopped and verified closed immediately after capture, and the temporary runtime directory was removed.

## Governed matrix row

- Surface: `baccarat`
- State: `result`
- Locale: `en-US`
- Viewport: `desktop_compact` (`1440 × 900`)
- Gates: `VIS-COPY-001`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-CATALOG-001`
