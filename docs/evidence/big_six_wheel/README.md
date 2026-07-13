# Big Six Wheel evidence status

Evidence class: blocked pre-integration record; not acceptance evidence.

The isolated module has no honest `after_pass` browser image yet because #110 owns catalog/router/shell/test discovery and #77 owns shared registration and visual-matrix integration. Known-failing or manually assembled imagery is intentionally absent.

Required post-integration evidence:

| Surface | State | Locales | Viewports | Required proof |
| --- | --- | --- | --- | --- |
| `big_six_wheel` | `ready` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Full controls, wheel, paytable, and no horizontal overflow |
| `big_six_wheel` | `spinning` | en-US, ru-RU | desktop primary, mobile | Stable stage, disabled duplicate action, timer ownership |
| `big_six_wheel` | `settled` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Backend result, wallet refresh, localized net result |
| `big_six_wheel` | `reduced_motion` | en-US, ru-RU | desktop primary, mobile | Zero-delay reveal and no lingering transform animation |

Each future `after_pass` artifact must record branch, commit, surface, state, locale, viewport, and path under the protocol in `docs/visual_design_standard.md`.
