# Virtual Casino Simulator v9.4.0 Release Notes

## Compatible restricted-preview update

- Packages the compatible Casino changes merged after v9.3.0, including gameplay and ledger correctness fixes, durable retry and reconnect behavior, responsive interface improvements, localization coverage, and static-cache parity.
- Preserves the accepted production adapter, restricted-preview session and Origin security, explicit MySQL migration boundary, encrypted recovery controls, and nginx/ACME observation and rollback gates.
- Keeps the MySQL schema at exact version 2 and preserves the DDL-free runtime account boundary; this release introduces no database rollback path.
- Keeps admission manual-invite only, with public signup and live OAuth disabled. Unrestricted public launch remains held under issue #209.
- Binds the retained v9.3.0 release manifest as the immediate application-only rollback predecessor under `TOOL-003`; immutable publication and deployment remain separately gated.

## Post-release module addendum: invite-only OAuth runtime

- Implements Google and Facebook authorization-code authentication only for existing private-invite accounts, with authenticated explicit first linking, prelinked-subject-only sign-in, no signup, and no email-based account association.
- Adds strict state, Google OIDC nonce and signed-token validation, S256 PKCE, Facebook app/token debugging, atomic expiring flow replay protection, transactional compound identity links, safe unlink, rollback-aware sessions, rate limits, safe redirects, and secret-free logging/errors through mockable provider adapters.
- Keeps both provider flags disabled by default and leaves frozen `/api/v1` unchanged. Live provider configuration, enablement, security-sensitive merge, and deployment remain held behind the exact separate Workroom approval gate recorded in issue #326.
- Adds permanent `OAUTH-007` through `OAUTH-010` and `TEST-074` traceability. Browser tests and visual-matrix rows are authored for GitHub checks; local Playwright execution remains skipped under the owner's machine-performance restriction.

## Prior v9.3.0 release record

### Private-invite restricted-preview release

- Packages the accepted production WSGI adapter and supervised graceful-service policy from issue #202 with loopback-only application binding and copied-release smoke coverage.
- Packages hardened sessions, exact Origin and trusted-proxy enforcement, CSRF protection, security headers, bounded requests and sessions, and the Admin/manual-invite boundary from issue #203.
- Packages the checksum-bound MySQL v2 migration runner, deployment-only DDL boundary, fail-closed migration state, and DDL-free runtime compatibility from issue #204.
- Packages the authenticated encrypted recovery tooling and clean-target restore gates from issue #205 without embedding recovery objects, credentials, private data, or provider identifiers.
- Packages the reviewed nginx, ACME, observation, smoke, and application-only rollback preparation from issue #206 without activating an edge, service, listener, certificate, DNS record, or firewall rule.
- Keeps public signup and live OAuth disabled. Unrestricted public launch remains outside this release under issue #209, and the release artifact does not authorize issue #201 deployment or exposure.
- Binds packaged release v9.2.0 as the immediate application-only rollback predecessor; database rollback is prohibited and immutable publication still requires its retained, checksum-verified release manifest under `TOOL-003`.
- Adds the reviewed one-time protected-main recovery for the missing v9.2.0 Release: exact pre-bump commit, two byte-identical rebuilds, checksum-bound v9.3.0 successor receipt, pre-existing tag/Release refusal, non-latest publication, and no clobber, upload-after-create, deletion, direct tag push, or manual local publication path.

## Prior v9.2.0 release record

## Post-release module addendum: encrypted recovery gate

- Adds permanent `MYSQL-006`, `TOOL-004`, and `TEST-049` repository traceability for issue #205: authenticated chunked encryption, independent evidence authorities, bounded retention and recovery-age checks, clean-target restore authorization, and quarantine-on-partial-failure behavior.
- Keeps provider-current backup evidence, a real encrypted off-instance recovery point, and a real clean-target restore proof as explicit external deployment blockers; this repository packet does not mutate infrastructure or claim those gates completed.

## Post-release module addendum: explicit MySQL migrations

- Adds the repository-only issue #204 gate with permanent `MYSQL-005`, `STORAGE-007`, and `TEST-048`: checksum-pinned ordered migrations, deployment-only credentials, HMAC-bound recovery preflight, fail-closed dirty state, DDL-free runtime compatibility, disposable MySQL 8.4 evidence, and release schema provenance.

## Post-release module addendum: restricted-preview security boundary

