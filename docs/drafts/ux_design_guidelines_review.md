# UX design guidelines review packet

Status: **draft for owner and external-reviewer review; not authoritative**.

This packet proposes a canonical UX standard and the GitHub implementation
ticket that would make the standard enforceable. Publishing this packet in a
review pull request does not create permanent requirements, repository rules,
tests, labels, or issues and does not approve the proposal.

## Decisions requested from the owner

1. Approve `docs/ux_design_guidelines.md` as the authority for user journeys,
   interaction behavior, content, accessibility, trust, and recovery.
2. Keep `docs/visual_design_standard.md` as the required presentation, layout,
   responsive, and visual-evidence companion rather than duplicating it.
3. Approve WCAG 2.2 AA as the accessibility target. The primary touch-target
   minimum is already settled at 42 CSS pixels by issue #283, with 44
   recommended for newly designed surfaces, so this draft adopts that floor
   rather than reopening it.
4. Approve a blocking UX governance check for every browser-visible pull
   request, including explicit guideline IDs, affected flows and states, tests,
   and `after_pass` evidence.
5. Approve the proposed implementation ticket as P1 because the owner requires
   all subsequent UX work to be evaluated against the guidelines.

---

# Proposed UX design guidelines

## 1. Status, authority, and scope

These guidelines are authoritative for every user-facing journey in Virtual
Casino Simulator, including authentication, terms consent, the shared shell,
lobby, wallet, all games, autoplay, bots, Admin, responsive behavior, errors,
loading, empty states, localization, and accessibility.

They apply equally to human contributors and AI-assisted engineering tools.

Authority is divided without overlap:

- `docs/ux_design_guidelines.md` governs user intent, journeys, interaction,
  language, feedback, recovery, accessibility, and trust.
- `docs/visual_design_standard.md` governs presentation hierarchy, layout,
  scrolling, responsive composition, and visual evidence.
- `tests/visual/visual_matrix.json` remains the executable visual surface,
  state, locale, viewport, and evidence inventory.
- A proposed `tests/ux/ux_matrix.json` records executable UX flows, states, and
  guideline gates.

When rules appear to conflict, choose the interpretation that best preserves
user control, accessibility, balance accuracy, fake-money clarity, safe
recovery, and server-authoritative state. Record any unresolved conflict before
implementation.

## 2. Core principles

### UX-PRINCIPLE-001 — Clarity before spectacle

The interface must make the current state, available actions, committed play
tokens, likely result of an action, and next step understandable before adding
animation, decoration, density, or novelty.

### UX-PRINCIPLE-002 — User control

The user initiates wagering and automated play. Rejected, cancelled, stopped,
or unavailable actions must not continue in the background. Stop controls must
prevent new atomic actions while allowing only already committed actions to
finish safely.

### UX-PRINCIPLE-003 — Accurate and trustworthy state

Wallet balances, stakes, committed wagers, outcomes, payouts, and net results
must agree across the shell, game view, history, and Admin. Displayed state must
come from the authoritative response rather than optimistic assumptions when
tokens or persistent state are involved.

### UX-PRINCIPLE-004 — Consistency with purpose

Shared actions, phases, labels, controls, wallet behavior, errors, and recovery
patterns use shared components and language. A game may differ when its rules
require it, but not because it independently reinvented a common interaction.

### UX-PRINCIPLE-005 — Inclusive by default

Keyboard, screen-reader, touch, zoom, reduced-motion, color-independent, and
localized use are normal acceptance paths, not optional follow-up work.

### UX-PRINCIPLE-006 — Progressive disclosure

The primary decision and stage remain obvious. Advanced configuration,
statistics, history, bots, and autoplay remain available without competing with
the current player task.

## 3. Information architecture and navigation

- Every screen identifies the current location and primary purpose.
- The lobby is always reachable through stable shared navigation.
- Browser Back, Forward, refresh, and a restored route must not silently lose or
  duplicate a committed action.
