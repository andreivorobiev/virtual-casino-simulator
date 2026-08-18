# Repository Facts

These facts were read from protected main at commit `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`. They are navigation aids; requirements, contracts, manifests, workflows, and source code remain authoritative.

## Fact: Descriptor-driven game catalog

- Source path: `docs/game_catalog_governance.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Each playable game owns its catalog descriptor in `modules/<game-id>.json`; `casino.config.GAMES`, backend registration, the shell, validators, and long suites consume those descriptors instead of maintaining another game allowlist.

## Fact: Module ownership boundaries

- Source path: `AGENTS.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: A game may import shared core/errors and itself, never another game or bot strategy; shared browser code belongs in `web/core/`, and `/api/v1` remains frozen except for backward-compatible optional additions.

## Fact: Exactly-once settlement boundary

- Source path: `docs/settlement_interface.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: All 46 game backends converge on `GameSettlementGateway`, which delegates token movement to `SettlementAdapter` and storage-atomic `debit_once` or `credit_once`; exact retries replay and changed reuse fails closed.

## Fact: Direct game ledger mutation is prohibited

- Source path: `scripts/validate_module_boundaries.py`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: The boundary gate rejects game imports of the legacy ledger boundary and direct game calls to debit, credit, debit-once, or credit-once functions.

## Fact: Storage provider abstraction

- Source path: `casino/core/storage/__init__.py`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: `StorageProvider` is the persistence boundary; JSON is the default provider and MySQL is selected explicitly, with both providers preserving the same users, sessions, player, document, history, ledger, and replay-safe action semantics.

## Fact: Contract locations and response envelopes

- Source path: `AGENTS.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: API specifications live under `contracts/openapi/`, compatibility evidence lives under `contracts/compatibility/`, and responses use the standard `{ ok, data }` or `{ ok, error }` envelope.

## Fact: Version authority

- Source path: `modules/module-manifest.json`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: The aggregate manifest is the canonical packaged-application and independent-module version interface; module-specific ownership and paths remain in `modules/*.json`.

## Fact: Release artifact construction

- Source path: `docs/release_artifacts.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: A formal release is built from an exact commit into an archive, manifest, and checksums set, includes rollback compatibility, and is verified before immutable publication.

## Fact: Production release flow

- Source path: `docs/production_cicd_runbook.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Protected-main merge, unique release publication, and trusted fail-closed activation are serialized; a failed or skipped activation is not deployment success and requires exact-state diagnosis before another attempt.

## Fact: Agent role boundaries

- Source path: `AGENTS.md`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Claude may implement and prepare pull requests but may not merge; Codex coordinates shared integration, performs independent review, and is the sole repository merge executor without bypassing other safety gates.

## Fact: Browser Tests gate

- Source path: `.github/workflows/browser-tests.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means affected-game detection, one or more browser shards, exact shard aggregation, or an explicitly selected formal browser qualification did not prove the requested browser surface.

## Fact: CI gate

- Source path: `.github/workflows/ci.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means core compilation, rules, lifecycle, storage/MySQL, API, catalog, requirements, versions, per-game Python, or frontend validation did not pass as one coherent repository state.

## Fact: Codex Review Placeholder gate

- Source path: `.github/workflows/codex-review.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: This workflow currently proves only that the placeholder job ran; it does not replace an actual independent code review or owner policy.

## Fact: Comment Density gate

- Source path: `.github/workflows/comment-density.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means executable comment coverage fell below policy or prohibited token terminology was introduced.

## Fact: Contract Tests gate

- Source path: `.github/workflows/contract-tests.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means OpenAPI, compatibility, authority, or related contract surfaces no longer validate together.

## Fact: Production Deploy gate

- Source path: `.github/workflows/deploy-production.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means immutable release resolution, artifact publication/verification, transfer, activation, or production verification failed; the failure must not be interpreted as a successful live deployment.

## Fact: Docs gate

- Source path: `.github/workflows/docs.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means a generated documentation surface differs from its canonical source.

## Fact: Long Suite 100 gate

- Source path: `.github/workflows/long-suite-100.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means a mandatory long-suite shard, Slots economics proof, Keno economics proof, artifact verification, or aggregate result failed.

## Fact: Long Suite Soak workflow

- Source path: `.github/workflows/long-suite-soak.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means the manually selected soak shard or its evidence upload did not complete; this manual workflow is not a substitute for the mandatory pull-request Long Suite 100 gate.

## Fact: Module Boundary Tests gate

- Source path: `.github/workflows/module-boundaries.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means a forbidden backend/frontend dependency or legacy direct game-money boundary was detected.

## Fact: Release Candidate gate

- Source path: `.github/workflows/release.yml`
- Source commit: `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`
- Stable fact: Failure means candidate construction, predecessor resolution, deterministic evidence, rollback metadata, or immutable publication eligibility did not validate for the exact source.