- Requires exact canonical Host and Origin validation, per-session CSRF proof, host-only Secure session cookies, and one exact loopback trusted-proxy contract for unsafe production requests.
- Restricts anonymous routes to login and liveness, protects readiness and every Admin surface, keeps public signup and live OAuth absent, and revokes sessions after privilege-bearing account changes.
- Adds bounded request bodies, sessions, and per-client windows; secret-safe fixed-class security logs; hardened browser request helpers; and fail-closed response security headers.
- Adds permanent `SEC-010`, `SESSION-006`, `ADMIN-024`, `AUTH-007`, and `TEST-047` traceability with listener-free hostile-request, concurrency, browser-helper, contract, and production-service regression evidence for GitHub issue #203.

## Reproducible release provenance gate

- Adds deterministic tracked-file application packaging with normalized ZIP metadata and a complete checksum inventory.
- Adds a canonical external manifest binding the artifact to exact source, packaged version, supported Python, module revisions, dependency/SBOM inputs, validation results, and every packaged file.
- Adds negative private/runtime/untracked-content tests, archive-tamper checks, and listener-free clean extracted-copy smoke.
- Separates unpublished pull-request candidates from protected-tag immutable publication with an additional repository switch and environment gate.
- Requires a checksum-bound immediately previous artifact before publication and keeps database rollback outside the application-only rollback procedure.
- Implements permanent requirement `TOOL-003` for GitHub issue #199 without authorizing deployment or public exposure.

## Post-release module addendum: disabled OAuth provider foundation

- Adds provider-neutral local, Google, and Facebook abstractions with mocked claim, callback-proof, and canonical identity-link validation while registering no provider authorization, link, callback, exchange, SDK, or live transport route.
- Adds an Admin-only secret-safe diagnostic route plus EN/RU native-disabled Google/Facebook login controls; local password login and Operations readiness remain unchanged.
- Adds permanent `OAUTH-001` through `OAUTH-006` and `TEST-045` traceability with centrally discovered mocked, API, browser, contract, responsive visual, and protected-listener cleanup evidence for GitHub issue #70.

## Post-release module addendum: Operations foundation

- Adds minimal anonymous `/healthz`, authenticated `/readyz`, and Admin-only Operations diagnostics with bounded storage probes and strict secret-safe payload validation.
- Adds EN/RU live, degraded, and client-derived down Admin states across governed viewports, using text and symbols rather than color alone.
- Adds permanent `OPS-001` through `OPS-005` and `TEST-044` traceability plus API, browser, copied-deployment, build-provenance, and listener-closure evidence for GitHub issue #72.

## Post-release module addendum: hostile-client server authority

- Adds a generated compatibility inventory for every state-changing action in all 30 currently registered games, with explicit intent, validation, outcome, storage/ledger, and response owners after Texas Hold'em integration.
- Strips client-authored privilege, wallet, RNG, result, payout, hidden-state, and round-control fields before game dispatch while preserving authenticated session precedence.
- Removes the client-reachable Roulette forced-result seam and verifies hostile attempts receive a server-owned wheel outcome.
- Adds catalog-wide API drift checks, browser wallet-tamper recovery, permanent `SEC-001` through `SEC-009` requirements, and links to existing two-user, restart, ledger, Admin, concurrency, and Long Suite evidence.

## Post-release module addendum: Texas Hold'em Practice Table

- Registers issue #95 through canonical catalog, contract, requirement, visual, and test-discovery surfaces after the accepted server-authority gate.
- Moves the authenticated human and all three funded practice opponents through storage-enforced escrow, refund, and payout ledger actions while retaining session-private cards, reload-safe state, and retry receipts.
- Extends the `SEC-001` through `SEC-009` hostile-client matrix with every Texas Hold'em mutation route and focused raw-API, cross-user, turn, outcome, ledger, replay, restart, Admin, concurrency, refresh, EN/RU, and Long Suite evidence.

## Post-release module addendum: funded practice opponents

- Allocates the three named bot player accounts as funded server-managed opponents for the held Texas Hold'em Practice Table proposal.
- Adds a public core accounting seam for opponent escrow, refunds, payouts, and fixed funding through storage-enforced ledger actions.
- Adds Admin account allocation, idempotent funding, append-only activity inspection, and EN/RU Players & Bots presentation.
- Adds restart, conflict, two-owner, 25-process duplicate, API, browser, and Admin evidence for GitHub issue #189 without registering PR #120.

## Post-release module addendum: storage action idempotency

- Adds `ledger.transact_once`, `debit_once`, and `credit_once` as additive provider-backed primitives for durable money-action identities.
- Enforces exact replay and changed-reuse conflict semantics across the JSON and MySQL providers without changing existing `/api/v1` response contracts.
- Adds a JSON process lock and recoverable committed-action journal for restart and lost-response safety.
- Adds nullable MySQL action columns and a unique `(player_id, action_scope, action_key)` index in the same transaction boundary as balance and ledger writes.
- Adds 25-way duplicate-family, restart, conflict, lost-response, static MySQL, and opt-in live two-process MySQL evidence for GitHub issue #190.

