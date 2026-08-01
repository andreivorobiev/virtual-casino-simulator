# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-07-31.

## Pull requests I authored (drafts; I never merge)

States follow `docs/coordination/codex.md`; the reviewer-readiness stack is serialized behind the current controller reconciliation.

| PR | Branch | What it is | State |
|---|---|---|---|
| #558 | `claude/readme-front-door` | Program task 1: README design decisions, release-note status archive, and token-terminology CI repair (#555) | open draft; immutable contributor preserved at `ed82cd35`; controller reconciliation in progress |
| #559 | `claude/arch-diagram` | Program task 2: bounded architecture request-path diagram | open draft; stacked on #558 and held for current-main reconciliation |
| #561 | `claude/guest-endpoint-hardening` | Program task 4: bounded guest-trial endpoint hardening | open draft; stacked on #559 and held for current-main reconciliation |
| #518 | `identity-admin-redesign` | Identity/Admin redesign: session timeouts, nested console, and Sessions page | open draft; held behind the serialized reviewer-readiness and release lanes |

## Active work — reviewer-readiness program (owner-directed, 2026-07-31)

The owner requested a bounded polish-and-hardening pass before an external technical review. Each task remains independently reviewed and serialized; no task closes umbrella issue #555 by itself.

1. `claude/readme-front-door` — move the README's per-release status paragraph verbatim into a dated `RELEASE_NOTES.md` archive, replace it with six durable design decisions, and repair plus wire the play-token terminology validator.
2. `claude/arch-diagram` — add one bounded request-path architecture diagram; held until task 1 reaches its own terminal release.
3. Featured-game smoke pass — completed without a product fix; the separate wallet add-token observation was tracked independently.
4. `claude/guest-endpoint-hardening` — add the bounded guest-trial protection described by its own task; held with the external stack untouched.
5. Legacy settlement migration — not part of task 1 and not started by this controller.
6. Comment-quality cleanup — not part of task 1 and not started by this controller.

## File claims / high collision risk

- Task 1 is being reconciled from terminal v0.9.5.47 through controller branch `codex/558-readme-front-door-controller` with ancestry shell `93035ae1`; the immutable contributor remains reachable as the second shell parent.
- The task-1 ceiling is exactly the README/release notes, comment-density workflow, token validator and its focused fixture, four owned module descriptors plus the aggregate manifest, generated requirements, and two coordination records. It claims no requirement source, contract, casino runtime, web runtime, game source, API, or Browser case.
- Compatible task-1 allocations are application `9.56.2`, tests `1.66.2`, docs `1.64.62`, and tooling `1.24.1`; packaged application `0.9.5.47` and every unrelated module remain unchanged.
- PRs #559 and #561 stay at their immutable stacked heads and must regenerate shared metadata from the future current main rather than lending stale hunks to task 1.

## Questions / requests for Codex

- Keep tasks 2 and 4 held until task 1 receives its unique terminal release and deployment disposition.

## Blockers I am waiting on (owner or Codex)

- Task 1 is awaiting independent mutable review after its current-main browser-free validation packet.
