# Engineering practices

This is the vendor-neutral engineering policy for the Virtual Casino Simulator.
It applies equally to human contributors, Claude, Codex, and any other approved
automation. A tool may provide a convenient workflow, but no tool or vendor has
a separate source of truth or a different quality bar.

Issue #267 owns this consolidation. Specialized policies linked below remain
authoritative for their domains; this handbook provides the common operating
model and resolves where contributors must look before acting.

## Policy hierarchy and conflict resolution

Use the most specific durable instruction that applies, in this order:

1. Current explicit owner direction recorded in the relevant GitHub issue or
   approval record.
2. Root `AGENTS.md` and the closest nested `AGENTS.md` for the files in scope.
3. This handbook and the specialized policy documents it identifies.
4. Permanent requirements, module manifests, API contracts, compatibility
   artifacts, visual matrices, and release manifests.
5. The assigned issue, task packet, branch, and pull-request acceptance record.

Chat history, model memory, generated summaries, old task packets, screenshots,
and historical release snapshots are context, not current authority. When two
durable sources conflict, stop before mutation, identify both sources, and ask
the coordinator or owner to resolve the conflict in GitHub.

The complete Markdown catalog is generated in `CODEX_START_HERE.md`. Historical
release documents and completed evidence remain indexed for traceability but do
not override current policies.

## Durable sources of truth

- GitHub issues define requested scope, dependencies, ownership, acceptance
  criteria, safety boundaries, and decisions.
- Pull requests define the reviewable change, exact commit, checks, evidence,
  and merge history.
- `docs/requirements/requirements.json` owns permanent requirement IDs and their
  validation mappings.
- `modules/module-manifest.json` and `modules/*.json` own packaged-release
  context, source-module revisions, paths, dependencies, and module boundaries.
- `contracts/openapi/` and `contracts/compatibility/` own API and compatibility
  promises.
- `tests/visual/visual_matrix.json` and `docs/visual_design_standard.md` own
  browser-visible acceptance coverage.
- Release manifests, checksums, provenance, recovery evidence, and deployment
  receipts own release and operational claims.

Open pull requests are pending proposals, not accepted current state. Read every
open PR that overlaps the assigned files before branching. Stack work when an
active PR owns a shared file; do not silently duplicate or overwrite it. Draft
PR numbers, exact heads, and dependency order belong in their durable issue and
PR records so this handbook does not turn transient queue state into policy.

## Authorization and safety boundary

An engineering task authorizes only the changes needed for its stated scope.
Priority, green checks, a deadline, a reaction, or an AI recommendation does not
authorize merge, deployment, public exposure, paid services, destructive work,
provider changes, DNS, mail, credentials, production data, or security-sensitive
mutations.

Prefer reversible, local, and read-only investigation. Preserve dirty worktrees,
active runtimes, user data, credentials, evidence, and another worker's branch.
Never expose secrets, tokens, cookies, private paths, addresses, provider IDs,
raw logs, personal data, or credential-manager contents in issues, PRs, evidence,
tool output, or chat.

The simulator remains fake-money only. Follow `CONTRIBUTING.md` and the legal
documents under `docs/legal/`; never introduce real-money, redemption, purchase,
cash-out, transferable-value, or public-gambling behavior or language.

## Issue intake, triage, and decisions

Every implementation or documentation lane needs a durable GitHub issue before
source work begins. The issue must state scope, non-goals, owner, dependencies,
acceptance criteria, safety boundaries, and expected evidence.

`docs/issue_prioritization.md` is authoritative for priority and label taxonomy.
Every open issue has exactly one of `P1`, `P2`, or `P3`; `P4` is not used.
Priority controls sequencing, not authority. Severity, blocked state, category,
area, and origin are separate labels.

Materially new findings become linked issues instead of hidden scope expansion.
Do not close an issue merely because a narrow test passed. Close only after its
acceptance criteria and required handback are satisfied or after an explicit
documented disposition.

