# Chuck-a-Luck after-pass evidence

Evidence class: `after_pass` for the isolated `chuck_a_luck` game surface.

Source branch: `codex/game-chuck-a-luck`

Tested source commit: `66b36dc78d419b04a3b9783e2ee59f114454a74e`

Focused command: `python tests/games/chuck_a_luck/browser_check.py --evidence-dir docs/evidence/chuck_a_luck`

Result: PASS on dedicated loopback port `65261`, process `64596`; listener and process closed. User listeners `8765` / PID `66932` and `8877` / PID `78548` remained unchanged. The harness forced the disposable JSON provider and redirected all player, ledger, game-state, authentication, and log writes to a temporary directory outside the worktree.

The pass used the real authenticated app, shared session-bound router, production game service, and shared ledger. Its game-local server shim loaded the issue-owned descriptor through the production catalog loader, added only the proposed `1.0.0` revision in memory, and held the first fully committed response until rolling-state assertions completed. It did not edit the aggregate manifest or shared runtime files.

## Evidence set

There are 28 PNG images and 28 matching JSON sidecars in this directory. Every sidecar records evidence class, branch, source commit, surface, state, locale, governed viewport ID and dimensions, and repository-relative image path.

| Surface | State | Locales | Browser assertion coverage | Image coverage |
| --- | --- | --- | --- | --- |
| `chuck_a_luck` | `ready` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | all eight locale/viewport pairs |
| `chuck_a_luck` | `rolling` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | desktop primary and mobile for both locales |
| `chuck_a_luck` | `settled` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | all eight locale/viewport pairs |
| `chuck_a_luck` | `reduced_motion` | en-US, ru-RU | desktop primary and mobile | desktop primary and mobile for both locales |
| `chuck_a_luck` | `route_restored` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | desktop primary and mobile for both locales |

The browser pass also verified standard success envelopes, server dice matching the rendered dice, page-level horizontal containment, minimum primary-action height, real reload restoration, and exact listener cleanup.

## Canonical integration evidence

This retained set proves the isolated game surface at its recorded source commit. Issue #77 separately promotes the canonical descriptor, permanent `CHUCK-001` through `CHUCK-005` requirements, aggregate manifest revision, compatibility registration, visual-matrix row, and central real-shell captures from the exact integrated head.
