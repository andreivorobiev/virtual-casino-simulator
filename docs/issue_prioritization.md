# Issue prioritization and label policy

This document is the repository source of truth for GitHub issue priority and
triage labels. It applies to every open issue in
`andreivorobiev/virtual-casino-simulator`.

## Required invariant

Every open issue must have exactly one priority label: `P1`, `P2`, or `P3`.

- An issue must never have two priority labels.
- `P4` is not part of this repository's taxonomy.
- A missing priority is a triage defect and must be corrected.
- Priority text such as `P1:` must not appear in an issue title. The label is
  authoritative.
- Closed issues may retain their last priority for historical context.

## Priority definitions

### P1 — Critical now

Use `P1` when the issue is an immediate safety, integrity, availability, or
release concern. Examples include:

- security, privacy, authentication, authorization, or Admin exposure;
- wallet, ledger, balance, or persistent-data corruption;
- incorrect wager settlement, payout mathematics, or exploitable game logic;
- production or restricted-preview outage;
- an active release, cutover, or acceptance blocker; or
- irreversible loss or a failure with no safe workaround.

P1 work is sequenced before lower priorities unless it is blocked. A blocked P1
remains P1; `blocked` records execution state, not importance.

### P2 — High next

Use `P2` for important near-term work that has major user or delivery impact but
is not an immediate P1 condition. Examples include:

- a major user-facing functional failure with a workaround;
- committed near-term product delivery or foundational work;
- an accessibility, localization, privacy, provider, or release-readiness
  obligation;
- significant workflow degradation; or
- important acceptance or qualification evidence.

### P3 — Planned or backlog

Use `P3` for work that can safely wait. It includes:

- contained defects with a safe workaround and limited blast radius;
- moderate UX, reliability, maintainability, or testability improvements;
- minor copy, spacing, layout, visual, or other polish defects;
- planned enhancements outside the immediate release path; and
- speculative or long-horizon backlog items worth retaining.

If an item is not worth retaining in P3, use an appropriate disposition such as
`duplicate`, `invalid`, or `wontfix` and close it. Do not create a fourth
priority tier.

## Decision rules

1. Read the issue title, body, labels, recent comments, dependencies, and release
   context before assigning priority.
2. Apply the highest priority whose definition is satisfied.
3. Do not infer priority from the title, issue number, severity, age, or current
   assignee alone.
4. Priority expresses urgency and sequencing. Severity expresses defect impact.
5. Being blocked does not lower priority.
6. An owner-committed release requirement must not be downgraded without a
   documented reason.
7. Priority labels authorize sequencing only. They do not authorize code
   changes, merges, deployments, provider mutations, issue closure, or bypassing
   dependencies and ownership.
8. Reassess priority when impact, exposure, dependencies, or release scope
   materially changes.

When two levels appear plausible, use the higher level and flag the uncertainty
for owner review.

## Label taxonomy

Use only existing repository labels unless the owner explicitly approves a new
label.

### Priority — exactly one

- `P1`
- `P2`
- `P3`

### Severity — bugs only, at most one

- `severity:critical` — active exploit, irreversible data loss, or service-wide
  failure;
- `severity:high` — major security, integrity, or functional impact;
- `severity:medium` — material but contained defect or available workaround;
- `severity:low` — minor or cosmetic defect.

### Issue category

- `bug`
- `enhancement`
- `documentation`
- `question`

`bug` and `enhancement` are mutually exclusive. `documentation` may accompany a
category when documentation is a material part of the work.

### Area — apply every relevant area

- `area:acey-deucey`
- `area:admin`
- `area:auth`
- `area:baccarat`
- `area:blackjack`
- `area:caribbean-stud`
- `area:casino-holdem`
- `area:fan-tan`
- `area:i18n`
- `area:keno`
- `area:lobby`
- `area:over-under-7`
- `area:plinko`
- `area:polish`
- `area:roulette`
- `area:slots`
- `area:wallet`

### Origin or workstream

- `qa` — discovered through exploratory or acceptance testing;
- `code-audit` — discovered through source inspection;
- `coordination` — planning or cross-issue sequencing;
- `deployment` — hosting, cutover, or release readiness;
- `oci` — Oracle Cloud Infrastructure work;
- `ops` — monitoring, backup, incident, or runbook work.

### Workflow or disposition

- `blocked`
- `duplicate`
- `invalid`
- `wontfix`
- `help wanted`
- `good first issue`

## Issue creation rules

Repository issue forms apply the primary category label for bug, feature,
documentation, and Codex coordination issues. They intentionally do not assign a
priority: the triage owner must read the completed issue and apply exactly one
priority label using this policy.

An issue author may describe impact and urgency, but must not place a proposed
priority in the title. Priority is recorded only through the canonical label.

## Triage procedure

1. Audit every open issue before making bulk changes.
2. Assign exactly one of `P1`, `P2`, or `P3`.
3. Remove conflicting or obsolete priority labels.
4. Add the relevant category, severity, area, origin, and workflow labels.
5. Preserve useful labels unless they are demonstrably incorrect or redundant.
6. Remove priority prefixes from titles because the label is authoritative.
7. Do not create, close, implement, merge, or deploy as part of a priority-only
   task unless separately authorized.
8. Verify the queue after all writes.

The final audit must satisfy:

```text
open issues = P1 + P2 + P3
missing priorities = 0
conflicting priorities = 0
P4 labels = 0
```

Report the total open issues, counts by priority, all changed issues, all label
changes, unresolved ambiguities, and any owner decision required.

## Copy-ready AI triage prompt

```text
You are the product-triage agent for
https://github.com/andreivorobiev/virtual-casino-simulator.

Follow docs/issue_prioritization.md as the authoritative priority and label
policy. Read it completely before changing GitHub state.

Your task is to audit the full open issue queue and enforce these invariants:
- every open issue has exactly one of P1, P2, or P3;
- no open issue has multiple priority labels;
- P4 does not exist and must not be recreated;
- severity, area, origin, and workflow labels remain separate from priority;
- issue titles do not contain priority prefixes.

Read each issue's title, body, labels, recent comments, dependencies, and release
context. Apply the highest priority whose definition is satisfied. Do not lower
a blocked issue, infer priority from severity alone, or downgrade an
owner-committed release requirement without documenting the reason.

Use only the labels listed in docs/issue_prioritization.md. Do not invent labels.
Preserve useful labels and remove only labels that are demonstrably incorrect,
obsolete, conflicting, or redundant.

This is a triage task only. Do not implement code, open pull requests, deploy,
mutate providers, close issues, or create replacement issues unless separately
authorized.

After applying changes, report:
- total open issues;
- P1, P2, and P3 counts;
- issues whose priority changed;
- missing or conflicting priorities;
- labels added or removed;
- owner decisions still required.

Do not finish until:
open issues = P1 + P2 + P3
missing priorities = 0
conflicting priorities = 0
P4 labels = 0
```
