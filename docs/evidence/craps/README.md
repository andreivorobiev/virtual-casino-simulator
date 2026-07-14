# Craps evidence status

Issue: [#90](https://github.com/andreivorobiev/virtual-casino-simulator/issues/90)

Evidence class: pre-integration record; not acceptance evidence.

No `after_pass` screenshot or browser artifact is stored for this isolated slice. The descriptor cannot produce honest shared-shell acceptance until #77 adds the canonical module revision, permanent requirements, compatibility metadata, central test mappings, and visual-matrix surface. Static markup, focused unit output, mock-server imagery, and known-failing shared-shell captures must not be relabeled as acceptance evidence.

## Required post-integration evidence

| Surface | State | Locales | Viewports | Required proof |
| --- | --- | --- | --- | --- |
| `craps` | `ready` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Line-bet and wager controls, full dominant table stage, localized rules, and no horizontal overflow |
| `craps` | `come_out` | en-US, ru-RU | desktop primary, mobile | Committed wager, clear come-out status, enabled primary roll action, and current wallet |
| `craps` | `point_active` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Visible point marker, prior dice, stable controls, and reload-safe continuation |
| `craps` | `settled` | en-US, ru-RU | desktop primary, desktop compact, tablet, mobile | Backend dice, localized win/loss/push result, refreshed wallet, and immutable roll history |
| `craps` | `reduced_motion` | en-US, ru-RU | desktop primary, mobile | Asynchronous zero-delay reveal with no lingering animation or timer |
| `craps` | `route_restored` | en-US, ru-RU | desktop primary, mobile | Direct route, reload, Back, and Forward restore the same authenticated game state |

Every future `after_pass` artifact must record branch, exact commit, evidence class, surface, state, locale, viewport, and repository path under `docs/visual_design_standard.md`. Listener evidence must also record its loopback port and PID, then prove the listener closed without touching port 8765 or shared runtime data.
