# Issue #88 browser evidence

Classification: `after_pass` for the isolated Sic Bo slice only. These captures do not claim shared #77 catalog, manifest, compatibility-matrix, generated-requirements, or visual-matrix acceptance.

Source branch: `codex/issue-88-sic-bo`. The exact source commit is recorded in the draft pull request validation section because a file cannot self-reference its own commit hash.

## Real-shell harness

`tests/games/sic_bo/browser_server.py` loaded the exact inert descriptor from `INTEGRATION.md` into one process before importing the real application. It redirected data and logs to system-temporary directories, used the real shell/auth/router/storage/ledger/static assets, and never created or edited a shared descriptor, manifest, registry, catalog, or visual-matrix file.

The listener bound only `127.0.0.1:63969`. English evidence used PID `79580`; Russian/mobile evidence used PID `65844`. The tool-owned process lifetime ended each listener before route-restoration capture, after which TCP closure was independently verified and all three harness temporary roots plus ready/stop control files were removed. Port `8765` and workspace `data/` were not read, written, stopped, or cleaned.

## Named evidence

| Proposed surface | State | Locale | Viewport | Evidence |
| --- | --- | --- | --- | --- |
| `game_sic_bo` | `wagers_selected` | `en-US` | `desktop_primary` 1920x1080 | `after_pass_desktop_primary_en-US_wagers_selected.png` |
| `game_sic_bo` | `settled` | `en-US` | `desktop_primary` 1920x1080 | `after_pass_desktop_primary_en-US_settled.png` |
| `game_sic_bo` | `settled` | `en-US` | `desktop_compact` 1440x900 | `after_pass_desktop_compact_en-US_settled.png` |
| `game_sic_bo` | `ready` | `ru-RU` | `mobile` 390x844 | `after_pass_mobile_ru-RU_ready.png` |

The permanent `game_sic_bo` matrix row is only a proposal until #77 registers it. Proposed additional states are `ready`, `wagers_selected`, `rolling`, `settled`, `reduced_motion`, and `route_restored`.

## Browser assertions

- Desktop primary exposed all 50 semantic position buttons, a minimum position height of 42 CSS pixels, no horizontal overflow, a 832.33px complete game surface inside the 934px shared game viewport, and no game-screen scroll.
- The real authenticated round rolled server-owned dice `[1, 1, 5]`, debited 1 play token once, credited 2 returned play tokens once, refreshed the shell wallet from 5,000 to 5,001, and showed one history row.
- Desktop compact exposed one themed game-screen scrollbar (`overflow-y: auto`), removed the competing data-rail scrollbar, and had no page-level horizontal overflow.
- Tablet 1024x900 stacked controls, stage, and data in that order, preserved a minimum 46px position height, used document scrolling, and had no horizontal overflow.
- Mobile 390x844 stacked controls, stage, and data in that order, exposed all 50 positions, preserved a minimum 46px position height, and had no horizontal overflow.
- The Russian game surface rendered `Сик Бо`, `Можно бросать кости`, `Бросить кости`, and the accessible name `Игровой стол Сик Бо`; no game-owned visible or ARIA string fell back to English or a resource key.
- The focused timer test proves ordinary reveal timing, zero-delay reduced-motion behavior, pagehide cancellation, listener removal, and terminal disposal through #97 `createMotionTimerScope`.

The attempted live `route_restored` browser capture was interrupted by the background-listener tool cutoff, not by a game assertion. Reload safety remains covered by the focused prepared/debit/payout crash-recovery tests; #77 must capture real catalog route restoration during shared acceptance.
