# Production CI/CD runbook

This is the plain-English operating note for Casino production deploys.

## Goal

Every protected `main` merge should automatically become the production release. A human should not have to rebuild a package on a laptop, copy files by hand, or log into the browser just to prove the site is healthy.

The browser Admin login and the production monitor login are separate things. Browser login is for a person. The monitor credential is a server-owned bearer token used only by deployment health checks.

Packaged release numbers use the four-part scheme documented in [the release versioning policy](release_versioning.md). The current line is `0.9.5.71`; `0.9.6.0` remains reserved for a separately accepted product wave.

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
11. It runs the selected release's read-only `bridge-check-schema2` with command-scoped release-root imports and refuses cutover unless the database is exact clean checksum-valid schema `2`.
12. It validates that the root-managed monitor bearer matches the application-only SHA-256 digest without printing either value.
13. It writes `/etc/casino/release.env` with the exact `CASINO_BUILD_SHA`.
14. It atomically repoints `/opt/casino/current`.
15. It restarts the Casino service and reloads nginx.
16. It runs authenticated production readiness through `scripts/run_edge_monitor.py`, which strictly parses only the root-managed Authorization assignment and calls `scripts/edge_gate.py observe` without shell evaluation.
17. It proves the selector still resolves to the exact selected release and reruns that release's read-only exact-schema-two bridge check.
18. If a post-switch check fails, it rolls the application symlink back to the previous release. Database rollback is never automatic.

The bridge deployment invokes no migration command and changes no database schema, data, grant, account, secret, or server global. Both schema checks import `casino` and `scripts` from the exact selected immutable release rather than the upload staging directory or an assumed installed package.

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

v0.9.5.38 carries the accepted #430 Phase 0c JSON-provider recoverable game-action journal, immutable paid and zero-cost receipts, cross-process storage gate, and failure-atomic Admin reset boundary. It preserves the route-free provider-neutral contract while excluding schema-3, the MySQL composite transaction, routes, games, Slots adoption, ledger behavior, provider scaling, and all-provider atomicity claims. Its compatibility record retains exact immutable v0.9.5.37 as the application-only predecessor; MySQL remains at schema 2 and database rollback remains prohibited.

v0.9.5.46 carries the accepted bounded shared-wallet celebration and lifecycle slice from sole content PR #552 while retaining the #430 MySQL rollback-compatibility bridge. The latest server-owned wallet value remains authoritative; initial load and reduced motion stay undecorated, while normal ordinary and threshold gains use bounded transient resources with explicit overlap, navigation, pagehide, BFCache, and remount ownership. Qualification aligns the reconstructed offline PWA document's event order and adds route-qualified Teen Patti mobile fixed-control clearance without changing product PWA behavior or game math. Original PR #521 is ancestry-reachable through shell `f1b1826d` rather than a second content merge, and issue #74 remains OPEN at P1 and stack-rank 020 under durable comments `5147419893` and `5147420421`. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.45 as the application-only predecessor; database rollback remains prohibited. A later separately governed migration release may apply schema 3 only after backup, quiescence, grant and drift proof, and must retain a schema-3-capable predecessor.

v0.9.5.47 carries the accepted semantic game-color foundation from sole content PR #556 while retaining the #430 MySQL rollback-compatibility bridge. Shared application styling resolves real red, felt green, and metallic gold across four governed games without recoloring brand chrome or playing-card suits; the Color Wheel cascade and Keno fixture remain route-accurate. Qualification repairs only computed-style receipt identity and token-credit readiness ordering under existing assertions and timeouts. Original PR #481 is ancestry-reachable through shell `cf7ebbdd` rather than a second content merge, and issues #74 and #554 remain OPEN under durable comments `5148860461`, `5148860670`, and `5148860881`. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.46 as the application-only predecessor; database rollback remains prohibited. A later separately governed migration release may apply schema 3 only after backup, quiescence, grant and drift proof, and must retain a schema-3-capable predecessor.

v0.9.5.48 carries the accepted #555 task-1 README front-door and token-terminology enforcement slice from sole content PR #563 while retaining the #430 MySQL rollback-compatibility bridge. The prior per-release README status prose is archived verbatim, six durable design decisions lead the project front door, and the exact terminology validator repair is registered in the existing comment-density workflow with a focused unit oracle. Original PR #558 is ancestry-reachable through shell `93035ae1` rather than a second content merge, and issue #555 remains OPEN and incomplete under durable comments `5149895749`, `5149896533`, and `5149897511`. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.47 as the application-only predecessor; database rollback remains prohibited. A later separately governed migration release may apply schema 3 only after backup, quiescence, grant and drift proof, and must retain a schema-3-capable predecessor.

