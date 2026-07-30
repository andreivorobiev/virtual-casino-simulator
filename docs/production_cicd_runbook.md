# Production CI/CD runbook

This is the plain-English operating note for Casino production deploys.

## Goal

Every protected `main` merge should automatically become the production release. A human should not have to rebuild a package on a laptop, copy files by hand, or log into the browser just to prove the site is healthy.

The browser Admin login and the production monitor login are separate things. Browser login is for a person. The monitor credential is a server-owned bearer token used only by deployment health checks.

Packaged release numbers use the four-part scheme documented in [the release versioning policy](release_versioning.md). The current line is `0.9.5.36`; `0.9.6.0` is reserved for the next large Claude LPR.

## What happens after a merge

1. A push to protected `main` starts `.github/workflows/deploy-production.yml`.
2. The workflow reads the packaged application version from `modules/module-manifest.json`.
3. It builds the exact `v<version>` release from the protected-main commit.
4. It refuses to overwrite an existing tag that points at a different commit.
5. It resolves the exact predecessor from the current compatibility record, downloads only that immutable release manifest, and verifies the manifest's version, tag, and full source commit before packaging.
6. It publishes or reuses the matching GitHub Release assets.
7. It downloads those hosted assets back into the deployment job.
8. It connects to the production host over SSH.
9. It verifies checksums and the exact commit/tag on the host.
10. It installs the archive under `/opt/casino/releases/<commit-sha>`.
11. It validates that the root-managed monitor bearer matches the application-only SHA-256 digest without printing either value.
12. It writes `/etc/casino/release.env` with the exact `CASINO_BUILD_SHA`.
13. It atomically repoints `/opt/casino/current`.
14. It restarts the Casino service and reloads nginx.
15. It runs authenticated production readiness through `scripts/run_edge_monitor.py`, which strictly parses only the root-managed Authorization assignment and calls `scripts/edge_gate.py observe` without shell evaluation.
16. If the post-switch health check fails, it rolls the application symlink back to the previous release. Database rollback is never automatic.

## Required GitHub Actions secrets

These repository secrets must exist before automatic deployment can reach the server:

- `CASINO_DEPLOY_SSH_HOST`: production SSH host name or IP.
- `CASINO_DEPLOY_SSH_PORT`: SSH port. This is optional when the host uses `22`.
- `CASINO_DEPLOY_SSH_USER`: SSH user allowed to stage and activate the release.
- `CASINO_DEPLOY_SSH_KEY`: private SSH key for that user.
- `CASINO_DEPLOY_KNOWN_HOSTS`: pinned known-hosts entry for the production host.

Do not paste these values into tickets, PRs, screenshots, browser tests, or chat transcripts.

## Required production host settings

The host needs two monitor-token settings.

`/etc/casino/edge-monitor.env` should contain the bearer token used by deployment health checks:

```text
CASINO_EDGE_MONITOR_AUTHORIZATION=Bearer <random-root-managed-token>
```

`/etc/casino/casino.env` should contain only the SHA-256 digest of that token:

```text
CASINO_EDGE_MONITOR_TOKEN_SHA256=<sha256-of-token-only>
```

The raw token and the digest are intentionally split. The application never needs the raw token. The deployment monitor never needs an Admin browser session.

Validate the installed pair without opening a listener or printing either value:

```text
sudo /opt/casino/venv/bin/python /opt/casino/current/scripts/validate_monitor_config.py check --monitor-env /etc/casino/edge-monitor.env --application-env /etc/casino/casino.env
```

When an authorized root operator has intentionally installed or rotated the bearer, repair only the digest assignment from the separate bearer file. Before v0.9.5.8 is active, invoke the tool from the checksum-verified candidate release directory created during staging:

```text
sudo /opt/casino/venv/bin/python /opt/casino/releases/<verified-candidate-commit>/scripts/validate_monitor_config.py repair-digest --monitor-env /etc/casino/edge-monitor.env --application-env /etc/casino/casino.env
```

After v0.9.5.8 is active, `/opt/casino/current/scripts/validate_monitor_config.py` is the canonical path. Repair mode does not accept a token on the command line, does not print the token or digest, rejects symlink and duplicate-assignment destinations, atomically replaces the application file, and preserves its unrelated settings, ownership, and permissions. Restart the Casino service after an authorized repair, then run read-only `check` again. The production workflow itself never selects repair mode; a mismatch blocks cutover.

