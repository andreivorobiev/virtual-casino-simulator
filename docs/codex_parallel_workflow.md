# Parallel Codex Workflow

This workflow lets multiple Codex chats work on the Virtual Casino Simulator without losing requirements, module boundaries, or task context.

## Source of truth

Do not treat chat history as the source of truth. Use these durable records instead:

- GitHub issues for requested work, scope, acceptance criteria, and open questions.
- `docs/requirements/requirements.json` for permanent requirement IDs.
- `modules/*.json` for module ownership and version numbers.
- `contracts/` for API compatibility rules.
- `codex/tasks/*.md` task packets for worker handoffs.
- Pull requests for reviewable implementation history and validation evidence.

## Version ownership

Use `modules/module-manifest.json` as the canonical aggregate version source. Its top-level `application` value is the packaged application release and changes only when a formal application release artifact is produced. The entries under `modules` are independent source-module revisions and may advance between packaged releases; `modules.application` is an application module revision, not the packaged release.

Workers must bump each directly affected module revision in both the aggregate manifest and its matching `modules/<name>.json` file. Ordinary feature and corrective PRs should report packaged-release impact as `None` unless the coordinator explicitly assigns release-artifact work. Runtime, API, browser, Admin, README, and starter-document release displays must stay aligned with the top-level packaged release.

## Chat roles

Use one long-lived coordinator chat and many bounded worker chats.

The coordinator chat owns:

- Turning user goals into GitHub issues or task packets.
- Assigning one branch and one file ownership list per worker.
- Preventing two chats from editing the same file at the same time.
- Sequencing stacked work when the same file must change twice.
- Reviewing PR summaries for requirement IDs, module versions, tests, and contract impact.

Each worker chat owns:

- One issue or task packet.
- One branch.
- One module-focused change unless the packet explicitly lists more.
- The tests and validation named in its packet.
- A PR handback with evidence and unresolved questions.

## Starting a worker chat

Create or update a task packet before starting a worker. Use `codex/tasks/TASK_PACKET_TEMPLATE.md` and include:

- Goal and non-goals.
- Requirement IDs.
- Impacted modules.
- Owned files.
- Files the worker must not touch.
- API, gameplay, ledger, bot, and autoplay impact.
- Required validation.
- Expected branch and PR title.

Paste the packet into the new chat along with:

- "Read `AGENTS.md`, the relevant nested `AGENTS.md`, and module manifests first."
- "Do not rely on prior chat context."
- "Stop and ask before expanding beyond the owned files."

## Working on one game from many chats

Parallel work on one game is allowed only when ownership is split by layer.

Game expansion workers must also follow [`game_catalog_governance.md`](game_catalog_governance.md). Each isolated game owns its `modules/<game-id>.json` descriptor and `tests/game_drivers/<game-id>.py` driver; shared registration, shell, validator, and long-suite allowlists must not be reintroduced.

Good splits:

- Engine and settlement rules: `casino/games/<game>/`.
- API route or schema work: game API files plus `contracts/`.
- Frontend view: `web/games/<game>.js` and related `web/core/` helpers.
- Tests only: `tests/` files for the game.
- Documentation only: `docs/` and task packet updates.

Avoid simultaneous edits to the same file. If two changes require the same file, stack them:

1. Worker A opens a PR against the base branch.
2. Worker B branches from Worker A's branch.
3. Worker B states the dependency in the PR.
4. Merge Worker A first, then rebase or retarget Worker B.

## Branches and PRs

Use short, explicit branch names:

- `agent/<module>-<task>`
- `agent/<game>-engine-<task>`
- `agent/<game>-ui-<task>`
- `agent/<game>-tests-<task>`
- `docs/<workflow-or-release-task>`

Every PR must include:

- Requirement IDs added, changed, or validated.
- Impacted modules.
- Packaged application release impact.
- Independent module revision bumps.
- API contract impact.
- Gameplay impact.
- Tests and validations run.
- Task packet link or issue link.
- Parallel work dependencies, if any.

## Conflict rules

The coordinator should pause new workers when:

- A worker needs a file already owned by another active worker.
- A requirement ID is missing or ambiguous.
- A module version bump conflicts with another active PR.
- A proposed API change could break `/api/v1`.
- Gameplay behavior changes without explicit scope.

When in doubt, make the packet smaller and split the work into a follow-up issue.

## Validation ladder

Workers should run the smallest relevant checks while developing, then the PR should finish with the required subset from `AGENTS.md`.

Documentation or tooling-only changes normally require:

```bash
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/check_comment_density.py
```

Game, API, ledger, bot, or autoplay changes require the module-relevant API/browser/contract checks named in the task packet.
