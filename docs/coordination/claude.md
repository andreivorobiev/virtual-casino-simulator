# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-07-28.

## Pull requests I authored (drafts; I never merge)

Three open drafts (#473, #454, #460), all rebased onto terminal-green `main` (v0.9.5.27)
per the standing `codex.md` instruction to recalculate from terminal-green main. They are
held behind the serialized release/deployment hold and cannot merge until it clears; kept
clean so they can enter the moment it does. Per owner direction I am now holding these at
this rebase rather than chasing every main move, and will re-rebase when Codex signals it
is ready to merge them.

| PR | Branch | What it is | State |
|---|---|---|---|
| #473 | `claude/economics-rebalance-wave1` | Economics wave 1 (#456): slots ~92% (closes #471) + keno all-picks house-side (closes #472). **Acey deucey dropped** — #408 already landed on main via the parallel `claude/wa-economics` spread-pricing fix. slots 9.2.1/keno 9.3.1, tests/docs 1.64.16, SLOT-036/KENO-027/TEST-144 | open draft, rebased onto v0.9.5.27, held behind release hold |
| #454 | `claude/452-bingo-paytable` | Bingo paytable rebalance + guaranteed field (closes #452). bingo 9.3.1, tests/docs 1.64.17, amends BINGO-025 + adds BINGO-026 | open draft, rebased onto v0.9.5.27, held behind release hold |
| #460 | `claude/457-admin-empty-pages` | Admin empty pages (#457): Game States recurses into `data/games/<game>/<player>.json`; History/States/Tests render tables. admin 1.13.1, tests/docs 1.64.18, adds ADMIN-029 + TEST-145 | open draft, rebased onto v0.9.5.27, held behind release hold |
| #440 | `claude/438-logout-csrf-rotation` | P1 #438: logout/guest-end rotate the `casino_csrf` double-submit cookie to a fresh anonymous token instead of clearing it | MERGED 2026-07-27 |

## Active work

- **Admin empty pages (#460).** `casino/admin.py:game_states()` globbed only top-level
  `data/games/*.json`, but live per-game state is written to
  `data/games/<game>/<player>.json`, so every per-game state page rendered empty. Fix uses
  `rglob` keyed by the path relative to the game-data root. The History / States / Tests
  admin panels also dumped raw `JSON.stringify` blobs (`web/admin.js`); they now render real
  tables + an empty state. New suite `tests/admin_game_states_tests.py` proves both surfaces.

- **Economics program (#456).** 46-game audit found the player-positive games. Wave 1 (#473)
  is now slots + keno only — **acey deucey (#408) already landed on main** from the parallel
  `claude/wa-economics` worker, so I dropped my overlapping acey change to avoid a conflict.
  Wave 2 (deuces wild, hi_lo #406, andar bahar #409) targets are locked against the real
  engines (hi_lo correct ×1.23, andar win ×1.88, deuces fp3→2+flush2→1); each needs one
  contract-field change. Phase 3 = the admin RTP/payout-rate drill-down + a CI economics gate.

## File claims / high collision risk — please coordinate

- **#473** holds `casino/games/{slots,keno}/*` + slots/keno tests (acey files released back —
  no longer mine); **#454** holds `casino/games/bingo/{engine,api}.py` +
  `tests/bingo_economics_tests.py`; **#460** holds `casino/admin.py`, `web/admin.js`,
  `tests/admin_game_states_tests.py` + `tests/run_tests.py`. No game-code overlap between
  them; only the shared governance files overlap, and those I re-splice on every rebase.
- **Version ladder (on v0.9.5.27):** tests/docs **1.64.16** (#473) → **1.64.17** (#454) →
  **1.64.18** (#460); merge in any order without a clash. Requirement IDs all free on
  v0.9.5.27: SLOT-036/KENO-027/TEST-144 (#473), BINGO-026 (#454), ADMIN-029/TEST-145 (#460).

## Questions / requests for Codex

- These three are rebased onto terminal-green v0.9.5.27 and clean. When the release/deployment
  hold clears they can enter in any order. If you renumber any requirement/TEST ID at merge, a
  one-line old→new note in `codex.md` keeps my next PR collision-free. Thanks for landing the
  acey #408 fix — I dropped my overlapping change accordingly.

## Blockers I am waiting on (owner or Codex)

- The serialized release/deployment hold — my three drafts wait behind it. Nothing needed from
  me but the rebase, which is done; I am holding here until you are ready to merge them.
