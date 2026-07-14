# Issue #72 Operations foundation and stacked integration packet

Branch: `codex/issue-72-operations-foundation`

Base at implementation start: `0a1ebc2d7d034bb855ad968215bc61adcd18f4c9` (`origin/main`)

Issue: [#72](https://github.com/andreivorobiev/virtual-casino-simulator/issues/72)

Shared integration owner: [#77](https://github.com/andreivorobiev/virtual-casino-simulator/issues/77)

## Delivered isolated slice

- Operations module proposal revision `1.0.0` with no imports from game modules.
- Storage-free liveness with the canonical #104 packaged application version.
- Optional 7-to-40-character hexadecimal build SHA from the Operations-owned `CASINO_BUILD_SHA` deployment input; invalid, absent, or failing sources become `null`.
- JSON readiness through read-only validation of the bootstrapped primary document plus root read/write access, without a probe marker or returned path/content.
- MySQL readiness through a fresh read-only `SELECT 1`, with cursor and connection cleanup.
- Process-local, thread-safe, monotonic last-successful heartbeat tracking.
- Fixed `live` and `degraded` backend states; client-derived `down` semantics.
- Fixed secret-safe reason codes, a standard `OPERATIONS_NOT_READY` 503 path, and a final `OPERATIONS_PROBE_FAILED` boundary for unexpected service/clock/route failures.
- Additive OpenAPI v1 and compatibility records.
- Focused direct-router, service, provider, leak-boundary, contract, and ownership tests requiring no server listener.

## Requirements for the stacked integration

Existing IDs validated by the foundation:

- `CORE-011`: standard success/error envelopes.
- `CORE-012`: versioned v1 routes.
- `AUTH-004`: unauthenticated behavior cannot leak protected details.
- `STORAGE-001` and `STORAGE-003`: provider abstraction and local JSON fallback.
- `MYSQL-001`: configured MySQL provider readiness.
- `API-001`: compatible additive v1 evolution.
- `TEST-001`: free-port local test listener.
- `TEST-034`: disposable copied deployment.
- `TEST-038`: storage-provider coverage.
- `TEST-041` and `AUTH-006`: loopback preservation and fail-closed public startup.

#77 must verify availability and then permanently allocate, at minimum:

- `OPS-001`: storage-independent liveness with canonical app version and optional sanitized SHA.
- `OPS-002`: backend/storage readiness with allowlisted provider identity and fixed degraded reasons.
- `OPS-003`: heartbeat updates and retains the last successful dependency timestamp.
- `OPS-004`: Operations UI maps backend `live`/`degraded` and transport/staleness `down` without debug leakage.
- `OPS-005`: copied-deployment smoke records PID, loopback host, non-8765 port, response SHA, and cleanup evidence.
- One new `TEST-*` ID for healthy/degraded API, browser, and copied-deployment coverage if existing test IDs are not extended.

These proposed IDs are not permanent until they are written to the canonical requirement registry. They must not be reused if #77 finds a concurrent allocation.

## Exact shared file ownership map for #77

The foundation intentionally does not edit these shared files:

| Shared owner file | Required integration |
| --- | --- |
| `casino/app.py` | Import `register` as `register_operations` and call `register_operations(router)` inside `build_router()` beside the other module registrars. |
| `casino/core/auth.py` | Add exactly the three Operations probe paths to `PUBLIC_API_PATHS`; do not make any Admin route public. |
| `modules/module-manifest.json` | Promote `operations.module.proposal.json` to `modules/operations.json`, add `operations: 1.0.0`, and recompute every directly affected shared module revision from the integration base. |
| `docs/requirements/requirements.json` | Allocate permanent Operations and test IDs, evidence mappings, statuses, and issue notes. |
| `docs/requirements/requirements_generated.md` | Regenerate with `scripts/generate_docs.py`; never hand-edit. |
| `contracts/compatibility/module-api-matrix.json` | Register `operations.v1.yaml` under Operations and contracts ownership as required by current policy. |
| `contracts/compatibility/contract-digests.json` | Add the exact SHA-256 digest generated from the accepted Operations OpenAPI file. |
| `scripts/validate_contracts.py` | Discover and validate the Operations contract without a new duplicated endpoint allowlist if a descriptor-driven seam is available. |
| `tests/run_tests.py` | Add real-HTTP healthy/degraded envelope checks and explicit public unauthenticated access checks. |
| `web/admin.html`, `web/admin.js`, shared styles | Add the Operations section without exposing raw probe fields or debug tooling. |
| `web/i18n/en-US/admin.json`, `web/i18n/ru-RU/admin.json` | Add complete localized status, reason, and timestamp copy. |
| `tests/visual/visual_matrix.json` | Extend the Admin surface with the Operations states and evidence gates below. |

Do not redesign `casino/module_versions.py`. Operations already consumes `APP_VERSION`; the merged interface has no SHA field. Do not use `SOURCE_BASELINE_VERSION` as build identity and do not shell out to Git at runtime.

## Acceptance tests for #77

1. Unauthenticated liveness returns HTTP 200 with the standard `ok/data` envelope, canonical `app_version`, nullable validated SHA, and no storage call.
2. Healthy JSON readiness and heartbeat return HTTP 200, `status=live`, `ready=true`, provider `json`, no reasons, and advancing success timestamps.
3. Healthy MySQL readiness performs a live constant query, returns provider `mysql`, and closes its resources.
4. A post-start storage outage returns HTTP 503 with `ok=false`, code `OPERATIONS_NOT_READY`, `status=degraded`, the prior successful timestamp, and only an approved reason code.
5. Injected exceptions containing passwords, tokens, DSNs, hosts, database names, filesystem paths, request IDs, and debug identifiers are absent from serialized responses and browser copy.
6. Normal authenticated and unauthenticated game/auth behavior is unchanged, proving the additive v1 contract does not alter frozen endpoints.
7. Admin renders live, degraded, and client-derived down states in English and Russian using text plus a non-color signal.
8. Copied-deployment smoke starts only on `127.0.0.1` with a recorded dynamically allocated non-8765 port, records child PID and expected SHA, probes all three endpoints, stops the tracked child, and verifies the port is closed.

## Proposed visual matrix extension

- Surface: existing `admin`
- Route: `/admin`
- Selector: an Operations-owned stable `data-testid`
- States: `operations_live`, `operations_degraded`, `operations_down`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`
- Gates: `VIS-COPY-001`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`
- Evidence: branch-current `after_pass` images only

The UI must not display internal field names, resource keys, provider error text, or raw timestamps without localized formatting. Color cannot be the only live/degraded/down signal.

## Version and release impact

- Packaged application release impact: None; remains the canonical top-level release unless formal release work is separately authorized.
- Isolated Operations module proposal: `1.0.0`.
- Expected shared integration bumps: recompute on the accepted #77 base rather than applying stale reservations from this packet.
- Formal release notes/artifact: not in this worker scope.

## Current intentional blockers

- The preserved `operations.module.proposal.json` remains outside central module discovery, so `scripts/validate_versions.py` passes without requiring a forbidden aggregate-manifest edit. #77 must promote the proposal and register `operations: 1.0.0` together during serialized integration.
- The routes are not reachable through the real application until #77 registers them.
- The paths are not public until #77 updates the shared auth allowlist.
- Permanent requirements, contract digest/matrix discovery, central API/browser tests, Admin UI/i18n, visual evidence, and copied-deployment smoke remain unimplemented here.

No listener is required for the isolated validation plan. Port 8765 and the user's active Casino session must remain untouched throughout integration.
