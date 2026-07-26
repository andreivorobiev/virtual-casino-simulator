# Restricted-preview edge preparation

Requirements CORE-024, TOOL-005, and TEST-050 define the repository-only edge packet for issue #206. Nothing in this packet installs nginx, requests a certificate, changes DNS or firewall policy, enables a service or timer, opens a listener, deploys an application, or changes a database. Those actions remain held by issue #201 and the qualifying cutover approval.

## Topology contract

The complete frontend and API share the owner-confirmed HTTPS origin. nginx is the future TLS endpoint, while the supervised application remains reachable only at IPv4 loopback port 8765. MySQL and protected application ports 8765 and 8877 are never public. The future ingress allowlist contains only TCP 80 and 443; SSH remains source-restricted under the existing host policy.

The canonical machine-readable source is deploy/edge/restricted-preview.json. It preserves the #203 access boundary:

- manual invitations are the only enrollment path;
- public signup and live OAuth remain disabled;
- readiness and Admin Operations require an authenticated Admin session or the root-managed monitor bearer token;
- anonymous liveness exposes only the fixed live state;
- Host, X-Forwarded-For, and X-Forwarded-Proto are replaced with edge-owned values; and
- all other reviewed forwarding headers are cleared before the request reaches the application.

The policy also preserves the #204 and #205 boundaries. Edge rollback may replace only the immutable application release link and prevalidated nginx configuration. Database rollback is prohibited; migration and recovery remain separate proof-gated procedures.

## Inert templates

The deploy/nginx/casino.conf.template source contains the future HTTP-01 challenge route, exact HTTPS redirect, reviewed TLS placeholders, and loopback upstream. It deliberately contains placeholders rather than host-specific certificate or challenge paths. Rendering, installing, enabling, reloading, or testing a host configuration is a separately approved cutover action.

The deploy/acme/casino-renewal-hook.sh.template source validates nginx before reload. Certificate account creation, issuance, renewal configuration, and provider interaction are absent from this repository packet.

The deploy/systemd/casino-edge-monitor service and timer templates describe an unprivileged, read-only, bounded observation job. They are not enabled. The service reads its monitor authorization header from a root-managed external environment file and sends it only to the two policy-declared authenticated same-origin probes. Existing hosts may keep the legacy cookie variable during rollout, but the preferred credential is `CASINO_EDGE_MONITOR_AUTHORIZATION=Bearer ...`.

The deploy/rollback/casino-edge-rollback.sh.template source requires a complete operator-rendered nginx preflight configuration for the previous site source, switches application and edge links, restarts the supervised application, reloads nginx, and requires a sanitized observation. Any failed restart, reload, or observation restores both prior links and attempts to recover the pre-rollback processes. It never invokes MySQL, migrations, recovery, backup, DNS, ACME issuance, or firewall tooling.

## Non-mutating validation

Static validation performs repository reads and exact comparisons only. It opens no socket, executes no command, starts no process, and writes no file:

    python scripts/edge_gate.py validate

It fails closed when the origin, upstream, ingress, access, proxy, ACME, monitoring, rollback, template path, or security-significant template content differs from the reviewed contract. Its JSON output contains fixed check class names only.

The focused TEST-050 suite proves this listener-free behavior and negative cases:

    python -m unittest tests.edge_gate_tests -v

## Sanitized observation

The observe command is intended only after the approved HTTPS cutover has supplied `CASINO_EDGE_MONITOR_AUTHORIZATION` in the root-managed monitor environment:

    python scripts/edge_gate.py observe

Observation performs GET requests only. It verifies the default trusted TLS chain and hostname, checks whole remaining certificate days, reads at most 65,536 response bytes, and requires the #203 security headers. It sends no credential to anonymous liveness. It sends the external monitor header only to readiness and Admin Operations.

Success output contains only a fixed schema, pass state, UTC observation time, whole certificate days remaining, and three boolean check names. Failure output contains one fixed category. URLs, addresses, headers, response bodies, cookies, credentials, provider values, identifiers, and filesystem paths are never emitted.

## Separately gated cutover evidence

Repository acceptance does not claim that any live edge exists. A future #201 cutover packet must independently record, without secrets:

1. exact protected-main release artifact and rollback artifact provenance;
2. rendered-template review and nginx configuration preflight;
3. DNS and ACME authorization followed by verified HTTPS;
4. minimum firewall changes with application and database ports still closed publicly;
5. supervised service, liveness, authenticated readiness, Admin, session, CSRF, and persistence smoke;
6. certificate and sanitized observation evidence;
7. rollback and completed #205 restore evidence; and
8. final listener closure or allowlist proof.

Any failed security, schema, recovery, TLS, readiness, monitoring, or rollback gate stops cutover and restores the prior safe state. The packaged private-invite application-version bump and publication remain outside issue #206.
