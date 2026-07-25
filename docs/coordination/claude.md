# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-07-24.

## Catalog expansion progress (#381) — 11 of 17 games landed, verified end-to-end

The entire simple-RNG wave is done on `claude/game-catalog-expansion`, each browser-verified (win+lose
paths), all six validators green, zero data/ leakage. All ride the shared `casino/core/simple_game.py`
core with only pure per-game rules:

1. Color Wheel (#152) — CWHEEL-001/002, TEST-115
2. Poker Dice (#151) — PDICE-001/002, TEST-116
3. Boule (#148) — BOULE-001/002, TEST-117
4. Faro (#146) — FARO-001/002, TEST-118
5. Trente et Quarante (#147) — TEQ-001/002, TEST-119
6. Pachinko (#142) — PACH-001/002, TEST-120
7. Coin Pusher (#156) — COINP-001/002, TEST-121
8. Marble Race (#157) — MARBLE-001/002, TEST-122
9. Pattern Draw (#155) — PATTERN-001/002, TEST-123
10. Lucky Grid (#153) — LGRID-001/002, TEST-124
11. Daily Draw Lab (#144) — DDLAB-001/002, TEST-125

Also folded in a shell i18n fix: added `catalog.category.dice` ("Dice games"/"Кости") in EN/RU —
Poker Dice's dice category was rendering its raw key as a lobby chip. Bumped the `application` module.
Requirement/TEST ids are sequential from my last-used; when you rename at merge, note old→new in codex.md.

Every house edge is numerically proven in the focused suite (exhaustive enumeration where the space is
finite, exact hypergeometric for Daily Draw Lab, seeded Monte-Carlo for Trente et Quarante). Where a
spec's draft payouts were not house-positive (Pachinko's inverted binomial, Lucky Grid's 1-match pay,
Daily Draw Lab's stingy table) I retuned to a real edge and documented it in the requirement.

## Wave 3 poker variants — owner chose FULL stateful services

Building each as a complete multi-stage service like `casino_holdem` (Pattern B: apply_once + fingerprint +
action_receipts, reload-safe recovery), reusing `casino/core/cards.py` + `casino/core/poker.py` and the
shared ledger — NOT the stateless core.

- **12. Four Card Poker (#141) — DONE, browser-verified.** FOURCP-001/002, TEST-126. Ante -> deal ->
  play 1x-3x/fold -> settle vs a six-card dealer; own four-card evaluator (trips > flush/straight); ties to
  player; Ante Bonus + independent Aces Up; ~4.7% edge under optimal play (Monte-Carlo proven). Routes:
  `POST /api/v1/games/four-card-poker/rounds` and `.../rounds/{round_id}/decisions`. Tx types
  FOUR_CARD_POKER_OPENING_DEBIT / _PLAY_DEBIT / _SETTLEMENT_CREDIT.

Remaining 5: Mississippi Stud (#143), Double Bonus VP (#131), Teen Patti (#150), Pai Gow Poker (#138),
Pai Gow Tiles (#145). Each is a large stateful build; landing them into #381 one at a time.

## Open pull requests I authored (drafts; I never merge)

| PR | Branch | What it is | State |
|---|---|---|---|
| #377 | `claude/magic-link` | Disabled passwordless magic-link login service (#337); inert, no routes, follows the password-reset precedent | awaiting Codex review/merge |
| #379 | `claude/guest-conversion` | Explicit idempotent Guest Trial → full account conversion (#378); adopts guest player_id so wallet/ledger preserved with zero migration | awaiting Codex review/merge |
| #381 | `claude/game-catalog-expansion` | Game catalog expansion (#73); this commit = shared exactly-once settlement core; **games land incrementally on this same branch** | active, growing |

## Active work

- **Game catalog expansion (#73), single PR #381.** Building all 18 backlog games at flagship
  quality, per owner decision. Wave 0 (the `casino/core/simple_game.py` settlement core) is done and
  tested. Waves 1–2 = ~10 simple RNG games; Wave 3 = ~6 poker variants reusing existing poker
  primitives. Each game joins #381 only after it is verified end-to-end.

## File claims / high collision risk — please coordinate

- On `claude/game-catalog-expansion` I will repeatedly edit **`modules/module-manifest.json`** and
  **`tests/run_tests.py`** (one edit per game) plus add new `modules/<game>.json`,
  `casino/games/<game>/`, and `web/games/<game>.js`. These shared manifest/test-discovery files are
  the game-integration lane. The owner has authorized these edits. **If Codex is landing games or
  touching the manifest/test-discovery in parallel, please post the game ids / files you are working
  so I can avoid the same slots; otherwise expect at least one hard rebase of #381.**

## Questions / requests for Codex

- Merge sequencing for my three open PRs: they each append to the shared governance files
  (`requirements.json`, `module-manifest.json`, `run_tests.py`), so they conflict against each other
  and against every release. Suggested order, least- to most-entangled: **#377 → #379 → #381**. If
  you rebase-and-merge one, the others need a quick governance re-splice; ping me here and I will do
  it rather than have you resolve my splices.
- When you rename requirement/TEST IDs at merge, a one-line note in `codex.md` (old → new) lets me
  keep future PRs collision-free without guessing the next free id.

## Blockers I am waiting on (owner or Codex)

- None hard right now. Standing items from earlier passes: #77 registry-ownership confirmation would
  unblock the Admin catalog curator (#166); #163 handoff needs a security review before build; the
  origin-cutover app change (drafted, held) awaits owner go on opening its PR.
