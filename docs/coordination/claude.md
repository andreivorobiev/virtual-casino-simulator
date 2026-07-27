# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-07-26.

## Pull requests I authored (drafts; I never merge)

None of mine are open right now. States below follow `docs/coordination/codex.md`.

| PR | Branch | What it is | State |
|---|---|---|---|
| #377 | `claude/magic-link` | Disabled passwordless magic-link login service (#337); inert, no routes, follows the password-reset precedent | merged 2026-07-25; #337 still open for the broader magic-link item |
| #379 | `claude/guest-conversion` | Explicit idempotent Guest Trial → full account conversion (#378); adopts guest player_id so wallet/ledger preserved with zero migration | closed unmerged 2026-07-25; #378 still open with no attached PR |
| #381 | `claude/game-catalog-expansion` | Game catalog expansion (#73); shared exactly-once settlement core plus the first tranche of games | merged 2026-07-26 as settlement core + 12 games; #73 still open for the rest of the catalog |

## Active work

- **Game catalog expansion (#73).** The single-PR plan is finished: #381 merged on 2026-07-26 with
  Wave 0 (the `casino/core/simple_game.py` settlement core) plus 12 games. The remaining games did
  not land on that branch — they shipped as separate PRs #389, #390, #391, and #392. #73 stays open
  for the rest of the catalog work. The catalog has already grown past the original 18-game backlog
  plan; the live game set is discovered from `casino.config.GAMES` / `casino/games/`, so read it
  there rather than trusting a count written here.

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
