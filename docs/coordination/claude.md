# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-07-26.

## Pull requests I authored (drafts; I never merge)

One open draft (the #438 fix below). States below follow `docs/coordination/codex.md`.

| PR | Branch | What it is | State |
|---|---|---|---|
| #440 | `claude/438-logout-csrf-rotation` | P1 #438: logout/guest-end now rotate the `casino_csrf` double-submit cookie to a fresh anonymous token instead of clearing it, so sign-in after logout works without a shell reload | open draft, awaiting Codex review |
| #377 | `claude/magic-link` | Disabled passwordless magic-link login service (#337); inert, no routes, follows the password-reset precedent | merged 2026-07-25; #337 still open for the broader magic-link item |
| #379 | `claude/guest-conversion` | Explicit idempotent Guest Trial → full account conversion (#378); adopts guest player_id so wallet/ledger preserved with zero migration | closed unmerged 2026-07-25; #378 still open with no attached PR |
| #381 | `claude/game-catalog-expansion` | Game catalog expansion (#73); shared exactly-once settlement core plus the first tranche of games | merged 2026-07-26 as settlement core + 12 games; #73 still open for the rest of the catalog |

## Active work

- **Logout CSRF rotation (#438, P1).** Owner-reported: every sign-in after logout failed with
  "CSRF validation failed" until a manual reload, because logout expired the `casino_csrf`
  double-submit cookie and only an `index.html` load re-issues one. Fix rotates the cookie to a
  fresh anonymous bootstrap token on `/api/v2/auth/logout` and `/api/v2/auth/guest/end` (shared
  `clear_cookie_headers` helper). Versions recalculated around in-flight claims: core 9.24.5
  (9.24.3/9.24.4 absorb #428/#429), tests/docs 1.60.38 (1.60.37 is #439's). Will re-bump on rebase
  if those land differently.

- **Game catalog expansion (#73).** The single-PR plan is finished: #381 merged on 2026-07-26 with
  Wave 0 (the `casino/core/simple_game.py` settlement core) plus 12 games. The remaining games did
  not land on that branch — they shipped as separate PRs #389, #390, #391, and #392. #73 stays open
  for the rest of the catalog work. The catalog has already grown past the original 18-game backlog
  plan; the live game set is discovered from `casino.config.GAMES` / `casino/games/`, so read it
  there rather than trusting a count written here.

## File claims / high collision risk — please coordinate

- On `claude/438-logout-csrf-rotation` I hold **`casino/core/auth.py`** (cookie helper),
  **`casino/core/security.py`** (removed the now-unused `clear_csrf_cookie_header`),
  **`tests/security/test_policy.py`**, **`tests/security/security_wsgi_probe.py`**, plus the shared
  governance files (`requirements.json`, generated docs, `modules/core|tests|docs.json`,
  `module-manifest.json`). Metadata-only overlap expected with #428/#429/#439 — I claimed
  collision-free version numbers, and I will re-splice on whichever merges first.
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
