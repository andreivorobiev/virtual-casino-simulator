# Production application service

Requirement `CORE-023` defines the repository-side production process for the restricted-preview topology. This packet does not install, enable, start, or expose any host service.

## Supported topology

- Gunicorn runs one `gthread` worker with two threads and imports `casino.wsgi:application`.
- `deploy/gunicorn.conf.py` fixes the interface to `127.0.0.1`; only the non-secret port may be changed for isolated tests.
- The Python development server in `casino.app` remains a local launcher and is not part of the production invocation.
- A future edge proxy may send same-origin requests to this loopback listener only after the separate security and edge gates are approved.
- The adapter uses the direct WSGI peer address and does not trust forwarded identity or scheme headers. Trusted-proxy policy belongs to issue #203.

## Immutable release layout

Each verified artifact is extracted to `/opt/casino/releases/<release-sha>`. The `/opt/casino/current` path is an atomic symlink to exactly one retained release, and the virtual environment is kept separately at `/opt/casino/venv`. Release directories are read-only to the `casino` service identity.

Mutable state is never linked into or created beneath a release. The tracked service template permits writes only to `/var/lib/casino` and `/var/log/casino`, so its environment file must set `CASINO_DATA_DIR=/var/lib/casino` and `CASINO_LOG_DIR=/var/log/casino`. A different external root requires a separately reviewed systemd drop-in whose `ReadWritePaths` exactly matches the environment setting; changing the environment alone will fail closed under `ProtectSystem=strict`.

A root-managed environment file at `/etc/casino/casino.env` supplies runtime configuration, including:

- `CASINO_DEPLOYMENT_MODE=production`;
- the exact external `CASINO_DATA_DIR=/var/lib/casino` and `CASINO_LOG_DIR=/var/log/casino` values authorized by the tracked template;
- the selected storage provider and its connection settings;
- unique bootstrap Admin settings;
- every credential required by the selected provider.

The environment file is not a release artifact, must never be committed, and should be readable only by the service manager. Secret values must not appear in the unit, process arguments, screenshots, test output, or release evidence.

## Supervised lifecycle

The tracked template at `deploy/systemd/casino.service` provides the service identity, environment-file guard, atomic-symlink guard, immutable working directory, writable-root allowlist, restart policy, bounded graceful stop, capability removal, and journald routing. The production command is:

```text
/opt/casino/venv/bin/gunicorn --config /opt/casino/current/deploy/gunicorn.conf.py casino.wsgi:application
```

The adapter validates explicit production mode, external mutable roots, and non-default bootstrap settings before initializing storage. A configuration failure therefore prevents a healthy worker from accepting requests. Liveness remains anonymous and sanitized at `/healthz`; readiness policy remains the accepted authenticated `/readyz` behavior from issue #72.

## Candidate validation

`TEST-046` exercises the WSGI adapter directly without a socket and runs the packaged production command from a clean extracted release on an operating-system-assigned loopback port. The copied-release smoke proves:

1. non-loopback configuration is absent from the supported invocation;
2. liveness succeeds without diagnostic detail;
3. a login and state mutation survive a graceful stop and restart using the same external temporary state root;
4. the tracked child exits within the bounded drain interval;
5. the exact temporary listener closes after each stop;
6. protected ports `8765` and `8877` are never selected by the smoke harness;
7. a configuration missing required external settings fails before worker readiness.

MySQL restart persistence is deliberately deferred until issue #204 provides the explicit migration and DDL-free runtime schema gate. This packet performs no database or schema mutation.

## Application rollback boundary

Rollback selects the retained predecessor by replacing `/opt/casino/current` atomically and restarting the supervised service. It does not edit the retained release, copy mutable data into a release, or change database schema. A rollback that requires schema reversal is prohibited until a separately approved migration and recovery packet supplies that evidence.
