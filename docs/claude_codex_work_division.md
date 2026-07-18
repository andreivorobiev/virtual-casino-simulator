# Claude and Codex work-division proposal

Status: proposed default operating model under issue #267. The owner-mandated
merge boundary in this document is fixed: Claude composes pull requests and
Codex performs every repository merge. Other allocation details may be tuned by
the owner without weakening repository gates.

## Objectives

- Keep implementation throughput high without duplicating branches or editing
  the same shared files concurrently.
- Give every change an independent review and integration path.
- Separate PR authorship from merge execution for Claude-authored work.
- Keep issue scope, evidence, versioning, requirements, and decisions durable in
  GitHub rather than private model context.
- Preserve one accountable merge sequence across product, documentation,
  release, and operational lanes.

## Fixed governance boundary

Claude is a PR author. It may investigate, implement, test, document, and revise
its assigned branch and PR. It may not merge, enable auto-merge, push protected
branches, or bypass a merge queue.

Codex is the coordinator, shared-integration owner, independent PR reviewer, and
sole merge executor. Codex verifies the exact proposed head, reviews scope and
evidence, resolves dependency order, and performs the merge only after every
applicable gate is satisfied.

The repository owner remains the decision authority for priorities, material
scope changes, security-sensitive actions, production, deployment, public
exposure, provider changes, spend, destructive work, DNS, mail, releases, and
any other approval required by repository policy. Codex's merge role is not
blanket approval and never converts green checks into authorization.

## Default allocation matrix

| Work type | Claude responsibility | Codex responsibility |
| --- | --- | --- |
| Bounded single-module issue | Root-cause analysis, implementation, focused tests, module docs, and draft PR. | Allocate IDs/versions/files, review exact diff and evidence, then merge when eligible. |
| UI or game defect | Implement the bounded fix and produce browser/visual evidence named by the task packet. | Confirm matrix coverage, interaction correctness, visual acceptance, regression scope, and merge. |
| API, auth, ledger, or storage change | Implement only the explicitly assigned contract and invariant scope with focused tests. | Own compatibility, security, data-integrity, cross-module review, merge sequencing, and any owner escalation. |
| Shared manifests, requirements, generated docs, catalogs, or release metadata | Edit only when the task packet explicitly assigns the shared file and exact dependency. | Default integration owner; prevent collisions, allocate versions/IDs, regenerate, and merge serially. |
| CI or review feedback on a Claude PR | Update the same branch, explain the root cause, and rerun focused validation. | Classify failures, verify the correction, require follow-up when scope expands, and merge. |
| Research, audit, or proposal | Produce a durable issue/PR-backed analysis with evidence and bounded recommendations. | Reconcile it with current authority, decide implementation packets, and merge accepted documentation. |
| Release, deployment, migration, or recovery | Prepare only explicitly assigned reversible repository artifacts and evidence. | Own integration and merge; obtain every separate publication, target, provider, or production approval. |
| P1 incident or integrity defect | Take one bounded diagnostic or implementation lane assigned by Codex. | Coordinate the incident queue, freeze collisions, verify recovery and rollback, and control merges. |

## Work intake and allocation

1. Codex reconciles open issues, PRs, checks, branches, worktrees, dependencies,
   requirements, module versions, and active ownership.
2. Codex creates or confirms one durable issue and task packet per lane.
3. The task packet names the worker, base commit, branch, owned files, no-touch
   files, assigned requirement IDs, planned module versions, required evidence,
   dependency PRs, stop conditions, and Codex as merge executor.
4. Claude acknowledges the exact packet before mutation and stops if its base or
   ownership has changed.
5. Shared integration is serialized. Disjoint module work may proceed in
   parallel, but no two active PRs own the same shared metadata.

Default capacity is one active shared-integration lane plus up to two disjoint
Claude implementation PRs. Codex may lower that limit when review, test, release,
or dependency load makes additional work unsafe. Priority order is P1, active
release/dependency blockers, P2, then P3; priority controls sequencing only.

## Claude PR composition lifecycle

1. Branch from the exact assigned base using a scoped `claude/<issue>-<topic>`
   name unless the task packet specifies another compatible convention.
2. Make the smallest module-scoped change and preserve no-touch files.
3. Add tests, requirement mappings, module revisions, docs, and generated
   artifacts required by the task packet.
4. Run focused checks during development and the full assigned validation subset
   before handback.
5. Open or update one draft PR linked to the issue. Do not open a replacement PR
   for the same scope unless Codex directs it.
6. Record the exact head, results, evidence, cleanup, risks, and decisions in the
   PR. Request Codex review.
7. Address review feedback on the same branch. Never merge or enable auto-merge.

## Codex review and merge lifecycle

1. Confirm the PR still maps to its issue, task packet, branch, base, dependency,
   owned files, requirements, and module versions.
2. Review the exact diff and changed behavior rather than relying on the PR
   summary or another model's conclusion.
3. Verify required checks and evidence are tied to the current head. Reproduce
   high-risk behavior or run additional validation in proportion to risk.
4. Require Claude to revise its branch when the defect is within assigned scope;
   open a linked issue or reallocate work when correction would expand scope.
5. Resolve stacked PRs in dependency order and rebase/retarget downstream work.
6. Confirm required owner approvals and protected-branch rules. Use an expected
   head SHA so a moved PR fails closed.
7. Codex alone performs the repository merge, verifies the merged commit and
   checks, updates or closes the durable issue as appropriate, and releases the
   next approved dependency.

If Codex authored the PR, sole merge execution still does not permit unchecked
self-approval. The PR must satisfy repository-required review, owner authority,
automated checks, and any independent acceptance gate before Codex merges it.

## Merge gate checklist

Codex may merge only when all applicable answers are yes:

- Is the issue authorized, current, and satisfied by the exact PR scope?
- Are dependencies merged or explicitly valid as the target base?
- Are owned/no-touch files and shared-integration rules honored?
- Are requirements, contracts, modules, versions, generated files, and docs
  aligned?
- Are required tests, checks, browser/visual evidence, and cleanup complete for
  the exact head?
- Are security, money, storage, retry, recovery, release, and rollback gates
  satisfied where applicable?
- Is every required owner or external approval recorded durably?
- Is the PR free of unresolved requested changes and material decisions?
- Will the merge method preserve the required provenance and dependency history?

A no or unknown answer blocks merge. Codex records the exact failing gate and
the next recovery action; it does not weaken the gate.

## Handoff contract

Claude-to-Codex handback:

```text
Issue / task packet:
PR / branch / base / dependencies:
Exact head SHA:
Owned and no-touch files:
Requirements and module versions:
Validation and evidence:
Cleanup status:
Open risks or decisions:
Requested next action: Codex review and merge when eligible
```

Codex post-merge handback:

```text
PR and merged commit:
Merge method and verified head:
Checks and acceptance evidence:
Issue disposition:
Released dependency or next lane:
Residual risk, rollback, or follow-up:
```

## Exceptions and changes

Only the repository owner may change the Claude no-merge boundary or designate a
different merge executor. Any temporary exception must be explicit, scoped to a
named PR, recorded in GitHub, and preserve protected-branch and approval rules.
No chat-only exception is valid.