- Locale changes preserve the current route and recoverable in-progress state.
- No journey ends in a dead end; error and empty states provide a safe next
  action.
- Navigation must not present Admin access to users who lack the required role.
- Unsaved or unresolved wagers receive an explicit leave behavior: preserve,
  complete, refund, or warn according to the authoritative game contract.

## 4. Interaction and control behavior

### Stable controls

- An enabled control remains addressable until its action is synchronously
  accepted, disabled, or marked busy.
- Controls must not disappear between pointer-down and action acceptance.
- The primary action remains in a stable location across adjacent phases unless
  the journey documents a necessary replacement.

### Busy and duplicate-action protection

- Mutating actions enter a visible busy state before the first asynchronous
  yield.
- Busy controls are semantically disabled, expose `aria-busy` where applicable,
  and cannot submit a second mutation.
- Retryable commands retain the same idempotency key across an ambiguous or lost
  response. A retry must replay or reconcile the original action, not debit a
  second wager.
- A failed server-authority request must not start a client-only fallback loop.

### Inputs and validation

- Inputs have persistent labels, constraints, units, and examples where useful.
- Validation occurs before submission when possible and is repeated by the
  server.
- Invalid, negative, non-finite, stale, or out-of-range values cannot reach a
  token-changing action.
- Errors appear next to the relevant field or action and explain how to recover.
- User input is preserved after a recoverable error.

### Feedback timing

- Direct manipulation and selection feedback should appear within 100 ms.
- Actions that may exceed 500 ms expose an intentional busy or progress state.
- Long operations identify what is happening and provide a safe cancellation or
  stop path when cancellation is supported.

## 5. Game and wagering journeys

Before a wager is committed, the interface shows:

- the selected wager type;
- the per-bet and total stake;
- the available play-token balance;
- whether placement immediately debits tokens or commitment occurs on the
  primary play action; and
- the next available action.

All games follow these rules:

- Bet-placement and debit timing must be consistent within the game and clearly
  communicated.
- Clearing an unplayed bet restores exactly the amount removed for that bet.
- Leaving a game with an unresolved bet must not silently lose or duplicate the
  stake.
- Bet labels identify the actual covered outcome and cannot rely on ambiguous
  internal names.
- A result view shows the wager, outcome, return, and net change using one
  consistent convention.
- Side bets, insurance, raises, splits, doubles, refunds, commissions, and bonus
  payouts are included in settlement summaries.
- The UI never claims success until the authoritative result is known.

## 6. Wallet and fake-money framing

- Play tokens are simulator values with no cash value, purchase, deposit,
  withdrawal, redemption, sale, transfer, exchange, prize, or conversion path.
- The same balance uses a consistent precision and rounding rule everywhere.
- Token-changing actions identify the amount and reason.
- The wallet distinguishes available, committed, returned, and won tokens when
  that distinction is material to the current journey.
- An add-token action is clearly simulator replenishment and never resembles a
  payment flow.
- Currency symbols, payment language, and real-money calls to action are
  forbidden.

## 7. System status, errors, and recovery

Every user-facing flow defines loading, ready, busy, success, empty, disabled,
error, offline/degraded where applicable, and recovered states.

- Errors use plain language, identify what failed, and provide the safest next
  action.
- Error details never expose stack traces, secrets, internal paths, resource
  keys, database details, or raw provider responses.
- A toast may announce an error, but a persistent inline or page-level state is
  required when the user must act on it.
- A retry does not duplicate a committed action.
- Refresh or route restoration reconciles against server-authoritative state.
- Degraded services identify unavailable capabilities without making unrelated
  areas unusable.
- Destructive Admin actions require clear scope, confirmation, result feedback,
  and an audit trail where supported.

## 8. Content and terminology

- Use concise, direct, player-facing language.
- Buttons describe the action: `Spin`, `Deal`, `Draw`, `Place wager`, `Clear
  bets`, or `Stop autoplay`; avoid vague labels such as `Submit` or `Continue`
  when a more specific action exists.
