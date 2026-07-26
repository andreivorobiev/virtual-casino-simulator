# Restricted-preview security policy

Requirements `SEC-010`, `SESSION-006`, `ADMIN-024`, `AUTH-007`, and `TEST-047` define the repository-side security boundary for the invite-only Casino preview. This packet does not change DNS, TLS, firewall rules, services, credentials, data, or public exposure.

## Required production configuration

The released Casino hostname is `https://casino.tiltseven.com`. Production startup requires:

- `CASINO_RESTRICTED_PREVIEW=1`;
- `CASINO_CANONICAL_ORIGIN=https://casino.tiltseven.com`;
- `CASINO_TRUSTED_PROXY` set to exactly one loopback IP used by the separately approved edge proxy;
- `CASINO_SESSION_SAMESITE=Strict` or `Lax`;
- bounded `CASINO_MAX_BODY_BYTES`, `CASINO_RATE_LIMIT_REQUESTS`, and `CASINO_RATE_LIMIT_WINDOW_SECONDS` values when the reviewed defaults are unsuitable.

Tests use only reserved `.invalid` origins and disposable state. Missing, malformed, or weakened security configuration prevents the production adapter from becoming ready.

## Request and proxy boundary

Every request must use the exact canonical Host authority. Only the configured direct loopback peer may provide one `X-Forwarded-For` value paired with `X-Forwarded-Proto: https`; partial values, lists, alternate forwarding headers, and forwarding metadata from any other peer fail closed. The edge must replace, not append, those two headers and must not forward `Forwarded`, `X-Forwarded-Host`, or `X-Forwarded-Port`.

Every `POST`, `PUT`, `PATCH`, and `DELETE` requires both the exact configured Origin and the appropriate CSRF proof. Anonymous login, guest, invitation-redemption, and disabled-provider start requests use the host-only bootstrap CSRF cookie; authenticated linking also requires the exact initiating session's CSRF value. Successful login rotates both session and CSRF values. The session cookie is host-only, Secure, HttpOnly, and SameSite-governed. Privilege-bearing account changes revoke existing sessions.

## Restricted access

Anonymous application access is limited to `/healthz`, `/api/v2/auth/login`, the owner-approved repository-only guest and invitation-redemption routes, boolean OAuth availability, and the exact Google/Facebook start/callback shapes. Readiness remains authenticated through either a normal Admin session or the root-managed deployment monitor bearer token accepted only by `/readyz` and `/api/v2/admin/operations`. Admin HTML, JavaScript, and all other Admin APIs require an active Admin session. Public signup and provider-created accounts remain absent. The OAuth routes are disabled and provider-network inaccessible by default; they become executable only if both provider-specific gates and every future external release condition are separately satisfied. First linking requires the exact authenticated existing private-invite local-password account and explicit confirmation, and later sign-in requires its prior provider-subject link. Provider email never selects an account. Invitation and local-password recovery remain authoritative; a guest is never a registered account and cannot be recovered, converted, or linked.

## Disposable guest-trial boundary

Guest creation requires an affirmative `private-beta-1` terms acceptance and creates a new non-Admin guest principal with an isolated 5,000-play-token wallet. The service limits active guest principals, permits at most 1,000 state-changing game attempts per disposable session, clamps one concurrent guest autoplay registration to 25 rounds, ends guests after 30 minutes of server-observed inactivity or four hours absolute lifetime, and revokes the wallet, sessions, identity, and guest-owned autoplay on explicit End. The cookie is a browser-session cookie; a separate one-time context proof is retained only in browser `sessionStorage`, while the server stores only its SHA-256 digest. A cookie without that proof cannot restore the trial after browser-context loss. A `pagehide` marker makes departure observable while the same browser context can still reload.

Guest analytics are Admin-only and contain no user, player, auth-session, cookie, browser-proof, email, network, or user-agent identifier. Raw rows retain only an unrelated analytics id, timestamps, bounded lifecycle reason, locale, coarse device class, game slug, the named journey milestones, allowlisted server event/action/error categories, coarse latency buckets, fake-token-only wager/return/net totals, and aggregate counters for 30 days; daily aggregates are retained for 400 days. Admin filters are limited to time bounds, lifecycle, catalog game, locale, coarse device, first-round completion, sanitized error category, and list limit. Locale/device error breakdowns require a cohort of at least five, timelines retain at most 80 allowlisted rows, no export is provided, and fixed server cleanup cutoffs cannot be widened or redirected by an API caller. The v2 guest and Admin contracts plus `contracts/compatibility/guest-trials-restricted-preview.json` are authoritative.

This scope changes no deployment, DNS, TLS, firewall, provider, billing, or public-exposure state and does not authorize unrestricted launch under issue #209.

## Response, bounds, and logs

The adapter emits the tracked CSP, anti-framing, MIME-sniffing, referrer, permissions, cross-origin isolation, and HSTS policy on effective HTTPS responses. Request bodies, session retention, and per-client request windows are bounded. Security logs contain only a generated request identifier, method, fixed route class, and status code; they never record request paths, query strings, credentials, cookies, CSRF values, forwarding values, or request bodies.

The compatibility artifact at `contracts/compatibility/restricted-preview-security.json` is the machine-checked access-policy source. The listener-free focused suite and copied production-service tests must pass before issue #201 may release an infrastructure cutover.
