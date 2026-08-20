# Pachinko lifecycle-adopter evidence

This after-pass evidence covers the fourth bounded adopter slice of issue #718 and permanent owners `CORE-034` and `TEST-248`. The affected visual-matrix surface is `pachinko`; the slice intentionally preserves its `ready` and `repeat_available` presentation while moving lifecycle ownership into `web/core/game_lifecycle.js` and the same CSS declarations into a formatted external module asset.

## Evidence

`issue-999-after-pass-desktop-en-US.png` is captured by the permanent `BR-PACHINKO-001` Browser case from the real authenticated route outlet before its real settled drop. The case requires exactly one `link#pachinko-styles` pointing to `/games/pachinko.css`, the unchanged two-column desktop route, the unchanged thirteen-column pockets grid, the real drop response, terminal wallet convergence, reload recovery, and the enabled repeat action.

The accepted PNG is 342,269 bytes with SHA-256 `4c795031d2a1f881b34512ec177cb4a42d0fa26d2709a934b5270724d5c580a2`. It shows the English `ready` state at the primary desktop viewport. Existing catalog-wide responsive and Russian-locale Browser gates remain unchanged; no intentional visual delta, game math, wager, payout, outcome, ledger, API, contract, provider, package, release, or deployment change is part of this slice.

## Acceptance boundary

The listener-free `UI-GAME-LIFECYCLE-001` case owns lifecycle semantics and duplicate-helper deletion. The dedicated `BR-PACHINKO-001` case owns the rendered external-style proof and real game flow. Future issue #718 adopter slices repeat this boundary per game rather than broadening earlier adopters.
