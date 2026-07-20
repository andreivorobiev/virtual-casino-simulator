# Restricted-preview security policy

Requirements `SEC-010`, `SESSION-006`, `ADMIN-024`, `AUTH-007`, and `TEST-047` define the repository-side security boundary for the invite-only Casino preview. This packet does not change DNS, TLS, firewall rules, services, credentials, data, or public exposure.

## Required production configuration

The released hostname is documented as `https://casino.andvor.com`, but it remains inactive until the separate edge cutover packet is approved. Production startup requires:

- `CASINO_RESTRICTED_PREVIEW=1`;
- `CASINO_CANONICAL_ORIGIN=https://casino.andvor.com`;
- `CASINO_TRUSTED_PROXY` set to exactly one loopback IP used by the separately approved edge proxy;
- `CASINO_SESSION_SAMESITE=Strict` or `Lax`;
- bounded `CASINO_MAX_BODY_BYTES`, `CASINO_RATE_LIMIT_REQUESTS`, and `CASINO_RATE_LIMIT_WINDOW_SECONDS` values when the reviewed defaults are unsuitable.

Tests use only reserved `.invalid` origins and disposable state. Missing, malformed, or weakened security configuration prevents the production adapter from becoming ready.

## Request and proxy boundary

Every request must use the exact canonical Host authority. Only the configured direct loopback peer may provide one `X-Forwarded-For` value paired with `X-Forwarded-Proto: https`; partial values, lists, alternate forwarding headers, and forwarding metadata from any other peer fail closed. The edge must replace, not append, those two headers and must not forward `Forwarded`, `X-Forwarded-Host`, or `X-Forwarded-Port`.

Every `POST`, `PUT`, `PATCH`, and `DELETE` requires both the exact configured Origin and the per-session CSRF proof. Login uses the host-only bootstrap CSRF cookie; successful login rotates both session and CSRF values. The session cookie is host-only, Secure, HttpOnly, and SameSite-governed. Privilege-bearing account changes revoke existing sessions.

## Restricted access

Anonymous application access is limited to `/healthz`, `/api/v2/auth/login`, boolean-only OAuth provider status, and exact Google/Facebook start and callback routes. Readiness remains authenticated. Admin HTML, JavaScript, and APIs require an active Admin session. Public signup, provider-driven user creation, and email-based linking remain absent. Manual invitation is the only enrollment path; local password remains the recovery path, while an explicitly configured provider may authenticate only a previously linked active invite user.

Both providers are independently disabled by default. Start requires exact Origin and double-submit CSRF proof, callbacks require one-time state plus the initiating browser binding, and authenticated linking also requires exact initiating user/session ownership and explicit confirmation. Disabling a flag prevents new flows and invalidates provider-authenticated sessions; unlink preserves local-password sessions.

## Response, bounds, and logs

The adapter emits the tracked CSP, anti-framing, MIME-sniffing, referrer, permissions, cross-origin isolation, and HSTS policy on effective HTTPS responses. Request bodies, session retention, and per-client request windows are bounded. Security logs contain only a generated request identifier, method, fixed route class, and status code; they never record request paths, query strings, credentials, cookies, CSRF values, forwarding values, or request bodies.

The compatibility artifact at `contracts/compatibility/restricted-preview-security.json` is the machine-checked access-policy source. The listener-free focused suite and copied production-service tests must pass before issue #201 may release an infrastructure cutover.