- Status language describes a user-understandable phase rather than an internal
  state name.
- Odds, payout, return, and net use one documented convention per game and
  explain exceptions.
- English and Russian content must communicate the same meaning and action.
- Resource keys, fallback identifiers, slugs, test IDs, implementation labels,
  and debug copy are failures.
- Text must tolerate localization expansion without clipping or hiding primary
  actions.

## 9. Accessibility

The target is WCAG 2.2 Level AA for supported user-facing surfaces.

- All actions are operable by keyboard with a logical focus order and visible
  focus indication.
- Controls use semantic elements and stable accessible names.
- Dynamic status changes use appropriate announcements without excessive noise.
- Color is not the only indicator of selection, phase, success, loss, warning,
  or error.
- Primary touch actions are at least 42 by 42 CSS pixels (issue #283), with 44
  by 44 recommended for newly designed surfaces; closely spaced targets provide
  sufficient separation.
- Content remains usable at 200% browser zoom and with text enlargement.
- Animation respects `prefers-reduced-motion` and offers an equivalent clear
  state transition.
- Time-dependent flows provide sufficient control and do not punish assistive
  technology users for slower interaction.

## 10. Motion and feedback

- Motion explains cause, progress, or outcome; decorative motion must not obscure
  state or delay the next safe action.
- Essential controls do not move during interaction.
- The animation result must match the authoritative result and end in a stable,
  inspectable state.
- Interrupted or failed animation recovers to the correct authoritative phase.
- Reduced-motion mode preserves timing clarity without simulated physical
  movement.
- Sound is supplementary, respects user preference, and is never the only result
  signal.

## 11. Responsive UX

- Desktop, compact desktop, tablet, and mobile preserve the same task meaning
  even when composition changes.
- Primary action, stake, phase, and result remain easy to find.
- Touch targets, focus order, reading order, and announcements follow the visual
  order.
- Page-level horizontal scrolling is forbidden.
- Mobile stacking must not create large empty regions, nested primary scrolling,
  clipped actions, or hidden wallet context.

## 12. Shared components and design-system use

Use shared components for the shell, wallet, phase status, primary actions,
inputs, validation, busy states, dialogs, toasts, tabs, tables, and evidence
hooks. A local variant must document why the shared pattern cannot satisfy the
journey and how its accessibility and recovery behavior remain equivalent.

Visual tokens control color, typography, spacing, radius, elevation, motion,
focus, and disabled states. Hard-coded local styles must not create a competing
interaction language.

## 13. UX evidence and acceptance

Every browser-visible pull request identifies:

- affected user journeys and actors;
- UX guideline gate IDs;
- visual matrix surface and state IDs;
- changed loading, ready, busy, success, empty, disabled, error, and recovery
  states;
- required locales and viewports;
- keyboard, touch, reduced-motion, and route-restoration coverage;
- affected requirements and module versions; and
- `after_pass` evidence from the exact tested commit.

Acceptance evidence must prove behavior, not only appearance. A screenshot can
prove layout and copy; browser tests or traces prove focus order, mutation
serialization, retries, state restoration, and recovery.

## 14. Exceptions

An exception must be explicit in the pull request, explain the user impact,
name the owner, and link a follow-up issue with a due release or decision point.

Exceptions may not waive:

- fake-money and no-cash-value framing;
- authorization and least privilege;
- wallet, wager, payout, or settlement accuracy;
- duplicate-action and retry safety;
- keyboard access and visible focus;
- reduced-motion support for essential journeys;
- absence of debug/resource-key content; or
- safe recovery from rejected or ambiguous mutations.

## 15. Definition of UX done

A browser-visible change is UX-complete only when:

1. the intended journey and affected states are documented;
2. the implementation satisfies these guidelines and the visual standard;
3. shared components are used or an approved exception is documented;
4. relevant automated and manual acceptance paths pass;
5. required locales, viewports, keyboard, touch, and reduced-motion paths pass;
6. exact-commit `after_pass` evidence is attached;
7. requirements, matrix coverage, module versions, and release notes are aligned;
   and
8. no unresolved P1 or P2 UX defect remains in the affected journey unless the
   owner explicitly holds release with documented rationale.

---

# Proposed GitHub ticket

## Title

Establish canonical UX design guidelines and enforce them for every browser-visible change

## Proposed labels

`P1`, `enhancement`, `documentation`, `coordination`, `area:polish`, `qa`

## Body

### Objective

Create a vendor-neutral, repository-authoritative UX design standard and make
conformance a required, evidence-backed gate for every browser-visible change.
The new standard must complement—not duplicate or weaken—the existing visual
design standard and visual matrix.

### Context

`docs/visual_design_standard.md` and `tests/visual/visual_matrix.json` already
govern presentation, responsive layout, visual states, and evidence. The
repository lacks one canonical authority for end-to-end user journeys,
interaction behavior, stable controls, validation, busy states, retries,
recovery, settlement clarity, content, and cross-surface UX consistency.

### Deliverables

1. Add approved `docs/ux_design_guidelines.md` with stable UX gate IDs.
2. Define the authority boundary between the UX guidelines, visual standard,
   and visual matrix.
3. Add `tests/ux/ux_matrix.json` covering actors, flows, states, applicable UX
   gate IDs, locales, viewports, input modes, and recovery paths.
4. Update root and nested engineering instructions so human and AI-assisted UI
   work must read and cite the UX guidelines.
5. Update the pull-request template with a blocking UX-governance section.
6. Update browser-visible issue forms to capture affected journeys, actors,
   states, accessibility paths, and expected evidence.
7. Add a validator and GitHub Actions check that fail when a browser-visible PR
   omits required UX declarations or references unknown UX/matrix IDs.
8. Add browser-test mapping for stable controls, duplicate-action protection,
   retry idempotency, loading/error/recovery states, keyboard operation,
   reduced motion, responsive behavior, and EN/RU parity.
9. Adopt the resolved touch-target rule from issue #283: a 42 CSS-pixel floor
   for primary and high-frequency controls, with 44 recommended for newly
   designed surfaces (`docs/visual_design_standard.md`).
10. Document the exception process and non-waivable UX gates.

### Acceptance criteria

- One unambiguous UX authority exists and is linked from engineering practices,
  contributor guidance, agent instructions, issue forms, and the PR template.
- Every browser-visible PR must name affected UX gate IDs and visual/UX matrix
  rows.
- CI rejects unknown IDs, missing declarations, missing required states, or a
  claimed exception without a linked follow-up issue.
- UX coverage includes loading, ready, busy, success, empty, disabled, error,
  degraded/offline where applicable, and recovered states.
- UX coverage includes keyboard, touch, reduced-motion, route restoration,
  EN/RU, and the required viewports.
- Token-changing actions prove stable controls, duplicate-submit prevention,
  retry idempotency, authoritative reconciliation, and accurate settlement.
- Visual-only evidence is not accepted for behavioral UX gates.
- Existing visual governance remains valid and no competing standard is left in
  the repository.
- Relevant requirements, module versions, generated docs, and release notes are
  updated according to repository policy.
- Full required validation and exact-head GitHub checks pass.

### Non-goals

- Do not redesign every existing surface in this issue.
- Do not waive current visual, accessibility, fake-money, security, ledger, or
  API-contract requirements.
- Do not create tool-vendor-specific UX instructions.
- Do not treat a checklist alone as proof of UX correctness.

### Validation

Run the repository-required validators, focused UX-governance tests, complete
browser acceptance, matrix validation, and exact-head GitHub checks. Include
clean `after_pass` evidence for the governance examples used to prove the new
standard.

### Owner review gate

Do not implement or file follow-up enforcement work until the owner approves
the guideline authority model, accessibility target, touch-target rule,
blocking CI behavior, proposed priority, and ticket text.
