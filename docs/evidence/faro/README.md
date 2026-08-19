# Faro lifecycle-adopter evidence

This after-pass evidence covers the second bounded adopter slice of issue #718 and permanent owners `CORE-034` and `TEST-248`. The affected visual-matrix surface is `faro`; the slice intentionally preserves its `ready` and `repeat_available` presentation while moving lifecycle ownership into `web/core/game_lifecycle.js` and the same CSS declarations into a formatted external module asset.

## Evidence

`issue-718-after-pass-desktop-en-US.png` is captured by the permanent `BR-FARO-001` Browser case from the real authenticated route outlet before its real settled deal. The case requires exactly one `link#faro-styles` pointing to `/games/faro.css`, the unchanged two-column desktop route, the unchanged seven-column rank grid, the real deal response, terminal wallet convergence, reload recovery, and the enabled repeat action.

The PNG is 313,385 bytes with SHA-256 `cb01baed25d9ef6237454b1a2dacdc46c9cd8f51ca72388f7b09951b3f173f93`. It shows the English `ready` state at the primary desktop viewport. Existing catalog-wide responsive and Russian-locale Browser gates remain unchanged; no intentional visual delta, game math, wager, payout, outcome, ledger, API, contract, provider, package, release, or deployment change is part of this slice.

## Acceptance boundary

The listener-free `UI-GAME-LIFECYCLE-001` case owns lifecycle semantics and duplicate-helper deletion. The dedicated `BR-FARO-001` case owns the rendered external-style proof and real game flow. Future issue #718 adopter slices repeat this boundary per game rather than broadening earlier adopters.
