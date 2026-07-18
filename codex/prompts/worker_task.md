# Agent worker task prompt

You are the assigned human, Claude, Codex, or approved worker for one Virtual
Casino Simulator task. The legacy path is retained for stable links.

## First actions

1. Read the full task packet provided by the coordinator.
2. Read `CODEX_START_HERE.md`, root `AGENTS.md`, and `CLAUDE.md` when using Claude.
3. Read `ENGINEERING_PRACTICES.md`, `docs/engineering_skills.md`, and `docs/claude_codex_work_division.md`.
4. Read every relevant nested `AGENTS.md`.
5. Read the impacted module manifests and requirements.
6. Read relevant contracts before touching API behavior.
7. For browser-visible work, read `docs/visual_design_standard.md` and select the affected rows in `tests/visual/visual_matrix.json`.

## Scope rules

- Work only on the issue or task packet.
- Touch only owned files unless the packet allows adjacent files.
- Do not change gameplay behavior unless the packet explicitly requests it.
- Do not edit another worker's owned files.
- Stop and ask if the requirement IDs, module bump, or API impact are unclear.
- Stop if the assigned base, file ownership, dependency PR, or required approval changed.

## Implementation rules

- Keep changes module-scoped.
- Update or add tests mapped to the requirement IDs.
- Bump module versions when module source changes.
- Preserve `/api/v1` compatibility unless the packet explicitly authorizes a versioned change.
- Include browser evidence for browser-visible behavior.
- Treat known-failing and before-state screenshots only as `before_failure`; acceptance requires matrix-labeled `after_pass` evidence.

## Handback

Open or prepare one PR with:

- Requirement IDs added, changed, or validated.
- Impacted modules.
- Version bumps.
- API contract impact.
- Gameplay impact.
- Tests and validations run.
- Screenshots or browser evidence when relevant.
- Open questions or follow-up tasks.
- Exact base, dependency PRs, and head SHA.
- Owned/no-touch files and cleanup status.
- Required owner approvals and a request for Codex review.

Do not merge, enable auto-merge, push a protected branch, or bypass a merge
queue. Claude's terminal action is a complete PR or blocked handback to Codex.
