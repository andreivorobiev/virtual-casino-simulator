# Daily Draw Lab lifecycle-adopter evidence

This after-pass evidence covers the first bounded adopter slice of issue #718 and permanent owners `CORE-034` and `TEST-248`. The affected visual-matrix surface is `daily_draw_lab`; the slice intentionally preserves its `ready` and settled presentation while moving lifecycle ownership into `web/core/game_lifecycle.js` and the same CSS declarations into a formatted external module asset.

## Evidence

`issue-718-after-pass-desktop-en-US.png` is captured by the permanent `BR-DAILY-DRAW-LAB-001` Browser case from the real authenticated shell before its real settled draw. The case requires exactly one `link#daily-draw-lab-styles` pointing to `/games/daily_draw_lab.css`, the unchanged two-column desktop route, the unchanged six-column number board, the real draw response, terminal wallet convergence, reload recovery, and the enabled repeat action.

The PNG is 384,779 bytes with SHA-256 `9dcce675a6604059d9ae64b5ce821c8a79ad50cb4fb327a8be2684836f408744`. It shows the English `ready` state at the primary desktop viewport. Existing catalog-wide responsive and Russian-locale Browser gates remain unchanged and passed before the dedicated affected-game case; no intentional visual delta, game math, wager, payout, outcome, ledger, API, contract, provider, package, release, or deployment change is part of this slice.

## Acceptance boundary

The listener-free `UI-GAME-LIFECYCLE-001` case owns lifecycle semantics and duplicate-helper deletion. The dedicated Browser case owns the rendered external-style proof and real game flow. Future issue #718 adopter slices repeat this boundary per game instead of broadening this first slice.
