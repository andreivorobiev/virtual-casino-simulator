# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-08-13.

## Pull requests I authored (drafts; I never merge)

None in flight. The 2026-08-07 account/enrollment/product-admin omnibus is fully landed (`claude/account-admin-omnibus` tip `c8f78c73` is an ancestor of main via #638 and the follow-on integrations); that row is retired.

## Active work — owner audit execution program (2026-08-13)

The owner commissioned a full repository audit (unmerged PRs, all 302 closed issues verified claim-vs-code, fix/refactor review, architecture, pipeline) and approved the resulting execution program. Everything is filed as tickets for Codex — Claude authored the tickets and is deliberately NOT opening implementation PRs for them, to keep the highest-collision files (tests/run_tests.py, deploy lanes) single-author.

- **Program tickets:** #697 (login redesign — has three open owner questions; ask before building), #698-#722 (audit findings; #698 P1 wallet corruption, #732 P1 deploy), #723 (issue-PR linking rule + enforcement workflow), #727-#730 (owner-approved monolith split series: run_tests.py, storage package, admin.js, app.js), #731 (file-length standard + register), #732 (P1: pull-based production deploy on the prod host; the dead SSH leg retires; owner executes the host install step from the runbook).
- **Sequencing and hard boundaries** are in the owner's program prompt; the load-bearing ones: #727 slices must prove case-inventory equality per slice and keep the shard-union verification intact; no contracts/ schema changes except the additive-v2 admin surface in #701; required status contexts keep their exact names; #723's linking rule applies to every closure in this program.
- Observed 2026-08-13: #698 already fixed and merged (#725), #699 in draft (#726) — thank you for the fast pickup.
- Owner decision: the dedicated-VM idea is shelved; #732 needs no VM. #450 stays closed as a documented alternative.

## File claims / high collision risk

- None held by Claude. The five audited comment-quality files, keno/baccarat engines, and guest limiter from the #555 program are all on main; Claude claims nothing while the split series (#727-#730) is in flight.

## Questions / requests for Codex

- When any reconciliation touches `tests/run_tests.py` or shared governance files, please diff the contributor's final head against post-merge main for the owned files — the two historical content drops both happened there (#573 restore, #574 restore).

## Blockers I am waiting on (owner or Codex)

- #732 host-install step waits on the runbook handback; the owner runs it.
