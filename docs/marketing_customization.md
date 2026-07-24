# Marketing and brand customization

This guide separates the replaceable marketing layer from the reusable casino simulator. It is for teams that want to clone the repository, apply their own public brand, and run the site without accidentally changing game rules, API contracts, ledger behavior, security gates, or release provenance.

Related requirements: DOC-017 and TOOL-006 keep this guide discoverable through the generated Markdown catalog.

## Separation model

Treat the repository as four layers:

| Layer | Purpose | Typical owner | Change risk |
|---|---|---|---|
| Simulator core | Games, wallet ledger, auth, Admin, API contracts, requirements, tests, persistence, and release tooling. | Engineering | High: changes require requirements, tests, versions, and exact-head evidence. |
| App brand shell | Product name, shell copy, app icons, PWA manifest, browser titles, mobile display names, and localized UI labels. | Product plus engineering | Medium: user-visible changes require localization and browser evidence. |
| Public marketing site | Landing pages, sales copy, screenshots, brand story, domain routing, and calls to action. | Marketing plus web owner | Medium: keep it separate from the simulator runtime and release it deliberately. |
| Deployment identity | Canonical origin, allowed host, TLS, nginx, OAuth callback base, mail-link base, cookie assumptions, release tags, and rollback artifacts. | Operations | High: must move atomically through the deployment gate. |

The goal is simple: someone should be able to replace the public brand without rewriting the casino engine or weakening the fake-money safety boundary.

## Keep These Stable

Do not rename or reshape these just to apply a new marketing identity:

- API routes, request/response envelopes, OpenAPI compatibility files, and `/api/v1` contract titles.
- Requirement IDs, test IDs, module IDs, game IDs, browser route IDs, and saved-state keys.
- Ledger semantics for bets, refunds, winnings, wallet balance, and audit events.
- The play-token legal position: no real-money gambling, no cash value, no withdrawal, and no redemption for value.
- Disabled-by-default provider, OAuth, mail, public signup, and deployment gates.
- Release artifact identity, package versioning, rollback eligibility, and source provenance.

Internal names can remain stable even when the public site uses a new brand. A fork can market the app as something else while still keeping internal API titles such as "Virtual Casino" for compatibility and history.

## Replaceable Brand Surfaces

Use this inventory when applying a new brand:

| Surface | Primary files | Notes |
|---|---|---|
| Browser shell title and lockup | `web/index.html`, `web/i18n/en-US/shell.json`, `web/i18n/ru-RU/shell.json` | Keep EN/RU key parity and placeholder parity. Browser evidence is required for visible copy changes. |
| Admin browser title and Admin copy | `web/admin.html`, `web/i18n/en-US/admin.json`, `web/i18n/ru-RU/admin.json` | Admin is an operational control plane, not a marketing landing page. Keep labels clear and work-focused. |
| Visual brand assets | `web/assets/favicon.svg`, `web/assets/pwa-icon-*.png`, `web/assets/pwa-maskable-*.png`, `web/assets/casino-backdrop.png`, `web/assets/slot-machine.png` | Preserve dimensions, maskable icon purpose, contrast, and PWA manifest compatibility. |
| PWA metadata | `web/manifest.webmanifest` | Names, short names, icons, display mode, and theme colors are user-visible and cached by service workers. |
| Native wrapper names | `mobile/capacitor.config.json`, `mobile/android/app/src/main/res/values/strings.xml`, `mobile/ios/App/App/Info.plist`, `mobile/package.json` | Update only when packaging mobile shells. Native install/relaunch evidence remains separate from web-only evidence. |
| Legal and safety copy | `docs/legal/README.md`, `docs/legal/terms.md`, `docs/legal/privacy.md`, `NOTICE`, `LICENSE`, `CONTRIBUTING.md` | Marketing can change tone, but must not imply real-money wagering or cash-out value. License and notice changes need legal review. |
| Public marketing pages | Prefer a separate `marketing/` or `site/` root, a separate repository, or a separate host | Keep landing pages independent from game runtime code. Link to the app instead of importing runtime modules. |

## Public Marketing Site Boundary

If a fork adds a public marketing website, keep it intentionally separate:

- Put landing-page source under a dedicated root such as `marketing/` or host it in a separate repository.
- Do not import `casino/`, `web/app.js`, `web/admin.js`, game modules, or runtime API helpers into marketing pages.
- Do not make marketing pages depend on authenticated app state, wallet state, ledger state, or provider credentials.
- Link users to the app URL as a normal navigation target.
- Keep marketing routes, assets, and deployment steps out of the game app's service-worker static allowlist unless a release packet explicitly adds them.
- Keep marketing claims compatible with the legal docs: fake-money simulator, private preview or demo status when applicable, no real-money gambling, no cash-out, no prize redemption.

This lets a downstream team replace the public story without creating a second application shell inside the casino runtime.

## Deployment Identity Is Not Marketing Copy

Domain and origin changes are operational changes, not simple copy changes. Move these together through the deployment gate:

- Runtime environment, including `CASINO_CANONICAL_ORIGIN`.
- `deploy/edge/restricted-preview.json`.
- `deploy/nginx/casino.conf.template`.
- `contracts/compatibility/restricted-preview-security.json`.
- `scripts/edge_gate.py`.
- `docs/restricted_preview_security.md`.
- OAuth public base URL, mail canonical origin, callback registrations, cookie assumptions, TLS, and DNS.

Changing only one of those surfaces can produce a site that loads but rejects login, state-changing requests, OAuth callbacks, or recovery links.

## Fork Customization Flow

Use this order when cloning and applying a new brand:

1. Clone the repository and run the default app unchanged.
2. Record the current packaged release and module versions from `modules/module-manifest.json`.
3. Choose the public brand kit: product name, logo, favicon, PWA icons, screenshots, domain plan, legal wording, and EN/RU copy expectations.
4. Apply app-shell branding only to the replaceable surfaces listed above.
5. Keep the game catalog, APIs, module IDs, requirement IDs, and ledger behavior stable unless a separate engineering task requires them to change.
6. Add or update a separate public marketing site only in its own root or repository.
7. Update legal/safety wording carefully and keep fake-money disclaimers intact.
8. Run documentation generation after Markdown changes: `python scripts/generate_docs.py`.
9. Run the relevant validators and browser evidence for every visible surface you changed.
10. Treat deployment identity, DNS, TLS, providers, mail, public exposure, and release artifacts as a separate gated deployment packet.

## Minimal Validation Checklist

For documentation-only marketing guidance:

- `python scripts/generate_docs.py --check`
- `python scripts/validate_requirements.py`
- `python scripts/validate_versions.py`

For user-visible app branding:

- `python scripts/generate_docs.py --check`
- `python scripts/validate_requirements.py`
- `python scripts/validate_versions.py`
- `python tests/run_tests.py --browser`
- Human review of EN/RU governed screenshots for the changed shell, Admin, PWA, or marketing surfaces.

For deployment identity changes:

- Run the normal release/deployment gate.
- Prove exact protected-main source, release artifact identity, rollback eligibility, TLS, DNS, readiness, persistence, monitoring, and host/origin behavior.
- Do not publish, enable providers, expose public signup, or mutate DNS from a documentation-only change.

## Handoff Summary

Marketing is replaceable. The simulator core is reusable. Deployment identity is gated. Keep those three ideas separate and a downstream team can safely bring its own brand, launch its own public site, and still preserve the tested fake-money casino engine.
