# Issue #488 Challenge Points policy-foundation task packet

Status: source-only implementation admitted as child #1091; central metadata remains Senior A-owned.

## Task

- Issue: #1091 bounded code-delivery child of #488.
- Priority: inherits #488 P3 sequencing; priority does not authorize activation.
- Assigned author: Worker07.
- Authoring system: Codex.
- Coordinator and merge executor: Codex / Senior A integration queue.
- Branch: `codex/488-challenge-foundation`.
- Base branch and commit: protected `main` at `8cce66851edef2a97350e39be661e5e2f1808b6c`, tree `7256a1ec26f9eb24a8cc2c36bdc08ca1918369ff`.
- Dependency PRs: none for the route-free prototype; shared integration remains coordinator-held.
- PR title: `feat(core): add inactive Challenge Points policy foundation`.
- Required owner approval or external gate: central metadata stack, predecessor rebase, push and draft-PR release.
- Coordinator task: integrate the reserved IDs, module revisions, shared test registration, generated files, and merge order.
- Worker task: provide the inactive provider-neutral transition kernel, focused tests, aligned documentation, and a draft PR after allocation.

## Goal

- Goal: establish server-owned Challenge Points admission and scoring transitions over trusted versioned scorers before any ranked game can award points, while leaving production-formula determinism to owning-game certification.
- Non-goals: no game implementation, production rule registration, endpoint, provider adapter, migration, season aggregation, leaderboard, Admin view, UI, token movement, deployment, or external system.
- User-visible behavior expected: none; the production rule registry remains explicitly empty and routes remain absent.

## Requirements

- Requirement IDs reused: `CHALLENGE-001`, `CHALLENGE-002`, `CHALLENGE-003`, and test evidence `TEST-263`.
- Requirement IDs changed: none planned.
- Requirement IDs validated: `CHALLENGE-001`, `CHALLENGE-002`, `CHALLENGE-003`, and `TEST-263`; no Ledger requirement is mapped because this slice proves structural separation rather than ledger behavior.

## Scope

- Impacted modules: Core, Tests, Docs after authorization.
- Packaged application release impact: none.
- Independent module revision bumps planned: Core `10.20.0`; exact Tests/Docs versions remain coordinator-owned pending predecessor order.
- Worker-owned new files: `casino/core/challenges/__init__.py`, `casino/core/challenges/policy.py`, `tests/challenge_policy_tests.py`, and this packet.
- Shared files retained by Senior A: `tests/cases/api/player_foundation.py`, `tests/api_case_inventory.json`, module manifests, requirement sources/generated outputs, and generated Markdown index.
- Files not to touch: ledger, player wallet, storage providers, migrations, router/app routes, contracts until separately assigned, game catalog/descriptors, game modules, web UI, visual matrix, Admin, CI/workflows, release artifacts, deployment/provider files.
- Allowed adjacent files: only coordinator-approved generated requirement/docs outputs after source IDs land.

## Compatibility

- API contract impact: none in this slice; no endpoint or response envelope exists.
- Gameplay impact: none; no game or ruleset registers the kernel.
- Ledger impact: none; source structurally imports no ledger/player/storage boundary and the reviewed top-level event inventory contains no amount, balance, token, wager, payout, transaction, or ledger identifier. Trusted canonical fact mappings carry no movement authority.
- Bot/autoplay impact: no behavior; ranked events reserve a canonical non-secret map for future bot strategy IDs/versions.
- Data migration impact: none; the kernel emits immutable provider-neutral append candidates but no adapter consumes them.
- Security/privacy impact: authenticated player identity is an internal required argument; receipts contain no email, session, address, active secret, private board, or raw bot decision. Commitment IDs are references only.
- Release/provenance impact: none.
- Deployment/provider impact: none; JSON, MySQL, PostgreSQL, OCI, VM, DNS, mail, billing, and public exposure stay untouched.

## Kernel transition contract

1. Practice start/completion returns zero append candidates and a receipt marked non-durable. Practice can show feedback from a trusted leaf-certified formula but cannot change ranked attempts or daily best.
2. Ranked start owns the authenticated player, game, rules version, server configuration, commitment reference, optional bot strategy versions, coordinator-supplied season identity, and start UTC day. Exactly three starts are admitted per player/game/start day; abandoned active starts remain consumed.
3. Terminal acceptance invokes only a trusted versioned formula over canonical server facts; the owning game, not this kernel, must certify that formula's determinism. Points must be an exact integer from 0 through 1,000. Rejected validation skips the formula and records zero.
4. Daily best is the highest accepted score. `counted_best_delta` is the strict positive improvement over prior accepted history, never an additive balance.
5. One operation key is global to the player/game journal. Exact semantic retry returns the original immutable receipt without formula, identity generation, or append. Changed meaning raises a stable conflict.
6. A run has one charged start and at most one terminal. Decoded history rejects mismatched start days, duplicate operation or run identities, orphaned or repeated terminals, reversed append or time order, and terminal drift in day, ordinal, rule, configuration, season, commitment, or bot-strategy authority. Cross-subject, cross-game, noncanonical, changed-policy, or inconsistent aggregate evidence also fails closed.
7. The kernel must run inside one future provider transaction. Concurrent callers cannot safely append candidates from separate snapshots; provider parity, recovery, and concurrency remain unclaimed until separately implemented and certified.

