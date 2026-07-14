# Chuck-a-Luck evidence status

Evidence class: blocked pre-integration record; not acceptance evidence.

The isolated module does not claim shared-route `after_pass` evidence before issue #77 registers its descriptor, contract, locale resources, and visual-matrix rows. Known-failing, concept-only, or manually assembled imagery is intentionally absent. A game-local focused harness may verify the isolated surface, but that output does not replace post-integration acceptance evidence.

Provisional requirement scope: `CHUCK`; permanent requirement IDs remain a blocker for #77.

Required post-integration evidence:

| Surface | State | Locales | Viewports | Required proof |
| --- | --- | --- | --- | --- |
| `chuck_a_luck` | `ready` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Complete controls, three-die stage, paytable, and no horizontal overflow |
| `chuck_a_luck` | `rolling` | en-US, ru-RU | desktop primary, mobile | Stable stage, disabled duplicate action, decorative preview, and owned timer cleanup |
| `chuck_a_luck` | `settled` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Server dice, wallet refresh, localized net result, and recent-round restoration |
| `chuck_a_luck` | `reduced_motion` | en-US, ru-RU | desktop primary, mobile | Immediate reveal with no decorative delay or lingering transform animation |
| `chuck_a_luck` | `route_restored` | en-US, ru-RU | desktop primary, mobile | Reloaded settled result, retained server dice, and no duplicate ledger action |

Each future `after_pass` artifact must record branch, commit, surface, state, locale, viewport, and path under the protocol in `docs/visual_design_standard.md`.
