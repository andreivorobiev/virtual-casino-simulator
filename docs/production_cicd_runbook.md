# Production CI/CD runbook

This is the plain-English operating note for Casino production deploys.

## Goal

Every protected `main` merge should automatically become the production release. A human should not have to rebuild a package on a laptop, copy files by hand, or log into the browser just to prove the site is healthy.

The browser Admin login and the production monitor login are separate things. Browser login is for a person. The monitor credential is a server-owned bearer token used only by deployment health checks.

Packaged release numbers use the four-part scheme documented in [the release versioning policy](release_versioning.md). The current line is `0.9.5.79`; `0.9.6.0` remains reserved for a separately accepted product wave.

## What happens after a merge

1. A push to protected `main` starts `.github/workflows/deploy-production.yml`.
2. The workflow reads the packaged application version from `modules/module-manifest.json`.
3. It builds the exact `v<version>` release from the protected-main commit.
4. It refuses to overwrite an existing tag that points at a different commit.
5. It resolves the exact predecessor from the current compatibility record, downloads only that immutable release manifest, and verifies the manifest's version, tag, and full source commit before packaging.
6. It publishes or reuses the matching GitHub Release assets.
7. The workflow stops after hosted-asset verification. It owns publication and never opens an inbound production connection.
8. `casino-release-poller.timer` runs on the production host every five minutes and queries the public GitHub Releases API.
9. The poller compares the installed four-part version with the newest stable release and never downgrades.
10. For a newer release, the host downloads the exact archive, manifest, and checksum file directly from GitHub.
11. It verifies the canonical two-file checksum list, manifest artifact binding, exact tag and full source commit, complete packaged inventory, rollback declaration, monitor configuration, and the candidate's read-only `bridge-check-schema2` before any production selector or environment mutation.
12. It stages the archive under `/opt/casino/releases/<commit-sha>`, writes a candidate `release.env`, captures the current selector and fragment, then atomically repoints `/opt/casino/current`.
13. It restarts Casino, reloads nginx, rechecks exact schema `2`, runs the authenticated edge observation, and requires `/healthz` to be live plus `/readyz` to report the exact candidate application version and build SHA.
14. If any post-switch check fails, it restores the prior application symlink and `release.env`, restarts the service, re-observes the prior release, and writes a durable alarm. Database rollback is prohibited.
15. After success, it atomically refreshes `/usr/local/libexec/casino-release-poller` from the verified active release and clears the alarm.
16. The existing edge-monitor timer runs `check-lag`; a published release that remains newer than production for more than three poll intervals fails loudly and records `release_delivery_lag`.

The pull bridge invokes no migration command and changes no database schema, data, grant, account, provider, or server global. Candidate, activated, and rolled-back schema checks import `casino` and `scripts` from the exact selected immutable release. The retired GitHub-runner SSH leg is not an emergency fallback; issue #450 documents the unrevived self-hosted-runner alternative.

## Release API credential

The repository is public, so the poller normally requires no GitHub credential. If GitHub's anonymous API limit is insufficient, install one fine-grained token with access only to this repository's **Contents: read** and **Metadata: read** surfaces. The poller accepts it only through the root-managed optional `/etc/casino/release-poller.env` assignment:

```text
CASINO_GITHUB_RELEASE_TOKEN=<fine-grained-read-only-token>
```

The same file may override `CASINO_RELEASE_POLL_INTERVAL_SECONDS=300` and `CASINO_RELEASE_LAG_INTERVAL_MULTIPLIER=3`. Do not place a token on a command line or paste it into tickets, PRs, screenshots, browser tests, or chat transcripts. The production host needs no inbound GitHub Actions credential, SSH allowlist, deploy key, or runner agent.

## Owner host-install gate for #732

Repository acceptance stops before this section is executed. The owner performs this one host step only after a unique immutable release containing the poller is published and its three hosted assets pass the normal release verifier.