## Focused test matrix

| Cell | Expected invariant |
| --- | --- |
| Practice start and accepted completion | No append event; leaf-certified fixture score; no counted delta; all ranked attempts remain. |
| Three ranked starts, no terminals | Ordinals 1–3; fourth start conflicts; abandonment does not refund. |
| Accepted scores 650, 500, 900 | Deltas 650, 0, 250; projected best 900 rather than 2,050. |
| Exact start and terminal retries | Original receipt; no event; no new identity; counting scorer remains at one call after terminal replay. |
| Changed facts/day/rules/config/key meaning | Stable conflict; first committed meaning remains authoritative. |
| Rejected validation | Formula not called; score/delta zero; attempt remains consumed. |
| Score and canonical-input boundaries | Exact integers 0 and 1,000 succeed; underflow, overflow, fractions, booleans, strings, NaN, and malformed inputs fail before append construction. |
| New UTC day | Independent three-attempt allowance; operation-key uniqueness remains global. |
| Decoded start identities | Start day matches its instant; duplicate run or operation identities fail before projection or identity generation. |
| Decoded terminal authority | Every inherited start field, append/time order, and single-terminal invariant fails closed before rescoring or identity generation. |
| Cross-subject/game, duplicate/reordered history | Projection fails closed without exposing another subject. |
| Static dependency and event-field audit | No wallet/storage/route/game imports and no money/ledger fields. |

## Required reading

- `CODEX_START_HERE.md`, root and nested `AGENTS.md`, `ENGINEERING_PRACTICES.md`.
- `docs/engineering_skills.md`, `docs/claude_codex_work_division.md`, `docs/codex_parallel_workflow.md`.
- Issue #488 and current comments, closed #77 disposition, `docs/server_authority_certification.md`, and `docs/api_contract_freeze.md`.
- `modules/module-manifest.json`, `modules/core.json`, `modules/tests.json`, `modules/docs.json`.
- Existing ledger requirements only for negative separation; ledger implementation remains no-touch.

## Validation

- Focused prototype: bundled Python `-m unittest tests.challenge_policy_tests -v` reports exactly 13 tests, and `py_compile` covers the three new Python files.
- After allocation: registered API case, requirements assembly/validation, versions, module boundaries, headers, file length, generated docs check, and contract validator for unchanged-API proof.
- Hosted CI: ordinary protected checks after draft PR push.
- Heavy API/Browser/Long/formal/load suites: not authorized locally; request the single heavy-test slot if Senior A requires one.
- Visual rows/locales/viewports/browser evidence: none because no browser-visible behavior exists.
- Disposable state and cleanup: no listener, provider, file-backed state, or external target is created by focused tests.

## Deferred decisions and stop conditions

- Season calendar and aggregation semantics are deliberately not inferred; the kernel carries a server-owned `season_id` only.
- Server-proven failure before gameplay, attempt reversal, and explicit abandon terminal semantics need a bounded product/storage decision.
- Fairness reveal payload, active-secret lifecycle, durable JSON/MySQL/PostgreSQL transaction schema, concurrency protocol, recovery, API schemas, privacy projections, leaderboards, Admin telemetry, and production rule registration remain future foundation slices.
- Production formula registration requires owning-game golden vectors and clean-process evidence bound to the exact rules version; this kernel validates only the bounded canonical result shape.
- Future leaf formula contradictions or missing numeric rules remain leaf blockers; core does not correct them implicitly.
- The implementation lease covers only the four worker-owned paths; stop before shared metadata, permanent IDs, routes/contracts, adapters, or activation.

## Handback

- Expected PR summary: inactive provider-neutral Challenge Points transition kernel, focused hostile/invariant tests, explicit structural wallet separation, calibrated formula-certification ownership, and a complete list of deferred activation/storage/API decisions.
- PR state: draft; no merge or auto-merge by this worker.
- Exact base: `8cce66851edef2a97350e39be661e5e2f1808b6c`, tree `7256a1ec26f9eb24a8cc2c36bdc08ca1918369ff`.
- Evidence: focused test counts, syntax checks, validators, exact head/tree, clean scoped diff, and hosted CI status.
- Merge recommendation: only after independent review confirms allocated requirements, module revisions, shared registration, exact-head checks, and the intentionally inactive boundary.
