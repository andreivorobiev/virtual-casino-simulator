# Production application service

Private invitation enrollment remains disabled by default and is governed by [the invitation enrollment runbook](invitation_enrollment.md). Repository merge does not authorize live enrollment, mail/provider release, deployment, or public signup.

Invite-only Google and Facebook OAuth also remains disabled by default and requires both provider configuration and a separate provider-specific network-release latch before any adapter can be constructed. Repository merge and deployment authorize no provider console, credentials, callback registration, DNS, public signup, or unrestricted exposure. See [the OAuth runbook](oauth_invite_only.md) for readiness, privacy, recovery, and rollback requirements.

Requirement `CORE-023` defines the repository-side production process for the restricted-preview topology. This packet does not install, enable, start, or expose any host service.

## Supported topology

- Gunicorn runs one `gthread` worker with two threads and imports `casino.wsgi:application`.
- `deploy/gunicorn.conf.py` fixes the interface to `127.0.0.1`; only the non-secret port may be changed for isolated tests.
- The Python development server in `casino.app` remains a local launcher and is not part of the production invocation.
- A future edge proxy may send same-origin requests to this loopback listener only after the separate edge gate is approved.
- The adapter trusts forwarding metadata only from the one configured loopback peer under the exact paired-header policy in `docs/restricted_preview_security.md`. Issue #203 supplies repository policy and tests only; it does not install or configure that proxy.

## Static asset cache contract

Requirement `CORE-026` defines one cache policy for the local development/test adapter and the production WSGI adapter: every HTML, CSS, localization, image, and lazy JavaScript response carries `Cache-Control: no-store`. API and liveness responses retain the same existing no-store behavior from `CORE-013`.

The policy intentionally favors current-source correctness over browser reuse for this private simulator. A document reload must obtain the exact current `web/index.html` bytes, and a later lazy game import must obtain the exact current module bytes from the same checkout or immutable release. `BR-STATIC-CACHE-001` exercises the development adapter through Chromium with a real reload and repeated lazy-module fetches. `SERVICE-WSGI-001` exercises the production adapter directly without opening a listener. Neither adapter may introduce a different static cache policy independently.

## Immutable release layout

Each verified artifact is extracted to `/opt/casino/releases/<release-sha>`. The `/opt/casino/current` path is an atomic symlink to exactly one retained release, and the virtual environment is kept separately at `/opt/casino/venv`. Release directories are read-only to the `casino` service identity.

Mutable state is never linked into or created beneath a release. The tracked service template permits writes only to `/var/lib/casino` and `/var/log/casino`, so its environment file must set `CASINO_DATA_DIR=/var/lib/casino` and `CASINO_LOG_DIR=/var/log/casino`. A different external root requires a separately reviewed systemd drop-in whose `ReadWritePaths` exactly matches the environment setting; changing the environment alone will fail closed under `ProtectSystem=strict`.

A root-managed environment file at `/etc/casino/casino.env` supplies runtime configuration, including:

- `CASINO_DEPLOYMENT_MODE=production`;
- the complete restricted-preview security settings documented in `docs/restricted_preview_security.md`;
- the exact external `CASINO_DATA_DIR=/var/lib/casino` and `CASINO_LOG_DIR=/var/log/casino` values authorized by the tracked template;
- the selected storage provider and its connection settings;
- unique bootstrap Admin settings;
- a unique external `CASINO_TOKEN_DIGEST_KEY` of at least 32 bytes, distinct from every provider or bootstrap credential;
- a separate unique external `CASINO_MAIL_DIGEST_KEY` of at least 32 bytes, even while transactional mail remains disabled;
- every credential required by the selected provider.

Transactional mail is additionally fail-closed. `CASINO_MAIL_ENABLED` and the independent `CASINO_MAIL_NETWORK_ENABLED` release switch both default to false; setting only one can never reach the provider adapter. Provider selection, sender identity, canonical origin, verified domain, credentials, and either release switch must not be changed as part of a normal application deployment. Follow `docs/transactional_mail_runbook.md` and obtain the separately durable live-release authority before any such operation.

Deployment-only `CASINO_MYSQL_MIGRATION_*` variables are never part of this file. The tracked unit unsets them defensively, and `docs/mysql_migrations.md` requires the operator to load them only for the proof-gated migration command and remove them before application startup.

The environment file is not a release artifact, must never be committed, and should be readable only by the service manager. Secret values must not appear in the unit, process arguments, screenshots, test output, or release evidence.

## Supervised lifecycle

The tracked template at `deploy/systemd/casino.service` provides the service identity, environment-file guard, atomic-symlink guard, immutable working directory, writable-root allowlist, restart policy, bounded graceful stop, capability removal, and journald routing. The production command is:

```text
/opt/casino/venv/bin/gunicorn --config /opt/casino/current/deploy/gunicorn.conf.py casino.wsgi:application
```

The adapter validates explicit production mode, external mutable roots, and non-default bootstrap settings before initializing storage. A configuration failure therefore prevents a healthy worker from accepting requests. Liveness remains anonymous and sanitized at `/healthz`; readiness policy remains the accepted authenticated `/readyz` behavior from issue #72.

## Candidate validation

`TEST-046` and `TEST-068` exercise the WSGI adapter directly without a socket and run the packaged production command from a clean extracted release on an operating-system-assigned loopback port. The copied-release smoke proves:

1. non-loopback configuration is absent from the supported invocation;
2. liveness succeeds without diagnostic detail;
3. a login and state mutation survive a graceful stop and restart using the same external temporary state root;
4. the tracked child exits within the bounded drain interval;
5. the exact temporary listener closes after each stop;
6. protected ports `8765` and `8877` are never selected by the smoke harness;
7. a configuration missing required external settings fails before worker readiness.

Issue #204 supplies the repository-only explicit migration and DDL-free runtime gate documented in `docs/mysql_migrations.md`. Application startup now performs a read-only exact-version and checksum check before bootstrap DML. The disposable MySQL 8.4 matrix proves restart persistence and runtime privilege denial, but this packet still performs no existing database, service, or schema mutation. A live apply remains held until the recovery and cutover gates release a target-specific packet.

## Application rollback boundary

Rollback selects the retained predecessor by replacing `/opt/casino/current` atomically and restarting the supervised service. It does not edit the retained release, copy mutable data into a release, or change database schema. The predecessor manifest must accept the already-applied MySQL migration version. If it does not, rollback is blocked; schema reversal remains prohibited without a separately approved migration and recovery packet.
# Disabled invite-only OAuth

The packaged service includes disabled-by-default Google and Facebook OAuth routes only for existing private-invite local-password accounts. Both provider configuration and the provider-specific network-release latch must be true before any provider adapter can be constructed. Repository merge and deployment keep both release latches false and do not authorize provider console, credential, callback, DNS, public-signup, or unrestricted-exposure work. See [oauth_invite_only.md](oauth_invite_only.md) for readiness, privacy, recovery, and rollback requirements.
