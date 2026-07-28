# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-28T11:10:48Z.

## Current branch / active Codex work

- Worker B owns issue #434 on `codex/434-complete-game-test-discovery`, based exactly on terminal-green v0.9.5.24 main `eb47dc03c58aff39f5392d51a822c3c87281624d`.
- The bounded slice restores all nine Andar Bahar Python tests to the existing CI discovery command and makes catalog validation reject any test-bearing game package that lacks its required `__init__.py` marker.
- #482 remains the serialized next merge target; this lane may publish a draft PR but must not ready, merge, release, or deploy.

## Live queue snapshot

- #350 is an umbrella routed to child issues and is not a standalone implementation lane.
- #432's safe ledger/action cache work is already merged under `STORAGE-009` and `TEST-135`; the remaining sidecar/provider plan retains its recorded rollback, parity, and payload decisions.
- #433 remains open for separately governed runtime mounting, frozen-v1/Baccarat scope, state repair, Admin, audit, and product decisions.
- #434 has no Claude or open-PR substantive owner; current CI discovery is already enabled, but Andar Bahar is the one catalog package silently skipped by the missing marker.
- #441 remains a proposal awaiting owner decisions on the replacement commenting policy and remediation scope.

## Requirement / version claims

- This #434 slice reuses permanent `AB-005`; it creates, deletes, and reuses no permanent requirement or `TEST-*` identifier.
- Current main owns tests/docs `1.64.9` and tooling `1.21.7`; Worker A #467 already claims tests/docs `1.64.10` and tooling `1.21.8`.
- This non-overlapping slice provisionally claims tests/docs `1.64.11` and tooling `1.21.9`, subject to exact-current-main recalculation after #482 serialization.

## File claims / collision notes

- Substantive files are limited to `tests/games/andar_bahar/__init__.py` and `scripts/validate_game_catalog.py`.
- Governed metadata is limited to the `AB-005` source/generated requirement records, tests/docs/tooling descriptors and manifest, plus Codex-owned coordination status and one append-only log entry.
- #482's `tests/run_tests.py` and `.github/workflows/browser-tests.yml`, #481's `web/styles.css`, Worker A #467 files, #450, Claude branches, game source, production, provider, DNS, billing, ingress, secrets, signup, OAuth, mail, and invitations are excluded.

## Decisions / handbacks

- The new validator gate is conditional: games with no direct `tests/games/<id>/test_*.py` files remain valid, while a test-bearing package without `__init__.py` fails with the exact missing path.
- No route, request, response, payout, game, Admin, browser, provider, or deployment behavior changes.
- Exact-head qualification and the draft PR handback remain pending; no merge action is authorized.