## Coordination and parallel work

Use one coordinator and bounded workers as described in
`docs/codex_parallel_workflow.md` (the legacy filename applies to every agent).
The coordinator owns allocation, collision prevention, acceptance sequencing,
and handback consumption. Each worker owns one issue, one branch, one explicit
file set, and one terminal PR or blocked handback.

The default Claude/Codex allocation is defined in
`docs/claude_codex_work_division.md`. Claude composes assigned PRs and may revise
them after review, but it never merges or enables auto-merge. Codex owns
coordination, shared integration, independent review, dependency sequencing, and
every repository merge. Codex's sole-merge role identifies the executor; it does
not replace owner authorization, required review, protected-branch rules,
exact-head checks, release gates, or deployment approval.

Before editing:

1. Inspect open PRs, branches, worktrees, and recently changed issues.
2. Read the issue and every applicable instruction, manifest, contract, and
   requirement.
3. Confirm owned and no-touch files in a task packet based on
   `codex/tasks/TASK_PACKET_TEMPLATE.md`.
4. Stop when an active worker owns the same file; stack, rebase, or wait through
   the coordinator rather than racing.

Do not create duplicate workers, issues, branches, or PRs for the same released
scope. Do not interrupt a genuinely active worker merely because a status check
occurred. A handback must name the exact commit, tests, evidence, residual risks,
and next authorized action.

## Required capabilities and skill routing

`docs/engineering_skills.md` defines the capabilities required for repository
work and how humans, Claude, Codex, and automation satisfy them. Contributors
must select the smallest applicable capability set, read its complete local
instructions, and remain within the issue boundary.

At minimum, every contributor needs policy discovery, GitHub issue/PR handling,
Git/worktree safety, repository search, language-aware implementation, validation,
and evidence handback skills. UI work additionally requires real-browser control
and visual inspection. API work requires contract validation. Release, security,
storage, migration, recovery, and deployment work require their specialized
policy and evidence capabilities.

## Branches, worktrees, commits, and pull requests

Follow `CONTRIBUTING.md`, `.github/pull_request_template.md`, and the parallel
workflow.

- Start from the current accepted base or an explicitly documented stacked PR.
- Use an isolated worktree for parallel work and preserve unrelated changes.
- Use a scoped branch name that identifies the owner and task.
- Make the smallest module-scoped diff; never stage unrelated files.
- Keep commits intentional and reviewable.
- Push through the repository remote and open a draft PR unless the owner asks
  for ready-for-review state.
- Do not push directly to `main`, force-update another worker's branch, or delete
  a branch/worktree without authority.
- Claude must stop at a complete PR handback and must not merge, squash-merge,
  rebase-merge, enable auto-merge, or bypass a merge queue.
- Codex is the only merge executor and must verify the exact head, required
  checks, reviews, dependencies, evidence, and owner approvals before merging.

Every PR reports its issue, dependencies, owned files, impacted requirements,
modules, version changes, API/gameplay/data impact, validation, evidence, release
impact, and unresolved decisions. Green checks are evidence, not merge approval.

## Module ownership and implementation discipline

Read the root and nested `AGENTS.md` files plus every affected module manifest
before editing. Respect module path ownership and dependency rules. A game may
depend on shared core services and itself, but not another game. Shared frontend
behavior belongs under `web/core/`; game views do not import other game views.

Use catalog metadata and shared discovery rather than reintroducing hard-coded
game allowlists. `docs/game_catalog_governance.md` is authoritative for isolated
games and `docs/game_expansion_integration_sequence.md` records the serialized
shared-file integration model.

### Source file-length review tripwire

Hand-written first-party Python and JavaScript that exceeds 1,200 physical lines
or 96 KiB requires an explicit split-or-justify decision. The canonical audit is
the path-specific row in `docs/file_length_register.json`; each row records the
reviewed line count, one-paragraph reason to remain whole, named reviewer, review
date, and revisit date. A row is not a permanent exemption: growth greater than
20 percent forces a new review, and a file that returns below both thresholds
must remove its stale row in the same change.

