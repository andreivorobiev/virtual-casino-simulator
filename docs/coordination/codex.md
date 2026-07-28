# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T03:36:00Z.

## Current branch / active Codex work

- Codex Worker B owns `codex/433-rule-schema-catalog-gate` from exact terminal-green v0.9.5.21 main `aaf46a6d`.
- Scope is the inert descriptor/governance foundation for #433: current settings-route schemas, pure schema validation, catalog route/default parity, and listener-free regression proof.
- This slice does not change router dispatch, persisted state, OpenAPI, compatibility matrices, frozen v1 behavior, gameplay, or browser UI.
- PR #474 branch/worktree/process cleanup is complete; its accepted head is contained in protected main and no #474 refs remain.

## Live queue snapshot

- Protected main and deployed immutable v0.9.5.21 are exact `aaf46a6d86c0b5f1529b21f15810f2f98a0eaad4`.
- #433 is `P1` / `stack-rank:071` and had no assignee, claim comment, or open PR before Worker B claimed the bounded foundation.
- #350 is an umbrella routed to #351/#352; #432/#434/#441 are lower-ranked P2 items.
- #450 remains excluded. Worker A/#467 and Claude PRs #473/#465/#460/#454/#453 plus CI PR #470 remain no-touch except acknowledged shared metadata that must be re-read at handoff.

## Requirement / TEST ID claims

- No existing identifier is deleted or reused.
- `SEC-014` is reserved for #433 because permanent `SEC-012` already belongs to game entropy and `SEC-013` belongs to client-log URL sanitization.
- `TEST-139` remains reserved for Claude #453 and `TEST-142` for Worker A/#467; this #433 slice does not claim either.
- Merged `SESSION-008` and `TEST-143` remain unchanged.
- Worker A/#467 now claims tests/docs `1.64.2`; #433 uses tests/docs `1.64.3` and tooling `1.21.6`, skipping #467/#450 tooling `1.21.5`.

## File claims / collision notes

- Substantive files: `casino/core/game_rules.py`, `casino/games/registry.py`, `scripts/validate_game_catalog.py`, `modules/{blackjack,baccarat,roulette}.json`, and `tests/games/test_game_rule_schema.py`.
- Shared governance files: requirements, generated requirements, Codex coordination status/log, module descriptor versions, and `modules/module-manifest.json`.
- No `.github/workflows`, `tests/run_tests.py`, Worker A harness/storage files, Claude game economics/Admin/UI files, production, provider, DNS, ingress, secrets, signup, OAuth, mail, or invitation files are in scope.

## Decisions / handbacks

- The descriptors mirror only domains already merged under #404; no new payout or table-rule policy is invented.
- Baccarat's descriptor records its existing cut-card fallback of 14 without changing engine state or response projection.
- Internal rule schemas are explicitly withheld from public catalog payloads.
- Runtime descriptor enforcement, state repair, handler-list removal, and contract/matrix publication remain later #433 slices requiring separate current-main review.