## Release name
Control Plane + UX Stabilization Release

## Summary
v9.1.0 fixes the major control and UX issues identified after v9.0.0. It separates bot controllers from game modules, moves global sound and voice configuration into `/admin`, redesigns the admin console, centralizes autoplay, fixes the Roulette wheel result state, and stabilizes game screen layouts during actions.

## Module revisions

| Module | Revision |
|---|---:|
| Application | 9.1.0 |
| Core | 9.1.0 |
| Ledger | 9.0.1 |
| Players | 9.0.1 |
| Bot Controller | 1.0.0 |
| Autoplay Controller | 1.1.0 |
| Audio / Voice | 9.1.0 |
| Logging | 9.1.0 |
| Roulette | 9.1.0 |
| Slots | 9.0.1 |
| Blackjack | 9.0.1 |
| Baccarat | 9.0.1 |
| Keno | 9.0.1 |
| Bingo | 9.0.1 |
| Admin | 1.1.0 |
| Tests | 1.1.0 |
| Docs | 1.1.0 |

## Changes

### Bot controller separation
- Added `casino/bots/` with bot profiles, capabilities, strategies, and controller actions.
- Removed per-game bot settings endpoints from Roulette, Baccarat, Keno, and Bingo.
- Added `/api/v1/bots`, `/api/v1/bots/capabilities`, `/api/v1/games/{game_id}/eligible-bots`, and `/api/v1/games/{game_id}/bots/play-round`.
- Games no longer own bot configuration. Bots are controllers for player accounts.

### Global audio and voice
- Added persisted audio settings under `data/settings/audio.json`.
- Moved full sound and voice controls to `/admin -> Audio & Voice`.
- Roulette no longer renders the voice settings panel.
- Added master mute, SFX volume, voice volume, selected voice, rate, pitch, and per-game announcement toggles.

### Admin redesign
- Rebuilt `/admin` as a sidebar/topbar control plane.
- Added Dashboard, Players & Bots, Ledger, History, Telemetry, Game States, Audio & Voice, Autoplay, Requirements, Tests, and System tabs.
- Added editable bot strategies and stakes in Admin.
- Added Admin Stop All Autoplay.

### Autoplay controller
- Added server-registered autoplay sessions with `autoplay_id`.
- Added `/api/v1/autoplay/start`, `/stop`, `/tick`, `/complete`, `/finish-stop`, `/stop-all`, and session listing endpoints.
- Reworked browser autoplay to use shared session state and a central stop contract.
- Stop now prevents the next action from starting after the current atomic action is safe.
- Bingo autoplay now uses stepwise ball calls rather than one long auto-to-Bingo call.

### Roulette wheel and UX
- Roulette wheel no longer defaults to a fake `0` state when there has not been a spin.
- Roulette wheel highlights the latest actual spin result.
- Roulette bot actions happen through the bot controller before the spin.
- Added layout-stability styles for game stages, controls, result panels, and autoplay panels.

### Tests and documentation
- Requirement registry increased from 287 to 344 requirements.
- Added new `BOT`, `AUDIO`, `AUTO`, and `UX` requirement families.
- Updated API tests for bot controller, audio persistence, and autoplay lifecycle.
- Updated browser tests for Admin Audio and Roulette autoplay stop behavior.
- Generated `docs/requirements_validation_v9_1.pdf` and `docs/requirements_validation_v9_1.md`.

## Validation run in packaging environment

```bash
python -m py_compile run.py $(find casino -name '*.py') verify_rules.py tests/run_tests.py
python verify_rules.py
python tests/run_tests.py --api
node --check web/app.js
node --check web/core/*.js
node --check web/games/*.js
node --check web/admin.js
```

## Browser tests on your machine

```powershell
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 tests/run_tests.py --browser
```

## Known limitations
- Blackjack autoplay remains disabled unless a dedicated Blackjack strategy controller is added later.
- This is still fake-money entertainment software only; it has no real-money or regulated casino functionality.


## Documentation refresh
- Replaced the requirements/validation PDF with a redesigned landscape report.
- Split diagrams into separate clean views with non-overlapping connectors.
- Added clearer summaries, module tables, and requirement registry formatting.


## v9.1.1 - Repository Bootstrap + Codex Migration Payload

- GitHub/Codex governance payload added.
- Module manifests and API contract skeletons added.
- Commenting policy and checker added.
- CI workflow scaffolding and Codex prompts added.
- No intentional gameplay behavior changes from v9.1.0.