`scripts/validate_file_length.py` scans Git-tracked `.py` and `.js` files, skips
repository data, vendored code, and explicitly marked generated sources, and
runs inside the existing Module Boundary required context. New source and split
series must keep the register current instead of weakening or bypassing the
validator. The four original monolith exceptions for #727 through #730 retired
when their source paths dropped below threshold; successor owners are reviewed
on their own current paths and rationale.

Python and JavaScript follow `docs/commenting_policy.md`: every meaningful
executable line has an inline or immediately adjacent purpose comment. Other
formats use clear section comments where legal. Generated artifacts must be
updated through their generator, not hand-edited in isolation.

## Requirements and traceability

Requirement IDs are permanent and never reused or deleted. Mark obsolete
requirements superseded or retired. Read the relevant IDs before editing and
record added, changed, and validated IDs in the issue and PR.

Browser-visible behavior needs browser-test mappings. API behavior needs API and
contract mappings. Money, security, storage, release, and operational behavior
needs focused invariant and recovery evidence. Run
`python scripts/validate_requirements.py` after requirement changes and
`python scripts/generate_docs.py --check` after generated documentation changes.

## Versioning, releases, and provenance

The top-level `application` value in `modules/module-manifest.json` is the
packaged application release. It changes only for a formal release artifact.
Entries under `modules` are independent source-module revisions and change when
their owned source changes. Update the matching `modules/<name>.json` and
aggregate manifest together.

Use semantic versioning: compatible fixes are patch revisions, compatible
additions are minor revisions, and breaking changes are major revisions. Do not
overwrite a version reserved by an open PR; stack on that PR or recalculate from
accepted `main`.

`docs/release_artifacts.md`, `RELEASE_NOTES.md`, `CHANGELOG.md`, and the release
workflow own formal artifact, checksum, provenance, dependency, publication,
and predecessor rules. A source-module bump does not by itself publish or deploy
a packaged release.

## API and compatibility practice

Read `docs/api_contract_freeze.md`, the relevant OpenAPI file, compatibility
artifact, and `contracts/AGENTS.md` before changing endpoints or payloads.
`/api/v1` is frozen. Only backward-compatible optional additions may remain in
v1. Breaking behavior requires `/api/v2` or an explicit reviewed compatibility
shim.

Every API response uses the standard success or error envelope. API changes
update contracts, compatibility data, tests, requirements, documentation, and
module versions together. Run contract and module-boundary validators. Client
input is intent only; `docs/server_authority_certification.md` defines the
server-authoritative player, action, outcome, and settlement boundary.

## Wallet, ledger, storage, and retry safety

All bets, tickets, cards, splits, insurance, refunds, winnings, and adjustments
move through `casino/core/ledger.py`. Game engines request settlements but never
mutate balances directly. Ledger events identify player, game, round/session,
amount, and details.

State-changing commands must preserve one stable idempotency identity across an
ambiguous retry. Exact replays return the committed result; changed-meaning
reuse fails closed. Do not treat disabling a button during flight as sufficient
retry safety.

JSON and MySQL providers must preserve the documented parity, concurrency,
persistence, and migration gates. Read `docs/local_mysql_setup.md` and
`docs/mysql_migrations.md` before storage work. Read `docs/mysql_connection_pool.md`
before changing connection acquisition, cleanup, capacity, or server concurrency. Never test against live or user
data; use disposable isolated state and verify cleanup.

## Authentication, security, privacy, and secrets

Read `docs/restricted_preview_security.md` before auth, Admin, cookie, CSRF,
proxy, header, logging, or exposure changes. Restricted preview remains manual
invite and local-password only; signup and live OAuth stay separately gated.

