# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-07-31.

## Pull requests I authored (drafts; I never merge)

States follow `docs/coordination/codex.md`; #481 and #518 are held behind the release lane per that file.

| PR | Branch | What it is | State |
|---|---|---|---|
| #564 | `claude/comment-quality` | Program task 6: comment quality in five audited files + documented density-gate exemption (#555), stacked on #562 | open draft, ready for review |
| #562 | `claude/legacy-settlement-keno-baccarat` | Program task 5: keno+baccarat entropy-committed exactly-once settlement (#555, advances #430), stacked on #561 | open draft, ready for review |
| #561 | `claude/guest-endpoint-hardening` | Program task 4: per-source guest-creation rate limit + bounded source log (#555), stacked on #559 | open draft, ready for review |
| #559 | `claude/arch-diagram` | Program task 2: ARCHITECTURE.md request-path Mermaid diagram (#555), stacked on #558 | open draft, ready for review |
| #558 | `claude/readme-front-door` | Program task 1: README Design decisions + RELEASE_NOTES status archive + token-validator repair/CI wiring (#555) | open draft, ready for review |
| #454 | `claude/452-bingo-paytable` | Bingo paytable house-side rebalance + guaranteed competitor field (#452) | open draft; governance re-splice on Codex merge signal (owner 2026-07-28 hold decision) |
| #460 | `claude/457-admin-empty-pages` | Admin console empty-page fixes (#457) | open draft; same hold |
| #506 | `claude/456-admin-rtp-view` | Admin per-game payout-rate view (#456 phase 3), stacked on #460 | open draft; same hold |
| #481 | `claude/game-real-red-green` | Post-rebrand game colours: real red/green, metallic gold | open; held behind release lane |
| #518 | `identity-admin-redesign` | Identity/admin redesign: session timeouts, nested console, Sessions page | open; held behind release lane |

## Active work — reviewer-readiness program (owner-directed, 2026-07-31) — ALL SIX TASKS BUILT; PRs #558→#559→#561→#562→#564 stacked and ready for review

The owner asked for a bounded polish-and-hardening pass before an external technical review of the repository on 2026-08-07. Six small sequential PRs, one task each. Constraints: no new features, no new games, no renames, no `contracts/` schema or server-authority generation changes, every PR keeps the full suite green.

1. `claude/readme-front-door` — README "Current repository status" prose moved verbatim into a dated `RELEASE_NOTES.md` archive section; README gains a six-bullet "Design decisions" section. **Note for release packets: README no longer carries per-release status prose — release status belongs in `RELEASE_NOTES.md` only; please stop rewriting that README section at release time.**
2. ARCHITECTURE.md gains one Mermaid request-path diagram near the top (docs only).
3. Featured-game smoke pass — DONE 2026-07-31, all six clean (full round, balance math exact, mid-round reload recovery verified per game); no fix PR needed. One out-of-scope find filed as #557 (wallet add-tokens #247 guard races behind refreshShellState; also the root cause of local BR-TOKEN-001 flakiness).
4. Guest-trial endpoint hardening: per-IP rate limit on `POST /api/v2/auth/guest` reusing the existing `casino/core/security.py` limiter pattern and error taxonomy, plus a bounded guest-creation source record. No `GUEST_STARTING_BALANCE` or gameplay changes.
5. Legacy settlement migration (limited): 2-3 of the six original games move onto `casino/core/simple_game.py` exactly-once settlement, with retry-safety tests; ARCHITECTURE.md "Known gap" updated to match. The remaining originals stay legacy and stay documented as such.
6. Comment quality in five high-traffic files (simple_game.py, auth.py, validate_module_boundaries.py, validate_token_terminology.py, verify_keno_economics_artifact.py): tautological comments replaced with purpose/why comments; if density drops below the gate, a documented per-path exemption list is added to `check_comment_density.py` instead of lowering the global threshold.

## File claims / high collision risk

- PR 1 (this branch): `README.md`, `RELEASE_NOTES.md` (append-only archive at EOF), `modules/application.json` (9.55.2), `modules/docs.json` (1.64.58), `modules/module-manifest.json`, regenerated `CODEX_START_HERE.md` + `requirements_generated.md`, this file.
- Upcoming claims: `ARCHITECTURE.md` (PRs 2 and 5, different sections); `casino/core/auth.py` + `casino/core/security.py` + `tests/security/` (PR 4); `casino/games/<2-3 legacy games>` + `tests/games/<same>` (PR 5, exact games named in that PR); `scripts/check_comment_density.py` + the five listed files (PR 6).
- Version claims: application 9.55.2, docs 1.64.58 (PR 1). Later PRs claim sequentially above current main at open time; I re-bump on rebase if a release lands in between.

## Questions / requests for Codex

- Merge order for the program PRs: sequential oldest-first preferred but not required; PRs 2 and 5 both touch `ARCHITECTURE.md` in different sections and merge cleanly in either order.

## Blockers I am waiting on (owner or Codex)

- None.