1. Download `checksums.txt`, `release-manifest.json`, and `virtual_casino_simulator_package.zip` from that exact GitHub Release into one new root-owned temporary directory. Do not use branch, source-archive, or Actions-artifact bytes.
2. Verify the two checksum records, then run the currently installed `scripts/package_app.py --verify-only` with the expected full commit, tag, and `--require-rollback` arguments.
3. Extract the archive, run the extracted release's verifier against the same three assets, run its monitor configuration `check`, and run its command-scoped `bridge-check-schema2`. Stop on any mismatch.
4. Create `/usr/local/libexec` root-owned mode `0755` if it is absent, then install the extracted `deploy/pull/casino-release-poller.sh` at `/usr/local/libexec/casino-release-poller` with root ownership and mode `0755`.
5. Install `casino-release-poller.service.template` and `casino-release-poller.timer.template` as `/etc/systemd/system/casino-release-poller.service` and `.timer`; replace the edge-monitor service with its same-release template. Keep `/etc/casino/release-poller.env` absent for anonymous public access or create it root-owned mode `0640` with only the optional values above.
6. Run `systemd-analyze verify` on all three service/timer files, then `systemctl daemon-reload`. Do not enable the timer yet.
7. While the new immutable release is newer than the installed application, execute `sudo /usr/local/libexec/casino-release-poller rollback-drill` exactly once. The direct command reads only the allowlisted authorization and public-origin assignments from `/etc/casino/edge-monitor.env` when systemd has not supplied them; it never shell-sources or prints that file. The drill must activate and health-check the candidate, restore the exact predecessor, recheck schema `2` and authenticated health, leave the predecessor live, and log `decision=rollback_drill` without an alarm.
8. Execute `sudo systemctl start casino-release-poller.service`. Within one polling interval it must install the same verified release, expose its exact version and SHA in authenticated readiness, keep schema `2`, and clear `/var/lib/casino/release-poller/alarm`.
9. Enable future pulls with `sudo systemctl enable --now casino-release-poller.timer`; restart the edge-monitor timer so its next successful observation includes the release-lag check.
10. Paste only sanitized evidence to issue #732: release tag/full SHA, asset-verifier PASS, rollback-drill predecessor/candidate identities, before/after selector targets, schema `2` before/drill/after, exact readiness version/SHA, timer next-run timestamp, alarm absence, and `systemctl is-enabled/is-active` results. Never paste tokens or environment-file bytes.

If the drill or first delivery fails, the EXIT path removes only its captured direct-child `.poller.<suffix>` work directory and writes the durable `poll_failed` alarm after rollback. Leave that alarm and the journal intact, keep the restored predecessor live, disable the poller timer, and stop. Do not retry with altered bytes; inspect `journalctl -u casino-release-poller.service` and open a bounded follow-up.

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

v0.9.5.72 packages accepted performance-target PR #676 and closes repository-controlled issue #323. Exact-source hosted JSON and disposable-MySQL request-latency grids now fail closed against the accepted authenticated game-state read targets while write and concurrency-eight cohorts remain diagnostic and the one-worker/two-thread production topology remains unchanged. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.71 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.73 packages accepted verified-email enrollment PR #678 and closes repository-controlled issue #69. Email/password enrollment remains disabled by default; no canonical user, player, balance, or session exists before bearer verification, and successful verification still requires a separate login. Recoverable resend, ownership-bound cancellation, rate controls, terminal scrubbing, and bounded retention authorize no live mail/provider traffic or public signup. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.72 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.74 packages accepted secure mobile-core PR #680, closes repository-controlled issue #681, and leaves umbrella issue #183 open for native OAuth handoff, signed-device, verified-link, store, and physical-device evidence. The default-off native path uses direct OS transport, OS-vault bearer plus matching session CSRF, exact lifecycle generations, and governed deep-link scrubbing while browser/PWA cookie behavior remains unchanged. Deployment must prove exact schema 2 before and after activation while invoking no migration. Its compatibility record retains exact terminal-green v0.9.5.73 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.75 packages accepted inert game-action lifecycle Phase A PR #686, closes bounded issue #685, and leaves umbrella issue #683 open for governed route and game adoption. Provider-neutral JSON and exact clean-schema-four MySQL storage can converge immutable execute-or-uncommitted claims, exact receipts, resolver-first cancellation, and reset epochs, but no route, game, public API, or production path activates that capacity. The catalog remains minimum 2, expected 4, and apply held; deployment must prove exact schema 2 before and after activation while invoking no migration or grant mutation. Its compatibility record retains exact terminal-green v0.9.5.74 as the application-only predecessor; database rollback remains prohibited. Issues #168 and #488 also remain open.

