# Engineering skills and capability routing

This document defines the capabilities required to work safely in the Virtual
Casino Simulator repository. It is vendor-neutral: humans, Claude, Codex, and
other approved automation use the same repository policy and acceptance gates.
Tool names differ; responsibilities do not.

## Capability selection rule

Choose the smallest capability set that covers the assigned issue. Read the
complete instructions for every selected capability before acting. A capability
does not broaden scope or authority; it only describes how to perform an already
authorized action safely.

If a required capability is unavailable, continue with a safe read-only
alternative or report the blocker. Do not invent access, bypass a gate, expose a
secret, or substitute an ungoverned tool.

## Required baseline capabilities

| Capability | Required use | Completion evidence |
| --- | --- | --- |
| Policy and instruction discovery | Locate and read root/nested `AGENTS.md`, the handbook, module manifests, requirements, contracts, and issue instructions before editing. | Required-reading list in the task packet or PR. |
| GitHub issue and PR management | Read issues/comments/PRs, preserve decisions, create durable scope, and publish reviewable handbacks. | Linked issue and PR with exact state. |
| Git and worktree safety | Inspect status, preserve dirty state, isolate branches, stage only owned files, and avoid destructive operations. | Branch, commit, base, and clean scoped diff. |
| Repository search and code reading | Use fast indexed search and targeted file inspection before assumptions or edits. | Root-cause or design evidence tied to files. |
| Language-aware implementation | Follow Python, JavaScript, JSON, CSS, HTML, YAML, OpenAPI, and comment rules for touched files. | Focused diff and validators. |
| Requirement and version traceability | Map behavior to permanent IDs and bump every changed module without changing packaged release accidentally. | Requirement and version sections in the PR. |
| Validation and evidence | Run focused and required checks, sanitize results, and distinguish test evidence from authority. | Exact commands, results, commit, and cleanup. |
| Coordinator handback | Report outcome, remaining risks, dependencies, decisions, and next authorized step without relying on chat history. | Terminal PR or blocked handback. |

## Specialized capabilities

### GitHub review and publication

Use a connector, GitHub CLI, or reviewed human workflow that can read issue/PR
metadata, comments, diffs, reviews, checks, and branch state. Publication must
support scoped staging, intentional commits, branch pushes, and draft PR creation.
Never infer merge approval from green checks or a reaction. Claude's GitHub
capability ends at PR composition and revision. Codex alone performs merges
after verifying every applicable approval and acceptance gate.

### Browser control and visual inspection

Browser-visible work requires real-browser navigation, semantic interaction,
viewport/locale control, console/network/page-error capture, screenshots, and
human visual inspection. Headless automation alone is insufficient for clipping,
motion, hit-target, readability, or hierarchy claims. Follow the visual standard
and matrix.

### API and contract engineering

Endpoint work requires OpenAPI and compatibility inspection, request/response
envelope validation, hostile-input testing, and frozen-v1 analysis. Use the
repository validators; do not rely on a client stub or one happy-path call.

### Game, wallet, and retry engineering

Gameplay work requires rules/engine knowledge, ledger inspection, deterministic
settlement tests, session-bound player verification, idempotent retry behavior,
and public-action browser/API coverage. Money safety is an invariant, not a UI
detail.

### Load, soak, and concurrency testing

Qualification work requires disposable users and state, deterministic workload
accounting, bounded concurrency, per-control coverage, latency/error collection,
wallet/ledger invariants, and exact cleanup. UI qualifications must actually use
rendered UI controls.

### Security and privacy review

Auth, Admin, proxy, CSRF, cookies, logs, secrets, and exposure work requires
threat-boundary analysis, fail-closed behavior, sanitized diagnostics, hostile
tests, and least-privilege evidence. Credential managers are used through their
supported injection/autofill interfaces; secrets are not copied into source,
logs, screenshots, issues, or chat.

### Storage, migration, and recovery

Storage work requires provider-parity analysis, transactional/concurrency
semantics, explicit migration catalogs, DDL-free runtime checks, disposable
targets, encrypted recovery, and rollback compatibility. Live targets and data
need separate authorization.

### Release and deployment

Release work requires deterministic artifacts, checksums, dependency manifests,
exact provenance, clean-copy smoke, predecessor mapping, recovery compatibility,
and publication gates. Deployment adds target-specific readiness, monitoring,
rollback, access, and live verification authority.

### Documentation generation and indexing

Documentation work requires source-authority classification, stable links,
generated-artifact discipline, historical/current separation, Markdown index
regeneration, requirements/version mapping, and the docs validation command.

## Tool adapters

### Codex

Use the installed repository-relevant skill package when one exists, such as
GitHub management/publication or in-app browser control. Read its complete
instructions before action. Prefer purpose-built connectors for semantic state
and local Git for branch/worktree operations. Skill instructions remain
subordinate to repository scope, safety, and owner authority.

Codex is the default coordinator, shared-file integrator, independent PR
reviewer, and sole merge executor. Before merging, Codex must inspect the exact
head, validate dependencies and shared metadata, confirm checks and required
acceptance evidence, and verify that every owner approval is recorded. Sole
merge execution does not authorize unchecked self-approval or bypassing gates.

### Claude

Use Claude Code's repository, GitHub, shell, and browser capabilities as
available. Claude must read the same root/nested instructions, issues, manifests,
contracts, requirements, and specialized policies. Claude-authored issue or PR
comments must identify that they were written by an AI assistant when repository
or owner policy requires provenance.

Claude may create and update assigned branches and PRs, run tests, attach
evidence, and respond to review feedback. Claude must not merge, enable
auto-merge, push a protected branch, retarget or close a handed-back PR without
coordination, or treat checks as acceptance. Its terminal action is a complete
PR or blocked handback to Codex.

### Humans and other automation

Humans may perform investigation, implementation, review, approval, release, and
operational capabilities through authorized local or GitHub workflows. Under the
current owner direction, Codex still executes the repository merge. Other
automation is acceptable only when it produces the same durable inputs, respects
the same authority boundaries, emits equivalent reviewable evidence, and stops
before merge unless the owner changes the merge-executor policy.

## Coordination between tools

Multiple tools may work concurrently only with explicit file ownership. The
coordinator records issue, branch, owned files, no-touch files, dependency, and
expected handback for each worker. Agents consume GitHub state and committed task
packets, not each other's private memory.

For the default two-agent model, Codex allocates and integrates while Claude
authors bounded PRs. `docs/claude_codex_work_division.md` defines the allocation
matrix, capacity limit, PR lifecycle, merge gates, and handback formats.

When one worker has an open PR owning a shared file, the next worker either waits
or creates a documented stacked branch. It does not create a competing version
bump, requirement allocation, generated artifact, or integration PR.

## Stop conditions

Stop before mutation and report the exact blocker when:

- scope or authority is missing;
- an active worker owns the required file;
- the base commit, requirement ID, or module version is ambiguous;
- a frozen API may break;
- a test would touch user, live, production, provider, or real data;
- a secret or private identifier would be exposed;
- deployment, public exposure, paid, destructive, DNS, mail, or provider action
  lacks explicit approval; or
- required evidence cannot be produced honestly.
