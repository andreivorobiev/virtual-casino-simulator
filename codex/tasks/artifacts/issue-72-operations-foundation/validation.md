# Issue #72 focused validation

Status: the Operations-owned foundation was refreshed onto main `f8c836163eab3dc92d83e7bf875ee963c11bddcf`. Focused listener-free checks pass; shared integration remains serialized under #77.

## Reconciled listener-free checks

- `python -m unittest discover -s tests/operations -p "test_*.py" -v` — PASS, 22 tests. Coverage includes storage-free liveness, canonical app version use, SHA sanitization, temporary JSON and MySQL readiness, retained heartbeat state, exact contract shapes, exception suppression, imported-error bypass prevention, and rejection of hostile, malformed, enum-spoofing, or impossible-timestamp returns.
- `python -m py_compile` for all Operations source and focused test files — PASS.
- `python verify_rules.py` — PASS, 32/32 checks.
- `python scripts/validate_contracts.py` — PASS for the eight centrally registered APIs and twelve catalog games; the isolated Operations OpenAPI file remains covered by its focused static contract test until #77 adds central discovery.
- `python scripts/validate_module_boundaries.py` — PASS.
- `python scripts/validate_requirements.py` — PASS for 445 current requirements.
- `python scripts/validate_versions.py` — PASS for packaged application 9.1.1 and 25 centrally registered module revisions while the Operations 1.0.0 proposal remains outside shared discovery.
- `python scripts/check_comment_density.py` — PASS at 99.9%; the eleven warnings are pre-existing machine-draw prerender lines outside issue #72.
- `python scripts/generate_docs.py --check` — PASS; generated requirements are current.
- `python scripts/validate_game_catalog.py` — PASS for all twelve current catalog games.
- `git diff --check` — PASS for the complete reconciled working diff.
- `git range-diff 727d5cf2..aac948be f8c83616..HEAD` — PASS; all three Operations commits remain patch-equivalent after the refresh.

## Pre-reconcile regression evidence

The pre-reconcile PR head `483823329094f99726b7b41cdcf54c8190351dca` passed GitHub API, Browser, Long Suite 100, contracts, docs, module boundaries, comment density, and placeholder review workflows. Its local bootstrap also passed 22 API cases, 31 browser cases, and copied-deployment Long Suite 100. These results establish branch continuity but are not represented as exact-head evidence for the rebased draft.

## Serialized shared-integration gates

- #77 must register the routes and choose an explicit authentication policy in shared `casino/app.py` and `casino/core/auth.py`. The current OpenAPI proposes `security: []` for all three probes, but issue #72 does not authorize anonymous access. Whether any probe is anonymous—including liveness-only versus all three—requires an explicit least-privilege decision; any endpoint exposed beyond a trusted monitor also needs bounded timeout plus ingress or rate-limit coverage.
- #77 must promote `operations.module.proposal.json` to `modules/operations.json`, add `operations: 1.0.0` to the aggregate manifest, assign permanent OPS requirements, update central contract digests/matrices and test discovery, and recompute directly affected shared module revisions.
- Admin UI, shared styles/i18n, the visual matrix, and Operations-specific copied-deployment smoke remain blocked on serialized integration.
- MySQL readiness currently depends on the shared provider connection behavior and has no Operations-owned connection timeout. A public or deployment gate must supply and test a bounded timeout before readiness or heartbeat is exposed to untrusted traffic.
- Public launch remains separately blocked on deployment terms/privacy, Secure-cookie and CSRF posture, OAuth provider verification, and OCI TLS, ingress, backup, and readiness evidence.

## Exact-head suites deferred to GitHub

Bootstrap, central API, browser, and Long Suite 100 were not rerun locally after reconciliation to avoid modifying repository runtime data or adding unnecessary local listener lifecycle risk. The pushed exact head must pass those GitHub workflows before handoff; their isolated runners remain the authoritative evidence.

## Listener safety

The reconciled checks above start no server and use only temporary storage. This review started no listener and did not use or stop ports 8765 or 8877.