v0.9.5.76 packages accepted complete catalog economics PR #691 and records issue #456 complete. The repository now validates all 46 games and 74 wager selectors through source-bound deterministic expectations, with retained deep Slots and Keno artifacts, while game engines, paytables, APIs, wager acceptance, wallet behavior, and settlements remain unchanged. The catalog remains minimum 2, expected 4, and apply held; deployment must prove exact schema 2 before and after activation while invoking no migration or grant mutation. Its compatibility record retains exact terminal-green v0.9.5.75 as the application-only predecessor; database rollback remains prohibited.

v0.9.5.77 packages accepted repository-side pull-poller PR #736 and closes release prerequisite #735 while parent #732 remains open for owner-run installation evidence. GitHub Actions publish immutable assets only; the production host polls stable releases, verifies exact assets, provenance, inventory, schema-two compatibility, health, readiness, rollback, and alarms, then adopts the application atomically. The catalog remains minimum 2, expected 4, and apply held; no migration, grant mutation, or database rollback is authorized. Its compatibility record retains exact immutable v0.9.5.76 as the application-only predecessor.

v0.9.5.78 packages the accepted post-v0.9.5.77 reliability and provider-atomic state wave and carries the same fail-closed pull-delivery boundary into the owner-authorized #732 installation. The first pull must execute the documented rollback drill, retain exact schema 2 and persistence, prove authenticated readiness at the release SHA, clear the lag alarm, and leave the timer active. Its compatibility record retains exact immutable v0.9.5.77 as the application-only predecessor; database rollback, migration application, and grant mutation remain prohibited.

v0.9.5.79 supersedes v0.9.5.78 for production delivery after the first v0.9.5.78 host attempt failed closed during its direct rollback drill and restored the exact live predecessor. The replacement poller reads only the exact monitor authorization and public-origin keys from the root-owned monitor environment when a direct command lacks systemd injection, never sources the file as shell code, and removes only its validated owned work directory before writing the durable failure alarm. Its listener-free and disposable state-machine evidence covers candidate failure, predecessor failure, and a successful rollback drill followed by an ordinary poll. v0.9.5.78 is never retried; the v0.9.5.79 installation must retain exact schema 2 and persistence, prove authenticated readiness at the release SHA, clear the lag alarm, and leave the timer active. Its compatibility record retains exact immutable v0.9.5.78 as the application-only predecessor; database rollback, migration application, and grant mutation remain prohibited.

## Retired push-delivery history

The original GitHub-hosted deployment job published releases successfully but could not reach the source-restricted production SSH ingress. Its first SSH connection timed out before remote command success, asset transfer, or activation, and repeated ordinary releases therefore accumulated while production stayed stale. Installing broader inbound credentials would not repair that network ownership mismatch.

Issue #732 retires that designed-to-fail leg. Protected-main Actions own immutable publication only; the production host owns delivery through the pull timer. Do not restore or rerun the old SSH job. A future self-hosted runner remains a separately governed alternative under closed issue #450, not a fallback inside this runbook.

## One-time pull setup checklist

1. Keep the existing monitor bearer and application digest pair valid with the read-only `check` command above.
2. Complete the exact owner host-install gate in this document once, including the rollback drill before enabling the timer.
3. Confirm both `casino-release-poller.timer` and `casino-edge-monitor.timer` are enabled and have future trigger times.
4. Confirm the poller alarm is absent and direct authenticated readiness reports the installed immutable release version and full SHA.
5. Attach sanitized host evidence to #732; keep umbrella #435 open until that evidence is accepted.

After this setup is green, future unique packaged releases should reach production within one poll interval without an inbound deployment connection or manual browser login.

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

The production source of truth is the GitHub Release asset built from the exact protected-main commit. If a later protected-main commit should go live, create a new packaged version, let the protected-main workflow publish it, and let the host poller perform the verified delivery.
