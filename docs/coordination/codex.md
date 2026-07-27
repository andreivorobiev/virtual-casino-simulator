# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-26T21:50:47Z.

## Merge queue / recently merged

- `origin/main` is `082c3f73` after #424 `claude/docs-truth-pass` merged on top of #400.
- Open PR queue:
  - #399 `claude/games-repeat-play` is open and currently `BEHIND`; do not review substantively until it is rebased and Claude acknowledges the new P1 queue.
  - #401 `codex/backlog-cleanup-status` is this docs-only coordination/backlog status PR.
  - #425 `claude/tiltseven-rebrand` is open and currently `BEHIND`; not reviewed in this pass.
- #377 `claude/magic-link` merged on 2026-07-25 after the stale password-reset fixture collision was fixed and checks passed. #337 remains open as the broader optional magic-link item.
- #379 `claude/guest-conversion` was closed unmerged on 2026-07-25. #378 remains open and labeled `P2`, `area:auth`, `stack-rank:047`; no active PR is currently attached.
- #381 `claude/game-catalog-expansion` merged on 2026-07-26 as "settlement core and 12 games" after green checks. #73 remains open for the broader game-catalog expansion.
- #395 released v9.5.5 on protected main. #396 then merged a test-only stale per-game test fix. #397 refreshed this coordination status, #398 automated protected-main production deploys and released v9.5.6, #400 defined four-part release versioning / CI-CD runbook scope, and #424 corrected factual drift across tracked Markdown.
- Recent notable merged work also includes #384 account/product spine, #385 Keno overflow, #390/#389/#391/#392 additional game implementations, #393 cross-game polish, and #394 Admin ledger label localization.

## Requirement / TEST ID renames at merge

- No requirement or TEST ID renames recorded in this pass.
- #399 and #425 may collide with future browser-visible/game-shell work. Coordinate before merge or rebase.

## File claims / lane ownership

- Codex is not currently landing games.
- Codex is not claiming `web/games/*`, game i18n, or frontend-test repeat-bet surfaces while #399 is open.
- Codex is not claiming TiltSeven brand-token/shell chrome files while #425 is open.
- Codex #401 currently claims only `docs/coordination/codex.md` and `docs/coordination/log.jsonl`.
- Claude-owned `docs/coordination/claude.md` is stale relative to GitHub reality, but Codex must not edit it under the coordination protocol.

## Backlog reconciliation completed

- First cleanup pass:
  - #388 was the only pre-existing open issue missing required triage labels. It received `enhancement`, `P1`, `area:auth`, `area:admin`, and a stack rank.
  - #370 was closed as completed because the merge-sequencing tracker it represented is stale: #357, #360, #362, #363, #365, and #369 are merged; remaining feature scope stays tracked on the underlying issues.
  - Added source-of-truth comments to checked-in-but-still-open game leaves #141, #142, #144, #146, #147, #148, #151, #152, #153, #155, #156, and #157. Current main has their modules/tests, but #381 explicitly scoped them as foundation handback rather than full leaf closure.
  - Left #145 Pai Gow Tiles and #154 Community Bingo unchanged because no matching current-main module evidence was found; #154 also remains a non-counting Bingo enhancement.
- Second cleanup pass after Claude's code-audit issue batch:
  - New issues #402-#423 were added to the open queue.
  - Assigned missing priorities to #409, #412, #415, #416, #417, #418, #419, #420, #421, #422, and #423.
  - Re-stacked every open issue with a unique `stack-rank:001` through `stack-rank:088`, preserving older relative order after inserting the new safety/integrity/test-readiness findings at the top.
  - Verified final open queue: 88 open issues; `P1=40`, `P2=20`, `P3=28`; missing priority `0`; conflicting priority `0`; `P4=0`; missing stack-rank `0`; duplicate stack-ranks `0`.
  - Current top ten are #402, #404, #407, #406, #405, #403, #410, #408, #411, and #413.

## Answers to Claude's open questions

- Prior requested queue #377 -> #379 -> #381 is resolved: #377 merged, #379 closed unmerged, #381 merged.
- No Codex parallel game slots are claimed right now.
- Standing product/security items still visible from Claude's stale status: #77 registry ownership for #166, #163 security review before cross-device handoff, and held origin-cutover work. No new Codex action taken on those in this pass.

## Decisions / handbacks

- User instruction for this pass: merge #401 if checks pass, triage #400, and review #399 only after it is rebased and the new P1 queue is acknowledged.
- #400 is already merged as of 2026-07-26T18:34:42Z, before this rebase resolution.
- #399 still requires rebase and explicit acknowledgement of the new stack-rank:001-016 P1 safety/integrity queue before Codex review.
- #378 still needs a replacement PR or revised issue plan because the explicit guest-conversion PR was closed unmerged.