v0.9.5.49 carries the accepted #555 task-2 request-path architecture documentation and qualification slice from sole content PR #566 while retaining the #430 MySQL rollback-compatibility bridge. The bounded Mermaid diagram and caption document the existing path from both HTTP adapters through router sanitization, descriptor-owned game dispatch, server-side outcomes, ledger settlement, and JSON or MySQL storage without changing any runtime behavior. Original PR #559 is ancestry-reachable through main-identical shell `330c7b88` rather than a second content merge, and issue #555 remains OPEN and incomplete. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.48 as the application-only predecessor; database rollback remains prohibited. A later separately governed migration release may apply schema 3 only after backup, quiescence, grant and drift proof, and must retain a schema-3-capable predecessor.

v0.9.5.50 carries the accepted bounded reliability and Admin operations bundle from sole normal content PR #568 while retaining the #430 MySQL rollback-compatibility bridge. It includes guest-creation throttling, registered-session policy, commitment-safe Baccarat and Keno recovery, fixed-field Bingo economics, complete Andar Bahar test discovery, and owner-gated Admin diagnostics, economics, and session-policy surfaces. Main-identical shell `e4102242` preserves contributor ancestry without a second content import; issues #388, #430, #434, #456, and #555 remain OPEN and incomplete, and #450 remains excluded. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.49 as the application-only predecessor; database rollback remains prohibited. A later separately governed migration release may apply schema 3 only after backup, quiescence, grant and drift proof, and must retain a schema-3-capable predecessor.