Starting with v0.9.5.9, production observation invokes `/opt/casino/current/scripts/run_edge_monitor.py`. The runner reads the exact `CASINO_EDGE_MONITOR_AUTHORIZATION` assignment with the same strict Python parser, validates its `Bearer <token>` shape, and passes that one value directly to the in-process edge observer. It never sources the root-managed file through Bash, expands shell syntax, mutates the file, or prints the credential.

The monitor token is accepted only for:

- `GET /readyz`
- `GET /api/v2/admin/operations`

It is rejected for normal account, gameplay, Admin mutation, wallet, ledger, and `/api/v2/me` routes.

## Recovery from the v0.9.5.6 through v0.9.5.8 release sequence

The immutable v0.9.5.6 release manifest selected a different historical release because the workflow inferred rollback from GitHub release ordering. v0.9.5.7 corrected predecessor selection but its package allowlist omitted `scripts/package_app.py` and `scripts/validate_monitor_config.py`, even though host activation invokes both from the extracted release. Neither immutable release is replaced in place. v0.9.5.8 keeps rollback provenance in `contracts/compatibility/app-0.9.5.8.json`, retains v0.9.5.5 as the application-only predecessor, packages every host-required script, and tests the archive against the host commands derived from the production workflow.

v0.9.5.9 preserves the fail-closed monitor configuration check before the application symlink moves and supersedes only the unsafe post-restart Bash sourcing boundary. Its compatibility record retains exact immutable v0.9.5.8 as the application-only predecessor. A root operator may use the explicit repair command above to align an intentionally rotated bearer and digest without exposing secret material.

v0.9.5.10 carries the accepted wallet-integrity and table-rule authority fixes without changing the deployment model. Its compatibility record retains exact immutable v0.9.5.9 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.11 carries the accepted frontend-safety and runtime-state hygiene fixes, including URL-bearer redaction, fail-closed Roulette feedback, persistent live-region semantics, reduced-motion guards, mobile feedback-control clearance, and the required static-shell cache rotation. Its compatibility record retains exact immutable v0.9.5.10 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.12 carries the accepted logout and Guest Trial request-integrity continuity fix. Its compatibility record retains exact immutable v0.9.5.11 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.13 carries the accepted settlement replay, browser request-integrity recovery, competitive Bingo, practice-game recovery, and governed-regression hardening bundle. Its compatibility record retains exact immutable v0.9.5.12 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.14 carries the accepted TiltSeven Neon Pit identity across the authenticated shell, lobby, PWA metadata, game palettes, and fixed transactional-mail subjects. Its compatibility record retains exact immutable v0.9.5.13 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.15 carries the accepted localized one-click Repeat bet control across the 43 catalog games that previously lacked it. Its compatibility record retains exact immutable v0.9.5.14 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.17 carries the accepted repository-owned nginx timing foundation for issue #323. Its compatibility record retains exact immutable v0.9.5.16 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.18 carries the accepted transactional, non-destructive MySQL player compatibility writer for issue #431. Its compatibility record retains exact immutable v0.9.5.17 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.19 carries the accepted bounded per-process MySQL connection lifecycle for issue #323. Its compatibility record retains exact immutable v0.9.5.18 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.21 carries the accepted privacy-safe Admin session-control core for issue #351. Its compatibility record retains exact immutable v0.9.5.20 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.22 carries the accepted runtime-inert game rule-schema and catalog-validation foundation for issue #433. Its compatibility record retains exact immutable v0.9.5.21 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.23 carries the accepted same-PR ordinary-check cancellation and four-shard mandatory Long Suite 100 acceleration for issue #468. Its compatibility record retains exact immutable v0.9.5.22 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.24 carries the accepted runtime-inert descriptor lookup and pure settings-value coercion foundation for issue #433. Its compatibility record retains exact immutable v0.9.5.23 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.25 carries the accepted deterministic Browser shard-state controller for issue #468. Its compatibility record retains exact immutable v0.9.5.24 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.26 carries the accepted governed Acey-Deucey spread-pricing repair for issue #408. Its compatibility record retains exact immutable v0.9.5.25 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.27 carries the accepted all-game desktop control-reachability gate for issue #221. Its compatibility record retains exact immutable v0.9.5.26 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.28 carries the accepted exact 138-browser full-catalog qualification and bounded concurrency-resilience repairs for issue #225. Its compatibility record retains exact immutable v0.9.5.27 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.29 carries the accepted route-free storage-atomic settlement-adapter foundation for issue #430. Its compatibility record retains exact immutable v0.9.5.28 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.30 carries the accepted fail-closed affected-game Browser qualification controller for issue #468 item 4. Its compatibility record retains exact immutable v0.9.5.29 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.31 carries the accepted independent Andar/Bahar side pricing for issue #409 while preserving the deprecated frozen-v1 integer return scalar. Its compatibility record retains exact immutable v0.9.5.30 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.32 carries the accepted exact visible-rank Hi-Lo pricing for issue #406 while preserving the deprecated frozen-v1 integer return scalar. Its compatibility record retains exact immutable v0.9.5.31 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.33 carries the accepted Slots economics-only slice for issue #471 through the established route, with an authoritative line-bet, scatter, four-free-spin, and paid-only progressive model. It makes no durable reservation, cross-process, exactly-once, or composite state-and-ledger claim. Its compatibility record retains exact immutable v0.9.5.32 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.34 carries the accepted Keno economics correction for issue #472 while preserving the frozen-v1 routes, envelopes, amount range, and float-plus-hundredth settlement law. Exact proof keeps every accepted pick-count and amount house-side, including the approved pick-one cent-rounding exception. Its compatibility record retains exact immutable v0.9.5.33 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.35 carries the accepted listener-free request-latency baseline for issue #323. The test-only harness measures fixed direct-WSGI route families against isolated JSON and disposable loopback MySQL providers, emits aggregate-only exact-source evidence, and changes no runtime, API, provider, pool-default, game, production, or deployment behavior. Its compatibility record retains exact immutable v0.9.5.34 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.36 carries the accepted #430 Phase 0b route-free atomic player game-state update foundation. The public core helper delegates one complete player-scoped document mutation to the existing JSON process-lock or MySQL row-locking transaction boundary without wiring any route or game. Its compatibility record retains exact immutable v0.9.5.35 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

