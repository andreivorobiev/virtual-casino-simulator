# OCI PostgreSQL restricted preview

Issue #1078 owns one additional Casino deployment at `https://preview.tiltseven.com`. It uses an OCI Ampere A1 instance, native PostgreSQL 16, the same immutable GitHub Release channel as the existing service, and Midphase/StackDNS only for the explicit DNS record. The existing `casino.tiltseven.com` MySQL deployment is independent and must remain available throughout setup and rollback.

## Fixed topology and cost boundary

- One OCI `VM.Standard.A1.Flex` instance is created only inside the existing `casino-preview` compartment and only within available no-new-cost capacity. Do not select a paid shape, paid public IP, load balancer, managed database, NAT gateway, or paid storage fallback.
- Nginx is the only public service on TCP 80 and 443. SSH is restricted to the current reviewed operator source. PostgreSQL 5432, Gunicorn 8765, and the recovery listener 8877 are private and bind only to `127.0.0.1`.
- Midphase/StackDNS owns an explicit `preview.tiltseven.com` A record. It does not run Python, PostgreSQL, Gunicorn, or the release poller.
- The preview retains manual invitations, disabled public signup, disabled live OAuth, authenticated Admin, and the standard same-origin security boundary.

If OCI cannot supply the reviewed no-new-cost capacity, stop. Do not silently create a chargeable substitute. Oracle may reclaim idle Always Free compute, so this preview needs normal uptime monitoring and is not a replacement for the existing production service.

## Immutable release and host preparation

Use only a published release whose `release-manifest.json`, checksum file, archive, tag, and source commit verify under the normal release tooling. Install the optional PostgreSQL dependency into the dedicated application virtual environment. Keep the archive extraction immutable beneath `/opt/casino/releases/<commit>` and select it through `/opt/casino/current`.

Install the checked systemd service, release-poller service and timer, edge-monitor service and timer, and the rendered `deploy/nginx/casino-postgres-preview.conf.template`. Set this non-secret poller override in `/etc/casino/release-poller.env`:

```text
CASINO_EDGE_POLICY_PATH=/opt/casino/current/deploy/edge/postgres-preview.json
```

The root-owned `/etc/casino/casino.env` selects `CASINO_STORAGE_PROVIDER=postgres`, uses the DML-only runtime role, and keeps the database host literal `127.0.0.1`. The application unit strips every migration credential, marker, binding key, and release SHA before Gunicorn starts.

## One-time empty-target bootstrap

Generate the administrator, migration, and runtime secrets outside Git. Load the two role passwords through the environment and execute `deploy/postgres/create-target.sql` once through local `psql` as the cluster administrator. The script refuses existing target identities, creates distinct non-superuser roles, creates `virtual_casino` under `casino_migrate`, and removes public database/schema access.

Load the guarded production migration variables from [`postgres_migrations.md`](postgres_migrations.md), including the exact published release commit and an independent target-binding key. Run:

```text
python scripts/postgres_migrate.py dry-run --release-manifest /root/release-manifest.json
python scripts/postgres_migrate.py apply --release-manifest /root/release-manifest.json
```

Production apply refuses any pre-existing table or migration state and is not repeatable. After the exact clean schema-five result, run `deploy/postgres/finalize-runtime-grants.sql` locally as the migration role. Remove every migration variable and secret, then prove the DML-only runtime boundary with:

```text
python scripts/postgres_runtime_check.py
```

Do not grant the runtime role schema creation, DDL, grant management, database creation, role creation, replication, row-security bypass, or superuser authority.

## DNS, TLS, and activation

Create the explicit StackDNS A record only after the OCI public address and source-restricted firewall are verified. Wait for authoritative DNS to return only the intended address, render the nginx placeholders into a root-owned candidate, and require `nginx -t` before enabling it. Issue the certificate for `preview.tiltseven.com` through HTTP-01 only after DNS convergence; a failed issuance must leave the current nginx configuration intact.

Start PostgreSQL, then Casino, nginx, the release poller, and the edge monitor. The PostgreSQL edge policy requires exact HTTPS liveness, authenticated readiness reporting `storage_provider=postgres`, authenticated Admin Operations readiness, reviewed response headers, and a certificate with at least fourteen days remaining.

## Backup, restore, and rollback

Before enrollment, create an encrypted off-instance PostgreSQL custom-format backup and verify its checksum. Restore that backup into a fresh isolated loopback database under new synthetic roles, run the read-only runtime compatibility check, and remove the restore target. Never restore over the active database.

The first PostgreSQL preview release has no older PostgreSQL-capable application predecessor. Its rollback is therefore stop-and-withdraw only: stop Casino and its timers, disable the preview nginx site, preserve the database and evidence, and remove the explicit DNS record if exposure must end. Never repoint this PostgreSQL schema to the older MySQL-only application release and never reverse schema DDL. Later application rollback is allowed only after an immutable PostgreSQL-compatible predecessor release has been retained and tested against the same clean schema.

## Acceptance evidence

Retain only sanitized evidence: exact release tag, source commit and manifest digest; OCI resource identifiers without credentials; authoritative DNS answers; firewall port inventory; PostgreSQL version and clean schema number; runtime provider; three edge probe results; certificate lifetime; service active states; encrypted backup checksum; isolated restore result; and cleanup status. Do not retain passwords, binding keys, bearer tokens, cookies, connection strings, SQL payloads, user data, or raw provider exceptions.
