# Offline-safe PWA foundation

Status: narrowed repository foundation authorized by Workroom #29 comment 5049351844.

This slice adds installable browser metadata and an offline-safe public shell. It does not deploy the application, authorize public hosting, create app-store or provider accounts, package a native application, change DNS or billing, or complete unrestricted-launch issue #209. Full issue #182 remains open while #74 and #168 and representative Android Chrome plus iOS Safari/Home Screen install and relaunch evidence remain incomplete.

## Canonical identity and assets

`modules/module-manifest.json` is the canonical packaged application release. `web/sw.js` binds its cache name to that version. The manifest exposes complete 192×192 and 512×512 PNG assets for both `any` and `maskable` purposes; the Apple touch icon uses the reviewed 192×192 asset. Maskable art keeps meaningful wheel geometry inside the mask-safe central region.

## Exact cache boundary

The worker caches only the exact credential-free public paths declared by `SHELL_ASSETS` in `web/sw.js`: the index, shell stylesheet and controller modules, manifest, reviewed icons, and the en-US/ru-RU shell and feedback dictionaries needed to render the public shell. Prefix discovery is forbidden. Worker fetches omit credentials and carry one fixed public-shell marker; both supported HTTP adapters honor it only when Cookie and Authorization are absent, preventing the cached index response from setting or refreshing a CSRF cookie. The worker intentionally overrides the adapters' generic static `no-store` header only inside this exact credential-free allowlist. Query-bearing static requests, cross-origin traffic, non-GET requests, Authorization-bearing requests, API paths, Admin routes, game modules, authenticated responses, wallet values, ledger data, outcomes, credentials, private content, OAuth, invitations, feedback payloads, and provider traffic are never intercepted or cached.

Application navigations are network-first. Only reviewed root, game-route, and invitation-route patterns may fall back to the public cached index when the network is absent. Dynamic game modules and authoritative state remain network-only, so an offline shell cannot present a wager or result as accepted.

## Offline and reconnect behavior

The browser API boundary rejects every authoritative request while `navigator.onLine` is false; mutations are never queued for replay. The PWA controller natively disables currently rendered login, terms, invitation, wallet, feedback, and game controls that require the server. Local navigation remains available.

When connectivity returns, the controller keeps those actions disabled while the application revalidates the current session, reloads shell/catalog and wallet state, and remounts the active route from the authoritative backend. It releases actions only after that refresh succeeds. An expired session returns to sign-in; a failed refresh remains fail-closed with localized EN/RU status.

## Update and rollback behavior

Installation fetches and validates the complete public allowlist before the new worker can install. A failed installation leaves the previous complete worker active. A newly installed worker waits until the user activates the localized update action. Controller-version mismatch produces an explicit stale-client state. Activation deletes only prior caches with the Casino static-shell prefix and claims clients only after the new cache exists. If activation does not complete within the bounded client timeout, the current page remains active and shows update failure.

Repository rollback is a normal protected-branch revert. Any future deployment must independently prove immutable release provenance, predecessor compatibility, cache retirement, readiness, persistence, monitoring, and rollback; none of those actions are authorized by this slice.

## Evidence boundary

TEST-095 owns browser-free manifest, PNG, cache-policy, request-exclusion, version, and update-cleanup tests plus exact-head Browser Tests. Browser evidence covers EN/RU cold start, warm start, offline, reconnecting, update available, update failed, stale client, expired session, and route restoration at all four governed viewports. Android and iOS metadata are validated only as browser-platform prerequisites. Native installation and relaunch acceptance must not be inferred from this evidence and remains on open issue #182.