## Historical first-rollout blocker

The CI/CD code merged and the exact `v9.5.6` release was published successfully.

The deployment job then stopped before touching production because the repository did not have the SSH deployment secrets listed above. The failed step was the SSH preparation step, so no files were uploaded, no service was restarted, and production remained unchanged.

That failure is expected until the secrets are installed. It is not related to a user browser login.

## One-time setup checklist

1. Add the five GitHub Actions secrets listed above.
2. Install or rotate the production monitor bearer token.
3. Store the bearer value in `/etc/casino/edge-monitor.env`.
4. Use the explicit `repair-digest` command above to derive the application digest without shell or log exposure.
5. Run read-only `check`.
6. Restart the service once after changing host environment files.
7. Rerun an eligible deployment path, or push the next protected-main release. Do not rerun an unchanged hosted job when the runner cannot reach source-restricted SSH ingress.

After this one-time setup is correct, future protected-main merges should roll out without manual browser login.

## Domain behavior

The governed production Casino origin is:

```text
https://casino.tiltseven.com
```

The older `casino.andvor.com` host is kept only as a compatibility redirect to the canonical TiltSeven origin. If a browser shows a certificate warning for `casino.tiltseven.com`, that is a TLS/DNS/edge configuration problem and deployment must stop until the certificate and redirect are correct.

## Rollback behavior

Rollback is application-only:

- repoint `/opt/casino/current` to the retained predecessor release;
- rewrite `/etc/casino/release.env` for that predecessor;
- restart the service;
- rerun readiness checks.

Rollback does not edit historical release directories. It does not roll back MySQL schema or mutable data. If the predecessor cannot run against the current schema, rollback is blocked and must be handled by a separately approved recovery plan.

## Operator rule

Do not deploy unversioned protected `main` bytes by hand.

The production source of truth is the GitHub Release asset built from the exact protected-main commit. If a later protected-main commit should go live, create a new packaged version and let the production workflow publish and deploy it.
