# Engineering Workforce Governance

Status: authoritative for engineering workforce topology, parallel allocation,
review separation, and queue reporting in this repository.

This policy implements the repository owner's standing direction for a staffed,
parallel engineering organization. It applies to humans, Claude, Codex, and
other approved automation. It supplements `ENGINEERING_PRACTICES.md` and
supersedes the lower-capacity defaults in `docs/codex_parallel_workflow.md` and
`docs/claude_codex_work_division.md` only where those documents limit the number
of concurrent implementation lanes. Their issue, worktree, module, evidence,
Claude no-merge, Codex merge-execution, and owner-authorization rules remain in
force.

## Required workforce

The fully staffed operating unit has thirteen concurrent roles:

- exactly **one Engineering Manager**;
- at least **ten Implementation Workers**; and
- exactly **two Senior Release Engineers**.

The Engineering Manager and Senior Release Engineers are not implementation
workers and never count toward the ten-worker minimum. One person or agent may
hold only one of these thirteen active roles at a time. Additional
implementation workers may be added when the backlog, file ownership, review
capacity, and execution environment support them.

When the runtime exposes at least thirteen safe execution slots, all thirteen
required roles operate concurrently. When it exposes fewer slots, the same
roster is maintained as a rolling queue under [Capacity and scheduling](#capacity-and-scheduling);
queued, waiting, blocked, or completed roles must never be reported as active.

## Role boundaries

### Engineering Manager

There is exactly one Engineering Manager. The manager orchestrates and audits;
the manager does not implement.

The manager:

- reconciles protected `main`, open issues, open PRs, checks, branches,
  worktrees, dependencies, requirement IDs, module versions, and current file
  claims before allocation;
- ranks authorized work by `docs/issue_prioritization.md`, then by explicit
  owner sequence and dependency order;
- creates or confirms the issue and task packet for every lane;
- assigns one ticket, owner, branch, worktree, owned-file set, no-touch set,
  acceptance record, and handoff target per worker;
- prevents duplicate work and concurrent ownership of the same file;
- maintains the worker roster, rolling queue, approval-credit ledger, incident
  state, and truthful status report;
- audits worker handoffs and routes frozen change packets to the Senior Release
  Engineers; and
- stops or reallocates work when authority, dependencies, exact base, required
  evidence, or collision safety is unclear.

The manager must not edit implementation or documentation deliverables, create
implementation commits, author a delivery PR, approve its own work, mark a PR
ready, merge, publish a release, deploy, or mutate an external system. Read-only
inspection, issue/task allocation, audit notes, and queue coordination are the
manager's work product.

### Implementation Workers

At least ten Implementation Workers are assigned to distinct, genuinely
unblocked tickets. Each worker:

- owns one ticket at a time, one isolated worktree, one scoped branch, and one
  explicit file set;
- reads the issue, root and nested instructions, relevant requirements,
  manifests, contracts, and specialist policies before mutation;
- implements the smallest complete acceptance unit within its authority;
- adds the required tests, requirement mappings, module revisions,
  documentation, generated artifacts, and sanitized evidence;
- stages only owned paths and preserves all user and other-worker changes;
- opens or updates one draft PR for the ticket, or returns one explicit blocked
  handoff; and
- stops after the frozen exact-head handoff unless a Senior Release Engineer
  returns bounded review findings to the same branch.

Workers do not mark their own PRs ready, approve, merge, enable auto-merge,
publish releases, deploy, or perform provider or production mutations. A worker
may not silently absorb another ticket; a materially new finding becomes a
linked issue and a new manager allocation.

### Senior Release Engineers

There are exactly two Senior Release Engineers. Both independently review every
candidate exact head and jointly own the ready, merge, release, and deployment
gates. Neither may be the PR author or implementation worker for the candidate
under review.

- **Senior Release Engineer A — Integration:** verifies issue scope,
  dependencies, owned files, exact base/head, requirements, contracts, module
  versions, generated artifacts, checks, acceptance evidence, approvals, and
  merge order. Under the repository's current fixed boundary, this role is held
  by Codex and is the only role that executes the repository merge.
- **Senior Release Engineer B — Independent Assurance:** independently reviews
  the exact diff and risk, reproduces or inspects required evidence in
  proportion to risk, confirms rollback and recovery boundaries, and records a
  separate approve-or-block decision without relying on Engineer A's
  conclusion.

A PR is marked ready only after both engineers record terminal approval for the
same exact head. Engineer A may then perform the normal protected-branch merge
with expected-head protection. A moved head invalidates both approvals. Green
checks, approval credits, urgency, or a prior successful version never replace
either independent review.

Release publication and deployment are separate gates after merge. Both Senior
Release Engineers verify exact provenance, immutable artifacts, predecessor and
rollback compatibility, target readiness, monitoring, and the applicable
runbook. They do not execute an external action until the repository owner has
provided every separately required release, production, provider, spend,
security, or destructive-action authorization.

## Specialty implementation seats

The manager assigns the following specialties across the implementation-worker
roster. A specialty is a least-privilege capability, not standing authority.
One worker may cover more than one compatible specialty, but a high-risk
specialty must not also act as either Senior Release Engineer for its PR.

| Specialty | Owned work | Mandatory boundary |
| --- | --- | --- |
| GitHub and CI | Issues, task packets, branch/PR mechanics, workflow diagnostics, sharding, and check evidence. | No gate weakening, bypass merge, protected-branch push, or secret extraction. |
| Vultr and production cloud | Repository-side host templates, probes, monitoring, rollback plans, and explicitly authorized host operations. | No host, firewall, network, instance, or production mutation without a named target and current owner authorization. |
| Databases and storage providers | Provider-parity code, migrations, transactional behavior, recovery tooling, disposable-target evidence, and capacity analysis. | No live target, schema, data, grant, credential, provider, backup, restore, or database rollback mutation without its separate approved packet. |
| Security and secrets | Threat-boundary review, auth/CSRF/cookie/log safety, secret-safe interfaces, hostile tests, and incident containment. | Never reveal, copy, rotate, create, or broaden access to a secret unless the exact operation is explicitly authorized; use supported secret interfaces only. |
| Browser and QA | Real-browser behavior, accessibility, localization, visual-matrix evidence, regressions, performance, load, and cleanup. | Use disposable isolated users/state and non-user listeners; a shortcut, skipped control, or before-failure image is not acceptance evidence. |
| Release artifacts | Versioning, deterministic packaging, manifests, checksums, SBOM/dependencies, predecessor proof, clean-copy smoke, and publication readiness. | Candidate creation is not publication or deployment authority; immutable assets are never overwritten. |
| DNS | Repository-side records, validation tooling, transition plans, certificate/redirect checks, and rollback instructions. | No zone, registrar, nameserver, certificate, or routing mutation without explicit record-level owner authority and verified rollback. |
| Billing and provider consoles | Read-only readiness audits, bounded change plans, cost/risk statements, and sanitized evidence templates. | No purchase, subscription, quota, account, billing, console, callback, mail, OAuth, or provider-policy mutation without explicit owner authority. |
| Incident response | Triage, containment analysis, evidence preservation, rollback recommendation, recovery validation, and post-incident follow-up. | Follow the incident rules below; do not improvise destructive cleanup, database rollback, credential changes, or public communication. |

Every specialty operates with the smallest repository, environment, account,
target, permission, duration, and data access needed for its assigned ticket.
Capability availability never broadens ticket scope.

## Ticket ownership and collision control

Every implementation lane requires a durable GitHub issue containing scope,
non-goals, owner, priority, dependencies, acceptance criteria, safety boundaries,
and expected evidence. The Engineering Manager records the worker allocation in
the issue or its task packet before implementation begins.

The one-ticket/one-owner invariant is strict:

- one active implementation owner per ticket;
- one branch and one isolated worktree per owner ticket;
- one terminal draft PR or blocked handoff per ticket;
- no duplicate issue, branch, worktree, worker, or PR for the same released
  scope; and
- no unrecorded transfer of ownership.

Before allocation, the manager checks open PRs, remote branches, worktrees, and
recent issue activity. Before editing, the worker repeats the overlap check. If
another active lane owns a required file, the later ticket waits or uses an
explicitly documented stack; it never races or overwrites the earlier lane.

## Worktrees, branches, commits, and PRs

Workers branch from the exact accepted base or from an explicitly approved
stack head. Every worktree is isolated from the user's primary checkout and
from other workers' disposable state. Branch names follow `CONTRIBUTING.md`.

Commits are intentional, bisectable, and scoped to the ticket. A worker stages
only named owned paths and never uses broad staging to absorb unrelated files.
Generated files are updated through their generator. Dirty user data, active
runtimes, evidence, and another worker's worktree are preserved.

A PR contains one reviewable acceptance unit. It normally touches one module
plus its tests, requirements, contracts, and docs. Split a PR when independent
parts can be reviewed, reverted, or released separately; do not split one
atomic invariant merely to reduce line count. A cross-module or omnibus PR
requires a durable owner-approved rationale, a single rollback unit, explicit
file ownership, and an ordered commit series.

Shared manifests, requirement sources, generated docs, catalogs, compatibility
records, visual matrices, and release metadata have one integration owner. When
successive PRs need the same shared file, stack them in declared dependency
order. The downstream worker branches from the approved upstream head, records
the dependency, and after the upstream merge rebases or retargets, recalculates
versions and generated files, and reruns its complete validation set.

## Tests and acceptance evidence

The issue's acceptance criteria are the definition of the worker's required
evidence. During development, workers run the narrowest focused checks; before
handoff they run every applicable repository, module, contract, browser,
visual, security, storage, recovery, release, or operational gate named by the
issue and repository policy.

Evidence must:

- bind to the exact base, exact head, environment, provider class, and command;
- report attempted, completed, failed, skipped, timing, invariant, and cleanup
  counts where applicable;
- use real public UI/actions when the requirement says browser or UI;
- use disposable state and verify listeners, processes, temporary data, and
  credentials are cleaned up;
- be sanitized of secrets, identifiers, personal data, paths, cookies, raw
  errors, and provider payloads; and
- distinguish `before_failure` diagnosis from `after_pass` acceptance.

No check may be weakened, skipped, renamed, retried into a false pass, or
replaced by a lower-fidelity test. A passing short test cannot overrule a
failing long, browser, visual, security, money, migration, or recovery gate.

## Approval-credit ledger

The Engineering Manager maintains the owner's standing PR approval-credit
ledger. The ledger records its opening balance, every successful merge that
consumes a credit, and the remaining balance.

- One ordinary repository PR lifecycle consumes exactly one credit when the PR
  merges successfully.
- Opening a draft, updating a branch, rerunning checks, receiving review,
  closing without merge, or retrying a failed check consumes no additional
  credit.
- While the balance is positive, agents do not interrupt the owner for another
  routine PR approval; they still satisfy all issue, review, protected-branch,
  and exact-head gates.
- At zero, no new routine merge is initiated until the owner adds credits.
  In-flight implementation may reach a safe frozen handoff.
- Credits do not authorize production, deployment, release publication,
  database, provider, billing, DNS, mail, signup, OAuth, secret, destructive,
  public-exposure, or spend mutations, and never waive a required approval.

## Capacity and scheduling

The Engineering Manager keeps at least ten implementation tickets assigned and
ready whenever ten genuinely unblocked, non-colliding tickets exist. The active
execution target is thirteen simultaneous roles: one manager, ten workers, and
two Senior Release Engineers.

If technical concurrency is below thirteen, the manager uses a rolling queue:

1. Reserve one slot for the Engineering Manager.
2. Keep a Senior Release Engineer available whenever a candidate is awaiting
   review, and make both available for the final exact-head decision.
3. Fill remaining slots with the highest-ranked unblocked implementation lanes
   whose file ownership and dependencies are disjoint.
4. When a worker reaches terminal handoff or a genuine wait, immediately admit
   the next ready worker instead of leaving the slot idle.
5. Serialize only the shared-file or dependency-critical portion; unrelated
   workers continue.
6. Reconcile the queue after every merge, changed head, new P1, incident,
   authority change, or dependency transition.

A worker waiting on CI, review, an owner decision, external access, or a stacked
dependency is not actively implementing. The manager may use the released slot
for another non-colliding ticket while preserving ownership of the waiting
branch.

## Truthful workforce reporting

Every workforce status report states:

- timestamp and exact protected-main SHA;
- runtime slot capacity;
- active Engineering Manager count, which must be zero or one;
- active Implementation Worker count and each ticket/branch/current phase;
- active Senior Release Engineer count and each exact-head review;
- queued, waiting, blocked, and completed counts separately;
- open PRs, dependency stacks, and shared-file reservations;
- approval credits remaining; and
- the next worker admission and next release-gate action.

`Active` means the role currently occupies an execution slot and is performing
read, implementation, validation, review, or authorized operational work.
Queued assignments, scheduled automations, stale chats, completed workers,
waiting CI jobs, and named specialties with no running task are not active.
Reports must never claim ten active workers when the runtime exposes fewer than
ten worker slots.

## Retries, failures, and handoffs

Retries are bounded, evidence-preserving continuations of the same action. A
state-changing retry reuses the same stable idempotency identity; changed
meaning requires a new action and explicit scope. A worker diagnoses the first
concrete failure before retrying and may not hide elapsed time, reset evidence,
change immutable bytes, relax a timeout, skip a control, or rerun until random
success.

CI failures inside scope return to the same worker and branch. Scope expansion,
foreign failures, capacity defects, and new findings become manager decisions
or linked tickets. A failed release or deployment follows its runbook: preserve
the alarm and evidence, keep or restore the verified predecessor, stop automatic
retry where required, and open a bounded follow-up. Never replace an immutable
release in place or perform database rollback as an application retry.

Every worker handoff includes:

```text
Issue and task packet:
Worker, branch, worktree, base, dependencies, and exact head:
Owned and no-touch files:
Requirements, modules, versions, contracts, and release impact:
Validation, evidence, timing, and cleanup:
Known risks, blockers, and linked findings:
Requested next action: independent Senior Release Engineer review
```

Each Senior Release Engineer records its own exact-head approve-or-block result.
After merge, Engineer A records the merge commit and method, checks on merged
state, issue disposition and rollout link, approval-credit balance, released
dependency, and any residual rollback or follow-up.

## Production mutation and outage rules

Repository implementation, merge, release publication, deployment, migration,
provider change, and live verification are separate authorizations. No role may
infer external authority from priority, approval credits, green checks, a
deadline, an outage, or possession of credentials.

Before any authorized production mutation, both Senior Release Engineers must
verify the named target, exact immutable artifact, owner approval, least-
privilege actor, current backup/recovery evidence, schema/runtime compatibility,
rollback boundary, monitoring, maintenance/readiness plan, sanitized evidence,
and stop conditions. The operator follows the applicable runbook exactly.
Secrets never enter Git, arguments, screenshots, issues, PRs, logs, or chat.

During a suspected outage or integrity incident:

1. The Engineering Manager declares incident mode, records the durable incident
   ticket, severity, timestamp, observed impact, and current production
   identity, and pauses unrelated ready/merge/release/deploy actions.
2. The manager assigns an Incident Response worker for diagnosis and separate
   bounded workers for containment, verification, or repair only when their
   ownership is disjoint.
3. Workers preserve logs and evidence, use read-only probes first, protect
   secrets and user data, and report facts rather than speculative success.
4. Both Senior Release Engineers independently verify any rollback, failover,
   hotfix, migration, or service-restoration plan. The owner supplies every
   external or destructive authorization still required.
5. Application rollback uses only the authenticated compatible predecessor.
   Database or schema rollback is prohibited unless a separately approved
   recovery plan explicitly authorizes it.
6. If the predecessor is incompatible or restoration evidence fails, keep the
   service held or degraded according to the runbook; do not improvise a
   destructive repair.
7. Resume the ordinary queue only after service identity, readiness, persistence,
   monitoring, alarms, cleanup, and follow-up ownership are durably recorded.

## Definition of done

A workforce-delivered ticket is done only when:

- its durable issue, allocation, scope, dependencies, non-goals, and acceptance
  criteria are satisfied;
- the implementation worker used an isolated worktree, honored owned/no-touch
  files, and produced an intentional exact-head diff;
- requirements, contracts, compatibility data, module versions, generated
  artifacts, docs, tests, and release notes align;
- every focused and required gate passes on the exact proposed head with honest
  sanitized evidence and verified cleanup;
- both Senior Release Engineers independently approve that same exact head;
- Engineer A performs and verifies the normal protected-branch merge;
- the issue has a merged PR cross-reference or explicit `Rolled out with #NNN`
  evidence before completed disposition;
- the approval-credit ledger is decremented exactly once for the successful
  merge;
- any release, publication, deployment, live verification, migration, provider,
  DNS, billing, security, or destructive gate remains open until separately
  authorized and evidenced; and
- the manager releases the next dependency, updates the truthful roster, and
  records every residual risk or follow-up ticket.

Implementation completion is not release completion, and release completion is
not deployment completion. No role may report a later stage complete because an
earlier stage passed.
