# Parallel agent workflow

This workflow lets humans, Claude, Codex, and other approved workers collaborate
without losing requirements, module boundaries, or task context. The legacy
filename is retained for stable links.

## Source of truth

Do not treat chat history or model memory as source of truth. Use:

- GitHub issues for requested work, scope, acceptance criteria, dependencies,
  safety boundaries, and open questions;
- `docs/requirements/requirements.json` for permanent requirement IDs;
- `modules/*.json` for module ownership and versions;
- `contracts/` for API compatibility rules;
- `codex/tasks/*.md` task packets for durable worker handoffs; and
- pull requests for reviewable implementation history, checks, and evidence.

All workers follow `ENGINEERING_PRACTICES.md` and
`docs/engineering_skills.md`. Tool-specific convenience never changes authority
or the definition of done.

## Version ownership

Use `modules/module-manifest.json` as the canonical aggregate version source. Its
top-level `application` value is the packaged application release and changes
only when a formal application release artifact is produced. Entries under
`modules` are independent source-module revisions and may advance between
packaged releases; `modules.application` is an application module revision, not
the packaged release.

Workers bump each directly affected module revision in both the aggregate
manifest and `modules/<name>.json`. Ordinary feature and corrective PRs report
packaged-release impact as `None` unless the coordinator explicitly assigns
release-artifact work. Do not allocate a version already owned by an open PR.

## Roles

Use one long-lived coordinator and bounded worker tasks.

The coordinator owns:

- turning user goals into GitHub issues or task packets;
- assigning one branch and one file ownership list per worker;
- preventing simultaneous edits to the same file;
- sequencing stacked work when the same file must change twice;
- consuming handbacks and releasing only the next approved dependency; and
- reviewing PR summaries for requirement IDs, module versions, tests, evidence,
  contracts, and residual decisions.

Each worker owns:

- one issue or task packet;
- one branch;
- one explicit file set and no-touch boundary;
- one module-focused change unless the packet explicitly lists more;
- the tests and validation named in its packet; and
- a terminal PR or blocked handback with exact evidence.

## Starting a worker

Create or update a task packet from `codex/tasks/TASK_PACKET_TEMPLATE.md` before
starting. Include:

- goal, non-goals, and user-visible outcome;
- requirement IDs and impacted modules;
- packaged-release impact and expected module bumps;
- owned, no-touch, and allowed-adjacent files;
- API, gameplay, ledger, bot/autoplay, data, security, and deployment impact;
- required reading, validation, visual rows, evidence, and cleanup; and
- branch, PR title, dependencies, handback, and stop conditions.

The worker must read root and nested instructions, current GitHub state, module
manifests, requirements, contracts, and specialized policies itself. Do not ask
another agent to summarize instructions that the worker is required to follow.

## Parallel ownership

Parallel work is allowed only when file ownership is disjoint. Good layer splits
include engine/service, API/contracts, frontend, tests, and documentation. Shared
registration, manifests, requirements, generated docs, compatibility artifacts,
visual matrices, and release metadata normally have one integration owner.

When two changes require the same file, stack them:

1. Worker A opens a PR against the accepted base.
2. Worker B branches from Worker A's exact accepted or coordinator-approved head.
3. Worker B records the dependency and targets the predecessor branch when
   appropriate.
4. Worker A merges first.
5. Worker B rebases or retargets, recalculates shared versions/generated files,
   reruns validation, and then requests review.

Do not open competing PRs, copy commits manually between dirty worktrees, or
force-update another worker's branch. Preserve active worktrees and user runtime
data.

## Game work

Game expansion follows `docs/game_catalog_governance.md`. Each isolated game owns
its module descriptor, backend package, frontend module, locale domain, contract,
focused tests, long driver, and evidence. Shared catalog and integration files
belong to the serialized integration owner.

Avoid simultaneous edits to the same game file. If a game is split by layer,
every worker still names its shared behavioral requirements and integration
dependency.

## Branches and PRs

Use short explicit branch names consistent with `CONTRIBUTING.md`. Every PR
includes:

- issue and task packet;
- base branch and parallel/stacked dependencies;
- owned and honored no-touch files;
- requirements added, changed, and validated;
- impacted modules and independent version bumps;
- packaged application release impact;
- API, gameplay, ledger, data, security, and deployment impact;
- tests, validators, visual rows, evidence, and cleanup; and
- unresolved risks and owner decisions.

Green checks do not authorize merge. The coordinator consumes the handback and
applies the repository's review and release gates.

## Pause and conflict rules

Pause a worker when:

- another active worker owns a required file;
- a requirement ID or module version is missing, reserved, or ambiguous;
- the base or open-PR dependency changed;
- a proposed API change could break `/api/v1`;
- gameplay, ledger, security, deployment, or data scope expands without authority;
  or
- required tests or evidence would touch user, live, provider, or production
  state.

When in doubt, reduce scope, create a linked follow-up issue, or request an owner
decision. Do not solve coordination ambiguity through an unreviewed mutation.

## Validation ladder

Run the smallest relevant checks during development and the issue's complete
required subset before handoff. Documentation/tooling-only changes normally run:

```bash
python scripts/generate_docs.py --check
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/validate_module_boundaries.py
python scripts/check_comment_density.py
```

Game, API, ledger, auth, storage, UI, security, release, or operational changes
add the specialized API, browser, contract, catalog, long, visual, recovery, and
deployment checks named by their task packet and policies.
