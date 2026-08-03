# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-08-03.

## Pull requests I authored (drafts; I never merge)

| PR | Branch | What it is | State |
|---|---|---|---|
| #574 | `claude/restore-guest-window-proof` | Restore the per-source guest-creation window proof that the #568 shell resolution dropped from `tests/run_tests.py` (GUEST-001 ↔ API-GUEST-LIFECYCLE-001 alignment) | open draft, ready for review |

## Recently disposed

- Reviewer-readiness program (#555, all six tasks): #558 merged; #559/#561/#562/#564 closed after their content was integrated via #563, #566, and #568 and released through v0.9.5.50. Post-merge verification on 2026-08-03 confirmed every deliverable present on `main` at v0.9.5.51 with one exception — the guest-window proof — restored by #574 above. #555 stays open for the owner to close after the external review.
- #557 (wallet add-tokens #247 guard races behind `refreshShellState`) remains open; the two-line reorder offer stands.
- Older drafts: #454, #460, #481, #518 merged; #506 closed (admin RTP view disposed by Codex).

## File claims / high collision risk

- #574 owns one block in `tests/run_tests.py` `validate_guest_lifecycle`, `modules/tests.json` (1.67.4), `modules/module-manifest.json`, the tests pin line in `tests/unit/request_latency_benchmark_tests.py`, and regenerated docs. Nothing else claimed.

## Questions / requests for Codex

- When resolving `tests/run_tests.py` in future shell reconciles, the guest-window block sits between the action-cap and capacity proofs inside `validate_guest_lifecycle`; it belongs to GUEST-001's mapped case.

## Blockers I am waiting on (owner or Codex)

- None.
