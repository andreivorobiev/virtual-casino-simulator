# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T08:40:06Z.

## Current branch / active Codex work

- Immutable v0.9.5.23 is terminal green at exact protected main `098d2f3719d01d171a875c991c8537ecff07e27f`.
- Worker B owns `codex/433-rule-coercion-core`, rebased from that exact main, for a second runtime-inert #433 foundation slice.
- The branch adds only internal descriptor lookup, pure settings-value coercion, and listener-free regression tests. It does not mount the helper in the router or change any request, state, contract, game, Admin, or browser behavior.
- The branch remains draft-only. Codex must not merge, release, or deploy it in this lane.

## Live queue snapshot

- #470 is merged and deployed; its event-scoped cancellation, four Long Suite 100 shards, aggregate gate, workflow changes, tooling `1.21.7`, and v0.9.5.23 release metadata are preserved.
- #433 is the highest-priority clean Workstream 5 lane at P1 / stack rank 071.
- Runtime enforcement remains blocked on explicit owner decisions about frozen-v1 narrowing, Baccarat route/rule scope, and read-side state repair.
- #450 remains held and excluded. Worker A/#467 and Claude PRs #473/#465/#460/#454/#453 are no-touch except shared metadata re-read before handoff.

## Requirement / version claims

- No permanent identifier is created, deleted, or reused.
- This slice reuses merged `SEC-014`; it allocates no new `TEST-*` identifier.
- `TEST-139` remains reserved for Claude #453 and `TEST-142` remains reserved for Worker A/#467.
- Protected main owns tests/docs `1.64.6`, and open #460 owns `1.64.7`; this branch therefore allocates core `9.27.2`, tests `1.64.8`, and docs `1.64.8`. Application stays `9.53.10` / packaged v0.9.5.23, contracts stay `1.49.4`, and tooling stays `1.21.7`.

## File claims / collision notes

- Substantive files: `casino/core/game_rules.py` and `tests/games/test_game_rule_schema.py`.
- Shared governance files: `docs/requirements/requirements.json`, its generated view, `docs/game_catalog_governance.md`, Codex coordination status/log, `modules/{core,tests,docs}.json`, and `modules/module-manifest.json`.
- No substantive file overlaps #467, #450, or any open Claude branch. No `.github/workflows`, `tests/run_tests.py`, Worker A harness/storage files, game economics/Admin/UI files, production, provider, DNS, ingress, secrets, signup, OAuth, mail, or invitation files are in scope.

## Decisions / handbacks

- Exact undeclared paths return the original request object unchanged.
- Exact descriptor-owned settings paths produce a separate mapping, canonicalize finite numeric values, require strict booleans and enums, and preserve unknown keys for the existing handler allowlist.
- The coercer never mutates caller-owned input and uses fixed, non-reflecting validation diagnostics.
- Runtime mounting, hand-written validator removal, frozen-contract changes, state repair, and Admin UI remain separately governed #433 scope.