Security-sensitive code fails closed, emits sanitized standard envelopes, and
never reflects raw exception text or filesystem details. Tests cover hostile
input, concurrency, authorization, revocation, bounded resources, and secret-safe
logs. Credential stores are consumed through supported interfaces; secrets are
not extracted merely to make them copyable.

## Browser UI, visual quality, accessibility, and localization

Read `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
completely before browser-visible changes. Name affected surfaces, states,
locales, viewports, and gates in the PR.

UI acceptance requires real-browser behavior plus visual inspection. Controls
must remain reachable, stable, correctly mapped, keyboard accessible, readable,
and unclipped at governed viewports. Page-level horizontal overflow, hidden
essential actions, stale balances, raw keys, debug labels, and broken motion are
failures even when the DOM mounts and the console is clean. Reduced-motion,
focus order, touch targets, scrolling, and accessible names are product behavior.

Localization requires resource parity, safe fallback behavior, formatting,
text-expansion containment, script/font coverage, and bidirectional layout where
applicable. Resource-file existence is not linguistic or visual certification.
Machine-generated legal, privacy, or consent language is never called approved
without the required human review.

## Testing, qualification, and evidence

Use the narrowest focused tests while developing, then run the required
validation set from `AGENTS.md` and the issue. `docs/long_test_suites.md` defines
catalog-wide scenario profiles and isolation. Large UI, concurrency, soak, or
qualification claims must state attempted, completed, failed, skipped, per-game,
per-control, error, latency, invariant, and cleanup counts.

A passing short suite does not overrule a failing long-run or visual gate. Tests
must use the public UI/actions where the requirement says UI, real registered
routes where it says integration, and disposable isolated data. Direct API or
engine tests cannot substitute for a UI acceptance requirement.

Evidence is tied to the exact commit and environment, sanitized, classified,
and reproducible. Known-failing or before-state screenshots document defects;
they are never after-pass acceptance evidence. Every listener is loopback-only,
tracked, stopped, and verified closed without disturbing user runtimes.

## Operations, deployment, migration, and recovery

Repository implementation, release publication, deployment, cutover, and live
verification are separate gates. Read `casino/operations/README.md`,
`docs/production_service.md`, `docs/restricted_preview_edge.md`,
`docs/mysql_migrations.md`, and `docs/recovery.md` for applicable work.

Operational changes require explicit target, authority, rollback, recovery,
monitoring, readiness, and sanitized evidence. Production, provider, DNS, mail,
public exposure, spend, destructive changes, and real target/data access require
explicit owner approval. A deadline never waives security, versioning, recovery,
evidence, or rollback gates.

## Documentation governance

`CODEX_START_HERE.md` is the root Markdown catalog despite its retained legacy
filename. `ENGINEERING_PRACTICES.md` is the policy handbook. Specialized files
remain authoritative for their named domains.

Every tracked Markdown file must appear in the generated root catalog. Run
`python scripts/generate_docs.py` after adding, deleting, moving, or retitling a
Markdown file, and run `python scripts/generate_docs.py --check` before handoff.
The check rejects missing, stale, duplicate, or nonexistent catalog entries.

Historical release snapshots, old prompts, completed task packets, and evidence
records must be labeled and interpreted as historical context. Do not edit a
historical release snapshot to describe current behavior.

## Definition of done

A change is done only when:

- the issue scope and acceptance criteria are satisfied;
- applicable instructions and ownership boundaries were honored;
- requirements, contracts, compatibility data, module versions, generated docs,
  tests, and release notes align with the code;
- focused and required checks pass from the exact proposed commit;
- UI or operational evidence meets its specialized policy;
- runtimes and disposable state are cleaned up;
- the PR contains a complete sanitized handback; and
- a Claude-authored PR has been handed to Codex without merge or auto-merge; and
- no required owner decision, review, merge, deployment, or live-verification
  gate is falsely claimed as complete.
