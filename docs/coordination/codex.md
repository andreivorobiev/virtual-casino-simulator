# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T01:53:10Z.

## Current branch / active Codex work

- Codex Worker B owns `codex/351-session-control-core` from exact terminal-green v0.9.5.20 main `dc5a4274`.
- Scope is the route-free server-side #351 session-control foundation: persistent-account-only bounded inventory, stable one-way aliases, privacy-safe projections, and idempotent targeted or all-session revocation.
- Permanent claims `SESSION-008` and `TEST-143` were reserved durably on issue #351 before source mutation.
- No Admin route, browser UI, contract change, provider configuration, schema migration, production mutation, release, or deployment is included.

## Live queue snapshot

- Protected main and this branch base are exact `dc5a4274087ee3c1efc0a827dd8f9fa8559f0b51`.
- #433 is the highest-priority assigned issue but remains non-executable beyond its already-fixed acute defect because its durable adversarial review requires owner decisions.
- #350 is the parent policy epic and routes its implementation through #351.
- #351 is therefore the highest-ranked substantive actionable Workstream 5 item.
- Claude PR #460 owns `casino/admin.py` and `web/admin.js`; this Codex slice deliberately does not touch either file or add routes/UI.
- Newly opened Claude PR #473 has no session-control source overlap, but its head carries stale v0.9.5.16 shared versions and reuses `TEST-141`, which already belongs to the merged MySQL pool foundation; #473 must reconcile from current main and allocate a fresh permanent TEST ID before qualification.

## Requirement / TEST ID claims

- No existing identifier is deleted or reused.
- This branch claims `SESSION-008` for the server-side session-control behavior.
- This branch claims `TEST-143` for its listener-free isolated-provider evidence.
- `TEST-139` remains reserved for the separately coordinated Claude #453 re-splice; open PR #467 already claims `TEST-142`.

## File claims / collision notes

- Source ownership is limited to `casino/core/auth.py` and new `tests/admin_session_control_tests.py`.
- Shared integration edits are limited to `tests/run_tests.py`, requirements/generated documentation, core/tests/docs versions, the module manifest, and Codex-owned coordination files.
- Codex is not touching Claude branches or #450/#453/#460/#465/#470, and is not duplicating #351 Admin UI work.

## Decisions / handbacks

- Session inventory returns at most one hundred rows and never returns raw session IDs, bearer or CSRF material, user IDs, IP addresses, or raw client strings.
- Targeted lookup uses a domain-separated stable SHA-256 alias truncated to sixteen lowercase hexadecimal characters.
- Guest trial principals and missing identities receive the same persistent-account validation failure.
- Complete session documents are validated before mutation; malformed evidence raises a fixed operator-recovery error and is not normalized or partially rewritten.
- PR #474's independent malformed-JSON blocker is repaired locally: strict state-store reads and mutations preserve MySQL transactions while syntactically invalid default-provider JSON raises the same fixed recovery error without backup, default substitution, normalization, or rewrite; exact original bytes remain unchanged across inventory and both revocation paths.
- PR #474 remains draft and merge-held until this fresh head completes all nine hosted checks with zero comments, reviews, and threads.
- Later #351 slices still own Admin authorization/routes, reason, recent reauthentication, request idempotency, durable audit history, separate Administrators UI, EN/RU browser/accessibility evidence, and additive v2 contracts.
