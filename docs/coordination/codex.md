# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-27T07:07:26Z.

## Merge queue / recently merged

- `origin/main` is `96ac4584` after #439 `codex/monitor-env-runner-v0.9.5.9` merged and published release assets for v0.9.5.9.
- Open PR queue as of this pass:
  - #428 `claude/slice1-storage-settings-authority` is green but `DIRTY` against current main. Do not merge until rebased/spliced onto `96ac4584` and fresh exact-head checks pass. Also ensure the merge carries a unique release/app version so the protected-main deploy does not collide with the existing v0.9.5.9 tag.
  - #429 `claude/slice5-frontend-a11y` is green but `DIRTY` against current main. Sequence after #428 unless explicitly reworked. Do not merge until rebased/spliced and fresh exact-head checks pass. The release carrying #429 must rotate `web/sw.js` `APP_VERSION` and `web/core/pwa.js` `PWA_APP_VERSION`; #418 is no longer closed by this PR per Claude's correction.
  - #440 `claude/438-logout-csrf-rotation` is draft and `DIRTY`. Do not merge while draft or dirty, even though its existing checks are green.
  - #425 `claude/tiltseven-rebrand` is `BEHIND`; `browser_tests` is failing and `long_suite_100` was still in progress when checked. Hold until rebased and green.
  - #399 `claude/games-repeat-play` is `BEHIND` with failing `browser_tests`. Prior Codex gate remains: do not review substantively until it is rebased and Claude explicitly acknowledges the new P1 queue / stack-rank 001-016.
- Recent merged work includes #424, #427, #436, #437, and #439. Earlier status lines in this file about #401 being open are superseded; #401 is already merged.

## Production deployment status

- Production Deploy is not healthy. The latest main deploy run for #439/v0.9.5.9 (`30243768771`, head `96ac4584`) ended `cancelled` during deploy upload.
- The preceding protected-main deployment runs for v0.9.5.8, v0.9.5.7, v0.9.5.6, #401, #424, #400, and #398 failed.
- Current durable blocker is #435: GitHub-hosted Actions cannot reach the SSH endpoint used by Production Deploy. Do not keep rerunning deploy while the SSH endpoint is still unreachable; it needs a reachable SSH host/port, bastion, or self-hosted runner path before deployments can complete.
- `casino.tiltseven.com` resolves to `45.63.35.198` in this pass. Public reachability checks from this environment did not prove an alternate deploy path.

## Requirement / TEST ID renames at merge

- No requirement or TEST ID renames recorded in this pass.
- #428/#429/#440 touch shared release/governance surfaces and need fresh splice after the current main head.
- #399 and #425 still collide with browser-visible/game-shell work; coordinate before rebase/merge.

## File claims / lane ownership

- Codex is not currently landing games.
- Codex is not claiming `web/games/*`, game i18n, or frontend-test repeat-bet surfaces while #399 is open.
- Codex is not claiming TiltSeven brand-token/shell chrome files while #425 is open.
- Codex is not resolving Claude's governance splices in #428/#429/#440 unless explicitly taking ownership of the branch for a rebase/version pass.
- Claude-owned `docs/coordination/claude.md` is stale relative to GitHub reality, but Codex must not edit it under the coordination protocol.

## Backlog reconciliation completed

- Prior cleanup remains valid through #401: every open issue had exactly one of `P1`, `P2`, or `P3`; no `P4`; unique `stack-rank:001` through `stack-rank:088` at that time.
- Follow-up cleanup in this pass:
  - #435 changed from invalid `P0` to `P1` and received `blocked` / `ops` / `deployment`.
  - #432 received `P2`; #433 received `P1`.
  - #435 became `stack-rank:001`; the prior ranked queue shifted down one slot.
  - Remaining unranked new issues were assigned: #163 `stack-rank:089`, #438 `090`, #431 `091`, #433 `092`, #426 `093`, #430 `094`, #432 `095`, #434 `096`.
  - Verified final open queue: 96 open issues; no missing priorities, no conflicting priorities, no `P0`/`P4`, no missing stack-ranks, and no duplicate stack-ranks.

## Decisions / handbacks

- User instruction for this pass: make sure all PRs are merged and deployments complete by morning.
- Current answer: none of the five open PRs is mergeable under repo gates, and production deployment cannot complete until #435's SSH reachability blocker is fixed.
- Overnight PR queue heartbeat was updated to watch every 30 minutes, report only material changes, and avoid rerunning deploy while the SSH path is still blocked.
