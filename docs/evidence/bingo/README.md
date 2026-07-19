# Bingo card-purchase guard evidence

Evidence class: `after_pass` for the issue #259 Bingo purchase control rail.

Source branch: `codex/259-bingo-purchase-guard`

Tested source commit: `12abd967c5d5dda1306c65bae49b3db179216dfb`

The capture used the real authenticated application, the production Bingo service, and the shared ledger through the visible Buy control. Mutable data and logs used the JSON provider under a disposable temporary directory; no shared checkout state or user runtime was read or changed.

## Acceptance result

- While the first real purchase response was held after backend commit, the control rail reported `aria-busy="true"`, showed `Buy card…`, rendered the submitted action at `0.55` opacity with a wait cursor, and disabled Buy, amount, pattern, and reset.
- A second activation attempt issued no request: the exact request count remained one.
- After release, the rail returned to `aria-busy="false"`, normal visual contrast, and an enabled Call action.
- The authoritative result contained one human card, one visible card, and one `BINGO_CARD_PURCHASED` debit of `-5` play tokens.
- The permanent real-browser regression `BR-BINGO-PURCHASE-001` passed as part of the full `62/62` browser suite.
- Authenticated capture produced no console errors. The expected unauthenticated `/api/v2/me` login-gate probe was excluded before the governed flow began.

The supervised listener used process `48600` on `127.0.0.1:64812`. The process and exact listener were explicitly stopped and verified closed immediately after capture, and the temporary runtime directory was removed.

## Governed matrix row

- Surface: `bingo`
- State: `purchase_ready`, with `purchase_pending` and `purchase_recovered` variants
- Locale: `en-US`
- Viewport: `desktop_compact` (`1440 × 900`)
- Capture region: `bingo-control-rail`
- Gates: `VIS-COPY-001`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-CATALOG-001`

## Files

- `purchase_pending_en-US_desktop_compact.png` and its JSON sidecar show the locked in-flight boundary.
- `purchase_recovered_en-US_desktop_compact.png` and its JSON sidecar show the authoritative one-card recovery.

The screenshots are intentionally scoped to the affected Bingo control rail. They do not present the unrelated, already-tracked shared-shell navigation defects from the stacked base as passing evidence.
