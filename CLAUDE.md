# Claude repository adapter

This file makes the repository operating model discoverable to Claude Code. It
does not create a Claude-specific source of truth or relax any repository rule.
Claude must follow the same issue, requirement, module, contract, validation,
evidence, security, and safety gates as every other contributor.

## Mandatory start

Before changing repository or GitHub state, Claude must read:

1. `CODEX_START_HERE.md`;
2. root `AGENTS.md` and every closest nested `AGENTS.md` for files in scope;
3. `ENGINEERING_PRACTICES.md`;
4. `docs/engineering_skills.md`;
5. `docs/claude_codex_work_division.md`;
6. the assigned GitHub issue, recent comments, dependency PRs, and task packet;
7. affected requirements, module manifests, contracts, and specialized policy;
8. the pull-request template and the issue's required validation plan.

When sources conflict, Claude stops before mutation and records the conflict in
the assigned GitHub issue. Chat context and model memory are not authority.

## Claude role boundary

Claude may investigate assigned scope, implement on its assigned branch, add
tests and documentation, run validation, and create or update a pull request.
Claude may respond to review feedback by updating that same branch and PR.

Claude must not:

- merge, squash-merge, rebase-merge, enable auto-merge, or bypass a merge queue;
- push directly to `main` or another protected/integration branch;
- mark a dependency accepted merely because checks are green;
- retarget, close, replace, or force-update a handed-back PR without Codex
  coordination; or
- claim deployment, release, acceptance, or issue completion beyond its evidence.

Codex is the sole merge executor for this repository. That role identifies who
performs the merge; it does not replace required owner approval, independent
review, protected-branch rules, exact-head checks, release gates, or deployment
authorization.

## Required PR handback

Claude's terminal handback must include:

- issue and task packet;
- branch, base, dependency PRs, and exact head commit;
- owned files and honored no-touch files;
- requirements and module-version changes;
- commands run and exact results;
- evidence and cleanup status;
- unresolved risks, decisions, and follow-up issues; and
- a direct request for Codex review, integration, and merge when eligible.

The handback is complete when the PR is reviewable or honestly blocked. It is
not complete merely because the PR exists.
