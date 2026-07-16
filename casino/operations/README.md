# Operations probe foundation

Issue: [#72](https://github.com/andreivorobiev/virtual-casino-simulator/issues/72)

This integrated module defines sanitized liveness, readiness, and Admin heartbeat behavior under the shared #77 route and authorization policy.

## Public probe contract

- `GET /healthz` is anonymous and returns only `{"status":"live"}` inside the standard success envelope. It does not construct storage or disclose metadata.
- `GET /readyz` requires an authenticated session, checks storage, and returns healthy data or a sanitized `OPERATIONS_NOT_READY` 503.
- `GET /api/v2/admin/operations` requires Admin authority and returns sanitized healthy or degraded heartbeat telemetry.

A responding healthy process reports `live`. A responding process with a failed required dependency reports `degraded`. Clients must infer `down` from a transport failure or stale heartbeat because a down process cannot return an API response.

Every successful readiness-equivalent check advances a process-local `last_successful_heartbeat_at` timestamp. A later failure retains the prior success. Restarting the process intentionally resets this in-memory timestamp.

## Build and dependency metadata

`casino.module_versions.APP_VERSION` remains the only packaged application release source. The Operations module does not parse the aggregate manifest, derive a release from a module revision, or use the historical source baseline.

The merged #104 interface has no commit-SHA accessor. Operations therefore accepts optional deployment provenance from `CASINO_BUILD_SHA`, validates it as 7 to 40 hexadecimal characters, and otherwise publishes `null`. Missing SHA is valid for local use and does not degrade readiness. The runtime never invokes Git or discovers checkout paths.

The JSON provider checks that its bootstrapped primary player document exists, is readable and valid, and that its storage root remains readable and writable; it never writes a probe marker or returns file contents or paths. MySQL uses a fresh `SELECT 1` connection for every dependency probe and closes the cursor and connection in all outcomes, so a cached schema-ready flag cannot hide lost database connectivity.

## Sanitization boundary

Public payloads are limited to:

- schema and probe names;
- `live` or `degraded` status;
- canonical packaged application version and optional validated SHA;
- `json`, `mysql`, or `unknown` provider identity;
- component pass/fail values;
- fixed degraded reason codes;
- checked and last-success timestamps.

Provider and build-source exceptions are consumed by the probe layer, and a final API boundary converts any remaining service, clock, or route failure before the application's generic exception handler can expose it. Responses never include raw errors, exception classes, credentials, tokens, DSNs, hosts, database names, internal paths, request IDs, or debug identifiers.

## Requirement and integration state

Permanent `OPS-001` through `OPS-005` and `TEST-044` map the integrated route policy, sanitized dependency behavior, heartbeat state, Admin EN/RU presentation, copied-deployment smoke, and listener cleanup.

Focused validation requires no listener:

```bash
python -m unittest discover -s tests/operations -p "test_*.py"
```