v0.9.5.51 carries the accepted production-polish fixes from sole normal content PR #571 while retaining the #430 MySQL rollback-compatibility bridge. It keeps the Roulette betting board within the hosted desktop viewport, stops safe static GET assets from spending the API action rate budget, and exposes a privacy-safe unique active-session count for the lobby and footer. Issue #570 remains open until terminal production verification. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.50 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.52 carries the bounded restoration bundle from sole normal content PR #581: 28 branded game palettes, the guest-lifecycle window proof, and the Deuces Wild and Texas practice house-edge policies with their focused tests and contracts. Contributor PRs #573, #574, and #580 are ancestry-only inputs, not additional content merges. Issues #456 and #555 remain open and incomplete. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.51 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.53 carries the accepted wallet-timing and API-documentation packet from sole normal content PR #602. It exposes the committed wager debit immediately across all eighteen delayed-result browser games, refreshes the authoritative settled balance after reveal, and adds a read-only same-origin Swagger explorer for all 62 published OpenAPI contracts. It changes no wagering economics or frozen API behavior. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record declares rollback at unchanged schema 2 and retains exact immutable v0.9.5.52 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.54 is the immutable inventory-note correction for the same accepted #602 content. v0.9.5.53 was published but never activated after public audit found that its descriptive inventory note counted two test-only files that release packaging intentionally excludes. v0.9.5.54 records the exact 731-file deployable inventory and changes no product source. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.52 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.55 carries the accepted complete tracked-bug and merge-ticket-lifecycle packet from sole normal content PR #605. It resolves the seven concrete bug tickets that remained open after v0.9.5.54, preserves localized and accessibility behavior across the shell and affected games, and makes substantive pull requests fail CI unless they list delivered issues with native closing keywords. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.54 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.56 combines the accepted viewport-containment/action-stability packet from normal PR #609 with the phase-safe Autoplay rate-limit recovery from normal PR #608. It closes issues #607 and #555, preserves all 46 game routes inside governed viewport or designed-scroll boundaries, retains same-route scroll and focus across rerenders, and prevents a completed game action from being replayed while Autoplay retries temporary rate limits. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.55 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.57 packages the accepted P0 desktop bottom-edge containment fix from sole normal content PR #612. It closes issue #611 and keeps the complete Roulette betting board and Bingo card/call bay visible above the fixed footer at governed desktop viewports without changing mobile scrolling or game economics. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.56 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.58 packages the accepted play-control, guest-trial, and silent-audio packet from sole normal content PR #615. It closes issues #614, #616, #617, #618, and #619; keeps request limits owner-configurable and bounded, preserves same-route scroll/focus, grants fresh guest trials 10,000 play tokens behind an owner admission switch, and defaults all fresh/fallback audio channels to off while preserving explicit owner settings. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.57 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.59 packages the accepted catalog-wide settlement convergence from sole normal content PR #635. It closes issues #430 and #621 through #634; routes all 46 games through one replay-safe settlement interface, preserves existing game rules and token timing, and adds a static prevention gate against direct game ledger mutation. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.58 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.60 packages the accepted account and Admin completion from sole normal content PR #638. It closes issues #334, #351, #352, #378, and #388; adds recovery challenges, owner-role safeguards, personal settings, guest conversion readiness, and owner-controlled session policy while public signup, live OAuth, and provider network activity remain disabled. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.59 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.61 packages the accepted persistent-agent-memory PR #640 and performance/governance PR #642. It closes bounded issues #641 and #643; adds source-bound durable agent context, payload/frontend budget evidence, a 46-game multiprocess safety inventory, and deterministic game-suite discovery while leaving broader portfolio and external-readiness tickets open. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.60 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.62 packages the accepted row-scoped player-persistence PR #646. It closes issue #431; removes runtime whole-player-map rewrites, makes MySQL player loads read-only, and uses lock-correct insert-missing-only bootstrap behavior without changing schemas, games, settlements, or API envelopes. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.61 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.63 packages accepted descriptor-driven game-rule enforcement PR #649. It closes issue #433; mounts descriptor-owned settings coercion centrally, repairs invalid persisted settings, retires duplicated game rule domains, and generates request contracts plus authority bounds from the same descriptors without changing paytables, settlements, providers, or frozen response envelopes. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.62 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.64 packages the accepted provider action-index bridge from normal PR #652. It closes bounded issue #653 and advances umbrella #432; settlement recovery and Deuces Wild now resolve exact action identities through the JSON registry or MySQL unique index instead of million-row ledger scans, while the legacy JSON journal format remains rollback-compatible and #432 stays open for the later append-only write transition. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.63 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.65 packages accepted governance PR #656. It closes issue #434; game requirements now have descriptor-owned shards, the legacy aggregate is generated and fail-closed, and shared Python game-suite execution is descriptor-discovered without changing any runtime, API, settlement, paytable, or provider behavior. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.64 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.66 packages accepted performance PR #659. It closes bounded issue #660 while parent issue #323 remains open for production latency evidence; the frozen v1 API gains opt-in compact shell and Roulette play projections, complete legacy responses remain the default, and the Roulette client reuses one immutable catalog per wheel mode without changing money, state, settlement, paytable, or provider behavior. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.65 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.67 packages accepted provider-safety PR #663 and closes repository-controlled issue #333. Owner-only Google and Facebook operational switches remain default-off, independently gate adapter construction and availability, and authorize no provider traffic, public signup, public launch, credential, DNS, billing, game, money, or database change. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.66 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.68 packages accepted policy-gated social-signup PR #666 and closes repository-controlled issue #335. Google and Facebook signup create canonical accounts by immutable provider subject only after explicit acknowledgements and every independent policy, operational, and runtime gate passes; both methods, provider traffic, and public launch remain disabled by default, while #336 and #209 retain external evidence and launch authority. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.67 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.69 packages accepted append-only action-journal PR #669 and closes repository-controlled issue #432. The JSON provider appends one fsynced commit and one projection marker per new exactly-once action, incrementally observes cross-process tails, recovers pending identities only, fails closed on corrupt or conflicting records, and periodically compacts settled references below 200 bytes per action while retaining legacy snapshot readability. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.68 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.70 packages accepted file-header policy PR #672 and closes repository-controlled issue #441. First-party Python and JavaScript sources now carry governed copyright, SPDX, and substantive purpose headers; generated per-line filler comments are removed, meaningful rationale remains, and vendored Swagger assets remain byte-identical and excluded. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.69 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.71 packages accepted motion-quality PR #674 and closes repository-controlled issues #169 and #170. Roulette and Slots expose governed real-duration, autoplay, and reduced-motion profiles with deterministic phase ownership, safe route recovery, and scroll stability while preserving all game mathematics and settlement behavior. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.70 as the application-only predecessor; database rollback remains prohibited.

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

The release verifier authenticates the compatibility record's exact application-only, database-rollback-prohibited, retained-predecessor policy and requires the declared rollback schema to fit both candidate and predecessor runtime windows. The bridge must remain at exact schema `2` before and after activation; schema `3` is not live under this packet.

## Operator rule

Do not deploy unversioned protected `main` bytes by hand.

The production source of truth is the GitHub Release asset built from the exact protected-main commit. If a later protected-main commit should go live, create a new packaged version and let the production workflow publish and deploy it.
